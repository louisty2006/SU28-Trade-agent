"""TradingAgents Web UI (Streamlit).

A product-style interface over the existing CLI capabilities:
  - Mode toggle: short-term trading vs long-term investing (with horizon)
  - Single-ticker deep analysis (full multi-agent team), live progress
  - Recommendations / screener (long-term quant watchlist; optional deep dive)
  - Report center to browse saved runs

Run with:
    streamlit run app.py

The LLM provider / models / API keys come from your .env (same as the CLI),
so nothing extra to configure here.
"""

from __future__ import annotations

# load_dotenv must run BEFORE importing tradingagents, because DEFAULT_CONFIG
# applies TRADINGAGENTS_* env overrides at import time.
from dotenv import load_dotenv

load_dotenv()

import datetime as _dt
import logging
import threading
import time
import json
from pathlib import Path

import streamlit as st

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.dataflows.stockstats_utils import is_yf_rate_limited
from tradingagents.mode_profiles import merge_mode_into_config, mode_label

_log = logging.getLogger("tradingagents.app")

ANALYST_LABELS = {
    "market": "Market (technical)",
    "social": "Sentiment (social)",
    "news": "News / macro",
    "fundamentals": "Fundamentals",
}

REPORT_STEPS = [
    ("market_report", "Market Analyst"),
    ("sentiment_report", "Sentiment Analyst"),
    ("news_report", "News Analyst"),
    ("fundamentals_report", "Fundamentals Analyst"),
    ("investment_plan", "Research Manager"),
    ("trader_investment_plan", "Trader"),
    ("final_trade_decision", "Portfolio Manager"),
]

# Per-step estimated seconds (mixed LLM: quick=OpenRouter free, deep=Poe).
# Used for ETA display only; recalibrate after a few real runs.
STEP_ESTIMATES = {
    "market_report": 40,
    "sentiment_report": 60,        # 3 sources fetch + free-text synthesis
    "news_report": 50,
    "fundamentals_report": 50,
    "investment_plan": 45,         # Research Manager -> deep (Poe)
    "trader_investment_plan": 25,
    "final_trade_decision": 45,    # Portfolio Manager -> deep (Poe)
}
TOTAL_ESTIMATE = sum(STEP_ESTIMATES.values())


st.set_page_config(
    page_title="TradingAgents",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def build_config(mode: str, horizon: str, analysts: list[str]) -> dict:
    """Build the run config from DEFAULT_CONFIG + chosen mode/horizon."""
    cfg = dict(DEFAULT_CONFIG)
    cfg["investment_mode"] = mode
    cfg["investment_horizon"] = horizon
    return merge_mode_into_config(cfg)


def provider_summary() -> dict[str, str]:
    return {
        "provider": DEFAULT_CONFIG.get("llm_provider", "?"),
        "deep": DEFAULT_CONFIG.get("deep_think_llm", "?"),
        "quick": DEFAULT_CONFIG.get("quick_think_llm", "?"),
        "backend_url": DEFAULT_CONFIG.get("backend_url") or "(provider default)",
    }


def results_root() -> Path:
    return Path(DEFAULT_CONFIG["results_dir"])


def _console(msg: str) -> None:
    """Mirror progress to the terminal where ``streamlit run app.py`` is running."""
    ts = _dt.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] TradingAgents | {msg}"
    print(line, flush=True)
    _log.info(msg)


def _batch_cooldown_seconds() -> int:
    return int(DEFAULT_CONFIG.get("batch_analysis_cooldown_seconds", 30))


def _post_screen_cooldown_seconds() -> int:
    return int(DEFAULT_CONFIG.get("post_screen_cooldown_seconds", 60))


