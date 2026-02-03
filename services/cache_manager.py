"""Cache manager for stock data using in-memory TTL cache"""
from cachetools import TTLCache
from typing import Any, Optional, Callable
import hashlib
import json
from loguru import logger
from config import config


class CacheManager:
    """
    In-memory cache manager with TTL (Time To Live) support.
    Uses cachetools for efficient caching without external dependencies like Redis.
    """
    
    def __init__(self):
        # Separate caches with different TTLs
        self.current_price_cache = TTLCache(
            maxsize=1000,  # Store up to 1000 stock prices
            ttl=config.CACHE_TTL_CURRENT_PRICE  # 5 minutes default
        )
        
        self.historical_cache = TTLCache(
            maxsize=500,  # Store up to 500 historical datasets
            ttl=config.CACHE_TTL_HISTORICAL  # 1 hour default
        )
        
        self.indicator_cache = TTLCache(
            maxsize=500,  # Store up to 500 indicator calculations
            ttl=config.CACHE_TTL_INDICATORS  # 1 hour default
        )
        
        self.market_cache = TTLCache(
            maxsize=100,  # Store market summaries
            ttl=300  # 5 minutes for market data
        )
        
        logger.info("Cache manager initialized with TTL: "
                   f"price={config.CACHE_TTL_CURRENT_PRICE}s, "
                   f"historical={config.CACHE_TTL_HISTORICAL}s, "
                   f"indicators={config.CACHE_TTL_INDICATORS}s")
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate a unique cache key from arguments"""
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get_current_price(self, symbol: str, exchange: str) -> Optional[dict]:
        """Get cached current price"""
        key = f"{symbol}:{exchange}"
        value = self.current_price_cache.get(key)
        if value:
            logger.debug(f"Cache HIT: current_price for {key}")
        return value
    
    def set_current_price(self, symbol: str, exchange: str, data: dict):
        """Cache current price data"""
        key = f"{symbol}:{exchange}"
        self.current_price_cache[key] = data
        logger.debug(f"Cache SET: current_price for {key}")
    
    def get_historical(self, symbol: str, interval: str, range_: str) -> Optional[dict]:
        """Get cached historical data"""
        key = f"{symbol}:{interval}:{range_}"
        value = self.historical_cache.get(key)
        if value:
            logger.debug(f"Cache HIT: historical for {key}")
        return value
    
    def set_historical(self, symbol: str, interval: str, range_: str, data: dict):
        """Cache historical data"""
        key = f"{symbol}:{interval}:{range_}"
        self.historical_cache[key] = data
        logger.debug(f"Cache SET: historical for {key}")
    
    def get_indicator(self, symbol: str, indicator_type: str, period: int, interval: str = "1d") -> Optional[dict]:
        """Get cached indicator data"""
        key = f"{symbol}:{indicator_type}:{period}:{interval}"
        value = self.indicator_cache.get(key)
        if value:
            logger.debug(f"Cache HIT: indicator for {key}")
        return value
    
    def set_indicator(self, symbol: str, indicator_type: str, period: int, interval: str, data: dict):
        """Cache indicator data"""
        key = f"{symbol}:{indicator_type}:{period}:{interval}"
        self.indicator_cache[key] = data
        logger.debug(f"Cache SET: indicator for {key}")
    
    def get_market(self, category: str) -> Optional[dict]:
        """Get cached market data (gainers, losers, etc.)"""
        value = self.market_cache.get(category)
        if value:
            logger.debug(f"Cache HIT: market for {category}")
        return value
    
    def set_market(self, category: str, data: dict):
        """Cache market data"""
        self.market_cache[category] = data
        logger.debug(f"Cache SET: market for {category}")
    
    def invalidate_stock(self, symbol: str):
        """Invalidate all cache entries for a specific stock"""
        # Remove from current price cache
        for key in list(self.current_price_cache.keys()):
            if key.startswith(f"{symbol}:"):
                del self.current_price_cache[key]
                logger.debug(f"Cache INVALIDATE: {key}")
        
        # Remove from historical cache
        for key in list(self.historical_cache.keys()):
            if key.startswith(f"{symbol}:"):
                del self.historical_cache[key]
                logger.debug(f"Cache INVALIDATE: {key}")
        
        # Remove from indicator cache
        for key in list(self.indicator_cache.keys()):
            if key.startswith(f"{symbol}:"):
                del self.indicator_cache[key]
                logger.debug(f"Cache INVALIDATE: {key}")
    
    def clear_all(self):
        """Clear all caches"""
        self.current_price_cache.clear()
        self.historical_cache.clear()
        self.indicator_cache.clear()
        self.market_cache.clear()
        logger.warning("All caches cleared")
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        return {
            "current_price": {
                "size": len(self.current_price_cache),
                "maxsize": self.current_price_cache.maxsize,
                "ttl": config.CACHE_TTL_CURRENT_PRICE
            },
            "historical": {
                "size": len(self.historical_cache),
                "maxsize": self.historical_cache.maxsize,
                "ttl": config.CACHE_TTL_HISTORICAL
            },
            "indicator": {
                "size": len(self.indicator_cache),
                "maxsize": self.indicator_cache.maxsize,
                "ttl": config.CACHE_TTL_INDICATORS
            },
            "market": {
                "size": len(self.market_cache),
                "maxsize": self.market_cache.maxsize,
                "ttl": 300
            }
        }


# Global cache instance
cache_manager = CacheManager()


def cached(cache_type: str = "current_price"):
    """
    Decorator for caching function results
    
    Args:
        cache_type: Type of cache to use ('current_price', 'historical', 'indicator', 'market')
    """
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            # Generate cache key
            key = cache_manager._generate_key(func.__name__, *args, **kwargs)
            
            # Select appropriate cache
            if cache_type == "current_price":
                cache = cache_manager.current_price_cache
            elif cache_type == "historical":
                cache = cache_manager.historical_cache
            elif cache_type == "indicator":
                cache = cache_manager.indicator_cache
            elif cache_type == "market":
                cache = cache_manager.market_cache
            else:
                # No caching, just execute
                return func(*args, **kwargs)
            
            # Check cache
            if key in cache:
                logger.debug(f"Cache HIT: {func.__name__}")
                return cache[key]
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache[key] = result
            logger.debug(f"Cache SET: {func.__name__}")
            
            return result
        
        return wrapper
    return decorator
