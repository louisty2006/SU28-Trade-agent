# SU28 Trade Agent — MVP v1.0

Multi-agent stock analysis with a Streamlit UI, short/long-term modes, stock screening, and Traditional Chinese reports. Built on [TradingAgents](https://github.com/TauricResearch/TradingAgents) (Tauric Research).

> Research and education only. **Not financial advice.** LLM output is non-deterministic — verify all numbers before acting.

---

## What it does

A team of LLM agents analyses a stock the way a trading desk would, then writes a report:

```
Analysts (market · sentiment · news · fundamentals)
        ↓
Research debate (bull vs bear → manager)
        ↓
Trader → Risk debate (aggressive · neutral · conservative)
        ↓
Portfolio Manager → final decision (Buy / Hold / Sell)
```

Output is saved as Markdown (a Traditional Chinese investment memo, a scorecard, and per-agent reports).

---

## Quick start

```bash
git clone git@github.com:louisty2006/SU28-Trade-agent.git
cd SU28-Trade-agent

python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[ui]"

cp .env.example .env          # then add your Poe key (see below)
streamlit run app.py          # open http://localhost:8501
```

Progress (per-step timing + ETA) prints in the **terminal** where Streamlit runs, not only the browser.

Full setup, troubleshooting, and report structure: **[MVP_v1.0.md](MVP_v1.0.md)**.

---

## Configuration (`.env`)

MVP v1.0 default — everything on Poe (one key, no rate-limit issues):

```bash
OPENAI_COMPATIBLE_API_KEY=sk-poe-xxxxxxxx      # https://poe.com/api/keys

TRADINGAGENTS_LLM_PROVIDER=openai_compatible
TRADINGAGENTS_LLM_BACKEND_URL=https://api.poe.com/v1
TRADINGAGENTS_QUICK_THINK_LLM=gpt-5-nano       # high-volume worker (~$0.05/$0.40 per 1M)
TRADINGAGENTS_DEEP_THINK_LLM=gpt-5-mini        # 2 calls/run (managers, ~87% finance reasoning)

TRADINGAGENTS_MAX_DEBATE_ROUNDS=1
TRADINGAGENTS_MAX_RISK_ROUNDS=1
TRADINGAGENTS_SENTIMENT_FREETEXT_FIRST=true
TRADINGAGENTS_OUTPUT_LANGUAGE=Traditional Chinese
```

Optional: `FRED_API_KEY` for macro data in long-term mode ([free key](https://fred.stlouisfed.org/docs/api/api_key.html)).

---

## Two LLM roles

The graph uses two models. **Quick** does most of the work; **deep** runs only twice per ticker.

| Role | Used by | Calls/ticker |
|------|---------|--------------|
| **Quick** | 4 analysts · research debate · trader · risk debate | ~13–16 |
| **Deep** | Research Manager · Portfolio Manager | 2 |

Putting the cheap model on **quick** is where you save money.

---

## Model choices

All prices are per 1M tokens. "Per ticker" assumes ~80k input + ~10k output across the whole run.

### Recommended (verified)

| Setup | Quick | Deep | ~Cost/ticker | 429 risk | Notes |
|-------|-------|------|-------------|----------|-------|
| **Poe all-in-one** (default) | `gpt-5-nano` | `gpt-5-mini` | **$0.02–0.08** | None | One key, OpenAI tool-calling, best value |
| Previous MVP | `gpt-4o-mini` | `claude-haiku-4.5` | $0.05–0.15 | None | Still works; weaker finance reasoning on deep |
| OpenRouter + Poe | `google/gemini-2.5-flash-lite` ($0.10/$0.40) | `gpt-5-mini` (Poe) | $0.03–0.08 | None | Cheapest stable; two providers |
| Premium | `claude-sonnet` | `claude-opus` | $1–3+ | None | Best quality, expensive |

### Avoid

| Setup | Why |
|-------|-----|
| OpenRouter **`:free`** models | HTTP **429** during tool-calling; Market Analyst stalls then fails |
| Poe **Gemini Flash** as quick | Tool-calling returns `None` on Poe — breaks Market/News/Fundamentals |
| Sonnet/Opus as **quick** | Works but burns budget fast (quick = ~15 calls/run) |

### Poe vs OpenRouter (same model)

Poe is ~7–15% cheaper for identical OpenAI/Anthropic models, but the difference is fractions of a cent per ticker. Pick by **reliability**, not price: Poe = one provider + zero 429; OpenRouter = widest catalog + native OpenAI tool-calling.

---

## Token & cost prediction

Per ticker, full run (4 analysts, 1 debate round each):

| Item | Estimate |
|------|----------|
| LLM calls | ~15–18 |
| Total tokens | ~60k–120k (mostly input; later agents re-read earlier reports) |
| Deep-model share | ~15k–30k tokens (2 calls) |
| Time | ~3–5 min (verified LYFT: **192s**) |
| Cost (Poe MVP) | **$0.02–0.08** |
| Cost (OpenRouter flash-lite quick) | **$0.03–0.08** |

Rough scaling: a 20-stock batch on the Poe MVP config ≈ **$0.50–1.50 total**.

> Costs grow with debate rounds and number of analysts. Each extra debate round adds several quick calls.

---

## Usage

**Streamlit UI** (recommended):
```bash
streamlit run app.py
```
Sidebar → pick mode/horizon/analysts → 選股 tab (screen) → 深度分析 tab (full report) → 報告 tab (browse).

**CLI**:
```bash
tradingagents                                   # interactive
tradingagents analyze --mode long_term --horizon 3y
tradingagents screen --universe sp500 --top 20 --analyze-top 5
```

**Python**:
```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

ta = TradingAgentsGraph(config=DEFAULT_CONFIG.copy())
_, decision = ta.propagate("NVDA", "2026-01-15")
print(decision)
```

---

## Markets

Any market Yahoo Finance covers, via exchange-suffixed tickers:

- US: `AAPL`, `SPY` · HK: `0700.HK` · Tokyo: `7203.T` · London: `AZN.L`
- India: `RELIANCE.NS` · Canada: `.TO` · Australia: `.AX` · China A: `.SS` / `.SZ`
- Crypto: `BTC-USD`, `ETH-USD`

---

## Data sources (no extra keys)

| Source | Used for |
|--------|----------|
| yfinance | Price, fundamentals, news |
| Arctic Shift | Reddit sentiment (no OAuth) |
| StockTwits | Retail sentiment |
| FRED | Macro (long-term; needs `FRED_API_KEY`) |

SSL on macOS is fixed via `certifi` ([`http_utils.py`](tradingagents/dataflows/http_utils.py)).

---

## Reports

Saved to `~/.tradingagents/logs/reports/{TICKER}_{timestamp}/`:

| File | Content |
|------|---------|
| `investment_memo.md` | **Main read** — Traditional Chinese memo |
| `scorecard.md` | Quality / growth / value scores |
| `complete_report.md` | Full pipeline in one file |
| `1_analysts/` … `5_portfolio/` | Per-agent raw output |

---

## Tests

```bash
pytest tests/ -q     # 516+ tests
```

---

## Citation

```
@misc{xiao2025tradingagentsmultiagentsllmfinancial,
      title={TradingAgents: Multi-Agents LLM Financial Trading Framework},
      author={Yijia Xiao and Edward Sun and Di Luo and Wei Wang},
      year={2025}, eprint={2412.20138}, archivePrefix={arXiv},
      primaryClass={q-fin.TR}, url={https://arxiv.org/abs/2412.20138},
}
```
