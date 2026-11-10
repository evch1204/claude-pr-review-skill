# Review: `feature/order-search` → `main`

**Verdict: Don't merge yet.** There's a live Stripe secret key in the code and a SQL injection in the new search endpoint. Pagination and discount codes also have bugs that break normal use. The details are below. I checked each bug against an in-memory SQLite database. The existing test suite passes (3 tests), but none of those tests cover the new code.

---

## Blockers

### 1. A live Stripe secret key is committed (`app/payments.py:4`)
```python
STRIPE_API_KEY = "sk_live_51NfQ2bKx9TzL4mVq8rWj3HyPc7sDe2Ag"
```
- This is a **live** secret key. It's now in commit `1a7f7ee`, so deleting the line in a later commit won't remove it. It stays in history for anyone who has the branch.
- **Action:** rotate the key in the Stripe dashboard now. If this branch was ever pushed or shared, treat the key as compromised. Then rewrite or squash the branch so the key is gone from history before merging.
- **Fix:** read it the way the README says secrets should be read, through `app/config.py`. For example, `STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY")` in config. `charge()` should fail with a clear error when the key isn't set.
- The PR description says it's moving secrets *out* of code, but this commit adds one *into* code.

### 2. SQL injection in `search_orders` (`app/orders.py:10-15`)
The `q` value from the query string is pasted straight into the SQL with an f-string:
```python
f"WHERE customer_name LIKE '%{customer_name}%' "
```
I confirmed both problems:
- `q = x%' UNION SELECT id, 0, email, 0 FROM users --` returns user emails from the `users` table. Anyone who can call the endpoint can read any table.
- `q = O'Brien` raises `sqlite3.OperationalError`, so searching for an ordinary customer name with an apostrophe returns a 500 error.

This also breaks the README rule: "All SQL must use parameter binding." Fix:
```python
offset = (page - 1) * page_size
rows = conn.execute(
    "SELECT id, customer_id, customer_name, total FROM orders "
    "WHERE customer_name LIKE ? ORDER BY id LIMIT ? OFFSET ?",
    (f"%{customer_name}%", page_size, offset),
)
```
You may also want to escape `%` and `_` in the search text (with `ESCAPE '\'`) so they match literally.

### 3. Pages are off by one, so the first page is always skipped (`app/orders.py:10`)
The docstring and the README both say pages are 1-indexed, but the code computes `offset = page * page_size`. With 25 matching orders:
- `page=1` (the default) returns ids 21–25 instead of 1–20.
- `page=2` returns nothing.

So the default request never shows the first 20 results. This is probably why it looked fine in manual testing with only a few results. The fix is `(page - 1) * page_size`. Also reject `page < 1`: SQLite treats a negative offset as 0, but Postgres (which prod uses, per the README) returns an error. A non-numeric `page` currently causes an unhandled `ValueError` in `handle_search_orders`, which should be a 400.

### 4. An unknown discount code crashes the order endpoint (`app/orders.py:23-24`)
The docstring says "Unknown codes are ignored", but `DISCOUNTS.get(code.upper())` returns `None` for an unknown code. The next line then raises `TypeError: unsupported operand type(s) for *: 'float' and 'NoneType'`. So `GET /orders/<id>?code=TYPO` returns a 500. Fix:
```python
pct = DISCOUNTS.get(code.upper())
if pct is None:
    return order_total
```

---

## Should fix

### 5. `charge()` can't distinguish "declined" from "we don't know" (`app/payments.py:16-17`)
`except Exception: return False` treats a timeout or network error the same as a declined card. If the request times out *after* Stripe has accepted the charge, the caller sees `False` and will probably retry, which charges the customer twice. Suggestions:
- Send an `Idempotency-Key` header, built from the order id, so retries are safe.
- Let network and timeout errors raise, or return a distinct status, instead of folding them into `False`. Catch `urllib.error.HTTPError` specifically for Stripe's 4xx responses.
- Build the request body with `urllib.parse.urlencode(...)` rather than an f-string, so `customer_token` is encoded properly.
- Note that `/v1/charges` and `source=` are Stripe's legacy Charges API. Check that this is intentional rather than PaymentIntents.

### 6. Order detail crashes if the customer row is missing (`app/orders.py:35-36`)
`get_user` returns `None` for a deleted or missing customer, and then `customer["email"]` raises `TypeError` (I confirmed this). Either handle `None` (for example, `customer_email: None`) or use a single `JOIN` query, which also saves a round trip.

### 7. No tests for any of the new code
The README says "Every new module needs tests in `tests/`." `orders.py` and `payments.py` have none. The only new test is for `list_users`, which isn't related to this feature. Each bug above (pagination, the unknown code, the apostrophe and injection, the missing customer) would have been caught by a short unit test using the same in-memory `make_conn()` pattern as `tests/test_users.py`. For `charge()`, a test that mocks `urllib.request.urlopen` would cover success, decline and timeout.

### 8. The session-secret change doesn't match the description (`app/config.py`)
- The description says this PR "moves the session secret to an env var", but there was no hard-coded session secret in `main`, and nothing reads `config.SECRET_KEY`. As it stands this is an unused constant.
- If something does start using it, the `""` default is risky: a missing env var silently becomes an empty signing key. Prefer failing at startup when the variable is unset, at least outside dev.

---

## Minor / questions
- **Exposed data:** `GET /orders/search` with an empty `q` lists every order. Order detail returns `customer_email`. These handlers have no auth check. That may be fine for an internal service, but confirm it's intended now that the endpoints return customer PII.
- **Money as floats:** totals and discounts use `float` with `round(..., 2)`. Since this now feeds `charge(amount_cents)`, consider keeping amounts in integer cents (or `Decimal`) from start to finish.
- **Hard-coded discount codes:** `DISCOUNTS` lives in code, so changing a code means a deploy. That's fine for now, but a table or config would be easier to manage.
- **Unrelated change:** `list_users` and its test are unrelated to orders. It's harmless, but it would be cleaner as a separate PR or at least mentioned in the description.
- **Open connections:** the handlers call `get_conn()` and never close the connection. This already happened in `handle_get_user`, but the PR adds two more places that do it.

---

## Summary checklist before merge
- [ ] Rotate the Stripe key, load it from env through `config.py`, and remove it from branch history
- [ ] Parameterize the search query
- [ ] Use `offset = (page - 1) * page_size` and validate `page`
- [ ] Ignore unknown discount codes instead of crashing
- [ ] Make `charge()` safe to retry (idempotency key, no blanket `except`)
- [ ] Handle a missing customer in order detail
- [ ] Add tests for `orders.py` and `payments.py`
- [ ] Fix the PR description, or wire up `SECRET_KEY`
