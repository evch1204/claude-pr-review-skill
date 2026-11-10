/**
 * Retry an async function with exponential backoff.
 * @param {() => Promise<T>} fn
 * @param {{ attempts?: number, baseDelayMs?: number, sleep?: (ms: number) => Promise<void> }} [opts]
 * @template T
 */
export async function retry(fn, { attempts = 3, baseDelayMs = 100, sleep = defaultSleep } = {}) {
  if (!Number.isInteger(attempts) || attempts < 1) {
    throw new RangeError("attempts must be a positive integer");
  }
  let lastErr;
  for (let i = 0; i < attempts; i++) {
    try {
      return await fn();
    } catch (err) {
      lastErr = err;
      if (i < attempts - 1) await sleep(baseDelayMs * 2 ** i);
    }
  }
  throw lastErr;
}

function defaultSleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
