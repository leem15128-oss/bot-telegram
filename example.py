#!/usr/bin/env python3
"""
Example usage of the candlestick pattern detection and scoring system.

This script demonstrates how to:
1. Create sample candle data
2. Detect patterns
3. Score candles
4. Get detailed analysis
"""

from bot.candle_patterns import detect_all_patterns
from bot.scoring_engine import ScoringEngine, score_candles


def create_sample_data():
    """Create sample candle data for demonstration."""
    # Example: A morning star pattern (bullish reversal)
    morning_star_candles = [
        # Long bearish candle
        {'open': 110, 'high': 111, 'low': 99, 'close': 100},
        # Small star that gaps down
        {'open': 95, 'high': 96, 'low': 94, 'close': 95.5},
        # Long bullish candle
        {'open': 96, 'high': 109, 'low': 95, 'close': 108},
    ]
    
    # Example: An evening star pattern (bearish reversal)
    evening_star_candles = [
        # Long bullish candle
        {'open': 100, 'high': 111, 'low': 99, 'close': 110},
        # Small star that gaps up
        {'open': 111, 'high': 112, 'low': 110.5, 'close': 111.5},
        # Long bearish candle
        {'open': 108, 'high': 109, 'low': 95, 'close': 96},
    ]
    
    return morning_star_candles, evening_star_candles


def demo_pattern_detection():
    """Demonstrate pattern detection."""
    print("=" * 60)
    print("PATTERN DETECTION DEMO")
    print("=" * 60)
    
    morning_star, evening_star = create_sample_data()
    
    # Detect morning star
    print("\n1. Morning Star Pattern Detection:")
    print("-" * 60)
    patterns = detect_all_patterns(morning_star)
    print(f"Input: {len(morning_star)} candles")
    print(f"Detected patterns: {len(patterns)}")
    for pattern in patterns:
        print(f"  - {pattern['type']} at candle index {pattern['candle_index']}")
    
    # Detect evening star
    print("\n2. Evening Star Pattern Detection:")
    print("-" * 60)
    patterns = detect_all_patterns(evening_star)
    print(f"Input: {len(evening_star)} candles")
    print(f"Detected patterns: {len(patterns)}")
    for pattern in patterns:
        print(f"  - {pattern['type']} at candle index {pattern['candle_index']}")


def demo_scoring():
    """Demonstrate scoring functionality."""
    print("\n" + "=" * 60)
    print("SCORING ENGINE DEMO")
    print("=" * 60)
    
    morning_star, evening_star = create_sample_data()
    
    # Score morning star (bullish)
    print("\n1. Morning Star Scoring:")
    print("-" * 60)
    result = score_candles(morning_star)
    print(f"Score: {result['score']:.2f}")
    print(f"Signal: {result['signal'].upper()}")
    print(f"Patterns detected: {result['pattern_count']}")
    
    # Score evening star (bearish)
    print("\n2. Evening Star Scoring:")
    print("-" * 60)
    result = score_candles(evening_star)
    print(f"Score: {result['score']:.2f}")
    print(f"Signal: {result['signal'].upper()}")
    print(f"Patterns detected: {result['pattern_count']}")


def demo_detailed_analysis():
    """Demonstrate detailed analysis."""
    print("\n" + "=" * 60)
    print("DETAILED ANALYSIS DEMO")
    print("=" * 60)
    
    morning_star, _ = create_sample_data()
    
    engine = ScoringEngine()
    breakdown = engine.get_detailed_breakdown(morning_star)
    
    print(f"\nTotal Score: {breakdown['total_score']:.2f}")
    print(f"Bullish Score: {breakdown['bullish_score']:.2f}")
    print(f"Bearish Score: {breakdown['bearish_score']:.2f}")
    print(f"Signal: {breakdown['signal'].upper()}")
    
    print(f"\nBullish Patterns ({len(breakdown['bullish_patterns'])}):")
    for p in breakdown['bullish_patterns']:
        print(f"  - {p['type']}: weight={p['weight']}")
    
    print(f"\nBearish Patterns ({len(breakdown['bearish_patterns'])}):")
    for p in breakdown['bearish_patterns']:
        print(f"  - {p['type']}: weight={p['weight']}")


def demo_custom_weights():
    """Demonstrate custom weight configuration."""
    print("\n" + "=" * 60)
    print("CUSTOM WEIGHTS DEMO")
    print("=" * 60)
    
    morning_star, _ = create_sample_data()
    
    # Create engine with custom weights
    custom_weights = {
        'morning_star': 5.0,  # Increase importance
        'doji': 0.0,          # Ignore doji patterns
    }
    
    engine = ScoringEngine(custom_weights)
    result = engine.score_candles(morning_star)
    
    print("\nWith custom weights:")
    print(f"  morning_star weight: 5.0 (default: 2.5)")
    print(f"  doji weight: 0.0 (default: 0.5)")
    print(f"\nScore: {result['score']:.2f}")
    print(f"Signal: {result['signal'].upper()}")


def main():
    """Run all demonstrations."""
    print("\n")
    print("*" * 60)
    print("CANDLESTICK PATTERN DETECTION SYSTEM")
    print("Example Usage Demonstration")
    print("*" * 60)
    
    demo_pattern_detection()
    demo_scoring()
    demo_detailed_analysis()
    demo_custom_weights()
    
    print("\n" + "=" * 60)
    print("All demonstrations completed!")
    print("=" * 60)
    print("\nFor more information, see:")
    print("  - README.md for usage guide")
    print("  - IMPLEMENTATION.md for technical details")
    print("  - VERIFICATION.md for testing methodology")
    print()


if __name__ == '__main__':
    main()
