# 刘强 · Personal AI Work OS — Opportunity Engine V4.1 Decision Edition
from __future__ import annotations
from typing import Any

ASSETS = ["黄金", "美股", "美债", "美元", "原油"]


def _num(v):
    try:
        return float(v) if v is not None else None
    except Exception:
        return None


def _asset(f, a):
    return f.get("market", {}).get(a, {}) or {}


def _macro(f, a):
    return f.get("macro", {}).get(a, {}) or {}


def _news_text(f):
    trusted = [x for x in (f.get("news") or []) if x.get("tier") in {"authoritative", "professional"}]
    return " ".join((x.get("title") or "").lower() for x in trusted[:40])


def _score(asset, f):
    dxy = _num(_asset(f, "美元指数").get("change_20d"))
    y10 = _num(_asset(f, "美国10Y").get("change_20d"))
    spx = _num(_asset(f, "标普500").get("change_20d"))
    gold = _num(_asset(f, "黄金期货").get("change_20d"))
    oil = _num(_asset(f, "原油期货").get("change_20d"))
    y2 = _num(_macro(f, "2Y收益率").get("value"))
    effr = _num(_macro(f, "联邦基金有效利率").get("value"))
    confidence = _num(f.get("confidence")) or 0
    text = _news_text(f)

    score = 50
    evidence, risks, triggers, opportunity = [], [], [], []
    action = "观察"
    invalidation = []
    horizon = "短线"

    if asset == "黄金":
        horizon = "1–4周"
        if dxy is not None:
            if dxy < -1:
                score += 13; evidence.append(f"美元20日{dxy:+.2f}%，对黄金形成顺风")
            elif dxy > 1:
                score -= 13; risks.append(f"美元20日{dxy:+.2f}%，对黄金形成逆风")
        if y10 is not None:
            if y10 < -1:
                score += 9; evidence.append("美国10Y近期回落，持有黄金的利率机会成本下降")
            elif y10 > 2:
                score -= 9; risks.append("美国10Y上行，对黄金估值形成压制")
        if y2 is not None and effr is not None and y2 - effr < 0.8:
            score += 4; evidence.append("短端利率与政策利率利差较窄，宽松预期值得跟踪")
        if gold is not None:
            if gold > 12:
                score -= 12; risks.append(f"黄金20日上涨{gold:.2f}%，短线拥挤度较高，不宜追涨")
            elif gold > 5:
                score -= 5; risks.append("黄金近期上涨较快，新增仓位应等待回撤")
            elif gold < -5:
                score += 5; opportunity.append("若美元和利率没有反转，回撤可作为分批观察窗口")
        if any(k in text for k in ["iran", "war", "attack", "sanction", "conflict", "geopolitical"]):
            score += 7; evidence.append("权威/专业新闻存在地缘风险线索，避险需求获得支撑")
        opportunity += [
            "核心逻辑：美元走弱/实际利率回落/避险升温至少两项同时成立时，黄金胜率更高",
            "当前位置更适合等待回撤确认，而不是因为趋势强就直接追高",
        ]
        triggers = ["美元继续走弱", "10Y/实际利率继续回落", "Fed宽松预期增强", "地缘风险升级"]
        invalidation = ["美元20日趋势转强", "10Y快速上行", "地缘风险溢价明显消退"]
        action = "重点观察；若回撤且美元/利率没有反转，可考虑分批布局" if score >= 60 else "持有观察；等待宏观顺风重新形成"

    elif asset == "美股":
        horizon = "1–3个月"
        if spx is not None:
            if 2 <= spx <= 8:
                score += 9; evidence.append(f"标普500 20日上涨{spx:.2f}%，趋势尚健康")
            elif spx > 10:
                score -= 10; risks.append("指数短期涨幅较大，估值/拥挤风险上升")
            elif spx < -5:
                score += 4; opportunity.append("若盈利预期没有同步恶化，深度回撤才更具配置价值")
        if y10 is not None:
            if y10 > 2:
                score -= 10; risks.append("10Y上行压制高估值权益资产")
            elif y10 < -1:
                score += 8; evidence.append("10Y回落改善权益估值环境")
        if y2 is not None and y2 >= 4.25:
            score -= 5; risks.append(f"2Y约{y2:.2f}%，金融条件仍偏紧")
        if any(k in text for k in ["recession", "tariff", "crisis"]):
            score -= 6; risks.append("增长/政策风险可能放大美股波动")
        opportunity = [
            "不是指数越强越值得买；重点寻找盈利增长能够覆盖估值压力的板块",
            "若10Y回落且盈利预期上修，科技/成长风格的风险收益比改善",
        ]
        triggers = ["10Y停止上行", "盈利预期上修", "Fed预期改善", "市场出现健康回撤"]
        invalidation = ["10Y持续快速上行", "盈利预期连续下修", "信用/增长风险明显恶化"]
        action = "观察优先；不追高，等待利率或估值提供更好的入场窗口"

    elif asset == "美债":
        horizon = "1–6个月"
        if y10 is not None:
            if y10 < -1:
                score += 14; evidence.append(f"10Y收益率20日{y10:+.2f}%，利于债券价格")
            elif y10 > 2:
                score -= 13; risks.append(f"10Y收益率20日上升{y10:.2f}%，债券价格承压")
        if y2 is not None and y2 >= 4.25:
            score -= 4; risks.append("2Y仍高，降息交易尚未充分确认")
        opportunity = [
            "债券真正的交易变量是未来收益率方向；降息确认比当前高票息更重要",
            "若通胀继续降温且就业转弱，中长期美债的赔率明显改善",
        ]
        triggers = ["CPI/PCE继续降温", "就业明显走弱", "Fed转鸽", "10Y趋势反转向下"]
        invalidation = ["通胀重新加速", "Fed重新转鹰", "10Y突破并持续上行"]
        action = "等待利率拐点；目前不把高收益率本身当成买入信号"

    elif asset == "美元":
        horizon = "2–8周"
        if dxy is not None:
            if dxy > 1:
                score += 10; evidence.append(f"美元20日上涨{dxy:.2f}%，趋势偏强")
            elif dxy < -1:
                score -= 10; risks.append(f"美元20日下跌{abs(dxy):.2f}%，趋势偏弱")
        if y2 is not None and y2 >= 4.25:
            score += 3; evidence.append("美国短端利率仍高，对美元提供一定利差支撑")
        opportunity = [
            "美元更适合作为全球资产风险温度计，而不是单独追涨交易",
            "美元继续走弱通常利好黄金、部分新兴市场及大宗商品风险偏好",
        ]
        triggers = ["美国利率预期上修", "美元趋势重新转强", "全球避险资金回流美元"]
        invalidation = ["Fed明显转鸽", "美国利差继续收窄", "美元跌势延续"]
        action = "偏弱观察；若美元继续下行，优先关注其对黄金和风险资产的传导"

    elif asset == "原油":
        horizon = "1–8周"
        if oil is not None:
            if oil > 5:
                score += 10; evidence.append(f"原油20日上涨{oil:.2f}%，趋势偏强")
            elif oil < -5:
                score -= 8; risks.append(f"原油20日下跌{abs(oil):.2f}%，需求/供给预期偏弱")
        if any(k in text for k in ["iran", "war", "attack", "sanction", "conflict"]):
            score += 8; evidence.append("地缘风险可能抬升原油风险溢价")
        if any(k in text for k in ["recession", "demand slowdown"]):
            score -= 6; risks.append("增长放缓可能压制原油需求")
        opportunity = [
            "先区分地缘风险推动的上涨与真实需求推动的上涨，再决定是否追涨",
            "油价持续上行会重新推高通胀预期，从而反过来压制降息交易",
        ]
        triggers = ["地缘冲突升级", "OPEC+供给变化", "全球需求预期上修"]
        invalidation = ["地缘溢价快速消退", "需求预期下修", "库存持续增加"]
        action = "观察为主；地缘驱动上涨不宜盲目追高"

    missing = sum(v is None for v in (dxy, y10, y2))
    if missing >= 2:
        score -= 5; risks.append("关键宏观变量缺失，判断置信度下降")
    if confidence < 60:
        score -= 4; risks.append(f"底层数据置信度仅{confidence:.0f}%")
    score = max(0, min(100, round(score)))
    direction = "偏多" if score >= 62 else "偏空" if score <= 38 else "震荡"
    level = "⭐⭐⭐⭐⭐" if score >= 80 else "⭐⭐⭐⭐" if score >= 70 else "⭐⭐⭐" if score >= 60 else "⭐⭐" if score >= 45 else "⭐"
    return {
        "asset": asset, "score": score, "direction": direction, "level": level,
        "evidence": evidence[:6], "risks": risks[:6], "triggers": triggers[:6],
        "opportunity": opportunity[:4], "action": action, "invalidation": invalidation[:4],
        "horizon": horizon,
    }


