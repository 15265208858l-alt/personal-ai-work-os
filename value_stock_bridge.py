# =========================================================
# Personal AI Work OS
# V1.5 ValueStock AI Bridge
#
# 不复制 ValueStock AI 的分析模块。
# 运行时直接从用户自己的 value-stock-ai/main 获取最新模块，
# Work OS 只负责调度和汇总。
# =========================================================

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import requests


REPO = "15265208858l-alt/value-stock-ai"
BRANCH = "main"
CACHE_ROOT = Path(".value_stock_cache")


def _load_value_stock_modules():
    """下载并加载 ValueStock AI 最新 Python 模块。"""
    CACHE_ROOT.mkdir(exist_ok=True)

    ref_url = f"https://api.github.com/repos/{REPO}/git/ref/heads/{BRANCH}"
    ref = requests.get(ref_url, timeout=15)
    ref.raise_for_status()
    commit_sha = ref.json()["object"]["sha"]
    cache_dir = CACHE_ROOT / commit_sha[:12]
    cache_dir.mkdir(exist_ok=True)

    api_url = f"https://api.github.com/repos/{REPO}/contents/?ref={BRANCH}"
    listing = requests.get(api_url, timeout=15)
    listing.raise_for_status()

    py_files = [x["name"] for x in listing.json() if x.get("type") == "file" and x.get("name", "").endswith(".py") and x.get("name") != "app.py"]

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

    return commit_sha


def _num(value):
    try:
        if value is None or str(value).strip() in {"", "--", "None", "none", "nan", "NaN"}:
            return None
        return float(str(value).replace(",", "").replace("%", ""))
    except Exception:
        return None


def _load_modules():
    _load_value_stock_modules()

    modules = {}
    names = [
        "data", "financial", "risk", "valuation", "adaptive_valuation",
        "earnings_basis", "growth_quality", "historical_valuation",
        "peer_compare", "investment_score", "investment_decision", "industry"
    ]

    for name in names:
        modules[name] = importlib.import_module(name)

    return modules


def _build_peer_dataframe(modules, target_code):
    industry = modules["industry"]
    data_mod = modules["data"]
    financial = modules["financial"]

    info = industry.get_peer_candidates(target_code, max_peers=2)
    codes = [target_code] + info.get("peers", [])
    rows = []

    for code in codes:
        try:
            stock_data = data_mod.load_stock_data(code)
            if not stock_data:
                continue
            indicators = stock_data.get("indicators")
            if indicators is None or indicators.empty:
                continue
            fd = financial.process_financial_indicators(indicators)
            latest = fd.get("latest", {})
            market = stock_data.get("market") or {}
            price = _num(market.get("最新价"))
            eps = _num(latest.get("eps"))
            bvps = _num(latest.get("bvps"))
            pe = None if price is None or eps is None or eps <= 0 else price / eps
            pb = None if price is None or bvps is None or bvps <= 0 else price / bvps
            rows.append({
                "代码": code,
                "ROE": _num(latest.get("roe")),
                "营收增长率": _num(latest.get("revenue_growth")),
                "净利润增长率": _num(latest.get("profit_growth")),
                "资产负债率": _num(latest.get("debt")),
                "PE": pe,
                "PB": pb,
            })
        except Exception:
            continue

    return pd.DataFrame(rows), info


