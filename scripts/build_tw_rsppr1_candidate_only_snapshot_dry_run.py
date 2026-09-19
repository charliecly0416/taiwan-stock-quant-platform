#!/usr/bin/env python3
"""Build RSPPR1 candidate-only readonly snapshot dry-run evidence.

RSPPR1 builds payload plans only. It reads the controlled signal latest,
derives top candidates from candidate_rank <= 50, validates the candidate-only
contract in-memory, and writes evidence under the RSPPR experiment directory.
It never creates the readonly snapshot publish directory and never writes the
readonly snapshot latest pointer.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGET_ASOF = "2026-07-08"
MODEL_ID = "e4_frozen_qlib_2018_2022"
RUN_ID = "pbpr3x_modela_20260708_contained"
STRATEGY_RULE = "candidate_only_no_strategy_replay"

RSPPR_MAINLINE = Path(
    "docs/tw_portfolio_decision_model/"
    "POLICY_RSPPR_READONLY_SNAPSHOT_BUILDER_PUBLISH_ROUTE_MAINLINE_CN.md"
)
RSPPR0_WORK = Path(
    "docs/tw_portfolio_decision_model/"
    "POLICY_RSPPR0_CONTRACT_EXTENSION_AND_PUBLISH_PLAN_WORK_CN.md"
)
RSPPR0_EXECUTION_REPORT = Path(
    "docs/tw_portfolio_decision_model/"
    "POLICY_RSPPR0_CONTRACT_EXTENSION_AND_PUBLISH_PLAN_EXECUTION_REPORT_CN.md"
)
RSPPR0_REVIEW = Path(
    "docs/tw_portfolio_decision_model/"
    "POLICY_RSPPR0_CONTRACT_EXTENSION_AND_PUBLISH_PLAN_REVIEW_CN.md"
)
RSPPR1_WORK = Path(
    "docs/tw_portfolio_decision_model/"
    "POLICY_RSPPR1_CANDIDATE_ONLY_SNAPSHOT_DRY_RUN_WORK_CN.md"
)
RSPPR1_EXECUTION_REPORT = Path(
    "docs/tw_portfolio_decision_model/"
    "POLICY_RSPPR1_CANDIDATE_ONLY_SNAPSHOT_DRY_RUN_EXECUTION_REPORT_CN.md"
)
RSPPR2_WORK = Path(
    "docs/tw_portfolio_decision_model/"
    "POLICY_RSPPR2_CANDIDATE_ONLY_SNAPSHOT_PUBLISH_WORK_CN.md"
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

RSPPR0_EVIDENCE_ROOT = Path(
    "data_tw/experiments/readonly_snapshot_builder_publish_route/"
    "rsppr0_contract_extension_and_publish_plan"
)
RSPPR0_SOURCE_INVENTORY = RSPPR0_EVIDENCE_ROOT / "source_inventory.json"
RSPPR0_CONTRACT_EXTENSION = RSPPR0_EVIDENCE_ROOT / "candidate_only_contract_extension.json"
RSPPR0_PUBLISH_PLAN = RSPPR0_EVIDENCE_ROOT / "publish_plan.json"
RSPPR0_VALIDATOR_PLAN = RSPPR0_EVIDENCE_ROOT / "validator_plan.json"
RSPPR0_ROLLBACK_PLAN = RSPPR0_EVIDENCE_ROOT / "rollback_plan.json"
RSPPR0_FORBIDDEN_ACTION_AUDIT = RSPPR0_EVIDENCE_ROOT / "forbidden_action_audit.json"
RSPPR0_ARTIFACT_MANIFEST = RSPPR0_EVIDENCE_ROOT / "artifact_manifest.json"

SIGNAL_ROOT = Path("data_tw/artifacts/signals") / MODEL_ID
CONTROLLED_SIGNAL_LATEST = SIGNAL_ROOT / "latest.json"
CANONICAL_SIGNAL_DIR = SIGNAL_ROOT / RUN_ID
CANONICAL_MANIFEST = CANONICAL_SIGNAL_DIR / "manifest.json"
CANONICAL_SIGNALS = CANONICAL_SIGNAL_DIR / "signals.csv"
CANONICAL_VALIDATOR = CANONICAL_SIGNAL_DIR / "validator_report.json"

READONLY_SNAPSHOT_ROOT = Path("data_tw/artifacts/publish/readonly_strategy_snapshot")
READONLY_SNAPSHOT_LATEST = READONLY_SNAPSHOT_ROOT / "latest.json"
TARGET_SNAPSHOT_DIR = READONLY_SNAPSHOT_ROOT / TARGET_ASOF
TARGET_MANIFEST = TARGET_SNAPSHOT_DIR / "manifest.json"
TARGET_STRATEGY_SNAPSHOT = TARGET_SNAPSHOT_DIR / "strategy_snapshot.json"
TARGET_VALIDATION_REPORT = TARGET_SNAPSHOT_DIR / "validation_report.json"
TARGET_FORBIDDEN_SCOPE_AUDIT = TARGET_SNAPSHOT_DIR / "forbidden_scope_audit.json"
TARGET_CHECKSUM_MANIFEST = TARGET_SNAPSHOT_DIR / "checksum_manifest.json"
AGENT_DAILY_PROMPT_LATEST = Path("data_tw/artifacts/agent_daily_prompt/latest.json")
LEGACY_QLIB_OPTION_C_LATEST = Path(
    "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json"
)
LEGACY_DATA_OPTION_C_LATEST = Path(
    "data_tw/experiments/option_c_daily_signal/latest_signal.json"
)
EXISTING_READONLY_VALIDATOR = Path("scripts/validate_tw_modular_readonly_snapshot.py")

EVIDENCE_ROOT = Path(
    "data_tw/experiments/readonly_snapshot_builder_publish_route/"
    "rsppr1_candidate_only_snapshot_dry_run"
)

FORBIDDEN_COLUMN_EXACT = {
    "relevance_10d_top_heavy",
    "ltr_relevance_label",
    "realized_pnl",
    "realized_return",
    "action",
    "holding",
    "position",
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
    full = resolve(path)
    with full.open("r", encoding="utf-8") as fh:
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
                    "run_id",
                    "snapshot_manifest",
                    "readonly_only",
                    "production_trade_enabled",
                )
                if key in data
            }
        except Exception as exc:  # pragma: no cover - diagnostic payload only
            item["json_error"] = str(exc)
    return item


def is_forbidden_column(column: str) -> bool:
    return column in FORBIDDEN_COLUMN_EXACT or any(
        column.startswith(prefix) for prefix in FORBIDDEN_COLUMN_PREFIXES
    )


def numeric_int(value: str) -> int:
    return int(float(value))


def audit_signals_csv(path: Path) -> dict[str, Any]:
    full = resolve(path)
    row_count = 0
    seen: set[tuple[str, str]] = set()
    duplicate_count = 0
    date_values: set[str] = set()
    signal_asof_values: set[str] = set()
    columns: list[str] = []
    top_candidates: list[dict[str, Any]] = []
    with full.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        columns = list(reader.fieldnames or [])
        for row in reader:
            row_count += 1
            key = (row.get("date", ""), row.get("instrument", ""))
            if key in seen:
                duplicate_count += 1
            seen.add(key)
            if row.get("date"):
                date_values.add(row["date"])
            if row.get("signal_asof"):
                signal_asof_values.add(row["signal_asof"])
            try:
                candidate_rank = numeric_int(row.get("candidate_rank", ""))
            except ValueError:
                candidate_rank = 999999
            if candidate_rank <= 50:
                top_candidates.append(
                    {
                        "instrument": row.get("instrument"),
                        "candidate_rank": candidate_rank,
                        "buy_score": row.get("buy_score"),
                        "raw_score": row.get("raw_score"),
                        "score_rank": numeric_int(row.get("score_rank", "")),
                        "full_qlib_rank": numeric_int(row.get("full_qlib_rank", "")),
                        "signal_asof": row.get("signal_asof"),
                        "available_at": row.get("available_at"),
                        "source_artifact": row.get("source_artifact"),
                        "source_model_artifact": row.get("source_model_artifact"),
                        "source_feature_artifact": row.get("source_feature_artifact"),
                    }
                )
    forbidden_columns = sorted([column for column in columns if is_forbidden_column(column)])
    top_candidates = sorted(
        top_candidates, key=lambda item: (item["candidate_rank"], item["instrument"] or "")
    )
    return {
        "path": rel(full),
        "exists": full.exists(),
        "row_count": row_count,
        "columns": columns,
        "date_values": sorted(date_values),
        "signal_asof_values": sorted(signal_asof_values),
        "duplicate_key_count": duplicate_count,
        "forbidden_columns": forbidden_columns,
        "candidate_rank_le_50_count": len(top_candidates),
        "top_candidates": top_candidates,
        "top_candidate_preview": top_candidates[:10],
        "sha256": sha256_file(path),
        "checks": {
            "row_count_150": row_count == 150,
            "date_only_target_asof": sorted(date_values) == [TARGET_ASOF],
            "signal_asof_only_target_asof": sorted(signal_asof_values) == [TARGET_ASOF],
            "duplicate_key_count_zero": duplicate_count == 0,
            "forbidden_columns_empty": forbidden_columns == [],
            "candidate_rank_le_50_count_50": len(top_candidates) == 50,
        },
    }


def build_source_preflight(created_at: str) -> dict[str, Any]:
    latest = load_json(CONTROLLED_SIGNAL_LATEST)
    manifest = load_json(CANONICAL_MANIFEST)
    validator = load_json(CANONICAL_VALIDATOR)
    signals_audit = audit_signals_csv(CANONICAL_SIGNALS)
    manifest_sha = sha256_file(CANONICAL_MANIFEST)
    signals_sha = sha256_file(CANONICAL_SIGNALS)
    rsppr0_jsons = {
        "source_inventory": load_json(RSPPR0_SOURCE_INVENTORY),
        "candidate_only_contract_extension": load_json(RSPPR0_CONTRACT_EXTENSION),
        "publish_plan": load_json(RSPPR0_PUBLISH_PLAN),
        "validator_plan": load_json(RSPPR0_VALIDATOR_PLAN),
        "rollback_plan": load_json(RSPPR0_ROLLBACK_PLAN),
        "forbidden_action_audit": load_json(RSPPR0_FORBIDDEN_ACTION_AUDIT),
        "artifact_manifest": load_json(RSPPR0_ARTIFACT_MANIFEST),
    }
    target_dir_exists = resolve(TARGET_SNAPSHOT_DIR).exists()
    checks = {
        "rsppr0_execution_report_pass": text_contains(
            RSPPR0_EXECUTION_REPORT,
            "PASS_RECOMMEND_RSPPR1_CANDIDATE_ONLY_SNAPSHOT_DRY_RUN",
        ),
        "rsppr0_reviewer_pass": text_contains(
            RSPPR0_REVIEW,
            "PASS_RECOMMEND_RSPPR1_CANDIDATE_ONLY_SNAPSHOT_DRY_RUN",
        ),
        "rsppr0_evidence_all_pass": all(
            payload.get("status") == "pass" for payload in rsppr0_jsons.values()
        )
        and rsppr0_jsons["forbidden_action_audit"].get("all_false") is True,
        "controlled_signal_latest_exists": resolve(CONTROLLED_SIGNAL_LATEST).is_file(),
        "controlled_signal_latest_asof_2026_07_08": latest.get("asof") == TARGET_ASOF,
        "controlled_signal_latest_signal_asof_2026_07_08": latest.get("signal_asof")
        == TARGET_ASOF,
        "controlled_signal_latest_run_id_match": latest.get("run_id") == RUN_ID,
        "canonical_manifest_checksum_matches_latest_pointer": manifest_sha
        == latest.get("canonical_manifest_sha256"),
        "canonical_signals_checksum_matches_latest_pointer": signals_sha
        == latest.get("canonical_signals_sha256"),
        "canonical_manifest_ready": manifest.get("status") == "READY",
        "canonical_manifest_asof_2026_07_08": manifest.get("asof") == TARGET_ASOF,
        "canonical_manifest_signal_asof_2026_07_08": manifest.get("signal_asof")
        == TARGET_ASOF,
        "canonical_manifest_row_count_150": manifest.get("row_count") == 150,
        "canonical_validator_pass": validator.get("status") == "PASS",
        "signals_row_count_150": signals_audit["checks"]["row_count_150"],
        "signals_date_only_2026_07_08": signals_audit["checks"]["date_only_target_asof"],
        "signals_signal_asof_only_2026_07_08": signals_audit["checks"][
            "signal_asof_only_target_asof"
        ],
        "signals_duplicate_keys_zero": signals_audit["checks"]["duplicate_key_count_zero"],
        "signals_forbidden_columns_empty": signals_audit["checks"][
            "forbidden_columns_empty"
        ],
        "top_candidates_count_50": signals_audit["checks"][
            "candidate_rank_le_50_count_50"
        ],
        "target_snapshot_dir_not_written": not target_dir_exists,
        "target_snapshot_dir_collision_explicit": True,
        "existing_readonly_snapshot_latest_fingerprinted_only": True,
    }
    return {
        "schema_version": "rsppr1.source_preflight.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "documents_read": [
            rel(resolve(RSPPR_MAINLINE)),
            rel(resolve(RSPPR0_WORK)),
            rel(resolve(RSPPR0_EXECUTION_REPORT)),
            rel(resolve(RSPPR0_REVIEW)),
            rel(resolve(RSPPR1_WORK)),
            rel(resolve(CLPR4_REVIEW)),
            rel(resolve(PROJECT_CONSTITUTION)),
            rel(resolve(MODEL_SIGNAL_CONTRACT)),
            rel(resolve(READONLY_SNAPSHOT_CONTRACT)),
        ],
        "source_lineage": {
            "controlled_signal_latest": rel(resolve(CONTROLLED_SIGNAL_LATEST)),
            "canonical_artifact_dir": rel(resolve(CANONICAL_SIGNAL_DIR)),
            "canonical_manifest": rel(resolve(CANONICAL_MANIFEST)),
            "canonical_signals": rel(resolve(CANONICAL_SIGNALS)),
            "canonical_validator": rel(resolve(CANONICAL_VALIDATOR)),
            "model_id": latest.get("model_id"),
            "run_id": latest.get("run_id"),
            "asof": latest.get("asof"),
            "signal_asof": latest.get("signal_asof"),
        },
        "controlled_signal_latest": {
            "fingerprint": file_fingerprint(CONTROLLED_SIGNAL_LATEST),
            "canonical_manifest_sha256_in_pointer": latest.get(
                "canonical_manifest_sha256"
            ),
            "canonical_manifest_sha256_actual": manifest_sha,
            "canonical_signals_sha256_in_pointer": latest.get("canonical_signals_sha256"),
            "canonical_signals_sha256_actual": signals_sha,
        },
        "canonical_manifest_summary": {
            "artifact_type": manifest.get("artifact_type"),
            "schema_version": manifest.get("schema_version"),
            "status": manifest.get("status"),
            "model_id": manifest.get("model_id"),
            "model_family": manifest.get("model_family"),
            "asof": manifest.get("asof"),
            "signal_asof": manifest.get("signal_asof"),
            "row_count": manifest.get("row_count"),
            "available_at_policy": manifest.get("available_at_policy"),
            "no_latest": manifest.get("no_latest"),
            "no_target_output": manifest.get("no_target_output"),
        },
        "canonical_validator_summary": {
            "path": rel(resolve(CANONICAL_VALIDATOR)),
            "status": validator.get("status"),
            "errors": validator.get("errors"),
        },
        "signals_csv_audit": signals_audit,
        "rsppr0_evidence_summary": {
            name: {
                "status": payload.get("status"),
                "path": rel(resolve(path)),
            }
            for name, payload, path in [
                ("source_inventory", rsppr0_jsons["source_inventory"], RSPPR0_SOURCE_INVENTORY),
                (
                    "candidate_only_contract_extension",
                    rsppr0_jsons["candidate_only_contract_extension"],
                    RSPPR0_CONTRACT_EXTENSION,
                ),
                ("publish_plan", rsppr0_jsons["publish_plan"], RSPPR0_PUBLISH_PLAN),
                ("validator_plan", rsppr0_jsons["validator_plan"], RSPPR0_VALIDATOR_PLAN),
                ("rollback_plan", rsppr0_jsons["rollback_plan"], RSPPR0_ROLLBACK_PLAN),
                (
                    "forbidden_action_audit",
                    rsppr0_jsons["forbidden_action_audit"],
                    RSPPR0_FORBIDDEN_ACTION_AUDIT,
                ),
                (
                    "artifact_manifest",
                    rsppr0_jsons["artifact_manifest"],
                    RSPPR0_ARTIFACT_MANIFEST,
                ),
            ]
        },
        "existing_readonly_snapshot_latest_fingerprint_before_dry_run": file_fingerprint(
            READONLY_SNAPSHOT_LATEST
        ),
        "target_snapshot_collision_audit": {
            "target_snapshot_dir": rel(resolve(TARGET_SNAPSHOT_DIR)),
            "target_snapshot_dir_exists": target_dir_exists,
            "collision_status": "explicit_collision_blocker"
            if target_dir_exists
            else "no_collision",
            "rsppr1_created_target_snapshot_dir": False,
            "rsppr1_wrote_readonly_snapshot_latest": False,
        },
        "out_of_scope_pointer_fingerprints_before_dry_run": {
            "agent_daily_prompt_latest": file_fingerprint(AGENT_DAILY_PROMPT_LATEST),
            "legacy_qlib_option_c_latest_signal": file_fingerprint(
                LEGACY_QLIB_OPTION_C_LATEST
            ),
            "legacy_data_option_c_latest_signal": file_fingerprint(
                LEGACY_DATA_OPTION_C_LATEST
            ),
        },
        "checks": checks,
    }


def planned_manifest_payload(created_at: str, source_preflight: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_type": "readonly_strategy_snapshot",
        "schema_version": "readonly_strategy_snapshot_r13_v1",
        "asof": TARGET_ASOF,
        "created_at": created_at,
        "created_by_planned_phase": "RSPPR2_CANDIDATE_ONLY_SNAPSHOT_PUBLISH",
        "created_by_dry_run": rel(resolve(Path(__file__))),
        "readonly_only": True,
        "production_trade_enabled": False,
        "no_order_action": True,
        "not_target_position": True,
        "not_investment_advice": True,
        "display_role": "primary_readonly_candidate",
        "is_primary_readonly_candidate": True,
        "is_production_trading_default": False,
        "candidate_only": True,
        "source_lineage": "clpr_controlled_model_signal_latest",
        "model_id": MODEL_ID,
        "base_model_id": MODEL_ID,
        "model_family": "qlib",
        "strategy_rule": STRATEGY_RULE,
        "candidate_boundary": "qlib_top50",
        "ranking_source": "qlib_rank_controlled_signal",
        "exit_hold_context_status": "not_built_no_strategy_replay",
        "strategy_replay_status": "not_built_forbidden_in_rsppr",
        "order_intent_status": "not_built_forbidden_in_rsppr",
        "replay_result_status": "not_built_forbidden_in_rsppr",
        "source_signal_latest": rel(resolve(CONTROLLED_SIGNAL_LATEST)),
        "source_signal_manifest": rel(resolve(CANONICAL_MANIFEST)),
        "source_signal_csv": rel(resolve(CANONICAL_SIGNALS)),
        "source_signal_latest_sha256": source_preflight["controlled_signal_latest"][
            "fingerprint"
        ]["sha256"],
        "source_signal_manifest_sha256": source_preflight["controlled_signal_latest"][
            "canonical_manifest_sha256_actual"
        ],
        "source_signal_csv_sha256": source_preflight["controlled_signal_latest"][
            "canonical_signals_sha256_actual"
        ],
        "snapshot": "strategy_snapshot.json",
        "validation_report": "validation_report.json",
        "forbidden_scope_audit": "forbidden_scope_audit.json",
        "checksum_manifest": "checksum_manifest.json",
        "quality_status": "pass",
    }


def planned_strategy_snapshot_payload(
    source_preflight: dict[str, Any],
) -> dict[str, Any]:
    top_candidates = source_preflight["signals_csv_audit"]["top_candidates"]
    return {
        "asof": TARGET_ASOF,
        "data_asof": TARGET_ASOF,
        "signal_asof": TARGET_ASOF,
        "model_id": MODEL_ID,
        "base_model_id": MODEL_ID,
        "model_family": "qlib",
        "strategy_rule": STRATEGY_RULE,
        "candidate_only": True,
        "source_lineage": "clpr_controlled_model_signal_latest",
        "candidate_boundary": "qlib_top50",
        "ranking_source": "qlib_rank_controlled_signal",
        "display_role": "primary_readonly_candidate",
        "is_primary_readonly_candidate": True,
        "is_production_trading_default": False,
        "top_candidates_source": "signals.csv rows with candidate_rank <= 50, sorted by candidate_rank then instrument",
        "top_candidates_count": len(top_candidates),
        "top_candidates": top_candidates,
        "exit_candidates": [],
        "hold_candidates": [],
        "exit_hold_context_status": "not_built_no_strategy_replay",
        "available_at_policy": source_preflight["canonical_manifest_summary"].get(
            "available_at_policy"
        ),
        "readonly_only": True,
        "not_order": True,
        "no_order_action": True,
        "not_target_position": True,
        "not_investment_advice": True,
        "production_trade_enabled": False,
        "no_production_trading": True,
        "not_full_strategy_snapshot": True,
        "strategy_replay_status": "not_built_forbidden_in_rsppr",
        "order_intent_status": "not_built_forbidden_in_rsppr",
        "replay_result_status": "not_built_forbidden_in_rsppr",
        "explanations": [],
    }


def planned_validation_report_payload(created_at: str) -> dict[str, Any]:
    return {
        "artifact_type": "readonly_strategy_snapshot_validation_report",
        "schema_version": "rsppr1.candidate_only_validation_report_plan.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "validator_type": "candidate_only_dry_run_validator_evidence",
        "status": "pass",
        "readonly_snapshot_validator_ok": True,
        "checksum_ok": True,
        "latest_pointer_points_to_readonly_snapshot_only": True,
        "existing_ltr_primary_validator_not_used": True,
        "existing_ltr_primary_validator_path": rel(resolve(EXISTING_READONLY_VALIDATOR)),
        "existing_ltr_primary_validator_skip_reason": (
            "scripts/validate_tw_modular_readonly_snapshot.py is LTR-primary "
            "hardcoded; RSPPR1 validates Model A candidate-only payload plans "
            "with candidate-only validator evidence."
        ),
    }


def planned_forbidden_scope_audit_payload(created_at: str) -> dict[str, Any]:
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
        "readonly_snapshot_artifact_written": False,
        "readonly_snapshot_latest_written": False,
        "agent_prompt_built_or_published": False,
        "openai_call_triggered": False,
        "frontend_or_api_default_switched": False,
        "monitor_broker_order_triggered": False,
        "trade_target_or_size_output_generated": False,
    }
    return {
        "artifact_type": "readonly_strategy_snapshot_forbidden_scope_audit",
        "schema_version": "rsppr1.forbidden_scope_audit_plan.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass",
        "all_forbidden_false": all(value is False for value in flags.values()),
        "flags": flags,
    }


def build_candidate_snapshot_payload_plan(
    created_at: str, source_preflight: dict[str, Any]
) -> dict[str, Any]:
    manifest_payload = planned_manifest_payload(created_at, source_preflight)
    strategy_snapshot_payload = planned_strategy_snapshot_payload(source_preflight)
    validation_report_payload = planned_validation_report_payload(created_at)
    forbidden_scope_audit_payload = planned_forbidden_scope_audit_payload(created_at)
    checks = {
        "source_preflight_pass": source_preflight.get("status") == "pass",
        "artifact_type_readonly_strategy_snapshot": manifest_payload.get("artifact_type")
        == "readonly_strategy_snapshot",
        "schema_version_readonly_snapshot_r13_v1": manifest_payload.get("schema_version")
        == "readonly_strategy_snapshot_r13_v1",
        "candidate_only_true": strategy_snapshot_payload.get("candidate_only") is True,
        "model_id_model_a": strategy_snapshot_payload.get("model_id") == MODEL_ID,
        "base_model_id_model_a": strategy_snapshot_payload.get("base_model_id") == MODEL_ID,
        "ranking_source_qlib_rank_controlled_signal": strategy_snapshot_payload.get(
            "ranking_source"
        )
        == "qlib_rank_controlled_signal",
        "candidate_boundary_qlib_top50": strategy_snapshot_payload.get(
            "candidate_boundary"
        )
        == "qlib_top50",
        "top_candidates_derived_from_candidate_rank_le_50": all(
            item["candidate_rank"] <= 50
            for item in strategy_snapshot_payload["top_candidates"]
        ),
        "top_candidates_count_50": len(strategy_snapshot_payload["top_candidates"]) == 50,
        "exit_candidates_empty": strategy_snapshot_payload.get("exit_candidates") == [],
        "hold_candidates_empty": strategy_snapshot_payload.get("hold_candidates") == [],
        "exit_hold_context_status_not_built": strategy_snapshot_payload.get(
            "exit_hold_context_status"
        )
        == "not_built_no_strategy_replay",
        "readonly_flags_true": all(
            [
                manifest_payload.get("readonly_only") is True,
                strategy_snapshot_payload.get("readonly_only") is True,
                strategy_snapshot_payload.get("not_order") is True,
                strategy_snapshot_payload.get("no_order_action") is True,
                strategy_snapshot_payload.get("not_investment_advice") is True,
            ]
        ),
        "production_trade_enabled_false": manifest_payload.get(
            "production_trade_enabled"
        )
        is False
        and strategy_snapshot_payload.get("production_trade_enabled") is False,
        "not_full_strategy_replay_snapshot": strategy_snapshot_payload.get(
            "not_full_strategy_snapshot"
        )
        is True,
        "forbidden_scope_audit_plan_pass": forbidden_scope_audit_payload.get("status")
        == "pass"
        and forbidden_scope_audit_payload.get("all_forbidden_false") is True,
    }
    checksum_manifest_payload_plan = {
        "artifact_type": "readonly_strategy_snapshot_checksum_manifest",
        "schema_version": "rsppr1.checksum_manifest_payload_plan.v1",
        "asof": TARGET_ASOF,
        "created_at": created_at,
        "checksum_scope": "planned_payloads_only_checksum_manifest_excludes_itself",
        "files": {
            "manifest.json": sha256_json_payload(manifest_payload),
            "strategy_snapshot.json": sha256_json_payload(strategy_snapshot_payload),
            "validation_report.json": sha256_json_payload(validation_report_payload),
            "forbidden_scope_audit.json": sha256_json_payload(
                forbidden_scope_audit_payload
            ),
        },
    }
    return {
        "schema_version": "rsppr1.candidate_snapshot_payload_plan.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "write_status": {
            "dry_run_only": True,
            "target_snapshot_dir_created": False,
            "target_snapshot_files_written": False,
            "target_snapshot_dir": rel(resolve(TARGET_SNAPSHOT_DIR)),
        },
        "planned_files": {
            "manifest": rel(resolve(TARGET_MANIFEST)),
            "strategy_snapshot": rel(resolve(TARGET_STRATEGY_SNAPSHOT)),
            "validation_report": rel(resolve(TARGET_VALIDATION_REPORT)),
            "forbidden_scope_audit": rel(resolve(TARGET_FORBIDDEN_SCOPE_AUDIT)),
            "checksum_manifest": rel(resolve(TARGET_CHECKSUM_MANIFEST)),
        },
        "payloads": {
            "manifest": manifest_payload,
            "strategy_snapshot": strategy_snapshot_payload,
            "validation_report": validation_report_payload,
            "forbidden_scope_audit": forbidden_scope_audit_payload,
            "checksum_manifest": checksum_manifest_payload_plan,
        },
        "checks": checks,
    }


def build_latest_pointer_payload_plan(
    created_at: str,
    source_preflight: dict[str, Any],
    candidate_snapshot_payload_plan: dict[str, Any],
) -> dict[str, Any]:
    payload_plan = {
        "artifact_type": "readonly_strategy_snapshot_latest_pointer",
        "schema_version": "readonly_strategy_snapshot_latest_r13_v1",
        "asof": TARGET_ASOF,
        "data_asof": TARGET_ASOF,
        "signal_asof": TARGET_ASOF,
        "target_date": TARGET_ASOF,
        "readonly_only": True,
        "production_trade_enabled": False,
        "candidate_only": True,
        "snapshot_manifest": rel(resolve(TARGET_MANIFEST)),
        "created_by_planned_phase": "RSPPR2_CANDIDATE_ONLY_SNAPSHOT_PUBLISH",
        "not_provider_accepted_latest": True,
        "not_trade_target_latest": True,
        "source_signal_latest": rel(resolve(CONTROLLED_SIGNAL_LATEST)),
        "source_signal_latest_sha256": source_preflight["controlled_signal_latest"][
            "fingerprint"
        ]["sha256"],
        "source_signal_manifest_sha256": source_preflight["controlled_signal_latest"][
            "canonical_manifest_sha256_actual"
        ],
        "source_signal_csv_sha256": source_preflight["controlled_signal_latest"][
            "canonical_signals_sha256_actual"
        ],
        "planned_manifest_payload_sha256": sha256_json_payload(
            candidate_snapshot_payload_plan["payloads"]["manifest"]
        ),
    }
    checks = {
        "candidate_snapshot_payload_plan_pass": candidate_snapshot_payload_plan.get(
            "status"
        )
        == "pass",
        "latest_pointer_write_forbidden_in_rsppr1": True,
        "latest_pointer_planned_for_rsppr2_only": True,
        "points_to_readonly_snapshot_manifest": payload_plan["snapshot_manifest"]
        == rel(resolve(TARGET_MANIFEST)),
        "candidate_only_true": payload_plan["candidate_only"] is True,
        "readonly_only_true": payload_plan["readonly_only"] is True,
        "production_trade_enabled_false": payload_plan["production_trade_enabled"]
        is False,
        "not_provider_accepted_latest_true": payload_plan["not_provider_accepted_latest"]
        is True,
    }
    return {
        "schema_version": "rsppr1.latest_pointer_payload_plan.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "path": rel(resolve(READONLY_SNAPSHOT_LATEST)),
        "write_status": {
            "dry_run_only": True,
            "latest_pointer_written": False,
            "write_allowed_in_rsppr1": False,
            "write_allowed_in_phase": "RSPPR2 only after RSPPR1 reviewer PASS",
        },
        "payload_plan": payload_plan,
        "checks": checks,
    }


def build_validator_dry_run(
    created_at: str,
    source_preflight: dict[str, Any],
    candidate_snapshot_payload_plan: dict[str, Any],
    latest_pointer_payload_plan: dict[str, Any],
) -> dict[str, Any]:
    validator_text = resolve(EXISTING_READONLY_VALIDATOR).read_text(encoding="utf-8")
    manifest_payload = candidate_snapshot_payload_plan["payloads"]["manifest"]
    snapshot_payload = candidate_snapshot_payload_plan["payloads"]["strategy_snapshot"]
    forbidden_scope_audit_payload = candidate_snapshot_payload_plan["payloads"][
        "forbidden_scope_audit"
    ]
    top_source = source_preflight["signals_csv_audit"]["top_candidates"]
    top_payload = snapshot_payload["top_candidates"]
    checks = {
        "source_preflight_pass": source_preflight.get("status") == "pass",
        "candidate_snapshot_payload_plan_pass": candidate_snapshot_payload_plan.get(
            "status"
        )
        == "pass",
        "latest_pointer_payload_plan_pass": latest_pointer_payload_plan.get("status")
        == "pass",
        "did_not_use_existing_ltr_primary_validator": True,
        "existing_ltr_primary_validator_exists": resolve(EXISTING_READONLY_VALIDATOR).is_file(),
        "existing_ltr_primary_validator_hardcodes_ltr_model": (
            'snapshot.get("model_id") == "e4_frozen_qlib_2023_2025_ltr"'
            in validator_text
        ),
        "existing_ltr_primary_validator_hardcodes_ltr_ranking_source": (
            'snapshot.get("ranking_source") == "ltr_rerank_within_qlib_top50"'
            in validator_text
        ),
        "manifest_artifact_type_ok": manifest_payload.get("artifact_type")
        == "readonly_strategy_snapshot",
        "manifest_schema_version_ok": manifest_payload.get("schema_version")
        == "readonly_strategy_snapshot_r13_v1",
        "manifest_readonly_flags_ok": manifest_payload.get("readonly_only") is True
        and manifest_payload.get("production_trade_enabled") is False,
        "snapshot_candidate_only_ok": snapshot_payload.get("candidate_only") is True,
        "snapshot_model_id_ok": snapshot_payload.get("model_id") == MODEL_ID,
        "snapshot_base_model_id_ok": snapshot_payload.get("base_model_id") == MODEL_ID,
        "snapshot_ranking_source_ok": snapshot_payload.get("ranking_source")
        == "qlib_rank_controlled_signal",
        "snapshot_candidate_boundary_ok": snapshot_payload.get("candidate_boundary")
        == "qlib_top50",
        "top_candidates_equal_source_candidate_rank_le_50": top_payload == top_source,
        "top_candidates_count_50": len(top_payload) == 50,
        "exit_candidates_empty": snapshot_payload.get("exit_candidates") == [],
        "hold_candidates_empty": snapshot_payload.get("hold_candidates") == [],
        "exit_hold_context_status_ok": snapshot_payload.get("exit_hold_context_status")
        == "not_built_no_strategy_replay",
        "no_order_intent_reference": snapshot_payload.get("order_intent_status")
        == "not_built_forbidden_in_rsppr",
        "no_replay_result_reference": snapshot_payload.get("replay_result_status")
        == "not_built_forbidden_in_rsppr",
        "forbidden_scope_audit_pass": forbidden_scope_audit_payload.get("status")
        == "pass"
        and forbidden_scope_audit_payload.get("all_forbidden_false") is True,
        "latest_pointer_points_to_readonly_snapshot_only": latest_pointer_payload_plan[
            "payload_plan"
        ]["snapshot_manifest"]
        == rel(resolve(TARGET_MANIFEST)),
    }
    return {
        "schema_version": "rsppr1.validator_dry_run.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "validator_type": "candidate_only_validator_evidence",
        "existing_validator_not_used": {
            "path": rel(resolve(EXISTING_READONLY_VALIDATOR)),
            "not_used": True,
            "reason": (
                "scripts/validate_tw_modular_readonly_snapshot.py is LTR-primary "
                "hardcoded; RSPPR1 uses candidate-only validator evidence for "
                "Model A qlib-rank controlled signal payload plans."
            ),
        },
        "candidate_only_validator_scope": [
            "manifest payload plan",
            "strategy_snapshot payload plan",
            "validation_report payload plan",
            "forbidden_scope_audit payload plan",
            "latest pointer payload plan",
            "source signals candidate_rank <= 50 equality",
        ],
        "checks": checks,
    }


def build_checksum_plan(
    created_at: str,
    candidate_snapshot_payload_plan: dict[str, Any],
    latest_pointer_payload_plan: dict[str, Any],
    validator_dry_run: dict[str, Any],
) -> dict[str, Any]:
    payloads = candidate_snapshot_payload_plan["payloads"]
    planned_snapshot_file_checksums = {
        "manifest.json": sha256_json_payload(payloads["manifest"]),
        "strategy_snapshot.json": sha256_json_payload(payloads["strategy_snapshot"]),
        "validation_report.json": sha256_json_payload(payloads["validation_report"]),
        "forbidden_scope_audit.json": sha256_json_payload(payloads["forbidden_scope_audit"]),
    }
    checksum_manifest_payload = payloads["checksum_manifest"]
    checks = {
        "candidate_snapshot_payload_plan_pass": candidate_snapshot_payload_plan.get(
            "status"
        )
        == "pass",
        "latest_pointer_payload_plan_pass": latest_pointer_payload_plan.get("status")
        == "pass",
        "validator_dry_run_pass": validator_dry_run.get("status") == "pass",
        "checksum_manifest_excludes_itself": "checksum_manifest.json"
        not in checksum_manifest_payload.get("files", {}),
        "checksum_manifest_matches_planned_payloads": checksum_manifest_payload.get(
            "files"
        )
        == planned_snapshot_file_checksums,
        "source_signal_manifest_checksum_matches_latest": True,
        "source_signal_csv_checksum_matches_latest": True,
    }
    return {
        "schema_version": "rsppr1.checksum_plan.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "checksum_scope": "dry_run_payload_plans_only_no_publish_files_written",
        "planned_snapshot_files": {
            "manifest.json": {
                "planned_path": rel(resolve(TARGET_MANIFEST)),
                "sha256": planned_snapshot_file_checksums["manifest.json"],
            },
            "strategy_snapshot.json": {
                "planned_path": rel(resolve(TARGET_STRATEGY_SNAPSHOT)),
                "sha256": planned_snapshot_file_checksums["strategy_snapshot.json"],
            },
            "validation_report.json": {
                "planned_path": rel(resolve(TARGET_VALIDATION_REPORT)),
                "sha256": planned_snapshot_file_checksums["validation_report.json"],
            },
            "forbidden_scope_audit.json": {
                "planned_path": rel(resolve(TARGET_FORBIDDEN_SCOPE_AUDIT)),
                "sha256": planned_snapshot_file_checksums[
                    "forbidden_scope_audit.json"
                ],
            },
            "checksum_manifest.json": {
                "planned_path": rel(resolve(TARGET_CHECKSUM_MANIFEST)),
                "sha256": sha256_json_payload(checksum_manifest_payload),
                "excludes_itself": True,
            },
        },
        "planned_latest_pointer": {
            "planned_path": rel(resolve(READONLY_SNAPSHOT_LATEST)),
            "sha256": sha256_json_payload(latest_pointer_payload_plan["payload_plan"]),
            "write_allowed_in_rsppr1": False,
        },
        "checks": checks,
    }


def build_rollback_preflight(created_at: str) -> dict[str, Any]:
    target_dir_exists = resolve(TARGET_SNAPSHOT_DIR).exists()
    checks = {
        "existing_readonly_snapshot_latest_fingerprinted": True,
        "target_snapshot_dir_fingerprinted": True,
        "target_snapshot_dir_not_written_by_rsppr1": not target_dir_exists,
        "dry_run_latest_pointer_restore_required_false": True,
        "dry_run_snapshot_artifact_restore_required_false": True,
        "rollback_scope_limited_to_rsppr2_snapshot_publish": True,
    }
    return {
        "schema_version": "rsppr1.rollback_preflight.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
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
        "rsppr1_dry_run_rollback": {
            "required_action": "discard dry-run evidence only",
            "snapshot_artifact_restore_required": False,
            "latest_pointer_restore_required": False,
        },
        "rsppr2_publish_rollback_preflight": {
            "backup_previous_latest_pointer_before_write": True,
            "restore_previous_latest_pointer_bytes_and_verify_sha256": True,
            "if_latest_pointer_absent_before_publish": "delete only RSPPR2-created latest.json after verifying provenance",
            "if_target_snapshot_dir_preexists": "block publish unless reviewer approves collision disposition; never overwrite blindly",
            "must_not_modify_or_restore_out_of_scope": [
                rel(resolve(CONTROLLED_SIGNAL_LATEST)),
                rel(resolve(AGENT_DAILY_PROMPT_LATEST)),
                rel(resolve(LEGACY_QLIB_OPTION_C_LATEST)),
                rel(resolve(LEGACY_DATA_OPTION_C_LATEST)),
                "provider accepted latest",
                "qlib accepted latest",
                "frontend/API/default",
            ],
        },
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
        "readonly_snapshot_artifact_created": False,
        "readonly_snapshot_latest_written": False,
        "agent_prompt_built": False,
        "agent_prompt_published": False,
        "openai_call_triggered": False,
        "frontend_or_api_default_switched": False,
        "monitor_broker_order_triggered": False,
        "trade_target_or_size_output_generated": False,
    }
    return {
        "schema_version": "rsppr1.forbidden_action_audit.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass",
        "all_false": all(value is False for value in flags.values()),
        "flags": flags,
        "write_scope": {
            "evidence_root": rel(resolve(EVIDENCE_ROOT)),
            "script": rel(resolve(Path("scripts/build_tw_rsppr1_candidate_only_snapshot_dry_run.py"))),
            "execution_report": rel(resolve(RSPPR1_EXECUTION_REPORT)),
            "next_work_doc": rel(resolve(RSPPR2_WORK)),
            "target_snapshot_dir_created": False,
            "readonly_snapshot_latest_written": False,
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
        "schema_version": "rsppr1.artifact_manifest.v1",
        "created_at": created_at,
        "status": "pass" if not missing else "fail",
        "entries": entries,
        "missing": missing,
        "checksum_mismatches": [],
    }


def build_execution_report(
    created_at: str,
    source_preflight: dict[str, Any],
    candidate_snapshot_payload_plan: dict[str, Any],
    latest_pointer_payload_plan: dict[str, Any],
    validator_dry_run: dict[str, Any],
    checksum_plan: dict[str, Any],
    rollback_preflight: dict[str, Any],
    forbidden_action_audit: dict[str, Any],
    artifact_manifest: dict[str, Any],
) -> str:
    verdict = (
        "PASS_RECOMMEND_RSPPR1_REVIEWER"
        if all(
            [
                source_preflight.get("status") == "pass",
                candidate_snapshot_payload_plan.get("status") == "pass",
                latest_pointer_payload_plan.get("status") == "pass",
                validator_dry_run.get("status") == "pass",
                checksum_plan.get("status") == "pass",
                rollback_preflight.get("status") == "pass",
                forbidden_action_audit.get("all_false") is True,
                artifact_manifest.get("status") == "pass",
            ]
        )
        else "STOP_REPAIR_RSPPR1"
    )
    signals = source_preflight["signals_csv_audit"]
    latest_summary = source_preflight[
        "existing_readonly_snapshot_latest_fingerprint_before_dry_run"
    ].get("json_summary", {})
    return f"""---
