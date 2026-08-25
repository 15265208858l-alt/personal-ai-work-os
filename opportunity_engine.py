# 刘强 · Personal AI Work OS — Opportunity Engine V4.0
from __future__ import annotations
from typing import Any

ASSETS = ["黄金", "美股", "美债", "美元", "原油"]

def _num(v):
    try: return float(v) if v is not None else None
    except Exception: return None

def _asset(f, a): return f.get("market", {}).get(a, {}) or {}
def _macro(f, a): return f.get("macro", {}).get(a, {}) or {}

def _news_text(f):
    trusted = [x for x in (f.get("news") or []) if x.get("tier") in {"authoritative", "professional"}]
    return " ".join((x.get("title") or "").lower() for x in trusted[:30])

def _score(asset, f):
    dxy = _num(_asset(f,"美元指数").get("change_20d")); y10 = _num(_asset(f,"美国10Y").get("change_20d"))
    spx = _num(_asset(f,"标普500").get("change_20d")); gold = _num(_asset(f,"黄金期货").get("change_20d")); oil = _num(_asset(f,"原油期货").get("change_20d"))
    y2 = _num(_macro(f,"2Y收益率").get("value")); effr = _num(_macro(f,"联邦基金有效利率").get("value")); confidence = _num(f.get("confidence")) or 0
    text = _news_text(f); score = 50; evidence=[]; risks=[]; triggers=[]; opportunity=[]

    if asset == "黄金":
        if dxy is not None:
            if dxy < -1: score += 13; evidence.append(f"美元20日{dxy:+.2f}%，形成黄金顺风")
            elif dxy > 1: score -= 13; risks.append(f"美元20日{dxy:+.2f}%，形成黄金逆风")
        if y10 is not None:
            if y10 < -1: score += 9; evidence.append("10Y收益率20日回落，利率环境改善")
            elif y10 > 2: score -= 9; risks.append("10Y收益率上行，对黄金形成压制")
        if y2 is not None and effr is not None and y2-effr < .8:
            score += 4; evidence.append("短端利率与政策利率利差收窄，宽松预期值得跟踪")
        if gold is not None:
            if gold > 12: score -= 12; risks.append(f"黄金20日上涨{gold:.2f}%，短线拥挤度较高")
            elif gold > 5: score -= 5; risks.append("黄金近期上涨较快，追涨性价比下降")
            elif gold < -5: score += 5; opportunity.append("若宏观支撑未破坏，回撤可作为分批观察窗口")
        if any(k in text for k in ["iran","war","attack","sanction","conflict","geopolitical"]):
            score += 7; evidence.append("权威/专业新闻存在地缘风险线索，避险需求获得支撑")
        opportunity.append("核心观察：美元、实际利率/10Y、Fed预期与地缘风险是否继续同向")
        triggers += ["美元继续走弱","10Y/实际利率回落","Fed宽松预期增强"]

    elif asset == "美股":
        if spx is not None:
            if 2 <= spx <= 8: score += 9; evidence.append(f"标普20日上涨{spx:.2f}%，趋势健康")
            elif spx > 10: score -= 10; risks.append("指数短期涨幅过大，拥挤风险上升")
            elif spx < -5: score += 4; opportunity.append("若盈利预期稳定，深度回撤可进入观察区")
        if y10 is not None:
            if y10 > 2: score -= 10; risks.append("10Y上行压制权益估值")
            elif y10 < -1: score += 8; evidence.append("10Y回落改善权益估值环境")
        if y2 is not None and y2 >= 4.25: score -= 5; risks.append(f"2Y约{y2:.2f}%，金融条件仍偏紧")
        if any(k in text for k in ["recession","tariff","crisis"]): score -= 6; risks.append("增长/政策风险可能放大波动")
        opportunity.append("重点看盈利增长能否覆盖估值压力，而不是只看指数涨跌")
        triggers += ["10Y停止上行","盈利预期上修","Fed预期改善"]

    elif asset == "美债":
        if y10 is not None:
            if y10 < -1: score += 14; evidence.append(f"10Y收益率20日{y10:+.2f}%，利于债券价格")
            elif y10 > 2: score -= 13; risks.append(f"10Y收益率20日上升{y10:.2f}%，债券价格承压")
        if y2 is not None and y2 >= 4.25: score -= 4; risks.append("2Y仍高，降息交易尚未充分确认")
        opportunity.append("债券机会取决于未来收益率方向，而非当前收益率高低")
        triggers += ["CPI/PCE继续降温","就业明显走弱","Fed转鸽"]

    elif asset == "美元":
        if dxy is not None:
            if dxy > 1: score += 10; evidence.append(f"美元20日上涨{dxy:.2f}%")
            elif dxy < -1: score -= 10; risks.append(f"美元20日下跌{abs(dxy):.2f}%，趋势偏弱")
        if y2 is not None and y2 >= 4.25: score += 3; evidence.append("美国短端利率仍高，提供一定利差支撑")
        opportunity.append("美元方向重点观察Fed预期与美欧利差")
        triggers += ["美国利率预期上修","美元趋势反转"]

    elif asset == "原油":
        if oil is not None:
            if oil > 5: score += 10; evidence.append(f"原油20日上涨{oil:.2f}%，趋势偏强")
            elif oil < -5: score -= 8; risks.append(f"原油20日下跌{abs(oil):.2f}%，需求/供给预期偏弱")
        if any(k in text for k in ["iran","war","attack","sanction","conflict"]): score += 8; evidence.append("地缘风险可能抬升原油风险溢价")
        if any(k in text for k in ["recession","demand slowdown"]): score -= 6; risks.append("增长放缓可能压制原油需求")
        opportunity.append("区分地缘风险推动的上涨与真实需求推动的上涨")
        triggers += ["地缘冲突升级","OPEC+供给变化","全球需求预期上修"]

    missing = sum(v is None for v in (dxy,y10,y2))
    if missing >= 2: score -= 5; risks.append("关键宏观变量缺失，判断置信度下降")
    if confidence < 60: score -= 4; risks.append(f"底层数据置信度仅{confidence:.0f}%")
    score = max(0,min(100,round(score)))
    direction = "偏多" if score >= 62 else "偏空" if score <= 38 else "震荡"
    level = "⭐⭐⭐⭐⭐" if score>=80 else "⭐⭐⭐⭐" if score>=70 else "⭐⭐⭐" if score>=60 else "⭐⭐" if score>=45 else "⭐"
    action = "可进入重点观察池，等待触发条件后分批布局" if score>=70 else "有条件机会，等待价格/宏观信号确认" if score>=60 else "观察为主，不主动追涨杀跌" if score>40 else "降低暴露，等待风险改善"
    return {"asset":asset,"score":score,"direction":direction,"level":level,"evidence":evidence[:6],"risks":risks[:6],"triggers":triggers[:6],"opportunity":opportunity[:4],"action":action}

