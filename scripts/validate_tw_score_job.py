#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from tw_modela_score_common import (
    FORBIDDEN_ACTIONS_FALSE,
    MODEL_ID,
    SIGNAL_FIELDS,
    TARGET_ASOF,
    contained_path_forbidden_reason,
    forbidden_columns,
    is_relative_to,
    read_json,
    rel,
    resolve_runtime_path,
    validate_signal_frame,
    write_json,
)


SCORE_REQUIRED_FILES = [
    "manifest.json",
    "raw_scores.csv",
    "rank_audit.csv",
    "model_load_audit.json",
    "input_readiness.json",
    "output_model_signal_manifest.json",
]
SIGNAL_REQUIRED_FILES = ["manifest.json", "signals.csv", "schema.json", "coverage_audit.csv", "forbidden_field_audit.csv"]


def validate(
    score_dir: Path,
    signal_dir: Path | None = None,
    target_asof: str = TARGET_ASOF,
    write_report: bool = True,
    contained_output_root: Path | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    if contained_output_root is not None:
        contained_output_root = resolve_runtime_path(contained_output_root)
        for role, path in {"score_dir": score_dir, "signal_dir": signal_dir or Path("")}.items():
            if role == "signal_dir" and signal_dir is None:
                continue
            resolved = resolve_runtime_path(path)
            if not is_relative_to(resolved, contained_output_root):
                errors.append(f"{role}_not_under_contained_output_root")
            reason = contained_path_forbidden_reason(resolved)
            if reason:
                errors.append(f"{role}_{reason}")
    file_status = {}
    for name in SCORE_REQUIRED_FILES:
        path = score_dir / name
        file_status[f"score/{name}"] = path.exists()
        if not path.exists():
            errors.append(f"missing_score_file:{name}")
    manifest = read_json(score_dir / "manifest.json") if (score_dir / "manifest.json").exists() else {}
    if signal_dir is None:
        signal_path = manifest.get("signal_artifact", "")
        signal_dir = Path(signal_path)
        if not signal_dir.is_absolute():
            signal_dir = Path(__file__).resolve().parents[1] / signal_dir
        if contained_output_root is not None:
            resolved_signal_dir = resolve_runtime_path(signal_dir)
            if not is_relative_to(resolved_signal_dir, contained_output_root):
                errors.append("signal_dir_not_under_contained_output_root")
            reason = contained_path_forbidden_reason(resolved_signal_dir)
            if reason:
                errors.append(f"signal_dir_{reason}")
    for name in SIGNAL_REQUIRED_FILES:
        path = signal_dir / name
        file_status[f"signal/{name}"] = path.exists()
        if not path.exists():
            errors.append(f"missing_signal_file:{name}")

    raw = pd.DataFrame()
    signals = pd.DataFrame()
    if (score_dir / "raw_scores.csv").exists():
        raw = pd.read_csv(score_dir / "raw_scores.csv")
        required_raw = {"date", "instrument", "raw_score", "score_rank", "full_qlib_rank"}
        missing = sorted(required_raw - set(raw.columns))
        if missing:
            errors.append("missing_raw_score_fields:" + ",".join(missing))
        forbidden = forbidden_columns(list(raw.columns))
        if forbidden:
            errors.append("forbidden_raw_score_fields:" + ",".join(forbidden))
        if len(raw) != 150:
            errors.append(f"raw_score_row_count_not_150:{len(raw)}")
        if "date" in raw.columns and sorted(str(x) for x in raw["date"].dropna().unique()) != [target_asof]:
            errors.append("raw_score_date_not_target")
    if (signal_dir / "signals.csv").exists():
        signals = pd.read_csv(signal_dir / "signals.csv")
        signal_errors, signal_summary = validate_signal_frame(signals, target_asof)
        errors.extend(signal_errors)
        if len(signals) != 150:
            errors.append(f"signal_row_count_not_150:{len(signals)}")
        if sorted(set(SIGNAL_FIELDS) - set(signals.columns)):
            errors.append("signal_contract_missing_fields")
    else:
        signal_summary = {}

    if manifest.get("model_id") != MODEL_ID:
        errors.append("score_manifest_model_id_mismatch")
    if manifest.get("asof") != target_asof:
        errors.append("score_manifest_asof_mismatch")
    if manifest.get("score_status") != "SCORED_ASOF_TARGET":
        errors.append(f"score_status_not_scored_target:{manifest.get('score_status')}")
    actions = manifest.get("forbidden_actions", {})
    for key, expected in FORBIDDEN_ACTIONS_FALSE.items():
        if actions.get(key) is not expected:
            errors.append(f"forbidden_action_flag_not_false:{key}")
    load_audit = read_json(score_dir / "model_load_audit.json") if (score_dir / "model_load_audit.json").exists() else {}
    if load_audit.get("no_training") is not True or load_audit.get("no_tuning") is not True:
        errors.append("model_load_audit_training_tuning_not_false")
    input_readiness = read_json(score_dir / "input_readiness.json") if (score_dir / "input_readiness.json").exists() else {}
    if input_readiness.get("ok") is not True:
        errors.append("input_readiness_not_ok")
    signal_manifest = read_json(signal_dir / "manifest.json") if (signal_dir / "manifest.json").exists() else {}
    if signal_manifest.get("status") != "READY":
        errors.append(f"signal_manifest_status_not_ready:{signal_manifest.get('status')}")
    report = {
        "ok": not errors,
        "status": "PASS" if not errors else "FAIL",
        "artifact_type": "ScoreJob",
        "target_asof": target_asof,
        "score_job_dir": rel(score_dir),
        "signal_dir": rel(signal_dir),
        "contained_output_root": rel(contained_output_root) if contained_output_root else "",
        "checked_at": pd.Timestamp.utcnow().replace(microsecond=0).isoformat(),
        "errors": errors,
        "file_status": file_status,
        "raw_score_rows": int(len(raw)),
        "signal_rows": int(len(signals)),
        "score_status": manifest.get("score_status"),
        "signal_summary": signal_summary,
    }
    if write_report:
        write_json(score_dir / "validator_report.json", report)
        write_json(
            signal_dir / "validator_report.json",
            {
                "ok": report["ok"],
                "status": report["status"],
                "artifact_type": "ModelSignalArtifact",
                "target_asof": target_asof,
                "signal_dir": rel(signal_dir),
                "checked_at": report["checked_at"],
                "errors": errors,
                "signal_rows": int(len(signals)),
                "signal_summary": signal_summary,
            },
        )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate DNG7 qlib Model A ScoreJob and ModelSignalArtifact.")
    parser.add_argument("--score-dir", required=True)
    parser.add_argument("--signal-dir", default=None)
    parser.add_argument("--asof", default=TARGET_ASOF)
    parser.add_argument("--contained-output-root", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = validate(
        Path(args.score_dir),
        Path(args.signal_dir) if args.signal_dir else None,
        args.asof,
        contained_output_root=Path(args.contained_output_root) if args.contained_output_root else None,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=True, indent=2))
    else:
        print(f"{report['status']} {report['score_job_dir']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
