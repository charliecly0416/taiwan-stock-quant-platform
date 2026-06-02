"""
Symbol Mapping and Conversion

Converts QuantDinger system symbols to IB contract format.
"""

from typing import Tuple, Optional


def _normalize_tw_symbol(symbol: str) -> Tuple[str, str]:
    raw = (symbol or "").strip().upper()
    exchange = "TWSE"
    if raw.upper().startswith("TWSTOCK:"):
        raw = raw.split(":", 1)[1]
    if ":" in raw:
        prefix, raw = raw.split(":", 1)
        if prefix in ("TWSE", "TPEX"):
            exchange = prefix
    elif raw.endswith(".TPEX"):
        exchange = "TPEX"
        raw = raw[:-5]
    elif raw.endswith(".TW"):
        exchange = "TWSE"
        raw = raw[:-3]
    elif raw.endswith(".TWSE"):
        exchange = "TWSE"
        raw = raw[:-5]
    raw = raw.strip()
    if not raw.isdigit() or not (2 <= len(raw) <= 8):
        return "", exchange
    return raw, exchange


def normalize_symbol(symbol: str, market_type: str) -> Tuple[str, str, str]:
    """
    Convert system symbol to IB contract parameters.
    
    Args:
        symbol: Symbol code in the system
        market_type: Market type (USStock)
        
    Returns:
        (ib_symbol, exchange, currency)
    """
    symbol = (symbol or "").strip().upper()
    market_type = (market_type or "").strip()
    
    if market_type == "USStock":
        # US stocks: AAPL, TSLA, GOOGL
        # Use SMART routing for best execution
        return symbol, "SMART", "USD"

    if market_type == "TWStock":
        tw_symbol, exchange = _normalize_tw_symbol(symbol)
        return tw_symbol, exchange, "TWD"

    else:
        # Default to US stock
        return symbol, "SMART", "USD"


def parse_symbol(symbol: str) -> Tuple[str, Optional[str]]:
    """
    Parse symbol and auto-detect market type.
    
    Args:
        symbol: Symbol code
        
    Returns:
        (clean_symbol, market_type)
    """
    symbol = (symbol or "").strip().upper()
    tw_symbol, _exchange = _normalize_tw_symbol(symbol)
    if tw_symbol:
        return tw_symbol, "TWStock"

    # Default to US stock
    return symbol, "USStock"


def format_display_symbol(ib_symbol: str, exchange: str) -> str:
    """
    Convert IB contract format back to display format.
    
    Args:
        ib_symbol: IB symbol
        exchange: Exchange code
        
    Returns:
        Display symbol
    """
    if (exchange or "").upper() == "TPEX":
        return f"{ib_symbol}.TPEX"
    if (exchange or "").upper() == "TWSE":
        return f"{ib_symbol}.TW"
    return ib_symbol
