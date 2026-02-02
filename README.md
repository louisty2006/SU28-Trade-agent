# 🔮 REISHI 霊視 Stock Scanner — v5.0

AI 完整決策系統：五層防護、五大分析方向、決策引擎與即時監控；支援 Orchestrator 回測對接。

---

## 快速開始

```bash
pip install -r requirements.txt
cp V5.0_config.yaml.example config.yaml   # 可選：自訂掃描列表等
cp .env.example .env                      # 填入 API Key（見下方）

# 每日分析
python main_v5.py --daily

# 回測（Orchestrator 對接）
python main_v5.py --backtest 2025-01-01 2025-01-31

# 即時監控 / 統計
python main_v5.py --monitor
python main_v5.py --stats
```

---

## API Key 與流程（簡要）

v5.0 每日分析與回測會用到以下 Key；**回測模式**僅需 `config.json`（可選），不強制 API Key。

| 類型 | 環境變數（.env） | 用途 |
|------|------------------|------|
| **LLM（至少一個即可）** | `SCITELY_API_KEY`, `COHERE_API_KEY`, `MISTRAL_API_KEY`, `OPENROUTER_API_KEY` | 決策、防幻覺、型態/情緒/Multi-Agent 等；Key 不足時單一 LLM 兼多角 |
| **數據源（可選）** | `IEX_CLOUD_API_KEY`, `FMP_API_KEY`, `TWELVE_DATA_API_KEY`, … | 多數據源驗證；不設則用 yfinance |
| **通知（可選）** | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | 每日報告與即時警報；不設則跳過發送 |

**流程中 Key 使用位置**：數據獲取 → 型態識別 → 因果推理 → 情緒分析 → Multi-Agent → 霊視記憶 → 決策引擎 → 輸出驗證 → 最終審計 → 報告/通知。  
完整步驟與模組對照見 **[docs/API_KEYS_IN_FLOW.md](docs/API_KEYS_IN_FLOW.md)**。

---

## 給回測 / Orchestrator 同事 — v5.0 注意事項

- **介面不變**：輸入仍為 `config.json`，輸出仍為 `backtest_summary.csv`、`backtest_trades.csv`（欄位一致），**Orchestrator 讀取邏輯無需修改**。
- **本分支唯一入口**：`python main_v5.py --backtest START_DATE END_DATE`（固定兩個日期）。  
  範例配置：複製 `V5.0_config.json.example` 為 `config.json`，或由 Orchestrator 寫入 `config.json`。
- **初始資金**：預設 40,000 HKD，可由 `config.json` 的 `backtest_initial_cash` 覆寫。
- **評分與成本**：Sortino、MDD、交易成本等由 **Orchestrator** 計算；v5.0 只產出原始 CSV。
- 若需「完整 pipeline 逐日回測」（Stage 1→2→3 + 持倉監控），請使用 **v4.3 分支**；v5.0 回測為獨立簡化模組，產出格式與 v4.3 相同。

詳見：**[docs/guides/V5.0_BACKTEST_ORCHESTRATOR_NOTES.md](docs/guides/V5.0_BACKTEST_ORCHESTRATOR_NOTES.md)**、**[docs/guides/V5.0_ORCHESTRATOR_INTEGRATION.md](docs/guides/V5.0_ORCHESTRATOR_INTEGRATION.md)**。

---

## 配置檔說明

| 檔案 | 說明 |
|------|------|
| `V5.0_config.yaml.example` | 每日分析用（掃描列表等）；使用時複製為 `config.yaml` |
| `V5.0_config.json.example` | 回測/Orchestrator 用；使用時複製為 `config.json` |
| `.env` | API Key（從 `.env.example` 複製並填入） |

---

## 文件導覽

- **[V5.0 快速開始](docs/guides/V5.0_QUICKSTART.md)**  
- **[API Key 流程（完整）](docs/API_KEYS_IN_FLOW.md)**  
- **[V5.0 回測說明](docs/guides/V5.0_BACKTEST_GUIDE.md)**  
- **[Orchestrator 對接契約](docs/guides/V5.0_ORCHESTRATOR_INTEGRATION.md)**  
- **[v4.3→v5.0 回測注意事項](docs/guides/V5.0_BACKTEST_ORCHESTRATOR_NOTES.md)**  
- **[文件中心](docs/README.md)**

---

**REISHI 霊視 v5.0** — AI 決策 + Orchestrator 回測對接
