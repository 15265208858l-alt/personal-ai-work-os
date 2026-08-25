# =========================================================
# Personal AI Work OS
# AI Task Router V1.1
# =========================================================


# =========================================================
# 1. 六大工作模块
# =========================================================

MODULES = {
    "file": {
        "name": "📁 文件中心",
        "description": "PDF、Word、Excel、PPT、报告、合同等文件处理"
    },

    "investment": {
        "name": "📈 投资中心",
        "description": "A股、黄金、美股、港股、公司和行业投资分析"
    },

    "finance": {
        "name": "📰 财经情报",
        "description": "全球财经、宏观经济、美联储、美债、美元、地缘政治"
    },

    "learning": {
        "name": "🧠 AI学习",
        "description": "ChatGPT、GitHub、Python、Streamlit、API、Skill、Agent"
    },

    "task": {
        "name": "📋 任务中心",
        "description": "每日任务、待办事项、工作计划和任务管理"
    },

    "project": {
        "name": "🚀 项目中心",
        "description": "ValueStock AI、AI网店、AI视频、AI工具等项目"
    }
}


# =========================================================
# 2. 投资分析工作流
# =========================================================

INVESTMENT_WORKFLOW = [
    "行业与成长空间",
    "企业护城河",
    "营收与净利润成长",
    "ROE及盈利能力",
    "经营现金流与利润匹配",
    "资产负债表与偿债能力",
    "应收账款与存货质量",
    "商誉、资本开支及潜在减值",
    "管理层、股东结构、关联交易",
    "估值与买入价格"
]


# =========================================================
# 3. 投资风险扫描
# =========================================================

INVESTMENT_RISKS = [
    "经营现金流与净利润是否匹配",
    "应收账款增长是否过快",
    "存货是否异常增加",
    "资产负债率是否过高",
    "短期偿债压力",
    "商誉减值风险",
    "资本开支压力",
    "利润增长质量",
    "关联交易风险",
    "管理层及治理风险"
]


# =========================================================
# 4. 关键词
# =========================================================

KEYWORDS = {

    "file": [
        "pdf",
        "word",
        "excel",
        "ppt",
        "文件",
        "报告",
        "合同",
        "表格"
    ],

    "investment": [
        "股票",
        "a股",
        "美股",
        "港股",
        "黄金",
        "白银",
        "投资",
        "估值",
        "roe",
        "pe",
        "pb",
        "公司",
        "股票池",
        "建仓",
        "重仓"
    ],

    "finance": [
        "财经",
        "新闻",
        "美联储",
        "美债",
        "美元",
        "原油",
        "宏观",
        "地缘政治",
        "经济",
        "cpi",
        "非农",
        "降息",
        "加息"
    ],

    "learning": [
        "学习",
        "github",
        "python",
        "streamlit",
        "codex",
        "skill",
        "api",
        "agent",
        "ai"
    ],

    "task": [
        "任务",
        "待办",
        "今天",
        "明天",
        "计划",
        "安排",
        "提醒"
    ],

    "project": [
        "项目",
        "valuestock",
        "网店",
        "视频",
        "小程序",
        "工具",
        "商业",
        "创业"
    ]
}


# =========================================================
# 5. 任务分类
# =========================================================

def classify_task(task):

    if not task:
        return "unknown"

    text = task.lower()

    scores = {
        module: 0
        for module in KEYWORDS
    }

    for module, words in KEYWORDS.items():

        for word in words:

            if word in text:
                scores[module] += 1

    best_module = max(
        scores,
        key=scores.get
    )

    if scores[best_module] == 0:
        return "unknown"

    return best_module


# =========================================================
# 6. 投资任务进一步分析
# =========================================================

def analyze_investment_task(task):

    text = task.lower()

    result = {
        "workflow": INVESTMENT_WORKFLOW,
        "risk_scan": INVESTMENT_RISKS,
        "type": "投资分析"
    }

    if "黄金" in text:
        result["sub_type"] = "黄金分析"

    elif any(
        word in text
        for word in ["股票", "a股", "美股", "港股"]
    ):
        result["sub_type"] = "股票分析"

    elif any(
        word in text
        for word in ["公司", "企业"]
    ):
        result["sub_type"] = "公司基本面分析"

    else:
        result["sub_type"] = "综合投资分析"

    return result


# =========================================================
# 7. 总路由
# =========================================================

def route_task(task):

    module = classify_task(task)

    result = {
        "module": module,
        "module_name": MODULES.get(
            module,
            {
                "name": "🧠 AI总控台",
                "description": "无法自动识别的任务"
            }
        )["name"],
        "task": task
    }

    if module == "investment":

        investment_result = analyze_investment_task(task)

        result.update(investment_result)

    return result
