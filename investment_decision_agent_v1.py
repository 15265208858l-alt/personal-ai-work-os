# 刘强 · Personal AI Work OS — Investment Decision Agent V1.0
from __future__ import annotations
from typing import Any


def _num(v):
    try:
        if v in (None, "", "暂无", "N/A"):
            return None
        return float(v)
    except Exception:
        return None


def _text(v, default="暂无"):
    return str(v) if v not in (None, "", "暂无") else default


def _asset_rows(opportunity):
    return [x for x in opportunity.get("assets", []) if isinstance(x, dict)] if isinstance(opportunity, dict) else []


def _stock_rows(research):
    if not isinstance(research, dict):
        return []
    rows = research.get("shortlist", [])
    return [x for x in rows if isinstance(x, dict)]


def _asset_action(asset, score, confidence):
    score = _num(score)
    if score is None:
        return {"status": "数据不足", "action": "不主动配置", "condition": "补齐核心数据后重新评估"}
    if confidence < 60:
        return {"status": "低置信度", "action": "观察", "condition": "数据置信度恢复至60%以上，并出现第二独立证据"}
    if score >= 75 and confidence >= 75:
        return {"status": "强机会", "action": "分批配置", "condition": "核心驱动未反转，价格未出现明显过热"}
    if score >= 65:
        return {"status": "条件机会", "action": "等待确认/轻仓试探", "condition": "至少两个核心变量同向，且价格/估值不过热"}
    if score >= 50:
        return {"status": "观察", "action": "暂不主动增加风险", "condition": "评分突破65并得到独立基本面/宏观证据"}
    return {"status": "偏弱", "action": "回避", "condition": "核心驱动改善并重新通过数据验证"}


def _stock_action(x, confidence):
    score = _num(x.get("research_score")) or 0
    data = _num(x.get("data_score"))
    price_state = _text(x.get("price_state"), "价格中性")
    if data is not None and data < 70:
        return "暂不参与", "数据完整度低于70%", "数据完整后重新验证"
    if confidence < 65:
        return "观察", "总置信度不足，禁止放大个股风险", "整体置信度≥70%且基本面未恶化"
    if score >= 85 and price_state in ("进入建仓参考区", "中性价值以下"):
        return "优先研究/分批建仓", "高质量 + 价格具安全边际", "基本面稳定且价格仍在安全边际内"
    if score >= 80:
        return "重点跟踪", "质量较高，但价格/估值仍需确认", "进入建仓参考区后再提高仓位"
    if score >= 70:
        return "观察", "尚未形成高质量与价格共振", "盈利预期上修或估值明显改善"
    return "暂不参与", "研究评分不足", "重新进入70分以上并通过数据验证"


