"""Tests for TWStock monitor config import script."""
from __future__ import annotations

import json
from pathlib import Path

from scripts import import_tw_stock_monitor_config as importer


SAMPLE_CONFIG = Path(__file__).resolve().parents[2] / "docs" / "examples" / "tw_stock_monitor_conservative_sample.json"


class _Cursor:
    def __init__(self):
        self.sql = []
        self.params = []
        self.row = None

    def execute(self, sql, params=None):
        self.sql.append(" ".join(sql.split()))
        self.params.append(params or ())
        user_id, name, symbols_json, limit_bars, interval, threshold, enabled, notes = params
        self.row = {
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

    def fetchone(self):
        return self.row

    def close(self):
        pass


class _Conn:
    def __init__(self, cursor):
        self.cursor_obj = cursor
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.committed = True


def test_normalize_config_dedupes_and_defaults_disabled():
    payload = {"name": "phase7c", "symbols": ["2330", "2330.TW", "TWSE:0050"], "limit_bars": 999}

    config = importer.normalize_config(payload, user_id=3)

    assert config["user_id"] == 3
    assert config["name"] == "phase7c"
    assert config["symbols"] == ["2330", "0050"]
    assert config["limit_bars"] == 500
    assert config["enabled"] is False


def test_conservative_sample_config_is_research_only():
    payload = json.loads(SAMPLE_CONFIG.read_text(encoding="utf-8"))

    config = importer.normalize_config(payload, user_id=1)

    assert config["name"] == "tw_conservative_research_watchlist"
    assert config["symbols"] == ["2330", "2317", "2454", "0050", "0056", "00878"]
    assert config["limit_bars"] == 120
    assert config["refresh_interval_sec"] == 900
    assert config["score_change_threshold"] == 8.0
    assert config["enabled"] is False
    assert "manual review" in config["notes"]
    assert "no automatic trading" in config["notes"]
    assert "no broker connection" in config["notes"]


def test_import_monitor_config_dry_run_does_not_write(monkeypatch, tmp_path):
    path = tmp_path / "monitor.json"
    path.write_text(json.dumps({"symbols": ["2330", "0050"], "enabled": True}), encoding="utf-8")
    called = []
    monkeypatch.setattr(importer, "upsert_monitor_config", lambda config: called.append(config) or config)

    report = importer.import_monitor_config(path=path, user_id=1, apply=False)

    assert report["apply"] is False
    assert report["symbol_count"] == 2
    assert report["orders_enabled"] is False
    assert report["scanned"] is False
    assert report["alerts_created"] == 0
    assert called == []


def test_import_monitor_config_apply_upserts(monkeypatch, tmp_path):
    path = tmp_path / "monitor.json"
    path.write_text(json.dumps({"name": "phase7c", "symbols": ["2330"], "enabled": False}), encoding="utf-8")
    cur = _Cursor()
    conn = _Conn(cur)
    monkeypatch.setattr(importer, "get_db_connection", lambda: conn)

    report = importer.import_monitor_config(path=path, user_id=2, enabled=True, apply=True)

    assert report["apply"] is True
    assert report["saved"]["user_id"] == 2
    assert report["saved"]["name"] == "phase7c"
    assert report["saved"]["symbols"] == ["2330"]
    assert report["saved"]["enabled"] is True
    assert conn.committed is True
    assert "INSERT INTO qd_tw_stock_monitor_configs" in cur.sql[0]


def test_cli_prints_json(monkeypatch, tmp_path, capsys):
    path = tmp_path / "monitor.json"
    path.write_text(json.dumps({"symbols": ["2330"]}), encoding="utf-8")
    monkeypatch.setattr(importer, "import_monitor_config", lambda **kwargs: {"apply": kwargs["apply"], "orders_enabled": False})

    rc = importer.main(["--input-json", str(path), "--apply", "--dry-run"])

    assert rc == 0
    assert json.loads(capsys.readouterr().out) == {"apply": False, "orders_enabled": False}
