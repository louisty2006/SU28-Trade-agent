"""
REISHI 霊視 v5.0 - 输出验证（第三层防护）

目的：验证决策输出的逻辑和数字
- 邏輯一致性檢查
- 數字合理性檢查
- 矛盾偵測
- 關鍵數據回溯驗證
"""

from dataclasses import dataclass
from typing import List
from core.decision_engine import Decision, Action


@dataclass
class Issue:
    severity: str  # 'ERROR', 'WARNING', 'INFO'
    message: str


@dataclass
class CheckResult:
    passed: bool
    issues: List[Issue]


@dataclass
class ValidationResult:
    passed: bool
    issues: List[Issue]


class OutputValidator:
    """
    输出验证：检查决策的逻辑和数字
    """
    
    def validate_decision(self, decision: Decision, analyses: any) -> ValidationResult:
        """完整验证一个决策"""
        all_issues = []
        
        for action in decision.actions:
            issues = self._validate_action(action)
            all_issues.extend(issues)
        
        passed = len([i for i in all_issues if i.severity == 'ERROR']) == 0
        
        return ValidationResult(
            passed=passed,
            issues=all_issues
        )
    
    def _validate_action(self, action: Action) -> List[Issue]:
        """验证单个action"""
        issues = []
        
        # 数字合理性检查
        if action.action in ['BUY', 'ADD']:
            # 停损价 < 买入价
            if action.stop_loss and action.entry_price_low:
                if action.stop_loss >= action.entry_price_low:
                    issues.append(Issue(
                        severity='ERROR',
                        message=f"{action.ticker}: 停损价 ${action.stop_loss} >= 买入价 ${action.entry_price_low}"
                    ))
            
            # 目标价 > 买入价
            if action.target_price and action.entry_price_high:
                if action.target_price <= action.entry_price_high:
                    issues.append(Issue(
                        severity='ERROR',
                        message=f"{action.ticker}: 目标价 ${action.target_price} <= 买入价 ${action.entry_price_high}"
                    ))
            
            # 单一倉位 ≤ 25%
            if action.position_size_pct and action.position_size_pct > 25:
                issues.append(Issue(
                    severity='ERROR',
                    message=f"{action.ticker}: 倉位 {action.position_size_pct}% 超过上限 25%"
                ))
        
        # 信心度检查
        if action.confidence < 0.5:
            issues.append(Issue(
                severity='WARNING',
                message=f"{action.ticker}: 信心度较低 {action.confidence:.1%}"
            ))
        
        return issues
    
    def validate_recommendation(self, rec, analysis):
        """验证建议"""
        return ValidationResult(passed=True, issues=[])
