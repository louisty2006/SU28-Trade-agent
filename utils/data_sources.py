"""
多數據源模組 - 第一性原理：多來源 + 交叉驗證

統一介面：
- get_daily_bars(symbol, start, end) -> DataFrame
- get_close_on_date(symbol, d) -> float | None
- get_close_verified(symbol, d) -> (float, verified: bool, sources: list)

數據源（按可靠性 + 免費額度排序）：
1. Yahoo Finance - 無限制，但有時某段沒資料
2. Stooq（波蘭）- 免費無 key，有美股歷史日線
3. FMP - 250/天
4. Alpha Vantage - 25/天
5. Twelve Data - 800/天
6. Tiingo - 500/天
7. Finnhub - 60/min
8. Polygon - 250/天
9. Marketstack - 100/月
10. IEX Cloud - 1,666/天

設計原則：
- 依序嘗試多個源，直到拿到該日數據
- 若多個源都有數據，可交叉驗證（收盤價差 < 0.5% 視為一致）
- 缺數據明確回傳 None，不用「最後一筆」冒充
"""

import os
import time
import requests
import pandas as pd
from datetime import date, datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any
from abc import ABC, abstractmethod

# 載入 config（若可用）
try:
    from config import (
        FMP_API_KEY, ALPHA_VANTAGE_API_KEY, TWELVE_DATA_API_KEY,
        TIINGO_API_KEY, FINNHUB_API_KEY, POLYGON_API_KEY,
        MARKETSTACK_API_KEY, IEX_CLOUD_API_KEY,
        FMP_BASE_URL, ALPHA_VANTAGE_BASE_URL, TWELVE_DATA_BASE_URL,
        TIINGO_BASE_URL, FINNHUB_BASE_URL, POLYGON_BASE_URL,
        MARKETSTACK_BASE_URL, IEX_CLOUD_BASE_URL,
    )
except ImportError:
    # 允許獨立測試
    from dotenv import load_dotenv
    load_dotenv()
    FMP_API_KEY = os.getenv("FMP_API_KEY", "")
    ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")
    TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "")
    TIINGO_API_KEY = os.getenv("TIINGO_API_KEY", "")
    FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
    POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "")
    MARKETSTACK_API_KEY = os.getenv("MARKETSTACK_API_KEY", "")
    IEX_CLOUD_API_KEY = os.getenv("IEX_CLOUD_API_KEY", "")
    FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"
    ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"
    TWELVE_DATA_BASE_URL = "https://api.twelvedata.com"
    TIINGO_BASE_URL = "https://api.tiingo.com"
    FINNHUB_BASE_URL = "https://finnhub.io/api/v1"
    POLYGON_BASE_URL = "https://api.polygon.io"
    MARKETSTACK_BASE_URL = "http://api.marketstack.com/v1"  # 注意：免費版用 http
    IEX_CLOUD_BASE_URL = "https://cloud.iexapis.com/stable"

# 全域 session
_session = requests.Session()
_session.headers.update({"User-Agent": "StockScanner/4.3"})

# =============================================================================
# 抽象基類：數據源
# =============================================================================

class DataSource(ABC):
    """數據源抽象基類"""
    
    name: str = "base"
    requires_key: bool = False
    daily_limit: int = 999999
    
    @abstractmethod
    def fetch_daily_bars(self, symbol: str, start: date, end: date) -> Optional[pd.DataFrame]:
        """
        取得 [start, end] 內的日線 DataFrame。
        回傳格式：columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        若無資料回傳 None。
        """
        pass
    
    def fetch_close(self, symbol: str, d: date) -> Optional[float]:
        """取得 symbol 在 d 當日的收盤價。預設實作：呼叫 fetch_daily_bars 再取該日。"""
        df = self.fetch_daily_bars(symbol, d, d)
        if df is None or df.empty:
            return None
        # 嘗試找到該日
        df['_date'] = pd.to_datetime(df['Date']).dt.date
        row = df[df['_date'] == d]
        if row.empty:
            return None
        return float(row['Close'].iloc[0])
    
    def is_available(self) -> bool:
        """檢查此數據源是否可用（例如有 API key）"""
        return True


