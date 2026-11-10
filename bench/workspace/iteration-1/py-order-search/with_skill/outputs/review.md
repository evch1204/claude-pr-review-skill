## PR Review: Order search, discount codes, and Stripe charging

**Verdict: ❌ Request changes**: there are four blocking problems. The search query can be injected with SQL, a live Stripe secret key is committed, page 1 of search always skips the first 20 results, and an unknown discount code crashes the order endpoint.

This PR adds a paginated customer-name search over orders, discount codes on the order detail endpoint, a Stripe `charge()` helper that nothing calls yet, a `SECRET_KEY` read from an env var, and an unrelated `list_users` helper with a test. I ran the new functions against an in-memory SQLite DB, and every 🔴 below reproduced.

### 🔴 Blocking
1. **SQL injection in order search**: `app/orders.py:11-15`
   The `q` parameter goes straight into the SQL through f-strings. The README forbids this: *"All SQL must use parameter binding (`?` placeholders). Never build SQL with string formatting."*
   **Breaks when:** `q=zzz' UNION SELECT id, name, email, 0 FROM users --` returns every user's email through the search endpoint (reproduced). A real customer name with an apostrophe, such as `q=O'Brien`, raises `OperationalError`, so the endpoint returns a 500.
   **Fix:**
   ```python
   query = ("SELECT id, customer_id, customer_name, total FROM orders "
            "WHERE customer_name LIKE ? ORDER BY id LIMIT ? OFFSET ?")
   rows = conn.execute(query, (f"%{customer_name}%", page_size, offset)).fetchall()
   ```
   (Optionally escape `%` and `_` in `customer_name` with `ESCAPE '\'` so they match literally.)

2. **Live Stripe secret key committed**: `app/payments.py:4`
   `STRIPE_API_KEY = "sk_live_..."` is hard-coded. That breaks *"Secrets come from environment variables via `app/config.py`"*, and the key is now in this branch's history (commit `1a7f7ee`).
   **Breaks when:** anyone who can read the repo can create charges and refunds on the live Stripe account.
   **Fix:** **rotate the key in Stripe now**. Deleting the line doesn't help, because the key stays in git history. Then read it in `config.py` (e.g. `STRIPE_API_KEY = os.environ["STRIPE_API_KEY"]`), and rewrite or squash the branch history before merging so the key never reaches `main`.

3. **Pagination off by one: page 1 skips the first page**: `app/orders.py:10`
   The docstring and the README both say pages are 1-indexed, but `offset = page * page_size` treats them as 0-indexed. `handle_search_orders` defaults to `page=1`.
   **Breaks when:** any search with 20 or fewer matches returns `[]`. With 5 matching orders, `search_orders(conn, "Ada", 1)` returned `[]` (reproduced). Larger result sets silently lose their first 20 rows.
   **Fix:** `offset = (page - 1) * page_size`, and reject `page < 1` (see 🟡 3).

4. **Unknown discount code crashes the order endpoint**: `app/orders.py:23-24`
   The docstring promises "Unknown codes are ignored", but `DISCOUNTS.get(...)` returns `None` and `order_total * None` raises.
   **Breaks when:** `GET` order detail with `code=BOGUS` (or any typo) raises `TypeError` and the endpoint returns a 500 (reproduced).
   **Fix:**
   ```python
   pct = DISCOUNTS.get(code.upper())
   if pct is None:
       return order_total
   ```

### 🟡 Should fix
1. **Order detail crashes when the customer was deleted**: `app/orders.py:34-35`
   `get_user` documents that it returns `None` "e.g. deleted accounts", but `customer["email"]` is read without a check.
   **Breaks when:** an order belongs to a deleted user. You get `TypeError: 'NoneType' object is not subscriptable` and a 500 (reproduced).
   **Fix:** `order["customer_email"] = customer["email"] if customer else None`, or a single JOIN query.

