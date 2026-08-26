# 刘强 · Personal AI Work OS — Opportunity Radar V5.2 Action Edition
from __future__ import annotations

from typing import Any

from opportunity_engine import analyze_opportunities as _base_analyze


def _action_matrix(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    by = {x.get("asset"): x for x in rows}
    out: list[dict[str, str]] = []

    gold = by.get("黄金", {})
    if gold:
        score = gold.get("score", 50)
        if score >= 70:
            action = "回撤分批"
            condition = "美元继续走弱或10Y/实际利率回落，且价格没有出现加速拉升"
        elif score >= 60:
            action = "重点观察"
            condition = "等待美元+利率至少一个核心变量继续利多，再考虑加仓"
        else:
            action = "暂不加仓"
            condition = "等待宏观顺风重新形成"
        out.append({"asset": "黄金", "action": action, "condition": condition, "why": "美元、实际利率、避险需求三者至少两项共振时，黄金机会质量最高。"})

    stocks = by.get("美股", {})
    if stocks:
        out.append({"asset": "美股", "action": "回撤配置", "condition": "10Y不再快速上行，同时盈利预期稳定/改善", "why": "利率决定估值，盈利决定持续性；不能只看指数涨跌。"})

    bonds = by.get("美债", {})
    if bonds:
        out.append({"asset": "美债", "action": "等待拐点", "condition": "CPI/PCE降温 + 就业走弱 + 10Y确认向下", "why": "真正的交易机会来自久期收益率下降，而不是单纯高票息。"})

    dollar = by.get("美元", {})
    if dollar:
        out.append({"asset": "美元", "action": "作为风向标", "condition": "观察美元20日趋势是否反转", "why": "美元是黄金、商品和全球风险资产的重要传导变量。"})

    oil = by.get("原油", {})
    if oil:
        out.append({"asset": "原油", "action": "不追地缘冲高", "condition": "等待库存、供给和需求数据确认上涨性质", "why": "地缘溢价与真实需求上涨，对通胀和利率的影响不同。"})

    return out


def _next_checklist(rows: list[dict[str, Any]]) -> list[str]:
    by = {x.get("asset"): x for x in rows}
    checks = []
    gold = by.get("黄金", {})
    if gold:
        checks.append("黄金：下一次重点核验美元方向、美国10Y/实际利率、Fed降息预期和地缘风险，而不是单看金价。")
    stocks = by.get("美股", {})
    if stocks:
        checks.append("美股：核验10Y是否回落、盈利预期是否上修、指数是否出现健康回撤。")
    bonds = by.get("美债", {})
    if bonds:
        checks.append("美债：核验CPI/PCE、就业和Fed表态是否共同指向宽松。")
    oil = by.get("原油", {})
    if oil:
        checks.append("原油：核验地缘冲突、库存、OPEC+供给和需求预期，防止把风险溢价当趋势。")
    return checks


def analyze_opportunities(finance_result: dict[str, Any]):
    result = _base_analyze(finance_result)
    result["version"] = "V5.2"
    rows = result.get("assets", [])
    result["action_matrix"] = _action_matrix(rows)
    result["next_checklist"] = _next_checklist(rows)
    result["decision"] = (
        result.get("decision", "当前没有足够强的机会。")
        + " V5.2进一步要求：先确认触发条件，再决定仓位；没有触发条件时只观察。"
    )
    return result


def render_opportunities(data: dict[str, Any]) -> None:
    import streamlit as st

    r = data if isinstance(data, dict) and isinstance(data.get("assets"), list) else analyze_opportunities(data)
    st.markdown("## 🎯 投资机会雷达 V5.2")
    st.caption(f"行动版：趋势 + 利率 + 美元 + 权威/专业新闻 + 拥挤度 + 数据质量；置信度 {r.get('confidence', 0):.0f}%。评分不是收益率预测。")

    st.markdown("### 🧭 今日核心结论")
    st.info(r.get("decision", "当前没有足够强的机会。"))

    st.markdown("### 🔥 今日重点机会")
    tops = r.get("top_opportunities", [])
    if not tops:
        st.write("当前没有达到条件型机会阈值，系统选择等待。")
    for x in tops:
        st.markdown(f"#### {x.get('level','⭐')} {x.get('asset','未知')}｜{x.get('direction','观察')}｜{x.get('score',0)}/100")
        st.write(f"**核心逻辑：** {x.get('why_now','')}")
        st.write(f"**现在怎么做：** {x.get('action','观察')}")
        st.write(f"**什么时候可以做：** {x.get('entry_condition','等待确认')}")
        st.write(f"**仓位参考：** {x.get('position','0–5%试探')}")
        st.write(f"**观察周期：** {x.get('horizon','短线')}")
        if x.get("evidence"):
            st.write("**已验证证据：** " + "；".join(x["evidence"]))
        if x.get("risks"):
            st.warning("**主要风险：** " + "；".join(x["risks"]))

    st.markdown("### 🧩 机会→行动矩阵")
    for x in r.get("action_matrix", []):
        st.markdown(f"**{x['asset']}｜{x['action']}**")
        st.write(f"触发条件：{x['condition']}")
        st.caption(f"逻辑：{x['why']}")

    st.markdown("### 🌐 对黄金 / 股票市场的影响")
    impacts = r.get("cross_asset_impacts", [])
    for item in impacts:
        st.write("• " + item)

    st.markdown("### ⏭️ 下一步只盯这几件事")
    for item in r.get("next_checklist", []):
        st.write("☑️ " + item)

    st.markdown("### 📊 资产机会排名")
    for x in sorted(r.get("assets", []), key=lambda z: z.get("score", 0), reverse=True):
        st.write(f"{x.get('level','⭐')} **{x.get('asset','未知')}**｜{x.get('direction','观察')}｜{x.get('score',0)}/100｜{x.get('action','观察')}")

    st.markdown("### 🚨 风险优先级")
    for x in r.get("top_risks", []):
        risk_text = "；".join(x.get("risks", [])) or "当前主要是等待确认，而非明确风险事件。"
        st.warning(f"{x.get('asset','未知')}｜{x.get('score',0)}/100：{risk_text}")

    st.caption(r.get("decision_rule", ""))
    st.caption(r.get("disclaimer", ""))
