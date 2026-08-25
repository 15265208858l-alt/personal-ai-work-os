# =========================================================
# 刘强 · Personal AI Work OS
# Execution Engine V2.0.0
# =========================================================

from data_provider import normalize_stock_code
from value_stock_bridge import run_value_stock_analysis
from gold_macro_engine import analyze_gold_market, render_gold_result
from finance_intelligence_agent import analyze_finance_market


def execute_task(task, user_request, market_data=None, value_stock_result=None, gold_result=None, finance_result=None):
    result = {"task_id": task["id"], "task_name": task["name"], "status": "执行完成", "message": ""}
    if market_data is not None: result["market_data"] = market_data
    if value_stock_result is not None: result["value_stock_result"] = value_stock_result
    if gold_result is not None: result["gold_result"] = gold_result
    if finance_result is not None: result["finance_result"] = finance_result
    if task["id"].startswith("INV-"): result["message"] = f"已接入 ValueStock AI：{task['name']}。"
    elif task["id"].startswith("GOLD-"): result["message"] = f"已接入黄金综合宏观Agent：{task['name']}。"
    elif task["id"].startswith("FIN-"): result["message"] = f"已接入全球财经情报Agent：{task['name']}。"
    elif task["id"].startswith("PROJ"): result["message"] = f"正在执行项目任务：{task['name']}"
    elif task["id"].startswith("LEARN"): result["message"] = f"正在执行学习任务：{task['name']}"
    else:
        result["status"] = "待开发"; result["message"] = "该任务的具体执行模块将在后续版本接入。"
    return result


def execute_tasks(tasks, user_request, route_result=None, **kwargs):
    if route_result is None: route_result = kwargs.get("route_result") or {}
    market_data = None; value_stock_result = None; gold_result = None; finance_result = None
    agent = route_result.get("agent")
    if agent == "value_stock_agent":
        try:
            code = normalize_stock_code(user_request)
            value_stock_result = run_value_stock_analysis(code) if code else {"success": False, "error": "未识别到A股股票名称或6位股票代码。"}
            if isinstance(value_stock_result, dict): market_data = value_stock_result.get("market")
        except Exception as exc:
            value_stock_result = {"success": False, "error": f"ValueStock AI 调用异常：{type(exc).__name__}"}
    elif agent == "gold_agent":
        try:
            gold_result = analyze_gold_market()
        except Exception as exc:
            gold_result = {"success": False, "error": f"黄金综合宏观Agent调用异常：{type(exc).__name__}: {exc}"}
    elif agent == "finance_intelligence_agent":
        try:
            finance_result = analyze_finance_market()
        except Exception as exc:
            finance_result = {"success": False, "error": f"财经情报Agent调用异常：{type(exc).__name__}: {exc}"}
    return [execute_task(task, user_request, market_data, value_stock_result, gold_result, finance_result) for task in tasks]


def get_execution_summary(results):
    total = len(results); completed = len([r for r in results if r["status"] == "执行完成"]); pending = total - completed
    return {"total": total, "completed": completed, "pending": pending}
