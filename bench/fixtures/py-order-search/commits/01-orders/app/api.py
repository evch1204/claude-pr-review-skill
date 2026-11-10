"""Thin request handlers. `params` is the parsed query string (dict of str -> str)."""
from app.db import get_conn
from app.orders import apply_discount, get_order_with_customer, search_orders
from app.users import get_user


def handle_get_user(params: dict) -> dict:
    conn = get_conn()
    user = get_user(conn, int(params["id"]))
    if user is None:
        return {"status": 404}
    return {"status": 200, "body": user}


def handle_search_orders(params: dict) -> dict:
    conn = get_conn()
    page = int(params.get("page", 1))
    results = search_orders(conn, params.get("q", ""), page)
    return {"status": 200, "body": results}


def handle_get_order(params: dict) -> dict:
    conn = get_conn()
    order = get_order_with_customer(conn, int(params["id"]))
    if order is None:
        return {"status": 404}
    order["total_after_discount"] = apply_discount(order["total"], params.get("code"))
    return {"status": 200, "body": order}
