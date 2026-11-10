# Review checklist

These are deeper prompts for each of the seven review areas. Use them to find candidates, then verify each one (SKILL.md Step 4). You don't need to report on every item. Most items won't apply to a given PR, and saying "checked X, fine" for each one is noise.

Sources the checklist draws on:
- Google Engineering Practices, "What to look for in a code review"
- OWASP Top 10 (2025) and the OWASP Code Review Guide
- Conventional Comments
- SmartBear/Cisco peer review study, which found defect detection drops past about 400 LOC per review

## Contents
1. Correctness
2. Security
3. Testing
4. Readability and maintainability
5. Performance
6. Style and conventions
7. PR quality
8. Language and framework pitfalls
9. Not bugs: precedents that prevent false positives

---

## 1. Correctness

- **Intent match.** Does the code do what the title, description, and linked issue say? Does it do anything they don't mention?
- **Contracts.** Do docstrings, comments, types, README, and API docs agree with the behavior? Examples: "1-indexed", "returns None if missing", "unknown codes are ignored". Each stated promise is a test case you can run in your head.
- **Edge inputs:**
  - empty collections or strings
  - `None`/`null`/`undefined`
  - zero, negative, and very large numbers
  - NaN
  - duplicates
  - first and last element (off-by-one)
  - Unicode and case
  - time zones and DST
  - floating-point money
- **Lookups that can miss.** `dict.get`, `find`, `rows[0]`, and `getUser` can all return nothing. What happens next?
- **Error paths:**
  - a bare `except`/`catch` that swallows the error or returns a misleading default
  - errors logged but not handled
  - wrong HTTP status
  - async errors with no handler, such as an unawaited promise or an Express 4 async route without `next(err)`
- **Partial failure.** If step 2 of 3 fails, what state is left behind? Multi-statement writes need a transaction.
- **Concurrency:**
  - check-then-act races, such as read balance → check → write
  - lost updates
  - shared mutable state
  - async results arriving out of order: stale responses, React effects without cleanup
  - missing locks or `SELECT … FOR UPDATE`
  - idempotency of retried operations
- **Regressions.** Compare removed lines with the base version. Look for:
  - a dropped guard, validation, or `await`
  - changed dependency arrays
  - changed defaults
  - narrowed types
  - keys changed from stable IDs to indexes
- **Resource handling.** Check for files, connections, and listeners that aren't closed or removed, and for timeouts that are missing on network calls.
- **Configuration and migrations.** Check for schema changes without migrations, migrations that aren't reversible or that lock big tables, and feature flags or default values that are wrong.

## 2. Security (OWASP Top 10 2025, mapped)

Trace every piece of untrusted data from its source to where it's used. Sources include request params, body, headers, cookies, files, webhook payloads, third-party API responses, and DB fields written by users. Pay most attention to code paths the PR adds or changes.

| OWASP 2025 | What to look for in a diff |
|---|---|
| A01 Broken Access Control | Object fetched by an ID from the request with no ownership or role check (IDOR). Missing authorization on a new route. CSRF missing on a cookie-authenticated state-changing route when the repo requires it or the cookie isn't SameSite-protected. CORS opened wide. |
| A02 Security Misconfiguration | Debug mode on, permissive CORS, verbose errors returned to clients, insecure cookie flags, default credentials. |
| A03 Software Supply Chain | New dependency: is it needed? Does an existing dependency already do it? Is it maintained (not abandoned or deprecated)? Lockfile updated consistently? Install scripts? Typosquat-looking names? Unpinned CI actions? |
| A04 Cryptographic Failures | Homemade crypto, MD5/SHA1 for passwords, ECB, static IVs, `Math.random()` for tokens, secrets compared without constant time. |
| A05 Injection | SQL built with string formatting or concatenation. Shell commands built from input (`shell=True`, `exec`). Template injection. Path traversal (`../` in file paths). NoSQL operator injection. LDAP or XPath. |
| A06 Insecure Design | Business-logic abuse such as negative quantities or amounts, skipping steps in a flow, or trusting client-computed prices or totals. |
| A07 Authentication Failures | Session fixation, missing re-auth for sensitive actions, tokens in URLs or logs, weak password handling. |
| A08 Software/Data Integrity | Unsafe deserialization (`pickle`, `yaml.load`, Java serialization), unsigned updates or webhooks. |
| A09 Logging and Alerting Failures | Secrets or PII written to logs. Security-relevant failures that leave no trace at all. |
| A10 Mishandling of Exceptional Conditions | Fail-open error handling: a catch that grants access or skips a check. Swallowed exceptions in security paths. |

