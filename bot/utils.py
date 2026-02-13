"""
Utility functions for the trading bot
"""
import asyncio
import logging
import random
import time
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import deque
import aiohttp

logger = logging.getLogger(__name__)


def calculate_atr(candles: deque, period: int = 14) -> float:
    """Calculate Average True Range"""
    if len(candles) < period + 1:
        return 0.0
    
    true_ranges = []
    candles_list = list(candles)
    
    for i in range(1, min(len(candles_list), period + 1)):
        high = float(candles_list[-i]['high'])
        low = float(candles_list[-i]['low'])
        prev_close = float(candles_list[-i-1]['close'])
        
        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )
        true_ranges.append(tr)
    
    return sum(true_ranges) / len(true_ranges) if true_ranges else 0.0


def calculate_volume_ma(candles: deque, period: int = 20) -> float:
    """Calculate volume moving average"""
    if len(candles) < period:
        return 0.0
    
    candles_list = list(candles)[-period:]
    volumes = [float(c['volume']) for c in candles_list]
    return sum(volumes) / len(volumes) if volumes else 0.0


def is_bullish_candle(candle: Dict) -> bool:
    """Check if candle is bullish"""
    return float(candle['close']) > float(candle['open'])


def is_bearish_candle(candle: Dict) -> bool:
    """Check if candle is bearish"""
    return float(candle['close']) < float(candle['open'])


def candle_body_size(candle: Dict) -> float:
    """Calculate candle body size"""
    return abs(float(candle['close']) - float(candle['open']))


def candle_range(candle: Dict) -> float:
    """Calculate candle high-low range"""
    return float(candle['high']) - float(candle['low'])


def candle_wick_upper(candle: Dict) -> float:
    """Calculate upper wick size"""
    open_price = float(candle['open'])
    close_price = float(candle['close'])
    high = float(candle['high'])
    return high - max(open_price, close_price)


def candle_wick_lower(candle: Dict) -> float:
    """Calculate lower wick size"""
    open_price = float(candle['open'])
    close_price = float(candle['close'])
    low = float(candle['low'])
    return min(open_price, close_price) - low


async def async_retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True
) -> Any:
    """
    Retry an async function with exponential backoff and jitter
    """
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            
            delay = min(base_delay * (2 ** attempt), max_delay)
            if jitter:
                delay = delay * (0.5 + random.random())
            
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries} failed: {e}. "
                f"Retrying in {delay:.2f}s..."
            )
            await asyncio.sleep(delay)


class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self, min_interval: float = 0.1):
        self.min_interval = min_interval
        self.last_call = 0.0
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire rate limit lock"""
        async with self._lock:
            now = time.time()
            time_since_last = now - self.last_call
            
            if time_since_last < self.min_interval:
                await asyncio.sleep(self.min_interval - time_since_last)
            
            self.last_call = time.time()


class TTLCache:
    """Simple TTL cache for API responses"""
    
    def __init__(self, ttl: int = 60):
        self.ttl = ttl
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired"""
        async with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if time.time() - timestamp < self.ttl:
                    return value
                else:
                    del self._cache[key]
            return None
    
    async def set(self, key: str, value: Any):
        """Set cache value with current timestamp"""
        async with self._lock:
            self._cache[key] = (value, time.time())
    
    async def clear(self):
        """Clear all cached values"""
        async with self._lock:
            self._cache.clear()


def format_price(price: float, decimals: int = 8) -> str:
    """Format price with appropriate decimals"""
    if price >= 1000:
        return f"{price:.2f}"
    elif price >= 1:
        return f"{price:.4f}"
    else:
        return f"{price:.{decimals}f}".rstrip('0').rstrip('.')


def format_percentage(value: float) -> str:
    """Format percentage value"""
    return f"{value * 100:.2f}%"


def get_swing_highs_lows(
    candles: deque,
    lookback: int = 20
) -> Tuple[Optional[float], Optional[float]]:
    """
    Get swing high and low from recent candles
    Returns (swing_high, swing_low)
    """
    if len(candles) < lookback:
        return None, None
    
    candles_list = list(candles)[-lookback:]
    
    highs = [float(c['high']) for c in candles_list]
    lows = [float(c['low']) for c in candles_list]
    
    swing_high = max(highs) if highs else None
    swing_low = min(lows) if lows else None
    
    return swing_high, swing_low


def calculate_risk_reward(
    entry: float,
    stop_loss: float,
    take_profit: float
) -> float:
    """Calculate risk/reward ratio"""
    risk = abs(entry - stop_loss)
    reward = abs(take_profit - entry)
    
    if risk == 0:
        return 0.0
    
    return reward / risk


def is_displacement_candle(
    candle: Dict,
    atr: float,
    volume_ma: float,
    atr_multiple: float = 1.5,
    volume_multiple: float = 1.2
) -> bool:
    """
    Check if candle represents displacement
    """
    body = candle_body_size(candle)
    volume = float(candle['volume'])
    
    return (
        body > atr * atr_multiple and
        volume > volume_ma * volume_multiple
    )


def find_fvg(
    candles: deque,
    lookback: int = 10
) -> List[Dict]:
    """
    Find Fair Value Gaps in recent candles
    Returns list of FVG zones
    """
    if len(candles) < 3:
        return []
    
    fvgs = []
    candles_list = list(candles)[-lookback:]
    
    for i in range(len(candles_list) - 2):
        c1 = candles_list[i]
        c2 = candles_list[i + 1]
        c3 = candles_list[i + 2]
        
        # Bullish FVG: c1 low > c3 high
        if float(c1['low']) > float(c3['high']):
            fvgs.append({
                'type': 'bullish',
                'top': float(c1['low']),
                'bottom': float(c3['high']),
                'candle_index': i
            })
        
        # Bearish FVG: c1 high < c3 low
        elif float(c1['high']) < float(c3['low']):
            fvgs.append({
                'type': 'bearish',
                'top': float(c3['low']),
                'bottom': float(c1['high']),
                'candle_index': i
            })
    
    return fvgs


def timestamp_to_readable(timestamp: int) -> str:
    """Convert timestamp to readable format"""
    from datetime import datetime
    dt = datetime.fromtimestamp(timestamp / 1000)
    return dt.strftime('%Y-%m-%d %H:%M:%S')


async def safe_close_session(session: aiohttp.ClientSession):
    """Safely close aiohttp session"""
    try:
        if session and not session.closed:
            await session.close()
            await asyncio.sleep(0.1)  # Give time for cleanup
    except Exception as e:
        logger.warning(f"Error closing session: {e}")


def chunks(lst: List, n: int) -> List[List]:
    """Yield successive n-sized chunks from lst"""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]
