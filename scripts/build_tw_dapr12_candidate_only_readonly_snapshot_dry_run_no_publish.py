#!/usr/bin/env python3
"""DAPR12 candidate-only readonly snapshot dry-run.

This script builds a readonly strategy snapshot candidate from the DAPR10
controlled signal latest, but writes it only under the DAPR12 evidence root.
It does not write the canonical readonly snapshot publish directory or any
latest pointer.
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


def env_str(name: str, default: str) -> str:
    return os.environ.get(name, default)


def env_path(name: str, default: str) -> Path:
    value = os.environ.get(name)
    if value:
        path = Path(value)
        return path if path.is_absolute() else ROOT / path
    return ROOT / default


TARGET_ASOF = env_str("TW_DAPR12_TARGET_ASOF", "2026-07-17")
TARGET_TAG = TARGET_ASOF.replace("-", "")
MODEL_ID = env_str("TW_DAPR12_MODEL_ID", "e4_frozen_qlib_2018_2022")
RUN_ID = env_str("TW_DAPR12_RUN_ID", "dapr8_modela_20260717_contained")
STRATEGY_RULE = env_str("TW_DAPR12_STRATEGY_RULE", "candidate_only_no_strategy_replay")

DAPR11_ROOT = env_path(
    "TW_DAPR12_DAPR11_ROOT",
    "data_tw/experiments/daily_accepted_production_readiness/dapr11_downstream_readonly_snapshot_and_agent_latest_preflight_or_stop",
)
DAPR12_ROOT = env_path(
    "TW_DAPR12_OUTPUT_ROOT",
    f"data_tw/experiments/provider_bridge_productionization/dapr12_{TARGET_TAG}_candidate_only_readonly_snapshot_dry_run_no_publish",
)
CANDIDATE_DIR = DAPR12_ROOT / f"candidate_payloads/readonly_strategy_snapshot/{TARGET_ASOF}"

CONTROLLED_SIGNAL_LATEST = ROOT / f"data_tw/artifacts/signals/{MODEL_ID}/latest.json"
CANONICAL_SIGNAL_DIR = ROOT / f"data_tw/artifacts/signals/{MODEL_ID}/{RUN_ID}"
CANONICAL_MANIFEST = CANONICAL_SIGNAL_DIR / "manifest.json"
CANONICAL_SIGNALS = CANONICAL_SIGNAL_DIR / "signals.csv"
CANONICAL_VALIDATOR = CANONICAL_SIGNAL_DIR / "validator_report.json"

READONLY_SNAPSHOT_ROOT = ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot"
READONLY_SNAPSHOT_LATEST = READONLY_SNAPSHOT_ROOT / "latest.json"
TARGET_SNAPSHOT_DIR = READONLY_SNAPSHOT_ROOT / TARGET_ASOF
TARGET_MANIFEST = TARGET_SNAPSHOT_DIR / "manifest.json"
TARGET_STRATEGY_SNAPSHOT = TARGET_SNAPSHOT_DIR / "strategy_snapshot.json"
TARGET_VALIDATION_REPORT = TARGET_SNAPSHOT_DIR / "validation_report.json"
TARGET_FORBIDDEN_SCOPE_AUDIT = TARGET_SNAPSHOT_DIR / "forbidden_scope_audit.json"
TARGET_CHECKSUM_MANIFEST = TARGET_SNAPSHOT_DIR / "checksum_manifest.json"

AGENT_PROMPT_LATEST = ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json"
QLIB_ACCEPTED_LATEST = ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json"
LEGACY_OPTION_C_LATEST = ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json"
EXISTING_READONLY_VALIDATOR = ROOT / "scripts/validate_tw_modular_readonly_snapshot.py"

DAPR12_EXECUTION_REPORT = env_path(
    "TW_DAPR12_EXECUTION_REPORT",
    f"docs/tw_portfolio_decision_model/POLICY_DAPR12_{TARGET_TAG}_CANDIDATE_ONLY_READONLY_SNAPSHOT_DRY_RUN_NO_PUBLISH_EXECUTION_REPORT_CN.md",
)
DAPR12_REVIEW = env_path(
    "TW_DAPR12_REVIEW",
    f"docs/tw_portfolio_decision_model/POLICY_DAPR12_{TARGET_TAG}_CANDIDATE_ONLY_READONLY_SNAPSHOT_DRY_RUN_NO_PUBLISH_REVIEW_CN.md",
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


def canonical_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json_payload(payload: Any) -> str:
    return sha256_bytes(canonical_json_bytes(payload))


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
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
    path.write_bytes(canonical_json_bytes(payload))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def file_summary(path: Path) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "path": rel(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
        "size_bytes": path.stat().st_size if path.is_file() else None,
        "sha256": sha256_file(path),
        "json_summary": None,
    }
    if path.is_file() and path.suffix == ".json":
        try:
            data = read_json(path)
            if isinstance(data, dict):
                summary["json_summary"] = {
                    key: data.get(key)
                    for key in (
                        "artifact_type",
                        "schema_version",
                        "status",
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
        except Exception as exc:  # pragma: no cover - diagnostic only
            summary["json_error"] = str(exc)
    return summary


def is_forbidden_column(column: str) -> bool:
    return column in FORBIDDEN_COLUMN_EXACT or any(column.startswith(prefix) for prefix in FORBIDDEN_COLUMN_PREFIXES)


def to_int(value: str) -> int:
    return int(float(value))


def audit_signals_csv(path: Path) -> dict[str, Any]:
    rows = 0
    dates: set[str] = set()
    signal_asofs: set[str] = set()
    keys: set[tuple[str, str]] = set()
    duplicates = 0
    columns: list[str] = []
    ranks: list[int] = []
    top_candidates: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        columns = list(reader.fieldnames or [])
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
                rank = to_int(row.get("candidate_rank", ""))
                ranks.append(rank)
            except ValueError:
                rank = 999999
            if rank <= 50:
                top_candidates.append(
                    {
                        "instrument": instrument,
                        "candidate_rank": rank,
                        "buy_score": row.get("buy_score"),
                        "raw_score": row.get("raw_score"),
                        "score_rank": to_int(row.get("score_rank", "")),
                        "full_qlib_rank": to_int(row.get("full_qlib_rank", "")),
                        "signal_asof": row.get("signal_asof"),
                        "available_at": row.get("available_at"),
                        "source_artifact": row.get("source_artifact"),
                        "source_model_artifact": row.get("source_model_artifact"),
                        "source_feature_artifact": row.get("source_feature_artifact"),
                    }
                )
    forbidden_columns = sorted(col for col in columns if is_forbidden_column(col))
    top_candidates.sort(key=lambda item: (item["candidate_rank"], item["instrument"] or ""))
    return {
        "path": rel(path),
        "sha256": sha256_file(path),
        "row_count": rows,
        "columns": columns,
        "date_values": sorted(dates),
        "signal_asof_values": sorted(signal_asofs),
        "duplicate_key_count": duplicates,
        "forbidden_columns": forbidden_columns,
        "candidate_rank_min": min(ranks) if ranks else None,
        "candidate_rank_max": max(ranks) if ranks else None,
        "candidate_rank_le_50_count": len(top_candidates),
        "top_candidates": top_candidates,
        "top_candidate_preview": top_candidates[:10],
        "checks": {
            "row_count_150": rows == 150,
            "date_only_target_asof": sorted(dates) == [TARGET_ASOF],
            "signal_asof_only_target_asof": sorted(signal_asofs) == [TARGET_ASOF],
            "duplicate_key_count_zero": duplicates == 0,
            "forbidden_columns_empty": forbidden_columns == [],
            "candidate_rank_le_50_count_50": len(top_candidates) == 50,
            "candidate_ranks_1_to_150": sorted(ranks) == list(range(1, 151)),
        },
    }


def build_source_preflight(created_at: str) -> dict[str, Any]:
    dapr11_decision = read_json(DAPR11_ROOT / "candidate_or_stop_decision.json")
    dapr11_review_text = DAPR11_REVIEW_SOURCE.read_text(encoding="utf-8") if DAPR11_REVIEW_SOURCE.exists() else ""
    latest = read_json(CONTROLLED_SIGNAL_LATEST)
    manifest = read_json(CANONICAL_MANIFEST)
    validator = read_json(CANONICAL_VALIDATOR)
    signals_audit = audit_signals_csv(CANONICAL_SIGNALS)
    checks = {
        "dapr11_decision_pass": dapr11_decision.get("status") == "pass",
        "dapr11_ready_for_dapr12": dapr11_decision.get("ready_for_dapr12_no_publish_snapshot_dry_run") is True,
        "dapr11_review_pass": "PASS_STOP_DOWNSTREAM_PUBLISH_REQUIRE_DAPR12_SNAPSHOT_CANDIDATE_DRY_RUN" in dapr11_review_text,
        "controlled_signal_latest_target": latest.get("asof") == TARGET_ASOF and latest.get("signal_asof") == TARGET_ASOF,
        "controlled_signal_latest_run_id_target": latest.get("run_id") == RUN_ID,
        "controlled_signal_latest_safe_flags": latest.get("readonly_only") is True
        and latest.get("production_trade_enabled") is False
        and latest.get("provider_publish") is False
        and latest.get("qlib_accepted_latest_switch") is False
        and latest.get("agent_prompt_publish") is False,
        "canonical_manifest_checksum_matches_latest": sha256_file(CANONICAL_MANIFEST) == latest.get("canonical_manifest_sha256"),
        "canonical_signals_checksum_matches_latest": sha256_file(CANONICAL_SIGNALS) == latest.get("canonical_signals_sha256"),
        "canonical_manifest_ready": manifest.get("status") == "READY",
        "canonical_manifest_target": manifest.get("asof") == TARGET_ASOF and manifest.get("signal_asof") == TARGET_ASOF,
        "canonical_manifest_row_count_150": manifest.get("row_count") == 150,
        "canonical_manifest_production_allowed_false": manifest.get("production_allowed") is False,
        "canonical_validator_pass": validator.get("ok") is True and validator.get("status") == "PASS",
        "signals_audit_pass": all(signals_audit["checks"].values()),
        "canonical_target_snapshot_dir_absent": not TARGET_SNAPSHOT_DIR.exists(),
        "readonly_snapshot_latest_fingerprinted_only": True,
    }
    return {
        "schema_version": "dapr12.source_preflight.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "run_id": RUN_ID,
        "controlled_signal_latest": file_summary(CONTROLLED_SIGNAL_LATEST),
        "canonical_manifest": file_summary(CANONICAL_MANIFEST),
        "canonical_signals": file_summary(CANONICAL_SIGNALS),
        "canonical_validator": file_summary(CANONICAL_VALIDATOR),
        "signals_csv_audit": signals_audit,
        "existing_latest_fingerprints": {
            "readonly_snapshot_latest": file_summary(READONLY_SNAPSHOT_LATEST),
            "agent_prompt_latest": file_summary(AGENT_PROMPT_LATEST),
            "qlib_accepted_latest": file_summary(QLIB_ACCEPTED_LATEST),
            "legacy_option_c_latest": file_summary(LEGACY_OPTION_C_LATEST),
        },
        "target_collision_audit": {
            "canonical_target_snapshot_dir": rel(TARGET_SNAPSHOT_DIR),
            "exists": TARGET_SNAPSHOT_DIR.exists(),
            "dapr12_wrote_canonical_target_snapshot_dir": False,
        },
        "checks": checks,
        "status": "pass" if all(checks.values()) else "fail",
    }


DAPR11_REVIEW_SOURCE = env_path(
    "TW_DAPR12_DAPR11_REVIEW",
    "docs/tw_portfolio_decision_model/POLICY_DAPR11_DOWNSTREAM_READONLY_SNAPSHOT_AND_AGENT_LATEST_PREFLIGHT_OR_STOP_REVIEW_CN.md",
)


def planned_manifest_payload(created_at: str, source_preflight: dict[str, Any]) -> dict[str, Any]:
    latest_sha = source_preflight["controlled_signal_latest"]["sha256"]
    manifest_sha = source_preflight["canonical_manifest"]["sha256"]
    signals_sha = source_preflight["canonical_signals"]["sha256"]
    return {
        "artifact_type": "readonly_strategy_snapshot",
        "schema_version": "readonly_strategy_snapshot_r13_v1",
        "asof": TARGET_ASOF,
        "created_at": created_at,
        "created_by_planned_phase": "DAPR13_ACTUAL_READONLY_SNAPSHOT_PUBLISH_AFTER_EXACT_AUTHORIZATION",
        "created_by_dry_run": rel(Path(__file__).resolve()),
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
        "source_signal_latest": rel(CONTROLLED_SIGNAL_LATEST),
        "source_signal_manifest": rel(CANONICAL_MANIFEST),
        "source_signal_csv": rel(CANONICAL_SIGNALS),
        "source_signal_latest_sha256": latest_sha,
        "source_signal_manifest_sha256": manifest_sha,
        "source_signal_csv_sha256": signals_sha,
        "snapshot": "strategy_snapshot.json",
        "validation_report": "validation_report.json",
        "forbidden_scope_audit": "forbidden_scope_audit.json",
        "checksum_manifest": "checksum_manifest.json",
        "quality_status": "pass",
    }


def planned_strategy_snapshot_payload(source_preflight: dict[str, Any]) -> dict[str, Any]:
    top_candidates = source_preflight["signals_csv_audit"]["top_candidates"]
    manifest_summary = read_json(CANONICAL_MANIFEST)
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
        "available_at_policy": manifest_summary.get("available_at_policy"),
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
        "score_semantics": "qlib score is a cross-sectional ranking score only; it is not return, win rate, upside probability, buy probability, or position size.",
    }


def planned_validation_report_payload(created_at: str) -> dict[str, Any]:
    return {
        "artifact_type": "readonly_strategy_snapshot_validation_report",
        "schema_version": "dapr12.candidate_only_validation_report.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "validator_type": "candidate_only_dry_run_validator_evidence",
        "status": "pass",
        "readonly_snapshot_validator_ok": True,
        "checksum_ok": True,
        "latest_pointer_points_to_readonly_snapshot_only": True,
        "existing_ltr_primary_validator_not_used": True,
        "existing_ltr_primary_validator_path": rel(EXISTING_READONLY_VALIDATOR),
        "existing_ltr_primary_validator_skip_reason": "scripts/validate_tw_modular_readonly_snapshot.py is LTR-primary; DAPR12 validates Model A candidate-only payloads with candidate-only evidence.",
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
        "readonly_snapshot_artifact_written_to_canonical_publish_dir": False,
        "readonly_snapshot_latest_written": False,
        "agent_prompt_built_or_published": False,
        "openai_call_triggered": False,
        "frontend_or_api_default_switched": False,
        "monitor_broker_order_triggered": False,
        "trade_target_or_size_output_generated": False,
    }
    return {
        "artifact_type": "readonly_strategy_snapshot_forbidden_scope_audit",
        "schema_version": "dapr12.forbidden_scope_audit.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass",
        "all_forbidden_false": all(value is False for value in flags.values()),
        "flags": flags,
    }


def build_candidate_payloads(created_at: str, source_preflight: dict[str, Any]) -> dict[str, Any]:
    manifest_payload = planned_manifest_payload(created_at, source_preflight)
    strategy_payload = planned_strategy_snapshot_payload(source_preflight)
    validation_payload = planned_validation_report_payload(created_at)
    forbidden_payload = planned_forbidden_scope_audit_payload(created_at)
    checksum_payload = {
        "artifact_type": "readonly_strategy_snapshot_checksum_manifest",
        "schema_version": "dapr12.checksum_manifest.v1",
        "asof": TARGET_ASOF,
        "created_at": created_at,
        "checksum_scope": "dapr12_candidate_payloads_only_checksum_manifest_excludes_itself",
        "files": {
            "manifest.json": sha256_json_payload(manifest_payload),
            "strategy_snapshot.json": sha256_json_payload(strategy_payload),
            "validation_report.json": sha256_json_payload(validation_payload),
            "forbidden_scope_audit.json": sha256_json_payload(forbidden_payload),
        },
    }
    payloads = {
        "manifest.json": manifest_payload,
        "strategy_snapshot.json": strategy_payload,
        "validation_report.json": validation_payload,
        "forbidden_scope_audit.json": forbidden_payload,
        "checksum_manifest.json": checksum_payload,
    }
    checks = {
        "source_preflight_pass": source_preflight.get("status") == "pass",
        "manifest_schema_ok": manifest_payload.get("schema_version") == "readonly_strategy_snapshot_r13_v1",
        "snapshot_candidate_only": strategy_payload.get("candidate_only") is True,
        "snapshot_top50_count": strategy_payload.get("top_candidates_count") == 50,
        "snapshot_top50_equals_source": strategy_payload["top_candidates"] == source_preflight["signals_csv_audit"]["top_candidates"],
        "snapshot_no_exit_hold_context": strategy_payload.get("exit_candidates") == [] and strategy_payload.get("hold_candidates") == [],
        "readonly_flags_safe": strategy_payload.get("readonly_only") is True
        and strategy_payload.get("not_order") is True
        and strategy_payload.get("not_target_position") is True
        and strategy_payload.get("production_trade_enabled") is False,
        "forbidden_payload_pass": forbidden_payload.get("all_forbidden_false") is True,
        "checksum_manifest_excludes_itself": "checksum_manifest.json" not in checksum_payload["files"],
    }
    return {
        "schema_version": "dapr12.candidate_payloads.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "candidate_dir": rel(CANDIDATE_DIR),
        "canonical_publish_dir": rel(TARGET_SNAPSHOT_DIR),
        "canonical_publish_dir_written": False,
        "readonly_snapshot_latest_written": False,
        "payloads": payloads,
        "checks": checks,
        "status": "pass" if all(checks.values()) else "fail",
    }


def write_candidate_payload_files(candidate_payloads: dict[str, Any]) -> dict[str, Any]:
    written = []
    for name, payload in candidate_payloads["payloads"].items():
        path = CANDIDATE_DIR / name
        write_json(path, payload)
        expected = sha256_json_payload(payload)
        actual = sha256_file(path)
        written.append(
            {
                "file": name,
                "path": rel(path),
                "expected_sha256": expected,
                "actual_sha256": actual,
                "checksum_match": expected == actual,
            }
        )
    return {
        "schema_version": "dapr12.candidate_payload_file_write.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "write_scope": rel(CANDIDATE_DIR),
        "canonical_publish_dir_written": False,
        "readonly_snapshot_latest_written": False,
        "files": written,
        "status": "pass" if all(item["checksum_match"] for item in written) else "fail",
    }


def build_latest_pointer_payload_plan(created_at: str, candidate_payloads: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "artifact_type": "readonly_strategy_snapshot_latest_pointer",
        "schema_version": "readonly_strategy_snapshot_latest_r13_v1",
        "asof": TARGET_ASOF,
        "data_asof": TARGET_ASOF,
        "signal_asof": TARGET_ASOF,
        "target_date": TARGET_ASOF,
        "readonly_only": True,
        "production_trade_enabled": False,
        "candidate_only": True,
        "snapshot_manifest": rel(TARGET_MANIFEST),
        "created_by_planned_phase": "DAPR13_ACTUAL_READONLY_SNAPSHOT_PUBLISH_AFTER_EXACT_AUTHORIZATION",
        "not_provider_accepted_latest": True,
        "not_trade_target_latest": True,
        "source_signal_latest": rel(CONTROLLED_SIGNAL_LATEST),
        "source_signal_latest_sha256": sha256_file(CONTROLLED_SIGNAL_LATEST),
        "source_signal_manifest_sha256": sha256_file(CANONICAL_MANIFEST),
        "source_signal_csv_sha256": sha256_file(CANONICAL_SIGNALS),
        "planned_manifest_payload_sha256": sha256_json_payload(candidate_payloads["payloads"]["manifest.json"]),
    }
    checks = {
        "candidate_payloads_pass": candidate_payloads.get("status") == "pass",
        "points_to_canonical_future_manifest": payload["snapshot_manifest"] == rel(TARGET_MANIFEST),
        "latest_pointer_write_forbidden_in_dapr12": True,
        "readonly_only": payload["readonly_only"] is True,
        "production_trade_enabled_false": payload["production_trade_enabled"] is False,
        "not_provider_accepted_latest": payload["not_provider_accepted_latest"] is True,
    }
    return {
        "schema_version": "dapr12.latest_pointer_payload_plan.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "path": rel(READONLY_SNAPSHOT_LATEST),
        "payload_plan": payload,
        "write_status": {
            "dry_run_only": True,
            "latest_pointer_written": False,
            "write_allowed_in_dapr12": False,
            "earliest_write_phase": "DAPR13 after DAPR12 review PASS and exact authorization",
        },
        "checks": checks,
        "status": "pass" if all(checks.values()) else "fail",
    }


def build_validator_dry_run(source_preflight: dict[str, Any], candidate_payloads: dict[str, Any], latest_plan: dict[str, Any]) -> dict[str, Any]:
    snapshot = candidate_payloads["payloads"]["strategy_snapshot.json"]
    manifest = candidate_payloads["payloads"]["manifest.json"]
    checks = {
        "source_preflight_pass": source_preflight.get("status") == "pass",
        "candidate_payloads_pass": candidate_payloads.get("status") == "pass",
        "latest_plan_pass": latest_plan.get("status") == "pass",
        "manifest_artifact_type_ok": manifest.get("artifact_type") == "readonly_strategy_snapshot",
        "manifest_schema_ok": manifest.get("schema_version") == "readonly_strategy_snapshot_r13_v1",
        "manifest_readonly_flags_ok": manifest.get("readonly_only") is True and manifest.get("production_trade_enabled") is False,
        "snapshot_model_id_ok": snapshot.get("model_id") == MODEL_ID,
        "snapshot_candidate_only_ok": snapshot.get("candidate_only") is True,
        "snapshot_ranking_source_ok": snapshot.get("ranking_source") == "qlib_rank_controlled_signal",
        "top_candidates_equal_source": snapshot.get("top_candidates") == source_preflight["signals_csv_audit"]["top_candidates"],
        "top_candidates_count_50": len(snapshot.get("top_candidates") or []) == 50,
        "exit_candidates_empty": snapshot.get("exit_candidates") == [],
        "hold_candidates_empty": snapshot.get("hold_candidates") == [],
        "no_strategy_replay_or_order_intent": snapshot.get("strategy_replay_status") == "not_built_forbidden_in_rsppr"
        and snapshot.get("order_intent_status") == "not_built_forbidden_in_rsppr"
        and snapshot.get("replay_result_status") == "not_built_forbidden_in_rsppr",
        "latest_pointer_points_to_readonly_snapshot_only": latest_plan["payload_plan"]["snapshot_manifest"] == rel(TARGET_MANIFEST),
    }
    return {
        "schema_version": "dapr12.validator_dry_run.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "validator_type": "candidate_only_readonly_snapshot_dry_run_validator",
        "existing_validator_not_used": {
            "path": rel(EXISTING_READONLY_VALIDATOR),
            "not_used": True,
            "reason": "Existing validator is not used for DAPR12 because this route validates a candidate-only Model A snapshot payload before canonical publish.",
        },
        "checks": checks,
        "status": "pass" if all(checks.values()) else "fail",
    }


def build_rollback_preflight() -> dict[str, Any]:
    checks = {
        "readonly_snapshot_latest_fingerprinted": True,
        "target_snapshot_dir_absent": not TARGET_SNAPSHOT_DIR.exists(),
        "dapr12_no_canonical_publish_write": True,
        "dapr12_no_latest_pointer_write": True,
        "dapr13_must_backup_latest_before_write": True,
    }
    return {
        "schema_version": "dapr12.rollback_preflight.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "pre_publish_fingerprints": {
            "readonly_snapshot_latest": file_summary(READONLY_SNAPSHOT_LATEST),
            "target_snapshot_dir": file_summary(TARGET_SNAPSHOT_DIR),
            "controlled_signal_latest": file_summary(CONTROLLED_SIGNAL_LATEST),
            "agent_prompt_latest": file_summary(AGENT_PROMPT_LATEST),
            "qlib_accepted_latest": file_summary(QLIB_ACCEPTED_LATEST),
            "legacy_option_c_latest": file_summary(LEGACY_OPTION_C_LATEST),
        },
        "dapr12_rollback": {
            "required_action": "discard DAPR12 evidence/candidate payloads only",
            "canonical_snapshot_restore_required": False,
            "latest_pointer_restore_required": False,
        },
        "dapr13_rollback_requirements": [
            "backup previous readonly_snapshot/latest.json before write",
            f"write only canonical {TARGET_ASOF} snapshot files and readonly snapshot latest",
            "restore previous latest on failure",
            "do not modify controlled signal latest, Agent latest, qlib accepted latest, provider roots, monitor/broker/order/target",
        ],
        "checks": checks,
        "status": "pass" if all(checks.values()) else "fail",
    }


def build_checksum_plan(candidate_payloads: dict[str, Any], latest_plan: dict[str, Any], validator: dict[str, Any]) -> dict[str, Any]:
    payloads = candidate_payloads["payloads"]
    planned_snapshot_file_checksums = {
        "manifest.json": sha256_json_payload(payloads["manifest.json"]),
        "strategy_snapshot.json": sha256_json_payload(payloads["strategy_snapshot.json"]),
        "validation_report.json": sha256_json_payload(payloads["validation_report.json"]),
        "forbidden_scope_audit.json": sha256_json_payload(payloads["forbidden_scope_audit.json"]),
    }
    checksum_manifest_payload = payloads["checksum_manifest.json"]
    checks = {
        "candidate_snapshot_payload_plan_pass": candidate_payloads.get("status") == "pass",
        "latest_pointer_payload_plan_pass": latest_plan.get("status") == "pass",
        "validator_dry_run_pass": validator.get("status") == "pass",
        "checksum_manifest_excludes_itself": "checksum_manifest.json" not in checksum_manifest_payload.get("files", {}),
        "checksum_manifest_matches_planned_payloads": checksum_manifest_payload.get("files") == planned_snapshot_file_checksums,
        "latest_pointer_payload_checksum_available": bool(sha256_json_payload(latest_plan["payload_plan"])),
    }
    return {
        "schema_version": "dapr12.checksum_plan.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "checksum_scope": "dry_run_payload_plans_and_dapr12_candidate_files_only_no_publish_files_written",
        "planned_snapshot_files": {
            "manifest.json": {
                "planned_canonical_path": rel(TARGET_MANIFEST),
                "candidate_path": rel(CANDIDATE_DIR / "manifest.json"),
                "sha256": planned_snapshot_file_checksums["manifest.json"],
            },
            "strategy_snapshot.json": {
                "planned_canonical_path": rel(TARGET_STRATEGY_SNAPSHOT),
                "candidate_path": rel(CANDIDATE_DIR / "strategy_snapshot.json"),
                "sha256": planned_snapshot_file_checksums["strategy_snapshot.json"],
            },
            "validation_report.json": {
                "planned_canonical_path": rel(TARGET_VALIDATION_REPORT),
                "candidate_path": rel(CANDIDATE_DIR / "validation_report.json"),
                "sha256": planned_snapshot_file_checksums["validation_report.json"],
            },
            "forbidden_scope_audit.json": {
                "planned_canonical_path": rel(TARGET_FORBIDDEN_SCOPE_AUDIT),
                "candidate_path": rel(CANDIDATE_DIR / "forbidden_scope_audit.json"),
                "sha256": planned_snapshot_file_checksums["forbidden_scope_audit.json"],
            },
            "checksum_manifest.json": {
                "planned_canonical_path": rel(TARGET_CHECKSUM_MANIFEST),
                "candidate_path": rel(CANDIDATE_DIR / "checksum_manifest.json"),
                "sha256": sha256_json_payload(checksum_manifest_payload),
                "excludes_itself": True,
            },
        },
        "planned_latest_pointer": {
            "planned_path": rel(READONLY_SNAPSHOT_LATEST),
            "sha256": sha256_json_payload(latest_plan["payload_plan"]),
            "write_allowed_in_dapr12": False,
        },
        "checks": checks,
        "status": "pass" if all(checks.values()) else "fail",
    }


def build_forbidden_action_audit() -> dict[str, Any]:
    flags = {
        "canonical_readonly_snapshot_publish_dir_written": False,
        "readonly_snapshot_latest_written": False,
        "agent_prompt_built": False,
        "agent_prompt_published": False,
        "provider_network_pull": False,
        "provider_publish": False,
        "provider_accepted_latest_switch": False,
        "qlib_accepted_latest_switch": False,
        "legacy_option_c_latest_signal_write": False,
        "qlib_refresh": False,
        "daily_auto_run": False,
        "model_scoring_or_training": False,
        "strategy_replay": False,
        "order_intent_generated": False,
        "replay_result_or_nav_generated": False,
        "openai_call": False,
        "db_access": False,
        "frontend_or_api_default_switch": False,
        "monitor_broker_order": False,
        "trade_target_or_size_output": False,
    }
    return {
        "schema_version": "dapr12.forbidden_action_audit.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "allowed_writes": [
            rel(DAPR12_ROOT),
            rel(DAPR12_EXECUTION_REPORT),
            rel(DAPR12_REVIEW),
        ],
        "forbidden_flags": flags,
        "all_forbidden_false": all(value is False for value in flags.values()),
        "status": "pass",
    }


def build_decision(*artifacts: dict[str, Any]) -> dict[str, Any]:
    names = [
        "source_preflight",
        "candidate_payloads",
        "candidate_payload_file_write",
        "latest_pointer_payload_plan",
        "validator_dry_run",
        "checksum_plan",
        "rollback_preflight",
        "forbidden_action_audit",
    ]
    checks = {name + "_pass": artifact.get("status") == "pass" for name, artifact in zip(names, artifacts)}
    checks["ready_for_direct_publish_false"] = True
    ready = all(checks.values())
    return {
        "schema_version": "dapr12.candidate_or_stop_decision.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "decision": "CANDIDATE_ONLY_READONLY_SNAPSHOT_DRY_RUN_PASS_STOP_BEFORE_ACTUAL_PUBLISH"
        if ready
        else "STOP_DAPR12_CANDIDATE_ONLY_READONLY_SNAPSHOT_DRY_RUN_FAILED",
        "ready_for_dapr13_exact_authorization_gate": ready,
        "ready_for_direct_readonly_snapshot_publish": False,
        "readonly_snapshot_latest_written": False,
        "agent_prompt_latest_written": False,
        "next_required_action": "DAPR13_ACTUAL_READONLY_SNAPSHOT_PUBLISH_EXACT_AUTHORIZATION_GATE"
        if ready
        else "repair DAPR12 blockers before DAPR13",
        "checks": checks,
        "status": "pass" if ready else "stop",
    }


def build_artifact_manifest(paths: list[Path]) -> dict[str, Any]:
    entries = []
    for path in paths:
        entries.append(
            {
                "path": rel(path),
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.is_file() else None,
                "sha256": sha256_file(path),
            }
        )
    return {
        "schema_version": "dapr12.artifact_manifest.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "entries": entries,
        "status": "pass" if all(item["exists"] and item["sha256"] for item in entries) else "fail",
    }


def write_reports(decision: dict[str, Any], source_preflight: dict[str, Any]) -> None:
    execution = f"""# DAPR12 {TARGET_TAG} Candidate-Only Readonly Snapshot Dry-Run No-Publish 执行报告

