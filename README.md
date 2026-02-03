# EquiAlert Stock API

A full-featured stock analytics API providing real-time quotes, historical data, technical indicators, and chart-ready endpoints. Built with FastAPI and powered by **dual data sources** (Google Finance & Yahoo Finance) with automatic fallback for maximum reliability.

## 🌟 Features

- ✅ **Dual Data Sources** - Google Finance (web scraping) + Yahoo Finance (yfinance library)
- ✅ **Automatic Fallback** - If one source fails, automatically tries the alternate
- ✅ **Real-time Stock Quotes** - Current prices with change %, volume, and market data
- ✅ **Historical Data** - OHLCV time series stored in database
- ✅ **Technical Indicators** - SMA, EMA, RSI, MACD, Bollinger Bands
- ✅ **Chart-Ready Endpoints** - JSON optimized for Chart.js and TradingView
- ✅ **Stock Comparison** - Side-by-side analysis of multiple stocks
- ✅ **Database Persistence** - SQLite (local) / PostgreSQL (production)
- ✅ **In-Memory Caching** - 5-minute cache for quotes, 1-hour for historical data
- ✅ **Rate Limiting** - 60 requests/minute per IP
- ✅ **Structured Logging** - Loguru with file rotation
- ✅ **Production Ready** - Render-optimized with UptimeRobot support

## 🏗️ Architecture

```
EquiAlert Stock API
├── FastAPI Application (api.py)
├── Dual Data Sources
│   ├── Google Finance Scraper (web scraping, free)
│   └── Yahoo Finance Scraper (yfinance library, better data)
├── Database Layer (SQLAlchemy)
│   ├── Stock (symbol, exchange, profile, last_source)
│   ├── PriceHistory (OHLCV data + data_source tracking)
│   ├── IndicatorCache (computed indicators)
│   └── MarketSnapshot (market movers)
├── Services
│   ├── scrapers/ (modular scraper architecture)
│   │   ├── base_scraper.py (abstract interface)
│   │   ├── google_scraper.py (Google Finance implementation)
│   │   ├── yahoo_scraper.py (Yahoo Finance with lazy loading)
│   │   ├── symbol_mapper.py (exchange format conversion)
│   │   └── scraper_factory.py (factory + fallback logic)
│   ├── scraper_service.py (DB integration + fallback)
│   ├── cache_manager.py (In-memory TTL cache)
│   └── indicators.py (Technical analysis)
└── Routers (Versioned API /api/v1)
    ├── stocks.py (Quote, History, Profile)
    ├── analytics.py (Indicators, Comparison)
    └── charts.py (Chart-ready data)
```

## 🚀 Tech Stack

- **FastAPI** 0.128.0 - Modern async web framework
- **SQLAlchemy** 2.0.25 - ORM for database operations
- **yfinance** 1.1.0 - Yahoo Finance API wrapper (lazy loaded)
- **Pandas** 2.2.0 - Data manipulation for indicators
- **NumPy** 1.26.3 - Numerical computations
- **Loguru** 0.7.2 - Structured logging
- **slowapi** 0.1.9 - Rate limiting middleware
- **cachetools** 5.3.2 - In-memory caching
- **Beautiful Soup 4** 4.14.3 - HTML parsing (Google Finance)
- **Uvicorn** 0.40.0 - ASGI server

## 📚 API Endpoints

### Core Endpoints

#### `GET /`
Service information and endpoint listing

#### `GET /health`
Health check for monitoring (UptimeRobot, Render)
- ⚠️ Lightweight - no heavy operations
- Used for uptime tracking

#### `GET /metrics`
API metrics and cache statistics

### Stock Data (`/api/v1/stocks`)

#### `GET /api/v1/stocks/{symbol}/quote?exchange={exchange}&source={source}`
Get current stock quote with real-time data