2. **`charge()` can double-charge on retry**: `app/payments.py:13-17`
   `except Exception: return False` handles a decline, a network error, and a read timeout the same way, and the request sends no `Idempotency-Key`.
   **Breaks when:** Stripe accepts the charge but the response times out. `charge()` returns `False`, the caller reasonably retries, and the customer is charged twice. Nothing calls `charge()` yet, so fix this before anything does.
   **Fix:** send an `Idempotency-Key` header supplied by the caller (e.g. the order ID). Let network errors raise, or return a result that tells "declined" apart from "unknown". Build the body with `urllib.parse.urlencode` rather than an f-string.

3. **`page` isn't validated**: `app/api.py:17`
   **Breaks when:** `page=abc` raises `ValueError` and returns a 500. `page=0` or `page=-3` is accepted, and once 🔴 3 is fixed it produces a negative offset.
   **Fix:** parse inside a try and return `{"status": 400}` for non-integers or `page < 1`.

4. **Search is case-sensitive in production**: `app/orders.py:13`
   The README says *"SQLite in dev, Postgres in prod."* SQLite's `LIKE` ignores case for ASCII, but Postgres's doesn't.
   **Breaks when:** searching `q=ada` finds "Ada" locally and nothing in prod. That's likely why local manual testing looked fine.
   **Fix:** `WHERE LOWER(customer_name) LIKE LOWER(?)` works on both databases.

5. **No tests for the new modules**: `app/orders.py`, `app/payments.py`
   The README says *"Every new module needs tests in `tests/`"*. The only test added is for `list_users`. A three-line test of `search_orders(..., page=1)` or `apply_discount(100, "BOGUS")` would have caught 🔴 3 and 🔴 4.
   **Fix:** add `tests/test_orders.py` covering page 1 and page 2, a quote in `q`, unknown, lowercase and missing discount codes, and a deleted customer. Add `tests/test_payments.py` with `urlopen` mocked to cover success, a decline and a timeout.

### ⚪ Nits
- `app/orders.py:19`: money is handled as `float` with `round(..., 2)`. Integer cents (or `Decimal`) would match `charge(amount_cents: int)` and avoid rounding drift.
- `app/users.py:12` and `tests/test_users.py`: `list_users` has nothing to do with this PR, and it's bundled into a commit titled "Read session secret from env". Split it out, or at least mention it in the description.
- `app/orders.py:3`: `search_orders` filters on a denormalized `orders.customer_name`, while `get_order_with_customer` looks up `users`. Worth confirming the two can't drift apart (e.g. after a user renames).

### ❓ Questions
- The description says this PR "moves the session secret to an env var", but `main` had no secret in code and nothing reads `config.SECRET_KEY`. What is it for? If a session signer is coming, `os.environ.get(..., "")` will silently sign with an empty key when the var is unset. Failing fast with `os.environ[SECRET_KEY_ENV_VAR]` would be safer.
- With the default `page=1`, every search with 20 or fewer matches returns an empty list. Did the manual search testing go through this endpoint, or call the DB directly?

### Scorecard
| Area | | Note |
|---|---|---|
| Correctness | ❌ | Off-by-one paging; unknown code and deleted customer both 500 |
| Security | ❌ | SQL injection; live Stripe key committed |
| Testing | ⚠️ | No tests for orders or payments, against repo rule |
| Readability | ✅ | |
| Performance | ✅ | Paged and bounded |
| Conventions | ❌ | Breaks the README's SQL-binding and secrets rules |
| PR quality | ⚠️ | Unrelated `list_users`; description overstates the secret change |

**Checked:** `pytest` passes (3 tests, all for users). Ran `search_orders`, `apply_discount` and `get_order_with_customer` against an in-memory SQLite DB to reproduce 🔴 1, 3, 4 and 🟡 1, 3. A fresh-eyes verifier pass confirmed every finding. The Postgres `LIKE` behaviour is from its documentation, not run. · **Not reviewed:** nothing skipped (86 changed lines).
**Good:** `get_order_with_customer` and `list_users` use bound parameters correctly, and the new handlers follow the existing thin-handler shape in `api.py`.
