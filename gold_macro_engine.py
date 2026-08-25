# =========================================================
# Personal AI Work OS — Gold Macro Decision Engine V4.0.1
# =========================================================
# 关键修复：优先使用XAU/USD现货，GC=F仅作期金备份/对照；技术压力不再把当前价直接当压力。

from __future__ import annotations

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
HEADERS = {"User-Agent": "Mozilla/5.0 Personal-AI-Work-OS/4.0.1"}
SYMBOLS = {"gold_spot": "XAUUSD=X", "gold_futures": "GC=F", "dxy": "DX-Y.NYB", "us10y": "^TNX", "us2y": "^UST2Y", "gld": "GLD"}
BLS_SERIES = {"cpi": "CUSR0000SA0", "payroll": "CES0000000001", "unemployment": "LNS14000000"}
FRED_SERIES = {"pce": "PCEPI", "core_pce": "PCEPILFE", "real10y": "DFII10", "breakeven10y": "T10YIE"}
NEWS_QUERIES = [
    "gold Iran Israel Middle East conflict ceasefire sanctions",
    "gold Russia Ukraine geopolitics sanctions ceasefire",
    "gold central bank buying gold ETF flows safe haven",
]
FED_LOW, FED_HIGH = 3.50, 3.75
FED_NEXT = "2026-09-15/16"

def _retry(fn, attempts=2):
    errors=[]
    for i in range(attempts):
        try: return fn(), errors
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            if i < attempts-1: time.sleep(0.4*(i+1))
    return None, errors

def _yahoo(symbol, range_="1y"):
    r=requests.get(YAHOO.format(requests.utils.quote(symbol,safe="")),params={"range":range_,"interval":"1d","events":"history"},headers=HEADERS,timeout=10)
    r.raise_for_status(); result=r.json().get("chart",{}).get("result")
    if not result: raise RuntimeError(f"Yahoo无{symbol}数据")
    item=result[0]; ts=item.get("timestamp") or []; q=((item.get("indicators") or {}).get("quote") or [{}])[0]; closes=q.get("close") or []; vols=q.get("volume") or []
    rows=[(t,v,(vols[i] if i<len(vols) else None)) for i,(t,v) in enumerate(zip(ts,closes)) if v is not None]
    if not rows: raise RuntimeError(f"Yahoo返回{symbol}空数据")
    return rows

def _fred(sid,limit=120):
    r=requests.get(FRED.format(sid),headers=HEADERS,timeout=10); r.raise_for_status(); lines=r.text.strip().splitlines()
    if len(lines)<=1: raise RuntimeError(f"FRED无{sid}数据")
    rows=[]
    for line in lines[1:]:
        p=line.split(",",1)
        if len(p)!=2 or p[1] in ("","."): continue
        try: rows.append((p[0],float(p[1])))
        except ValueError: pass
    return rows[-limit:]

def _bls(sid,start_year,end_year):
    r=requests.post(BLS,json={"seriesid":[sid],"startyear":str(start_year),"endyear":str(end_year)},headers={**HEADERS,"Content-Type":"application/json"},timeout=10); r.raise_for_status(); series=r.json().get("Results",{}).get("series") or []
    if not series: raise RuntimeError(f"BLS无{sid}数据")
    return series[0].get("data") or []

def _news(q,limit=6):
    r=requests.get(NEWS.format(query=requests.utils.quote(q,safe="")),headers=HEADERS,timeout=10); r.raise_for_status(); root=ET.fromstring(r.text)
    return [{"title":(i.findtext("title") or "").strip(),"date":(i.findtext("pubDate") or "").strip(),"source":(i.findtext("source") or "Google News").strip(),"link":(i.findtext("link") or "").strip()} for i in root.findall("./channel/item")[:limit]]

def _pct(rows,days,value_index=1):
    if not rows or len(rows)<=days:return None
    a,b=rows[-1][value_index],rows[-1-days][value_index]
    return None if b in (None,0) else (a/b-1)*100

def _trend(rows):
    if not rows or len(rows)<60:return "数据不足"
    a=sum(v[1] for v in rows[-10:])/10; b=sum(v[1] for v in rows[-30:])/30; c=sum(v[1] for v in rows[-60:])/60; x=rows[-1][1]
    return "偏强" if x>a>b>c else "偏弱" if x<a<b<c else "震荡"

def _months(data): return [x for x in data if str(x.get("period","" )).startswith("M") and x.get("value") not in (None,"")]

