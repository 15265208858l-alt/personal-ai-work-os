# XAU/USD live spot provider
# Uses XAUS live spot endpoint; returns explicit freshness metadata.
from __future__ import annotations

import requests

URL = "https://xaus.com/api/v1/spot"
HEADERS = {"User-Agent": "LiuQiang-Personal-AI-Work-OS/4.3"}


def get_xauusd_spot(timeout: int = 6) -> dict:
    r = requests.get(URL, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    price = data.get("spot_usd_oz")
    if price is None:
        xau = data.get("xau") or {}
        price = xau.get("price")
    if price is None:
        raise RuntimeError("XAUUSD live API返回中没有spot价格")
    state = data.get("data_state") or {}
    return {
        "price": float(price),
        "source": data.get("source") or state.get("source") or "XAUS",
        "status": state.get("status") or "fresh",
        "as_of": state.get("as_of") or data.get("updated_at"),
        "age_seconds": state.get("age_seconds"),
        "updated_at": data.get("updated_at"),
    }
