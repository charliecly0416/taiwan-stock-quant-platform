#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

PRICE_REQUIRED_FILES = [
    "manifest.json",
    "prices.csv",
    "schema.json",
    "coverage_audit.csv",
    "adjustment_audit.json",
    "execution_availability_audit.csv",
    "halt_suspension_audit.json",
    "lineage.json",
]

TWII_REQUIRED_FILES = [
    "manifest.json",
    "twii.csv",
    "schema.json",
    "coverage_audit.csv",
    "lineage.json",
]

PRICE_REQUIRED_FIELDS = [
    "price_date",
    "instrument",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "adj_factor",
    "tradable_flag",
    "halt_flag",
    "halt_flag_source",
    "next_day_execution_availability",
    "next_day_execution_status",
    "price_source",
    "adjustment_policy",
]

TWII_REQUIRED_FIELDS = [
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "return_1d",
    "ma_5",
    "ma_20",
    "ma_60",
    "market_trend_state",
    "source",
]

FORBIDDEN_FIELDS = [
    "strategy_action",
    "target_position",
    "target_weight",
    "order_qty",
    "broker_order_id",
    "portfolio_equity",
]

FORBIDDEN_PREFIXES = [
    "future_return_",
    "forward_return_",
    "label_",
]

FORBIDDEN_ACTION_KEYS = [
    "real_data_fetch_triggered",
    "provider_refresh_triggered",
    "provider_publish_triggered",
    "qlib_accepted_latest_switched",
    "readonly_latest_published",
    "agent_prompt_published",
    "model_training_triggered",
    "model_inference_triggered",
    "strategy_replay_triggered",
    "broker_order_quick_trade_triggered",
    "target_position_or_weight_generated",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def csv_header_and_count(path: Path) -> tuple[list[str], int]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return [], 0
        return header, sum(1 for _ in reader)


def forbidden_columns(header: list[str]) -> list[str]:
    bad = [field for field in header if field in FORBIDDEN_FIELDS]
    bad.extend(field for field in header if any(field.startswith(prefix) for prefix in FORBIDDEN_PREFIXES))
    return sorted(set(bad))


def validate_required_files(base: Path, required: list[str], errors: list[str]) -> dict[str, str]:
    paths: dict[str, str] = {}
    for name in required:
        path = base / name
        paths[name] = rel(path)
        if not path.exists():
            errors.append(f"missing required file: {rel(path)}")
    return paths


def validate_schema(schema_path: Path, expected_artifact_type: str, required_fields: list[str], errors: list[str]) -> None:
    if not schema_path.exists():
        return
    schema = read_json(schema_path)
    if schema.get("artifact_type") != expected_artifact_type:
        errors.append(f"{rel(schema_path)} artifact_type={schema.get('artifact_type')} expected={expected_artifact_type}")
    schema_required = schema.get("required_fields", [])
    missing = [field for field in required_fields if field not in schema_required]
    if missing:
        errors.append(f"{rel(schema_path)} missing required_fields: {missing}")


def validate_manifest(
    manifest_path: Path,
    expected_artifact_type: str,
    run_id: str,
    errors: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    if not manifest_path.exists():
        return {}
    manifest = read_json(manifest_path)
    if manifest.get("artifact_type") != expected_artifact_type:
        errors.append(f"{rel(manifest_path)} artifact_type={manifest.get('artifact_type')} expected={expected_artifact_type}")
    if manifest.get("run_id") != run_id:
        errors.append(f"{rel(manifest_path)} run_id={manifest.get('run_id')} expected={run_id}")
    if manifest.get("no_provider_publish") is not True:
        errors.append(f"{rel(manifest_path)} must set no_provider_publish=true")
    if manifest.get("no_accepted_latest_switch") is not True:
        errors.append(f"{rel(manifest_path)} must set no_accepted_latest_switch=true")
    flags = manifest.get("forbidden_action_flags", {})
    for key in FORBIDDEN_ACTION_KEYS:
        if flags.get(key) is not False:
            errors.append(f"{rel(manifest_path)} forbidden_action_flags.{key} must be false")
    if manifest.get("status") not in {
        "READY",
        "PARTIAL_READY",
        "PARTIAL_READY_WITH_DECLARED_GAP",
        "BLOCKED_COVERAGE",
        "BLOCKED_SCHEMA",
        "BLOCKED_VALIDATOR",
    }:
        warnings.append(f"{rel(manifest_path)} has non-standard status={manifest.get('status')}")
    return manifest


def validate_csv(
    path: Path,
    required_fields: list[str],
    errors: list[str],
) -> dict[str, Any]:
    if not path.exists():
        return {"row_count": 0, "header": []}
    header, row_count = csv_header_and_count(path)
    missing = [field for field in required_fields if field not in header]
    if missing:
        errors.append(f"{rel(path)} missing required fields: {missing}")
    bad = forbidden_columns(header)
    if bad:
        errors.append(f"{rel(path)} contains forbidden fields: {bad}")
    if row_count <= 0:
        errors.append(f"{rel(path)} row_count must be > 0")
    return {"row_count": row_count, "header": header}


def validate_readiness(readiness_path: Path, run_id: str, asof: str, errors: list[str]) -> dict[str, Any]:
    if not readiness_path.exists():
        errors.append(f"missing readiness matrix: {rel(readiness_path)}")
        return {}
    readiness = read_json(readiness_path)
    if readiness.get("route_id") != "price_market_calendar":
        errors.append(f"{rel(readiness_path)} route_id must be price_market_calendar")
    if readiness.get("run_id") != run_id:
        errors.append(f"{rel(readiness_path)} run_id={readiness.get('run_id')} expected={run_id}")
    if readiness.get("asof") != asof:
        errors.append(f"{rel(readiness_path)} asof={readiness.get('asof')} expected={asof}")
    dependencies = readiness.get("dependencies")
    if not isinstance(dependencies, list) or not dependencies:
        errors.append(f"{rel(readiness_path)} dependencies must be a non-empty list")
    else:
        names = {row.get("dependency_name") for row in dependencies}
        required_names = {
            "price_coverage",
            "twii_coverage",
            "calendar_coverage",
            "next_day_execution_availability",
            "halt_suspension_evidence",
            "mark_to_market_close_coverage",
            "holiday_or_no_data_evidence",
        }
        missing = sorted(required_names - names)
        if missing:
            errors.append(f"{rel(readiness_path)} missing dependencies: {missing}")
    for key in [
        "can_continue_to_model_score",
        "can_continue_to_replay",
        "can_continue_to_shadow_execution",
        "can_continue_to_dng3",
    ]:
        if not isinstance(readiness.get(key), bool):
            errors.append(f"{rel(readiness_path)} {key} must be boolean")
    flags = readiness.get("forbidden_action_flags", {})
    for key in FORBIDDEN_ACTION_KEYS:
        if flags.get(key) is not False:
            errors.append(f"{rel(readiness_path)} forbidden_action_flags.{key} must be false")
    return readiness


def overall_status(errors: list[str], readiness: dict[str, Any], price_manifest: dict[str, Any], twii_manifest: dict[str, Any]) -> str:
    if errors:
        return "BLOCKED_VALIDATOR"
    readiness_status = readiness.get("status")
    if readiness_status == "READY":
        return "READY"
    if readiness_status == "BLOCKED_COVERAGE":
        return "BLOCKED_COVERAGE"
    if "BLOCKED_COVERAGE" in {price_manifest.get("status"), twii_manifest.get("status")}:
        return "BLOCKED_COVERAGE"
    return "PARTIAL_READY"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate DNG2 canonical PriceStore/TWII/calendar artifacts.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--asof", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    generated_at = utc_now()
    price_dir = ROOT / "data_tw/canonical/price_store/tw_equity_daily" / args.run_id
    twii_dir = ROOT / "data_tw/canonical/market_feature_store/twii_daily" / args.run_id
    readiness_path = ROOT / "data_tw/catalog/readiness_matrix" / args.asof / "price_market_calendar.json"
    validation_path = ROOT / "data_tw/catalog/dng2_price_market_calendar_validation.json"

    errors: list[str] = []
    warnings: list[str] = []
    required_paths = {
        "price_store": validate_required_files(price_dir, PRICE_REQUIRED_FILES, errors),
        "twii": validate_required_files(twii_dir, TWII_REQUIRED_FILES, errors),
        "readiness_matrix": rel(readiness_path),
    }

    price_manifest = validate_manifest(price_dir / "manifest.json", "price_store", args.run_id, errors, warnings)
    twii_manifest = validate_manifest(twii_dir / "manifest.json", "market_feature_store", args.run_id, errors, warnings)
    validate_schema(price_dir / "schema.json", "price_store", PRICE_REQUIRED_FIELDS, errors)
    validate_schema(twii_dir / "schema.json", "market_feature_store", TWII_REQUIRED_FIELDS, errors)
    price_csv = validate_csv(price_dir / "prices.csv", PRICE_REQUIRED_FIELDS, errors)
    twii_csv = validate_csv(twii_dir / "twii.csv", TWII_REQUIRED_FIELDS, errors)
    readiness = validate_readiness(readiness_path, args.run_id, args.asof, errors)

    status = overall_status(errors, readiness, price_manifest, twii_manifest)
    payload = {
        "ok": not errors,
        "status": status,
        "generated_at": generated_at,
        "run_id": args.run_id,
        "asof": args.asof,
        "errors": errors,
        "warnings": warnings,
        "required_paths": required_paths,
        "checks": {
            "price_required_files": not any(f"missing required file: {rel(price_dir / name)}" in errors for name in PRICE_REQUIRED_FILES),
            "twii_required_files": not any(f"missing required file: {rel(twii_dir / name)}" in errors for name in TWII_REQUIRED_FILES),
            "price_required_fields": all(field in price_csv.get("header", []) for field in PRICE_REQUIRED_FIELDS),
            "twii_required_fields": all(field in twii_csv.get("header", []) for field in TWII_REQUIRED_FIELDS),
            "price_row_count_gt_0": price_csv.get("row_count", 0) > 0,
            "twii_row_count_gt_0": twii_csv.get("row_count", 0) > 0,
            "forbidden_fields_absent": not forbidden_columns(price_csv.get("header", [])) and not forbidden_columns(twii_csv.get("header", [])),
            "forbidden_action_flags_false": not any("forbidden_action_flags" in error for error in errors),
            "readiness_matrix_exists": readiness_path.exists(),
        },
        "row_counts": {
            "prices": price_csv.get("row_count", 0),
            "twii": twii_csv.get("row_count", 0),
        },
        "artifact_status": {
            "price_store": price_manifest.get("status"),
            "twii": twii_manifest.get("status"),
            "readiness_matrix": readiness.get("status"),
            "can_continue": readiness.get("can_continue"),
            "can_continue_to_model_score": readiness.get("can_continue_to_model_score"),
            "can_continue_to_replay": readiness.get("can_continue_to_replay"),
            "can_continue_to_shadow_execution": readiness.get("can_continue_to_shadow_execution"),
            "can_continue_to_dng3": readiness.get("can_continue_to_dng3"),
            "external_source_repair_required": readiness.get("external_source_repair_required"),
        },
        "forbidden_action_confirmation": {
            key: False for key in FORBIDDEN_ACTION_KEYS
        },
    }
    write_json(validation_path, payload)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"ok={payload['ok']} status={status} errors={len(errors)} warnings={len(warnings)}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
