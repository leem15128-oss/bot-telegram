"""
Symbol Engine - Manages symbol selection, rotation, and universe refresh
"""
import asyncio
import logging
import time
from typing import List, Set
import aiohttp
from collections import defaultdict

from . import config
from .utils import async_retry_with_backoff, RateLimiter, TTLCache

logger = logging.getLogger(__name__)


class SymbolEngine:
    """Manages symbol universe, rotation, and subscription limits"""
    
    def __init__(self):
        self.fixed_symbols: Set[str] = set(config.FIXED_SYMBOLS)
        self.top_volume_symbols: List[str] = []
        self.active_symbols: Set[str] = set()
        self.all_candidates: List[str] = []
        
        self.rate_limiter = RateLimiter(config.REST_RATE_LIMIT_DELAY)
        self.cache = TTLCache(config.REST_CACHE_TTL)
        
        self.last_universe_refresh = 0
        self.last_rotation = 0
        self.rotation_index = 0
    
    async def initialize(self):
        """Initialize symbol universe"""
        logger.info("Initializing symbol engine...")
        await self.refresh_universe()
        self.rotate_symbols()
        logger.info(f"Symbol engine initialized with {len(self.active_symbols)} active symbols")
    
    async def refresh_universe(self):
        """Refresh the universe of tradeable symbols"""
        logger.info("Refreshing symbol universe...")
        
        try:
            # Get top volume symbols from Binance Futures
            top_symbols = await self._fetch_top_volume_symbols()
            
            # Filter to USDT perpetuals only
            usdt_symbols = [
                s for s in top_symbols 
                if s.endswith('USDT')
            ]
            
            # Combine fixed + top volume, remove duplicates
            all_symbols = list(self.fixed_symbols) + usdt_symbols
            self.all_candidates = list(dict.fromkeys(all_symbols))  # Remove duplicates while preserving order
            
            # Store top 300 candidates
            self.all_candidates = self.all_candidates[:config.TOP_VOLUME_COUNT]
            
            self.last_universe_refresh = time.time()
            
            logger.info(
                f"Universe refreshed: {len(self.all_candidates)} total candidates "
                f"({len(self.fixed_symbols)} fixed, {len(usdt_symbols)} top volume)"
            )
            
        except Exception as e:
            logger.error(f"Failed to refresh universe: {e}", exc_info=True)
            # If refresh fails, keep existing candidates
    
    async def _fetch_top_volume_symbols(self) -> List[str]:
        """Fetch top volume symbols from Binance Futures"""
        
        # Check cache first
        cached = await self.cache.get("top_volume_symbols")
        if cached:
            logger.debug("Using cached top volume symbols")
            return cached
        
        async def fetch():
            await self.rate_limiter.acquire()
            
            url = f"{config.BINANCE_FUTURES_REST_BASE}/fapi/v1/ticker/24hr"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    data = await response.json()
            
            # Sort by quote volume (USD volume for futures)
            sorted_tickers = sorted(
                data,
                key=lambda x: float(x.get('quoteVolume', 0)),
                reverse=True
            )
            
            # Extract symbols
            symbols = [ticker['symbol'] for ticker in sorted_tickers]
            
            return symbols
        
        try:
            symbols = await async_retry_with_backoff(
                fetch,
                max_retries=config.REST_MAX_RETRIES,
                base_delay=config.REST_RETRY_BACKOFF_BASE
            )
            
            # Cache the result
            await self.cache.set("top_volume_symbols", symbols)
            
            return symbols
            
        except Exception as e:
            logger.error(f"Failed to fetch top volume symbols: {e}")
            return []
    
    def rotate_symbols(self):
        """
        Rotate active symbols while keeping fixed symbols always subscribed
        """
        # Always include fixed symbols
        new_active = set(self.fixed_symbols)
        
        # Calculate how many additional symbols we can add
        slots_available = config.MAX_SYMBOLS_SUBSCRIBED - len(new_active)
        
        if slots_available <= 0:
            logger.warning(
                f"Fixed symbols ({len(self.fixed_symbols)}) exceed MAX_SYMBOLS_SUBSCRIBED "
                f"({config.MAX_SYMBOLS_SUBSCRIBED})"
            )
            self.active_symbols = new_active
            return
        
        # Get additional symbols from candidates (excluding fixed)
        additional_candidates = [
            s for s in self.all_candidates 
            if s not in self.fixed_symbols
        ]
        
        if not additional_candidates:
            self.active_symbols = new_active
            return
        
        # Rotate through candidates
        start_idx = self.rotation_index % len(additional_candidates)
        
        # Select next batch
        selected_count = 0
        idx = start_idx
        
        while selected_count < slots_available:
            symbol = additional_candidates[idx % len(additional_candidates)]
            new_active.add(symbol)
            selected_count += 1
            idx += 1
            
            # Prevent infinite loop
            if idx - start_idx >= len(additional_candidates):
                break
        
        # Update rotation index for next rotation
        self.rotation_index = idx
        
        # Calculate what changed
        added = new_active - self.active_symbols
        removed = self.active_symbols - new_active
        
        if added or removed:
            logger.info(
                f"Symbol rotation: +{len(added)} -{len(removed)} "
                f"(Total: {len(new_active)})"
            )
            if added:
                logger.debug(f"Added: {sorted(list(added))[:10]}...")
            if removed:
                logger.debug(f"Removed: {sorted(list(removed))[:10]}...")
        
        self.active_symbols = new_active
        self.last_rotation = time.time()
    
    def should_refresh_universe(self) -> bool:
        """Check if universe should be refreshed"""
        return (
            time.time() - self.last_universe_refresh >= 
            config.UNIVERSE_REFRESH_INTERVAL
        )
    
    def should_rotate_symbols(self) -> bool:
        """Check if symbols should be rotated"""
        return (
            time.time() - self.last_rotation >= 
            config.SYMBOL_ROTATION_INTERVAL
        )
    
    def get_active_symbols(self) -> List[str]:
        """Get current active symbols"""
        return sorted(list(self.active_symbols))
    
    def is_fixed_symbol(self, symbol: str) -> bool:
        """Check if symbol is in fixed list"""
        return symbol in self.fixed_symbols
    
    async def maintenance_loop(self):
        """Background task for universe refresh and symbol rotation"""
        logger.info("Starting symbol maintenance loop...")
        
        while True:
            try:
                # Check if universe refresh is needed
                if self.should_refresh_universe():
                    logger.info("Triggering universe refresh...")
                    await self.refresh_universe()
                    # After refresh, do a rotation to update active symbols
                    self.rotate_symbols()
                
                # Check if rotation is needed
                elif self.should_rotate_symbols():
                    logger.info("Triggering symbol rotation...")
                    self.rotate_symbols()
                
                # Sleep for a short interval before checking again
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in symbol maintenance loop: {e}", exc_info=True)
                await asyncio.sleep(60)
