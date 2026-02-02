"""
REISHI 霊視 v5.0 - 回测引擎（Orchestrator 对接）

目的：为 Orchestrator 提供回测功能
- 读取 config.json 动态参数
- 输出 backtest_summary.csv
- 输出 backtest_trades.csv
- v5.0 大回測／小回測：逐日跑 v5.0 流程（需由 main_v5 迴圈呼叫）
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, date, timedelta
import pandas as pd
import os
import json

# ---------------------------------------------------------------------------
# 交易日曆與執行價（供 v5.0 逐日回測用）
# ---------------------------------------------------------------------------

_nyse_cal = None
_nyse_failed = False


def get_trading_days(start: date, end: date) -> List[date]:
    """取得 start～end 間的交易日（美國市場）。無日曆則僅排除週末。"""
    global _nyse_cal, _nyse_failed
    if not _nyse_failed and _nyse_cal is None:
        try:
            import pandas_market_calendars as mcal
            _nyse_cal = mcal.get_calendar("NYSE")
        except Exception:
            _nyse_failed = True
    if _nyse_cal is not None:
        try:
            schedule = _nyse_cal.schedule(start_date=start, end_date=end)
            if schedule is not None and not schedule.empty:
                return [d.date() for d in schedule.index]
        except Exception:
            pass
    days = []
    d = start
    while d <= end:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


def prev_trading_day(d: date) -> date:
    """d 的前一交易日。"""
    out = d - timedelta(days=1)
    while out.weekday() >= 5:
        out -= timedelta(days=1)
    return out


def get_execution_prices_for_date(tickers: List[str], execution_date: date) -> Dict[str, float]:
    """取得 execution_date 當日收盤價（供回測執行用）。"""
    out = {}
    end_str = execution_date.strftime("%Y-%m-%d")
    try:
        from utils.data_fetcher import DataFetcher
        fetcher = DataFetcher()
        for t in tickers:
            df = fetcher.get_yahoo_history(t, period="5d", end_date=end_str)
            if df is not None and not df.empty and "Close" in df.columns:
                out[t] = float(df["Close"].iloc[-1])
    except Exception:
        pass
    if len(out) < len(tickers):
        try:
            import yfinance as yf
            from datetime import timedelta
            end_excl = (execution_date + timedelta(days=1)).strftime("%Y-%m-%d")
            for t in tickers:
                if t in out:
                    continue
                hist = yf.Ticker(t).history(period="5d", end=end_excl)
                if hist is not None and not hist.empty and "Close" in hist.columns:
                    out[t] = float(hist["Close"].iloc[-1])
        except Exception:
            pass
    return out


def apply_v5_decision(
    cash: float,
    positions: List[Dict],
    decision: Any,
    execution_prices: Dict[str, float],
    date_str: str,
    config: "BacktestConfig",
) -> Tuple[float, List[Dict], List[Trade]]:
    """
    依 v5.0 決策與當日執行價更新持倉，回傳 (新現金, 新持倉, 交易列表)。
    positions: [{"ticker": str, "shares": int, "entry_price" or "buy_price": float}, ...]
    """
    trades: List[Trade] = []
    new_cash = cash
    new_positions = [dict(p) for p in positions]
    pct_entry = config.pct_per_new_entry
    pct_add = config.add_pct
    pct_reduce = config.reduce_pct
    actions = getattr(decision, "actions", []) or []
    # #region agent log
    try:
        import json, time
        _n_actions = len(actions)
        _n_prices = len(execution_prices)
        _sample_actions = []
        for a in actions[:3]:
            _t = getattr(a, "ticker", "") or (a.get("ticker") if isinstance(a, dict) else "")
            _a = getattr(a, "action", "") or (a.get("action") if isinstance(a, dict) else "")
            _sample_actions.append({"ticker": _t, "action": _a})
        with open("/Users/lautinyam/stock_scanner/.cursor/debug.log", "a", encoding="utf-8") as _dbg:
            _dbg.write(json.dumps({"hypothesisId": "H7", "message": "apply_v5_decision_entry", "data": {"n_actions": _n_actions, "n_exec_prices": _n_prices, "cash": cash, "sample_actions": _sample_actions, "exec_prices_sample": list(execution_prices.items())[:3]}, "timestamp": int(time.time() * 1000)}, ensure_ascii=False) + "\n")
    except Exception:
        pass
    # #endregion
    for act in actions:
        ticker = getattr(act, "ticker", "") or (act.get("ticker") if isinstance(act, dict) else "")
        action = (getattr(act, "action", "HOLD") or "HOLD").upper()
        if action == "HOLD" or not ticker:
            continue
        price = execution_prices.get(ticker)
        if price is None or price <= 0:
            continue
        pos = next((p for p in new_positions if (p.get("ticker") or p.get("symbol")) == ticker), None)
        if action in ("BUY", "ADD"):
            pct = pct_add if action == "ADD" and pos else pct_entry
            size_pct = getattr(act, "position_size_pct", None) or (act.get("position_size_pct") if isinstance(act, dict) else None)
            if size_pct is not None:
                pct = size_pct / 100.0
            amt = new_cash * min(pct, 1.0)
            qty = int(amt / price)
            # #region agent log
            try:
                import json, time
                with open("/Users/lautinyam/stock_scanner/.cursor/debug.log", "a", encoding="utf-8") as _dbg:
                    _dbg.write(json.dumps({"hypothesisId": "H7", "message": "buy_calculation", "data": {"ticker": ticker, "price": price, "pct": pct, "amt": amt, "qty": qty, "new_cash": new_cash}, "timestamp": int(time.time() * 1000)}, ensure_ascii=False) + "\n")
            except Exception:
                pass
            # #endregion
            if qty <= 0:
                continue
            cost = qty * price
            if cost > new_cash:
                continue
            new_cash -= cost
            trades.append(Trade(date=date_str, ticker=ticker, action="buy" if action == "BUY" else "add", price=round(price, 2), quantity=qty))
            if pos:
                old_shares = pos.get("shares", 0) or pos.get("quantity", 0)
                old_cost = pos.get("entry_price", 0) or pos.get("buy_price", 0)
                pos["shares"] = old_shares + qty
                pos["entry_price"] = (old_cost * old_shares + cost) / (old_shares + qty) if (old_shares + qty) else price
            else:
                new_positions.append({"ticker": ticker, "shares": qty, "entry_price": price, "buy_price": price})
        elif action in ("SELL", "REDUCE") and pos:
            shares = pos.get("shares", 0) or pos.get("quantity", 0)
            if shares <= 0:
                continue
            sell_pct = 1.0 if action == "SELL" else min(pct_reduce, 1.0)
            sell_qty = max(1, int(shares * sell_pct))
            sell_qty = min(sell_qty, shares)
            new_cash += sell_qty * price
            trades.append(Trade(date=date_str, ticker=ticker, action="sell" if action == "SELL" else "reduce", price=round(price, 2), quantity=sell_qty))
            pos["shares"] = shares - sell_qty
            if pos["shares"] <= 0:
                new_positions.remove(pos)
    # 更新持倉市值供當日組合價值計算
    for p in new_positions:
        t = p.get("ticker") or p.get("symbol")
        if t and t in execution_prices:
            p["current_price"] = execution_prices[t]
    return new_cash, new_positions, trades


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
