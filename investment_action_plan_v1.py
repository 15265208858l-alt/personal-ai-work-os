# 刘强 · Personal AI Work OS — Investment Action Plan V1.0
from __future__ import annotations
from typing import Any


def _num(v):
    try:
        return float(v) if v is not None and v != "" else None
    except Exception:
        return None


def _action_for_stock(x: dict[str, Any]) -> dict[str, Any]:
    score = _num(x.get("research_score")) or 0
    current = _num(x.get("current_price"))
    entry = _num(x.get("entry_price"))
    heavy = _num(x.get("heavy_price"))
    valuation = _num(x.get("valuation"))

    if current is not None and entry is not None and current <= entry:
        action = "进入第一观察/建仓区"
        trigger = f"当前价≤建仓参考价 {entry:g}，且基本面没有出现新的恶化信号"
    elif score >= 85:
        action = "重点跟踪，等待价格"
        trigger = "企业质量继续稳定，同时价格回到建仓参考区"
    elif score >= 75:
        action = "观察，等待估值改善"
        trigger = "估值或价格进一步改善，并保持现金流/盈利质量"
    else:
        action = "暂不参与"
        trigger = "等待研究评分、数据质量或价格条件改善"

    invalid = [
        "核心盈利/经营现金流明显恶化",
        "估值快速脱离基本面，安全边际消失",
        "出现重大监管、治理、商誉或资产负债表风险",
    ]
    return {
        "name": x.get("name", "未知"), "code": x.get("code", ""),
        "theme": x.get("theme", "暂无"), "research_score": round(score),
        "current_price": current, "entry_price": entry, "heavy_price": heavy,
        "valuation": valuation, "action": action, "trigger": trigger,
        "invalid_conditions": invalid,
        "position_cap": "单一A股机会仓原则上不超过模型A股机会仓的50%",
    }


def build_action_plan(finance: dict[str, Any], opportunity: dict[str, Any], research: dict[str, Any], portfolio: dict[str, Any]) -> dict[str, Any]:
    shortlist = research.get("shortlist", []) if isinstance(research, dict) else []
    stocks = [_action_for_stock(x) for x in shortlist if isinstance(x, dict)]
    confidence = _num(finance.get("confidence")) or _num(portfolio.get("confidence")) or 0
    mode = portfolio.get("mode", "谨慎模式")

    ranked = []
    for x in opportunity.get("assets", []) if isinstance(opportunity, dict) else []:
        if isinstance(x, dict) and x.get("asset"):
            s = _num(x.get("score"))
            if s is not None: ranked.append((s, x.get("asset"), x))
    ranked.sort(reverse=True)
    top = ranked[0] if ranked else (None, "暂无", {})

    if stocks:
        headline = f"优先研究 {stocks[0]['name']}（{stocks[0]['code']}），但必须按价格触发条件分批；不要因宏观主题直接追高。"
    elif top[0] is not None and top[0] >= 70:
        headline = f"当前第一优先级是{top[1]}；等待核心触发条件后再行动，不因单日行情追涨。"
    else:
        headline = "当前没有形成足够强的共振机会；以观察和保留流动性为主。"

    if confidence < 70:
        headline += f" 当前数据置信度仅{confidence:.0f}%，因此只给条件式行动，不给强制买入指令。"

    return {
        "version": "V1.0", "mode": mode, "confidence": confidence,
        "headline": headline, "stock_actions": stocks[:3],
        "market_watch": [
            "美元与美国10Y/实际利率方向是否继续支持当前资产逻辑",
            "Fed利率预期、CPI/PCE/就业数据是否改变宽松预期",
            "地缘政治风险是否继续提供风险溢价，或转化为通胀冲击",
        ],
        "execution_rules": [
            "先确认逻辑，再确认价格，最后决定仓位；三者缺一不可。",
            "任何单一新闻不得触发重仓。",
            "价格进入建仓区也不等于立即重仓，先复核最新基本面和数据质量。",
            "若核心逻辑失效，停止加仓并重新评估，而不是摊平亏损。",
        ],
        "disclaimer": "这是研究与条件式执行框架，不构成针对个人账户的确定性买卖指令。",
    }


def render_action_plan(data: dict[str, Any]) -> None:
    import streamlit as st
    st.divider()
    st.markdown("## 🧭 最终投资执行计划 V1.0")
    st.caption(data.get("disclaimer", ""))
    c1, c2, c3 = st.columns(3)
    c1.metric("执行模式", data.get("mode", "观察"))
    c2.metric("数据置信度", f"{data.get('confidence', 0):.0f}%")
    c3.metric("研究候选", str(len(data.get("stock_actions", []))))
    st.markdown("### 🎯 今日核心行动")
    st.success(data.get("headline", "保持观察"))

    if data.get("stock_actions"):
        st.markdown("### 📌 个股条件式执行卡")
        for x in data["stock_actions"]:
            st.markdown(f"#### {x['name']}（{x['code']}）｜研究评分 {x['research_score']}/100")
            st.write(f"**当前动作：** {x['action']}")
            st.write(f"**触发条件：** {x['trigger']}")
            st.write(f"**当前价：** {x.get('current_price') if x.get('current_price') is not None else '暂无'} ｜ **建仓参考：** {x.get('entry_price') if x.get('entry_price') is not None else '暂无'} ｜ **重仓参考：** {x.get('heavy_price') if x.get('heavy_price') is not None else '暂无'}")
            st.write(f"**中性价值：** {x.get('valuation') if x.get('valuation') is not None else '暂无'} ｜ **仓位上限：** {x['position_cap']}")
            with st.expander("🚨 观点失效条件", expanded=False):
                for item in x["invalid_conditions"]: st.write("• " + item)
    else:
        st.info("目前没有通过深度研究的个股进入条件式执行卡。系统不会为了产生推荐而强行制造股票机会。")

    st.markdown("### 👀 未来重点监控")
    for x in data.get("market_watch", []): st.write("• " + x)
    st.markdown("### 🧱 执行纪律")
    for i, x in enumerate(data.get("execution_rules", []), 1): st.write(f"{i}. {x}")
