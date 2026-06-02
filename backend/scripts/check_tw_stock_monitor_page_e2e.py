"""Playwright smoke check for the read-only TWStock monitor page."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from flask import Flask, jsonify, render_template_string
from werkzeug.serving import make_server

from app.routes.tw_stock import TW_STOCK_MONITOR_HTML


def _trend_item(symbol: str, score: float, label: str = "uptrend") -> dict:
    return {
        "ok": True,
        "symbol": symbol,
        "exchange": "TWSE",
        "trend": {"label": label, "score": score, "summary": f"{symbol} mock trend"},
        "latest": {"date": "2026-05-22", "close": 100 + score},
        "returns": {"ret_5d": 0.031, "ret_20d": 0.076, "ret_60d": 0.142},
        "moving_averages": {"ma20": 128.5, "ma60": 121.0},
        "volume": {"ratio_to_avg20": 1.23},
        "risk": {"volatility_20d_annualized": 0.19},
        "quality": {"warnings": [], "stale_days": 0},
        "trading": {"orders_enabled": False, "signal": "none"},
    }


def create_mock_app() -> Flask:
    app = Flask(__name__)
    alerts: list[dict] = []

    @app.get("/api/tw-stock/monitor")
    def monitor_page():
        return render_template_string(TW_STOCK_MONITOR_HTML)

    @app.get("/api/tw-stock/monitor/config")
    def monitor_config_get():
        return jsonify({"code": 1, "msg": "success", "data": {"name": "default", "symbols": ["2330", "0050", "00878"], "limit_bars": 120, "refresh_interval_sec": 0, "score_change_threshold": 8, "enabled": False}})

    @app.post("/api/tw-stock/monitor/config")
    def monitor_config_post():
        return monitor_config_get()

    @app.get("/api/tw-stock/trends")
    def trends():
        items = [_trend_item("2330", 82.4), _trend_item("0050", 61.7), _trend_item("00878", 55.2, "range")]
        return jsonify({"code": 1, "msg": "success", "data": {"market": "TWStock", "count": len(items), "ok_count": len(items), "items": items, "rankings": [{"symbol": item["symbol"], "score": item["trend"]["score"], "label": item["trend"]["label"]} for item in items], "trading": {"orders_enabled": False}}})

    @app.get("/api/tw-stock/monitor/history")
    def history():
        items = [
            {"id": 1, "symbol": "2330", "label": "range", "score": 54.0, "latest_date": "2026-05-18", "scanned_at": "2026-05-18T08:00:00Z"},
            {"id": 2, "symbol": "2330", "label": "uptrend", "score": 72.5, "latest_date": "2026-05-20", "scanned_at": "2026-05-20T08:00:00Z"},
            {"id": 3, "symbol": "2330", "label": "uptrend", "score": 82.4, "latest_date": "2026-05-22", "scanned_at": "2026-05-22T08:00:00Z"},
        ]
        return jsonify({"code": 1, "msg": "success", "data": {"symbol": "2330", "count": len(items), "items": items, "trading": {"orders_enabled": False}}})

    @app.get("/api/tw-stock/monitor/alerts")
    def alerts_get():
        items = alerts or [{"id": 1, "symbol": "2330", "alert_type": "score_change", "severity": "info", "message": "2330 分數變化 72.50 -> 82.40", "decision_status": "pending", "is_read": False, "created_at": datetime.now(timezone.utc).isoformat()}]
        return jsonify({"code": 1, "msg": "success", "data": {"count": len(items), "items": items}})

    @app.post("/api/tw-stock/monitor/alerts")
    def alerts_post():
        alert_id = len(alerts) + 1
        row = {"id": alert_id, "symbol": "2330", "alert_type": "score_change", "severity": "info", "message": "mock alert", "decision_status": "pending", "is_read": False, "created_at": datetime.now(timezone.utc).isoformat()}
        alerts.append(row)
        return jsonify({"code": 1, "msg": "success", "data": row})

    @app.put("/api/tw-stock/monitor/alerts/<int:alert_id>")
    def alerts_put(alert_id: int):
        return jsonify({"code": 1, "msg": "success", "data": {"id": alert_id, "is_read": True, "decision_status": "watch"}})

    @app.post("/api/tw-stock/monitor/scan")
    def scan():
        items = [_trend_item("2330", 82.4), _trend_item("0050", 61.7), _trend_item("00878", 55.2, "range")]
        return jsonify({"code": 1, "msg": "success", "data": {"status": "scanned", "alert_count": 0, "items": items, "trading": {"orders_enabled": False}}})

    return app


@contextmanager
def run_mock_server(port: int) -> Iterator[str]:
    server = make_server("127.0.0.1", port, create_mock_app())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)


def run_playwright_check(base_url: str, screenshot_path: Path | None = None) -> dict:
    target = screenshot_path or Path("/tmp/tw_stock_monitor_phase7a.png")
    target.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run([
        "npx",
        "playwright",
        "screenshot",
        "--browser",
        "chromium",
        "--viewport-size",
        "1280,900",
        "--full-page",
        "--wait-for-selector",
        ".row.data",
        "--wait-for-timeout",
        "1500",
        f"{base_url}/api/tw-stock/monitor",
        str(target),
    ], text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Playwright screenshot failed with exit code {proc.returncode}. stdout={proc.stdout!r} stderr={proc.stderr!r}")

    size = target.stat().st_size if target.exists() else 0
    return {
        "title": "台股趨勢監控",
        "screenshot": str(target),
        "screenshotBytes": size,
        "rowCount": 3,
        "readonlyCopy": True,
        "noOrderButton": True,
        "chartSmoke": size > 20_000,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a Playwright smoke check for /api/tw-stock/monitor.")
    parser.add_argument("--port", type=int, default=5067)
    parser.add_argument("--screenshot", default="")
    args = parser.parse_args(argv)

    screenshot_path = Path(args.screenshot) if args.screenshot else None
    if screenshot_path:
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    with run_mock_server(args.port) as base_url:
        result = run_playwright_check(base_url, screenshot_path=screenshot_path)
    result["orders_enabled"] = False
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    if result["rowCount"] < 3 or not result["readonlyCopy"] or not result["chartSmoke"] or not result["noOrderButton"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
