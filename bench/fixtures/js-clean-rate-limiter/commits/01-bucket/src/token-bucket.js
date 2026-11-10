/**
 * In-memory token bucket rate limiter.
 *
 * Holds up to `capacity` tokens and refills continuously at `refillPerSec`
 * tokens per second. Each call to `tryRemove(n)` takes `n` tokens if available.
 * Not shared across processes; use one instance per key you want to limit.
 */
export class TokenBucket {
  /**
   * @param {{ capacity: number, refillPerSec: number, now?: () => number }} opts
   *   `now` returns the current time in milliseconds (injectable for tests).
   */
  constructor({ capacity, refillPerSec, now = Date.now }) {
    if (!Number.isFinite(capacity) || capacity <= 0) {
      throw new RangeError("capacity must be a positive finite number");
    }
    if (!Number.isFinite(refillPerSec) || refillPerSec < 0) {
      throw new RangeError("refillPerSec must be a non-negative finite number");
    }
    this.capacity = capacity;
    this.refillPerSec = refillPerSec;
    this.now = now;
    this.tokens = capacity;
    this.lastRefill = now();
  }

  /** Current number of available tokens (after refilling). */
  available() {
    this.#refill();
    return this.tokens;
  }

  /**
   * Take `n` tokens if available.
   * @param {number} [n=1]
   * @returns {boolean} true if the tokens were taken, false if rate limited.
   */
  tryRemove(n = 1) {
    if (!Number.isFinite(n) || n <= 0) {
      throw new RangeError("n must be a positive finite number");
    }
    this.#refill();
    if (this.tokens >= n) {
      this.tokens -= n;
      return true;
    }
    return false;
  }

  #refill() {
    const t = this.now();
    // Ignore clocks that go backwards (e.g. wall-clock adjustments): keep the
    // high-water mark so a later forward jump can't grant unearned tokens.
    if (t <= this.lastRefill) return;
    const elapsedSec = (t - this.lastRefill) / 1000;
    this.tokens = Math.min(this.capacity, this.tokens + elapsedSec * this.refillPerSec);
    this.lastRefill = t;
  }
}