def run_value_stock_analysis(stock_code: str) -> dict[str, Any]:
    """调用 ValueStock AI V17.x 核心模块并返回结构化结果。"""
    code = str(stock_code).strip()
    if not (len(code) == 6 and code.isdigit()):
        return {"success": False, "error": "股票代码必须是6位数字。"}

    try:
        m = _load_modules()
        data_mod = m["data"]
        financial = m["financial"]
        risk_mod = m["risk"]
        valuation = m["valuation"]
        adaptive = m["adaptive_valuation"]
        earnings = m["earnings_basis"]
        growth = m["growth_quality"]
        historical = m["historical_valuation"]
        peer = m["peer_compare"]
        score_mod = m["investment_score"]
        decision_mod = m["investment_decision"]
        industry = m["industry"]

        data = data_mod.load_stock_data(code)
        if data is None:
            return {"success": False, "error": "ValueStock AI 未获取到股票数据。"}

        completeness = data_mod.check_data_completeness(data)
        market = data.get("market") or {}
        history = data.get("history")
        indicators = data.get("indicators")

        name = market.get("名称") or industry.get_stock_name(code) or code
        price = _num(market.get("最新价"))
        change_pct = _num(market.get("涨跌幅"))

        if indicators is None or indicators.empty:
            return {"success": False, "error": "ValueStock AI 财务指标获取失败。"}

        fd = financial.process_financial_indicators(indicators)
        latest = fd.get("latest", {})
        annual = fd.get("annual", {})
        trend = fd.get("trend")

        annual_roe = _num(annual.get("roe"))
        annual_eps = _num(annual.get("eps"))
        annual_bvps = _num(annual.get("bvps"))
        annual_debt = _num(annual.get("debt"))

        def lastv(df, names):
            if df is None or df.empty:
                return None
            for c in names:
                if c in df.columns:
                    return _num(df.iloc[0][c])
            return None

        profit = data.get("profit")
        balance = data.get("balance")
        cashflow = data.get("cashflow")
        revenue = lastv(profit, ["营业总收入", "营业收入", "一、营业总收入"])
        net_profit = lastv(profit, ["归属于母公司所有者的净利润", "归属于母公司股东的净利润", "净利润", "五、净利润"])
        receivable = lastv(balance, ["应收账款", "应收款项"])
        inventory = lastv(balance, ["存货"])
        ocf = lastv(cashflow, ["经营活动产生的现金流量净额", "经营活动现金流量净额"])

        cash_ratio = None if ocf is None or net_profit in {None, 0} else ocf / net_profit
        risk = risk_mod.analyze_financial_risk(ocf, net_profit, receivable, revenue, inventory, annual_roe, annual_debt)
        risk_score = risk.get("score", 5)

        financial_quality = financial.calculate_financial_quality(trend, cash_ratio)

        override = "自动识别"
        model = adaptive.detect_valuation_model(stock_code=code, override=override)
        cfg = dict(adaptive.get_valuation_config(model, annual_roe=annual_roe))

        earn = earnings.build_earnings_basis(
            indicators=indicators,
            annual_eps=annual_eps,
            operating_cashflow_ratio=cash_ratio,
            profit_growth=latest.get("profit_growth"),
        )
        normalized_eps = earn.get("normalized_eps")
        valuation_eps = normalized_eps or annual_eps

        annual_pe = None if price is None or annual_eps is None or annual_eps <= 0 else price / annual_eps
        hist = historical.build_historical_pe(history, trend, max_years=10)
        hs = historical.calculate_historical_statistics(hist, annual_pe)

        growth_quality = None
        if model == "growth_tech":
            growth_quality = growth.calculate_growth_quality(
                revenue_growth=latest.get("revenue_growth"),
                profit_growth=latest.get("profit_growth"),
                roe=latest.get("roe") if latest.get("roe") is not None else annual_roe,
                cashflow_ratio=cash_ratio,
                ttm_eps=earn.get("ttm_eps"),
                annual_eps=annual_eps,
                historical_percentile=hs.get("percentile"),
            )
            dynamic_pe = growth.get_dynamic_growth_pe(
                growth_quality["score"],
                historical_percentile=hs.get("percentile"),
                cashflow_ratio=cash_ratio,
            )
            cfg["conservative_pe"] = dynamic_pe["conservative_pe"]
            cfg["normal_pe"] = dynamic_pe["normal_pe"]
            cfg["optimistic_pe"] = dynamic_pe["optimistic_pe"]

        valuation_pe = None if price is None or valuation_eps is None or valuation_eps <= 0 else price / valuation_eps
        pb = None if price is None or annual_bvps is None or annual_bvps <= 0 else price / annual_bvps

        vr = valuation.calculate_valuation_scenarios(
            eps=valuation_eps,
            bvps=annual_bvps,
            conservative_pe=cfg["conservative_pe"],
            normal_pe=cfg["normal_pe"],
            optimistic_pe=cfg["optimistic_pe"],
            conservative_pb=cfg["conservative_pb"],
            normal_pb=cfg["normal_pb"],
            optimistic_pb=cfg["optimistic_pb"],
            pe_weight=cfg["pe_weight"],
            pb_weight=cfg["pb_weight"],
        )

        # 同行比较：沿用 ValueStock AI 的同行池和评分模块。
        peer_df, peer_info = _build_peer_dataframe(m, code)
        peer_result = peer.calculate_peer_score(peer_df, code)
        peer_score = peer_result.get("score") if peer_result else None

        valuation_gap = None
        if price is not None and vr.get("normal") is not None and price != 0:
            valuation_gap = (vr["normal"] / price - 1) * 100

        investment = score_mod.calculate_investment_score(
            financial_score=financial_quality.get("score"),
            peer_score=peer_score,
            valuation_gap=valuation_gap,
            risk_score=risk_score,
            historical_percentile=hs.get("percentile"),
        )

        decision = decision_mod.make_investment_decision(
            investment_score=investment.get("score"),
            valuation_level=investment.get("valuation_level"),
            historical_level=investment.get("historical_level"),
            risk_level=investment.get("risk_level"),
        )

        return {
            "success": True,
            "engine": "ValueStock AI V17.x",
            "code": code,
            "name": name,
            "industry": peer_info.get("industry"),
            "price": price,
            "change_pct": change_pct,
            "data_completeness": completeness,
            "financial": {
                "roe": _num(latest.get("roe")),
                "revenue_growth": _num(latest.get("revenue_growth")),
                "profit_growth": _num(latest.get("profit_growth")),
                "debt": _num(latest.get("debt")),
                "annual_roe": annual_roe,
                "annual_eps": annual_eps,
                "annual_bvps": annual_bvps,
                "annual_debt": annual_debt,
                "quality_score": financial_quality.get("score"),
                "quality_rating": financial_quality.get("rating"),
                "cash_ratio": cash_ratio,
            },
            "risk": {
                "score": risk_score,
                "items": risk.get("risk_items", []),
            },
            "valuation": {
                "model": cfg.get("name", model),
                "annual_pe": annual_pe,
                "valuation_pe": valuation_pe,
                "pb": pb,
                "normalized_eps": normalized_eps,
                "conservative": vr.get("conservative"),
                "normal": vr.get("normal"),
                "optimistic": vr.get("optimistic"),
                "entry_price": vr.get("entry_price"),
                "heavy_price": vr.get("heavy_price"),
                "valuation_gap": valuation_gap,
                "historical_percentile": hs.get("percentile"),
                "historical_level": historical.get_historical_valuation_level(hs.get("percentile")),
            },
            "growth_quality": growth_quality,
            "peer": {
                "industry": peer_info.get("industry"),
                "peers": peer_info.get("peers", []),
                "score": peer_score,
                "rating": peer_result.get("rating") if peer_result else None,
                "relative": peer_result.get("relative_valuation") if peer_result else {},
            },
            "investment": investment,
            "decision": decision,
        }

    except Exception as exc:
        return {
            "success": False,
            "error": f"ValueStock AI 调用失败：{type(exc).__name__}: {exc}",
        }