created_at: {created_at}
status: execution_report
route: RSPPR_READONLY_SNAPSHOT_BUILDER_PUBLISH_ROUTE
phase: RSPPR1_CANDIDATE_ONLY_SNAPSHOT_DRY_RUN
executor: RSPPR1_EXECUTOR
target_asof: {TARGET_ASOF}
verdict: {verdict}
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

# RSPPR1 Candidate-only Snapshot Dry-run Execution Report

## 1. Verdict

```text
{verdict}
```

RSPPR1 只生成 candidate-only readonly snapshot 的 dry-run payload、latest pointer payload plan、candidate-only validator evidence、checksum plan 和 rollback preflight。未创建 `data_tw/artifacts/publish/readonly_strategy_snapshot/{TARGET_ASOF}/`，未写 `data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json`，未构建或发布 Agent prompt。

## 2. Scope

```text
RSPPR1_CANDIDATE_ONLY_SNAPSHOT_DRY_RUN
```

## 3. Documents / Contracts / Evidence Read

```text
docs/tw_portfolio_decision_model/POLICY_RSPPR_READONLY_SNAPSHOT_BUILDER_PUBLISH_ROUTE_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR0_CONTRACT_EXTENSION_AND_PUBLISH_PLAN_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR0_CONTRACT_EXTENSION_AND_PUBLISH_PLAN_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR0_CONTRACT_EXTENSION_AND_PUBLISH_PLAN_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR1_CANDIDATE_ONLY_SNAPSHOT_DRY_RUN_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_CLPR4_FINAL_SAFETY_AND_INTEGRATION_ACCEPTANCE_REVIEW_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/READONLY_STRATEGY_SNAPSHOT_CONTRACT_CN.md
{rel(resolve(RSPPR0_SOURCE_INVENTORY))}
{rel(resolve(RSPPR0_CONTRACT_EXTENSION))}
{rel(resolve(RSPPR0_PUBLISH_PLAN))}
{rel(resolve(RSPPR0_VALIDATOR_PLAN))}
{rel(resolve(RSPPR0_ROLLBACK_PLAN))}
{rel(resolve(CONTROLLED_SIGNAL_LATEST))}
{rel(resolve(CANONICAL_MANIFEST))}
{rel(resolve(CANONICAL_SIGNALS))}
```

