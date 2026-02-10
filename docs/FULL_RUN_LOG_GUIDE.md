# REISHI v5.4 完整執行日誌 (Full Run Log) 使用指南

## 概述

REISHI v5.4 現在提供完整的執行日誌系統，記錄每個 step 的詳細過程和每個 LLM 呼叫的完整思考過程，讓你能夠透視系統的決策邏輯。

## 功能特性

### 1. 逐步詳細記錄 (Step-by-Step Logging)
- 每個步驟（Step 1-9）都有詳細記錄
- 記錄每步的輸入數據、執行過程、輸出結果
- 記錄每步的執行時間

### 2. LLM 完整思考過程 (Complete LLM Thought Process)
- 記錄每個 LLM 呼叫的完整 Prompt
- 記錄 LLM 原始回應（raw response）
- 記錄解析後的結果（parsed result）
- 記錄所使用的 LLM 提供商和模型

### 3. 數據流向追蹤 (Data Flow Tracking)
- 記錄數據在各 step 間的流向
- 記錄中間數據的樣本和大小
- 幫助理解數據如何轉化為決策

### 4. 統一的 Master Log (Master Flow Log)
- 彙總所有步驟和 LLM 呼叫的統一日誌
- 可視化完整的執行時序
- 包含所有重要的決策點和數據轉變

## 日誌文件結構

每次 daily run 會生成以下日誌：

```
reports/daily/
└── 2026-02-10_154253/                     # 時間戳目錄
    ├── 00_MASTER_FLOW.md                  # ⭐ 完整執行流程日誌
    ├── 01_LLM_CALLS.jsonl                 # LLM 呼叫記錄（JSONL 格式）
    ├── 02_DATA_FLOW.md                    # 數據流向追蹤
    ├── step_01_數據獲取與驗證.md           # Step 1 詳細報告
    ├── step_02_基本面分析.md               # Step 2 詳細報告
    ├── step_03_圖表型態識別.md             # Step 3 詳細報告
    ├── ... (更多步驟報告)
    ├── SUMMARY_REPORT.md                  # 最終摘要報告
    └── (其他臨時文件)
```

### 各文件說明

| 文件 | 說明 | 格式 |
|------|------|------|
| **00_MASTER_FLOW.md** | 完整執行流程，包含所有步驟和 LLM 呼叫的彙總視圖 | Markdown |
| **01_LLM_CALLS.jsonl** | 每行一個 LLM 呼叫記錄，便於後續分析和解析 | JSONL |
| **02_DATA_FLOW.md** | 數據在各步驟間的流向和轉化過程 | Markdown |
| **step_NN_名稱.md** | 第 N 個步驟的詳細報告，包含輸入/輸出/思考過程 | Markdown |
| **SUMMARY_REPORT.md** | 最終的投資建議和決策摘要 | Markdown |

## 如何查看日誌

### 方法 1: 使用 Log Viewer 工具

最簡單的方法是使用提供的 `view_full_run_log.py` 工具：

```bash
# 查看最新日誌的完整流程
python view_full_run_log.py

# 列出所有日誌
python view_full_run_log.py --list

# 查看特定時間戳的日誌
python view_full_run_log.py 2026-02-10_154253

# 分析最新日誌並生成統計
python view_full_run_log.py --analyze

# 查看 LLM 呼叫摘要
python view_full_run_log.py llm

# 查看數據流向
python view_full_run_log.py flow

# 列出所有步驟報告
python view_full_run_log.py steps

# 查看特定步驟報告
python view_full_run_log.py step 3      # 查看 Step 3 報告
```

### 方法 2: 直接查看文件

```bash
# 查看完整執行流程
cat reports/daily/2026-02-10_154253/00_MASTER_FLOW.md

# 查看 LLM 呼叫記錄（JSON 格式）
cat reports/daily/2026-02-10_154253/01_LLM_CALLS.jsonl | jq .

# 查看特定 step 報告
cat reports/daily/2026-02-10_154253/step_03_圖表型態識別.md
```

## 理解 Master Flow Log

Master Flow Log 是最重要的文檔，它包含：

### 1. 執行時序 (Execution Timeline)
```
### [2026-02-10 15:42:53] Step 1: 數據獲取與驗證
**描述**: 從 Yahoo Finance / 多數據源取得 K 線數據，驗證數據有效性
**輸入數據**: ...
**輸出數據**: ...
```

### 2. LLM 思考過程 (LLM Thinking Process)
```
#### 🤖 LLM 呼叫 [Fundamental 分析師] - AAPL

**提供商**: mistral | **模型**: mistral-small-latest

**System Prompt**:
你是一個基本面分析師...

**User Prompt**:
請分析 AAPL 的基本面指標...

**LLM Response**:
AAPL 的 PE 比率為 25.5...

**解析結果**:
{
  "pe_ratio": 25.5,
  "recommendation": "HOLD",
  ...
}
```

