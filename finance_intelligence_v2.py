# =========================================================
# 刘强 · Personal AI Work OS — Finance Intelligence Agent V2.0
# 权威优先：Fed/BLS/BEA/NY Fed + Reuters；聚合源仅作补充
# =========================================================
from __future__ import annotations

import email.utils
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from typing import Any

import requests

HEADERS = {"User-Agent": "Mozilla/5.0 LiuQiang-Personal-AI-Work-OS/2.0"}
YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{}"
FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"
NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

MARKETS = {
    "标普500": "^GSPC",
    "纳斯达克": "^IXIC",
    "黄金期货": "GC=F",
    "原油期货": "CL=F",
    "美元指数": "DX-Y.NYB",
    "美国10Y": "^TNX",
}
FRED_SERIES = {"联邦基金有效利率": "DFF", "SOFR": "SOFR", "2Y收益率": "DGS2"}

# 权威/专业来源优先级。Google News 仅用于补充发现，不进入核心风险评分。
NEWS_SOURCES = [
    ("Reuters", "site:reuters.com (Fed OR inflation OR PCE OR CPI OR jobs OR Treasury OR dollar OR markets OR gold OR oil OR Iran OR China)", 48),
    ("Federal Reserve", "site:federalreserve.gov FOMC OR Federal Reserve OR monetary policy", 72),
    ("BLS", "site:bls.gov CPI OR employment OR jobs OR PPI", 96),
    ("BEA", "site:bea.gov PCE OR GDP OR personal income", 120),
    ("U.S. Treasury", "site:home.treasury.gov Treasury OR sanctions OR buybacks OR debt", 120),
]

def _get(url, **kwargs):
    return requests.get(url, headers=HEADERS, timeout=8, **kwargs)

def _yahoo(symbol):
    r = _get(YAHOO.format(requests.utils.quote(symbol, safe="")), params={"range": "5d", "interval": "1d", "events": "history"})
    r.raise_for_status()
    result = ((r.json().get("chart") or {}).get("result") or [])
    if not result:
        raise RuntimeError(f"Yahoo无{symbol}数据")
    item = result[0]
    ts = item.get("timestamp") or []
    close = (((item.get("indicators") or {}).get("quote")) or [{}])[0].get("close") or []
    rows = [(t, v) for t, v in zip(ts, close) if v is not None]
    if not rows:
        raise RuntimeError(f"Yahoo返回{symbol}空数据")
    return rows

def _fred(series):
    r = _get(FRED.format(series))
    r.raise_for_status()
    rows = []
    for line in r.text.strip().splitlines()[1:]:
        parts = line.split(",", 1)
        if len(parts) == 2 and parts[1] not in ("", "."):
            try:
                rows.append((parts[0], float(parts[1])))
            except ValueError:
                pass
    if not rows:
        raise RuntimeError(f"FRED无{series}数据")
    return rows

def _rss(query, source, max_age_hours, limit=8):
    r = _get(NEWS_RSS.format(query=requests.utils.quote(query, safe="")))
    r.raise_for_status()
    root = ET.fromstring(r.text)
    now = time.time(); out = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        link = (item.findtext("link") or "").strip()
        source_text = (item.findtext("source") or source).strip()
        try:
            ts = email.utils.parsedate_to_datetime(pub).timestamp() if pub else 0
        except Exception:
            ts = 0
        age_h = max(0.0, (now - ts) / 3600) if ts else 99999.0
        if title and age_h <= max_age_hours:
            out.append({"title": title, "published": pub, "timestamp": ts, "age_hours": round(age_h, 1), "source": source_text, "link": link, "tier": "authoritative" if source in {"Federal Reserve", "BLS", "BEA", "U.S. Treasury"} else "professional"})
        if len(out) >= limit:
            break
    return out

def _pct(rows, days=20):
    if not rows or len(rows) <= days:
        return None
    a, b = rows[-1][1], rows[-1-days][1]
    return None if b in (None, 0) else (a / b - 1) * 100

def _latest(rows):
    return (rows[-1][1], rows[-1][0]) if rows else (None, None)

def _dedupe_news(items):
    seen = set(); out=[]
    for x in sorted(items, key=lambda z: z.get("timestamp", 0), reverse=True):
        key = x.get("title", "").lower().strip()
        if key and key not in seen:
            seen.add(key); out.append(x)
    return out

def _importance(item):
    text = item.get("title", "").lower()
    score = 0
    for word in ["fomc", "federal reserve", "rate", "cpi", "pce", "nonfarm", "jobs", "treasury", "sanctions", "iran", "china", "war", "tariff"]:
        if word in text:
            score += 8
    if item.get("tier") == "authoritative":
        score += 20
    elif item.get("tier") == "professional":
        score += 12
    if item.get("age_hours", 9999) <= 6:
        score += 10
    return min(100, score)

def _direction(title):
    t = title.lower()
    risk = ["war", "attack", "sanction", "tariff", "crisis", "conflict", "recession", "inflation"]
    easing = ["ceasefire", "truce", "de-escalation", "rate cut", "cuts rates", "lower rates"]
    tightening = ["rate hike", "raises rates", "higher for longer", "hawkish"]
    risk_n = sum(t.count(w) for w in risk); ease_n = sum(t.count(w) for w in easing); tight_n = sum(t.count(w) for w in tightening)
    if ease_n and not tight_n:
        return "偏宽松/风险缓和"
    if tight_n:
        return "偏紧/风险升温"
    if risk_n:
        return "风险升温"
    return "中性"

