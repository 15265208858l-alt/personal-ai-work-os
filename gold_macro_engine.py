# =========================================================
# 刘强 · Personal AI Work OS — Gold Macro Decision Engine V4.2
# =========================================================
from __future__ import annotations

import csv
import io
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from typing import Any

import requests

YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{}"
FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"
BLS = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
NEWS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
STOOQ = "https://stooq.com/q/l/?s=xauusd&i=d&f=sd2t2ohlcv&h&e=csv"
HEADERS = {"User-Agent": "Mozilla/5.0 LiuQiang-Personal-AI-Work-OS/4.2"}

# 国际黄金现货优先；只有现货失败才使用GC=F备用。
SPOT_SYMBOLS = ["XAUUSD=X", "GC=F"]
OTHER = {"dxy": "DX-Y.NYB", "us10y": "^TNX", "gld": "GLD"}
FRED_SERIES = {"us2y": "DGS2", "real10y": "DFII10", "breakeven10y": "T10YIE", "pce": "PCEPI", "core_pce": "PCEPILFE"}
BLS_SERIES = {"cpi": "CUSR0000SA0", "payroll": "CES0000000001", "unemployment": "LNS14000000"}
NEWS_QUERIES = [
    "gold Iran Israel Middle East conflict ceasefire sanctions",
    "gold Russia Ukraine geopolitics sanctions ceasefire",
    "gold central bank buying gold ETF flows safe haven",
]
FED_LOW, FED_HIGH = 3.50, 3.75
FED_NEXT = "2026-09-15/16"

# 2026-08-25官方最近公布值兜底；不是实时值，页面会标注日期和来源。
FALLBACK = {
    "us2y": (4.24, "2026-08-21", "FRED DGS2"),
    "real10y": (2.40, "2026-08-21", "FRED DFII10"),
    "breakeven10y": (2.34, "2026-08-21", "FRED T10YIE"),
    "core_pce_yoy": (3.30, "2026-06", "BEA/FRED PCEPILFE"),
}


def _get(url, **kwargs):
    return requests.get(url, headers=HEADERS, timeout=8, **kwargs)


def _retry(fn, attempts=2):
    last = None
    for i in range(attempts):
        try:
            return fn(), None
        except Exception as exc:
            last = f"{type(exc).__name__}: {exc}"
            if i < attempts - 1:
                time.sleep(0.4)
    return None, last


def _yahoo(symbol, range_="1y"):
    r = _get(YAHOO.format(requests.utils.quote(symbol, safe="")), params={"range": range_, "interval": "1d", "events": "history"})
    r.raise_for_status()
    result = ((r.json().get("chart") or {}).get("result") or [])
    if not result:
        raise RuntimeError(f"Yahoo无{symbol}数据")
    item = result[0]
    ts = item.get("timestamp") or []
    q = (((item.get("indicators") or {}).get("quote")) or [{}])[0]
    closes, vols = q.get("close") or [], q.get("volume") or []
    rows = [(t, v, vols[i] if i < len(vols) else None) for i, (t, v) in enumerate(zip(ts, closes)) if v is not None]
    if not rows:
        raise RuntimeError(f"Yahoo返回{symbol}空数据")
    return rows


def _stooq_spot():
    r = _get(STOOQ)
    r.raise_for_status()
    lines = [x.strip() for x in r.text.splitlines() if x.strip()]
    if len(lines) < 2:
        raise RuntimeError("Stooq无XAUUSD数据")
    header = [x.strip().upper() for x in lines[0].split(",")]
    vals = [x.strip() for x in lines[1].split(",")]
    row = dict(zip(header, vals))
    return float(row["CLOSE"]), row.get("DATE") or ""


def _spot_source():
    for symbol in SPOT_SYMBOLS:
        try:
            rows = _yahoo(symbol)
            source = "Yahoo XAU/USD现货" if symbol == "XAUUSD=X" else "Yahoo COMEX期金备用"
            return rows, source, symbol
        except Exception:
            continue
    close, date = _stooq_spot()
    return [(int(time.time()), close, None)], f"Stooq XAU/USD现货（{date}）", "XAUUSD-STOOQ"


