# Pull Request Review - Detailed Analysis

## PR Information

**Repository**: orders-service (local, no GitHub remote)
**PR Number**: #N/A (local branch review)
**Title**: Order search, discount codes, and Stripe charging
**Author**: Dev <dev@example.com>
**Branch**: feature/order-search → main
**Size**: 6 files, +86 / -1 across 3 commits (`f7fcadb`, `1a7f7ee`, `af8bb77`)

## Summary

Please don't merge this yet. It adds the order search endpoint, discount codes on order detail, a Stripe `charge()` helper, and a `SECRET_KEY` config entry. Four problems need fixing first:

- A live Stripe secret key is committed in plain text.
- The search query is open to SQL injection.
- Pagination skips the first page of results.
- Any unrecognised discount code crashes the order detail endpoint.

I confirmed the last three by running the new functions against an in-memory SQLite database. The README sets four conventions, and this PR breaks three of them: parameterised SQL only, secrets from env via `app/config.py`, and tests for every new module. It follows the fourth (1-indexed pages) in the docstring only. The code itself is 0-indexed.

The existing test suite passes (3 passed), but it never touches `app/orders.py`, `app/payments.py`, or the new handlers. The PR's testing note ("ran the service locally and searched for a few customers") would not have caught any of the issues below. A manual search will still return results even when the first page is skipped, unless you count rows.

## 🔴 Critical Issues (Blockers)

**These MUST be fixed before merging.**

### 1. Security: Live Stripe secret key hardcoded and committed

**File**: `app/payments.py:4`

**Problem**: `STRIPE_API_KEY = "sk_live_..."` is a production secret key in source code. It is now in git history (commit `1a7f7ee`), so deleting the line in a follow-up commit does not remove it. Anyone with repo access, or any future clone, fork or CI log, can create charges and refunds and read customer payment data. This also breaks the README rule "Secrets come from environment variables via `app/config.py`". The same PR adds `SECRET_KEY` to config the right way, so the two approaches are inconsistent.

**Solution**:
1. Treat the key as compromised and roll it in the Stripe dashboard now, whether or not this PR merges.
2. Read it from config, for example `STRIPE_API_KEY = os.environ["STRIPE_API_KEY"]` in `app/config.py`, and import it in `payments.py`.
3. Rewrite the branch history so the key never reaches `main` (squash or rebase `1a7f7ee` before merging). Never push the current branch to any remote.

**Current Code**:
```
STRIPE_API_KEY = "sk_live_51NfQ2bKx9TzL4mVq8rWj3HyPc7sDe2Ag"
```

---

### 2. Security: SQL injection in order search

**File**: `app/orders.py:13`

**Problem**: `q` comes straight from the query string and is put into the SQL with an f-string. I confirmed this against an in-memory DB:
- `q=zzz' OR 1=1 --` returns every order.
- `q=zzz' UNION SELECT id, name, email, 0 FROM users --` returns user emails through the orders endpoint.
- A real name such as `O'Brien` raises `sqlite3.OperationalError`, which surfaces as a 500.

Prod runs on Postgres, so stacked queries and data changes may also be possible there. This breaks the README's first convention.

**Solution**: Use parameter binding for the pattern, `LIMIT` and `OFFSET`. To match `%` and `_` literally, escape them in the user's input:
```python
pattern = "%" + customer_name.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
conn.execute(
    "SELECT id, customer_id, customer_name, total FROM orders "
    "WHERE customer_name LIKE ? ESCAPE '\\' ORDER BY id LIMIT ? OFFSET ?",
    (pattern, page_size, offset),
)
```

**Current Code**:
```
f"WHERE customer_name LIKE '%{customer_name}%' "
f"ORDER BY id LIMIT {page_size} OFFSET {offset}"
```

---

### 3. Functionality: Off-by-one pagination skips the first page

**File**: `app/orders.py:10`

**Problem**: The docstring and the README say `page` is 1-indexed, but `offset = page * page_size`. With the default `page=1`, the query uses `OFFSET 20`, so results 1 to 20 can never be fetched. Verified: with `page_size=2`, page 1 returned order ids `[3, 4]` instead of `[1, 2]`. Page 0 returns the real first page, which the docs say is not a valid page.

