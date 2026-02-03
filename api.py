"""
EquiAlert Stock API - Production Version

Full-featured stock analytics API with:
- Real-time stock quotes
- Historical price data
- Technical indicators (SMA, EMA, RSI, MACD, Bollinger)
- Chart-ready endpoints
- Database persistence
- In-memory caching
- Rate limiting
"""

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
import time
from datetime import datetime
from loguru import logger
import sys

# Configure logging
logger.remove()  # Remove default handler
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO"
)
logger.add(
    "logs/api_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="7 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
    level="DEBUG"
)

from config import config
from database import init_db, engine
from stock_logic import get_stock_price  # Legacy compatibility
from services.cache_manager import cache_manager

# Import routers
from routers import stocks, analytics, charts


# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting EquiAlert Stock API")
    logger.info(f"Environment: {config.ENVIRONMENT}")
    logger.info(f"Database: {config.DATABASE_URL.split('/')[-1]}")
    
    # Initialize database
    init_db()
    logger.info("✅ Database initialized")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down EquiAlert Stock API")
    engine.dispose()
    logger.info("✅ Database connections closed")


# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI app
app = FastAPI(
    title=config.API_TITLE,
    description=config.API_DESCRIPTION,
    version=config.API_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if config.is_development else [
        "http://localhost:5000",
        "http://localhost:5173",
        "https://*.onrender.com",
        "https://*.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.debug(f"{request.method} {request.url.path} - {process_time:.3f}s")
    return response


# Root endpoint
@app.get("/", tags=["root"])
@limiter.limit("60/minute")
def read_root(request: Request):
    """
    API information and available endpoints
    
    ⚠️ This endpoint is monitored by UptimeRobot for uptime tracking
    """
    return {
        "service": config.API_TITLE,
        "status": "running",
        "version": config.API_VERSION,
        "environment": config.ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "endpoints": {
            "/health": "Health check (use for monitoring)",
            "/metrics": "API metrics and cache statistics",
            "/api/v1/stocks/{symbol}/quote": "Get current stock quote",
            "/api/v1/stocks/{symbol}/history": "Get historical OHLCV data",
            "/api/v1/stocks/{symbol}/profile": "Get company profile",
            "/api/v1/analytics/indicators": "Get technical indicators",
            "/api/v1/analytics/compare": "Compare multiple stocks",
            "/api/v1/charts/{symbol}/price": "Price chart data",
            "/api/v1/charts/{symbol}/candlestick": "Candlestick chart data",
            "/api/v1/charts/{symbol}/rsi": "RSI indicator chart",
            "/api/v1/charts/{symbol}/volume": "Volume chart data",
            "/docs": "Interactive API documentation",
            "/redoc": "ReDoc documentation"
        },
        "disclaimer": "Data scraped from public sources. Not for trading or financial advice."
    }


# Health check endpoint (for UptimeRobot and Render)
@app.get("/health", tags=["monitoring"])
def health_check():
    """
    Health check endpoint
    
    Used by:
    - Render for service health monitoring
    - UptimeRobot for uptime tracking
    
    ⚠️ Keep this endpoint lightweight - no heavy scraping!
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "uptime": time.process_time(),
        "environment": config.ENVIRONMENT
    }


# Metrics endpoint
@app.get("/metrics", tags=["monitoring"])
@limiter.limit("30/minute")
def get_metrics(request: Request):
    """
    API metrics and cache statistics
    
    Provides insights into:
    - Cache hit rates
    - Cache sizes
    - System health
    """
    cache_stats = cache_manager.get_stats()
    
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "environment": config.ENVIRONMENT,
        "cache": cache_stats,
        "rate_limits": {
            "general": "60 requests/minute",
            "heavy_endpoints": "30 requests/minute"
        }
    }


# Legacy endpoint for backwards compatibility
@app.get("/stock/{ticker}/{exchange}", tags=["legacy"])
@limiter.limit("60/minute")
def fetch_stock_legacy(request: Request, ticker: str, exchange: str):
    """
    Legacy endpoint (v1.0 compatibility)
    
    ⚠️ Deprecated: Use /api/v1/stocks/{symbol}/quote instead
    """
    try:
        result = get_stock_price(ticker.upper(), exchange.upper())
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        logger.warning(f"Legacy endpoint used: {ticker}:{exchange}")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Include routers with rate limiting
app.include_router(stocks.router)
app.include_router(analytics.router)
app.include_router(charts.router)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if config.is_development else "An error occurred",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=config.is_development
    )
