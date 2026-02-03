"""
Scraper factory with lazy initialization and automatic fallback support.
"""

from typing import Optional
from loguru import logger
from .base_scraper import BaseScraper
from .google_scraper import GoogleFinanceScraper
from .yahoo_scraper import YahooFinanceScraper


class ScraperFactory:
    """Factory for creating and managing scraper instances with singleton pattern"""
    
    _google_instance: Optional[GoogleFinanceScraper] = None
    _yahoo_instance: Optional[YahooFinanceScraper] = None
    
    @classmethod
    def get_scraper(cls, source: str = "google") -> Optional[BaseScraper]:
        """
        Get scraper instance (lazy initialization with singleton pattern).
        
        Args:
            source: Data source ("google", "yahoo", or "auto")
            
        Returns:
            BaseScraper instance or None if invalid source
        """
        source_lower = source.lower()
        
        if source_lower == "google":
            if cls._google_instance is None:
                logger.info("Initializing Google Finance scraper...")
                cls._google_instance = GoogleFinanceScraper()
            return cls._google_instance
        
        elif source_lower == "yahoo":
            if cls._yahoo_instance is None:
                logger.info("Initializing Yahoo Finance scraper...")
                cls._yahoo_instance = YahooFinanceScraper()
            return cls._yahoo_instance
        
        elif source_lower == "auto":
            # For "auto" mode, return Google by default
            # The service layer will handle trying both sources
            return cls.get_scraper("google")
        
        else:
            logger.error(f"Invalid scraper source: {source}")
            return None
    
    @classmethod
    def get_alternate_scraper(cls, current_source: str) -> Optional[BaseScraper]:
        """
        Get the alternate scraper for fallback.
        
        Args:
            current_source: Current source that failed
            
        Returns:
            Alternate scraper instance
        """
        if current_source.lower() == "google":
            logger.info("Switching to Yahoo Finance as fallback")
            return cls.get_scraper("yahoo")
        elif current_source.lower() == "yahoo":
            logger.info("Switching to Google Finance as fallback")
            return cls.get_scraper("google")
        else:
            return None
    
    @classmethod
    def reset_instances(cls):
        """Reset singleton instances (useful for testing)"""
        cls._google_instance = None
        cls._yahoo_instance = None
        logger.info("Scraper instances reset")


# Convenience function for backward compatibility
def get_scraper(source: str = "google") -> Optional[BaseScraper]:
    """
    Get scraper instance for the specified source.
    
    Args:
        source: Data source ("google", "yahoo", or "auto")
        
    Returns:
        BaseScraper instance or None
        
    Examples:
        >>> google_scraper = get_scraper("google")
        >>> quote = google_scraper.get_stock_quote("AAPL", "NASDAQ")
        
        >>> yahoo_scraper = get_scraper("yahoo")
        >>> profile = yahoo_scraper.get_stock_profile("RELIANCE", "NSE")
    """
    return ScraperFactory.get_scraper(source)
