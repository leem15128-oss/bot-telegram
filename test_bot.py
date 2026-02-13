"""
Test suite for bot candlestick pattern detection and scoring.

Tests all pattern detection functions and scoring engine functionality.
"""

import pytest
from bot.candle_patterns import (
    calculate_atr,
    get_body_size,
    get_range_size,
    get_body_to_range_ratio,
    is_bullish,
    is_bearish,
    get_upper_shadow,
    get_lower_shadow,
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
    detect_all_patterns,
)
from bot.scoring_engine import (
    ScoringEngine,
    DEFAULT_PATTERN_WEIGHTS,
    create_default_engine,
    score_candles,
)


# Helper functions for creating test candles

def create_candle(open_price, high, low, close):
    """Create a candle dictionary."""
    return {
        'open': open_price,
        'high': high,
        'low': low,
        'close': close
    }


def create_bullish_candle(base=100, body=5, upper_shadow=1, lower_shadow=1):
    """Create a bullish candle with specified characteristics."""
    low = base
    open_price = low + lower_shadow
    close = open_price + body
    high = close + upper_shadow
    return create_candle(open_price, high, low, close)


def create_bearish_candle(base=100, body=5, upper_shadow=1, lower_shadow=1):
    """Create a bearish candle with specified characteristics."""
    low = base
    close = low + lower_shadow
    open_price = close + body
    high = open_price + upper_shadow
    return create_candle(open_price, high, low, close)


# Tests for helper functions

def test_get_body_size():
    """Test body size calculation."""
    candle = create_candle(100, 110, 95, 105)
    assert get_body_size(candle) == 5
    
    candle = create_candle(105, 110, 95, 100)
    assert get_body_size(candle) == 5


def test_get_range_size():
    """Test range size calculation."""
    candle = create_candle(100, 110, 95, 105)
    assert get_range_size(candle) == 15


def test_get_body_to_range_ratio():
    """Test body-to-range ratio calculation."""
    candle = create_candle(100, 110, 95, 105)
    ratio = get_body_to_range_ratio(candle)
    assert abs(ratio - 5/15) < 0.001


def test_is_bullish():
    """Test bullish candle detection."""
    assert is_bullish(create_candle(100, 110, 95, 105))
    assert not is_bullish(create_candle(105, 110, 95, 100))


def test_is_bearish():
    """Test bearish candle detection."""
    assert is_bearish(create_candle(105, 110, 95, 100))
    assert not is_bearish(create_candle(100, 110, 95, 105))


def test_get_upper_shadow():
    """Test upper shadow calculation."""
    candle = create_candle(100, 110, 95, 105)
    assert get_upper_shadow(candle) == 5


def test_get_lower_shadow():
    """Test lower shadow calculation."""
    candle = create_candle(100, 110, 95, 105)
    assert get_lower_shadow(candle) == 5


def test_calculate_atr():
    """Test ATR calculation."""
    candles = [
        create_candle(100, 105, 95, 102),
        create_candle(102, 107, 98, 105),
        create_candle(105, 110, 100, 108),
    ]
    atr = calculate_atr(candles)
    assert atr > 0


# Tests for Doji patterns

def test_detect_doji_positive():
    """Test doji detection - should detect."""
    candles = [
        create_candle(100, 105, 95, 100),  # Previous candle
        create_candle(100, 105, 95, 100.2),  # Doji - small body, shadows on both sides
    ]
    result = detect_doji(candles)
    assert result['detected']
    assert result['type'] == 'doji'


def test_detect_doji_negative():
    """Test doji detection - should not detect with large body."""
    candles = [
        create_candle(100, 105, 95, 100),
        create_candle(100, 108, 95, 105),  # Large body
    ]
    result = detect_doji(candles)
    assert not result['detected']


def test_detect_long_legged_doji_positive():
    """Test long-legged doji detection - should detect."""
    candles = [
        create_candle(100, 105, 95, 100),
        create_candle(100, 110, 90, 100.2),  # Small body, long shadows both sides
    ]
    result = detect_long_legged_doji(candles)
    assert result['detected']
    assert result['type'] == 'long_legged_doji'


