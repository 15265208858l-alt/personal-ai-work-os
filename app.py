import streamlit as st
from router import route_task
from task_engine import decompose_task, get_task_summary
from executor import execute_tasks, get_execution_summary
from data_provider import normalize_stock_code
from gold_agent import render_gold_result
from finance_intelligence_v2 import render_finance_result_v2
from opportunity_engine_v52 import render_opportunities
from investment_cockpit_v60 import render_cockpit
from industry_stock_engine_v1 import render_industry_stock_opportunities
from investment_research_engine_v1 import render_investment_research

st.set_page_config(page_title="刘强 · Personal AI Work OS", page_icon="🧠", layout="wide")
st.title("🧠 刘强 · Personal AI Work OS")
st.subheader("个人 AI 工作操作系统 V2.6")
st.caption("AI总控台 · 财经情报 · 投资机会 V5.2 · 决策驾驶舱 V6.0 · 行业→A股候选 · 深度研究 V1.0")

def as_dict(value): return value if isinstance(value, dict) else {}
def first_dict(*values):
    for value in values:
        if isinstance(value, dict): return value
    return {}
def val_get(mapping,*keys,default=None):
    mapping=as_dict(mapping)
    for key in keys:
        if key in mapping and mapping[key] is not None: return mapping[key]
    return default

st.markdown("## 🧭 AI工作模块")
modules=[("📁 文件中心","PDF / Word / Excel / PPT / 报告"),("📈 投资中心","A股 / 黄金 / 美股 / 价值投资"),("📰 财经情报","全球市场 / 美联储 / 美债 / 美元"),("🧠 AI学习","GitHub / Python / Streamlit / Skill / Agent"),("📋 任务中心","今日任务 / 待办 / 计划"),("🚀 项目中心","ValueStock AI / AI网店 / AI视频 / AI工具")]
for i in range(0,len(modules),3):
    cols=st.columns(3)
    for col,(title,desc) in zip(cols,modules[i:i+3]):
        with col: st.info(f"### {title}\n\n{desc}")
st.divider(); st.markdown("## 💬 AI总控台")
user_task=st.text_area("告诉AI你想完成什么",placeholder="例如：分析今天全球财经市场，寻找黄金、美股、美债、美元、原油的投资机会",height=130)

