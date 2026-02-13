"""Binance Futures API client with throttling and caching."""
import asyncio
import time
import hmac
import hashlib
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode
import aiohttp
from .config import config

logger = logging.getLogger(__name__)


class BinanceClient:
    """Async Binance Futures API client with rate limiting and caching."""
    
    def __init__(self):
        self.base_url = config.BINANCE_BASE_URL
        self.api_key = config.BINANCE_API_KEY
        self.api_secret = config.BINANCE_API_SECRET
        
        # Rate limiting
        self._rate_limit_window = 60  # 1 minute
        self._max_requests_per_window = config.REST_RATE_LIMIT_PER_MINUTE
        self._request_times: List[float] = []
        self._rate_limit_lock = asyncio.Lock()
        
        # Caching
        self._exchange_info_cache: Optional[Dict[str, Any]] = None
        self._exchange_info_cache_time: float = 0
        self._ticker_cache: Dict[str, tuple] = {}  # symbol -> (data, timestamp)
        
        # Session
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _wait_for_rate_limit(self):
        """Wait if necessary to respect rate limits."""
        async with self._rate_limit_lock:
            now = time.time()
            # Remove old requests outside the window
            self._request_times = [t for t in self._request_times if now - t < self._rate_limit_window]
            
            if len(self._request_times) >= self._max_requests_per_window:
                # Need to wait
                oldest = self._request_times[0]
                wait_time = self._rate_limit_window - (now - oldest)
                if wait_time > 0:
                    logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                    # Re-clean after waiting
                    now = time.time()
                    self._request_times = [t for t in self._request_times if now - t < self._rate_limit_window]
            
            self._request_times.append(time.time())
    
    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """Generate HMAC SHA256 signature."""
        query_string = urlencode(params)
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    async def _request(self, method: str, endpoint: str, params: Dict[str, Any] = None, 
                      signed: bool = False, retry_count: int = 0) -> Dict[str, Any]:
        """Make HTTP request with retry logic."""
        if params is None:
            params = {}
        
        # Add signature for signed endpoints
        if signed:
            params['timestamp'] = int(time.time() * 1000)
            params['signature'] = self._generate_signature(params)
        
        url = f"{self.base_url}{endpoint}"
        headers = {'X-MBX-APIKEY': self.api_key} if self.api_key else {}
        
        await self._wait_for_rate_limit()
        
        session = await self._get_session()
        
        try:
            async with session.request(method, url, params=params, headers=headers, timeout=10) as response:
                data = await response.json()
                
                if response.status == 200:
                    return data
                elif response.status == 429:  # Rate limit
                    retry_after = int(response.headers.get('Retry-After', 5))
                    logger.warning(f"Rate limited, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    return await self._request(method, endpoint, params, signed, retry_count)
                else:
                    logger.error(f"API error {response.status}: {data}")
                    raise Exception(f"API error: {data}")
        
        except asyncio.TimeoutError:
            if retry_count < config.REST_RETRY_MAX_ATTEMPTS:
                delay = config.REST_RETRY_BASE_DELAY * (2 ** retry_count)
                jitter = delay * 0.1 * (time.time() % 1)  # Add jitter
                total_delay = delay + jitter
                logger.warning(f"Request timeout, retrying in {total_delay:.2f}s (attempt {retry_count + 1})")
                await asyncio.sleep(total_delay)
                return await self._request(method, endpoint, params, signed, retry_count + 1)
            else:
                raise
        
        except Exception as e:
            if retry_count < config.REST_RETRY_MAX_ATTEMPTS:
                delay = config.REST_RETRY_BASE_DELAY * (2 ** retry_count)
                jitter = delay * 0.1 * (time.time() % 1)
                total_delay = delay + jitter
                logger.warning(f"Request error: {e}, retrying in {total_delay:.2f}s (attempt {retry_count + 1})")
                await asyncio.sleep(total_delay)
                return await self._request(method, endpoint, params, signed, retry_count + 1)
            else:
                raise
    
    async def get_exchange_info(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Get exchange info with caching."""
        now = time.time()
        cache_age = now - self._exchange_info_cache_time
        
        if not force_refresh and self._exchange_info_cache and cache_age < config.CACHE_TTL_EXCHANGE_INFO:
            logger.debug(f"Using cached exchange info (age: {cache_age:.0f}s)")
            return self._exchange_info_cache
        
        logger.info("Fetching fresh exchange info")
        data = await self._request('GET', '/fapi/v1/exchangeInfo')
        self._exchange_info_cache = data
        self._exchange_info_cache_time = now
        return data
    
    async def get_top_volume_symbols(self, limit: int = None) -> List[str]:
        """Get top volume USDT perpetual symbols."""
        limit = limit or config.TOP_VOLUME_FETCH_LIMIT
        
        # Get 24h ticker data
        data = await self._request('GET', '/fapi/v1/ticker/24hr')
        
        # Filter for USDT perpetuals and sort by volume
        usdt_perps = [
            item for item in data
            if item['symbol'].endswith('USDT') and float(item['quoteVolume']) > 0
        ]
        
        # Sort by quote volume (descending)
        usdt_perps.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
        
        # Return top symbols
        return [item['symbol'] for item in usdt_perps[:limit]]
    
    async def get_klines(self, symbol: str, interval: str, limit: int = 500) -> List[List]:
        """Get historical klines."""
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        return await self._request('GET', '/fapi/v1/klines', params)
    
    async def get_symbol_price(self, symbol: str, use_cache: bool = True) -> float:
        """Get current symbol price with optional caching."""
        if use_cache:
            now = time.time()
            if symbol in self._ticker_cache:
                price, timestamp = self._ticker_cache[symbol]
                if now - timestamp < config.CACHE_TTL_TICKER:
                    return price
        
        data = await self._request('GET', '/fapi/v1/ticker/price', {'symbol': symbol})
        price = float(data['price'])
        
        if use_cache:
            self._ticker_cache[symbol] = (price, time.time())
        
        return price


# Global client instance
binance_client = BinanceClient()
