#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OPS_ROOT = ROOT / "data_tw/ops/daily_auto_update"
CRON_PATH = OPS_ROOT / "tw-daily-auto-update.installed.cron"
CRON_LOG = OPS_ROOT / "cron.log"
FINMIND_SEGMENT_CACHE_ROOT = OPS_ROOT / "finmind_segment_cache"
FULL_SCOPE_SEGMENTS = {"daily_price", "corporate_actions", "institutional", "margin", "monthly_revenue", "valuation"}


def is_daily_auto_cron_entry(line: str) -> bool:
    """Recognize both the legacy runner and the registered task dispatcher."""
    value = str(line or "")
    return "run_daily_tw_stock_auto_update.py" in value or (
        "scripts/run_tw_task.py" in value
        and "--request configs/tasks/daily_update" in value
    )


def cron_entry_scope(line: str) -> str:
    """Read scope from an inline legacy env or from the task request identity."""
    value = str(line or "")
    match = re.search(r"TW_DAILY_AUTO_FINMIND_SCOPE=(\w+)", value)
    if match:
        return match.group(1)
    if "configs/tasks/daily_update_base.yaml" in value:
        return "daily"
    if "configs/tasks/daily_update.yaml" in value:
        return "full"
    return "unspecified"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def path_origin_issue(raw_path: str) -> str:
    raw = str(raw_path or "").strip()
    if not raw:
        return "missing_path"
    path = Path(raw)
    resolved = (path if path.is_absolute() else ROOT / path).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return "outside_repo"
    try:
        resolved.relative_to(OPS_ROOT.resolve())
    except ValueError:
        return "outside_daily_auto_ops"
    if not resolved.exists() or not resolved.is_file():
        return "missing_file"
    return ""


