"""Long-term screener scoring and runner (offline / mocked)."""

from unittest import mock

import pytest

from tradingagents.screening.scorer import passes_risk_filters, score_metrics
from tradingagents.screening.universe import load_universe


@pytest.mark.unit
def test_score_metrics_composite():
    metrics = {
        "roe": 0.20,
        "profit_margin": 0.25,
        "revenue_growth": 0.12,
        "earnings_growth": 0.15,
        "peg": 1.2,
        "fcf_yield": 0.05,
        "debt_equity": 50,
        "beta": 1.1,
    }
    scores = score_metrics(metrics)
    assert 0 <= scores["composite_score"] <= 10
    assert scores["hook"]


@pytest.mark.unit
def test_risk_filters_reject_small_cap():
    assert passes_risk_filters({"market_cap": 100_000_000}) is False
    assert passes_risk_filters({"market_cap": 2_000_000_000, "debt_equity": 100}) is True


@pytest.mark.unit
def test_load_universe_custom_file(tmp_path):
    f = tmp_path / "tickers.txt"
    f.write_text("AAPL\n# comment\nMSFT\n", encoding="utf-8")
    assert load_universe("sp500", universe_file=f) == ["AAPL", "MSFT"]


@pytest.mark.unit
def test_run_screen_with_mocked_metrics(tmp_path):
    from tradingagents.screening.runner import run_screen

    fake_metrics = {
        "ticker": "AAPL",
        "sector": "Technology",
        "roe": 0.5,
        "profit_margin": 0.25,
        "revenue_growth": 0.1,
        "earnings_growth": 0.1,
        "peg": 1.0,
        "fcf_yield": 0.04,
        "debt_equity": 80,
        "beta": 1.2,
        "market_cap": 3_000_000_000_000,
    }

    with mock.patch(
        "tradingagents.screening.runner.load_universe",
        return_value=["AAPL", "MSFT"],
    ), mock.patch(
        "tradingagents.screening.runner.compute_trend_metrics",
        return_value=fake_metrics,
    ):
        result = run_screen(universe="sp500", top_n=1, output_dir=tmp_path)

    assert result["total_scored"] == 2
    assert len(result["watchlist"]) == 1
    assert (tmp_path / "watchlist.json").exists()
    assert (tmp_path / "watchlist.md").exists()