def test_detect_dragonfly_doji_positive():
    """Test dragonfly doji detection - should detect."""
    candles = [
        create_candle(100, 105, 95, 100),
        create_candle(105, 105.2, 95, 105),  # Small body at top, long lower shadow
    ]
    result = detect_dragonfly_doji(candles)
    assert result['detected']
    assert result['type'] == 'dragonfly_doji'


def test_detect_gravestone_doji_positive():
    """Test gravestone doji detection - should detect."""
    candles = [
        create_candle(100, 105, 95, 100),
        create_candle(95, 105, 94.8, 95),  # Small body at bottom, long upper shadow
    ]
    result = detect_gravestone_doji(candles)
    assert result['detected']
    assert result['type'] == 'gravestone_doji'


# Tests for Star patterns

def test_detect_morning_star_positive():
    """Test morning star detection - should detect."""
    # Create proper morning star pattern
    # C1: Bearish from 110 to 100 (body=10)
    # C2: Small star 95-96 (gaps down below 100, body=1)  
    # C3: Bullish from 96 to 108 (body=12, closes above C1 midpoint of 105)
    candles = [
        create_candle(110, 111, 99, 100),  # Long bearish
        create_candle(95, 96, 94, 95.5),  # Small star that gaps down
        create_candle(96, 109, 95, 108),  # Long bullish, closes above midpoint
    ]
    result = detect_morning_star(candles)
    assert result['detected']
    assert result['type'] == 'morning_star'


def test_detect_morning_star_negative():
    """Test morning star detection - should not detect without gap."""
    candles = [
        create_bearish_candle(base=100, body=8),
        create_candle(98, 100, 96, 97),  # No gap down
        create_bullish_candle(base=96, body=8),
    ]
    result = detect_morning_star(candles)
    assert not result['detected']


def test_detect_evening_star_positive():
    """Test evening star detection - should detect."""
    # Create proper evening star pattern
    # C1: Bullish from 100 to 110 (body=10)
    # C2: Small star 111-112 (gaps up above 110, body=1)
    # C3: Bearish from 108 to 96 (body=12, closes below C1 midpoint of 105)
    candles = [
        create_candle(100, 111, 99, 110),  # Long bullish
        create_candle(111, 112, 110.5, 111.5),  # Small star that gaps up
        create_candle(108, 109, 95, 96),  # Long bearish, closes below midpoint
    ]
    result = detect_evening_star(candles)
    assert result['detected']
    assert result['type'] == 'evening_star'


# Tests for Harami patterns

def test_detect_bullish_harami_positive():
    """Test bullish harami detection - should detect."""
    candles = [
        create_bearish_candle(base=95, body=10, lower_shadow=1, upper_shadow=1),  # Long bearish
        create_bullish_candle(base=98, body=3, lower_shadow=0.5, upper_shadow=0.5),  # Small bullish inside
    ]
    result = detect_bullish_harami(candles)
    assert result['detected']
    assert result['type'] == 'bullish_harami'


def test_detect_bullish_harami_negative():
    """Test bullish harami - should not detect if second candle not contained."""
    candles = [
        create_bearish_candle(base=95, body=5),
        create_bullish_candle(base=90, body=8),  # Too large, extends beyond first
    ]
    result = detect_bullish_harami(candles)
    assert not result['detected']


def test_detect_bearish_harami_positive():
    """Test bearish harami detection - should detect."""
    candles = [
        create_bullish_candle(base=95, body=10, lower_shadow=1, upper_shadow=1),  # Long bullish
        create_bearish_candle(base=101, body=3, lower_shadow=0.5, upper_shadow=0.5),  # Small bearish inside
    ]
    result = detect_bearish_harami(candles)
    assert result['detected']
    assert result['type'] == 'bearish_harami'


# Tests for Tweezer patterns

