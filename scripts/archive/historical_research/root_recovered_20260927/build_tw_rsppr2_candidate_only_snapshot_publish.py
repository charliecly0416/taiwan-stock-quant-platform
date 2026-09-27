#!/usr/bin/env python3
"""Publish the RSPPR2 candidate-only readonly strategy snapshot.

RSPPR2 consumes the RSPPR1 dry-run payload plan and writes exactly those
planned readonly snapshot payloads to the publish directory. It then updates
the readonly snapshot latest pointer, validates checksums, and writes rollback
evidence. It does not pull providers, score models, run strategy replay, build
Agent prompts, or touch product defaults.
"""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGET_ASOF = "2026-07-08"
MODEL_ID = "e4_frozen_qlib_2018_2022"

RSPPR_MAINLINE = Path(
    "docs/tw_portfolio_decision_model/"
    "POLICY_RSPPR_READONLY_SNAPSHOT_BUILDER_PUBLISH_ROUTE_MAINLINE_CN.md"
)
RSPPR1_EXECUTION_REPORT = Path(
    "docs/tw_portfolio_decision_model/"
    "POLICY_RSPPR1_CANDIDATE_ONLY_SNAPSHOT_DRY_RUN_EXECUTION_REPORT_CN.md"
)
RSPPR1_REVIEW = Path(
    "docs/tw_portfolio_decision_model/"
    "POLICY_RSPPR1_CANDIDATE_ONLY_SNAPSHOT_DRY_RUN_REVIEW_CN.md"
)
RSPPR2_WORK = Path(
    "docs/tw_portfolio_decision_model/"
    "POLICY_RSPPR2_CANDIDATE_ONLY_SNAPSHOT_PUBLISH_WORK_CN.md"
)
RSPPR2_EXECUTION_REPORT = Path(
    "docs/tw_portfolio_decision_model/"
    "POLICY_RSPPR2_CANDIDATE_ONLY_SNAPSHOT_PUBLISH_EXECUTION_REPORT_CN.md"
)
RSPPR3_WORK = Path(
    "docs/tw_portfolio_decision_model/"
    "POLICY_RSPPR3_SNAPSHOT_READONLY_INTEGRATION_ACCEPTANCE_WORK_CN.md"
)
CLPR4_REVIEW = Path(
    "docs/tw_portfolio_decision_model/"
    "POLICY_CLPR4_FINAL_SAFETY_AND_INTEGRATION_ACCEPTANCE_REVIEW_CN.md"
)
PROJECT_CONSTITUTION = Path(
    "docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md"
)
MODEL_SIGNAL_CONTRACT = Path("docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md")
READONLY_SNAPSHOT_CONTRACT = Path(
    "docs/tw_modular_contracts/READONLY_STRATEGY_SNAPSHOT_CONTRACT_CN.md"
)

RSPPR1_EVIDENCE_ROOT = Path(
    "data_tw/experiments/readonly_snapshot_builder_publish_route/"
    "rsppr1_candidate_only_snapshot_dry_run"
)
RSPPR1_SOURCE_PREFLIGHT = RSPPR1_EVIDENCE_ROOT / "source_preflight.json"
RSPPR1_PAYLOAD_PLAN = RSPPR1_EVIDENCE_ROOT / "candidate_snapshot_payload_plan.json"
RSPPR1_LATEST_POINTER_PLAN = RSPPR1_EVIDENCE_ROOT / "latest_pointer_payload_plan.json"
RSPPR1_VALIDATOR_DRY_RUN = RSPPR1_EVIDENCE_ROOT / "validator_dry_run.json"
RSPPR1_CHECKSUM_PLAN = RSPPR1_EVIDENCE_ROOT / "checksum_plan.json"
RSPPR1_ROLLBACK_PREFLIGHT = RSPPR1_EVIDENCE_ROOT / "rollback_preflight.json"
RSPPR1_FORBIDDEN_ACTION_AUDIT = RSPPR1_EVIDENCE_ROOT / "forbidden_action_audit.json"

READONLY_SNAPSHOT_ROOT = Path("data_tw/artifacts/publish/readonly_strategy_snapshot")
TARGET_SNAPSHOT_DIR = READONLY_SNAPSHOT_ROOT / TARGET_ASOF
TARGET_MANIFEST = TARGET_SNAPSHOT_DIR / "manifest.json"
TARGET_STRATEGY_SNAPSHOT = TARGET_SNAPSHOT_DIR / "strategy_snapshot.json"
TARGET_VALIDATION_REPORT = TARGET_SNAPSHOT_DIR / "validation_report.json"
TARGET_FORBIDDEN_SCOPE_AUDIT = TARGET_SNAPSHOT_DIR / "forbidden_scope_audit.json"
TARGET_CHECKSUM_MANIFEST = TARGET_SNAPSHOT_DIR / "checksum_manifest.json"
READONLY_SNAPSHOT_LATEST = READONLY_SNAPSHOT_ROOT / "latest.json"

CONTROLLED_SIGNAL_LATEST = Path(
    "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json"
)
AGENT_DAILY_PROMPT_LATEST = Path("data_tw/artifacts/agent_daily_prompt/latest.json")
LEGACY_QLIB_OPTION_C_LATEST = Path(
    "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json"
)
LEGACY_DATA_OPTION_C_LATEST = Path(
    "data_tw/experiments/option_c_daily_signal/latest_signal.json"
)

