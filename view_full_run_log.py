#!/usr/bin/env python3
"""
REISHI 霊視 v5.0 - 完整運行日誌查看工具

用法:
  python view_full_run_log.py                    # 查看最新日誌
  python view_full_run_log.py [timestamp]        # 查看特定時間的日誌 (e.g., 2026-02-10_154253)
  python view_full_run_log.py --list             # 列出所有日誌目錄
  python view_full_run_log.py --analyze          # 分析並總結最新日誌
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List


class FullRunLogViewer:
    """查看和分析完整運行日誌"""

    BASE_DIR = Path("reports/daily")

    def __init__(self):
        self.base_dir = self.BASE_DIR
        if not self.base_dir.exists():
            print(f"❌ 報告目錄不存在: {self.base_dir}")
            sys.exit(1)

    def list_all_logs(self) -> List[Path]:
        """列出所有日誌目錄"""
        logs = sorted(
            [d for d in self.base_dir.iterdir() if d.is_dir()],
            reverse=True
        )
        return logs

    def get_latest_log_dir(self) -> Optional[Path]:
        """取得最新的日誌目錄"""
        logs = self.list_all_logs()
        return logs[0] if logs else None

    def find_log_dir(self, timestamp: str) -> Optional[Path]:
        """根據時間戳查找日誌目錄"""
        log_dir = self.base_dir / timestamp
        return log_dir if log_dir.exists() else None

    def display_master_log(self, log_dir: Path):
        """顯示 master log（完整執行流程）"""
        master_log = log_dir / "00_MASTER_FLOW.md"
        if not master_log.exists():
            print(f"❌ Master log 不存在: {master_log}")
            return

        print("\n" + "=" * 80)
        print(f"📖 MASTER FLOW LOG - {log_dir.name}")
        print("=" * 80)
        with open(master_log, "r", encoding="utf-8") as f:
            print(f.read())

    def display_llm_calls_summary(self, log_dir: Path):
        """顯示 LLM 呼叫摘要"""
        llm_log = log_dir / "01_LLM_CALLS.jsonl"
        if not llm_log.exists():
            print(f"⚠️  LLM log 不存在: {llm_log}")
            return

        print("\n" + "=" * 80)
        print(f"🤖 LLM CALLS SUMMARY - {log_dir.name}")
        print("=" * 80)

        calls = []
        with open(llm_log, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        call = json.loads(line)
                        calls.append(call)
                    except json.JSONDecodeError:
                        continue

        if not calls:
            print("無 LLM 呼叫記錄")
            return

        print(f"\n共 {len(calls)} 個 LLM 呼叫:\n")

        # 按 step 分組
        by_step = {}
        for call in calls:
            step = call.get("step_index", "unknown")
            if step not in by_step:
                by_step[step] = []
            by_step[step].append(call)

        for step in sorted(by_step.keys()):
            step_calls = by_step[step]
            step_name = step_calls[0].get("step_name", "未知")
            print(f"\n### Step {step}: {step_name}")
            print(f"   共 {len(step_calls)} 個呼叫:\n")

            for i, call in enumerate(step_calls, 1):
                print(f"   **呼叫 #{i}**")
                print(f"   - 角色: {call.get('agent_role', 'N/A')}")
                if call.get('ticker'):
                    print(f"   - 股票: {call['ticker']}")
                print(f"   - 提供商: {call.get('provider', 'N/A')}")
                print(f"   - 模型: {call.get('model', 'N/A')}")
                print(f"   - 時間: {call.get('timestamp', 'N/A')}")
                if call.get('user_prompt'):
                    prompt_preview = call['user_prompt'][:100] + "..." if len(call['user_prompt']) > 100 else call['user_prompt']
                    print(f"   - Prompt: {prompt_preview}")
                if call.get('parsed_result'):
                    result_str = str(call['parsed_result'])[:100]
                    print(f"   - 結果: {result_str}...")
                print()

    def display_data_flow(self, log_dir: Path):
        """顯示數據流向"""
        data_flow_log = log_dir / "02_DATA_FLOW.md"
        if not data_flow_log.exists():
            print(f"⚠️  Data flow log 不存在: {data_flow_log}")
            return

        print("\n" + "=" * 80)
        print(f"🔄 DATA FLOW LOG - {log_dir.name}")
        print("=" * 80)
        with open(data_flow_log, "r", encoding="utf-8") as f:
            print(f.read())

    def list_step_reports(self, log_dir: Path):
        """列出所有步驟報告"""
        step_files = sorted([f for f in log_dir.glob("step_*.md")])
        if not step_files:
            print(f"⚠️  無步驟報告")
            return

        print("\n" + "=" * 80)
        print(f"📋 STEP REPORTS - {log_dir.name}")
        print("=" * 80)
        print(f"\n共 {len(step_files)} 份步驟報告:\n")
        for f in step_files:
            print(f"  - {f.name}")

    def display_step_report(self, log_dir: Path, step_num: int):
        """顯示特定步驟報告"""
        step_files = sorted([f for f in log_dir.glob(f"step_{step_num:02d}_*.md")])
        if not step_files:
            print(f"❌ Step {step_num} 報告不存在")
            return

        step_file = step_files[0]
        print("\n" + "=" * 80)
        print(f"📋 {step_file.name}")
        print("=" * 80)
        with open(step_file, "r", encoding="utf-8") as f:
            print(f.read())

    def analyze_log(self, log_dir: Path):
        """分析並總結日誌"""
        print("\n" + "=" * 80)
        print(f"📊 LOG ANALYSIS - {log_dir.name}")
        print("=" * 80)

        # 統計 step 報告
        step_files = list(log_dir.glob("step_*.md"))
        print(f"\n✅ 步驟報告: {len(step_files)} 份")

        # 統計 LLM 呼叫
        llm_log = log_dir / "01_LLM_CALLS.jsonl"
        llm_count = 0
        if llm_log.exists():
            with open(llm_log, "r", encoding="utf-8") as f:
                llm_count = sum(1 for _ in f if _.strip())
        print(f"✅ LLM 呼叫: {llm_count} 次")

        # Master log 大小
        master_log = log_dir / "00_MASTER_FLOW.md"
        if master_log.exists():
            size = master_log.stat().st_size / 1024
            print(f"✅ Master log: {size:.1f} KB")

        # 摘要報告
        summary_file = log_dir / "SUMMARY_REPORT.md"
        if summary_file.exists():
            print(f"✅ 摘要報告已生成")

        print(f"\n📂 日誌目錄: {log_dir}")
        print(f"\n可用命令:")
        print(f"  python view_full_run_log.py master         # 查看完整流程")
        print(f"  python view_full_run_log.py llm            # 查看 LLM 呼叫摘要")
        print(f"  python view_full_run_log.py flow           # 查看數據流向")
        print(f"  python view_full_run_log.py steps          # 列出所有步驟報告")
        print(f"  python view_full_run_log.py step [N]       # 查看 step N 報告")


def main():
    viewer = FullRunLogViewer()

    # 解析命令
    if len(sys.argv) < 2:
        # 預設顯示最新日誌的 master log
        log_dir = viewer.get_latest_log_dir()
        if not log_dir:
            print("❌ 無日誌目錄，請先運行 daily analysis")
            sys.exit(1)
        print(f"📂 查看最新日誌: {log_dir.name}\n")
        viewer.display_master_log(log_dir)
    else:
        cmd = sys.argv[1]

        if cmd == "--list":
            logs = viewer.list_all_logs()
            print("📂 所有日誌目錄 (最新優先):\n")
            for log in logs:
                print(f"  {log.name}")
            sys.exit(0)

        elif cmd == "--analyze":
            log_dir = viewer.get_latest_log_dir()
            if not log_dir:
                print("❌ 無日誌目錄")
                sys.exit(1)
            viewer.analyze_log(log_dir)
            sys.exit(0)

        # 可能是 timestamp 或 subcommand
        log_dir = viewer.find_log_dir(cmd)

        if not log_dir:
            # 嘗試作為 subcommand
            log_dir = viewer.get_latest_log_dir()
            if not log_dir:
                print("❌ 無日誌目錄")
                sys.exit(1)

            if cmd == "master":
                viewer.display_master_log(log_dir)
            elif cmd == "llm":
                viewer.display_llm_calls_summary(log_dir)
            elif cmd == "flow":
                viewer.display_data_flow(log_dir)
            elif cmd == "steps":
                viewer.list_step_reports(log_dir)
            elif cmd == "step" and len(sys.argv) > 2:
                try:
                    step_num = int(sys.argv[2])
                    viewer.display_step_report(log_dir, step_num)
                except ValueError:
                    print("❌ 步驟編號必須是整數")
                    sys.exit(1)
            else:
                print(f"❌ 未知命令: {cmd}")
                print(__doc__)
                sys.exit(1)
        else:
            # 顯示指定日誌的 master log
            viewer.display_master_log(log_dir)


if __name__ == "__main__":
    main()
