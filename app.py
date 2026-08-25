import streamlit as st

from router import route_task
from task_engine import decompose_task, get_task_summary
from executor import execute_tasks, get_execution_summary

st.set_page_config(page_title="Personal AI Work OS", page_icon="🧠", layout="wide")
st.title("🧠 Personal AI Work OS")
st.subheader("个人 AI 工作操作系统 V1.6")
st.caption("AI总控台 · 智能任务路由 · 专业Agent调度 · ValueStock AI V17.x 投资引擎")

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
user_task = st.text_area("告诉AI你想完成什么", placeholder="例如：分析美的集团现在是否值得长期投资", height=130)

if st.button("🚀 开始执行", type="primary"):
    if not user_task.strip():
        st.warning("请先输入任务。")
    else:
        result = route_task(user_task)
        st.markdown("## 🔎 AI任务解析")
        st.write(f"**任务：** {result['task']}")
        st.write(f"**任务模块：** {result['module_name']}")
        if result.get("agent"):
            st.write(f"**专业Agent：** `{result['agent']}`")

        if result["module"] in ["investment", "project", "learning"]:
            st.success(f"已进入：{result['module_name']}")
            if result["module"] == "investment":
                st.write(f"**分析类型：** {result.get('sub_type', '投资分析')}")

            tasks = decompose_task(result["module"])
            if tasks:
                st.markdown("### 🧩 AI任务拆解")
                summary = get_task_summary(tasks)
                col1, col2, col3 = st.columns(3)
                col1.metric("总任务", summary["total"])
                col2.metric("已完成", summary["completed"])
                col3.metric("待执行", summary["pending"])
                st.divider()
                for task in tasks:
                    st.write(f"**{task['id']}**  {task['name']}  — {task['status']}")

                st.markdown("### ⚙️ AI任务执行")
                with st.spinner("正在调用专业Agent，请稍候……"):
                    # 使用位置参数传递 route_result，避免 Streamlit 热更新时出现
                    # “unexpected keyword argument route_result”的旧模块缓存兼容问题。
                    results = execute_tasks(tasks, user_task, result)

                execution_summary = get_execution_summary(results)
                col1, col2, col3 = st.columns(3)
                col1.metric("执行任务", execution_summary["total"])
                col2.metric("执行完成", execution_summary["completed"])
                col3.metric("待开发", execution_summary["pending"])

                market_data = next((x.get("market_data") for x in results if x.get("market_data") is not None), None)
                value_stock_result = next((x.get("value_stock_result") for x in results if x.get("value_stock_result") is not None), None)

                if result.get("agent") == "value_stock_agent" and value_stock_result is not None:
                    st.divider()
                    st.markdown("# 📈 ValueStock AI V17.x 投资分析结果")
                    if not value_stock_result.get("success"):
                        st.error(value_stock_result.get("error", "ValueStock AI 执行失败"))
                    else:
                        vr = value_stock_result
                        st.success(f"✅ 已成功调用 ValueStock AI：{vr['name']}（{vr['code']}）")
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("综合投资评分", f"{vr['investment'].get('score', '暂无')}/100")
                        col2.metric("财务质量", f"{vr['financial'].get('quality_score', '暂无')}/100")
                        col3.metric("财务风险", f"{vr['risk'].get('score', '暂无')}/10")
                        col4.metric("同行评分", str(vr['peer'].get('score', '暂无')))

                        st.markdown("### 🏢 公司与财务质量")
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("行业", vr.get("industry") or "暂无")
                        roe = vr["financial"].get("roe")
                        col2.metric("最新ROE", "暂无" if roe is None else f"{roe:.2f}%")
                        rg = vr["financial"].get("revenue_growth")
                        col3.metric("营收增长", "暂无" if rg is None else f"{rg:.2f}%")
                        pg = vr["financial"].get("profit_growth")
                        col4.metric("净利润增长", "暂无" if pg is None else f"{pg:.2f}%")

                        st.markdown("### 💰 估值结果")
                        val = vr["valuation"]
                        col1, col2, col3, col4, col5 = st.columns(5)
                        pe = val.get("valuation_pe")
                        pb = val.get("pb")
                        conservative = val.get("conservative")
                        normal = val.get("normal")
                        entry = val.get("entry_price")
                        col1.metric("当前PE", "暂无" if pe is None else f"{pe:.2f}")
                        col2.metric("当前PB", "暂无" if pb is None else f"{pb:.2f}")
                        col3.metric("保守价值", "暂无" if conservative is None else f"{conservative:.2f}")
                        col4.metric("中性合理价", "暂无" if normal is None else f"{normal:.2f}")
                        col5.metric("建仓参考价", "暂无" if entry is None else f"{entry:.2f}")
                        st.write(f"**重仓参考价：** {val.get('heavy_price', '暂无')} 元")
                        st.write(f"**历史估值：** {val.get('historical_level', '数据不足')}｜历史PE分位：{val.get('historical_percentile', '暂无')}")

                        st.markdown("### 🚨 财务排雷")
                        risks = vr["risk"].get("items", [])
                        if risks:
                            for item in risks:
                                st.warning(f"⚠️ {item}")
                        else:
                            st.success("✅ 当前 ValueStock AI 未发现明显财务风险")

                        st.markdown("### 🏭 同行比较")
                        peers = vr["peer"].get("peers", [])
                        if peers:
                            st.dataframe(peers, use_container_width=True, hide_index=True)
                        else:
                            st.info("暂无同行比较数据")

                        st.markdown("### 🧠 最终投资决策")
                        decision = vr["investment"].get("decision") or vr.get("decision") or "暂无"
                        st.info(str(decision))

                st.divider()
                st.markdown("### 📋 执行明细")
                for r in results:
                    icon = "✅" if r["status"] == "执行完成" else "⏳"
                    st.write(f"{icon} **{r['task_id']}** {r['task_name']} — {r['message']}")