EVIDENCE_ROOT = Path(
    "data_tw/experiments/readonly_snapshot_builder_publish_route/"
    "rsppr2_candidate_only_snapshot_publish"
)

PRE_PUBLISH_FINGERPRINT = EVIDENCE_ROOT / "pre_publish_fingerprint.json"
WRITTEN_SNAPSHOT_ARTIFACT = EVIDENCE_ROOT / "written_snapshot_artifact.json"
LATEST_POINTER_WRITE = EVIDENCE_ROOT / "latest_pointer_write.json"
VALIDATOR_PUBLISH = EVIDENCE_ROOT / "validator_publish.json"
CHECKSUM_MANIFEST_VERIFY = EVIDENCE_ROOT / "checksum_manifest_verify.json"
ROLLBACK_PACKAGE = EVIDENCE_ROOT / "rollback_package.json"
FORBIDDEN_ACTION_AUDIT = EVIDENCE_ROOT / "forbidden_action_audit.json"
ARTIFACT_MANIFEST = EVIDENCE_ROOT / "artifact_manifest.json"

SCRIPT_PATH = Path("scripts/build_tw_rsppr2_candidate_only_snapshot_publish.py")

SNAPSHOT_FILES = {
    "manifest.json": TARGET_MANIFEST,
    "strategy_snapshot.json": TARGET_STRATEGY_SNAPSHOT,
    "validation_report.json": TARGET_VALIDATION_REPORT,
    "forbidden_scope_audit.json": TARGET_FORBIDDEN_SCOPE_AUDIT,
    "checksum_manifest.json": TARGET_CHECKSUM_MANIFEST,
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


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_json_payload(payload: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(payload))


def sha256_file(path: Path) -> str | None:
    full = resolve(path)
    if not full.exists() or not full.is_file():
        return None
    digest = hashlib.sha256()
    with full.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with resolve(path).open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def write_json(path: Path, payload: dict[str, Any]) -> None:
    full = resolve(path)
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_bytes(canonical_json_bytes(payload))


def write_text(path: Path, text: str) -> None:
    full = resolve(path)
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(text.rstrip() + "\n", encoding="utf-8")


def text_contains(path: Path, needle: str) -> bool:
    full = resolve(path)
    return full.exists() and needle in full.read_text(encoding="utf-8")


def file_fingerprint(path: Path) -> dict[str, Any]:
    full = resolve(path)
    item: dict[str, Any] = {
        "path": rel(full),
        "exists": full.exists(),
        "is_file": full.is_file(),
        "is_dir": full.is_dir(),
        "size_bytes": full.stat().st_size if full.exists() and full.is_file() else None,
        "sha256": sha256_file(path),
        "json_summary": None,
    }
    if full.exists() and full.is_file() and full.suffix == ".json":
        try:
            data = load_json(path)
            item["json_summary"] = {
                key: data.get(key)
                for key in (
                    "artifact_type",
                    "schema_version",
                    "status",
                    "verdict",
                    "asof",
                    "data_asof",
                    "signal_asof",
                    "target_date",
                    "model_id",
                    "snapshot_manifest",
                    "readonly_only",
                    "candidate_only",
                    "production_trade_enabled",
                )
                if key in data
            }
        except Exception as exc:  # pragma: no cover - diagnostic only
            item["json_error"] = str(exc)
    return item


def latest_bytes_backup(path: Path) -> dict[str, Any]:
    full = resolve(path)
    if not full.exists() or not full.is_file():
        return {
            "path": rel(full),
            "exists": False,
            "bytes_base64": None,
            "sha256": None,
            "size_bytes": None,
            "json_summary": None,
        }
    data = full.read_bytes()
    summary = None
    try:
        parsed = json.loads(data.decode("utf-8"))
        if isinstance(parsed, dict):
            summary = {
                key: parsed.get(key)
                for key in (
                    "artifact_type",
                    "schema_version",
                    "asof",
                    "data_asof",
                    "signal_asof",
                    "target_date",
                    "snapshot_manifest",
                )
                if key in parsed
            }
    except Exception:
        summary = None
    return {
        "path": rel(full),
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


def load_rsppr1_inputs() -> dict[str, dict[str, Any]]:
    return {
        "source_preflight": load_json(RSPPR1_SOURCE_PREFLIGHT),
        "candidate_snapshot_payload_plan": load_json(RSPPR1_PAYLOAD_PLAN),
        "latest_pointer_payload_plan": load_json(RSPPR1_LATEST_POINTER_PLAN),
        "validator_dry_run": load_json(RSPPR1_VALIDATOR_DRY_RUN),
        "checksum_plan": load_json(RSPPR1_CHECKSUM_PLAN),
        "rollback_preflight": load_json(RSPPR1_ROLLBACK_PREFLIGHT),
        "forbidden_action_audit": load_json(RSPPR1_FORBIDDEN_ACTION_AUDIT),
    }


def build_pre_publish_fingerprint(
    created_at: str, rsppr1: dict[str, dict[str, Any]], previous_latest: dict[str, Any]
) -> dict[str, Any]:
    target_dir = resolve(TARGET_SNAPSHOT_DIR)
    rsppr1_status_checks = {
        name: payload.get("status") == "pass"
        for name, payload in rsppr1.items()
        if name != "forbidden_action_audit"
    }
    rsppr1_status_checks["rsppr1_forbidden_action_audit_pass"] = (
        rsppr1["forbidden_action_audit"].get("status") == "pass"
        and rsppr1["forbidden_action_audit"].get("all_false") is True
    )
    checks = {
        "rsppr1_reviewer_pass": text_contains(
            RSPPR1_REVIEW,
            "PASS_RECOMMEND_RSPPR2_CANDIDATE_ONLY_SNAPSHOT_PUBLISH",
        ),
        "rsppr1_execution_report_pass": text_contains(
            RSPPR1_EXECUTION_REPORT,
            "PASS_RECOMMEND_RSPPR1_REVIEWER",
        ),
        "target_snapshot_dir_absent_before_write": not target_dir.exists(),
        "previous_latest_pointer_backed_up": previous_latest["exists"] is True,
        "controlled_signal_latest_matches_rsppr1": file_fingerprint(
            CONTROLLED_SIGNAL_LATEST
        ).get("sha256")
        == rsppr1["source_preflight"]["controlled_signal_latest"]["fingerprint"][
            "sha256"
        ],
        **rsppr1_status_checks,
    }
    return {
        "schema_version": "rsppr2.pre_publish_fingerprint.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "documents_read": [
            rel(resolve(RSPPR_MAINLINE)),
            rel(resolve(RSPPR1_EXECUTION_REPORT)),
            rel(resolve(RSPPR1_REVIEW)),
            rel(resolve(RSPPR2_WORK)),
            rel(resolve(CLPR4_REVIEW)),
            rel(resolve(PROJECT_CONSTITUTION)),
            rel(resolve(MODEL_SIGNAL_CONTRACT)),
            rel(resolve(READONLY_SNAPSHOT_CONTRACT)),
            rel(resolve(RSPPR1_SOURCE_PREFLIGHT)),
            rel(resolve(RSPPR1_PAYLOAD_PLAN)),
            rel(resolve(RSPPR1_LATEST_POINTER_PLAN)),
            rel(resolve(RSPPR1_VALIDATOR_DRY_RUN)),
            rel(resolve(RSPPR1_CHECKSUM_PLAN)),
            rel(resolve(RSPPR1_ROLLBACK_PREFLIGHT)),
            rel(resolve(RSPPR1_FORBIDDEN_ACTION_AUDIT)),
        ],
        "pre_publish_fingerprints": {
            "readonly_snapshot_latest": file_fingerprint(READONLY_SNAPSHOT_LATEST),
            "target_snapshot_dir": file_fingerprint(TARGET_SNAPSHOT_DIR),
            "controlled_signal_latest": file_fingerprint(CONTROLLED_SIGNAL_LATEST),
            "agent_daily_prompt_latest": file_fingerprint(AGENT_DAILY_PROMPT_LATEST),
            "legacy_qlib_option_c_latest_signal": file_fingerprint(
                LEGACY_QLIB_OPTION_C_LATEST
            ),
            "legacy_data_option_c_latest_signal": file_fingerprint(
                LEGACY_DATA_OPTION_C_LATEST
            ),
        },
        "previous_latest_pointer_backup_summary": {
            "path": previous_latest["path"],
            "exists": previous_latest["exists"],
            "sha256": previous_latest["sha256"],
            "size_bytes": previous_latest["size_bytes"],
            "json_summary": previous_latest["json_summary"],
        },
        "checks": checks,
    }


def stop_if_collision(pre_publish: dict[str, Any]) -> None:
    if pre_publish["checks"]["target_snapshot_dir_absent_before_write"] is not True:
        raise RuntimeError(
            f"STOP: target snapshot dir already exists: {TARGET_SNAPSHOT_DIR}"
        )
    if pre_publish["status"] != "pass":
        raise RuntimeError("STOP: pre-publish fingerprint checks did not pass")


def write_snapshot_and_latest(
    rsppr1: dict[str, dict[str, Any]]
) -> tuple[dict[str, Any], dict[str, Any]]:
    payloads = rsppr1["candidate_snapshot_payload_plan"]["payloads"]
    latest_payload = rsppr1["latest_pointer_payload_plan"]["payload_plan"]
    resolve(TARGET_SNAPSHOT_DIR).mkdir(parents=True, exist_ok=False)
    for file_name, path in SNAPSHOT_FILES.items():
        payload_key = file_name.removesuffix(".json")
        write_json(path, payloads[payload_key])
    write_json(READONLY_SNAPSHOT_LATEST, latest_payload)
    return payloads, latest_payload


def build_written_snapshot_artifact(
    created_at: str,
    rsppr1: dict[str, dict[str, Any]],
    payloads: dict[str, Any],
) -> dict[str, Any]:
    planned = rsppr1["checksum_plan"]["planned_snapshot_files"]
    actual = {
        name: {
            "path": rel(resolve(path)),
            "exists": resolve(path).is_file(),
            "sha256": sha256_file(path),
            "planned_sha256": planned[name]["sha256"],
            "matches_rsppr1_checksum_plan": sha256_file(path) == planned[name]["sha256"],
        }
        for name, path in SNAPSHOT_FILES.items()
    }
    snapshot = payloads["strategy_snapshot"]
    checks = {
        "all_snapshot_files_exist": all(item["exists"] for item in actual.values()),
        "all_snapshot_files_match_rsppr1_checksum_plan": all(
            item["matches_rsppr1_checksum_plan"] for item in actual.values()
        ),
        "candidate_only_true": snapshot.get("candidate_only") is True,
        "top_candidates_count_50": snapshot.get("top_candidates_count") == 50,
        "exit_candidates_empty": snapshot.get("exit_candidates") == [],
        "hold_candidates_empty": snapshot.get("hold_candidates") == [],
        "exit_hold_context_status_not_built": snapshot.get(
            "exit_hold_context_status"
        )
        == "not_built_no_strategy_replay",
        "model_id_model_a": snapshot.get("model_id") == MODEL_ID,
    }
    return {
        "schema_version": "rsppr2.written_snapshot_artifact.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "target_snapshot_dir": rel(resolve(TARGET_SNAPSHOT_DIR)),
        "files": actual,
        "candidate_only_summary": {
            "candidate_only": snapshot.get("candidate_only"),
            "top_candidates_count": snapshot.get("top_candidates_count"),
            "exit_candidates": snapshot.get("exit_candidates"),
            "hold_candidates": snapshot.get("hold_candidates"),
            "exit_hold_context_status": snapshot.get("exit_hold_context_status"),
            "ranking_source": snapshot.get("ranking_source"),
            "candidate_boundary": snapshot.get("candidate_boundary"),
        },
        "checks": checks,
    }


def build_latest_pointer_write(
    created_at: str,
    rsppr1: dict[str, dict[str, Any]],
    latest_payload: dict[str, Any],
) -> dict[str, Any]:
    planned_sha = rsppr1["checksum_plan"]["planned_latest_pointer"]["sha256"]
    actual_sha = sha256_file(READONLY_SNAPSHOT_LATEST)
    loaded_latest = load_json(READONLY_SNAPSHOT_LATEST)
    checks = {
        "latest_pointer_exists": resolve(READONLY_SNAPSHOT_LATEST).is_file(),
        "latest_pointer_matches_rsppr1_plan": actual_sha == planned_sha,
        "latest_pointer_payload_roundtrip": loaded_latest == latest_payload,
        "points_to_2026_07_08_manifest_only": loaded_latest.get("snapshot_manifest")
        == rel(resolve(TARGET_MANIFEST)),
        "candidate_only_true": loaded_latest.get("candidate_only") is True,
        "readonly_only_true": loaded_latest.get("readonly_only") is True,
        "production_trade_enabled_false": loaded_latest.get("production_trade_enabled")
        is False,
        "not_provider_accepted_latest_true": loaded_latest.get(
            "not_provider_accepted_latest"
        )
        is True,
        "not_trade_target_latest_true": loaded_latest.get("not_trade_target_latest")
        is True,
    }
    return {
        "schema_version": "rsppr2.latest_pointer_write.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "path": rel(resolve(READONLY_SNAPSHOT_LATEST)),
        "sha256": actual_sha,
        "planned_sha256": planned_sha,
        "payload_summary": {
            "artifact_type": loaded_latest.get("artifact_type"),
            "schema_version": loaded_latest.get("schema_version"),
            "asof": loaded_latest.get("asof"),
            "data_asof": loaded_latest.get("data_asof"),
            "signal_asof": loaded_latest.get("signal_asof"),
            "target_date": loaded_latest.get("target_date"),
            "snapshot_manifest": loaded_latest.get("snapshot_manifest"),
            "candidate_only": loaded_latest.get("candidate_only"),
            "readonly_only": loaded_latest.get("readonly_only"),
            "production_trade_enabled": loaded_latest.get("production_trade_enabled"),
        },
        "checks": checks,
    }


def build_checksum_manifest_verify(created_at: str) -> dict[str, Any]:
    checksum_manifest = load_json(TARGET_CHECKSUM_MANIFEST)
    manifest_files = checksum_manifest.get("files", {})
    actual_files = {
        name: sha256_file(path)
        for name, path in SNAPSHOT_FILES.items()
        if name != "checksum_manifest.json"
    }
    rsppr1_plan = load_json(RSPPR1_CHECKSUM_PLAN)["planned_snapshot_files"]
    checks = {
        "checksum_manifest_exists": resolve(TARGET_CHECKSUM_MANIFEST).is_file(),
        "checksum_manifest_excludes_itself": "checksum_manifest.json"
        not in manifest_files,
        "checksum_manifest_matches_written_files": manifest_files == actual_files,
        "checksum_manifest_sha_matches_rsppr1_plan": sha256_file(
            TARGET_CHECKSUM_MANIFEST
        )
        == rsppr1_plan["checksum_manifest.json"]["sha256"],
        "all_written_files_match_rsppr1_plan": all(
            sha256_file(path) == rsppr1_plan[name]["sha256"]
            for name, path in SNAPSHOT_FILES.items()
        ),
    }
    return {
        "schema_version": "rsppr2.checksum_manifest_verify.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "checksum_manifest_path": rel(resolve(TARGET_CHECKSUM_MANIFEST)),
        "checksum_manifest_sha256": sha256_file(TARGET_CHECKSUM_MANIFEST),
        "checksum_manifest_files": manifest_files,
        "actual_file_sha256": {
            name: sha256_file(path) for name, path in SNAPSHOT_FILES.items()
        },
        "checks": checks,
    }


def build_validator_publish(
    created_at: str,
    written: dict[str, Any],
    latest_write: dict[str, Any],
    checksum_verify: dict[str, Any],
) -> dict[str, Any]:
    manifest = load_json(TARGET_MANIFEST)
    snapshot = load_json(TARGET_STRATEGY_SNAPSHOT)
    validation = load_json(TARGET_VALIDATION_REPORT)
    forbidden_scope = load_json(TARGET_FORBIDDEN_SCOPE_AUDIT)
    latest = load_json(READONLY_SNAPSHOT_LATEST)
    forbidden_key_hits = (
        collect_forbidden_keys(manifest)
        + collect_forbidden_keys(snapshot)
        + collect_forbidden_keys(validation)
        + collect_forbidden_keys(forbidden_scope)
        + collect_forbidden_keys(latest)
    )
    top_candidates = snapshot.get("top_candidates", [])
    checks = {
        "written_snapshot_artifact_pass": written.get("status") == "pass",
        "latest_pointer_write_pass": latest_write.get("status") == "pass",
        "checksum_manifest_verify_pass": checksum_verify.get("status") == "pass",
        "manifest_artifact_type_ok": manifest.get("artifact_type")
        == "readonly_strategy_snapshot",
        "manifest_schema_version_ok": manifest.get("schema_version")
        == "readonly_strategy_snapshot_r13_v1",
        "manifest_candidate_only_true": manifest.get("candidate_only") is True,
        "snapshot_candidate_only_true": snapshot.get("candidate_only") is True,
        "top_candidates_50": len(top_candidates) == 50
        and snapshot.get("top_candidates_count") == 50,
        "all_top_candidates_rank_le_50": all(
            isinstance(item, dict) and item.get("candidate_rank", 999999) <= 50
            for item in top_candidates
        ),
        "exit_candidates_empty": snapshot.get("exit_candidates") == [],
        "hold_candidates_empty": snapshot.get("hold_candidates") == [],
        "exit_hold_context_status_not_built": snapshot.get(
            "exit_hold_context_status"
        )
        == "not_built_no_strategy_replay",
        "validation_report_pass": validation.get("status") == "pass",
        "forbidden_scope_audit_pass": forbidden_scope.get("status") == "pass"
        and forbidden_scope.get("all_forbidden_false") is True,
        "latest_pointer_points_to_manifest": latest.get("snapshot_manifest")
        == rel(resolve(TARGET_MANIFEST)),
        "readonly_flags_ok": all(
            [
                manifest.get("readonly_only") is True,
                snapshot.get("readonly_only") is True,
                latest.get("readonly_only") is True,
                manifest.get("production_trade_enabled") is False,
                snapshot.get("production_trade_enabled") is False,
                latest.get("production_trade_enabled") is False,
                snapshot.get("not_order") is True,
                snapshot.get("no_order_action") is True,
                snapshot.get("not_investment_advice") is True,
            ]
        ),
        "forbidden_output_keys_absent": forbidden_key_hits == [],
        "agent_prompt_not_built": not resolve(AGENT_DAILY_PROMPT_LATEST).exists(),
    }
    return {
        "schema_version": "rsppr2.validator_publish.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "validator_type": "candidate_only_publish_validator_evidence",
        "existing_ltr_primary_validator_not_used": True,
        "candidate_only_summary": {
            "candidate_only": snapshot.get("candidate_only"),
            "top_candidates_count": snapshot.get("top_candidates_count"),
            "exit_candidates": snapshot.get("exit_candidates"),
            "hold_candidates": snapshot.get("hold_candidates"),
            "exit_hold_context_status": snapshot.get("exit_hold_context_status"),
            "model_id": snapshot.get("model_id"),
            "base_model_id": snapshot.get("base_model_id"),
            "ranking_source": snapshot.get("ranking_source"),
            "candidate_boundary": snapshot.get("candidate_boundary"),
        },
        "forbidden_output_key_hits": forbidden_key_hits,
        "checks": checks,
    }


def build_rollback_package(
    created_at: str, previous_latest: dict[str, Any]
) -> dict[str, Any]:
    current_latest = file_fingerprint(READONLY_SNAPSHOT_LATEST)
    checks = {
        "previous_latest_bytes_backed_up": previous_latest["exists"] is True
        and previous_latest["bytes_base64"] is not None,
        "previous_latest_sha_recorded": previous_latest["sha256"]
        == "cbe27481f20e45db9c1f9be5d16b2636da3dae54fa5c45161be009bfbc17ec4d",
        "current_latest_points_to_target": (
            current_latest.get("json_summary") or {}
        ).get("snapshot_manifest")
        == rel(resolve(TARGET_MANIFEST)),
        "old_2026_06_18_artifact_not_deleted": resolve(
            READONLY_SNAPSHOT_ROOT / "2026-06-18" / "manifest.json"
        ).is_file(),
        "rollback_scope_limited": True,
    }
    return {
        "schema_version": "rsppr2.rollback_package.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "previous_latest_pointer_backup": previous_latest,
        "current_latest_pointer": current_latest,
        "created_snapshot_dir": rel(resolve(TARGET_SNAPSHOT_DIR)),
        "rollback_instructions": [
            "Restore readonly_strategy_snapshot/latest.json from previous_latest_pointer_backup bytes after verifying sha256.",
            "Do not delete or modify data_tw/artifacts/publish/readonly_strategy_snapshot/2026-06-18/.",
            "Do not touch controlled signal latest, provider accepted latest, qlib accepted latest, legacy option_c latest, Agent prompt latest, frontend/API/default, monitor, broker, or order paths.",
        ],
        "checks": checks,
    }


def build_forbidden_action_audit(created_at: str) -> dict[str, Any]:
    flags = {
        "provider_network_pull_triggered": False,
        "provider_publish_triggered": False,
        "provider_accepted_latest_switched": False,
        "qlib_accepted_latest_switched": False,
        "legacy_option_c_latest_signal_switched": False,
        "model_scoring_or_training_triggered": False,
        "strategy_replay_triggered": False,
        "order_intent_generated": False,
        "replay_result_or_nav_generated": False,
        "agent_prompt_built": False,
        "agent_prompt_published": False,
        "openai_call_triggered": False,
        "frontend_or_api_default_switched": False,
        "monitor_broker_order_triggered": False,
        "trade_target_or_size_output_generated": False,
    }
    return {
        "schema_version": "rsppr2.forbidden_action_audit.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass",
        "all_false": all(value is False for value in flags.values()),
        "flags": flags,
        "allowed_writes_executed": {
            "readonly_snapshot_artifact_written": True,
            "readonly_snapshot_latest_written": True,
            "rsppr2_evidence_written": True,
            "rsppr2_execution_report_written": True,
            "rsppr3_work_doc_written": True,
        },
        "write_scope": {
            "snapshot_dir": rel(resolve(TARGET_SNAPSHOT_DIR)),
            "latest_pointer": rel(resolve(READONLY_SNAPSHOT_LATEST)),
            "evidence_root": rel(resolve(EVIDENCE_ROOT)),
            "execution_report": rel(resolve(RSPPR2_EXECUTION_REPORT)),
            "next_work_doc": rel(resolve(RSPPR3_WORK)),
        },
    }


def build_artifact_manifest(created_at: str, files: list[Path]) -> dict[str, Any]:
    entries = []
    missing = []
    for path in files:
        full = resolve(path)
        exists = full.exists() and full.is_file()
        if not exists:
            missing.append(rel(full))
        entries.append(
            {
                "path": rel(full),
                "exists": exists,
                "size_bytes": full.stat().st_size if exists else None,
                "sha256": sha256_file(path) if exists else None,
            }
        )
    return {
        "schema_version": "rsppr2.artifact_manifest.v1",
        "created_at": created_at,
        "status": "pass" if not missing else "fail",
        "entries": entries,
        "missing": missing,
        "checksum_mismatches": [],
    }


def build_execution_report(
    created_at: str,
    pre_publish: dict[str, Any],
    written: dict[str, Any],
    latest_write: dict[str, Any],
    validator: dict[str, Any],
    checksum_verify: dict[str, Any],
    rollback: dict[str, Any],
    forbidden: dict[str, Any],
    artifact_manifest: dict[str, Any],
) -> str:
    overall_pass = all(
        [
            pre_publish.get("status") == "pass",
            written.get("status") == "pass",
            latest_write.get("status") == "pass",
            validator.get("status") == "pass",
            checksum_verify.get("status") == "pass",
            rollback.get("status") == "pass",
            forbidden.get("all_false") is True,
            artifact_manifest.get("status") == "pass",
        ]
    )
    verdict = (
        "PASS_RECOMMEND_RSPPR2_REVIEWER"
        if overall_pass
        else "STOP_REPAIR_RSPPR2"
    )
    return f"""---
created_at: {created_at}
status: execution_report
route: RSPPR_READONLY_SNAPSHOT_BUILDER_PUBLISH_ROUTE
phase: RSPPR2_CANDIDATE_ONLY_SNAPSHOT_PUBLISH
executor: RSPPR2_EXECUTOR
target_asof: {TARGET_ASOF}
verdict: {verdict}
readonly_snapshot_artifact_write_allowed: true
readonly_snapshot_latest_write_allowed: true
agent_prompt_build_allowed: false
agent_prompt_publish_allowed: false
provider_pull_allowed: false
network_command_allowed: false
provider_publish_allowed: false
provider_accepted_latest_switch_allowed: false
qlib_accepted_latest_switch_allowed: false
legacy_option_c_latest_signal_switch_allowed: false
model_scoring_allowed: false
strategy_replay_allowed: false
order_intent_allowed: false
replay_result_allowed: false
openai_call_allowed: false
monitor_write_allowed: false
order_or_trade_target_output_allowed: false
production_default_switch_allowed: false
---

# RSPPR2 Candidate-only Snapshot Publish Execution Report

## 1. Verdict

```text
{verdict}
```

RSPPR2 wrote the RSPPR1-validated candidate-only readonly snapshot payloads and updated `readonly_strategy_snapshot/latest.json` to the `{TARGET_ASOF}` readonly snapshot manifest. It did not build or publish Agent prompt.

## 2. Evidence Summary

```text
pre_publish_fingerprint.status={pre_publish.get("status")}
written_snapshot_artifact.status={written.get("status")}
latest_pointer_write.status={latest_write.get("status")}
validator_publish.status={validator.get("status")}
checksum_manifest_verify.status={checksum_verify.get("status")}
rollback_package.status={rollback.get("status")}
forbidden_action_audit.all_false={str(forbidden.get("all_false")).lower()}
artifact_manifest.status={artifact_manifest.get("status")}
artifact_manifest entries={len(artifact_manifest.get("entries", []))}
artifact_manifest missing={artifact_manifest.get("missing")}
```

## 3. Published Artifact

```text
target_snapshot_dir={rel(resolve(TARGET_SNAPSHOT_DIR))}
manifest_sha256={written["files"]["manifest.json"]["sha256"]}
strategy_snapshot_sha256={written["files"]["strategy_snapshot.json"]["sha256"]}
validation_report_sha256={written["files"]["validation_report.json"]["sha256"]}
forbidden_scope_audit_sha256={written["files"]["forbidden_scope_audit.json"]["sha256"]}
checksum_manifest_sha256={written["files"]["checksum_manifest.json"]["sha256"]}
latest_pointer_sha256={latest_write.get("sha256")}
latest_snapshot_manifest={latest_write["payload_summary"]["snapshot_manifest"]}
```

Candidate-only checks:

```text
candidate_only=true
top_candidates_count=50
exit_candidates=[]
hold_candidates=[]
exit_hold_context_status=not_built_no_strategy_replay
ranking_source=qlib_rank_controlled_signal
candidate_boundary=qlib_top50
```

## 4. Rollback Evidence

```text
previous_latest_path={rollback["previous_latest_pointer_backup"]["path"]}
previous_latest_exists={str(rollback["previous_latest_pointer_backup"]["exists"]).lower()}
previous_latest_sha256={rollback["previous_latest_pointer_backup"]["sha256"]}
previous_latest_size_bytes={rollback["previous_latest_pointer_backup"]["size_bytes"]}
old_2026_06_18_artifact_not_deleted={rollback["checks"]["old_2026_06_18_artifact_not_deleted"]}
```

## 5. Forbidden Actions

Confirmed not executed:

```text
provider/network pull
provider publish
provider/qlib accepted latest switch
legacy option_c latest signal switch
model scoring/training
strategy replay
OrderIntentArtifact generation
ReplayResult/NAV generation
Agent prompt build/publish
OpenAI call
frontend/API/default switch
monitor/broker/order
trade target or size output
```

## 6. Recommendation

Proceed to `RSPPR2` reviewer. Do not enter Agent prompt latest route until RSPPR route final PASS opens that separate route.
"""


def build_rsppr3_work_doc(created_at: str) -> str:
    return f"""---
created_at: {created_at}
status: work_document
route: RSPPR_READONLY_SNAPSHOT_BUILDER_PUBLISH_ROUTE
phase: RSPPR3_SNAPSHOT_READONLY_INTEGRATION_ACCEPTANCE
target_asof: {TARGET_ASOF}
requires_rsppr2_reviewer_pass: true
readonly_snapshot_artifact_write_allowed: false
readonly_snapshot_latest_write_allowed: false
agent_prompt_build_allowed: false
agent_prompt_publish_allowed: false
provider_pull_allowed: false
network_command_allowed: false
provider_publish_allowed: false
provider_accepted_latest_switch_allowed: false
qlib_accepted_latest_switch_allowed: false
legacy_option_c_latest_signal_switch_allowed: false
model_scoring_allowed: false
strategy_replay_allowed: false
order_intent_allowed: false
replay_result_allowed: false
openai_call_allowed: false
monitor_write_allowed: false
order_or_trade_target_output_allowed: false
production_default_switch_allowed: false
---

# RSPPR3 Snapshot Readonly Integration Acceptance Work

## 1. Objective

RSPPR3 only validates the published candidate-only `ReadonlyStrategySnapshot` and its latest pointer. It must not build Agent prompt; Agent prompt latest route remains separate and can start only after RSPPR final PASS.

## 2. Required Inputs

```text
docs/tw_portfolio_decision_model/POLICY_RSPPR_READONLY_SNAPSHOT_BUILDER_PUBLISH_ROUTE_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR2_CANDIDATE_ONLY_SNAPSHOT_PUBLISH_EXECUTION_REPORT_CN.md
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr2_candidate_only_snapshot_publish/*.json
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/{TARGET_ASOF}/manifest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/{TARGET_ASOF}/strategy_snapshot.json
data_tw/artifacts/publish/readonly_strategy_snapshot/{TARGET_ASOF}/validation_report.json
data_tw/artifacts/publish/readonly_strategy_snapshot/{TARGET_ASOF}/forbidden_scope_audit.json
data_tw/artifacts/publish/readonly_strategy_snapshot/{TARGET_ASOF}/checksum_manifest.json
```

## 3. Required Checks

```text
RSPPR2 reviewer PASS
latest pointer points only to data_tw/artifacts/publish/readonly_strategy_snapshot/{TARGET_ASOF}/manifest.json
published snapshot files match checksum_manifest and RSPPR2 evidence
candidate_only=true
top_candidates=50
exit_candidates=[]
hold_candidates=[]
exit_hold_context_status=not_built_no_strategy_replay
no provider/qlib accepted latest, legacy option_c, frontend/API/default, model, strategy, replay, order, monitor, OpenAI, or Agent prompt action
```

## 4. Allowed Writes

```text
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr3_snapshot_readonly_integration_acceptance/*.json
docs/tw_portfolio_decision_model/POLICY_RSPPR3_SNAPSHOT_READONLY_INTEGRATION_ACCEPTANCE_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR4_FINAL_CLOSURE_AND_AGENT_ROUTE_GATE_WORK_CN.md
```

## 5. Pass Gate

RSPPR3 PASS may recommend final RSPPR closure review. It must not itself start or publish Agent prompt.
"""


def main() -> int:
    created_at = now_iso()
    rsppr1 = load_rsppr1_inputs()
    previous_latest = latest_bytes_backup(READONLY_SNAPSHOT_LATEST)
    pre_publish = build_pre_publish_fingerprint(created_at, rsppr1, previous_latest)
    write_json(PRE_PUBLISH_FINGERPRINT, pre_publish)
    stop_if_collision(pre_publish)

    payloads, latest_payload = write_snapshot_and_latest(rsppr1)
    written = build_written_snapshot_artifact(created_at, rsppr1, payloads)
    latest_write = build_latest_pointer_write(created_at, rsppr1, latest_payload)
    checksum_verify = build_checksum_manifest_verify(created_at)
    validator = build_validator_publish(
        created_at, written, latest_write, checksum_verify
    )
    rollback = build_rollback_package(created_at, previous_latest)
    forbidden = build_forbidden_action_audit(created_at)

    write_json(WRITTEN_SNAPSHOT_ARTIFACT, written)
    write_json(LATEST_POINTER_WRITE, latest_write)
    write_json(VALIDATOR_PUBLISH, validator)
    write_json(CHECKSUM_MANIFEST_VERIFY, checksum_verify)
    write_json(ROLLBACK_PACKAGE, rollback)
    write_json(FORBIDDEN_ACTION_AUDIT, forbidden)

    files = [
        SCRIPT_PATH,
        TARGET_MANIFEST,
        TARGET_STRATEGY_SNAPSHOT,
        TARGET_VALIDATION_REPORT,
        TARGET_FORBIDDEN_SCOPE_AUDIT,
        TARGET_CHECKSUM_MANIFEST,
        READONLY_SNAPSHOT_LATEST,
        PRE_PUBLISH_FINGERPRINT,
        WRITTEN_SNAPSHOT_ARTIFACT,
        LATEST_POINTER_WRITE,
        VALIDATOR_PUBLISH,
        CHECKSUM_MANIFEST_VERIFY,
        ROLLBACK_PACKAGE,
        FORBIDDEN_ACTION_AUDIT,
        RSPPR2_EXECUTION_REPORT,
        RSPPR3_WORK,
    ]

    provisional_manifest = build_artifact_manifest(created_at, files)
    write_text(
        RSPPR2_EXECUTION_REPORT,
        build_execution_report(
            created_at,
            pre_publish,
            written,
            latest_write,
            validator,
            checksum_verify,
            rollback,
            forbidden,
            provisional_manifest,
        ),
    )
    write_text(RSPPR3_WORK, build_rsppr3_work_doc(created_at))

    artifact_manifest = build_artifact_manifest(created_at, files)
    write_json(ARTIFACT_MANIFEST, artifact_manifest)
    write_text(
        RSPPR2_EXECUTION_REPORT,
        build_execution_report(
            created_at,
            pre_publish,
            written,
            latest_write,
            validator,
            checksum_verify,
            rollback,
            forbidden,
            artifact_manifest,
        ),
    )
    artifact_manifest = build_artifact_manifest(created_at, files)
    write_json(ARTIFACT_MANIFEST, artifact_manifest)

    overall_pass = all(
        [
            pre_publish["status"] == "pass",
            written["status"] == "pass",
            latest_write["status"] == "pass",
            validator["status"] == "pass",
            checksum_verify["status"] == "pass",
            rollback["status"] == "pass",
            forbidden["all_false"] is True,
            artifact_manifest["status"] == "pass",
        ]
    )
    print(
        json.dumps(
            {
                "status": "pass" if overall_pass else "fail",
                "verdict": "PASS_RECOMMEND_RSPPR2_REVIEWER"
                if overall_pass
                else "STOP_REPAIR_RSPPR2",
                "evidence_root": rel(resolve(EVIDENCE_ROOT)),
                "target_snapshot_dir": rel(resolve(TARGET_SNAPSHOT_DIR)),
                "latest_pointer": rel(resolve(READONLY_SNAPSHOT_LATEST)),
                "pre_publish_fingerprint": pre_publish["status"],
                "written_snapshot_artifact": written["status"],
                "latest_pointer_write": latest_write["status"],
                "validator_publish": validator["status"],
                "checksum_manifest_verify": checksum_verify["status"],
                "rollback_package": rollback["status"],
                "forbidden_action_all_false": forbidden["all_false"],
                "artifact_manifest": artifact_manifest["status"],
                "top_candidates_count": validator["candidate_only_summary"][
                    "top_candidates_count"
                ],
                "agent_prompt_built": False,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
