"""
REISHI 霊視 v5.0 - 完整運行日誌記錄系統

功能：
1. 記錄每個 step 的詳細輸入/輸出
2. 記錄每個 LLM call 的完整思考過程
3. 生成 master log 展示完整數據流和 LLM 思考
4. 生成結構化的 step 報告
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class MasterFlowLogger:
    """彙總記錄所有步驟和 LLM 思考的日誌系統"""

    def __init__(self, report_dir: str):
        """
        初始化 Master Flow Logger

        Args:
            report_dir: 報告輸出目錄（例如 reports/daily/2026-02-10_154253）
        """
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)

        # 初始化日誌檔案
        self.master_log = self.report_dir / "00_MASTER_FLOW.md"
        self.llm_log = self.report_dir / "01_LLM_CALLS.jsonl"
        self.data_flow_log = self.report_dir / "02_DATA_FLOW.md"
        self.step_logs = {}  # step_index -> file path

        # 記錄所有事件
        self.events = []  # 時序事件記錄
        self.llm_calls = []  # 所有 LLM 呼叫記錄
        self.data_snapshots = {}  # 數據快照 {step_name -> data}

        # 初始化 master log
        self._init_master_log()

    def _init_master_log(self):
        """初始化 master flow log 檔頭"""
        header = f"""# REISHI 霊視 v5.0 - 完整執行日誌

**生成時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**報告目錄**: {self.report_dir.name}

---

## 📋 目錄

