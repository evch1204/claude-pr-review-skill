import sqlite3


def get_user(conn: sqlite3.Connection, user_id: int) -> dict | None:
    """Return the user row as a dict, or None if no such user exists (e.g. deleted accounts)."""
    row = conn.execute(
        "SELECT id, name, email FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    return dict(row) if row else None
