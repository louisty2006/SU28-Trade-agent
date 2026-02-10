#!/usr/bin/env python3
"""
檢查 OpenRouter 模型是否免費可用

訪問 OpenRouter API 獲取模型信息並檢查價格
"""

import requests
import json
from typing import Dict, List

def check_models():
    """檢查 OpenRouter 上的免費模型"""

    print("=" * 80)
    print("🔍 OpenRouter 免費模型檢查")
    print("=" * 80)
    print()

    # 你當前配置的模型
    your_models = [
        "meta-llama/llama-3.2-3b-instruct:free",
        "meta-llama/llama-3.1-8b-instruct:free",
    ]

    print("📋 你當前配置的模型:")
    for model in your_models:
        print(f"  • {model}")
    print()

    # 嘗試從 OpenRouter API 獲取模型列表
    try:
        print("正在從 OpenRouter API 獲取模型信息...")
        response = requests.get(
            "https://openrouter.ai/api/v1/models",
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            models = data.get("data", [])

            print(f"✅ 獲取到 {len(models)} 個模型\n")

            # 篩選免費模型
            free_models = []
            your_model_status = {}

            for model in models:
                model_id = model.get("id", "")
                pricing = model.get("pricing", {})

                # 檢查輸入和輸出價格
                input_price = float(pricing.get("prompt", 0) or 0)
                output_price = float(pricing.get("completion", 0) or 0)

                is_free = input_price == 0 and output_price == 0

                if is_free:
                    free_models.append(model_id)

                # 檢查你配置的模型
                for your_model in your_models:
                    base_model = your_model.replace(":free", "")
                    if base_model in model_id or model_id in base_model:
                        your_model_status[your_model] = {
                            "found": True,
                            "is_free": is_free,
                            "input_price": input_price,
                            "output_price": output_price,
                            "model_name": model.get("name", "Unknown"),
                        }

            print("=" * 80)
            print("✅ 你的模型狀態")
            print("=" * 80)
            print()

            for model, status in your_model_status.items():
                if status["found"]:
                    if status["is_free"]:
                        print(f"✅ {model}")
                        print(f"   名稱: {status['model_name']}")
                        print(f"   價格: 免費 (輸入: $0, 輸出: $0)")
                    else:
                        print(f"⚠️  {model}")
                        print(f"   名稱: {status['model_name']}")
                        print(f"   價格: 不免費")
                        print(f"   輸入: ${status['input_price']}, 輸出: ${status['output_price']}")
                else:
                    print(f"❓ {model}")
                    print(f"   狀態: 在 OpenRouter 上未找到")
                print()

            print("=" * 80)
            print("💡 推薦的免費模型")
            print("=" * 80)
            print()

            # 推薦一些受歡迎的免費模型
            recommended = [
                "meta-llama/llama-3.2-3b-instruct:free",
                "meta-llama/llama-3.1-8b-instruct:free",
                "meta-llama/llama-2-7b-chat:free",
                "microsoft/phi-3-mini-128k-instruct:free",
            ]

            print("受歡迎的免費模型:")
            for model in recommended:
                if model in free_models:
                    print(f"  ✅ {model}")
                else:
                    print(f"  ⚠️  {model} (可能已下架或改名)")

            print()
            print(f"OpenRouter 上的所有免費模型數量: {len(free_models)}")

        else:
            print(f"❌ API 調用失敗 (狀態碼: {response.status_code})")

    except Exception as e:
        print(f"❌ 無法連接 OpenRouter API: {e}")
        print()
        print("💡 替代方案:")
        print()
        print("1. 直接訪問: https://openrouter.ai/models?max_price=0")
        print("2. 在頁面上查看免費模型列表")
        print("3. 更新 .env 中的 OPENROUTER_MODEL 和 OPENROUTER_MODEL_2")

    print()
    print("=" * 80)
    print("📝 配置建議")
    print("=" * 80)
    print()
    print("如果上面的模型不是免費的，可以嘗試:")
    print()
    print("  推薦 (快速 + 免費):")
    print("    OPENROUTER_MODEL=meta-llama/llama-3.2-3b-instruct:free")
    print("    OPENROUTER_MODEL_2=meta-llama/llama-3.1-8b-instruct:free")
    print()
    print("  或 (更強大但仍免費):")
    print("    OPENROUTER_MODEL=mistralai/mistral-7b-instruct:free")
    print("    OPENROUTER_MODEL_2=meta-llama/llama-2-13b-chat:free")
    print()

if __name__ == "__main__":
    check_models()
