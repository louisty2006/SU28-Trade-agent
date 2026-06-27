"""Weighted scoring for long-term stock screening."""

from __future__ import annotations

from typing import Any


_HORIZON_WEIGHTS = {
    # Near-term investment: growth/catalyst sensitivity matters more, but avoid
    # very volatile balance sheets when the holding window is short.
    "6m": {"quality": 0.30, "growth": 0.45, "value": 0.25},
    "1y": {"quality": 0.35, "growth": 0.40, "value": 0.25},
    "3y": {"quality": 0.40, "growth": 0.35, "value": 0.25},
    "5y+": {"quality": 0.50, "growth": 0.25, "value": 0.25},
}


def _clip_score(value: float | None, low: float, high: float, invert: bool = False) -> float:
    if value is None:
        return 0.0
    if high == low:
        return 5.0
    t = max(0.0, min(1.0, (value - low) / (high - low)))
    if invert:
        t = 1.0 - t
    return round(t * 10, 2)


def score_metrics(metrics: dict[str, Any], horizon: str | None = None) -> dict[str, Any]:
    """Return quality/growth/value/composite scores (0–10) and a one-line hook."""
    roe = metrics.get("roe")
    margin = metrics.get("profit_margin")
    rev_g = metrics.get("revenue_growth")
    earn_g = metrics.get("earnings_growth")
    peg = metrics.get("peg")
    fcf_yield = metrics.get("fcf_yield")
    debt = metrics.get("debt_equity")
    beta = metrics.get("beta")

    quality = (
        _clip_score(roe, 0.05, 0.25)
        + _clip_score(margin, 0.05, 0.30)
        + _clip_score(debt, 0, 200, invert=True)
    ) / 3

    growth = (
        _clip_score(rev_g, 0, 0.25)
        + _clip_score(earn_g, 0, 0.30)
    ) / 2

    value = (
        _clip_score(peg, 0.5, 3.0, invert=True)
        + _clip_score(fcf_yield, 0, 0.08)
    ) / 2

    horizon = horizon or "3y"
    weights = _HORIZON_WEIGHTS.get(horizon, _HORIZON_WEIGHTS["3y"])

    # Penalize extreme beta more for shorter horizons where volatility can
    # overwhelm a 6-12 month thesis before fundamentals have time to compound.
    if beta is not None:
        if horizon == "6m" and beta > 1.5:
            quality *= 0.85
        elif horizon == "1y" and beta > 1.7:
            quality *= 0.9
        elif beta > 1.8:
            quality *= 0.9

    composite = round(
        quality * weights["quality"]
        + growth * weights["growth"]
        + value * weights["value"],
        2,
    )

    hook_parts = []
    if roe is not None and roe > 0.15:
        hook_parts.append("strong ROE")
    if rev_g is not None and rev_g > 0.1:
        hook_parts.append("solid revenue growth")
    if fcf_yield is not None and fcf_yield > 0.03:
        hook_parts.append("healthy FCF yield")
    if peg is not None and peg < 1.5:
        hook_parts.append("reasonable PEG")
    hook = ", ".join(hook_parts) if hook_parts else "balanced fundamentals"

    return {
        "quality_score": round(quality, 2),
        "growth_score": round(growth, 2),
        "value_score": round(value, 2),
        "composite_score": composite,
        "horizon": horizon,
        "hook": hook,
    }


def passes_risk_filters(metrics: dict[str, Any]) -> bool:
    """Exclude obvious red flags."""
    debt = metrics.get("debt_equity")
    rev_g = metrics.get("revenue_growth")
    cap = metrics.get("market_cap")
    if cap is not None and cap < 500_000_000:
        return False
    if debt is not None and debt > 400:
        return False
    if rev_g is not None and rev_g < -0.15:
        return False
    return True
