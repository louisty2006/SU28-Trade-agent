# SU28 Trade Agent — MVP v1.0

Multi-agent stock analysis with Streamlit UI, long/short-term modes, screening, and Traditional Chinese reports.

**Verified baseline (2026-06-26):** LYFT full analysis in ~192s, 7/7 steps, Poe `gpt-4o-mini` + `claude-haiku-4.5`.

**Current default (2026-06-27):** Poe `gpt-5-nano` (quick) + `gpt-5-mini` (deep) — higher finance-reasoning scores at lower cost.

---

## 1. Requirements

- **Python 3.10+** (tested on 3.11 / 3.13)
- **macOS / Linux** (SSL cert fix included for macOS Python)
- **Poe API key** (required for MVP v1.0 default config)
- Optional: **FRED API key** (macro data in long-term mode)
- Optional: **OpenRouter API key** (only if you switch away from Poe)

---

## 2. Installation

```bash
cd TradingAgents-main   # or your clone path
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[ui,dev]"
```

Copy environment template and fill in keys:

```bash
cp .env.example .env
```

---

## 3. Environment setup (`.env`)

### Required — Poe (MVP v1.0 default)

```bash
# Poe API key: https://poe.com/api/keys
OPENAI_COMPATIBLE_API_KEY=sk-poe-xxxxxxxx

TRADINGAGENTS_LLM_PROVIDER=openai_compatible
TRADINGAGENTS_LLM_BACKEND_URL=https://api.poe.com/v1
TRADINGAGENTS_QUICK_THINK_LLM=gpt-5-nano
TRADINGAGENTS_DEEP_THINK_LLM=gpt-5-mini
```

### Recommended tuning

```bash
TRADINGAGENTS_MAX_DEBATE_ROUNDS=1
TRADINGAGENTS_MAX_RISK_ROUNDS=1
TRADINGAGENTS_SENTIMENT_FREETEXT_FIRST=true
TRADINGAGENTS_OUTPUT_LANGUAGE=Traditional Chinese
TRADINGAGENTS_LLM_TIMEOUT=120
TRADINGAGENTS_LLM_MAX_RETRIES=1
```

### Optional — macro data (long-term mode)

```bash
# Free: https://fred.stlouisfed.org/docs/api/api_key.html
FRED_API_KEY=your_fred_key
```

### Optional — report output inside project

```bash
TRADINGAGENTS_RESULTS_DIR=/path/to/TradingAgents-main/results
```

Default reports go to `~/.tradingagents/logs/reports/`.

---

## 4. Run

```bash
streamlit run app.py
```

Open http://localhost:8501

**Watch the terminal** where Streamlit runs — progress logs (step timing, ETA) print there, not only in the browser.

### Typical workflow

1. **Sidebar:** choose 短線 / 長線, horizon, analysts
2. **Tab 選股:** run screener (e.g. sp600, top 5)
3. **Tab 深度分析:** pick tickers → full report (~3–5 min/ticker on Poe MVP config)
4. **Tab 報告:** open saved reports

---

## 5. LLM model configuration (important)

### MVP v1.0 architecture

| Role | Model | Provider | Calls per ticker | Why |
|------|-------|----------|------------------|-----|
| **Quick** (analysts, debate, trader, risk) | `gpt-5-nano` | Poe | ~15 | Cheapest OpenAI tier, stable tool-calling |
| **Deep** (Research Manager, Portfolio Manager) | `gpt-5-mini` | Poe | 2 | ~87% finance reasoning (AIMultiple), structured output |

Both use the same Poe endpoint and `OPENAI_COMPATIBLE_API_KEY`.

### Cost (rough)

- **~$0.02–0.08 per full ticker** on Poe MVP config (`gpt-5-nano` + `gpt-5-mini`)
- Previous `gpt-4o-mini` + `claude-haiku-4.5` was ~$0.05–0.15; deep model ranked low on finance reasoning benchmarks

### Do NOT use (lessons from testing)

