"""Chart-ready data endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from loguru import logger

from database import get_db
from services.scraper_service import scraper_service
from services.indicators import indicator_service

router = APIRouter(prefix="/api/v1/charts", tags=["charts"])


@router.get("/{symbol}/price")
def get_price_chart(
    symbol: str,
    exchange: str = Query(..., description="Exchange code"),
    days: int = Query(30, description="Number of days", ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get price chart data in Chart.js compatible format
    
    Returns line chart data ready to use with Chart.js or similar libraries
    """
    logger.info(f"Price chart request: {symbol}:{exchange}")
    
    history = scraper_service.get_historical_data(db, symbol, exchange, days)
    
    if "error" in history:
        raise HTTPException(status_code=404, detail=history["error"])
    
    # Format for Chart.js
    labels = []
    data = []
    
    for point in history.get("data", []):
        labels.append(point["t"])
        data.append(point["c"])  # Close price
    
    return {
        "type": "line",
        "symbol": symbol.upper(),
        "labels": labels,
        "datasets": [
            {
                "label": f"{symbol.upper()} Price",
                "data": data,
                "borderColor": "rgb(75, 192, 192)",
                "tension": 0.1
            }
        ]
    }


@router.get("/{symbol}/candlestick")
def get_candlestick_chart(
    symbol: str,
    exchange: str = Query(..., description="Exchange code"),
    days: int = Query(30, description="Number of days", ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get candlestick (OHLC) chart data
    
    Returns data ready for candlestick chart libraries
    """
    logger.info(f"Candlestick chart request: {symbol}:{exchange}")
    
    history = scraper_service.get_historical_data(db, symbol, exchange, days)
    
    if "error" in history:
        raise HTTPException(status_code=404, detail=history["error"])
    
    # Format for candlestick charts
    data = []
    for point in history.get("data", []):
        data.append({
            "x": point["t"],
            "o": point["o"],
            "h": point["h"],
            "l": point["l"],
            "c": point["c"]
        })
    
    return {
        "type": "candlestick",
        "symbol": symbol.upper(),
        "data": data
    }


@router.get("/{symbol}/rsi")
def get_rsi_chart(
    symbol: str,
    exchange: str = Query(..., description="Exchange code"),
    period: int = Query(14, description="RSI period"),
    db: Session = Depends(get_db)
):
    """
    Get RSI indicator chart data with overbought/oversold levels
    
    Returns RSI chart data with standard 70/30 levels
    """
    logger.info(f"RSI chart request: {symbol}:{exchange}")
    
    rsi_data = indicator_service.get_indicator(db, symbol, exchange, "rsi", period)
    
    if "error" in rsi_data:
        raise HTTPException(status_code=400, detail=rsi_data["error"])
    
    return {
        "type": "line",
        "symbol": symbol.upper(),
        "indicator": "RSI",
        "period": period,
        "overbought": 70,
        "oversold": 30,
        "data": rsi_data.get("data", [])
    }


@router.get("/{symbol}/volume")
def get_volume_chart(
    symbol: str,
    exchange: str = Query(..., description="Exchange code"),
    days: int = Query(30, description="Number of days", ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get volume chart data
    
    Returns bar chart data for trading volume
    """
    logger.info(f"Volume chart request: {symbol}:{exchange}")
    
    history = scraper_service.get_historical_data(db, symbol, exchange, days)
    
    if "error" in history:
        raise HTTPException(status_code=404, detail=history["error"])
    
    labels = []
    data = []
    
    for point in history.get("data", []):
        labels.append(point["t"])
        data.append(point["v"])  # Volume
    
    return {
        "type": "bar",
        "symbol": symbol.upper(),
        "labels": labels,
        "datasets": [
            {
                "label": f"{symbol.upper()} Volume",
                "data": data,
                "backgroundColor": "rgba(54, 162, 235, 0.5)"
            }
        ]
    }
