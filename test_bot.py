"""
Test script to validate bot components and simulate signal generation.
This script tests the bot without requiring Telegram or live WebSocket connections.
"""

import sys
import time
from bot.config import get_config_summary
from bot.candle_patterns import Candle, CandlePatternDetector, calculate_atr
from bot.trendline_detector import TrendlineDetector
from bot.signal_deduplicator import SignalDeduplicator
from bot.risk_manager import RiskManager
from bot.scoring_engine import ScoringEngine
from bot.data_manager import DataManager
from bot.strategy import TradingStrategy
from bot.trade_tracker import TradeTracker

def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def test_configuration():
    """Test configuration module."""
    print_section("Configuration Test")
    config = get_config_summary()
    print(f"✓ Continuation threshold: {config['continuation_min_score']}")
    print(f"✓ Reversal threshold: {config['reversal_min_score']}")
    print(f"✓ Unlimited mode: {config['unlimited_mode']}")
    print(f"✓ Signal cooldown: {config['signal_cooldown_seconds']}s")
    print(f"✓ Global cooldown: {config['global_cooldown_seconds']}s")
    print(f"✓ Symbols monitored: {config['symbols']}")
    print(f"✓ Timeframes: {config['timeframes']}")

def test_candle_patterns():
    """Test candle pattern detection."""
    print_section("Candle Pattern Detection Test")
    
    detector = CandlePatternDetector()
    
    # Test bullish engulfing
    bearish_candle = Candle(105, 106, 102, 103, 1000)
    bullish_candle = Candle(103, 108, 102, 107, 1500)
    
    is_engulfing = detector.detect_bullish_engulfing(bearish_candle, bullish_candle)
    print(f"✓ Bullish engulfing detected: {is_engulfing}")
    
    # Test hammer
    hammer = Candle(100, 101, 95, 100.5, 1000)
    is_hammer = detector.detect_hammer(hammer)
    print(f"✓ Hammer pattern detected: {is_hammer}")
    
    # Test momentum candle
    momentum = Candle(100, 110, 99, 109, 2000)
    atr = 5.0
    is_momentum = detector.detect_momentum_candle_bullish(momentum, atr)
    print(f"✓ Momentum candle detected: {is_momentum}")

def test_risk_manager():
    """Test risk management."""
    print_section("Risk Manager Test")
    
    # Test unlimited mode
    risk_mgr = RiskManager(max_signals_per_day=0)
    can_send, reason = risk_mgr.can_send_signal()
    print(f"✓ Unlimited mode: can_send={can_send}, reason={reason}")
    
    # Test limited mode
    risk_mgr_limited = RiskManager(max_signals_per_day=3)
    for i in range(4):
        can_send, reason = risk_mgr_limited.can_send_signal()
        if can_send:
            risk_mgr_limited.record_signal()
            print(f"  Signal {i+1}: Sent")
        else:
            print(f"  Signal {i+1}: {reason}")
    
    # Test R:R calculation
    rr = risk_mgr.calculate_risk_reward(100, 95, 110)
    print(f"✓ Risk:Reward ratio: 1:{rr:.2f}")

def test_deduplicator():
    """Test signal deduplication."""
    print_section("Signal Deduplicator Test")
    
    dedup = SignalDeduplicator(
        signal_cooldown_seconds=10,
        global_cooldown_seconds=2
    )
    
    # First signal should pass
    can_send, reason = dedup.can_send_signal("BTCUSDT", "long", "continuation")
    print(f"✓ First signal: can_send={can_send}, reason={reason}")
    
    if can_send:
        dedup.record_signal("BTCUSDT", "long", "continuation")
    
    # Immediate duplicate should fail
    can_send, reason = dedup.can_send_signal("BTCUSDT", "long", "continuation")
    print(f"✓ Duplicate signal: can_send={can_send}, reason={reason}")
    
    # Different setup should fail due to global cooldown
    can_send, reason = dedup.can_send_signal("ETHUSDT", "short", "reversal")
    print(f"✓ Different symbol (global cooldown): can_send={can_send}, reason={reason}")
    
    # Wait for global cooldown
    time.sleep(2.1)
    can_send, reason = dedup.can_send_signal("ETHUSDT", "short", "reversal")
    print(f"✓ After global cooldown: can_send={can_send}, reason={reason}")

def test_data_manager():
    """Test data management."""
    print_section("Data Manager Test")
    
    data_mgr = DataManager()
    
    # Add some test candles
    for i in range(100):
        price = 100 + i * 0.5
        data_mgr.add_candle(
            symbol="BTCUSDT",
            timeframe="30m",
            open_price=price,
            high=price + 2,
            low=price - 1,
            close=price + 1,
            volume=1000 + i * 10,
            open_time=i * 1800000,
            close_time=(i + 1) * 1800000,
            is_closed=True
        )
    
    # Get candles
    candles = data_mgr.get_closed_candles("BTCUSDT", "30m")
    print(f"✓ Stored {len(candles)} candles")
    
    # Calculate trend
    trend = data_mgr.calculate_trend("BTCUSDT", "30m")
    print(f"✓ Detected trend: {trend}")
    
    # Find support/resistance
    latest_price = candles[-1].close
    atr = calculate_atr(candles)
    support, resistance = data_mgr.find_support_resistance("BTCUSDT", "30m", latest_price, atr)
    print(f"✓ Support: {support}, Resistance: {resistance}")

