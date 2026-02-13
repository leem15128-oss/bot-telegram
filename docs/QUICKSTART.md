# Quick Start Guide

## Prerequisites Check

```bash
# Check Python version (must be 3.11+)
python3 --version

# Check system resources
free -h  # Should have at least 2GB RAM
df -h    # Should have at least 1GB free disk
```

## Installation (5 minutes)

### 1. Clone and Setup

```bash
# Clone repository
git clone https://github.com/leem15128-oss/bot-telegram.git
cd bot-telegram

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

**Minimum required settings:**
```env
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_secret
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 3. Test Run

```bash
# Run in foreground to test
python -m bot.main

# You should see:
# "Trading Bot initialized successfully"
# "Bot khởi động thành công!" (Telegram message)
```

Press `Ctrl+C` to stop.

## Production Deployment

### Option 1: Screen Session (Quick)

```bash
# Start in screen
screen -S trading-bot
source venv/bin/activate
python -m bot.main

# Detach: Ctrl+A, D
# Reattach: screen -r trading-bot
```

### Option 2: Systemd Service (Recommended)

```bash
# Create bot user
sudo useradd -r -s /bin/false bot

# Setup directories
sudo mkdir -p /var/log/trading-bot
sudo chown bot:bot /var/log/trading-bot

# Move bot to /home/bot
sudo mv /path/to/bot-telegram /home/bot/
sudo chown -R bot:bot /home/bot/bot-telegram

# Install service
sudo cp /home/bot/bot-telegram/trading-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable trading-bot
sudo systemctl start trading-bot

# Check status
sudo systemctl status trading-bot
sudo journalctl -u trading-bot -f
```

## Verification

### 1. Check Logs

```bash
# Application log
tail -f bot.log

# Look for:
# - "Database connected"
# - "Symbol universe initialized"
# - "Market data warmup complete"
# - "WebSocket connected"
```

### 2. Check Database

```bash
sqlite3 trading_bot.db "SELECT * FROM memory_state;"
sqlite3 trading_bot.db "SELECT COUNT(*) FROM signals;"
```

### 3. Telegram Notifications

You should receive:
- ✅ "Bot khởi động thành công!" on startup
- 🔔 Signal notifications when patterns detected
- 📊 Status updates periodically

## Monitoring

### Health Check

```bash
# Check process
ps aux | grep "bot.main"

# Check memory usage
ps aux --sort=-%mem | head -10

# Check logs for errors
grep ERROR bot.log
```

### Database Queries

```bash
sqlite3 trading_bot.db
```

```sql
-- Recent signals
SELECT * FROM signals ORDER BY created_at DESC LIMIT 5;

-- Trading performance
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
    ROUND(AVG(pnl_percent), 2) as avg_pnl
FROM trades WHERE status = 'closed';

-- Memory state
SELECT * FROM memory_state ORDER BY updated_at DESC;
```

## Common Issues

### Issue: Bot not starting

```bash
# Check Python version
python3 --version  # Must be 3.11+

# Check dependencies
pip install -r requirements.txt

# Check configuration
cat .env  # Verify API keys are set
```

### Issue: No signals generated

```bash
# Check logs
tail -100 bot.log | grep -i signal

# Possible reasons:
# - Score threshold too high (check config)
# - Memory engine paused trading (check logs)
# - Insufficient candle data (wait 5-10 minutes)
```

### Issue: WebSocket errors

```bash
# Check network
ping fstream.binance.com

# Check firewall
sudo ufw status

# Restart bot
sudo systemctl restart trading-bot
```

### Issue: Telegram not working

```bash
# Test bot token
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getMe"

# Test chat ID
curl "https://api.telegram.org/bot<YOUR_TOKEN>/sendMessage?chat_id=<YOUR_CHAT_ID>&text=test"
```

## Stopping the Bot

### Screen:
```bash
screen -r trading-bot
# Press Ctrl+C
```

### Systemd:
```bash
sudo systemctl stop trading-bot
```

## Updating

```bash
cd /home/bot/bot-telegram
git pull
sudo systemctl restart trading-bot
```

## Backup

```bash
# Backup database and configuration
tar -czf bot-backup-$(date +%Y%m%d).tar.gz \
    trading_bot.db \
    .env \
    bot.log

# Copy to safe location
scp bot-backup-*.tar.gz user@backup-server:/backups/
```

## Performance Tuning

### Reduce Memory Usage

Edit `.env`:
```env
MAX_SYMBOLS_SUBSCRIBED=20  # Reduce from 40
TOP_VOLUME_FETCH_LIMIT=150  # Reduce from 300
```

### Increase Signal Frequency

Edit `.env`:
```env
SCORE_THRESHOLD=70  # Lower from 75
MAX_SIGNALS_PER_DAY=10  # Increase from 5
```

### Conservative Mode

Edit `.env`:
```env
RISK_PER_TRADE=0.5  # Lower risk
MAX_SIGNALS_PER_DAY=3  # Fewer signals
SCORE_THRESHOLD=80  # Higher quality
```

## Next Steps

1. **Monitor for 24 hours**: Watch logs and Telegram
2. **Review performance**: Check memory engine status
3. **Adjust parameters**: Fine-tune based on results
4. **Setup alerts**: Configure additional monitoring
5. **Schedule backups**: Automate database backups

## Support

- Documentation: `README.md`
- Memory Engine: `docs/MEMORY_ENGINE.md`
- Issues: GitHub Issues
- Logs: `bot.log` and systemd journal

---

**Happy Trading! 🚀**