# =============================================================================
# 數據源 1: Yahoo Finance
# =============================================================================

class YahooSource(DataSource):
    """Yahoo Finance 數據源（透過 yfinance）"""
    
    name = "yahoo"
    requires_key = False
    daily_limit = 999999
    
    def fetch_daily_bars(self, symbol: str, start: date, end: date) -> Optional[pd.DataFrame]:
        try:
            import yfinance as yf
            stock = yf.Ticker(symbol)
            # yfinance end 是 exclusive，要含 end 當日須用 end+1
            end_inclusive = end + timedelta(days=1)
            hist = stock.history(start=start.isoformat(), end=end_inclusive.isoformat())
            if hist is None or hist.empty:
                return None
            # 標準化欄位
            hist = hist.reset_index()
            hist = hist.rename(columns={'Date': 'Date', 'Open': 'Open', 'High': 'High', 
                                        'Low': 'Low', 'Close': 'Close', 'Volume': 'Volume'})
            hist['Date'] = pd.to_datetime(hist['Date']).dt.date
            return hist[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        except Exception:
            return None
    
    def fetch_close(self, symbol: str, d: date) -> Optional[float]:
        """Yahoo 特化：先 start/end，無資料再 period 取最近再篩"""
        try:
            import yfinance as yf
            stock = yf.Ticker(symbol)
            end_inclusive = d + timedelta(days=1)
            
            # 方法 1: start/end
            hist = stock.history(start=d.isoformat(), end=end_inclusive.isoformat())
            if hist is not None and not hist.empty:
                return float(hist['Close'].iloc[-1])
            
            # 方法 2: period='1mo' + end
            hist = stock.history(period='1mo', end=end_inclusive.isoformat())
            if hist is not None and not hist.empty:
                hist_dates = hist.index.normalize().date if hasattr(hist.index, 'normalize') else hist.index.date
                mask = [dt <= d for dt in hist_dates]
                filtered = hist[mask]
                if not filtered.empty:
                    # 只取該日（不是「最後一筆」）
                    exact = filtered[filtered.index.normalize().date == d] if hasattr(filtered.index, 'normalize') else filtered[filtered.index.date == d]
                    if not exact.empty:
                        return float(exact['Close'].iloc[-1])
            
            # 方法 3: period='3mo' 不帶 end，再篩
            hist = stock.history(period='3mo')
            if hist is not None and not hist.empty:
                hist_dates = hist.index.normalize().date if hasattr(hist.index, 'normalize') else hist.index.date
                exact_mask = [dt == d for dt in hist_dates]
                exact = hist[exact_mask]
                if not exact.empty:
                    return float(exact['Close'].iloc[-1])
            
            return None
        except Exception:
            return None


# =============================================================================
# 數據源 2: Stooq（波蘭，免費無 key）
# =============================================================================

class StooqSource(DataSource):
    """
    Stooq 數據源 - 波蘭財經網站，免費提供美股歷史日線
    https://stooq.com/q/d/l/?s=AAPL.US&d1=20250101&d2=20250110&i=d
    """
    
    name = "stooq"
    requires_key = False
    daily_limit = 999999
    
    def fetch_daily_bars(self, symbol: str, start: date, end: date) -> Optional[pd.DataFrame]:
        try:
            # Stooq 美股格式：SYMBOL.US
            stooq_symbol = f"{symbol}.US"
            d1 = start.strftime("%Y%m%d")
            d2 = end.strftime("%Y%m%d")
            url = f"https://stooq.com/q/d/l/?s={stooq_symbol}&d1={d1}&d2={d2}&i=d"
            
            df = pd.read_csv(url, parse_dates=['Date'])
            if df is None or df.empty:
                return None
            
            # 標準化欄位
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            df = df.sort_values('Date')
            return df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        except Exception:
            return None


# =============================================================================
# 數據源 3: FMP (Financial Modeling Prep)
# =============================================================================

class FMPSource(DataSource):
    """FMP 數據源 - 250/天免費"""
    
    name = "fmp"
    requires_key = True
    daily_limit = 250
    
    def is_available(self) -> bool:
        return bool(FMP_API_KEY)
    
    def fetch_daily_bars(self, symbol: str, start: date, end: date) -> Optional[pd.DataFrame]:
        if not self.is_available():
            return None
        try:
            url = f"{FMP_BASE_URL}/historical-price-full/{symbol}"
            params = {
                "apikey": FMP_API_KEY,
                "from": start.isoformat(),
                "to": end.isoformat(),
            }
            resp = _session.get(url, params=params, timeout=15)
            if resp.status_code != 200:
                return None
            data = resp.json()
            historical = data.get("historical", [])
            if not historical:
                return None
            
            df = pd.DataFrame(historical)
            df['Date'] = pd.to_datetime(df['date']).dt.date
            df = df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 
                                    'close': 'Close', 'volume': 'Volume'})
            df = df.sort_values('Date')
            return df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        except Exception:
            return None


