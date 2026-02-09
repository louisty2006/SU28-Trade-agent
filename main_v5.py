"""
REISHI 霊視 v5.0 MVP - 主程式

完整系统架构：
- 五层防护系统
- 五大AI方向分析
- 决策引擎
- 即时监控

API Key：與 v4.3 共用同一 .env（OPENROUTER_API_KEY / SCITELY_API_KEY 等）
"""

import argparse
import sys
import time
from datetime import datetime, timedelta
import os

# 與 v4.3 相同：依序載入 .env，既有 API Key（OPENROUTER / SCITELY 等）直接沿用
from dotenv import load_dotenv
_env_dir = os.path.dirname(os.path.abspath(__file__))
_DEBUG_LOG_PATH = os.path.join(_env_dir, ".cursor", "debug.log")
_DEBUG_LOG_FALLBACK = os.path.join(_env_dir, "debug_run.log")

def _debug_log(payload):
    """寫入兩處 log，方便在專案根目錄用 tail/grep 查看。"""
    for _path in (_DEBUG_LOG_PATH, _DEBUG_LOG_FALLBACK):
        try:
            os.makedirs(os.path.dirname(_path), exist_ok=True)
            with open(_path, "a", encoding="utf-8") as _f:
                _f.write(__import__("json").dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            pass

_interactive_run_id = None

def _run_summary(line: str, run_id: str = None):
    """寫入單行運行摘要到 debug_run.log 與 .cursor/debug.log，方便 tail -1 或 grep [REISHI] 查看有效性/錯誤。"""
    rid = run_id if run_id is not None else globals().get("_interactive_run_id") or str(int(time.time() * 1000))
    msg = f"[REISHI] run_id={rid} {line}"
    for _path in (_DEBUG_LOG_PATH, _DEBUG_LOG_FALLBACK):
        try:
            os.makedirs(os.path.dirname(_path), exist_ok=True)
            with open(_path, "a", encoding="utf-8") as _f:
                _f.write(msg + "\n")
        except Exception:
            pass
_env_candidates = [
    os.path.join(_env_dir, ".env"),
    os.path.expanduser("~/stock_scanner/.env"),
    os.path.join(_env_dir, "..", ".env"),
]
load_dotenv()
for _path in _env_candidates:
    if _path and os.path.isfile(_path):
        load_dotenv(_path, override=True)

# Core modules
from core.data_validator import DataValidator
from core.anti_hallucination import AntiHallucination
from core.decision_engine import DecisionEngine, PortfolioState, AllAnalyses
from core.output_validator import OutputValidator
from core.final_auditor import FinalAuditor

# Analysis modules
from analysis.pattern_recognition import PatternRecognition
from analysis.fundamental_analysis import FundamentalAnalyzer
from analysis.sentiment_analysis import SentimentAnalyzer
from analysis.multi_agent import MultiAgentAnalysis
from analysis.knowledge_graph import KnowledgeGraph
from analysis.causal_reasoning import CausalReasoning

# Memory module
from memory.reishi_memory import ReishiMemory

# Monitoring modules
from monitoring.realtime_monitor import RealtimeMonitor
from monitoring.notification_service import TelegramNotifier

# Reporting module
from reporting.daily_report import DailyReportGenerator


class ReishiV5:
    """
    REISHI 霊視 v5.0 主程式
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        print("=" * 70)
        print("🔮 REISHI 霊視 v5.3")
        print("=" * 70)
        print("初始化系统...")
        
        # 初始化所有模块
        self.data_validator = DataValidator()
        self.anti_hallucination = AntiHallucination()
        self.pattern_recognition = PatternRecognition()
        self.fundamental_analyzer = FundamentalAnalyzer()
        self.knowledge_graph = KnowledgeGraph()
        self.causal_reasoning = CausalReasoning(self.knowledge_graph)
        self.sentiment_analyzer = SentimentAnalyzer()
        self.multi_agent = MultiAgentAnalysis()
        self.memory = ReishiMemory()
        self.output_validator = OutputValidator()
        self.final_auditor = FinalAuditor()
        self.decision_engine = DecisionEngine(
            self.anti_hallucination,
            self.output_validator
        )
        self.report_generator = DailyReportGenerator()
        self.monitor = RealtimeMonitor()
        self.notifier = TelegramNotifier(
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        )
        
        print("✓ 所有模块已加载")
        _clients = getattr(self.anti_hallucination, "_llm_clients", None)
        if _clients and _clients.has_any_key():
            _providers = _clients.available_providers()
            if len(_providers) == 1:
                print("✓ LLM 已連接（1 個 Key，兼多角）：" + _providers[0])
            else:
                print("✓ LLM 已連接（四供應商與 v4.3 相同）：" + ", ".join(_providers))
        else:
            print("ℹ️  LLM 未配置（請設 SCITELY / COHERE / MISTRAL / OPENROUTER 任一 API Key）")
        
        # 默认组合状态
        self.portfolio = PortfolioState(
            cash=40_000.0,  # 40,000 HKD
            positions=[],
            total_value=40_000.0
        )
    
    def run_daily(self):
        """
        每日运行。Log 依流程圖結構輸出：輸入層 → 第一層防護 → 五大 AI 分析層 → 第二層防護 → 輸出驗證與審計 → 報告。
        """
        from reporting.flow_logger import FlowLogger
        print("\n" + "=" * 70)
        print("🔮 REISHI 霊視 v5.3 - 每日分析")
        print("=" * 70)
        flow_logger = FlowLogger(flush_each=True)
        try:
            print("取得掃描名單…", flush=True)
            tickers_to_fetch = self._get_scan_tickers()
            print(f"  掃描名單：共 {len(tickers_to_fetch)} 檔", flush=True)
            # 即時新聞：Finnhub 公司新聞（輸入層用）；僅對前 N 檔請求，避免 9000 檔導致長時間/卡住
            NEWS_CAP = 150
            tickers_for_news = tickers_to_fetch[:NEWS_CAP]
            from utils.news_fetcher import fetch_news_for_tickers, to_news_objects
            to_date = datetime.now().strftime("%Y-%m-%d")
            from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            print(f"正在取得新聞（Finnhub，前 {len(tickers_for_news)} 檔）…", flush=True)
            all_news_raw, news_by_ticker_raw = fetch_news_for_tickers(tickers_for_news, from_date, to_date)
            # 其餘 ticker 補空列表，供後續 sentiment 使用
            for t in tickers_to_fetch:
                if t not in news_by_ticker_raw:
                    news_by_ticker_raw[t] = []
            print(f"  新聞取得完成（共 {len(all_news_raw)} 筆）", flush=True)
            all_news_for_causal = to_news_objects(all_news_raw)
            news_by_ticker_for_sentiment = {t: to_news_objects(news_by_ticker_raw.get(t, [])) for t in tickers_to_fetch}
            if all_news_raw:
                news_desc = f"已載入 {len(all_news_raw)} 筆（Finnhub，{from_date}～{to_date}）"
            else:
                try:
                    from config import FINNHUB_API_KEY
                    news_desc = "0 筆（該區間無資料）" if (FINNHUB_API_KEY or os.getenv("FINNHUB_API_KEY")) else "0 筆（未設定 FINNHUB_API_KEY）"
                except Exception:
                    news_desc = "0 筆（未設定 FINNHUB_API_KEY）"
            # 輸入層：你的狀態 → 市場數據 → 即時新聞 → 霊視記憶（標明數據源）
            your_state = f"現金 {self.portfolio.cash:,.0f}、持倉 {len(self.portfolio.positions)} 檔、總值 {self.portfolio.total_value:,.0f}"
            market_data_desc = f"掃描標的 {len(tickers_to_fetch)} 檔（{', '.join(tickers_to_fetch[:8])}{' ...' if len(tickers_to_fetch) > 8 else ''}）；數據源：Yahoo (DataFetcher) / yfinance"
            try:
                mem_stats = self.memory.get_statistics()
                memory_desc = f"已載入，歷史建議 {mem_stats.get('total_recommendations', 0)} 筆、已執行 {mem_stats.get('executed', 0)}、已完成 {mem_stats.get('completed', 0)}"
            except Exception:
                memory_desc = "已載入"
            flow_logger.log_input_layer(your_state, market_data_desc, news_desc, memory_desc, as_of_date="", mode="每日分析")
            # 1. 获取并验证数据 — 第一層防護：數據驗證（先標明步驟與數據源，再拉取）
            print("\n[1/9] 数据获取与验证...")
            print("[REISHI] [步驟1] 判斷基準：Yahoo/多數據源 K 線；僅美股/港股交易所；數據源依 config。")
            flow_logger.log_layer1_start("Yahoo (DataFetcher) / yfinance（依環境）")
            market_data, data_source = self._fetch_and_validate_data(on_ticker=lambda t, i, n: flow_logger.log_layer1_fetch(t, i, n))
            tickers = list(market_data.keys()) or tickers_to_fetch
            flow_logger.log_layer1_result(len(market_data), tickers, data_source=data_source)
            print(f"[REISHI] 擇要：有效 ticker 數={len(market_data)}，來源={data_source}，前5檔={tickers[:5]}")
            if not market_data:
                print("   ⚠ 無市場數據，分析將僅有架構輸出")
            # 基本面分析（數據源：DataFetcher / yfinance 財報與估值）
            print("\n[2/9] 基本面分析...")
            print("[REISHI] [步驟2] 判斷基準：get_yahoo_info / get_yahoo_financials_as_of；PE/PB/ROE/營收與盈利成長/利潤率。")
            fundamental_by_ticker = self.fundamental_analyzer.analyze_batch(
                tickers, on_ticker=lambda t, i, n: flow_logger.log_layer1_fetch(t, i, n) if flow_logger else None
            )
            _n_f = len(fundamental_by_ticker)
            _preview_f = [f"{t}: {getattr(fundamental_by_ticker[t], 'summary_text', '')[:40]}…" for t in list(fundamental_by_ticker.keys())[:3]]
            print(f"[REISHI] 擇要：成功基本面數={_n_f}，前3檔擇要={_preview_f}")
            # 五大 AI 方向分析層
            flow_logger.log_ai_layer_start()
            # 3. 图表型态识别（數據源：第一層驗證後的 K 線）
            print("\n[3/9] 图表型态识别...")
            print("[REISHI] [步驟3] 判斷基準：收盤≥20日高 0.98 視為突破；成交量/均線未檢核。")
            flow_logger.log_ai_2_start(len(tickers), data_sources="第一層驗證後的 K 線（步驟 1 的 Yahoo/DataFetcher）")
            pattern_analysis = self.pattern_recognition.scan_all(tickers, market_data, on_ticker=lambda t, i, n: flow_logger.log_ai_2_fetch(t, i, n))
            flow_logger.log_ai_2_result(len(pattern_analysis), [getattr(c, "ticker", "") for c in pattern_analysis] if pattern_analysis else None)
            _pt = [getattr(c, "ticker", "?") for c in (pattern_analysis or [])[:5]]
            print(f"[REISHI] 擇要：圖表候選數={len(pattern_analysis or [])}，前5檔={_pt}")
            # 4. 因果推理（數據源：即時新聞 Finnhub、持倉本地）
            print("\n[4/9] 因果推理...")
            print("[REISHI] [步驟4] 判斷基準：Finnhub 新聞 + 持倉；LLM 因果鏈（四角）。")
            flow_logger.log_ai_3_start(data_sources="即時新聞（Finnhub）、持倉（本地）；LLM 因果鏈（四角）")
            causal_analysis = self.causal_reasoning.analyze_all(news=all_news_for_causal, portfolio=self.portfolio.positions)
            flow_logger.log_ai_3_result()
            print("[REISHI] 擇要：因果推理完成（新聞筆數、持倉數已納入）。")
            # 5. 情绪分析（數據源：即時新聞 Finnhub、標的列表）
            print("\n[5/9] 情绪分析...")
            print("[REISHI] [步驟5] 判斷基準：新聞內容→LLM；輸出 score(-1~1)/key_factors/risks；無新聞或失敗→中性。")
            flow_logger.log_ai_4_start(len(tickers), data_sources="即時新聞（Finnhub）、標的列表；LLM 情緒分析（四角）")
            sentiment_analysis = self.sentiment_analyzer.analyze_batch(tickers, on_ticker=lambda t, i, n: flow_logger.log_ai_4_fetch(t, i, n), news_by_ticker=news_by_ticker_for_sentiment)
            flow_logger.log_ai_4_result()
            _s_preview = [(t, getattr(sentiment_analysis.get(t), "score", 0.5)) for t in list(sentiment_analysis.keys())[:5]]
            print(f"[REISHI] 擇要：情緒分析檔數={len(sentiment_analysis)}，前5檔 score={_s_preview}")
            # 6. Multi-Agent 分析（數據源：圖表候選 + 市場數據；LLM 四角）
            print("\n[6/9] Multi-Agent 协作分析...")
            print("[REISHI] [步驟6] 判斷基準：三角色(Fundamental/Sentiment/Valuation)→單輪共識；輸出 consensus_action/disagreements/final_recommendation。")
            flow_logger.log_ai_5_start(len(pattern_analysis), data_sources="圖表候選（步驟 3）、市場數據（步驟 1）；LLM 四角（Scitely/Cohere/Mistral/OpenRouter）")
            multi_agent_analysis = self.multi_agent.analyze_all(
                candidates=pattern_analysis,
                data={
                    "market_data": market_data,
                    "fundamental_by_ticker": fundamental_by_ticker,
                    "sentiment_by_ticker": sentiment_analysis,
                },
            )
            flow_logger.log_ai_5_result()
            _ma = multi_agent_analysis or {}
            _by_t = _ma.get("by_ticker") or {}
            _ma_preview = [f"{t}: {getattr(_by_t[t], 'consensus_action', '?')}" for t in list(_by_t.keys())[:5]]
            print(f"[REISHI] 擇要：Multi-Agent 候選數={len(_by_t)}，前5檔共識={_ma_preview}")
            # 7. 霊視记忆参考（數據源：霊視記憶 DB、圖表候選）
            print("\n[7/9] 霊視记忆参考...")
            print("[REISHI] [步驟7] 判斷基準：霊視記憶 DB + 圖表候選；LLM 摘要/洞察（四角）。")
            flow_logger.log_ai_6_start(data_sources="霊視記憶 DB（本地）、圖表候選（步驟 3）；LLM 摘要/洞察（四角）")
            memory_insights = self.memory.get_insights_for_candidates(pattern_analysis)
            n_insights = len(memory_insights.get("insights", [])) if isinstance(memory_insights, dict) else 0
            flow_logger.log_ai_6_result(n_insights)
            print(f"[REISHI] 擇要：霊視記憶洞察數={n_insights}")
            # 8. 决策引擎 — 第二層防護：LLM 防幻覺（數據源：防幻覺模組 + 步驟 1～7 結果）
            print("\n[8/9] 决策引擎...")
            print("[REISHI] [步驟8] 判斷基準：三大原則(賺最多/賺最快/風險最少)+ AllAnalyses 摘要→防幻覺 LLM→解析 actions。")
            flow_logger.log_layer2_start(data_sources="防幻覺模組（Scitely/Cohere/Mistral/OpenRouter）、步驟 1～7 分析結果")
            all_analyses = AllAnalyses(
                pattern=pattern_analysis,
                causal=causal_analysis,
                sentiment=sentiment_analysis,
                multi_agent=multi_agent_analysis,
                memory=memory_insights,
                fundamental=fundamental_by_ticker,
            )
            decision = self.decision_engine.decide(
                state=self.portfolio,
                analyses=all_analyses,
                on_llm_progress=lambda phase, total, msg, provider=None: flow_logger.log_layer2_llm_phase(phase, total, msg, provider)
            )
            acts = getattr(decision, "actions", []) or []
            summary = ", ".join([f"{getattr(a, 'action', '')} {getattr(a, 'ticker', '')}" for a in acts[:3]]) if acts else "無操作"
            flow_logger.log_layer2_result(len(acts), summary)
            print(f"[REISHI] 擇要：決策解析 actions 數={len(acts)}，前3筆={summary}")
            # 9. 验证 + 审计
            print("\n[9/9] 最终验证与审计...")
            print("[REISHI] [步驟9] 判斷基準：output_validator 邏輯/數字檢查；final_auditor 審計（只檢查不判斷）。")
            flow_logger.log_validation_start()
            validation = self.output_validator.validate_decision(decision, all_analyses)
            flow_logger.log_audit_start()
            audit = self.final_auditor.audit(decision, all_analyses)
            print(f"[REISHI] 擇要：驗證 passed={getattr(validation, 'passed', None)}；審計完成。")
            # 生成报告
            print("\n生成报告...")
            report = self.report_generator.generate(decision, all_analyses, audit)
            report_dir = f"reports/daily"
            os.makedirs(report_dir, exist_ok=True)
            report_path = f"{report_dir}/{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.md"
            report.save(report_path)
            flow_logger.log_report_start(report_path)
            flow_logger.log_flow_end()
            self.notifier.send_daily_report(report)
            print("\n" + "=" * 70)
            print("✅ 每日分析完成！")
            print(f"📄 报告已保存: {report_path}")
            print("=" * 70)
            print("\n" + report.to_text())
            return report
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    # 與 docs/API_KEYS_IN_FLOW.md / Logic Flow 對應的步驟名稱
    FLOW_STEPS = (
        "數據獲取與驗證",
        "圖表型態識別",
        "因果推理",
        "情緒分析",
        "Multi-Agent 協作分析",
        "霊視記憶參考",
        "決策引擎",
    )

    def run_daily_for_backtest(self, as_of_date, backtest_start=None, stock_count: int = 20, silent: bool = True, on_progress=None, on_llm_progress=None, on_ticker=None, on_step_activity=None, flow_logger=None, report_dir=None, step_log=None, day_index: int = 0, total_days: int = 0, day_start_ts: float = 0, est_per_day_sec: float = 0, pre_fetched_market_data=None):
        """
        為回測跑單日 v5.0 流程：數據僅到 as_of_date（無偷看），回傳 (decision, all_analyses)。
        stock_count: 每日掃描股票數量（預設 20）。
        pre_fetched_market_data: 若提供（本地 parquet），則跳過網路取數，直接用此 dict[ticker]->DataFrame。
        flow_logger: 可選 FlowLogger。step_log(msg): 可選，每步寫入步驟日誌檔。
        day_index/total_days/day_start_ts/est_per_day_sec: 供進度顯示整體剩餘時間用。
        """
        # #region agent log
        try:
            import json, time
            with open("/Users/lautinyam/stock_scanner/.cursor/debug.log", "a", encoding="utf-8") as _dbg:
                _dbg.write(json.dumps({"hypothesisId": "H5", "location": "main_v5.py:236", "message": "run_daily_for_backtest_entry", "data": {"stock_count": stock_count, "as_of_date": str(as_of_date)}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session"}, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
        from datetime import timedelta
        from reporting.step_report import write_step_report
        total_steps = 7
        flow_steps = getattr(ReishiV5, "FLOW_STEPS", ("數據獲取與驗證", "圖表型態識別", "因果推理", "情緒分析", "Multi-Agent 協作分析", "霊視記憶參考", "決策引擎"))
        short_names = ("取數", "圖形掃描", "因果分析", "情緒分析", "多智能體", "記憶洞察", "決策引擎")
        def _prog(i, name, pct=100):
            if callable(on_progress):
                on_progress(i, total_steps, name, pct)
        def _activity(step_i, msg):
            if callable(on_step_activity):
                on_step_activity(step_i, msg)
        def _on_ticker_wrap(t, i, n):
            # #region agent log
            if i == 1:
                try:
                    import json
                    with open("/Users/lautinyam/stock_scanner/.cursor/debug.log", "a", encoding="utf-8") as _dbg:
                        _dbg.write(json.dumps({"hypothesisId": "H2", "message": "on_ticker_wrap_first", "data": {"ticker": str(t), "has_flow_logger": flow_logger is not None, "has_on_ticker": callable(on_ticker)}, "timestamp": int(time.time() * 1000)}, ensure_ascii=False) + "\n")
                except Exception:
                    pass
            # #endregion
            if flow_logger:
                flow_logger.log_layer1_fetch(t, i, n)
            if callable(on_ticker):
                on_ticker(t, i, n)
        def _on_llm_wrap(phase, total, message, provider=None):
            _step(f"決策引擎 LLM 第 {phase}/{total} 「{message}」" + (f" 使用 {provider}" if provider else " 進行中…"))
            if flow_logger:
                flow_logger.log_layer2_llm_phase(phase, total, message, provider)
            if callable(on_llm_progress):
                on_llm_progress(phase, total, message, provider)
        _step = step_log if callable(step_log) else (lambda msg: None)

        start_d = (backtest_start if backtest_start else (as_of_date - timedelta(days=90)) if hasattr(as_of_date, "day") else None)
        end_str = as_of_date.strftime("%Y-%m-%d") if hasattr(as_of_date, "strftime") else as_of_date
        start_str = start_d.strftime("%Y-%m-%d") if start_d and hasattr(start_d, "strftime") else None
        tickers_to_fetch = self._get_scan_tickers(cap=stock_count)
        _step(f"取得掃描列表 共 {len(tickers_to_fetch)} 檔")
        # #region agent log
        try:
            import json, time
            with open("/Users/lautinyam/stock_scanner/.cursor/debug.log", "a", encoding="utf-8") as _dbg:
                _dbg.write(json.dumps({"hypothesisId": "H1", "location": "main_v5.py:286", "message": "tickers_to_fetch_after_get_scan_tickers", "data": {"stock_count_param": stock_count, "tickers_count": len(tickers_to_fetch), "first_10_tickers": tickers_to_fetch[:10]}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session"}, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
        # 即時新聞：Finnhub（回測時用 as_of_date 區間，不偷看未來）
        from utils.news_fetcher import fetch_news_for_tickers, to_news_objects
        to_date_news = end_str
        from_date_news = (as_of_date - timedelta(days=7)).strftime("%Y-%m-%d") if hasattr(as_of_date, "strftime") else to_date_news
        _step(f"取得新聞 開始 {len(tickers_to_fetch)} 檔 ({from_date_news}～{to_date_news})")
        all_news_raw, news_by_ticker_raw = fetch_news_for_tickers(tickers_to_fetch, from_date_news, to_date_news)
        _step(f"取得新聞 完成 共 {len(all_news_raw)} 筆")
        all_news_for_causal = to_news_objects(all_news_raw)
        news_by_ticker_for_sentiment = {t: to_news_objects(news_by_ticker_raw.get(t, [])) for t in tickers_to_fetch}
        if all_news_raw:
            news_desc = f"已載入 {len(all_news_raw)} 筆（Finnhub，{from_date_news}～{to_date_news}）"
        else:
            try:
                from config import FINNHUB_API_KEY
                news_desc = "0 筆（該區間無資料）" if (FINNHUB_API_KEY or os.getenv("FINNHUB_API_KEY")) else "0 筆（未設定 FINNHUB_API_KEY）"
            except Exception:
                news_desc = "0 筆（未設定 FINNHUB_API_KEY）"
        if flow_logger:
            # 輸入層：你的狀態 → 市場數據 → 即時新聞 → 霊視記憶（標明數據源）
            your_state = f"現金 {self.portfolio.cash:,.0f}、持倉 {len(self.portfolio.positions)} 檔、總值 {self.portfolio.total_value:,.0f}"
            # #region agent log
            try:
                import json, time
                with open("/Users/lautinyam/stock_scanner/.cursor/debug.log", "a", encoding="utf-8") as _dbg:
                    _dbg.write(json.dumps({"hypothesisId": "H4", "location": "main_v5.py:313", "message": "flow_logger_market_data_desc", "data": {"tickers_to_fetch_count": len(tickers_to_fetch), "first_10": tickers_to_fetch[:10]}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session"}, ensure_ascii=False) + "\n")
            except Exception:
                pass
            # #endregion
            market_data_desc = f"掃描標的 {len(tickers_to_fetch)} 檔（{', '.join(tickers_to_fetch[:8])}{' ...' if len(tickers_to_fetch) > 8 else ''}）；數據源：Yahoo (DataFetcher) / yfinance"
            try:
                mem_stats = self.memory.get_statistics()
                memory_desc = f"已載入，歷史建議 {mem_stats.get('total_recommendations', 0)} 筆、已執行 {mem_stats.get('executed', 0)}、已完成 {mem_stats.get('completed', 0)}"
            except Exception:
                memory_desc = "已載入"
            flow_logger.log_input_layer(your_state, market_data_desc, news_desc, memory_desc, as_of_date=end_str, mode="回測（數據截至當日）")
        if not silent:
            print(f"   [回測日] 數據截至 {end_str}")
        # 細項 1：取數 — 第一層防護：數據驗證（先標明步驟與數據源，再拉取）
        if not silent:
            print("[REISHI] [回測步驟1] 判斷基準：K 線僅到 as_of_date；Yahoo/多數據源。")
        _prog(1, "取數", 0)
        _activity(1, "開始從數據源拉取歷史 K 線…")
        # #region agent log
        try:
            import json
            with open("/Users/lautinyam/stock_scanner/.cursor/debug.log", "a", encoding="utf-8") as _dbg:
                _dbg.write(json.dumps({"hypothesisId": "H1", "message": "before_log_layer1_start", "data": {"end_str": str(end_str)}, "timestamp": int(time.time() * 1000)}, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
        if flow_logger:
            flow_logger.log_layer1_start("本地 parquet" if pre_fetched_market_data else "Yahoo (DataFetcher) / yfinance（依環境）")
        _step(f"步驟1 數據獲取 開始 {len(tickers_to_fetch)} 檔")
        if pre_fetched_market_data is not None:
            market_data = pre_fetched_market_data
            data_source = "本地 parquet"
        else:
            market_data, data_source = self._fetch_and_validate_data(end_date=as_of_date, start_date=start_d, cap=stock_count, silent=silent, on_ticker=_on_ticker_wrap, on_fetch_progress=_step)
        _step(f"步驟1 數據獲取 完成 有效 {len(market_data)} 檔 來源 {data_source}")
        if not silent:
            print(f"[REISHI] 擇要：有效 ticker 數={len(market_data)}，來源={data_source}，前5={list(market_data.keys())[:5]}")
        # #region agent log
        try:
            import json
            with open("/Users/lautinyam/stock_scanner/.cursor/debug.log", "a", encoding="utf-8") as _dbg:
                _dbg.write(json.dumps({"hypothesisId": "H1", "message": "after_fetch_before_layer1_result", "data": {"n_market": len(market_data)}, "timestamp": int(time.time() * 1000)}, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
        # #region agent log
        try:
            import json
            with open("/Users/lautinyam/stock_scanner/.cursor/debug.log", "a", encoding="utf-8") as _dbg:
                _dbg.write(json.dumps({"hypothesisId": "H4", "message": "market_data_result", "data": {"n_valid": len(market_data), "valid_tickers": list(market_data.keys())[:5], "requested": len(tickers_to_fetch)}, "timestamp": int(time.time() * 1000)}, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
        if flow_logger:
            flow_logger.log_layer1_result(len(market_data), list(market_data.keys()), data_source=data_source)
        _activity(1, f"取數完成，共 {len(market_data)} 檔有效數據")
        _prog(1, "取數", 100)
        if report_dir:
            write_step_report(report_dir, 1, flow_steps[0], short_names[0], data_source=data_source)
        tickers = list(market_data.keys()) or tickers_to_fetch
        # 基本面分析（回測：僅用 as_of_date 及之前數據）
        if not silent:
            print("[REISHI] [回測步驟1b] 判斷基準：get_yahoo_financials_as_of(as_of_date)；不取未來。")
        _step("步驟1b 基本面分析 開始")
        fundamental_by_ticker = self.fundamental_analyzer.analyze_batch(
            tickers,
            as_of_date=end_str,
            backtest_start=start_str,
            on_ticker=lambda t, i, n: _activity(1, f"基本面 {t} ({i}/{n})") if callable(on_step_activity) else None,
        )
        _step(f"步驟1b 基本面分析 完成 有效 {len(fundamental_by_ticker)} 檔")
        if not silent:
            print(f"[REISHI] 擇要：基本面有效數={len(fundamental_by_ticker)}")
        # 五大 AI 方向分析層
        if flow_logger:
            flow_logger.log_ai_layer_start()
        # 細項 2：圖表型態識別（數據源：第一層驗證後的 K 線）
        if not silent:
            print("[REISHI] [回測步驟2] 判斷基準：收盤≥20日高 0.98 為突破。")
        _prog(2, "圖形掃描", 0)
        _step(f"步驟2 圖表型態識別 開始 {len(tickers)} 檔")
        _activity(2, f"開始掃描 {len(tickers)} 檔圖表型態（突破、VCP 等）…")
        if flow_logger:
            flow_logger.log_ai_2_start(len(tickers), data_sources="第一層驗證後的 K 線（步驟 1 的 Yahoo/DataFetcher）")
        pattern_analysis = self.pattern_recognition.scan_all(
            tickers, market_data,
            on_ticker=lambda t, i, n: (flow_logger.log_ai_2_fetch(t, i, n) if flow_logger else None, _activity(2, f"正在掃描 {t} ({i}/{n}) …") if callable(on_step_activity) else None)
        )
        # #region agent log
        try:
            import json
            _n_pattern = len(pattern_analysis) if pattern_analysis else 0
            _pattern_tickers = [getattr(c, "ticker", "") for c in (pattern_analysis or [])][:5]
            _pattern_details = []
            for c in (pattern_analysis or [])[:3]:
                _pattern_details.append({
                    "ticker": getattr(c, 'ticker', '?'),
                    "type": getattr(c, 'pattern_type', '?'),
                    "current_price": getattr(c, 'current_price', None),
                    "entry_low": getattr(c, 'entry_price_low', None),
                    "entry_high": getattr(c, 'entry_price_high', None),
                    "stop_loss": getattr(c, 'stop_loss', None),
                    "target_price": getattr(c, 'target_price', None),
                    "reasoning": (getattr(c, 'reasoning', '') or '')[:50]
                })
            with open("/Users/lautinyam/stock_scanner/.cursor/debug.log", "a", encoding="utf-8") as _dbg:
                _dbg.write(json.dumps({"hypothesisId": "H5", "message": "pattern_analysis_result", "data": {"n_candidates": _n_pattern, "candidate_tickers": _pattern_tickers, "pattern_details": _pattern_details}, "timestamp": int(time.time() * 1000)}, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
        if flow_logger:
            flow_logger.log_ai_2_result(len(pattern_analysis), [getattr(c, "ticker", "") for c in pattern_analysis] if pattern_analysis else None)
        _step(f"步驟2 圖表型態識別 完成 候選 {len(pattern_analysis)} 檔")
        if not silent:
            print(f"[REISHI] 擇要：圖表候選數={len(pattern_analysis)}，前5={[getattr(c,'ticker','') for c in (pattern_analysis or [])[:5]]}")
        _activity(2, f"圖形掃描完成，候選數 {len(pattern_analysis)}")
        _prog(2, "圖形掃描", 100)
        if report_dir:
            write_step_report(report_dir, 2, flow_steps[1], short_names[1])
        # 細項 3：因果推理（數據源：Finnhub 新聞、持倉）
        if not silent:
            print("[REISHI] [回測步驟3] 判斷基準：新聞+持倉→LLM 因果鏈。")
        _prog(3, "因果分析", 0)
        _step("步驟3 因果推理 開始（LLM 因果鏈）")
        _activity(3, "因果推理：分析新聞影響與持倉風險…")
        if flow_logger:
            flow_logger.log_ai_3_start(data_sources="即時新聞（Finnhub）、持倉（本地）；LLM 因果鏈（四角）")
        causal_analysis = self.causal_reasoning.analyze_all(news=all_news_for_causal, portfolio=self.portfolio.positions)
        if flow_logger:
            causal_lines = []
            if isinstance(causal_analysis, dict):
                s = causal_analysis.get("summary")
                if s:
                    causal_lines.append(s[:66])
                risk = causal_analysis.get("risk")
                if risk is not None and getattr(risk, "diversification_score", None) is not None:
                    causal_lines.append(f"分散化得分：{risk.diversification_score:.2f}")
                impact = causal_analysis.get("impact")
                if impact is not None:
                    chain = getattr(impact, "causal_chain", None) or getattr(impact, "suggested_action", "")
                    if chain:
                        causal_lines.append((str(chain))[:66])
            flow_logger.log_ai_3_result(causal_lines if causal_lines else None)
        _step("步驟3 因果推理 完成")
        if not silent:
            print("[REISHI] 擇要：因果推理完成。")
        _activity(3, "因果分析完成")
        _prog(3, "因果分析", 100)
        if report_dir:
            write_step_report(report_dir, 3, flow_steps[2], short_names[2])
        # 細項 4：情緒分析（數據源：Finnhub 新聞、標的）
        if not silent:
            print("[REISHI] [回測步驟4] 判斷基準：新聞→LLM 情緒；無新聞/失敗→中性。")
        _prog(4, "情緒分析", 0)
        _step(f"步驟4 情緒分析 開始 {len(tickers)} 檔")
        _activity(4, f"開始對 {len(tickers)} 檔做情緒分析…")
        if flow_logger:
            flow_logger.log_ai_4_start(len(tickers), data_sources="即時新聞（Finnhub）、標的列表；LLM 情緒分析（四角）")
        sentiment_analysis = self.sentiment_analyzer.analyze_batch(
            tickers,
            on_ticker=lambda t, i, n: (flow_logger.log_ai_4_fetch(t, i, n) if flow_logger else None, _activity(4, f"正在分析 {t} ({i}/{n}) …") if callable(on_step_activity) else None),
            news_by_ticker=news_by_ticker_for_sentiment,
        )
        if flow_logger:
            sentiment_lines = []
            if isinstance(sentiment_analysis, dict):
                for ticker, res in list(sentiment_analysis.items())[:5]:
                    score = getattr(res, "score", None)
                    conf = getattr(res, "confidence", None)
                    factors = getattr(res, "key_factors", []) or []
                    fstr = (factors[0][:20] + "…") if factors else "—"
                    if score is not None:
                        part = f"  {ticker}: 分數 {score:.2f}"
                        if conf is not None:
                            part += f" (信心 {conf:.2f})"
                        part += f" {fstr}"
                        sentiment_lines.append(part[:66])
            flow_logger.log_ai_4_result(sentiment_lines if sentiment_lines else None)
        _step("步驟4 情緒分析 完成")
        if not silent:
            print(f"[REISHI] 擇要：情緒分析檔數={len(sentiment_analysis)}")
        _activity(4, "情緒分析完成")
        _prog(4, "情緒分析", 100)
        if report_dir:
            write_step_report(report_dir, 4, flow_steps[3], short_names[3])
        # 細項 5：Multi-Agent 協作分析（數據源：圖表候選 + 市場數據；LLM 四角）
        if not silent:
            print("[REISHI] [回測步驟5] 判斷基準：三角色+單輪共識→consensus_action/disagreements。")
        _prog(5, "多智能體", 0)
        _step(f"步驟5 Multi-Agent 開始 候選 {len(pattern_analysis)} 檔（LLM 四角）")
        _activity(5, "多智能體：彙總候選與市場數據、產出共識…")
        if flow_logger:
            flow_logger.log_ai_5_start(len(pattern_analysis), data_sources="圖表候選（步驟 2）、市場數據（步驟 1）；LLM 四角（Scitely/Cohere/Mistral/OpenRouter）")
        multi_agent_analysis = self.multi_agent.analyze_all(
            candidates=pattern_analysis,
            data={
                "market_data": market_data,
                "fundamental_by_ticker": fundamental_by_ticker,
                "sentiment_by_ticker": sentiment_analysis,
            },
        )
        if flow_logger:
            multi_lines = []
            if isinstance(multi_agent_analysis, dict):
                s = multi_agent_analysis.get("summary")
                if s:
                    multi_lines.append(s[:66])
                for k in ("consensus_action", "consensus_score", "final_recommendation"):
                    v = multi_agent_analysis.get(k)
                    if v is not None:
                        multi_lines.append(f"  {k}: {str(v)[:60]}")
            flow_logger.log_ai_5_result(multi_lines if multi_lines else None)
        _step("步驟5 Multi-Agent 完成")
        if not silent:
            _by = (multi_agent_analysis or {}).get("by_ticker") or {}
            print(f"[REISHI] 擇要：Multi-Agent 候選數={len(_by)}")
        _activity(5, "多智能體分析完成")
        _prog(5, "多智能體", 100)
        if report_dir:
            write_step_report(report_dir, 5, flow_steps[4], short_names[4])
        # 細項 6：霊視記憶參考（數據源：霊視記憶 DB、圖表候選）
        if not silent:
            print("[REISHI] [回測步驟6] 判斷基準：霊視記憶 DB + 候選→LLM 洞察。")
        _prog(6, "記憶洞察", 0)
        _step("步驟6 霊視記憶 開始（LLM 摘要/洞察）")
        _activity(6, "霊視記憶：查詢歷史案例、提取洞察…")
        if flow_logger:
            flow_logger.log_ai_6_start(data_sources="霊視記憶 DB（本地）、圖表候選（步驟 2）；LLM 摘要/洞察（四角）")
        memory_insights = self.memory.get_insights_for_candidates(pattern_analysis)
        n_insights = len(memory_insights.get("insights", [])) if isinstance(memory_insights, dict) else 0
        if flow_logger:
            insight_preview = []
            if isinstance(memory_insights, dict):
                for ins in (memory_insights.get("insights") or [])[:2]:
                    if isinstance(ins, dict):
                        insight_preview.append((ins.get("summary") or ins.get("text") or str(ins))[:66])
                    else:
                        insight_preview.append(str(ins)[:66])
            flow_logger.log_ai_6_result(n_insights, insight_preview if insight_preview else None)
        _step(f"步驟6 霊視記憶 完成 {n_insights} 條洞察")
        if not silent:
            print(f"[REISHI] 擇要：洞察數={n_insights}")
        _activity(6, "記憶洞察完成")
        _prog(6, "記憶洞察", 100)
        if report_dir:
            write_step_report(report_dir, 6, flow_steps[5], short_names[5])
        if not silent:
            print("[REISHI] [回測步驟7] 判斷基準：AllAnalyses→防幻覺 LLM→解析 actions。")
        all_analyses = AllAnalyses(
            pattern=pattern_analysis,
            causal=causal_analysis,
            sentiment=sentiment_analysis,
            multi_agent=multi_agent_analysis,
            memory=memory_insights,
            fundamental=fundamental_by_ticker,
        )
        # 細項 7：決策引擎 — 第二層防護：LLM 防幻覺（數據源：防幻覺模組 + 步驟 1～6）
        _prog(7, "決策引擎（LLM 決策中…）", 0)
        _step("步驟7 決策引擎 開始（LLM 防幻覺 多輪）")
        _activity(7, "決策引擎：組裝 prompt、呼叫 LLM（防幻覺 + 自我質疑）…")
        if flow_logger:
            flow_logger.log_layer2_start(data_sources="防幻覺模組（Scitely/Cohere/Mistral/OpenRouter）、步驟 1～6 分析結果")
        decision = self.decision_engine.decide(
            state=self.portfolio, analyses=all_analyses, on_llm_progress=_on_llm_wrap
        )
        if flow_logger and decision:
            acts = getattr(decision, "actions", []) or []
            summary = ", ".join([f"{getattr(a, 'action', '')} {getattr(a, 'ticker', '')}" for a in acts[:3]]) if acts else "無操作"
            flow_logger.log_layer2_result(len(acts), summary)
        _step(f"步驟7 決策引擎 完成 " + (f"{len(getattr(decision, 'actions', []) or [])} 筆行動" if decision else "無決策"))
        _activity(7, "決策引擎完成，已解析行動與持倉建議")
        _prog(7, "決策引擎", 100)
        llm_reasoning = ""
        if decision and getattr(decision, "actions", None):
            parts = []
            for a in decision.actions[:5]:
                r = getattr(a, "reasoning", None) or (a.get("reasoning") if isinstance(a, dict) else None)
                if r:
                    parts.append(r[:300] + ("..." if len(r) > 300 else ""))
            llm_reasoning = "\n\n".join(parts) if parts else "（無具體推理文字）"
        if report_dir:
            write_step_report(report_dir, 7, flow_steps[6], short_names[6], llm_reasoning=llm_reasoning)
        if flow_logger and report_dir:
            flow_logger.log_report_start(report_dir)
            flow_logger.log_flow_end()
        return decision, all_analyses
    
    def _get_scan_tickers(self, cap: int = 9000):
        """取得要掃描的股票列表。cap 為數量上限（預設 9000，接近全美股）。"""
        # #region agent log
        try:
            import json, time
            with open("/Users/lautinyam/stock_scanner/.cursor/debug.log", "a", encoding="utf-8") as _dbg:
                _dbg.write(json.dumps({"hypothesisId": "H1", "location": "main_v5.py:530", "message": "_get_scan_tickers_entry", "data": {"cap": cap}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session"}, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
        import yaml
        tickers = []
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # 優先從完整股票池取（約 9000+ 檔）
        complete_paths = [
            os.path.join(base_dir, "data", "COMPLETE_ALL_STOCKS_FINAL.csv"),
            os.path.join(base_dir, "COMPLETE_ALL_STOCKS_FINAL.csv"),
        ]
        for csv_path in complete_paths:
            if os.path.isfile(csv_path):
                try:
                    import csv
                    with open(csv_path, "r", encoding="utf-8-sig") as f:
                        reader = csv.DictReader(f)
                        col = "Symbol" if (reader.fieldnames and "Symbol" in reader.fieldnames) else "symbol"
                        _seen = set()
                        for row in reader:
                            sym = (row.get(col) or row.get("Symbol") or row.get("symbol") or "").strip()
                            if sym and sym.upper() not in _seen:
                                _seen.add(sym.upper())
                                tickers.append(sym)
                                if len(tickers) >= cap:
                                    break
                        if len(tickers) >= cap:
                            break
                    if tickers:
                        if len(tickers) > cap:
                            import random
                            random.shuffle(tickers)
                        return tickers[:cap]
                except Exception:
                    tickers = []
                    break
        # 若無完整池或讀取失敗，從 us_universe.csv 取美股
        us_path = os.path.join(base_dir, "data", "us_universe.csv")
        if os.path.isfile(us_path):
            try:
                import csv
                with open(us_path, "r", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        sym = (row.get("symbol") or row.get("Symbol") or "").strip()
                        if sym:
                            tickers.append(sym)
                # #region agent log
                try:
                    import json, time
                    with open("/Users/lautinyam/stock_scanner/.cursor/debug.log", "a", encoding="utf-8") as _dbg:
                        _dbg.write(json.dumps({"hypothesisId": "H1", "location": "main_v5.py:545", "message": "us_universe_loaded", "data": {"us_path": us_path, "tickers_loaded": len(tickers), "first_10": tickers[:10]}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session"}, ensure_ascii=False) + "\n")
                except Exception:
                    pass
                # #endregion
            except Exception as e:
                # #region agent log
                try:
                    import json, time
                    with open("/Users/lautinyam/stock_scanner/.cursor/debug.log", "a", encoding="utf-8") as _dbg:
                        _dbg.write(json.dumps({"hypothesisId": "H1", "location": "main_v5.py:546", "message": "us_universe_load_failed", "data": {"error": str(e)}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session"}, ensure_ascii=False) + "\n")
                except Exception:
                    pass
                # #endregion
                pass
        # 若 us_universe 不足，從 config.yaml 補
        if len(tickers) < cap and os.path.isfile("config.yaml"):
            try:
                with open("config.yaml", "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                if cfg and isinstance(cfg.get("mvp"), dict):
                    _seen = set(t.upper() for t in tickers)
                    for sym in (cfg["mvp"].get("scan_tickers") or []):
                        if sym.upper() not in _seen:
                            tickers.append(sym)
                            _seen.add(sym.upper())
            except Exception:
                pass
        # 若仍不足，從環境變數或預設名單補足
        if len(tickers) < cap:
            _seen = set(t.upper() for t in tickers)
            env_tickers = os.getenv("V5_SCAN_TICKERS", "AAPL,GOOGL,MSFT,TSLA,NVDA")
            for sym in [t.strip() for t in env_tickers.split(",") if t.strip()]:
                if sym.upper() not in _seen and len(tickers) < cap:
                    tickers.append(sym)
                    _seen.add(sym.upper())
        # 最後用預設流動性名單補足
        if len(tickers) < cap:
            _seen = set(t.upper() for t in tickers)
            _default = ("AAPL", "GOOGL", "MSFT", "AMZN", "NVDA", "META", "TSLA", "BRK.B", "JPM", "V", "JNJ", "WMT", "PG", "UNH", "HD", "DIS", "BAC", "ADBE", "XOM", "NFLX", "CRM", "COST", "PEP", "AVGO", "TMO", "ABBV", "ACN", "MRK", "LLY", "CVX")
            for sym in _default:
                if len(tickers) >= cap:
                    break
                if sym.upper() not in _seen:
                    tickers.append(sym)
                    _seen.add(sym.upper())
        if len(tickers) > cap:
            import random
            random.shuffle(tickers)
        return tickers[:cap]

    def _fetch_and_validate_data(self, end_date=None, start_date=None, cap: int = 9000, silent: bool = False, on_ticker=None, on_fetch_progress=None):
        """获取并验证市场数据。on_fetch_progress(msg) 可選，並行取得時每 N 筆回報一次（同時會 print）。"""
        import logging
        _yf_log = logging.getLogger("yfinance")
        _yf_prev_level = _yf_log.level
        _yf_log.setLevel(logging.ERROR)
        _yf_log.disabled = True
        try:
            return self._fetch_and_validate_data_impl(end_date, start_date, cap, silent, on_ticker, on_fetch_progress)
        finally:
            _yf_log.disabled = False
            _yf_log.setLevel(_yf_prev_level)

    def _fetch_and_validate_data_impl(self, end_date=None, start_date=None, cap: int = 9000, silent: bool = False, on_ticker=None, on_fetch_progress=None):
        # #region agent log
        try:
            import json, time
            with open("/Users/lautinyam/stock_scanner/.cursor/debug.log", "a", encoding="utf-8") as _dbg:
                _dbg.write(json.dumps({"hypothesisId": "H3", "location": "main_v5.py:604", "message": "_fetch_and_validate_data_entry", "data": {"cap": cap}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session"}, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
        tickers = self._get_scan_tickers(cap=cap)
        market_data = {}
        data_source = "yfinance"
        end_str = end_date.strftime("%Y-%m-%d") if hasattr(end_date, "strftime") else end_date
        start_str = start_date.strftime("%Y-%m-%d") if start_date and hasattr(start_date, "strftime") else start_date
        # #region agent log
        try:
            import json
            with open("/Users/lautinyam/stock_scanner/.cursor/debug.log", "a", encoding="utf-8") as _dbg:
                _dbg.write(json.dumps({"hypothesisId": "H4", "message": "fetch_params", "data": {"end_str": end_str, "start_str": start_str, "n_tickers": len(tickers), "tickers_sample": tickers[:3]}, "timestamp": int(time.time() * 1000)}, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
        n_tickers = len(tickers)
        if not silent and n_tickers > 100:
            _progress_every = max(50, min(500, n_tickers // 10))
            print(f"    開始取得 {n_tickers} 檔 K 線（每 {_progress_every} 檔顯示進度）…", flush=True)
        _max_workers = min(16, max(4, n_tickers))
        try:
            from utils.data_fetcher import DataFetcher
            from concurrent.futures import ThreadPoolExecutor, as_completed
            fetcher = DataFetcher()
            data_source = "Yahoo (DataFetcher)"

            def _fetch_one(t):
                try:
                    df = fetcher.get_yahoo_history(t, period="90d", end_date=end_str, start_date=start_str)
                    return (t, df, None)
                except Exception as e:
                    return (t, None, e)

            _results = {}
            _done_count = 0
            _progress_every = max(50, min(500, n_tickers // 10))
            executor = ThreadPoolExecutor(max_workers=_max_workers)
            try:
                _futures = {executor.submit(_fetch_one, t): t for t in tickers}
                for _f in as_completed(_futures):
                    _t, _df, _err = _f.result()
                    _results[_t] = (_df, _err)
                    _done_count += 1
                    if _done_count % _progress_every == 0 or _done_count == n_tickers:
                        _sample = list(_results.keys())[-5:]
                        _msg = f"數據獲取：進行中 {_done_count}/{n_tickers}（例如：{', '.join(_sample)}）"
                        print(f"    {_msg}", flush=True)
                        if callable(on_fetch_progress):
                            on_fetch_progress(_msg)
            except KeyboardInterrupt:
                executor.shutdown(wait=False, cancel_futures=True)
                raise
            finally:
                executor.shutdown(wait=True)
            _first_done = False
            _used_multi_fallback = False
            from datetime import datetime as _dt, timedelta as _td
            _end_d = _dt.strptime(end_str, "%Y-%m-%d").date() if end_str else None
            _start_d = _dt.strptime(start_str, "%Y-%m-%d").date() if start_str else (_end_d - _td(days=90) if _end_d else None)
            for idx, ticker in enumerate(tickers):
                if callable(on_ticker):
                    on_ticker(ticker, idx + 1, n_tickers)
                _df, _err = _results.get(ticker, (None, None))
                if not _first_done:
                    try:
                        import json
                        _df_len = len(_df) if _df is not None and not (_df.empty if hasattr(_df, 'empty') else True) else 0
                        with open("/Users/lautinyam/stock_scanner/.cursor/debug.log", "a", encoding="utf-8") as _dbg:
                            _dbg.write(json.dumps({"hypothesisId": "H4", "message": "first_ticker_fetch_result", "data": {"ticker": ticker, "df_is_none": _df is None, "df_len": _df_len, "end_str": end_str, "start_str": start_str}, "timestamp": int(time.time() * 1000)}, ensure_ascii=False) + "\n")
                    except Exception:
                        pass
                    _first_done = True
                if _err is not None:
                    if not silent and n_tickers <= 100:
                        print(f"   ⚠ {ticker}: {_err}")
                    _df = None
                if _df is not None and not _df.empty and len(_df) >= 20:
                    market_data[ticker] = _df
                    if not silent and n_tickers <= 100:
                        print(f"   ✓ {ticker}: {len(_df)} 筆")
                else:
                    # 第一來源不足時，用多數據源補拿（Stooq/FMP 等），確保拿到準確數據
                    if _end_d is not None and _start_d is not None:
                        try:
                            import pandas as _pd
                            from utils.data_sources import get_daily_bars
                            _df2 = get_daily_bars(ticker, _start_d, _end_d, min_bars=20, merge_sources=True)
                            if _df2 is not None and not _df2.empty and len(_df2) >= 20:
                                _df2 = _df2.set_index('Date')
                                _df2.index = _pd.to_datetime(_df2.index)
                                market_data[ticker] = _df2
                                _used_multi_fallback = True
                                if not silent and n_tickers <= 100:
                                    print(f"   ✓ {ticker}: {len(_df2)} 筆（多數據源）")
                                continue
                        except Exception:
                            pass
                    if not silent and n_tickers <= 100:
                        print(f"   ⚠ {ticker}: 資料不足，跳過")
            if _used_multi_fallback:
                data_source = "Yahoo+MultiSource"
            if not market_data and not silent:
                print("   ⚠ 無有效數據，使用預設空結構")
        except ImportError:
            import yfinance as yf
            from datetime import timedelta
            from concurrent.futures import ThreadPoolExecutor, as_completed
            data_source = "yfinance"
            end_excl = None
            if end_str:
                try:
                    d = datetime.strptime(end_str, "%Y-%m-%d").date() if isinstance(end_str, str) else end_str
                    end_excl = (d + timedelta(days=1)).strftime("%Y-%m-%d")
                except Exception:
                    end_excl = None

            def _fetch_one_yf(t):
                try:
                    stock = yf.Ticker(t)
                    hist = stock.history(period="90d", end=end_excl) if end_excl else stock.history(period="90d")
                    return (t, hist, None)
                except Exception as e:
                    return (t, None, e)

            _results = {}
            _done_count = 0
            _progress_every = max(50, min(500, n_tickers // 10))
            executor = ThreadPoolExecutor(max_workers=_max_workers)
            try:
                _futures = {executor.submit(_fetch_one_yf, t): t for t in tickers}
                for _f in as_completed(_futures):
                    _t, _df, _err = _f.result()
                    _results[_t] = (_df, _err)
                    _done_count += 1
                    if _done_count % _progress_every == 0 or _done_count == n_tickers:
                        _sample = list(_results.keys())[-5:]
                        _msg = f"數據獲取：進行中 {_done_count}/{n_tickers}（例如：{', '.join(_sample)}）"
                        print(f"    {_msg}", flush=True)
                        if callable(on_fetch_progress):
                            on_fetch_progress(_msg)
            except KeyboardInterrupt:
                executor.shutdown(wait=False, cancel_futures=True)
                raise
            finally:
                executor.shutdown(wait=True)
            _end_d = datetime.strptime(end_str, "%Y-%m-%d").date() if end_str else None
            _start_d = datetime.strptime(start_str, "%Y-%m-%d").date() if start_str else (_end_d - timedelta(days=90) if _end_d else None)
            for idx, ticker in enumerate(tickers):
                if callable(on_ticker):
                    on_ticker(ticker, idx + 1, n_tickers)
                _df, _err = _results.get(ticker, (None, None))
                if _err is not None:
                    if not silent and n_tickers <= 100:
                        print(f"   ⚠ {ticker}: {_err}")
                    _df = None
                if _df is not None and not _df.empty and len(_df) >= 20:
                    market_data[ticker] = _df
                    if not silent and n_tickers <= 100:
                        print(f"   ✓ {ticker}: {len(_df)} 筆")
                elif _end_d and _start_d:
                    try:
                        import pandas as _pd
                        from utils.data_sources import get_daily_bars
                        _df2 = get_daily_bars(ticker, _start_d, _end_d, min_bars=20, merge_sources=True)
                        if _df2 is not None and not _df2.empty and len(_df2) >= 20:
                            _df2 = _df2.set_index('Date')
                            _df2.index = _pd.to_datetime(_df2.index)
                            market_data[ticker] = _df2
                            data_source = "yfinance+MultiSource"
                            if not silent and n_tickers <= 100:
                                print(f"   ✓ {ticker}: {len(_df2)} 筆（多數據源）")
                    except Exception:
                        if not silent and n_tickers <= 100:
                            print(f"   ⚠ {ticker}: 資料不足，跳過")
                else:
                    if not silent and n_tickers <= 100:
                        print(f"   ⚠ {ticker}: 資料不足，跳過")
        return market_data, data_source
    
    def start_monitoring(self):
        """
        启动即时监控
        """
        print("🔮 启动即时监控...")
        self.monitor.start(self.portfolio)
    
    def show_statistics(self):
        """显示统计信息"""
        print("\n" + "=" * 70)
        print("📊 REISHI 霊視 统计信息")
        print("=" * 70)
        
        stats = self.memory.get_statistics()
        print(f"\n总建议数: {stats['total_recommendations']}")
        print(f"已执行: {stats['executed']}")
        print(f"已完成: {stats['completed']}")
        
        insights = self.memory.get_insights()
        if insights:
            print("\n洞察:")
            for insight in insights:
                print(f"  • {insight}")


def run_backtest_v5_full_range(start_date: str, end_date: str, stock_count: int = 20, use_local_data: bool = False):
    """v5.0/v5.1 回測：逐日跑 v5.0 流程，回傳 (summary_path, trades_path)。stock_count 為每日掃描股票數量。use_local_data=True 時從本地 parquet 讀 K 線，速度快。"""
    from datetime import datetime as dt
    from core.backtest_engine import (
        BacktestEngine,
        get_trading_days,
        prev_trading_day,
        get_execution_prices_for_date,
        apply_v5_decision,
    )
    from reporting.step_report import write_daily_final_report
    from core.data_manager import read_local_market_data_for_date
    start_d = dt.strptime(start_date, "%Y-%m-%d").date()
    end_d = dt.strptime(end_date, "%Y-%m-%d").date()
    engine = BacktestEngine(config_path="config.json")
    config = engine.config
    trading_days = get_trading_days(start_d, end_d)
    if not trading_days:
        print("❌ 區間內無交易日")
        return None, None
    output_dir = f"reports/backtest_range/{start_date}_to_{end_date}"
    os.makedirs(output_dir, exist_ok=True)
    n_days = len(trading_days)
    # 預計運行時間：本地約 15–20 分/天，即時約 1.5*stock_count+90 秒/天
    est_per_day_sec = (15 * 60) if use_local_data else (stock_count * 1.5 + 90)
    est_total_sec = n_days * est_per_day_sec
    est_min = est_total_sec / 60
    est_hr = est_min / 60
    if est_hr >= 1:
        est_str = f"約 {est_hr:.1f} 小時"
    else:
        est_str = f"約 {est_min:.0f} 分鐘"
    print("\n" + "=" * 70)
    print(f"🔗 REISHI v5.3 回测（逐日 v5.0 流程）— 每日 {stock_count} 檔" + (" [本地數據]" if use_local_data else ""))
    print("=" * 70)
    print(f"📅 期間: {start_date} → {end_date}，共 {n_days} 個交易日")
    print(f"💰 初始資金: {config.initial_cash:,.0f} HKD")
    print(f"⏱ 預計運行時間：{est_str}（每日約 {est_per_day_sec/60:.1f} 分鐘）")
    print(f"📁 細項報告與當日報告: {output_dir}/daily_YYYY-MM-DD/")
    print("=" * 70)
    print("⏳ 每日會跑完整 v5.0 流程（數據+多模組+LLM），首日可能需數分鐘，請稍候…")
    print("📄 回測「完整跑完」後: backtest_summary.csv, backtest_trades.csv")
    print("📋 每一步驟會寫入: REIKAN_steps.log（含時間戳、數據來源、LLM 階段）")
    print("   （若中途 Ctrl+C 中斷，已完成的當日報告會保留）")
    print("=" * 70)
    reishi = ReishiV5()
    cash = config.initial_cash
    positions = []
    daily_records = []
    all_trades = []
    est_per_day_sec = est_total_sec / n_days if n_days else 0
    step_log_path = os.path.join(output_dir, "REIKAN_steps.log")
    step_log_file = open(step_log_path, "w", encoding="utf-8")
    step_log_file.write(f"[{datetime.now().isoformat()}] 回測開始 {start_date} ~ {end_date} 共 {n_days} 日 每日 {stock_count} 檔\n")
    step_log_file.flush()
    def _step_log(msg):
        step_log_file.write(f"[{datetime.now().isoformat()}] {msg}\n")
        step_log_file.flush()
    for i, T in enumerate(trading_days):
        try:
            print(f"   [{i+1}/{len(trading_days)}] 正在處理 {T} …", flush=True)
            if stock_count > 50:
                print(f"    ⏳ 本日將先取得新聞（{stock_count} 檔）與市場數據（並行），需數分鐘，請勿中斷…", flush=True)
            day_start = time.time()
            prev_d = prev_trading_day(T)
            # Always use 90-day lookback window from prev_d (never collapse to start_d)
            backtest_start_eff = prev_d - timedelta(days=90)
            # #region agent log
            if i == 0:
                try:
                    import json
                    with open("/Users/lautinyam/stock_scanner/.cursor/debug.log", "a", encoding="utf-8") as _dbg:
                        _dbg.write(json.dumps({"hypothesisId": "H4", "message": "first_day_dates", "data": {"T": T.strftime("%Y-%m-%d"), "prev_d": prev_d.strftime("%Y-%m-%d"), "backtest_start_eff": backtest_start_eff.strftime("%Y-%m-%d") if hasattr(backtest_start_eff, "strftime") else str(backtest_start_eff)}, "timestamp": int(time.time() * 1000)}, ensure_ascii=False) + "\n")
                except Exception:
                    pass
            # #endregion
            reishi.portfolio = PortfolioState(
                cash=cash,
                positions=positions,
                total_value=cash + sum((p.get("shares") or p.get("quantity", 0)) * (p.get("current_price") or p.get("entry_price") or p.get("buy_price", 0)) for p in positions),
            )
            flow_steps = getattr(ReishiV5, "FLOW_STEPS", ("數據獲取與驗證", "圖表型態識別", "因果推理", "情緒分析", "Multi-Agent 協作分析", "霊視記憶參考", "決策引擎"))
            daily_report_dir = os.path.join(output_dir, f"daily_{T.strftime('%Y-%m-%d')}")
            from reporting.flow_logger import FlowLogger
            flow_logger = FlowLogger(flush_each=True)
            def _on_progress(step_i, total, name, pct):
                flow_label = f"[Flow 步驟 {step_i}] {flow_steps[step_i - 1]}" if 1 <= step_i <= len(flow_steps) else ""
                elapsed = time.time() - day_start
                remaining_days = len(trading_days) - i - 1
                avg_per_day = (elapsed / step_i * 7) if step_i > 0 else est_per_day_sec
                overall_remaining_sec = remaining_days * avg_per_day
                overall_str = f"，回測整體剩餘約 {overall_remaining_sec/60:.0f} 分鐘（未完成 {remaining_days} 日）" if remaining_days > 0 else ""
                if pct >= 100:
                    remaining = (elapsed / step_i) * (total - step_i) if step_i > 0 else 0
                    print(f"    細項 {step_i}/{total} {name} {flow_label} {pct}% (已用 {elapsed:.0f} 秒，本日預計剩餘約 {remaining:.0f} 秒{overall_str})", flush=True)
                else:
                    msg = f"    細項 {step_i}/{total} {name} {flow_label} {pct}% (已用 {elapsed:.0f} 秒，請稍候…)"
                    if step_i == 7 and pct == 0:
                        msg += "\n    ※ 約需 30～120 秒；若超過 2 分鐘無新輸出可能為 API/網路問題"
                    else:
                        completed = max(1, step_i - 1)
                        remaining = (elapsed / completed) * (total - step_i + 1) if completed > 0 else 0
                        msg += f"，本日預計剩餘約 {remaining:.0f} 秒"
                    msg += overall_str
                    print(msg, flush=True)
            def _on_ticker(ticker, idx, total):
                print(f"    [Flow 步驟 1] 數據獲取: 正在取得 {ticker} ({idx}/{total}) …", flush=True)
            def _on_step_activity(step_i, message):
                flow_name = flow_steps[step_i - 1] if 1 <= step_i <= len(flow_steps) else ""
                print(f"    細項 {step_i}/7 {flow_name}: {message}", flush=True)
            def _on_llm_progress(phase, total, message, provider=None):
                if provider:
                    print(f"    LLM：{provider} 完成「{message}」（第 {phase}/{total} 階段）", flush=True)
                else:
                    print(f"    LLM：第 {phase}/{total} 階段「{message}」進行中…", flush=True)
            try:
                _step_log(f"日 {i+1}/{n_days} {T} 開始")
                pre_fetched = None
                if use_local_data:
                    tickers_for_day = reishi._get_scan_tickers(cap=stock_count)
                    pre_fetched = read_local_market_data_for_date(prev_d, tickers_for_day, lookback_days=90)
                    if not pre_fetched:
                        print(f"   ⚠ 本地無 {prev_d} 的 K 線數據，請先執行「數據管理」下載該區間")
                        decision, all_analyses = None, None
                    else:
                        decision, all_analyses = reishi.run_daily_for_backtest(
                            prev_d, backtest_start_eff, stock_count=stock_count, silent=True,
                            on_progress=_on_progress, on_llm_progress=_on_llm_progress,
                            on_ticker=None if flow_logger else _on_ticker,
                            on_step_activity=None if flow_logger else _on_step_activity,
                            flow_logger=flow_logger,
                            report_dir=daily_report_dir,
                            step_log=_step_log,
                            day_index=i, total_days=n_days, day_start_ts=day_start, est_per_day_sec=est_per_day_sec,
                            pre_fetched_market_data=pre_fetched,
                        )
                else:
                    decision, all_analyses = reishi.run_daily_for_backtest(
                        prev_d, backtest_start_eff, stock_count=stock_count, silent=True,
                        on_progress=_on_progress, on_llm_progress=_on_llm_progress,
                        on_ticker=None if flow_logger else _on_ticker,
                        on_step_activity=None if flow_logger else _on_step_activity,
                        flow_logger=flow_logger,
                        report_dir=daily_report_dir,
                        step_log=_step_log,
                        day_index=i, total_days=n_days, day_start_ts=day_start, est_per_day_sec=est_per_day_sec,
                    )
            except Exception as e:
                print(f"   ⚠ 日 {T} 決策錯誤: {e}")
                decision = None
                all_analyses = None
            tickers_needed = list({p.get("ticker") or p.get("symbol") for p in positions if p.get("ticker") or p.get("symbol")})
            if decision and getattr(decision, "actions", None):
                for a in decision.actions:
                    t = getattr(a, "ticker", None) or (a.get("ticker") if isinstance(a, dict) else None)
                    if t:
                        tickers_needed.append(t)
            execution_prices = get_execution_prices_for_date(tickers_needed or ["AAPL"], T)
            # #region agent log
            try:
                import json
                _n_exec = len(execution_prices)
                _exec_sample = list(execution_prices.items())[:3]
                with open("/Users/lautinyam/stock_scanner/.cursor/debug.log", "a", encoding="utf-8") as _dbg:
                    _dbg.write(json.dumps({"hypothesisId": "H7", "message": "execution_prices_fetched", "data": {"date": T.strftime("%Y-%m-%d"), "n_prices": _n_exec, "tickers_needed": tickers_needed[:5], "exec_sample": _exec_sample}, "timestamp": int(time.time() * 1000)}, ensure_ascii=False) + "\n")
            except Exception:
                pass
            # #endregion
            trades = []
            if decision:
                cash, positions, trades = apply_v5_decision(
                    cash, positions, decision, execution_prices,
                    T.strftime("%Y-%m-%d"), config,
                )
                all_trades.extend(trades)
                # 每日決策摘要：讓使用者看到 LLM 回了什麼、為何沒有買賣
                acts = getattr(decision, "actions", []) or []
                non_hold = [a for a in acts if (getattr(a, "action", "HOLD") or (a.get("action") if isinstance(a, dict) else "HOLD")) not in ("HOLD", "", None)]
                if non_hold:
                    parts = []
                    for a in non_hold[:5]:
                        tk = getattr(a, "ticker", "") or (a.get("ticker") if isinstance(a, dict) else "")
                        ac = (getattr(a, "action", "HOLD") or (a.get("action") if isinstance(a, dict) else "HOLD")).upper()
                        pct = getattr(a, "position_size_pct", None) or (a.get("position_size_pct") if isinstance(a, dict) else None)
                        parts.append(f"{ac} {tk}" + (f" {pct}%" if pct is not None else ""))
                    print(f"    本日決策: {len(non_hold)} 筆操作 — {', '.join(parts)}", flush=True)
                else:
                    print(f"    本日決策: 無買賣（LLM 回傳 {len(acts)} 筆皆 HOLD 或 0 筆操作）", flush=True)
                if non_hold and not trades:
                    print(f"    （LLM 有建議買賣但未執行：可能缺該標的執行價或現金/持倉不足）", flush=True)
                if trades:
                    for tr in trades:
                        print(f"    執行: {tr.action.upper()} {tr.ticker} {tr.quantity} 股 @ {tr.price}", flush=True)
            else:
                print(f"    本日決策: 跳過（決策錯誤或無決策）", flush=True)
            pos_value = sum((p.get("shares") or p.get("quantity", 0)) * execution_prices.get(p.get("ticker") or p.get("symbol"), p.get("entry_price") or 0) for p in positions)
            portfolio_value = cash + pos_value
            return_pct = (portfolio_value - config.initial_cash) / config.initial_cash * 100
            # 當日最終報告：分析結果 + 當日行動
            try:
                analysis_summary = all_analyses.summary() if (all_analyses and hasattr(all_analyses, "summary")) else ""
                acts = getattr(decision, "actions", []) or [] if decision else []
                write_daily_final_report(
                    output_dir,
                    T.strftime("%Y-%m-%d"),
                    analysis_summary,
                    acts,
                    trades if decision else [],
                    portfolio_value=portfolio_value,
                    return_pct=return_pct,
                )
            except Exception as _e:
                pass
            daily_records.append({
                "date": T.strftime("%Y-%m-%d"),
                "portfolio_value": round(portfolio_value, 2),
                "cash": round(cash, 2),
                "positions_count": len(positions),
                "return_pct": round(return_pct, 2),
            })
            if (i + 1) % 5 == 0 or i == 0:
                print(f"   [{i+1}/{len(trading_days)}] {T} 組合 {portfolio_value:.0f} 報酬 {return_pct:+.2f}%", flush=True)
        except KeyboardInterrupt:
            try:
                _step_log("回測中斷 (Ctrl+C)")
                step_log_file.close()
            except Exception:
                pass
            output_dir_partial = f"reports/backtest_range/{start_date}_to_{end_date}_interrupted_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            engine.daily_records = daily_records
            engine.trades = all_trades
            summary_path, trades_path = engine.save_results(output_dir_partial)
            print("\n⚠ 已中斷 (Ctrl+C)，部分報告已寫入: {} , {}".format(summary_path or "", trades_path or ""), flush=True)
            raise
    try:
        _step_log("回測完成")
        step_log_file.close()
    except Exception:
        pass
    output_dir = f"reports/backtest_range/{start_date}_to_{end_date}"
    engine.daily_records = daily_records
    engine.trades = all_trades
    summary_path, trades_path = engine.save_results(output_dir)
    return summary_path, trades_path


def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(description='REISHI 霊視 v5.3')
    parser.add_argument('--daily', action='store_true', help='运行每日分析')
    parser.add_argument('--monitor', action='store_true', help='启动即时监控')
    parser.add_argument('--stats', action='store_true', help='显示统计信息')
    parser.add_argument('--backtest', nargs='*', metavar=('START_DATE', 'END_DATE'),
                        help='运行回测（逐日 v5.0 流程）。不传日期则用默认区间（约最近 90 天）；传两个日期则用 YYYY-MM-DD YYYY-MM-DD')
    parser.add_argument('--stock-count', type=int, default=20, help='每日扫描股票数量（预设 20，输入 0 或超大数值则扫描全美股）')
    
    args = parser.parse_args()
    
    # 回测模式（命令列）
    if args.backtest is not None:
        # 讀取美股總數
        us_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "us_universe.csv")
        total_us_stocks = 7055
        if os.path.isfile(us_path):
            try:
                with open(us_path, "r", encoding="utf-8") as f:
                    total_us_stocks = sum(1 for _ in f) - 1
            except Exception:
                pass
        stock_count = args.stock_count if args.stock_count > 0 else total_us_stocks
        if stock_count >= total_us_stocks:
            stock_count = total_us_stocks
            print(f"📌 掃描全美股（{total_us_stocks} 檔）")
        stock_count = max(1, stock_count)
        if len(args.backtest) == 2:
            start_date, end_date = args.backtest
        else:
            # 默认：最近约 90 天
            from core.backtest_engine import get_trading_days
            end_d = datetime.now().date()
            start_d = end_d - timedelta(days=90)
            trading = get_trading_days(start_d, end_d)
            if not trading:
                start_date, end_date = str(start_d), str(end_d)
            else:
                start_date = trading[0].strftime("%Y-%m-%d")
                end_date = trading[-1].strftime("%Y-%m-%d")
            print(f"回测默认区间: {start_date} ~ {end_date}")
        summary_path, trades_path = run_backtest_v5_full_range(start_date, end_date, stock_count=stock_count)
        if summary_path:
            print("\n" + "=" * 70)
            print("✅ 回测完成")
            print(f"📄 摘要: {summary_path}")
            print(f"📄 交易: {trades_path}")
            print("=" * 70)
        return
    
    # 正常模式（有 --daily / --monitor / --stats 時直接執行）
    if args.daily or args.monitor or args.stats:
        reishi = ReishiV5()
        if args.daily:
            reishi.run_daily()
        elif args.monitor:
            reishi.start_monitoring()
        elif args.stats:
            reishi.show_statistics()
        return

    # 互動模式：v5.1 主選單
    global _interactive_run_id
    _interactive_run_id = str(int(time.time() * 1000))
    print(BANNER_V5)
    print("\n請選擇運行模式：")
    print("  [1] 正常 mode — 今日決策")
    print("  [2] 回測 mode — 歷史回放")
    print("  [3] 數據管理 — 下載／檢查歷史數據")
    print("  [0] 顯示命令列參數說明")
    choice = input("\n請輸入選項 [1/2/3/0]: ").strip()
    # #region agent log
    _debug_log({"location": "main_v5.py:menu", "message": "main_menu_choice", "data": {"choice": choice}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session", "hypothesisId": "H1", "runId": _interactive_run_id})
    # #endregion

    if choice == "1":
        run_dir = _create_run_dir_v5()
        log_file, original_stdout = _start_log_v5(run_dir)
        try:
            print(f"\n📁 本次報告目錄: {run_dir}")
            reishi = ReishiV5()
            stock_count = len(reishi._get_scan_tickers())
            # 預計運行時間：依實際掃描名單數量估算（每檔約 1.5 秒取數 + LLM 等）
            est_sec = stock_count * 1.5 + 90
            if est_sec >= 3600:
                est_str = f"約 {est_sec/3600:.1f} 小時"
            else:
                est_str = f"約 {est_sec/60:.0f} 分鐘"
            print(f"⏱ 預計運行時間：{est_str}（{stock_count} 檔股票）")
            print("🔮 啟動霊視，洞察市場...\n")
            reishi.run_daily()
        finally:
            _stop_log_v5(log_file, original_stdout)
        _run_summary("choice=1 daily_done")

    elif choice == "2":
        print("\n📅 回測模式")
        print("  [A] 本地數據回測（推薦）— 使用預下載數據，速度快")
        print("  [B] 即時數據回測 — 每日即時拉取，限 1–7 天，用於驗證程式運行")
        sub = input("請選擇 [A/B]: ").strip().upper()
        # #region agent log
        _debug_log({"location": "main_v5.py:backtest_sub", "message": "backtest_sub_choice", "data": {"sub": sub, "valid": sub in ("A", "B")}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session", "hypothesisId": "H1", "runId": _interactive_run_id})
        # #endregion
        if sub not in ("A", "B"):
            _run_summary(f"choice=2 sub=invalid value={sub!r}")
            print("❌ 請輸入 A 或 B")
            return
        # 讀取美股總數
        us_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "us_universe.csv")
        total_us_stocks = 7055
        if os.path.isfile(us_path):
            try:
                with open(us_path, "r", encoding="utf-8-sig") as f:
                    total_us_stocks = sum(1 for _ in f) - 1
            except Exception:
                pass

        def _norm_date(s):
            s = s.strip().replace(" ", "")
            if len(s) == 8 and s.isdigit():
                return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
            return s

        if sub == "A":
            from core.data_manager import check_data_sufficient, run_data_management_ui
            print("\n  目前 2015–2025 的回測數據最完整；請先於「數據管理」下載所需區間。")
            start_str = input("  請輸入開始日期（YYYY-MM-DD 或 YYYYMMDD）：").strip()
            end_str = input("  請輸入結束日期（YYYY-MM-DD 或 YYYYMMDD）：").strip()
            if not start_str or not end_str:
                _run_summary("choice=2 sub=A error=missing_dates")
                print("❌ 未輸入日期")
                return
            try:
                start_dt = datetime.strptime(_norm_date(start_str), "%Y-%m-%d").date()
                end_dt = datetime.strptime(_norm_date(end_str), "%Y-%m-%d").date()
            except ValueError:
                _run_summary("choice=2 sub=A error=invalid_date_format")
                print("❌ 日期格式錯誤，請用 YYYY-MM-DD 或 YYYYMMDD")
                return
            if start_dt >= end_dt:
                _run_summary("choice=2 sub=A error=end_before_start")
                print("❌ 結束日期必須晚於開始日期")
                return
            sufficient, msg, relevant = check_data_sufficient(start_dt, end_dt)
            # #region agent log
            _debug_log({"location": "main_v5.py:check_sufficient", "message": "check_data_sufficient_result", "data": {"sufficient": sufficient, "msg": msg, "start_dt": str(start_dt), "end_dt": str(end_dt), "relevant_years": [r.year for r in relevant], "statuses": [r.status for r in relevant]}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session", "hypothesisId": "H2", "runId": _interactive_run_id})
            # #endregion
            print(f"  {msg}")
            if not sufficient:
                print("  [R] 修復後再回測  [P] 用現有數據繼續  [C] 換區間")
                action = input("請選擇 [R/P/C]: ").strip().upper()
                if action == "C":
                    _run_summary(f"choice=2 sub=A action=C sufficient=false")
                    return
                if action == "R":
                    _run_summary("choice=2 sub=A action=R opening_data_management")
                    run_data_management_ui()
                    _run_summary("choice=2 sub=A action=R data_management_done")
                    return
                if action != "P":
                    print("將使用現有數據繼續（可能缺部分標的）")
            stock_count_str = input(f"  每日掃描股票數量（預設 20，all=全美股 {total_us_stocks}）：").strip()
            stock_count = total_us_stocks if (stock_count_str.lower() == "all" or not stock_count_str) else (int(stock_count_str) if stock_count_str.isdigit() else 20)
            stock_count = max(1, min(stock_count, total_us_stocks))
            from core.backtest_engine import get_trading_days
            trading = get_trading_days(start_dt, end_dt)
            n_days = len(trading)
            est_per_day_sec = 15 * 60  # 約 15 分/天
            est_total_sec = n_days * est_per_day_sec
            est_hr = est_total_sec / 3600
            est_str = f"約 {est_hr:.1f} 小時" if est_hr >= 1 else f"約 {est_total_sec/60:.0f} 分鐘"
            print(f"\n🔮 啟動霊視本地回測（{start_dt} ~ {end_dt}）")
            print(f"   📊 每日掃描 {stock_count} 檔，共 {n_days} 個交易日")
            print(f"   ⏱ 預計運行時間：{est_str}（每日約 15–20 分鐘）\n")
            backtest_run_dir = os.path.join("reports", "backtest_range", f"{start_dt.strftime('%Y-%m-%d')}_to_{end_dt.strftime('%Y-%m-%d')}")
            os.makedirs(backtest_run_dir, exist_ok=True)
            log_file_bt, original_stdout_bt = _start_log_v5(backtest_run_dir, log_name="REIKAN_run.log")
            # #region agent log
            _debug_log({"location": "main_v5.py:before_local_backtest", "message": "about_to_run_local_backtest", "data": {"start": start_dt.strftime("%Y-%m-%d"), "end": end_dt.strftime("%Y-%m-%d"), "stock_count": stock_count}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session", "hypothesisId": "H3", "runId": _interactive_run_id})
            # #endregion
            _run_summary(f"choice=2 sub=A backtest_started start={start_dt} end={end_dt} stock_count={stock_count} local=true")
            try:
                summary_path, trades_path = run_backtest_v5_full_range(
                    start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"), stock_count=stock_count, use_local_data=True
                )
            finally:
                _stop_log_v5(log_file_bt, original_stdout_bt)
            if summary_path:
                _run_summary(f"choice=2 sub=A backtest_ok summary={summary_path} trades={trades_path}")
                print("\n" + "=" * 70)
                print("✅ 回測完成")
                print(f"📄 摘要: {summary_path}")
                print(f"📄 交易: {trades_path}")
                print("=" * 70)
            else:
                _run_summary("choice=2 sub=A backtest_done no_summary")
        return
        # [B] 即時數據回測
        start_str = input("  請輸入開始日期（YYYY-MM-DD 或 YYYYMMDD）：").strip().replace(" ", "")
        end_str = input("  請輸入結束日期（YYYY-MM-DD 或 YYYYMMDD）：").strip().replace(" ", "")
        stock_count_str = input(f"  每日掃描股票數量（預設 20，all=全美股 {total_us_stocks}）：").strip()
        stock_count = total_us_stocks if (stock_count_str.lower() == "all" or not stock_count_str) else (int(stock_count_str) if stock_count_str.isdigit() else 20)
        stock_count = max(1, min(stock_count, total_us_stocks))
        try:
            from core.backtest_engine import get_trading_days
            start_dt = datetime.strptime(_norm_date(start_str), "%Y-%m-%d").date()
            end_dt = datetime.strptime(_norm_date(end_str), "%Y-%m-%d").date()
            if start_dt >= end_dt:
                print("❌ 結束日期必須晚於開始日期")
                return
            trading = get_trading_days(start_dt, end_dt)
            n_days = len(trading)
            if n_days > 7:
                print(f"⚠ 即時回測建議不超過 7 天（目前 {n_days} 天）。建議改用 [A] 本地數據回測。")
                if input("仍要繼續？[y/N]: ").strip().lower() != "y":
                    return
            est_per_day_sec = stock_count * 1.5 + 90
            est_total_sec = n_days * est_per_day_sec
            est_min = est_total_sec / 60
            est_hr = est_min / 60
            est_str = f"約 {est_hr:.1f} 小時" if est_hr >= 1 else f"約 {est_min:.0f} 分鐘"
            print(f"\n🔮 啟動霊視即時回測（{start_dt} ~ {end_dt}）")
            print(f"   📊 每日掃描 {stock_count} 檔，共 {n_days} 個交易日")
            print(f"   ⏱ 預計運行時間：{est_str}（每日約 {est_per_day_sec/60:.1f} 分鐘）\n")
            backtest_run_dir = os.path.join("reports", "backtest_range", f"{start_dt.strftime('%Y-%m-%d')}_to_{end_dt.strftime('%Y-%m-%d')}")
            os.makedirs(backtest_run_dir, exist_ok=True)
            log_file_bt, original_stdout_bt = _start_log_v5(backtest_run_dir, log_name="REIKAN_run.log")
            try:
                summary_path, trades_path = run_backtest_v5_full_range(
                    start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"), stock_count=stock_count, use_local_data=False
                )
            finally:
                _stop_log_v5(log_file_bt, original_stdout_bt)
            if summary_path:
                _run_summary(f"choice=2 sub=B backtest_ok summary={summary_path} trades={trades_path}")
                print("\n" + "=" * 70)
                print("✅ 回測完成")
                print(f"📄 摘要: {summary_path}")
                print(f"📄 交易: {trades_path}")
                print("=" * 70)
            else:
                _run_summary("choice=2 sub=B backtest_done no_summary")
        except ValueError:
            _run_summary("choice=2 sub=B error=invalid_date_format")
            print("❌ 日期格式錯誤，請用 YYYY-MM-DD 或 YYYYMMDD")
        except Exception as e:
            _run_summary(f"choice=2 sub=B ERROR {e!r}")
            print(f"❌ 回測錯誤: {e}")
            import traceback
            traceback.print_exc()

    elif choice == "3":
        _run_summary("choice=3 data_management_enter")
        try:
            from core.data_manager import run_data_management_ui
            run_data_management_ui()
            _run_summary("choice=3 data_management_done")
        except Exception as e:
            _run_summary(f"choice=3 ERROR {type(e).__name__}: {e!r}")
            raise

    elif choice == "0":
        _run_summary("choice=0 help")
        print("\n" + "=" * 50)
        print("📋 命令列參數說明")
        print("=" * 50)
        print("  python main_v5.py --daily    # 每日分析")
        print("  python main_v5.py --monitor  # 即時監控")
        print("  python main_v5.py --stats    # 統計資訊")
        print("  python main_v5.py --backtest [START END] [--stock-count N]  # 回測")
        print("    不傳日期則預設約 90 天")
        print("    --stock-count N  設定每日掃描股票數量（預設 20，輸入 0 或超大值則掃描全美股約 7000 檔）")
        print("=" * 50)
    else:
        _run_summary(f"choice=invalid value={choice!r}")
        print("❌ 無效選項，請重新執行並選擇 1/2/3/0")


# ---------------------------------------------------------------------------
# v4.3 風格：美學 banner、run 目錄、tee log（與 main.py 一致）
# ---------------------------------------------------------------------------
# ASCII block font: R E I S H I 5 . 3 (each char 5 wide, 1 space between)
BANNER_V5 = """
================================================================================
                                                                                
   ###   #####   ###   ####  #   #   ###   #####         ####                  
  #   #  #       #     #     #   #    #   #         #      #   #               
  #   #  #       #     #  ###   #   #    #   ####      ####
  ####   ###     #     ###   #####    #   ####   #   ####                
  #  #   #       #     #  ####  #   #    #   #### #   #  ####                
  #   #  #       #     #  #    #   #    #   #   #        #   #               
  #   #  #####   ###   ####  #   #   ###   ####     ###   ####                
                                                                                
                          霊  視  ·  REISHI  5.3                               
                ---  AI 市場洞察 · 五層防護 · 多智能體  ---                      
                                                                                
================================================================================
"""


def _create_run_dir_v5():
    """建立本次運行的資料夾：reports/YYYY-MM-DD_HHMMSS"""
    run_dir = os.path.join("reports", datetime.now().strftime("%Y-%m-%d_%H%M%S"))
    os.makedirs(run_dir, exist_ok=True)
    return run_dir


class _Tee:
    """同時輸出到終端與 log 檔"""
    def __init__(self, stdout, log_file):
        self._stdout = stdout
        self._log_file = log_file

    def write(self, data):
        self._stdout.write(data)
        if self._log_file:
            self._log_file.write(data)
            self._log_file.flush()

    def flush(self):
        self._stdout.flush()
        if self._log_file:
            self._log_file.flush()


def _start_log_v5(run_dir, log_name="REIKAN_run.log"):
    """開始將 stdout 同時寫入 run_dir/log_name，並寫入 banner"""
    log_path = os.path.join(run_dir, log_name)
    log_file = open(log_path, "w", encoding="utf-8")
    log_file.write(BANNER_V5)
    log_file.flush()
    original_stdout = sys.stdout
    sys.stdout = _Tee(original_stdout, log_file)
    return log_file, original_stdout


def _stop_log_v5(log_file, original_stdout):
    """還原 stdout 並關閉 log 檔"""
    if log_file and original_stdout is not None:
        sys.stdout = original_stdout
        log_file.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ 已中斷 (Ctrl+C)", flush=True)
        sys.exit(130)
