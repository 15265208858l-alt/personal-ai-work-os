# 刘强 · Personal AI Work OS — Opportunity Engine V5.0 Decision Edition
from __future__ import annotations

from typing import Any

ASSETS = ["黄金", "美股", "美债", "美元", "原油"]


def _num(v):
    try:
        if v is None or v == "":
            return None
        return float(v)
    except Exception:
        return None


def _asset(f, name):
    return (f.get("market", {}).get(name, {}) or {}) if isinstance(f, dict) else {}


def _macro(f, name):
    return (f.get("macro", {}).get(name, {}) or {}) if isinstance(f, dict) else {}


def _news_items(f):
    items = f.get("news") or []
    if not isinstance(items, list):
        return []
    return [x for x in items if isinstance(x, dict) and x.get("tier") in {"authoritative", "professional"}]


def _news_text(f):
    return " ".join((x.get("title") or "").lower() for x in _news_items(f)[:50])


def _has_any(text, words):
    return any(w in text for w in words)


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
    invalidation = []
    action = "观察"
    entry = "等待更多确认"
    position = "0–5%试探"
    horizon = "短线"
    why_now = "宏观信号尚未形成足够强的共振。"

    if asset == "黄金":
        horizon = "1–4周"
        if dxy is not None:
            if dxy < -1:
                score += 13
                evidence.append(f"美元20日{dxy:+.2f}%，形成黄金顺风")
            elif dxy > 1:
                score -= 13
                risks.append(f"美元20日{dxy:+.2f}%，形成黄金逆风")
        if y10 is not None:
            if y10 < -1:
                score += 9
                evidence.append("美国10Y近期回落，黄金机会成本下降")
            elif y10 > 2:
                score -= 9
                risks.append("美国10Y明显上行，压制黄金估值")
        if y2 is not None and effr is not None:
            spread = y2 - effr
            if spread < 0.8:
                score += 4
                evidence.append(f"2Y与政策利率利差约{spread:.2f}个百分点，降息预期值得跟踪")
        if gold is not None:
            if gold > 12:
                score -= 12
                risks.append(f"黄金20日上涨{gold:.2f}%，短线拥挤，追涨性价比下降")
            elif gold > 5:
                score -= 5
                risks.append("黄金近期上涨较快，新增仓位宜等待回撤")
            elif gold < -5:
                score += 5
                opportunity.append("若美元和利率没有同步反转，回撤可成为分批观察窗口")
        if _has_any(text, ["iran", "war", "attack", "sanction", "conflict", "geopolitical"]):
            score += 7
            evidence.append("权威/专业新闻存在地缘风险线索，避险需求获得支撑")
        opportunity += [
            "黄金最有价值的做多组合是：美元走弱 + 实际利率回落 + 避险升温，至少两项同时成立",
            "如果价格已明显上涨，不因趋势强而追高，优先等待回撤后的宏观条件未破坏",
        ]
        triggers = ["美元继续走弱", "10Y/实际利率继续回落", "Fed宽松预期增强", "地缘风险升级"]
        invalidation = ["美元趋势重新转强", "10Y快速上行", "通胀重新加速并推高实际利率", "地缘风险溢价快速消退"]
        entry = "回撤后若美元、实际利率至少一项继续利多且没有出现明显逆风，再考虑分批"
        position = "5–10%观察仓；强共振后再提高，不建议一次性重仓"
        why_now = "黄金是否值得继续配置，关键不是绝对价格，而是美元、实际利率和避险需求是否继续共振。"
        action = "重点观察；回撤确认后分批，而非追涨" if score >= 60 else "暂缓加仓；等待宏观顺风重新形成"

    elif asset == "美股":
        horizon = "1–3个月"
        if spx is not None:
            if 2 <= spx <= 8:
                score += 9
                evidence.append(f"标普500 20日上涨{spx:.2f}%，趋势相对健康")
            elif spx > 10:
                score -= 10
                risks.append("指数短期涨幅较大，估值与拥挤风险上升")
            elif spx < -5:
                score += 4
                opportunity.append("若盈利预期没有明显恶化，深度回撤后的配置赔率改善")
        if y10 is not None:
            if y10 > 2:
                score -= 10
                risks.append("10Y上行压制高估值权益资产")
            elif y10 < -1:
                score += 8
                evidence.append("10Y回落改善成长股估值环境")
        if y2 is not None and y2 >= 4.25:
            score -= 5
            risks.append(f"2Y约{y2:.2f}%，金融条件仍偏紧")
        if _has_any(text, ["recession", "tariff", "crisis", "earnings warning"]):
            score -= 6
            risks.append("增长、贸易或盈利风险可能放大美股波动")
        opportunity = [
            "优先寻找盈利增长能够覆盖估值压力的板块，而不是简单追逐指数强势",
            "若10Y回落、盈利预期上修且市场出现健康回撤，成长资产的风险收益比改善",
        ]
        triggers = ["10Y停止上行", "盈利预期上修", "Fed预期改善", "市场出现健康回撤"]
        invalidation = ["10Y持续快速上行", "盈利预期连续下修", "信用/增长风险明显恶化"]
        entry = "回撤不破趋势且盈利预期稳定时分批；不建议因单日上涨追入"
        position = "5–15%分批配置，具体比例取决于整体资产配置"
        why_now = "美股机会取决于盈利与利率的组合，而不是单看指数涨跌。"
        action = "观察优先；等待利率或估值提供更好的入场窗口"

    elif asset == "美债":
        horizon = "1–6个月"
        if y10 is not None:
            if y10 < -1:
                score += 14
                evidence.append(f"10Y收益率20日{y10:+.2f}%，利于债券价格")
            elif y10 > 2:
                score -= 13
                risks.append(f"10Y收益率20日上升{y10:.2f}%，债券价格承压")
        if y2 is not None and y2 >= 4.25:
            score -= 4
            risks.append("2Y仍高，降息交易尚未充分确认")
        opportunity = [
            "美债真正的交易变量是未来收益率方向；高票息本身不是充分买入理由",
            "若通胀继续降温、就业转弱并带动Fed转鸽，中长期美债赔率明显改善",
        ]
        triggers = ["CPI/PCE继续降温", "就业明显走弱", "Fed转鸽", "10Y趋势反转向下"]
        invalidation = ["通胀重新加速", "Fed重新转鹰", "10Y突破并持续上行"]
        entry = "等待收益率出现明确拐点，再考虑分批配置中长期久期"
        position = "5–15%防御/利率交易仓，避免把全部资金押注单一降息路径"
        why_now = "美债的核心机会来自利率拐点，而不是单纯看到收益率高。"
        action = "等待利率拐点；暂不把高收益率本身当成买入信号"

    elif asset == "美元":
        horizon = "2–8周"
        if dxy is not None:
            if dxy > 1:
                score += 10
                evidence.append(f"美元20日上涨{dxy:.2f}%，趋势偏强")
            elif dxy < -1:
                score -= 10
                risks.append(f"美元20日下跌{abs(dxy):.2f}%，趋势偏弱")
        if y2 is not None and y2 >= 4.25:
            score += 3
            evidence.append("美国短端利率仍高，对美元提供一定利差支撑")
        opportunity = [
            "美元更适合作为全球资产风险温度计，而不是孤立追涨交易",
            "美元继续走弱通常利好黄金、部分非美风险资产和大宗商品，但若风险厌恶升级也可能重新走强",
        ]
        triggers = ["美国利率预期上修", "美元趋势重新转强", "全球避险资金回流美元"]
        invalidation = ["Fed明显转鸽", "美国利差继续收窄", "美元跌势延续"]
        entry = "不以弱势美元本身作为交易理由，重点观察利差与全球风险偏好变化"
        position = "以资产配置对冲为主，不建议单独重仓押注美元方向"
        why_now = "美元是其他资产的重要传导变量，当前更重要的是判断它会不会反转。"
        action = "偏弱观察；重点观察其对黄金和风险资产的传导"

    elif asset == "原油":
        horizon = "1–8周"
        if oil is not None:
            if oil > 5:
                score += 10
                evidence.append(f"原油20日上涨{oil:.2f}%，趋势偏强")
            elif oil < -5:
                score -= 8
                risks.append(f"原油20日下跌{abs(oil):.2f}%，需求/供给预期偏弱")
        if _has_any(text, ["iran", "war", "attack", "sanction", "conflict"]):
            score += 8
            evidence.append("地缘风险可能抬升原油风险溢价")
        if _has_any(text, ["recession", "demand slowdown", "weak demand"]):
            score -= 6
            risks.append("增长放缓可能压制原油需求")
        opportunity = [
            "先区分地缘风险推动的上涨与真实需求推动的上涨，再决定是否追涨",
            "油价持续上行会重新推高通胀预期，从而压制降息交易并影响美债、美股估值",
        ]
        triggers = ["地缘冲突升级", "OPEC+供给变化", "全球需求预期上修"]
        invalidation = ["地缘溢价快速消退", "需求预期下修", "库存持续增加"]
        entry = "地缘冲高不追；等供需数据确认后再决定是否参与"
        position = "0–10%卫星仓，严格控制波动风险"
        why_now = "原油最大的价值是观察通胀与地缘风险的传导，而不是简单追逐涨跌。"
        action = "观察为主；地缘驱动上涨不宜盲目追高"

    missing = sum(v is None for v in (dxy, y10, y2))
    if missing >= 2:
        score -= 5
        risks.append("关键宏观变量缺失，判断置信度下降")
    if confidence < 60:
        score -= 4
        risks.append(f"底层数据置信度仅{confidence:.0f}%")

    score = max(0, min(100, round(score)))
    direction = "偏多" if score >= 62 else "偏空" if score <= 38 else "震荡"
    level = "⭐⭐⭐⭐⭐" if score >= 80 else "⭐⭐⭐⭐" if score >= 70 else "⭐⭐⭐" if score >= 60 else "⭐⭐" if score >= 45 else "⭐"

    return {
        "asset": asset,
        "score": score,
        "direction": direction,
        "level": level,
        "evidence": evidence[:6],
        "risks": risks[:6],
        "triggers": triggers[:6],
        "opportunity": opportunity[:4],
        "action": action,
        "entry_condition": entry,
        "position": position,
        "why_now": why_now,
        "invalidation": invalidation[:4],
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
            "plan": f"情景模型：回撤观察区约{p*0.985:.2f}–{p*0.97:.2f}；向上突破约{p*1.01:.2f}可作为趋势确认参考。该区间是模型化观察带，不是真实技术支撑/压力位。",
        }
    return {"current": p, "plan": "价格可用；缺少完整技术序列时不虚构支撑/压力位。"}


