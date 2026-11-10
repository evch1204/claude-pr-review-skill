# Review: `transfers` → `main` ("updates")

**Verdict: don't merge yet.** The new `POST /transfers` endpoint lets any logged-in user move money out of any account, can be triggered cross-site, accepts negative amounts, and isn't transactional. Several of these are direct breaks of rules in `CONTRIBUTING.md`. The rest of the PR is unrelated churn that should be split out.

What the PR contains (3 commits: `wip`, `fix`, `more fixes`):
- `src/routes/transfers.js` (new): the transfer endpoint
- `src/app.js`: mounts the router (after `requireUser`, so routes do require a login)
- `package.json`: bumps express `^4.19.2` → `^4.21.1`, adds `lodash`
- `src/utils/format.js`: reformatting only (4-space indent, single quotes, no semicolons)

Existing tests pass (`node --test test/`, 2/2). Nothing tests the new endpoint.

---

## Blocking

### 1. No ownership check, so any user can drain any account
`src/routes/transfers.js:23`
```js
const from = await db.query("SELECT * FROM accounts WHERE id = $1", [fromId]);
```
`fromId` comes straight from the request body, and nothing checks that `from.owner_id === req.user.id`. Any authenticated user can send `{ fromId: <victim>, toId: <me>, amount: <balance> }`. `CONTRIBUTING.md` requires the owner check on every route that touches an account; `routes/accounts.js` already has the pattern in `loadOwnedAccount`.

### 2. No CSRF protection, and the session cookie is `SameSite=None`
`src/routes/transfers.js:20`. The route is `router.post("/transfers", async ...)` with no `csrfProtection`. `src/session.js` says the session cookie is `sameSite=none` so the partner widget works across origins. That means any website a logged-in user visits can send a transfer request with their cookie attached. This is a real attack, not a theoretical one. Add `csrfProtection` the way `POST /accounts/:id/nickname` does (also required by `CONTRIBUTING.md`).

