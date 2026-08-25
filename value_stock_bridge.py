# =========================================================
# Personal AI Work OS
# ValueStock AI Bridge V2.1.0
# =========================================================
# 当前策略：
# - 保留 ValueStock 的财务、风险、估值、历史估值、成长质量、综合评分、决策。
# - Work OS 关闭“同行业比较”，因此不再加载 peer_compare / relative_valuation。
# - 继续保留引擎缓存、6路目标数据并行、短时结果缓存。
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
    "investment_score.py",
    "investment_decision.py",
    "industry.py",
    "insurance_valuation.py",
)

VALUESTOCK_MODULES = {Path(filename).stem for filename in REQUIRED_FILES}
_LATEST_COMMIT_VALUE = None
_LATEST_COMMIT_TIME = 0.0
_COMMIT_TTL_SECONDS = 300
_ANALYSIS_CACHE: dict[tuple[str, str, str], dict[str, Any]] = {}
_ANALYSIS_CACHE_TTL = 90


def _get_latest_commit() -> str:
    global _LATEST_COMMIT_VALUE, _LATEST_COMMIT_TIME
    now = time.time()
    if _LATEST_COMMIT_VALUE and now - _LATEST_COMMIT_TIME < _COMMIT_TTL_SECONDS:
        return _LATEST_COMMIT_VALUE
    url = f"https://api.github.com/repos/{REPO}/git/ref/heads/{BRANCH}"
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    _LATEST_COMMIT_VALUE = response.json()["object"]["sha"]
    _LATEST_COMMIT_TIME = now
    return _LATEST_COMMIT_VALUE


def _download_file(commit_sha: str, filename: str, target: Path) -> None:
    raw_url = f"https://raw.githubusercontent.com/{REPO}/{commit_sha}/{filename}"
    last_error = None
    for attempt in range(2):
        try:
            response = requests.get(raw_url, timeout=10)
            response.raise_for_status()
            target.write_text(response.text, encoding="utf-8")
            return
        except Exception as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(0.2)
    raise RuntimeError(f"下载 ValueStock 模块 {filename} 失败：{last_error}")


@lru_cache(maxsize=2)
def _load_value_stock_engine_for_commit(commit_sha: str):
    started = time.time()
    CACHE_ROOT.mkdir(exist_ok=True)
    cache_dir = CACHE_ROOT / commit_sha[:12]
    cache_dir.mkdir(exist_ok=True)

    missing = []
    for filename in REQUIRED_FILES:
        target = cache_dir / filename
        if not target.exists() or target.stat().st_size == 0:
            missing.append((filename, target))

    if missing:
        with ThreadPoolExecutor(max_workers=min(6, len(missing))) as pool:
            futures = [pool.submit(_download_file, commit_sha, filename, target) for filename, target in missing]
            for future in as_completed(futures):
                future.result()

    path = str(cache_dir.resolve())
    if path not in sys.path:
        sys.path.insert(0, path)

    for name in VALUESTOCK_MODULES:
        sys.modules.pop(name, None)

    importlib.invalidate_caches()
    engine = importlib.import_module("analysis_engine")
    data_module = importlib.import_module("data")

    @lru_cache(maxsize=64)
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
        with ThreadPoolExecutor(max_workers=6) as pool:
            future_map = {pool.submit(fn): key for key, fn in jobs.items()}
            for future in as_completed(future_map):
                key = future_map[future]
                try:
                    result[key] = future.result()
                except Exception:
                    result[key] = None
        return result

    engine.load_stock_data = fast_load_stock_data
    engine._workos_bridge_load_time = round(time.time() - started, 2)
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
            return {"diagnostic_reader": "当前 ValueStock data 模块没有 get_data_diagnostics()"}
        raw = getter()
        if not isinstance(raw, dict):
            return {"diagnostic_reader": f"诊断结果类型异常：{type(raw).__name__}"}
        return {str(key): str(value) for key, value in raw.items()}
    except Exception as exc:
        return {"diagnostic_reader": f"{type(exc).__name__}: {exc}"}


def run_value_stock_analysis(stock_code: str, peer_input: str = "", override: str = "自动识别") -> dict[str, Any]:
    started = time.time()
    code = str(stock_code).strip()
    cache_key = (code, str(peer_input or ""), str(override or "自动识别"))

    cached = _ANALYSIS_CACHE.get(cache_key)
    if cached and time.time() - cached["time"] < _ANALYSIS_CACHE_TTL:
        result = dict(cached["result"])
        bridge = dict(result.get("bridge") or {})
        bridge.update({"cache_hit": True, "elapsed_seconds": round(time.time() - started, 2)})
        result["bridge"] = bridge
        return result

    try:
        engine, commit_sha = _load_value_stock_engine()
        analysis_started = time.time()
        result = engine.analyze_stock(code, peer_input=peer_input, override=override)
        analysis_time = round(time.time() - analysis_started, 2)

        if isinstance(result, dict):
            dc = result.get("data_center", {})
            score = dc.get("score", 100) if isinstance(dc, dict) else 100
            result["source_commit"] = commit_sha
            result["diagnostics"] = _get_data_diagnostics(engine)
            result["bridge"] = {
                "version": "V2.1.0",
                "engine_cached": True,
                "cache_hit": False,
                "full_analysis_retry": False,
                "data_retry_delegated_to_valuestock": True,
                "parallel_data_prefetch": True,
                "peer_comparison": False,
                "source_repo": REPO,
                "data_score": score,
                "engine_load_seconds": getattr(engine, "_workos_bridge_load_time", 0.0),
                "analysis_seconds": analysis_time,
                "elapsed_seconds": round(time.time() - started, 2),
                "optimization": "peer comparison removed + target data parallel + cached repeat analysis",
            }
            _ANALYSIS_CACHE[cache_key] = {"time": time.time(), "result": result}
        return result
    except Exception as exc:
        return {
            "success": False,
            "error": f"ValueStock AI共享引擎调用失败：{type(exc).__name__}: {exc}",
            "diagnostics": {"bridge_error": f"{type(exc).__name__}: {exc}"},
            "bridge": {
                "version": "V2.1.0",
                "engine_cached": True,
                "parallel_data_prefetch": True,
                "peer_comparison": False,
                "source_repo": REPO,
                "elapsed_seconds": round(time.time() - started, 2),
            },
        }
