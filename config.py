import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration"""
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./stock_data.db")
    
    # Environment
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    
    # API
    API_VERSION = os.getenv("API_VERSION", "1.0.0")
    API_TITLE = os.getenv("API_TITLE", "EquiAlert Stock API")
    API_DESCRIPTION = os.getenv("API_DESCRIPTION", "Microservice for fetching stock prices and analytics")
    
    # Cache TTL (Time To Live) in seconds
    CACHE_TTL_CURRENT_PRICE = int(os.getenv("CACHE_TTL_CURRENT_PRICE", 300))  # 5 minutes
    CACHE_TTL_HISTORICAL = int(os.getenv("CACHE_TTL_HISTORICAL", 3600))  # 1 hour
    CACHE_TTL_INDICATORS = int(os.getenv("CACHE_TTL_INDICATORS", 3600))  # 1 hour
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", 60))
    
    # Scraping
    SCRAPER_TIMEOUT = int(os.getenv("SCRAPER_TIMEOUT", 10))
    SCRAPER_MAX_RETRIES = int(os.getenv("SCRAPER_MAX_RETRIES", 3))
    SCRAPER_BACKOFF_FACTOR = int(os.getenv("SCRAPER_BACKOFF_FACTOR", 2))
    
    # Background Tasks
    SCRAPER_INTERVAL_MINUTES = int(os.getenv("SCRAPER_INTERVAL_MINUTES", 15))
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

# Global config instance
config = Config()
