"""Market data manager for candle storage and processing."""
import asyncio
import logging
from collections import deque
from typing import Dict, List, Optional, Deque
from datetime import datetime
from .config import config

logger = logging.getLogger(__name__)


class CandleData:
    """Represents a single candle."""
    
    def __init__(self, symbol: str, timeframe: str, data: List):
        self.symbol = symbol
        self.timeframe = timeframe
        self.open_time = int(data[0])
        self.open = float(data[1])
        self.high = float(data[2])
        self.low = float(data[3])
        self.close = float(data[4])
        self.volume = float(data[5])
        self.close_time = int(data[6])
        self.is_closed = data[8] if len(data) > 8 else True  # Default to closed for historical data
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'open_time': self.open_time,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'close_time': self.close_time,
            'is_closed': self.is_closed
        }


class MarketDataManager:
    """Manages market data storage and provides data access."""
    
    def __init__(self):
        # Storage: symbol -> timeframe -> deque of candles
        self.candles: Dict[str, Dict[str, Deque[CandleData]]] = {}
        self._lock = asyncio.Lock()
        self._warmup_complete = False
    
    async def warmup(self, symbols: List[str], timeframes: List[str]):
        """Warmup with historical data for given symbols and timeframes."""
        from .binance_client import binance_client
        
        logger.info(f"Starting market data warmup for {len(symbols)} symbols, {len(timeframes)} timeframes")
        
        # Limit concurrent requests to avoid overwhelming the API
        semaphore = asyncio.Semaphore(5)
        
        async def fetch_and_store(symbol: str, timeframe: str):
            async with semaphore:
                try:
                    # Fetch historical klines
                    klines = await binance_client.get_klines(
                        symbol, 
                        timeframe, 
                        limit=config.MAX_CANDLES_PER_TIMEFRAME
                    )
                    
                    # Store candles
                    async with self._lock:
                        if symbol not in self.candles:
                            self.candles[symbol] = {}
                        if timeframe not in self.candles[symbol]:
                            self.candles[symbol][timeframe] = deque(
                                maxlen=config.MAX_CANDLES_PER_TIMEFRAME
                            )
                        
                        for kline in klines:
                            candle = CandleData(symbol, timeframe, kline)
                            self.candles[symbol][timeframe].append(candle)
                    
                    logger.debug(f"Warmed up {symbol} {timeframe}: {len(klines)} candles")
                    
                except Exception as e:
                    logger.error(f"Error warming up {symbol} {timeframe}: {e}")
        
        # Create tasks for all symbol/timeframe combinations
        tasks = []
        for symbol in symbols:
            for timeframe in timeframes:
                tasks.append(fetch_and_store(symbol, timeframe))
        
        # Execute all warmup tasks
        await asyncio.gather(*tasks, return_exceptions=True)
        
        self._warmup_complete = True
        logger.info("Market data warmup complete")
    
    async def update_candle(self, symbol: str, timeframe: str, kline_data: Dict):
        """Update or append candle from WebSocket data."""
        # Only process closed candles
        is_closed = kline_data.get('x', False)
        if not is_closed:
            return
        
        # Extract kline info
        k = kline_data.get('k', {})
        candle_data = [
            k.get('t'),  # open time
            k.get('o'),  # open
            k.get('h'),  # high
            k.get('l'),  # low
            k.get('c'),  # close
            k.get('v'),  # volume
            k.get('T'),  # close time
            k.get('q'),  # quote volume
            True  # is_closed
        ]
        
        candle = CandleData(symbol, timeframe, candle_data)
        
        async with self._lock:
            # Initialize storage if needed
            if symbol not in self.candles:
                self.candles[symbol] = {}
            if timeframe not in self.candles[symbol]:
                self.candles[symbol][timeframe] = deque(
                    maxlen=config.MAX_CANDLES_PER_TIMEFRAME
                )
            
            # Check if this is an update to the last candle or a new one
            candle_queue = self.candles[symbol][timeframe]
            if candle_queue and candle_queue[-1].open_time == candle.open_time:
                # Update existing candle
                candle_queue[-1] = candle
            else:
                # Append new candle
                candle_queue.append(candle)
        
        logger.debug(f"Updated {symbol} {timeframe} candle: close={candle.close:.2f}")
        return candle
    
    def get_candles(self, symbol: str, timeframe: str, limit: int = None) -> List[CandleData]:
        """Get candles for a symbol and timeframe."""
        if symbol not in self.candles or timeframe not in self.candles[symbol]:
            return []
        
        candles = list(self.candles[symbol][timeframe])
        
        if limit:
            return candles[-limit:]
        return candles
    
    def get_latest_candle(self, symbol: str, timeframe: str) -> Optional[CandleData]:
        """Get the most recent candle for a symbol and timeframe."""
        candles = self.get_candles(symbol, timeframe, limit=1)
        return candles[0] if candles else None
    
    def has_sufficient_data(self, symbol: str, timeframe: str, min_candles: int = 50) -> bool:
        """Check if we have sufficient data for analysis."""
        candles = self.get_candles(symbol, timeframe)
        return len(candles) >= min_candles
    
    def is_warmup_complete(self) -> bool:
        """Check if warmup is complete."""
        return self._warmup_complete


# Global market data manager
market_data = MarketDataManager()
