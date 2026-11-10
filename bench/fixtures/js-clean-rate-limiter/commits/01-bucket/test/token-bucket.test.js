import { test } from "node:test";
import assert from "node:assert/strict";
import { TokenBucket } from "../src/token-bucket.js";

function fakeClock(start = 0) {
  let t = start;
  return { now: () => t, advance: (ms) => { t += ms; } };
}

test("starts full and drains", () => {
  const clock = fakeClock();
  const b = new TokenBucket({ capacity: 2, refillPerSec: 1, now: clock.now });
  assert.equal(b.tryRemove(), true);
  assert.equal(b.tryRemove(), true);
  assert.equal(b.tryRemove(), false);
});

test("refills over time but never above capacity", () => {
  const clock = fakeClock();
  const b = new TokenBucket({ capacity: 2, refillPerSec: 1, now: clock.now });
  b.tryRemove(2);
  clock.advance(1500);
  assert.equal(b.available(), 1.5);
  clock.advance(60_000);
  assert.equal(b.available(), 2);
});

test("tryRemove(n) is all-or-nothing", () => {
  const clock = fakeClock();
  const b = new TokenBucket({ capacity: 3, refillPerSec: 0, now: clock.now });
  assert.equal(b.tryRemove(4), false);
  assert.equal(b.available(), 3);
});

test("clock going backwards does not remove tokens", () => {
  const clock = fakeClock(10_000);
  const b = new TokenBucket({ capacity: 2, refillPerSec: 1, now: clock.now });
  b.tryRemove(1);
  clock.advance(-5_000);
  assert.equal(b.available(), 1);
});

test("rejects invalid arguments", () => {
  assert.throws(() => new TokenBucket({ capacity: 0, refillPerSec: 1 }), RangeError);
  assert.throws(() => new TokenBucket({ capacity: 1, refillPerSec: -1 }), RangeError);
  assert.throws(() => new TokenBucket({ capacity: 1, refillPerSec: NaN }), RangeError);
  const b = new TokenBucket({ capacity: 1, refillPerSec: 1 });
  assert.throws(() => b.tryRemove(0), RangeError);
});
