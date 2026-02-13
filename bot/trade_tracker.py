"""
Trade Tracker - Stores signals/trades and ingests CSV outcomes
"""
import asyncio
import csv
import logging
import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

from . import config
from .memory_engine import AdaptiveMemory

logger = logging.getLogger(__name__)


class TradeTracker:
    """Tracks trading signals and outcomes with SQLite storage"""
    
    def __init__(self, memory_engine: AdaptiveMemory, db_path: str = None):
        self.db_path = db_path or config.TRADE_DB_PATH
        self.memory_engine = memory_engine
        
        # Track last processed CSV line
        self.last_processed_line = 0
        
        # Initialize database
        self._init_db()
        self._load_state()
    
    def _init_db(self):
        """Initialize SQLite database for trades"""
        
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create trades table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    model_type TEXT NOT NULL,
                    regime TEXT NOT NULL,
                    entry REAL NOT NULL,
                    sl REAL NOT NULL,
                    tp1 REAL NOT NULL,
                    tp2 REAL NOT NULL,
                    tp3 REAL NOT NULL,
                    score INTEGER NOT NULL,
                    rr REAL NOT NULL,
                    outcome TEXT,
                    r_multiple REAL,
                    date_utc TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
            ''')
            
            # Create index on date and symbol for faster lookups
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_trades_date_symbol 
                ON trades(date_utc, symbol, model_type)
            ''')
            
            # Create state table for tracking CSV processing
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tracker_state (
                    id INTEGER PRIMARY KEY,
                    last_processed_line INTEGER,
                    last_check_time TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("Trade tracker database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize trade tracker database: {e}")
    
    def _load_state(self):
        """Load tracker state from database"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT last_processed_line FROM tracker_state WHERE id = 1')
            row = cursor.fetchone()
            
            if row:
                self.last_processed_line = row[0]
                logger.info(f"Loaded state: last processed line = {self.last_processed_line}")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to load tracker state: {e}")
    
    def _save_state(self):
        """Save tracker state to database"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO tracker_state (id, last_processed_line, last_check_time)
                VALUES (1, ?, ?)
            ''', (self.last_processed_line, datetime.utcnow().isoformat()))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save tracker state: {e}")
    
    def store_signal(self, signal_data: Dict) -> int:
        """
        Store a trading signal in the database
        Returns the signal ID
        """
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO trades 
                (symbol, model_type, regime, entry, sl, tp1, tp2, tp3, 
                 score, rr, date_utc, timestamp, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal_data['symbol'],
                signal_data['model_type'],
                signal_data['regime'],
                signal_data['entry'],
                signal_data['sl'],
                signal_data['tp1'],
                signal_data['tp2'],
                signal_data['tp3'],
                signal_data['score'],
                signal_data['rr'],
                signal_data['date_utc'],
                signal_data['timestamp'],
                datetime.utcnow().isoformat()
            ))
            
            signal_id = cursor.lastrowid
            
            conn.commit()
            conn.close()
            
            logger.info(
                f"Signal stored: ID={signal_id}, {signal_data['symbol']} "
                f"{signal_data['model_type']}"
            )
            
            return signal_id
            
        except Exception as e:
            logger.error(f"Failed to store signal: {e}")
            return -1
    
    async def ingest_outcomes_from_csv(self):
        """
        Ingest new outcomes from CSV file
        Lightweight, only processes new lines
        """
        
        csv_path = config.OUTCOMES_CSV_PATH
        
        if not os.path.exists(csv_path):
            logger.debug(f"Outcomes CSV not found: {csv_path}")
            return
        
        try:
            new_outcomes = []
            
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                
                for i, row in enumerate(reader):
                    # Skip already processed lines
                    if i < self.last_processed_line:
                        continue
                    
                    new_outcomes.append(row)
                    self.last_processed_line = i + 1
            
            if not new_outcomes:
                logger.debug("No new outcomes to process")
                return
            
            logger.info(f"Processing {len(new_outcomes)} new outcomes from CSV")
            
            # Process each outcome
            for outcome_row in new_outcomes:
                await self._process_outcome_row(outcome_row)
            
            # Save state
            self._save_state()
            
            logger.info(f"Processed {len(new_outcomes)} outcomes")
            
        except Exception as e:
            logger.error(f"Failed to ingest outcomes: {e}", exc_info=True)
    
    async def _process_outcome_row(self, row: Dict):
        """Process a single outcome row from CSV"""
        
        try:
            # Expected CSV columns: date_utc, symbol, model_type, outcome
            date_utc = row.get('date_utc', '').strip()
            symbol = row.get('symbol', '').strip()
            model_type = row.get('model_type', '').strip()
            outcome = row.get('outcome', '').strip().upper()
            
            if not all([date_utc, symbol, model_type, outcome]):
                logger.warning(f"Incomplete outcome row: {row}")
                return
            
            # Map outcome to R multiple
            r_multiple = config.OUTCOME_TO_R.get(outcome)
            
            if r_multiple is None:
                logger.warning(f"Unknown outcome: {outcome}")
                return
            
            # Find matching signal in database
            signal = self._find_matching_signal(date_utc, symbol, model_type)
            
            if not signal:
                logger.warning(
                    f"No matching signal found for: {date_utc} {symbol} {model_type}"
                )
                return
            
            signal_id = signal[0]
            
            # Update the signal with outcome
            self._update_signal_outcome(signal_id, outcome, r_multiple)
            
            # Update memory engine
            self.memory_engine.update_after_trade_closed(
                symbol=symbol,
                model_type=model_type,
                r_multiple=r_multiple
            )
            
            logger.info(
                f"Outcome processed: {symbol} {model_type} = {outcome} ({r_multiple}R)"
            )
            
        except Exception as e:
            logger.error(f"Failed to process outcome row: {e}", exc_info=True)
    
    def _find_matching_signal(
        self,
        date_utc: str,
        symbol: str,
        model_type: str
    ) -> Optional[tuple]:
        """
        Find matching signal in database
        Matches by date, symbol, and model_type
        If multiple exist, picks the one with closest timestamp
        """
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, timestamp FROM trades
                WHERE date_utc = ? AND symbol = ? AND model_type = ?
                AND outcome IS NULL
                ORDER BY timestamp ASC
                LIMIT 1
            ''', (date_utc, symbol, model_type))
            
            result = cursor.fetchone()
            conn.close()
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to find matching signal: {e}")
            return None
    
    def _update_signal_outcome(
        self,
        signal_id: int,
        outcome: str,
        r_multiple: float
    ):
        """Update signal with outcome"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE trades
                SET outcome = ?, r_multiple = ?
                WHERE id = ?
            ''', (outcome, r_multiple, signal_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to update signal outcome: {e}")
    
    def get_recent_trades(self, limit: int = 20) -> List[Dict]:
        """Get recent trades"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM trades
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            # Convert to list of dicts
            trades = []
            for row in rows:
                trades.append({
                    'id': row[0],
                    'symbol': row[1],
                    'model_type': row[2],
                    'regime': row[3],
                    'entry': row[4],
                    'sl': row[5],
                    'tp1': row[6],
                    'tp2': row[7],
                    'tp3': row[8],
                    'score': row[9],
                    'rr': row[10],
                    'outcome': row[11],
                    'r_multiple': row[12],
                    'date_utc': row[13],
                    'timestamp': row[14],
                    'created_at': row[15]
                })
            
            return trades
            
        except Exception as e:
            logger.error(f"Failed to get recent trades: {e}")
            return []
    
    async def periodic_ingestion_loop(self):
        """Background task to periodically ingest outcomes"""
        
        logger.info("Starting periodic outcome ingestion loop...")
        
        while True:
            try:
                await self.ingest_outcomes_from_csv()
                await asyncio.sleep(config.OUTCOMES_CHECK_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in outcome ingestion loop: {e}", exc_info=True)
                await asyncio.sleep(60)
