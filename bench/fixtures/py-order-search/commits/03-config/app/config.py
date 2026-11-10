import os

DATABASE_PATH = os.environ.get("DATABASE_PATH", "orders.db")

# Name of the env var that holds the session-signing secret (the value itself is never in code).
SECRET_KEY_ENV_VAR = "ORDERS_SECRET_KEY"
SECRET_KEY = os.environ.get(SECRET_KEY_ENV_VAR, "")
