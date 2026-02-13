# Verification and Testing

This document describes the testing and validation methodology for the candlestick pattern detection system.

## Test Coverage

The test suite (`test_bot.py`) provides comprehensive coverage with **39 tests** covering:

### 1. Helper Function Tests (8 tests)

- `test_get_body_size`: Body size calculation
- `test_get_range_size`: Range size calculation
- `test_get_body_to_range_ratio`: Body-to-range ratio calculation
- `test_is_bullish`: Bullish candle detection
- `test_is_bearish`: Bearish candle detection
- `test_get_upper_shadow`: Upper shadow calculation
- `test_get_lower_shadow`: Lower shadow calculation
- `test_calculate_atr`: ATR calculation

### 2. Pattern Detection Tests (17 tests)

Each pattern has positive and/or negative test cases:

**Doji Patterns:**
- `test_detect_doji_positive`: Should detect standard doji
- `test_detect_doji_negative`: Should NOT detect with large body
- `test_detect_long_legged_doji_positive`: Should detect long-legged variant
- `test_detect_dragonfly_doji_positive`: Should detect dragonfly variant
- `test_detect_gravestone_doji_positive`: Should detect gravestone variant

**Star Patterns:**
- `test_detect_morning_star_positive`: Should detect morning star
- `test_detect_morning_star_negative`: Should NOT detect without gap
- `test_detect_evening_star_positive`: Should detect evening star

**Harami Patterns:**
- `test_detect_bullish_harami_positive`: Should detect bullish harami
- `test_detect_bullish_harami_negative`: Should NOT detect if not contained
- `test_detect_bearish_harami_positive`: Should detect bearish harami

**Tweezer Patterns:**
- `test_detect_tweezer_top_positive`: Should detect tweezer top
- `test_detect_tweezer_bottom_positive`: Should detect tweezer bottom

**Three Soldiers/Crows:**
- `test_detect_three_white_soldiers_positive`: Should detect three white soldiers
- `test_detect_three_black_crows_positive`: Should detect three black crows

**Aggregate Detection:**
- `test_detect_all_patterns_multiple`: Multiple pattern detection
- `test_detect_all_patterns_empty`: Empty input handling

### 3. Scoring Engine Tests (11 tests)

- `test_scoring_engine_initialization`: Engine initialization
- `test_scoring_engine_custom_weights`: Custom weight configuration
- `test_get_pattern_weight`: Get weight for pattern
- `test_set_pattern_weight`: Modify pattern weight
- `test_calculate_pattern_score`: Score calculation from patterns
- `test_score_candles_bullish`: Bullish pattern scoring
- `test_score_candles_bearish`: Bearish pattern scoring
- `test_get_detailed_breakdown`: Detailed scoring breakdown
- `test_create_default_engine`: Default engine creation
- `test_score_candles_convenience_function`: Convenience function
- `test_signal_generation`: Buy/sell signal generation

### 4. Integration Tests (3 tests)

- `test_full_pipeline_morning_star`: Complete pipeline with morning star
- `test_full_pipeline_evening_star`: Complete pipeline with evening star
- `test_pattern_count`: Pattern counting in results

## Running Tests

### Run All Tests

```bash
pytest test_bot.py -v
```

Expected output:
```
================================================= test session starts ==================================================
...
================================================== 39 passed in 0.07s ==================================================
```

### Run Specific Test Category

```bash
# Test only pattern detection
pytest test_bot.py -k "detect" -v

# Test only scoring engine
pytest test_bot.py -k "scoring" -v

# Test only helper functions
pytest test_bot.py -k "test_get" -v
```

### Run with Coverage

```bash
pytest test_bot.py --cov=bot --cov-report=html
```

## Test Data Generation

Tests use helper functions to create realistic candle data:

```python
def create_candle(open_price, high, low, close):
    """Create a candle dictionary."""
    return {'open': open_price, 'high': high, 'low': low, 'close': close}

def create_bullish_candle(base=100, body=5, upper_shadow=1, lower_shadow=1):
    """Create a bullish candle with specified characteristics."""
    # Generates: low -> open -> close -> high

def create_bearish_candle(base=100, body=5, upper_shadow=1, lower_shadow=1):
    """Create a bearish candle with specified characteristics."""
    # Generates: low -> close -> open -> high
```

## Validation Methodology

### 1. Positive Tests (Pattern Should Detect)

Each pattern has at least one positive test that:
- Creates candles matching the pattern definition
- Calls the detection function
- Asserts `result['detected'] == True`
- Validates pattern type matches

