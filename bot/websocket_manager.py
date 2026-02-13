"""WebSocket manager with connection sharding and auto-reconnect."""
import asyncio
import json
import logging
from typing import Dict, List, Callable, Optional
import websockets
from .config import config

logger = logging.getLogger(__name__)


class WebSocketConnection:
    """Individual WebSocket connection handler."""
    
    def __init__(self, conn_id: int, streams: List[str], callback: Callable):
        self.conn_id = conn_id
        self.streams = streams
        self.callback = callback
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def connect(self):
        """Connect to Binance WebSocket."""
        base_url = "wss://fstream.binance.com"
        if config.BINANCE_TESTNET:
            base_url = "wss://stream.binancefuture.com"
        
        stream_names = "/".join(self.streams)
        url = f"{base_url}/stream?streams={stream_names}"
        
        try:
            self.ws = await websockets.connect(url, ping_interval=20, ping_timeout=10)
            logger.info(f"WebSocket {self.conn_id} connected with {len(self.streams)} streams")
            return True
        except Exception as e:
            logger.error(f"WebSocket {self.conn_id} connection failed: {e}")
            return False
    
    async def start(self):
        """Start the WebSocket connection with auto-reconnect."""
        self._running = True
        self._task = asyncio.create_task(self._run())
    
    async def _run(self):
        """Run the WebSocket connection with reconnection logic."""
        reconnect_delay = 1
        
        while self._running:
            try:
                if not self.ws or self.ws.closed:
                    success = await self.connect()
                    if not success:
                        await asyncio.sleep(reconnect_delay)
                        reconnect_delay = min(reconnect_delay * 2, 60)
                        continue
                    reconnect_delay = 1
                
                async for message in self.ws:
                    if not self._running:
                        break
                    
                    try:
                        data = json.loads(message)
                        await self.callback(data)
                    except Exception as e:
                        logger.error(f"Error processing WebSocket message: {e}")
            
            except websockets.ConnectionClosed:
                logger.warning(f"WebSocket {self.conn_id} connection closed, reconnecting...")
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 60)
            
            except Exception as e:
                logger.error(f"WebSocket {self.conn_id} error: {e}")
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 60)
    
    async def stop(self):
        """Stop the WebSocket connection."""
        self._running = False
        if self.ws and not self.ws.closed:
            await self.ws.close()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass


class WebSocketManager:
    """Manages multiple WebSocket connections with sharding."""
    
    def __init__(self, max_streams_per_conn: int = None):
        self.max_streams_per_conn = max_streams_per_conn or config.WS_MAX_STREAMS_PER_CONN
        self.connections: List[WebSocketConnection] = []
        self._callback: Optional[Callable] = None
    
    def set_callback(self, callback: Callable):
        """Set the callback for WebSocket messages."""
        self._callback = callback
    
    async def subscribe(self, symbols: List[str], timeframes: List[str]):
        """Subscribe to kline streams for given symbols and timeframes."""
        if not self._callback:
            raise ValueError("Callback must be set before subscribing")
        
        # Build stream names
        streams = []
        for symbol in symbols:
            for tf in timeframes:
                stream_name = f"{symbol.lower()}@kline_{tf}"
                streams.append(stream_name)
        
        # Shard streams across multiple connections
        shards = []
        for i in range(0, len(streams), self.max_streams_per_conn):
            shard = streams[i:i + self.max_streams_per_conn]
            shards.append(shard)
        
        logger.info(f"Creating {len(shards)} WebSocket connections for {len(streams)} streams")
        
        # Create connections
        for i, shard in enumerate(shards):
            conn = WebSocketConnection(i, shard, self._callback)
            self.connections.append(conn)
            await conn.start()
            # Small delay between connections to avoid overwhelming the server
            await asyncio.sleep(0.5)
    
    async def resubscribe(self, symbols: List[str], timeframes: List[str]):
        """Resubscribe with new symbol list (for rotation)."""
        logger.info(f"Resubscribing to {len(symbols)} symbols")
        
        # Stop existing connections
        await self.stop_all()
        
        # Small delay before reconnecting
        await asyncio.sleep(2)
        
        # Subscribe with new symbols
        await self.subscribe(symbols, timeframes)
    
    async def stop_all(self):
        """Stop all WebSocket connections."""
        logger.info("Stopping all WebSocket connections")
        tasks = [conn.stop() for conn in self.connections]
        await asyncio.gather(*tasks, return_exceptions=True)
        self.connections.clear()


# Global WebSocket manager instance
ws_manager = WebSocketManager()
