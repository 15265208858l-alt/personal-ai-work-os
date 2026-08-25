# =========================================================
# Personal AI Work OS
# ValueStock AI Bridge V1.7.1
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
    """按 ValueStock AI main 最新 commit 加载共享分析引擎。"""
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

    # Streamlit 是长生命周期进程：如果之前已经加载过 ValueStock 模块，
    # 单纯 import/reload 可能继续使用旧 commit。这里强制清理，确保每次使用最新源码。
    for name in VALUESTOCK_MODULES:
        sys.modules.pop(name, None)

    importlib.invalidate_caches()
    engine = importlib.import_module("analysis_engine")
    return engine, commit_sha


def run_value_stock_analysis(stock_code: str, peer_input: str = "", override: str = "自动识别") -> dict[str, Any]:
    """调用 ValueStock AI 共享分析引擎，返回与独立版同口径的完整结果。"""
    try:
        engine, commit_sha = _load_value_stock_engine()
        result = engine.analyze_stock(stock_code, peer_input=peer_input, override=override)
        if isinstance(result, dict):
            result["source_commit"] = commit_sha
        return result
    except Exception as exc:
        return {
            "success": False,
            "error": f"ValueStock AI共享引擎调用失败：{type(exc).__name__}: {exc}",
        }
