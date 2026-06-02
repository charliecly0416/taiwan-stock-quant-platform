"""Disabled-by-default controlled EOD automation scheduler for Option C.

This layer decides whether a manual controlled scheduler tick is allowed to call
Phase 4 EOD pipeline. It has no background loop and never accepts provider paths
from API payloads.
"""
from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

from app.services.tw_stock_qlib_option_c import QlibOptionCSignalError, QlibOptionCSignalReader, research_only_trading_flags
from app.services.tw_stock_qlib_option_c_eod_pipeline import QlibOptionCEodPipeline, option_c_eod_pipeline
from app.services.tw_stock_qlib_option_c_ops import DEFAULT_OPS_ROOT, OptionCFileLock, utc_now

EOD_AUTOMATION_MODE = "controlled_scheduler_smoke"
DEFAULT_EOD_AUTOMATION_ENABLED = False
EOD_AUTOMATION_LOCK_FILENAME = "option_c_eod_automation.lock"
DEFAULT_PROVIDER_CALENDAR = "/home/chuliyang/qlib/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt"


def _parse_bool(raw: Optional[str], *, default: bool = False) -> bool:
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class OptionCEodAutomationConfig:
    enabled: bool = DEFAULT_EOD_AUTOMATION_ENABLED
    mode: str = EOD_AUTOMATION_MODE
    ops_root: Path = Path(DEFAULT_OPS_ROOT)
    provider_calendar: Path = Path(DEFAULT_PROVIDER_CALENDAR)
    timezone_name: str = "Asia/Taipei"
    market_close_time: str = "13:30"
    eod_window_start: str = "15:30"
    eod_window_end: str = "23:59"
    lock_stale_seconds: int = 900

    @classmethod
    def from_env(cls) -> "OptionCEodAutomationConfig":
        repo_root = Path(__file__).resolve().parents[3]
        return cls(
            enabled=_parse_bool(os.getenv("ENABLE_TW_QLIB_OPTION_C_EOD_AUTOMATION"), default=False),
            mode=os.getenv("TW_QLIB_OPTION_C_EOD_AUTOMATION_MODE") or EOD_AUTOMATION_MODE,
            ops_root=Path(os.getenv("TW_OPTION_C_OPS_ROOT") or repo_root / DEFAULT_OPS_ROOT),
            provider_calendar=Path(os.getenv("TW_QLIB_OPTION_C_PROVIDER_CALENDAR") or DEFAULT_PROVIDER_CALENDAR),
            timezone_name=os.getenv("TW_QLIB_OPTION_C_EOD_TZ") or "Asia/Taipei",
            market_close_time=os.getenv("TW_QLIB_OPTION_C_MARKET_CLOSE_TIME") or "13:30",
            eod_window_start=os.getenv("TW_QLIB_OPTION_C_EOD_WINDOW_START") or "15:30",
            eod_window_end=os.getenv("TW_QLIB_OPTION_C_EOD_WINDOW_END") or "23:59",
        )


