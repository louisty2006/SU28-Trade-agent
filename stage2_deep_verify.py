"""
Stage 2: 深度驗證
從 Stage 1 的 Top 1000 驗證篩選出 Top 250

數據源：Yahoo Finance + FMP (免費版)
並行：30 線程（考慮 API 限制）
預計時間：10-15 分鐘
"""
import pandas as pd
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import time

from config import STAGE2_CONFIG, STAGE2_DIR
from utils.data_fetcher import data_fetcher
from utils.scoring import calculate_stage2_score, get_score_explanation


class Stage2Verifier:
    """Stage 2 深度驗證器"""
    
    def __init__(self, stage1_results_path: str = None):
        self.stage1_path = stage1_results_path
        self.results = []
        self.results_lock = Lock()
        self.count = 0
        self.count_lock = Lock()
        self.start_time = None
        self.api_calls = {"yahoo": 0, "fmp": 0}
        self.api_lock = Lock()
    
    def load_stage1_results(self) -> pd.DataFrame:
        """載入 Stage 1 結果"""
        if self.stage1_path and os.path.exists(self.stage1_path):
            print(f"📂 載入 Stage 1 結果：{self.stage1_path}")
            return pd.read_csv(self.stage1_path)
        
        # 自動尋找最新的 Stage 1 檔案
        import glob
        stage1_files = glob.glob("reports/stage1/*_stage1.csv")
        
        if not stage1_files:
            print("❌ 找不到 Stage 1 結果檔案")
            return pd.DataFrame()
        
        # 按修改時間排序，取最新的
        stage1_files.sort(key=os.path.getmtime, reverse=True)
        latest_file = stage1_files[0]
        print(f"📂 自動載入最新檔案：{latest_file}")
        return pd.read_csv(latest_file)
    
    def verify_stock(self, row: dict) -> dict:
        """深度驗證單一股票"""
        try:
            ticker = row.get('ticker') or row.get('symbol')
            stage1_score = float(row['score'])
            
            # === Yahoo Finance 詳細資訊 ===
            with self.api_lock:
                self.api_calls['yahoo'] += 1
            
            yahoo_info = data_fetcher.get_yahoo_info(ticker)
            if yahoo_info is None:
                return None
            
            # === FMP 數據（如果有 API Key）===
            fmp_profile = None
            fmp_ratios = None
            
            if STAGE2_CONFIG.get('use_fmp', False) and data_fetcher.fmp_api_key:
                with self.api_lock:
                    self.api_calls['fmp'] += 2
                
                fmp_profile = data_fetcher.get_fmp_profile(ticker)
                fmp_ratios = data_fetcher.get_fmp_ratios(ticker)
                
                # API 限速
                data_fetcher.rate_limit_sleep()
            
            # === 提取財務數據 ===
            financial_data = data_fetcher.extract_financial_data(
                yahoo_info, fmp_profile, fmp_ratios
            )
            
            # === 計算 Stage 2 評分 ===
            stage2_score = calculate_stage2_score(stage1_score, financial_data)
            
            # === 組裝結果 ===
            result = {
                'ticker': ticker,
                'name': row.get('name', ''),
                'sector': financial_data['sector'],
                'industry': financial_data['industry'],
                'price': row.get('price', 0),
                'stage1_score': round(stage1_score, 1),
                'stage2_score': round(stage2_score, 1),
                'score_improvement': round(stage2_score - stage1_score, 1),
                'score_explanation': get_score_explanation(stage2_score),
                
                # 技術指標（繼承自 Stage 1）
                'rsi': row.get('rsi', 0),
                'macd_cross': row.get('macd_cross', ''),
                'kd_cross': row.get('kd_cross', ''),
                'change_1d': row.get('change_1d', 0),
                'change_5d': row.get('change_5d', 0),
                'change_20d': row.get('change_20d', 0),
                
                # 財務指標
                'market_cap_b': round(financial_data['market_cap'] / 1e9, 2),
                'pe_ratio': round(financial_data['pe_ratio'], 2),
                'pb_ratio': round(financial_data['pb_ratio'], 2),
                'current_ratio': round(financial_data['current_ratio'], 2),
                'debt_to_equity': round(financial_data['debt_to_equity'], 2),
                'roe': round(financial_data['roe'], 2),
                'revenue_growth': round(financial_data['revenue_growth'], 2),
                'earnings_growth': round(financial_data['earnings_growth'], 2),
                'profit_margin': round(financial_data['profit_margin'], 2),
                'beta': round(financial_data['beta'], 2),
                
                # 數據來源標記
                'data_source': 'Yahoo+FMP' if fmp_ratios else 'Yahoo',
            }
            
            return result
            
        except Exception as e:
            return None
    
    def process_stock(self, row: dict, total: int) -> dict:
        """處理單一股票（包含進度更新）"""
        result = self.verify_stock(row)
        
        # 更新進度
        with self.count_lock:
            self.count += 1
            current_count = self.count
        
        # 每 50 支或找到高分股票時顯示進度
        if current_count % 50 == 0 or (result and result['stage2_score'] >= 75):
            elapsed = time.time() - self.start_time
            rate = current_count / elapsed if elapsed > 0 else 0
            eta = (total - current_count) / rate / 60 if rate > 0 else 0
            
            signal = "🔥" if result and result['stage2_score'] >= 80 else \
                     "⭐" if result and result['stage2_score'] >= 75 else \
                     "✓" if result else "❌"
            
            score_info = ""
            if result:
                s1 = result['stage1_score']
                s2 = result['stage2_score']
                diff = result['score_improvement']
                score_info = f"S1:{s1:.1f} → S2:{s2:.1f} ({diff:+.1f})"
            
            with self.api_lock:
                api_info = f"API: Y={self.api_calls['yahoo']} F={self.api_calls['fmp']}"
            
            print(f"[{current_count}/{total}] {row['ticker']} {signal} {score_info} | "
                  f"{api_info} | ETA:{eta:.1f}分", flush=True)
        
        if result:
            with self.results_lock:
                self.results.append(result)
        
        return result
    
    def run(self) -> pd.DataFrame:
        """執行 Stage 2 驗證"""
        print("=" * 80)
        print("🔍 Stage 2: 深度驗證啟動")
        print("=" * 80)
        
        self.start_time = time.time()
        
        # 載入 Stage 1 結果
        df_stage1 = self.load_stage1_results()
        if df_stage1.empty:
            return pd.DataFrame()
        
        total = len(df_stage1)
        
        print(f"\n📊 輸入：{total:,} 支股票")
        print(f"⚡ 並行線程：{STAGE2_CONFIG['max_workers']}")
        print(f"🎯 目標輸出：Top {STAGE2_CONFIG['target_output']}")
        print(f"📡 數據源：Yahoo Finance" + 
              (" + FMP" if STAGE2_CONFIG.get('use_fmp') else ""))
        print(f"\n開始驗證...\n")
        
        # 轉換為字典列表
        stocks = df_stage1.to_dict('records')
        
        # 並行處理
        max_workers = STAGE2_CONFIG['max_workers']
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.process_stock, stock, total): stock
                for stock in stocks
            }
            
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    pass
        
        # 完成統計
        elapsed = time.time() - self.start_time
        
        print("\n" + "=" * 80)
        print(f"✅ Stage 2 完成！")
        print("=" * 80)
        print(f"⏱️  耗時：{elapsed/60:.1f} 分鐘 ({elapsed:.1f} 秒)")
        print(f"📊 成功驗證：{len(self.results):,} / {total:,} 支")
        print(f"📈 驗證速度：{total/elapsed:.1f} 支/秒")
        print(f"📡 API 調用：Yahoo={self.api_calls['yahoo']}, FMP={self.api_calls['fmp']}")
        
        if not self.results:
            print("❌ 沒有找到符合條件的股票！")
            return pd.DataFrame()
        
        # 轉換為 DataFrame 並排序
        df = pd.DataFrame(self.results)
        df = df.sort_values('stage2_score', ascending=False)
        
        # 取 Top N
        target = STAGE2_CONFIG['target_output']
        df_top = df.head(target)
        
        print(f"\n🏆 Top {target} 股票：")
        print(f"   最高分：{df_top.iloc[0]['stage2_score']:.1f} ({df_top.iloc[0]['ticker']})")
        print(f"   最低分：{df_top.iloc[-1]['stage2_score']:.1f} ({df_top.iloc[-1]['ticker']})")
        print(f"   平均分：{df_top['stage2_score'].mean():.1f}")
        
        # 統計評分提升
        improved = df_top[df_top['score_improvement'] > 0]
        declined = df_top[df_top['score_improvement'] < 0]
        print(f"\n📊 評分變化：")
        print(f"   提升：{len(improved)} 支 (平均 +{improved['score_improvement'].mean():.1f})")
        print(f"   下降：{len(declined)} 支 (平均 {declined['score_improvement'].mean():.1f})")
        
        return df_top
    
    def save_results(self, df: pd.DataFrame) -> str:
        """儲存結果"""
        if df.empty:
            return ""
        
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M')
        output_dir = os.path.join(STAGE2_DIR, f"{timestamp}_stage2")
        os.makedirs(output_dir, exist_ok=True)
        
        # CSV
        csv_path = os.path.join(output_dir, "stage2_results.csv")
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        # HTML 報告
        html_path = os.path.join(output_dir, "stage2_report.html")
        self._generate_html_report(df, html_path, timestamp)
        
        print(f"\n💾 結果已儲存：")
        print(f"   📁 目錄：{output_dir}/")
        print(f"   📄 CSV：stage2_results.csv")
        print(f"   📊 HTML：stage2_report.html")
        
        return output_dir
    
    def _generate_html_report(self, df: pd.DataFrame, path: str, timestamp: str):
        """生成 HTML 報告"""
        top30 = df.head(30)
        
        html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stage 2 深度驗證報告 - {timestamp}</title>
    <style>
        body {{ 
            font-family: Arial, sans-serif; 
            background: #1a1a2e; 
            color: #eee; 
            padding: 20px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        h1 {{ color: #00d9ff; text-align: center; }}
        h2 {{ color: #00ff88; }}
        table {{ 
            width: 100%; 
            border-collapse: collapse; 
            margin: 20px 0;
            background: rgba(255,255,255,0.05);
            font-size: 0.9em;
        }}
        th, td {{ 
            padding: 10px; 
            text-align: left; 
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        th {{ background: rgba(0,217,255,0.2); color: #00d9ff; }}
        .score-high {{ color: #00ff88; font-weight: bold; }}
        .score-mid {{ color: #ffd700; font-weight: bold; }}
        .positive {{ color: #00ff88; }}
        .negative {{ color: #ff6b6b; }}
        .improved {{ background: rgba(0,255,136,0.1); }}
        .declined {{ background: rgba(255,107,107,0.1); }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Stage 2 深度驗證報告</h1>
        <p style="text-align: center; color: #888;">
            {timestamp} | 共驗證 {len(df)} 支股票
        </p>
        
        <h2>🏆 Top 30 深度驗證結果</h2>
        <table>
            <tr>
                <th>排名</th>
                <th>股票</th>
                <th>名稱</th>
                <th>板塊</th>
                <th>S1評分</th>
                <th>S2評分</th>
                <th>變化</th>
                <th>PE</th>
                <th>PB</th>
                <th>ROE%</th>
                <th>負債率</th>
                <th>市值B</th>
            </tr>
"""
        
        for i, (_, row) in enumerate(top30.iterrows(), 1):
            s2_class = "score-high" if row['stage2_score'] >= 80 else "score-mid"
            improve_class = "improved" if row['score_improvement'] > 0 else \
                           "declined" if row['score_improvement'] < 0 else ""
            improve_sign = "positive" if row['score_improvement'] > 0 else "negative"
            
            html += f"""
            <tr class="{improve_class}">
                <td>{i}</td>
                <td><strong>{row['ticker']}</strong></td>
                <td>{row['name'][:20]}</td>
                <td>{row['sector']}</td>
                <td>{row['stage1_score']:.1f}</td>
                <td class="{s2_class}">{row['stage2_score']:.1f}</td>
                <td class="{improve_sign}">{row['score_improvement']:+.1f}</td>
                <td>{row.get('pe_ratio', 0):.1f}</td>
                <td>{row.get('pb_ratio', 0):.1f}</td>
                <td>{row.get('roe', 0):.1f}</td>
                <td>{row.get('debt_to_equity', 0):.2f}</td>
                <td>{row.get('market_cap_b', 0):.1f}</td>
            </tr>
"""
        
        html += f"""
        </table>
        
        <h2>📊 統計摘要</h2>
        <table style="width: 50%;">
            <tr><th>指標</th><th>數值</th></tr>
            <tr><td>平均 Stage 2 評分</td><td class="score-high">{df['stage2_score'].mean():.1f}</td></tr>
            <tr><td>平均評分提升</td><td>{df['score_improvement'].mean():+.1f}</td></tr>
            <tr><td>評分提升股票</td><td class="positive">{len(df[df['score_improvement'] > 0])}</td></tr>
            <tr><td>評分下降股票</td><td class="negative">{len(df[df['score_improvement'] < 0])}</td></tr>
            <tr><td>平均 PE</td><td>{df['pe_ratio'].mean():.1f}</td></tr>
            <tr><td>平均 PB</td><td>{df['pb_ratio'].mean():.1f}</td></tr>
            <tr><td>平均 ROE</td><td>{df['roe'].mean():.1f}%</td></tr>
        </table>
        
        <p style="text-align: center; color: #888; margin-top: 40px;">
            ➡️ 接下來：執行 Stage 3 Multi-Agent LLM 討論
        </p>
    </div>
</body>
</html>
"""
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)


def main():
    """主程式"""
    import sys
    
    # 可選：接受命令行參數指定 Stage 1 結果路徑
    stage1_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    verifier = Stage2Verifier(stage1_path)
    df = verifier.run()
    
    if not df.empty:
        output_dir = verifier.save_results(df)
        print(f"\n✅ Stage 2 完成，請繼續執行 Stage 3")
        print(f"   輸入資料：{output_dir}/stage2_results.csv")


if __name__ == "__main__":
    main()
