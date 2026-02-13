"""Telegram notifier with Vietnamese formatting."""
import asyncio
import logging
from typing import Dict, Any
from telegram import Bot
from telegram.error import TelegramError
from .config import config

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Sends trading notifications via Telegram in Vietnamese."""
    
    def __init__(self):
        self.bot_token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.bot: Bot = None
        self._enabled = bool(self.bot_token and self.chat_id)
        
        if self._enabled:
            self.bot = Bot(token=self.bot_token)
        else:
            logger.warning("Telegram not configured, notifications disabled")
    
    async def send_signal(self, signal: Dict[str, Any]):
        """Send a trading signal notification."""
        if not self._enabled:
            return
        
        try:
            # Format message in Vietnamese
            signal_type_vn = "MUA" if signal['signal_type'] == 'LONG' else "BÁN"
            model_type_vn = "Xu hướng" if signal['model_type'] == 'continuation' else "Đảo chiều"
            
            message = f"""
🔔 <b>TÍN HIỆU MỚI</b>

📊 <b>Cặp:</b> {signal['symbol']}
⏰ <b>Khung:</b> {signal['timeframe'].upper()}
📈 <b>Loại:</b> {signal_type_vn}
🎯 <b>Mô hình:</b> {model_type_vn}
⭐ <b>Điểm:</b> {signal['score']:.1f}/100

💰 <b>Giá vào:</b> ${signal['entry_price']:.4f}
🛡️ <b>Cắt lỗ:</b> ${signal['stop_loss']:.4f}
🎯 <b>Chốt lời:</b> ${signal['take_profit']:.4f}

📝 <b>Rủi ro/Lợi nhuận:</b> 1:{abs((signal['take_profit'] - signal['entry_price']) / (signal['entry_price'] - signal['stop_loss'])):.2f}
"""
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message.strip(),
                parse_mode='HTML'
            )
            
            logger.info(f"Signal sent to Telegram: {signal['symbol']}")
        
        except TelegramError as e:
            logger.error(f"Telegram error: {e}")
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
    
    async def send_trade_closed(self, trade: Dict[str, Any]):
        """Send notification when a trade is closed."""
        if not self._enabled:
            return
        
        try:
            pnl = trade.get('pnl', 0)
            pnl_percent = trade.get('pnl_percent', 0)
            
            emoji = "✅" if pnl > 0 else "❌"
            result_vn = "THẮNG" if pnl > 0 else "THUA"
            
            message = f"""
{emoji} <b>GIAO DỊCH ĐÓNG</b>

📊 <b>Cặp:</b> {trade['symbol']}
📈 <b>Loại:</b> {trade['side'].upper()}
📝 <b>Kết quả:</b> {result_vn}

💰 <b>Vào:</b> ${trade['entry_price']:.4f}
💰 <b>Ra:</b> ${trade['exit_price']:.4f}

💵 <b>Lãi/Lỗ:</b> ${pnl:.2f} ({pnl_percent:+.2f}%)

⏰ <b>Mở:</b> {trade['opened_at']}
⏰ <b>Đóng:</b> {trade['closed_at']}
"""
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message.strip(),
                parse_mode='HTML'
            )
            
            logger.info(f"Trade closed notification sent: {trade['symbol']}")
        
        except TelegramError as e:
            logger.error(f"Telegram error: {e}")
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
    
    async def send_status(self, status: Dict[str, Any]):
        """Send bot status update."""
        if not self._enabled:
            return
        
        try:
            message = f"""
📊 <b>TRẠNG THÁI BOT</b>

🎯 <b>Tỷ lệ thắng (20 GD):</b> {status.get('last_20_winrate', 0):.1f}%
📉 <b>Drawdown:</b> {status.get('current_drawdown_percent', 0):.2f}%
🔢 <b>Thua liên tiếp:</b> {status.get('consecutive_losses', 0)}

📈 <b>Xu hướng WR:</b> {status.get('continuation_winrate', 0):.1f}%
🔄 <b>Đảo chiều WR:</b> {status.get('reversal_winrate', 0):.1f}%

💰 <b>Vốn hiện tại:</b> ${status.get('current_capital', 0):.2f}

⚙️ <b>Ngưỡng điểm:</b> {status.get('score_threshold', 75)}
📊 <b>Tín hiệu hôm nay:</b> {status.get('signals_today', 0)}/{status.get('max_signals_per_day', 5)}
"""
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message.strip(),
                parse_mode='HTML'
            )
            
            logger.info("Status update sent to Telegram")
        
        except TelegramError as e:
            logger.error(f"Telegram error: {e}")
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
    
    async def send_alert(self, message: str):
        """Send a general alert message."""
        if not self._enabled:
            return
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=f"⚠️ <b>CẢNH BÁO</b>\n\n{message}",
                parse_mode='HTML'
            )
            
            logger.info(f"Alert sent: {message}")
        
        except TelegramError as e:
            logger.error(f"Telegram error: {e}")
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")


# Global Telegram notifier
telegram_notifier = TelegramNotifier()
