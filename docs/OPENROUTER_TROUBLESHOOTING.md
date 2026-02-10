# OpenRouter 連接問題排查指南

## 🔍 快速診斷

首先運行診斷工具：

```bash
python test_openrouter.py
```

這會檢查：
1. ✅ API Key 是否設置
2. ✅ 網絡連接是否正常
3. ✅ OpenRouter API 是否可用
4. ✅ 認證是否成功
5. ✅ 其他 fallback providers

---

## ❌ 常見問題和解決方案

### 問題 1: API Key 未設置

**症狀**:
```
❌ OPENROUTER_API_KEY 未設置
```

**解決方案**:
```bash
# 1. 在 .env 文件中設置 API Key
echo "OPENROUTER_API_KEY=sk-or-v1-xxxxxxxx" >> .env

# 2. 確認設置成功
cat .env | grep OPENROUTER_API_KEY
```

**注意**:
- API Key 應該以 `sk-or-v1-` 開頭
- 不要在 Git 中提交 .env 文件（已在 .gitignore 中）

---

### 問題 2: API Key 無效或過期

**症狀**:
```
❌ 認證失敗 (401)
可能原因:
1. API Key 無效或過期
2. API Key 有額度限制已用完
```

**解決方案**:

1. **檢查 API Key 是否有效**:
   - 訪問 https://openrouter.ai/account
   - 查看 "API Keys" 部分
   - 確保你的 key 仍然有效（未被刪除）

2. **檢查額度**:
   - 在 OpenRouter 帳戶中查看 "Credits" 部分
   - 如果額度為 0，需要充值
   - OpenRouter 提供免費 credits 給新用戶，檢查是否有可用的免費模型

3. **生成新 Key**:
   - 如果 key 過期，在帳戶中生成新的 API Key
   - 更新 .env 文件

4. **使用免費模型**:
   ```bash
   # 編輯 .env 使用免費模型
   OPENROUTER_MODEL=meta-llama/llama-3.2-3b-instruct:free
   ```

---

### 問題 3: 網絡連接問題

**症狀**:
```
❌ 無法訪問 openrouter.ai
```

**原因和解決方案**:

1. **檢查網絡連接**:
   ```bash
   # 測試網絡
   ping google.com

   # 測試 OpenRouter 連接
   curl -I https://openrouter.ai
   ```

2. **檢查防火牆/代理**:
   - 某些企業網絡可能阻止外部 API 調用
   - 嘗試使用 VPN
   - 或配置代理設置

3. **檢查 DNS 解析**:
   ```bash
   # 檢查 DNS
   nslookup openrouter.ai
   ```

---

### 問題 4: 請求超時

**症狀**:
```
❌ 請求超時 (30 秒)
```

**原因和解決方案**:

1. **網絡速度慢**:
   - 嘗試更換網絡
   - 檢查網速

2. **OpenRouter 服務響應慢**:
   - 檢查 OpenRouter 狀態頁面: https://status.openrouter.ai
   - 使用更快的模型（例如 llama-3.2-3b:free）

3. **增加超時時間**:
   ```python
   # 在 core/llm_clients.py 中修改
   timeout = 120  # 改為 300（5分鐘）
   ```

---

### 問題 5: 速率限制 (429)

**症狀**:
```
❌ 請求過於頻繁 (429)
可能原因: 超過速率限制
```

**解決方案**:

1. **等待重試**:
   - OpenRouter 有速率限制
   - 等待 1-5 分鐘後重試

2. **使用免費模型**:
   - 免費模型通常限制較少
   ```bash
   OPENROUTER_MODEL=meta-llama/llama-3.2-3b-instruct:free
   ```

3. **分批處理**:
   - 不要一次性處理太多股票
   - 使用 `--quick` 模式進行回測

---

### 問題 6: 502/503 服務不可用

**症狀**:
```
❌ 服務暫時不可用 (502/503)
OpenRouter 服務可能正在維護
```

**解決方案**:
- 檢查 OpenRouter 狀態: https://status.openrouter.ai
- 等待服務恢復
- 使用其他 provider 作為 fallback（例如 Mistral, Ollama）

---

## 🔄 配置 Fallback Providers

如果 OpenRouter 無法使用，系統會自動嘗試其他 providers。確保至少配置了一個：

