#!/usr/bin/env python3
"""
REISHI v5.0 - API 健康检查
测试所有LLM和数据源API的可用性
"""
import os
import sys
import logging
from dotenv import load_dotenv
from datetime import datetime

# 加载环境变量
load_dotenv()

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_llm_apis():
    """测试所有LLM API"""
    print("\n" + "=" * 70)
    print("📡 测试 LLM API 连接")
    print("=" * 70)

    from core.llm_clients import LLMClients, CONFIG

    llm = LLMClients()
    available = llm.available_providers()

    print(f"\n✓ 可用的 providers: {available}")
    print(f"✓ 总数: {len(available)}/4")

    # 检查每个provider的配置
    print("\n" + "-" * 70)
    print("Provider 配置检查:")
    print("-" * 70)

    for provider_id in ["scitely", "cohere", "mistral", "openrouter"]:
        config = CONFIG[provider_id]
        key_env = config["api_key_env"]
        key_value = os.getenv(key_env)

        status = "✅" if key_value else "❌"
        key_preview = f"{key_value[:15]}...{key_value[-10:]}" if key_value and len(key_value) > 25 else "N/A"

        print(f"{status} {provider_id:12} | Key: {key_preview:30} | 长度: {len(key_value) if key_value else 0}")

    # 测试实际调用
    print("\n" + "-" * 70)
    print("实际调用测试:")
    print("-" * 70)

    test_prompt = "请用一句话回答：1+1等于多少？"
    results = {}

    for provider in available:
        print(f"\n测试 {provider}...", end=" ", flush=True)
        try:
            response, used = llm.call(
                test_prompt,
                provider_hint=provider,
                timeout=30
            )

            if response:
                success = "✅"
                preview = response[:50].replace("\n", " ")
                results[provider] = {
                    "success": True,
                    "response_length": len(response),
                    "preview": preview
                }
                print(f"{success} 成功 | 长度: {len(response)} | 预览: {preview}")
            else:
                print(f"❌ 失败 - 空响应")
                results[provider] = {"success": False, "error": "空响应"}

        except Exception as e:
            print(f"❌ 失败 - {str(e)[:50]}")
            results[provider] = {"success": False, "error": str(e)}

    # 汇总
    print("\n" + "=" * 70)
    successful = sum(1 for r in results.values() if r.get("success"))
    print(f"LLM API 测试结果: {successful}/{len(results)} 成功")
    print("=" * 70)

    return results


def test_data_apis():
    """测试数据源API"""
    print("\n" + "=" * 70)
    print("📊 测试数据源 API 连接")
    print("=" * 70)

    results = {}

    # 测试 Yahoo Finance（yfinance库，无需API key）
    print("\n[1] Yahoo Finance (yfinance)...", end=" ", flush=True)
    try:
        import yfinance as yf
        ticker = yf.Ticker("AAPL")
        info = ticker.info
        if info and 'currentPrice' in info:
            print(f"✅ 成功 | AAPL 当前价: ${info['currentPrice']:.2f}")
            results['yahoo'] = {"success": True, "needs_key": False}
        else:
            print("❌ 失败 - 无法获取数据")
            results['yahoo'] = {"success": False, "error": "无法获取数据"}
    except Exception as e:
        print(f"❌ 失败 - {str(e)[:50]}")
        results['yahoo'] = {"success": False, "error": str(e)}

    # 测试 Finnhub
    print("\n[2] Finnhub API...", end=" ", flush=True)
    finnhub_key = os.getenv("FINNHUB_API_KEY")
    if not finnhub_key:
        print("❌ 未配置 API key")
        results['finnhub'] = {"success": False, "error": "未配置 key"}
    else:
        try:
            import requests
            url = f"https://finnhub.io/api/v1/quote?symbol=AAPL&token={finnhub_key}"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if 'c' in data:
                    print(f"✅ 成功 | AAPL 价格: ${data['c']:.2f}")
                    results['finnhub'] = {"success": True, "needs_key": True}
                else:
                    print("❌ 失败 - 响应格式错误")
                    results['finnhub'] = {"success": False, "error": "响应格式错误"}
            else:
                print(f"❌ 失败 - HTTP {r.status_code}")
                results['finnhub'] = {"success": False, "error": f"HTTP {r.status_code}"}
        except Exception as e:
            print(f"❌ 失败 - {str(e)[:50]}")
            results['finnhub'] = {"success": False, "error": str(e)}

    # 测试 Alpha Vantage
    print("\n[3] Alpha Vantage API...", end=" ", flush=True)
    av_key = os.getenv("ALPHAVANTAGE_API_KEY") or os.getenv("ALPHA_VANTAGE_API_KEY")
    if not av_key:
        print("❌ 未配置 API key")
        results['alphavantage'] = {"success": False, "error": "未配置 key"}
    else:
        try:
            import requests
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=AAPL&apikey={av_key}"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if 'Global Quote' in data and data['Global Quote']:
                    price = data['Global Quote'].get('05. price', 'N/A')
                    print(f"✅ 成功 | AAPL 价格: ${price}")
                    results['alphavantage'] = {"success": True, "needs_key": True}
                else:
                    print(f"❌ 失败 - {data.get('Note', data.get('Error Message', '未知错误'))[:50]}")
                    results['alphavantage'] = {"success": False, "error": "API限流或错误"}
            else:
                print(f"❌ 失败 - HTTP {r.status_code}")
                results['alphavantage'] = {"success": False, "error": f"HTTP {r.status_code}"}
        except Exception as e:
            print(f"❌ 失败 - {str(e)[:50]}")
            results['alphavantage'] = {"success": False, "error": str(e)}

    # 汇总
    print("\n" + "=" * 70)
    successful = sum(1 for r in results.values() if r.get("success"))
    print(f"数据源 API 测试结果: {successful}/{len(results)} 成功")
    print("=" * 70)

    return results


