# REISHI (霊視) v4.2 → v4.3 變更總覽

**版本**：v4.3  
**整理日期**：2026-01-31  

---

## 一、多數據源架構（新增）

### 1.1 新增 `utils/data_sources.py`

| 功能 | 說明 |
|------|------|
| **統一介面** | `get_daily_bars()`, `get_close_on_date()`, `get_close_verified()` |
| **11 個數據源** | Yahoo → Stooq → FMP → Twelve Data → Tiingo → Finnhub → Polygon → Alpha Vantage → IEX → Marketstack → EODHD |
| **交叉驗證** | `get_close_verified()` 多源比對，價差 < 0.5% 視為一致 |
| **OHLCV 驗證** | 移除 NaN、負數、異常列（Open≤High, Low≤Close, Volume≥0） |
| **多源合併補洞** | 首源不足 min_bars 時，嘗試他源補齊缺失交易日 |

### 1.2 Yahoo 多層 fallback

- **`fetch_daily_bars`**：start/end → period=1mo → 3mo → 6mo，確保回測 2025 等近期數據可取到
- **`fetch_close`**：原有 3 層 fallback 保留

### 1.3 已改用多數據源的模組

| 檔案 | 變更 |
|------|------|
| `stage1_quick_scan.py` | `get_daily_bars()` 取代直接 yfinance |
| `stage2_deep_verify.py` | 引入多數據源介面 |
| `daily_monitor.py` | `get_close_on_date()` + 優先 `get_close_verified()` |
| `utils/data_fetcher.py` | 股價優先走統一介面 |
| `backtest_simulator.py` | 執行價由 daily_monitor（多數據源）取 |

---

## 二、回測修正

### 2.1 Stage 1 日期範圍 bug 修正

- **問題**：回測區間起始日當作 start_date，僅數日歷史，導致 `len(df)<20` 全被篩掉
- **修正**：確保至少 90 日歷史（`start_date = min(backtest_start, end_date - 90天)`）

### 2.2 CLI 回測區間

- **原本**：`--backtest YYYY-MM-DD`（單日）
- **現在**：
  - 單日：`--backtest 2025-01-10`
  - 區間：`--backtest 2025-01-01 2025-01-15`
  - 小股數加快：`--backtest 2025-01-01 2025-01-15 --quick`

### 2.3 起始資本

- **原本**：100,000 USD
- **現在**：7,000 USD（`config.BACKTEST_INITIAL_CASH`）

---

## 三、數據品質強化

### 3.1 收盤價交叉驗證

- `get_current_price()` 改為優先使用 `get_close_verified()`（至少 2 源）
- 無足夠源時退為 `get_close_on_date()`

### 3.2 多源合併參數

- `get_daily_bars()` 新增 `min_bars=20`, `merge_sources=True`
- 首源不足時自動嘗試他源補洞

---

## 四、Config 與測試階段

### 4.1 Stage 2 數據源

- `required_sources`: 3 → 2（測試階段兩源對照即通過）

### 4.2 API Keys（.env）

已支援：FMP、Alpha Vantage、Twelve Data、Tiingo、Finnhub、Polygon、EODHD、FRED、Alpaca 等。

---

## 五、檔案變更清單

| 檔案 | 狀態 |
|------|------|
| `utils/data_sources.py` | 新增 |
| `config.py` | 修改（BACKTEST_INITIAL_CASH, STAGE2_CONFIG） |
| `main.py` | 修改（--backtest 區間、--quick） |
| `stage1_quick_scan.py` | 修改（多數據源、回測日期範圍） |
| `stage2_deep_verify.py` | 修改（多數據源） |
| `daily_monitor.py` | 修改（get_close_verified 優先） |
| `utils/data_fetcher.py` | 修改（多數據源整合） |
| `backtest_simulator.py` | 修改（假日處理、多數據源註解） |
| `RECENT_CHANGES.md` | 修改（近期變更整理） |

---

## 六、常用指令

```bash
python main.py                          # 互動選單
python main.py --daily                  # 今日流程
python main.py --backtest 2025-01-10    # 單日回測
python main.py --backtest 2025-01-01 2025-01-15 --quick  # 區間回測（小股數）
python main.py --test-all               # 小樣本 Stage1→2→3
```
