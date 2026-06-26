"""Investment mode profiles and config merge."""

import pytest

from tradingagents.mode_profiles import (
    INVESTMENT_HORIZONS,
    INVESTMENT_MODES,
    get_mode_profile,
    is_long_term,
    merge_mode_into_config,
    mode_label,
    reflection_days_for_horizon,
)


@pytest.mark.unit
def test_short_term_profile_defaults():
    profile = get_mode_profile("short_term")
    assert profile["market_lookback_days"] == 30
    assert profile["reflection_holding_days"] == 5
    assert profile["report_template"] == "trading"


@pytest.mark.unit
def test_long_term_profile_uses_horizon_reflection():
    profile = get_mode_profile("long_term", "1y")
    assert profile["market_lookback_days"] == 756
    assert profile["fundamentals_statement_freq"] == "annual"
    assert profile["reflection_holding_days"] == reflection_days_for_horizon("1y")
    assert profile["investment_horizon"] == "1y"


@pytest.mark.unit
@pytest.mark.parametrize("horizon,days", [("6m", 126), ("3y", 756), ("5y+", 1260)])
def test_reflection_days_mapping(horizon, days):
    assert reflection_days_for_horizon(horizon) == days


@pytest.mark.unit
def test_merge_mode_into_config():
    merged = merge_mode_into_config({"investment_mode": "long_term", "investment_horizon": "5y+"})
    assert merged["investment_mode"] == "long_term"
    assert merged["global_news_lookback_days"] == 90
    assert merged["reflection_holding_days"] == 1260


@pytest.mark.unit
def test_mode_label_and_is_long_term():
    cfg = {"investment_mode": "long_term", "investment_horizon": "3y"}
    assert is_long_term(cfg)
    assert "Long-term" in mode_label(cfg)
    assert is_long_term({"investment_mode": "short_term"}) is False


@pytest.mark.unit
def test_known_modes_and_horizons():
    assert "short_term" in INVESTMENT_MODES
    assert "long_term" in INVESTMENT_MODES
    assert "3y" in INVESTMENT_HORIZONS
