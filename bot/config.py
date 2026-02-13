"""
Configuration module for Institutional Price Action Swing Bot v2
"""
import os
from typing import List

# ==================== API Configuration ====================
BINANCE_FUTURES_WS_BASE = "wss://fstream.binance.com"
BINANCE_FUTURES_REST_BASE = "https://fapi.binance.com"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ==================== Symbol Configuration ====================
# Fixed symbols that are always monitored
FIXED_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "XAUUSDT", "TONUSDT", 
    "TRBUSDT", "TRIAUSDT", "NEARUSDT", "SOLUSDT", "ETHFIUSDT",
    "1000SHIBUSDT", "MSTRUSDT"
]

# Symbol rotation and subscription limits
# Max concurrent subscriptions for VPS stability
# 40 chosen based on: 180 streams/conn limit, 3 timeframes = 60 symbols max per conn
# Using 40 provides comfortable margin and works well on 1-2GB RAM VPS
MAX_SYMBOLS_SUBSCRIBED = 40
TOP_VOLUME_COUNT = 300  # Top volume symbols to track
SYMBOL_ROTATION_INTERVAL = 30 * 60  # 30 minutes in seconds
UNIVERSE_REFRESH_INTERVAL = 6 * 60 * 60  # 6 hours in seconds

# ==================== WebSocket Configuration ====================
WS_MAX_STREAMS_PER_CONN = 180  # Max streams per WebSocket connection
WS_RECONNECT_DELAY = 5  # Seconds before reconnecting
WS_PING_INTERVAL = 30  # Seconds between pings

# ==================== Data Configuration ====================
TIMEFRAMES = ["1d", "4h", "30m"]
MAX_CANDLES_STORED = 500  # Per timeframe per symbol
CONCURRENT_SYMBOL_SCANS = 5  # Semaphore limit for parallel processing

# ==================== REST API Configuration ====================
REST_RATE_LIMIT_DELAY = 0.1  # Minimum delay between requests
REST_MAX_RETRIES = 3
REST_RETRY_BACKOFF_BASE = 2  # Exponential backoff base
REST_CACHE_TTL = 60  # Cache TTL in seconds

# ==================== Market Regime Configuration ====================
class RegimeType:
    TRENDING_CONTINUATION = "TRENDING_CONTINUATION"
    CONFIRMED_REVERSAL = "CONFIRMED_REVERSAL"
    SIDEWAY = "SIDEWAY"

# Sideway detection thresholds
SIDEWAY_ATR_THRESHOLD = 0.005  # Low ATR threshold
SIDEWAY_DISPLACEMENT_THRESHOLD = 1.5  # No displacement > 1.5 ATR

# ==================== Trading Logic Configuration ====================
# Pullback thresholds
CONTINUATION_PULLBACK_MAX = 0.50  # Max 50% pullback for continuation
REVERSAL_PULLBACK_MIN = 0.50  # Min 50% pullback for reversal

# Displacement validation
DISPLACEMENT_ATR_MULTIPLE = 1.5  # Body must be > 1.5 ATR
DISPLACEMENT_VOLUME_MULTIPLE = 1.2  # Volume must be > 1.2x average

# Premium/Discount zones
PREMIUM_DISCOUNT_EQ = 0.50  # 50% equilibrium

# ==================== Scoring Configuration ====================
# Continuation setup weights (total should be 100)
CONTINUATION_WEIGHTS = {
    "structure": 25,
    "pullback": 20,
    "premium_discount": 15,
    "liquidity": 15,
    "ob_fvg": 10,
    "displacement": 10,
    "volatility": 5
}
CONTINUATION_MIN_SCORE = 80

# Reversal setup weights (total should be 100)
REVERSAL_WEIGHTS = {
    "external_sweep": 25,
    "choch_4h": 25,
    "displacement": 15,
    "sr_strength": 15,
    "pattern": 10,
    "volatility": 5,
    "premium_discount": 5
}
REVERSAL_MIN_SCORE = 85

# ==================== Risk Management Configuration ====================
RISK_PER_TRADE = 0.01  # 1% risk per trade
TP1_RR = 1.0  # 1R for TP1
TP2_RR = 2.0  # 2R for TP2 (internal liquidity)
TP3_RR = 3.0  # 3R for TP3 (external liquidity)
MIN_RR_RATIO = 2.5  # Minimum risk/reward ratio

MAX_SIGNALS_PER_DAY = 3
MAX_TRADES_PER_SYMBOL = 1  # One active trade per symbol
CANDLE_COOLDOWN = 4  # Number of candles to wait after a signal

# ==================== Memory Engine Configuration ====================
MEMORY_ROLLING_WINDOW = 20  # Last 20 trades for rolling stats
MEMORY_DB_PATH = "data/memory.db"

# Memory adjustment rules
MEMORY_LOW_WR_THRESHOLD = 0.55  # 55% winrate threshold
MEMORY_SCORE_INCREASE = 5  # Score increase when WR is low
MEMORY_CONSECUTIVE_LOSS_LIMIT = 3  # Pause after 3 consecutive losses
MEMORY_PAUSE_DURATION = 12 * 60 * 60  # 12 hours pause

MEMORY_DRAWDOWN_MODERATE = 0.05  # 5% drawdown
MEMORY_DRAWDOWN_HIGH = 0.08  # 8% drawdown
MEMORY_REDUCED_SIGNALS = 2
MEMORY_REDUCED_RISK = 0.005  # 0.5% risk

MEMORY_SYMBOL_LOSS_LIMIT = 2  # Consecutive losses per symbol
MEMORY_SYMBOL_COOLDOWN = 24 * 60 * 60  # 24 hours
MEMORY_SYMBOL_WR_THRESHOLD = 0.50  # 50% winrate
MEMORY_SYMBOL_WR_WINDOW = 10  # Last 10 trades per symbol

MEMORY_REVERSAL_WR_THRESHOLD = 0.45  # 45% reversal winrate
MEMORY_REVERSAL_DISABLE_DURATION = 48 * 60 * 60  # 48 hours
MEMORY_TRENDING_WR_THRESHOLD = 0.65  # 65% trending winrate

# ==================== Trade Tracking Configuration ====================
TRADE_DB_PATH = "data/trades.db"
OUTCOMES_CSV_PATH = "data/outcomes.csv"
OUTCOMES_CHECK_INTERVAL = 60 * 60  # Check for new outcomes every hour

# Outcome mapping to R multiples
OUTCOME_TO_R = {
    "TP1": 1.0,
    "TP2": 2.0,
    "TP3": 3.0,
    "SL": -1.0
}

# ==================== Notification Configuration ====================
NOTIFICATION_SOURCE = "Posiya Tú"
NOTIFICATION_QUOTE = "Xu hướng là bạn cho đến khi xu hướng đảo chiều."

# ==================== Logging Configuration ====================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = "data/bot.log"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 5

# ==================== Technical Indicators Configuration ====================
ATR_PERIOD = 14
VOLUME_MA_PERIOD = 20
