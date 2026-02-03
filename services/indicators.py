"""Technical indicators computation using pandas and numpy"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from loguru import logger

from database import Stock, PriceHistory, IndicatorCache
from services.cache_manager import cache_manager
import json


class IndicatorService:
    """Service for computing technical indicators from price history"""
    
    @staticmethod
    def get_price_dataframe(db: Session, symbol: str, exchange: str, days: int = 365) -> Optional[pd.DataFrame]:
        """Get price history as pandas DataFrame"""
        stock = db.query(Stock).filter(
            Stock.symbol == symbol.upper(),
            Stock.exchange == exchange.upper()
        ).first()
        
        if not stock:
            return None
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        price_records = db.query(PriceHistory).filter(
            PriceHistory.stock_id == stock.id,
            PriceHistory.timestamp >= cutoff_date
        ).order_by(PriceHistory.timestamp.asc()).all()
        
        if not price_records:
            return None
        
        # Convert to DataFrame
        data = []
        for record in price_records:
            data.append({
                'timestamp': record.timestamp,
                'open': record.open,
                'high': record.high,
                'low': record.low,
                'close': record.close,
                'volume': record.volume
            })
        
        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        return df
    
    @staticmethod
    def calculate_sma(prices: pd.Series, period: int) -> pd.Series:
        """Calculate Simple Moving Average"""
        return prices.rolling(window=period).mean()
    
    @staticmethod
    def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return prices.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    @staticmethod
    def calculate_bollinger_bands(prices: pd.Series, period: int = 20, std_dev: int = 2) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands"""
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return {
            'upper': upper_band,
            'middle': sma,
            'lower': lower_band
        }
    
    @staticmethod
    def get_indicator(
        db: Session,
        symbol: str,
        exchange: str,
        indicator_type: str,
        period: int = 14,
        interval: str = "1d"
    ) -> Dict[str, Any]:
        """
        Get technical indicator with caching
        
        Args:
            db: Database session
            symbol: Stock symbol
            exchange: Exchange code
            indicator_type: Type of indicator (sma, ema, rsi, macd, bollinger)
            period: Period for calculation
            interval: Time interval
        
        Returns:
            {
                "symbol": str,
                "indicator_type": str,
                "period": int,
                "data": [{"t": timestamp, "value": float}] or {"macd": [], "signal": [], "histogram": []}
            }
        """
        # Check cache first
        cached = cache_manager.get_indicator(symbol, indicator_type, period, interval)
        if cached:
            logger.debug(f"Cache hit for {symbol} {indicator_type}-{period}")
            return cached
        
        # Get price data
        df = IndicatorService.get_price_dataframe(db, symbol, exchange)
        
        if df is None or len(df) < period:
            return {
                "error": f"Insufficient data for {indicator_type} calculation. Need at least {period} data points.",
                "symbol": symbol,
                "indicator_type": indicator_type
            }
        
        # Calculate indicator
        result = {
            "symbol": symbol.upper(),
            "exchange": exchange.upper(),
            "indicator_type": indicator_type,
            "period": period,
            "interval": interval
        }
        
        try:
            if indicator_type.lower() == "sma":
                sma = IndicatorService.calculate_sma(df['close'], period)
                result["data"] = [
                    {"t": idx.isoformat() + "Z", "value": float(val)}
                    for idx, val in sma.dropna().items()
                ]
            
            elif indicator_type.lower() == "ema":
                ema = IndicatorService.calculate_ema(df['close'], period)
                result["data"] = [
                    {"t": idx.isoformat() + "Z", "value": float(val)}
                    for idx, val in ema.dropna().items()
                ]
            
            elif indicator_type.lower() == "rsi":
                rsi = IndicatorService.calculate_rsi(df['close'], period)
                result["data"] = [
                    {"t": idx.isoformat() + "Z", "value": float(val)}
                    for idx, val in rsi.dropna().items()
                ]
            
            elif indicator_type.lower() == "macd":
                macd_data = IndicatorService.calculate_macd(df['close'])
                result["data"] = {
                    "macd": [
                        {"t": idx.isoformat() + "Z", "value": float(val)}
                        for idx, val in macd_data['macd'].dropna().items()
                    ],
                    "signal": [
                        {"t": idx.isoformat() + "Z", "value": float(val)}
                        for idx, val in macd_data['signal'].dropna().items()
                    ],
                    "histogram": [
                        {"t": idx.isoformat() + "Z", "value": float(val)}
                        for idx, val in macd_data['histogram'].dropna().items()
                    ]
                }
            
            elif indicator_type.lower() == "bollinger":
                bb = IndicatorService.calculate_bollinger_bands(df['close'], period)
                result["data"] = {
                    "upper": [
                        {"t": idx.isoformat() + "Z", "value": float(val)}
                        for idx, val in bb['upper'].dropna().items()
                    ],
                    "middle": [
                        {"t": idx.isoformat() + "Z", "value": float(val)}
                        for idx, val in bb['middle'].dropna().items()
                    ],
                    "lower": [
                        {"t": idx.isoformat() + "Z", "value": float(val)}
                        for idx, val in bb['lower'].dropna().items()
                    ]
                }
            
            else:
                return {"error": f"Unknown indicator type: {indicator_type}"}
            
            # Cache the result
            cache_manager.set_indicator(symbol, indicator_type, period, interval, result)
            
            logger.success(f"Calculated {indicator_type}-{period} for {symbol}:{exchange}")
            return result
        
        except Exception as e:
            logger.error(f"Error calculating {indicator_type}: {e}")
            return {"error": f"Failed to calculate {indicator_type}: {str(e)}"}


# Global service instance
indicator_service = IndicatorService()
