#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "fpala.formal_accepted_latest_automation_decision.v1"

DEFAULT_OUTPUT_ROOT = ROOT / "data_tw/experiments/formal_provider_accepted_latest_automation_alignment"
DEFAULT_CANDIDATE_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/daily_auto_provider_candidates"
DEFAULT_FORMAL_PROVIDER_CALENDAR = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt"
DEFAULT_QLIB_ACCEPTED_LATEST = ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json"
DEFAULT_LEGACY_LATEST = ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json"
DEFAULT_DAPR18_SIGNAL_LATEST = ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json"
DEFAULT_READONLY_SNAPSHOT_LATEST = ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json"
DEFAULT_AGENT_PROMPT_LATEST = ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json"
DEFAULT_INSTALLED_CRON = ROOT / "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron"
DEFAULT_PENDING_ASOF = ROOT / "data_tw/ops/daily_auto_update/pending_asof.json"
TAIPEI = ZoneInfo("Asia/Taipei")

FORBIDDEN_AUDIT_KEYS = [
    "daily_auto_manual_run",
    "real_provider_pull_or_refresh",
    "provider_publish",
    "formal_provider_mutation",
    "qlib_refresh",
    "qlib_accepted_latest_switch",
    "legacy_latest_switch",
    "dapr18_product_latest_publish",
    "readonly_snapshot_latest_publish",
    "agent_prompt_build_or_publish",
    "cron_change",
    "openai_call",
    "db_access_or_write",
    "strategy_replay",
    "monitor_broker_order_target",
    "frontend_api_default_switch",
]


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return now_utc().isoformat(timespec="seconds")


def rel(path: Path, *, root: Path = ROOT) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def resolve_path(raw: str | Path, *, root: Path = ROOT) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else root / path


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")


def json_asof(payload: dict[str, Any]) -> str:
    return str(payload.get("asof") or payload.get("signal_asof") or payload.get("target_asof") or "")


def fingerprint(path: Path, *, root: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": rel(path, root=root),
        "exists": path.exists(),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size if path.exists() and path.is_file() else None,
        "mtime_ns": path.stat().st_mtime_ns if path.exists() else None,
        "asof_or_signal_asof_when_json": "",
    }
    if path.exists() and path.is_file() and path.suffix == ".json":
        try:
            result["asof_or_signal_asof_when_json"] = json_asof(read_json(path))
        except Exception as exc:  # pragma: no cover - defensive evidence
            result["json_error"] = str(exc)
    return result


