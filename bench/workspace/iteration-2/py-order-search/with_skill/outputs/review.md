## PR Review: Order search, discount codes, and Stripe charging

**Verdict: ❌ Request changes**: the search query can be injected, a live Stripe secret key is committed, page 1 of search is always empty, and an unknown discount code crashes the order endpoint.

The PR adds `handle_search_orders` (customer-name search, 20 per page), discount codes on `handle_get_order` (which now also returns the customer's email), a `charge()` helper that POSTs to Stripe, and a `SECRET_KEY` read from `ORDERS_SECRET_KEY`. It also adds an unmentioned `list_users()` plus a test for it.

### 🔴 Blocking
1. **SQL injection in order search**: `app/orders.py:11-15`
   `q` goes straight from the query string into the SQL through an f-string. The README says: *"All SQL must use parameter binding (`?` placeholders). Never build SQL with string formatting."*
   **Breaks when:** `q=x' UNION SELECT id,name,email,0 FROM users --` returns every user's name and email. I ran this against an in-memory DB and it returned the `users` rows. The `--` also comments out the `LIMIT`, so pagination doesn't limit it. The same input could reach any table.
   **Fix:**
   ```python
   query = (
       "SELECT id, customer_id, customer_name, total FROM orders "
       "WHERE customer_name LIKE ? ORDER BY id LIMIT ? OFFSET ?"
   )
   rows = conn.execute(query, (f"%{customer_name}%", page_size, offset)).fetchall()
   ```
   (Also escape `%`/`_` in `customer_name` with `ESCAPE '\'` if a literal `%` search should match only a literal `%`.)

2. **Live Stripe secret key committed to source**: `app/payments.py:4`
   `STRIPE_API_KEY = "sk_live_..."` is a production secret key in code. The README says: *"Secrets come from environment variables via `app/config.py`."*
   **Breaks when:** anyone with read access to the repo, a clone, a CI log, or a backup can create charges and refunds on the live Stripe account. The key is already in the history of commit `1a7f7ee`, so deleting the line won't remove it.
   **Fix:** **Rotate the key in the Stripe dashboard now**, whether or not this PR merges. Then read it in `app/config.py` (`STRIPE_API_KEY = os.environ["STRIPE_API_KEY"]`) and rewrite the branch so the key never lands on `main`.

3. **Pagination skips the first page**: `app/orders.py:10`
   The docstring and the README say pages are 1-indexed, but `offset = page * page_size` treats them as 0-indexed.
   **Breaks when:** `page=1` (the default) gives `OFFSET 20`, so the first 20 matches never show. A customer with 20 or fewer orders gets `[]`, which looks like "no orders found". I confirmed this: 5 matching orders, `page=1` → `[]`.
   **Fix:** `offset = (page - 1) * page_size`. In `handle_search_orders`, reject `page < 1` and non-numeric `page` with a 400 (at the moment `int("abc")` raises and gives a 500).

4. **Unknown discount code crashes the order endpoint**: `app/orders.py:23-24`
   The docstring says *"Unknown codes are ignored"*, but `DISCOUNTS.get(code.upper())` returns `None` for them, and `order_total * None / 100` raises `TypeError`.
   **Breaks when:** `GET /orders?id=1&code=WELCOM10` (any typo or expired code) → 500 instead of the undiscounted total. Reproduced: `apply_discount(100.0, "BOGUS")` → `TypeError`.
   **Fix:**
   ```python
   pct = DISCOUNTS.get(code.upper())
   if pct is None:
       return order_total
   ```
   (Or return a 400 saying the code is invalid, if the client should tell the user. Either way, decide on purpose.)

### 🟡 Should fix
1. **Order detail crashes when the customer was deleted**: `app/orders.py:34-35`
   `get_user` documents that it returns `None` *"if no such user exists (e.g. deleted accounts)"*. `customer["email"]` then raises.
   **Breaks when:** someone opens an order whose customer account was deleted → `TypeError` → 500. Reproduced with an order pointing at a missing user.
   **Fix:** `order["customer_email"] = customer["email"] if customer else None`.

2. **`charge()` turns every failure into `False`, which invites double charges**: `app/payments.py:13-17`
   `except Exception: return False` makes "card declined", "bad key", and "network timed out after Stripe already charged" look the same. No idempotency key is sent.
   **Breaks when:** Stripe takes the charge but the response times out (10s) → `charge()` returns `False` → the caller reasonably retries → the customer is charged twice. Errors also leave no log or trace.
   **Fix:** send an `Idempotency-Key` header that the caller passes in (for example the order id). Let timeouts and other transport errors raise, or return a status other than `False`, so callers can tell "declined" apart from "unknown". Use `urllib.parse.urlencode` for the body rather than an f-string. Nothing calls `charge()` yet, so this is the cheapest time to get the contract right.

3. **No tests for the new modules**: `tests/`
   The README says: *"Every new module needs tests in `tests/`."* `orders.py` and `payments.py` have none. The only new test is for `list_users`, which the PR description doesn't mention. Basic tests would have caught blocking #3 and #4 and should-fix #1. "Searched for a few customers locally" won't stop these from coming back.
   **Fix:** in-memory SQLite tests for `search_orders` (page 1 returns the first rows; a quote in `q` is treated as text), `apply_discount` (known, lowercase, unknown, empty code), and `get_order_with_customer` (missing customer). Also a `charge()` test with `urlopen` mocked.

### ⚪ Nits
- `app/orders.py:19`: money as `float` with `round()`. Totals like `19.99` will pick up float error. `charge()` already uses integer cents, so storing and returning cents (or `Decimal`) would keep the two consistent.
- `app/users.py:12`: `list_users` has no callers and isn't in the PR description. Drop it, or say what it's for.

### ❓ Questions
- The description says this PR *"moves the session secret to an env var"*, but `main` has no hard-coded session secret, and nothing reads `config.SECRET_KEY`. Is there a follow-up that wires it into session signing? When that happens, the `""` default will quietly sign sessions with an empty key if `ORDERS_SECRET_KEY` is unset. Failing at startup (`os.environ["ORDERS_SECRET_KEY"]`) would be safer.
- `handle_get_order` returns `customer_email` for any order id, with no check of who is asking. That matches the existing `handle_get_user`, so I assume this internal service is protected at the network or gateway level. Can you confirm?

### Scorecard
| Area | | Note |
|---|---|---|
| Correctness | ❌ | Page 1 always empty; unknown code → 500 |
| Security | ❌ | SQL injection; live Stripe key committed |
| Testing | ⚠️ | No tests for orders.py or payments.py |
| Readability | ✅ | |
| Performance | ✅ | |
| Conventions | ❌ | Breaks 4 of 4 README conventions |
| PR quality | ⚠️ | Unmentioned `list_users`; description overstates secret move |

**Checked:** `pytest` passes (3 tests, none cover the new code). I reproduced blocking #1, #3 and #4 and should-fix #1 with an in-memory SQLite script. No CI (local branch).
**Good:** `get_order_with_customer` and the new `list_users` use bound parameters correctly. The search function is the only place that drifted.
