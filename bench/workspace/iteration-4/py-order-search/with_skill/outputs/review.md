## PR Review: Order search, discount codes, and Stripe charging

**Verdict: ❌ Request changes**: the search query is open to SQL injection, a live Stripe secret key is committed, and both new endpoints return wrong results or 500s on ordinary input.
The PR adds `GET /orders/search` (paginated customer-name search), discount codes on the order detail endpoint, a Stripe `charge()` helper, and a `SECRET_KEY` setting read from the environment.

### 1. 🔴 Bind the search SQL, fix the page offset, pull the Stripe key from env, and stop the order-detail 500s
Two of these break README rules that exist for safety ("All SQL must use parameter binding… Never build SQL with string formatting", "Secrets come from environment variables via `app/config.py`"). The other three return wrong data or crash on normal requests. I reproduced each one against the branch with an in-memory SQLite DB.
**Breaks when:** someone calls `/orders/search?q=' UNION SELECT id,name,email,0 FROM users --` and gets back every user's name and email (confirmed). Any SQL that can be put in `q` runs against the orders DB, which is Postgres in prod.
- `app/orders.py:13-14`: `q` is f-stringed into the `LIKE` clause → SQL injection, against the repo's binding rule.
- `app/orders.py:10`: `offset = page * page_size` with 1-indexed pages → `page=1` (the default) skips the first 20 matches. With 25 matching orders, page 1 returned ids 21–25, and a search with fewer than 21 matches comes back empty. Customers will read that as "no orders".
- `app/payments.py:4`: a hard-coded `sk_live_…` Stripe secret. It's also in history (commit `1a7f7ee`), so removing the line isn't enough: **revoke and rotate the key in Stripe now**, whether or not this merges.
- `app/orders.py:23-24`: an unknown code makes `DISCOUNTS.get()` return `None` → `TypeError`. `GET /orders?id=1&code=TYPO` returns a 500 even though the docstring says unknown codes are ignored.
- `app/orders.py:34-35`: `get_user` returns `None` for deleted accounts (its own docstring says so) → `customer["email"]` raises a `TypeError`, so the detail view of any order whose customer was deleted returns a 500.

**Fix:**
```python
offset = (page - 1) * page_size   # and reject page < 1 with a 400
query = ("SELECT id, customer_id, customer_name, total FROM orders "
         "WHERE customer_name LIKE ? ORDER BY id LIMIT ? OFFSET ?")
conn.execute(query, (f"%{customer_name}%", page_size, offset))
```
Read the key in `config.py` (`STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY")`) and fail loudly if it's unset. In `apply_discount`, return `order_total` when `pct is None`. In `get_order_with_customer`, use `customer["email"] if customer else None`.

### 2. 🟡 Add tests for the new modules, make `charge()` failures distinguishable, and tighten the PR scope
- `tests/`: `app/orders.py` and `app/payments.py` have no tests, but the README says "Every new module needs tests in `tests/`". Page-1 results, an unknown code and a deleted customer are each a single-assert test that would have caught the bugs in comment 1.
- `app/payments.py:13-17`: `except Exception: return False` makes a timeout, a 5xx and a bad key all look like "card declined". If Stripe charged the card but the response timed out, a caller that retries charges the customer twice. Let network/auth errors raise, and send an `Idempotency-Key` header.
- `app/config.py:5-7`: the description says this "moves the session secret to an env var", but `main` had no secret and nothing reads `SECRET_KEY`. If it's meant to be wired up, don't default to `""`: an unset env var would then silently sign sessions with an empty key.
- PR description: "searched for a few customers" locally wouldn't catch the page-1 offset bug. Please say how the discount and charge paths were tested, and mention the new `list_users` helper (`app/users.py:12`), which nothing calls yet.

**Fix:** add `tests/test_orders.py` (search pagination and injection-safe input, discount edge cases, a missing customer) and `tests/test_payments.py` (mock `urlopen`). Narrow the `except` in `charge()`, and update the description to match what's actually in the PR.
Optional: once `q` is bound, `%` and `_` in a search term still act as wildcards. Escape them if you want literal matching.

**Scorecard:** Correctness ❌ · Security ❌ · Testing ⚠️ · Readability ✅ · Performance ✅ · Conventions ❌ · PR quality ⚠️
**Checked:** `pytest` passes (3 tests, all in `test_users.py`; none cover the new code). Reproduced the injection, page-1 offset, unknown-code crash and deleted-customer crash with a scratch script on an in-memory SQLite DB. Ruff isn't installed, so lint wasn't run. There's no CI because this is a local branch.