def _cross_asset_impacts(rows):
    by = {x["asset"]: x for x in rows}
    out = []
    gold = by.get("黄金", {}).get("score", 50)
    dollar = by.get("美元", {}).get("score", 50)
    oil = by.get("原油", {}).get("score", 50)
    bonds = by.get("美债", {}).get("score", 50)
    stocks = by.get("美股", {}).get("score", 50)

    if gold >= 60 and dollar <= 45:
        out.append("黄金←美元：美元偏弱与黄金偏强形成同向验证，黄金信号可信度高于单看价格。")
    if oil >= 60:
        out.append("原油→通胀→利率：油价上行若持续，可能抬高通胀预期、延后宽松，对长久期美债和高估值美股形成压力。")
    if bonds >= 60 and stocks >= 55:
        out.append("美债→美股：收益率回落通常改善成长股估值环境，但必须有盈利预期稳定配合。")
    if dollar <= 45:
        out.append("美元走弱→全球资产：通常利好黄金、大宗商品及部分非美风险资产；若同时出现衰退式避险，美元可能反向走强。")
    if stocks <= 40 and bonds >= 60:
        out.append("风险切换：若美股偏弱而美债偏强，资金可能从风险资产向防御资产迁移，应降低高估值资产暴露。")
    if not out:
        out.append("当前资产信号尚未形成强共振，暂不把单一资产信号升级为高置信度交易机会。")
    return out[:6]


