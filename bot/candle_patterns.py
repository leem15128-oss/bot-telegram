"""
Candlestick Pattern Detection Module

This module provides functions to detect various candlestick patterns
using ATR-normalized and body-to-range ratios for reliable pattern recognition.
All patterns support intrabar confirmation (use closed candles for structure,
allow last candle confirmation).
"""

from typing import List, Dict, Optional, Tuple


def calculate_atr(candles: List[Dict], period: int = 14) -> float:
    """
    Calculate Average True Range (ATR) for normalization.
    
    Args:
        candles: List of candle dictionaries with 'high', 'low', 'close' keys
        period: ATR period (default 14)
    
    Returns:
        ATR value
    """
    if len(candles) < period + 1:
        # Fall back to simple range average if not enough data
        if len(candles) < 2:
            return 0.0
        ranges = [c['high'] - c['low'] for c in candles]
        return sum(ranges) / len(ranges)
    
    true_ranges = []
    for i in range(1, len(candles)):
        high = candles[i]['high']
        low = candles[i]['low']
        prev_close = candles[i - 1]['close']
        
        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )
        true_ranges.append(tr)
    
    # Use last 'period' true ranges for ATR
    recent_trs = true_ranges[-period:] if len(true_ranges) >= period else true_ranges
    return sum(recent_trs) / len(recent_trs)


def get_body_size(candle: Dict) -> float:
    """Get candle body size (absolute difference between open and close)."""
    return abs(candle['close'] - candle['open'])


def get_range_size(candle: Dict) -> float:
    """Get candle range size (high - low)."""
    return candle['high'] - candle['low']


def get_body_to_range_ratio(candle: Dict) -> float:
    """
    Calculate body-to-range ratio.
    
    Returns:
        Ratio between 0 and 1, or 0 if range is 0
    """
    range_size = get_range_size(candle)
    if range_size == 0:
        return 0.0
    return get_body_size(candle) / range_size


def is_bullish(candle: Dict) -> bool:
    """Check if candle is bullish (close > open)."""
    return candle['close'] > candle['open']


def is_bearish(candle: Dict) -> bool:
    """Check if candle is bearish (close < open)."""
    return candle['close'] < candle['open']


def get_upper_shadow(candle: Dict) -> float:
    """Get upper shadow length."""
    return candle['high'] - max(candle['open'], candle['close'])


def get_lower_shadow(candle: Dict) -> float:
    """Get lower shadow length."""
    return min(candle['open'], candle['close']) - candle['low']


# Pattern Detection Functions

def detect_doji(candles: List[Dict], atr: Optional[float] = None) -> Dict:
    """
    Detect standard Doji pattern - small body with upper and lower shadows.
    
    A Doji indicates indecision in the market.
    
    Args:
        candles: List of candles (need at least 1)
        atr: ATR value for normalization (calculated if not provided)
    
    Returns:
        Dict with 'detected' (bool) and 'type' (str)
    """
    if len(candles) < 1:
        return {'detected': False, 'type': 'doji'}
    
    candle = candles[-1]
    body = get_body_size(candle)
    range_size = get_range_size(candle)
    
    if atr is None:
        atr = calculate_atr(candles)
    
    # Doji: very small body relative to range and ATR
    body_to_range = get_body_to_range_ratio(candle)
    is_doji = body_to_range < 0.1 and range_size > 0.3 * atr
    
    return {
        'detected': is_doji,
        'type': 'doji',
        'candle_index': len(candles) - 1
    }


def detect_long_legged_doji(candles: List[Dict], atr: Optional[float] = None) -> Dict:
    """
    Detect Long-Legged Doji - small body with very long upper and lower shadows.
    
    Indicates strong indecision with wide price range.
    
    Args:
        candles: List of candles (need at least 1)
        atr: ATR value for normalization
    
    Returns:
        Dict with 'detected' (bool) and 'type' (str)
    """
    if len(candles) < 1:
        return {'detected': False, 'type': 'long_legged_doji'}
    
    candle = candles[-1]
    range_size = get_range_size(candle)
    upper_shadow = get_upper_shadow(candle)
    lower_shadow = get_lower_shadow(candle)
    
    if atr is None:
        atr = calculate_atr(candles)
    
    # Long-legged doji: small body with both shadows being significant
    body_to_range = get_body_to_range_ratio(candle)
    has_long_shadows = (upper_shadow > 0.3 * range_size and 
                        lower_shadow > 0.3 * range_size)
    is_long_legged = (body_to_range < 0.1 and 
                      has_long_shadows and 
                      range_size > 0.5 * atr)
    
    return {
        'detected': is_long_legged,
        'type': 'long_legged_doji',
        'candle_index': len(candles) - 1
    }