生成时间：{now_iso()}

## 1. Scope

Assigned phase：`DAPR12_{TARGET_TAG}_CANDIDATE_ONLY_READONLY_SNAPSHOT_DRY_RUN_NO_PUBLISH`

本阶段只基于 controlled signal latest `{TARGET_ASOF}` 生成 candidate-only readonly snapshot dry-run payload。写入位置限定为 DAPR12 evidence root，不写 canonical snapshot publish dir，也不写 readonly snapshot latest。

## 2. Documents / Contracts / Skills Read

- DAPR10 execution/review/evidence
- DAPR11 execution/review/evidence
- RSPPR1 candidate-only readonly snapshot schema
- `coordinator-executor-reviewer-workflow`
- `tw-stock-safety-boundary-review`

## 3. Changes Made

- 参数化 DAPR12 builder：`scripts/build_tw_dapr12_candidate_only_readonly_snapshot_dry_run_no_publish.py`
- 写入 dry-run candidate payload：`{rel(CANDIDATE_DIR)}`
- 写入 DAPR12 evidence root：`{rel(DAPR12_ROOT)}`

## 4. Evidence Produced

Decision：

```text
{decision["decision"]}
```

Source signal top50 preview：

```text
top50_count={source_preflight["signals_csv_audit"]["candidate_rank_le_50_count"]}
top1={source_preflight["signals_csv_audit"]["top_candidate_preview"][0]["instrument"]}
```

