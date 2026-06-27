import os

_TRADINGAGENTS_HOME = os.path.join(os.path.expanduser("~"), ".tradingagents")

# Single source of truth for env-var → config-key overrides. To expose
# a new config key for environment-based override, add a row here — no
# entry-point script changes required. Coercion is driven by the type
# of the existing default, so users can keep writing plain strings in
# their .env file.
_ENV_OVERRIDES = {
    "TRADINGAGENTS_LLM_PROVIDER":         "llm_provider",
    "TRADINGAGENTS_DEEP_THINK_LLM":       "deep_think_llm",
    "TRADINGAGENTS_QUICK_THINK_LLM":      "quick_think_llm",
    "TRADINGAGENTS_LLM_BACKEND_URL":      "backend_url",
    "TRADINGAGENTS_DEEP_THINK_PROVIDER":  "deep_think_provider",
    "TRADINGAGENTS_DEEP_THINK_BACKEND_URL": "deep_think_backend_url",
    "TRADINGAGENTS_QUICK_THINK_PROVIDER": "quick_think_provider",
    "TRADINGAGENTS_QUICK_THINK_BACKEND_URL": "quick_think_backend_url",
    "TRADINGAGENTS_OUTPUT_LANGUAGE":      "output_language",
    "TRADINGAGENTS_MAX_DEBATE_ROUNDS":    "max_debate_rounds",
    "TRADINGAGENTS_MAX_RISK_ROUNDS":      "max_risk_discuss_rounds",
    "TRADINGAGENTS_CHECKPOINT_ENABLED":   "checkpoint_enabled",
    "TRADINGAGENTS_BENCHMARK_TICKER":     "benchmark_ticker",
    "TRADINGAGENTS_TEMPERATURE":          "temperature",
    # Provider-specific reasoning/thinking knobs (None = each provider's own
    # default). Settable here for non-interactive runs; the CLI also offers an
    # interactive choice, which is skipped when the matching var is set.
    "TRADINGAGENTS_GOOGLE_THINKING_LEVEL":   "google_thinking_level",
    "TRADINGAGENTS_OPENAI_REASONING_EFFORT": "openai_reasoning_effort",
    "TRADINGAGENTS_ANTHROPIC_EFFORT":        "anthropic_effort",
    "TRADINGAGENTS_INVESTMENT_MODE":         "investment_mode",
    "TRADINGAGENTS_INVESTMENT_HORIZON":      "investment_horizon",
    "TRADINGAGENTS_SCREENER_TOP_N":          "screener_top_n",
    "TRADINGAGENTS_LLM_TIMEOUT":             "llm_timeout",
    "TRADINGAGENTS_LLM_MAX_RETRIES":         "llm_max_retries",
    "TRADINGAGENTS_SENTIMENT_ADAPTIVE":      "sentiment_adaptive_enabled",
    "TRADINGAGENTS_SENTIMENT_STAGE_A_CHARS": "sentiment_stage_a_max_chars",
    "TRADINGAGENTS_SENTIMENT_STAGE_B_CHARS": "sentiment_stage_b_max_chars",
    "TRADINGAGENTS_SENTIMENT_STAGE_A_STOCKTWITS_LIMIT": "sentiment_stage_a_stocktwits_limit",
    "TRADINGAGENTS_SENTIMENT_STAGE_B_STOCKTWITS_LIMIT": "sentiment_stage_b_stocktwits_limit",
    "TRADINGAGENTS_SENTIMENT_STAGE_B_MAX_STAGE_A_SECONDS": "sentiment_stage_b_max_stage_a_seconds",
    "TRADINGAGENTS_SENTIMENT_STRUCTURED_PROMPT_MAX_CHARS": "sentiment_structured_prompt_max_chars",
    "TRADINGAGENTS_SENTIMENT_FREETEXT_FIRST": "sentiment_freetext_first",
    "TRADINGAGENTS_SCREENER_MAX_WORKERS":    "screener_max_workers",
    "TRADINGAGENTS_SCREENER_MAX_RETRY_ROUNDS": "screener_max_retry_rounds",
    "TRADINGAGENTS_SCREENER_RETRY_COOLDOWN_SECONDS": "screener_retry_cooldown_seconds",
    "TRADINGAGENTS_BATCH_COOLDOWN_SECONDS":  "batch_analysis_cooldown_seconds",
    "TRADINGAGENTS_POST_SCREEN_COOLDOWN_SECONDS": "post_screen_cooldown_seconds",
    "TRADINGAGENTS_YF_MIN_INTERVAL":         "yf_min_interval_seconds",
    "TRADINGAGENTS_YF_MAX_RETRIES":          "yf_max_retries",
    "TRADINGAGENTS_YF_RETRY_BASE_DELAY":     "yf_retry_base_delay",
}


