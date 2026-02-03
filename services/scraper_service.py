"""Scraper service that integrates with database for persistence"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from loguru import logger

from stock_logic import scraper
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
    def fetch_and_store_quote(db: Session, symbol: str, exchange: str) -> Dict[str, Any]:
        """
        Fetch current stock quote and store in database
        
        Returns the scraped data with database integration
        """
        # Check cache first
        cached = cache_manager.get_current_price(symbol, exchange)
        if cached:
            logger.debug(f"Returning cached quote for {symbol}:{exchange}")
            return cached
        
        # Scrape fresh data
        quote_data = scraper.get_stock_quote(symbol, exchange)
        
        if "error" in quote_data:
            return quote_data
        
        # Get or create stock
        stock = ScraperService.get_or_create_stock(db, symbol, exchange)
        
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
                # For intraday data, we store as both open and close
                # Later we can aggregate these into daily OHLC
                open=quote_data["price"],
                high=quote_data["price"],
                low=quote_data["price"]
            )
            db.add(price_history)
            db.commit()
            
            logger.success(f"Stored price history for {symbol}:{exchange} at ")
        
        except Exception as e:
            logger.error(f"Failed to store price history: {e}")
            db.rollback()
        
        # Cache the result
        cache_manager.set_current_price(symbol, exchange, quote_data)
        
        return quote_data
    
    @staticmethod
    def fetch_and_store_profile(db: Session, symbol: str, exchange: str) -> Dict[str, Any]:
        """
        Fetch company profile and update stock record
        
        Returns the profile data
        """
        profile_data = scraper.get_stock_profile(symbol, exchange)
        
        if "error" in profile_data:
            return profile_data
        
        # Update stock with profile information
        stock = ScraperService.get_or_create_stock(db, symbol, exchange)
        
        try:
            stock.name = profile_data.get("name")
            stock.sector = profile_data.get("sector")
            stock.industry = profile_data.get("industry")
            stock.market_cap = profile_data.get("market_cap")
            stock.currency = profile_data.get("currency", "USD")
            stock.updated_at = datetime.utcnow()
            
            db.commit()
            logger.success(f"Updated profile for {symbol}:{exchange}")
        
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
