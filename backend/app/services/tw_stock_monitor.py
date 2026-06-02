"""Service-layer TWStock monitor scanning logic.

Research-only: functions in this module persist trend monitor state, alerts,
history, and scan logs. They never create orders or touch broker clients.
"""
from __future__ import annotations

import json
import time
from typing import Callable

from app.utils.logger import get_logger

logger = get_logger(__name__)

DbFactory = Callable[[], object]
InsertAlert = Callable[..., dict]
MAX_MONITOR_SYMBOLS = 100


def symbols_from_value(value) -> list[str]:
    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = str(value or "").split(",")
    out = []
    seen = set()
    for item in raw_items:
        symbol = str(item or "").strip()
        if not symbol:
            continue
        normalized = symbol.upper()
        if normalized not in seen:
            seen.add(normalized)
            out.append(normalized)
    return out[:MAX_MONITOR_SYMBOLS]


def monitor_config_from_row(row: dict | None, *, user_id: int, name: str) -> dict:
    if not row:
        return {
            "user_id": user_id,
            "name": name,
            "symbols": ["2330", "0050", "00878"],
            "limit_bars": 120,
            "refresh_interval_sec": 300,
            "score_change_threshold": 8.0,
            "enabled": False,
            "notes": "",
        }
    symbols = row.get("symbols_json") or []
    if isinstance(symbols, str):
        try:
            symbols = json.loads(symbols)
        except Exception:
            symbols = []
    return {
        "id": row.get("id"),
        "user_id": int(row.get("user_id") or user_id),
        "name": row.get("name") or name,
        "symbols": symbols_from_value(symbols),
        "limit_bars": int(row.get("limit_bars") or 120),
        "refresh_interval_sec": int(row.get("refresh_interval_sec") or 300),
        "score_change_threshold": float(row.get("score_change_threshold") or 8),
        "enabled": bool(row.get("enabled")),
        "notes": row.get("notes") or "",
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def warnings_set(report: dict) -> set[str]:
    warnings = ((report.get("quality") or {}).get("warnings") or []) if isinstance(report, dict) else []
    return {str(item) for item in warnings}


def build_alert_payload(*, alert_type: str, severity: str, symbol: str, message: str, reason: str, category: str, human_action: str) -> dict:
    return {
        "type": alert_type,
        "severity": severity,
        "message": message,
        "category": category,
        "reason": reason,
        "human_action": human_action,
        "orders_enabled": False,
    }


def snapshot_with_alert_context(report: dict, alert: dict) -> dict:
    snapshot = dict(report or {})
    snapshot["alert_context"] = {
        "category": alert.get("category") or "trend_monitor",
        "reason": alert.get("reason") or alert.get("type") or "unknown",
        "human_action": alert.get("human_action") or "人工复盘后决定，不自动交易。",
        "orders_enabled": False,
    }
    return snapshot


def insert_trend_history(db, *, user_id: int, name: str, symbol: str, report: dict) -> None:
    trend = report.get("trend") or {}
    latest = report.get("latest") or {}
    quality = report.get("quality") or {}
    cur = db.cursor()
    cur.execute(
        """
        INSERT INTO qd_tw_stock_trend_history
            (user_id, monitor_name, symbol, label, score, latest_date, latest_close,
             warnings_json, snapshot, scanned_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?::jsonb, ?::jsonb, NOW())
        """,
        (
            user_id,
            name,
            symbol,
            str(trend.get("label") or "unknown")[:40],
            float(trend.get("score") or 0.0),
            str(quality.get("latest_date") or latest.get("date") or "")[:20],
            float(latest.get("close") or 0.0),
            json.dumps(quality.get("warnings") or []),
            json.dumps(report),
        ),
    )
    cur.close()


def build_scan_alerts(symbol: str, report: dict, previous: dict | None, threshold: float) -> list[dict]:
    alerts = []
    trend = report.get("trend") or {}
    label = str(trend.get("label") or "unknown")
    score = float(trend.get("score") or 0.0)
    warnings_now = warnings_set(report)
    if not previous:
        if warnings_now:
            alerts.append(build_alert_payload(
                alert_type="quality_warning",
                severity="warning",
                symbol=symbol,
                message=f"{symbol} 数据质量提示：{', '.join(sorted(warnings_now))}。请先复核数据后再做人工判断。",
                reason="initial_quality_warning",
                category="data_quality",
                human_action="先复核日线数据质量；不自动交易。",
            ))
        return alerts
    prev_label = str(previous.get("last_label") or "")
    try:
        prev_score = float(previous.get("last_score") or 0.0)
    except Exception:
        prev_score = 0.0
    prev_warnings = previous.get("last_warnings_json") or []
    if isinstance(prev_warnings, str):
        try:
            prev_warnings = json.loads(prev_warnings)
        except Exception:
            prev_warnings = []
    warnings_before = {str(item) for item in prev_warnings}
    if prev_label and prev_label != label:
        alerts.append(build_alert_payload(
            alert_type="label_change",
            severity="warning",
            symbol=symbol,
            message=f"{symbol} 趋势标签由 {prev_label} 变为 {label}。请人工复盘趋势变化。",
            reason="trend_label_changed",
            category="trend_change",
            human_action="人工复盘趋势变化；不自动交易。",
        ))
    if abs(score - prev_score) >= threshold:
        direction = "上升" if score > prev_score else "下降"
        alerts.append(build_alert_payload(
            alert_type="score_change",
            severity="info",
            symbol=symbol,
            message=f"{symbol} 趋势分数{direction} {prev_score:.2f} -> {score:.2f}，达到阈值 {threshold:.2f}。请人工确认是否继续观察。",
            reason="trend_score_threshold_crossed",
            category="trend_change",
            human_action="人工确认趋势分数变化；不自动交易。",
        ))
    new_warnings = warnings_now - warnings_before
    if new_warnings:
        alerts.append(build_alert_payload(
            alert_type="quality_warning",
            severity="warning",
            symbol=symbol,
            message=f"{symbol} 新增数据质量提示：{', '.join(sorted(new_warnings))}。请先复核数据后再做人工判断。",
            reason="new_quality_warning",
            category="data_quality",
            human_action="先复核新增数据质量提示；不自动交易。",
        ))
    return alerts


def scan_monitor_config(
    config: dict,
    *,
    force: bool = False,
    trend_service,
    get_db_connection: DbFactory,
    insert_alert: InsertAlert,
) -> dict:
    user_id = int(config.get("user_id") or 1)
    name = str(config.get("name") or "default")[:80]
    symbols = symbols_from_value(config.get("symbols"))
    limit_bars = max(20, min(int(config.get("limit_bars") or 120), 500))
    threshold = max(0.0, min(float(config.get("score_change_threshold") or 8.0), 100.0))
    if not force and not bool(config.get("enabled")):
        return {"status": "skipped", "reason": "monitor_disabled", "scanned_count": 0, "alert_count": 0, "alerts": [], "items": []}
    alerts = []
    items = []
    with get_db_connection() as db:
        for symbol in symbols:
            report = trend_service.analyze_symbol(symbol=symbol, limit=limit_bars)
            cur = db.cursor()
            cur.execute(
                """
                SELECT id, last_label, last_score, last_latest_date, last_warnings_json, snapshot, last_scanned_at
                FROM qd_tw_stock_monitor_states
                WHERE user_id = ? AND monitor_name = ? AND symbol = ?
                """,
                (user_id, name, report.get("symbol") or symbol),
            )
            previous = cur.fetchone()
            cur.close()
            if report.get("ok"):
                planned_alerts = build_scan_alerts(report.get("symbol") or symbol, report, previous, threshold)
                for alert in planned_alerts:
                    alerts.append(insert_alert(
                        db,
                        user_id=user_id,
                        name=name,
                        symbol=report.get("symbol") or symbol,
                        alert_type=alert["type"],
                        severity=alert["severity"],
                        message=alert["message"],
                        snapshot=snapshot_with_alert_context(report, alert),
                    ))
                quality = report.get("quality") or {}
                trend = report.get("trend") or {}
                cur = db.cursor()
                cur.execute(
                    """
                    INSERT INTO qd_tw_stock_monitor_states
                        (user_id, monitor_name, symbol, last_label, last_score, last_latest_date,
                         last_warnings_json, snapshot, last_scanned_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?::jsonb, ?::jsonb, NOW())
                    ON CONFLICT (user_id, monitor_name, symbol) DO UPDATE SET
                        last_label = EXCLUDED.last_label,
                        last_score = EXCLUDED.last_score,
                        last_latest_date = EXCLUDED.last_latest_date,
                        last_warnings_json = EXCLUDED.last_warnings_json,
                        snapshot = EXCLUDED.snapshot,
                        last_scanned_at = NOW()
                    """,
                    (
                        user_id,
                        name,
                        report.get("symbol") or symbol,
                        trend.get("label") or "unknown",
                        float(trend.get("score") or 0.0),
                        quality.get("latest_date") or "",
                        json.dumps(quality.get("warnings") or []),
                        json.dumps(report),
                    ),
                )
                cur.close()
                insert_trend_history(db, user_id=user_id, name=name, symbol=report.get("symbol") or symbol, report=report)
            items.append(report)
        db.commit()
    return {
        "status": "scanned",
        "monitor_name": name,
        "scanned_count": len(items),
        "alert_count": len(alerts),
        "alerts": alerts,
        "items": items,
        "trading": {"orders_enabled": False, "note": "Backend monitor scan is research-only."},
    }


def write_scan_log(*, get_db_connection: DbFactory, trigger_source: str, status: str, result: dict | None = None, error: str = "", duration_ms: int = 0) -> None:
    result = result or {}
    try:
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                """
                INSERT INTO qd_tw_stock_monitor_scan_logs
                    (trigger_source, status, monitor_count, scanned_count, alert_count, error,
                     result_summary, duration_ms, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?::jsonb, ?, NOW())
                """,
                (
                    trigger_source[:40],
                    status[:20],
                    int(result.get("count") or 0),
                    int(result.get("total_scanned_count") or 0),
                    int(result.get("total_alert_count") or 0),
                    error[:4000],
                    json.dumps({"count": result.get("count", 0), "total_scanned_count": result.get("total_scanned_count", 0), "total_alert_count": result.get("total_alert_count", 0)}),
                    int(duration_ms or 0),
                ),
            )
            cur.close()
            db.commit()
    except Exception as exc:
        logger.warning(f"TWStock monitor scan log write failed: {exc}")