def detect_dragonfly_doji(candles: List[Dict], atr: Optional[float] = None) -> Dict:
    """
    Detect Dragonfly Doji - small body at the high with long lower shadow.
    
    Bullish reversal signal when found at bottom of downtrend.
    
    Args:
        candles: List of candles (need at least 1)
        atr: ATR value for normalization
    
    Returns:
        Dict with 'detected' (bool) and 'type' (str)
    """
    if len(candles) < 1:
        return {'detected': False, 'type': 'dragonfly_doji'}
    
    candle = candles[-1]
    range_size = get_range_size(candle)
    upper_shadow = get_upper_shadow(candle)
    lower_shadow = get_lower_shadow(candle)
    
    if atr is None:
        atr = calculate_atr(candles)
    
    # Dragonfly: small body, minimal upper shadow, long lower shadow
    body_to_range = get_body_to_range_ratio(candle)
    is_dragonfly = (body_to_range < 0.1 and
                    upper_shadow < 0.1 * range_size and
                    lower_shadow > 0.6 * range_size and
                    range_size > 0.3 * atr)
    
    return {
        'detected': is_dragonfly,
        'type': 'dragonfly_doji',
        'candle_index': len(candles) - 1
    }


def detect_gravestone_doji(candles: List[Dict], atr: Optional[float] = None) -> Dict:
    """
    Detect Gravestone Doji - small body at the low with long upper shadow.
    
    Bearish reversal signal when found at top of uptrend.
    
    Args:
        candles: List of candles (need at least 1)
        atr: ATR value for normalization
    
    Returns:
        Dict with 'detected' (bool) and 'type' (str)
    """
    if len(candles) < 1:
        return {'detected': False, 'type': 'gravestone_doji'}
    
    candle = candles[-1]
    range_size = get_range_size(candle)
    upper_shadow = get_upper_shadow(candle)
    lower_shadow = get_lower_shadow(candle)
    
    if atr is None:
        atr = calculate_atr(candles)
    
    # Gravestone: small body, long upper shadow, minimal lower shadow
    body_to_range = get_body_to_range_ratio(candle)
    is_gravestone = (body_to_range < 0.1 and
                     lower_shadow < 0.1 * range_size and
                     upper_shadow > 0.6 * range_size and
                     range_size > 0.3 * atr)
    
    return {
        'detected': is_gravestone,
        'type': 'gravestone_doji',
        'candle_index': len(candles) - 1
    }


def detect_morning_star(candles: List[Dict], atr: Optional[float] = None) -> Dict:
    """
    Detect Morning Star pattern - bullish reversal (3 candles).
    
    Pattern:
    1. Long bearish candle
    2. Small-bodied candle (star) that gaps down
    3. Long bullish candle that closes above midpoint of first candle
    
    Args:
        candles: List of candles (need at least 3)
        atr: ATR value for normalization
    
    Returns:
        Dict with 'detected' (bool) and 'type' (str)
    """
    if len(candles) < 3:
        return {'detected': False, 'type': 'morning_star'}
    
    c1, c2, c3 = candles[-3], candles[-2], candles[-1]
    
    if atr is None:
        atr = calculate_atr(candles)
    
    # First candle: long bearish
    c1_bearish = is_bearish(c1)
    c1_body = get_body_size(c1)
    c1_long = c1_body > 0.6 * atr
    
    # Second candle: small body (star)
    c2_body = get_body_size(c2)
    c2_small = c2_body < 0.3 * atr
    # Star should gap down (high of star below close of first candle)
    c2_gaps_down = c2['high'] < c1['close']
    
    # Third candle: long bullish
    c3_bullish = is_bullish(c3)
    c3_body = get_body_size(c3)
    c3_long = c3_body > 0.6 * atr
    # Close above midpoint of first candle
    c1_midpoint = (c1['open'] + c1['close']) / 2
    c3_closes_high = c3['close'] > c1_midpoint
    
    is_morning_star = (c1_bearish and c1_long and
                       c2_small and c2_gaps_down and
                       c3_bullish and c3_long and c3_closes_high)
    
    return {
        'detected': is_morning_star,
        'type': 'morning_star',
        'candle_index': len(candles) - 3
    }


