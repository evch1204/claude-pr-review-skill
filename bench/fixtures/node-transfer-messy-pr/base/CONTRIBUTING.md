# Contributing

- Money is always integer cents (`*_cents` columns). Validate amounts at the route boundary.
- Every route that touches an account must check `account.owner_id === req.user.id` (see `routes/accounts.js`).
- Every state-changing route (POST/PUT/PATCH/DELETE) must use the `csrfProtection` middleware.
- Multi-statement writes must use `db.withTransaction()`; never issue dependent UPDATEs separately.
- Keep PRs focused on one change. Don't mix refactors/reformatting with features.
- Commit messages: imperative mood, describe the change ("Add transfer endpoint"), no "wip"/"fix" one-worders.
- PR descriptions must explain what, why, and how it was tested.
