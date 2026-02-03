"""
REISHI 霊視 v5.0 - 即時新聞取得（Finnhub）

為輸入層、因果推理、情緒分析提供公司新聞。
回傳格式相容 analysis.sentiment_analysis.News（headline, source, timestamp, content）。
"""

import os
from datetime import datetime
from typing import List, Dict, Optional, Any

try:
    from config import FINNHUB_API_KEY
except ImportError:
    FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")

FINNHUB_COMPANY_NEWS_URL = "https://finnhub.io/api/v1/company-news"


def fetch_company_news(
    ticker: str,
    from_date: str,
    to_date: str,
    api_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    取得單一標的的公司新聞（Finnhub）。
    from_date / to_date 格式 YYYY-MM-DD。
    回傳 list of dict: headline, source, timestamp (ISO), content (summary), ticker。
    """
    key = (api_key or FINNHUB_API_KEY or "").strip()
    if not key:
        return []
    try:
        import requests
        r = requests.get(
            FINNHUB_COMPANY_NEWS_URL,
            params={"symbol": ticker, "from": from_date, "to": to_date, "token": key},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list):
            return []
        out = []
        for item in data:
            ts = item.get("datetime")
            if ts:
                try:
                    ts_str = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%dT%H:%M:%SZ")
                except Exception:
                    ts_str = str(ts)
            else:
                ts_str = ""
            out.append({
                "headline": item.get("headline") or "",
                "source": item.get("source") or "",
                "timestamp": ts_str,
                "content": item.get("summary") or "",
                "ticker": ticker,
            })
        return out
    except Exception:
        return []


def fetch_news_for_tickers(
    tickers: List[str],
    from_date: str,
    to_date: str,
    api_key: Optional[str] = None,
    max_per_ticker: int = 20,
) -> tuple[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    """
    為多檔標的取得新聞（並行請求，加快速度）。
    回傳 (all_news_flat, news_by_ticker)。
    all_news_flat / news_by_ticker 每筆為 dict: headline, source, timestamp, content, ticker。
    """
    key = (api_key or FINNHUB_API_KEY or "").strip()
    all_news = []
    news_by_ticker = {t: [] for t in tickers}
    if not key:
        return all_news, news_by_ticker
    from concurrent.futures import ThreadPoolExecutor, as_completed
    _workers = min(6, max(1, len(tickers)))
    def _fetch(t):
        items = fetch_company_news(t, from_date, to_date, api_key=key)
        return (t, items[:max_per_ticker])
    with ThreadPoolExecutor(max_workers=_workers) as executor:
        futures = {executor.submit(_fetch, t): t for t in tickers}
        for fut in as_completed(futures):
            ticker, items = fut.result()
            news_by_ticker[ticker] = items
            all_news.extend(items)
    return all_news, news_by_ticker


def to_news_objects(
    items: List[Dict[str, Any]],
) -> List[Any]:
    """
    將 fetch 回來的 dict 轉成 analysis.sentiment_analysis.News（若可用）。
    若無法 import News 則回傳原 dict list（呼叫端可依 key 使用）。
    """
    try:
        from analysis.sentiment_analysis import News
        return [
            News(
                headline=item.get("headline") or "",
                source=item.get("source") or "",
                timestamp=item.get("timestamp") or "",
                content=item.get("content") or "",
            )
            for item in items
        ]
    except ImportError:
        return items
