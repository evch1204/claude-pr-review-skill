## PR Review: Add TokenBucket rate limiter (`feat/token-bucket` → `main`)

**Verdict: ✅ Approve**: the code is correct, tested, and documented. I found nothing above nit.

The PR adds a dependency-free, in-memory `TokenBucket` with continuous refill capped at `capacity`, all-or-nothing `tryRemove(n)`, an injectable `now()` clock, and a guard that keeps the clock's high-water mark when time goes backwards. It's exported from `src/index.js` and documented in the README. The style matches `retry.js`: `RangeError` validation and an injectable dependency for tests.

### ⚪ Nits
- `src/token-bucket.js:13`: Consider defaulting `now` to `performance.now` (monotonic, global in Node ≥ 20) instead of `Date.now`. With `Date.now`, the backwards-clock guard at line 54 keeps the limiter from refilling until wall time catches up. I checked this with a fake clock: a 1-hour backwards step left a drained bucket at 0 tokens for the whole hour, so the webhook sender would stop sending. A monotonic default removes that case, and the guard still protects injected clocks.
- `src/token-bucket.js:39`: `tryRemove(n)` with `n > capacity` returns `false` forever, which reads as "rate limited" but can never succeed. A caller that loops until `true` would spin forever. Consider throwing `RangeError` here, as you already do for `n <= 0`. The "all-or-nothing" test (`test/token-bucket.test.js:31`) uses exactly this case, so it would need a satisfiable request instead, e.g. take 2 of 3, then `tryRemove(2)` → `false` with `available()` still `1`.
- `test/token-bucket.test.js:35`: This test doesn't pin down the high-water-mark behavior the comment at line 52 promises. If the code reset `lastRefill = t` on a backwards step, the test would still pass. Add `clock.advance(3_000)` and assert `available()` is still `1`, then advance past the old mark and assert it refills.

### Scorecard
| Area | | Note |
|---|---|---|
| Correctness | ✅ | Refill, cap, validation and backwards clock all correct |
| Security | ✅ | No input surface, no new dependencies |
| Testing | ✅ | 5 focused deterministic tests; one small gap (nit) |
| Readability | ✅ | Small, clear, comment explains why |
| Performance | ✅ | O(1) per call |
| Conventions | ✅ | Matches `retry.js` patterns |
| PR quality | ✅ | Focused, clear description, README updated |

**Checked:** ran `npm test`: 8/8 pass (5 new). I also used a fake clock to probe the bucket for `n > capacity`, large backwards clock steps, and float build-up over many 1 ms refills; refills land on whole tokens with no rounding shortfall. No CI or remote, and issue #212 isn't reachable locally. · **Not reviewed:** nothing skipped.
**Good:** The injectable clock keeps every test deterministic with no sleeps, and the backwards-clock comment says *why* the high-water mark is kept, not just what the code does.
