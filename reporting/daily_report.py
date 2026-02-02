"""
REISHI 霊視 v5.0 - 每日报告生成

目的：生成人类可读的每日报告
- 今日行动指令
- 持仓状态
- 异常与警告清单
- 需要确认的项目
- 一键验证连结
"""

from typing import List, Dict, Any
from datetime import datetime
from core.decision_engine import Decision, Action
from core.data_validator import ValidationResult


class DailyReport:
    """每日报告"""
    
    def __init__(self):
        self.timestamp = datetime.now()
        self.actions_text = ""
        self.positions_text = ""
        self.warnings_text = ""
        self.confirmations_text = ""
        self.verification_links_text = ""
        self.analysis_summary_text = ""
    
    def to_text(self) -> str:
        """输出完整报告文本"""
        report = f"""
{'='*70}
REISHI 霊視 v5.0 - 每日報告
{'='*70}

生成時間: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

{self.actions_text}

{self.positions_text}

{self.warnings_text}

{self.confirmations_text}

{self.verification_links_text}

{self.analysis_summary_text}

{'='*70}
"""
        return report
    
    def save(self, filepath: str):
        """保存报告到文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_text())


class DailyReportGenerator:
    """
    每日报告生成器
    """
    
    def generate(self, decision: Decision, analyses: Any, audit: Any = None) -> DailyReport:
        """
        生成完整每日报告
        
        Args:
            decision: 决策结果
            analyses: 所有分析结果
            audit: 审计结果（可选）
        
        Returns:
            DailyReport
        """
        report = DailyReport()
        
        # 1. 今日行动指令
        report.actions_text = self._format_actions(decision.actions)
        
        # 2. 持仓状态
        report.positions_text = self._format_positions(decision.hold_positions)
        
        # 3. 异常与警告清单
        report.warnings_text = self._compile_warnings(decision, audit)
        
        # 4. 需要确认的项目
        report.confirmations_text = self._get_confirmations(decision)
        
        # 5. 一键验证连结
        report.verification_links_text = self._generate_links(decision)
        
        # 6. 分析摘要（可选阅读）
        report.analysis_summary_text = self._summarize_analyses(analyses)
        
        return report
    
    def _format_actions(self, actions: List[Action]) -> str:
        """格式化行动指令"""
        
        output = "═" * 60 + "\n"
        output += "📋 今日行動指令\n"
        output += "═" * 60 + "\n\n"
        
        if not actions:
            output += "今日無操作建議。\n\n"
            return output
        
        for i, action in enumerate(actions, 1):
            output += f"【指令 #{i}】{action.action} {action.ticker}\n"
            output += "─" * 40 + "\n"
            output += f"股票代碼：{action.ticker}\n"
            output += f"操作：{action.action}\n"
            output += f"信心度：{action.confidence:.0%} {'⭐' * int(action.confidence * 5)}\n"
            output += f"\n"
            
            if action.action in ['BUY', 'ADD']:
                output += f"執行細節：\n"
                output += f"  • 價格區間：${action.entry_price_low}-${action.entry_price_high}\n"
                output += f"  • 停損價：${action.stop_loss}\n"
                output += f"  • 目標價：${action.target_price}\n"
                output += f"  • 建議倉位：{action.position_size_pct}%\n"
                output += f"\n"
            
            output += f"理由：\n{action.reasoning}\n"
            output += f"\n"
            
            if action.risks:
                output += f"風險提醒：\n"
                for risk in action.risks:
                    output += f"  ⚠️ {risk}\n"
                output += f"\n"
            
            output += f"執行步驟：\n"
            output += f"  ☐ 1. 確認價格在區間內\n"
            output += f"  ☐ 2. 下單（限價單）\n"
            output += f"  ☐ 3. 設定停損單\n"
            output += f"  ☐ 4. 回報執行結果\n"
            output += f"\n"
        
        return output
    
    def _format_positions(self, positions: List[Dict]) -> str:
        """格式化持仓状态"""
        
        output = "═" * 60 + "\n"
        output += "📊 持倉狀態\n"
        output += "═" * 60 + "\n\n"
        
        if not positions:
            output += "目前無持倉。\n\n"
            return output
        
        for pos in positions:
            ticker = pos.get('ticker', '')
            action = pos.get('action', 'HOLD')
            output += f"{ticker}: {action}\n"
        
        output += "\n"
        return output
    
    def _compile_warnings(self, decision: Decision, audit: Any) -> str:
        """彙整所有警告"""
        
        output = "═" * 60 + "\n"
        output += "⚠️ 異常與警告清單\n"
        output += "═" * 60 + "\n\n"
        
        all_warnings = []
        
        # 从决策中收集
        all_warnings.extend(decision.risk_warnings)
        all_warnings.extend([str(issue) for issue in decision.issues])
        
        # 从审计中收集（如果有）
        if audit:
            all_warnings.extend(getattr(audit, 'warning_summary', []))
            all_warnings.extend(getattr(audit, 'suspicious_points', []))
        
        if not all_warnings:
            output += "✅ 未發現異常\n\n"
            return output
        
        for warning in all_warnings:
            output += f"⚠️ {warning}\n"
        
        output += "\n"
        return output
    
    def _get_confirmations(self, decision: Decision) -> str:
        """需要确认的项目"""
        
        output = "═" * 60 + "\n"
        output += "✋ 需要確認的項目\n"
        output += "═" * 60 + "\n\n"
        
        if not decision.requires_confirmation:
            output += "✅ 所有決策已通過驗證，可直接執行\n\n"
            return output
        
        output += "以下項目需要您的確認：\n\n"
        
        for issue in decision.issues:
            output += f"□ {issue}\n"
        
        output += "\n"
        return output
    
    def _generate_links(self, decision: Decision) -> str:
        """生成一键验证连结"""
        
        output = "═" * 60 + "\n"
        output += "🔗 一鍵驗證連結\n"
        output += "═" * 60 + "\n\n"
        
        for action in decision.actions:
            ticker = action.ticker
            output += f"{ticker}:\n"
            output += f"  • Yahoo Finance: https://finance.yahoo.com/quote/{ticker}\n"
            output += f"  • TradingView: https://www.tradingview.com/symbols/{ticker}\n"
            output += f"  • Google Finance: https://www.google.com/finance/quote/{ticker}:NASDAQ\n"
            output += "\n"
        
        return output
    
    def _summarize_analyses(self, analyses: Any) -> str:
        """分析摘要"""
        
        output = "═" * 60 + "\n"
        output += "📈 分析摘要（可選閱讀）\n"
        output += "═" * 60 + "\n\n"
        
        if hasattr(analyses, 'summary'):
            output += analyses.summary()
        else:
            output += "分析結果摘要不可用\n"
        
        output += "\n"
        return output
