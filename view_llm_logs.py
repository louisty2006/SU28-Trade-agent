#!/usr/bin/env python3
"""
查看 LLM 調試日誌
顯示每個 LLM 調用的詳細過程
"""

import json
from pathlib import Path
import sys

def show_llm_logs(log_dir: str = "logs/llm_debug"):
    """顯示最新的 LLM 日誌"""
    log_path = Path(log_dir)

    if not log_path.exists():
        print(f"❌ 日誌目錄不存在：{log_dir}")
        print("💡 提示：首次運行 'python main_v5.py --daily' 會生成日誌")
        return

    # 找最新的日誌文件
    jsonl_files = sorted(log_path.glob("llm_run_*.jsonl"))
    if not jsonl_files:
        print(f"❌ 未找到 LLM 日誌")
        return

    latest_log = jsonl_files[-1]
    print(f"📋 顯示最新日誌：{latest_log.name}\n")

    # 讀取 JSONL 並格式化顯示
    with open(latest_log, "r", encoding="utf-8") as f:
        calls = [json.loads(line) for line in f if line.strip()]

    print(f"總共 {len(calls)} 次 LLM 調用\n")
    print("=" * 80)

    for i, call in enumerate(calls, 1):
        timestamp = call.get("timestamp", "?")
        provider = call.get("provider", "?")
        model = call.get("model", "?")
        ticker = call.get("ticker", "-")
        agent = call.get("agent", "?")

        print(f"\n[{i}] {timestamp}")
        print(f"    代理：{agent:20} | 股票：{ticker}")
        print(f"    提供商：{provider:15} | 模型：{model}")

        # 顯示 System Prompt
        sys_prompt = call.get("system_prompt", "")
        if sys_prompt:
            sys_preview = sys_prompt[:80].replace("\n", " ")
            print(f"    系統提示：{sys_preview}...")

        # 顯示 User Prompt
        user_prompt = call.get("user_prompt", "")
        user_preview = user_prompt[:100].replace("\n", " ")
        print(f"    用戶提示：{user_preview}...")

        # 顯示原始回應
        raw_resp = call.get("raw_response", "")
        raw_preview = raw_resp[:100].replace("\n", " ")
        print(f"    LLM 回應：{raw_preview}...")

        # 顯示解析結果
        parsed = call.get("parsed_result", {})
        if parsed:
            action = parsed.get("action", "?")
            score = parsed.get("score", "?")
            print(f"    ✓ 結果：{action} | 分數：{score}")

        print(f"    {'-'*76}")


def show_detailed_view(log_dir: str = "logs/llm_debug"):
    """顯示詳細的文本日誌"""
    log_path = Path(log_dir)

    # 找最新的 .log 文件
    log_files = sorted(log_path.glob("llm_run_*.log"))
    if not log_files:
        print(f"❌ 未找到詳細日誌")
        return

    latest_log = log_files[-1]
    print(f"📖 詳細日誌：{latest_log.name}\n")

    with open(latest_log, "r", encoding="utf-8") as f:
        content = f.read()

    # 只顯示最後 N 個調用
    calls = content.split("=" * 70)
    for call in calls[-5:]:  # 最後 5 個調用
        if call.strip():
            print(call)
            print("=" * 80)


if __name__ == "__main__":
    print("=" * 80)
    print("🔍 LLM 調試日誌查看器")
    print("=" * 80)

    if len(sys.argv) > 1 and sys.argv[1] == "--detail":
        show_detailed_view()
    else:
        show_llm_logs()
        print("\n💡 提示：運行 'python view_llm_logs.py --detail' 查看詳細日誌")
