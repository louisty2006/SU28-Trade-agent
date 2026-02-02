"""
REISHI 霊視 v5.0 - 最终审视（第四层防护）

目的：最后一道LLM检查（只检查，不判断）
- 检查数据一致性
- 检查逻辑矛盾
- 整理异常清单
"""

from dataclasses import dataclass
from typing import List, Dict


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
    
    def __init__(self, llm_client=None):
        self.llm = llm_client
    
    def audit(self, decision, analyses) -> AuditResult:
        """
        审计完整报告
        
        Args:
            decision: 决策结果
            analyses: 所有分析结果
        
        Returns:
            AuditResult
        """
        # MVP: 简化实现，不调用LLM
        return AuditResult(
            consistency_check={
                'passed': True,
                'issues': []
            },
            logic_check={
                'passed': True,
                'issues': []
            },
            warning_summary=[],
            suspicious_points=[]
        )
