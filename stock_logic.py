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
        
        # Extract change and change percent with multiple fallback patterns
        change = None
        change_percent = None
        
        # Pattern 1: Try standard change class
        change_elements = soup.find_all(class_="JwB6zf")
        for elem in change_elements:
            text = elem.text.strip()
            if "%" in text:
                change_percent = self._parse_percentage(text)
            elif "$" in text or "₹" in text or "€" in text or "£" in text:
                change = self._parse_price(text)
            elif not change_percent and any(c.isdigit() for c in text):
                # Try parsing as number (might be change without symbol)
                try:
                    parsed = self._parse_price(text)
                    if parsed and abs(parsed) < price * 0.5:  # Sanity check: change < 50% of price
                        change = parsed
                except:
                    pass
        
        # Pattern 2: Look in data attributes or nearby elements
        if not change or not change_percent:
            try:
                # Try to find elements with specific data attributes
                price_section = soup.find("div", attrs={"data-last-price": True})
                if price_section:
                    change_elem = price_section.find_next("div", class_="JwB6zf")
                    if change_elem and not change:
                        change = self._parse_price(change_elem.text)
            except Exception as e:
                logger.debug(f"Fallback pattern 2 failed: {e}")
        
        # Pattern 3: Extract from header area (where price is displayed)
        if not change_percent:
            try:
                # Look for percentage near the main price
                header_section = soup.find("div", class_="YMlKec fxKbKc")
                if header_section:
                    parent = header_section.find_parent()
                    if parent:
                        percent_elems = parent.find_all(string=lambda text: text and "%" in str(text))
                        for elem in percent_elems:
                            parsed = self._parse_percentage(str(elem))
                            if parsed is not None:
                                change_percent = parsed
                                break
            except Exception as e:
                logger.debug(f"Fallback pattern 3 failed: {e}")
        
        # Extract previous close with multiple patterns
        previous_close = None
        
        # Pattern 1: Look for "Previous close" label
        try:
            all_divs = soup.find_all("div", class_="P6K39c")
            for div in all_divs:
                text = div.text.lower()
                if "previous close" in text or "prev close" in text or "prev. close" in text:
                    # Try next sibling with price class
                    value_div = div.find_next("div", class_="YMlKec fxKbKc")
                    if value_div:
                        previous_close = self._parse_price(value_div.text)
                        break
                    # Try parent's next sibling
                    parent = div.find_parent()
                    if parent:
                        next_div = parent.find_next_sibling()
                        if next_div:
                            previous_close = self._parse_price(next_div.text)
                            break
        except Exception as e:
            logger.debug(f"Previous close pattern 1 failed: {e}")
        
        # Pattern 2: Calculate from price and change
        if previous_close is None and price and change is not None:
            previous_close = price - change
            logger.debug(f"Calculated previous close from price-change: {previous_close}")
        
        # Pattern 3: Calculate from price and change_percent
        if previous_close is None and price and change_percent is not None:
            # previous_close = price / (1 + change_percent/100)
            previous_close = price / (1 + (change_percent / 100))
            logger.debug(f"Calculated previous close from percentage: {previous_close}")
        
        # Extract volume with multiple patterns
        volume = None
        
        # Pattern 1: Standard volume label search
        try:
            all_divs = soup.find_all("div", class_="P6K39c")
            for div in all_divs:
                text = div.text.lower()
                if "volume" in text and "avg" not in text:  # Avoid "Avg volume"
                    value_div = div.find_next("div", class_="YMlKec fxKbKc")
                    if value_div:
                        volume = self._parse_volume(value_div.text)
                        break
                    # Try parent's next sibling
                    parent = div.find_parent()
                    if parent:
                        next_div = parent.find_next_sibling()
                        if next_div:
                            volume = self._parse_volume(next_div.text)
                            break
        except Exception as e:
            logger.debug(f"Volume pattern 1 failed: {e}")
        
        # Pattern 2: Look for volume in table/grid structure
        if not volume:
            try:
                # Some pages show data in a grid
                all_text_nodes = soup.find_all(string=lambda text: text and "volume" in text.lower())
                for node in all_text_nodes:
                    parent = node.find_parent()
                    if parent:
                        # Look at siblings
                        for sibling in parent.find_next_siblings(limit=3):
                            vol = self._parse_volume(sibling.text)
                            if vol:
                                volume = vol
                                break
                    if volume:
                        break
            except Exception as e:
                logger.debug(f"Volume pattern 2 failed: {e}")
        
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
        
        # Extract company name with multiple patterns
        name = None
        
        # Pattern 1: Standard name div
        try:
            name_div = soup.find("div", class_="zzDege")
            if name_div:
                name = name_div.text.strip()
        except Exception:
            pass
        
        # Pattern 2: Try h1 or title elements
        if not name:
            try:
                h1 = soup.find("h1")
                if h1:
                    name = h1.text.strip()
            except Exception:
                pass
        
        # Pattern 3: Try meta tags
        if not name:
            try:
                meta_title = soup.find("meta", property="og:title")
                if meta_title and meta_title.get("content"):
                    name = meta_title["content"].strip()
                    # Clean up if it has extra text like " Stock Price"
                    if " - " in name:
                        name = name.split(" - ")[0]
            except Exception:
                pass
        
        # Extract sector/industry with multiple patterns
        sector = None
        industry = None
        
        # Pattern 1: Look for sector/industry labels
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
        except Exception as e:
            logger.debug(f"Sector/industry extraction failed: {e}")
        
        # Pattern 2: Try to find in description or about section
        if not sector:
            try:
                # Look for "about" section which sometimes contains sector info
                about_section = soup.find("div", class_="bLLb2d")
                if about_section:
                    text = about_section.text
                    # Common patterns like "Technology sector" or "operates in Healthcare"
                    import re
                    sector_match = re.search(r'(Technology|Healthcare|Finance|Energy|Consumer|Industrial|Materials|Utilities|Real Estate|Communication)', text, re.IGNORECASE)
                    if sector_match:
                        sector = sector_match.group(1)
            except Exception as e:
                logger.debug(f"Sector pattern 2 failed: {e}")
        
        # Extract market cap with multiple patterns
        market_cap = None
        
        # Pattern 1: Standard market cap label
        try:
            all_divs = soup.find_all("div", class_="P6K39c")
            for div in all_divs:
                text = div.text.lower()
                if "market cap" in text or "mkt cap" in text or "market capitalization" in text:
                    value_div = div.find_next("div", class_="YMlKec fxKbKc")
                    if value_div:
                        market_cap_str = value_div.text
                        market_cap = self._parse_volume(market_cap_str)
                        break
                    # Try parent's next sibling
                    parent = div.find_parent()
                    if parent:
                        next_div = parent.find_next_sibling()
                        if next_div:
                            market_cap = self._parse_volume(next_div.text)
                            break
        except Exception as e:
            logger.debug(f"Market cap pattern 1 failed: {e}")
        
        # Pattern 2: Look in data attributes or structured data
        if not market_cap:
            try:
                # Try to find in any element containing "market cap"
                cap_elements = soup.find_all(string=lambda text: text and "market cap" in text.lower())
                for elem in cap_elements:
                    parent = elem.find_parent()
                    if parent:
                        # Look for siblings with number values
                        for sibling in parent.find_next_siblings(limit=2):
                            parsed = self._parse_volume(sibling.text)
                            if parsed and parsed > 1000000:  # At least 1M market cap
                                market_cap = parsed
                                break
                    if market_cap:
                        break
            except Exception as e:
                logger.debug(f"Market cap pattern 2 failed: {e}")
        
        # Detect currency based on exchange or symbol
        currency = "USD"  # Default
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

