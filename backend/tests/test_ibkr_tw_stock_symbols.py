"""Tests for IBKR TWStock symbol mapping."""
from app.services.ibkr_trading.symbols import format_display_symbol, normalize_symbol, parse_symbol


def test_normalize_twstock_symbol_defaults_to_twse_twd():
    assert normalize_symbol("2330", "TWStock") == ("2330", "TWSE", "TWD")
    assert normalize_symbol("TWStock:2330", "TWStock") == ("2330", "TWSE", "TWD")
    assert normalize_symbol("2330.TW", "TWStock") == ("2330", "TWSE", "TWD")
    assert normalize_symbol("TWSE:2330", "TWStock") == ("2330", "TWSE", "TWD")


def test_normalize_twstock_symbol_preserves_tpex_exchange():
    assert normalize_symbol("TPEX:6488", "TWStock") == ("6488", "TPEX", "TWD")
    assert normalize_symbol("6488.TPEX", "TWStock") == ("6488", "TPEX", "TWD")


def test_parse_symbol_detects_twstock_codes_before_us_default():
    assert parse_symbol("2330.TW") == ("2330", "TWStock")
    assert parse_symbol("TPEX:6488") == ("6488", "TWStock")
    assert parse_symbol("AAPL") == ("AAPL", "USStock")


def test_format_display_symbol_adds_taiwan_suffix():
    assert format_display_symbol("2330", "TWSE") == "2330.TW"
    assert format_display_symbol("6488", "TPEX") == "6488.TPEX"
    assert format_display_symbol("AAPL", "SMART") == "AAPL"
