"""Reusable report-tree writer shared by the CLI and the programmatic API.

Writes a run's per-section markdown (analysts, research, trading, risk,
portfolio) plus a consolidated ``complete_report.md`` under ``save_path``. The
CLI and ``TradingAgentsGraph.save_reports`` both call this, so a headless / API
run produces the same on-disk report tree a CLI run does.
"""

from datetime import datetime
from pathlib import Path

from tradingagents.dataflows.config import get_config
from tradingagents.mode_profiles import is_long_term, mode_label


def _portfolio_decision_text(final_state: dict) -> str:
    risk = final_state.get("risk_debate_state") or {}
    return risk.get("judge_decision") or final_state.get("final_trade_decision") or ""


def write_investment_memo(final_state: dict, ticker: str, save_path: Path) -> Path | None:
    """Write long-term investment memo markdown; return path or None if not applicable."""
    if not is_long_term():
        return None
    decision = _portfolio_decision_text(final_state)
    if not decision:
        return None

    cfg = get_config()
    horizon = cfg.get("investment_horizon", "3y")
    sections = [
        f"# Investment Memo: {ticker}",
        "",
        f"**Mode**: {mode_label(cfg)} | **Horizon**: {horizon}",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Executive Summary",
        "",
        decision,
        "",
    ]

    analyst_blocks = [
        ("Business Quality & Analyst Inputs", "fundamentals_report"),
        ("Market & Technical Context", "market_report"),
        ("Macro & News", "news_report"),
        ("Sentiment Overlay", "sentiment_report"),
    ]
    for title, key in analyst_blocks:
        body = final_state.get(key)
        if body:
            sections.extend([f"## {title}", "", body, ""])

    if final_state.get("investment_plan"):
        sections.extend(["## Research Plan", "", final_state["investment_plan"], ""])
    if final_state.get("trader_investment_plan"):
        sections.extend(["## Accumulation / Action Plan", "", final_state["trader_investment_plan"], ""])

    sections.extend([
        "## Catalysts & Monitoring",
        "",
        "_Review analyst reports above for catalysts; set rebalance triggers aligned with your horizon._",
        "",
        "## Bear Case & Invalidation",
        "",
        "_See Portfolio Manager decision for invalidation triggers when provided._",
    ])

    path = save_path / "investment_memo.md"
    path.write_text("\n".join(sections), encoding="utf-8")
    return path


