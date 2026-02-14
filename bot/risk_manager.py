"""
Risk management module.
Handles daily signal limits and risk parameters.
"""

import logging
from datetime import datetime, date
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


class RiskManager:
    """
    Manages risk parameters and daily signal limits.
    Supports unlimited mode when max_signals_per_day <= 0.
    """
    
    def __init__(self, max_signals_per_day: int = 0):
        """
        Initialize risk manager.
        
        Args:
            max_signals_per_day: Maximum signals per day (0 or negative = unlimited)
        """
        self.max_signals_per_day = max_signals_per_day
        self.unlimited_mode = max_signals_per_day <= 0
        
        # Track signals sent today
        self._signals_today: Dict[date, int] = {}
        self._current_date = date.today()
        
        logger.info(f"RiskManager initialized: unlimited_mode={self.unlimited_mode}, "
                   f"max_signals_per_day={self.max_signals_per_day}")
    
    def can_send_signal(self) -> Tuple[bool, str]:
        """
        Check if a signal can be sent based on daily limits.
        
        Returns:
            Tuple of (can_send, reason)
        """
        # Unlimited mode always allows signals
        if self.unlimited_mode:
            return True, "unlimited_mode"
        
        # Check if date has changed
        today = date.today()
        if today != self._current_date:
            logger.info(f"New day detected: {today}, resetting daily count")
            self._current_date = today
            self._signals_today[today] = 0
        
        # Check daily limit
        signals_sent = self._signals_today.get(today, 0)
        if signals_sent >= self.max_signals_per_day:
            return False, f"daily_limit_reached ({signals_sent}/{self.max_signals_per_day})"
        
        return True, f"within_limit ({signals_sent}/{self.max_signals_per_day})"
    
    def record_signal(self):
        """Record that a signal was sent today."""
        today = date.today()
        
        # Update current date if needed
        if today != self._current_date:
            self._current_date = today
            self._signals_today[today] = 0
        
        # Increment count
        self._signals_today[today] = self._signals_today.get(today, 0) + 1
        
        if not self.unlimited_mode:
            logger.info(f"Signal recorded: {self._signals_today[today]}/{self.max_signals_per_day} today")
        else:
            logger.info(f"Signal recorded: {self._signals_today[today]} today (unlimited mode)")
    
    def get_signals_remaining_today(self) -> int:
        """
        Get number of signals remaining for today.
        
        Returns:
            Remaining signals (or -1 for unlimited)
        """
        if self.unlimited_mode:
            return -1
        
        today = date.today()
        signals_sent = self._signals_today.get(today, 0)
        return max(0, self.max_signals_per_day - signals_sent)
    
    def get_stats(self) -> dict:
        """Return statistics about risk management."""
        today = date.today()
        signals_today = self._signals_today.get(today, 0)
        
        return {
            "unlimited_mode": self.unlimited_mode,
            "max_signals_per_day": self.max_signals_per_day,
            "signals_today": signals_today,
            "signals_remaining": self.get_signals_remaining_today(),
            "current_date": today.isoformat(),
        }
    
    def calculate_position_size(self, account_balance: float, risk_pct: float, 
                               stop_loss_pct: float) -> float:
        """
        Calculate position size based on risk parameters.
        
        Args:
            account_balance: Total account balance
            risk_pct: Percentage of account to risk (e.g., 1.0 for 1%)
            stop_loss_pct: Stop loss percentage from entry
        
        Returns:
            Position size in quote currency
        """
        if stop_loss_pct <= 0:
            logger.warning("Invalid stop_loss_pct, cannot calculate position size")
            return 0
        
        risk_amount = account_balance * (risk_pct / 100)
        position_size = risk_amount / (stop_loss_pct / 100)
        
        return position_size
    
    def calculate_risk_reward(self, entry: float, stop_loss: float, 
                             take_profit: float) -> float:
        """
        Calculate risk/reward ratio.
        
        Args:
            entry: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
        
        Returns:
            Risk/reward ratio (e.g., 3.0 means 1:3 RR)
        """
        if entry <= 0 or stop_loss <= 0 or take_profit <= 0:
            return 0
        
        risk = abs(entry - stop_loss)
        reward = abs(take_profit - entry)
        
        if risk == 0:
            return 0
        
        return reward / risk
    
    def validate_setup(self, entry: float, stop_loss: float, take_profit: float,
                      min_rr: float = 1.5) -> Tuple[bool, str]:
        """
        Validate a trade setup meets minimum risk/reward requirements.
        
        Args:
            entry: Entry price
            stop_loss: Stop loss price  
            take_profit: Take profit price
            min_rr: Minimum acceptable risk/reward ratio
        
        Returns:
            Tuple of (is_valid, reason)
        """
        rr = self.calculate_risk_reward(entry, stop_loss, take_profit)
        
        if rr < min_rr:
            return False, f"poor_risk_reward (RR: {rr:.2f}, min: {min_rr})"
        
        return True, f"good_risk_reward (RR: {rr:.2f})"
