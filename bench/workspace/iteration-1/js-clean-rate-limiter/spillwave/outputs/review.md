# Pull Request Review - Detailed Analysis

## PR Information

**Repository**: @acme/net-utils (local repository, no GitHub remote)
**PR Number**: N/A (local branch review)
**Title**: Add TokenBucket rate limiter
**Author**: Dev
**Branch**: feat/token-bucket → main

## Summary

This PR adds a small in-memory `TokenBucket` (`src/token-bucket.js`, 59 lines), exports it from `src/index.js`, documents it in the README, and adds 5 tests. It's 113 added lines across 2 commits with clear messages, and the scope is tight. The code is clean and matches the style of `retry.js`: JSDoc, `RangeError` input checks and an injectable dependency for tests. Continuous refill, the cap at capacity, all-or-nothing `tryRemove(n)` and the input checks are all correct.

I ran `npm test` on Node v20.19.4: 8/8 pass (the 5 new tests plus the 3 existing `retry` tests). The claim in the description holds.

There is one substantive issue, in the feature the description highlights: "Guards against the system clock going backwards". The default clock is `Date.now`, which is wall-clock time. The guard ignores any reading below the high-water mark, so a backward clock step stops all refill until the wall clock catches up again. I reproduced this: after a 1-hour backward step, the bucket granted **0 tokens in the next hour** of calls, then recovered. For the webhook sender in #212, a routine NTP step or VM resume would silently stop outbound webhooks for as long as the clock was moved back. The fix is one line (use a monotonic clock as the default). The other findings are minor.

Data gathered locally in place of the GitHub fetch: `git log main..feat/token-bucket`, `git diff main...feat/token-bucket`, and the full sources of `src/` and `test/`, plus `npm test` and small throwaway `node -e` checks against the branch. I didn't have access to issue #212, PR comments or CI status.

## 🟡 Important Issues

**Should be addressed before merging.**

### 1. Functionality: Backward wall-clock step stalls refill for the whole size of the step

**File**: `src/token-bucket.js:13`

**Impact**: The default `now = Date.now` reads the wall clock, which NTP, a VM snapshot restore or an admin can move backwards. In `#refill()` (line 54), `if (t <= this.lastRefill) return;` keeps `lastRefill` at the old high-water mark. No tokens are added until wall time passes that mark again, so a backward step of D stops refill for D. I reproduced this with capacity 5 at 1 token/sec, drained, then stepped back 1 hour: 3,599 calls of `tryRemove()`, one per second, all returned `false`. The first success came only after the clock passed the old mark. The comment's goal ("a later forward jump can't grant unearned tokens") is reasonable, but it swaps a bounded risk (at most `capacity` extra tokens) for an unbounded outage. For a rate limiter guarding outbound webhooks, the outage is the worse failure.

**Suggestion**: Make the default clock monotonic so it can't go backwards: `now = () => performance.now()`. `performance` is a global in Node >= 20 (the `engines` floor), and it also counts in milliseconds, so no other code changes. Keep the `t <= lastRefill` guard as a fallback for injected clocks. If you'd rather keep wall-clock time, move the baseline instead of freezing it (`if (t < this.lastRefill) { this.lastRefill = t; return; }`); at worst that grants up to `capacity` tokens after a later forward jump. Either way, update the PR description and the README so they don't promise more than the code does.

**Code**:
```
constructor({ capacity, refillPerSec, now = Date.now }) {
...
    if (t <= this.lastRefill) return;
```

---

## 🟢 Minor Issues (Nits)

**Nice to have, but not blocking.**

1. **Testing**: The backward-clock test doesn't check the behavior the comment describes
   - File: `test/token-bucket.test.js`
   - `clock going backwards does not remove tokens` (line 35) only checks that tokens don't go down. Nothing tests what happens when the clock moves forward again after a backward step, which is what the guard is for and where issue 1 sits. Add a case that steps back, then forward, and asserts the expected count. Also add a case with a large backward step followed by steady small forward steps, to pin down whichever behavior you pick.

2. **API**: `tryRemove(n)` with `n > capacity` returns `false` forever
   - File: `src/token-bucket.js:38`
   - A request larger than the bucket can never succeed, but the caller can't tell that apart from normal rate limiting and may retry forever. Consider throwing a `RangeError` for `n > this.capacity`, the same way invalid `n` already throws. At minimum, document it.

3. **Encapsulation**: Internal state is public and mutable
   - File: `src/token-bucket.js:20-24`
   - `tokens`, `lastRefill`, `capacity`, `refillPerSec` and `now` are plain public fields. Outside code can write `bucket.tokens = 1e9` (I checked: `available()` then returns 1e9). The class already uses a private `#refill()`, so making `#tokens` and `#lastRefill` private would match that and close the gap. Expose `capacity` through a getter if callers need it.

4. **Docs**: `available()` returns fractional values
   - File: `README.md`
   - Refill is continuous, so `available()` returns values like `1.5` (the test checks exactly this). "Returns the current token count" reads as an integer. Say it can be fractional so callers don't compare it to whole numbers. The README also leaves out the `now` option. That's reasonable if it's only meant for tests, but then say so in the JSDoc.

5. **Testing**: Minor gaps in the invalid-argument tests
   - File: `test/token-bucket.test.js:43-49`
   - Validation for `capacity: Infinity`, `capacity: NaN`, `tryRemove(NaN)` and `tryRemove(-1)` isn't tested. The code handles all of them correctly; these are just cheap regression tests to add.

## 💡 Suggestions for Future

1. For the #212 webhook sender, a `msUntilAvailable(n = 1)` (or `tryRemove` returning a wait time) would let callers schedule a retry instead of polling `tryRemove()` in a loop. It fits well with the existing `retry` helper's injectable `sleep`.
2. "One instance per key" will need a keyed wrapper with eviction (for example, a `Map` with idle expiry) if the sender limits per destination host. Otherwise the map of buckets grows without limit. Better as a separate PR.
3. Adding a public export to a published package (`@acme/net-utils` 2.1.0) is a minor-version change. Make sure the release process bumps the version.

## ❓ Questions / Clarifications Needed

1. Was `Date.now` chosen on purpose as the default, for example to match timestamps elsewhere in the webhook sender? If not, is there any reason not to switch to `performance.now()`?
2. Does #212 need per-destination limiting (many buckets) or one global limit? The answer decides whether suggestion 2 is needed soon.

## ✅ Positive Notes

- The injectable `now` clock makes the tests fully deterministic, with no timers or sleeps. It's the same pattern as the `sleep` injection in `retry.js`.
- Constructor and `tryRemove` validation is thorough (`Number.isFinite` rejects `NaN` and `Infinity`) and uses `RangeError`, consistent with the existing code.
- `tryRemove(n)` is all-or-nothing and tested that way, and refill is correctly capped at capacity (tested with a 60-second jump).
- Floating-point drift is a non-issue in practice: I polled `available()` at fine intervals across several rate/step combinations and saw only about 1e-16 error.
- The PR is small and focused: two atomic commits with clear messages, README updated, no new dependencies, and all tests pass.

## Overall Recommendation

**Request Changes** - Important issues should be fixed.

There's one important issue, and the fix is small: default to a monotonic clock (or move the baseline back on a backward step) and add a test for "backward, then forward". Once that's done, this is ready to merge. The nits can be handled now or later.
