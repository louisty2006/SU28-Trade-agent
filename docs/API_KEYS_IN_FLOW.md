# REISHI 霊視 v5.0 - API Key 流程與使用位置（完整版）

依 v5.0 設計，**流程中每一步**都會使用多個 API Key（數據源、新聞、LLM、通知）。  
下表與流程圖標示為「完整實作時」各步驟會用到的 Key。

---

## 一、總覽流程圖（每一步對應的 API Key）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    REISHI v5.0 每日分析流程（含 API Key 使用點）               │
└─────────────────────────────────────────────────────────────────────────────┘

  [1] 數據獲取與驗證
       │
       │   API Keys:
       │   • 數據源: IEX_CLOUD_API_KEY, FMP_API_KEY, TWELVE_DATA_API_KEY,
       │            POLYGON_API_KEY, FINNHUB_API_KEY, TIINGO_API_KEY,
       │            INTRINIO_API_KEY, ALPHA_VANTAGE_API_KEY, MARKETSTACK_API_KEY,
       │            QUANDL_API_KEY, YAHOO_FINANCE_API_KEY（可選）
       │   模組: main_v5._fetch_and_validate_data() → utils.data_fetcher → config
       ▼
  [2] 圖表型態識別（規則偵測 + LLM 看圖驗證）
       │
       │   API Keys:
       │   • LLM（技術面驗證）: SCITELY_API_KEY, COHERE_API_KEY,
       │                        MISTRAL_API_KEY, OPENROUTER_API_KEY（fallback）
       │   模組: analysis.pattern_recognition.PatternRecognition
       ▼
  [3] 因果推理（新聞影響 + 組合風險）
       │
       │   API Keys:
       │   • 新聞/事件: FINNHUB_API_KEY（新聞）, 或 Alpha Vantage / 其他新聞源
       │   • LLM（因果鏈）: SCITELY_API_KEY, COHERE_API_KEY, MISTRAL_API_KEY,
       │                   OPENROUTER_API_KEY
       │   • 知識圖譜可接: FMP_API_KEY（公司/供應鏈資料）
       │   模組: analysis.causal_reasoning.CausalReasoning, analysis.knowledge_graph
       ▼
  [4] 情緒分析（LLM 情緒分析）
       │
       │   API Keys:
       │   • 新聞/情緒數據: FINNHUB_API_KEY, ALPHA_VANTAGE_API_KEY（新聞/情緒）
       │   • LLM: SCITELY_API_KEY, COHERE_API_KEY, MISTRAL_API_KEY,
       │          OPENROUTER_API_KEY
       │   模組: analysis.sentiment_analysis.SentimentAnalyzer
       ▼
  [5] Multi-Agent 協作分析（四角：基本面 / 技術 / 風險 / 宏觀）
       │
       │   API Keys:
       │   • 基本面: SCITELY_API_KEY
       │   • 技術面: COHERE_API_KEY
       │   • 風險: MISTRAL_API_KEY
       │   • 宏觀: OPENROUTER_API_KEY
       │   （Key 不足時依 core.llm_clients.FALLBACK_ORDER 單一 LLM 兼多角）
       │   模組: analysis.multi_agent.MultiAgentAnalysis
       ▼
  [6] 霊視記憶參考（經驗累積、類似案例、洞察提取）
       │
       │   API Keys:
       │   • LLM（摘要/洞察）: SCITELY_API_KEY, COHERE_API_KEY, MISTRAL_API_KEY,
       │                      OPENROUTER_API_KEY
       │   模組: memory.reishi_memory.ReishiMemory
       ▼
  [7] 決策引擎（防幻覺 + 綜合決策）
       │
       │   API Keys:
       │   • 四角 LLM: SCITELY_API_KEY, COHERE_API_KEY, MISTRAL_API_KEY,
       │              OPENROUTER_API_KEY
       │   模組: core.decision_engine.DecisionEngine → core.anti_hallucination.LLMClients
       ▼
  [8] 輸出驗證（邏輯與數字檢查，可含 LLM 回溯驗證）
       │
       │   API Keys:
       │   • LLM（可選回溯驗證）: SCITELY_API_KEY, COHERE_API_KEY, MISTRAL_API_KEY,
       │                         OPENROUTER_API_KEY
       │   模組: core.output_validator.OutputValidator
       ▼
  [9] 最終審計（最後一道 LLM 檢查，只檢查不判斷）
       │
       │   API Keys:
       │   • LLM（審計員）: SCITELY_API_KEY, COHERE_API_KEY, MISTRAL_API_KEY,
       │                   OPENROUTER_API_KEY
       │   模組: core.final_auditor.FinalAuditor
       ▼
  生成報告
       │
       │   API Keys:
       │   • 通知: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
       │   模組: reporting.daily_report, monitoring.notification_service.TelegramNotifier
       ▼
  結束