def write_scorecard(final_state: dict, ticker: str, save_path: Path) -> Path | None:
    """Write a one-page scorecard for long-term mode using screener metrics when available."""
    if not is_long_term():
        return None
    try:
        from tradingagents.dataflows.fundamental_analytics import compute_trend_metrics
        from tradingagents.screening.scorer import score_metrics

        metrics = compute_trend_metrics(ticker)
        scores = score_metrics(metrics)
    except Exception:
        return None

    lines = [
        f"# Scorecard: {ticker}",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Quality | {scores.get('quality_score', 'N/A')}/10 |",
        f"| Growth | {scores.get('growth_score', 'N/A')}/10 |",
        f"| Value | {scores.get('value_score', 'N/A')}/10 |",
        f"| Composite | {scores.get('composite_score', 'N/A')}/10 |",
        f"| ROE | {metrics.get('roe', 'N/A')} |",
        f"| Profit Margin | {metrics.get('profit_margin', 'N/A')} |",
        f"| PEG | {metrics.get('peg', 'N/A')} |",
        f"| FCF Yield | {metrics.get('fcf_yield', 'N/A')} |",
        "",
        f"**Hook**: {scores.get('hook', '')}",
    ]
    path = save_path / "scorecard.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_report_tree(final_state: dict, ticker: str, save_path) -> Path:
    """Save a completed run's reports to ``save_path``; return the complete-report path."""
    save_path = Path(save_path)
    save_path.mkdir(parents=True, exist_ok=True)
    sections = []
    mode_hdr = f"**Investment Mode**: {mode_label()}\n\n" if is_long_term() else ""

    # 1. Analysts
    analysts_dir = save_path / "1_analysts"
    analyst_parts = []
    if final_state.get("market_report"):
        analysts_dir.mkdir(exist_ok=True)
        (analysts_dir / "market.md").write_text(final_state["market_report"], encoding="utf-8")
        analyst_parts.append(("Market Analyst", final_state["market_report"]))
    if final_state.get("sentiment_report"):
        analysts_dir.mkdir(exist_ok=True)
        (analysts_dir / "sentiment.md").write_text(final_state["sentiment_report"], encoding="utf-8")
        analyst_parts.append(("Sentiment Analyst", final_state["sentiment_report"]))
    if final_state.get("news_report"):
        analysts_dir.mkdir(exist_ok=True)
        (analysts_dir / "news.md").write_text(final_state["news_report"], encoding="utf-8")
        analyst_parts.append(("News Analyst", final_state["news_report"]))
    if final_state.get("fundamentals_report"):
        analysts_dir.mkdir(exist_ok=True)
        (analysts_dir / "fundamentals.md").write_text(final_state["fundamentals_report"], encoding="utf-8")
        analyst_parts.append(("Fundamentals Analyst", final_state["fundamentals_report"]))
    if analyst_parts:
        content = "\n\n".join(f"### {name}\n{text}" for name, text in analyst_parts)
        sections.append(f"## I. Analyst Team Reports\n\n{content}")

    # 2. Research
    if final_state.get("investment_debate_state"):
        research_dir = save_path / "2_research"
        debate = final_state["investment_debate_state"]
        research_parts = []
        if debate.get("bull_history"):
            research_dir.mkdir(exist_ok=True)
            (research_dir / "bull.md").write_text(debate["bull_history"], encoding="utf-8")
            research_parts.append(("Bull Researcher", debate["bull_history"]))
        if debate.get("bear_history"):
            research_dir.mkdir(exist_ok=True)
            (research_dir / "bear.md").write_text(debate["bear_history"], encoding="utf-8")
            research_parts.append(("Bear Researcher", debate["bear_history"]))
        if debate.get("judge_decision"):
            research_dir.mkdir(exist_ok=True)
            (research_dir / "manager.md").write_text(debate["judge_decision"], encoding="utf-8")
            research_parts.append(("Research Manager", debate["judge_decision"]))
        if research_parts:
            content = "\n\n".join(f"### {name}\n{text}" for name, text in research_parts)
            sections.append(f"## II. Research Team Decision\n\n{content}")

    # 3. Trading
    if final_state.get("trader_investment_plan"):
        trading_dir = save_path / "3_trading"
        trading_dir.mkdir(exist_ok=True)
        (trading_dir / "trader.md").write_text(final_state["trader_investment_plan"], encoding="utf-8")
        sections.append(f"## III. Trading Team Plan\n\n### Trader\n{final_state['trader_investment_plan']}")

    # 4. Risk Management
    if final_state.get("risk_debate_state"):
        risk_dir = save_path / "4_risk"
        risk = final_state["risk_debate_state"]
        risk_parts = []
        if risk.get("aggressive_history"):
            risk_dir.mkdir(exist_ok=True)
            (risk_dir / "aggressive.md").write_text(risk["aggressive_history"], encoding="utf-8")
            risk_parts.append(("Aggressive Analyst", risk["aggressive_history"]))
        if risk.get("conservative_history"):
            risk_dir.mkdir(exist_ok=True)
            (risk_dir / "conservative.md").write_text(risk["conservative_history"], encoding="utf-8")
            risk_parts.append(("Conservative Analyst", risk["conservative_history"]))
        if risk.get("neutral_history"):
            risk_dir.mkdir(exist_ok=True)
            (risk_dir / "neutral.md").write_text(risk["neutral_history"], encoding="utf-8")
            risk_parts.append(("Neutral Analyst", risk["neutral_history"]))
        if risk_parts:
            content = "\n\n".join(f"### {name}\n{text}" for name, text in risk_parts)
            sections.append(f"## IV. Risk Management Team Decision\n\n{content}")

        # 5. Portfolio Manager
        if risk.get("judge_decision"):
            portfolio_dir = save_path / "5_portfolio"
            portfolio_dir.mkdir(exist_ok=True)
            (portfolio_dir / "decision.md").write_text(risk["judge_decision"], encoding="utf-8")
            sections.append(f"## V. Portfolio Manager Decision\n\n### Portfolio Manager\n{risk['judge_decision']}")

    # Write consolidated report
    header = (
        f"# Trading Analysis Report: {ticker}\n\n"
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"{mode_hdr}"
    )
    (save_path / "complete_report.md").write_text(header + "\n\n".join(sections), encoding="utf-8")

    write_investment_memo(final_state, ticker, save_path)
    write_scorecard(final_state, ticker, save_path)

    return save_path / "complete_report.md"