def _load_latest_watchlist() -> dict | None:
    """Load the newest screening watchlist.json from disk, if any."""
    screening_dir = results_root() / "screening"
    if not screening_dir.exists():
        return None
    candidates = sorted(
        screening_dir.glob("*/watchlist.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for path in candidates:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("watchlist"):
            data["_source_dir"] = str(path.parent)
            return data
    return None


def _maybe_wait_after_screening() -> None:
    """Let Yahoo Finance recover after a heavy screener run."""
    finished = st.session_state.get("screen_finished_at")
    if not finished:
        return
    elapsed = time.time() - finished
    wait = _post_screen_cooldown_seconds() - elapsed
    if wait > 0:
        _console(f"選股剛完成，等待 Yahoo 冷卻 {wait:.0f}s 後開始深度分析…")
        time.sleep(wait)


def _pending_step_label(done: set[str]) -> str:
    for key, label in REPORT_STEPS:
        if key not in done:
            return label
    return "finishing"


def run_analysis_streaming(ticker: str, date: str, mode: str, horizon: str,
                           analysts: list[str], status_box, progress_bar,
                           *, batch_pos: tuple[int, int] | None = None):
    """Run the full agent graph, updating the UI as nodes complete.

    Returns (final_state, save_path).
    """
    from tradingagents.dataflows.config import set_config
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from tradingagents.reporting import write_report_tree

    try:
        from cli.utils import detect_asset_type, normalize_ticker_symbol
        ticker = normalize_ticker_symbol(ticker)
        asset_type = detect_asset_type(ticker).value
    except Exception:
        asset_type = "stock"

    cfg = build_config(mode, horizon, analysts)
    set_config(cfg)

    batch_note = f" [{batch_pos[0]}/{batch_pos[1]}]" if batch_pos else ""
    _console(
        f"▶ Start{batch_note}: {ticker} | mode={mode} horizon={horizon} "
        f"| analysts={','.join(analysts)} | LLM={provider_summary()['quick']} "
        f"| 預計總時間 ~{TOTAL_ESTIMATE}s"
    )

    graph = TradingAgentsGraph(analysts, config=cfg, debug=False)
    instrument_context = graph.resolve_instrument_context(ticker, asset_type)
    init_state = graph.propagator.create_initial_state(
        ticker, date, asset_type=asset_type, instrument_context=instrument_context,
    )
    args = graph.propagator.get_graph_args()

    done: set[str] = set()
    prev_done: set[str] = set()
    total = len(REPORT_STEPS)
    final_state: dict = {}
    t0 = time.monotonic()
    last_done_at = t0
    step_durations: dict[str, float] = {}
    stop_heartbeat = threading.Event()

    def _heartbeat() -> None:
        while not stop_heartbeat.wait(30):
            elapsed = time.monotonic() - t0
            pending = _pending_step_label(done)
            completed = len(done)
            pending_key = next((k for k, _ in REPORT_STEPS if k not in done), None)
            pending_est = STEP_ESTIMATES.get(pending_key, 0) if pending_key else 0
            remaining_est = sum(
                STEP_ESTIMATES.get(k, 0) for k, _ in REPORT_STEPS if k not in done
            )
            _console(
                f"… still running {ticker} ({elapsed:.0f}s / 預計 {TOTAL_ESTIMATE}s) — "
                f"{completed}/{total} steps done, current: {pending} "
                f"(該步預計 {pending_est}s, 剩餘預計 ~{remaining_est}s)"
            )

    hb = threading.Thread(target=_heartbeat, daemon=True)
    hb.start()
    try:
        for chunk in graph.graph.stream(init_state, **args):
            final_state.update(chunk)
            for key, _ in REPORT_STEPS:
                if _section_value(final_state, key):
                    done.add(key)

            newly = done - prev_done
            if newly:
                now = time.monotonic()
                step_secs = now - last_done_at
                for key, label in REPORT_STEPS:
                    if key in newly:
                        step_durations[key] = step_secs
                        est = STEP_ESTIMATES.get(key, 0)
                        _console(
                            f"  ✓ {label}: 實際 {step_secs:.0f}s / 預計 {est}s "
                            f"(累計 {now - t0:.0f}s)"
                        )
                last_done_at = now
                prev_done = set(done)

            current_key = next((k for k, _ in REPORT_STEPS if k not in done), None)
            lines = []
            for key, label in REPORT_STEPS:
                est = STEP_ESTIMATES.get(key, 0)
                if key in done:
                    actual = step_durations.get(key)
                    actual_txt = f"{actual:.0f}s" if actual is not None else "—"
                    lines.append(f"✅ {label} — 實際 {actual_txt} / 預計 {est}s")
                elif key == current_key:
                    running = time.monotonic() - last_done_at
                    lines.append(f"⏳ {label} — 進行中 {running:.0f}s (預計 {est}s)")
                else:
                    lines.append(f"⏳ {label} — 預計 {est}s")
            status_box.markdown("\n\n".join(lines))
            progress_bar.progress(min(len(done) / total, 1.0))
    finally:
        stop_heartbeat.set()

    progress_bar.progress(1.0)
    elapsed = time.monotonic() - t0

    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = results_root() / "reports" / f"{_safe(ticker)}_{stamp}"
    write_report_tree(final_state, ticker, save_path)
    _console(
        f"✓ Done {ticker} in {elapsed:.0f}s "
        f"(預計 {TOTAL_ESTIMATE}s, 差 {elapsed - TOTAL_ESTIMATE:+.0f}s) → {save_path}"
    )
    return final_state, save_path


def _section_value(state: dict, key: str):
    """Pull a report-section value, accounting for debate-state nesting."""
    if key == "investment_plan":
        d = state.get("investment_debate_state") or {}
        return d.get("judge_decision") or state.get("investment_plan")
    if key == "final_trade_decision":
        d = state.get("risk_debate_state") or {}
        return d.get("judge_decision") or state.get("final_trade_decision")
    return state.get(key)


def _safe(ticker: str) -> str:
    return "".join(c if c.isalnum() or c in "-._" else "_" for c in ticker)


def render_final_state(final_state: dict):
    """Render a completed run's sections in tabs."""
    tabs = st.tabs([
        "Decision", "Analysts", "Research debate", "Trader", "Risk", "Raw",
    ])

    with tabs[0]:
        decision = _section_value(final_state, "final_trade_decision")
        if decision:
            st.markdown(decision)
        else:
            st.info("No portfolio decision produced.")

    with tabs[1]:
        for key, label in [
            ("market_report", "Market"),
            ("fundamentals_report", "Fundamentals"),
            ("news_report", "News / Macro"),
            ("sentiment_report", "Sentiment"),
        ]:
            body = final_state.get(key)
            if body:
                with st.expander(label, expanded=False):
                    st.markdown(body)

    with tabs[2]:
        debate = final_state.get("investment_debate_state") or {}
        if debate.get("bull_history"):
            with st.expander("Bull", expanded=False):
                st.markdown(debate["bull_history"])
        if debate.get("bear_history"):
            with st.expander("Bear", expanded=False):
                st.markdown(debate["bear_history"])
        if debate.get("judge_decision"):
            st.markdown("**Research Manager**")
            st.markdown(debate["judge_decision"])

    with tabs[3]:
        plan = final_state.get("trader_investment_plan")
        st.markdown(plan if plan else "_No trader plan._")

    with tabs[4]:
        risk = final_state.get("risk_debate_state") or {}
        for key, label in [
            ("aggressive_history", "Aggressive"),
            ("conservative_history", "Conservative"),
            ("neutral_history", "Neutral"),
        ]:
            if risk.get(key):
                with st.expander(label, expanded=False):
                    st.markdown(risk[key])

    with tabs[5]:
        st.json({k: (v if isinstance(v, str) else str(v)) for k, v in final_state.items()})


# --------------------------------------------------------------------------- #
# Sidebar — mode selection (the "home" control)
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.title("📈 TradingAgents")

    mode_label_choice = st.radio(
        "投資模式 / Mode",
        options=["短線 Short-term", "長線 Long-term"],
        index=0,
    )
    mode = "long_term" if mode_label_choice.startswith("長線") else "short_term"

    horizon = "3y"
    if mode == "long_term":
        horizon = st.selectbox(
            "持有期 / Horizon",
            options=["6m", "1y", "3y", "5y+"],
            index=2,
        )

    analysts = st.multiselect(
        "分析師團隊 / Analysts",
        options=list(ANALYST_LABELS.keys()),
        default=list(ANALYST_LABELS.keys()),
        format_func=lambda k: ANALYST_LABELS[k],
    )

    st.divider()
    p = provider_summary()
    st.caption("LLM 設定 (來自 .env)")
    st.markdown(
        f"- Provider: `{p['provider']}`\n"
        f"- Deep: `{p['deep']}`\n"
        f"- Quick: `{p['quick']}`"
    )
    st.caption(f"模式: {mode_label({'investment_mode': mode, 'investment_horizon': horizon})}")


st.session_state.setdefault("last_state", None)
st.session_state.setdefault("last_path", None)

# --------------------------------------------------------------------------- #
# Main tabs
# --------------------------------------------------------------------------- #
tab_home, tab_analyze, tab_screen, tab_reports = st.tabs([
    "🏠 首頁", "🔍 單股分析", "📋 推薦/選股", "📁 報告中心",
])


# ---- Home ----------------------------------------------------------------- #
with tab_home:
    st.header("Welcome")
    st.write(
        f"今日: **{_dt.date.today().isoformat()}** ｜ "
        f"目前模式: **{mode_label({'investment_mode': mode, 'investment_horizon': horizon})}**"
    )
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🔍 單股分析")
        st.write("輸入一隻股票，跑完整 multi-agent 分析（短線交易報告 / 長線投資備忘錄）。")
    with c2:
        st.subheader("📋 推薦 / 選股")
        st.write("長線：量化篩選 watchlist，並可一鍵對 Top N 跑深度分析。")
    st.info(
        "提示：左側切換短線 / 長線。LLM 與 API key 由 `.env` 控制，"
        "與 CLI 共用同一套設定。",
        icon="💡",
    )


# ---- Single-stock analysis ------------------------------------------------ #
with tab_analyze:
    st.header("單股深度分析")
    col1, col2 = st.columns([2, 1])
    with col1:
        ticker = st.text_input("股票代號 / Ticker", value="NVDA",
                               help="例如 NVDA、AAPL、0700.HK、BTC-USD")
    with col2:
        date = st.date_input("分析日期", value=_dt.date.today()).isoformat()

    run = st.button("▶️ 開始分析", type="primary", disabled=not analysts)
    if not analysts:
        st.warning("請在左側至少選一個分析師。")

    if run and ticker.strip():
        st.caption(
            f"模式 {mode_label({'investment_mode': mode, 'investment_horizon': horizon})} ｜ "
            f"模型 deep=`{provider_summary()['deep']}` quick=`{provider_summary()['quick']}`"
        )
        progress = st.progress(0.0)
        status = st.empty()
        with st.spinner(f"分析 {ticker} 中…（多 agent 流程，需數分鐘；終端機每 30s 印進度）"):
            try:
                final_state, save_path = run_analysis_streaming(
                    ticker.strip(), date, mode, horizon, analysts, status, progress,
                )
                st.session_state["last_state"] = final_state
                st.session_state["last_path"] = str(save_path)
                st.success(f"完成！報告已存至 {save_path}")
            except Exception as exc:
                st.error(f"分析失敗：{exc}")
                _console(f"✗ 分析失敗 {ticker}: {exc}")
                st.exception(exc)

    if st.session_state.get("last_state"):
        st.divider()
        st.subheader("分析結果")
        if st.session_state.get("last_path"):
            st.caption(f"報告路徑：`{st.session_state['last_path']}`")
        render_final_state(st.session_state["last_state"])


# ---- Screener / recommendations ------------------------------------------- #
with tab_screen:
    st.header("長線量化選股 / Recommendations")
    if mode != "long_term":
        st.info("選股目前針對長線。左側切換到「長線 Long-term」後使用，或直接在下方執行。",
                icon="ℹ️")

    UNIVERSE_CHOICES = {
        "sp500": "S&P 500（大型股）",
        "nasdaq100": "Nasdaq 100（大型科技）",
        "sp400": "S&P MidCap 400（中型股）",
        "sp600": "S&P SmallCap 600（小型股 · 潛力股）",
        "all_us": "全美股 NYSE/NASDAQ/AMEX（~6000+，慢）",
    }
    c1, c2, c3 = st.columns(3)
    with c1:
        universe = st.selectbox(
            "股票池 / Universe",
            list(UNIVERSE_CHOICES.keys()),
            index=0,
            format_func=lambda k: UNIVERSE_CHOICES[k],
        )
    with c2:
        top_n = st.number_input("Top N", min_value=5, max_value=100, value=20, step=5)
    with c3:
        scr_horizon = st.selectbox("Horizon", ["6m", "1y", "3y", "5y+"], index=2)

    big = universe in ("sp400", "sp600", "all_us")
    max_tickers = None
    if big:
        max_tickers = st.slider(
            "最多掃描股票數（控制速度 / 限流）",
            min_value=100, max_value=6000, value=500, step=100,
        )
        st.caption(
            "⚠️ 全美股逐隻抓 yfinance 很慢且可能被限流。建議先用較小上限試跑，"
            "小型股池（S&P 600）通常是潛力股的好起點。"
        )

    if st.button("🔎 執行選股", type="primary"):
        from tradingagents.dataflows.config import set_config
        from tradingagents.screening.runner import run_screen

        stamp = _dt.datetime.now().strftime("%Y-%m-%d")
        out = results_root() / "screening" / f"{stamp}_{universe}_{scr_horizon}"
        scr_cfg = merge_mode_into_config({
            **DEFAULT_CONFIG,
            "investment_mode": "long_term",
            "investment_horizon": scr_horizon,
            "screener_universe": universe,
            "screener_top_n": int(top_n),
        })
        set_config(scr_cfg)
        prog = st.progress(0.0)
        prog_txt = st.empty()
        status_txt = st.empty()

        def _cb(done: int, total: int):
            prog.progress(min(done / total, 1.0) if total else 1.0)
            prog_txt.caption(f"已掃描 {done}/{total}…")
            if done == 1 or done == total or done % max(1, total // 10) == 0:
                _console(f"選股進度 {done}/{total}")

        def _status(msg: str):
            status_txt.caption(msg)
            _console(msg)

        with st.spinner(f"篩選 {UNIVERSE_CHOICES[universe]} 中…（抓 yfinance 基本面）"):
            _console(f"▶ 選股開始: universe={universe} top={top_n}")
            try:
                result = run_screen(
                    universe=universe,
                    top_n=int(top_n),
                    output_dir=out,
                    max_tickers=max_tickers,
                    progress_cb=_cb,
                    status_cb=_status,
                )
                st.session_state["screen_result"] = result
                st.session_state["screen_out"] = str(out)
                st.session_state["screen_finished_at"] = time.time()
                failed = result.get("failed") or []
                st.success(
                    f"完成！掃描 {result.get('total_scanned', '?')} 隻，"
                    f"通過篩選 {result['total_scored']} 隻，存至 {out}"
                )
                if failed:
                    st.warning(
                        f"重試 {result.get('retry_rounds', 0)} 輪後仍有 "
                        f"{len(failed)} 隻無法取得資料：{', '.join(failed[:30])}"
                        + ("…" if len(failed) > 30 else "")
                    )
                _console(
                    f"✓ 選股完成: {result['total_scored']} 隻通過"
                    + (f", {len(failed)} 隻失敗" if failed else "")
                    + f" → {out}"
                )
            except Exception as exc:
                st.error(f"選股失敗：{exc}")

    # Fall back to the most recent watchlist on disk so the deep-analysis
    # section (and its button) does not vanish after an app restart or a
    # screening run that returned zero rows in-session.
    screen_result = st.session_state.get("screen_result")
    if not screen_result:
        screen_result = _load_latest_watchlist()
        if screen_result:
            st.session_state["screen_result"] = screen_result
            st.session_state.setdefault("screen_out", screen_result.get("_source_dir", ""))
            st.caption("（已載入最近一次選股結果）")

    if screen_result:
        watchlist = screen_result.get("watchlist", [])
        if watchlist:
            cols = ["ticker", "sector", "quality_score", "growth_score",
                    "value_score", "composite_score", "hook"]
            rows = [{c: row.get(c, "") for c in cols} for row in watchlist]
            st.dataframe(rows, width="stretch", hide_index=True)
            st.caption(f"輸出資料夾：`{st.session_state.get('screen_out','')}`")

            # --- Chain selected names into the full multi-agent analysis ---- #
            st.divider()
            st.subheader("➡️ 對選出股票跑完整分析報告")
            st.caption(
                "選股只給量化分數；按此對選定股票跑與「單股分析」一樣的完整 "
                "multi-agent 報告（每隻數分鐘，逐隻順序執行）。"
                " **建議一次不超過 3–5 檔**；選股後會自動等待 Yahoo 冷卻。"
                " **終端機**（執行 `streamlit run app.py` 的視窗）會每 30 秒印出進度。"
            )
            wl_tickers = [r["ticker"] for r in watchlist]
            picks = st.multiselect(
                "選擇要深度分析的股票",
                options=wl_tickers,
                default=wl_tickers[: min(3, len(wl_tickers))],
                help="預設選前 3 名；可自行增減。",
            )
            force_all = st.checkbox(
                "重跑全部（取消勾選時，再按只會重跑未成功的檔）",
                value=False,
            )
            if st.button("📑 產生完整分析報告", type="primary", disabled=not picks):
                if not analysts:
                    st.warning("請在左側至少選一個分析師。")
                else:
                    today = _dt.date.today().isoformat()
                    # Prefer the horizon the watchlist was screened with so a
                    # loaded-from-disk run stays consistent with its selection.
                    run_horizon = screen_result.get("horizon", scr_horizon)
                    overall = st.progress(0.0)
                    _maybe_wait_after_screening()
                    cooldown = _batch_cooldown_seconds()

                    # results keyed by ticker so a retry pass overwrites cleanly.
                    results: dict[str, dict] = {}

                    # Carry over prior successes so a re-press only reruns the
                    # not-yet-successful tickers (unless "重跑全部" is checked).
                    prior = {
                        r["ticker"]: r
                        for r in st.session_state.get("batch_summary", [])
                        if r.get("report") not in (None, "", "FAILED")
                    }
                    if force_all:
                        to_run = list(picks)
                    else:
                        for tk in picks:
                            if tk in prior:
                                results[tk] = prior[tk]
                        to_run = [tk for tk in picks if tk not in prior]
                    if not to_run:
                        st.info("選定的股票本次都已成功分析過；如需重跑請勾選「重跑全部」。")
                        st.stop()

                    def _run_pass(tickers: list[str], pass_label: str,
                                  done_offset: int, grand_total: int) -> list[str]:
                        """Run one sequential pass; return the tickers that failed."""
                        failed: list[str] = []
                        for j, tk in enumerate(tickers):
                            st.markdown(f"**{tk}** ({pass_label} {j + 1}/{len(tickers)})")
                            per_status = st.empty()
                            per_prog = st.progress(0.0)
                            try:
                                fs, sp = run_analysis_streaming(
                                    tk, today, "long_term", run_horizon,
                                    analysts, per_status, per_prog,
                                    batch_pos=(j + 1, len(tickers)),
                                )
                                decision = _section_value(fs, "final_trade_decision") or ""
                                results[tk] = {"ticker": tk, "report": str(sp),
                                               "decision_excerpt": decision[:160]}
                                st.success(f"{tk} 完成 → {sp}")
                            except Exception as exc:
                                failed.append(tk)
                                results[tk] = {"ticker": tk, "report": "FAILED",
                                               "decision_excerpt": str(exc)[:160]}
                                st.error(f"{tk} 暫時失敗（稍後重試）：{exc}")
                                _console(f"✗ {pass_label} 失敗 {tk}: {exc}")
                            done_offset += 1
                            overall.progress(min(done_offset / grand_total, 1.0))
                            if j + 1 < len(tickers):
                                _console(f"冷卻 {cooldown}s 後開始下一檔…")
                                time.sleep(cooldown)
                        return failed

                    # Pass 1: run everything; record failures, don't block.
                    grand_total = len(to_run)
                    _console(f"▶ 批次深度分析開始（第一輪）: {len(to_run)} 檔 — {', '.join(to_run)}")
                    failed = _run_pass(to_run, "第一輪", 0, grand_total)

                    # Retry passes: come back to the ones that failed.
                    max_retry_passes = 2
                    pass_num = 1
                    while failed and pass_num <= max_retry_passes:
                        wait = 90
                        _console(
                            f"第一輪有 {len(failed)} 檔失敗：{', '.join(failed)}。"
                            f"等待 {wait}s 後開始第 {pass_num + 1} 輪重試…"
                        )
                        st.info(
                            f"等待 {wait}s 後重試失敗的 {len(failed)} 檔："
                            f"{', '.join(failed)}"
                        )
                        time.sleep(wait)
                        grand_total += len(failed)
                        retry_list = failed
                        failed = _run_pass(
                            retry_list, f"第{pass_num + 1}輪重試",
                            grand_total - len(retry_list), grand_total,
                        )
                        pass_num += 1

                    overall.progress(1.0)
                    summary_rows = [results[tk] for tk in picks]
                    st.session_state["batch_summary"] = summary_rows
                    ok = sum(1 for r in summary_rows if r["report"] != "FAILED")
                    _console(
                        f"✓ 批次完成：成功 {ok}/{len(picks)}"
                        + (f"，仍失敗 {', '.join(failed)}" if failed else "")
                    )
                    if failed:
                        st.warning(
                            f"完成 {ok}/{len(picks)} 檔。仍失敗：{', '.join(failed)}。"
                            "可稍後再按一次本鍵，只會重跑失敗的檔。"
                        )
                    else:
                        st.success("全部完成！報告已存,可到「📁 報告中心」逐份查看。")

            if st.session_state.get("batch_summary"):
                st.markdown("**本次批量分析結果**")
                st.dataframe(st.session_state["batch_summary"],
                             width="stretch", hide_index=True)


# ---- Report center -------------------------------------------------------- #
with tab_reports:
    st.header("報告中心")
    reports_dir = results_root() / "reports"
    screening_dir = results_root() / "screening"

    st.subheader("深度分析報告")
    if reports_dir.exists():
        runs = sorted(reports_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if runs:
            chosen = st.selectbox("選擇報告", runs, format_func=lambda p: p.name)
            complete = chosen / "complete_report.md"
            memo = chosen / "investment_memo.md"
            scorecard = chosen / "scorecard.md"
            for label, f in [("完整報告", complete), ("投資備忘錄", memo), ("評分卡", scorecard)]:
                if f.exists():
                    with st.expander(label, expanded=(f == complete)):
                        st.markdown(f.read_text(encoding="utf-8"))
        else:
            st.write("尚無報告。先到「單股分析」跑一隻。")
    else:
        st.write("尚無報告資料夾。")

    st.subheader("選股 watchlist")
    if screening_dir.exists():
        screens = sorted(screening_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if screens:
            chosen_s = st.selectbox("選擇 watchlist", screens, format_func=lambda p: p.name)
            md = chosen_s / "watchlist.md"
            if md.exists():
                st.markdown(md.read_text(encoding="utf-8"))
        else:
            st.write("尚無 watchlist。")
    else:
        st.write("尚無選股資料夾。")