### 3. 完整時序表 (Full Timeline)
```
- **[時間]** 🟢 Step 1 開始: 數據獲取與驗證
- **[時間]** 🤖 LLM 呼叫: Fundamental 分析師 (AAPL)
- **[時間]** 🔴 Step 1 完成 (12.34s)
...
```

## LLM 呼叫記錄格式 (JSONL)

每行是一個 JSON 物件，結構如下：

```json
{
  "timestamp": "2026-02-10T15:42:53.123456",
  "step_index": 6,
  "step_name": "Multi-Agent 協作分析",
  "agent_role": "Fundamental 分析師",
  "ticker": "AAPL",
  "provider": "mistral",
  "model": "mistral-small-latest",
  "system_prompt": "你是一個基本面分析師...",
  "user_prompt": "請分析以下股票...",
  "raw_response": "AAPL 的 PE 比率為...",
  "parsed_result": {
    "pe_ratio": 25.5,
    "recommendation": "HOLD",
    "confidence": 0.8
  }
}
```

## 使用案例

### 案例 1: 理解為什麼推薦 BUY AAPL

1. 打開 `00_MASTER_FLOW.md`
2. 搜尋 "AAPL"
3. 查看:
   - Step 3: 圖表型態識別 → AAPL 是否有突破型態
   - Step 6: Multi-Agent 分析 → AAPL 的多角色共識
   - Step 8: 決策引擎 → 為什麼最終決策是 BUY

### 案例 2: 檢查 LLM 是否幻覺

1. 查看 `01_LLM_CALLS.jsonl`
2. 搜尋相關股票的 LLM 呼叫
3. 檢查:
   - user_prompt: 提示是否清晰准確
   - raw_response: LLM 是否按指示回答
   - parsed_result: 解析是否正確

### 案例 3: 追蹤數據轉化過程

1. 查看 `02_DATA_FLOW.md`
2. 追蹤:
   - Step 1 輸出 → Step 3 輸入 (市場數據)
   - Step 3 輸出 → Step 6 輸入 (圖表候選)
   - Step 6 輸出 → Step 8 輸入 (共識)

## 性能監控

Master Flow Log 還記錄了每個 step 的執行時間：

```
**耗時**: 12.34s
```

查看 Master Flow Log 可以快速識別性能瓶頸：

```bash
# 查看各步驟執行時間
grep "耗時" reports/daily/2026-02-10_154253/00_MASTER_FLOW.md
```

## 數據量監控

LLM 呼叫記錄 (`01_LLM_CALLS.jsonl`) 的行數表示 LLM 呼叫次數：

```bash
# 統計 LLM 呼叫次數
wc -l reports/daily/2026-02-10_154253/01_LLM_CALLS.jsonl

# 按 agent role 統計
cat reports/daily/2026-02-10_154253/01_LLM_CALLS.jsonl | jq -r '.agent_role' | sort | uniq -c
```

## 故障排除

### Q: 沒有生成日誌文件
A: 確保已執行 `python main_v5.py --daily`，並檢查 `reports/daily/` 目錄是否存在

### Q: Master Flow Log 為空或不完整
A: 這可能表示：
1. Daily run 在中途出錯，查看 console 輸出或 `debug_run.log`
2. 某些 step 沒有正確記錄，檢查 main_v5.py 中的 log 呼叫

### Q: 如何導出日誌用於外部分析
A: 使用 JSONL 格式的 LLM 呼叫記錄：
```bash
cat reports/daily/2026-02-10_154253/01_LLM_CALLS.jsonl | jq . | less
```

## 最佳實踐

1. **定期查看**: 每日 run 後查看最新日誌，了解系統決策邏輯
2. **比較分析**: 比較不同日期的日誌，識別趨勢變化
3. **驗證假設**: 使用日誌驗證系統是否符合設計預期
4. **性能優化**: 識別時間最長的步驟，進行優化
5. **改進提示**: 基於 LLM 呼叫記錄改進 system/user prompts

## 限制和注意事項

1. **文件大小**: Master Flow Log 可能很大（>10MB），使用 `less` 或編輯器打開
2. **敏感信息**: 日誌中包含完整的 prompt，避免分享包含 API key 的部分
3. **保留時間**: 定期清理舊日誌以節省磁碟空間（建議保留最近 90 天）
4. **實時流**: 日誌在 run 完成後才完整生成，不能用於實時監控

## 相關文檔

- [CLAUDE.md](../CLAUDE.md) - 項目配置和架構
- [API_KEYS_IN_FLOW.md](./API_KEYS_IN_FLOW.md) - API 使用詳情
- [KLINE_DATA_FORMAT.md](./KLINE_DATA_FORMAT.md) - 市場數據格式

---

**版本**: v5.4 (2026-02-10)
