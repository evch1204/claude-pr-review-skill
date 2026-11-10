## PR Review: updates (`transfers` → `main`)

**Verdict: ❌ Request changes**: the new `POST /transfers` lets any logged-in user move money out of any account, and it breaks all four of the repo's money and safety rules in CONTRIBUTING.md.

The PR adds a `POST /transfers` route (`src/routes/transfers.js`) that checks the source balance, debits the source, credits the destination and writes an audit row. The route is wired into `app.js`. The PR also reformats `utils/format.js` and changes `package.json`.

### 🔴 Blocking

1. **No ownership check on the source account (IDOR)**: `src/routes/transfers.js:23`
   The source account is loaded by id only. Nothing compares `owner_id` to `req.user.id`, which breaks CONTRIBUTING: *"Every route that touches an account must check `account.owner_id === req.user.id`"*.
   **Breaks when:** user B sends `{fromId: <A's account>, toId: <B's account>, amount: 10000}`. A's money moves to B.
   **Fix:** load the source account through an ownership check, as `loadOwnedAccount` does in `routes/accounts.js:8-20`. Return 404 or 403 the same way. Also check that `toId` exists.

2. **`amount` is never validated**: `src/routes/transfers.js:21-29`
   CONTRIBUTING says *"Money is always integer cents … Validate amounts at the route boundary."*. Here `amount` goes straight from `req.body` into the comparison and the SQL.
   **Breaks when:**
   - `amount: -5000` passes `balance < -5000`. The route then adds 5000 to `fromId` and takes 5000 from `toId`, which pulls money out of any account.
   - A missing `amount` passes the check (`x < undefined` is false). Both UPDATEs then run `balance_cents ± NULL`, which wipes both balances to NULL unless the column is `NOT NULL`.
   - `0.5` or `"abc"` gets through and errors in Postgres. That error then crashes the server, as in #4.

   **Fix:** reject the request with 400 unless `Number.isSafeInteger(amount) && amount > 0`. Also reject `fromId === toId`.

3. **Transfer is not atomic and the balance check is racy**: `src/routes/transfers.js:23-29`
   The route runs a read, a check, a debit and a credit as three separate pool queries. CONTRIBUTING says *"Multi-statement writes must use `db.withTransaction()`; never issue dependent UPDATEs separately."*. `db.js:9-12` documents `withTransaction` together with `SELECT … FOR UPDATE`.
   **Breaks when:**
   - Two concurrent transfers of the full balance both read the old balance and both pass, so the account goes overdrawn.
   - `toId` doesn't exist: the credit UPDATE matches 0 rows, the debit stays, the money disappears, and the response says `ok: true`.
   - The credit query fails for any reason after the debit has already been committed.

   **Fix:**
   ```js
   await db.withTransaction(async (client) => {
     const { rows } = await client.query("SELECT * FROM accounts WHERE id = $1 FOR UPDATE", [fromId]);
     // ownership + balance checks on rows[0]
     await client.query("UPDATE accounts SET balance_cents = balance_cents - $1 WHERE id = $2", [amount, fromId]);
     const credit = await client.query("UPDATE accounts SET balance_cents = balance_cents + $1 WHERE id = $2", [amount, toId]);
     if (credit.rowCount !== 1) throw new Error("destination not found"); // rolls back
     // audit_log insert here too, awaited
   });
   ```
   To rule out deadlocks between opposite-direction transfers, lock both rows in a consistent order, for example by id.

4. **Async handler with no error handling, so one bad id can crash the server**: `src/routes/transfers.js:20-24`
   There is no not-found check and no `try/catch` → `next(err)`, unlike every handler in `accounts.js`. Express 4 (`^4.21.1`) doesn't catch rejected promises from async handlers.
   **Breaks when:** a request has a nonexistent or missing `fromId`. `from.rows[0]` is undefined and `.balance_cents` throws. The request hangs, and on Node 15 or later the unhandled rejection exits the process unless something installs a handler (nothing in this repo does). Any DB error on this route has the same effect.
   **Fix:** wrap the body in `try { … } catch (err) { next(err); }` and return 404 when the account isn't found. The ownership helper from #1 covers the not-found part.

