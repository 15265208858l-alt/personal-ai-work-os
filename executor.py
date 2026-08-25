# =========================================================
# Personal AI Work OS
# Execution Engine V1.3
# =========================================================


# =========================================================
# 1. 执行单个任务
# =========================================================

def execute_task(task, user_request):

    task_name = task["name"]

    result = {
        "task_id": task["id"],
        "task_name": task_name,
        "status": "执行完成",
        "message": ""
    }


    # =====================================================
    # 投资分析任务
    # =====================================================

    if task["id"] == "INV-01":

        result["message"] = (
            "准备分析目标公司的行业空间、行业周期、"
            "竞争格局和长期成长空间。"
        )


    elif task["id"] == "INV-02":

        result["message"] = (
            "准备分析企业护城河，包括品牌、成本、"
            "技术、渠道、规模和客户粘性。"
        )


    elif task["id"] == "INV-03":

        result["message"] = (
            "准备分析过去几年营业收入、"
            "净利润以及增长质量。"
        )


    elif task["id"] == "INV-04":

        result["message"] = (
            "准备分析ROE、毛利率、净利率、"
            "资产周转率和盈利能力。"
        )


    elif task["id"] == "INV-05":

        result["message"] = (
            "重点检查经营现金流与净利润是否匹配，"
            "识别利润含金量风险。"
        )


    elif task["id"] == "INV-06":

        result["message"] = (
            "分析资产负债率、流动比率、"
            "短期债务和长期偿债能力。"
        )


    elif task["id"] == "INV-07":

        result["message"] = (
            "检查应收账款和存货增长速度，"
            "识别经营质量变化。"
        )


    elif task["id"] == "INV-08":

        result["message"] = (
            "检查商誉、资本开支以及潜在资产减值风险。"
        )


    elif task["id"] == "INV-09":

        result["message"] = (
            "分析管理层、主要股东、"
            "关联交易以及公司治理情况。"
        )


    elif task["id"] == "INV-10":

        result["message"] = (
            "准备进行估值分析，并计算合理价值、"
            "建仓区、重仓区和高估区。"
        )


    elif task["id"] == "INV-11":

        result["message"] = (
            "汇总前面所有分析结果，"
            "形成最终投资判断。"
        )


    # =====================================================
    # 项目任务
    # =====================================================

    elif task["id"].startswith("PROJ"):

        result["message"] = (
            f"正在执行项目任务：{task_name}"
        )


    # =====================================================
    # 学习任务
    # =====================================================

    elif task["id"].startswith("LEARN"):

        result["message"] = (
            f"正在执行学习任务：{task_name}"
        )


    else:

        result["status"] = "待开发"

        result["message"] = (
            "该任务的具体执行模块将在后续版本接入。"
        )


    return result


# =========================================================
# 2. 执行整个任务列表
# =========================================================

def execute_tasks(tasks, user_request):

    results = []

    for task in tasks:

        result = execute_task(
            task,
            user_request
        )

        results.append(result)

    return results


# =========================================================
# 3. 统计执行结果
# =========================================================

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
        "pending": pending
    }
