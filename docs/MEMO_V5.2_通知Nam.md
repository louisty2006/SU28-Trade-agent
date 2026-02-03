# REISHI v5.2 更新備忘與通知 Nam

## 一、更新內容摘要

- **版本**：v5.1.2 → **v5.2**
- **數據管理**  
  - 下載／續跑都在同一資料夾 `data/market_data/us_stocks/`，按年存檔（`2005.parquet` … `2025.parquet`）。  
  - 中斷後再執行會從上次 partial 繼續，不會從頭開始。  
  - 需安裝 Parquet 引擎（`pip install pyarrow`）；若未安裝，程式會提示並不會開始下載。
- **狀態表即時更新**  
  - 進入數據管理時，K 線表格會依目前檔案即時顯示。  
  - 每次下載或修復完成後，會自動重新整理「年份／狀態／股票數／完整度」，選 [B] 時每完成一年也會更新一次。
- **依賴**：`requirements.txt` 已加入 `pyarrow`；`.gitignore` 已忽略 `data/market_data/`。

詳細變更見：`docs/changelogs/V5.2.md`。

---

## 二、通知 Nam 用範本（可複製傳送）

```
Nam，

REISHI 已更新到 v5.2 並推到 GitHub（branch: v5.2）。

本版重點：
・數據管理：下載與續跑都在同一個資料夾（data/market_data/us_stocks/），按年份存檔；中斷後再跑會從上次進度繼續。
・狀態表會即時更新：進入選單或每次下載/修復後，會自動刷新「年份／狀態／股票數／完整度」。
・需安裝 pyarrow 才能寫入 Parquet（pip install pyarrow）；若未安裝會先提示再開始下載。

Repo: https://github.com/akidennisleung/stock-scanner
分支: v5.2
變更說明: docs/changelogs/V5.2.md
```

---

*備忘日期：2025-01-30*
