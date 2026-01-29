"""
Stage 3: Multi-Agent LLM 討論系統 v4.2
四個 LLM 進行投資分析討論，產生最終 Top 20

LLM 配置：
- Gemini 2.5 Flash: 基本面分析師
- Cohere Command R: 技術面分析師  
- Mistral Small: 風險評估師
- HuggingFace Qwen 72B: 宏觀分析師 🆕

討論流程：
- Round 1: 各自獨立分析
- Round 2: 交叉質疑與反駁
- Final: 投票產生共識
"""

import os
import json
import re
import time
import requests
from datetime import datetime
from typing import List, Dict
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# === LLM 配置 ===
LLM_CONFIG = {
    "gemini": {
        "name": "基本面分析師",
        "model": "gemini-2.5-flash",
        "api_key_env": "GEMINI_API_KEY",
        "focus": "財務報表、營收、獲利能力、估值"
    },
    "cohere": {
        "name": "技術面分析師",
        "model": "command-a-03-2025",
        "api_key_env": "COHERE_API_KEY",
        "focus": "技術指標、趨勢、動能、圖表形態"
    },
    "mistral": {
        "name": "風險評估師",
        "model": "mistral-small-latest",
        "api_key_env": "MISTRAL_API_KEY",
        "focus": "風險因素、波動性、下行風險、止損位"
    },
    "huggingface": {
        "name": "宏觀分析師",
        "model": "Qwen/Qwen2.5-72B-Instruct",
        "api_key_env": "HUGGINGFACE_API_KEY",
        "focus": "宏觀經濟、行業趨勢、市場情緒、長期展望"
    }
}

