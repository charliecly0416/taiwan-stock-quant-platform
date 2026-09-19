#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FEATURE_SET_ID = "daily_orthogonal"

REQUIRED_FILES = [
    "manifest.json",
    "features.csv",
    "schema.json",
    "source_data_audit.json",
    "pit_audit.csv",
    "coverage_audit.csv",
    "provider_status.json",
    "lineage.json",
]

FEATURE_REQUIRED_FIELDS = [
    "feature_date",
    "instrument",
    "feature_name",
    "feature_value",
    "source_dataset",
    "source_path",
    "source_provider",
    "available_at",
    "pit_policy",
    "coverage_status",
]

REQUIRED_PROVIDER_DATASETS = {
    "institutional_flow",
    "margin_short",
    "corporate_actions",
    "monthly_revenue",
    "valuation",
}

FORBIDDEN_FIELDS = {
    "target_position",
    "target_weight",
    "order_qty",
    "broker_order_id",
    "portfolio_equity",
    "strategy_action",
}

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


def validate_required_files(base: Path, errors: list[str]) -> dict[str, str]:
    paths: dict[str, str] = {}
    for name in REQUIRED_FILES:
        path = base / name
        paths[name] = rel(path)
        if not path.exists():
            errors.append(f"missing required file: {rel(path)}")
    return paths


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


def validate_flags(payload: dict[str, Any], path: Path, errors: list[str]) -> None:
    flags = payload.get("forbidden_action_flags", {})
    for key in FORBIDDEN_ACTION_KEYS:
        if flags.get(key) is not False:
            errors.append(f"{rel(path)} forbidden_action_flags.{key} must be false")


def validate_manifest(path: Path, run_id: str, asof: str, errors: list[str], warnings: list[str]) -> dict[str, Any]:
    if not path.exists():
        return {}
    manifest = read_json(path)
    if manifest.get("artifact_type") != "CanonicalOrthogonalFeatureStore":
        errors.append(f"{rel(path)} artifact_type must be CanonicalOrthogonalFeatureStore")
    if manifest.get("feature_set_id") != FEATURE_SET_ID:
        errors.append(f"{rel(path)} feature_set_id must be {FEATURE_SET_ID}")
    if manifest.get("run_id") != run_id:
        errors.append(f"{rel(path)} run_id={manifest.get('run_id')} expected={run_id}")
    if manifest.get("asof") != asof:
        errors.append(f"{rel(path)} asof={manifest.get('asof')} expected={asof}")
    if manifest.get("no_provider_publish") is not True:
        errors.append(f"{rel(path)} must set no_provider_publish=true")
    if manifest.get("no_accepted_latest_switch") is not True:
        errors.append(f"{rel(path)} must set no_accepted_latest_switch=true")
    if manifest.get("can_continue_to_model_score") is not True:
        warnings.append(f"{rel(path)} can_continue_to_model_score is not true")
    validate_flags(manifest, path, errors)
    return manifest


