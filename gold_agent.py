# =========================================================
# Personal AI Work OS
# Gold Macro Research Agent V2.0.1
# =========================================================
# 综合维度：黄金、美元、美国10Y、2Y利率预期代理、Fed政策状态、CPI、就业、地缘政治、趋势
# 数据源：Yahoo Finance、BLS Public API、Google News RSS；单项失败不影响整体研究。
# =========================================================

from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from typing import Any

import requests

_YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{}"
_BLS = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
HEADERS = {"User-Agent": "Mozilla/5.0 Personal-AI-Work-OS/2.0"}

SYMBOLS = {
    "gold": "GC=F",
    "dxy": "DX-Y.NYB",
    "us10y": "^TNX",
    "us2y": "^UST2Y",
}
BLS_SERIES = {
    "cpi": "CUUR0000SA0",
    "nonfarm": "CES0000000001",
    "unemployment": "LNS14000000",
}
NEWS_QUERIES = [
    "gold Iran sanctions Middle East war",
    "gold Russia Ukraine sanctions ceasefire",
    "gold geopolitics central bank conflict",
]

# 最新可验证的FOMC状态：2026-07-30生效目标区间3.50%-3.75%，下一次会议2026-09-15/16。
FED_TARGET_LOW = 3.50
FED_TARGET_HIGH = 3.75
FED_TARGET_MID = (FED_TARGET_LOW + FED_TARGET_HIGH) / 2
FED_NEXT_MEETING = "2026-09-15/16"


def _retry(fn, attempts=2):
    errors = []
    for i in range(attempts):
        try:
            return fn(), errors
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            if i < attempts - 1:
                time.sleep(0.5)
    return None, errors


def _yahoo(symbol, range_="1y"):
    url = _YAHOO.format(requests.utils.quote(symbol, safe=""))
    r = requests.get(url, params={"range": range_, "interval": "1d", "events": "history"}, headers=HEADERS, timeout=10)
    r.raise_for_status()
    result = r.json().get("chart", {}).get("result")
    if not result:
        raise RuntimeError(f"Yahoo无{symbol}数据")
    item = result[0]
    ts = item.get("timestamp") or []
    quote = (item.get("indicators", {}).get("quote") or [{}])[0]
    closes = quote.get("close") or []
    rows = [(a, b) for a, b in zip(ts, closes) if b is not None]
    if not rows:
        raise RuntimeError(f"Yahoo返回{symbol}空序列")
    return rows


def _bls(series_id, start_year, end_year):
    r = requests.post(_BLS, json={"seriesid": [series_id], "startyear": str(start_year), "endyear": str(end_year)}, headers={**HEADERS, "Content-Type": "application/json"}, timeout=10)
    r.raise_for_status()
    series = r.json().get("Results", {}).get("series") or []
    if not series:
        raise RuntimeError(f"BLS无{series_id}数据")
    return series[0].get("data") or []


def _news(query, limit=5):
    url = _NEWS_RSS.format(query=requests.utils.quote(query, safe=""))
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    rows = []
    for item in root.findall("./channel/item")[:limit]:
        rows.append({
            "title": (item.findtext("title") or "").strip(),
            "pub_date": (item.findtext("pubDate") or "").strip(),
            "source": (item.findtext("source") or "Google News").strip(),
        })
    return rows


def _pct(rows, days):
    if not rows or len(rows) <= days:
        return None
    latest, prev = rows[-1][1], rows[-1 - days][1]
    if prev in (None, 0):
        return None
    return (latest / prev - 1) * 100


def _trend(rows):
    if not rows or len(rows) < 60:
        return "数据不足"
    a = sum(v for _, v in rows[-10:]) / 10
    b = sum(v for _, v in rows[-30:]) / 30
    c = sum(v for _, v in rows[-60:]) / 60
    if rows[-1][1] > a > b > c:
        return "偏强"
    if rows[-1][1] < a < b < c:
        return "偏弱"
    return "震荡"


