# Adaptive Behavioral Memory Layer

## Overview

The Adaptive Behavioral Memory Layer is a lightweight, intelligent system that learns from trading performance and dynamically adjusts bot parameters to optimize performance and protect capital.

## Architecture

### Core Components

1. **Rolling Performance Tracking**
   - Uses `deque(maxlen=20)` for efficient memory management
   - No heavy pandas operations
   - Minimal memory footprint

2. **SQLite Persistence**
   - State saved to database on each update
   - Loads previous state on bot startup
   - Survives bot restarts

3. **Async-Safe Design**
   - Thread-safe with asyncio locks
   - Exception-safe error handling
   - Non-blocking operations

## Tracked Metrics

### Global Performance
```python
last_20_results: Deque[bool]          # Last 20 trades (True=win, False=loss)
consecutive_losses: int                # Current losing streak
current_drawdown_percent: float       # Peak-to-current drawdown
continuation_results: Deque[bool]     # Continuation model performance
reversal_results: Deque[bool]         # Reversal model performance
```

### Symbol-Specific Memory
```python
{
    'symbol_name': {
        'last_result': bool,           # Last trade result
        'consecutive_losses': int,      # Symbol losing streak
        'last_10': deque([...])        # Last 10 trades for this symbol
    }
}
```

### Cooldown Tracking
```python
symbol_cooldowns: Dict[str, datetime]    # Symbol -> cooldown_until
trading_paused_until: datetime           # Global pause
reversal_model_disabled_until: datetime  # Model-specific pause
```

## Adaptive Rules

### Rule 1: Global Winrate Adjustment
- **Condition**: `last_20_winrate < 55%`
- **Action**: Increase `score_threshold` by +5
- **Purpose**: Raise bar for signal quality when performance is poor

### Rule 2: Consecutive Loss Protection
- **Condition**: `consecutive_losses >= 3`
- **Action**: Pause trading for 12 hours
- **Purpose**: Stop trading during unfavorable market conditions

### Rule 3: Drawdown Management (Level 1)
- **Condition**: `drawdown > 5%`
- **Action**: Reduce `max_signals_per_day` to 2
- **Purpose**: Limit exposure during drawdown periods

### Rule 4: Drawdown Management (Level 2)
- **Condition**: `drawdown > 8%`
- **Action**: Reduce `risk_per_trade` to 0.5%
- **Purpose**: Protect capital during severe drawdowns

### Rule 5: Symbol Cooldown
- **Condition**: `consecutive_symbol_losses >= 2`
- **Action**: Apply 24-hour cooldown to that symbol
- **Purpose**: Avoid repeating mistakes on problematic symbols

### Rule 6: Symbol Score Adjustment
- **Condition**: `symbol_winrate_last_10 < 50%`
- **Action**: Require +5 higher score for that symbol
- **Purpose**: Be more selective with underperforming symbols

### Rule 7: Reversal Model Protection
- **Condition**: `reversal_winrate < 45%`
- **Action**: Disable reversal model for 48 hours
- **Purpose**: Stop using ineffective strategies

### Rule 8: Continuation Model Prioritization
- **Condition**: `continuation_winrate > 65%`
- **Action**: Log positive performance (no penalty)
- **Purpose**: Identify high-performing strategies

## Integration Points

### Pre-Signal Check
```python
# In main.py, before sending a signal:

# Check if trading is allowed
can_trade, reason = await adaptive_memory.can_trade(symbol, model_type)
if not can_trade:
    logger.info(f"Memory blocked signal: {reason}")
    return

# Get symbol-specific score adjustment
score_adjustment = adaptive_memory.get_symbol_score_adjustment(symbol)

# Validate score with adjustment
if not risk_manager.validate_signal_score(signal.score, symbol, score_adjustment):
    return
```

