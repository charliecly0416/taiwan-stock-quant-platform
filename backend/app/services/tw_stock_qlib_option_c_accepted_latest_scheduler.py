"""Disabled-by-default Option C accepted latest scheduler skeleton.

This scheduler coordinates the existing dry-run scheduler/runner and the normal
publish service. It has no background loop in this phase and never refreshes
providers, mutates qlib data, or touches trading.
"""
from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from app.services.tw_stock_qlib_option_c import research_only_trading_flags
from app.services.tw_stock_qlib_option_c_normal_publish import QlibOptionCNormalPublishGate, option_c_normal_publish_gate
from app.services.tw_stock_qlib_option_c_ops import ASOF_RE, DEFAULT_OPS_ROOT, OptionCFileLock, utc_now
from app.services.tw_stock_qlib_option_c_scheduler import QlibOptionCDryRunScheduler, option_c_dry_run_scheduler

ACCEPTED_LATEST_SCHEDULER_MODE = "accepted-latest-scheduler-review"
DEFAULT_ACCEPTED_LATEST_SCHEDULER_ENABLED = False
ACCEPTED_LATEST_SCHEDULER_LOCK_FILENAME = "option_c_accepted_latest_scheduler.lock"


def _parse_bool(raw: Optional[str], *, default: bool = False) -> bool:
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class OptionCAcceptedLatestSchedulerConfig:
    enabled: bool = DEFAULT_ACCEPTED_LATEST_SCHEDULER_ENABLED
    mode: str = ACCEPTED_LATEST_SCHEDULER_MODE
    ops_root: Path = Path(DEFAULT_OPS_ROOT)
    lock_stale_seconds: int = 900

    @classmethod
    def from_env(cls) -> "OptionCAcceptedLatestSchedulerConfig":
        repo_root = Path(__file__).resolve().parents[3]
        return cls(
            enabled=_parse_bool(os.getenv("ENABLE_TW_QLIB_OPTION_C_ACCEPTED_LATEST_SCHEDULER"), default=False),
            mode=os.getenv("TW_QLIB_OPTION_C_ACCEPTED_LATEST_SCHEDULER_MODE") or ACCEPTED_LATEST_SCHEDULER_MODE,
            ops_root=Path(os.getenv("TW_OPTION_C_OPS_ROOT") or repo_root / DEFAULT_OPS_ROOT),
        )