### 3. Amount isn't validated, and a negative amount reverses the transfer
`src/routes/transfers.js:21-26`. `amount` is used as-is:
- **Negative amount:** `balance_cents < -5000` is false, so the balance check passes. Then the source account is *credited* and the destination is *debited*. Together with #1, this pulls money out of any `toId` without any balance check on that account.
- **Zero, fractions, strings, `null`:** `"abc"` or `null` fails the comparison (it evaluates to false), so the check passes and the bad value goes to Postgres, which errors (see #5). Fractions break the integer-cents rule.

Validate at the route boundary as `CONTRIBUTING.md` asks: `Number.isSafeInteger(amount) && amount > 0`. Also reject `fromId === toId` and missing IDs.

### 4. Not atomic, so concurrent requests can double-spend and a failure loses money
`src/routes/transfers.js:23-30`. There's a read, a separate balance check, then two independent `UPDATE`s on the shared pool:
- **Race:** two concurrent requests can both read the old balance, both pass the check, and both debit, which overdraws the account.
- **Partial failure:** if the second `UPDATE` fails, or the process dies between the two, the debit stays and the credit never happens, so money disappears.
- **Nonexistent `toId`:** the credit `UPDATE` matches 0 rows silently, so the debit succeeds and the money is gone. Nothing checks `rowCount`.

Use `db.withTransaction()` with `SELECT ... FOR UPDATE` on both rows (lock them in a consistent order, such as by id, to avoid deadlocks). Check the balance inside the transaction, and check that both accounts exist. `CONTRIBUTING.md` explicitly says "never issue dependent UPDATEs separately."

### 5. Errors aren't handled, so bad input can crash the server
The handler is `async` with no `try/catch`/`next(err)`. Express 4 doesn't catch rejected promises. On Node 15+ (the repo runs on 20), an unhandled rejection kills the process by default. Easy ways to trigger it:
- an unknown `fromId`: `from.rows[0]` is `undefined`, so `.balance_cents` throws a `TypeError`
- `amount: "abc"`: Postgres rejects the `UPDATE`
- any DB error

Any logged-in user (or a CSRF page, see #2) can take the API down with one request. Wrap the handler like `accounts.js` does, return 404 when an account is missing, and 400 for bad input.

### 6. Audit log write is fire-and-forget and outside the transfer
`src/routes/transfers.js:11`. `db.query("INSERT INTO audit_log ...")` isn't awaited:
- If it fails, that's another unhandled rejection (and crash, see #5).
- The transfer can succeed with no audit row, and the response reports `ok: true` regardless.
- It logs the raw `req.body`, unvalidated, which can be anything the client sends.

Do the audit insert inside the same transaction as the balance updates, await it, and log the validated `{ fromId, toId, amount }`.

---

## Should fix

- **The `proc` helper is hard to follow.** `proc(r, u, d, flag)` has single-letter params, and `flag` is always `true`, so the `{ ok: true }` branch is dead code and `r` is just a timestamp. Inline it or give it a clear name and signature. Note also that `transferId` is the audit-log row id; there's no `transfers` record. Decide whether that's intended.
- **No tests for the endpoint.** `supertest` is already a devDependency. At minimum, cover: transferring from someone else's account (403), missing CSRF token (403), negative, zero or non-integer amount (400), insufficient funds (400), unknown account (404), and a successful transfer that moves the balances and writes an audit row.
- **Unused `lodash` dependency.** Nothing in `src/` or `test/` requires it. Remove it.

## Scope / process

- **`src/utils/format.js` is a reformat only.** I checked it: whitespace, quotes and semicolons change, and behavior is the same (tests still pass). It also moves away from the repo's existing style (2-space indent, double quotes, semicolons, as in every other file). `CONTRIBUTING.md` says not to mix reformatting with features. Drop this commit.
- **The express bump is unrelated.** 4.21.x does include security fixes, so it's worth doing, but in its own PR.
- **Commit messages** (`wip`, `fix`, `more fixes`) and the **PR title/description** ("updates", empty) don't meet `CONTRIBUTING.md`. Please squash or reword (e.g. "Add transfer endpoint") and add a description covering what, why and how it was tested.

---

## Suggested shape for the handler

```js
router.post("/transfers", csrfProtection, async (req, res, next) => {
  try {
    const { fromId, toId, amount } = req.body;
    if (!fromId || !toId || fromId === toId || !Number.isSafeInteger(amount) || amount <= 0) {
      return res.status(400).json({ error: "invalid transfer" });
    }
    const result = await db.withTransaction(async (client) => {
      const { rows } = await client.query(
        "SELECT * FROM accounts WHERE id = ANY($1) ORDER BY id FOR UPDATE",
        [[fromId, toId]]
      );
      const from = rows.find((a) => a.id === fromId);
      const to = rows.find((a) => a.id === toId);
      if (!from || !to) return { status: 404, body: { error: "not found" } };
      if (from.owner_id !== req.user.id) return { status: 403, body: { error: "forbidden" } };
      if (from.balance_cents < amount) return { status: 400, body: { error: "insufficient funds" } };

      await client.query("UPDATE accounts SET balance_cents = balance_cents - $1 WHERE id = $2", [amount, fromId]);
      await client.query("UPDATE accounts SET balance_cents = balance_cents + $1 WHERE id = $2", [amount, toId]);
      const id = crypto.randomUUID();
      await client.query(
        "INSERT INTO audit_log (id, actor, action, details) VALUES ($1, $2, 'transfer', $3)",
        [id, req.user.id, JSON.stringify({ fromId, toId, amount })]
      );
      return { status: 200, body: { ok: true, transferId: id } };
    });
    res.status(result.status).json(result.body);
  } catch (err) {
    next(err);
  }
});
```
(Two things to adjust for your schema: if `balance_cents` is `BIGINT`, `pg` returns it as a string, so convert it before comparing. The `a.id === fromId` comparison may need the same treatment depending on the id type.)
