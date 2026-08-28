# =========================================================
# 刘强 · Personal AI Work OS
# 投资复盘记忆中心 V2.0
# =========================================================
from datetime import datetime


def _d(v): return v if isinstance(v, dict) else {}

def _num(v):
    try: return float(v) if v not in (None, "") else None
    except Exception: return None

def _get(d,*keys,default=None):
    d=_d(d)
    for k in keys:
        if d.get(k) is not None: return d[k]
    return default


def _asset_list(opp):
    for key in ("assets","asset_ranking","ranking","opportunities"):
        v=_d(opp).get(key)
        if isinstance(v,list): return [x for x in v if isinstance(x,dict)]
    return []


def _stock_list(research):
    for key in ("shortlist","candidates","stocks","stock_candidates","selected_stocks"):
        v=_d(research).get(key)
        if isinstance(v,list): return [x for x in v if isinstance(x,dict)]
    return []


def build_review_record(finance_result, opportunity_result, cockpit_result,
                        research_result, portfolio_result, action_plan_result,
                        risk_review_result, monitor_result):
    """建立可验证的投资判断基线，不把模型判断当成实际收益。"""
    finance=_d(finance_result); opp=_d(opportunity_result); cockpit=_d(cockpit_result)
    research=_d(research_result); portfolio=_d(portfolio_result); action=_d(action_plan_result)
    risk=_d(risk_review_result); monitor=_d(monitor_result)

    assets=[]
    for item in _asset_list(opp)[:10]:
        assets.append({
            "asset":_get(item,"asset","name","symbol",default="未知资产"),
            "score":_get(item,"score","total_score",default=None),
            "direction":_get(item,"direction","trend","view",default="观察"),
            "action":_get(item,"action","recommendation",default="观察"),
            "price":_get(item,"price","current_price",default=None),
        })

    stocks=[]
    for item in _stock_list(research)[:10]:
        stocks.append({
            "name":_get(item,"name","stock_name",default="未知股票"),
            "code":_get(item,"code","stock_code",default=""),
            "score":_get(item,"research_score","score","investment_score",default=None),
            "price":_get(item,"current_price","price",default=None),
            "entry":_get(item,"entry_price",default=None),
            "heavy":_get(item,"heavy_price",default=None),
            "action":_get(item,"action","decision",default="观察"),
        })

    return {
        "timestamp":datetime.now().isoformat(timespec="seconds"),
        "status":"待复盘",
        "review_horizon":"3-10个交易日",
        "macro_view":_get(cockpit,"overall_view","view","conclusion",default="暂无"),
        "confidence":_get(finance,"confidence","data_confidence",default=None),
        "asset_snapshot":assets,
        "stock_snapshot":stocks,
        "portfolio_action":_get(portfolio,"action","decision","recommendation",default="观察"),
        "action_plan":_get(action,"core_action","action","recommendation",default="观察"),
        "risk_level":_get(risk,"risk_level","level",default=_get(risk,"mode",default="暂无")),
        "monitor_triggers":len(monitor.get("signals",[])) if isinstance(monitor.get("signals"),list) else 0,
        "review_result":None,
        "review_note":"首次记录。后续复盘重点验证：方向是否正确、触发条件是否有效、仓位建议是否过激、风险提示是否提前。",
    }


def compare_latest(records):
    """比较最近两次研究快照，识别方向变化；不是收益率计算。"""
    if len(records)<2: return []
    old,new=records[-2],records[-1]; changes=[]
    old_assets={x.get("asset"):x for x in old.get("asset_snapshot",[]) if isinstance(x,dict)}
    for item in new.get("asset_snapshot",[]):
        if not isinstance(item,dict): continue
        name=item.get("asset"); prev=old_assets.get(name)
        if not prev: continue
        try: delta=round(float(item.get("score"))-float(prev.get("score")),1)
        except Exception: delta=None
        if delta is not None and abs(delta)>=5:
            changes.append(f"{name}评分变化 {delta:+g} 分：{prev.get('direction','观察')} → {item.get('direction','观察')}")
    return changes


def summarize_records(records):
    records=[r for r in records if isinstance(r,dict)]
    reviewed=[r for r in records if r.get("status")=="已复盘" and r.get("review_result") in {"正确","部分正确","错误"}]
    correct=sum(r.get("review_result")=="正确" for r in reviewed); partial=sum(r.get("review_result")=="部分正确" for r in reviewed); wrong=sum(r.get("review_result")=="错误" for r in reviewed)
    rate=round((correct+0.5*partial)/len(reviewed)*100,1) if reviewed else None
    return {"total":len(records),"reviewed":len(reviewed),"pending":len(records)-len(reviewed),"correct":correct,"partial":partial,"wrong":wrong,"accuracy":rate}


def render_memory_center(records):
    import streamlit as st
    summary=summarize_records(records); changes=compare_latest(records)
    st.divider(); st.markdown("# 📒 投资复盘记忆中心 V2.0")
    st.caption("记录每次判断的基线，并在后续复盘中验证方向、触发条件和仓位纪律；不虚构收益率。")
    c1,c2,c3,c4=st.columns(4)
    c1.metric("研究记录",summary["total"]); c2.metric("待复盘",summary["pending"]); c3.metric("已复盘",summary["reviewed"]); c4.metric("判断质量", "暂无" if summary["accuracy"] is None else f"{summary['accuracy']}%")

    if changes:
        st.markdown("### 🔄 最近一次研究变化")
        for x in changes: st.warning(x)

    if not records:
        st.info("暂无历史投资判断。完成一次财经投资研究后自动建立基线。")
        return

    st.markdown("### 🧠 最近投资判断基线")
    for idx,record in enumerate(reversed(records[-8:])):
        ts=str(record.get("timestamp",""))[:16].replace("T"," ")
        with st.expander(f"{ts} · {record.get('status','待复盘')} · {record.get('macro_view','暂无')}",expanded=False):
            st.write(f"**复盘周期：** {record.get('review_horizon','3-10个交易日')}")
            st.write(f"**组合动作：** {record.get('portfolio_action','暂无')}")
            st.write(f"**执行计划：** {record.get('action_plan','暂无')}")
            st.write(f"**风险等级：** {record.get('risk_level','暂无')}｜**置信度：** {record.get('confidence','暂无')}%")
            if record.get("stock_snapshot"): st.write("**A股候选基线：**",record["stock_snapshot"])
            if record.get("asset_snapshot"): st.write("**资产基线：**",record["asset_snapshot"])
            st.caption(record.get("review_note","等待复盘。"))

    st.markdown("### 🧪 复盘机制")
    st.write("1. **方向验证**：判断黄金/美股/美债/原油等资产方向是否被后续市场验证。")
    st.write("2. **触发验证**：检查建仓、加仓、减仓条件是否真正出现。")
    st.write("3. **仓位验证**：判断模型是否在高不确定性阶段给出过高风险预算。")
    st.write("4. **错误归因**：区分数据错误、逻辑错误、时点错误和突发事件。")
    st.write("5. **模型修正**：连续出现同类错误后，降低对应信号权重，而不是简单提高评分。")

    if summary["reviewed"]==0:
        st.info("目前尚无已验证样本。建议积累至少10次有效复盘后，再评价模型判断质量。")
    else:
        st.write(f"已复盘：正确 {summary['correct']} · 部分正确 {summary['partial']} · 错误 {summary['wrong']}")
