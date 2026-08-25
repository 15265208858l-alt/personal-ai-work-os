# =========================================================
# Personal AI Work OS
# Execution Engine V1.4
# =========================================================

from data_provider import normalize_stock_code, get_stock_quote


def execute_task(task, user_request, market_data=None):

    task_name = task["name"]

    result = {
        "task_id": task["id"],
        "task_name": task_name,
        "status": "执行完成",
        "message": "",
    }

    if market_data is not None:
        result["market_data"] = market_data

    if task["id"] == "INV-01":
        result["message"] = (
            "已进入行业分析任务。V1.4开始接入真实股票行情；"
            "行业基本面数据将在后续版本接入。"
        )

    elif task["id"] == "INV-02":
        result["message"] = (
            "已进入护城河分析任务。将结合公司业务、竞争格局"
            "和历史经营表现继续分析。"
        )

    elif task["id"] == "INV-03":
        result["message"] = (
            "已进入营收与净利润成长任务。财务报表数据接口"
            "将在下一阶段接入。"
        )

    elif task["id"] == "INV-04":
        result["message"] = (
            "已进入ROE及盈利能力任务。真实财务指标将在下一阶段接入。"
        )

    elif task["id"] == "INV-05":
        result["message"] = (
            "已进入经营现金流任务。重点检查现金流与利润匹配度。"
        )

    elif task["id"] == "INV-06":
        result["message"] = "已进入资产负债表与偿债能力任务。"

    elif task["id"] == "INV-07":
        result["message"] = "已进入应收账款与存货质量任务。"

    elif task["id"] == "INV-08":
        result["message"] = "已进入商誉、资本开支与减值风险任务。"

    elif task["id"] == "INV-09":
        result["message"] = "已进入管理层、股东结构及公司治理任务。"

    elif task["id"] == "INV-10":
        result["message"] = (
            "已进入估值任务。合理价格模型将在财务数据接入后启用。"
        )

    elif task["id"] == "INV-11":
        result["message"] = (
            "已进入综合投资判断任务。当前先汇总真实行情与任务状态。"
        )

    elif task["id"].startswith("PROJ"):
        result["message"] = f"正在执行项目任务：{task_name}"

    elif task["id"].startswith("LEARN"):
        result["message"] = f"正在执行学习任务：{task_name}"

    else:
        result["status"] = "待开发"
        result["message"] = "该任务的具体执行模块将在后续版本接入。"

    return result


def execute_tasks(tasks, user_request):

    market_data = None

    if any(task["id"].startswith("INV-") for task in tasks):
        code = normalize_stock_code(user_request)

        if code:
            market_data = get_stock_quote(code)
        else:
            market_data = {
                "success": False,
                "error": "未识别到A股股票名称或6位股票代码。",
            }

    results = []

    for task in tasks:
        results.append(
            execute_task(
                task,
                user_request,
                market_data=market_data,
            )
        )

    return results


def get_execution_summary(results):

    total = len(results)

    completed = len([
        r for r in results
        if r["status"] == "执行完成"
    ])

    pending = total - completed

    return {
        "total": total,
        "completed": completed,
        "pending": pending,
    }
