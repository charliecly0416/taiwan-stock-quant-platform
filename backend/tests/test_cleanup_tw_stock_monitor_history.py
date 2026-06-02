"""Tests for TWStock monitor history cleanup script."""
from __future__ import annotations

import json

from scripts import cleanup_tw_stock_monitor_history as cleanup


class _Cursor:
    def __init__(self, counts):
        self.counts = list(counts)
        self.sql = []
        self.params = []
        self.row = None
        self.rowcount = 0

    def execute(self, sql, params=None):
        self.sql.append(" ".join(sql.split()))
        self.params.append(params or ())
        if sql.strip().upper().startswith("SELECT COUNT"):
            self.row = {"cnt": self.counts.pop(0)}
        elif sql.strip().upper().startswith("DELETE"):
            self.rowcount += 3

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


def test_cleanup_dry_run_counts_without_deleting(monkeypatch):
    cur = _Cursor([11, 2])
    conn = _Conn(cur)
    monkeypatch.setattr(cleanup, "get_db_connection", lambda: conn)

    report = cleanup.cleanup_monitor_history(trend_retention_days=365, scan_log_retention_days=90, apply=False)

    assert report["apply"] is False
    assert report["trend_old_count"] == 11
    assert report["scan_log_old_count"] == 2
    assert report["trend_deleted"] == 0
    assert report["scan_log_deleted"] == 0
    assert report["orders_enabled"] is False
    assert conn.committed is False
    assert len([sql for sql in cur.sql if sql.startswith("DELETE")]) == 0


def test_cleanup_apply_deletes_and_commits(monkeypatch):
    cur = _Cursor([5, 4])
    conn = _Conn(cur)
    monkeypatch.setattr(cleanup, "get_db_connection", lambda: conn)

    report = cleanup.cleanup_monitor_history(trend_retention_days=30, scan_log_retention_days=7, apply=True)

    assert report["apply"] is True
    assert report["trend_deleted"] == 3
    assert report["scan_log_deleted"] == 6
    assert conn.committed is True
    assert len([sql for sql in cur.sql if sql.startswith("DELETE")]) == 2
    assert cur.params[0] == (30,)
    assert cur.params[1] == (7,)


def test_cleanup_cli_prints_json(monkeypatch, capsys):
    monkeypatch.setattr(cleanup, "cleanup_monitor_history", lambda **kwargs: {"apply": kwargs["apply"], "orders_enabled": False})

    rc = cleanup.main(["--apply", "--dry-run"])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"apply": False, "orders_enabled": False}
