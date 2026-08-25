import streamlit as st

from router import route_task
from task_engine import decompose_task, get_task_summary
from executor import execute_tasks, get_execution_summary


st.set_page_config(
    page_title="Personal AI Work OS",
    page_icon="🧠",
    layout="wide"
)


st.title("🧠 Personal AI Work OS")
st.subheader("个人 AI 工作操作系统 V1.4")
st.caption(
    "AI总控台 · 智能任务路由 · 任务拆解 · 真实行情 · 投资执行"
)


st.markdown("## 🧭 AI工作模块")

col1, col2, col3 = st.columns(3)

with col1:
    st.info("### 📁 文件中心\n\nPDF / Word / Excel\n\n报告总结\n\n风险排查")

with col2:
    st.success("### 📈 投资中心\n\nA股\n\n黄金\n\n美股\n\n价值投资")

with col3:
    st.warning("### 📰 财经情报\n\n全球市场\n\n美联储\n\n美债\n\n美元")

col1, col2, col3 = st.columns(3)

with col1:
    st.info("### 🧠 AI学习\n\nGitHub\n\nPython\n\nStreamlit\n\nSkill / Agent")

with col2:
    st.success("### 📋 任务中心\n\n今日任务\n\n待办\n\n计划\n\n任务跟踪")

with col3:
    st.warning("### 🚀 项目中心\n\nValueStock AI\n\nAI网店\n\nAI视频\n\nAI工具")


st.divider()
st.markdown("## 💬 AI总控台")

user_task = st.text_area(
    "告诉AI你想完成什么",
    placeholder="例如：分析美的集团现在是否值得长期投资",
    height=130
)


if st.button("🚀 开始执行", type="primary"):

    if not user_task.strip():
        st.warning("请先输入任务。")

    else:
        result = route_task(user_task)

        st.markdown("## 🔎 AI任务解析")
        st.write(f"**任务：** {result['task']}")
        st.write(f"**任务模块：** {result['module_name']}")

        if result["module"] in ["investment", "project", "learning"]:

            st.success(f"已进入：{result['module_name']}")

            if result["module"] == "investment":
                st.write(f"**分析类型：** {result['sub_type']}")

            tasks = decompose_task(result["module"])

            if tasks:
                st.markdown("### 🧩 AI任务拆解")

                summary = get_task_summary(tasks)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("总任务", summary["total"])
                with col2:
                    st.metric("已完成", summary["completed"])
                with col3:
                    st.metric("待执行", summary["pending"])

                st.divider()

                for task in tasks:
                    st.write(
                        f"**{task['id']}**  {task['name']}  — {task['status']}"
                    )

                st.markdown("### ⚙️ AI任务执行")

                with st.spinner("正在执行任务并尝试获取真实行情……"):
                    results = execute_tasks(tasks, user_task)

                execution_summary = get_execution_summary(results)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("执行任务", execution_summary["total"])
                with col2:
                    st.metric("执行完成", execution_summary["completed"])
                with col3:
                    st.metric("待开发", execution_summary["pending"])

                # =================================================
                # V1.4 真实行情
                # =================================================

                market_data = None
                for item in results:
                    if item.get("market_data") is not None:
                        market_data = item["market_data"]
                        break

                if market_data is not None:
                    st.markdown("### 📊 实时行情数据")

                    if market_data.get("success"):
                        col1, col2, col3, col4 = st.columns(4)

                        with col1:
                            st.metric(
                                "股票",
                                f"{market_data.get('name', '')} ({market_data.get('code', '')})"
                            )

                        with col2:
                            price = market_data.get("price")
                            st.metric(
                                "最新价",
                                f"{price:.2f}" if price is not None else "暂无"
                            )

                        with col3:
                            pct = market_data.get("change_pct")
                            st.metric(
                                "涨跌幅",
                                f"{pct:.2f}%" if pct is not None else "暂无"
                            )

                        with col4:
                            cap = market_data.get("market_cap_yuan")
                            if cap is not None:
                                cap_text = (
                                    f"{cap / 1e12:.2f} 万亿"
                                    if cap >= 1e12
                                    else f"{cap / 1e8:.2f} 亿"
                                )
                            else:
                                cap_text = "暂无"

                            st.metric("总市值", cap_text)

                        st.caption(
                            "V1.4已接入实时行情接口；财务报表、估值和风险指标将在后续版本继续接入。"
                        )

                    else:
                        st.warning(
                            f"实时行情暂未获取成功：{market_data.get('error', '未知错误')}"
                        )

                st.divider()

                for execution_result in results:
                    if execution_result["status"] == "执行完成":
                        st.success(
                            f"✅ {execution_result['task_id']} "
                            f"{execution_result['task_name']}"
                        )
                        st.caption(execution_result["message"])
                    else:
                        st.warning(
                            f"⏳ {execution_result['task_id']} "
                            f"{execution_result['task_name']}"
                        )
                        st.caption(execution_result["message"])

        else:
            st.info("任务已经成功路由。")
            st.write("该模块的具体执行能力将在后续版本接入。")


st.divider()
st.markdown("## 🚀 当前项目")

projects = [
    ("ValueStock AI", "🟢 进行中"),
    ("Personal AI Work OS", "🔵 V1.4"),
    ("AI学习系统", "🔵 进行中"),
    ("AI网店", "🟡 规划中"),
    ("AI视频", "🟡 规划中")
]

for name, status in projects:
    col1, col2 = st.columns([4, 1])
    with col1:
        st.write(name)
    with col2:
        st.write(status)
