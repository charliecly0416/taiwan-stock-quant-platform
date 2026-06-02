"""Tests for qlib/TWStock cross-analysis signal history import."""
from __future__ import annotations

from app.services.tw_stock_cross_analysis_history import TWStockCrossAnalysisHistoryService
from app.services.tw_stock_qlib_option_c import QlibOptionCSignalError, research_only_trading_flags


RECORDER = "950741cfd5f14ee5a05464fec3e12e0a"


def _row(rank: int, *, bucket: str, symbol: str | None = None) -> dict:
    clean = symbol or str(8000 + rank)
    return {
        "asof": "2026-06-03",
        "instrument": f"TW{clean}",
        "symbol": clean,
        "qlib_score": 0.2 - rank / 1000,
        "rank": rank,
        "bucket": bucket,
        "source_model_recorder": RECORDER,
        "diagnostic_only": True,
        "research_signal_not_order": True,
    }


def _payload(*, asof: str = "2026-06-03", run_id: str = "option_c_daily_signal_20260603_20260604T090000Z", research: bool = True) -> dict:
    # Shape current run to trigger new entry, rank up/down, dropped_from_top30 and consecutive alerts.
    top30 = [_row(rank, bucket="top30") for rank in range(1, 31)]
    top30[0].update({"symbol": "2330", "instrument": "TW2330", "rank": 1})
    top30[1].update({"symbol": "2454", "instrument": "TW2454", "rank": 2})
    top30[2].update({"symbol": "2317", "instrument": "TW2317", "rank": 3})
    top50 = [_row(rank, bucket="top50") for rank in range(1, 51)]
    top50[0].update({"symbol": "2330", "instrument": "TW2330", "rank": 1})
    top50[1].update({"symbol": "2454", "instrument": "TW2454", "rank": 2})
    top50[2].update({"symbol": "2317", "instrument": "TW2317", "rank": 3})
    top50[30].update({"symbol": "9999", "instrument": "TW9999", "rank": 31})
    for rows in (top30, top50):
        for row in rows:
            row["asof"] = asof
    return {
        "ok": True,
        "status": "accepted",
        "asof": asof,
        "run_id": run_id,
        "recorder_id": RECORDER,
        "source": {"run_dir": run_id},
        "summary": {
            "status": "accepted",
            "prediction_rows": 150,
            "top30_rows": 30,
            "top50_rows": 50,
            "finite_prediction_share": 1.0,
            "diagnostic_only": True,
            "research_signal_not_order": research,
        },
        "metadata": {"status": "accepted", "provider_uri": "fixture", "config": "fixture.yaml"},
        "top30": top30,
        "top50": top50,
        "trading": {**research_only_trading_flags(), "research_signal_not_order": research},
    }


class FakeReader:
    def __init__(self, payload=None, error=None):
        self.payload = payload or _payload()
        self.error = error
        self.calls = []

    def latest(self, *, bucket="top30", enrich_trend=False):
        self.calls.append((bucket, enrich_trend))
        if self.error:
            raise self.error
        return self.payload


class FakeCrossService:
    def latest(self, **kwargs):
        return {
            "ok": True,
            "items": [
                {"symbol": "2454", "quantdinger": {"trend_label": "pullback"}, "cross": {"category": "model_trend_divergence"}},
                {"symbol": "2317", "quantdinger": {"trend_label": "uptrend"}, "cross": {"category": "data_review_required"}},
            ],
        }


