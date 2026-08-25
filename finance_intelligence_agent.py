# =========================================================
# 刘强 · Personal AI Work OS — Finance Intelligence Agent V1.0
# 全球市场 / 宏观 / 新闻 / 风险情报
# =========================================================
from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from typing import Any

import requests

YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{}"
FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"
NEWS = "https://news.google.com/rss/search?q={query}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
HEADERS = {"User-Agent": "Mozilla/5.0 LiuQiang-Personal-AI-Work-OS/1.0"}

MARKETS = {
    "标普500": "^GSPC",
    "纳斯达克": "^IXIC",
    "黄金期货": "GC=F",
    "原油": "CL=F",
    "美元指数": "DX-Y.NYB",
    "美国10Y": "^TNX",
}
FRED_SERIES = {"联邦基金利率": "DFF", "SOFR": "SOFR"}
NEWS_QUERIES = [
    "美联储 FOMC 利率 通胀 CPI PCE 非农 美债 美元 黄金",
    "美国经济 recession GDP jobs inflation treasury yields",
    "全球股市 China Japan Europe geopolitics oil gold",
]


def _yahoo(symbol: str):
    r = requests.get(YAHOO.format(requests.utils.quote(symbol, safe="")), params={"range": "3mo", "interval": "1d"}, headers=HEADERS, timeout=8)
    r.raise_for_status()
    result = ((r.json().get("chart") or {}).get("result") or [])
    if not result:
        raise RuntimeError(f"Yahoo无{symbol}数据")
    item = result[0]
    ts = item.get("timestamp") or []
    quote = (((item.get("indicators") or {}).get("quote")) or [{}])[0]
    close = quote.get("close") or []
    rows = [(t, v) for t, v in zip(ts, close) if v is not None]
    if not rows:
        raise RuntimeError(f"Yahoo返回{symbol}空数据")
    return rows


def _fred(series_id: str):
    r = requests.get(FRED.format(series_id), headers=HEADERS, timeout=8)
    r.raise_for_status()
    lines = r.text.strip().splitlines()
    if len(lines) < 2:
        raise RuntimeError(f"FRED无{series_id}数据")
    out = []
    for line in lines[1:]:
        parts = line.split(",", 1)
        if len(parts) != 2 or parts[1] in ("", "."):
            continue
        try:
            out.append((parts[0], float(parts[1])))
        except ValueError:
            continue
    return out


def _news(query: str, limit: int = 8):
    r = requests.get(NEWS.format(query=requests.utils.quote(query, safe="")), headers=HEADERS, timeout=8)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    return [{
        "title": (item.findtext("title") or "").strip(),
        "date": (item.findtext("pubDate") or "").strip(),
        "source": (item.findtext("source") or "Google News").strip(),
        "link": (item.findtext("link") or "").strip(),
    } for item in root.findall("./channel/item")[:limit]]


def _pct(rows, days=20):
    if not rows or len(rows) <= days:
        return None
    a, b = rows[-1][1], rows[-1-days][1]
    return None if not b else (a / b - 1) * 100


def _latest(rows):
    return (rows[-1][1], rows[-1][0]) if rows else (None, None)


def _market_state(change):
    if change is None:
        return "数据不足"
    if change >= 5:
        return "明显走强"
    if change >= 1:
        return "偏强"
    if change <= -5:
        return "明显走弱"
    if change <= -1:
        return "偏弱"
    return "震荡"


def _news_risk(headlines):
    text = " ".join(x.get("title", "").lower() for x in headlines)
    risk_words = ["war", "sanction", "conflict", "attack", "tariff", "recession", "default", "crisis", "geopolit", "战争", "制裁", "冲突", "关税", "衰退", "危机"]
    hits = sum(text.count(w) for w in risk_words)
    return max(0, min(100, 30 + hits * 4))


def _build_conclusion(market, macro, risk_score):
    spx = market.get("标普500", {}).get("change_20d")
    dxy = market.get("美元指数", {}).get("change_20d")
    y10 = market.get("美国10Y", {}).get("change_20d")
    fed = macro.get("联邦基金利率", {}).get("value")
    signals = []
    if spx is not None and spx < -3: signals.append("风险资产偏弱")
    elif spx is not None and spx > 3: signals.append("风险资产偏强")
    if dxy is not None and dxy > 1: signals.append("美元走强")
    elif dxy is not None and dxy < -1: signals.append("美元走弱")
    if y10 is not None and y10 > 2: signals.append("美债长端收益率上升")
    elif y10 is not None and y10 < -2: signals.append("美债长端收益率回落")
    if fed is not None: signals.append(f"联邦基金利率约{fed:.2f}%")
    if risk_score >= 65:
        regime = "风险偏好谨慎"
    elif risk_score <= 40:
        regime = "风险偏好相对稳定"
    else:
        regime = "风险偏好中性"
    return regime + "；" + "、".join(signals[:4]) if signals else regime + "；主要市场信号中性。"


