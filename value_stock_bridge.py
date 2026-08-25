# =========================================================
# Personal AI Work OS
# ValueStock AI Bridge V1.9.0
# =========================================================
# 目标：
# 1. ValueStock AI 引擎只加载一次。
# 2. 同一个 commit 复用已经加载好的分析引擎。
# 3. 不因为数据完整度低而重复整套股票分析。
# 4. 运行时依赖完整，避免 ModuleNotFoundError。
# 5. Work OS 调用 ValueStock 时，把互相独立的数据请求并行化，
#    明显缩短首次分析等待时间，同时不修改 ValueStock 独立版核心逻辑。
# =========================================================

from __future__ import annotations

import importlib
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from pathlib import Path
from typing import Any

import requests

REPO = "15265208858l-alt/value-stock-ai"
BRANCH = "main"
CACHE_ROOT = Path(".value_stock_cache")

REQUIRED_FILES = (
    "analysis_engine.py",
    "data.py",
    "financial.py",
    "risk.py",
    "valuation.py",
    "adaptive_valuation.py",
    "earnings_basis.py",
    "growth_quality.py",
    "historical_valuation.py",
    "peer_compare.py",
    "relative_valuation.py",
    "investment_score.py",
    "investment_decision.py",
    "industry.py",
    "insurance_valuation.py",
)

VALUESTOCK_MODULES = {Path(filename).stem for filename in REQUIRED_FILES}

# Streamlit 每次点击都会重新运行脚本，但通常复用同一个 Python 进程。
# 最新 commit 不需要每次点击都访问 GitHub；5 分钟检查一次即可。
_LATEST_COMMIT_VALUE = None
_LATEST_COMMIT_TIME = 0.0
_COMMIT_TTL_SECONDS = 300


def _get_latest_commit() -> str:
    global _LATEST_COMMIT_VALUE, _LATEST_COMMIT_TIME
    now = time.time()
    if _LATEST_COMMIT_VALUE and now - _LATEST_COMMIT_TIME < _COMMIT_TTL_SECONDS:
        return _LATEST_COMMIT_VALUE

    url = f"https://api.github.com/repos/{REPO}/git/ref/heads/{BRANCH}"
    response = requests.get(url, timeout=8)
    response.raise_for_status()
    _LATEST_COMMIT_VALUE = response.json()["object"]["sha"]
    _LATEST_COMMIT_TIME = now
    return _LATEST_COMMIT_VALUE


def _download_file(commit_sha: str, filename: str, target: Path) -> None:
    raw_url = f"https://raw.githubusercontent.com/{REPO}/{commit_sha}/{filename}"
    last_error = None
    for attempt in range(2):
        try:
            response = requests.get(raw_url, timeout=12)
            response.raise_for_status()
            target.write_text(response.text, encoding="utf-8")
            return
        except Exception as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(0.3)
    raise RuntimeError(f"下载 ValueStock 模块 {filename} 失败：{last_error}")


