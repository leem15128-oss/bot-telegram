"""Adaptive Behavioral Memory Layer for dynamic parameter adjustment."""
import asyncio
import logging
import json
from collections import deque
from typing import Dict, Any, Optional, Deque
from datetime import datetime, timedelta
from .database import db
from .risk_manager import risk_manager

logger = logging.getLogger(__name__)


class AdaptiveMemory:
    """
    Lightweight adaptive memory engine that tracks performance and adjusts parameters.
    Uses rolling counters with deque(maxlen=20) and stores state in SQLite.
    """
    
    def __init__(self):
        # Global performance metrics (rolling window of last 20)
        self.last_20_results: Deque[bool] = deque(maxlen=20)  # True=win, False=loss
        self.consecutive_losses = 0
        self.current_drawdown_percent = 0.0
        
        # Model-specific tracking
        self.continuation_results: Deque[bool] = deque(maxlen=20)
        self.reversal_results: Deque[bool] = deque(maxlen=20)
        
        # Symbol-specific memory: symbol -> {'last_result': bool, 'consecutive_losses': int, 'last_10': deque}
        self.symbol_memory: Dict[str, Dict[str, Any]] = {}
        
        # Cooldown tracking
        self.symbol_cooldowns: Dict[str, datetime] = {}  # symbol -> cooldown_until
        self.trading_paused_until: Optional[datetime] = None
        self.reversal_model_disabled_until: Optional[datetime] = None
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
        
        # Initial capital tracking (simplified)
        self.initial_capital = 1000.0
        self.current_capital = 1000.0
        self.peak_capital = 1000.0
    
    async def initialize(self):
        """Load memory state from database."""
        try:
            async with self._lock:
                # Load global state
                global_state = await db.get_all_memory_state('global')
                if global_state:
                    if 'last_20_results' in global_state:
                        results = json.loads(global_state['last_20_results'])
                        self.last_20_results = deque(results, maxlen=20)
                    
                    if 'consecutive_losses' in global_state:
                        self.consecutive_losses = int(global_state['consecutive_losses'])
                    
                    if 'current_drawdown' in global_state:
                        self.current_drawdown_percent = float(global_state['current_drawdown'])
                    
                    if 'continuation_results' in global_state:
                        results = json.loads(global_state['continuation_results'])
                        self.continuation_results = deque(results, maxlen=20)
                    
                    if 'reversal_results' in global_state:
                        results = json.loads(global_state['reversal_results'])
                        self.reversal_results = deque(results, maxlen=20)
                    
                    if 'current_capital' in global_state:
                        self.current_capital = float(global_state['current_capital'])
                        self.peak_capital = max(self.peak_capital, self.current_capital)
                
                # Load symbol memory
                symbol_state = await db.get_all_memory_state('symbols')
                if symbol_state:
                    for key, value in symbol_state.items():
                        self.symbol_memory[key] = json.loads(value)
                        # Convert last_10 back to deque
                        if 'last_10' in self.symbol_memory[key]:
                            self.symbol_memory[key]['last_10'] = deque(
                                self.symbol_memory[key]['last_10'], 
                                maxlen=10
                            )
                
                logger.info("Adaptive memory initialized from database")
        
        except Exception as e:
            logger.error(f"Error loading memory state: {e}")
            # Continue with fresh state
    
    async def save_state(self):
        """Save memory state to database."""
        try:
            async with self._lock:
                # Save global state
                await db.save_memory_state('global', 'last_20_results', 
                                          json.dumps(list(self.last_20_results)))
                await db.save_memory_state('global', 'consecutive_losses', 
                                          str(self.consecutive_losses))
                await db.save_memory_state('global', 'current_drawdown', 
                                          str(self.current_drawdown_percent))
                await db.save_memory_state('global', 'continuation_results', 
                                          json.dumps(list(self.continuation_results)))
                await db.save_memory_state('global', 'reversal_results', 
                                          json.dumps(list(self.reversal_results)))
                await db.save_memory_state('global', 'current_capital', 
                                          str(self.current_capital))
                
                # Save symbol memory
                for symbol, mem in self.symbol_memory.items():
                    # Convert deque to list for JSON serialization
                    mem_copy = mem.copy()
                    if 'last_10' in mem_copy:
                        mem_copy['last_10'] = list(mem_copy['last_10'])
                    await db.save_memory_state('symbols', symbol, json.dumps(mem_copy))
        
        except Exception as e:
            logger.error(f"Error saving memory state: {e}")
    
    async def update_after_trade_closed(self, trade_data: Dict[str, Any]):
        """
        Update memory after a trade is closed.
        This is the main entry point for memory updates.
        """
        try:
            async with self._lock:
                symbol = trade_data.get('symbol')
                model_type = trade_data.get('model_type')
                pnl = trade_data.get('pnl', 0.0)
                pnl_percent = trade_data.get('pnl_percent', 0.0)
                
                is_win = pnl > 0
                
                # Update global performance
                self.last_20_results.append(is_win)
                
                if is_win:
                    self.consecutive_losses = 0
                else:
                    self.consecutive_losses += 1
                
                # Update capital tracking
                self.current_capital += pnl
                if self.current_capital > self.peak_capital:
                    self.peak_capital = self.current_capital
                
                # Calculate drawdown
                if self.peak_capital > 0:
                    self.current_drawdown_percent = (
                        (self.peak_capital - self.current_capital) / self.peak_capital
                    ) * 100
                
                # Update model-specific results
                if model_type == 'continuation':
                    self.continuation_results.append(is_win)
                elif model_type == 'reversal':
                    self.reversal_results.append(is_win)
                
                # Update symbol memory
                if symbol not in self.symbol_memory:
                    self.symbol_memory[symbol] = {
                        'last_result': is_win,
                        'consecutive_losses': 0 if is_win else 1,
                        'last_10': deque([is_win], maxlen=10)
                    }
                else:
                    self.symbol_memory[symbol]['last_result'] = is_win
                    if is_win:
                        self.symbol_memory[symbol]['consecutive_losses'] = 0
                    else:
                        self.symbol_memory[symbol]['consecutive_losses'] += 1
                    self.symbol_memory[symbol]['last_10'].append(is_win)
                
                logger.info(f"Memory updated for {symbol}: win={is_win}, pnl={pnl:.2f}")
                
                # Apply rules
                await self._apply_rules()
                
                # Save state
                await self.save_state()
        
        except Exception as e:
            logger.error(f"Error updating memory: {e}")
    
    async def _apply_rules(self):
        """Apply adaptive rules based on current memory state."""
        now = datetime.utcnow()
        
        # Rule 1: Global performance - adjust score threshold
        if len(self.last_20_results) >= 10:
            winrate = sum(self.last_20_results) / len(self.last_20_results) * 100
            if winrate < 55:
                logger.warning(f"Low winrate ({winrate:.1f}%), increasing score threshold")
                risk_manager.update_score_threshold(risk_manager.score_threshold + 5)
        
        # Rule 2: Consecutive losses - pause trading
        if self.consecutive_losses >= 3:
            self.trading_paused_until = now + timedelta(hours=12)
            logger.warning(f"3+ consecutive losses, pausing trading until {self.trading_paused_until}")
        
        # Rule 3: Drawdown management
        if self.current_drawdown_percent > 5:
            logger.warning(f"Drawdown {self.current_drawdown_percent:.1f}%, reducing max signals")
            risk_manager.update_max_signals_per_day(2)
        
        if self.current_drawdown_percent > 8:
            logger.warning(f"High drawdown {self.current_drawdown_percent:.1f}%, reducing risk")
            risk_manager.update_risk_per_trade(0.5)
        
        # Rule 4: Symbol-specific cooldowns
        for symbol, mem in self.symbol_memory.items():
            if mem['consecutive_losses'] >= 2:
                cooldown_until = now + timedelta(hours=24)
                self.symbol_cooldowns[symbol] = cooldown_until
                logger.warning(f"Symbol {symbol} on 24h cooldown (2+ consecutive losses)")
        
        # Rule 5: Reversal model performance
        if len(self.reversal_results) >= 10:
            reversal_winrate = sum(self.reversal_results) / len(self.reversal_results) * 100
            if reversal_winrate < 45:
                self.reversal_model_disabled_until = now + timedelta(hours=48)
                risk_manager.set_model_enabled('reversal', False)
                logger.warning(f"Reversal model disabled for 48h (winrate: {reversal_winrate:.1f}%)")
        
        # Rule 6: Continuation model prioritization
        if len(self.continuation_results) >= 10:
            continuation_winrate = sum(self.continuation_results) / len(self.continuation_results) * 100
            if continuation_winrate > 65:
                logger.info(f"Continuation model performing well ({continuation_winrate:.1f}%)")
                # Prioritize by lowering threshold slightly for continuation
        
        # Auto-restore after cooldowns
        if self.reversal_model_disabled_until and now >= self.reversal_model_disabled_until:
            risk_manager.set_model_enabled('reversal', True)
            self.reversal_model_disabled_until = None
            logger.info("Reversal model re-enabled after cooldown")
        
        if self.trading_paused_until and now >= self.trading_paused_until:
            self.trading_paused_until = None
            logger.info("Trading resumed after pause")
    
    async def can_trade(self, symbol: str, model_type: str) -> tuple[bool, str]:
        """
        Check if trading is allowed for a symbol and model type.
        
        Returns:
            (can_trade: bool, reason: str)
        """
        try:
            async with self._lock:
                now = datetime.utcnow()
                
                # Check global trading pause
                if self.trading_paused_until and now < self.trading_paused_until:
                    return False, f"Trading paused until {self.trading_paused_until}"
                
                # Check model enabled
                if not risk_manager.is_model_enabled(model_type):
                    return False, f"{model_type} model disabled"
                
                # Check symbol cooldown
                if symbol in self.symbol_cooldowns:
                    cooldown_until = self.symbol_cooldowns[symbol]
                    if now < cooldown_until:
                        return False, f"Symbol on cooldown until {cooldown_until}"
                    else:
                        # Remove expired cooldown
                        del self.symbol_cooldowns[symbol]
                
                return True, "OK"
        
        except Exception as e:
            logger.error(f"Error in can_trade check: {e}")
            return True, "OK"  # Fail open
    
    def get_symbol_score_adjustment(self, symbol: str) -> int:
        """
        Get score threshold adjustment for a specific symbol.
        Returns additional threshold to add.
        """
        if symbol not in self.symbol_memory:
            return 0
        
        mem = self.symbol_memory[symbol]
        
        # Rule: If symbol winrate < 50%, require +5 higher score
        if 'last_10' in mem and len(mem['last_10']) >= 5:
            winrate = sum(mem['last_10']) / len(mem['last_10']) * 100
            if winrate < 50:
                return 5
        
        return 0
    
    def get_status(self) -> Dict[str, Any]:
        """Get current memory status for monitoring."""
        winrate = 0
        if len(self.last_20_results) > 0:
            winrate = sum(self.last_20_results) / len(self.last_20_results) * 100
        
        continuation_winrate = 0
        if len(self.continuation_results) > 0:
            continuation_winrate = sum(self.continuation_results) / len(self.continuation_results) * 100
        
        reversal_winrate = 0
        if len(self.reversal_results) > 0:
            reversal_winrate = sum(self.reversal_results) / len(self.reversal_results) * 100
        
        return {
            'last_20_winrate': round(winrate, 1),
            'consecutive_losses': self.consecutive_losses,
            'current_drawdown_percent': round(self.current_drawdown_percent, 2),
            'continuation_winrate': round(continuation_winrate, 1),
            'reversal_winrate': round(reversal_winrate, 1),
            'trading_paused': self.trading_paused_until is not None,
            'active_symbol_cooldowns': len(self.symbol_cooldowns),
            'current_capital': round(self.current_capital, 2)
        }


# Global adaptive memory instance
adaptive_memory = AdaptiveMemory()
