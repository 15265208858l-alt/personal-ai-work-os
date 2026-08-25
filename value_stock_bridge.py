# =========================================================
# Personal AI Work OS
# ValueStock AI Bridge V1.7.2
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
        # 当前 commit 单独缓存；如果文件存在则不会重复下载。
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


def _get_data_diagnostics():
    try:
        data_module = sys.modules.get("data")
        if data_module and hasattr(data_module, "get_data_diagnostics"):
            return data_module.get_data_diagnostics()
    except Exception as exc:
        return {"diagnostic_reader": f"{type(exc).__name__}: {exc}"}
    return {}


def _clear_data_cache():
    try:
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

        # AkShare/Eastmoney/Sina 在云端偶发空响应。第一次完整性过低时，清理缓存再跑一次。
        dc = result.get("data_center", {}) if isinstance(result, dict) else {}
        score = dc.get("score", 100) if isinstance(dc, dict) else 100
        if isinstance(result, dict) and score < 75:
            diagnostics_first = _get_data_diagnostics()
            _clear_data_cache()
            result_retry = engine.analyze_stock(stock_code, peer_input=peer_input, override=override)
            if isinstance(result_retry, dict):
                result = result_retry
                result["diagnostics_first_attempt"] = diagnostics_first

        if isinstance(result, dict):
            result["source_commit"] = commit_sha
            result["diagnostics"] = _get_data_diagnostics()
            result["bridge"] = {
                "version": "V1.7.2",
                "data_retry_enabled": True,
                "source_repo": REPO,
            }
        return result
    except Exception as exc:
        return {
            "success": False,
            "error": f"ValueStock AI共享引擎调用失败：{type(exc).__name__}: {exc}",
            "diagnostics": _get_data_diagnostics(),
        }
