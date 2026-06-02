#!/usr/bin/env python3
"""Preflight a TWStock monitor config before importing/enabling it.

This script reads a reviewed monitor config JSON, runs read-only trend analysis
for each symbol, and prints a quality report. It never writes the database,
creates alerts, runs monitor scans, submits orders, or touches broker clients.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Sequence

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SECRET_KEY", "tw-stock-monitor-preflight")
os.environ.setdefault("ADMIN_USER", "monitor-preflight")
os.environ.setdefault("ADMIN_PASSWORD", "monitorpreflightpass")
os.environ.setdefault("AGENT_LIVE_TRADING_ENABLED", "false")
os.environ.setdefault("ENABLE_PENDING_ORDER_WORKER", "false")
os.environ.setdefault("ENABLE_PORTFOLIO_MONITOR", "false")
os.environ.setdefault("ENABLE_TW_STOCK_MONITOR_WORKER", "false")

from app.services.tw_stock_trend import TWStockTrendService  # noqa: E402
from scripts.import_tw_stock_monitor_config import load_config_json, normalize_config  # noqa: E402


def evaluate_quality_gate(
    reports: Sequence[Dict[str, Any]],
    *,
    min_bars: int = 60,
    max_stale_days: int = 5,
) -> Dict[str, Any]:
    failures: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    min_seen_bar_count: int | None = None
    max_seen_stale_days: int | None = None

    for item in reports:
        symbol = str(item.get("symbol") or "").strip()
        quality = item.get("quality") or {}
        item_warnings = list(quality.get("warnings") or [])
        bar_count = quality.get("bar_count")
        stale_days = quality.get("stale_days")
        if isinstance(bar_count, int):
            min_seen_bar_count = bar_count if min_seen_bar_count is None else min(min_seen_bar_count, bar_count)
        if isinstance(stale_days, int):
            max_seen_stale_days = stale_days if max_seen_stale_days is None else max(max_seen_stale_days, stale_days)

        if not item.get("ok"):
            failures.append({"symbol": symbol, "reason": item.get("error") or "trend_analysis_failed"})
            continue
        if isinstance(bar_count, int) and bar_count < min_bars:
            failures.append({"symbol": symbol, "reason": "insufficient_history", "bar_count": bar_count})
        if isinstance(stale_days, int) and stale_days > max_stale_days:
            failures.append({"symbol": symbol, "reason": "stale_daily_bar", "stale_days": stale_days})
        if "latest_bar_in_future" in item_warnings:
            failures.append({"symbol": symbol, "reason": "latest_bar_in_future"})

        soft_warnings = [
            warning
            for warning in item_warnings
            if warning not in {"short_history_below_60_bars", "stale_daily_bar", "latest_bar_in_future", "no_daily_bars"}
        ]
        if soft_warnings:
            warnings.append({"symbol": symbol, "warnings": soft_warnings})

    return {
        "ready_for_manual_review": len(failures) == 0,
        "status": "pass" if not failures and not warnings else ("fail" if failures else "warn"),
        "min_bars_required": int(min_bars),
        "max_stale_days_allowed": int(max_stale_days),
        "min_seen_bar_count": min_seen_bar_count,
        "max_seen_stale_days": max_seen_stale_days,
        "failure_count": len(failures),
        "warning_count": len(warnings),
        "failures": failures,
        "warnings": warnings,
        "orders_enabled": False,
        "db_written": False,
    }


def summarize_report(
    config: Dict[str, Any],
    reports: Sequence[Dict[str, Any]],
    *,
    min_bars: int = 60,
    max_stale_days: int = 5,
) -> Dict[str, Any]:
    ok_items = [item for item in reports if item.get("ok")]
    failed_items = [item for item in reports if not item.get("ok")]
    warning_items = [item for item in ok_items if ((item.get("quality") or {}).get("warnings") or [])]
    quality_gate = evaluate_quality_gate(reports, min_bars=min_bars, max_stale_days=max_stale_days)
    return {
        "config": config,
        "symbol_count": len(config.get("symbols") or []),
        "ok_count": len(ok_items),
        "failed_count": len(failed_items),
        "warning_count": len(warning_items),
        "failed_symbols": [item.get("symbol") for item in failed_items],
        "warning_symbols": [item.get("symbol") for item in warning_items],
        "items": reports,
        "orders_enabled": False,
        "scanned": False,
        "alerts_created": 0,
        "db_written": False,
        "quality_gate": quality_gate,
    }


def preflight_monitor_config(
    *,
    path: str,
    user_id: int = 1,
    name: str = "",
    limit: int | None = None,
    trend_service: TWStockTrendService | None = None,
    min_bars: int = 60,
    max_stale_days: int = 5,
) -> Dict[str, Any]:
    config = normalize_config(load_config_json(path), user_id=user_id, name_override=name)
    service = trend_service or TWStockTrendService()
    limit_bars = max(20, min(int(limit or config.get("limit_bars") or 120), 500))
    reports = [service.analyze_symbol(symbol=symbol, limit=limit_bars) for symbol in config["symbols"]]
    return summarize_report(config, reports, min_bars=min_bars, max_stale_days=max_stale_days)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only preflight for TWStock monitor config JSON.")
    parser.add_argument("--input-json", required=True, help="Path to reviewed monitor config JSON.")
    parser.add_argument("--user-id", type=int, default=1)
    parser.add_argument("--name", default="", help="Optional monitor name override.")
    parser.add_argument("--limit", type=int, default=0, help="Override daily bar limit for trend analysis.")
    parser.add_argument("--fail-on-warning", action="store_true", help="Exit non-zero if any symbol has quality warnings.")
    parser.add_argument("--min-bars", type=int, default=60, help="Minimum daily bars required by the read-only quality gate.")
    parser.add_argument("--max-stale-days", type=int, default=5, help="Maximum allowed calendar days since latest daily bar.")
    parser.add_argument("--fail-on-quality-gate", action="store_true", help="Exit non-zero if the read-only quality gate fails.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    report = preflight_monitor_config(
        path=args.input_json,
        user_id=args.user_id,
        name=args.name,
        limit=args.limit or None,
        min_bars=max(1, int(args.min_bars or 60)),
        max_stale_days=max(0, int(args.max_stale_days or 5)),
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    if report["failed_count"] > 0:
        return 2
    if args.fail_on_quality_gate and not report["quality_gate"]["ready_for_manual_review"]:
        return 3
    if args.fail_on_warning and report["warning_count"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
