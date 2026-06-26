"""Investment mode profiles: short-term trading vs long-term investing.

Single source of truth for lookbacks, reflection horizons, and prompt hints.
Merged into the active config by the CLI and TradingAgentsGraph.
"""

from __future__ import annotations

from copy import deepcopy

INVESTMENT_MODES = ("short_term", "long_term")
INVESTMENT_HORIZONS = ("6m", "1y", "3y", "5y+")

_HORIZON_REFLECTION_DAYS = {
    "6m": 126,
    "1y": 252,
    "3y": 756,
    "5y+": 1260,
}

_SHORT_TERM_PROFILE = {
    "global_news_lookback_days": 7,
    "macro_lookback_days": 365,
    "market_lookback_days": 30,
    "market_snapshot_max_days": 30,
    "fundamentals_statement_freq": "quarterly",
    "sentiment_lookback_days": 7,
    "reflection_holding_days": 5,
    "sentiment_weight": "primary",
    "report_template": "trading",
}

_LONG_TERM_BASE = {
    "global_news_lookback_days": 90,
    "macro_lookback_days": 1825,
    "market_lookback_days": 756,
    "market_snapshot_max_days": 252,
    "fundamentals_statement_freq": "annual",
    "sentiment_lookback_days": 30,
    "sentiment_weight": "overlay",
    "report_template": "investment_memo",
}


def reflection_days_for_horizon(horizon: str | None) -> int:
    if not horizon:
        return _HORIZON_REFLECTION_DAYS["3y"]
    return _HORIZON_REFLECTION_DAYS.get(horizon, _HORIZON_REFLECTION_DAYS["3y"])


def get_mode_profile(mode: str, horizon: str | None = None) -> dict:
    """Return config overrides for the given investment mode."""
    if mode not in INVESTMENT_MODES:
        mode = "short_term"
    if mode == "short_term":
        return deepcopy(_SHORT_TERM_PROFILE)
    profile = deepcopy(_LONG_TERM_BASE)
    profile["reflection_holding_days"] = reflection_days_for_horizon(horizon)
    profile["investment_horizon"] = horizon or "3y"
    return profile


def merge_mode_into_config(config: dict) -> dict:
    """Apply mode profile fields onto a config copy."""
    merged = deepcopy(config)
    mode = merged.get("investment_mode", "short_term")
    horizon = merged.get("investment_horizon")
    profile = get_mode_profile(mode, horizon)
    merged.update(profile)
    return merged


def is_long_term(config: dict | None = None) -> bool:
    if config is None:
        from tradingagents.dataflows.config import get_config

        config = get_config()
    return config.get("investment_mode", "short_term") == "long_term"


def mode_label(config: dict | None = None) -> str:
    if config is None:
        from tradingagents.dataflows.config import get_config

        config = get_config()
    mode = config.get("investment_mode", "short_term")
    if mode == "long_term":
        return f"Long-term ({config.get('investment_horizon', '3y')})"
    return "Short-term"


_ANALYST_PROMPTS: dict[str, dict[str, str]] = {
    "fundamentals": {
        "short_term": (
            "You are a researcher tasked with analyzing fundamental information over the past week "
            "about a company. Write a comprehensive report of financial documents, company profile, "
            "basic financials, and financial history to inform traders. Include actionable insights "
            "with supporting evidence."
        ),
        "long_term": (
            "You are a long-term investment analyst. Analyze 3–5 years of fundamentals: revenue and "
            "earnings trends, margin stability, free cash flow, capital allocation, balance-sheet "
            "strength, and competitive moat. Prefer annual statements; use quarterly for recent "
            "inflection. Focus on business quality and valuation context for a multi-year hold, "
            "not short-term trading signals."
        ),
    },
    "market": {
        "short_term": (
            "You are a trading assistant analyzing financial markets for short-term opportunities. "
            "Select complementary technical indicators, emphasize entries, stop-loss (ATR), and "
            "momentum. Provide actionable insights for traders."
        ),
        "long_term": (
            "You are a long-term market analyst. Emphasize 200-week/200-day trends, multi-year "
            "relative performance vs the benchmark, drawdown history, and valuation-relevant price "
            "levels. De-emphasize short-term RSI/MACD noise; support a multi-year investment thesis."
        ),
    },
    "news": {
        "short_term": (
            "You are a news researcher analyzing recent news and trends over the past week relevant "
            "for trading and macroeconomics. Provide actionable insights for traders."
        ),
        "long_term": (
            "You are a macro and industry analyst for long-term investors. Cover structural themes "
            "over the past 90–365 days, multi-year macro cycles (use FRED with extended lookback), "
            "and secular industry tailwinds/headwinds—not day-to-day headlines alone."
        ),
    },
    "sentiment": {
        "short_term": (
            "Produce a comprehensive sentiment report from news, StockTwits, and Reddit for the "
            "analysis window. Treat sentiment as a tactical signal for traders."
        ),
        "long_term": (
            "Produce a sentiment overlay report. Label clearly that retail sentiment is short-term "
            "noise and must NOT drive the long-term investment thesis. Note divergences only if "
            "they flag extreme positioning risk for a multi-year holder."
        ),
    },
}


def get_analyst_system_prompt(analyst: str, config: dict | None = None) -> str:
    if config is None:
        from tradingagents.dataflows.config import get_config

        config = get_config()
    mode = config.get("investment_mode", "short_term")
    prompts = _ANALYST_PROMPTS.get(analyst, {})
    return prompts.get(mode, prompts.get("short_term", ""))


def pm_mode_instructions(config: dict | None = None) -> str:
    if is_long_term(config):
        horizon = (config or {}).get("investment_horizon", "3y")
        return (
            f"\n\n**Long-term mode**: You MUST set time_horizon to reflect a {horizon} hold. "
            "Fill conviction, fair_value_low/fair_value_high when estimable, and "
            "invalidation_triggers (what would break the thesis). Structure investment_thesis "
            "around business quality, valuation, catalysts, and bear case."
        )
    return (
        "\n\n**Short-term mode**: Focus on actionable entry, sizing, and risk levels for "
        "near-term trading."
    )


def research_manager_mode_instructions(config: dict | None = None) -> str:
    if is_long_term(config):
        return (
            "\n\n**Long-term mode**: strategic_actions should describe accumulation pace, "
            "target portfolio weight, and rebalance triggers—not day-trading entries."
        )
    return ""


def trader_mode_instructions(config: dict | None = None) -> str:
    if is_long_term(config):
        return (
            " You are planning a multi-year accumulation strategy. entry_price and stop_loss are "
            "optional; emphasize position_sizing and phased buying."
        )
    return ""