def calendar_max(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    last = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if value:
            last = value
    return last


def find_candidate_readiness(candidate_root: Path, target_asof: str, explicit_candidate_dir: Path | None = None) -> tuple[Path | None, dict[str, Any]]:
    candidates: list[Path] = []
    if explicit_candidate_dir is not None:
        candidates = [explicit_candidate_dir]
    elif candidate_root.exists():
        candidates = sorted(candidate_root.glob(f"daily_auto_provider_candidate_{target_asof.replace('-', '')}_*"), reverse=True)
    for candidate_dir in candidates:
        readiness = candidate_dir / "provider_candidate_readiness.json"
        if readiness.exists():
            return candidate_dir, read_json(readiness)
    return (explicit_candidate_dir if explicit_candidate_dir else None), {}


def all_false(mapping: dict[str, Any]) -> bool:
    return all(value is False for value in mapping.values())


def forbidden_scope_audit() -> dict[str, Any]:
    actions = {key: False for key in FORBIDDEN_AUDIT_KEYS}
    return {"all_false": True, "actions": actions}


def candidate_forbidden_violation(readiness: dict[str, Any]) -> bool:
    top_level_flags = [
        "formal_provider_mutated",
        "formal_normalized_mutated",
        "latest_signal_updated",
    ]
    if any(bool(readiness.get(key)) for key in top_level_flags):
        return True
    forbidden = readiness.get("forbidden_actions")
    return isinstance(forbidden, dict) and any(bool(value) for value in forbidden.values())


def candidate_validation(candidate_dir: Path | None, readiness: dict[str, Any], target_asof: str) -> dict[str, Any]:
    if not readiness:
        return {
            "ok": False,
            "missing": True,
            "invalid": False,
            "forbidden_violation": False,
            "errors": ["candidate_readiness_missing"],
        }
    errors: list[str] = []
    calendar = str(readiness.get("staged_provider_calendar_max") or readiness.get("calendar_max") or "")
    candidate_asof = str(readiness.get("candidate_asof") or readiness.get("asof") or "")
    calendar_has_asof = bool(readiness.get("staged_provider_calendar_has_asof") or readiness.get("calendar_has_asof") or False)
    success = int(readiness.get("candidate_normalized_symbols_success") or readiness.get("symbols_success") or 0)
    with_asof = int(readiness.get("candidate_normalized_symbols_with_asof") or readiness.get("symbols_with_asof") or 0)
    validation = str(readiness.get("staged_provider_validation_status") or readiness.get("provider_validation_status") or "")
    smoke = str(readiness.get("candidate_model_smoke_status") or readiness.get("model_smoke_status") or "")
    forbidden_violation = candidate_forbidden_violation(readiness)
    if not candidate_dir or not candidate_dir.exists():
        errors.append("candidate_dir_missing")
    if candidate_asof != target_asof:
        errors.append("candidate_asof_mismatch")
    if success != 150:
        errors.append("candidate_normalized_symbols_success_not_150")
    if with_asof != 150:
        errors.append("candidate_normalized_symbols_with_asof_not_150")
    if calendar < target_asof:
        errors.append("staged_provider_calendar_max_before_target")
    if not calendar_has_asof:
        errors.append("staged_provider_calendar_missing_target_asof")
    if validation != "pass":
        errors.append("staged_provider_validation_status_not_pass")
    if smoke != "pass":
        errors.append("candidate_model_smoke_status_not_pass")
    if bool(readiness.get("production_allowed")):
        errors.append("production_allowed_true_in_no_publish_candidate")
    if bool(readiness.get("publish_latest_authorized")):
        errors.append("publish_latest_authorized_true_in_no_publish_candidate")
    if forbidden_violation:
        errors.append("candidate_forbidden_action_true")
    return {
        "ok": not errors,
        "missing": False,
        "invalid": bool(errors),
        "forbidden_violation": forbidden_violation,
        "errors": errors,
        "candidate_asof": candidate_asof,
        "calendar_max": calendar,
        "calendar_has_asof": calendar_has_asof,
        "symbols_success": success,
        "symbols_with_asof": with_asof,
        "validation_status": validation,
        "model_smoke_status": smoke,
    }


@dataclass
class FPALAPaths:
    root: Path = ROOT
    output_root: Path = DEFAULT_OUTPUT_ROOT
    candidate_root: Path = DEFAULT_CANDIDATE_ROOT
    formal_provider_calendar: Path = DEFAULT_FORMAL_PROVIDER_CALENDAR
    qlib_accepted_latest: Path = DEFAULT_QLIB_ACCEPTED_LATEST
    legacy_latest: Path = DEFAULT_LEGACY_LATEST
    dapr18_signal_latest: Path = DEFAULT_DAPR18_SIGNAL_LATEST
    readonly_snapshot_latest: Path = DEFAULT_READONLY_SNAPSHOT_LATEST
    agent_prompt_latest: Path = DEFAULT_AGENT_PROMPT_LATEST
    installed_cron: Path = DEFAULT_INSTALLED_CRON
    pending_asof: Path = DEFAULT_PENDING_ASOF
    candidate_dir: Path | None = None
    accepted_payload_path: Path | None = None


@dataclass
class FPALAFlags:
    enabled: bool
    no_publish: bool
    allow_formal_provider_publish: bool
    allow_accepted_latest_switch: bool
    exact_authorization_id: str
    legacy_provider_publish_enabled: bool = False
    dapr18_authorization_present: bool = False

    @property
    def exact_authorization_present(self) -> bool:
        return bool(self.exact_authorization_id.strip())


def read_latest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return read_json(path)


def build_contracts(
    *,
    target_asof: str,
    paths: FPALAPaths,
    flags: FPALAFlags,
    candidate_dir: Path | None,
    readiness: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], str]:
    qlib_latest = read_latest(paths.qlib_accepted_latest)
    current_asof = json_asof(qlib_latest)
    current_run_id = str(qlib_latest.get("run_id") or Path(str(qlib_latest.get("run_dir") or "")).name)
    formal_calendar_max = calendar_max(paths.formal_provider_calendar)
    formal_covers = bool(formal_calendar_max >= target_asof)
    candidate_check = candidate_validation(candidate_dir, readiness, target_asof)
    accepted_payload = paths.accepted_payload_path
    accepted_payload_exists = bool(accepted_payload and accepted_payload.exists())
    accepted_payload_path = rel(accepted_payload, root=paths.root) if accepted_payload else ""

    candidate_contract = {
        "candidate_dir": rel(candidate_dir, root=paths.root) if candidate_dir else "",
        "candidate_source": str(readiness.get("candidate_source") or ""),
        "candidate_asof": str(readiness.get("candidate_asof") or readiness.get("asof") or target_asof if readiness else ""),
        "staged_provider_calendar_max": str(readiness.get("staged_provider_calendar_max") or readiness.get("calendar_max") or ""),
        "staged_provider_calendar_has_asof": bool(readiness.get("staged_provider_calendar_has_asof") or readiness.get("calendar_has_asof") or False),
        "candidate_normalized_symbols_expected": int(readiness.get("candidate_normalized_symbols_expected") or readiness.get("symbols_expected") or 150 if readiness else 0),
        "candidate_normalized_symbols_success": int(readiness.get("candidate_normalized_symbols_success") or readiness.get("symbols_success") or 0),
        "candidate_normalized_symbols_with_asof": int(readiness.get("candidate_normalized_symbols_with_asof") or readiness.get("symbols_with_asof") or 0),
        "staged_provider_validation_status": str(readiness.get("staged_provider_validation_status") or readiness.get("provider_validation_status") or ""),
        "candidate_model_smoke_status": str(readiness.get("candidate_model_smoke_status") or readiness.get("model_smoke_status") or ""),
        "production_allowed": bool(readiness.get("production_allowed")) if readiness else False,
        "publish_latest_authorized": bool(readiness.get("publish_latest_authorized")) if readiness else False,
        "formal_provider_mutated": bool(readiness.get("formal_provider_mutated")) if readiness else False,
        "formal_normalized_mutated": bool(readiness.get("formal_normalized_mutated")) if readiness else False,
        "latest_signal_updated": bool(readiness.get("latest_signal_updated")) if readiness else False,
        "forbidden_actions": readiness.get("forbidden_actions") if isinstance(readiness.get("forbidden_actions"), dict) else {},
        "validation": candidate_check,
    }

    provider_status = "not_required_already_covers_target"
    if not formal_covers:
        provider_status = "ready_no_publish" if candidate_check["ok"] else "blocked_candidate_invalid"
    if not formal_covers and flags.allow_formal_provider_publish and flags.no_publish and not flags.exact_authorization_present:
        provider_status = "blocked_requires_exact_authorization"

    formal_provider_contract = {
        "formal_provider_path": rel(paths.formal_provider_calendar.parent.parent, root=paths.root),
        "calendar_path": rel(paths.formal_provider_calendar, root=paths.root),
        "calendar_max_before": formal_calendar_max,
        "calendar_hash_before": sha256_file(paths.formal_provider_calendar),
        "expected_target_asof": target_asof,
        "formal_provider_covers_target": formal_covers,
        "expected_write_set_summary": "formal provider calendar/instruments/features only in future exact authorization route",
        "rollback_required": True,
        "before_fingerprint_required": True,
        "after_fingerprint_required": True,
        "diff_required": True,
        "provider_validation_required": True,
        "calendar_validation_required": True,
        "publish_preflight_status": provider_status,
        "publish_allowed_by_flags": False,
        "would_publish_if_authorized": bool(not formal_covers and candidate_check["ok"]),
    }

    if current_asof == target_asof:
        switch_status = "not_required_already_aligned"
    elif not formal_covers:
        switch_status = "blocked_formal_provider_not_ready"
    elif not accepted_payload_exists:
        switch_status = "blocked_accepted_payload_missing"
    else:
        switch_status = "ready_no_publish"
    if current_asof != target_asof and flags.allow_accepted_latest_switch and flags.no_publish and not flags.exact_authorization_present:
        switch_status = "blocked_requires_exact_authorization"

    accepted_latest_contract = {
        "accepted_latest_pointer_path": rel(paths.qlib_accepted_latest, root=paths.root),
        "current_asof": current_asof,
        "current_run_id": current_run_id,
        "current_hash": sha256_file(paths.qlib_accepted_latest),
        "target_asof": target_asof,
        "target_run_id": Path(str(paths.accepted_payload_path or "")).name if paths.accepted_payload_path else "",
        "candidate_payload_path": accepted_payload_path,
        "candidate_payload_exists": accepted_payload_exists,
        "formal_provider_covers_target": formal_covers,
        "QlibOptionCSignalReader_validation_required": True,
        "rollback_required": True,
        "before_fingerprint_required": True,
        "after_fingerprint_required": True,
        "diff_required": True,
        "switch_preflight_status": switch_status,
        "switch_allowed_by_flags": False,
        "would_switch_if_authorized": bool(current_asof != target_asof and formal_covers and accepted_payload_exists),
    }

    protected = {
        "formal_provider_calendar": fingerprint(paths.formal_provider_calendar, root=paths.root),
        "qlib_accepted_latest": fingerprint(paths.qlib_accepted_latest, root=paths.root),
        "legacy_latest": fingerprint(paths.legacy_latest, root=paths.root),
        "dapr18_signal_latest": fingerprint(paths.dapr18_signal_latest, root=paths.root),
        "readonly_snapshot_latest": fingerprint(paths.readonly_snapshot_latest, root=paths.root),
        "agent_prompt_latest": fingerprint(paths.agent_prompt_latest, root=paths.root),
        "installed_cron": fingerprint(paths.installed_cron, root=paths.root),
    }
    return candidate_contract, formal_provider_contract, accepted_latest_contract, protected, current_asof