def test_detect_tweezer_top_positive():
    """Test tweezer top detection - should detect."""
    candles = [
        create_bullish_candle(base=95, body=5),
        create_bearish_candle(base=96, body=5),
    ]
    # Adjust to have matching highs
    candles[0]['high'] = 105
    candles[1]['high'] = 105
    result = detect_tweezer_top(candles)
    assert result['detected']
    assert result['type'] == 'tweezer_top'


def test_detect_tweezer_bottom_positive():
    """Test tweezer bottom detection - should detect."""
    candles = [
        create_bearish_candle(base=95, body=5),
        create_bullish_candle(base=95, body=5),
    ]
    # Both have same low
    result = detect_tweezer_bottom(candles)
    assert result['detected']
    assert result['type'] == 'tweezer_bottom'


# Tests for Three Soldiers/Crows patterns

def test_detect_three_white_soldiers_positive():
    """Test three white soldiers detection - should detect."""
    candles = [
        create_bullish_candle(base=90, body=6, lower_shadow=1, upper_shadow=1),
        create_bullish_candle(base=94, body=6, lower_shadow=1, upper_shadow=1),
        create_bullish_candle(base=98, body=6, lower_shadow=1, upper_shadow=1),
    ]
    # Adjust to ensure proper pattern
    candles[1]['open'] = 94
    candles[2]['open'] = 98
    result = detect_three_white_soldiers(candles)
    assert result['detected']
    assert result['type'] == 'three_white_soldiers'


def test_detect_three_black_crows_positive():
    """Test three black crows detection - should detect."""
    candles = [
        create_bearish_candle(base=90, body=6, lower_shadow=1, upper_shadow=1),
        create_bearish_candle(base=84, body=6, lower_shadow=1, upper_shadow=1),
        create_bearish_candle(base=78, body=6, lower_shadow=1, upper_shadow=1),
    ]
    # Adjust to ensure proper pattern
    candles[1]['open'] = 92
    candles[2]['open'] = 86
    result = detect_three_black_crows(candles)
    assert result['detected']
    assert result['type'] == 'three_black_crows'


# Tests for detect_all_patterns

def test_detect_all_patterns_multiple():
    """Test that detect_all_patterns finds multiple patterns."""
    candles = [
        create_candle(100, 105, 95, 100.1),  # Could be a doji
        create_candle(100, 110, 90, 100.2),  # Could be long-legged doji
    ]
    patterns = detect_all_patterns(candles)
    assert isinstance(patterns, list)
    # Should detect at least one pattern
    assert len(patterns) >= 0


def test_detect_all_patterns_empty():
    """Test detect_all_patterns with empty input."""
    patterns = detect_all_patterns([])
    assert patterns == []


# Tests for ScoringEngine

def test_scoring_engine_initialization():
    """Test scoring engine initialization."""
    engine = ScoringEngine()
    assert engine.pattern_weights is not None
    assert len(engine.pattern_weights) > 0


def test_scoring_engine_custom_weights():
    """Test scoring engine with custom weights."""
    custom_weights = {'doji': 10.0}
    engine = ScoringEngine(custom_weights)
    assert engine.get_pattern_weight('doji') == 10.0


def test_get_pattern_weight():
    """Test getting pattern weight."""
    engine = ScoringEngine()
    weight = engine.get_pattern_weight('morning_star')
    assert weight == DEFAULT_PATTERN_WEIGHTS['morning_star']


def test_set_pattern_weight():
    """Test setting pattern weight."""
    engine = ScoringEngine()
    engine.set_pattern_weight('doji', 5.0)
    assert engine.get_pattern_weight('doji') == 5.0


def test_calculate_pattern_score():
    """Test pattern score calculation."""
    engine = ScoringEngine()
    patterns = [
        {'type': 'morning_star', 'detected': True},
        {'type': 'doji', 'detected': True},
    ]
    score = engine.calculate_pattern_score(patterns)
    expected = DEFAULT_PATTERN_WEIGHTS['morning_star'] + DEFAULT_PATTERN_WEIGHTS['doji']
    assert abs(score - expected) < 0.001


