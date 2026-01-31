# 🔮 REISHI Stock Scanner — 三階段智能篩選

> **洞察本質，智贏未來** · AI Insight, Infinite Returns  
> 霊視市場 · 霊視風險 · 霊視趨勢 · 霊視情緒 — 使用免費 API 驗證三階段架構

**五重視角**：第一視（圖表型態）→ 第二視（情緒分析）→ 第三視（因果推理）→ **第四視（Multi-Agent 集體決策，已上線）** → 第五視（強化學習自適應）。詳見 [BRAND.md](BRAND.md)。

---

## 🎯 系統架構

```
Stage 1: 快速篩選 (15-20分鐘)
10,000+ stocks ──────▶ Top 1,000
         [Yahoo Finance 單源高速掃描]

Stage 2: 深度驗證 (10-15分鐘)  
Top 1,000 ──────▶ Top 250
    [Yahoo + FMP 交叉驗證 + 財務健康度]

Stage 3: Multi-Agent LLM討論 (20-30分鐘) [開發中]
Top 250 ──────▶ Top 20
    [4個LLM協同分析 + 辯論共識]

總耗時: ~50分鐘 | API成本: 免費 (初代版)
```

---

## ✨ 核心特色

### Stage 1: 快速篩選
- ⚡ **100 線程並行**處理，15-20 分鐘掃描 10,000+ 股票
- 📊 **技術指標**：RSI, MACD, KD, 布林通道, 成交量異動
- 🎯 **智能評分**：多維度加權評分系統 (0-100 分)
- 🔍 **自動過濾**：最低價格、成交量、市值門檻

### Stage 2: 深度驗證
- 📡 **多數據源交叉驗證**：Yahoo Finance + FMP
- 💰 **財務健康度**：流動比率、負債比、ROE
- 📈 **估值分析**：PE, PB, 成長性指標
- 🔄 **評分優化**：結合技術面 + 基本面綜合評分

### Stage 3: LLM 討論 (開發中)
- 🤖 **Multi-Agent 架構**：4 個 LLM 協同分析
- 💬 **三輪辯論**：獨立分析 → 交叉質疑 → 形成共識
- 🎯 **最終產出**：Top 20 + 完整投資建議

---

## 🚀 快速開始

### 1️⃣ 環境準備

```bash
# 克隆或下載專案
cd stock_scanner_v4

# 安裝依賴
pip install -r requirements.txt

# 配置環境變數（可選）
cp .env.example .env
# 編輯 .env，填入你的 API Keys（暫時不填也能運行）
```

### 2️⃣ 準備股票池 (可選)

將您的股票清單 CSV 放在以下任一位置：
- `COMPLETE_ALL_STOCKS_FINAL.csv`
- `data/COMPLETE_ALL_STOCKS_FINAL.csv`

CSV 格式：至少包含 `symbol` 欄位
```csv
symbol,market,exchange
AAPL,US,NASDAQ
TSLA,US,NASDAQ
0700.HK,HK,HKEX
```

如果沒有 CSV，系統會使用內建預設清單。

### 3️⃣ 執行掃描

#### 方式 A：互動模式（推薦新手）
```bash
python main.py
```
會出現選單，按提示操作。

#### 方式 B：命令行模式
```bash
# 僅執行 Stage 1
python main.py --stage1

# 僅執行 Stage 2（自動尋找最新 Stage 1 結果）
python main.py --stage2

# 執行 Stage 1 + Stage 2 連續流程
python main.py --all

# 指定 Stage 1 結果執行 Stage 2
python main.py --stage2 --input reports/stage1/xxx/stage1_results.csv
```

#### 方式 C：單獨執行
```bash
# 單獨執行 Stage 1
python stage1_quick_scan.py

# 單獨執行 Stage 2
python stage2_deep_verify.py
```

---

## 📁 輸出結構

```
reports/
├── stage1/
│   └── 2024-01-29_1430_stage1/
│       ├── stage1_results.csv       # Top 1000 數據
│       └── stage1_report.html       # 視覺化報告
│
└── stage2/
    └── 2024-01-29_1500_stage2/
        ├── stage2_results.csv       # Top 250 數據
        └── stage2_report.html       # 深度分析報告
```

---

## ⚙️ 配置說明

### config.py 核心參數

