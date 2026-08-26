# 刘强 · Personal AI Work OS — Portfolio Decision Engine V2.0
from __future__ import annotations
from typing import Any


def _num(v):
    try:
        if v is None or v == "":
            return None
        return float(v)
    except Exception:
        return None


def _bucket(score: float | None):
    if score is None:
        return "数据不足"
    if score >= 70:
        return "强"
    if score >= 60:
        return "条件型"
    if score >= 45:
        return "观察"
    return "偏弱"


def _stock_action(x: dict[str, Any]) -> str:
    s = _num(x.get("research_score")) or 0
    current = _num(x.get("current_price"))
    entry = _num(x.get("entry_price"))
    heavy = _num(x.get("heavy_price"))
    if current is not None and entry is not None and current <= entry:
        return "进入建仓观察区"
    if current is not None and heavy is not None and current <= heavy:
        return "接近重仓参考区，先复核基本面"
    if s >= 85:
        return "重点跟踪，等待价格"
    if s >= 75:
        return "观察，等待估值改善"
    return "暂不进入机会仓"


def build_portfolio_decision(finance: dict[str, Any], opportunity: dict[str, Any], research: dict[str, Any]) -> dict[str, Any]:
    confidence = _num(finance.get("confidence")) or _num(opportunity.get("confidence")) or 0
    assets = {x.get("asset"): x for x in opportunity.get("assets", []) if isinstance(x, dict)}
    shortlist = research.get("shortlist", []) if isinstance(research, dict) else []
    watchlist = research.get("watchlist", []) if isinstance(research, dict) else []

    gold = _num(assets.get("黄金", {}).get("score"))
    stocks = _num(assets.get("美股", {}).get("score"))
    bonds = _num(assets.get("美债", {}).get("score"))
    oil = _num(assets.get("原油", {}).get("score"))

    mode = "谨慎模式" if confidence < 70 else "正常模式"
    cash_floor = 45 if confidence < 70 else 30

    # 基础框架：现金优先，机会出现后再释放仓位。
    allocation = {
        "现金/低波动": cash_floor,
        "黄金/贵金属": 10,
        "A股机会仓": 5,
        "美股/权益": 15,
        "美债/利率资产": 15,
        "原油/商品": 5,
    }
    reasons: list[str] = []
    constraints: list[str] = []

    # 资产级机会释放仓位
    if gold is not None and gold >= 70:
        allocation["黄金/贵金属"] += 5
        allocation["现金/低波动"] -= 5
        reasons.append("黄金进入强机会区，可从现金中释放一部分风险预算")
    elif gold is not None and gold >= 60:
        reasons.append("黄金为条件型机会，保留观察仓，不追涨")

    if stocks is not None and stocks >= 70:
        allocation["美股/权益"] += 5
        allocation["现金/低波动"] -= 5
        reasons.append("美股风险资产信号较强，可提高权益关注度")
    elif stocks is not None and stocks >= 60:
        reasons.append("美股属于条件型机会，等待利率与盈利确认")

    if bonds is not None and bonds >= 70:
        allocation["美债/利率资产"] += 5
        allocation["现金/低波动"] -= 5
        reasons.append("美债进入强机会区，收益率拐点值得配置")

    if oil is not None and oil >= 75:
        allocation["原油/商品"] += 3
        allocation["现金/低波动"] -= 3
        reasons.append("原油风险溢价偏强，但仍限制商品仓位")

    # A股机会仓严格绑定深度研究结果
    actionable_stocks = []
    for x in shortlist:
        y = dict(x)
        y["portfolio_action"] = _stock_action(y)
        actionable_stocks.append(y)

    if actionable_stocks:
        top_score = max((_num(x.get("research_score")) or 0) for x in actionable_stocks)
        if top_score >= 85 and confidence >= 70:
            allocation["A股机会仓"] = 10
            allocation["现金/低波动"] -= 5
            reasons.append("存在高质量A股深度研究候选，A股机会仓提高至10%模型上限")
        elif top_score >= 75:
            allocation["A股机会仓"] = 7
            allocation["现金/低波动"] -= 2
            reasons.append("存在通过基本面验证的A股候选，但价格条件尚未完全确认")
    else:
        constraints.append("没有通过深度研究阈值的A股候选，A股机会仓保持低配")

    if mode == "谨慎模式":
        constraints.append(f"数据置信度{confidence:.0f}%<70%，现金/低波动仓位不得低于{cash_floor}%")

    # 保证合计100并避免负仓位
    for k in allocation:
        allocation[k] = max(0, allocation[k])
    total = sum(allocation.values())
    allocation = {k: round(v / total * 100) for k, v in allocation.items()}
    diff = 100 - sum(allocation.values())
    allocation["现金/低波动"] += diff

    # 今日最终动作：按最值得关注的机会与A股候选共同决定
    ranked_assets = sorted(assets.values(), key=lambda x: _num(x.get("score")) or -1, reverse=True)
    top_asset = ranked_assets[0] if ranked_assets else {}
    top_asset_name = top_asset.get("asset", "暂无")
    top_asset_score = _num(top_asset.get("score"))

    if actionable_stocks:
        top_stock = sorted(actionable_stocks, key=lambda x: _num(x.get("research_score")) or -1, reverse=True)[0]
        next_action = f"重点跟踪 {top_stock.get('name','未知')}（{top_stock.get('code','')}），{top_stock.get('portfolio_action','观察')}"
    elif top_asset_score is not None and top_asset_score >= 70:
        next_action = f"第一优先级关注 {top_asset_name}，按触发条件分批，不追单日波动"
    elif top_asset_score is not None and top_asset_score >= 60:
        next_action = f"第一优先级观察 {top_asset_name}，等待核心触发条件确认"
    else:
        next_action = "暂不扩大风险仓，保持现金/低波动资产，等待更强共振"

    return {
        "version": "V2.0",
        "mode": mode,
        "confidence": confidence,
        "model_allocation": allocation,
        "reasons": reasons,
        "constraints": constraints,
        "next_action": next_action,
        "top_asset": top_asset_name,
        "top_asset_score": top_asset_score,
        "shortlist_count": len(shortlist),
        "watchlist_count": len(watchlist),
        "stock_actions": actionable_stocks[:3],
        "rules": [
            "单一新闻不触发重仓；至少两个独立变量形成共振。",
            "趋势成立但价格过热时，优先等待回撤。",
            "A股机会仓必须通过ValueStock基本面、数据质量和估值/价格验证。",
            "数据置信度不足70%时，自动进入谨慎模式并提高现金比例。",
        ],
        "discipline": "这里是模型仓位框架，不是实际账户仓位；真实执行需要结合你的实际资产、风险承受能力和流动性需求。",
    }


