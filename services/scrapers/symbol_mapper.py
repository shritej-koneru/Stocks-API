"""
Symbol format converter for different exchanges.
Converts between Google Finance format (SYMBOL:EXCHANGE) and Yahoo Finance format (SYMBOL.SUFFIX).
"""

from typing import Tuple, Optional


# Exchange suffix mapping for Yahoo Finance
EXCHANGE_SUFFIX_MAP = {
    # Indian Exchanges
    "NSE": ".NS",
    "BSE": ".BO",
    
    # US Exchanges (no suffix needed)
    "NASDAQ": "",
    "NYSE": "",
    "AMEX": "",
    "NYSEAMERICAN": "",
    
    # European Exchanges
    "LON": ".L",       # London Stock Exchange
    "LSE": ".L",       # London Stock Exchange (alternative)
    "FRA": ".DE",      # Frankfurt Stock Exchange
    "PAR": ".PA",      # Euronext Paris
    "AMS": ".AS",      # Euronext Amsterdam
    "BME": ".MC",      # Madrid Stock Exchange
    "MIL": ".MI",      # Milan Stock Exchange
    "SWX": ".SW",      # Swiss Exchange
    
    # Asian Exchanges
    "JPX": ".T",       # Tokyo Stock Exchange
    "TSE": ".T",       # Tokyo Stock Exchange (alternative)
    "HKG": ".HK",      # Hong Kong Stock Exchange
    "HKEX": ".HK",     # Hong Kong Stock Exchange (alternative)
    "SHA": ".SS",      # Shanghai Stock Exchange
    "SHE": ".SZ",      # Shenzhen Stock Exchange
    "KRX": ".KS",      # Korea Exchange
    "KSE": ".KS",      # Korea Stock Exchange (alternative)
    
    # Other Major Exchanges
    "TSX": ".TO",      # Toronto Stock Exchange
    "TSXV": ".V",      # TSX Venture Exchange
    "ASX": ".AX",      # Australian Securities Exchange
    "NZX": ".NZ",      # New Zealand Exchange
    "JSE": ".JO",      # Johannesburg Stock Exchange
    "BSP": ".SA",      # B3 (Brazil)
    "BMV": ".MX",      # Mexican Stock Exchange
}


def convert_to_yahoo_symbol(symbol: str, exchange: str) -> str:
    """
    Convert Google Finance format to Yahoo Finance format.
    
    Args:
        symbol: Stock symbol (e.g., "RELIANCE", "AAPL")
        exchange: Exchange code (e.g., "NSE", "NASDAQ")
        
    Returns:
        Yahoo Finance symbol (e.g., "RELIANCE.NS", "AAPL")
        
    Examples:
        >>> convert_to_yahoo_symbol("RELIANCE", "NSE")
        'RELIANCE.NS'
        >>> convert_to_yahoo_symbol("AAPL", "NASDAQ")
        'AAPL'
        >>> convert_to_yahoo_symbol("BP", "LON")
        'BP.L'
    """
    exchange_upper = exchange.upper()
    suffix = EXCHANGE_SUFFIX_MAP.get(exchange_upper, "")
    return f"{symbol.upper()}{suffix}"


def parse_yahoo_symbol(yahoo_symbol: str) -> Tuple[str, Optional[str]]:
    """
    Parse Yahoo Finance symbol back to (symbol, exchange).
    
    Args:
        yahoo_symbol: Yahoo Finance symbol (e.g., "RELIANCE.NS", "AAPL")
        
    Returns:
        Tuple of (symbol, exchange) where exchange may be None if unknown
        
    Examples:
        >>> parse_yahoo_symbol("RELIANCE.NS")
        ('RELIANCE', 'NSE')
        >>> parse_yahoo_symbol("AAPL")
        ('AAPL', 'NASDAQ')
        >>> parse_yahoo_symbol("BP.L")
        ('BP', 'LON')
    """
    # Try to find matching suffix
    for exchange, suffix in EXCHANGE_SUFFIX_MAP.items():
        if suffix and yahoo_symbol.endswith(suffix):
            symbol = yahoo_symbol[:-len(suffix)]
            return (symbol, exchange)
    
    # No suffix found - assume US exchange (NASDAQ by default)
    return (yahoo_symbol, "NASDAQ")


def get_yahoo_symbol_examples() -> dict:
    """
    Get example symbol conversions for documentation.
    
    Returns:
        Dict mapping exchange to example conversion
    """
    examples = {
        "NSE": "RELIANCE → RELIANCE.NS",
        "BSE": "TCS → TCS.BO",
        "NASDAQ": "AAPL → AAPL",
        "NYSE": "IBM → IBM",
        "LON": "BP → BP.L",
        "FRA": "SAP → SAP.DE",
        "JPX": "SONY → SONY.T",
        "HKG": "0700 → 0700.HK",
        "TSX": "SHOP → SHOP.TO",
        "ASX": "BHP → BHP.AX",
    }
    return examples


def is_valid_exchange(exchange: str) -> bool:
    """
    Check if exchange is supported.
    
    Args:
        exchange: Exchange code to validate
        
    Returns:
        True if exchange is supported, False otherwise
    """
    return exchange.upper() in EXCHANGE_SUFFIX_MAP
