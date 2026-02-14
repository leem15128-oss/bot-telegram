"""
Multi-component scoring engine for trading signals.
Combines trend alignment, structure, momentum, patterns, and trendlines.
"""

import logging
from typing import Dict, List, Tuple, Optional
from bot.candle_patterns import Candle, CandlePatternDetector, calculate_atr
from bot.trendline_detector import TrendlineDetector
import bot.config as config

logger = logging.getLogger(__name__)


class ScoringEngine:
    """
    Scores trading setups using multiple components:
    - Trend alignment (multi-timeframe)
    - Structure (support/resistance, breakout quality)
    - Momentum (volume, price action)
    - Candle patterns
    - Trendline analysis
    - Risk/reward
    """
    
    def __init__(self):
        self.pattern_detector = CandlePatternDetector(
            pin_bar_min_wick_ratio=config.PIN_BAR_MIN_WICK_RATIO,
            momentum_min_body_ratio=config.MOMENTUM_MIN_BODY_RATIO
        )
        self.trendline_detector = TrendlineDetector(
            lookback_bars=config.PIVOT_LOOKBACK_BARS,
            min_touches=config.MIN_TRENDLINE_TOUCHES,
            max_deviation_pct=config.TRENDLINE_MAX_DEVIATION_PCT
        )
        self.weights = config.SCORE_WEIGHTS
    
    def score_trend_alignment(self, trend_30m: str, trend_1h: str, trend_4h: str,
                             direction: str) -> Tuple[float, str]:
        """
        Score multi-timeframe trend alignment.
        
        Args:
            trend_30m: Trend on 30m timeframe ('up', 'down', 'neutral')
            trend_1h: Trend on 1h timeframe
            trend_4h: Trend on 4h timeframe (regime)
            direction: Expected signal direction ('long' or 'short')
        
        Returns:
            Tuple of (score out of 100, reason)
        """
        expected_trend = 'up' if direction == 'long' else 'down'
        score = 0
        aligned = []
        
        # 4h trend is most important (regime)
        if trend_4h == expected_trend:
            score += 50
            aligned.append('4h')
        elif trend_4h == 'neutral':
            score += 25
        
        # 1h trend for setup context
        if trend_1h == expected_trend:
            score += 30
            aligned.append('1h')
        elif trend_1h == 'neutral':
            score += 15
        
        # 30m trend for entry timing
        if trend_30m == expected_trend:
            score += 20
            aligned.append('30m')
        elif trend_30m == 'neutral':
            score += 10
        
        reason = f"aligned_timeframes: {','.join(aligned)}" if aligned else "no_alignment"
        return score, reason
    
    def score_structure(self, current_price: float, nearest_support: Optional[float],
                       nearest_resistance: Optional[float], atr: float,
                       direction: str, volume_ratio: float = 1.0) -> Tuple[float, str]:
        """
        Score structure quality (support/resistance zones, breakout strength).
        
        Args:
            current_price: Current price
            nearest_support: Nearest support level
            nearest_resistance: Nearest resistance level
            atr: Average True Range
            direction: Signal direction
            volume_ratio: Current volume vs average
        
        Returns:
            Tuple of (score out of 100, reason)
        """
        score = 0
        reasons = []
        
        if direction == 'long':
            # For longs, want to be near support or breaking resistance
            if nearest_support:
                distance_to_support = abs(current_price - nearest_support) / atr if atr > 0 else 999
                if distance_to_support < 0.5:
                    score += 40
                    reasons.append('at_support')
                elif distance_to_support < 1.0:
                    score += 25
                    reasons.append('near_support')
            
            if nearest_resistance:
                if current_price > nearest_resistance:
                    score += 40
                    reasons.append('broke_resistance')
                    # Volume confirmation
                    if volume_ratio >= config.MIN_VOLUME_INCREASE_RATIO:
                        score += 20
                        reasons.append('strong_volume')
        
        else:  # short
            # For shorts, want to be near resistance or breaking support
            if nearest_resistance:
                distance_to_resistance = abs(current_price - nearest_resistance) / atr if atr > 0 else 999
                if distance_to_resistance < 0.5:
                    score += 40
                    reasons.append('at_resistance')
                elif distance_to_resistance < 1.0:
                    score += 25
                    reasons.append('near_resistance')
            
            if nearest_support:
                if current_price < nearest_support:
                    score += 40
                    reasons.append('broke_support')
                    # Volume confirmation
                    if volume_ratio >= config.MIN_VOLUME_INCREASE_RATIO:
                        score += 20
                        reasons.append('strong_volume')
        
        score = min(score, 100)
        reason = ','.join(reasons) if reasons else 'no_clear_structure'
        return score, reason
    
    def score_momentum(self, candles: List[Candle], direction: str,
                      recent_bars: int = 5) -> Tuple[float, str]:
        """
        Score price momentum and strength.
        
        Args:
            candles: List of recent candles
            direction: Signal direction
            recent_bars: Number of recent bars to analyze
        
        Returns:
            Tuple of (score out of 100, reason)
        """
        if len(candles) < recent_bars:
            return 50, "insufficient_data"
        
        recent = candles[-recent_bars:]
        score = 0
        
        if direction == 'long':
            # Count bullish candles
            bullish_count = sum(1 for c in recent if c.is_bullish)
            bullish_pct = bullish_count / len(recent)
            
            # Higher closes
            higher_closes = sum(1 for i in range(1, len(recent)) 
                              if recent[i].close > recent[i-1].close)
            
            score = bullish_pct * 60 + (higher_closes / (len(recent) - 1)) * 40
            reason = f"bullish_{bullish_count}/{len(recent)}"
        
        else:  # short
            # Count bearish candles
            bearish_count = sum(1 for c in recent if c.is_bearish)
            bearish_pct = bearish_count / len(recent)
            
            # Lower closes
            lower_closes = sum(1 for i in range(1, len(recent)) 
                             if recent[i].close < recent[i-1].close)
            
            score = bearish_pct * 60 + (lower_closes / (len(recent) - 1)) * 40
            reason = f"bearish_{bearish_count}/{len(recent)}"
        
        return score, reason
    
    def calculate_total_score(self, 
                             trend_30m: str, trend_1h: str, trend_4h: str,
                             candles_30m: List[Candle],
                             current_price: float,
                             direction: str,
                             nearest_support: Optional[float] = None,
                             nearest_resistance: Optional[float] = None,
                             volume_ratio: float = 1.0,
                             entry: Optional[float] = None,
                             stop_loss: Optional[float] = None,
                             take_profit: Optional[float] = None) -> Tuple[float, Dict[str, any]]:
        """
        Calculate total weighted score for a trading setup.
        
        Args:
            trend_30m, trend_1h, trend_4h: Trends on each timeframe
            candles_30m: List of 30m candles (closed)
            current_price: Current price
            direction: Signal direction ('long' or 'short')
            nearest_support: Nearest support level
            nearest_resistance: Nearest resistance level
            volume_ratio: Current volume vs average
            entry, stop_loss, take_profit: For risk/reward calculation
        
        Returns:
            Tuple of (total_score, component_scores_dict)
        """
        component_scores = {}
        
        # 1. Trend alignment
        trend_score, trend_reason = self.score_trend_alignment(
            trend_30m, trend_1h, trend_4h, direction
        )
        component_scores['trend_alignment'] = {
            'score': trend_score,
            'weighted': trend_score * self.weights['trend_alignment'] / 100,
            'reason': trend_reason
        }
        
        # 2. Structure
        atr = calculate_atr(candles_30m, config.ATR_PERIOD)
        structure_score, structure_reason = self.score_structure(
            current_price, nearest_support, nearest_resistance, atr, direction, volume_ratio
        )
        component_scores['structure'] = {
            'score': structure_score,
            'weighted': structure_score * self.weights['structure'] / 100,
            'reason': structure_reason
        }
        
        # 3. Momentum
        momentum_score, momentum_reason = self.score_momentum(candles_30m, direction)
        component_scores['momentum'] = {
            'score': momentum_score,
            'weighted': momentum_score * self.weights['momentum'] / 100,
            'reason': momentum_reason
        }
        
        # 4. Candle patterns
        pattern_score = 50  # Default neutral
        patterns = []
        if len(candles_30m) >= 1:
            nearby_level = nearest_support if direction == 'long' else nearest_resistance
            pattern_score, patterns = self.pattern_detector.score_pattern_confirmation(
                candles_30m, direction, atr, nearby_level
            )
        
        component_scores['candle_patterns'] = {
            'score': pattern_score,
            'weighted': pattern_score * self.weights['candle_patterns'] / 100,
            'patterns': patterns
        }
        
        # 5. Trendline
        trendline_score = 50  # Default neutral
        trendline_reason = "not_analyzed"
        if len(candles_30m) >= config.MIN_CLOSED_CANDLES_FOR_STRUCTURE:
            trendline_score, trendline_reason = self.trendline_detector.score_trendline_alignment(
                candles_30m, current_price, direction
            )
        
        component_scores['trendline'] = {
            'score': trendline_score,
            'weighted': trendline_score * self.weights['trendline'] / 100,
            'reason': trendline_reason
        }
        
        # 6. Risk/reward
        rr_score = 50  # Default neutral
        rr_reason = "not_provided"
        if entry and stop_loss and take_profit:
            risk = abs(entry - stop_loss)
            reward = abs(take_profit - entry)
            rr_ratio = reward / risk if risk > 0 else 0
            
            # Score based on RR ratio
            if rr_ratio >= 3.0:
                rr_score = 100
            elif rr_ratio >= 2.0:
                rr_score = 80
            elif rr_ratio >= 1.5:
                rr_score = 60
            else:
                rr_score = 30
            
            rr_reason = f"rr_{rr_ratio:.2f}"
        
        component_scores['risk_reward'] = {
            'score': rr_score,
            'weighted': rr_score * self.weights['risk_reward'] / 100,
            'reason': rr_reason
        }
        
        # Calculate total weighted score
        total_score = sum(comp['weighted'] for comp in component_scores.values())
        
        return total_score, component_scores