def _latest_prev(data):
    rows=_months(data)
    if not rows:return None,None
    return {"year":rows[0].get("year"),"period":rows[0].get("period"),"value":float(rows[0]["value"])}, (float(rows[1]["value"]) if len(rows)>1 else None)

def _cpi(data):
    rows=_months(data)
    if not rows:return {"index":None,"mom_pct":None,"yoy_pct":None}
    latest=float(rows[0]["value"]); prev=float(rows[1]["value"]) if len(rows)>1 else None; yoy=(latest/float(rows[12]["value"])-1)*100 if len(rows)>=13 else None
    return {"index":latest,"period":f"{rows[0].get('year','')}-{rows[0].get('period','')}","mom_pct":None if prev in (None,0) else (latest/prev-1)*100,"yoy_pct":yoy}

def _latest_fred(rows): return rows[-1][1] if rows else None

def _rate_proxy(us2y,us10y):
    if us2y is None:return None,"数据不足"
    if us2y>=4.25:return 30,"偏鹰/高利率压力"
    if us2y<=3.25:return 75,"偏鸽/降息预期较强"
    if us10y is not None and us10y<us2y:return 65,"增长担忧/曲线偏弱"
    return 50,"中性"

def _geo(headlines):
    if not headlines:return {"score":None,"level":"数据不足","reason":"暂无足够新闻样本"}
    risk=["war","strike","attack","missile","sanction","conflict","tension","iran","israel","russia","ukraine"]; ease=["ceasefire","truce","peace","de-escalation","talks","agreement"]; signal=0
    for row in headlines:
        t=row.get("title","").lower(); signal+=sum(1 for x in risk if x in t); signal-=sum(1 for x in ease if x in t)
    score=max(0,min(100,50+signal*5)); return {"score":score,"level":"高" if score>=70 else "低" if score<=30 else "中","reason":"避险风险偏高" if score>=70 else "风险偏低" if score<=30 else "风险中性偏复杂"}

def _technical(rows):
    closes=[x[1] for x in rows]; last=closes[-1]
    # 排除最近3个交易日，避免“当前价=压力位”。
    base=closes[:-3] if len(closes)>63 else closes[:-1]
    short=base[-20:] if len(base)>=20 else base; mid=base[-60:] if len(base)>=60 else base
    s20=min(short) if short else None; s60=min(mid) if mid else None; r20=max(short) if short else None; r60=max(mid) if mid else None
    ma20=sum(closes[-20:])/20 if len(closes)>=20 else None; ma60=sum(closes[-60:])/60 if len(closes)>=60 else None
    return {"price":last,"support_short":s20,"support_mid":s60,"resistance_short":r20,"resistance_mid":r60,"ma20":ma20,"ma60":ma60,"distance_from_20d_high_pct":None if r20 is None else (last/r20-1)*100,"distance_from_20d_low_pct":None if s20 is None else (last/s20-1)*100}

def _weighted(parts):
    valid=[x for x in parts if x[0] is not None]
    if not valid:return None,0,[]
    total=sum(w for _,w,_ in valid); score=round(sum(s*w for s,w,_ in valid)/total); reasons=[r for _,_,r in sorted(valid,key=lambda x:abs(x[0]-50),reverse=True) if r][:8]
    return score,round(total),reasons

def _scenario(score,trend,real10y,dxy20,technical):
    up,flat,down=35.,40.,25.
    if score is not None: up+=(score-50)*.65; down-=(score-50)*.40
    if trend=="偏强": up+=8; down-=5
    elif trend=="偏弱": up-=8; down+=7
    if real10y is not None and real10y<1.5: up+=5; down-=3
    if dxy20 is not None and dxy20<-1: up+=4; down-=2
    if technical.get("distance_from_20d_high_pct") is not None and technical["distance_from_20d_high_pct"]>-1: up-=3; down+=4
    up=max(5,min(80,up)); down=max(5,min(80,down)); flat=max(5,100-up-down); tot=up+flat+down
    return {"上涨/延续":round(up/tot*100),"震荡/高位消化":round(flat/tot*100),"回撤/转弱":round(down/tot*100)}