| Config | Problem |
|--------|---------|
| OpenRouter **free** models (`:free` suffix) | HTTP **429** on tool-calling steps; Market Analyst fails after ~3 min |
| Poe **Sonnet / Opus** for quick | Works but **very expensive** on Poe points |
| Poe **Gemini Flash** for quick | Tool-calling returns **None** on Poe endpoint — do not use for Market/News/Fundamentals |
| `TRADINGAGENTS_LLM_MAX_RETRIES=3` with failing provider | Multiplies wait time (each retry ~60–180s) |

### OpenRouter vs Poe (if you want to experiment)

| | OpenRouter paid (e.g. `google/gemini-2.5-flash-lite`) | Poe (`gpt-5-nano` / `gpt-5-mini`) |
|--|--|--|
| Price per ticker | ~$0.01–0.02 | ~$0.02–0.08 |
| Rate limits | Paid: no 429 | Poe points pool |
| Tool-calling | Native OpenAI path, stable | Verified on Poe for GPT-5 family |
| Setup | `OPENROUTER_API_KEY` + `TRADINGAGENTS_LLM_PROVIDER=openrouter` | Single Poe key |

Poe is ~7–15% cheaper than OpenRouter for the **same** model family, but the main win for MVP v1.0 is **one provider, zero 429, verified tool-calls**.

### Mixed provider (advanced)

Per-model overrides in `.env`:

```bash
TRADINGAGENTS_LLM_PROVIDER=openrouter
TRADINGAGENTS_QUICK_THINK_LLM=google/gemini-2.5-flash-lite
TRADINGAGENTS_DEEP_THINK_PROVIDER=openai_compatible
TRADINGAGENTS_DEEP_THINK_BACKEND_URL=https://api.poe.com/v1
TRADINGAGENTS_DEEP_THINK_LLM=gpt-5-mini
```

---

## 6. Data sources (no extra keys)

| Source | Used by | Notes |
|--------|---------|-------|
| yfinance | Price, fundamentals, news | Default |
| Arctic Shift | Reddit sentiment | Primary; no OAuth |
| StockTwits | Retail sentiment | Public API |
| Reddit RSS | Reddit fallback | May 429 under burst |
| FRED | Macro (long-term) | Needs `FRED_API_KEY` |

SSL: `certifi` CA bundle via `tradingagents/dataflows/http_utils.py` (fixes macOS `CERTIFICATE_VERIFY_FAILED`).

---

## 7. Report output structure

Each run saves under `~/.tradingagents/logs/reports/{TICKER}_{timestamp}/`:

| Path | Content |
|------|---------|
| `scorecard.md` | One-page quality/growth/value scores |
| `investment_memo.md` | **Main read** — Traditional Chinese investment memo |
| `complete_report.md` | Full pipeline in one file |
| `1_analysts/` | market, sentiment, news, fundamentals |
| `2_research/` | bull, bear, research manager |
| `3_trading/` | trader plan |
| `4_risk/` | aggressive, conservative, neutral |
| `5_portfolio/` | final Hold/Buy/Sell decision |

---

## 8. Troubleshooting

| Symptom | Fix |
|---------|-----|
| `429 Provider returned error` | You are on OpenRouter **free** model — switch to Poe MVP config above |
| Stuck on Market Analyst 0/7 | Tool-calling model failing; use `gpt-5-nano` on Poe |
| `FRED_API_KEY not set` | Optional warning; add key or ignore for non-macro runs |
| `Event loop is closed` on Ctrl+C | Harmless Streamlit shutdown noise on Python 3.13 |
| Progress bar frozen | Check **terminal** logs; LLM steps can take 30–60s each |

---

## 9. Tests

```bash
pytest tests/ -q
```

516+ tests pass on MVP v1.0 baseline.

---

## 10. Disclaimer

For **research and education only**. Not financial advice. LLM outputs are non-deterministic; verify numbers against primary sources before any investment decision.

---

Based on [TradingAgents](https://github.com/TauricResearch/TradingAgents) (Tauric Research). MVP v1.0 customizations: Poe LLM stack, Arctic Shift Reddit, SSL fix, Streamlit timing UI, Traditional Chinese output, debate rounds = 1.
