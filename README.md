# Telegram Trading Signal Bot

A sophisticated multi-timeframe technical analysis bot for generating quality trading signals on Binance markets. The bot analyzes 30m, 1h, and 4h timeframes to produce well-scored continuation and reversal signals without spamming.

## Features

### 🎯 Core Functionality
- **Multi-timeframe Analysis**: Uses 30m for entry timing, 1h for setup context, and 4h for regime/trend
- **Quality Signal Scoring**: Multi-component scoring system (trend, structure, momentum, patterns, trendlines, R:R)
- **Intrabar Analysis**: Runs on every candle update but computes structure from closed candles only
- **Smart Anti-Spam**: Per-symbol cooldowns, global cooldowns, and same-candle deduplication

### 📊 Technical Analysis Components
1. **Trend Alignment** (25 pts): Multi-timeframe trend confirmation
2. **Structure Analysis** (20 pts): Support/resistance, breakout quality, volume confirmation
3. **Momentum** (15 pts): Price action strength and direction
4. **Candle Patterns** (15 pts): 20+ patterns including:
   - **Reversal**: Engulfing, Hammer, Shooting Star, Pin Bars, Morning/Evening Star, Harami, Tweezers
   - **Continuation**: Three White Soldiers, Three Black Crows, Momentum Candles
   - **Indecision**: Doji (Standard, Long-Legged, Dragonfly, Gravestone)
   - **Special**: Inside Bar, Fakeout Detection
5. **Trendline Detection** (15 pts): Lightweight pivot-based trendline analysis
6. **Risk/Reward** (10 pts): Automatic stop loss and take profit calculation

### 🔧 Configuration
- **Adjustable Thresholds**: Continuation (65) and Reversal (70) minimum scores
- **Unlimited Mode**: No daily signal cap when `MAX_SIGNALS_PER_DAY <= 0`
- **Cooldown Controls**:
  - Per-symbol/direction/setup cooldown (default: 30 minutes)
  - Global cooldown between any signals (default: 60 seconds)
  - Max active signals per symbol (default: 3)

## Installation

### Prerequisites
- Python 3.8 or higher
- Binance account (for market data, no trading required)
- Telegram bot token and chat ID

### Setup

1. **Clone the repository**:
```bash
git clone https://github.com/leem15128-oss/bot-telegram.git
cd bot-telegram
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure environment variables**:
Create a `.env` file in the project root:
```env
# Binance API (optional, for potential future features)
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here

# Telegram Bot Configuration (required)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Optional Settings
LOG_LEVEL=INFO
DATABASE_PATH=bot_data.db
MESSAGE_TEMPLATE=default  # Options: "default" or "vip" (Vietnamese VIP format)
RR_MIN=1.2  # Minimum Risk:Reward ratio for signals (default: 1.2)
SIGNAL_TIMEFRAMES=30m,1h,4h  # Timeframes to display in trend confirmation (comma-separated)

