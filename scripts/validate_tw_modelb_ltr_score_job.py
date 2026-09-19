#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tw_modelb_ltr_score_common import (
    BLOCKED_STATUS,
    DEFAULT_RUN_ID,
    FALLBACK_ALLOWED,
    FORBIDDEN_ACTIONS_FALSE,
    INPUT_BASE,
    MODEL_ID,
    SCORE_BASE,
    TARGET_ASOF,
    csv_columns,
    forbidden_columns,
    read_json,
    rel,
    utc_now,
    write_json,
)


INPUT_REQUIRED_FILES = [
    "manifest.json",
    "blocker_input_readiness.json",
    "schema.json",
    "source_readiness.json",
    "feature_lineage.json",
    "pit_audit.csv",
]
SCORE_REQUIRED_FILES = [
    "manifest.json",
    "input_readiness.json",
]


def _resolve_input_dir(score_manifest: dict[str, Any], explicit_input_dir: Path | None) -> Path:
    if explicit_input_dir is not None:
        return explicit_input_dir
    value = score_manifest.get("inference_input", "")
    path = Path(value)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[1] / path
    return path


def _check_forbidden_actions(payload: dict[str, Any], prefix: str, errors: list[str]) -> None:
    actions = payload.get("forbidden_actions", {})
    for key, expected in FORBIDDEN_ACTIONS_FALSE.items():
        if actions.get(key) is not expected:
            errors.append(f"{prefix}_forbidden_action_flag_not_false:{key}")


def validate(
    score_dir: Path,
    input_dir: Path | None = None,
    target_asof: str = TARGET_ASOF,
    write_report: bool = True,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    file_status: dict[str, bool] = {}

    for name in SCORE_REQUIRED_FILES:
        path = score_dir / name
        file_status[f"score/{name}"] = path.exists()
        if not path.exists():
            errors.append(f"missing_score_file:{name}")
    score_manifest = read_json(score_dir / "manifest.json") if (score_dir / "manifest.json").exists() else {}
    input_dir = _resolve_input_dir(score_manifest, input_dir)

    for name in INPUT_REQUIRED_FILES:
        path = input_dir / name
        file_status[f"input/{name}"] = path.exists()
        if not path.exists():
            errors.append(f"missing_input_file:{name}")

    input_manifest = read_json(input_dir / "manifest.json") if (input_dir / "manifest.json").exists() else {}
    blocker = read_json(input_dir / "blocker_input_readiness.json") if (input_dir / "blocker_input_readiness.json").exists() else {}
    input_readiness = read_json(score_dir / "input_readiness.json") if (score_dir / "input_readiness.json").exists() else {}

    if score_manifest.get("model_id") != MODEL_ID:
        errors.append("score_manifest_model_id_mismatch")
    if input_manifest.get("model_id") != MODEL_ID:
        errors.append("input_manifest_model_id_mismatch")
    if score_manifest.get("asof") != target_asof:
        errors.append(f"score_manifest_asof_mismatch:{score_manifest.get('asof')}")
    if input_manifest.get("asof") != target_asof:
        errors.append(f"input_manifest_asof_mismatch:{input_manifest.get('asof')}")

    for label, payload in [("score", score_manifest), ("input", input_manifest), ("blocker", blocker)]:
        if payload.get("score_status") != BLOCKED_STATUS:
            errors.append(f"{label}_score_status_not_blocked:{payload.get('score_status')}")
        if payload.get("model_b_ltr_ready") is not False:
            errors.append(f"{label}_model_b_ltr_ready_not_false:{payload.get('model_b_ltr_ready')}")
        if payload.get("fallback_allowed") != FALLBACK_ALLOWED:
            errors.append(f"{label}_fallback_allowed_mismatch:{payload.get('fallback_allowed')}")
        _check_forbidden_actions(payload, label, errors)

    blocking = blocker.get("blocking_datasets") or input_manifest.get("blocking_datasets") or []
    for dataset in ["corporate_actions", "monthly_revenue", "valuation"]:
        if dataset not in blocking:
            errors.append(f"missing_expected_blocking_dataset:{dataset}")

    if (input_dir / "inference_frame.csv").exists():
        errors.append("inference_frame_present_despite_blocked_input")
    forbidden_input_columns = forbidden_columns(csv_columns(input_dir / "inference_frame.csv"))
    if forbidden_input_columns:
        errors.append("forbidden_inference_fields:" + ",".join(forbidden_input_columns))

    signals_csvs = sorted(score_dir.glob("signals.csv")) + sorted((score_dir / "signals").glob("*.csv")) if score_dir.exists() else []
    if signals_csvs:
        errors.append("modelb_signal_csv_present_despite_blocked_input")
    if score_manifest.get("signal_artifact"):
        errors.append("score_manifest_has_signal_artifact_despite_blocked_input")
    if score_manifest.get("fallback_signal_artifact") and "dng7_modela_20260625" not in str(score_manifest.get("fallback_signal_artifact")):
        errors.append("fallback_signal_artifact_is_not_dng7_modela")

    if input_readiness.get("status") != BLOCKED_STATUS:
        errors.append(f"input_readiness_status_not_blocked:{input_readiness.get('status')}")
    if input_readiness.get("model_b_ltr_ready") is not False:
        errors.append("input_readiness_model_b_ltr_ready_not_false")
    if input_readiness.get("do_not_substitute_qlib_score_as_ltr_score") is not True:
        errors.append("missing_do_not_substitute_qlib_score_as_ltr_score_flag")

    if input_manifest.get("production_allowed") is not False or score_manifest.get("production_allowed") is not False:
        errors.append("production_allowed_not_false")
    if input_manifest.get("not_published_latest") is not True or score_manifest.get("not_published_latest") is not True:
        errors.append("not_published_latest_not_true")

    report = {
        "ok": not errors,
        "status": "PASS" if not errors else "FAIL",
        "artifact_type": "ScoreJob",
        "model_id": MODEL_ID,
        "target_asof": target_asof,
        "score_job_dir": rel(score_dir),
        "input_dir": rel(input_dir),
        "checked_at": utc_now(),
        "score_status": score_manifest.get("score_status"),
        "model_b_ltr_ready": score_manifest.get("model_b_ltr_ready"),
        "fallback_allowed": score_manifest.get("fallback_allowed"),
        "blocking_datasets": blocking,
        "ltr_signal_generated": False,
        "fake_ltr_signal_detected": bool(signals_csvs),
        "errors": errors,
        "warnings": warnings,
        "file_status": file_status,
        "forbidden_action_audit": FORBIDDEN_ACTIONS_FALSE,
    }
    if write_report:
        write_json(score_dir / "validator_report.json", report)
        if input_dir.exists():
            write_json(input_dir / "validator_report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate DNG8 blocked Model B LTR ScoreJob.")
    parser.add_argument("--score-dir", default=str(SCORE_BASE / DEFAULT_RUN_ID))
    parser.add_argument("--input-dir", default=None)
    parser.add_argument("--asof", default=TARGET_ASOF)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = validate(
        Path(args.score_dir),
        Path(args.input_dir) if args.input_dir else None,
        args.asof,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=True, indent=2))
    else:
        print(f"{report['status']} {report['score_job_dir']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
