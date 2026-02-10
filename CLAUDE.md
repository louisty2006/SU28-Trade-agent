# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**REISHI 霊視 v5.0** is an AI-powered stock scanner system for US and Hong Kong markets. It uses a **five-layer protection system** and **five major AI analysis directions** with an integrated decision engine to identify trading opportunities.

**Current Version**: v5.4 (on branch `v5.4`)
**Main Entry Point**: `main_v5.py` (daily analysis, backtesting, monitoring)

---

## Quick Commands

### Daily Analysis (Primary Mode)
```bash
# Full daily analysis: 9-step AI pipeline
python main_v5.py --daily

# Expected runtime: ~15-30 minutes (depends on stock list size)
# Output: Reports in `reports/daily/`, console logs
```

### Backtesting (Orchestrator Integration)
```bash
# Full backtest: Run v5.0 8-step pipeline for each day
python main_v5.py --backtest 2025-01-01 2025-01-31

# Quick backtest: Sample 5 stocks per day (faster)
python main_v5.py --backtest 2025-01-01 2025-01-31 --quick

# Output: backtest_summary.csv, backtest_trades.csv (Orchestrator-compatible)
```

### Monitoring & Stats
```bash
python main_v5.py --monitor      # Real-time portfolio monitoring
python main_v5.py --stats        # Show memory & system statistics
```

### Setup & Dependencies
```bash
# Install dependencies
pip install -r requirements.txt

# Configure API keys (required for LLM analysis)
cp .env.example .env              # Then fill in API keys
cp config.yaml config.yaml        # Optional: customize stock list

# For backtesting (optional)
cp V5.0_config.json.example config.json
```

---

## Architecture: 9-Step Daily Analysis Pipeline

REISHI v5.0 executes a **9-step analysis** each day, with multiple **AI analysis layers** and **five-layer protection**:

### Flow Overview
```
Input Layer
  ↓
[1] Data Fetch & Validation (First Protection: DataValidator)
  ↓
[2] Fundamental Analysis (DataFetcher: PE, PB, ROE, etc.)
  ↓
AI Analysis Layers (Five Directions):
  [3] Pattern Recognition (Chart technical breakouts + LLM chart verification)
  [4] Causal Reasoning (News + portfolio risk + LLM cause-effect chains)
  [5] Sentiment Analysis (News sentiment scoring via LLM)
  [6] Multi-Agent Analysis (Consensus from Fundamental/Sentiment/Valuation agents)
  [7] Memory Insights (ReishiMemory: historical patterns & knowledge)
  ↓
[8] Decision Engine (Anti-Hallucination protection + synthesis)
  ↓
[9] Output Validation & Final Audit (Second Protection)
  ↓
Report Generation & Notifications
```

### Key Modules

| Module | Location | Responsibility |
|--------|----------|-----------------|
| **ReishiV5** | `main_v5.py` | Orchestrator for all 9 steps, flow logging |
| **DataValidator** | `core/data_validator.py` | Validates stock data from multiple sources |
| **PatternRecognition** | `analysis/pattern_recognition.py` | Detects chart patterns (breakouts, support/resistance) |
| **FundamentalAnalyzer** | `analysis/fundamental_analysis.py` | Analyzes PE, PB, ROE, revenue growth, profit margins |
| **CausalReasoning** | `analysis/causal_reasoning.py` | Links news events to market impacts via LLM |
| **SentimentAnalyzer** | `analysis/sentiment_analysis.py` | Scores news sentiment (-1 to +1) |
| **MultiAgentAnalysis** | `analysis/multi_agent.py` | Consensus from 3+ roles (Fundamental/Sentiment/Valuation) |
| **KnowledgeGraph** | `analysis/knowledge_graph.py` | Company relationships & supply chains |
| **ReishiMemory** | `memory/reishi_memory.py` | Historical recommendations, lessons learned, similar cases |
| **DecisionEngine** | `core/decision_engine.py` | Final decision: BUY/SELL/HOLD, position sizing, stop losses |
| **AntiHallucination** | `core/anti_hallucination.py` | Fact-checks LLM outputs, detects contradictions |
| **OutputValidator** | `core/output_validator.py` | Validates logic & numbers in decisions |
| **FinalAuditor** | `core/final_auditor.py` | Last LLM check (auditor role, checks not judges) |

---

## Configuration & API Keys

### Required Files
- **`.env`**: API keys (required for LLM/news/data)
- **`config.yaml`**: Daily analysis config (stock list, LLM params, validation thresholds)
- **`config.json`**: Backtest config (portfolio size, dates, Orchestrator params)

### Required API Keys (At Least One LLM)
Pick at least **one** LLM provider:
- `SCITELY_API_KEY` (Scitely)
- `COHERE_API_KEY` (Cohere)
- `MISTRAL_API_KEY` (Mistral)
- `OPENROUTER_API_KEY` (OpenRouter, fallback)

### Optional Data Sources
- `FINNHUB_API_KEY` (news, required for causal reasoning & sentiment)
- `IEX_CLOUD_API_KEY`, `FMP_API_KEY`, `TWELVE_DATA_API_KEY`, etc. (multi-source validation)

