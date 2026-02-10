# REISHI v5.4 報告目錄結構詳解

## 📂 完整目錄樹

```
stock_scanner/
├── reports/
│   ├── daily/                                    # 每日分析報告
│   │   ├── 2026-02-10_154253.md                 # 舊格式摘要（已棄用）
│   │   ├── 2026-02-10_142025.md
│   │   ├── 2026-02-10_123522.md
│   │   │
│   │   ├── 2026-02-10_154253/                   # ⭐ 新格式：完整日誌目錄
│   │   │   ├── 00_MASTER_FLOW.md                # 完整執行流程 (最重要)
│   │   │   ├── 01_LLM_CALLS.jsonl               # LLM 呼叫記錄 (JSONL)
│   │   │   ├── 02_DATA_FLOW.md                  # 數據流向追蹤
│   │   │   │
│   │   │   ├── step_01_數據獲取與驗證.md        # Step 1: 取數
│   │   │   │   ├── 輸入：tickers_count: 4800
│   │   │   │   ├── 輸出：valid_tickers: 2478
│   │   │   │   └── 耗時：12.34s
│   │   │   │
│   │   │   ├── step_02_基本面分析.md            # Step 2: 基本面
│   │   │   │   ├── 輸入：market_data: 2478 檔
│   │   │   │   ├── 輸出：PE, PB, ROE 分析
│   │   │   │   └── 耗時：8.56s
│   │   │   │
│   │   │   ├── step_03_圖表型態識別.md          # Step 3: 圖表
│   │   │   │   ├── 輸入：K 線數據
│   │   │   │   ├── 輸出：211 個候選
│   │   │   │   └── 耗時：15.23s
│   │   │   │
│   │   │   ├── step_04_因果推理.md              # Step 4: 因果分析
│   │   │   │   ├── 輸入：新聞 + 持倉
│   │   │   │   ├── 輸出：因果鏈分析
│   │   │   │   └── 耗時：5.12s
│   │   │   │
│   │   │   ├── step_05_情緒分析.md              # Step 5: 情緒
│   │   │   │   ├── 輸入：新聞文本
│   │   │   │   ├── 輸出：sentiment scores
│   │   │   │   └── 耗時：7.89s
│   │   │   │
│   │   │   ├── step_06_Multi-Agent協作.md       # Step 6: 多代理共識
│   │   │   │   ├── 輸入：圖表候選 211 個
│   │   │   │   ├── 輸出：共識建議
│   │   │   │   ├── LLM 呼叫數：6-10 次
│   │   │   │   └── 耗時：18.45s
│   │   │   │
│   │   │   ├── step_07_霊視記憶.md              # Step 7: 記憶洞察
│   │   │   │   ├── 輸入：歷史交易
│   │   │   │   ├── 輸出：相似案例
│   │   │   │   └── 耗時：3.21s
│   │   │   │
│   │   │   ├── step_08_決策引擎.md              # Step 8: 決策
│   │   │   │   ├── 輸入：所有分析結果
│   │   │   │   ├── 輸出：BUY/SELL/HOLD 指令
│   │   │   │   ├── LLM 呼叫數：2-3 次
│   │   │   │   └── 耗時：12.34s
│   │   │   │
│   │   │   ├── step_09_驗證與審計.md            # Step 9: 驗證
│   │   │   │   ├── 輸入：決策結果
│   │   │   │   ├── 輸出：驗證通過/失敗
│   │   │   │   └── 耗時：2.15s
│   │   │   │
│   │   │   └── SUMMARY_REPORT.md                # 最終摘要報告
│   │   │       ├── 今日行動指令
│   │   │       ├── 持倉狀態
│   │   │       ├── 異常與警告
│   │   │       └── 分析摘要
│   │   │
│   │   ├── 2026-02-10_142025/                   # 前一次運行
│   │   │   └── (同樣結構)
│   │   │
│   │   └── ... (更多日期)
│   │
│   │
│   ├── backtest_range/                          # 回測報告
│   │   ├── 2025-01-01_to_2025-12-31/
│   │   │   ├── backtest_summary.csv             # 日級別摘要
│   │   │   │   ├── Date, Initial_Cash, Final_Value, Daily_PnL, ...
│   │   │   │   └── 365 行（每日一行）
│   │   │   │
│   │   │   ├── backtest_trades.csv              # 交易記錄
│   │   │   │   ├── Entry_Date, Entry_Price, Ticker, Quantity, ...
│   │   │   │   └── N 行交易
│   │   │   │
│   │   │   ├── state/
│   │   │   │   ├── positions_2025-01-02.csv
│   │   │   │   ├── positions_2025-01-03.csv
│   │   │   │   └── ... (每個交易日)
│   │   │   │
│   │   │   └── daily_2025-01-02/
│   │   │       ├── step_01_*.md
│   │   │       ├── step_02_*.md
│   │   │       └── ... (每日詳細報告)
│   │   │
│   │   └── 2024-01-01_to_2024-06-30/            # 其他時間範圍
│   │       └── (同樣結構)
│   │
│   │
│   ├── monitor/                                 # 實時監控報告
│   │   ├── portfolio_status_2026-02-10_154300.md
│   │   ├── portfolio_status_2026-02-10_160000.md
│   │   ├── real_time_alerts_2026-02-10.log
│   │   └── performance_metrics.json
│   │
│   └── 2026-02-09_234618/                       # 舊格式回測報告 (棄用)
│       ├── REIKAN_run.log
│       ├── REIKAN_daily_report.txt
│       └── ...
│
│
├── data/                                        # 市場數據
│   ├── market_data/
│   │   ├── us_stocks/
│   │   │   ├── 2025.parquet                     # 2025 年 US 股票數據
│   │   │   ├── 2024.parquet
│   │   │   ├── 2023.parquet
│   │   │   └── ...
│   │   │
│   │   └── hk_stocks/
│   │       ├── 2025.parquet                     # 2025 年港股數據
│   │       ├── 2024.parquet
│   │       └── ...
│   │
│   ├── reishi_memory.db                         # 歷史交易記錄數據庫
│   ├── company_relationships.db                 # 公司關係圖數據庫
│   │
│   └── download_log_2026-02-10.txt              # 數據下載日誌
│
│
├── logs/                                        # 系統日誌（新增）
│   └── llm_debug/
│       ├── llm_run_20260210_154253.log
│       ├── llm_run_20260210_154253.jsonl
│       └── ...
│
│
└── .cursor/
    └── debug.log                                # 實時執行日誌
```

