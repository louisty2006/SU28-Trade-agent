"""Sentiment analyst — multi-source sentiment analysis for a target ticker.

Previously named ``social_media_analyst``. Renamed and redesigned because
the old version had a prompt that demanded social-media analysis but the
only tool available was Yahoo Finance news — which led LLMs to fabricate
Reddit/X/StockTwits content under prompt pressure (verified live).

The redesigned agent pre-fetches three complementary data sources before
the LLM is invoked and injects them into the prompt as structured blocks:

  1. News headlines     — Yahoo Finance (institutional framing)
  2. StockTwits messages — retail-trader posts indexed by cashtag, with
                           user-labeled Bullish/Bearish sentiment tags
  3. Reddit posts        — r/wallstreetbets, r/stocks, r/investing

The agent does not use tool-calling; the data is in the prompt from
turn 0. Output uses the structured-output pattern (json_schema for
OpenAI/xAI, response_schema for Gemini, tool-use for Anthropic), falling
back to free-text generation for providers that lack native support, so
the sentiment header (band + score + confidence) is deterministic across
runs and providers instead of free-form per-model prose.

See: https://github.com/TauricResearch/TradingAgents/issues/557
See: https://github.com/TauricResearch/TradingAgents/issues/796
"""

import time
from datetime import datetime, timedelta

from langchain_core.messages import AIMessage, HumanMessage

from tradingagents.agents.schemas import SentimentReport, render_sentiment_report
from tradingagents.agents.utils.agent_utils import (
    get_instrument_context_from_state,
    get_language_instruction,
    get_news,
)
from tradingagents.agents.utils.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)
from tradingagents.dataflows.reddit import fetch_reddit_posts
from tradingagents.dataflows.stocktwits import fetch_stocktwits_messages
from tradingagents.dataflows.config import get_config
from tradingagents.mode_profiles import get_analyst_system_prompt


def _lookback_start(trade_date: str, days: int) -> str:
    return (datetime.strptime(trade_date, "%Y-%m-%d") - timedelta(days=days)).strftime("%Y-%m-%d")


def _truncate_data_block(text: str, max_chars: int = 800) -> str:
    """Cap pre-fetched source blocks so Poe/OpenAI-compatible proxies don't time out.

    Runtime evidence: sentiment prompts >~6k chars routinely hit Poe's ~180s
  limit on structured-output calls; truncating each source block keeps calls
    under that ceiling while preserving the headline signal.
    """
    text = text or ""
    if len(text) <= max_chars:
        return text
    return (
        text[:max_chars]
        + f"\n\n[... truncated {len(text) - max_chars} characters for API limits ...]"
    )


def _strip_sentiment_header(text: str) -> str:
    """Drop the standardized sentiment header if present."""
    lines = (text or "").splitlines()
    if len(lines) >= 2 and lines[0].startswith("**Overall Sentiment:**") and lines[1].startswith(
        "**Confidence:**"
    ):
        body = "\n".join(lines[2:]).lstrip()
        return body
    return text


def _stage_cfg(cfg: dict) -> dict:
    """Adaptive sentiment-stage knobs with safe defaults."""
    return {
        "enabled": bool(cfg.get("sentiment_adaptive_enabled", True)),
        "freetext_first": bool(cfg.get("sentiment_freetext_first", True)),
        "a_chars": int(cfg.get("sentiment_stage_a_max_chars", 800)),
        "b_chars": int(cfg.get("sentiment_stage_b_max_chars", 1800)),
        "a_stocktwits_limit": int(cfg.get("sentiment_stage_a_stocktwits_limit", 15)),
        "b_stocktwits_limit": int(cfg.get("sentiment_stage_b_stocktwits_limit", 40)),
        "max_stage_a_seconds": float(cfg.get("sentiment_stage_b_max_stage_a_seconds", 90)),
        "structured_prompt_max_chars": int(
            cfg.get("sentiment_structured_prompt_max_chars", 4500)
        ),
    }


def _hard_fallback_sentiment_report(
    ticker: str,
    start_date: str,
    end_date: str,
    *,
    error: Exception | None = None,
) -> str:
    """Deterministic last-resort output when every LLM path fails.

    The graph must keep moving even if the provider has a transient outage.
    """
    error_line = f"- LLM fallback error: {type(error).__name__}: {error}" if error else "- LLM fallback error: unknown"
    return "\n".join(
        [
            "**Overall Sentiment:** **Mixed** (Score: 5.0/10)",
            "**Confidence:** Low",
            "",
            f"# {ticker} — Sentiment Overlay Report",
            f"**Period:** {start_date} to {end_date}",
            "",
            "Sentiment model call failed after retries. Using a safe neutral-overlay fallback so downstream agents can continue.",
            "",
            "## Reliability Note",
            "- Data sources were fetched, but sentiment synthesis model failed.",
            error_line,
            "- Treat this sentiment block as low-confidence and rely more on market/fundamentals/news sections for this run.",
        ]
    )


