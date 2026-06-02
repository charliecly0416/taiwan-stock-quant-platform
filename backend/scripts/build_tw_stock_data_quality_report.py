#!/usr/bin/env python3
"""Build a read-only TWStock monitor data-quality report.

This script wraps the monitor-config preflight output into a compact JSON and
optional Markdown report for manual review. It does not import monitor configs,
run scans, create alerts, write production data, submit orders, or touch broker
clients.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Sequence

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SECRET_KEY", "tw-stock-quality-report")
os.environ.setdefault("ADMIN_USER", "quality-report")
os.environ.setdefault("ADMIN_PASSWORD", "qualityreportpass")
os.environ.setdefault("AGENT_LIVE_TRADING_ENABLED", "false")
os.environ.setdefault("ENABLE_PENDING_ORDER_WORKER", "false")
os.environ.setdefault("ENABLE_PORTFOLIO_MONITOR", "false")
os.environ.setdefault("ENABLE_TW_STOCK_MONITOR_WORKER", "false")

from scripts.preflight_tw_stock_monitor_config import preflight_monitor_config  # noqa: E402


def _symbol_status(item: Dict[str, Any], failures_by_symbol: Dict[str, list[Dict[str, Any]]]) -> Dict[str, Any]:
    symbol = str(item.get("symbol") or "")
    quality = item.get("quality") or {}
    latest = item.get("latest") or {}
    trend = item.get("trend") or {}
    failures = failures_by_symbol.get(symbol, [])
    return {
        "symbol": symbol,
        "ok": bool(item.get("ok")),
        "latest_date": quality.get("latest_date") or latest.get("date") or "",
        "bar_count": quality.get("bar_count"),
        "stale_days": quality.get("stale_days"),
        "trend_label": trend.get("label") or "",
        "trend_score": trend.get("score"),
        "warnings": list(quality.get("warnings") or []),
        "failures": failures,
    }


def summarize_preflight_report(preflight: Dict[str, Any], *, input_json: str) -> Dict[str, Any]:
    quality_gate = preflight.get("quality_gate") or {}
    failures_by_symbol: Dict[str, list[Dict[str, Any]]] = {}
    for failure in quality_gate.get("failures") or []:
        symbol = str(failure.get("symbol") or "")
        failures_by_symbol.setdefault(symbol, []).append(dict(failure))
    symbols = [_symbol_status(item, failures_by_symbol) for item in preflight.get("items") or []]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_json": input_json,
        "config_name": (preflight.get("config") or {}).get("name") or "",
        "symbol_count": preflight.get("symbol_count", 0),
        "ok_count": preflight.get("ok_count", 0),
        "failed_count": preflight.get("failed_count", 0),
        "warning_count": preflight.get("warning_count", 0),
        "quality_gate": quality_gate,
        "symbols": symbols,
        "orders_enabled": False,
        "writes_production_data": False,
        "connects_to_broker": False,
        "scanned": False,
        "alerts_created": 0,
    }


def render_markdown(report: Dict[str, Any]) -> str:
    gate = report.get("quality_gate") or {}
    lines = [
        "# TWStock Data Quality Report",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- input_json: `{report.get('input_json')}`",
        f"- config_name: `{report.get('config_name')}`",
        f"- quality_gate_status: `{gate.get('status')}`",
        f"- ready_for_manual_review: `{gate.get('ready_for_manual_review')}`",
        f"- symbol_count: `{report.get('symbol_count')}`",
        f"- failed_count: `{report.get('failed_count')}`",
        f"- warning_count: `{report.get('warning_count')}`",
        f"- orders_enabled: `{report.get('orders_enabled')}`",
        f"- writes_production_data: `{report.get('writes_production_data')}`",
        f"- connects_to_broker: `{report.get('connects_to_broker')}`",
        "",
        "| Symbol | OK | Latest Date | Bars | Stale Days | Trend | Score | Warnings | Failures |",
        "|---|---:|---|---:|---:|---|---:|---|---|",
    ]
    for item in report.get("symbols") or []:
        warnings = ",".join(item.get("warnings") or [])
        failures = ",".join(f.get("reason", "") for f in item.get("failures") or [])
        lines.append(
            f"| {item.get('symbol')} | {item.get('ok')} | {item.get('latest_date')} | "
            f"{item.get('bar_count')} | {item.get('stale_days')} | {item.get('trend_label')} | "
            f"{item.get('trend_score')} | {warnings} | {failures} |"
        )
    return "\n".join(lines) + "\n"


def build_quality_report(
    *,
    input_json: str,
    user_id: int = 1,
    name: str = "",
    limit: int | None = None,
    min_bars: int = 60,
    max_stale_days: int = 5,
    preflight: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    raw = preflight or preflight_monitor_config(
        path=input_json,
        user_id=user_id,
        name=name,
        limit=limit,
        min_bars=min_bars,
        max_stale_days=max_stale_days,
    )
    return summarize_preflight_report(raw, input_json=input_json)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build read-only TWStock data-quality report for manual review.")
    parser.add_argument("--input-json", required=True, help="Monitor config JSON to preflight and summarize.")
    parser.add_argument("--user-id", type=int, default=1)
    parser.add_argument("--name", default="", help="Optional monitor name override.")
    parser.add_argument("--limit", type=int, default=0, help="Override daily bar limit for trend analysis.")
    parser.add_argument("--min-bars", type=int, default=60)
    parser.add_argument("--max-stale-days", type=int, default=5)
    parser.add_argument("--output-json", default="", help="Optional path to write JSON report.")
    parser.add_argument("--output-md", default="", help="Optional path to write Markdown report.")
    parser.add_argument("--fail-on-quality-gate", action="store_true", help="Exit non-zero when quality gate is not ready for manual review.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    report = build_quality_report(
        input_json=args.input_json,
        user_id=args.user_id,
        name=args.name,
        limit=args.limit or None,
        min_bars=max(1, int(args.min_bars or 60)),
        max_stale_days=max(0, int(args.max_stale_days or 5)),
    )
    text = json.dumps(report, ensure_ascii=False, sort_keys=True)
    print(text)
    if args.output_json:
        path = Path(args.output_json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.output_md:
        path = Path(args.output_md)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_markdown(report), encoding="utf-8")
    if args.fail_on_quality_gate and not (report.get("quality_gate") or {}).get("ready_for_manual_review"):
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
