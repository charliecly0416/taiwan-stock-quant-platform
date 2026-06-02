"""Disabled-by-default qlib Option C dry-run scheduler skeleton.

The scheduler has no background loop in this phase. Manual ticks are explicit
admin/ops smoke actions and can only call the existing dry-run runner.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

from app.services.tw_stock_qlib_option_c import research_only_trading_flags
from app.services.tw_stock_qlib_option_c_ops import ASOF_RE, QlibOptionCOpsRunner, option_c_ops_runner, utc_now

DEFAULT_SCHEDULER_ENABLED = False
DEFAULT_SCHEDULER_TIME = "18:30"
DEFAULT_SCHEDULER_TZ = "Asia/Taipei"
SCHEDULER_MODE = "dry-run-only"
DEFAULT_PROVIDER_CALENDAR = "/home/chuliyang/qlib/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt"


def _parse_bool(raw: Optional[str], *, default: bool = False) -> bool:
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class OptionCSchedulerConfig:
    enabled: bool = DEFAULT_SCHEDULER_ENABLED
    schedule_time: str = DEFAULT_SCHEDULER_TIME
    timezone: str = DEFAULT_SCHEDULER_TZ
    mode: str = SCHEDULER_MODE
    provider_calendar: Path = Path(DEFAULT_PROVIDER_CALENDAR)

    @classmethod
    def from_env(cls) -> "OptionCSchedulerConfig":
        return cls(
            enabled=_parse_bool(os.getenv("ENABLE_TW_QLIB_OPTION_C_SCHEDULER"), default=DEFAULT_SCHEDULER_ENABLED),
            schedule_time=os.getenv("TW_QLIB_OPTION_C_SCHEDULER_TIME") or DEFAULT_SCHEDULER_TIME,
            timezone=os.getenv("TW_QLIB_OPTION_C_SCHEDULER_TZ") or DEFAULT_SCHEDULER_TZ,
            mode=os.getenv("TW_QLIB_OPTION_C_SCHEDULER_MODE") or SCHEDULER_MODE,
            provider_calendar=Path(os.getenv("TW_QLIB_OPTION_C_PROVIDER_CALENDAR") or DEFAULT_PROVIDER_CALENDAR),
        )


class QlibOptionCDryRunScheduler:
    """Dry-run-only scheduler skeleton with no automatic runner thread."""

    def __init__(self, config: Optional[OptionCSchedulerConfig] = None, runner: Optional[QlibOptionCOpsRunner] = None) -> None:
        self.config = config or OptionCSchedulerConfig.from_env()
        self.runner = runner or option_c_ops_runner
        self.last_tick: Optional[Dict[str, Any]] = None
        self.last_job_id: Optional[str] = None

    def status(self) -> Dict[str, Any]:
        valid_mode = self.config.mode == SCHEDULER_MODE
        enabled = bool(self.config.enabled and valid_mode)
        asof_plan = self.select_asof(None)
        return {
            "ok": valid_mode,
            "enabled": enabled,
            "configured_enabled": bool(self.config.enabled),
            "mode": self.config.mode,
            "valid_mode": valid_mode,
            "schedule_time": self.config.schedule_time,
            "timezone": self.config.timezone,
            "provider_calendar": str(self.config.provider_calendar),
            "selected_asof": asof_plan.get("asof"),
            "asof_source": asof_plan.get("source"),
            "asof_status": asof_plan.get("status"),
            "asof_message": asof_plan.get("message"),
            "next_run_at": self._next_run_at() if enabled else None,
            "last_tick": self.last_tick,
            "last_job_id": self.last_job_id,
            "auto_loop_started": False,
            "dry_run_only": True,
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
            return self._blocked("blocked", errors[0])
        if self.config.mode != SCHEDULER_MODE:
            return self._blocked("blocked", "scheduler mode must be dry-run-only")
        asof_plan = self.select_asof(payload.get("asof"))
        if not asof_plan.get("ok"):
            return self._blocked("blocked", str(asof_plan.get("message") or "unable to select scheduler asof"))
        asof = str(asof_plan["asof"])
        tick_started_at = utc_now()
        result = self.runner.trigger_dry_run({"asof": asof})
        self.last_job_id = result.get("job_id")
        self.last_tick = {
            "asof": asof,
            "started_at": tick_started_at,
            "finished_at": utc_now(),
            "status": result.get("status"),
            "job_id": self.last_job_id,
            "ok": bool(result.get("ok")),
            "manual": True,
            "dry_run_only": True,
            "asof_source": asof_plan.get("source"),
        }
        data = dict(result)
        data["asof_source"] = asof_plan.get("source")
        data["scheduler"] = self.status()
        data["dry_run_only"] = True
        data["normal_signal_run"] = bool(data.get("normal_signal_run") is True)
        data["accepted_artifact_generated"] = bool(data.get("accepted_artifact_generated") is True)
        return data

    def _validate_tick_payload(self, payload: Dict[str, Any]) -> list[str]:
        allowed = {"asof", "dry_run_only"}
        if set(payload.keys()) - allowed:
            return ["request must contain only optional asof and dry_run_only"]
        if payload.get("dry_run_only") is not True:
            return ["dry_run_only must be true"]
        raw_asof = payload.get("asof")
        if raw_asof in (None, ""):
            return []
        asof = str(raw_asof)
        if not ASOF_RE.match(asof):
            return ["asof must match YYYY-MM-DD"]
        try:
            datetime.strptime(asof, "%Y-%m-%d")
        except ValueError:
            return ["asof must be a valid calendar date"]
        return []

    def select_asof(self, explicit_asof: Optional[str]) -> Dict[str, Any]:
        if explicit_asof:
            return {"ok": True, "status": "ok", "asof": str(explicit_asof), "source": "explicit"}
        try:
            tz = ZoneInfo(self.config.timezone)
            today = datetime.now(tz).date().isoformat()
        except Exception:
            today = datetime.utcnow().date().isoformat()
        if not self.config.provider_calendar.exists():
            return {"ok": False, "status": "blocked", "asof": None, "source": "provider_calendar", "message": "provider calendar not found"}
        rows = [line.strip() for line in self.config.provider_calendar.read_text(encoding="utf-8").splitlines() if line.strip()]
        candidates = [row for row in rows if row <= today]
        if not candidates:
            return {"ok": False, "status": "blocked", "asof": None, "source": "provider_calendar", "message": "provider calendar has no available date not later than Asia/Taipei today"}
        return {"ok": True, "status": "ok", "asof": max(candidates), "source": "provider_calendar"}

    def _next_run_at(self) -> Optional[str]:
        try:
            hour_raw, minute_raw = self.config.schedule_time.split(":", 1)
            hour = int(hour_raw)
            minute = int(minute_raw)
            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                return None
            tz = ZoneInfo(self.config.timezone)
            now = datetime.now(tz).replace(second=0, microsecond=0)
            candidate = now.replace(hour=hour, minute=minute)
            if candidate <= now:
                candidate = candidate + timedelta(days=1)
            return candidate.isoformat()
        except Exception:
            return None

    def _blocked(self, status: str, message: str) -> Dict[str, Any]:
        return {
            "ok": False,
            "status": status,
            "message": message,
            "dry_run_only": True,
            "normal_signal_run": False,
            "latest_signal_updated": False,
            "accepted_artifact_generated": False,
            "refresh_triggered": False,
            "publish_triggered": False,
            "provider_mutation_triggered": False,
            "trading": research_only_trading_flags(),
            "scheduler": self.status(),
        }


option_c_dry_run_scheduler = QlibOptionCDryRunScheduler()