class QlibOptionCEodAutomationScheduler:
    """Manual controlled scheduler; default disabled and no automatic loop."""

    def __init__(
        self,
        config: Optional[OptionCEodAutomationConfig] = None,
        *,
        pipeline: Optional[QlibOptionCEodPipeline] = None,
        signal_reader: Optional[QlibOptionCSignalReader] = None,
    ) -> None:
        self.config = config or OptionCEodAutomationConfig.from_env()
        self.pipeline = pipeline or option_c_eod_pipeline
        self.signal_reader = signal_reader or QlibOptionCSignalReader()
        self.last_tick: Optional[Dict[str, Any]] = None
        self._lock = threading.Lock()

    def status(self, *, now: Optional[str] = None) -> Dict[str, Any]:
        valid_mode = self.config.mode == EOD_AUTOMATION_MODE
        decision = self.plan(now=now)
        return {
            "ok": valid_mode,
            "enabled": bool(self.config.enabled and valid_mode),
            "configured_enabled": bool(self.config.enabled),
            "mode": self.config.mode,
            "required_mode": EOD_AUTOMATION_MODE,
            "auto_loop_started": False,
            "loop_enabled": False,
            "timezone": self.config.timezone_name,
            "market_close_time": self.config.market_close_time,
            "eod_window_start": self.config.eod_window_start,
            "eod_window_end": self.config.eod_window_end,
            "provider_calendar": str(self.config.provider_calendar),
            "plan": decision,
            "last_tick": self.last_tick,
            "refresh_triggered": False,
            "provider_mutation_triggered": False,
            "latest_signal_updated": False,
            "research_signal_not_order": True,
            "trading": research_only_trading_flags(),
        }

    def tick(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        errors = self._validate_payload(payload)
        if errors:
            return self._blocked(errors[0])
        if not self.config.enabled:
            return self._blocked("ENABLE_TW_QLIB_OPTION_C_EOD_AUTOMATION is false")
        if self.config.mode != EOD_AUTOMATION_MODE:
            return self._blocked("mode must be controlled_scheduler_smoke")
        if not self._lock.acquire(blocking=False):
            return self._blocked("EOD automation already running", status="conflict")
        now_raw = str(payload.get("now") or "")
        plan = self.plan(now=now_raw)
        job_id = self._job_id(str(plan.get("asof") or "none"))
        file_lock = OptionCFileLock(self.config.ops_root / EOD_AUTOMATION_LOCK_FILENAME, stale_seconds=self.config.lock_stale_seconds)
        acquired = file_lock.acquire(job_id=job_id)
        if not acquired.get("ok"):
            self._lock.release()
            return self._blocked("another Option C EOD automation job is already running", status="conflict")
        try:
            return self._run_tick(payload, plan=plan, job_id=job_id)
        finally:
            try:
                file_lock.release(job_id=job_id)
            finally:
                self._lock.release()

    def plan(self, *, now: Optional[str] = None) -> Dict[str, Any]:
        parsed = self._parse_now(now)
        if not parsed.get("ok"):
            return parsed
        local_now: datetime = parsed["now"]
        rows = self._calendar_rows()
        if not rows:
            return {"ok": False, "status": "market_closed_or_no_new_asof", "message": "provider calendar missing or empty", "now": local_now.isoformat()}
        market_date = local_now.date().isoformat()
        if market_date not in rows:
            return {"ok": False, "status": "market_closed_or_no_new_asof", "message": "market date is not in provider calendar", "now": local_now.isoformat(), "market_date": market_date}
        if not self._inside_eod_window(local_now):
            return {"ok": False, "status": "outside_eod_window", "message": "now is outside configured Asia/Taipei EOD window", "now": local_now.isoformat(), "market_date": market_date}
        target_date = self._next_trading_day(rows, market_date)
        latest = self._accepted_latest_for_asof(market_date)
        if latest.get("ok"):
            return {
                "ok": False,
                "status": "already_accepted_latest",
                "message": "accepted latest already exists for asof",
                "now": local_now.isoformat(),
                "asof": market_date,
                "market_date": market_date,
                "target_date": target_date,
                "latest_run_id": latest.get("run_id"),
                "signals_count": latest.get("signals_count"),
            }
        return {
            "ok": True,
            "status": "ready_to_run",
            "now": local_now.isoformat(),
            "asof": market_date,
            "market_date": market_date,
            "target_date": target_date,
            "target_horizon": "next_trading_day_research_ranking",
        }

    def _run_tick(self, payload: Dict[str, Any], *, plan: Dict[str, Any], job_id: str) -> Dict[str, Any]:
        job_dir = self.config.ops_root / job_id
        job_path = job_dir / "job.json"
        job_dir.mkdir(parents=True, exist_ok=True)
        job: Dict[str, Any] = {
            "job_id": job_id,
            "type": "option_c_eod_automation",
            "status": "running",
            "request": payload,
            "plan": plan,
            "started_at": utc_now(),
            "pipeline": None,
            "refresh_triggered": False,
            "provider_mutation_triggered": False,
            "latest_signal_updated": False,
            "research_signal_not_order": True,
            "trading": research_only_trading_flags(),
        }
        self._write_json(job_path, job)
        if not plan.get("ok"):
            job.update({"status": plan.get("status"), "message": plan.get("message"), "finished_at": utc_now()})
            self._write_json(job_path, job)
            return self._result(job, ok=False)
        pipeline = self.pipeline.tick({"asof": plan["asof"], "confirm_eod_pipeline": True, "mode": "controlled_smoke"})
        job["pipeline"] = pipeline
        job["refresh_triggered"] = bool(pipeline.get("refresh_triggered"))
        job["provider_mutation_triggered"] = bool(pipeline.get("provider_mutation_triggered"))
        job["latest_signal_updated"] = bool(pipeline.get("latest_signal_updated"))
        job["finished_at"] = utc_now()
        if pipeline.get("ok"):
            job["status"] = "eod_automation_pipeline_passed"
        else:
            job["status"] = str(pipeline.get("status") or "pipeline_blocked")
            job["message"] = pipeline.get("message") or job["status"]
        self._write_json(job_path, job)
        return self._result(job, ok=bool(pipeline.get("ok")))

    def _validate_payload(self, payload: Dict[str, Any]) -> list[str]:
        if set(payload.keys()) != {"confirm_eod_automation", "mode", "now"}:
            return ["request must contain only confirm_eod_automation, mode, and now"]
        if payload.get("confirm_eod_automation") is not True:
            return ["confirm_eod_automation must be true"]
        if payload.get("mode") != EOD_AUTOMATION_MODE:
            return ["mode must be controlled_scheduler_smoke"]
        if not str(payload.get("now") or "").strip():
            return ["now is required for controlled scheduler smoke"]
        return []

    def _result(self, job: Dict[str, Any], *, ok: bool) -> Dict[str, Any]:
        self.last_tick = dict(job)
        pipeline = job.get("pipeline") or {}
        plan = job.get("plan") or {}
        return {
            "ok": ok,
            "status": job.get("status"),
            "message": job.get("message"),
            "automation_job_id": job.get("job_id"),
            "pipeline_job_id": pipeline.get("pipeline_job_id"),
            "asof": plan.get("asof"),
            "market_date": plan.get("market_date"),
            "target_date": plan.get("target_date"),
            "target_horizon": "next_trading_day_research_ranking",
            "latest_run_id": pipeline.get("latest_run_id") or plan.get("latest_run_id"),
            "signals_count": pipeline.get("signals_count") or plan.get("signals_count"),
            "refresh_triggered": bool(job.get("refresh_triggered")),
            "provider_mutation_triggered": bool(job.get("provider_mutation_triggered")),
            "latest_signal_updated": bool(job.get("latest_signal_updated")),
            "research_signal_not_order": True,
            "trading": research_only_trading_flags(),
            "job_path": str(self.config.ops_root / str(job.get("job_id")) / "job.json"),
        }

    def _blocked(self, message: str, *, status: str = "blocked") -> Dict[str, Any]:
        return {
            "ok": False,
            "status": status,
            "message": message,
            "refresh_triggered": False,
            "provider_mutation_triggered": False,
            "latest_signal_updated": False,
            "research_signal_not_order": True,
            "trading": research_only_trading_flags(),
            "scheduler": self.status(),
        }

    def _parse_now(self, raw: Optional[str]) -> Dict[str, Any]:
        tz = ZoneInfo(self.config.timezone_name)
        if raw:
            try:
                dt = datetime.fromisoformat(str(raw))
            except ValueError:
                return {"ok": False, "status": "invalid_now", "message": "now must be ISO datetime"}
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tz)
            return {"ok": True, "status": "ok", "now": dt.astimezone(tz)}
        return {"ok": True, "status": "ok", "now": datetime.now(tz)}

    def _inside_eod_window(self, dt: datetime) -> bool:
        start = self._parse_time(self.config.eod_window_start)
        end = self._parse_time(self.config.eod_window_end)
        current = dt.time().replace(second=0, microsecond=0)
        return start <= current <= end

    @staticmethod
    def _parse_time(raw: str) -> time:
        hour, minute = str(raw).split(":", 1)
        return time(int(hour), int(minute))

    def _calendar_rows(self) -> list[str]:
        try:
            return [line.strip() for line in self.config.provider_calendar.read_text(encoding="utf-8").splitlines() if line.strip()]
        except Exception:
            return []

    @staticmethod
    def _next_trading_day(rows: list[str], asof: str) -> Optional[str]:
        for row in rows:
            if row > asof:
                return row
        return None

    def _accepted_latest_for_asof(self, asof: str) -> Dict[str, Any]:
        try:
            latest = self.signal_reader.latest(bucket="top30", enrich_trend=False)
        except QlibOptionCSignalError:
            return {"ok": False, "status": "latest_unavailable"}
        if latest.get("status") == "accepted" and latest.get("asof") == asof and len(latest.get("signals") or []) == 30:
            return {"ok": True, "status": "accepted", "run_id": latest.get("run_id"), "signals_count": 30}
        return {"ok": False, "status": "accepted_latest_not_for_asof", "latest_asof": latest.get("asof"), "run_id": latest.get("run_id")}

    def _job_id(self, asof: str) -> str:
        clean = asof.replace("-", "") if asof else "none"
        return f"option_c_eod_automation_{clean}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    @staticmethod
    def _write_json(path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


option_c_eod_automation_scheduler = QlibOptionCEodAutomationScheduler()
