# =========================================================
# 刘强 · Gold Agent compatibility wrapper V4.3
# =========================================================
# Keep the historical gold_agent import path stable while delegating
# research calculations to gold_macro_engine.py and patching the displayed
# spot price with a dedicated live XAU/USD spot endpoint.

from gold_macro_engine import analyze_gold_market as _analyze_gold_market
from gold_macro_engine import render_gold_result as _render_gold_result
from xauusd_live import get_xauusd_spot


def analyze_gold_market():
    result = _analyze_gold_market()
    if not isinstance(result, dict) or not result.get("success"):
        return result

    try:
        live = get_xauusd_spot()
        market = dict(result.get("market") or {})
        old_price = market.get("gold")
        market["gold"] = live["price"]
        market["gold_spot_price"] = live["price"]
        market["gold_spot_source"] = live["source"]
        market["gold_spot_status"] = live["status"]
        market["gold_spot_as_of"] = live["as_of"]
        market["gold_spot_age_seconds"] = live["age_seconds"]
        market["gold_price_previous_engine"] = old_price
        result["market"] = market
        result["gold_spot"] = live
        result["version"] = "V4.3"
        result.setdefault("diagnostics", {})
        result["diagnostics"]["gold_spot"] = {
            "source": live["source"],
            "status": live["status"],
            "as_of": live["as_of"],
            "age_seconds": live["age_seconds"],
            "note": "页面当前黄金价格采用独立XAU/USD实时现货接口；宏观/历史计算仍由Gold Macro Engine提供。",
        }
    except Exception as exc:
        result.setdefault("diagnostics", {})
        result["diagnostics"]["gold_spot"] = {
            "status": "live_api_failed",
            "error": f"{type(exc).__name__}: {exc}",
            "note": "实时XAU/USD接口失败时，保留Gold Macro Engine原价格作为研究计算结果。",
        }
    return result


def render_gold_result(result):
    _render_gold_result(result)


__all__ = ["analyze_gold_market", "render_gold_result"]
