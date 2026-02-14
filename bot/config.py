"""
Configuration module for the trading signal bot.
Contains all configurable parameters for signal generation, scoring, and anti-spam controls.
"""

import os
from typing import List

# ===== API CREDENTIALS =====
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ===== TIMEFRAMES =====
# Multi-timeframe analysis: 30m for entry, 1h for setup, 4h for regime
TIMEFRAMES = ["30m", "1h", "4h"]
PRIMARY_TIMEFRAME = "30m"  # For entry timing
SECONDARY_TIMEFRAME = "1h"  # For setup context
REGIME_TIMEFRAME = "4h"  # For main trend/structure

# ===== SYMBOLS TO MONITOR =====
SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "SOLUSDT",
    "ADAUSDT",
]

# ===== SIGNAL SCORING THRESHOLDS =====
# Lowered from 80 -> 65 to increase signal frequency while maintaining quality
CONTINUATION_MIN_SCORE = 65

# Lowered from 85 -> 70 for better reversal detection
REVERSAL_MIN_SCORE = 70

# ===== DAILY SIGNAL LIMITS =====
# Set to <= 0 for unlimited signals (no daily cap)
# Set to positive number to limit signals per day
MAX_SIGNALS_PER_DAY = 0  # Unlimited mode enabled by default

# ===== ANTI-SPAM / COOLDOWN CONTROLS =====
# Cooldown in seconds between signals for the same (symbol, direction, setup_type)
# Default: 30 minutes to avoid duplicate alerts on the same setup
SIGNAL_COOLDOWN_SECONDS = 1800  # 30 minutes

# Global cooldown between ANY signals (across all symbols)
# Default: 60 seconds to avoid notification spam
GLOBAL_SIGNAL_COOLDOWN_SECONDS = 60  # 1 minute

# Maximum number of active (unresolved) signals per symbol
# Prevents overloading on a single symbol
MAX_ACTIVE_SIGNALS_PER_SYMBOL = 3

# ===== CONFIRMATION REQUIREMENTS =====
# Require current candle to show confirmation patterns (engulfing, breakout strength, etc.)
CONFIRMATION_CANDLE_REQUIRED = True

# Minimum volume increase for breakout confirmation (vs average volume)
MIN_VOLUME_INCREASE_RATIO = 1.2

# ===== CANDLE PATTERN SCORING WEIGHTS =====
# Weight for each pattern type in overall score
PATTERN_SCORE_WEIGHT = 15  # Out of 100 total score

# Minimum wick ratio for pin bar / hammer patterns
PIN_BAR_MIN_WICK_RATIO = 2.0  # Wick should be 2x body size

# Minimum body ratio for momentum candles
MOMENTUM_MIN_BODY_RATIO = 0.6  # Body should be 60%+ of total range

# ===== TRENDLINE DETECTION =====
# Minimum number of pivot points to form a valid trendline
MIN_TRENDLINE_TOUCHES = 2

# Maximum allowed deviation from trendline (as % of price)
TRENDLINE_MAX_DEVIATION_PCT = 0.5

# Number of bars to look back for pivot detection
PIVOT_LOOKBACK_BARS = 10

# ===== STRUCTURE DETECTION =====
# Number of closed candles required for structure analysis
MIN_CLOSED_CANDLES_FOR_STRUCTURE = 50

# ATR period for volatility measurement
ATR_PERIOD = 14

# Support/Resistance zone width (as multiplier of ATR)
SR_ZONE_WIDTH_ATR = 0.5

# ===== WEBSOCKET SETTINGS =====
# Reconnect delay on WebSocket failure
WEBSOCKET_RECONNECT_DELAY = 5  # seconds

# Maximum reconnect attempts before giving up
WEBSOCKET_MAX_RECONNECT_ATTEMPTS = 10

# ===== LOGGING =====
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Log diagnostic info when signals are rejected
LOG_REJECTED_SIGNALS = True

# ===== DATA RETENTION =====
# Maximum candles to keep in memory per symbol per timeframe
MAX_CANDLES_IN_MEMORY = 500

# SQLite database for persistence
DATABASE_PATH = os.getenv("DATABASE_PATH", "bot_data.db")

# ===== SCORING COMPONENT WEIGHTS =====
# Total must equal 100
SCORE_WEIGHTS = {
    "trend_alignment": 25,      # Multi-timeframe trend alignment
    "structure": 20,            # Support/resistance, breakout quality
    "momentum": 15,             # Price momentum and volume
    "candle_patterns": 15,      # Candle pattern recognition
    "trendline": 15,            # Trendline support/resistance
    "risk_reward": 10,          # RR ratio and stop placement
}

# Validate weights sum to 100
assert sum(SCORE_WEIGHTS.values()) == 100, "Score weights must sum to 100"


def get_config_summary() -> dict:
    """Return a summary of current configuration for logging."""
    return {
        "continuation_min_score": CONTINUATION_MIN_SCORE,
        "reversal_min_score": REVERSAL_MIN_SCORE,
        "max_signals_per_day": MAX_SIGNALS_PER_DAY,
        "unlimited_mode": MAX_SIGNALS_PER_DAY <= 0,
        "signal_cooldown_seconds": SIGNAL_COOLDOWN_SECONDS,
        "global_cooldown_seconds": GLOBAL_SIGNAL_COOLDOWN_SECONDS,
        "symbols": len(SYMBOLS),
        "timeframes": TIMEFRAMES,
    }
