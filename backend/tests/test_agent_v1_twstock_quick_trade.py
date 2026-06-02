"""Tests for TWStock paper-only quick trade guards."""
from __future__ import annotations

from app.routes.agent_v1 import quick_trade
from app.utils import agent_auth
from tests.test_agent_v1 import _bearer, _fake_token_row


def _enable_t_scope(monkeypatch):
    agent_auth._schema_ready = True
    monkeypatch.setattr(agent_auth, "_lookup_token", lambda raw: _fake_token_row(scopes="T", paper_only=True))
    monkeypatch.setattr(agent_auth, "_touch_token_last_used", lambda *_: None)
    monkeypatch.setattr(agent_auth, "_audit", lambda *a, **kw: None)
    monkeypatch.setattr(quick_trade, "market_allowed", lambda market: True)
    monkeypatch.setattr(quick_trade, "instrument_allowed", lambda symbol: True)
    monkeypatch.setattr(quick_trade, "with_idempotency", lambda kind: _NoIdempotency())


class _NoIdempotency:
    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, tb):
        return False


def test_twstock_quick_trade_requires_limit_order(client, monkeypatch):
    _enable_t_scope(monkeypatch)

    resp = client.post(
        "/api/agent/v1/quick-trade/orders",
        headers=_bearer({"Content-Type": "application/json"}),
        json={"market": "TWStock", "symbol": "2330", "side": "buy", "qty": 1000, "order_type": "market"},
    )

    assert resp.status_code == 400
    assert "require order_type='limit'" in resp.get_json()["message"]


def test_twstock_quick_trade_requires_lot_multiple(client, monkeypatch):
    _enable_t_scope(monkeypatch)

    resp = client.post(
        "/api/agent/v1/quick-trade/orders",
        headers=_bearer({"Content-Type": "application/json"}),
        json={"market": "TWStock", "symbol": "2330", "side": "buy", "qty": 1500, "order_type": "limit", "limit_price": 100},
    )

    assert resp.status_code == 400
    assert "multiple of 1000" in resp.get_json()["message"]


def test_twstock_quick_trade_blocks_short_sell(client, monkeypatch):
    _enable_t_scope(monkeypatch)

    resp = client.post(
        "/api/agent/v1/quick-trade/orders",
        headers=_bearer({"Content-Type": "application/json"}),
        json={
            "market": "TWStock",
            "symbol": "2330.TW",
            "side": "sell",
            "qty": 2000,
            "current_qty": 1000,
            "order_type": "limit",
            "limit_price": 100,
        },
    )

    assert resp.status_code == 400
    assert "sell qty cannot exceed current_qty" in resp.get_json()["message"]


def test_twstock_quick_trade_records_valid_paper_order(client, monkeypatch):
    _enable_t_scope(monkeypatch)
    recorded = {}

    def fake_record(*, body, fill_price, status, note=""):
        recorded.update({"body": dict(body), "fill_price": fill_price, "status": status, "note": note})
        return {
            "order_uid": "paper-1",
            "market": body["market"],
            "symbol": body["symbol"],
            "side": body["side"],
            "order_type": body["order_type"],
            "qty": float(body["qty"]),
            "limit_price": float(body["limit_price"]),
            "fill_price": fill_price,
            "fill_value": fill_price * float(body["qty"]),
            "status": status,
            "paper": True,
            "note": note,
        }

    monkeypatch.setattr(quick_trade, "_twstock_last_price", lambda symbol: 250.0)
    monkeypatch.setattr(quick_trade, "_record_paper_order", fake_record)

    resp = client.post(
        "/api/agent/v1/quick-trade/orders",
        headers=_bearer({"Content-Type": "application/json"}),
        json={"market": "TWStock", "symbol": "TWStock:2317", "side": "buy", "qty": 6000, "order_type": "limit", "limit_price": 251.25},
    )

    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["market"] == "TWStock"
    assert data["symbol"] == "2317"
    assert data["paper"] is True
    assert data["fill_price"] == 250.0
    assert recorded["status"] == "filled"

def test_twstock_quick_trade_accepts_preview_order_shape(client, monkeypatch):
    _enable_t_scope(monkeypatch)
    monkeypatch.setattr(quick_trade, "_twstock_last_price", lambda symbol: 250.0)
    monkeypatch.setattr(
        quick_trade,
        "_record_paper_order",
        lambda *, body, fill_price, status, note="": {
            "order_uid": "paper-preview-1",
            "market": body["market"],
            "symbol": body["symbol"],
            "side": body["side"],
            "order_type": body["order_type"],
            "qty": float(body["qty"]),
            "limit_price": float(body["limit_price"]),
            "fill_price": fill_price,
            "fill_value": fill_price * float(body["qty"]),
            "status": status,
            "paper": True,
            "note": note,
        },
    )
    preview_order = {
        "symbol": "2317",
        "side": "buy",
        "qty": 6000,
        "order_type": "limit",
        "limit_price": 251.25,
    }
    payload = {"market": "TWStock", **preview_order}

    resp = client.post(
        "/api/agent/v1/quick-trade/orders",
        headers=_bearer({"Content-Type": "application/json"}),
        json=payload,
    )

    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["symbol"] == "2317"
    assert data["qty"] == 6000.0
    assert data["limit_price"] == 251.25
    assert data["status"] == "filled"


