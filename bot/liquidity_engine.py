"""
Liquidity Engine - Detects liquidity sweeps and pools
"""
import logging
from collections import deque
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class LiquidityEngine:
    """Detects liquidity sweeps and liquidity pools"""
    
    def detect_liquidity_sweep(
        self,
        candles: deque,
        sweep_type: str = "both"  # "internal", "external", or "both"
    ) -> Dict:
        """
        Detect liquidity sweep in recent candles
        Returns information about the sweep
        """
        
        if len(candles) < 20:
            return {'swept': False}
        
        candles_list = list(candles)
        recent_high = max(float(c['high']) for c in candles_list[-20:-1])
        recent_low = min(float(c['low']) for c in candles_list[-20:-1])
        
        latest_candle = candles_list[-1]
        latest_high = float(latest_candle['high'])
        latest_low = float(latest_candle['low'])
        latest_close = float(latest_candle['close'])
        
        # External sweep: price goes beyond recent high/low and reverses
        external_sweep_up = (
            latest_high > recent_high and 
            latest_close < recent_high
        )
        
        external_sweep_down = (
            latest_low < recent_low and 
            latest_close > recent_low
        )
        
        # Internal sweep: price tests recent levels without breaking
        internal_sweep_up = (
            abs(latest_high - recent_high) / recent_high < 0.002 and  # Within 0.2%
            latest_close < latest_high
        )
        
        internal_sweep_down = (
            abs(latest_low - recent_low) / recent_low < 0.002 and  # Within 0.2%
            latest_close > latest_low
        )
        
        result = {'swept': False}
        
        if external_sweep_up:
            result = {
                'swept': True,
                'type': 'external',
                'direction': 'up',
                'level': recent_high,
                'sweep_high': latest_high
            }
        elif external_sweep_down:
            result = {
                'swept': True,
                'type': 'external',
                'direction': 'down',
                'level': recent_low,
                'sweep_low': latest_low
            }
        elif internal_sweep_up and sweep_type in ["internal", "both"]:
            result = {
                'swept': True,
                'type': 'internal',
                'direction': 'up',
                'level': recent_high
            }
        elif internal_sweep_down and sweep_type in ["internal", "both"]:
            result = {
                'swept': True,
                'type': 'internal',
                'direction': 'down',
                'level': recent_low
            }
        
        return result
    
    def identify_liquidity_pools(
        self,
        candles: deque,
        structure: Dict
    ) -> Dict:
        """
        Identify potential liquidity pools based on structure
        Returns levels for internal and external liquidity
        """
        
        swing_highs = structure.get('swing_highs', [])
        swing_lows = structure.get('swing_lows', [])
        
        if not swing_highs or not swing_lows:
            return {'internal': None, 'external': None}
        
        # External liquidity: beyond recent swing points
        external_high = max(sh.price for sh in swing_highs[-3:]) if len(swing_highs) >= 3 else None
        external_low = min(sl.price for sl in swing_lows[-3:]) if len(swing_lows) >= 3 else None
        
        # Internal liquidity: recent swing points
        internal_high = swing_highs[-1].price if swing_highs else None
        internal_low = swing_lows[-1].price if swing_lows else None
        
        return {
            'internal': {
                'high': internal_high,
                'low': internal_low
            },
            'external': {
                'high': external_high,
                'low': external_low
            }
        }
    
    def score_liquidity_sweep(
        self,
        sweep_info: Dict,
        required_type: str = "internal"
    ) -> int:
        """
        Score liquidity sweep for trading setup (0-100)
        """
        
        if not sweep_info.get('swept', False):
            return 0
        
        score = 0
        
        # Type match
        if sweep_info.get('type') == required_type:
            score += 60
        elif sweep_info.get('type') == 'external' and required_type == 'internal':
            score += 30  # External sweep is good but not what we want for entry
        
        # Clean reversal after sweep
        if 'sweep_high' in sweep_info or 'sweep_low' in sweep_info:
            score += 40
        
        return min(score, 100)
