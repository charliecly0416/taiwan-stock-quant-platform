#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from tw_modela_score_common import (
    FORBIDDEN_ACTIONS_FALSE,
    INFERENCE_FIELDS,
    MODEL_ID,
    TARGET_ASOF,
    forbidden_columns,
    read_json,
    rel,
    write_json,
)


REQUIRED_FILES = [
    "manifest.json",
    "inference_frame.csv",
    "schema.json",
    "source_readiness.json",
    "feature_lineage.json",
    "pit_audit.csv",
    "coverage_audit.csv",
]


def validate(input_dir: Path, target_asof: str = TARGET_ASOF, write_report: bool = True) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    file_status = {}
    for name in REQUIRED_FILES:
        path = input_dir / name
        file_status[name] = path.exists()
        if not path.exists():
            errors.append(f"missing_required_file:{name}")
    manifest = read_json(input_dir / "manifest.json") if (input_dir / "manifest.json").exists() else {}
    source = read_json(input_dir / "source_readiness.json") if (input_dir / "source_readiness.json").exists() else {}
    frame = pd.DataFrame()
    if (input_dir / "inference_frame.csv").exists():
        frame = pd.read_csv(input_dir / "inference_frame.csv")
        missing = sorted(set(INFERENCE_FIELDS) - set(frame.columns))
        if missing:
            errors.append("missing_inference_fields:" + ",".join(missing))
        forbidden = forbidden_columns(list(frame.columns))
        if forbidden:
            errors.append("forbidden_inference_fields:" + ",".join(forbidden))
        if {"date", "instrument"} <= set(frame.columns):
            duplicates = int(frame.duplicated(["date", "instrument"]).sum())
            if duplicates:
                errors.append(f"duplicate_date_instrument:{duplicates}")
            dates = sorted(str(x) for x in frame["date"].dropna().unique())
            if dates != [target_asof]:
                errors.append(f"inference_date_not_target:{dates}")
        if "instrument" in frame.columns and int(frame["instrument"].nunique()) != 150:
            errors.append(f"instrument_count_not_150:{int(frame['instrument'].nunique())}")
    if manifest.get("model_id") != MODEL_ID:
        errors.append("manifest_model_id_mismatch")
    if manifest.get("asof") != target_asof:
        errors.append("manifest_asof_mismatch")
    if source.get("qlib_provider_calendar_max", "") < target_asof:
        errors.append("provider_calendar_stale")
    if source.get("normalized_source_summary", {}).get("symbols_with_asof") != 150:
        errors.append("normalized_symbols_with_asof_not_150")
    if source.get("provider_field_inventory", {}).get("status") != "pass":
        errors.append("provider_field_inventory_not_pass")
    actions = manifest.get("forbidden_actions", {})
    for key, expected in FORBIDDEN_ACTIONS_FALSE.items():
        if actions.get(key) is not expected:
            errors.append(f"forbidden_action_flag_not_false:{key}")
    if manifest.get("not_published_latest") is not True:
        errors.append("manifest_not_published_latest_missing")
    if manifest.get("production_allowed") is not False:
        errors.append("manifest_production_allowed_not_false")
    if manifest.get("status") != "READY":
        errors.append(f"input_status_not_ready:{manifest.get('status')}")
    report = {
        "ok": not errors,
        "status": "PASS" if not errors else "FAIL",
        "artifact_type": "ModelInferenceInput",
        "target_asof": target_asof,
        "input_dir": rel(input_dir),
        "checked_at": pd.Timestamp.utcnow().replace(microsecond=0).isoformat(),
        "errors": errors,
        "warnings": warnings,
        "file_status": file_status,
        "row_count": int(len(frame)),
        "instrument_count": int(frame["instrument"].nunique()) if "instrument" in frame.columns else 0,
        "manifest_status": manifest.get("status"),
        "source_status": source.get("status"),
    }
    if write_report:
        write_json(input_dir / "validator_report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate DNG7 ModelInferenceInput artifact.")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--asof", default=TARGET_ASOF)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = validate(Path(args.input_dir), args.asof)
    if args.json:
        print(json.dumps(report, ensure_ascii=True, indent=2))
    else:
        print(f"{report['status']} {report['input_dir']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
