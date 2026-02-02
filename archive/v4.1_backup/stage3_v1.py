"""
Stage 3: Multi-Agent LLM 討論系統
三個 LLM 進行投資分析討論，產生最終 Top 20

LLM 配置：
- Gemini 1.5 Flash: 基本面分析師
- Cohere Command R: 技術面分析師  
- Mistral: 風險評估師

討論流程：
- Round 1: 各自獨立分析
- Round 2: 交叉質疑與反駁
- Final: 投票產生共識
"""

import os
import json
import time
import requests
from datetime import datetime
from typing import List, Dict
import pandas as pd

# =============================================================================
# LLM API 配置
# =============================================================================

LLM_CONFIG = {
    "gemini": {
        "name": "基本面分析師",
        "api_key": "AIzaSyBv66ccIZSz455ZX4iotWWXtR464xPbsyI",
        "model": "gemini-1.5-flash",
        "weight": 1.0,
        "can_veto": True,
        "system_prompt": """你是一位專業的基本面分析師，專注於：
- 公司財務健康度（營收、利潤、現金流）
- 估值指標（PE、PB、PS）
- 護城河與競爭優勢
- 長期成長潛力
請用數據說話，給出明確的投資建議。回覆請用繁體中文。"""
    },
    "cohere": {
        "name": "技術面分析師",
        "api_key": "Ha9Troa91JkgHn0mLt4c88G9zTQRBvzrUcRTmVjU",
        "model": "command-r",
        "weight": 1.0,
        "can_veto": True,
        "system_prompt": """你是一位專業的技術面分析師，專注於：
- 價格趨勢與動能
- 技術指標（RSI、MACD、KD、布林通道）
- 支撐與阻力位
- 成交量分析
- 入場時機判斷
請根據技術指標給出明確的買入/賣出建議。回覆請用繁體中文。"""
    },
    "mistral": {
        "name": "風險評估師",
        "api_key": "fRk2qfSaAiDjETdWFhFoj3SQUBW47u2s",
        "model": "mistral-small-latest",
        "weight": 1.0,
        "can_veto": True,
        "system_prompt": """你是一位專業的風險評估師，專注於：
- 下行風險評估
- 波動性分析
- 行業風險
- 宏觀經濟影響
- 最壞情況分析
請識別潛在風險，並評估風險/回報比。回覆請用繁體中文。"""
    }
}

# =============================================================================
# LLM API 客戶端
# =============================================================================

class GeminiClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    
    def chat(self, prompt: str, system_prompt: str = "") -> str:
        try:
            url = f"{self.base_url}?key={self.api_key}"
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            payload = {
                "contents": [{"parts": [{"text": full_prompt}]}],
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048}
            }
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            return f"[Gemini 錯誤: {str(e)}]"


class CohereClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.cohere.ai/v1/chat"
    
    def chat(self, prompt: str, system_prompt: str = "") -> str:
        try:
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            payload = {"model": "command-r", "message": prompt, "preamble": system_prompt, "temperature": 0.7}
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result.get("text", "")
        except Exception as e:
            return f"[Cohere 錯誤: {str(e)}]"


class MistralClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.mistral.ai/v1/chat/completions"
    
    def chat(self, prompt: str, system_prompt: str = "") -> str:
        try:
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            payload = {"model": "mistral-small-latest", "messages": messages, "temperature": 0.7, "max_tokens": 2048}
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            return f"[Mistral 錯誤: {str(e)}]"


# =============================================================================
# Stage 3 討論引擎
# =============================================================================

