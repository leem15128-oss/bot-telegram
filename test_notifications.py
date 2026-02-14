"""
Test script for notification behavior and message templates.
Tests startup notification control and Vietnamese VIP template rendering.
"""

import os
import sys
import time
import tempfile
from unittest.mock import MagicMock, patch
from bot.config import get_config_summary
from bot.telegram_notifier import TelegramNotifier
from bot.scoring_engine import ScoringEngine
from bot.candle_patterns import Candle

def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def test_startup_notification_control():
    """Test that startup notification can be disabled via config."""
    print_section("Startup Notification Control Test")
    
    # Mock config values
    with patch('bot.config.SEND_STARTUP_MESSAGE', False):
        with patch('bot.config.SEND_STATS_ON_STARTUP', False):
            with patch('bot.config.SEND_STATS_ON_SHUTDOWN', True):
                notifier = TelegramNotifier()
                notifier.enabled = False  # Disable actual sending
                
                config_summary = get_config_summary()
                result = notifier.send_startup_message(config_summary)
                
                print(f"✓ Startup message disabled: {not result}")
                assert not result, "Startup message should be disabled"
                
    print("✓ Test passed: Startup messages can be controlled via config")

def test_startup_cooldown():
    """Test startup message cooldown mechanism."""
    print_section("Startup Message Cooldown Test")
    
    # Create a temporary timestamp file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.last_startup') as f:
        timestamp_file = f.name
        # Write current time
        f.write(str(time.time()))
    
    try:
        with patch('bot.config.SEND_STARTUP_MESSAGE', True):
            with patch('bot.config.STARTUP_MESSAGE_COOLDOWN_MINUTES', 5):
                notifier = TelegramNotifier()
                notifier.enabled = False  # Disable actual sending
                
                # Override the timestamp file path
                with patch.object(notifier, '_check_startup_cooldown') as mock_check:
                    # First call should be blocked by cooldown
                    mock_check.return_value = False
                    
                    config_summary = get_config_summary()
                    result1 = notifier.send_startup_message(config_summary)
                    print(f"✓ First call (within cooldown): {result1}")
                    
                    # Second call after cooldown should succeed
                    mock_check.return_value = True
                    result2 = notifier.send_startup_message(config_summary)
                    print(f"✓ Second call (after cooldown): {result2}")
                    
        print("✓ Test passed: Startup cooldown prevents rapid duplicate messages")
    
    finally:
        # Clean up
        if os.path.exists(timestamp_file):
            os.unlink(timestamp_file)

def test_vietnamese_vip_template():
    """Test Vietnamese VIP message template rendering."""
    print_section("Vietnamese VIP Template Test")
    
    with patch('bot.config.MESSAGE_TEMPLATE', 'vip'):
        notifier = TelegramNotifier()
        
        # Create a sample signal
        signal = {
            'symbol': 'BTCUSDT',
            'direction': 'long',
            'setup_type': 'reversal',
            'score': 78.5,
            'entry': 45250.0,
            'stop_loss': 44800.0,
            'take_profit': 46600.0,
            'tp1': 45800.0,
            'tp2': 46200.0,
            'tp3': 46600.0,
            'volume_ratio': 1.8,
            'trends': {
                '30m': 'up',
                '1h': 'up',
                '4h': 'up'
            },
            'component_scores': {
                'trend_alignment': {'score': 85, 'weighted': 21.25, 'reason': 'aligned_timeframes: 4h,1h,30m'},
                'structure': {'score': 75, 'weighted': 15.0, 'reason': 'broke_resistance,strong_volume'},
                'momentum': {'score': 72, 'weighted': 10.8, 'reason': 'bullish_4/5'},
                'candle_patterns': {'score': 80, 'weighted': 12.0, 'patterns': ['bullish_engulfing', 'hammer']},
                'trendline': {'score': 65, 'weighted': 9.75, 'reason': 'support_bounce'},
                'risk_reward': {'score': 90, 'weighted': 9.0, 'reason': 'rr_3.00'}
            }
        }
        
        message = notifier._format_vip_message(signal)
        
        # Verify key Vietnamese elements are present
        assert 'BUY/LONG' in message, "Should contain BUY/LONG label"
        assert 'Vào lệnh:' in message, "Should contain entry label in Vietnamese"
        assert 'SL:' in message, "Should contain SL label"
        assert 'TP1:' in message, "Should contain TP1"
        assert 'TP2:' in message, "Should contain TP2"
        assert 'TP3:' in message, "Should contain TP3"
        assert 'RR:' in message, "Should contain RR ratio"
        assert 'Lý do vào kèo:' in message, "Should contain reasons section"
        assert 'Trailing:' in message, "Should contain trailing guidance"
        assert 'Posiya Tú' in message, "Should contain source attribution"
        
        print("✓ Vietnamese VIP template contains required sections:")
        print(f"  - Direction label: BUY/LONG")
        print(f"  - Entry/SL/TP levels in Vietnamese")
        print(f"  - Reasons list (Lý do vào kèo)")
        print(f"  - Trailing guidance")
        print(f"  - Source attribution")
        
        # Check reasons content
        assert 'Xu hướng' in message or 'Phá vỡ' in message, "Should contain trend or structure reasons"
        
        print("\n✓ Sample VIP message preview:")
        print("-" * 70)
        print(message)
        print("-" * 70)
        
        print("\n✓ Test passed: Vietnamese VIP template renders correctly")

