"""
Volatility Engine - Calculates volatility metrics
"""
import logging
from collections import deque
from typing import Dict

from . import config
from .utils import calculate_atr

logger = logging.getLogger(__name__)


class VolatilityEngine:
    """Calculates and analyzes volatility metrics"""
    
    def calculate_volatility_metrics(self, candles: deque) -> Dict:
        """
        Calculate various volatility metrics
        """
        
        if len(candles) < config.ATR_PERIOD:
            return {
                'atr': 0,
                'atr_percentage': 0,
                'volatility_regime': 'low'
            }
        
        # Calculate ATR
        atr = calculate_atr(candles, config.ATR_PERIOD)
        
        # Get current price for percentage calculation
        current_price = float(list(candles)[-1]['close'])
        atr_percentage = (atr / current_price * 100) if current_price > 0 else 0
        
        # Classify volatility regime
        if atr_percentage < 1.0:
            volatility_regime = 'low'
        elif atr_percentage < 3.0:
            volatility_regime = 'medium'
        else:
            volatility_regime = 'high'
        
        return {
            'atr': atr,
            'atr_percentage': atr_percentage,
            'volatility_regime': volatility_regime
        }
    
    def score_volatility(
        self,
        volatility_metrics: Dict,
        preferred_regime: str = 'medium'
    ) -> int:
        """
        Score volatility conditions (0-100)
        Prefer medium volatility for best trading conditions
        """
        
        regime = volatility_metrics.get('volatility_regime', 'low')
        
        if regime == preferred_regime:
            return 100
        elif regime == 'medium':
            return 80  # Medium is generally good
        elif regime == 'high':
            return 60  # High volatility increases risk
        else:  # low
            return 40  # Low volatility means less opportunity
    
    def is_sufficient_volatility(self, volatility_metrics: Dict) -> bool:
        """Check if there's sufficient volatility for trading"""
        
        regime = volatility_metrics.get('volatility_regime', 'low')
        return regime in ['medium', 'high']
