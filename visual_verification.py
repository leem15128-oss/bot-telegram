"""
Visual verification script for enhanced VIP message format.
Creates sample messages to showcase the improvements.
"""

import os
os.environ['MESSAGE_TEMPLATE'] = 'vip'

from bot.telegram_notifier import TelegramNotifier
from bot.candle_patterns import Candle


def create_realistic_signal(direction='long'):
    """Create a realistic signal for visual inspection."""
    if direction == 'long':
        entry = 45250.0
        stop_loss = 44800.0
        tp1 = 45800.0
        tp2 = 46400.0
        tp3 = 47000.0
        trends = {'30m': 'up', '1h': 'up', '4h': 'up'}
    else:
        entry = 45250.0
        stop_loss = 45700.0
        tp1 = 44700.0
        tp2 = 44100.0
        tp3 = 43500.0
        trends = {'30m': 'down', '1h': 'down', '4h': 'down'}
    
    return {
        'symbol': 'BTCUSDT',
        'direction': direction,
        'setup_type': 'continuation',
        'timeframe': '30m',
        'entry': entry,
        'stop_loss': stop_loss,
        'take_profit': tp3,
        'tp1': tp1,
        'tp2': tp2,
        'tp3': tp3,
        'score': 72.5,
        'trends': trends,
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


def main():
    """Display sample VIP messages."""
    print("\n" + "=" * 80)
    print("  ENHANCED VIP MESSAGE FORMAT - VISUAL VERIFICATION")
    print("=" * 80)
    
    notifier = TelegramNotifier(bot_token='test', chat_id='test')
    
    print("\n" + "-" * 80)
    print("  LONG SIGNAL EXAMPLE")
    print("-" * 80)
    signal_long = create_realistic_signal('long')
    message_long = notifier._format_signal_message(signal_long)
    print(message_long)
    
    print("\n\n" + "-" * 80)
    print("  SHORT SIGNAL EXAMPLE")
    print("-" * 80)
    signal_short = create_realistic_signal('short')
    message_short = notifier._format_signal_message(signal_short)
    print(message_short)
    
    print("\n\n" + "=" * 80)
    print("  KEY IMPROVEMENTS")
    print("=" * 80)
    print("✅ Professional header with timeframe: [30M]")
    print("✅ Enhanced icons throughout: 💰 🛑 🎯 ⚖️ 📊 🔍 📋")
    print("✅ Trend confirmation section with arrows: ⬆️ ⬇️ ➡️")
    print("✅ Checkmarks (✅) in reasons list instead of bullets")
    print("✅ Comprehensive trade management section")
    print("✅ Professional footer with separator line")
    print("✅ Configurable RR_MIN (default 1.2)")
    print("✅ Configurable SIGNAL_TIMEFRAMES (default 30m,1h,4h)")
    print("=" * 80)


if __name__ == "__main__":
    main()
