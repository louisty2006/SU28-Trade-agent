"""
股票掃描系統 v4 - 配置文件（美股專用）

🎯 三數據源強制驗證系統
- 每支股票必須有 3 個有效數據源
- 主力：Yahoo (無限) + IEX (1,666/天)
- 備用池：9 個數據源

📊 每日總額度（理論值）：
  Yahoo Finance: 無限制 ✅
  IEX Cloud:     1,666
  Twelve Data:     800
  Finnhub:       1,440
  Tiingo:          500
  Intrinio:        500
  FMP:             250
  Polygon:         250
  Quandl:           50
  Alpha Vantage:    25
  Marketstack:       3
  ─────────────────────
  總計:         5,484/天（不含 Yahoo）
  
💡 實際可處理：
  - Stage 1: 10,000+ 支（僅 Yahoo）
  - Stage 2: 1,000 支（三源驗證，有充足備用）

🔗 Orchestrator 對接：
  - 支援讀取 config.json 動態調參
  - 輸出 backtest_summary.csv 供 Orchestrator 評分
"""
import os
import json
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# API Keys - 三數據源強制驗證 + 多重備用源
# ============================================================================
# 主力數據源（必須，優先使用）
# 1. Yahoo Finance - 不需要 API Key (無限制) ✅
IEX_CLOUD_API_KEY = os.getenv("IEX_CLOUD_API_KEY", "")  # 2. IEX Cloud (50,000/月 ≈ 1,666/天) ✅

# 備用數據源池（按順序自動補位）
FMP_API_KEY = os.getenv("FMP_API_KEY", "")  # 3. FMP (250/天)
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "")  # 4. Twelve Data (800/天)
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "")  # 5. Polygon (250/天)
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")  # 6. Finnhub (60/分鐘 ≈ 1,440/天)
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")  # 7. Alpha Vantage (25/天)
MARKETSTACK_API_KEY = os.getenv("MARKETSTACK_API_KEY", "")  # 8. Marketstack (100/月 ≈ 3/天)
YAHOO_FINANCE_API_KEY = os.getenv("YAHOO_FINANCE_API_KEY", "")  # 9. Yahoo Finance Premium (可選)
TIINGO_API_KEY = os.getenv("TIINGO_API_KEY", "")  # 10. Tiingo (500/天)
INTRINIO_API_KEY = os.getenv("INTRINIO_API_KEY", "")  # 11. Intrinio (500/天)
QUANDL_API_KEY = os.getenv("QUANDL_API_KEY", "")  # 12. Quandl/NASDAQ Data Link (50/天)

# ============================================================================
# Stage 1: 快速篩選配置
# ============================================================================
STAGE1_CONFIG = {
    "max_workers": 20,  # 並行線程數
    "target_output": 1000,  # 輸出 Top 1000
    "min_price": 1.0,  # 最低價格過濾
    "min_volume": 100000,  # 最低成交量
    "min_market_cap": 100_000_000,  # 最低市值 (100M)
}