_BOOL_TRUE = ("true", "1", "yes", "on")
_BOOL_FALSE = ("false", "0", "no", "off")


def _coerce(value: str, reference):
    """Coerce env-var string to the type of the existing default value.

    Invalid values raise ``ValueError`` rather than silently falling back to a
    default — a misspelled boolean (e.g. ``treu``) or non-numeric int should fail
    loudly at startup, not quietly misconfigure an unattended run.
    """
    if isinstance(reference, bool):
        normalized = value.strip().lower()
        if normalized in _BOOL_TRUE:
            return True
        if normalized in _BOOL_FALSE:
            return False
        raise ValueError(
            f"expected a boolean ({'/'.join(_BOOL_TRUE + _BOOL_FALSE)}), got {value!r}"
        )
    if isinstance(reference, int) and not isinstance(reference, bool):
        return int(value)
    if isinstance(reference, float):
        return float(value)
    return value


def _apply_env_overrides(config: dict) -> dict:
    """Apply TRADINGAGENTS_* env vars to the config dict in-place."""
    for env_var, key in _ENV_OVERRIDES.items():
        raw = os.environ.get(env_var)
        if raw is None or raw == "":
            continue
        try:
            config[key] = _coerce(raw, config.get(key))
        except ValueError as exc:
            raise ValueError(f"Invalid value for {env_var}: {exc}") from exc
    return config