def _fred(series_id):
    r = _get(FRED.format(series_id))
    r.raise_for_status()
    text = r.text.strip()
    if not text or "DATE" not in text.splitlines()[0].upper():
        raise RuntimeError(f"FRED无{series_id}数据")
    out = []
    for row in csv.DictReader(io.StringIO(text)):
        value = row.get(series_id) or row.get(series_id.upper())
        if value not in (None, "", "."):
            out.append((row.get("DATE"), float(value)))
    if not out:
        raise RuntimeError(f"FRED空数据:{series_id}")
    return out


def _bls(series_id, start_year, end_year):
    r = requests.post(BLS, json={"seriesid": [series_id], "startyear": str(start_year), "endyear": str(end_year)}, headers={**HEADERS, "Content-Type": "application/json"}, timeout=8)
    r.raise_for_status()
    series = ((r.json().get("Results") or {}).get("series")) or []
    if not series:
        raise RuntimeError(f"BLS无{series_id}数据")
    return series[0].get("data") or []


def _news(query, limit=6):
    r = _get(NEWS.format(query=requests.utils.quote(query, safe="")))
    r.raise_for_status(); root = ET.fromstring(r.text)
    return [{"title": (i.findtext("title") or "").strip(), "date": (i.findtext("pubDate") or "").strip(), "source": (i.findtext("source") or "Google News").strip(), "link": (i.findtext("link") or "").strip()} for i in root.findall("./channel/item")[:limit]]


def _pct(rows, days):
    if not rows or len(rows) <= days:
        return None
    a, b = rows[-1][1], rows[-1-days][1]
    return None if b in (None, 0) else (a / b - 1) * 100


def _trend(rows):
    if not rows or len(rows) < 60:
        return "数据不足"
    a = sum(x[1] for x in rows[-10:]) / 10; b = sum(x[1] for x in rows[-30:]) / 30; c = sum(x[1] for x in rows[-60:]) / 60; x = rows[-1][1]
    return "偏强" if x > a > b > c else "偏弱" if x < a < b < c else "震荡"


def _months(data):
    return [x for x in data if str(x.get("period", "")).startswith("M") and x.get("value") not in (None, "")]


def _latest_prev(data):
    rows = _months(data)
    if not rows:
        return None, None
    return {"year": rows[0].get("year"), "period": rows[0].get("period"), "value": float(rows[0]["value"])}, (float(rows[1]["value"]) if len(rows) > 1 else None)


def _cpi(data):
    latest, prev = _latest_prev(data); rows = _months(data)
    if latest is None:
        return {"index": None, "mom_pct": None, "yoy_pct": None, "period": None}
    yoy = (latest["value"] / float(rows[12]["value"]) - 1) * 100 if len(rows) >= 13 else None
    mom = None if prev in (None, 0) else (latest["value"] / prev - 1) * 100
    return {"index": latest["value"], "period": f"{latest.get('year','')}-{latest.get('period','')}", "mom_pct": mom, "yoy_pct": yoy}


def _latest(rows):
    return (rows[-1][1], rows[-1][0]) if rows else (None, None)


def _pce_yoy(rows):
    if not rows or len(rows) < 13:
        return None, None
    return (rows[-1][1] / rows[-13][1] - 1) * 100, rows[-1][0]


def _rate_proxy(us2y, us10y):
    if us2y is None: return None, "数据不足"
    if us2y >= 4.25: return 30, "偏鹰/高利率压力"
    if us2y <= 3.25: return 75, "偏鸽/降息预期较强"
    if us10y is not None and us10y < us2y: return 65, "增长担忧/曲线偏弱"
    return 50, "中性"


def _geo(headlines):
    if not headlines: return {"score": None, "level": "数据不足", "reason": "暂无足够新闻样本"}
    risk=["war","strike","attack","missile","sanction","conflict","tension","iran","israel","russia","ukraine"]; ease=["ceasefire","truce","peace","de-escalation","talks","agreement"]
    signal=0
    for row in headlines:
        text=row.get("title","").lower(); signal += sum(1 for x in risk if x in text); signal -= sum(1 for x in ease if x in text)
    score=max(0,min(100,50+signal*5)); return {"score":score,"level":"高" if score>=70 else "低" if score<=30 else "中","reason":"避险风险偏高" if score>=70 else "风险偏低" if score<=30 else "风险中性偏复杂"}


