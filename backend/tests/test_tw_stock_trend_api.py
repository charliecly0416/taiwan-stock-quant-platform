"""Tests for read-only TWStock trend API."""
from __future__ import annotations

from datetime import date, datetime, timezone, timedelta

from flask import Flask

from app.routes import tw_stock as tw_stock_route
from app.services.tw_stock_trend import TWStockTrendService


def _bars(count=80, *, start=100.0, step=1.0):
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = []
    for idx in range(count):
        close = start + idx * step
        rows.append({
            "time": int((base + timedelta(days=idx)).timestamp()),
            "open": close - 0.5,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": 1000 + idx * 10,
        })
    return rows


class FakeKlineService:
    def __init__(self, data):
        self.data = data
        self.calls = []

    def get_kline(self, market, symbol, timeframe, limit):
        self.calls.append((market, symbol, timeframe, limit))
        return list(self.data.get(symbol, []))[-limit:]


def _client(monkeypatch, data):
    app = Flask(__name__)
    tw_stock_route.trend_service = TWStockTrendService(FakeKlineService(data))
    app.register_blueprint(tw_stock_route.tw_stock_bp, url_prefix="/api/tw-stock")
    return app.test_client()


def test_trend_service_reports_uptrend_and_read_only_flags():
    service = TWStockTrendService(FakeKlineService({"2330": _bars(80, start=100, step=2)}))

    report = service.analyze_symbol(symbol="2330.TW", limit=80, as_of=date(2026, 3, 25))

    assert report["ok"] is True
    assert report["symbol"] == "2330"
    assert report["exchange"] == "TWSE"
    assert report["trend"]["label"] == "uptrend"
    assert report["trend"]["score"] > 50
    assert report["moving_averages"]["close_above_ma20"] is True
    assert report["trading"]["orders_enabled"] is False
    assert report["trading"]["signal"] == "none"




def test_trend_score_uses_smooth_components_without_easy_saturation():
    service = TWStockTrendService(FakeKlineService({
        "9901": _bars(120, start=100, step=3.0),
        "9902": _bars(120, start=100, step=0.0),
    }))

    strong = service.analyze_symbol(symbol="9901", limit=120, as_of=date(2026, 5, 15))
    flat = service.analyze_symbol(symbol="9902", limit=120, as_of=date(2026, 5, 15))

    assert strong["trend"]["label"] == "uptrend"
    assert 70 < strong["trend"]["score"] < 100
    assert abs(flat["trend"]["score"] - 50.0) < 1.0


def test_trend_service_flags_stale_data_and_short_history():
    service = TWStockTrendService(FakeKlineService({"0050": _bars(25, start=50, step=0)}))

    report = service.analyze_symbol(symbol="0050", limit=25, as_of=date(2026, 5, 1))

    assert report["ok"] is True
    assert "stale_daily_bar" in report["quality"]["warnings"]
    assert "short_history_below_60_bars" in report["quality"]["warnings"]


def test_trend_api_returns_single_symbol_report(monkeypatch):
    client = _client(monkeypatch, {"2330": _bars(80, start=100, step=1.5)})

    resp = client.get("/api/tw-stock/trend?symbol=2330&limit=80&as_of=2026-03-25")

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 1
    assert body["data"]["symbol"] == "2330"
    assert body["data"]["trading"]["orders_enabled"] is False


def test_trend_api_requires_symbol(monkeypatch):
    client = _client(monkeypatch, {})

    resp = client.get("/api/tw-stock/trend")

    assert resp.status_code == 400
    assert resp.get_json()["msg"] == "Missing symbol parameter"


def test_trends_api_returns_rankings(monkeypatch):
    client = _client(monkeypatch, {
        "2330": _bars(80, start=100, step=2),
        "0050": _bars(80, start=100, step=0.2),
    })

    resp = client.get("/api/tw-stock/trends?symbols=2330,0050&limit=80&as_of=2026-03-25")

    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["count"] == 2
    assert data["ok_count"] == 2
    assert data["rankings"][0]["symbol"] == "2330"
    assert data["trading"]["orders_enabled"] is False


