"""Symbol universe manager with volume-based rotation."""
import asyncio
import logging
from typing import List, Set
from .config import config
from .binance_client import binance_client

logger = logging.getLogger(__name__)


class SymbolUniverseManager:
    """Manages the active symbol universe with rotation."""
    
    def __init__(self):
        self.fixed_symbols: Set[str] = set(config.FIXED_SYMBOLS)
        self.all_volume_symbols: List[str] = []
        self.active_symbols: Set[str] = set()
        self._rotation_index = 0
        self._last_universe_refresh = 0
        self._refresh_task: asyncio.Task = None
        self._rotation_task: asyncio.Task = None
    
    async def initialize(self):
        """Initialize the symbol universe."""
        logger.info("Initializing symbol universe")
        await self._refresh_universe()
        await self._rotate_symbols()
        
        # Start background tasks
        self._refresh_task = asyncio.create_task(self._refresh_loop())
        self._rotation_task = asyncio.create_task(self._rotation_loop())
        
        logger.info(f"Symbol universe initialized: {len(self.active_symbols)} active symbols")
    
    async def _refresh_universe(self):
        """Refresh the list of top volume symbols."""
        try:
            logger.info("Refreshing symbol universe from Binance")
            top_symbols = await binance_client.get_top_volume_symbols(
                limit=config.TOP_VOLUME_FETCH_LIMIT
            )
            
            # Filter to ensure only USDT perpetuals
            self.all_volume_symbols = [
                s for s in top_symbols 
                if s.endswith('USDT')
            ]
            
            logger.info(f"Fetched {len(self.all_volume_symbols)} top volume USDT perpetual symbols")
            
        except Exception as e:
            logger.error(f"Error refreshing symbol universe: {e}")
            # Keep existing symbols on error
    
    async def _rotate_symbols(self):
        """Rotate active symbols while keeping fixed symbols."""
        # Always include fixed symbols
        new_active = set(self.fixed_symbols)
        
        # Calculate how many extra symbols we can add
        max_extra = config.MAX_SYMBOLS_SUBSCRIBED - len(self.fixed_symbols)
        
        if max_extra > 0 and self.all_volume_symbols:
            # Get a rotating slice of volume symbols
            num_volume_symbols = len(self.all_volume_symbols)
            
            # Calculate rotation window
            for i in range(max_extra):
                idx = (self._rotation_index + i) % num_volume_symbols
                symbol = self.all_volume_symbols[idx]
                # Don't duplicate fixed symbols
                if symbol not in self.fixed_symbols:
                    new_active.add(symbol)
            
            # Move rotation index for next rotation
            self._rotation_index = (self._rotation_index + max_extra) % num_volume_symbols
        
        old_active = self.active_symbols
        self.active_symbols = new_active
        
        # Log changes
        added = new_active - old_active
        removed = old_active - new_active
        
        if added:
            logger.info(f"Added symbols: {', '.join(sorted(added)[:10])}{'...' if len(added) > 10 else ''}")
        if removed:
            logger.info(f"Removed symbols: {', '.join(sorted(removed)[:10])}{'...' if len(removed) > 10 else ''}")
        
        logger.info(f"Active symbols: {len(self.active_symbols)} (fixed: {len(self.fixed_symbols)}, rotated: {len(self.active_symbols) - len(self.fixed_symbols)})")
    
    async def _refresh_loop(self):
        """Background task to refresh universe periodically."""
        while True:
            try:
                await asyncio.sleep(config.UNIVERSE_REFRESH_SECONDS)
                await self._refresh_universe()
                logger.info("Universe refresh completed")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in refresh loop: {e}")
    
    async def _rotation_loop(self):
        """Background task to rotate symbols periodically."""
        while True:
            try:
                await asyncio.sleep(config.ROTATION_SLOT_SECONDS)
                await self._rotate_symbols()
                logger.info("Symbol rotation completed")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in rotation loop: {e}")
    
    def get_active_symbols(self) -> List[str]:
        """Get current list of active symbols."""
        return sorted(list(self.active_symbols))
    
    async def stop(self):
        """Stop background tasks."""
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
        
        if self._rotation_task:
            self._rotation_task.cancel()
            try:
                await self._rotation_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Symbol universe manager stopped")


# Global symbol universe manager
symbol_universe = SymbolUniverseManager()