def _latest_bls(data):
    if not data:
        return None
    usable = [x for x in data if str(x.get("period", "")).startswith("M") and x.get("value") not in (None, "")]
    if not usable:
        return None
    x = usable[0]
    return {"year": x.get("year"), "period": x.get("period"), "value": float(x.get("value"))}


def _previous_bls(data):
    if not data:
        return None
    usable = [x for x in data if str(x.get("period", "")).startswith("M") and x.get("value") not in (None, "")]
    return float(usable[1]["value"]) if len(usable) >= 2 else None


def _geopolitics_score(headlines):
    if not headlines:
        return 50, ["暂无足够地缘政治新闻样本"]
    risk_words = ["war", "strike", "attack", "sanction", "missile", "tension", "conflict", "iran", "israel", "russia", "ukraine"]
    easing_words = ["ceasefire", "truce", "peace", "de-escalation", "talks", "agreement"]
    pressure = 0
    for h in headlines:
        text = h.get("title", "").lower()
        pressure += sum(1 for w in risk_words if w in text)
        pressure -= sum(1 for w in easing_words if w in text)
    score = max(0, min(100, 50 + pressure * 5))
    reason = "地缘政治风险偏高，避险需求增强" if score >= 65 else "地缘政治风险边际缓和" if score <= 35 else "地缘政治信号中性偏复杂"
    return score, [reason]


def _rate_expectation(us2y, us10y):
    if us2y is None:
        return {"label": "数据不足", "score": 50}
    if us2y >= 4.25:
        return {"label": "偏鹰/高利率预期", "score": 30}
    if us2y <= 3.25:
        return {"label": "偏鸽/降息预期较强", "score": 75}
    if us10y is not None and us10y < us2y:
        return {"label": "增长担忧/曲线偏弱", "score": 65}
    return {"label": "中性", "score": 50}


def _composite_score(gold_trend, dxy20, us10y20, rate_score, cpi_mom, payroll_delta, geop_score):
    score = 50
    reasons = []
    if gold_trend == "偏强": score += 12; reasons.append("黄金价格趋势偏强")
    elif gold_trend == "偏弱": score -= 12; reasons.append("黄金价格趋势偏弱")
    if dxy20 is not None:
        if dxy20 < -1: score += 10; reasons.append("美元走弱利多黄金")
        elif dxy20 > 1: score -= 10; reasons.append("美元走强压制黄金")
    if us10y20 is not None:
        if us10y20 < -2: score += 8; reasons.append("美国10Y收益率回落利多黄金")
        elif us10y20 > 2: score -= 8; reasons.append("美国10Y收益率上行压制黄金")
    score += int((rate_score - 50) * 0.25)
    if cpi_mom is not None:
        if cpi_mom < -0.2: score += 6; reasons.append("CPI边际降温，有利于降息预期")
        elif cpi_mom > 0.3: score += 2; reasons.append("通胀仍有黏性，黄金兼具抗通胀属性")
    if payroll_delta is not None:
        if payroll_delta < 0: score += 7; reasons.append("非农环比走弱，政策转松预期增强")
        elif payroll_delta > 0.2: score -= 4; reasons.append("就业仍有韧性，对降息形成约束")
    score += int((geop_score - 50) * 0.15)
    return max(0, min(100, score)), reasons