@lru_cache(maxsize=4)
def analyze_finance_market() -> dict[str, Any]:
    started = time.time(); raw = {}; errors = {}; jobs = {}
    with ThreadPoolExecutor(max_workers=12) as pool:
        for name, symbol in MARKETS.items():
            jobs[pool.submit(lambda s=symbol: _yahoo(s))] = ("market", name)
        for name, sid in FRED_SERIES.items():
            jobs[pool.submit(lambda s=sid: _fred(s))] = ("fred", name)
        for i, q in enumerate(NEWS_QUERIES):
            jobs[pool.submit(lambda q=q: _news(q))] = ("news", f"news_{i}")
        for f in as_completed(jobs):
            kind, key = jobs[f]
            try:
                raw[key] = f.result()
            except Exception as exc:
                errors[key] = f"{type(exc).__name__}: {exc}"

    market = {}
    for name in MARKETS:
        rows = raw.get(name) or []
        latest, date = _latest(rows)
        change = _pct(rows, 20)
        market[name] = {"value": latest, "date": date, "change_20d": change, "state": _market_state(change)}

    macro = {}
    for name in FRED_SERIES:
        rows = raw.get(name) or []
        value, date = _latest(rows)
        macro[name] = {"value": value, "date": date}

    headlines = sum([raw.get("news_0") or [], raw.get("news_1") or [], raw.get("news_2") or []], [])
    risk_score = _news_risk(headlines)
    conclusion = _build_conclusion(market, macro, risk_score)
    confidence = max(40, min(100, 100 - len(errors) * 10))
    return {
        "success": True,
        "agent": "finance_intelligence_agent",
        "version": "V1.0",
        "as_of": int(time.time()),
        "market": market,
        "macro": macro,
        "news": headlines[:18],
        "risk_score": risk_score,
        "confidence": confidence,
        "conclusion": conclusion,
        "diagnostics": errors,
        "elapsed_seconds": round(time.time() - started, 2),
    }


def render_finance_result(result: dict[str, Any]) -> None:
    import streamlit as st
    st.divider()
    st.markdown("# 📰 全球财经情报与宏观研究 V1.0")
    if not result.get("success"):
        st.error(result.get("error", "财经情报Agent执行失败"))
        st.json(result.get("diagnostics") or {})
        return

    st.markdown("## 🌍 核心市场")
    names = ["标普500", "纳斯达克", "黄金期货", "原油", "美元指数", "美国10Y"]
    cols = st.columns(3)
    for col, name in zip(cols, names[:3]):
        item = result["market"].get(name, {})
        value = "暂无" if item.get("value") is None else f"{item['value']:.2f}"
        change = "暂无" if item.get("change_20d") is None else f"{item['change_20d']:+.2f}%"
        col.metric(name, value, change)
    cols = st.columns(3)
    for col, name in zip(cols, names[3:]):
        item = result["market"].get(name, {})
        value = "暂无" if item.get("value") is None else f"{item['value']:.2f}"
        change = "暂无" if item.get("change_20d") is None else f"{item['change_20d']:+.2f}%"
        col.metric(name, value, change)

    st.markdown("## 🏦 宏观政策")
    c1, c2 = st.columns(2)
    fed = result["macro"].get("联邦基金利率", {})
    sofr = result["macro"].get("SOFR", {})
    c1.metric("联邦基金利率", "暂无" if fed.get("value") is None else f"{fed['value']:.2f}%")
    c2.metric("SOFR", "暂无" if sofr.get("value") is None else f"{sofr['value']:.2f}%")

    st.markdown("## 🧭 市场风险状态")
    c1, c2 = st.columns(2)
    c1.metric("新闻风险评分", f"{result.get('risk_score', '暂无')}/100")
    c2.metric("数据置信度", f"{result.get('confidence', 0)}%")
    st.info("🧠 综合判断：" + str(result.get("conclusion", "暂无")))

    st.markdown("## 📰 重要财经情报")
    for item in result.get("news", [])[:12]:
        title = item.get("title", "")
        source = item.get("source", "")
        date = item.get("date", "")
        st.write(f"• **{title}**　`{source}`　{date}")

    with st.expander("🩺 财经数据源诊断", expanded=False):
        st.json(result.get("diagnostics") or {"status": "主要数据链路正常"})
    st.caption("研究定位：市场情报与宏观研究辅助，不构成单独交易指令。")