# ============================================================================
# Stage 2: 深度驗證配置（測試階段：兩數據源對照即可，省 token/資源）
# ============================================================================
STAGE2_CONFIG = {
    "max_workers": 30,  # 並行線程數
    "target_output": 250,  # 輸出 Top 250
    
    # 測試階段：對照互測改為兩網站即可（省 token/資源）
    "required_sources": 2,  # 兩數據源對照即通過
    
    # 數據源優先順序（按可靠性 + 免費額度排序）
    "data_sources_priority": [
        "yahoo",      # 1. Yahoo Finance (無限制) - 必用
        "iex",        # 2. IEX Cloud (1,666/天) - 優先
        "twelve",     # 3. Twelve Data (800/天)
        "tiingo",     # 4. Tiingo (500/天)
        "intrinio",   # 5. Intrinio (500/天)
        "finnhub",    # 6. Finnhub (1,440/天)
        "fmp",        # 7. FMP (250/天)
        "polygon",    # 8. Polygon (250/天)
        "quandl",     # 9. Quandl (50/天)
        "alpha",      # 10. Alpha Vantage (25/天)
        "marketstack",# 11. Marketstack (3/天)
    ],
    
    # 數據源配置（每日免費額度）
    "sources_config": {
        "yahoo": {
            "enabled": True, 
            "daily_limit": 999999,  # 無限制
            "required": True,  # 必須使用
            "reliability": 0.99,
        },
        "iex": {
            "enabled": True, 
            "daily_limit": 1666,  # 50,000/月
            "required": False,
            "reliability": 0.95,
        },
        "twelve": {
            "enabled": True, 
            "daily_limit": 800,
            "required": False,
            "reliability": 0.90,
        },
        "tiingo": {
            "enabled": True, 
            "daily_limit": 500,
            "required": False,
            "reliability": 0.90,
        },
        "intrinio": {
            "enabled": True, 
            "daily_limit": 500,
            "required": False,
            "reliability": 0.85,
        },
        "finnhub": {
            "enabled": True, 
            "daily_limit": 1440,  # 60/min
            "required": False,
            "reliability": 0.85,
        },
        "fmp": {
            "enabled": True, 
            "daily_limit": 250,
            "required": False,
            "reliability": 0.90,
        },
        "polygon": {
            "enabled": True, 
            "daily_limit": 250,
            "required": False,
            "reliability": 0.85,
        },
        "quandl": {
            "enabled": True, 
            "daily_limit": 50,
            "required": False,
            "reliability": 0.80,
        },
        "alpha": {
            "enabled": True, 
            "daily_limit": 25,
            "required": False,
            "reliability": 0.75,
        },
        "marketstack": {
            "enabled": True, 
            "daily_limit": 3,  # 100/月
            "required": False,
            "reliability": 0.70,
        },
    },
    
    # 智能分配策略
    "smart_allocation": True,  # 自動根據剩餘額度智能分配
    "balance_load": True,  # 均衡使用各數據源
    "prioritize_reliability": True,  # 優先使用可靠性高的源
    
    # 失敗處理
    "retry_on_failure": True,  # 失敗時自動切換備用源
    "max_retries_per_source": 2,  # 每個數據源最多重試次數
    "skip_if_quota_exceeded": True,  # 額度用完自動跳過
    "fallback_to_next_source": True,  # 自動切換到下一個備用源
    
    # 數據一致性檢查（測試階段：兩源一致即可）
    "data_consistency_check": True,
    "max_variance_pct": 20,  # PE/PB/ROE 允許 20% 差異
    "flag_if_inconsistent": True,  # 標記異常數據
    "require_majority_consensus": True,  # 兩源時 2/2 一致即通過
    
    # API 限速
    "api_delay": 0.15,  # API 調用延遲（秒）
    "respect_rate_limits": True,  # 嚴格遵守速率限制
    "rate_limit_buffer": 0.9,  # 只用 90% 額度，留 10% 緩衝
}

# ============================================================================
# Stage 3: LLM 討論配置 (後續實作)
# ============================================================================
STAGE3_CONFIG = {
    "target_output": 20,
    "llm_providers": ["groq", "openrouter"],  # 免費 LLM
    "discussion_rounds": 3,
}

# ============================================================================
# 技術指標參數
# ============================================================================
INDICATORS = {
    "rsi_period": 14,
    "rsi_oversold": 30,
    "rsi_overbought": 70,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "kd_period": 14,
    "bb_period": 20,
    "bb_std": 2,
    "volume_ma_period": 20,
}

# ============================================================================
# 評分權重
# ============================================================================
STAGE1_WEIGHTS = {
    "rsi": 0.20,
    "macd": 0.15,
    "kd": 0.12,
    "bollinger": 0.10,
    "volume": 0.08,
    "price_momentum": 0.15,
    "from_high": 0.10,
    "from_low": 0.10,
}

STAGE2_WEIGHTS = {
    "stage1_score": 0.30,  # 繼承 Stage 1 評分
    "financial_health": 0.25,
    "valuation": 0.20,
    "growth": 0.15,
    "news_sentiment": 0.10,
}

# ============================================================================
# 股票池路徑
# ============================================================================
STOCK_UNIVERSE_PATHS = [
    "COMPLETE_ALL_STOCKS_FINAL.csv",
    "data/COMPLETE_ALL_STOCKS_FINAL.csv",
    "/mnt/user-data/uploads/COMPLETE_ALL_STOCKS_FINAL.csv",
]

# ============================================================================
# 報告輸出
# ============================================================================
REPORTS_DIR = "reports"
STAGE1_DIR = f"{REPORTS_DIR}/stage1"
STAGE2_DIR = f"{REPORTS_DIR}/stage2"
STAGE3_DIR = f"{REPORTS_DIR}/stage3"

# ============================================================================
# 允許的交易所（僅美股）
# ============================================================================
ALLOWED_EXCHANGES = {
    # 美股交易所
    'NMS', 'NCM', 'NGM', 'NAS', 'NSQ',  # NASDAQ 系列
    'NYQ', 'NYS',  # NYSE 系列
    'ASE', 'AMEX',  # AMEX
}

# ============================================================================
# 數據源 URLs
# ============================================================================
# 主力數據源
YAHOO_FINANCE_BASE_URL = "https://query1.finance.yahoo.com"  # 內建於 yfinance
IEX_CLOUD_BASE_URL = "https://cloud.iexapis.com/stable"

