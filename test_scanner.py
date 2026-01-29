import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

warnings.filterwarnings("ignore")

def load_universe() -> dict:
    """載入測試用的 100 支股票"""
    
    csv_path = "test_100_stocks.csv"
    
    if not os.path.exists(csv_path):
        print(f"❌ 找不到 {csv_path}")
        return {}
    
    try:
        print(f"📂 載入測試股票池：{csv_path}")
        df = pd.read_csv(csv_path)
        
        # 統一欄位名稱（不區分大小寫）
        df.columns = df.columns.str.lower()
        
        if 'symbol' not in df.columns:
            print("❌ CSV 缺少 Symbol 欄位")
            return {}
        
        # 清理數據
        df['symbol'] = df['symbol'].astype(str).str.strip()
        df = df[df['symbol'].notna() & (df['symbol'] != '')]
        
        stocks = {}
        
        # 按市場分組
        if 'market' in df.columns:
            for market, group in df.groupby('market'):
                market_name = str(market).upper()
                
                # 如果有交易所資訊，進一步分組
                if 'exchange' in df.columns:
                    for exchange, sub_group in group.groupby('exchange'):
                        key = f"{market_name}_{exchange}"
                        stocks[key] = sub_group['symbol'].unique().tolist()
                else:
                    stocks[market_name] = group['symbol'].unique().tolist()
        else:
            # 沒有市場分類，全部放在一起
            stocks['ALL'] = df['symbol'].unique().tolist()
        
        total = sum(len(v) for v in stocks.values())
        print(f"✅ 已載入 {total} 支測試股票，分為 {len(stocks)} 個分組")
        return stocks
        
    except Exception as e:
        print(f"❌ 讀取 CSV 時出錯：{e}")
        return {}


import os
STOCKS = load_universe()

def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(prices):
    ema12 = prices.ewm(span=12).mean()
    ema26 = prices.ewm(span=26).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    return macd, signal

def calculate_kd(high, low, close, period=14):
    lowest_low = low.rolling(window=period).min()
    highest_high = high.rolling(window=period).max()
    rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
    k = rsv.ewm(com=2).mean()
    d = k.ewm(com=2).mean()
    return k, d

def calculate_bollinger(prices, period=20):
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper = sma + (std * 2)
    lower = sma - (std * 2)
    return upper, sma, lower

