# =========================================================
# Personal AI Work OS
# Execution Engine V1.7.0
# =========================================================

from data_provider import normalize_stock_code
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


def execute_tasks(tasks, user_request, route_result=None, **kwargs):
    """根据 Router 的 agent 决定调用哪个专业引擎。

    ValueStock 已经会一次性返回实时行情，因此 Work OS 不再先调用
    data_provider.get_stock_quote() 做重复请求，减少一次外部数据访问。
    """
    if route_result is None:
        route_result = kwargs.get("route_result") or {}

    market_data = None
    value_stock_result = None
    agent = route_result.get("agent")

    if agent == "value_stock_agent":
        try:
            code = normalize_stock_code(user_request)
            if code:
                value_stock_result = run_value_stock_analysis(code)
                # UI 仍保留 market_data 字段兼容旧版本，但直接复用 ValueStock 返回的行情。
                if isinstance(value_stock_result, dict):
                    market_data = value_stock_result.get("market")
            else:
                market_data = {
                    "success": False,
                    "error": "未识别到A股股票名称或6位股票代码。"
                }
                value_stock_result = {
                    "success": False,
                    "error": "未识别到A股股票名称或6位股票代码，未启动 ValueStock AI。"
                }
        except Exception as exc:
            market_data = {
                "success": False,
                "error": f"行情数据获取异常：{type(exc).__name__}"
            }
            value_stock_result = {
                "success": False,
                "error": f"ValueStock AI 调用异常：{type(exc).__name__}"
            }

    results = []
    for task in tasks:
        results.append(execute_task(task, user_request, market_data, value_stock_result))
    return results


def get_execution_summary(results):
    total = len(results)
    completed = len([r for r in results if r["status"] == "执行完成"])
    pending = total - completed
    return {"total": total, "completed": completed, "pending": pending}