# =============================================================================
# 數據源 4: Alpha Vantage
# =============================================================================

class AlphaVantageSource(DataSource):
    """Alpha Vantage 數據源 - 25/天免費"""
    
    name = "alpha_vantage"
    requires_key = True
    daily_limit = 25
    
    def is_available(self) -> bool:
        return bool(ALPHA_VANTAGE_API_KEY)
    
    def fetch_daily_bars(self, symbol: str, start: date, end: date) -> Optional[pd.DataFrame]:
        if not self.is_available():
            return None
        try:
            params = {
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "outputsize": "full",  # 取完整歷史
                "apikey": ALPHA_VANTAGE_API_KEY,
            }
            resp = _session.get(ALPHA_VANTAGE_BASE_URL, params=params, timeout=15)
            if resp.status_code != 200:
                return None
            data = resp.json()
            ts = data.get("Time Series (Daily)", {})
            if not ts:
                return None
            
            rows = []
            for dt_str, vals in ts.items():
                dt = datetime.strptime(dt_str, "%Y-%m-%d").date()
                if start <= dt <= end:
                    rows.append({
                        'Date': dt,
                        'Open': float(vals['1. open']),
                        'High': float(vals['2. high']),
                        'Low': float(vals['3. low']),
                        'Close': float(vals['4. close']),
                        'Volume': int(vals['5. volume']),
                    })
            if not rows:
                return None
            df = pd.DataFrame(rows).sort_values('Date')
            return df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        except Exception:
            return None


# =============================================================================
# 數據源 5: Twelve Data
# =============================================================================

class TwelveDataSource(DataSource):
    """Twelve Data 數據源 - 800/天免費"""
    
    name = "twelve_data"
    requires_key = True
    daily_limit = 800
    
    def is_available(self) -> bool:
        return bool(TWELVE_DATA_API_KEY)
    
    def fetch_daily_bars(self, symbol: str, start: date, end: date) -> Optional[pd.DataFrame]:
        if not self.is_available():
            return None
        try:
            url = f"{TWELVE_DATA_BASE_URL}/time_series"
            params = {
                "symbol": symbol,
                "interval": "1day",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "apikey": TWELVE_DATA_API_KEY,
            }
            resp = _session.get(url, params=params, timeout=15)
            if resp.status_code != 200:
                return None
            data = resp.json()
            values = data.get("values", [])
            if not values:
                return None
            
            rows = []
            for v in values:
                rows.append({
                    'Date': datetime.strptime(v['datetime'], "%Y-%m-%d").date(),
                    'Open': float(v['open']),
                    'High': float(v['high']),
                    'Low': float(v['low']),
                    'Close': float(v['close']),
                    'Volume': int(v.get('volume', 0)),
                })
            df = pd.DataFrame(rows).sort_values('Date')
            return df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        except Exception:
            return None


# =============================================================================
# 數據源 6: Tiingo
# =============================================================================