def render_portfolio_decision(data: dict[str, Any]) -> None:
    import streamlit as st
    st.divider()
    st.markdown("## 💰 投资组合与仓位决策中心 V2.0")
    st.caption(data.get("discipline", ""))

    c1, c2, c3 = st.columns(3)
    c1.metric("决策模式", data.get("mode", "观察"))
    c2.metric("数据置信度", f"{data.get('confidence', 0):.0f}%")
    c3.metric("第一关注", f"{data.get('top_asset','暂无')} {data.get('top_asset_score','')}" if data.get('top_asset') else "暂无")

    st.markdown("### 🎯 今天应该怎么做")
    st.success(data.get("next_action", "保持观察"))

    st.markdown("### 📊 模型仓位框架")
    cols = st.columns(3)
    items = list(data.get("model_allocation", {}).items())
    for i, (k, v) in enumerate(items):
        cols[i % 3].metric(k, f"{v}%")

    if data.get("reasons"):
        st.markdown("### ✅ 配置依据")
        for x in data["reasons"]:
            st.write("• " + x)
    if data.get("constraints"):
        st.markdown("### 🚧 当前约束")
        for x in data["constraints"]:
            st.warning(x)

    if data.get("stock_actions"):
        st.markdown("### 📈 A股候选仓位动作")
        for x in data["stock_actions"]:
            st.write(f"**{x.get('name','未知')}（{x.get('code','')}）**｜研究评分 {x.get('research_score','暂无')}/100｜{x.get('portfolio_action','观察')}")
            st.caption(f"当前价 {x.get('current_price','暂无')}｜建仓参考 {x.get('entry_price','暂无')}｜重仓参考 {x.get('heavy_price','暂无')}")

    st.markdown("### 🧭 仓位纪律")
    for i, rule in enumerate(data.get("rules", []), 1):
        st.write(f"{i}. {rule}")
