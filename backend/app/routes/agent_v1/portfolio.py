"""Portfolio (read-only summary, class R).

Surfaces the calling tenant's manual positions in a stable shape suitable
for agent reasoning.  We only read from `qd_user_positions`-style tables that
already exist; we do NOT expose alerts/monitors here (those are a separate W
class addition for a future phase).
"""
from __future__ import annotations

from flask import request

from app.utils.agent_auth import SCOPE_R, agent_required, current_user_id
from app.utils.db import get_db_connection
from app.utils.logger import get_logger

from . import agent_v1_bp
from ._helpers import envelope, error

logger = get_logger(__name__)


@agent_v1_bp.route("/portfolio/positions", methods=["GET"])
@agent_required(SCOPE_R)
def positions():
    """Manual portfolio positions for the calling tenant."""
    try:
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                """
                SELECT id, market, symbol, quantity, avg_price, currency,
                       notes, created_at, updated_at
                FROM qd_user_positions
                WHERE user_id = %s
                ORDER BY id DESC
                """,
                (current_user_id(),),
            )
            rows = cur.fetchall() or []
            cur.close()
        return envelope(rows)
    except Exception as exc:
        # Tenants without the table get an empty list rather than a 500.
        msg = str(exc).lower()
        if "does not exist" in msg or "undefinedtable" in msg:
            return envelope([])
        logger.error(f"agent_v1/portfolio failed: {exc}", exc_info=True)
        return error(500, "portfolio query failed", details=str(exc), http=500)


def _build_paper_positions(rows):
    positions = {}
    warnings = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("status") or "").lower() != "filled":
            continue
        market = str(row.get("market") or "").strip()
        symbol = str(row.get("symbol") or "").strip()
        side = str(row.get("side") or "").strip().lower()
        try:
            qty = float(row.get("qty") or 0)
            fill_price = float(row.get("fill_price") or 0)
        except Exception:
            warnings.append(f"invalid_order_values:{row.get('order_uid') or symbol}")
            continue
        if not market or not symbol or qty <= 0 or fill_price <= 0:
            continue
        key = (market, symbol)
        pos = positions.setdefault(key, {
            "market": market,
            "symbol": symbol,
            "quantity": 0.0,
            "avg_price": 0.0,
            "cost_value": 0.0,
            "currency": "TWD" if market == "TWStock" else "",
            "source": "agent_paper_orders",
            "order_count": 0,
        })
        pos["order_count"] += 1
        if side == "buy":
            new_qty = pos["quantity"] + qty
            new_cost = pos["cost_value"] + qty * fill_price
            pos["quantity"] = new_qty
            pos["cost_value"] = new_cost
            pos["avg_price"] = new_cost / new_qty if new_qty > 0 else 0.0
        elif side == "sell":
            if qty > pos["quantity"]:
                warnings.append(f"paper_position_oversell:{market}:{symbol}")
                qty = pos["quantity"]
            pos["quantity"] -= qty
            pos["cost_value"] = pos["avg_price"] * pos["quantity"]
            if pos["quantity"] <= 0:
                pos["quantity"] = 0.0
                pos["cost_value"] = 0.0
                pos["avg_price"] = 0.0
        else:
            warnings.append(f"unknown_paper_order_side:{side}:{market}:{symbol}")
    out = [pos for pos in positions.values() if pos["quantity"] > 0]
    out.sort(key=lambda item: (item["market"], item["symbol"]))
    for pos in out:
        pos["quantity"] = float(pos["quantity"])
        pos["avg_price"] = float(pos["avg_price"])
        pos["cost_value"] = float(pos["cost_value"])
    return {"positions": out, "warnings": warnings}