### Optional Notifications
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (daily reports + alerts)

**Details**: See `docs/API_KEYS_IN_FLOW.md` for which step uses which key.

---

## Data Flow & Data Sources

### Market Data Sources (Step 1)
- **Primary**: Yahoo Finance (unlimited, via yfinance)
- **Secondary**: IEX Cloud, FMP, Finnhub, etc. (optional fallbacks)
- **Validation**: Checks for price anomalies (>30% daily change = red flag)

### News Sources (Step 4-5)
- **Primary**: Finnhub API (company news)
- **Fallback**: Alpha Vantage, Yahoo RSS (if Finnhub insufficient)

### Financial Data (Step 2)
- **Primary**: Yahoo Finance (PE, PB, ROE, revenue growth, margins)
- **Source**: `DataFetcher.get_yahoo_info()` and `get_yahoo_financials_as_of()`

### Portfolio Memory (Step 7)
- **Local SQLite DB**: `data/reishi_memory.db`
- **Tracks**: Historical trades, lessons learned, similar patterns
- **Used by**: ReishiMemory module to provide context for new candidates

---

## LLM Usage & Multi-Provider Fallback

v5.0 supports **four LLM providers** (same as v4.3):
1. **Scitely** (preferred for decision-making)
2. **Cohere** (preferred for analysis)
3. **Mistral** (preferred for risk assessment)
4. **OpenRouter** (fallback if others unavailable)

### How Fallback Works
- If all four keys present: Each module uses its preferred provider
- If only one key present: Single LLM handles all roles (multi-tasking)
- If no keys: System runs in "framework mode" (logic-only, no LLM insights)

**Module**: `core/llm_clients.py` — Central dispatcher for LLM calls.

---

## Backtesting & Orchestrator Integration

### Contract with Orchestrator
- **Input**: `config.json` (dates, initial cash, stock universe)
- **Output**:
  - `backtest_summary.csv` (daily P&L, Sortino, MDD, etc.)
  - `backtest_trades.csv` (trade list: entry/exit dates, prices, P&L)
- **Format**: Identical to v4.3 (backward compatible)

### Orchestrator Calculation
- Orchestrator **computes** Sortino, MDD, transaction costs
- v5.0 **only produces** raw trade data (one CSV per day)
- No config changes needed on Orchestrator side

**Docs**: `docs/guides/V5.0_ORCHESTRATOR_INTEGRATION.md`

---

## Important Implementation Details

### Step 1 (Data Fetch) Progress Reporting
- When fetching data for many tickers, use `on_ticker` callback to log progress
- Example: `self._fetch_and_validate_data(on_ticker=lambda t, i, n: flow_logger.log_layer1_fetch(t, i, n))`
- Helps track progress in long-running scans (100+ stocks)

### Step 3 (Pattern Recognition) Output
- Returns list of `PatternAnalysis` objects with `ticker`, `pattern_name`, `confidence`, `entry_price`, `stop_loss`, `target_price`
- If no patterns found, returns empty list (not an error)

### Step 5 (Sentiment Analysis) News Handling
- Limited to **first 150 tickers** to avoid timeout on large scans (e.g., 9,000 stocks)
- Remaining tickers get empty news lists (treated as neutral sentiment)
- **Config**: `NEWS_CAP = 150` in `main_v5.py` line 150

### Step 6 (Multi-Agent) Consensus
- Takes **pattern candidates** as input (from Step 3)
- Outputs **MultiAgentResult** with consensus action, disagreements, final recommendation
- **No pattern input** = framework output (no trades)

### Step 7 (Memory Insights)
- Searches historical memory for similar patterns to current candidates
- Returns insights like "Similar to May 2024 breakout, worked 80% of the time"
- Used for confidence adjustment by DecisionEngine

### Step 8-9 (Validation & Audit)
- **OutputValidator**: Checks logical consistency (e.g., entry < target, stop < entry)
- **FinalAuditor**: Last LLM check (does NOT override decisions, only flags issues)

---

## Debugging & Logging

### Debug Logs
- **`.cursor/debug.log`**: Real-time run logs (tail-friendly)
- **`debug_run.log`**: Fallback log (at project root)
- Both logs include run_id for correlation: `[REISHI] run_id=1707...`

### Flow Logs
- **`reporting/flow_logger.py`**: Structured logging of each step
- Outputs human-readable step summaries during daily analysis
- Used to understand which modules completed, how many stocks processed, etc.

### How to Debug a Run
```bash
# Check latest run status
tail -20 debug_run.log | grep REISHI

# Monitor live execution
tail -f debug_run.log

# Find a specific run
grep "run_id=1707..." debug_run.log
```

---

## Code Style & Conventions

- **Config parameters**: Keep in `config.yaml` or `config.py`, not hardcoded
- **API calls**: Use `core/llm_clients.py` (LLMClients class) for all LLM interactions
- **Data validation**: Always validate ticker lists before use (empty list = no trades)
- **Error handling**: Log errors with context (ticker, step, data source) but continue execution
- **Progress reporting**: Use `on_ticker` callbacks for long-running loops (>50 items)

