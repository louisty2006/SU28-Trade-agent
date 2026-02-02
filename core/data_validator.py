"""
REISHI 霊視 v5.0 - 数据验证层（第一层防护）

目的：所有数据进入系统前必须通过验证
- 多源交叉验证
- 合理性检查
- 时间戳验证
- 异常值侦测
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd


@dataclass
class ValidationResult:
    """验证结果"""
    valid: bool
    confidence: str  # 'HIGH', 'MEDIUM', 'LOW'
    warnings: List[str]
    errors: List[str]
    data: Optional[Dict] = None


@dataclass
class CrossValidationResult:
    """交叉验证结果"""
    valid: bool
    confidence: str
    values: List[float]
    sources: List[str]
    variance_pct: float
    consensus_value: Optional[float]
    conflicts: List[str]


@dataclass
class Anomaly:
    """异常值"""
    field: str
    value: float
    z_score: float
    severity: str  # 'HIGH', 'MEDIUM', 'LOW'
    description: str


class DataValidator:
    """
    数据验证器
    所有数据必须通过验证才能进入系统
    """
    
    def __init__(self):
        self.data_sources = {
            'price': {
                'primary': 'yahoo',
                'secondary': 'finnhub',
                'fallback': 'iex'
            },
            'news': {
                'primary': 'finnhub',
                'secondary': 'yahoo_rss',
                'fallback': 'google_news'
            },
            'financials': {
                'primary': 'yahoo',
                'secondary': 'finnhub'
            }
        }
    
    def validate_price(self, ticker: str, price: float, source: str, 
                      historical_data: Optional[pd.DataFrame] = None) -> ValidationResult:
        """
        验证股价数据
        
        规则：
        1. 多源交叉验证：从至少 2 个来源获取，差异 >2% 标记冲突
        2. 合理性检查：价格 > 0，单日涨跌幅 < 30%
        3. 时间戳验证：数据不能过期
        
        返回：
        - ValidationResult(valid=True/False, confidence='HIGH'/'MEDIUM'/'LOW', warnings=[...])
        """
        warnings = []
        errors = []
        
        # 1. 基本合理性检查
        if price is None or price <= 0:
            errors.append(f"{ticker} 价格无效: {price}")
            return ValidationResult(
                valid=False,
                confidence='LOW',
                warnings=warnings,
                errors=errors
            )
        
        # 2. 单日涨跌幅检查（如果有历史数据）
        if historical_data is not None and len(historical_data) > 0:
            last_close = historical_data['Close'].iloc[-1]
            change_pct = abs((price - last_close) / last_close) * 100
            
            if change_pct > 30:
                errors.append(f"{ticker} 单日涨跌幅 {change_pct:.1f}% 超过30%，需确认")
                return ValidationResult(
                    valid=False,
                    confidence='LOW',
                    warnings=warnings,
                    errors=errors
                )
            elif change_pct > 15:
                warnings.append(f"{ticker} 单日涨跌幅 {change_pct:.1f}% 超过15%，请检查重大事件")
        
        # 3. 确定信心度
        confidence = 'HIGH'
        if warnings:
            confidence = 'MEDIUM'
        
        return ValidationResult(
            valid=True,
            confidence=confidence,
            warnings=warnings,
            errors=errors,
            data={'price': price, 'source': source}
        )
    
    def validate_volume(self, ticker: str, volume: int, 
                       historical_data: Optional[pd.DataFrame] = None) -> ValidationResult:
        """
        验证成交量
        
        规则：
        1. volume >= 0
        2. volume > 平均 10 倍 → 警告，需确认是否有事件
        """
        warnings = []
        errors = []
        
        # 1. 基本检查
        if volume is None or volume < 0:
            errors.append(f"{ticker} 成交量无效: {volume}")
            return ValidationResult(
                valid=False,
                confidence='LOW',
                warnings=warnings,
                errors=errors
            )
        
        # 2. 异常成交量检查
        if historical_data is not None and len(historical_data) > 0:
            avg_volume = historical_data['Volume'].mean()
            
            if volume == 0:
                warnings.append(f"{ticker} 成交量为0，可能停牌或数据错误")
            elif volume > avg_volume * 10:
                warnings.append(f"{ticker} 成交量 {volume:,} 超过平均 {avg_volume:,.0f} 的10倍，需确认事件")
        
        confidence = 'HIGH' if not warnings else 'MEDIUM'
        
        return ValidationResult(
            valid=True,
            confidence=confidence,
            warnings=warnings,
            errors=errors,
            data={'volume': volume}
        )
    
    def validate_financial(self, ticker: str, data: dict) -> ValidationResult:
        """
        验证财务数据
        
        规则：
        1. 营收不能为负
        2. 毛利率在 -50% ~ 100%
        3. P/E 异常值（负数或 > 1000）标记
        """
        warnings = []
        errors = []
        
        # 1. 营收检查
        revenue = data.get('revenue')
        if revenue is not None and revenue < 0:
            errors.append(f"{ticker} 营收为负: {revenue}")
        
        # 2. 毛利率检查
        gross_margin = data.get('gross_margin')
        if gross_margin is not None:
            if gross_margin < -50 or gross_margin > 100:
                errors.append(f"{ticker} 毛利率异常: {gross_margin}%")
        
        # 3. P/E 检查
        pe_ratio = data.get('pe_ratio')
        if pe_ratio is not None:
            if pe_ratio < 0:
                warnings.append(f"{ticker} P/E为负 {pe_ratio}，公司可能亏损")
            elif pe_ratio > 1000:
                warnings.append(f"{ticker} P/E {pe_ratio} 过高，可能数据错误或极端估值")
        
        valid = len(errors) == 0
        confidence = 'HIGH' if not warnings else 'MEDIUM'
        
        return ValidationResult(
            valid=valid,
            confidence=confidence,
            warnings=warnings,
            errors=errors,
            data=data
        )
    
    def cross_validate(self, ticker: str, field: str, 
                      values_sources: List[Tuple[float, str]]) -> CrossValidationResult:
        """
        多源交叉验证
        
        从多个数据源获取同一数据，比对差异
        - 差异 < 0.5% → HIGH confidence
        - 差异 0.5-2% → MEDIUM confidence + 警告
        - 差异 > 2% → 标记冲突，需人工确认
        """
        if len(values_sources) < 2:
            return CrossValidationResult(
                valid=False,
                confidence='LOW',
                values=[],
                sources=[],
                variance_pct=0,
                consensus_value=None,
                conflicts=[f"{ticker} {field}: 数据源不足，需要至少2个"]
            )
        
        values = [v for v, _ in values_sources]
        sources = [s for _, s in values_sources]
        
        # 计算差异
        mean_value = np.mean(values)
        max_diff = max(abs(v - mean_value) for v in values)
        variance_pct = (max_diff / mean_value * 100) if mean_value != 0 else 0
        
        conflicts = []
        
        # 判断信心度
        if variance_pct < 0.5:
            confidence = 'HIGH'
            valid = True
        elif variance_pct < 2:
            confidence = 'MEDIUM'
            valid = True
            conflicts.append(f"{ticker} {field}: 数据源差异 {variance_pct:.2f}%，需注意")
        else:
            confidence = 'LOW'
            valid = False
            conflicts.append(f"{ticker} {field}: 数据源差异 {variance_pct:.2f}% 超过2%，需人工确认")
            for i, (v, s) in enumerate(values_sources):
                conflicts.append(f"  来源 {s}: {v}")
        
        return CrossValidationResult(
            valid=valid,
            confidence=confidence,
            values=values,
            sources=sources,
            variance_pct=variance_pct,
            consensus_value=mean_value if valid else None,
            conflicts=conflicts
        )
    
    def detect_anomaly(self, ticker: str, metrics: dict, 
                      historical_metrics: Optional[pd.DataFrame] = None) -> List[Anomaly]:
        """
        异常值偵測
        
        使用 Z-Score：
        - |Z| > 3 → 高度异常
        - |Z| > 2 → 中度异常
        """
        anomalies = []
        
        if historical_metrics is None or len(historical_metrics) < 10:
            return anomalies
        
        for field, value in metrics.items():
            if field not in historical_metrics.columns:
                continue
            
            if value is None or pd.isna(value):
                continue
            
            # 计算 Z-Score
            hist_values = historical_metrics[field].dropna()
            if len(hist_values) < 3:
                continue
            
            mean = hist_values.mean()
            std = hist_values.std()
            
            if std == 0:
                continue
            
            z_score = (value - mean) / std
            
            # 判断异常程度
            if abs(z_score) > 3:
                anomalies.append(Anomaly(
                    field=field,
                    value=value,
                    z_score=z_score,
                    severity='HIGH',
                    description=f"{ticker} {field} {value:.2f} 高度异常 (Z={z_score:.1f})"
                ))
            elif abs(z_score) > 2:
                anomalies.append(Anomaly(
                    field=field,
                    value=value,
                    z_score=z_score,
                    severity='MEDIUM',
                    description=f"{ticker} {field} {value:.2f} 中度异常 (Z={z_score:.1f})"
                ))
        
        return anomalies
    
    def validate_timestamp(self, timestamp: datetime, 
                         trading_hours: bool = False) -> ValidationResult:
        """
        时间戳验证
        
        规则：
        - 交易时段内：数据延迟 > 30 分钟 → 警告
        - 交易时段内：数据延迟 > 2 小时 → 拒绝使用
        - 非交易时段：应该是最近收盘数据
        """
        warnings = []
        errors = []
        
        now = datetime.now()
        delay = (now - timestamp).total_seconds() / 60  # 分钟
        
        if trading_hours:
            if delay > 120:
                errors.append(f"数据延迟 {delay:.0f} 分钟超过2小时，拒绝使用")
                return ValidationResult(
                    valid=False,
                    confidence='LOW',
                    warnings=warnings,
                    errors=errors
                )
            elif delay > 30:
                warnings.append(f"数据延迟 {delay:.0f} 分钟超过30分钟")
        
        confidence = 'HIGH' if not warnings else 'MEDIUM'
        
        return ValidationResult(
            valid=True,
            confidence=confidence,
            warnings=warnings,
            errors=errors,
            data={'timestamp': timestamp, 'delay_minutes': delay}
        )
    
    def validate_all(self, ticker: str, data: dict, 
                    historical_data: Optional[pd.DataFrame] = None) -> ValidationResult:
        """
        完整验证一个股票的所有数据
        """
        all_warnings = []
        all_errors = []
        confidence_levels = []
        
        # 1. 价格验证
        if 'price' in data:
            price_result = self.validate_price(
                ticker, 
                data['price'], 
                data.get('price_source', 'unknown'),
                historical_data
            )
            all_warnings.extend(price_result.warnings)
            all_errors.extend(price_result.errors)
            confidence_levels.append(price_result.confidence)
        
        # 2. 成交量验证
        if 'volume' in data:
            volume_result = self.validate_volume(
                ticker,
                data['volume'],
                historical_data
            )
            all_warnings.extend(volume_result.warnings)
            all_errors.extend(volume_result.errors)
            confidence_levels.append(volume_result.confidence)
        
        # 3. 财务数据验证
        financial_fields = ['revenue', 'gross_margin', 'pe_ratio']
        financial_data = {k: data.get(k) for k in financial_fields if k in data}
        if financial_data:
            financial_result = self.validate_financial(ticker, financial_data)
            all_warnings.extend(financial_result.warnings)
            all_errors.extend(financial_result.errors)
            confidence_levels.append(financial_result.confidence)
        
        # 确定总体信心度
        if 'HIGH' in confidence_levels and len([c for c in confidence_levels if c == 'LOW']) == 0:
            overall_confidence = 'HIGH'
        elif 'LOW' in confidence_levels:
            overall_confidence = 'LOW'
        else:
            overall_confidence = 'MEDIUM'
        
        valid = len(all_errors) == 0
        
        return ValidationResult(
            valid=valid,
            confidence=overall_confidence,
            warnings=all_warnings,
            errors=all_errors,
            data=data
        )
