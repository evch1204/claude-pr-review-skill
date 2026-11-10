## PR Review: Add TokenBucket rate limiter

**Verdict: ✅ Approve**: Small, correct, well-tested change. I found nothing that blocks merge, only three optional nits.

This adds an in-memory `TokenBucket` (continuous refill capped at `capacity`, all-or-nothing `tryRemove(n)`, injectable `now` clock) to `src/token-bucket.js`, exports it from `src/index.js`, and documents it in the README. I traced the refill math, the input validation, and the clock-going-backwards guard, and ran them against edge inputs. They behave as the doc comments and the README say.

### ⚪ Nits
- `src/token-bucket.js:13,54`: The backwards-clock guard keeps the high-water mark, so after a wall-clock step back the bucket refills nothing until the clock catches up again. I confirmed it: with a drained bucket, a 1-hour step back followed by 10 s of real time leaves `available() === 0`, and a webhook sender using it would stall for about an hour. Making the default clock `() => performance.now()` (monotonic, global in Node ≥ 20) avoids backwards steps entirely, and the guard stays as a safety net for injected clocks.
- `src/token-bucket.js:38`: `tryRemove(n)` with `n > capacity` can never succeed, and it returns `false` exactly like ordinary rate limiting. A caller that retries until `true` will wait forever. Consider throwing a `RangeError` for `n > capacity`, as the method already does for `n <= 0`, or say in the README that it always fails.
- `test/token-bucket.test.js:35`: The backwards-clock test only checks that tokens aren't removed. Nothing tests the promise in the comment at `src/token-bucket.js:52-53` that "a later forward jump can't grant unearned tokens". Add one assertion: step back, step forward to the old time, and `available()` should be unchanged.

### Scorecard
| Area | | Note |
|---|---|---|
| Correctness | ✅ | Refill, cap, all-or-nothing, and validation all check out |
| Security | n/a | No untrusted input or I/O |
| Testing | ✅ | 5 focused cases with deterministic fake clock |
| Readability | ✅ | Clear JSDoc and a "why" comment on the guard |
| Performance | ✅ | O(1) per call |
| Conventions | ✅ | Matches `retry.js` (RangeError validation, injectable deps) |
| PR quality | ✅ | Focused, README updated, clear description |

**Checked:** `npm test` on Node 20.19.4: 8/8 pass (5 new + 3 existing). I also ran ad-hoc `node -e` probes for clock step-back, float drift (about 3e-15 after 1,000 refills, which doesn't matter), and the `n > capacity` case. There's no CI because this is a local branch with no remote. I couldn't open #212 (no remote), so I didn't check how the webhook sender will call this. · **Not reviewed:** nothing skipped.
**Good:** The injectable `now` clock follows the same pattern as `retry`'s injectable `sleep`, so the tests are fully deterministic with no real timers.
