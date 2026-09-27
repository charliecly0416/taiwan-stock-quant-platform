#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "fpala.formal_accepted_latest_automation_decision.v1"
VALIDATION_SCHEMA_VERSION = "fpala.no_publish_decision_validation.v1"

VALID_STATUSES = {
    "disabled_by_default",
    "today_data_window_wait",
    "pending_retry_wait",
    "already_aligned_idempotent_noop",
    "candidate_ready_no_publish",
    "provider_publish_preflight_ready_no_publish",
    "accepted_latest_preflight_ready_no_publish",
    "blocked_candidate_missing",
    "blocked_candidate_invalid",
    "blocked_formal_provider_not_ready",
    "blocked_accepted_payload_missing",
    "blocked_requires_exact_authorization",
    "blocked_forbidden_scope_violation",
}

TOP_LEVEL_REQUIRED = {
    "schema_version",
    "created_at",
    "job_id",
    "target_asof",
    "status",
    "ok",
    "flags",
    "candidate_contract",
    "formal_provider_contract",
    "accepted_latest_contract",
    "protected_pointer_fingerprints",
    "forbidden_scope_audit",
    "status_evidence",
}

CANDIDATE_REQUIRED = {
    "candidate_dir",
    "candidate_asof",
    "staged_provider_calendar_max",
    "staged_provider_calendar_has_asof",
    "candidate_normalized_symbols_expected",
    "candidate_normalized_symbols_success",
    "candidate_normalized_symbols_with_asof",
    "staged_provider_validation_status",
    "candidate_model_smoke_status",
    "production_allowed",
    "publish_latest_authorized",
    "formal_provider_mutated",
    "formal_normalized_mutated",
    "latest_signal_updated",
    "forbidden_actions",
    "validation",
}

FORMAL_PROVIDER_REQUIRED = {
    "formal_provider_path",
    "calendar_path",
    "calendar_max_before",
    "calendar_hash_before",
    "expected_target_asof",
    "formal_provider_covers_target",
    "publish_preflight_status",
    "publish_allowed_by_flags",
    "would_publish_if_authorized",
}

ACCEPTED_LATEST_REQUIRED = {
    "accepted_latest_pointer_path",
    "current_asof",
    "current_run_id",
    "current_hash",
    "target_asof",
    "target_run_id",
    "candidate_payload_path",
    "candidate_payload_exists",
    "formal_provider_covers_target",
    "switch_preflight_status",
    "switch_allowed_by_flags",
    "would_switch_if_authorized",
}

PROTECTED_REQUIRED = {
    "formal_provider_calendar",
    "qlib_accepted_latest",
    "legacy_latest",
    "dapr18_signal_latest",
    "readonly_snapshot_latest",
    "agent_prompt_latest",
    "installed_cron",
}

MUTATION_CANDIDATE_FLAGS = {
    "production_allowed",
    "publish_latest_authorized",
    "formal_provider_mutated",
    "formal_normalized_mutated",
    "latest_signal_updated",
}


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")


def check(condition: bool, code: str, message: str, errors: list[dict[str, str]], warnings: list[dict[str, str]] | None = None, severity: str = "error") -> None:
    if condition:
        return
    item = {"code": code, "message": message}
    if severity == "warning" and warnings is not None:
        warnings.append(item)
    else:
        errors.append(item)


def missing_keys(payload: dict[str, Any], required: set[str]) -> list[str]:
    return sorted(key for key in required if key not in payload)


def any_true(mapping: Any) -> bool:
    return isinstance(mapping, dict) and any(value is True for value in mapping.values())