class TiingoSource(DataSource):
    """Tiingo 數據源 - 500/天免費"""
    
    name = "tiingo"
    requires_key = True
    daily_limit = 500
    
    def is_available(self) -> bool:
        return bool(TIINGO_API_KEY)
    
    def fetch_daily_bars(self, symbol: str, start: date, end: date) -> Optional[pd.DataFrame]:
        if not self.is_available():
            return None
        try:
            url = f"{TIINGO_BASE_URL}/tiingo/daily/{symbol}/prices"
            params = {
                "startDate": start.isoformat(),
                "endDate": end.isoformat(),
                "token": TIINGO_API_KEY,
            }
            headers = {"Content-Type": "application/json"}
            resp = _session.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code != 200:
                return None
            data = resp.json()
            if not data:
                return None
            
            rows = []
            for d in data:
                rows.append({
                    'Date': datetime.strptime(d['date'][:10], "%Y-%m-%d").date(),
                    'Open': float(d['open']),
                    'High': float(d['high']),
                    'Low': float(d['low']),
                    'Close': float(d['close']),
                    'Volume': int(d.get('volume', 0)),
                })
            df = pd.DataFrame(rows).sort_values('Date')
            return df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        except Exception:
            return None


# =============================================================================
# 數據源 7: Finnhub
# =============================================================================

class FinnhubSource(DataSource):
    """Finnhub 數據源 - 60/min 免費"""
    
    name = "finnhub"
    requires_key = True
    daily_limit = 1440
    
    def is_available(self) -> bool:
        return bool(FINNHUB_API_KEY)
    
    def fetch_daily_bars(self, symbol: str, start: date, end: date) -> Optional[pd.DataFrame]:
        if not self.is_available():
            return None
        try:
            url = f"{FINNHUB_BASE_URL}/stock/candle"
            # Finnhub 用 UNIX timestamp
            start_ts = int(datetime.combine(start, datetime.min.time()).timestamp())
            end_ts = int(datetime.combine(end, datetime.max.time()).timestamp())
            params = {
                "symbol": symbol,
                "resolution": "D",  # Daily
                "from": start_ts,
                "to": end_ts,
                "token": FINNHUB_API_KEY,
            }
            resp = _session.get(url, params=params, timeout=15)
            if resp.status_code != 200:
                return None
            data = resp.json()
            if data.get("s") != "ok" or not data.get("t"):
                return None
            
            rows = []
            for i, ts in enumerate(data['t']):
                rows.append({
                    'Date': datetime.utcfromtimestamp(ts).date(),
                    'Open': float(data['o'][i]),
                    'High': float(data['h'][i]),
                    'Low': float(data['l'][i]),
                    'Close': float(data['c'][i]),
                    'Volume': int(data['v'][i]),
                })
            df = pd.DataFrame(rows).sort_values('Date')
            return df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        except Exception:
            return None


# =============================================================================
# 數據源 8: Polygon.io
# =============================================================================

class PolygonSource(DataSource):
    """Polygon.io 數據源 - 免費有限"""
    
    name = "polygon"
    requires_key = True
    daily_limit = 250
    
    def is_available(self) -> bool:
        return bool(POLYGON_API_KEY)
    
    def fetch_daily_bars(self, symbol: str, start: date, end: date) -> Optional[pd.DataFrame]:
        if not self.is_available():
            return None
        try:
            url = f"{POLYGON_BASE_URL}/v2/aggs/ticker/{symbol}/range/1/day/{start.isoformat()}/{end.isoformat()}"
            params = {
                "adjusted": "true",
                "sort": "asc",
                "apiKey": POLYGON_API_KEY,
            }
            resp = _session.get(url, params=params, timeout=15)
            if resp.status_code != 200:
                return None
            data = resp.json()
            results = data.get("results", [])
            if not results:
                return None
            
            rows = []
            for r in results:
                # Polygon 的 t 是 milliseconds timestamp
                rows.append({
                    'Date': datetime.utcfromtimestamp(r['t'] / 1000).date(),
                    'Open': float(r['o']),
                    'High': float(r['h']),
                    'Low': float(r['l']),
                    'Close': float(r['c']),
                    'Volume': int(r['v']),
                })
            df = pd.DataFrame(rows).sort_values('Date')
            return df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        except Exception:
            return None


# =============================================================================
# 數據源 9: Marketstack
# =============================================================================