def analyze_stock(ticker, sector):
    """分析單一股票"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="30d")
        if hist.empty or len(hist) < 20:
            return None

        info = stock.info
        # 僅鎖定美股與港股
        exchange = str(info.get('exchange', '')).upper()
        allowed_exchanges = {
            'NMS', 'NCM', 'NGM', 'NAS', 'NSQ',  # NASDAQ
            'NYQ', 'NYS',                        # NYSE
            'ASE', 'AMEX',                       # AMEX
            'HKG',                               # 港股
        }
        if exchange not in allowed_exchanges:
            return None

        price = hist['Close'].iloc[-1]
        
        change_1d = ((price - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100 if len(hist) >= 2 else 0
        change_5d = ((price - hist['Close'].iloc[-5]) / hist['Close'].iloc[-5]) * 100 if len(hist) >= 5 else 0
        change_20d = ((price - hist['Close'].iloc[-20]) / hist['Close'].iloc[-20]) * 100 if len(hist) >= 20 else 0
        
        rsi = calculate_rsi(hist['Close']).iloc[-1]
        macd, signal = calculate_macd(hist['Close'])
        macd_val = macd.iloc[-1]
        signal_val = signal.iloc[-1]
        macd_cross = "金叉" if macd_val > signal_val else "死叉"
        macd_diff = macd_val - signal_val
        
        k, d = calculate_kd(hist['High'], hist['Low'], hist['Close'])
        k_val = k.iloc[-1]
        d_val = d.iloc[-1]
        kd_cross = "金叉" if k_val > d_val else "死叉"
        
        upper, middle, lower = calculate_bollinger(hist['Close'])
        bb_position = (price - lower.iloc[-1]) / (upper.iloc[-1] - lower.iloc[-1]) * 100
        
        vol_avg = hist['Volume'].rolling(20).mean().iloc[-1]
        vol_ratio = hist['Volume'].iloc[-1] / vol_avg if vol_avg > 0 else 1
        
        high_52w = hist['High'].tail(252).max() if len(hist) >= 252 else hist['High'].max()
        low_52w = hist['Low'].tail(252).min() if len(hist) >= 252 else hist['Low'].min()
        from_high = ((price - high_52w) / high_52w) * 100
        from_low = ((price - low_52w) / low_52w) * 100
        
        score = 50
        if 30 <= rsi <= 40: score += 20
        elif rsi < 30: score += 15
        elif 40 < rsi <= 50: score += 10
        elif rsi > 70: score -= 10
        if macd_diff > 0 and len(macd) >= 2 and macd.iloc[-2] - signal.iloc[-2] < 0: score += 15
        elif macd_diff > 0: score += 8
        if k_val < 30 and k_val > d_val: score += 12
        elif k_val < 20: score += 8
        if bb_position < 20: score += 10
        elif bb_position < 30: score += 5
        if vol_ratio > 2: score += 8
        elif vol_ratio > 1.5: score += 5
        if from_high < -30: score += 10
        if from_high < -40: score += 5
        if -15 < change_5d < -5: score += 10
        
        return {
            '股票': ticker,
            '名稱': info.get('shortName', '')[:20],
            '板塊': sector,
            '價格': round(price, 2),
            '1日%': round(change_1d, 2),
            '5日%': round(change_5d, 2),
            '20日%': round(change_20d, 2),
            'RSI': round(rsi, 1),
            'MACD': macd_cross,
            'MACD差': round(macd_diff, 3),
            'K值': round(k_val, 1),
            'D值': round(d_val, 1),
            'KD': kd_cross,
            '布林%': round(bb_position, 1),
            '成交量比': round(vol_ratio, 2),
            '離52高%': round(from_high, 1),
            '離52低%': round(from_low, 1),
            'PE': round(info.get('trailingPE', 0), 1) if info.get('trailingPE') else 0,
            '市值B': round(info.get('marketCap', 0) / 1e9, 1),
            '評分': min(100, max(0, score)),
        }
    except Exception as e:
        return None

def generate_simple_report(df, timestamp):
    """生成簡化版 HTML 報告"""
    
    top10 = df.head(10)
    
    html = f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>測試報告 - {timestamp}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ 
            text-align: center; 
            color: #00ff88;
            padding: 20px;
        }}
        .subtitle {{ text-align: center; color: #888; margin-bottom: 20px; }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            overflow: hidden;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        th {{
            background: rgba(0,217,255,0.2);
            color: #00d9ff;
        }}
        tr:hover {{
            background: rgba(255,255,255,0.05);
        }}
        .positive {{ color: #00ff88; }}
        .negative {{ color: #ff6b6b; }}
        .score-high {{ 
            background: #00ff88; 
            color: #000; 
            padding: 3px 10px; 
            border-radius: 5px; 
            font-weight: bold;
        }}
        .score-mid {{ 
            background: #ffd700; 
            color: #000; 
            padding: 3px 10px; 
            border-radius: 5px; 
            font-weight: bold;
        }}
        .score-low {{ 
            background: #ff6b6b; 
            color: #fff; 
            padding: 3px 10px; 
            border-radius: 5px; 
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 測試掃描報告</h1>
        <p class="subtitle">掃描時間：{timestamp} | 共掃描 {len(df)} 支股票</p>
        
        <h2 style="color: #00d9ff; margin: 30px 0 20px 0;">🏆 TOP 10 股票</h2>
        <table>
            <tr>
                <th>排名</th>
                <th>股票</th>
                <th>名稱</th>
                <th>板塊</th>
                <th>價格</th>
                <th>1日%</th>
                <th>5日%</th>
                <th>RSI</th>
                <th>MACD</th>
                <th>評分</th>
            </tr>
'''
    
    for i, (_, row) in enumerate(top10.iterrows(), 1):
        score_class = "score-high" if row['評分'] >= 80 else "score-mid" if row['評分'] >= 60 else "score-low"
        change_1d_class = "positive" if row['1日%'] >= 0 else "negative"
        change_5d_class = "positive" if row['5日%'] >= 0 else "negative"
        
        html += f'''
            <tr>
                <td><strong>#{i}</strong></td>
                <td><strong>{row['股票']}</strong></td>
                <td>{row['名稱']}</td>
                <td>{row['板塊']}</td>
                <td>${row['價格']}</td>
                <td class="{change_1d_class}">{row['1日%']:+.2f}%</td>
                <td class="{change_5d_class}">{row['5日%']:+.2f}%</td>
                <td>{row['RSI']}</td>
                <td>{row['MACD']}</td>
                <td><span class="{score_class}">{row['評分']}</span></td>
            </tr>
'''
    
    html += '''
        </table>
        
        <h2 style="color: #00d9ff; margin: 30px 0 20px 0;">📈 完整數據</h2>
        <table>
            <tr>
                <th>排名</th>
                <th>股票</th>
                <th>名稱</th>
                <th>板塊</th>
                <th>價格</th>
                <th>評分</th>
            </tr>
'''
    
    for i, (_, row) in enumerate(df.iterrows(), 1):
        score_class = "score-high" if row['評分'] >= 80 else "score-mid" if row['評分'] >= 60 else "score-low"
        html += f'''
            <tr>
                <td>{i}</td>
                <td><strong>{row['股票']}</strong></td>
                <td>{row['名稱']}</td>
                <td>{row['板塊']}</td>
                <td>${row['價格']}</td>
                <td><span class="{score_class}">{row['評分']}</span></td>
            </tr>
'''
    
    html += '''
        </table>
    </div>
</body>
</html>
'''
    return html

def main():
    start_time = time.time()
    print("=" * 60)
    print(f"🔍 股票掃描系統 - 測試版 (100支)")
    print(f"   {datetime.now().strftime('%Y年%m月%d日 %H:%M')}")
    print("=" * 60)
    
    if not STOCKS:
        print("❌ 沒有載入到股票數據！")
        return
    
    # 收集所有股票
    all_tickers = []
    for sector, tickers in STOCKS.items():
        for ticker in tickers:
            all_tickers.append((ticker, sector))
    
    total = len(all_tickers)
    print(f"\n📊 開始掃描 {total} 支股票...")
    print(f"⚡ 使用 20 個並行線程\n")
    
    results = []
    results_lock = Lock()
    count = 0
    count_lock = Lock()
    
    def process_stock(ticker_sector):
        ticker, sector = ticker_sector
        nonlocal count
        
        data = analyze_stock(ticker, sector)
        
        with count_lock:
            count += 1
            if data:
                signal = "🔥" if data['評分'] >= 75 else "✅" if data['評分'] >= 60 else "✓"
                print(f"[{count}/{total}] {ticker:8s} {signal} {data['評分']}分", flush=True)
            else:
                print(f"[{count}/{total}] {ticker:8s} ❌", flush=True)
        
        return data
    
    # 使用線程池並行處理
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_ticker = {
            executor.submit(process_stock, (ticker, sector)): (ticker, sector)
            for ticker, sector in all_tickers
        }
        
        for future in as_completed(future_to_ticker):
            try:
                data = future.result()
                if data:
                    with results_lock:
                        results.append(data)
            except Exception:
                pass
    
    elapsed_time = time.time() - start_time
    print(f"\n⏱️  掃描完成，耗時: {elapsed_time:.1f} 秒")
    
    if not results:
        print("❌ 沒有找到有效數據！")
        return
    
    df = pd.DataFrame(results).sort_values('評分', ascending=False)
    
    # 創建報告資料夾結構
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M')
    timestamp_display = datetime.now().strftime('%Y年%m月%d日 %H:%M')
    
    # 建立資料夾：reports/test/YYYY-MM-DD_HHMM_test/
    report_dir = os.path.join("reports", "test", f"{timestamp}_test")
    os.makedirs(report_dir, exist_ok=True)
    
    # CSV
    csv_file = os.path.join(report_dir, "test_scan.csv")
    df.to_csv(csv_file, index=False, encoding='utf-8-sig')
    
    # HTML 報告
    html_file = os.path.join(report_dir, "test_report.html")
    html_content = generate_simple_report(df, timestamp_display)
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("\n" + "=" * 60)
    print("✅ 測試完成！")
    print("=" * 60)
    print(f"📊 成功掃描: {len(results)} 支股票")
    print(f"📁 報告資料夾: {report_dir}/")
    print(f"   📄 CSV 數據: test_scan.csv")
    print(f"   📊 HTML 報告: test_report.html")
    print(f"⏱️  總耗時: {elapsed_time:.1f} 秒")
    
    # 顯示 TOP 5
    print("\n🏆 TOP 5 股票：")
    for i, (_, row) in enumerate(df.head(5).iterrows(), 1):
        print(f"  {i}. {row['股票']:8s} - {row['名稱']:20s} 評分: {row['評分']}/100")
    
    # 自動打開報告
    print(f"\n🚀 正在開啟報告...")
    import subprocess
    try:
        subprocess.run(['open', html_file], check=False)
    except:
        print(f"請手動開啟：{html_file}")

if __name__ == "__main__":
    main()
