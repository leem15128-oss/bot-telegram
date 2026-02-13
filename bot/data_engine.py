"""
Data Engine - WebSocket sharding for real-time kline data
"""
import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from typing import Dict, List, Optional, Set
import aiohttp
import websockets

from . import config
from .utils import async_retry_with_backoff, RateLimiter, chunks

logger = logging.getLogger(__name__)


class DataEngine:
    """Manages WebSocket connections with sharding for kline data"""
    
    def __init__(self, symbol_engine):
        self.symbol_engine = symbol_engine
        
        # Candle storage: {symbol: {timeframe: deque([candles])}}
        self.candles: Dict[str, Dict[str, deque]] = defaultdict(
            lambda: {tf: deque(maxlen=config.MAX_CANDLES_STORED) for tf in config.TIMEFRAMES}
        )
        
        # WebSocket connections
        self.ws_connections: List[websockets.WebSocketClientProtocol] = []
        self.ws_tasks: List[asyncio.Task] = []
        
        # Track which symbols are subscribed
        self.subscribed_symbols: Set[str] = set()
        
        # Rate limiter for REST API warmup
        self.rate_limiter = RateLimiter(config.REST_RATE_LIMIT_DELAY)
        
        # Event for signaling new closed candles
        self.new_candle_events: Dict[str, asyncio.Event] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        # Semaphore for concurrent symbol processing
        self.scan_semaphore = asyncio.Semaphore(config.CONCURRENT_SYMBOL_SCANS)
    
    async def initialize(self):
        """Initialize data engine with warmup data"""
        logger.info("Initializing data engine...")
        
        # Get active symbols
        symbols = self.symbol_engine.get_active_symbols()
        
        # Warmup historical data for active symbols
        await self._warmup_historical_data(symbols)
        
        # Start WebSocket connections
        await self._start_websocket_connections(symbols)
        
        logger.info(f"Data engine initialized with {len(symbols)} symbols")
    
    async def _warmup_historical_data(self, symbols: List[str]):
        """Fetch initial historical data via REST API"""
        logger.info(f"Warming up historical data for {len(symbols)} symbols...")
        
        tasks = []
        for symbol in symbols:
            for timeframe in config.TIMEFRAMES:
                task = self._fetch_historical_klines(symbol, timeframe)
                tasks.append(task)
        
        # Execute all warmup tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successes and failures
        success = sum(1 for r in results if not isinstance(r, Exception))
        failed = len(results) - success
        
        logger.info(
            f"Warmup complete: {success} successful, {failed} failed"
        )
    
    async def _fetch_historical_klines(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 500
    ):
        """Fetch historical klines from REST API"""
        
        async def fetch():
            await self.rate_limiter.acquire()
            
            url = f"{config.BINANCE_FUTURES_REST_BASE}/fapi/v1/klines"
            params = {
                'symbol': symbol,
                'interval': timeframe,
                'limit': min(limit, 1500)  # Binance max is 1500
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()
            
            return data
        
        try:
            klines = await async_retry_with_backoff(
                fetch,
                max_retries=config.REST_MAX_RETRIES,
                base_delay=config.REST_RETRY_BACKOFF_BASE
            )
            
            # Store klines
            for kline in klines:
                candle = self._parse_kline(kline)
                self.candles[symbol][timeframe].append(candle)
            
            logger.debug(
                f"Loaded {len(klines)} historical candles for {symbol} {timeframe}"
            )
            
        except Exception as e:
            logger.error(
                f"Failed to fetch historical data for {symbol} {timeframe}: {e}"
            )
    
    def _parse_kline(self, kline) -> Dict:
        """Parse kline data to standardized format"""
        return {
            'timestamp': kline[0],
            'open': kline[1],
            'high': kline[2],
            'low': kline[3],
            'close': kline[4],
            'volume': kline[5],
            'close_time': kline[6],
            'is_closed': True  # Historical data is always closed
        }
    
    async def _start_websocket_connections(self, symbols: List[str]):
        """Start WebSocket connections with sharding"""
        logger.info("Starting WebSocket connections with sharding...")
        
        # Create stream names for all symbols and timeframes
        streams = []
        for symbol in symbols:
            for timeframe in config.TIMEFRAMES:
                stream = f"{symbol.lower()}@kline_{timeframe}"
                streams.append(stream)
        
        # Shard streams across multiple connections
        stream_shards = list(chunks(streams, config.WS_MAX_STREAMS_PER_CONN))
        
        logger.info(
            f"Creating {len(stream_shards)} WebSocket connections "
            f"for {len(streams)} streams"
        )
        
        # Start a WebSocket connection for each shard
        for i, shard_streams in enumerate(stream_shards):
            task = asyncio.create_task(
                self._websocket_connection(i, shard_streams)
            )
            self.ws_tasks.append(task)
        
        # Update subscribed symbols
        self.subscribed_symbols = set(symbols)
    
    async def _websocket_connection(self, shard_id: int, streams: List[str]):
        """Maintain a WebSocket connection for a shard of streams"""
        
        while True:
            try:
                # Build WebSocket URL
                stream_names = '/'.join(streams)
                ws_url = f"{config.BINANCE_FUTURES_WS_BASE}/stream?streams={stream_names}"
                
                logger.info(
                    f"Shard {shard_id}: Connecting to WebSocket with {len(streams)} streams"
                )
                
                async with websockets.connect(ws_url, ping_interval=config.WS_PING_INTERVAL) as ws:
                    logger.info(f"Shard {shard_id}: WebSocket connected")
                    
                    async for message in ws:
                        try:
                            data = json.loads(message)
                            
                            if 'data' in data:
                                await self._handle_kline_message(data['data'])
                        
                        except json.JSONDecodeError as e:
                            logger.warning(f"Shard {shard_id}: Invalid JSON: {e}")
                        
                        except Exception as e:
                            logger.error(
                                f"Shard {shard_id}: Error processing message: {e}",
                                exc_info=True
                            )
            
            except websockets.exceptions.ConnectionClosed:
                logger.warning(f"Shard {shard_id}: Connection closed, reconnecting...")
            
            except Exception as e:
                logger.error(
                    f"Shard {shard_id}: WebSocket error: {e}",
                    exc_info=True
                )
            
            # Wait before reconnecting
            await asyncio.sleep(config.WS_RECONNECT_DELAY)
    
    async def _handle_kline_message(self, data: Dict):
        """Handle incoming kline WebSocket message"""
        
        if data.get('e') != 'kline':
            return
        
        kline_data = data.get('k', {})
        symbol = kline_data.get('s')
        interval = kline_data.get('i')
        is_closed = kline_data.get('x', False)
        
        # Only process closed candles
        if not is_closed:
            return
        
        candle = {
            'timestamp': kline_data['t'],
            'open': kline_data['o'],
            'high': kline_data['h'],
            'low': kline_data['l'],
            'close': kline_data['c'],
            'volume': kline_data['v'],
            'close_time': kline_data['T'],
            'is_closed': True
        }
        
        # Store candle
        async with self._lock:
            self.candles[symbol][interval].append(candle)
        
        # Signal new candle event
        event_key = f"{symbol}_{interval}"
        if event_key not in self.new_candle_events:
            self.new_candle_events[event_key] = asyncio.Event()
        
        self.new_candle_events[event_key].set()
        
        logger.debug(f"New closed candle: {symbol} {interval}")
    
    async def update_subscriptions(self, new_symbols: List[str]):
        """Update WebSocket subscriptions when symbols change"""
        new_symbols_set = set(new_symbols)
        
        # Check if update is needed
        if new_symbols_set == self.subscribed_symbols:
            return
        
        logger.info("Updating WebSocket subscriptions...")
        
        # Cancel existing WebSocket tasks
        for task in self.ws_tasks:
            task.cancel()
        
        await asyncio.gather(*self.ws_tasks, return_exceptions=True)
        self.ws_tasks.clear()
        
        # Warmup new symbols
        new_added = new_symbols_set - self.subscribed_symbols
        if new_added:
            await self._warmup_historical_data(list(new_added))
        
        # Start new WebSocket connections
        await self._start_websocket_connections(new_symbols)
        
        logger.info("WebSocket subscriptions updated")
    
    def get_candles(
        self,
        symbol: str,
        timeframe: str,
        count: Optional[int] = None
    ) -> deque:
        """Get candles for a symbol and timeframe"""
        
        if symbol not in self.candles:
            return deque(maxlen=config.MAX_CANDLES_STORED)
        
        candles = self.candles[symbol].get(timeframe, deque(maxlen=config.MAX_CANDLES_STORED))
        
        if count:
            # Return last N candles
            return deque(list(candles)[-count:], maxlen=config.MAX_CANDLES_STORED)
        
        return candles
    
    def has_sufficient_data(
        self,
        symbol: str,
        timeframe: str,
        min_candles: int = 50
    ) -> bool:
        """Check if we have sufficient data for analysis"""
        candles = self.get_candles(symbol, timeframe)
        return len(candles) >= min_candles
    
    async def wait_for_new_candle(self, symbol: str, timeframe: str, timeout: float = 3600):
        """Wait for a new closed candle"""
        event_key = f"{symbol}_{timeframe}"
        
        if event_key not in self.new_candle_events:
            self.new_candle_events[event_key] = asyncio.Event()
        
        event = self.new_candle_events[event_key]
        event.clear()
        
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for new candle: {symbol} {timeframe}")
    
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up data engine...")
        
        # Cancel all WebSocket tasks
        for task in self.ws_tasks:
            task.cancel()
        
        await asyncio.gather(*self.ws_tasks, return_exceptions=True)
        
        logger.info("Data engine cleanup complete")
