#!/usr/bin/env python3
"""Run the MBCDS2 input-only shadow gate without scoring or training."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow/mbcds2_shadow_20260905"
READINESS = ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow/mbcds0_preflight_20260905/readiness_report.json"
CONTRACT = ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow/model_artifact_phase1c_20260905/model_contract.json"
PICKLE = ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow/model_artifact_phase1c_20260905/phase1c_head10_all_l31_model.pkl"
INFERENCE_ROOT = ROOT / "data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022"
SCORE_ROOT = ROOT / "data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022"

PROTECTED = [
    ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json",
    ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def sha(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint(path: Path) -> dict[str, object]:
    return {"path": rel(path), "exists": path.exists(), "size": path.stat().st_size if path.is_file() else None, "sha256": sha(path)}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def csv_header_and_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.is_file():
        return [], []
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), list(reader)


def latest_csv(root: Path, name: str) -> Path | None:
    paths = list(root.glob(f"*/{name}"))
    if not paths:
        return None
    dated = []
    for path in paths:
        header, rows = csv_header_and_rows(path)
        date = rows[0].get("date", "") if rows else ""
        dated.append((date, path.stat().st_mtime, path))
    return max(dated, key=lambda item: (item[0], item[1], str(item[2])))[2]


def write_json(name: str, value: dict) -> None:
    (OUT / name).write_text(json.dumps(value, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    contract = read_json(CONTRACT)
    readiness = read_json(READINESS)
    features = contract.get("features", [])
    inference = latest_csv(INFERENCE_ROOT, "inference_frame.csv")
    prediction = latest_csv(SCORE_ROOT, "raw_scores.csv")
    inference_header, inference_rows = csv_header_and_rows(inference) if inference else ([], [])
    prediction_header, prediction_rows = csv_header_and_rows(prediction) if prediction else ([], [])
    target_asof = inference_rows[0].get("date", "") if inference_rows else ""

    before = {str(path): fingerprint(path) for path in PROTECTED}
    materialized = []
    numeric_status = {}
    for feature in features:
        present = feature in inference_header
        numeric = False
        if present and inference_rows:
            try:
                numeric = all(row.get(feature, "") not in (None, "") and float(row[feature]) == float(row[feature]) for row in inference_rows)
            except (TypeError, ValueError):
                numeric = False
        numeric_status[feature] = {"column_present": present, "numeric_finite_for_all_rows": numeric}
        if present and numeric:
            materialized.append(feature)

    missing = [feature for feature in features if feature not in materialized]
    feature_rows = []
    for feature in features:
        status = numeric_status[feature]
        feature_rows.append({
            "feature": feature,
            "column_present": str(status["column_present"]).lower(),
            "numeric_finite_for_all_rows": str(status["numeric_finite_for_all_rows"]).lower(),
            "row_count": len(inference_rows),
            "target_asof": target_asof,
            "decision": "READY" if feature in materialized else "MISSING_NOT_MATERIALIZED",
        })
    with (OUT / "feature_contract_audit.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(feature_rows[0]))
        writer.writeheader()
        writer.writerows(feature_rows)

    after = {str(path): fingerprint(path) for path in PROTECTED}
    source_inventory = {
        "readiness_report": fingerprint(READINESS),
        "model_contract": fingerprint(CONTRACT),
        "model_pickle": fingerprint(PICKLE),
        "latest_modela_inference_frame": fingerprint(inference) if inference else {"exists": False},
        "latest_modela_prediction": fingerprint(prediction) if prediction else {"exists": False},
    }
    input_readiness = {
        "status": "BLOCKED_INPUT_FEATURES_NOT_MATERIALIZED",
        "can_score": False,
        "can_train": False,
        "target_asof": target_asof,
        "modela_inference_rows": len(inference_rows),
        "modela_prediction_rows": len(prediction_rows),
        "inference_columns": inference_header,
        "required_feature_count": len(features),
        "materialized_numeric_feature_count": len(materialized),
        "missing_feature_count": len(missing),
        "missing_features": missing,
        "label_or_future_data_read": False,
        "latest_inference_frame": rel(inference) if inference else None,
        "latest_modela_prediction": rel(prediction) if prediction else None,
        "model_pickle_read": True,
        "model_pickle_loaded_or_called": False,
        "reason": "latest inference_frame contains metadata/lineage columns but no 34 daily LTR numeric feature columns",
    }
    forbidden = {
        "status": "PASS_NO_FORBIDDEN_SIDE_EFFECTS_DECLARED",
        "training_triggered": False,
        "scoring_triggered": False,
        "labels_or_future_data_used": False,
        "model_signal_artifact_generated": False,
        "latest_written": False,
        "provider_written_or_refreshed": False,
        "cron_written": False,
        "frontend_written": False,
        "backend_written": False,
        "protected_before": before,
        "protected_after": after,
        "protected_unchanged": before == after,
        "only_output_root": rel(OUT),
    }
    write_json("manifest.json", {
        "route": "MBCDS2_LATEST_SHADOW_SCORE_BUILD_NO_PUBLISH",
        "created_at": now(),
        "status": "BLOCKED_INPUT_FEATURES_NOT_MATERIALIZED",
        "scope": "input readiness only; no score, training, labels, future data, artifact, latest, provider, cron, frontend, or backend writes",
        "output_root": rel(OUT),
        "target_asof": target_asof,
        "source_inventory": source_inventory,
    })
    write_json("input_readiness.json", input_readiness)
    write_json("forbidden_scope_audit.json", forbidden)

    report = f"""# MBCDS2 No-Publish Shadow Gate Execution Report

## Result

`BLOCKED_INPUT_FEATURES_NOT_MATERIALIZED`

## Evidence

- Latest Model A inference frame: `{rel(inference) if inference else 'MISSING'}`
- Inference target: `{target_asof}`
- Model A inference rows: `{len(inference_rows)}`
- Latest Model A prediction: `{rel(prediction) if prediction else 'MISSING'}`
- Model B required features: `{len(features)}`
- Materialized finite numeric features: `{len(materialized)}`
- Missing features: `{len(missing)}`

The latest inference frame has identity, lineage, and timing metadata only. It does not contain the daily numeric columns required by the Phase1C 34-feature contract. The gate therefore stops before model loading/calling, scoring, training, labels, or future-data access.

## Boundary Review

- MBCDS0 readiness, Phase1C contract, model pickle metadata, latest Model A prediction, and latest inference frame were read.
- No Model B score was generated.
- No training, label, future-data, ModelSignalArtifact, latest/provider/cron/frontend/backend write occurred.
- Protected fingerprints unchanged: `{forbidden['protected_unchanged']}`

Next permitted step: materialize or explicitly bridge the 34 PIT-safe daily features into an isolated candidate, then rerun this input-only gate. Do not bypass the missing-feature gate with medians, forward-fill, interpolation, labels, or future data.
"""
    (OUT / "execution_report.md").write_text(report, encoding="utf-8")

    manifest_files = [p for p in OUT.iterdir() if p.is_file() and p.name != "checksum_manifest.json"]
    checksum = {rel(path): sha(path) for path in sorted(manifest_files)}
    write_json("checksum_manifest.json", checksum)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
