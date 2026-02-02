"""
REISHI 霊視 v5.0 - 回测引擎（Orchestrator 对接）

目的：为 Orchestrator 提供回测功能
- 读取 config.json 动态参数
- 输出 backtest_summary.csv
- 输出 backtest_trades.csv

注意：这是独立模块，不影响 v5.0 的核心功能
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date, timedelta
import pandas as pd
import os
import json


@dataclass
class BacktestConfig:
    """回测配置"""
    initial_cash: float = 40_000.0  # HKD
    pct_per_new_entry: float = 0.20
    add_pct: float = 0.10
    reduce_pct: float = 0.50
    stage1_weights: Optional[Dict] = None
    stage2_weights: Optional[Dict] = None


@dataclass
class Position:
    """持仓"""
    ticker: str
    shares: int
    entry_price: float
    current_price: float = 0.0


@dataclass
class Trade:
    """交易记录"""
    date: str
    ticker: str
    action: str  # buy, sell, add, reduce
    price: float
    quantity: int


class BacktestEngine:
    """
    回测引擎（专为 Orchestrator 设计）
    
    功能：
    1. 读取 config.json
    2. 执行历史回测
    3. 输出标准化 CSV
    """
    
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.cash = self.config.initial_cash
        self.positions: List[Position] = []
        self.trades: List[Trade] = []
        self.daily_records = []
    
    def _load_config(self, config_path: str) -> BacktestConfig:
        """读取 Orchestrator 配置"""
        if not os.path.exists(config_path):
            print(f"ℹ️  未找到 {config_path}，使用默认配置")
            return BacktestConfig()
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            print(f"🔗 已读取 Orchestrator 配置: {config_path}")
            
            return BacktestConfig(
                initial_cash=data.get("backtest_initial_cash", 40_000.0),
                pct_per_new_entry=data.get("backtest_pct_per_new_entry", 0.20),
                add_pct=data.get("backtest_add_pct", 0.10),
                reduce_pct=data.get("backtest_reduce_pct", 0.50),
                stage1_weights=data.get("stage1_weights"),
                stage2_weights=data.get("stage2_weights"),
            )
        except Exception as e:
            print(f"⚠️ 读取配置失败: {e}，使用默认配置")
            return BacktestConfig()
    
    def run(self, start_date: date, end_date: date, candidates: List[str]) -> Dict:
        """
        执行回测
        
        Args:
            start_date: 回测开始日期
            end_date: 回测结束日期
            candidates: 候选股票列表
        
        Returns:
            回测结果摘要
        """
        print(f"\n🔮 REISHI v5.0 回测引擎")
        print(f"📅 期间: {start_date} → {end_date}")
        print(f"💰 初始资金: {self.config.initial_cash:,.0f} HKD")
        print(f"📊 候选股票: {len(candidates)} 支")
        
        # 重置状态
        self.cash = self.config.initial_cash
        self.positions = []
        self.trades = []
        self.daily_records = []
        
        # 模拟交易（简化版，实际应调用 v5.0 的分析模块）
        current_date = start_date
        day_count = 0
        
        while current_date <= end_date:
            day_count += 1
            
            # 每日记录
            portfolio_value = self._calculate_portfolio_value()
            return_pct = (portfolio_value - self.config.initial_cash) / self.config.initial_cash * 100
            
            self.daily_records.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'portfolio_value': round(portfolio_value, 2),
                'cash': round(self.cash, 2),
                'positions_count': len(self.positions),
                'return_pct': round(return_pct, 2),
            })
            
            # 下一个交易日（简化：每天都是交易日）
            current_date += timedelta(days=1)
        
        print(f"✓ 回测完成：{day_count} 个交易日")
        print(f"✓ 总交易: {len(self.trades)} 笔")
        print(f"✓ 最终价值: {portfolio_value:,.2f} HKD")
        print(f"✓ 累计报酬: {return_pct:.2f}%")
        
        return {
            'final_value': portfolio_value,
            'return_pct': return_pct,
            'total_trades': len(self.trades),
        }
    
    def _calculate_portfolio_value(self) -> float:
        """计算组合总价值"""
        positions_value = sum(p.shares * p.current_price for p in self.positions)
        return self.cash + positions_value
    
    def _execute_trade(self, trade: Trade):
        """执行交易"""
        self.trades.append(trade)
        
        if trade.action in ['buy', 'add']:
            # 买入
            cost = trade.price * trade.quantity
            if cost <= self.cash:
                self.cash -= cost
                # 更新持仓
                existing = next((p for p in self.positions if p.ticker == trade.ticker), None)
                if existing:
                    # 加仓
                    total_shares = existing.shares + trade.quantity
                    avg_price = (existing.entry_price * existing.shares + cost) / total_shares
                    existing.shares = total_shares
                    existing.entry_price = avg_price
                else:
                    # 新建仓位
                    self.positions.append(Position(
                        ticker=trade.ticker,
                        shares=trade.quantity,
                        entry_price=trade.price,
                        current_price=trade.price,
                    ))
        
        elif trade.action in ['sell', 'reduce']:
            # 卖出
            pos = next((p for p in self.positions if p.ticker == trade.ticker), None)
            if pos:
                self.cash += trade.price * trade.quantity
                pos.shares -= trade.quantity
                if pos.shares <= 0:
                    self.positions.remove(pos)
    
    def save_results(self, output_dir: str):
        """
        保存回测结果（Orchestrator 标准格式）
        
        输出：
        1. backtest_summary.csv - 每日盈亏
        2. backtest_trades.csv - 交易清单
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # 1. 每日盈亏
        summary_path = os.path.join(output_dir, "backtest_summary.csv")
        df_summary = pd.DataFrame(self.daily_records)
        df_summary.to_csv(summary_path, index=False, encoding='utf-8-sig')
        print(f"✓ 已保存: {summary_path}")
        
        # 2. 交易清单
        trades_path = os.path.join(output_dir, "backtest_trades.csv")
        trades_data = [{
            'date': t.date,
            'ticker': t.ticker,
            'action': t.action,
            'price': t.price,
            'quantity': t.quantity,
        } for t in self.trades]
        df_trades = pd.DataFrame(trades_data)
        df_trades.to_csv(trades_path, index=False, encoding='utf-8-sig')
        print(f"✓ 已保存: {trades_path}")
        
        return summary_path, trades_path


def run_backtest_for_orchestrator(
    start_date: str,
    end_date: str,
    candidates: Optional[List[str]] = None,
    config_path: str = "config.json",
) -> Tuple[str, str]:
    """
    为 Orchestrator 运行回测（便捷函数）
    
    Args:
        start_date: 开始日期 "YYYY-MM-DD"
        end_date: 结束日期 "YYYY-MM-DD"
        candidates: 候选股票列表（可选）
        config_path: 配置文件路径
    
    Returns:
        (summary_path, trades_path) 输出文件路径
    """
    # 转换日期
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    
    # 默认候选
    if candidates is None:
        candidates = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'NVDA']
    
    # 创建引擎
    engine = BacktestEngine(config_path=config_path)
    
    # 运行回测
    engine.run(start, end, candidates)
    
    # 保存结果
    output_dir = f"reports/backtest_range/{start_date}_to_{end_date}"
    return engine.save_results(output_dir)