@lru_cache(maxsize=4)
def analyze_gold_market()->dict[str,Any]:
    started=time.time(); year=time.gmtime().tm_year; raw={}; errors={}; jobs={}
    with ThreadPoolExecutor(max_workers=16) as pool:
        for key,symbol in SYMBOLS.items(): jobs[pool.submit(_retry,lambda s=symbol:_yahoo(s),2)]=("market",key)
        for key,sid in FRED_SERIES.items(): jobs[pool.submit(_retry,lambda sid=sid:_fred(sid),2)]=("fred",key)
        for key,sid in BLS_SERIES.items(): jobs[pool.submit(_retry,lambda sid=sid:_bls(sid,year-2,year),2)]=("bls",key)
        for i,q in enumerate(NEWS_QUERIES): jobs[pool.submit(_retry,lambda q=q:_news(q),2)]=( "news",f"news_{i}")
        for f in as_completed(jobs):
            kind,key=jobs[f]
            try:
                value,err=f.result()
                if value is not None: raw[key]=value
                elif err: errors[key]=err[-1]
            except Exception as exc: errors[key]=f"{type(exc).__name__}: {exc}"
    gold=raw.get("gold_spot") or raw.get("gold_futures") or []
    gold_source="spot" if raw.get("gold_spot") else "futures_fallback"
    futures=raw.get("gold_futures") or []
    if not gold:return {"success":False,"agent":"gold_agent","version":"V4.0.1","error":"黄金价格数据暂时无法获取。","diagnostics":errors,"elapsed_seconds":round(time.time()-started,2)}
    dxy,us10y,us2y,gld=raw.get("dxy") or [],raw.get("us10y") or [],raw.get("us2y") or [],raw.get("gld") or []
    dxy20=_pct(dxy,20) if dxy else None; y1020=_pct(us10y,20) if us10y else None; gold20=_pct(gold,20); trend=_trend(gold)
    real10y=_latest_fred(raw.get("real10y") or []); breakeven=_latest_fred(raw.get("breakeven10y") or []); pce=_latest_fred(raw.get("pce") or []); core_pce=_latest_fred(raw.get("core_pce") or [])
    cpi=_cpi(raw.get("cpi") or []); payroll,prev_payroll=_latest_prev(raw.get("payroll") or []); unemployment,_=_latest_prev(raw.get("unemployment") or []); payroll_change=None if not payroll or prev_payroll is None else payroll["value"]-prev_payroll
    rate_score,rate_label=_rate_proxy(us2y[-1][1] if us2y else None,us10y[-1][1] if us10y else None)
    headlines=sum([(raw.get("news_0") or []),(raw.get("news_1") or []),(raw.get("news_2") or [])],[]); geo=_geo(headlines); technical=_technical(gold)
    trend_score=75 if trend=="偏强" else 25 if trend=="偏弱" else 50 if trend=="震荡" else None; dxy_score=None if dxy20 is None else max(20,min(80,50-dxy20*8)); yield_score=None if y1020 is None else max(20,min(80,50-y1020*6)); real_score=None if real10y is None else max(20,min(80,65-(real10y-1.5)*12)); pce_score=None if core_pce is None else max(25,min(75,70-max(0,core_pce-2.0)*10)); emp_score=None if payroll_change is None or unemployment is None else (65 if payroll_change<0 or unemployment["value"]>=4.2 else 45)
    etf_score=None
    if gld:
        gld20=_pct(gld,20); etf_score=max(30,min(70,50-(gld20 or 0)*3)) if gld20 is not None else None
    tech_score=75 if trend=="偏强" else 25 if trend=="偏弱" else 50
    score,confidence,reasons=_weighted([(trend_score,15,"黄金价格趋势偏强" if trend=="偏强" else "黄金趋势偏弱" if trend=="偏弱" else "黄金处于震荡"),(dxy_score,12,"美元20日走弱，利多黄金" if dxy20 is not None and dxy20<-1 else "美元走强，压制黄金" if dxy20 is not None and dxy20>1 else "美元方向中性"),(yield_score,10,"10Y收益率回落，利多黄金" if y1020 is not None and y1020<-2 else "10Y收益率上升，压制黄金" if y1020 is not None and y1020>2 else "10Y影响中性"),(real_score,15,f"实际10Y约{real10y:.2f}%" if real10y is not None else "实际利率数据不足"),(rate_score,10,f"利率环境：{rate_label}" if rate_score is not None else "利率预期数据不足"),(pce_score,10,f"核心PCE约{core_pce:.2f}%" if core_pce is not None else "PCE数据不足"),(emp_score,8,"就业边际走弱，有利于宽松预期" if emp_score==65 else "就业仍有韧性，对降息形成约束" if emp_score==45 else "就业数据不足"),(geo["score"],5,"地缘风险提高避险需求" if geo["score"] is not None and geo["score"]>=70 else "地缘政治影响中性"),(tech_score,10,"技术趋势偏强" if trend=="偏强" else "技术趋势偏弱" if trend=="偏弱" else "技术趋势震荡"),(etf_score,5,"GLD价格动量为ETF情绪代理" if etf_score is not None else "ETF代理数据不足")])
    outlook="偏多" if score is not None and score>=68 else "偏空" if score is not None and score<=35 else "震荡" if score is not None else "数据不足"; scenario=_scenario(score,trend,real10y,dxy20,technical)
    risks=[]
    if real10y is not None and real10y>2.0:risks.append("实际利率偏高，对黄金估值形成压力")
    if dxy20 is not None and dxy20>1:risks.append("美元持续走强")
    if y1020 is not None and y1020>2:risks.append("美国10Y收益率快速上升")
    if emp_score==45:risks.append("就业韧性可能使降息预期反复")
    if geo["score"] is not None and geo["score"]>=70:risks.append("地缘冲突升级可能推高油价和通胀")
    if gold20 is not None and gold20>10:risks.append("近20日涨幅较大，短期高位回撤风险较高")
    if technical.get("distance_from_20d_high_pct") is not None and technical["distance_from_20d_high_pct"]>-1:risks.append("价格接近20日高位，追涨性价比下降")
    if outlook=="偏多" and trend=="偏强":conclusion="中期结构偏多，但价格已处强势区；持有优先，新增仓位等待回撤或实际利率继续回落确认。"
    elif outlook=="偏多":conclusion="宏观偏多但趋势确认度一般；以持有为主，新增仓位分批并等待宏观催化。"
    elif outlook=="偏空":conclusion="宏观逆风增加；控制新增仓位，重点等待实际利率和美元压力缓和。"
    else:conclusion="多空因素交织；等待PCE、Fed、就业及实际利率变化进一步确认方向。"
    return {"success":True,"agent":"gold_agent","version":"V4.0.1","as_of":int(gold[-1][0]),"market":{"gold":gold[-1][1],"gold_source":gold_source,"gold_futures":futures[-1][1] if futures else None,"gold_5d_pct":_pct(gold,5),"gold_20d_pct":gold20,"gold_trend":trend,"dxy":dxy[-1][1] if dxy else None,"dxy_20d_pct":dxy20,"us10y":us10y[-1][1] if us10y else None,"us10y_20d_pct":y1020,"us2y":us2y[-1][1] if us2y else None,"gld_20d_pct":_pct(gld,20) if gld else None},"macro":{"fed":{"target_range":f"{FED_LOW:.2f}-{FED_HIGH:.2f}%","next_meeting":FED_NEXT,"expectation_proxy":rate_label,"score":rate_score,"method":"2Y美债代理，不等同CME FedWatch概率"},"cpi":cpi,"pce":{"headline":pce,"core":core_pce},"real_rates":{"real10y":real10y,"breakeven10y":breakeven},"employment":{"nonfarm_change_thousands":payroll_change,"unemployment_rate":unemployment["value"] if unemployment else None},"geopolitics":{"score":geo["score"],"level":geo["level"],"headlines":headlines[:12]},"central_bank":{"status":"未接入实时央行购金数据库，本项不进入评分"}},"technical":technical,"score":score,"confidence":confidence,"outlook":outlook,"conclusion":conclusion,"scenario":scenario,"reasons":reasons,"risk_flags":risks,"diagnostics":errors,"elapsed_seconds":round(time.time()-started,2),"limitations":["黄金主价优先采用XAU/USD现货；若现货接口不可用才回退GC=F。GC=F与现货存在价差；Fed预期使用2Y利率代理而非CME概率；GLD为ETF情绪代理，不等同ETF份额净流入；央行购金尚未实时接入；地缘政治为新闻标题信号。"]}

