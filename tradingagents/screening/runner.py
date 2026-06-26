"""Run quantitative long-term stock screen."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from tradingagents.dataflows.fundamental_analytics import compute_trend_metrics
from tradingagents.screening.scorer import passes_risk_filters, score_metrics
from tradingagents.screening.universe import load_universe


def _score_one(ticker: str) -> dict[str, Any] | None:
    """Fetch + filter + score a single ticker; fail-open to None."""
    try:
        metrics = compute_trend_metrics(ticker)
        if not passes_risk_filters(metrics):
            return None
        return {**metrics, **score_metrics(metrics)}
    except Exception:
        return None


def run_screen(
    universe: str = "sp500",
    top_n: int = 20,
    universe_file: str | Path | None = None,
    output_dir: str | Path | None = None,
    max_tickers: int | None = None,
    max_workers: int = 8,
    progress_cb: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    """Score universe and write watchlist JSON + markdown.

    ``max_tickers`` caps how many symbols are fetched (useful for huge universes
    like ``all_us``). yfinance calls are IO-bound, so they run on a small thread
    pool (``max_workers``); ``progress_cb(done, total)`` is invoked as results
    arrive so callers (e.g. the UI) can render a progress bar.
    """
    tickers = load_universe(universe, universe_file)
    if max_tickers:
        tickers = tickers[:max_tickers]

    rows: list[dict[str, Any]] = []
    total = len(tickers)
    done = 0

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_score_one, t): t for t in tickers}
        for fut in as_completed(futures):
            done += 1
            row = fut.result()
            if row is not None:
                rows.append(row)
            if progress_cb is not None:
                progress_cb(done, total)

    rows.sort(key=lambda r: r.get("composite_score", 0), reverse=True)
    top = rows[:top_n]

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "universe": universe if not universe_file else str(universe_file),
        "total_scanned": total,
        "total_scored": len(rows),
        "top_n": top_n,
        "watchlist": top,
    }

    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "watchlist.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        lines = [
            f"# Watchlist — {universe}",
            "",
            f"Generated: {result['generated_at']}",
            "",
            "| Rank | Ticker | Sector | Quality | Growth | Value | Composite | Hook |",
            "|---:|---|---|---:|---:|---:|---:|---|",
        ]
        for i, row in enumerate(top, 1):
            lines.append(
                f"| {i} | {row['ticker']} | {row.get('sector', '')} | "
                f"{row.get('quality_score', '')} | {row.get('growth_score', '')} | "
                f"{row.get('value_score', '')} | {row.get('composite_score', '')} | "
                f"{row.get('hook', '')} |"
            )
        (out / "watchlist.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    return result
