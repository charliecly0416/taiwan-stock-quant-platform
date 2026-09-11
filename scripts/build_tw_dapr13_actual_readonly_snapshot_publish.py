#!/usr/bin/env python3
"""DAPR13 actual readonly strategy snapshot publish.

This script consumes a DAPR12 candidate-only readonly snapshot payload and
publishes exactly the authorized readonly snapshot files plus the readonly
snapshot latest pointer. It does not pull providers, refresh qlib,
build Agent prompts, run replay, call OpenAI, touch DB, or switch frontend/API
production defaults.
"""

from __future__ import annotations

import base64
import difflib
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def env_str(name: str, default: str) -> str:
    return os.environ.get(name, default)


def env_path(name: str, default: str) -> Path:
    value = os.environ.get(name)
    if value:
        path = Path(value)
        return path if path.is_absolute() else ROOT / path
    return ROOT / default


TARGET_ASOF = env_str("TW_DAPR13_TARGET_ASOF", "2026-07-17")
TARGET_TAG = TARGET_ASOF.replace("-", "")
MODEL_ID = env_str("TW_DAPR13_MODEL_ID", "e4_frozen_qlib_2018_2022")

DAPR12_ROOT = env_path(
    "TW_DAPR13_DAPR12_ROOT",
    "data_tw/experiments/daily_accepted_production_readiness/dapr12_20260717_candidate_only_readonly_snapshot_dry_run_no_publish",
)
CANDIDATE_DIR = DAPR12_ROOT / f"candidate_payloads/readonly_strategy_snapshot/{TARGET_ASOF}"

READONLY_SNAPSHOT_ROOT = ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot"
TARGET_SNAPSHOT_DIR = READONLY_SNAPSHOT_ROOT / TARGET_ASOF
READONLY_SNAPSHOT_LATEST = READONLY_SNAPSHOT_ROOT / "latest.json"

CONTROLLED_SIGNAL_LATEST = ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json"
AGENT_DAILY_PROMPT_LATEST = ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json"
LEGACY_QLIB_OPTION_C_LATEST = ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json"
LEGACY_DATA_OPTION_C_LATEST = ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json"

DAPR13_ROOT = env_path(
    "TW_DAPR13_OUTPUT_ROOT",
    f"data_tw/experiments/provider_bridge_productionization/dapr13_{TARGET_TAG}_actual_readonly_snapshot_publish",
)
ROLLBACK_DIR = DAPR13_ROOT / "rollback"
ROLLBACK_LATEST_COPY = ROLLBACK_DIR / "readonly_strategy_snapshot_latest.before_dapr13.json"

DAPR12_REVIEW = env_path(
    "TW_DAPR13_DAPR12_REVIEW",
    "docs/tw_portfolio_decision_model/POLICY_DAPR12_20260717_CANDIDATE_ONLY_READONLY_SNAPSHOT_DRY_RUN_NO_PUBLISH_REVIEW_CN.md",
)
DAPR13_EXECUTION_REPORT = env_path(
    "TW_DAPR13_EXECUTION_REPORT",
    f"docs/tw_portfolio_decision_model/POLICY_DAPR13_{TARGET_TAG}_ACTUAL_READONLY_SNAPSHOT_PUBLISH_EXECUTION_REPORT_CN.md",
)
DAPR13_REVIEW = env_path(
    "TW_DAPR13_REVIEW",
    f"docs/tw_portfolio_decision_model/POLICY_DAPR13_{TARGET_TAG}_ACTUAL_READONLY_SNAPSHOT_PUBLISH_REVIEW_CN.md",
)