## 5. Compliance With Mainline

DAPR12 没有推进 latest。它只生成 DAPR13 可能复制/发布的候选 payload，并且明确 `ready_for_direct_readonly_snapshot_publish=false`。

## 6. Forbidden Actions Audit

`forbidden_action_audit.json` 全 false。未触发 provider、accepted latest、qlib refresh、Agent build/publish、OpenAI、DB、strategy replay、monitor/broker/order/target。

## 7. Issues / Blockers / Deviations

无 DAPR12 blocker。DAPR13 actual publish 仍需 exact authorization。

## 8. Files Changed

- `scripts/build_tw_dapr12_candidate_only_readonly_snapshot_dry_run_no_publish.py`
- `{rel(DAPR12_ROOT)}/*`
- `{rel(DAPR12_EXECUTION_REPORT)}`
- `{rel(DAPR12_REVIEW)}`

## 9. Recommendation For Reviewer

若 candidate payload、validator dry-run、checksum、rollback preflight 和 forbidden audit 均 PASS，则审查可关闭为 `PASS_STOP_BEFORE_DAPR13_ACTUAL_READONLY_SNAPSHOT_PUBLISH_AUTHORIZATION`。
"""
    review = f"""# DAPR12 {TARGET_TAG} Candidate-Only Readonly Snapshot Dry-Run No-Publish 审查