class QlibOptionCAcceptedLatestScheduler:
    """Manual tick scheduler for accepted latest publishing; default disabled."""

    def __init__(
        self,
        config: Optional[OptionCAcceptedLatestSchedulerConfig] = None,
        *,
        dry_run_scheduler: Optional[QlibOptionCDryRunScheduler] = None,
        normal_publish_gate: Optional[QlibOptionCNormalPublishGate] = None,
    ) -> None:
        self.config = config or OptionCAcceptedLatestSchedulerConfig.from_env()
        self.dry_run_scheduler = dry_run_scheduler or option_c_dry_run_scheduler
        self.normal_publish_gate = normal_publish_gate or option_c_normal_publish_gate
        self.last_tick: Optional[Dict[str, Any]] = None
        self._lock = threading.Lock()

    def status(self) -> Dict[str, Any]:
        valid_mode = self.config.mode == ACCEPTED_LATEST_SCHEDULER_MODE
        enabled = bool(self.config.enabled and valid_mode)
        return {
            "ok": valid_mode,
            "enabled": enabled,
            "configured_enabled": bool(self.config.enabled),
            "mode": self.config.mode,
            "required_mode": ACCEPTED_LATEST_SCHEDULER_MODE,
            "auto_loop_started": False,
            "loop_enabled": False,
            "last_tick": self.last_tick,
            "dry_run_scheduler": self.dry_run_scheduler.status(),
            "normal_publish": self.normal_publish_gate.status(),
            "normal_signal_run": False,
            "latest_signal_updated": False,
            "accepted_artifact_generated": False,
            "refresh_triggered": False,
            "publish_triggered": False,
            "provider_mutation_triggered": False,
            "trading": research_only_trading_flags(),
        }

    def tick(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        errors = self._validate_tick_payload(payload)
        if errors:
            return self._blocked(errors[0])
        if not self.config.enabled:
            return self._blocked("ENABLE_TW_QLIB_OPTION_C_ACCEPTED_LATEST_SCHEDULER is false")
        if self.config.mode != ACCEPTED_LATEST_SCHEDULER_MODE:
            return self._blocked("mode must be accepted-latest-scheduler-review")
        if not self._lock.acquire(blocking=False):
            return self._blocked("accepted latest scheduler tick already running", status="conflict")
        job_id = self._scheduler_job_id(str(payload.get("asof") or "auto"))
        file_lock = OptionCFileLock(self.config.ops_root / ACCEPTED_LATEST_SCHEDULER_LOCK_FILENAME, stale_seconds=self.config.lock_stale_seconds)
        acquired = file_lock.acquire(job_id=job_id)
        if not acquired.get("ok"):
            self._lock.release()
            return self._blocked("another Option C ops job is already running", status="conflict")
        try:
            return self._run_tick(payload, job_id=job_id)
        finally:
            try:
                file_lock.release(job_id=job_id)
            finally:
                self._lock.release()

    def _run_tick(self, payload: Dict[str, Any], *, job_id: str) -> Dict[str, Any]:
        job_dir = self.config.ops_root / job_id
        job_path = job_dir / "job.json"
        job_dir.mkdir(parents=True, exist_ok=True)
        asof = str(payload.get("asof") or "")
        job: Dict[str, Any] = {
            "job_id": job_id,
            "type": "option_c_accepted_latest_scheduler_tick",
            "status": "running",
            "asof": asof or None,
            "started_at": utc_now(),
            "dry_run": None,
            "normal_publish": None,
            "latest_signal_updated": False,
            "normal_signal_run": False,
            "accepted_artifact_generated": False,
            "refresh_triggered": False,
            "publish_triggered": False,
            "provider_mutation_triggered": False,
            "trading": research_only_trading_flags(),
        }
        self._write_json(job_path, job)

        dry_payload = {"dry_run_only": True}
        if asof:
            dry_payload["asof"] = asof
        dry = self.dry_run_scheduler.tick(dry_payload)
        job["dry_run"] = self._summary(dry)
        resolved_asof = str(dry.get("asof") or dry.get("scheduler", {}).get("selected_asof") or asof or "")
        dry_run_job_id = str(dry.get("job_id") or "")
        if not dry.get("ok") or dry.get("status") != "dry_run_passed" or not dry_run_job_id:
            job.update({"status": "blocked_dry_run_failed", "finished_at": utc_now()})
            self._write_json(job_path, job)
            return self._result(job, ok=False, message="dry-run did not pass")

        normal_payload = {
            "asof": resolved_asof,
            "confirm_normal_publish": True,
            "dry_run_job_id": dry_run_job_id,
        }
        normal = self.normal_publish_gate.publish(normal_payload)
        job["normal_publish"] = self._summary(normal)
        job["normal_signal_run"] = bool(normal.get("normal_signal_run"))
        job["latest_signal_updated"] = bool(normal.get("latest_signal_updated"))
        job["accepted_artifact_generated"] = bool(normal.get("accepted_artifact_generated"))
        job["refresh_triggered"] = bool(normal.get("refresh_triggered"))
        job["publish_triggered"] = bool(normal.get("publish_triggered"))
        job["provider_mutation_triggered"] = bool(normal.get("provider_mutation_triggered"))
        job["finished_at"] = utc_now()
        if normal.get("ok") and normal.get("status") == "normal_publish_passed":
            job["status"] = "accepted_latest_scheduler_passed"
            self._write_json(job_path, job)
            return self._result(job, ok=True, message="accepted latest scheduler tick passed")
        job["status"] = "blocked_normal_publish_failed"
        self._write_json(job_path, job)
        return self._result(job, ok=False, message=str(normal.get("message") or "normal publish did not pass"))

    def _validate_tick_payload(self, payload: Dict[str, Any]) -> list[str]:
        if set(payload.keys()) != {"asof", "confirm_accepted_latest_scheduler"}:
            return ["request must contain only asof and confirm_accepted_latest_scheduler"]
        if payload.get("confirm_accepted_latest_scheduler") is not True:
            return ["confirm_accepted_latest_scheduler must be true"]
        asof = str(payload.get("asof") or "")
        if not ASOF_RE.match(asof):
            return ["asof must match YYYY-MM-DD"]
        try:
            datetime.strptime(asof, "%Y-%m-%d")
        except ValueError:
            return ["asof must be a valid calendar date"]
        return []

    def _scheduler_job_id(self, asof: str) -> str:
        clean = asof.replace("-", "") if asof and asof != "auto" else "auto"
        return f"option_c_accepted_latest_scheduler_{clean}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    def _blocked(self, message: str, *, status: str = "blocked") -> Dict[str, Any]:
        return {
            "ok": False,
            "status": status,
            "message": message,
            "normal_signal_run": False,
            "latest_signal_updated": False,
            "accepted_artifact_generated": False,
            "refresh_triggered": False,
            "publish_triggered": False,
            "provider_mutation_triggered": False,
            "scheduler": self.status(),
            "trading": research_only_trading_flags(),
        }

    def _result(self, job: Dict[str, Any], *, ok: bool, message: str) -> Dict[str, Any]:
        self.last_tick = dict(job)
        return {
            "ok": ok,
            "status": job.get("status"),
            "message": message,
            "scheduler_job_id": job.get("job_id"),
            "asof": job.get("asof"),
            "dry_run": job.get("dry_run"),
            "normal_publish": job.get("normal_publish"),
            "normal_signal_run": bool(job.get("normal_signal_run")),
            "latest_signal_updated": bool(job.get("latest_signal_updated")),
            "accepted_artifact_generated": bool(job.get("accepted_artifact_generated")),
            "refresh_triggered": bool(job.get("refresh_triggered")),
            "publish_triggered": bool(job.get("publish_triggered")),
            "provider_mutation_triggered": bool(job.get("provider_mutation_triggered")),
            "trading": research_only_trading_flags(),
            "scheduler": self.status(),
        }

    @staticmethod
    def _summary(payload: Dict[str, Any]) -> Dict[str, Any]:
        keys = [
            "ok",
            "status",
            "message",
            "job_id",
            "normal_publish_job_id",
            "dry_run_job_id",
            "asof",
            "normal_signal_run",
            "latest_signal_updated",
            "accepted_artifact_generated",
            "refresh_triggered",
            "publish_triggered",
            "provider_mutation_triggered",
        ]
        return {key: payload.get(key) for key in keys if key in payload}

    @staticmethod
    def _write_json(path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


option_c_accepted_latest_scheduler = QlibOptionCAcceptedLatestScheduler()
