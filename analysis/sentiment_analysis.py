"""
REISHI 霊視 v5.0 - LLM 情緒分析

使用即時新聞內容呼叫 LLM，輸出 score / key_factors / risks。
無新聞或 LLM 失敗時回退為中性並標註。
"""

import json
import re
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# 單則新聞最長字數、最多則數
_MAX_NEWS_ITEMS = 10
_MAX_CHARS_PER_ITEM = 200


@dataclass
class News:
    headline: str
    source: str
    timestamp: str
    content: str = ""


@dataclass
class SentimentResult:
    ticker: str
    score: float  # -1.0 ~ +1.0
    confidence: float
    key_factors: List[str]
    risks: List[str]


def _build_news_text(news_list: List[News]) -> str:
    """將新聞列表組合成一段文字，供 LLM 閱讀。"""
    parts = []
    for i, n in enumerate(news_list[: _MAX_NEWS_ITEMS]):
        line = (n.headline or "").strip()
        if n.content:
            line += " " + (n.content or "")[: _MAX_CHARS_PER_ITEM]
        if n.source:
            line += f" (來源: {n.source})"
        if line:
            parts.append(f"[{i+1}] {line}")
    return "\n".join(parts) if parts else ""


def _parse_llm_sentiment(raw: str, ticker: str) -> Optional[SentimentResult]:
    """從 LLM 回傳解析出 score, confidence, key_factors, risks。"""
    raw = (raw or "").strip()
    if not raw:
        return None
    # 嘗試剝掉 markdown 代碼塊
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.IGNORECASE)
    if m:
        raw = m.group(1).strip()
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        score = float(data.get("score", 0.5))
        score = max(-1.0, min(1.0, score))
        confidence = float(data.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))
        kf = data.get("key_factors") or data.get("key_factors_list")
        if isinstance(kf, list):
            key_factors = [str(x) for x in kf[:10]]
        else:
            key_factors = []
        r = data.get("risks") or data.get("risks_list")
        if isinstance(r, list):
            risks = [str(x) for x in r[:10]]
        else:
            risks = []
        return SentimentResult(
            ticker=ticker,
            score=score,
            confidence=confidence,
            key_factors=key_factors or ["（未解析到關鍵因素）"],
            risks=risks,
        )
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.warning("sentiment_analysis parse %s: %s", ticker, e)
        return None


# 中性回退
def _neutral_result(ticker: str, reason: str = "無新聞") -> SentimentResult:
    return SentimentResult(
        ticker=ticker,
        score=0.5,
        confidence=0.5,
        key_factors=[f"市場情緒中性（{reason}）"],
        risks=[],
    )


_SYSTEM_SENTIMENT = """你是股票新聞情緒分析師。根據用戶提供的公司相關新聞，評估對該公司股價的市場情緒。

請僅根據提供的新聞內容作答，不要臆測或使用新聞以外的資訊。

輸出必須為單一 JSON 對象，且包含以下欄位：
- "score": 數值，範圍 -1.0（極度悲觀）到 +1.0（極度樂觀），0 為中性
- "confidence": 數值 0~1，表示你對此情緒判斷的信心度
- "key_factors": 字串陣列，列出影響情緒的關鍵因素（最多 5 項）
- "risks": 字串陣列，列出從新聞中看到的風險或負面因素（若無則 []）

不要輸出 markdown 代碼塊以外的說明，只輸出一個 JSON 對象。"""


class SentimentAnalyzer:
    """LLM 情緒分析：使用新聞內容呼叫 LLM，失敗時回退中性。"""

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

    def analyze_news(self, ticker: str, news_list: List[News]) -> SentimentResult:
        """分析單一標的新聞情緒。有新聞則呼叫 LLM；無新聞或失敗則回退中性。"""
        news_list = news_list or []
        if not news_list:
            return _neutral_result(ticker, "無新聞")

        news_text = _build_news_text(news_list)
        if not news_text.strip():
            return _neutral_result(ticker, "新聞內容為空")

        llm = self._get_llm()
        if not llm or not llm.has_any_key():
            logger.warning("sentiment_analysis: 無 LLM 配置，回退中性")
            return _neutral_result(ticker, "LLM 未配置")

        prompt = f"以下為股票代碼 {ticker} 的相關新聞，請評估市場情緒並輸出 JSON。\n\n{news_text}"
        try:
            response, _ = llm.call(
                prompt,
                system_prompt=_SYSTEM_SENTIMENT,
                provider_hint="mistral",
                timeout=60,
                step_index=5, step_name="情緒分析",
                agent_role="Sentiment Analyzer", ticker=ticker,
            )
            parsed = _parse_llm_sentiment(response, ticker)
            if parsed:
                return parsed
        except Exception as e:
            logger.warning("sentiment_analysis LLM call %s: %s", ticker, e)
        return _neutral_result(ticker, "LLM 失敗或無法解析")

    def analyze_batch(
        self,
        tickers: List[str],
        on_ticker=None,
        news_by_ticker: Optional[Dict[str, List[News]]] = None,
    ) -> Dict[str, SentimentResult]:
        """批量分析多支股票。on_ticker(ticker, index, total) 可選。news_by_ticker 依標的傳入即時新聞。"""
        result = {}
        total = len(tickers)
        news_by_ticker = news_by_ticker or {}
        for idx, ticker in enumerate(tickers):
            if callable(on_ticker):
                on_ticker(ticker, idx + 1, total)
            news_list = news_by_ticker.get(ticker, [])
            result[ticker] = self.analyze_news(ticker, news_list)
        with_news = sum(1 for t in tickers if (news_by_ticker.get(t) or []))
        preview = [(t, getattr(result.get(t), "score", 0.5)) for t in tickers[:5]]
        logger.info(f"[情緒] 完成 檔數={total} 有新聞={with_news}，前5檔 score={preview}")
        return result
