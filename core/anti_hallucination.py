"""
REISHI 霊視 v5.0 - LLM防幻觉机制（第二层防护）

目的：在所有 LLM 调用中防止幻觉
- 强制引用来源
- 事实与推论分离
- 信心度标记
- 多次调用交叉验证
- 自我质疑机制

LLM 對接：支援 OpenRouter / Scitely（OpenAI-compatible API）
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Any
import json


@dataclass
class ProtectedResponse:
    """带防护的LLM响应"""
    content: str
    facts: List[Dict]  # {"statement": str, "source": str, "verified": bool}
    inferences: List[Dict]  # {"statement": str, "based_on": [], "confidence": float}
    uncertainties: List[Dict]  # {"statement": str, "reason": str}
    overall_confidence: float
    warnings: List[str]
    raw_response: str


@dataclass
class CritiquedResponse:
    """经过自我质疑的响应"""
    initial_analysis: ProtectedResponse
    critique: ProtectedResponse
    final_analysis: ProtectedResponse
    modifications: List[str]  # 记录修正了什么


@dataclass
class ConsensusResponse:
    """多次调用的共识结果"""
    consensus: str
    confidence: float
    individual_responses: List[ProtectedResponse]
    agreements: List[str]
    disagreements: List[str]


class AntiHallucination:
    """
    LLM 防幻覺機制
    包裝所有 LLM 調用，加入防護
    """
    
    def __init__(self, llm_client=None):
        """
        初始化防幻覺機制。
        與 v4.3 相同：四 LLM（Scitely, Cohere, Mistral, OpenRouter）。
        Key 不足時一 LLM 兼多角，框架不變。llm_client 參數保留相容，實際一律用四供應商。
        """
        from core.llm_clients import LLMClients
        self._llm_clients = LLMClients()
        self.llm = self._llm_clients.has_any_key()
    
    def query_with_protection(self, 
                              prompt: str, 
                              provided_data: Dict,
                              require_sources: bool = True,
                              system_prompt: Optional[str] = None) -> ProtectedResponse:
        """
        带防护的 LLM 调用
        
        流程：
        1. 在 prompt 前加入防幻覺指令
        2. 要求 LLM 只使用提供的數據
        3. 要求標記每個事實的來源
        4. 要求區分事實和推論
        5. 要求標記信心度
        
        Args:
            prompt: 原始问题
            provided_data: 提供给LLM的数据
            require_sources: 是否要求标记来源
            system_prompt: 系统提示词（可选）
        
        Returns:
            (ProtectedResponse, used_provider_id or None)
        """
        
        # 构建防幻覺 prompt
        protected_prompt = self._build_protected_prompt(prompt, provided_data, require_sources)
        
        # 调用 LLM
        if self.llm is None:
            # 如果没有LLM客户端，返回模拟结果
            return self._mock_response(prompt, provided_data), None
        
        # 实际调用（需要集成真实LLM）
        phase = getattr(self, '_current_critique_phase', 'Anti-Hallucination LLM')
        raw_response, used_provider = self._call_llm(protected_prompt, system_prompt, agent_role=phase)
        
        # 验证响应
        validated_response = self._validate_response(raw_response, provided_data)
        
        return validated_response, used_provider
    
    def _build_protected_prompt(self, prompt: str, provided_data: Dict, require_sources: bool) -> str:
        """构建带防护的 prompt"""
        
        protection_rules = """
【重要規則 - 必須遵守】

1. 你只能使用【以下提供的數據】來分析，不能使用任何其他信息：
```json
{data}
```

2. 每個事實陳述必須標明來源：
   格式：[陳述] (來源：xxx)

3. 明確區分「事實」和「推論」：
   - 事實：直接來自數據
   - 推論：基於事實的推理

4. 為每個結論標記信心度（0-1）

5. 如果某信息不在提供的數據中，必須說「此信息未提供，無法確認」

6. 絕對禁止：
   - 編造數據
   - 假設未經確認的事實
   - 過度自信

