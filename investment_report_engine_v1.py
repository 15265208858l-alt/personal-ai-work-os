# 刘强 · Personal AI Work OS — Investment Report Engine V1.0
from __future__ import annotations
from typing import Any


def _num(v):
    try:
        return float(v) if v is not None else None
    except Exception:
        return None


def build_investment_report(finance: dict[str, Any], opportunity: dict[str, Any], cockpit: dict[str, Any], industry: dict[str, Any], research: dict[str, Any], portfolio: dict[str, Any]) -> dict[str, Any]:
    assets = [x for x in opportunity.get("assets", []) if isinstance(x, dict)]
    assets = sorted(assets, key=lambda x: _num(x.get("score")) or -1, reverse=True)
    top = assets[0] if assets else {}
    shortlist = research.get("shortlist", []) if isinstance(research, dict) else []
    watchlist = research.get("watchlist", []) if isinstance(research, dict) else []
    reasons = opportunity.get("drivers", []) if isinstance(opportunity, dict) else []
    risks = opportunity.get("risks", []) if isinstance(opportunity, dict) else []
    monitoring = cockpit.get("next_24h", []) if isinstance(cockpit, dict) else []
    if not monitoring:
        monitoring = cockpit.get("monitor", []) if isinstance(cockpit, dict) else []

    confidence = _num(finance.get("confidence")) or _num(opportunity.get("confidence")) or 0
    mode = portfolio.get("mode", "谨慎模式" if confidence < 70 else "正常模式") if isinstance(portfolio, dict) else "谨慎模式"

    if shortlist:
        lead = shortlist[0]
        headline = f"重点研究 {lead.get('name','未知')}（{lead.get('code','')}），但以建仓参考价和基本面确认作为行动前提。"
    elif top.get("asset"):
        score = _num(top.get("score"))
        if score is not None and score >= 70:
            headline = f"当前第一关注为{top.get('asset')}，但仍需结合价格位置与关键宏观变量决定是否行动。"
        elif score is not None and score >= 60:
            headline = f"当前第一关注为{top.get('asset')}，属于条件型机会，优先等待确认，不追涨。"
        else:
            headline = "当前没有形成足够强的共振机会，优先控制风险并等待确认。"
    else:
        headline = "当前数据不足以形成明确的高置信度投资机会。"

    actions = []
    if isinstance(portfolio, dict) and portfolio.get("next_action"):
        actions.append(portfolio["next_action"])
    if shortlist:
        for x in shortlist[:3]:
            actions.append(f"{x.get('name','未知')}：{x.get('action','观察')}；当前价 {x.get('current_price','暂无')}，建仓参考 {x.get('entry_price','暂无')}。")
    elif top.get("asset"):
        actions.append(f"{top.get('asset')}：等待核心触发条件，避免仅凭单条新闻追涨。")
    if not actions:
        actions.append("保持观察，等待更高质量数据或独立变量共振。")

    return {
        "version": "V1.0",
        "headline": headline,
        "mode": mode,
        "confidence": confidence,
        "top_asset": top.get("asset", "暂无"),
        "top_asset_score": _num(top.get("score")),
        "actions": actions[:5],
        "drivers": reasons[:6],
        "risks": risks[:5],
        "monitoring": monitoring[:5],
        "shortlist": shortlist[:3],
        "watchlist": watchlist[:3],
        "allocation": portfolio.get("model_allocation", {}) if isinstance(portfolio, dict) else {},
        "bottom_line": "结论用于研究与决策辅助，不构成保证收益的买卖指令；数据不足时优先等待确认。",
    }


def render_investment_report(data: dict[str, Any]) -> None:
    import streamlit as st
    st.divider()
    st.markdown("# 🧠 最终投资研究报告 V1.0")
    st.caption(data.get("bottom_line", ""))
    c1, c2, c3 = st.columns(3)
    c1.metric("研究模式", data.get("mode", "暂无"))
    c2.metric("数据置信度", f"{data.get('confidence', 0):.0f}%")
    c3.metric("第一关注", f"{data.get('top_asset','暂无')} {data.get('top_asset_score','')}" if data.get('top_asset') else "暂无")

    st.markdown("## 🎯 一句话结论")
    st.success(data.get("headline", "暂无明确结论"))

    st.markdown("## 💰 现在具体怎么做")
    for i, x in enumerate(data.get("actions", []), 1):
        st.write(f"**{i}.** {x}")

    if data.get("drivers"):
        st.markdown("## 🧠 为什么")
        for x in data["drivers"]: st.write("• " + str(x))

    if data.get("risks"):
        st.markdown("## 🚨 最大风险")
        for x in data["risks"]: st.warning(str(x))

    if data.get("shortlist"):
        st.markdown("## ⭐ 今日重点A股")
        for x in data["shortlist"]:
            st.write(f"**{x.get('name','未知')}（{x.get('code','')}）**｜研究评分 {x.get('research_score','暂无')}/100｜{x.get('action','观察')}")
            st.caption(f"当前价 {x.get('current_price','暂无')}｜建仓参考 {x.get('entry_price','暂无')}｜重仓参考 {x.get('heavy_price','暂无')}｜风险 {x.get('risk','暂无')}")
    elif data.get("watchlist"):
        st.markdown("## 👀 今日观察A股")
        for x in data["watchlist"]: st.write(f"**{x.get('name','未知')}（{x.get('code','')}）**｜研究评分 {x.get('research_score','暂无')}/100｜{x.get('action','观察')}")

    if data.get("monitoring"):
        st.markdown("## ⏰ 下一步重点监控")
        for x in data["monitoring"]: st.write("• " + str(x))

    if data.get("allocation"):
        st.markdown("## 📊 当前模型仓位参考")
        cols = st.columns(3)
        for i, (k, v) in enumerate(data["allocation"].items()): cols[i % 3].metric(k, f"{v}%")
