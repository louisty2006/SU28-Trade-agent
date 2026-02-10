#!/usr/bin/env python3
"""
REISHI 霊視 v5.4 - 快速運行索引查看工具

用法:
  python view_runs.py                        # 查看所有 runs 索引
  python view_runs.py 2026-02-10_154253     # 查看特定 run
  python view_runs.py latest                # 查看最新 run
  python view_runs.py latest master         # 查看最新 run 的 master log
  python view_runs.py 2026-02-10_154253 llm # 查看特定 run 的 LLM 摘要
"""

import os
import sys
from pathlib import Path
from datetime import datetime


class RunsViewer:
    """運行索引查看工具"""

    BASE_DIR = Path("reports/runs")
    INDEX_FILE = BASE_DIR / "INDEX.md"

    def list_all_runs(self):
        """列出所有 runs"""
        if not self.BASE_DIR.exists():
            print(f"❌ 運行目錄不存在: {self.BASE_DIR}")
            return []

        runs = sorted(
            [d for d in self.BASE_DIR.iterdir() if d.is_dir()],
            reverse=True
        )
        return runs

    def get_latest_run(self):
        """取得最新的 run"""
        runs = self.list_all_runs()
        return runs[0] if runs else None

    def find_run(self, identifier: str):
        """根據 identifier 查找 run"""
        if identifier == "latest":
            return self.get_latest_run()

        run_dir = self.BASE_DIR / identifier
        return run_dir if run_dir.exists() else None

    def display_index(self):
        """顯示索引文件"""
        if not self.INDEX_FILE.exists():
            print(f"❌ 索引文件不存在: {self.INDEX_FILE}")
            print("\n請先運行 daily analysis:")
            print("  python main_v5.py --daily")
            return

        print("\n" + "=" * 80)
        print("📋 REISHI 運行索引")
        print("=" * 80)
        with open(self.INDEX_FILE, "r", encoding="utf-8") as f:
            print(f.read())

    def display_run_info(self, run_dir: Path):
        """顯示單個 run 的信息"""
        timestamp = run_dir.name

        print("\n" + "=" * 80)
        print(f"📂 Run: {timestamp}")
        print("=" * 80)

        # 列出文件
        print("\n📄 文件列表:")
        print()

        files = sorted(run_dir.glob("*"))
        for f in files:
            if f.is_file():
                size = f.stat().st_size
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} MB"

                icon = self._get_file_icon(f.name)
                print(f"  {icon} {f.name:<40} {size_str:>10}")

        # 統計信息
        print("\n📊 統計信息:")
        total_size = sum(f.stat().st_size for f in run_dir.glob("*") if f.is_file())
        step_files = list(run_dir.glob("step_*.md"))

        print(f"  - 總文件數: {len(list(run_dir.glob('*')))}")
        print(f"  - Step 報告: {len(step_files)}")
        print(f"  - 總大小: {total_size / (1024*1024):.1f} MB")

        # LLM 呼叫統計
        llm_log = run_dir / "01_LLM_CALLS.jsonl"
        if llm_log.exists():
            try:
                with open(llm_log, "r", encoding="utf-8") as f:
                    llm_count = sum(1 for _ in f if _.strip())
                print(f"  - LLM 呼叫次數: {llm_count}")
            except:
                pass

        print("\n🔍 快速命令:")
        print()
        print(f"  # 查看完整執行流程")
        print(f"  cat reports/runs/{timestamp}/00_MASTER_FLOW.md | less")
        print()
        print(f"  # 查看最終報告")
        print(f"  cat reports/runs/{timestamp}/SUMMARY_REPORT.md")
        print()
        print(f"  # 分析特定股票 (e.g., AAPL)")
        print(f"  grep 'AAPL' reports/runs/{timestamp}/01_LLM_CALLS.jsonl | jq .")
        print()
        print(f"  # 查看性能指標")
        print(f"  grep '耗時' reports/runs/{timestamp}/00_MASTER_FLOW.md")
        print()

    def _get_file_icon(self, filename: str) -> str:
        """根據文件名返回圖標"""
        if filename.startswith("00_MASTER"):
            return "⭐"
        elif filename.startswith("01_LLM"):
            return "🤖"
        elif filename.startswith("02_DATA"):
            return "🔄"
        elif filename.startswith("step_"):
            return "📋"
        elif filename == "SUMMARY_REPORT.md":
            return "📄"
        else:
            return "📁"

    def display_master_flow(self, run_dir: Path):
        """顯示 master flow log"""
        master_log = run_dir / "00_MASTER_FLOW.md"
        if not master_log.exists():
            print(f"❌ Master log 不存在: {master_log}")
            return

        print(f"\n{'='*80}")
        print(f"📖 Master Flow Log - {run_dir.name}")
        print(f"{'='*80}\n")

        with open(master_log, "r", encoding="utf-8") as f:
            print(f.read())

    def display_summary(self, run_dir: Path):
        """顯示最終報告"""
        summary = run_dir / "SUMMARY_REPORT.md"
        if not summary.exists():
            print(f"❌ 最終報告不存在: {summary}")
            return

        print(f"\n{'='*80}")
        print(f"📄 最終報告 - {run_dir.name}")
        print(f"{'='*80}\n")

        with open(summary, "r", encoding="utf-8") as f:
            print(f.read())

    def display_llm_summary(self, run_dir: Path):
        """顯示 LLM 呼叫摘要"""
        llm_log = run_dir / "01_LLM_CALLS.jsonl"
        if not llm_log.exists():
            print(f"⚠️  LLM log 不存在: {llm_log}")
            return

        print(f"\n{'='*80}")
        print(f"🤖 LLM Calls Summary - {run_dir.name}")
        print(f"{'='*80}\n")

        import json

        calls = []
        with open(llm_log, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        calls.append(json.loads(line))
                    except:
                        pass

        if not calls:
            print("無 LLM 呼叫記錄")
            return

        print(f"共 {len(calls)} 個 LLM 呼叫:\n")

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
            print(f"### Step {step}: {step_name}")
            print(f"   共 {len(step_calls)} 個呼叫\n")

            for call in step_calls[:3]:  # 只顯示前 3 個
                print(f"   - {call.get('agent_role', 'N/A')}", end="")
                if call.get('ticker'):
                    print(f" ({call['ticker']})", end="")
                print()

            if len(step_calls) > 3:
                print(f"   ... 還有 {len(step_calls) - 3} 個呼叫")
            print()


def main():
    viewer = RunsViewer()

    if len(sys.argv) < 2:
        # 預設顯示索引
        viewer.display_index()
    else:
        cmd = sys.argv[1]

        if cmd == "--list" or cmd == "-l":
            viewer.display_index()
        elif cmd == "index":
            viewer.display_index()
        else:
            # 嘗試查找 run
            run_dir = viewer.find_run(cmd)

            if not run_dir:
                print(f"❌ 找不到 run: {cmd}")
                print("\n可用的命令:")
                print("  python view_runs.py              # 查看索引")
                print("  python view_runs.py latest       # 查看最新 run")
                print("  python view_runs.py [timestamp]  # 查看特定 run")
                sys.exit(1)

            # 檢查是否有 subcommand
            if len(sys.argv) > 2:
                subcommand = sys.argv[2]
                if subcommand == "master":
                    viewer.display_master_flow(run_dir)
                elif subcommand == "summary":
                    viewer.display_summary(run_dir)
                elif subcommand == "llm":
                    viewer.display_llm_summary(run_dir)
                else:
                    viewer.display_run_info(run_dir)
            else:
                # 顯示 run 信息
                viewer.display_run_info(run_dir)


if __name__ == "__main__":
    main()