**Solution**: `offset = (page - 1) * page_size`. Reject `page < 1` with a 400 in the handler (see Important #2).

**Current Code**:
```
offset = page * page_size
```

---

### 4. Functionality: Unknown discount code crashes order detail (500)

**File**: `app/orders.py:23`

**Problem**: The docstring says "Unknown codes are ignored", but `DISCOUNTS.get(code.upper())` returns `None`, and `order_total * None / 100` raises `TypeError`. Verified: `apply_discount(100.0, "BOGUS")` gives `TypeError: unsupported operand type(s) for *: 'float' and 'NoneType'`. `handle_get_order` passes `params.get("code")` straight through, so any customer who mistypes a code gets a 500 on the order page.

**Solution**:
```python
pct = DISCOUNTS.get(code.strip().upper())
if pct is None:
    return order_total
```

**Current Code**:
```
pct = DISCOUNTS.get(code.upper())
return round(order_total - order_total * pct / 100, 2)
```

---

## 🟡 Important Issues

**Should be addressed before merging.**

### 1. Functionality: Order detail crashes when the customer was deleted

**File**: `app/orders.py:35`

**Impact**: `get_user` documents that it returns `None` for deleted accounts, but `get_order_with_customer` reads `customer["email"]` with no check. Verified: an order whose `customer_id` has no user row raises `TypeError: 'NoneType' object is not subscriptable`. Every historic order from a deleted account will return a 500.

**Suggestion**: `order["customer_email"] = customer["email"] if customer else None`, or decide on an explicit placeholder. Also consider a single `JOIN` instead of two queries.

**Code**:
```
customer = get_user(conn, order["customer_id"])
order["customer_email"] = customer["email"]
```

---

### 2. Functionality: Handlers don't validate input, so bad input gives a 500 instead of a 400

**File**: `app/api.py:17`

**Impact**:
- `int(params.get("page", 1))` raises `ValueError` on `page=abc`.
- `page=0` and negative pages are accepted silently. SQLite treats a negative offset as 0, so both return data.
- `handle_get_order` raises `KeyError` or `ValueError` when `id` is missing or not numeric.

The existing `handle_get_user` has the same `int(params["id"])` pattern, but the new endpoints are public search inputs and get much more varied traffic.

**Suggestion**: Parse `page` and `id` defensively. Return `{"status": 400}` for non-integers and for `page < 1`. Consider capping `len(q)`.

**Code**:
```
page = int(params.get("page", 1))
```

---

### 3. Testing: No tests for any new module

**File**: `app/orders.py`, `app/payments.py`, `app/api.py`

**Impact**: The README says "Every new module needs tests in `tests/`". The only test added covers `list_users`, which nothing in this PR uses. Basic unit tests would have caught all three functional blockers and Important #1. That includes the first-page case of pagination, an unknown discount code, a quote in the search term, and a deleted customer.

**Suggestion**: Add `tests/test_orders.py` covering:
- Page 1 returns the first rows.
- Page boundaries.
- An empty `q`.
- `q` containing `'`, `%` and `_`.
- Known, unknown, lowercase and empty discount codes.
- An order with a missing customer.

Add `tests/test_payments.py`, with `urllib.request.urlopen` mocked, for the paid, declined and network-error cases.

---

### 4. Functionality: `charge()` hides failures and can double-charge on retry

**File**: `app/payments.py:16`

**Impact**: `except Exception: return False` treats several different outcomes the same way:
- a card decline (HTTP 402)
- a bad or revoked key (401)
- a timeout or network error
- a programming error

A timeout is the dangerous one. The charge may have succeeded at Stripe while the caller sees `False`. If the caller retries, the customer is charged twice, because no `Idempotency-Key` header is sent. Nothing is logged either, so failures can't be diagnosed. The form body is also built by string interpolation without URL-encoding `customer_token`.

**Suggestion**:
- Send an `Idempotency-Key` (for example, derived from the order id).
- Build the body with `urllib.parse.urlencode`.
- Catch `urllib.error.HTTPError` and `URLError` separately. Log them, and return or raise a result that tells "declined" apart from "unknown, do not retry blindly".
- Consider the official `stripe` library, which handles all of this, and PaymentIntents instead of the legacy Charges API.

**Code**:
```
    except Exception:
        return False
```

---

### 5. Security: `SECRET_KEY` silently defaults to an empty string

**File**: `app/config.py:7`

**Impact**: If `ORDERS_SECRET_KEY` is not set in an environment, the service starts with `SECRET_KEY == ""`. Session signing with an empty key amounts to signing with a public, known key. Fail fast instead.

**Suggestion**: `SECRET_KEY = os.environ[SECRET_KEY_ENV_VAR]`, or raise a clear error at startup when it is empty (optionally allowing a dev default only when an explicit dev flag is set).

**Code**:
```
SECRET_KEY = os.environ.get(SECRET_KEY_ENV_VAR, "")
```

---

## 🟢 Minor Issues (Nits)

**Nice to have, but not blocking.**

1. **Scope**: `list_users` and its test are unrelated to order search
   - File: `app/users.py`
   - `list_users` is added in the "order search" commit but nothing in the PR calls it. Move it to its own PR or drop it.

2. **Maintainability**: Discount codes are hardcoded in source
   - File: `app/orders.py`
   - `DISCOUNTS = {"WELCOME10": 10, "VIP25": 25}` means adding or expiring a code needs a deploy. That's fine for now, but a config or DB table is the usual end state. There is also no expiry, usage limit, or per-customer restriction, so anyone can apply `VIP25`.

3. **Correctness**: Money is calculated in floats
   - File: `app/orders.py`
   - `round(total - total * pct / 100, 2)` can produce rounding drift, and `charge()` takes cents. Consider integer cents or `Decimal` throughout, so the displayed `total_after_discount` matches what is charged.

4. **Resource handling**: Connections are never closed
   - File: `app/api.py`
   - Each handler calls `get_conn()` and never closes the connection. This copies the existing `handle_get_user` pattern, but it now happens on a high-traffic search endpoint. Use `with closing(get_conn()) as conn:`.

5. **Commits**: Commit `af8bb77` mixes an unrelated config change with a test for `users.py`
   - File: `app/config.py`, `tests/test_users.py`
   - Splitting these, or squashing the whole branch once the key is removed, would keep history clean.

## 💡 Suggestions for Future

1. Add an index on `orders.customer_name` (or a trigram/full-text index in Postgres). A leading-wildcard `LIKE '%q%'` scans the whole table and will slow down as orders grow.
2. Return pagination metadata with search results (`page`, `page_size`, `has_more` or `total`) so clients know when to stop.
3. Add a secret-scanning pre-commit hook or CI step (for example gitleaks or GitHub secret scanning) so a live key cannot be committed again.
4. Wire `charge()` into an actual order flow behind tests before it is used. Right now it is dead code.

## ❓ Questions / Clarifications Needed

1. The description says the PR "moves the session secret to an env var", but `main` has no hardcoded session secret, and nothing in the codebase reads `config.SECRET_KEY`. Is a later PR going to use it, or was a hardcoded secret removed somewhere outside this repo?
2. Should `GET /orders/search` and order detail require authentication or authorization? Neither handler checks the caller. Search lists customer names and totals across all customers, and order detail now exposes `customer_email`. Is this endpoint strictly internal?
3. Is `customer_name` a copy stored on `orders`, alongside `customer_id`? If so, searching by name won't find orders after a customer renames. Should search join on `users.name` instead?
4. Who calls `charge()`, and should it run before or after the discount is applied? `apply_discount` returns a float total, while `charge()` takes integer cents.

## ✅ Positive Notes

- `get_order_with_customer` and `list_users` correctly use parameter binding, so the right pattern is already in the branch and only needs to be applied to search.
- `charge()` sets a request timeout (`timeout=10`), which is easy to forget with `urllib`.
- `SECRET_KEY` is read from the environment through `app/config.py`, following the project convention, and the comment makes clear that the value never belongs in code.
- `list_users` has a focused, readable test, and the fixture was extended rather than duplicated.
- The commits are small and have descriptive messages.

## Overall Recommendation

**Request Changes** - Critical issues must be addressed.

Required before merge:
1. Roll the Stripe live key now, move it to env/config, and remove it from branch history.
2. Parameterise the search SQL.
3. Fix the pagination offset to `(page - 1) * page_size`.
4. Make unknown discount codes a no-op.
5. Add tests for `orders.py` and `payments.py`, as the README requires.

Strongly recommended: handle deleted customers, validate the handler input (400 instead of 500), make `charge()` idempotent and stop it hiding failures, and fail fast on an empty `SECRET_KEY`.
