#!/usr/bin/env python3
"""
測試 Ollama 通過 OpenAI 相容 API 的連接
Ollama 在 http://localhost:11434 運行
模型：deepseek-r1:14b
"""

import requests
import json

print("=" * 70)
print("🧪 測試 Ollama OpenAI 相容 API")
print("=" * 70)

# 1️⃣ 測試服務是否運行
print("\n[1/3] 檢查 Ollama 服務...")
try:
    r = requests.get("http://localhost:11434/api/tags", timeout=5)
    if r.status_code == 200:
        models = r.json().get("models", [])
        print(f"✅ Ollama 服務運行中")
        print(f"   可用模型：")
        for m in models:
            print(f"     • {m['name']}")
    else:
        print(f"❌ Ollama 服務返回錯誤：{r.status_code}")
except Exception as e:
    print(f"❌ 無法連接 Ollama：{e}")
    exit(1)

# 2️⃣ 測試 OpenAI 相容 API 端點
print("\n[2/3] 測試 OpenAI 相容 API 端點...")
url = "http://localhost:11434/v1/chat/completions"
model = "deepseek-r1:14b"

payload = {
    "model": model,
    "messages": [
        {
            "role": "system",
            "content": "你是一個有幫助的助手。用中文回答。"
        },
        {
            "role": "user",
            "content": "你是誰？請用一句話回答。"
        }
    ],
    "temperature": 0.7,
    "max_tokens": 200,
    "stream": False
}

print(f"   請求地址：{url}")
print(f"   模型：{model}")

try:
    print("   發送請求...", end=" ", flush=True)
    r = requests.post(url, json=payload, timeout=60)
    print(f"✅ 連接成功（狀態碼：{r.status_code}）")

    # 3️⃣ 解析回覆
    print("\n[3/3] 解析回覆...")
    if r.status_code == 200:
        data = r.json()

        # 提取回覆內容
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        if content:
            print(f"✅ 收到回覆（{len(content)} 字）：")
            print(f"\n   {content}\n")
            print("=" * 70)
            print("✨ Ollama OpenAI 相容 API 測試成功！")
            print("=" * 70)
        else:
            print(f"❌ 回覆為空")
            print(f"   完整回應：{json.dumps(data, ensure_ascii=False, indent=2)}")
    else:
        print(f"❌ 請求失敗")
        print(f"   狀態碼：{r.status_code}")
        print(f"   回應：{r.text[:200]}")

except requests.Timeout:
    print(f"❌ 請求超時（60秒）")
    print(f"   提示：DeepSeek-R1 首次運行較慢，請等待...")
except Exception as e:
    print(f"❌ 請求失敗：{e}")

print("\n💡 如果成功，可以在代碼中這樣使用：")
print("""
   from openai import OpenAI

   client = OpenAI(
       api_key="",  # Ollama 不需要 key
       base_url="http://localhost:11434/v1"
   )

   response = client.chat.completions.create(
       model="deepseek-r1:14b",
       messages=[{"role": "user", "content": "你好"}]
   )

   print(response.choices[0].message.content)
""")