def build_decision_agent(finance: dict[str, Any], opportunity: dict[str, Any], cockpit: dict[str, Any], research: dict[str, Any], portfolio: dict[str, Any], action_plan: dict[str, Any], risk_review: dict[str, Any], monitor: dict[str, Any]) -> dict[str, Any]:
    confidence = _num(finance.get("confidence")) or _num(opportunity.get("confidence")) or 0
    assets = _asset_rows(opportunity)
    ranked_assets = sorted(assets, key=lambda x: _num(x.get("score")) or -1, reverse=True)
    top_assets = []
    for x in ranked_assets[:5]:
        score = _num(x.get("score"))
        act = _asset_action(x.get("asset", "未知"), score, confidence)
        top_assets.append({
            "asset": _text(x.get("asset"), "未知"),
            "score": score,
            "direction": _text(x.get("direction"), "观察"),
            "status": act["status"],
            "action": act["action"],
            "condition": act["condition"],
            "why": _text(x.get("why_now") or x.get("reason"), "暂无充分理由"),
        })

    stocks = _stock_rows(research)
    stock_cards = []
    for x in stocks[:5]:
        action, reason, trigger = _stock_action(x, confidence)
        stock_cards.append({
            "name": _text(x.get("name"), "未知股票"),
            "code": _text(x.get("code"), ""),
            "score": _num(x.get("research_score")),
            "price_state": _text(x.get("price_state"), "价格中性"),
            "current_price": x.get("current_price"),
            "entry_price": x.get("entry_price"),
            "heavy_price": x.get("heavy_price"),
            "valuation": x.get("valuation"),
            "action": action,
            "reason": reason,
            "trigger": trigger,
        })

    actionable_assets = [x for x in top_assets if x["status"] == "强机会"]
    conditional_assets = [x for x in top_assets if x["status"] == "条件机会"]
    eligible_stocks = [x for x in stock_cards if x["action"] in ("优先研究/分批建仓", "重点跟踪")]

    if confidence < 60:
        regime = "🔴 防守"
        headline = "数据置信度不足，今天优先保护本金，不主动扩大风险暴露。"
    elif actionable_assets:
        regime = "🟢 有条件行动"
        headline = f"最高优先级：{actionable_assets[0]['asset']}；可以行动，但必须服从触发条件和仓位纪律。"
    elif conditional_assets:
        regime = "🟡 等待确认"
        headline = f"最高优先级：{conditional_assets[0]['asset']}；方向值得跟踪，但证据不足以支持重仓。"
    elif eligible_stocks:
        regime = "🟡 个股研究"
        headline = f"资产层没有强共振，优先研究：{eligible_stocks[0]['name']}（{eligible_stocks[0]['code']}）。"
    else:
        regime = "🟡 观察"
        headline = "当前没有达到系统行动阈值的高质量机会，保持流动性并等待新证据。"

    top_stock = max(stock_cards, key=lambda x: x["score"] if x["score"] is not None else -1) if stock_cards else None
    portfolio_alloc = portfolio.get("model_allocation", {}) if isinstance(portfolio, dict) else {}
    cash = portfolio_alloc.get("现金/低波动")

    next_actions = []
    if actionable_assets:
        a = actionable_assets[0]
        next_actions.append(f"资产：{a['asset']} → {a['action']}；触发：{a['condition']}")
    elif conditional_assets:
        a = conditional_assets[0]
        next_actions.append(f"资产：{a['asset']} → {a['action']}；触发：{a['condition']}")
    if eligible_stocks:
        s = eligible_stocks[0]
        next_actions.append(f"个股：{s['name']}（{s['code']}）→ {s['action']}；{s['trigger']}")
    if not next_actions:
        next_actions.append("暂不新增主动风险；等待核心变量出现明确变化后重新运行。")

    stop_conditions = [
        "核心驱动与价格方向同时反转，不因为原先观点继续加仓。",
        "数据质量明显下降或关键数据互相矛盾，自动降低仓位权限。",
        "个股基本面、现金流、治理或资产负债表出现实质性恶化，投资逻辑失效优先于价格止损。",
    ]
    if risk_review.get("alerts"):
        stop_conditions.extend([_text(x) for x in risk_review.get("alerts", [])[:3]])

    return {
        "version": "V1.0",
        "confidence": confidence,
        "regime": regime,
        "headline": headline,
        "top_asset": top_assets[0] if top_assets else {},
        "asset_actions": top_assets,
        "stock_actions": stock_cards,
        "next_actions": next_actions,
        "cash_reference": cash,
        "stop_conditions": stop_conditions[:6],
        "decision_basis": [
            "先看数据质量，再看宏观与资产方向，再看个股质量和估值，最后才决定仓位。",
            "单一新闻、单一指标或单一评分不能直接触发重仓。",
            "价格与基本面必须同时通过；便宜但基本面恶化不能买，高质量但明显过热也不追。",
        ],
        "disclaimer": "V1.0是研究与风险预算框架，不是确定性收益预测或自动交易指令。",
    }


def render_decision_agent(data: dict[str, Any]) -> None:
    import streamlit as st
    st.divider()
    st.markdown("## 🤖 投资决策 Agent V1.0")
    st.caption(f"决策状态：{data.get('regime','观察')}｜数据置信度：{data.get('confidence',0):.0f}%｜评分不是收益率预测")
    st.success(data.get("headline", "当前没有达到行动阈值的机会。"))

    c1, c2, c3 = st.columns(3)
    top = data.get("top_asset", {})
    c1.metric("第一优先级", _text(top.get("asset"), "暂无"))
    c2.metric("机会评分", f"{top.get('score'):.0f}/100" if isinstance(top.get("score"), (int,float)) else "暂无")
    c3.metric("现金/低波动参考", f"{data.get('cash_reference')}%" if data.get('cash_reference') is not None else "暂无")

    st.markdown("### 🎯 今天具体怎么做")
    for i, x in enumerate(data.get("next_actions", []), 1):
        st.write(f"**{i}.** {x}")

    st.markdown("### 🌍 资产行动矩阵")
    for x in data.get("asset_actions", []):
        st.markdown(f"**{x['asset']}｜{x['status']}｜{x['score'] if x['score'] is not None else '暂无'}/100**")
        st.write(f"行动：{x['action']}｜触发：{x['condition']}")
        st.caption(f"理由：{x['why']}")

    if data.get("stock_actions"):
        st.markdown("### 📈 A股个股行动卡")
        for x in data["stock_actions"]:
            score = f"{x['score']:.0f}/100" if isinstance(x.get('score'), (int,float)) else "暂无"
            st.markdown(f"**{x['name']}（{x['code']}）｜{score}｜{x['action']}**")
            st.write(f"理由：{x['reason']}｜触发：{x['trigger']}")
            st.caption(f"当前价：{_text(x.get('current_price'))}｜建仓：{_text(x.get('entry_price'))}｜重仓：{_text(x.get('heavy_price'))}｜估值：{_text(x.get('valuation'))}")

    st.markdown("### 🚨 什么时候必须停止原来的判断")
    for x in data.get("stop_conditions", []):
        st.warning(x)

    st.markdown("### 🧠 决策纪律")
    for x in data.get("decision_basis", []):
        st.write("• " + x)
    st.caption(data.get("disclaimer", ""))
