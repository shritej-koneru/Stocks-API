"""Enhanced Google Finance scraper implementing BaseScraper interface"""
import requests
from bs4 import BeautifulSoup
import time
from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger
from config import config
from .base_scraper import BaseScraper


class GoogleFinanceScraper(BaseScraper):
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
    
    @property
    def source_name(self) -> str:
        return "google"
    
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
            logger.warning(f"Google Finance timeout for {url} (attempt {retry_count + 1}/{self.max_retries})")
        
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # Rate limited
                logger.warning(f"Rate limited by Google Finance (attempt {retry_count + 1}/{self.max_retries})")
            elif e.response.status_code == 404:
                logger.error(f"Stock not found on Google Finance: {url}")
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
    
    def get_stock_quote(self, symbol: str, exchange: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive stock quote from Google Finance"""
        url = f"{self.base_url}/quote/{symbol}:{exchange}"
        logger.info(f"[Google] Scraping stock quote: {symbol}:{exchange}")
        
        response = self._make_request(url)
        if not response:
            logger.error(f"[Google] Failed to fetch stock data for {symbol}:{exchange}")
            return None
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extract current price
        price_class = "YMlKec fxKbKc"
        price_str = self._extract_text(soup, price_class)
        price = self._parse_price(price_str)
        
        if price is None:
            logger.error(f"[Google] Could not extract price for {symbol}:{exchange}")
            return None
        
        # Extract change and change percent with fallback patterns
        change = None
        change_percent = None
        
        change_elements = soup.find_all(class_="JwB6zf")
        for elem in change_elements:
            text = elem.text.strip()
            if "%" in text:
                change_percent = self._parse_percentage(text)
            elif "$" in text or "₹" in text or "€" in text or "£" in text:
                change = self._parse_price(text)
            elif not change_percent and any(c.isdigit() for c in text):
                try:
                    parsed = self._parse_price(text)
                    if parsed and abs(parsed) < price * 0.5:
                        change = parsed
                except:
                    pass
        
        # Extract previous close
        previous_close = None
        try:
            all_divs = soup.find_all("div", class_="P6K39c")
            for div in all_divs:
                if "previous close" in div.text.lower():
                    value_div = div.find_next("div", class_="YMlKec fxKbKc")
                    if value_div:
                        previous_close = self._parse_price(value_div.text)
                        break
        except:
            pass
        
        # Calculate previous close if not found
        if previous_close is None and price and change is not None:
            previous_close = price - change
        elif previous_close is None and price and change_percent is not None:
            previous_close = price / (1 + (change_percent / 100))
        
        # Extract volume
        volume = None
        try:
            all_divs = soup.find_all("div", class_="P6K39c")
            for div in all_divs:
                text = div.text.lower()
                if "volume" in text and "avg" not in text:
                    value_div = div.find_next("div", class_="YMlKec fxKbKc")
                    if value_div:
                        volume = self._parse_volume(value_div.text)
                        break
        except:
            pass
        
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
        
        logger.success(f"[Google] Successfully scraped {symbol}:{exchange} - Price: {price}")
        return result
    
    def get_stock_profile(self, symbol: str, exchange: str) -> Optional[Dict[str, Any]]:
        """Get company profile information from Google Finance"""
        url = f"{self.base_url}/quote/{symbol}:{exchange}"
        logger.info(f"[Google] Scraping stock profile: {symbol}:{exchange}")
        
        response = self._make_request(url)
        if not response:
            return None
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extract company name
        name = None
        try:
            name_div = soup.find("div", class_="zzDege")
            if name_div:
                name = name_div.text.strip()
        except:
            pass
        
        if not name:
            try:
                h1 = soup.find("h1")
                if h1:
                    name = h1.text.strip()
            except:
                pass
        
        # Extract sector/industry
        sector = None
        industry = None
        try:
            all_divs = soup.find_all("div", class_="P6K39c")
            for div in all_divs:
                text = div.text.lower()
                if "sector" in text:
                    value_div = div.find_next("div", class_="YMlKec fxKbKc")
                    if value_div:
                        sector = value_div.text.strip()
                elif "industry" in text:
                    value_div = div.find_next("div", class_="YMlKec fxKbKc")
                    if value_div:
                        industry = value_div.text.strip()
        except:
            pass
        
        # Regex fallback for sector
        if not sector:
            try:
                about_section = soup.find("div", class_="bLLb2d")
                if about_section:
                    import re
                    sector_match = re.search(r'(Technology|Healthcare|Finance|Energy|Consumer|Industrial|Materials|Utilities|Real Estate|Communication)', about_section.text, re.IGNORECASE)
                    if sector_match:
                        sector = sector_match.group(1)
            except:
                pass
        
        # Extract market cap
        market_cap = None
        try:
            all_divs = soup.find_all("div", class_="P6K39c")
            for div in all_divs:
                if "market cap" in div.text.lower():
                    value_div = div.find_next("div", class_="YMlKec fxKbKc")
                    if value_div:
                        market_cap = self._parse_volume(value_div.text)
                        break
        except:
            pass
        
        # Detect currency
        currency = "USD"
        if exchange.upper() in ["NSE", "BSE"]:
            currency = "INR"
        elif exchange.upper() in ["LSE", "LON"]:
            currency = "GBP"
        elif exchange.upper() in ["FRA", "PAR", "AMS"]:
            currency = "EUR"
        elif exchange.upper() in ["JPX", "TSE"]:
            currency = "JPY"
        
        result = {
            "symbol": symbol.upper(),
            "exchange": exchange.upper(),
            "name": name or f"{symbol} ({exchange})",
            "sector": sector,
            "industry": industry,
            "market_cap": market_cap,
            "currency": currency
        }
        
        logger.success(f"[Google] Successfully scraped profile for {symbol}:{exchange}")
        return result
    
    def get_historical_data(self, symbol: str, exchange: str, days: int = 30) -> Optional[List[Dict[str, Any]]]:
        """
        Get historical data from Google Finance.
        Note: Google Finance doesn't provide easy historical data access via scraping.
        This returns None to indicate the data source doesn't support this operation.
        """
        logger.warning(f"[Google] Historical data scraping not implemented for {symbol}:{exchange}")
        return None
