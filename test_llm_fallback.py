#!/usr/bin/env python3
"""
测试 LLM fallback 行为
"""
import logging
from dotenv import load_dotenv
from core.llm_clients import LLMClients

# 加载 .env 文件
load_dotenv()

# 设置 logging 为 INFO 级别，这样可以看到所有尝试
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_llm_fallback():
    print("=" * 60)
    print("测试 LLM Clients Fallback 行为")
    print("=" * 60)

    llm = LLMClients()

    print(f"\n✓ 可用的 providers: {llm.available_providers()}")
    print(f"✓ 有任何 key: {llm.has_any_key()}")

    # 测试简单的调用
    print("\n" + "=" * 60)
    print("测试1: 简单调用（无 provider_hint）")
    print("=" * 60)
    response, used = llm.call("请用一句话说明你是谁", timeout=30)
    print(f"\n结果:")
    print(f"  使用的 provider: {used}")
    print(f"  回应长度: {len(response)}")
    print(f"  回应预览: {response[:100]}...")

    # 测试各个 provider hint
    for provider in ["scitely", "cohere", "mistral", "openrouter"]:
        print("\n" + "=" * 60)
        print(f"测试2: 使用 provider_hint='{provider}'")
        print("=" * 60)
        response, used = llm.call(
            "请用一句话回答：1+1=?",
            provider_hint=provider,
            timeout=30
        )
        print(f"\n结果:")
        print(f"  使用的 provider: {used}")
        print(f"  回应长度: {len(response)}")
        print(f"  回应预览: {response[:100] if response else '(空)'}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_llm_fallback()
