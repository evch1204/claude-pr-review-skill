const { Pool } = require("pg");

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

function query(text, params) {
  return pool.query(text, params);
}

/**
 * Run `fn(client)` inside a transaction. Commits on success, rolls back on throw.
 * Use `SELECT ... FOR UPDATE` inside to lock rows you will modify.
 */
async function withTransaction(fn) {
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    const result = await fn(client);
    await client.query("COMMIT");
    return result;
  } catch (err) {
    await client.query("ROLLBACK");
    throw err;
  } finally {
    client.release();
  }
}

module.exports = { query, withTransaction };
