# =========================================================
# 刘强 · Personal AI Work OS
# AI Task Router V1.7.0
# =========================================================

MODULES = {
    "file": {"name": "📁 文件中心", "description": "PDF、Word、Excel、PPT、报告、合同等文件处理"},
    "investment": {"name": "📈 投资中心", "description": "A股、黄金、美股、港股、公司和行业投资分析"},
    "finance": {"name": "📰 财经情报", "description": "全球财经、宏观经济、美联储、美债、美元、地缘政治"},
    "learning": {"name": "🧠 AI学习", "description": "ChatGPT、GitHub、Python、Streamlit、API、Skill、Agent"},
    "task": {"name": "📋 任务中心", "description": "每日任务、待办事项、工作计划和任务管理"},
    "project": {"name": "🚀 项目中心", "description": "ValueStock AI、AI网店、AI视频、AI工具等项目"}
}
INVESTMENT_WORKFLOW = ["行业与成长空间", "企业护城河", "营收与净利润成长", "ROE及盈利能力", "经营现金流与利润匹配", "资产负债表与偿债能力", "应收账款与存货质量", "商誉、资本开支及潜在减值", "管理层、股东结构、关联交易", "估值与买入价格"]
INVESTMENT_RISKS = ["经营现金流与净利润是否匹配", "应收账款增长是否过快", "存货是否异常增加", "资产负债率是否过高", "短期偿债压力", "商誉减值风险", "资本开支压力", "利润增长质量", "关联交易风险", "管理层及治理风险"]
STOCK_KEYWORDS = ["分析", "值得投资", "值不值得买", "值得买吗", "是否值得", "投资价值", "价值投资", "合理价", "合理价格", "建仓价", "重仓价", "高估价", "低估", "高估", "综合投资评分", "财务质量", "估值", "基本面", "roe", "pe", "pb", "现金流", "应收账款", "存货", "商誉", "偿债"]
STOCK_NAME_HINTS = ["美的集团", "特变电工", "紫金矿业", "牧原股份", "紫光股份", "博敏电子", "沪电股份", "深南电路", "生益科技", "平安银行", "章源钨业", "步步高"]
KEYWORDS = {
    "file": ["pdf", "word", "excel", "ppt", "文件", "报告", "合同", "表格"],
    "investment": ["股票", "a股", "美股", "港股", "黄金", "白银", "投资", "估值", "roe", "pe", "pb", "公司", "股票池", "建仓", "重仓"],
    "finance": ["财经", "新闻", "美联储", "美债", "美元", "原油", "宏观", "地缘政治", "经济", "cpi", "pce", "非农", "降息", "加息", "标普", "纳斯达克", "市场", "全球股市"],
    "learning": ["学习", "github", "python", "streamlit", "codex", "skill", "api", "agent", "ai"],
    "task": ["任务", "待办", "今天", "明天", "计划", "安排", "提醒"],
    "project": ["项目", "valuestock", "网店", "视频", "小程序", "工具", "商业", "创业"]
}

def has_stock_identifier(task):
    if not task: return False
    text = task.lower()
    if any(name.lower() in text for name in STOCK_NAME_HINTS): return True
    if any(x in text for x in ["股票", "a股", "个股", "上市公司"]): return True
    import re
    return bool(re.search(r"(?<!\d)\d{6}(?!\d)", text))

def is_stock_value_investment_task(task):
    if not task: return False
    return has_stock_identifier(task) and any(x.lower() in task.lower() for x in STOCK_KEYWORDS)

def classify_task(task):
    if not task: return "unknown"
    if is_stock_value_investment_task(task): return "investment"
    text = task.lower(); scores = {module: 0 for module in KEYWORDS}
    for module, words in KEYWORDS.items():
        for word in words:
            if word in text: scores[module] += 1
    best_module = max(scores, key=scores.get)
    return best_module if scores[best_module] else "unknown"

def analyze_investment_task(task):
    text = task.lower(); result = {"workflow": INVESTMENT_WORKFLOW, "risk_scan": INVESTMENT_RISKS, "type": "投资分析"}
    if "黄金" in text:
        result["sub_type"] = "黄金分析"; result["agent"] = "gold_agent"
    elif has_stock_identifier(task):
        result["sub_type"] = "股票价值投资分析"; result["agent"] = "value_stock_agent"
    elif any(word in text for word in ["公司", "企业"]):
        result["sub_type"] = "公司基本面分析"; result["agent"] = "value_stock_agent"
    else:
        result["sub_type"] = "综合投资分析"; result["agent"] = "investment_agent"
    return result

def route_task(task):
    module = classify_task(task)
    result = {"module": module, "module_name": MODULES.get(module, {"name": "🧠 AI总控台", "description": "无法自动识别的任务"})["name"], "task": task}
    if module != "investment" and has_stock_identifier(task):
        module = "investment"; result["module"] = module; result["module_name"] = MODULES[module]["name"]
    if module == "investment": result.update(analyze_investment_task(task))
    elif module == "finance":
        result["agent"] = "finance_intelligence_agent"; result["sub_type"] = "全球财经情报与宏观研究"
    return result
