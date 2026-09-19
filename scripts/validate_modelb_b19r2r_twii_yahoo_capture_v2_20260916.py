#!/usr/bin/env python3
"""Strictly validate the immutable B19R2R Yahoo dual-interval TWII acquisition."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import os
import statistics
import sys
from datetime import UTC, timedelta
from email.utils import parsedate_to_datetime
from itertools import pairwise
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_v3_manual_source_20260916"
SOURCE = BASE / "twii_acquisition_v5_yahoo_scrapling"
OUTPUT = BASE / "twii_acquisition_v5_validation_v2"
HANDOFF_OUTPUT = BASE / "TWII_V5_VALIDATION_V2.json"
SUPERSEDED_VALIDATION = BASE / "twii_acquisition_v5_validation/VALIDATION.json"
VALIDATOR_SCRIPT = Path(__file__).resolve()
CAPTURE_SCRIPT = ROOT / "scripts/capture_modelb_b19r2r_twii_yahoo_20260916.py"
TEST_FILE = ROOT / "tests/isolated/test_modelb_b19r2r_twii_yahoo_capture_20260916.py"
MATERIALIZER = ROOT / "scripts/materialize_modelb_b19r2r_v3_bundle_20260916.py"
MATERIALIZER_SHA = "06f9a4d6bfca4ccee6c3acc3af25dc5a36e0c6aaed463549a0cbbc2d27ce52a3"
CALENDAR_SOURCE = ROOT / "data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260916_20260916T103002Z/same_run_handoff_artifacts/daily_price/daily_price.normalized.json"
CALENDAR_SOURCE_SHA = "78891f7ccd2a0ce8e05407c8ff7fb07d09238f178d067f2c8f01c010f4fc3088"
LAST120_CALENDAR_SHA = "84745b4cb83e8c85b84a5ff8856858c65d227748254dbc4aa8e62b29e12d4d24"
FEATURE_NAMES = (
    "TWII_ret20",
    "TWII_ret60",
    "TWII_close_vs_MA60",
    "TWII_close_vs_MA120",
    "market_volatility20",
    "market_drawdown60",
)


def load_capture_module():
    name = "capture_modelb_b19r2r_twii_yahoo_20260916_for_validation_v2"
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


def sequence_sha(values: list[str]) -> str:
    return hashlib.sha256(json.dumps(values, separators=(",", ":")).encode("utf-8")).hexdigest()


def calculate_six_features(rows: list[dict[str, Any]]) -> dict[str, float]:
    ordered = sorted(rows, key=lambda row: str(row["date"]))
    closes = [float(row["close"]) for row in ordered]
    if len(closes) < 121 or any(not math.isfinite(value) or value <= 0 for value in closes):
        raise ValidationError("at least 121 finite positive closes required")
    returns = [right / left - 1.0 for left, right in pairwise(closes)]
    values = {
        "TWII_ret20": closes[-1] / closes[-21] - 1.0,
        "TWII_ret60": closes[-1] / closes[-61] - 1.0,
        "TWII_close_vs_MA60": closes[-1] / statistics.fmean(closes[-60:]) - 1.0,
        "TWII_close_vs_MA120": closes[-1] / statistics.fmean(closes[-120:]) - 1.0,
        "market_volatility20": statistics.stdev(returns[-20:]),
        "market_drawdown60": closes[-1] / max(closes[-60:]) - 1.0,
    }
    if set(values) != set(FEATURE_NAMES) or any(not math.isfinite(value) for value in values.values()):
        raise ValidationError("six TWII features are not all finite")
    return values


def six_feature_score_gate(features: dict[str, Any], *, independent_review_passed: bool) -> dict[str, Any]:
    finite = set(features) == set(FEATURE_NAMES)
    if finite:
        try:
            finite = all(math.isfinite(float(features[name])) for name in FEATURE_NAMES)
        except (TypeError, ValueError):
            finite = False
    return {
        "six_features_present_and_finite": finite,
        "independent_review_passed": independent_review_passed,
        "scoring_authorized": bool(finite and independent_review_passed),
        "reason": "ready_only_after_independent_review" if finite else "blocked_nonfinite_or_missing_twii_feature",
    }


def header_evidence(headers: dict[str, Any], request_started: str, fetched_at: str) -> dict[str, Any]:
    server_time = parsedate_to_datetime(str(headers["date"])).astimezone(UTC)
    started = capture.parse_time(request_started)
    fetched = capture.parse_time(fetched_at)
    return {
        "date": headers["date"],
        "date_utc": server_time.isoformat(timespec="seconds"),
        "age": headers.get("age"),
        "cache_control": headers.get("cache-control"),
        "content_type": headers.get("content-type"),
        "server_time_within_request": started - timedelta(seconds=1) <= server_time <= fetched + timedelta(seconds=1),
        "age_is_zero": str(headers.get("age")) == "0",
        "cache_policy_recorded": bool(headers.get("cache-control")),
    }


def validate(source: Path = SOURCE, output: Path = OUTPUT) -> dict[str, Any]:
    if output.exists():
        raise ValidationError(f"write-once output exists: {output}")
    if HANDOFF_OUTPUT.exists():
        raise ValidationError(f"write-once handoff output exists: {HANDOFF_OUTPUT}")
    paths = {
        "manifest": source / "TWII_CAPTURE_MANIFEST.json",
        "daily_raw": source / "twii_daily_raw.json",
        "intraday_raw": source / "twii_intraday_1m_raw.json",
        "normalized": source / "TWII_NORMALIZED.csv",
        "daily_headers": source / "RESPONSE_HEADERS_DAILY.json",
        "intraday_headers": source / "RESPONSE_HEADERS_INTRADAY.json",
        "daily_request": source / "REQUEST_DAILY.json",
        "intraday_request": source / "REQUEST_INTRADAY.json",
    }
    manifest = read_json(paths["manifest"])
    daily_payload = read_json(paths["daily_raw"])
    intraday_payload = read_json(paths["intraday_raw"])
    daily_headers = read_json(paths["daily_headers"])
    intraday_headers = read_json(paths["intraday_headers"])
    daily_request = read_json(paths["daily_request"])
    intraday_request = read_json(paths["intraday_request"])
    source_before = capture.fingerprint_path(source)
    checks: dict[str, bool] = {}

    checks["capture_candidate_status"] = manifest.get("status") == "PASS_REVIEWABLE_CANDIDATE"
    checks["awaiting_independent_review"] = manifest.get("validator_status") == "PASS_CANDIDATE_AWAITING_INDEPENDENT_REVIEW"
    checks["provider_is_yahoo_not_official"] = manifest.get("provider") == "Yahoo Finance" and manifest.get("official_source") is False
    checks["available_at_before_next_open"] = capture.parse_time(manifest["available_at"]) < capture.parse_time(capture.NEXT_OPEN_UTC)
    checks["protected_unchanged_at_capture"] = manifest.get("protected_unchanged") is True and manifest.get("protected_before") == manifest.get("protected_after")
    for role, item in manifest["artifacts"].items():
        artifact_path = ROOT / item["path"]
        checks[f"artifact_sha_{role}"] = artifact_path.is_file() and capture.sha256(artifact_path) == item["sha256"]
    checks["raw_sha_fields"] = (
        manifest["raw_sha256"]["daily"] == capture.sha256(paths["daily_raw"])
        and manifest["raw_sha256"]["intraday"] == capture.sha256(paths["intraday_raw"])
        and manifest["normalized_sha256"] == capture.sha256(paths["normalized"])
    )

    daily_rows, daily_coverage = capture.yahoo_payload_to_rows(daily_payload, require_target=False)
    target_row, intraday_coverage = capture.yahoo_intraday_to_target_row(intraday_payload)
    stub = capture.validate_daily_target_stub(daily_payload, target_row)
    checks["daily_target_stub_unique_and_rejected"] = (
        stub["target_timestamp_count"] == 1
        and stub["daily_stub_close"] is None
        and stub["daily_stub_adjclose"] is None
        and daily_coverage["target_row_count"] == 0
    )
    checks["daily_stub_ohl_matches_1m"] = max(stub["daily_vs_intraday_ohl_absolute_differences"].values()) <= 1e-9
    checks["daily_identity_and_array_lengths"] = (
        daily_coverage["symbol"] == capture.TICKER
        and daily_coverage["exchange_name"] == "TAI"
        and daily_coverage["exchange_timezone_name"] == "Asia/Taipei"
        and daily_coverage["gmtoffset"] == 28800
        and daily_coverage["data_granularity"] == "1d"
        and set(daily_coverage["array_lengths"].values()) == {daily_coverage["input_timestamp_count"]}
    )
    checks["intraday_exact_271_minute_session"] = (
        intraday_coverage["point_count"] == 271
        and intraday_coverage["adjacent_delta_seconds"] == 60
        and intraday_coverage["all_taipei_dates_equal_target"] is True
        and intraday_coverage["first_timestamp_utc"] == "2026-09-16T01:00:00.000000+00:00"
        and intraday_coverage["last_timestamp_utc"] == "2026-09-16T05:30:00.000000+00:00"
        and intraday_coverage["gmtoffset"] == 28800
        and intraday_coverage["data_granularity"] == "1m"
        and set(intraday_coverage["array_lengths"].values()) == {271}
    )
    checks["strict_rounded_meta_close_tolerance"] = (
        intraday_coverage["rounded_close_meta_absolute_difference"] <= 0.01
        and intraday_coverage["meta_close_tolerance"] == 0.01
    )

    with paths["normalized"].open(encoding="utf-8", newline="") as stream:
        normalized = list(csv.DictReader(stream))
    normalized_dates = [row["date"] for row in normalized]
    target_rows = [row for row in normalized if row["date"] == capture.TARGET]
    checks["normalized_no_duplicate_or_future"] = (
        len(normalized_dates) == len(set(normalized_dates))
        and normalized_dates == sorted(normalized_dates)
        and max(normalized_dates) == capture.TARGET
    )
    checks["normalized_target_binds_intraday"] = len(target_rows) == 1 and all(
        abs(float(target_rows[0][field]) - float(target_row[field])) <= 1e-9 for field in ("open", "high", "low", "close")
    )

    checks["calendar_source_sha_frozen"] = capture.sha256(CALENDAR_SOURCE) == CALENDAR_SOURCE_SHA
    calendar_payload = read_json(CALENDAR_SOURCE)
    calendar_dates = sorted(
        {
            str(row["trade_date"])
            for row in calendar_payload.get("records", [])
            if row.get("trade_date") and str(row["trade_date"]) <= capture.TARGET
        }
    )
    calendar_last120 = calendar_dates[-120:]
    normalized_last120 = normalized_dates[-120:]
    checks["calendar_last120_hash_frozen"] = sequence_sha(calendar_last120) == LAST120_CALENDAR_SHA
    checks["calendar_last120_exact_parity"] = (
        len(calendar_last120) == 120
        and normalized_last120 == calendar_last120
        and sequence_sha(normalized_last120) == LAST120_CALENDAR_SHA
    )
    last120_rows = {row["date"]: row for row in normalized if row["date"] in set(normalized_last120)}
    last120_factors = [float(last120_rows[day]["factor"]) for day in normalized_last120]
    checks["last120_factors_finite_and_one"] = all(math.isfinite(value) and value == 1.0 for value in last120_factors)
    calendar_counts: dict[str, int] = {}
    for row in calendar_payload.get("records", []):
        day = str(row.get("trade_date") or "")
        if day:
            calendar_counts[day] = calendar_counts.get(day, 0) + 1
    checks["same_run_calendar_cross_section_complete"] = (
        len(calendar_counts) == 173 and set(calendar_counts.values()) == {150} and "2026-07-10" not in calendar_counts
    )

    checks["materializer_sha_frozen"] = capture.sha256(MATERIALIZER) == MATERIALIZER_SHA
    materializer_text = MATERIALIZER.read_text(encoding="utf-8")
    checks["feature_consumer_date_close_only"] = (
        'pd.read_csv(TWII_HISTORY, usecols=["date", "close"])' in materializer_text
        and 'pd.read_csv(TWII_RECENT, usecols=["date", "close"])' in materializer_text
    )
    checks["target_volume_is_minute_sum_not_consumed"] = (
        len(target_rows) == 1
        and int(float(target_rows[0]["volume"])) == int(intraday_coverage["aggregated_volume"])
    )
    expected_vwap = sum(float(target_row[field]) for field in ("open", "high", "low", "close")) / 4.0
    checks["target_vwap_is_derived_not_consumed"] = len(target_rows) == 1 and abs(float(target_rows[0]["vwap"]) - expected_vwap) <= 1e-9

    request_ids = {
        "daily": manifest["acquisition_run_id"] + ".subrequest.daily.1d",
        "intraday": manifest["acquisition_run_id"] + ".subrequest.target.1m",
    }
    checks["subrequest_ids_unique"] = len(set(request_ids.values())) == 2
    checks["subrequest_timeline_ordered"] = (
        capture.parse_time(daily_request["started_at"])
        <= capture.parse_time(manifest["daily_fetched_at"])
        <= capture.parse_time(intraday_request["started_at"])
        <= capture.parse_time(manifest["intraday_fetched_at"])
        <= capture.parse_time(manifest["completed_at"])
        and manifest["available_at"] == manifest["intraday_fetched_at"]
    )
    daily_header_evidence = header_evidence(daily_headers, daily_request["started_at"], manifest["daily_fetched_at"])
    intraday_header_evidence = header_evidence(intraday_headers, intraday_request["started_at"], manifest["intraday_fetched_at"])
    checks["response_header_availability_evidence"] = all(
        evidence["server_time_within_request"] and evidence["age_is_zero"] and evidence["cache_policy_recorded"]
        for evidence in (daily_header_evidence, intraday_header_evidence)
    )

    six_features = calculate_six_features(normalized)
    feature_gate = six_feature_score_gate(six_features, independent_review_passed=False)
    checks["six_twii_features_independently_recomputed_finite"] = feature_gate["six_features_present_and_finite"] is True
    checks["scoring_remains_blocked_pending_review"] = feature_gate["scoring_authorized"] is False and manifest.get("scoring_performed") is False
    checks["no_upper_layer_action"] = (
        manifest.get("upper_layer_materialization_authorized") is False
        and manifest.get("capture_or_ledger_append_performed") is False
        and manifest.get("training_performed") is False
        and manifest.get("no_publish") is True
        and manifest.get("no_latest_write") is True
    )
    checks["source_directory_readonly"] = source.stat().st_mode & 0o777 == 0o555
    checks["source_files_readonly"] = all(path.stat().st_mode & 0o777 == 0o444 for path in source.iterdir() if path.is_file())
    source_after = capture.fingerprint_path(source)
    checks["source_unchanged_during_validation"] = source_before == source_after
    status = "PASS" if all(checks.values()) else "FAIL"
    report = {
        "schema_version": "modelb_b19r2r.yahoo_twii_dual_interval_validation.v2",
        "status": status,
        "source_acquisition_run_id": manifest.get("acquisition_run_id"),
        "source_manifest": capture.rel(paths["manifest"]),
        "source_manifest_sha256": capture.sha256(paths["manifest"]),
        "implementation": {
            "capture_script": capture.rel(CAPTURE_SCRIPT),
            "capture_script_sha256": capture.sha256(CAPTURE_SCRIPT),
            "validator_script": capture.rel(VALIDATOR_SCRIPT),
            "validator_script_sha256": capture.sha256(VALIDATOR_SCRIPT),
            "test_file": capture.rel(TEST_FILE),
            "test_file_sha256": capture.sha256(TEST_FILE),
        },
        "validated_artifacts": manifest["artifacts"],
        "supersedes": {
            "path": capture.rel(SUPERSEDED_VALIDATION),
            "sha256": capture.sha256(SUPERSEDED_VALIDATION),
            "reason": "validator v1 predates strict reviewer requirements and capture implementation SHA changed",
        },
        "source_directory_fingerprint_before": source_before,
        "source_directory_fingerprint_after": source_after,
        "checks": checks,
        "daily_coverage": daily_coverage,
        "daily_target_stub_evidence": stub,
        "intraday_target_aggregation": intraday_coverage,
        "calendar_evidence": {
            "source": capture.rel(CALENDAR_SOURCE),
            "source_sha256": CALENDAR_SOURCE_SHA,
            "unique_date_count": len(calendar_dates),
            "date_min": calendar_dates[0],
            "date_max": calendar_dates[-1],
            "last120_date_min": calendar_last120[0],
            "last120_date_max": calendar_last120[-1],
            "last120_sequence_sha256": LAST120_CALENDAR_SHA,
            "missing_from_twii": sorted(set(calendar_last120) - set(normalized_last120)),
            "extra_in_twii": sorted(set(normalized_last120) - set(calendar_last120)),
            "calendar_authority_policy": "same-run FinMind observed market dates with complete 150-symbol cross-section",
            "same_run_rows_per_date_min": min(calendar_counts.values()),
            "same_run_rows_per_date_max": max(calendar_counts.values()),
            "same_run_2026_07_10_row_count": calendar_counts.get("2026-07-10", 0),
            "qlib_day_txt_not_used_as_actual_session_authority": True,
            "known_calendar_dispute": "generic qlib day.txt contains 2026-07-10, while same-run FinMind has zero rows for all 150 symbols; reviewer must adjudicate authority before upper-layer materialization",
        },
        "feature_consumer_contract": {
            "materializer": capture.rel(MATERIALIZER),
            "materializer_sha256": MATERIALIZER_SHA,
            "consumed_columns": ["date", "close"],
            "target_volume_semantics": "sum of Yahoo 1m provider volume; not consumed by six TWII features",
            "target_vwap_semantics": "derived OHLC4; not provider VWAP; not consumed by six TWII features",
        },
        "six_twii_features": six_features,
        "score_gate": feature_gate,
        "subrequest_ids": request_ids,
        "subrequest_timing": {
            "daily_started_at": daily_request["started_at"],
            "daily_fetched_at": manifest["daily_fetched_at"],
            "intraday_started_at": intraday_request["started_at"],
            "intraday_fetched_at": manifest["intraday_fetched_at"],
            "available_at": manifest["available_at"],
            "available_at_semantics": "max of first successful observation times for the two bound subrequests",
        },
        "response_header_evidence": {"daily": daily_header_evidence, "intraday": intraday_header_evidence},
        "same_run_contract_decision": "NOT_MADE",
        "upper_layer_materialization_authorized": False,
        "capture_or_ledger_append_authorized": False,
        "research_only": True,
    }
    output.mkdir(parents=True, mode=0o700)
    report_path = output / "VALIDATION_V2.json"
    serialized = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    report_path.write_text(serialized, encoding="utf-8")
    HANDOFF_OUTPUT.write_text(serialized, encoding="utf-8")
    os.chmod(report_path, 0o444)
    os.chmod(HANDOFF_OUTPUT, 0o444)
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
                "capture_script_sha256": report["implementation"]["capture_script_sha256"],
                "test_file_sha256": report["implementation"]["test_file_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
