"""
Stage 1: 快速掃描全市場（多數據源版）

數據源：多數據源（Yahoo → Stooq → FMP → ...）
- 依序嘗試多個源，直到拿到該日數據
- 真實數據，不用 fallback 替換
"""

import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, date, timedelta
import time
import os
import random
import warnings
warnings.filterwarnings('ignore')
from config import REIKAN_STAGE1_CSV

# 多數據源統一介面
from utils.data_sources import get_daily_bars, get_close_on_date

class Stage1Scanner:
    def __init__(self, stock_file='COMPLETE_ALL_STOCKS_FINAL.csv', output_dir='reports/stage1'):
        self.stock_file = stock_file
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.rate_limited = False
    
    def load_stocks(self):
        print("📂 載入股票池...")
        if os.path.exists(self.stock_file):
            df = pd.read_csv(self.stock_file)
            for col in ['symbol', 'Symbol', 'ticker', 'Ticker', 'SYMBOL']:
                if col in df.columns:
                    symbols = df[col].dropna().unique().tolist()
                    symbols = [s for s in symbols if isinstance(s, str) and not s[0].isdigit() and '^' not in s and 'W' not in s[-1:]]
                    print(f"✅ 載入 {len(symbols)} 支美股（已過濾權證）")
                    return symbols
            symbols = df.iloc[:, 0].dropna().unique().tolist()
            symbols = [s for s in symbols if isinstance(s, str) and not s[0].isdigit() and '^' not in s]
            return symbols
        return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'AMD']
    
    def calculate_score(self, symbol, retry=0, as_of_date=None, backtest_start=None):
        """
        計算股票評分（使用多數據源）
        
        Args:
            symbol: 股票代碼
            retry: 重試次數
            as_of_date: 回測時數據截至該日（date 物件）
            backtest_start: 回測時數據起始日（date 物件）
        """
        try:
            time.sleep(random.uniform(0.1, 0.3))
            
            # 決定日期範圍
            if as_of_date:
                # 確保是 date 物件
                if isinstance(as_of_date, str):
                    end_date = datetime.strptime(as_of_date, "%Y-%m-%d").date()
                elif hasattr(as_of_date, 'date'):
                    end_date = as_of_date.date()
                else:
                    end_date = as_of_date
                
                if backtest_start:
                    if isinstance(backtest_start, str):
                        start_date = datetime.strptime(backtest_start, "%Y-%m-%d").date()
                    elif hasattr(backtest_start, 'date'):
                        start_date = backtest_start.date()
                    else:
                        start_date = backtest_start
                    # 回測時仍需至少 90 日歷史才能算 SMA20，否則 len(df)<20 全被篩掉
                    min_start = end_date - timedelta(days=90)
                    if start_date > min_start:
                        start_date = min_start
                else:
                    # 預設取 3 個月的資料
                    start_date = end_date - timedelta(days=90)
            else:
                # 即時模式
                end_date = date.today()
                start_date = end_date - timedelta(days=90)
            
            # 使用多數據源統一介面取得日線
            df = get_daily_bars(symbol, start_date, end_date)
            if df is None or df.empty or len(df) < 20:
                return None
            
            # 轉換為標準格式（模擬 yfinance 的 hist）
            hist = df.copy()
            hist = hist.set_index('Date')

            if hist.empty or len(hist) < 20:
                return None
            
            close = hist['Close'].iloc[-1]
            volume = hist['Volume'].iloc[-1]
            avg_volume = hist['Volume'].mean()
            
            if close < 1 or avg_volume < 50000:
                return None
            
            self.rate_limited = False  # 成功了，重置限流標記
            
            score = 50
            signals = []
            
            # 均線
            sma5 = hist['Close'].rolling(5).mean().iloc[-1]
            sma10 = hist['Close'].rolling(10).mean().iloc[-1]
            sma20 = hist['Close'].rolling(20).mean().iloc[-1]
            
            if close > sma5 > sma10 > sma20:
                score += 20
                signals.append("多頭排列")
            elif close > sma20:
                score += 10
                signals.append("站上MA20")
            elif close > sma5:
                score += 5
            
            # 成交量
            vol_ratio = volume / avg_volume if avg_volume > 0 else 0
            if vol_ratio > 2:
                score += 15
                signals.append("放量")
            elif vol_ratio > 1.5:
                score += 10
            elif vol_ratio > 1:
                score += 5
            
            # 動能
            ret_5d = (close / hist['Close'].iloc[-5] - 1) * 100
            if ret_5d > 5:
                score += 10
                signals.append(f"5日+{ret_5d:.1f}%")
            elif ret_5d > 2:
                score += 5
            
            # RSI
            delta = hist['Close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = (100 - (100 / (1 + rs))).iloc[-1]
            
            if 40 <= rsi <= 70:
                score += 10
            elif 30 <= rsi < 40:
                score += 5
            
            return {
                'symbol': symbol,
                'score': min(score, 100),
                'price': close,
                'volume': int(volume),
                'signals': ', '.join(signals) if signals else '-'
            }
        except Exception as e:
            err = str(e).lower()
            if 'rate' in err or 'too many' in err:
                self.rate_limited = True
                if retry < 2:
                    time.sleep(3 + retry * 2)
                    return self.calculate_score(symbol, retry + 1, as_of_date=as_of_date, backtest_start=backtest_start)
            return None
    
    def run(self, top_n=500, max_workers=3, max_stocks=None, as_of_date=None, backtest_start=None):
        """
        max_stocks: 小樣本時只掃前 N 檔。
        as_of_date: 回測時數據截至該日。
        backtest_start: 回測時數據起始日（range 之前看不到）。
        """
        print("=" * 70)
        print("🚀 Stage 1: 快速篩選啟動（限流保護模式）")
        print("=" * 70)
        
        symbols = self.load_stocks()
        if max_stocks is not None:
            symbols = symbols[:max_stocks]
            print(f"\n🧪 小樣本模式：只掃前 {max_stocks} 檔")
        total = len(symbols)
        
        print(f"\n📊 總共 {total:,} 支股票")
        print(f"⚡ 並行線程：{max_workers}（保守模式）")
        print(f"🎯 目標輸出：Top {top_n}\n")
        
        end_str = as_of_date.strftime("%Y-%m-%d") if hasattr(as_of_date, 'strftime') else (as_of_date or "")
        start_str = backtest_start.strftime("%Y-%m-%d") if backtest_start and hasattr(backtest_start, 'strftime') else (backtest_start or "")
        start_time = time.time()
        results = []
        consecutive_fails = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.calculate_score, s, 0, end_str or None, start_str or None): s for s in symbols}
            
            for i, future in enumerate(as_completed(futures), 1):
                symbol = futures[future]
                try:
                    result = future.result()
                    
                    elapsed = time.time() - start_time
                    speed = i / elapsed if elapsed > 0 else 0
                    remain = (total - i) / speed / 60 if speed > 0 else 0
                    
                    if result:
                        results.append(result)
                        consecutive_fails = 0
                        s = result['score']
                        icon = "🔥" if s >= 75 else "⭐" if s >= 70 else "✓" if s >= 50 else "❌"
                        print(f"[{i}/{total}] {symbol:6} {icon} {s:.0f}分 | {speed:.1f}/s | 剩餘:{remain:.1f}分")
                    else:
                        consecutive_fails += 1
                        print(f"[{i}/{total}] {symbol:6} ❌ | {speed:.1f}/s | 剩餘:{remain:.1f}分")
                        
                        # 連續失敗太多，暫停
                        if consecutive_fails >= 20:
                            print(f"\n⚠️  連續 {consecutive_fails} 次失敗，暫停 10 秒...")
                            time.sleep(10)
                            consecutive_fails = 0
                except:
                    consecutive_fails += 1
                    print(f"[{i}/{total}] {symbol:6} ❌ | 錯誤")
                
                # 每 30 支暫停
                if i % 30 == 0:
                    time.sleep(0.5)
        
        results.sort(key=lambda x: x['score'], reverse=True)
        top_results = results[:top_n]
        
        elapsed = time.time() - start_time
        
        if top_results:
            df = pd.DataFrame(top_results)
            timestamp = datetime.now().strftime('%Y-%m-%d_%H%M')
            # 本次運行資料夾（main 傳入 run_dir）時用固定檔名，方便 Stage 2 讀取
            if self.output_dir == 'reports/stage1':
                output_file = f"{self.output_dir}/{timestamp}_stage1.csv"
            else:
                output_file = os.path.join(self.output_dir, REIKAN_STAGE1_CSV)
            df.to_csv(output_file, index=False)
            
            print("\n" + "=" * 70)
            print("✅ Stage 1 完成！")
            print("=" * 70)
            print(f"⏱️  耗時：{elapsed/60:.1f} 分鐘")
            print(f"📊 符合條件：{len(results)} 支")
            print(f"📈 輸出 Top {len(top_results)} 支")
            print(f"💾 儲存：{output_file}")
            
            print(f"\n🏆 Top 20：")
            for i, r in enumerate(top_results[:20], 1):
                print(f"  {i:2}. {r['symbol']:6} | {r['score']:.0f}分 | ${r['price']:.2f} | {r['signals']}")
            
            return top_results
        
        print("\n❌ 沒有找到符合條件的股票")
        return []

def run_stage1():
    scanner = Stage1Scanner()
    return scanner.run(top_n=500, max_workers=3)

if __name__ == "__main__":
    run_stage1()
