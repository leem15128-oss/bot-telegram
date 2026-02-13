# Institutional Price Action Swing Bot v2

Advanced trading bot implementing ICT/SMC (Institutional/Smart Money Concepts) methodology for cryptocurrency futures trading.

> 📖 **[Quick Start Guide](QUICKSTART.md)** | **[Implementation Details](IMPLEMENTATION.md)**

## Features

### Core Trading Logic
- **Market Structure Analysis**: CHoCH (Change of Character), BOS (Break of Structure), swing points
- **Regime Classification**: Trending Continuation, Confirmed Reversal, Sideway detection
- **Liquidity Concepts**: Internal/External liquidity sweeps, liquidity pools
- **Premium/Discount Zones**: Price positioning relative to swing ranges
- **Order Blocks & Fair Value Gaps**: Entry zones based on institutional footprints
- **Displacement Detection**: Impulse move validation with volume confirmation
- **Multi-Timeframe Analysis**: 1D, 4H, 30M confluence

### Data & Infrastructure
- **WebSocket Sharding**: Multiple WS connections to handle 300+ symbols
- **Symbol Rotation**: Top 300 volume symbols with 30-minute rotation
- **Universe Refresh**: Automatic 6-hour refresh of symbol universe
- **Fixed Symbols**: Always-on monitoring for key assets (BTC, ETH, etc.)
- **Rate Limiting**: Intelligent REST API throttling with exponential backoff
- **TTL Caching**: Reduce API calls with time-based caching

### Risk Management
- **Dynamic Position Sizing**: 1% risk per trade (adjustable)
- **Multi-Target System**: TP1 (1R), TP2 (Internal Liquidity), TP3 (External Liquidity)
- **Breakeven Management**: Move SL to BE at TP1
- **Daily Limits**: Max 3 signals per day (memory-adjusted)
- **Symbol Limits**: 1 active trade per symbol
- **Cooldown Periods**: 4 candle cooldown after signals

### Adaptive Memory Engine (Rule-Based)
Lightweight, no ML, using rolling counters and simple rules:

**Global Performance Rules:**
- Winrate < 55% → Increase score threshold +5
- 3 consecutive losses → Pause trading 12 hours
- Drawdown > 5% → Reduce to 2 signals/day
- Drawdown > 8% → Reduce risk to 0.5%

**Symbol-Specific Rules:**
- 2 consecutive losses → 24h cooldown
- Winrate < 50% (last 10) → Require +5 higher score

**Model-Specific Rules:**
- Reversal winrate < 45% → Disable 48 hours
- Trending winrate > 65% → Prioritize continuation setups

### Scoring System

**Continuation Setup (Min 80):**
- Structure: 25%
- Pullback: 20%
- Premium/Discount: 15%
- Liquidity: 15%
- OB/FVG: 10%
- Displacement: 10%
- Volatility: 5%

**Reversal Setup (Min 85):**
- External Sweep: 25%
- 4H CHoCH: 25%
- Displacement: 15%
- SR Strength: 15%
- Pattern: 10%
- Volatility: 5%
- Premium/Discount: 5%

### Telegram Notifications
Beautiful Vietnamese-formatted signals including:
- Entry/SL/TP levels with percentages
- RR/WR/EV metrics
- Trailing guidance
- Entry reasons (checkmark list)
- Source attribution: "Nguồn: Posiya Tú"
- Quote: "Xu hướng là bạn cho đến khi xu hướng đảo chiều."

### Trade Tracking & Outcomes
- **SQLite Storage**: All signals and trades persisted
- **CSV Ingestion**: Automatic periodic outcome ingestion
- **Memory Updates**: Trade outcomes feed back into adaptive memory
- **Performance Analytics**: Track winrate, R-multiples, model performance

## Installation

### Prerequisites
- Python 3.9+
- Telegram Bot Token
- Telegram Chat ID

### Setup

1. Clone the repository:
```bash
git clone https://github.com/leem15128-oss/bot-telegram.git
cd bot-telegram
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
export LOG_LEVEL="INFO"  # Optional
```

4. Run the bot:
```bash
python -m bot.main
```

## Directory Structure

