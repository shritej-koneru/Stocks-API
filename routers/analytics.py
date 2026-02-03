"""Analytics and indicators router"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from loguru import logger

from database import get_db
from services.indicators import indicator_service

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/indicators")
def get_indicators(
    symbol: str = Query(..., description="Stock symbol"),
    exchange: str = Query(..., description="Exchange code"),
    types: str = Query(..., description="Comma-separated indicator types (sma,ema,rsi,macd,bollinger)"),
    period: int = Query(14, description="Period for calculation", ge=2, le=200),
    interval: str = Query("1d", description="Time interval"),
    db: Session = Depends(get_db)
):
    """
    Get technical indicators for a stock
    
    Supported indicators:
    - sma: Simple Moving Average
    - ema: Exponential Moving Average
    - rsi: Relative Strength Index
    - macd: Moving Average Convergence Divergence
    - bollinger: Bollinger Bands
    
    Example: /api/v1/analytics/indicators?symbol=AAPL&exchange=NASDAQ&types=sma,rsi&period=14
    """
    logger.info(f"Indicators request: {symbol}:{exchange} - {types}")
    
    indicator_types = [t.strip().lower() for t in types.split(",")]
    results = {}
    errors = []
    
    for indicator_type in indicator_types:
        result = indicator_service.get_indicator(
            db, symbol, exchange, indicator_type, period, interval
        )
        
        if "error" in result:
            errors.append({indicator_type: result["error"]})
        else:
            results[indicator_type] = result
    
    if errors and not results:
        raise HTTPException(status_code=400, detail={"errors": errors})
    
    response = {
        "symbol": symbol.upper(),
        "exchange": exchange.upper(),
        "period": period,
        "interval": interval,
        "indicators": results
    }
    
    if errors:
        response["errors"] = errors
    
    return response


@router.get("/compare")
def compare_stocks(
    symbols: str = Query(..., description="Comma-separated stock symbols (e.g., AAPL,MSFT,GOOGL)"),
    exchange: str = Query(..., description="Exchange code"),
    db: Session = Depends(get_db)
):
    """
    Compare multiple stocks side-by-side
    
    Returns current price, change, and basic metrics for each stock
    """
    from services.scraper_service import scraper_service
    
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    logger.info(f"Compare request: {symbol_list} on {exchange}")
    
    if len(symbol_list) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 stocks for comparison")
    
    results = {}
    
    for symbol in symbol_list:
        try:
            quote = scraper_service.fetch_and_store_quote(db, symbol, exchange)
            if "error" not in quote:
                results[symbol] = {
                    "price": quote.get("price"),
                    "change": quote.get("change"),
                    "change_percent": quote.get("change_percent"),
                    "volume": quote.get("volume")
                }
        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
            results[symbol] = {"error": str(e)}
    
    return {
        "exchange": exchange.upper(),
        "stocks": results,
        "count": len(results)
    }
