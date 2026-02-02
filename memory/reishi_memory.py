"""
REISHI 霊視 v5.0 - 霊視记忆（经验累积系统）

目的：记录所有交易，累积学习
- 记录AI建议
- 记录执行结果
- 记录交易结果
- 查找类似案例
- 提取洞察
"""

from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime
import sqlite3
import os


@dataclass
class Recommendation:
    id: str
    timestamp: datetime
    ticker: str
    action: str
    entry_price_low: float
    entry_price_high: float
    stop_loss: float
    target_price: float
    position_size_pct: float
    confidence: float
    reasoning: str


@dataclass
class Execution:
    recommendation_id: str
    executed: bool
    execution_time: datetime
    actual_price: float
    actual_shares: int
    modifications: str
    skip_reason: Optional[str] = None


@dataclass
class TradeResult:
    recommendation_id: str
    exit_time: datetime
    exit_price: float
    exit_reason: str
    pnl_amount: float
    pnl_pct: float
    holding_days: int
    max_drawdown: float
    max_gain: float
    notes: str


class ReishiMemory:
    """
    霊視记忆：经验累积系统
    """
    
    def __init__(self, db_path: str = "data/reishi_memory.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        
        # 创建recommendations表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS recommendations (
                id TEXT PRIMARY KEY,
                timestamp TEXT,
                ticker TEXT,
                action TEXT,
                entry_price_low REAL,
                entry_price_high REAL,
                stop_loss REAL,
                target_price REAL,
                position_size_pct REAL,
                confidence REAL,
                reasoning TEXT
            )
        """)
        
        # 创建executions表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS executions (
                recommendation_id TEXT PRIMARY KEY,
                executed INTEGER,
                execution_time TEXT,
                actual_price REAL,
                actual_shares INTEGER,
                modifications TEXT,
                skip_reason TEXT,
                FOREIGN KEY (recommendation_id) REFERENCES recommendations(id)
            )
        """)
        
        # 创建trade_results表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trade_results (
                recommendation_id TEXT PRIMARY KEY,
                exit_time TEXT,
                exit_price REAL,
                exit_reason TEXT,
                pnl_amount REAL,
                pnl_pct REAL,
                holding_days INTEGER,
                max_drawdown REAL,
                max_gain REAL,
                notes TEXT,
                FOREIGN KEY (recommendation_id) REFERENCES recommendations(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def record_recommendation(self, rec: Recommendation):
        """记录AI建议"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO recommendations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rec.id,
            rec.timestamp.isoformat(),
            rec.ticker,
            rec.action,
            rec.entry_price_low,
            rec.entry_price_high,
            rec.stop_loss,
            rec.target_price,
            rec.position_size_pct,
            rec.confidence,
            rec.reasoning
        ))
        conn.commit()
        conn.close()
    
    def record_execution(self, rec_id: str, execution: Execution):
        """记录执行"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO executions VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            rec_id,
            1 if execution.executed else 0,
            execution.execution_time.isoformat(),
            execution.actual_price,
            execution.actual_shares,
            execution.modifications,
            execution.skip_reason
        ))
        conn.commit()
        conn.close()
    
    def record_result(self, rec_id: str, result: TradeResult):
        """记录交易结果"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO trade_results VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rec_id,
            result.exit_time.isoformat(),
            result.exit_price,
            result.exit_reason,
            result.pnl_amount,
            result.pnl_pct,
            result.holding_days,
            result.max_drawdown,
            result.max_gain,
            result.notes
        ))
        conn.commit()
        conn.close()
    
    def get_similar_cases(self, current: Dict, limit: int = 10) -> List[Dict]:
        """查找类似的历史案例"""
        # MVP: 简化实现
        return []
    
    def get_statistics(self) -> Dict:
        """获取统计数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 总交易数
        cursor.execute("SELECT COUNT(*) FROM recommendations")
        total = cursor.fetchone()[0]
        
        # 已执行数
        cursor.execute("SELECT COUNT(*) FROM executions WHERE executed = 1")
        executed = cursor.fetchone()[0]
        
        # 已完成数
        cursor.execute("SELECT COUNT(*) FROM trade_results")
        completed = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_recommendations': total,
            'executed': executed,
            'completed': completed
        }
    
    def get_insights(self) -> List[str]:
        """从历史数据中提取洞察"""
        stats = self.get_statistics()
        insights = []
        
        if stats['total_recommendations'] > 0:
            execute_rate = stats['executed'] / stats['total_recommendations'] * 100
            insights.append(f"执行率: {execute_rate:.1f}%")
        
        return insights
    
    def get_insights_for_candidates(self, candidates):
        """为候选股票获取历史洞察"""
        return {
            'summary': f'霊視记忆分析 - 共{len(self.get_insights())}条洞察',
            'insights': self.get_insights()
        }