def _decision_text(top, confidence):
    if not top:
        return "当前没有达到观察阈值的机会，系统选择等待。"
    lead = top[0]
    if lead["score"] >= 70:
        return f"当前第一优先级是【{lead['asset']}】。信号达到重点观察区，但仍需等待触发条件，不把评分当成收益率预测。"
    if lead["score"] >= 60:
        return f"当前第一优先级是【{lead['asset']}】。属于条件型机会，只有触发器出现后才值得提高仓位。"
    return f"当前【{lead['asset']}】相对占优，但还没有形成足够强的交易优势，以观察为主。"


def analyze_opportunities(finance_result: dict[str, Any]):
    rows = []
    for asset in ASSETS:
        row = _score(asset, finance_result)
        row["price_plan"] = _price_plan(asset, finance_result)
        rows.append(row)

    ranked = sorted(rows, key=lambda x: x["score"], reverse=True)
    strong = [x for x in ranked if x["score"] >= 70]
    conditional = [x for x in ranked if 60 <= x["score"] < 70]
    top = (strong + conditional)[:3]
    risks = sorted(rows, key=lambda x: x["score"])[:3]
    confidence = _num(finance_result.get("confidence")) or 0

    return {
        "version": "V5.0",
        "assets": rows,
        "top_opportunities": top,
        "top_risks": risks,
        "cross_asset_impacts": _cross_asset_impacts(rows),
        "confidence": confidence,
        "decision": _decision_text(top, confidence),
        "decision_rule": "≥70重点机会；60–69条件型机会；45–59观察；≤40降低暴露。评分不是收益率预测。",
        "disclaimer": "本模块用于研究和情景决策，不构成收益保证；价格、新闻和宏观数据若缺失，系统不会虚构结论。",
    }


