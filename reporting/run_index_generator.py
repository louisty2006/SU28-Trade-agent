"""
REISHI 霊視 v5.4 - 運行索引生成器

在 reports/runs/ 根目錄下生成 INDEX.md 文件，
列出所有的 runs 及其快速信息，方便導航。
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


class RunIndexGenerator:
    """生成和管理所有 runs 的索引"""

    def __init__(self, runs_dir: str = "reports/runs"):
        self.runs_dir = Path(runs_dir)
        self.index_file = self.runs_dir / "INDEX.md"
        self.metadata_file = self.runs_dir / "runs_metadata.json"

    def generate_index(self):
        """生成索引文件"""
        if not self.runs_dir.exists():
            os.makedirs(self.runs_dir, exist_ok=True)

        # 獲取所有 run 目錄
        run_dirs = sorted(
            [d for d in self.runs_dir.iterdir() if d.is_dir()],
            reverse=True  # 最新的在前
        )

        if not run_dirs:
            self._write_empty_index()
            return

        # 收集 metadata
        runs_info = []
        for run_dir in run_dirs:
            info = self._extract_run_info(run_dir)
            runs_info.append(info)

        # 生成索引
        self._write_index(runs_info)

        # 保存 metadata JSON
        self._save_metadata(runs_info)

    def _extract_run_info(self, run_dir: Path) -> Dict:
        """提取單個 run 的信息"""
        timestamp = run_dir.name

        info = {
            "timestamp": timestamp,
            "datetime": self._parse_timestamp(timestamp),
            "path": run_dir.name,
            "files": {}
        }

        # 檢查各文件是否存在並獲取大小
        files_to_check = {
            "master_flow": "00_MASTER_FLOW.md",
            "llm_calls": "01_LLM_CALLS.jsonl",
            "data_flow": "02_DATA_FLOW.md",
            "summary_report": "SUMMARY_REPORT.md",
        }

        step_files = list(run_dir.glob("step_*.md"))

        for key, filename in files_to_check.items():
            filepath = run_dir / filename
            if filepath.exists():
                size = filepath.stat().st_size
                info["files"][key] = {
                    "exists": True,
                    "size_bytes": size,
                    "size_kb": round(size / 1024, 1)
                }
            else:
                info["files"][key] = {"exists": False}

        info["step_count"] = len(step_files)
        info["total_size_bytes"] = sum(
            f.stat().st_size for f in run_dir.glob("*")
            if f.is_file()
        )
        info["total_size_mb"] = round(info["total_size_bytes"] / (1024 * 1024), 1)

        # 統計 LLM 呼叫數
        llm_log = run_dir / "01_LLM_CALLS.jsonl"
        if llm_log.exists():
            try:
                with open(llm_log, "r", encoding="utf-8") as f:
                    info["llm_calls_count"] = sum(1 for _ in f if _.strip())
            except:
                info["llm_calls_count"] = 0
        else:
            info["llm_calls_count"] = 0

        return info

    def _parse_timestamp(self, timestamp: str) -> str:
        """將時間戳轉換為可讀格式"""
        try:
            dt = datetime.strptime(timestamp, "%Y-%m-%d_%H%M%S")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return timestamp

    def _write_empty_index(self):
        """寫入空索引"""
        content = """# REISHI 霊視 v5.4 - 運行記錄索引

還沒有運行記錄。

執行以下命令開始第一次運行：

```bash
python main_v5.py --daily
```

完成後，索引會自動更新。
"""
        with open(self.index_file, "w", encoding="utf-8") as f:
            f.write(content)

    def _write_index(self, runs_info: List[Dict]):
        """寫入索引文件"""
        lines = [
            "# REISHI 霊視 v5.4 - 運行記錄索引",
            "",
            f"**最後更新**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"**總運行次數**: {len(runs_info)}",
            "",
            "---",
            "",
        ]

        # 摘要表格
        lines.extend([
            "## 📊 運行摘要",
            "",
            "| 時間 | 文件數 | LLM 呼叫 | 大小 | 快速查看 |",
            "|------|--------|---------|------|---------|",
        ])

        for info in runs_info:
            timestamp = info["datetime"]
            step_count = info["step_count"]
            llm_count = info["llm_calls_count"]
            total_size = info["total_size_mb"]
            path = info["path"]

            lines.append(
                f"| {timestamp} | {step_count + 4} | {llm_count} | {total_size} MB | "
                f"[查看](#run-{path}) |"
            )

        lines.extend(["", "---", "", "## 🔍 詳細記錄", ""])

        # 詳細信息
        for info in runs_info:
            path = info["path"]
            timestamp = info["datetime"]

            lines.extend([
                f"### Run {path}",
                f"**時間**: {timestamp}",
                "",
            ])

            # 文件列表
            files_exist = [k for k, v in info["files"].items() if v.get("exists")]
            if files_exist:
                lines.append("**文件**:")
                lines.append("")

                if "master_flow" in files_exist:
                    size_kb = info["files"]["master_flow"].get("size_kb", 0)
                    lines.append(
                        f"- [`00_MASTER_FLOW.md`](./{path}/00_MASTER_FLOW.md) "
                        f"({size_kb} KB) - ⭐ 完整執行流程"
                    )

                if "llm_calls" in files_exist:
                    size_kb = info["files"]["llm_calls"].get("size_kb", 0)
                    lines.append(
                        f"- [`01_LLM_CALLS.jsonl`](./{path}/01_LLM_CALLS.jsonl) "
                        f"({size_kb} KB) - LLM 呼叫記錄 ({info['llm_calls_count']} 次)"
                    )

                if "data_flow" in files_exist:
                    size_kb = info["files"]["data_flow"].get("size_kb", 0)
                    lines.append(
                        f"- [`02_DATA_FLOW.md`](./{path}/02_DATA_FLOW.md) "
                        f"({size_kb} KB) - 數據流向"
                    )

                if "summary_report" in files_exist:
                    size_kb = info["files"]["summary_report"].get("size_kb", 0)
                    lines.append(
                        f"- [`SUMMARY_REPORT.md`](./{path}/SUMMARY_REPORT.md) "
                        f"({size_kb} KB) - 最終報告"
                    )

            if info["step_count"] > 0:
                lines.append("")
                lines.append(f"**步驟報告**: {info['step_count']} 份")

            lines.extend([
                "",
                f"**總大小**: {info['total_size_mb']} MB",
                "",
            ])

            # 快速命令
            lines.extend([
                "**快速命令**:",
                "```bash",
                f"# 查看完整執行流程",
                f"cat runs/{path}/00_MASTER_FLOW.md",
                "",
                f"# 查看 LLM 呼叫摘要",
                f"wc -l runs/{path}/01_LLM_CALLS.jsonl",
                "",
                f"# 分析特定股票",
                f"grep 'TICKER' runs/{path}/01_LLM_CALLS.jsonl | jq .",
                "```",
                "",
                "---",
                "",
            ])

        with open(self.index_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print(f"✅ 索引已更新: {self.index_file}")

    def _save_metadata(self, runs_info: List[Dict]):
        """保存 metadata JSON"""
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(runs_info, f, ensure_ascii=False, indent=2)

        print(f"✅ Metadata 已保存: {self.metadata_file}")


def update_run_index(runs_dir: str = "reports/runs"):
    """便利函數：更新索引"""
    generator = RunIndexGenerator(runs_dir)
    generator.generate_index()
