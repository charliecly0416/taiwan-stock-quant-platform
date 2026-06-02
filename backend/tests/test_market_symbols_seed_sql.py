"""Offline checks for qd_market_symbols bootstrap seed SQL."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INIT_SQL = ROOT / "migrations" / "init.sql"


def _sql() -> str:
    return INIT_SQL.read_text(encoding="utf-8")


def test_market_symbols_table_keeps_unique_market_symbol_constraint():
    sql = _sql()

    assert "CREATE TABLE IF NOT EXISTS qd_market_symbols" in sql
    assert "UNIQUE(market, symbol)" in sql
    assert "ON CONFLICT (market, symbol) DO NOTHING" in sql


def test_twstock_hot_symbols_are_seeded():
    sql = _sql()

    expected_rows = [
        "('TWStock', '2330', '台積電', 'TWSE', 'TWD', 1, 1, 100)",
        "('TWStock', '2317', '鴻海', 'TWSE', 'TWD', 1, 1, 99)",
        "('TWStock', '2454', '聯發科', 'TWSE', 'TWD', 1, 1, 98)",
        "('TWStock', '0050', '元大台灣50', 'TWSE', 'TWD', 1, 1, 91)",
        "('TWStock', '0056', '元大高股息', 'TWSE', 'TWD', 1, 1, 90)",
        "('TWStock', '00878', '國泰永續高股息', 'TWSE', 'TWD', 1, 1, 89)",
    ]
    for row in expected_rows:
        assert row in sql

    assert sql.count("('TWStock',") == 12


def test_twstock_seed_is_before_moex_and_uses_twd():
    sql = _sql()

    tw_pos = sql.index("-- 台股 (TWStock) large caps and ETFs")
    moex_pos = sql.index("-- MOEX (Moscow Exchange) blue chips")
    assert tw_pos < moex_pos

    tw_block = sql[tw_pos:moex_pos]
    assert "'TWD'" in tw_block
    assert "'USD'" not in tw_block
    assert "'HKD'" not in tw_block


def test_market_symbols_schema_has_twstock_metadata_columns():
    sql = _sql()

    assert "instrument_type VARCHAR(32) DEFAULT ''" in sql
    assert "lot_size INTEGER DEFAULT 1" in sql
    assert "price_tick_json TEXT DEFAULT ''" in sql
    assert "ALTER TABLE qd_market_symbols ADD COLUMN IF NOT EXISTS instrument_type" in sql
    assert "ALTER TABLE qd_market_symbols ADD COLUMN IF NOT EXISTS lot_size" in sql
    assert "ALTER TABLE qd_market_symbols ADD COLUMN IF NOT EXISTS price_tick_json" in sql


def test_twstock_seed_metadata_is_backfilled_idempotently():
    sql = _sql()

    assert "UPDATE qd_market_symbols" in sql
    assert "WHERE market = 'TWStock'" in sql
    assert "lot_size = 1000" in sql
    assert "WHEN symbol IN ('0050', '0056', '00878') THEN 'etf'" in sql
    assert "ELSE 'stock'" in sql
    assert '"source":"twse_default"' in sql



def test_twstock_daily_archive_table_schema_exists():
    sql = _sql()

    assert "CREATE TABLE IF NOT EXISTS qd_tw_stock_daily_bars" in sql
    assert "trade_date DATE NOT NULL" in sql
    assert "source VARCHAR(32) NOT NULL DEFAULT 'finmind'" in sql
    assert "official_checked INTEGER NOT NULL DEFAULT 0" in sql
    assert "official_match INTEGER NOT NULL DEFAULT 0" in sql
    assert "raw_json JSONB" in sql
    assert "UNIQUE(symbol, trade_date, source)" in sql
    assert "idx_tw_stock_daily_symbol_date" in sql
    assert "idx_tw_stock_daily_quality" in sql


def test_twstock_corporate_actions_table_schema_exists():
    sql = _sql()

    assert "CREATE TABLE IF NOT EXISTS qd_tw_stock_corporate_actions" in sql
    assert "action_date DATE NOT NULL" in sql
    assert "before_price DECIMAL(20,6) NOT NULL" in sql
    assert "after_price DECIMAL(20,6) NOT NULL" in sql
    assert "cash_or_stock_dividend DECIMAL(20,6) DEFAULT 0" in sql
    assert "adjustment_factor DECIMAL(20,12) NOT NULL" in sql
    assert "UNIQUE(symbol, action_date, source)" in sql
    assert "idx_tw_stock_ca_symbol_date" in sql
    assert "idx_tw_stock_ca_quality" in sql


def test_twstock_institutional_trades_table_schema_exists():
    sql = _sql()

    assert "CREATE TABLE IF NOT EXISTS qd_tw_stock_institutional_trades" in sql
    assert "foreign_net_buy BIGINT DEFAULT 0" in sql
    assert "investment_trust_net_buy BIGINT DEFAULT 0" in sql
    assert "dealer_self_net_buy BIGINT DEFAULT 0" in sql
    assert "dealer_hedging_net_buy BIGINT DEFAULT 0" in sql
    assert "dealer_net_buy BIGINT DEFAULT 0" in sql
    assert "total_institutional_net_buy BIGINT DEFAULT 0" in sql
    assert "UNIQUE(symbol, trade_date, source)" in sql
    assert "idx_tw_stock_inst_symbol_date" in sql
    assert "idx_tw_stock_inst_quality" in sql


def test_twstock_margin_trading_table_schema_exists():
    sql = _sql()

    assert "CREATE TABLE IF NOT EXISTS qd_tw_stock_margin_trading" in sql
    assert "margin_purchase_buy BIGINT DEFAULT 0" in sql
    assert "margin_purchase_today_balance BIGINT DEFAULT 0" in sql
    assert "short_sale_sell BIGINT DEFAULT 0" in sql
    assert "short_sale_today_balance BIGINT DEFAULT 0" in sql
    assert "offset_loan_and_short BIGINT DEFAULT 0" in sql
    assert "UNIQUE(symbol, trade_date, source)" in sql
    assert "idx_tw_stock_margin_symbol_date" in sql
    assert "idx_tw_stock_margin_quality" in sql


def test_twstock_monthly_revenue_table_schema_exists():
    sql = _sql()

    assert "CREATE TABLE IF NOT EXISTS qd_tw_stock_monthly_revenue" in sql
    assert "revenue_period VARCHAR(7) NOT NULL" in sql
    assert "monthly_revenue BIGINT NOT NULL DEFAULT 0" in sql
    assert "mom_growth DECIMAL(20,8)" in sql
    assert "yoy_growth DECIMAL(20,8)" in sql
    assert "UNIQUE(symbol, revenue_period, source)" in sql
    assert "idx_tw_stock_revenue_symbol_period" in sql
    assert "idx_tw_stock_revenue_quality" in sql


def test_twstock_valuation_table_schema_exists():
    sql = _sql()

    assert "CREATE TABLE IF NOT EXISTS qd_tw_stock_valuation" in sql
    assert "pe DECIMAL(20,8)" in sql
    assert "pb DECIMAL(20,8)" in sql
    assert "dividend_yield DECIMAL(20,8)" in sql
    assert "UNIQUE(symbol, trade_date, source)" in sql
    assert "idx_tw_stock_valuation_symbol_date" in sql
    assert "idx_tw_stock_valuation_quality" in sql