class MarketstackSource(DataSource):
    """Marketstack 數據源 - 100/月免費"""
    
    name = "marketstack"
    requires_key = True
    daily_limit = 3
    
    def is_available(self) -> bool:
        return bool(MARKETSTACK_API_KEY)
    
    def fetch_daily_bars(self, symbol: str, start: date, end: date) -> Optional[pd.DataFrame]:
        if not self.is_available():
            return None
        try:
            url = f"{MARKETSTACK_BASE_URL}/eod"
            params = {
                "access_key": MARKETSTACK_API_KEY,
                "symbols": symbol,
                "date_from": start.isoformat(),
                "date_to": end.isoformat(),
            }
            resp = _session.get(url, params=params, timeout=15)
            if resp.status_code != 200:
                return None
            data = resp.json()
            eod_data = data.get("data", [])
            if not eod_data:
                return None
            
            rows = []
            for d in eod_data:
                rows.append({
                    'Date': datetime.strptime(d['date'][:10], "%Y-%m-%d").date(),
                    'Open': float(d.get('open', 0)),
                    'High': float(d.get('high', 0)),
                    'Low': float(d.get('low', 0)),
                    'Close': float(d.get('close', 0)),
                    'Volume': int(d.get('volume', 0)),
                })
            df = pd.DataFrame(rows).sort_values('Date')
            return df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        except Exception:
            return None


# =============================================================================
# 數據源 10: IEX Cloud
# =============================================================================

class IEXSource(DataSource):
    """IEX Cloud 數據源 - 1,666/天（50,000/月）"""
    
    name = "iex"
    requires_key = True
    daily_limit = 1666
    
    def is_available(self) -> bool:
        return bool(IEX_CLOUD_API_KEY)
    
    def fetch_daily_bars(self, symbol: str, start: date, end: date) -> Optional[pd.DataFrame]:
        if not self.is_available():
            return None
        try:
            # IEX 用 range 或 date 參數；這裡用 chart/date
            url = f"{IEX_CLOUD_BASE_URL}/stock/{symbol}/chart/3m"
            params = {"token": IEX_CLOUD_API_KEY}
            resp = _session.get(url, params=params, timeout=15)
            if resp.status_code != 200:
                return None
            data = resp.json()
            if not data:
                return None
            
            rows = []
            for d in data:
                dt = datetime.strptime(d['date'], "%Y-%m-%d").date()
                if start <= dt <= end:
                    rows.append({
                        'Date': dt,
                        'Open': float(d.get('open', 0) or 0),
                        'High': float(d.get('high', 0) or 0),
                        'Low': float(d.get('low', 0) or 0),
                        'Close': float(d.get('close', 0) or 0),
                        'Volume': int(d.get('volume', 0) or 0),
                    })
            if not rows:
                return None
            df = pd.DataFrame(rows).sort_values('Date')
            return df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        except Exception:
            return None


# =============================================================================
# 數據源 11: EODHD（額外備援）
# =============================================================================

class EODHDSource(DataSource):
    """EODHD 數據源 - 有限免費"""
    
    name = "eodhd"
    requires_key = True
    daily_limit = 20
    
    def __init__(self):
        self.api_key = os.getenv("EODHD_API_KEY", "")
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def fetch_daily_bars(self, symbol: str, start: date, end: date) -> Optional[pd.DataFrame]:
        if not self.is_available():
            return None
        try:
            url = f"https://eodhistoricaldata.com/api/eod/{symbol}.US"
            params = {
                "api_token": self.api_key,
                "from": start.isoformat(),
                "to": end.isoformat(),
                "fmt": "json",
            }
            resp = _session.get(url, params=params, timeout=15)
            if resp.status_code != 200:
                return None
            data = resp.json()
            if not data:
                return None
            
            rows = []
            for d in data:
                rows.append({
                    'Date': datetime.strptime(d['date'], "%Y-%m-%d").date(),
                    'Open': float(d.get('open', 0)),
                    'High': float(d.get('high', 0)),
                    'Low': float(d.get('low', 0)),
                    'Close': float(d.get('close', 0)),
                    'Volume': int(d.get('volume', 0)),
                })
            df = pd.DataFrame(rows).sort_values('Date')
            return df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        except Exception:
            return None


