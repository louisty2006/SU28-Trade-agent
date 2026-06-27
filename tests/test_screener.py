"""Long-term screener scoring and runner (offline / mocked)."""

from unittest import mock

import pytest

from tradingagents.screening.scorer import passes_risk_filters, score_metrics
from tradingagents.screening.universe import load_universe


@pytest.fixture(autouse=True)
def _reset_config():
    import copy

    import tradingagents.default_config as default_config
    from tradingagents.dataflows import config as cfg_mod

    cfg_mod._config = copy.deepcopy(default_config.DEFAULT_CONFIG)
    yield
    cfg_mod._config = copy.deepcopy(default_config.DEFAULT_CONFIG)


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
def test_score_metrics_changes_by_horizon():
    metrics = {
        "roe": 0.08,
        "profit_margin": 0.10,
        "revenue_growth": 0.22,
        "earnings_growth": 0.25,
        "peg": 2.5,
        "fcf_yield": 0.01,
        "debt_equity": 150,
        "beta": 1.2,
    }

    six_month = score_metrics(metrics, horizon="6m")
    five_year = score_metrics(metrics, horizon="5y+")

    assert six_month["horizon"] == "6m"
    assert five_year["horizon"] == "5y+"
    assert six_month["composite_score"] > five_year["composite_score"]


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
        from tradingagents.dataflows.config import set_config

        set_config({"investment_horizon": "6m"})
        result = run_screen(universe="sp500", top_n=1, output_dir=tmp_path)

    assert result["total_scored"] == 2
    assert result["horizon"] == "6m"
    assert result["watchlist"][0]["horizon"] == "6m"
    assert len(result["watchlist"]) == 1
    assert (tmp_path / "watchlist.json").exists()
    assert (tmp_path / "watchlist.md").exists()


@pytest.mark.unit
def test_info_is_usable():
    from tradingagents.dataflows.fundamental_analytics import _info_is_usable

    assert _info_is_usable({}) is False
    assert _info_is_usable({"marketCap": 1_000_000_000}) is True
    assert _info_is_usable({"shortName": "Apple"}) is True


@pytest.mark.unit
def test_run_screen_retries_until_ok(tmp_path):
    from yfinance.exceptions import YFRateLimitError

    from tradingagents.dataflows.config import set_config
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
    attempts = {"MSFT": 0}

    def _metrics(ticker: str):
        if ticker == "MSFT":
            attempts["MSFT"] += 1
            if attempts["MSFT"] < 2:
                raise YFRateLimitError("rate limited")
            return {**fake_metrics, "ticker": "MSFT"}
        return {**fake_metrics, "ticker": ticker}

    set_config({
        "screener_max_retry_rounds": 5,
        "screener_retry_cooldown_seconds": 0,
        "screener_max_workers": 1,
    })

    with mock.patch(
        "tradingagents.screening.runner.load_universe",
        return_value=["AAPL", "MSFT"],
    ), mock.patch(
        "tradingagents.screening.runner.compute_trend_metrics",
        side_effect=_metrics,
    ), mock.patch("tradingagents.screening.runner.time.sleep"):
        result = run_screen(universe="sp500", top_n=2, output_dir=tmp_path)

    assert result["total_scored"] == 2
    assert result["failed"] == []
    assert attempts["MSFT"] == 2


@pytest.mark.unit
def test_run_screen_lists_failed_after_max_rounds(tmp_path):
    from yfinance.exceptions import YFRateLimitError

    from tradingagents.dataflows.config import set_config
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

    def _metrics(ticker: str):
        if ticker == "MSFT":
            raise YFRateLimitError("always rate limited")
        return {**fake_metrics, "ticker": ticker}

    set_config({
        "screener_max_retry_rounds": 2,
        "screener_retry_cooldown_seconds": 0,
        "screener_max_workers": 1,
    })

    with mock.patch(
        "tradingagents.screening.runner.load_universe",
        return_value=["AAPL", "MSFT"],
    ), mock.patch(
        "tradingagents.screening.runner.compute_trend_metrics",
        side_effect=_metrics,
    ), mock.patch("tradingagents.screening.runner.time.sleep"):
        result = run_screen(universe="sp500", top_n=2, output_dir=tmp_path)

    assert result["total_scored"] == 1
    assert result["failed"] == ["MSFT"]
    assert "MSFT" in (tmp_path / "watchlist.md").read_text()
