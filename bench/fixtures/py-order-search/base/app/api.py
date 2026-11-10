"""Thin request handlers. `params` is the parsed query string (dict of str -> str)."""
from app.db import get_conn
from app.users import get_user


def handle_get_user(params: dict) -> dict:
    conn = get_conn()
    user = get_user(conn, int(params["id"]))
    if user is None:
        return {"status": 404}
    return {"status": 200, "body": user}
