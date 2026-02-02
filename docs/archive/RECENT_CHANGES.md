# 近期變更整理（v4.2 → v4.3）

> **完整變更清單**：見 [CHANGELOG_V4.2_TO_V4.3.md](CHANGELOG_V4.2_TO_V4.3.md)

## 一、多數據源架構（第一性原理）

### 1. 新增模組 `utils/data_sources.py`

- **統一介面**
  - `get_daily_bars(symbol, start, end)`：取得區間日線
  - `get_close_on_date(symbol, d)`：取得單日收盤價
  - `get_close_verified(symbol, d)`：取得收盤價 + 交叉驗證（fact check）

- **數據源（依序嘗試，直到拿到數據）**
  - Yahoo Finance（無 key）
  - Stooq 波蘭（無 key）
  - FMP、Alpha Vantage、Twelve Data、Tiingo、Finnhub、Polygon、Marketstack、IEX、EODHD（需 key）

- **交叉驗證**：多源有數據時比對收盤價，差異 < 0.5% 視為一致（verified）。

### 2. 已改用多數據源的檔案

| 檔案 | 變更 |
|------|------|
| `stage1_quick_scan.py` | 用 `get_daily_bars()` 取代直接 yfinance |
| `stage2_deep_verify.py` | 引入多數據源介面（財報仍 Yahoo/FMP） |
| `daily_monitor.py` | 用 `get_close_on_date()` 取當前價 |
| `utils/data_fetcher.py` | 整合多數據源，股價優先走統一介面 |
| `backtest_simulator.py` | 註解標示多數據源（執行價仍由 daily_monitor 取） |

### 3. 數據品質強化（v4.3 後續）

- **Yahoo fetch_daily_bars**：多層 fallback（1mo/3mo/6mo）
- **OHLCV 驗證**：過濾 NaN、負數、異常列
- **多源合併補洞**：首源不足 min_bars 時他源補齊
- **get_current_price**：優先 `get_close_verified()` 交叉驗證

---

## 二、測試階段：省 token/資源

### `config.py` 調整

- **Stage 2 對照互測**：由「3 個數據源」改為 **2 個數據源** 即通過。
  - `required_sources`: `3` → `2`
  - 註解：測試階段兩網站對照即可。

---

## 三、API Key 配置（.env）

### 已寫入的數據源 Key

| 變數名 | 用途 |
|--------|------|
| `ALPHA_VANTAGE_API_KEY` | Alpha Vantage 日線（25/天） |
| `TWELVE_DATA_API_KEY` | Twelve Data（800/天） |
| `FINNHUB_API_KEY` | Finnhub（1,440/天） |
| `FMP_API_KEY` | FMP（250/天） |
| `TIINGO_API_KEY` | Tiingo（500/天） |
| `POLYGON_API_KEY` | Polygon/MASSIVE（250/天） |
| `EODHD_API_KEY` | EODHD 歷史數據 |
| `FRED_API_KEY` | FRED 總經（GDP、CPI 等，非股價） |

### 其他已配置

| 變數名 | 用途 |
|--------|------|
| `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` / `ALPACA_BASE_URL` | Alpaca Paper Trading（模擬下單，尚未接程式） |
| Stage 3 LLM | `SCITELY_API_KEY`、`OPENROUTER_API_KEY` 等（既有） |

### 尚未配置（可選）

- `IEX_CLOUD_API_KEY`、`MARKETSTACK_API_KEY`、`QUANDL_API_KEY` 等。

---

## 四、Alpaca 說明

- **行情數據**：可當多一個備援源，但現有 10+ 數據源已夠用，邊際效益小。
- **下單**：若未來要做「依 LLM 建議自動模擬下單」或實盤下單，接 Alpaca Trading API 會很有幫助；目前僅 key 已寫入 .env，尚未接程式。

---

## 五、目錄與檔案一覽

```
stock_scanner/
├── config.py              # STAGE2 required_sources=2，註解更新
├── .env                   # 多組 API key 已填入
├── utils/
│   ├── data_sources.py    # 新增：多數據源 + 交叉驗證
│   └── data_fetcher.py    # 整合多數據源
├── stage1_quick_scan.py   # 用 get_daily_bars
├── stage2_deep_verify.py  # 引入 data_sources
├── daily_monitor.py       # 用 get_close_on_date
├── backtest_simulator.py  # 註解多數據源
├── CHANGELOG_4.3.md       # v4.3 品牌與回測說明
├── UPDATE_SUMMARY.md      # v4 三數據源版本摘要
└── RECENT_CHANGES.md      # 本文件（近期變更整理）
```

---

## 六、常用指令（未變）

```bash
python main.py              # 互動選單
python main.py --daily      # 今日流程
python main.py --backtest 2025-01-10   # 單日回測
python main.py --backtest 2025-01-01 2025-01-15 --quick  # 區間回測
python main.py --test-all   # 小樣本 Stage1→2→3
```

---

**整理日期**：依本次對話完成內容  
**版本**：v4.3 + 多數據源 + 測試階段兩源對照