### Post-Trade Update
```python
# After a trade closes (manual or automated):

trade_data = {
    'symbol': 'BTCUSDT',
    'model_type': 'continuation',  # or 'reversal'
    'pnl': 50.0,                   # profit/loss in quote currency
    'pnl_percent': 5.0             # percentage return
}

await adaptive_memory.update_after_trade_closed(trade_data)
# Automatically:
# - Updates all metrics
# - Applies rules
# - Saves state to database
```

## API Reference

### `AdaptiveMemory.initialize()`
Loads memory state from database. Call once on bot startup.

### `AdaptiveMemory.can_trade(symbol: str, model_type: str) -> (bool, str)`
Checks if trading is allowed for a symbol/model combination.

**Returns:**
- `(True, "OK")` - Trading allowed
- `(False, reason)` - Trading blocked with reason

**Reasons:**
- "Trading paused until {datetime}" - Global pause active
- "{model_type} model disabled" - Model disabled by rule
- "Symbol on cooldown until {datetime}" - Symbol cooldown active

### `AdaptiveMemory.get_symbol_score_adjustment(symbol: str) -> int`
Returns additional score threshold for a specific symbol.

**Returns:**
- `0` - No adjustment needed
- `5` - Symbol underperforming, require higher score

### `AdaptiveMemory.update_after_trade_closed(trade_data: Dict)`
Updates memory after a trade closes. This is the main entry point for learning.

**Required trade_data fields:**
```python
{
    'symbol': str,         # Trading symbol
    'model_type': str,     # 'continuation' or 'reversal'
    'pnl': float,          # P&L in quote currency
    'pnl_percent': float   # P&L as percentage
}
```

### `AdaptiveMemory.get_status() -> Dict`
Returns current memory state for monitoring.

**Returns:**
```python
{
    'last_20_winrate': float,           # 0-100
    'consecutive_losses': int,
    'current_drawdown_percent': float,
    'continuation_winrate': float,      # 0-100
    'reversal_winrate': float,          # 0-100
    'trading_paused': bool,
    'active_symbol_cooldowns': int,
    'current_capital': float
}
```

## Configuration

### Hardcoded Constants

These values are intentionally hardcoded for safety:

```python
# Rolling windows
GLOBAL_WINDOW = 20          # Last N trades for global metrics
MODEL_WINDOW = 20           # Last N trades per model
SYMBOL_WINDOW = 10          # Last N trades per symbol

# Cooldown durations
GLOBAL_PAUSE_HOURS = 12     # After 3 consecutive losses
SYMBOL_COOLDOWN_HOURS = 24  # After 2 symbol losses
MODEL_DISABLE_HOURS = 48    # For underperforming models

# Thresholds
WINRATE_THRESHOLD = 55      # Global winrate minimum
SYMBOL_WINRATE_THRESHOLD = 50  # Symbol winrate minimum
REVERSAL_WINRATE_THRESHOLD = 45  # Reversal model minimum
CONTINUATION_WINRATE_BONUS = 65  # High performance threshold

# Score adjustments
POOR_PERFORMANCE_SCORE_INCREASE = 5
POOR_SYMBOL_SCORE_INCREASE = 5

# Drawdown levels
DRAWDOWN_LEVEL_1 = 5.0      # Reduce signals
DRAWDOWN_LEVEL_2 = 8.0      # Reduce risk

# Capital tracking
INITIAL_CAPITAL = 1000.0    # Starting capital (USD)
```

### Modifying Constants

To change these values, edit `bot/memory_engine.py`:

```python
# Example: Change global window to 30 trades
self.last_20_results: Deque[bool] = deque(maxlen=30)  # Changed from 20

# Example: Change pause duration to 24 hours
self.trading_paused_until = now + timedelta(hours=24)  # Changed from 12
```

**Warning:** Changing these values may affect system stability. Test thoroughly.

## Database Schema

### Table: `memory_state`

```sql
CREATE TABLE memory_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,           -- 'global' or 'symbols'
    key TEXT NOT NULL,                -- Metric name or symbol name
    value TEXT NOT NULL,              -- JSON-encoded value
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(category, key)
)
```

### Stored Values