DEFAULT_CONFIG = _apply_env_overrides({
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", os.path.join(_TRADINGAGENTS_HOME, "logs")),
    "data_cache_dir": os.getenv("TRADINGAGENTS_CACHE_DIR", os.path.join(_TRADINGAGENTS_HOME, "cache")),
    "memory_log_path": os.getenv("TRADINGAGENTS_MEMORY_LOG_PATH", os.path.join(_TRADINGAGENTS_HOME, "memory", "trading_memory.md")),
    # Optional cap on the number of resolved memory log entries. When set,
    # the oldest resolved entries are pruned once this limit is exceeded.
    # Pending entries are never pruned. None disables rotation entirely.
    "memory_log_max_entries": None,
    # LLM settings
    "llm_provider": "openai",
    "deep_think_llm": "gpt-5.5",
    "quick_think_llm": "gpt-5.4-mini",
    # When None, each provider's client falls back to its own default endpoint
    # (api.openai.com for OpenAI, generativelanguage.googleapis.com for Gemini, ...).
    # The CLI overrides this per provider when the user picks one. Keeping a
    # provider-specific URL here would leak (e.g. OpenAI's /v1 was previously
    # being forwarded to Gemini, producing malformed request URLs).
    "backend_url": None,
    # Per-model provider overrides (None -> fall back to llm_provider / backend_url).
    "deep_think_provider": None,
    "deep_think_backend_url": None,
    "quick_think_provider": None,
    "quick_think_backend_url": None,
    # Provider-specific thinking configuration
    "google_thinking_level": None,      # "high", "minimal", etc.
    "openai_reasoning_effort": None,    # "medium", "high", "low"
    "anthropic_effort": None,           # "high", "medium", "low"
    # Sampling temperature, forwarded to every provider when set. None leaves
    # each provider at its own default. Lower values reduce run-to-run
    # variation on models that honor it; reasoning models largely ignore it
    # and no setting makes LLM output bit-identical across runs (see README).
    "temperature": None,
    # HTTP timeout (seconds) for LLM API calls; lower values fail faster on
    # Poe/OpenAI-compatible proxies so free-text fallback can recover sooner.
    "llm_timeout": 120,
    "llm_max_retries": 1,
    # Checkpoint/resume: when True, LangGraph saves state after each node
    # so a crashed run can resume from the last successful step.
    "checkpoint_enabled": False,
    # Output language for analyst reports and final decision
    # Internal agent debate stays in English for reasoning quality
    "output_language": "English",
    # Debate and discussion settings
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    # News / data fetching parameters
    # Increase for longer lookback strategies or to broaden macro coverage;
    # decrease to reduce token usage in agent prompts.
    "news_article_limit": 20,             # max articles per ticker (ticker-news)
    "global_news_article_limit": 10,      # max articles for global/macro news
    "global_news_lookback_days": 7,       # macro news lookback window (overridden by mode profile)
    # Investment mode: short_term (default trading) or long_term (6m–5y+ investing)
    "investment_mode": "short_term",
    "investment_horizon": "3y",           # 6m | 1y | 3y | 5y+ when long_term
    "macro_lookback_days": 365,
    "market_lookback_days": 30,
    "market_snapshot_max_days": 30,
    "fundamentals_statement_freq": "quarterly",
    "sentiment_lookback_days": 7,
    # Sentiment adaptive two-stage policy:
    # stage-A uses compact inputs for speed/stability; if stage-A is fast enough,
    # stage-B runs with larger blocks to enrich the final report.
    "sentiment_adaptive_enabled": True,
    "sentiment_stage_a_max_chars": 800,
    "sentiment_stage_b_max_chars": 1800,
    "sentiment_stage_a_stocktwits_limit": 15,
    "sentiment_stage_b_stocktwits_limit": 40,
    "sentiment_stage_b_max_stage_a_seconds": 90,
    "sentiment_structured_prompt_max_chars": 4500,
    # Skip structured-output for sentiment (faster on free/proxy models).
    "sentiment_freetext_first": True,
    "reflection_holding_days": 5,
    "sentiment_weight": "primary",
    "report_template": "trading",
    # Screener (long-term workflow)
    "screener_universe": "sp500",
    "screener_top_n": 20,
    "screener_max_workers": 2,
    # After the initial pass, retry rate-limited tickers this many times (with
    # cooldown between rounds) before listing them as failed.
    "screener_max_retry_rounds": 15,
    "screener_retry_cooldown_seconds": 60,
    # Pause between back-to-back full analyses in the Streamlit batch workflow.
    "batch_analysis_cooldown_seconds": 30,
    # After a large screener run, wait before deep analysis so Yahoo cooldown clears.
    "post_screen_cooldown_seconds": 60,
    # yfinance request pacing (shared across screening + analysts).
    "yf_min_interval_seconds": 1.0,
    "yf_max_retries": 5,
    "yf_retry_base_delay": 3.0,
    # Search queries used by get_global_news for macro headlines. Extend or
    # replace to broaden geographic / sector coverage.
    "global_news_queries": [
        "Federal Reserve interest rates inflation",
        "S&P 500 earnings GDP economic outlook",
        "geopolitical risk trade war sanctions",
        "ECB Bank of England BOJ central bank policy",
        "oil commodities supply chain energy",
    ],
    # Data vendor configuration
    # Category-level configuration (default for all tools in category).
    # The configured value is the exact vendor chain — requests are NOT silently
    # routed to vendors you didn't choose. For ordered fallback, list several,
    # e.g. "yfinance,alpha_vantage". "default" uses all available vendors.
    "data_vendors": {
        "core_stock_apis": "yfinance",       # Options: alpha_vantage, yfinance
        "technical_indicators": "yfinance",  # Options: alpha_vantage, yfinance
        "fundamental_data": "yfinance",      # Options: alpha_vantage, yfinance
        "news_data": "yfinance",             # Options: alpha_vantage, yfinance
        "macro_data": "fred",                # Options: fred (needs FRED_API_KEY)
        "prediction_markets": "polymarket",  # Options: polymarket (keyless)
    },
    # Tool-level configuration (takes precedence over category-level)
    "tool_vendors": {
        # Example: "get_stock_data": "alpha_vantage",  # Override category default
    },
    # Benchmark for alpha calculation in the reflection layer.
    # ``benchmark_ticker`` (when set) overrides the suffix map for all
    # tickers; leave it None to use ``benchmark_map`` for auto-detection
    # based on the ticker's exchange suffix. SPY remains the US default
    # so the reflection label keeps reading "Alpha vs SPY" for US tickers
    # while non-US tickers get their regional index automatically.
    "benchmark_ticker": None,
    "benchmark_map": {
        ".NS":  "^NSEI",       # NSE India (Nifty 50)
        ".BO":  "^BSESN",      # BSE India (Sensex)
        ".T":   "^N225",       # Tokyo (Nikkei 225)
        ".HK":  "^HSI",        # Hong Kong (Hang Seng)
        ".L":   "^FTSE",       # London (FTSE 100)
        ".TO":  "^GSPTSE",     # Toronto (TSX Composite)
        ".AX":  "^AXJO",       # Australia (ASX 200)
        ".SS":  "000001.SS",   # Shanghai (SSE Composite)
        ".SZ":  "399001.SZ",   # Shenzhen (SZSE Component)
        "":     "SPY",         # default for US-listed tickers (no suffix)
    },
})