def print_recommendations(llm_results, data_results):
    """打印建议"""
    print("\n" + "=" * 70)
    print("💡 建议和下一步")
    print("=" * 70)

    # 检查LLM
    llm_success = [k for k, v in llm_results.items() if v.get("success")]
    llm_failed = [k for k, v in llm_results.items() if not v.get("success")]

    print("\n🤖 LLM APIs:")
    if len(llm_success) >= 2:
        print(f"  ✅ 有 {len(llm_success)} 个可用，可以运行系统")
        print(f"     可用: {', '.join(llm_success)}")
    else:
        print(f"  ⚠️  只有 {len(llm_success)} 个可用，建议至少2个")

    if llm_failed:
        print(f"\n  需要修复的 LLM providers:")
        for provider in llm_failed:
            error = llm_results[provider].get("error", "未知错误")
            print(f"    ❌ {provider}: {error[:60]}")

            # 给出具体建议
            if "空响应" in error or "未知错误" in error:
                print(f"       建议: 检查 API key 是否有效，是否有配额")
            elif "timeout" in error.lower():
                print(f"       建议: 检查网络连接，或增加 timeout")

    # 检查数据源
    data_success = [k for k, v in data_results.items() if v.get("success")]
    data_failed = [k for k, v in data_results.items() if not v.get("success")]

    print("\n📊 数据源 APIs:")
    if 'yahoo' in data_success:
        print(f"  ✅ Yahoo Finance 可用，这是主要数据源")
    else:
        print(f"  ❌ Yahoo Finance 不可用，这会严重影响系统运行")

    if data_failed:
        print(f"\n  可选数据源状态:")
        for source in data_failed:
            error = data_results[source].get("error", "未知错误")
            print(f"    ⚠️  {source}: {error[:60]}")

    print("\n" + "=" * 70)
    print("总结:")
    total_llm = len(llm_results)
    total_data = len(data_results)
    success_llm = len(llm_success)
    success_data = len(data_success)

    if success_llm >= 2 and 'yahoo' in data_success:
        print("  ✅ 系统可以正常运行！")
    elif success_llm >= 1 and 'yahoo' in data_success:
        print("  ⚠️  系统可以运行，但建议修复更多LLM providers以提高可靠性")
    else:
        print("  ❌ 系统无法正常运行，请先修复关键API")

    print("=" * 70)


def main():
    print("\n" + "=" * 70)
    print("🔍 REISHI v5.0 API 健康检查")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # 测试LLM APIs
    llm_results = test_llm_apis()

    # 测试数据源APIs
    data_results = test_data_apis()

    # 打印建议
    print_recommendations(llm_results, data_results)

    print("\n✨ 测试完成！\n")


if __name__ == "__main__":
    main()