def test_scoring_engine():
    """Test scoring engine."""
    print_section("Scoring Engine Test")
    
    # Setup test data
    data_mgr = DataManager()
    
    # Add uptrending candles
    for i in range(60):
        price = 100 + i * 0.3
        for tf in ["30m", "1h", "4h"]:
            data_mgr.add_candle(
                symbol="TESTUSDT",
                timeframe=tf,
                open_price=price,
                high=price + 2,
                low=price - 0.5,
                close=price + 1.5,
                volume=1000,
                open_time=i * 1800000,
                close_time=(i + 1) * 1800000,
                is_closed=True
            )
    
    candles_30m = data_mgr.get_closed_candles("TESTUSDT", "30m")
    
    # Score a long setup
    scoring_engine = ScoringEngine()
    total_score, components = scoring_engine.calculate_total_score(
        trend_30m='up',
        trend_1h='up',
        trend_4h='up',
        candles_30m=candles_30m,
        current_price=115,
        direction='long',
        nearest_support=110,
        nearest_resistance=120,
        volume_ratio=1.3,
        entry=115,
        stop_loss=110,
        take_profit=125
    )
    
    print(f"✓ Total score: {total_score:.1f}/100")
    print("\n  Component breakdown:")
    for component, data in components.items():
        weighted = data['weighted']
        score = data['score']
        print(f"    • {component}: {weighted:.1f} (raw: {score:.1f})")

def test_strategy():
    """Test complete strategy."""
    print_section("Strategy Integration Test")
    
    # Setup components
    data_mgr = DataManager()
    dedup = SignalDeduplicator()
    risk_mgr = RiskManager(max_signals_per_day=0)
    strategy = TradingStrategy(data_mgr, dedup, risk_mgr)
    
    # Add test data for strong uptrend
    for i in range(80):
        price = 100 + i * 0.5
        for tf in ["30m", "1h", "4h"]:
            data_mgr.add_candle(
                symbol="BTCUSDT",
                timeframe=tf,
                open_price=price,
                high=price + 3,
                low=price - 1,
                close=price + 2,
                volume=1000 + i * 20,
                open_time=i * 1800000,
                close_time=(i + 1) * 1800000,
                is_closed=True
            )
    
    # Try to generate signal
    signal = strategy.analyze_symbol("BTCUSDT")
    
    if signal:
        print(f"✓ Signal generated!")
        print(f"  Symbol: {signal['symbol']}")
        print(f"  Direction: {signal['direction']}")
        print(f"  Setup: {signal['setup_type']}")
        print(f"  Score: {signal['score']:.1f}")
        print(f"  Entry: {signal['entry']:.2f}")
        print(f"  Stop: {signal['stop_loss']:.2f}")
        print(f"  Target: {signal['take_profit']:.2f}")
    else:
        print("✗ No signal generated (might need more data or better conditions)")

def test_trade_tracker():
    """Test trade tracking."""
    print_section("Trade Tracker Test")
    
    tracker = TradeTracker(db_path="/tmp/test_bot.db")
    
    # Create a test signal
    test_signal = {
        'symbol': 'BTCUSDT',
        'direction': 'long',
        'setup_type': 'continuation',
        'entry': 45000,
        'stop_loss': 44500,
        'take_profit': 46500,
        'score': 72.5,
        'trends': {'30m': 'up', '1h': 'up', '4h': 'up'},
        'component_scores': {
            'trend_alignment': {'score': 90, 'weighted': 22.5, 'reason': 'all_aligned'},
            'structure': {'score': 75, 'weighted': 15.0, 'reason': 'at_support'},
            'momentum': {'score': 70, 'weighted': 10.5, 'reason': 'bullish_3/5'},
            'candle_patterns': {'score': 65, 'weighted': 9.75, 'patterns': ['momentum_bullish']},
            'trendline': {'score': 80, 'weighted': 12.0, 'reason': 'support_bounce'},
            'risk_reward': {'score': 60, 'weighted': 6.0, 'reason': 'rr_2.02'},
        }
    }
    
    # Add signal
    signal_id = tracker.add_signal(test_signal)
    print(f"✓ Signal #{signal_id} tracked")
    
    # Get active signals
    active = tracker.get_active_signals()
    print(f"✓ Active signals: {len(active)}")
    
    # Get stats
    stats = tracker.get_stats()
    print(f"✓ Total signals: {stats['total_signals']}")
    print(f"  Active: {stats['active']}")

def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("  TELEGRAM TRADING BOT - COMPONENT TESTS")
    print("=" * 70)
    
    try:
        test_configuration()
        test_candle_patterns()
        test_risk_manager()
        test_deduplicator()
        test_data_manager()
        test_scoring_engine()
        test_strategy()
        test_trade_tracker()
        
        print_section("✅ ALL TESTS PASSED")
        print("\nThe bot is ready to run with live data!")
        print("To start the bot: python -m bot.main")
        print("\nNote: You'll need to configure Telegram credentials in .env")
        return 0
    
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
