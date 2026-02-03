"""Test script for Yahoo Finance scraper"""
import sys
sys.path.append(".")

from services.scrapers import get_scraper
from loguru import logger

def test_google_scraper():
    """Test Google Finance scraper"""
    logger.info("=== Testing Google Finance Scraper ===")
    
    scraper = get_scraper("google")
    quote = scraper.get_stock_quote("AAPL", "NASDAQ")
    
    if quote:
        logger.success(f"Google - AAPL Quote: ${quote['price']}")
        logger.info(f"Data: {quote}")
    else:
        logger.error("Google scraper failed")
    
    print()

def test_yahoo_scraper():
    """Test Yahoo Finance scraper"""
    logger.info("=== Testing Yahoo Finance Scraper ===")
    
    scraper = get_scraper("yahoo")
    quote = scraper.get_stock_quote("AAPL", "NASDAQ")
    
    if quote:
        logger.success(f"Yahoo - AAPL Quote: ${quote['price']}")
        logger.info(f"Data: {quote}")
    else:
        logger.error("Yahoo scraper failed")
    
    print()

def test_indian_stocks():
    """Test Indian stock symbols"""
    logger.info("=== Testing Indian Stocks (NSE) ===")
    
    yahoo_scraper = get_scraper("yahoo")
    quote = yahoo_scraper.get_stock_quote("RELIANCE", "NSE")
    
    if quote:
        logger.success(f"Yahoo - RELIANCE.NS: ₹{quote['price']}")
        logger.info(f"Data: {quote}")
    else:
        logger.error("Yahoo scraper failed for RELIANCE.NS")
    
    print()

def test_profile():
    """Test profile fetching"""
    logger.info("=== Testing Profile Fetching ===")
    
    yahoo_scraper = get_scraper("yahoo")
    profile = yahoo_scraper.get_stock_profile("AAPL", "NASDAQ")
    
    if profile:
        logger.success(f"Profile: {profile['name']}")
        logger.info(f"Sector: {profile.get('sector')}")
        logger.info(f"Market Cap: ${profile.get('market_cap')}")
    else:
        logger.error("Profile fetching failed")

if __name__ == "__main__":
    logger.info("Starting scraper tests...\n")
    
    test_google_scraper()
    test_yahoo_scraper()
    test_indian_stocks()
    test_profile()
    
    logger.success("\n✅ All tests completed!")