def _price_plan(asset,f):
    source = "黄金期货" if asset=="黄金" else asset
    p = _num(_asset(f,source).get("price"))
    if p is None and asset=="黄金": p=_num(_asset(f,"黄金").get("price"))
    if p is None: return {"current":None,"plan":"当前没有可靠价格，不生成虚构价位。"}
    if asset=="黄金": return {"current":p,"plan":f"回撤观察区模型：{round(p*.985,2)}–{round(p*.97,2)}；突破确认：{round(p*1.01,2)}；保护参考：{round(p*.97,2)}。仅为情景模型。"}
    return {"current":p,"plan":"价格可用；缺少完整技术序列时不虚构支撑/压力位。"}

def analyze_opportunities(finance_result:dict[str,Any]):
    rows=[]
    for a in ASSETS:
        r=_score(a,finance_result); r["price_plan"]=_price_plan(a,finance_result); rows.append(r)
    ranked=sorted(rows,key=lambda x:x["score"],reverse=True)
    return {"version":"V4.0","assets":rows,"top_opportunities":[x for x in ranked if x["score"]>=60][:3],"top_risks":[x for x in ranked if x["score"]<=40][:3],"confidence":finance_result.get("confidence",0),"decision_rule":"≥70重点观察；60-69有条件机会；41-59观察；≤40降低暴露。"}

def render_opportunities(data:dict[str,Any])->None:
    import streamlit as st
    r=data if isinstance(data,dict) and isinstance(data.get("assets"),list) and "top_opportunities" in data else analyze_opportunities(data)
    st.markdown(f"## 🎯 投资机会雷达 {r.get('version','V4.0')}")
    st.caption(f"综合趋势、利率/美元、权威/专业新闻、拥挤度和数据质量；置信度 {r.get('confidence',0)}%。评分不是收益率预测。")
    if r.get("top_opportunities"):
        st.markdown("### 🔥 今日重点机会")
        for x in r["top_opportunities"]:
            st.markdown(f"### {x['level']} {x['asset']}｜{x['direction']}｜{x['score']}/100")
            st.write(f"**操作思路：** {x['action']}")
            pp=x.get("price_plan",{})
            if pp.get("current") is not None: st.write(f"**当前价格：** {pp['current']}")
            st.write(f"**价格/触发计划：** {pp.get('plan','无可靠价格')}")
            if x.get('opportunity'): st.write("**机会逻辑：** "+"；".join(x['opportunity']))
            if x.get('evidence'): st.write("**核心证据：** "+"；".join(x['evidence']))
            if x.get('triggers'): st.write("**关键触发器：** "+"；".join(x['triggers']))
            if x.get('risks'): st.write("**主要风险：** "+"；".join(x['risks']))
            st.divider()
    else: st.info("当前没有达到60分观察阈值的资产机会，系统选择不强行推荐。")
    st.markdown("### 📊 资产机会排名")
    for x in sorted(r.get("assets",[]),key=lambda z:z.get("score",0),reverse=True):
        st.write(f"{x['level']} **{x['asset']}**｜{x['direction']}｜{x['score']}/100｜{x['action']}")
    if r.get("top_risks"):
        st.markdown("### 🚨 风险优先级")
        for x in r["top_risks"]: st.warning(f"{x['asset']}｜{x['score']}/100："+"；".join(x.get('risks',[])))
    st.caption(r.get("decision_rule",""))
