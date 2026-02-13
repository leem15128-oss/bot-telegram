"""
Lightweight trendline detection module.
Identifies pivot points and computes trendlines for breakout detection.
"""

from typing import List, Tuple, Optional
import logging
from bot.candle_patterns import Candle

logger = logging.getLogger(__name__)


class Pivot:
    """Represents a pivot point (swing high or swing low)."""
    
    def __init__(self, index: int, price: float, is_high: bool):
        self.index = index  # Position in candle array
        self.price = price
        self.is_high = is_high  # True for swing high, False for swing low


class Trendline:
    """Represents a trendline connecting multiple pivots."""
    
    def __init__(self, pivot1: Pivot, pivot2: Pivot):
        self.pivot1 = pivot1
        self.pivot2 = pivot2
        self.is_ascending = pivot2.price > pivot1.price
        
        # Calculate slope
        if pivot2.index == pivot1.index:
            self.slope = 0
        else:
            self.slope = (pivot2.price - pivot1.price) / (pivot2.index - pivot1.index)
        
        self.intercept = pivot1.price - self.slope * pivot1.index
        self.touches = 2  # Number of pivots on this line
    
    def price_at_index(self, index: int) -> float:
        """Calculate expected price at given index."""
        return self.slope * index + self.intercept
    
    def is_broken(self, current_index: int, current_price: float, direction: str) -> bool:
        """
        Check if trendline is broken.
        
        Args:
            current_index: Current candle index
            current_price: Current price to check
            direction: 'bullish' (expecting upward break) or 'bearish' (expecting downward break)
        """
        expected_price = self.price_at_index(current_index)
        
        if direction == 'bullish':
            # Bullish break: price breaks above descending trendline
            return current_price > expected_price and not self.is_ascending
        else:
            # Bearish break: price breaks below ascending trendline
            return current_price < expected_price and self.is_ascending