def _technical(rows):
    closes=[x[1] for x in rows]; n=len(closes)
    s20=min(closes[-min(20,n):]); s60=min(closes[-min(60,n):]); r20=max(closes[-min(20,n):]); r60=max(closes[-min(60,n):])
    return {"price": closes[-1], "support_short": s20, "support_mid": s60, "resistance_short": r20, "resistance_mid": r60, "ma20": sum(closes[-min(20,n):])/min(20,n), "ma60": sum(closes[-min(60,n):])/min(60,n), "distance_from_20d_high_pct": (closes[-1]/r20-1)*100 if r20 else None}


def _weighted(parts):
    valid=[x for x in parts if x[0] is not None]
    if not valid:return None,0,[]
    total=sum(w for _,w,_ in valid); score=round(sum(s*w for s,w,_ in valid)/total); reasons=[r for _,_,r in sorted(valid,key=lambda x:abs(x[0]-50),reverse=True) if r][:8]
    return score,round(total),reasons


def _scenario(score,trend,real10y,dxy20,technical):
    up,flat,down=35.,40.,25.
    if score is not None: up+=(score-50)*.65; down-=(score-50)*.40
    if trend=="偏强":up+=8;down-=5
    elif trend=="偏弱":up-=8;down+=7
    if real10y is not None and real10y<1.5:up+=5;down-=3
    if dxy20 is not None and dxy20<-1:up+=4;down-=2
    if technical.get("distance_from_20d_high_pct") is not None and technical["distance_from_20d_high_pct"]>-1:up-=3;down+=4
    up=max(5,min(80,up));down=max(5,min(80,down));flat=max(5,100-up-down);t=up+flat+down
    return {"上涨/延续":round(up/t*100),"震荡/高位消化":round(flat/t*100),"回撤/转弱":round(down/t*100)}


