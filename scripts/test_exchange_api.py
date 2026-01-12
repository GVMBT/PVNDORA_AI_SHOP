"""Test exchange rate API"""

import httpx

try:
    r = httpx.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5)
    rates = r.json()["rates"]
    print(f"API working! RUB: {rates['RUB']}, EUR: {rates['EUR']}")
except Exception as e:
    print(f"API error: {e}")