```

---

## 二、各步驟與 API Key 對照表（完整版）

| 步驟 | 功能 | 使用的 API Key | 模組/檔案 |
|------|------|----------------|-----------|
| [1] | 數據獲取與驗證 | IEX_CLOUD_API_KEY, FMP_API_KEY, TWELVE_DATA_API_KEY, POLYGON_API_KEY, FINNHUB_API_KEY, TIINGO_API_KEY, INTRINIO_API_KEY, ALPHA_VANTAGE_API_KEY, MARKETSTACK_API_KEY, QUANDL_API_KEY, YAHOO_FINANCE_API_KEY（可選） | main_v5.py, utils/data_fetcher.py, config.py |
| [2] | 圖表型態識別 | SCITELY_API_KEY, COHERE_API_KEY, MISTRAL_API_KEY, OPENROUTER_API_KEY（LLM 看圖驗證） | analysis/pattern_recognition.py |
| [3] | 因果推理 | FINNHUB_API_KEY（新聞）, FMP_API_KEY（公司/供應鏈）, SCITELY / COHERE / MISTRAL / OPENROUTER（LLM 因果鏈） | analysis/causal_reasoning.py, analysis/knowledge_graph.py |
| [4] | 情緒分析 | FINNHUB_API_KEY, ALPHA_VANTAGE_API_KEY（新聞/情緒數據）, 四組 LLM Key | analysis/sentiment_analysis.py |
| [5] | Multi-Agent | SCITELY_API_KEY（基本面）, COHERE_API_KEY（技術）, MISTRAL_API_KEY（風險）, OPENROUTER_API_KEY（宏觀） | analysis/multi_agent.py, core/llm_clients.py |
| [6] | 霊視記憶 | 四組 LLM Key（摘要/洞察提取） | memory/reishi_memory.py |
| [7] | 決策引擎 | SCITELY_API_KEY, COHERE_API_KEY, MISTRAL_API_KEY, OPENROUTER_API_KEY | core/decision_engine.py, core/anti_hallucination.py, core/llm_clients.py |
| [8] | 輸出驗證 | 四組 LLM Key（可選回溯驗證） | core/output_validator.py |
| [9] | 最終審計 | 四組 LLM Key（審計員） | core/final_auditor.py |
| 報告/通知 | 每日報告與即時警報 | TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID | main_v5.py, monitoring/notification_service.py |

---

## 三、API Key 依類型彙總

| 類型 | 環境變數 | 出現於流程步驟 |
|------|----------|----------------|
| 數據源 | IEX_CLOUD_API_KEY, FMP_API_KEY, TWELVE_DATA_API_KEY, POLYGON_API_KEY, FINNHUB_API_KEY, TIINGO_API_KEY, INTRINIO_API_KEY, ALPHA_VANTAGE_API_KEY, MARKETSTACK_API_KEY, QUANDL_API_KEY, YAHOO_FINANCE_API_KEY | [1] 數據獲取；[3][4] 新聞/情緒若接外部 API |
| LLM（四角） | SCITELY_API_KEY, COHERE_API_KEY, MISTRAL_API_KEY, OPENROUTER_API_KEY | [2][3][4][5][6][7][8][9] |
| 通知 | TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID | 報告與警報發送 |

---

## 四、說明

- **數據 Key**：步驟 [1] 必用（多數據源驗證）；[3][4] 若接新聞/情緒 API 時使用。
- **LLM Key**：設計上 [2]～[9] 皆可能呼叫 LLM；實作可共用 `core/llm_clients.py`，Key 不足時由單一 LLM 兼多角（fallback）。
- **Telegram**：僅用於報告與即時警報；未設定則跳過發送，不影響主流程。
