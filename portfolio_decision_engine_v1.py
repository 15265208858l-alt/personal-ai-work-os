# 刘强 · Personal AI Work OS — Portfolio Decision Engine V3.0
from __future__ import annotations
from typing import Any


def _num(v):
    try:
        return float(v) if v not in (None, "") else None
    except Exception:
        return None


def _asset_bucket(score):
    if score is None: return "数据不足"
    if score >= 75: return "强机会"
    if score >= 65: return "条件机会"
    if score >= 50: return "观察"
    return "偏弱"


def _stock_decision(x):
    score=_num(x.get("research_score")) or 0
    data=_num(x.get("data_score"))
    price=str(x.get("price_state") or "价格中性")
    if data is not None and data < 70:
        return {"action":"不参与","position":"0%","trigger":"数据完整度达到70%以上并重新通过基本面验证"}
    if score >= 85 and price in ("进入建仓参考区","中性价值以下"):
        return {"action":"优先研究/分批建仓","position":"A股机会仓的30%-50%","trigger":"基本面无恶化，且价格继续处于安全边际区域"}
    if score >= 85:
        return {"action":"重点跟踪，等待价格","position":"0%-10%观察仓","trigger":"价格进入建仓参考区，且现金流/盈利预期未恶化"}
    if score >= 75:
        return {"action":"观察","position":"0%-20%机会仓","trigger":"估值下降或盈利预期上修，同时数据质量稳定"}
    return {"action":"暂不参与","position":"0%","trigger":"研究评分或数据质量改善后重新评估"}


def build_portfolio_decision(finance: dict[str, Any], opportunity: dict[str, Any], research: dict[str, Any]) -> dict[str, Any]:
    confidence=_num(finance.get("confidence")) or _num(opportunity.get("confidence")) or 0
    assets={x.get("asset"):x for x in opportunity.get("assets",[]) if isinstance(x,dict)}
    shortlist=research.get("shortlist",[]) if isinstance(research,dict) else []

    scores={k:_num(v.get("score")) for k,v in assets.items()}
    strong=[k for k,v in scores.items() if v is not None and v>=75]
    conditional=[k for k,v in scores.items() if v is not None and 65<=v<75]

    # V3.0采用“风险预算”而不是固定预测：数据越不完整，现金缓冲越高。
    cash=50 if confidence<70 else 35 if confidence<85 else 25
    allocation={"现金/低波动":cash,"黄金/贵金属":10,"A股机会仓":5,"美股/权益":15,"美债/利率资产":15,"原油/商品":5}
    reasons=[]; constraints=[]

    def release_cash(key,points,reason):
        nonlocal cash
        if cash>=points:
            allocation["现金/低波动"]-=points; allocation[key]+=points; cash-=points; reasons.append(reason)

    if scores.get("黄金") is not None:
        if scores["黄金"]>=75: release_cash("黄金/贵金属",5,"黄金达到强机会阈值，释放5个百分点风险预算")
        elif scores["黄金"]>=65: reasons.append("黄金为条件机会：只观察/分批，不因单一宏观信号追涨")
    if scores.get("美股") is not None:
        if scores["美股"]>=75: release_cash("美股/权益",5,"美股达到强机会阈值，权益风险预算提高5个百分点")
        elif scores["美股"]>=65: reasons.append("美股为条件机会，等待利率与盈利共振确认")
    if scores.get("美债") is not None and scores["美债"]>=75:
        release_cash("美债/利率资产",5,"美债达到强机会阈值，收益率/政策拐点值得配置")
    if scores.get("原油") is not None and scores["原油"]>=75:
        release_cash("原油/商品",3,"原油风险溢价较强，但商品仓位仍受上限约束")

    stock_actions=[]
    for x in shortlist[:3]:
        if isinstance(x,dict):
            y=dict(x); y["portfolio_decision"]=_stock_decision(y); stock_actions.append(y)
    eligible=[x for x in stock_actions if x["portfolio_decision"]["action"] in ("优先研究/分批建仓","观察")]
    if eligible:
        best=max(eligible,key=lambda x:_num(x.get("research_score")) or 0)
        bs=_num(best.get("research_score")) or 0
        if bs>=85 and confidence>=70:
            release_cash("A股机会仓",5,"存在高质量A股研究候选，且整体数据置信度足够，A股机会仓提高5个百分点")
        elif bs>=75:
            release_cash("A股机会仓",2,"存在合格A股候选，但尚未形成高置信度共振，只释放2个百分点风险预算")
    else:
        constraints.append("暂无同时满足研究质量、数据质量与价格条件的A股候选，保持低机会仓")

    if confidence<70: constraints.append(f"数据置信度{confidence:.0f}%低于70%，进入谨慎模式，现金缓冲提高")
    if len(strong)==0: constraints.append("当前资产层没有强机会信号，不扩大整体风险暴露")
    if len(strong)>=2: reasons.append("至少两个资产方向形成强信号，但仍需检查相关性与估值，避免同一宏观因子重复下注")

    for k in allocation: allocation[k]=max(0,allocation[k])
    total=sum(allocation.values()); allocation={k:round(v/total*100,1) for k,v in allocation.items()}
    allocation["现金/低波动"]=round(100-sum(v for k,v in allocation.items() if k!="现金/低波动"),1)

    ranked=sorted(((v,k) for k,v in scores.items() if v is not None),reverse=True)
    top_asset=ranked[0][1] if ranked else "暂无"; top_score=ranked[0][0] if ranked else None
    if stock_actions:
        top_stock=max(stock_actions,key=lambda x:_num(x.get("research_score")) or 0)
        sd=top_stock["portfolio_decision"]
        next_action=f"个股优先级：{top_stock.get('name','未知')}（{top_stock.get('code','')}）｜{sd['action']}｜建议模型仓位：{sd['position']}"
    elif top_score is not None and top_score>=75:
        next_action=f"资产优先级：{top_asset}（{top_score:.0f}/100）｜按触发条件分批，不追涨"
    elif top_score is not None and top_score>=65:
        next_action=f"资产优先级：{top_asset}（{top_score:.0f}/100）｜条件观察，等待第二证据确认"
    else:
        next_action="当前没有足够强的共振机会｜保持流动性，等待新的触发信号"

    return {
        "version":"V3.0","mode":"谨慎模式" if confidence<70 else "正常模式","confidence":confidence,
        "model_allocation":allocation,"next_action":next_action,"top_asset":top_asset,"top_asset_score":top_score,
        "strong_assets":strong,"conditional_assets":conditional,"reasons":reasons,"constraints":constraints,
        "stock_actions":stock_actions,
        "trigger_matrix":[
            "加仓：方向评分≥75 + 数据置信度≥70% + 价格未明显脱离估值 + 基本面未恶化",
            "观察：评分65-74或价格偏贵，等待第二证据确认",
            "减仓：核心驱动反转 + 价格趋势转弱，或基本面出现连续恶化",
            "退出：核心投资逻辑失效、治理/资产负债表出现重大风险，或数据被证伪",
        ],
        "rules":[
            "单一新闻不触发重仓；至少两个独立变量共振才释放风险预算。",
            "评分不是收益率预测；数据质量不足时自动降低仓位权限。",
            "个股仓位必须服从A股机会仓上限，不允许因主题热度突破组合风险预算。",
            "价格越高、估值越贵，越需要等待；价格便宜也必须先确认基本面没有恶化。",
        ],
        "discipline":"V3.0输出的是模型风险预算与条件式行动框架，不代表对个人账户的确定性买卖指令。"
    }