if st.button("🚀 开始执行", type="primary"):
    if not user_task.strip(): st.warning("请先输入任务。"); st.stop()
    result=route_task(user_task); stock_code=normalize_stock_code(user_task); effective_route=dict(result)

    # 只有明确识别到股票且原始Agent不是财经/黄金时，才覆盖为ValueStock。
    # 防止财经任务被 normalize_stock_code 的宽松匹配误判成“股票任务”。
    if (
        stock_code
        and result.get("module") == "investment"
        and result.get("agent") not in {"gold_agent", "finance_intelligence_agent"}
    ):
        effective_route["agent"]="value_stock_agent"
        effective_route["sub_type"]="股票价值投资分析"

    st.markdown("## 🔎 AI任务解析"); st.write(f"**任务：** {result['task']}"); st.write(f"**任务模块：** {effective_route['module_name']}")
    if effective_route.get("agent"): st.write(f"**专业Agent：** `{effective_route['agent']}`")
    if stock_code and effective_route.get("agent") != "finance_intelligence_agent": st.write(f"**识别股票：** `{stock_code}`")
    if effective_route["module"] not in ["investment","project","learning"]: st.info("当前模块仍处于基础路由阶段，后续版本继续接入专业Agent。"); st.stop()
    st.success(f"已进入：{effective_route['module_name']}")
    if effective_route["module"]=="investment": st.write(f"**分析类型：** {effective_route.get('sub_type','投资分析')}")
    tasks=decompose_task(effective_route["module"])
    if tasks:
        with st.expander("🧩 查看AI任务拆解（后台执行流程）",expanded=False):
            summary=get_task_summary(tasks); c1,c2,c3=st.columns(3); c1.metric("总任务",summary["total"]); c2.metric("已完成",summary["completed"]); c3.metric("待执行",summary["pending"])
            for task in tasks: st.write(f"**{task['id']}**  {task['name']}  — {task['status']}")
    spinner_text="正在调用 ValueStock AI 专业分析引擎，请稍候……"
    if effective_route.get("agent")=="gold_agent": spinner_text="正在调用黄金综合宏观研究 Agent，请稍候……"
    elif effective_route.get("agent")=="finance_intelligence_agent": spinner_text="正在执行财经情报 → 投资机会 V5.2 → 决策驾驶舱 V6.0 → 行业/A股 → 深度研究，请稍候……"
    with st.spinner(spinner_text): results=execute_tasks(tasks,user_task,effective_route)
    execution_summary=get_execution_summary(results); first_result=results[0] if results else {}
    value_stock_result=next((x.get("value_stock_result") for x in results if x.get("value_stock_result") is not None),None)
    gold_result=next((x.get("gold_result") for x in results if x.get("gold_result") is not None),None)

    if effective_route.get("agent")=="finance_intelligence_agent":
        finance_result=first_result.get("finance_result"); opportunity_result=first_result.get("opportunity_result"); cockpit_result=first_result.get("cockpit_result"); industry_stock_result=first_result.get("industry_stock_result"); research_result=first_result.get("research_result"); finance_error=first_result.get("finance_error")
        if finance_error: st.error(finance_error); st.stop()
        if not isinstance(finance_result,dict): st.error("❌ 财经情报 Agent 没有返回有效的 finance_result。"); st.stop()
        render_finance_result_v2(finance_result)
        if not isinstance(opportunity_result,dict): st.error("❌ 投资机会雷达没有返回有效结果。"); st.stop()
        render_opportunities(opportunity_result)
        if not isinstance(cockpit_result,dict): st.error("❌ 投资决策驾驶舱没有返回有效结果。"); st.stop()
        render_cockpit(cockpit_result)
        if not isinstance(industry_stock_result,dict): st.error("❌ 行业/A股机会引擎没有返回有效结果。"); st.stop()
        render_industry_stock_opportunities(industry_stock_result)
        if not isinstance(research_result,dict): st.error("❌ A股深度研究引擎没有返回有效结果。"); st.stop()
        render_investment_research(research_result)
        with st.expander("🔧 查看财经 Agent 后台执行明细",expanded=False):
            for r in results:
                icon="✅" if r["status"]=="执行完成" else "⏳"; st.write(f"{icon} **{r['task_id']}** {r['task_name']} — {r['message']}")
        st.stop()

    if effective_route.get("agent")=="gold_agent":
        if gold_result is None: st.error("❌ 黄金宏观 Agent 没有返回结果。")
        else: render_gold_result(gold_result)
        st.stop()

    if effective_route.get("agent")=="value_stock_agent":
        st.divider(); st.markdown("# 📈 最终投资研究结果")
        if value_stock_result is None: st.error("❌ ValueStock AI 没有返回结果。"); st.stop()
        if not value_stock_result.get("success"): st.error(value_stock_result.get("error","ValueStock AI 执行失败")); st.stop()
        vr=value_stock_result; st.success(f"✅ ValueStock AI分析完成：{vr.get('name','未知')}（{vr.get('code',stock_code)}）")
        dc=as_dict(vr.get("data_center")); st.markdown("## 📡 数据中心"); c1,c2,c3=st.columns(3); c1.metric("数据完整度",f"{val_get(dc,'score',default='暂无')}%"); c2.metric("已获取模块",f"{val_get(dc,'available',default='暂无')}/{val_get(dc,'total',default='暂无')}"); c3.metric("数据质量",val_get(dc,'level',default='暂无'))
        score=first_dict(vr.get("investment_score"),vr.get("investment"),vr.get("score")); decision=first_dict(vr.get("decision"),vr.get("investment")); c1,c2,c3=st.columns(3); c1.metric("综合投资评分",f"{val_get(score,'score',default='暂无')}/100"); c2.metric("投资评级",val_get(score,'rating',default='暂无')); c3.metric("风险判断",val_get(score,'risk_level',default='暂无'))
        st.markdown("## 🧠 最终投资决策"); d1,d2,d3=st.columns(3); d1.metric("投资决策",val_get(decision,'decision',default='暂无')); d2.metric("建议操作",val_get(decision,'action',default='暂无')); d3.metric("建议仓位",val_get(decision,'position',default='暂无')); st.info("💡 决策理由："+str(val_get(decision,'reason',default='暂无'))); st.success("🏆 最终结论："+str(vr.get('conclusion','暂无')))
        st.stop()

    st.info("任务已完成基础调度。后续继续扩展对应专业Agent。")
