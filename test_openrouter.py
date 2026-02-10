#!/usr/bin/env python3
"""
測試 OpenRouter 連接和 API 可用性

運行此腳本來診斷 OpenRouter 連接問題
"""

import os
import requests
import json
from dotenv import load_dotenv

# 載入 .env
load_dotenv()

def test_openrouter():
    """測試 OpenRouter 連接"""

    print("=" * 80)
    print("🔧 OpenRouter 連接診斷工具")
    print("=" * 80)
    print()

    # 1. 檢查 API Key
    print("1️⃣  檢查 API Key...")
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY 未設置")
        print("   請在 .env 文件中設置: OPENROUTER_API_KEY=your_key")
        return False

    print(f"✅ API Key 已設置: {api_key[:10]}...{api_key[-5:]}")
    print()

    # 2. 檢查模型
    print("2️⃣  檢查模型...")
    model = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.2-3b-instruct:free")
    print(f"✅ 使用模型: {model}")
    print()

    # 3. 檢查網絡連接
    print("3️⃣  測試網絡連接...")
    try:
        r = requests.get("https://openrouter.ai", timeout=5)
        print(f"✅ 可以訪問 openrouter.ai (狀態碼: {r.status_code})")
    except Exception as e:
        print(f"❌ 無法訪問 openrouter.ai: {e}")
        print("   可能是網絡問題，請檢查你的網絡連接")
        return False
    print()

    # 4. 測試 API 端點
    print("4️⃣  測試 OpenRouter API 端點...")
    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com",  # OpenRouter 需要這個頭
        "X-Title": "REISHI Stock Scanner",
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant. Reply briefly in English."
            },
            {
                "role": "user",
                "content": "Say 'OpenRouter is working' if you receive this message."
            }
        ],
        "temperature": 0.3,
        "max_tokens": 100,
    }

    try:
        print(f"   📤 發送請求到: {url}")
        print(f"   📦 模型: {model}")
        print(f"   ⏱️  超時: 30 秒")
        print()

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )

        print(f"   📨 響應狀態碼: {response.status_code}")

        if response.status_code == 200:
            print(f"✅ API 調用成功!")
            data = response.json()
            result = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"   💬 LLM 回應: {result[:100]}")
            print()
            return True

        elif response.status_code == 401:
            print(f"❌ 認證失敗 (401)")
            print(f"   可能原因:")
            print(f"   1. API Key 無效或過期")
            print(f"   2. API Key 有額度限制已用完")
            print(f"   請檢查 OpenRouter 帳戶: https://openrouter.ai/account")
            data = response.json()
            print(f"   詳情: {data.get('error', {}).get('message', 'Unknown error')}")
            print()
            return False

        elif response.status_code == 429:
            print(f"❌ 請求過於頻繁 (429)")
            print(f"   可能原因: 超過速率限制")
            print(f"   請等待一段時間後重試")
            print()
            return False

        elif response.status_code == 502 or response.status_code == 503:
            print(f"❌ 服務暫時不可用 ({response.status_code})")
            print(f"   OpenRouter 服務可能正在維護")
            print(f"   請稍後重試")
            print()
            return False

        else:
            print(f"❌ API 調用失敗 ({response.status_code})")
            try:
                data = response.json()
                error = data.get("error", {})
                print(f"   錯誤信息: {error.get('message', 'Unknown error')}")
            except:
                print(f"   響應: {response.text[:200]}")
            print()
            return False

    except requests.exceptions.Timeout:
        print(f"❌ 請求超時 (30 秒)")
        print(f"   可能原因:")
        print(f"   1. 網絡連接慢")
        print(f"   2. OpenRouter 伺服器響應慢")
        print()
        return False

    except Exception as e:
        print(f"❌ 發生異常: {e}")
        print()
        return False


def test_fallback():
    """測試其他 LLM providers 的 fallback"""
    print("=" * 80)
    print("🔄 測試 Fallback 提供商")
    print("=" * 80)
    print()

    providers = {
        "mistral": ("MISTRAL_API_KEY", "https://api.mistral.ai/v1/chat/completions"),
        "ollama": ("OLLAMA_API_KEY", "http://localhost:11434/api/chat"),
    }

    for name, (key_env, url) in providers.items():
        key = os.getenv(key_env)
        status = "✅ 可用" if key else "❌ 未設置"
        print(f"  {name.upper():10} {status}")

    print()
    print("💡 建議: 如果 OpenRouter 無法使用，確保至少有一個其他 provider 配置")
    print()


if __name__ == "__main__":
    success = test_openrouter()
    print()
    test_fallback()

    print("=" * 80)
    if success:
        print("✅ OpenRouter 一切正常!")
    else:
        print("❌ OpenRouter 連接有問題")
        print()
        print("解決方案:")
        print("1. 檢查 API Key 是否正確設置在 .env 中")
        print("2. 檢查 API Key 是否有額度 (https://openrouter.ai/account)")
        print("3. 檢查網絡連接")
        print("4. 檢查 OpenRouter 服務狀態 (https://status.openrouter.ai)")
        print("5. 配置其他 LLM provider 作為 fallback (Mistral, Ollama)")
    print("=" * 80)