def validate_schema(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.exists():
        return {}
    schema = read_json(path)
    if schema.get("artifact_type") != "CanonicalOrthogonalFeatureStore":
        errors.append(f"{rel(path)} artifact_type must be CanonicalOrthogonalFeatureStore")
    missing = [field for field in FEATURE_REQUIRED_FIELDS if field not in schema.get("required_fields", [])]
    if missing:
        errors.append(f"{rel(path)} schema missing required_fields: {missing}")
    return schema


def validate_features(path: Path, asof: str, errors: list[str], warnings: list[str]) -> dict[str, Any]:
    if not path.exists():
        return {"row_count": 0, "header": [], "datasets": []}
    header, row_count = csv_header_and_count(path)
    missing = [field for field in FEATURE_REQUIRED_FIELDS if field not in header]
    if missing:
        errors.append(f"{rel(path)} missing required fields: {missing}")
    bad = forbidden_columns(header)
    if bad:
        errors.append(f"{rel(path)} contains forbidden fields: {bad}")
    if row_count <= 0:
        errors.append(f"{rel(path)} row_count must be > 0")

    datasets: set[str] = set()
    pit_errors = 0
    available_after_asof = 0
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            datasets.add(row.get("source_dataset", ""))
            feature_date = row.get("feature_date", "")
            available_at = row.get("available_at", "")
            if not feature_date or not row.get("instrument") or not row.get("feature_name"):
                pit_errors += 1
            if not available_at:
                pit_errors += 1
            elif feature_date and available_at < feature_date:
                pit_errors += 1
            if available_at and available_at > asof:
                available_after_asof += 1
            if not row.get("pit_policy"):
                pit_errors += 1
    if pit_errors:
        errors.append(f"{rel(path)} PIT/required row validation failed count={pit_errors}")
    if available_after_asof:
        warnings.append(
            f"{rel(path)} has PIT-delayed rows with available_at after asof count={available_after_asof}; "
            "kept as canonical evidence and blocked from Model B readiness by dataset gates"
        )
    return {
        "row_count": row_count,
        "header": header,
        "datasets": sorted(dataset for dataset in datasets if dataset),
        "available_after_asof": available_after_asof,
        "pit_errors": pit_errors,
    }


def validate_provider_status(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = read_json(path)
    datasets = payload.get("datasets", [])
    if not isinstance(datasets, list) or not datasets:
        errors.append(f"{rel(path)} datasets must be a non-empty list")
        return payload
    names = {row.get("dataset_id") for row in datasets}
    missing = sorted(REQUIRED_PROVIDER_DATASETS - names)
    if missing:
        errors.append(f"{rel(path)} missing provider datasets: {missing}")
    for row in datasets:
        for field in [
            "dataset_id",
            "provider",
            "source_max_date",
            "row_count",
            "symbol_count",
            "status",
            "status_reason",
            "quota_or_permission_status",
            "holiday_or_no_data_evidence",
            "requires_external_source_repair",
        ]:
            if field not in row:
                errors.append(f"{rel(path)} provider row missing {field}: {row}")
    validate_flags(payload, path, errors)
    return payload


def validate_readiness(path: Path, run_id: str, asof: str, errors: list[str]) -> dict[str, Any]:
    if not path.exists():
        errors.append(f"missing readiness matrix: {rel(path)}")
        return {}
    readiness = read_json(path)
    if readiness.get("route_id") != "orthogonal_feature_store":
        errors.append(f"{rel(path)} route_id must be orthogonal_feature_store")
    if readiness.get("run_id") != run_id:
        errors.append(f"{rel(path)} run_id={readiness.get('run_id')} expected={run_id}")
    if readiness.get("asof") != asof:
        errors.append(f"{rel(path)} asof={readiness.get('asof')} expected={asof}")
    for key in ["can_continue_to_model_b_ltr", "can_continue_to_model_score", "can_continue_to_dng4"]:
        if not isinstance(readiness.get(key), bool):
            errors.append(f"{rel(path)} {key} must be boolean")
    if not isinstance(readiness.get("blocking_datasets"), list):
        errors.append(f"{rel(path)} blocking_datasets must be a list")
    dependency_names = {row.get("dependency_name") for row in readiness.get("dependencies", []) if isinstance(row, dict)}
    missing = sorted(REQUIRED_PROVIDER_DATASETS - dependency_names)
    if missing:
        errors.append(f"{rel(path)} missing dependency rows: {missing}")
    if readiness.get("can_continue_to_model_b_ltr") is True and readiness.get("blocking_datasets"):
        errors.append(f"{rel(path)} cannot allow model_b_ltr with blocking_datasets")
    validate_flags(readiness, path, errors)
    return readiness


def validate_lineage(path: Path, run_id: str, errors: list[str]) -> dict[str, Any]:
    if not path.exists():
        return {}
    lineage = read_json(path)
    if lineage.get("lineage_type") != "local_canonicalization_no_fetch":
        errors.append(f"{rel(path)} lineage_type must be local_canonicalization_no_fetch")
    if lineage.get("run_id") != run_id:
        errors.append(f"{rel(path)} run_id={lineage.get('run_id')} expected={run_id}")
    for key in ["no_provider_publish", "no_accepted_latest_switch"]:
        if lineage.get(key) is not True:
            errors.append(f"{rel(path)} {key} must be true")
    validate_flags(lineage, path, errors)
    return lineage


def validate_aux_csv(path: Path, required_fields: list[str], errors: list[str]) -> dict[str, Any]:
    if not path.exists():
        return {}
    header, row_count = csv_header_and_count(path)
    missing = [field for field in required_fields if field not in header]
    if missing:
        errors.append(f"{rel(path)} missing fields: {missing}")
    if row_count <= 0:
        errors.append(f"{rel(path)} row_count must be > 0")
    return {"header": header, "row_count": row_count}


def append_validation_to_report(report_path: Path, validation: dict[str, Any]) -> None:
    if not report_path.exists():
        return
    text = report_path.read_text(encoding="utf-8")
    marker = "## 6. Validator 输出\n"
    if marker not in text:
        return
    before = text.split(marker)[0]
    after = text.split("## 7. Forbidden Action Audit\n", 1)
    tail = "## 7. Forbidden Action Audit\n" + after[1] if len(after) == 2 else ""
    validator_text = f"""## 6. Validator 输出

```json
{json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True)}
```

"""
    report_path.write_text(before + validator_text + tail, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate DNG3 canonical TW orthogonal feature store artifacts.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--asof", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    out_dir = ROOT / "data_tw/canonical/orthogonal_feature_store" / FEATURE_SET_ID / args.run_id
    readiness_path = ROOT / "data_tw/catalog/readiness_matrix" / args.asof / "orthogonal_feature_store.json"
    validation_path = ROOT / "data_tw/catalog/dng3_orthogonal_feature_store_validation.json"
    report_path = ROOT / "docs/tw_data_governance/DNG3_ORTHOGONAL_DATA_STORE_EXECUTION_REPORT_CN.md"

    errors: list[str] = []
    warnings: list[str] = []
    required_paths = validate_required_files(out_dir, errors)

    manifest = validate_manifest(out_dir / "manifest.json", args.run_id, args.asof, errors, warnings)
    schema = validate_schema(out_dir / "schema.json", errors)
    features = validate_features(out_dir / "features.csv", args.asof, errors, warnings)
    provider_status = validate_provider_status(out_dir / "provider_status.json", errors)
    readiness = validate_readiness(readiness_path, args.run_id, args.asof, errors)
    lineage = validate_lineage(out_dir / "lineage.json", args.run_id, errors)
    pit_audit = validate_aux_csv(
        out_dir / "pit_audit.csv",
        ["dataset_id", "rows_checked", "pit_violation_count", "available_after_asof_count", "status"],
        errors,
    )
    coverage_audit = validate_aux_csv(
        out_dir / "coverage_audit.csv",
        ["dataset_id", "status", "coverage_status", "row_count", "feature_row_count", "symbol_count"],
        errors,
    )

    if (out_dir / "source_data_audit.json").exists():
        source_data_audit = read_json(out_dir / "source_data_audit.json")
        validate_flags(source_data_audit, out_dir / "source_data_audit.json", errors)
    else:
        source_data_audit = {}

    status = "BLOCKED_VALIDATOR" if errors else readiness.get("status", manifest.get("status", "PARTIAL_READY"))
    validation = {
        "schema_version": "v1.dng3.orthogonal_feature_store.validation",
        "generated_at": utc_now(),
        "ok": not errors,
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "run_id": args.run_id,
        "asof": args.asof,
        "required_paths": required_paths,
        "feature_store": {
            "path": rel(out_dir),
            "row_count": features.get("row_count", 0),
            "datasets": features.get("datasets", []),
            "manifest_status": manifest.get("status"),
            "can_continue_to_model_b_ltr": readiness.get("can_continue_to_model_b_ltr"),
            "can_continue_to_model_score": readiness.get("can_continue_to_model_score"),
            "can_continue_to_dng4": readiness.get("can_continue_to_dng4"),
            "blocking_datasets": readiness.get("blocking_datasets", []),
        },
        "provider_status": {
            "dataset_count": len(provider_status.get("datasets", [])) if isinstance(provider_status.get("datasets"), list) else 0,
            "statuses": {
                row.get("dataset_id"): row.get("status")
                for row in provider_status.get("datasets", [])
                if isinstance(row, dict)
            },
        },
        "pit_audit": pit_audit,
        "coverage_audit": coverage_audit,
        "forbidden_action_flags": {key: False for key in FORBIDDEN_ACTION_KEYS},
        "validated_files": {
            "manifest": bool(manifest),
            "schema": bool(schema),
            "provider_status": bool(provider_status),
            "readiness": bool(readiness),
            "lineage": bool(lineage),
            "source_data_audit": bool(source_data_audit),
        },
    }

    write_json(validation_path, validation)
    append_validation_to_report(report_path, validation)

    if args.json:
        print(json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"ok={validation['ok']} status={status} errors={len(errors)} warnings={len(warnings)}")
    return 0 if validation["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