5. **Missing `csrfProtection` on a state-changing route**: `src/routes/transfers.js:20`
   CONTRIBUTING: *"Every state-changing route (POST/PUT/PATCH/DELETE) must use the `csrfProtection` middleware."*. The session cookie is `sameSite=none` (`session.js:1-2`), so browsers send it on cross-site requests.
   **Breaks when:** a third-party page posts to `/transfers` while the victim is logged in. Today `express.json()` won't parse a cross-site form body, so this can't move money yet. It does reach the handler with `req.body = {}` and triggers the crash in #4. If anyone later adds a urlencoded parser, it becomes a full cross-site transfer.
   **Fix:** `router.post("/transfers", csrfProtection, async (req, res, next) => { … })`, the same pattern as `accounts.js:32`.

### 🟡 Should fix

6. **The `proc` helper is hard to follow, and its audit insert is fire-and-forget**: `src/routes/transfers.js:7-18, 31`
   - The names `r`, `u`, `d` and `flag` say nothing about what they hold.
   - The only caller passes `flag = true`, so the `{ ok: true }` branch is dead code.
   - The `audit_log` INSERT isn't awaited, so the client gets `ok` before the audit row exists.
   - It stores the raw, unvalidated `req.body`.

   **Breaks when:** the audit insert fails. The audit row is silently lost and the unhandled rejection can take the process down, as in #4.
   **Fix:** inline the insert into the transaction from #3, awaited, and store only the validated `{fromId, toId, amount}`. Then delete `proc`.

7. **Unrelated changes are mixed in**: `src/utils/format.js`, `package.json`
   - The `format.js` diff is a reformat only: 4-space indent, single quotes and no semicolons, which no other file in the repo uses.
   - `express` is bumped from `^4.19.2` to `^4.21.1`.
   - `lodash` is added but never `require`d anywhere.

   CONTRIBUTING: *"Keep PRs focused on one change. Don't mix refactors/reformatting with features."*.
   **Fix:** revert the `format.js` reformat and drop `lodash`. If you want the express bump, put it in its own PR.

8. **No tests for the transfer route**
   `test/` only has `format.test.js`, and `supertest` is already a devDependency. For money movement, cover at least these cases:
   - a happy-path transfer;
   - insufficient funds → 400;
   - another user's `fromId` → 403;
   - a negative, zero or non-integer amount → 400;
   - an unknown `toId` → error with both balances unchanged;
   - a missing CSRF token → 403.

9. **The PR title, description and commits don't meet CONTRIBUTING**
   The title "updates" doesn't say what changed, and the description is empty, but the repo requires *"what, why, and how it was tested"*. The commits `wip`, `fix` and `more fixes` break the commit-message rule. Squash them into something like "Add transfer endpoint" and fill in the description.

### Scorecard
| Area | | Note |
|---|---|---|
| Correctness | ❌ | Non-atomic, racy, unvalidated amount, crashes on bad id |
| Security | ❌ | IDOR on fromId; CSRF middleware missing |
| Testing | ⚠️ | No tests for the new route |
| Readability | ⚠️ | Opaque `proc(r, u, d, flag)` helper |
| Performance | ✅ | |
| Conventions | ❌ | Breaks 4 CONTRIBUTING safety rules; off-style reformat |
| PR quality | ⚠️ | Unfocused, no description, "wip"/"fix" commits |

**Checked:** I ran `node --test test/` and both existing format tests pass. Lint wasn't run because `node_modules` isn't installed. There's no CI for a local branch. · **Not reviewed:** nothing skipped. The PR is small (about 45 lines).
**Good:** all the SQL is parameterized (`$1`, `$2`), so there's no injection risk in the new queries.
