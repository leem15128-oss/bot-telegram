# Vietnamese VIP Message Template Implementation Summary

## Overview
This implementation adds a configurable Vietnamese VIP-style message template for Telegram signals, with support for multiple take-profit targets based on support/resistance levels.

## What Was Changed

### 1. Configuration (`bot/config.py`)
- Added `MESSAGE_TEMPLATE` environment variable (default: "default", options: "default" or "vip")
- Updated `.env.example` with the new configuration option

### 2. Data Manager (`bot/data_manager.py`)
- Added `find_multiple_sr_levels()` method to find up to 3 support/resistance levels
- Used for calculating TP1/TP2/TP3 targets based on actual market structure

### 3. Strategy (`bot/strategy.py`)
- Added `_calculate_tp_targets()` method to compute TP1/TP2/TP3
- Calculation logic:
  - Primary: Uses SR levels found by `find_multiple_sr_levels()`
  - Fallback: RR-based targets (1R, 2R, 3R) when fewer SR levels available
- Updated signal dictionary to include `tp1`, `tp2`, `tp3` fields

### 4. Telegram Notifier (`bot/telegram_notifier.py`)
- Refactored `_format_signal_message()` to support multiple templates
- Added `_format_default_message()` for existing format (unchanged behavior)
- Added `_format_vip_message()` for Vietnamese VIP format with:
  - Vietnamese field labels (Vào lệnh, SL, TP1/TP2/TP3, RR)
  - "Lý do vào kèo" section with component-based reasons
  - Trailing stop guidance
  - Footer: "Nguồn: Posiya Tú" / "Tồn tại để kiếm tiền"
- Added helper methods:
  - `_get_vietnamese_setup_label()`: Maps patterns to Vietnamese setup names
  - `_build_vietnamese_reasons()`: Generates reason list from component scores
  - `_get_trailing_guidance()`: Returns Vietnamese trailing stop text

### 5. Documentation (`README.md`)
- Updated configuration section with MESSAGE_TEMPLATE option
- Added detailed Signal Format section showing both templates
- Documented TP target calculation logic

### 6. Tests
- `test_vip_template.py`: Unit tests for VIP template formatting
- `test_vip_integration.py`: Integration tests for SR-based TP calculation
- All existing tests (`test_bot.py`) still pass

## Vietnamese VIP Template Features

### Fields Included
1. **Header**: Symbol + BUY/LONG or SELL/SHORT
2. **Setup**: Vietnamese pattern/setup label
3. **Vào lệnh** (Entry): Entry price
4. **SL**: Stop loss
5. **TP1/TP2/TP3**: Three take profit levels
6. **RR**: Risk:Reward ratio
7. **Lý do vào kèo**: Bulleted reason list including:
   - Trend alignment across timeframes
   - Structure/BOS (breakout of structure)
   - Candlestick patterns
   - Momentum
   - Trendline support/resistance
   - Volume confirmation
8. **Trailing**: Vietnamese guidance for trailing stops
9. **Footer**: Credit line (2 lines)

### Vietnamese Labels Mapping
- Patterns: Nến Nhấn Chìm Tăng/Giảm, Nến Búa, Sao Băng, etc.
- Setup types: Tiếp Diễn Xu Hướng (Continuation), Đảo Chiều (Reversal)
- Structure: Phá vỡ kháng cự/hỗ trợ (BOS), Vùng hỗ trợ/kháng cự mạnh
- Momentum: Momentum tăng/giảm mạnh
- Trendline: Trendline hỗ trợ/kháng cự

## Usage

### Enable VIP Template
Set environment variable in `.env`:
```env
MESSAGE_TEMPLATE=vip
```

### Use Default Template
Set environment variable in `.env` (or omit for default):
```env
MESSAGE_TEMPLATE=default
```

## Testing

### Run VIP Template Tests
```bash
python test_vip_template.py
```

### Run Integration Tests
```bash
python test_vip_integration.py
```

### Run All Tests
```bash
python test_bot.py
```

## Sample Output Comparison

### VIP Template (MESSAGE_TEMPLATE=vip)
```
🟢 BTCUSDT - BUY/LONG
Setup: Nến Nhấn Chìm Tăng

Vào lệnh: 45250.0000
SL: 44800.0000
TP1: 45800.0000
TP2: 46400.0000
TP3: 47000.0000
RR: 1:3.89

Lý do vào kèo:
  • Xu hướng 4h, 1h, 30m đồng thuận
  • Phá vỡ kháng cự (BOS)
  • Nến nhấn chìm tăng
  • Mẫu hình búa
  • Momentum tăng mạnh
  • Trendline hỗ trợ
  • Khối lượng tăng mạnh

Trailing: Dời SL lên BOS gần nhất khi chạm TP1, tiếp tục theo SR/BOS tiếp theo

Nguồn: Posiya Tú
Tồn tại để kiếm tiền
```

### Default Template (MESSAGE_TEMPLATE=default)
```
🟢 BTCUSDT - LONG 📈

Setup: Continuation
Score: 72.5/100

📊 Entry: 45250.0000
🛑 Stop Loss: 44800.0000 (-0.99%)
🎯 Take Profit: 47000.0000 (+3.87%)
⚖️ Risk:Reward: 1:3.89

📈 Trends:
  • 30m: ⬆️ up
  • 1h: ⬆️ up
  • 4h: ⬆️ up

🔍 Component Scores:
  ✅ Trend Alignment: 22.5/25
  ✅ Structure: 15.0/25
  ✅ Momentum: 12.0/25
  ⚠️ Candle Patterns: 10.5/25
  ⚠️ Trendline: 9.8/25
  ✅ Risk Reward: 8.5/25

⚠️ Alert only - not financial advice
```

## Backward Compatibility

- When `MESSAGE_TEMPLATE` is not set or set to "default", the bot uses the original format
- All existing functionality remains unchanged
- No breaking changes to the API or signal structure
- Tests confirm both templates work correctly

## Key Design Decisions

1. **Minimal Changes**: Only modified necessary files; core logic unchanged
2. **SR-based TP with Fallback**: Prefers market structure but ensures 3 TPs always available
3. **Component-Based Reasons**: Extracts actual strategy components rather than hardcoding
4. **Template Switching**: Clean separation between templates via config
5. **Vietnamese Mapping**: Intelligent pattern/setup name mapping to Vietnamese

## Files Changed
- `.env.example` - Added MESSAGE_TEMPLATE configuration
- `bot/config.py` - Added MESSAGE_TEMPLATE config variable
- `bot/data_manager.py` - Added find_multiple_sr_levels() method
- `bot/strategy.py` - Added TP1/TP2/TP3 calculation and _calculate_tp_targets()
- `bot/telegram_notifier.py` - Added VIP template formatting methods
- `README.md` - Updated documentation with template examples
- `test_vip_template.py` - New unit tests for VIP template
- `test_vip_integration.py` - New integration tests

## Verification

✅ All existing tests pass (`test_bot.py`)
✅ VIP template tests pass (`test_vip_template.py`)
✅ Integration tests pass (`test_vip_integration.py`)
✅ Default template still works correctly
✅ Template switching works as expected
✅ No syntax errors or import issues
✅ Backward compatible - existing behavior unchanged
