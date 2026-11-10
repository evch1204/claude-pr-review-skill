import sqlite3

from app.users import get_user

DISCOUNTS = {"WELCOME10": 10, "VIP25": 25}


def search_orders(conn: sqlite3.Connection, customer_name: str, page: int, page_size: int = 20):
    """Search orders by (partial) customer name. `page` is 1-indexed."""
    offset = page * page_size
    query = (
        "SELECT id, customer_id, customer_name, total FROM orders "
        f"WHERE customer_name LIKE '%{customer_name}%' "
        f"ORDER BY id LIMIT {page_size} OFFSET {offset}"
    )
    return [dict(r) for r in conn.execute(query).fetchall()]


def apply_discount(order_total: float, code: str | None) -> float:
    """Return the total after applying a discount code. Unknown codes are ignored."""
    if not code:
        return order_total
    pct = DISCOUNTS.get(code.upper())
    return round(order_total - order_total * pct / 100, 2)


def get_order_with_customer(conn: sqlite3.Connection, order_id: int) -> dict | None:
    row = conn.execute(
        "SELECT id, customer_id, total FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    if row is None:
        return None
    order = dict(row)
    customer = get_user(conn, order["customer_id"])
    order["customer_email"] = customer["email"]
    return order
