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
    source: str = Query("google", enum=["google", "yahoo", "auto"], description="Data source: google, yahoo, or auto (tries both)"),
    auto_fallback: bool = Query(True, description="Automatically try alternate source on failure"),
    db: Session = Depends(get_db)
):
    """
    Get current stock quote with real-time price, change, volume
    
    Parameters:
    - source: "google" (default), "yahoo", or "auto" (tries both sources)
    - auto_fallback: If True, automatically tries alternate source on failure
    
    Returns:
        {
            "symbol": "AAPL",
            "exchange": "NASDAQ",
            "price": 185.32,
            "change": 2.04,
            "change_percent": 1.12,
            "previous_close": 183.28,
            "volume": 52000000,
            "timestamp": "2026-02-03T09:45:00Z",
            "source": "google"
        }
    """
    logger.info(f"Quote request: {symbol}:{exchange} (source: {source}, fallback: {auto_fallback})")
    
    result = scraper_service.fetch_and_store_quote(db, symbol, exchange, source, auto_fallback)
    
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
    source: str = Query("google", enum=["google", "yahoo", "auto"], description="Data source"),
    auto_fallback: bool = Query(True, description="Automatically try alternate source on failure"),
    db: Session = Depends(get_db)
):
    """
    Get company profile information
    
    Parameters:
    - source: "google" (default), "yahoo", or "auto"
    - auto_fallback: If True, automatically tries alternate source on failure
    
    Returns:
        {
            "symbol": "AAPL",
            "exchange": "NASDAQ",
            "name": "Apple Inc.",
            "sector": "Technology",
            "market_cap": 2900000000000,
            "currency": "USD",
            "source": "yahoo"
        }
    """
    logger.info(f"Profile request: {symbol}:{exchange} (source: {source})")
    
    result = scraper_service.fetch_and_store_profile(db, symbol, exchange, source, auto_fallback)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result
