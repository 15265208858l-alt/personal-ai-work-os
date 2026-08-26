# 刘强 · Personal AI Work OS — Investment Research Engine V1.0
from __future__ import annotations
from typing import Any

def _num(v):
    try: return float(v) if v is not None else None
    except Exception: return None

def _research_score(x):
    score=_num(x.get("score")); data=_num(x.get("data_score"))
    if score is None: return 0
    out=score
    if data is not None and data<70: out-=10
    elif data is not None and data>=90: out+=3
    risk=str(x.get("risk") or "").lower()
    if any(k in risk for k in ["高","high","危险"]): out-=8
    return max(0,min(100,round(out)))

def _action(x):
    s=x.get("research_score",0); entry=_num(x.get("entry_price")); current=_num(x.get("current_price")); heavy=_num(x.get("heavy_price"))
    if entry is not None and current is not None and current<=entry: return "进入建仓观察区"
    if heavy is not None and current is not None and current<=heavy: return "接近重仓参考区，等待基本面确认"
    if s>=85: return "重点研究，不代表立即买入"
    if s>=75: return "观察，等待估值/价格改善"
    return "暂不进入核心候选"

def analyze_investment_research(industry_result):
    rows=[]
    for x in (industry_result.get("stock_candidates",[]) if isinstance(industry_result,dict) else []):
        if not isinstance(x,dict) or not x.get("success"): continue
        y=dict(x); y["research_score"]=_research_score(y); y["action"]=_action(y)
        y["thesis"]=f"{y.get('theme','行业主题')} + ValueStock基本面评分 {y.get('score','暂无')} + 估值/价格条件共同决定。"
        rows.append(y)
    rows.sort(key=lambda z:z.get("research_score",0),reverse=True)
    return {"version":"V1.0","shortlist":[x for x in rows if x.get("research_score",0)>=75][:3],"watchlist":[x for x in rows if 60<=x.get("research_score",0)<75][:3],"all_candidates":rows[:10],"decision":"宏观主题用于发现方向，ValueStock用于验证企业；只有质量、数据和价格三项同时达标，才进入重点候选。"}

def render_investment_research(data):
    import streamlit as st
    st.divider(); st.markdown("## 🎯 A股深度研究与最终候选 V1.0"); st.caption(data.get("decision",""))
    if data.get("shortlist"):
        st.markdown("### 🏆 今日重点研究候选")
        for x in data["shortlist"]:
            st.markdown(f"#### ⭐ {x.get('name','未知')}（{x.get('code','')}）｜研究评分 {x.get('research_score',0)}/100")
            st.write(f"**所属主题：** {x.get('theme','暂无')}｜**企业评分：** {x.get('score','暂无')}/100｜**评级：** {x.get('rating','暂无')}")
            st.write(f"**当前价格：** {x.get('current_price','暂无')}｜**建仓参考：** {x.get('entry_price','暂无')}｜**重仓参考：** {x.get('heavy_price','暂无')}｜**中性价值：** {x.get('valuation','暂无')}")
            st.write(f"**当前动作：** {x.get('action','观察')}｜**研究逻辑：** {x.get('thesis','')}")
            st.caption(f"风险：{x.get('risk','暂无')}｜数据完整度：{x.get('data_score','暂无')}%")
    else: st.info("当前没有同时满足主题、企业质量、数据完整度和价格条件的重点候选。")
    if data.get("watchlist"):
        st.markdown("### 👀 观察名单")
        for x in data["watchlist"]: st.write(f"**{x.get('name','未知')}（{x.get('code','')}）**｜研究评分 {x.get('research_score',0)}/100｜{x.get('action','观察')}")