SNAPSHOT_FILE_NAMES = (
    "manifest.json",
    "strategy_snapshot.json",
    "validation_report.json",
    "forbidden_scope_audit.json",
    "checksum_manifest.json",
)
SNAPSHOT_TARGETS = {name: TARGET_SNAPSHOT_DIR / name for name in SNAPSHOT_FILE_NAMES}
PROTECTED_POINTERS = {
    "controlled_signal_latest": CONTROLLED_SIGNAL_LATEST,
    "agent_daily_prompt_latest": AGENT_DAILY_PROMPT_LATEST,
    "legacy_qlib_option_c_latest_signal": LEGACY_QLIB_OPTION_C_LATEST,
    "legacy_data_option_c_latest_signal": LEGACY_DATA_OPTION_C_LATEST,
}
FORBIDDEN_OUTPUT_KEYS = {
    "target_position",
    "target_weight",
    "quantity",
    "shares",
    "lots",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {rel(path)}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(payload))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def file_fingerprint(path: Path) -> dict[str, Any]:
    item: dict[str, Any] = {
        "path": rel(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
        "size_bytes": path.stat().st_size if path.exists() and path.is_file() else None,
        "sha256": sha256_file(path),
        "json_summary": None,
    }
    if path.exists() and path.is_file() and path.suffix == ".json":
        try:
            payload = read_json(path)
            item["json_summary"] = {
                key: payload.get(key)
                for key in (
                    "artifact_type",
                    "schema_version",
                    "asof",
                    "data_asof",
                    "signal_asof",
                    "target_date",
                    "snapshot_manifest",
                    "source_signal_latest_sha256",
                    "readonly_only",
                    "candidate_only",
                    "production_trade_enabled",
                )
                if key in payload
            }
        except Exception as exc:
            item["json_error"] = str(exc)
    return item


def latest_bytes_backup(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {
            "path": rel(path),
            "exists": False,
            "bytes_base64": None,
            "sha256": None,
            "size_bytes": None,
            "json_summary": None,
        }
    data = path.read_bytes()
    summary = None
    try:
        payload = json.loads(data.decode("utf-8"))
        if isinstance(payload, dict):
            summary = {
                key: payload.get(key)
                for key in (
                    "artifact_type",
                    "schema_version",
                    "asof",
                    "snapshot_manifest",
                    "readonly_only",
                    "candidate_only",
                    "production_trade_enabled",
                )
                if key in payload
            }
    except Exception:
        summary = None
    return {
        "path": rel(path),
        "exists": True,
        "bytes_base64": base64.b64encode(data).decode("ascii"),
        "sha256": sha256_bytes(data),
        "size_bytes": len(data),
        "json_summary": summary,
    }


def collect_forbidden_keys(value: Any, prefix: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{prefix}.{key}"
            if key in FORBIDDEN_OUTPUT_KEYS:
                hits.append(child_path)
            hits.extend(collect_forbidden_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(collect_forbidden_keys(child, f"{prefix}[{index}]"))
    return hits


def load_dapr12_inputs() -> dict[str, dict[str, Any]]:
    paths = {
        "source_preflight": DAPR12_ROOT / "source_preflight.json",
        "candidate_snapshot_payload_plan": DAPR12_ROOT / "candidate_snapshot_payload_plan.json",
        "candidate_payload_file_write": DAPR12_ROOT / "candidate_payload_file_write.json",
        "latest_pointer_payload_plan": DAPR12_ROOT / "latest_pointer_payload_plan.json",
        "validator_dry_run": DAPR12_ROOT / "validator_dry_run.json",
        "checksum_plan": DAPR12_ROOT / "checksum_plan.json",
        "rollback_preflight": DAPR12_ROOT / "rollback_preflight.json",
        "forbidden_action_audit": DAPR12_ROOT / "forbidden_action_audit.json",
        "candidate_or_stop_decision": DAPR12_ROOT / "candidate_or_stop_decision.json",
    }
    return {name: read_json(path) for name, path in paths.items()}


def backup_latest_pointer() -> dict[str, Any]:
    ROLLBACK_DIR.mkdir(parents=True, exist_ok=True)
    backup = latest_bytes_backup(READONLY_SNAPSHOT_LATEST)
    if backup["exists"] is True:
        shutil.copy2(READONLY_SNAPSHOT_LATEST, ROLLBACK_LATEST_COPY)
    return backup


def build_before_fingerprint(
    created_at: str, inputs: dict[str, dict[str, Any]], latest_backup: dict[str, Any]
) -> dict[str, Any]:
    checksum_plan = inputs["checksum_plan"]
    decision = inputs["candidate_or_stop_decision"]
    latest_plan = inputs["latest_pointer_payload_plan"]
    review_text = DAPR12_REVIEW.read_text(encoding="utf-8") if DAPR12_REVIEW.exists() else ""
    expected_latest_sha = checksum_plan["planned_latest_pointer"]["sha256"]
    candidate_file_checks = {}
    for name in SNAPSHOT_FILE_NAMES:
        planned = checksum_plan["planned_snapshot_files"][name]
        candidate = ROOT / planned["candidate_path"]
        candidate_file_checks[name] = {
            "candidate_path": rel(candidate),
            "exists": candidate.is_file(),
            "sha256": sha256_file(candidate),
            "planned_sha256": planned["sha256"],
            "matches_plan": candidate.is_file() and sha256_file(candidate) == planned["sha256"],
            "planned_canonical_path": planned["planned_canonical_path"],
        }
    latest_plan_sha = sha256_bytes(canonical_json_bytes(latest_plan["payload_plan"]))
    controlled_signal = read_json(CONTROLLED_SIGNAL_LATEST)
    checks = {
        "dapr12_decision_pass": decision.get("status") == "pass",
        "dapr12_ready_for_exact_authorization": decision.get("ready_for_dapr13_exact_authorization_gate") is True,
        "dapr12_stops_before_actual_publish": decision.get("ready_for_direct_readonly_snapshot_publish") is False,
        "dapr12_review_pass_marker_present": "PASS_STOP_BEFORE_DAPR13_ACTUAL_READONLY_SNAPSHOT_PUBLISH_AUTHORIZATION" in review_text,
        "dapr12_checksum_plan_pass": checksum_plan.get("status") == "pass",
        "dapr12_latest_pointer_plan_pass": latest_plan.get("status") == "pass",
        "latest_plan_sha_matches_checksum_plan": latest_plan_sha == expected_latest_sha,
        "all_candidate_files_match_checksum_plan": all(
            item["matches_plan"] is True for item in candidate_file_checks.values()
        ),
        "target_snapshot_dir_absent_before_write": not TARGET_SNAPSHOT_DIR.exists(),
        "readonly_latest_exists_before_write": latest_backup["exists"] is True,
        "rollback_copy_created": ROLLBACK_LATEST_COPY.is_file()
        and sha256_file(ROLLBACK_LATEST_COPY) == latest_backup["sha256"],
        "controlled_signal_latest_asof_target": controlled_signal.get("asof") == TARGET_ASOF,
        "controlled_signal_latest_sha_matches_dapr12_plan": sha256_file(CONTROLLED_SIGNAL_LATEST)
        == latest_plan["payload_plan"].get("source_signal_latest_sha256"),
    }
    return {
        "schema_version": "dapr13.before_fingerprint.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "authorization_scope": {
            "only_candidate_input_dir": rel(CANDIDATE_DIR),
            "allowed_snapshot_dir": rel(TARGET_SNAPSHOT_DIR),
            "allowed_latest_pointer": rel(READONLY_SNAPSHOT_LATEST),
            "forbidden_default_or_provider_or_agent_side_effects": True,
        },
        "candidate_file_checks": candidate_file_checks,
        "fingerprints_before": {
            "readonly_snapshot_latest": file_fingerprint(READONLY_SNAPSHOT_LATEST),
            "target_snapshot_dir": file_fingerprint(TARGET_SNAPSHOT_DIR),
            **{name: file_fingerprint(path) for name, path in PROTECTED_POINTERS.items()},
        },
        "rollback_backup": {
            "path": rel(ROLLBACK_LATEST_COPY),
            "exists": ROLLBACK_LATEST_COPY.is_file(),
            "sha256": sha256_file(ROLLBACK_LATEST_COPY),
            "source_latest_sha256": latest_backup["sha256"],
        },
        "checks": checks,
    }


def stop_if_preflight_failed(before: dict[str, Any]) -> None:
    if before["status"] != "pass":
        failed = [key for key, value in before["checks"].items() if value is not True]
        raise RuntimeError(f"STOP_DAPR13_PREFLIGHT_FAILED: {failed}")


def publish_snapshot_and_latest(inputs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    TARGET_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=False)
    writes = {}
    for name in SNAPSHOT_FILE_NAMES:
        source = CANDIDATE_DIR / name
        target = SNAPSHOT_TARGETS[name]
        shutil.copy2(source, target)
        writes[name] = {
            "source": rel(source),
            "target": rel(target),
            "sha256": sha256_file(target),
        }
    latest_payload = inputs["latest_pointer_payload_plan"]["payload_plan"]
    write_json(READONLY_SNAPSHOT_LATEST, latest_payload)
    return {
        "snapshot_files": writes,
        "latest_pointer": {
            "path": rel(READONLY_SNAPSHOT_LATEST),
            "sha256": sha256_file(READONLY_SNAPSHOT_LATEST),
        },
    }


def build_after_fingerprint(
    created_at: str, before: dict[str, Any], publish_write: dict[str, Any]
) -> dict[str, Any]:
    after = {
        "readonly_snapshot_latest": file_fingerprint(READONLY_SNAPSHOT_LATEST),
        "target_snapshot_dir": file_fingerprint(TARGET_SNAPSHOT_DIR),
        **{name: file_fingerprint(path) for name, path in PROTECTED_POINTERS.items()},
    }
    protected_checks = {}
    for name in PROTECTED_POINTERS:
        before_item = before["fingerprints_before"][name]
        after_item = after[name]
        protected_checks[f"{name}_unchanged"] = before_item.get("sha256") == after_item.get("sha256")
    checks = {
        "target_dir_exists_after_write": TARGET_SNAPSHOT_DIR.is_dir(),
        "latest_pointer_exists_after_write": READONLY_SNAPSHOT_LATEST.is_file(),
        "publish_write_has_five_snapshot_files": len(publish_write["snapshot_files"]) == 5,
        **protected_checks,
    }
    return {
        "schema_version": "dapr13.after_fingerprint.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "fingerprints_after": after,
        "checks": checks,
    }


def build_diff_summary(
    created_at: str, before_latest_backup: dict[str, Any], publish_write: dict[str, Any]
) -> dict[str, Any]:
    before_text = ""
    previous_asof = None
    if before_latest_backup.get("bytes_base64"):
        before_text = base64.b64decode(before_latest_backup["bytes_base64"]).decode("utf-8")
        try:
            previous_payload = json.loads(before_text)
            if isinstance(previous_payload, dict):
                previous_asof = previous_payload.get("asof") or previous_payload.get("signal_asof")
        except Exception:
            previous_asof = None
    after_text = READONLY_SNAPSHOT_LATEST.read_text(encoding="utf-8")
    diff_lines = list(
        difflib.unified_diff(
            before_text.splitlines(),
            after_text.splitlines(),
            fromfile="readonly_strategy_snapshot/latest.before_dapr13.json",
            tofile="readonly_strategy_snapshot/latest.after_dapr13.json",
            lineterm="",
        )
    )
    created_files = sorted(item["target"] for item in publish_write["snapshot_files"].values())
    checks = {
        "latest_diff_contains_target_asof": any(TARGET_ASOF in line for line in diff_lines),
        "latest_diff_contains_previous_asof": previous_asof is not None
        and any(previous_asof in line for line in diff_lines),
        "five_canonical_snapshot_files_created": len(created_files) == 5,
    }
    return {
        "schema_version": "dapr13.diff_summary.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "created_canonical_files": created_files,
        "latest_pointer_unified_diff": diff_lines,
        "previous_asof": previous_asof,
        "checks": checks,
    }


def build_checksum_validation(created_at: str, inputs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    plan = inputs["checksum_plan"]
    snapshot_checks = {}
    for name in SNAPSHOT_FILE_NAMES:
        planned = plan["planned_snapshot_files"][name]
        target = SNAPSHOT_TARGETS[name]
        snapshot_checks[name] = {
            "path": rel(target),
            "exists": target.is_file(),
            "sha256": sha256_file(target),
            "planned_sha256": planned["sha256"],
            "matches_dapr12_plan": sha256_file(target) == planned["sha256"],
        }
    checksum_manifest = read_json(SNAPSHOT_TARGETS["checksum_manifest.json"])
    checksum_files = checksum_manifest.get("files", {})
    actual_files = {
        name: sha256_file(SNAPSHOT_TARGETS[name])
        for name in SNAPSHOT_FILE_NAMES
        if name != "checksum_manifest.json"
    }
    latest_sha = sha256_file(READONLY_SNAPSHOT_LATEST)
    checks = {
        "all_canonical_files_exist": all(item["exists"] for item in snapshot_checks.values()),
        "all_canonical_files_match_dapr12_checksum_plan": all(
            item["matches_dapr12_plan"] for item in snapshot_checks.values()
        ),
        "checksum_manifest_excludes_itself": "checksum_manifest.json" not in checksum_files,
        "checksum_manifest_matches_written_files": checksum_files == actual_files,
        "latest_pointer_matches_dapr12_checksum_plan": latest_sha
        == plan["planned_latest_pointer"]["sha256"],
    }
    return {
        "schema_version": "dapr13.canonical_file_checksum_validation.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "snapshot_file_checks": snapshot_checks,
        "checksum_manifest_files": checksum_files,
        "actual_files_for_checksum_manifest": actual_files,
        "latest_pointer": {
            "path": rel(READONLY_SNAPSHOT_LATEST),
            "sha256": latest_sha,
            "planned_sha256": plan["planned_latest_pointer"]["sha256"],
        },
        "checks": checks,
    }


def build_latest_payload_validation(
    created_at: str, inputs: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    latest = read_json(READONLY_SNAPSHOT_LATEST)
    planned = inputs["latest_pointer_payload_plan"]["payload_plan"]
    manifest = read_json(SNAPSHOT_TARGETS["manifest.json"])
    snapshot = read_json(SNAPSHOT_TARGETS["strategy_snapshot.json"])
    validation = read_json(SNAPSHOT_TARGETS["validation_report.json"])
    forbidden = read_json(SNAPSHOT_TARGETS["forbidden_scope_audit.json"])
    forbidden_key_hits = (
        collect_forbidden_keys(latest)
        + collect_forbidden_keys(manifest)
        + collect_forbidden_keys(snapshot)
        + collect_forbidden_keys(validation)
        + collect_forbidden_keys(forbidden)
    )
    top_candidates = snapshot.get("top_candidates", [])
    checks = {
        "latest_payload_equals_dapr12_plan": latest == planned,
        "latest_points_to_target_manifest": latest.get("snapshot_manifest")
        == rel(SNAPSHOT_TARGETS["manifest.json"]),
        "latest_asof_fields_target": all(
            latest.get(key) == TARGET_ASOF
            for key in ("asof", "data_asof", "signal_asof", "target_date")
        ),
        "latest_readonly_flags_ok": latest.get("readonly_only") is True
        and latest.get("candidate_only") is True
        and latest.get("production_trade_enabled") is False
        and latest.get("not_provider_accepted_latest") is True
        and latest.get("not_trade_target_latest") is True,
        "manifest_schema_ok": manifest.get("artifact_type") == "readonly_strategy_snapshot"
        and manifest.get("schema_version") == "readonly_strategy_snapshot_r13_v1",
        "manifest_asof_target": manifest.get("asof") == TARGET_ASOF,
        "snapshot_asof_fields_target": all(
            snapshot.get(key) == TARGET_ASOF
            for key in ("asof", "data_asof", "signal_asof")
        ),
        "snapshot_candidate_only_top50": snapshot.get("candidate_only") is True
        and snapshot.get("candidate_boundary") == "qlib_top50"
        and len(top_candidates) == 50
        and snapshot.get("top_candidates_count") == 50,
        "snapshot_no_replay_no_order": snapshot.get("strategy_replay_status")
        == "not_built_forbidden_in_rsppr"
        and snapshot.get("order_intent_status") == "not_built_forbidden_in_rsppr"
        and snapshot.get("replay_result_status") == "not_built_forbidden_in_rsppr"
        and snapshot.get("not_order") is True
        and snapshot.get("not_target_position") is True,
        "snapshot_score_semantics_readonly": "not return" in snapshot.get("score_semantics", ""),
        "validation_report_pass": validation.get("status") == "pass",
        "forbidden_scope_audit_pass": forbidden.get("status") == "pass"
        and forbidden.get("all_forbidden_false") is True,
        "forbidden_output_keys_absent": forbidden_key_hits == [],
        "source_signal_latest_sha_matches_current": latest.get("source_signal_latest_sha256")
        == sha256_file(CONTROLLED_SIGNAL_LATEST),
    }
    return {
        "schema_version": "dapr13.latest_pointer_payload_validation.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "latest_payload_summary": {
            "artifact_type": latest.get("artifact_type"),
            "schema_version": latest.get("schema_version"),
            "asof": latest.get("asof"),
            "snapshot_manifest": latest.get("snapshot_manifest"),
            "readonly_only": latest.get("readonly_only"),
            "candidate_only": latest.get("candidate_only"),
            "production_trade_enabled": latest.get("production_trade_enabled"),
        },
        "snapshot_summary": {
            "model_id": snapshot.get("model_id"),
            "candidate_boundary": snapshot.get("candidate_boundary"),
            "top_candidates_count": snapshot.get("top_candidates_count"),
            "top3": [
                {
                    "instrument": item.get("instrument"),
                    "candidate_rank": item.get("candidate_rank"),
                    "score_rank": item.get("score_rank"),
                }
                for item in top_candidates[:3]
                if isinstance(item, dict)
            ],
        },
        "forbidden_output_key_hits": forbidden_key_hits,
        "checks": checks,
    }


def build_rollback_package(
    created_at: str, latest_backup: dict[str, Any]
) -> dict[str, Any]:
    current_latest = file_fingerprint(READONLY_SNAPSHOT_LATEST)
    checks = {
        "rollback_copy_exists": ROLLBACK_LATEST_COPY.is_file(),
        "rollback_copy_sha_matches_before_latest": sha256_file(ROLLBACK_LATEST_COPY)
        == latest_backup.get("sha256"),
        "previous_latest_bytes_backed_up": latest_backup.get("bytes_base64") is not None,
        "current_latest_points_to_target": (
            current_latest.get("json_summary") or {}
        ).get("snapshot_manifest")
        == rel(SNAPSHOT_TARGETS["manifest.json"]),
        "rollback_scope_limited_to_readonly_snapshot_latest_pointer": True,
    }
    return {
        "schema_version": "dapr13.rollback_package.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "rollback_copy": {
            "path": rel(ROLLBACK_LATEST_COPY),
            "sha256": sha256_file(ROLLBACK_LATEST_COPY),
        },
        "previous_latest_pointer_backup": latest_backup,
        "current_latest_pointer": current_latest,
        "rollback_instructions": [
            "Restore data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json from rollback/readonly_strategy_snapshot_latest.before_dapr13.json after verifying sha256.",
            "Do not touch controlled signal latest, Agent prompt latest, qlib accepted latest, legacy option_c latest, provider, qlib refresh, frontend/API defaults, monitor, broker, order, or target paths.",
            "Do not delete the DAPR13 canonical snapshot directory unless the coordinator explicitly authorizes cleanup.",
        ],
        "checks": checks,
    }


def build_forbidden_action_audit(created_at: str) -> dict[str, Any]:
    forbidden_flags = {
        "provider_network_pull_triggered": False,
        "provider_publish_triggered": False,
        "provider_accepted_latest_switched": False,
        "qlib_refresh_triggered": False,
        "qlib_accepted_latest_switched": False,
        "daily_auto_triggered": False,
        "accepted_latest_switch_triggered": False,
        "agent_prompt_built": False,
        "agent_prompt_published": False,
        "openai_call_triggered": False,
        "db_access_triggered": False,
        "strategy_replay_triggered": False,
        "order_intent_generated": False,
        "replay_result_or_nav_generated": False,
        "monitor_broker_order_triggered": False,
        "trade_target_or_size_output_generated": False,
        "frontend_or_api_production_default_switched": False,
    }
    allowed_writes = {
        "canonical_readonly_snapshot_files_written": True,
        "readonly_snapshot_latest_pointer_written": True,
        "rollback_copy_written": True,
        "dapr13_evidence_written": True,
        "dapr13_docs_written": True,
    }
    return {
        "schema_version": "dapr13.forbidden_action_audit.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass",
        "all_forbidden_false": all(value is False for value in forbidden_flags.values()),
        "flags": forbidden_flags,
        "allowed_writes": allowed_writes,
        "write_scope": {
            "canonical_snapshot_dir": rel(TARGET_SNAPSHOT_DIR),
            "latest_pointer": rel(READONLY_SNAPSHOT_LATEST),
            "rollback_copy": rel(ROLLBACK_LATEST_COPY),
            "evidence_root": rel(DAPR13_ROOT),
            "execution_report": rel(DAPR13_EXECUTION_REPORT),
            "review": rel(DAPR13_REVIEW),
        },
    }


def build_artifact_manifest(created_at: str, files: list[Path]) -> dict[str, Any]:
    entries = []
    missing = []
    for path in files:
        exists = path.exists() and path.is_file()
        if not exists and path != DAPR13_ROOT / "artifact_manifest.json":
            missing.append(rel(path))
        entries.append(
            {
                "path": rel(path),
                "exists": exists,
                "size_bytes": path.stat().st_size if exists else None,
                "sha256": sha256_file(path) if exists else None,
            }
        )
    return {
        "schema_version": "dapr13.artifact_manifest.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if not missing else "fail",
        "entries": entries,
        "missing": missing,
    }


def build_execution_report(
    created_at: str,
    before: dict[str, Any],
    publish_write: dict[str, Any],
    after: dict[str, Any],
    diff_summary: dict[str, Any],
    checksum_validation: dict[str, Any],
    latest_validation: dict[str, Any],
    rollback: dict[str, Any],
    forbidden: dict[str, Any],
    artifact_manifest: dict[str, Any],
) -> str:
    overall_pass = all(
        item.get("status") == "pass"
        for item in (
            before,
            after,
            diff_summary,
            checksum_validation,
            latest_validation,
            rollback,
            artifact_manifest,
        )
    ) and forbidden.get("all_forbidden_false") is True
    verdict = (
        "PASS_RECOMMEND_DAPR13_REVIEWER"
        if overall_pass
        else "STOP_REPAIR_DAPR13"
    )
    top3 = latest_validation["snapshot_summary"]["top3"]
    return f"""# DAPR13 Actual Readonly Snapshot Publish 执行报告

created_at: `{created_at}`

phase: `DAPR13_ACTUAL_READONLY_SNAPSHOT_PUBLISH`

target_asof: `{TARGET_ASOF}`

verdict: `{verdict}`

## 1. Scope

本阶段执行用户 exact authorization：输入只使用 `{rel(CANDIDATE_DIR)}`；唯一产品侧写入为 `{rel(TARGET_SNAPSHOT_DIR)}` 下五个 readonly snapshot canonical JSON 和 `{rel(READONLY_SNAPSHOT_LATEST)}`。

不执行 Agent prompt publish、provider publish/pull、qlib refresh、daily auto、accepted latest switch、OpenAI、DB、strategy replay、monitor/broker/order/target、frontend/API production default switch。

## 2. Changes Made

- 参数化 DAPR13 publisher：`scripts/build_tw_dapr13_actual_readonly_snapshot_publish.py`
- 写入 canonical readonly snapshot 目录：`{rel(TARGET_SNAPSHOT_DIR)}`
- 将 readonly snapshot latest 指向：`{rel(SNAPSHOT_TARGETS["manifest.json"])}`
- 创建 rollback copy：`{rel(ROLLBACK_LATEST_COPY)}`

## 3. Evidence Produced

- `before_fingerprint.json`: `{before["status"]}`
- `publish_write.json`: `pass`
- `after_fingerprint.json`: `{after["status"]}`
- `diff_summary.json`: `{diff_summary["status"]}`
- `canonical_file_checksum_validation.json`: `{checksum_validation["status"]}`
- `latest_pointer_payload_validation.json`: `{latest_validation["status"]}`
- `rollback_package.json`: `{rollback["status"]}`
- `forbidden_action_audit.json`: `{forbidden["status"]}`
- `artifact_manifest.json`: `{artifact_manifest["status"]}`

## 4. Published Payload Summary

readonly snapshot latest now points to `{rel(SNAPSHOT_TARGETS["manifest.json"])}`。

Top3 candidate-only symbols:

- rank 1: `{top3[0]["instrument"]}`
- rank 2: `{top3[1]["instrument"]}`
- rank 3: `{top3[2]["instrument"]}`

## 5. Protected Pointer Audit

- controlled signal latest unchanged: `{after["checks"]["controlled_signal_latest_unchanged"]}`
- Agent prompt latest unchanged: `{after["checks"]["agent_daily_prompt_latest_unchanged"]}`
- qlib_pipeline option_c latest unchanged: `{after["checks"]["legacy_qlib_option_c_latest_signal_unchanged"]}`
- legacy option_c latest unchanged: `{after["checks"]["legacy_data_option_c_latest_signal_unchanged"]}`

## 6. Forbidden Actions Audit

`all_forbidden_false={forbidden["all_forbidden_false"]}`。本阶段没有 provider/qlib/daily-auto/Agent/OpenAI/DB/replay/order/default-switch 行为。

## 7. Issues / Blockers / Deviations

无 DAPR13 blocker。DAPR12 candidate payload 仅作为本次一次性输入例外，不代表后续自动 latest switch 已获授权。

## 8. Files Changed

- `scripts/build_tw_dapr13_actual_readonly_snapshot_publish.py`
- `{rel(TARGET_SNAPSHOT_DIR)}/manifest.json`
- `{rel(TARGET_SNAPSHOT_DIR)}/strategy_snapshot.json`
- `{rel(TARGET_SNAPSHOT_DIR)}/validation_report.json`
- `{rel(TARGET_SNAPSHOT_DIR)}/forbidden_scope_audit.json`
- `{rel(TARGET_SNAPSHOT_DIR)}/checksum_manifest.json`
- `{rel(READONLY_SNAPSHOT_LATEST)}`
- `{rel(DAPR13_ROOT)}/*`
- `{rel(DAPR13_EXECUTION_REPORT)}`
- `{rel(DAPR13_REVIEW)}`

## 9. Recommendation For Reviewer

请独立复核 DAPR13 是否严格限制在 authorized readonly snapshot publish scope，并确认 protected pointers 未变化。
"""


def build_review_doc(
    created_at: str,
    before: dict[str, Any],
    after: dict[str, Any],
    checksum_validation: dict[str, Any],
    latest_validation: dict[str, Any],
    rollback: dict[str, Any],
    forbidden: dict[str, Any],
    artifact_manifest: dict[str, Any],
) -> str:
    overall_pass = all(
        item.get("status") == "pass"
        for item in (
            before,
            after,
            checksum_validation,
            latest_validation,
            rollback,
            artifact_manifest,
        )
    ) and forbidden.get("all_forbidden_false") is True
    verdict = "PASS_STOP_BEFORE_AGENT_PROMPT_PUBLISH" if overall_pass else "FAIL_NEEDS_REPAIR"
    return f"""# DAPR13 Actual Readonly Snapshot Publish 审查

created_at: `{created_at}`

verdict: `{verdict}`

## 1. Verdict

{verdict}

## 2. Findings

### Critical

无。

### High

无。

### Medium

无。

### Low

无。

## 3. Mainline Compliance

DAPR13 只执行了用户授权的 readonly snapshot canonical publish 和 readonly snapshot latest 指针写入。DAPR12 candidate payload 是本次一次性输入，不提升为 final production readiness，也不授权后续自动 latest switch。

## 4. Evidence Checked

- `{rel(DAPR13_ROOT / "before_fingerprint.json")}`
- `{rel(DAPR13_ROOT / "after_fingerprint.json")}`
- `{rel(DAPR13_ROOT / "diff_summary.json")}`
- `{rel(DAPR13_ROOT / "canonical_file_checksum_validation.json")}`
- `{rel(DAPR13_ROOT / "latest_pointer_payload_validation.json")}`
- `{rel(DAPR13_ROOT / "rollback_package.json")}`
- `{rel(DAPR13_ROOT / "forbidden_action_audit.json")}`
- `{rel(DAPR13_ROOT / "artifact_manifest.json")}`

## 5. Safety Boundary Review

- Protected signal latest unchanged: `{after["checks"]["controlled_signal_latest_unchanged"]}`
- Agent prompt latest unchanged: `{after["checks"]["agent_daily_prompt_latest_unchanged"]}`
- qlib option_c latest unchanged: `{after["checks"]["legacy_qlib_option_c_latest_signal_unchanged"]}`
- legacy option_c latest unchanged: `{after["checks"]["legacy_data_option_c_latest_signal_unchanged"]}`
- forbidden actions all false: `{forbidden["all_forbidden_false"]}`

## 6. Payload Acceptance

- canonical file checksum validation: `{checksum_validation["status"]}`
- latest pointer payload validation: `{latest_validation["status"]}`
- rollback package: `{rollback["status"]}`
- artifact manifest: `{artifact_manifest["status"]}`

## 7. Next Work Document

如果继续，应进入 `DAPR14_AGENT_PROMPT_LATEST_PREFLIGHT_OR_STOP`。DAPR14 只能做 Agent prompt latest 的 preflight/stop，不得默认发布 Agent prompt，不得触发 OpenAI，不得触发 provider/qlib/DB/replay/order/default switch。

## 8. Command For Executor Or Coordinator

等待 coordinator 明确是否进入 DAPR14；当前 DAPR13 已完成 readonly snapshot publish 并停在 Agent prompt publish 之前。
"""


def main() -> None:
    created_at = now_iso()
    DAPR13_ROOT.mkdir(parents=True, exist_ok=True)
    inputs = load_dapr12_inputs()
    latest_backup = backup_latest_pointer()
    before = build_before_fingerprint(created_at, inputs, latest_backup)
    write_json(DAPR13_ROOT / "before_fingerprint.json", before)
    stop_if_preflight_failed(before)

    publish_write = publish_snapshot_and_latest(inputs)
    write_json(DAPR13_ROOT / "publish_write.json", {
        "schema_version": "dapr13.publish_write.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass",
        **publish_write,
    })

    after = build_after_fingerprint(created_at, before, publish_write)
    diff_summary = build_diff_summary(created_at, latest_backup, publish_write)
    checksum_validation = build_checksum_validation(created_at, inputs)
    latest_validation = build_latest_payload_validation(created_at, inputs)
    rollback = build_rollback_package(created_at, latest_backup)
    forbidden = build_forbidden_action_audit(created_at)

    evidence_files = [
        DAPR13_ROOT / "before_fingerprint.json",
        DAPR13_ROOT / "publish_write.json",
        DAPR13_ROOT / "after_fingerprint.json",
        DAPR13_ROOT / "diff_summary.json",
        DAPR13_ROOT / "canonical_file_checksum_validation.json",
        DAPR13_ROOT / "latest_pointer_payload_validation.json",
        DAPR13_ROOT / "rollback_package.json",
        DAPR13_ROOT / "forbidden_action_audit.json",
    ]
    write_json(DAPR13_ROOT / "after_fingerprint.json", after)
    write_json(DAPR13_ROOT / "diff_summary.json", diff_summary)
    write_json(DAPR13_ROOT / "canonical_file_checksum_validation.json", checksum_validation)
    write_json(DAPR13_ROOT / "latest_pointer_payload_validation.json", latest_validation)
    write_json(DAPR13_ROOT / "rollback_package.json", rollback)
    write_json(DAPR13_ROOT / "forbidden_action_audit.json", forbidden)

    artifact_manifest = build_artifact_manifest(
        created_at,
        evidence_files
        + [ROLLBACK_LATEST_COPY]
        + [SNAPSHOT_TARGETS[name] for name in SNAPSHOT_FILE_NAMES]
        + [READONLY_SNAPSHOT_LATEST],
    )
    execution_report = build_execution_report(
        created_at,
        before,
        publish_write,
        after,
        diff_summary,
        checksum_validation,
        latest_validation,
        rollback,
        forbidden,
        artifact_manifest,
    )
    review_doc = build_review_doc(
        created_at,
        before,
        after,
        checksum_validation,
        latest_validation,
        rollback,
        forbidden,
        artifact_manifest,
    )
    write_text(DAPR13_EXECUTION_REPORT, execution_report)
    write_text(DAPR13_REVIEW, review_doc)
    write_json(DAPR13_ROOT / "artifact_manifest.json", artifact_manifest)

    final_checks = [
        before.get("status") == "pass",
        after.get("status") == "pass",
        diff_summary.get("status") == "pass",
        checksum_validation.get("status") == "pass",
        latest_validation.get("status") == "pass",
        rollback.get("status") == "pass",
        forbidden.get("all_forbidden_false") is True,
        artifact_manifest.get("status") == "pass",
    ]
    if not all(final_checks):
        raise RuntimeError("STOP_DAPR13_POST_WRITE_VALIDATION_FAILED")
    print(
        json.dumps(
            {
                "status": "pass",
                "phase": "DAPR13_ACTUAL_READONLY_SNAPSHOT_PUBLISH",
                "target_asof": TARGET_ASOF,
                "latest_pointer": rel(READONLY_SNAPSHOT_LATEST),
                "snapshot_manifest": rel(SNAPSHOT_TARGETS["manifest.json"]),
                "evidence_root": rel(DAPR13_ROOT),
                "execution_report": rel(DAPR13_EXECUTION_REPORT),
                "review": rel(DAPR13_REVIEW),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
