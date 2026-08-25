# =========================================================
# Personal AI Work OS
# ValueStock AI Bridge V1.8.0
# =========================================================
# 核心目标：
# 1. ValueStock AI 只加载一次，不要每次点击“开始执行”都重新下载/导入。
# 2. 同一个 commit 复用已经加载好的分析引擎。
# 3. 不再因为数据完整度低而自动把整套股票分析再跑一遍，避免执行时间翻倍。
# 4. ValueStock 自己的数据模块负责重试；Work OS 只负责调度。
# =========================================================

from __future__ import annotations

import importlib
import sys
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

import requests

REPO = "15265208858l-alt/value-stock-ai"
BRANCH = "main"
CACHE_ROOT = Path(".value_stock_cache")
VALUESTOCK_MODULES = {
    "analysis_engine", "data", "financial", "risk", "valuation",
    "adaptive_valuation", "earnings_basis", "growth_quality",
    "historical_valuation", "peer_compare", "investment_score",
    "investment_decision", "industry"
}
REQUIRED_FILES = tuple(sorted(f"{name}.py" for name in VALUESTOCK_MODULES))


def _get_latest_commit() -> str:
    """只查询一次最新 commit；失败时给出明确错误。"""
    url = f"https://api.github.com/repos/{REPO}/git/ref/heads/{BRANCH}"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()["object"]["sha"]


def _download_file(commit_sha: str, filename: str, target: Path) -> None:
    raw_url = f"https://raw.githubusercontent.com/{REPO}/{commit_sha}/{filename}"
    last_error = None
    for attempt in range(2):
        try:
            response = requests.get(raw_url, timeout=15)
            response.raise_for_status()
            target.write_text(response.text, encoding="utf-8")
            return
        except Exception as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(0.5)
    raise RuntimeError(f"下载 ValueStock 模块 {filename} 失败：{last_error}")


@lru_cache(maxsize=2)
def _load_value_stock_engine_for_commit(commit_sha: str):
    """同一 commit 只下载、导入一次。

    这是本次性能修复的核心：Streamlit 每次点击按钮都会重新执行脚本，
    但 Python 进程仍然存在，因此用 lru_cache 复用已经加载的引擎。
    """
    CACHE_ROOT.mkdir(exist_ok=True)
    cache_dir = CACHE_ROOT / commit_sha[:12]
    cache_dir.mkdir(exist_ok=True)

    for filename in REQUIRED_FILES:
        target = cache_dir / filename
        if not target.exists():
            _download_file(commit_sha, filename, target)

    path = str(cache_dir.resolve())
    if path not in sys.path:
        sys.path.insert(0, path)

    # 只有第一次加载这个 commit 时才清理旧模块。
    # 不要每次按钮点击都 pop，否则会破坏已经加载好的依赖关系。
    for name in VALUESTOCK_MODULES:
        sys.modules.pop(name, None)

    importlib.invalidate_caches()
    engine = importlib.import_module("analysis_engine")
    return engine


def _load_value_stock_engine():
    """获取最新 commit，并复用对应的已加载引擎。"""
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


def _clear_data_cache(engine=None):
    try:
        load_fn = getattr(engine, "load_stock_data", None) if engine is not None else None
        if load_fn is not None and hasattr(load_fn, "cache_clear"):
            load_fn.cache_clear()
            return
        data_module = sys.modules.get("data")
        if data_module and hasattr(data_module, "load_stock_data"):
            data_module.load_stock_data.cache_clear()
    except Exception:
        pass


def run_value_stock_analysis(stock_code: str, peer_input: str = "", override: str = "自动识别") -> dict[str, Any]:
    """调用 ValueStock AI。

    注意：这里不再自动进行第二次完整 analyze_stock。
    ValueStock 的 data.py 已经负责单个数据源重试；如果第一次分析数据不足，
    我们直接返回诊断信息。这样可以把一次点击从“整套分析跑两遍”降为“一遍”。
    """
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
                "version": "V1.8.0",
                "engine_cached": True,
                "full_analysis_retry": False,
                "data_retry_delegated_to_valuestock": True,
                "source_repo": REPO,
                "data_score": score,
                "elapsed_seconds": round(time.time() - started, 2),
            }
        return result
    except Exception as exc:
        return {
            "success": False,
            "error": f"ValueStock AI共享引擎调用失败：{type(exc).__name__}: {exc}",
            "diagnostics": {"bridge_error": f"{type(exc).__name__}: {exc}"},
            "bridge": {
                "version": "V1.8.0",
                "engine_cached": True,
                "source_repo": REPO,
                "elapsed_seconds": round(time.time() - started, 2),
            },
        }
