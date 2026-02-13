"""
Notifier - Sends trading signals to Telegram in Vietnamese format
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict
import aiohttp

from . import config
from .utils import format_price, format_percentage

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Sends formatted notifications to Telegram"""
    
    def __init__(self):
        self.bot_token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    async def send_signal(self, signal_data: Dict):
        """
        Send trading signal to Telegram
        Format matches the Vietnamese screenshot style
        """
        
        try:
            message = self._format_signal_message(signal_data)
            await self._send_message(message)
            logger.info(f"Signal sent to Telegram: {signal_data['symbol']}")
            
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}", exc_info=True)
    
    def _format_signal_message(self, signal: Dict) -> str:
        """
        Format signal message in Vietnamese style matching screenshot
        """
        
        symbol = signal['symbol']
        direction = signal['direction']  # 'long' or 'short'
        entry = signal['entry']
        sl = signal['sl']
        tp1 = signal['tp1']
        tp2 = signal['tp2']
        tp3 = signal['tp3']
        score = signal['score']
        rr = signal['rr']
        reasons = signal.get('reasons', [])
        
        # Calculate percentages
        sl_pct = abs((sl - entry) / entry) * 100
        tp1_pct = abs((tp1 - entry) / entry) * 100
        tp2_pct = abs((tp2 - entry) / entry) * 100
        tp3_pct = abs((tp3 - entry) / entry) * 100
        
        # Determine action (MUA = Buy, BÁN = Sell)
        if direction == 'long':
            action = "🟢🟢 MUA"
            action_verb = "MUA"
        else:
            action = "🔴🔴 BÁN"
            action_verb = "BÁN"
        
        # Build message
        lines = []
        
        # Header line
        lines.append(f"{action} {symbol}")
        lines.append("")
        
        # Entry
        lines.append(f"📍 Entry: {format_price(entry)}")
        
        # Stop Loss
        lines.append(f"🛑 SL: {format_price(sl)} (-{sl_pct:.2f}%)")
        
        # Take Profits
        lines.append(f"🎯 TP1: {format_price(tp1)} (+{tp1_pct:.2f}%)")
        lines.append(f"🎯 TP2: {format_price(tp2)} (+{tp2_pct:.2f}%)")
        lines.append(f"🎯 TP3: {format_price(tp3)} (+{tp3_pct:.2f}%)")
        lines.append("")
        
        # RR and metrics
        winrate = signal.get('winrate', 0)
        ev = signal.get('ev', 0)
        
        lines.append(f"📊 RR: 1:{rr:.1f} | WR: {winrate:.0f}% | EV: {ev:.1f}%")
        lines.append("")
        
        # Trailing guidance
        lines.append(f"📈 Trailing: Chốt 50% tại TP1, dời SL về Entry")
        lines.append("")
        
        # Reasons
        lines.append("✅ Lý do vào kèo:")
        for reason in reasons:
            lines.append(f"  ✓ {reason}")
        lines.append("")
        
        # Footer
        current_date = datetime.utcnow().strftime("%d/%m/%Y")
        lines.append(f"📅 {current_date}")
        lines.append(f"📌 Nguồn: {config.NOTIFICATION_SOURCE}")
        lines.append(f'💭 "{config.NOTIFICATION_QUOTE}"')
        
        return "\n".join(lines)
    
    async def _send_message(self, text: str):
        """Send message via Telegram API"""
        
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram credentials not configured, skipping notification")
            return
        
        url = f"{self.api_url}/sendMessage"
        
        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Telegram API error: {error_text}")
                    else:
                        logger.debug("Telegram message sent successfully")
        
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
    
    async def send_alert(self, message: str):
        """Send a simple alert message"""
        
        try:
            await self._send_message(f"⚠️ {message}")
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
    
    async def send_status(self, status_data: Dict):
        """Send bot status update"""
        
        try:
            lines = []
            lines.append("📊 <b>Bot Status</b>")
            lines.append("")
            
            for key, value in status_data.items():
                lines.append(f"{key}: {value}")
            
            message = "\n".join(lines)
            await self._send_message(message)
            
        except Exception as e:
            logger.error(f"Failed to send status: {e}")