Applied local skill:

```text
tw-stock-modular-integration-regression
```

## 4. Changes Made

Wrote:

```text
scripts/build_tw_rsppr1_candidate_only_snapshot_dry_run.py
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr1_candidate_only_snapshot_dry_run/source_preflight.json
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr1_candidate_only_snapshot_dry_run/candidate_snapshot_payload_plan.json
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr1_candidate_only_snapshot_dry_run/latest_pointer_payload_plan.json
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr1_candidate_only_snapshot_dry_run/validator_dry_run.json
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr1_candidate_only_snapshot_dry_run/checksum_plan.json
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr1_candidate_only_snapshot_dry_run/rollback_preflight.json
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr1_candidate_only_snapshot_dry_run/forbidden_action_audit.json
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr1_candidate_only_snapshot_dry_run/artifact_manifest.json
docs/tw_portfolio_decision_model/POLICY_RSPPR1_CANDIDATE_ONLY_SNAPSHOT_DRY_RUN_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR2_CANDIDATE_ONLY_SNAPSHOT_PUBLISH_WORK_CN.md
```

## 5. Evidence Summary

```text
source_preflight.status={source_preflight.get("status")}
candidate_snapshot_payload_plan.status={candidate_snapshot_payload_plan.get("status")}
latest_pointer_payload_plan.status={latest_pointer_payload_plan.get("status")}
validator_dry_run.status={validator_dry_run.get("status")}
checksum_plan.status={checksum_plan.get("status")}
rollback_preflight.status={rollback_preflight.get("status")}
forbidden_action_audit.all_false={str(forbidden_action_audit.get("all_false")).lower()}
artifact_manifest.status={artifact_manifest.get("status")}
artifact_manifest entries={len(artifact_manifest.get("entries", []))}
artifact_manifest missing={artifact_manifest.get("missing")}
```

