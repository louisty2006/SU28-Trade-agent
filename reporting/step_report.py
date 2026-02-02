"""
REISHI 霊視 v5.0 - 細項步驟報告

每個 Flow 步驟對應一份報告：Flow 步驟名、使用的數據 API、LLM 推理摘要（若適用）。
"""

import os
from typing import Optional, List, Any
from datetime import datetime


def write_step_report(
    report_dir: str,
    step_index: int,
    flow_step_name: str,
    step_short_name: str,
    data_source: Optional[str] = None,
    llm_reasoning: Optional[str] = None,
    extra: Optional[dict] = None,
) -> str:
    """
    寫入單一細項報告到 report_dir/step_{index:02d}_{short_name}.md。
    返回寫入的檔案路徑。
    """
    os.makedirs(report_dir, exist_ok=True)
    safe_name = step_short_name.replace(" ", "_").replace("/", "_")
    fname = f"step_{step_index:02d}_{safe_name}.md"
    path = os.path.join(report_dir, fname)
    lines = [
        "# 細項報告",
        "",
        f"**Flow 步驟 {step_index}**：{flow_step_name}",
        "",
        f"*生成時間*：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
    ]
    if data_source:
        lines.extend(["## 數據來源", "", f"- **API/數據源**：{data_source}", "", ""])
    if llm_reasoning:
        lines.extend(["## LLM 推理摘要", "", llm_reasoning.strip(), "", ""])
    if extra:
        for k, v in extra.items():
            if v is not None and str(v).strip():
                lines.extend([f"## {k}", "", str(v).strip(), "", ""])
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


def write_daily_final_report(
    report_dir: str,
    as_of_date: str,
    analysis_summary: str,
    decision_actions: List[Any],
    executed_trades: List[Any],
    portfolio_value: Optional[float] = None,
    return_pct: Optional[float] = None,
) -> str:
    """
    寫入當日最終報告：分析結果 + 當日行動。
    返回寫入的檔案路徑。
    """
    os.makedirs(report_dir, exist_ok=True)
    path = os.path.join(report_dir, f"daily_{as_of_date}_報告.md")
    lines = [
        f"# REISHI 霊視 v5.0 — 當日報告 ({as_of_date})",
        "",
        f"*生成時間*：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
        "## 分析結果摘要",
        "",
        (analysis_summary or "（無摘要）").strip(),
        "",
        "---",
        "",
        "## 當日決策（LLM 輸出）",
        "",
    ]
    if not decision_actions:
        lines.append("無買賣建議（皆 HOLD 或 0 筆）。")
    else:
        for i, a in enumerate(decision_actions, 1):
            ticker = getattr(a, "ticker", None) or (a.get("ticker") if isinstance(a, dict) else "")
            action = getattr(a, "action", "HOLD") or (a.get("action") if isinstance(a, dict) else "HOLD")
            reasoning = getattr(a, "reasoning", "") or (a.get("reasoning") if isinstance(a, dict) else "")
            pct = getattr(a, "position_size_pct", None) or (a.get("position_size_pct") if isinstance(a, dict) else None)
            lines.append(f"### 指令 #{i}：{action} {ticker}" + (f" {pct}%" if pct is not None else ""))
            if reasoning:
                lines.append("")
                lines.append(reasoning.strip()[:500] + ("..." if len(reasoning) > 500 else ""))
            lines.append("")
    lines.extend(["---", "", "## 實際執行交易", "", ""])
    if not executed_trades:
        lines.append("本日無執行交易。")
    else:
        for tr in executed_trades:
            action = getattr(tr, "action", "?")
            ticker = getattr(tr, "ticker", "?")
            qty = getattr(tr, "quantity", 0)
            price = getattr(tr, "price", 0)
            lines.append(f"- **{action}** {ticker} {qty} 股 @ {price}")
    lines.append("")
    if portfolio_value is not None:
        lines.extend(["---", "", f"**組合市值**：{portfolio_value:,.2f}", ""])
    if return_pct is not None:
        lines.append(f"**累計報酬率**：{return_pct:+.2f}%")
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path
