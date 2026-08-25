# =========================================================
# Personal AI Work OS
# Execution Engine V1.6
# =========================================================

from data_provider import normalize_stock_code, get_stock_quote
from value_stock_bridge import run_value_stock_analysis


def execute_task(task, user_request, market_data=None, value_stock_result=None):
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

    if task["id"].startswith("INV-"):
        result["message"] = f"已接入 ValueStock AI：{task_name}。"
    elif task["id"].startswith("PROJ"):
        result["message"] = f"正在执行项目任务：{task_name}"
    elif task["id"].startswith("LEARN"):
        result["message"] = f"正在执行学习任务：{task_name}"
    else:
        result["status"] = "待开发"
        result["message"] = "该任务的具体执行模块将在后续版本接入。"
    return result


def execute_tasks(tasks, user_request, route_result=None):
    """根据 Router 的 agent 决定调用哪个专业引擎。"""
    market_data = None
    value_stock_result = None
    agent = (route_result or {}).get("agent")

    # 只有明确路由到 ValueStock AI 时才启动股票价值投资引擎。
    if agent == "value_stock_agent":
        code = normalize_stock_code(user_request)
        if code:
            market_data = get_stock_quote(code)
            value_stock_result = run_value_stock_analysis(code)
        else:
            market_data = {"success": False, "error": "未识别到A股股票名称或6位股票代码。"}
            value_stock_result = {"success": False, "error": "未识别到A股股票名称或6位股票代码，未启动 ValueStock AI。"}

    results = []
    for task in tasks:
        results.append(execute_task(task, user_request, market_data, value_stock_result))
    return results


def get_execution_summary(results):
    total = len(results)
    completed = len([r for r in results if r["status"] == "执行完成"])
    pending = total - completed
    return {"total": total, "completed": completed, "pending": pending}
