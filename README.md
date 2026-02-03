# EquiAlert Stock API

A microservice for fetching real-time stock prices from Google Finance using web scraping.

## Features

- ✅ Real-time stock price fetching from Google Finance
- ✅ Support for multiple exchanges (NSE, BSE, NASDAQ, etc.)
- ✅ Fast and lightweight Python FastAPI service
- ✅ RESTful API with automatic OpenAPI documentation
- ✅ CORS enabled for frontend integration
- ✅ Health check endpoint for monitoring

## Tech Stack

- **FastAPI**: Modern, fast web framework
- **Beautiful Soup 4**: HTML parsing and web scraping
- **Requests**: HTTP library
- **Uvicorn**: ASGI server

## API Endpoints

### `GET /`
Service information and available endpoints

**Response:**
```json
{
  "service": "EquiAlert Stock API",
  "status": "running",
  "version": "1.0.0",
  "endpoints": {...}
}
```

### `GET /health`
Health check endpoint for monitoring

**Response:**
```json
{
  "status": "healthy"
}
```

### `GET /stock/{ticker}/{exchange}`
Fetch current stock price

**Parameters:**
- `ticker` (path): Stock ticker symbol (e.g., RELIANCE, TCS, INFY)
- `exchange` (path): Exchange code (e.g., NSE, BSE, NASDAQ)

**Example:**
```bash
curl https://your-api.onrender.com/stock/RELIANCE/NSE
```

**Response:**
```json
{
  "ticker": "RELIANCE",
  "exchange": "NSE",
  "price": 2450.75
}
```

**Error Response:**
```json
{
  "error": "Invalid ticker or exchange"
}
```

## Local Development

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Copy environment file:
```bash
cp .env.example .env
```

3. Run the server:
```bash
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

### Interactive Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Deployment to Render

### Option 1: Using render.yaml (Recommended)

1. Push code to GitHub
2. Connect repository to Render
3. Render will automatically detect `render.yaml` and deploy

### Option 2: Manual Setup

1. Create new Web Service on Render
2. Select "Python" runtime
3. Configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/health`

### Environment Variables

Set in Render dashboard:
- `ENVIRONMENT=production`
- `PORT` (automatically set by Render)

## Testing

Test the API locally:

```bash
# Test root endpoint
curl http://localhost:8000

# Test health check
curl http://localhost:8000/health

# Test stock price fetch
curl http://localhost:8000/stock/TCS/NSE

# Test with error
curl http://localhost:8000/stock/INVALID/NSE
```

## Integration with Main Application

Update your main API's environment variables:

```env
STOCK_API_URL=https://equialert-stock-api.onrender.com
```

Then call from your Node.js backend:

```javascript
const stockApiUrl = process.env.STOCK_API_URL || 'http://localhost:8000';
const response = await fetch(`${stockApiUrl}/stock/RELIANCE/NSE`);
const data = await response.json();
```

## Performance

- **Cold Start**: ~2-3 seconds (Render free tier)
- **Warm Request**: <500ms per stock price fetch
- **Concurrent Requests**: Supports multiple simultaneous requests

## Monitoring

Check service health:
```bash
curl https://your-api.onrender.com/health
```

View logs in Render dashboard for debugging.

## Supported Exchanges

- NSE (National Stock Exchange of India)
- BSE (Bombay Stock Exchange)
- NASDAQ
- NYSE
- And more (any exchange supported by Google Finance)

## Limitations

- **Free Tier**: Spins down after 15 minutes of inactivity
- **Rate Limiting**: Respect Google's rate limits
- **Data Accuracy**: Prices are scraped from Google Finance (slight delay possible)

## License

MIT License - Part of EquiAlert project

## Support

For issues or questions, open an issue in the main EquiAlert repository.
