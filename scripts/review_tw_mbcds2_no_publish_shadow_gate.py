#!/usr/bin/env python3
"""Independent reviewer for the MBCDS2 input-only gate."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow/mbcds2_shadow_20260905"
REQUIRED = ["manifest.json", "input_readiness.json", "feature_contract_audit.csv", "forbidden_scope_audit.json", "checksum_manifest.json", "execution_report.md"]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    errors = []
    missing = [name for name in REQUIRED if not (OUT / name).is_file()]
    if missing:
        errors.append("missing_outputs:" + ",".join(missing))
        result = {"verdict": "FAIL", "errors": errors}
    else:
        manifest = json.loads((OUT / "manifest.json").read_text())
        readiness = json.loads((OUT / "input_readiness.json").read_text())
        forbidden = json.loads((OUT / "forbidden_scope_audit.json").read_text())
        checksums = json.loads((OUT / "checksum_manifest.json").read_text())
        with (OUT / "feature_contract_audit.csv").open(newline="") as fh:
            rows = list(csv.DictReader(fh))
        if manifest.get("status") != "BLOCKED_INPUT_FEATURES_NOT_MATERIALIZED":
            errors.append("manifest_status_mismatch")
        if readiness.get("status") != "BLOCKED_INPUT_FEATURES_NOT_MATERIALIZED":
            errors.append("readiness_status_mismatch")
        if readiness.get("can_score") is not False or readiness.get("can_train") is not False:
            errors.append("score_or_train_not_blocked")
        if readiness.get("required_feature_count") != 34 or readiness.get("materialized_numeric_feature_count") != 0:
            errors.append("feature_counts_mismatch")
        if len(rows) != 34 or any(row.get("decision") != "MISSING_NOT_MATERIALIZED" for row in rows):
            errors.append("feature_audit_not_complete_blocked")
        if readiness.get("modela_inference_rows") != 150 or readiness.get("modela_prediction_rows") != 150:
            errors.append("modela_input_row_count_mismatch")
        if readiness.get("label_or_future_data_read") is not False:
            errors.append("label_future_data_boundary_failed")
        if readiness.get("model_pickle_loaded_or_called") is not False:
            errors.append("model_pickle_called")
        if forbidden.get("protected_unchanged") is not True:
            errors.append("protected_fingerprint_changed")
        forbidden_keys = ["training_triggered", "scoring_triggered", "labels_or_future_data_used", "model_signal_artifact_generated", "latest_written", "provider_written_or_refreshed", "cron_written", "frontend_written", "backend_written"]
        if any(forbidden.get(key) is not False for key in forbidden_keys):
            errors.append("forbidden_scope_flag_failed")
        for path, expected in checksums.items():
            actual = sha(ROOT / path)
            if actual != expected:
                errors.append(f"checksum_mismatch:{path}")
        result = {
            "verdict": "PASS" if not errors else "FAIL",
            "gate_status": readiness.get("status"),
            "errors": errors,
            "required_outputs": REQUIRED,
            "feature_count": len(rows),
            "materialized_numeric_feature_count": readiness.get("materialized_numeric_feature_count"),
            "protected_unchanged": forbidden.get("protected_unchanged"),
            "checksum_validation": not any(error.startswith("checksum_mismatch:") for error in errors),
            "review_scope": "independent isolated no-publish readiness review; no scoring or training",
        }
    (OUT / "independent_review.json").write_text(json.dumps(result, ensure_ascii=True, indent=2) + "\n")
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
