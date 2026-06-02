"""Disabled-by-default Option C EOD refresh and research signal pipeline.

The pipeline coordinates qlib-side Yahoo-only staged refresh, reviewed formal
publish, and the Phase 3 accepted latest scheduler. It never accepts provider
paths from API payloads and has no background loop in this phase.
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
QLIB_PIPELINE_ROOT = REPO_ROOT / "qlib_pipeline"
from typing import Any, Dict, Optional

from app.services.tw_stock_qlib_option_c import QlibOptionCSignalReader, research_only_trading_flags
from app.services.tw_stock_qlib_option_c_accepted_latest_scheduler import (
    QlibOptionCAcceptedLatestScheduler,
    option_c_accepted_latest_scheduler,
)
from app.services.tw_stock_qlib_option_c_ops import ASOF_RE, DEFAULT_OPS_ROOT, OptionCFileLock, utc_now

EOD_PIPELINE_MODE = "controlled_smoke"
DEFAULT_EOD_PIPELINE_ENABLED = False
EOD_PIPELINE_LOCK_FILENAME = "option_c_eod_pipeline.lock"
DEFAULT_QLIB_CWD = str(QLIB_PIPELINE_ROOT)
REFRESH_SCRIPT = "examples/tw/run_option_c_yahoo_scrapling_refresh.py"
PUBLISH_SCRIPT = "examples/tw/publish_option_c_yahoo_scrapling_refresh.py"
DEFAULT_PROVIDER_CALENDAR = str(QLIB_PIPELINE_ROOT / "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt")


def _parse_bool(raw: Optional[str], *, default: bool = False) -> bool:
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class OptionCEodPipelineConfig:
    enabled: bool = DEFAULT_EOD_PIPELINE_ENABLED
    mode: str = EOD_PIPELINE_MODE
    ops_root: Path = Path(DEFAULT_OPS_ROOT)
    qlib_cwd: Path = Path(DEFAULT_QLIB_CWD)
    provider_calendar: Path = Path(DEFAULT_PROVIDER_CALENDAR)
    refresh_script: str = REFRESH_SCRIPT
    publish_script: str = PUBLISH_SCRIPT
    timeout_seconds: int = 900
    lock_stale_seconds: int = 1020
    refresh_start: str = "2015-01-01"
    refresh_max_workers: int = 4
    refresh_sleep_seconds: float = 1.0
    refresh_timeout: float = 30.0
    refresh_retries: int = 1
    refresh_proxy: str = "http://127.0.0.1:7890"
    publish_max_workers: int = 4

    @classmethod
    def from_env(cls) -> "OptionCEodPipelineConfig":
        repo_root = Path(__file__).resolve().parents[3]
        return cls(
            enabled=_parse_bool(os.getenv("ENABLE_TW_QLIB_OPTION_C_EOD_PIPELINE"), default=False),
            mode=os.getenv("TW_QLIB_OPTION_C_EOD_PIPELINE_MODE") or EOD_PIPELINE_MODE,
            ops_root=Path(os.getenv("TW_OPTION_C_OPS_ROOT") or repo_root / DEFAULT_OPS_ROOT),
            qlib_cwd=Path(os.getenv("TW_QLIB_OPTION_C_CWD") or DEFAULT_QLIB_CWD),
            provider_calendar=Path(os.getenv("TW_QLIB_OPTION_C_PROVIDER_CALENDAR") or DEFAULT_PROVIDER_CALENDAR),
            timeout_seconds=int(os.getenv("TW_QLIB_OPTION_C_EOD_TIMEOUT_SECONDS") or 900),
            refresh_sleep_seconds=float(os.getenv("TW_QLIB_OPTION_C_REFRESH_SLEEP_SECONDS") or 1.0),
            refresh_timeout=float(os.getenv("TW_QLIB_OPTION_C_REFRESH_TIMEOUT") or 30.0),
            refresh_retries=int(os.getenv("TW_QLIB_OPTION_C_REFRESH_RETRIES") or 1),
            refresh_proxy=cls._proxy_from_env(os.getenv("TW_QLIB_OPTION_C_REFRESH_PROXY")),
        )

    @staticmethod
    def _proxy_from_env(raw: Optional[str]) -> str:
        if raw is None:
            return "http://127.0.0.1:7890"
        value = str(raw).strip()
        if value.lower() in {"none", "off", "disabled"}:
            return ""
        return value


class QlibOptionCEodPipeline:
    """Manual EOD pipeline tick; default disabled and no automatic loop."""

    def __init__(
        self,
        config: Optional[OptionCEodPipelineConfig] = None,
        *,
        accepted_latest_scheduler: Optional[QlibOptionCAcceptedLatestScheduler] = None,
        signal_reader: Optional[QlibOptionCSignalReader] = None,
    ) -> None:
        self.config = config or OptionCEodPipelineConfig.from_env()
        self.accepted_latest_scheduler = accepted_latest_scheduler or option_c_accepted_latest_scheduler
        self.signal_reader = signal_reader or QlibOptionCSignalReader()
        self.last_tick: Optional[Dict[str, Any]] = None
        self._lock = threading.Lock()

    def status(self) -> Dict[str, Any]:
        valid_mode = self.config.mode == EOD_PIPELINE_MODE
        return {
            "ok": valid_mode,
            "enabled": bool(self.config.enabled and valid_mode),
            "configured_enabled": bool(self.config.enabled),
            "mode": self.config.mode,
            "required_mode": EOD_PIPELINE_MODE,
            "auto_loop_started": False,
            "loop_enabled": False,
            "data_source_policy": "Yahoo-only Scrapling chart API",
            "universe": "option_c_accepted_150",
            "provider_scope": "option_c_150",
            "provider_calendar": str(self.config.provider_calendar),
            "selected_asof": self.select_asof(None).get("asof"),
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
            return self._blocked("ENABLE_TW_QLIB_OPTION_C_EOD_PIPELINE is false")
        if self.config.mode != EOD_PIPELINE_MODE:
            return self._blocked("mode must be controlled_smoke")
        if not self._lock.acquire(blocking=False):
            return self._blocked("EOD pipeline already running", status="conflict")
        asof_plan = self.select_asof(str(payload.get("asof") or ""))
        if not asof_plan.get("ok"):
            self._lock.release()
            return self._blocked(str(asof_plan.get("message") or asof_plan.get("status") or "unable to select asof"), status=str(asof_plan.get("status") or "blocked"))
        asof = str(asof_plan["asof"])
        job_id = self._job_id(asof)
        file_lock = OptionCFileLock(self.config.ops_root / EOD_PIPELINE_LOCK_FILENAME, stale_seconds=self.config.lock_stale_seconds)
        acquired = file_lock.acquire(job_id=job_id)
        if not acquired.get("ok"):
            self._lock.release()
            return self._blocked("another Option C EOD pipeline job is already running", status="conflict")
        try:
            return self._run_tick(dict(payload), asof=asof, asof_plan=asof_plan, job_id=job_id)
        finally:
            try:
                file_lock.release(job_id=job_id)
            finally:
                self._lock.release()

    def _run_tick(self, request_payload: Dict[str, Any], *, asof: str, asof_plan: Dict[str, Any], job_id: str) -> Dict[str, Any]:
        job_dir = self.config.ops_root / job_id
        job_dir.mkdir(parents=True, exist_ok=False)
        job_path = job_dir / "job.json"
        job: Dict[str, Any] = {
            "job_id": job_id,
            "type": "option_c_eod_pipeline",
            "status": "running",
            "request": request_payload,
            "asof": asof,
            "selected_asof": asof_plan,
            "started_at": utc_now(),
            "env_config": self._config_snapshot(),
            "data_source_policy": "Yahoo-only Scrapling chart API",
            "universe": "option_c_accepted_150",
            "provider_scope": "option_c_150",
            "refresh_triggered": False,
            "provider_mutation_triggered": False,
            "latest_signal_updated": False,
            "research_signal_not_order": True,
            "trading": research_only_trading_flags(),
        }
        self._write_json(job_path, job)

        refresh_job_id = f"option_c_yahoo_scrapling_refresh_{asof.replace('-', '')}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_eod"
        refresh_report = job_dir / "refresh_report.md"
        refresh_argv = self.fixed_refresh_argv(asof, refresh_job_id=refresh_job_id, report_path=refresh_report)
        job["candidate_refresh_job_id"] = refresh_job_id
        job["refresh"] = self._run_subprocess(refresh_argv, job_dir / "refresh_stdout.txt", job_dir / "refresh_stderr.txt")
        job["refresh_triggered"] = True
        job["fixed_refresh_argv"] = refresh_argv
        refresh_summary = self._read_json_if_exists(self.config.qlib_cwd / "data_tw/experiments/option_c_ops" / refresh_job_id / "reports/execution_summary.json")
        job["candidate_refresh_report"] = refresh_summary or {"status": "missing"}
        self._write_json(job_path, job)
        if not job["refresh"].get("ok") or refresh_summary.get("status") != "staged_refresh_complete_waiting_for_review":
            job.update({"status": "fresh_data_wait", "message": "candidate refresh did not produce reviewed staged data", "finished_at": utc_now()})
            self._write_json(job_path, job)
            return self._result(job, ok=False)

        publish_job_id = f"option_c_yahoo_scrapling_publish_{asof.replace('-', '')}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_eod"
        publish_report = job_dir / "publish_report.md"
        staged_job_dir = f"data_tw/experiments/option_c_ops/{refresh_job_id}"
        publish_argv = self.fixed_publish_argv(asof, staged_job_dir=staged_job_dir, publish_job_id=publish_job_id, report_path=publish_report)
        job["formal_publish_job_id"] = publish_job_id
        job["fixed_publish_argv"] = publish_argv
        job["formal_publish"] = self._run_subprocess(publish_argv, job_dir / "publish_stdout.txt", job_dir / "publish_stderr.txt")
        job["provider_mutation_triggered"] = True
        publish_summary = self._read_json_if_exists(self.config.qlib_cwd / "data_tw/experiments/option_c_ops" / publish_job_id / "reports/publish_execution_summary.json")
        job["formal_publish_report"] = publish_summary or {"status": "missing"}
        self._write_json(job_path, job)
        if not job["formal_publish"].get("ok") or publish_summary.get("status") != "publish_complete_waiting_for_review":
            job.update({"status": "formal_publish_failed", "message": "formal publish did not pass; qlib publish script owns backup/rollback metadata", "finished_at": utc_now()})
            self._write_json(job_path, job)
            return self._result(job, ok=False)

        accepted = self.accepted_latest_scheduler.tick({"asof": asof, "confirm_accepted_latest_scheduler": True})
        job["accepted_latest_scheduler"] = accepted
        job["accepted_latest_scheduler_job_id"] = accepted.get("scheduler_job_id")
        job["latest_signal_updated"] = bool(accepted.get("latest_signal_updated"))
        self._write_json(job_path, job)
        if not accepted.get("ok") or accepted.get("status") != "accepted_latest_scheduler_passed":
            job.update({
                "status": "accepted_latest_scheduler_blocked",
                "message": "formal provider retained after publish; accepted latest did not update",
                "finished_at": utc_now(),
            })
            self._write_json(job_path, job)
            return self._result(job, ok=False)

        reader = self._reader_smoke()
        job["latest_reader_smoke"] = reader
        job["latest_run_id"] = reader.get("run_id")
        job["signals_count"] = reader.get("signals_count")
        job.update({"status": "eod_pipeline_passed", "finished_at": utc_now()})
        self._write_json(job_path, job)
        return self._result(job, ok=True)

    def fixed_refresh_argv(self, asof: str, *, refresh_job_id: str, report_path: Path) -> list[str]:
        argv = [
            "python",
            self.config.refresh_script,
            "--asof",
            asof,
            "--start",
            self.config.refresh_start,
            "--universe",
            "option_c_accepted_150",
            "--output-root",
            "data_tw/experiments/option_c_ops",
            "--job-id",
            refresh_job_id,
            "--timeout",
            str(self.config.refresh_timeout),
            "--retries",
            str(self.config.refresh_retries),
            "--sleep-seconds",
            str(self.config.refresh_sleep_seconds),
            "--continue-on-error",
            "--suffix",
            "auto",
            "--max-workers",
            str(self.config.refresh_max_workers),
            "--report-path",
            str(report_path),
        ]
        proxy = str(self.config.refresh_proxy or "").strip()
        if proxy.lower() in {"none", "off", "disabled"}:
            proxy = ""
        if proxy:
            timeout_index = argv.index("--timeout")
            argv[timeout_index:timeout_index] = ["--proxy", proxy]
        return argv

    def fixed_publish_argv(self, asof: str, *, staged_job_dir: str, publish_job_id: str, report_path: Path) -> list[str]:
        return [
            "python",
            self.config.publish_script,
            "--job-dir",
            staged_job_dir,
            "--asof",
            asof,
            "--mode",
            "publish",
            "--provider-scope",
            "option_c_150",
            "--publish-job-id",
            publish_job_id,
            "--max-workers",
            str(self.config.publish_max_workers),
            "--report-path",
            str(report_path),
        ]

    def select_asof(self, explicit_asof: Optional[str]) -> Dict[str, Any]:
        if explicit_asof:
            return {"ok": True, "status": "ok", "asof": str(explicit_asof), "source": "explicit"}
        if not self.config.provider_calendar.exists():
            return {"ok": False, "status": "market_closed_or_no_new_asof", "message": "provider calendar not found"}
        rows = [line.strip() for line in self.config.provider_calendar.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not rows:
            return {"ok": False, "status": "market_closed_or_no_new_asof", "message": "provider calendar has no rows"}
        return {"ok": True, "status": "ok", "asof": rows[-1], "source": "provider_calendar"}

    def _validate_payload(self, payload: Dict[str, Any]) -> list[str]:
        if set(payload.keys()) != {"asof", "confirm_eod_pipeline", "mode"}:
            return ["request must contain only asof, confirm_eod_pipeline, and mode"]
        if payload.get("confirm_eod_pipeline") is not True:
            return ["confirm_eod_pipeline must be true"]
        if payload.get("mode") != EOD_PIPELINE_MODE:
            return ["mode must be controlled_smoke"]
        asof = str(payload.get("asof") or "")
        if not ASOF_RE.match(asof):
            return ["asof must match YYYY-MM-DD"]
        try:
            datetime.strptime(asof, "%Y-%m-%d")
        except ValueError:
            return ["asof must be a valid calendar date"]
        return []

    def _run_subprocess(self, argv: list[str], stdout_path: Path, stderr_path: Path) -> Dict[str, Any]:
        completed = self._execute_subprocess(argv, timeout=self.config.timeout_seconds)
        stdout_path.write_text(completed.stdout or "", encoding="utf-8")
        stderr_path.write_text(completed.stderr or "", encoding="utf-8")
        parsed = self._parse_json_tail(completed.stdout or "")
        return {
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "stdout_tail": (completed.stdout or "")[-1600:],
            "stderr_tail": (completed.stderr or "")[-1600:],
            "parsed_stdout": parsed,
        }

    def _execute_subprocess(self, argv: list[str], *, timeout: int) -> subprocess.CompletedProcess:
        return subprocess.run(
            argv,
            cwd=self.config.qlib_cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )

    def _reader_smoke(self) -> Dict[str, Any]:
        latest = self.signal_reader.latest(bucket="top30", enrich_trend=False)
        return {
            "status": latest.get("status"),
            "asof": latest.get("asof"),
            "run_id": latest.get("run_id"),
            "signals_count": len(latest.get("signals") or []),
            "trading": latest.get("trading") or research_only_trading_flags(),
        }

    def _result(self, job: Dict[str, Any], *, ok: bool) -> Dict[str, Any]:
        self.last_tick = dict(job)
        accepted = job.get("accepted_latest_scheduler") or {}
        return {
            "ok": ok,
            "status": job.get("status"),
            "message": job.get("message"),
            "pipeline_job_id": job.get("job_id"),
            "asof": job.get("asof"),
            "candidate_refresh_job_id": job.get("candidate_refresh_job_id"),
            "formal_publish_job_id": job.get("formal_publish_job_id"),
            "accepted_latest_scheduler_job_id": job.get("accepted_latest_scheduler_job_id"),
            "latest_run_id": job.get("latest_run_id"),
            "signals_count": job.get("signals_count"),
            "data_source_policy": job.get("data_source_policy"),
            "refresh_triggered": bool(job.get("refresh_triggered")),
            "provider_mutation_triggered": bool(job.get("provider_mutation_triggered")),
            "latest_signal_updated": bool(job.get("latest_signal_updated")),
            "research_signal_not_order": True,
            "accepted_latest_status": accepted.get("status"),
            "trading": research_only_trading_flags(),
            "job_path": str(self.config.ops_root / str(job.get("job_id")) / "job.json"),
        }

    def _blocked(self, message: str, *, status: str = "blocked") -> Dict[str, Any]:
        return {
            "ok": False,
            "status": status,
            "message": message,
            "normal_signal_run": False,
            "refresh_triggered": False,
            "provider_mutation_triggered": False,
            "latest_signal_updated": False,
            "research_signal_not_order": True,
            "trading": research_only_trading_flags(),
            "pipeline": self.status(),
        }

    def _job_id(self, asof: str) -> str:
        return f"option_c_eod_pipeline_{asof.replace('-', '')}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    def _config_snapshot(self) -> Dict[str, Any]:
        return {
            "enabled": self.config.enabled,
            "mode": self.config.mode,
            "qlib_cwd": str(self.config.qlib_cwd),
            "ops_root": str(self.config.ops_root),
            "provider_calendar": str(self.config.provider_calendar),
            "refresh_script": self.config.refresh_script,
            "publish_script": self.config.publish_script,
            "auto_loop_started": False,
            "loop_enabled": False,
        }

    @staticmethod
    def _parse_json_tail(text: str) -> Dict[str, Any]:
        start = text.rfind("{")
        if start < 0:
            return {}
        try:
            parsed = json.loads(text[start:])
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def _read_json_if_exists(path: Path) -> Dict[str, Any]:
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            return {"status": "unreadable", "message": str(exc), "path": str(path)}
        return {}

    @staticmethod
    def _write_json(path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


option_c_eod_pipeline = QlibOptionCEodPipeline()