def _price_plan(asset, f):
    source = "黄金期货" if asset == "黄金" else asset
    p = _num(_asset(f, source).get("price"))
    if p is None and asset == "黄金":
        p = _num(_asset(f, "黄金").get("price"))
    if p is None:
        return {"current": None, "plan": "当前没有可靠价格，不生成虚构价位。"}
    if asset == "黄金":
        return {
            "current": p,
            "plan": f"参考模型：回撤观察区 {p*.985:.2f}–{p*.97:.2f}；突破确认 {p*1.01:.2f}；保护参考 {p*.97:.2f}。仅作情景模型，不替代实时技术位。",
        }
    return {"current": p, "plan": "价格可用；缺少完整技术序列时不虚构支撑/压力位。"}


def _cross_asset_impacts(rows):
    by = {x["asset"]: x for x in rows}
    out = []
    if by.get("黄金", {}).get("score", 50) >= 60 and by.get("美元", {}).get("score", 50) <= 45:
        out.append("黄金/美元：美元偏弱与黄金偏强形成同向验证，黄金优先级高于单独看黄金价格。")
    if by.get("原油", {}).get("score", 50) >= 60:
        out.append("原油→通胀→利率：油价上行若持续，可能抬高通胀预期并延后宽松，对长久期美债和高估值美股形成压力。")
    if by.get("美债", {}).get("score", 50) >= 60:
        out.append("美债→美股：收益率回落通常改善成长股估值环境，但需要盈利预期没有恶化配合。")
    if by.get("美元", {}).get("score", 50) <= 45:
        out.append("美元走弱→全球资产：通常利好黄金、大宗商品及部分非美风险资产，但需警惕美国增长恶化导致的‘风险厌恶式美元走强’反转。")
    if not out:
        out.append("当前资产信号尚未形成强共振，暂不把单一资产信号升级为高置信度交易机会。")
    return out[:5]


