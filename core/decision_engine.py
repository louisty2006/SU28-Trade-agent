"""
REISHI 霊視 v5.0 - 决策引擎

目的：根据三大原则做最终决策
- 赚最多：最大化报酬率
- 赚最快：最快达到财务目标
- 风险最少：保护本金
"""

import time
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
    fundamental: Any = None  # Dict[str, FundamentalResult] 基本面分析（可選）

    def to_dict(self) -> Dict:
        """转换为字典"""
        d = {
            "pattern": str(self.pattern) if self.pattern else None,
            "causal": str(self.causal) if self.causal else None,
            "sentiment": str(self.sentiment) if self.sentiment else None,
            "multi_agent": str(self.multi_agent) if self.multi_agent else None,
            "memory": str(self.memory) if self.memory else None
        }
        if self.fundamental is not None:
            d["fundamental"] = str(self.fundamental)
        return d
    
    def summary(self) -> str:
        """简要摘要"""
        # 处理 pattern（可能是 List[PatternCandidate]）
        pattern_summary = '無'
        if self.pattern:
            if hasattr(self.pattern, 'summary'):
                pattern_summary = self.pattern.summary()
            elif isinstance(self.pattern, list) and len(self.pattern) > 0:
                # 生成详细的候选摘要，包含交易参数
                lines = [f"發現 {len(self.pattern)} 個候選："]
                for c in self.pattern[:3]:  # 最多显示前3个
                    ticker = getattr(c, 'ticker', '?')
                    ptype = getattr(c, 'pattern_type', '?')
                    score = getattr(c, 'score', 0)
                    current = getattr(c, 'current_price', None)
                    entry_low = getattr(c, 'entry_price_low', None)
                    entry_high = getattr(c, 'entry_price_high', None)
                    stop = getattr(c, 'stop_loss', None)
                    target = getattr(c, 'target_price', None)
                    reasoning = getattr(c, 'reasoning', '')
                    
                    line = f"  • {ticker} ({ptype}, 得分 {score:.2f})"
                    if current:
                        line += f", 當前價 ${current:.2f}"
                    if entry_low and entry_high:
                        line += f", 建議進場 ${entry_low:.2f}-${entry_high:.2f}"
                    if stop:
                        risk_pct = ((current - stop) / current * 100) if current else 0
                        line += f", 止損 ${stop:.2f} (風險 {risk_pct:.1f}%)"
                    if target:
                        reward_pct = ((target - current) / current * 100) if current else 0
                        line += f", 目標 ${target:.2f} (潛在報酬 {reward_pct:.1f}%)"
                    if reasoning:
                        line += f", {reasoning}"
                    lines.append(line)
                pattern_summary = "\n".join(lines)
        
        fundamental_summary = '無'
        if self.fundamental and isinstance(self.fundamental, dict):
            lines_f = []
            for t, r in list(self.fundamental.items())[:5]:
                s = getattr(r, 'summary_text', None) or str(r)[:80]
                lines_f.append(f"  • {t}: {s}")
            fundamental_summary = "\n".join(lines_f) if lines_f else '無'
        elif self.fundamental:
            fundamental_summary = str(self.fundamental)[:500]

        multi_agent_summary = '無'
        if self.multi_agent and isinstance(self.multi_agent, dict):
            by_ticker = self.multi_agent.get("by_ticker") or {}
            summary_str = self.multi_agent.get("summary")
            if by_ticker:
                lines_m = []
                for t, res in list(by_ticker.items())[:5]:
                    action = getattr(res, 'consensus_action', 'HOLD')
                    rec = getattr(res, 'final_recommendation', '')[:60]
                    dis = getattr(res, 'disagreements', []) or []
                    lines_m.append(f"  • {t}: {action} — {rec}" + (f" 分歧: {dis[:2]}" if dis else ""))
                multi_agent_summary = "\n".join(lines_m)
            elif summary_str:
                multi_agent_summary = summary_str[:500]
        elif self.multi_agent and hasattr(self.multi_agent, 'summary'):
            multi_agent_summary = self.multi_agent.summary() or '無'

        return f"""
圖表型態: {pattern_summary}
基本面: {fundamental_summary}
因果推理: {getattr(self.causal, 'summary', lambda: '無')() if self.causal else '無'}
情緒分析: {getattr(self.sentiment, 'summary', lambda: '無')() if self.sentiment else '無'}
Multi-Agent: {multi_agent_summary}
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

**使用分析中提供的交易參數**：
- 如果圖表型態分析提供了「建議進場」、「止損」、「目標」價格，請優先使用這些參數
- 你可以根據風險管理原則微調這些參數（例如：收緊止損、調整倉位大小）
- 如果沒有提供價格建議，則需要明確說明為何無法執行該操作

如果今天不應該有任何操作，也要說明原因。

【輸出格式】（JSON）
在「conclusion」欄位中，必須輸出一個 JSON 對象（不是字符串），格式如下：
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
  "hold_positions": [],
  "overall_assessment": "...",
  "risk_warnings": []
}}

注意：conclusion 必須是 JSON 對象，不是字符串。如果無操作，也要輸出 {{"actions": [], "overall_assessment": "原因..."}}
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
    
    def decide(
        self, state: PortfolioState, analyses: AllAnalyses, on_llm_progress=None
    ) -> Decision:
        """
        做出今日決策
        
        on_llm_progress: 可選 callback(phase, total, message) 回報決策引擎內 3 次 LLM 呼叫進度
        """
        # 1. 準備 prompt
        analyses_summary = analyses.summary()
        print(f"[REISHI] [決策引擎] 送給 LLM 的摘要長度={len(analyses_summary)} 字，預覽 300 字：{analyses_summary[:300]}…")
        prompt = self.DECISION_PROMPT.format(
            cash=state.cash,
            positions=state.positions_summary(),
            analyses=analyses_summary
        )
        
        # #region agent log
        try:
            import json
            import time
            with open("/Users/lautinyam/stock_scanner/.cursor/debug.log", "a", encoding="utf-8") as _dbg:
                _dbg.write(json.dumps({"hypothesisId": "H8", "message": "analyses_summary_sent_to_llm", "data": {"summary_len": len(analyses_summary), "summary_preview": analyses_summary[:500], "full_summary": analyses_summary}, "timestamp": int(time.time() * 1000)}, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
        
        # 2. 使用防幻覺機制調用 LLM（如果可用）
        if self.anti_hallucination:
            response = self.anti_hallucination.query_with_self_critique(
                prompt=prompt,
                provided_data=analyses.to_dict(),
                on_llm_progress=on_llm_progress,
            )
            # #region agent log
            try:
                import json
                import time
                _full_content = response.final_analysis.content or ""
                _content = _full_content[:500] if len(_full_content) > 500 else _full_content
                with open("/Users/lautinyam/stock_scanner/.cursor/debug.log", "a", encoding="utf-8") as _dbg:
                    _dbg.write(json.dumps({"hypothesisId": "H6", "message": "llm_response_before_parse", "data": {"content_len": len(_full_content), "content_preview": _content, "full_content": _full_content}, "timestamp": int(time.time() * 1000)}, ensure_ascii=False) + "\n")
            except Exception:
                pass
            # #endregion
            decision_data = self._parse_decision_from_response(response.final_analysis.content)
            if not decision_data.get("actions") and any("格式" in w for w in decision_data.get("risk_warnings", [])):
                decision_data = self._parse_decision_from_response(
                    response.final_analysis.raw_response or response.final_analysis.content
                )
        else:
            # 沒有LLM時，返回保守決策
            decision_data = self._default_conservative_decision(state, analyses)
        
        # 3. 解析決策
        # #region agent log
        try:
            import json
            import time
            _n_actions = len(decision_data.get("actions", []))
            with open("/Users/lautinyam/stock_scanner/.cursor/debug.log", "a", encoding="utf-8") as _dbg:
                _dbg.write(json.dumps({"hypothesisId": "H5", "message": "decision_data_after_parse", "data": {"n_actions": _n_actions, "overall_assessment": (decision_data.get("overall_assessment") or "")[:100]}, "timestamp": int(time.time() * 1000)}, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
        decision = self._build_decision(decision_data)
        acts = getattr(decision, "actions", []) or []
        act_preview = [f"{getattr(a, 'action', '')} {getattr(a, 'ticker', '')}" for a in acts[:3]]
        print(f"[REISHI] [決策引擎] 解析完成 actions 數={len(acts)}，前3筆={act_preview}")
        
        # 若為 LLM 無回應／未配置之保守決策，明確提示
        assessment = (decision.overall_assessment or "").strip()
        if "LLM 無回應" in assessment or "LLM未配置" in assessment:
            print("    ⚠ 決策引擎：LLM 無回應，使用保守決策", flush=True)
        
        # 4. 驗證決策（如果有驗證器）
        if self.output_validator:
            validation = self.output_validator.validate_decision(decision, analyses)
            
            if not validation.passed:
                decision.issues = validation.issues
                decision.requires_confirmation = True
        
        return decision
    
    def _parse_decision_from_response(self, response: str) -> Dict:
        """從LLM响應解析決策（支援防幻覺格式的 conclusion 或純決策 JSON）"""
        import json
        import re
        
        if not response or not response.strip():
            return self._default_decision_dict("LLM 無回應")
        raw = response.strip()
        
        # #region agent log
        try:
            _raw_before = raw[:300]
            with open("/Users/lautinyam/stock_scanner/.cursor/debug.log", "a", encoding="utf-8") as _dbg:
                _dbg.write(json.dumps({"hypothesisId": "H6", "message": "parse_input", "data": {"raw_len": len(raw), "raw_preview": _raw_before}, "timestamp": int(time.time() * 1000)}, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
        
        # 1) Strip markdown code blocks (```json ... ``` or ``` ... ```)
        # More flexible pattern: handles both \n``` and ``` (without newline)
        raw = re.sub(r"```(?:json)?\s*([\s\S]*?)```", r"\1", raw, flags=re.IGNORECASE)
        raw = raw.strip()
        
        # #region agent log
        try:
            _raw_after = raw[:300]
            with open("/Users/lautinyam/stock_scanner/.cursor/debug.log", "a", encoding="utf-8") as _dbg:
                _dbg.write(json.dumps({"hypothesisId": "H6", "message": "parse_after_strip", "data": {"raw_len": len(raw), "raw_preview": _raw_after}, "timestamp": int(time.time() * 1000)}, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
        
        try:
            data = json.loads(raw)
            # #region agent log
            try:
                _has_actions = "actions" in data if isinstance(data, dict) else False
                _has_conclusion = "conclusion" in data if isinstance(data, dict) else False
                with open("/Users/lautinyam/stock_scanner/.cursor/debug.log", "a", encoding="utf-8") as _dbg:
                    _dbg.write(json.dumps({"hypothesisId": "H6", "message": "json_loads_success", "data": {"is_dict": isinstance(data, dict), "has_actions": _has_actions, "has_conclusion": _has_conclusion, "keys": list(data.keys()) if isinstance(data, dict) else None}, "timestamp": int(time.time() * 1000)}, ensure_ascii=False) + "\n")
            except Exception:
                pass
            # #endregion
            if isinstance(data, dict) and "actions" in data:
                return data
            if isinstance(data, dict) and "conclusion" in data:
                inner = data["conclusion"]
                if isinstance(inner, dict) and "actions" in inner:
                    # conclusion is already a decision object
                    return inner
                elif isinstance(inner, str):
                    # conclusion is a string, try to parse it
                    inner_stripped = inner.strip()
                    if inner_stripped.startswith("{") or "actions" in inner_stripped.lower():
                        try:
                            return json.loads(inner_stripped)
                        except json.JSONDecodeError:
                            pass
                    # conclusion is plain text (e.g., "今日無合適標的")
                    # Return valid decision with assessment as the conclusion text
                    return {
                        "actions": [],
                        "hold_positions": [],
                        "overall_assessment": inner_stripped,
                        "risk_warnings": []
                    }
                # conclusion is some other type
                return inner
        except json.JSONDecodeError as e:
            # #region agent log
            try:
                with open("/Users/lautinyam/stock_scanner/.cursor/debug.log", "a", encoding="utf-8") as _dbg:
                    _dbg.write(json.dumps({"hypothesisId": "H6", "message": "json_loads_failed", "data": {"error": str(e), "raw_start": raw[:200]}, "timestamp": int(time.time() * 1000)}, ensure_ascii=False) + "\n")
            except Exception:
                pass
            # #endregion
            pass
        match = re.search(r"\{[\s\S]*\"actions\"[\s\S]*\}", raw)
        if match:
            try:
                _matched = match.group(0)
                # #region agent log
                try:
                    with open("/Users/lautinyam/stock_scanner/.cursor/debug.log", "a", encoding="utf-8") as _dbg:
                        _dbg.write(json.dumps({"hypothesisId": "H6", "message": "regex_match_attempt", "data": {"matched_len": len(_matched), "matched_preview": _matched[:200]}, "timestamp": int(time.time() * 1000)}, ensure_ascii=False) + "\n")
                except Exception:
                    pass
                # #endregion
                return json.loads(_matched)
            except json.JSONDecodeError as e:
                # #region agent log
                try:
                    with open("/Users/lautinyam/stock_scanner/.cursor/debug.log", "a", encoding="utf-8") as _dbg:
                        _dbg.write(json.dumps({"hypothesisId": "H6", "message": "regex_match_parse_failed", "data": {"error": str(e)}, "timestamp": int(time.time() * 1000)}, ensure_ascii=False) + "\n")
                except Exception:
                    pass
                # #endregion
                pass
        return self._default_decision_dict("無法解析 LLM 決策 JSON")
    
    def _default_decision_dict(self, reason: str) -> Dict:
        return {
            "actions": [],
            "hold_positions": [],
            "overall_assessment": reason,
            "risk_warnings": ["LLM響應格式錯誤"] if "解析" in reason else []
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