# =============================================================================
# 統一管理器：多數據源 + 交叉驗證
# =============================================================================

class MultiSourceManager:
    """
    多數據源管理器
    - 依序嘗試多個源，直到拿到該日數據
    - 可交叉驗證（fact check）
    """
    
    def __init__(self):
        # 按可靠性 + 免費額度排序
        self.sources: List[DataSource] = [
            YahooSource(),
            StooqSource(),
            FMPSource(),
            TwelveDataSource(),
            TiingoSource(),
            FinnhubSource(),
            PolygonSource(),
            AlphaVantageSource(),
            IEXSource(),
            MarketstackSource(),
            EODHDSource(),
        ]
        self._call_counts: Dict[str, int] = {}
    
    def get_available_sources(self) -> List[str]:
        """回傳可用的數據源名稱列表"""
        return [s.name for s in self.sources if s.is_available()]
    
    def get_daily_bars(self, symbol: str, start: date, end: date, 
                       prefer_sources: List[str] = None) -> Optional[pd.DataFrame]:
        """
        取得 [start, end] 內的日線 DataFrame。
        依序嘗試多個源，直到拿到有效數據。
        
        Args:
            symbol: 股票代碼
            start: 起始日期
            end: 結束日期
            prefer_sources: 優先使用的數據源列表（可選）
        
        Returns:
            DataFrame with columns ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
            若所有源都沒有，回傳 None
        """
        # 決定源順序
        sources = self.sources
        if prefer_sources:
            preferred = [s for s in self.sources if s.name in prefer_sources]
            others = [s for s in self.sources if s.name not in prefer_sources]
            sources = preferred + others
        
        for source in sources:
            if not source.is_available():
                continue
            try:
                df = source.fetch_daily_bars(symbol, start, end)
                if df is not None and not df.empty:
                    self._call_counts[source.name] = self._call_counts.get(source.name, 0) + 1
                    return df
            except Exception as e:
                continue
            time.sleep(0.1)  # 避免太快
        return None
    
    def get_close_on_date(self, symbol: str, d: date,
                          prefer_sources: List[str] = None) -> Optional[float]:
        """
        取得 symbol 在 d 當日的收盤價。
        依序嘗試多個源，直到拿到該日數據。
        
        重要：只回傳**該日**的收盤價，若該日無數據則回傳 None。
        不會用「最後一筆 ≤ d」冒充。
        
        Args:
            symbol: 股票代碼
            d: 日期
            prefer_sources: 優先使用的數據源列表（可選）
        
        Returns:
            收盤價 float，若無該日數據回傳 None
        """
        sources = self.sources
        if prefer_sources:
            preferred = [s for s in self.sources if s.name in prefer_sources]
            others = [s for s in self.sources if s.name not in prefer_sources]
            sources = preferred + others
        
        for source in sources:
            if not source.is_available():
                continue
            try:
                close = source.fetch_close(symbol, d)
                if close is not None:
                    self._call_counts[source.name] = self._call_counts.get(source.name, 0) + 1
                    return close
            except Exception as e:
                continue
            time.sleep(0.1)
        return None
    
    def get_close_verified(self, symbol: str, d: date, 
                           min_sources: int = 2,
                           max_variance_pct: float = 0.5) -> Tuple[Optional[float], bool, List[str]]:
        """
        取得 symbol 在 d 當日的收盤價，並進行交叉驗證（fact check）。
        
        Args:
            symbol: 股票代碼
            d: 日期
            min_sources: 至少需要多少個源同意才視為 verified
            max_variance_pct: 允許的最大價格差異百分比
        
        Returns:
            (close, verified, sources)
            - close: 收盤價（若多源，取平均）
            - verified: 是否通過交叉驗證
            - sources: 有提供數據的源名稱列表
        """
        results: List[Tuple[str, float]] = []
        
        for source in self.sources:
            if not source.is_available():
                continue
            try:
                close = source.fetch_close(symbol, d)
                if close is not None:
                    results.append((source.name, close))
                    self._call_counts[source.name] = self._call_counts.get(source.name, 0) + 1
                    # 若已有足夠源且一致，可提前結束
                    if len(results) >= min_sources:
                        prices = [c for _, c in results]
                        if max(prices) / min(prices) - 1 < max_variance_pct / 100:
                            break
            except Exception:
                continue
            time.sleep(0.1)
        
        if not results:
            return None, False, []
        
        sources_used = [s for s, _ in results]
        prices = [c for _, c in results]
        
        # 只有一個源：無法驗證，但仍回傳
        if len(results) == 1:
            return prices[0], False, sources_used
        
        # 多源：檢查一致性
        variance = (max(prices) / min(prices) - 1) * 100
        verified = len(results) >= min_sources and variance < max_variance_pct
        avg_price = sum(prices) / len(prices)
        
        return avg_price, verified, sources_used
    
    def get_call_stats(self) -> Dict[str, int]:
        """回傳各數據源的呼叫次數統計"""
        return dict(self._call_counts)
    
    def reset_stats(self):
        """重置統計"""
        self._call_counts = {}


