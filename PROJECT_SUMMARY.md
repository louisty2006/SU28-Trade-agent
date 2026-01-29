# 📦 股票掃描系統 v4 - 專案摘要

## 🎯 專案目標

建立一個**三階段漏斗式股票篩選系統**：
1. Stage 1: 從 10,000+ 股票快速篩選出 Top 1,000
2. Stage 2: 深度驗證篩選出 Top 250
3. Stage 3: Multi-Agent LLM 討論產出 Top 20（開發中）

## ✅ 當前進度（v4 初代版）

### 已完成
- ✅ **Stage 1 快速篩選**
  - 100 線程並行處理
  - Yahoo Finance 單數據源
  - 技術指標計算（RSI, MACD, KD, 布林通道）
  - 智能評分系統
  - HTML + CSV 報告輸出

- ✅ **Stage 2 深度驗證**
  - 30 線程並行
  - 多數據源整合（Yahoo + FMP）
  - 財務健康度評估
  - 估值分析
  - 評分優化算法

- ✅ **完整專案架構**
  - 模組化設計
  - 配置文件管理
  - 命令行 + 互動式介面
  - 測試腳本
  - 完整文檔

### 開發中
- 🚧 **Stage 3 Multi-Agent LLM 討論**
  - 需要整合免費 LLM API（Groq, OpenRouter）
  - Multi-Agent 辯論框架
  - 共識算法

## 📂 專案結構

```
stock_scanner_v4/
├── config.py                  # 全局配置
├── main.py                    # 主程式入口
├── test.py                    # 測試腳本
│
├── stage1_quick_scan.py       # Stage 1 主程式
├── stage2_deep_verify.py      # Stage 2 主程式
├── stage3_llm_discuss.py      # Stage 3 主程式（未建立）
│
├── utils/                     # 工具模組
│   ├── __init__.py
│   ├── data_fetcher.py        # 數據獲取
│   ├── indicators.py          # 技術指標
│   └── scoring.py             # 評分邏輯
│
├── requirements.txt           # 依賴套件
├── .env.example              # 環境變數範例
├── README.md                 # 完整說明文檔
├── QUICKSTART.md             # 快速開始指南
│
└── reports/                  # 輸出報告（執行後生成）
    ├── stage1/
    ├── stage2/
    └── test/
```

## 🔧 核心技術

### 技術棧
- **Python 3.8+**
- **數據處理**：pandas, numpy
- **股票數據**：yfinance
- **並行處理**：ThreadPoolExecutor
- **API 請求**：requests

### 數據源（免費版）
- **Yahoo Finance**：主要數據源（無限制）
- **FMP**：財務數據補充（250 calls/day）
- **未來**：Groq, OpenRouter (LLM)

### 核心算法
1. **多維度評分系統**：加權平均 8+ 技術指標
2. **交叉驗證**：多數據源比對
3. **動態閾值**：自適應評分標準

## 📊 性能指標

### Stage 1
- **處理速度**：~500-700 stocks/min
- **預計時間**：15-20 分鐘（10,000 stocks）
- **並行度**：100 線程
- **成功率**：~70-80%（取決於數據可用性）

### Stage 2
- **處理速度**：~50-70 stocks/min
- **預計時間**：10-15 分鐘（1,000 stocks）
- **並行度**：30 線程（API 限速）
- **API 調用**：~2,000 calls (Yahoo + FMP)

## 🎯 使用場景

1. **日常掃描**：每日收盤後執行，找出潛力股
2. **深度研究**：針對特定板塊或條件篩選
3. **回測驗證**：測試策略有效性
4. **學習研究**：了解技術分析和量化選股

## ⚠️ 注意事項

### 限制
- **免費 API 限制**：FMP 每日 250 calls
- **數據延遲**：Yahoo Finance 有 15 分鐘延遲
- **網路依賴**：需要穩定網路連線

### 風險提示
- 本工具僅供參考，不構成投資建議
- 技術指標有滯後性
- 需結合基本面和市場環境判斷

## 🚀 下一步計畫

### 短期（1-2 週）
1. 完成 Stage 3 Multi-Agent LLM 討論
2. 整合免費 LLM API
3. 實作辯論流程

### 中期（1 個月）
1. Web Dashboard（FastAPI + React）
2. 即時監控功能
3. 資料庫持久化

### 長期（2-3 個月）
1. 回測系統
2. 策略優化
3. 自動通知（Telegram/Email）
4. 多語言支援

## 📈 改進方向

### 性能優化
- [ ] 實作快取機制減少重複請求
- [ ] 使用異步 IO 提升速度
- [ ] 增量更新而非全量掃描

### 功能擴展
- [ ] 支援更多市場（A股、台股）
- [ ] 自訂篩選條件 UI
- [ ] 歷史數據回測
- [ ] 投資組合管理

### 數據增強
- [ ] 整合更多免費數據源
- [ ] 新聞情緒分析
- [ ] 社群媒體情緒追蹤

## 💻 開發建議

### 本地開發
```bash
# 虛擬環境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安裝依賴
pip install -r requirements.txt

# 開發模式運行
python test.py
```

### 貢獻指南
1. Fork 專案
2. 創建功能分支
3. 提交變更
4. 發起 Pull Request

## 📞 聯絡方式

- **Issues**: 在 GitHub 提交 Issue
- **Email**: your.email@example.com

---

**版本**：v4.0.0-beta  
**最後更新**：2024-01-29  
**作者**：Claude & You  
**授權**：MIT License
