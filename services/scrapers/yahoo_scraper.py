"""Yahoo Finance scraper with lazy yfinance import for memory optimization"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from loguru import logger
from .base_scraper import BaseScraper
from .symbol_mapper import convert_to_yahoo_symbol


class YahooFinanceScraper(BaseScraper):
    """Yahoo Finance scraper using yfinance library with lazy loading"""
    
    def __init__(self):
        self._yf = None  # Lazy load yfinance
        logger.info("[Yahoo] Initialized (yfinance not loaded yet - lazy loading enabled)")
    
    @property
    def source_name(self) -> str:
        return "yahoo"
    
    def _ensure_yfinance(self):
        """Lazy load yfinance library only when needed (saves ~70MB RAM)"""
        if self._yf is None:
            try:
                logger.info("[Yahoo] Loading yfinance library...")
                import yfinance as yf
                self._yf = yf
                logger.success("[Yahoo] yfinance library loaded successfully")
            except ImportError:
                logger.error("[Yahoo] yfinance library not installed. Run: pip install yfinance")
                raise ImportError("yfinance library not installed. Install with: pip install yfinance>=0.2.40")
    
    def _normalize_yahoo_value(self, value: Any, default: Any = None) -> Any:
        """Normalize Yahoo Finance values (handle NaN, None, 'N/A')"""
        if value is None:
            return default
        
        # Check if it's a pandas NaN or similar
        try:
            import math
            if isinstance(value, float) and math.isnan(value):
                return default
        except:
            pass
        
        # Handle 'N/A' or empty strings
        if isinstance(value, str) and (value.strip() == "" or value.upper() == "N/A"):
            return default
        
        return value
    
    def get_stock_quote(self, symbol: str, exchange: str) -> Optional[Dict[str, Any]]:
        """Get current stock quote from Yahoo Finance"""
        try:
            self._ensure_yfinance()
            
            yahoo_symbol = convert_to_yahoo_symbol(symbol, exchange)
            logger.info(f"[Yahoo] Fetching quote: {symbol}:{exchange} → {yahoo_symbol}")
            
            ticker = self._yf.Ticker(yahoo_symbol)
            info = ticker.info
            
            # Check if we got valid data
            if not info or "regularMarketPrice" not in info and "currentPrice" not in info:
                logger.error(f"[Yahoo] No quote data available for {yahoo_symbol}")
                return None
            
            # Extract price (try multiple fields)
            price = self._normalize_yahoo_value(info.get("currentPrice")) or \
                    self._normalize_yahoo_value(info.get("regularMarketPrice"))
            
            if not price:
                logger.error(f"[Yahoo] Could not extract price for {yahoo_symbol}")
                return None
            
            # Extract other fields
            change = self._normalize_yahoo_value(info.get("regularMarketChange"))
            change_percent = self._normalize_yahoo_value(info.get("regularMarketChangePercent"))
            previous_close = self._normalize_yahoo_value(info.get("regularMarketPreviousClose")) or \
                           self._normalize_yahoo_value(info.get("previousClose"))
            volume = self._normalize_yahoo_value(info.get("regularMarketVolume")) or \
                    self._normalize_yahoo_value(info.get("volume"))
            
            # Convert volume to int if present
            if volume:
                try:
                    volume = int(volume)
                except:
                    volume = None
            
            timestamp = datetime.utcnow().isoformat() + "Z"
            
            result = {
                "symbol": symbol.upper(),
                "exchange": exchange.upper(),
                "price": float(price),
                "change": float(change) if change else None,
                "change_percent": float(change_percent) if change_percent else None,
                "previous_close": float(previous_close) if previous_close else None,
                "volume": volume,
                "timestamp": timestamp
            }
            
            logger.success(f"[Yahoo] Successfully fetched {yahoo_symbol} - Price: {price}")
            return result
        
        except Exception as e:
            logger.error(f"[Yahoo] Error fetching quote for {symbol}:{exchange}: {str(e)}")
            return None
    
    def get_stock_profile(self, symbol: str, exchange: str) -> Optional[Dict[str, Any]]:
        """Get company profile from Yahoo Finance"""
        try:
            self._ensure_yfinance()
            
            yahoo_symbol = convert_to_yahoo_symbol(symbol, exchange)
            logger.info(f"[Yahoo] Fetching profile: {symbol}:{exchange} → {yahoo_symbol}")
            
            ticker = self._yf.Ticker(yahoo_symbol)
            info = ticker.info
            
            if not info:
                logger.error(f"[Yahoo] No profile data available for {yahoo_symbol}")
                return None
            
            # Extract profile fields with fallbacks
            name = self._normalize_yahoo_value(info.get("longName")) or \
                   self._normalize_yahoo_value(info.get("shortName")) or \
                   f"{symbol} ({exchange})"
            
            sector = self._normalize_yahoo_value(info.get("sector"))
            industry = self._normalize_yahoo_value(info.get("industry"))
            market_cap = self._normalize_yahoo_value(info.get("marketCap"))
            currency = self._normalize_yahoo_value(info.get("currency"), "USD")
            
            # Convert market cap to int if present
            if market_cap:
                try:
                    market_cap = int(market_cap)
                except:
                    market_cap = None
            
            result = {
                "symbol": symbol.upper(),
                "exchange": exchange.upper(),
                "name": name,
                "sector": sector,
                "industry": industry,
                "market_cap": market_cap,
                "currency": currency
            }
            
            logger.success(f"[Yahoo] Successfully fetched profile for {yahoo_symbol}")
            return result
        
        except Exception as e:
            logger.error(f"[Yahoo] Error fetching profile for {symbol}:{exchange}: {str(e)}")
            return None
    
    def get_historical_data(self, symbol: str, exchange: str, days: int = 30) -> Optional[List[Dict[str, Any]]]:
        """Get historical OHLCV data from Yahoo Finance"""
        try:
            self._ensure_yfinance()
            
            yahoo_symbol = convert_to_yahoo_symbol(symbol, exchange)
            logger.info(f"[Yahoo] Fetching historical data: {yahoo_symbol} ({days} days)")
            
            ticker = self._yf.Ticker(yahoo_symbol)
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days + 5)  # Get extra days to ensure enough data
            
            # Fetch historical data
            hist = ticker.history(start=start_date, end=end_date)
            
            if hist.empty:
                logger.error(f"[Yahoo] No historical data available for {yahoo_symbol}")
                return None
            
            # Convert DataFrame to list of dicts
            data = []
            for date, row in hist.iterrows():
                try:
                    data.append({
                        "date": date.strftime("%Y-%m-%d"),
                        "open": float(row["Open"]) if not self._is_nan(row["Open"]) else None,
                        "high": float(row["High"]) if not self._is_nan(row["High"]) else None,
                        "low": float(row["Low"]) if not self._is_nan(row["Low"]) else None,
                        "close": float(row["Close"]) if not self._is_nan(row["Close"]) else None,
                        "volume": int(row["Volume"]) if not self._is_nan(row["Volume"]) else None,
                    })
                except Exception as e:
                    logger.warning(f"[Yahoo] Error parsing row {date}: {str(e)}")
                    continue
            
            # Limit to requested days
            data = data[-days:] if len(data) > days else data
            
            logger.success(f"[Yahoo] Fetched {len(data)} days of historical data for {yahoo_symbol}")
            return data
        
        except Exception as e:
            logger.error(f"[Yahoo] Error fetching historical data for {symbol}:{exchange}: {str(e)}")
            return None
    
    def _is_nan(self, value: Any) -> bool:
        """Check if value is NaN"""
        try:
            import math
            return isinstance(value, float) and math.isnan(value)
        except:
            return False