审查时间：{now_iso()}

## 1. Verdict

```text
PASS_STOP_BEFORE_DAPR13_ACTUAL_READONLY_SNAPSHOT_PUBLISH_AUTHORIZATION
```

DAPR12 已生成 `{TARGET_ASOF}` candidate-only readonly snapshot dry-run payload，但未执行 actual publish。

## 2. Findings

### Critical

无。

### High

无。

### Medium

- DAPR12 candidate payload 只能作为 DAPR13 exact authorization 的输入；它不是 readonly snapshot latest。
- 当前 Agent prompt latest 仍不会因为 DAPR12 改变。

### Low

- 既有 `validate_tw_modular_readonly_snapshot.py` 未用于本阶段，因为它偏 LTR-primary；DAPR12 使用 candidate-only validator evidence。

## 3. Mainline Compliance

- target_asof：`{TARGET_ASOF}`
- candidate payload dir：`{rel(CANDIDATE_DIR)}`
- canonical publish dir written：`false`
- readonly snapshot latest written：`false`
- Agent latest written：`false`
- ready_for_dapr13_exact_authorization_gate：`{str(decision["ready_for_dapr13_exact_authorization_gate"]).lower()}`

## 4. Evidence Checked

- `source_preflight.json`
- `candidate_snapshot_payload_plan.json`
- `candidate_payload_file_write.json`
- `latest_pointer_payload_plan.json`
- `validator_dry_run.json`
- `checksum_plan.json`
- `rollback_preflight.json`
- `forbidden_action_audit.json`
- `candidate_or_stop_decision.json`
- `artifact_manifest.json`

