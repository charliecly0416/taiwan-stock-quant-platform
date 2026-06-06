"""Taiwan stock simulation account service.

This module is a research-only simulation ledger. It never connects to a
securities account, never calls external execution routes, and never submits real
market instructions. The only price input is the latest close already stored
in the local qd_tw_stock_daily_bars archive.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.utils.db import get_db_connection


MONEY = Decimal("0.01")
PRICE = Decimal("0.0001")
DEFAULT_INITIAL_CASH = Decimal("1000000.00")
DEFAULT_LOT_SIZE = 10
DEFAULT_FEE_RATE = Decimal("0.001425")
DEFAULT_SELL_TAX_RATE = Decimal("0.003")
ALLOWED_SOURCE_TYPES = {"manual", "qlib_rank", "cross_analysis", "agent_research"}


def sim_trading_flags() -> Dict[str, Any]:
    return {
        "real_orders_enabled": False,
        "connects_to_broker": False,
        "simulation_only": True,
    }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _to_decimal(value: Any, default: Decimal = Decimal("0")) -> Decimal:
    try:
        if value is None or value == "":
            return default
        return Decimal(str(value))
    except Exception:
        return default


def _money(value: Any) -> Decimal:
    return _to_decimal(value).quantize(MONEY, rounding=ROUND_HALF_UP)


def _price(value: Any) -> Decimal:
    return _to_decimal(value).quantize(PRICE, rounding=ROUND_HALF_UP)


def _float(value: Any) -> float:
    return float(_to_decimal(value))


def _normalize_symbol(symbol: Any) -> str:
    value = str(symbol or "").strip().upper()
    if not value:
        return ""
    if ":" in value:
        value = value.split(":")[-1]
    if value.startswith("TW"):
        value = value[2:]
    if "." in value:
        value = value.split(".")[0]
    return value if re.fullmatch(r"\d{4,6}", value) else ""


def _row(row: Any) -> Dict[str, Any]:
    return dict(row or {})


class TWStockSimAccountService:
    """Simulation-only Taiwan stock account ledger."""

    def __init__(
        self,
        *,
        db_factory: Callable[[], Any] = get_db_connection,
        now_fn: Callable[[], datetime] = _utc_now,
        stale_warning_days: int = 3,
        lot_size: int = DEFAULT_LOT_SIZE,
        fee_rate: Decimal = DEFAULT_FEE_RATE,
        sell_tax_rate: Decimal = DEFAULT_SELL_TAX_RATE,
    ) -> None:
        self.db_factory = db_factory
        self.now_fn = now_fn
        self.stale_warning_days = int(stale_warning_days)
        self.lot_size = int(lot_size)
        self.fee_rate = Decimal(str(fee_rate))
        self.sell_tax_rate = Decimal(str(sell_tax_rate))
        self._schema_ready = False

    def ensure_schema(self) -> None:
        if self._schema_ready:
            return
        with self.db_factory() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS qd_tw_sim_accounts (
                    id BIGSERIAL PRIMARY KEY,
                    account_uid VARCHAR(64) NOT NULL UNIQUE,
                    user_id INTEGER NOT NULL DEFAULT 0,
                    name VARCHAR(120) NOT NULL,
                    currency VARCHAR(8) NOT NULL DEFAULT 'TWD',
                    initial_cash DECIMAL(24,2) NOT NULL,
                    cash DECIMAL(24,2) NOT NULL,
                    simulation_only BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS qd_tw_sim_positions (
                    id BIGSERIAL PRIMARY KEY,
                    account_uid VARCHAR(64) NOT NULL,
                    symbol VARCHAR(20) NOT NULL,
                    quantity BIGINT NOT NULL DEFAULT 0,
                    avg_cost DECIMAL(20,6) NOT NULL DEFAULT 0,
                    cost_value DECIMAL(24,2) NOT NULL DEFAULT 0,
                    simulation_only BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(account_uid, symbol)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS qd_tw_sim_orders (
                    id BIGSERIAL PRIMARY KEY,
                    sim_order_uid VARCHAR(64) NOT NULL UNIQUE,
                    account_uid VARCHAR(64) NOT NULL,
                    user_id INTEGER NOT NULL DEFAULT 0,
                    symbol VARCHAR(20) NOT NULL,
                    side VARCHAR(8) NOT NULL,
                    quantity BIGINT NOT NULL,
                    status VARCHAR(24) NOT NULL,
                    source_type VARCHAR(24) NOT NULL DEFAULT 'manual',
                    source_context_json TEXT DEFAULT '',
                    requested_price DECIMAL(20,6),
                    reference_price DECIMAL(20,6),
                    price_source VARCHAR(64) DEFAULT '',
                    price_date DATE,
                    gross_amount DECIMAL(24,2) DEFAULT 0,
                    fee DECIMAL(24,2) DEFAULT 0,
                    tax DECIMAL(24,2) DEFAULT 0,
                    net_cash_effect DECIMAL(24,2) DEFAULT 0,
                    message TEXT DEFAULT '',
                    warnings TEXT DEFAULT '',
                    simulation_only BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    filled_at TIMESTAMP
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS qd_tw_sim_trades (
                    id BIGSERIAL PRIMARY KEY,
                    sim_trade_uid VARCHAR(64) NOT NULL UNIQUE,
                    sim_order_uid VARCHAR(64) NOT NULL,
                    account_uid VARCHAR(64) NOT NULL,
                    user_id INTEGER NOT NULL DEFAULT 0,
                    symbol VARCHAR(20) NOT NULL,
                    side VARCHAR(8) NOT NULL,
                    quantity BIGINT NOT NULL,
                    price DECIMAL(20,6) NOT NULL,
                    price_source VARCHAR(64) DEFAULT '',
                    price_date DATE,
                    gross_amount DECIMAL(24,2) NOT NULL,
                    fee DECIMAL(24,2) NOT NULL DEFAULT 0,
                    tax DECIMAL(24,2) NOT NULL DEFAULT 0,
                    net_cash_effect DECIMAL(24,2) NOT NULL DEFAULT 0,
                    source_type VARCHAR(24) NOT NULL DEFAULT 'manual',
                    source_context_json TEXT DEFAULT '',
                    simulation_only BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW()
                )
                """
            )
            cur.execute("ALTER TABLE qd_tw_sim_orders ADD COLUMN IF NOT EXISTS source_context_json TEXT DEFAULT ''")
            cur.execute("ALTER TABLE qd_tw_sim_trades ADD COLUMN IF NOT EXISTS source_context_json TEXT DEFAULT ''")
            cur.close()
            conn.commit()
        self._schema_ready = True

    def create_account(self, *, user_id: int = 0, name: str = "台股研究模拟账户", initial_cash: Any = DEFAULT_INITIAL_CASH) -> Dict[str, Any]:
        self.ensure_schema()
        cash = _money(initial_cash)
        if cash <= 0:
            return self._reject("invalid_initial_cash", "initial_cash must be positive")
        account_uid = f"tw_sim_{uuid.uuid4().hex}"
        now = self.now_fn()
        with self.db_factory() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO qd_tw_sim_accounts
                  (account_uid, user_id, name, currency, initial_cash, cash, simulation_only, created_at, updated_at)
                VALUES (?, ?, ?, 'TWD', ?, ?, TRUE, ?, ?)
                RETURNING *
                """,
                (account_uid, int(user_id or 0), str(name or "台股研究模拟账户")[:120], cash, cash, now, now),
            )
            row = _row(cur.fetchone())
            cur.close()
            conn.commit()
        return {"ok": True, "status": "created", "account": self._account_payload(row), "simulation_only": True, "trading": sim_trading_flags()}

    def list_accounts(self, *, user_id: int = 0) -> Dict[str, Any]:
        self.ensure_schema()
        with self.db_factory() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM qd_tw_sim_accounts WHERE user_id = ? ORDER BY created_at ASC", (int(user_id or 0),))
            rows = [_row(item) for item in (cur.fetchall() or [])]
            cur.close()
        items = [self._account_with_nav(row) for row in rows]
        return {"ok": True, "status": "ok", "items": items, "count": len(items), "simulation_only": True, "trading": sim_trading_flags()}

    def get_account(self, *, account_uid: str, user_id: int = 0) -> Dict[str, Any]:
        self.ensure_schema()
        account = self._get_account_row(account_uid, user_id=user_id)
        if not account:
            return self._reject("not_found", "simulation account not found")
        return {"ok": True, "status": "ok", "account": self._account_with_nav(account), "simulation_only": True, "trading": sim_trading_flags()}

    def positions(self, *, account_uid: str, user_id: int = 0) -> Dict[str, Any]:
        self.ensure_schema()
        account = self._get_account_row(account_uid, user_id=user_id)
        if not account:
            return self._reject("not_found", "simulation account not found")
        items = self._position_payloads(account_uid)
        return {"ok": True, "status": "ok", "items": items, "count": len(items), "simulation_only": True, "trading": sim_trading_flags()}

    def trades(self, *, account_uid: str, user_id: int = 0, limit: int = 100) -> Dict[str, Any]:
        self.ensure_schema()
        account = self._get_account_row(account_uid, user_id=user_id)
        if not account:
            return self._reject("not_found", "simulation account not found")
        safe_limit = max(1, min(int(limit or 100), 500))
        with self.db_factory() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM qd_tw_sim_trades WHERE account_uid = ? ORDER BY created_at DESC LIMIT ?",
                (account_uid, safe_limit),
            )
            rows = [_row(item) for item in (cur.fetchall() or [])]
            cur.close()
        return {"ok": True, "status": "ok", "items": [self._trade_payload(row) for row in rows], "count": len(rows), "simulation_only": True, "trading": sim_trading_flags()}

    def draft(self, *, user_id: int = 0, account_uid: str, symbol: Any, side: Any, quantity: Any, source_type: str = "manual", source_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.ensure_schema()
        account = self._get_account_row(account_uid, user_id=user_id)
        if not account:
            return self._reject("not_found", "simulation account not found")
        clean_symbol = _normalize_symbol(symbol)
        clean_side = str(side or "").strip().lower()
        source = str(source_type or "manual").strip().lower()
        qty = self._parse_quantity(quantity)
        clean_context = self._normalize_source_context(source_context, clean_symbol)
        validation = self._validate_request(clean_symbol, clean_side, qty, source)
        if validation:
            return validation
        price_info = self._latest_price(clean_symbol)
        if not price_info:
            return self._store_rejected(account, clean_symbol, clean_side, qty, source, "missing_price", ["missing_latest_close"], clean_context)
        calc = self._cash_calc(clean_side, qty, price_info["price"])
        warnings = self._price_warnings(price_info)
        if clean_side == "buy" and _to_decimal(account.get("cash")) < calc["cash_required"]:
            return self._store_rejected(account, clean_symbol, clean_side, qty, source, "insufficient_cash", warnings, clean_context)
        if clean_side == "sell" and self._position_quantity(account_uid, clean_symbol) < qty:
            return self._store_rejected(account, clean_symbol, clean_side, qty, source, "short_sale_blocked", warnings, clean_context)
        draft_row = self._insert_sim_order(account, clean_symbol, clean_side, qty, source, "draft", price_info, calc, "draft_ready", warnings, clean_context)
        return {"ok": True, "status": "draft", "sim_order": self._order_payload(draft_row), "simulation_only": True, "trading": sim_trading_flags()}

    def confirm(self, *, user_id: int = 0, sim_order_uid: str) -> Dict[str, Any]:
        self.ensure_schema()
        sim_order = self._get_sim_order_row(sim_order_uid, user_id=user_id)
        if not sim_order:
            return self._reject("not_found", "simulation order draft not found")
        if sim_order.get("status") != "draft":
            return self._reject(str(sim_order.get("status") or "not_draft"), "only draft simulation orders can be confirmed", sim_order=sim_order)
        account = self._get_account_row(str(sim_order.get("account_uid") or ""), user_id=user_id)
        if not account:
            return self._reject("not_found", "simulation account not found")
        side = str(sim_order.get("side") or "")
        symbol = str(sim_order.get("symbol") or "")
        qty = int(sim_order.get("quantity") or 0)
        price = _price(sim_order.get("reference_price"))
        calc = self._cash_calc(side, qty, price)
        if side == "buy" and _to_decimal(account.get("cash")) < calc["cash_required"]:
            return self._mark_rejected(sim_order, "insufficient_cash_at_confirm")
        if side == "sell" and self._position_quantity(str(account.get("account_uid")), symbol) < qty:
            return self._mark_rejected(sim_order, "short_sale_blocked_at_confirm")
        now = self.now_fn()
        with self.db_factory() as conn:
            cur = conn.cursor()
            if side == "buy":
                new_cash = _money(_to_decimal(account.get("cash")) - calc["cash_required"])
                self._apply_buy(cur, account, symbol, qty, price, calc)
            else:
                new_cash = _money(_to_decimal(account.get("cash")) + calc["cash_credit"])
                self._apply_sell(cur, account, symbol, qty, price, calc)
            cur.execute("UPDATE qd_tw_sim_accounts SET cash = ?, updated_at = ? WHERE account_uid = ?", (new_cash, now, account.get("account_uid")))
            cur.execute(
                """
                UPDATE qd_tw_sim_orders
                SET status = 'filled', updated_at = ?, filled_at = ?
                WHERE sim_order_uid = ?
                RETURNING *
                """,
                (now, now, sim_order_uid),
            )
            filled = _row(cur.fetchone())
            trade_uid = f"tw_sim_trade_{uuid.uuid4().hex}"
            cur.execute(
                """
                INSERT INTO qd_tw_sim_trades
                  (sim_trade_uid, sim_order_uid, account_uid, user_id, symbol, side, quantity, price,
                   price_source, price_date, gross_amount, fee, tax, net_cash_effect, source_type,
                   source_context_json, simulation_only, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE, ?)
                RETURNING *
                """,
                (
                    trade_uid,
                    sim_order_uid,
                    account.get("account_uid"),
                    int(user_id or 0),
                    symbol,
                    side,
                    qty,
                    price,
                    filled.get("price_source") or "latest_close",
                    filled.get("price_date"),
                    calc["gross_amount"],
                    calc["fee"],
                    calc["tax"],
                    calc["net_cash_effect"],
                    filled.get("source_type") or "manual",
                    filled.get("source_context_json") or "",
                    now,
                ),
            )
            trade = _row(cur.fetchone())
            cur.close()
            conn.commit()
        return {"ok": True, "status": "filled", "sim_order": self._order_payload(filled), "trade": self._trade_payload(trade), "account": self.get_account(account_uid=str(account.get("account_uid")), user_id=user_id).get("account"), "simulation_only": True, "trading": sim_trading_flags()}

    def cancel(self, *, user_id: int = 0, sim_order_uid: str) -> Dict[str, Any]:
        self.ensure_schema()
        sim_order = self._get_sim_order_row(sim_order_uid, user_id=user_id)
        if not sim_order:
            return self._reject("not_found", "simulation order draft not found")
        if sim_order.get("status") != "draft":
            return self._reject(str(sim_order.get("status") or "not_draft"), "only draft simulation orders can be cancelled", sim_order=sim_order)
        now = self.now_fn()
        with self.db_factory() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE qd_tw_sim_orders SET status = 'cancelled', updated_at = ? WHERE sim_order_uid = ? RETURNING *", (now, sim_order_uid))
            row = _row(cur.fetchone())
            cur.close()
            conn.commit()
        return {"ok": True, "status": "cancelled", "sim_order": self._order_payload(row), "simulation_only": True, "trading": sim_trading_flags()}

    def _reject(self, status: str, message: str, **extra: Any) -> Dict[str, Any]:
        payload = {"ok": False, "status": status, "message": message, "simulation_only": True, "trading": sim_trading_flags()}
        payload.update(extra)
        return payload

    def _parse_quantity(self, quantity: Any) -> int:
        try:
            return int(quantity)
        except Exception:
            return 0

    def _validate_request(self, symbol: str, side: str, qty: int, source: str) -> Optional[Dict[str, Any]]:
        if not symbol:
            return self._reject("invalid_symbol", "invalid TWStock symbol")
        if side not in {"buy", "sell"}:
            return self._reject("invalid_side", "side must be buy or sell for simulation")
        if qty <= 0:
            return self._reject("invalid_quantity", "quantity must be positive")
        if qty % self.lot_size != 0:
            return self._reject("invalid_lot_size", f"quantity must be a multiple of {self.lot_size}")
        if source not in ALLOWED_SOURCE_TYPES:
            return self._reject("unsupported_source_type", "simulation source_type must be one of manual, qlib_rank, cross_analysis, agent_research")
        return None

    def _latest_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        with self.db_factory() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT symbol, trade_date::text AS trade_date, close, source
                FROM qd_tw_stock_daily_bars
                WHERE symbol = ?
                  AND close > 0
                  AND (quality_flags IS NULL OR quality_flags = '')
                ORDER BY trade_date DESC
                LIMIT 1
                """,
                (symbol,),
            )
            row = _row(cur.fetchone())
            cur.close()
        if not row:
            return None
        return {"symbol": symbol, "price": _price(row.get("close")), "price_date": str(row.get("trade_date") or ""), "price_source": "latest_close", "raw_source": row.get("source") or "qd_tw_stock_daily_bars"}

    def _price_warnings(self, price_info: Dict[str, Any]) -> List[str]:
        warnings: List[str] = []
        raw = price_info.get("price_date") or ""
        try:
            lag = (self.now_fn().date() - date.fromisoformat(str(raw))).days
            if lag > self.stale_warning_days:
                warnings.append("stale_latest_close")
        except Exception:
            warnings.append("unknown_price_date")
        return warnings

    def _normalize_source_context(self, context: Optional[Dict[str, Any]], symbol: str) -> Dict[str, Any]:
        if not isinstance(context, dict):
            return {}
        allowed = {
            "symbol",
            "asof",
            "run_id",
            "qlib_rank",
            "qlib_score",
            "trend_label",
            "trend_score",
            "cross_category",
            "cross_alignment",
            "technical_status",
            "risk_hint",
            "combo_label",
            "combo_type",
            "combo_reason",
            "backtest_strategy",
            "backtest_return",
            "backtest_trades",
            "bucket",
            "source_label",
            "user_edited",
        }
        out = {key: context.get(key) for key in allowed if key in context and context.get(key) is not None}
        if symbol:
            out["symbol"] = symbol
        if "source_label" in out:
            out["source_label"] = str(out["source_label"])[:120]
        return out

    def _source_context_json(self, context: Optional[Dict[str, Any]]) -> str:
        if not context:
            return ""
        try:
            return json.dumps(context, ensure_ascii=False, sort_keys=True)
        except Exception:
            return ""

    def _source_context_payload(self, value: Any) -> Dict[str, Any]:
        if isinstance(value, dict):
            return value
        if not value:
            return {}
        try:
            parsed = json.loads(str(value))
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    def _cash_calc(self, side: str, qty: int, price: Decimal) -> Dict[str, Decimal]:
        gross = _money(Decimal(qty) * price)
        fee = _money(gross * self.fee_rate)
        tax = _money(gross * self.sell_tax_rate) if side == "sell" else Decimal("0.00")
        if side == "buy":
            net = _money(gross + fee)
            return {"gross_amount": gross, "fee": fee, "tax": tax, "net_cash_effect": -net, "cash_required": net, "cash_credit": Decimal("0.00")}
        credit = _money(gross - fee - tax)
        return {"gross_amount": gross, "fee": fee, "tax": tax, "net_cash_effect": credit, "cash_required": Decimal("0.00"), "cash_credit": credit}

    def _insert_sim_order(self, account: Dict[str, Any], symbol: str, side: str, qty: int, source: str, status: str, price_info: Dict[str, Any], calc: Dict[str, Decimal], message: str, warnings: List[str], source_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        uid = f"tw_sim_order_{uuid.uuid4().hex}"
        now = self.now_fn()
        with self.db_factory() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO qd_tw_sim_orders
                  (sim_order_uid, account_uid, user_id, symbol, side, quantity, status, source_type,
                   source_context_json, reference_price, price_source, price_date, gross_amount, fee, tax, net_cash_effect,
                   message, warnings, simulation_only, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE, ?, ?)
                RETURNING *
                """,
                (
                    uid,
                    account.get("account_uid"),
                    int(account.get("user_id") or 0),
                    symbol,
                    side,
                    qty,
                    status,
                    source,
                    self._source_context_json(source_context),
                    price_info.get("price"),
                    price_info.get("price_source") or "latest_close",
                    price_info.get("price_date") or None,
                    calc.get("gross_amount"),
                    calc.get("fee"),
                    calc.get("tax"),
                    calc.get("net_cash_effect"),
                    message,
                    ",".join(warnings),
                    now,
                    now,
                ),
            )
            row = _row(cur.fetchone())
            cur.close()
            conn.commit()
        return row

    def _store_rejected(self, account: Dict[str, Any], symbol: str, side: str, qty: int, source: str, reason: str, warnings: List[str], source_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        price_info = self._latest_price(symbol) or {"price": Decimal("0"), "price_source": "latest_close", "price_date": None}
        calc = self._cash_calc(side if side in {"buy", "sell"} else "buy", max(qty, 0), _price(price_info.get("price")))
        row = self._insert_sim_order(account, symbol, side, qty, source, "rejected", price_info, calc, reason, warnings, source_context)
        return {"ok": False, "status": "rejected", "message": reason, "sim_order": self._order_payload(row), "simulation_only": True, "trading": sim_trading_flags()}

    def _mark_rejected(self, sim_order: Dict[str, Any], reason: str) -> Dict[str, Any]:
        now = self.now_fn()
        with self.db_factory() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE qd_tw_sim_orders SET status = 'rejected', message = ?, updated_at = ? WHERE sim_order_uid = ? RETURNING *", (reason, now, sim_order.get("sim_order_uid")))
            row = _row(cur.fetchone())
            cur.close()
            conn.commit()
        return {"ok": False, "status": "rejected", "message": reason, "sim_order": self._order_payload(row), "simulation_only": True, "trading": sim_trading_flags()}

    def _get_account_row(self, account_uid: str, *, user_id: int = 0) -> Optional[Dict[str, Any]]:
        with self.db_factory() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM qd_tw_sim_accounts WHERE account_uid = ? AND user_id = ?", (account_uid, int(user_id or 0)))
            row = _row(cur.fetchone())
            cur.close()
        return row or None

    def _get_sim_order_row(self, sim_order_uid: str, *, user_id: int = 0) -> Optional[Dict[str, Any]]:
        with self.db_factory() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM qd_tw_sim_orders WHERE sim_order_uid = ? AND user_id = ?", (sim_order_uid, int(user_id or 0)))
            row = _row(cur.fetchone())
            cur.close()
        return row or None

    def _position_quantity(self, account_uid: str, symbol: str) -> int:
        with self.db_factory() as conn:
            cur = conn.cursor()
            cur.execute("SELECT quantity FROM qd_tw_sim_positions WHERE account_uid = ? AND symbol = ?", (account_uid, symbol))
            row = _row(cur.fetchone())
            cur.close()
        return int(row.get("quantity") or 0) if row else 0

    def _apply_buy(self, cur: Any, account: Dict[str, Any], symbol: str, qty: int, price: Decimal, calc: Dict[str, Decimal]) -> None:
        account_uid = str(account.get("account_uid"))
        now = self.now_fn()
        cur.execute("SELECT * FROM qd_tw_sim_positions WHERE account_uid = ? AND symbol = ?", (account_uid, symbol))
        pos = _row(cur.fetchone())
        if pos:
            old_qty = int(pos.get("quantity") or 0)
            old_cost = _money(pos.get("cost_value"))
            add_cost = _money(calc["gross_amount"] + calc["fee"])
            new_qty = old_qty + qty
            new_cost = _money(old_cost + add_cost)
            avg_cost = _price(new_cost / Decimal(new_qty)) if new_qty else Decimal("0")
            cur.execute("UPDATE qd_tw_sim_positions SET quantity = ?, avg_cost = ?, cost_value = ?, updated_at = ? WHERE account_uid = ? AND symbol = ?", (new_qty, avg_cost, new_cost, now, account_uid, symbol))
        else:
            cost = _money(calc["gross_amount"] + calc["fee"])
            avg_cost = _price(cost / Decimal(qty))
            cur.execute("INSERT INTO qd_tw_sim_positions (account_uid, symbol, quantity, avg_cost, cost_value, simulation_only, created_at, updated_at) VALUES (?, ?, ?, ?, ?, TRUE, ?, ?)", (account_uid, symbol, qty, avg_cost, cost, now, now))

    def _apply_sell(self, cur: Any, account: Dict[str, Any], symbol: str, qty: int, price: Decimal, calc: Dict[str, Decimal]) -> None:
        account_uid = str(account.get("account_uid"))
        now = self.now_fn()
        cur.execute("SELECT * FROM qd_tw_sim_positions WHERE account_uid = ? AND symbol = ?", (account_uid, symbol))
        pos = _row(cur.fetchone())
        old_qty = int(pos.get("quantity") or 0)
        avg_cost = _price(pos.get("avg_cost"))
        new_qty = old_qty - qty
        new_cost = _money(avg_cost * Decimal(new_qty)) if new_qty > 0 else Decimal("0.00")
        cur.execute("UPDATE qd_tw_sim_positions SET quantity = ?, cost_value = ?, updated_at = ? WHERE account_uid = ? AND symbol = ?", (new_qty, new_cost, now, account_uid, symbol))

    def _position_payloads(self, account_uid: str) -> List[Dict[str, Any]]:
        with self.db_factory() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM qd_tw_sim_positions WHERE account_uid = ? AND quantity > 0 ORDER BY symbol ASC", (account_uid,))
            rows = [_row(item) for item in (cur.fetchall() or [])]
            cur.close()
        out = []
        for row in rows:
            price_info = self._latest_price(str(row.get("symbol") or ""))
            latest_price = price_info.get("price") if price_info else Decimal("0")
            market_value = _money(Decimal(int(row.get("quantity") or 0)) * _price(latest_price))
            cost_value = _money(row.get("cost_value"))
            out.append({
                "symbol": row.get("symbol"),
                "quantity": int(row.get("quantity") or 0),
                "avg_cost": _float(row.get("avg_cost")),
                "cost_value": _float(cost_value),
                "latest_close": _float(latest_price),
                "latest_date": price_info.get("price_date") if price_info else None,
                "market_value": _float(market_value),
                "unrealized_pnl": _float(_money(market_value - cost_value)),
                "simulation_only": True,
            })
        return out

    def _account_with_nav(self, row: Dict[str, Any]) -> Dict[str, Any]:
        account = self._account_payload(row)
        positions = self._position_payloads(str(row.get("account_uid") or ""))
        market_value = _money(sum((_to_decimal(item.get("market_value")) for item in positions), Decimal("0")))
        cash = _money(row.get("cash"))
        total = _money(cash + market_value)
        initial = _money(row.get("initial_cash"))
        account.update({
            "market_value": _float(market_value),
            "total_equity": _float(total),
            "total_pnl": _float(_money(total - initial)),
            "total_return": _float((total / initial - Decimal("1")) if initial > 0 else Decimal("0")),
            "position_count": len(positions),
        })
        return account

    def _account_payload(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "account_uid": row.get("account_uid"),
            "user_id": int(row.get("user_id") or 0),
            "name": row.get("name"),
            "currency": row.get("currency") or "TWD",
            "initial_cash": _float(row.get("initial_cash")),
            "cash": _float(row.get("cash")),
            "simulation_only": True,
            "created_at": str(row.get("created_at") or ""),
            "updated_at": str(row.get("updated_at") or ""),
        }

    def _order_payload(self, row: Dict[str, Any]) -> Dict[str, Any]:
        warnings = [item for item in str(row.get("warnings") or "").split(",") if item]
        return {
            "sim_order_uid": row.get("sim_order_uid"),
            "account_uid": row.get("account_uid"),
            "symbol": row.get("symbol"),
            "side": row.get("side"),
            "quantity": int(row.get("quantity") or 0),
            "status": row.get("status"),
            "source_type": row.get("source_type") or "manual",
            "reference_price": _float(row.get("reference_price")),
            "price_source": row.get("price_source") or "latest_close",
            "price_date": str(row.get("price_date") or "") or None,
            "gross_amount": _float(row.get("gross_amount")),
            "fee": _float(row.get("fee")),
            "tax": _float(row.get("tax")),
            "net_cash_effect": _float(row.get("net_cash_effect")),
            "message": row.get("message") or "",
            "warnings": warnings,
            "source_context": self._source_context_payload(row.get("source_context_json")),
            "simulation_only": True,
        }

    def _trade_payload(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "sim_trade_uid": row.get("sim_trade_uid"),
            "sim_order_uid": row.get("sim_order_uid"),
            "account_uid": row.get("account_uid"),
            "symbol": row.get("symbol"),
            "side": row.get("side"),
            "quantity": int(row.get("quantity") or 0),
            "price": _float(row.get("price")),
            "price_source": row.get("price_source") or "latest_close",
            "price_date": str(row.get("price_date") or "") or None,
            "gross_amount": _float(row.get("gross_amount")),
            "fee": _float(row.get("fee")),
            "tax": _float(row.get("tax")),
            "net_cash_effect": _float(row.get("net_cash_effect")),
            "source_type": row.get("source_type") or "manual",
            "source_context": self._source_context_payload(row.get("source_context_json")),
            "simulation_only": True,
            "created_at": str(row.get("created_at") or ""),
        }
