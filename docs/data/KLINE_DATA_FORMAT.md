# K 線歷史數據格式說明

數據管理下載的 K 線存於 `data/market_data/us_stocks/`，每年一個 Parquet 檔：`YYYY.parquet`（如 `2005.parquet`）。

## 欄位（齊備清晰）

| 欄位   | 說明           |
|--------|----------------|
| Date   | 交易日（date） |
| Open   | 開盤價         |
| High   | 最高價         |
| Low    | 最低價         |
| Close  | 收盤價         |
| Volume | 成交量         |
| symbol | 股票代碼       |

- 欄位名稱與順序固定，寫入前會正規化（小寫會轉成首字大寫，`ticker` 會對應到 `symbol`）。
- 同一 (Date, symbol) 僅保留一筆（去重保留最後一筆）。
- 寫入前依 `symbol`、`Date` 排序，方便檢視與回測讀取。

## 目錄結構

```
data/market_data/
├── metadata.json          # 每年狀態、股票數、日期區間、檔案大小
└── us_stocks/
    ├── 2005.parquet
    ├── 2006.parquet
    └── ...
```

## 回測使用

回測選「[A] 本地數據回測」時，會從上述路徑依年份讀取，與下載／續跑使用同一目錄，無需另設路徑。
