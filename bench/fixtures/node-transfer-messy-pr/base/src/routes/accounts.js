const express = require("express");
const db = require("../db");
const csrfProtection = require("../csrf");
const { formatCents } = require("../utils/format");

const router = express.Router();

async function loadOwnedAccount(req, res) {
  const { rows } = await db.query("SELECT * FROM accounts WHERE id = $1", [req.params.id]);
  const account = rows[0];
  if (!account) {
    res.status(404).json({ error: "not found" });
    return null;
  }
  if (account.owner_id !== req.user.id) {
    res.status(403).json({ error: "forbidden" });
    return null;
  }
  return account;
}

router.get("/accounts/:id", async (req, res, next) => {
  try {
    const account = await loadOwnedAccount(req, res);
    if (!account) return;
    res.json({ id: account.id, balance: formatCents(account.balance_cents) });
  } catch (err) {
    next(err);
  }
});

router.post("/accounts/:id/nickname", csrfProtection, async (req, res, next) => {
  try {
    const account = await loadOwnedAccount(req, res);
    if (!account) return;
    const nickname = String(req.body.nickname || "").slice(0, 40);
    await db.query("UPDATE accounts SET nickname = $1 WHERE id = $2", [nickname, account.id]);
    res.json({ ok: true });
  } catch (err) {
    next(err);
  }
});

module.exports = router;
