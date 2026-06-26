"""Deterministic fundamental metrics for screening and long-term analysis."""

from __future__ import annotations

import math
from typing import Any

import yfinance as yf

from tradingagents.dataflows.symbol_utils import normalize_symbol


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _cagr(start: float | None, end: float | None, years: float) -> float | None:
    if start is None or end is None or start <= 0 or end <= 0 or years <= 0:
        return None
    try:
        return (end / start) ** (1 / years) - 1
    except (ValueError, ZeroDivisionError):
        return None


def fetch_ticker_info(ticker: str) -> dict[str, Any]:
    """Return yfinance .info dict for a normalized ticker."""
    sym = normalize_symbol(ticker)
    t = yf.Ticker(sym)
    return dict(t.info or {})


def compute_trend_metrics(ticker: str, years: int = 5) -> dict[str, Any]:
    """Compute screening-friendly metrics from yfinance info and statements."""
    info = fetch_ticker_info(ticker)
    sym = normalize_symbol(ticker)

    revenue = _safe_float(info.get("totalRevenue"))
    profit_margin = _safe_float(info.get("profitMargins"))
    roe = _safe_float(info.get("returnOnEquity"))
    debt_equity = _safe_float(info.get("debtToEquity"))
    pe = _safe_float(info.get("trailingPE"))
    forward_pe = _safe_float(info.get("forwardPE"))
    peg = _safe_float(info.get("pegRatio"))
    fcf = _safe_float(info.get("freeCashflow"))
    market_cap = _safe_float(info.get("marketCap"))
    beta = _safe_float(info.get("beta"))
    div_yield = _safe_float(info.get("dividendYield"))
    sector = info.get("sector") or "Unknown"
    name = info.get("shortName") or info.get("longName") or sym

    fcf_yield = None
    if fcf is not None and market_cap and market_cap > 0:
        fcf_yield = fcf / market_cap

    earnings_growth = _safe_float(info.get("earningsGrowth"))
    revenue_growth = _safe_float(info.get("revenueGrowth"))

    return {
        "ticker": sym,
        "name": name,
        "sector": sector,
        "revenue": revenue,
        "profit_margin": profit_margin,
        "roe": roe,
        "debt_equity": debt_equity,
        "pe": pe,
        "forward_pe": forward_pe,
        "peg": peg,
        "fcf_yield": fcf_yield,
        "earnings_growth": earnings_growth,
        "revenue_growth": revenue_growth,
        "beta": beta,
        "dividend_yield": div_yield,
        "market_cap": market_cap,
    }


def compute_valuation_snapshot(ticker: str) -> dict[str, Any]:
    """Point-in-time valuation fields from yfinance info."""
    info = fetch_ticker_info(ticker)
    return {
        "pe": _safe_float(info.get("trailingPE")),
        "forward_pe": _safe_float(info.get("forwardPE")),
        "peg": _safe_float(info.get("pegRatio")),
        "price_to_book": _safe_float(info.get("priceToBook")),
        "enterprise_to_ebitda": _safe_float(info.get("enterpriseToEbitda")),
        "fcf_yield": (
            _safe_float(info.get("freeCashflow")) / _safe_float(info.get("marketCap"))
            if _safe_float(info.get("marketCap"))
            else None
        ),
    }
