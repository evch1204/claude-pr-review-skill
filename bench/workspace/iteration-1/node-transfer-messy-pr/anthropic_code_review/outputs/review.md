## Code review: `transfers` → `main` ("updates")

Don't merge this yet. The new `POST /transfers` endpoint has several serious problems in money handling and security.

Scope: 3 commits (`wip`, `fix`, `more fixes`), 4 files. The PR adds `src/routes/transfers.js`, mounts it in `src/app.js`, bumps `express`, adds `lodash` and reformats `src/utils/format.js`.

There is no CLAUDE.md in the repo, so I checked the change against `CONTRIBUTING.md`, the repo's rules file.

### Issues found

**1. Any logged-in user can move money out of any account.** (security; `src/routes/transfers.js` L20-31)
`fromId` and `toId` come straight from `req.body`, and nothing checks `account.owner_id === req.user.id`. `req.user.id` is only written to the audit log. A user can send `{ fromId: <someone else's account>, toId: <their own>, amount: N }` and take the money. This also breaks the CONTRIBUTING rule: *"Every route that touches an account must check `account.owner_id === req.user.id`"*. The `loadOwnedAccount` pattern in `routes/accounts.js` already does this check.

**2. The amount is never checked, so a negative amount reverses the transfer.** (security/bug; L21-29)
With `amount = -50000` the funds check `balance_cents < -50000` is false, so it passes. The two UPDATEs then add 50000 to `fromId` and take 50000 from `toId`, and `toId`'s balance is never checked. Together with #1, any user can drain any account into their own. CONTRIBUTING says: *"Validate amounts at the route boundary."* The route should require a positive integer number of cents.

**3. The check and the two balance updates are not in a transaction.** (bug; L23-29)
- **Race:** the balance is read without `FOR UPDATE`, so two transfers sent at the same time can both pass the funds check and overdraw the account.
- **Partial write:** if the credit UPDATE fails after the debit succeeds, the money is gone.
- **Missing target account:** a `toId` that doesn't exist makes the credit UPDATE change 0 rows. The source is still debited, the money disappears, and the response still says `ok: true`.

This breaks the CONTRIBUTING rule *"Multi-statement writes must use `db.withTransaction()`; never issue dependent UPDATEs separately."* `db.withTransaction` already exists, and its comment says to use `SELECT ... FOR UPDATE` inside it.

**4. A bad `fromId` can crash the server process.** (bug; L23-24)
If `fromId` doesn't match any account, or the body is empty, `from.rows[0]` is `undefined` and `.balance_cents` throws inside the `async` handler. Express 4 (still `^4.21.x` here) does not catch rejected promises from handlers. The request hangs, and Node's default handling of unhandled promise rejections ends the process. Any logged-in user can bring the API down with one request. The handler needs a 404 for a missing account and the `try/catch` + `next(err)` pattern that `routes/accounts.js` uses.

The audit-log `db.query(...)` in `proc()` (L11) has the same problem: it is not awaited, so if it fails it also becomes an unhandled rejection. The response also returns a `transferId` even when the audit row was never written.

**5. No CSRF protection on a route that changes data.** (CONTRIBUTING; L20)
The rule is *"Every state-changing route (POST/PUT/PATCH/DELETE) must use the `csrfProtection` middleware."* `router.post("/transfers", ...)` does not use it. `src/session.js` notes that the session cookie is `sameSite=none`, so the browser does not block cross-site requests on its own.

### Smaller CONTRIBUTING violations
- **Reformatting mixed into a feature PR:** the `src/utils/format.js` diff only changes formatting (4-space indent, no semicolons, single quotes) and now looks different from the rest of the codebase. The rule is *"Don't mix refactors/reformatting with features."* Drop it from this PR.
- **Unrelated dependency changes:** `lodash` is added to `package.json` but nothing imports it. The `express` bump has nothing to do with transfers.
- **Commit messages and PR description:** the commits are named `wip`, `fix` and `more fixes`, the title is "updates" and the description is empty. CONTRIBUTING asks for imperative commit messages ("no 'wip'/'fix' one-worders") and a PR description that explains what, why and how the change was tested. No tests were added for the new endpoint.

### Suggested shape for the handler
Validate that `amount` is a positive integer. Then inside `db.withTransaction(client => ...)`:
- `SELECT ... FOR UPDATE` both accounts, ordered by id to avoid deadlocks.
- Return 404 if either account is missing and 403 if `from.owner_id !== req.user.id`.
- Check the balance, run both UPDATEs and insert the audit row, all on `client`.

Also add `csrfProtection` to the route and wrap the handler in `try/catch` → `next(err)`.