@lru_cache(maxsize=4)
def analyze_gold_market()->dict[str,Any]:
    started=time.time(); year=time.gmtime().tm_year; raw={}; errors={}; meta={}; jobs={}
    with ThreadPoolExecutor(max_workers=14) as pool:
        jobs[pool.submit(_retry,_spot_source,1)] = ("market","gold")
        for key,symbol in OTHER.items(): jobs[pool.submit(_retry,lambda s=symbol:_yahoo(s),1)] = ("market",key)
        for key,sid in FRED_SERIES.items(): jobs[pool.submit(_retry,lambda s=sid:_fred(s),1)] = ("fred",key)
        for key,sid in BLS_SERIES.items(): jobs[pool.submit(_retry,lambda s=sid:_bls(s,year-2,year),1)] = ("bls",key)
        for i,q in enumerate(NEWS_QUERIES): jobs[pool.submit(_retry,lambda q=q:_news(q),1)] = ("news",f"news_{i}")
        for future in as_completed(jobs):
            kind,key=jobs[future]
            try:
                value,err=future.result()
                if value is not None:
                    if kind=="market" and key=="gold": raw[key],meta["gold_source"],meta["gold_symbol"]=value
                    else: raw[key]=value
                elif err: errors[key]=err
            except Exception as exc: errors[key]=f"{type(exc).__name__}: {exc}"

    # 宏观关键值：FRED实时优先，失败使用官方最近公布值，并明确日期。
    macro={}
    for key in ("us2y","real10y","breakeven10y"):
        value,date=_latest(raw.get(key) or [])
        if value is None:
            value,date,source=FALLBACK[key]; macro[key]=value; meta[f"{key}_source"]=f"官方最近公布值备用｜{source}"; meta[f"{key}_date"]=date
        else:
            macro[key]=value; meta[f"{key}_source"]="FRED实时读取"; meta[f"{key}_date"]=date
    core_rows=raw.get("core_pce") or []; core_pce,pce_date=_pce_yoy(core_rows)
    if core_pce is None:
        core_pce,pce_date,source=FALLBACK["core_pce_yoy"]; meta["core_pce_source"]=f"官方最近公布值备用｜{source}"
    else: meta["core_pce_source"]="FRED PCEPILFE计算同比"
    meta["core_pce_date"]=pce_date

    gold=raw.get("gold") or []
    if not gold:
        return {"success":False,"agent":"gold_agent","version":"V4.2","error":"国际黄金现货数据暂时无法获取。","diagnostics":errors,"elapsed_seconds":round(time.time()-started,2)}
    dxy,us10y,gld=raw.get("dxy") or [],raw.get("us10y") or [],raw.get("gld") or []
    gold20=_pct(gold,20); dxy20=_pct(dxy,20) if dxy else None; y1020=_pct(us10y,20) if us10y else None; trend=_trend(gold); technical=_technical(gold)
    us2y,real10y,breakeven=macro["us2y"],macro["real10y"],macro["breakeven10y"]
    rate_score,rate_label=_rate_proxy(us2y,us10y[-1][1] if us10y else None)
    cpi=_cpi(raw.get("cpi") or []); payroll,prev_payroll=_latest_prev(raw.get("payroll") or []); unemployment,_=_latest_prev(raw.get("unemployment") or []); payroll_change=None if payroll is None or prev_payroll is None else payroll["value"]-prev_payroll
    headlines=sum([(raw.get("news_0") or []),(raw.get("news_1") or []),(raw.get("news_2") or [])],[]); geo=_geo(headlines)
    trend_score=75 if trend=="偏强" else 25 if trend=="偏弱" else 50
    dxy_score=None if dxy20 is None else max(20,min(80,50-dxy20*8)); yield_score=None if y1020 is None else max(20,min(80,50-y1020*6)); real_score=max(20,min(80,65-(real10y-1.5)*12)); pce_score=max(25,min(75,70-max(0,core_pce-2)*10)); emp_score=None if payroll_change is None or unemployment is None else (65 if payroll_change<0 or unemployment["value"]>=4.2 else 45)
    gld20=_pct(gld,20) if gld else None; etf_score=max(30,min(70,50-(gld20 or 0)*3)) if gld20 is not None else None
    score,confidence,reasons=_weighted([
        (trend_score,15,"黄金价格趋势偏强" if trend=="偏强" else "黄金趋势偏弱" if trend=="偏弱" else "黄金处于震荡"),
        (dxy_score,12,"美元20日走弱，利多黄金" if dxy20 is not None and dxy20<-1 else "美元走强，压制黄金" if dxy20 is not None and dxy20>1 else "美元方向中性"),
        (yield_score,10,"10Y收益率回落，利多黄金" if y1020 is not None and y1020<-2 else "10Y收益率上升，压制黄金" if y1020 is not None and y1020>2 else "10Y影响中性"),
        (real_score,15,f"实际10Y约{real10y:.2f}%"),(rate_score,10,f"利率环境：{rate_label}"),(pce_score,10,f"核心PCE同比约{core_pce:.2f}%"),
        (emp_score,8,"就业边际走弱，有利于宽松预期" if emp_score==65 else "就业仍有韧性，对降息形成约束" if emp_score==45 else "就业数据不足"),
        (geo["score"],5,"地缘风险提高避险需求" if geo["score"] is not None and geo["score"]>=70 else "地缘政治影响中性"),
        (75 if trend=="偏强" else 25 if trend=="偏弱" else 50,10,"技术趋势偏强" if trend=="偏强" else "技术趋势偏弱" if trend=="偏弱" else "技术趋势震荡"),
        (etf_score,5,"GLD价格动量为ETF情绪代理" if etf_score is not None else "ETF代理数据不足"),
    ])
    outlook="偏多" if score>=68 else "偏空" if score<=35 else "震荡"; scenario=_scenario(score,trend,real10y,dxy20,technical)
    risks=[]
    if real10y>2: risks.append("实际利率偏高，对黄金估值形成压力")
    if dxy20 is not None and dxy20>1: risks.append("美元持续走强")
    if y1020 is not None and y1020>2: risks.append("美国10Y收益率快速上升")
    if emp_score==45: risks.append("就业韧性可能使降息预期反复")
    if geo["score"] is not None and geo["score"]>=70: risks.append("地缘冲突升级可能推高油价和通胀")
    if gold20 is not None and gold20>10: risks.append("近20日涨幅较大，短期高位回撤风险较高")
    if technical.get("distance_from_20d_high_pct") is not None and technical["distance_from_20d_high_pct"]>-1: risks.append("价格接近20日高位，追涨性价比下降")
    conclusion="中期结构偏多，但价格已处强势区；持有优先，新增仓位等待回撤或实际利率继续回落确认。" if outlook=="偏多" and trend=="偏强" else "宏观偏多但趋势确认度一般；以持有为主，新增仓位分批并等待宏观催化。" if outlook=="偏多" else "宏观逆风增加；控制新增仓位，重点等待实际利率和美元压力缓和。" if outlook=="偏空" else "多空因素交织；等待PCE、Fed、就业及实际利率变化进一步确认方向。"
    return {"success":True,"agent":"gold_agent","version":"V4.2","market":{"gold":gold[-1][1],"gold_symbol":meta.get("gold_symbol","XAUUSD=X"),"gold_source":meta.get("gold_source","XAU/USD"),"gold_5d_pct":_pct(gold,5),"gold_20d_pct":gold20,"gold_trend":trend,"dxy":dxy[-1][1] if dxy else None,"dxy_20d_pct":dxy20,"us10y":us10y[-1][1] if us10y else None,"us10y_20d_pct":y1020,"us2y":us2y,"gld_20d_pct":gld20},"macro":{"fed":{"target_range":f"{FED_LOW:.2f}-{FED_HIGH:.2f}%","next_meeting":FED_NEXT,"expectation_proxy":rate_label,"score":rate_score,"method":"2Y美国国债收益率代理，不等同CME FedWatch概率"},"cpi":cpi,"pce":{"core_yoy":core_pce,"date":pce_date},"real_rates":{"real10y":real10y,"breakeven10y":breakeven},"employment":{"nonfarm_change_thousands":payroll_change,"unemployment_rate":unemployment["value"] if unemployment else None},"geopolitics":{"score":geo["score"],"level":geo["level"],"headlines":headlines[:12]}},"data_meta":meta,"technical":technical,"score":score,"confidence":confidence,"outlook":outlook,"conclusion":conclusion,"scenario":scenario,"reasons":reasons,"risk_flags":risks,"diagnostics":errors,"elapsed_seconds":round(time.time()-started,2),"limitations":["国际黄金主口径为XAU/USD现货；GC=F仅作备用。不同平台因报价源/时点/点差可能有小幅差异。","2Y、实际10Y、10Y通胀预期及核心PCE在实时接口失败时使用官方最近公布值，并显示日期。","Fed预期使用2Y收益率代理，不等同CME FedWatch概率；GLD为ETF情绪代理，不等同ETF份额净流入。"]}