class Stage3Discussion:
    """Stage 3: 四人 LLM 討論系統"""
    
    def __init__(self):
        self.results = []
        self.discussion_log = []
        self.api_keys = self._load_api_keys()
        
    def _load_api_keys(self) -> Dict:
        """載入 API Keys"""
        keys = {}
        for llm_id, config in LLM_CONFIG.items():
            key = os.getenv(config["api_key_env"])
            if key:
                keys[llm_id] = key
                print(f"  ✅ {config['name']} ({llm_id}) API Key 已載入")
            else:
                print(f"  ⚠️ {config['name']} ({llm_id}) API Key 未設置")
        return keys
    
    def _call_gemini(self, prompt: str) -> str:
        """呼叫 Gemini API"""
        api_key = self.api_keys.get("gemini")
        if not api_key:
            return ""
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        
        try:
            response = requests.post(url, json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.3}
            }, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            else:
                print(f"    Gemini 錯誤: {response.status_code}")
                return ""
        except Exception as e:
            print(f"    Gemini 異常: {str(e)[:50]}")
            return ""
    
    def _call_cohere(self, prompt: str) -> str:
        """呼叫 Cohere API (Chat API)"""
        api_key = self.api_keys.get("cohere")
        if not api_key:
            return ""
        
        url = "https://api.cohere.com/v2/chat"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(url, headers=headers, json={
                "model": "command-a-03-2025",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            }, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                content = data.get("message", {}).get("content", [])
                return content[0].get("text", "") if content else ""
            else:
                print(f"    Cohere 錯誤: {response.status_code}")
                return ""
        except Exception as e:
            print(f"    Cohere 異常: {str(e)[:50]}")
            return ""
    
    def _call_mistral(self, prompt: str) -> str:
        """呼叫 Mistral API"""
        api_key = self.api_keys.get("mistral")
        if not api_key:
            return ""
        
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(url, headers=headers, json={
                "model": "mistral-small-latest",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            }, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                print(f"    Mistral 錯誤: {response.status_code}")
                return ""
        except Exception as e:
            print(f"    Mistral 異常: {str(e)[:50]}")
            return ""
    
    def _call_huggingface(self, prompt: str) -> str:
        """呼叫 HuggingFace Router API (Qwen 72B)"""
        api_key = self.api_keys.get("huggingface")
        if not api_key:
            return ""
        
        url = "https://router.huggingface.co/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(url, headers=headers, json={
                "model": "Qwen/Qwen2.5-72B-Instruct",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2000,
                "temperature": 0.3
            }, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                print(f"    HuggingFace 錯誤: {response.status_code}")
                return ""
        except Exception as e:
            print(f"    HuggingFace 異常: {str(e)[:50]}")
            return ""
    
    def _call_llm(self, llm_id: str, prompt: str) -> str:
        """統一呼叫 LLM"""
        if llm_id == "gemini":
            return self._call_gemini(prompt)
        elif llm_id == "cohere":
            return self._call_cohere(prompt)
        elif llm_id == "mistral":
            return self._call_mistral(prompt)
        elif llm_id == "huggingface":
            return self._call_huggingface(prompt)
        return ""
    
    def _extract_json(self, text: str) -> dict:
        """從回應中提取 JSON"""
        if not text:
            return {}
        
        # 嘗試提取 ```json ... ``` 區塊
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except:
                pass
        
        # 嘗試直接解析
        try:
            # 找到第一個 { 和最後一個 }
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end > start:
                return json.loads(text[start:end+1])
        except:
            pass
        
        return {}
    
    def load_stage2_results(self) -> pd.DataFrame:
        """載入 Stage 2 結果"""
        print("📂 自動尋找最新 Stage 2 結果...")
        
        # 優先找 Stage 2
        if os.path.exists("reports/stage2"):
            for dirname in sorted(os.listdir("reports/stage2"), reverse=True):
                csv_path = os.path.join("reports/stage2", dirname, "stage2_results.csv")
                if os.path.exists(csv_path):
                    print(f"✅ 使用 Stage 2 結果：{csv_path}")
                    return pd.read_csv(csv_path)
        
        # 退而找 Stage 1
        print("📂 嘗試尋找 Stage 1 結果...")
        if os.path.exists("reports/stage1"):
            for dirname in sorted(os.listdir("reports/stage1"), reverse=True):
                csv_path = os.path.join("reports/stage1", dirname, "stage1_results.csv")
                if os.path.exists(csv_path):
                    print(f"✅ 使用 Stage 1 結果：{csv_path}")
                    return pd.read_csv(csv_path)
        
        # 找測試結果
        if os.path.exists("reports/test/test_stage1.csv"):
            print(f"✅ 使用測試結果：reports/test/test_stage1.csv")
            return pd.read_csv("reports/test/test_stage1.csv")
        
        print("❌ 找不到任何結果")
        return pd.DataFrame()
    
    def run_round1(self, stock_group: List[Dict], group_id: int) -> Dict:
        """Round 1: 各自獨立分析"""
        print(f"\n{'='*60}")
        print(f"📊 Round 1 - 第 {group_id} 組獨立分析（{len(stock_group)} 支股票）")
        print(f"{'='*60}")
        
        # 構建股票數據摘要
        stock_summary = "\n".join([
            f"- {s['ticker']}: "
            f"技術: RSI={s.get('rsi', 0):.1f}, MACD={s.get('macd_cross', 'N/A')}, "
            f"財務: PE={s.get('pe_ratio', 0):.1f}, ROE={s.get('roe', 0):.1f}%, "
            f"成長: 營收{s.get('revenue_growth', 0):.1f}%, 獲利{s.get('earnings_growth', 0):.1f}%, "
            f"Stage2分數={s.get('stage2_score', s.get('score', 0)):.1f}"
            for s in stock_group
        ])
        
        results = {}
        
        for llm_id, config in LLM_CONFIG.items():
            if llm_id not in self.api_keys:
                continue
            
            print(f"\n🤖 {config['name']} ({llm_id}) 分析中...")
            
            prompt = f"""你是一位專業的{config['name']}，專注於{config['focus']}。

請分析以下股票，為每支股票給出 0-100 的評分和簡短理由。

股票數據：
{stock_summary}

請用以下 JSON 格式回應（不要加任何其他文字）：
{{
  "TICKER1": {{"score": 85, "reason": "簡短理由"}},
  "TICKER2": {{"score": 70, "reason": "簡短理由"}}
}}"""
            
            response = self._call_llm(llm_id, prompt)
            parsed = self._extract_json(response)
            
            if parsed:
                results[llm_id] = {"parsed": parsed, "raw": response}
                print(f"  ✅ 分析完成，評估了 {len(parsed)} 支股票")
            else:
                results[llm_id] = {"parsed": {}, "raw": response}
                print(f"  ⚠️ 無法解析 JSON")
            
            time.sleep(1)
        
        return results
    
    def run_round2(self, stock_group: List[Dict], round1_results: Dict, group_id: int) -> Dict:
        """Round 2: 交叉質疑"""
        print(f"\n{'='*60}")
        print(f"🔥 Round 2 - 第 {group_id} 組交叉質疑")
        print(f"{'='*60}")
        
        # 找出分歧最大的股票
        all_tickers = set()
        for llm_results in round1_results.values():
            if llm_results.get("parsed"):
                all_tickers.update(llm_results["parsed"].keys())
        
        disagreements = []
        for ticker in all_tickers:
            scores = []
            for llm_id, llm_results in round1_results.items():
                if llm_results.get("parsed") and ticker in llm_results["parsed"]:
                    score = llm_results["parsed"][ticker].get("score", 50)
                    scores.append((llm_id, score))
            
            if len(scores) >= 2:
                max_score = max(s[1] for s in scores)
                min_score = min(s[1] for s in scores)
                if max_score - min_score >= 20:
                    disagreements.append({
                        "ticker": ticker,
                        "scores": scores,
                        "diff": max_score - min_score
                    })
        
        if not disagreements:
            print("  ✅ 本組無重大分歧，跳過 Round 2")
            return round1_results
        
        # 對分歧最大的進行討論
        disagreements.sort(key=lambda x: x["diff"], reverse=True)
        top_disagreement = disagreements[0]
        
        print(f"  📌 最大分歧：{top_disagreement['ticker']} (差異 {top_disagreement['diff']} 分)")
        
        return round1_results
    
    def final_vote(self, stock_group: List[Dict], round_results: Dict) -> List[Dict]:
        """最終投票"""
        print(f"\n{'='*60}")
        print(f"🗳️ 最終投票")
        print(f"{'='*60}")
        
        # 彙總所有評分
        ticker_scores = {}
        
        for llm_id, llm_results in round_results.items():
            if not llm_results.get("parsed"):
                continue
            
            config = LLM_CONFIG.get(llm_id, {})
            
            for ticker, data in llm_results["parsed"].items():
                if ticker not in ticker_scores:
                    ticker_scores[ticker] = {
                        "scores": [],
                        "reasons": [],
                        "votes": {"buy": 0, "hold": 0, "sell": 0}
                    }
                
                score = data.get("score", 50)
                reason = data.get("reason", "")
                
                ticker_scores[ticker]["scores"].append(score)
                ticker_scores[ticker]["reasons"].append(f"{config.get('name', llm_id)}: {reason}")
                
                if score >= 75:
                    ticker_scores[ticker]["votes"]["buy"] += 1
                elif score >= 50:
                    ticker_scores[ticker]["votes"]["hold"] += 1
                else:
                    ticker_scores[ticker]["votes"]["sell"] += 1
        
        # 計算最終結果
        final_results = []
        passed = 0
        rejected = 0
        
        for ticker, data in ticker_scores.items():
            avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0
            votes = data["votes"]
            
            # 決定共識
            if votes["buy"] >= 2:
                consensus = "買入"
                passed += 1
            elif votes["sell"] >= 2:
                consensus = "賣出"
                rejected += 1
            else:
                consensus = "觀望"
                passed += 1
            
            final_results.append({
                "ticker": ticker,
                "final_score": round(avg_score, 1),
                "consensus": consensus,
                "individual_scores": data["scores"],
                "comments": data["reasons"][:3]
            })
        
        final_results.sort(key=lambda x: x["final_score"], reverse=True)
        
        print(f"\n✅ 投票完成！通過: {passed} 支 | 否決: {rejected} 支")
        
        return final_results
    
    def run(self, top_n: int = 20) -> List[Dict]:
        """執行完整討論流程"""
        print("\n" + "="*70)
        print("🤖 Stage 3: Multi-Agent LLM 討論系統 (4人版)")
        print("="*70)
        
        # 載入數據
        df = self.load_stage2_results()
        if df.empty:
            print("❌ 無數據可分析")
            return []
        
        stocks = df.head(top_n * 2).to_dict('records')
        print(f"\n📊 總共 {len(stocks)} 支股票待討論")
        
        # 分組討論
        group_size = 10
        all_results = []
        
        for i in range(0, len(stocks), group_size):
            group = stocks[i:i+group_size]
            group_id = i // group_size + 1
            
            print(f"\n{'#'*60}")
            print(f"# 第 {group_id} 組討論 ({len(group)} 支股票)")
            print(f"{'#'*60}")
            
            # Round 1
            round1_results = self.run_round1(group, group_id)
            
            # Round 2
            round2_results = self.run_round2(group, round1_results, group_id)
            
            # 投票
            group_results = self.final_vote(group, round2_results)
            all_results.extend(group_results)
            
            print(f"\n✅ 第 {group_id} 組完成，產生 {len(group_results)} 支候選")
        
        # 最終排名
        all_results.sort(key=lambda x: x["final_score"], reverse=True)
        self.results = all_results[:top_n]
        
        print(f"\n{'='*70}")
        print(f"🏆 Stage 3 完成！最終 Top {len(self.results)}")
        print(f"{'='*70}")
        
        for i, r in enumerate(self.results[:10], 1):
            emoji = "🟢" if r["consensus"] == "買入" else "🟡" if r["consensus"] == "觀望" else "🔴"
            print(f" {i:2}. {r['ticker']:6} | {r['final_score']:5.1f}分 | {emoji} {r['consensus']}")
        
        return self.results
    
    def save_report(self) -> str:
        """儲存報告"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        output_dir = f"reports/stage3/{timestamp}"
        os.makedirs(output_dir, exist_ok=True)
        
        # CSV
        df = pd.DataFrame(self.results)
        df.to_csv(f"{output_dir}/stage3_top20.csv", index=False)
        
        # JSON
        with open(f"{output_dir}/stage3_discussion.json", "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "llm_config": {k: {"name": v["name"], "model": v["model"]} for k, v in LLM_CONFIG.items()},
                "final_ranking": self.results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 報告已儲存: {output_dir}")
        return output_dir


def main():
    print("\n" + "🤖" * 25)
    print("Stage 3: Multi-Agent LLM 討論系統 (4人版)")
    print("🤖" * 25)
    
    stage3 = Stage3Discussion()
    results = stage3.run(top_n=20)
    
    if results:
        stage3.save_report()
    
    return results


if __name__ == "__main__":
    main()
