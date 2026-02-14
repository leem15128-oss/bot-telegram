"""
Test script for enhanced VIP message template features.
Tests new icons, sections, configurable RR_MIN and SIGNAL_TIMEFRAMES.
"""

import os
import sys
import importlib

# Set MESSAGE_TEMPLATE to vip for testing
os.environ['MESSAGE_TEMPLATE'] = 'vip'

from bot.telegram_notifier import TelegramNotifier
from bot.candle_patterns import Candle
from bot.risk_manager import RiskManager
import bot.config as config


def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def create_sample_signal(direction='long', setup_type='continuation', rr_ratio=3.89):
    """Create a sample signal for testing."""
    if direction == 'long':
        entry = 45250.0
        stop_loss = 44800.0
        tp1 = 45800.0
        tp2 = 46400.0
        tp3 = 47000.0
    else:
        entry = 45250.0
        stop_loss = 45700.0
        tp1 = 44700.0
        tp2 = 44100.0
        tp3 = 43500.0
    
    return {
        'symbol': 'BTCUSDT',
        'direction': direction,
        'setup_type': setup_type,
        'timeframe': '30m',
        'entry': entry,
        'stop_loss': stop_loss,
        'take_profit': tp3,
        'tp1': tp1,
        'tp2': tp2,
        'tp3': tp3,
        'score': 72.5,
        'trends': {
            '30m': 'up' if direction == 'long' else 'down',
            '1h': 'up' if direction == 'long' else 'down',
            '4h': 'up' if direction == 'long' else 'down',
        },
        'component_scores': {
            'trend_alignment': {'score': 90},
            'structure': {'score': 75, 'reason': f"broke_{'resistance' if direction == 'long' else 'support'}_strong_volume"},
            'candle_patterns': {
                'score': 70,
                'patterns': ['bullish_engulfing' if direction == 'long' else 'bearish_engulfing', 'hammer' if direction == 'long' else 'shooting_star']
            },
            'momentum': {'score': 80},
            'trendline': {'score': 65, 'reason': 'support trendline' if direction == 'long' else 'resistance trendline'},
        },
        'volume_ratio': 1.8,
    }


def test_enhanced_icons():
    """Test that enhanced icons are present in VIP message."""
    print_section("Enhanced Icons Test")
    
    notifier = TelegramNotifier(bot_token='test', chat_id='test')
    signal = create_sample_signal('long', 'continuation')
    
    message = notifier._format_signal_message(signal)
    
    # Check for enhanced icons
    required_icons = [
        '🟢',  # Direction emoji for long
        '📈',  # Direction arrow for long
        '📌',  # Setup icon
        '💰',  # Entry icon
        '🛑',  # Stop loss icon
        '🎯',  # Take profit icon
        '⚖️',  # RR icon
        '📊',  # Trend confirmation icon
        '🔍',  # Reasons icon
        '📋',  # Trade management icon
        '✅',  # Checkmark for reasons
        '💡',  # Footer icon
        '💰',  # Footer icon
    ]
    
    missing_icons = []
    for icon in required_icons:
        if icon not in message:
            missing_icons.append(icon)
    
    if missing_icons:
        print(f"❌ Missing icons: {', '.join(missing_icons)}")
        print(f"\nMessage:\n{message}")
        return False
    else:
        print("✓ All required icons present")
        print(f"✓ Message includes professional formatting with {len(required_icons)} different icons")
        return True


def test_trend_confirmation_section():
    """Test that trend confirmation section shows configured timeframes."""
    print_section("Trend Confirmation Section Test")
    
    notifier = TelegramNotifier(bot_token='test', chat_id='test')
    signal = create_sample_signal('long', 'continuation')
    
    message = notifier._format_signal_message(signal)
    
    # Check for trend confirmation section
    if '📊 Xác nhận xu hướng:' not in message:
        print("❌ Trend confirmation section header missing")
        return False
    
    print("✓ Trend confirmation section header present")
    
    # Check that configured timeframes are displayed
    for tf in config.SIGNAL_TIMEFRAMES:
        tf_upper = tf.upper()
        if tf_upper not in message:
            print(f"❌ Timeframe {tf_upper} not found in message")
            return False
        print(f"✓ Timeframe {tf_upper} displayed in trend confirmation")
    
    # Check for trend direction indicators
    trend_indicators = ['⬆️ Tăng', '⬇️ Giảm', '➡️ Sideway']
    found_indicator = False
    for indicator in trend_indicators:
        if indicator in message:
            found_indicator = True
            break
    
    if not found_indicator:
        print("❌ No trend direction indicators found")
        return False
    
    print("✓ Trend direction indicators present")
    return True


