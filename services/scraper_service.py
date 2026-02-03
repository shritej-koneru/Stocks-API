"""Scraper service that integrates with database for persistence"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from loguru import logger

from services.scrapers import get_scraper
from services.scrapers.scraper_factory import ScraperFactory
from database import Stock, PriceHistory
from services.cache_manager import cache_manager


class ScraperService:
    """Service for scraping stock data and persisting to database"""
    
    @staticmethod
    def get_or_create_stock(db: Session, symbol: str, exchange: str) -> Stock:
        """Get existing stock or create new one"""
        stock = db.query(Stock).filter(
            Stock.symbol == symbol.upper(),
            Stock.exchange == exchange.upper()
        ).first()
        
        if stock:
            return stock
        
        # Create new stock entry
        logger.info(f"Creating new stock entry: {symbol}:{exchange}")
        stock = Stock(
            symbol=symbol.upper(),
            exchange=exchange.upper()
        )
        db.add(stock)
        db.commit()
        db.refresh(stock)
        
        return stock
    
    @staticmethod
    def fetch_and_store_quote(
        db: Session, 
        symbol: str, 
        exchange: str,
        source: str = "google",
        auto_fallback: bool = True
    ) -> Dict[str, Any]:
        """
        Fetch current stock quote and store in database
        
        Args:
            db: Database session
            symbol: Stock symbol
            exchange: Exchange code
            source: Data source ("google", "yahoo", or "auto")
            auto_fallback: If True, automatically try alternate source on failure
        
        Returns the scraped data with database integration
        """
        # Check cache first (include source in cache key)
        cached = cache_manager.get_current_price(symbol, exchange, source)
        if cached:
            logger.debug(f"Returning cached quote for {symbol}:{exchange} (source: {source})")
            return cached
        
        # Try primary source
        scraper = get_scraper(source)
        if not scraper:
            return {"error": f"Invalid source: {source}", "symbol": symbol, "exchange": exchange}
        
        quote_data = scraper.get_stock_quote(symbol, exchange)
        used_source = scraper.source_name
        
        # Handle fallback logic
        if quote_data is None and auto_fallback and source != "auto":
            logger.warning(f"[{used_source}] Failed, attempting fallback...")
            alternate_scraper = ScraperFactory.get_alternate_scraper(used_source)
            
            if alternate_scraper:
                quote_data = alternate_scraper.get_stock_quote(symbol, exchange)
                if quote_data:
                    used_source = alternate_scraper.source_name
                    logger.success(f"Fallback to {used_source} successful!")
        
        # Handle "auto" mode - try both sources
        if source == "auto" and quote_data is None:
            logger.info("Auto mode: Trying alternate source...")
            alternate_scraper = ScraperFactory.get_alternate_scraper("google")
            if alternate_scraper:
                quote_data = alternate_scraper.get_stock_quote(symbol, exchange)
                if quote_data:
                    used_source = alternate_scraper.source_name
        
        # If still no data, return error
        if quote_data is None:
            return {"error": "Failed to fetch stock data from all sources", "symbol": symbol, "exchange": exchange}
        
        # Add source to response
        quote_data["source"] = used_source
        
        # Get or create stock
        stock = ScraperService.get_or_create_stock(db, symbol, exchange)
        
        # Update last_source in stock record
        stock.last_source = used_source
        
        # Store price history
        try:
            price_history = PriceHistory(
                stock_id=stock.id,
                timestamp=datetime.utcnow(),
                close=quote_data["price"],
                change=quote_data.get("change"),
                change_percent=quote_data.get("change_percent"),
                previous_close=quote_data.get("previous_close"),
                volume=quote_data.get("volume"),
                data_source=used_source,  # Track which source provided this data
                # For intraday data, we store as both open and close
                open=quote_data["price"],
                high=quote_data["price"],
                low=quote_data["price"]
            )
            db.add(price_history)
            db.commit()
            
            logger.success(f"Stored price history for {symbol}:{exchange} from {used_source}")
        
        
        except Exception as e:
            logger.error(f"Failed to store price history: {e}")
            db.rollback()
        
        # Cache the result (include source in cache key)
        cache_manager.set_current_price(symbol, exchange, quote_data, source)
        
        return quote_data
    
    @staticmethod
    def fetch_and_store_profile(
        db: Session, 
        symbol: str, 
        exchange: str,
        source: str = "google",
        auto_fallback: bool = True
    ) -> Dict[str, Any]:
        """
        Fetch company profile and update stock record
        
        Args:
            db: Database session
            symbol: Stock symbol
            exchange: Exchange code
            source: Data source ("google", "yahoo", or "auto")
            auto_fallback: If True, automatically try alternate source on failure
        
        Returns the profile data
        """
        # Try primary source
        scraper = get_scraper(source)
        if not scraper:
            return {"error": f"Invalid source: {source}", "symbol": symbol, "exchange": exchange}
        
        profile_data = scraper.get_stock_profile(symbol, exchange)
        used_source = scraper.source_name
        
        # Handle fallback
        if profile_data is None and auto_fallback and source != "auto":
            logger.warning(f"[{used_source}] Profile fetch failed, attempting fallback...")
            alternate_scraper = ScraperFactory.get_alternate_scraper(used_source)
            
            if alternate_scraper:
                profile_data = alternate_scraper.get_stock_profile(symbol, exchange)
                if profile_data:
                    used_source = alternate_scraper.source_name
                    logger.success(f"Fallback to {used_source} successful!")
        
        # Handle "auto" mode
        if source == "auto" and profile_data is None:
            alternate_scraper = ScraperFactory.get_alternate_scraper("google")
            if alternate_scraper:
                profile_data = alternate_scraper.get_stock_profile(symbol, exchange)
                if profile_data:
                    used_source = alternate_scraper.source_name
        
        if profile_data is None:
            return {"error": "Failed to fetch profile from all sources", "symbol": symbol, "exchange": exchange}
        
        # Add source to response
        profile_data["source"] = used_source
        
        # Update stock with profile information
        stock = ScraperService.get_or_create_stock(db, symbol, exchange)
        
        try:
            stock.name = profile_data.get("name")
            stock.sector = profile_data.get("sector")
            stock.industry = profile_data.get("industry")
            stock.market_cap = profile_data.get("market_cap")
            stock.currency = profile_data.get("currency", "USD")
            stock.last_source = used_source
            stock.updated_at = datetime.utcnow()
            
            db.commit()
            logger.success(f"Updated profile for {symbol}:{exchange} from {used_source}")
        
        except Exception as e:
            logger.error(f"Failed to update stock profile: {e}")
            db.rollback()
        
        return profile_data
    
    @staticmethod
    def get_historical_data(
        db: Session,
        symbol: str,
        exchange: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get historical price data from database
        
        Args:
            db: Database session
            symbol: Stock symbol
            exchange: Exchange code
            days: Number of days to fetch (default 30)
        
        Returns:
            {
                "symbol": str,
                "exchange": str,
                "interval": str,
                "data": [{"t": timestamp, "o": open, "h": high, "l": low, "c": close, "v": volume}]
            }
        """
        from datetime import timedelta
        
        stock = db.query(Stock).filter(
            Stock.symbol == symbol.upper(),
            Stock.exchange == exchange.upper()
        ).first()
        
        if not stock:
            return {"error": "Stock not found in database"}
        
        # Get price history for the specified period
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        price_records = db.query(PriceHistory).filter(
            PriceHistory.stock_id == stock.id,
            PriceHistory.timestamp >= cutoff_date
        ).order_by(PriceHistory.timestamp.asc()).all()
        
        if not price_records:
            return {
                "symbol": symbol,
                "exchange": exchange,
                "interval": "1d",
                "data": [],
                "message": "No historical data available yet. Data will accumulate as the scraper runs."
            }
        
        # Format data for response
        data = []
        for record in price_records:
            data.append({
                "t": record.timestamp.isoformat() + "Z",
                "o": record.open,
                "h": record.high,
                "l": record.low,
                "c": record.close,
                "v": record.volume
            })
        
        return {
            "symbol": symbol,
            "exchange": exchange,
            "interval": "1d",
            "data": data,
            "count": len(data)
        }


# Global service instance
scraper_service = ScraperService()