```python
# Stage 1 配置
STAGE1_CONFIG = {
    "max_workers": 100,          # 並行線程數
    "target_output": 1000,       # 輸出 Top 1000
    "min_price": 1.0,            # 最低價格過濾
    "min_volume": 100000,        # 最低成交量
    "min_market_cap": 100_000_000,  # 最低市值
}

# Stage 2 配置
STAGE2_CONFIG = {
    "max_workers": 30,           # 考慮 API 限制
    "target_output": 250,        # 輸出 Top 250
    "use_fmp": True,             # 是否使用 FMP（需 API Key）
    "api_delay": 0.1,            # API 調用延遲
}
```

---

## 🔑 API Keys 說明

### 免費版可用的 API

| API | 免費額度 | 用途 | 註冊連結 |
|-----|---------|------|---------|
| **Yahoo Finance** | 無限制 | Stage 1 & 2 主要數據源 | 無需註冊 |
| **FMP** | 250 calls/day | Stage 2 財務數據補充 | [註冊](https://site.financialmodeprep.com/developer/docs/) |
| Finnhub | 60 calls/min | 新聞數據（v3 功能） | [註冊](https://finnhub.io/) |

### Stage 3 未來需要的 API (暫不使用)
- Groq (免費 LLM)
- OpenRouter (免費額度)
- Claude, GPT-4, Gemini, Perplexity

---

## 📊 評分邏輯

### Stage 1 技術面評分 (0-100)

| 指標 | 權重 | 評分邏輯 |
|-----|------|---------|
| RSI | 20% | 30-40 超賣區 +20, <30 深度超賣 +15 |
| MACD | 15% | 金叉 +15, MACD>0 +8 |
| KD | 12% | K<30 且金叉 +12, K<20 +8 |
| 布林通道 | 10% | 接近下軌(<20%) +10 |
| 成交量 | 8% | 爆量(>2x) +8, 量增(>1.5x) +5 |
| 價格動量 | 15% | 回調不深(-5%~-15%) +10 |
| 52週高低 | 20% | 距高點遠(<-30%) +10 |

### Stage 2 綜合評分

```
Stage 2 評分 = Stage 1 評分 * 30%
             + 財務健康度 * 25%
             + 估值指標 * 20%
             + 成長性 * 15%
             + 新聞情緒 * 10%
```

**財務健康度**：流動比率、負債率、ROE  
**估值指標**：PE, PB  
**成長性**：營收成長、獲利成長

---

## 🛠️ 常見問題

### Q1: 執行時間比預期長？
A: 
- Stage 1 受網路速度影響，可能需要 20-30 分鐘
- 可調整 `max_workers` 降低並行數
- 確保網路連線穩定

### Q2: 沒有 API Key 能運行嗎？
A: 
- **可以！** Yahoo Finance 免費無限制
- FMP API Key 只是補充數據，非必需
- Stage 1 完全不需要 API Key

### Q3: 如何添加自己的股票清單？
A:
1. 準備 CSV，至少包含 `symbol` 欄位
2. 放在專案根目錄或 `data/` 資料夾
3. 命名為 `COMPLETE_ALL_STOCKS_FINAL.csv`

### Q4: 報告在哪裡？
A:
- `reports/stage1/` - Stage 1 結果
- `reports/stage2/` - Stage 2 結果
- 每次執行會創建新的時間戳記資料夾

---

## 🔮 未來計畫 (v4 完整版)

- [ ] **Stage 3 Multi-Agent LLM 討論**
  - [ ] Groq API 整合
  - [ ] OpenRouter 整合
  - [ ] 辯論流程實作
  - [ ] 共識算法

- [ ] **Web Dashboard**
  - [ ] FastAPI 後端
  - [ ] React 前端
  - [ ] 即時進度顯示
  - [ ] 互動式圖表

- [ ] **進階功能**
  - [ ] 歷史回測
  - [ ] 策略優化
  - [ ] 自動通知（Telegram/Email）
  - [ ] 資料庫持久化

---

## 📝 版本歷史

### v4.0.0-beta (2024-01-29)
- ✅ 完成 Stage 1 快速篩選
- ✅ 完成 Stage 2 深度驗證
- ✅ 100 線程並行優化
- ✅ 多數據源整合 (Yahoo + FMP)
- 🚧 Stage 3 開發中

### v3.1 (舊版)
- 單階段掃描
- HTML 報告生成
- Finnhub 新聞整合

---

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

---

## 📄 授權

MIT License

---

## ⚠️ 免責聲明

本工具僅供教育和研究用途。  
股票投資有風險，請自行判斷並承擔投資決策責任。  
本工具不構成任何投資建議。

---

**Made with ❤️ by Claude & You**
