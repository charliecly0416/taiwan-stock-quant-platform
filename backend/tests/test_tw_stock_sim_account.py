"""Tests for TWStock simulation-only account MVP."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from app.services.tw_stock_sim_account import TWStockSimAccountService


class SimCursor:
    def __init__(self, db):
        self.db = db
        self.row = None
        self.rows = []

    def execute(self, sql, params=None):
        compact = " ".join(str(sql).split())
        params = tuple(params or ())
        self.db.sql.append(compact)
        self.row = None
        self.rows = []
        if compact.startswith("CREATE TABLE"):
            return
        if compact.startswith("ALTER TABLE"):
            return
        if compact.startswith("INSERT INTO qd_tw_sim_accounts"):
            uid, user_id, name, initial_cash, cash, created_at, updated_at = params
            row = {
                "id": len(self.db.accounts) + 1,
                "account_uid": uid,
                "user_id": user_id,
                "name": name,
                "currency": "TWD",
                "initial_cash": Decimal(str(initial_cash)),
                "cash": Decimal(str(cash)),
                "simulation_only": True,
                "created_at": created_at,
                "updated_at": updated_at,
            }
            self.db.accounts[uid] = row
            self.row = dict(row)
            return
        if compact.startswith("SELECT * FROM qd_tw_sim_accounts WHERE user_id"):
            user_id = params[0]
            self.rows = [dict(row) for row in self.db.accounts.values() if row["user_id"] == user_id]
            return
        if compact.startswith("SELECT * FROM qd_tw_sim_accounts WHERE account_uid"):
            uid, user_id = params
            row = self.db.accounts.get(uid)
            self.row = dict(row) if row and row["user_id"] == user_id else None
            return
        if "FROM qd_tw_stock_daily_bars" in compact:
            symbol = params[0]
            price = self.db.prices.get(symbol)
            self.row = dict(price) if price else None
            return
        if compact.startswith("INSERT INTO qd_tw_sim_orders"):
            (
                uid,
                account_uid,
                user_id,
                symbol,
                side,
                quantity,
                status,
                source_type,
                source_context_json,
                reference_price,
                price_source,
                price_date,
                gross_amount,
                fee,
                tax,
                net_cash_effect,
                message,
                warnings,
                created_at,
                updated_at,
            ) = params
            row = {
                "id": len(self.db.sim_orders) + 1,
                "sim_order_uid": uid,
                "account_uid": account_uid,
                "user_id": user_id,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "status": status,
                "source_type": source_type,
                "source_context_json": source_context_json,
                "reference_price": Decimal(str(reference_price or 0)),
                "price_source": price_source,
                "price_date": price_date,
                "gross_amount": Decimal(str(gross_amount or 0)),
                "fee": Decimal(str(fee or 0)),
                "tax": Decimal(str(tax or 0)),
                "net_cash_effect": Decimal(str(net_cash_effect or 0)),
                "message": message,
                "warnings": warnings,
                "simulation_only": True,
                "created_at": created_at,
                "updated_at": updated_at,
                "filled_at": None,
            }
            self.db.sim_orders[uid] = row
            self.row = dict(row)
            return
        if compact.startswith("SELECT * FROM qd_tw_sim_orders"):
            uid, user_id = params
            row = self.db.sim_orders.get(uid)
            self.row = dict(row) if row and row["user_id"] == user_id else None
            return
        if compact.startswith("UPDATE qd_tw_sim_orders SET status = 'filled'"):
            updated_at, filled_at, uid = params
            row = self.db.sim_orders[uid]
            row["status"] = "filled"
            row["updated_at"] = updated_at
            row["filled_at"] = filled_at
            self.row = dict(row)
            return
        if compact.startswith("UPDATE qd_tw_sim_orders SET status = 'cancelled'"):
            updated_at, uid = params
            row = self.db.sim_orders[uid]
            row["status"] = "cancelled"
            row["updated_at"] = updated_at
            self.row = dict(row)
            return
        if compact.startswith("UPDATE qd_tw_sim_orders SET status = 'rejected'"):
            message, updated_at, uid = params
            row = self.db.sim_orders[uid]
            row["status"] = "rejected"
            row["message"] = message
            row["updated_at"] = updated_at
            self.row = dict(row)
            return
        if compact.startswith("SELECT quantity FROM qd_tw_sim_positions"):
            account_uid, symbol = params
            row = self.db.positions.get((account_uid, symbol))
            self.row = {"quantity": row["quantity"]} if row else None
            return
        if compact.startswith("SELECT * FROM qd_tw_sim_positions WHERE account_uid = ? AND symbol = ?"):
            account_uid, symbol = params
            row = self.db.positions.get((account_uid, symbol))
            self.row = dict(row) if row else None
            return
        if compact.startswith("SELECT * FROM qd_tw_sim_positions WHERE account_uid = ? AND quantity > 0"):
            account_uid = params[0]
            self.rows = [dict(row) for key, row in self.db.positions.items() if key[0] == account_uid and row["quantity"] > 0]
            return
        if compact.startswith("INSERT INTO qd_tw_sim_positions"):
            account_uid, symbol, quantity, avg_cost, cost_value, created_at, updated_at = params
            self.db.positions[(account_uid, symbol)] = {
                "id": len(self.db.positions) + 1,
                "account_uid": account_uid,
                "symbol": symbol,
                "quantity": quantity,
                "avg_cost": Decimal(str(avg_cost)),
                "cost_value": Decimal(str(cost_value)),
                "simulation_only": True,
                "created_at": created_at,
                "updated_at": updated_at,
            }
            return
        if compact.startswith("UPDATE qd_tw_sim_positions SET quantity"):
            quantity, cost_value_or_avg, maybe_cost_or_updated, *rest = params
            if len(rest) == 3:
                # buy update: quantity, avg_cost, cost_value, updated_at, account_uid, symbol
                avg_cost = Decimal(str(cost_value_or_avg))
                cost_value = Decimal(str(maybe_cost_or_updated))
                updated_at, account_uid, symbol = rest
                row = self.db.positions[(account_uid, symbol)]
                row.update({"quantity": quantity, "avg_cost": avg_cost, "cost_value": cost_value, "updated_at": updated_at})
            else:
                # sell update: quantity, cost_value, updated_at, account_uid, symbol
                updated_at, account_uid, symbol = maybe_cost_or_updated, rest[0], rest[1]
                row = self.db.positions[(account_uid, symbol)]
                row.update({"quantity": quantity, "cost_value": Decimal(str(cost_value_or_avg)), "updated_at": updated_at})
            return
        if compact.startswith("UPDATE qd_tw_sim_accounts SET cash"):
            cash, updated_at, uid = params
            self.db.accounts[uid]["cash"] = Decimal(str(cash))
            self.db.accounts[uid]["updated_at"] = updated_at
            return
        if compact.startswith("INSERT INTO qd_tw_sim_trades"):
            (
                trade_uid,
                sim_order_uid,
                account_uid,
                user_id,
                symbol,
                side,
                quantity,
                price,
                price_source,
                price_date,
                gross_amount,
                fee,
                tax,
                net_cash_effect,
                source_type,
                source_context_json,
                created_at,
            ) = params
            row = {
                "id": len(self.db.trades) + 1,
                "sim_trade_uid": trade_uid,
                "sim_order_uid": sim_order_uid,
                "account_uid": account_uid,
                "user_id": user_id,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": Decimal(str(price)),
                "price_source": price_source,
                "price_date": price_date,
                "gross_amount": Decimal(str(gross_amount)),
                "fee": Decimal(str(fee)),
                "tax": Decimal(str(tax)),
                "net_cash_effect": Decimal(str(net_cash_effect)),
                "source_type": source_type,
                "source_context_json": source_context_json,
                "simulation_only": True,
                "created_at": created_at,
            }
            self.db.trades.append(row)
            self.row = dict(row)
            return
        if compact.startswith("SELECT * FROM qd_tw_sim_trades"):
            account_uid = params[0]
            self.rows = [dict(row) for row in self.db.trades if row["account_uid"] == account_uid]
            return
        raise AssertionError(f"Unhandled SQL: {compact}")

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows

    def close(self):
        pass


class SimDb:
    def __init__(self):
        self.accounts = {}
        self.sim_orders = {}
        self.trades = []
        self.positions = {}
        self.prices = {}
        self.sql = []
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return SimCursor(self)

    def commit(self):
        self.commits += 1


def make_service(db, now="2026-06-05T12:00:00"):
    return TWStockSimAccountService(db_factory=lambda: db, now_fn=lambda: datetime.fromisoformat(now))


def seed_price(db, symbol="2330", close="100", trade_date="2026-06-04"):
    db.prices[symbol] = {"symbol": symbol, "trade_date": trade_date, "close": Decimal(str(close)), "source": "finmind"}


def create_account(service, user_id=7, cash=1_000_000):
    payload = service.create_account(user_id=user_id, initial_cash=cash)
    assert payload["ok"] is True
    return payload["account"]["account_uid"]


def assert_sim_flags(payload):
    assert payload["simulation_only"] is True
    assert payload["trading"]["simulation_only"] is True
    assert payload["trading"]["real_orders_enabled"] is False
    assert payload["trading"]["connects_to_broker"] is False


def test_create_account_and_list_returns_simulation_flags():
    db = SimDb()
    service = make_service(db)
    account_uid = create_account(service)

    listed = service.list_accounts(user_id=7)

    assert_sim_flags(listed)
    assert listed["count"] == 1
    assert listed["items"][0]["account_uid"] == account_uid
    assert listed["items"][0]["cash"] == 1_000_000.0
    assert listed["items"][0]["currency"] == "TWD"


def test_manual_buy_draft_and_confirm_updates_cash_and_position():
    db = SimDb()
    seed_price(db, close="100")
    service = make_service(db)
    account_uid = create_account(service)

    draft = service.draft(user_id=7, account_uid=account_uid, symbol="TW2330", side="buy", quantity=1000)
    filled = service.confirm(user_id=7, sim_order_uid=draft["sim_order"]["sim_order_uid"])
    positions = service.positions(account_uid=account_uid, user_id=7)

    assert_sim_flags(draft)
    assert draft["status"] == "draft"
    assert draft["sim_order"]["source_type"] == "manual"
    assert draft["sim_order"]["price_source"] == "latest_close"
    assert filled["status"] == "filled"
    assert filled["trade"]["simulation_only"] is True
    assert positions["items"][0]["symbol"] == "2330"
    assert positions["items"][0]["quantity"] == 1000
    assert pytest.approx(filled["account"]["cash"], rel=0, abs=0.01) == 899857.5


def test_buy_rejected_when_cash_is_insufficient():
    db = SimDb()
    seed_price(db, close="100")
    service = make_service(db)
    account_uid = create_account(service, cash=5000)

    rejected = service.draft(user_id=7, account_uid=account_uid, symbol="2330", side="buy", quantity=1000)

    assert rejected["status"] == "rejected"
    assert rejected["message"] == "insufficient_cash"
    assert rejected["sim_order"]["status"] == "rejected"
    assert db.positions == {}


def test_manual_sell_success_and_short_sale_rejected():
    db = SimDb()
    seed_price(db, close="100")
    service = make_service(db)
    account_uid = create_account(service)
    buy = service.draft(user_id=7, account_uid=account_uid, symbol="2330", side="buy", quantity=1000)
    service.confirm(user_id=7, sim_order_uid=buy["sim_order"]["sim_order_uid"])

    sell = service.draft(user_id=7, account_uid=account_uid, symbol="2330", side="sell", quantity=1000)
    filled = service.confirm(user_id=7, sim_order_uid=sell["sim_order"]["sim_order_uid"])
    oversell = service.draft(user_id=7, account_uid=account_uid, symbol="2330", side="sell", quantity=1000)

    assert sell["status"] == "draft"
    assert filled["status"] == "filled"
    assert pytest.approx(filled["account"]["cash"], rel=0, abs=0.01) == 999415.0
    assert service.positions(account_uid=account_uid, user_id=7)["items"] == []
    assert oversell["status"] == "rejected"
    assert oversell["message"] == "short_sale_blocked"


def test_missing_price_does_not_fill_and_stale_price_returns_warning():
    db = SimDb()
    service = make_service(db, now="2026-06-10T12:00:00")
    account_uid = create_account(service)

    missing = service.draft(user_id=7, account_uid=account_uid, symbol="2330", side="buy", quantity=1000)
    seed_price(db, close="88", trade_date="2026-06-01")
    stale = service.draft(user_id=7, account_uid=account_uid, symbol="2330", side="buy", quantity=1000)

    assert missing["status"] == "rejected"
    assert missing["message"] == "missing_price"
    assert "missing_latest_close" in missing["sim_order"]["warnings"]
    assert stale["status"] == "draft"
    assert "stale_latest_close" in stale["sim_order"]["warnings"]


def test_phase4_accepts_research_sources_and_rejects_unsafe_source_or_odd_lot():
    db = SimDb()
    seed_price(db)
    service = make_service(db)
    account_uid = create_account(service)

    linked = service.draft(
        user_id=7,
        account_uid=account_uid,
        symbol="2330",
        side="buy",
        quantity=1000,
        source_type="qlib_rank",
        source_context={"symbol": "2330", "asof": "2026-06-04", "run_id": "run-1", "qlib_rank": 1, "qlib_score": 0.1234, "trend_label": "uptrend"},
    )
    unsafe = service.draft(user_id=7, account_uid=account_uid, symbol="2330", side="buy", quantity=1000, source_type="agent")
    small_lot = service.draft(user_id=7, account_uid=account_uid, symbol="2330", side="buy", quantity=10)
    odd_lot = service.draft(user_id=7, account_uid=account_uid, symbol="2330", side="buy", quantity=7)

    assert linked["status"] == "draft"
    assert linked["sim_order"]["source_type"] == "qlib_rank"
    assert linked["sim_order"]["source_context"]["run_id"] == "run-1"
    assert linked["sim_order"]["source_context"]["symbol"] == "2330"
    assert unsafe["status"] == "unsupported_source_type"
    assert small_lot["status"] == "draft"
    assert odd_lot["status"] == "invalid_lot_size"


def test_service_source_does_not_reference_forbidden_execution_paths():
    root = Path(__file__).resolve().parents[1]
    text = (root / "app/services/tw_stock_sim_account.py").read_text(encoding="utf-8").lower()
    forbidden = [
        "quick_trade",
        "quick-trade",
        "app.services.broker",
        "place_order(",
        "submit_order(",
        "target_position",
        "target_weight",
        "tw_stock_qlib_option_c_ops",
        "refresh provider",
        "accepted latest",
        "openai",
    ]
    for item in forbidden:
        assert item not in text, f"simulation service references forbidden execution path: {item}"


def test_api_contract_uses_sim_service_and_current_user(client, monkeypatch):
    from app.routes import tw_stock as tw_stock_route

    calls = []

    class FakeService:
        def create_account(self, **kwargs):
            calls.append(("create", kwargs))
            return {"ok": True, "status": "created", "account": {"account_uid": "sim-1", "simulation_only": True}, "simulation_only": True, "trading": {"real_orders_enabled": False, "connects_to_broker": False, "simulation_only": True}}

        def list_accounts(self, **kwargs):
            calls.append(("list", kwargs))
            return {"ok": True, "status": "ok", "items": [], "count": 0, "simulation_only": True, "trading": {"real_orders_enabled": False, "connects_to_broker": False, "simulation_only": True}}

        def draft(self, **kwargs):
            calls.append(("draft", kwargs))
            return {"ok": True, "status": "draft", "sim_order": {"sim_order_uid": "draft-1", "source_type": kwargs.get("source_type"), "source_context": kwargs.get("source_context"), "simulation_only": True}, "simulation_only": True, "trading": {"real_orders_enabled": False, "connects_to_broker": False, "simulation_only": True}}

    monkeypatch.setattr(tw_stock_route, "tw_stock_sim_account_service", FakeService())

    # Bypass auth decorator by calling the wrapped business function inside a request context.
    with client.application.test_request_context("/api/tw-stock/sim/accounts", method="POST", json={"initial_cash": 123456}):
        tw_stock_route.g.user_id = 42
        resp, status = tw_stock_route.create_tw_stock_sim_account.__wrapped__()
        assert status == 200
        payload = resp.get_json()["data"]
        assert payload["trading"]["real_orders_enabled"] is False

    with client.application.test_request_context("/api/tw-stock/sim/orders/draft", method="POST", json={"account_uid": "sim-1", "symbol": "2330", "side": "buy", "quantity": 1000, "source_type": "cross_analysis", "source_context": {"cross_category": "focus_watch"}}):
        tw_stock_route.g.user_id = 42
        resp, status = tw_stock_route.draft_tw_stock_sim_order.__wrapped__()
        assert status == 200
        payload = resp.get_json()["data"]
        assert payload["status"] == "draft"
        assert payload["simulation_only"] is True

    assert calls[0][1]["user_id"] == 42
    assert calls[1][1]["source_type"] == "cross_analysis"
    assert calls[1][1]["source_context"]["cross_category"] == "focus_watch"
