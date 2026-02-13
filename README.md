# Trading Signal Bot for Binance Futures

A production-ready Python 3.11 trading signal bot with an Adaptive Behavioral Memory Layer for Binance Futures trading.

## Features

### Core Functionality
- ✅ **Async Architecture**: Optimized for 2GB VPS deployment
- ✅ **Binance Futures WebSocket**: Real-time kline data (1D, 4H, 30M)
- ✅ **Memory Management**: Max 500 candles per timeframe per symbol
- ✅ **Concurrent Processing**: Semaphore-limited (5) concurrent symbol scans
- ✅ **SQLite Storage**: Persistent storage for signals, trades, and memory state
- ✅ **Telegram Notifications**: Clean Vietnamese format alerts

### Symbol Universe Management
- ✅ **Fixed Symbols**: Always-monitored priority symbols (BTC, ETH, BNB)
- ✅ **Volume-Based Selection**: Top 300 USDT perpetuals by 24h volume
- ✅ **Smart Rotation**: Rotate extra symbols every 30 minutes
- ✅ **Capacity Control**: Max 40 concurrent symbol subscriptions
- ✅ **Universe Refresh**: Update top volume list every 6 hours

### API & WebSocket Optimization
- ✅ **REST API Throttling**: Rate limiting with exponential backoff + jitter
- ✅ **Smart Caching**: TTL-based caching for exchangeInfo and ticker data
- ✅ **WebSocket Sharding**: Multiple connections to avoid stream limits
- ✅ **Auto-Reconnect**: Automatic WebSocket reconnection with backoff

### Adaptive Behavioral Memory Layer 🧠
The bot features an intelligent adaptive memory system that learns from trading performance and dynamically adjusts parameters:

#### Global Performance Tracking
- **Last 20 Winrate**: Rolling window of last 20 trades
- **Consecutive Losses**: Tracks losing streaks
- **Drawdown Management**: Monitors peak-to-current drawdown
- **Model Performance**: Separate tracking for continuation vs reversal models

#### Adaptive Rules
1. **Performance-Based Threshold**: If winrate < 55%, increase score threshold by +5
2. **Loss Protection**: If 3+ consecutive losses, pause trading for 12 hours
3. **Drawdown Control**: 
   - If drawdown > 5%, reduce max signals to 2/day
   - If drawdown > 8%, reduce risk per trade to 0.5%
4. **Symbol Memory**: 
   - Track per-symbol performance (last 10 trades)
   - If 2+ consecutive losses on a symbol, apply 24h cooldown
   - If symbol winrate < 50%, require +5 higher score
5. **Model Adaptation**:
   - If reversal model winrate < 45%, disable for 48 hours
   - Prioritize continuation setups if winrate > 65%

#### Safety Features
- ✅ **Lightweight**: Rolling deques (maxlen=20), no heavy pandas operations
- ✅ **Persistent State**: SQLite storage, loads on startup
- ✅ **Async Safe**: Thread-safe with asyncio locks
- ✅ **Exception Safe**: Graceful error handling
- ✅ **Auto-Restore**: Cooldowns expire automatically

## Installation

### Prerequisites
- Python 3.11+
- 2GB RAM VPS (minimum)
- Binance Futures account with API keys
- Telegram bot token

### Setup

1. **Clone the repository**:
```bash
git clone https://github.com/leem15128-oss/bot-telegram.git
cd bot-telegram
```

2. **Create virtual environment**:
```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure environment**:
```bash
cp .env.example .env
nano .env  # Edit with your credentials
```

Required `.env` variables:
```env
# Binance API
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
BINANCE_TESTNET=false

# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Trading Parameters (can be adjusted by memory engine)
RISK_PER_TRADE=1.0
MAX_SIGNALS_PER_DAY=5
SCORE_THRESHOLD=75

# Symbol Universe
MAX_SYMBOLS_SUBSCRIBED=40
TOP_VOLUME_FETCH_LIMIT=300
UNIVERSE_REFRESH_SECONDS=21600
ROTATION_SLOT_SECONDS=1800
FIXED_SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT

# WebSocket
WS_MAX_STREAMS_PER_CONN=50
```

5. **Run the bot**:
```bash
python -m bot.main
```

## Systemd Service (Production Deployment)

1. **Create bot user**:
```bash
sudo useradd -r -s /bin/false bot
```

2. **Setup directories**:
```bash
sudo mkdir -p /var/log/trading-bot
sudo chown bot:bot /var/log/trading-bot
```

3. **Copy service file**:
```bash
sudo cp trading-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
```

4. **Enable and start**:
```bash
sudo systemctl enable trading-bot
sudo systemctl start trading-bot
```

5. **Check status**:
```bash
sudo systemctl status trading-bot
sudo journalctl -u trading-bot -f
```

## Architecture

### Component Overview

```
bot/
├── config.py              # Configuration management
├── database.py            # SQLite database layer
├── binance_client.py      # Binance REST API client
├── websocket_manager.py   # WebSocket connection manager
├── symbol_universe.py     # Symbol selection & rotation
├── market_data.py         # Candle storage & management
├── scoring_engine.py      # Signal generation (no ML)
├── risk_manager.py        # Risk & position sizing
├── memory_engine.py       # 🧠 Adaptive Memory Layer
├── telegram_notifier.py   # Telegram notifications
└── main.py               # Bot orchestration
```

### Data Flow

1. **Initialization**:
   - Load adaptive memory state from SQLite
   - Fetch top volume symbols from Binance
   - Warmup historical candle data
   - Subscribe to WebSocket streams

2. **Real-time Processing**:
   - Receive closed candles via WebSocket
   - Update market data storage
   - Trigger signal analysis
   - Apply memory engine filters
   - Send signals via Telegram

3. **Symbol Rotation**:
   - Every 30 minutes: rotate extra symbols
   - Every 6 hours: refresh universe from Binance
   - Always keep fixed symbols active

4. **Adaptive Learning**:
   - After each trade closes: update memory
   - Apply performance-based rules
   - Adjust risk parameters dynamically
   - Save state to SQLite

### Signal Generation

The bot uses technical analysis (no ML) with two models:

1. **Continuation Model**: Trend-following using SMA and momentum
2. **Reversal Model**: Mean-reversion using Bollinger Bands

Each signal includes:
- Entry price
- Stop loss (ATR-based)
- Take profit (risk/reward optimized)
- Score (0-100)

### Memory Engine Integration

Before sending a signal, the memory engine checks:
```python
can_trade, reason = await adaptive_memory.can_trade(symbol, model_type)
if not can_trade:
    # Signal blocked
    return

