import streamlit as st

from router import route_task


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

st.subheader("个人 AI 工作操作系统 V1.1")

st.caption(
    "AI总控台 · 智能任务路由 · 投资分析 · 文件管理 · 项目管理"
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

if st.button(
    "🚀 开始执行",
    type="primary"
):

    if not user_task.strip():

        st.warning("请先输入任务。")

    else:

        result = route_task(user_task)

        st.markdown("## 🔎 AI任务解析")

        st.write(
            f"**任务：** {result['task']}"
        )

        st.write(
            f"**任务模块：** {result['module_name']}"
        )


        # =================================================
        # 投资任务
        # =================================================

        if result["module"] == "investment":

            st.success(
                f"已进入：{result['module_name']}"
            )

            st.write(
                f"**分析类型：** {result['sub_type']}"
            )

            st.markdown(
                "### 📈 长期价值投资10步"
            )

            for i, item in enumerate(
                result["workflow"],
                start=1
            ):

                st.write(
                    f"{i}. {item}"
                )


            st.markdown(
                "### 🚨 财务风险扫描"
            )

            for risk in result["risk_scan"]:

                st.write(
                    f"⚠️ {risk}"
                )


        # =================================================
        # 其他任务
        # =================================================

        else:

            st.info(
                "任务已经成功路由。"
            )

            st.write(
                "下一阶段将为该模块接入真正的工作能力。"
            )


# =========================================================
# 当前项目
# =========================================================

st.divider()

st.markdown("## 🚀 当前项目")

projects = [
    ("ValueStock AI", "🟢 进行中"),
    ("Personal AI Work OS", "🔵 V1.1"),
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
