"""
REISHI 霊視 v5.0 - 图表型态识别

目的：识别技术图表型态（VCP、突破、杯柄等）
实现方式：规则侦测 + LLM看图验证
"""

from dataclasses import dataclass
from typing import List, Optional
import pandas as pd


@dataclass
class Pattern:
    """型态"""
    ticker: str
    pattern_type: str  # 'breakout', 'vcp', 'ma_alignment', etc.
    confidence: float
    description: str
    verified_by_llm: bool = False


@dataclass
class PatternCandidate:
    """型态候选"""
    ticker: str
    pattern_type: str
    score: float
    data: pd.DataFrame
    # 交易建议参数
    current_price: Optional[float] = None
    entry_price_low: Optional[float] = None
    entry_price_high: Optional[float] = None
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None
    reasoning: str = ""


class PatternRecognition:
    """
    图表型态识别
    混合方案：规则侦测（快速筛选）+ LLM看图（精确验证）
    """
    
    def scan_all(self, tickers: List[str], market_data: dict, on_ticker=None) -> List[PatternCandidate]:
        """
        第一阶段：规则侦测，快速扫描全市场
        返回候选清单。on_ticker(ticker, index, total) 可選，回報正在掃描的標的。
        """
        candidates = []
        limited = [t for t in tickers if t in market_data]
        total = len(limited)
        for idx, ticker in enumerate(limited):
            if callable(on_ticker):
                on_ticker(ticker, idx + 1, total)
            # 检测各种型态
            df = market_data.get(ticker)
            breakout = self.detect_breakout(ticker, df)
            if breakout and df is not None and len(df) > 0:
                # 计算交易参数
                current = df['Close'].iloc[-1]
                high_20d = df['High'].iloc[-20:].max()
                low_20d = df['Low'].iloc[-20:].min()
                
                # 进场区间：当前价 ± 2%
                entry_low = current * 0.98
                entry_high = current * 1.02
                
                # 止损：20日低点下方 2%（风险约 15-20%）
                stop = low_20d * 0.98
                
                # 目标价：基于突破后上涨空间（风险回报比 2:1）
                risk = current - stop
                target = current + (risk * 2.0)
                
                candidates.append(PatternCandidate(
                    ticker=ticker,
                    pattern_type='breakout',
                    score=0.7,
                    data=df,
                    current_price=float(current),
                    entry_price_low=float(entry_low),
                    entry_price_high=float(entry_high),
                    stop_loss=float(stop),
                    target_price=float(target),
                    reasoning=f"突破 20 日高点 ${high_20d:.2f}，风险回报比 2:1"
                ))
        return candidates
    
    def detect_breakout(self, ticker: str, data: Optional[pd.DataFrame]) -> Optional[Pattern]:
        """
        侦测突破型态
        
        规则：
        - 价格突破近 N 日高点
        - 成交量 > 平均 1.5 倍
        - 均线排列向上
        """
        if data is None or len(data) < 20:
            return None
        
        # 简化实现
        current_price = data['Close'].iloc[-1]
        max_20d = data['Close'].iloc[-20:].max()
        
        if current_price >= max_20d * 0.98:
            return Pattern(
                ticker=ticker,
                pattern_type='breakout',
                confidence=0.7,
                description=f"{ticker} 接近或突破20日新高 (当前: ${current_price:.2f}, 20日高点: ${max_20d:.2f})"
            )
        
        return None
    
    def detect_vcp(self, ticker: str, data: Optional[pd.DataFrame]) -> Optional[Pattern]:
        """侦测 VCP（波动收缩型态）"""
        # MVP: 简化实现
        return None
    
    def detect_ma_alignment(self, ticker: str, data: Optional[pd.DataFrame]) -> Optional[Pattern]:
        """侦测均线排列"""
        # MVP: 简化实现
        return None
    
    def verify_with_llm(self, ticker: str, pattern_type: str) -> dict:
        """
        第二阶段：LLM看图验证
        
        流程：
        1. 用 mplfinance 生成 K 线图
        2. 把图片传给 LLM
        3. 问：「这张图是否呈现 {pattern_type} 型态？请给出信心度。」
        """
        # MVP: 跳过LLM验证
        return {
            'confirmed': True,
            'confidence': 0.7,
            'reasoning': 'MVP版本，未启用LLM验证'
        }
    
    def generate_chart_image(self, ticker: str, days: int = 120) -> str:
        """生成 K 线图图片"""
        # MVP: 跳过图表生成
        return f"chart_{ticker}.png"