@lru_cache(maxsize=4)
def analyze_finance_market_v2() -> dict[str, Any]:
    started=time.time(); raw={}; errors={}; jobs={}
    with ThreadPoolExecutor(max_workers=12) as pool:
        for name,symbol in MARKETS.items():
            jobs[pool.submit(_yahoo, symbol)] = ("market", name)
        for name,series in FRED_SERIES.items():
            jobs[pool.submit(_fred, series)] = ("macro", name)
        for source, query, max_age in NEWS_SOURCES:
            jobs[pool.submit(_rss, query, source, max_age)] = ("news", source)
        for f in as_completed(jobs):
            kind,key=jobs[f]
            try: raw[key]=f.result()
            except Exception as exc: errors[key]=f"{type(exc).__name__}: {exc}"

    market={}
    for name in MARKETS:
        rows=raw.get(name) or []; value,date=_latest(rows)
        market[name]={"value":value,"date":date,"change_20d":_pct(rows),"source":"Yahoo Finance（日线快照，非交易所直连实时）" if value is not None else None}
    macro={}
    for name in FRED_SERIES:
        value,date=_latest(raw.get(name) or [])
        macro[name]={"value":value,"date":date,"source":"FRED官方数据" if value is not None else None}

    news=[]
    for source,_query,_max_age in NEWS_SOURCES:
        news.extend(raw.get(source) or [])
    news=_dedupe_news(news)
    for item in news:
        item["importance"]=_importance(item); item["direction"]=_direction(item["title"])
    news=news[:24]

    # 核心结论只使用专业/权威来源；新闻聚合不影响核心风险分。
    authoritative=[x for x in news if x.get("tier")=="authoritative"]
    professional=[x for x in news if x.get("tier")=="professional"]
    risk_score=50
    if any("inflation" in x["title"].lower() or "cpi" in x["title"].lower() or "pce" in x["title"].lower() for x in news): risk_score += 5
    if any(x["direction"]=="偏紧/风险升温" for x in news): risk_score += 10
    if any(x["direction"]=="偏宽松/风险缓和" for x in news): risk_score -= 10
    risk_score=max(0,min(100,risk_score))
    confidence=max(0,min(100,100-len(errors)*12))
    if len(authoritative)+len(professional)<3: confidence=max(0,confidence-15)

    return {"success":True,"agent":"finance_intelligence_agent","version":"V2.0","as_of":int(time.time()),"market":market,"macro":macro,"news":news,"risk_score":risk_score,"confidence":confidence,"authoritative_news_count":len(authoritative),"professional_news_count":len(professional),"conclusion":"财经数据以官方宏观源和Reuters专业新闻为主；市场行情为Yahoo日线快照，不能视为交易所实时成交价。","diagnostics":errors,"elapsed_seconds":round(time.time()-started,2),"data_policy":"核心结论仅使用权威/专业来源；普通聚合源不进入核心评分。新闻按发布时间过滤，避免陈旧消息混入。"}

def render_finance_result_v2(result: dict[str, Any]) -> None:
    import streamlit as st
    st.divider(); st.markdown("# 📰 全球财经情报与宏观研究 V2.0")
    if not result.get("success"):
        st.error(result.get("error","财经情报Agent执行失败")); st.json(result.get("diagnostics") or {}); return
    st.markdown("### 🌍 核心市场（Yahoo日线快照）")
    names=list(MARKETS)
    cols=st.columns(3)
    for col,name in zip(cols,names[:3]):
        item=result["market"].get(name,{})
        col.metric(name,"暂无" if item.get("value") is None else f"{item['value']:.2f}","暂无" if item.get("change_20d") is None else f"{item['change_20d']:+.2f}%")
    cols=st.columns(3)
    for col,name in zip(cols,names[3:]):
        item=result["market"].get(name,{})
        col.metric(name,"暂无" if item.get("value") is None else f"{item['value']:.2f}","暂无" if item.get("change_20d") is None else f"{item['change_20d']:+.2f}%")
    st.markdown("### 🏦 官方宏观数据")
    c1,c2,c3=st.columns(3)
    for col,name in zip((c1,c2,c3),list(FRED_SERIES)):
        item=result["macro"].get(name,{})
        col.metric(name,"暂无" if item.get("value") is None else f"{item['value']:.2f}")
        if item.get("date"): col.caption(f"数据日期：{item['date']}｜FRED")
    st.markdown("### 📰 权威/专业新闻")
    st.caption(f"权威来源：{result.get('authoritative_news_count',0)} 条｜专业来源：{result.get('professional_news_count',0)} 条｜新闻仅纳入最近窗口")
    for item in result.get("news",[])[:15]:
        badge="🔴 权威" if item.get("tier")=="authoritative" else "🟠 Reuters"
        st.write(f"{badge} **{item.get('title','')}** · {item.get('source','')} · {item.get('published','')}")
    st.markdown("### 🧭 综合判断")
    c1,c2=st.columns(2); c1.metric("风险状态",f"{result.get('risk_score','暂无')}/100"); c2.metric("数据置信度",f"{result.get('confidence',0)}%")
    st.info(result.get("conclusion","暂无"))
    with st.expander("🩺 数据源与时效诊断",expanded=False):
        st.json({"diagnostics":result.get("diagnostics") or {"status":"主要数据链路正常"},"data_policy":result.get("data_policy"),"as_of":result.get("as_of")})
