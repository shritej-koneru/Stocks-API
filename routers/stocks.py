"""Stock endpoints router"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from loguru import logger

from database import get_db
from services.scraper_service import scraper_service

router = APIRouter(prefix="/api/v1/stocks", tags=["stocks"])


@router.get("/{symbol}/quote")
def get_stock_quote(
    symbol: str,
    exchange: str = Query(..., description="Exchange code (e.g., NASDAQ, NYSE, NSE)"),
    db: Session = Depends(get_db)
):
    """
    Get current stock quote with real-time price, change, volume
    
    Returns:
        {
            "symbol": "AAPL",
            "exchange": "NASDAQ",
            "price": 185.32,
            "change": 2.04,
            "change_percent": 1.12,
            "previous_close": 183.28,
            "volume": 52000000,
            "timestamp": "2026-02-03T09:45:00Z"
        }
    """
    logger.info(f"Quote request: {symbol}:{exchange}")
    
    result = scraper_service.fetch_and_store_quote(db, symbol, exchange)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.get("/{symbol}/history")
def get_stock_history(
    symbol: str,
    exchange: str = Query(..., description="Exchange code"),
    days: int = Query(30, description="Number of days of history", ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get historical OHLCV data from database
    
    Note: Historical data accumulates as the API scrapes prices over time.
    For immediate use, data may be limited.
    """
    logger.info(f"History request: {symbol}:{exchange} ({days} days)")
    
    result = scraper_service.get_historical_data(db, symbol, exchange, days)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.get("/{symbol}/profile")
def get_stock_profile(
    symbol: str,
    exchange: str = Query(..., description="Exchange code"),
    db: Session = Depends(get_db)
):
    """
    Get company profile information
    
    Returns:
        {
            "symbol": "AAPL",
            "exchange": "NASDAQ",
            "name": "Apple Inc.",
            "sector": "Technology",
            "market_cap": 2900000000000,
            "currency": "USD"
        }
    """
    logger.info(f"Profile request: {symbol}:{exchange}")
    
    result = scraper_service.fetch_and_store_profile(db, symbol, exchange)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result
