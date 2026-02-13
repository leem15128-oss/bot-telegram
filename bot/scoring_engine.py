"""
Scoring Engine - Scores trading setups for continuation and reversal
"""
import logging
from typing import Dict

from . import config

logger = logging.getLogger(__name__)


class ScoringEngine:
    """Scores trading setups based on multiple factors"""
    
    def score_continuation_setup(
        self,
        structure_score: int,
        pullback_score: int,
        premium_discount_score: int,
        liquidity_score: int,
        ob_fvg_score: int,
        displacement_score: int,
        volatility_score: int
    ) -> Dict:
        """
        Score a continuation trading setup
        
        Weights:
        - Structure: 25%
        - Pullback: 20%
        - Premium/Discount: 15%
        - Liquidity: 15%
        - OB/FVG: 10%
        - Displacement: 10%
        - Volatility: 5%
        """
        
        weights = config.CONTINUATION_WEIGHTS
        
        # Calculate weighted score
        total_score = (
            structure_score * weights['structure'] / 100 +
            pullback_score * weights['pullback'] / 100 +
            premium_discount_score * weights['premium_discount'] / 100 +
            liquidity_score * weights['liquidity'] / 100 +
            ob_fvg_score * weights['ob_fvg'] / 100 +
            displacement_score * weights['displacement'] / 100 +
            volatility_score * weights['volatility'] / 100
        )
        
        breakdown = {
            'structure': structure_score,
            'pullback': pullback_score,
            'premium_discount': premium_discount_score,
            'liquidity': liquidity_score,
            'ob_fvg': ob_fvg_score,
            'displacement': displacement_score,
            'volatility': volatility_score
        }
        
        return {
            'total_score': int(total_score),
            'breakdown': breakdown,
            'min_required': config.CONTINUATION_MIN_SCORE,
            'passes': total_score >= config.CONTINUATION_MIN_SCORE
        }
    
    def score_reversal_setup(
        self,
        external_sweep_score: int,
        choch_4h_score: int,
        displacement_score: int,
        sr_strength_score: int,
        pattern_score: int,
        volatility_score: int,
        premium_discount_score: int
    ) -> Dict:
        """
        Score a reversal trading setup
        
        Weights:
        - External Sweep: 25%
        - 4H CHoCH: 25%
        - Displacement: 15%
        - SR Strength: 15%
        - Pattern: 10%
        - Volatility: 5%
        - Premium/Discount: 5%
        """
        
        weights = config.REVERSAL_WEIGHTS
        
        # Calculate weighted score
        total_score = (
            external_sweep_score * weights['external_sweep'] / 100 +
            choch_4h_score * weights['choch_4h'] / 100 +
            displacement_score * weights['displacement'] / 100 +
            sr_strength_score * weights['sr_strength'] / 100 +
            pattern_score * weights['pattern'] / 100 +
            volatility_score * weights['volatility'] / 100 +
            premium_discount_score * weights['premium_discount'] / 100
        )
        
        breakdown = {
            'external_sweep': external_sweep_score,
            'choch_4h': choch_4h_score,
            'displacement': displacement_score,
            'sr_strength': sr_strength_score,
            'pattern': pattern_score,
            'volatility': volatility_score,
            'premium_discount': premium_discount_score
        }
        
        return {
            'total_score': int(total_score),
            'breakdown': breakdown,
            'min_required': config.REVERSAL_MIN_SCORE,
            'passes': total_score >= config.REVERSAL_MIN_SCORE
        }
    
    def calculate_structure_score(self, structure: Dict, regime: str) -> int:
        """Calculate structure alignment score"""
        
        if regime == config.RegimeType.SIDEWAY:
            return 0
        
        score = 0
        
        # Structure intact
        if structure.get('structure_intact', False):
            score += 60
        
        # Proper swing pattern
        if regime == config.RegimeType.TRENDING_CONTINUATION:
            from .structure_engine import TrendDirection
            trend = structure.get('trend')
            
            if trend == TrendDirection.BULLISH:
                if structure.get('has_higher_highs') and structure.get('has_higher_lows'):
                    score += 40
            elif trend == TrendDirection.BEARISH:
                if structure.get('has_lower_highs') and structure.get('has_lower_lows'):
                    score += 40
        
        return min(score, 100)
    
    def calculate_pullback_score(
        self,
        pullback_percentage: float,
        regime: str
    ) -> int:
        """Calculate pullback quality score"""
        
        if regime == config.RegimeType.TRENDING_CONTINUATION:
            # For continuation, prefer shallow pullbacks (< 50%)
            if pullback_percentage > config.CONTINUATION_PULLBACK_MAX:
                return 0
            
            # Best pullback: 38.2% - 50%
            if 0.35 <= pullback_percentage <= 0.50:
                return 100
            elif 0.25 <= pullback_percentage < 0.35:
                return 80
            else:
                return 60
        
        elif regime == config.RegimeType.CONFIRMED_REVERSAL:
            # For reversal, prefer deep pullbacks (> 50%)
            if pullback_percentage < config.REVERSAL_PULLBACK_MIN:
                return 0
            
            # Deeper pullback = better for reversal
            if pullback_percentage >= 0.618:
                return 100
            elif pullback_percentage >= 0.50:
                return 80
            else:
                return 40
        
        return 0