# Get symbol-specific score adjustment
score_adjustment = adaptive_memory.get_symbol_score_adjustment(symbol)

# Validate with adjusted threshold
if not risk_manager.validate_signal_score(signal.score, symbol, score_adjustment):
    # Score too low
    return
```

After a trade closes:
```python
await adaptive_memory.update_after_trade_closed(trade_data)
# Memory engine automatically:
# - Updates rolling performance metrics
# - Applies adaptive rules
# - Adjusts risk parameters
# - Saves state to database
```

## Monitoring

### Logs
- `bot.log`: Application logs
- `/var/log/trading-bot/output.log`: Stdout (systemd)
- `/var/log/trading-bot/error.log`: Stderr (systemd)

### Telegram Notifications

The bot sends Vietnamese-formatted notifications for:
- 🔔 **New Signals**: Entry, SL, TP details
- ✅❌ **Trade Results**: P&L and performance
- 📊 **Status Updates**: Winrates, drawdown, parameters
- ⚠️ **Alerts**: System warnings and errors

### Database Queries

Check recent signals:
```sql
SELECT * FROM signals ORDER BY created_at DESC LIMIT 10;
```

Check memory state:
```sql
SELECT * FROM memory_state ORDER BY updated_at DESC;
```

Check trade performance:
```sql
SELECT 
    COUNT(*) as total_trades,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
    AVG(pnl_percent) as avg_pnl_pct
FROM trades 
WHERE status = 'closed';
```

## Configuration

### Adjustable Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| RISK_PER_TRADE | 1.0% | Risk per trade (can be reduced by memory) |
| MAX_SIGNALS_PER_DAY | 5 | Max daily signals (can be reduced by memory) |
| SCORE_THRESHOLD | 75 | Minimum signal score (can be increased by memory) |
| MAX_SYMBOLS_SUBSCRIBED | 40 | Max concurrent symbols |
| TOP_VOLUME_FETCH_LIMIT | 300 | Top symbols to consider |
| UNIVERSE_REFRESH_SECONDS | 21600 | 6 hours |
| ROTATION_SLOT_SECONDS | 1800 | 30 minutes |
| WS_MAX_STREAMS_PER_CONN | 50 | Streams per WebSocket |

### Memory Engine Tuning

The memory engine uses conservative defaults:
- Rolling window: 20 trades
- Symbol memory: 10 trades per symbol
- Cooldown periods: 12h (global), 24h (symbol), 48h (model)

These are hardcoded for safety but can be adjusted in `memory_engine.py` if needed.

## Performance

### Resource Usage
- **Memory**: ~500MB - 1GB RAM
- **CPU**: Low (<10% on 1 vCPU)
- **Network**: ~1-5 MB/hour
- **Disk**: Minimal (SQLite database)

### Scalability
- Handles 40+ concurrent symbols
- Multiple WebSocket connections (sharded)
- Efficient deque-based candle storage
- Async I/O for API calls

## Safety Features

1. **Rate Limiting**: Respects Binance API limits
2. **Error Recovery**: Auto-reconnect and retry logic
3. **Memory Management**: Fixed-size deques prevent memory leaks
4. **Adaptive Protection**: Dynamic risk reduction on drawdowns
5. **Cooldown System**: Prevents overtrading losing symbols/models
6. **Database Persistence**: Survives restarts

## Troubleshooting

### Bot not connecting
- Check API keys in `.env`
- Verify network connectivity
- Check Binance API status

### No signals generated
- Check score threshold (may be too high)
- Verify sufficient candle data
- Check if memory engine has paused trading
- Review logs for filter reasons

### WebSocket disconnects
- Normal behavior, auto-reconnects
- Check network stability
- Verify firewall allows WSS connections

### High memory usage
- Reduce MAX_SYMBOLS_SUBSCRIBED
- Check for memory leaks (should be stable)
- Restart service if needed

## Development

### Running Tests
```bash
python -m pytest tests/
```

### Code Structure
- Follow async/await patterns
- Use type hints
- Handle exceptions gracefully
- Log important events

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit pull request

## License

MIT License - see LICENSE file

## Disclaimer

This bot is for educational purposes. Trading cryptocurrencies involves risk. Use at your own discretion. The adaptive memory system adjusts parameters but does not guarantee profitability.

## Support

For issues and questions:
- GitHub Issues: https://github.com/leem15128-oss/bot-telegram/issues
- Documentation: See this README

---

**Version**: 1.0.0  
**Python**: 3.11+  
**Status**: Production Ready ✅
