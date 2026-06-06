"""Disabled-by-default Option C normal accepted latest publish gate.

This module defines the review gate for future normal accepted latest publishing.
It does not refresh data, mutate providers, train models, or connect to trading.
When disabled, the public endpoint always blocks before any normal runner call.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
QLIB_PIPELINE_ROOT = REPO_ROOT / "qlib_pipeline"
from typing import Any, Dict, Optional

from app.services.tw_stock_qlib_option_c import research_only_trading_flags
from app.services.tw_stock_qlib_option_c_ops import (
    ASOF_RE,
    DEFAULT_LATEST_SIGNAL,
    DEFAULT_QLIB_CWD,
    JOB_ID_RE,
    LOCK_FILENAME,
    TIMEOUT_SECONDS,
    WRAPPER_SCRIPT,
    OptionCFileLock,
    _fingerprint,
    utc_now,
)

DEFAULT_OPS_ROOT = "data_tw/ops/option_c_jobs"
DEFAULT_SIGNAL_ROOT = str(QLIB_PIPELINE_ROOT / "data_tw/experiments/option_c_daily_signal")
DEFAULT_PROVIDER_CALENDAR = str(QLIB_PIPELINE_ROOT / "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt")
DEFAULT_EXPECTED_UNIVERSE = str(QLIB_PIPELINE_ROOT / "data_tw/experiments/option_c_forward_validation/timed_data_availability_retry_20260601T101323Z/symbols_accepted_prediction_universe.txt")
NORMAL_PUBLISH_MODE = "accepted-latest-publish-review"
EXPECTED_PREDICTION_ROWS = 150
EXPECTED_TOP30_ROWS = 30
EXPECTED_TOP50_ROWS = 50


def _parse_bool(raw: Optional[str], *, default: bool = False) -> bool:
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class OptionCNormalPublishConfig:
    enabled: bool = False
    mode: str = NORMAL_PUBLISH_MODE
    ops_root: Path = Path(DEFAULT_OPS_ROOT)
    signal_root: Path = Path(DEFAULT_SIGNAL_ROOT)
    provider_calendar: Path = Path(DEFAULT_PROVIDER_CALENDAR)
    expected_universe: Path = Path(DEFAULT_EXPECTED_UNIVERSE)
    qlib_cwd: Path = Path(DEFAULT_QLIB_CWD)
    wrapper_script: str = WRAPPER_SCRIPT
    latest_signal: Path = Path(DEFAULT_LATEST_SIGNAL)
    python_executable: str = os.getenv("TW_QLIB_OPTION_C_PYTHON") or sys.executable
    timeout_seconds: int = TIMEOUT_SECONDS
    lock_stale_seconds: int = TIMEOUT_SECONDS + 120

    @classmethod
    def from_env(cls) -> "OptionCNormalPublishConfig":
        repo_root = Path(__file__).resolve().parents[3]
        ops_root = Path(os.getenv("TW_OPTION_C_OPS_ROOT") or repo_root / DEFAULT_OPS_ROOT)
        return cls(
            enabled=_parse_bool(os.getenv("ENABLE_TW_QLIB_OPTION_C_NORMAL_PUBLISH"), default=False),
            mode=os.getenv("TW_QLIB_OPTION_C_NORMAL_PUBLISH_MODE") or NORMAL_PUBLISH_MODE,
            ops_root=ops_root,
            signal_root=Path(os.getenv("QLIB_TW_OPTION_C_ROOT") or DEFAULT_SIGNAL_ROOT),
            provider_calendar=Path(os.getenv("TW_QLIB_OPTION_C_PROVIDER_CALENDAR") or DEFAULT_PROVIDER_CALENDAR),
            expected_universe=Path(os.getenv("TW_QLIB_OPTION_C_EXPECTED_UNIVERSE") or DEFAULT_EXPECTED_UNIVERSE),
            qlib_cwd=Path(os.getenv("TW_QLIB_OPTION_C_CWD") or DEFAULT_QLIB_CWD),
            wrapper_script=os.getenv("TW_QLIB_OPTION_C_WRAPPER_SCRIPT") or WRAPPER_SCRIPT,
            latest_signal=Path(os.getenv("TW_QLIB_OPTION_C_LATEST_SIGNAL") or DEFAULT_LATEST_SIGNAL),
            python_executable=os.getenv("TW_QLIB_OPTION_C_PYTHON") or sys.executable,
            timeout_seconds=int(os.getenv("TW_QLIB_OPTION_C_NORMAL_TIMEOUT_SECONDS") or TIMEOUT_SECONDS),
        )


class QlibOptionCNormalPublishGate:
    """Review gate for accepted latest publishing; default disabled."""

    def __init__(self, config: Optional[OptionCNormalPublishConfig] = None) -> None:
        self.config = config or OptionCNormalPublishConfig.from_env()

    def status(self) -> Dict[str, Any]:
        return {
            "ok": self.config.mode == NORMAL_PUBLISH_MODE,
            "enabled": bool(self.config.enabled and self.config.mode == NORMAL_PUBLISH_MODE),
            "configured_enabled": bool(self.config.enabled),
            "mode": self.config.mode,
            "required_mode": NORMAL_PUBLISH_MODE,
            "signal_root": str(self.config.signal_root),
            "provider_calendar": str(self.config.provider_calendar),
            "normal_runner_enabled": bool(self.config.enabled and self.config.mode == NORMAL_PUBLISH_MODE),
            "auto_scheduler_enabled": False,
            "trading": research_only_trading_flags(),
        }

    def publish(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        errors = self.validate_payload(payload)
        if errors:
            return self._blocked(errors[0])
        if not self.config.enabled:
            return self._blocked("ENABLE_TW_QLIB_OPTION_C_NORMAL_PUBLISH is false")
        if self.config.mode != NORMAL_PUBLISH_MODE:
            return self._blocked("mode must be accepted-latest-publish-review")
        gate = self.preflight_gate(
            asof=str(payload["asof"]),
            dry_run_job_id=str(payload["dry_run_job_id"]),
        )
        if not gate.get("ok"):
            return self._blocked(str(gate.get("message") or gate.get("status") or "normal publish preflight blocked"), gate=gate)
        return self._run_publish(asof=str(payload["asof"]), dry_run_job_id=str(payload["dry_run_job_id"]), gate=gate)

    def validate_payload(self, payload: Dict[str, Any]) -> list[str]:
        if set(payload.keys()) != {"asof", "confirm_normal_publish", "dry_run_job_id"}:
            return ["request must contain only asof, confirm_normal_publish, and dry_run_job_id"]
        asof = str(payload.get("asof") or "")
        if not ASOF_RE.match(asof):
            return ["asof must match YYYY-MM-DD"]
        try:
            datetime.strptime(asof, "%Y-%m-%d")
        except ValueError:
            return ["asof must be a valid calendar date"]
        if payload.get("confirm_normal_publish") is not True:
            return ["confirm_normal_publish must be true"]
        if not JOB_ID_RE.match(str(payload.get("dry_run_job_id") or "")):
            return ["dry_run_job_id is invalid"]
        return []

    def preflight_gate(self, *, asof: str, dry_run_job_id: str) -> Dict[str, Any]:
        checks: Dict[str, Any] = {
            "mode": self.config.mode,
            "asof": asof,
            "dry_run_job_id": dry_run_job_id,
            "trading": research_only_trading_flags(),
        }
        if self.config.mode != NORMAL_PUBLISH_MODE:
            return self._gate_blocked("mode_invalid", "mode must be accepted-latest-publish-review", checks)
        lock_path = self.config.ops_root / LOCK_FILENAME
        if lock_path.exists():
            return self._gate_blocked("ops_lock_running", "normal publish blocked while ops lock exists", checks)
        dry_run = self._load_dry_run_job(dry_run_job_id)
        checks["dry_run_job"] = dry_run
        if not dry_run.get("ok"):
            return self._gate_blocked(str(dry_run.get("status") or "dry_run_job_invalid"), str(dry_run.get("message") or "dry-run job invalid"), checks)
        job = dry_run["job"]
        if job.get("status") != "dry_run_passed":
            return self._gate_blocked("dry_run_not_passed", "latest dry-run job must be dry_run_passed", checks)
        if str(job.get("asof") or "") != asof:
            return self._gate_blocked("asof_mismatch", "dry-run asof must match target asof", checks)
        if job.get("latest_signal_updated") is True:
            return self._gate_blocked("dry_run_mutated_latest", "dry-run must not update latest_signal", checks)
        before = job.get("latest_before") or {}
        after = job.get("latest_after") or {}
        if before != after:
            return self._gate_blocked("dry_run_latest_fingerprint_changed", "dry-run latest_signal fingerprint must remain unchanged", checks)
        calendar = self.provider_calendar_check(asof)
        checks["provider_calendar_check"] = calendar
        if not calendar.get("ok"):
            return self._gate_blocked(str(calendar.get("status")), str(calendar.get("message")), checks)
        formal = self.formal_provider_validation(asof)
        checks["formal_provider_validation"] = formal
        if not formal.get("ok"):
            return self._gate_blocked(str(formal.get("status")), str(formal.get("message")), checks)
        checks["ok"] = True
        checks["status"] = "preflight_passed"
        return checks

    def _load_dry_run_job(self, job_id: str) -> Dict[str, Any]:
        if not JOB_ID_RE.match(str(job_id or "")):
            return {"ok": False, "status": "invalid_dry_run_job_id", "message": "invalid dry_run_job_id"}
        path = self.config.ops_root / job_id / "job.json"
        if not path.exists():
            return {"ok": False, "status": "dry_run_job_not_found", "message": "dry-run job not found"}
        try:
            job = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            return {"ok": False, "status": "dry_run_job_unreadable", "message": str(exc)}
        return {"ok": True, "status": "ok", "job": job}

    def provider_calendar_check(self, asof: str) -> Dict[str, Any]:
        path = self.config.provider_calendar
        if not path.exists():
            return {"ok": False, "status": "provider_calendar_missing", "message": "provider calendar missing"}
        rows = {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}
        if asof not in rows:
            return {"ok": False, "status": "provider_calendar_missing_asof", "message": "provider calendar does not contain target asof"}
        return {"ok": True, "status": "pass", "asof": asof, "calendar_path": str(path)}

    def formal_provider_validation(self, asof: str) -> Dict[str, Any]:
        universe = self.config.expected_universe
        if not universe.exists():
            return {"ok": False, "status": "expected_universe_missing", "message": "expected universe file missing"}
        symbols = [line.strip() for line in universe.read_text(encoding="utf-8").splitlines() if line.strip()]
        if len(symbols) != EXPECTED_PREDICTION_ROWS:
            return {"ok": False, "status": "expected_universe_size_invalid", "message": "expected universe must contain 150 symbols", "count": len(symbols)}
        return {"ok": True, "status": "pass", "asof": asof, "expected_universe_count": len(symbols), "expected_universe": str(universe)}

    def validate_accepted_artifacts(self, run_dir: Path, *, asof: str) -> Dict[str, Any]:
        run_dir = Path(run_dir)
        required = {
            "run_metadata": run_dir / "run_metadata.json",
            "signal_summary": run_dir / "signal_summary.json",
            "top30_signals": run_dir / "top30_signals.csv",
            "top50_signals": run_dir / "top50_signals.csv",
        }
        missing = [key for key, path in required.items() if not path.exists()]
        if missing:
            return {"ok": False, "status": "artifact_missing", "message": "required artifacts missing", "missing": missing, "trading": research_only_trading_flags()}
        try:
            metadata = json.loads(required["run_metadata"].read_text(encoding="utf-8"))
            summary = json.loads(required["signal_summary"].read_text(encoding="utf-8"))
        except Exception as exc:
            return {"ok": False, "status": "artifact_unreadable", "message": str(exc), "trading": research_only_trading_flags()}
        errors: list[str] = []
        if metadata.get("status") != "accepted" or summary.get("status") != "accepted":
            errors.append("status_not_accepted")
        if str(metadata.get("asof") or summary.get("asof") or "") != asof:
            errors.append("asof_mismatch")
        expected_pairs = {
            "prediction_rows": EXPECTED_PREDICTION_ROWS,
            "top30_rows": EXPECTED_TOP30_ROWS,
            "top50_rows": EXPECTED_TOP50_ROWS,
        }
        for key, expected in expected_pairs.items():
            if int(summary.get(key) or 0) != expected:
                errors.append(f"{key}_invalid")
        if float(summary.get("finite_prediction_share") or 0.0) != 1.0:
            errors.append("finite_prediction_share_invalid")
        for key in ("diagnostic_only", "research_signal_not_order"):
            if summary.get(key) is not True:
                errors.append(f"{key}_not_true")
        for key in (
            "paper_trading_started",
            "live_trading_started",
            "target_trades_generated",
            "executable_orders_generated",
        ):
            if summary.get(key) is True or metadata.get(key) is True:
                errors.append(f"{key}_true")
        if errors:
            return {"ok": False, "status": "artifact_validation_failed", "errors": errors, "trading": research_only_trading_flags()}
        return {
            "ok": True,
            "status": "pass",
            "run_dir": str(run_dir),
            "artifacts": {key: str(path) for key, path in required.items()},
            "before_latest_required": True,
            "trading": research_only_trading_flags(),
        }


    def fixed_runner_argv(self, asof: str) -> list[str]:
        return [self.config.python_executable, self.config.wrapper_script, "--asof", asof, "--normal"]

    def _run_publish(self, *, asof: str, dry_run_job_id: str, gate: Dict[str, Any]) -> Dict[str, Any]:
        job_id = self._normal_job_id(asof)
        job_dir = self.config.ops_root / job_id
        job_dir.mkdir(parents=True, exist_ok=False)
        stdout_path = job_dir / "stdout.txt"
        stderr_path = job_dir / "stderr.txt"
        job_path = job_dir / "job.json"
        lock = OptionCFileLock(self.config.ops_root / LOCK_FILENAME, stale_seconds=self.config.lock_stale_seconds)
        lock_state = lock.acquire(job_id=job_id)
        if not lock_state.get("ok"):
            payload = self._blocked("normal publish blocked while ops lock exists", gate=gate)
            payload["status"] = "conflict"
            payload["normal_publish_job_id"] = job_id
            payload["lock"] = lock_state
            return payload

        argv = self.fixed_runner_argv(asof)
        job: Dict[str, Any] = {
            "job_id": job_id,
            "type": "option_c_normal_publish",
            "asof": asof,
            "dry_run_job_id": dry_run_job_id,
            "status": "running",
            "cwd": str(self.config.qlib_cwd),
            "argv": argv,
            "started_at": utc_now(),
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "latest_before": _fingerprint(self.config.latest_signal),
            "normal_signal_run": False,
            "accepted_artifact_generated": False,
            "latest_signal_updated": False,
            "refresh_triggered": False,
            "publish_triggered": False,
            "provider_mutation_triggered": False,
            "trading": research_only_trading_flags(),
        }
        self._write_json(job_path, job)

        try:
            completed = self._execute_subprocess(argv, timeout=self.config.timeout_seconds)
            stdout_path.write_text(completed.stdout or "", encoding="utf-8")
            stderr_path.write_text(completed.stderr or "", encoding="utf-8")
            job.update({"returncode": completed.returncode, "normal_signal_run": True})
            if completed.returncode != 0:
                job.update({"status": "normal_runner_failed", "reason": "normal runner returned non-zero"})
                return self._finish_blocked(job_path, job, "normal runner failed", gate=gate)

            parsed = self._parse_runner_output(completed.stdout or "")
            job["runner_output"] = parsed
            if parsed.get("status") != "accepted":
                job.update({"status": "normal_runner_not_accepted", "reason": "normal runner did not return accepted status"})
                return self._finish_blocked(job_path, job, "normal runner did not return accepted", gate=gate)

            run_dir = self._resolve_run_dir(str(parsed.get("run_dir") or ""))
            job["run_dir"] = str(run_dir)
            artifact_validation = self.validate_accepted_artifacts(run_dir, asof=asof)
            job["artifact_validation"] = artifact_validation
            if not artifact_validation.get("ok"):
                job.update({"status": "artifact_validation_failed", "accepted_artifact_generated": True})
                return self._finish_blocked(job_path, job, "artifact validation failed", gate=gate)

            new_latest_doc = self._build_latest_doc(run_dir, asof=asof)
            prepared = self.prepare_latest_update(self.config.latest_signal, new_latest_doc, backup_dir=self.config.ops_root / "latest_backups")
            self._atomic_write_json(self.config.latest_signal, new_latest_doc)
            latest_after = _fingerprint(self.config.latest_signal)
            job.update(
                {
                    "status": "normal_publish_passed",
                    "finished_at": utc_now(),
                    "accepted_artifact_generated": True,
                    "latest_signal_updated": True,
                    "latest_update": {"prepared": prepared, "after_fingerprint": latest_after},
                    "latest_after": latest_after,
                }
            )
            self._write_json(job_path, job)
            return {
                "ok": True,
                "status": "normal_publish_passed",
                "message": "normal accepted latest published",
                "normal_publish_job_id": job_id,
                "dry_run_job_id": dry_run_job_id,
                "asof": asof,
                "gate": gate,
                "run_dir": str(run_dir),
                "runner": {"cwd": str(self.config.qlib_cwd), "argv": argv, "returncode": completed.returncode},
                "artifact_validation": artifact_validation,
                "latest_update": job["latest_update"],
                "normal_signal_run": True,
                "accepted_artifact_generated": True,
                "latest_signal_updated": True,
                "refresh_triggered": False,
                "publish_triggered": False,
                "provider_mutation_triggered": False,
                "trading": research_only_trading_flags(),
            }
        except subprocess.TimeoutExpired as exc:
            stdout_path.write_text(str(exc.stdout or ""), encoding="utf-8")
            stderr_path.write_text(str(exc.stderr or ""), encoding="utf-8")
            job.update({"status": "normal_runner_timeout", "reason": str(exc), "finished_at": utc_now()})
            return self._finish_blocked(job_path, job, "normal runner timed out", gate=gate)
        except Exception as exc:
            job.update({"status": "normal_publish_failed", "reason": str(exc), "finished_at": utc_now()})
            return self._finish_blocked(job_path, job, str(exc), gate=gate)
        finally:
            lock.release(job_id=job_id)

    def _execute_subprocess(self, argv: list[str], *, timeout: int) -> subprocess.CompletedProcess:
        return subprocess.run(
            argv,
            cwd=str(self.config.qlib_cwd),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )

    def _normal_job_id(self, asof: str) -> str:
        digest = f"{os.getpid():x}{threading.get_ident():x}"[-8:].rjust(8, "0")
        return f"option_c_normal_publish_{asof.replace('-', '')}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{digest}"

    def _parse_runner_output(self, stdout: str) -> Dict[str, Any]:
        for index in [i for i, char in enumerate(stdout) if char == "{"][::-1]:
            try:
                payload = json.loads(stdout[index:])
            except Exception:
                continue
            if isinstance(payload, dict):
                return payload
        return {}

    def _resolve_run_dir(self, raw: str) -> Path:
        path = Path(raw)
        if not raw:
            raise ValueError("normal runner output missing run_dir")
        if path.is_absolute():
            run_dir = path
        else:
            prefix = Path("data_tw/experiments/option_c_daily_signal")
            if path == prefix:
                run_dir = self.config.signal_root
            elif str(path).startswith(str(prefix) + os.sep):
                run_dir = self.config.signal_root / path.relative_to(prefix)
            else:
                run_dir = self.config.qlib_cwd / path
        root = self.config.signal_root.resolve(strict=False)
        resolved = run_dir.resolve(strict=False)
        if resolved.parent != root:
            raise ValueError("normal runner run_dir must be directly under signal_root")
        return resolved

    def _build_latest_doc(self, run_dir: Path, *, asof: str) -> Dict[str, Any]:
        metadata = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))
        run_rel = Path("data_tw/experiments/option_c_daily_signal") / run_dir.name
        return {
            "status": "accepted",
            "created_at": metadata.get("created_at") or utc_now(),
            "run_dir": str(run_rel),
            "asof": asof,
            "top30_signals": str(run_rel / "top30_signals.csv"),
            "top50_signals": str(run_rel / "top50_signals.csv"),
            "diagnostic_only": True,
            "research_signal_not_order": True,
        }

    @staticmethod
    def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
        os.replace(tmp, path)

    @staticmethod
    def _write_json(path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    def _finish_blocked(self, job_path: Path, job: Dict[str, Any], message: str, *, gate: Dict[str, Any]) -> Dict[str, Any]:
        job.setdefault("finished_at", utc_now())
        job["latest_after"] = _fingerprint(self.config.latest_signal)
        job["latest_signal_updated"] = False
        self._write_json(job_path, job)
        payload = self._blocked(message, gate=gate)
        payload.update(
            {
                "normal_publish_job_id": job.get("job_id"),
                "normal_job_status": job.get("status"),
                "runner": {"cwd": job.get("cwd"), "argv": job.get("argv"), "returncode": job.get("returncode")},
                "artifact_validation": job.get("artifact_validation"),
                "normal_signal_run": bool(job.get("normal_signal_run")),
                "accepted_artifact_generated": bool(job.get("accepted_artifact_generated")),
                "latest_signal_updated": False,
            }
        )
        return payload

    def prepare_latest_update(self, latest_path: Path, new_latest_doc: Dict[str, Any], *, backup_dir: Path) -> Dict[str, Any]:
        latest_path = Path(latest_path)
        backup_dir = Path(backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        before = _fingerprint(latest_path)
        backup_path = backup_dir / f"latest_signal_backup_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        if latest_path.exists():
            shutil.copy2(latest_path, backup_path)
        backup = _fingerprint(backup_path)
        return {
            "ok": True,
            "status": "prepared",
            "latest_path": str(latest_path),
            "backup_path": str(backup_path),
            "before_fingerprint": before,
            "backup_fingerprint": backup,
            "new_latest_doc": new_latest_doc,
            "rollback_command": f"cp {backup_path} {latest_path}",
            "trading": research_only_trading_flags(),
        }

    def rollback_latest(self, *, latest_path: Path, backup_path: Path) -> Dict[str, Any]:
        latest_path = Path(latest_path)
        backup_path = Path(backup_path)
        if not backup_path.exists():
            return {"ok": False, "status": "backup_missing", "message": "backup latest_signal missing", "trading": research_only_trading_flags()}
        before = _fingerprint(latest_path)
        shutil.copy2(backup_path, latest_path)
        after = _fingerprint(latest_path)
        return {"ok": True, "status": "rolled_back", "before": before, "after": after, "trading": research_only_trading_flags()}

    def _gate_blocked(self, status: str, message: str, checks: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(checks)
        data.update({"ok": False, "status": status, "message": message, "trading": research_only_trading_flags()})
        return data

    def _blocked(self, message: str, *, gate: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {
            "ok": False,
            "status": "blocked",
            "message": message,
            "gate": gate,
            "normal_signal_run": False,
            "latest_signal_updated": False,
            "accepted_artifact_generated": False,
            "refresh_triggered": False,
            "publish_triggered": False,
            "provider_mutation_triggered": False,
            "trading": research_only_trading_flags(),
        }


option_c_normal_publish_gate = QlibOptionCNormalPublishGate()
