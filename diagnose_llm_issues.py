#!/usr/bin/env python3
"""
深度诊断 LLM API 问题
"""
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def test_scitely():
    """测试 Scitely API"""
    print("\n" + "=" * 70)
    print("🔍 诊断 Scitely API")
    print("=" * 70)

    key = os.getenv("SCITELY_API_KEY")
    if not key:
        print("❌ 未找到 SCITELY_API_KEY")
        return

    url = "https://api.scitely.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "qwen3-235b-a22b-instruct",
        "messages": [{"role": "user", "content": "请回答：1+1=?"}],
        "temperature": 0.3,
        "max_tokens": 4000
    }

    print(f"URL: {url}")
    print(f"Model: {payload['model']}")
    print(f"Key preview: {key[:15]}...{key[-10:]}")

    try:
        print("\n发送请求...", end=" ", flush=True)
        r = requests.post(url, headers=headers, json=payload, timeout=30)

        print(f"状态码: {r.status_code}")
        print(f"\n响应头:")
        for k, v in r.headers.items():
            if k.lower() in ['content-type', 'content-length', 'x-ratelimit-remaining']:
                print(f"  {k}: {v}")

        print(f"\n响应内容:")
        if r.status_code == 200:
            data = r.json()
            print(json.dumps(data, indent=2, ensure_ascii=False)[:500])

            # 检查响应结构
            if 'choices' in data and len(data['choices']) > 0:
                content = data['choices'][0].get('message', {}).get('content', '')
                print(f"\n提取的内容: '{content}'")
                print(f"内容长度: {len(content)}")
            else:
                print("⚠️  响应中没有 choices 或 message.content")
        else:
            print(r.text[:500])

    except Exception as e:
        print(f"\n❌ 异常: {e}")


def test_cohere():
    """测试 Cohere API"""
    print("\n" + "=" * 70)
    print("🔍 诊断 Cohere API")
    print("=" * 70)

    key = os.getenv("COHERE_API_KEY")
    if not key:
        print("❌ 未找到 COHERE_API_KEY")
        return

    url = "https://api.cohere.com/v2/chat"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "command-a-03-2025",
        "messages": [{"role": "user", "content": "请回答：1+1=?"}],
        "temperature": 0.3
    }

    print(f"URL: {url}")
    print(f"Model: {payload['model']}")
    print(f"Key preview: {key[:15]}...{key[-10:]}")

    try:
        print("\n发送请求...", end=" ", flush=True)
        r = requests.post(url, headers=headers, json=payload, timeout=30)

        print(f"状态码: {r.status_code}")
        print(f"\n响应内容:")
        if r.status_code == 200:
            data = r.json()
            print(json.dumps(data, indent=2, ensure_ascii=False)[:500])
        else:
            print(r.text[:500])

    except Exception as e:
        print(f"\n❌ 异常: {e}")


def test_openrouter():
    """测试 OpenRouter API"""
    print("\n" + "=" * 70)
    print("🔍 诊断 OpenRouter API")
    print("=" * 70)

    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        print("❌ 未找到 OPENROUTER_API_KEY")
        return

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "meta-llama/llama-3.1-8b-instruct",
        "messages": [{"role": "user", "content": "请回答：1+1=?"}],
        "temperature": 0.3,
        "max_tokens": 4000
    }

    print(f"URL: {url}")
    print(f"Model: {payload['model']}")
    print(f"Key preview: {key[:15]}...{key[-10:]}")

    try:
        print("\n发送请求...", end=" ", flush=True)
        r = requests.post(url, headers=headers, json=payload, timeout=30)

        print(f"状态码: {r.status_code}")
        print(f"\n响应内容:")
        if r.status_code == 200:
            data = r.json()
            print(json.dumps(data, indent=2, ensure_ascii=False)[:500])
        else:
            print(r.text[:500])

    except Exception as e:
        print(f"\n❌ 异常: {e}")


if __name__ == "__main__":
    test_scitely()
    test_cohere()
    test_openrouter()

    print("\n" + "=" * 70)
    print("✨ 诊断完成")
    print("=" * 70)
