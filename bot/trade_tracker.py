"""
Trade tracker module.
Tracks active signals and their outcomes for monitoring and statistics.
"""

import sqlite3
import logging
from typing import Dict, List, Optional
from datetime import datetime
import bot.config as config

logger = logging.getLogger(__name__)


class TradeTracker:
    """
    Tracks trading signals in a SQLite database.
    Monitors active signals and their resolution.
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize trade tracker.
        
        Args:
            db_path: Path to SQLite database (default from config)
        """
        self.db_path = db_path or config.DATABASE_PATH
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Signals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                setup_type TEXT NOT NULL,
                entry REAL NOT NULL,
                stop_loss REAL NOT NULL,
                take_profit REAL NOT NULL,
                score REAL NOT NULL,
                trends TEXT,
                status TEXT DEFAULT 'active',
                resolution TEXT,
                resolved_at TEXT,
                pnl_pct REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Component scores table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS component_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id INTEGER NOT NULL,
                component TEXT NOT NULL,
                score REAL NOT NULL,
                weighted REAL NOT NULL,
                details TEXT,
                FOREIGN KEY (signal_id) REFERENCES signals (id)
            )
        ''')
        
        # Create indexes
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_signals_symbol 
            ON signals(symbol)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_signals_status 
            ON signals(status)
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info(f"Trade tracker initialized with database: {self.db_path}")
    
    def add_signal(self, signal: Dict) -> int:
        """
        Add a new signal to the tracker.
        
        Args:
            signal: Signal dictionary from strategy
        
        Returns:
            Signal ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Insert signal
        trends_str = f"{signal['trends']['30m']},{signal['trends']['1h']},{signal['trends']['4h']}"
        
        cursor.execute('''
            INSERT INTO signals (
                timestamp, symbol, direction, setup_type,
                entry, stop_loss, take_profit, score, trends
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            signal['symbol'],
            signal['direction'],
            signal['setup_type'],
            signal['entry'],
            signal['stop_loss'],
            signal['take_profit'],
            signal['score'],
            trends_str
        ))
        
        signal_id = cursor.lastrowid
        
        # Insert component scores
        for component, data in signal['component_scores'].items():
            details = data.get('reason', '') or ','.join(data.get('patterns', []))
            cursor.execute('''
                INSERT INTO component_scores (
                    signal_id, component, score, weighted, details
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                signal_id,
                component,
                data['score'],
                data['weighted'],
                details
            ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Tracked signal #{signal_id}: {signal['symbol']} {signal['direction']} "
                   f"{signal['setup_type']} @ {signal['entry']}")
        
        return signal_id
    
    def update_signal_status(self, signal_id: int, current_price: float):
        """
        Update signal status based on current price.
        
        Args:
            signal_id: Signal ID to update
            current_price: Current market price
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get signal details
        cursor.execute('''
            SELECT direction, entry, stop_loss, take_profit, status
            FROM signals WHERE id = ?
        ''', (signal_id,))
        
        row = cursor.fetchone()
        if not row or row[4] != 'active':
            conn.close()
            return
        
        direction, entry, stop_loss, take_profit, status = row
        
        # Check if resolved
        resolution = None
        pnl_pct = 0
        
        if direction == 'long':
            if current_price <= stop_loss:
                resolution = 'stop_loss'
                pnl_pct = ((current_price - entry) / entry) * 100
            elif current_price >= take_profit:
                resolution = 'take_profit'
                pnl_pct = ((current_price - entry) / entry) * 100
        else:  # short
            if current_price >= stop_loss:
                resolution = 'stop_loss'
                pnl_pct = ((entry - current_price) / entry) * 100
            elif current_price <= take_profit:
                resolution = 'take_profit'
                pnl_pct = ((entry - current_price) / entry) * 100
        
        if resolution:
            cursor.execute('''
                UPDATE signals
                SET status = 'closed',
                    resolution = ?,
                    resolved_at = ?,
                    pnl_pct = ?
                WHERE id = ?
            ''', (resolution, datetime.now().isoformat(), pnl_pct, signal_id))
            
            conn.commit()
            logger.info(f"Signal #{signal_id} resolved: {resolution} (PnL: {pnl_pct:.2f}%)")
        
        conn.close()
    
    def get_active_signals(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        Get all active signals.
        
        Args:
            symbol: Filter by symbol (optional)
        
        Returns:
            List of active signal dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if symbol:
            cursor.execute('''
                SELECT id, timestamp, symbol, direction, setup_type,
                       entry, stop_loss, take_profit, score
                FROM signals
                WHERE status = 'active' AND symbol = ?
                ORDER BY timestamp DESC
            ''', (symbol,))
        else:
            cursor.execute('''
                SELECT id, timestamp, symbol, direction, setup_type,
                       entry, stop_loss, take_profit, score
                FROM signals
                WHERE status = 'active'
                ORDER BY timestamp DESC
            ''')
        
        signals = []
        for row in cursor.fetchall():
            signals.append({
                'id': row[0],
                'timestamp': row[1],
                'symbol': row[2],
                'direction': row[3],
                'setup_type': row[4],
                'entry': row[5],
                'stop_loss': row[6],
                'take_profit': row[7],
                'score': row[8],
            })
        
        conn.close()
        return signals
    
    def get_stats(self) -> Dict:
        """Get statistics about tracked signals."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total signals
        cursor.execute('SELECT COUNT(*) FROM signals')
        total = cursor.fetchone()[0]
        
        # Active signals
        cursor.execute('SELECT COUNT(*) FROM signals WHERE status = "active"')
        active = cursor.fetchone()[0]
        
        # Closed signals
        cursor.execute('SELECT COUNT(*) FROM signals WHERE status = "closed"')
        closed = cursor.fetchone()[0]
        
        # Win rate
        cursor.execute('''
            SELECT COUNT(*) FROM signals 
            WHERE status = "closed" AND resolution = "take_profit"
        ''')
        wins = cursor.fetchone()[0]
        
        win_rate = (wins / closed * 100) if closed > 0 else 0
        
        # Average score
        cursor.execute('SELECT AVG(score) FROM signals')
        avg_score = cursor.fetchone()[0] or 0
        
        # Average PnL
        cursor.execute('''
            SELECT AVG(pnl_pct) FROM signals 
            WHERE status = "closed" AND pnl_pct IS NOT NULL
        ''')
        avg_pnl = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_signals': total,
            'active': active,
            'closed': closed,
            'wins': wins,
            'losses': closed - wins,
            'win_rate_pct': win_rate,
            'avg_score': avg_score,
            'avg_pnl_pct': avg_pnl,
        }
