#!/usr/bin/env python3
"""Build the immutable B19R2R V4 logical source-run inventory."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ASOF = "2026-09-16"
NEXT_OPEN = "2026-09-17T01:00:00+00:00"
MODEL_A_ID = "e4_frozen_qlib_2018_2022"
FINMIND_RUN_ID = "finmind.logical.20260916.2e6d6cc1257daf79dcdc"
REQUIRED_ROLES = ("daily_price", "institutional", "margin", "model_a_inference", "twii_yahoo")
OUT_ROOT = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_v4_source_run_20260916"

PRICE_ADAPTER = ROOT / "data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260916_20260916T103002Z/same_run_handoff_artifacts/daily_price/daily_price.adapter_output.json"
INSTITUTIONAL_ADAPTER = ROOT / "data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260916_20260916T144502Z/same_run_handoff_artifacts/institutional/institutional.adapter_output.json"
MARGIN_ADAPTER = ROOT / "data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260916_20260916T144502Z/same_run_handoff_artifacts/margin/margin.adapter_output.json"
MODEL_A_RUN = ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260916_20260916T145712Z"
MODEL_A_PREDICTION = MODEL_A_RUN / "prediction.csv"
MODEL_A_METADATA = MODEL_A_RUN / "run_metadata.json"
MODEL_A_ARTIFACT_MANIFEST = MODEL_A_RUN / "artifact_manifest.json"
MODEL_A_SECONDARY_RUN = ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260916_20260916T145733Z"
MODEL_A_SECONDARY_PREDICTION = MODEL_A_SECONDARY_RUN / "prediction.csv"
MODEL_A_SECONDARY_METADATA = MODEL_A_SECONDARY_RUN / "run_metadata.json"
MODEL_A_SECONDARY_ARTIFACT_MANIFEST = MODEL_A_SECONDARY_RUN / "artifact_manifest.json"
MODEL_A_FORMAL_MANIFEST = ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/dng9_daily_auto_model_signal_gate_20260916_20260916T145726Z/manifest.json"
MODEL_A_FORMAL_SIGNALS = MODEL_A_FORMAL_MANIFEST.parent / "signals.csv"
TWII_DIR = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_v3_manual_source_20260916/twii_acquisition_v5_yahoo_scrapling"
TWII_MANIFEST = TWII_DIR / "TWII_CAPTURE_MANIFEST.json"
TWII_CAPTURE_IMPLEMENTATION = ROOT / "scripts/capture_modelb_b19r2r_twii_yahoo_20260916.py"
TWII_VALIDATION = TWII_DIR.parent / "TWII_V5_VALIDATION_V2.json"
TWII_INDEPENDENT_REVIEW = TWII_DIR.parent / "TWII_V5_INDEPENDENT_REVIEW.json"
TWII_CAPTURE_VALIDATOR = ROOT / "scripts/validate_modelb_b19r2r_twii_yahoo_capture_v2_20260916.py"
TWII_CAPTURE_TESTS = ROOT / "tests/isolated/test_modelb_b19r2r_twii_yahoo_capture_20260916.py"
TWII_INDEPENDENT_REVIEW_SHA = "84f99384ebe80ca9a77dc308e83762b11037b42c2eb6b6c20429b95f8e041218"
CLEAN_CALENDAR = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_pretraining_materialization_20260916/isolated_model_a_provider_no_nontrading_placeholders/calendars/day.txt"
CLEAN_CALENDAR_SHA = "953d55c48367d309f3bc93fb1f3a9095f417feb6032d24da04d3475c1a4e2aa7"
CLEAN_CALENDAR_MANIFEST = CLEAN_CALENDAR.parent.parent / "B19R2R_ISOLATED_PROVIDER_MANIFEST.json"
B19R1_REVIEW = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r1_independent_review_20260916/B19R1_FINAL_INDEPENDENT_REVIEW.json"
B19R2R_REVIEW = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_postmaterialization_independent_review_20260916/B19R2R_POSTMATERIALIZATION_INDEPENDENT_REVIEW.json"

PROTECTED = (
    ROOT / "configs/tw_modular_registry.yaml",
    ROOT / "configs/active_baseline_descriptor.yaml",
    ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json",
)


class InventoryError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryError("B19V4I_E_JSON", str(path)) from exc
    if not isinstance(value, dict):
        raise InventoryError("B19V4I_E_JSON", str(path))
    return value


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def parse_time(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise InventoryError("B19V4I_E_TIME", str(value)) from exc
    if parsed.tzinfo is None:
        raise InventoryError("B19V4I_E_TIME", str(value))
    return parsed.astimezone(UTC)


def artifact(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise InventoryError("B19V4I_E_ARTIFACT_MISSING", str(path))
    return {"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256(path)}


def resolve_declared(path: Any) -> Path:
    value = Path(str(path))
    return value if value.is_absolute() else ROOT / value


def fingerprints() -> dict[str, str | None]:
    return {rel(path): sha256(path) if path.is_file() else None for path in PROTECTED}


def declared_artifact(value: dict[str, Any]) -> dict[str, Any]:
    path = resolve_declared(value.get("path", "__missing__"))
    actual = artifact(path)
    if value.get("sha256") != actual["sha256"]:
        raise InventoryError("B19V4I_E_ARTIFACT_HASH", str(path))
    if value.get("bytes") not in (None, actual["bytes"]):
        raise InventoryError("B19V4I_E_ARTIFACT_BYTES", str(path))
    role = value.get("role")
    return {**actual, **({"role": role} if role else {})}


def finmind_child(role: str, path: Path) -> dict[str, Any]:
    value = read_json(path)
    if (
        value.get("status") != "captured"
        or value.get("acquisition_run_id") != FINMIND_RUN_ID
        or value.get("target_asof") != ASOF
        or value.get("trade_date") != ASOF
        or value.get("pit_status") != "PASS"
        or value.get("validator_status") != "PASS"
    ):
        raise InventoryError("B19V4I_E_FINMIND_BINDING", role)
    normalized = value.get("normalized_files")
    raw = value.get("raw_files")
    if not isinstance(normalized, list) or len(normalized) != 1 or not isinstance(raw, list) or len(raw) != 150:
        raise InventoryError("B19V4I_E_FINMIND_SCOPE", role)
    normalized_artifact = declared_artifact(normalized[0])
    raw_artifacts = [declared_artifact(item) for item in raw]
    available_at = str(value.get("available_at") or "")
    if parse_time(available_at) >= parse_time(NEXT_OPEN):
        raise InventoryError("B19V4I_E_AFTER_NEXT_OPEN", role)
    return {
        "role": role,
        "provider": value.get("provider"),
        "source_id": value.get("dataset"),
        "physical_run_id": FINMIND_RUN_ID,
        "asof": ASOF,
        "trade_date": ASOF,
        "fetched_at": value.get("fetched_at"),
        "available_at": available_at,
        "pit_status": "PASS",
        "validator_status": "PASS",
        "metadata": artifact(path),
        "normalized_artifact": normalized_artifact,
        "raw_artifact_count": len(raw_artifacts),
        "raw_artifact_inventory_sha256": canonical_sha(raw_artifacts),
        "raw_artifacts": raw_artifacts,
    }


def model_a_child() -> dict[str, Any]:
    metadata = read_json(MODEL_A_METADATA)
    manifest = read_json(MODEL_A_ARTIFACT_MANIFEST)
    secondary_metadata = read_json(MODEL_A_SECONDARY_METADATA)
    secondary_manifest = read_json(MODEL_A_SECONDARY_ARTIFACT_MANIFEST)
    formal = read_json(MODEL_A_FORMAL_MANIFEST)
    entry = next((item for item in manifest.get("entries", []) if item.get("key") == "prediction"), None)
    secondary_entry = next(
        (item for item in secondary_manifest.get("entries", []) if item.get("key") == "prediction"), None
    )
    primary_available_at = metadata.get("created_at")
    secondary_available_at = secondary_metadata.get("created_at")
    formal_available_at = formal.get("created_at")
    model_path = ROOT / "qlib_pipeline" / str(metadata.get("model_path") or "__missing__")
    formal_source = ROOT / "qlib_pipeline" / str(formal.get("source_artifact") or "__missing__")
    formal_model = ROOT / str(formal.get("source_model_artifact") or "__missing__")
    if (
        metadata.get("status") != "accepted"
        or metadata.get("asof") != ASOF
        or metadata.get("run_id") != MODEL_A_RUN.name
        or manifest.get("status") != "accepted"
        or manifest.get("run_id") != MODEL_A_RUN.name
        or manifest.get("created_at") != primary_available_at
        or not isinstance(entry, dict)
        or entry.get("sha256") != sha256(MODEL_A_PREDICTION)
        or secondary_metadata.get("status") != "accepted"
        or secondary_metadata.get("asof") != ASOF
        or secondary_metadata.get("run_id") != MODEL_A_SECONDARY_RUN.name
        or secondary_manifest.get("status") != "accepted"
        or secondary_manifest.get("run_id") != MODEL_A_SECONDARY_RUN.name
        or secondary_manifest.get("created_at") != secondary_available_at
        or not isinstance(secondary_entry, dict)
        or secondary_entry.get("sha256") != sha256(MODEL_A_SECONDARY_PREDICTION)
        or sha256(MODEL_A_SECONDARY_PREDICTION) != sha256(MODEL_A_PREDICTION)
        or secondary_metadata.get("frozen_recorder") != metadata.get("frozen_recorder")
        or secondary_metadata.get("model_path") != metadata.get("model_path")
        or not model_path.is_file()
        or formal.get("model_id") != MODEL_A_ID
        or formal.get("asof") != ASOF
        or formal.get("status") != "READY"
        or formal.get("row_count") != 150
        or formal_source.resolve() != MODEL_A_SECONDARY_PREDICTION.resolve()
        or formal_model.resolve() != model_path.resolve()
        or formal.get("source_acquisition_run_id") != FINMIND_RUN_ID
        or parse_time(primary_available_at) >= parse_time(NEXT_OPEN)
        or parse_time(secondary_available_at) >= parse_time(NEXT_OPEN)
        or parse_time(formal_available_at) >= parse_time(NEXT_OPEN)
    ):
        raise InventoryError("B19V4I_E_MODELA_BINDING")
    available_at = max(
        parse_time(primary_available_at),
        parse_time(secondary_available_at),
        parse_time(formal_available_at),
    ).isoformat(timespec="microseconds")
    child = {
        "role": "model_a_inference",
        "provider": "project_fixed_model_a_inference",
        "source_id": MODEL_A_ID,
        "physical_run_id": MODEL_A_RUN.name,
        "supporting_physical_run_ids": [MODEL_A_SECONDARY_RUN.name, formal.get("run_id")],
        "upstream_physical_run_ids": [FINMIND_RUN_ID],
        "asof": ASOF,
        "trade_date": ASOF,
        "fetched_at": None,
        "available_at": available_at,
        "pit_status": "PIT_SAFE",
        "validator_status": "accepted",
        "primary_inference": {
            "physical_run_id": MODEL_A_RUN.name,
            "available_at": primary_available_at,
            "selection_role": "exact50_scoring_source",
        },
        "model_identity": {
            "model_id": MODEL_A_ID,
            "frozen_recorder": metadata.get("frozen_recorder"),
            "model_artifact": artifact(model_path),
            "attestation_semantics": "secondary_formal_identity_and_exact_prediction_parity_only",
        },
        "secondary_identity_attestation": {
            "physical_run_id": formal.get("run_id"),
            "upstream_physical_run_id": MODEL_A_SECONDARY_RUN.name,
            "upstream_available_at": secondary_available_at,
            "available_at": formal_available_at,
            "declared_decision_cutoff": formal.get("decision_cutoff"),
            "declared_cutoff_precedes_upstream_available_at": (
                parse_time(formal.get("decision_cutoff")) < parse_time(secondary_available_at)
            ),
            "allowed_use": "canonical_model_id_and_exact_prediction_parity_attestation_only",
            "pit_timing_authority": False,
            "source_prediction_equals_primary": True,
            "artifacts": {
                "prediction": artifact(MODEL_A_SECONDARY_PREDICTION),
                "run_metadata": artifact(MODEL_A_SECONDARY_METADATA),
                "artifact_manifest": artifact(MODEL_A_SECONDARY_ARTIFACT_MANIFEST),
                "formal_manifest": artifact(MODEL_A_FORMAL_MANIFEST),
                "formal_signals": artifact(MODEL_A_FORMAL_SIGNALS),
            },
        },
        "artifacts": {
            "prediction": artifact(MODEL_A_PREDICTION),
            "run_metadata": artifact(MODEL_A_METADATA),
            "artifact_manifest": artifact(MODEL_A_ARTIFACT_MANIFEST),
        },
    }
    validate_model_a_lineage(child)
    return child


def validate_model_a_lineage(child: dict[str, Any]) -> None:
    primary = child.get("primary_inference", {})
    identity = child.get("model_identity", {})
    secondary = child.get("secondary_identity_attestation", {})
    supporting = child.get("supporting_physical_run_ids")
    primary_available = parse_time(primary.get("available_at"))
    secondary_upstream_available = parse_time(secondary.get("upstream_available_at"))
    secondary_available = parse_time(secondary.get("available_at"))
    child_available = parse_time(child.get("available_at"))
    expected_available = max(primary_available, secondary_upstream_available, secondary_available)
    if (
        child.get("role") != "model_a_inference"
        or child.get("source_id") != MODEL_A_ID
        or child.get("physical_run_id") != MODEL_A_RUN.name
        or primary.get("physical_run_id") != MODEL_A_RUN.name
        or supporting != [MODEL_A_SECONDARY_RUN.name, secondary.get("physical_run_id")]
        or secondary.get("upstream_physical_run_id") != MODEL_A_SECONDARY_RUN.name
        or not str(secondary.get("physical_run_id") or "").startswith("dng9_daily_auto_model_signal_gate_")
        or identity.get("model_id") != MODEL_A_ID
        or secondary.get("allowed_use") != "canonical_model_id_and_exact_prediction_parity_attestation_only"
        or secondary.get("pit_timing_authority") is not False
        or secondary.get("source_prediction_equals_primary") is not True
        or child_available != expected_available
    ):
        raise InventoryError("B19V4I_E_MODELA_LINEAGE")


def yahoo_child() -> dict[str, Any]:
    value = read_json(TWII_MANIFEST)
    validation = read_json(TWII_VALIDATION)
    review = read_json(TWII_INDEPENDENT_REVIEW)
    available_at = value.get("available_at")
    if (
        value.get("status") != "PASS_REVIEWABLE_CANDIDATE"
        or value.get("provider") != "Yahoo Finance"
        or value.get("official_source") is not False
        or value.get("target_asof") != ASOF
        or value.get("trade_date") != ASOF
        or value.get("pit_status") != "PASS"
        or not str(value.get("validator_status") or "").startswith("PASS")
        or value.get("protected_unchanged") is not True
        or value.get("production_allowed") is not False
        or parse_time(available_at) >= parse_time(NEXT_OPEN)
    ):
        raise InventoryError("B19V4I_E_YAHOO_BINDING")
    manifest_sha = sha256(TWII_MANIFEST)
    implementation_sha = sha256(TWII_CAPTURE_IMPLEMENTATION)
    validation_implementation = validation.get("implementation", {})
    if (
        validation.get("status") != "PASS"
        or validation.get("source_manifest") != rel(TWII_MANIFEST)
        or validation.get("source_manifest_sha256") != manifest_sha
        or validation_implementation.get("capture_script") != rel(TWII_CAPTURE_IMPLEMENTATION)
        or validation_implementation.get("capture_script_sha256") != implementation_sha
        or validation.get("capture_or_ledger_append_authorized") is not False
        or validation.get("upper_layer_materialization_authorized") is not False
        or validation.get("score_gate", {}).get("scoring_authorized") is not False
    ):
        raise InventoryError("B19V4I_E_YAHOO_VALIDATION_BINDING")
    review_manifest = review.get("reviewed_capture_manifest", {})
    review_validation = review.get("reviewed_validation", {})
    review_implementation = review.get("reviewed_capture_implementation", {})
    review_validator = review.get("reviewed_validator_implementation", {})
    review_tests = review.get("reviewed_test_implementation", {})
    authorization = review.get("authorization", {})
    if (
        sha256(TWII_INDEPENDENT_REVIEW) != TWII_INDEPENDENT_REVIEW_SHA
        or review.get("schema_version") != "modelb_b19r2r.twii_v5_independent_review.v1"
        or review.get("verdict") != "PASS"
        or review.get("status") != "PASS_TWII_CHILD_EVIDENCE_ONLY_UPPER_LAYER_CAPTURE_NOT_AUTHORIZED"
        or review_manifest.get("path") != rel(TWII_MANIFEST)
        or review_manifest.get("sha256") != manifest_sha
        or review_validation.get("path") != rel(TWII_VALIDATION)
        or review_validation.get("sha256") != sha256(TWII_VALIDATION)
        or review_implementation.get("path") != rel(TWII_CAPTURE_IMPLEMENTATION)
        or review_implementation.get("sha256") != implementation_sha
        or review_validator.get("path") != rel(TWII_CAPTURE_VALIDATOR)
        or review_validator.get("sha256") != sha256(TWII_CAPTURE_VALIDATOR)
        or review_tests.get("path") != rel(TWII_CAPTURE_TESTS)
        or review_tests.get("sha256") != sha256(TWII_CAPTURE_TESTS)
        or authorization.get("composite_child_consumption_authorized") is not True
        or authorization.get("composite_wrapper_implementation_authorized") is not True
        or authorization.get("upper_layer_model_b_scoring_authorized") is not False
        or authorization.get("signal_captured_authorized") is not False
        or authorization.get("capture_authorized") is not False
        or authorization.get("accepted_ledger_append_authorized") is not False
        or authorization.get("accepted_ledger_event_written") is not False
        or authorization.get("training_authorized") is not False
        or authorization.get("baseline_change_authorized") is not False
        or authorization.get("production_change_authorized") is not False
        or authorization.get("provider_publish_authorized") is not False
        or authorization.get("accepted_latest_switch_authorized") is not False
        or authorization.get("latest_write_authorized") is not False
    ):
        raise InventoryError("B19V4I_E_YAHOO_REVIEW_BINDING")
    artifacts = value.get("artifacts")
    required = {
        "daily_request", "daily_response_headers", "daily_raw_response",
        "intraday_request", "intraday_response_headers", "intraday_raw_response",
        "normalized_csv", "normalized_schema",
    }
    if not isinstance(artifacts, dict) or set(artifacts) != required:
        raise InventoryError("B19V4I_E_YAHOO_ARTIFACT_SCOPE")
    checked = {name: declared_artifact(item) for name, item in sorted(artifacts.items())}
    coverage = value.get("coverage", {})
    if coverage.get("target_row_count") != 1 or coverage.get("date_max") != ASOF or coverage.get("normalized_row_count", 0) < 120:
        raise InventoryError("B19V4I_E_YAHOO_COVERAGE")
    run_id = str(value.get("acquisition_run_id") or "")
    if not run_id or run_id == FINMIND_RUN_ID:
        raise InventoryError("B19V4I_E_YAHOO_RUN_ID")
    return {
        "role": "twii_yahoo",
        "provider": "Yahoo Finance",
        "source_id": value.get("source_id"),
        "physical_run_id": run_id,
        "asof": ASOF,
        "trade_date": ASOF,
        "fetched_at": value.get("fetched_at"),
        "available_at": available_at,
        "pit_status": "PASS",
        "validator_status": value.get("validator_status"),
        "selector": "^TWII",
        "subrequest_roles": ["daily_history", "target_day_1m_aggregation"],
        "metadata": artifact(TWII_MANIFEST),
        "capture_implementation": artifact(TWII_CAPTURE_IMPLEMENTATION),
        "validation": artifact(TWII_VALIDATION),
        "independent_review": artifact(TWII_INDEPENDENT_REVIEW),
        "artifacts": checked,
        "coverage": coverage,
    }


def extended_calendar() -> tuple[list[str], dict[str, Any]]:
    if sha256(CLEAN_CALENDAR) != CLEAN_CALENDAR_SHA:
        raise InventoryError("B19V4I_E_CLEAN_CALENDAR_HASH")
    dates = [line.strip()[:10] for line in CLEAN_CALENDAR.read_text(encoding="utf-8").splitlines() if line.strip()]
    clean_manifest = read_json(CLEAN_CALENDAR_MANIFEST)
    r1_review = read_json(B19R1_REVIEW)
    r2r_review = read_json(B19R2R_REVIEW)
    if (
        len(dates) != 2846
        or dates != sorted(set(dates))
        or dates[-1] != "2026-09-15"
        or "2026-07-10" in dates
        or clean_manifest.get("clean_calendar_sha256") != CLEAN_CALENDAR_SHA
        or clean_manifest.get("removed_provider_only_dates") != ["2026-07-10"]
        or r1_review.get("verdict") != "PASS_REPAIR_ONLY"
        or r2r_review.get("verdict") != "PASS_INPUTS_MATERIALIZED_NO_OUTCOMES"
    ):
        raise InventoryError("B19V4I_E_CLEAN_CALENDAR_CONTRACT")
    price = read_json(resolve_declared(read_json(PRICE_ADAPTER)["normalized_files"][0]["path"]))
    price_dates = {str(row.get("trade_date") or "")[:10] for row in price.get("records", [])}
    with MODEL_A_PREDICTION.open(encoding="utf-8", newline="") as stream:
        model_a_dates = {str(row.get("datetime") or "")[:10] for row in csv.DictReader(stream)}
    if ASOF not in price_dates or model_a_dates != {ASOF}:
        raise InventoryError("B19V4I_E_CALENDAR_EXTENSION_EVIDENCE")
    extended = [*dates, ASOF]
    return extended, {
        "base_calendar": artifact(CLEAN_CALENDAR),
        "base_calendar_manifest": artifact(CLEAN_CALENDAR_MANIFEST),
        "b19r1_independent_review": artifact(B19R1_REVIEW),
        "b19r2r_postmaterialization_review": artifact(B19R2R_REVIEW),
        "base_row_count": len(dates),
        "base_last_date": dates[-1],
        "appended_dates": [ASOF],
        "removed_nontrading_placeholders": ["2026-07-10"],
        "target_finmind_price_present": True,
        "target_model_a_prediction_present": True,
        "extended_row_count": len(extended),
    }
def validate_children(children: list[dict[str, Any]], decision_cutoff: str) -> None:
    roles = [str(child.get("role") or "") for child in children]
    if tuple(roles) != REQUIRED_ROLES or len(set(roles)) != len(roles):
        raise InventoryError("B19V4I_E_CHILD_ROLES", repr(roles))
    physical = [str(child.get("physical_run_id") or "") for child in children]
    if any(not item for item in physical):
        raise InventoryError("B19V4I_E_PHYSICAL_RUN_ID")
    cutoff = parse_time(decision_cutoff)
    if cutoff >= parse_time(NEXT_OPEN):
        raise InventoryError("B19V4I_E_CUTOFF_AFTER_NEXT_OPEN")
    for child in children:
        if child.get("asof") != ASOF or child.get("trade_date") != ASOF:
            raise InventoryError("B19V4I_E_CHILD_ASOF", str(child.get("role")))
        if parse_time(child.get("available_at")) > cutoff:
            raise InventoryError("B19V4I_E_CHILD_AFTER_CUTOFF", str(child.get("role")))
        if child.get("role") == "model_a_inference":
            validate_model_a_lineage(child)


def physical_run_ids(children: list[dict[str, Any]]) -> list[str]:
    values: list[str] = []
    for child in children:
        values.append(str(child["physical_run_id"]))
        values.extend(str(item) for item in child.get("supporting_physical_run_ids", []))
    return list(dict.fromkeys(values))


def build(output: Path, decision_cutoff: str) -> dict[str, Any]:
    output = output.resolve()
    if output.parent != OUT_ROOT.resolve():
        raise InventoryError("B19V4I_E_OUTPUT", str(output))
    if output.exists():
        raise InventoryError("B19V4I_E_NO_OVERWRITE", str(output))
    before = fingerprints()
    children = [
        finmind_child("daily_price", PRICE_ADAPTER),
        finmind_child("institutional", INSTITUTIONAL_ADAPTER),
        finmind_child("margin", MARGIN_ADAPTER),
        model_a_child(),
        yahoo_child(),
    ]
    validate_children(children, decision_cutoff)
    max_available = max((parse_time(item["available_at"]) for item in children)).isoformat(timespec="microseconds")
    output.mkdir(parents=True, mode=0o700)
    calendar, calendar_lineage = extended_calendar()
    calendar_path = output / "EXTENDED_CLEAN_CALENDAR.txt"
    calendar_path.write_text("\n".join(calendar) + "\n", encoding="ascii")
    calendar_binding = {
        **calendar_lineage,
        "extended_calendar": artifact(calendar_path),
        "extension_semantics": "append_only_exact_target_date_after_reviewed_clean_calendar",
    }
    inventory_path = output / "CHILD_INVENTORY.json"
    inventory = {
        "schema_version": "modelb_b19r2r.logical_child_inventory.v2",
        "asof": ASOF,
        "required_child_roles": list(REQUIRED_ROLES),
        "child_count": len(children),
        "max_child_available_at": max_available,
        "calendar_binding": calendar_binding,
        "children": children,
        "future_or_outcome_fields": [],
    }
    write_json(inventory_path, inventory)
    inventory_sha = sha256(inventory_path)
    logical_id = f"research.logical_composite.{ASOF.replace('-', '')}.{inventory_sha[:20]}"
    physical_ids = physical_run_ids(children)
    if logical_id in physical_ids:
        raise InventoryError("B19V4I_E_LOGICAL_EQUALS_PHYSICAL")
    frozen_at = datetime.now(UTC).isoformat(timespec="microseconds")
    after = fingerprints()
    if before != after:
        raise InventoryError("B19V4I_E_PROTECTED_DRIFT")
    manifest = {
        "schema_version": "modelb_b19r2r.logical_composite_source_run.v2",
        "source_run_kind": "logical_composite",
        "logical_source_run_id": logical_id,
        "asof": ASOF,
        "decision_cutoff": decision_cutoff,
        "created_at": frozen_at,
        "frozen_at": frozen_at,
        "next_session_open_at": NEXT_OPEN,
        "required_child_roles": list(REQUIRED_ROLES),
        "physical_run_ids": physical_ids,
        "child_inventory": artifact(inventory_path),
        "child_inventory_sha256": inventory_sha,
        "calendar_binding": calendar_binding,
        "max_child_available_at": max_available,
        "pit_status": "PASS",
        "validator_status": "PENDING_INDEPENDENT_REVIEW",
        "capture_authorized": False,
        "accepted_ledger_event_written": False,
        "no_publish": True,
        "no_latest_write": True,
        "production_allowed": False,
        "protected_before": before,
        "protected_after": after,
        "protected_unchanged": True,
    }
    manifest_path = output / "COMPOSITE_SOURCE_RUN_MANIFEST.json"
    write_json(manifest_path, manifest)
    for path in output.iterdir():
        os.chmod(path, 0o444)
    os.chmod(output, 0o555)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT_ROOT / "logical_composite_v2")
    parser.add_argument("--decision-cutoff", required=True)
    args = parser.parse_args()
    try:
        result = build(args.output, args.decision_cutoff)
    except InventoryError as exc:
        print(json.dumps({"status": "FAIL", "error_code": exc.code, "detail": exc.detail}, sort_keys=True))
        return 2
    print(json.dumps({"status": "PASS", "logical_source_run_id": result["logical_source_run_id"], "inventory_sha256": result["child_inventory_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