**Global Category:**
- `last_20_results`: JSON array of booleans
- `consecutive_losses`: Integer string
- `current_drawdown`: Float string
- `continuation_results`: JSON array
- `reversal_results`: JSON array
- `current_capital`: Float string

**Symbols Category:**
- `{SYMBOL}`: JSON object with last_result, consecutive_losses, last_10

## Monitoring

### Telegram Status Updates

The bot sends Vietnamese-formatted status updates including:

```
📊 TRẠNG THÁI BOT

🎯 Tỷ lệ thắng (20 GD): 55.0%
📉 Drawdown: 3.50%
🔢 Thua liên tiếp: 1

📈 Xu hướng WR: 60.0%
🔄 Đảo chiều WR: 50.0%

💰 Vốn hiện tại: $1035.50
```

### Log Messages

The memory engine logs important events:

```
WARNING: Low winrate (52.5%), increasing score threshold
WARNING: 3+ consecutive losses, pausing trading until 2024-01-01 12:00:00
WARNING: Drawdown 6.5%, reducing max signals
WARNING: Symbol BTCUSDT on 24h cooldown (2+ consecutive losses)
WARNING: Reversal model disabled for 48h (winrate: 42.0%)
INFO: Reversal model re-enabled after cooldown
INFO: Trading resumed after pause
```

### Database Queries

**Check current memory state:**
```sql
SELECT * FROM memory_state WHERE category = 'global';
```

**Check symbol performance:**
```sql
SELECT key, value FROM memory_state WHERE category = 'symbols';
```

**Recent memory updates:**
```sql
SELECT * FROM memory_state ORDER BY updated_at DESC LIMIT 10;
```

## Safety Features

1. **Fail-Open Design**: If memory engine encounters errors, it allows trading to continue
2. **Auto-Restore**: All cooldowns expire automatically - no manual intervention needed
3. **Bounded Adjustments**: Risk and threshold changes are clamped to safe ranges
4. **Exception Handling**: All operations wrapped in try-except blocks
5. **Async-Safe**: Uses locks to prevent race conditions
6. **Persistence**: State survives bot crashes and restarts

## Performance Impact

- **Memory**: ~1-2 MB for typical usage (40 symbols, 20-trade window)
- **CPU**: Minimal (<0.1% on modern CPU)
- **Database**: Small queries, minimal I/O
- **Latency**: <1ms for checks, <10ms for updates

## Testing

### Unit Tests

```bash
python test_components.py
```

Tests cover:
- ✓ Memory initialization and loading
- ✓ can_trade() decision logic
- ✓ Score adjustment calculation
- ✓ Status reporting

### Integration Tests

To test the full flow:

1. Run bot with paper trading
2. Manually close some trades with losses
3. Observe rule activations in logs
4. Verify parameter changes
5. Wait for cooldowns to expire
6. Confirm auto-restore

## Troubleshooting

### Issue: Memory not loading on startup
**Solution:** Check that `await adaptive_memory.initialize()` is called in main.py

### Issue: Rules not applying
**Solution:** Ensure `update_after_trade_closed()` is called when trades close

### Issue: Database errors
**Solution:** Check write permissions on trading_bot.db file

### Issue: Unexpected trading blocks
**Solution:** Check logs for cooldown reasons, query `memory_state` table

### Issue: State reset after restart
**Solution:** Verify database persistence, check for file deletion

## Future Enhancements

Potential improvements (not currently implemented):

1. **Market Regime Detection**: Adapt to trending vs ranging markets
2. **Time-of-Day Analysis**: Learn optimal trading hours
3. **Correlation Tracking**: Avoid correlated losers
4. **Dynamic Window Sizing**: Adjust rolling window based on trade frequency
5. **Multi-Timeframe Memory**: Separate tracking per timeframe
6. **Risk Scaling**: Gradually increase risk after winning streaks

## References

- Main implementation: `bot/memory_engine.py`
- Integration: `bot/main.py` lines 80-100
- Risk manager: `bot/risk_manager.py`
- Database schema: `bot/database.py`

---

Last updated: 2024-01-01
