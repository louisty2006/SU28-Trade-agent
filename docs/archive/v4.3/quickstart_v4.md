# 🚀 快速開始指南

## 5 分鐘上手

### 步驟 1️⃣：安裝依賴

```bash
pip install -r requirements.txt
```

### 步驟 2️⃣：快速測試（推薦）

用 10 支股票測試系統是否正常：

```bash
python test.py
```

預計耗時：< 1 分鐘  
如果測試通過，說明系統運作正常！

### 步驟 3️⃣：開始正式掃描

#### 選項 A：互動模式（最簡單）

```bash
python main.py
```

會出現選單，選擇你要的模式：
- 1️⃣ 僅 Stage 1 (快速篩選)
- 2️⃣ 僅 Stage 2 (深度驗證)
- 3️⃣ Stage 1 + 2 (連續執行)

#### 選項 B：一鍵執行全流程

```bash
python main.py --all
```

自動執行 Stage 1 + Stage 2，中間會暫停讓你確認。

---

## 📊 查看結果

結果會儲存在 `reports/` 資料夾：

```
reports/
├── stage1/
│   └── 2024-01-29_1430_stage1/
│       ├── stage1_results.csv    ← 打開這個看數據
│       └── stage1_report.html    ← 打開這個看報告
│
└── stage2/
    └── 2024-01-29_1500_stage2/
        ├── stage2_results.csv
        └── stage2_report.html
```

**直接雙擊 `.html` 文件**就能在瀏覽器看到精美報告！

---

## ⚙️ 可選：配置 API Keys

如果你想使用額外的數據源（非必需）：

1. 複製環境變數範例：
```bash
cp .env.example .env
```

2. 編輯 `.env`，填入你的 API Keys：
```bash
# 免費註冊 Financial Modeling Prep
FMP_API_KEY=your_api_key_here
```

**不填也能運行！** Yahoo Finance 已經夠用了。

---

## 🎯 準備股票清單（可選）

如果你有自己的股票清單 CSV：

1. 確保 CSV 有 `symbol` 欄位
2. 放在專案根目錄，命名為：`COMPLETE_ALL_STOCKS_FINAL.csv`

範例格式：
```csv
symbol,market,exchange
AAPL,US,NASDAQ
MSFT,US,NASDAQ
TSLA,US,NASDAQ
```

**沒有 CSV 也沒關係！** 系統會自動用內建股票清單。

---

## 🆘 遇到問題？

### 錯誤：ModuleNotFoundError
```bash
pip install -r requirements.txt
```

### 錯誤：找不到股票數據
- 檢查網路連線
- Yahoo Finance 可能暫時故障，稍後再試

### 執行太慢
- 降低並行數：編輯 `config.py`
```python
STAGE1_CONFIG = {
    "max_workers": 50,  # 改小一點
}
```

---

## 💡 Pro Tips

1. **先跑測試**：確保系統正常
```bash
python test.py
```

2. **分段執行**：可以先跑 Stage 1，看完結果再決定是否跑 Stage 2
```bash
python main.py --stage1
# 查看結果，滿意後再：
python main.py --stage2
```

3. **自訂篩選條件**：編輯 `config.py` 調整參數
```python
STAGE1_CONFIG = {
    "min_price": 5.0,        # 只看 $5 以上的股票
    "min_market_cap": 1e9,   # 只看市值 > 10 億的
}
```

---

**準備好了嗎？開始掃描吧！** 🚀

```bash
python test.py
```