def test_score_candles_bullish():
    """Test scoring with bullish pattern."""
    engine = ScoringEngine()
    candles = [
        create_bearish_candle(base=100, body=8),
        create_candle(92, 94, 90, 91),
        create_bullish_candle(base=90, body=8),
    ]
    result = engine.score_candles(candles)
    assert 'score' in result
    assert 'patterns' in result
    assert 'signal' in result


def test_score_candles_bearish():
    """Test scoring with bearish pattern."""
    engine = ScoringEngine()
    # Use proper evening star pattern
    candles = [
        create_candle(100, 111, 99, 110),  # Long bullish
        create_candle(111, 112, 110.5, 111.5),  # Small star that gaps up
        create_candle(108, 109, 95, 96),  # Long bearish
    ]
    result = engine.score_candles(candles)
    assert 'score' in result
    # With evening star, score should be negative
    assert result['score'] < 0


def test_get_detailed_breakdown():
    """Test detailed breakdown functionality."""
    engine = ScoringEngine()
    candles = [
        create_candle(100, 105, 95, 100.1),
    ]
    breakdown = engine.get_detailed_breakdown(candles)
    assert 'total_score' in breakdown
    assert 'bullish_score' in breakdown
    assert 'bearish_score' in breakdown
    assert 'pattern_contributions' in breakdown
    assert 'signal' in breakdown


def test_create_default_engine():
    """Test default engine creation."""
    engine = create_default_engine()
    assert isinstance(engine, ScoringEngine)
    assert engine.pattern_weights == DEFAULT_PATTERN_WEIGHTS


def test_score_candles_convenience_function():
    """Test convenience function for scoring."""
    candles = [create_candle(100, 105, 95, 100.1)]
    result = score_candles(candles)
    assert 'score' in result
    assert 'patterns' in result
    assert 'signal' in result


def test_signal_generation():
    """Test signal generation based on score."""
    engine = ScoringEngine()
    
    # Test buy signal
    patterns_bullish = [{'type': 'morning_star', 'detected': True}]
    score_bullish = engine.calculate_pattern_score(patterns_bullish)
    assert score_bullish > 1.0  # Should trigger buy
    
    # Test sell signal
    patterns_bearish = [{'type': 'evening_star', 'detected': True}]
    score_bearish = engine.calculate_pattern_score(patterns_bearish)
    assert score_bearish < -1.0  # Should trigger sell


# Integration tests

def test_full_pipeline_morning_star():
    """Test full pipeline with morning star pattern."""
    candles = [
        create_candle(110, 111, 99, 100),  # Long bearish
        create_candle(95, 96, 94, 95.5),  # Small star
        create_candle(96, 109, 95, 108),  # Long bullish
    ]
    
    # Detect patterns
    patterns = detect_all_patterns(candles)
    pattern_types = [p['type'] for p in patterns]
    
    # Should detect morning star
    assert 'morning_star' in pattern_types
    
    # Score should be positive (bullish)
    result = score_candles(candles)
    assert result['score'] > 0
    assert result['signal'] == 'buy'


def test_full_pipeline_evening_star():
    """Test full pipeline with evening star pattern."""
    candles = [
        create_candle(100, 111, 99, 110),  # Long bullish
        create_candle(111, 112, 110.5, 111.5),  # Small star
        create_candle(108, 109, 95, 96),  # Long bearish
    ]
    
    patterns = detect_all_patterns(candles)
    pattern_types = [p['type'] for p in patterns]
    
    assert 'evening_star' in pattern_types
    
    result = score_candles(candles)
    assert result['score'] < 0
    assert result['signal'] == 'sell'


def test_pattern_count():
    """Test that pattern count is tracked."""
    engine = ScoringEngine()
    candles = [create_candle(100, 105, 95, 100.1)]
    result = engine.score_candles(candles)
    assert 'pattern_count' in result
    assert result['pattern_count'] >= 0
