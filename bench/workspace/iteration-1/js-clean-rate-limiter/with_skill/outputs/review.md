## PR Review: Add TokenBucket rate limiter

**Verdict: ✅ Approve**: The code is correct, validates its inputs, and is well tested. Only optional nits below.

This adds an in-memory `TokenBucket` (`src/token-bucket.js`). It refills continuously, caps at `capacity`, takes tokens all-or-nothing in `tryRemove(n)`, and accepts an injectable `now()` clock. It's exported from `src/index.js` and documented in the README. I traced the refill math, the cap, the backwards-clock guard, and the validation paths. All of them do what the PR description and JSDoc say.

### ⚪ Nits
- `src/token-bucket.js:13`: The default `now = Date.now` is a wall clock. The guard stops a backwards jump from minting tokens, but refill also stops until the clock gets back to the old time. If NTP steps the clock back 30 s while the bucket is empty, the webhook sender is throttled for an extra 30 s. Defaulting to `() => performance.now()` (monotonic, global in Node ≥ 20) avoids this, and the guard can stay as a safety net.
- `test/token-bucket.test.js:36`: The backwards-clock test only checks that tokens don't drop. It doesn't test the comment's other claim, that "a later forward jump can't grant unearned tokens." Add `clock.advance(5_500); assert.equal(b.available(), 1.5);` so the test fails if someone later resets `lastRefill` on a backwards step. I checked by hand that the current code returns 1.5 here.
- `src/token-bucket.js:40`: `tryRemove(n)` with `n > capacity` can never succeed, but it returns `false` the same way normal rate limiting does. A caller that waits and retries on `false` would loop forever. Consider throwing a `RangeError` here, which matches the other argument checks, or at least mention this in the JSDoc/README.

### Scorecard
| Area | | Note |
|---|---|---|
| Correctness | ✅ | Refill, cap, all-or-nothing, clock guard all verified |
| Security | n/a | No untrusted input or I/O |
| Testing | ✅ | Good fake-clock tests; one small gap (nit) |
| Readability | ✅ | Clear JSDoc; comment explains why |
| Performance | ✅ | O(1) per call |
| Conventions | ✅ | Matches `retry.js` style (RangeError, injectable dependency) |
| PR quality | ✅ | Focused, README updated, clear description |

**Checked:** `npm test` on `feat/token-bucket` (Node v20.19.4): 8/8 pass (5 new, 3 existing). I also ran a quick script on the backwards-then-forward clock case, which returned the correct 0.5 tokens. No lint config or CI in the repo. · **Not reviewed:** nothing skipped (113 lines added across 4 files).
**Good:** The injectable `now` follows the same pattern as `retry`'s injectable `sleep`, so the tests are fully deterministic with no real timers.
