"""
Candle pattern recognition module.
Detects various candlestick patterns for confirmation signals.
"""

from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class Candle:
    """Represents a single candlestick."""
    
    def __init__(self, open_price: float, high: float, low: float, close: float, volume: float):
        self.open = open_price
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        
        # Calculated properties
        self.body = abs(close - open_price)
        self.range = high - low
        self.upper_wick = high - max(open_price, close)
        self.lower_wick = min(open_price, close) - low
        self.is_bullish = close > open_price
        self.is_bearish = close < open_price
        
    @property
    def body_ratio(self) -> float:
        """Body size as ratio of total range."""
        if self.range == 0:
            return 0
        return self.body / self.range
    
    @property
    def upper_wick_ratio(self) -> float:
        """Upper wick size as ratio of body."""
        if self.body == 0:
            return float('inf') if self.upper_wick > 0 else 0
        return self.upper_wick / self.body
    
    @property
    def lower_wick_ratio(self) -> float:
        """Lower wick size as ratio of body."""
        if self.body == 0:
            return float('inf') if self.lower_wick > 0 else 0
        return self.lower_wick / self.body


class CandlePatternDetector:
    """Detects candlestick patterns and scores them for signal confirmation."""
    
    def __init__(self, pin_bar_min_wick_ratio: float = 2.0, 
                 momentum_min_body_ratio: float = 0.6):
        self.pin_bar_min_wick_ratio = pin_bar_min_wick_ratio
        self.momentum_min_body_ratio = momentum_min_body_ratio
    
    def detect_bullish_engulfing(self, prev_candle: Candle, current_candle: Candle) -> bool:
        """
        Detect bullish engulfing pattern.
        Previous candle is bearish, current candle is bullish and engulfs it.
        """
        if not (prev_candle.is_bearish and current_candle.is_bullish):
            return False
        
        # Current candle must engulf previous candle
        engulfs = (current_candle.open <= prev_candle.close and 
                  current_candle.close >= prev_candle.open)
        
        return engulfs
    
    def detect_bearish_engulfing(self, prev_candle: Candle, current_candle: Candle) -> bool:
        """
        Detect bearish engulfing pattern.
        Previous candle is bullish, current candle is bearish and engulfs it.
        """
        if not (prev_candle.is_bullish and current_candle.is_bearish):
            return False
        
        # Current candle must engulf previous candle
        engulfs = (current_candle.open >= prev_candle.close and 
                  current_candle.close <= prev_candle.open)
        
        return engulfs
    
    def detect_hammer(self, candle: Candle) -> bool:
        """
        Detect hammer pattern (bullish reversal).
        Small body at top, long lower wick.
        """
        if not candle.is_bullish:
            return False
        
        # Long lower wick relative to body
        if candle.lower_wick_ratio < self.pin_bar_min_wick_ratio:
            return False
        
        # Small upper wick
        if candle.upper_wick > candle.body:
            return False
        
        return True
    
    def detect_shooting_star(self, candle: Candle) -> bool:
        """
        Detect shooting star pattern (bearish reversal).
        Small body at bottom, long upper wick.
        """
        if not candle.is_bearish:
            return False
        
        # Long upper wick relative to body
        if candle.upper_wick_ratio < self.pin_bar_min_wick_ratio:
            return False
        
        # Small lower wick
        if candle.lower_wick > candle.body:
            return False
        
        return True
    
    def detect_pin_bar_bullish(self, candle: Candle) -> bool:
        """
        Detect bullish pin bar.
        Long lower wick, small body, suggests rejection of lower prices.
        """
        # Long lower wick
        if candle.lower_wick_ratio < self.pin_bar_min_wick_ratio:
            return False
        
        # Small body relative to range
        if candle.body_ratio > 0.3:
            return False
        
        # Upper wick should be small
        if candle.upper_wick > candle.body:
            return False
        
        return True
    
    def detect_pin_bar_bearish(self, candle: Candle) -> bool:
        """
        Detect bearish pin bar.
        Long upper wick, small body, suggests rejection of higher prices.
        """
        # Long upper wick
        if candle.upper_wick_ratio < self.pin_bar_min_wick_ratio:
            return False
        
        # Small body relative to range
        if candle.body_ratio > 0.3:
            return False
        
        # Lower wick should be small
        if candle.lower_wick > candle.body:
            return False
        
        return True
    
    def detect_inside_bar(self, prev_candle: Candle, current_candle: Candle) -> bool:
        """
        Detect inside bar pattern.
        Current candle's range is completely within previous candle's range.
        """
        inside = (current_candle.high <= prev_candle.high and 
                 current_candle.low >= prev_candle.low)
        return inside
    
    def detect_momentum_candle_bullish(self, candle: Candle, atr: float) -> bool:
        """
        Detect bullish momentum candle.
        Large bullish body with minimal wicks.
        """
        if not candle.is_bullish:
            return False
        
        # Large body relative to range
        if candle.body_ratio < self.momentum_min_body_ratio:
            return False
        
        # Body should be significant relative to ATR
        if atr > 0 and candle.body < 0.5 * atr:
            return False
        
        return True
    
    def detect_momentum_candle_bearish(self, candle: Candle, atr: float) -> bool:
        """
        Detect bearish momentum candle.
        Large bearish body with minimal wicks.
        """
        if not candle.is_bearish:
            return False
        
        # Large body relative to range
        if candle.body_ratio < self.momentum_min_body_ratio:
            return False
        
        # Body should be significant relative to ATR
        if atr > 0 and candle.body < 0.5 * atr:
            return False
        
        return True
    
    def detect_fakeout(self, candle: Candle, level: float, direction: str) -> bool:
        """
        Detect fakeout pattern.
        Price breaks through level with a wick but closes back inside.
        
        Args:
            candle: Current candle
            level: Support/resistance level
            direction: 'bullish' (fakeout below) or 'bearish' (fakeout above)
        """
        if direction == 'bullish':
            # Wick pierced below support but closed above
            fakeout = (candle.low < level and candle.close > level)
        else:  # bearish
            # Wick pierced above resistance but closed below
            fakeout = (candle.high > level and candle.close < level)
        
        return fakeout
    
    def score_pattern_confirmation(self, prev_candle: Optional[Candle], 
                                   current_candle: Candle, 
                                   direction: str, 
                                   atr: float,
                                   nearby_level: Optional[float] = None) -> Tuple[float, List[str]]:
        """
        Score the current candle for pattern confirmation.
        
        Args:
            prev_candle: Previous candle (if available)
            current_candle: Current candle to analyze
            direction: Expected signal direction ('long' or 'short')
            atr: Average True Range for momentum detection
            nearby_level: Nearby support/resistance level for fakeout detection
        
        Returns:
            Tuple of (score out of 100, list of detected patterns)
        """
        score = 0
        patterns = []
        
        if direction == 'long':
            # Bullish patterns
            if prev_candle:
                if self.detect_bullish_engulfing(prev_candle, current_candle):
                    score += 30
                    patterns.append("bullish_engulfing")
                elif self.detect_inside_bar(prev_candle, current_candle):
                    score += 10
                    patterns.append("inside_bar")
            
            if self.detect_hammer(current_candle):
                score += 25
                patterns.append("hammer")
            elif self.detect_pin_bar_bullish(current_candle):
                score += 20
                patterns.append("pin_bar_bullish")
            
            if self.detect_momentum_candle_bullish(current_candle, atr):
                score += 25
                patterns.append("momentum_bullish")
            
            if nearby_level and self.detect_fakeout(current_candle, nearby_level, 'bullish'):
                score += 30
                patterns.append("fakeout_bullish")
        
        else:  # short
            # Bearish patterns
            if prev_candle:
                if self.detect_bearish_engulfing(prev_candle, current_candle):
                    score += 30
                    patterns.append("bearish_engulfing")
                elif self.detect_inside_bar(prev_candle, current_candle):
                    score += 10
                    patterns.append("inside_bar")
            
            if self.detect_shooting_star(current_candle):
                score += 25
                patterns.append("shooting_star")
            elif self.detect_pin_bar_bearish(current_candle):
                score += 20
                patterns.append("pin_bar_bearish")
            
            if self.detect_momentum_candle_bearish(current_candle, atr):
                score += 25
                patterns.append("momentum_bearish")
            
            if nearby_level and self.detect_fakeout(current_candle, nearby_level, 'bearish'):
                score += 30
                patterns.append("fakeout_bearish")
        
        # Cap at 100
        score = min(score, 100)
        
        return score, patterns


def calculate_atr(candles: List[Candle], period: int = 14) -> float:
    """
    Calculate Average True Range.
    
    Args:
        candles: List of candles (most recent last)
        period: ATR period
    
    Returns:
        ATR value
    """
    if len(candles) < period + 1:
        return 0
    
    true_ranges = []
    for i in range(len(candles) - period, len(candles)):
        if i == 0:
            tr = candles[i].range
        else:
            high_low = candles[i].high - candles[i].low
            high_close = abs(candles[i].high - candles[i-1].close)
            low_close = abs(candles[i].low - candles[i-1].close)
            tr = max(high_low, high_close, low_close)
        true_ranges.append(tr)
    
    return sum(true_ranges) / len(true_ranges)