def render_opportunities(data: dict[str, Any]) -> None:
    import streamlit as st

    r = data if isinstance(data, dict) and isinstance(data.get("assets"), list) else analyze_opportunities(data)
    version = r.get("version", "V5.0")

    st.markdown(f"## 🎯 投资机会雷达 {version}")
    st.caption(f"决策版：趋势 + 利率 + 美元 + 权威/专业新闻 + 拥挤度 + 数据质量；置信度 {r.get('confidence', 0):.0f}%。评分不是收益率预测。")

    st.markdown("### 🧭 今日核心结论")
    st.info(r.get("decision", "当前没有足够强的机会。"))

    tops = r.get("top_opportunities", [])
    if tops:
        st.markdown("### 🎯 具体机会在哪里")
        for x in tops:
            st.markdown(f"#### {x['level']} {x['asset']}｜{x['direction']}｜{x['score']}/100")
            st.write(f"**为什么现在关注：** {x.get('why_now', '')}")
            st.write(f"**建议动作：** {x.get('action', '')}")
            st.write(f"**入场条件：** {x.get('entry_condition', '')}")
            st.write(f"**参考仓位：** {x.get('position', '')}")
            st.write(f"**观察周期：** {x.get('horizon', '')}")
            pp = x.get("price_plan", {})
            if pp.get("current") is not None:
                st.write(f"**当前价格：** {pp['current']}")
                st.write(f"**价格计划：** {pp.get('plan', '')}")
            if x.get("evidence"):
                st.write("**数据证据：** " + "；".join(x["evidence"]))
            if x.get("triggers"):
                st.write("**下一步等什么：** " + "；".join(x["triggers"]))
            if x.get("invalidation"):
                st.write("**观点失效条件：** " + "；".join(x["invalidation"]))
            if x.get("risks"):
                st.warning("主要风险：" + "；".join(x["risks"]))
            st.divider()
    else:
        st.write("暂无达到观察阈值的资产机会，系统选择等待。")

    st.markdown("### 🌐 五大资产传导影响")
    for item in r.get("cross_asset_impacts", []):
        st.write("• " + item)

    st.markdown("### 📊 资产机会排名")
    for x in sorted(r.get("assets", []), key=lambda z: z.get("score", 0), reverse=True):
        st.write(f"{x['level']} **{x['asset']}**｜{x['direction']}｜{x['score']}/100｜{x['action']}")

    st.markdown("### 🚨 风险优先级")
    for x in r.get("top_risks", []):
        risk_text = "；".join(x.get("risks", [])) or "当前主要是等待确认，而非明确风险事件。"
        st.warning(f"{x['asset']}｜{x['score']}/100：{risk_text}")

    st.caption(r.get("decision_rule", ""))
    st.caption(r.get("disclaimer", ""))
