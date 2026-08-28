# 刘强 · Personal AI Work OS — A股深度研究引擎 V2.0
from __future__ import annotations
from typing import Any

def _num(v):
    try:
        return float(v) if v not in (None, "") else None
    except Exception:
        return None

def _research_score(x):
    score=_num(x.get("score")); data=_num(x.get("data_score"))
    if score is None: return 0
    out=score
    if data is not None and data<70: out-=12
    elif data is not None and data<85: out-=5
    elif data>=90: out+=3
    risk=str(x.get("risk") or "").lower()
    if any(k in risk for k in ("高","high","危险")): out-=8
    return max(0,min(100,round(out)))

def _price_state(x):
    current=_num(x.get("current_price")); entry=_num(x.get("entry_price")); heavy=_num(x.get("heavy_price")); value=_num(x.get("valuation"))
    if current is None: return "价格数据不足"
    if entry is not None and current<=entry: return "进入建仓参考区"
    if heavy is not None and current<=heavy: return "接近重仓参考区"
    if value is not None and current>value*1.15: return "明显高于中性价值"
    if value is not None and current>value: return "高于中性价值"
    if value is not None and current<=value: return "中性价值以下"
    return "价格中性"

def _action(x):
    s=x.get("research_score",0); data=_num(x.get("data_score")); state=_price_state(x)
    if data is not None and data<70: return "数据不足，不主动买入"
    if state=="进入建仓参考区" and s>=75: return "可小仓位建仓，基本面未恶化再加"
    if state=="接近重仓参考区" and s>=85: return "重点关注，先复核现金流与估值"
    if s>=85: return "重点跟踪，等待价格"
    if s>=75: return "观察，等待估值改善"
    return "暂不进入核心候选"

def _catalysts(theme):
    t=str(theme)
    if any(k in t for k in ("AI","算力","PCB")): return ["AI资本开支继续增长","订单/产能利用率改善","业绩预期上修"]
    if any(k in t for k in ("黄金","贵金属")): return ["金价维持强势","美元/实际利率回落","产量或资源量改善"]
    if any(k in t for k in ("能源","油气")): return ["油价维持高位","供给约束持续","产量/成本改善"]
    return ["行业景气改善","盈利预期上修","估值回归合理区间"]

def _invalidations(theme):
    base=["经营现金流持续弱于净利润","应收账款/存货异常上升","核心盈利预期明显下修"]
    t=str(theme)
    if any(k in t for k in ("AI","算力","PCB")): base.append("AI资本开支或订单明显放缓")
    elif any(k in t for k in ("黄金","贵金属")): base.append("金价趋势反转且美元/实际利率同步转强")
    elif any(k in t for k in ("能源","油气")): base.append("油价快速回落且供需逻辑恶化")
    return base

def analyze_investment_research(industry_result):
    rows=[]
    candidates=industry_result.get("stock_candidates",[]) if isinstance(industry_result,dict) else []
    for x in candidates:
        if not isinstance(x,dict) or not x.get("success"): continue
        y=dict(x); y["research_score"]=_research_score(y); y["price_state"]=_price_state(y); y["action"]=_action(y)
        y["thesis"]=f"{y.get('theme','行业主题')}提供催化，企业质量评分{y.get('score','暂无')}/100；价格状态为‘{y['price_state']}’，行动需同时满足基本面、估值与价格条件。"
        y["catalysts"]=_catalysts(y.get("theme")); y["invalidation"]=_invalidations(y.get("theme"))
        y["evidence_chain"]=[f"主题评分 {y.get('theme_score','暂无')}/100",f"企业质量 {y.get('score','暂无')}/100",f"数据完整度 {y.get('data_score','暂无')}%",f"价格状态 {y['price_state']}"]
        rows.append(y)
    rows.sort(key=lambda z:z.get("research_score",0),reverse=True)
    shortlist=[x for x in rows if x.get("research_score",0)>=75 and (_num(x.get("data_score")) or 100)>=70][:3]
    watchlist=[x for x in rows if 60<=x.get("research_score",0)<75][:3]
    return {"version":"V2.0","shortlist":shortlist,"watchlist":watchlist,"all_candidates":rows[:10],"decision":"V2.0：宏观主题发现方向 → ValueStock验证企业质量 → 价格/估值决定行动；数据不足自动降级观察，不把研究评分当收益率预测。"}

def render_investment_research(data):
    import streamlit as st
    st.divider(); st.markdown("## 🎯 A股深度研究与最终候选 V2.0"); st.caption(data.get("decision",""))
    if data.get("shortlist"):
        st.markdown("### 🏆 今日重点研究候选")
        for x in data["shortlist"]:
            st.markdown(f"#### ⭐ {x.get('name','未知')}（{x.get('code','')}）｜研究评分 {x.get('research_score',0)}/100")
            st.write(f"主题：{x.get('theme','暂无')}｜企业评分：{x.get('score','暂无')}/100｜评级：{x.get('rating','暂无')}｜风险：{x.get('risk','暂无')}")
            st.write(f"当前价：{x.get('current_price','暂无')}｜价格状态：{x.get('price_state','暂无')}｜建仓：{x.get('entry_price','暂无')}｜重仓：{x.get('heavy_price','暂无')}｜中性价值：{x.get('valuation','暂无')}")
            st.success(f"🎯 当前动作：{x.get('action','观察')}")
            st.write(f"研究结论：{x.get('thesis','')}")
            st.write("核心证据："+"；".join(x.get("evidence_chain",[])))
            st.write("潜在催化："+"；".join(x.get("catalysts",[])))
            st.warning("失效条件："+"；".join(x.get("invalidation",[])))
    else: st.info("当前没有同时满足主题、企业质量、数据完整度和价格条件的重点候选；系统选择等待，不强行推荐。")
    if data.get("watchlist"):
        st.markdown("### 👀 观察名单")
        for x in data["watchlist"]: st.write(f"**{x.get('name','未知')}（{x.get('code','')}）**｜研究评分 {x.get('research_score',0)}/100｜{x.get('price_state','暂无')}｜{x.get('action','观察')}")
