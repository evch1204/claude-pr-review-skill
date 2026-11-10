# Review: Add TokenBucket rate limiter (`feat/token-bucket` → `main`)

**Verdict: Request changes, but only one small fix.** The code is tidy, the API is small, and the tests are deterministic. `npm test` passes on Node 20.19 (8/8: 3 retry, 5 new). One thing should change before this goes to the webhook sender: the "clock going backwards" guard doesn't do what the PR says. A wall-clock step backwards stalls the bucket for as long as the step, so every request gets rate limited for that whole time.

## Must fix

### 1. A backwards clock step stops refills for as long as the step (`src/token-bucket.js`, `#refill`)

```js
constructor({ capacity, refillPerSec, now = Date.now }) { ... }
...
if (t <= this.lastRefill) return;
```

The default clock is `Date.now`, which is wall-clock time and can be stepped back by NTP, a VM resume or a manual change. When that happens, `lastRefill` stays at the old high-water mark. No tokens are added until wall-clock time catches up to it. Real time is still passing, but the bucket doesn't earn anything for it. If the bucket was empty when the step happened, `tryRemove()` returns `false` for the entire length of the step.

I reproduced this with the injected clock: capacity 10, 10 tokens/sec, drained, then the clock steps back 1 hour, then 10 real minutes pass in 1-second ticks. **0 of 600 `tryRemove()` calls succeed** (about 600 should). For the webhook sender in #212, that means an outage of up to an hour, with no error, caused by a routine clock correction.

The code comment says the guard stops "a later forward jump [from granting] unearned tokens". Refill is already capped at `capacity`, so the most a forward jump can grant is one full bucket. Stalling for an unbounded time is the worse failure.

**Suggested fix:** use a monotonic clock by default so the problem can't happen:

```js
constructor({ capacity, refillPerSec, now = () => performance.now() }) {
```

Keep the arrow wrapper. Passing `performance.now` directly throws `TypeError: The "this" argument must be an instance of Performance` on Node 20, because it's called unbound. The README or JSDoc should also say that `now` must not go backwards, or the guard should reset the baseline (`this.lastRefill = t`) when it detects a backwards step instead of just returning. Either way, a backwards step would cost at most the interval in which it happened.

**Test gap:** `"clock going backwards does not remove tokens"` only checks the moment right after the step. Add a recovery check, for example step back 5 s, advance 1 s, and assert that about 1 token came back. That would have caught this.

## Worth considering (non-blocking)

2. **`tryRemove(n)` with `n > capacity` returns `false` forever.** It isn't an error, and no amount of waiting will make it succeed. A caller that retries on `false` (likely in the webhook sender) would loop forever. I'd throw a `RangeError` for `n > capacity`, the same way invalid `n` is already rejected, or at least document it.
3. **Callers can't tell how long to wait.** The only signal is `false`, so the webhook sender will have to poll or guess a delay. A small helper such as `msUntil(n = 1)` returning `(n - tokens) / refillPerSec * 1000` would let it sleep exactly as long as needed (with `retry`, or with `setTimeout`). This is fine to do in a follow-up if #212 doesn't need it yet.
4. **`new TokenBucket()` with no arguments** throws a destructuring `TypeError` rather than the `RangeError` used everywhere else. A default of `= {}` on the parameter would make the errors consistent. Cosmetic.
5. **`tokens`, `lastRefill` and `now` are public, writable fields.** `#refill` is already private. Making the state private too (or at least treating it as internal) stops callers from relying on `b.tokens`, which can be stale until `available()` triggers a refill.

## Checked and fine

- Refill is capped at `capacity`, and `tryRemove(n)` is all-or-nothing (the tests cover both).
- Input validation rejects `0`, negative, `NaN` and `Infinity` for `capacity` and `n`, and allows `refillPerSec = 0`, which is a sensible fixed-quota bucket.
- Floating-point accumulation behaves: at 0.1 tokens/sec over 100 × 100 ms ticks, the bucket ends at exactly 1 and the token can be taken.
- The export from `src/index.js` and the README entry match the implementation. The style matches `retry.js`, with an injectable dependency for tests.
- `performance` is a global on Node ≥ 20 (the `engines` floor), so the suggested fix needs no new import.