def create_sentiment_analyst(llm):
    """Create a sentiment analyst node for the trading graph.

    Pre-fetches news + StockTwits + Reddit data, injects them into the
    prompt as structured blocks, and produces a deterministic sentiment
    report via structured output (with a free-text fallback for providers
    that do not support it).
    """
    structured_llm = bind_structured(llm, SentimentReport, "Sentiment Analyst")

    def _run_sentiment_pass(
        *,
        instrument_context: str,
        system_message: str,
        llm,
        structured_llm,
        structured_prompt_max_chars: int,
        freetext_first: bool = False,
    ) -> str:
        compact_prompt = [
            HumanMessage(
                content=f"{instrument_context}\n\n{system_message}".strip(),
            )
        ]
        prompt_chars = len(compact_prompt[0].content)
        if freetext_first:
            structured_for_call = None
            schema_for_call = None
        else:
            structured_for_call = (
                structured_llm if prompt_chars <= structured_prompt_max_chars else None
            )
            schema_for_call = SentimentReport if structured_for_call is not None else None
        return invoke_structured_or_freetext(
            structured_for_call,
            llm,
            compact_prompt,
            render_sentiment_report,
            "Sentiment Analyst",
            schema=schema_for_call,
        )

    def sentiment_analyst_node(state):
        ticker = state["company_of_interest"]
        end_date = state["trade_date"]
        cfg = get_config()
        stage = _stage_cfg(cfg)
        lookback = cfg.get("sentiment_lookback_days", 7)
        start_date = _lookback_start(end_date, lookback)
        instrument_context = get_instrument_context_from_state(state)

        # Pre-fetch all three sources. Each fetcher degrades gracefully and
        # returns a string (no exceptions surface from here), so the LLM
        # always sees something — either real data or a clear placeholder.
        news_raw = get_news.func(ticker, start_date, end_date)
        stocktwits_raw = fetch_stocktwits_messages(ticker, limit=stage["b_stocktwits_limit"])
        reddit_raw = fetch_reddit_posts(ticker)

        news_block = _truncate_data_block(news_raw, max_chars=stage["a_chars"])
        stocktwits_block = _truncate_data_block(stocktwits_raw, max_chars=stage["a_chars"])
        reddit_block = _truncate_data_block(reddit_raw, max_chars=stage["a_chars"])

        system_message = _build_system_message(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            lookback_days=lookback,
            news_block=news_block,
            stocktwits_block=stocktwits_block,
            reddit_block=reddit_block,
        )

        t0 = time.time()
        try:
            report_text = _run_sentiment_pass(
                instrument_context=instrument_context,
                system_message=system_message,
                llm=llm,
                structured_llm=structured_llm,
                structured_prompt_max_chars=stage["structured_prompt_max_chars"],
                freetext_first=stage["freetext_first"],
            )
        except Exception as exc:
            report_text = _hard_fallback_sentiment_report(
                ticker,
                start_date,
                end_date,
                error=exc,
            )
            return {
                "messages": [AIMessage(content=report_text)],
                "sentiment_report": report_text,
            }
        stage_a_seconds = time.time() - t0

        # Adaptive stage-B enrichment: run only when stage-A is quick enough and
        # we are on a real provider-backed LLM (not unit-test mocks).
        has_real_model = isinstance(getattr(llm, "model_name", None), str)
        if (
            stage["enabled"]
            and structured_llm is not None
            and has_real_model
            and stage_a_seconds <= stage["max_stage_a_seconds"]
        ):
            b_news = _truncate_data_block(news_raw, max_chars=stage["b_chars"])
            b_stocktwits = _truncate_data_block(stocktwits_raw, max_chars=stage["b_chars"])
            b_reddit = _truncate_data_block(reddit_raw, max_chars=stage["b_chars"])
            enrich_system_message = _build_system_message(
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
                lookback_days=lookback,
                news_block=b_news,
                stocktwits_block=b_stocktwits,
                reddit_block=b_reddit,
            ) + (
                "\n\nProduce an incremental supplement only. Focus on evidence not already"
                " covered. Do not repeat the standard sentiment header."
            )
            try:
                extra = _run_sentiment_pass(
                    instrument_context=instrument_context,
                    system_message=enrich_system_message,
                    llm=llm,
                    structured_llm=structured_llm,
                    structured_prompt_max_chars=stage["structured_prompt_max_chars"],
                    freetext_first=stage["freetext_first"],
                )
                extra_body = _strip_sentiment_header(extra)
                if extra_body and extra_body.strip():
                    report_text = (
                        f"{report_text}\n\n## Supplemental Sentiment Evidence\n\n{extra_body.strip()}"
                    )
            except Exception:
                # Keep stage-A output when enrichment fails.
                pass

        return {
            "messages": [AIMessage(content=report_text)],
            "sentiment_report": report_text,
        }

    return sentiment_analyst_node


