"""Enhanced Google Finance scraper with comprehensive data extraction"""
import requests
from bs4 import BeautifulSoup
import time
from typing import Optional, Dict, Any
from loguru import logger
from config import config


class GoogleFinanceScraper:
    """Google Finance web scraper with retry logic and enhanced data extraction"""
    
    def __init__(self):
        self.base_url = "https://www.google.com/finance"
        self.timeout = config.SCRAPER_TIMEOUT
        self.max_retries = config.SCRAPER_MAX_RETRIES
        self.backoff_factor = config.SCRAPER_BACKOFF_FACTOR
        
        # User agents for rotation
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        self.current_agent_idx = 0
    
    def _get_headers(self) -> dict:
        """Get request headers with rotating user agent"""
        headers = {
            "User-Agent": self.user_agents[self.current_agent_idx],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        # Rotate user agent
        self.current_agent_idx = (self.current_agent_idx + 1) % len(self.user_agents)
        return headers
    
    def _make_request(self, url: str, retry_count: int = 0) -> Optional[requests.Response]:
        """Make HTTP request with retry logic and exponential backoff"""
        try:
            response = requests.get(url, headers=self._get_headers(), timeout=self.timeout)
            response.raise_for_status()
            return response
        
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout for {url} (attempt {retry_count + 1}/{self.max_retries})")
        
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # Rate limited
                logger.warning(f"Rate limited by Google Finance (attempt {retry_count + 1}/{self.max_retries})")
            elif e.response.status_code == 404:
                logger.error(f"Stock not found: {url}")
                return None
            else:
                logger.error(f"HTTP error {e.response.status_code} for {url}")
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for {url}: {str(e)}")
        
        # Retry logic with exponential backoff
        if retry_count < self.max_retries:
            wait_time = self.backoff_factor ** retry_count
            logger.info(f"Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
            return self._make_request(url, retry_count + 1)
        
        logger.error(f"Max retries exceeded for {url}")
        return None
    
    def _extract_text(self, soup: BeautifulSoup, class_name: str) -> Optional[str]:
        """Extract text from element by class name"""
        element = soup.find(class_=class_name)
        return element.text.strip() if element else None
    
    def _parse_price(self, price_str: str) -> Optional[float]:
        """Parse price string to float (handles currency symbols and commas)"""
        if not price_str:
            return None
        try:
            # Remove currency symbols, commas, and whitespace
            clean_price = price_str.replace("$", "").replace("₹", "").replace("€", "").replace("£", "")
            clean_price = clean_price.replace(",", "").strip()
            return float(clean_price)
        except (ValueError, AttributeError):
            return None
    
    def _parse_percentage(self, percent_str: str) -> Optional[float]:
        """Parse percentage string to float"""
        if not percent_str:
            return None
        try:
            # Remove % symbol and parentheses
            clean_percent = percent_str.replace("%", "").replace("(", "").replace(")", "").strip()
            return float(clean_percent)
        except (ValueError, AttributeError):
            return None
    
    def _parse_volume(self, volume_str: str) -> Optional[int]:
        """Parse volume string with K/M/B suffixes"""
        if not volume_str:
            return None
        try:
            volume_str = volume_str.upper().strip()
            multipliers = {"K": 1000, "M": 1000000, "B": 1000000000}
            
            for suffix, multiplier in multipliers.items():
                if suffix in volume_str:
                    number = float(volume_str.replace(suffix, "").strip())
                    return int(number * multiplier)
            
            return int(float(volume_str.replace(",", "")))
        except (ValueError, AttributeError):
            return None
    
    def get_stock_quote(self, symbol: str, exchange: str) -> Dict[str, Any]:
        """
        Get comprehensive stock quote from Google Finance
        
        Returns:
            {
                "symbol": str,
                "exchange": str,
                "price": float,
                "change": float,
                "change_percent": float,
                "previous_close": float,
                "volume": int,
                "timestamp": str (ISO format)
            }
        """
        url = f"{self.base_url}/quote/{symbol}:{exchange}"
        logger.info(f"Scraping stock quote: {symbol}:{exchange}")
        
        response = self._make_request(url)
        if not response:
            return {"error": "Failed to fetch stock data", "symbol": symbol, "exchange": exchange}
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extract current price (main price element)
        price_class = "YMlKec fxKbKc"
        price_str = self._extract_text(soup, price_class)
        price = self._parse_price(price_str)
        
        if price is None:
            logger.error(f"Could not extract price for {symbol}:{exchange}")
            return {"error": "Invalid ticker or exchange", "symbol": symbol, "exchange": exchange}
        
        # Extract change and change percent
        change_class = "JwB6zf"  # Change amount
        change_percent_class = "JwB6zf"  # Also contains percentage
        
        # Get all change elements (usually shows both absolute and percentage)
        change_elements = soup.find_all(class_=change_class)
        change = None
        change_percent = None
        
        for elem in change_elements:
            text = elem.text.strip()
            if "%" in text:
                change_percent = self._parse_percentage(text)
            elif "$" in text or "₹" in text or any(c.isdigit() for c in text):
                change = self._parse_price(text)
        
        # Extract previous close
        # Look for "Previous close" label and get the value
        previous_close = None
        try:
            all_divs = soup.find_all("div", class_="P6K39c")
            for div in all_divs:
                if "Previous close" in div.text or "Prev close" in div.text:
                    # Get the next sibling or nearby element with the value
                    value_div = div.find_next("div", class_="YMlKec fxKbKc")
                    if value_div:
                        previous_close = self._parse_price(value_div.text)
                    break
        except Exception as e:
            logger.warning(f"Could not extract previous close: {e}")
        
        # Calculate previous close from current price and change if not found
        if previous_close is None and price and change:
            previous_close = price - change
        
        # Extract volume
        volume = None
        try:
            all_divs = soup.find_all("div", class_="P6K39c")
            for div in all_divs:
                if "Volume" in div.text:
                    value_div = div.find_next("div", class_="YMlKec fxKbKc")
                    if value_div:
                        volume = self._parse_volume(value_div.text)
                    break
        except Exception as e:
            logger.warning(f"Could not extract volume: {e}")
        
        # Get timestamp (current UTC time)
        from datetime import datetime
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        result = {
            "symbol": symbol.upper(),
            "exchange": exchange.upper(),
            "price": price,
            "change": change,
            "change_percent": change_percent,
            "previous_close": previous_close,
            "volume": volume,
            "timestamp": timestamp
        }
        
        logger.success(f"Successfully scraped {symbol}:{exchange} - Price: ${price}")
        return result
    
    def get_stock_profile(self, symbol: str, exchange: str) -> Dict[str, Any]:
        """
        Get company profile information
        
        Returns:
            {
                "symbol": str,
                "name": str,
                "sector": str,
                "industry": str,
                "market_cap": float,
                "currency": str
            }
        """
        url = f"{self.base_url}/quote/{symbol}:{exchange}"
        logger.info(f"Scraping stock profile: {symbol}:{exchange}")
        
        response = self._make_request(url)
        if not response:
            return {"error": "Failed to fetch stock data", "symbol": symbol, "exchange": exchange}
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extract company name
        name = None
        try:
            name_div = soup.find("div", class_="zzDege")
            if name_div:
                name = name_div.text.strip()
        except Exception:
            pass
        
        # Extract sector/industry from description or metadata
        sector = None
        industry = None
        
        # Extract market cap
        market_cap = None
        try:
            all_divs = soup.find_all("div", class_="P6K39c")
            for div in all_divs:
                if "Market cap" in div.text or "Mkt cap" in div.text:
                    value_div = div.find_next("div", class_="YMlKec fxKbKc")
                    if value_div:
                        market_cap_str = value_div.text
                        market_cap = self._parse_volume(market_cap_str)  # Uses same parser as volume
                    break
        except Exception as e:
            logger.warning(f"Could not extract market cap: {e}")
        
        result = {
            "symbol": symbol.upper(),
            "exchange": exchange.upper(),
            "name": name or f"{symbol} ({exchange})",
            "sector": sector,
            "industry": industry,
            "market_cap": market_cap,
            "currency": "USD"  # Default, could be extracted from page
        }
        
        logger.success(f"Successfully scraped profile for {symbol}:{exchange}")
        return result


# Global scraper instance
scraper = GoogleFinanceScraper()


# Backwards compatibility function
def get_stock_price(ticker: str, exchange: str) -> Dict[str, Any]:
    """Legacy function for backwards compatibility"""
    result = scraper.get_stock_quote(ticker, exchange)
    if "error" in result:
        return result
    return {
        "ticker": result["symbol"],
        "exchange": result["exchange"],
        "price": result["price"]
    }

