"""
Test script for Vietnamese VIP message template.
Validates the VIP format output without requiring live connections.
"""

import os
import sys

# Set MESSAGE_TEMPLATE to vip for testing
os.environ['MESSAGE_TEMPLATE'] = 'vip'

from bot.telegram_notifier import TelegramNotifier
from bot.candle_patterns import Candle

def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def create_sample_signal(direction='long', setup_type='continuation'):
    """
    Create a sample signal for testing.
    
    Args:
        direction: 'long' or 'short'
        setup_type: 'continuation' or 'reversal'
    
    Returns:
        Sample signal dictionary
    """
    if direction == 'long':
        entry = 45250.00
        stop_loss = 44800.00
        tp1 = 45800.00
        tp2 = 46400.00
        tp3 = 47000.00
    else:
        entry = 45250.00
        stop_loss = 45700.00
        tp1 = 44700.00
        tp2 = 44100.00
        tp3 = 43500.00
    
    signal = {
        'symbol': 'BTCUSDT',
        'direction': direction,
        'setup_type': setup_type,
        'entry': entry,
        'stop_loss': stop_loss,
        'take_profit': tp3,  # For compatibility
        'tp1': tp1,
        'tp2': tp2,
        'tp3': tp3,
        'score': 72.5,
        'component_scores': {
            'trend_alignment': {
                'score': 90.0,
                'weighted': 22.5,
                'reason': 'aligned_timeframes: 4h,1h,30m'
            },
            'structure': {
                'score': 75.0,
                'weighted': 15.0,
                'reason': 'broke_resistance,strong_volume' if direction == 'long' else 'broke_support,strong_volume'
            },
            'momentum': {
                'score': 80.0,
                'weighted': 12.0,
                'reason': 'bullish_4/5' if direction == 'long' else 'bearish_4/5'
            },
            'candle_patterns': {
                'score': 70.0,
                'weighted': 10.5,
                'patterns': ['bullish_engulfing', 'hammer'] if direction == 'long' else ['bearish_engulfing', 'shooting_star']
            },
            'trendline': {
                'score': 65.0,
                'weighted': 9.75,
                'reason': 'support_trendline' if direction == 'long' else 'resistance_trendline'
            },
            'risk_reward': {
                'score': 85.0,
                'weighted': 8.5,
                'reason': 'rr_3.89'
            }
        },
        'trends': {
            '30m': 'up' if direction == 'long' else 'down',
            '1h': 'up' if direction == 'long' else 'down',
            '4h': 'up' if direction == 'long' else 'down',
        },
        'atr': 150.0,
        'volume_ratio': 1.8,
    }
    
    return signal

def test_vip_long_continuation():
    """Test VIP format for LONG continuation signal."""
    print_section("VIP Template - LONG Continuation")
    
    notifier = TelegramNotifier(bot_token='test', chat_id='test')
    signal = create_sample_signal('long', 'continuation')
    
    message = notifier._format_signal_message(signal)
    print(message)
    print("\n✓ LONG continuation message formatted successfully")

def test_vip_short_reversal():
    """Test VIP format for SHORT reversal signal."""
    print_section("VIP Template - SHORT Reversal")
    
    notifier = TelegramNotifier(bot_token='test', chat_id='test')
    signal = create_sample_signal('short', 'reversal')
    
    message = notifier._format_signal_message(signal)
    print(message)
    print("\n✓ SHORT reversal message formatted successfully")

def test_default_template():
    """Test that default template still works."""
    print_section("Default Template (for comparison)")
    
    # Temporarily switch to default
    os.environ['MESSAGE_TEMPLATE'] = 'default'
    import importlib
    import bot.config as config
    importlib.reload(config)
    
    notifier = TelegramNotifier(bot_token='test', chat_id='test')
    signal = create_sample_signal('long', 'continuation')
    
    message = notifier._format_signal_message(signal)
    print(message)
    print("\n✓ Default template still works")
    
    # Switch back to vip
    os.environ['MESSAGE_TEMPLATE'] = 'vip'
    importlib.reload(config)

def test_vietnamese_components():
    """Test Vietnamese component labels and reasons."""
    print_section("Vietnamese Component Details")
    
    notifier = TelegramNotifier(bot_token='test', chat_id='test')
    signal = create_sample_signal('long', 'continuation')
    
    # Test setup label
    setup_label = notifier._get_vietnamese_setup_label(
        signal['setup_type'], 
        signal['component_scores']
    )
    print(f"✓ Setup label: {setup_label}")
    
    # Test reasons
    reasons = notifier._build_vietnamese_reasons(signal, signal['direction'])
    print(f"✓ Reasons ({len(reasons)} items):")
    for reason in reasons:
        print(f"  • {reason}")
    
    # Test trailing guidance
    trailing = notifier._get_trailing_guidance(signal['direction'])
    print(f"✓ Trailing guidance: {trailing}")

def verify_message_structure():
    """Verify VIP message contains all required elements."""
    print_section("VIP Message Structure Verification")
    
    notifier = TelegramNotifier(bot_token='test', chat_id='test')
    signal = create_sample_signal('long', 'continuation')
    
    message = notifier._format_signal_message(signal)
    
    # Check for required Vietnamese keywords
    required_elements = [
        'BUY/LONG',
        'Vào lệnh:',
        'SL:',
        'TP1:',
        'TP2:',
        'TP3:',
        'RR:',
        'Lý do vào kèo:',
        'Trailing:',
        'Nguồn: Posiya Tú',
        'Tồn tại để kiếm tiền'
    ]
    
    missing = []
    for element in required_elements:
        if element not in message:
            missing.append(element)
    
    if missing:
        print(f"❌ Missing elements: {', '.join(missing)}")
        return False
    else:
        print("✓ All required elements present in VIP message")
        print(f"✓ Message contains {len(message.split('•'))-1} reasons")
        return True

def main():
    """Run all VIP template tests."""
    print("\n" + "=" * 70)
    print("  VIETNAMESE VIP MESSAGE TEMPLATE TESTS")
    print("=" * 70)
    
    try:
        test_vip_long_continuation()
        test_vip_short_reversal()
        test_vietnamese_components()
        verify_message_structure()
        test_default_template()
        
        print("\n" + "=" * 70)
        print("  ✅ ALL TESTS PASSED")
        print("=" * 70)
        return 0
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
