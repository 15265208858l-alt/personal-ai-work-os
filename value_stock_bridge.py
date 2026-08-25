# =========================================================
# Personal AI Work OS
# ValueStock AI Bridge V1.7
#
# 重要架构：Work OS 不再复制 ValueStock AI 的分析逻辑。
# 直接加载 value-stock-ai/main 的共享 analysis_engine.py。
# 因此独立版 ValueStock AI 与 Work OS 使用同一套计算口径。
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


def _load_value_stock_engine():
    """按 main 最新 commit 下载共享分析引擎，避免复制分析逻辑。"""
    CACHE_ROOT.mkdir(exist_ok=True)

    ref_url = f"https://api.github.com/repos/{REPO}/git/ref/heads/{BRANCH}"
    ref = requests.get(ref_url, timeout=15)
    ref.raise_for_status()
    commit_sha = ref.json()["object"]["sha"]
    cache_dir = CACHE_ROOT / commit_sha[:12]
    cache_dir.mkdir(exist_ok=True)

    # analysis_engine 依赖 ValueStock AI 的全部核心模块，因此同步下载所有 .py 文件。
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

    importlib.invalidate_caches()
    module = importlib.import_module("analysis_engine")
    # 防止 Streamlit 热更新时继续复用旧模块。
    module = importlib.reload(module)
    return module, commit_sha


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
            "error": f"ValueStock AI 共享引擎调用失败：{type(exc).__name__}: {exc}",
        }
