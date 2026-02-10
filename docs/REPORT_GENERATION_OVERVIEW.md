# REISHI v5.4 報告生成完整清單

## 概述

每次執行 `python main_v5.py --daily` 會生成以下報告文件。根據執行方式的不同，會生成不同層級的詳細度。

---

## 1️⃣ Daily Run 報告 (`--daily`)

### 輸出位置
```
reports/daily/
├── 2026-02-10_154253.md                    # 舊格式：簡單摘要（已棄用）
├── 2026-02-10_154253/                      # 新格式：詳細日誌目錄
│   ├── 00_MASTER_FLOW.md                   # ⭐ 完整執行流程
│   ├── 01_LLM_CALLS.jsonl                  # ⭐ LLM 呼叫詳細記錄
│   ├── 02_DATA_FLOW.md                     # ⭐ 數據流向追蹤
│   ├── step_01_數據獲取與驗證.md           # Step 1 詳細報告
│   ├── step_02_基本面分析.md               # Step 2 詳細報告
│   ├── step_03_圖表型態識別.md             # Step 3 詳細報告
│   ├── step_04_因果推理.md                 # Step 4 詳細報告（如果啟用）
│   ├── step_05_情緒分析.md                 # Step 5 詳細報告（如果啟用）
│   ├── step_06_Multi-Agent協作.md          # Step 6 詳細報告
│   ├── step_07_霊視記憶.md                 # Step 7 詳細報告（如果啟用）
│   ├── step_08_決策引擎.md                 # Step 8 詳細報告
│   ├── step_09_驗證與審計.md               # Step 9 詳細報告（如果啟用）
│   └── SUMMARY_REPORT.md                   # 最終摘要報告
└── ...更多日期的報告
```

### 各文件說明

#### ⭐ **00_MASTER_FLOW.md** (完整執行流程)
最重要的日誌文件，包含：
- **執行時序** — 所有步驟的開始/結束時間
- **LLM 思考過程** — 每個 LLM 呼叫的完整詳情
  - System Prompt
  - User Prompt
  - Raw Response
  - Parsed Result
- **數據統計** — 每步處理的數據量
- **耗時信息** — 每步耗時

**示例內容:**
```markdown
## 執行時序

### [2026-02-10 15:42:53] Step 1: 數據獲取與驗證
**描述**: 從 Yahoo Finance / 多數據源取得 K 線數據
**輸入數據**: 掃描標的 4,800 檔
**輸出數據**: 有效數據 2,478 檔

#### 🤖 LLM 呼叫 [Fundamental 分析師] - AAPL
**提供商**: mistral | **模型**: mistral-small-latest
**System Prompt**: 你是一個基本面分析師...
**User Prompt**: 請分析 AAPL...
**LLM Response**: AAPL 的 PE 比率為 25.5...
```

#### **01_LLM_CALLS.jsonl** (LLM 呼叫詳細記錄)
結構化的 JSON Lines 格式，每行一條 LLM 呼叫：

```json
{
  "timestamp": "2026-02-10T15:42:53.123456",
  "step_index": 6,
  "step_name": "Multi-Agent 協作分析",
  "agent_role": "Fundamental 分析師",
  "ticker": "AAPL",
  "provider": "mistral",
  "model": "mistral-small-latest",
  "system_prompt": "你是一個基本面分析師，評估以下股票...",
  "user_prompt": "請分析 AAPL 的 PE、PB、ROE...",
  "raw_response": "AAPL 的 PE 比率為 25.5，PB 比率為 35.2...",
  "parsed_result": {
    "pe_ratio": 25.5,
    "pb_ratio": 35.2,
    "roe": 95.3,
    "recommendation": "HOLD"
  }
}
```

用途：
- 導入 Excel/BI 工具進行分析
- 自動化數據提取（使用 jq）
- 統計 LLM 使用情況和成本

#### **02_DATA_FLOW.md** (數據流向追蹤)
記錄數據在各步驟間的轉化：

