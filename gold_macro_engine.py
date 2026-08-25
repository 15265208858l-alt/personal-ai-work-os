from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from typing import Any

import requests

YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{}"
BLS = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
NEWS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
HEADERS = {"User-Agent": "Mozilla/5.0 Personal-AI-Work-OS/3.0"}
SYMBOLS = {"gold": "GC=F", "dxy": "DX-Y.NYB", "us10y": "^TNX", "us2y": "^UST2Y"}
BLS_SERIES = {"cpi": "CUSR0000SA0", "payroll": "CES0000000001", "unemployment": "LNS14000000"}
NEWS_QUERIES = [
    "gold Iran Israel Middle East conflict ceasefire sanctions",
    "gold Russia Ukraine geopolitics sanctions ceasefire",
    "gold central bank purchases safe haven geopolitics",
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


def _yahoo(symbol):
    url=YAHOO.format(requests.utils.quote(symbol, safe=""))
    r=requests.get(url,params={"range":"1y","interval":"1d","events":"history"},headers=HEADERS,timeout=10)
    r.raise_for_status(); result=r.json().get("chart",{}).get("result")
    if not result: raise RuntimeError(f"Yahoo无{symbol}数据")
    item=result[0]; ts=item.get("timestamp") or []; close=((item.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
    rows=[(t,v) for t,v in zip(ts,close) if v is not None]
    if not rows: raise RuntimeError(f"Yahoo返回{symbol}空数据")
    return rows


def _bls(series_id, start_year, end_year):
    r=requests.post(BLS,json={"seriesid":[series_id],"startyear":str(start_year),"endyear":str(end_year)},headers={**HEADERS,"Content-Type":"application/json"},timeout=10)
    r.raise_for_status(); series=r.json().get("Results",{}).get("series") or []
    if not series: raise RuntimeError(f"BLS无{series_id}数据")
    return series[0].get("data") or []


def _news(query, limit=6):
    r=requests.get(NEWS.format(query=requests.utils.quote(query,safe="")),headers=HEADERS,timeout=10); r.raise_for_status()
    root=ET.fromstring(r.text); rows=[]
    for item in root.findall("./channel/item")[:limit]:
        rows.append({"title":(item.findtext("title") or "").strip(),"date":(item.findtext("pubDate") or "").strip(),"source":(item.findtext("source") or "Google News").strip(),"link":(item.findtext("link") or "").strip()})
    return rows


def _pct(rows, days):
    if not rows or len(rows)<=days:return None
    a,b=rows[-1][1],rows[-1-days][1]
    return None if b in (None,0) else (a/b-1)*100


def _trend(rows):
    if not rows or len(rows)<60:return "数据不足"
    a=sum(v for _,v in rows[-10:])/10; b=sum(v for _,v in rows[-30:])/30; c=sum(v for _,v in rows[-60:])/60; x=rows[-1][1]
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


def _rate_proxy(us2y,us10y):
    if us2y is None:return None,"数据不足"
    if us2y>=4.25:return 30,"偏鹰/高利率压力"
    if us2y<=3.25:return 75,"偏鸽/降息预期较强"
    if us10y is not None and us10y<us2y:return 65,"增长担忧/曲线偏弱"
    return 50,"中性"


def _geo(headlines):
    if not headlines:return {"score":None,"level":"数据不足","reason":"暂无足够新闻样本"}
    risk=["war","strike","attack","missile","sanction","conflict","tension","iran","israel","russia","ukraine"]; ease=["ceasefire","truce","peace","de-escalation","talks","agreement"]
    signal=0
    for row in headlines:
        text=row.get("title","").lower(); signal += sum(1 for x in risk if x in text); signal -= sum(1 for x in ease if x in text)
    score=max(0,min(100,50+signal*5)); return {"score":score,"level":"高" if score>=70 else "低" if score<=30 else "中","reason":"避险风险偏高" if score>=70 else "风险偏低" if score<=30 else "风险中性偏复杂"}


def _weighted(parts):
    valid=[x for x in parts if x[0] is not None]
    if not valid:return None,0,[]
    total=sum(w for _,w,_ in valid); score=round(sum(s*w for s,w,_ in valid)/total); reasons=[r for s,w,r in sorted(valid,key=lambda x:abs(x[0]-50),reverse=True) if r][:8]
    return score,round(total),reasons


def _scenario(score,trend,dxy20,y10):
    up,flat,down=35.,40.,25.
    if score is not None: up+=(score-50)*.65; down-=(score-50)*.4
    if trend=="偏强": up+=8; down-=5
    elif trend=="偏弱": up-=8; down+=7
    if dxy20 is not None and dxy20<-1:up+=5;down-=3
    if y10 is not None and y10>2:up-=4;down+=5
    up=max(5,min(80,up));down=max(5,min(80,down));flat=max(5,100-up-down);tot=up+flat+down
    return {"上涨/延续":round(up/tot*100),"震荡/高位消化":round(flat/tot*100),"回撤/转弱":round(down/tot*100)}


@lru_cache(maxsize=4)
def analyze_gold_market()->dict[str,Any]:
    started=time.time(); year=time.gmtime().tm_year; raw={}; errors={}; futures={}
    with ThreadPoolExecutor(max_workers=10) as pool:
        for k,s in SYMBOLS.items(): futures[pool.submit(_retry,lambda s=s:_yahoo(s),2)]=k
        for k,s in BLS_SERIES.items(): futures[pool.submit(_retry,lambda s=s:_bls(s,year-2,year),2)]=k
        for i,q in enumerate(NEWS_QUERIES): futures[pool.submit(_retry,lambda q=q:_news(q),2)]=f"news_{i}"
        for f in as_completed(futures):
            k=futures[f]
            try:
                v,e=f.result()
                if v is not None:raw[k]=v
                elif e:errors[k]=e[-1]
            except Exception as exc:errors[k]=f"{type(exc).__name__}: {exc}"
    gold=raw.get("gold") or []
    if not gold:return {"success":False,"agent":"gold_agent","version":"V3.0","error":"黄金价格数据暂时无法获取。","diagnostics":errors,"elapsed_seconds":round(time.time()-started,2)}
    dxy,us10y,us2y=raw.get("dxy") or [],raw.get("us10y") or [],raw.get("us2y") or []; gold20=_pct(gold,20); dxy20=_pct(dxy,20) if dxy else None; y1020=_pct(us10y,20) if us10y else None; trend=_trend(gold)
    rate_score,rate_label=_rate_proxy(us2y[-1][1] if us2y else None,us10y[-1][1] if us10y else None); cpi=_cpi(raw.get("cpi") or []); payroll,prev_payroll=_latest_prev(raw.get("payroll") or []); unemployment,_=_latest_prev(raw.get("unemployment") or []); payroll_change=None if not payroll or prev_payroll is None else payroll["value"]-prev_payroll
    headlines=sum([(raw.get("news_0") or []),(raw.get("news_1") or []),(raw.get("news_2") or [])],[]); geo=_geo(headlines)
    trend_score=75 if trend=="偏强" else 25 if trend=="偏弱" else 50 if trend=="震荡" else None; dxy_score=None if dxy20 is None else max(20,min(80,50-dxy20*8)); y_score=None if y1020 is None else max(20,min(80,50-y1020*6)); cpi_score=None if cpi["yoy_pct"] is None else max(25,min(75,70-max(0,cpi["yoy_pct"]-2)*8)); emp_score=None if payroll_change is None or unemployment is None else (65 if payroll_change<0 or unemployment["value"]>=4.2 else 45)
    score,confidence,reasons=_weighted([(trend_score,20,"黄金价格趋势偏强" if trend=="偏强" else "黄金趋势偏弱" if trend=="偏弱" else "黄金处于震荡"),(dxy_score,15,"美元20日走弱，利多黄金" if dxy20 is not None and dxy20<-1 else "美元走强，压制黄金" if dxy20 is not None and dxy20>1 else "美元方向中性"),(y_score,15,"10Y收益率回落，利多黄金" if y1020 is not None and y1020<-2 else "10Y收益率上升，压制黄金" if y1020 is not None and y1020>2 else "10Y影响中性"),(rate_score,15,f"利率环境：{rate_label}"),(cpi_score,10,f"CPI同比约{cpi['yoy_pct']:.1f}%" if cpi['yoy_pct'] is not None else "CPI数据不足"),(emp_score,10,"就业边际走弱，有利于宽松预期" if emp_score==65 else "就业仍有韧性，对降息形成约束" if emp_score==45 else "就业数据不足"),(geo['score'],15,"地缘政治风险偏高，提升避险需求" if geo['score'] is not None and geo['score']>=70 else "地缘政治影响中性")])
    outlook="偏多" if score is not None and score>=68 else "偏空" if score is not None and score<=35 else "震荡" if score is not None else "数据不足"; scenario=_scenario(score,trend,dxy20,y1020)
    risks=[]
    if dxy20 is not None and dxy20>1: risks.append("美元持续走强")
    if y1020 is not None and y1020>2: risks.append("美国10Y收益率快速上升")
    if emp_score==45: risks.append("就业韧性可能让降息预期反复")
    if geo['score'] is not None and geo['score']>=70: risks.append("地缘冲突升级可能推高油价和通胀")
    if gold20 is not None and gold20>10: risks.append("近20日涨幅较大，短期高位回撤风险较高")
    if outlook=="偏多" and trend=="偏强": conclusion="中期结构偏多，但短期涨幅较大；优先持有，新增仓位等回撤或宏观确认，不追涨。"
    elif outlook=="偏多": conclusion="宏观偏多，但价格趋势确认度一般；持有优先，新增仓位分批。"
    elif outlook=="偏空": conclusion="宏观逆风增加；控制新增仓位，等待美元与利率压力缓和。"
    else: conclusion="多空因素交织；等待通胀、Fed与就业的新信息确认方向。"
    return {"success":True,"agent":"gold_agent","version":"V3.0","as_of":int(gold[-1][0]),"market":{"gold":gold[-1][1],"gold_5d_pct":_pct(gold,5),"gold_20d_pct":gold20,"gold_trend":trend,"dxy":dxy[-1][1] if dxy else None,"dxy_20d_pct":dxy20,"us10y":us10y[-1][1] if us10y else None,"us10y_20d_pct":y1020,"us2y":us2y[-1][1] if us2y else None},"macro":{"fed":{"target_range":f"{FED_LOW:.2f}-{FED_HIGH:.2f}%","next_meeting":FED_NEXT,"expectation_proxy":rate_label,"score":rate_score,"method":"2Y美债收益率代理，不等同CME FedWatch概率"},"cpi":cpi,"employment":{"nonfarm_change_thousands":payroll_change,"latest_payroll_thousands":payroll['value'] if payroll else None,"unemployment_rate":unemployment['value'] if unemployment else None},"geopolitics":{"score":geo['score'],"level":geo['level'],"headlines":headlines[:12]}},"score":score,"confidence":confidence,"outlook":outlook,"conclusion":conclusion,"scenario":scenario,"reasons":reasons,"risk_flags":risks,"diagnostics":errors,"elapsed_seconds":round(time.time()-started,2),"limitations":["Fed预期使用2Y利率代理而非CME概率；地缘政治为新闻标题风险信号；本系统用于研究辅助，不构成单独交易指令。"]}


def render_gold_result(result:dict[str,Any])->None:
    import streamlit as st
    st.divider();st.markdown("# 🥇 黄金综合宏观研究")
    if not result.get("success"):
        st.error(result.get("error","黄金宏观Agent执行失败"));st.json(result.get("diagnostics") or {});return
    m=result.get("market") or {}; macro=result.get("macro") or {}; fed=macro.get("fed") or {}; cpi=macro.get("cpi") or {}; emp=macro.get("employment") or {}; geo=macro.get("geopolitics") or {}
    c1,c2,c3,c4=st.columns(4);c1.metric("国际黄金",f"{m['gold']:.2f}");c2.metric("美元指数","暂无" if m.get('dxy') is None else f"{m['dxy']:.2f}");c3.metric("美国10Y","暂无" if m.get('us10y') is None else f"{m['us10y']:.2f}%");c4.metric("黄金趋势",m.get('gold_trend','暂无'))
    c1,c2,c3,c4=st.columns(4);c1.metric("2Y利率","暂无" if m.get('us2y') is None else f"{m['us2y']:.2f}%");c2.metric("Fed预期代理",fed.get('expectation_proxy','数据不足'));c3.metric("Fed目标区间",fed.get('target_range','暂无'));c4.metric("下次FOMC",fed.get('next_meeting','暂无'))
    c1,c2,c3,c4=st.columns(4);c1.metric("CPI同比","暂无" if cpi.get('yoy_pct') is None else f"{cpi['yoy_pct']:.1f}%");c2.metric("CPI环比","暂无" if cpi.get('mom_pct') is None else f"{cpi['mom_pct']:.1f}%");c3.metric("非农月度变化","暂无" if emp.get('nonfarm_change_thousands') is None else f"{emp['nonfarm_change_thousands']:+.0f}千");c4.metric("失业率","暂无" if emp.get('unemployment_rate') is None else f"{emp['unemployment_rate']:.1f}%")
    c1,c2,c3=st.columns(3);c1.metric("黄金20日涨跌","暂无" if m.get('gold_20d_pct') is None else f"{m['gold_20d_pct']:.2f}%");c2.metric("美元20日涨跌","暂无" if m.get('dxy_20d_pct') is None else f"{m['dxy_20d_pct']:.2f}%");c3.metric("综合宏观评分",f"{result.get('score','暂无')}/100")
    outlook=result.get('outlook','数据不足');st.success(f"🟢 综合判断：{outlook}") if outlook=='偏多' else st.error(f"🔴 综合判断：{outlook}") if outlook=='偏空' else st.warning(f"🟡 综合判断：{outlook}")
    st.info(f"🧠 研究结论：{result.get('conclusion','暂无')}｜数据置信度：{result.get('confidence',0)}%")
    sc=result.get('scenario') or {};st.markdown("### 🧭 情景推演");c1,c2,c3=st.columns(3);c1.metric('上涨/延续',f"{sc.get('上涨/延续','暂无')}%");c2.metric('震荡/高位消化',f"{sc.get('震荡/高位消化','暂无')}%");c3.metric('回撤/转弱',f"{sc.get('回撤/转弱','暂无')}%")
    st.markdown("### 🧠 核心驱动因素");[st.write(f"• {r}") for r in result.get('reasons') or []]
    st.markdown("### 🚨 主要风险");risks=result.get('risk_flags') or [];[st.warning(f"⚠️ {r}") for r in risks] if risks else st.success("✅ 当前未发现明显新增风险信号")
    st.markdown("### 🌍 地缘政治情报");st.caption(f"风险等级：{geo.get('level','数据不足')}｜信号评分：{geo.get('score','暂无')}/100");[st.write(f"• {r.get('title','')}") for r in (geo.get('headlines') or [])[:8]]
    with st.expander("🩺 黄金Agent数据诊断",expanded=False):st.json(result.get('diagnostics') or {"status":"主要数据链路正常"})
    with st.expander("📐 研究口径与局限",expanded=False):
        for x in result.get('limitations') or []:st.write(f"• {x}")
        st.caption("数据来源：Yahoo Finance、美国BLS公开数据、Google News RSS。")
