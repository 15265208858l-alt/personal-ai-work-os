# =========================================================
# Personal AI Work OS
# Gold Macro Agent V1.1
# =========================================================
# 第一阶段：黄金价格 + 美元 + 美债收益率 + 趋势
# 数据：Yahoo Finance chart API（无需API Key）
# 不依赖ValueStock，也不调用GitHub API。
# =========================================================

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from typing import Any

import requests

_BASE = "https://query1.finance.yahoo.com/v8/finance/chart/{}"
SYMBOLS = {
    "gold": "GC=F",
    "dxy": "DX-Y.NYB",
    "us10y": "^TNX",
    "us2y": "^IRX",
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
    result = response.json().get("chart", {}).get("result")
    if not result:
        raise RuntimeError(f"Yahoo未返回{symbol}数据")
    item = result[0]
    timestamps = item.get("timestamp") or []
    quote = (item.get("indicators", {}).get("quote") or [{}])[0]
    closes = quote.get("close") or []
    rows = [(ts, close) for ts, close in zip(timestamps, closes) if close is not None]
    if not rows:
        raise RuntimeError(f"Yahoo返回{symbol}空价格序列")
    return {"symbol": symbol, "rows": rows}


def _fetch_with_retry(symbol: str):
    errors = []
    for attempt in range(2):
        try:
            return _fetch(symbol), errors
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            if attempt == 0:
                time.sleep(0.4)
    return None, errors


def _pct_change(rows, days: int):
    if len(rows) <= days:
        return None
    latest = rows[-1][1]
    prev = rows[-1 - days][1]
    if prev in (None, 0):
        return None
    return (latest / prev - 1) * 100


def _trend(rows, fast=10, slow=30):
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


@lru_cache(maxsize=8)
def analyze_gold_market():
    started = time.time()
    series = {}
    errors = {}

    # 四类市场数据并行，避免黄金Agent自己变慢。
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_fetch_with_retry, symbol): key for key, symbol in SYMBOLS.items()}
        for future in as_completed(futures):
            key = futures[future]
            try:
                data, err = future.result()
                if data:
                    series[key] = data["rows"]
                elif err:
                    errors[key] = err[-1]
            except Exception as exc:
                errors[key] = f"{type(exc).__name__}: {exc}"

    gold = series.get("gold")
    dxy = series.get("dxy")
    us10y = series.get("us10y")
    us2y = series.get("us2y")

    if not gold:
        return {
            "success": False,
            "agent": "gold_agent",
            "error": "黄金价格数据暂时无法获取。",
            "diagnostics": errors,
            "elapsed_seconds": round(time.time() - started, 2),
        }

    gold_5d = _pct_change(gold, 5)
    gold_20d = _pct_change(gold, 20)
    dxy_20d = _pct_change(dxy, 20) if dxy else None
    us10y_20d = _pct_change(us10y, 20) if us10y else None

    score = 50
    reasons = []
    if gold_20d is not None:
        if gold_20d > 3:
            score += 15; reasons.append("黄金20日动量偏强")
        elif gold_20d < -3:
            score -= 15; reasons.append("黄金20日动量偏弱")
    if dxy_20d is not None:
        if dxy_20d < -1:
            score += 10; reasons.append("美元指数20日走弱，对黄金形成支撑")
        elif dxy_20d > 1:
            score -= 10; reasons.append("美元指数20日走强，对黄金形成压制")
    if us10y_20d is not None:
        if us10y_20d < -3:
            score += 10; reasons.append("美国10Y收益率近期回落")
        elif us10y_20d > 3:
            score -= 10; reasons.append("美国10Y收益率近期上行")

    score = max(0, min(100, score))
    outlook = "偏多" if score >= 70 else "偏空" if score <= 35 else "震荡"

    return {
        "success": True,
        "agent": "gold_agent",
        "as_of": int(gold[-1][0]),
        "market": {
            "gold": gold[-1][1],
            "gold_5d_pct": gold_5d,
            "gold_20d_pct": gold_20d,
            "gold_trend": _trend(gold),
            "dxy": dxy[-1][1] if dxy else None,
            "dxy_20d_pct": dxy_20d,
            "us10y": us10y[-1][1] if us10y else None,
            "us10y_20d_pct": us10y_20d,
            "us2y_approx": us2y[-1][1] if us2y else None,
        },
        "score": score,
        "outlook": outlook,
        "reasons": reasons,
        "limitations": [
            "当前版本尚未接入FOMC概率、CPI/非农日历、央行购金和地缘政治新闻流。"
        ],
        "diagnostics": errors,
        "elapsed_seconds": round(time.time() - started, 2),
    }


def render_gold_result(result: dict[str, Any]) -> None:
    """在当前Streamlit执行流中展示黄金Agent结果，避免必须重构旧app。"""
    import streamlit as st

    st.divider()
    st.markdown("# 🥇 黄金宏观研究结果")

    if not result.get("success"):
        st.error(result.get("error", "黄金宏观Agent执行失败"))
        diagnostics = result.get("diagnostics") or {}
        if diagnostics:
            st.json(diagnostics)
        return

    market = result.get("market") or {}
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("国际黄金", f"{market.get('gold', '暂无'):.2f}" if isinstance(market.get('gold'), (int, float)) else "暂无")
    c2.metric("美元指数", f"{market.get('dxy', '暂无'):.2f}" if isinstance(market.get('dxy'), (int, float)) else "暂无")
    c3.metric("美国10Y", f"{market.get('us10y', '暂无'):.2f}%" if isinstance(market.get('us10y'), (int, float)) else "暂无")
    c4.metric("黄金趋势", market.get("gold_trend", "暂无"))

    c1, c2, c3 = st.columns(3)
    c1.metric("黄金5日涨跌", "暂无" if market.get("gold_5d_pct") is None else f"{market['gold_5d_pct']:.2f}%")
    c2.metric("黄金20日涨跌", "暂无" if market.get("gold_20d_pct") is None else f"{market['gold_20d_pct']:.2f}%")
    c3.metric("黄金宏观评分", f"{result.get('score', '暂无')}/100")

    outlook = result.get("outlook", "暂无")
    if outlook == "偏多":
        st.success(f"🟢 综合判断：{outlook}")
    elif outlook == "偏空":
        st.error(f"🔴 综合判断：{outlook}")
    else:
        st.warning(f"🟡 综合判断：{outlook}")

    reasons = result.get("reasons") or []
    if reasons:
        st.markdown("### 🧠 主要驱动因素")
        for reason in reasons:
            st.write(f"• {reason}")

    with st.expander("🩺 黄金Agent数据诊断", expanded=False):
        diagnostics = result.get("diagnostics") or {}
        if diagnostics:
            st.json(diagnostics)
        else:
            st.success("✅ 当前价格数据链路正常")

    st.caption(
        "数据来源：Yahoo Finance行情接口。当前为第一阶段价格/美元/美债宏观模型，不应单独作为交易决策依据。"
    )