@lru_cache(maxsize=4)
def analyze_gold_market() -> dict[str, Any]:
    started = time.time()
    year = time.gmtime().tm_year
    raw = {}
    errors = {}
    jobs = {}
    with ThreadPoolExecutor(max_workers=10) as pool:
        for key, symbol in SYMBOLS.items():
            jobs[pool.submit(_retry, lambda symbol=symbol: _yahoo(symbol), 2)] = ("market", key)
        for key, series_id in BLS_SERIES.items():
            jobs[pool.submit(_retry, lambda series_id=series_id: _bls(series_id, year - 2, year), 2)] = ("macro", key)
        for idx, query in enumerate(NEWS_QUERIES):
            jobs[pool.submit(_retry, lambda query=query: _news(query, 5), 2)] = ("news", f"news_{idx}")
        for future in as_completed(jobs):
            kind, key = jobs[future]
            try:
                result, err = future.result()
                if result is not None:
                    raw[key] = result
                elif err:
                    errors[key] = err[-1]
            except Exception as exc:
                errors[key] = f"{type(exc).__name__}: {exc}"

    gold, dxy = raw.get("gold") or [], raw.get("dxy") or []
    us10y, us2y = raw.get("us10y") or [], raw.get("us2y") or []
    if not gold:
        return {"success": False, "agent": "gold_agent", "version": "V2.0.1", "error": "黄金价格数据暂时无法获取。", "diagnostics": errors, "elapsed_seconds": round(time.time()-started, 2)}

    cpi, nfp, unemp = raw.get("cpi") or [], raw.get("nonfarm") or [], raw.get("unemployment") or []
    cpi_latest, cpi_prev = _latest_bls(cpi), _previous_bls(cpi)
    nfp_latest, nfp_prev = _latest_bls(nfp), _previous_bls(nfp)
    unemp_latest = _latest_bls(unemp)
    cpi_mom = None if cpi_latest is None or cpi_prev in (None, 0) else (cpi_latest["value"] / cpi_prev - 1) * 100
    payroll_delta = None if nfp_latest is None or nfp_prev is None else (nfp_latest["value"] - nfp_prev) / 1000

    headlines = []
    for i in range(3):
        headlines.extend(raw.get(f"news_{i}") or [])
    geop_score, geop_reason = _geopolitics_score(headlines)
    rate = _rate_expectation(us2y[-1][1] if us2y else None, us10y[-1][1] if us10y else None)
    score, reasons = _composite_score(_trend(gold), _pct(dxy, 20) if dxy else None, _pct(us10y, 20) if us10y else None, rate["score"], cpi_mom, payroll_delta, geop_score)
    reasons.extend(geop_reason)
    outlook = "偏多" if score >= 70 else "偏空" if score <= 35 else "震荡"

    risk_flags = []
    if dxy and (_pct(dxy, 20) or 0) > 1: risk_flags.append("美元快速走强")
    if us10y and (_pct(us10y, 20) or 0) > 2: risk_flags.append("美国长端收益率快速上升")
    if payroll_delta is not None and payroll_delta > 0.2: risk_flags.append("就业仍偏强，降息预期可能反复")
    if geop_score >= 70: risk_flags.append("地缘冲突升级可能带来油价/通胀冲击")
    stance = "趋势偏多，但不建议追涨；优先等待回撤确认。" if outlook == "偏多" and _trend(gold) == "偏强" else "宏观环境偏利多，可继续持有，新增仓位宜分批。" if outlook == "偏多" else "宏观逆风增强，控制仓位，等待美元/利率改善。" if outlook == "偏空" else "多空因素交织，适合区间思维，等待关键宏观数据验证。"

    return {
        "success": True,
        "agent": "gold_agent",
        "version": "V2.0.1",
        "as_of": int(gold[-1][0]),
        "market": {"gold": gold[-1][1], "gold_5d_pct": _pct(gold, 5), "gold_20d_pct": _pct(gold, 20), "gold_trend": _trend(gold), "dxy": dxy[-1][1] if dxy else None, "dxy_20d_pct": _pct(dxy, 20) if dxy else None, "us10y": us10y[-1][1] if us10y else None, "us10y_20d_pct": _pct(us10y, 20) if us10y else None, "us2y": us2y[-1][1] if us2y else None},
        "macro": {
            "fed": {"target_range": f"{FED_TARGET_LOW:.2f}-{FED_TARGET_HIGH:.2f}%", "target_mid": FED_TARGET_MID, "next_meeting": FED_NEXT_MEETING, "expectation_proxy": rate["label"], "score": rate["score"], "method": "2Y美国国债收益率代理，不等同CME FedWatch概率"},
            "cpi": {"latest": cpi_latest, "mom_pct": cpi_mom},
            "employment": {"nonfarm": nfp_latest, "nonfarm_change_million": payroll_delta, "unemployment": unemp_latest},
            "geopolitics": {"score": geop_score, "headlines": headlines[:10]},
        },
        "score": score,
        "outlook": outlook,
        "stance": stance,
        "reasons": reasons[:10],
        "risk_flags": risk_flags,
        "diagnostics": errors,
        "elapsed_seconds": round(time.time() - started, 2),
        "limitations": ["Fed预期采用2Y美债代理而非CME概率；地缘政治采用新闻RSS风险信号；研究结果仅作辅助，不构成单一交易指令。"],
    }