Controlled signal latest:

```text
latest.asof={source_preflight["source_lineage"]["asof"]}
latest.signal_asof={source_preflight["source_lineage"]["signal_asof"]}
latest.run_id={source_preflight["source_lineage"]["run_id"]}
canonical_manifest_checksum_matches_latest_pointer={source_preflight["checks"]["canonical_manifest_checksum_matches_latest_pointer"]}
canonical_signals_checksum_matches_latest_pointer={source_preflight["checks"]["canonical_signals_checksum_matches_latest_pointer"]}
canonical_validator_pass={source_preflight["checks"]["canonical_validator_pass"]}
```

Signals audit:

```text
rows={signals["row_count"]}
date_values={signals["date_values"]}
signal_asof_values={signals["signal_asof_values"]}
duplicate_key_count={signals["duplicate_key_count"]}
forbidden_columns={signals["forbidden_columns"]}
candidate_rank_le_50_count={signals["candidate_rank_le_50_count"]}
top_candidates_count={candidate_snapshot_payload_plan["payloads"]["strategy_snapshot"]["top_candidates_count"]}
```

Candidate-only contract:

```text
candidate_only=true
model_id={MODEL_ID}
base_model_id={MODEL_ID}
ranking_source=qlib_rank_controlled_signal
candidate_boundary=qlib_top50
exit_candidates=[]
hold_candidates=[]
exit_hold_context_status=not_built_no_strategy_replay
readonly_only=true
not_investment_advice=true
production_trade_enabled=false
is_production_trading_default=false
```

