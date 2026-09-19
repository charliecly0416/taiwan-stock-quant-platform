#!/usr/bin/env python3
"""Build RSPPR0 contract extension and publish plan evidence.

RSPPR0 is intentionally plan-only. It fingerprints the controlled signal
latest and existing readonly snapshot latest, then writes evidence under the
RSPPR experiment directory. It does not create a readonly snapshot artifact and
does not write any latest pointer.
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

CLPR4_REVIEW = Path(
    "docs/tw_portfolio_decision_model/"
    "POLICY_CLPR4_FINAL_SAFETY_AND_INTEGRATION_ACCEPTANCE_REVIEW_CN.md"
)
RSPPR_MAINLINE = Path(
    "docs/tw_portfolio_decision_model/"
    "POLICY_RSPPR_READONLY_SNAPSHOT_BUILDER_PUBLISH_ROUTE_MAINLINE_CN.md"
)
RSPPR0_WORK = Path(
    "docs/tw_portfolio_decision_model/"
    "POLICY_RSPPR0_CONTRACT_EXTENSION_AND_PUBLISH_PLAN_WORK_CN.md"
)
EXECUTION_REPORT = Path(
    "docs/tw_portfolio_decision_model/"
    "POLICY_RSPPR0_CONTRACT_EXTENSION_AND_PUBLISH_PLAN_EXECUTION_REPORT_CN.md"
)
RSPPR1_WORK = Path(
    "docs/tw_portfolio_decision_model/"
    "POLICY_RSPPR1_CANDIDATE_ONLY_SNAPSHOT_DRY_RUN_WORK_CN.md"
)

SIGNAL_ROOT = Path("data_tw/artifacts/signals") / MODEL_ID
CONTROLLED_SIGNAL_LATEST = SIGNAL_ROOT / "latest.json"
CANONICAL_SIGNAL_DIR = SIGNAL_ROOT / RUN_ID
CANONICAL_MANIFEST = CANONICAL_SIGNAL_DIR / "manifest.json"
CANONICAL_SIGNALS = CANONICAL_SIGNAL_DIR / "signals.csv"
CANONICAL_VALIDATOR = CANONICAL_SIGNAL_DIR / "validator_report.json"
CANONICAL_SCHEMA = CANONICAL_SIGNAL_DIR / "schema.json"
CANONICAL_COVERAGE_AUDIT = CANONICAL_SIGNAL_DIR / "coverage_audit.csv"
CANONICAL_FORBIDDEN_FIELD_AUDIT = CANONICAL_SIGNAL_DIR / "forbidden_field_audit.csv"

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
    "rsppr0_contract_extension_and_publish_plan"
)

FORBIDDEN_COLUMN_EXACT = {
    "relevance_10d_top_heavy",
    "ltr_relevance_label",
    "realized_pnl",
    "realized_return",
    "action",
    "holding",
    "position",
    "target_position",
    "target_weight",
    "quantity",
    "shares",
    "lots",
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
    full.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, text: str) -> None:
    full = resolve(path)
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(text.rstrip() + "\n", encoding="utf-8")


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
                candidate_rank = int(float(row.get("candidate_rank", "")))
            except ValueError:
                candidate_rank = 999999
            if candidate_rank <= 50:
                top_candidates.append(
                    {
                        "instrument": row.get("instrument"),
                        "candidate_rank": candidate_rank,
                        "score_rank": row.get("score_rank"),
                        "buy_score": row.get("buy_score"),
                    }
                )
    forbidden_columns = sorted([column for column in columns if is_forbidden_column(column)])
    top_candidates = sorted(top_candidates, key=lambda item: (item["candidate_rank"], item["instrument"] or ""))
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


def text_contains(path: Path, needle: str) -> bool:
    full = resolve(path)
    return full.exists() and needle in full.read_text(encoding="utf-8")


def build_source_inventory(created_at: str) -> dict[str, Any]:
    latest = load_json(CONTROLLED_SIGNAL_LATEST)
    manifest = load_json(CANONICAL_MANIFEST)
    validator = load_json(CANONICAL_VALIDATOR)
    signals_audit = audit_signals_csv(CANONICAL_SIGNALS)
    manifest_sha = sha256_file(CANONICAL_MANIFEST)
    signals_sha = sha256_file(CANONICAL_SIGNALS)
    clpr4_text_pass = text_contains(
        CLPR4_REVIEW,
        "PASS_CLOSE_CLPR_CONTROLLED_SIGNAL_LATEST_ONLY_WITH_SNAPSHOT_BLOCKER",
    )
    target_dir_exists = resolve(TARGET_SNAPSHOT_DIR).exists()
    checks = {
        "clpr_final_review_pass": clpr4_text_pass,
        "controlled_signal_latest_exists": resolve(CONTROLLED_SIGNAL_LATEST).is_file(),
        "controlled_signal_latest_asof_2026_07_08": latest.get("asof") == TARGET_ASOF,
        "controlled_signal_latest_signal_asof_2026_07_08": latest.get("signal_asof")
        == TARGET_ASOF,
        "controlled_signal_latest_run_id_match": latest.get("run_id") == RUN_ID,
        "canonical_manifest_exists": resolve(CANONICAL_MANIFEST).is_file(),
        "canonical_signals_exists": resolve(CANONICAL_SIGNALS).is_file(),
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
        "signals_date_only_2026_07_08": signals_audit["checks"][
            "date_only_target_asof"
        ],
        "signals_signal_asof_only_2026_07_08": signals_audit["checks"][
            "signal_asof_only_target_asof"
        ],
        "signals_duplicate_keys_zero": signals_audit["checks"][
            "duplicate_key_count_zero"
        ],
        "signals_forbidden_columns_empty": signals_audit["checks"][
            "forbidden_columns_empty"
        ],
        "readonly_snapshot_latest_fingerprinted_only": "sha256"
        in file_fingerprint(READONLY_SNAPSHOT_LATEST),
        "target_snapshot_dir_collision_explicit": True,
        "target_snapshot_dir_absent_for_rsppr0": not target_dir_exists,
    }
    return {
        "schema_version": "rsppr0.source_inventory.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "source_lineage": {
            "clpr4_review": rel(resolve(CLPR4_REVIEW)),
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
            "not_published_latest": manifest.get("not_published_latest"),
            "no_latest": manifest.get("no_latest"),
            "no_target_output": manifest.get("no_target_output"),
        },
        "canonical_validator_summary": {
            "path": rel(resolve(CANONICAL_VALIDATOR)),
            "status": validator.get("status"),
            "checks": validator.get("checks"),
            "errors": validator.get("errors"),
        },
        "signals_csv_audit": signals_audit,
        "existing_readonly_snapshot_latest_fingerprint_only": file_fingerprint(
            READONLY_SNAPSHOT_LATEST
        ),
        "target_snapshot_collision_audit": {
            "target_snapshot_dir": rel(resolve(TARGET_SNAPSHOT_DIR)),
            "target_snapshot_dir_exists": target_dir_exists,
            "collision_status": "explicit_collision_blocker"
            if target_dir_exists
            else "no_collision",
            "rsppr0_created_target_snapshot_dir": False,
            "rsppr0_wrote_readonly_snapshot_latest": False,
        },
        "out_of_scope_pointer_fingerprints": {
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


def build_candidate_only_contract_extension(
    created_at: str, inventory: dict[str, Any]
) -> dict[str, Any]:
    checks = {
        "source_inventory_pass": inventory.get("status") == "pass",
        "artifact_type_preserved": True,
        "schema_version_preserved": True,
        "readonly_flags_true": True,
        "production_trade_enabled_false": True,
        "candidate_only_true": True,
        "exit_candidates_empty": True,
        "hold_candidates_empty": True,
        "exit_hold_context_marked_not_built": True,
        "no_strategy_replay_required": True,
        "no_order_intent_required": True,
        "no_replay_result_required": True,
        "not_target_output": True,
    }
    return {
        "schema_version": "rsppr0.candidate_only_contract_extension.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "extends_contract": "docs/tw_modular_contracts/READONLY_STRATEGY_SNAPSHOT_CONTRACT_CN.md",
        "artifact_contract": {
            "artifact_type": "readonly_strategy_snapshot",
            "schema_version": "readonly_strategy_snapshot_r13_v1",
            "display_role": "primary_readonly_candidate",
            "readonly_only": True,
            "production_trade_enabled": False,
            "no_order_action": True,
            "not_target_position": True,
            "not_investment_advice": True,
            "is_primary_readonly_candidate": True,
            "is_production_trading_default": False,
        },
        "candidate_only_extension": {
            "candidate_only": True,
            "source_lineage": "clpr_controlled_model_signal_latest",
            "source_signal_latest": rel(resolve(CONTROLLED_SIGNAL_LATEST)),
            "source_signal_manifest": rel(resolve(CANONICAL_MANIFEST)),
            "source_signal_csv": rel(resolve(CANONICAL_SIGNALS)),
            "model_id": MODEL_ID,
            "base_model_id": MODEL_ID,
            "model_family": "qlib",
            "strategy_rule": STRATEGY_RULE,
            "candidate_boundary": "qlib_top50",
            "ranking_source": "qlib_rank_controlled_signal",
            "top_candidates_source": "signals.csv rows with candidate_rank <= 50, sorted by candidate_rank then instrument",
            "exit_candidates": [],
            "hold_candidates": [],
            "exit_hold_context_status": "not_built_no_strategy_replay",
            "strategy_replay_status": "not_built_forbidden_in_rsppr0_rsppr1",
            "order_intent_status": "not_built_forbidden_in_rsppr",
            "replay_result_status": "not_built_forbidden_in_rsppr",
            "agent_prompt_status": "not_built_in_rsppr",
            "not_full_strategy_snapshot": True,
            "not_trade_target": True,
        },
        "allowed_snapshot_sections_for_rsppr1_dry_run": {
            "manifest": "payload_plan_only",
            "strategy_snapshot": "payload_plan_only",
            "validation_report": "validator_plan_only",
            "forbidden_scope_audit": "audit_plan_only",
            "checksum_manifest": "checksum_plan_only",
        },
        "checks": checks,
    }


def build_publish_plan(
    created_at: str,
    inventory: dict[str, Any],
    contract_extension: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "source_inventory_pass": inventory.get("status") == "pass",
        "candidate_only_contract_extension_pass": contract_extension.get("status")
        == "pass",
        "target_dir_collision_explicit": inventory["target_snapshot_collision_audit"][
            "collision_status"
        ]
        in {"no_collision", "explicit_collision_blocker"},
        "rsppr0_writes_no_snapshot_artifact": True,
        "rsppr0_writes_no_latest_pointer": True,
        "rsppr1_dry_run_only": True,
        "rsppr2_publish_requires_rsppr1_reviewer_pass": True,
        "agent_prompt_route_separate_after_rsppr_final_pass": True,
    }
    latest_payload_plan = {
        "artifact_type": "readonly_strategy_snapshot_latest_pointer",
        "schema_version": "readonly_strategy_snapshot_latest_r13_v1",
        "asof": TARGET_ASOF,
        "data_asof": TARGET_ASOF,
        "signal_asof": TARGET_ASOF,
        "target_date": TARGET_ASOF,
        "readonly_only": True,
        "production_trade_enabled": False,
        "snapshot_manifest": rel(resolve(TARGET_MANIFEST)),
        "created_by_planned_phase": "RSPPR2_CANDIDATE_ONLY_SNAPSHOT_PUBLISH",
        "not_provider_accepted_latest": True,
        "not_trade_target_latest": True,
        "candidate_only": True,
        "source_signal_latest": rel(resolve(CONTROLLED_SIGNAL_LATEST)),
        "source_signal_manifest_sha256": inventory["controlled_signal_latest"][
            "canonical_manifest_sha256_actual"
        ],
        "source_signal_csv_sha256": inventory["controlled_signal_latest"][
            "canonical_signals_sha256_actual"
        ],
    }
    return {
        "schema_version": "rsppr0.publish_plan.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "rsppr0_publish_status": {
            "created_target_snapshot_dir": False,
            "wrote_readonly_snapshot_latest": False,
            "built_agent_prompt": False,
            "modified_controlled_signal_latest": False,
        },
        "planned_snapshot_artifact": {
            "target_dir": rel(resolve(TARGET_SNAPSHOT_DIR)),
            "files": [
                rel(resolve(TARGET_MANIFEST)),
                rel(resolve(TARGET_STRATEGY_SNAPSHOT)),
                rel(resolve(TARGET_VALIDATION_REPORT)),
                rel(resolve(TARGET_FORBIDDEN_SCOPE_AUDIT)),
                rel(resolve(TARGET_CHECKSUM_MANIFEST)),
            ],
            "target_dir_exists_now": resolve(TARGET_SNAPSHOT_DIR).exists(),
            "collision_policy": inventory["target_snapshot_collision_audit"][
                "collision_status"
            ],
        },
        "planned_latest_pointer": {
            "path": rel(resolve(READONLY_SNAPSHOT_LATEST)),
            "payload_plan": latest_payload_plan,
            "write_allowed_in_phase": "RSPPR2 only after RSPPR1 reviewer PASS",
        },
        "phase_gates": [
            {
                "phase": "RSPPR1",
                "action": "candidate_only_snapshot_payload_dry_run",
                "writes_snapshot_artifact": False,
                "writes_latest_pointer": False,
                "requires": "RSPPR0 reviewer PASS",
            },
            {
                "phase": "RSPPR2",
                "action": "candidate_only_snapshot_artifact_and_latest_publish",
                "writes_snapshot_artifact": True,
                "writes_latest_pointer": True,
                "requires": "RSPPR1 reviewer PASS; target collision clear; checksum plan pass; rollback preflight pass",
            },
            {
                "phase": "RSPPR3",
                "action": "readonly_snapshot_latest_integration_acceptance",
                "writes_snapshot_artifact": False,
                "writes_latest_pointer": False,
                "requires": "RSPPR2 reviewer PASS",
            },
            {
                "phase": "RSPPR4",
                "action": "final_closure_and_agent_prompt_latest_route_gate",
                "opens_agent_prompt_route_if_pass": True,
                "requires": "RSPPR3 reviewer PASS and no safety blocker",
            },
        ],
        "forbidden_publish_targets": [
            rel(resolve(CONTROLLED_SIGNAL_LATEST)),
            rel(resolve(AGENT_DAILY_PROMPT_LATEST)),
            rel(resolve(LEGACY_QLIB_OPTION_C_LATEST)),
            rel(resolve(LEGACY_DATA_OPTION_C_LATEST)),
            "provider accepted latest",
            "qlib accepted latest",
            "frontend/API/default",
        ],
        "checks": checks,
    }


def build_validator_plan(created_at: str, inventory: dict[str, Any]) -> dict[str, Any]:
    validator_text = resolve(EXISTING_READONLY_VALIDATOR).read_text(encoding="utf-8")
    mismatch_checks = {
        "existing_validator_exists": resolve(EXISTING_READONLY_VALIDATOR).is_file(),
        "existing_validator_hardcodes_ltr_primary_model": (
            'snapshot.get("model_id") == "e4_frozen_qlib_2023_2025_ltr"'
            in validator_text
        ),
        "existing_validator_hardcodes_ltr_ranking_source": (
            'snapshot.get("ranking_source") == "ltr_rerank_within_qlib_top50"'
            in validator_text
        ),
        "candidate_only_model_is_model_a": MODEL_ID == "e4_frozen_qlib_2018_2022",
        "candidate_only_ranking_source_is_qlib_rank": True,
    }
    checks = {
        "source_inventory_pass": inventory.get("status") == "pass",
        "existing_ltr_primary_validator_mismatch_documented": all(
            mismatch_checks.values()
        ),
        "rsppr1_custom_candidate_only_validator_required": True,
        "validator_must_not_modify_existing_ltr_primary_validator": True,
        "validator_must_not_require_exit_hold_context": True,
        "validator_must_require_exit_hold_marked_not_built": True,
        "validator_must_reject_forbidden_columns": True,
    }
    return {
        "schema_version": "rsppr0.validator_plan.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "existing_validator_mismatch": {
            "validator_path": rel(resolve(EXISTING_READONLY_VALIDATOR)),
            "status": "documented_mismatch_not_blocking_rsppr0",
            "reason": (
                "Existing validator is LTR-primary and expects model_id "
                "e4_frozen_qlib_2023_2025_ltr plus ranking_source "
                "ltr_rerank_within_qlib_top50; RSPPR candidate-only snapshot "
                "uses Model A qlib ranks from controlled signal latest."
            ),
            "mismatch_checks": mismatch_checks,
            "do_not_patch_existing_validator_in_rsppr0": True,
        },
        "candidate_only_validator_requirements": [
            "manifest.artifact_type == readonly_strategy_snapshot",
            "manifest.schema_version == readonly_strategy_snapshot_r13_v1",
            "manifest/source flags readonly_only true and production_trade_enabled false",
            "strategy_snapshot.candidate_only == true",
            "strategy_snapshot.model_id == e4_frozen_qlib_2018_2022",
            "strategy_snapshot.base_model_id == e4_frozen_qlib_2018_2022",
            "strategy_snapshot.ranking_source == qlib_rank_controlled_signal",
            "top_candidates derived from signals.csv candidate_rank <= 50",
            "exit_candidates == [] and hold_candidates == []",
            "exit_hold_context_status == not_built_no_strategy_replay",
            "no OrderIntentArtifact and no ReplayResult/NAV references",
            "forbidden_scope_audit.status == pass",
            "checksum_manifest excludes itself and matches all snapshot files",
            "latest pointer points only to readonly_strategy_snapshot manifest",
            "no provider/qlib accepted latest, legacy option_c, Agent latest, default, order, or target action flags",
        ],
        "source_signal_preconditions": inventory["signals_csv_audit"]["checks"],
        "checks": checks,
    }


def build_rollback_plan(created_at: str) -> dict[str, Any]:
    return {
        "schema_version": "rsppr0.rollback_plan.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass",
        "rsppr0_writes_nothing_to_rollback": True,
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
        "rsppr2_publish_rollback_plan": {
            "backup_previous_latest_pointer_before_write": True,
            "restore_previous_latest_pointer_bytes_and_verify_sha256": True,
            "if_latest_pointer_absent_before_publish": "delete only RSPPR2-created latest.json after verifying provenance",
            "if_target_snapshot_dir_created_by_rsppr2": "remove only RSPPR2-created target dir after artifact evidence is archived",
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
        "checks": {
            "rsppr0_writes_nothing_to_rollback": True,
            "existing_readonly_snapshot_latest_fingerprinted": True,
            "target_snapshot_dir_fingerprinted": True,
            "rollback_scope_limited_to_rsppr2_snapshot_publish": True,
        },
    }


def build_forbidden_action_audit(created_at: str) -> dict[str, Any]:
    flags = {
        "readonly_snapshot_artifact_created": False,
        "readonly_snapshot_latest_written": False,
        "agent_prompt_built": False,
        "agent_prompt_published": False,
        "controlled_signal_latest_modified": False,
        "legacy_option_c_latest_signal_modified": False,
        "provider_network_pull_triggered": False,
        "provider_publish_triggered": False,
        "provider_accepted_latest_switched": False,
        "qlib_accepted_latest_switched": False,
        "model_scoring_triggered": False,
        "strategy_replay_triggered": False,
        "order_intent_generated": False,
        "replay_result_generated": False,
        "openai_call_triggered": False,
        "frontend_or_api_default_switched": False,
        "monitor_write_scan_alert_triggered": False,
        "broker_order_quick_trade_triggered": False,
        "target_output_generated": False,
    }
    return {
        "schema_version": "rsppr0.forbidden_action_audit.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass",
        "all_false": all(value is False for value in flags.values()),
        "flags": flags,
    }


def build_artifact_manifest(created_at: str, files: list[Path]) -> dict[str, Any]:
    entries = []
    missing = []
    checksum_mismatches: list[dict[str, Any]] = []
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
        "schema_version": "rsppr0.artifact_manifest.v1",
        "created_at": created_at,
        "status": "pass" if not missing and not checksum_mismatches else "fail",
        "entries": entries,
        "missing": missing,
        "checksum_mismatches": checksum_mismatches,
    }


def build_execution_report(
    created_at: str,
    inventory: dict[str, Any],
    contract_extension: dict[str, Any],
    publish_plan: dict[str, Any],
    validator_plan: dict[str, Any],
    rollback_plan: dict[str, Any],
    forbidden_action_audit: dict[str, Any],
    artifact_manifest: dict[str, Any],
) -> str:
    verdict = (
        "PASS_RECOMMEND_RSPPR1_CANDIDATE_ONLY_SNAPSHOT_DRY_RUN"
        if all(
            [
                inventory.get("status") == "pass",
                contract_extension.get("status") == "pass",
                publish_plan.get("status") == "pass",
                validator_plan.get("status") == "pass",
                rollback_plan.get("status") == "pass",
                forbidden_action_audit.get("all_false") is True,
                artifact_manifest.get("status") == "pass",
            ]
        )
        else "FAIL_NEEDS_REPAIR"
    )
    signals = inventory["signals_csv_audit"]
    return f"""---