# 備用數據源
FMP_BASE_URL = "https://financialmodeprep.com/api/v3"
TWELVE_DATA_BASE_URL = "https://api.twelvedata.com"
POLYGON_BASE_URL = "https://api.polygon.io"
TIINGO_BASE_URL = "https://api.tiingo.com"
INTRINIO_BASE_URL = "https://api-v2.intrinio.com"
FINNHUB_BASE_URL = "https://finnhub.io/api/v1"
QUANDL_BASE_URL = "https://data.nasdaq.com/api/v3"
ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"
MARKETSTACK_BASE_URL = "https://api.marketstack.com/v1"

# ---------------------------------------------------------------------------
# REISHI 品牌（霊視）- 報告與 log 檔名（全面使用 REIKAN_ 前綴，以保持兼容性）
# ---------------------------------------------------------------------------
REIKAN_PREFIX = "REIKAN_"  # 保持檔名前綴（避免破壞現有報告）
REIKAN_RUN_LOG = REIKAN_PREFIX + "run.log"
REIKAN_STAGE1_CSV = REIKAN_PREFIX + "stage1_results.csv"
REIKAN_STAGE2_CSV = REIKAN_PREFIX + "stage2_results.csv"
REIKAN_STAGE2_HTML = REIKAN_PREFIX + "stage2_report.html"
REIKAN_STAGE3_CSV = REIKAN_PREFIX + "stage3_top20.csv"
REIKAN_STAGE3_JSON = REIKAN_PREFIX + "stage3_discussion.json"
REIKAN_DAILY_TXT = REIKAN_PREFIX + "daily_report.txt"
REIKAN_DAILY_JSON = REIKAN_PREFIX + "daily_report.json"

# 品牌名稱（顯示用）
APP_NAME = "REISHI Stock Scanner"
APP_NAME_JP = "霊視"
VERSION = "5.0"

# ---------------------------------------------------------------------------
# 回測模擬（365 天逐日）
# ---------------------------------------------------------------------------
BACKTEST_INITIAL_CASH = 40_000.0       # 回測 Day0 起動資本（HKD）- Orchestrator 統一基準
BACKTEST_PCT_PER_NEW_ENTRY = 0.20      # 每筆新買入動用現金比例（最多 3 筆）
BACKTEST_ADD_PCT = 0.10                # 加碼時動用現金比例
BACKTEST_REDUCE_PCT = 0.50              # 減碼時賣出持倉比例

# ---------------------------------------------------------------------------
# Orchestrator 對接：動態參數讀取
# ---------------------------------------------------------------------------
def load_orchestrator_config(config_path: str = "config.json"):
    """
    讀取 Orchestrator 動態生成的 config.json
    若檔案不存在或讀取失敗，返回 None（使用預設配置）
    
    預期 JSON 結構範例：
    {
        "stage1_weights": {
            "rsi": 0.20,
            "macd": 0.15,
            ...
        },
        "stage2_weights": {
            "stage1_score": 0.30,
            "financial_health": 0.25,
            ...
        },
        "backtest_initial_cash": 40000.0,
        ...
    }
    """
    if not os.path.exists(config_path):
        return None
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        return config
    except (json.JSONDecodeError, IOError) as e:
        print(f"⚠️ 讀取 {config_path} 失敗: {e}")
        return None


def apply_orchestrator_config():
    """
    應用 Orchestrator 配置（若存在）
    自動覆寫全局配置變數
    """
    global STAGE1_WEIGHTS, STAGE2_WEIGHTS, BACKTEST_INITIAL_CASH
    global BACKTEST_PCT_PER_NEW_ENTRY, BACKTEST_ADD_PCT, BACKTEST_REDUCE_PCT
    
    config = load_orchestrator_config()
    if not config:
        return False
    
    print("🔗 偵測到 Orchestrator config.json，正在應用動態參數...")
    
    # 應用 Stage 1 權重
    if "stage1_weights" in config:
        STAGE1_WEIGHTS.update(config["stage1_weights"])
        print(f"   ✓ Stage 1 權重已更新")
    
    # 應用 Stage 2 權重
    if "stage2_weights" in config:
        STAGE2_WEIGHTS.update(config["stage2_weights"])
        print(f"   ✓ Stage 2 權重已更新")
    
    # 應用回測參數
    if "backtest_initial_cash" in config:
        BACKTEST_INITIAL_CASH = float(config["backtest_initial_cash"])
        print(f"   ✓ 初始資金已更新: {BACKTEST_INITIAL_CASH:,.0f} HKD")
    
    if "backtest_pct_per_new_entry" in config:
        BACKTEST_PCT_PER_NEW_ENTRY = float(config["backtest_pct_per_new_entry"])
    
    if "backtest_add_pct" in config:
        BACKTEST_ADD_PCT = float(config["backtest_add_pct"])
    
    if "backtest_reduce_pct" in config:
        BACKTEST_REDUCE_PCT = float(config["backtest_reduce_pct"])
    
    print("🔗 Orchestrator 配置應用完成\n")
    return True