def analyze_opportunities(finance_result: dict[str, Any]):
    rows = []
    for a in ASSETS:
        r = _score(a, finance_result)
        r["price_plan"] = _price_plan(a, finance_result)
        rows.append(r)
    ranked = sorted(rows, key=lambda x: x["score"], reverse=True)
    strong = [x for x in ranked if x["score"] >= 70]
    conditional = [x for x in ranked if 60 <= x["score"] < 70]
    return {
        "version": "V4.1",
        "assets": rows,
        "top_opportunities": (strong + conditional)[:3],
        "top_risks": [x for x in ranked if x["score"] <= 40][:3],
        "cross_asset_impacts": _cross_asset_impacts(rows),
        "confidence": finance_result.get("confidence", 0),
        "decision_rule": "≥70重点机会；60-69有条件机会；45-59观察；≤40降低暴露。评分不是收益率预测。",
    }


def render_opportunities(data: dict[str, Any]) -> None:
    import streamlit as st
    r = data if isinstance(data, dict) and isinstance(data.get("assets"), list) and "top_opportunities" in data else analyze_opportunities(data)
    st.markdown(f"## 🎯 投资机会雷达 {r.get('version', 'V4.1')}")
    st.caption(f"决策版：趋势 + 利率 + 美元 + 权威/专业新闻 + 拥挤度 + 数据质量；置信度 {r.get('confidence', 0)}%。")

    st.markdown("### 🧭 今日一句话结论")
    tops = r.get("top_opportunities", [])
    if tops:
        lead = tops[0]
        st.info(f"**首要关注：{lead['asset']}｜{lead['direction']}｜{lead['score']}/100。** {lead['action']}；核心不是追涨，而是等待关键触发器。")
    else:
        st.info("当前没有形成高置信度机会，系统选择等待，而不是强行推荐。")

    st.markdown("### 🎯 今日重点机会")
    if tops:
        for x in tops:
            st.markdown(f"#### {x['level']} {x['asset']}｜{x['direction']}｜{x['score']}/100")
            st.write(f"**建议动作：** {x['action']}")
            st.write(f"**观察周期：** {x['horizon']}")
            pp = x.get("price_plan", {})
            if pp.get("current") is not None:
                st.write(f"**当前价格：** {pp['current']}")
                st.write(f"**价格计划：** {pp.get('plan', '')}")
            st.write("**为什么关注：** " + "；".join(x.get("opportunity", [])))
            if x.get("evidence"):
                st.write("**数据证据：** " + "；".join(x["evidence"]))
            st.write("**下一步等什么：** " + "；".join(x.get("triggers", [])))
            if x.get("invalidation"):
                st.write("**观点失效条件：** " + "；".join(x["invalidation"]))
            if x.get("risks"):
                st.write("**主要风险：** " + "；".join(x["risks"]))
            st.divider()
    else:
        st.write("暂无高置信度机会。")

    st.markdown("### 🌐 五大资产传导影响")
    for item in r.get("cross_asset_impacts", []):
        st.write("• " + item)

    st.markdown("### 📊 资产机会排名")
    for x in sorted(r.get("assets", []), key=lambda z: z.get("score", 0), reverse=True):
        st.write(f"{x['level']} **{x['asset']}**｜{x['direction']}｜{x['score']}/100｜{x['action']}")

    if r.get("top_risks"):
        st.markdown("### 🚨 风险优先级")
        for x in r["top_risks"]:
            st.warning(f"{x['asset']}｜{x['score']}/100：" + "；".join(x.get("risks", [])))
    st.caption(r.get("decision_rule", ""))
