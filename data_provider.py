# =========================================================
# Personal AI Work OS
# Real Market Data Provider V1.4
# =========================================================

import re
import requests


EASTMONEY_URL = "https://push2.eastmoney.com/api/qt/stock/get"


def normalize_stock_code(text):
    """从用户输入中提取A股6位代码。"""
    match = re.search(r"(?<!\d)(\d{6})(?!\d)", text or "")
    if match:
        return match.group(1)

    name_map = {
        "美的集团": "000333",
        "特变电工": "600089",
        "牧原股份": "002714",
        "紫光股份": "000938",
        "博敏电子": "603936",
        "沪电股份": "002463",
        "深南电路": "002916",
        "生益科技": "600183",
        "紫金矿业": "601899",
        "章源钨业": "002378",
    }

    for name, code in name_map.items():
        if name in (text or ""):
            return code

    return None


def get_secid(code):
    """生成东方财富 secid：沪市1，深市0。"""
    if code.startswith(("5", "6", "9")):
        return f"1.{code}"
    return f"0.{code}"


def get_stock_quote(code):
    """获取A股实时行情。失败时返回可读错误，不让主程序崩溃。"""

    secid = get_secid(code)

    params = {
        "secid": secid,
        "fields": "f57,f58,f43,f169,f170,f116,f117",
    }

    try:
        response = requests.get(
            EASTMONEY_URL,
            params=params,
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0"
            },
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data")

        if not data:
            return {
                "success": False,
                "error": "没有获取到行情数据。"
            }

        price_raw = data.get("f43")
        change_raw = data.get("f169")
        pct_raw = data.get("f170")
        market_cap_raw = data.get("f116")
        circulating_raw = data.get("f117")

        def to_float(value, scale=1):
            if value in (None, "-", ""):
                return None
            return float(value) / scale

        return {
            "success": True,
            "code": data.get("f57", code),
            "name": data.get("f58", ""),
            "price": to_float(price_raw, 100),
            "change": to_float(change_raw, 100),
            "change_pct": to_float(pct_raw, 100),
            "market_cap_yuan": to_float(market_cap_raw, 1),
            "circulating_cap_yuan": to_float(circulating_raw, 1),
        }

    except Exception as exc:
        return {
            "success": False,
            "error": f"行情接口暂时无法访问：{exc}"
        }


def format_market_cap(value):
    if value is None:
        return "暂无"

    value = float(value)

    if value >= 1e12:
        return f"{value / 1e12:.2f} 万亿元"

    if value >= 1e8:
        return f"{value / 1e8:.2f} 亿元"

    return f"{value / 1e4:.2f} 万元"
