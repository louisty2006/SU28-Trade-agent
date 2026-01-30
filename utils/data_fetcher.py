"""
數據獲取工具模組（多數據源版）
支援回測：end_date / as_of_date 時取該日為止的歷史數據。

整合多數據源：Yahoo → Stooq → FMP → Twelve Data → ...
"""
import yfinance as yf
import pandas as pd
import requests
import time
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any
from config import (
    FMP_API_KEY,
    FMP_BASE_URL,
    ALLOWED_EXCHANGES,
    STAGE2_CONFIG
)

# 多數據源統一介面
try:
    from utils.data_sources import get_daily_bars, get_close_on_date, get_close_verified
except ImportError:
    # 避免循環 import
    get_daily_bars = None
    get_close_on_date = None
    get_close_verified = None


class DataFetcher:
    """統一的數據獲取接口"""
    
    def __init__(self):
        self.fmp_api_key = FMP_API_KEY
        self.session = requests.Session()
    
    def get_yahoo_history(self, ticker: str, period: str = "30d", end_date: str = None, start_date: str = None) -> Optional[pd.DataFrame]:
        """
        獲取歷史數據（多數據源版）。
        end_date 有值時為回測：取截至該日（含）的數據。
        start_date 有值時限制起始（回測 range 之前看不到）。
        
        優先使用多數據源統一介面，若無則回退到 yfinance。
        """
        try:
            # 嘗試使用多數據源
            if get_daily_bars is not None and end_date:
                # 解析日期
                if isinstance(end_date, str):
                    end_d = datetime.strptime(end_date, "%Y-%m-%d").date()
                else:
                    end_d = end_date
                
                if start_date:
                    if isinstance(start_date, str):
                        start_d = datetime.strptime(start_date, "%Y-%m-%d").date()
                    else:
                        start_d = start_date
                else:
                    # 根據 period 計算 start
                    days_map = {"5d": 5, "1mo": 30, "30d": 30, "3mo": 90, "6mo": 180, "1y": 365}
                    days = days_map.get(period, 30)
                    start_d = end_d - timedelta(days=days)
                
                df = get_daily_bars(ticker, start_d, end_d)
                if df is not None and not df.empty:
                    # 轉換為 yfinance 格式
                    df = df.set_index('Date')
                    df.index = pd.to_datetime(df.index)
                    return df
            
            # 回退到 yfinance
            stock = yf.Ticker(ticker)
            if end_date:
                # yfinance end 是 exclusive，要加一天
                if isinstance(end_date, str):
                    end_d = datetime.strptime(end_date, "%Y-%m-%d").date()
                else:
                    end_d = end_date
                end_inclusive = (end_d + timedelta(days=1)).isoformat()
                
                if start_date:
                    hist = stock.history(start=start_date, end=end_inclusive)
                else:
                    hist = stock.history(period=period, end=end_inclusive)
            else:
                hist = stock.history(period=period)
            
            if hist.empty:
                return None
            
            return hist
        except Exception as e:
            return None
    
    def get_yahoo_info(self, ticker: str) -> Optional[Dict]:
        """
        獲取 Yahoo Finance 股票基本資訊（當前快照）。
        Returns:
            包含股票資訊的字典
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # 驗證交易所
            exchange = str(info.get('exchange', '')).upper()
            if exchange not in ALLOWED_EXCHANGES:
                return None
            
            return info
        except Exception as e:
            return None

    def get_yahoo_financials_as_of(self, ticker: str, as_of_date: str, backtest_start: str = None) -> Optional[Dict[str, Any]]:
        """
        回測用：取截至 as_of_date 的財報與股價（多數據源版）。
        backtest_start 有值時限制數據起始（range 之前看不到）。
        
        股價使用多數據源統一介面；財報仍使用 yfinance。
        """
        try:
            # 解析日期
            as_of_d = pd.Timestamp(as_of_date).date()
            
            # 優先使用多數據源取得股價
            price = None
            if get_close_on_date is not None:
                price = get_close_on_date(ticker, as_of_d)
            
            # 若多數據源無法取得，回退到 yfinance
            if price is None:
                end_ts = pd.Timestamp(as_of_date) + pd.Timedelta(days=1)
                end_str = end_ts.strftime("%Y-%m-%d")
                stock = yf.Ticker(ticker)
                if backtest_start:
                    hist = stock.history(start=backtest_start, end=end_str)
                else:
                    hist = stock.history(period="5d", end=end_str)
                # 若 start/end 無資料，改 period+end 再篩到 as_of_date
                if hist is None or hist.empty:
                    hist = stock.history(period="1mo", end=end_str)
                    if hist is not None and not hist.empty:
                        try:
                            ad = pd.Timestamp(as_of_date).date()
                            mask = hist.index.normalize().date <= ad if hasattr(hist.index, 'normalize') else (hist.index.date <= ad)
                            hist = hist.loc[mask]
                            if backtest_start:
                                bd = pd.Timestamp(backtest_start).date()
                                mask2 = hist.index.normalize().date >= bd if hasattr(hist.index, 'normalize') else (hist.index.date >= bd)
                                hist = hist.loc[mask2]
                        except Exception:
                            pass
                if hist is None or hist.empty:
                    return None
                price = float(hist["Close"].iloc[-1])
            
            # 取得財報資料（仍使用 yfinance）
            stock = yf.Ticker(ticker)

            inc = getattr(stock, "quarterly_income_stmt", None)
            bal = getattr(stock, "quarterly_balance_sheet", None)
            if inc is None or bal is None:
                return None
            inc_df = inc if isinstance(inc, pd.DataFrame) else pd.DataFrame()
            bal_df = bal if isinstance(bal, pd.DataFrame) else pd.DataFrame()
            if inc_df.empty or bal_df.empty:
                return None

            def _select_row_as_of(df: pd.DataFrame, end: str):
                """取 index（報告期）<= end 的最近一筆 row（Series）。"""
                try:
                    idx = pd.to_datetime(df.index)
                    mask = idx <= pd.Timestamp(end)
                    if not mask.any():
                        return df.iloc[-1] if len(df) else None
                    return df.loc[mask].iloc[-1]
                except Exception:
                    return df.iloc[-1] if len(df) else None

            row_inc = _select_row_as_of(inc_df, as_of_date)
            row_bal = _select_row_as_of(bal_df, as_of_date)
            if row_inc is None or row_bal is None:
                return None

            def _num(s: pd.Series, key: str, default=0):
                v = s.get(key, default)
                if pd.isna(v):
                    return default
                try:
                    return float(v)
                except (TypeError, ValueError):
                    return default

            revenue = _num(row_inc, "Total Revenue", 0) or _num(row_inc, "Revenue", 0)
            net_income = _num(row_inc, "Net Income", 0) or _num(row_inc, "Net Income Common Stockholders", 0)
            total_equity = _num(row_bal, "Total Stockholder Equity", 0) or _num(row_bal, "Stockholders Equity", 0)
            total_liab = _num(row_bal, "Total Liab", 0)
            shares = _num(row_bal, "Share Issued", 0) or 1
            if shares <= 0:
                shares = 1
            eps = _num(row_inc, "Diluted EPS", 0) or (net_income / shares if shares else 0)
            if eps <= 0:
                eps = _num(row_inc, "Basic EPS", 0)
            pe = (price / eps) if eps and eps > 0 else 0
            roe = (net_income / total_equity * 100) if total_equity and total_equity > 0 else 0
            bps = (total_equity / shares) if total_equity and shares and total_equity > 0 else 0
            pb = (price / bps) if bps and bps > 0 else 0
            profit_margin = (net_income / revenue * 100) if revenue and revenue > 0 else 0
            curr_assets = _num(row_bal, "Current Assets", 0)
            curr_liab = _num(row_bal, "Current Liabilities", 1)
            current_ratio = (curr_assets / curr_liab) if curr_liab and curr_liab > 0 else 1
            debt_equity = (total_liab / total_equity) if total_equity and total_equity > 0 else 0

            rev_growth = 0
            earn_growth = 0
            try:
                idx = pd.to_datetime(inc_df.index)
                mask = idx <= pd.Timestamp(as_of_date)
                valid = inc_df.loc[mask] if mask.any() else inc_df
                if len(valid) >= 2:
                    prev = valid.iloc[-2]
                    prev_rev = _num(prev, "Total Revenue", 0) or _num(prev, "Revenue", 0)
                    prev_ni = _num(prev, "Net Income", 0) or _num(prev, "Net Income Common Stockholders", 0)
                    if prev_rev and prev_rev > 0:
                        rev_growth = (revenue - prev_rev) / prev_rev * 100
                    if prev_ni and prev_ni > 0:
                        earn_growth = (net_income - prev_ni) / prev_ni * 100
            except Exception:
                pass

            market_cap = price * shares if shares else 0
            return {
                "marketCap": market_cap,
                "sector": "Unknown",
                "industry": "Unknown",
                "trailingPE": pe,
                "priceToBook": pb,
                "currentRatio": current_ratio,
                "debtToEquity": debt_equity,
                "returnOnEquity": roe / 100 if roe else 0,
                "revenueGrowth": rev_growth / 100 if rev_growth else 0,
                "earningsGrowth": earn_growth / 100 if earn_growth else 0,
                "profitMargins": profit_margin / 100 if profit_margin else 0,
                "beta": 1,
            }
        except Exception as e:
            return None
    
    def get_fmp_profile(self, ticker: str) -> Optional[Dict]:
        """
        獲取 Financial Modeling Prep 公司資料
        
        免費版限制：250 calls/day
        """
        if not self.fmp_api_key:
            return None
        
        try:
            url = f"{FMP_BASE_URL}/profile/{ticker}"
            params = {"apikey": self.fmp_api_key}
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return data[0]
            
            return None
        except Exception as e:
            return None
    
    def get_fmp_ratios(self, ticker: str) -> Optional[Dict]:
        """
        獲取 FMP 財務比率
        
        免費版限制：250 calls/day
        """
        if not self.fmp_api_key:
            return None
        
        try:
            url = f"{FMP_BASE_URL}/ratios/{ticker}"
            params = {"apikey": self.fmp_api_key, "limit": 1}
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return data[0]
            
            return None
        except Exception as e:
            return None
    
    def get_fmp_key_metrics(self, ticker: str) -> Optional[Dict]:
        """
        獲取 FMP 關鍵指標
        
        免費版限制：250 calls/day
        """
        if not self.fmp_api_key:
            return None
        
        try:
            url = f"{FMP_BASE_URL}/key-metrics/{ticker}"
            params = {"apikey": self.fmp_api_key, "limit": 1}
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return data[0]
            
            return None
        except Exception as e:
            return None
    
    def extract_financial_data(self, yahoo_info: Dict, fmp_profile: Dict = None, 
                              fmp_ratios: Dict = None) -> Dict:
        """
        從多個數據源提取財務數據
        
        優先順序：FMP > Yahoo Finance
        """
        financial_data = {}
        
        # === 基本資訊 ===
        financial_data['market_cap'] = yahoo_info.get('marketCap', 0)
        financial_data['sector'] = yahoo_info.get('sector', 'Unknown')
        financial_data['industry'] = yahoo_info.get('industry', 'Unknown')
        
        # === 估值指標 ===
        # PE Ratio
        if fmp_ratios and 'priceEarningsRatio' in fmp_ratios:
            financial_data['pe_ratio'] = fmp_ratios['priceEarningsRatio']
        else:
            financial_data['pe_ratio'] = yahoo_info.get('trailingPE', 0) or 0
        
        # PB Ratio
        if fmp_ratios and 'priceToBookRatio' in fmp_ratios:
            financial_data['pb_ratio'] = fmp_ratios['priceToBookRatio']
        else:
            financial_data['pb_ratio'] = yahoo_info.get('priceToBook', 0) or 0
        
        # === 財務健康度 ===
        # Current Ratio (流動比率)
        if fmp_ratios and 'currentRatio' in fmp_ratios:
            financial_data['current_ratio'] = fmp_ratios['currentRatio']
        else:
            financial_data['current_ratio'] = yahoo_info.get('currentRatio', 1) or 1
        
        # Debt to Equity
        if fmp_ratios and 'debtEquityRatio' in fmp_ratios:
            financial_data['debt_to_equity'] = fmp_ratios['debtEquityRatio']
        else:
            financial_data['debt_to_equity'] = yahoo_info.get('debtToEquity', 0) or 0
        
        # ROE
        if fmp_ratios and 'returnOnEquity' in fmp_ratios:
            financial_data['roe'] = fmp_ratios['returnOnEquity'] * 100
        else:
            financial_data['roe'] = (yahoo_info.get('returnOnEquity', 0) or 0) * 100
        
        # === 成長性 ===
        # Revenue Growth
        if fmp_profile and 'revenuePerShareTTM' in fmp_profile:
            financial_data['revenue_growth'] = 0  # 需要歷史數據對比
        else:
            financial_data['revenue_growth'] = (yahoo_info.get('revenueGrowth', 0) or 0) * 100
        
        # Earnings Growth
        financial_data['earnings_growth'] = (yahoo_info.get('earningsGrowth', 0) or 0) * 100
        
        # === 其他指標 ===
        financial_data['profit_margin'] = (yahoo_info.get('profitMargins', 0) or 0) * 100
        financial_data['beta'] = yahoo_info.get('beta', 1) or 1
        
        # 新聞情緒 (預設中性)
        financial_data['news_sentiment'] = 0
        
        return financial_data
    
    def rate_limit_sleep(self):
        """API 限速延遲"""
        if STAGE2_CONFIG.get('api_delay', 0) > 0:
            time.sleep(STAGE2_CONFIG['api_delay'])


# 全域實例
data_fetcher = DataFetcher()
