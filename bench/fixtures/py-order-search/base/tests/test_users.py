import sqlite3

from app.users import get_user


def make_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)")
    conn.execute("INSERT INTO users VALUES (1, 'Ada', 'ada@example.com')")
    return conn


def test_get_user_found():
    assert get_user(make_conn(), 1)["email"] == "ada@example.com"


def test_get_user_missing():
    assert get_user(make_conn(), 99) is None