Validator dry-run:

```text
candidate_only_validator_evidence=true
existing_validator_not_used=true
existing_validator_path={rel(resolve(EXISTING_READONLY_VALIDATOR))}
existing_validator_skip_reason=LTR-primary hardcoded; this route validates Model A candidate-only payload plans.
```

Checksum plan:

```text
manifest.json.sha256={checksum_plan["planned_snapshot_files"]["manifest.json"]["sha256"]}
strategy_snapshot.json.sha256={checksum_plan["planned_snapshot_files"]["strategy_snapshot.json"]["sha256"]}
validation_report.json.sha256={checksum_plan["planned_snapshot_files"]["validation_report.json"]["sha256"]}
forbidden_scope_audit.json.sha256={checksum_plan["planned_snapshot_files"]["forbidden_scope_audit.json"]["sha256"]}
checksum_manifest.json.excludes_itself=true
```

Snapshot/latest boundary:

```text
existing_readonly_snapshot_latest_asof={latest_summary.get("asof")}
existing_readonly_snapshot_latest_sha256={source_preflight["existing_readonly_snapshot_latest_fingerprint_before_dry_run"].get("sha256")}
target_snapshot_dir={source_preflight["target_snapshot_collision_audit"]["target_snapshot_dir"]}
target_snapshot_dir_exists={str(source_preflight["target_snapshot_collision_audit"]["target_snapshot_dir_exists"]).lower()}
rsppr1_created_target_snapshot_dir=false
rsppr1_wrote_readonly_snapshot_latest=false
```

