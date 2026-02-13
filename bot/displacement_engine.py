"""
Displacement Engine - Validates impulse moves and displacement
"""
import logging
from collections import deque
from typing import Dict, List, Optional

from . import config
from .utils import (
    calculate_atr, calculate_volume_ma, candle_body_size,
    is_displacement_candle
)

logger = logging.getLogger(__name__)


class DisplacementEngine:
    """Validates displacement and impulse moves"""
    
    def detect_displacement(
        self,
        candles: deque,
        direction: str,  # "bullish" or "bearish"
        lookback: int = 10
    ) -> Dict:
        """
        Detect displacement in recent candles
        Returns displacement information
        """
        
        if len(candles) < config.ATR_PERIOD + lookback:
            return {'detected': False}
        
        # Calculate ATR and volume MA
        atr = calculate_atr(candles, config.ATR_PERIOD)
        volume_ma = calculate_volume_ma(candles, config.VOLUME_MA_PERIOD)
        
        # Check recent candles for displacement
        recent_candles = list(candles)[-lookback:]
        
        for i, candle in enumerate(recent_candles):
            body = candle_body_size(candle)
            volume = float(candle['volume'])
            
            # Check displacement criteria
            is_displacement = (
                body > atr * config.DISPLACEMENT_ATR_MULTIPLE and
                volume > volume_ma * config.DISPLACEMENT_VOLUME_MULTIPLE
            )
            
            if not is_displacement:
                continue
            
            # Check direction match
            candle_direction = "bullish" if float(candle['close']) > float(candle['open']) else "bearish"
            
            if candle_direction == direction:
                # Check if it breaks structure (leaves FVG)
                has_fvg = self._check_fvg_left(recent_candles, i)
                
                return {
                    'detected': True,
                    'candle_index': i,
                    'body_size': body,
                    'atr_multiple': body / atr if atr > 0 else 0,
                    'volume_multiple': volume / volume_ma if volume_ma > 0 else 0,
                    'has_fvg': has_fvg,
                    'strength': self._calculate_displacement_strength(body, atr, volume, volume_ma)
                }
        
        return {'detected': False}
    
    def _check_fvg_left(self, candles: List[Dict], displacement_index: int) -> bool:
        """Check if displacement left an FVG"""
        
        if displacement_index < 1 or displacement_index >= len(candles) - 1:
            return False
        
        prev_candle = candles[displacement_index - 1]
        displacement_candle = candles[displacement_index]
        next_candle = candles[displacement_index + 1] if displacement_index + 1 < len(candles) else None
        
        if not next_candle:
            return False
        
        # Check for bullish FVG
        if float(prev_candle['low']) > float(next_candle['high']):
            return True
        
        # Check for bearish FVG
        if float(prev_candle['high']) < float(next_candle['low']):
            return True
        
        return False
    
    def _calculate_displacement_strength(
        self,
        body: float,
        atr: float,
        volume: float,
        volume_ma: float
    ) -> float:
        """Calculate displacement strength score"""
        
        atr_ratio = body / atr if atr > 0 else 0
        volume_ratio = volume / volume_ma if volume_ma > 0 else 0
        
        # Combine both ratios
        strength = (atr_ratio + volume_ratio) / 2
        
        return strength
    
    def score_displacement(self, displacement_info: Dict) -> int:
        """
        Score displacement quality (0-100)
        """
        
        if not displacement_info.get('detected', False):
            return 0
        
        strength = displacement_info.get('strength', 0)
        has_fvg = displacement_info.get('has_fvg', False)
        
        # Base score from strength
        score = min(int(strength * 30), 70)
        
        # Bonus for leaving FVG
        if has_fvg:
            score += 30
        
        return min(score, 100)
    
    def validate_impulse(
        self,
        candles: deque,
        direction: str
    ) -> bool:
        """
        Validate if there's a valid impulse move
        
        Criteria:
        - Body > 1.5 ATR
        - Breaks structure
        - Leaves FVG
        - Volume > 1.2x average
        """
        
        displacement = self.detect_displacement(candles, direction)
        
        if not displacement.get('detected', False):
            return False
        
        # Check all criteria
        atr_multiple = displacement.get('atr_multiple', 0)
        volume_multiple = displacement.get('volume_multiple', 0)
        has_fvg = displacement.get('has_fvg', False)
        
        return (
            atr_multiple >= config.DISPLACEMENT_ATR_MULTIPLE and
            volume_multiple >= config.DISPLACEMENT_VOLUME_MULTIPLE and
            has_fvg
        )
