# 持倉表 positions.csv 說明

持倉表用於**每日監控**與**今日決策報告**。請依實際持倉編輯 `positions.csv`。

## 欄位

| 欄位 | 必填 | 說明 |
|------|------|------|
| ticker | ✅ | 股票代碼，如 AAPL、NVDA |
| buy_date | ✅ | 買入日期，格式 YYYY-MM-DD |
| buy_price | ✅ | 買入均價（數字） |
| quantity | ✅ | 持股數量（整數） |
| target_price | 選填 | 目標價，達標可考慮獲利了結 |
| stop_loss | 選填 | 止損價，觸及建議出場 |
| notes | 選填 | 備註，如「Stage3 建議買入」、報告路徑等 |

## 範例

```csv
ticker,buy_date,buy_price,quantity,target_price,stop_loss,notes
AAPL,2026-01-15,250.0,10,280,,Stage3 建議買入
NVDA,2026-01-20,190.0,5,220,175,
```

- 未填 target_price / stop_loss 時，腳本仍會計算盈虧與持倉天數，決策建議會以「持有／減碼／出場」等簡單邏輯為主。
- 之後可與 Stage 3 報告綁定（notes 或另欄記錄來源報告）。