def detect_evening_star(candles: List[Dict], atr: Optional[float] = None) -> Dict:
    """
    Detect Evening Star pattern - bearish reversal (3 candles).
    
    Pattern:
    1. Long bullish candle
    2. Small-bodied candle (star) that gaps up
    3. Long bearish candle that closes below midpoint of first candle
    
    Args:
        candles: List of candles (need at least 3)
        atr: ATR value for normalization
    
    Returns:
        Dict with 'detected' (bool) and 'type' (str)
    """
    if len(candles) < 3:
        return {'detected': False, 'type': 'evening_star'}
    
    c1, c2, c3 = candles[-3], candles[-2], candles[-1]
    
    if atr is None:
        atr = calculate_atr(candles)
    
    # First candle: long bullish
    c1_bullish = is_bullish(c1)
    c1_body = get_body_size(c1)
    c1_long = c1_body > 0.6 * atr
    
    # Second candle: small body (star)
    c2_body = get_body_size(c2)
    c2_small = c2_body < 0.3 * atr
    # Star should gap up (low of star above close of first candle)
    c2_gaps_up = c2['low'] > c1['close']
    
    # Third candle: long bearish
    c3_bearish = is_bearish(c3)
    c3_body = get_body_size(c3)
    c3_long = c3_body > 0.6 * atr
    # Close below midpoint of first candle
    c1_midpoint = (c1['open'] + c1['close']) / 2
    c3_closes_low = c3['close'] < c1_midpoint
    
    is_evening_star = (c1_bullish and c1_long and
                       c2_small and c2_gaps_up and
                       c3_bearish and c3_long and c3_closes_low)
    
    return {
        'detected': is_evening_star,
        'type': 'evening_star',
        'candle_index': len(candles) - 3
    }


def detect_bullish_harami(candles: List[Dict], atr: Optional[float] = None) -> Dict:
    """
    Detect Bullish Harami pattern - potential bullish reversal (2 candles).
    
    Pattern:
    1. Long bearish candle
    2. Small bullish candle contained within first candle's body
    
    Args:
        candles: List of candles (need at least 2)
        atr: ATR value for normalization
    
    Returns:
        Dict with 'detected' (bool) and 'type' (str)
    """
    if len(candles) < 2:
        return {'detected': False, 'type': 'bullish_harami'}
    
    c1, c2 = candles[-2], candles[-1]
    
    if atr is None:
        atr = calculate_atr(candles)
    
    # First candle: long bearish
    c1_bearish = is_bearish(c1)
    c1_body = get_body_size(c1)
    c1_long = c1_body > 0.5 * atr
    
    # Second candle: small bullish, contained in first candle's body
    c2_bullish = is_bullish(c2)
    c2_body = get_body_size(c2)
    c2_small = c2_body < 0.5 * c1_body
    
    # Second candle contained within first candle's real body
    c1_body_high = max(c1['open'], c1['close'])
    c1_body_low = min(c1['open'], c1['close'])
    c2_contained = (c2['open'] > c1_body_low and c2['open'] < c1_body_high and
                    c2['close'] > c1_body_low and c2['close'] < c1_body_high)
    
    is_bullish_harami = c1_bearish and c1_long and c2_bullish and c2_small and c2_contained
    
    return {
        'detected': is_bullish_harami,
        'type': 'bullish_harami',
        'candle_index': len(candles) - 2
    }


def detect_bearish_harami(candles: List[Dict], atr: Optional[float] = None) -> Dict:
    """
    Detect Bearish Harami pattern - potential bearish reversal (2 candles).
    
    Pattern:
    1. Long bullish candle
    2. Small bearish candle contained within first candle's body
    
    Args:
        candles: List of candles (need at least 2)
        atr: ATR value for normalization
    
    Returns:
        Dict with 'detected' (bool) and 'type' (str)
    """
    if len(candles) < 2:
        return {'detected': False, 'type': 'bearish_harami'}
    
    c1, c2 = candles[-2], candles[-1]
    
    if atr is None:
        atr = calculate_atr(candles)
    
    # First candle: long bullish
    c1_bullish = is_bullish(c1)
    c1_body = get_body_size(c1)
    c1_long = c1_body > 0.5 * atr
    
    # Second candle: small bearish, contained in first candle's body
    c2_bearish = is_bearish(c2)
    c2_body = get_body_size(c2)
    c2_small = c2_body < 0.5 * c1_body
    
    # Second candle contained within first candle's real body
    c1_body_high = max(c1['open'], c1['close'])
    c1_body_low = min(c1['open'], c1['close'])
    c2_contained = (c2['open'] > c1_body_low and c2['open'] < c1_body_high and
                    c2['close'] > c1_body_low and c2['close'] < c1_body_high)
    
    is_bearish_harami = c1_bullish and c1_long and c2_bearish and c2_small and c2_contained
    
    return {
        'detected': is_bearish_harami,
        'type': 'bearish_harami',
        'candle_index': len(candles) - 2
    }