def validate_decision(decision: dict[str, Any], *, target_asof: str = "", expect_status: str = "") -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    missing_top = missing_keys(decision, TOP_LEVEL_REQUIRED)
    check(not missing_top, "missing_top_level_fields", f"missing={missing_top}", errors)

    status = str(decision.get("status") or "")
    target = target_asof or str(decision.get("target_asof") or "")
    flags = decision.get("flags") if isinstance(decision.get("flags"), dict) else {}
    candidate = decision.get("candidate_contract") if isinstance(decision.get("candidate_contract"), dict) else {}
    formal = decision.get("formal_provider_contract") if isinstance(decision.get("formal_provider_contract"), dict) else {}
    accepted = decision.get("accepted_latest_contract") if isinstance(decision.get("accepted_latest_contract"), dict) else {}
    fingerprints = decision.get("protected_pointer_fingerprints") if isinstance(decision.get("protected_pointer_fingerprints"), dict) else {}
    forbidden = decision.get("forbidden_scope_audit") if isinstance(decision.get("forbidden_scope_audit"), dict) else {}

    check(decision.get("schema_version") == SCHEMA_VERSION, "schema_version_mismatch", f"schema_version={decision.get('schema_version')}", errors)
    check(status in VALID_STATUSES, "unknown_status", f"status={status}", errors)
    if expect_status:
        check(status == expect_status, "status_mismatch", f"expected={expect_status} actual={status}", errors)
    if target_asof:
        check(str(decision.get("target_asof") or "") == target_asof, "target_asof_mismatch", f"expected={target_asof} actual={decision.get('target_asof')}", errors)

    check(flags.get("no_publish") is True, "no_publish_not_true", "FPALA validation only accepts no-publish decisions", errors)
    exact_present = flags.get("exact_authorization_present") is True and bool(str(flags.get("exact_authorization_id") or "").strip())
    mutation_requested = flags.get("allow_formal_provider_publish") is True or flags.get("allow_accepted_latest_switch") is True
    check(not mutation_requested or exact_present, "mutation_flag_without_exact_authorization", "publish/switch allow flags require exact FPALA authorization id", errors)
    exact_id = str(flags.get("exact_authorization_id") or "")
    check(not exact_id.startswith("DAPR18"), "dapr18_authorization_misused_for_fpala", f"exact_authorization_id={exact_id}", errors)
    check(not (flags.get("dapr18_authorization_present") is True and mutation_requested and not exact_present), "dapr18_authorization_claim_unlocks_fpala", "DAPR18 authorization cannot unlock FPALA publish/switch", errors)

    actions = forbidden.get("actions") if isinstance(forbidden.get("actions"), dict) else {}
    check(forbidden.get("all_false") is True, "forbidden_scope_audit_not_all_false", "forbidden_scope_audit.all_false must be true", errors)
    check(not any_true(actions), "forbidden_scope_action_true", "forbidden_scope_audit.actions contains true values", errors)

    check(not missing_keys(candidate, CANDIDATE_REQUIRED), "missing_candidate_contract_fields", f"missing={missing_keys(candidate, CANDIDATE_REQUIRED)}", errors)
    check(not missing_keys(formal, FORMAL_PROVIDER_REQUIRED), "missing_formal_provider_contract_fields", f"missing={missing_keys(formal, FORMAL_PROVIDER_REQUIRED)}", errors)
    check(not missing_keys(accepted, ACCEPTED_LATEST_REQUIRED), "missing_accepted_latest_contract_fields", f"missing={missing_keys(accepted, ACCEPTED_LATEST_REQUIRED)}", errors)
    check(not missing_keys(fingerprints, PROTECTED_REQUIRED), "missing_protected_pointer_fingerprints", f"missing={missing_keys(fingerprints, PROTECTED_REQUIRED)}", errors)

    for key in MUTATION_CANDIDATE_FLAGS:
        check(candidate.get(key) is not True, f"candidate_{key}_true", f"candidate_contract.{key} must not be true", errors)
    check(not any_true(candidate.get("forbidden_actions")), "candidate_forbidden_action_true", "candidate_contract.forbidden_actions contains true values", errors)
    check(formal.get("publish_allowed_by_flags") is not True, "formal_provider_publish_allowed_by_flags_true", "no-publish decision must not allow formal provider publish", errors)
    check(accepted.get("switch_allowed_by_flags") is not True, "accepted_latest_switch_allowed_by_flags_true", "no-publish decision must not allow accepted latest switch", errors)

    if candidate.get("candidate_dir") and not candidate.get("validation", {}).get("missing"):
        check(str(candidate.get("candidate_asof") or "") == target, "candidate_asof_mismatch", f"candidate_asof={candidate.get('candidate_asof')} target_asof={target}", errors)
        if candidate.get("validation", {}).get("ok") is True:
            check(candidate.get("staged_provider_calendar_has_asof") is True, "candidate_calendar_missing_target_asof", "valid candidate must report staged_provider_calendar_has_asof=true", errors)
            check(str(candidate.get("staged_provider_calendar_max") or "") >= target, "candidate_calendar_max_before_target", f"calendar_max={candidate.get('staged_provider_calendar_max')} target_asof={target}", errors)

    check(formal.get("expected_target_asof") in {"", target}, "formal_expected_target_asof_mismatch", f"formal expected={formal.get('expected_target_asof')} target={target}", errors)
    check(accepted.get("target_asof") in {"", target}, "accepted_target_asof_mismatch", f"accepted target={accepted.get('target_asof')} decision target={target}", errors)

    if status == "blocked_forbidden_scope_violation":
        check(any_true(candidate.get("forbidden_actions")) or candidate.get("validation", {}).get("forbidden_violation") is True, "forbidden_status_without_evidence", "blocked_forbidden_scope_violation needs candidate forbidden evidence", errors)
    if status == "already_aligned_idempotent_noop":
        check(formal.get("formal_provider_covers_target") is True, "aligned_status_formal_not_covering", "idempotent no-op requires formal provider coverage", errors)
        check(accepted.get("current_asof") == target, "aligned_status_accepted_not_target", "idempotent no-op requires accepted latest target_asof", errors)

    return {
        "schema_version": VALIDATION_SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ok": not errors,
        "decision_status": status,
        "target_asof": target,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate an FPALA no-publish decision artifact.")
    parser.add_argument("--decision", required=True)
    parser.add_argument("--target-asof", default="")
    parser.add_argument("--expect-status", default="")
    parser.add_argument("--output", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    decision_path = Path(args.decision)
    report = validate_decision(read_json(decision_path), target_asof=args.target_asof, expect_status=args.expect_status)
    if args.output:
        write_json(Path(args.output), report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