def test_trends_api_rejects_empty_watchlist(monkeypatch):
    client = _client(monkeypatch, {})

    resp = client.get("/api/tw-stock/trends")

    assert resp.status_code == 400
    assert resp.get_json()["msg"] == "Missing symbols parameter"


def test_monitor_page_is_read_only_and_loads_trends_endpoint(monkeypatch):
    client = _client(monkeypatch, {"2330": _bars(80, start=100, step=1.5)})

    resp = client.get("/api/tw-stock/monitor")

    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "台股趨勢監控" in html
    assert "/api/tw-stock/trends" in html
    assert "orders_enabled" not in html
    assert "下單" in html
    assert "fetch(`/api/tw-stock/trends" in html
    assert "啟動監控" in html
    assert "後端掃描" in html
    assert "/api/tw-stock/monitor/scan" in html
    assert "趨勢分數曲線" in html
    assert "trendChart" in html
    assert "/api/tw-stock/monitor/history?symbol=" in html
    assert "提醒與人工備註" in html
    assert "alertFilter" in html
    assert 'data-status="watch"' in html
    assert 'data-status="ignored"' in html
    assert 'data-status="acted"' in html



class _MonitorCursor:
    def __init__(self, store):
        self.store = store
        self.row = None
        self.rows = []

    def execute(self, sql, params=None):
        params = params or ()
        sql_up = " ".join(sql.upper().split())
        if sql_up.startswith("SELECT ID, USER_ID, NAME, SYMBOLS_JSON") and "WHERE USER_ID =" in sql_up:
            key = (params[0], params[1])
            self.row = self.store["configs"].get(key)
        elif sql_up.startswith("INSERT INTO QD_TW_STOCK_MONITOR_CONFIGS"):
            user_id, name, symbols_json, limit_bars, interval, threshold, enabled, notes = params
            row = {
                "id": 1,
                "user_id": user_id,
                "name": name,
                "symbols_json": symbols_json,
                "limit_bars": limit_bars,
                "refresh_interval_sec": interval,
                "score_change_threshold": threshold,
                "enabled": enabled,
                "notes": notes,
                "created_at": "2026-05-24T00:00:00Z",
                "updated_at": "2026-05-24T00:00:00Z",
            }
            self.store["configs"][(user_id, name)] = row
            self.row = row
        elif sql_up.startswith("INSERT INTO QD_TW_STOCK_MONITOR_ALERTS"):
            user_id, name, symbol, alert_type, severity, message, snapshot = params
            row = {
                "id": len(self.store["alerts"]) + 1,
                "user_id": user_id,
                "monitor_name": name,
                "symbol": symbol,
                "alert_type": alert_type,
                "severity": severity,
                "message": message,
                "snapshot": snapshot,
                "is_read": False,
                "decision_status": "pending",
                "user_note": "",
                "created_at": "2026-05-24T00:00:00Z",
                "acknowledged_at": None,
            }
            self.store["alerts"].append(row)
            self.row = row
        elif sql_up.startswith("SAVEPOINT") or sql_up.startswith("RELEASE SAVEPOINT") or sql_up.startswith("ROLLBACK TO SAVEPOINT"):
            self.row = None
        elif sql_up.startswith("INSERT INTO QD_STRATEGY_NOTIFICATIONS"):
            user_id, symbol, signal_type, title, message, payload_json = params
            self.store.setdefault("notifications", []).append({
                "id": len(self.store.setdefault("notifications", [])) + 1,
                "user_id": user_id,
                "strategy_id": None,
                "symbol": symbol,
                "signal_type": signal_type,
                "channels": "browser",
                "title": title,
                "message": message,
                "payload_json": payload_json,
                "is_read": 0,
                "created_at": "2026-05-24T00:00:00Z",
            })
            self.row = None
        elif sql_up.startswith("SELECT ID, LAST_LABEL"):
            self.row = self.store.get("states", {}).get((params[0], params[1], params[2]))
        elif sql_up.startswith("INSERT INTO QD_TW_STOCK_MONITOR_STATES"):
            user_id, name, symbol, label, score, latest_date, warnings_json, snapshot = params
            self.store.setdefault("states", {})[(user_id, name, symbol)] = {
                "id": 1,
                "last_label": label,
                "last_score": score,
                "last_latest_date": latest_date,
                "last_warnings_json": warnings_json,
                "snapshot": snapshot,
                "last_scanned_at": "2026-05-24T00:00:00Z",
            }
            self.row = None
        elif sql_up.startswith("INSERT INTO QD_TW_STOCK_TREND_HISTORY"):
            user_id, name, symbol, label, score, latest_date, latest_close, warnings_json, snapshot = params
            rows = self.store.setdefault("trend_history", [])
            rows.append({
                "id": len(rows) + 1,
                "user_id": user_id,
                "monitor_name": name,
                "symbol": symbol,
                "label": label,
                "score": score,
                "latest_date": latest_date,
                "latest_close": latest_close,
                "warnings_json": warnings_json,
                "snapshot": snapshot,
                "scanned_at": f"2026-05-24T00:{len(rows):02d}:00Z",
            })
            self.row = None
        elif sql_up.startswith("INSERT INTO QD_TW_STOCK_MONITOR_SCAN_LOGS"):
            trigger_source, status, monitor_count, scanned_count, alert_count, error, result_summary, duration_ms = params
            self.store.setdefault("scan_logs", []).append({
                "id": len(self.store.setdefault("scan_logs", [])) + 1,
                "trigger_source": trigger_source,
                "status": status,
                "monitor_count": monitor_count,
                "scanned_count": scanned_count,
                "alert_count": alert_count,
                "error": error,
                "result_summary": result_summary,
                "duration_ms": duration_ms,
                "created_at": "2026-05-24T00:02:00Z",
            })
            self.row = None
        elif "FROM QD_TW_STOCK_MONITOR_SCAN_LOGS" in sql_up and sql_up.startswith("SELECT"):
            self.rows = list(reversed(self.store.setdefault("scan_logs", [])))[: params[0]]
        elif "FROM QD_TW_STOCK_TREND_HISTORY" in sql_up and sql_up.startswith("SELECT"):
            user_id, name, symbol, limit = params
            rows = [
                row for row in self.store.setdefault("trend_history", [])
                if row["user_id"] == user_id and row["monitor_name"] == name and row["symbol"] == symbol
            ]
            rows.sort(key=lambda row: (row["scanned_at"], row["id"]), reverse=True)
            self.rows = rows[:limit]
        elif "FROM QD_TW_STOCK_MONITOR_CONFIGS" in sql_up and "WHERE ENABLED = TRUE" in sql_up:
            force = bool(params[0])
            self.rows = [row for row in self.store["configs"].values() if row.get("enabled") or force]
        elif "FROM QD_TW_STOCK_MONITOR_ALERTS" in sql_up and sql_up.startswith("SELECT"):
            user_id, name = params[0], params[1]
            self.rows = [r for r in self.store["alerts"] if r["user_id"] == user_id and r["monitor_name"] == name]
        elif sql_up.startswith("UPDATE QD_TW_STOCK_MONITOR_ALERTS"):
            is_read, decision_status, user_note, _is_read_again, alert_id, user_id = params
            self.row = None
            for row in self.store["alerts"]:
                if row["id"] == alert_id and row["user_id"] == user_id:
                    row["is_read"] = is_read
                    row["decision_status"] = decision_status
                    row["user_note"] = user_note
                    row["acknowledged_at"] = "2026-05-24T00:01:00Z" if is_read else None
                    self.row = row
                    break
        else:
            raise AssertionError(sql)

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows

    def close(self):
        pass


