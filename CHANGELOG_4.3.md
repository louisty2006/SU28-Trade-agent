# REISHI 霊視 v4.3 改動手冊（給同事）

## 一句話

**品牌改為 REISHI（霊視），新增互動啟動選單與回測日期區間，持倉可為空、Stage3「賣出」改為「避開」。**

---

## 1. 品牌與顯示

| 項目 | 變更 |
|------|------|
| 應用名稱 | **REISHI（霊視）**，取代舊名 |
| 開機語 | 「啟動霊視，洞察市場」 |
| 報告標題 | 深度驗證／每日洞察報告皆標示 REISHI 霊視 |
| 輸出檔名 | 仍為 `REIKAN_*`（相容舊報告） |

---

## 2. 互動啟動（無參數執行）

執行 **`python main.py`**（不帶參數）時：

1. 顯示 REISHI banner  
2. 詢問模式：  
   - **[1] 正常 mode**：今日決策（持倉 + 當天思考）→ 等同 `--daily`  
   - **[2] 回測 mode**：輸入**開始日期**與**結束日期**，數據限制在該區間（區間之前看不到）  
   - **[0]**：顯示命令列參數說明  

正常／回測仍可直接用參數：`--daily`、`--backtest YYYY-MM-DD`。

---

## 3. 回測：日期區間

- **以前**：`--backtest 2023-06-15`，單一「截至日」。  
- **現在**：互動選 [2] 可輸入 **開始日 + 結束日**；程式只使用該區間內的數據（區間之前看不到）。  
- 各階段（Stage1/2、daily monitor）取價與財報皆依此區間限制。

---

## 4. 持倉與 Stage3 用語

- **持倉可為空**：不再因「持倉表為空」報錯；無持倉時會依當日掃描給「新標的建議」。  
- **Stage3**：無持倉時，原「賣出」改為 **「避開」**，避免語意混淆。

---

## 5. 常用指令速查

```bash
python main.py              # 互動選單（正常/回測/說明）
python main.py --daily      # 直接跑今日流程
python main.py --backtest 2023-06-15   # 單日回測
python main.py --test-all   # 小樣本 Stage1→2→3
python main.py --daily --positions reports/daily/YYYY-MM-DD/positions_edit.csv  # 指定持倉
```

---

## 6. 報告目錄

- 正常：`reports/daily/YYYY-MM-DD/`  
- 回測：`reports/backtest/YYYY-MM-DD/`（以結束日為目錄名）  
- 報告檔名仍為 `REIKAN_*`，內容與標題為 REISHI 霊視。

---

**版本：v4.3 | REISHI 霊視**