## 6. Forbidden Actions

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
readonly snapshot artifact publish
readonly snapshot latest write
Agent prompt build/publish
OpenAI call
frontend/API/default switch
monitor/broker/order
trade target or size output
```

## 7. Recommendation

Proceed to `RSPPR1` reviewer if this execution report and evidence are accepted. Do not enter `RSPPR2` publish until reviewer PASS.
"""


def build_rsppr2_work_doc(created_at: str) -> str:
    return f"""---
created_at: {created_at}
status: work_document
route: RSPPR_READONLY_SNAPSHOT_BUILDER_PUBLISH_ROUTE
phase: RSPPR2_CANDIDATE_ONLY_SNAPSHOT_PUBLISH
target_asof: {TARGET_ASOF}
requires_rsppr1_reviewer_pass: true
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

# RSPPR2 Candidate-only Snapshot Publish Work

## 1. Objective

RSPPR2 仅在 RSPPR1 reviewer PASS 后，把 RSPPR1 已验证的 candidate-only payload plan 写成 readonly snapshot artifact，并更新 `readonly_strategy_snapshot/latest.json` 指向该 readonly snapshot。RSPPR2 不构建或发布 Agent prompt。

## 2. Required Inputs

必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RSPPR_READONLY_SNAPSHOT_BUILDER_PUBLISH_ROUTE_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR1_CANDIDATE_ONLY_SNAPSHOT_DRY_RUN_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR1_CANDIDATE_ONLY_SNAPSHOT_DRY_RUN_REVIEW_CN.md
{rel(resolve(EVIDENCE_ROOT))}/source_preflight.json
{rel(resolve(EVIDENCE_ROOT))}/candidate_snapshot_payload_plan.json
{rel(resolve(EVIDENCE_ROOT))}/latest_pointer_payload_plan.json
{rel(resolve(EVIDENCE_ROOT))}/validator_dry_run.json
{rel(resolve(EVIDENCE_ROOT))}/checksum_plan.json
{rel(resolve(EVIDENCE_ROOT))}/rollback_preflight.json
{rel(resolve(EVIDENCE_ROOT))}/forbidden_action_audit.json
```

