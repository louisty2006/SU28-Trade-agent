"""
REISHI 霊視 v5.0 MVP - 主程式

完整系统架构：
- 五层防护系统
- 五大AI方向分析
- 决策引擎
- 即时监控
"""

import argparse
from datetime import datetime
import os

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
        self.notifier = TelegramNotifier()
        
        print("✓ 所有模块已加载")
        
        # 默认组合状态
        self.portfolio = PortfolioState(
            cash=40_000.0,  # 40,000 HKD
            positions=[],
            total_value=40_000.0
        )
    
    def run_daily(self):
        """
        每日运行
        """
        print("\n" + "=" * 70)
        print("🔮 REISHI 霊視 v5.0 - 每日分析")
        print("=" * 70)
        
        try:
            # 1. 获取并验证数据
            print("\n[1/8] 数据获取与验证...")
            market_data = self._fetch_and_validate_data()
            
            # 2. 图表型态识别
            print("\n[2/8] 图表型态识别...")
            pattern_analysis = self.pattern_recognition.scan_all(
                ['AAPL', 'GOOGL', 'MSFT'],  # MVP: 示例股票
                market_data
            )
            
            # 3. 因果推理
            print("\n[3/8] 因果推理...")
            causal_analysis = self.causal_reasoning.analyze_all(
                news=[],
                portfolio=self.portfolio.positions
            )
            
            # 4. 情绪分析
            print("\n[4/8] 情绪分析...")
            sentiment_analysis = self.sentiment_analyzer.analyze_batch(
                ['AAPL', 'GOOGL', 'MSFT']
            )
            
            # 5. Multi-Agent 分析
            print("\n[5/8] Multi-Agent 协作分析...")
            multi_agent_analysis = self.multi_agent.analyze_all(
                candidates=pattern_analysis,
                data=market_data
            )
            
            # 6. 霊視记忆参考
            print("\n[6/8] 霊視记忆参考...")
            memory_insights = self.memory.get_insights_for_candidates(pattern_analysis)
            
            # 7. 决策引擎
            print("\n[7/8] 决策引擎...")
            all_analyses = AllAnalyses(
                pattern=pattern_analysis,
                causal=causal_analysis,
                sentiment=sentiment_analysis,
                multi_agent=multi_agent_analysis,
                memory=memory_insights
            )
            
            decision = self.decision_engine.decide(
                state=self.portfolio,
                analyses=all_analyses
            )
            
            # 8. 验证 + 审计
            print("\n[8/8] 最终验证与审计...")
            validation = self.output_validator.validate_decision(decision, all_analyses)
            audit = self.final_auditor.audit(decision, all_analyses)
            
            # 生成报告
            print("\n生成报告...")
            report = self.report_generator.generate(decision, all_analyses, audit)
            
            # 保存报告
            report_dir = f"reports/daily"
            os.makedirs(report_dir, exist_ok=True)
            report_path = f"{report_dir}/{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.md"
            report.save(report_path)
            
            # 发送报告
            self.notifier.send_daily_report(report)
            
            print("\n" + "=" * 70)
            print("✅ 每日分析完成！")
            print(f"📄 报告已保存: {report_path}")
            print("=" * 70)
            
            # 显示报告摘要
            print("\n" + report.to_text())
            
            return report
            
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _fetch_and_validate_data(self):
        """获取并验证市场数据"""
        # MVP: 返回模拟数据
        return {
            'AAPL': None,
            'GOOGL': None,
            'MSFT': None
        }
    
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


def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(description='REISHI 霊視 v5.0 MVP')
    parser.add_argument('--daily', action='store_true', help='运行每日分析')
    parser.add_argument('--monitor', action='store_true', help='启动即时监控')
    parser.add_argument('--stats', action='store_true', help='显示统计信息')
    
    args = parser.parse_args()
    
    reishi = ReishiV5()
    
    if args.daily:
        reishi.run_daily()
    elif args.monitor:
        reishi.start_monitoring()
    elif args.stats:
        reishi.show_statistics()
    else:
        # 互动模式
        print("\nREISHI 霊視 v5.0 MVP")
        print("[1] 运行每日分析")
        print("[2] 启动即时监控")
        print("[3] 显示统计信息")
        choice = input("\n选择: ")
        
        if choice == "1":
            reishi.run_daily()
        elif choice == "2":
            reishi.start_monitoring()
        elif choice == "3":
            reishi.show_statistics()
        else:
            print("无效选项")


if __name__ == "__main__":
    main()