def render_portfolio_decision(data:dict[str,Any])->None:
    import streamlit as st
    st.divider(); st.markdown("## 💰 投资决策驾驶舱 V3.0"); st.caption(data.get("discipline",""))
    c1,c2,c3=st.columns(3); c1.metric("决策模式",data.get("mode","观察")); c2.metric("数据置信度",f"{data.get('confidence',0):.0f}%"); c3.metric("第一优先级",f"{data.get('top_asset','暂无')} {data.get('top_asset_score','')}")
    st.markdown("### 🎯 今天到底怎么做")
    st.success(data.get("next_action","保持观察"))
    st.markdown("### 📊 模型风险预算")
    cols=st.columns(3)
    for i,(k,v) in enumerate(data.get("model_allocation",{}).items()): cols[i%3].metric(k,f"{v}%")
    if data.get("reasons"):
        st.markdown("### ✅ 为什么这样配置")
        for x in data["reasons"]: st.write("• "+x)
    if data.get("constraints"):
        st.markdown("### 🚧 当前不能做什么")
        for x in data["constraints"]: st.warning(x)
    if data.get("stock_actions"):
        st.markdown("### 📈 A股候选行动卡")
        for x in data["stock_actions"]:
            d=x["portfolio_decision"]
            st.markdown(f"#### ⭐ {x.get('name','未知')}（{x.get('code','')}）｜{x.get('research_score','暂无')}/100")
            st.write(f"**动作：** {d['action']}｜**模型仓位：** {d['position']}｜**触发：** {d['trigger']}")
            st.caption(f"当前价：{x.get('current_price','暂无')}｜建仓参考：{x.get('entry_price','暂无')}｜重仓参考：{x.get('heavy_price','暂无')}｜中性价值：{x.get('valuation','暂无')}")
    st.markdown("### 🧭 决策触发矩阵")
    for i,x in enumerate(data.get("trigger_matrix",[]),1): st.write(f"{i}. {x}")
    st.markdown("### 🧱 投资纪律")
    for i,x in enumerate(data.get("rules",[]),1): st.write(f"{i}. {x}")
