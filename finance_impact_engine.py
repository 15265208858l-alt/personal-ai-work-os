# =========================================================
# 刘强 · Personal AI Work OS
# Finance Impact Engine V1.0
# 新闻/宏观 -> 资产影响矩阵
# =========================================================
from __future__ import annotations

from typing import Any


def _market_direction(item: dict[str, Any] | None) -> float | None:
    if not isinstance(item, dict):
        return None
    value = item.get("change_20d")
    try:
        return float(value) if value is not None else None
    except Exception:
        return None


def _asset_scores(finance: dict[str, Any]) -> dict[str, dict[str, Any]]:
    market = finance.get("market") or {}
    macro = finance.get("macro") or {}
    news = finance.get("news") or []

    dxy20 = _market_direction(market.get("美元指数"))
    spx20 = _market_direction(market.get("标普500"))
    gold20 = _market_direction(market.get("黄金期货"))
    oil20 = _market_direction(market.get("原油期货"))
    y10_20 = _market_direction(market.get("美国10Y"))

    fed = macro.get("联邦基金有效利率", {}).get("value")
    us2y = macro.get("2Y收益率", {}).get("value")

    # 分数含义：0=偏空，50=中性，100=偏多；只作为当前信息框架，不是价格预测概率。
    out = {
        "黄金": {"score": 50, "reasons": []},
        "美股": {"score": 50, "reasons": []},
        "美债": {"score": 50, "reasons": []},
        "美元": {"score": 50, "reasons": []},
        "原油": {"score": 50, "reasons": []},
    }

    if dxy20 is not None:
        out["黄金"]["score"] += max(-15, min(15, -dxy20 * 4))
        out["美元"]["score"] += max(-15, min(15, dxy20 * 4))
        out["黄金"]["reasons"].append("美元20日走弱通常对黄金形成支撑" if dxy20 < 0 else "美元20日走强通常对黄金形成压制")

    if y10_20 is not None:
        out["黄金"]["score"] += max(-10, min(10, -y10_20 * 3))
        out["美债"]["score"] += max(-15, min(15, -y10_20 * 4))
        out["黄金"]["reasons"].append("10Y收益率回落有利于黄金" if y10_20 < 0 else "10Y收益率上升对黄金不利")

    if spx20 is not None:
        out["美股"]["score"] += max(-15, min(15, spx20 * 3))
        out["美股"]["reasons"].append("标普500近20日偏强" if spx20 > 0 else "标普500近20日偏弱")

    if oil20 is not None:
        out["原油"]["score"] += max(-15, min(15, oil20 * 3))
        out["原油"]["reasons"].append("原油近20日偏强" if oil20 > 0 else "原油近20日偏弱")

    if isinstance(us2y, (int, float)):
        if us2y >= 4.25:
            out["美股"]["score"] -= 8
            out["黄金"]["score"] -= 4
            out["美元"]["score"] += 3
            out["美股"]["reasons"].append("2Y收益率较高，金融条件偏紧")
        elif us2y <= 3.50:
            out["美股"]["score"] += 6
            out["黄金"]["score"] += 5
            out["美元"]["score"] -= 3
            out["美股"]["reasons"].append("2Y收益率偏低，金融条件压力较轻")

    if isinstance(fed, (int, float)) and fed >= 3.75:
        out["黄金"]["reasons"].append("政策利率仍处较高区间，黄金继续受实际利率约束")
        out["美股"]["reasons"].append("政策利率较高，估值对利率仍敏感")

    # 只把权威/专业标题用于方向提示，避免普通聚合源影响核心分数。
    trusted = [x for x in news if x.get("tier") in {"authoritative", "professional"}]
    for item in trusted[:20]:
        direction = item.get("direction")
        title = (item.get("title") or "").lower()
        if direction == "偏紧/风险升温":
            out["美股"]["score"] -= 4
            out["黄金"]["score"] += 2
            out["美元"]["score"] += 2
        elif direction == "偏宽松/风险缓和":
            out["美股"]["score"] += 4
            out["黄金"]["score"] += 2
            out["美元"]["score"] -= 2
        if any(k in title for k in ["iran", "war", "attack", "sanction", "冲突", "战争", "制裁"]):
            out["黄金"]["score"] += 4
            out["原油"]["score"] += 3
            out["美股"]["score"] -= 2

    for name, item in out.items():
        item["score"] = max(0, min(100, round(item["score"])))
        s = item["score"]
        item["state"] = "偏多" if s >= 62 else "偏空" if s <= 38 else "中性/震荡"
        # 删除重复理由
        seen = set(); reasons=[]
        for r in item["reasons"]:
            if r and r not in seen:
                seen.add(r); reasons.append(r)
        item["reasons"] = reasons[:4]
    return out


def build_impact(finance: dict[str, Any]) -> dict[str, Any]:
    scores = _asset_scores(finance)
    confidence = finance.get("confidence", 0)
    return {
        "version": "V1.0",
        "asset_impacts": scores,
        "confidence": confidence,
        "method_note": "资产影响评分是基于当前宏观与新闻证据的方向性辅助判断，不代表未来收益概率或交易指令。",
    }


def render_impact(finance: dict[str, Any]) -> None:
    import streamlit as st
    impact = build_impact(finance)
    st.markdown("### 🎯 消息 → 宏观 → 资产影响")
    st.caption("评分仅表示当前信息框架下的方向性偏向，不等同于涨跌预测。")
    cols = st.columns(5)
    for col, name in zip(cols, ["黄金", "美股", "美债", "美元", "原油"]):
        item = impact["asset_impacts"][name]
        col.metric(name, f"{item['score']}/100", item["state"])

    st.markdown("#### 🧠 为什么这样判断")
    for name in ["黄金", "美股", "美债", "美元", "原油"]:
        reasons = impact["asset_impacts"][name]["reasons"]
        if reasons:
            st.write(f"**{name}：** " + "；".join(reasons))
        else:
            st.write(f"**{name}：** 当前没有足够的方向性证据，维持中性。")
    st.caption(f"数据置信度沿用财经情报引擎：{impact['confidence']}%")
