# =========================================================
# 刘强 · Personal AI Work OS
# 投资复盘记忆中心 V1.0
# =========================================================
from datetime import datetime


def _d(value):
    return value if isinstance(value, dict) else {}


def _get(d, *keys, default=None):
    d = _d(d)
    for k in keys:
        if d.get(k) is not None:
            return d[k]
    return default


def build_review_record(finance_result, opportunity_result, cockpit_result,
                        research_result, portfolio_result, action_plan_result,
                        risk_review_result, monitor_result):
    """把一次完整投资研究固化为可复盘的判断快照。
    V1.0只记录判断，不虚构收益结果；结果统一标记为待复盘。
    """
    finance = _d(finance_result)
    opp = _d(opportunity_result)
    cockpit = _d(cockpit_result)
    research = _d(research_result)
    portfolio = _d(portfolio_result)
    action = _d(action_plan_result)
    risk = _d(risk_review_result)
    monitor = _d(monitor_result)

    assets = []
    for key in ("asset_ranking", "ranking", "opportunities"):
        value = opp.get(key)
        if isinstance(value, list):
            assets = value
            break
    asset_snapshot = []
    for item in assets[:10]:
        if isinstance(item, dict):
            asset_snapshot.append({
                "asset": _get(item, "asset", "name", "symbol", default="未知资产"),
                "score": _get(item, "score", "total_score", default=None),
                "direction": _get(item, "direction", "trend", "view", default="观察"),
                "action": _get(item, "action", "recommendation", default="观察"),
            })

    candidates = []
    for key in ("candidates", "stocks", "stock_candidates", "selected_stocks"):
        value = research.get(key)
        if isinstance(value, list):
            candidates = value
            break
    stock_snapshot = []
    for item in candidates[:10]:
        if isinstance(item, dict):
            stock_snapshot.append({
                "name": _get(item, "name", "stock_name", default="未知股票"),
                "code": _get(item, "code", "stock_code", default=""),
                "score": _get(item, "score", "investment_score", default=None),
                "action": _get(item, "action", "decision", default="观察"),
            })

    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "status": "待复盘",
        "macro_view": _get(cockpit, "overall_view", "view", "conclusion", default="暂无"),
        "confidence": _get(finance, "confidence", "data_confidence", default=None),
        "asset_snapshot": asset_snapshot,
        "stock_snapshot": stock_snapshot,
        "portfolio_action": _get(portfolio, "action", "decision", "recommendation", default="观察"),
        "action_plan": _get(action, "core_action", "action", "recommendation", default="观察"),
        "risk_level": _get(risk, "risk_level", "level", default="暂无"),
        "monitor_count": len(monitor.get("triggers", [])) if isinstance(monitor.get("triggers"), list) else 0,
        "review_result": None,
        "review_note": "首次记录，等待后续市场结果进行验证。",
    }


def summarize_records(records):
    records = [r for r in records if isinstance(r, dict)]
    reviewed = [r for r in records if r.get("status") == "已复盘" and r.get("review_result") in {"正确", "部分正确", "错误"}]
    correct = sum(r.get("review_result") == "正确" for r in reviewed)
    partial = sum(r.get("review_result") == "部分正确" for r in reviewed)
    wrong = sum(r.get("review_result") == "错误" for r in reviewed)
    rate = round((correct + 0.5 * partial) / len(reviewed) * 100, 1) if reviewed else None
    pending = len(records) - len(reviewed)
    return {
        "total": len(records),
        "reviewed": len(reviewed),
        "pending": pending,
        "correct": correct,
        "partial": partial,
        "wrong": wrong,
        "accuracy": rate,
    }


def render_memory_center(records):
    import streamlit as st
    summary = summarize_records(records)
    st.divider()
    st.markdown("# 📒 投资复盘记忆中心 V1.0")
    st.caption("记录每次投资判断，等待实际市场结果验证；V1.0 不虚构收益率或胜率。")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("研究记录", summary["total"])
    c2.metric("已复盘", summary["reviewed"])
    c3.metric("待复盘", summary["pending"])
    c4.metric("判断准确率", "暂无" if summary["accuracy"] is None else f"{summary['accuracy']}%")

    if not records:
        st.info("暂无历史投资判断。完成一次财经投资研究后，这里会自动建立第一条记录。")
        return

    st.markdown("### 🧠 最近判断")
    for record in reversed(records[-8:]):
        ts = str(record.get("timestamp", ""))[:16].replace("T", " ")
        with st.expander(f"{ts} · {record.get('status', '待复盘')} · {record.get('macro_view', '暂无')}", expanded=False):
            st.write(f"**组合动作：** {record.get('portfolio_action', '暂无')}")
            st.write(f"**执行计划：** {record.get('action_plan', '暂无')}")
            st.write(f"**风险等级：** {record.get('risk_level', '暂无')}")
            if record.get("asset_snapshot"):
                st.write("**资产判断：**", record["asset_snapshot"])
            if record.get("stock_snapshot"):
                st.write("**A股候选：**", record["stock_snapshot"])
            st.caption(record.get("review_note", "等待复盘。"))

    st.markdown("### 📊 判断质量说明")
    if summary["reviewed"] == 0:
        st.info("目前只有预测快照，还没有足够的已验证样本。系统不会把‘预测次数’冒充成‘胜率’。建议积累至少 10 次有效复盘后再观察准确率。")
    else:
        st.write(f"正确 {summary['correct']} 次 · 部分正确 {summary['partial']} 次 · 错误 {summary['wrong']} 次")
