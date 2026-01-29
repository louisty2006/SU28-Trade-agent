"""
技術指標計算模組
"""
import pandas as pd
import numpy as np
from config import INDICATORS


def calculate_rsi(prices: pd.Series, period: int = None) -> pd.Series:
    """計算 RSI (Relative Strength Index)"""
    if period is None:
        period = INDICATORS["rsi_period"]
    
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(prices: pd.Series) -> tuple:
    """計算 MACD"""
    fast = INDICATORS["macd_fast"]
    slow = INDICATORS["macd_slow"]
    signal_period = INDICATORS["macd_signal"]
    
    ema_fast = prices.ewm(span=fast).mean()
    ema_slow = prices.ewm(span=slow).mean()
    
    macd = ema_fast - ema_slow
    signal = macd.ewm(span=signal_period).mean()
    histogram = macd - signal
    
    return macd, signal, histogram


def calculate_kd(high: pd.Series, low: pd.Series, close: pd.Series, period: int = None) -> tuple:
    """計算 KD 指標"""
    if period is None:
        period = INDICATORS["kd_period"]
    
    lowest_low = low.rolling(window=period).min()
    highest_high = high.rolling(window=period).max()
    
    rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
    k = rsv.ewm(com=2).mean()
    d = k.ewm(com=2).mean()
    
    return k, d


def calculate_bollinger(prices: pd.Series, period: int = None, std_dev: int = None) -> tuple:
    """計算布林通道"""
    if period is None:
        period = INDICATORS["bb_period"]
    if std_dev is None:
        std_dev = INDICATORS["bb_std"]
    
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    
    return upper, sma, lower


def calculate_volume_ratio(volume: pd.Series, period: int = None) -> float:
    """計算成交量比率"""
    if period is None:
        period = INDICATORS["volume_ma_period"]
    
    vol_avg = volume.rolling(window=period).mean().iloc[-1]
    current_vol = volume.iloc[-1]
    
    if vol_avg > 0:
        return current_vol / vol_avg
    return 1.0


def calculate_price_changes(prices: pd.Series) -> dict:
    """計算價格變化百分比"""
    current = prices.iloc[-1]
    
    changes = {}
    
    if len(prices) >= 2:
        changes['1d'] = ((current - prices.iloc[-2]) / prices.iloc[-2]) * 100
    else:
        changes['1d'] = 0
    
    if len(prices) >= 6:
        changes['5d'] = ((current - prices.iloc[-6]) / prices.iloc[-6]) * 100
    else:
        changes['5d'] = 0
    
    if len(prices) >= 21:
        changes['20d'] = ((current - prices.iloc[-21]) / prices.iloc[-21]) * 100
    else:
        changes['20d'] = 0
    
    return changes


def calculate_52week_metrics(high: pd.Series, low: pd.Series, current_price: float) -> dict:
    """計算 52 週高低點指標"""
    # 取最多 252 個交易日（約1年）
    period = min(252, len(high))
    
    high_52w = high.tail(period).max()
    low_52w = low.tail(period).min()
    
    from_high = ((current_price - high_52w) / high_52w) * 100
    from_low = ((current_price - low_52w) / low_52w) * 100
    
    return {
        'high_52w': high_52w,
        'low_52w': low_52w,
        'from_high': from_high,
        'from_low': from_low
    }


def get_all_indicators(hist: pd.DataFrame) -> dict:
    """
    計算所有技術指標
    
    Args:
        hist: Yahoo Finance 歷史數據 DataFrame
    
    Returns:
        包含所有指標的字典
    """
    if hist.empty or len(hist) < 20:
        return None
    
    close = hist['Close']
    high = hist['High']
    low = hist['Low']
    volume = hist['Volume']
    
    current_price = close.iloc[-1]
    
    # RSI
    rsi = calculate_rsi(close)
    rsi_val = rsi.iloc[-1] if not rsi.empty else 50
    
    # MACD
    macd, signal, histogram = calculate_macd(close)
    macd_val = macd.iloc[-1] if not macd.empty else 0
    signal_val = signal.iloc[-1] if not signal.empty else 0
    macd_cross = "金叉" if macd_val > signal_val else "死叉"
    macd_diff = macd_val - signal_val
    
    # KD
    k, d = calculate_kd(high, low, close)
    k_val = k.iloc[-1] if not k.empty else 50
    d_val = d.iloc[-1] if not d.empty else 50
    kd_cross = "金叉" if k_val > d_val else "死叉"
    
    # 布林通道
    upper, middle, lower = calculate_bollinger(close)
    bb_upper = upper.iloc[-1] if not upper.empty else current_price
    bb_lower = lower.iloc[-1] if not lower.empty else current_price
    
    if bb_upper != bb_lower:
        bb_position = ((current_price - bb_lower) / (bb_upper - bb_lower)) * 100
    else:
        bb_position = 50
    
    # 成交量
    vol_ratio = calculate_volume_ratio(volume)
    
    # 價格變化
    price_changes = calculate_price_changes(close)
    
    # 52週高低
    week_52_metrics = calculate_52week_metrics(high, low, current_price)
    
    return {
        'current_price': current_price,
        'rsi': rsi_val,
        'macd_value': macd_val,
        'macd_signal': signal_val,
        'macd_diff': macd_diff,
        'macd_cross': macd_cross,
        'k_value': k_val,
        'd_value': d_val,
        'kd_cross': kd_cross,
        'bb_position': bb_position,
        'bb_upper': bb_upper,
        'bb_lower': bb_lower,
        'volume_ratio': vol_ratio,
        'change_1d': price_changes['1d'],
        'change_5d': price_changes['5d'],
        'change_20d': price_changes['20d'],
        **week_52_metrics
    }
