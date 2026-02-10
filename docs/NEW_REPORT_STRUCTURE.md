# REISHI v5.4 新報告結構 (Runs-Based Organization)

## 📂 新的目錄組織方式

從 v5.4 開始，報告文件組織方式已更改，現在所有運行的文件都**集中在 `reports/runs/` 目錄下**，而不是分散在 `reports/daily/` 中。

### 舊結構 (已棄用)
```
reports/
├── daily/
│   ├── 2026-02-10_154253.md          # 摘要
│   ├── 2026-02-10_154253/            # 完整日誌
│   │   ├── 00_MASTER_FLOW.md
│   │   └── ...
│   └── ...
├── backtest_range/
└── monitor/
```

### 新結構 (v5.4+) ✨
```
reports/
├── runs/                              # ⭐ 所有運行集中在這
│   ├── INDEX.md                       # 📋 所有 runs 的索引（自動生成）
│   ├── runs_metadata.json             # 📊 元數據 JSON（用於分析）
│   │
│   ├── 2026-02-10_154253/             # Run 1: 完整日誌目錄
│   │   ├── 00_MASTER_FLOW.md          # ⭐ 完整執行流程
│   │   ├── 01_LLM_CALLS.jsonl         # 🤖 LLM 呼叫記錄
│   │   ├── 02_DATA_FLOW.md            # 🔄 數據流向
│   │   ├── step_01_數據獲取.md
│   │   ├── step_02_基本面分析.md
│   │   ├── ...
│   │   ├── step_08_決策引擎.md
│   │   └── SUMMARY_REPORT.md          # 📄 最終報告
│   │
│   ├── 2026-02-10_142025/             # Run 2: 同樣結構
│   │   ├── 00_MASTER_FLOW.md
│   │   ├── ...
│   │   └── SUMMARY_REPORT.md
│   │
│   ├── 2026-02-10_123522/             # Run 3: ...
│   │   └── ...
│   │
│   └── ... (更多 runs)
│
├── backtest/                          # Backtest 報告（暫時未變)
│   ├── 2025-01-01_to_2025-12-31/
│   └── ...
│
└── monitor/                           # Monitor 報告
    └── ...
```

## 🎯 核心特性

### 1. **集中化管理**
- 所有 daily runs 都在 `reports/runs/` 下
- 用 timestamp 作為目錄名，自動排序
- 每個 run 的所有文件都在同一個 folder 中

### 2. **自動索引生成** ✨
- 每次 run 完成後，自動生成 `INDEX.md`
- 列出所有 runs 及其快速信息
- 提供快速導航和查看命令

### 3. **元數據追蹤** 📊
- `runs_metadata.json` 記錄所有 runs 的統計信息
- 包含：LLM 呼叫次數、文件大小、step 數量等
- 便於外部工具分析

---

## 🚀 如何使用

### 查看索引 (推薦)
```bash
# 查看所有 runs 的索引和摘要
python view_runs.py

# 或直接打開索引文件
open reports/runs/INDEX.md
```

### 查看特定 Run
```bash
# 查看最新 run 的信息
python view_runs.py latest

# 查看特定 run 的信息
python view_runs.py 2026-02-10_154253

# 查看最新 run 的完整流程
python view_runs.py latest master

# 查看最新 run 的最終報告
python view_runs.py latest summary

# 查看特定 run 的 LLM 摘要
python view_runs.py 2026-02-10_154253 llm
```

### 直接查看文件
```bash
# 查看最新 run 的完整流程
cat reports/runs/$(ls -t reports/runs | grep -v INDEX | grep -v metadata | head -1)/00_MASTER_FLOW.md

# 簡化版（使用別名）
alias view-latest='cat reports/runs/$(ls -t reports/runs | grep -v INDEX | grep -v metadata | head -1)'
view-latest/00_MASTER_FLOW.md

# 查看 LLM 呼叫記錄
cat reports/runs/2026-02-10_154253/01_LLM_CALLS.jsonl | jq .
```

---

## 📋 INDEX.md 說明

自動生成的 `INDEX.md` 包含：

### 摘要表格
```markdown
| 時間 | 文件數 | LLM 呼叫 | 大小 | 快速查看 |
|------|--------|---------|------|---------|
| 2026-02-10 15:42:53 | 12 | 24 | 8.5 MB | [查看](#run-2026-02-10_154253) |
```

