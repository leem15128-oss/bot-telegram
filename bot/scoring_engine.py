"""
Scoring Engine Module

This module provides scoring functionality for detected candlestick patterns.
Each pattern is assigned a weight that contributes to the overall score.
"""

from typing import List, Dict, Optional
from bot.candle_patterns import detect_all_patterns


# Default pattern weights for scoring
# Bullish patterns have positive weights, bearish patterns have negative weights
DEFAULT_PATTERN_WEIGHTS = {
    # Doji patterns - neutral/reversal indicators (context-dependent)
    'doji': 0.5,
    'long_legged_doji': 0.6,
    'dragonfly_doji': 1.5,  # Bullish when at support
    'gravestone_doji': -1.5,  # Bearish when at resistance
    
    # Star patterns - strong reversal signals
    'morning_star': 2.5,  # Strong bullish reversal
    'evening_star': -2.5,  # Strong bearish reversal
    
    # Harami patterns - reversal signals
    'bullish_harami': 1.5,
    'bearish_harami': -1.5,
    
    # Tweezer patterns - reversal signals
    'tweezer_bottom': 1.8,  # Bullish reversal
    'tweezer_top': -1.8,  # Bearish reversal
    
    # Three soldiers/crows - strong continuation signals
    'three_white_soldiers': 3.0,  # Very strong bullish
    'three_black_crows': -3.0,  # Very strong bearish
}


class ScoringEngine:
    """
    Scoring engine for candlestick patterns.
    
    Calculates scores based on detected patterns and configurable weights.
    """
    
    def __init__(self, pattern_weights: Optional[Dict[str, float]] = None):
        """
        Initialize scoring engine.
        
        Args:
            pattern_weights: Custom pattern weights (uses defaults if not provided)
        """
        self.pattern_weights = pattern_weights or DEFAULT_PATTERN_WEIGHTS.copy()
    
    def get_pattern_weight(self, pattern_type: str) -> float:
        """
        Get weight for a specific pattern type.
        
        Args:
            pattern_type: Pattern type name
        
        Returns:
            Pattern weight (0.0 if pattern not found)
        """
        return self.pattern_weights.get(pattern_type, 0.0)
    
    def set_pattern_weight(self, pattern_type: str, weight: float) -> None:
        """
        Set weight for a specific pattern type.
        
        Args:
            pattern_type: Pattern type name
            weight: New weight value
        """
        self.pattern_weights[pattern_type] = weight
    
    def calculate_pattern_score(self, patterns: List[Dict]) -> float:
        """
        Calculate total score from detected patterns.
        
        Args:
            patterns: List of detected patterns from detect_all_patterns()
        
        Returns:
            Total score (sum of weighted pattern contributions)
        """
        total_score = 0.0
        
        for pattern in patterns:
            pattern_type = pattern.get('type', '')
            weight = self.get_pattern_weight(pattern_type)
            total_score += weight
        
        return total_score
    
    def score_candles(self, candles: List[Dict]) -> Dict:
        """
        Detect patterns and calculate score for candle data.
        
        Args:
            candles: List of candle dictionaries with OHLC data
        
        Returns:
            Dict with 'score', 'patterns', and 'signal' (buy/sell/neutral)
        """
        # Detect all patterns
        patterns = detect_all_patterns(candles)
        
        # Calculate score
        score = self.calculate_pattern_score(patterns)
        
        # Determine signal based on score
        signal = 'neutral'
        if score > 1.0:
            signal = 'buy'
        elif score < -1.0:
            signal = 'sell'
        
        return {
            'score': score,
            'patterns': patterns,
            'signal': signal,
            'pattern_count': len(patterns)
        }
    
    def get_detailed_breakdown(self, candles: List[Dict]) -> Dict:
        """
        Get detailed breakdown of pattern scoring.
        
        Args:
            candles: List of candle dictionaries with OHLC data
        
        Returns:
            Dict with detailed scoring information
        """
        patterns = detect_all_patterns(candles)
        
        pattern_contributions = []
        total_score = 0.0
        
        for pattern in patterns:
            pattern_type = pattern.get('type', '')
            weight = self.get_pattern_weight(pattern_type)
            total_score += weight
            
            pattern_contributions.append({
                'type': pattern_type,
                'weight': weight,
                'candle_index': pattern.get('candle_index', -1)
            })
        
        # Categorize patterns
        bullish_patterns = [p for p in pattern_contributions if p['weight'] > 0]
        bearish_patterns = [p for p in pattern_contributions if p['weight'] < 0]
        neutral_patterns = [p for p in pattern_contributions if p['weight'] == 0]
        
        bullish_score = sum(p['weight'] for p in bullish_patterns)
        bearish_score = sum(p['weight'] for p in bearish_patterns)
        
        return {
            'total_score': total_score,
            'bullish_score': bullish_score,
            'bearish_score': bearish_score,
            'pattern_contributions': pattern_contributions,
            'bullish_patterns': bullish_patterns,
            'bearish_patterns': bearish_patterns,
            'neutral_patterns': neutral_patterns,
            'signal': 'buy' if total_score > 1.0 else ('sell' if total_score < -1.0 else 'neutral')
        }


def create_default_engine() -> ScoringEngine:
    """
    Create a scoring engine with default weights.
    
    Returns:
        ScoringEngine instance with default configuration
    """
    return ScoringEngine()


def score_candles(candles: List[Dict], 
                  pattern_weights: Optional[Dict[str, float]] = None) -> Dict:
    """
    Convenience function to score candles with optional custom weights.
    
    Args:
        candles: List of candle dictionaries with OHLC data
        pattern_weights: Optional custom pattern weights
    
    Returns:
        Dict with 'score', 'patterns', and 'signal'
    """
    engine = ScoringEngine(pattern_weights)
    return engine.score_candles(candles)