def detect_tweezer_top(candles: List[Dict], atr: Optional[float] = None) -> Dict:
    """
    Detect Tweezer Top pattern - bearish reversal (2 candles).
    
    Pattern: Two candles with matching highs, first bullish, second bearish.
    
    Args:
        candles: List of candles (need at least 2)
        atr: ATR value for normalization
    
    Returns:
        Dict with 'detected' (bool) and 'type' (str)
    """
    if len(candles) < 2:
        return {'detected': False, 'type': 'tweezer_top'}
    
    c1, c2 = candles[-2], candles[-1]
    
    if atr is None:
        atr = calculate_atr(candles)
    
    # First candle: bullish
    c1_bullish = is_bullish(c1)
    
    # Second candle: bearish
    c2_bearish = is_bearish(c2)
    
    # Highs should match (within small tolerance)
    tolerance = 0.1 * atr
    highs_match = abs(c1['high'] - c2['high']) <= tolerance
    
    # Both candles should have reasonable body size
    c1_body = get_body_size(c1)
    c2_body = get_body_size(c2)
    both_significant = c1_body > 0.3 * atr and c2_body > 0.3 * atr
    
    is_tweezer_top = c1_bullish and c2_bearish and highs_match and both_significant
    
    return {
        'detected': is_tweezer_top,
        'type': 'tweezer_top',
        'candle_index': len(candles) - 2
    }


def detect_tweezer_bottom(candles: List[Dict], atr: Optional[float] = None) -> Dict:
    """
    Detect Tweezer Bottom pattern - bullish reversal (2 candles).
    
    Pattern: Two candles with matching lows, first bearish, second bullish.
    
    Args:
        candles: List of candles (need at least 2)
        atr: ATR value for normalization
    
    Returns:
        Dict with 'detected' (bool) and 'type' (str)
    """
    if len(candles) < 2:
        return {'detected': False, 'type': 'tweezer_bottom'}
    
    c1, c2 = candles[-2], candles[-1]
    
    if atr is None:
        atr = calculate_atr(candles)
    
    # First candle: bearish
    c1_bearish = is_bearish(c1)
    
    # Second candle: bullish
    c2_bullish = is_bullish(c2)
    
    # Lows should match (within small tolerance)
    tolerance = 0.1 * atr
    lows_match = abs(c1['low'] - c2['low']) <= tolerance
    
    # Both candles should have reasonable body size
    c1_body = get_body_size(c1)
    c2_body = get_body_size(c2)
    both_significant = c1_body > 0.3 * atr and c2_body > 0.3 * atr
    
    is_tweezer_bottom = c1_bearish and c2_bullish and lows_match and both_significant
    
    return {
        'detected': is_tweezer_bottom,
        'type': 'tweezer_bottom',
        'candle_index': len(candles) - 2
    }


