"""
REISHI 霊視 v5.0 - 基本面分析

使用現有 DataFetcher 取得財報/估值（PE、PB、ROE、營收與盈利成長等），
輸出結構化結果供決策引擎與 Multi-Agent 使用。
回測時使用 get_yahoo_financials_as_of，不取未來數據。
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any


@dataclass
class FundamentalResult:
    """單一標的基本面分析結果"""
    ticker: str
    pe_ratio: float
    pb_ratio: float
    roe: float
    revenue_growth: float
    earnings_growth: float
    profit_margin: float
    sector: str
    industry: str
    market_cap: float
    summary_text: str
    # 可選，供進階使用
    current_ratio: float = 0
    debt_to_equity: float = 0


def _build_summary(fin: Dict[str, Any], ticker: str) -> str:
    """從財務 dict 生成簡短摘要"""
    parts = []
    pe = fin.get("pe_ratio") or fin.get("trailingPE")
    if pe is not None and pe != 0:
        parts.append(f"PE {float(pe):.1f}")
    pb = fin.get("pb_ratio") or fin.get("priceToBook")
    if pb is not None and pb != 0:
        parts.append(f"PB {float(pb):.2f}")
    roe = fin.get("roe")
    if roe is not None:
        parts.append(f"ROE {float(roe):.1f}%")
    rev_g = fin.get("revenue_growth") or (fin.get("revenueGrowth") or 0) * 100
    if rev_g:
        parts.append(f"營收成長 {float(rev_g):.1f}%")
    earn_g = fin.get("earnings_growth") or (fin.get("earningsGrowth") or 0) * 100
    if earn_g:
        parts.append(f"盈利成長 {float(earn_g):.1f}%")
    pm = fin.get("profit_margin") or (fin.get("profitMargins") or 0) * 100
    if pm:
        parts.append(f"利潤率 {float(pm):.1f}%")
    sector = fin.get("sector") or "Unknown"
    industry = fin.get("industry") or "Unknown"
    parts.append(f"{sector}/{industry}")
    return "；".join(parts) if parts else f"{ticker} 無基本面數據"


class FundamentalAnalyzer:
    """基本面分析：拉取財報/估值並輸出結構化結果"""

    def __init__(self):
        try:
            from utils.data_fetcher import DataFetcher
            self._fetcher = DataFetcher()
        except ImportError:
            self._fetcher = None

    def analyze_one(
        self,
        ticker: str,
        as_of_date: Optional[str] = None,
        backtest_start: Optional[str] = None,
    ) -> Optional[FundamentalResult]:
        """
        分析單一標的。
        as_of_date 有值時為回測，使用 get_yahoo_financials_as_of。
        """
        if not self._fetcher:
            return None
        try:
            if as_of_date:
                raw = self._fetcher.get_yahoo_financials_as_of(
                    ticker, as_of_date, backtest_start=backtest_start
                )
                if not raw:
                    return None
                # 回測回傳格式與 yahoo info 相容，直接傳入 extract_financial_data
                fin = self._fetcher.extract_financial_data(raw)
            else:
                info = self._fetcher.get_yahoo_info(ticker)
                if not info:
                    return None
                fin = self._fetcher.extract_financial_data(info)
            return FundamentalResult(
                ticker=ticker,
                pe_ratio=float(fin.get("pe_ratio", 0) or 0),
                pb_ratio=float(fin.get("pb_ratio", 0) or 0),
                roe=float(fin.get("roe", 0) or 0),
                revenue_growth=float(fin.get("revenue_growth", 0) or 0),
                earnings_growth=float(fin.get("earnings_growth", 0) or 0),
                profit_margin=float(fin.get("profit_margin", 0) or 0),
                sector=str(fin.get("sector", "Unknown")),
                industry=str(fin.get("industry", "Unknown")),
                market_cap=float(fin.get("market_cap", 0) or 0),
                summary_text=_build_summary(fin, ticker),
                current_ratio=float(fin.get("current_ratio", 0) or 0),
                debt_to_equity=float(fin.get("debt_to_equity", 0) or 0),
            )
        except Exception as e:
            # Fallback: 不令流程崩潰，寫 log 可選
            try:
                import logging
                logging.getLogger(__name__).warning("fundamental_analysis %s: %s", ticker, e)
            except Exception:
                pass
            return None

    def analyze_batch(
        self,
        tickers: List[str],
        as_of_date: Optional[str] = None,
        backtest_start: Optional[str] = None,
        on_ticker=None,
    ) -> Dict[str, FundamentalResult]:
        """
        批量分析。on_ticker(ticker, index, total) 可選。
        回傳 Dict[ticker, FundamentalResult]，失敗的標的不會出現在 dict 中。
        """
        print(f"[REISHI] [基本面] 開始 batch，ticker 數={len(tickers)}，as_of_date={as_of_date or '即時'}")
        result = {}
        total = len(tickers)
        for idx, ticker in enumerate(tickers):
            if callable(on_ticker):
                on_ticker(ticker, idx + 1, total)
            r = self.analyze_one(ticker, as_of_date=as_of_date, backtest_start=backtest_start)
            if r:
                result[ticker] = r
        preview = [f"{t}: {getattr(result[t], 'summary_text', '')[:35]}…" for t in list(result.keys())[:3]]
        print(f"[REISHI] [基本面] 完成 成功數={len(result)}/{total}，前3檔擇要={preview}")
        return result
