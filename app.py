import streamlit as st

from router import route_task
from task_engine import decompose_task, get_task_summary
from executor import execute_tasks, get_execution_summary


# =========================================================
# 页面设置
# =========================================================

st.set_page_config(
    page_title="Personal AI Work OS",
    page_icon="🧠",
    layout="wide"
)


# =========================================================
# 标题
# =========================================================

st.title("🧠 Personal AI Work OS")

st.subheader("个人 AI 工作操作系统 V1.3")

st.caption(
    "AI总控台 · 智能任务路由 · 任务拆解 · 任务执行 · 投资分析"
)


# =========================================================
# 六大模块
# =========================================================

st.markdown("## 🧭 AI工作模块")

col1, col2, col3 = st.columns(3)

with col1:
    st.info(
        """
        ### 📁 文件中心

        文件分析  
        PDF / Word / Excel  
        报告总结  
        风险排查
        """
    )

with col2:
    st.success(
        """
        ### 📈 投资中心

        A股  
        黄金  
        美股  
        公司分析  
        价值投资
        """
    )

with col3:
    st.warning(
        """
        ### 📰 财经情报

        全球市场  
        美联储  
        美债  
        美元  
        地缘政治
        """
    )

col1, col2, col3 = st.columns(3)

with col1:
    st.info(
        """
        ### 🧠 AI学习

        GitHub  
        Python  
        Streamlit  
        Skill  
        Agent
        """
    )

with col2:
    st.success(
        """
        ### 📋 任务中心

        今日任务  
        待办  
        计划  
        任务跟踪
        """
    )

with col3:
    st.warning(
        """
        ### 🚀 项目中心

        ValueStock AI  
        AI网店  
        AI视频  
        AI工具
        """
    )


st.divider()


# =========================================================
# AI总控台
# =========================================================

st.markdown("## 💬 AI总控台")

user_task = st.text_area(
    "告诉AI你想完成什么",
    placeholder="例如：分析美的集团现在是否值得长期投资",
    height=130
)


# =========================================================
# 执行
# =========================================================

if st.button("🚀 开始执行", type="primary"):

    if not user_task.strip():
        st.warning("请先输入任务。")

    else:
        result = route_task(user_task)

        st.markdown("## 🔎 AI任务解析")

        st.write(f"**任务：** {result['task']}")
        st.write(f"**任务模块：** {result['module_name']}")

        # =================================================
        # 支持任务拆解和执行的模块
        # =================================================

        if result["module"] in [
            "investment",
            "project",
            "learning"
        ]:

            st.success(
                f"已进入：{result['module_name']}"
            )

            if result["module"] == "investment":
                st.write(
                    f"**分析类型：** {result['sub_type']}"
                )

            # =================================================
            # 任务拆解
            # =================================================

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
                        f"**{task['id']}**  "
                        f"{task['name']}  "
                        f"— {task['status']}"
                    )

                # =================================================
                # 任务执行
                # =================================================

                st.markdown("### ⚙️ AI任务执行")

                results = execute_tasks(
                    tasks,
                    user_task
                )

                execution_summary = get_execution_summary(results)

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric(
                        "执行任务",
                        execution_summary["total"]
                    )

                with col2:
                    st.metric(
                        "执行完成",
                        execution_summary["completed"]
                    )

                with col3:
                    st.metric(
                        "待开发",
                        execution_summary["pending"]
                    )

                st.divider()

                for execution_result in results:

                    if execution_result["status"] == "执行完成":

                        st.success(
                            f"✅ {execution_result['task_id']} "
                            f"{execution_result['task_name']}"
                        )

                        st.caption(
                            execution_result["message"]
                        )

                    else:

                        st.warning(
                            f"⏳ {execution_result['task_id']} "
                            f"{execution_result['task_name']}"
                        )

                        st.caption(
                            execution_result["message"]
                        )

        # =================================================
        # 暂未接入任务执行的模块
        # =================================================

        else:

            st.info(
                "任务已经成功路由。"
            )

            st.write(
                "该模块的具体执行能力将在后续版本接入。"
            )


# =========================================================
# 当前项目
# =========================================================

st.divider()

st.markdown("## 🚀 当前项目")

projects = [
    ("ValueStock AI", "🟢 进行中"),
    ("Personal AI Work OS", "🔵 V1.3"),
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