def pending_target(paths: FPALAPaths) -> str:
    if not paths.pending_asof.exists():
        return ""
    try:
        payload = read_json(paths.pending_asof)
    except Exception:
        return ""
    return str(payload.get("asof") or payload.get("pending_asof") or "")


def determine_status(
    *,
    target_asof: str,
    flags: FPALAFlags,
    candidate_contract: dict[str, Any],
    formal_provider_contract: dict[str, Any],
    accepted_latest_contract: dict[str, Any],
    pending_asof: str,
    today_wait: bool,
) -> tuple[str, bool, str, str, str]:
    if not flags.enabled:
        return (
            "disabled_by_default",
            True,
            "FPALA automation is disabled by default.",
            "",
            "set ENABLE_TW_FPALA_FORMAL_ACCEPTED_LATEST_AUTOMATION=true or pass --enable for no-publish readiness",
        )
    if today_wait:
        return ("today_data_window_wait", True, "Target is same-day before the configured Taipei data window.", "", "wait_for_next_scheduled_run")
    if pending_asof and pending_asof == target_asof:
        return ("pending_retry_wait", True, "Pending asof exists and should be retried by scheduled automation.", "next scheduled daily-auto should retry pending asof", "observe_scheduled_retry")
    if candidate_contract.get("validation", {}).get("forbidden_violation"):
        return ("blocked_forbidden_scope_violation", False, "Provider candidate contains a forbidden action flag.", "", "repair_candidate_or_contract")
    if formal_provider_contract["formal_provider_covers_target"] and accepted_latest_contract["current_asof"] == target_asof:
        return ("already_aligned_idempotent_noop", True, "Formal provider and qlib accepted latest already match target_asof.", "", "no_action")
    if not candidate_contract.get("validation", {}).get("ok") and candidate_contract.get("validation", {}).get("missing"):
        return ("blocked_candidate_missing", False, "No provider candidate readiness exists for target_asof.", "wait for provider candidate refresh under scheduled automation", "observe_or_open_candidate_repair")
    if not candidate_contract.get("validation", {}).get("ok"):
        return ("blocked_candidate_invalid", False, "Provider candidate readiness failed validation.", "repair provider candidate in a separate no-publish route", "open_candidate_validation_repair")
    if formal_provider_contract["publish_preflight_status"] == "blocked_requires_exact_authorization" or accepted_latest_contract["switch_preflight_status"] == "blocked_requires_exact_authorization":
        return ("blocked_requires_exact_authorization", False, "Requested mutation flags require exact authorization and are still no-publish in FPALA2.", "", "request_exact_authorization_in_later_route")
    if not formal_provider_contract["formal_provider_covers_target"]:
        if not flags.allow_formal_provider_publish:
            return ("candidate_ready_no_publish", True, "Provider candidate is ready; no formal provider publish preflight was requested.", "", "continue_no_publish_validation")
        if formal_provider_contract["publish_preflight_status"] == "ready_no_publish":
            return ("provider_publish_preflight_ready_no_publish", True, "Provider candidate is ready; formal provider publish remains no-publish.", "", "continue_no_publish_validation")
        return ("blocked_formal_provider_not_ready", False, "Formal provider does not cover target_asof.", "", "prepare_formal_provider_preflight")
    if accepted_latest_contract["switch_preflight_status"] == "blocked_accepted_payload_missing":
        return ("blocked_accepted_payload_missing", False, "Accepted latest target payload is missing.", "", "build_or_validate_accepted_payload_no_publish")
    if accepted_latest_contract["switch_preflight_status"] == "ready_no_publish":
        return ("accepted_latest_preflight_ready_no_publish", True, "Accepted latest switch preflight is ready but remains no-publish.", "", "continue_no_publish_validation")
    return ("candidate_ready_no_publish", True, "Provider candidate is ready; no-publish prevents mutation.", "", "continue_no_publish_validation")