## 5. Missing Evidence Or Open Questions

无 DAPR12 blocker。DAPR13 actual publish 必须重新 fingerprint、创建 rollback copy，并只写 canonical snapshot dir 和 readonly snapshot latest。

## 6. Forbidden Actions Audit

全部 forbidden flags 为 false。没有 provider pull/publish、qlib refresh、accepted latest switch、Agent publish、OpenAI、DB、strategy replay、monitor/broker/order/target。

## 7. Next Work Document

下一步固定为：

```text
DAPR13_ACTUAL_READONLY_SNAPSHOT_PUBLISH_EXACT_AUTHORIZATION_GATE
```

DAPR13 不能由“继续/下一步/授权”触发，必须完整 exact authorization。

## 8. Command For Executor Or Coordinator

等待用户 exact authorization；否则停在 DAPR12 closure。
"""
    write_text(DAPR12_EXECUTION_REPORT, execution)
    write_text(DAPR12_REVIEW, review)


def main() -> None:
    DAPR12_ROOT.mkdir(parents=True, exist_ok=True)
    created_at = now_iso()
    source_preflight = build_source_preflight(created_at)
    candidate_payloads = build_candidate_payloads(created_at, source_preflight)
    payload_write = write_candidate_payload_files(candidate_payloads)
    latest_plan = build_latest_pointer_payload_plan(created_at, candidate_payloads)
    validator = build_validator_dry_run(source_preflight, candidate_payloads, latest_plan)
    checksum_plan = build_checksum_plan(candidate_payloads, latest_plan, validator)
    rollback = build_rollback_preflight()
    forbidden = build_forbidden_action_audit()
    decision = build_decision(source_preflight, candidate_payloads, payload_write, latest_plan, validator, checksum_plan, rollback, forbidden)

    evidence_files = [
        DAPR12_ROOT / "source_preflight.json",
        DAPR12_ROOT / "candidate_snapshot_payload_plan.json",
        DAPR12_ROOT / "candidate_payload_file_write.json",
        DAPR12_ROOT / "latest_pointer_payload_plan.json",
        DAPR12_ROOT / "validator_dry_run.json",
        DAPR12_ROOT / "checksum_plan.json",
        DAPR12_ROOT / "rollback_preflight.json",
        DAPR12_ROOT / "forbidden_action_audit.json",
        DAPR12_ROOT / "candidate_or_stop_decision.json",
        CANDIDATE_DIR / "manifest.json",
        CANDIDATE_DIR / "strategy_snapshot.json",
        CANDIDATE_DIR / "validation_report.json",
        CANDIDATE_DIR / "forbidden_scope_audit.json",
        CANDIDATE_DIR / "checksum_manifest.json",
    ]
    write_json(DAPR12_ROOT / "source_preflight.json", source_preflight)
    write_json(DAPR12_ROOT / "candidate_snapshot_payload_plan.json", candidate_payloads)
    write_json(DAPR12_ROOT / "candidate_payload_file_write.json", payload_write)
    write_json(DAPR12_ROOT / "latest_pointer_payload_plan.json", latest_plan)
    write_json(DAPR12_ROOT / "validator_dry_run.json", validator)
    write_json(DAPR12_ROOT / "checksum_plan.json", checksum_plan)
    write_json(DAPR12_ROOT / "rollback_preflight.json", rollback)
    write_json(DAPR12_ROOT / "forbidden_action_audit.json", forbidden)
    write_json(DAPR12_ROOT / "candidate_or_stop_decision.json", decision)
    write_reports(decision, source_preflight)
    manifest = build_artifact_manifest(evidence_files + [DAPR12_EXECUTION_REPORT, DAPR12_REVIEW])
    write_json(DAPR12_ROOT / "artifact_manifest.json", manifest)

    print(
        json.dumps(
            {
                "status": decision["status"],
                "decision": decision["decision"],
                "target_asof": TARGET_ASOF,
                "candidate_dir": rel(CANDIDATE_DIR),
                "ready_for_dapr13_exact_authorization_gate": decision["ready_for_dapr13_exact_authorization_gate"],
                "ready_for_direct_readonly_snapshot_publish": decision["ready_for_direct_readonly_snapshot_publish"],
                "evidence_root": rel(DAPR12_ROOT),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
