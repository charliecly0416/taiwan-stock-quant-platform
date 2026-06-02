"""Tests for optional TWStock monitor background worker."""
from __future__ import annotations

from app.services import tw_stock_monitor_worker as worker_mod


def test_worker_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ENABLE_TW_STOCK_MONITOR_WORKER", raising=False)

    worker = worker_mod.start_tw_stock_monitor_worker()

    assert worker is None


def test_worker_start_when_enabled(monkeypatch):
    created = []

    class FakeWorker:
        def __init__(self, *, interval_sec, force):
            self.interval_sec = interval_sec
            self.force = force
            self.started = False
            created.append(self)

        def start(self):
            self.started = True

        def is_alive(self):
            return self.started

    monkeypatch.setenv("ENABLE_TW_STOCK_MONITOR_WORKER", "true")
    monkeypatch.setenv("TW_STOCK_MONITOR_INTERVAL_SEC", "60")
    monkeypatch.setenv("TW_STOCK_MONITOR_FORCE_SCAN", "true")
    monkeypatch.setattr(worker_mod, "_worker", None)
    monkeypatch.setattr(worker_mod, "TWStockMonitorWorker", FakeWorker)

    worker = worker_mod.start_tw_stock_monitor_worker()

    assert worker is created[0]
    assert worker.started is True
    assert worker.interval_sec == 60
    assert worker.force is True