def build_decision(
    *,
    target_asof: str,
    job_id: str,
    paths: FPALAPaths,
    flags: FPALAFlags,
    asof_source: str = "cli",
    today_wait: bool = False,
) -> dict[str, Any]:
    candidate_dir, readiness = find_candidate_readiness(paths.candidate_root, target_asof, paths.candidate_dir)
    candidate_contract, formal_provider_contract, accepted_latest_contract, protected, current_asof = build_contracts(
        target_asof=target_asof,
        paths=paths,
        flags=flags,
        candidate_dir=candidate_dir,
        readiness=readiness,
    )
    forbidden = forbidden_scope_audit()
    status, ok, message, retry_hint, next_action = determine_status(
        target_asof=target_asof,
        flags=flags,
        candidate_contract=candidate_contract,
        formal_provider_contract=formal_provider_contract,
        accepted_latest_contract=accepted_latest_contract,
        pending_asof=pending_target(paths),
        today_wait=today_wait,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": utc_now_iso(),
        "job_id": job_id,
        "target_asof": target_asof,
        "asof_source": asof_source,
        "status": status,
        "ok": ok,
        "message": message,
        "next_retry_hint": retry_hint,
        "recommended_next_action": next_action,
        "flags": {
            "enabled": flags.enabled,
            "no_publish": flags.no_publish,
            "allow_formal_provider_publish": flags.allow_formal_provider_publish,
            "allow_accepted_latest_switch": flags.allow_accepted_latest_switch,
            "exact_authorization_present": flags.exact_authorization_present,
            "exact_authorization_id": flags.exact_authorization_id,
            "legacy_provider_publish_enabled": flags.legacy_provider_publish_enabled,
            "dapr18_authorization_present": flags.dapr18_authorization_present,
        },
        "candidate_contract": candidate_contract,
        "formal_provider_contract": formal_provider_contract,
        "accepted_latest_contract": accepted_latest_contract,
        "protected_pointer_fingerprints": protected,
        "forbidden_scope_audit": forbidden,
        "status_evidence": {
            "current_accepted_latest_asof": current_asof,
            "formal_provider_calendar_max": formal_provider_contract["calendar_max_before"],
            "candidate_validation_errors": candidate_contract.get("validation", {}).get("errors", []),
            "pending_asof": pending_target(paths),
            "today_wait": today_wait,
        },
    }