- [執行時序](#執行時序)
- [LLM 思考過程](#llm-思考過程)
- [數據流向](#數據流向)
- [步驟詳情](#步驟詳情)

---

## 執行時序

"""
        with open(self.master_log, "w", encoding="utf-8") as f:
            f.write(header)

    def log_step_start(
        self,
        step_index: int,
        step_name: str,
        step_desc: str,
        input_data: Optional[Dict[str, Any]] = None,
    ):
        """記錄步驟開始"""
        timestamp = datetime.now().isoformat()
        event = {
            "type": "step_start",
            "timestamp": timestamp,
            "step_index": step_index,
            "step_name": step_name,
            "step_desc": step_desc,
            "input_data": input_data,
        }
        self.events.append(event)

        # 寫入 master log
        self._append_master_log(
            f"### [{timestamp}] Step {step_index}: {step_name}\n"
            f"**描述**: {step_desc}\n"
        )

        if input_data:
            self._append_master_log(
                f"**輸入數據**:\n```json\n{json.dumps(input_data, ensure_ascii=False, indent=2)}\n```\n"
            )

        logger.info(f"Step {step_index} [{step_name}] 開始")

    def log_step_end(
        self,
        step_index: int,
        step_name: str,
        output_data: Optional[Dict[str, Any]] = None,
        duration_sec: Optional[float] = None,
    ):
        """記錄步驟結束"""
        timestamp = datetime.now().isoformat()
        event = {
            "type": "step_end",
            "timestamp": timestamp,
            "step_index": step_index,
            "step_name": step_name,
            "output_data": output_data,
            "duration_sec": duration_sec,
        }
        self.events.append(event)

        # 保存數據快照
        self.data_snapshots[step_name] = output_data

        # 寫入 master log
        if output_data:
            self._append_master_log(
                f"**輸出數據**: {len(str(output_data))} 字符\n"
            )
            if isinstance(output_data, dict) and "summary" in output_data:
                self._append_master_log(f"> {output_data['summary']}\n\n")

        if duration_sec:
            self._append_master_log(f"**耗時**: {duration_sec:.2f}s\n\n")

        logger.info(f"Step {step_index} [{step_name}] 完成 ({duration_sec:.2f}s)" if duration_sec else f"Step {step_index} [{step_name}] 完成")

    def log_llm_call(
        self,
        step_index: int,
        step_name: str,
        agent_role: str,
        ticker: Optional[str] = None,
        system_prompt: Optional[str] = None,
        user_prompt: str = "",
        raw_response: str = "",
        parsed_result: Optional[Dict[str, Any]] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        tokens_used: Optional[Dict[str, int]] = None,
    ):
        """記錄 LLM 呼叫及完整思考過程"""
        timestamp = datetime.now().isoformat()

        llm_record = {
            "timestamp": timestamp,
            "step_index": step_index,
            "step_name": step_name,
            "agent_role": agent_role,
            "ticker": ticker,
            "provider": provider,
            "model": model,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt[:3000],  # 完整提示（截斷 3000）
            "raw_response": raw_response[:3000],  # 完整回應（截斷 3000）
            "parsed_result": parsed_result,
            "tokens_used": tokens_used,
        }

        self.llm_calls.append(llm_record)

        # 寫入 JSONL (便於後續分析)
        with open(self.llm_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(llm_record, ensure_ascii=False) + "\n")

        # 寫入 master log (格式化展示)
        self._append_master_log(f"\n#### 🤖 LLM 呼叫 [{agent_role}]")
        if ticker:
            self._append_master_log(f" - {ticker}")
        self._append_master_log(f"\n")

        if provider and model:
            self._append_master_log(f"**提供商**: {provider} | **模型**: {model}\n\n")

        self._append_master_log("**System Prompt**:\n```\n")
        if system_prompt:
            self._append_master_log(system_prompt[:1000])
        else:
            self._append_master_log("(無)")
        self._append_master_log("\n```\n\n")

        self._append_master_log("**User Prompt（送入 LLM 的完整問題）**:\n```\n")
        self._append_master_log(user_prompt[:2000])
        self._append_master_log("\n```\n\n")

        self._append_master_log("**LLM 回應（完整思考與判斷）**:\n```\n")
        self._append_master_log(raw_response[:2000])
        self._append_master_log("\n```\n\n")

        if parsed_result:
            self._append_master_log("**解析後結構化結果**:\n```json\n")
            self._append_master_log(json.dumps(parsed_result, ensure_ascii=False, indent=2)[:1000])
            self._append_master_log("\n```\n\n")

        logger.info(f"LLM call: {agent_role} ({ticker or 'N/A'}) → {provider}")

    def log_data_flow(
        self,
        source_step: str,
        target_step: str,
        data_description: str,
        sample_data: Optional[Any] = None,
    ):
        """記錄數據流向"""
        timestamp = datetime.now().isoformat()

        flow_record = {
            "timestamp": timestamp,
            "source": source_step,
            "target": target_step,
            "description": data_description,
            "sample": str(sample_data)[:500] if sample_data else None,
        }

        # 寫入 data flow log
        with open(self.data_flow_log, "a", encoding="utf-8") as f:
            if not f.tell():  # 檔案為空時寫入頭部
                f.write("# 數據流向記錄\n\n")
            f.write(f"## {source_step} → {target_step}\n")
            f.write(f"**時間**: {timestamp}\n")
            f.write(f"**描述**: {data_description}\n")
            if sample_data:
                f.write(f"**樣本**: {str(sample_data)[:200]}\n\n")

        logger.info(f"Data flow: {source_step} → {target_step}")

    def write_step_detail_report(
        self,
        step_index: int,
        step_name: str,
        content: str,
    ) -> str:
        """
        寫入單個步驟的詳細報告

        Returns:
            報告檔案路徑
        """
        safe_name = step_name.replace(" ", "_").replace("/", "_")
        filename = f"step_{step_index:02d}_{safe_name}.md"
        filepath = self.report_dir / filename

        self.step_logs[step_index] = str(filepath)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# Step {step_index}: {step_name}\n\n")
            f.write(f"**生成時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            f.write(content)

        logger.info(f"步驟報告已寫入: {filename}")
        return str(filepath)

    def finalize(self):
        """完成日誌並生成摘要"""
        # 補充 LLM 思考過程章節（按步驟分組）
        self._append_master_log("\n---\n\n## LLM 思考過程總覽\n\n")
        self._append_master_log(f"**共 {len(self.llm_calls)} 個 LLM 呼叫**\n\n")

        # 按步驟分組
        calls_by_step = {}
        for call in self.llm_calls:
            step_key = f"Step {call.get('step_index', '?')}: {call.get('step_name', '未知')}"
            if step_key not in calls_by_step:
                calls_by_step[step_key] = []
            calls_by_step[step_key].append(call)

        for step_key, calls in calls_by_step.items():
            self._append_master_log(f"### {step_key} ({len(calls)} 次呼叫)\n\n")

            # 按 ticker 分組（如果有的話）
            tickers_seen = {}
            for call in calls:
                ticker = call.get('ticker', 'N/A')
                if ticker not in tickers_seen:
                    tickers_seen[ticker] = []
                tickers_seen[ticker].append(call)

            # 如果 ticker 很多，只顯示摘要表格
            if len(tickers_seen) > 10:
                self._append_master_log(f"| # | Ticker | Agent | Provider | 回應摘要 |\n")
                self._append_master_log(f"|---|--------|-------|----------|----------|\n")
                for idx, (ticker, t_calls) in enumerate(list(tickers_seen.items())[:30], 1):
                    for tc in t_calls:
                        resp_short = (tc.get('raw_response', '') or '')[:80].replace('\n', ' ').replace('|', '/')
                        self._append_master_log(
                            f"| {idx} | {ticker} | {tc.get('agent_role', '?')} | "
                            f"{tc.get('provider', '?')} | {resp_short} |\n"
                        )
                if len(tickers_seen) > 30:
                    self._append_master_log(f"\n... 還有 {len(tickers_seen) - 30} 個 ticker（詳見 01_LLM_CALLS.jsonl）\n")
                self._append_master_log("\n")
            else:
                # 少量呼叫：顯示完整思考過程
                for i, call in enumerate(calls, 1):
                    ticker_label = f" [{call.get('ticker', '')}]" if call.get('ticker') else ""
                    self._append_master_log(
                        f"**{i}. {call['agent_role']}{ticker_label}** "
                        f"(provider: {call.get('provider', '未知')}, model: {call.get('model', '未知')})\n\n"
                    )
                    # 顯示 prompt 摘要
                    prompt_preview = (call.get('user_prompt', '') or '')[:300].replace('\n', '\n> ')
                    self._append_master_log(f"> **問**: {prompt_preview}\n\n")
                    # 顯示完整回應
                    response_preview = (call.get('raw_response', '') or '')[:500].replace('\n', '\n> ')
                    self._append_master_log(f"> **答**: {response_preview}\n\n")
                self._append_master_log("\n")

        # 補充步驟詳情章節
        self._append_master_log("\n---\n\n## 步驟詳情\n\n")
        for idx, path in sorted(self.step_logs.items()):
            self._append_master_log(f"- [Step {idx}]({Path(path).name})\n")

        # 補充執行時序
        self._append_master_log("\n---\n\n### 完整執行時序\n\n")
        for event in self.events:
            ts = event["timestamp"]
            if event["type"] == "step_start":
                self._append_master_log(
                    f"- **[{ts}]** 🟢 Step {event['step_index']} 開始: {event['step_name']}\n"
                )
            elif event["type"] == "step_end":
                duration = f" ({event['duration_sec']:.2f}s)" if event.get('duration_sec') else ""
                self._append_master_log(
                    f"- **[{ts}]** 🔴 Step {event['step_index']} 完成{duration}\n"
                )

        logger.info(f"完整日誌已生成: {self.master_log}")

    def _append_master_log(self, content: str):
        """追加內容到 master log"""
        with open(self.master_log, "a", encoding="utf-8") as f:
            f.write(content)

    def get_summary(self) -> Dict[str, Any]:
        """取得執行摘要"""
        return {
            "total_steps": len(set(e["step_index"] for e in self.events if "step_index" in e)),
            "total_llm_calls": len(self.llm_calls),
            "report_dir": str(self.report_dir),
            "master_log": str(self.master_log),
            "llm_log": str(self.llm_log),
            "data_flow_log": str(self.data_flow_log),
        }


# 全局實例管理
_global_logger: Optional[MasterFlowLogger] = None


def init_master_flow_logger(report_dir: str) -> MasterFlowLogger:
    """初始化全局 Master Flow Logger"""
    global _global_logger
    _global_logger = MasterFlowLogger(report_dir)
    return _global_logger


def get_master_flow_logger() -> Optional[MasterFlowLogger]:
    """取得全局 Master Flow Logger"""
    return _global_logger
