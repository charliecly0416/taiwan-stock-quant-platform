"""Trading (class T) — paper-only by default, hard-gated for live execution.

Live execution from agents requires *all* of the following:
  1. Token has scope `T`.
  2. Token has `paper_only=false` (operator must flip explicitly).
  3. Server-side env `AGENT_LIVE_TRADING_ENABLED=true` (deployment kill switch).

Until live is unlocked, this endpoint records orders to `qd_agent_paper_orders`
using the latest market price as the simulated fill — so AI workflows can
exercise the round trip without ever touching exchange credentials.
"""
from __future__ import annotations

import os
import uuid
from typing import Any

from app.data_sources.tw_stock import TWStockDataSource
from app.services.kline import KlineService
from app.utils.agent_auth import (
    SCOPE_T, agent_required, current_token, current_user_id,
    instrument_allowed, market_allowed, paper_only, with_idempotency,
)
from app.utils.db import get_db_connection
from app.utils.logger import get_logger
from flask import request

from . import agent_v1_bp
from ._helpers import envelope, error, get_json_or_400

logger = get_logger(__name__)
_kline = KlineService()


def _live_trading_kill_switch() -> bool:
    return os.getenv("AGENT_LIVE_TRADING_ENABLED", "false").lower() in ("1", "true", "yes")




def _twstock_symbol(symbol: str) -> str:
    raw = str(symbol or "").strip()
    if raw.upper().startswith("TWSTOCK:"):
        raw = raw.split(":", 1)[1]
    return TWStockDataSource.normalize_symbol(raw).symbol or raw.strip().upper()


def _twstock_last_price(symbol: str) -> float | None:
    try:
        ds = TWStockDataSource()
        rows = ds.get_kline(symbol=symbol, timeframe="1D", limit=10) or []
        for row in reversed(rows):
            if isinstance(row, dict):
                value = row.get("close") or row.get("Close") or row.get("c")
                if value is not None and float(value) > 0:
                    return float(value)
    except Exception as exc:
        logger.warning(f"agent_v1 quick_trade TWStock last_price failed: {exc}")
    return None


def _twstock_request_current_qty(body: dict) -> float | None:
    for key in ("current_qty", "currentQty", "current_position", "currentPosition"):
        if key in body and body.get(key) is not None:
            try:
                return float(body.get(key) or 0)
            except Exception:
                return 0.0
    return None


def _twstock_position_qty(symbol: str) -> float:
    try:
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                """
                SELECT COALESCE(SUM(quantity), 0) AS quantity
                FROM qd_user_positions
                WHERE user_id = %s AND market = %s AND symbol = %s
                """,
                (current_user_id(), "TWStock", symbol),
            )
            row = cur.fetchone()
            cur.close()
        if isinstance(row, dict):
            return float(row.get("quantity") or 0)
        if isinstance(row, (tuple, list)) and row:
            return float(row[0] or 0)
    except Exception as exc:
        logger.warning(f"agent_v1 quick_trade TWStock position lookup failed: {exc}")
    return 0.0


def _validate_twstock_order(body: dict, *, symbol: str, side: str, qty: float, order_type: str) -> str:
    lot_size = int(body.get("lot_size") or body.get("lotSize") or 1000)
    if lot_size <= 0:
        return "TWStock lot_size must be positive"
    if int(qty) != qty or int(qty) % lot_size != 0:
        return f"TWStock qty must be an integer multiple of {lot_size}"
    if side == "sell":
        current_qty = _twstock_request_current_qty(body) or 0
        if qty > current_qty:
            return "TWStock paper orders are long-only; sell qty cannot exceed current_qty"
    if order_type != "limit":
        return "TWStock paper orders require order_type='limit' for price protection"
    limit_price = body.get("limit_price") or body.get("limitPrice")
    try:
        if float(limit_price) <= 0:
            raise ValueError
    except Exception:
        return "TWStock limit_price must be a positive number"
    return ""

def _last_price(market: str, symbol: str) -> float | None:
    if (market or "").strip() == "TWStock":
        return _twstock_last_price(symbol)
    try:
        rows = _kline.get_kline(market=market, symbol=symbol, timeframe="1m", limit=1) or []
        if not rows:
            return None
        last = rows[-1]
        if isinstance(last, dict):
            for k in ("close", "c", "Close"):
                v = last.get(k)
                if v is not None:
                    return float(v)
        return None
    except Exception as exc:
        logger.warning(f"agent_v1 quick_trade last_price failed: {exc}")
        return None


def _paper_fill_decision(*, market: str, side: str, order_type: str, limit_price: Any, last_price: float | None) -> tuple[float | None, str, str]:
    if last_price is None:
        return None, "rejected", "no last price available; recorded without fill"
    if (market or "").strip() == "TWStock" and (order_type or "").strip().lower() == "limit":
        try:
            limit = float(limit_price)
        except Exception:
            return None, "rejected", "invalid limit price; recorded without fill"
        px = float(last_price)
        if side == "buy" and px > limit:
            return None, "rejected", f"paper limit not marketable: last_price {px} > buy limit {limit}"
        if side == "sell" and px < limit:
            return None, "rejected", f"paper limit not marketable: last_price {px} < sell limit {limit}"
    return float(last_price), "filled", ""