def _build_system_message(
    *,
    ticker: str,
    start_date: str,
    end_date: str,
    lookback_days: int,
    news_block: str,
    stocktwits_block: str,
    reddit_block: str,
) -> str:
    """Assemble the sentiment-analyst system message with structured data blocks."""
    cfg = get_config()
    mode_intro = get_analyst_system_prompt("sentiment", cfg)
    return f"""{mode_intro}

You are a financial market sentiment analyst for {ticker} ({start_date} to {end_date}).

## Data sources (pre-fetched)

### News headlines — Yahoo Finance, past {lookback_days} days
Institutional framing. Fact-driven, slower-moving signal.

<start_of_news>
{news_block}
<end_of_news>

### StockTwits messages — retail-trader social platform indexed by cashtag
Fast-moving signal. Each message carries a user-labeled sentiment tag (Bullish / Bearish / no-label) plus the message body.

<start_of_stocktwits>
{stocktwits_block}
<end_of_stocktwits>

### Reddit posts — r/wallstreetbets, r/stocks, r/investing (past {lookback_days} days)
Community discussion. Engagement signal via upvote score and comment count. Subreddit character matters (r/wallstreetbets is often contrarian/exuberant; r/stocks more measured; r/investing longer-term).

<start_of_reddit>
{reddit_block}
<end_of_reddit>

## How to analyze this data (best practices)

1. **Read the StockTwits Bullish/Bearish ratio as a leading retail-sentiment signal.** A 70/30 bullish/bearish split is moderately bullish; ≥90/10 may indicate over-extension and contrarian risk; 50/50 is uncertainty. Sample size matters — base rates on the actual message count, not percentages alone.

2. **Look for cross-source divergences.** If news framing is bearish but StockTwits is overwhelmingly bullish, that mismatch is itself a signal — it can mean retail is leaning into a thesis the news flow hasn't caught up to (or vice versa, that retail is chasing while institutions are cautious).

3. **Weight Reddit posts by engagement.** A 400-upvote / 200-comment thread reflects community attention; a 3-upvote post is noise. Read the body excerpts for context — the title alone often misleads.

4. **Distinguish opinion from event.** A news headline ("Nvidia announces $500M Corning deal") is an event; a StockTwits post ("buying NVDA, this is going to moon") is opinion. Both are inputs but should be weighted differently in your conclusions.

5. **Identify recurring narrative themes.** What topic keeps coming up across sources? That's the dominant narrative driving current sentiment.

6. **Be honest about data limits.** If StockTwits returned only a handful of messages, or one or more sources returned an "<unavailable>" placeholder, the sentiment read is less robust — flag this explicitly in the `confidence` field and the narrative. If the sources are silent on a given subreddit, say so.

7. **Identify catalysts and risks** that emerge across sources — news of upcoming earnings, product launches, competitive threats, macro headlines, etc.

8. **Past sentiment is not predictive.** Frame your conclusions as signal for the trader to weigh alongside fundamentals and technicals, not as a price call.

## Output fields

Fill the following fields:

- **overall_band**: Exactly one of Bullish / Mildly Bullish / Neutral / Mixed / Mildly Bearish / Bearish. Use Mixed when sources point in clearly different directions; Neutral only when all sources are genuinely silent.
- **overall_score**: A number from 0 (maximally bearish) to 10 (maximally bullish); 5 is neutral. Keep it consistent with overall_band.
- **confidence**: low / medium / high, based on data quality and sample size.
- **narrative**: Full source-by-source breakdown, divergences, dominant narrative themes, catalysts and risks, and a markdown summary table of key sentiment signals (direction, source, supporting evidence).

If you cannot use structured output, start your markdown with this exact header shape:
**Overall Sentiment:** **Bullish/Mildly Bullish/Neutral/Mixed/Mildly Bearish/Bearish** (Score: X.X/10)
**Confidence:** Low/Medium/High

{get_language_instruction()}"""


# ---------------------------------------------------------------------------
# Backwards-compatibility shim
# ---------------------------------------------------------------------------
def create_social_media_analyst(llm):
    """Deprecated alias for :func:`create_sentiment_analyst`.

    Kept so existing code that imports ``create_social_media_analyst``
    continues to work.

    .. deprecated::
        Import :func:`create_sentiment_analyst` directly instead.
    """
    import warnings
    warnings.warn(
        "create_social_media_analyst is deprecated and will be removed in a "
        "future version. Use create_sentiment_analyst instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return create_sentiment_analyst(llm)
