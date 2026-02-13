# Implementation Details

This document provides technical details about the candlestick pattern detection implementation.

## Architecture

The system is composed of two main modules:

### 1. Pattern Detection Module (`bot/candle_patterns.py`)

#### Core Components

**Helper Functions:**
- `calculate_atr()`: Calculates Average True Range for normalization
- `get_body_size()`: Returns candle body absolute size
- `get_range_size()`: Returns candle total range (high - low)
- `get_body_to_range_ratio()`: Calculates body/range ratio (0-1)
- `is_bullish()`, `is_bearish()`: Direction detection
- `get_upper_shadow()`, `get_lower_shadow()`: Shadow calculations

**Pattern Detection Functions:**

Each pattern has a dedicated detection function following this signature:
```python
def detect_pattern(candles: List[Dict], atr: Optional[float] = None) -> Dict
```

Returns:
```python
{
    'detected': bool,        # True if pattern found
    'type': str,            # Pattern name
    'candle_index': int     # Starting index of pattern
}
```

### 2. Scoring Engine Module (`bot/scoring_engine.py`)

The `ScoringEngine` class provides:
- Configurable pattern weights
- Pattern scoring calculation
- Signal generation (buy/sell/neutral)
- Detailed scoring breakdowns

## Pattern Implementation Details

### ATR Calculation

```python
def calculate_atr(candles: List[Dict], period: int = 14) -> float
```

Uses the True Range formula:
```
TR = max(high - low, |high - prev_close|, |low - prev_close|)
ATR = average of TR over period
```

Fallback: If insufficient data, uses simple range average.

### Doji Family

**Standard Doji:**
- Body-to-range ratio < 0.1
- Range > 0.3 × ATR (to filter noise)
- Indicates market indecision

**Long-Legged Doji:**
- Standard Doji criteria
- Upper shadow > 30% of range
- Lower shadow > 30% of range
- Range > 0.5 × ATR
- Strong indecision signal

**Dragonfly Doji:**
- Body-to-range ratio < 0.1
- Upper shadow < 10% of range (body at top)
- Lower shadow > 60% of range (long tail)
- Range > 0.3 × ATR
- Bullish reversal when at support

**Gravestone Doji:**
- Body-to-range ratio < 0.1
- Lower shadow < 10% of range (body at bottom)
- Upper shadow > 60% of range (long wick)
- Range > 0.3 × ATR
- Bearish reversal when at resistance

### Star Patterns

**Morning Star (Bullish Reversal):**

3-candle pattern:
1. Long bearish candle (body > 0.6 × ATR)
2. Small-bodied star (body < 0.3 × ATR) that gaps down
   - Gap: star's high < first candle's close
3. Long bullish candle (body > 0.6 × ATR)
   - Closes above midpoint of first candle

**Evening Star (Bearish Reversal):**

3-candle pattern (inverse of Morning Star):
1. Long bullish candle (body > 0.6 × ATR)
2. Small-bodied star (body < 0.3 × ATR) that gaps up
   - Gap: star's low > first candle's close
3. Long bearish candle (body > 0.6 × ATR)
   - Closes below midpoint of first candle

### Harami Patterns

**Bullish Harami:**