def detect_three_white_soldiers(candles: List[Dict], atr: Optional[float] = None) -> Dict:
    """
    Detect Three White Soldiers pattern - strong bullish continuation (3 candles).
    
    Pattern: Three consecutive long bullish candles with higher closes,
    each opening within the previous candle's body.
    
    Args:
        candles: List of candles (need at least 3)
        atr: ATR value for normalization
    
    Returns:
        Dict with 'detected' (bool) and 'type' (str)
    """
    if len(candles) < 3:
        return {'detected': False, 'type': 'three_white_soldiers'}
    
    c1, c2, c3 = candles[-3], candles[-2], candles[-1]
    
    if atr is None:
        atr = calculate_atr(candles)
    
    # All three candles must be bullish
    all_bullish = is_bullish(c1) and is_bullish(c2) and is_bullish(c3)
    
    # All three must have strong bodies
    c1_body = get_body_size(c1)
    c2_body = get_body_size(c2)
    c3_body = get_body_size(c3)
    all_long = (c1_body > 0.5 * atr and 
                c2_body > 0.5 * atr and 
                c3_body > 0.5 * atr)
    
    # Each close should be higher than the previous
    rising_closes = c2['close'] > c1['close'] and c3['close'] > c2['close']
    
    # Each candle should open within the previous candle's body
    c2_opens_in_c1 = c2['open'] > c1['open'] and c2['open'] < c1['close']
    c3_opens_in_c2 = c3['open'] > c2['open'] and c3['open'] < c2['close']
    opens_within_body = c2_opens_in_c1 and c3_opens_in_c2
    
    # Small upper shadows (not excessive buying exhaustion)
    c1_upper = get_upper_shadow(c1)
    c2_upper = get_upper_shadow(c2)
    c3_upper = get_upper_shadow(c3)
    small_shadows = (c1_upper < 0.3 * c1_body and
                     c2_upper < 0.3 * c2_body and
                     c3_upper < 0.3 * c3_body)
    
    is_three_white = (all_bullish and all_long and rising_closes and 
                      opens_within_body and small_shadows)
    
    return {
        'detected': is_three_white,
        'type': 'three_white_soldiers',
        'candle_index': len(candles) - 3
    }


def detect_three_black_crows(candles: List[Dict], atr: Optional[float] = None) -> Dict:
    """
    Detect Three Black Crows pattern - strong bearish continuation (3 candles).
    
    Pattern: Three consecutive long bearish candles with lower closes,
    each opening within the previous candle's body.
    
    Args:
        candles: List of candles (need at least 3)
        atr: ATR value for normalization
    
    Returns:
        Dict with 'detected' (bool) and 'type' (str)
    """
    if len(candles) < 3:
        return {'detected': False, 'type': 'three_black_crows'}
    
    c1, c2, c3 = candles[-3], candles[-2], candles[-1]
    
    if atr is None:
        atr = calculate_atr(candles)
    
    # All three candles must be bearish
    all_bearish = is_bearish(c1) and is_bearish(c2) and is_bearish(c3)
    
    # All three must have strong bodies
    c1_body = get_body_size(c1)
    c2_body = get_body_size(c2)
    c3_body = get_body_size(c3)
    all_long = (c1_body > 0.5 * atr and 
                c2_body > 0.5 * atr and 
                c3_body > 0.5 * atr)
    
    # Each close should be lower than the previous
    falling_closes = c2['close'] < c1['close'] and c3['close'] < c2['close']
    
    # Each candle should open within the previous candle's body
    c2_opens_in_c1 = c2['open'] < c1['open'] and c2['open'] > c1['close']
    c3_opens_in_c2 = c3['open'] < c2['open'] and c3['open'] > c2['close']
    opens_within_body = c2_opens_in_c1 and c3_opens_in_c2
    
    # Small lower shadows (not excessive selling exhaustion)
    c1_lower = get_lower_shadow(c1)
    c2_lower = get_lower_shadow(c2)
    c3_lower = get_lower_shadow(c3)
    small_shadows = (c1_lower < 0.3 * c1_body and
                     c2_lower < 0.3 * c2_body and
                     c3_lower < 0.3 * c3_body)
    
    is_three_black = (all_bearish and all_long and falling_closes and 
                      opens_within_body and small_shadows)
    
    return {
        'detected': is_three_black,
        'type': 'three_black_crows',
        'candle_index': len(candles) - 3
    }


def detect_all_patterns(candles: List[Dict]) -> List[Dict]:
    """
    Detect all supported candlestick patterns.
    
    Args:
        candles: List of candle dictionaries with OHLC data
    
    Returns:
        List of detected patterns (each pattern as a dict)
    """
    if not candles:
        return []
    
    atr = calculate_atr(candles)
    detected_patterns = []
    
    # Define all pattern detection functions
    pattern_detectors = [
        detect_doji,
        detect_long_legged_doji,
        detect_dragonfly_doji,
        detect_gravestone_doji,
        detect_morning_star,
        detect_evening_star,
        detect_bullish_harami,
        detect_bearish_harami,
        detect_tweezer_top,
        detect_tweezer_bottom,
        detect_three_white_soldiers,
        detect_three_black_crows,
    ]
    
    # Run all detectors
    for detector in pattern_detectors:
        result = detector(candles, atr)
        if result['detected']:
            detected_patterns.append(result)
    
    return detected_patterns