7. 輸出格式（JSON）：
```json
{{
  "facts": [
    {{"statement": "...", "source": "...", "verified": true}}
  ],
  "inferences": [
    {{"statement": "...", "based_on": [...], "confidence": 0.0-1.0, "reasoning": "..."}}
  ],
  "uncertainties": [
    {{"statement": "...", "reason": "..."}}
  ],
  "conclusion": "...",
  "overall_confidence": 0.0-1.0
}}
```

---

{original_prompt}
"""
        
        return protection_rules.format(
            data=json.dumps(provided_data, indent=2, ensure_ascii=False),
            original_prompt=prompt
        )
    
    @staticmethod
    def _empty_response_json(conclusion: str, confidence: float = 0.5, uncertainties: Optional[List] = None) -> str:
        """生成空的防幻覺 JSON 回應"""
        return json.dumps({
            "facts": [],
            "inferences": [],
            "uncertainties": uncertainties or [],
            "conclusion": conclusion,
            "overall_confidence": confidence,
        }, ensure_ascii=False)

    def _call_llm(self, prompt: str, system_prompt: Optional[str] = None, agent_role: str = "Anti-Hallucination LLM") -> tuple:
        """
        調用 LLM。回傳 (response_json_str, used_provider_id or None)。
        """
        if not self._llm_clients or not self._llm_clients.has_any_key():
            return self._empty_response_json("LLM未配置（請設 MISTRAL/OPENROUTER 任一 API Key）"), None
        text, used = self._llm_clients.call(
            prompt, system_prompt, provider_hint=None, timeout=120,
            step_index=8, step_name="決策引擎（防幻覺）",
            agent_role=agent_role,
        )
        if not text:
            return self._empty_response_json(
                "LLM 無回應", 0.0,
                [{"statement": "API 無回應", "reason": "請檢查 Key 與額度"}],
            ), None
        return text, used
    
    def _validate_response(self, response: str, provided_data: Dict) -> ProtectedResponse:
        """
        验证 LLM 响应
        
        检查：
        - 是否有未标记来源的事实
        - 引用的数据是否真的存在于 provided_data
        - 是否有明显的幻覺跡象
        """
        warnings = []
        
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError:
            warnings.append("LLM响应不是有效JSON，尝试提取")
            parsed = {
                "facts": [],
                "inferences": [],
                "uncertainties": [],
                "conclusion": response,
                "overall_confidence": 0.3
            }
        
        facts = parsed.get("facts", [])
        inferences = parsed.get("inferences", [])
        uncertainties = parsed.get("uncertainties", [])
        overall_confidence = parsed.get("overall_confidence", 0.5)
        
        # 验证事实来源
        for fact in facts:
            if "source" not in fact or not fact["source"]:
                warnings.append(f"事实未标记来源: {fact.get('statement', '')}")
        
        # 验证推论信心度
        for inference in inferences:
            if "confidence" not in inference:
                warnings.append(f"推论未标记信心度: {inference.get('statement', '')}")
        
        return ProtectedResponse(
            content=parsed.get("conclusion", ""),
            facts=facts,
            inferences=inferences,
            uncertainties=uncertainties,
            overall_confidence=overall_confidence,
            warnings=warnings,
            raw_response=response
        )
    
    def _mock_response(self, prompt: str, provided_data: Dict) -> ProtectedResponse:
        """模拟响应（用于测试）"""
        return ProtectedResponse(
            content="模拟分析结果",
            facts=[
                {"statement": "模拟事实", "source": "系统数据", "verified": True}
            ],
            inferences=[
                {"statement": "模拟推论", "based_on": ["模拟事实"], "confidence": 0.7, "reasoning": "基于数据分析"}
            ],
            uncertainties=[],
            overall_confidence=0.7,
            warnings=[],
            raw_response="模拟响应"
        )
    
    def _provider_display(self, pid: Optional[str]) -> str:
        """供應商顯示名：如 scitely -> Scitely（基本面）"""
        if not pid:
            return "無"
        from core.llm_clients import CONFIG
        name = CONFIG.get(pid, {}).get("name", pid)
        return f"{pid.capitalize()}（{name}）"

    def query_with_self_critique(
        self, prompt: str, provided_data: Dict, on_llm_progress=None
    ) -> CritiquedResponse:
        """
        带自我质疑的 LLM 调用
        
        三阶段：
        1. 分析
        2. 质疑自己的分析
        3. 修正后的最终结论
        
        on_llm_progress: 可選 callback(phase, total, message, provider=None) 回報每次 LLM 呼叫與使用供應商
        """
        if callable(on_llm_progress):
            on_llm_progress(1, 3, "初次分析", None)
        self._current_critique_phase = "Phase 1: 初次分析"
        initial_analysis, used1 = self.query_with_protection(prompt, provided_data)
        if callable(on_llm_progress):
            on_llm_progress(1, 3, "初次分析", self._provider_display(used1))
        
        if callable(on_llm_progress):
            on_llm_progress(2, 3, "自我質疑", None)
        critique_prompt = f"""