class _MonitorConn:
    def __init__(self, store):
        self.store = store

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return _MonitorCursor(self.store)

    def commit(self):
        pass


def test_monitor_config_api_roundtrip(monkeypatch):
    store = {"configs": {}, "alerts": [], "notifications": []}
    monkeypatch.setattr(tw_stock_route, "get_db_connection", lambda: _MonitorConn(store))
    client = _client(monkeypatch, {})

    resp = client.post("/api/tw-stock/monitor/config", json={
        "symbols": ["2330", "0050"],
        "limit_bars": 80,
        "refresh_interval_sec": 300,
        "score_change_threshold": 7,
        "enabled": True,
    })

    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["symbols"] == ["2330", "0050"]
    assert data["enabled"] is True

    resp = client.get("/api/tw-stock/monitor/config")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["limit_bars"] == 80


def test_monitor_alert_api_create_list_and_ack(monkeypatch):
    store = {"configs": {}, "alerts": [], "notifications": []}
    monkeypatch.setattr(tw_stock_route, "get_db_connection", lambda: _MonitorConn(store))
    client = _client(monkeypatch, {})

    resp = client.post("/api/tw-stock/monitor/alerts", json={
        "symbol": "2330",
        "alert_type": "score_change",
        "message": "2330 分數變化 80 -> 90",
        "snapshot": {"trend": {"score": 90}},
    })

    assert resp.status_code == 200
    alert_id = resp.get_json()["data"]["id"]
    assert resp.get_json()["data"]["is_read"] is False
    assert len(store["notifications"]) == 1
    notification = store["notifications"][0]
    assert notification["signal_type"] == "tw_stock_monitor"
    assert notification["channels"] == "browser"
    assert notification["title"] == "台股趋势提醒"
    assert notification["symbol"] == "2330"
    assert "2330 分數變化" in notification["message"]

    resp = client.get("/api/tw-stock/monitor/alerts?limit=5")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["count"] == 1

    resp = client.put(f"/api/tw-stock/monitor/alerts/{alert_id}", json={"is_read": True, "decision_status": "watch", "user_note": "人工观察"})
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["is_read"] is True
    assert data["decision_status"] == "watch"
    assert data["user_note"] == "人工观察"