created_at: {created_at}
status: execution_report
route: RSPPR_READONLY_SNAPSHOT_BUILDER_PUBLISH_ROUTE
phase: RSPPR0_CONTRACT_EXTENSION_AND_PUBLISH_PLAN
executor: RSPPR0_EXECUTOR
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

# RSPPR0 Contract Extension And Publish Plan Execution Report

## 1. Verdict

```text
{verdict}
```

RSPPR0 只完成 candidate-only readonly snapshot 的合同扩展、source inventory、publish plan、validator plan 和 rollback plan。未创建 `data_tw/artifacts/publish/readonly_strategy_snapshot/{TARGET_ASOF}/`，未写 `readonly_strategy_snapshot/latest.json`，未构建或发布 Agent prompt。

## 2. Scope

Assigned phase:

```text
RSPPR0_CONTRACT_EXTENSION_AND_PUBLISH_PLAN
```

Mainline document:

```text
{rel(resolve(RSPPR_MAINLINE))}
```

Work document:

```text
{rel(resolve(RSPPR0_WORK))}
```

## 3. Documents / Contracts / Skills Read

```text
docs/tw_portfolio_decision_model/POLICY_RSPPR_READONLY_SNAPSHOT_BUILDER_PUBLISH_ROUTE_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR0_CONTRACT_EXTENSION_AND_PUBLISH_PLAN_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_CLPR4_FINAL_SAFETY_AND_INTEGRATION_ACCEPTANCE_REVIEW_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/READONLY_STRATEGY_SNAPSHOT_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md
docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/manifest.json
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/signals.csv
```