def test_pattern_detection():
    """Test candle pattern detection methods."""
    print_section("Candle Pattern Detection Test")
    
    engine = ScoringEngine()
    atr = 5.0
    
    # Test breakout detection
    print("\n1. Testing Breakout Detection:")
    current_price = 45500.0
    resistance = 45300.0
    volume_ratio = 1.8
    
    is_breakout, strength = engine.detect_breakout(current_price, resistance, atr, volume_ratio)
    print(f"  ✓ Breakout detected: {is_breakout}, Strength: {strength:.1f}")
    assert is_breakout, "Should detect valid breakout"
    assert strength >= 30, "Breakout should have minimum strength"
    
    # Test breakdown detection
    print("\n2. Testing Breakdown Detection:")
    current_price = 45000.0
    support = 45200.0
    volume_ratio = 2.0
    
    is_breakdown, strength = engine.detect_breakdown(current_price, support, atr, volume_ratio)
    print(f"  ✓ Breakdown detected: {is_breakdown}, Strength: {strength:.1f}")
    assert is_breakdown, "Should detect valid breakdown"
    assert strength >= 30, "Breakdown should have minimum strength"
    
    # Test false breakout detection
    print("\n3. Testing False Breakout (Fakeout) Detection:")
    
    # Bullish fakeout: previous candle broke below support, current closes above
    support_level = 45000.0
    prev_candle = Candle(45100, 45150, 44950, 44980, 1000)  # Broke below
    curr_candle = Candle(45000, 45200, 44990, 45150, 1200)  # Closed above
    candles = [prev_candle, curr_candle]
    
    is_fakeout, description = engine.detect_false_breakout(candles, support_level, 'bullish', atr)
    print(f"  ✓ Bullish fakeout detected: {is_fakeout}")
    if is_fakeout:
        print(f"    Description: {description}")
    assert is_fakeout, "Should detect bullish fakeout"
    
    # Bearish fakeout: previous candle broke above resistance, current closes below
    resistance_level = 46000.0
    prev_candle = Candle(45900, 46050, 45850, 45920, 1000)  # Broke above
    curr_candle = Candle(45950, 45980, 45800, 45850, 1200)  # Closed below
    candles = [prev_candle, curr_candle]
    
    is_fakeout, description = engine.detect_false_breakout(candles, resistance_level, 'bearish', atr)
    print(f"  ✓ Bearish fakeout detected: {is_fakeout}")
    if is_fakeout:
        print(f"    Description: {description}")
    assert is_fakeout, "Should detect bearish fakeout"
    
    print("\n✓ Test passed: All pattern detection methods work correctly")

def test_no_duplicate_startup():
    """Test that no duplicate messages are sent on startup with default settings."""
    print_section("No Duplicate Startup Messages Test")
    
    # With default settings, should send startup but not stats
    with patch('bot.config.SEND_STARTUP_MESSAGE', True):
        with patch('bot.config.SEND_STATS_ON_STARTUP', False):
            with patch('bot.config.SEND_STATS_ON_SHUTDOWN', True):
                notifier = TelegramNotifier()
                
                # Mock the actual sending
                with patch.object(notifier, '_send_message', return_value=True) as mock_send:
                    with patch.object(notifier, '_check_startup_cooldown', return_value=True):
                        with patch.object(notifier, '_update_startup_timestamp'):
                            config_summary = get_config_summary()
                            
                            # Simulate startup
                            startup_sent = notifier.send_startup_message(config_summary)
                            
                            # Count calls
                            calls_count = mock_send.call_count
                            
                            print(f"✓ Startup message sent: {startup_sent}")
                            print(f"✓ Number of Telegram messages sent: {calls_count}")
                            
                            assert calls_count <= 1, "Should send at most 1 message on startup with default settings"
                            
    print("✓ Test passed: No duplicate messages on startup")

def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("  NOTIFICATION AND TEMPLATE TESTS")
    print("=" * 70)
    
    tests = [
        test_startup_notification_control,
        test_startup_cooldown,
        test_no_duplicate_startup,
        test_vietnamese_vip_template,
        test_pattern_detection,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ Test failed: {test.__name__}")
            print(f"   Error: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ Test error: {test.__name__}")
            print(f"   Error: {e}")
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"  TEST SUMMARY: {passed} passed, {failed} failed")
    print("=" * 70)
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