# Notification Control
SEND_STARTUP_MESSAGE=true  # Send notification when bot starts (true/false)
SEND_STATS_ON_STARTUP=false  # Send statistics on startup (true/false) 
SEND_STATS_ON_SHUTDOWN=true  # Send statistics on shutdown (true/false)
STARTUP_MESSAGE_COOLDOWN_MINUTES=5  # Cooldown to prevent spam if bot restarts frequently
```

4. **Get Telegram credentials**:
   - Create a bot with [@BotFather](https://t.me/botfather) to get the token
   - Get your chat ID from [@userinfobot](https://t.me/userinfobot)

## Usage

### Run the bot:
```bash
python -m bot.main
```

Or using python3:
```bash
python3 -m bot.main
```

### The bot will:
1. Load historical candle data for all symbols and timeframes
2. Connect to Binance WebSocket streams
3. Analyze markets on every candle update
4. Send high-quality signals to your Telegram

### Stop the bot:
Press `Ctrl+C` for graceful shutdown

## Configuration

### Notification Controls

The bot provides fine-grained control over Telegram notifications to prevent spam:

```env
# Control startup notifications
SEND_STARTUP_MESSAGE=true         # Enable/disable bot startup notification
SEND_STATS_ON_STARTUP=false       # Send statistics when bot starts (default: off)
SEND_STATS_ON_SHUTDOWN=true       # Send statistics when bot stops (default: on)
STARTUP_MESSAGE_COOLDOWN_MINUTES=5  # Prevent duplicate startup messages if bot restarts quickly
```

**Default behavior:**
- ✅ Single startup message when bot starts (if enabled)
- ❌ No statistics message on startup (prevents duplicate notifications)
- ✅ Statistics message when bot shuts down
- 🛡️ 5-minute cooldown prevents spam if bot restarts multiple times

**To disable all startup notifications:**
```env
SEND_STARTUP_MESSAGE=false
SEND_STATS_ON_STARTUP=false
```

### Signal Thresholds
```python
CONTINUATION_MIN_SCORE = 65  # Lower = more signals
REVERSAL_MIN_SCORE = 70      # Lower = more signals
```

### Risk/Reward Filtering
```env
RR_MIN=1.2  # Minimum Risk:Reward ratio for signals (default: 1.2)
```
Only signals with Risk:Reward ratio >= `RR_MIN` will be sent. This ensures signal quality by filtering out setups with unfavorable risk/reward profiles.

### Message Template Configuration
```env
MESSAGE_TEMPLATE=vip  # Options: "default" or "vip"
SIGNAL_TIMEFRAMES=30m,1h,4h  # Timeframes to display in VIP trend confirmation (comma-separated)
```
- `MESSAGE_TEMPLATE=vip`: Use Vietnamese VIP format with enhanced icons and structure
- `MESSAGE_TEMPLATE=default`: Use standard English format
- `SIGNAL_TIMEFRAMES`: Controls which timeframes are displayed in the VIP template's trend confirmation section (default: 30m,1h,4h)

### Daily Limits
```python
MAX_SIGNALS_PER_DAY = 0  # 0 or negative = unlimited
```

### Anti-Spam Controls
```python
SIGNAL_COOLDOWN_SECONDS = 1800      # 30 min between same signals
GLOBAL_SIGNAL_COOLDOWN_SECONDS = 60  # 1 min between any signals
MAX_ACTIVE_SIGNALS_PER_SYMBOL = 3    # Max concurrent signals per symbol
```

### Symbols to Monitor
```python
SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "SOLUSDT",
    "ADAUSDT",
]
```

### Timeframes
```python
TIMEFRAMES = ["30m", "1h", "4h"]
PRIMARY_TIMEFRAME = "30m"    # Entry timing
SECONDARY_TIMEFRAME = "1h"   # Setup context
REGIME_TIMEFRAME = "4h"      # Main trend
```

## Signal Format

The bot supports two message templates configured via `MESSAGE_TEMPLATE` environment variable:

### Default Template (MESSAGE_TEMPLATE=default)

Signals sent to Telegram include:
- **Symbol & Direction**: e.g., BTCUSDT - LONG
- **Setup Type**: Continuation or Reversal
- **Total Score**: Out of 100
- **Entry, Stop Loss, Take Profit**: With percentages
- **Risk:Reward Ratio**: e.g., 1:2.5
- **Multi-timeframe Trends**: 30m, 1h, 4h
- **Component Scores**: Breakdown of scoring

Example:
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

⚠️ Alert only - not financial advice
```

### VIP Template (MESSAGE_TEMPLATE=vip)

Vietnamese VIP format with professional styling, enhanced icons, and detailed analysis:
- **Header**: Symbol + Direction + Timeframe (e.g., 🟢 BTCUSDT - BUY/LONG 📈 [30M])
- **Setup**: Vietnamese setup description with 📌 icon
- **Entry Section** with professional icons:
  - 💰 **Vào lệnh** (Entry): Entry price
  - 🛑 **SL** (Stop Loss): Stop loss price
  - 🎯 **TP1/TP2/TP3**: Three take profit targets based on support/resistance levels
  - ⚖️ **RR**: Risk:Reward ratio
- **📊 Xác nhận xu hướng** (Trend Confirmation):
  - Displays trends for configured timeframes (default: 30m, 1h, 4h)
  - Each timeframe shows direction with arrows: ⬆️ Tăng, ⬇️ Giảm, ➡️ Sideway
  - Configurable via `SIGNAL_TIMEFRAMES` environment variable
- **🔍 Lý do vào kèo** (Entry Reasons) with ✅ checkmarks:
  - Multi-timeframe trend alignment
  - **Breakout/Breakdown detection** with volume confirmation
  - **False breakout (Fakeout) detection** for reversal setups
  - 20+ candlestick patterns (all Vietnamese labels)
  - Momentum and trendline analysis
  - Volume confirmation
- **📋 Quản lý lệnh / Trailing** (Trade Management):
  - Detailed trailing stop guidance in Vietnamese
  - Profit-taking strategy (1/3 at each TP level)
  - Risk management tips
