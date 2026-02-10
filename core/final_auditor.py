"""
REISHI 霊視 v5.0 - 最终审视（第四层防护）

目的：最后一道LLM检查（只检查，不判断）
- 检查数据一致性
- 检查逻辑矛盾
- 整理异常清单
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import json
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class AuditResult:
    """审计结果"""
    consistency_check: Dict
    logic_check: Dict
    warning_summary: List[str]
    suspicious_points: List[str]


class FinalAuditor:
    """
    最终LLM审视
    角色：审计员（只检查，不判断）
    """
    
    SYSTEM_PROMPT = """
你是 REISHI 霊視的最終審計員。

你的唯一任務是【檢查】，不是【判斷】。

你要做的：
1. 檢查報告內數字是否前後一致
2. 檢查邏輯是否有明顯矛盾
3. 檢查是否有遺漏的警告
4. 把所有異常整理成清單

你不能做的：
1. 不能說「這個分析是對的」或「錯的」
2. 不能加入任何市場判斷
3. 不能修改任何數字或結論
4. 不能說「一切正常」— 只能說「未發現額外異常」

記住：你是審計員，不是分析師。只檢查，不判斷。
"""
    
    def __init__(self):
        self._llm = None

    def _get_llm(self):
        """懒加载 LLM 客户端"""
        if self._llm is None:
            try:
                from core.llm_clients import LLMClients
                self._llm = LLMClients()
            except ImportError:
                pass
        return self._llm

    def audit(self, decision, analyses) -> AuditResult:
        """
        审计完整报告

        Args:
            decision: 决策结果
            analyses: 所有分析结果

        Returns:
            AuditResult
        """
        llm = self._get_llm()

        # 如果没有LLM可用，使用简单规则检查
        if not llm or not llm.has_any_key():
            logger.warning("[FinalAuditor] 無 LLM 可用，使用規則檢查")
            return self._rule_based_audit(decision, analyses)

        # 构建审计prompt
        audit_prompt = self._build_audit_prompt(decision, analyses)

        # 调用LLM进行审计（使用scitely作为审计员）
        try:
            response, provider = llm.call(
                audit_prompt,
                system_prompt=self.SYSTEM_PROMPT,
                provider_hint="scitely",
                timeout=60,
                step_index=9, step_name="最終審計",
                agent_role="Final Auditor",
            )

            if response:
                result = self._parse_audit_response(response)
                if result:
                    logger.info(f"[FinalAuditor] 審計完成，使用 {provider}")
                    return result
        except Exception as e:
            logger.error(f"[FinalAuditor] LLM 審計失敗: {e}")

        # Fallback到规则检查
        logger.warning("[FinalAuditor] LLM 審計失敗，使用規則檢查")
        return self._rule_based_audit(decision, analyses)

    def _build_audit_prompt(self, decision, analyses) -> str:
        """构建审计prompt"""
        prompt_parts = ["請審計以下交易決策報告，檢查數據一致性、邏輯矛盾、遺漏警告。\n"]

        # 添加决策信息
        if decision:
            prompt_parts.append(f"\n### 決策結果\n")
            if hasattr(decision, 'actions'):
                prompt_parts.append(f"行動數量：{len(decision.actions)}\n")
                for i, action in enumerate(decision.actions[:3], 1):  # 只显示前3个
                    prompt_parts.append(
                        f"{i}. {getattr(action, 'ticker', 'N/A')}: "
                        f"{getattr(action, 'action', 'N/A')} @ "
                        f"${getattr(action, 'entry_price', 0):.2f}\n"
                    )

        # 添加分析摘要
        if analyses and isinstance(analyses, dict):
            prompt_parts.append(f"\n### 分析摘要\n")
            for key, value in analyses.items():
                if isinstance(value, str):
                    prompt_parts.append(f"{key}: {value[:200]}...\n")

        prompt_parts.append("\n請以 JSON 格式回應，包含以下欄位：")
        prompt_parts.append("""
{
  "consistency_check": {
    "passed": true/false,
    "issues": ["問題描述1", "問題描述2"]
  },
  "logic_check": {
    "passed": true/false,
    "issues": ["矛盾描述1"]
  },
  "warning_summary": ["警告1", "警告2"],
  "suspicious_points": ["可疑點1", "可疑點2"]
}
""")

        return "".join(prompt_parts)

    def _parse_audit_response(self, response: str) -> Optional[AuditResult]:
        """解析LLM审计响应"""
        try:
            # 提取JSON
            match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response, re.IGNORECASE)
            if match:
                response = match.group(1).strip()

            data = json.loads(response)

            return AuditResult(
                consistency_check=data.get('consistency_check', {'passed': True, 'issues': []}),
                logic_check=data.get('logic_check', {'passed': True, 'issues': []}),
                warning_summary=data.get('warning_summary', []),
                suspicious_points=data.get('suspicious_points', [])
            )
        except Exception as e:
            logger.warning(f"[FinalAuditor] 解析審計回應失敗: {e}")
            return None

    def _rule_based_audit(self, decision, analyses) -> AuditResult:
        """基于规则的简单审计（LLM不可用时的fallback）"""
        issues = []
        warnings = []
        suspicious = []

        # 检查决策是否有行动
        if decision and hasattr(decision, 'actions'):
            if len(decision.actions) == 0:
                warnings.append("決策未產生任何交易行動")
            elif len(decision.actions) > 10:
                suspicious.append(f"決策產生了 {len(decision.actions)} 個行動，數量較多")

            # 检查每个行动的合理性
            for action in decision.actions:
                if hasattr(action, 'entry_price') and hasattr(action, 'stop_loss'):
                    if action.entry_price <= 0:
                        issues.append(f"{action.ticker}: 入場價 ≤ 0")
                    if action.stop_loss >= action.entry_price:
                        issues.append(f"{action.ticker}: 止損價 ({action.stop_loss}) ≥ 入場價 ({action.entry_price})")

        return AuditResult(
            consistency_check={
                'passed': len(issues) == 0,
                'issues': issues
            },
            logic_check={
                'passed': True,
                'issues': []
            },
            warning_summary=warnings,
            suspicious_points=suspicious
        )
