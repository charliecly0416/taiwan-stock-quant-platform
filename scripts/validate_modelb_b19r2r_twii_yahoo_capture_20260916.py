#!/usr/bin/env python3
"""Validate the immutable B19R2R Yahoo dual-interval TWII acquisition."""
from __future__ import annotations

import csv
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_v3_manual_source_20260916/twii_acquisition_v5_yahoo_scrapling"
OUTPUT = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_v3_manual_source_20260916/twii_acquisition_v5_validation"
CAPTURE_SCRIPT = ROOT / "scripts/capture_modelb_b19r2r_twii_yahoo_20260916.py"


def load_capture_module():
    name = "capture_modelb_b19r2r_twii_yahoo_20260916_for_validation"
    spec = importlib.util.spec_from_file_location(name, CAPTURE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    if spec.loader is None:
        raise RuntimeError("validator cannot load capture implementation")
    spec.loader.exec_module(module)
    return module


capture = load_capture_module()


class ValidationError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValidationError(f"object required: {path}")
    return value


def validate(source: Path = SOURCE, output: Path = OUTPUT) -> dict[str, Any]:
    if output.exists():
        raise ValidationError(f"write-once output exists: {output}")
    manifest_path = source / "TWII_CAPTURE_MANIFEST.json"
    daily_raw_path = source / "twii_daily_raw.json"
    intraday_raw_path = source / "twii_intraday_1m_raw.json"
    normalized_path = source / "TWII_NORMALIZED.csv"
    manifest = read_json(manifest_path)
    daily_payload = read_json(daily_raw_path)
    intraday_payload = read_json(intraday_raw_path)
    source_before = capture.fingerprint_path(source)

    checks: dict[str, bool] = {}
    checks["capture_candidate_status"] = manifest.get("status") == "PASS_REVIEWABLE_CANDIDATE"
    checks["awaiting_independent_review"] = manifest.get("validator_status") == "PASS_CANDIDATE_AWAITING_INDEPENDENT_REVIEW"
    checks["provider_is_yahoo_not_official"] = manifest.get("provider") == "Yahoo Finance" and manifest.get("official_source") is False
    checks["available_at_before_next_open"] = capture.parse_time(manifest["available_at"]) < capture.parse_time(capture.NEXT_OPEN_UTC)
    checks["protected_unchanged_at_capture"] = (
        manifest.get("protected_unchanged") is True
        and manifest.get("protected_before") == manifest.get("protected_after")
    )
    checks["daily_raw_sha"] = manifest["raw_sha256"]["daily"] == capture.sha256(daily_raw_path)
    checks["intraday_raw_sha"] = manifest["raw_sha256"]["intraday"] == capture.sha256(intraday_raw_path)
    checks["normalized_sha"] = manifest["normalized_sha256"] == capture.sha256(normalized_path)

    daily_rows, daily_coverage = capture.yahoo_payload_to_rows(daily_payload, require_target=False)
    target_row, intraday_coverage = capture.yahoo_intraday_to_target_row(intraday_payload)
    stub = capture.validate_daily_target_stub(daily_payload, target_row)
    checks["daily_has_120_complete_history_rows"] = len(daily_rows) >= capture.MIN_ROWS
    checks["daily_target_stub_unique_and_incomplete"] = (
        stub["target_timestamp_count"] == 1
        and stub["daily_stub_close"] is None
        and stub["daily_stub_adjclose"] is None
    )
    checks["daily_stub_ohl_matches_1m_aggregate"] = max(stub["daily_vs_intraday_ohl_absolute_differences"].values()) <= stub["ohl_tolerance"]
    checks["all_complete_daily_factors_are_one"] = stub["complete_daily_factor_max_deviation_from_one"] <= stub["ohl_tolerance"]
    checks["intraday_exact_session"] = (
        intraday_coverage["point_count"] == 271
        and intraday_coverage["first_timestamp_utc"] == "2026-09-16T01:00:00.000000+00:00"
        and intraday_coverage["last_timestamp_utc"] == "2026-09-16T05:30:00.000000+00:00"
    )
    checks["intraday_meta_close_within_tolerance"] = (
        intraday_coverage["meta_close_absolute_difference"] <= intraday_coverage["meta_close_tolerance"]
    )

    with normalized_path.open(encoding="utf-8", newline="") as stream:
        normalized = list(csv.DictReader(stream))
    target_rows = [row for row in normalized if row["date"] == capture.TARGET]
    checks["normalized_coverage"] = len(normalized) >= capture.MIN_ROWS and len(target_rows) == 1
    if len(target_rows) == 1:
        normalized_target = target_rows[0]
        checks["normalized_target_binds_intraday"] = (
            normalized_target["source"] == capture.INTRADAY_SOURCE_VALUE
            and float(normalized_target["factor"]) == 1.0
            and all(abs(float(normalized_target[field]) - float(target_row[field])) <= 1e-9 for field in ("open", "high", "low", "close"))
        )
    else:
        checks["normalized_target_binds_intraday"] = False
    checks["source_directory_readonly"] = source.stat().st_mode & 0o777 == 0o555
    checks["source_files_readonly"] = all(path.stat().st_mode & 0o777 == 0o444 for path in source.iterdir() if path.is_file())
    checks["no_upper_layer_action"] = (
        manifest.get("upper_layer_materialization_authorized") is False
        and manifest.get("capture_or_ledger_append_performed") is False
        and manifest.get("training_performed") is False
        and manifest.get("scoring_performed") is False
        and manifest.get("no_publish") is True
        and manifest.get("no_latest_write") is True
    )
    source_after = capture.fingerprint_path(source)
    checks["source_unchanged_during_validation"] = source_before == source_after
    status = "PASS" if all(checks.values()) else "FAIL"
    report = {
        "schema_version": "modelb_b19r2r.yahoo_twii_dual_interval_validation.v1",
        "status": status,
        "source_acquisition_run_id": manifest.get("acquisition_run_id"),
        "source_manifest": capture.rel(manifest_path),
        "source_manifest_sha256": capture.sha256(manifest_path),
        "capture_script": capture.rel(CAPTURE_SCRIPT),
        "capture_script_sha256": capture.sha256(CAPTURE_SCRIPT),
        "source_directory_fingerprint_before": source_before,
        "source_directory_fingerprint_after": source_after,
        "checks": checks,
        "daily_coverage": daily_coverage,
        "daily_target_stub_evidence": stub,
        "intraday_target_aggregation": intraday_coverage,
        "normalized_target_row": target_rows[0] if len(target_rows) == 1 else None,
        "same_run_contract_decision": "NOT_MADE",
        "upper_layer_materialization_authorized": False,
        "capture_or_ledger_append_authorized": False,
        "research_only": True,
    }
    output.mkdir(parents=True, mode=0o700)
    report_path = output / "VALIDATION.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")
    os.chmod(report_path, 0o444)
    os.chmod(output, 0o555)
    if status != "PASS":
        failed = [name for name, passed in checks.items() if not passed]
        raise ValidationError("failed checks: " + ",".join(failed))
    return report


def main() -> int:
    try:
        report = validate()
    except (ValidationError, capture.CaptureError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, sort_keys=True))
        return 2
    print(
        json.dumps(
            {
                "status": report["status"],
                "source_acquisition_run_id": report["source_acquisition_run_id"],
                "checks": len(report["checks"]),
                "source_manifest_sha256": report["source_manifest_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
