# 刘强 · Personal AI Work OS — Industry → A-share Stock Engine V1.0
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from value_stock_bridge import run_value_stock_analysis

THEMES = {
    "贵金属/黄金产业链": {
        "triggers": ["gold","黄金","sanction","iran","war","conflict","geopolitical","避险"],
        "reason": "黄金、美元/实际利率与避险需求形成共振时，贵金属企业可能受益；继续核验金价、成本和估值。",
        "stocks": [("紫金矿业","601899"),("山东黄金","600547"),("赤峰黄金","600988")],
    },
    "AI算力/PCB/光通信": {
        "triggers": ["ai","nvidia","data center","datacenter","semiconductor","cloud","算力","光通信","服务器","pcb"],
        "reason": "AI资本开支和数据中心投资可向服务器、PCB、高速互连和光模块传导；最终用ValueStock验证。",
        "stocks": [("沪电股份","002463"),("深南电路","002916"),("中际旭创","300308")],
    },
    "能源/油气": {
        "triggers": ["oil","crude","opec","iran","sanction","war","原油","石油","油价"],
        "reason": "油价若由供给约束和地缘风险驱动，上游油气企业可能受益；需区分风险溢价与真实需求。",
        "stocks": [("中国石油","601857"),("中国石化","600028"),("中海油服","601808")],
    },
    "高股息/防御": {
        "triggers": ["risk-off","recession","defensive","dividend","避险","衰退","risk aversion"],
        "reason": "风险偏好下降、利率方向改善时，高股息和防御资产可能相对占优；高股息不等于低估值。",
        "stocks": [("中国神华","601088"),("长江电力","600900"),("中国移动","600941")],
    },
}

def _text(finance):
    return " ".join(str(x.get("title", "")) for x in finance.get("news", []) if isinstance(x,dict) and x.get("tier") in {"authoritative","professional"}).lower()

def _theme_score(name, theme, finance, opportunity):
    text=_text(finance); score=0; evidence=[]
    score += sum(8 for w in theme["triggers"] if w.lower() in text)
    assets={x.get("asset"):x for x in opportunity.get("assets",[]) if isinstance(x,dict)}
    if name.startswith("贵金属"):
        g=assets.get("黄金",{}); score += max(0,int((float(g.get("score",50))-50)*0.5))
        if g.get("score",0)>=60: evidence.append("黄金已进入条件型机会区")
    elif name.startswith("AI算力"):
        s=assets.get("美股",{}); score += 10 if s.get("score",0)>=60 else 0
        if s.get("score",0)>=60: evidence.append("美股风险资产相对强势")
    elif name.startswith("能源"):
        o=assets.get("原油",{}); score += 12 if o.get("score",0)>=60 else 0
        if o.get("score",0)>=60: evidence.append("原油进入偏强区")
    elif name.startswith("高股息"):
        s=assets.get("美股",{}); b=assets.get("美债",{})
        score += 8 if s.get("score",0)<=45 else 0; score += 6 if b.get("score",0)>=55 else 0
        if s.get("score",0)<=45: evidence.append("风险资产偏弱")
        if b.get("score",0)>=55: evidence.append("防御逻辑增强")
    return min(score,100),evidence

def _extract(v):
    score=v.get("investment_score") or v.get("score") or {}; decision=v.get("decision") or {}; val=v.get("valuation") or {}; sc=val.get("scenarios") if isinstance(val,dict) else {}
    market=v.get("market") if isinstance(v.get("market"),dict) else {}; dc=v.get("data_center") if isinstance(v.get("data_center"),dict) else {}
    return {"success":bool(v.get("success")),"name":v.get("name",""),"code":v.get("code",""),"score":score.get("score") if isinstance(score,dict) else None,"rating":score.get("rating") if isinstance(score,dict) else None,"risk":score.get("risk_level") if isinstance(score,dict) else None,"action":decision.get("action") if isinstance(decision,dict) else None,"current_price":market.get("price"),"entry_price":sc.get("entry_price") if isinstance(sc,dict) else None,"heavy_price":sc.get("heavy_price") if isinstance(sc,dict) else None,"valuation":sc.get("normal") if isinstance(sc,dict) else None,"data_score":dc.get("score")}

def _validate(stocks):
    out=[]
    with ThreadPoolExecutor(max_workers=min(3,len(stocks))) as pool:
        fs={pool.submit(run_value_stock_analysis,code):(name,code) for name,code in stocks[:3]}
        for f in as_completed(fs):
            name,code=fs[f]
            try:
                x=_extract(f.result()); x["name"]=x.get("name") or name; x["code"]=x.get("code") or code; out.append(x)
            except Exception as e: out.append({"success":False,"name":name,"code":code,"error":f"{type(e).__name__}: {e}"})
    return sorted(out,key=lambda x:(x.get("score") is not None,x.get("score") or -1),reverse=True)

def analyze_industry_stock_opportunities(finance:dict[str,Any],opportunity:dict[str,Any])->dict[str,Any]:
    themes=[]
    for name,theme in THEMES.items():
        s,e=_theme_score(name,theme,finance,opportunity)
        if s>=12: themes.append({"theme":name,"score":s,"reason":theme["reason"],"evidence":e,"stocks":theme["stocks"]})
    themes=sorted(themes,key=lambda x:x["score"],reverse=True)[:2]
    candidates=[]
    for t in themes:
        for x in _validate(t["stocks"]):
            x.update({"theme":t["theme"],"theme_score":t["score"],"theme_reason":t["reason"]}); candidates.append(x)
    return {"version":"V1.0","themes":themes,"stock_candidates":candidates[:6],"rule":"先用宏观/资产信号筛行业，再用ValueStock AI验证企业质量与估值；数据不完整时不做强推荐。"}

def render_industry_stock_opportunities(data):
    import streamlit as st
    st.divider(); st.markdown("## 🏭 宏观机会 → 行业 → A股候选 V1.0"); st.caption(data.get("rule",""))
    if not data.get("themes"): st.info("当前没有形成足够强的行业共振，暂不强行筛选A股。") ; return
    st.markdown("### 🔥 当前最值得研究的行业")
    for t in data["themes"]:
        st.markdown(f"#### {t['theme']}｜主题评分 {t['score']}/100"); st.write(f"**为什么关注：** {t['reason']}");
        if t.get("evidence"): st.write("**证据：** "+"；".join(t["evidence"]))
    st.markdown("### 📈 ValueStock AI 验证后的A股候选")
    for x in data.get("stock_candidates",[]):
        if not x.get("success"): st.warning(f"{x.get('name','未知')}（{x.get('code','')}）：验证失败 {x.get('error','')}"); continue
        st.markdown(f"**{x.get('name','未知')}（{x.get('code','')}）**｜{x.get('theme','')}｜企业评分 {x.get('score','暂无')}/100")
        st.write(f"评级：{x.get('rating','暂无')}｜风险：{x.get('risk','暂无')}｜当前价：{x.get('current_price','暂无')}｜建仓参考：{x.get('entry_price','暂无')}｜重仓参考：{x.get('heavy_price','暂无')}｜中性价值：{x.get('valuation','暂无')}")
        st.caption(f"数据完整度：{x.get('data_score','暂无')}%｜主题逻辑：{x.get('theme_reason','')}")
