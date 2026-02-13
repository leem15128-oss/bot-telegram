"""
Risk Manager - Handles position sizing and risk management
"""
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

from . import config

logger = logging.getLogger(__name__)


class RiskManager:
    """Manages risk and position sizing"""
    
    def __init__(self):
        # Track active trades per symbol
        self.active_trades: Dict[str, Dict] = {}
        
        # Track recent signals per symbol (for cooldown)
        self.last_signal_time: Dict[str, datetime] = {}
        self.last_signal_candle: Dict[str, int] = {}
        
        # Daily signal counter
        self.daily_signals = 0
        self.last_reset_date = datetime.utcnow().date()
    
    def can_trade_symbol(self, symbol: str) -> bool:
        """Check if we can trade this symbol"""
        
        # Check if there's already an active trade
        if symbol in self.active_trades:
            logger.debug(f"Symbol {symbol} already has an active trade")
            return False
        
        return True
    
    def check_cooldown(
        self,
        symbol: str,
        current_candle_index: int
    ) -> bool:
        """Check if symbol is in cooldown period"""
        
        if symbol not in self.last_signal_candle:
            return True
        
        candles_since_signal = current_candle_index - self.last_signal_candle[symbol]
        
        if candles_since_signal < config.CANDLE_COOLDOWN:
            logger.debug(
                f"Symbol {symbol} in cooldown: "
                f"{candles_since_signal}/{config.CANDLE_COOLDOWN} candles"
            )
            return False
        
        return True
    
    def check_daily_limit(self, max_signals: Optional[int] = None) -> bool:
        """Check if we've hit the daily signal limit"""
        
        # Reset counter if it's a new day
        current_date = datetime.utcnow().date()
        if current_date != self.last_reset_date:
            self.daily_signals = 0
            self.last_reset_date = current_date
        
        # Check limit
        limit = max_signals if max_signals is not None else config.MAX_SIGNALS_PER_DAY
        
        if self.daily_signals >= limit:
            logger.debug(f"Daily signal limit reached: {self.daily_signals}/{limit}")
            return False
        
        return True
    
    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        account_balance: float,
        risk_percentage: Optional[float] = None
    ) -> Dict:
        """
        Calculate position size based on risk
        
        Returns position details including size and dollar risk
        """
        
        risk_pct = risk_percentage if risk_percentage is not None else config.RISK_PER_TRADE
        
        # Calculate risk in dollars
        risk_amount = account_balance * risk_pct
        
        # Calculate price distance to stop loss
        price_risk = abs(entry_price - stop_loss)
        
        if price_risk == 0:
            logger.error("Stop loss equals entry price")
            return None
        
        # Calculate position size
        position_size = risk_amount / price_risk
        
        return {
            'position_size': position_size,
            'risk_amount': risk_amount,
            'risk_percentage': risk_pct,
            'price_risk': price_risk
        }
    
    def calculate_targets(
        self,
        entry: float,
        stop_loss: float,
        direction: str,  # "long" or "short"
        liquidity_levels: Optional[Dict] = None
    ) -> Dict:
        """
        Calculate take profit targets
        
        TP1 = 1R
        TP2 = internal liquidity or 2R
        TP3 = external liquidity or 3R
        """
        
        risk = abs(entry - stop_loss)
        
        if direction == "long":
            tp1 = entry + (risk * config.TP1_RR)
            tp2 = entry + (risk * config.TP2_RR)
            tp3 = entry + (risk * config.TP3_RR)
            
            # Override with liquidity levels if available
            if liquidity_levels:
                internal = liquidity_levels.get('internal', {})
                external = liquidity_levels.get('external', {})
                
                if internal.get('high'):
                    tp2 = internal['high']
                
                if external.get('high'):
                    tp3 = external['high']
        
        else:  # short
            tp1 = entry - (risk * config.TP1_RR)
            tp2 = entry - (risk * config.TP2_RR)
            tp3 = entry - (risk * config.TP3_RR)
            
            # Override with liquidity levels if available
            if liquidity_levels:
                internal = liquidity_levels.get('internal', {})
                external = liquidity_levels.get('external', {})
                
                if internal.get('low'):
                    tp2 = internal['low']
                
                if external.get('low'):
                    tp3 = external['low']
        
        return {
            'tp1': tp1,
            'tp2': tp2,
            'tp3': tp3,
            'tp1_rr': self._calculate_rr(entry, stop_loss, tp1),
            'tp2_rr': self._calculate_rr(entry, stop_loss, tp2),
            'tp3_rr': self._calculate_rr(entry, stop_loss, tp3)
        }
    
    def _calculate_rr(self, entry: float, stop_loss: float, take_profit: float) -> float:
        """Calculate risk/reward ratio"""
        
        risk = abs(entry - stop_loss)
        reward = abs(take_profit - entry)
        
        if risk == 0:
            return 0
        
        return reward / risk
    
    def validate_risk_reward(
        self,
        entry: float,
        stop_loss: float,
        take_profit: float,
        min_rr: Optional[float] = None
    ) -> bool:
        """Validate that risk/reward ratio meets minimum"""
        
        min_required = min_rr if min_rr is not None else config.MIN_RR_RATIO
        
        rr = self._calculate_rr(entry, stop_loss, take_profit)
        
        return rr >= min_required
    
    def register_signal(
        self,
        symbol: str,
        current_candle_index: int
    ):
        """Register a new signal"""
        
        self.last_signal_time[symbol] = datetime.utcnow()
        self.last_signal_candle[symbol] = current_candle_index
        self.daily_signals += 1
        
        logger.debug(
            f"Signal registered: {symbol}, "
            f"daily count: {self.daily_signals}/{config.MAX_SIGNALS_PER_DAY}"
        )
    
    def register_trade(
        self,
        symbol: str,
        trade_details: Dict
    ):
        """Register an active trade"""
        
        self.active_trades[symbol] = {
            **trade_details,
            'opened_at': datetime.utcnow()
        }
        
        logger.info(f"Trade registered: {symbol}")
    
    def close_trade(self, symbol: str):
        """Close/remove an active trade"""
        
        if symbol in self.active_trades:
            del self.active_trades[symbol]
            logger.info(f"Trade closed: {symbol}")
    
    def get_active_trade_count(self) -> int:
        """Get number of active trades"""
        return len(self.active_trades)
