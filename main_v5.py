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
        print("🔮 REISHI 霊視 v5.0 MVP")
        print("=" * 70)
        print("初始化系统...")
        
        # 初始化所有模块
        self.data_validator = DataValidator()
        self.anti_hallucination = AntiHallucination()
        self.pattern_recognition = PatternRecognition()
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
        print("🔮 REISHI 霊視 v5.0 - 每日分析")
        print("=" * 70)
        flow_logger = FlowLogger(flush_each=True)
        try:
            tickers_to_fetch = self._get_scan_tickers()
            # 即時新聞：Finnhub 公司新聞（輸入層用）
            from utils.news_fetcher import fetch_news_for_tickers, to_news_objects
            to_date = datetime.now().strftime("%Y-%m-%d")
            from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            all_news_raw, news_by_ticker_raw = fetch_news_for_tickers(tickers_to_fetch, from_date, to_date)
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
            # 輸入層：你的狀態 → 市場數據 → 即時新聞 → 霊視記憶
            your_state = f"現金 {self.portfolio.cash:,.0f}、持倉 {len(self.portfolio.positions)} 檔、總值 {self.portfolio.total_value:,.0f}"
            market_data_desc = f"掃描標的 {len(tickers_to_fetch)} 檔（{', '.join(tickers_to_fetch[:8])}{' ...' if len(tickers_to_fetch) > 8 else ''}）"
            try:
                mem_stats = self.memory.get_statistics()
                memory_desc = f"已載入，歷史建議 {mem_stats.get('total_recommendations', 0)} 筆、已執行 {mem_stats.get('executed', 0)}、已完成 {mem_stats.get('completed', 0)}"
            except Exception:
                memory_desc = "已載入"
            flow_logger.log_input_layer(your_state, market_data_desc, news_desc, memory_desc, as_of_date="", mode="每日分析")
            # 1. 获取并验证数据 — 第一層防護：數據驗證
            print("\n[1/8] 数据获取与验证...")
            market_data, data_source = self._fetch_and_validate_data(on_ticker=lambda t, i, n: flow_logger.log_layer1_fetch(t, i, n))
            flow_logger.log_layer1_start(data_source)
            tickers = list(market_data.keys()) or tickers_to_fetch
            flow_logger.log_layer1_result(len(market_data), tickers, data_source=data_source)
            if not market_data:
                print("   ⚠ 無市場數據，分析將僅有架構輸出")
            # 五大 AI 方向分析層
            flow_logger.log_ai_layer_start()
            # 2. 图表型态识别
            print("\n[2/8] 图表型态识别...")
            flow_logger.log_ai_2_start(len(tickers))
            pattern_analysis = self.pattern_recognition.scan_all(tickers, market_data, on_ticker=lambda t, i, n: flow_logger.log_ai_2_fetch(t, i, n))
            flow_logger.log_ai_2_result(len(pattern_analysis), [getattr(c, "ticker", "") for c in pattern_analysis] if pattern_analysis else None)
            # 3. 因果推理（傳入即時新聞）
            print("\n[3/8] 因果推理...")
            flow_logger.log_ai_3_start()
            causal_analysis = self.causal_reasoning.analyze_all(news=all_news_for_causal, portfolio=self.portfolio.positions)
            flow_logger.log_ai_3_result()
            # 4. 情绪分析（傳入即時新聞 by ticker）
            print("\n[4/8] 情绪分析...")
            flow_logger.log_ai_4_start(len(tickers))
            sentiment_analysis = self.sentiment_analyzer.analyze_batch(tickers, on_ticker=lambda t, i, n: flow_logger.log_ai_4_fetch(t, i, n), news_by_ticker=news_by_ticker_for_sentiment)
            flow_logger.log_ai_4_result()
            # 5. Multi-Agent 分析
            print("\n[5/8] Multi-Agent 协作分析...")
            flow_logger.log_ai_5_start(len(pattern_analysis))
            multi_agent_analysis = self.multi_agent.analyze_all(candidates=pattern_analysis, data=market_data)
            flow_logger.log_ai_5_result()
            # 6. 霊視记忆参考
            print("\n[6/8] 霊視记忆参考...")
            flow_logger.log_ai_6_start()
            memory_insights = self.memory.get_insights_for_candidates(pattern_analysis)
            n_insights = len(memory_insights.get("insights", [])) if isinstance(memory_insights, dict) else 0
            flow_logger.log_ai_6_result(n_insights)
            # 7. 决策引擎 — 第二層防護：LLM 防幻覺
            print("\n[7/8] 决策引擎...")
            flow_logger.log_layer2_start()
            all_analyses = AllAnalyses(
                pattern=pattern_analysis,
                causal=causal_analysis,
                sentiment=sentiment_analysis,
                multi_agent=multi_agent_analysis,
                memory=memory_insights
            )
            decision = self.decision_engine.decide(
                state=self.portfolio,
                analyses=all_analyses,
                on_llm_progress=lambda phase, total, msg, provider=None: flow_logger.log_layer2_llm_phase(phase, total, msg, provider)
            )
            acts = getattr(decision, "actions", []) or []
            summary = ", ".join([f"{getattr(a, 'action', '')} {getattr(a, 'ticker', '')}" for a in acts[:3]]) if acts else "無操作"
            flow_logger.log_layer2_result(len(acts), summary)
            # 8. 验证 + 审计
            print("\n[8/8] 最终验证与审计...")
            flow_logger.log_validation_start()
            validation = self.output_validator.validate_decision(decision, all_analyses)
            flow_logger.log_audit_start()
            audit = self.final_auditor.audit(decision, all_analyses)
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

    def run_daily_for_backtest(self, as_of_date, backtest_start=None, quick: bool = False, full_universe: bool = False, silent: bool = True, on_progress=None, on_llm_progress=None, on_ticker=None, on_step_activity=None, flow_logger=None, report_dir=None):
        """
        為回測跑單日 v5.0 流程：數據僅到 as_of_date（無偷看），回傳 (decision, all_analyses)。
        flow_logger: 可選 FlowLogger，log 依流程圖一層層輸出（輸入層→第一層防護→五大 AI→第二層防護→結果）。
        on_step_activity / on_ticker 仍會呼叫（若未提供 flow_logger 則靠其輸出）。
        report_dir 有值時會寫入細項報告 step_01..step_07。
        """
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
            if flow_logger:
                flow_logger.log_layer1_fetch(t, i, n)
            if callable(on_ticker):
                on_ticker(t, i, n)
        def _on_llm_wrap(phase, total, message, provider=None):
            if flow_logger:
                flow_logger.log_layer2_llm_phase(phase, total, message, provider)
            if callable(on_llm_progress):
                on_llm_progress(phase, total, message, provider)

        start_d = (backtest_start if backtest_start else (as_of_date - timedelta(days=90)) if hasattr(as_of_date, "day") else None)
        end_str = as_of_date.strftime("%Y-%m-%d") if hasattr(as_of_date, "strftime") else as_of_date
        start_str = start_d.strftime("%Y-%m-%d") if start_d and hasattr(start_d, "strftime") else None
        tickers_to_fetch = self._get_scan_tickers(quick=quick, full_universe=full_universe)
        # 即時新聞：Finnhub（回測時用 as_of_date 區間，不偷看未來）
        from utils.news_fetcher import fetch_news_for_tickers, to_news_objects
        to_date_news = end_str
        from_date_news = (as_of_date - timedelta(days=7)).strftime("%Y-%m-%d") if hasattr(as_of_date, "strftime") else to_date_news
        all_news_raw, news_by_ticker_raw = fetch_news_for_tickers(tickers_to_fetch, from_date_news, to_date_news)
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
            # 輸入層：你的狀態 → 市場數據 → 即時新聞 → 霊視記憶
            your_state = f"現金 {self.portfolio.cash:,.0f}、持倉 {len(self.portfolio.positions)} 檔、總值 {self.portfolio.total_value:,.0f}"
            market_data_desc = f"掃描標的 {len(tickers_to_fetch)} 檔（{', '.join(tickers_to_fetch[:8])}{' ...' if len(tickers_to_fetch) > 8 else ''}）"
            try:
                mem_stats = self.memory.get_statistics()
                memory_desc = f"已載入，歷史建議 {mem_stats.get('total_recommendations', 0)} 筆、已執行 {mem_stats.get('executed', 0)}、已完成 {mem_stats.get('completed', 0)}"
            except Exception:
                memory_desc = "已載入"
            flow_logger.log_input_layer(your_state, market_data_desc, news_desc, memory_desc, as_of_date=end_str, mode="回測（數據截至當日）")
        if not silent:
            print(f"   [回測日] 數據截至 {end_str}")
        # 細項 1：取數 — 第一層防護：數據驗證
        _prog(1, "取數", 0)
        _activity(1, "開始從數據源拉取歷史 K 線…")
        market_data, data_source = self._fetch_and_validate_data(end_date=as_of_date, start_date=start_d, quick=quick, full_universe=full_universe, silent=silent, on_ticker=_on_ticker_wrap)
        if flow_logger:
            flow_logger.log_layer1_start(data_source)
            flow_logger.log_layer1_result(len(market_data), list(market_data.keys()), data_source=data_source)
        _activity(1, f"取數完成，共 {len(market_data)} 檔有效數據")
        _prog(1, "取數", 100)
        if report_dir:
            write_step_report(report_dir, 1, flow_steps[0], short_names[0], data_source=data_source)
        tickers = list(market_data.keys()) or tickers_to_fetch
        # 五大 AI 方向分析層
        if flow_logger:
            flow_logger.log_ai_layer_start()
        # 細項 2：圖表型態識別
        _prog(2, "圖形掃描", 0)
        _activity(2, f"開始掃描 {len(tickers)} 檔圖表型態（突破、VCP 等）…")
        if flow_logger:
            flow_logger.log_ai_2_start(len(tickers))
        pattern_analysis = self.pattern_recognition.scan_all(
            tickers, market_data,
            on_ticker=lambda t, i, n: (flow_logger.log_ai_2_fetch(t, i, n) if flow_logger else None, _activity(2, f"正在掃描 {t} ({i}/{n}) …") if callable(on_step_activity) else None)
        )
        if flow_logger:
            flow_logger.log_ai_2_result(len(pattern_analysis), [getattr(c, "ticker", "") for c in pattern_analysis] if pattern_analysis else None)
        _activity(2, f"圖形掃描完成，候選數 {len(pattern_analysis)}")
        _prog(2, "圖形掃描", 100)
        if report_dir:
            write_step_report(report_dir, 2, flow_steps[1], short_names[1])
        # 細項 3：因果推理（傳入即時新聞）
        _prog(3, "因果分析", 0)
        _activity(3, "因果推理：分析新聞影響與持倉風險…")
        if flow_logger:
            flow_logger.log_ai_3_start()
        causal_analysis = self.causal_reasoning.analyze_all(news=all_news_for_causal, portfolio=self.portfolio.positions)
        if flow_logger:
            flow_logger.log_ai_3_result()
        _activity(3, "因果分析完成")
        _prog(3, "因果分析", 100)
        if report_dir:
            write_step_report(report_dir, 3, flow_steps[2], short_names[2])
        # 細項 4：情緒分析（傳入即時新聞 by ticker）
        _prog(4, "情緒分析", 0)
        _activity(4, f"開始對 {len(tickers)} 檔做情緒分析…")
        if flow_logger:
            flow_logger.log_ai_4_start(len(tickers))
        sentiment_analysis = self.sentiment_analyzer.analyze_batch(
            tickers,
            on_ticker=lambda t, i, n: (flow_logger.log_ai_4_fetch(t, i, n) if flow_logger else None, _activity(4, f"正在分析 {t} ({i}/{n}) …") if callable(on_step_activity) else None),
            news_by_ticker=news_by_ticker_for_sentiment,
        )
        if flow_logger:
            flow_logger.log_ai_4_result()
        _activity(4, "情緒分析完成")
        _prog(4, "情緒分析", 100)
        if report_dir:
            write_step_report(report_dir, 4, flow_steps[3], short_names[3])
        # 細項 5：Multi-Agent 協作分析
        _prog(5, "多智能體", 0)
        _activity(5, "多智能體：彙總候選與市場數據、產出共識…")
        if flow_logger:
            flow_logger.log_ai_5_start(len(pattern_analysis))
        multi_agent_analysis = self.multi_agent.analyze_all(candidates=pattern_analysis, data=market_data)
        if flow_logger:
            flow_logger.log_ai_5_result()
        _activity(5, "多智能體分析完成")
        _prog(5, "多智能體", 100)
        if report_dir:
            write_step_report(report_dir, 5, flow_steps[4], short_names[4])
        # 細項 6：霊視記憶參考
        _prog(6, "記憶洞察", 0)
        _activity(6, "霊視記憶：查詢歷史案例、提取洞察…")
        if flow_logger:
            flow_logger.log_ai_6_start()
        memory_insights = self.memory.get_insights_for_candidates(pattern_analysis)
        if flow_logger:
            n_insights = len(memory_insights.get("insights", [])) if isinstance(memory_insights, dict) else 0
            flow_logger.log_ai_6_result(n_insights)
        _activity(6, "記憶洞察完成")
        _prog(6, "記憶洞察", 100)
        if report_dir:
            write_step_report(report_dir, 6, flow_steps[5], short_names[5])
        all_analyses = AllAnalyses(
            pattern=pattern_analysis,
            causal=causal_analysis,
            sentiment=sentiment_analysis,
            multi_agent=multi_agent_analysis,
            memory=memory_insights,
        )
        # 細項 7：決策引擎 — 第二層防護：LLM 防幻覺
        _prog(7, "決策引擎（LLM 決策中…）", 0)
        _activity(7, "決策引擎：組裝 prompt、呼叫 LLM（防幻覺 + 自我質疑）…")
        if flow_logger:
            flow_logger.log_layer2_start()
        decision = self.decision_engine.decide(
            state=self.portfolio, analyses=all_analyses, on_llm_progress=_on_llm_wrap
        )
        if flow_logger and decision:
            acts = getattr(decision, "actions", []) or []
            summary = ", ".join([f"{getattr(a, 'action', '')} {getattr(a, 'ticker', '')}" for a in acts[:3]]) if acts else "無操作"
            flow_logger.log_layer2_result(len(acts), summary)
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
    
    def _get_scan_tickers(self, quick: bool = False, full_universe: bool = False):
        """取得要掃描的股票列表。quick=True 時 20 支（小回測）；quick=False 且 full_universe=True 時從美股池取（大回測，預設 cap 50）；否則 50 支。"""
        import yaml
        tickers = []
        if full_universe:
            # 大回測：從 data/us_universe.csv 取美股（cap 由 env 或 50）
            us_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "us_universe.csv")
            if os.path.isfile(us_path):
                try:
                    import csv
                    with open(us_path, "r", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            sym = (row.get("symbol") or row.get("Symbol") or "").strip()
                            if sym:
                                tickers.append(sym)
                except Exception:
                    pass
            cap_full = int(os.getenv("V5_BACKTEST_FULL_CAP", "50"))
            return tickers[:cap_full] if tickers else []
        if os.path.isfile("config.yaml"):
            try:
                with open("config.yaml", "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                if cfg and isinstance(cfg.get("mvp"), dict):
                    tickers = cfg["mvp"].get("scan_tickers") or []
            except Exception:
                pass
        if not tickers:
            env_tickers = os.getenv("V5_SCAN_TICKERS", "AAPL,GOOGL,MSFT,TSLA,NVDA")
            tickers = [t.strip() for t in env_tickers.split(",") if t.strip()]
        cap = 20 if quick else 50
        return tickers[:cap]

    def _fetch_and_validate_data(self, end_date=None, start_date=None, quick: bool = False, full_universe: bool = False, silent: bool = False, on_ticker=None):
        """获取并验证市场数据。end_date 有值時為回測：只取該日及之前（無偷看）。on_ticker(ticker, index, total) 可選回報正在取的標的。返回 (market_data, data_source_str)。"""
        tickers = self._get_scan_tickers(quick=quick, full_universe=full_universe)
        market_data = {}
        data_source = "yfinance"
        end_str = end_date.strftime("%Y-%m-%d") if hasattr(end_date, "strftime") else end_date
        start_str = start_date.strftime("%Y-%m-%d") if start_date and hasattr(start_date, "strftime") else start_date
        n_tickers = len(tickers)
        try:
            from utils.data_fetcher import DataFetcher
            fetcher = DataFetcher()
            data_source = "Yahoo (DataFetcher)"
            for idx, ticker in enumerate(tickers):
                if callable(on_ticker):
                    on_ticker(ticker, idx + 1, n_tickers)
                try:
                    df = fetcher.get_yahoo_history(ticker, period="90d", end_date=end_str, start_date=start_str)
                    if df is not None and not df.empty and len(df) >= 20:
                        market_data[ticker] = df
                        if not silent:
                            print(f"   ✓ {ticker}: {len(df)} 筆")
                    else:
                        if not silent:
                            print(f"   ⚠ {ticker}: 資料不足，跳過")
                except Exception as e:
                    if not silent:
                        print(f"   ⚠ {ticker}: {e}")
            if not market_data and not silent:
                print("   ⚠ 無有效數據，使用預設空結構")
        except ImportError:
            import yfinance as yf
            from datetime import timedelta
            data_source = "yfinance"
            end_excl = None
            if end_str:
                try:
                    d = datetime.strptime(end_str, "%Y-%m-%d").date() if isinstance(end_str, str) else end_str
                    end_excl = (d + timedelta(days=1)).strftime("%Y-%m-%d")
                except Exception:
                    end_excl = None
            for idx, ticker in enumerate(tickers):
                if callable(on_ticker):
                    on_ticker(ticker, idx + 1, n_tickers)
                try:
                    stock = yf.Ticker(ticker)
                    hist = stock.history(period="90d", end=end_excl) if end_excl else stock.history(period="90d")
                    if hist is not None and not hist.empty and len(hist) >= 20:
                        market_data[ticker] = hist
                        if not silent:
                            print(f"   ✓ {ticker}: {len(hist)} 筆")
                except Exception as e:
                    if not silent:
                        print(f"   ⚠ {ticker}: {e}")
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


def run_backtest_v5_full_range(start_date: str, end_date: str, quick: bool = False, full_universe: bool = False):
    """v5.0 大回測／小回測：逐日跑 v5.0 流程，回傳 (summary_path, trades_path)。full_universe=True 時從美股池取（大回測），quick=True 時 20 檔（小回測）。"""
    from datetime import datetime as dt
    from core.backtest_engine import (
        BacktestEngine,
        get_trading_days,
        prev_trading_day,
        get_execution_prices_for_date,
        apply_v5_decision,
    )
    from reporting.step_report import write_daily_final_report
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
    mode_str = "小回測（20 檔/日）" if quick else "大回測（美股池約 50 檔/日）" if full_universe else "回測（50 檔/日）"
    print("\n" + "=" * 70)
    print("🔗 REISHI v5.0 回测（逐日 v5.0 流程） " + mode_str)
    print("=" * 70)
    print(f"📅 期間: {start_date} → {end_date}，共 {len(trading_days)} 個交易日")
    print(f"💰 初始資金: {config.initial_cash:,.0f} HKD")
    print(f"📁 細項報告與當日報告: {output_dir}/daily_YYYY-MM-DD/")
    print("=" * 70)
    print("⏳ 每日會跑完整 v5.0 流程（數據+多模組+LLM），首日可能需數分鐘，請稍候…")
    print("📄 回測「完整跑完」後: backtest_summary.csv, backtest_trades.csv")
    print("   （若中途 Ctrl+C 中斷，已完成的當日報告會保留）")
    print("=" * 70)
    reishi = ReishiV5()
    cash = config.initial_cash
    positions = []
    daily_records = []
    all_trades = []
    for i, T in enumerate(trading_days):
        try:
            print(f"   [{i+1}/{len(trading_days)}] 正在處理 {T} …", flush=True)
            day_start = time.time()
            prev_d = prev_trading_day(T)
            backtest_start_eff = (prev_d - timedelta(days=90)) if prev_d < start_d else start_d
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
                if pct >= 100:
                    remaining = (elapsed / step_i) * (total - step_i) if step_i > 0 else 0
                    print(f"    細項 {step_i}/{total} {name} {flow_label} {pct}% (已用 {elapsed:.0f} 秒，本日預計剩餘約 {remaining:.0f} 秒)", flush=True)
                else:
                    msg = f"    細項 {step_i}/{total} {name} {flow_label} {pct}% (已用 {elapsed:.0f} 秒，請稍候…)"
                    if step_i == 7 and pct == 0:
                        msg += "\n    ※ 約需 30～120 秒；若超過 2 分鐘無新輸出可能為 API/網路問題"
                    else:
                        completed = max(1, step_i - 1)
                        remaining = (elapsed / completed) * (total - step_i + 1) if completed > 0 else 0
                        msg += f"，本日預計剩餘約 {remaining:.0f} 秒"
                    print(msg, flush=True)
            def _on_ticker(ticker, idx, total):
                print(f"    [Flow 步驟 1] 數據獲取: 正在取得 {ticker} ({idx}/{total}) …", flush=True)
            def _on_step_activity(step_i, message):
                flow_name = flow_steps[step_i - 1] if 1 <= step_i <= len(flow_steps) else ""
                print(f"    細項 {step_i}/7 {flow_name}: {message}", flush=True)
            def _on_llm_progress(phase, total, message, provider=None):
                if provider:
                    print(f"    決策引擎 LLM 第 {phase}/{total} 次（{message}）完成，使用 {provider}", flush=True)
                else:
                    print(f"    決策引擎 LLM 第 {phase}/{total} 次（{message}）…", flush=True)
            try:
                decision, all_analyses = reishi.run_daily_for_backtest(
                    prev_d, backtest_start_eff, quick=quick, full_universe=full_universe, silent=True,
                    on_progress=_on_progress, on_llm_progress=_on_llm_progress, on_ticker=_on_ticker,
                    on_step_activity=_on_step_activity,
                    flow_logger=flow_logger,
                    report_dir=daily_report_dir,
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
            output_dir_partial = f"reports/backtest_range/{start_date}_to_{end_date}_interrupted_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            engine.daily_records = daily_records
            engine.trades = all_trades
            summary_path, trades_path = engine.save_results(output_dir_partial)
            print("\n⚠ 已中斷 (Ctrl+C)，部分報告已寫入: {} , {}".format(summary_path or "", trades_path or ""), flush=True)
            raise
    output_dir = f"reports/backtest_range/{start_date}_to_{end_date}"
    engine.daily_records = daily_records
    engine.trades = all_trades
    summary_path, trades_path = engine.save_results(output_dir)
    return summary_path, trades_path


def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(description='REISHI 霊視 v5.0 MVP')
    parser.add_argument('--daily', action='store_true', help='运行每日分析')
    parser.add_argument('--monitor', action='store_true', help='启动即时监控')
    parser.add_argument('--stats', action='store_true', help='显示统计信息')
    parser.add_argument('--backtest', nargs='*', metavar=('START_DATE', 'END_DATE'),
                        help='运行回测（逐日 v5.0 流程）。不传日期则用默认区间（约最近 90 天）；传两个日期则用 YYYY-MM-DD YYYY-MM-DD')
    parser.add_argument('--quick', action='store_true', help='回测时小回测（每日 20 档）')
    parser.add_argument('--full-universe', action='store_true', help='回测时大回测（从美股池取约 50 档）')
    
    args = parser.parse_args()
    
    # 回测模式：v5.0 大回测／小回测（逐日跑 v5.0 流程）
    if args.backtest is not None:
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
        quick = getattr(args, "quick", False)
        full_universe = getattr(args, "full_universe", False)
        summary_path, trades_path = run_backtest_v5_full_range(start_date, end_date, quick=quick, full_universe=full_universe)
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

    # 互動模式：先選 正常 mode 或 回測 mode（與 v4.3 一致）
    print(BANNER_V5)
    print("\n請選擇運行模式：")
    print("  [1] 正常 mode — 今日決策（持倉 + 當天思考）")
    print("  [2] 回測 mode — 歷史回放（測試策略）")
    print("  [0] 顯示命令列參數說明")
    choice = input("\n請輸入選項 [1/2/0]: ").strip()

    if choice == "1":
        run_dir = _create_run_dir_v5()
        log_file, original_stdout = _start_log_v5(run_dir)
        try:
            print(f"\n📁 本次報告目錄: {run_dir}")
            print("🔮 啟動霊視，洞察市場...\n")
            reishi = ReishiV5()
            reishi.run_daily()
        finally:
            _stop_log_v5(log_file, original_stdout)

    elif choice == "2":
        print("\n📅 回測模式")
        print("  請選擇回測規模：")
        print("    [1] 大回測 — 從美股池取樣（每日約 50 檔，可設 V5_BACKTEST_FULL_CAP）")
        print("    [2] 小回測 — 快速測試（每日 20 檔美股）")
        choice2 = input("  請輸入 [1/2]: ").strip()
        quick = choice2 == "2"  # 小回測 = quick
        full_universe = choice2 == "1"  # 大回測 = 從美股池取
        start_str = input("  請輸入開始日期（YYYY-MM-DD 或 YYYYMMDD）：").strip().replace(" ", "")
        end_str = input("  請輸入結束日期（YYYY-MM-DD 或 YYYYMMDD）：").strip().replace(" ", "")

        def _norm_date(s):
            s = s.strip()
            if len(s) == 8 and s.isdigit():
                return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
            return s

        try:
            from core.backtest_engine import get_trading_days
            start_dt = datetime.strptime(_norm_date(start_str), "%Y-%m-%d").date()
            end_dt = datetime.strptime(_norm_date(end_str), "%Y-%m-%d").date()
            if start_dt >= end_dt:
                print("❌ 結束日期必須晚於開始日期")
                return
            trading = get_trading_days(start_dt, end_dt)
            n_days = len(trading)
            mode_str = "小回測（20 檔/日）" if quick else "大回測（美股池約 50 檔/日）"
            print(f"\n🔮 啟動霊視回測 — {mode_str}（{start_dt} ~ {end_dt}），共 {n_days} 個交易日，選定後開始執行...\n")
            # 美學：回測時也 tee 到報告目錄的 log
            backtest_run_dir = os.path.join("reports", "backtest_range", f"{start_dt.strftime('%Y-%m-%d')}_to_{end_dt.strftime('%Y-%m-%d')}")
            os.makedirs(backtest_run_dir, exist_ok=True)
            log_file_bt, original_stdout_bt = _start_log_v5(backtest_run_dir, log_name="REIKAN_run.log")
            try:
                summary_path, trades_path = run_backtest_v5_full_range(
                    start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"), quick=quick, full_universe=full_universe
                )
            finally:
                _stop_log_v5(log_file_bt, original_stdout_bt)
            if summary_path:
                print("\n" + "=" * 70)
                print("✅ 回測完成")
                print(f"📄 摘要: {summary_path}")
                print(f"📄 交易: {trades_path}")
                print("=" * 70)
        except ValueError:
            print("❌ 日期格式錯誤，請用 YYYY-MM-DD 或 YYYYMMDD")
        except Exception as e:
            print(f"❌ 回測錯誤: {e}")
            import traceback
            traceback.print_exc()

    elif choice == "0":
        print("\n" + "=" * 50)
        print("📋 命令列參數說明")
        print("=" * 50)
        print("  python main_v5.py --daily    # 每日分析")
        print("  python main_v5.py --monitor  # 即時監控")
        print("  python main_v5.py --stats    # 統計資訊")
        print("  python main_v5.py --backtest [START END] [--quick] [--full-universe]  # 回測（不傳日期則預設約 90 天）")
        print("    --quick = 小回測（20 檔/日），--full-universe = 大回測（美股池約 50 檔/日）")
        print("=" * 50)
    else:
        print("❌ 無效選項，請重新執行並選擇 1/2/0")


# ---------------------------------------------------------------------------
# v4.3 風格：美學 banner、run 目錄、tee log（與 main.py 一致）
# ---------------------------------------------------------------------------
BANNER_V5 = """
═══════════════════════════════════════════════════════════════════════
                                                                       
                     R  E  I  S  H  I                      
                   ━━━━━━━━━━━━━━━━                       
                 ━━━━━━━━━━━━━━━━━━━━                     
               ━━━━━━━━━━━━━━━━━━━━━━━━                   
                                                                       
                      霊      視                          
                                                                       
             ░░░░░░░░░⚡░░░░░░░░░                       
           ░░░░░░░░░░░░░░░░░░░░░░░░                     
         ░░░░░░░░░░░░░░░░░░░░░░░░░░░░                   
                                                                       
                      v5.0 MVP
                                                                       
═══════════════════════════════════════════════════════════════════════
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
