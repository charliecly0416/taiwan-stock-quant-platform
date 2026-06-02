#!/usr/bin/env python3
"""Run TWStock monitor scans outside the API process.

Research-only: this script calls the same scan-all function used by the API
worker. It writes scan logs / alerts / trend history, but never creates orders
or touches broker clients.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SECRET_KEY", "tw-stock-monitor-scan")
os.environ.setdefault("ADMIN_USER", "monitor")
os.environ.setdefault("ADMIN_PASSWORD", "monitorpass")
os.environ.setdefault("AGENT_LIVE_TRADING_ENABLED", "false")
os.environ.setdefault("ENABLE_PENDING_ORDER_WORKER", "false")
os.environ.setdefault("ENABLE_PORTFOLIO_MONITOR", "false")
os.environ.setdefault("ENABLE_TW_STOCK_MONITOR_WORKER", "false")


def run_scan_once(*, force: bool = False, trigger_source: str = "cron", write_log: bool = True) -> Dict[str, Any]:
    from app.routes.tw_stock import run_tw_stock_monitor_scan_all

    # Compatibility wrapper delegates to app.services.tw_stock_monitor.
    return run_tw_stock_monitor_scan_all(force=force, trigger_source=trigger_source, write_log=write_log)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run TWStock monitor scan-all as an independent worker/cron command.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="Run one scan and exit. This is the default and recommended cron mode.")
    mode.add_argument("--loop", action="store_true", help="Run scans forever with --interval-sec sleeps.")
    parser.add_argument("--interval-sec", type=int, default=900, help="Loop interval in seconds; clamped to [30, 86400].")
    parser.add_argument("--force", action="store_true", help="Scan disabled configs too. Default scans enabled configs only.")
    parser.add_argument("--trigger-source", default="cron", help="Value stored in scan logs, e.g. cron, worker, systemd.")
    parser.add_argument("--no-log", action="store_true", help="Do not write qd_tw_stock_monitor_scan_logs.")
    parser.add_argument("--max-runs", type=int, default=0, help="For tests/controlled runs: stop loop after N scans. 0 means unlimited.")
    return parser


def clamp_interval(seconds: int) -> int:
    try:
        value = int(seconds)
    except Exception:
        value = 900
    return max(30, min(86400, value))


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    loop = bool(args.loop)  # Without --loop, run once and exit.
    interval_sec = clamp_interval(args.interval_sec)
    write_log = not bool(args.no_log)
    run_count = 0

    while True:
        started = time.monotonic()
        result = run_scan_once(force=bool(args.force), trigger_source=str(args.trigger_source or "cron")[:40], write_log=write_log)
        run_count += 1
        print(json.dumps({
            "status": "success",
            "run_count": run_count,
            "count": result.get("count", 0),
            "total_scanned_count": result.get("total_scanned_count", 0),
            "total_alert_count": result.get("total_alert_count", 0),
            "orders_enabled": bool((result.get("trading") or {}).get("orders_enabled", False)),
            "duration_ms": int((time.monotonic() - started) * 1000),
        }, ensure_ascii=False), flush=True)

        if not loop or (args.max_runs and run_count >= int(args.max_runs)):
            return 0
        time.sleep(max(1, interval_sec - (time.monotonic() - started)))


if __name__ == "__main__":
    raise SystemExit(main())