class FakeCursor:
    def __init__(self, db):
        self.db = db
        self.result = []

    def execute(self, sql, params=None):
        params = tuple(params or ())
        compact = " ".join(str(sql).split())
        self.db.sql.append(compact)
        if compact.startswith("CREATE TABLE"):
            self.result = []
        elif "SELECT run_id, asof, instrument, symbol, bucket, rank, score FROM qd_tw_qlib_signals WHERE asof =" in compact:
            asof = str(params[0])
            prev_dates = sorted({row["asof"] for row in self.db.signals.values() if row["asof"] < asof})
            latest = prev_dates[-1] if prev_dates else None
            self.result = [dict(row) for row in self.db.signals.values() if row["asof"] == latest]
        elif "SELECT asof, symbol, bucket FROM qd_tw_qlib_signals WHERE asof IN" in compact:
            asof = str(params[0])
            limit = int(params[1])
            dates = sorted({row["asof"] for row in self.db.signals.values() if row["asof"] < asof}, reverse=True)[:limit]
            self.result = [{"asof": row["asof"], "symbol": row["symbol"], "bucket": row["bucket"]} for row in self.db.signals.values() if row["asof"] in dates]
        elif compact.startswith("INSERT INTO qd_tw_qlib_signal_runs"):
            run_id = params[0]
            self.db.runs[run_id] = {"run_id": run_id, "asof": params[1], "status": params[2], "prediction_rows": params[8], "top30_rows": params[9], "top50_rows": params[10], "diagnostic_only": True, "research_signal_not_order": True}
        elif compact.startswith("INSERT INTO qd_tw_qlib_signals"):
            key = (params[0], params[4], params[2])
            asof_key = (params[1], params[4], params[2])
            if key not in self.db.signals and asof_key not in self.db.signal_asof_keys:
                self.db.signals[key] = {"run_id": params[0], "asof": params[1], "instrument": params[2], "symbol": params[3], "bucket": params[4], "rank": params[5], "score": params[6], "research_signal_not_order": True}
                self.db.signal_asof_keys.add(asof_key)
        elif compact.startswith("INSERT INTO qd_tw_qlib_signal_alerts"):
            key = (params[0], params[2], params[4])
            if key not in self.db.alerts:
                self.db.alerts[key] = {"run_id": params[0], "asof": params[1], "symbol": params[2], "instrument": params[3], "alert_type": params[4], "old_rank": params[5], "new_rank": params[6], "old_bucket": params[7], "new_bucket": params[8], "message": params[9], "human_action": params[10], "research_signal_not_order": True}
        elif "FROM qd_tw_qlib_signal_runs" in compact:
            self.result = list(self.db.runs.values())
        elif "FROM qd_tw_qlib_signal_alerts" in compact:
            self.result = list(self.db.alerts.values())
        elif "FROM qd_tw_qlib_signals" in compact:
            self.result = list(self.db.signals.values())
        else:
            self.result = []

    def fetchall(self):
        return self.result

    def close(self):
        pass


class FakeDb:
    def __init__(self):
        self.runs = {}
        self.signals = {}
        self.signal_asof_keys = set()
        self.alerts = {}
        self.sql = []
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1


def _seed_previous(db: FakeDb, asof: str = "2026-06-02"):
    previous = [
        {"symbol": "2330", "instrument": "TW2330", "bucket": "top30", "rank": 20},
        {"symbol": "2454", "instrument": "TW2454", "bucket": "top30", "rank": 1},
        {"symbol": "9999", "instrument": "TW9999", "bucket": "top30", "rank": 10},
        {"symbol": "2330", "instrument": "TW2330", "bucket": "top50", "rank": 20},
        {"symbol": "2454", "instrument": "TW2454", "bucket": "top50", "rank": 1},
        {"symbol": "2317", "instrument": "TW2317", "bucket": "top50", "rank": 30},
        {"symbol": "9999", "instrument": "TW9999", "bucket": "top50", "rank": 10},
    ]
    for row in previous:
        key = (f"prev-{asof}", row["bucket"], row["instrument"])
        db.signals[key] = {"run_id": f"prev-{asof}", "asof": asof, "score": 0.1, "research_signal_not_order": True, **row}
        db.signal_asof_keys.add((asof, row["bucket"], row["instrument"]))


def _service(db, reader=None):
    return TWStockCrossAnalysisHistoryService(qlib_reader=reader or FakeReader(), cross_service=FakeCrossService(), db_factory=lambda: db)


def test_import_latest_requires_confirm_gate():
    db = FakeDb()
    result = _service(db).import_latest(confirm_import_qlib_signal_history=False)

    assert result["ok"] is False
    assert result["status"] == "confirm_required"
    assert db.runs == {}


def test_accepted_latest_import_is_idempotent_and_counts_signals():
    db = FakeDb()
    _seed_previous(db, "2026-06-01")
    _seed_previous(db, "2026-06-02")
    service = _service(db)

    first = service.import_latest(confirm_import_qlib_signal_history=True)
    second = service.import_latest(confirm_import_qlib_signal_history=True)

    assert first["ok"] is True
    assert second["ok"] is True
    assert first["signals"]["top30"] == 30
    assert first["signals"]["top50"] == 50
    current_rows = [row for row in db.signals.values() if row["asof"] == "2026-06-03"]
    assert len(current_rows) == 80
    assert len(db.runs) == 1
    assert len(db.alerts) == len({(key[0], key[1], key[2]) for key in db.alerts})


def test_blocked_or_non_accepted_runs_are_not_imported():
    db = FakeDb()
    blocked_reader = FakeReader(error=QlibOptionCSignalError("blocked_validation_failed", "fixture blocked"))
    non_accepted = _payload()
    non_accepted["status"] = "wait_state"

    blocked = _service(db, blocked_reader).import_latest(confirm_import_qlib_signal_history=True)
    wait = _service(db, FakeReader(non_accepted)).import_latest(confirm_import_qlib_signal_history=True)

    assert blocked["ok"] is False
    assert blocked["status"] == "blocked_validation_failed"
    assert wait["ok"] is False
    assert wait["status"] == "import_blocked"
    assert db.runs == {}


