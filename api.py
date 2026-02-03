from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from stock_logic import get_stock_price
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(
    title="EquiAlert Stock API",
    description="Microservice for fetching real-time stock prices from Google Finance",
    version="1.0.0"
)

# CORS configuration
origins = [
    "http://localhost:5000",
    "http://localhost:5173",
    "https://*.onrender.com",
    "https://*.devtunnels.ms",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, use specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "service": "EquiAlert Stock API",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "/stock/{ticker}/{exchange}": "Get stock price for a ticker and exchange",
            "/health": "Health check endpoint"
        }
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/stock/{ticker}/{exchange}")
def fetch_stock(ticker: str, exchange: str):
    """
    Fetch stock price from Google Finance
    
    Args:
        ticker: Stock ticker symbol (e.g., RELIANCE, TCS, HDFCBANK)
        exchange: Exchange code (e.g., NSE, BSE, NASDAQ)
    
    Returns:
        JSON with ticker, exchange, and current price
    """
    try:
        result = get_stock_price(ticker.upper(), exchange.upper())
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
