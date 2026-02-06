"""
REISHI 霊視 v5.0 - Multi-Agent 協作分析（AlphaRock 類格式）

三角色：Fundamental / Sentiment / Valuation(技術)，各用 LLM 產出；
單輪共識 LLM 產出 consensus_action、consensus_score、disagreements、final_recommendation。
data 須包含 market_data、可選 fundamental_by_ticker、sentiment_by_ticker。
"""

import json
import re
import logging
from dataclasses import dataclass
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class AgentAnalysis:
    agent_name: str
    score: float  # 1-10
    action: str  # 'BUY', 'HOLD', 'SELL'
    confidence: float
    key_points: List[str]
    risks: List[str]
    reasoning: str


@dataclass
class MultiAgentResult:
    ticker: str
    individual_analyses: Dict[str, AgentAnalysis]
    consensus_score: float
    consensus_action: str
    disagreements: List[str]
    final_recommendation: str


def _placeholder_analysis(agent_name: str, ticker: str, reason: str = "無數據") -> AgentAnalysis:
    return AgentAnalysis(
        agent_name=agent_name,
        score=5.0,
        action="HOLD",
        confidence=0.3,
        key_points=[reason],
        risks=[],
        reasoning=f"{agent_name} 未取得足夠輸入，暫持觀望。",
    )


def _parse_agent_response(raw: str, agent_name: str, ticker: str) -> Optional[AgentAnalysis]:
    raw = (raw or "").strip()
    if not raw:
        return None
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.IGNORECASE)
    if m:
        raw = m.group(1).strip()
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        action = (data.get("action") or "HOLD").upper()
        if action not in ("BUY", "HOLD", "SELL"):
            action = "HOLD"
        score = float(data.get("score", 5))
        score = max(1, min(10, score))
        confidence = float(data.get("confidence", 0.5))
        confidence = max(0, min(1, confidence))
        kp = data.get("key_points") or data.get("key_points_list") or []
        key_points = [str(x) for x in (kp if isinstance(kp, list) else [])[:5]]
        r = data.get("risks") or data.get("risks_list") or []
        risks = [str(x) for x in (r if isinstance(r, list) else [])[:5]]
        reasoning = str(data.get("reasoning") or data.get("reason") or "")[:500]
        return AgentAnalysis(
            agent_name=agent_name,
            score=score,
            action=action,
            confidence=confidence,
            key_points=key_points or ["（未解析）"],
            risks=risks,
            reasoning=reasoning or "（無）",
        )
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def _parse_consensus_response(raw: str, ticker: str) -> Optional[tuple]:
    """Returns (consensus_action, consensus_score, disagreements, final_recommendation) or None."""
    raw = (raw or "").strip()
    if not raw:
        return None
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.IGNORECASE)
    if m:
        raw = m.group(1).strip()
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        action = (data.get("consensus_action") or data.get("action") or "HOLD").upper()
        if action not in ("BUY", "HOLD", "SELL"):
            action = "HOLD"
        score = float(data.get("consensus_score") or data.get("score") or 5)
        score = max(1, min(10, score))
        dis = data.get("disagreements") or data.get("disagreements_list") or []
        disagreements = [str(x) for x in (dis if isinstance(dis, list) else [])[:5]]
        rec = str(data.get("final_recommendation") or data.get("recommendation") or f"{ticker}: 持有觀望")[:300]
        return (action, score, disagreements, rec)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