2-candle pattern:
1. Long bearish candle (body > 0.5 × ATR)
2. Small bullish candle (body < 50% of first candle's body)
   - Completely contained within first candle's real body
   - Both open and close within first candle's body range

**Bearish Harami:**

2-candle pattern (inverse):
1. Long bullish candle (body > 0.5 × ATR)
2. Small bearish candle (body < 50% of first candle's body)
   - Completely contained within first candle's real body

### Tweezer Patterns

**Tweezer Top (Bearish):**

2-candle pattern:
1. Bullish candle with significant body (> 0.3 × ATR)
2. Bearish candle with significant body (> 0.3 × ATR)
- Matching highs (within 0.1 × ATR tolerance)
- Indicates resistance level

**Tweezer Bottom (Bullish):**

2-candle pattern:
1. Bearish candle with significant body (> 0.3 × ATR)
2. Bullish candle with significant body (> 0.3 × ATR)
- Matching lows (within 0.1 × ATR tolerance)
- Indicates support level

### Three Soldiers/Crows

**Three White Soldiers (Strong Bullish):**

3-candle pattern:
- All three candles bullish
- Each body > 0.5 × ATR
- Rising closes (each higher than previous)
- Each opens within previous candle's body
- Small upper shadows (< 30% of body) - no exhaustion

**Three Black Crows (Strong Bearish):**

3-candle pattern (inverse):
- All three candles bearish
- Each body > 0.5 × ATR
- Falling closes (each lower than previous)
- Each opens within previous candle's body
- Small lower shadows (< 30% of body) - no exhaustion

## Scoring System

### Default Pattern Weights

```python
DEFAULT_PATTERN_WEIGHTS = {
    # Doji patterns - neutral/reversal indicators
    'doji': 0.5,
    'long_legged_doji': 0.6,
    'dragonfly_doji': 1.5,      # Bullish at support
    'gravestone_doji': -1.5,     # Bearish at resistance
    
    # Star patterns - strong reversals
    'morning_star': 2.5,         # Strong bullish
    'evening_star': -2.5,        # Strong bearish
    
    # Harami patterns - reversals
    'bullish_harami': 1.5,
    'bearish_harami': -1.5,
    
    # Tweezer patterns - reversals
    'tweezer_bottom': 1.8,       # Bullish
    'tweezer_top': -1.8,         # Bearish
    
    # Three soldiers/crows - strong continuation
    'three_white_soldiers': 3.0, # Very strong bullish
    'three_black_crows': -3.0,   # Very strong bearish
}
```

### Score Calculation

```python
total_score = sum(weight for pattern in detected_patterns)
```

### Signal Generation

- `score > 1.0`: BUY signal (bullish patterns dominate)
- `score < -1.0`: SELL signal (bearish patterns dominate)
- `-1.0 ≤ score ≤ 1.0`: NEUTRAL (weak or conflicting signals)

## Intrabar Confirmation

The pattern detection system follows these principles:

1. **Closed Candles for Structure**: Historical candles (all but the last) must be fully formed
2. **Last Candle Confirmation**: The most recent candle can be used for pattern completion
3. **Real-time Support**: Enables live trading signal generation

Example: For a Morning Star detected on live data, candles[0] and candles[1] must be closed, but candles[2] (the confirming bullish candle) can be forming.

## Data Format

Input candles must be dictionaries with OHLC data:

```python
{
    'open': float,   # Opening price
    'high': float,   # Highest price
    'low': float,    # Lowest price
    'close': float   # Closing price
}
```

Candles should be ordered chronologically (oldest first).

## Performance Considerations

- **Pure Python**: No heavy dependencies for fast loading
- **Single-pass Detection**: Each pattern detector runs in O(1) time
- **Efficient ATR**: Calculated once and reused across all patterns
- **Minimal Memory**: Patterns examine only the most recent 1-3 candles

## Extension Points

### Adding New Patterns

1. Create detection function in `candle_patterns.py`:
```python
def detect_new_pattern(candles: List[Dict], atr: Optional[float] = None) -> Dict:
    # Implementation
    return {'detected': bool, 'type': 'pattern_name', 'candle_index': int}
```

2. Add to `detect_all_patterns()` detector list

3. Add weight to `DEFAULT_PATTERN_WEIGHTS` in `scoring_engine.py`

4. Add tests in `test_bot.py`

### Custom Weights

Users can override default weights:

```python
engine = ScoringEngine({
    'morning_star': 5.0,  # Custom weight
    'doji': 0.0,          # Ignore pattern
})
```

## Testing Strategy

See `VERIFICATION.md` for detailed testing methodology.

Key testing principles:
- Unit tests for each helper function
- Positive tests (pattern should be detected)
- Negative tests (pattern should NOT be detected)
- Integration tests (full pipeline)
- Edge cases (empty data, insufficient candles)
