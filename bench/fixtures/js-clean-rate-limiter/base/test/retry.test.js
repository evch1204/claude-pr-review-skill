import { test } from "node:test";
import assert from "node:assert/strict";
import { retry } from "../src/retry.js";

const noSleep = async () => {};

test("returns first success", async () => {
  let calls = 0;
  const out = await retry(async () => { calls++; if (calls < 2) throw new Error("x"); return 42; }, { sleep: noSleep });
  assert.equal(out, 42);
  assert.equal(calls, 2);
});

test("rethrows last error", async () => {
  await assert.rejects(retry(async () => { throw new Error("boom"); }, { attempts: 2, sleep: noSleep }), /boom/);
});

test("validates attempts", async () => {
  await assert.rejects(retry(async () => 1, { attempts: 0 }), RangeError);
});