---

## 📊 報告生成流程圖

```
python main_v5.py --daily
        ↓
    [初始化 ReishiV5]
        ↓
    [初始化 MasterFlowLogger]
        ↓
    ┌─────────────────────────────────────┐
    │   報告目錄創建                        │
    │   reports/daily/2026-02-10_154253/  │
    └─────────────────────────────────────┘
        ↓
    ┌───────────────────────────────────────────┐
    │  Step 1: 數據獲取 (15-30s)                 │
    │  → step_01_數據獲取與驗證.md              │
    └───────────────────────────────────────────┘
        ↓
    ┌───────────────────────────────────────────┐
    │  Step 2-8: AI 分析 (30-60s)               │
    │  → step_02_*.md, step_03_*.md, ...       │
    │  → 01_LLM_CALLS.jsonl 持續記錄            │
    │  → 02_DATA_FLOW.md 持續記錄              │
    └───────────────────────────────────────────┘
        ↓
    ┌───────────────────────────────────────────┐
    │  Step 9: 驗證與審計 (5-10s)               │
    │  → step_09_驗證與審計.md                  │
    └───────────────────────────────────────────┘
        ↓
    ┌───────────────────────────────────────────┐
    │  報告生成                                  │
    │  → 00_MASTER_FLOW.md (終結合)             │
    │  → SUMMARY_REPORT.md                     │
    │  → DailyReportGenerator 摘要報告          │
    └───────────────────────────────────────────┘
        ↓
    ✅ 完成！總耗時: 60-120 秒
```

---

## 📈 報告大小估計

