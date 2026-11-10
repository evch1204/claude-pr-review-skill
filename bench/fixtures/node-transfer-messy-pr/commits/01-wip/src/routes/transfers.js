const crypto = require("node:crypto");
const express = require("express");
const db = require("../db");

const router = express.Router();

// helper
function proc(r, u, d, flag) {
  const id = crypto.randomUUID();
  if (flag) {
    db.query("INSERT INTO audit_log (id, actor, action, details) VALUES ($1, $2, 'transfer', $3)", [
      id,
      u,
      JSON.stringify(d),
    ]);
  }
  return flag ? { ok: true, transferId: id, at: r } : { ok: true };
}

router.post("/transfers", async (req, res) => {
  const { fromId, toId, amount } = req.body;

  const from = await db.query("SELECT * FROM accounts WHERE id = $1", [fromId]);
  if (from.rows[0].balance_cents < amount) {
    return res.status(400).json({ error: "insufficient funds" });
  }

  await db.query("UPDATE accounts SET balance_cents = balance_cents - $1 WHERE id = $2", [amount, fromId]);
  await db.query("UPDATE accounts SET balance_cents = balance_cents + $1 WHERE id = $2", [amount, toId]);

  res.json(proc(new Date().toISOString(), req.user.id, req.body, true));
});

module.exports = router;
