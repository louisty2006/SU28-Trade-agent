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

_HORIZON_HOLDING_LABEL = {
    "6m": "6 個月 (6 months)",
    "1y": "1 年 (1 year)",
    "3y": "3 年 (3 years)",
    "5y+": "5 年以上 (5 years+)",
}

_HORIZON_GUIDANCE = {
    "6m": {
        "label": "6-month investment horizon",
        "focus": (
            "Focus on a 6-month investment case: next 1-2 earnings reports, near-term "
            "catalysts, estimate revisions, margin inflection, valuation re-rating risk, "
            "liquidity, and downside if catalysts slip."
        ),
        "action": (
            "Actions should define whether to buy now, wait for a catalyst/price level, "
            "or avoid until the 6-month thesis is de-risked."
        ),
    },
    "1y": {
        "label": "12-month investment horizon",
        "focus": (
            "Focus on a 12-month investment case: execution milestones, industry cycle, "
            "macro sensitivity, earnings growth, valuation normalization, and expected "
            "drivers over the next four quarters."
        ),
        "action": (
            "Actions should map accumulation and review triggers to 12-month milestones "
            "rather than open-ended multi-year holding."
        ),
    },
    "3y": {
        "label": "3-year investment horizon",
        "focus": (
            "Focus on a 3-year investment case: business quality, moat, compounding "
            "potential, multi-year revenue and earnings growth, capital allocation, and "
            "valuation against durable growth."
        ),
        "action": (
            "Actions should support phased accumulation and monitoring across a 3-year "
            "holding period."
        ),
    },
    "5y+": {
        "label": "5-year-plus investment horizon",
        "focus": (
            "Focus on a 5-year-plus investment case: durable competitive advantage, "
            "management quality, capital allocation, secular industry structure, balance "
            "sheet resilience, and long-run thesis-breakers."
        ),
        "action": (
            "Actions should emphasize long-term position sizing, rebalancing, and "
            "invalidation triggers over tactical entry timing."
        ),
    },
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


def horizon_holding_label(config: dict | None = None) -> str:
    """Human-readable holding period for the active long-term horizon."""
    if config is None:
        from tradingagents.dataflows.config import get_config

        config = get_config()
    horizon = config.get("investment_horizon", "3y")
    return _HORIZON_HOLDING_LABEL.get(horizon, horizon)


def horizon_guidance(config: dict | None = None) -> str:
    if config is None:
        from tradingagents.dataflows.config import get_config

        config = get_config()
    horizon = config.get("investment_horizon", "3y")
    guidance = _HORIZON_GUIDANCE.get(horizon, _HORIZON_GUIDANCE["3y"])
    return (
        f" Horizon target: {guidance['label']}. {guidance['focus']} "
        f"{guidance['action']}"
    )


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
    prompt = prompts.get(mode, prompts.get("short_term", ""))
    if mode == "long_term":
        prompt += horizon_guidance(config)
    return prompt


def pm_mode_instructions(config: dict | None = None) -> str:
    if is_long_term(config):
        if config is None:
            from tradingagents.dataflows.config import get_config

            config = get_config()
        holding = horizon_holding_label(config)
        guidance = horizon_guidance(config)
        return (
            f"\n\n**Long-term mode**: You MUST set time_horizon to the holding period {holding}. "
            "Set price_target to a concrete suggested exit price and fill "
            "fair_value_low/fair_value_high when estimable. The executive_summary MUST state "
            "the holding period, a suggested entry price, and a suggested exit price. Also fill "
            "conviction and invalidation_triggers (what would break the thesis). Structure "
            f"investment_thesis around business quality, valuation, catalysts, and bear case.{guidance}"
        )
    return (
        "\n\n**Short-term mode**: Focus on actionable entry, sizing, and risk levels for "
        "near-term trading."
    )


def research_manager_mode_instructions(config: dict | None = None) -> str:
    if is_long_term(config):
        guidance = horizon_guidance(config)
        return (
            "\n\n**Long-term mode**: strategic_actions should describe accumulation pace, "
            f"target portfolio weight, and rebalance triggers—not day-trading entries.{guidance}"
        )
    return ""


def trader_mode_instructions(config: dict | None = None) -> str:
    if is_long_term(config):
        guidance = horizon_guidance(config)
        holding = horizon_holding_label(config)
        return (
            " You are planning an investment action plan, not day trading. "
            f"State the intended holding period as {holding}. For any Buy, you MUST "
            "provide concrete numbers for entry_price (建議入場價), target_price "
            "(建議離場價 / take-profit, consistent with that holding period) and "
            "stop_loss (止蝕價). Also give position_sizing and phased-buying guidance."
            f"{guidance}"
        )
    return ""
