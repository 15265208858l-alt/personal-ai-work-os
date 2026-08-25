# =========================================================
# Personal AI Work OS
# ValueStock AI Bridge V2.1.1
# =========================================================
# 修复：数据源诊断必须读取本次实际加载的 ValueStock data 模块，
# 不再依赖 sys.modules['data']，避免与其他 data 模块重名冲突。
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
BRIDGE_VERSION = "V2.1.1"
CACHE_ROOT = Path(".value_stock_cache")

REQUIRED_FILES = (
    "analysis_engine.py", "data.py", "financial.py", "risk.py", "valuation.py",
    "adaptive_valuation.py", "earnings_basis.py", "growth_quality.py",
    "historical_valuation.py", "investment_score.py", "investment_decision.py",
    "industry.py", "insurance_valuation.py", "peer_compare.py", "relative_valuation.py",
)
VALUESTOCK_MODULES = {Path(filename).stem for filename in REQUIRED_FILES}


def _download_file(filename: str, target: Path) -> None:
    raw_url = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{filename}"
    last_error = None
    for attempt in range(3):
        try:
            response = requests.get(raw_url, timeout=15)
            response.raise_for_status()
            target.write_text(response.text, encoding="utf-8")
            return
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"下载 ValueStock 模块 {filename} 失败：{last_error}")


@lru_cache(maxsize=1)
def _load_value_stock_engine():
    started = time.time()
    cache_dir = CACHE_ROOT / f"{BRIDGE_VERSION}_main"
    cache_dir.mkdir(parents=True, exist_ok=True)

    missing = []
    for filename in REQUIRED_FILES:
        target = cache_dir / filename
        if not target.exists() or target.stat().st_size == 0:
            missing.append((filename, target))

    if missing:
        with ThreadPoolExecutor(max_workers=min(8, len(missing))) as pool:
            futures = [pool.submit(_download_file, filename, target) for filename, target in missing]
            for future in as_completed(futures):
                future.result()

    path = str(cache_dir.resolve())
    sys.path = [p for p in sys.path if p != path]
    sys.path.insert(0, path)

    for name in VALUESTOCK_MODULES:
        sys.modules.pop(name, None)
    importlib.invalidate_caches()

    importlib.import_module("peer_compare")
    importlib.import_module("relative_valuation")
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
    # 保存本次真正加载的 data 模块对象，诊断时直接使用，避免 sys.modules 名称冲突。
    engine._workos_data_module = data_module
    engine._workos_engine_file = str(getattr(engine, "__file__", ""))
    engine._workos_bridge_load_time = round(time.time() - started, 2)
    engine._workos_bridge_version = BRIDGE_VERSION
    engine._workos_peer_comparison_enabled = False
    return engine


def _get_data_diagnostics(engine=None):
    try:
        data_module = getattr(engine, "_workos_data_module", None) if engine is not None else None
        if data_module is None:
            return {"diagnostic_reader": "未找到本次 ValueStock 使用的 data 模块"}

        getter = getattr(data_module, "get_data_diagnostics", None)
        if callable(getter):
            raw = getter()
            if isinstance(raw, dict):
                return {str(k): str(v) for k, v in raw.items()}
            return {"diagnostic_reader": f"诊断结果类型异常：{type(raw).__name__}"}

        # 兼容旧版 data.py：没有诊断函数时，直接读取底层状态变量。
        status = getattr(data_module, "_SOURCE_STATUS", {})
        errors = getattr(data_module, "_LAST_ERRORS", {})
        result = {}
        if isinstance(status, dict):
            result.update({str(k): str(v) for k, v in status.items()})
        if isinstance(errors, dict):
            for key, value in errors.items():
                if str(key) not in result or result[str(key)] in {"失败", "异常"}:
                    result[str(key)] = str(value)
        if result:
            return result

        return {
            "diagnostic_reader": "本次 ValueStock 数据模块已加载，但没有记录数据源错误。",
            "data_module": str(getattr(data_module, "__file__", "unknown")),
        }
    except Exception as exc:
        return {"diagnostic_reader": f"{type(exc).__name__}: {exc}"}


_ANALYSIS_CACHE = {}
_ANALYSIS_CACHE_TTL = 90


def run_value_stock_analysis(stock_code: str, peer_input: str = "", override: str = "自动识别") -> dict[str, Any]:
    started = time.time()
    code = str(stock_code).strip()
    cache_key = (code, str(override or "自动识别"))

    cached = _ANALYSIS_CACHE.get(cache_key)
    if cached and time.time() - cached["time"] < _ANALYSIS_CACHE_TTL:
        result = dict(cached["result"])
        bridge = dict(result.get("bridge") or {})
        bridge.update({"cache_hit": True, "elapsed_seconds": round(time.time() - started, 2)})
        result["bridge"] = bridge
        return result

    try:
        engine = _load_value_stock_engine()
        load_time = getattr(engine, "_workos_bridge_load_time", 0.0)
        analysis_started = time.time()
        result = engine.analyze_stock(code, peer_input="", override=override)
        analysis_time = round(time.time() - analysis_started, 2)

        if isinstance(result, dict):
            dc = result.get("data_center", {})
            result["source"] = {
                "repo": REPO,
                "branch": BRANCH,
                "bridge_version": BRIDGE_VERSION,
                "engine_file": getattr(engine, "_workos_engine_file", ""),
                "data_module_file": str(getattr(getattr(engine, "_workos_data_module", None), "__file__", "")),
            }
            result["diagnostics"] = _get_data_diagnostics(engine)
            result["bridge"] = {
                "version": BRIDGE_VERSION,
                "engine_cached": True,
                "cache_hit": False,
                "peer_comparison_enabled": False,
                "peer_modules_loaded_for_compatibility_only": True,
                "full_analysis_retry": False,
                "parallel_data_prefetch": True,
                "source_repo": REPO,
                "data_score": dc.get("score", 100) if isinstance(dc, dict) else 100,
                "engine_load_seconds": load_time,
                "analysis_seconds": analysis_time,
                "elapsed_seconds": round(time.time() - started, 2),
            }
            _ANALYSIS_CACHE[cache_key] = {"time": time.time(), "result": result}
        return result

    except Exception as exc:
        return {
            "success": False,
            "error": f"ValueStock AI共享引擎调用失败：{type(exc).__name__}: {exc}",
            "diagnostics": {"bridge_error": f"{type(exc).__name__}: {exc}", "bridge_version": BRIDGE_VERSION},
            "bridge": {
                "version": BRIDGE_VERSION,
                "peer_comparison_enabled": False,
                "elapsed_seconds": round(time.time() - started, 2),
            },
        }