```
bot-telegram/
├── bot/
│   ├── main.py                 # Main orchestrator
│   ├── config.py               # Configuration
│   ├── utils.py                # Utility functions
│   ├── symbol_engine.py        # Symbol selection & rotation
│   ├── data_engine.py          # WebSocket data management
│   ├── structure_engine.py     # Market structure analysis
│   ├── regime_engine.py        # Regime classification
│   ├── liquidity_engine.py     # Liquidity detection
│   ├── premium_discount.py     # Premium/Discount zones
│   ├── orderblock_engine.py    # Order block detection
│   ├── fvg_engine.py          # Fair Value Gap detection
│   ├── displacement_engine.py  # Displacement validation
│   ├── volatility_engine.py    # Volatility metrics
│   ├── scoring_engine.py       # Setup scoring
│   ├── risk_manager.py         # Risk management
│   ├── memory_engine.py        # Adaptive memory
│   ├── trade_tracker.py        # Trade tracking & CSV ingestion
│   └── notifier.py            # Telegram notifications
├── data/
│   ├── trades.db              # SQLite database
│   ├── memory.db              # Memory state
│   ├── outcomes.csv           # Trade outcomes (user-provided)
│   └── bot.log               # Log file
├── requirements.txt
└── README.md
```

## Configuration

Key configuration parameters in `bot/config.py`:

### Symbol Settings
- `FIXED_SYMBOLS`: Always-monitored symbols
- `MAX_SYMBOLS_SUBSCRIBED`: Max concurrent subscriptions (default: 40)
- `TOP_VOLUME_COUNT`: Top volume symbols to track (default: 300)
- `SYMBOL_ROTATION_INTERVAL`: Rotation interval (default: 30 minutes)
- `UNIVERSE_REFRESH_INTERVAL`: Universe refresh (default: 6 hours)

### Trading Settings
- `RISK_PER_TRADE`: Risk per trade (default: 1%)
- `MIN_RR_RATIO`: Minimum risk/reward (default: 2.5)
- `MAX_SIGNALS_PER_DAY`: Daily signal limit (default: 3)
- `CANDLE_COOLDOWN`: Cooldown candles (default: 4)

### Memory Settings
- `MEMORY_ROLLING_WINDOW`: Rolling window size (default: 20)
- `MEMORY_LOW_WR_THRESHOLD`: Low winrate threshold (default: 55%)
- `MEMORY_CONSECUTIVE_LOSS_LIMIT`: Pause trigger (default: 3)

## CSV Outcome Format

Create `data/outcomes.csv` with the following format:

```csv
date_utc,symbol,model_type,outcome
2024-01-15,BTCUSDT,continuation,TP1
2024-01-15,ETHUSDT,continuation,TP2
2024-01-16,BNBUSDT,reversal,SL
```

**Outcome values:**
- `TP1`: Hit Take Profit 1 (+1R)
- `TP2`: Hit Take Profit 2 (+2R)
- `TP3`: Hit Take Profit 3 (+3R)
- `SL`: Hit Stop Loss (-1R)

The bot automatically ingests new outcomes every hour and updates the adaptive memory.

## Systemd Service

Example service file (`/etc/systemd/system/trading-bot.service`):

```ini
[Unit]
Description=Institutional Price Action Swing Bot v2
After=network.target

[Service]
Type=simple
User=trader
WorkingDirectory=/home/trader/bot-telegram
Environment="TELEGRAM_BOT_TOKEN=your_token"
Environment="TELEGRAM_CHAT_ID=your_chat_id"
ExecStart=/usr/bin/python3 -m bot.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable trading-bot
sudo systemctl start trading-bot
sudo systemctl status trading-bot
```

## Monitoring

View logs:
```bash
# Real-time log
tail -f data/bot.log

# Systemd journal
sudo journalctl -u trading-bot -f
```

Check database:
```bash
sqlite3 data/trades.db "SELECT * FROM trades ORDER BY timestamp DESC LIMIT 10;"
```

## Safety Features

- **No Permanent Disabling**: All cooldowns and pauses are temporary
- **Auto-Recovery**: Automatic restoration after cooldown periods
- **Conservative Defaults**: Safe default parameters
- **Exception Handling**: Comprehensive error handling and logging
- **Resource Limits**: Semaphores and rate limiting to prevent overload

## Performance Tuning

For VPS with limited resources:
- Reduce `MAX_SYMBOLS_SUBSCRIBED` (e.g., 20-30)
- Increase `SYMBOL_ROTATION_INTERVAL` for less frequent changes
- Reduce `CONCURRENT_SYMBOL_SCANS` (e.g., 3)

For high-volume trading:
- Increase `MAX_SIGNALS_PER_DAY`
- Adjust `CANDLE_COOLDOWN` to lower values
- Fine-tune scoring thresholds

## License

MIT License

## Disclaimer

This bot is for educational and research purposes only. Trading cryptocurrency carries significant risk. Always test thoroughly in a demo environment before using real funds. Past performance does not guarantee future results.

## Support

For issues and questions, please open an issue on GitHub.