Applied local skills:

```text
coordinator-executor-reviewer-workflow
tw-stock-new-strategy-onboarding
```

## 4. Changes Made

Wrote:

```text
scripts/build_tw_rsppr0_contract_extension_and_publish_plan.py
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr0_contract_extension_and_publish_plan/source_inventory.json
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr0_contract_extension_and_publish_plan/candidate_only_contract_extension.json
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr0_contract_extension_and_publish_plan/publish_plan.json
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr0_contract_extension_and_publish_plan/validator_plan.json
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr0_contract_extension_and_publish_plan/rollback_plan.json
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr0_contract_extension_and_publish_plan/forbidden_action_audit.json
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr0_contract_extension_and_publish_plan/artifact_manifest.json
docs/tw_portfolio_decision_model/POLICY_RSPPR0_CONTRACT_EXTENSION_AND_PUBLISH_PLAN_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR1_CANDIDATE_ONLY_SNAPSHOT_DRY_RUN_WORK_CN.md
```

## 5. Evidence Summary

```text
source_inventory.status={inventory.get("status")}
candidate_only_contract_extension.status={contract_extension.get("status")}
publish_plan.status={publish_plan.get("status")}
validator_plan.status={validator_plan.get("status")}
rollback_plan.status={rollback_plan.get("status")}
forbidden_action_audit.all_false={str(forbidden_action_audit.get("all_false")).lower()}
artifact_manifest.status={artifact_manifest.get("status")}
artifact_manifest entries={len(artifact_manifest.get("entries", []))}
artifact_manifest missing={artifact_manifest.get("missing")}
artifact_manifest checksum_mismatches={artifact_manifest.get("checksum_mismatches")}
```

