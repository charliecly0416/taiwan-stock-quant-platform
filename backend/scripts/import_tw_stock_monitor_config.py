#!/usr/bin/env python3
"""Import a reviewed TWStock monitor config JSON.

Dry-run by default. Use --apply to upsert qd_tw_stock_monitor_configs.
This script only changes research monitor configuration; it never scans,
creates alerts, submits orders, or touches broker clients.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Sequence

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SECRET_KEY", "tw-stock-monitor-import")
os.environ.setdefault("ADMIN_USER", "monitor-import")
os.environ.setdefault("ADMIN_PASSWORD", "monitorimportpass")
os.environ.setdefault("AGENT_LIVE_TRADING_ENABLED", "false")
os.environ.setdefault("ENABLE_PENDING_ORDER_WORKER", "false")
os.environ.setdefault("ENABLE_PORTFOLIO_MONITOR", "false")
os.environ.setdefault("ENABLE_TW_STOCK_MONITOR_WORKER", "false")

from app.data_sources.tw_stock import TWStockDataSource  # noqa: E402
from app.services.tw_stock_monitor import monitor_config_from_row  # noqa: E402
from app.utils.db import get_db_connection  # noqa: E402


def _symbols_from_value(value: Any) -> list[str]:
    raw_items = value if isinstance(value, list) else str(value or "").split(",")
    out: list[str] = []
    seen = set()
    for item in raw_items:
        symbol = TWStockDataSource.normalize_symbol(str(item or "")).symbol
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        out.append(symbol)
    return out[:50]


def load_config_json(path: str | Path) -> Dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("monitor config JSON must be an object")
    return payload


def normalize_config(payload: Dict[str, Any], *, user_id: int = 1, name_override: str = "", enabled_override: bool | None = None) -> Dict[str, Any]:
    name = str(name_override or payload.get("name") or payload.get("monitor_name") or "default").strip()[:80] or "default"
    symbols = _symbols_from_value(payload.get("symbols") or payload.get("symbols_csv") or payload.get("symbolsCsv"))
    if not symbols:
        raise ValueError("monitor config must include at least one symbol")
    try:
        limit_bars = max(20, min(int(payload.get("limit_bars") or payload.get("limit") or 120), 500))
    except Exception:
        limit_bars = 120
    try:
        refresh_interval_sec = max(0, min(int(payload.get("refresh_interval_sec") or payload.get("interval") or 300), 86400))
    except Exception:
        refresh_interval_sec = 300
    try:
        threshold = max(0.0, min(float(payload.get("score_change_threshold") or payload.get("threshold") or 8.0), 100.0))
    except Exception:
        threshold = 8.0
    enabled = bool(payload.get("enabled", False)) if enabled_override is None else bool(enabled_override)
    notes = str(payload.get("notes") or "Imported by import_tw_stock_monitor_config.py; research-only, no automatic trading.")[:2000]
    return {
        "user_id": max(1, int(user_id or 1)),
        "name": name,
        "symbols": symbols,
        "limit_bars": limit_bars,
        "refresh_interval_sec": refresh_interval_sec,
        "score_change_threshold": threshold,
        "enabled": enabled,
        "notes": notes,
    }


def upsert_monitor_config(config: Dict[str, Any]) -> Dict[str, Any]:
    with get_db_connection() as db:
        cur = db.cursor()
        cur.execute(
            """
            INSERT INTO qd_tw_stock_monitor_configs
                (user_id, name, symbols_json, limit_bars, refresh_interval_sec,
                 score_change_threshold, enabled, notes, created_at, updated_at)
            VALUES (?, ?, ?::jsonb, ?, ?, ?, ?, ?, NOW(), NOW())
            ON CONFLICT (user_id, name) DO UPDATE SET
                symbols_json = EXCLUDED.symbols_json,
                limit_bars = EXCLUDED.limit_bars,
                refresh_interval_sec = EXCLUDED.refresh_interval_sec,
                score_change_threshold = EXCLUDED.score_change_threshold,
                enabled = EXCLUDED.enabled,
                notes = EXCLUDED.notes,
                updated_at = NOW()
            RETURNING id, user_id, name, symbols_json, limit_bars, refresh_interval_sec,
                      score_change_threshold, enabled, notes, created_at, updated_at
            """,
            (
                config["user_id"],
                config["name"],
                json.dumps(config["symbols"]),
                config["limit_bars"],
                config["refresh_interval_sec"],
                config["score_change_threshold"],
                config["enabled"],
                config["notes"],
            ),
        )
        row = cur.fetchone()
        cur.close()
        db.commit()
    return monitor_config_from_row(row, user_id=config["user_id"], name=config["name"])


def import_monitor_config(*, path: str | Path, user_id: int = 1, name: str = "", enabled: bool | None = None, apply: bool = False) -> Dict[str, Any]:
    config = normalize_config(load_config_json(path), user_id=user_id, name_override=name, enabled_override=enabled)
    report: Dict[str, Any] = {
        "apply": bool(apply),
        "config": config,
        "symbol_count": len(config["symbols"]),
        "orders_enabled": False,
        "scanned": False,
        "alerts_created": 0,
    }
    if apply:
        report["saved"] = upsert_monitor_config(config)
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import reviewed TWStock monitor config JSON.")
    parser.add_argument("--input-json", required=True, help="Path to monitor config JSON generated/reviewed by the user.")
    parser.add_argument("--user-id", type=int, default=1)
    parser.add_argument("--name", default="", help="Optional monitor name override.")
    parser.add_argument("--enabled", action="store_true", help="Enable imported monitor config. Default follows JSON, usually false.")
    parser.add_argument("--disabled", action="store_true", help="Force imported monitor config disabled.")
    parser.add_argument("--apply", action="store_true", help="Write qd_tw_stock_monitor_configs. Default is dry-run.")
    parser.add_argument("--dry-run", action="store_true", help="Force dry-run even if --apply is supplied.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    enabled_override = None
    if args.enabled:
        enabled_override = True
    if args.disabled:
        enabled_override = False
    report = import_monitor_config(
        path=args.input_json,
        user_id=args.user_id,
        name=args.name,
        enabled=enabled_override,
        apply=bool(args.apply and not args.dry_run),
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
