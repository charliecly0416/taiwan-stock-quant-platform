#!/usr/bin/env python3
"""Build a read-only TWStock monitor alert review report.

This script reads existing monitor alerts and summarizes them for manual
review. It does not create alerts, send notifications, run scans, write
production data, submit orders, or touch broker clients.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Sequence

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SECRET_KEY", "tw-stock-alert-review")
os.environ.setdefault("ADMIN_USER", "alert-review")
os.environ.setdefault("ADMIN_PASSWORD", "alertreviewpass")
os.environ.setdefault("AGENT_LIVE_TRADING_ENABLED", "false")
os.environ.setdefault("ENABLE_PENDING_ORDER_WORKER", "false")
os.environ.setdefault("ENABLE_PORTFOLIO_MONITOR", "false")
os.environ.setdefault("ENABLE_TW_STOCK_MONITOR_WORKER", "false")

from app.utils.db import get_db_connection  # noqa: E402


def _safe_json_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _alert_category(row: Dict[str, Any]) -> str:
    snapshot = _safe_json_dict(row.get("snapshot"))
    context = snapshot.get("alert_context") if isinstance(snapshot, dict) else {}
    category = (context or {}).get("category") if isinstance(context, dict) else ""
    if category:
        return str(category)
    alert_type = str(row.get("alert_type") or "")
    if alert_type == "quality_warning":
        return "data_quality"
    if alert_type in {"label_change", "score_change"}:
        return "trend_change"
    return "other"


def normalize_alert_row(row: Dict[str, Any]) -> Dict[str, Any]:
    snapshot = _safe_json_dict(row.get("snapshot"))
    context = snapshot.get("alert_context") if isinstance(snapshot, dict) else {}
    context = context if isinstance(context, dict) else {}
    return {
        "id": row.get("id"),
        "user_id": int(row.get("user_id") or 1),
        "monitor_name": row.get("monitor_name") or "default",
        "symbol": row.get("symbol") or "",
        "alert_type": row.get("alert_type") or "",
        "category": _alert_category(row),
        "reason": context.get("reason") or "",
        "severity": row.get("severity") or "info",
        "message": row.get("message") or "",
        "is_read": bool(row.get("is_read")),
        "decision_status": row.get("decision_status") or "pending",
        "user_note": row.get("user_note") or "",
        "human_action": context.get("human_action") or "",
        "created_at": row.get("created_at"),
        "orders_enabled": False,
    }


def summarize_alerts(alerts: list[Dict[str, Any]]) -> Dict[str, Any]:
    items = list(alerts or [])
    by_category = Counter(item.get("category") or "other" for item in items)
    by_type = Counter(item.get("alert_type") or "unknown" for item in items)
    by_status = Counter(item.get("decision_status") or "pending" for item in items)
    by_severity = Counter(item.get("severity") or "info" for item in items)
    unread = sum(1 for item in items if not item.get("is_read"))
    return {
        "alert_count": len(items),
        "unread_count": unread,
        "by_category": dict(sorted(by_category.items())),
        "by_alert_type": dict(sorted(by_type.items())),
        "by_decision_status": dict(sorted(by_status.items())),
        "by_severity": dict(sorted(by_severity.items())),
        "needs_review_count": sum(1 for item in items if (not item.get("is_read")) or item.get("decision_status") == "pending"),
        "orders_enabled": False,
        "writes_production_data": False,
        "connects_to_broker": False,
    }


def load_alerts(*, user_id: int = 1, name: str = "default", limit: int = 100, db_factory=get_db_connection) -> list[Dict[str, Any]]:
    limit = max(1, min(int(limit or 100), 500))
    with db_factory() as db:
        cur = db.cursor()
        cur.execute(
            """
            SELECT id, user_id, monitor_name, symbol, alert_type, severity, message,
                   snapshot, is_read, decision_status, user_note, created_at, acknowledged_at
            FROM qd_tw_stock_monitor_alerts
            WHERE user_id = ? AND monitor_name = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (user_id, name, limit),
        )
        rows = cur.fetchall() or []
        cur.close()
    return [normalize_alert_row(row) for row in rows]


def build_alert_review_report(*, user_id: int = 1, name: str = "default", limit: int = 100, alerts: list[Dict[str, Any]] | None = None, db_factory=get_db_connection) -> Dict[str, Any]:
    items = list(alerts) if alerts is not None else load_alerts(user_id=user_id, name=name, limit=limit, db_factory=db_factory)
    return {
        "user_id": int(user_id or 1),
        "monitor_name": name or "default",
        "limit": max(1, min(int(limit or 100), 500)),
        "summary": summarize_alerts(items),
        "items": items,
        "alerts_created": 0,
        "notifications_sent": 0,
        "orders_enabled": False,
        "writes_production_data": False,
        "connects_to_broker": False,
    }


def render_markdown(report: Dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# TWStock Alert Review Report",
        "",
        f"- user_id: `{report.get('user_id')}`",
        f"- monitor_name: `{report.get('monitor_name')}`",
        f"- alert_count: `{summary.get('alert_count')}`",
        f"- unread_count: `{summary.get('unread_count')}`",
        f"- needs_review_count: `{summary.get('needs_review_count')}`",
        f"- by_category: `{json.dumps(summary.get('by_category') or {}, ensure_ascii=False, sort_keys=True)}`",
        f"- orders_enabled: `{report.get('orders_enabled')}`",
        f"- writes_production_data: `{report.get('writes_production_data')}`",
        f"- connects_to_broker: `{report.get('connects_to_broker')}`",
        "",
        "| ID | Symbol | Category | Type | Severity | Status | Read | Message |",
        "|---:|---|---|---|---|---|---:|---|",
    ]
    for item in report.get("items") or []:
        message = str(item.get("message") or "").replace("|", "/")[:120]
        lines.append(
            f"| {item.get('id')} | {item.get('symbol')} | {item.get('category')} | {item.get('alert_type')} | "
            f"{item.get('severity')} | {item.get('decision_status')} | {item.get('is_read')} | {message} |"
        )
    return "\n".join(lines) + "\n"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only TWStock monitor alert review report.")
    parser.add_argument("--user-id", type=int, default=1)
    parser.add_argument("--name", default="default")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--output-md", default="", help="Optional Markdown report path.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    report = build_alert_review_report(user_id=args.user_id, name=args.name, limit=args.limit)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    if args.output_md:
        path = Path(args.output_md)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_markdown(report), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
