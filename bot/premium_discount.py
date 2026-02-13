"""
Premium/Discount Engine - Determines price positioning relative to range
"""
import logging
from collections import deque
from typing import Dict, Optional, Tuple

from . import config

logger = logging.getLogger(__name__)


class PremiumDiscountEngine:
    """Analyzes premium and discount zones"""
    
    def calculate_premium_discount(
        self,
        candles_4h: deque,
        current_price: float
    ) -> Dict:
        """
        Calculate premium/discount positioning
        Returns zone information and score
        """
        
        if len(candles_4h) < 50:
            return {
                'zone': 'neutral',
                'percentage': 0.5,
                'swing_high': None,
                'swing_low': None,
                'equilibrium': None
            }
        
        # Get swing high and low from 4H
        swing_high, swing_low = self._get_swing_range(candles_4h)
        
        if not swing_high or not swing_low or swing_high <= swing_low:
            return {
                'zone': 'neutral',
                'percentage': 0.5,
                'swing_high': swing_high,
                'swing_low': swing_low,
                'equilibrium': None
            }
        
        # Calculate equilibrium (50%)
        equilibrium = swing_low + (swing_high - swing_low) * config.PREMIUM_DISCOUNT_EQ
        
        # Calculate where current price sits in the range (0 = low, 1 = high)
        range_size = swing_high - swing_low
        position_in_range = (current_price - swing_low) / range_size
        
        # Determine zone
        if position_in_range < config.PREMIUM_DISCOUNT_EQ:
            zone = 'discount'
        elif position_in_range > config.PREMIUM_DISCOUNT_EQ:
            zone = 'premium'
        else:
            zone = 'equilibrium'
        
        return {
            'zone': zone,
            'percentage': position_in_range,
            'swing_high': swing_high,
            'swing_low': swing_low,
            'equilibrium': equilibrium,
            'distance_from_eq': abs(position_in_range - 0.5)
        }
    
    def _get_swing_range(
        self,
        candles: deque,
        lookback: int = 50
    ) -> Tuple[Optional[float], Optional[float]]:
        """Get swing high and low from recent candles"""
        
        if len(candles) < lookback:
            lookback = len(candles)
        
        recent_candles = list(candles)[-lookback:]
        
        highs = [float(c['high']) for c in recent_candles]
        lows = [float(c['low']) for c in recent_candles]
        
        swing_high = max(highs) if highs else None
        swing_low = min(lows) if lows else None
        
        return swing_high, swing_low
    
    def is_valid_for_long(self, pd_info: Dict) -> bool:
        """Check if price is in valid zone for long entry"""
        zone = pd_info.get('zone')
        return zone == 'discount' or pd_info.get('percentage', 1.0) < config.PREMIUM_DISCOUNT_EQ
    
    def is_valid_for_short(self, pd_info: Dict) -> bool:
        """Check if price is in valid zone for short entry"""
        zone = pd_info.get('zone')
        return zone == 'premium' or pd_info.get('percentage', 0.0) > config.PREMIUM_DISCOUNT_EQ
    
    def score_premium_discount(
        self,
        pd_info: Dict,
        direction: str  # "long" or "short"
    ) -> int:
        """
        Score premium/discount positioning (0-100)
        Better positioning = higher score
        """
        
        zone = pd_info.get('zone', 'neutral')
        percentage = pd_info.get('percentage', 0.5)
        
        if direction == "long":
            # For longs, we want to be in discount (below 50%)
            if zone == 'discount':
                # Deeper discount = better score
                # 0% = 100 score, 50% = 0 score
                score = int((0.5 - percentage) * 200)
            elif zone == 'equilibrium':
                score = 50
            else:  # premium
                score = 0
        
        elif direction == "short":
            # For shorts, we want to be in premium (above 50%)
            if zone == 'premium':
                # Higher premium = better score
                # 100% = 100 score, 50% = 0 score
                score = int((percentage - 0.5) * 200)
            elif zone == 'equilibrium':
                score = 50
            else:  # discount
                score = 0
        
        else:
            score = 0
        
        return max(0, min(100, score))