def summarize_scan_health(logs: list[dict]) -> dict:
    items = list(logs or [])
    total = len(items)
    success = sum(1 for item in items if str(item.get("status") or "").lower() == "success")
    failed = sum(1 for item in items if str(item.get("status") or "").lower() == "failed")
    scanned_count = sum(int(item.get("scanned_count") or 0) for item in items)
    alert_count = sum(int(item.get("alert_count") or 0) for item in items)
    durations = [int(item.get("duration_ms") or 0) for item in items if item.get("duration_ms") is not None]
    recent_failures = [
        {
            "id": item.get("id"),
            "trigger_source": item.get("trigger_source"),
            "error": str(item.get("error") or "")[:400],
            "created_at": item.get("created_at"),
        }
        for item in items
        if str(item.get("status") or "").lower() == "failed"
    ][:5]
    status = "unknown"
    if total:
        status = "healthy" if failed == 0 else ("degraded" if success > 0 else "failed")
    return {
        "status": status,
        "log_count": total,
        "success_count": success,
        "failed_count": failed,
        "success_rate": round(success / total, 4) if total else None,
        "total_scanned_count": scanned_count,
        "total_alert_count": alert_count,
        "avg_duration_ms": round(sum(durations) / len(durations), 2) if durations else None,
        "latest_status": str(items[0].get("status") or "") if items else "",
        "latest_created_at": items[0].get("created_at") if items else None,
        "recent_failures": recent_failures,
        "orders_enabled": False,
        "writes_production_data": False,
        "connects_to_broker": False,
    }


