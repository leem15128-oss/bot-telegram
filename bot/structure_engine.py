"""
Structure Engine - Detects market structure (CHoCH, BOS, swing points)
"""
import logging
from collections import deque
from typing import Dict, List, Optional, Tuple
from enum import Enum

from .utils import is_bullish_candle, is_bearish_candle

logger = logging.getLogger(__name__)


class TrendDirection(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class StructureEvent(Enum):
    CHOCH = "CHoCH"  # Change of Character
    BOS = "BOS"  # Break of Structure
    NONE = "none"


class SwingPoint:
    """Represents a swing high or swing low"""
    
    def __init__(self, price: float, index: int, is_high: bool):
        self.price = price
        self.index = index
        self.is_high = is_high
    
    def __repr__(self):
        type_str = "High" if self.is_high else "Low"
        return f"Swing{type_str}({self.price}, idx={self.index})"


class StructureEngine:
    """Analyzes market structure for ICT/SMC concepts"""
    
    def __init__(self):
        # Cache structure analysis results
        self._structure_cache: Dict[str, Dict] = {}
    
    def analyze_structure(
        self,
        candles: deque,
        timeframe: str
    ) -> Dict:
        """
        Analyze market structure for a given timeframe
        Returns structure information including trend, swing points, and breaks
        """
        
        if len(candles) < 20:
            return self._empty_structure()
        
        # Find swing highs and lows
        swing_highs = self._find_swing_highs(candles)
        swing_lows = self._find_swing_lows(candles)
        
        # Determine current trend
        trend = self._determine_trend(swing_highs, swing_lows)
        
        # Detect structure breaks
        last_break = self._detect_structure_break(
            candles, swing_highs, swing_lows, trend
        )
        
        # Check if structure is intact
        structure_intact = self._is_structure_intact(
            swing_highs, swing_lows, trend
        )
        
        # Get most recent swing points
        recent_high = swing_highs[-1] if swing_highs else None
        recent_low = swing_lows[-1] if swing_lows else None
        
        return {
            'timeframe': timeframe,
            'trend': trend,
            'swing_highs': swing_highs,
            'swing_lows': swing_lows,
            'recent_high': recent_high,
            'recent_low': recent_low,
            'last_break': last_break,
            'structure_intact': structure_intact,
            'has_higher_highs': self._has_higher_highs(swing_highs),
            'has_lower_lows': self._has_lower_lows(swing_lows),
            'has_higher_lows': self._has_higher_lows(swing_lows),
            'has_lower_highs': self._has_lower_highs(swing_highs)
        }
    
    def _empty_structure(self) -> Dict:
        """Return empty structure data"""
        return {
            'timeframe': None,
            'trend': TrendDirection.NEUTRAL,
            'swing_highs': [],
            'swing_lows': [],
            'recent_high': None,
            'recent_low': None,
            'last_break': StructureEvent.NONE,
            'structure_intact': False,
            'has_higher_highs': False,
            'has_lower_lows': False,
            'has_higher_lows': False,
            'has_lower_highs': False
        }
    
    def _find_swing_highs(self, candles: deque, lookback: int = 5) -> List[SwingPoint]:
        """Find swing highs in the candle data"""
        swing_highs = []
        candles_list = list(candles)
        
        for i in range(lookback, len(candles_list) - lookback):
            current_high = float(candles_list[i]['high'])
            
            # Check if this is a local high
            is_swing_high = True
            
            # Check left side
            for j in range(i - lookback, i):
                if float(candles_list[j]['high']) >= current_high:
                    is_swing_high = False
                    break
            
            # Check right side
            if is_swing_high:
                for j in range(i + 1, min(i + lookback + 1, len(candles_list))):
                    if float(candles_list[j]['high']) >= current_high:
                        is_swing_high = False
                        break
            
            if is_swing_high:
                swing_highs.append(SwingPoint(current_high, i, True))
        
        return swing_highs
    
    def _find_swing_lows(self, candles: deque, lookback: int = 5) -> List[SwingPoint]:
        """Find swing lows in the candle data"""
        swing_lows = []
        candles_list = list(candles)
        
        for i in range(lookback, len(candles_list) - lookback):
            current_low = float(candles_list[i]['low'])
            
            # Check if this is a local low
            is_swing_low = True
            
            # Check left side
            for j in range(i - lookback, i):
                if float(candles_list[j]['low']) <= current_low:
                    is_swing_low = False
                    break
            
            # Check right side
            if is_swing_low:
                for j in range(i + 1, min(i + lookback + 1, len(candles_list))):
                    if float(candles_list[j]['low']) <= current_low:
                        is_swing_low = False
                        break
            
            if is_swing_low:
                swing_lows.append(SwingPoint(current_low, i, False))
        
        return swing_lows
    
    def _determine_trend(
        self,
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint]
    ) -> TrendDirection:
        """Determine the current trend based on swing points"""
        
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return TrendDirection.NEUTRAL
        
        # Check for higher highs and higher lows (bullish trend)
        has_hh = swing_highs[-1].price > swing_highs[-2].price
        has_hl = swing_lows[-1].price > swing_lows[-2].price
        
        # Check for lower highs and lower lows (bearish trend)
        has_lh = swing_highs[-1].price < swing_highs[-2].price
        has_ll = swing_lows[-1].price < swing_lows[-2].price
        
        if has_hh and has_hl:
            return TrendDirection.BULLISH
        elif has_lh and has_ll:
            return TrendDirection.BEARISH
        else:
            return TrendDirection.NEUTRAL
    
    def _detect_structure_break(
        self,
        candles: deque,
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint],
        current_trend: TrendDirection
    ) -> StructureEvent:
        """Detect if there's a structure break (CHoCH or BOS)"""
        
        if not candles or len(candles) < 10:
            return StructureEvent.NONE
        
        if not swing_highs or not swing_lows:
            return StructureEvent.NONE
        
        recent_candles = list(candles)[-10:]
        recent_close = float(recent_candles[-1]['close'])
        
        # In bullish trend, look for break below recent swing low (CHoCH)
        if current_trend == TrendDirection.BULLISH:
            if swing_lows:
                recent_swing_low = swing_lows[-1].price
                if recent_close < recent_swing_low:
                    return StructureEvent.CHOCH
        
        # In bearish trend, look for break above recent swing high (CHoCH)
        elif current_trend == TrendDirection.BEARISH:
            if swing_highs:
                recent_swing_high = swing_highs[-1].price
                if recent_close > recent_swing_high:
                    return StructureEvent.CHOCH
        
        return StructureEvent.NONE
    
    def _is_structure_intact(
        self,
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint],
        trend: TrendDirection
    ) -> bool:
        """Check if market structure is still intact"""
        
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return False
        
        if trend == TrendDirection.BULLISH:
            # In bullish trend, structure is intact if we have higher lows
            return swing_lows[-1].price > swing_lows[-2].price
        
        elif trend == TrendDirection.BEARISH:
            # In bearish trend, structure is intact if we have lower highs
            return swing_highs[-1].price < swing_highs[-2].price
        
        return False
    
    def _has_higher_highs(self, swing_highs: List[SwingPoint]) -> bool:
        """Check if there are higher highs"""
        if len(swing_highs) < 2:
            return False
        return swing_highs[-1].price > swing_highs[-2].price
    
    def _has_lower_lows(self, swing_lows: List[SwingPoint]) -> bool:
        """Check if there are lower lows"""
        if len(swing_lows) < 2:
            return False
        return swing_lows[-1].price < swing_lows[-2].price
    
    def _has_higher_lows(self, swing_lows: List[SwingPoint]) -> bool:
        """Check if there are higher lows"""
        if len(swing_lows) < 2:
            return False
        return swing_lows[-1].price > swing_lows[-2].price
    
    def _has_lower_highs(self, swing_highs: List[SwingPoint]) -> bool:
        """Check if there are lower highs"""
        if len(swing_highs) < 2:
            return False
        return swing_highs[-1].price < swing_highs[-2].price
    
    def check_alignment(
        self,
        structure_1d: Dict,
        structure_4h: Dict
    ) -> bool:
        """Check if 1D and 4H structures are aligned"""
        
        if not structure_1d or not structure_4h:
            return False
        
        trend_1d = structure_1d.get('trend')
        trend_4h = structure_4h.get('trend')
        
        # Both must be trending in the same direction
        return trend_1d == trend_4h and trend_1d != TrendDirection.NEUTRAL
    
    def detect_choch_on_timeframe(
        self,
        candles: deque,
        timeframe: str,
        lookback: int = 20
    ) -> bool:
        """Detect CHoCH on specific timeframe"""
        
        if len(candles) < lookback:
            return False
        
        structure = self.analyze_structure(candles, timeframe)
        return structure['last_break'] == StructureEvent.CHOCH
