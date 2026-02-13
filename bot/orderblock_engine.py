"""
Order Block Engine - Detects order blocks for entry zones
"""
import logging
from collections import deque
from typing import Dict, List, Optional

from .utils import is_bullish_candle, is_bearish_candle, candle_body_size

logger = logging.getLogger(__name__)


class OrderBlockEngine:
    """Detects and validates order blocks"""
    
    def find_order_blocks(
        self,
        candles: deque,
        direction: str,  # "bullish" or "bearish"
        lookback: int = 20
    ) -> List[Dict]:
        """
        Find order blocks in recent candles
        Returns list of order block zones
        """
        
        if len(candles) < lookback:
            return []
        
        order_blocks = []
        candles_list = list(candles)[-lookback:]
        
        for i in range(len(candles_list) - 1):
            current = candles_list[i]
            next_candle = candles_list[i + 1]
            
            # Bullish order block: strong bearish candle followed by bullish move
            if direction == "bullish":
                if is_bearish_candle(current) and is_bullish_candle(next_candle):
                    body_size = candle_body_size(current)
                    
                    # Check if it's a significant candle
                    if body_size > 0:
                        order_blocks.append({
                            'type': 'bullish',
                            'high': float(current['high']),
                            'low': float(current['low']),
                            'open': float(current['open']),
                            'close': float(current['close']),
                            'index': len(candles_list) - lookback + i,
                            'strength': self._calculate_ob_strength(current, next_candle)
                        })
            
            # Bearish order block: strong bullish candle followed by bearish move
            elif direction == "bearish":
                if is_bullish_candle(current) and is_bearish_candle(next_candle):
                    body_size = candle_body_size(current)
                    
                    if body_size > 0:
                        order_blocks.append({
                            'type': 'bearish',
                            'high': float(current['high']),
                            'low': float(current['low']),
                            'open': float(current['open']),
                            'close': float(current['close']),
                            'index': len(candles_list) - lookback + i,
                            'strength': self._calculate_ob_strength(current, next_candle)
                        })
        
        # Sort by strength
        order_blocks.sort(key=lambda x: x['strength'], reverse=True)
        
        return order_blocks
    
    def _calculate_ob_strength(self, setup_candle: Dict, reaction_candle: Dict) -> float:
        """Calculate order block strength based on candle characteristics"""
        
        setup_body = candle_body_size(setup_candle)
        reaction_body = candle_body_size(reaction_candle)
        
        # Strength based on body sizes
        strength = (setup_body + reaction_body) / 2
        
        return strength
    
    def check_ob_retest(
        self,
        current_price: float,
        order_block: Dict,
        tolerance: float = 0.002  # 0.2% tolerance
    ) -> bool:
        """Check if current price is retesting an order block"""
        
        ob_high = order_block['high']
        ob_low = order_block['low']
        
        # Check if price is within the order block zone
        in_zone = ob_low <= current_price <= ob_high
        
        if in_zone:
            return True
        
        # Check if price is near the zone (within tolerance)
        ob_mid = (ob_high + ob_low) / 2
        distance = abs(current_price - ob_mid) / ob_mid
        
        return distance <= tolerance
    
    def score_order_block(
        self,
        order_blocks: List[Dict],
        current_price: float
    ) -> int:
        """
        Score order block setup (0-100)
        """
        
        if not order_blocks:
            return 0
        
        # Find the nearest order block being retested
        valid_obs = [
            ob for ob in order_blocks
            if self.check_ob_retest(current_price, ob)
        ]
        
        if not valid_obs:
            return 0
        
        # Use the strongest order block
        best_ob = valid_obs[0]
        
        # Base score for having a valid OB
        score = 70
        
        # Bonus for strong OB
        if best_ob['strength'] > 0:
            score += 30
        
        return min(score, 100)
