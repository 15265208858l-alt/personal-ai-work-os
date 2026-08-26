# 刘强 · Personal AI Work OS — Investment Monitor Engine V1.0
from __future__ import annotations
from typing import Any


def _num(v):
    try:
        if v is None or v == "": return None
        return float(v)
    except Exception:
        return None


def _asset_score(opportunity, name):
    for x in opportunity.get("assets", []):
        if isinstance(x, dict) and x.get("asset") == name:
            return _num(x.get("score"))
    return None


def build_investment_monitor(finance: dict[str, Any], opportunity: dict[str, Any], research: dict[str, Any], portfolio: dict[str, Any], risk_review: dict[str, Any]) -> dict[str, Any]:
    confidence = _num(finance.get("confidence")) or _num(opportunity.get("confidence")) or 0
    signals = []
    gold = _asset_score(opportunity, "黄金")
    stocks = _asset_score(opportunity, "美股")
    bonds = _asset_score(opportunity, "美债")
    oil = _asset_score(opportunity, "原油")

    for name, score, rule in [
        ("黄金", gold, "美元转强、实际利率快速上行或避险溢价明显回落时，降低黄金风险预算。"),
        ("美股", stocks, "实际利率上行叠加盈利预期下修时，降低权益风险暴露。"),
        ("美债", bonds, "10Y收益率继续上行且降息预期下降时，暂缓增加久期。"),
        ("原油", oil, "油价上涨若主要由地缘冲击驱动而非供需改善，避免追高商品仓位。"),
    ]:
        if score is not None:
            if score >= 70: status = "强信号，进入重点监控"
            elif score >= 60: status = "条件信号，等待确认"
            elif score >= 45: status = "中性观察"
            else: status = "偏弱，不主动增加"
            signals.append({"asset":name,"score":score,"status":status,"invalid_rule":rule})

    shortlist = research.get("shortlist", []) if isinstance(research, dict) else []
    stock_triggers = []
    for x in shortlist[:3]:
        current = _num(x.get("current_price")); entry = _num(x.get("entry_price")); heavy = _num(x.get("heavy_price")); score = _num(x.get("research_score")) or 0
        if current is not None and entry is not None:
            trigger = "当前价格进入建仓参考区" if current <= entry else f"等待价格≤{entry:g}再进入建仓观察"
        else: trigger = "等待有效价格数据后判断"
        if current is not None and heavy is not None and current <= heavy:
            trigger += "；若基本面未恶化，再评估提高仓位"
        stock_triggers.append({"name":x.get("name","未知"),"code":x.get("code",""),"score":score,"trigger":trigger,"risk":x.get("risk","暂无")})

    priority = []
    if confidence < 70: priority.append("数据置信度低于70%，本轮以观察和验证为主，不扩大主动风险仓。")
    if gold is not None and gold >= 70: priority.append("优先跟踪黄金：等待回撤、美元/实际利率确认，不追单日急涨。")
    if stocks is not None and stocks >= 70: priority.append("优先跟踪美股：关注利率与盈利预期是否形成共振。")
    if stock_triggers: priority.append(f"优先复核A股候选：{stock_triggers[0]['name']}（{stock_triggers[0]['code']}）的估值、现金流和价格条件。")
    if not priority: priority.append("当前没有形成足够强的共振信号，保持观察，等待新数据。")

    return {
        "version":"V1.0",
        "confidence":confidence,
        "monitor_mode":"谨慎监控" if confidence < 70 else "正常监控",
        "signals":signals,
        "stock_triggers":stock_triggers,
        "priority":priority[:4],
        "checklist":[
            "美元指数方向是否反转",
            "美国10Y与实际利率是否突破关键区间",
            "Fed降息预期是否发生明显变化",
            "CPI/PCE/非农是否改变政策路径",
            "黄金是否出现放量上涨后的回撤确认",
            "A股候选是否进入建仓参考价且基本面没有恶化",
        ],
        "discipline":"监控中心只生成条件和提醒，不自动下单；真实账户仓位需结合实际持仓、成本和风险承受能力单独核验。",
    }


def render_investment_monitor(data: dict[str, Any]) -> None:
    import streamlit as st
    st.divider()
    st.markdown("## 🔭 投资监控与触发器中心 V1.0")
    c1,c2,c3=st.columns(3)
    c1.metric("监控模式",data.get("monitor_mode","观察"))
    c2.metric("数据置信度",f"{data.get('confidence',0):.0f}%")
    c3.metric("重点信号",str(len(data.get("signals",[]))))
    st.markdown("### 🎯 当前优先级")
    for x in data.get("priority",[]): st.success("• "+x)
    if data.get("signals"):
        st.markdown("### 📡 资产触发器")
        for x in data["signals"]:
            st.write(f"**{x['asset']}**｜{x['status']}｜评分 {x['score']:.0f}/100")
            st.caption("失效/降风险条件："+x["invalid_rule"])
    if data.get("stock_triggers"):
        st.markdown("### 📈 A股价格触发器")
        for x in data["stock_triggers"]:
            st.write(f"**{x['name']}（{x['code']}）**｜研究评分 {x['score']:.0f}/100")
            st.info(x["trigger"])
    st.markdown("### 🧾 每日检查清单")
    for i,x in enumerate(data.get("checklist",[]),1): st.write(f"{i}. {x}")
    st.caption(data.get("discipline",""))
