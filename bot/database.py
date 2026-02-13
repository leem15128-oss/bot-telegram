"""Database module for SQLite storage."""
import aiosqlite
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from .config import config

logger = logging.getLogger(__name__)


class Database:
    """Async SQLite database manager."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.DATABASE_PATH
        self._conn: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()
    
    async def connect(self):
        """Initialize database connection and create tables."""
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._create_tables()
        logger.info(f"Database connected: {self.db_path}")
    
    async def close(self):
        """Close database connection."""
        if self._conn:
            await self._conn.close()
            logger.info("Database connection closed")
    
    async def _create_tables(self):
        """Create database tables if they don't exist."""
        async with self._lock:
            await self._conn.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    model_type TEXT NOT NULL,
                    score REAL NOT NULL,
                    entry_price REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await self._conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id INTEGER,
                    symbol TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    side TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    pnl REAL,
                    pnl_percent REAL,
                    status TEXT DEFAULT 'open',
                    opened_at TEXT NOT NULL,
                    closed_at TEXT,
                    model_type TEXT,
                    FOREIGN KEY (signal_id) REFERENCES signals (id)
                )
            """)
            
            await self._conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_state (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(category, key)
                )
            """)
            
            await self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol)
            """)
            
            await self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp)
            """)
            
            await self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)
            """)
            
            await self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)
            """)
            
            await self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_category ON memory_state(category)
            """)
            
            await self._conn.commit()
    
    async def save_signal(self, signal_data: Dict[str, Any]) -> int:
        """Save a trading signal to the database."""
        async with self._lock:
            cursor = await self._conn.execute("""
                INSERT INTO signals (timestamp, symbol, timeframe, signal_type, model_type, 
                                   score, entry_price, stop_loss, take_profit, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal_data.get("timestamp"),
                signal_data.get("symbol"),
                signal_data.get("timeframe"),
                signal_data.get("signal_type"),
                signal_data.get("model_type"),
                signal_data.get("score"),
                signal_data.get("entry_price"),
                signal_data.get("stop_loss"),
                signal_data.get("take_profit"),
                signal_data.get("status", "pending")
            ))
            await self._conn.commit()
            return cursor.lastrowid
    
    async def save_trade(self, trade_data: Dict[str, Any]) -> int:
        """Save a trade to the database."""
        async with self._lock:
            cursor = await self._conn.execute("""
                INSERT INTO trades (signal_id, symbol, entry_price, stop_loss, take_profit,
                                  side, quantity, status, opened_at, model_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_data.get("signal_id"),
                trade_data.get("symbol"),
                trade_data.get("entry_price"),
                trade_data.get("stop_loss"),
                trade_data.get("take_profit"),
                trade_data.get("side"),
                trade_data.get("quantity"),
                trade_data.get("status", "open"),
                trade_data.get("opened_at"),
                trade_data.get("model_type")
            ))
            await self._conn.commit()
            return cursor.lastrowid
    
    async def update_trade(self, trade_id: int, update_data: Dict[str, Any]):
        """Update a trade record."""
        async with self._lock:
            set_clause = ", ".join([f"{k} = ?" for k in update_data.keys()])
            values = list(update_data.values()) + [trade_id]
            await self._conn.execute(
                f"UPDATE trades SET {set_clause} WHERE id = ?",
                values
            )
            await self._conn.commit()
    
    async def get_trade(self, trade_id: int) -> Optional[Dict[str, Any]]:
        """Get a trade by ID."""
        async with self._lock:
            cursor = await self._conn.execute(
                "SELECT * FROM trades WHERE id = ?",
                (trade_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def get_open_trades(self) -> List[Dict[str, Any]]:
        """Get all open trades."""
        async with self._lock:
            cursor = await self._conn.execute(
                "SELECT * FROM trades WHERE status = 'open'"
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_closed_trades(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent closed trades."""
        async with self._lock:
            cursor = await self._conn.execute(
                "SELECT * FROM trades WHERE status = 'closed' ORDER BY closed_at DESC LIMIT ?",
                (limit,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def save_memory_state(self, category: str, key: str, value: str):
        """Save or update memory state."""
        async with self._lock:
            await self._conn.execute("""
                INSERT INTO memory_state (category, key, value, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(category, key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP
            """, (category, key, value))
            await self._conn.commit()
    
    async def get_memory_state(self, category: str, key: str) -> Optional[str]:
        """Retrieve memory state value."""
        async with self._lock:
            cursor = await self._conn.execute(
                "SELECT value FROM memory_state WHERE category = ? AND key = ?",
                (category, key)
            )
            row = await cursor.fetchone()
            return row["value"] if row else None
    
    async def get_all_memory_state(self, category: str) -> Dict[str, str]:
        """Get all memory state for a category."""
        async with self._lock:
            cursor = await self._conn.execute(
                "SELECT key, value FROM memory_state WHERE category = ?",
                (category,)
            )
            rows = await cursor.fetchall()
            return {row["key"]: row["value"] for row in rows}


# Global database instance
db = Database()