```
Daily Run (單次):
├── 00_MASTER_FLOW.md          ~ 2-5 MB
├── 01_LLM_CALLS.jsonl         ~ 1-3 MB
├── 02_DATA_FLOW.md            ~ 100-500 KB
├── step_01_*.md               ~ 50-200 KB
├── step_02_*.md               ~ 100-300 KB
├── ... (其他 steps)           ~ 400-1000 KB
└── SUMMARY_REPORT.md          ~ 5-10 KB
                              ─────────────
                              總計: 4-10 MB

Backtest Run (60 天):
├── backtest_summary.csv       ~ 10-20 KB
├── backtest_trades.csv        ~ 500-1000 KB
├── state/*.csv                ~ 30-50 MB
└── daily_*/ (60 個)           ~ 240-600 MB
                              ─────────────
                              總計: 270-650 MB

磁碟使用 (30 天 daily runs):
├── 30 個完整日誌              ~ 120-300 MB
├── 市場數據 (1 年)            ~ 30-50 GB
└── 數據庫                     ~ 100-500 MB
                              ─────────────
                              總計: 30-50 GB
```

---

## 🔍 文件查詢速查表

| 我想知道... | 查看文件 | 命令 |
|-----------|---------|------|
| 為什麼推薦 BUY AAPL | `00_MASTER_FLOW.md` | `grep -A 20 "AAPL" ...` |
| AAPL 的圖表型態 | `step_03_*.md` | `grep "AAPL" step_03_*.md` |
| LLM 是否正確分析 AAPL | `01_LLM_CALLS.jsonl` | `grep "AAPL" 01_LLM_CALLS.jsonl` |
| 數據如何流動 | `02_DATA_FLOW.md` | 直接查看 |
| 今天的決策 | `SUMMARY_REPORT.md` | 直接查看 |
| LLM 呼叫次數統計 | `01_LLM_CALLS.jsonl` | `wc -l 01_LLM_CALLS.jsonl` |
| 每個 step 耗時 | `00_MASTER_FLOW.md` | `grep "耗時" ...` |
| 回測績效 | `backtest_summary.csv` | 在 Excel 中打開 |
| 特定交易明細 | `backtest_trades.csv` | `grep "AAPL" backtest_trades.csv` |
| 當前持倉 | `portfolio_status_*.md` | `cat portfolio_status_latest.md` |

---

## 💡 常見使用場景

### 場景 1: 調試為什麼推薦 BUY
```bash
# 1. 查看完整流程
python view_full_run_log.py master

# 2. 搜尋特定股票
grep -n "AAPL" reports/daily/2026-02-10_154253/00_MASTER_FLOW.md

# 3. 查看 LLM 呼叫
cat reports/daily/2026-02-10_154253/01_LLM_CALLS.jsonl | jq 'select(.ticker == "AAPL")'

# 4. 查看特定 step
cat reports/daily/2026-02-10_154253/step_06_Multi-Agent協作.md
```

### 場景 2: 性能優化
```bash
# 1. 找最慢的步驟
grep "耗時" reports/daily/2026-02-10_154253/00_MASTER_FLOW.md | sort -t'.' -k1 -rn

# 2. 統計 LLM 呼叫
wc -l reports/daily/2026-02-10_154253/01_LLM_CALLS.jsonl

# 3. 估算成本
cat reports/daily/2026-02-10_154253/01_LLM_CALLS.jsonl | jq -r '.provider' | sort | uniq -c
```

### 場景 3: 數據驗證
```bash
# 1. 查看數據流向
cat reports/daily/2026-02-10_154253/02_DATA_FLOW.md

# 2. 驗證數據大小
grep "tickers_count\|valid_tickers" reports/daily/2026-02-10_154253/step_01_*.md

# 3. 檢查異常
grep -i "error\|failed\|invalid" reports/daily/2026-02-10_154253/step_*.md
```

---

## 🗂️ 檔案組織最佳實踐

### 命名約定
```
daily/
├── YYYY-MM-DD_HHMMSS/          # 時間戳目錄（精確到秒）
│   ├── 00_MASTER_FLOW.md       # 固定前綴便於排序
│   ├── 01_LLM_CALLS.jsonl
│   ├── 02_DATA_FLOW.md
│   ├── step_01_名稱.md          # step 編號 + 中文名稱
│   └── step_NN_名稱.md
│
└── YYYY-MM-DD_HHMMSS.md        # 舊格式摘要（已棄用）
```

### 清理策略
```bash
# 刪除 30 天以上的舊日誌，保留最近 7 天
find reports/daily -type d -mtime +30 -name "????-??-??_??????" -exec rm -rf {} \;

# 只保留摘要，刪除詳細日誌（節省空間）
find reports/daily -type d -mtime +7 -name "????-??-??_??????" -exec rm -rf {} \;
```

---

**版本**: v5.4 (2026-02-10)
