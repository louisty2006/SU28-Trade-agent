"""
REISHI 霊視 v5.0 - LLM情绪分析
"""

from dataclasses import dataclass
from typing import List, Dict


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


class SentimentAnalyzer:
    """LLM 情绪分析"""
    
    def analyze_news(self, ticker: str, news_list: List[News]) -> SentimentResult:
        """分析新闻情绪"""
        # MVP: 简化实现
        return SentimentResult(
            ticker=ticker,
            score=0.5,
            confidence=0.7,
            key_factors=["市场情绪中性"],
            risks=[]
        )
    
    def analyze_batch(self, tickers: List[str], on_ticker=None, news_by_ticker: Dict[str, List["News"]] = None) -> Dict[str, SentimentResult]:
        """批量分析多支股票。on_ticker(ticker, index, total) 可選。news_by_ticker 可選，依標的傳入即時新聞。"""
        result = {}
        total = len(tickers)
        news_by_ticker = news_by_ticker or {}
        for idx, ticker in enumerate(tickers):
            if callable(on_ticker):
                on_ticker(ticker, idx + 1, total)
            news_list = news_by_ticker.get(ticker, [])
            result[ticker] = self.analyze_news(ticker, news_list)
        return result
