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
    
    def detect_doji(self, candle: Candle, atr: float) -> bool:
        """
        Detect standard Doji pattern - small body with upper and lower shadows.
        A Doji indicates indecision in the market.
        """
        body_to_range = candle.body_ratio
        is_doji = body_to_range < 0.1 and candle.range > 0.3 * atr
        return is_doji
    
    def detect_long_legged_doji(self, candle: Candle, atr: float) -> bool:
        """
        Detect Long-Legged Doji - doji with very long upper and lower shadows.
        Indicates strong indecision with large price swings.
        """
        body_to_range = candle.body_ratio
        # Very small body and large range
        is_long_legged = (body_to_range < 0.05 and 
                         candle.range > 0.8 * atr and
                         candle.upper_wick > 0.3 * candle.range and
                         candle.lower_wick > 0.3 * candle.range)
        return is_long_legged
    
    def detect_dragonfly_doji(self, candle: Candle, atr: float) -> bool:
        """
        Detect Dragonfly Doji - doji with long lower shadow, little to no upper shadow.
        Bullish reversal signal.
        """
        body_to_range = candle.body_ratio
        # Small body, long lower shadow, minimal upper shadow
        is_dragonfly = (body_to_range < 0.1 and
                       candle.range > 0.3 * atr and
                       candle.lower_wick > 0.6 * candle.range and
                       candle.upper_wick < 0.1 * candle.range)
        return is_dragonfly
    
    def detect_gravestone_doji(self, candle: Candle, atr: float) -> bool:
        """
        Detect Gravestone Doji - doji with long upper shadow, little to no lower shadow.
        Bearish reversal signal.
        """
        body_to_range = candle.body_ratio
        # Small body, long upper shadow, minimal lower shadow
        is_gravestone = (body_to_range < 0.1 and
                        candle.range > 0.3 * atr and
                        candle.upper_wick > 0.6 * candle.range and
                        candle.lower_wick < 0.1 * candle.range)
        return is_gravestone
    
    def detect_morning_star(self, candles: List[Candle], atr: float) -> bool:
        """
        Detect Morning Star pattern - bullish reversal (3 candles).
        Pattern: Long bearish candle, small-bodied star that gaps down, 
                 long bullish candle closing above midpoint of first.
        """
        if len(candles) < 3:
            return False
        
        c1, c2, c3 = candles[-3], candles[-2], candles[-1]
        
        # First candle: long bearish
        c1_bearish = c1.is_bearish
        c1_long = c1.body > 0.6 * atr
        
        # Second candle: small body (star)
        c2_small = c2.body < 0.3 * atr
        # Star should gap down
        c2_gaps_down = c2.high < c1.close
        
        # Third candle: long bullish
        c3_bullish = c3.is_bullish
        c3_long = c3.body > 0.6 * atr
        # Close above midpoint of first candle
        c1_midpoint = (c1.open + c1.close) / 2
        c3_closes_high = c3.close > c1_midpoint
        
        return (c1_bearish and c1_long and c2_small and c2_gaps_down and
                c3_bullish and c3_long and c3_closes_high)
    
    def detect_evening_star(self, candles: List[Candle], atr: float) -> bool:
        """
        Detect Evening Star pattern - bearish reversal (3 candles).
        Pattern: Long bullish candle, small-bodied star that gaps up,
                 long bearish candle closing below midpoint of first.
        """
        if len(candles) < 3:
            return False
        
        c1, c2, c3 = candles[-3], candles[-2], candles[-1]
        
        # First candle: long bullish
        c1_bullish = c1.is_bullish
        c1_long = c1.body > 0.6 * atr
        
        # Second candle: small body (star)
        c2_small = c2.body < 0.3 * atr
        # Star should gap up
        c2_gaps_up = c2.low > c1.close
        
        # Third candle: long bearish
        c3_bearish = c3.is_bearish
        c3_long = c3.body > 0.6 * atr
        # Close below midpoint of first candle
        c1_midpoint = (c1.open + c1.close) / 2
        c3_closes_low = c3.close < c1_midpoint
        
        return (c1_bullish and c1_long and c2_small and c2_gaps_up and
                c3_bearish and c3_long and c3_closes_low)
    
    def detect_bullish_harami(self, prev_candle: Candle, current_candle: Candle, atr: float) -> bool:
        """
        Detect Bullish Harami pattern - bullish reversal (2 candles).
        Pattern: Large bearish candle followed by small bullish candle 
                 contained within the body of the first.
        """
        # First candle: long bearish
        prev_bearish = prev_candle.is_bearish
        prev_long = prev_candle.body > 0.6 * atr
        
        # Second candle: small bullish, contained within first's body
        curr_bullish = current_candle.is_bullish
        curr_small = current_candle.body < 0.5 * prev_candle.body
        curr_contained = (current_candle.open < prev_candle.open and
                         current_candle.close > prev_candle.close)
        
        return prev_bearish and prev_long and curr_bullish and curr_small and curr_contained
    
    def detect_bearish_harami(self, prev_candle: Candle, current_candle: Candle, atr: float) -> bool:
        """
        Detect Bearish Harami pattern - bearish reversal (2 candles).
        Pattern: Large bullish candle followed by small bearish candle
                 contained within the body of the first.
        """
        # First candle: long bullish
        prev_bullish = prev_candle.is_bullish
        prev_long = prev_candle.body > 0.6 * atr
        
        # Second candle: small bearish, contained within first's body
        curr_bearish = current_candle.is_bearish
        curr_small = current_candle.body < 0.5 * prev_candle.body
        curr_contained = (current_candle.open > prev_candle.open and
                         current_candle.close < prev_candle.close)
        
        return prev_bullish and prev_long and curr_bearish and curr_small and curr_contained
    
    def detect_tweezer_top(self, prev_candle: Candle, current_candle: Candle, atr: float) -> bool:
        """
        Detect Tweezer Top pattern - bearish reversal (2 candles).
        Pattern: Two candles with similar highs, second should be bearish.
        """
        # Similar highs (within 0.5% or 0.1*ATR)
        high_diff = abs(prev_candle.high - current_candle.high)
        tolerance = min(prev_candle.high * 0.005, 0.1 * atr)
        similar_highs = high_diff < tolerance
        
        # First candle bullish, second bearish
        prev_bullish = prev_candle.is_bullish
        curr_bearish = current_candle.is_bearish
        
        # Both should have reasonable bodies
        both_have_body = prev_candle.body > 0.3 * atr and current_candle.body > 0.3 * atr
        
        return similar_highs and prev_bullish and curr_bearish and both_have_body
    
    def detect_tweezer_bottom(self, prev_candle: Candle, current_candle: Candle, atr: float) -> bool:
        """
        Detect Tweezer Bottom pattern - bullish reversal (2 candles).
        Pattern: Two candles with similar lows, second should be bullish.
        """
        # Similar lows (within 0.5% or 0.1*ATR)
        low_diff = abs(prev_candle.low - current_candle.low)
        tolerance = min(prev_candle.low * 0.005, 0.1 * atr)
        similar_lows = low_diff < tolerance
        
        # First candle bearish, second bullish
        prev_bearish = prev_candle.is_bearish
        curr_bullish = current_candle.is_bullish
        
        # Both should have reasonable bodies
        both_have_body = prev_candle.body > 0.3 * atr and current_candle.body > 0.3 * atr
        
        return similar_lows and prev_bearish and curr_bullish and both_have_body
    
    def detect_three_white_soldiers(self, candles: List[Candle], atr: float) -> bool:
        """
        Detect Three White Soldiers pattern - strong bullish continuation (3 candles).
        Pattern: Three consecutive long bullish candles with higher closes,
                 each opening within the previous candle's body.
        """
        if len(candles) < 3:
            return False
        
        c1, c2, c3 = candles[-3], candles[-2], candles[-1]
        
        # All three must be bullish with strong bodies
        all_bullish = c1.is_bullish and c2.is_bullish and c3.is_bullish
        all_long = (c1.body > 0.5 * atr and c2.body > 0.5 * atr and c3.body > 0.5 * atr)
        
        # Each close higher than previous
        rising_closes = c2.close > c1.close and c3.close > c2.close
        
        # Each opens within previous body
        c2_opens_in_c1 = c2.open > c1.open and c2.open < c1.close
        c3_opens_in_c2 = c3.open > c2.open and c3.open < c2.close
        opens_within_body = c2_opens_in_c1 and c3_opens_in_c2
        
        # Small upper shadows (not excessive buying exhaustion)
        small_shadows = (c1.upper_wick < 0.3 * c1.body and
                        c2.upper_wick < 0.3 * c2.body and
                        c3.upper_wick < 0.3 * c3.body)
        
        return all_bullish and all_long and rising_closes and opens_within_body and small_shadows
    
    def detect_three_black_crows(self, candles: List[Candle], atr: float) -> bool:
        """
        Detect Three Black Crows pattern - strong bearish continuation (3 candles).
        Pattern: Three consecutive long bearish candles with lower closes,
                 each opening within the previous candle's body.
        """
        if len(candles) < 3:
            return False
        
        c1, c2, c3 = candles[-3], candles[-2], candles[-1]
        
        # All three must be bearish with strong bodies
        all_bearish = c1.is_bearish and c2.is_bearish and c3.is_bearish
        all_long = (c1.body > 0.5 * atr and c2.body > 0.5 * atr and c3.body > 0.5 * atr)
        
        # Each close lower than previous
        falling_closes = c2.close < c1.close and c3.close < c2.close
        
        # Each opens within previous body
        c2_opens_in_c1 = c2.open < c1.open and c2.open > c1.close
        c3_opens_in_c2 = c3.open < c2.open and c3.open > c2.close
        opens_within_body = c2_opens_in_c1 and c3_opens_in_c2
        
        # Small lower shadows (not excessive selling exhaustion)
        small_shadows = (c1.lower_wick < 0.3 * c1.body and
                        c2.lower_wick < 0.3 * c2.body and
                        c3.lower_wick < 0.3 * c3.body)
        
        return all_bearish and all_long and falling_closes and opens_within_body and small_shadows
    
    def score_pattern_confirmation(self, candles: List[Candle], 
                                   direction: str, 
                                   atr: float,
                                   nearby_level: Optional[float] = None) -> Tuple[float, List[str]]:
        """
        Score the candles for pattern confirmation.
        
        Args:
            candles: List of candles (most recent last), need at least 1-3 depending on pattern
            direction: Expected signal direction ('long' or 'short')
            atr: Average True Range for momentum detection
            nearby_level: Nearby support/resistance level for fakeout detection
        
        Returns:
            Tuple of (score out of 100, list of detected patterns)
        """
        if not candles:
            return 0, []
        
        score = 0
        patterns = []
        current_candle = candles[-1]
        prev_candle = candles[-2] if len(candles) >= 2 else None
        
        if direction == 'long':
            # Two-candle bullish patterns
            if prev_candle:
                if self.detect_bullish_engulfing(prev_candle, current_candle):
                    score += 30
                    patterns.append("bullish_engulfing")
                elif self.detect_bullish_harami(prev_candle, current_candle, atr):
                    score += 18
                    patterns.append("bullish_harami")
                elif self.detect_tweezer_bottom(prev_candle, current_candle, atr):
                    score += 15
                    patterns.append("tweezer_bottom")
                elif self.detect_inside_bar(prev_candle, current_candle):
                    score += 10
                    patterns.append("inside_bar")
            
            # Three-candle bullish patterns
            if len(candles) >= 3:
                if self.detect_morning_star(candles, atr):
                    score += 25
                    patterns.append("morning_star")
                elif self.detect_three_white_soldiers(candles, atr):
                    score += 30
                    patterns.append("three_white_soldiers")
            
            # Single-candle bullish patterns
            if self.detect_hammer(current_candle):
                score += 25
                patterns.append("hammer")
            elif self.detect_pin_bar_bullish(current_candle):
                score += 20
                patterns.append("pin_bar_bullish")
            elif self.detect_dragonfly_doji(current_candle, atr):
                score += 15
                patterns.append("dragonfly_doji")
            
            if self.detect_momentum_candle_bullish(current_candle, atr):
                score += 25
                patterns.append("momentum_bullish")
            
            # Doji patterns (indecision but can support reversal)
            if self.detect_long_legged_doji(current_candle, atr):
                score += 10
                patterns.append("long_legged_doji")
            elif self.detect_doji(current_candle, atr):
                score += 5
                patterns.append("doji")
            
            if nearby_level and self.detect_fakeout(current_candle, nearby_level, 'bullish'):
                score += 30
                patterns.append("fakeout_bullish")
        
        else:  # short
            # Two-candle bearish patterns
            if prev_candle:
                if self.detect_bearish_engulfing(prev_candle, current_candle):
                    score += 30
                    patterns.append("bearish_engulfing")
                elif self.detect_bearish_harami(prev_candle, current_candle, atr):
                    score += 18
                    patterns.append("bearish_harami")
                elif self.detect_tweezer_top(prev_candle, current_candle, atr):
                    score += 15
                    patterns.append("tweezer_top")
                elif self.detect_inside_bar(prev_candle, current_candle):
                    score += 10
                    patterns.append("inside_bar")
            
            # Three-candle bearish patterns
            if len(candles) >= 3:
                if self.detect_evening_star(candles, atr):
                    score += 25
                    patterns.append("evening_star")
                elif self.detect_three_black_crows(candles, atr):
                    score += 30
                    patterns.append("three_black_crows")
            
            # Single-candle bearish patterns
            if self.detect_shooting_star(current_candle):
                score += 25
                patterns.append("shooting_star")
            elif self.detect_pin_bar_bearish(current_candle):
                score += 20
                patterns.append("pin_bar_bearish")
            elif self.detect_gravestone_doji(current_candle, atr):
                score += 15
                patterns.append("gravestone_doji")
            
            if self.detect_momentum_candle_bearish(current_candle, atr):
                score += 25
                patterns.append("momentum_bearish")
            
            # Doji patterns (indecision but can support reversal)
            if self.detect_long_legged_doji(current_candle, atr):
                score += 10
                patterns.append("long_legged_doji")
            elif self.detect_doji(current_candle, atr):
                score += 5
                patterns.append("doji")
            
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