def test_monitor_scan_builds_baseline_then_alerts_on_score_change(monkeypatch):
    store = {"configs": {}, "alerts": [], "states": {}, "notifications": [], "trend_history": []}
    monkeypatch.setattr(tw_stock_route, "get_db_connection", lambda: _MonitorConn(store))
    client = _client(monkeypatch, {"2330": _bars(144, start=100, step=0.0)})

    resp = client.post("/api/tw-stock/monitor/config", json={
        "symbols": ["2330"],
        "limit_bars": 120,
        "score_change_threshold": 5,
        "enabled": True,
    })
    assert resp.status_code == 200

    resp = client.post("/api/tw-stock/monitor/scan")
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["status"] == "scanned"
    assert data["alert_count"] == 0
    assert data["trading"]["orders_enabled"] is False
    assert len(store["trend_history"]) == 1
    assert store["trend_history"][0]["symbol"] == "2330"

    tw_stock_route.trend_service = TWStockTrendService(FakeKlineService({"2330": _bars(144, start=100, step=3.0)}))
    resp = client.post("/api/tw-stock/monitor/scan")
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["alert_count"] >= 1
    assert any(item["alert_type"] == "score_change" for item in data["alerts"])
    assert len(store["notifications"]) == data["alert_count"]
    assert store["notifications"][0]["signal_type"] == "tw_stock_monitor"
    assert len(store["trend_history"]) == 2

    resp = client.get("/api/tw-stock/monitor/history?symbol=2330&limit=10")
    assert resp.status_code == 200
    history = resp.get_json()["data"]
    assert history["symbol"] == "2330"
    assert history["count"] == 2
    assert history["items"][0]["id"] == 1
    assert history["items"][1]["id"] == 2
    assert history["trading"]["orders_enabled"] is False


def test_monitor_history_requires_symbol(monkeypatch):
    store = {"configs": {}, "alerts": [], "states": {}, "trend_history": []}
    monkeypatch.setattr(tw_stock_route, "get_db_connection", lambda: _MonitorConn(store))
    client = _client(monkeypatch, {})

    resp = client.get("/api/tw-stock/monitor/history")

    assert resp.status_code == 400
    assert resp.get_json()["msg"] == "Missing symbol parameter"