**Parameters:**
- `symbol`: Stock symbol (AAPL, MSFT, RELIANCE, etc.)
- `exchange`: Exchange code (NASDAQ, NYSE, NSE, BSE)
- `source`: Data source - **"google"** (default), **"yahoo"**, or **"auto"** (tries both)
- `auto_fallback`: Automatically try alternate source on failure (default: true)

**Data Source Comparison:**

| Feature | Google Finance | Yahoo Finance |
|---------|---------------|---------------|
| Speed | ⚡ Faster | 🐌 Slower |
| Reliability | 🔶 Moderate | ✅ High |
| Data Completeness | ⚠️ Often has nulls | ✅ Complete data |
| Volume | ❌ Often null | ✅ Always present |
| Market Cap | ❌ Often null | ✅ Always present |
| Rate Limits | ✅ Generous | ⚠️ Stricter |
| Historical Data | ❌ Not available | ✅ Available |

**Recommendation:** Use `source=yahoo` for better data quality, or `source=auto` for maximum reliability.

**Example:**
```bash
# Yahoo Finance (recommended - better data)
curl "http://localhost:8000/api/v1/stocks/AAPL/quote?exchange=NASDAQ&source=yahoo"

# Google Finance (faster, but may have null values)
curl "http://localhost:8000/api/v1/stocks/AAPL/quote?exchange=NASDAQ&source=google"

# Auto mode (tries both sources)
curl "http://localhost:8000/api/v1/stocks/AAPL/quote?exchange=NASDAQ&source=auto"
```

**Response (Yahoo):**
```json
{
  "symbol": "AAPL",
  "exchange": "NASDAQ",
  "price": 270.01,
  "change": 10.53,
  "change_percent": 4.05812,
  "previous_close": 259.48,
  "volume": 72890096,
  "timestamp": "2026-02-03T10:30:00Z",
  "source": "yahoo"
}
```

**Response (Google):**
```json
{
  "symbol": "AAPL",
  "exchange": "NASDAQ",
  "price": 269.96,
  "change": null,
  "change_percent": 0.67,
  "previous_close": 268.16,
  "volume": null,
  "timestamp": "2026-02-03T10:30:00Z",
  "source": "google"
}
```

#### `GET /api/v1/stocks/{symbol}/history?exchange={exchange}&days=30`
Get historical OHLCV data

**Parameters:**
- `days`: Number of days of history (1-365)

**Response:**
```json
{
  "symbol": "AAPL",
  "exchange": "NASDAQ",
  "interval": "1d",
  "data": [
    {
      "t": "2026-01-15T00:00:00Z",
      "o": 265.5,
      "h": 268.2,
      "l": 264.8,
      "c": 267.9,
      "v": 48500000
    }
  ],
  "count": 30
}
```

#### `GET /api/v1/stocks/{symbol}/profile?exchange={exchange}&source={source}`
Get company profile information

**Parameters:**
- `source`: Data source - "google", "yahoo", or "auto"

**Response (Yahoo - Complete Data):**
```json
{
  "symbol": "AAPL",
  "exchange": "NASDAQ",
  "name": "Apple Inc.",
  "sector": "Technology",
  "industry": "Consumer Electronics",
  "market_cap": 3968587005952,
  "currency": "USD",
  "source": "yahoo"
}
```

**Response (Google - May Have Nulls):**
```json
{
  "symbol": "AAPL",
  "exchange": "NASDAQ",
  "name": "Apple Inc",
  "sector": "technology",
  "industry": null,
  "market_cap": null,
  "currency": "USD",
  "source": "google"
}
```

### Analytics (`/api/v1/analytics`)

#### `GET /api/v1/analytics/indicators`
Get technical indicators

**Parameters:**
- `symbol`, `exchange`: Stock identification
- `types`: Comma-separated (sma,ema,rsi,macd,bollinger)
- `period`: Calculation period (default: 14)

**Example:**
```bash
curl "http://localhost:8000/api/v1/analytics/indicators?symbol=AAPL&exchange=NASDAQ&types=sma,rsi&period=14"
```

