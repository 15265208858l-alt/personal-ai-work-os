# 刘强 · Personal AI Work OS — Portfolio Decision Engine V1.0
from __future__ import annotations
from typing import Any


def _num(v):
    try: return float(v) if v is not None else None
    except Exception: return None


def build_portfolio_decision(finance: dict[str, Any], opportunity: dict[str, Any], research: dict[str, Any]) -> dict[str, Any]:
    confidence = _num(finance.get("confidence")) or _num(opportunity.get("confidence")) or 0
    assets = {x.get("asset"): x for x in opportunity.get("assets", []) if isinstance(x, dict)}
    shortlist = research.get("shortlist", []) if isinstance(research, dict) else []
    mode = "谨慎" if confidence < 70 else "正常"

    gold = _num(assets.get("黄金", {}).get("score")); stocks = _num(assets.get("美股", {}).get("score")); bonds = _num(assets.get("美债", {}).get("score")); oil = _num(assets.get("原油", {}).get("score"))
    model = {"黄金/贵金属":10, "股票/权益":20, "美债/利率资产":15, "现金/低波动":45, "原油/商品":5, "A股机会仓":5}
    reasons=[]; risks=[]
    if gold is not None and gold >= 65: model["黄金/贵金属"] += 5; model["现金/低波动"] -= 5; reasons.append("黄金宏观信号相对占优")
    if stocks is not None and stocks >= 65: model["股票/权益"] += 5; model["现金/低波动"] -= 5; reasons.append("风险资产趋势较强")
    if bonds is not None and bonds >= 65: model["美债/利率资产"] += 5; model["现金/低波动"] -= 5; reasons.append("利率资产配置条件改善")
    if oil is not None and oil >= 70: model["原油/商品"] += 3; model["现金/低波动"] -= 3; reasons.append("商品风险溢价较强")
    if not shortlist: risks.append("当前没有通过深度研究的A股重点候选，不增加A股机会仓")
    if mode == "谨慎": risks.append("数据置信度不足70%，整体保持防守，不使用满仓模型")
    total=sum(model.values()); model={k:round(v/total*100) for k,v in model.items()}
    return {"version":"V1.0","mode":mode,"confidence":confidence,"model_allocation":model,"reasons":reasons,"risks":risks,"shortlist_count":len(shortlist),"discipline":"模型仓位仅作为研究框架，不代表用户当前实际持仓；真正执行需结合个人资产、风险承受能力与流动性需求。"}


def render_portfolio_decision(data: dict[str, Any]) -> None:
    import streamlit as st
    st.divider(); st.markdown("## 💰 投资组合与仓位决策中心 V1.0")
    st.caption(data.get("discipline", ""))
    c1,c2,c3=st.columns(3); c1.metric("决策模式", data.get("mode","观察")); c2.metric("数据置信度", f"{data.get('confidence',0):.0f}%"); c3.metric("重点A股候选", str(data.get("shortlist_count",0)))
    st.markdown("### 📊 模型仓位框架")
    for k,v in data.get("model_allocation",{}).items(): st.write(f"**{k}**：{v}%")
    if data.get("reasons"): st.success("配置依据："+"；".join(data["reasons"]))
    if data.get("risks"): st.warning("主要约束："+"；".join(data["risks"]))
    st.markdown("### 🧭 仓位纪律")
    st.write("1. 单一宏观新闻不触发重仓。")
    st.write("2. 资产方向成立但价格过热，优先等待回撤。")
    st.write("3. A股个股只有通过ValueStock基本面与估值验证，才进入机会仓。")
    st.write("4. 数据置信度不足时，自动提高现金/低波动资产比例。")