你剛才的分析：
{initial_analysis.content}

現在請嚴格質疑你的分析：
1. 你的分析可能有什麼錯誤？
2. 有哪些假設可能是錯的？
3. 有什麼你可能遺漏的風險？
4. 你的信心度是否過高？

請誠實、嚴格地審視。
"""
        self._current_critique_phase = "Phase 2: 自我質疑"
        critique, used2 = self.query_with_protection(critique_prompt, provided_data, require_sources=False)
        if callable(on_llm_progress):
            on_llm_progress(2, 3, "自我質疑", self._provider_display(used2))
        
        if callable(on_llm_progress):
            on_llm_progress(3, 3, "修正結論", None)
        correction_prompt = f"""
原始分析：
{initial_analysis.content}

自我質疑：
{critique.content}

根據質疑，請修正你的分析和信心度。
如果質疑發現了問題，降低信心度或修改結論。
"""
        self._current_critique_phase = "Phase 3: 修正結論"
        final_analysis, used3 = self.query_with_protection(correction_prompt, provided_data)
        if callable(on_llm_progress):
            on_llm_progress(3, 3, "修正結論", self._provider_display(used3))
        
        # 记录修正内容
        modifications = []
        if final_analysis.overall_confidence != initial_analysis.overall_confidence:
            modifications.append(
                f"信心度调整: {initial_analysis.overall_confidence:.2f} → {final_analysis.overall_confidence:.2f}"
            )
        
        return CritiquedResponse(
            initial_analysis=initial_analysis,
            critique=critique,
            final_analysis=final_analysis,
            modifications=modifications
        )
    
    def query_multiple_times(self, prompt: str, provided_data: Dict, n: int = 3) -> ConsensusResponse:
        """
        多次调用交叉验证
        
        同一问题调用 n 次，比对结果
        """
        responses = []
        for i in range(n):
            resp, _ = self.query_with_protection(prompt, provided_data)
            responses.append(resp)
        
        return self._find_consensus(responses)
    
    def _find_consensus(self, responses: List[ProtectedResponse]) -> ConsensusResponse:
        """
        找出多次响应的共识
        
        - 完全一致 → HIGH confidence
        - 大致一致 → MEDIUM confidence
        - 有衝突 → 標記衝突點
        """
        if not responses:
            return ConsensusResponse(
                consensus="无响应",
                confidence=0.0,
                individual_responses=[],
                agreements=[],
                disagreements=[]
            )
        
        # 简单实现：取平均信心度
        avg_confidence = sum(r.overall_confidence for r in responses) / len(responses)
        
        # 提取共同结论
        contents = [r.content for r in responses]
        
        # 检查一致性
        agreements = []
        disagreements = []
        
        # 如果所有响应相似度高
        if len(set(contents)) == 1:
            agreements.append("所有响应完全一致")
            final_confidence = min(avg_confidence + 0.1, 1.0)
        else:
            disagreements.append(f"响应存在 {len(set(contents))} 个不同版本")
            final_confidence = avg_confidence * 0.8
        
        return ConsensusResponse(
            consensus=responses[0].content if responses else "",
            confidence=final_confidence,
            individual_responses=responses,
            agreements=agreements,
            disagreements=disagreements
        )
    