# =============================================================================
# 全域實例與便捷函數
# =============================================================================

# 全域管理器
_manager = MultiSourceManager()


def get_daily_bars(symbol: str, start: date, end: date,
                   prefer_sources: List[str] = None) -> Optional[pd.DataFrame]:
    """
    統一介面：取得 [start, end] 內的日線 DataFrame。
    依序嘗試多個數據源，直到拿到有效數據。
    
    Example:
        df = get_daily_bars("AAPL", date(2025, 1, 1), date(2025, 1, 10))
    """
    return _manager.get_daily_bars(symbol, start, end, prefer_sources)


def get_close_on_date(symbol: str, d: date,
                      prefer_sources: List[str] = None) -> Optional[float]:
    """
    統一介面：取得 symbol 在 d 當日的收盤價。
    只回傳**該日**的收盤價，若該日無數據則回傳 None。
    
    Example:
        close = get_close_on_date("AAPL", date(2025, 1, 2))
    """
    return _manager.get_close_on_date(symbol, d, prefer_sources)


def get_close_verified(symbol: str, d: date,
                       min_sources: int = 2,
                       max_variance_pct: float = 0.5) -> Tuple[Optional[float], bool, List[str]]:
    """
    統一介面：取得收盤價 + 交叉驗證（fact check）。
    
    Example:
        close, verified, sources = get_close_verified("AAPL", date(2025, 1, 2))
        if verified:
            print(f"收盤價 {close}，已由 {sources} 驗證")
        elif close is not None:
            print(f"收盤價 {close}，但僅 {sources}，未經驗證")
        else:
            print("該日無數據")
    """
    return _manager.get_close_verified(symbol, d, min_sources, max_variance_pct)


def get_available_sources() -> List[str]:
    """回傳可用的數據源名稱列表"""
    return _manager.get_available_sources()


def get_call_stats() -> Dict[str, int]:
    """回傳各數據源的呼叫次數統計"""
    return _manager.get_call_stats()


def reset_stats():
    """重置統計"""
    _manager.reset_stats()


# =============================================================================
# 測試（獨立執行時）
# =============================================================================

if __name__ == "__main__":
    from datetime import date
    
    print("=" * 60)
    print("多數據源模組測試")
    print("=" * 60)
    
    print(f"\n可用數據源：{get_available_sources()}")
    
    symbol = "AAPL"
    test_date = date(2025, 1, 2)
    
    print(f"\n測試 {symbol} 在 {test_date} 的收盤價...")
    
    # 測試單一收盤價
    close = get_close_on_date(symbol, test_date)
    print(f"  get_close_on_date: {close}")
    
    # 測試交叉驗證
    close_v, verified, sources = get_close_verified(symbol, test_date)
    print(f"  get_close_verified: {close_v}, verified={verified}, sources={sources}")
    
    # 測試日線
    start = date(2025, 1, 2)
    end = date(2025, 1, 10)
    print(f"\n測試 {symbol} 從 {start} 到 {end} 的日線...")
    df = get_daily_bars(symbol, start, end)
    if df is not None:
        print(df.head(10))
    else:
        print("  無數據")
    
    print(f"\n呼叫統計：{get_call_stats()}")
