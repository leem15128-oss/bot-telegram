# Bot Telegram - Candlestick Pattern Detection

A sophisticated candlestick pattern detection and scoring system for cryptocurrency and stock trading analysis.

## Features

This bot provides comprehensive candlestick pattern detection with ATR-normalized analysis and configurable scoring:

### Supported Patterns

#### Doji Patterns
- **Standard Doji**: Small body with upper and lower shadows (indecision signal)
- **Long-Legged Doji**: Small body with very long shadows (strong indecision)
- **Dragonfly Doji**: Small body at high with long lower shadow (bullish reversal)
- **Gravestone Doji**: Small body at low with long upper shadow (bearish reversal)

#### Star Patterns (3-candle reversals)
- **Morning Star**: Bearish → Small Star (gaps down) → Bullish (strong bullish reversal)
- **Evening Star**: Bullish → Small Star (gaps up) → Bearish (strong bearish reversal)

#### Harami Patterns (2-candle reversals)
- **Bullish Harami**: Long bearish → Small bullish contained within (bullish reversal)
- **Bearish Harami**: Long bullish → Small bearish contained within (bearish reversal)

#### Tweezer Patterns (2-candle reversals)
- **Tweezer Top**: Matching highs, bearish reversal signal
- **Tweezer Bottom**: Matching lows, bullish reversal signal

#### Three Soldiers/Crows (3-candle continuation)
- **Three White Soldiers**: Three consecutive strong bullish candles (strong bullish)
- **Three Black Crows**: Three consecutive strong bearish candles (strong bearish)

## Installation

```bash
# Clone the repository
git clone https://github.com/leem15128-oss/bot-telegram.git
cd bot-telegram

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Pattern Detection

```python
from bot.candle_patterns import detect_all_patterns

# Define your candles (OHLC format)
candles = [
    {'open': 100, 'high': 105, 'low': 95, 'close': 102},
    {'open': 102, 'high': 108, 'low': 98, 'close': 106},
    # ... more candles
]

# Detect all patterns
patterns = detect_all_patterns(candles)
for pattern in patterns:
    print(f"Detected: {pattern['type']} at index {pattern['candle_index']}")
```

### Pattern Scoring

```python
from bot.scoring_engine import score_candles

# Score candles based on detected patterns
result = score_candles(candles)

print(f"Score: {result['score']}")
print(f"Signal: {result['signal']}")  # 'buy', 'sell', or 'neutral'
print(f"Patterns detected: {result['pattern_count']}")
```

### Custom Scoring Weights

```python
from bot.scoring_engine import ScoringEngine

# Create engine with custom weights
custom_weights = {
    'morning_star': 3.0,  # Increase importance
    'doji': 1.0,
    # ... other patterns
}

engine = ScoringEngine(custom_weights)
result = engine.score_candles(candles)
```

### Detailed Analysis

```python
from bot.scoring_engine import ScoringEngine

engine = ScoringEngine()
breakdown = engine.get_detailed_breakdown(candles)

print(f"Total score: {breakdown['total_score']}")
print(f"Bullish score: {breakdown['bullish_score']}")
print(f"Bearish score: {breakdown['bearish_score']}")
print(f"Bullish patterns: {breakdown['bullish_patterns']}")
print(f"Bearish patterns: {breakdown['bearish_patterns']}")
```

## Pattern Detection Methodology

### ATR Normalization
All patterns use Average True Range (ATR) normalization to adapt to different market volatilities. This ensures patterns work across different instruments and timeframes.

### Body-to-Range Ratios
Patterns analyze the ratio of candle body to total range, providing more reliable signals than absolute price movements.

### Intrabar Confirmation
The system uses closed candles for pattern structure but allows confirmation on the last candle, supporting real-time analysis.

## Scoring System

Each pattern has a predefined weight:
- **Bullish patterns**: Positive weights (e.g., Morning Star: +2.5)
- **Bearish patterns**: Negative weights (e.g., Evening Star: -2.5)
- **Neutral patterns**: Near-zero weights (e.g., Standard Doji: +0.5)

**Signal Generation:**
- Score > 1.0: **BUY** signal
- Score < -1.0: **SELL** signal
- -1.0 ≤ Score ≤ 1.0: **NEUTRAL**

## Testing

Run the comprehensive test suite:

```bash
pytest test_bot.py -v
```

All pattern detection functions are thoroughly tested with positive and negative test cases.

## Documentation

- **README.md** (this file): Overview and usage
- **IMPLEMENTATION.md**: Technical implementation details
- **VERIFICATION.md**: Testing and validation methodology

## Requirements

- Python 3.7+
- pytest (for testing)

No heavy dependencies - pure Python implementation!

## License

MIT License

## Contributing

Contributions welcome! Please ensure all tests pass before submitting pull requests.

```bash
pytest test_bot.py -v
```
