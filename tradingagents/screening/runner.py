"""Run quantitative long-term stock screen."""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

from tradingagents.dataflows.fundamental_analytics import compute_trend_metrics
from tradingagents.dataflows.config import get_config
from tradingagents.screening.scorer import passes_risk_filters, score_metrics
from tradingagents.screening.universe import load_universe

_ScoreStatus = Literal["scored", "filtered", "failed"]


def _score_one(ticker: str, horizon: str = "3y") -> tuple[_ScoreStatus, dict[str, Any] | None]:
    """Fetch + filter + score a single ticker.

    Returns ``("scored", row)`` on success, ``("filtered", None)`` when data
    was fetched but the ticker fails risk filters, or ``("failed", None)`` when
    yfinance could not return usable data (rate limit / network).
    """
    try:
        metrics = compute_trend_metrics(ticker)
        if not passes_risk_filters(metrics):
            return "filtered", None
        return "scored", {**metrics, **score_metrics(metrics, horizon=horizon)}
    except Exception:
        return "failed", None


def _run_pass(
    tickers: list[str],
    horizon: str,
    max_workers: int,
    progress_cb: Callable[[int, int], None] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Scan ``tickers`` once; return scored rows and tickers that failed to fetch."""
    scored: list[dict[str, Any]] = []
    failed: list[str] = []
    total = len(tickers)
    done = 0

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_score_one, t, horizon): t for t in tickers}
        for fut in as_completed(futures):
            done += 1
            ticker = futures[fut]
            status, row = fut.result()
            if status == "scored" and row is not None:
                scored.append(row)
            elif status == "failed":
                failed.append(ticker)
            if progress_cb is not None:
                progress_cb(done, total)

    return scored, failed


def run_screen(
    universe: str = "sp500",
    top_n: int = 20,
    universe_file: str | Path | None = None,
    output_dir: str | Path | None = None,
    max_tickers: int | None = None,
    max_workers: int | None = None,
    progress_cb: Callable[[int, int], None] | None = None,
    status_cb: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Score universe and write watchlist JSON + markdown.

    ``max_tickers`` caps how many symbols are fetched (useful for huge universes
    like ``all_us``). yfinance calls are IO-bound, so they run on a small thread
    pool (``max_workers``); ``progress_cb(done, total)`` is invoked as results
    arrive so callers (e.g. the UI) can render a progress bar.

    Tickers that fail to fetch (rate limit / empty .info) are retried after a
    cooldown until they succeed or ``screener_max_retry_rounds`` is exhausted.
    Only then are they listed in ``failed``.
    """
    cfg = get_config()
    if max_workers is None:
        max_workers = int(cfg.get("screener_max_workers", 2))
    max_workers = max(1, min(max_workers, 8))
    max_retry_rounds = int(cfg.get("screener_max_retry_rounds", 15))
    retry_cooldown = float(cfg.get("screener_retry_cooldown_seconds", 60))
    horizon = cfg.get("investment_horizon", "3y")
    tickers = load_universe(universe, universe_file)
    if max_tickers:
        tickers = tickers[:max_tickers]

    rows: list[dict[str, Any]] = []
    total = len(tickers)
    pending = list(tickers)
    truly_failed: list[str] = []
    retry_round = 0

    while pending:
        scored, failed = _run_pass(pending, horizon, max_workers, progress_cb)
        rows.extend(scored)

        if not failed:
            break

        retry_round += 1
        if retry_round > max_retry_rounds:
            truly_failed = failed
            msg = (
                f"重試 {max_retry_rounds} 輪後仍有 {len(failed)} 隻無法取得資料："
                f"{', '.join(failed[:20])}"
                + ("…" if len(failed) > 20 else "")
            )
            if status_cb:
                status_cb(msg)
            break

        msg = (
            f"第 {retry_round} 輪重試：{len(failed)} 隻尚未取得資料，"
            f"冷卻 {retry_cooldown:.0f}s 後再試…"
        )
        if status_cb:
            status_cb(msg)
        time.sleep(retry_cooldown)
        pending = failed

    rows.sort(key=lambda r: r.get("composite_score", 0), reverse=True)
    top = rows[:top_n]

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "universe": universe if not universe_file else str(universe_file),
        "total_scanned": total,
        "total_scored": len(rows),
        "total_failed": len(truly_failed),
        "retry_rounds": retry_round,
        "top_n": top_n,
        "horizon": horizon,
        "watchlist": top,
        "failed": truly_failed,
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
            f"Horizon: {horizon}",
            f"Scored: {result['total_scored']} | Failed after retries: {result['total_failed']}",
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
        if truly_failed:
            lines.extend([
                "",
                "## Failed tickers (data unavailable after retries)",
                "",
                ", ".join(truly_failed),
            ])
        (out / "watchlist.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    return result
