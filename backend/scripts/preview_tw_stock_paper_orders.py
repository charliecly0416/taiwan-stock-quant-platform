#!/usr/bin/env python3
"""Preview paper TWStock orders from target weights.

Phase 4 safety entry: this script never connects to a broker and never writes
orders. It converts a TWStock rebalance plan into auditable paper order previews
with Taiwan-specific execution checks.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SECRET_KEY", "preview-tw-stock-paper-orders")
os.environ.setdefault("ADMIN_USER", "paper-preview")
os.environ.setdefault("ADMIN_PASSWORD", "paperpreviewpass")

from app.data_sources.tw_stock import TWStockDataSource  # noqa: E402
from app.services.ibkr_trading.symbols import normalize_symbol as normalize_ibkr_symbol  # noqa: E402
from scripts.archive_tw_stock_daily import fetch_finmind_rows, parse_finmind_rows  # noqa: E402
from scripts.plan_tw_stock_rebalance import parse_ranked_items  # noqa: E402


@dataclass(frozen=True)
class PaperOrderPreview:
    symbol: str
    config_symbol: str
    side: str
    qty: int
    order_type: str
    limit_price: float
    reference_price: float
    estimated_notional: float
    status: str
    reasons: List[str]
    contract: Dict[str, Any]
    current_qty: int = 0


def normalize_tw_symbol(symbol: str) -> str:
    raw = str(symbol or "").strip()
    if raw.upper().startswith("TWSTOCK:"):
        raw = raw.split(":", 1)[1]
    return TWStockDataSource.normalize_symbol(raw).symbol or raw.strip().upper()


def ibkr_tw_contract(symbol: str) -> Dict[str, Any]:
    ib_symbol, exchange, currency = normalize_ibkr_symbol(symbol, "TWStock")
    return {
        "secType": "STK",
        "symbol": ib_symbol,
        "exchange": exchange,
        "currency": currency,
        "market": "TWStock",
    }


def load_json(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8")) if path else {}


def parse_positions(payload: Any) -> Dict[str, int]:
    if not payload:
        return {}
    items = payload.get("positions") if isinstance(payload, dict) else payload
    if isinstance(items, dict):
        return {normalize_tw_symbol(symbol): int(float(qty or 0)) for symbol, qty in items.items() if int(float(qty or 0)) > 0}
    out: Dict[str, int] = {}
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            symbol = normalize_tw_symbol(item.get("symbol") or item.get("config_symbol"))
            qty = int(float(item.get("shares") or item.get("qty") or item.get("quantity") or 0))
            if symbol and qty > 0:
                out[symbol] = qty
    return out


def parse_target_weights(payload: Dict[str, Any]) -> Dict[str, float]:
    targets: Dict[str, float] = {}
    positions = payload.get("target_positions") or []
    if isinstance(positions, list) and positions:
        for item in positions:
            if not isinstance(item, dict):
                continue
            symbol = normalize_tw_symbol(item.get("symbol") or item.get("config_symbol"))
            weight = float(item.get("target_weight") or item.get("weight") or 0.0)
            if symbol and weight > 0:
                targets[symbol] = weight
        return targets

    # Allow simulator event output as a convenience.
    weights = payload.get("weights") or {}
    if isinstance(weights, dict) and weights:
        return {normalize_tw_symbol(symbol): float(weight) for symbol, weight in weights.items() if float(weight or 0.0) > 0}

    ranked = parse_ranked_items(payload)
    if ranked:
        raw_weight = 1.0 / len(ranked)
        return {normalize_tw_symbol(item["symbol"]): raw_weight for item in ranked}
    return targets


def parse_prices(payload: Any) -> Dict[str, float]:
    if not payload:
        return {}
    prices = payload.get("prices") if isinstance(payload, dict) else payload
    if not isinstance(prices, dict):
        return {}
    out: Dict[str, float] = {}
    for symbol, value in prices.items():
        price = float(value or 0.0)
        if price > 0:
            out[normalize_tw_symbol(symbol)] = price
    return out


def fetch_last_close(symbol: str, as_of: str, *, lookback_days: int = 10) -> Optional[float]:
    end = datetime.strptime(as_of, "%Y-%m-%d").date()
    start = (end - timedelta(days=max(lookback_days, 1))).isoformat()
    rows = parse_finmind_rows(fetch_finmind_rows(symbol, start, as_of), symbol=symbol)
    clean = [row for row in rows if not row.quality_flags and row.close > 0 and row.trade_date <= as_of]
    return float(clean[-1].close) if clean else None


def resolve_prices(symbols: Sequence[str], price_map: Dict[str, float], as_of: str) -> Dict[str, float]:
    out = dict(price_map)
    for symbol in symbols:
        clean = normalize_tw_symbol(symbol)
        if out.get(clean, 0) > 0:
            continue
        last = fetch_last_close(clean, as_of)
        if last:
            out[clean] = last
    return out


def _limit_price(reference_price: float, side: str, buffer_pct: float) -> float:
    ref = max(float(reference_price or 0.0), 0.0)
    buffer = max(float(buffer_pct or 0.0), 0.0)
    if side == "buy":
        return round(ref * (1.0 + buffer), 2)
    return round(ref * (1.0 - buffer), 2)


def build_order_previews(
    *,
    target_weights: Dict[str, float],
    current_positions: Dict[str, int],
    prices: Dict[str, float],
    portfolio_value: float,
    lot_size: int = 1000,
    limit_buffer: float = 0.005,
    max_order_value: float = 0.0,
    max_total_buy_value: float = 0.0,
    allow_short: bool = False,
) -> Dict[str, Any]:
    lot = max(int(lot_size or 1), 1)
    value = max(float(portfolio_value or 0.0), 0.0)
    symbols = sorted(set(target_weights) | set(current_positions))
    orders: List[PaperOrderPreview] = []
    warnings: List[str] = []
    total_buy_value = 0.0

    for symbol in symbols:
        price = float(prices.get(symbol) or 0.0)
        reasons: List[str] = []
        if price <= 0:
            warnings.append(f"missing_reference_price:{symbol}")
            continue
        target_weight = max(float(target_weights.get(symbol, 0.0)), 0.0)
        target_qty = int((value * target_weight / price) // lot) * lot if value > 0 else 0
        current_qty = int(current_positions.get(symbol, 0) or 0)
        delta = target_qty - current_qty
        if delta == 0:
            if target_weight > 0 and target_qty == 0 and current_qty == 0:
                warnings.append(f"target_below_one_lot:{symbol}")
            continue
        side = "buy" if delta > 0 else "sell"
        qty = abs(delta)
        if side == "sell" and qty > current_qty and not allow_short:
            qty = current_qty
            reasons.append("short_blocked")
        if qty <= 0:
            continue
        if qty % lot != 0:
            rounded = (qty // lot) * lot
            reasons.append("qty_rounded_to_lot")
            qty = rounded
        if qty <= 0:
            continue
        notional = round(qty * price, 2)
        status = "preview"
        if max_order_value and notional > max_order_value:
            status = "blocked"
            reasons.append("max_order_value_exceeded")
        if side == "buy":
            total_buy_value += notional
        orders.append(PaperOrderPreview(
            symbol=symbol,
            config_symbol=f"TWStock:{symbol}",
            side=side,
            qty=int(qty),
            order_type="limit",
            limit_price=_limit_price(price, side, limit_buffer),
            reference_price=round(price, 4),
            estimated_notional=notional,
            status=status,
            reasons=reasons,
            contract=ibkr_tw_contract(symbol),
            current_qty=int(current_qty),
        ))

    if max_total_buy_value and total_buy_value > max_total_buy_value:
        warnings.append("max_total_buy_value_exceeded")
        adjusted = []
        for order in orders:
            if order.side == "buy" and order.status != "blocked":
                data = asdict(order)
                data["status"] = "blocked"
                data["reasons"] = list(order.reasons) + ["max_total_buy_value_exceeded"]
                adjusted.append(PaperOrderPreview(**data))
            else:
                adjusted.append(order)
        orders = adjusted

    blocked_count = sum(1 for order in orders if order.status == "blocked")
    return {
        "market": "TWStock",
        "paper_only": True,
        "order_count": len(orders),
        "blocked_count": blocked_count,
        "total_buy_value": round(total_buy_value, 2),
        "assumptions": {
            "broker": "IBKR",
            "currency": "TWD",
            "exchange": "TWSE",
            "lot_size": lot,
            "order_type": "limit",
            "limit_buffer": limit_buffer,
            "allow_short": bool(allow_short),
            "writes_orders": False,
        },
        "warnings": warnings,
        "orders": [asdict(order) for order in orders],
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Preview paper TWStock orders from target weights.")
    parser.add_argument("--plan-json", required=True, help="JSON from plan_tw_stock_rebalance.py or one rebalance event.")
    parser.add_argument("--positions-json", default="", help="Current positions JSON; defaults to empty portfolio.")
    parser.add_argument("--price-json", default="", help="Optional reference prices JSON.")
    parser.add_argument("--as-of", default=date.today().isoformat())
    parser.add_argument("--portfolio-value", type=float, required=True)
    parser.add_argument("--lot-size", type=int, default=1000)
    parser.add_argument("--limit-buffer", type=float, default=0.005)
    parser.add_argument("--max-order-value", type=float, default=0.0)
    parser.add_argument("--max-total-buy-value", type=float, default=0.0)
    parser.add_argument("--allow-short", action="store_true")
    parser.add_argument("--output-json", default="")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    plan = load_json(args.plan_json)
    target_weights = parse_target_weights(plan)
    current_positions = parse_positions(load_json(args.positions_json))
    symbols = sorted(set(target_weights) | set(current_positions))
    prices = resolve_prices(symbols, parse_prices(load_json(args.price_json)), args.as_of)
    report = build_order_previews(
        target_weights=target_weights,
        current_positions=current_positions,
        prices=prices,
        portfolio_value=args.portfolio_value,
        lot_size=args.lot_size,
        limit_buffer=args.limit_buffer,
        max_order_value=args.max_order_value,
        max_total_buy_value=args.max_total_buy_value,
        allow_short=args.allow_short,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.output_json:
        path = Path(args.output_json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    return 0 if report["order_count"] > 0 and report["blocked_count"] == 0 else (1 if report["order_count"] > 0 else 2)


if __name__ == "__main__":
    raise SystemExit(main())