### 詳細記錄
- 每個 run 的完整文件列表
- 大小統計
- LLM 呼叫次數
- 快速命令

---

## 📊 runs_metadata.json 格式

```json
[
  {
    "timestamp": "2026-02-10_154253",
    "datetime": "2026-02-10 15:42:53",
    "path": "2026-02-10_154253",
    "files": {
      "master_flow": {"exists": true, "size_bytes": 2145000, "size_kb": 2094.2},
      "llm_calls": {"exists": true, "size_bytes": 1250000, "size_kb": 1220.7},
      "data_flow": {"exists": true, "size_bytes": 450000, "size_kb": 439.5},
      "summary_report": {"exists": true, "size_bytes": 8500, "size_kb": 8.3}
    },
    "step_count": 8,
    "llm_calls_count": 24,
    "total_size_bytes": 3853500,
    "total_size_mb": 3.7
  },
  ...
]
```

**用途**：
- 數據分析：分析 LLM 使用趨勢
- 性能監控：追蹤執行時間、文件大小
- 外部集成：導入到 BI 工具或數據庫

---

## 🔍 快速命令速查表

| 用途 | 命令 |
|------|------|
| 查看所有 runs | `python view_runs.py` |
| 查看最新 run | `python view_runs.py latest` |
| 查看最新完整流程 | `python view_runs.py latest master` |
| 查看最新最終報告 | `python view_runs.py latest summary` |
| 查看最新 LLM 摘要 | `python view_runs.py latest llm` |
| 查看特定 run | `python view_runs.py 2026-02-10_154253` |
| 直接打開索引 | `open reports/runs/INDEX.md` |
| 查看元數據 | `cat reports/runs/runs_metadata.json \| jq .` |

---

## 🛠️ 開發者說明

### 如何更新索引

```python
from reporting.run_index_generator import update_run_index

# 手動更新索引（通常在 run 完成後自動調用）
update_run_index()
```

### 自動集成

索引在 `main_v5.py` 的 `run_daily()` 方法中自動調用：

```python
# 完成完整運行日誌記錄
master_flow_logger.finalize()
summary = master_flow_logger.get_summary()

# 更新運行索引 (自動)
update_run_index()
```

### 添加自定義元數據

如需為每個 run 添加自定義元數據，修改 `RunIndexGenerator._extract_run_info()` 方法。

---

## 📈 遷移舊數據

如果你有舊的 `reports/daily/` 目錄，可以遷移到新結構：

```bash
# 1. 創建新目錄
mkdir -p reports/runs

# 2. 複製舊日誌
cp reports/daily/*/  reports/runs/

# 3. 更新索引
python -c "from reporting.run_index_generator import update_run_index; update_run_index()"

# 4. （可選）刪除舊目錄
rm -rf reports/daily/*_*/
```

---

## 💾 磁碟清理

### 查看大小
```bash
# 查看 runs 目錄大小
du -sh reports/runs/

# 查看單個 run 大小
du -sh reports/runs/2026-02-10_154253/

# 查看最大的 runs
du -sh reports/runs/*/ | sort -rh | head -10
```

### 清理舊 runs
```bash
# 刪除 30 天以上的 runs
find reports/runs -maxdepth 1 -type d -mtime +30 -exec rm -rf {} \;

# 刪除特定 run
rm -rf reports/runs/2026-02-01_120000/
```

---

## 🔗 相關文檔

- [FULL_RUN_LOG_GUIDE.md](./FULL_RUN_LOG_GUIDE.md) — 完整日誌系統詳解
- [REPORT_GENERATION_OVERVIEW.md](./REPORT_GENERATION_OVERVIEW.md) — 報告類型詳解
- [CLAUDE.md](../CLAUDE.md) — 項目配置

---

## 常見問題

### Q: 為什麼改變了目錄結構?
A: 新結構更清晰，所有 run 的文件都在同一個 folder，方便查看和管理。同時自動索引和元數據使得批量分析更容易。

### Q: 舊的 runs 還能查看嗎?
A: 可以，但需要手動導航。建議用遷移腳本將舊數據移到新結構。

### Q: 索引多久更新一次?
A: 每次 run 完成後自動更新，無需手動操作。

### Q: 可以禁用自動索引生成嗎?
A: 可以，在 `main_v5.py` 中註釋掉 `update_run_index()` 呼叫。

---

**版本**: v5.4 (2026-02-10)
**狀態**: ✅ 生產就緒
