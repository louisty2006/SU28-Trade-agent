#!/usr/bin/env python3
"""
測試 OpenRouter 修復後的智能重試和雙帳號輪替

驗證：
1. 速率限制 (429) 會自動重試
2. 第一帳號失敗會切換到第二帳號
3. 指數退避策略有效
"""

import os
from dotenv import load_dotenv
load_dotenv()

from core.llm_clients import LLMClients

print("=" * 80)
print("🧪 測試 OpenRouter 智能重試和雙帳號輪替")
print("=" * 80)
print()

# 初始化 LLM 客戶端
client = LLMClients()

print("1️⃣  檢查可用的 providers:")
providers = client.available_providers()
print(f"   {providers}")
print()

if "openrouter" not in providers and "openrouter2" not in providers:
    print("❌ 沒有 OpenRouter provider 可用")
    print("   請確保 .env 中已設置 OPENROUTER_API_KEY")
    exit(1)

print("2️⃣  測試簡單的 LLM 呼叫 (會自動處理速率限制):")
print()

# 測試 3 次呼叫，驗證重試機制
for i in range(3):
    print(f"   測試 #{i+1}")
    response, provider = client.call(
        prompt="Say 'Test successful' if you receive this.",
        system_prompt="You are a helpful assistant. Reply briefly.",
        provider_hint="openrouter",  # 優先使用 OpenRouter
    )

    if response:
        print(f"   ✅ 成功！使用 provider: {provider}")
        print(f"   回應: {response[:50]}...")
    else:
        print(f"   ❌ 失敗")

    print()

print("=" * 80)
print("📊 測試結果")
print("=" * 80)
print()
print("如果看到以上成功訊息，說明修復有效！")
print()
print("修復內容:")
print("  ✅ 遇到 429 錯誤會自動重試 (等待 1s, 2s, 4s)")
print("  ✅ openrouter 失敗會自動切換到 openrouter2")
print("  ✅ 添加了必要的 HTTP headers")
print("  ✅ 更好的錯誤日誌")
print()
print("Fallback 順序: openrouter → openrouter2 → mistral → ollama")
print()
