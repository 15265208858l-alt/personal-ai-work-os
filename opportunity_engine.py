# 刘强 · Personal AI Work OS — Opportunity Engine V1.0
from __future__ import annotations

from typing import Any


def _impact(score: float) -> str:
    if score >= 65:
        return "偏多"
    if score <= 35:
        return "偏空"
    return "中性"


def _asset_score(asset: str, market: dict[str, Any], macro: dict[str, Any], news: list[dict[str, Any]]) -> tuple[int, list[str]]:
    score = 50
    reasons: list[str] = []
    dxy20 = market.get("美元指数", {}).get("change_20d")
    y10 = market.get("美国10Y", {}).get("change_20d")
    spx20 = market.get("标普500", {}).get("change_20d")
    gold20 = market.get("黄金期货", {}).get("change_20d")
    us2y = macro.get("2Y收益率", {}).get("value")
    risk_titles = " ".join(x.get("title", "").lower() for x in news[:20])

    if asset == "黄金":
        if dxy20 is not None and dxy20 < -1:
            score += 12; reasons.append("美元20日走弱，形成黄金支撑")
        if y10 is not None and y10 < -1:
            score += 10; reasons.append("10Y收益率回落，实际利率压力边际缓和")
        if us2y is not None and us2y > 4.0:
            score -= 7; reasons.append("2Y仍处高位，利率压力尚未完全解除")
        if gold20 is not None and gold20 > 10:
            score -= 8; reasons.append("黄金近期涨幅较大，短线追涨性价比下降")
        if any(k in risk_titles for k in ["iran", "war", "sanction", "conflict", "geopolit"]):
            score += 8; reasons.append("地缘风险对避险需求形成支撑")
    elif asset == "美股":
        if spx20 is not None and spx20 > 2:
            score += 8; reasons.append("标普近期趋势偏强")
        if y10 is not None and y10 > 2:
            score -= 10; reasons.append("长端收益率上行压制估值")
        if us2y is not None and us2y > 4.0:
            score -= 5; reasons.append("短端利率仍高，宽松确认不足")
        if any(k in risk_titles for k in ["recession", "crisis", "tariff"]):
            score -= 6; reasons.append("宏观风险事件增加波动压力")
    elif asset == "美债":
        if y10 is not None and y10 < -1:
            score += 10; reasons.append("10Y收益率回落有利于债券价格")
        if y10 is not None and y10 > 2:
            score -= 10; reasons.append("10Y收益率上升压低债券价格")
        if us2y is not None and us2y > 4.0:
            score -= 4; reasons.append("短端利率偏高")
    elif asset == "美元":
        if dxy20 is not None and dxy20 > 1:
            score += 10; reasons.append("美元指数近期走强")
        if dxy20 is not None and dxy20 < -1:
            score -= 10; reasons.append("美元指数近期走弱")
    return max(0, min(100, score)), reasons[:4]


def _opportunity(score: int, asset: str, reasons: list[str]) -> str:
    if asset == "黄金" and score >= 65:
        return "中期关注，短线不追涨；优先等待回撤确认或实际利率进一步回落。"
    if asset == "美股" and score >= 65:
        return "趋势偏强可继续观察，但应重点监控估值与美债收益率。"
    if asset == "美债" and score >= 65:
        return "若收益率继续回落，债券价格可能受益；更适合分批配置而非追涨。"
    if asset == "美元" and score >= 65:
        return "美元偏强时可作为防御资产观察，但需警惕政策转鸽。"
    return "当前证据不足以形成高置信度机会，继续等待催化。"


def analyze_opportunities(finance_result: dict[str, Any]) -> dict[str, Any]:
    market = finance_result.get("market", {})
    macro = finance_result.get("macro", {})
    news = finance_result.get("news", [])
    assets = ["黄金", "美股", "美债", "美元"]
    rows = []
    for asset in assets:
        score, reasons = _asset_score(asset, market, macro, news)
        rows.append({"asset": asset, "score": score, "direction": _impact(score), "reasons": reasons, "action": _opportunity(score, asset, reasons)})
    opportunities = [x for x in rows if x["score"] >= 65]
    risks = [x for x in rows if x["score"] <= 35]
    return {
        "version": "V1.0",
        "assets": rows,
        "opportunities": opportunities,
        "risks": risks,
        "message": "机会扫描基于当前宏观、市场与权威新闻证据，不等于价格上涨概率；未达到证据阈值的资产不列为机会。",
    }


def render_opportunities(result: dict[str, Any]) -> None:
    import streamlit as st
    st.markdown("## 🎯 投资机会与资产影响扫描")
    st.caption(result.get("message", ""))
    for row in result.get("assets", []):
        icon = "🟢" if row["score"] >= 65 else "🔴" if row["score"] <= 35 else "🟡"
        with st.container(border=True):
            st.markdown(f"### {icon} {row['asset']} · {row['direction']} · {row['score']}/100")
            if row.get("reasons"):
                for reason in row["reasons"]:
                    st.write(f"• {reason}")
            st.info(f"操作思路：{row['action']}")
    st.markdown("### 🔎 当前值得重点跟踪")
    if result.get("opportunities"):
        for row in result["opportunities"]:
            st.success(f"{row['asset']}：{row['action']}")
    else:
        st.warning("当前没有达到高置信度机会阈值的资产；系统选择不强行推荐。")
