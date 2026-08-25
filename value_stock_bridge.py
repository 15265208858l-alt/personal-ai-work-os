# =========================================================
# Personal AI Work OS
# ValueStock AI Bridge V2.1.0
# =========================================================
# 核心修复：
# 1. 运行时不再访问 api.github.com，彻底消除 GitHub API ReadTimeout。
# 2. 直接从 raw.githubusercontent.com/main 读取 ValueStock 模块。
# 3. 保留旧版 peer_compare / relative_valuation 作为兼容依赖，避免历史 import 报错。
# 4. Work OS 仍然关闭同行业比较，不执行同行数据分析。
# 5. 保留并行数据、引擎缓存、90秒重复分析缓存。
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
BRIDGE_VERSION = "V2.1.0"
SOURCE_TAG = "main"
CACHE_ROOT = Path(".value_stock_cache")

# 保留旧版 import 依赖，但不执行同行比较。
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
    # 用固定 Bridge 版本 + main 作为缓存键；不再请求 GitHub API 查询 commit。
    cache_dir = CACHE_ROOT / f"{BRIDGE_VERSION}_{SOURCE_TAG}"
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

    # 清掉可能来自旧缓存的顶层 ValueStock 模块，保证全部来自同一目录。
    for name in VALUESTOCK_MODULES:
        sys.modules.pop(name, None)
    importlib.invalidate_caches()

    # 兼容历史 analysis_engine 的 import 依赖；不执行同行比较函数。
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
    engine._workos_bridge_load_time = round(time.time() - started, 2)
    engine._workos_engine_file = str(getattr(engine, "__file__", ""))
    engine._workos_bridge_version = BRIDGE_VERSION
    engine._workos_peer_comparison_enabled = False
    return engine


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
        return {str(k): str(v) for k, v in raw.items()} if isinstance(raw, dict) else {"diagnostic_reader": f"诊断结果类型异常：{type(raw).__name__}"}
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
            "diagnostics": {
                "bridge_error": f"{type(exc).__name__}: {exc}",
                "bridge_version": BRIDGE_VERSION,
                "source": f"{REPO}/{BRANCH}",
            },
            "bridge": {
                "version": BRIDGE_VERSION,
                "peer_comparison_enabled": False,
                "elapsed_seconds": round(time.time() - started, 2),
            },
        }
