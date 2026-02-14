"""
Telegram notification module.
Sends formatted trading signals to Telegram.
"""

import logging
import requests
import os
import time
from typing import Dict, Optional, List
import bot.config as config

logger = logging.getLogger(__name__)

# Vietnamese pattern name mappings
VIETNAMESE_PATTERN_LABELS = {
    'bullish_engulfing': 'Nến nhấn chìm tăng',
    'bearish_engulfing': 'Nến nhấn chìm giảm',
    'hammer': 'Mẫu hình búa',
    'shooting_star': 'Mẫu hình sao băng',
    'pin_bar_bullish': 'Pin bar tăng',
    'pin_bar_bearish': 'Pin bar giảm',
    'morning_star': 'Mẫu hình sao mai',
    'evening_star': 'Mẫu hình sao hôm',
    'three_white_soldiers': 'Ba Người Lính Trắng',
    'three_black_crows': 'Ba Con Quạ Đen',
    'tweezer_top': 'Mẫu hình kẹp trên',
    'tweezer_bottom': 'Mẫu hình kẹp dưới',
    'bullish_harami': 'Harami tăng',
    'bearish_harami': 'Harami giảm',
    'doji': 'Nến Doji',
    'dragonfly_doji': 'Doji chuồn chuồn',
    'gravestone_doji': 'Doji bia mộ',
    'inside_bar': 'Inside bar',
    'momentum_bullish': 'Nến momentum tăng',
    'momentum_bearish': 'Nến momentum giảm',
}


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
        # Check if VIP template is enabled
        if config.MESSAGE_TEMPLATE == "vip":
            return self._format_vip_message(signal)
        else:
            return self._format_default_message(signal)
    
    def _format_default_message(self, signal: Dict) -> str:
        """
        Format signal in default English format.
        
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
    
    def _format_vip_message(self, signal: Dict) -> str:
        """
        Format signal in Vietnamese VIP format.
        
        Args:
            signal: Signal dictionary
        
        Returns:
            Formatted message string in Vietnamese VIP style
        """
        # Determine direction and setup labels in Vietnamese
        direction = signal['direction']
        setup_type = signal['setup_type']
        
        if direction == 'long':
            direction_label = "BUY/LONG"
            direction_emoji = "🟢"
        else:
            direction_label = "SELL/SHORT"
            direction_emoji = "🔴"
        
        # Map setup type to Vietnamese
        setup_label = self._get_vietnamese_setup_label(setup_type, signal.get('component_scores', {}))
        
        # Calculate R:R ratio
        entry = signal['entry']
        stop = signal['stop_loss']
        tp1 = signal.get('tp1', signal['take_profit'])
        tp2 = signal.get('tp2', signal['take_profit'])
        tp3 = signal.get('tp3', signal['take_profit'])
        
        risk = abs(entry - stop)
        reward = abs(tp3 - entry)
        rr_ratio = reward / risk if risk > 0 else 0
        
        # Build reasons list from component scores
        reasons = self._build_vietnamese_reasons(signal, direction)
        reasons_text = '\n'.join([f"  • {reason}" for reason in reasons])
        
        # Trailing guidance
        trailing_text = self._get_trailing_guidance(direction)
        
        # Build VIP message
        message = f"""
{direction_emoji} <b>{signal['symbol']}</b> - {direction_label}
<b>Setup:</b> {setup_label}

<b>Vào lệnh:</b> {entry:.4f}
<b>SL:</b> {stop:.4f}
<b>TP1:</b> {tp1:.4f}
<b>TP2:</b> {tp2:.4f}
<b>TP3:</b> {tp3:.4f}
<b>RR:</b> 1:{rr_ratio:.2f}

<b>Lý do vào kèo:</b>
{reasons_text}

<b>Trailing:</b> {trailing_text}

