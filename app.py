import streamlit as st

from router import route_task
from task_engine import decompose_task, get_task_summary
from executor import execute_tasks, get_execution_summary
from data_provider import normalize_stock_code, format_market_cap

st.set_page_config(page_title="Personal AI Work OS", page_icon="🧠", layout="wide")
st.title("🧠 Personal AI Work OS")
st.subheader("个人 AI 工作操作系统 V1.6.3")
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
user_task = st.text_area(
    "告诉AI你想完成什么",
    placeholder="例如：分析美的集团现在是否值得长期投资",
    height=130,
)

if st.button("🚀 开始执行", type="primary"):
    if not user_task.strip():
        st.warning("请先输入任务。")
    else:
        result = route_task(user_task)

        # 双保险：只要输入中能识别到A股名称/代码，就强制进入 ValueStock AI。
        stock_code = normalize_stock_code(user_task)
        effective_route = dict(result)
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

        if effective_route["module"] in ["investment", "project", "learning"]:
            st.success(f"已进入：{effective_route['module_name']}")
            if effective_route["module"] == "investment":
                st.write(f"**分析类型：** {effective_route.get('sub_type', '投资分析')}")

            tasks = decompose_task(effective_route["module"])
            if tasks:
                # 任务拆解改为折叠区，避免用户最终只看到“执行明细”。
                with st.expander("🧩 查看AI任务拆解（11步价值投资框架）", expanded=False):
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
                market_data = next((x.get("market_data") for x in results if x.get("market_data") is not None), None)
                value_stock_result = next((x.get("value_stock_result") for x in results if x.get("value_stock_result") is not None), None)

                # =====================================================
                # 最终结果优先展示
                # =====================================================
                if effective_route.get("agent") == "value_stock_agent":
                    st.divider()
                    st.markdown("# 📈 最终投资研究结果")

                    if value_stock_result is None:
                        st.error("❌ ValueStock AI 没有返回结果。")
                        st.info("系统已识别股票，但专业引擎没有产生结果。请把本页面截图发给小雅继续排查。")
                    elif not value_stock_result.get("success"):
                        st.error(value_stock_result.get("error", "ValueStock AI 执行失败"))
                    else:
                        vr = value_stock_result
                        st.success(f"✅ 已成功调用 ValueStock AI V17.x：{vr['name']}（{vr['code']}）")

                        # 核心结论区
                        investment = vr.get("investment", {})
                        decision = investment.get("decision") or vr.get("decision") or "暂无"
                        score = investment.get("score", "暂无")
                        valuation_level = investment.get("valuation_level", "暂无")
                        risk_level = investment.get("risk_level", "暂无")

                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("综合投资评分", f"{score}/100")
                        col2.metric("估值状态", str(valuation_level))
                        col3.metric("风险等级", str(risk_level))
                        col4.metric("同行评分", str(vr.get('peer', {}).get('score', '暂无')))

                        st.markdown("## 🧠 AI最终投资判断")
                        st.info(str(decision))

                        # 行情
                        if market_data and market_data.get("success"):
                            st.markdown("### 📊 当前市场数据")
                            col1, col2, col3, col4 = st.columns(4)
                            col1.metric("股票", f"{market_data.get('name', vr['name'])}（{vr['code']}）")
                            price = market_data.get("price")
                            pct = market_data.get("change_pct")
                            col2.metric("最新价", "暂无" if price is None else f"{price:.2f} 元")
                            col3.metric("涨跌幅", "暂无" if pct is None else f"{pct:.2f}%")
                            col4.metric("总市值", format_market_cap(market_data.get("market_cap_yuan")))

                        # 公司质量
                        st.markdown("### 🏢 公司质量")
                        financial = vr.get("financial", {})
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("行业", vr.get("industry") or "暂无")
                        roe = financial.get("roe")
                        col2.metric("最新ROE", "暂无" if roe is None else f"{roe:.2f}%")
                        rg = financial.get("revenue_growth")
                        col3.metric("营收增长", "暂无" if rg is None else f"{rg:.2f}%")
                        pg = financial.get("profit_growth")
                        col4.metric("净利润增长", "暂无" if pg is None else f"{pg:.2f}%")

                        # 估值
                        st.markdown("### 💰 估值与买入区间")
                        val = vr.get("valuation", {})
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

                        # 财务排雷
                        st.markdown("### 🚨 财务排雷")
                        risks = vr.get("risk", {}).get("items", [])
                        if risks:
                            for item in risks:
                                st.warning(f"⚠️ {item}")
                        else:
                            st.success("✅ 当前 ValueStock AI 未发现明显财务风险")

                        # 同行
                        st.markdown("### 🏭 同行比较")
                        peer = vr.get("peer", {})
                        peers = peer.get("peers", [])
                        if peers:
                            st.write(f"同行评分：**{peer.get('score', '暂无')}**　评级：**{peer.get('rating', '暂无')}**")
                            st.write("同行股票：" + "、".join(peers))
                        else:
                            st.info("暂无同行比较数据")

                        # 详细数据放入折叠区
                        with st.expander("📋 查看完整ValueStock AI结构化结果", expanded=False):
                            st.json(vr)

                else:
                    st.markdown("### ⚙️ Agent执行状态")
                    col1, col2, col3 = st.columns(3)
                    col1.metric("执行任务", execution_summary["total"])
                    col2.metric("执行完成", execution_summary["completed"])
                    col3.metric("待开发", execution_summary["pending"])
                    st.info("该专业Agent目前处于框架阶段，下一步接入真实数据与分析能力。")

                # 执行明细默认折叠，不再作为最终结果主界面。
                with st.expander("🔧 查看后台执行明细", expanded=False):
                    for r in results:
                        icon = "✅" if r["status"] == "执行完成" else "⏳"
                        st.write(f"{icon} **{r['task_id']}** {r['task_name']} — {r['message']}")
