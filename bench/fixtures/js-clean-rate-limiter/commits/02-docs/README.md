# @acme/net-utils

Small, dependency-free networking helpers.

## API
- `retry(fn, { attempts, baseDelayMs })` — retry an async function with exponential backoff.
- `new TokenBucket({ capacity, refillPerSec })` — in-memory token bucket.
  - `tryRemove(n = 1)` returns `true` if `n` tokens were taken, `false` if rate limited.
  - `available()` returns the current token count.
  - Per-process only; create one bucket per key you want to limit.