def test_monitor_scan_skips_disabled_config(monkeypatch):
    store = {"configs": {}, "alerts": [], "states": {}}
    monkeypatch.setattr(tw_stock_route, "get_db_connection", lambda: _MonitorConn(store))
    client = _client(monkeypatch, {"2330": _bars(80, start=100, step=1.0)})

    client.post("/api/tw-stock/monitor/config", json={"symbols": ["2330"], "enabled": False})
    resp = client.post("/api/tw-stock/monitor/scan")

    assert resp.status_code == 200
    assert resp.get_json()["data"]["status"] == "skipped"
    assert resp.get_json()["data"]["reason"] == "monitor_disabled"



def test_monitor_scan_all_writes_scan_log(monkeypatch):
    store = {"configs": {}, "alerts": [], "states": {}, "scan_logs": []}
    monkeypatch.setattr(tw_stock_route, "get_db_connection", lambda: _MonitorConn(store))
    client = _client(monkeypatch, {"2330": _bars(144, start=100, step=0.0)})

    client.post("/api/tw-stock/monitor/config", json={"symbols": ["2330"], "enabled": True})
    resp = client.post("/api/tw-stock/monitor/scan-all")

    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["count"] == 1
    assert data["total_scanned_count"] == 1
    assert data["trading"]["orders_enabled"] is False
    assert store["scan_logs"][0]["trigger_source"] == "api"
    assert store["scan_logs"][0]["status"] == "success"

    resp = client.get("/api/tw-stock/monitor/scan-logs?limit=5")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["count"] == 1

def test_monitor_alert_webhook_disabled_by_default(monkeypatch):
    calls = []
    monkeypatch.delenv("TW_STOCK_MONITOR_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("TW_STOCK_MONITOR_WEBHOOK_ENABLED", raising=False)
    monkeypatch.setattr(tw_stock_route, "_load_monitor_webhook_targets", lambda user_id: {})
    monkeypatch.setattr(tw_stock_route, "_build_monitor_alert_webhook_payload", lambda alert: calls.append(alert) or {})

    tw_stock_route._try_send_monitor_alert_webhook(alert={"user_id": 1, "symbol": "2330", "message": "noop"})

    assert calls == []


def test_monitor_alert_webhook_sends_research_only_payload(monkeypatch):
    calls = []

    class FakeNotifier:
        def _notify_webhook(self, **kwargs):
            calls.append(kwargs)
            return True, ""

    monkeypatch.setattr(tw_stock_route, "_load_monitor_webhook_targets", lambda user_id: {
        "url": "https://example.test/hook",
        "headers": {"X-Test": "1"},
        "token": "token",
        "signing_secret": "secret",
    })
    monkeypatch.setattr("app.services.signal_notifier.SignalNotifier", lambda: FakeNotifier())

    alert = {
        "id": 9,
        "user_id": 1,
        "monitor_name": "default",
        "symbol": "2330",
        "alert_type": "score_change",
        "severity": "warning",
        "message": "2330 分數變化 70 -> 82",
        "snapshot": {
            "trend": {"label": "uptrend", "score": 82.4},
            "latest": {"date": "2026-05-22", "close": 900.0},
        },
    }

    tw_stock_route._try_send_monitor_alert_webhook(alert=alert)

    assert len(calls) == 1
    call = calls[0]
    assert call["url"] == "https://example.test/hook"
    assert call["headers_override"] == {"X-Test": "1"}
    assert call["token_override"] == "token"
    assert call["signing_secret_override"] == "secret"
    payload = call["payload"]
    assert payload["source"] == "tw_stock_monitor"
    assert payload["event"] == "tw_stock_monitor_alert"
    assert payload["symbol"] == "2330"
    assert payload["trend"]["score"] == 82.4
    assert payload["trading"]["orders_enabled"] is False