def parse_hhmm(raw: str) -> time:
    try:
        hour_text, minute_text = raw.split(":", 1)
        return time(hour=int(hour_text), minute=int(minute_text))
    except Exception as exc:
        raise argparse.ArgumentTypeError("--same-day-wait-until-taipei must be HH:MM") from exc


def parse_taipei_datetime(raw: str) -> datetime:
    value = raw.strip()
    if not value:
        return now_utc().astimezone(TAIPEI)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=TAIPEI)
    return parsed.astimezone(TAIPEI)


def compute_today_wait(target_asof: str, *, taipei_now: datetime, wait_until: time, enabled: bool) -> bool:
    if not enabled:
        return False
    return target_asof == taipei_now.date().isoformat() and taipei_now.time() < wait_until


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build FPALA2 no-publish formal provider / accepted latest decision.")
    parser.add_argument("--target-asof", required=True)
    parser.add_argument("--job-id", default="")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--enable", action="store_true", default=env_bool("ENABLE_TW_FPALA_FORMAL_ACCEPTED_LATEST_AUTOMATION", False))
    parser.add_argument("--no-publish", action="store_true", default=env_bool("TW_FPALA_NO_PUBLISH", True))
    parser.add_argument("--allow-formal-provider-publish", action="store_true", default=env_bool("TW_FPALA_ALLOW_FORMAL_PROVIDER_PUBLISH", False))
    parser.add_argument("--allow-accepted-latest-switch", action="store_true", default=env_bool("TW_FPALA_ALLOW_ACCEPTED_LATEST_SWITCH", False))
    parser.add_argument("--exact-authorization-id", default=os.getenv("TW_FPALA_EXACT_AUTHORIZATION_ID", ""))
    parser.add_argument("--candidate-dir", default="")
    parser.add_argument("--accepted-payload-path", default="")
    parser.add_argument("--taipei-now", default=os.getenv("TW_FPALA_TAIPEI_NOW", ""))
    parser.add_argument("--same-day-wait-until-taipei", type=parse_hhmm, default=parse_hhmm(os.getenv("TW_FPALA_SAME_DAY_WAIT_UNTIL_TAIPEI", "20:30")))
    parser.add_argument("--disable-same-day-window-wait", action="store_true", default=env_bool("TW_FPALA_DISABLE_SAME_DAY_WINDOW_WAIT", False))
    parser.add_argument("--today-data-window-wait", action="store_true", default=False)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    job_id = args.job_id.strip() or f"fpala2_no_publish_orchestrator_precheck_{args.target_asof.replace('-', '')}_{now_utc().strftime('%Y%m%dT%H%M%SZ')}"
    output_root = resolve_path(args.output_root)
    job_dir = output_root / job_id
    paths = FPALAPaths(
        output_root=output_root,
        candidate_dir=resolve_path(args.candidate_dir) if args.candidate_dir.strip() else None,
        accepted_payload_path=resolve_path(args.accepted_payload_path) if args.accepted_payload_path.strip() else None,
    )
    flags = FPALAFlags(
        enabled=bool(args.enable),
        no_publish=bool(args.no_publish),
        allow_formal_provider_publish=bool(args.allow_formal_provider_publish),
        allow_accepted_latest_switch=bool(args.allow_accepted_latest_switch),
        exact_authorization_id=str(args.exact_authorization_id or ""),
        legacy_provider_publish_enabled=env_bool("TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH", False),
        dapr18_authorization_present=bool(os.getenv("TW_DAPR18_EXACT_AUTHORIZATION_ID", "").strip()),
    )
    taipei_now = parse_taipei_datetime(args.taipei_now)
    today_wait = bool(args.today_data_window_wait) or compute_today_wait(
        args.target_asof,
        taipei_now=taipei_now,
        wait_until=args.same_day_wait_until_taipei,
        enabled=not bool(args.disable_same_day_window_wait),
    )
    decision = build_decision(target_asof=args.target_asof, job_id=job_id, paths=paths, flags=flags, today_wait=today_wait)
    decision["status_evidence"]["taipei_now"] = taipei_now.isoformat(timespec="seconds")
    decision["status_evidence"]["same_day_wait_until_taipei"] = args.same_day_wait_until_taipei.strftime("%H:%M")
    write_json(job_dir / "decision.json", decision)
    print(json.dumps(decision, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if decision.get("ok") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
