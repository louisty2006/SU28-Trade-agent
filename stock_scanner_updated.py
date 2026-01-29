import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import finnhub
import os
from dotenv import load_dotenv
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

warnings.filterwarnings("ignore")

load_dotenv()
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY) if FINNHUB_API_KEY else None


# 內建預設股票清單（當找不到 CSV 時會用呢個）
DEFAULT_STOCKS = {
    "科技巨頭": ["AAPL", "MSFT", "GOOGL", "META", "AMZN", "NVDA", "TSLA"],
    "半導體": [
        "AMD",
        "INTC",
        "QCOM",
        "AVGO",
        "MU",
        "AMAT",
        "LRCX",
        "KLAC",
        "TSM",
        "ASML",
    ],
    "軟體SaaS": ["CRM", "ADBE", "NOW", "SNOW", "PLTR", "NET", "DDOG", "ZS", "CRWD", "PANW"],
    "電商零售": ["WMT", "COST", "TGT", "HD", "LOW", "BABA", "JD", "PDD", "MELI", "SE"],
    "金融銀行": ["JPM", "BAC", "GS", "MS", "WFC", "C", "BLK", "SCHW", "AXP", "V", "MA"],
    "醫療製藥": ["JNJ", "UNH", "PFE", "MRK", "LLY", "ABBV", "TMO", "ABT", "BMY", "AMGN"],
    "生技股": ["MRNA", "BNTX", "REGN", "VRTX", "GILD", "BIIB", "ILMN"],
    "能源石油": ["XOM", "CVX", "COP", "SLB", "EOG", "PXD", "OXY", "VLO", "MPC"],
    "新能源": ["ENPH", "SEDG", "FSLR", "RUN", "PLUG", "BE", "CHPT"],
    "電動車": ["RIVN", "LCID", "NIO", "XPEV", "LI", "F", "GM"],
    "航空國防": ["BA", "LMT", "RTX", "NOC", "GD", "GE"],
    "消費品牌": ["NKE", "SBUX", "MCD", "KO", "PEP", "PG", "CL"],
    "娛樂媒體": ["DIS", "NFLX", "CMCSA", "WBD", "PARA", "SPOT", "RBLX"],
    "通訊服務": ["VZ", "T", "TMUS"],
    "房地產REITs": ["AMT", "PLD", "CCI", "EQIX", "SPG", "O"],
    "工業製造": ["CAT", "DE", "UNP", "UPS", "FDX", "HON", "MMM"],
    "中概股": ["BIDU", "NTES", "BILI", "TME", "IQ", "FUTU", "TIGR"],
}


def load_universe() -> dict:
    """載入美股 / 港股股票池。

    優先順序：
    1. 嘗試讀取 COMPLETE_ALL_STOCKS_FINAL.csv（完整股票池）
    2. 嘗試讀取 data/us_universe.csv 和 data/hk_universe.csv
    3. 使用內建 DEFAULT_STOCKS

    返回格式：{板塊名稱: [股票代碼列表]}
    """
    stocks: dict = {}
    
    # 優先讀取 COMPLETE_ALL_STOCKS_FINAL.csv
    complete_csv_paths = [
        "COMPLETE_ALL_STOCKS_FINAL.csv",  # 當前目錄
        "data/COMPLETE_ALL_STOCKS_FINAL.csv",  # data 子目錄
        "/mnt/user-data/uploads/COMPLETE_ALL_STOCKS_FINAL.csv",  # 上傳目錄
    ]
    
    for csv_path in complete_csv_paths:
        if os.path.exists(csv_path):
            try:
                print(f"📂 找到完整股票池：{csv_path}")
                df = pd.read_csv(csv_path)
                
                # 檢查必要欄位
                if 'Symbol' not in df.columns and 'symbol' not in df.columns:
                    print(f"⚠️ CSV 缺少 Symbol 欄位，跳過")
                    continue
                
                # 統一欄位名稱（不區分大小寫）
                df.columns = df.columns.str.lower()
                
                # 清理數據
                df['symbol'] = df['symbol'].astype(str).str.strip()
                df = df[df['symbol'].notna() & (df['symbol'] != '')]
                
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
                print(f"✅ 已載入 {total} 支股票，分為 {len(stocks)} 個分組")
                return stocks
                
            except Exception as e:
                print(f"⚠️ 讀取 {csv_path} 時出錯：{e}")
                continue
    
    # 如果找不到完整 CSV，嘗試讀取分開的 CSV
    print("📂 嘗試讀取分開的 US/HK universe CSV...")
    base_dir = os.path.dirname(__file__)
    data_dir = os.path.join(base_dir, "data")

    us_path = os.path.join(data_dir, "us_universe.csv")
    hk_path = os.path.join(data_dir, "hk_universe.csv")

    us_stocks = _load_single_universe_csv(us_path, "US")
    hk_stocks = _load_single_universe_csv(hk_path, "HK")

    stocks.update(us_stocks)
    stocks.update(hk_stocks)

    if stocks:
        total = sum(len(v) for v in stocks.values())
        print(f"✅ 已從 CSV 載入股票池，共 {total} 支（{len(stocks)} 個分組）。")
        return stocks

    # 最後才使用內建預設清單
    print("⚠️ 未找到任何 CSV，改用內建 DEFAULT_STOCKS 股票清單。")
    return DEFAULT_STOCKS


