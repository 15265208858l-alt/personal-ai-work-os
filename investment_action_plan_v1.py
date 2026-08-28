# 刘强 · Personal AI Work OS — Investment Action Plan V2.0
from __future__ import annotations
from typing import Any


def _num(v):
    try: return float(v) if v not in (None, "") else None
    except Exception: return None


def _stock_card(x:dict[str,Any])->dict[str,Any]:
    score=_num(x.get("research_score")) or 0; current=_num(x.get("current_price")); entry=_num(x.get("entry_price")); heavy=_num(x.get("heavy_price")); value=_num(x.get("valuation"))
    price_state=x.get("price_state","价格数据不足")
    if score<75: action="暂不参与"; trigger="研究评分达到75以上且数据质量稳定"
    elif current is not None and entry is not None and current<=entry: action="可进入小仓位验证"; trigger=f"价格≤建仓参考 {entry:g}，且现金流、盈利预期和治理没有新风险"
    elif score>=85: action="重点跟踪，等待价格"; trigger="价格进入建仓区或估值明显改善，同时基本面保持稳定"
    else: action="观察"; trigger="等待估值改善或第二证据确认"
    return {"name":x.get("name","未知"),"code":x.get("code",""),"research_score":round(score),"current_price":current,"entry_price":entry,"heavy_price":heavy,"valuation":value,"price_state":price_state,"action":action,"trigger":trigger,"add_trigger":["盈利/现金流没有恶化","估值仍有安全边际","行业景气或订单得到第二证据确认"],"reduce_trigger":["核心盈利预期连续下修","经营现金流与利润严重背离","价格明显脱离合理估值且情绪极端"],"exit_trigger":["核心投资逻辑被证伪","重大治理/财务风险","行业基本面发生结构性恶化"],"position_rule":"单只个股原则上不超过A股机会仓的50%"}


def build_action_plan(finance:dict[str,Any],opportunity:dict[str,Any],research:dict[str,Any],portfolio:dict[str,Any])->dict[str,Any]:
    stocks=[_stock_card(x) for x in research.get("shortlist",[])[:3] if isinstance(x,dict)]
    confidence=_num(finance.get("confidence")) or _num(portfolio.get("confidence")) or 0
    assets=opportunity.get("assets",[]) if isinstance(opportunity,dict) else []
    ranked=sorted([( _num(x.get("score")),x.get("asset"),x) for x in assets if isinstance(x,dict) and _num(x.get("score")) is not None],reverse=True)
    top=ranked[0] if ranked else (None,"暂无",{})
    if stocks and stocks[0]["action"] in ("可进入小仓位验证","重点跟踪，等待价格"):
        headline=f"第一执行对象：{stocks[0]['name']}（{stocks[0]['code']}）｜{stocks[0]['action']}。先小仓位验证，不因主题热度一次性打满。"
    elif top[0] is not None and top[0]>=75: headline=f"第一执行对象：{top[1]}｜评分{top[0]:.0f}/100。等待触发条件后分批，不追涨。"
    else: headline="当前没有足够强的执行信号｜保持流动性，等待第二证据。"
    if confidence<70: headline+=f" 数据置信度{confidence:.0f}%，执行权限降级为观察/小仓位验证。"
    return {"version":"V2.0","mode":portfolio.get("mode","谨慎模式"),"confidence":confidence,"headline":headline,"stock_actions":stocks,"asset_priority":top[1],"asset_score":top[0],"market_watch":["美元与美国10Y/实际利率方向","Fed预期与CPI/PCE/就业变化","地缘政治风险是否转化为通胀冲击","A股盈利预期、北向/机构资金与行业景气是否共振"],"execution_rules":["先逻辑、再估值、后价格、最后仓位；缺一不可。","单一新闻不得触发重仓，至少两个独立变量共振。","价格进入建仓区不等于立即重仓，必须复核最新财务质量。","逻辑失效时停止加仓并重新评估，不机械摊平。","数据质量不足时降低执行权限，不用模型分数替代事实。"],"disclaimer":"这是模型化研究与条件式执行框架，不构成针对个人账户的确定性买卖指令。"}


def render_action_plan(data:dict[str,Any])->None:
    import streamlit as st
    st.divider(); st.markdown("## 🧭 最终投资执行计划 V2.0"); st.caption(data.get("disclaimer",""))
    c1,c2,c3=st.columns(3); c1.metric("执行模式",data.get("mode","观察")); c2.metric("数据置信度",f"{data.get('confidence',0):.0f}%"); c3.metric("优先资产",data.get("asset_priority","暂无"))
    st.markdown("### 🎯 今日核心行动"); st.success(data.get("headline","保持观察"))
    if data.get("stock_actions"):
        st.markdown("### 📌 个股执行卡")
        for x in data["stock_actions"]:
            st.markdown(f"#### ⭐ {x['name']}（{x['code']}）｜研究评分 {x['research_score']}/100")
            st.write(f"**当前动作：** {x['action']}｜**价格状态：** {x['price_state']}")
            st.write(f"**当前价：** {x.get('current_price','暂无')}｜**建仓：** {x.get('entry_price','暂无')}｜**重仓：** {x.get('heavy_price','暂无')}｜**中性价值：** {x.get('valuation','暂无')}")
            st.info("**触发条件：** "+x["trigger"])
            st.write("**加仓前必须满足：** "+"；".join(x["add_trigger"]))
            st.warning("**减仓信号：** "+"；".join(x["reduce_trigger"]))
            st.error("**退出/逻辑失效：** "+"；".join(x["exit_trigger"]))
    st.markdown("### 👀 下一步重点监控")
    for x in data.get("market_watch",[]): st.write("• "+x)
    st.markdown("### 🧱 执行纪律")
    for i,x in enumerate(data.get("execution_rules",[]),1): st.write(f"{i}. {x}")
