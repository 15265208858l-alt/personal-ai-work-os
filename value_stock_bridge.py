# =========================================================
# Personal AI Work OS
# ValueStock AI Bridge V1.7.3
# =========================================================

from __future__ import annotations

import importlib
import sys
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


def _load_value_stock_engine():
    """按 ValueStock AI main 最新 commit 加载完整共享分析引擎。"""
    CACHE_ROOT.mkdir(exist_ok=True)

    ref_url = f"https://api.github.com/repos/{REPO}/git/ref/heads/{BRANCH}"
    ref = requests.get(ref_url, timeout=15)
    ref.raise_for_status()
    commit_sha = ref.json()["object"]["sha"]
    cache_dir = CACHE_ROOT / commit_sha[:12]
    cache_dir.mkdir(exist_ok=True)

    listing_url = f"https://api.github.com/repos/{REPO}/contents/?ref={BRANCH}"
    listing = requests.get(listing_url, timeout=15)
    listing.raise_for_status()

    py_files = [
        item["name"] for item in listing.json()
        if item.get("type") == "file"
        and item.get("name", "").endswith(".py")
        and item.get("name") != "app.py"
    ]

    for filename in py_files:
        target = cache_dir / filename
        if not target.exists():
            raw_url = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{filename}"
            response = requests.get(raw_url, timeout=20)
            response.raise_for_status()
            target.write_text(response.text, encoding="utf-8")

    path = str(cache_dir.resolve())
    if path not in sys.path:
        sys.path.insert(0, path)

    # Streamlit 长生命周期进程：清理旧模块，保证加载的是当前 commit。
    for name in VALUESTOCK_MODULES:
        sys.modules.pop(name, None)

    importlib.invalidate_caches()
    engine = importlib.import_module("analysis_engine")
    return engine, commit_sha


def _get_data_diagnostics(engine=None):
    """从本次实际加载的 ValueStock data 模块读取诊断信息。

    不再盲目读取当前进程中可能同名的 data 模块，避免与 Work OS
    或其他依赖产生模块名冲突。所有输出强制转换成 JSON 可序列化字符串。
    """
    try:
        data_module = None

        # analysis_engine 的 load_stock_data 是本次实际执行所使用的函数。
        if engine is not None:
            load_fn = getattr(engine, "load_stock_data", None)
            module_name = getattr(load_fn, "__module__", None)
            if module_name:
                data_module = sys.modules.get(module_name)

        # 兼容旧调用方式。
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

        return {
            str(key): str(value)
            for key, value in raw.items()
        }
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
    """调用 ValueStock AI 共享分析引擎，并在数据源瞬时失败时自动重试一次。"""
    try:
        engine, commit_sha = _load_value_stock_engine()
        result = engine.analyze_stock(stock_code, peer_input=peer_input, override=override)

        dc = result.get("data_center", {}) if isinstance(result, dict) else {}
        score = dc.get("score", 100) if isinstance(dc, dict) else 100
        if isinstance(result, dict) and score < 75:
            diagnostics_first = _get_data_diagnostics(engine)
            _clear_data_cache(engine)
            result_retry = engine.analyze_stock(stock_code, peer_input=peer_input, override=override)
            if isinstance(result_retry, dict):
                result = result_retry
                result["diagnostics_first_attempt"] = diagnostics_first

        if isinstance(result, dict):
            result["source_commit"] = commit_sha
            result["diagnostics"] = _get_data_diagnostics(engine)
            result["bridge"] = {
                "version": "V1.7.3",
                "data_retry_enabled": True,
                "source_repo": REPO,
                "diagnostics_safe": True,
            }
        return result
    except Exception as exc:
        return {
            "success": False,
            "error": f"ValueStock AI共享引擎调用失败：{type(exc).__name__}: {exc}",
            "diagnostics": {"bridge_error": f"{type(exc).__name__}: {exc}"},
        }