def _load_single_universe_csv(path: str, prefix: str) -> dict:
    """從單一 CSV 載入股票清單。

    CSV 至少要有一欄 `symbol`，可選 `sector`：
    - 有 sector：會變成 {f"{prefix}_{sector}": [symbols...]}
    - 無 sector：會變成 {f"{prefix}_All": [symbols...]}
    """
    if not os.path.exists(path):
        return {}

    try:
        df = pd.read_csv(path)
    except Exception:
        # CSV 壞咗就當冇
        return {}

    if "symbol" not in df.columns:
        return {}

    stocks = {}
    df["symbol"] = df["symbol"].astype(str).str.strip()

    if "sector" in df.columns:
        for sector, sub in df.groupby("sector"):
            key = f"{prefix}_{sector}"
            stocks[key] = sub["symbol"].dropna().unique().tolist()
    else:
        key = f"{prefix}_All"
        stocks[key] = df["symbol"].dropna().unique().tolist()

    return stocks


# 最終使用的股票池
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

def get_news(ticker):
    if not finnhub_client:
        return []
    try:
        end = datetime.now()
        start = end - timedelta(days=7)
        news = finnhub_client.company_news(ticker, _from=start.strftime('%Y-%m-%d'), to=end.strftime('%Y-%m-%d'))
        return news[:3] if news else []
    except:
        return []

def analyze_stock(ticker, sector, fetch_news=False):
    """分析單一股票
    
    Args:
        ticker: 股票代碼
        sector: 板塊名稱
        fetch_news: 是否獲取新聞（只對高分股票使用，節省 API 調用）
    """
    try:
        stock = yf.Ticker(ticker)
        # 優化：使用 30 日數據而非 90 日，加快速度
        hist = stock.history(period="30d")
        if hist.empty or len(hist) < 20:  # 降低最低要求
            return None

        info = stock.info
        # 僅鎖定美股與港股
        exchange = str(info.get('exchange', '')).upper()
        allowed_exchanges = {
            # 美股常見交易所代碼（NASDAQ / NYSE / AMEX 等）
            'NMS', 'NCM', 'NGM', 'NAS', 'NSQ',  # NASDAQ 系列
            'NYQ', 'NYS',                        # NYSE 系列
            'ASE', 'AMEX',                       # AMEX
            # 港股
            'HKG',
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
        
        # 優化：如果數據不足 252 日，就用現有數據計算
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
        
        # 優化：只對高分股票獲取新聞，節省 API 調用
        news = []
        if fetch_news:
            news = get_news(ticker)
        
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
            '新聞標題': news[0].get('headline', '')[:80] if news else '',
            '新聞連結': news[0].get('url', '') if news else ''
        }
    except Exception as e:
        return None