- **Footer**: "💡 Nguồn: Posiya Tú / 💰 Tồn tại để kiếm tiền"

Example:
```
🟢 BTCUSDT - BUY/LONG 📈 [30M]

📌 Setup: Nến Nhấn Chìm Tăng

💰 Vào lệnh: 45250.0000
🛑 SL: 44800.0000
🎯 TP1: 45800.0000
🎯 TP2: 46400.0000
🎯 TP3: 47000.0000
⚖️ RR: 1:3.89

📊 Xác nhận xu hướng:
  • 30M: ⬆️ Tăng
  • 1H: ⬆️ Tăng
  • 4H: ⬆️ Tăng

🔍 Lý do vào kèo:
  ✅ Xu hướng 4h, 1h, 30m đồng thuận
  ✅ Phá vỡ kháng cự mạnh với khối lượng cao (Breakout)
  ✅ Nến nhấn chìm tăng
  ✅ Momentum tăng mạnh
  ✅ Khối lượng tăng mạnh

📋 Quản lý lệnh / Trailing:
  • Dời SL lên BOS gần nhất khi chạm TP1, tiếp tục theo SR/BOS tiếp theo
  • Chốt 1/3 tại TP1, 1/3 tại TP2, để TP3 chạy
  • Không revenge trade nếu hit SL

━━━━━━━━━━━━━━━━━━━
💡 Nguồn: Posiya Tú
💰 Tồn tại để kiếm tiền
```

**TP Target Calculation:**
- The bot finds up to 3 support/resistance levels based on swing points
- For LONG: Uses resistance levels above entry as TP1/TP2/TP3
- For SHORT: Uses support levels below entry as TP1/TP2/TP3
- If fewer than 3 SR levels are found, falls back to RR-based targets (1R, 2R, 3R)

## Supported Candlestick Patterns

The bot includes 20+ ATR-normalized candlestick patterns for signal confirmation with **enhanced breakout/breakdown and false breakout (fakeout) detection**:

### Price Action Detection

**Breakout Detection** (detect_breakout):
- Confirms bullish breakout above resistance levels
- Evaluates breakout strength based on:
  - Distance from resistance (in ATR multiples)
  - Volume confirmation (1.2x to 2.0x+ average volume)
- Minimum 30 points required for valid breakout
- Vietnamese label: "Phá vỡ kháng cự mạnh với khối lượng cao (Breakout)"

**Breakdown Detection** (detect_breakdown):
- Confirms bearish breakdown below support levels
- Evaluates breakdown strength based on:
  - Distance from support (in ATR multiples)
  - Volume confirmation (1.2x to 2.0x+ average volume)
- Minimum 30 points required for valid breakdown
- Vietnamese label: "Phá vỡ hỗ trợ mạnh với khối lượng cao (Breakdown)"

**False Breakout Detection** (detect_false_breakout):
- Detects fakeout patterns where price briefly breaks a level but reverses
- Bullish fakeout: Price breaks below support, then closes back above
- Bearish fakeout: Price breaks above resistance, then closes back below
- Requires significant wick size (>0.3 ATR)
- Vietnamese labels:
  - "Fakeout bẫy giảm" (bullish fakeout/failed breakdown)
  - "Fakeout bẫy tăng" (bearish fakeout/failed breakout)

### Reversal Patterns (Bullish)
- **Bullish Engulfing**: Large bullish candle engulfs previous bearish candle (30 pts)
- **Hammer**: Small body at top with long lower wick (25 pts)
- **Pin Bar Bullish**: Long lower wick rejection (20 pts)
- **Morning Star**: 3-candle reversal with gap down star (25 pts)
- **Bullish Harami**: Small bullish candle inside large bearish body (18 pts)
- **Tweezer Bottom**: Two candles with matching lows, second bullish (15 pts)
- **Dragonfly Doji**: Long lower shadow, minimal upper shadow (15 pts)

### Reversal Patterns (Bearish)
- **Bearish Engulfing**: Large bearish candle engulfs previous bullish candle (30 pts)
- **Shooting Star**: Small body at bottom with long upper wick (25 pts)
- **Pin Bar Bearish**: Long upper wick rejection (20 pts)
- **Evening Star**: 3-candle reversal with gap up star (25 pts)
- **Bearish Harami**: Small bearish candle inside large bullish body (18 pts)
- **Tweezer Top**: Two candles with matching highs, second bearish (15 pts)
- **Gravestone Doji**: Long upper shadow, minimal lower shadow (15 pts)

