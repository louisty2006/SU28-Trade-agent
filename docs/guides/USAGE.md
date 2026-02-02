# 使用說明（Web App）

以下係使用流程，教你由掃描到 Web App 做入場/離場決策。

## 1) 跑掃描產生 CSV

在 `stock_scanner` 資料夾執行：

```
python scanner_full2.py
```

完成後會喺 `stock_scanner/data/` 生成：
- `scan_YYYYMMDD_HHMM.csv`
- `report_YYYYMMDD_HHMM.html`

## 2) 安裝依賴

```
pip install -r requirements.txt
```

## 3) 設定資料庫（雲端 Postgres）

在 `.env` 或系統環境變數設定：

```
DATABASE_URL=postgresql://user:password@host:port/dbname
```

如果未設定，程式會自動用本地 `sqlite`（不建議長期用）。

## 4) 開啟 Web App

```
cd /Users/ysoffice/Desktop/Stock2026/stock_scanner
streamlit run app.py
```

## 5) 使用流程

### Sidebar（左邊設定）
- **Data folder**：指向 `stock_scanner/data`
- **Strategy mode**：
  - `BottomFishingReversal` = 抄底反轉
  - `TrendBreakout` = 趨勢突破
- **Base capital / TP / SL**：資金、獲利%、止蝕%
- **Score weights**：分數越高，入場資金越大

設定完按 **Save settings**。

### Dashboard
- 顯示最新 CSV 內全部掃描結果

### Entry Planner
- 只顯示符合「策略訊號」股票
- 有建議入場價、目標價、止蝕、建議金額
- 可以 **Save scan + signals to DB** 存入資料庫
- 可以勾選股票 → **Open positions**

### Positions
- 顯示持倉
- 手動輸入出場價 → **Close position**

### History
- 已平倉交易記錄
