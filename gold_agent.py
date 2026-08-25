# =========================================================
# Personal AI Work OS
# Gold Macro Agent V1.0
# =========================================================
# 目标：提供一个轻量、可落地的黄金宏观观察器。
# 数据：Yahoo Finance chart API（无需API Key）。
# 本模块不调用GitHub API，不依赖ValueStock。
# =========================================================

from __future__ import annotations

import time
from functools import lru_cache
from typing import Any

import requests

_BASE = "https://query1.finance.yahoo.com/v8/finance/chart/{}"

SYMBOLS = {
    "gold": "GC=F",
    "dxy": "DX-Y.NYB",
    "us10y": "^TNX",
    "us2y": "^IRX",  # 作为短端利率的近似观察指标，UI中明确标注
}


def _fetch(symbol: str, range_: str = "6mo", interval: str = "1d") -> dict[str, Any]:
    url = _BASE.format(requests.utils.quote(symbol, safe=""))
    response = requests.get(
        url,
        params={"range": range_, "interval": interval, "events": "history"},
        timeout=10,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    response.raise_for_status()
    payload = response.json()
    result = payload.get("chart", {}).get("result")
    if not result:
        raise RuntimeError(f"Yahoo未返回{symbol}数据")
    item = result[0]
    timestamps = item.get("timestamp") or []
    quote = (item.get("indicators", {}).get("quote") or [{}])[0]
    closes = quote.get("close") or []
    rows = [(ts, close) for ts, close in zip(timestamps, closes) if close is not None]
    if not rows:
        raise RuntimeError(f"Yahoo返回{symbol}空价格序列")
    return {"symbol": symbol, "rows": rows, "meta": item.get("meta", {})}


def _pct_change(rows, days: int):
    if len(rows) <= days:
        return None
    latest = rows[-1][1]
    prev = rows[-1 - days][1]
    if prev in (None, 0):
        return None
    return (latest / prev - 1) * 100


def _slope_signal(rows, fast: int = 10, slow: int = 30):
    if len(rows) < slow + 2:
        return "数据不足"
    fast_avg = sum(v for _, v in rows[-fast:]) / fast
    slow_avg = sum(v for _, v in rows[-slow:]) / slow
    latest = rows[-1][1]
    if latest > fast_avg > slow_avg:
        return "偏强"
    if latest < fast_avg < slow_avg:
        return "偏弱"
    return "震荡"


def _fetch_with_fallback(symbol: str):
    errors = []
    for _ in range(2):
        try:
            return _fetch(symbol), errors
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            time.sleep(0.5)
    return None, errors


@lru_cache(maxsize=8)
def analyze_gold_market():
    started = time.time()
    series = {}
    errors = {}
    for key, symbol in SYMBOLS.items():
        data, err = _fetch_with_fallback(symbol)
        if data is not None:
            series[key] = data["rows"]
        elif err:
            errors[key] = err[-1]

    gold = series.get("gold")
    dxy = series.get("dxy")
    us10y = series.get("us10y")
    us2y = series.get("us2y")

    if not gold:
        return {
            "success": False,
            "error": "黄金价格数据暂时无法获取。",
            "diagnostics": errors,
            "elapsed_seconds": round(time.time() - started, 2),
        }

    gold_price = gold[-1][1]
    dxy_latest = dxy[-1][1] if dxy else None
    us10y_latest = us10y[-1][1] if us10y else None
    us2y_latest = us2y[-1][1] if us2y else None

    gold_5d = _pct_change(gold, 5)
    gold_20d = _pct_change(gold, 20)
    dxy_20d = _pct_change(dxy, 20) if dxy else None
    us10y_20d = _pct_change(us10y, 20) if us10y else None

    score = 50
    reasons = []
    if gold_20d is not None and gold_20d > 3:
        score += 15
        reasons.append("黄金20日动量偏强")
    elif gold_20d is not None and gold_20d < -3:
        score -= 15
        reasons.append("黄金20日动量偏弱")
    if dxy_20d is not None and dxy_20d < -1:
        score += 10
        reasons.append("美元指数20日走弱，对黄金形成支撑")
    elif dxy_20d is not None and dxy_20d > 1:
        score -= 10
        reasons.append("美元指数20日走强，对黄金形成压制")
    if us10y_20d is not None and us10y_20d < -3:
        score += 10
        reasons.append("美国10Y收益率近期回落")
    elif us10y_20d is not None and us10y_20d > 3:
        score -= 10
        reasons.append("美国10Y收益率近期上行")

    score = max(0, min(100, score))
    if score >= 70:
        outlook = "偏多"
    elif score <= 35:
        outlook = "偏空"
    else:
        outlook = "震荡"

    return {
        "success": True,
        "agent": "gold_agent",
        "as_of": int(gold[-1][0]),
        "market": {
            "gold": gold_price,
            "gold_5d_pct": gold_5d,
            "gold_20d_pct": gold_20d,
            "gold_trend": _slope_signal(gold),
            "dxy": dxy_latest,
            "dxy_20d_pct": dxy_20d,
            "us10y": us10y_latest,
            "us10y_20d_pct": us10y_20d,
            "us2y_approx": us2y_latest,
        },
        "score": score,
        "outlook": outlook,
        "reasons": reasons,
        "limitations": ["未接入FOMC概率、CPI/非农日历、央行购金与地缘政治新闻流，当前属于价格+利率+美元的第一版宏观观察器。"],
        "diagnostics": errors,
        "elapsed_seconds": round(time.time() - started, 2),
    }