### Continuation Patterns
- **Three White Soldiers**: Three consecutive strong bullish candles (30 pts)
- **Three Black Crows**: Three consecutive strong bearish candles (30 pts)
- **Momentum Candle**: Large body relative to ATR (25 pts)

### Indecision Patterns
- **Long-Legged Doji**: Small body with very long shadows both ways (10 pts)
- **Standard Doji**: Very small body, shows indecision (5 pts)

### Special Patterns
- **Inside Bar**: Current candle range within previous candle (10 pts)
- **Fakeout**: Wick breaks level but closes back inside (30 pts)

All patterns use ATR normalization for volatility-independent detection and support intrabar confirmation.

## Architecture

### Components

1. **config.py**: Centralized configuration with sane defaults
2. **candle_patterns.py**: Candlestick pattern recognition
3. **trendline_detector.py**: Pivot-based trendline analysis
4. **scoring_engine.py**: Multi-component signal scoring
5. **signal_deduplicator.py**: Anti-spam and cooldown management
6. **risk_manager.py**: Daily limits and risk calculations
7. **data_manager.py**: Multi-timeframe candle storage
8. **strategy.py**: Signal generation logic
9. **trade_tracker.py**: SQLite-based signal tracking
10. **telegram_notifier.py**: Formatted Telegram alerts
11. **websocket_handler.py**: Binance WebSocket integration
12. **main.py**: Bot orchestration

### Data Flow

```
Binance WebSocket
       ↓
  Data Manager (stores candles per timeframe)
       ↓
  Strategy (analyzes on 30m updates)
       ↓
  Scoring Engine (multi-component scoring)
       ↓
  Signal Deduplicator (anti-spam checks)
       ↓
  Risk Manager (daily limit checks)
       ↓
  Trade Tracker (SQLite persistence)
       ↓
  Telegram Notifier (send alert)
```

## Signal Quality Controls

### Why Signals are Rejected

The bot logs detailed reasons when signals are rejected:

1. **Below Score Threshold**: Total score < minimum (65 for continuation, 70 for reversal)
2. **Cooldown Active**: Too soon after last signal for same symbol/direction/setup
3. **Daily Limit Reached**: Max signals per day exceeded (if enabled)
4. **Same-Window Duplicate**: Already sent signal in current 30m candle
5. **Poor Risk:Reward**: R:R ratio below RR_MIN (default: 1.2, configurable via environment variable)
6. **Insufficient Data**: Not enough candles for analysis

Check logs for detailed diagnostic information:
```
INFO - BTCUSDT long continuation REJECTED: score=62.5 < threshold=65
INFO - ETHUSDT short reversal REJECTED: signal_cooldown (850s remaining)
```

## Database

Signals are tracked in SQLite database (`bot_data.db`):
- **signals** table: All generated signals with entry/stop/target
- **component_scores** table: Detailed scoring breakdown

Query example:
```sql
SELECT symbol, direction, setup_type, score, timestamp 
FROM signals 
WHERE status = 'active' 
ORDER BY timestamp DESC;
```

## Monitoring

### View Bot Statistics
The bot sends periodic stats to Telegram with:
- Total/Active/Closed signals
- Win/Loss counts and win rate
- Average signal score
- Average PnL percentage

### Logs
- Console output: Real-time status
- `bot.log` file: Complete logging history

## Safety & Disclaimers

⚠️ **Important Notes**:
- This bot is **alert-only** and does not execute trades automatically
- Signals are for informational purposes only, not financial advice
- Past performance does not guarantee future results
- Always do your own research and risk management
- Cryptocurrency trading involves significant risk

## Troubleshooting

### Bot not sending signals?
1. Check logs for rejection reasons
2. Verify sufficient historical data loaded
3. Lower score thresholds in config if too strict
4. Check cooldown settings

### WebSocket disconnections?
- Normal reconnection attempts are automatic
- Check network connectivity
- Binance API may have rate limits

### Telegram not working?
- Verify `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`
- Test bot manually with `/start` command
- Check bot has permission to message you

## Development

### Run tests (if available):
```bash
pytest
```

### Add new symbols:
Edit `SYMBOLS` list in `bot/config.py`

### Adjust scoring weights:
Edit `SCORE_WEIGHTS` dict in `bot/config.py` (must sum to 100)

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Contact: [Your contact info]

## Acknowledgments

- Built for the crypto trading community
- Uses Binance WebSocket API
- Inspired by multi-timeframe analysis techniques

---

**Disclaimer**: This software is provided "as is" without warranty. Use at your own risk. The authors are not responsible for any trading losses.