def cache_origin_issues(quota_control: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    events = quota_control.get("cache_events") if isinstance(quota_control.get("cache_events"), dict) else {}
    for segment, event in events.items():
        if not isinstance(event, dict):
            continue
        cache = event.get("cache") if isinstance(event.get("cache"), dict) else {}
        issues = {
            "stdout_path": path_origin_issue(str(cache.get("stdout_path") or "")),
            "stderr_path": path_origin_issue(str(cache.get("stderr_path") or "")),
        }
        issues = {key: value for key, value in issues.items() if value}
        if issues:
            out[str(segment)] = {
                "action": event.get("action", ""),
                "issues": issues,
                "stdout_path": cache.get("stdout_path", ""),
                "stderr_path": cache.get("stderr_path", ""),
            }
    return out


def active_segment_cache_origin_issues() -> dict[str, Any]:
    out: dict[str, Any] = {}
    if not FINMIND_SEGMENT_CACHE_ROOT.exists():
        return out
    for path in sorted(FINMIND_SEGMENT_CACHE_ROOT.glob("*.json")):
        payload = read_json(path)
        issues = {
            "stdout_path": path_origin_issue(str(payload.get("stdout_path") or "")),
            "stderr_path": path_origin_issue(str(payload.get("stderr_path") or "")),
        }
        issues = {key: value for key, value in issues.items() if value}
        if issues:
            out[path.name] = {
                "issues": issues,
                "stdout_path": payload.get("stdout_path", ""),
                "stderr_path": payload.get("stderr_path", ""),
            }
    return out


def finmind_summary(path: Path) -> dict[str, Any]:
    payload = read_json(path)

    def classify_segment_status(segment_status: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for segment, status in segment_status.items():
            if not isinstance(status, dict):
                continue
            row = dict(status)
            if not row.get("provider_error"):
                stderr_path = ROOT / str(row.get("stderr_path") or "")
                stderr = stderr_path.read_text(encoding="utf-8", errors="ignore").lower() if stderr_path.is_file() else ""
                if "402" in stderr or "payment required" in stderr:
                    row["provider_error"] = "provider_402_quota_or_payment_required"
                elif "429" in stderr or "too many requests" in stderr or "rate limit" in stderr:
                    row["provider_error"] = "provider_rate_limited"
                elif "read timed out" in stderr or "readtimeout" in stderr or "timeout" in stderr:
                    row["provider_error"] = "provider_timeout"
            out[segment] = row
        return out

    def section(name: str, archived_key: str = "") -> dict[str, Any]:
        item = payload.get(name) if isinstance(payload.get(name), dict) else {}
        return {
            "count": int(item.get("count") or 0),
            "date_min": item.get("date_min"),
            "date_max": item.get("date_max"),
            "symbol_count": len(item.get("symbols") or []),
            "archived_count": int(payload.get(archived_key) or 0) if archived_key else 0,
        }

    quota_control = payload.get("quota_control") if isinstance(payload.get("quota_control"), dict) else {}
    return {
        "path": rel(path),
        "archive": section("archive", "archived_count"),
        "institutional_trades": section("institutional_trades", "institutional_trades_archived_count"),
        "margin_trading": section("margin_trading", "margin_trading_archived_count"),
        "corporate_actions": section("corporate_actions", "corporate_actions_archived_count"),
        "monthly_revenue": section("monthly_revenue", "monthly_revenue_archived_count"),
        "valuation": section("valuation", "valuation_archived_count"),
        "segment_status": classify_segment_status(payload.get("segment_status")) if isinstance(payload.get("segment_status"), dict) else {},
        "quota_control": quota_control,
        "orthogonal_batch_control": payload.get("orthogonal_batch_control") if isinstance(payload.get("orthogonal_batch_control"), dict) else {},
        "cache_origin_issues": cache_origin_issues(quota_control),
    }


def cron_finmind_scopes(cron_text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in cron_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or not is_daily_auto_cron_entry(line):
            continue
        schedule = " ".join(line.split()[:5])
        rows.append({
            "schedule": schedule,
            "scope": cron_entry_scope(line),
            "line": line,
        })
    return rows


def cron_ador_config(cron_rows: list[dict[str, Any]], cron_text: str) -> dict[str, Any]:
    required_scopes = {"daily", "full"}
    scoped_rows = [row for row in cron_rows if row.get("scope") in required_scopes]

    def flag(line: str, name: str, value: str) -> bool:
        return re.search(rf"(^|\s){re.escape(name)}={re.escape(value)}(\s|$)", line) is not None

    rows: list[dict[str, Any]] = []
    for row in scoped_rows:
        line = str(row.get("line") or "")
        rows.append({
            "schedule": row.get("schedule", ""),
            "scope": row.get("scope", "unspecified"),
            "ador_no_publish_gate_enabled": flag(line, "ENABLE_TW_ADOR_NO_PUBLISH_ORCHESTRATION_DRY_RUN", "true"),
            "ador_dry_run_true": flag(line, "TW_ADOR_NO_PUBLISH_ORCHESTRATION_DRY_RUN", "true"),
            "agent_prompt_dry_run_true": flag(line, "TW_AGENT_DAILY_PROMPT_DRY_RUN", "true"),
            "agent_prompt_publish_disabled": flag(line, "ENABLE_TW_AGENT_DAILY_PROMPT_PUBLISH", "false"),
            "agent_prompt_publish_latest_disabled": flag(line, "TW_AGENT_DAILY_PROMPT_PUBLISH_LATEST", "false"),
            "disable_ador_cli_present": "--disable-ador-no-publish-orchestration-dry-run" in line,
            "agent_prompt_publish_enabled_true": flag(line, "ENABLE_TW_AGENT_DAILY_PROMPT_PUBLISH", "true"),
            "agent_prompt_publish_latest_true": flag(line, "TW_AGENT_DAILY_PROMPT_PUBLISH_LATEST", "true"),
        })
    scopes_present = {str(row.get("scope")) for row in rows}
    both_daily_full_present = required_scopes.issubset(scopes_present)
    gate_enabled = bool(rows) and both_daily_full_present and all(row["ador_no_publish_gate_enabled"] for row in rows)
    ador_dry_run_true = bool(rows) and both_daily_full_present and all(row["ador_dry_run_true"] for row in rows)
    agent_prompt_dry_run_true = bool(rows) and both_daily_full_present and all(row["agent_prompt_dry_run_true"] for row in rows)
    publish_disabled = bool(rows) and both_daily_full_present and all(row["agent_prompt_publish_disabled"] for row in rows)
    publish_latest_disabled = bool(rows) and both_daily_full_present and all(row["agent_prompt_publish_latest_disabled"] for row in rows)
    forbidden_controls_absent = not any(
        row["disable_ador_cli_present"] or row["agent_prompt_publish_enabled_true"] or row["agent_prompt_publish_latest_true"]
        for row in rows
    )
    formal_provider_gate_enabled = "TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH=true" in cron_text
    formal_provider_allow = "TW_FPALA_ALLOW_FORMAL_PROVIDER_PUBLISH=true" in cron_text
    accepted_latest_allow = "TW_FPALA_ALLOW_ACCEPTED_LATEST_SWITCH=true" in cron_text
    auth_match = re.search(r"(?:^|\n)TW_FPALA_EXACT_AUTHORIZATION_ID=(\S+)", cron_text)
    formal_authorization_id = auth_match.group(1) if auth_match else ""
    formal_authorization_valid = bool(
        re.match(r"^FPALA_AUTO_ACCEPTED_LATEST_DAILY_[A-Za-z0-9_:-]+$", formal_authorization_id)
    )
    formal_accepted_latest_authorized = bool(
        formal_provider_gate_enabled
        and formal_provider_allow
        and accepted_latest_allow
        and formal_authorization_valid
    )
    no_publish_safe = bool(
        rows
        and both_daily_full_present
        and all(row["ador_no_publish_gate_enabled"] for row in rows)
        and all(row["ador_dry_run_true"] for row in rows)
        and all(row["agent_prompt_publish_disabled"] for row in rows)
        and all(row["agent_prompt_publish_latest_disabled"] for row in rows)
        and not any(
            row["disable_ador_cli_present"]
            or row["agent_prompt_publish_enabled_true"]
            or row["agent_prompt_publish_latest_true"]
            for row in rows
        )
        and not formal_provider_gate_enabled
    )
    return {
        "cron_config_ador_scope_rows": rows,
        "cron_config_ador_daily_full_rows_present": both_daily_full_present,
        "cron_config_ador_no_publish_gate_enabled": gate_enabled,
        "cron_config_ador_dry_run_true": ador_dry_run_true,
        "cron_config_agent_prompt_dry_run_true": agent_prompt_dry_run_true,
        "cron_config_agent_prompt_publish_disabled": publish_disabled,
        "cron_config_agent_prompt_publish_latest_disabled": publish_latest_disabled,
        "cron_config_ador_forbidden_controls_absent": forbidden_controls_absent,
        "cron_config_ador_no_publish_safe_for_cron": no_publish_safe,
        "cron_config_formal_provider_gate_enabled": formal_provider_gate_enabled,
        "cron_config_formal_provider_authorization_id": formal_authorization_id,
        "cron_config_formal_accepted_latest_authorized": formal_accepted_latest_authorized,
        "cron_config_ador_safe_for_cron": bool(no_publish_safe or formal_accepted_latest_authorized),
    }


def summarize_ador_no_publish(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    keys = (
        "enabled",
        "attempted",
        "ok",
        "status",
        "dry_run",
        "agent_prompt_dry_run",
        "agent_prompt_publish_enabled",
        "agent_prompt_publish_latest",
        "source_readiness_state",
        "blocked_controls",
        "protected_paths_unchanged",
        "forbidden_actions_all_false",
    )
    return {key: payload.get(key) for key in keys if key in payload}


def collect_jobs(limit: int) -> list[dict[str, Any]]:
    job_paths = sorted(OPS_ROOT.glob("daily_tw_stock_auto_update_*/job.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    rows: list[dict[str, Any]] = []
    for path in job_paths[:limit]:
        job = read_json(path)
        job_dir = path.parent
        row: dict[str, Any] = {
            "job_id": job.get("job_id") or job_dir.name,
            "job_path": rel(path),
            "mtime": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat(),
            "status": job.get("status"),
            "asof": job.get("asof"),
            "finmind_scope": job.get("finmind_scope"),
            "full_orthogonal_refresh_required": bool(job.get("full_orthogonal_refresh_required")),
            "full_orthogonal_refresh_triggered": bool(job.get("full_orthogonal_refresh_triggered")),
            "taipei_now": job.get("taipei_now"),
            "asof_source": job.get("asof_source"),
            "finmind_update_triggered": bool(job.get("finmind_update_triggered")),
            "provider_publish_triggered": bool(job.get("provider_publish_triggered")),
            "latest_signal_updated": bool(job.get("latest_signal_updated")),
            "legacy_provider_publish_enabled": bool(job.get("legacy_provider_publish_enabled")),
            "strict_e4_readonly_chain_enabled": bool(job.get("strict_e4_readonly_chain_enabled")),
            "daily_source_inventory_path": job.get("daily_source_inventory_path", ""),
            "daily_full_capture_accounting": job.get("daily_full_capture_accounting", {}),
            "ador_no_publish_orchestration": summarize_ador_no_publish(job.get("ador_no_publish_orchestration")),
            "ador_no_publish_orchestration_warning": job.get("ador_no_publish_orchestration_warning", ""),
        }
        stdout = job_dir / "finmind_stdout.txt"
        if stdout.exists():
            row["finmind_stdout"] = finmind_summary(stdout)
        rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Readonly audit for installed TW daily auto scheduled jobs.")
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--out", default="")
    parser.add_argument(
        "--require-full-scope",
        action="store_true",
        help="Fail if installed cron has no full-scope daily-update entry.",
    )
    args = parser.parse_args()

    cron_text = CRON_PATH.read_text(encoding="utf-8") if CRON_PATH.exists() else ""
    jobs = collect_jobs(args.limit)
    real_finmind_jobs = [row for row in jobs if row.get("finmind_update_triggered") and row.get("finmind_stdout")]
    latest_real = real_finmind_jobs[0] if real_finmind_jobs else {}
    full_scope_real_jobs = [
        row for row in real_finmind_jobs
        if str(row.get("finmind_scope") or "") == "full"
        or bool(row.get("full_orthogonal_refresh_required"))
        or bool(row.get("full_orthogonal_refresh_triggered"))
    ]
    latest_full_scope_real = full_scope_real_jobs[0] if full_scope_real_jobs else {}
    # A later daily-scope retry must not hide the most recent full-scope
    # attempt.  Freshness uses the latest real job; the full-scope gate uses
    # the latest full-scope job independently.
    scope_assessment_job = latest_full_scope_real if args.require_full_scope else latest_real
    latest_stdout = scope_assessment_job.get("finmind_stdout") if isinstance(scope_assessment_job.get("finmind_stdout"), dict) else {}
    archive = latest_stdout.get("archive") if isinstance(latest_stdout.get("archive"), dict) else {}
    institutional = latest_stdout.get("institutional_trades") if isinstance(latest_stdout.get("institutional_trades"), dict) else {}
    margin = latest_stdout.get("margin_trading") if isinstance(latest_stdout.get("margin_trading"), dict) else {}
    segment_status = latest_stdout.get("segment_status") if isinstance(latest_stdout.get("segment_status"), dict) else {}
    provider_errors = {
        segment: status.get("provider_error")
        for segment, status in segment_status.items()
        if isinstance(status, dict) and status.get("provider_error")
    }
    cached_segments = sorted([
        segment
        for segment, status in segment_status.items()
        if isinstance(status, dict) and status.get("cached")
    ])
    segment_names = sorted(segment_status.keys())
    orthogonal_batch = latest_stdout.get("orthogonal_batch_control") if isinstance(latest_stdout.get("orthogonal_batch_control"), dict) else {}
    orthogonal_batch_status = str(orthogonal_batch.get("status") or "")
    orthogonal_batch_coverage = orthogonal_batch.get("coverage") if isinstance(orthogonal_batch.get("coverage"), dict) else {}
    base_full_segments = {"daily_price", "corporate_actions"}.issubset(set(segment_names))
    orthogonal_batch_observed = orthogonal_batch_status in {"success", "success_partial", "quota_exhausted_retry_next_day", "provider_timeout", "permission_denied"}
    latest_real_full_scope_segment_coverage_ok = FULL_SCOPE_SEGMENTS.issubset(set(segment_names)) or (base_full_segments and orthogonal_batch_observed)
    if FULL_SCOPE_SEGMENTS.issubset(set(segment_names)):
        latest_real_inferred_scope = "full"
    elif base_full_segments and orthogonal_batch_observed:
        latest_real_inferred_scope = "full_with_quota_aware_orthogonal_batch"
    elif segment_names == ["daily_price"]:
        latest_real_inferred_scope = "daily"
    else:
        latest_real_inferred_scope = "partial" if segment_names else "unknown"
    latest_full_scope_inferred_scope = latest_real_inferred_scope if latest_full_scope_real else "unknown"
    latest_overall_stdout = latest_real.get("finmind_stdout") if isinstance(latest_real.get("finmind_stdout"), dict) else {}
    overall_segment_names = sorted((latest_overall_stdout.get("segment_status") or {}).keys()) if isinstance(latest_overall_stdout.get("segment_status"), dict) else []
    if FULL_SCOPE_SEGMENTS.issubset(set(overall_segment_names)):
        latest_overall_inferred_scope = "full"
    elif overall_segment_names == ["daily_price"]:
        latest_overall_inferred_scope = "daily"
    elif overall_segment_names:
        latest_overall_inferred_scope = "partial"
    else:
        latest_overall_inferred_scope = "unknown"
    latest_real_cache_origin_issues = latest_stdout.get("cache_origin_issues") if isinstance(latest_stdout.get("cache_origin_issues"), dict) else {}
    active_cache_origin_issues = active_segment_cache_origin_issues()
    statuses = {}
    for row in jobs:
        statuses[str(row.get("status"))] = statuses.get(str(row.get("status")), 0) + 1
    cron_scope_rows = cron_finmind_scopes(cron_text)
    cron_scopes = sorted({row["scope"] for row in cron_scope_rows})
    cron_scope = "+".join(cron_scopes) if cron_scopes else "unspecified"
    cron_has_full_scope = any(row["scope"] == "full" for row in cron_scope_rows)
    cron_has_daily_scope = any(row["scope"] == "daily" for row in cron_scope_rows)
    full_scope_schedules = [row["schedule"] for row in cron_scope_rows if row["scope"] == "full"]
    daily_scope_schedules = [row["schedule"] for row in cron_scope_rows if row["scope"] == "daily"]
    cron_scope_schedule_collision = bool(set(full_scope_schedules) & set(daily_scope_schedules))
    ador_config = cron_ador_config(cron_scope_rows, cron_text)
    full_scope_real_run_gate_ok = (
        bool(latest_full_scope_real)
        and latest_real_inferred_scope in {"full", "full_with_quota_aware_orthogonal_batch"}
        and latest_real_full_scope_segment_coverage_ok
    ) if args.require_full_scope else True
    shadow_blocker = ""
    if args.require_full_scope and not latest_full_scope_real:
        shadow_blocker = "full_scope_real_run_not_observed"
    elif args.require_full_scope and not full_scope_real_run_gate_ok:
        shadow_blocker = "full_scope_real_run_incomplete"
    if args.require_full_scope and not cron_has_full_scope:
        primary_blocker = "cron_missing_full_scope_orthogonal_job"
    elif args.require_full_scope and cron_scope_schedule_collision:
        primary_blocker = "cron_daily_full_same_minute_lock_collision"
    elif not ador_config["cron_config_ador_safe_for_cron"]:
        primary_blocker = "cron_ador_no_publish_dry_run_gate_not_safe"
    elif active_cache_origin_issues:
        primary_blocker = "finmind_segment_cache_invalid_origin"
    elif "provider_402_quota_or_payment_required" in set(provider_errors.values()):
        primary_blocker = "finmind_provider_402_quota_or_payment_required"
    elif orthogonal_batch_status in {"quota_exhausted_retry_next_day", "provider_timeout", "permission_denied"}:
        primary_blocker = f"finmind_orthogonal_batch_{orthogonal_batch_status}"
    else:
        primary_blocker = ""
    result = {
        "schema_version": "rcpt15_r8_real_scheduled_job_audit_v1",
        "created_at": now(),
        "readonly_only": True,
        "real_data_pull_triggered_by_this_audit": False,
        "provider_publish_triggered_by_this_audit": False,
        "accepted_latest_switch_triggered_by_this_audit": False,
        "cron_installed": CRON_PATH.exists(),
        "cron_path": rel(CRON_PATH),
        "cron_log_path": rel(CRON_LOG),
        "cron_contains_daily_auto_entry": any(
            is_daily_auto_cron_entry(line) for line in cron_text.splitlines()
        ),
        "cron_config_finmind_scope": cron_scope,
        "cron_config_finmind_scope_rows": cron_scope_rows,
        "cron_has_daily_scope": cron_has_daily_scope,
        "cron_has_full_scope": cron_has_full_scope,
        "cron_daily_scope_schedules": daily_scope_schedules,
        "cron_full_scope_schedules": full_scope_schedules,
        "cron_scope_schedule_collision": cron_scope_schedule_collision,
        "cron_full_scope_required": bool(args.require_full_scope),
        "cron_full_scope_gate_ok": cron_has_full_scope if args.require_full_scope else True,
        "cron_config_skip_finmind_validate": "TW_DAILY_AUTO_SKIP_FINMIND_VALIDATE=true" in cron_text,
        "cron_config_legacy_provider_gate_enabled": "TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH=true" in cron_text,
        "cron_config_strict_e4_gate_enabled": "TW_DAILY_AUTO_ENABLE_STRICT_E4_READONLY_CHAIN=true" in cron_text,
        **ador_config,
        "job_count_checked": len(jobs),
        "status_counts": statuses,
        "latest_job": jobs[0] if jobs else {},
        "latest_job_ador_no_publish_orchestration": jobs[0].get("ador_no_publish_orchestration", {}) if jobs else {},
        "latest_real_finmind_job": latest_real,
        "latest_full_scope_real_finmind_job": latest_full_scope_real,
        "full_scope_real_job_count": len(full_scope_real_jobs),
        "latest_real_finmind_job_ador_no_publish_orchestration": latest_real.get("ador_no_publish_orchestration", {}) if latest_real else {},
        "latest_real_finmind_daily_price": archive,
        "latest_real_finmind_institutional": institutional,
        "latest_real_finmind_margin": margin,
        "latest_real_finmind_segment_status": segment_status,
        "latest_real_finmind_segments": segment_names,
        "latest_real_finmind_inferred_scope": latest_overall_inferred_scope,
        "latest_full_scope_real_finmind_inferred_scope": latest_full_scope_inferred_scope,
        "latest_real_finmind_full_scope_segments_required": sorted(FULL_SCOPE_SEGMENTS),
        "latest_real_finmind_full_scope_segment_coverage_ok": latest_real_full_scope_segment_coverage_ok,
        "latest_real_finmind_base_full_segments_present": base_full_segments,
        "latest_real_finmind_orthogonal_batch_observed": orthogonal_batch_observed,
        "latest_real_finmind_cache_origin_issues": latest_real_cache_origin_issues,
        "active_finmind_segment_cache_origin_issues": active_cache_origin_issues,
        "full_scope_real_run_gate_ok": full_scope_real_run_gate_ok,
        "full_scope_shadow_nonblocking": bool(shadow_blocker and not primary_blocker),
        "full_scope_shadow_blocker": shadow_blocker,
        "latest_real_finmind_provider_errors": provider_errors,
        "latest_real_finmind_cached_segments": cached_segments,
        "latest_real_finmind_orthogonal_batch_control": orthogonal_batch,
        "latest_real_finmind_orthogonal_batch_status": orthogonal_batch_status,
        "latest_real_finmind_orthogonal_batch_coverage": orthogonal_batch_coverage,
        "latest_real_finmind_orthogonal_batch_full_ready": orthogonal_batch_status == "success",
        "latest_real_finmind_orthogonal_batch_partial": orthogonal_batch_status == "success_partial",
        "latest_real_finmind_orthogonal_batch_cooldown": orthogonal_batch_status == "quota_exhausted_retry_next_day",
        "scheduler_running_evidence": bool(
            jobs
            and CRON_PATH.exists()
            and any(is_daily_auto_cron_entry(line) for line in cron_text.splitlines())
        ),
        "daily_price_captured": bool(archive.get("count", 0) and archive.get("date_max")),
        "institutional_captured": bool(institutional.get("count", 0) and institutional.get("date_max")),
        "margin_captured": bool(margin.get("count", 0) and margin.get("date_max")),
        "primary_blocker": primary_blocker,
        "jobs": jobs,
    }
    out_path = Path(args.out) if args.out else ROOT / "data_tw/experiments/risk_control_policy_2022/rcpt15_r8_real_scheduled_job_audit/real_scheduled_job_audit.json"
    write_json(out_path, result)
    ok = bool(
        result["cron_full_scope_gate_ok"]
        and result["cron_config_ador_safe_for_cron"]
        and not result["cron_scope_schedule_collision"]
        and not active_cache_origin_issues
    )
    print(json.dumps({"ok": ok, "out": rel(out_path), "scheduler_running_evidence": result["scheduler_running_evidence"], "cron_config_finmind_scope": cron_scope, "cron_config_ador_safe_for_cron": result["cron_config_ador_safe_for_cron"], "primary_blocker": result["primary_blocker"], "full_scope_shadow_blocker": result["full_scope_shadow_blocker"], "full_scope_shadow_nonblocking": result["full_scope_shadow_nonblocking"]}, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
