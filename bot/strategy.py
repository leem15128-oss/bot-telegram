"""
Trading strategy module.
Implements multi-timeframe analysis and signal generation logic.
"""

import logging
from typing import Dict, Optional, Tuple
from bot.data_manager import DataManager
from bot.scoring_engine import ScoringEngine
from bot.signal_deduplicator import SignalDeduplicator
from bot.risk_manager import RiskManager
from bot.candle_patterns import calculate_atr
import bot.config as config

logger = logging.getLogger(__name__)


class TradingStrategy:
    """
    Multi-timeframe trading strategy.
    Uses 30m for entry timing, 1h for setup context, 4h for regime.
    """
    
    def __init__(self, data_manager: DataManager, 
                 deduplicator: SignalDeduplicator,
                 risk_manager: RiskManager):
        """
        Initialize strategy.
        
        Args:
            data_manager: Data manager instance
            deduplicator: Signal deduplicator instance
            risk_manager: Risk manager instance
        """
        self.data_manager = data_manager
        self.deduplicator = deduplicator
        self.risk_manager = risk_manager
        self.scoring_engine = ScoringEngine()
    
    def analyze_symbol(self, symbol: str, is_closed: bool = False) -> Optional[Dict]:
        """
        Analyze a symbol for potential trading signals.
        
        Args:
            symbol: Trading symbol to analyze
            is_closed: Whether the triggering candle just closed (not used for structure)
        
        Returns:
            Signal dict if found, None otherwise
        """
        # Get closed candles for each timeframe (structure from closed only)
        candles_30m = self.data_manager.get_closed_candles(symbol, '30m')
        candles_1h = self.data_manager.get_closed_candles(symbol, '1h')
        candles_4h = self.data_manager.get_closed_candles(symbol, '4h')
        
        # Need sufficient data
        if (len(candles_30m) < config.MIN_CLOSED_CANDLES_FOR_STRUCTURE or
            len(candles_1h) < 20 or len(candles_4h) < 20):
            logger.debug(f"{symbol}: Insufficient candles for analysis "
                        f"(30m:{len(candles_30m)}, 1h:{len(candles_1h)}, 4h:{len(candles_4h)})")
            return None
        
        # Get current price from forming candle or last closed
        current_price = self.data_manager.get_latest_price(symbol, '30m')
        if not current_price:
            logger.debug(f"{symbol}: No current price available")
            return None
        
        # Calculate trends on each timeframe
        trend_30m = self.data_manager.calculate_trend(symbol, '30m', lookback=20)
        trend_1h = self.data_manager.calculate_trend(symbol, '1h', lookback=20)
        trend_4h = self.data_manager.calculate_trend(symbol, '4h', lookback=20)
        
        logger.debug(f"{symbol}: Trends - 30m:{trend_30m}, 1h:{trend_1h}, 4h:{trend_4h}")
        
        # Try both long and short setups
        for direction in ['long', 'short']:
            signal = self._evaluate_setup(
                symbol, direction, current_price,
                trend_30m, trend_1h, trend_4h,
                candles_30m, candles_1h, candles_4h
            )
            
            if signal:
                return signal
        
        return None
    
    def _evaluate_setup(self, symbol: str, direction: str, current_price: float,
                       trend_30m: str, trend_1h: str, trend_4h: str,
                       candles_30m: list, candles_1h: list, candles_4h: list) -> Optional[Dict]:
        """
        Evaluate a specific setup (long or short).
        
        Returns:
            Signal dict if valid, None otherwise
        """
        # Calculate ATR for volatility-based levels
        atr = calculate_atr(candles_30m, config.ATR_PERIOD)
        
        # Find support/resistance
        support, resistance = self.data_manager.find_support_resistance(
            symbol, '30m', current_price, atr
        )
        
        # Calculate average volume
        recent_volumes = [c.volume for c in candles_30m[-20:]]
        avg_volume = sum(recent_volumes) / len(recent_volumes)
        
        # Get current volume (forming candle or last closed)
        forming = self.data_manager.get_forming_candle(symbol, '30m')
        current_volume = forming.volume if forming else candles_30m[-1].volume
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        # Calculate entry/stop/target
        if direction == 'long':
            entry = current_price
            stop_loss = support if support else entry * (1 - 0.02)  # 2% default
            take_profit = resistance if resistance else entry * (1 + 0.04)  # 4% default
        else:
            entry = current_price
            stop_loss = resistance if resistance else entry * (1 + 0.02)
            take_profit = support if support else entry * (1 - 0.04)
        
        # Validate risk/reward
        is_valid, rr_reason = self.risk_manager.validate_setup(entry, stop_loss, take_profit, min_rr=1.5)
        if not is_valid:
            logger.debug(f"{symbol} {direction}: {rr_reason}")
            return None
        
        # Calculate total score
        total_score, component_scores = self.scoring_engine.calculate_total_score(
            trend_30m=trend_30m,
            trend_1h=trend_1h,
            trend_4h=trend_4h,
            candles_30m=candles_30m,
            current_price=current_price,
            direction=direction,
            nearest_support=support,
            nearest_resistance=resistance,
            volume_ratio=volume_ratio,
            entry=entry,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        # Determine setup type
        expected_trend = 'up' if direction == 'long' else 'down'
        if trend_4h == expected_trend:
            setup_type = 'continuation'
            min_score = config.CONTINUATION_MIN_SCORE
        else:
            setup_type = 'reversal'
            min_score = config.REVERSAL_MIN_SCORE
        
        # Check if score meets threshold
        if total_score < min_score:
            if config.LOG_REJECTED_SIGNALS:
                logger.info(f"{symbol} {direction} {setup_type} REJECTED: "
                          f"score={total_score:.1f} < threshold={min_score} | "
                          f"components: {self._format_component_scores(component_scores)}")
            return None
        
        # Check daily limit
        can_send_daily, daily_reason = self.risk_manager.can_send_signal()
        if not can_send_daily:
            if config.LOG_REJECTED_SIGNALS:
                logger.warning(f"{symbol} {direction} {setup_type} REJECTED: {daily_reason}")
            return None
        
        # Check cooldown
        can_send_cooldown, cooldown_reason = self.deduplicator.can_send_signal(
            symbol, direction, setup_type
        )
        if not can_send_cooldown:
            if config.LOG_REJECTED_SIGNALS:
                logger.info(f"{symbol} {direction} {setup_type} REJECTED: {cooldown_reason}")
            return None
        
        # Check same-window duplicate
        window_start = self.data_manager.get_candle_window(symbol, '30m')
        if window_start:
            can_send_window, window_reason = self.deduplicator.can_send_signal_in_window(
                symbol, direction, window_start
            )
            if not can_send_window:
                if config.LOG_REJECTED_SIGNALS:
                    logger.info(f"{symbol} {direction} {setup_type} REJECTED: {window_reason}")
                return None
        
        # All checks passed - generate signal
        logger.info(f"✓ {symbol} {direction} {setup_type} SIGNAL GENERATED: "
                   f"score={total_score:.1f} | "
                   f"components: {self._format_component_scores(component_scores)}")
        
        signal = {
            'symbol': symbol,
            'direction': direction,
            'setup_type': setup_type,
            'entry': entry,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'score': total_score,
            'component_scores': component_scores,
            'trends': {
                '30m': trend_30m,
                '1h': trend_1h,
                '4h': trend_4h,
            },
            'atr': atr,
            'volume_ratio': volume_ratio,
        }
        
        return signal
    
    def _format_component_scores(self, component_scores: Dict) -> str:
        """Format component scores for logging."""
        parts = []
        for component, data in component_scores.items():
            weighted = data['weighted']
            parts.append(f"{component}={weighted:.1f}")
        return ', '.join(parts)
