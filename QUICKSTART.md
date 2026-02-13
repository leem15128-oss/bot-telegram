# Quick Start Guide

## Institutional Price Action Swing Bot v2

### Installation (5 minutes)

```bash
# 1. Clone the repository
git clone https://github.com/leem15128-oss/bot-telegram.git
cd bot-telegram

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Configure credentials
cp .env.example .env
nano .env  # Add your Telegram bot token and chat ID

# 4. Run the bot
python -m bot.main
```

### Getting Telegram Credentials

1. **Create a Bot:**
   - Message [@BotFather](https://t.me/botfather) on Telegram
   - Send `/newbot` and follow instructions
   - Copy the bot token (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

2. **Get Your Chat ID:**
   - Message [@userinfobot](https://t.me/userinfobot) on Telegram
   - Copy the ID shown (looks like `123456789`)

3. **Update .env:**
   ```
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   TELEGRAM_CHAT_ID=123456789
   LOG_LEVEL=INFO
   ```

### First Run

The bot will:
1. ✅ Initialize symbol engine (fetch top 300 volume symbols)
2. ✅ Start WebSocket connections (sharded for efficiency)
3. ✅ Warm up historical data for active symbols
4. ✅ Begin scanning for trading opportunities
5. ✅ Send Telegram notification when signal found

### Monitoring

**View Logs:**
```bash
tail -f data/bot.log
```

**Check Trades:**
```bash
sqlite3 data/trades.db "SELECT symbol, model_type, entry, score FROM trades ORDER BY timestamp DESC LIMIT 10;"
```

**Check Memory State:**
```bash
sqlite3 data/memory.db "SELECT * FROM memory_state WHERE id = 1;"
```

### Adding Trade Outcomes

Create/edit `data/outcomes.csv`:

```csv
date_utc,symbol,model_type,outcome
2024-01-15,BTCUSDT,continuation,TP1
2024-01-15,ETHUSDT,continuation,TP2
2024-01-16,BNBUSDT,reversal,SL
```

**Outcome values:**
- `TP1` = Hit Take Profit 1 (+1R)
- `TP2` = Hit Take Profit 2 (+2R)
- `TP3` = Hit Take Profit 3 (+3R)
- `SL` = Hit Stop Loss (-1R)

Bot checks for new outcomes every hour and updates memory automatically.

### Configuration Options

Edit `bot/config.py` to customize:

**Symbol Settings:**
```python
MAX_SYMBOLS_SUBSCRIBED = 40  # Reduce for low-end VPS
FIXED_SYMBOLS = [...]  # Add/remove symbols
```

**Risk Settings:**
```python
RISK_PER_TRADE = 0.01  # 1% risk per trade
MIN_RR_RATIO = 2.5  # Minimum risk/reward
MAX_SIGNALS_PER_DAY = 3  # Daily limit
```

**Memory Settings:**
```python
MEMORY_LOW_WR_THRESHOLD = 0.55  # 55% winrate threshold
MEMORY_CONSECUTIVE_LOSS_LIMIT = 3  # Pause after 3 losses
```

### Production Deployment

**Using Systemd:**

```bash
# 1. Edit service file
sudo nano /etc/systemd/system/trading-bot.service

# Update these lines:
# WorkingDirectory=/home/YOUR_USER/bot-telegram
# User=YOUR_USER
# EnvironmentFile=/home/YOUR_USER/bot-telegram/.env

# 2. Enable and start
sudo systemctl enable trading-bot
sudo systemctl start trading-bot

# 3. Check status
sudo systemctl status trading-bot

# 4. View logs
sudo journalctl -u trading-bot -f
```

### Common Issues

**Issue: "No module named 'aiohttp'"**
```bash
pip install -r requirements.txt
```

**Issue: "Telegram credentials not configured"**
- Check `.env` file exists and has correct values
- Restart bot after updating `.env`

**Issue: "WebSocket connection failed"**
- Check internet connectivity
- Verify Binance Futures API is accessible
- Check firewall settings

**Issue: "No signals generated"**
- Bot needs sufficient data (50+ candles per timeframe)
- Wait 10-15 minutes for data warmup
- Check if market is in SIDEWAY regime (bot skips these)
- Review scoring thresholds in config

**Issue: "Trading paused by memory engine"**
- Check memory state: Bot pauses after 3 consecutive losses
- Wait for cooldown period (12 hours)
- Or reset memory: `rm data/memory.db` and restart

### Understanding Signals

**Signal Example:**
```
🟢🟢 MUA BTCUSDT

📍 Entry: 45000.00
🛑 SL: 44325.00 (-1.50%)
🎯 TP1: 45675.00 (+1.50%)
🎯 TP2: 46350.00 (+3.00%)
🎯 TP3: 47025.00 (+4.50%)

📊 RR: 1:3.0 | WR: 60% | EV: 80%
```

**What it means:**
- 🟢 MUA = BUY, 🔴 BÁN = SELL
- Entry at market or limit order at 45000
- Stop loss at 44325 (-1.5%)
- Take 50% profit at TP1 and move SL to breakeven
- Let remaining 50% run to TP2/TP3
- Risk/Reward ratio is 1:3.0

### Performance Tuning

**Low-End VPS (1GB RAM):**
```python
MAX_SYMBOLS_SUBSCRIBED = 20
CONCURRENT_SYMBOL_SCANS = 3
```

**High-End VPS (4GB+ RAM):**
```python
MAX_SYMBOLS_SUBSCRIBED = 60
CONCURRENT_SYMBOL_SCANS = 10
MAX_SIGNALS_PER_DAY = 5
```

**Conservative Trading:**
```python
CONTINUATION_MIN_SCORE = 85  # Higher threshold
REVERSAL_MIN_SCORE = 90
MIN_RR_RATIO = 3.0  # Better RR required
```

**Aggressive Trading:**
```python
CONTINUATION_MIN_SCORE = 75  # Lower threshold
MAX_SIGNALS_PER_DAY = 5
CANDLE_COOLDOWN = 2  # Shorter cooldown
```

### Safety Features

✅ **Auto-pause after losses:** Prevents drawdown spirals  
✅ **Symbol cooldowns:** Avoids overtrading bad symbols  
✅ **Score adjustments:** Tightens criteria when performance drops  
✅ **Model disabling:** Temporarily disables underperforming setups  
✅ **All temporary:** Auto-recovery after cooldown periods  

### Getting Help

- Read the full README.md for detailed documentation
- Check IMPLEMENTATION.md for technical details
- Review logs in `data/bot.log` for errors
- Open an issue on GitHub for bugs

### Best Practices

1. **Start Small:** Test with low risk first
2. **Monitor Daily:** Check logs and performance
3. **Update Outcomes:** Manually track trade results
4. **Review Memory:** Check adjustments weekly
5. **Backup Data:** Keep trades.db and memory.db backed up
6. **Stay Updated:** Pull latest changes regularly

### Resources

- Binance Futures API: https://binance-docs.github.io/apidocs/futures/en/
- Telegram Bot API: https://core.telegram.org/bots/api
- ICT Concepts: Search "Inner Circle Trader" on YouTube
- SMC Concepts: Search "Smart Money Concepts" for education

---

**Happy Trading! 🚀**

Remember: This bot is for educational purposes. Always test thoroughly before using real funds. Past performance does not guarantee future results.
