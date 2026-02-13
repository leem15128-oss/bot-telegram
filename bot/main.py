"""Main bot orchestration module."""
import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import Dict, Any

from .config import config
from .database import db
from .binance_client import binance_client
from .websocket_manager import ws_manager
from .symbol_universe import symbol_universe
from .market_data import market_data
from .scoring_engine import scoring_engine
from .risk_manager import risk_manager
from .memory_engine import adaptive_memory
from .telegram_notifier import telegram_notifier

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class TradingBot:
    """Main trading bot orchestrator."""
    
    def __init__(self):
        self.running = False
        self._scan_task: asyncio.Task = None
        self._scan_semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_SCANS)
    
    async def initialize(self):
        """Initialize all bot components."""
        logger.info("=" * 60)
        logger.info("Initializing Trading Bot")
        logger.info("=" * 60)
        
        # Initialize database
        await db.connect()
        
        # Initialize adaptive memory
        await adaptive_memory.initialize()
        
        # Initialize symbol universe
        await symbol_universe.initialize()
        
        # Get initial active symbols
        active_symbols = symbol_universe.get_active_symbols()
        logger.info(f"Active symbols: {len(active_symbols)}")
        
        # Warmup market data
        await market_data.warmup(active_symbols, config.TIMEFRAMES)
        
        # Setup WebSocket callback
        ws_manager.set_callback(self._handle_websocket_message)
        
        # Subscribe to WebSocket streams
        await ws_manager.subscribe(active_symbols, config.TIMEFRAMES)
        
        # Start periodic scanner
        self._scan_task = asyncio.create_task(self._periodic_scan())
        
        logger.info("Trading Bot initialized successfully")
        await telegram_notifier.send_alert("🤖 Bot khởi động thành công!")
    
    async def _handle_websocket_message(self, message: Dict[str, Any]):
        """Handle incoming WebSocket messages."""
        try:
            # Extract stream info
            stream = message.get('stream', '')
            data = message.get('data', {})
            
            if 'kline' in stream:
                # Parse kline data
                symbol = data.get('s', '').upper()
                kline = data.get('k', {})
                interval = kline.get('i', '')
                is_closed = kline.get('x', False)
                
                # Only process closed candles
                if is_closed:
                    # Update market data
                    candle = await market_data.update_candle(symbol, interval, data)
                    
                    if candle:
                        # Trigger analysis for this symbol/timeframe
                        asyncio.create_task(self._analyze_and_signal(symbol, interval))
        
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
    
    async def _analyze_and_signal(self, symbol: str, timeframe: str):
        """Analyze a symbol and generate signal if conditions are met."""
        async with self._scan_semaphore:
            try:
                # Check if we have sufficient data
                if not market_data.has_sufficient_data(symbol, timeframe):
                    return
                
                # Generate signal
                signal = scoring_engine.analyze_symbol(symbol, timeframe)
                
                if not signal:
                    return
                
                # Check if model is enabled
                if not risk_manager.is_model_enabled(signal.model_type):
                    logger.debug(f"Model {signal.model_type} disabled, skipping signal")
                    return
                
                # Check memory engine
                can_trade, reason = await adaptive_memory.can_trade(symbol, signal.model_type)
                if not can_trade:
                    logger.info(f"Memory engine blocked {symbol}: {reason}")
                    return
                
                # Get symbol-specific score adjustment
                score_adjustment = adaptive_memory.get_symbol_score_adjustment(symbol)
                
                # Validate score
                if not risk_manager.validate_signal_score(signal.score, symbol, score_adjustment):
                    logger.debug(f"Signal score {signal.score} below threshold for {symbol}")
                    return
                
                # Check daily limit
                if not risk_manager.can_send_signal():
                    logger.info("Daily signal limit reached")
                    return
                
                # Signal passed all checks - save and send
                signal_data = signal.to_dict()
                signal_data['timestamp'] = datetime.utcnow().isoformat()
                signal_data['status'] = 'active'
                
                signal_id = await db.save_signal(signal_data)
                
                # Increment signal counter
                risk_manager.increment_signal_counter()
                
                # Send notification
                await telegram_notifier.send_signal(signal_data)
                
                logger.info(f"✅ Signal generated: {symbol} {timeframe} {signal.signal_type} "
                          f"(score: {signal.score:.1f})")
            
            except Exception as e:
                logger.error(f"Error in analyze_and_signal for {symbol} {timeframe}: {e}")
    
    async def _periodic_scan(self):
        """Periodically scan all active symbols."""
        while self.running:
            try:
                # Wait for warmup to complete
                if not market_data.is_warmup_complete():
                    await asyncio.sleep(10)
                    continue
                
                active_symbols = symbol_universe.get_active_symbols()
                
                # Scan each symbol/timeframe combination
                tasks = []
                for symbol in active_symbols:
                    for timeframe in config.TIMEFRAMES:
                        task = self._analyze_and_signal(symbol, timeframe)
                        tasks.append(task)
                
                # Execute scans (semaphore will limit concurrency)
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Wait before next scan (5 minutes)
                await asyncio.sleep(300)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic scan: {e}")
                await asyncio.sleep(60)
    
    async def start(self):
        """Start the trading bot."""
        self.running = True
        await self.initialize()
        
        logger.info("Trading Bot started - monitoring markets...")
        
        # Keep running
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the trading bot."""
        logger.info("Shutting down Trading Bot...")
        
        self.running = False
        
        # Cancel periodic scan
        if self._scan_task:
            self._scan_task.cancel()
            try:
                await self._scan_task
            except asyncio.CancelledError:
                pass
        
        # Stop components
        await ws_manager.stop_all()
        await symbol_universe.stop()
        await binance_client.close()
        await db.close()
        
        logger.info("Trading Bot stopped")
        await telegram_notifier.send_alert("🛑 Bot đã dừng")


async def main():
    """Main entry point."""
    bot = TradingBot()
    
    # Handle shutdown signals
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        asyncio.create_task(bot.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    await bot.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot terminated by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
