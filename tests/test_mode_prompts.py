"""Mode-specific analyst and manager prompt helpers."""

import pytest

from tradingagents.mode_profiles import (
    get_analyst_system_prompt,
    pm_mode_instructions,
    research_manager_mode_instructions,
    trader_mode_instructions,
)


@pytest.mark.unit
def test_analyst_prompts_differ_by_mode():
    short = get_analyst_system_prompt("fundamentals", {"investment_mode": "short_term"})
    long = get_analyst_system_prompt("fundamentals", {"investment_mode": "long_term"})
    assert short != long
    assert "long-term" in long.lower() or "multi-year" in long.lower()


@pytest.mark.unit
def test_pm_instructions_include_horizon_for_long_term():
    text = pm_mode_instructions({"investment_mode": "long_term", "investment_horizon": "3y"})
    assert "3y" in text
    assert "conviction" in text.lower()


@pytest.mark.unit
def test_trader_and_rm_long_term_hints():
    assert "accumulation" in research_manager_mode_instructions(
        {"investment_mode": "long_term"}
    ).lower()
    assert "multi-year" in trader_mode_instructions(
        {"investment_mode": "long_term"}
    ).lower()
