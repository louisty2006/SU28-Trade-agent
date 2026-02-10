"""
REISHI 霊視 v5.0 - Multi-Agent 協作分析（原設計完整版）

四角色：Fundamental / Technical / Sentiment / Risk，各用專屬 LLM 產出；
單輪共識 LLM 產出 consensus_action、consensus_score、disagreements、final_recommendation。
Provider 映射（與原設計一致）：
- Fundamental Agent → Scitely（基本面分析）
- Technical Agent → Cohere（技術面分析）
- Sentiment Agent → OpenRouter（情緒分析）
- Risk Agent → Mistral（風險評估）
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
        logger.warning(f"[Multi-Agent] {agent_name} 對 {ticker} 無回應")
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

        # 改進：支持文字格式的 confidence 映射為數字
        conf_raw = data.get("confidence", 0.5)
        if isinstance(conf_raw, str):
            conf_str = conf_raw.upper()
            if conf_str in ("LOW", "L"):
                confidence = 0.3
            elif conf_str in ("MEDIUM", "MED", "M"):
                confidence = 0.5
            elif conf_str in ("HIGH", "H"):
                confidence = 0.8
            else:
                try:
                    confidence = float(conf_raw)
                except ValueError:
                    confidence = 0.5
        else:
            confidence = float(conf_raw)
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
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.warning(f"[Multi-Agent] {agent_name} 對 {ticker} 解析失敗: {e}")
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
    """Multi-Agent 協作：四角色 + 單輪共識（原設計完整版）。"""

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

    def _call_agent(self, prompt: str, system: str, provider_hint: str,
                     agent_role: str = "unknown", ticker: str = None) -> Optional[str]:
        llm = self._get_llm()
        if not llm or not llm.has_any_key():
            return None
        try:
            text, _ = llm.call(
                prompt, system_prompt=system, provider_hint=provider_hint, timeout=90,
                step_index=6, step_name="Multi-Agent 協作分析",
                agent_role=agent_role, ticker=ticker,
            )
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
            sys_f = "你是基本面分析師。根據提供的財務摘要，給出 BUY/HOLD/SELL、1-10 分、信心度、key_points、risks、reasoning。輸出單一 JSON，欄位: action, score (數字1-10), confidence (數字0-1，例如0.7), key_points (字串陣列), risks (字串陣列), reasoning (字串)。"
            prompt_f = f"股票 {ticker} 基本面摘要：\n{getattr(fundamental, 'summary_text', '')}\n\n請輸出 JSON，格式範例：{{\"action\":\"HOLD\",\"score\":6,\"confidence\":0.65,\"key_points\":[\"...\"],\"risks\":[\"...\"],\"reasoning\":\"...\"}}"
            raw_f = self._call_agent(prompt_f, sys_f, "scitely", agent_role="Fundamental Agent", ticker=ticker)
            a_f = _parse_agent_response(raw_f, "Fundamental", ticker) if raw_f else None
            individual["Fundamental"] = a_f or _placeholder_analysis("Fundamental", ticker, "LLM 未回傳")
        else:
            individual["Fundamental"] = _placeholder_analysis("Fundamental", ticker, "無基本面數據")

        # --- Technical Agent (Cohere) ---
        tech_desc = "無 K 線數據"
        if df is not None and hasattr(df, "iloc") and len(df) >= 5:
            try:
                close = df["Close"].iloc[-1]
                high_20 = df["High"].iloc[-20:].max() if len(df) >= 20 else df["High"].max()
                low_20 = df["Low"].iloc[-20:].min() if len(df) >= 20 else df["Low"].min()
                tech_desc = f"收盤 {close:.2f}，近20日高 {high_20:.2f}，低 {low_20:.2f}"
            except Exception:
                pass
        sys_t = "你是技術分析師。根據價格與技術指標，給出 BUY/HOLD/SELL、1-10 分、信心度、key_points、risks、reasoning。輸出單一 JSON，欄位: action, score (數字1-10), confidence (數字0-1，例如0.7), key_points (字串陣列), risks (字串陣列), reasoning (字串)。"
        prompt_t = f"股票 {ticker} 技術描述：{tech_desc}\n\n請輸出 JSON，格式範例：{{\"action\":\"HOLD\",\"score\":6,\"confidence\":0.65,\"key_points\":[\"...\"],\"risks\":[\"...\"],\"reasoning\":\"...\"}}"
        raw_t = self._call_agent(prompt_t, sys_t, "cohere", agent_role="Technical Agent", ticker=ticker)
        a_t = _parse_agent_response(raw_t, "Technical", ticker) if raw_t else None
        individual["Technical"] = a_t or _placeholder_analysis("Technical", ticker, tech_desc)

        # --- Sentiment Agent (OpenRouter) ---
        if sentiment is not None and getattr(sentiment, "key_factors", None):
            sys_s = "你是情緒分析師。根據市場情緒和新聞分析，給出 BUY/HOLD/SELL、1-10 分、信心度、key_points、risks、reasoning。輸出單一 JSON，欄位: action, score (數字1-10), confidence (數字0-1，例如0.7), key_points (字串陣列), risks (字串陣列), reasoning (字串)。"
            factors = getattr(sentiment, "key_factors", []) or []
            risks_s = getattr(sentiment, "risks", []) or []
            score_s = getattr(sentiment, "score", 0.5)
            prompt_s = f"股票 {ticker} 市場情緒：score={score_s}，key_factors={factors}，risks={risks_s}\n\n請輸出 JSON，格式範例：{{\"action\":\"HOLD\",\"score\":6,\"confidence\":0.65,\"key_points\":[\"...\"],\"risks\":[\"...\"],\"reasoning\":\"...\"}}"
            raw_s = self._call_agent(prompt_s, sys_s, "openrouter", agent_role="Sentiment Agent", ticker=ticker)
            a_s = _parse_agent_response(raw_s, "Sentiment", ticker) if raw_s else None
            individual["Sentiment"] = a_s or _placeholder_analysis("Sentiment", ticker, "LLM 未回傳")
        else:
            individual["Sentiment"] = _placeholder_analysis("Sentiment", ticker, "無情緒數據")

        # --- Risk Agent (Mistral) ---
        # 综合评估各种风险因素
        risk_factors = []
        if fundamental:
            risk_factors.append(f"基本面數據：{getattr(fundamental, 'summary_text', '')[:100]}")
        if sentiment:
            risk_factors.append(f"情緒風險：{getattr(sentiment, 'risks', [])}")
        if df is not None and hasattr(df, "iloc") and len(df) >= 5:
            try:
                volatility = df["Close"].pct_change().std() * 100
                risk_factors.append(f"價格波動率：{volatility:.2f}%")
            except Exception:
                pass
        risk_desc = "; ".join(risk_factors) if risk_factors else "無風險數據"
        sys_r = "你是風險分析師。專注於識別下行風險、市場風險、公司特定風險。給出 BUY/HOLD/SELL、1-10 分（低分=高風險）、信心度、key_points、risks、reasoning。輸出單一 JSON，欄位: action, score (數字1-10), confidence (數字0-1，例如0.7), key_points (字串陣列), risks (字串陣列), reasoning (字串)。"
        prompt_r = f"股票 {ticker} 風險評估：{risk_desc}\n\n請輸出風險分析 JSON，格式範例：{{\"action\":\"HOLD\",\"score\":6,\"confidence\":0.65,\"key_points\":[\"...\"],\"risks\":[\"...\"],\"reasoning\":\"...\"}}"
        raw_r = self._call_agent(prompt_r, sys_r, "mistral", agent_role="Risk Agent", ticker=ticker)
        a_r = _parse_agent_response(raw_r, "Risk", ticker) if raw_r else None
        individual["Risk"] = a_r or _placeholder_analysis("Risk", ticker, risk_desc)

        # --- Consensus (Scitely - 最終協調者) ---
        lines = []
        for name, ana in individual.items():
            lines.append(f"{name}: action={ana.action}, score={ana.score}, reasoning={ana.reasoning[:150]}")
        consensus_text = "\n".join(lines)
        sys_c = "你是最終協調者。根據四位分析師（基本面、技術面、情緒、風險）的結論，整合出共識決策。JSON 欄位: consensus_action (BUY/HOLD/SELL), consensus_score (1-10), disagreements (字串陣列), final_recommendation (一句話建議)。"
        prompt_c = f"股票 {ticker} 四位分析師結論：\n{consensus_text}\n\n請輸出共識 JSON。"
        raw_c = self._call_agent(prompt_c, sys_c, "scitely", agent_role="Consensus Coordinator", ticker=ticker)
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

    def analyze_all(self, candidates: List, data: dict, on_ticker=None) -> dict:
        """
        批量分析。candidates 為 PatternCandidate 列表；data 含 market_data、fundamental_by_ticker、sentiment_by_ticker（可選）。
        on_ticker(ticker, result, index, total) 可選，每完成一檔呼叫一次，供終端顯示進度與擇要。
        回傳 { "by_ticker": { ticker: MultiAgentResult }, "summary": "..." } 以兼容現有流程與決策摘要。
        """
        cand_list = list(candidates or [])
        total = len(cand_list)
        by_ticker: Dict[str, MultiAgentResult] = {}
        tickers_done = []
        if total > 0:
            logger.info(f"[Multi-Agent] 開始分析 {total} 檔（每檔 5 次 LLM：Fundamental/Technical/Sentiment/Risk + Consensus）")
        for idx, c in enumerate(cand_list):
            ticker = getattr(c, "ticker", None)
            if not ticker:
                continue
            result = self.analyze(ticker, data)
            by_ticker[ticker] = result
            tickers_done.append(ticker)
            i = len(tickers_done)
            if callable(on_ticker):
                try:
                    on_ticker(ticker, result, i, total)
                except Exception:
                    pass
            # 每 20 檔在終端印一則擇要，避免刷屏又讓用戶看到進度
            if i % 20 == 0 or i == total:
                rec_short = (result.final_recommendation or "")[:55].replace("\n", " ")
                logger.info(f"[Multi-Agent] [{i}/{total}] {ticker}: {result.consensus_action} — {rec_short}")
        summary_parts = [f"{t}: {by_ticker[t].consensus_action} ({by_ticker[t].final_recommendation[:50]}...)" for t in tickers_done[:5]]
        summary = "Multi-Agent 分析完成。\n" + "\n".join(summary_parts) if summary_parts else "Multi-Agent 分析完成（無候選）。"
        logger.info(f"[Multi-Agent] 完成 候選數={len(by_ticker)}，前5檔共識={[f'{t}: {by_ticker[t].consensus_action}' for t in tickers_done[:5]]}")

        # 寫入 Multi-Agent 步驟詳細報告
        self._write_step_detail(by_ticker, tickers_done)

        return {"by_ticker": by_ticker, "summary": summary}

    def _write_step_detail(self, by_ticker: Dict[str, "MultiAgentResult"], tickers_done: list):
        """寫入 Multi-Agent 步驟的詳細報告，讓用戶能看到每個 agent 的判斷"""
        try:
            from core.llm_clients import get_master_flow_logger
            flow_logger = get_master_flow_logger()
            if not flow_logger:
                return

            lines = []
            lines.append(f"## Multi-Agent 協作分析詳細報告\n")
            lines.append(f"**分析標的數**: {len(by_ticker)}\n")
            lines.append(f"**每檔分析角色**: Fundamental / Technical / Sentiment / Risk + Consensus\n\n")

            for ticker in tickers_done:
                result = by_ticker.get(ticker)
                if not result:
                    continue
                lines.append(f"### {ticker}\n")
                lines.append(f"**共識決策**: {result.consensus_action} (分數: {result.consensus_score:.1f})")
                lines.append(f"**最終建議**: {result.final_recommendation}\n")
                if result.disagreements:
                    lines.append(f"**分歧**: {result.disagreements}\n")

                lines.append("| Agent | 行動 | 分數 | 信心度 | 推理 |")
                lines.append("|-------|------|------|--------|------|")
                for name, ana in result.individual_analyses.items():
                    reasoning_short = (ana.reasoning or "")[:100].replace("\n", " ")
                    lines.append(f"| {name} | {ana.action} | {ana.score:.1f} | {ana.confidence:.2f} | {reasoning_short} |")
                lines.append("")

                # 顯示每個 agent 的重點和風險
                for name, ana in result.individual_analyses.items():
                    if ana.key_points and ana.key_points != ["（未解析）"]:
                        lines.append(f"**{name} 重點**: {ana.key_points}")
                    if ana.risks:
                        lines.append(f"**{name} 風險**: {ana.risks}")
                lines.append("\n---\n")

            flow_logger.write_step_detail_report(
                step_index=6,
                step_name="Multi-Agent 協作分析",
                content="\n".join(lines),
            )
        except Exception as e:
            logger.warning(f"[Multi-Agent] 寫入步驟報告失敗: {e}")