def generate_html_report(df, timestamp):
    """生成 HTML 報告"""
    
    top20 = df.head(20)
    tickers_str = ", ".join(top20.head(10)['股票'].tolist())
    
    html = f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>股票掃描報告 - {timestamp}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        h1 {{ 
            text-align: center; 
            padding: 30px;
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 2.5em;
        }}
        .subtitle {{ text-align: center; color: #888; margin-bottom: 30px; }}
        
        .section {{ 
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .section h2 {{ 
            color: #00d9ff;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #00d9ff;
        }}
        
        .stock-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }}
        
        .stock-card {{
            background: linear-gradient(145deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02));
            border-radius: 12px;
            padding: 20px;
            border-left: 4px solid #00ff88;
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        .stock-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,217,255,0.2);
        }}
        .stock-card.top3 {{ border-left-color: #ffd700; }}
        .stock-card.top6 {{ border-left-color: #c0c0c0; }}
        .stock-card.top10 {{ border-left-color: #cd7f32; }}
        
        .stock-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }}
        .stock-rank {{ 
            font-size: 1.5em; 
            font-weight: bold;
            color: #ffd700;
        }}
        .stock-ticker {{ 
            font-size: 1.8em; 
            font-weight: bold;
            color: #fff;
        }}
        .stock-name {{ color: #888; font-size: 0.9em; }}
        .stock-sector {{ 
            background: #00d9ff;
            color: #000;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 0.8em;
        }}
        
        .stock-price {{ font-size: 2em; color: #00ff88; margin: 10px 0; }}
        .stock-score {{ 
            font-size: 1.5em;
            padding: 5px 15px;
            border-radius: 10px;
            font-weight: bold;
        }}
        .score-high {{ background: #00ff88; color: #000; }}
        .score-mid {{ background: #ffd700; color: #000; }}
        .score-low {{ background: #ff6b6b; color: #fff; }}
        
        .metrics {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 15px 0; }}
        .metric {{ 
            background: rgba(0,0,0,0.3);
            padding: 10px;
            border-radius: 8px;
            text-align: center;
        }}
        .metric-label {{ color: #888; font-size: 0.8em; }}
        .metric-value {{ font-size: 1.1em; font-weight: bold; }}
        .metric-value.positive {{ color: #00ff88; }}
        .metric-value.negative {{ color: #ff6b6b; }}
        
        .news {{ 
            background: rgba(0,217,255,0.1);
            padding: 10px;
            border-radius: 8px;
            margin-top: 10px;
            font-size: 0.85em;
        }}
        .news a {{ color: #00d9ff; text-decoration: none; }}
        .news a:hover {{ text-decoration: underline; }}
        
        .prompt-section {{
            background: rgba(0,255,136,0.1);
            border: 2px solid #00ff88;
        }}
        .prompt-box {{
            background: #000;
            padding: 20px;
            border-radius: 10px;
            margin: 15px 0;
            font-family: monospace;
            font-size: 0.9em;
            line-height: 1.6;
            white-space: pre-wrap;
            max-height: 400px;
            overflow-y: auto;
        }}
        .copy-btn {{
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            color: #000;
            border: none;
            padding: 12px 30px;
            border-radius: 25px;
            font-size: 1em;
            font-weight: bold;
            cursor: pointer;
            margin: 10px 5px;
            transition: transform 0.2s;
        }}
        .copy-btn:hover {{ transform: scale(1.05); }}
        .copy-btn:active {{ transform: scale(0.95); }}
        
        .next-steps {{
            background: linear-gradient(145deg, rgba(255,215,0,0.1), rgba(255,215,0,0.05));
            border: 2px solid #ffd700;
        }}
        .next-steps h2 {{ color: #ffd700; border-bottom-color: #ffd700; }}
        .step {{ 
            display: flex;
            align-items: flex-start;
            margin: 20px 0;
            padding: 15px;
            background: rgba(0,0,0,0.3);
            border-radius: 10px;
        }}
        .step-num {{
            background: #ffd700;
            color: #000;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 1.2em;
            margin-right: 15px;
            flex-shrink: 0;
        }}
        .step-content h3 {{ color: #ffd700; margin-bottom: 5px; }}
        .step-content p {{ color: #aaa; }}
        
        .summary-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        .summary-table th, .summary-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        .summary-table th {{
            background: rgba(0,217,255,0.2);
            color: #00d9ff;
        }}
        .summary-table tr:hover {{
            background: rgba(255,255,255,0.05);
        }}
        
        @media (max-width: 768px) {{
            .stock-grid {{ grid-template-columns: 1fr; }}
            .metrics {{ grid-template-columns: repeat(2, 1fr); }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 股票掃描報告</h1>
        <p class="subtitle">掃描時間：{timestamp} | 共掃描 {len(df)} 支股票</p>
        
        <!-- TOP 20 股票 -->
        <div class="section">
            <h2>🏆 TOP 20 投資機會</h2>
            <div class="stock-grid">
'''
    
    for i, (_, row) in enumerate(top20.iterrows(), 1):
        card_class = "top3" if i <= 3 else "top6" if i <= 6 else "top10" if i <= 10 else ""
        score_class = "score-high" if row['評分'] >= 80 else "score-mid" if row['評分'] >= 60 else "score-low"
        
        change_1d_class = "positive" if row['1日%'] >= 0 else "negative"
        change_5d_class = "positive" if row['5日%'] >= 0 else "negative"
        rsi_class = "negative" if row['RSI'] < 30 else "positive" if row['RSI'] > 70 else ""
        
        rank_emoji = "🥇" if i <= 3 else "🥈" if i <= 6 else "🥉" if i <= 10 else f"#{i}"
        
        html += f'''
                <div class="stock-card {card_class}">
                    <div class="stock-header">
                        <div>
                            <span class="stock-rank">{rank_emoji}</span>
                            <span class="stock-ticker">{row['股票']}</span>
                            <div class="stock-name">{row['名稱']}</div>
                        </div>
                        <div style="text-align: right;">
                            <span class="stock-sector">{row['板塊']}</span>
                            <div class="stock-score {score_class}" style="margin-top: 10px;">{row['評分']}分</div>
                        </div>
                    </div>
                    <div class="stock-price">${row['價格']}</div>
                    <div class="metrics">
                        <div class="metric">
                            <div class="metric-label">1日漲跌</div>
                            <div class="metric-value {change_1d_class}">{row['1日%']:+.2f}%</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">5日漲跌</div>
                            <div class="metric-value {change_5d_class}">{row['5日%']:+.2f}%</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">RSI</div>
                            <div class="metric-value {rsi_class}">{row['RSI']}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">MACD</div>
                            <div class="metric-value">{row['MACD']}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">KD</div>
                            <div class="metric-value">{row['KD']}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">布林%</div>
                            <div class="metric-value">{row['布林%']}%</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">成交量比</div>
                            <div class="metric-value">{row['成交量比']}x</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">離52週高</div>
                            <div class="metric-value negative">{row['離52高%']}%</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">市值</div>
                            <div class="metric-value">{row['市值B']}B</div>
                        </div>
                    </div>
'''
        if row['新聞標題']:
            html += f'''
                    <div class="news">
                        📰 <a href="{row['新聞連結']}" target="_blank">{row['新聞標題']}</a>
                    </div>
'''
        html += '''
                </div>
'''
    
    # Claude 提問模板
    claude_prompt = f'''請分析以下 10 支潛力股票，並給出投資建議：

'''
    for i, (_, row) in enumerate(top20.head(10).iterrows(), 1):
        claude_prompt += f'''【{i}. {row['股票']} - {row['名稱']}】
• 現價: ${row['價格']} | 板塊: {row['板塊']}
• 漲跌: 1日 {row['1日%']}% | 5日 {row['5日%']}% | 20日 {row['20日%']}%
• RSI: {row['RSI']} | MACD: {row['MACD']} | KD: {row['KD']}
• 布林位置: {row['布林%']}% | 成交量比: {row['成交量比']}x
• 距52週高: {row['離52高%']}% | 市值: {row['市值B']}B
• 系統評分: {row['評分']}/100

'''
    claude_prompt += '''請針對每支股票回答：
1. 基本面評估（公司體質、護城河）
2. 技術面評估（是否好入場點）
3. 投資建議：買入/觀望/避開
4. 若建議買入：入場價、停損點、目標價'''

    # Perplexity 提問模板
    perplexity_prompt = f'''請搜尋並分析以下股票的最新新聞和市場動態：

{tickers_str}

針對每支股票：
1. 最近 7 天的重要新聞（附來源連結）
2. 分析師最新評級和目標價
3. 是否有財報發布或重大事件即將發生
4. 國際局勢（如關稅、政策）對該股票的影響
5. 市場情緒總結：看多/看空/中性'''

    html += f'''
            </div>
        </div>
        
        <!-- 下一步行動 -->
        <div class="section next-steps">
            <h2>🎯 下一步行動</h2>
            
            <div class="step">
                <div class="step-num">1</div>
                <div class="step-content">
                    <h3>📋 複製 Claude 提問到 Claude Project</h3>
                    <p>進行深度基本面和技術面分析</p>
                </div>
            </div>
            <button class="copy-btn" onclick="copyToClipboard('claude-prompt')">📋 複製 Claude 提問</button>
            <div class="prompt-box" id="claude-prompt">{claude_prompt}</div>
            
            <div class="step">
                <div class="step-num">2</div>
                <div class="step-content">
                    <h3>🔍 複製 Perplexity 提問到 Perplexity Space</h3>
                    <p>搜尋最新新聞、分析師評級和市場動態</p>
                </div>
            </div>
            <button class="copy-btn" onclick="copyToClipboard('perplexity-prompt')">📋 複製 Perplexity 提問</button>
            <div class="prompt-box" id="perplexity-prompt">{perplexity_prompt}</div>
            
            <div class="step">
                <div class="step-num">3</div>
                <div class="step-content">
                    <h3>📊 綜合分析並做出投資決策</h3>
                    <p>結合 Claude 的深度分析和 Perplexity 的最新資訊，制定投資策略</p>
                </div>
            </div>
        </div>
        
        <!-- 完整數據表 -->
        <div class="section">
            <h2>📈 完整掃描數據</h2>
            <div style="overflow-x: auto;">
                <table class="summary-table">
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
                        <th>KD</th>
                        <th>評分</th>
                    </tr>
'''
    
    for i, (_, row) in enumerate(df.iterrows(), 1):
        html += f'''
                    <tr>
                        <td>{i}</td>
                        <td><strong>{row['股票']}</strong></td>
                        <td>{row['名稱']}</td>
                        <td>{row['板塊']}</td>
                        <td>${row['價格']}</td>
                        <td class="{'positive' if row['1日%'] >= 0 else 'negative'}" style="color: {'#00ff88' if row['1日%'] >= 0 else '#ff6b6b'}">{row['1日%']:+.2f}%</td>
                        <td class="{'positive' if row['5日%'] >= 0 else 'negative'}" style="color: {'#00ff88' if row['5日%'] >= 0 else '#ff6b6b'}">{row['5日%']:+.2f}%</td>
                        <td>{row['RSI']}</td>
                        <td>{row['MACD']}</td>
                        <td>{row['KD']}</td>
                        <td><strong>{row['評分']}</strong></td>
                    </tr>
'''
    
    html += '''
                </table>
            </div>
        </div>
        
    </div>
    
    <script>
        function copyToClipboard(elementId) {
            const text = document.getElementById(elementId).innerText;
            navigator.clipboard.writeText(text).then(() => {
                alert('已複製到剪貼簿！✅');
            }).catch(err => {
                // Fallback for older browsers
                const textarea = document.createElement('textarea');
                textarea.value = text;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                alert('已複製到剪貼簿！✅');
            });
        }
    </script>
</body>
</html>
'''
    return html

def main():
    start_time = time.time()
    print("=" * 60)
    print(f"🔍 股票掃描系統 v3.1 (完整市場版) - {datetime.now().strftime('%Y年%m月%d日 %H:%M')}")
    print("=" * 60)
    
    # 收集所有股票
    all_tickers = []
    for sector, tickers in STOCKS.items():
        for ticker in tickers:
            all_tickers.append((ticker, sector))
    
    total = len(all_tickers)
    print(f"\n📊 總共 {total} 支股票，開始並行掃描...")
    print(f"⚡ 使用 60 個並行線程加速處理")
    print(f"⏱️  預計耗時：{total * 2 / 60 / 60:.1f} 小時\n")
    
    results = []
    results_lock = Lock()  # 線程安全的結果列表
    count = 0
    count_lock = Lock()  # 線程安全的計數器
    
    def process_stock(ticker_sector):
        """處理單一股票的包裝函數"""
        ticker, sector = ticker_sector
        nonlocal count
        
        # 先快速掃描（不獲取新聞）
        data = analyze_stock(ticker, sector, fetch_news=False)
        
        # 如果高分（>= 70），再獲取新聞
        if data and data['評分'] >= 70:
            news_data = analyze_stock(ticker, sector, fetch_news=True)
            if news_data:
                data = news_data
        
        # 更新進度
        with count_lock:
            count += 1
            if count % 100 == 0 or data:
                signal = "🔥" if data and data['評分'] >= 75 else "✅" if data and data['評分'] >= 60 else "✓" if data else "❌"
                score_str = f"{data['評分']}分" if data else ""
                print(f"[{count}/{total}] {ticker} {signal} {score_str}", flush=True)
        
        return data
    
    # 使用線程池並行處理
    max_workers = 60  # 60 個並行線程
    completed = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任務
        future_to_ticker = {
            executor.submit(process_stock, (ticker, sector)): (ticker, sector)
            for ticker, sector in all_tickers
        }
        
        # 收集結果
        for future in as_completed(future_to_ticker):
            ticker, sector = future_to_ticker[future]
            try:
                data = future.result()
                if data:
                    with results_lock:
                        results.append(data)
                completed += 1
            except Exception as e:
                completed += 1
                # 錯誤已記錄在 process_stock 中
    
    elapsed_time = time.time() - start_time
    print(f"\n⏱️  掃描完成，耗時: {elapsed_time:.1f} 秒 ({elapsed_time/60:.1f} 分鐘 / {elapsed_time/3600:.1f} 小時)")
    
    if not results:
        print("❌ 沒有找到數據！")
        return
    
    df = pd.DataFrame(results).sort_values('評分', ascending=False)
    
    # 創建報告資料夾結構
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M')
    timestamp_display = datetime.now().strftime('%Y年%m月%d日 %H:%M')
    
    # 建立資料夾：reports/full/YYYY-MM-DD_HHMM_full/
    report_dir = os.path.join("reports", "full", f"{timestamp}_full")
    os.makedirs(report_dir, exist_ok=True)
    
    # CSV
    csv_file = os.path.join(report_dir, "scan.csv")
    df.to_csv(csv_file, index=False, encoding='utf-8-sig')
    
    # HTML 報告
    html_file = os.path.join(report_dir, "report.html")
    html_content = generate_html_report(df, timestamp_display)
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("\n" + "=" * 60)
    print("✅ 掃描完成！")
    print("=" * 60)
    print(f"📊 成功掃描: {len(results)} 支股票")
    print(f"📁 報告資料夾: {report_dir}/")
    print(f"   📄 CSV 數據: scan.csv")
    print(f"   📊 HTML 報告: report.html")
    print(f"⏱️  總耗時: {elapsed_time/60:.1f} 分鐘 ({elapsed_time/3600:.1f} 小時)")
    print("\n🚀 正在開啟報告...")
    
    # 自動開啟 HTML 報告
    import subprocess
    try:
        subprocess.run(['open', html_file], check=False)
    except:
        try:
            subprocess.run(['xdg-open', html_file], check=False)
        except:
            print(f"請手動開啟：{html_file}")

if __name__ == "__main__":
    main()
