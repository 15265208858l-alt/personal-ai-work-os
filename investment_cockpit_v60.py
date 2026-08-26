# 刘强 · Personal AI Work OS — Investment Decision Cockpit V6.0
from __future__ import annotations

from typing import Any


def _asset_map(opportunity: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {x.get("asset"): x for x in opportunity.get("assets", []) if isinstance(x, dict)}


def build_cockpit(finance: dict[str, Any], opportunity: dict[str, Any]) -> dict[str, Any]:
    assets = _asset_map(opportunity)
    confidence = float(opportunity.get("confidence", finance.get("confidence", 0)) or 0)
    market = finance.get("market", {}) or {}
    macro = finance.get("macro", {}) or {}

    gold = assets.get("黄金", {})
    stocks = assets.get("美股", {})
    bonds = assets.get("美债", {})
    dollar = assets.get("美元", {})
    oil = assets.get("原油", {})

    actions: list[dict[str, str]] = []

    def add(asset: str, priority: str, action: str, trigger: str, invalid: str, reason: str):
        actions.append({"asset": asset, "priority": priority, "action": action, "trigger": trigger, "invalid": invalid, "reason": reason})

    # 严格门槛：数据置信度不足时，不制造强买卖结论。
    if confidence < 70:
        mode = "谨慎模式"
        mode_reason = "数据置信度低于70%，系统只给观察条件，不生成强买入/卖出指令。"
    else:
        mode = "正常决策模式"
        mode_reason = "数据质量达到决策阈值，可以结合趋势、宏观变量和新闻进行条件式行动。"

    if gold:
        gs = float(gold.get("score", 50) or 50)
        if gs >= 70:
            add("黄金", "高", "回撤分批关注", "美元继续走弱 + 10Y/实际利率回落，且价格回撤后企稳", "美元反弹且10Y/实际利率同步上行", "黄金最重要的确认变量是实际利率、美元和避险需求的共振。")
        elif gs >= 60:
            add("黄金", "中高", "持有/等待回撤，不追涨", "美元不转强，利率压力缓解，地缘风险没有明显降温", "美元与实际利率同时上行", "趋势尚可但需要价格与宏观信号确认。")
        else:
            add("黄金", "低", "观察", "宏观顺风重新形成", "实际利率持续上行且美元走强", "当前信号不足以支持主动扩大仓位。")

    if stocks:
        add("美股", "中", "回撤观察", "10Y稳定/回落 + 盈利预期没有恶化 + 指数健康回撤", "10Y快速上行或盈利预期明显下修", "美股估值对利率敏感，不能仅凭指数强弱追涨。")

    if bonds:
        add("美债", "中", "等待久期拐点", "CPI/PCE降温 + 就业走弱 + 10Y确认下行", "通胀重新上行或Fed转鹰", "债券的高胜率机会来自收益率下降形成的资本利得。")

    if dollar:
        add("美元", "观察", "作为风向标", "美元20日趋势由弱转强/由强转弱并得到利率确认", "单日波动与宏观方向相反", "美元本身不是唯一交易对象，更适合作为黄金和风险资产的传导变量。")

    if oil:
        add("原油", "观察", "不追地缘脉冲", "库存/供给/需求共同确认上涨", "只有冲突新闻而没有供需确认", "区分地缘风险溢价与真实供需趋势，避免把短期脉冲当长期趋势。")

    # 从资产排名中选出今日第一观察对象，但不把分数解释成收益率。
    ranked = sorted(opportunity.get("assets", []), key=lambda x: x.get("score", 0), reverse=True)
    top = ranked[0] if ranked else {}

    market_watch = []
    for name in ["美元指数", "美国10Y", "黄金期货", "标普500", "原油期货"]:
        item = market.get(name, {})
        if item.get("value") is not None:
            market_watch.append(f"{name} {item['value']:.2f}")
    macro_watch = []
    for name in ["联邦基金有效利率", "SOFR", "2Y收益率"]:
        item = macro.get(name, {})
        if item.get("value") is not None:
            macro_watch.append(f"{name} {item['value']:.2f}%")

    return {
        "version": "V6.0",
        "mode": mode,
        "mode_reason": mode_reason,
        "confidence": confidence,
        "today_focus": top.get("asset", "暂无明确第一机会"),
        "today_focus_score": top.get("score", 0),
        "today_focus_action": top.get("action", "观察"),
        "actions": actions,
        "market_watch": market_watch,
        "macro_watch": macro_watch,
        "decision_sequence": [
            "先确认数据质量与发布时间",
            "再确认美元/利率方向",
            "再确认资产价格趋势是否配合",
            "最后才决定仓位，而不是反过来追价格",
        ],
        "next_24h": [
            "关注Fed/官方宏观数据与Reuters等专业媒体是否出现新的方向性信息",
            "关注美国10Y与美元是否同时朝同一方向变化",
            "关注黄金、美股是否出现价格与宏观变量背离",
        ],
        "risk_control": "任何单一新闻、单一指标或单日价格波动，都不能单独触发重仓。",
    }


def render_cockpit(data: dict[str, Any]) -> None:
    import streamlit as st

    st.divider()
    st.markdown("# 🧠 投资决策驾驶舱 V6.0")
    st.caption("把财经情报和投资机会转化为‘今天看什么、什么条件下行动、什么情况下取消行动’。不是收益率预测。")

    c1, c2, c3 = st.columns(3)
    c1.metric("决策模式", data.get("mode", "观察"))
    c2.metric("数据置信度", f"{data.get('confidence', 0):.0f}%")
    c3.metric("今日第一关注", data.get("today_focus", "暂无"))
    st.info(data.get("mode_reason", ""))

    st.markdown("## 🎯 今天真正应该关注什么")
    st.success(f"**{data.get('today_focus','暂无')}**｜评分 {data.get('today_focus_score',0)}/100｜{data.get('today_focus_action','观察')}")

    st.markdown("## 🧭 条件式行动清单")
    for x in data.get("actions", []):
        st.markdown(f"### {x['asset']}｜{x['priority']}优先级")
        st.write(f"**当前动作：** {x['action']}")
        st.write(f"**可以行动的条件：** {x['trigger']}")
        st.write(f"**条件失效：** {x['invalid']}")
        st.caption(f"为什么：{x['reason']}")

    st.markdown("## 👀 当前监控面板")
    if data.get("market_watch"):
        st.write("**市场：** " + "｜".join(data["market_watch"]))
    if data.get("macro_watch"):
        st.write("**宏观：** " + "｜".join(data["macro_watch"]))

    st.markdown("## ⏱️ 未来24小时只盯3件事")
    for item in data.get("next_24h", []):
        st.write("☑️ " + item)

    st.markdown("## 🔄 决策顺序")
    for i, item in enumerate(data.get("decision_sequence", []), 1):
        st.write(f"{i}. {item}")

    st.warning("风险纪律：" + data.get("risk_control", "不追单一信号。"))