def render_gold_result(result:dict[str,Any])->None:
    import streamlit as st
    st.divider(); st.markdown(f"# 🥇 黄金综合宏观研究 V{result.get('version','4.0')}")
    if not result.get("success"):
        st.error(result.get("error","黄金宏观Agent执行失败")); st.json(result.get("diagnostics") or {}); return
    m=result.get("market") or {}; macro=result.get("macro") or {}; fed=macro.get("fed") or {}; cpi=macro.get("cpi") or {}; pce=macro.get("pce") or {}; emp=macro.get("employment") or {}; rr=macro.get("real_rates") or {}; geo=macro.get("geopolitics") or {}; tech=result.get("technical") or {}
    c1,c2,c3,c4=st.columns(4); c1.metric("国际黄金现货",f"{m['gold']:.2f}"); c2.metric("美元指数","暂无" if m.get('dxy') is None else f"{m['dxy']:.2f}"); c3.metric("美国10Y","暂无" if m.get('us10y') is None else f"{m['us10y']:.2f}%"); c4.metric("黄金趋势",m.get('gold_trend','暂无'))
    if m.get('gold_futures') is not None: st.caption(f"COMEX期金参考：{m['gold_futures']:.2f}；与现货存在时点/合约价差，不混用作主价")
    c1,c2,c3,c4=st.columns(4); c1.metric("实际10Y","暂无" if rr.get('real10y') is None else f"{rr['real10y']:.2f}%"); c2.metric("10Y通胀预期","暂无" if rr.get('breakeven10y') is None else f"{rr['breakeven10y']:.2f}%"); c3.metric("2Y利率","暂无" if m.get('us2y') is None else f"{m['us2y']:.2f}%"); c4.metric("Fed预期代理",fed.get('expectation_proxy','数据不足'))
    c1,c2,c3,c4=st.columns(4); c1.metric("核心PCE","暂无" if pce.get('core') is None else f"{pce['core']:.2f}%"); c2.metric("CPI同比","暂无" if cpi.get('yoy_pct') is None else f"{cpi['yoy_pct']:.1f}%"); c3.metric("非农月度变化","暂无" if emp.get('nonfarm_change_thousands') is None else f"{emp['nonfarm_change_thousands']:+.0f}千"); c4.metric("失业率","暂无" if emp.get('unemployment_rate') is None else f"{emp['unemployment_rate']:.1f}%")
    c1,c2,c3=st.columns(3); c1.metric("综合宏观评分",f"{result.get('score','暂无')}/100"); c2.metric("数据置信度",f"{result.get('confidence',0)}%"); c3.metric("黄金20日涨跌","暂无" if m.get('gold_20d_pct') is None else f"{m['gold_20d_pct']:.2f}%")
    outlook=result.get('outlook','数据不足'); st.success(f"🟢 综合判断：{outlook}") if outlook=='偏多' else st.error(f"🔴 综合判断：{outlook}") if outlook=='偏空' else st.warning(f"🟡 综合判断：{outlook}")
    st.info(f"🧠 研究结论：{result.get('conclusion','暂无')}")
    st.markdown("### 📐 关键技术位"); c1,c2,c3,c4=st.columns(4); c1.metric("短线支撑", "暂无" if tech.get('support_short') is None else f"{tech['support_short']:.2f}"); c2.metric("中期支撑", "暂无" if tech.get('support_mid') is None else f"{tech['support_mid']:.2f}"); c3.metric("短线压力", "暂无" if tech.get('resistance_short') is None else f"{tech['resistance_short']:.2f}"); c4.metric("中期压力", "暂无" if tech.get('resistance_mid') is None else f"{tech['resistance_mid']:.2f}")
    sc=result.get('scenario') or {}; st.markdown("### 🧭 情景推演"); c1,c2,c3=st.columns(3); c1.metric('上涨/延续',f"{sc.get('上涨/延续','暂无')}%"); c2.metric('震荡/高位消化',f"{sc.get('震荡/高位消化','暂无')}%"); c3.metric('回撤/转弱',f"{sc.get('回撤/转弱','暂无')}%")
    st.markdown("### 🧠 核心驱动因素"); [st.write(f"• {r}") for r in result.get('reasons') or []]
    st.markdown("### 🚨 主要风险"); risks=result.get('risk_flags') or []; [st.warning(f"⚠️ {r}") for r in risks] if risks else st.success("✅ 当前未发现明显新增风险信号")
    st.markdown("### 🌍 地缘政治情报"); st.caption(f"风险等级：{geo.get('level','数据不足')}｜信号评分：{geo.get('score','暂无')}/100"); [st.write(f"• {r.get('title','')}") for r in (geo.get('headlines') or [])[:8]]
    with st.expander("🩺 数据源诊断",expanded=False): st.json(result.get('diagnostics') or {"status":"主要数据链路正常"})
    with st.expander("📐 研究口径与局限",expanded=False):
        for x in result.get('limitations') or []: st.write(f"• {x}")
        st.caption("数据来源：Yahoo Finance、FRED、美国BLS公开数据、Google News RSS。")