**Response:**
```json
{
  "symbol": "AAPL",
  "indicators": {
    "sma": {
      "data": [{"t": "2026-02-01", "value": 265.4}]
    },
    "rsi": {
      "data": [{"t": "2026-02-01", "value": 62.3}]
    }
  }
}
```

#### `GET /api/v1/analytics/compare`
Compare multiple stocks

**Parameters:**
- `symbols`: Comma-separated symbols (max 10)
- `exchange`: Common exchange
- `source`: Data source - "google", "yahoo", or "auto"

**Example:**
```bash
curl "http://localhost:8000/api/v1/analytics/compare?symbols=AAPL,MSFT,GOOGL&exchange=NASDAQ&source=yahoo"
```

**Response:**
```json
{
  "exchange": "NASDAQ",
  "stocks": {
    "AAPL": {
      "price": 270.01,
      "change": 10.53,
      "change_percent": 4.05812,
      "volume": 72890096,
      "source": "yahoo"
    },
    "MSFT": {
      "price": 423.37,
      "change": -6.92,
      "change_percent": -1.60822,
      "volume": 41784456,
      "source": "yahoo"
    },
    "GOOGL": {
      "price": 343.69,
      "change": 5.457,
      "change_percent": 1.61339,
      "volume": 31667686,
      "source": "yahoo"
    }
  },
  "count": 3
}
```

### Charts (`/api/v1/charts`)

#### `GET /api/v1/charts/{symbol}/price`
Price line chart data (Chart.js ready)

#### `GET /api/v1/charts/{symbol}/candlestick`
OHLC candlestick chart data

#### `GET /api/v1/charts/{symbol}/rsi`
RSI indicator chart with overbought/oversold levels

#### `GET /api/v1/charts/{symbol}/volume`
Volume bar chart data

## 🛠️ Local Development

### Installation

1. **Clone repository:**
```bash
git clone https://github.com/your-username/Stocks-API.git
cd Stocks-API
```

2. **Create virtual environment:**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Setup environment:**
```bash
cp .env.example .env
# Edit .env with your settings
```

5. **Initialize database:**
```bash
python database.py
```

6. **Run server:**
```bash
uvicorn api:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

### Interactive Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Database

- **Local**: Uses SQLite (`stock_data.db`)
- **Production**: Uses PostgreSQL (configured via `DATABASE_URL`)

Historical data accumulates as the API runs. The scraper stores each price fetch in the database.

## 📦 Deployment to Render

### Prerequisites

1. GitHub repository with your code
2. Render account ([render.com](https://render.com))
3. (Optional) UptimeRobot account for monitoring

### Deployment Steps

#### Option 1: Using render.yaml (Recommended)

1. **Push to GitHub:**
```bash
git push origin main
```

2. **Connect to Render:**
   - Go to Render Dashboard
   - "New" → "Web Service"
   - Connect your GitHub repository
   - Render auto-detects `render.yaml` ✅

3. **Deploy:**
   - Click "Create Web Service"
   - Render builds and deploys automatically

#### Option 2: Manual Setup

1. Create new Web Service
2. Configure:
   - **Name**: `equialert-stock-api`
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn api:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/health`

### Environment Variables (Render)

Set in Render dashboard:
```
ENVIRONMENT=production
DATABASE_URL=<postgresql-connection-string>  # Auto-provided by Render if you add PostgreSQL
```

### Add PostgreSQL (Optional but Recommended)

1. In Render dashboard, add "PostgreSQL" database
2. Link it to your web service
3. Render automatically sets `DATABASE_URL`

### 🔁 UptimeRobot Setup (Prevent Cold Starts)

1. **Create monitor on UptimeRobot:**
   - Type: HTTP(s)
   - URL: `https://your-api.onrender.com/health`
   - Interval: 5 minutes
   - Method: GET

2. **Important:**
   - ✅ Use `/health` endpoint (lightweight)
   - ❌ Don't ping heavy endpoints like `/stock/` (wastes resources)

