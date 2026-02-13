"""
Main Bot Orchestrator - Institutional Price Action Swing Bot v2
"""
import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

from . import config
from .symbol_engine import SymbolEngine
from .data_engine import DataEngine
from .structure_engine import StructureEngine, TrendDirection
from .regime_engine import RegimeEngine
from .liquidity_engine import LiquidityEngine
from .premium_discount import PremiumDiscountEngine
from .orderblock_engine import OrderBlockEngine
from .fvg_engine import FVGEngine
from .displacement_engine import DisplacementEngine
from .volatility_engine import VolatilityEngine
from .scoring_engine import ScoringEngine
from .risk_manager import RiskManager
from .memory_engine import AdaptiveMemory
from .trade_tracker import TradeTracker
from .notifier import TelegramNotifier

# Setup logging
def setup_logging():
    """Configure logging"""
    
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)
    
    # Create formatters
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, config.LOG_LEVEL))
    console_handler.setFormatter(formatter)
    
    # File handler with rotation
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        config.LOG_FILE,
        maxBytes=config.LOG_MAX_BYTES,
        backupCount=config.LOG_BACKUP_COUNT
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


logger = logging.getLogger(__name__)


class TradingBot:
    """Main trading bot orchestrator"""
    
    def __init__(self):
        # Initialize all engines
        self.symbol_engine = SymbolEngine()
        self.data_engine = DataEngine(self.symbol_engine)
        self.structure_engine = StructureEngine()
        self.regime_engine = RegimeEngine(self.structure_engine)
        self.liquidity_engine = LiquidityEngine()
        self.premium_discount_engine = PremiumDiscountEngine()
        self.orderblock_engine = OrderBlockEngine()
        self.fvg_engine = FVGEngine()
        self.displacement_engine = DisplacementEngine()
        self.volatility_engine = VolatilityEngine()
        self.scoring_engine = ScoringEngine()
        self.risk_manager = RiskManager()
        self.memory_engine = AdaptiveMemory()
        self.trade_tracker = TradeTracker(self.memory_engine)
        self.notifier = TelegramNotifier()
        
        # Background tasks
        self.background_tasks = []
        
        # Running flag
        self.running = False
    
    async def initialize(self):
        """Initialize the bot"""
        
        logger.info("=" * 60)
        logger.info("Initializing Institutional Price Action Swing Bot v2")
        logger.info("=" * 60)
        
        # Initialize symbol engine
        await self.symbol_engine.initialize()
        
        # Initialize data engine
        await self.data_engine.initialize()
        
        logger.info("Bot initialization complete")
    
    async def start(self):
        """Start the bot"""
        
        await self.initialize()
        
        self.running = True
        
        # Start background tasks
        self.background_tasks.append(
            asyncio.create_task(self.symbol_engine.maintenance_loop())
        )
        self.background_tasks.append(
            asyncio.create_task(self.trade_tracker.periodic_ingestion_loop())
        )
        self.background_tasks.append(
            asyncio.create_task(self.scan_loop())
        )
        
        logger.info("Bot started successfully")
        
        # Wait for tasks
        try:
            await asyncio.gather(*self.background_tasks)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
            await self.shutdown()
    
    async def scan_loop(self):
        """Main scanning loop"""
        
        logger.info("Starting scan loop...")
        
        while self.running:
            try:
                # Check if trading is paused
                if self.memory_engine.is_trading_paused():
                    logger.warning("Trading is paused by memory engine")
                    await asyncio.sleep(300)  # Check every 5 minutes
                    continue
                
                # Get active symbols
                symbols = self.symbol_engine.get_active_symbols()
                
                # Scan each symbol
                await self._scan_symbols(symbols)
                
                # Wait before next scan
                await asyncio.sleep(60)  # Scan every minute
                
            except Exception as e:
                logger.error(f"Error in scan loop: {e}", exc_info=True)
                await asyncio.sleep(60)
    
    async def _scan_symbols(self, symbols: List[str]):
        """Scan all symbols for trading opportunities"""
        
        tasks = []
        
        for symbol in symbols:
            task = self._scan_symbol(symbol)
            tasks.append(task)
        
        # Use semaphore to limit concurrent scans
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _scan_symbol(self, symbol: str):
        """Scan a single symbol"""
        
        async with self.data_engine.scan_semaphore:
            try:
                # Check if we can trade this symbol
                if not self.risk_manager.can_trade_symbol(symbol):
                    return
                
                # Check symbol cooldown
                if self.memory_engine.is_symbol_on_cooldown(symbol):
                    return
                
                # Get candles
                candles_1d = self.data_engine.get_candles(symbol, "1d")
                candles_4h = self.data_engine.get_candles(symbol, "4h")
                candles_30m = self.data_engine.get_candles(symbol, "30m")
                
                # Check if we have sufficient data
                if not all([
                    self.data_engine.has_sufficient_data(symbol, "1d", 50),
                    self.data_engine.has_sufficient_data(symbol, "4h", 50),
                    self.data_engine.has_sufficient_data(symbol, "30m", 50)
                ]):
                    return
                
                # Get regime context
                regime_context = self.regime_engine.get_regime_context(
                    candles_1d, candles_4h, candles_30m
                )
                
                regime = regime_context['regime']
                
                # Skip if sideway
                if regime == config.RegimeType.SIDEWAY:
                    return
                
                # Try continuation setup
                if regime == config.RegimeType.TRENDING_CONTINUATION:
                    await self._check_continuation_setup(
                        symbol, regime_context, candles_1d, candles_4h, candles_30m
                    )
                
                # Try reversal setup
                elif regime == config.RegimeType.CONFIRMED_REVERSAL:
                    if not self.memory_engine.is_reversal_disabled():
                        await self._check_reversal_setup(
                            symbol, regime_context, candles_1d, candles_4h, candles_30m
                        )
                
            except Exception as e:
                logger.error(f"Error scanning {symbol}: {e}", exc_info=True)
    
    async def _check_continuation_setup(
        self,
        symbol: str,
        regime_context: Dict,
        candles_1d,
        candles_4h,
        candles_30m
    ):
        """Check for continuation trading setup"""
        
        structure_4h = regime_context['structure_4h']
        structure_30m = regime_context['structure_30m']
        
        trend = structure_4h.get('trend')
        
        if trend == TrendDirection.NEUTRAL:
            return
        
        direction = "long" if trend == TrendDirection.BULLISH else "short"
        
        # Get current price
        current_price = float(list(candles_30m)[-1]['close'])
        
        # Check premium/discount
        pd_info = self.premium_discount_engine.calculate_premium_discount(
            candles_4h, current_price
        )
        
        if direction == "long" and not self.premium_discount_engine.is_valid_for_long(pd_info):
            return
        
        if direction == "short" and not self.premium_discount_engine.is_valid_for_short(pd_info):
            return
        
        # Check liquidity sweep on 30M
        liquidity_sweep = self.liquidity_engine.detect_liquidity_sweep(
            candles_30m, sweep_type="internal"
        )
        
        if not liquidity_sweep.get('swept', False):
            return
        
        # Check for micro CHoCH on 30M
        has_choch = self.structure_engine.detect_choch_on_timeframe(candles_30m, "30m")
        
        if not has_choch:
            return
        
        # Find OB or FVG
        order_blocks = self.orderblock_engine.find_order_blocks(candles_30m, direction)
        fvgs = self.fvg_engine.find_fvgs(candles_30m, direction)
        
        # Calculate scores
        structure_score = self.scoring_engine.calculate_structure_score(
            structure_4h, regime_context['regime']
        )
        
        pullback_score = 80  # Simplified
        
        pd_score = self.premium_discount_engine.score_premium_discount(
            pd_info, direction
        )
        
        liquidity_score = self.liquidity_engine.score_liquidity_sweep(
            liquidity_sweep, "internal"
        )
        
        ob_score = self.orderblock_engine.score_order_block(order_blocks, current_price)
        fvg_score = self.fvg_engine.score_fvg(fvgs, current_price)
        ob_fvg_score = max(ob_score, fvg_score)
        
        displacement_info = self.displacement_engine.detect_displacement(candles_4h, direction)
        displacement_score = self.displacement_engine.score_displacement(displacement_info)
        
        volatility_metrics = self.volatility_engine.calculate_volatility_metrics(candles_30m)
        volatility_score = self.volatility_engine.score_volatility(volatility_metrics)
        
        # Calculate total score
        score_result = self.scoring_engine.score_continuation_setup(
            structure_score, pullback_score, pd_score, liquidity_score,
            ob_fvg_score, displacement_score, volatility_score
        )
        
        total_score = score_result['total_score']
        
        # Apply memory adjustments
        adjusted_threshold = self.memory_engine.get_adjusted_score_threshold(
            config.CONTINUATION_MIN_SCORE
        )
        symbol_adjustment = self.memory_engine.get_symbol_score_adjustment(symbol)
        adjusted_threshold += symbol_adjustment
        
        # Check if score passes
        if total_score < adjusted_threshold:
            logger.debug(
                f"{symbol}: Continuation score {total_score} < {adjusted_threshold}"
            )
            return
        
        # Calculate entry, SL, and TPs
        await self._execute_signal(
            symbol, direction, "continuation", regime_context['regime'],
            current_price, candles_4h, candles_30m, total_score
        )
    
    async def _check_reversal_setup(
        self,
        symbol: str,
        regime_context: Dict,
        candles_1d,
        candles_4h,
        candles_30m
    ):
        """Check for reversal trading setup"""
        
        # Simplified reversal logic
        # In practice, this would have detailed reversal criteria
        
        logger.debug(f"{symbol}: Reversal setup check (simplified)")
        # Implementation similar to continuation but with reversal-specific logic
    
    async def _execute_signal(
        self,
        symbol: str,
        direction: str,
        model_type: str,
        regime: str,
        entry_price: float,
        candles_4h,
        candles_30m,
        score: int
    ):
        """Execute a trading signal"""
        
        try:
            # Calculate stop loss and take profits
            volatility_metrics = self.volatility_engine.calculate_volatility_metrics(candles_30m)
            atr_30m = volatility_metrics['atr']
            
            if direction == "long":
                stop_loss = entry_price - (atr_30m * 1.5)
            else:
                stop_loss = entry_price + (atr_30m * 1.5)
            
            # Get liquidity levels
            structure_4h = self.structure_engine.analyze_structure(candles_4h, "4h")
            liquidity_levels = self.liquidity_engine.identify_liquidity_pools(
                candles_4h, structure_4h
            )
            
            # Calculate targets
            targets = self.risk_manager.calculate_targets(
                entry_price, stop_loss, direction, liquidity_levels
            )
            
            # Validate RR
            if not self.risk_manager.validate_risk_reward(
                entry_price, stop_loss, targets['tp3']
            ):
                logger.debug(f"{symbol}: RR ratio too low")
                return
            
            # Check daily limit
            max_signals = self.memory_engine.get_adjusted_max_signals(
                config.MAX_SIGNALS_PER_DAY
            )
            
            if not self.risk_manager.check_daily_limit(max_signals):
                return
            
            # Prepare signal data
            signal_data = {
                'symbol': symbol,
                'model_type': model_type,
                'regime': regime,
                'direction': direction,
                'entry': entry_price,
                'sl': stop_loss,
                'tp1': targets['tp1'],
                'tp2': targets['tp2'],
                'tp3': targets['tp3'],
                'score': score,
                'rr': targets['tp3_rr'],
                'date_utc': datetime.utcnow().strftime('%Y-%m-%d'),
                'timestamp': int(datetime.utcnow().timestamp() * 1000),
                'winrate': 0,  # Placeholder
                'ev': 0,  # Placeholder
                'reasons': self._generate_reasons(direction, model_type)
            }
            
            # Store in database
            signal_id = self.trade_tracker.store_signal(signal_data)
            
            # Register signal
            candle_index = len(candles_30m)
            self.risk_manager.register_signal(symbol, candle_index)
            
            # Send notification
            await self.notifier.send_signal(signal_data)
            
            logger.info(
                f"✅ SIGNAL: {symbol} {direction.upper()} "
                f"Entry={entry_price:.4f} Score={score}"
            )
            
        except Exception as e:
            logger.error(f"Failed to execute signal: {e}", exc_info=True)
    
    def _generate_reasons(self, direction: str, model_type: str) -> List[str]:
        """Generate Vietnamese reasons for entry"""
        
        reasons = []
        
        if model_type == "continuation":
            reasons.append("Cấu trúc HTF và LTF cùng hướng")
            reasons.append("Sweep liquidity nội bộ thành công")
            reasons.append("Micro CHoCH xác nhận")
            reasons.append(f"Giá ở vùng {'Discount' if direction == 'long' else 'Premium'}")
            reasons.append("Retest Order Block/FVG")
            reasons.append("RR >= 1:2.5")
        else:
            reasons.append("Sweep liquidity bên ngoài")
            reasons.append("CHoCH 4H xác nhận đảo chiều")
            reasons.append("Displacement mạnh")
            reasons.append("Breakout cấu trúc rõ ràng")
        
        return reasons
    
    async def shutdown(self):
        """Shutdown the bot gracefully"""
        
        logger.info("Shutting down bot...")
        
        self.running = False
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        # Cleanup data engine
        await self.data_engine.cleanup()
        
        logger.info("Bot shutdown complete")


async def main():
    """Main entry point"""
    
    setup_logging()
    
    bot = TradingBot()
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        await bot.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
