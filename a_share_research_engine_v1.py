# 刘强 · Personal AI Work OS — A-share Deep Research Engine V1.0
from __future__ import annotations
from typing import Any


def _num(v):
    try:
        return float(v) if v is not None else None
    except Exception:
        return None


def _score(x: dict[str, Any]) -> int:
    quality = _num(x.get("score")); data = _num(x.get("data_score")); entry = _num(x.get("entry_price")); current = _num(x.get("current_price")); val = _num(x.get("valuation"))
    s = 0
    if quality is not None: s += min(55, max(0, quality * 0.55))
    if data is not None: s += min(20, max(0, data * 0.20))
    if val is not None and current is not None and current > 0:
        upside = (val / current - 1) * 100
        s += min(15, max(-10, upside * 0.30))
    if entry is not None and current is not None and current <= entry:
        s += 10
    return max(0, min(100, round(s)))


def analyze_a_share_research(industry_result: dict[str, Any]) -> dict[str, Any]:
    candidates = [x for x in industry_result.get("stock_candidates", []) if isinstance(x, dict) and x.get("success")]
    enriched = []
    for x in candidates:
        row = dict(x)
        row["research_score"] = _score(row)
        current = _num(row.get("current_price")); entry = _num(row.get("entry_price")); heavy = _num(row.get("heavy_price")); val = _num(row.get("valuation")); quality = _num(row.get("score")); data = _num(row.get("data_score"))
        reasons=[]; risks=[]
        if quality is not None and quality >= 75: reasons.append("企业质量较强")
        elif quality is not None and quality < 60: risks.append("企业质量评分偏低")
        if data is not None and data < 70: risks.append("数据完整度不足70%")
        if current is not None and entry is not None:
            if current <= entry: reasons.append("当前价格进入ValueStock建仓参考区")
            else: risks.append("当前价格高于建仓参考区")
        if val is not None and current is not None and current > 0:
            upside=(val/current-1)*100
            if upside >= 15: reasons.append(f"中性价值相对当前价约有{upside:.1f}%空间")
            elif upside < 0: risks.append("当前价格已高于中性价值")
        action = "重点研究" if row["research_score"] >= 75 and not risks else "等待价格/数据确认" if row["research_score"] >= 60 else "暂不参与"
        row.update({"reasons":reasons[:4],"research_risks":risks[:4],"action":action})
        enriched.append(row)
    enriched.sort(key=lambda z:z.get("research_score",0), reverse=True)
    shortlist=[x for x in enriched if x.get("research_score",0)>=70 and x.get("action") in {"重点研究","等待价格/数据确认"}][:3]
    return {"version":"V1.0","decision":"优先选择同时满足主题催化、企业质量、数据完整度和估值安全边际的公司；未满足者只进入观察名单。","shortlist":shortlist,"watchlist":enriched[:6],"rule":"研究评分不是收益率预测；任何个股必须回到ValueStock基本面和估值结果复核。"}


def render_a_share_research(data: dict[str, Any]) -> None:
    import streamlit as st
    st.divider(); st.markdown("## 🎯 A股深度研究与最终候选 V1.0"); st.caption(data.get("rule",""))
    st.info(data.get("decision",""))
    if data.get("shortlist"):
        st.markdown("### 🏆 今日重点研究候选")
        for x in data["shortlist"]:
            st.markdown(f"#### ⭐ {x.get('name','未知')}（{x.get('code','')}）｜研究评分 {x.get('research_score',0)}/100")
            st.write(f"行业主题：{x.get('theme','暂无')}｜企业评分：{x.get('score','暂无')}/100｜评级：{x.get('rating','暂无')}｜风险：{x.get('risk','暂无')}")
            st.write(f"当前价：{x.get('current_price','暂无')}｜建仓参考：{x.get('entry_price','暂无')}｜重仓参考：{x.get('heavy_price','暂无')}｜中性价值：{x.get('valuation','暂无')}")
            if x.get("reasons"): st.success("为什么值得研究："+"；".join(x["reasons"]))
            if x.get("research_risks"): st.warning("需要注意："+"；".join(x["research_risks"]))
            st.success(f"最终动作：{x.get('action','观察')}")
    else:
        st.info("当前没有同时满足主题、企业质量、数据完整度和估值条件的重点候选。")
    st.markdown("### 👀 观察名单")
    for x in data.get("watchlist",[]):
        st.write(f"**{x.get('name','未知')}（{x.get('code','')}）**｜{x.get('theme','暂无')}｜研究评分 {x.get('research_score',0)}/100｜{x.get('action','观察')}")