def _record_paper_order(*, body: dict, fill_price: float | None, status: str, note: str = "") -> dict:
    order_uid = uuid.uuid4().hex
    market = (body.get("market") or "").strip()
    symbol = (body.get("symbol") or "").strip()
    side = (body.get("side") or "").strip().lower()
    order_type = (body.get("order_type") or body.get("orderType") or "market").strip().lower()
    qty = float(body.get("qty") or body.get("quantity") or 0)
    limit_price = body.get("limit_price") or body.get("limitPrice")
    if limit_price is not None:
        limit_price = float(limit_price)

    fill_value = (fill_price * qty) if (fill_price is not None and qty) else None

    with get_db_connection() as db:
        cur = db.cursor()
        cur.execute(
            """
            INSERT INTO qd_agent_paper_orders
              (order_uid, user_id, agent_token_id, market, symbol, side, order_type,
               qty, limit_price, fill_price, fill_value, status, note)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                order_uid, current_user_id(), int(current_token().get("id") or 0),
                market, symbol, side, order_type,
                qty, limit_price, fill_price, fill_value, status, note,
            ),
        )
        db.commit()
        cur.close()

    return {
        "order_uid": order_uid,
        "market": market,
        "symbol": symbol,
        "side": side,
        "order_type": order_type,
        "qty": qty,
        "limit_price": limit_price,
        "fill_price": fill_price,
        "fill_value": fill_value,
        "status": status,
        "paper": True,
        "note": note,
    }


@agent_v1_bp.route("/quick-trade/orders", methods=["POST"])
@agent_required(SCOPE_T)
def place_order():
    """Place an order. Paper-only unless explicitly unlocked (see module doc)."""
    body, err = get_json_or_400()
    if err:
        return err

    market = (body.get("market") or "").strip()
    symbol = (body.get("symbol") or "").strip()
    side = (body.get("side") or "").strip().lower()
    order_type = (body.get("order_type") or body.get("orderType") or "market").strip().lower()
    qty = body.get("qty") or body.get("quantity")

    if not market or not symbol:
        return error(400, "market and symbol are required")
    if side not in ("buy", "sell"):
        return error(400, "side must be 'buy' or 'sell'")
    try:
        qty_f = float(qty)
        if qty_f <= 0:
            raise ValueError
    except Exception:
        return error(400, "qty must be a positive number")

    if market == "TWStock":
        symbol = _twstock_symbol(symbol)
        body["symbol"] = symbol
        body["market"] = market
        body["order_type"] = order_type
        if side == "sell" and _twstock_request_current_qty(body) is None:
            body["current_qty"] = _twstock_position_qty(symbol)
        validation_error = _validate_twstock_order(body, symbol=symbol, side=side, qty=qty_f, order_type=order_type)
        if validation_error:
            return error(400, validation_error)

    if not market_allowed(market):
        return error(403, f"Market not allowed: {market}", http=403)
    if not instrument_allowed(symbol):
        return error(403, f"Instrument not allowed: {symbol}", http=403)

    with with_idempotency("quick_trade_order") as existing:
        if existing:
            return envelope({
                "duplicate": True,
                "previous": existing.get("result"),
            }, message="idempotent replay")

    # Live trading is hard-gated. Even with paper_only=false on the token, the
    # operator must enable AGENT_LIVE_TRADING_ENABLED to actually route to
    # exchange clients — keeping a final environment-level kill switch.
    if (not paper_only()) and _live_trading_kill_switch():
        return error(
            501,
            "Live agent trading is not implemented in this build. "
            "Use the human Quick Trade flow until live agent execution is enabled.",
            http=501,
        )

    last_price = _last_price(market, symbol)
    fill_price, status, note = _paper_fill_decision(
        market=market,
        side=side,
        order_type=order_type,
        limit_price=body.get("limit_price") or body.get("limitPrice"),
        last_price=last_price,
    )
    result = _record_paper_order(body=body, fill_price=fill_price, status=status, note=note)
    return envelope(result, message="paper-fill")


@agent_v1_bp.route("/quick-trade/kill-switch", methods=["POST"])
@agent_required(SCOPE_T)
def kill_switch():
    """Cancel all of the calling tenant's open paper orders.

    This intentionally limits scope to the agent's own surface; revoking live
    exchange orders requires the human admin path (separate, audited).
    """
    with get_db_connection() as db:
        cur = db.cursor()
        cur.execute(
            """
            UPDATE qd_agent_paper_orders
            SET status = 'cancelled', note = COALESCE(note,'') || ' [kill_switch]'
            WHERE user_id = %s AND status NOT IN ('filled','cancelled','rejected')
            """,
            (current_user_id(),),
        )
        affected = cur.rowcount
        db.commit()
        cur.close()
    return envelope({"cancelled_open_paper_orders": int(affected or 0)})
