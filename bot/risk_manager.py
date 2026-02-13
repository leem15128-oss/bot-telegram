"""Risk manager for position sizing and risk control."""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from .config import config

logger = logging.getLogger(__name__)


class RiskManager:
    """Manages risk parameters and position sizing."""
    
    def __init__(self):
        # Runtime parameters (can be modified by memory engine)
        self.risk_per_trade = config.RISK_PER_TRADE
        self.max_signals_per_day = config.MAX_SIGNALS_PER_DAY
        self.score_threshold = config.SCORE_THRESHOLD
        
        # Model enable flags
        self.reversal_model_enabled = True
        self.continuation_model_enabled = True
        
        # Daily signal counter
        self._signals_today = 0
        self._last_reset_date = datetime.utcnow().date()
    
    def update_risk_per_trade(self, new_risk: float):
        """Update risk per trade parameter."""
        old_risk = self.risk_per_trade
        self.risk_per_trade = max(0.1, min(new_risk, 5.0))  # Clamp between 0.1% and 5%
        logger.info(f"Risk per trade updated: {old_risk}% -> {self.risk_per_trade}%")
    
    def update_max_signals_per_day(self, new_max: int):
        """Update max signals per day."""
        old_max = self.max_signals_per_day
        self.max_signals_per_day = max(1, min(new_max, 20))  # Clamp between 1 and 20
        logger.info(f"Max signals per day updated: {old_max} -> {self.max_signals_per_day}")
    
    def update_score_threshold(self, new_threshold: int):
        """Update score threshold."""
        old_threshold = self.score_threshold
        self.score_threshold = max(50, min(new_threshold, 95))  # Clamp between 50 and 95
        logger.info(f"Score threshold updated: {old_threshold} -> {self.score_threshold}")
    
    def set_model_enabled(self, model_type: str, enabled: bool):
        """Enable or disable a model type."""
        if model_type == 'reversal':
            self.reversal_model_enabled = enabled
            logger.info(f"Reversal model {'enabled' if enabled else 'disabled'}")
        elif model_type == 'continuation':
            self.continuation_model_enabled = enabled
            logger.info(f"Continuation model {'enabled' if enabled else 'disabled'}")
    
    def is_model_enabled(self, model_type: str) -> bool:
        """Check if a model type is enabled."""
        if model_type == 'reversal':
            return self.reversal_model_enabled
        elif model_type == 'continuation':
            return self.continuation_model_enabled
        return True
    
    def can_send_signal(self) -> bool:
        """Check if we can send more signals today."""
        self._reset_daily_counter_if_needed()
        return self._signals_today < self.max_signals_per_day
    
    def increment_signal_counter(self):
        """Increment the daily signal counter."""
        self._reset_daily_counter_if_needed()
        self._signals_today += 1
        logger.info(f"Daily signals: {self._signals_today}/{self.max_signals_per_day}")
    
    def _reset_daily_counter_if_needed(self):
        """Reset daily counter if it's a new day."""
        today = datetime.utcnow().date()
        if today != self._last_reset_date:
            self._signals_today = 0
            self._last_reset_date = today
            logger.info("Daily signal counter reset")
    
    def calculate_position_size(self, entry_price: float, stop_loss: float, 
                               account_balance: float = 1000.0) -> Dict[str, float]:
        """
        Calculate position size based on risk parameters.
        
        Returns:
            Dict with 'quantity' and 'risk_amount'
        """
        # Calculate risk amount in quote currency (USDT)
        risk_amount = account_balance * (self.risk_per_trade / 100.0)
        
        # Calculate price distance to stop loss
        price_distance = abs(entry_price - stop_loss)
        
        if price_distance == 0:
            logger.warning("Stop loss equals entry price, using minimum position")
            return {'quantity': 0.001, 'risk_amount': risk_amount}
        
        # Calculate position size in base currency
        # risk_amount = quantity * price_distance
        quantity = risk_amount / price_distance
        
        # Round to reasonable precision
        quantity = round(quantity, 3)
        
        return {
            'quantity': quantity,
            'risk_amount': risk_amount
        }
    
    def validate_signal_score(self, score: float, symbol: str = None, 
                             additional_threshold: int = 0) -> bool:
        """
        Validate if a signal score meets the threshold.
        
        Args:
            score: Signal score
            symbol: Symbol name (for symbol-specific adjustments)
            additional_threshold: Additional threshold to add (from memory engine)
        
        Returns:
            True if score is sufficient
        """
        effective_threshold = self.score_threshold + additional_threshold
        return score >= effective_threshold
    
    def get_status(self) -> Dict[str, Any]:
        """Get current risk manager status."""
        self._reset_daily_counter_if_needed()
        return {
            'risk_per_trade': self.risk_per_trade,
            'max_signals_per_day': self.max_signals_per_day,
            'score_threshold': self.score_threshold,
            'signals_today': self._signals_today,
            'reversal_model_enabled': self.reversal_model_enabled,
            'continuation_model_enabled': self.continuation_model_enabled
        }


# Global risk manager
risk_manager = RiskManager()