3. **Expected behavior:**
   - **Mostly awake** (~18-20 hours/day)
   - **Occasional cold starts** (20-60 seconds) when UptimeRobot interval misses

⚠️ **Note**: Free tier has limitations. Render may still sleep after prolonged inactivity.

## 📊 Testing

### Local Testing

```bash
# Root endpoint
curl http://localhost:8000

# Health check
curl http://localhost:8000/health

# Stock quote (v1 API)
curl "http://localhost:8000/api/v1/stocks/AAPL/quote?exchange=NASDAQ"

# Historical data
curl "http://localhost:8000/api/v1/stocks/AAPL/history?exchange=NASDAQ&days=30"

# Technical indicators
curl "http://localhost:8000/api/v1/analytics/indicators?symbol=AAPL&exchange=NASDAQ&types=sma,rsi&period=14"

# Compare stocks
curl "http://localhost:8000/api/v1/analytics/compare?symbols=AAPL,MSFT&exchange=NASDAQ"

# Legacy endpoint (backwards compatible)
curl http://localhost:8000/stock/AAPL/NASDAQ
```

### Thunder Client / Postman

Import these requests:

**Quote:**
- Method: GET
- URL: `{{baseUrl}}/api/v1/stocks/AAPL/quote?exchange=NASDAQ`

**Indicators:**
- Method: GET
- URL: `{{baseUrl}}/api/v1/analytics/indicators?symbol=AAPL&exchange=NASDAQ&types=sma,ema,rsi&period=14`

## 🔌 Integration Examples

### Python
```python
import requests

API_URL = "https://your-api.onrender.com"

# Get stock quote
response = requests.get(f"{API_URL}/api/v1/stocks/AAPL/quote", params={"exchange": "NASDAQ"})
data = response.json()
print(f"AAPL Price: ${data['price']}")

# Get indicators
response = requests.get(f"{API_URL}/api/v1/analytics/indicators", params={
    "symbol": "AAPL",
    "exchange": "NASDAQ",
    "types": "sma,rsi",
    "period": 14
})
indicators = response.json()
```

### JavaScript / Node.js
```javascript
const API_URL = "https://your-api.onrender.com";

// Get stock quote
const response = await fetch(`${API_URL}/api/v1/stocks/AAPL/quote?exchange=NASDAQ`);
const data = await response.json();
console.log(`AAPL Price: $${data.price}`);

// Get chart data
const chartResponse = await fetch(`${API_URL}/api/v1/charts/AAPL/price?exchange=NASDAQ&days=30`);
const chartData = await chartResponse.json();
// Use chartData with Chart.js
```

### React
```jsx
import { useState, useEffect } from 'react';

function StockQuote() {
  const [quote, setQuote] = useState(null);
  
  useEffect(() => {
    fetch('https://your-api.onrender.com/api/v1/stocks/AAPL/quote?exchange=NASDAQ')
      .then(res => res.json())
      .then(data => setQuote(data));
  }, []);
  
  return quote && (
    <div>
      <h2>{quote.symbol}: ${quote.price}</h2>
      <p>Change: {quote.change_percent}%</p>
    </div>
  );
}
```

## 🎯 Performance & Limits

### Caching
- **Current Prices**: 5 minutes TTL
- **Historical Data**: 1 hour TTL
- **Indicators**: 1 hour TTL
- **Cache Type**: In-memory (cachetools)

### Rate Limiting
- **General Endpoints**: 60 requests/minute per IP
- **Metrics Endpoint**: 30 requests/minute per IP
- **Implementation**: slowapi middleware

### Response Times
- **Cached Data**: <50ms
- **Fresh Scrape**: 500ms - 2s
- **Indicators Calculation**: 200ms - 1s
- **Cold Start (Render Free)**: 20-60 seconds

## 🔍 Monitoring & Logs

### View Logs (Render)
1. Go to Render dashboard
2. Select your service
3. Click "Logs" tab