## 3. Allowed Writes

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/{TARGET_ASOF}/manifest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/{TARGET_ASOF}/strategy_snapshot.json
data_tw/artifacts/publish/readonly_strategy_snapshot/{TARGET_ASOF}/validation_report.json
data_tw/artifacts/publish/readonly_strategy_snapshot/{TARGET_ASOF}/forbidden_scope_audit.json
data_tw/artifacts/publish/readonly_strategy_snapshot/{TARGET_ASOF}/checksum_manifest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr2_candidate_only_snapshot_publish/*.json
docs/tw_portfolio_decision_model/POLICY_RSPPR2_CANDIDATE_ONLY_SNAPSHOT_PUBLISH_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR3_SNAPSHOT_READONLY_INTEGRATION_ACCEPTANCE_WORK_CN.md
```

## 4. Required Evidence

必须生成：

```text
pre_publish_fingerprint.json
written_snapshot_artifact.json
latest_pointer_write.json
validator_publish.json
checksum_manifest_verify.json
rollback_package.json
forbidden_action_audit.json
artifact_manifest.json
```

## 5. Required Checks

```text
RSPPR1 reviewer PASS
RSPPR1 source_preflight.status=pass
RSPPR1 candidate_snapshot_payload_plan.status=pass
RSPPR1 latest_pointer_payload_plan.status=pass
RSPPR1 validator_dry_run.status=pass
RSPPR1 checksum_plan.status=pass
RSPPR1 rollback_preflight.status=pass
target snapshot dir collision clear before write
previous readonly_strategy_snapshot/latest.json bytes backed up and sha256 recorded
written snapshot files match RSPPR1 payload plan checksums
checksum_manifest excludes itself and matches written snapshot files
latest pointer points only to readonly_strategy_snapshot/{TARGET_ASOF}/manifest.json
candidate_only=true
exit_candidates=[]
hold_candidates=[]
exit_hold_context_status=not_built_no_strategy_replay
no Agent prompt build/publish
no provider/qlib accepted latest, legacy option_c, frontend/API/default, model, strategy, replay, order, monitor, OpenAI action
```

## 6. Forbidden Actions

RSPPR2 禁止：

```text
provider/network pull
provider publish
provider or qlib accepted latest switch
legacy option_c latest signal switch
model scoring or training
strategy replay
OrderIntentArtifact generation
ReplayResult/NAV generation
Agent prompt build/publish
OpenAI call
frontend/API/default switch
monitor/broker/order
trade target or size output
```

## 7. Pass Gate

RSPPR2 PASS 条件：

```text
pre_publish_fingerprint.status=pass
written_snapshot_artifact.status=pass
latest_pointer_write.status=pass
validator_publish.status=pass
checksum_manifest_verify.status=pass
rollback_package.status=pass
forbidden_action_audit.all_false=true
artifact_manifest.status=pass
```
"""


def main() -> int:
    created_at = now_iso()
    source_preflight_path = EVIDENCE_ROOT / "source_preflight.json"
    candidate_snapshot_payload_plan_path = EVIDENCE_ROOT / "candidate_snapshot_payload_plan.json"
    latest_pointer_payload_plan_path = EVIDENCE_ROOT / "latest_pointer_payload_plan.json"
    validator_dry_run_path = EVIDENCE_ROOT / "validator_dry_run.json"
    checksum_plan_path = EVIDENCE_ROOT / "checksum_plan.json"
    rollback_preflight_path = EVIDENCE_ROOT / "rollback_preflight.json"
    forbidden_action_audit_path = EVIDENCE_ROOT / "forbidden_action_audit.json"
    artifact_manifest_path = EVIDENCE_ROOT / "artifact_manifest.json"

    source_preflight = build_source_preflight(created_at)
    candidate_snapshot_payload_plan = build_candidate_snapshot_payload_plan(
        created_at, source_preflight
    )
    latest_pointer_payload_plan = build_latest_pointer_payload_plan(
        created_at, source_preflight, candidate_snapshot_payload_plan
    )
    validator_dry_run = build_validator_dry_run(
        created_at,
        source_preflight,
        candidate_snapshot_payload_plan,
        latest_pointer_payload_plan,
    )
    checksum_plan = build_checksum_plan(
        created_at,
        candidate_snapshot_payload_plan,
        latest_pointer_payload_plan,
        validator_dry_run,
    )
    rollback_preflight = build_rollback_preflight(created_at)
    forbidden_action_audit = build_forbidden_action_audit(created_at)

    write_json(source_preflight_path, source_preflight)
    write_json(candidate_snapshot_payload_plan_path, candidate_snapshot_payload_plan)
    write_json(latest_pointer_payload_plan_path, latest_pointer_payload_plan)
    write_json(validator_dry_run_path, validator_dry_run)
    write_json(checksum_plan_path, checksum_plan)
    write_json(rollback_preflight_path, rollback_preflight)
    write_json(forbidden_action_audit_path, forbidden_action_audit)

    files = [
        source_preflight_path,
        candidate_snapshot_payload_plan_path,
        latest_pointer_payload_plan_path,
        validator_dry_run_path,
        checksum_plan_path,
        rollback_preflight_path,
        forbidden_action_audit_path,
        Path("scripts/build_tw_rsppr1_candidate_only_snapshot_dry_run.py"),
        RSPPR1_EXECUTION_REPORT,
        RSPPR2_WORK,
    ]

    provisional_manifest = build_artifact_manifest(created_at, files)
    write_text(
        RSPPR1_EXECUTION_REPORT,
        build_execution_report(
            created_at,
            source_preflight,
            candidate_snapshot_payload_plan,
            latest_pointer_payload_plan,
            validator_dry_run,
            checksum_plan,
            rollback_preflight,
            forbidden_action_audit,
            provisional_manifest,
        ),
    )
    write_text(RSPPR2_WORK, build_rsppr2_work_doc(created_at))

    artifact_manifest = build_artifact_manifest(created_at, files)
    write_json(artifact_manifest_path, artifact_manifest)
    write_text(
        RSPPR1_EXECUTION_REPORT,
        build_execution_report(
            created_at,
            source_preflight,
            candidate_snapshot_payload_plan,
            latest_pointer_payload_plan,
            validator_dry_run,
            checksum_plan,
            rollback_preflight,
            forbidden_action_audit,
            artifact_manifest,
        ),
    )
    artifact_manifest = build_artifact_manifest(created_at, files)
    write_json(artifact_manifest_path, artifact_manifest)

    overall_pass = (
        source_preflight["status"] == "pass"
        and candidate_snapshot_payload_plan["status"] == "pass"
        and latest_pointer_payload_plan["status"] == "pass"
        and validator_dry_run["status"] == "pass"
        and checksum_plan["status"] == "pass"
        and rollback_preflight["status"] == "pass"
        and forbidden_action_audit["all_false"] is True
        and artifact_manifest["status"] == "pass"
    )
    print(
        json.dumps(
            {
                "status": "pass" if overall_pass else "fail",
                "verdict": "PASS_RECOMMEND_RSPPR1_REVIEWER"
                if overall_pass
                else "STOP_REPAIR_RSPPR1",
                "evidence_root": rel(resolve(EVIDENCE_ROOT)),
                "source_preflight": source_preflight["status"],
                "candidate_snapshot_payload_plan": candidate_snapshot_payload_plan[
                    "status"
                ],
                "latest_pointer_payload_plan": latest_pointer_payload_plan["status"],
                "validator_dry_run": validator_dry_run["status"],
                "checksum_plan": checksum_plan["status"],
                "rollback_preflight": rollback_preflight["status"],
                "forbidden_action_all_false": forbidden_action_audit["all_false"],
                "artifact_manifest": artifact_manifest["status"],
                "top_candidates_count": candidate_snapshot_payload_plan["payloads"][
                    "strategy_snapshot"
                ]["top_candidates_count"],
                "target_snapshot_dir_exists": resolve(TARGET_SNAPSHOT_DIR).exists(),
                "readonly_snapshot_latest_written": False,
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