<i>Nguồn: Posiya Tú
Tồn tại để kiếm tiền</i>
        """.strip()
        
        return message
    
    def _get_vietnamese_setup_label(self, setup_type: str, component_scores: Dict) -> str:
        """
        Get Vietnamese label for setup type based on patterns and structure.
        
        Args:
            setup_type: 'continuation' or 'reversal'
            component_scores: Component scores dictionary
        
        Returns:
            Vietnamese setup label
        """
        # Check for specific patterns
        patterns = []
        if 'candle_patterns' in component_scores:
            patterns = component_scores['candle_patterns'].get('patterns', [])
        
        # If we have a strong pattern, use it
        for pattern in patterns:
            if pattern in VIETNAMESE_PATTERN_LABELS:
                return VIETNAMESE_PATTERN_LABELS[pattern]
        
        # Otherwise use setup type
        if setup_type == 'continuation':
            return 'Tiếp Diễn Xu Hướng'
        elif setup_type == 'reversal':
            return 'Đảo Chiều'
        else:
            return 'Tín Hiệu Giao Dịch'
    
    def _build_vietnamese_reasons(self, signal: Dict, direction: str) -> List[str]:
        """
        Build Vietnamese reasons list from component scores.
        
        Args:
            signal: Signal dictionary
            direction: 'long' or 'short'
        
        Returns:
            List of Vietnamese reasons
        """
        reasons = []
        component_scores = signal.get('component_scores', {})
        trends = signal.get('trends', {})
        
        # Trend alignment
        if 'trend_alignment' in component_scores:
            trend_score = component_scores['trend_alignment']['score']
            if trend_score >= 70:
                aligned_tfs = []
                expected_trend = 'up' if direction == 'long' else 'down'
                if trends.get('4h') == expected_trend:
                    aligned_tfs.append('4h')
                if trends.get('1h') == expected_trend:
                    aligned_tfs.append('1h')
                if trends.get('30m') == expected_trend:
                    aligned_tfs.append('30m')
                if aligned_tfs:
                    reasons.append(f"Xu hướng {', '.join(aligned_tfs)} đồng thuận")
        
        # Structure/BOS
        if 'structure' in component_scores:
            structure_score = component_scores['structure']['score']
            structure_reason = component_scores['structure'].get('reason', '')
            if structure_score >= 60:
                if 'broke_resistance' in structure_reason:
                    if 'strong_volume' in structure_reason:
                        reasons.append("Phá vỡ kháng cự mạnh với khối lượng cao (Breakout)")
                    else:
                        reasons.append("Phá vỡ kháng cự (Breakout)")
                elif 'broke_support' in structure_reason:
                    if 'strong_volume' in structure_reason:
                        reasons.append("Phá vỡ hỗ trợ mạnh với khối lượng cao (Breakdown)")
                    else:
                        reasons.append("Phá vỡ hỗ trợ (Breakdown)")
                elif 'at_support' in structure_reason:
                    reasons.append("Tại vùng hỗ trợ mạnh")
                elif 'at_resistance' in structure_reason:
                    reasons.append("Tại vùng kháng cự mạnh")
                elif 'near_support' in structure_reason:
                    reasons.append("Gần vùng hỗ trợ")
                elif 'near_resistance' in structure_reason:
                    reasons.append("Gần vùng kháng cự")
                else:
                    reasons.append("Cấu trúc thị trường hỗ trợ")
        
        # Candle patterns
        if 'candle_patterns' in component_scores:
            patterns = component_scores['candle_patterns'].get('patterns', [])
            if patterns:
                for pattern in patterns[:2]:  # First 2 patterns from the list
                    if pattern in VIETNAMESE_PATTERN_LABELS:
                        reasons.append(VIETNAMESE_PATTERN_LABELS[pattern])
        
        # Momentum
        if 'momentum' in component_scores:
            momentum_score = component_scores['momentum']['score']
            if momentum_score >= 70:
                if direction == 'long':
                    reasons.append("Momentum tăng mạnh")
                else:
                    reasons.append("Momentum giảm mạnh")
        
        # Trendline
        if 'trendline' in component_scores:
            trendline_score = component_scores['trendline']['score']
            trendline_reason = component_scores['trendline'].get('reason', '')
            if trendline_score >= 60:
                if 'support' in trendline_reason.lower():
                    reasons.append("Trendline hỗ trợ")
                elif 'resistance' in trendline_reason.lower():
                    reasons.append("Trendline kháng cự")
                elif 'break' in trendline_reason.lower():
                    reasons.append("Phá vỡ trendline")
        
        # Volume confirmation
        volume_ratio = signal.get('volume_ratio', 1.0)
        if volume_ratio >= 1.5:
            reasons.append("Khối lượng tăng mạnh")
        
        # If no reasons found, add generic ones
        if not reasons:
            reasons.append("Tín hiệu kỹ thuật phù hợp")
            if signal.get('score', 0) >= 75:
                reasons.append("Điểm số tổng thể cao")
        
        return reasons
    
    def _get_trailing_guidance(self, direction: str) -> str:
        """
        Get trailing stop guidance in Vietnamese.
        
        Args:
            direction: 'long' or 'short'
        
        Returns:
            Trailing guidance text
        """
        if direction == 'long':
            return "Dời SL lên BOS gần nhất khi chạm TP1, tiếp tục theo SR/BOS tiếp theo"
        else:
            return "Dời SL xuống BOS gần nhất khi chạm TP1, tiếp tục theo SR/BOS tiếp theo"
    
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
        # Check if startup messages are disabled
        if not config.SEND_STARTUP_MESSAGE:
            logger.info("Startup message disabled via config")
            return False
        
        # Check cooldown to prevent spam on rapid restarts
        if not self._check_startup_cooldown():
            logger.info("Startup message skipped due to cooldown")
            return False
        
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
        
        success = self._send_message(message)
        if success:
            self._update_startup_timestamp()
        return success
    
    def _check_startup_cooldown(self) -> bool:
        """
        Check if enough time has passed since last startup message.
        
        Returns:
            True if cooldown has passed, False if still in cooldown
        """
        timestamp_file = '.last_startup_message'
        cooldown_seconds = config.STARTUP_MESSAGE_COOLDOWN_MINUTES * 60
        
        try:
            if os.path.exists(timestamp_file):
                with open(timestamp_file, 'r') as f:
                    last_startup = float(f.read().strip())
                    elapsed = time.time() - last_startup
                    if elapsed < cooldown_seconds:
                        logger.debug(f"Startup cooldown active: {int(cooldown_seconds - elapsed)}s remaining")
                        return False
        except (IOError, ValueError) as e:
            logger.warning(f"Error reading startup timestamp: {e}")
        
        return True
    
    def _update_startup_timestamp(self):
        """Update the last startup message timestamp."""
        timestamp_file = '.last_startup_message'
        try:
            with open(timestamp_file, 'w') as f:
                f.write(str(time.time()))
        except IOError as e:
            logger.warning(f"Error writing startup timestamp: {e}")
    
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