---

## Common Development Tasks

### Adding a New Analysis Module
1. Create `analysis/your_analyzer.py` with a class inheriting from a base pattern
2. Implement `analyze()` or `analyze_batch()` method (signature varies by module type)
3. Import in `main_v5.py` and add to `ReishiV5.__init__()`
4. Call in the appropriate step (e.g., Step 3, 4, 5 for AI layers)
5. Update `docs/API_KEYS_IN_FLOW.md` if new API keys used

### Running a Subset of Tickers
- Modify `config.yaml` `scan_list` field to specify tickers
- Or pass tickers directly in code: `ReishiV5._get_scan_tickers()` reads from config

### Testing a Single Stock
```python
from analysis.pattern_recognition import PatternRecognition
pr = PatternRecognition()
result = pr.scan("AAPL", market_data_for_aapl)
```

### Adding a New Validation Rule
- Edit `core/data_validator.py` → add rule in `validate_market_data()`
- Or `core/output_validator.py` for trade decision validation
- Thresholds in `config.yaml` (e.g., `validation.max_price_change_pct`)

---

## File Structure

```
stock_scanner/
├── main_v5.py                      # Entry point (9-step pipeline)
├── config.yaml                     # Daily analysis config
├── config.json                     # Backtest config
├── .env                            # API keys (gitignored)
├── requirements.txt                # Python dependencies
│
├── core/                           # Protection layers & decision
│   ├── data_validator.py           # Step 1: Input validation
│   ├── anti_hallucination.py       # Step 8: Fact-check LLM outputs
│   ├── output_validator.py         # Step 8: Logic validation
│   ├── final_auditor.py            # Step 9: Final audit
│   ├── decision_engine.py          # Step 8-9: Trading decisions
│   ├── data_manager.py             # OHLC management, continuations
│   └── llm_clients.py              # LLM provider abstraction
│
├── analysis/                       # 5 AI analysis directions
│   ├── pattern_recognition.py      # Step 3: Chart patterns
│   ├── fundamental_analysis.py     # Step 2: PE, PB, ROE, growth
│   ├── sentiment_analysis.py       # Step 5: News sentiment
│   ├── multi_agent.py              # Step 6: Consensus analysis
│   ├── causal_reasoning.py         # Step 4: News → market impact
│   └── knowledge_graph.py          # Supply chain relationships
│
├── memory/
│   └── reishi_memory.py            # Step 7: Memory insights
│
├── core/backtest_engine.py         # Backtesting orchestration
├── monitoring/                     # Real-time monitoring
├── reporting/                      # Report generation & notifications
│
├── data/                           # Data storage
│   ├── reishi_memory.db            # Memory persistence
│   └── company_relationships.db    # Knowledge graph DB
│
├── docs/                           # Documentation
│   ├── API_KEYS_IN_FLOW.md         # API usage per step
│   ├── guides/                     # User guides, quickstarts
│   └── development/                # Dev docs
│
└── scripts/                        # Utility scripts
```

---

## Git Workflow

- **Main branch**: `main` (production, stable)
- **Development branch**: `v5.4` (current development)
- **Commit often**: Small, focused commits with clear messages
- **No force push**: Preserve history for debugging
- **Test before commit**: Run `--daily --quick` or unit tests if added

---

## Performance Considerations

### Large Stock Lists (1000+)
- Pattern recognition scales O(n) with tickers
- Sentiment analysis limited to first 150 tickers (see Step 5 notes)
- Use `--quick` backtest flag to sample 5 stocks/day instead of all

### LLM Token Usage
- Each multi-agent analysis consumes ~2-5K tokens per candidate
- Limit candidates to top 10-20 patterns to control costs
- Monitor OpenRouter / Scitely usage in dashboard

### Database Growth
- `reishi_memory.db` grows ~1MB/month with daily trades
- Periodically archive old records (keep last 90 days)
- See `config.yaml` → `database.max_age_days`

---

## Troubleshooting

### "No market data" Warning
- Check `config.yaml` stock list is not empty
- Verify API key for data source is configured
- Check market is open (US/HK trading hours)

### LLM Errors
- Verify at least one LLM API key is set in `.env`
- Check OpenRouter fallback is available if primary LLM fails
- See `core/llm_clients.py` for provider-specific error handling

### Backtest Output Missing
- Ensure `config.json` exists and has required fields (start_date, end_date, initial_cash)
- Check `reports/` folder has write permissions
- Verify date range is valid (not weekends/holidays)

### Memory DB Issues
- Delete `data/reishi_memory.db` to reset memory (will rebuild on next run)
- Check disk space for large historical backtests

---

## References

- **User Guide**: `docs/guides/quickstart_v5.md`
- **API Key Details**: `docs/API_KEYS_IN_FLOW.md`
- **Orchestrator Contract**: `docs/guides/V5.0_ORCHESTRATOR_INTEGRATION.md`
- **Backtesting Notes**: `docs/guides/V5.0_BACKTEST_ORCHESTRATOR_NOTES.md`
- **Changelog**: `docs/changelogs/CHANGELOG_V5.0.md`
