"""Loopback test for TWStock paper submit -> Agent route -> read-back verification.

This is an API-level offline loopback: it uses Flask's test client and an
in-memory fake DB so CI/local runs do not need PostgreSQL. It still exercises
our real Agent routes plus the submit/verify scripts' HTTP-facing behavior.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from app.routes.agent_v1 import portfolio, quick_trade
from app.utils import agent_auth
from tests.test_agent_v1 import _fake_token_row


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"


def _load_script(name: str):
    path = SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


submit_tw_stock_paper_orders = _load_script("submit_tw_stock_paper_orders")
verify_tw_stock_paper_orders = _load_script("verify_tw_stock_paper_orders")


class _MemoryCursor:
    def __init__(self, store):
        self.store = store
        self._row = None
        self.rowcount = 0

    def execute(self, sql, params=None):
        normalized = " ".join(sql.lower().split())
        params = params or ()
        if "insert into qd_agent_paper_orders" in normalized:
            (
                order_uid,
                user_id,
                agent_token_id,
                market,
                symbol,
                side,
                order_type,
                qty,
                limit_price,
                fill_price,
                fill_value,
                status,
                note,
            ) = params
            self.store["paper_orders"].insert(0, {
                "order_uid": order_uid,
                "user_id": user_id,
                "agent_token_id": agent_token_id,
                "market": market,
                "symbol": symbol,
                "side": side,
                "order_type": order_type,
                "qty": qty,
                "limit_price": limit_price,
                "fill_price": fill_price,
                "fill_value": fill_value,
                "status": status,
                "note": note,
                "created_at": "2026-05-23T00:00:00Z",
            })
            self.rowcount = 1
            return
        if "from qd_agent_paper_orders" in normalized and "where user_id" in normalized:
            user_id = int(params[0])
            self._row = [item for item in self.store["paper_orders"] if int(item["user_id"]) == user_id]
            return
        if "from qd_user_positions" in normalized:
            self._row = {"quantity": 0}
            return
        self._row = None

    def fetchone(self):
        if isinstance(self._row, list):
            return self._row[0] if self._row else None
        return self._row

    def fetchall(self):
        return self._row if isinstance(self._row, list) else []

    def close(self):
        return None


class _MemoryConnection:
    def __init__(self, store):
        self.store = store

    def cursor(self):
        return _MemoryCursor(self.store)

    def commit(self):
        return None

    def rollback(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _ClientResponse:
    def __init__(self, flask_response):
        self.status_code = flask_response.status_code
        self.text = flask_response.get_data(as_text=True)
        self._flask_response = flask_response

    def json(self):
        return self._flask_response.get_json()


def test_twstock_paper_submit_and_verify_loopback(client, monkeypatch):
    store = {"paper_orders": []}
    token = _fake_token_row(scopes="R,T", paper_only=True)

    agent_auth._schema_ready = True
    monkeypatch.setattr(agent_auth, "_ensure_schema", lambda: None)
    monkeypatch.setattr(agent_auth, "_lookup_token", lambda raw: token)
    monkeypatch.setattr(agent_auth, "_touch_token_last_used", lambda *_: None)
    monkeypatch.setattr(agent_auth, "_audit", lambda *a, **kw: None)
    monkeypatch.setattr(quick_trade, "market_allowed", lambda market: True)
    monkeypatch.setattr(quick_trade, "instrument_allowed", lambda symbol: True)
    monkeypatch.setattr(quick_trade, "with_idempotency", lambda kind: _NoIdempotency())
    monkeypatch.setattr(quick_trade, "_twstock_last_price", lambda symbol: 250.0)
    monkeypatch.setattr(quick_trade, "get_db_connection", lambda: _MemoryConnection(store))
    monkeypatch.setattr(portfolio, "get_db_connection", lambda: _MemoryConnection(store))

    def fake_post(url, headers, json, timeout):
        return _ClientResponse(client.post(
            "/api/agent/v1/quick-trade/orders",
            headers={"Authorization": headers["Authorization"], "Content-Type": "application/json"},
            json=json,
        ))

    def fake_get(url, headers, timeout):
        return _ClientResponse(client.get(
            "/api/agent/v1/portfolio/paper-orders",
            headers={"Authorization": headers["Authorization"]},
        ))

    monkeypatch.setattr(submit_tw_stock_paper_orders.requests, "post", fake_post)
    monkeypatch.setattr(verify_tw_stock_paper_orders.requests, "get", fake_get)

    payloads = [{
        "market": "TWStock",
        "symbol": "TWStock:2317",
        "side": "buy",
        "qty": 6000,
        "order_type": "limit",
        "limit_price": 251.25,
        "lot_size": 1000,
        "source": "loopback_test",
    }]
    submit_results = submit_tw_stock_paper_orders.submit_payloads(
        payloads=payloads,
        api_base_url="http://loopback.local",
        agent_token="qd_agent_TESTTOKEN12345",
        timeout=3,
    )

    assert submit_results[0]["ok"] is True
    submitted_uid = submit_results[0]["response"]["data"]["order_uid"]
    assert store["paper_orders"][0]["order_uid"] == submitted_uid
    assert store["paper_orders"][0]["symbol"] == "2317"

    fetched = verify_tw_stock_paper_orders.fetch_paper_orders(
        api_base_url="http://loopback.local",
        agent_token="qd_agent_TESTTOKEN12345",
        timeout=3,
    )
    verify_report = verify_tw_stock_paper_orders.build_report(
        expected_order_uids=verify_tw_stock_paper_orders.extract_order_uids({"submit_results": submit_results}),
        fetched=fetched,
    )

    assert verify_report["matched_order_uids"] == [submitted_uid]
    assert verify_report["missing_order_uids"] == []
    assert verify_report["matched_orders"][0]["symbol"] == "2317"
    assert verify_report["matched_orders"][0]["market"] == "TWStock"


class _NoIdempotency:
    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, tb):
        return False
