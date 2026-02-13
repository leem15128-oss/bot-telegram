"""
Fair Value Gap (FVG) Engine - Detects and validates FVGs
"""
import logging
from collections import deque
from typing import Dict, List, Optional

from .utils import find_fvg

logger = logging.getLogger(__name__)


class FVGEngine:
    """Detects and validates Fair Value Gaps"""
    
    def find_fvgs(
        self,
        candles: deque,
        direction: str,  # "bullish" or "bearish"
        lookback: int = 20
    ) -> List[Dict]:
        """
        Find Fair Value Gaps in recent candles
        """
        
        all_fvgs = find_fvg(candles, lookback)
        
        # Filter by direction
        filtered_fvgs = [
            fvg for fvg in all_fvgs
            if fvg['type'] == direction
        ]
        
        return filtered_fvgs
    
    def check_fvg_retest(
        self,
        current_price: float,
        fvg: Dict,
        tolerance: float = 0.001  # 0.1% tolerance
    ) -> bool:
        """Check if current price is retesting an FVG"""
        
        fvg_top = fvg['top']
        fvg_bottom = fvg['bottom']
        
        # Check if price is within the FVG zone
        in_zone = fvg_bottom <= current_price <= fvg_top
        
        if in_zone:
            return True
        
        # Check if price is near the zone
        fvg_mid = (fvg_top + fvg_bottom) / 2
        distance = abs(current_price - fvg_mid) / fvg_mid
        
        return distance <= tolerance
    
    def score_fvg(
        self,
        fvgs: List[Dict],
        current_price: float
    ) -> int:
        """
        Score FVG setup (0-100)
        """
        
        if not fvgs:
            return 0
        
        # Find FVGs being retested
        valid_fvgs = [
            fvg for fvg in fvgs
            if self.check_fvg_retest(current_price, fvg)
        ]
        
        if not valid_fvgs:
            return 0
        
        # Score based on FVG quality
        score = 70  # Base score for having a valid FVG
        
        # Bonus for multiple FVGs aligned
        if len(valid_fvgs) > 1:
            score += 30
        
        return min(score, 100)
