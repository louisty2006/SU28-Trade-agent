"""
數據獲取工具模組
"""
import yfinance as yf
import pandas as pd
import requests
import time
from typing import Optional, Dict
from config import (
    FMP_API_KEY,
    FMP_BASE_URL,
    ALLOWED_EXCHANGES,
    STAGE2_CONFIG
)


class DataFetcher:
    """統一的數據獲取接口"""
    
    def __init__(self):
        self.fmp_api_key = FMP_API_KEY
        self.session = requests.Session()
    
    def get_yahoo_history(self, ticker: str, period: str = "30d") -> Optional[pd.DataFrame]:
        """
        獲取 Yahoo Finance 歷史數據
        
        Args:
            ticker: 股票代碼
            period: 時間週期 (1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        
        Returns:
            DataFrame 或 None
        """
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)
            
            if hist.empty:
                return None
            
            return hist
        except Exception as e:
            return None
    
    def get_yahoo_info(self, ticker: str) -> Optional[Dict]:
        """
        獲取 Yahoo Finance 股票基本資訊
        
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