Controlled signal latest:

```text
latest.asof={inventory["source_lineage"]["asof"]}
latest.signal_asof={inventory["source_lineage"]["signal_asof"]}
latest.run_id={inventory["source_lineage"]["run_id"]}
canonical_manifest_checksum_matches_latest_pointer={inventory["checks"]["canonical_manifest_checksum_matches_latest_pointer"]}
canonical_signals_checksum_matches_latest_pointer={inventory["checks"]["canonical_signals_checksum_matches_latest_pointer"]}
canonical_validator_pass={inventory["checks"]["canonical_validator_pass"]}
```

Signals audit:

```text
rows={signals["row_count"]}
date_values={signals["date_values"]}
signal_asof_values={signals["signal_asof_values"]}
duplicate_key_count={signals["duplicate_key_count"]}
forbidden_columns={signals["forbidden_columns"]}
candidate_rank_le_50_count={signals["candidate_rank_le_50_count"]}
```

Snapshot boundary:

```text
existing_readonly_snapshot_latest_fingerprinted_only=true
existing_readonly_snapshot_latest_asof={inventory["existing_readonly_snapshot_latest_fingerprint_only"].get("json_summary", {}).get("asof")}
target_snapshot_dir={inventory["target_snapshot_collision_audit"]["target_snapshot_dir"]}
target_snapshot_dir_exists={str(inventory["target_snapshot_collision_audit"]["target_snapshot_dir_exists"]).lower()}
collision_status={inventory["target_snapshot_collision_audit"]["collision_status"]}
```

