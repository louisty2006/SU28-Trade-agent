"""
REISHI 霊視 v5.0 - 决策引擎

目的：根据三大原则做最终决策
- 赚最多：最大化报酬率
- 赚最快：最快达到财务目标
- 风险最少：保护本金
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from datetime import datetime


@dataclass
class Action:
    """交易行动"""
    ticker: str
    action: str  # 'BUY', 'SELL', 'HOLD', 'ADD', 'REDUCE', 'ADJUST_STOP'
    entry_price_low: Optional[float] = None
    entry_price_high: Optional[float] = None
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None
    position_size_pct: Optional[float] = None
    confidence: float = 0.5
    reasoning: str = ""
    risks: List[str] = None
    
    def __post_init__(self):
        if self.risks is None:
            self.risks = []


@dataclass
class Decision:
    """完整决策结果"""
    timestamp: datetime
    actions: List[Action]
    hold_positions: List[Dict]
    overall_assessment: str
    risk_warnings: List[str]
    requires_confirmation: bool = False
    issues: List[Any] = None
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []


@dataclass
class PortfolioState:
    """组合状态"""
    cash: float
    positions: List[Dict]  # [{"ticker": str, "quantity": int, "cost": float, ...}]
    total_value: float
    
    def positions_summary(self) -> str:
        """持倉摘要"""
        if not self.positions:
            return "空倉"
        
        lines = []
        for p in self.positions:
            ticker = p.get('ticker', '')
            qty = p.get('quantity', 0)
            cost = p.get('buy_price', 0)
            current = p.get('current_price', cost)
            pnl_pct = ((current - cost) / cost * 100) if cost > 0 else 0
            lines.append(f"{ticker}: {qty} 股 @ ${cost:.2f}, 當前 ${current:.2f} ({pnl_pct:+.1f}%)")
        
        return "\n".join(lines)


@dataclass
class AllAnalyses:
    """所有分析结果"""
    pattern: Any  # PatternAnalysis
    causal: Any  # CausalAnalysis
    sentiment: Any  # SentimentAnalysis
    multi_agent: Any  # MultiAgentAnalysis
    memory: Any  # MemoryInsights
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "pattern": str(self.pattern) if self.pattern else None,
            "causal": str(self.causal) if self.causal else None,
            "sentiment": str(self.sentiment) if self.sentiment else None,
            "multi_agent": str(self.multi_agent) if self.multi_agent else None,
            "memory": str(self.memory) if self.memory else None
        }
    
    def summary(self) -> str:
        """简要摘要"""
        return f"""
圖表型態: {getattr(self.pattern, 'summary', lambda: '無')() if self.pattern else '無'}
因果推理: {getattr(self.causal, 'summary', lambda: '無')() if self.causal else '無'}
情緒分析: {getattr(self.sentiment, 'summary', lambda: '無')() if self.sentiment else '無'}
Multi-Agent: {getattr(self.multi_agent, 'summary', lambda: '無')() if self.multi_agent else '無'}
霊視記憶: {getattr(self.memory, 'summary', lambda: '無')() if self.memory else '無'}
"""


class DecisionEngine:
    """
    决策引擎
    整合所有分析，根据三大原则做最终决策
    """
    
    DECISION_PROMPT = """
你是 REISHI 霊視的決策核心。

【三大原則】（按優先順序）
1. 賺最多：最大化報酬率
2. 賺最快：最快達到財務目標
3. 風險最少：保護本金

【當前狀態】
現金：{cash:.2f}
持倉：
{positions}

【分析結果】
{analyses}

【任務】
根據三大原則和所有分析結果，決定今天應該採取什麼行動。

可選行動：
- 買入（新建倉位）
- 增持（加碼現有持倉）
- 持有（不動）
- 減持（部分賣出）
- 賣出（全部清倉）
- 調整停損

對每個行動，說明：
1. 具體操作（股票、價格、數量、停損）
2. 理由（為什麼這樣做最符合三大原則）
3. 信心度

