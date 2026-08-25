import streamlit as st
import pandas as pd

from router import route_task
from task_engine import decompose_task, get_task_summary
from executor import execute_tasks, get_execution_summary
from data_provider import normalize_stock_code

st.set_page_config(page_title="Personal AI Work OS", page_icon="🧠", layout="wide")
st.title("🧠 Personal AI Work OS")
st.subheader("个人 AI 工作操作系统 V1.7.2")
st.caption("AI总控台 · 智能任务路由 · 专业Agent调度 · ValueStock AI V17.x共享分析引擎")


def as_dict(value):
    return value if isinstance(value, dict) else {}


def first_dict(*values):
    for value in values:
        if isinstance(value, dict):
            return value
    return {}


def val_get(mapping, *keys, default=None):
    mapping = as_dict(mapping)
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return default


st.markdown("## 🧭 AI工作模块")
modules = [
    ("📁 文件中心", "PDF / Word / Excel / PPT / 报告"),
    ("📈 投资中心", "A股 / 黄金 / 美股 / 价值投资"),
    ("📰 财经情报", "全球市场 / 美联储 / 美债 / 美元"),
    ("🧠 AI学习", "GitHub / Python / Streamlit / Skill / Agent"),
    ("📋 任务中心", "今日任务 / 待办 / 计划"),
    ("🚀 项目中心", "ValueStock AI / AI网店 / AI视频 / AI工具")
]
for i in range(0, len(modules), 3):
    cols = st.columns(3)
    for col, (title, desc) in zip(cols, modules[i:i+3]):
        with col:
            st.info(f"### {title}\n\n{desc}")

st.divider()
st.markdown("## 💬 AI总控台")
user_task = st.text_area(
    "告诉AI你想完成什么",
    placeholder="例如：分析美的集团现在是否值得长期投资",
    height=130,
)

