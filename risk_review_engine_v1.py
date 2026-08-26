# 刘强 · Personal AI Work OS — Risk Review Engine V1.0
from __future__ import annotations
from typing import Any


def _num(v):
    try:
        if v is None or v == "": return None
        return float(v)
    except Exception:
        return None


def build_risk_review(finance: dict[str, Any], opportunity: dict[str, Any], research: dict[str, Any], portfolio: dict[str, Any], action_plan: dict[str, Any]) -> dict[str, Any]:
    confidence = _num(finance.get("confidence")) or _num(opportunity.get("confidence")) or 0
    assets = [x for x in opportunity.get("assets", []) if isinstance(x, dict)]
    shortlist = research.get("shortlist", []) if isinstance(research, dict) else []
    watchlist = research.get("watchlist", []) if isinstance(research, dict) else []
    allocation = portfolio.get("model_allocation", {}) if isinstance(portfolio, dict) else {}

    risks = []
    if confidence < 70:
        risks.append({"level":"高","title":"数据置信度不足","detail":f"当前综合置信度约{confidence:.0f}%，不宜把模型判断当成强交易信号。","action":"降低主动风险仓，等待核心数据确认。"})
    if sum(_num(x.get("score")) or 0 for x in assets if _num(x.get("score")) is not None) > 0:
        top = max(assets, key=lambda x: _num(x.get("score")) or -1)
        top_score = _num(top.get("score"))
        if top_score is not None and top_score >= 70:
            risks.append({"level":"中","title":f"{top.get('asset','重点资产')}信号较强","detail":"强趋势同时意味着拥挤和回撤风险不能忽略。","action":"优先分批，不追单日急涨。"})
    if not shortlist:
        risks.append({"level":"中","title":"A股没有通过深度研究的核心候选","detail":"当前没有同时满足研究阈值的重点股票。","action":"A股机会仓维持低配，不为了交易而交易。"})

    stock_reviews=[]
    for x in shortlist[:5]:
        score=_num(x.get("research_score")) or 0
        current=_num(x.get("current_price")); entry=_num(x.get("entry_price")); heavy=_num(x.get("heavy_price"))
        if current is not None and entry is not None and current <= entry:
            status="进入建仓观察区"
        elif current is not None and heavy is not None and current <= heavy:
            status="接近重仓参考区，必须复核基本面"
        elif score >= 85:
            status="高质量候选，但等待价格"
        else:
            status="继续观察"
        stock_reviews.append({"name":x.get("name","未知"),"code":x.get("code",""),"score":score,"status":status,"risk":x.get("risk","暂无")})

    return {
        "version":"V1.0",
        "mode":"高风险警戒" if confidence < 60 else ("谨慎复盘" if confidence < 70 else "正常监控"),
        "confidence":confidence,
        "risk_count":len(risks),
        "risks":risks,
        "stock_reviews":stock_reviews,
        "watchlist_count":len(watchlist),
        "portfolio_snapshot":allocation,
        "review_rules":[
            "模型仓位不是实际账户仓位，真实持仓必须单独核验。",
            "单一新闻、单一技术指标或单一资产信号不得触发重仓。",
            "基本面恶化、估值逻辑失效或核心催化剂消失，应重新研究而不是机械补仓。",
            "连续上涨后的追涨必须通过价格、估值和宏观变量三重确认。",
        ],
        "next_review":"下一次复盘优先检查：美元、美国10Y/实际利率、Fed预期、就业/通胀数据，以及A股候选的估值和现金流。",
    }


def render_risk_review(data: dict[str, Any]) -> None:
    import streamlit as st
    st.divider()
    st.markdown("## 🛡️ 风险管理与投资复盘中心 V1.0")
    c1,c2,c3=st.columns(3)
    c1.metric("风险模式",data.get("mode","观察"))
    c2.metric("数据置信度",f"{data.get('confidence',0):.0f}%")
    c3.metric("风险事项",str(data.get("risk_count",0)))
    if data.get("risks"):
        st.markdown("### 🚨 当前最重要风险")
        for r in data["risks"]:
            msg=f"**{r.get('title','风险')}**｜{r.get('detail','')}\n\n建议：{r.get('action','')}"
            if r.get("level")=="高": st.error(msg)
            else: st.warning(msg)
    if data.get("stock_reviews"):
        st.markdown("### 📈 A股候选复盘")
        for x in data["stock_reviews"]:
            st.write(f"**{x['name']}（{x['code']}）**｜研究评分 {x['score']:.0f}/100｜{x['status']}｜风险：{x['risk']}")
    st.markdown("### 🧭 复盘纪律")
    for i,r in enumerate(data.get("review_rules",[]),1): st.write(f"{i}. {r}")
    st.info("🔄 下一次复盘："+data.get("next_review","等待新数据。"))
