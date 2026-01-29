"""
評分邏輯模組
"""
from config import STAGE1_WEIGHTS, INDICATORS


def calculate_stage1_score(indicators: dict) -> float:
    """
    Stage 1 快速評分
    
    評分範圍：0-100
    基於技術指標的綜合評分
    """
    score = 50  # 基礎分
    
    rsi = indicators.get('rsi', 50)
    macd_diff = indicators.get('macd_diff', 0)
    macd_cross = indicators.get('macd_cross', '')
    k_val = indicators.get('k_value', 50)
    d_val = indicators.get('d_value', 50)
    bb_position = indicators.get('bb_position', 50)
    vol_ratio = indicators.get('volume_ratio', 1)
    from_high = indicators.get('from_high', 0)
    change_5d = indicators.get('change_5d', 0)
    
    # === RSI 評分 (權重 20%) ===
    rsi_score = 0
    if 30 <= rsi <= 40:  # 超賣區反彈機會
        rsi_score = 20
    elif rsi < 30:  # 深度超賣
        rsi_score = 15
    elif 40 < rsi <= 50:  # 中性偏多
        rsi_score = 10
    elif rsi > 70:  # 超買風險
        rsi_score = -10
    
    # === MACD 評分 (權重 15%) ===
    macd_score = 0
    if macd_diff > 0:
        macd_score = 8
        # 檢查是否剛金叉
        if macd_cross == "金叉":
            macd_score += 7  # 總共 15
    elif macd_diff < 0 and macd_cross == "死叉":
        macd_score = -5
    
    # === KD 評分 (權重 12%) ===
    kd_score = 0
    if k_val < 30 and k_val > d_val:  # 低檔金叉
        kd_score = 12
    elif k_val < 20:  # 超賣
        kd_score = 8
    elif k_val > 80:  # 超買
        kd_score = -5
    
    # === 布林通道評分 (權重 10%) ===
    bb_score = 0
    if bb_position < 20:  # 接近下軌
        bb_score = 10
    elif bb_position < 30:
        bb_score = 5
    elif bb_position > 80:  # 接近上軌
        bb_score = -5
    
    # === 成交量評分 (權重 8%) ===
    vol_score = 0
    if vol_ratio > 2:  # 爆量
        vol_score = 8
    elif vol_ratio > 1.5:
        vol_score = 5
    elif vol_ratio < 0.5:  # 量縮
        vol_score = -3
    
    # === 價格動量評分 (權重 15%) ===
    momentum_score = 0
    if -15 < change_5d < -5:  # 回調不深
        momentum_score = 10
    elif change_5d < -20:  # 深度回調
        momentum_score = 5
    elif change_5d > 10:  # 強勢上漲
        momentum_score = 8
    elif change_5d < -30:  # 崩跌風險
        momentum_score = -10
    
    # === 距離52週高點評分 (權重 10%) ===
    high_score = 0
    if from_high < -30:  # 距離高點較遠
        high_score = 10
    if from_high < -40:
        high_score += 5
    elif from_high > -5:  # 接近高點
        high_score = -5
    
    # 總分計算
    total_score = (
        score +
        rsi_score +
        macd_score +
        kd_score +
        bb_score +
        vol_score +
        momentum_score +
        high_score
    )
    
    # 限制在 0-100
    return max(0, min(100, total_score))


def calculate_stage2_score(stage1_score: float, financial_data: dict) -> float:
    """
    Stage 2 深度評分
    
    結合 Stage 1 技術分析 + Stage 2 財務驗證
    """
    # 基礎分數繼承 Stage 1 (權重 30%)
    score = stage1_score * 0.30
    
    # === 財務健康度評分 (權重 25%) ===
    health_score = 0
    
    # 流動比率
    current_ratio = financial_data.get('current_ratio', 1)
    if current_ratio > 2:
        health_score += 8
    elif current_ratio > 1.5:
        health_score += 5
    elif current_ratio < 1:
        health_score -= 5
    
    # 負債比率
    debt_to_equity = financial_data.get('debt_to_equity', 0)
    if debt_to_equity < 0.5:
        health_score += 8
    elif debt_to_equity < 1:
        health_score += 4
    elif debt_to_equity > 2:
        health_score -= 5
    
    # ROE
    roe = financial_data.get('roe', 0)
    if roe > 15:
        health_score += 9
    elif roe > 10:
        health_score += 5
    elif roe < 0:
        health_score -= 10
    
    # === 估值評分 (權重 20%) ===
    valuation_score = 0
    
    pe_ratio = financial_data.get('pe_ratio', 0)
    if 0 < pe_ratio < 15:  # 低估
        valuation_score += 10
    elif 15 <= pe_ratio < 25:  # 合理
        valuation_score += 5
    elif pe_ratio > 40:  # 高估
        valuation_score -= 5
    
    pb_ratio = financial_data.get('pb_ratio', 0)
    if 0 < pb_ratio < 1:  # 破淨值
        valuation_score += 10
    elif 1 <= pb_ratio < 3:
        valuation_score += 5
    
    # === 成長性評分 (權重 15%) ===
    growth_score = 0
    
    revenue_growth = financial_data.get('revenue_growth', 0)
    if revenue_growth > 20:
        growth_score += 8
    elif revenue_growth > 10:
        growth_score += 5
    elif revenue_growth < -10:
        growth_score -= 5
    
    earnings_growth = financial_data.get('earnings_growth', 0)
    if earnings_growth > 20:
        growth_score += 7
    elif earnings_growth > 10:
        growth_score += 4
    
    # === 新聞情緒評分 (權重 10%) ===
    sentiment_score = financial_data.get('news_sentiment', 0) * 10
    
    # 總分
    total = (
        score +
        (health_score * 0.25) +
        (valuation_score * 0.20) +
        (growth_score * 0.15) +
        (sentiment_score * 0.10)
    )
    
    return max(0, min(100, total))


def get_score_explanation(score: float, indicators: dict = None) -> str:
    """生成評分說明"""
    if score >= 80:
        level = "🔥 強力推薦"
        desc = "技術面和基本面均表現優秀"
    elif score >= 70:
        level = "⭐ 值得關注"
        desc = "多項指標表現良好"
    elif score >= 60:
        level = "👀 可以觀望"
        desc = "部分指標符合條件"
    elif score >= 50:
        level = "⚠️ 謹慎評估"
        desc = "指標表現一般"
    else:
        level = "❌ 暫不推薦"
        desc = "多項指標不理想"
    
    return f"{level} - {desc}"