Also check:
- **Secrets.** Live-looking keys or tokens in code, config, tests, or fixtures. Patterns include `sk_live_`, `AKIA`, `ghp_`, `xox`, private key blocks, and URLs with embedded passwords. A hard-coded real secret is 🔴 even if it's "only for now". It must be rotated, not just deleted, because it's in git history.
- **XSS.** Look at raw-HTML sinks: `dangerouslySetInnerHTML`, `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `v-html`, `{{{ }}}`, `|safe`, `mark_safe`, `html_safe`. Is the value sanitized (DOMPurify or similar) or escaped first? Are URL schemes allowlisted (`javascript:`)?
- **SSRF.** Server-side fetches of URLs the user controls (host or protocol).
- **Uploads.** File type and size checks, storage path, and whether files are served back with the right content type.

## 3. Testing

- Every new behavior or bug fix should have a test that **would fail without the change**.
- Tests should cover error and edge paths, not only the happy path. For security-sensitive code, test hostile input such as an escaping test for a renderer or an unauthorized access test for a route.
- Tests should check behavior through public interfaces, not implementation details or mocks of the thing under test.
- Watch for flaky patterns: real clocks or `sleep`, network access, order dependence, shared global state. Look for injectable clocks and fakes.
- Tests are code too: readable, no copy-paste walls, meaningful assertions (not `assert result`).
- Did the repo's test, lint, or typecheck commands pass? For GitHub PRs, check CI with `gh pr checks`. Locally, run existing scripts only if they're cheap, need no installs or network, and have no side effects.
- Saying "manually tested" in the PR description doesn't replace automated tests for logic that can be unit tested.

## 4. Readability and maintainability

- **Names** say what something is or does. Look for `proc`, `data2`, `flag`, `handle`, single letters outside tiny scopes, and misleading names.
- **Single responsibility.** A function that validates, does I/O, and formats a response is three functions. A boolean flag parameter that switches behavior usually means two functions.
- **Duplication (DRY).** Does the new code reimplement an existing helper, utility, or dependency? Search the repo before calling something duplicate. Don't demand abstractions for two similar lines.
- **Comments** explain why. Watch for stale comments contradicting the code, and commented-out code.
- **Dead code.** Unused imports, variables, parameters, unreachable branches, or exports.
- **Complexity.** Deep nesting, long functions, and clever one-liners make code slow to understand. Google's test: "can't be understood quickly by code readers."
- **Over-engineering.** Generic frameworks for one use, configuration nobody asked for, speculative extension points.
- **Error messages.** Are they actionable for whoever sees them?

## 5. Performance

Only flag what matters at realistic scale. Use the PR's stated sizes, the data model, or how the code is called.

- Nested loops or `find`/`indexOf`/`includes` inside loops over collections that can be large (O(n²)). The usual fix is a Set or Map.
- N+1 queries: a DB or API call inside a loop. Missing indexes for new query patterns.
- Expensive work repeated on every render or request that could be memoized or cached.
- Loading entire tables or files into memory. Missing pagination or limits on list endpoints.
- Unbounded growth: caches, maps keyed by user, IP, or request, and listeners added and never removed.
- Synchronous or blocking I/O on hot or async paths. Missing timeouts.

## 6. Style and conventions

- The repo's documented rules come first: CLAUDE.md, AGENTS.md, CONTRIBUTING, README "Conventions", the PR template. Quote the rule when citing it.
- Next, consistency with surrounding code: naming style, error-handling pattern, module layout, logging style.
- Don't flag what the configured formatter or linter enforces, unless CI clearly doesn't run it and the PR breaks it.
- Style points that are personal preference are at most a ⚪ nit, or nothing.

## 7. PR quality

- **Focus.** One logical change. Flag unrelated refactors, reformatting, dependency bumps, or drive-by fixes mixed into a feature. They hide real changes and make reverts risky.
- **Size.** Over about 400 changed lines, excluding generated files, defect detection drops. Suggest a split when one is natural.
- **Description.** Covers what, why, and how it was tested, plus risks, rollout, and migrations when relevant. An empty or vague title or description is a 🟡 when the repo requires one, otherwise a ⚪.
- **Commits.** Meaningful messages. "wip", "fix", or "more fixes" should be squashed or reworded before merge, especially if the repo asks for it.
- **Completeness.** Docs, README, changelog, config examples, and migrations updated alongside behavior changes. Breaking changes called out.

## 8. Language and framework pitfalls

**Python**
- Mutable default arguments.
- `except Exception: pass`.
- f-strings or `%` formatting in SQL.
- `is` vs `==`.
- Naive vs aware datetimes.
- Float money (use `Decimal` or integer cents).
- Comparisons with `None` in `dict.get` results.
- Blocking calls inside `async def`.
- `subprocess` with `shell=True`.
- `yaml.load` without `SafeLoader`.
- `pickle` on untrusted data.

**JavaScript / TypeScript / Node**
- Missing `await`.
- Unhandled promise rejections.
- Express 4 async handlers without try/catch → `next(err)`.
- `==` coercion.
- `parseInt` without a radix.
- Floating-point money.
- Prototype pollution via object merge.
- `any` hiding type errors.
- Non-null assertions (`!`) on values that can be null.
- `JSON.parse` without try.

**React**
- `useEffect` dependency arrays: missing deps cause stale data, and objects or functions in deps cause loops.
- Missing cleanup or cancellation for async effects, so state is set after unmount or from an outdated request.
- `key={index}` on lists that reorder or insert.
- State updates that depend on previous state without the functional form.
- `dangerouslySetInnerHTML` without sanitizing.
- Expensive computation in render without `useMemo` on large data.

**Go**
- Ignored `err`.
- Loop variable capture in goroutines (before Go 1.22).
- Nil map writes.
- Missing `defer rows.Close()` or `resp.Body.Close()`.
- Data races on shared maps.
- `context` not propagated.

**SQL / ORMs**
- String-built queries.
- Missing transactions around dependent writes.
- `SELECT *` in hot paths.
- Missing `WHERE` on `UPDATE`/`DELETE`.
- Migrations that lock large tables.
- N+1 queries via lazy loading.

**Shell / CI**
- Unquoted variables.
- Missing `set -euo pipefail`.
- `curl | sh`.
- Secrets echoed to logs.
- Unpinned third-party actions.
- `pull_request_target` with checkout of PR code.

## 9. Not bugs: precedents that prevent false positives

Don't report these unless the PR gives a specific reason to:

- **Parameterized queries are safe.** That covers `?`, `$1`, `%s` with params, and ORM bound parameters, including `LIMIT ?`.
- **Constants that name a secret are not secrets.** `SECRET_KEY_ENV_VAR = "APP_SECRET"`, `os.environ["API_KEY"]`, and placeholders like `"changeme"` in example config are fine.
- **Environment variables and CLI flags are trusted input.** They're operator-controlled.
- **Framework auto-escaping is safe.** JSX `{value}`, Jinja autoescape, and Go `html/template` are fine. Only raw-HTML sinks matter, and a sink that receives sanitized output (such as DOMPurify) is fine.
- **Random IDs are unguessable.** `crypto.randomUUID()`, `uuid4()`, and `secrets.token_*` are not "predictable IDs".
- **Client-side checks.** Missing client-side checks are not a vulnerability; the server is the boundary.
- **Missing hardening is not a bug.** Rate limiting, audit logs, extra headers, and timeouts on internal calls are out of scope unless the PR's purpose involves them or the repo requires them.
- **Theoretical races and timing attacks** are out of scope without a realistic way to exploit them.
- **Outdated but unchanged dependencies** are pre-existing.
- **Tool-enforced style.** Anything the configured formatter or linter enforces, and code explicitly silenced with a lint-ignore comment that gives a reason.
- **Test-only code.** Test files using hardcoded fake credentials, `localhost`, or sleeps in clearly fake contexts.
- **Bugs that need impossible input.** If a caller or type guarantees the input can't occur, don't report it.
- **Personal preference.** Alternative designs that are merely different, not better for this codebase.
