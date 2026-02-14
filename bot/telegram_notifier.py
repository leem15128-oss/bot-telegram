"""
Telegram notification module.
Sends formatted trading signals to Telegram.
"""

import logging
import requests
from typing import Dict, Optional
import bot.config as config

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """
    Sends trading signal alerts to Telegram.
    """
    
    def __init__(self, bot_token: str = None, chat_id: str = None):
        """
        Initialize Telegram notifier.
        
        Args:
            bot_token: Telegram bot token (default from config)
            chat_id: Telegram chat ID (default from config)
        """
        self.bot_token = bot_token or config.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or config.TELEGRAM_CHAT_ID
        
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram credentials not configured - notifications disabled")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("Telegram notifier initialized")
    
    def send_signal(self, signal: Dict) -> bool:
        """
        Send a trading signal to Telegram.
        
        Args:
            signal: Signal dictionary from strategy
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.warning("Telegram not enabled, cannot send signal")
            return False
        
        message = self._format_signal_message(signal)
        return self._send_message(message)
    
    def send_message(self, text: str) -> bool:
        """
        Send a plain text message to Telegram.
        
        Args:
            text: Message text
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            return False
        
        return self._send_message(text)
    
    def _format_signal_message(self, signal: Dict) -> str:
        """
        Format signal as a pretty Telegram message.
        
        Args:
            signal: Signal dictionary
        
        Returns:
            Formatted message string
        """
        # Emoji for direction
        direction_emoji = "🟢" if signal['direction'] == 'long' else "🔴"
        setup_emoji = "📈" if signal['setup_type'] == 'continuation' else "🔄"
        
        # Calculate R:R ratio
        entry = signal['entry']
        stop = signal['stop_loss']
        target = signal['take_profit']
        risk = abs(entry - stop)
        reward = abs(target - entry)
        rr_ratio = reward / risk if risk > 0 else 0
        
        # Calculate percentages
        stop_pct = abs((stop - entry) / entry * 100)
        target_pct = abs((target - entry) / entry * 100)
        
        # Format trends
        trends = signal.get('trends', {})
        trend_30m = trends.get('30m', 'n/a')
        trend_1h = trends.get('1h', 'n/a')
        trend_4h = trends.get('4h', 'n/a')
        
        # Build message
        message = f"""
{direction_emoji} <b>{signal['symbol']}</b> - {signal['direction'].upper()} {setup_emoji}

<b>Setup:</b> {signal['setup_type'].title()}
<b>Score:</b> {signal['score']:.1f}/100

<b>📊 Entry:</b> {entry:.4f}
<b>🛑 Stop Loss:</b> {stop:.4f} (-{stop_pct:.2f}%)
<b>🎯 Take Profit:</b> {target:.4f} (+{target_pct:.2f}%)
<b>⚖️ Risk:Reward:</b> 1:{rr_ratio:.2f}

<b>📈 Trends:</b>
  • 30m: {self._trend_emoji(trend_30m)} {trend_30m}
  • 1h: {self._trend_emoji(trend_1h)} {trend_1h}
  • 4h: {self._trend_emoji(trend_4h)} {trend_4h}

<b>🔍 Component Scores:</b>
{self._format_components(signal['component_scores'])}

<i>⚠️ Alert only - not financial advice</i>
        """.strip()
        
        return message
    
    def _trend_emoji(self, trend: str) -> str:
        """Get emoji for trend direction."""
        if trend == 'up':
            return '⬆️'
        elif trend == 'down':
            return '⬇️'
        else:
            return '↔️'
    
    def _format_components(self, component_scores: Dict) -> str:
        """Format component scores for display."""
        lines = []
        for component, data in component_scores.items():
            score = data['score']
            weighted = data['weighted']
            
            # Get emoji based on score
            if score >= 75:
                emoji = '✅'
            elif score >= 50:
                emoji = '⚠️'
            else:
                emoji = '❌'
            
            component_name = component.replace('_', ' ').title()
            lines.append(f"  {emoji} {component_name}: {weighted:.1f}/25")
        
        return '\n'.join(lines)
    
    def _send_message(self, text: str) -> bool:
        """
        Send message via Telegram API.
        
        Args:
            text: Message text
        
        Returns:
            True if sent successfully
        """
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True,
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info("Telegram message sent successfully")
            return True
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    def send_startup_message(self, config_summary: Dict) -> bool:
        """
        Send bot startup notification.
        
        Args:
            config_summary: Configuration summary
        
        Returns:
            True if sent successfully
        """
        message = f"""
🤖 <b>Trading Signal Bot Started</b>

<b>Configuration:</b>
• Timeframes: {', '.join(config_summary['timeframes'])}
• Symbols: {config_summary['symbols']} monitored
• Continuation threshold: {config_summary['continuation_min_score']}
• Reversal threshold: {config_summary['reversal_min_score']}
• Daily limit: {'Unlimited' if config_summary['unlimited_mode'] else config_summary['max_signals_per_day']}
• Signal cooldown: {config_summary['signal_cooldown_seconds']}s
• Global cooldown: {config_summary['global_cooldown_seconds']}s

✅ Bot is now monitoring markets...
        """.strip()
        
        return self._send_message(message)
    
    def send_stats_update(self, stats: Dict) -> bool:
        """
        Send statistics update.
        
        Args:
            stats: Statistics dictionary
        
        Returns:
            True if sent successfully
        """
        message = f"""
📊 <b>Bot Statistics</b>

<b>Signals:</b>
• Total: {stats.get('total_signals', 0)}
• Active: {stats.get('active', 0)}
• Closed: {stats.get('closed', 0)}
• Wins: {stats.get('wins', 0)}
• Losses: {stats.get('losses', 0)}
• Win Rate: {stats.get('win_rate_pct', 0):.1f}%

<b>Performance:</b>
• Avg Score: {stats.get('avg_score', 0):.1f}
• Avg PnL: {stats.get('avg_pnl_pct', 0):.2f}%
        """.strip()
        
        return self._send_message(message)
