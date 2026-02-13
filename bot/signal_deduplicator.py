"""
Signal deduplication and anti-spam module.
Prevents repeated alerts for the same symbol/direction/setup with cooldown management.
"""

import time
import logging
from typing import Dict, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SignalDeduplicator:
    """
    Manages signal cooldowns to prevent spam.
    Tracks signals by (symbol, direction, setup_type) and enforces cooldown periods.
    """
    
    def __init__(self, 
                 signal_cooldown_seconds: int = 1800,
                 global_cooldown_seconds: int = 60,
                 max_active_per_symbol: int = 3):
        """
        Initialize the deduplicator.
        
        Args:
            signal_cooldown_seconds: Cooldown between signals for same (symbol, direction, setup)
            global_cooldown_seconds: Minimum time between ANY signals
            max_active_per_symbol: Maximum unresolved signals per symbol
        """
        self.signal_cooldown_seconds = signal_cooldown_seconds
        self.global_cooldown_seconds = global_cooldown_seconds
        self.max_active_per_symbol = max_active_per_symbol
        
        # Track last signal time by (symbol, direction, setup_type)
        self._signal_times: Dict[Tuple[str, str, str], float] = {}
        
        # Track last global signal time
        self._last_global_signal_time: float = 0
        
        # Track active signals per symbol
        self._active_signals: Dict[str, int] = {}
        
        # Track signals within current 30m window (for same-candle dedup)
        self._current_window_signals: Dict[Tuple[str, int], set] = {}
    
    def can_send_signal(self, symbol: str, direction: str, setup_type: str, 
                       current_time: Optional[float] = None) -> Tuple[bool, str]:
        """
        Check if a signal can be sent based on cooldown rules.
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            direction: Signal direction ("long" or "short")
            setup_type: Type of setup ("continuation" or "reversal")
            current_time: Current timestamp (or use time.time())
        
        Returns:
            Tuple of (can_send, reason)
        """
        if current_time is None:
            current_time = time.time()
        
        # Check global cooldown
        time_since_last_global = current_time - self._last_global_signal_time
        if time_since_last_global < self.global_cooldown_seconds:
            remaining = self.global_cooldown_seconds - time_since_last_global
            return False, f"global_cooldown ({remaining:.0f}s remaining)"
        
        # Check per-symbol active signals limit
        active_count = self._active_signals.get(symbol, 0)
        if active_count >= self.max_active_per_symbol:
            return False, f"max_active_per_symbol ({active_count}/{self.max_active_per_symbol})"
        
        # Check specific signal cooldown
        signal_key = (symbol, direction, setup_type)
        last_signal_time = self._signal_times.get(signal_key, 0)
        time_since_last = current_time - last_signal_time
        
        if time_since_last < self.signal_cooldown_seconds:
            remaining = self.signal_cooldown_seconds - time_since_last
            return False, f"signal_cooldown ({remaining:.0f}s remaining for {symbol} {direction} {setup_type})"
        
        return True, "ok"
    
    def can_send_signal_in_window(self, symbol: str, direction: str, 
                                  window_start_time: int) -> Tuple[bool, str]:
        """
        Check if signal can be sent within the same 30m candle window.
        
        Args:
            symbol: Trading symbol
            direction: Signal direction
            window_start_time: Start timestamp of current 30m window
        
        Returns:
            Tuple of (can_send, reason)
        """
        window_key = (symbol, window_start_time)
        
        if window_key not in self._current_window_signals:
            self._current_window_signals[window_key] = set()
        
        if direction in self._current_window_signals[window_key]:
            return False, f"duplicate_in_window (already sent {direction} signal in this 30m candle)"
        
        return True, "ok"
    
    def record_signal(self, symbol: str, direction: str, setup_type: str,
                     window_start_time: Optional[int] = None,
                     current_time: Optional[float] = None):
        """
        Record that a signal was sent.
        
        Args:
            symbol: Trading symbol
            direction: Signal direction
            setup_type: Type of setup
            window_start_time: Start timestamp of current 30m window (for same-candle tracking)
            current_time: Current timestamp (or use time.time())
        """
        if current_time is None:
            current_time = time.time()
        
        # Record signal time
        signal_key = (symbol, direction, setup_type)
        self._signal_times[signal_key] = current_time
        
        # Update global signal time
        self._last_global_signal_time = current_time
        
        # Increment active signals for symbol
        self._active_signals[symbol] = self._active_signals.get(symbol, 0) + 1
        
        # Record in current window if provided
        if window_start_time is not None:
            window_key = (symbol, window_start_time)
            if window_key not in self._current_window_signals:
                self._current_window_signals[window_key] = set()
            self._current_window_signals[window_key].add(direction)
        
        logger.info(f"Recorded signal: {symbol} {direction} {setup_type} at {datetime.fromtimestamp(current_time)}")
    
    def resolve_signal(self, symbol: str):
        """
        Mark a signal as resolved (e.g., target hit or stop loss).
        Decreases active signal count for the symbol.
        
        Args:
            symbol: Trading symbol
        """
        if symbol in self._active_signals and self._active_signals[symbol] > 0:
            self._active_signals[symbol] -= 1
            logger.info(f"Resolved signal for {symbol}, active count: {self._active_signals[symbol]}")
    
    def cleanup_old_windows(self, current_time: Optional[float] = None, 
                           window_retention_seconds: int = 7200):
        """
        Clean up old window tracking data.
        
        Args:
            current_time: Current timestamp (or use time.time())
            window_retention_seconds: How long to keep window data (default 2 hours)
        """
        if current_time is None:
            current_time = time.time()
        
        # Remove windows older than retention period
        to_remove = []
        for (symbol, window_start), _ in self._current_window_signals.items():
            if current_time - window_start > window_retention_seconds:
                to_remove.append((symbol, window_start))
        
        for key in to_remove:
            del self._current_window_signals[key]
        
        if to_remove:
            logger.debug(f"Cleaned up {len(to_remove)} old window entries")
    
    def get_stats(self) -> dict:
        """Return statistics about current state."""
        return {
            "tracked_signals": len(self._signal_times),
            "active_windows": len(self._current_window_signals),
            "symbols_with_active_signals": len([s for s in self._active_signals.values() if s > 0]),
            "total_active_signals": sum(self._active_signals.values()),
            "last_global_signal": datetime.fromtimestamp(self._last_global_signal_time).isoformat() 
                                 if self._last_global_signal_time > 0 else "none",
        }
    
    def reset(self):
        """Reset all tracking data (for testing or manual reset)."""
        self._signal_times.clear()
        self._last_global_signal_time = 0
        self._active_signals.clear()
        self._current_window_signals.clear()
        logger.info("Signal deduplicator reset")
