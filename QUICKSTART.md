# Quick Start Guide

This guide will help you get the Telegram Trading Signal Bot up and running in minutes.

## Prerequisites Checklist

- [ ] Python 3.8 or higher installed
- [ ] Telegram account
- [ ] Internet connection

## Step-by-Step Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` command
3. Follow prompts to choose a name and username
4. Copy the **bot token** (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
5. Save this token - you'll need it soon

### 3. Get Your Chat ID

1. Search for [@userinfobot](https://t.me/userinfobot) on Telegram
2. Send any message to it
3. Copy your **chat ID** (a number like: `123456789`)
4. Or use [@RawDataBot](https://t.me/rawdatabot) for the same purpose

### 4. Configure Environment

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```env
TELEGRAM_BOT_TOKEN=your_actual_bot_token_here
TELEGRAM_CHAT_ID=your_actual_chat_id_here
LOG_LEVEL=INFO
```

### 5. Test the Installation

Run the test suite to verify everything works:

```bash
python3 test_bot.py
```

You should see:
```
✅ ALL TESTS PASSED
```

### 6. Start the Bot

```bash
python3 -m bot.main
```

You should see:
```
============================================================
Initializing Trading Signal Bot
============================================================
All components initialized successfully
Loading historical data...
Fetched X historical candles for BTCUSDT 30m
...
Starting WebSocket connection...
WebSocket connected successfully
```

And you'll receive a startup message on Telegram! 🎉

### 7. Monitor the Bot

The bot will:
- ✅ Load historical candle data
- ✅ Connect to Binance WebSocket
- ✅ Analyze markets in real-time
- ✅ Send quality signals to your Telegram

Logs are written to:
- Console (stdout)
- `bot.log` file

### 8. Stop the Bot

Press `Ctrl+C` to gracefully stop the bot.

## Customization

### Change Monitored Symbols

Edit `bot/config.py`:

```python
SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    # Add more symbols here
]
```

### Adjust Signal Sensitivity

Lower thresholds = more signals (but potentially lower quality):

```python
CONTINUATION_MIN_SCORE = 60  # Default: 65
REVERSAL_MIN_SCORE = 65      # Default: 70
```

Higher thresholds = fewer signals (but higher quality):

```python
CONTINUATION_MIN_SCORE = 75
REVERSAL_MIN_SCORE = 80
```

### Enable Daily Limit

If you want to limit signals per day:

```python
MAX_SIGNALS_PER_DAY = 5  # 0 = unlimited (default)
```

### Adjust Cooldowns

```python
SIGNAL_COOLDOWN_SECONDS = 3600      # 1 hour between same signals
GLOBAL_SIGNAL_COOLDOWN_SECONDS = 120  # 2 min between any signals
```

## Troubleshooting

### Bot starts but no signals?

**Check logs for rejection reasons:**
```bash
tail -f bot.log | grep REJECTED
```

Common reasons:
1. **Score too low**: Lower thresholds in config
2. **Cooldown active**: Wait for cooldown period
3. **Insufficient data**: Wait 10-15 minutes for data collection

### Telegram not working?

**Test your credentials:**
```bash
python3 -c "
from bot.telegram_notifier import TelegramNotifier
notifier = TelegramNotifier()
print(f'Enabled: {notifier.enabled}')
notifier.send_message('Test message')
"
```

If you see `Enabled: False`, check your `.env` file.

### WebSocket keeps disconnecting?

This is normal - the bot will automatically reconnect. Check:
- Network stability
- Binance API status: https://www.binance.com/en/support/announcement

### Import errors?

Reinstall dependencies:
```bash
pip install -r requirements.txt --force-reinstall
```

## Understanding Signals

### Signal Format

```
🟢 BTCUSDT - LONG 📈

Setup: Continuation
Score: 72.5/100

📊 Entry: 45250.00
🛑 Stop Loss: 44800.00 (-1.00%)
🎯 Take Profit: 46600.00 (+2.98%)
⚖️ Risk:Reward: 1:3.00

📈 Trends:
  • 30m: ⬆️ up
  • 1h: ⬆️ up
  • 4h: ⬆️ up

🔍 Component Scores:
  ✅ Trend Alignment: 25.0/25
  ✅ Structure: 18.5/25
  ⚠️ Momentum: 12.0/25
  ✅ Candle Patterns: 11.0/25
  ✅ Trendline: 14.0/25
  ⚠️ Risk Reward: 8.0/25
```

### What to Look For

**Strong signals have:**
- ✅ Score > 70
- ✅ Multi-timeframe alignment
- ✅ Risk:Reward > 2.0
- ✅ Most components show ✅ (green)

**Weaker signals have:**
- ⚠️ Score 65-70
- ⚠️ Mixed timeframe trends
- ⚠️ Risk:Reward < 2.0
- ⚠️ Multiple components show ⚠️ (yellow)

## Next Steps

1. **Monitor for 24 hours** to understand signal frequency
2. **Adjust thresholds** based on your preferences
3. **Track performance** using the SQLite database
4. **Backtest strategies** (future feature)

## Support

- **Logs**: Check `bot.log` for detailed information
- **Database**: Query `bot_data.db` for signal history
- **Issues**: Report on GitHub

## Safety Reminder

⚠️ This bot provides **alerts only** - it does not execute trades.

- Always do your own analysis
- Manage your risk appropriately
- Never invest more than you can afford to lose
- Cryptocurrency trading is highly risky

---

**Happy Trading! 📊**
