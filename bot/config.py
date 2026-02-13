"""Configuration module for the trading bot."""
import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Central configuration class."""
    
    # Binance API
    BINANCE_API_KEY: str = os.getenv("BINANCE_API_KEY", "")
    BINANCE_API_SECRET: str = os.getenv("BINANCE_API_SECRET", "")
    BINANCE_TESTNET: bool = os.getenv("BINANCE_TESTNET", "false").lower() == "true"
    BINANCE_BASE_URL: str = "https://fapi.binance.com" if not BINANCE_TESTNET else "https://testnet.binancefuture.com"
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    
    # Trading Parameters
    RISK_PER_TRADE: float = float(os.getenv("RISK_PER_TRADE", "1.0"))
    MAX_SIGNALS_PER_DAY: int = int(os.getenv("MAX_SIGNALS_PER_DAY", "5"))
    SCORE_THRESHOLD: int = int(os.getenv("SCORE_THRESHOLD", "75"))
    
    # Symbol Universe
    MAX_SYMBOLS_SUBSCRIBED: int = int(os.getenv("MAX_SYMBOLS_SUBSCRIBED", "40"))
    TOP_VOLUME_FETCH_LIMIT: int = int(os.getenv("TOP_VOLUME_FETCH_LIMIT", "300"))
    UNIVERSE_REFRESH_SECONDS: int = int(os.getenv("UNIVERSE_REFRESH_SECONDS", "21600"))
    ROTATION_SLOT_SECONDS: int = int(os.getenv("ROTATION_SLOT_SECONDS", "1800"))
    FIXED_SYMBOLS: List[str] = os.getenv("FIXED_SYMBOLS", "BTCUSDT,ETHUSDT,BNBUSDT").split(",")
    
    # WebSocket Configuration
    WS_MAX_STREAMS_PER_CONN: int = int(os.getenv("WS_MAX_STREAMS_PER_CONN", "50"))
    
    # Database
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "./trading_bot.db")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Candle Management
    MAX_CANDLES_PER_TIMEFRAME: int = 500
    TIMEFRAMES: List[str] = ["1d", "4h", "30m"]
    
    # Concurrency
    MAX_CONCURRENT_SCANS: int = 5
    
    # REST API Configuration
    REST_RATE_LIMIT_PER_MINUTE: int = 1200
    REST_RETRY_MAX_ATTEMPTS: int = 3
    REST_RETRY_BASE_DELAY: float = 1.0
    CACHE_TTL_EXCHANGE_INFO: int = 3600  # 1 hour
    CACHE_TTL_TICKER: int = 60  # 1 minute


config = Config()
