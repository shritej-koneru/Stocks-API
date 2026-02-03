from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from config import config

# Create database engine
engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in config.DATABASE_URL else {},
    echo=config.is_development  # Log SQL queries in development
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Database dependency for FastAPI
def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Stock(Base):
    """Stock information model"""
    __tablename__ = "stocks"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, index=True, nullable=False)
    exchange = Column(String(20), nullable=False)
    name = Column(String(255))
    sector = Column(String(100))
    industry = Column(String(100))
    market_cap = Column(Float)
    currency = Column(String(10), default="USD")
    country = Column(String(50))
    last_source = Column(String(10))  # Track last data source used ("google" or "yahoo")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    price_history = relationship("PriceHistory", back_populates="stock", cascade="all, delete-orphan")
    indicator_cache = relationship("IndicatorCache", back_populates="stock", cascade="all, delete-orphan")
    
    # Composite index for symbol + exchange queries
    __table_args__ = (
        Index('idx_symbol_exchange', 'symbol', 'exchange'),
    )
    
    def __repr__(self):
        return f"<Stock(symbol='{self.symbol}', exchange='{self.exchange}', name='{self.name}')>"


class PriceHistory(Base):
    """Historical price data model (OHLCV)"""
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # OHLCV data
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float, nullable=False)  # Close is always required
    volume = Column(Integer)
    
    # Additional fields
    change = Column(Float)  # Absolute price change
    change_percent = Column(Float)  # Percentage change
    previous_close = Column(Float)
    data_source = Column(String(10), default="google")  # Track data source ("google" or "yahoo")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    stock = relationship("Stock", back_populates="price_history")
    
    # Composite index for efficient queries
    __table_args__ = (
        Index('idx_stock_timestamp', 'stock_id', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<PriceHistory(stock_id={self.stock_id}, timestamp='{self.timestamp}', close={self.close})>"


class IndicatorCache(Base):
    """Technical indicator cache model"""
    __tablename__ = "indicator_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    
    # Indicator metadata
    indicator_type = Column(String(50), nullable=False)  # sma, ema, rsi, macd, etc.
    period = Column(Integer)  # Period for the indicator (e.g., 14 for RSI-14)
    interval = Column(String(10), default="1d")  # Data interval (1d, 1h, etc.)
    
    # Indicator data (stored as JSON)
    value_json = Column(Text, nullable=False)  # Array of {timestamp, value} objects
    
    # Metadata
    calculated_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)
    
    # Relationships
    stock = relationship("Stock", back_populates="indicator_cache")
    
    # Composite index for cache lookups
    __table_args__ = (
        Index('idx_indicator_lookup', 'stock_id', 'indicator_type', 'period', 'interval'),
    )
    
    def __repr__(self):
        return f"<IndicatorCache(stock_id={self.stock_id}, type='{self.indicator_type}', period={self.period})>"


class MarketSnapshot(Base):
    """Market summary and top movers snapshot"""
    __tablename__ = "market_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Stock identification
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(20), nullable=False)
    
    # Market data
    price = Column(Float, nullable=False)
    change = Column(Float)
    change_percent = Column(Float)
    volume = Column(Integer)
    
    # Category
    category = Column(String(50))  # 'gainer', 'loser', 'active', 'index'
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Composite index for queries
    __table_args__ = (
        Index('idx_market_category', 'category', 'timestamp'),
        Index('idx_symbol_timestamp', 'symbol', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<MarketSnapshot(symbol='{self.symbol}', category='{self.category}', price={self.price})>"


def init_db():
    """Initialize database - create all tables"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized successfully")


def drop_db():
    """Drop all tables (use with caution!)"""
    Base.metadata.drop_all(bind=engine)
    print("⚠️  All database tables dropped")


if __name__ == "__main__":
    # Initialize database when run directly
    init_db()
