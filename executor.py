# =========================================================
# Personal AI Work OS
# Execution Engine V1.8.1
# =========================================================

from data_provider import normalize_stock_code
from value_stock_bridge import run_value_stock_analysis
from gold_agent import analyze_gold_market, render_gold_result


def execute_task(task, user_request, market_data=None, value_stock_result=None, gold_result=None):
    task_name = task["name"]
    result = {
        "task_id": task["id"],
        "task_name": task_name,
        "status": "执行完成",
        "message": "",
    }
    if market_data is not None:
        result["market_data"] = market_data
    if value_stock_result is not None:
        result["value_stock_result"] = value_stock_result
    if gold_result is not None:
        result["gold_result"] = gold_result

    if task["id"].startswith("INV-"):
        result["message"] = f"已接入 ValueStock AI：{task_name}。"
    elif task["id"].startswith("GOLD-"):
        result["message"] = f"已接入黄金宏观Agent：{task_name}。"
    elif task["id"].startswith("PROJ"):
        result["message"] = f"正在执行项目任务：{task_name}"
    elif task["id"].startswith("LEARN"):
        result["message"] = f"正在执行学习任务：{task_name}"
    else:
        result["status"] = "待开发"
        result["message"] = "该任务的具体执行模块将在后续版本接入。"
    return result


def execute_tasks(tasks, user_request, route_result=None, **kwargs):
    """根据 Router 的 agent 调度专业引擎。"""
    if route_result is None:
        route_result = kwargs.get("route_result") or {}

    market_data = None
    value_stock_result = None
    gold_result = None
    agent = route_result.get("agent")

    if agent == "value_stock_agent":
        try:
            code = normalize_stock_code(user_request)
            if code:
                value_stock_result = run_value_stock_analysis(code)
                if isinstance(value_stock_result, dict):
                    market_data = value_stock_result.get("market")
            else:
                value_stock_result = {"success": False, "error": "未识别到A股股票名称或6位股票代码。"}
        except Exception as exc:
            value_stock_result = {"success": False, "error": f"ValueStock AI 调用异常：{type(exc).__name__}"}

    elif agent == "gold_agent":
        try:
            gold_result = analyze_gold_market()
            # 旧 app.py 对非股票Agent只有通用框架展示；这里直接把黄金Agent
            # 的专业结果渲染到当前 Streamlit 执行流中，保持主界面无需大改。
            render_gold_result(gold_result)
        except Exception as exc:
            gold_result = {"success": False, "error": f"黄金宏观Agent调用异常：{type(exc).__name__}: {exc}"}
            try:
                import streamlit as st
                st.error(gold_result["error"])
            except Exception:
                pass

    results = []
    for task in tasks:
        results.append(execute_task(task, user_request, market_data, value_stock_result, gold_result))
    return results


def get_execution_summary(results):
    total = len(results)
    completed = len([r for r in results if r["status"] == "执行完成"])
    pending = total - completed
    return {"total": total, "completed": completed, "pending": pending}