Example:
```python
def test_detect_morning_star_positive():
    candles = [
        create_candle(110, 111, 99, 100),   # Long bearish
        create_candle(95, 96, 94, 95.5),    # Small star (gaps down)
        create_candle(96, 109, 95, 108),    # Long bullish (closes high)
    ]
    result = detect_morning_star(candles)
    assert result['detected']
    assert result['type'] == 'morning_star'
```

### 2. Negative Tests (Pattern Should NOT Detect)

Tests that verify pattern is NOT detected when conditions aren't met:
- Missing key characteristics (e.g., no gap in star pattern)
- Wrong candle direction
- Insufficient size requirements

Example:
```python
def test_detect_morning_star_negative():
    candles = [
        create_bearish_candle(base=100, body=8),
        create_candle(98, 100, 96, 97),  # No gap down - should fail
        create_bullish_candle(base=96, body=8),
    ]
    result = detect_morning_star(candles)
    assert not result['detected']
```

### 3. Edge Cases

Tests cover boundary conditions:
- Empty candle list
- Insufficient candles for pattern (e.g., 2 candles for 3-candle pattern)
- Zero-range candles
- Equal open/close (doji-like bodies)

### 4. Integration Tests

Full pipeline tests validate:
- Pattern detection → Scoring → Signal generation
- Multiple patterns interaction
- Score calculation accuracy
- Signal threshold logic

## Manual Verification

Beyond automated tests, patterns can be manually verified:

### Visual Verification Example

```python
from bot.candle_patterns import detect_all_patterns
from bot.scoring_engine import ScoringEngine

# Create test data
candles = [
    {'open': 110, 'high': 111, 'low': 99, 'close': 100},
    {'open': 95, 'high': 96, 'low': 94, 'close': 95.5},
    {'open': 96, 'high': 109, 'low': 95, 'close': 108},
]

# Detect and display
patterns = detect_all_patterns(candles)
print(f"Found {len(patterns)} pattern(s):")
for p in patterns:
    print(f"  - {p['type']} at index {p['candle_index']}")

# Score
engine = ScoringEngine()
result = engine.score_candles(candles)
print(f"\nScore: {result['score']}")
print(f"Signal: {result['signal']}")
```

### Real Market Data Testing

For production use, validate against historical market data:

```python
# Load real OHLC data (from CSV, API, etc.)
real_candles = load_market_data('BTC-USD', '1h')

# Detect patterns
patterns = detect_all_patterns(real_candles)

# Review detected patterns
for pattern in patterns:
    idx = pattern['candle_index']
    print(f"{pattern['type']} detected at candle {idx}")
    print(f"  Time: {real_candles[idx]['timestamp']}")
    print(f"  OHLC: {real_candles[idx]}")
```

## Continuous Integration

Recommended CI pipeline:

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest test_bot.py -v
```

## Test Results

Current test suite results:

```
✅ 39/39 tests passing (100%)
⏱️  Execution time: ~0.07s
📊 All pattern types covered
✔️  All helper functions tested
✔️  Integration tests passing
```

## Known Limitations

1. **Pattern Context**: Tests validate pattern structure but not market context (e.g., dragonfly doji is more reliable at support levels)
2. **Timeframe Independence**: Tests use arbitrary price values; real-world performance may vary by timeframe
3. **Volume**: Current implementation doesn't consider volume (future enhancement)

## Future Test Enhancements

- [ ] Add performance benchmarks (speed tests)
- [ ] Add tests for concurrent pattern detection
- [ ] Add backtesting framework integration tests
- [ ] Add property-based testing (hypothesis)
- [ ] Add stress tests with large datasets
- [ ] Add comparative tests vs. established TA libraries

## Validation Checklist

Before deployment:

- [x] All unit tests pass
- [x] All integration tests pass
- [x] Positive pattern detection validated
- [x] Negative pattern detection validated
- [x] Scoring logic validated
- [x] Signal generation validated
- [x] Edge cases handled
- [ ] Manual testing with real market data (user responsibility)
- [ ] Performance benchmarks acceptable (user responsibility)

## Reporting Issues

If you find a pattern that's incorrectly detected or missed:

1. Create a minimal test case with the exact candle data
2. Document expected vs. actual behavior
3. Submit issue with test case
4. Bonus: Submit PR with failing test + fix

Example issue report:

```python
# Expected: Should detect morning star
# Actual: Not detected

candles = [
    {'open': X, 'high': Y, 'low': Z, 'close': W},
    # ... more candles
]

result = detect_morning_star(candles)
# result['detected'] == False, but should be True
```
