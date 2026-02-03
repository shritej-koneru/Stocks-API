"""
Scrapers package for stock data sources.
Supports Google Finance and Yahoo Finance with automatic fallback.
"""

from .base_scraper import BaseScraper
from .scraper_factory import get_scraper

__all__ = ["BaseScraper", "get_scraper"]
