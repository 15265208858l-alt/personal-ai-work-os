# =========================================================
# Personal AI Work OS
# ValueStock AI Bridge V1.8.1
# =========================================================
# 核心目标：
# 1. ValueStock AI 只加载一次，不要每次点击“开始执行”都重新下载/导入。
# 2. 同一个 commit 复用已经加载好的分析引擎。
# 3. 不再因为数据完整度低而自动把整套股票分析再跑一遍。
# 4. 明确下载 ValueStock 的全部运行时依赖，避免出现
#    ModuleNotFoundError: relative_valuation 这类桥接层错误。
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

# analysis_engine -> peer_compare -> relative_valuation 是实际依赖链。
# 这里不再依赖 GitHub 目录枚举结果，直接列出运行时模块，避免某个文件
# 因网络/目录响应异常没有进入缓存目录。
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

VALUESTOCK_MODULES = {
    Path(filename).stem for filename in REQUIRED_FILES
}


def _get_latest_commit() -> str:
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
    CACHE_ROOT.mkdir(exist_ok=True)
    cache_dir = CACHE_ROOT / commit_sha[:12]
    cache_dir.mkdir(exist_ok=True)

    # 关键修复：无论缓存目录是否已存在，都逐个确认运行时依赖存在。
    # 这样旧缓存即使缺少 relative_valuation.py，也会自动补齐。
    for filename in REQUIRED_FILES:
        target = cache_dir / filename
        if not target.exists() or target.stat().st_size == 0:
            _download_file(commit_sha, filename, target)

    path = str(cache_dir.resolve())
    if path not in sys.path:
        sys.path.insert(0, path)

    # 只有第一次加载这个 commit 时清理旧模块；随后由 lru_cache 复用。
    for name in VALUESTOCK_MODULES:
        sys.modules.pop(name, None)

    importlib.invalidate_caches()

    # 先导入直接依赖，遇到缺失会在这里明确暴露，而不是运行到半途才失败。
    importlib.import_module("relative_valuation")
    importlib.import_module("peer_compare")
    engine = importlib.import_module("analysis_engine")
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
    """调用 ValueStock AI；不重复执行完整分析。"""
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
                "version": "V1.8.1",
                "engine_cached": True,
                "full_analysis_retry": False,
                "data_retry_delegated_to_valuestock": True,
                "source_repo": REPO,
                "data_score": score,
                "elapsed_seconds": round(time.time() - started, 2),
                "dependency_fix": "relative_valuation included and cache-verified",
            }
        return result
    except Exception as exc:
        return {
            "success": False,
            "error": f"ValueStock AI共享引擎调用失败：{type(exc).__name__}: {exc}",
            "diagnostics": {"bridge_error": f"{type(exc).__name__}: {exc}"},
            "bridge": {
                "version": "V1.8.1",
                "engine_cached": True,
                "source_repo": REPO,
                "elapsed_seconds": round(time.time() - started, 2),
            },
        }
