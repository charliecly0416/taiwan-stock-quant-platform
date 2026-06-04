"""Read-only Taiwan stock daily auto-update status service."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.tw_stock_qlib_option_c import DEFAULT_SIGNAL_ROOT, research_only_trading_flags

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OPS_ROOT = REPO_ROOT / "data_tw/ops/daily_auto_update"
OPS_ROOT_ENV = "TW_DAILY_AUTO_UPDATE_OPS_ROOT"
SIGNAL_ROOT_ENV = "QLIB_TW_OPTION_C_ROOT"
CRON_TAIL_LINES = 40


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_json(path: Path, warnings: list[str]) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
        warnings.append(f"{path.name}:json_not_object")
    except FileNotFoundError:
        warnings.append(f"{path.name}:missing")
    except Exception as exc:
        warnings.append(f"{path.name}:json_read_failed:{type(exc).__name__}")
    return {}


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        raw = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _read_tail(path: Path, lines: int = CRON_TAIL_LINES) -> list[str]:
    try:
        content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except FileNotFoundError:
        return []
    except Exception:
        return []
    return content[-max(1, lines):]


class TWStockDailyAutoUpdateStatusService:
    """Build a read-only daily auto-update status summary from local artifacts."""

    def __init__(self, *, signal_root: str | Path | None = None, ops_root: str | Path | None = None) -> None:
        raw_signal_root = signal_root or os.getenv(SIGNAL_ROOT_ENV) or DEFAULT_SIGNAL_ROOT
        raw_ops_root = ops_root or os.getenv(OPS_ROOT_ENV) or DEFAULT_OPS_ROOT
        self.signal_root = Path(raw_signal_root).expanduser().resolve(strict=False)
        self.ops_root = Path(raw_ops_root).expanduser().resolve(strict=False)

    def status(self, *, now: datetime | None = None) -> dict[str, Any]:
        warnings: list[str] = []
        latest = self._latest_signal(warnings)
        pending = self._pending_asof(warnings)
        last_job = self._last_job(warnings)
        cron = self._cron_status()
        data = self._status_payload(latest=latest, pending=pending, last_job=last_job, cron=cron, warnings=warnings, now=now or _utc_now())
        return data

    def _latest_signal(self, warnings: list[str]) -> dict[str, Any]:
        latest_path = self.signal_root / "latest_signal.json"
        doc = _safe_json(latest_path, warnings)
        run_dir = str(doc.get("run_dir") or "")
        run_id = Path(run_dir).name if run_dir else None
        return {
            "path": str(latest_path),
            "exists": latest_path.exists(),
            "status": doc.get("status"),
            "asof": doc.get("asof"),
            "run_id": run_id,
            "created_at": doc.get("created_at"),
        }

    def _pending_asof(self, warnings: list[str]) -> dict[str, Any]:
        pending_path = self.ops_root / "pending_asof.json"
        if not pending_path.exists():
            return {"path": str(pending_path), "exists": False}
        doc = _safe_json(pending_path, warnings)
        return {
            "path": str(pending_path),
            "exists": True,
            "asof": doc.get("asof"),
            "reason": doc.get("reason"),
            "job_id": doc.get("job_id"),
            "updated_at": doc.get("updated_at"),
        }

    def _last_job(self, warnings: list[str]) -> dict[str, Any]:
        job_paths = sorted(self.ops_root.glob("*/job.json")) if self.ops_root.exists() else []
        candidates: list[tuple[datetime, Path, dict[str, Any]]] = []
        for path in job_paths:
            doc = _safe_json(path, warnings)
            sort_time = _parse_dt(doc.get("finished_at") or doc.get("started_at") or doc.get("created_at"))
            if sort_time is None:
                try:
                    sort_time = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
                except Exception:
                    sort_time = datetime.min.replace(tzinfo=timezone.utc)
            candidates.append((sort_time, path, doc))
        if not candidates:
            return {"exists": False, "path": None}
        candidates.sort(key=lambda item: item[0], reverse=True)
        _, path, doc = candidates[0]
        return self._summarize_job(path, doc)

    def _summarize_job(self, path: Path, doc: dict[str, Any]) -> dict[str, Any]:
        refresh_summary = doc.get("refresh_summary") if isinstance(doc.get("refresh_summary"), dict) else {}
        validation = refresh_summary.get("normalized_validation") if isinstance(refresh_summary.get("normalized_validation"), dict) else {}
        fetch = refresh_summary.get("fetch") if isinstance(refresh_summary.get("fetch"), dict) else {}
        finmind = doc.get("finmind_update") if isinstance(doc.get("finmind_update"), dict) else {}
        yahoo = doc.get("yahoo_refresh") if isinstance(doc.get("yahoo_refresh"), dict) else {}
        yahoo_date_max = validation.get("date_max_max") or validation.get("date_max_min")
        if not yahoo_date_max:
            sample = fetch.get("per_symbol_sample") if isinstance(fetch.get("per_symbol_sample"), list) else []
            dates = [str(item.get("date_max")) for item in sample if isinstance(item, dict) and item.get("date_max")]
            yahoo_date_max = max(dates) if dates else None
        return {
            "exists": True,
            "path": str(path),
            "job_id": doc.get("job_id") or path.parent.name,
            "status": doc.get("status"),
            "asof": doc.get("asof") or refresh_summary.get("asof"),
            "started_at": doc.get("started_at"),
            "finished_at": doc.get("finished_at"),
            "message": doc.get("message"),
            "finmind_update_status": self._status_from_step(finmind, fallback_triggered=doc.get("finmind_update_triggered")),
            "finmind_archived_count": self._finmind_archived_count(doc, finmind),
            "yahoo_update_status": self._status_from_step(yahoo, fallback_triggered=doc.get("yahoo_refresh_triggered")),
            "yahoo_target_asof": doc.get("asof") or refresh_summary.get("asof"),
            "yahoo_date_max": yahoo_date_max,
            "yahoo_missing_asof_count": validation.get("missing_asof_count"),
            "provider_publish_triggered": bool(doc.get("provider_publish_triggered")),
            "latest_signal_updated": bool(doc.get("latest_signal_updated")),
            "refresh_status": refresh_summary.get("status"),
            "refresh_errors": refresh_summary.get("errors") if isinstance(refresh_summary.get("errors"), list) else [],
        }

    def _finmind_archived_count(self, doc: dict[str, Any], finmind: dict[str, Any]) -> Any:
        direct = doc.get("archived_count") or finmind.get("archived_count")
        if direct is not None:
            return direct
        for key in ("stdout_tail", "stdout"):
            raw = str(finmind.get(key) or "")
            match = re.search(r'"archived_count"\s*:\s*([0-9]+)', raw)
            if match:
                return int(match.group(1))
        return None

    def _status_from_step(self, step: dict[str, Any], *, fallback_triggered: Any = None) -> str:
        if step:
            if step.get("ok") is True:
                return "success"
            if step.get("ok") is False:
                return "failed"
            return str(step.get("status") or "unknown")
        if fallback_triggered is True:
            return "unknown"
        if fallback_triggered is False:
            return "not_triggered"
        return "not_available"

    def _cron_status(self) -> dict[str, Any]:
        installed_path = self.ops_root / "tw-daily-auto-update.installed.cron"
        cron_log = self.ops_root / "cron.log"
        installed_text = ""
        try:
            installed_text = installed_path.read_text(encoding="utf-8")
        except Exception:
            installed_text = ""
        return {
            "installed_file": str(installed_path),
            "installed_file_exists": installed_path.exists(),
            "cron_log": str(cron_log),
            "cron_log_exists": cron_log.exists(),
            "cron_installed_hint": installed_path.exists() or cron_log.exists(),
            "installed_schedule": self._extract_schedule(installed_text),
            "cron_log_tail": _read_tail(cron_log),
        }

    def _extract_schedule(self, text: str) -> list[str]:
        lines = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            lines.append(stripped)
        return lines

    def _status_payload(
        self,
        *,
        latest: dict[str, Any],
        pending: dict[str, Any],
        last_job: dict[str, Any],
        cron: dict[str, Any],
        warnings: list[str],
        now: datetime,
    ) -> dict[str, Any]:
        last_job_status = last_job.get("status")
        pending_asof = pending.get("asof") if pending.get("exists") else None
        pending_reason = pending.get("reason") if pending.get("exists") else None
        fresh_data_wait = bool(
            last_job_status == "fresh_data_wait"
            or pending_reason == "fresh_data_wait"
            or last_job.get("yahoo_missing_asof_count")
        )
        return {
            "ok": True,
            "status": "ok",
            "generated_at": now.isoformat(),
            "latest_asof": latest.get("asof"),
            "latest_status": latest.get("status"),
            "latest_run_id": latest.get("run_id"),
            "latest_created_at": latest.get("created_at"),
            "pending_asof": pending_asof,
            "pending_reason": pending_reason,
            "pending_job_id": pending.get("job_id") if pending.get("exists") else None,
            "pending_updated_at": pending.get("updated_at") if pending.get("exists") else None,
            "last_job_id": last_job.get("job_id"),
            "last_job_status": last_job_status,
            "last_job_started_at": last_job.get("started_at"),
            "last_job_finished_at": last_job.get("finished_at"),
            "last_job_message": last_job.get("message"),
            "finmind_update_status": last_job.get("finmind_update_status"),
            "finmind_archived_count": last_job.get("finmind_archived_count"),
            "yahoo_update_status": last_job.get("yahoo_update_status"),
            "yahoo_target_asof": last_job.get("yahoo_target_asof"),
            "yahoo_date_max": last_job.get("yahoo_date_max"),
            "yahoo_missing_asof_count": last_job.get("yahoo_missing_asof_count"),
            "fresh_data_wait": fresh_data_wait,
            "next_retry_hint": self._next_retry_hint(pending_asof=pending_asof, pending_reason=pending_reason, fresh_data_wait=fresh_data_wait, cron=cron),
            "cron_installed_hint": bool(cron.get("cron_installed_hint")),
            "cron": cron,
            "sources": {
                "latest_signal": latest.get("path"),
                "pending_asof": pending.get("path"),
                "last_job": last_job.get("path"),
            },
            "warnings": list(dict.fromkeys(warnings)),
            "trading": research_only_trading_flags(),
        }

    def _next_retry_hint(self, *, pending_asof: Any, pending_reason: Any, fresh_data_wait: bool, cron: dict[str, Any]) -> str:
        if fresh_data_wait and pending_asof:
            if cron.get("cron_installed_hint"):
                return f"pending asof {pending_asof} will be retried by the installed schedule; reason={pending_reason or 'fresh_data_wait'}"
            return f"pending asof {pending_asof} is waiting, but no installed cron hint was found"
        if cron.get("cron_installed_hint"):
            return "no pending asof; installed schedule will run at the next configured window"
        return "no installed cron hint found"
