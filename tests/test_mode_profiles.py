"""Mode profile prompts stay aligned with selected investment horizons."""

import pytest

from tradingagents.mode_profiles import (
    get_analyst_system_prompt,
    pm_mode_instructions,
    research_manager_mode_instructions,
    trader_mode_instructions,
)


@pytest.mark.unit
def test_long_term_six_month_prompt_mentions_six_month_horizon():
    cfg = {"investment_mode": "long_term", "investment_horizon": "6m"}

    prompt = get_analyst_system_prompt("fundamentals", cfg)
    assert "6-month investment case" in prompt
    assert "next 1-2 earnings" in prompt


@pytest.mark.unit
def test_manager_trader_pm_prompts_use_selected_horizon():
    cfg = {"investment_mode": "long_term", "investment_horizon": "6m"}

    assert "6-month investment horizon" in research_manager_mode_instructions(cfg)
    assert "6-month investment horizon" in trader_mode_instructions(cfg)
    pm_prompt = pm_mode_instructions(cfg)
    assert "6 個月" in pm_prompt
    assert "6-month investment horizon" in pm_prompt