```markdown
## Step 1: 數據獲取 → Step 3: 圖表掃描

**時間**: 2026-02-10 15:42:53
**描述**: 市場 K 線數據 (OHLCV)
**樣本**: AAPL [2026-02-10]: Open 230.5, High 231.2, Low 229.8...

## Step 3: 圖表掃描 → Step 6: Multi-Agent

**時間**: 2026-02-10 15:43:10
**描述**: 圖表候選 (breakthrough patterns)
**樣本**: PXS, GHY, SPXC (3 candidates)
```

#### **step_NN_名稱.md** (各步驟詳細報告)
每個步驟的獨立報告，包含：
- 步驟描述
- 輸入數據統計
- 處理邏輯
- 輸出結果
- 執行時間

#### **SUMMARY_REPORT.md** (最終摘要)
人類可讀的投資建議摘要，包含：
- 📋 今日行動指令
- 📊 持倉狀態
- ⚠️ 異常與警告
- ✅ 確認項目
- 📈 分析摘要

---

## 2️⃣ Backtest 報告 (`--backtest`)

### 輸出位置
```
reports/backtest_range/
├── 2025-01-01_to_2025-12-31/
│   ├── backtest_summary.csv                # ⭐ 回測摘要（日級別）
│   ├── backtest_trades.csv                 # ⭐ 交易記錄
│   ├── state/
│   │   ├── positions_2025-01-02.csv        # 每日持倉狀態
│   │   └── ...更多日期
│   └── daily_YYYY-MM-DD/                   # 每日詳細報告
│       ├── step_01_*.md
│       ├── step_02_*.md
│       └── ...
└── ...更多日期範圍
```

### 回測文件說明

#### **backtest_summary.csv** (日級別摘要)
```csv
Date,Initial_Cash,Final_Value,Daily_PnL,Cumulative_Return_%,Portfolio_Value,Num_Trades
2025-01-02,100000,100500,500,0.5,100500,1
2025-01-03,100500,101200,700,1.2,101200,1
...
```

#### **backtest_trades.csv** (交易記錄)
```csv
Entry_Date,Entry_Price,Exit_Date,Exit_Price,Ticker,Quantity,Action,PnL,Return_%,Duration_Days
2025-01-02,150.50,2025-01-10,155.20,AAPL,100,BUY,470,3.1%,8
2025-01-05,220.30,2025-01-15,215.50,MSFT,-100,SELL,470,2.2%,10
...
```

用途：與 Orchestrator 整合，計算 Sortino、MDD、夏普比等指標

#### **positions_YYYY-MM-DD.csv** (每日持倉)
```csv
Ticker,Quantity,Entry_Price,Current_Price,Entry_Date,Current_Value,Unrealized_PnL
AAPL,100,150.50,155.20,2025-01-02,15520,470
MSFT,-50,220.30,215.50,2025-01-05,-10775,235
```

---

## 3️⃣ 監控報告 (`--monitor`)

### 輸出位置
```
reports/monitor/
├── portfolio_status_YYYY-MM-DD_HHMMSS.md   # 即時持倉狀態
├── real_time_alerts_YYYY-MM-DD.log         # 實時警告日誌
└── performance_metrics.json                 # 性能指標快照
```

### 監控文件說明

#### **portfolio_status_*.md**
```markdown
## 實時持倉狀態 (2026-02-10 15:43:12)

### 持倉概覽
- 總市值: $1,250,000
- 現金: $50,000
- 已用槓桿: 0%

### 持倉詳情
| Ticker | 數量 | 成本價 | 現價 | 未實現損益 | 佔比 |
|--------|------|-------|------|-----------|------|
| AAPL   | 100  | 150.5 | 155.2| +470 (+3.1%)| 12.4%|
| MSFT   | -50  | 220.3 | 215.5| +235 (+2.2%)| -8.6%|
```

#### **real_time_alerts_*.log**
```
[2026-02-10 15:42:00] ⚠️  STOP LOSS: AAPL 跌破 145.00 (現價 144.80)
[2026-02-10 15:43:30] ✅ TARGET HIT: MSFT 達到 225.00 (現價 226.50)
[2026-02-10 15:45:00] 📢 SIGNAL: GHY 出現突破型態
```

