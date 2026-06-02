"""Tests for Agent paper position summaries."""
from __future__ import annotations

from app.routes.agent_v1 import portfolio
from app.utils import agent_auth
from tests.test_agent_v1 import _bearer, _fake_token_row


class _NoopCursor:
    def __init__(self, rows):
        self.rows = rows

    def execute(self, sql, params=None):
        self.sql = sql
        self.params = params

    def fetchall(self):
        return self.rows

    def close(self):
        return None


class _NoopConnection:
    def __init__(self, rows):
        self.rows = rows

    def cursor(self):
        return _NoopCursor(self.rows)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _enable_r_scope(monkeypatch):
    agent_auth._schema_ready = True
    monkeypatch.setattr(agent_auth, "_ensure_schema", lambda: None)
    monkeypatch.setattr(agent_auth, "_lookup_token", lambda raw: _fake_token_row(scopes="R", paper_only=True))
    monkeypatch.setattr(agent_auth, "_touch_token_last_used", lambda *_: None)
    monkeypatch.setattr(agent_auth, "_audit", lambda *a, **kw: None)


def test_build_paper_positions_weighted_average_and_sell():
    report = portfolio._build_paper_positions([
        {"order_uid": "b1", "market": "TWStock", "symbol": "2317", "side": "buy", "qty": 1000, "fill_price": 100, "status": "filled"},
        {"order_uid": "b2", "market": "TWStock", "symbol": "2317", "side": "buy", "qty": 1000, "fill_price": 200, "status": "filled"},
        {"order_uid": "s1", "market": "TWStock", "symbol": "2317", "side": "sell", "qty": 500, "fill_price": 220, "status": "filled"},
        {"order_uid": "r1", "market": "TWStock", "symbol": "2330", "side": "buy", "qty": 1000, "fill_price": 800, "status": "rejected"},
    ])

    assert report["warnings"] == []
    assert report["positions"] == [{
        "market": "TWStock",
        "symbol": "2317",
        "quantity": 1500.0,
        "avg_price": 150.0,
        "cost_value": 225000.0,
        "currency": "TWD",
        "source": "agent_paper_orders",
        "order_count": 3,
    }]


def test_build_paper_positions_records_oversell_warning_without_negative_position():
    report = portfolio._build_paper_positions([
        {"order_uid": "b1", "market": "TWStock", "symbol": "2317", "side": "buy", "qty": 1000, "fill_price": 100, "status": "filled"},
        {"order_uid": "s1", "market": "TWStock", "symbol": "2317", "side": "sell", "qty": 2000, "fill_price": 90, "status": "filled"},
    ])

    assert report["positions"] == []
    assert report["warnings"] == ["paper_position_oversell:TWStock:2317"]


def test_paper_positions_endpoint_returns_derived_positions(client, monkeypatch):
    _enable_r_scope(monkeypatch)
    rows = [
        {"order_uid": "b1", "market": "TWStock", "symbol": "2317", "side": "buy", "qty": 6000, "fill_price": 250, "status": "filled"},
    ]
    monkeypatch.setattr(portfolio, "get_db_connection", lambda: _NoopConnection(rows))

    resp = client.get("/api/agent/v1/portfolio/paper-positions", headers=_bearer())

    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["warnings"] == []
    assert data["positions"][0]["market"] == "TWStock"
    assert data["positions"][0]["symbol"] == "2317"
    assert data["positions"][0]["quantity"] == 6000.0
    assert data["positions"][0]["avg_price"] == 250.0

def test_build_paper_summary_tracks_cash_open_cost_and_realized_pnl():
    summary = portfolio._build_paper_summary([
        {"order_uid": "b1", "market": "TWStock", "symbol": "2317", "side": "buy", "qty": 1000, "fill_price": 100, "status": "filled"},
        {"order_uid": "b2", "market": "TWStock", "symbol": "2317", "side": "buy", "qty": 1000, "fill_price": 200, "status": "filled"},
        {"order_uid": "s1", "market": "TWStock", "symbol": "2317", "side": "sell", "qty": 500, "fill_price": 220, "status": "filled"},
    ], initial_cash=500000)

    assert summary["initial_cash"] == 500000.0
    assert summary["gross_buy_value"] == 300000.0
    assert summary["gross_sell_value"] == 110000.0
    assert summary["cash"] == 310000.0
    assert summary["realized_pnl"] == 35000.0
    assert summary["open_cost_value"] == 225000.0
    assert summary["equity_at_cost"] == 535000.0
    assert summary["filled_order_count"] == 3
    assert summary["position_count"] == 1
    assert summary["positions"][0]["quantity"] == 1500.0
    assert summary["positions"][0]["avg_price"] == 150.0


def test_paper_summary_endpoint_returns_cash_and_positions(client, monkeypatch):
    _enable_r_scope(monkeypatch)
    rows = [
        {"order_uid": "b1", "market": "TWStock", "symbol": "2317", "side": "buy", "qty": 6000, "fill_price": 250, "status": "filled"},
    ]
    monkeypatch.setattr(portfolio, "get_db_connection", lambda: _NoopConnection(rows))

    resp = client.get("/api/agent/v1/portfolio/paper-summary?initial_cash=5000000", headers=_bearer())

    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["initial_cash"] == 5000000.0
    assert data["cash"] == 3500000.0
    assert data["open_cost_value"] == 1500000.0
    assert data["equity_at_cost"] == 5000000.0
    assert data["positions"][0]["symbol"] == "2317"


def test_paper_summary_endpoint_rejects_invalid_initial_cash(client, monkeypatch):
    _enable_r_scope(monkeypatch)

    resp = client.get("/api/agent/v1/portfolio/paper-summary?initial_cash=bad", headers=_bearer())

    assert resp.status_code == 400
    assert "initial_cash must be numeric" in resp.get_json()["message"]

