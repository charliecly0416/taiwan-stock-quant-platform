"""Route-level coverage for exposing TWStock market metadata and symbols."""
from __future__ import annotations

import pytest

from app.routes import market as market_routes
from app.routes.agent_v1 import markets as agent_markets
from app.utils import agent_auth


def test_market_types_include_twstock_by_default(client, monkeypatch):
    monkeypatch.delenv("ENABLED_MARKETS", raising=False)
    monkeypatch.delenv("SHOW_CN_STOCK", raising=False)
    monkeypatch.delenv("SHOW_HK_STOCK", raising=False)

    resp = client.get("/api/market/types")

    assert resp.status_code == 200
    body = resp.get_json()
    values = [item["value"] for item in body["data"]]
    assert "TWStock" in values
    assert values.index("USStock") < values.index("TWStock") < values.index("Crypto")


def test_market_types_respect_enabled_markets_for_twstock(client, monkeypatch):
    monkeypatch.setenv("ENABLED_MARKETS", "TWStock,Crypto")

    resp = client.get("/api/market/types")

    assert resp.status_code == 200
    values = [item["value"] for item in resp.get_json()["data"]]
    assert values == ["TWStock", "Crypto"]


def test_twstock_symbol_search_and_hot_routes_use_seed_table(client, monkeypatch):
    monkeypatch.setattr(
        market_routes,
        "seed_search_symbols",
        lambda market, keyword, limit: [
            {"market": market, "symbol": "2330", "name": "台積電"},
            {"market": market, "symbol": "2330B", "name": "台積電乙特"},
        ][:limit],
    )
    monkeypatch.setattr(
        market_routes,
        "seed_get_hot_symbols",
        lambda market, limit: [
            {"market": market, "symbol": "2330", "name": "台積電"},
            {"market": market, "symbol": "0050", "name": "元大台灣50"},
        ][:limit],
    )

    search = client.get("/api/market/symbols/search?market=TWStock&keyword=2330&limit=1")
    hot = client.get("/api/market/symbols/hot?market=TWStock&limit=2")

    assert search.status_code == 200
    assert search.get_json()["data"] == [{"market": "TWStock", "symbol": "2330", "name": "台積電"}]
    assert hot.status_code == 200
    assert [item["symbol"] for item in hot.get_json()["data"]] == ["2330", "0050"]


@pytest.mark.parametrize(
    "market,symbol,expected",
    [
        ("TWStock", "2330", None),
        ("TWStock", "00878", None),
        ("TWStock", "006208", None),
        ("USStock", "006208", "CNStock or TWStock"),
    ],
)
def test_watchlist_validation_allows_six_digit_twstock_codes(market, symbol, expected):
    err = market_routes._validate_watchlist_pair(market, symbol)
    if expected is None:
        assert err is None
    else:
        assert expected in err


def _fake_agent_token(markets: str = "*") -> dict:
    return {
        "id": 999,
        "user_id": 1,
        "name": "test-agent",
        "scopes": "R",
        "markets": markets,
        "instruments": "*",
        "paper_only": True,
        "rate_limit_per_min": 60,
        "status": "active",
        "expires_at": None,
    }


def test_agent_markets_include_twstock(client, monkeypatch):
    agent_auth._schema_ready = True
    monkeypatch.setattr(agent_auth, "_lookup_token", lambda _raw: _fake_agent_token())
    monkeypatch.setattr(agent_auth, "_touch_token_last_used", lambda *_: None)
    monkeypatch.setattr(agent_auth, "_audit", lambda *a, **kw: None)
    monkeypatch.delenv("ENABLED_MARKETS", raising=False)

    resp = client.get(
        "/api/agent/v1/markets",
        headers={"Authorization": "Bearer qd_agent_TESTTOKEN12345"},
    )

    assert resp.status_code == 200
    values = [item["value"] for item in resp.get_json()["data"]]
    assert "TWStock" in values


def test_agent_twstock_symbols_route_uses_seed_table(client, monkeypatch):
    agent_auth._schema_ready = True
    monkeypatch.setattr(agent_auth, "_lookup_token", lambda _raw: _fake_agent_token(markets="TWStock"))
    monkeypatch.setattr(agent_auth, "_touch_token_last_used", lambda *_: None)
    monkeypatch.setattr(agent_auth, "_audit", lambda *a, **kw: None)
    monkeypatch.setattr(
        agent_markets,
        "seed_search_symbols",
        lambda market, keyword, limit: [{"market": market, "symbol": "0050", "name": "元大台灣50"}],
    )

    resp = client.get(
        "/api/agent/v1/markets/TWStock/symbols?keyword=0050",
        headers={"Authorization": "Bearer qd_agent_TESTTOKEN12345"},
    )

    assert resp.status_code == 200
    assert resp.get_json()["data"] == [{"market": "TWStock", "symbol": "0050", "name": "元大台灣50"}]



def test_twstock_seed_fallbacks_work_without_database(monkeypatch):
    from app.data import market_symbols_seed

    def fail_db():
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(market_symbols_seed, "_get_db_connection", fail_db)

    hot = market_symbols_seed.get_hot_symbols("TWStock", limit=3)
    search_code = market_symbols_seed.search_symbols("TWStock", "2330", limit=5)
    search_name = market_symbols_seed.search_symbols("TWStock", "台積", limit=5)
    all_tw = market_symbols_seed.get_all_symbols("TWStock")

    assert [item["symbol"] for item in hot] == ["2330", "2317", "2454"]
    assert search_code == [{"market": "TWStock", "symbol": "2330", "name": "台積電"}]
    assert search_name == [{"market": "TWStock", "symbol": "2330", "name": "台積電"}]
    assert market_symbols_seed.get_symbol_name("TWStock", "0050") == "元大台灣50"
    assert len(all_tw) == 12
    assert {item["symbol"]: item["instrument_type"] for item in all_tw}["00878"] == "etf"
    assert all_tw[0]["lot_size"] == 1000
