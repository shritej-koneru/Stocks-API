"""
Abstract base class for stock data scrapers.
Defines the interface that all scrapers must implement.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime


class BaseScraper(ABC):
    """Abstract base class for stock data scrapers"""
    
    @abstractmethod
    def get_stock_quote(self, symbol: str, exchange: str) -> Optional[Dict[str, Any]]:
        """
        Get current stock quote data.
        
        Args:
            symbol: Stock symbol (e.g., "AAPL", "RELIANCE")
            exchange: Exchange code (e.g., "NASDAQ", "NSE")
            
        Returns:
            Dict with keys: symbol, exchange, price, change, change_percent, 
                           previous_close, volume, timestamp
            None if data cannot be retrieved
        """
        pass
    
    @abstractmethod
    def get_stock_profile(self, symbol: str, exchange: str) -> Optional[Dict[str, Any]]:
        """
        Get company profile information.
        
        Args:
            symbol: Stock symbol
            exchange: Exchange code
            
        Returns:
            Dict with keys: symbol, exchange, name, sector, industry, 
                           market_cap, currency
            None if data cannot be retrieved
        """
        pass
    
    @abstractmethod
    def get_historical_data(
        self, 
        symbol: str, 
        exchange: str, 
        days: int = 30
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get historical OHLCV data.
        
        Args:
            symbol: Stock symbol
            exchange: Exchange code
            days: Number of days of historical data
            
        Returns:
            List of dicts with keys: date, open, high, low, close, volume
            None if data cannot be retrieved
        """
        pass
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the name of this data source (e.g., 'google', 'yahoo')"""
        pass
