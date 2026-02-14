"""
Main bot entry point.
Orchestrates all components for multi-timeframe signal generation.
"""

import asyncio
import logging
import signal
import sys
from typing import Dict
from bot.data_manager import DataManager
from bot.strategy import TradingStrategy
from bot.signal_deduplicator import SignalDeduplicator
from bot.risk_manager import RiskManager
from bot.trade_tracker import TradeTracker
from bot.telegram_notifier import TelegramNotifier
from bot.websocket_handler import BinanceWebSocketHandler, fetch_historical_klines
import bot.config as config

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)

logger = logging.getLogger(__name__)


class TradingBot:
    """
    Main trading signal bot.
    Coordinates all components and manages the signal generation workflow.
    """
    
    def __init__(self):
        """Initialize all bot components."""
        logger.info("=" * 60)
        logger.info("Initializing Trading Signal Bot")
        logger.info("=" * 60)
        
        # Initialize components
        self.data_manager = DataManager(max_candles=config.MAX_CANDLES_IN_MEMORY)
        self.deduplicator = SignalDeduplicator(
            signal_cooldown_seconds=config.SIGNAL_COOLDOWN_SECONDS,
            global_cooldown_seconds=config.GLOBAL_SIGNAL_COOLDOWN_SECONDS,
            max_active_per_symbol=config.MAX_ACTIVE_SIGNALS_PER_SYMBOL
        )
        self.risk_manager = RiskManager(max_signals_per_day=config.MAX_SIGNALS_PER_DAY)
        self.trade_tracker = TradeTracker()
        self.telegram = TelegramNotifier()
        self.strategy = TradingStrategy(
            self.data_manager,
            self.deduplicator,
            self.risk_manager
        )
        
        # WebSocket handler (initialized later)
        self.ws_handler = None
        
        # Running flag
        self.running = False
        
        logger.info("All components initialized successfully")
        
        # Log configuration
        config_summary = config.get_config_summary()
        logger.info(f"Configuration: {config_summary}")
    
    async def on_kline_update(self, symbol: str, timeframe: str, 
                             open_price: float, high: float, low: float, 
                             close: float, volume: float,
                             open_time: int, close_time: int, is_closed: bool):
        """
        Handle kline updates from WebSocket.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            open_price, high, low, close, volume: Candle data
            open_time, close_time: Timestamps (ms)
            is_closed: Whether candle is closed
        """
        # Add candle to data manager
        self.data_manager.add_candle(
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
        
        # Analyze on every update (intrabar analysis)
        # But structure is computed from closed candles only (handled in strategy)
        if timeframe == config.PRIMARY_TIMEFRAME:
            # Only analyze on primary timeframe updates to avoid redundant checks
            signal = self.strategy.analyze_symbol(symbol, is_closed=is_closed)
            
            if signal:
                await self._handle_signal(signal)
        
        # Cleanup old window data periodically
        if is_closed and timeframe == config.PRIMARY_TIMEFRAME:
            self.deduplicator.cleanup_old_windows()
    
    async def _handle_signal(self, signal: Dict):
        """
        Handle a generated signal.
        
        Args:
            signal: Signal dictionary from strategy
        """
        symbol = signal['symbol']
        direction = signal['direction']
        setup_type = signal['setup_type']
        
        # Record signal in tracker
        signal_id = self.trade_tracker.add_signal(signal)
        signal['id'] = signal_id
        
        # Record in deduplicator
        window_start = self.data_manager.get_candle_window(symbol, config.PRIMARY_TIMEFRAME)
        self.deduplicator.record_signal(symbol, direction, setup_type, window_start)
        
        # Record in risk manager
        self.risk_manager.record_signal()
        
        # Send Telegram notification
        success = self.telegram.send_signal(signal)
        
        if success:
            logger.info(f"✅ Signal #{signal_id} sent to Telegram successfully")
        else:
            logger.warning(f"⚠️ Failed to send signal #{signal_id} to Telegram")
    
    async def load_historical_data(self):
        """Load historical candle data for all symbols and timeframes."""
        logger.info("Loading historical data...")
        
        tasks = []
        for symbol in config.SYMBOLS:
            for timeframe in config.TIMEFRAMES:
                tasks.append(self._load_symbol_history(symbol, timeframe))
        
        await asyncio.gather(*tasks)
        
        logger.info("Historical data loaded successfully")
        
        # Log data stats
        stats = self.data_manager.get_stats()
        for symbol, tf_stats in stats.items():
            logger.info(f"{symbol}: {tf_stats}")
    
    async def _load_symbol_history(self, symbol: str, timeframe: str):
        """
        Load historical data for a specific symbol/timeframe.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
        """
        klines = await fetch_historical_klines(
            symbol, 
            timeframe, 
            limit=config.MAX_CANDLES_IN_MEMORY
        )
        
        for kline in klines:
            self.data_manager.add_candle(
                symbol=symbol,
                timeframe=timeframe,
                open_price=kline['open'],
                high=kline['high'],
                low=kline['low'],
                close=kline['close'],
                volume=kline['volume'],
                open_time=kline['open_time'],
                close_time=kline['close_time'],
                is_closed=True  # Historical candles are closed
            )
    
    async def start(self):
        """Start the trading bot."""
        self.running = True
        
        logger.info("=" * 60)
        logger.info("Starting Trading Signal Bot")
        logger.info("=" * 60)
        
        # Send startup notification (if enabled)
        config_summary = config.get_config_summary()
        if config.SEND_STARTUP_MESSAGE:
            self.telegram.send_startup_message(config_summary)
        
        # Send startup stats (if enabled)
        if config.SEND_STATS_ON_STARTUP:
            stats = self.trade_tracker.get_stats()
            self.telegram.send_stats_update(stats)
        
        # Load historical data
        await self.load_historical_data()
        
        # Start WebSocket handler
        self.ws_handler = BinanceWebSocketHandler(
            symbols=config.SYMBOLS,
            timeframes=config.TIMEFRAMES,
            on_kline_callback=self.on_kline_update
        )
        
        logger.info("Starting WebSocket connection...")
        await self.ws_handler.start()
    
    async def stop(self):
        """Stop the trading bot gracefully."""
        logger.info("Stopping bot...")
        self.running = False
        
        if self.ws_handler:
            await self.ws_handler.stop()
        
        # Send final stats (if enabled)
        if config.SEND_STATS_ON_SHUTDOWN:
            stats = self.trade_tracker.get_stats()
            self.telegram.send_stats_update(stats)
        
        logger.info("Bot stopped successfully")


async def main():
    """Main entry point."""
    bot = TradingBot()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, initiating shutdown...")
        asyncio.create_task(bot.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
