# =========================================================
# Personal AI Work OS
# ValueStock AI Bridge V2.0.0
# =========================================================
# 性能优化：
# 1. ValueStock 引擎只加载一次。
# 2. GitHub commit 5 分钟缓存。
# 3. 缺失模块并行下载。
# 4. 目标股票的 6 类数据并行获取。
# 5. 6 类数据全部并行，不再让三张报表排队。
# 6. 同行业股票并行获取，避免同行分析逐只等待。
# 7. 同一股票短时间重复分析直接复用结果。
# 8. 不修改 ValueStock 独立版核心代码。
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
_LATEST_COMMIT_VALUE = None
_LATEST_COMMIT_TIME = 0.0
_COMMIT_TTL_SECONDS = 300


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

    # 首次加载时并行下载缺失模块，避免 15 个文件逐个等待。
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
    importlib.import_module("relative_valuation")
    importlib.import_module("peer_compare")
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
        # 6 类数据全部同时发起；底层仍保留 ValueStock 自己的重试/备用源。
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
    peer_module = sys.modules.get("peer_compare")
    if peer_module is not None:
        peer_module.load_stock_data = fast_load_stock_data

    # ---------------------------------------------------------
    # Work OS 专用同行并行层
    # ValueStock 独立版 _peer_rows 保持不变；这里仅替换内存中的函数。
    # ---------------------------------------------------------
    def fast_peer_rows(code, data, peer_codes):
        rows = []

        def build_one(pc):
            try:
                pdta = data if pc == code else fast_load_stock_data(pc)
                if pdta is None or pdta.get("indicators") is None or pdta["indicators"].empty:
                    return None
                pfd = engine.process_financial_indicators(pdta["indicators"])["annual"]
                pm = pdta.get("market") or {}
                pp = engine.sf(pm.get("最新价")) or engine.get_latest_price(pdta.get("history"))
                pe = None if pp is None or pfd.get("eps") in {None, 0} else pp / pfd["eps"]
                pbt = None if pp is None or pfd.get("bvps") in {None, 0} else pp / pfd["bvps"]
                pname = pm.get("名称") or engine.get_stock_name(pc) or pc
                return {
                    "代码": pc,
                    "名称": pname,
                    "价格": pp,
                    "ROE": pfd.get("roe"),
                    "营收增长率": pfd.get("revenue_growth"),
                    "净利润增长率": pfd.get("profit_growth"),
                    "PE": pe,
                    "PB": pbt,
                    "资产负债率": pfd.get("debt"),
                }
            except Exception:
                return None

        targets = [code] + list(peer_codes[:5])
        with ThreadPoolExecutor(max_workers=min(3, len(targets))) as pool:
            future_map = {pool.submit(build_one, pc): pc for pc in targets}
            for future in as_completed(future_map):
                row = future.result()
                if row is not None:
                    rows.append(row)
        # 保持目标股票在第一位，尽量贴近独立版输出顺序。
        rows.sort(key=lambda x: 0 if x.get("代码") == code else 1)
        return rows

    engine._peer_rows = fast_peer_rows

    load_time = round(time.time() - started, 2)
    engine._workos_bridge_load_time = load_time
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


_ANALYSIS_CACHE = {}
_ANALYSIS_CACHE_TTL = 90


def run_value_stock_analysis(stock_code: str, peer_input: str = "", override: str = "自动识别") -> dict[str, Any]:
    started = time.time()
    code = str(stock_code).strip()
    cache_key = (code, str(peer_input or ""), str(override or "自动识别"))

    cached = _ANALYSIS_CACHE.get(cache_key)
    if cached and time.time() - cached["time"] < _ANALYSIS_CACHE_TTL:
        result = cached["result"]
        if isinstance(result, dict):
            result = dict(result)
            bridge = dict(result.get("bridge") or {})
            bridge.update({"cache_hit": True, "elapsed_seconds": round(time.time() - started, 2)})
            result["bridge"] = bridge
        return result

    try:
        engine, commit_sha = _load_value_stock_engine()
        load_time = getattr(engine, "_workos_bridge_load_time", 0.0)
        analysis_started = time.time()
        result = engine.analyze_stock(code, peer_input=peer_input, override=override)
        analysis_time = round(time.time() - analysis_started, 2)

        if isinstance(result, dict):
            dc = result.get("data_center", {})
            score = dc.get("score", 100) if isinstance(dc, dict) else 100
            result["source_commit"] = commit_sha
            result["diagnostics"] = _get_data_diagnostics(engine)
            result["bridge"] = {
                "version": "V2.0.0",
                "engine_cached": True,
                "cache_hit": False,
                "full_analysis_retry": False,
                "data_retry_delegated_to_valuestock": True,
                "parallel_data_prefetch": True,
                "parallel_peer_analysis": True,
                "source_repo": REPO,
                "data_score": score,
                "engine_load_seconds": load_time,
                "analysis_seconds": analysis_time,
                "elapsed_seconds": round(time.time() - started, 2),
                "optimization": "6-way target data + parallel peers + cached repeat analysis",
            }
            _ANALYSIS_CACHE[cache_key] = {"time": time.time(), "result": result}
        return result
    except Exception as exc:
        return {
            "success": False,
            "error": f"ValueStock AI共享引擎调用失败：{type(exc).__name__}: {exc}",
            "diagnostics": {"bridge_error": f"{type(exc).__name__}: {exc}"},
            "bridge": {
                "version": "V2.0.0",
                "engine_cached": True,
                "parallel_data_prefetch": True,
                "parallel_peer_analysis": True,
                "source_repo": REPO,
                "elapsed_seconds": round(time.time() - started, 2),
            },
        }