def run_scan_all(
    *,
    force: bool = False,
    trigger_source: str = "api",
    write_log: bool = True,
    trend_service,
    get_db_connection: DbFactory,
    insert_alert: InsertAlert,
) -> dict:
    start = time.monotonic()
    try:
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                """
                SELECT id, user_id, name, symbols_json, limit_bars, refresh_interval_sec,
                       score_change_threshold, enabled, notes, created_at, updated_at
                FROM qd_tw_stock_monitor_configs
                WHERE enabled = TRUE OR ? = TRUE
                ORDER BY user_id, name
                LIMIT 100
                """,
                (force,),
            )
            rows = cur.fetchall() or []
            cur.close()
        results = [
            scan_monitor_config(
                monitor_config_from_row(row, user_id=int(row.get("user_id") or 1), name=row.get("name") or "default"),
                force=force,
                trend_service=trend_service,
                get_db_connection=get_db_connection,
                insert_alert=insert_alert,
            )
            for row in rows
        ]
        result = {
            "count": len(results),
            "results": results,
            "total_scanned_count": sum(int(item.get("scanned_count") or 0) for item in results),
            "total_alert_count": sum(int(item.get("alert_count") or 0) for item in results),
            "trading": {"orders_enabled": False},
        }
        if write_log:
            write_scan_log(get_db_connection=get_db_connection, trigger_source=trigger_source, status="success", result=result, duration_ms=int((time.monotonic() - start) * 1000))
        return result
    except Exception as exc:
        if write_log:
            write_scan_log(get_db_connection=get_db_connection, trigger_source=trigger_source, status="failed", result={}, error=str(exc), duration_ms=int((time.monotonic() - start) * 1000))
        raise