class Stage3Discussion:
    def __init__(self, stage2_results_path: str = None):
        self.stage2_path = stage2_results_path
        self.stocks_df = None
        self.clients = {
            "gemini": GeminiClient(LLM_CONFIG["gemini"]["api_key"]),
            "cohere": CohereClient(LLM_CONFIG["cohere"]["api_key"]),
            "mistral": MistralClient(LLM_CONFIG["mistral"]["api_key"])
        }
        self.round1_results = {}
        self.round2_results = {}
        self.final_ranking = []
    
    def load_stage2_results(self) -> pd.DataFrame:
        if self.stage2_path and os.path.exists(self.stage2_path):
            print(f"📂 載入 Stage 2 結果：{self.stage2_path}")
            df = pd.read_csv(self.stage2_path)
            print(f"✅ 載入 {len(df)} 支股票")
            return df
        
        print("📂 自動尋找最新 Stage 2 結果...")
        stage2_dirs = []
        if os.path.exists("reports/stage2"):
            for dirname in os.listdir("reports/stage2"):
                dirpath = os.path.join("reports/stage2", dirname)
                if os.path.isdir(dirpath):
                    csv_path = os.path.join(dirpath, "stage2_results.csv")
                    if os.path.exists(csv_path):
                        stage2_dirs.append((csv_path, os.path.getmtime(csv_path)))
        
        if stage2_dirs:
            latest_path, _ = max(stage2_dirs, key=lambda x: x[1])
            print(f"✅ 找到最新結果：{latest_path}")
            return pd.read_csv(latest_path)
        
        # 嘗試找 Stage 1 結果
        print("📂 嘗試尋找 Stage 1 結果...")
        if os.path.exists("reports/stage1"):
            for dirname in os.listdir("reports/stage1"):
                dirpath = os.path.join("reports/stage1", dirname)
                if os.path.isdir(dirpath):
                    csv_path = os.path.join(dirpath, "stage1_results.csv")
                    if os.path.exists(csv_path):
                        print(f"✅ 使用 Stage 1 結果：{csv_path}")
                        return pd.read_csv(csv_path)
        
        # 嘗試找測試結果
        if os.path.exists("reports/test/test_stage1.csv"):
            print("✅ 使用測試結果：reports/test/test_stage1.csv")
            return pd.read_csv("reports/test/test_stage1.csv")
        
        print("❌ 找不到任何結果")
        return pd.DataFrame()
    
    def format_stock_data(self, stocks: List[Dict]) -> str:
        formatted = []
        for i, stock in enumerate(stocks, 1):
            ticker = stock.get('ticker', stock.get('股票', 'N/A'))
            price = stock.get('price', stock.get('current_price', stock.get('價格', 'N/A')))
            score = stock.get('score', stock.get('stage2_score', stock.get('評分', 'N/A')))
            rsi = stock.get('rsi', stock.get('RSI', 'N/A'))
            macd = stock.get('macd_cross', stock.get('MACD', 'N/A'))
            pe = stock.get('pe_ratio', stock.get('PE', 'N/A'))
            
            stock_info = f"【{i}. {ticker}】價格:${price} | 評分:{score} | RSI:{rsi} | MACD:{macd} | PE:{pe}"
            formatted.append(stock_info)
        return "\n".join(formatted)
    
    def run_round1(self, stock_group: List[Dict], group_id: int) -> Dict:
        print(f"\n{'='*60}")
        print(f"📊 Round 1 - 第 {group_id} 組獨立分析（{len(stock_group)} 支股票）")
        print(f"{'='*60}")
        
        stock_data = self.format_stock_data(stock_group)
        results = {}
        
        for llm_name, config in LLM_CONFIG.items():
            print(f"\n🤖 {config['name']} ({llm_name}) 分析中...")
            
            prompt = f"""請分析以下 {len(stock_group)} 支股票，針對每支給出評分（0-100）和建議（買入/觀望/避開）。

股票數據：
{stock_data}

請用以下 JSON 格式回覆：
{{"AAPL": {{"score": 85, "comment": "一句話評價", "action": "買入"}}}}

只回覆 JSON，不要其他文字。"""
            
            response = self.clients[llm_name].chat(prompt, config["system_prompt"])
            
            try:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    parsed = json.loads(json_str)
                    results[llm_name] = {"parsed": parsed, "raw": response}
                    print(f"  ✅ 分析完成，評估了 {len(parsed)} 支股票")
                else:
                    results[llm_name] = {"parsed": {}, "raw": response}
                    print(f"  ⚠️ 無法解析 JSON")
            except:
                results[llm_name] = {"parsed": {}, "raw": response}
                print(f"  ⚠️ JSON 解析失敗")
            
            time.sleep(1)
        
        return results
    
    def run_round2(self, stock_group: List[Dict], round1_results: Dict, group_id: int) -> Dict:
        print(f"\n{'='*60}")
        print(f"🔥 Round 2 - 第 {group_id} 組交叉質疑")
        print(f"{'='*60}")
        
        all_tickers = set()
        for llm_results in round1_results.values():
            if llm_results.get("parsed"):
                all_tickers.update(llm_results["parsed"].keys())
        
        disagreements = []
        for ticker in all_tickers:
            scores = []
            for llm_name, llm_results in round1_results.items():
                if llm_results.get("parsed") and ticker in llm_results["parsed"]:
                    score = llm_results["parsed"][ticker].get("score", 50)
                    scores.append((llm_name, score))
            
            if len(scores) >= 2:
                max_s = max(s[1] for s in scores)
                min_s = min(s[1] for s in scores)
                if max_s - min_s > 20:
                    disagreements.append({"ticker": ticker, "scores": scores, "diff": max_s - min_s})
        
        if not disagreements:
            print("  ✅ 本組無重大分歧，跳過 Round 2")
            return {}
        
        print(f"  ⚠️ 發現 {len(disagreements)} 支股票有分歧")
        
        debate_results = {}
        for disagreement in disagreements[:3]:
            ticker = disagreement["ticker"]
            print(f"\n  📌 討論 {ticker}...")
            
            scores_text = ", ".join([f"{LLM_CONFIG[llm]['name']}:{score}分" for llm, score in disagreement["scores"]])
            prompt = f"關於 {ticker}，各分析師評分：{scores_text}。請用30字內說明你的立場。"
            
            responses = {}
            for llm_name, config in LLM_CONFIG.items():
                resp = self.clients[llm_name].chat(prompt, config["system_prompt"])
                responses[llm_name] = resp[:100]
                time.sleep(0.5)
            
            debate_results[ticker] = {"scores": disagreement["scores"], "debate": responses}
        
        return debate_results
    
    def run_final_vote(self, stock_group: List[Dict], round1_results: Dict) -> List[Dict]:
        print(f"\n{'='*60}")
        print(f"🗳️ 最終投票")
        print(f"{'='*60}")
        
        final_scores = {}
        
        for llm_name, llm_results in round1_results.items():
            weight = LLM_CONFIG[llm_name]["weight"]
            parsed = llm_results.get("parsed", {})
            
            for ticker, data in parsed.items():
                if ticker not in final_scores:
                    final_scores[ticker] = {"scores": [], "weights": [], "actions": [], "comments": []}
                
                score = data.get("score", 50)
                final_scores[ticker]["scores"].append(score)
                final_scores[ticker]["weights"].append(weight)
                final_scores[ticker]["actions"].append(data.get("action", "觀望"))
                final_scores[ticker]["comments"].append(f"{LLM_CONFIG[llm_name]['name']}: {data.get('comment', '')}")
        
        results = []
        vetoed = []
        
        for ticker, data in final_scores.items():
            veto = False
            for i, (score, action) in enumerate(zip(data["scores"], data["actions"])):
                llm_names = list(LLM_CONFIG.keys())
                if i < len(llm_names) and LLM_CONFIG[llm_names[i]]["can_veto"]:
                    if score < 30 or action == "避開":
                        veto = True
                        vetoed.append((ticker, LLM_CONFIG[llm_names[i]]["name"]))
                        break
            
            if veto:
                continue
            
            weighted_sum = sum(s * w for s, w in zip(data["scores"], data["weights"]))
            total_weight = sum(data["weights"])
            final_score = weighted_sum / total_weight if total_weight > 0 else 50
            
            actions = data["actions"]
            if actions.count("買入") >= 2:
                consensus = "買入"
            elif actions.count("避開") >= 2:
                consensus = "避開"
            else:
                consensus = "觀望"
            
            results.append({
                "ticker": ticker,
                "final_score": round(final_score, 1),
                "consensus": consensus,
                "individual_scores": data["scores"],
                "comments": data["comments"]
            })
        
        results.sort(key=lambda x: x["final_score"], reverse=True)
        
        print(f"\n✅ 投票完成！通過: {len(results)} 支 | 否決: {len(vetoed)} 支")
        if vetoed:
            for ticker, analyst in vetoed[:3]:
                print(f"   ❌ {ticker} 被 {analyst} 否決")
        
        return results
    
    def run(self, top_n: int = 20) -> List[Dict]:
        print("\n" + "=" * 70)
        print("🤖 Stage 3: Multi-Agent LLM 討論系統")
        print("=" * 70)
        
        self.stocks_df = self.load_stage2_results()
        if self.stocks_df.empty:
            print("❌ 無法載入結果，使用測試數據...")
            test_stocks = [
                {"ticker": "AAPL", "price": 185, "score": 78, "rsi": 45, "macd_cross": "金叉", "PE": 28},
                {"ticker": "MSFT", "price": 390, "score": 75, "rsi": 52, "macd_cross": "金叉", "PE": 35},
                {"ticker": "GOOGL", "price": 142, "score": 72, "rsi": 48, "macd_cross": "死叉", "PE": 24},
                {"ticker": "NVDA", "price": 680, "score": 85, "rsi": 62, "macd_cross": "金叉", "PE": 65},
                {"ticker": "TSLA", "price": 185, "score": 65, "rsi": 38, "macd_cross": "死叉", "PE": 45},
            ]
            self.stocks_df = pd.DataFrame(test_stocks)
        
        stocks = self.stocks_df.to_dict('records')
        total_stocks = len(stocks)
        
        print(f"\n📊 總共 {total_stocks} 支股票待討論")
        
        group_size = 50
        all_results = []
        
        for i in range(0, total_stocks, group_size):
            group = stocks[i:i + group_size]
            group_id = (i // group_size) + 1
            
            print(f"\n{'#' * 60}")
            print(f"# 第 {group_id} 組討論 ({len(group)} 支股票)")
            print(f"{'#' * 60}")
            
            round1 = self.run_round1(group, group_id)
            self.round1_results[group_id] = round1
            
            round2 = self.run_round2(group, round1, group_id)
            self.round2_results[group_id] = round2
            
            group_results = self.run_final_vote(group, round1)
            all_results.extend(group_results)
            
            print(f"\n✅ 第 {group_id} 組完成，產生 {len(group_results)} 支候選")
        
        all_results.sort(key=lambda x: x["final_score"], reverse=True)
        self.final_ranking = all_results[:top_n]
        
        print("\n" + "=" * 70)
        print(f"🏆 Stage 3 完成！最終 Top {min(top_n, len(self.final_ranking))}")
        print("=" * 70)
        
        for i, stock in enumerate(self.final_ranking, 1):
            emoji = "🟢" if stock["consensus"] == "買入" else "🟡" if stock["consensus"] == "觀望" else "🔴"
            print(f"{i:2}. {stock['ticker']:6} | {stock['final_score']:5.1f}分 | {emoji} {stock['consensus']}")
        
        return self.final_ranking
    
    def save_report(self, output_dir: str = None) -> str:
        if not output_dir:
            timestamp = datetime.now().strftime('%Y-%m-%d_%H%M')
            output_dir = f"reports/stage3/{timestamp}"
        
        os.makedirs(output_dir, exist_ok=True)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "final_ranking": self.final_ranking
        }
        
        json_path = os.path.join(output_dir, "stage3_discussion.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        if self.final_ranking:
            df = pd.DataFrame(self.final_ranking)
            csv_path = os.path.join(output_dir, "stage3_top20.csv")
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        print(f"\n💾 報告已儲存: {output_dir}")
        return output_dir


def main():
    print("\n" + "🤖" * 25)
    print("Stage 3: Multi-Agent LLM 討論系統")
    print("🤖" * 25)
    
    stage3 = Stage3Discussion()
    results = stage3.run(top_n=20)
    
    if results:
        stage3.save_report()
    
    return results


if __name__ == "__main__":
    main()