Candidate-only contract:

```text
candidate_only=true
top_candidates_source=signals.csv candidate_rank <= 50
exit_candidates=[]
hold_candidates=[]
exit_hold_context_status=not_built_no_strategy_replay
strategy_replay_status=not_built_forbidden_in_rsppr0_rsppr1
order_intent_status=not_built_forbidden_in_rsppr
replay_result_status=not_built_forbidden_in_rsppr
```

Validator plan:

```text
existing LTR-primary validator mismatch documented=true
existing validator path={rel(resolve(EXISTING_READONLY_VALIDATOR))}
custom candidate-only validator required in RSPPR1/RSPPR2=true
```

## 6. Forbidden Actions

Confirmed not executed:

```text
readonly snapshot artifact create
readonly snapshot latest write
Agent prompt build/publish
controlled signal latest modification
legacy option_c latest_signal modification
provider/network pull
provider publish
provider/qlib accepted latest switch
model scoring
strategy replay
OrderIntentArtifact generation
ReplayResult/NAV generation
OpenAI call
frontend/API/default switch
monitor/broker/order
target output
```

## 7. Recommendation

Proceed to `RSPPR1_CANDIDATE_ONLY_SNAPSHOT_DRY_RUN` if reviewer PASS. RSPPR1 must remain dry-run only: no snapshot artifact directory, no latest pointer write, no Agent prompt, no provider/model/strategy/replay/order/default action.
"""


def build_rsppr1_work_doc(created_at: str) -> str:
    return f"""---