def render_gold_result(result:dict[str,Any])->None:
    import streamlit as st
    st.divider(); st.markdown("# 🥇 黄金综合宏观研究 V4.2")
    if not result.get("success"):
        st.error(result.get("error","黄金宏观Agent执行失败")); st.json(result.get("diagnostics") or {}); return
    m=result.get("market") or {}; macro=result.get("macro") or {}; fed=macro.get("fed") or {}; cpi=macro.get("cpi") or {}; pce=macro.get("pce") or {}; emp=macro.get("employment") or {}; rr=macro.get("real_rates") or {}; geo=macro.get("geopolitics") or {}; tech=result.get("technical") or {}; meta=result.get("data_meta") or {}
    c1,c2,c3,c4=st.columns(4); c1.metric("国际黄金现货",f"{m.get('gold',0):.2f}"); c2.metric("美元指数","暂无" if m.get('dxy') is None else f"{m['dxy']:.2f}"); c3.metric("美国10Y","暂无" if m.get('us10y') is None else f"{m['us10y']:.2f}%"); c4.metric("黄金趋势",m.get('gold_trend','暂无'))
    st.caption(f"价格口径：{m.get('gold_source','XAU/USD')}｜标的：{m.get('gold_symbol','XAUUSD=X')}")
    c1,c2,c3,c4=st.columns(4); c1.metric("实际10Y","暂无" if rr.get('real10y') is None else f"{rr['real10y']:.2f}%"); c2.metric("10Y通胀预期","暂无" if rr.get('breakeven10y') is None else f"{rr['breakeven10y']:.2f}%"); c3.metric("2Y利率","暂无" if m.get('us2y') is None else f"{m['us2y']:.2f}%"); c4.metric("Fed预期代理",fed.get('expectation_proxy','数据不足'))
    c1,c2,c3,c4=st.columns(4); c1.metric("核心PCE同比","暂无" if pce.get('core_yoy') is None else f"{pce['core_yoy']:.2f}%"); c2.metric("CPI同比","暂无" if cpi.get('yoy_pct') is None else f"{cpi['yoy_pct']:.2f}%"); c3.metric("非农月度变化","暂无" if emp.get('nonfarm_change_thousands') is None else f"{emp['nonfarm_change_thousands']:+.0f}千"); c4.metric("失业率","暂无" if emp.get('unemployment_rate') is None else f"{emp['unemployment_rate']:.1f}%")
    c1,c2,c3=st.columns(3); c1.metric("综合宏观评分",f"{result.get('score','暂无')}/100"); c2.metric("数据置信度",f"{result.get('confidence',0)}%"); c3.metric("黄金20日涨跌","暂无" if m.get('gold_20d_pct') is None else f"{m['gold_20d_pct']:.2f}%")
    outlook=result.get('outlook','数据不足'); st.success(f"🟢 综合判断：{outlook}") if outlook=='偏多' else st.error(f"🔴 综合判断：{outlook}") if outlook=='偏空' else st.warning(f"🟡 综合判断：{outlook}")
    st.info(f"🧠 研究结论：{result.get('conclusion','暂无')}")
    st.markdown("### 📐 关键技术位"); c1,c2,c3,c4=st.columns(4); c1.metric("短线支撑","暂无" if tech.get('support_short') is None else f"{tech['support_short']:.2f}"); c2.metric("中期支撑","暂无" if tech.get('support_mid') is None else f"{tech['support_mid']:.2f}"); c3.metric("短线压力","暂无" if tech.get('resistance_short') is None else f"{tech['resistance_short']:.2f}"); c4.metric("中期压力","暂无" if tech.get('resistance_mid') is None else f"{tech['resistance_mid']:.2f}")
    sc=result.get('scenario') or {}; st.markdown("### 🧭 情景推演"); c1,c2,c3=st.columns(3); c1.metric('上涨/延续',f"{sc.get('上涨/延续','暂无')}%"); c2.metric('震荡/高位消化',f"{sc.get('震荡/高位消化','暂无')}%"); c3.metric('回撤/转弱',f"{sc.get('回撤/转弱','暂无')}%")
    st.markdown("### 🧠 核心驱动因素"); [st.write(f"• {r}") for r in result.get('reasons') or []]
    st.markdown("### 🚨 主要风险"); risks=result.get('risk_flags') or []; [st.warning(f"⚠️ {r}") for r in risks] if risks else st.success("✅ 当前未发现明显新增风险信号")
    st.markdown("### 🌍 地缘政治情报"); st.caption(f"风险等级：{geo.get('level','数据不足')}｜信号评分：{geo.get('score','暂无')}/100"); [st.write(f"• {r.get('title','')}") for r in (geo.get('headlines') or [])[:8]]
    with st.expander("🩺 数据源与日期诊断",expanded=False): st.json(meta)
    with st.expander("📐 研究口径与局限",expanded=False):
        for x in result.get('limitations') or []: st.write(f"• {x}")
        st.caption("数据来源：Yahoo Finance、Stooq现货兜底、FRED、美国BLS、Google News RSS。")
