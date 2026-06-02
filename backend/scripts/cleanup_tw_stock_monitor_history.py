#!/usr/bin/env python3
"""Clean old TWStock monitor history and scan logs.

Dry-run by default. Use --apply to delete rows. Research-only maintenance:
this script never touches orders, broker clients, or market positions.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SECRET_KEY", "tw-stock-monitor-cleanup")
os.environ.setdefault("ADMIN_USER", "cleanup")
os.environ.setdefault("ADMIN_PASSWORD", "cleanuppass")
os.environ.setdefault("AGENT_LIVE_TRADING_ENABLED", "false")
os.environ.setdefault("ENABLE_PENDING_ORDER_WORKER", "false")
os.environ.setdefault("ENABLE_PORTFOLIO_MONITOR", "false")
os.environ.setdefault("ENABLE_TW_STOCK_MONITOR_WORKER", "false")

from app.utils.db import get_db_connection  # noqa: E402


def clamp_days(value: int, *, default: int, min_days: int = 1, max_days: int = 3650) -> int:
    try:
        days = int(value)
    except Exception:
        days = default
    return max(min_days, min(max_days, days))


def _count_old_rows(cur, *, table: str, column: str, retention_days: int) -> int:
    cur.execute(f"SELECT COUNT(1) AS cnt FROM {table} WHERE {column} < NOW() - (? * INTERVAL '1 day')", (retention_days,))
    row = cur.fetchone() or {}
    return int(row.get("cnt") or 0)


def _delete_old_rows(cur, *, table: str, column: str, retention_days: int) -> int:
    cur.execute(f"DELETE FROM {table} WHERE {column} < NOW() - (? * INTERVAL '1 day')", (retention_days,))
    return int(getattr(cur, "rowcount", 0) or 0)


def cleanup_monitor_history(*, trend_retention_days: int = 365, scan_log_retention_days: int = 90, apply: bool = False) -> Dict[str, Any]:
    trend_retention_days = clamp_days(trend_retention_days, default=365)
    scan_log_retention_days = clamp_days(scan_log_retention_days, default=90)
    with get_db_connection() as db:
        cur = db.cursor()
        trend_old_count = _count_old_rows(
            cur,
            table="qd_tw_stock_trend_history",
            column="scanned_at",
            retention_days=trend_retention_days,
        )
        scan_log_old_count = _count_old_rows(
            cur,
            table="qd_tw_stock_monitor_scan_logs",
            column="created_at",
            retention_days=scan_log_retention_days,
        )
        trend_deleted = 0
        scan_log_deleted = 0
        if apply:
            trend_deleted = _delete_old_rows(
                cur,
                table="qd_tw_stock_trend_history",
                column="scanned_at",
                retention_days=trend_retention_days,
            )
            scan_log_deleted = _delete_old_rows(
                cur,
                table="qd_tw_stock_monitor_scan_logs",
                column="created_at",
                retention_days=scan_log_retention_days,
            )
            db.commit()
        cur.close()
    return {
        "apply": bool(apply),
        "trend_retention_days": trend_retention_days,
        "scan_log_retention_days": scan_log_retention_days,
        "trend_old_count": trend_old_count,
        "scan_log_old_count": scan_log_old_count,
        "trend_deleted": trend_deleted,
        "scan_log_deleted": scan_log_deleted,
        "orders_enabled": False,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Clean old TWStock monitor trend history and scan logs.")
    parser.add_argument("--trend-retention-days", type=int, default=365, help="Keep trend history for N days. Default: 365.")
    parser.add_argument("--scan-log-retention-days", type=int, default=90, help="Keep scan logs for N days. Default: 90.")
    parser.add_argument("--apply", action="store_true", help="Actually delete old rows. Without this flag the script is dry-run.")
    parser.add_argument("--dry-run", action="store_true", help="Force dry-run even if --apply is also supplied.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    report = cleanup_monitor_history(
        trend_retention_days=args.trend_retention_days,
        scan_log_retention_days=args.scan_log_retention_days,
        apply=bool(args.apply and not args.dry_run),
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