---

## 4️⃣ 數據管理報告 (`--data-management`)

### 輸出位置
```
data/
├── market_data/
│   ├── us_stocks/
│   │   ├── 2025.parquet                    # US 股票年度數據
│   │   ├── 2024.parquet
│   │   └── ...
│   └── hk_stocks/
│       ├── 2025.parquet
│       └── ...
├── download_log_YYYY-MM-DD.txt             # 下載進度日誌
└── data_validation_report.json             # 數據驗證結果
```

### 數據文件說明

#### **數據統計**
```json
{
  "date": "2026-02-10",
  "us_stocks_total": 2478,
  "hk_stocks_total": 1200,
  "data_coverage": {
    "2025": "100%",
    "2024": "100%",
    "2023": "95%"
  },
  "missing_tickers": ["DELISTED1", "DELISTED2"],
  "file_sizes": {
    "us_stocks_2025.parquet": "18.5 GB",
    "hk_stocks_2025.parquet": "8.2 GB"
  }
}
```

---

## 📊 文件規模參考

| 報告類型 | 文件大小 | 生成時間 | 頻率 |
|---------|---------|---------|------|
| Daily (完整日誌) | 5-20 MB | 15-30 分鐘 | 每日 |
| Daily (摘要) | 5-10 KB | < 1 秒 | 每日 |
| Backtest (60 天) | 50-100 MB | 2-4 小時 | 按需 |
| Monitor (即時) | 100 KB | < 1 秒 | 持續 |

---

## 🎯 報告用途速查表

| 用途 | 查看文件 |
|------|---------|
| 了解今日決策邏輯 | `00_MASTER_FLOW.md` |
| 檢查 LLM 是否幻覺 | `01_LLM_CALLS.jsonl` |
| 追蹤數據流向 | `02_DATA_FLOW.md` |
| 查看投資建議 | `SUMMARY_REPORT.md` |
| 性能回測評估 | `backtest_summary.csv` |
| 交易明細檢查 | `backtest_trades.csv` |
| 實時持倉監控 | `portfolio_status_*.md` |
| 詳細步驟分析 | `step_NN_*.md` |
| 數據統計驗證 | `data_validation_report.json` |

---

## 🔍 快速查看命令

```bash
# Daily 報告
python view_full_run_log.py                    # 查看最新完整日誌
python view_full_run_log.py --list             # 列出所有日誌
python view_full_run_log.py llm                # 查看 LLM 呼叫摘要
python view_full_run_log.py step 3             # 查看 step 3 報告

# 快速文本搜尋
grep "AAPL" reports/daily/2026-02-10_154253/00_MASTER_FLOW.md
grep "error\|failed" reports/daily/2026-02-10_154253/step_01_*.md

# 數據分析
cat reports/daily/2026-02-10_154253/01_LLM_CALLS.jsonl | jq -r '.agent_role' | sort | uniq -c
cat backtest_trades.csv | awk -F',' '{sum+=$9} END {print "Total PnL: $" sum}'
```

---

## 💾 儲存管理

### 建議保留策略
- **最近 7 天**: 保留所有詳細日誌（用於調試）
- **8-30 天**: 保留摘要報告（用於回顧）
- **31 天以上**: 只保留 backtest 和關鍵指標

### 清理舊日誌
```bash
# 刪除 30 天以上的舊日誌
find reports/daily -type d -mtime +30 -exec rm -rf {} \;

# 統計磁碟使用
du -sh reports/daily/*
du -sh reports/backtest_range/*
```

---

## 🔗 相關文檔

- [FULL_RUN_LOG_GUIDE.md](./FULL_RUN_LOG_GUIDE.md) — 完整日誌使用指南
- [API_KEYS_IN_FLOW.md](./API_KEYS_IN_FLOW.md) — 各步驟使用的 API
- [CLAUDE.md](../CLAUDE.md) — 項目配置和架構

---

**版本**: v5.4 (2026-02-10)
**最後更新**: 2026-02-10
