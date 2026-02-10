"""
LLM 調試日誌系統
記錄每個 LLM 調用的詳細過程：Prompt → 回應 → 解析結果
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class LLMDebugLogger:
    """記錄 LLM 調用的詳細過程"""

    def __init__(self, log_dir: str = "logs/llm_debug"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 當前運行的日誌文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_log = self.log_dir / f"llm_run_{timestamp}.log"
        self.json_log = self.log_dir / f"llm_run_{timestamp}.jsonl"

    def log_call(
        self,
        provider: str,
        model: str,
        system_prompt: Optional[str],
        user_prompt: str,
        raw_response: str,
        parsed_result: Optional[Dict[str, Any]],
        ticker: Optional[str] = None,
        agent: Optional[str] = None,
    ):
        """記錄一個完整的 LLM 調用"""

        entry = {
            "timestamp": datetime.now().isoformat(),
            "provider": provider,
            "model": model,
            "ticker": ticker,
            "agent": agent,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "raw_response": raw_response[:500],  # 截斷長回應
            "parsed_result": parsed_result,
        }

        # 寫入 JSONL（方便後續分析）
        with open(self.json_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # 寫入可讀格式日誌
        with open(self.current_log, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*70}\n")
            f.write(f"[{entry['timestamp']}] {agent or 'Unknown'} ({ticker or 'N/A'})\n")
            f.write(f"Provider: {provider} | Model: {model}\n")
            f.write(f"{'-'*70}\n")
            f.write(f"SYSTEM PROMPT:\n{system_prompt or '(無)'}\n\n")
            f.write(f"USER PROMPT:\n{user_prompt}\n\n")
            f.write(f"RAW RESPONSE:\n{raw_response}\n\n")
            f.write(f"PARSED RESULT:\n{json.dumps(parsed_result, ensure_ascii=False, indent=2)}\n")
            f.write(f"{'='*70}\n")

        logger.debug(f"[{agent}] {provider} {model} → {parsed_result}")


# 全局實例
_debug_logger: Optional[LLMDebugLogger] = None


def get_llm_debug_logger() -> LLMDebugLogger:
    """獲取全局 LLM 調試日誌記錄器"""
    global _debug_logger
    if _debug_logger is None:
        _debug_logger = LLMDebugLogger()
    return _debug_logger
