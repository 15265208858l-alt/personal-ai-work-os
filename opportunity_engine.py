# 刘强 · Personal AI Work OS — Opportunity Engine V2.0
from __future__ import annotations
from typing import Any

ASSETS = ["黄金", "美股", "美债", "美元", "原油"]

def _num(v):
    try: return float(v) if v is not None else None
    except Exception: return None

def _score(asset: str, f: dict[str, Any]):
    m, macro, news = f.get("market", {}), f.get("macro", {}), f.get("news", [])
    s, evidence, risks = 50, [], []
    dxy=_num(m.get("美元指数",{}).get("change_20d")); y10=_num(m.get("美国10Y",{}).get("change_20d")); spx=_num(m.get("标普500",{}).get("change_20d")); gold=_num(m.get("黄金期货",{}).get("change_20d")); oil=_num(m.get("原油期货",{}).get("change_20d")); y2=_num(macro.get("2Y收益率",{}).get("value"))
    trusted=[x for x in news if x.get("tier") in {"authoritative","professional"}]
    text=" ".join((x.get("title") or "").lower() for x in trusted[:20])
    if asset=="黄金":
        if dxy is not None and dxy < -1: s+=12; evidence.append("美元近20日走弱")
        if y10 is not None and y10 < -1: s+=10; evidence.append("10Y收益率边际回落")
        if y2 is not None and y2>=4: s-=6; risks.append("短端利率仍高")
        if gold is not None and gold>10: s-=10; risks.append("近期涨幅较大，追涨风险高")
        if any(k in text for k in ["iran","war","attack","sanction","conflict"]): s+=7; evidence.append("权威/专业消息显示地缘风险仍需关注")
    elif asset=="美股":
        if spx is not None and spx>2: s+=8; evidence.append("标普20日趋势偏强")
        if y10 is not None and y10>2: s-=10; risks.append("长端收益率上行压制估值")
        if y2 is not None and y2>=4.25: s-=6; risks.append("短端利率偏高")
        if any(k in text for k in ["recession","tariff","crisis"]): s-=6; risks.append("宏观风险事件增加波动")
    elif asset=="美债":
        if y10 is not None and y10<-1: s+=12; evidence.append("10Y收益率回落利于债券价格")
        if y10 is not None and y10>2: s-=12; risks.append("10Y收益率上行压制债券价格")
        if y2 is not None and y2>=4.25: s-=4; risks.append("短端利率仍高")
    elif asset=="美元":
        if dxy is not None and dxy>1: s+=10; evidence.append("美元近20日走强")
        if dxy is not None and dxy<-1: s-=10; risks.append("美元近20日走弱")
    elif asset=="原油":
        if oil is not None and oil>3: s+=8; evidence.append("原油趋势偏强")
        if oil is not None and oil<-3: s-=8; risks.append("原油趋势偏弱")
        if any(k in text for k in ["iran","war","attack","sanction"]): s+=8; evidence.append("地缘风险可能抬升风险溢价")
    return max(0,min(100,round(s))), evidence[:4], risks[:4]

def _action(asset, score, risks):
    if score>=70: return "高关注：等待价格确认后考虑分批布局" if not risks else "中高关注：方向较好，但先消化主要风险"
    if score>=60: return "观察：具备一定催化，但暂不追涨"
    if score<=35: return "规避/降低暴露：当前风险证据较多"
    return "等待：当前证据不足，不主动交易"

def analyze_opportunities(finance_result: dict[str, Any]):
    rows=[]
    for a in ASSETS:
        s,e,r=_score(a,finance_result)
        rows.append({"asset":a,"score":s,"direction":"偏多" if s>=62 else "偏空" if s<=38 else "震荡","evidence":e,"risks":r,"action":_action(a,s,r)})
    ranked=sorted(rows,key=lambda x:x["score"],reverse=True)
    return {"version":"V2.0","assets":rows,"top_opportunities":[x for x in ranked if x["score"]>=60][:3],"top_risks":[x for x in ranked if x["score"]<=40][:3],"confidence":finance_result.get("confidence",0)}

def render_opportunities(finance_result: dict[str, Any]) -> None:
    import streamlit as st
    result=analyze_opportunities(finance_result)
    st.markdown("## 🎯 投资机会雷达 V2.0")
    st.caption(f"机会排序基于当前权威/专业新闻、宏观数据和市场趋势；置信度 {result['confidence']}%。不是收益率预测。")
    if result["top_opportunities"]:
        st.markdown("### 🔎 当前最值得跟踪")
        for x in result["top_opportunities"]:
            st.success(f"**{x['asset']}｜{x['direction']}｜{x['score']}/100**\n\n{x['action']}")
            if x['evidence']: st.write("证据："+"；".join(x['evidence']))
            if x['risks']: st.write("风险："+"；".join(x['risks']))
    else: st.info("当前没有达到观察阈值的资产机会，系统选择不强行推荐。")
    st.markdown("### 📊 五大资产影响")
    cols=st.columns(5)
    for c,x in zip(cols,result["assets"]): c.metric(x["asset"],f"{x['score']}/100",x["direction"])
    st.markdown("### 🚨 风险优先级")
    for x in result["top_risks"]: st.warning(f"{x['asset']}：{x['action']}｜"+"；".join(x['risks']))