如果今天不應該有任何操作，也要說明原因。

【輸出格式】（JSON）
{{
  "actions": [
    {{
      "ticker": "NVDA",
      "action": "BUY",
      "entry_price_low": 135,
      "entry_price_high": 138,
      "stop_loss": 115,
      "target_price": 175,
      "position_size_pct": 8,
      "reasoning": "...",
      "confidence": 0.85,
      "risks": ["風險1", "風險2"]
    }}
  ],
  "hold_positions": [...],
  "overall_assessment": "...",
  "risk_warnings": [...]
}}
"""
    
    def __init__(self, anti_hallucination=None, output_validator=None):
        """
        初始化决策引擎
        
        Args:
            anti_hallucination: 防幻覺機制
            output_validator: 輸出驗證器
        """
        self.anti_hallucination = anti_hallucination
        self.output_validator = output_validator
    
    def decide(self, state: PortfolioState, analyses: AllAnalyses) -> Decision:
        """
        做出今日決策
        
        Args:
            state: 組合狀態
            analyses: 所有分析結果
        
        Returns:
            Decision
        """
        # 1. 準備 prompt
        prompt = self.DECISION_PROMPT.format(
            cash=state.cash,
            positions=state.positions_summary(),
            analyses=analyses.summary()
        )
        
        # 2. 使用防幻覺機制調用 LLM（如果可用）
        if self.anti_hallucination:
            response = self.anti_hallucination.query_with_self_critique(
                prompt=prompt,
                provided_data=analyses.to_dict()
            )
            decision_data = self._parse_decision_from_response(response.final_analysis.content)
        else:
            # 沒有LLM時，返回保守決策
            decision_data = self._default_conservative_decision(state, analyses)
        
        # 3. 解析決策
        decision = self._build_decision(decision_data)
        
        # 4. 驗證決策（如果有驗證器）
        if self.output_validator:
            validation = self.output_validator.validate_decision(decision, analyses)
            
            if not validation.passed:
                decision.issues = validation.issues
                decision.requires_confirmation = True
        
        return decision
    
    def _parse_decision_from_response(self, response: str) -> Dict:
        """從LLM响應解析決策"""
        import json
        
        try:
            # 嘗試解析JSON
            data = json.loads(response)
            return data
        except json.JSONDecodeError:
            # 如果不是JSON，返回默認決策
            return {
                "actions": [],
                "hold_positions": [],
                "overall_assessment": "無法解析LLM響應",
                "risk_warnings": ["LLM響應格式錯誤"]
            }
    
    def _default_conservative_decision(self, state: PortfolioState, analyses: AllAnalyses) -> Dict:
        """默認保守決策（無LLM時）"""
        return {
            "actions": [],
            "hold_positions": [{"ticker": p.get("ticker"), "action": "HOLD"} for p in state.positions],
            "overall_assessment": "無LLM可用，採取保守策略：持有現有倉位",
            "risk_warnings": ["系統未連接LLM，無法進行完整分析"]
        }
    
    def _build_decision(self, data: Dict) -> Decision:
        """構建Decision對象"""
        actions = []
        
        for action_data in data.get("actions", []):
            action = Action(
                ticker=action_data.get("ticker", ""),
                action=action_data.get("action", "HOLD"),
                entry_price_low=action_data.get("entry_price_low"),
                entry_price_high=action_data.get("entry_price_high"),
                stop_loss=action_data.get("stop_loss"),
                target_price=action_data.get("target_price"),
                position_size_pct=action_data.get("position_size_pct"),
                confidence=action_data.get("confidence", 0.5),
                reasoning=action_data.get("reasoning", ""),
                risks=action_data.get("risks", [])
            )
            actions.append(action)
        
        return Decision(
            timestamp=datetime.now(),
            actions=actions,
            hold_positions=data.get("hold_positions", []),
            overall_assessment=data.get("overall_assessment", ""),
            risk_warnings=data.get("risk_warnings", []),
            requires_confirmation=False,
            issues=[]
        )
