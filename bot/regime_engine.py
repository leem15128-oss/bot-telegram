"""
Regime Engine - Classifies market regime (Trending/Reversal/Sideway)
"""
import logging
from collections import deque
from typing import Dict, Optional

from . import config
from .utils import calculate_atr
from .structure_engine import StructureEngine, TrendDirection

logger = logging.getLogger(__name__)


class RegimeEngine:
    """Classifies market regime for trading decisions"""
    
    def __init__(self, structure_engine: StructureEngine):
        self.structure_engine = structure_engine
    
    def classify_regime(
        self,
        candles_1d: deque,
        candles_4h: deque,
        candles_30m: deque
    ) -> str:
        """
        Classify market regime based on multi-timeframe analysis
        Returns: TRENDING_CONTINUATION, CONFIRMED_REVERSAL, or SIDEWAY
        """
        
        # Check for sideway conditions first
        if self._is_sideway(candles_4h):
            logger.debug("Regime: SIDEWAY detected")
            return config.RegimeType.SIDEWAY
        
        # Analyze structure on each timeframe
        structure_1d = self.structure_engine.analyze_structure(candles_1d, "1d")
        structure_4h = self.structure_engine.analyze_structure(candles_4h, "4h")
        structure_30m = self.structure_engine.analyze_structure(candles_30m, "30m")
        
        # Check for confirmed reversal
        if self._is_confirmed_reversal(structure_1d, structure_4h, candles_4h):
            logger.debug("Regime: CONFIRMED_REVERSAL")
            return config.RegimeType.CONFIRMED_REVERSAL
        
        # Check for trending continuation
        if self._is_trending_continuation(structure_1d, structure_4h):
            logger.debug("Regime: TRENDING_CONTINUATION")
            return config.RegimeType.TRENDING_CONTINUATION
        
        # Default to sideway if no clear regime
        logger.debug("Regime: SIDEWAY (default)")
        return config.RegimeType.SIDEWAY
    
    def _is_sideway(self, candles_4h: deque) -> bool:
        """
        Check if market is in sideway/ranging condition
        Criteria:
        - Low ATR
        - No clear HH/LL pattern
        - Overlapping structure
        - No displacement > 1.5 ATR
        """
        
        if len(candles_4h) < 50:
            return True  # Not enough data, assume sideway
        
        # Calculate ATR
        atr = calculate_atr(candles_4h, config.ATR_PERIOD)
        
        # Get recent price for relative ATR check
        recent_close = float(list(candles_4h)[-1]['close'])
        atr_percentage = atr / recent_close if recent_close > 0 else 0
        
        # Check 1: Low ATR
        if atr_percentage < config.SIDEWAY_ATR_THRESHOLD:
            logger.debug(f"Sideway: Low ATR ({atr_percentage:.4f})")
            return True
        
        # Analyze structure
        structure = self.structure_engine.analyze_structure(candles_4h, "4h")
        
        # Check 2: No clear HH/LL pattern
        has_hh = structure.get('has_higher_highs', False)
        has_ll = structure.get('has_lower_lows', False)
        
        if not has_hh and not has_ll:
            logger.debug("Sideway: No HH/LL pattern")
            return True
        
        # Check 3: Check for displacement
        recent_candles = list(candles_4h)[-10:]
        has_displacement = False
        
        for candle in recent_candles:
            body = abs(float(candle['close']) - float(candle['open']))
            if body > atr * config.SIDEWAY_DISPLACEMENT_THRESHOLD:
                has_displacement = True
                break
        
        if not has_displacement:
            logger.debug("Sideway: No displacement")
            return True
        
        return False
    
    def _is_confirmed_reversal(
        self,
        structure_1d: Dict,
        structure_4h: Dict,
        candles_4h: deque
    ) -> bool:
        """
        Check if this is a confirmed reversal setup
        Criteria:
        - External liquidity sweep
        - 4H CHoCH confirmed
        - Strong displacement
        - Pullback > 50%
        - Volume expansion
        """
        
        from .structure_engine import StructureEvent
        
        # Must have CHoCH on 4H
        if structure_4h.get('last_break') != StructureEvent.CHOCH:
            return False
        
        # Check for trend change
        trend_1d = structure_1d.get('trend')
        trend_4h = structure_4h.get('trend')
        
        # 4H should show trend change while 1D might be lagging
        if trend_4h == TrendDirection.NEUTRAL:
            return False
        
        # Check for displacement in recent candles
        if len(candles_4h) < 10:
            return False
        
        recent_candles = list(candles_4h)[-10:]
        atr = calculate_atr(candles_4h, config.ATR_PERIOD)
        
        has_strong_displacement = False
        for candle in recent_candles:
            body = abs(float(candle['close']) - float(candle['open']))
            if body > atr * 2.0:  # Strong displacement = 2x ATR
                has_strong_displacement = True
                break
        
        if not has_strong_displacement:
            return False
        
        return True
    
    def _is_trending_continuation(
        self,
        structure_1d: Dict,
        structure_4h: Dict
    ) -> bool:
        """
        Check if this is a trending continuation setup
        Criteria:
        - 1D and 4H aligned
        - Structure intact
        - No CHoCH
        """
        
        from .structure_engine import StructureEvent
        
        # Check alignment
        if not self.structure_engine.check_alignment(structure_1d, structure_4h):
            return False
        
        # Structure should be intact on both timeframes
        if not structure_1d.get('structure_intact', False):
            return False
        
        if not structure_4h.get('structure_intact', False):
            return False
        
        # Should not have CHoCH
        if structure_4h.get('last_break') == StructureEvent.CHOCH:
            return False
        
        return True
    
    def get_regime_context(
        self,
        candles_1d: deque,
        candles_4h: deque,
        candles_30m: deque
    ) -> Dict:
        """
        Get detailed regime context for decision making
        """
        
        regime = self.classify_regime(candles_1d, candles_4h, candles_30m)
        
        structure_1d = self.structure_engine.analyze_structure(candles_1d, "1d")
        structure_4h = self.structure_engine.analyze_structure(candles_4h, "4h")
        structure_30m = self.structure_engine.analyze_structure(candles_30m, "30m")
        
        return {
            'regime': regime,
            'structure_1d': structure_1d,
            'structure_4h': structure_4h,
            'structure_30m': structure_30m,
            'aligned': self.structure_engine.check_alignment(structure_1d, structure_4h),
            'atr_4h': calculate_atr(candles_4h, config.ATR_PERIOD),
            'atr_30m': calculate_atr(candles_30m, config.ATR_PERIOD)
        }
