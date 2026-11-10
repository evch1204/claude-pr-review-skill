## Code review

**`feature/order-search` → `main`**: Order search, discount codes, and Stripe charging (3 commits, 6 files, +86/−1)

I found 5 issues. I checked the first four by running the branch code against an in-memory SQLite database. The fifth, a live Stripe key committed to the code, is plain from reading it.

1. **SQL injection in order search.** `app/orders.py:11-15`
   `search_orders` builds the query with an f-string: `f"WHERE customer_name LIKE '%{customer_name}%' "`. The `q` value comes straight from the query string. Searching `zzz' OR 1=1 --` returned all 25 rows instead of none. The same code also breaks on ordinary names: searching `O'Brien` raises `sqlite3.OperationalError`. The README's conventions forbid this ("All SQL must use parameter binding (`?` placeholders). Never build SQL with string formatting."). Fix: use `WHERE customer_name LIKE ? ... LIMIT ? OFFSET ?` and bind `(f"%{customer_name}%", page_size, offset)`.

2. **Page 1 skips the first page of results.** `app/orders.py:10`
   The docstring and the PR say `page` is 1-indexed, but the code computes `offset = page * page_size`. The handler defaults to `page=1`, so the first request starts at row 21. With 25 matching orders, page 1 returned ids 21–25, and ids 1–20 can't be reached. Fix: `offset = (page - 1) * page_size`.

3. **An unknown discount code crashes the order detail endpoint.** `app/orders.py:23-24`
   The docstring says "Unknown codes are ignored", but `DISCOUNTS.get(code.upper())` returns `None` for a code that isn't in the table. The next line then does `order_total * None`. `apply_discount(100.0, "BOGUS")` raises `TypeError`, so `GET` order detail with any mistyped `?code=` gives a 500 instead of the full total. Fix: `if pct is None: return order_total`.

4. **Order detail crashes when the customer no longer exists.** `app/orders.py:34-35`
   `get_user` returns `None` when the user is missing; its docstring says "e.g. deleted accounts". `customer["email"]` then raises `TypeError: 'NoneType' object is not subscriptable`. Any order whose customer was deleted now returns a 500 from `handle_get_order`. Fix: guard against `None`, for example `order["customer_email"] = customer["email"] if customer else None`.

5. **A live Stripe secret key is committed.** `app/payments.py:4`
   `STRIPE_API_KEY = "sk_live_51NfQ2b..."` is a hardcoded live secret key. This goes against the PR's own aim of moving secrets to env vars and the README convention "Secrets come from environment variables via `app/config.py`". The key is now in git history on this branch, so removing it from the file is not enough: **rotate the key in Stripe** and load it from an env var through `app/config.py`.

---

Notes:
- The repository has no `CLAUDE.md` files, so there was nothing to check for CLAUDE.md compliance. Issues 1 and 5 also break conventions written in `README.md`.
- These fell below the bar for findings and were left out of the list:
  - `SECRET_KEY` defaults to `""` when the env var is unset.
  - `charge()` does not URL-encode its form body.
  - `int(params["page"])` fails on input that isn't a number.
  - `app/orders.py` and `app/payments.py` have no tests; the README asks for tests for every new module.
- The PR's testing ("searched for a few customers") would not have caught issues 2–4. Each one shows up on page 1 of a search, a wrong discount code, or a deleted customer.