if st.button("🚀 开始执行", type="primary"):
    if not user_task.strip():
        st.warning("请先输入任务。")
        st.stop()

    result = route_task(user_task)
    stock_code = normalize_stock_code(user_task)
    effective_route = dict(result)

    # 只要识别出A股代码，就强制进入 ValueStock Agent，避免名称关键词导致路由漂移。
    if stock_code and result.get("module") == "investment" and result.get("agent") != "gold_agent":
        effective_route["agent"] = "value_stock_agent"
        effective_route["sub_type"] = "股票价值投资分析"

    st.markdown("## 🔎 AI任务解析")
    st.write(f"**任务：** {result['task']}")
    st.write(f"**任务模块：** {effective_route['module_name']}")
    if effective_route.get("agent"):
        st.write(f"**专业Agent：** `{effective_route['agent']}`")
    if stock_code:
        st.write(f"**识别股票：** `{stock_code}`")

    if effective_route["module"] not in ["investment", "project", "learning"]:
        st.info("当前模块仍处于基础路由阶段，后续版本继续接入专业Agent。")
        st.stop()

    st.success(f"已进入：{effective_route['module_name']}")
    if effective_route["module"] == "investment":
        st.write(f"**分析类型：** {effective_route.get('sub_type', '投资分析')}")

    tasks = decompose_task(effective_route["module"])
    if tasks:
        with st.expander("🧩 查看AI任务拆解（后台执行流程）", expanded=False):
            summary = get_task_summary(tasks)
            col1, col2, col3 = st.columns(3)
            col1.metric("总任务", summary["total"])
            col2.metric("已完成", summary["completed"])
            col3.metric("待执行", summary["pending"])
            for task in tasks:
                st.write(f"**{task['id']}**  {task['name']}  — {task['status']}")

    with st.spinner("正在调用 ValueStock AI 专业分析引擎，请稍候……"):
        results = execute_tasks(tasks, user_task, effective_route)

    execution_summary = get_execution_summary(results)
    value_stock_result = next((x.get("value_stock_result") for x in results if x.get("value_stock_result") is not None), None)

    if effective_route.get("agent") == "value_stock_agent":
        st.divider()
        st.markdown("# 📈 最终投资研究结果")

        if value_stock_result is None:
            st.error("❌ ValueStock AI 没有返回结果。")
        elif not value_stock_result.get("success"):
            st.error(value_stock_result.get("error", "ValueStock AI 执行失败"))
        else:
            vr = value_stock_result
            st.success(f"✅ ValueStock AI分析完成：{vr.get('name', '未知')}（{vr.get('code', stock_code)}）")

            dc = as_dict(vr.get("data_center"))
            st.markdown("## 📡 数据中心")
            c1, c2, c3 = st.columns(3)
            c1.metric("数据完整度", f"{val_get(dc, 'score', default='暂无')}%")
            c2.metric("已获取模块", f"{val_get(dc, 'available', default='暂无')}/{val_get(dc, 'total', default='暂无')}")
            c3.metric("数据质量", val_get(dc, "level", default="暂无"))

            score = first_dict(vr.get("investment_score"), vr.get("investment"), vr.get("score"))
            decision = first_dict(vr.get("decision"), vr.get("investment"))
            peer = as_dict(vr.get("peer"))

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("综合投资评分", f"{val_get(score, 'score', default='暂无')}/100")
            c2.metric("投资评级", val_get(score, "rating", default="暂无"))
            c3.metric("风险判断", val_get(score, "risk_level", default="暂无"))
            peer_score = val_get(peer, "score", default=None)
            c4.metric("同行竞争力", "暂无" if peer_score is None else f"{peer_score}/100")

            st.markdown("## 🧠 最终投资决策")
            d1, d2, d3 = st.columns(3)
            d1.metric("投资决策", val_get(decision, "decision", default="暂无"))
            d2.metric("建议操作", val_get(decision, "action", default="暂无"))
            d3.metric("建议仓位", val_get(decision, "position", default="暂无"))
            st.info("💡 决策理由：" + str(val_get(decision, "reason", default="暂无")))
            st.success("🏆 最终结论：" + str(vr.get("conclusion", "暂无")))

            st.markdown("## 📌 当前市场数据")
            market = as_dict(vr.get("market"))
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("股票", f"{market.get('name', vr.get('name'))}（{vr.get('code')}）")
            price = val_get(market, "price", "最新价")
            pct = val_get(market, "change_pct", "涨跌幅")
            dyn_pe = val_get(market, "dynamic_pe", "市盈率-动态")
            c2.metric("当前价格", "暂无" if price is None else f"{float(price):.2f} 元")
            c3.metric("涨跌幅", "暂无" if pct is None else f"{float(pct):.2f}%")
            c4.metric("动态PE", "暂无" if dyn_pe is None else f"{float(dyn_pe):.2f}")

            st.markdown("## 📊 财务分析")
            financial = as_dict(vr.get("financial"))
            latest = as_dict(financial.get("latest"))
            annual = as_dict(financial.get("annual"))
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("最新ROE", "暂无" if latest.get("roe") is None else f"{float(latest['roe']):.2f}%")
            c2.metric("营收增长", "暂无" if latest.get("revenue_growth") is None else f"{float(latest['revenue_growth']):.2f}%")
            c3.metric("净利润增长", "暂无" if latest.get("profit_growth") is None else f"{float(latest['profit_growth']):.2f}%")
            c4.metric("资产负债率", "暂无" if latest.get("debt") is None else f"{float(latest['debt']):.2f}%")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("年度ROE", "暂无" if annual.get("roe") is None else f"{float(annual['roe']):.2f}%")
            c2.metric("年度EPS", "暂无" if annual.get("eps") is None else f"{float(annual['eps']):.2f} 元")
            c3.metric("年度BPS", "暂无" if annual.get("bvps") is None else f"{float(annual['bvps']):.2f} 元")
            c4.metric("年度负债率", "暂无" if annual.get("debt") is None else f"{float(annual['debt']):.2f}%")

            report = as_dict(financial.get("report"))
            with st.expander("💰 查看三大报表关键数据", expanded=False):
                c1, c2, c3, c4, c5 = st.columns(5)
                for col, label, key in [
                    (c1, "营业收入", "revenue"), (c2, "净利润", "net_profit"),
                    (c3, "经营现金流", "ocf"), (c4, "应收账款", "receivable"),
                    (c5, "存货", "inventory")
                ]:
                    value = report.get(key)
                    col.metric(label, "暂无" if value is None else f"{float(value)/1e8:.2f} 亿元")

            quality = as_dict(financial.get("quality"))
            st.markdown("### 📈 5年财务质量")
            c1, c2 = st.columns(2)
            c1.metric("财务质量评分", f"{val_get(quality, 'score', default='暂无')}/100")
            c2.metric("财务质量评级", val_get(quality, "rating", default="暂无"))

            st.markdown("## 🚨 财务排雷")
            risk = as_dict(vr.get("risk"))
            risks = risk.get("risk_items") or risk.get("items") or []
            if risks:
                for item in risks:
                    st.warning(f"⚠️ {item}")
            else:
                st.success("✅ 当前 ValueStock AI 未发现明显财务风险")

            st.markdown("## 💰 估值与买入区间")
            val = as_dict(vr.get("valuation"))
            earn = as_dict(val.get("earnings"))
            scenarios = as_dict(val.get("scenarios"))
            # 兼容 V17.x 不同版本：部分估值字段可能位于 valuation 顶层，也可能位于 scenarios。
            model_raw = val.get("model", {})
            model = as_dict(model_raw)
            hist = as_dict(val.get("historical"))
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("年度EPS", "暂无" if annual.get("eps") is None else f"{float(annual['eps']):.2f}")
            c2.metric("TTM EPS", "暂无" if val_get(earn, "ttm_eps", default=val.get("ttm_eps")) is None else f"{float(val_get(earn, 'ttm_eps', default=val.get('ttm_eps'))):.2f}")
            c3.metric("正常化EPS", "暂无" if val_get(earn, "normalized_eps", default=val.get("normalized_eps")) is None else f"{float(val_get(earn, 'normalized_eps', default=val.get('normalized_eps'))):.2f}")
            valuation_pe = val_get(val, "valuation_pe")
            pb = val_get(val, "pb")
            c4.metric("当前PE（估值口径）", "暂无" if valuation_pe is None else f"{float(valuation_pe):.2f}")
            c5.metric("当前PB", "暂无" if pb is None else f"{float(pb):.2f}")

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("保守价值", "暂无" if scenarios.get("conservative") is None else f"{float(scenarios['conservative']):.2f} 元")
            c2.metric("中性合理价", "暂无" if scenarios.get("normal") is None else f"{float(scenarios['normal']):.2f} 元")
            c3.metric("乐观价值", "暂无" if scenarios.get("optimistic") is None else f"{float(scenarios['optimistic']):.2f} 元")
            c4.metric("建仓参考价", "暂无" if scenarios.get("entry_price") is None else f"{float(scenarios['entry_price']):.2f} 元")
            c5.metric("重仓参考价", "暂无" if scenarios.get("heavy_price") is None else f"{float(scenarios['heavy_price']):.2f} 元")
            model_name = val_get(model, "name", "model", default=val_get(val, "model_name", default="暂无"))
            model_method = val_get(model, "method", default="")
            st.caption(f"估值模型：{model_name}｜{model_method}")
            percentile = val_get(hist, "percentile", default=val_get(val, "historical_percentile", default=None))
            historical_level = val_get(val, "historical_level", default="数据不足")
            st.write(f"**历史PE分位：** {'暂无' if percentile is None else percentile}%　｜　**历史估值区域：** {historical_level}")

            gq = val.get("growth_quality")
            if isinstance(gq, dict):
                st.write(f"成长质量：**{gq.get('score', '暂无')}/100**　等级：**{gq.get('level', '暂无')}**")

            st.markdown("## 🏭 同行业比较")
            st.write(f"行业：**{peer.get('industry') or vr.get('industry') or '暂无'}**　同行评分：**{peer.get('score', '暂无')}/100**")
            if peer.get("codes"):
                st.caption("同行：" + "、".join(peer.get("codes", [])))
            if peer.get("rows"):
                st.dataframe(pd.DataFrame(peer["rows"]).round(2), use_container_width=True, hide_index=True)
            if peer.get("summary"):
                st.dataframe(pd.DataFrame(peer["summary"]), use_container_width=True, hide_index=True)
            if peer.get("compare"):
                st.dataframe(pd.DataFrame(peer["compare"]), use_container_width=True, hide_index=True)
            relative = as_dict(peer.get("result")).get("relative_valuation")
            if isinstance(relative, dict) and relative.get("available"):
                st.info(f"同行PE中位数：{relative.get('peer_median_pe', '暂无')}倍｜同行PB中位数：{relative.get('peer_median_pb', '暂无')}倍｜相对估值：{relative.get('level', '数据不足')}")

            # 数据源诊断：如果仍然出现“暂无”，直接告诉我们究竟是哪一层没有数据。
            diagnostics = vr.get("diagnostics")
            if diagnostics:
                with st.expander("🩺 数据源诊断（出现暂无时优先查看）", expanded=True):
                    st.json(diagnostics)

            with st.expander("🧪 技术诊断 / 完整结构化结果", expanded=False):
                st.write(f"ValueStock AI源码 commit：`{vr.get('source_commit', '暂无')}`")
                st.json(vr)

    else:
        st.markdown("### ⚙️ Agent执行状态")
        col1, col2, col3 = st.columns(3)
        col1.metric("执行任务", execution_summary["total"])
        col2.metric("执行完成", execution_summary["completed"])
        col3.metric("待开发", execution_summary["pending"])
        st.info("该专业Agent目前处于框架阶段，后续版本接入真实数据与分析能力。")

    with st.expander("🔧 查看后台执行明细", expanded=False):
        for r in results:
            icon = "✅" if r["status"] == "执行完成" else "⏳"
            st.write(f"{icon} **{r['task_id']}** {r['task_name']} — {r['message']}")