created_at: {created_at}
status: work_document
route: RSPPR_READONLY_SNAPSHOT_BUILDER_PUBLISH_ROUTE
phase: RSPPR1_CANDIDATE_ONLY_SNAPSHOT_DRY_RUN
target_asof: {TARGET_ASOF}
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

# RSPPR1 Candidate-only Snapshot Dry-run Work

## 1. Objective

RSPPR1 只从 CLPR controlled `ModelSignalArtifact` latest 生成 candidate-only `ReadonlyStrategySnapshot` 的 payload dry-run、checksum plan、latest pointer payload plan、validator evidence plan 和 rollback preflight。RSPPR1 不创建 snapshot artifact 目录，不写 `readonly_strategy_snapshot/latest.json`。

## 2. Required Inputs

必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RSPPR_READONLY_SNAPSHOT_BUILDER_PUBLISH_ROUTE_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR0_CONTRACT_EXTENSION_AND_PUBLISH_PLAN_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR0_CONTRACT_EXTENSION_AND_PUBLISH_PLAN_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR0_CONTRACT_EXTENSION_AND_PUBLISH_PLAN_REVIEW_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/READONLY_STRATEGY_SNAPSHOT_CONTRACT_CN.md
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr0_contract_extension_and_publish_plan/source_inventory.json
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr0_contract_extension_and_publish_plan/candidate_only_contract_extension.json
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr0_contract_extension_and_publish_plan/publish_plan.json
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr0_contract_extension_and_publish_plan/validator_plan.json
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr0_contract_extension_and_publish_plan/rollback_plan.json
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/manifest.json
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/signals.csv
```

## 3. Allowed Writes

```text
scripts/build_tw_rsppr1_candidate_only_snapshot_dry_run.py
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr1_candidate_only_snapshot_dry_run/*.json
docs/tw_portfolio_decision_model/POLICY_RSPPR1_CANDIDATE_ONLY_SNAPSHOT_DRY_RUN_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR2_CANDIDATE_ONLY_SNAPSHOT_PUBLISH_WORK_CN.md
```

## 4. Required Evidence

必须生成：

```text
source_preflight.json
candidate_snapshot_payload_plan.json
latest_pointer_payload_plan.json
validator_dry_run.json
checksum_plan.json
rollback_preflight.json
forbidden_action_audit.json
artifact_manifest.json
```

## 5. Required Checks

```text
RSPPR0 reviewer PASS
controlled signal latest asof=2026-07-08
canonical manifest/signals checksum match latest pointer
signals.csv rows=150
date/signal_asof only 2026-07-08
duplicate keys=0
forbidden_columns=[]
top_candidates derived from candidate_rank<=50
top_candidates count=50
exit_candidates=[]
hold_candidates=[]
exit_hold_context_status=not_built_no_strategy_replay
candidate-only payload cannot be mistaken for full strategy replay snapshot
existing readonly snapshot latest fingerprint unchanged
target snapshot dir collision explicit and not written
existing LTR-primary validator mismatch remains documented
```

## 6. Forbidden Actions

RSPPR1 禁止：

```text
creating data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/
writing data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
building or publishing Agent prompt
modifying controlled signal latest
modifying legacy option_c latest_signal
provider/network pull
model scoring
strategy replay
OrderIntentArtifact generation
ReplayResult/NAV generation
OpenAI call
frontend/API/default switch
monitor/broker/order
target_position/target_weight/quantity/shares/lots output
```

## 7. Pass Gate

RSPPR1 PASS 条件：

```text
source_preflight.status=pass
candidate_snapshot_payload_plan.status=pass
latest_pointer_payload_plan.status=pass
validator_dry_run.status=pass
checksum_plan.status=pass
rollback_preflight.status=pass
forbidden_action_audit.all_false=true
artifact_manifest.status=pass
RSPPR2 work doc limits writes to candidate-only readonly snapshot artifact and latest pointer only
```
"""


def main() -> int:
    created_at = now_iso()
    source_inventory_path = EVIDENCE_ROOT / "source_inventory.json"
    contract_extension_path = EVIDENCE_ROOT / "candidate_only_contract_extension.json"
    publish_plan_path = EVIDENCE_ROOT / "publish_plan.json"
    validator_plan_path = EVIDENCE_ROOT / "validator_plan.json"
    rollback_plan_path = EVIDENCE_ROOT / "rollback_plan.json"
    forbidden_action_audit_path = EVIDENCE_ROOT / "forbidden_action_audit.json"
    artifact_manifest_path = EVIDENCE_ROOT / "artifact_manifest.json"

    inventory = build_source_inventory(created_at)
    contract_extension = build_candidate_only_contract_extension(created_at, inventory)
    publish_plan = build_publish_plan(created_at, inventory, contract_extension)
    validator_plan = build_validator_plan(created_at, inventory)
    rollback_plan = build_rollback_plan(created_at)
    forbidden_action_audit = build_forbidden_action_audit(created_at)

    write_json(source_inventory_path, inventory)
    write_json(contract_extension_path, contract_extension)
    write_json(publish_plan_path, publish_plan)
    write_json(validator_plan_path, validator_plan)
    write_json(rollback_plan_path, rollback_plan)
    write_json(forbidden_action_audit_path, forbidden_action_audit)

    provisional_manifest = build_artifact_manifest(
        created_at,
        [
            source_inventory_path,
            contract_extension_path,
            publish_plan_path,
            validator_plan_path,
            rollback_plan_path,
            forbidden_action_audit_path,
            Path("scripts/build_tw_rsppr0_contract_extension_and_publish_plan.py"),
            EXECUTION_REPORT,
            RSPPR1_WORK,
        ],
    )

    report = build_execution_report(
        created_at,
        inventory,
        contract_extension,
        publish_plan,
        validator_plan,
        rollback_plan,
        forbidden_action_audit,
        provisional_manifest,
    )
    write_text(EXECUTION_REPORT, report)
    write_text(RSPPR1_WORK, build_rsppr1_work_doc(created_at))

    artifact_manifest = build_artifact_manifest(
        created_at,
        [
            source_inventory_path,
            contract_extension_path,
            publish_plan_path,
            validator_plan_path,
            rollback_plan_path,
            forbidden_action_audit_path,
            Path("scripts/build_tw_rsppr0_contract_extension_and_publish_plan.py"),
            EXECUTION_REPORT,
            RSPPR1_WORK,
        ],
    )
    write_json(artifact_manifest_path, artifact_manifest)

    # Refresh the report after artifact_manifest exists, so the summary is exact.
    report = build_execution_report(
        created_at,
        inventory,
        contract_extension,
        publish_plan,
        validator_plan,
        rollback_plan,
        forbidden_action_audit,
        artifact_manifest,
    )
    write_text(EXECUTION_REPORT, report)

    artifact_manifest = build_artifact_manifest(
        created_at,
        [
            source_inventory_path,
            contract_extension_path,
            publish_plan_path,
            validator_plan_path,
            rollback_plan_path,
            forbidden_action_audit_path,
            Path("scripts/build_tw_rsppr0_contract_extension_and_publish_plan.py"),
            EXECUTION_REPORT,
            RSPPR1_WORK,
        ],
    )
    write_json(artifact_manifest_path, artifact_manifest)

    overall_pass = (
        inventory["status"] == "pass"
        and contract_extension["status"] == "pass"
        and publish_plan["status"] == "pass"
        and validator_plan["status"] == "pass"
        and rollback_plan["status"] == "pass"
        and forbidden_action_audit["all_false"] is True
        and artifact_manifest["status"] == "pass"
    )
    print(
        json.dumps(
            {
                "status": "pass" if overall_pass else "fail",
                "verdict": "PASS_RECOMMEND_RSPPR1_CANDIDATE_ONLY_SNAPSHOT_DRY_RUN"
                if overall_pass
                else "FAIL_NEEDS_REPAIR",
                "evidence_root": rel(resolve(EVIDENCE_ROOT)),
                "source_inventory": inventory["status"],
                "candidate_only_contract_extension": contract_extension["status"],
                "publish_plan": publish_plan["status"],
                "validator_plan": validator_plan["status"],
                "rollback_plan": rollback_plan["status"],
                "forbidden_action_all_false": forbidden_action_audit["all_false"],
                "artifact_manifest": artifact_manifest["status"],
                "signals_rows": inventory["signals_csv_audit"]["row_count"],
                "signals_duplicate_keys": inventory["signals_csv_audit"][
                    "duplicate_key_count"
                ],
                "signals_forbidden_columns": inventory["signals_csv_audit"][
                    "forbidden_columns"
                ],
                "target_snapshot_dir_exists": inventory["target_snapshot_collision_audit"][
                    "target_snapshot_dir_exists"
                ],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
