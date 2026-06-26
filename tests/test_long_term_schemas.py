"""Long-term structured output fields on PM and fundamentals schemas."""

import pytest

from tradingagents.agents.schemas import (
    FundamentalsReport,
    PortfolioDecision,
    PortfolioRating,
    render_fundamentals_report,
    render_pm_decision,
)


@pytest.mark.unit
def test_pm_optional_long_term_fields():
    decision = PortfolioDecision(
        rating=PortfolioRating.BUY,
        executive_summary="Accumulate on weakness.",
        investment_thesis="Quality compounder with durable moat.",
        conviction="High",
        fair_value_low=100.0,
        fair_value_high=130.0,
        invalidation_triggers=["Revenue decline >10% YoY"],
        time_horizon="3 years",
    )
    text = render_pm_decision(decision)
    assert "Conviction" in text
    assert "100" in text
    assert "Revenue" in text


@pytest.mark.unit
def test_fundamentals_report_renders_moat_section():
    report = FundamentalsReport(
        quality_score=8.0,
        growth_score=7.0,
        valuation_score=6.5,
        moat_assessment="Network effects and switching costs.",
        key_risks=["Regulatory pressure", "Competition from hyperscalers"],
        metrics_table="| Metric | Value |\n|---|---|\n| ROE | 22% |",
    )
    rendered = render_fundamentals_report(report)
    assert "moat" in rendered.lower()
    assert "Quality Score" in rendered
    assert "Regulatory" in rendered
