"""
Data manager for multi-timeframe candle storage and retrieval.
Maintains candles for 30m, 1h, and 4h timeframes.
"""

import logging
from typing import Dict, List, Optional
from collections import deque
from bot.candle_patterns import Candle
import bot.config as config

logger = logging.getLogger(__name__)


class DataManager:
    """
    Manages candle data for multiple symbols and timeframes.
    Stores closed candles and tracks the latest forming candle separately.
    """
    
    def __init__(self, max_candles: int = 500):
        """
        Initialize data manager.
        
        Args:
            max_candles: Maximum candles to keep per symbol/timeframe
        """
        self.max_candles = max_candles
        
        # Storage: {symbol: {timeframe: deque([Candle])}}
        self._closed_candles: Dict[str, Dict[str, deque]] = {}
        
        # Latest forming candle: {symbol: {timeframe: Candle}}
        self._forming_candles: Dict[str, Dict[str, Optional[Candle]]] = {}
        
        # Candle metadata: {symbol: {timeframe: {open_time, close_time}}}
        self._candle_times: Dict[str, Dict[str, Dict[str, int]]] = {}
    
    def _ensure_symbol(self, symbol: str):
        """Ensure symbol is initialized in data structures."""
        if symbol not in self._closed_candles:
            self._closed_candles[symbol] = {}
            self._forming_candles[symbol] = {}
            self._candle_times[symbol] = {}
            
            for tf in config.TIMEFRAMES:
                self._closed_candles[symbol][tf] = deque(maxlen=self.max_candles)
                self._forming_candles[symbol][tf] = None
                self._candle_times[symbol][tf] = {'open_time': 0, 'close_time': 0}
    
    def add_candle(self, symbol: str, timeframe: str, 
                   open_price: float, high: float, low: float, close: float, volume: float,
                   open_time: int, close_time: int, is_closed: bool):
        """
        Add or update a candle.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe (e.g., '30m', '1h', '4h')
            open_price, high, low, close, volume: Candle data
            open_time: Candle open timestamp (ms)
            close_time: Candle close timestamp (ms)
            is_closed: Whether this candle is closed
        """
        self._ensure_symbol(symbol)
        
        candle = Candle(open_price, high, low, close, volume)
        
        if is_closed:
            # Add to closed candles
            self._closed_candles[symbol][timeframe].append(candle)
            self._candle_times[symbol][timeframe] = {
                'open_time': open_time,
                'close_time': close_time
            }
            # Clear forming candle since this one closed
            self._forming_candles[symbol][timeframe] = None
            
            logger.debug(f"Added closed candle for {symbol} {timeframe}: "
                        f"O:{open_price} H:{high} L:{low} C:{close} V:{volume}")
        else:
            # Update forming candle
            self._forming_candles[symbol][timeframe] = candle
            self._candle_times[symbol][timeframe] = {
                'open_time': open_time,
                'close_time': close_time
            }
            
            logger.debug(f"Updated forming candle for {symbol} {timeframe}: "
                        f"O:{open_price} H:{high} L:{low} C:{close}")
    
    def get_closed_candles(self, symbol: str, timeframe: str, 
                          count: Optional[int] = None) -> List[Candle]:
        """
        Get closed candles for a symbol/timeframe.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            count: Number of recent candles to return (None = all)
        
        Returns:
            List of candles (oldest first)
        """
        self._ensure_symbol(symbol)
        
        candles = list(self._closed_candles[symbol][timeframe])
        
        if count is not None and count > 0:
            candles = candles[-count:]
        
        return candles
    
    def get_forming_candle(self, symbol: str, timeframe: str) -> Optional[Candle]:
        """
        Get the current forming (not yet closed) candle.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
        
        Returns:
            Forming candle or None
        """
        self._ensure_symbol(symbol)
        return self._forming_candles[symbol][timeframe]
    
    def get_all_candles(self, symbol: str, timeframe: str, 
                       include_forming: bool = True) -> List[Candle]:
        """
        Get all candles including the forming one if requested.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            include_forming: Whether to include the forming candle
        
        Returns:
            List of candles (oldest first, forming last if included)
        """
        candles = self.get_closed_candles(symbol, timeframe)
        
        if include_forming:
            forming = self.get_forming_candle(symbol, timeframe)
            if forming:
                candles = candles + [forming]
        
        return candles
    
    def get_latest_price(self, symbol: str, timeframe: str) -> Optional[float]:
        """
        Get the latest price (close of forming candle or last closed candle).
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
        
        Returns:
            Latest close price or None
        """
        # Try forming candle first
        forming = self.get_forming_candle(symbol, timeframe)
        if forming:
            return forming.close
        
        # Fall back to last closed candle
        closed = self.get_closed_candles(symbol, timeframe, count=1)
        if closed:
            return closed[-1].close
        
        return None
    
    def get_candle_window(self, symbol: str, timeframe: str) -> Optional[int]:
        """
        Get the current candle window start time.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
        
        Returns:
            Open time in seconds (or None)
        """
        self._ensure_symbol(symbol)
        open_time_ms = self._candle_times[symbol][timeframe].get('open_time', 0)
        return open_time_ms // 1000 if open_time_ms > 0 else None
    
    def calculate_trend(self, symbol: str, timeframe: str, lookback: int = 20) -> str:
        """
        Calculate simple trend based on recent candles.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            lookback: Number of candles to analyze
        
        Returns:
            'up', 'down', or 'neutral'
        """
        candles = self.get_closed_candles(symbol, timeframe, count=lookback)
        
        if len(candles) < 10:
            return 'neutral'
        
        # Simple trend: compare first half vs second half average close
        mid = len(candles) // 2
        first_half_avg = sum(c.close for c in candles[:mid]) / mid
        second_half_avg = sum(c.close for c in candles[mid:]) / (len(candles) - mid)
        
        diff_pct = ((second_half_avg - first_half_avg) / first_half_avg) * 100
        
        if diff_pct > 1.0:
            return 'up'
        elif diff_pct < -1.0:
            return 'down'
        else:
            return 'neutral'
    
    def find_support_resistance(self, symbol: str, timeframe: str, 
                               current_price: float, atr: float) -> tuple:
        """
        Find nearest support and resistance levels.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            current_price: Current price
            atr: Average True Range
        
        Returns:
            Tuple of (nearest_support, nearest_resistance)
        """
        candles = self.get_closed_candles(symbol, timeframe)
        
        if len(candles) < 20:
            return None, None
        
        # Find recent swing highs and lows
        highs = []
        lows = []
        
        for i in range(5, len(candles) - 5):
            # Check if local high
            is_high = all(candles[i].high >= candles[j].high 
                         for j in range(i-5, i+5) if j != i)
            if is_high:
                highs.append(candles[i].high)
            
            # Check if local low
            is_low = all(candles[i].low <= candles[j].low 
                        for j in range(i-5, i+5) if j != i)
            if is_low:
                lows.append(candles[i].low)
        
        # Find nearest support (below current price)
        zone_width = atr * config.SR_ZONE_WIDTH_ATR
        nearest_support = None
        for level in sorted(lows, reverse=True):
            if level < current_price - zone_width:
                nearest_support = level
                break
        
        # Find nearest resistance (above current price)
        nearest_resistance = None
        for level in sorted(highs):
            if level > current_price + zone_width:
                nearest_resistance = level
                break
        
        return nearest_support, nearest_resistance
    
    def find_multiple_sr_levels(self, symbol: str, timeframe: str, 
                               current_price: float, atr: float, 
                               direction: str, max_levels: int = 3) -> List[float]:
        """
        Find multiple support or resistance levels for take profit targets.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            current_price: Current price
            atr: Average True Range
            direction: 'long' (find resistances) or 'short' (find supports)
            max_levels: Maximum number of levels to return
        
        Returns:
            List of SR levels sorted by distance from current price
        """
        candles = self.get_closed_candles(symbol, timeframe)
        
        if len(candles) < 20:
            return []
        
        # Find recent swing highs and lows
        highs = []
        lows = []
        
        for i in range(5, len(candles) - 5):
            # Check if local high
            is_high = all(candles[i].high >= candles[j].high 
                         for j in range(i-5, i+5) if j != i)
            if is_high:
                highs.append(candles[i].high)
            
            # Check if local low
            is_low = all(candles[i].low <= candles[j].low 
                        for j in range(i-5, i+5) if j != i)
            if is_low:
                lows.append(candles[i].low)
        
        zone_width = atr * config.SR_ZONE_WIDTH_ATR
        
        if direction == 'long':
            # Find resistance levels above current price
            levels = [level for level in sorted(highs) 
                     if level > current_price + zone_width]
            return levels[:max_levels]
        else:
            # Find support levels below current price
            levels = [level for level in sorted(lows, reverse=True) 
                     if level < current_price - zone_width]
            return levels[:max_levels]
    
    def get_stats(self) -> dict:
        """Get statistics about stored data."""
        stats = {}
        for symbol in self._closed_candles:
            stats[symbol] = {}
            for tf in self._closed_candles[symbol]:
                stats[symbol][tf] = {
                    'closed_count': len(self._closed_candles[symbol][tf]),
                    'has_forming': self._forming_candles[symbol][tf] is not None,
                }
        return stats