def test_custom_timeframes():
    """Test that custom SIGNAL_TIMEFRAMES configuration works."""
    print_section("Custom Timeframes Configuration Test")
    
    # Test with custom timeframes
    original_timeframes = config.SIGNAL_TIMEFRAMES
    os.environ['SIGNAL_TIMEFRAMES'] = '15m,1h,1d'
    importlib.reload(config)
    
    notifier = TelegramNotifier(bot_token='test', chat_id='test')
    signal = create_sample_signal('long', 'continuation')
    # Add trends for custom timeframes
    signal['trends']['15m'] = 'up'
    signal['trends']['1d'] = 'up'
    
    message = notifier._format_signal_message(signal)
    
    # Check that custom timeframes are displayed
    custom_tfs = ['15M', '1H', '1D']
    all_present = True
    for tf in custom_tfs:
        if tf not in message:
            print(f"❌ Custom timeframe {tf} not found")
            all_present = False
        else:
            print(f"✓ Custom timeframe {tf} displayed")
    
    # Restore original timeframes
    os.environ['SIGNAL_TIMEFRAMES'] = ','.join(original_timeframes)
    importlib.reload(config)
    
    if not all_present:
        return False
    
    print("✓ Custom timeframes configuration works correctly")
    return True


def test_trade_management_section():
    """Test that trade management section is present with proper formatting."""
    print_section("Trade Management Section Test")
    
    notifier = TelegramNotifier(bot_token='test', chat_id='test')
    signal = create_sample_signal('long', 'continuation')
    
    message = notifier._format_signal_message(signal)
    
    # Check for trade management section
    required_elements = [
        '📋 Quản lý lệnh / Trailing:',
        'Chốt 1/3 tại TP1',
        'Không revenge trade',
    ]
    
    missing = []
    for element in required_elements:
        if element not in message:
            missing.append(element)
    
    if missing:
        print(f"❌ Missing trade management elements: {', '.join(missing)}")
        return False
    
    print("✓ Trade management section present with all elements")
    return True


def test_rr_min_filtering():
    """Test that RR_MIN configuration filters signals correctly."""
    print_section("RR_MIN Filtering Test")
    
    risk_manager = RiskManager()
    
    # Test signal with RR = 1.5 (should pass with default RR_MIN=1.2)
    entry = 100.0
    stop = 95.0  # Risk = 5
    tp = 107.5   # Reward = 7.5, RR = 1.5
    
    is_valid, reason = risk_manager.validate_setup(entry, stop, tp, min_rr=config.RR_MIN)
    if not is_valid:
        print(f"❌ Signal with RR=1.5 rejected with RR_MIN={config.RR_MIN}: {reason}")
        return False
    
    print(f"✓ Signal with RR=1.5 accepted with RR_MIN={config.RR_MIN}")
    
    # Test signal with RR = 1.0 (should fail with RR_MIN=1.2)
    tp_low = 105.0  # Reward = 5, RR = 1.0
    
    is_valid, reason = risk_manager.validate_setup(entry, stop, tp_low, min_rr=config.RR_MIN)
    if is_valid:
        print(f"❌ Signal with RR=1.0 accepted when it should be rejected with RR_MIN={config.RR_MIN}")
        return False
    
    print(f"✓ Signal with RR=1.0 correctly rejected with RR_MIN={config.RR_MIN}: {reason}")
    
    # Test with custom RR_MIN
    print("\nTesting with custom RR_MIN=2.0...")
    original_rr = config.RR_MIN
    os.environ['RR_MIN'] = '2.0'
    importlib.reload(config)
    
    is_valid, reason = risk_manager.validate_setup(entry, stop, tp, min_rr=config.RR_MIN)
    if is_valid:
        print(f"❌ Signal with RR=1.5 accepted when RR_MIN=2.0")
        os.environ['RR_MIN'] = str(original_rr)
        importlib.reload(config)
        return False
    
    print(f"✓ Signal with RR=1.5 correctly rejected with RR_MIN=2.0: {reason}")
    
    # Restore original RR_MIN
    os.environ['RR_MIN'] = str(original_rr)
    importlib.reload(config)
    
    return True