def test_research_signal_not_order_false_is_not_imported():
    db = FakeDb()
    result = _service(db, FakeReader(_payload(research=False))).import_latest(confirm_import_qlib_signal_history=True)

    assert result["ok"] is False
    assert "research_signal_not_order" in result["failed_checks"]
    assert db.signals == {}


def test_alert_rules_include_required_changes_and_no_trade_action():
    db = FakeDb()
    _seed_previous(db, "2026-06-01")
    _seed_previous(db, "2026-06-02")

    result = _service(db).import_latest(confirm_import_qlib_signal_history=True)
    types = {item["alert_type"] for item in result["alerts"]["items"]}

    assert {"new_top30_entry", "rank_up", "rank_down", "dropped_from_top30", "consecutive_top30", "qlib_top30_trend_turn_weak", "qlib_top30_data_warning"}.issubset(types)
    for alert in result["alerts"]["items"]:
        assert alert["human_action"] == "人工复盘，不自动交易"
        assert alert["research_signal_not_order"] is True
        assert "买入" not in alert["message"]
        assert "下单" not in alert["message"]


def test_history_read_apis_return_research_only_rows():
    db = FakeDb()
    _service(db).import_latest(confirm_import_qlib_signal_history=True)
    service = _service(db)

    runs = service.runs(limit=5)
    signals = service.signals(bucket="top30", limit=5)
    alerts = service.alerts(limit=5)

    assert runs["count"] >= 1
    assert signals["count"] >= 1
    assert alerts["trading"]["orders_enabled"] is False
    assert all(item["research_signal_not_order"] is True for item in alerts["items"])


def test_history_api_confirm_gate_and_query_contract(client, monkeypatch):
    class FakeHistoryService:
        def __init__(self):
            self.import_calls = []

        def import_latest(self, *, confirm_import_qlib_signal_history):
            self.import_calls.append(confirm_import_qlib_signal_history)
            if not confirm_import_qlib_signal_history:
                return {"ok": False, "status": "confirm_required", "message": "confirm required", "trading": research_only_trading_flags()}
            return {"ok": True, "status": "imported", "trading": research_only_trading_flags()}

        def runs(self, *, limit=20):
            return {"ok": True, "items": [{"run_id": "r1"}], "count": 1, "trading": research_only_trading_flags()}

        def signals(self, **kwargs):
            return {"ok": True, "items": [{"symbol": "2330"}], "count": 1, "trading": research_only_trading_flags()}

        def alerts(self, **kwargs):
            return {"ok": True, "items": [{"alert_type": "new_top30_entry", "human_action": "人工复盘，不自动交易"}], "count": 1, "trading": research_only_trading_flags()}

    fake = FakeHistoryService()
    from app.routes import tw_stock as tw_stock_route

    from app import utils as app_utils

    monkeypatch.setattr(tw_stock_route, "cross_analysis_history_service", fake)
    anonymous = client.post("/api/tw-stock/cross-analysis/history/import-latest", json={})
    monkeypatch.setattr(app_utils.auth, "verify_token", lambda _raw: {"sub": "tester", "user_id": 7, "role": "user"})
    denied = client.post("/api/tw-stock/cross-analysis/history/import-latest", json={}, headers={"Authorization": "Bearer user-token"})
    monkeypatch.setattr(app_utils.auth, "verify_token", lambda _raw: {"sub": "admin", "user_id": 1, "role": "admin"})
    confirm_missing = client.post("/api/tw-stock/cross-analysis/history/import-latest", json={}, headers={"Authorization": "Bearer admin-token"})
    accepted = client.post("/api/tw-stock/cross-analysis/history/import-latest", json={"confirm_import_qlib_signal_history": True}, headers={"Authorization": "Bearer admin-token"})
    runs = client.get("/api/tw-stock/cross-analysis/history/runs?limit=3")
    signals = client.get("/api/tw-stock/cross-analysis/history/signals?bucket=top30&symbol=2330")
    alerts = client.get("/api/tw-stock/cross-analysis/history/alerts?alertType=new_top30_entry")

    assert anonymous.status_code == 401
    assert denied.status_code == 403
    assert confirm_missing.status_code == 400
    assert confirm_missing.get_json()["data"]["status"] == "confirm_required"
    assert accepted.status_code == 200
    assert runs.get_json()["data"]["items"][0]["run_id"] == "r1"
    assert signals.get_json()["data"]["items"][0]["symbol"] == "2330"
    assert alerts.get_json()["data"]["items"][0]["human_action"] == "人工复盘，不自动交易"
    assert fake.import_calls == [False, True]


def test_history_module_does_not_reference_ops_or_trading_execution_terms():
    import pathlib

    text = pathlib.Path("app/services/tw_stock_cross_analysis_history.py").read_text(encoding="utf-8").lower()
    banned = ["refresh", "publish", "provider mutation", "quick_trade", "broker", "live_trading_started", "target_position"]

    assert all(term not in text for term in banned)