def _build_paper_summary(rows, *, initial_cash: float = 0.0):
    positions = {}
    warnings = []
    gross_buy_value = 0.0
    gross_sell_value = 0.0
    realized_pnl = 0.0
    filled_order_count = 0
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("status") or "").lower() != "filled":
            continue
        market = str(row.get("market") or "").strip()
        symbol = str(row.get("symbol") or "").strip()
        side = str(row.get("side") or "").strip().lower()
        try:
            qty = float(row.get("qty") or 0)
            fill_price = float(row.get("fill_price") or 0)
        except Exception:
            warnings.append(f"invalid_order_values:{row.get('order_uid') or symbol}")
            continue
        if not market or not symbol or qty <= 0 or fill_price <= 0:
            continue
        filled_order_count += 1
        key = (market, symbol)
        pos = positions.setdefault(key, {
            "market": market,
            "symbol": symbol,
            "quantity": 0.0,
            "avg_price": 0.0,
            "cost_value": 0.0,
            "currency": "TWD" if market == "TWStock" else "",
            "source": "agent_paper_orders",
            "order_count": 0,
        })
        pos["order_count"] += 1
        if side == "buy":
            trade_value = qty * fill_price
            gross_buy_value += trade_value
            new_qty = pos["quantity"] + qty
            new_cost = pos["cost_value"] + trade_value
            pos["quantity"] = new_qty
            pos["cost_value"] = new_cost
            pos["avg_price"] = new_cost / new_qty if new_qty > 0 else 0.0
        elif side == "sell":
            sell_qty = qty
            if sell_qty > pos["quantity"]:
                warnings.append(f"paper_position_oversell:{market}:{symbol}")
                sell_qty = pos["quantity"]
            trade_value = sell_qty * fill_price
            gross_sell_value += trade_value
            realized_pnl += sell_qty * (fill_price - pos["avg_price"])
            pos["quantity"] -= sell_qty
            pos["cost_value"] = pos["avg_price"] * pos["quantity"]
            if pos["quantity"] <= 0:
                pos["quantity"] = 0.0
                pos["cost_value"] = 0.0
                pos["avg_price"] = 0.0
        else:
            warnings.append(f"unknown_paper_order_side:{side}:{market}:{symbol}")
    open_positions = [pos for pos in positions.values() if pos["quantity"] > 0]
    open_positions.sort(key=lambda item: (item["market"], item["symbol"]))
    open_cost_value = sum(float(pos["cost_value"] or 0.0) for pos in open_positions)
    cash = float(initial_cash or 0.0) - gross_buy_value + gross_sell_value
    equity_at_cost = cash + open_cost_value
    for pos in open_positions:
        pos["quantity"] = float(pos["quantity"])
        pos["avg_price"] = float(pos["avg_price"])
        pos["cost_value"] = float(pos["cost_value"])
    return {
        "currency": "TWD",
        "initial_cash": float(initial_cash or 0.0),
        "cash": float(cash),
        "gross_buy_value": float(gross_buy_value),
        "gross_sell_value": float(gross_sell_value),
        "realized_pnl": float(realized_pnl),
        "open_cost_value": float(open_cost_value),
        "equity_at_cost": float(equity_at_cost),
        "filled_order_count": int(filled_order_count),
        "position_count": len(open_positions),
        "positions": open_positions,
        "warnings": warnings,
        "source": "agent_paper_orders",
    }


@agent_v1_bp.route("/portfolio/paper-orders", methods=["GET"])
@agent_required(SCOPE_R)
def paper_orders():
    """List recent paper orders the agent has submitted (per tenant)."""
    try:
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                """
                SELECT order_uid, market, symbol, side, order_type, qty,
                       limit_price, fill_price, fill_value, status, note, created_at
                FROM qd_agent_paper_orders
                WHERE user_id = %s
                ORDER BY id DESC LIMIT 200
                """,
                (current_user_id(),),
            )
            rows = cur.fetchall() or []
            cur.close()
        return envelope(rows)
    except Exception as exc:
        logger.error(f"agent_v1/paper_orders failed: {exc}", exc_info=True)
        return error(500, "paper orders query failed", details=str(exc), http=500)

@agent_v1_bp.route("/portfolio/paper-positions", methods=["GET"])
@agent_required(SCOPE_R)
def paper_positions():
    """Derived paper positions from filled agent paper orders (read-only)."""
    try:
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                """
                SELECT order_uid, market, symbol, side, qty, fill_price, status, created_at
                FROM qd_agent_paper_orders
                WHERE user_id = %s
                ORDER BY id ASC
                """,
                (current_user_id(),),
            )
            rows = cur.fetchall() or []
            cur.close()
        return envelope(_build_paper_positions(rows))
    except Exception as exc:
        logger.error(f"agent_v1/paper_positions failed: {exc}", exc_info=True)
        return error(500, "paper positions query failed", details=str(exc), http=500)

@agent_v1_bp.route("/portfolio/paper-summary", methods=["GET"])
@agent_required(SCOPE_R)
def paper_summary():
    """Derived paper portfolio summary from filled agent paper orders."""
    try:
        initial_cash = float((request.args.get("initial_cash") or 0) or 0)
    except Exception:
        return error(400, "initial_cash must be numeric", http=400)
    try:
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                """
                SELECT order_uid, market, symbol, side, qty, fill_price, status, created_at
                FROM qd_agent_paper_orders
                WHERE user_id = %s
                ORDER BY id ASC
                """,
                (current_user_id(),),
            )
            rows = cur.fetchall() or []
            cur.close()
        return envelope(_build_paper_summary(rows, initial_cash=initial_cash))
    except Exception as exc:
        logger.error(f"agent_v1/paper_summary failed: {exc}", exc_info=True)
        return error(500, "paper summary query failed", details=str(exc), http=500)