def test_twstock_quick_trade_sell_uses_server_position_when_current_qty_missing(client, monkeypatch):
    _enable_t_scope(monkeypatch)
    looked_up = []

    monkeypatch.setattr(quick_trade, "_twstock_position_qty", lambda symbol: looked_up.append(symbol) or 3000)
    monkeypatch.setattr(quick_trade, "_twstock_last_price", lambda symbol: 100.0)
    monkeypatch.setattr(
        quick_trade,
        "_record_paper_order",
        lambda *, body, fill_price, status, note="": {
            "order_uid": "paper-sell-1",
            "market": body["market"],
            "symbol": body["symbol"],
            "side": body["side"],
            "order_type": body["order_type"],
            "qty": float(body["qty"]),
            "limit_price": float(body["limit_price"]),
            "fill_price": fill_price,
            "fill_value": fill_price * float(body["qty"]),
            "status": status,
            "paper": True,
            "note": note,
            "current_qty": body["current_qty"],
        },
    )

    resp = client.post(
        "/api/agent/v1/quick-trade/orders",
        headers=_bearer({"Content-Type": "application/json"}),
        json={"market": "TWStock", "symbol": "TWStock:2330", "side": "sell", "qty": 2000, "order_type": "limit", "limit_price": 99},
    )

    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert looked_up == ["2330"]
    assert data["current_qty"] == 3000
    assert data["side"] == "sell"


def test_twstock_quick_trade_sell_rejects_when_server_position_insufficient(client, monkeypatch):
    _enable_t_scope(monkeypatch)
    monkeypatch.setattr(quick_trade, "_twstock_position_qty", lambda symbol: 1000)

    resp = client.post(
        "/api/agent/v1/quick-trade/orders",
        headers=_bearer({"Content-Type": "application/json"}),
        json={"market": "TWStock", "symbol": "2330.TW", "side": "sell", "qty": 2000, "order_type": "limit", "limit_price": 99},
    )

    assert resp.status_code == 400
    assert "sell qty cannot exceed current_qty" in resp.get_json()["message"]


def test_twstock_quick_trade_sell_keeps_request_current_qty_without_lookup(client, monkeypatch):
    _enable_t_scope(monkeypatch)

    def fail_lookup(symbol):
        raise AssertionError("server position lookup should not be called when current_qty is provided")

    monkeypatch.setattr(quick_trade, "_twstock_position_qty", fail_lookup)
    monkeypatch.setattr(quick_trade, "_twstock_last_price", lambda symbol: 100.0)
    monkeypatch.setattr(
        quick_trade,
        "_record_paper_order",
        lambda *, body, fill_price, status, note="": {
            "order_uid": "paper-sell-2",
            "market": body["market"],
            "symbol": body["symbol"],
            "side": body["side"],
            "order_type": body["order_type"],
            "qty": float(body["qty"]),
            "limit_price": float(body["limit_price"]),
            "fill_price": fill_price,
            "fill_value": fill_price * float(body["qty"]),
            "status": status,
            "paper": True,
            "note": note,
        },
    )

    resp = client.post(
        "/api/agent/v1/quick-trade/orders",
        headers=_bearer({"Content-Type": "application/json"}),
        json={"market": "TWStock", "symbol": "2330", "side": "sell", "qty": 2000, "current_qty": 3000, "order_type": "limit", "limit_price": 99},
    )

    assert resp.status_code == 200
    assert resp.get_json()["data"]["status"] == "filled"


def test_twstock_quick_trade_rejects_buy_when_last_price_above_limit(client, monkeypatch):
    _enable_t_scope(monkeypatch)
    recorded = {}

    def fake_record(*, body, fill_price, status, note=""):
        recorded.update({"fill_price": fill_price, "status": status, "note": note})
        return {
            "order_uid": "paper-limit-reject-buy",
            "market": body["market"],
            "symbol": body["symbol"],
            "side": body["side"],
            "order_type": body["order_type"],
            "qty": float(body["qty"]),
            "limit_price": float(body["limit_price"]),
            "fill_price": fill_price,
            "fill_value": None,
            "status": status,
            "paper": True,
            "note": note,
        }

    monkeypatch.setattr(quick_trade, "_twstock_last_price", lambda symbol: 2255.0)
    monkeypatch.setattr(quick_trade, "_record_paper_order", fake_record)

    resp = client.post(
        "/api/agent/v1/quick-trade/orders",
        headers=_bearer({"Content-Type": "application/json"}),
        json={"market": "TWStock", "symbol": "2330", "side": "buy", "qty": 2000, "order_type": "limit", "limit_price": 1005},
    )

    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["status"] == "rejected"
    assert data["fill_price"] is None
    assert "last_price 2255.0 > buy limit 1005.0" in data["note"]
    assert recorded["status"] == "rejected"


def test_twstock_quick_trade_rejects_sell_when_last_price_below_limit(client, monkeypatch):
    _enable_t_scope(monkeypatch)
    monkeypatch.setattr(quick_trade, "_twstock_last_price", lambda symbol: 90.0)
    monkeypatch.setattr(
        quick_trade,
        "_record_paper_order",
        lambda *, body, fill_price, status, note="": {
            "order_uid": "paper-limit-reject-sell",
            "market": body["market"],
            "symbol": body["symbol"],
            "side": body["side"],
            "order_type": body["order_type"],
            "qty": float(body["qty"]),
            "limit_price": float(body["limit_price"]),
            "fill_price": fill_price,
            "fill_value": None,
            "status": status,
            "paper": True,
            "note": note,
        },
    )

    resp = client.post(
        "/api/agent/v1/quick-trade/orders",
        headers=_bearer({"Content-Type": "application/json"}),
        json={"market": "TWStock", "symbol": "2330", "side": "sell", "qty": 1000, "current_qty": 2000, "order_type": "limit", "limit_price": 100},
    )

    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["status"] == "rejected"
    assert data["fill_price"] is None
    assert "last_price 90.0 < sell limit 100.0" in data["note"]