### Mistral (推薦)
```bash
# .env 文件
MISTRAL_API_KEY=your_mistral_key
MISTRAL_MODEL=mistral-small-latest
```
- 官網: https://mistral.ai
- 配置相對簡單
- 性能不錯

### Ollama (本地)
```bash
# .env 文件
OLLAMA_API_KEY=dummy  # Ollama 不需要真實 key
OLLAMA_MODEL=deepseek-r1:14b
```
- 安裝: https://ollama.ai
- 完全離線運行
- 推薦用於開發/測試

### 檢查可用的 Providers

```bash
python test_openrouter.py
# 會顯示：
# MISTRAL    ✅ 可用
# OLLAMA     ❌ 未設置
# OPENROUTER ❌ 未設置
```

---

## 📊 OpenRouter API 狀態檢查

### 在線狀態頁面
- https://status.openrouter.ai
- 檢查服務是否正在維護

### 官方文檔
- https://openrouter.ai/docs
- 檢查 API 格式是否有變化

### 帳戶管理
- https://openrouter.ai/account
- 檢查 API Keys
- 檢查額度和使用情況

---

## 🛠️ 高級診斷

### 查看詳細日誌

```bash
# 查看最近的 debug 日誌
tail -100 debug_run.log | grep -i "openrouter\|error\|failed"

# 查看 LLM 呼叫記錄
cat reports/runs/[timestamp]/01_LLM_CALLS.jsonl | grep openrouter
```

### 測試單個 LLM 呼叫

```python
from core.llm_clients import LLMClients

client = LLMClients()
response, provider = client.call(
    prompt="Say 'hello'",
    provider_hint="openrouter"
)
print(f"Provider: {provider}")
print(f"Response: {response}")
```

### 啟用詳細日誌

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 現在所有 LLM 調用都會被記錄
```

---

## 💡 最佳實踐

### 1. 配置多個 Providers

```bash
# .env
MISTRAL_API_KEY=sk-...
OPENROUTER_API_KEY=sk-or-v1-...
OLLAMA_API_KEY=dummy
```

系統會自動 fallback，確保可用性。

### 2. 使用免費模型

```bash
# 開發/測試階段使用免費模型
OPENROUTER_MODEL=meta-llama/llama-3.2-3b-instruct:free
```

### 3. 監控 Fallback 順序

```bash
# core/llm_clients.py
FALLBACK_ORDER: List[str] = [
    "mistral",       # 第一選擇
    "openrouter",    # 第二選擇
    "ollama",        # 第三選擇（本地）
]
```

### 4. 設置合理的超時

```python
# 不同場景的超時設置
daily_analysis_timeout = 120      # 2 分鐘
backtest_timeout = 300           # 5 分鐘
monitor_timeout = 30             # 30 秒
```

---

## 📞 尋求幫助

### 檢查清單

- [ ] 運行了 `python test_openrouter.py`
- [ ] 檢查了 API Key 是否設置正確
- [ ] 檢查了 OpenRouter 帳戶中的額度
- [ ] 檢查了網絡連接
- [ ] 檢查了 OpenRouter 狀態頁面
- [ ] 配置了 fallback providers
- [ ] 查看了 debug 日誌

### 常見修復命令

```bash
# 1. 重新安裝依賴
pip install -r requirements.txt --upgrade

# 2. 清除緩存
rm -rf reports/runs/latest
rm debug_run.log

# 3. 使用 fallback 運行
# (系統會自動 fallback，不需要特殊設置)

# 4. 檢查配置
python -c "from core.llm_clients import LLMClients; c = LLMClients(); print(c.available_providers())"
```

---

## 📋 報告問題

如果以上都不能解決，請提供以下信息：

1. **測試輸出**:
   ```bash
   python test_openrouter.py
   ```

2. **Debug 日誌**:
   ```bash
   cat debug_run.log | tail -50
   ```

3. **環境信息**:
   ```bash
   python --version
   pip show requests
   ```

4. **詳細描述**:
   - 什麼時候開始出現問題
   - 最後一次正常工作是什麼時候
   - 有沒有改變過配置

---

**版本**: v5.4 (2026-02-10)
**最後更新**: 2026-02-10