### Log Levels
- `INFO`: General operations
- `DEBUG`: Detailed cache/database operations
- `WARNING`: Cache misses, retries
- `ERROR`: Failed scrapes, exceptions
- `SUCCESS`: Successful operations

### Log Files (Local)
Logs are stored in `logs/` directory with daily rotation:
```
logs/api_2026-02-03.log
logs/api_2026-02-04.log
```

## 🌍 Supported Exchanges

- **US**: NASDAQ, NYSE, AMEX
- **India**: NSE, BSE
- **UK**: LSE
- **Europe**: FRA (Frankfurt), PAR (Paris), AMS (Amsterdam)
- **Asia**: JPX/TSE (Tokyo), HKG (Hong Kong), SHA/SHE (China)
- **Other**: TSX (Toronto), ASX (Australia), and more

### Symbol Format Conversion

The API automatically converts between Google Finance and Yahoo Finance symbol formats:

| Exchange | Google Format | Yahoo Format | Example |
|----------|--------------|--------------|---------|
| NSE (India) | `RELIANCE:NSE` | `RELIANCE.NS` | Indian stocks |
| BSE (India) | `TCS:BSE` | `TCS.BO` | Bombay Exchange |
| NASDAQ | `AAPL:NASDAQ` | `AAPL` | US stocks (no suffix) |
| NYSE | `IBM:NYSE` | `IBM` | US stocks |
| London | `BP:LON` | `BP.L` | UK stocks |
| Frankfurt | `SAP:FRA` | `SAP.DE` | German stocks |
| Tokyo | `SONY:JPX` | `SONY.T` | Japanese stocks |

**Note:** You always use Google Finance format in API requests. The conversion happens automatically when using Yahoo Finance as the data source.

## 📊 Data Source Selection Guide

### When to Use Google Finance (`source=google`):
- ✅ Need faster response times
- ✅ Making many requests (less strict rate limits)
- ✅ OK with occasional null values
- ✅ Only need current price and basic data

### When to Use Yahoo Finance (`source=yahoo`):
- ✅ Need complete data (volume, market cap, etc.)
- ✅ Need industry and detailed sector information
- ✅ Need historical data (Google doesn't provide)
- ✅ Data quality is more important than speed
- ✅ Building financial analysis tools

### When to Use Auto Mode (`source=auto`):
- ✅ Maximum reliability required
- ✅ Production applications
- ✅ Can tolerate slightly higher latency
- ✅ Want automatic fallback without client-side logic

### Fallback Behavior:
With `auto_fallback=true` (default):
1. Tries primary source (google or yahoo)
2. If primary fails → automatically tries alternate source
3. Returns data from whichever source succeeds
4. Response includes `"source"` field showing which source provided data

## ⚠️ Important Disclaimers

### Data Disclaimer
> **This API uses free data sources (Google Finance web scraping and Yahoo Finance unofficial API). Data may be delayed and should NOT be used for trading or financial advice.**

### Scraping Considerations
1. **Rate Limits**: 
   - Google Finance: More lenient, but aggressive scraping may cause IP blocks
   - Yahoo Finance: Stricter rate limits (recommend 20-30 req/min max)
2. **Data Delays**: Both sources typically have 15-20 minute delays
3. **Reliability**: Free sources may have downtime or structure changes
4. **Production Use**: For production trading systems, use official paid APIs (Alpha Vantage, Polygon, etc.)

### Render Free Tier Limitations
- **Sleep**: Service sleeps after 15 min inactivity
- **Cold Start**: 20-60 seconds to wake up
- **Hours**: 750 hours/month (can exceed with UptimeRobot)
- **Database**: 1GB PostgreSQL storage
- **Memory**: 512MB RAM (yfinance lazy-loaded to optimize)

For production use, consider:
- Render Starter plan ($7/month) - No sleep
- Paid data API for guaranteed reliability
- PostgreSQL cleanup for long-term data storage

## License

MIT License - Part of EquiAlert project

## Support

For issues or questions, open an issue in the main EquiAlert repository.
