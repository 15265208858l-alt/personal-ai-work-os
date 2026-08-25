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
st.subheader("个人 AI 工作操作系统 V1.5")
st.caption("AI总控台 · 智能任务路由 · 任务拆解 · ValueStock AI V17.x 投资引擎")

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
                    st.write(f"**{task['id']}**  {task['name']}  — {task['status']}")

                st.markdown("### ⚙️ AI任务执行")
                with st.spinner("正在调用 ValueStock AI V17.x，请稍候……"):
                    results = execute_tasks(tasks, user_task)

                execution_summary = get_execution_summary(results)
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("执行任务", execution_summary["total"])
                with col2:
                    st.metric("执行完成", execution_summary["completed"])
                with col3:
                    st.metric("待开发", execution_summary["pending"])

                market_data = next((x.get("market_data") for x in results if x.get("market_data") is not None), None)
                value_stock_result = next((x.get("value_stock_result") for x in results if x.get("value_stock_result") is not None), None)

                if market_data is not None and market_data.get("success"):
                    st.markdown("### 📊 实时行情")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("股票", f"{market_data.get('name', '')} ({market_data.get('code', '')})")
                    with col2:
                        price = market_data.get("price")
                        st.metric("最新价", f"{price:.2f}" if price is not None else "暂无")
                    with col3:
                        pct = market_data.get("change_pct")
                        st.metric("涨跌幅", f"{pct:.2f}%" if pct is not None else "暂无")
                    with col4:
                        cap = market_data.get("market_cap_yuan")
                        cap_text = "暂无" if cap is None else (f"{cap / 1e12:.2f} 万亿" if cap >= 1e12 else f"{cap / 1e8:.2f} 亿")
                        st.metric("总市值", cap_text)

                if value_stock_result is not None:
                    st.divider()
                    st.markdown("# 📈 ValueStock AI V17.x 投资分析结果")

                    if not value_stock_result.get("success"):
                        st.error(value_stock_result.get("error", "ValueStock AI 执行失败"))
                    else:
                        vr = value_stock_result
                        st.success(f"✅ 已成功调用 ValueStock AI：{vr['name']}（{vr['code']}）")

                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("综合投资评分", f"{vr['investment'].get('score', '暂无')}/100")
                        with col2:
                            st.metric("财务质量", f"{vr['financial'].get('quality_score', '暂无')}/100")
                        with col3:
                            st.metric("财务风险", f"{vr['risk'].get('score', '暂无')}/10")
                        with col4:
                            st.metric("同行评分", str(vr['peer'].get('score', '暂无')))

                        st.markdown("### 🏢 公司与财务质量")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("行业", vr.get("industry") or "暂无")
                        with col2:
                            value = vr["financial"].get("roe")
                            st.metric("最新ROE", "暂无" if value is None else f"{value:.2f}%")
                        with col3:
                            value = vr["financial"].get("revenue_growth")
                            st.metric("营收增长", "暂无" if value is None else f"{value:.2f}%")
                        with col4:
                            value = vr["financial"].get("profit_growth")
                            st.metric("净利润增长", "暂无" if value is None else f"{value:.2f}%")

                        st.markdown("### 💰 估值结果")
                        val = vr["valuation"]
                        col1, col2, col3, col4, col5 = st.columns(5)
                        with col1:
                            st.metric("当前PE", "暂无" if val.get("valuation_pe") is None else f"{val['valuation_pe']:.2f}")
                        with col2:
                            st.metric("当前PB", "暂无" if val.get("pb") is None else f"{val['pb']:.2f}")
                        with col3:
                            st.metric("保守价值", "暂无" if val.get("conservative") is None else f"{val['conservative']:.2f}")
                        with col4:
                            st.metric("中性合理价", "暂无" if val.get("normal") is None else f"{val['normal']:.2f}")
                        with col5:
                            st.metric("建仓参考价", "暂无" if val.get("entry_price") is None else f"{val['entry_price']:.2f}")

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

                        st.caption("投资分析由你现有的 ValueStock AI V17.x 核心模块执行；Personal AI Work OS 负责任务路由、调用与结果展示。")

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
    ("Personal AI Work OS", "🔵 V1.5"),
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
