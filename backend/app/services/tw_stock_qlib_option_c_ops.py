"""Controlled qlib Option C dry-run ops runner.

This service only executes the fixed Option C provider dry-run wrapper. It does
not refresh data, publish providers, write accepted signals, or touch trading
state.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from app.services.tw_stock_qlib_option_c import research_only_trading_flags


ASOF_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
JOB_ID_RE = re.compile(r"^option_c_dry_run_\d{8}_[0-9TZ]+_[0-9a-f]{8}$")
DEFAULT_QLIB_CWD = "/home/chuliyang/qlib"
DEFAULT_LATEST_SIGNAL = "/home/chuliyang/qlib/data_tw/experiments/option_c_daily_signal/latest_signal.json"
DEFAULT_OPS_ROOT = "data_tw/ops/option_c_jobs"
WRAPPER_SCRIPT = "examples/tw/run_option_c_daily_signal_option_c_provider.py"
TIMEOUT_SECONDS = 600
TAIL_CHARS = 4000
LOCK_FILENAME = "option_c_ops.lock"
LOCK_STALE_SECONDS = TIMEOUT_SECONDS + 120
RETENTION_MAX_JOBS = 50
RETENTION_MAX_AGE_DAYS = 14


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _fingerprint(path: Path) -> Dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {"exists": False, "path": str(path), "size_bytes": 0, "sha256": None}
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return {"exists": True, "path": str(path), "size_bytes": path.stat().st_size, "sha256": h.hexdigest()}


def _tail(path: Path, limit: int = TAIL_CHARS) -> str:
    if not path.exists() or not path.is_file():
        return ""
    data = path.read_text(encoding="utf-8", errors="replace")
    return data[-limit:]


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


@dataclass(frozen=True)
class OptionCOpsConfig:
    qlib_cwd: Path
    ops_root: Path
    latest_signal: Path
    timeout_seconds: int = TIMEOUT_SECONDS
    lock_stale_seconds: int = LOCK_STALE_SECONDS
    retention_max_jobs: int = RETENTION_MAX_JOBS
    retention_max_age_days: int = RETENTION_MAX_AGE_DAYS
    retention_keep_failed_jobs: bool = True
    retention_keep_latest_success: bool = True


class OptionCFileLock:
    """Atomic file lock for cross-process Option C ops exclusion."""

    def __init__(self, path: Path, *, stale_seconds: int = LOCK_STALE_SECONDS) -> None:
        self.path = path
        self.stale_seconds = stale_seconds

    def acquire(self, *, job_id: str) -> Dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "owner_pid": os.getpid(),
            "job_id": job_id,
            "started_at": utc_now(),
            "stale_after_seconds": self.stale_seconds,
        }
        while True:
            try:
                fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            except FileExistsError:
                existing = self.read()
                if self._is_stale(existing):
                    try:
                        self.path.unlink()
                    except FileNotFoundError:
                        continue
                    except OSError:
                        return {"ok": False, "status": "conflict", "owner": existing}
                    continue
                return {"ok": False, "status": "conflict", "owner": existing}
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
            return {"ok": True, "status": "locked", "owner": payload}

    def release(self, *, job_id: str) -> bool:
        owner = self.read()
        if owner and owner.get("job_id") and owner.get("job_id") != job_id:
            return False
        try:
            self.path.unlink()
            return True
        except FileNotFoundError:
            return True

    def read(self) -> Dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            try:
                stat = self.path.stat()
                started_at = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
            except Exception:
                started_at = None
            return {"owner_pid": None, "job_id": None, "started_at": started_at, "unparseable": True}

    def _is_stale(self, owner: Dict[str, Any]) -> bool:
        raw = owner.get("started_at") if isinstance(owner, dict) else None
        try:
            started = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
        except Exception:
            try:
                started = datetime.fromtimestamp(self.path.stat().st_mtime, timezone.utc)
            except Exception:
                return False
        return datetime.now(timezone.utc) - started > timedelta(seconds=max(1, int(self.stale_seconds)))


class QlibOptionCOpsRunner:
    """Run one fixed qlib Option C provider dry-run job at a time."""

    _lock = threading.Lock()

    def __init__(self, config: Optional[OptionCOpsConfig] = None) -> None:
        if config is None:
            repo_root = Path(__file__).resolve().parents[3]
            ops_root = Path(os.getenv("TW_OPTION_C_OPS_ROOT") or repo_root / DEFAULT_OPS_ROOT)
            config = OptionCOpsConfig(
                qlib_cwd=Path(os.getenv("QLIB_TW_OPTION_C_CWD") or DEFAULT_QLIB_CWD),
                ops_root=ops_root,
                latest_signal=Path(os.getenv("QLIB_TW_OPTION_C_LATEST_SIGNAL") or DEFAULT_LATEST_SIGNAL),
            )
        self.config = config

    def trigger_dry_run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        errors = self._validate_payload(payload)
        if errors:
            return self._blocked("blocked", errors[0])
        asof = str(payload["asof"])
        job_id = self._job_id(asof)
        if not self._lock.acquire(blocking=False):
            return self._blocked("conflict", "another Option C ops job is already running", asof=asof)
        file_lock = OptionCFileLock(self.config.ops_root / LOCK_FILENAME, stale_seconds=self.config.lock_stale_seconds)
        acquired = file_lock.acquire(job_id=job_id)
        if not acquired.get("ok"):
            self._lock.release()
            return self._blocked("conflict", "another Option C ops job is already running", asof=asof)
        try:
            return self._run_locked(asof, job_id=job_id)
        finally:
            try:
                file_lock.release(job_id=job_id)
            finally:
                self._lock.release()

    def get_job(self, job_id: str) -> Dict[str, Any]:
        if not JOB_ID_RE.match(str(job_id or "")):
            return {"ok": False, "status": "invalid_job_id", "message": "invalid job_id", "trading": research_only_trading_flags()}
        path = self.config.ops_root / job_id / "job.json"
        if not path.exists():
            return {"ok": False, "status": "job_not_found", "message": "job not found", "trading": research_only_trading_flags()}
        return self._public_job(json.loads(path.read_text(encoding="utf-8")))

    def latest(self) -> Dict[str, Any]:
        if not self.config.ops_root.exists():
            return {"ok": True, "status": "empty", "job": None, "trading": research_only_trading_flags()}
        jobs = sorted(
            [p for p in self.config.ops_root.glob("option_c_dry_run_*/job.json") if p.is_file()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not jobs:
            return {"ok": True, "status": "empty", "job": None, "trading": research_only_trading_flags()}
        return {"ok": True, "status": "ok", "job": self._public_job(json.loads(jobs[0].read_text(encoding="utf-8"))), "trading": research_only_trading_flags()}

    def log_tail(self, job_id: str, *, stream: str = "stdout") -> Dict[str, Any]:
        job = self.get_job(job_id)
        if not job.get("ok"):
            return job
        if stream not in {"stdout", "stderr"}:
            return {"ok": False, "status": "invalid_stream", "message": "stream must be stdout or stderr", "trading": research_only_trading_flags()}
        path = self.config.ops_root / job_id / f"{stream}.txt"
        return {"ok": True, "status": "ok", "job_id": job_id, "stream": stream, "tail": _tail(path), "trading": research_only_trading_flags()}

    def _validate_payload(self, payload: Dict[str, Any]) -> list[str]:
        if set(payload.keys()) != {"asof"}:
            return ["request must contain only asof"]
        asof = str(payload.get("asof") or "")
        if not ASOF_RE.match(asof):
            return ["asof must match YYYY-MM-DD"]
        try:
            datetime.strptime(asof, "%Y-%m-%d")
        except ValueError:
            return ["asof must be a valid calendar date"]
        return []

    def _job_id(self, asof: str) -> str:
        digest = hashlib.sha256(f"{asof}:{utc_now()}:{threading.get_ident()}:{os.getpid()}".encode()).hexdigest()[:8]
        return f"option_c_dry_run_{asof.replace('-', '')}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{digest}"

    def _argv(self, asof: str) -> list[str]:
        return ["python", WRAPPER_SCRIPT, "--asof", asof, "--dry-run"]

    def _run_locked(self, asof: str, *, job_id: str) -> Dict[str, Any]:
        job_dir = self.config.ops_root / job_id
        stdout_path = job_dir / "stdout.txt"
        stderr_path = job_dir / "stderr.txt"
        argv = self._argv(asof)
        before = _fingerprint(self.config.latest_signal)
        job: Dict[str, Any] = {
            "job_id": job_id,
            "type": "option_c_provider_dry_run",
            "asof": asof,
            "status": "running",
            "cwd": str(self.config.qlib_cwd),
            "argv": argv,
            "started_at": utc_now(),
            "finished_at": None,
            "returncode": None,
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "parsed_dry_run_status": None,
            "latest_before": before,
            "latest_after": None,
            "latest_signal_updated": False,
            "normal_signal_run": False,
            "accepted_artifact_generated": False,
            "trading": research_only_trading_flags(),
        }
        _write_json(job_dir / "job.json", job)
        try:
            result = self._execute_subprocess(argv, timeout=self.config.timeout_seconds)
            stdout = result.stdout or ""
            stderr = result.stderr or ""
            returncode = result.returncode
            reason = ""
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            returncode = -1
            reason = "timeout"
        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")
        after = _fingerprint(self.config.latest_signal)
        parsed = self._parse_dry_run_status(stdout)
        latest_changed = before != after
        if latest_changed:
            status = "blocked_latest_signal_changed"
        elif returncode == 0 and parsed == "dry_run_preflight_pass":
            status = "dry_run_passed"
        else:
            status = "dry_run_failed"
            if not reason:
                reason = "dry_run_status_not_pass"
        job.update(
            {
                "status": status,
                "finished_at": utc_now(),
                "returncode": returncode,
                "parsed_dry_run_status": parsed,
                "latest_after": after,
                "latest_signal_updated": latest_changed,
                "reason": reason,
                "stdout_tail": stdout[-TAIL_CHARS:],
                "stderr_tail": stderr[-TAIL_CHARS:],
            }
        )
        _write_json(job_dir / "job.json", job)
        self.cleanup_jobs()
        return self._public_job(job)

    def cleanup_jobs(self, *, dry_run: bool = False) -> Dict[str, Any]:
        """Clean old QuantDinger ops job logs only under the configured ops root."""
        if not self.config.ops_root.exists():
            return {"ok": True, "removed": [], "kept": [], "dry_run": dry_run}
        candidates = []
        for job_json in self.config.ops_root.glob("option_c_dry_run_*/job.json"):
            if not job_json.is_file():
                continue
            job_dir = job_json.parent
            try:
                job = json.loads(job_json.read_text(encoding="utf-8"))
            except Exception:
                job = {}
            candidates.append({
                "dir": job_dir,
                "job_id": job_dir.name,
                "status": job.get("status"),
                "mtime": job_json.stat().st_mtime,
            })
        if not candidates:
            return {"ok": True, "removed": [], "kept": [], "dry_run": dry_run}

        latest_success = None
        if self.config.retention_keep_latest_success:
            successes = [item for item in candidates if item.get("status") == "dry_run_passed"]
            latest_success = max(successes, key=lambda item: item["mtime"])["job_id"] if successes else None

        now = time.time()
        max_age_seconds = max(0, int(self.config.retention_max_age_days)) * 86400
        by_newest = sorted(candidates, key=lambda item: item["mtime"], reverse=True)
        keep_ids = {item["job_id"] for item in by_newest[: max(0, int(self.config.retention_max_jobs))]}
        if latest_success:
            keep_ids.add(latest_success)

        removed = []
        kept = []
        for item in by_newest:
            age_exceeded = max_age_seconds > 0 and now - item["mtime"] > max_age_seconds
            count_exceeded = item["job_id"] not in keep_ids
            failed = item.get("status") not in {"dry_run_passed", "running"}
            protected = item["job_id"] == latest_success or item.get("status") == "running"
            if self.config.retention_keep_failed_jobs and failed:
                protected = True
            if protected or not (age_exceeded or count_exceeded):
                kept.append(item["job_id"])
                continue
            removed.append(item["job_id"])
            if not dry_run:
                self._remove_job_dir(item["dir"])
        return {
            "ok": True,
            "removed": removed,
            "kept": kept,
            "dry_run": dry_run,
            "policy": {
                "max_jobs": self.config.retention_max_jobs,
                "max_age_days": self.config.retention_max_age_days,
                "keep_failed_jobs": self.config.retention_keep_failed_jobs,
                "keep_latest_success": self.config.retention_keep_latest_success,
            },
        }

    def _remove_job_dir(self, job_dir: Path) -> None:
        resolved_root = self.config.ops_root.resolve()
        resolved_dir = job_dir.resolve()
        if resolved_dir.parent != resolved_root or not JOB_ID_RE.match(resolved_dir.name):
            raise ValueError("refusing to remove path outside Option C ops job root")
        for child in resolved_dir.iterdir():
            if child.is_file() or child.is_symlink():
                child.unlink()
            else:
                raise ValueError("unexpected nested directory in ops job dir")
        resolved_dir.rmdir()

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

    def _parse_dry_run_status(self, stdout: str) -> Optional[str]:
        for line in reversed(stdout.splitlines()):
            raw = line.strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except Exception:
                continue
            status = payload.get("status")
            return str(status) if status else None
        if "dry_run_preflight_pass" in stdout:
            return "dry_run_preflight_pass"
        return None

    def _public_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(job)
        data["stdout_tail"] = _tail(Path(str(job.get("stdout_path") or "")))
        data["stderr_tail"] = _tail(Path(str(job.get("stderr_path") or "")))
        data["trading"] = research_only_trading_flags()
        data["ok"] = data.get("status") in {"running", "dry_run_passed"}
        return data

    def _blocked(self, status: str, message: str, *, asof: Optional[str] = None) -> Dict[str, Any]:
        return {
            "ok": False,
            "status": status,
            "message": message,
            "asof": asof,
            "trading": research_only_trading_flags(),
            "latest_signal_updated": False,
            "normal_signal_run": False,
        }


option_c_ops_runner = QlibOptionCOpsRunner()
