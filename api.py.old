from fastapi import FastAPI
from stock_logic import get_stock_price

app = FastAPI()

@app.get("/stock/{ticker}/{exchange}")
def fetch_stock(ticker: str, exchange: str):
    return get_stock_price(ticker.upper(), exchange.upper())
