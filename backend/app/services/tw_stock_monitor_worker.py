"""Optional background worker for TWStock monitor scans.

Research-only: this worker calls the TWStock monitor scan-all function and
only persists scan logs / alerts. It never creates orders or touches brokers.
"""
from __future__ import annotations

import os
import threading
import time

from app.utils.logger import get_logger

logger = get_logger(__name__)
_worker = None
_worker_lock = threading.Lock()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int, *, min_value: int = 1, max_value: int = 86400) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except Exception:
        value = default
    return max(min_value, min(max_value, value))


class TWStockMonitorWorker:
    def __init__(self, *, interval_sec: int = 900, force: bool = False) -> None:
        self.interval_sec = interval_sec
        self.force = force
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="TWStockMonitorWorker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def is_alive(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def _run(self) -> None:
        logger.info("TWStock monitor worker started: interval=%ss force=%s", self.interval_sec, self.force)
        while not self._stop_event.is_set():
            started = time.monotonic()
            try:
                from app.routes.tw_stock import run_tw_stock_monitor_scan_all

                # Compatibility wrapper delegates to app.services.tw_stock_monitor.
                result = run_tw_stock_monitor_scan_all(force=self.force, trigger_source="worker", write_log=True)
                logger.info(
                    "TWStock monitor worker scan OK: configs=%s scanned=%s alerts=%s",
                    result.get("count"),
                    result.get("total_scanned_count"),
                    result.get("total_alert_count"),
                )
            except Exception as exc:
                logger.warning("TWStock monitor worker scan failed: %s", exc, exc_info=True)
            elapsed = time.monotonic() - started
            wait_for = max(1.0, float(self.interval_sec) - elapsed)
            self._stop_event.wait(wait_for)
        logger.info("TWStock monitor worker stopped")


def start_tw_stock_monitor_worker():
    """Start optional TWStock monitor worker if enabled by env."""
    global _worker
    enabled = _env_bool("ENABLE_TW_STOCK_MONITOR_WORKER", False)
    if not enabled:
        logger.info("TWStock monitor worker is disabled. Set ENABLE_TW_STOCK_MONITOR_WORKER=true to enable.")
        return None
    debug = os.getenv("PYTHON_API_DEBUG", "false").lower() == "true"
    if debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return None
    interval_sec = _env_int("TW_STOCK_MONITOR_INTERVAL_SEC", 900, min_value=30, max_value=86400)
    force = _env_bool("TW_STOCK_MONITOR_FORCE_SCAN", False)
    with _worker_lock:
        if _worker and _worker.is_alive():
            return _worker
        _worker = TWStockMonitorWorker(interval_sec=interval_sec, force=force)
        _worker.start()
        return _worker
