# orders-service

Small internal service for looking up customers and orders. SQLite in dev, Postgres in prod.

## Conventions
- All SQL must use parameter binding (`?` placeholders). Never build SQL with string formatting.
- Secrets come from environment variables via `app/config.py`.
- Every new module needs tests in `tests/`.
- Page numbers in the public API are 1-indexed.
