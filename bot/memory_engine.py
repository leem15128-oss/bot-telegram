"""
Memory Engine - Adaptive rule-based memory for trading performance
"""
import logging
import sqlite3
import time
from collections import deque, defaultdict
from datetime import datetime, timedelta
from typing import Dict, Optional

from . import config

logger = logging.getLogger(__name__)


class AdaptiveMemory:
    """
    Lightweight adaptive memory using rule-based logic
    No ML, no heavy statistics, just rolling counters and simple rules
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.MEMORY_DB_PATH
        
        # Global performance tracking (last 20 trades)
        self.recent_outcomes = deque(maxlen=config.MEMORY_ROLLING_WINDOW)
        
        # Symbol-specific tracking (last 10 per symbol)
        self.symbol_outcomes = defaultdict(
            lambda: deque(maxlen=config.MEMORY_SYMBOL_WR_WINDOW)
        )
        
        # Regime/model tracking
        self.model_outcomes = {
            'continuation': deque(maxlen=config.MEMORY_ROLLING_WINDOW),
            'reversal': deque(maxlen=config.MEMORY_ROLLING_WINDOW)
        }
        
        # State variables
        self.consecutive_losses = 0
        self.current_drawdown = 0.0
        self.paused_until: Optional[datetime] = None
        self.reversal_disabled_until: Optional[datetime] = None
        
        # Symbol cooldowns
        self.symbol_cooldowns: Dict[str, datetime] = {}
        
        # Adjustments
        self.score_threshold_adjustment = 0
        self.max_signals_adjustment = 0
        self.risk_adjustment = 1.0  # Multiplier
        
        # Initialize database
        self._init_db()
        self._load_from_db()
    
    def _init_db(self):
        """Initialize SQLite database for persistence"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create memory state table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memory_state (
                    id INTEGER PRIMARY KEY,
                    consecutive_losses INTEGER,
                    current_drawdown REAL,
                    paused_until TEXT,
                    reversal_disabled_until TEXT,
                    score_threshold_adjustment INTEGER,
                    max_signals_adjustment INTEGER,
                    risk_adjustment REAL,
                    updated_at TEXT
                )
            ''')
            
            # Create symbol cooldowns table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS symbol_cooldowns (
                    symbol TEXT PRIMARY KEY,
                    cooldown_until TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("Memory database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize memory database: {e}")
    
    def _load_from_db(self):
        """Load memory state from database"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Load memory state
            cursor.execute('SELECT * FROM memory_state WHERE id = 1')
            row = cursor.fetchone()
            
            if row:
                self.consecutive_losses = row[1]
                self.current_drawdown = row[2]
                
                if row[3]:
                    self.paused_until = datetime.fromisoformat(row[3])
                if row[4]:
                    self.reversal_disabled_until = datetime.fromisoformat(row[4])
                
                self.score_threshold_adjustment = row[5]
                self.max_signals_adjustment = row[6]
                self.risk_adjustment = row[7]
                
                logger.info("Memory state loaded from database")
            
            # Load symbol cooldowns
            cursor.execute('SELECT symbol, cooldown_until FROM symbol_cooldowns')
            for symbol, cooldown_str in cursor.fetchall():
                self.symbol_cooldowns[symbol] = datetime.fromisoformat(cooldown_str)
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to load memory state: {e}")
    
    def _save_to_db(self):
        """Save memory state to database"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Save memory state
            cursor.execute('''
                INSERT OR REPLACE INTO memory_state 
                (id, consecutive_losses, current_drawdown, paused_until, 
                 reversal_disabled_until, score_threshold_adjustment, 
                 max_signals_adjustment, risk_adjustment, updated_at)
                VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.consecutive_losses,
                self.current_drawdown,
                self.paused_until.isoformat() if self.paused_until else None,
                self.reversal_disabled_until.isoformat() if self.reversal_disabled_until else None,
                self.score_threshold_adjustment,
                self.max_signals_adjustment,
                self.risk_adjustment,
                datetime.utcnow().isoformat()
            ))
            
            # Clear and save symbol cooldowns
            cursor.execute('DELETE FROM symbol_cooldowns')
            
            now = datetime.utcnow()
            for symbol, cooldown in self.symbol_cooldowns.items():
                if cooldown > now:  # Only save active cooldowns
                    cursor.execute(
                        'INSERT INTO symbol_cooldowns (symbol, cooldown_until) VALUES (?, ?)',
                        (symbol, cooldown.isoformat())
                    )
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save memory state: {e}")
    
    def update_after_trade_closed(
        self,
        symbol: str,
        model_type: str,  # 'continuation' or 'reversal'
        r_multiple: float  # e.g., +1.0 for TP1, -1.0 for SL
    ):
        """
        Update memory after a trade closes
        Called by trade tracker when outcome is ingested
        """
        
        is_win = r_multiple > 0
        
        # Update global outcomes
        self.recent_outcomes.append(is_win)
        
        # Update symbol outcomes
        self.symbol_outcomes[symbol].append(is_win)
        
        # Update model outcomes
        if model_type in self.model_outcomes:
            self.model_outcomes[model_type].append(is_win)
        
        # Update consecutive losses
        if is_win:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
        
        # Update drawdown (simplified)
        # Losses add to drawdown, wins reduce it partially
        # Win recovery multiplier is 0.5 because we only partially close positions at TP1
        WIN_RECOVERY_MULTIPLIER = 0.5
        self.current_drawdown = max(0, self.current_drawdown + r_multiple)
        if r_multiple > 0:
            self.current_drawdown = max(0, self.current_drawdown - r_multiple * WIN_RECOVERY_MULTIPLIER)
        
        # Apply rules
        self._apply_global_rules()
        self._apply_symbol_rules(symbol)
        self._apply_regime_rules()
        
        # Save to database
        self._save_to_db()
        
        logger.info(
            f"Memory updated: {symbol} {model_type} "
            f"{'WIN' if is_win else 'LOSS'} ({r_multiple:.1f}R)"
        )
    
    def _apply_global_rules(self):
        """Apply global performance rules"""
        
        # Rule 1: Low winrate -> increase score threshold
        if len(self.recent_outcomes) >= 10:
            winrate = sum(self.recent_outcomes) / len(self.recent_outcomes)
            
            if winrate < config.MEMORY_LOW_WR_THRESHOLD:
                self.score_threshold_adjustment = config.MEMORY_SCORE_INCREASE
                logger.warning(
                    f"Low winrate detected ({winrate:.1%}), "
                    f"increasing score threshold by {config.MEMORY_SCORE_INCREASE}"
                )
            else:
                self.score_threshold_adjustment = 0
        
        # Rule 2: Consecutive losses -> pause trading
        if self.consecutive_losses >= config.MEMORY_CONSECUTIVE_LOSS_LIMIT:
            self.paused_until = datetime.utcnow() + timedelta(
                seconds=config.MEMORY_PAUSE_DURATION
            )
            logger.warning(
                f"{self.consecutive_losses} consecutive losses, "
                f"pausing trading for 12 hours"
            )
        
        # Rule 3: Moderate drawdown -> reduce signals
        if self.current_drawdown > config.MEMORY_DRAWDOWN_MODERATE:
            self.max_signals_adjustment = config.MEMORY_REDUCED_SIGNALS - config.MAX_SIGNALS_PER_DAY
            logger.warning(
                f"Drawdown at {self.current_drawdown:.1%}, "
                f"reducing max signals to {config.MEMORY_REDUCED_SIGNALS}"
            )
        else:
            self.max_signals_adjustment = 0
        
        # Rule 4: High drawdown -> reduce risk
        if self.current_drawdown > config.MEMORY_DRAWDOWN_HIGH:
            self.risk_adjustment = config.MEMORY_REDUCED_RISK / config.RISK_PER_TRADE
            logger.warning(
                f"High drawdown at {self.current_drawdown:.1%}, "
                f"reducing risk to {config.MEMORY_REDUCED_RISK:.1%}"
            )
        else:
            self.risk_adjustment = 1.0
    
    def _apply_symbol_rules(self, symbol: str):
        """Apply symbol-specific rules"""
        
        symbol_outcomes = self.symbol_outcomes[symbol]
        
        if len(symbol_outcomes) < 2:
            return
        
        # Rule: Consecutive symbol losses -> cooldown
        recent_losses = list(symbol_outcomes)[-config.MEMORY_SYMBOL_LOSS_LIMIT:]
        
        if len(recent_losses) >= config.MEMORY_SYMBOL_LOSS_LIMIT:
            if not any(recent_losses):  # All losses
                self.symbol_cooldowns[symbol] = datetime.utcnow() + timedelta(
                    seconds=config.MEMORY_SYMBOL_COOLDOWN
                )
                logger.warning(
                    f"Symbol {symbol}: {config.MEMORY_SYMBOL_LOSS_LIMIT} "
                    f"consecutive losses, 24h cooldown applied"
                )
    
    def _apply_regime_rules(self):
        """Apply regime/model-specific rules"""
        
        # Rule: Low reversal winrate -> disable reversal
        reversal_outcomes = self.model_outcomes['reversal']
        
        if len(reversal_outcomes) >= 10:
            reversal_wr = sum(reversal_outcomes) / len(reversal_outcomes)
            
            if reversal_wr < config.MEMORY_REVERSAL_WR_THRESHOLD:
                self.reversal_disabled_until = datetime.utcnow() + timedelta(
                    seconds=config.MEMORY_REVERSAL_DISABLE_DURATION
                )
                logger.warning(
                    f"Reversal winrate low ({reversal_wr:.1%}), "
                    f"disabling reversals for 48 hours"
                )
    
    def is_trading_paused(self) -> bool:
        """Check if trading is currently paused"""
        
        if self.paused_until is None:
            return False
        
        if datetime.utcnow() > self.paused_until:
            # Reset pause
            self.paused_until = None
            self._save_to_db()
            return False
        
        return True
    
    def is_symbol_on_cooldown(self, symbol: str) -> bool:
        """Check if symbol is on cooldown"""
        
        if symbol not in self.symbol_cooldowns:
            return False
        
        if datetime.utcnow() > self.symbol_cooldowns[symbol]:
            # Cooldown expired
            del self.symbol_cooldowns[symbol]
            self._save_to_db()
            return False
        
        return True
    
    def is_reversal_disabled(self) -> bool:
        """Check if reversal model is disabled"""
        
        if self.reversal_disabled_until is None:
            return False
        
        if datetime.utcnow() > self.reversal_disabled_until:
            # Reset disable
            self.reversal_disabled_until = None
            self._save_to_db()
            return False
        
        return True
    
    def get_adjusted_score_threshold(self, base_threshold: int) -> int:
        """Get adjusted score threshold"""
        return base_threshold + self.score_threshold_adjustment
    
    def get_adjusted_max_signals(self, base_max: int) -> int:
        """Get adjusted max signals per day"""
        return max(1, base_max + self.max_signals_adjustment)
    
    def get_adjusted_risk(self, base_risk: float) -> float:
        """Get adjusted risk percentage"""
        return base_risk * self.risk_adjustment
    
    def get_symbol_score_adjustment(self, symbol: str) -> int:
        """Get score adjustment for specific symbol"""
        
        symbol_outcomes = self.symbol_outcomes[symbol]
        
        if len(symbol_outcomes) < config.MEMORY_SYMBOL_WR_WINDOW:
            return 0
        
        winrate = sum(symbol_outcomes) / len(symbol_outcomes)
        
        if winrate < config.MEMORY_SYMBOL_WR_THRESHOLD:
            return config.MEMORY_SCORE_INCREASE
        
        return 0
    
    def should_prioritize_continuation(self) -> bool:
        """Check if we should prioritize continuation setups"""
        
        continuation_outcomes = self.model_outcomes['continuation']
        
        if len(continuation_outcomes) < 10:
            return False
        
        continuation_wr = sum(continuation_outcomes) / len(continuation_outcomes)
        
        return continuation_wr > config.MEMORY_TRENDING_WR_THRESHOLD
