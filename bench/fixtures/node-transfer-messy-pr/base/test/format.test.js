const { test } = require("node:test");
const assert = require("node:assert/strict");
const { formatCents, parseCents } = require("../src/utils/format");

test("formatCents", () => {
  assert.equal(formatCents(12345), "$123.45");
  assert.equal(formatCents(-5), "-$0.05");
});

test("parseCents", () => {
  assert.equal(parseCents("$1.5"), 150);
  assert.equal(parseCents("abc"), null);
});