def render_gold_result(result: dict[str, Any]) -> None:
    import streamlit as st
    st.divider()
    st.markdown("# 🥇 黄金综合宏观研究")
    if not result.get("success"):
        st.error(result.get("error", "黄金宏观Agent执行失败"))
        if result.get("diagnostics"):
            st.json(result["diagnostics"])
        return
    market = result.get("market") or {}
    macro = result.get("macro") or {}
    fed = macro.get("fed") or {}
    cpi = macro.get("cpi") or {}
    emp = macro.get("employment") or {}
    geo = macro.get("geopolitics") or {}

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("国际黄金", f"{market['gold']:.2f}")
    c2.metric("美元指数", "暂无" if market.get("dxy") is None else f"{market['dxy']:.2f}")
    c3.metric("美国10Y", "暂无" if market.get("us10y") is None else f"{market['us10y']:.2f}%")
    c4.metric("黄金趋势", market.get("gold_trend", "暂无"))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("2Y利率", "暂无" if market.get("us2y") is None else f"{market['us2y']:.2f}%")
    c2.metric("Fed预期代理", fed.get("expectation_proxy", "暂无"))
    c3.metric("Fed目标区间", fed.get("target_range", "暂无"))
    c4.metric("下次FOMC", fed.get("next_meeting", "暂无"))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CPI最新值", "暂无" if not cpi.get("latest") else f"{cpi['latest']['value']:.1f}")
    c2.metric("CPI环比", "暂无" if cpi.get("mom_pct") is None else f"{cpi['mom_pct']:.2f}%")
    c3.metric("最新非农", "暂无" if not emp.get("nonfarm") else f"{emp['nonfarm']['value']:.0f}千")
    c4.metric("失业率", "暂无" if not emp.get("unemployment") else f"{emp['unemployment']['value']:.1f}%")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("黄金20日涨跌", "暂无" if market.get("gold_20d_pct") is None else f"{market['gold_20d_pct']:.2f}%")
    c2.metric("美元20日涨跌", "暂无" if market.get("dxy_20d_pct") is None else f"{market['dxy_20d_pct']:.2f}%")
    c3.metric("10Y20日变化", "暂无" if market.get("us10y_20d_pct") is None else f"{market['us10y_20d_pct']:.2f}%")
    c4.metric("综合宏观评分", f"{result.get('score', '暂无')}/100")

    outlook = result.get("outlook", "暂无")
    if outlook == "偏多": st.success(f"🟢 综合判断：{outlook}")
    elif outlook == "偏空": st.error(f"🔴 综合判断：{outlook}")
    else: st.warning(f"🟡 综合判断：{outlook}")
    st.info("🧭 研究结论：" + str(result.get("stance", "暂无")))

    st.markdown("### 🧠 核心驱动因素")
    for reason in result.get("reasons") or []:
        st.write(f"• {reason}")

    if result.get("risk_flags"):
        st.markdown("### 🚨 主要风险")
        for item in result["risk_flags"]:
            st.warning("⚠️ " + item)

    st.markdown("### 🌍 地缘政治情报")
    st.caption(f"地缘政治风险评分：{geo.get('score', '暂无')}/100")
    for item in (geo.get("headlines") or [])[:8]:
        st.write(f"• {item.get('title', '')} — {item.get('source', 'News')}")

    with st.expander("🩺 黄金Agent数据诊断", expanded=False):
        if result.get("diagnostics"):
            st.json(result["diagnostics"])
        else:
            st.success("✅ 各主要数据链路本轮未记录失败")

    with st.expander("📚 研究口径说明", expanded=False):
        for item in result.get("limitations") or []:
            st.write("• " + item)
        st.caption("宏观数据：BLS；市场行情：Yahoo Finance；地缘政治：Google News RSS。")
