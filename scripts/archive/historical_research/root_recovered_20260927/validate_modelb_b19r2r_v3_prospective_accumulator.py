#!/usr/bin/env python3
"""Validate the isolated B19R2R V3 prospective accumulator and readiness audit."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import build_modelb_b19r2r_v3_prospective_accumulator as builder


def fail(code: str, detail: str = "") -> None:
    raise builder.ContractError(code, detail)


def validate_accumulator(path: Path) -> dict[str, Any]:
    builder.validate_out(path)
    events = builder.load_events(path / "events.jsonl")
    seen: set[tuple[str, str]] = set()
    captured: set[str] = set()
    settled: set[str] = set()
    matured: set[str] = set()
    allowed = {"SIGNAL_CAPTURED", "EXECUTION_SETTLED", "LABEL_MATURED"}
    for event in events:
        event_type = str(event.get("event_type"))
        asof = str(event.get("asof"))
        key = (event_type, asof)
        if event_type not in allowed or key in seen:
            fail("B19V3V_E_EVENT", repr(key))
        seen.add(key)
        if event.get("production_allowed") is not False:
            fail("B19V3V_E_PRODUCTION_BOUNDARY", repr(key))
        if event_type == "SIGNAL_CAPTURED":
            if builder.forbidden_paths(event):
                # The explicit false assertion is part of the signal contract, not outcome data.
                paths = [item for item in builder.forbidden_paths(event) if item != "contains_future_label"]
                if paths:
                    fail("B19V3V_E_FUTURE_FIELD", ",".join(paths))
            if (
                event.get("model_id") != builder.MODEL_ID
                or event.get("model_a_id") != builder.MODEL_A_ID
                or event.get("model_sha256") != builder.MODEL_SHA256
                or event.get("candidate_id") != builder.CANDIDATE_ID
                or event.get("feature_count") != builder.FEATURE_COUNT
                or len(event.get("exact50_symbols", [])) != builder.EXACT_COUNT
                or builder.EXCLUDED_SYMBOL in event.get("exact50_symbols", [])
                or event.get("tw7769_excluded") is not True
            ):
                fail("B19V3V_E_SIGNAL_CONTRACT", asof)
            if builder.parse_time(event.get("decision_cutoff"), "B19V3V_E_CUTOFF") < builder.parse_time(
                builder.FINAL_MODEL_FROZEN_AT, "B19V3V_E_MODEL_FREEZE"
            ):
                fail("B19V3V_E_MODEL_FREEZE", asof)
            captured.add(asof)
        else:
            if asof not in captured:
                fail("B19V3V_E_EVENT_ORDER", repr(key))
            sealed_path = builder.resolve(str(event.get("sealed_payload") or ""))
            if not sealed_path.resolve().is_relative_to((path / "sealed_outcomes").resolve()):
                fail("B19V3V_E_SEALED_ESCAPE", str(sealed_path))
            if not sealed_path.is_file() or builder.canonical_hash(builder.read_json(sealed_path)) != event.get("sealed_payload_sha256"):
                fail("B19V3V_E_SEALED_HASH", str(sealed_path))
            if os.stat(sealed_path).st_mode & 0o077:
                fail("B19V3V_E_SEALED_MODE", oct(os.stat(sealed_path).st_mode & 0o777))
            if event_type == "EXECUTION_SETTLED":
                settled.add(asof)
            else:
                if asof not in settled:
                    fail("B19V3V_E_EVENT_ORDER", repr(key))
                matured.add(asof)
    sealed_root = path / "sealed_outcomes"
    if sealed_root.exists() and os.stat(sealed_root).st_mode & 0o077:
        fail("B19V3V_E_SEALED_ROOT_MODE", oct(os.stat(sealed_root).st_mode & 0o777))
    summary = builder.read_json(path / "summary.json")
    calendar_paths, dates = builder.signal_calendars(events, path)
    if any(os.stat(calendar).st_mode & 0o777 != 0o444 for calendar in calendar_paths):
        fail("B19V3V_E_CALENDAR_SNAPSHOT_MODE")
    streak = builder.longest_consecutive_capture_streak(captured, dates)
    if (
        summary.get("captured_days") != sorted(captured)
        or summary.get("execution_settled_days") != sorted(settled)
        or summary.get("label_matured_days") != sorted(matured)
        or summary.get("mainline_minimum_settled_days") != 10
        or summary.get("mainline_settled_day_count") != len(settled)
        or summary.get("mainline_gate_ready") is not (len(settled) >= 10)
        or summary.get("v3_replacement_window_days") != 30
        or summary.get("v3_captured_day_count") != len(captured)
        or summary.get("v3_longest_consecutive_capture_days") != streak
        or summary.get("v3_window_ready") is not (streak >= 30)
        or summary.get("trading_calendar_snapshots") != [builder.relative(item) for item in calendar_paths]
        or summary.get("trading_calendar_snapshot_sha256") != [builder.sha256(item) for item in calendar_paths]
        or summary.get("production_allowed") is not False
    ):
        fail("B19V3V_E_SUMMARY")
    return {"status": "PASS", "event_count": len(events), "captured": len(captured), "settled": len(settled), "matured": len(matured)}


def validate_readiness(path: Path) -> dict[str, Any]:
    audit = builder.read_json(path / "READINESS_AUDIT.json")
    rows = builder.read_csv(path / "READINESS_BY_DAY.csv")
    contract = builder.read_json(path / "EXPECTED_INPUT_BUNDLE_CONTRACT.json")
    if audit.get("actual_trading_day_count") != len(rows):
        fail("B19V3V_E_AUDIT_COUNT")
    eligible = sum(row.get("status") == "ELIGIBLE" for row in rows)
    if audit.get("eligible_capture_day_count") != eligible:
        fail("B19V3V_E_AUDIT_ELIGIBLE")
    if any(row.get("status") not in {"ELIGIBLE", "NOT_ELIGIBLE"} for row in rows):
        fail("B19V3V_E_AUDIT_STATUS")
    for row in rows:
        strict_count = int(row.get("strict_bundle_count") or -1)
        strict_pit = str(row.get("strict_pit_binding_proven", "")).lower() == "true"
        strict_after_freeze = str(row.get("strict_bundle_after_model_freeze", "")).lower() == "true"
        strict_cutoff = str(row.get("strict_bundle_cutoff") or "")
        semantic_eligible = (
            strict_count == 1
            and strict_pit
            and strict_after_freeze
            and bool(strict_cutoff)
            and builder.parse_time(strict_cutoff, "B19V3V_E_CUTOFF") >= builder.parse_time(
                builder.FINAL_MODEL_FROZEN_AT, "B19V3V_E_MODEL_FREEZE"
            )
            and str(row.get("asof")) >= builder.FINAL_MODEL_FROZEN_AT[:10]
            and row.get("model_a_evidence_present") == "True"
            and row.get("canonical_78f_bound") == "True"
            and row.get("candidate14_score_bound") == "True"
            and not row.get("reasons")
            and row.get("readiness_class") == "ELIGIBLE"
        )
        if (row.get("status") == "ELIGIBLE") != semantic_eligible:
            fail("B19V3V_E_AUDIT_ELIGIBILITY_SEMANTICS", str(row.get("asof")))
    allowed_classes = {"ELIGIBLE", "BEFORE_FINAL_MODEL_FREEZE", "MATERIALIZATION_GAP", "SOURCE_OR_LINEAGE_NOT_READY"}
    if any(row.get("readiness_class") not in allowed_classes for row in rows):
        fail("B19V3V_E_AUDIT_CLASS")
    expected_counts = {name: sum(row.get("readiness_class") == name for row in rows) for name in allowed_classes}
    if audit.get("readiness_class_counts") != expected_counts:
        fail("B19V3V_E_AUDIT_CLASS_COUNT")
    if audit.get("mainline_gate", {}).get("required_real_prospective_settled_days") != 10:
        fail("B19V3V_E_MAINLINE_GATE")
    if audit.get("v3_replacement_confirmation", {}).get("required_consecutive_capture_days") != 30:
        fail("B19V3V_E_V3_GATE")
    compatibility = audit.get("b8_compatibility", {})
    if compatibility.get("compatible_with_b19r2r_v3") is not False or compatibility.get("counted_in_v3_window") is not False:
        fail("B19V3V_E_B8_COMPATIBILITY")
    if audit.get("not_eligible_rows_are_not_ledger_events") is not True or audit.get("production_allowed") is not False:
        fail("B19V3V_E_AUDIT_BOUNDARY")
    if (
        contract.get("model_id") != builder.MODEL_ID
        or contract.get("model_a_id") != builder.MODEL_A_ID
        or contract.get("model_sha256") != builder.MODEL_SHA256
        or contract.get("candidate_id") != builder.CANDIDATE_ID
        or contract.get("required_feature_count") != builder.FEATURE_COUNT
        or contract.get("excluded_symbol") != builder.EXCLUDED_SYMBOL
        or contract.get("production_allowed") is not False
    ):
        fail("B19V3V_E_INPUT_CONTRACT")
    return {"status": "PASS", "row_count": len(rows), "eligible": eligible, "not_eligible": len(rows) - eligible}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--accumulator")
    result.add_argument("--readiness")
    return result


def main() -> int:
    args = parser().parse_args()
    if not args.accumulator and not args.readiness:
        print(json.dumps({"status": "FAIL", "error_code": "B19V3V_E_INPUT_REQUIRED"}, sort_keys=True))
        return 2
    try:
        result: dict[str, Any] = {"status": "PASS"}
        if args.accumulator:
            result["accumulator"] = validate_accumulator(builder.resolve(args.accumulator))
        if args.readiness:
            result["readiness"] = validate_readiness(builder.resolve(args.readiness))
    except builder.ContractError as exc:
        print(json.dumps({"status": "FAIL", "error_code": exc.code, "detail": exc.detail}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
