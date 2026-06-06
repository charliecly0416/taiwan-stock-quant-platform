"""
Market symbols seed data and lookup functions.

Data is stored in PostgreSQL table `qd_market_symbols` (initialized via migrations/init.sql).
This module provides helper functions to query hot symbols, search, and get symbol names.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)



_TWSTOCK_FALLBACK_SYMBOLS: List[Dict] = [
    ('2330', '台積電', 'stock', 100),
    ('2317', '鴻海', 'stock', 99),
    ('2454', '聯發科', 'stock', 98),
    ('2308', '台達電', 'stock', 97),
    ('2357', '華碩', 'stock', 96),
    ('2412', '中華電', 'stock', 95),
    ('6290', '良維', 'stock', 94),
    ('2881', '富邦金', 'stock', 93),
    ('2882', '國泰金', 'stock', 92),
    ('2891', '中信金', 'stock', 91),
    ('1303', '南亞', 'stock', 90),
    ('0050', '元大台灣50', 'etf', 89),
    ('0056', '元大高股息', 'etf', 88),
    ('00878', '國泰永續高股息', 'etf', 87),
]
_TWSTOCK_PRICE_TICK_JSON = '{"source":"twse_default","note":"Use official TWSE/TPEx tick-size table before live trading."}'


def _fallback_symbols(market: str = None) -> List[Dict]:
    m = (market or '').strip()
    if m and m != 'TWStock':
        return []
    rows = []
    for symbol, name, instrument_type, sort_order in _TWSTOCK_FALLBACK_SYMBOLS:
        rows.append({
            'market': 'TWStock',
            'symbol': symbol,
            'name': name,
            'exchange': 'TWSE',
            'currency': 'TWD',
            'is_hot': 1,
            'sort_order': sort_order,
            'instrument_type': instrument_type,
            'lot_size': 1000,
            'price_tick_json': _TWSTOCK_PRICE_TICK_JSON,
        })
    return rows

def _get_db_connection():
    """Get database connection, returns None if not available."""
    try:
        from app.utils.db import get_db_connection
        return get_db_connection()
    except Exception:
        return None


def get_hot_symbols(market: str, limit: int = 10) -> List[Dict]:
    """
    Get hot symbols for a market.
    
    Args:
        market: Market name (e.g., 'Crypto', 'USStock', 'Forex')
        limit: Maximum number of results
        
    Returns:
        List of {market, symbol, name} dicts
    """
    market = (market or '').strip()
    if not market:
        return []
    
    try:
        with _get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                """
                SELECT market, symbol, name FROM qd_market_symbols
                WHERE market = ? AND is_active = 1 AND is_hot = 1
                ORDER BY sort_order DESC
                LIMIT ?
                """,
                (market, max(limit, 0))
            )
            rows = cur.fetchall() or []
            cur.close()
            return [{'market': r['market'], 'symbol': r['symbol'], 'name': r.get('name') or ''} for r in rows]
    except Exception as e:
        logger.debug(f"get_hot_symbols from DB failed: {e}")
        return [
            {'market': r['market'], 'symbol': r['symbol'], 'name': r.get('name') or ''}
            for r in _fallback_symbols(market)
            if int(r.get('is_hot') or 0) == 1
        ][:max(limit, 0)]


def search_symbols(market: str, keyword: str, limit: int = 20) -> List[Dict]:
    """
    Search symbols by keyword.
    
    Args:
        market: Market name
        keyword: Search keyword (matches symbol or name)
        limit: Maximum number of results
        
    Returns:
        List of {market, symbol, name} dicts
    """
    market = (market or '').strip()
    kw = (keyword or '').strip()
    if not market or not kw:
        return []
    
    # Use ILIKE for case-insensitive search in PostgreSQL
    pattern = f'%{kw}%'
    
    try:
        with _get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                """
                SELECT market, symbol, name FROM qd_market_symbols
                WHERE market = ? AND is_active = 1
                  AND (UPPER(symbol) LIKE UPPER(?) OR UPPER(name) LIKE UPPER(?))
                ORDER BY sort_order DESC
                LIMIT ?
                """,
                (market, pattern, pattern, max(limit, 0))
            )
            rows = cur.fetchall() or []
            cur.close()
            return [{'market': r['market'], 'symbol': r['symbol'], 'name': r.get('name') or ''} for r in rows]
    except Exception as e:
        logger.debug(f"search_symbols from DB failed: {e}")
        out = []
        kw_upper = kw.upper()
        for r in _fallback_symbols(market):
            if kw_upper in str(r.get('symbol') or '').upper() or kw_upper in str(r.get('name') or '').upper():
                out.append({'market': r['market'], 'symbol': r['symbol'], 'name': r.get('name') or ''})
                if len(out) >= max(limit, 0):
                    break
        return out


def _normalize_for_match(market: str, symbol: str) -> str:
    """Normalize symbol for matching."""
    m = (market or '').strip()
    s = (symbol or '').strip().upper()
    if not m or not s:
        return s

    return s


def get_symbol_name(market: str, symbol: str) -> Optional[str]:
    """
    Get display name for a symbol.
    
    Args:
        market: Market name
        symbol: Symbol (e.g., 'AAPL', 'BTC/USDT', '600519')
        
    Returns:
        Symbol name or None if not found
    """
    m = (market or '').strip()
    if not m:
        return None

    s = _normalize_for_match(m, symbol)
    if not s:
        return None

    # Crypto: allow user to pass BTC (try BTC/USDT) or full pair
    candidate_symbols = [s]
    if m == 'Crypto' and '/' not in s:
        candidate_symbols.append(f"{s}/USDT")

    try:
        with _get_db_connection() as db:
            cur = db.cursor()
            for cand in candidate_symbols:
                cur.execute(
                    "SELECT name FROM qd_market_symbols WHERE market = ? AND UPPER(symbol) = ?",
                    (m, cand.upper())
                )
                row = cur.fetchone()
                if row and row.get('name'):
                    cur.close()
                    return str(row['name'])
            cur.close()
    except Exception as e:
        logger.debug(f"get_symbol_name from DB failed: {e}")

    for row in _fallback_symbols(m):
        if str(row.get('symbol') or '').upper() in candidate_symbols:
            return str(row.get('name') or '') or None

    return None


def get_all_symbols(market: str = None) -> List[Dict]:
    """
    Get all active symbols, optionally filtered by market.
    
    Args:
        market: Optional market filter
        
    Returns:
        List of symbol records
    """
    try:
        with _get_db_connection() as db:
            cur = db.cursor()
            if market:
                cur.execute(
                    """
                    SELECT market, symbol, name, exchange, currency, is_hot, sort_order, instrument_type, lot_size, price_tick_json
                    FROM qd_market_symbols
                    WHERE market = ? AND is_active = 1
                    ORDER BY sort_order DESC
                    """,
                    (market.strip(),)
                )
            else:
                cur.execute(
                    """
                    SELECT market, symbol, name, exchange, currency, is_hot, sort_order, instrument_type, lot_size, price_tick_json
                    FROM qd_market_symbols
                    WHERE is_active = 1
                    ORDER BY market, sort_order DESC
                    """
                )
            rows = cur.fetchall() or []
            cur.close()
            return [dict(r) for r in rows]
    except Exception as e:
        logger.debug(f"get_all_symbols from DB failed: {e}")
        return _fallback_symbols(market)
