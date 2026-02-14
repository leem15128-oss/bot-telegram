"""
Binance WebSocket handler for real-time kline data.
Manages WebSocket connections for multiple symbols and timeframes.
"""

import json
import logging
import asyncio
import websockets
from typing import Dict, Callable, List
from datetime import datetime
import bot.config as config

logger = logging.getLogger(__name__)


class BinanceWebSocketHandler:
    """
    Handles Binance WebSocket connections for kline (candlestick) data.
    Supports multiple symbols and timeframes with automatic reconnection.
    """
    
    def __init__(self, symbols: List[str], timeframes: List[str], 
                 on_kline_callback: Callable):
        """
        Initialize WebSocket handler.
        
        Args:
            symbols: List of symbols to monitor (e.g., ["BTCUSDT", "ETHUSDT"])
            timeframes: List of timeframes (e.g., ["30m", "1h", "4h"])
            on_kline_callback: Callback function(symbol, timeframe, kline_data)
        """
        self.symbols = [s.lower() for s in symbols]
        self.timeframes = self._convert_timeframes(timeframes)
        self.on_kline = on_kline_callback
        
        self.ws = None
        self.running = False
        self.reconnect_attempts = 0
        
        logger.info(f"WebSocket handler initialized for {len(symbols)} symbols, "
                   f"{len(timeframes)} timeframes")
    
    def _convert_timeframes(self, timeframes: List[str]) -> List[str]:
        """
        Convert timeframe notation to Binance format.
        
        Args:
            timeframes: List like ["30m", "1h", "4h"]
        
        Returns:
            List in Binance format
        """
        # Binance uses: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, etc.
        # Our format already matches
        return timeframes
    
    def _build_stream_names(self) -> List[str]:
        """
        Build stream names for all symbol/timeframe combinations.
        
        Returns:
            List of stream names like "btcusdt@kline_30m"
        """
        streams = []
        for symbol in self.symbols:
            for timeframe in self.timeframes:
                stream = f"{symbol}@kline_{timeframe}"
                streams.append(stream)
        
        logger.debug(f"Built {len(streams)} stream names")
        return streams
    
    def _get_websocket_url(self) -> str:
        """
        Get Binance WebSocket URL for combined streams.
        
        Returns:
            WebSocket URL
        """
        streams = self._build_stream_names()
        # Use combined stream endpoint
        stream_path = '/'.join(streams)
        url = f"wss://stream.binance.com:9443/stream?streams={stream_path}"
        return url
    
    async def start(self):
        """
        Start WebSocket connection and begin receiving data.
        """
        self.running = True
        
        while self.running:
            try:
                url = self._get_websocket_url()
                logger.info(f"Connecting to Binance WebSocket...")
                
                async with websockets.connect(url, ping_interval=20, ping_timeout=10) as ws:
                    self.ws = ws
                    self.reconnect_attempts = 0
                    logger.info("WebSocket connected successfully")
                    
                    # Receive messages
                    async for message in ws:
                        if not self.running:
                            break
                        
                        await self._handle_message(message)
            
            except websockets.exceptions.WebSocketException as e:
                logger.error(f"WebSocket error: {e}")
                await self._handle_reconnect()
            
            except Exception as e:
                logger.error(f"Unexpected error in WebSocket: {e}", exc_info=True)
                await self._handle_reconnect()
        
        logger.info("WebSocket handler stopped")
    
    async def _handle_reconnect(self):
        """Handle reconnection logic."""
        self.reconnect_attempts += 1
        
        if self.reconnect_attempts > config.WEBSOCKET_MAX_RECONNECT_ATTEMPTS:
            logger.error(f"Max reconnect attempts ({config.WEBSOCKET_MAX_RECONNECT_ATTEMPTS}) "
                        f"reached, stopping WebSocket")
            self.running = False
            return
        
        delay = config.WEBSOCKET_RECONNECT_DELAY * self.reconnect_attempts
        logger.warning(f"Reconnecting in {delay}s (attempt {self.reconnect_attempts}/"
                      f"{config.WEBSOCKET_MAX_RECONNECT_ATTEMPTS})")
        await asyncio.sleep(delay)
    
    async def _handle_message(self, message: str):
        """
        Handle incoming WebSocket message.
        
        Args:
            message: Raw WebSocket message
        """
        try:
            data = json.loads(message)
            
            # Binance combined stream format: {"stream": "...", "data": {...}}
            if 'stream' not in data or 'data' not in data:
                return
            
            stream_name = data['stream']
            kline_data = data['data']
            
            # Extract symbol and timeframe from stream name
            # Format: btcusdt@kline_30m
            parts = stream_name.split('@')
            if len(parts) != 2:
                return
            
            symbol = parts[0].upper()
            timeframe = parts[1].replace('kline_', '')
            
            # Parse kline data
            await self._process_kline(symbol, timeframe, kline_data)
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse WebSocket message: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
    
    async def _process_kline(self, symbol: str, timeframe: str, data: Dict):
        """
        Process kline data and invoke callback.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            data: Kline data from Binance
        """
        try:
            # Binance kline data structure
            kline = data.get('k', {})
            
            if not kline:
                return
            
            # Extract kline fields
            open_time = kline.get('t', 0)  # Open time (ms)
            close_time = kline.get('T', 0)  # Close time (ms)
            open_price = float(kline.get('o', 0))
            high = float(kline.get('h', 0))
            low = float(kline.get('l', 0))
            close = float(kline.get('c', 0))
            volume = float(kline.get('v', 0))
            is_closed = kline.get('x', False)
            
            # Log only closed candles at INFO level
            if is_closed:
                logger.info(f"Closed candle: {symbol} {timeframe} @ {close:.4f}")
            else:
                logger.debug(f"Forming candle: {symbol} {timeframe} @ {close:.4f}")
            
            # Invoke callback
            await self.on_kline(
                symbol=symbol,
                timeframe=timeframe,
                open_price=open_price,
                high=high,
                low=low,
                close=close,
                volume=volume,
                open_time=open_time,
                close_time=close_time,
                is_closed=is_closed
            )
        
        except Exception as e:
            logger.error(f"Error processing kline for {symbol} {timeframe}: {e}", 
                        exc_info=True)
    
    async def stop(self):
        """Stop WebSocket connection."""
        logger.info("Stopping WebSocket handler...")
        self.running = False
        
        if self.ws:
            await self.ws.close()
            self.ws = None


async def fetch_historical_klines(symbol: str, timeframe: str, limit: int = 500) -> List[Dict]:
    """
    Fetch historical kline data from Binance REST API.
    
    Args:
        symbol: Trading symbol
        timeframe: Timeframe (e.g., "30m", "1h", "4h")
        limit: Number of candles to fetch (max 1000)
    
    Returns:
        List of kline dictionaries
    """
    import aiohttp
    
    url = "https://api.binance.com/api/v3/klines"
    params = {
        'symbol': symbol.upper(),
        'interval': timeframe,
        'limit': min(limit, 1000)
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                
                klines = []
                for k in data:
                    klines.append({
                        'open_time': k[0],
                        'open': float(k[1]),
                        'high': float(k[2]),
                        'low': float(k[3]),
                        'close': float(k[4]),
                        'volume': float(k[5]),
                        'close_time': k[6],
                    })
                
                logger.info(f"Fetched {len(klines)} historical candles for {symbol} {timeframe}")
                return klines
    
    except Exception as e:
        logger.error(f"Failed to fetch historical klines for {symbol} {timeframe}: {e}")
        return []
