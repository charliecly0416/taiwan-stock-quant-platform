#!/usr/bin/env python3
"""Report TWStock monitor scan health from existing scan logs.

Read-only: this script only reads qd_tw_stock_monitor_scan_logs and prints a
summary. It does not run scans, create alerts, write production data, submit
orders, or touch broker clients.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, Sequence

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SECRET_KEY", "tw-stock-monitor-health")
os.environ.setdefault("ADMIN_USER", "monitor-health")
os.environ.setdefault("ADMIN_PASSWORD", "monitorhealthpass")
os.environ.setdefault("AGENT_LIVE_TRADING_ENABLED", "false")
os.environ.setdefault("ENABLE_PENDING_ORDER_WORKER", "false")
os.environ.setdefault("ENABLE_PORTFOLIO_MONITOR", "false")
os.environ.setdefault("ENABLE_TW_STOCK_MONITOR_WORKER", "false")

from app.services.tw_stock_monitor import summarize_scan_health  # noqa: E402
from app.utils.db import get_db_connection  # noqa: E402


def load_scan_logs(*, limit: int = 20, db_factory=get_db_connection) -> list[Dict[str, Any]]:
    limit = max(1, min(int(limit or 20), 100))
    with db_factory() as db:
        cur = db.cursor()
        cur.execute(
            """
            SELECT id, trigger_source, status, monitor_count, scanned_count, alert_count,
                   error, result_summary, duration_ms, created_at
            FROM qd_tw_stock_monitor_scan_logs
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall() or []
        cur.close()
    items: list[Dict[str, Any]] = []
    for row in rows:
        summary = row.get("result_summary") or {}
        if isinstance(summary, str) and summary.strip():
            try:
                summary = json.loads(summary)
            except Exception:
                summary = {}
        items.append({
            "id": row.get("id"),
            "trigger_source": row.get("trigger_source"),
            "status": row.get("status"),
            "monitor_count": int(row.get("monitor_count") or 0),
            "scanned_count": int(row.get("scanned_count") or 0),
            "alert_count": int(row.get("alert_count") or 0),
            "error": row.get("error") or "",
            "result_summary": summary if isinstance(summary, dict) else {},
            "duration_ms": row.get("duration_ms"),
            "created_at": row.get("created_at"),
        })
    return items


def build_health_report(*, limit: int = 20, logs: list[Dict[str, Any]] | None = None, db_factory=get_db_connection) -> Dict[str, Any]:
    items = list(logs) if logs is not None else load_scan_logs(limit=limit, db_factory=db_factory)
    return {
        "limit": max(1, min(int(limit or 20), 100)),
        "items": items,
        "health": summarize_scan_health(items),
        "scanned": False,
        "alerts_created": 0,
        "orders_enabled": False,
        "writes_production_data": False,
        "connects_to_broker": False,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only TWStock monitor scan health report.")
    parser.add_argument("--limit", type=int, default=20, help="Number of recent scan logs to inspect.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    report = build_health_report(limit=args.limit)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
