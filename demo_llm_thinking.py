#!/usr/bin/env python3
"""
演示 LLM 思考過程
模擬 Multi-Agent 分析，顯示完整的 LLM 輸入輸出
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# 手動加載 .env
env_file = Path(".env")
if env_file.exists():
    with open(".env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key] = val

from core.llm_clients import LLMClients

print("=" * 80)
print("🧠 演示 Multi-Agent 分析的 LLM 思考過程")
print("=" * 80)

llm = LLMClients()
ticker = "AAPL"

# 模擬四個分析師的 prompts
agents = [
    {
        "name": "Fundamental 基本面分析師",
        "system": "你是基本面分析師。給出 BUY/HOLD/SELL、1-10 分、信心度 0-1。輸出 JSON。",
        "prompt": f"""股票 {ticker} 基本面數據：
- PE Ratio: 28.5
- PB Ratio: 42.3
- ROE: 85.6%
- 營收成長: 5.2%
- 淨利潤率: 25.3%

請輸出 JSON，格式：{{"action":"HOLD","score":7,"confidence":0.8,...}}""",
    },
    {
        "name": "Technical 技術分析師",
        "system": "你是技術分析師。根據價格動作給出 BUY/HOLD/SELL。輸出 JSON。",
        "prompt": f"""股票 {ticker} 技術描述：
- 收盤: $182.50
- 近20日高: $195.80
- 近20日低: $175.20
- 突破 20 日高點？是

請輸出 JSON。""",
    },
    {
        "name": "Sentiment 情緒分析師",
        "system": "你是情緒分析師。根據市場情緒給出 BUY/HOLD/SELL。輸出 JSON。",
        "prompt": f"""股票 {ticker} 市場情緒：
- 情緒分數: 0.6（中立偏正面）
- 主要新聞: Apple 發布新產品
- 風險提示: 競爭加劇

請輸出 JSON。""",
    },
    {
        "name": "Risk 風險分析師",
        "system": "你是風險分析師。識別下行風險。給出 BUY/HOLD/SELL。輸出 JSON。",
        "prompt": f"""股票 {ticker} 風險評估：
- 市場風險: 高（美股波動）
- 公司風險: 中（競爭激烈）
- 價格波動率: 18.5%

請輸出 JSON。""",
    },
]

for i, agent in enumerate(agents, 1):
    print(f"\n{'='*80}")
    print(f"[{i}/4] {agent['name']}")
    print(f"{'='*80}\n")

    print("📝 系統提示（System Prompt）：")
    print(f"   {agent['system']}\n")

    print("🤖 用戶提示（User Prompt）：")
    for line in agent["prompt"].split("\n"):
        print(f"   {line}")

    print(f"\n⏳ 正在調用 LLM... (超時 30 秒)", end=" ", flush=True)

    try:
        response, provider = llm.call(
            agent["prompt"],
            system_prompt=agent["system"],
            timeout=30
        )

        print(f"✅ 完成\n")
        print(f"📤 LLM 回應（來自 {provider}）：")
        print(f"   {response[:200]}...")

        # 模擬解析
        if "action" in response.lower():
            print(f"\n✓ 解析成功")

    except Exception as e:
        print(f"❌ 失敗: {e}")

print("\n" + "=" * 80)
print("💡 說明：")
print("=" * 80)
print("""
這個演示顯示了 REISHI v5.0 在進行 Multi-Agent 分析時的完整思考過程：

1️⃣ 系統提示（System Prompt）
   - 定義 LLM 的角色和任務
   - 指定輸出格式（JSON）

2️⃣ 用戶提示（User Prompt）
   - 傳遞市場數據（基本面、技術面、情緒、風險）
   - 要求 LLM 進行分析

3️⃣ LLM 回應
   - 原始 LLM 輸出
   - 通常是 JSON 格式

4️⃣ 解析結果
   - 提取 action (BUY/HOLD/SELL)
   - 提取 score (1-10)
   - 提取 confidence (0-1)

四個分析師的結論會被匯總成最終共識決策。
""")

print("\n📊 查看完整日誌：")
print("   python view_llm_logs.py          # 簡明視圖")
print("   python view_llm_logs.py --detail # 詳細視圖")
