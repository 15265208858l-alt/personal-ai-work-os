# =========================================================
# Personal AI Work OS
# Task Engine V1.3
# =========================================================


def build_investment_tasks():
    return [
        {"id": "INV-01", "name": "行业与成长空间", "module": "industry", "status": "待执行"},
        {"id": "INV-02", "name": "企业护城河", "module": "moat", "status": "待执行"},
        {"id": "INV-03", "name": "营收与净利润成长", "module": "growth", "status": "待执行"},
        {"id": "INV-04", "name": "ROE及盈利能力", "module": "profitability", "status": "待执行"},
        {"id": "INV-05", "name": "经营现金流与利润匹配", "module": "cashflow", "status": "待执行"},
        {"id": "INV-06", "name": "资产负债表与偿债能力", "module": "balance_sheet", "status": "待执行"},
        {"id": "INV-07", "name": "应收账款与存货质量", "module": "working_capital", "status": "待执行"},
        {"id": "INV-08", "name": "商誉、资本开支与减值", "module": "impairment", "status": "待执行"},
        {"id": "INV-09", "name": "管理层与股东结构", "module": "management", "status": "待执行"},
        {"id": "INV-10", "name": "估值与买入价格", "module": "valuation", "status": "待执行"},
        {"id": "INV-11", "name": "综合投资判断", "module": "decision", "status": "待执行"},
    ]


def build_gold_tasks():
    return [
        {"id": "GOLD-01", "name": "美元指数", "module": "dollar", "status": "待执行"},
        {"id": "GOLD-02", "name": "美国国债收益率", "module": "treasury", "status": "待执行"},
        {"id": "GOLD-03", "name": "美联储利率环境", "module": "fed", "status": "待执行"},
        {"id": "GOLD-04", "name": "黄金价格与趋势", "module": "gold_price", "status": "待执行"},
        {"id": "GOLD-05", "name": "资金与市场情绪", "module": "capital_flow", "status": "待执行"},
        {"id": "GOLD-06", "name": "技术面", "module": "technical", "status": "待执行"},
        {"id": "GOLD-07", "name": "黄金综合判断", "module": "decision", "status": "待执行"},
    ]


def build_project_tasks():
    return [
        {"id": "PROJ-01", "name": "项目目标", "module": "goal", "status": "待执行"},
        {"id": "PROJ-02", "name": "市场需求", "module": "market", "status": "待执行"},
        {"id": "PROJ-03", "name": "竞品分析", "module": "competitor", "status": "待执行"},
        {"id": "PROJ-04", "name": "产品设计", "module": "product", "status": "待执行"},
        {"id": "PROJ-05", "name": "技术方案", "module": "technology", "status": "待执行"},
        {"id": "PROJ-06", "name": "商业模式", "module": "business", "status": "待执行"},
        {"id": "PROJ-07", "name": "执行计划", "module": "execution", "status": "待执行"},
        {"id": "PROJ-08", "name": "项目复盘", "module": "review", "status": "待执行"},
    ]


def build_learning_tasks():
    return [
        {"id": "LEARN-01", "name": "学习目标", "module": "goal", "status": "待执行"},
        {"id": "LEARN-02", "name": "核心概念", "module": "concept", "status": "待执行"},
        {"id": "LEARN-03", "name": "操作练习", "module": "practice", "status": "待执行"},
        {"id": "LEARN-04", "name": "实际项目", "module": "project", "status": "待执行"},
        {"id": "LEARN-05", "name": "复盘", "module": "review", "status": "待执行"},
    ]


def decompose_task(task_type):
    if task_type == "investment":
        return build_investment_tasks()
    if task_type == "gold":
        return build_gold_tasks()
    if task_type == "project":
        return build_project_tasks()
    if task_type == "learning":
        return build_learning_tasks()
    return []


def get_task_summary(tasks):
    total = len(tasks)
    completed = len([task for task in tasks if task["status"] == "已完成"])
    return {"total": total, "completed": completed, "pending": total - completed}
