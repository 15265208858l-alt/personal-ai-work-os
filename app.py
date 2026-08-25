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
                    results = execute_tasks(tasks, user_task, route_result=result)

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
                        st.write(f"**行业：** {vr['peer'].get('industry') or '暂无'}")
                        st.write(f"**自动同行：** {', '.join(vr['peer'].get('peers', [])) or '暂无'}")
                        st.write(f"**同行评级：** {vr['peer'].get('rating') or '数据不足'}")

                        st.markdown("### 🧠 最终投资决策")
                        decision = vr["decision"]
                        st.info(f"**{decision.get('decision', '数据不足')}**")
                        st.write(f"**操作建议：** {decision.get('action', '暂无')}")
                        st.write(f"**参考仓位：** {decision.get('position', '暂无')}")
                        st.write(f"**判断依据：** {decision.get('reason', '暂无')}")
                        st.caption("投资分析由你现有的 ValueStock AI V17.x 核心模块执行；Personal AI Work OS 负责任务路由、专业Agent调度与结果展示。")

                elif result.get("agent") == "gold_agent":
                    st.info("🥇 已识别为黄金分析任务。黄金专业Agent将在下一版本接入实时宏观与市场数据。")
                elif result.get("agent") == "investment_agent":
                    st.info("📊 已识别为综合投资任务，等待对应专业Agent接入。")

                if market_data is not None and not market_data.get("success"):
                    st.warning(f"实时行情暂未获取成功：{market_data.get('error', '未知错误')}")

                st.divider()
                for execution_result in results:
                    if execution_result["status"] == "执行完成":
                        st.success(f"✅ {execution_result['task_id']} {execution_result['task_name']}")
                        st.caption(execution_result["message"])
                    else:
                        st.warning(f"⏳ {execution_result['task_id']} {execution_result['task_name']}")
                        st.caption(execution_result["message"])
        else:
            st.info("任务已经成功路由。")
            st.write("该模块的具体执行能力将在后续版本接入。")

st.divider()
st.markdown("## 🚀 当前项目")
projects = [
    ("ValueStock AI", "🟢 V17.x 核心引擎"),
    ("Personal AI Work OS", "🔵 V1.6"),
    ("AI学习系统", "🔵 进行中"),
    ("AI网店", "🟡 规划中"),
    ("AI视频", "🟡 规划中")
]
for name, status in projects:
    col1, col2 = st.columns([4, 1])
    col1.write(name)
    col2.write(status)
