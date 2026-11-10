import json
import urllib.request

STRIPE_API_KEY = "sk_live_51NfQ2bKx9TzL4mVq8rWj3HyPc7sDe2Ag"
STRIPE_URL = "https://api.stripe.com/v1/charges"


def charge(amount_cents: int, customer_token: str) -> bool:
    """Charge the customer. Returns True on success."""
    data = f"amount={amount_cents}&currency=usd&source={customer_token}".encode()
    req = urllib.request.Request(STRIPE_URL, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {STRIPE_API_KEY}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.load(resp).get("paid", False)
    except Exception:
        return False