def test_vip_structure_enhancements():
    """Test that VIP message structure includes all enhanced sections."""
    print_section("VIP Structure Enhancements Test")
    
    notifier = TelegramNotifier(bot_token='test', chat_id='test')
    signal = create_sample_signal('long', 'continuation')
    
    message = notifier._format_signal_message(signal)
    
    # Check for all major sections with their icons
    required_sections = {
        'Header with timeframe': '[30M]',
        'Setup section': '📌 Setup:',
        'Entry section': '💰 Vào lệnh:',
        'Stop loss': '🛑 SL:',
        'Take profit 1': '🎯 TP1:',
        'Risk/Reward': '⚖️ RR:',
        'Trend confirmation': '📊 Xác nhận xu hướng:',
        'Entry reasons': '🔍 Lý do vào kèo:',
        'Trade management': '📋 Quản lý lệnh / Trailing:',
        'Footer separator': '━━━━━━━━━━━━━━━━━━━',
        'Footer source': '💡 Nguồn: Posiya Tú',
    }
    
    missing_sections = []
    for section_name, section_marker in required_sections.items():
        if section_marker not in message:
            missing_sections.append(section_name)
        else:
            print(f"✓ {section_name} present")
    
    if missing_sections:
        print(f"\n❌ Missing sections: {', '.join(missing_sections)}")
        print(f"\nMessage:\n{message}")
        return False
    
    print("\n✓ All enhanced sections present in VIP message")
    return True


def test_checkmarks_in_reasons():
    """Test that reasons list uses checkmarks instead of bullets."""
    print_section("Checkmarks in Reasons Test")
    
    notifier = TelegramNotifier(bot_token='test', chat_id='test')
    signal = create_sample_signal('long', 'continuation')
    
    message = notifier._format_signal_message(signal)
    
    # Extract reasons section
    if '🔍 Lý do vào kèo:' not in message:
        print("❌ Reasons section not found")
        return False
    
    reasons_start = message.index('🔍 Lý do vào kèo:')
    reasons_end = message.index('📋 Quản lý lệnh / Trailing:', reasons_start)
    reasons_section = message[reasons_start:reasons_end]
    
    # Count checkmarks
    checkmark_count = reasons_section.count('✅')
    
    if checkmark_count == 0:
        print("❌ No checkmarks found in reasons section")
        return False
    
    print(f"✓ Found {checkmark_count} checkmarks in reasons section")
    
    # Ensure old bullet format is not present
    if '  •' in reasons_section:
        print("⚠️ Warning: Old bullet format (•) still present alongside checkmarks")
    
    print("✓ Reasons use checkmark formatting (✅)")
    return True


def main():
    """Run all enhanced VIP template tests."""
    print("\n" + "=" * 70)
    print("  ENHANCED VIP MESSAGE TEMPLATE TESTS")
    print("=" * 70)
    
    print(f"\nCurrent configuration:")
    print(f"  MESSAGE_TEMPLATE: {config.MESSAGE_TEMPLATE}")
    print(f"  RR_MIN: {config.RR_MIN}")
    print(f"  SIGNAL_TIMEFRAMES: {config.SIGNAL_TIMEFRAMES}")
    
    tests = [
        ("Enhanced Icons", test_enhanced_icons),
        ("Trend Confirmation Section", test_trend_confirmation_section),
        ("Custom Timeframes", test_custom_timeframes),
        ("Trade Management Section", test_trade_management_section),
        ("RR_MIN Filtering", test_rr_min_filtering),
        ("VIP Structure Enhancements", test_vip_structure_enhancements),
        ("Checkmarks in Reasons", test_checkmarks_in_reasons),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"\n❌ {test_name} test FAILED")
        except Exception as e:
            failed += 1
            print(f"\n❌ {test_name} test FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    if failed == 0:
        print(f"  ✅ ALL {passed} TESTS PASSED")
        print("=" * 70)
        return 0
    else:
        print(f"  ❌ {failed} TEST(S) FAILED, {passed} PASSED")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