class TrendlineDetector:
    """Detects trendlines from pivot points."""
    
    def __init__(self, lookback_bars: int = 10, 
                 min_touches: int = 2,
                 max_deviation_pct: float = 0.5):
        self.lookback_bars = lookback_bars
        self.min_touches = min_touches
        self.max_deviation_pct = max_deviation_pct
    
    def find_pivots(self, candles: List[Candle]) -> Tuple[List[Pivot], List[Pivot]]:
        """
        Find swing highs and swing lows.
        
        Args:
            candles: List of candles (closed only)
        
        Returns:
            Tuple of (swing_highs, swing_lows)
        """
        if len(candles) < self.lookback_bars * 2 + 1:
            return [], []
        
        swing_highs = []
        swing_lows = []
        
        # Don't check the very first and last few candles
        for i in range(self.lookback_bars, len(candles) - self.lookback_bars):
            is_swing_high = True
            is_swing_low = True
            
            # Check if this is a local high/low
            for j in range(i - self.lookback_bars, i + self.lookback_bars + 1):
                if j == i:
                    continue
                
                if candles[j].high >= candles[i].high:
                    is_swing_high = False
                if candles[j].low <= candles[i].low:
                    is_swing_low = False
            
            if is_swing_high:
                swing_highs.append(Pivot(i, candles[i].high, True))
            if is_swing_low:
                swing_lows.append(Pivot(i, candles[i].low, False))
        
        return swing_highs, swing_lows
    
    def find_best_trendline(self, pivots: List[Pivot], candles: List[Candle]) -> Optional[Trendline]:
        """
        Find the best trendline from a list of pivots.
        
        Args:
            pivots: List of pivot points (all highs or all lows)
            candles: List of candles for validation
        
        Returns:
            Best trendline if found, None otherwise
        """
        if len(pivots) < self.min_touches:
            return None
        
        best_trendline = None
        max_touches = 0
        
        # Try all pairs of pivots
        for i in range(len(pivots)):
            for j in range(i + 1, len(pivots)):
                trendline = Trendline(pivots[i], pivots[j])
                
                # Count how many other pivots are near this line
                touches = 2  # The two defining pivots
                for k in range(len(pivots)):
                    if k == i or k == j:
                        continue
                    
                    expected_price = trendline.price_at_index(pivots[k].index)
                    deviation_pct = abs(pivots[k].price - expected_price) / expected_price * 100
                    
                    if deviation_pct <= self.max_deviation_pct:
                        touches += 1
                
                # Update best trendline if this one has more touches
                if touches >= self.min_touches and touches > max_touches:
                    max_touches = touches
                    trendline.touches = touches
                    best_trendline = trendline
        
        return best_trendline
    
    def detect_trendlines(self, candles: List[Candle]) -> Tuple[Optional[Trendline], Optional[Trendline]]:
        """
        Detect support and resistance trendlines.
        
        Args:
            candles: List of candles (closed only)
        
        Returns:
            Tuple of (resistance_trendline, support_trendline)
        """
        swing_highs, swing_lows = self.find_pivots(candles)
        
        resistance_trendline = self.find_best_trendline(swing_highs, candles) if swing_highs else None
        support_trendline = self.find_best_trendline(swing_lows, candles) if swing_lows else None
        
        return resistance_trendline, support_trendline
    
    def score_trendline_alignment(self, candles: List[Candle], 
                                  current_price: float, 
                                  direction: str) -> Tuple[float, str]:
        """
        Score trendline alignment for a potential signal.
        
        Args:
            candles: List of candles (closed only)
            current_price: Current price
            direction: Signal direction ('long' or 'short')
        
        Returns:
            Tuple of (score out of 100, reason)
        """
        if len(candles) < self.lookback_bars * 2 + 1:
            return 50, "insufficient_data"
        
        resistance_trendline, support_trendline = self.detect_trendlines(candles)
        current_index = len(candles)
        
        if direction == 'long':
            # For long signals, we want:
            # 1. Break above descending resistance (reversal)
            # 2. Bounce off ascending support (continuation)
            
            if resistance_trendline and resistance_trendline.is_broken(current_index, current_price, 'bullish'):
                logger.info(f"Bullish trendline break detected (resistance)")
                return 100, "resistance_break"
            
            if support_trendline:
                expected_support = support_trendline.price_at_index(current_index)
                if support_trendline.is_ascending and current_price >= expected_support * 0.99:
                    logger.info(f"Near ascending support trendline")
                    return 80, "support_bounce"
            
            # Check if we're NOT buying into descending trendline
            if resistance_trendline and not resistance_trendline.is_ascending:
                expected_resistance = resistance_trendline.price_at_index(current_index)
                if current_price < expected_resistance * 0.95:
                    logger.info(f"Below descending resistance - neutral")
                    return 50, "below_resistance"
                else:
                    logger.warning(f"Buying into descending resistance - negative")
                    return 20, "against_resistance"
            
            return 50, "no_clear_trendline"
        
        else:  # short
            # For short signals, we want:
            # 1. Break below ascending support (reversal)
            # 2. Rejection at descending resistance (continuation)
            
            if support_trendline and support_trendline.is_broken(current_index, current_price, 'bearish'):
                logger.info(f"Bearish trendline break detected (support)")
                return 100, "support_break"
            
            if resistance_trendline:
                expected_resistance = resistance_trendline.price_at_index(current_index)
                if not resistance_trendline.is_ascending and current_price <= expected_resistance * 1.01:
                    logger.info(f"Near descending resistance trendline")
                    return 80, "resistance_rejection"
            
            # Check if we're NOT selling into ascending trendline
            if support_trendline and support_trendline.is_ascending:
                expected_support = support_trendline.price_at_index(current_index)
                if current_price > expected_support * 1.05:
                    logger.info(f"Above ascending support - neutral")
                    return 50, "above_support"
                else:
                    logger.warning(f"Selling into ascending support - negative")
                    return 20, "against_support"
            
            return 50, "no_clear_trendline"
