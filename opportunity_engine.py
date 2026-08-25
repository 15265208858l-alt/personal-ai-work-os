# 刘强 · Personal AI Work OS — Opportunity Engine V3.0
from __future__ import annotations
from typing import Any

ASSETS=["黄金","美股","美债","美元","原油"]

def _num(v):
    try: return float(v) if v is not None else None
    except Exception: return None

def _asset(f,a): return f.get("market",{}).get(a,{})

def _score(asset,f):
    m,macro,news=f.get("market",{}),f.get("macro",{}),f.get("news",[])
    s=50; evidence=[]; risks=[]; triggers=[]
    dxy=_num(_asset(f,"美元指数").get("change_20d")); y10=_num(_asset(f,"美国10Y").get("change_20d")); spx=_num(_asset(f,"标普500").get("change_20d")); gold=_num(_asset(f,"黄金期货").get("change_20d")); oil=_num(_asset(f,"原油期货").get("change_20d")); y2=_num(macro.get("2Y收益率",{}).get("value"))
    trusted=[x for x in news if x.get("tier") in {"authoritative","professional"}]
    text=" ".join((x.get("title") or "").lower() for x in trusted[:20])
    if asset=="黄金":
        if dxy is not None and dxy<-1: s+=12; evidence.append("美元20日走弱"); triggers.append("若美元继续走弱，黄金宏观支撑延续")
        if y10 is not None and y10<-1: s+=10; evidence.append("10Y收益率20日回落"); triggers.append("若实际利率继续下降，黄金上行条件改善")
        if y2 is not None and y2>=4: s-=6; risks.append("2Y仍高，降息交易未完全确认"); triggers.append("若2Y明显上升，黄金承压")
        if gold is not None and gold>10: s-=10; risks.append("近20日涨幅较大，追涨风险高")
        if any(k in text for k in ["iran","war","attack","sanction","conflict"]): s+=7; evidence.append("权威/专业消息仍包含地缘风险因素")
    elif asset=="美股":
        if spx is not None and spx>2: s+=8; evidence.append("标普20日趋势偏强")
        if y10 is not None and y10>2: s-=10; risks.append("10Y上行压制估值")
        if y2 is not None and y2>=4.25: s-=6; risks.append("2Y利率偏高")
        if any(k in text for k in ["recession","tariff","crisis"]): s-=6; risks.append("宏观风险可能放大波动")
    elif asset=="美债":
        if y10 is not None and y10<-1: s+=12; evidence.append("10Y收益率回落利于债券价格")
        if y10 is not None and y10>2: s-=12; risks.append("10Y收益率上行压制债券价格")
        if y2 is not None and y2>=4.25: s-=4; risks.append("短端利率仍高")
    elif asset=="美元":
        if dxy is not None and dxy>1: s+=10; evidence.append("美元20日走强")
        if dxy is not None and dxy<-1: s-=10; risks.append("美元20日走弱")
    elif asset=="原油":
        if oil is not None and oil>3: s+=8; evidence.append("原油20日趋势偏强")
        if oil is not None and oil<-3: s-=8; risks.append("原油20日趋势偏弱")
        if any(k in text for k in ["iran","war","attack","sanction"]): s+=8; evidence.append("地缘风险可能抬升原油风险溢价")
    s=max(0,min(100,round(s)))
    direction="偏多" if s>=62 else "偏空" if s<=38 else "震荡"
    level="⭐⭐⭐⭐⭐" if s>=80 else "⭐⭐⭐⭐" if s>=70 else "⭐⭐⭐" if s>=60 else "⭐⭐" if s>=45 else "⭐"
    action="重点关注，等待触发条件后分批布局" if s>=70 else "观察，等待价格/宏观信号确认" if s>=60 else "暂不主动交易" if s>40 else "降低暴露，等待风险改善"
    return {"asset":asset,"score":s,"direction":direction,"level":level,"evidence":evidence[:5],"risks":risks[:5],"triggers":triggers[:5],"action":action}

def _price_plan(asset, row, f):
    p=_num(_asset(f, "黄金期货" if asset=="黄金" else asset).get("price"))
    if p is None and asset=="黄金": p=_num(_asset(f,"黄金").get("price"))
    if p is None: return {"current":None,"plan":"当前数据没有可靠价格，不生成虚构价位。"}
    ch=_num(_asset(f,"黄金期货" if asset=="黄金" else asset).get("change_20d"))
    if asset=="黄金":
        # Use volatility-aware zones only when price and 20d change exist; never claim exact support without a real technical series.
        pull1=round(p*0.985,2); pull2=round(p*0.97,2); breakout=round(p*1.01,2); invalid=round(p*0.97,2)
        return {"current":p,"plan":f"回撤观察区：{pull1}–{pull2}；突破确认参考：{breakout}；趋势保护参考：{invalid}。这些是模型区间，不是技术位。"}
    return {"current":p,"plan":"当前价格可用，但本版本不在缺少完整技术序列时虚构支撑/压力位。"}

def analyze_opportunities(finance_result:dict[str,Any]):
    rows=[]
    for a in ASSETS:
        r=_score(a,finance_result); r["price_plan"]=_price_plan(a,r,finance_result); rows.append(r)
    ranked=sorted(rows,key=lambda x:x["score"],reverse=True)
    return {"version":"V3.0","assets":rows,"top_opportunities":[x for x in ranked if x["score"]>=60][:3],"top_risks":[x for x in ranked if x["score"]<=40][:3],"confidence":finance_result.get("confidence",0)}

def render_opportunities(finance_result:dict[str,Any])->None:
    import streamlit as st
    r=analyze_opportunities(finance_result)
    st.markdown("## 🎯 投资机会雷达 V3.0")
    st.caption(f"方向评分基于权威/专业新闻、宏观与市场趋势；置信度 {r['confidence']}%。评分不是收益率预测。")
    if r["top_opportunities"]:
        st.markdown("### 🔥 今日重点机会")
        for x in r["top_opportunities"]:
            st.markdown(f"### {x['level']} {x['asset']}｜{x['direction']}｜{x['score']}/100")
            st.write(f"**操作思路：** {x['action']}")
            if x['price_plan']['current'] is not None: st.write(f"**当前价格：** {x['price_plan']['current']}")
            st.write(f"**价格计划：** {x['price_plan']['plan']}")
            if x['evidence']: st.write("**核心证据：** "+"；".join(x['evidence']))
            if x['triggers']: st.write("**触发条件：** "+"；".join(x['triggers']))
            if x['risks']: st.write("**主要风险：** "+"；".join(x['risks']))
            st.divider()
    else: st.info("当前没有达到观察阈值的资产机会，系统选择不强行推荐。")
    st.markdown("### 📊 资产机会排名")
    for x in r["assets"]: st.write(f"{x['level']} **{x['asset']}**｜{x['direction']}｜{x['score']}/100｜{x['action']}")
    if r["top_risks"]:
        st.markdown("### 🚨 风险优先级")
        for x in r["top_risks"]: st.warning(f"{x['asset']}｜{x['score']}/100："+"；".join(x['risks']))