@lru_cache(maxsize=2)
def _load_value_stock_engine_for_commit(commit_sha: str):
    CACHE_ROOT.mkdir(exist_ok=True)
    cache_dir = CACHE_ROOT / commit_sha[:12]
    cache_dir.mkdir(exist_ok=True)

    for filename in REQUIRED_FILES:
        target = cache_dir / filename
        if not target.exists() or target.stat().st_size == 0:
            _download_file(commit_sha, filename, target)

    path = str(cache_dir.resolve())
    if path not in sys.path:
        sys.path.insert(0, path)

    for name in VALUESTOCK_MODULES:
        sys.modules.pop(name, None)

    importlib.invalidate_caches()
    importlib.import_module("relative_valuation")
    importlib.import_module("peer_compare")
    engine = importlib.import_module("analysis_engine")

    # ---------------------------------------------------------
    # Work OS 专用加速层
    # ---------------------------------------------------------
    # ValueStock 独立版保持原样；这里只替换共享引擎在 Work OS 中使用的
    # load_stock_data。市场、历史、财务指标、利润表、资产负债表、现金流量表
    # 彼此独立，因此可以并行请求。每个底层函数仍使用 ValueStock 自己的
    # 重试与备用数据源逻辑。
    data_module = importlib.import_module("data")

    @lru_cache(maxsize=32)
    def fast_load_stock_data(stock_code: str):
        code = data_module.clean_stock_code(stock_code)
        if not code:
            return None

        jobs = {
            "market": lambda: data_module.get_realtime_market(code),
            "history": lambda: data_module.get_history_data(code),
            "indicators": lambda: data_module.get_financial_indicators(code),
            "profit": lambda: data_module.get_financial_report(code, "利润表"),
            "balance": lambda: data_module.get_financial_report(code, "资产负债表"),
            "cashflow": lambda: data_module.get_financial_report(code, "现金流量表"),
        }
        result = {"code": code}
        # 控制并发数，避免 Streamlit Cloud 出口同时发起过多请求。
        with ThreadPoolExecutor(max_workers=4) as pool:
            future_map = {pool.submit(fn): key for key, fn in jobs.items()}
            for future in as_completed(future_map):
                key = future_map[future]
                try:
                    result[key] = future.result()
                except Exception:
                    result[key] = None

        return result

    # analysis_engine._peer_rows 和主分析都通过模块级 load_stock_data。
    engine.load_stock_data = fast_load_stock_data
    peer_module = sys.modules.get("peer_compare")
    if peer_module is not None:
        peer_module.load_stock_data = fast_load_stock_data

    return engine


def _load_value_stock_engine():
    commit_sha = _get_latest_commit()
    engine = _load_value_stock_engine_for_commit(commit_sha)
    return engine, commit_sha


def _get_data_diagnostics(engine=None):
    try:
        data_module = None
        if engine is not None:
            load_fn = getattr(engine, "load_stock_data", None)
            module_name = getattr(load_fn, "__module__", None)
            if module_name:
                data_module = sys.modules.get(module_name)

        if data_module is None:
            data_module = sys.modules.get("data")

        if data_module is None:
            return {"diagnostic_reader": "未找到 ValueStock AI data 模块"}

        getter = getattr(data_module, "get_data_diagnostics", None)
        if not callable(getter):
            return {
                "diagnostic_reader": "当前 ValueStock data 模块没有 get_data_diagnostics()",
                "module": str(getattr(data_module, "__file__", "unknown")),
            }

        raw = getter()
        if not isinstance(raw, dict):
            return {"diagnostic_reader": f"诊断结果类型异常：{type(raw).__name__}"}
        return {str(key): str(value) for key, value in raw.items()}
    except Exception as exc:
        return {"diagnostic_reader": f"{type(exc).__name__}: {exc}"}


def run_value_stock_analysis(stock_code: str, peer_input: str = "", override: str = "自动识别") -> dict[str, Any]:
    """调用 ValueStock AI；Work OS 专用并行数据加载，不重复完整分析。"""
    started = time.time()
    try:
        engine, commit_sha = _load_value_stock_engine()
        result = engine.analyze_stock(stock_code, peer_input=peer_input, override=override)

        if isinstance(result, dict):
            dc = result.get("data_center", {})
            score = dc.get("score", 100) if isinstance(dc, dict) else 100
            result["source_commit"] = commit_sha
            result["diagnostics"] = _get_data_diagnostics(engine)
            result["bridge"] = {
                "version": "V1.9.0",
                "engine_cached": True,
                "full_analysis_retry": False,
                "data_retry_delegated_to_valuestock": True,
                "parallel_data_prefetch": True,
                "source_repo": REPO,
                "data_score": score,
                "elapsed_seconds": round(time.time() - started, 2),
                "optimization": "market/history/financial/report requests run concurrently in Work OS",
            }
        return result
    except Exception as exc:
        return {
            "success": False,
            "error": f"ValueStock AI共享引擎调用失败：{type(exc).__name__}: {exc}",
            "diagnostics": {"bridge_error": f"{type(exc).__name__}: {exc}"},
            "bridge": {
                "version": "V1.9.0",
                "engine_cached": True,
                "parallel_data_prefetch": True,
                "source_repo": REPO,
                "elapsed_seconds": round(time.time() - started, 2),
            },
        }
