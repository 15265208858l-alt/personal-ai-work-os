import streamlit as st
import pandas as pd

from router import route_task
from task_engine import decompose_task, get_task_summary
from executor import execute_tasks, get_execution_summary
from data_provider import normalize_stock_code

st.set_page_config(page_title="Personal AI Work OS", page_icon="🧠", layout="wide")
st.title("🧠 Personal AI Work OS")
st.subheader("个人 AI 工作操作系统 V1.7")
st.caption("AI总控台 · 智能任务路由 · 专业Agent调度 · ValueStock AI V17.2共享分析引擎")

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

    # 股票代码/名称识别成功后，优先调用专业 ValueStock AI。
    if result.get("module") == "investment" and stock_code and result.get("agent") != "gold_agent":
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

    with st.spinner("正在调用专业Agent，请稍候……"):
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
            st.success(f"✅ ValueStock AI共享引擎分析完成：{vr.get('name', '未知')}（{vr.get('code', stock_code)}）")

            # =====================================================
            # 1. 数据完整度：与独立版 ValueStock AI 保持一致
            # =====================================================
            dc = vr.get("data_center", {})
            st.markdown("## 📡 数据中心")
            c1, c2, c3 = st.columns(3)
            c1.metric("数据完整度", f"{dc.get('score', '暂无')}%")
            c2.metric("已获取模块", f"{dc.get('available', '暂无')}/{dc.get('total', '暂无')}")
            c3.metric("数据质量", dc.get("level", "暂无"))

            # =====================================================
            # 2. 核心决策：直接使用 ValueStock AI 的原始决策对象
            # =====================================================
            score = vr.get("investment_score", {})
            decision = vr.get("decision", {})
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("综合投资评分", f"{score.get('score', '暂无')}/100")
            c2.metric("投资评级", score.get("rating", "暂无"))
            c3.metric("风险判断", score.get("risk_level", "暂无"))
            c4.metric("同行竞争力", f"{vr.get('peer', {}).get('score', '暂无')}/100")

            st.markdown("## 🧠 最终投资决策")
            d1, d2, d3 = st.columns(3)
            d1.metric("投资决策", decision.get("decision", "暂无"))
            d2.metric("建议操作", decision.get("action", "暂无"))
            d3.metric("建议仓位", decision.get("position", "暂无"))
            st.info("💡 决策理由：" + str(decision.get("reason", "暂无")))
            st.success("🏆 最终结论：" + str(vr.get("conclusion", "暂无")))

            # =====================================================
            # 3. 行情：直接采用 ValueStock AI 数据，不再使用第二套行情口径
            # =====================================================
            st.markdown("## 📌 当前市场数据")
            market = vr.get("market", {})
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("股票", f"{market.get('name', vr.get('name'))}（{vr.get('code')}）")
            price = market.get("price")
            pct = market.get("change_pct")
            dyn_pe = market.get("dynamic_pe")
            c2.metric("当前价格", "暂无" if price is None else f"{price:.2f} 元")
            c3.metric("涨跌幅", "暂无" if pct is None else f"{pct:.2f}%")
            c4.metric("动态PE", "暂无" if dyn_pe is None else f"{dyn_pe:.2f}")

            # =====================================================
            # 4. 财务分析：完整沿用 V17.1 结果
            # =====================================================
            st.markdown("## 📊 财务分析")
            financial = vr.get("financial", {})
            latest = financial.get("latest", {})
            annual = financial.get("annual", {})
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("最新ROE", "暂无" if latest.get("roe") is None else f"{latest['roe']:.2f}%")
            c2.metric("营收增长", "暂无" if latest.get("revenue_growth") is None else f"{latest['revenue_growth']:.2f}%")
            c3.metric("净利润增长", "暂无" if latest.get("profit_growth") is None else f"{latest['profit_growth']:.2f}%")
            c4.metric("资产负债率", "暂无" if latest.get("debt") is None else f"{latest['debt']:.2f}%")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("年度ROE", "暂无" if annual.get("roe") is None else f"{annual['roe']:.2f}%")
            c2.metric("年度EPS", "暂无" if annual.get("eps") is None else f"{annual['eps']:.2f} 元")
            c3.metric("年度BPS", "暂无" if annual.get("bvps") is None else f"{annual['bvps']:.2f} 元")
            c4.metric("年度负债率", "暂无" if annual.get("debt") is None else f"{annual['debt']:.2f}%")

            # 三大报表关键项
            report = financial.get("report", {})
            with st.expander("💰 查看三大报表关键数据", expanded=False):
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("营业收入", "暂无" if report.get("revenue") is None else f"{report['revenue']/1e8:.2f} 亿元")
                c2.metric("净利润", "暂无" if report.get("net_profit") is None else f"{report['net_profit']/1e8:.2f} 亿元")
                c3.metric("经营现金流", "暂无" if report.get("ocf") is None else f"{report['ocf']/1e8:.2f} 亿元")
                c4.metric("应收账款", "暂无" if report.get("receivable") is None else f"{report['receivable']/1e8:.2f} 亿元")
                c5.metric("存货", "暂无" if report.get("inventory") is None else f"{report['inventory']/1e8:.2f} 亿元")

            quality = financial.get("quality", {})
            st.markdown("### 📈 5年财务质量")
            c1, c2 = st.columns(2)
            c1.metric("财务质量评分", f"{quality.get('score', '暂无')}/100")
            c2.metric("财务质量评级", quality.get("rating", "暂无"))

            # =====================================================
            # 5. 财务排雷
            # =====================================================
            st.markdown("## 🚨 财务排雷")
            risks = vr.get("risk", {}).get("risk_items", [])
            if risks:
                for item in risks:
                    st.warning(f"⚠️ {item}")
            else:
                st.success("✅ 当前 ValueStock AI 未发现明显财务风险")

            # =====================================================
            # 6. 估值：完整保留正常化EPS、动态PE、历史PE和买入区间
            # =====================================================
            st.markdown("## 💰 估值与买入区间")
            val = vr.get("valuation", {})
            earn = val.get("earnings", {})
            scenarios = val.get("scenarios", {})
            model = val.get("model", {})
            hist = val.get("historical", {})
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("年度EPS", "暂无" if annual.get("eps") is None else f"{annual['eps']:.2f}")
            c2.metric("TTM EPS", "暂无" if earn.get("ttm_eps") is None else f"{earn['ttm_eps']:.2f}")
            c3.metric("正常化EPS", "暂无" if earn.get("normalized_eps") is None else f"{earn['normalized_eps']:.2f}")
            c4.metric("当前PE（估值口径）", "暂无" if val.get("valuation_pe") is None else f"{val['valuation_pe']:.2f}")
            c5.metric("当前PB", "暂无" if val.get("pb") is None else f"{val['pb']:.2f}")

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("保守价值", "暂无" if scenarios.get("conservative") is None else f"{scenarios['conservative']:.2f} 元")
            c2.metric("中性合理价", "暂无" if scenarios.get("normal") is None else f"{scenarios['normal']:.2f} 元")
            c3.metric("乐观价值", "暂无" if scenarios.get("optimistic") is None else f"{scenarios['optimistic']:.2f} 元")
            c4.metric("建仓参考价", "暂无" if scenarios.get("entry_price") is None else f"{scenarios['entry_price']:.2f} 元")
            c5.metric("重仓参考价", "暂无" if scenarios.get("heavy_price") is None else f"{scenarios['heavy_price']:.2f} 元")
            st.caption(f"估值模型：{model.get('name', '暂无')}｜{model.get('method', '')}")
            st.write(f"**历史PE分位：** {hist.get('percentile', '暂无')}%　｜　**历史估值区域：** {val.get('historical_level', '数据不足')}")

            gq = val.get("growth_quality")
            if gq:
                st.write(f"成长质量：**{gq.get('score', '暂无')}/100**　等级：**{gq.get('level', '暂无')}**")

            # =====================================================
            # 7. 同行比较：恢复 V17.1 的表格能力
            # =====================================================
            st.markdown("## 🏭 同行业比较")
            peer = vr.get("peer", {})
            st.write(f"行业：**{peer.get('industry') or '暂无'}**　同行评分：**{peer.get('score', '暂无')}/100**")
            if peer.get("codes"):
                st.caption("同行：" + "、".join(peer.get("codes", [])))
            if peer.get("rows"):
                st.dataframe(pd.DataFrame(peer["rows"]).round(2), use_container_width=True, hide_index=True)
            if peer.get("summary"):
                st.dataframe(pd.DataFrame(peer["summary"]), use_container_width=True, hide_index=True)
            if peer.get("compare"):
                st.dataframe(pd.DataFrame(peer["compare"]), use_container_width=True, hide_index=True)
            if peer.get("result") and peer["result"].get("relative_valuation"):
                rel = peer["result"]["relative_valuation"]
                if rel.get("available"):
                    st.info(f"同行PE中位数：{rel.get('peer_median_pe', '暂无')}倍｜同行PB中位数：{rel.get('peer_median_pb', '暂无')}倍｜相对估值：{rel.get('level', '数据不足')}")

            # =====================================================
            # 8. 完整结构化结果仅供调试，不干扰主界面
            # =====================================================
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