class MultiAgentAnalysis:
    """Multi-Agent 協作：三角色 + 單輪共識（AlphaRock 類格式）。"""

    def __init__(self):
        self._llm = None

    def _get_llm(self):
        if self._llm is None:
            try:
                from core.llm_clients import LLMClients
                self._llm = LLMClients()
            except ImportError:
                pass
        return self._llm

    def _call_agent(self, prompt: str, system: str, provider_hint: str) -> Optional[str]:
        llm = self._get_llm()
        if not llm or not llm.has_any_key():
            return None
        try:
            text, _ = llm.call(prompt, system_prompt=system, provider_hint=provider_hint, timeout=90)
            return text
        except Exception as e:
            logger.warning("multi_agent LLM %s: %s", provider_hint, e)
            return None

    def analyze(self, ticker: str, data: dict) -> MultiAgentResult:
        """
        單一標的完整 Multi-Agent 分析。
        data 應含: market_data, fundamental_by_ticker (可選), sentiment_by_ticker (可選)
        """
        individual: Dict[str, AgentAnalysis] = {}
        fundamental = (data.get("fundamental_by_ticker") or {}).get(ticker)
        sentiment = (data.get("sentiment_by_ticker") or {}).get(ticker)
        market_data = data.get("market_data") or {}
        df = market_data.get(ticker) if isinstance(market_data, dict) else None

        # --- Fundamental Agent (Scitely) ---
        if fundamental is not None and getattr(fundamental, "summary_text", None):
            sys_f = "你是基本面分析師。根據提供的財務摘要，給出 BUY/HOLD/SELL、1-10 分、信心度、key_points、risks、reasoning。輸出單一 JSON，欄位: action, score, confidence, key_points (陣列), risks (陣列), reasoning。"
            prompt_f = f"股票 {ticker} 基本面摘要：\n{getattr(fundamental, 'summary_text', '')}\n\n請輸出 JSON。"
            raw_f = self._call_agent(prompt_f, sys_f, "scitely")
            a_f = _parse_agent_response(raw_f, "Fundamental", ticker) if raw_f else None
            individual["Fundamental"] = a_f or _placeholder_analysis("Fundamental", ticker, "LLM 未回傳")
        else:
            individual["Fundamental"] = _placeholder_analysis("Fundamental", ticker, "無基本面數據")

        # --- Sentiment Agent (Mistral) ---
        if sentiment is not None and getattr(sentiment, "key_factors", None):
            sys_s = "你是情緒分析師。根據情緒結果，給出 BUY/HOLD/SELL、1-10 分、信心度、key_points、risks、reasoning。輸出單一 JSON，欄位: action, score, confidence, key_points, risks, reasoning。"
            factors = getattr(sentiment, "key_factors", []) or []
            risks_s = getattr(sentiment, "risks", []) or []
            score_s = getattr(sentiment, "score", 0.5)
            prompt_s = f"股票 {ticker} 情緒：score={score_s}，key_factors={factors}，risks={risks_s}\n\n請輸出 JSON。"
            raw_s = self._call_agent(prompt_s, sys_s, "mistral")
            a_s = _parse_agent_response(raw_s, "Sentiment", ticker) if raw_s else None
            individual["Sentiment"] = a_s or _placeholder_analysis("Sentiment", ticker, "LLM 未回傳")
        else:
            individual["Sentiment"] = _placeholder_analysis("Sentiment", ticker, "無情緒數據")

        # --- Valuation/Technical Agent (Cohere) ---
        tech_desc = "無 K 線數據"
        if df is not None and hasattr(df, "iloc") and len(df) >= 5:
            try:
                close = df["Close"].iloc[-1]
                high_20 = df["High"].iloc[-20:].max() if len(df) >= 20 else df["High"].max()
                low_20 = df["Low"].iloc[-20:].min() if len(df) >= 20 else df["Low"].min()
                tech_desc = f"收盤 {close:.2f}，近20日高 {high_20:.2f}，低 {low_20:.2f}"
            except Exception:
                pass
        sys_v = "你是估值/技術分析師。根據價格與技術描述，給出 BUY/HOLD/SELL、1-10 分、信心度、key_points、risks、reasoning。輸出單一 JSON，欄位: action, score, confidence, key_points, risks, reasoning。"
        prompt_v = f"股票 {ticker} 技術/估值：{tech_desc}\n\n請輸出 JSON。"
        raw_v = self._call_agent(prompt_v, sys_v, "cohere")
        a_v = _parse_agent_response(raw_v, "Valuation", ticker) if raw_v else None
        individual["Valuation"] = a_v or _placeholder_analysis("Valuation", ticker, tech_desc)

        # --- Consensus (OpenRouter) ---
        lines = []
        for name, ana in individual.items():
            lines.append(f"{name}: action={ana.action}, score={ana.score}, reasoning={ana.reasoning[:150]}")
        consensus_text = "\n".join(lines)
        sys_c = "你是協調者。根據三位分析師的結論，輸出共識。JSON 欄位: consensus_action (BUY/HOLD/SELL), consensus_score (1-10), disagreements (字串陣列), final_recommendation (一句話建議)。"
        prompt_c = f"股票 {ticker} 三位分析師結論：\n{consensus_text}\n\n請輸出共識 JSON。"
        raw_c = self._call_agent(prompt_c, sys_c, "openrouter")
        parsed = _parse_consensus_response(raw_c, ticker) if raw_c else None
        if parsed:
            action, score, disagreements, rec = parsed
        else:
            actions = [a.action for a in individual.values()]
            action = "HOLD"
            if actions.count("BUY") > actions.count("SELL") and actions.count("BUY") >= 2:
                action = "BUY"
            elif actions.count("SELL") > actions.count("BUY") and actions.count("SELL") >= 2:
                action = "SELL"
            score = sum(a.score for a in individual.values()) / len(individual) if individual else 5
            disagreements = ["共識 LLM 未回傳，以多數決代替"]
            rec = f"{ticker}: {action}（共識回退）"

        return MultiAgentResult(
            ticker=ticker,
            individual_analyses=individual,
            consensus_score=score,
            consensus_action=action,
            disagreements=disagreements or [],
            final_recommendation=rec,
        )

    def analyze_all(self, candidates: List, data: dict) -> dict:
        """
        批量分析。candidates 為 PatternCandidate 列表；data 含 market_data、fundamental_by_ticker、sentiment_by_ticker（可選）。
        回傳 { "by_ticker": { ticker: MultiAgentResult }, "summary": "..." } 以兼容現有流程與決策摘要。
        """
        by_ticker: Dict[str, MultiAgentResult] = {}
        tickers_done = []
        for c in candidates or []:
            ticker = getattr(c, "ticker", None)
            if not ticker:
                continue
            result = self.analyze(ticker, data)
            by_ticker[ticker] = result
            tickers_done.append(ticker)
        summary_parts = [f"{t}: {by_ticker[t].consensus_action} ({by_ticker[t].final_recommendation[:50]}...)" for t in tickers_done[:5]]
        summary = "Multi-Agent 分析完成。\n" + "\n".join(summary_parts) if summary_parts else "Multi-Agent 分析完成（無候選）。"
        print(f"[REISHI] [Multi-Agent] 完成 候選數={len(by_ticker)}，前5檔共識={[f'{t}: {by_ticker[t].consensus_action}' for t in tickers_done[:5]]}")
        return {"by_ticker": by_ticker, "summary": summary}