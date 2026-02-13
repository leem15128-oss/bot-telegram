"""Scoring engine for trading signal generation."""
import logging
from typing import List, Optional, Dict, Any
from .market_data import CandleData, market_data
from .config import config

logger = logging.getLogger(__name__)


class TradingSignal:
    """Represents a trading signal."""
    
    def __init__(self, symbol: str, timeframe: str, signal_type: str, 
                 model_type: str, score: float, entry_price: float,
                 stop_loss: float, take_profit: float):
        self.symbol = symbol
        self.timeframe = timeframe
        self.signal_type = signal_type  # 'LONG' or 'SHORT'
        self.model_type = model_type  # 'continuation' or 'reversal'
        self.score = score
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'signal_type': self.signal_type,
            'model_type': self.model_type,
            'score': self.score,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit
        }


class ScoringEngine:
    """Generates and scores trading signals without ML."""
    
    def __init__(self):
        self.min_candles = 50  # Minimum candles needed for analysis
    
    def analyze_symbol(self, symbol: str, timeframe: str) -> Optional[TradingSignal]:
        """Analyze a symbol and generate a signal if conditions are met."""
        # Get candles
        candles = market_data.get_candles(symbol, timeframe, limit=100)
        
        if len(candles) < self.min_candles:
            return None
        
        # Try continuation pattern first
        signal = self._check_continuation_pattern(symbol, timeframe, candles)
        if signal:
            return signal
        
        # Try reversal pattern
        signal = self._check_reversal_pattern(symbol, timeframe, candles)
        if signal:
            return signal
        
        return None
    
    def _check_continuation_pattern(self, symbol: str, timeframe: str, 
                                   candles: List[CandleData]) -> Optional[TradingSignal]:
        """Check for continuation patterns (trend following)."""
        if len(candles) < 20:
            return None
        
        recent = candles[-20:]
        latest = candles[-1]
        
        # Calculate simple moving average
        sma_20 = sum(c.close for c in recent) / len(recent)
        
        # Check for uptrend continuation
        if latest.close > sma_20 * 1.01:  # Price above SMA by 1%
            # Check momentum
            price_change = (latest.close - recent[0].close) / recent[0].close
            
            if price_change > 0.02:  # Positive momentum
                # Calculate score based on strength
                score = min(100, 70 + abs(price_change) * 100)
                
                # Calculate stop loss and take profit
                atr = self._calculate_atr(candles[-14:])
                stop_loss = latest.close - (atr * 2)
                take_profit = latest.close + (atr * 3)
                
                return TradingSignal(
                    symbol=symbol,
                    timeframe=timeframe,
                    signal_type='LONG',
                    model_type='continuation',
                    score=score,
                    entry_price=latest.close,
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
        
        # Check for downtrend continuation
        elif latest.close < sma_20 * 0.99:  # Price below SMA by 1%
            price_change = (latest.close - recent[0].close) / recent[0].close
            
            if price_change < -0.02:  # Negative momentum
                score = min(100, 70 + abs(price_change) * 100)
                
                atr = self._calculate_atr(candles[-14:])
                stop_loss = latest.close + (atr * 2)
                take_profit = latest.close - (atr * 3)
                
                return TradingSignal(
                    symbol=symbol,
                    timeframe=timeframe,
                    signal_type='SHORT',
                    model_type='continuation',
                    score=score,
                    entry_price=latest.close,
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
        
        return None
    
    def _check_reversal_pattern(self, symbol: str, timeframe: str,
                               candles: List[CandleData]) -> Optional[TradingSignal]:
        """Check for reversal patterns (mean reversion)."""
        if len(candles) < 20:
            return None
        
        recent = candles[-20:]
        latest = candles[-1]
        
        # Calculate Bollinger Bands
        sma_20 = sum(c.close for c in recent) / len(recent)
        variance = sum((c.close - sma_20) ** 2 for c in recent) / len(recent)
        std_dev = variance ** 0.5
        
        upper_band = sma_20 + (std_dev * 2)
        lower_band = sma_20 - (std_dev * 2)
        
        # Check for oversold (potential reversal up)
        if latest.close < lower_band:
            # Check for reversal signs
            if latest.close > latest.open:  # Bullish candle
                distance_from_band = (lower_band - latest.close) / latest.close
                score = min(100, 65 + distance_from_band * 200)
                
                atr = self._calculate_atr(candles[-14:])
                stop_loss = latest.close - (atr * 1.5)
                take_profit = sma_20  # Target mean reversion
                
                return TradingSignal(
                    symbol=symbol,
                    timeframe=timeframe,
                    signal_type='LONG',
                    model_type='reversal',
                    score=score,
                    entry_price=latest.close,
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
        
        # Check for overbought (potential reversal down)
        elif latest.close > upper_band:
            if latest.close < latest.open:  # Bearish candle
                distance_from_band = (latest.close - upper_band) / latest.close
                score = min(100, 65 + distance_from_band * 200)
                
                atr = self._calculate_atr(candles[-14:])
                stop_loss = latest.close + (atr * 1.5)
                take_profit = sma_20
                
                return TradingSignal(
                    symbol=symbol,
                    timeframe=timeframe,
                    signal_type='SHORT',
                    model_type='reversal',
                    score=score,
                    entry_price=latest.close,
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
        
        return None
    
    def _calculate_atr(self, candles: List[CandleData], period: int = 14) -> float:
        """Calculate Average True Range."""
        if len(candles) < 2:
            return 0
        
        true_ranges = []
        for i in range(1, len(candles)):
            high = candles[i].high
            low = candles[i].low
            prev_close = candles[i-1].close
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        if not true_ranges:
            return 0
        
        return sum(true_ranges[-period:]) / min(period, len(true_ranges))


# Global scoring engine
scoring_engine = ScoringEngine()
