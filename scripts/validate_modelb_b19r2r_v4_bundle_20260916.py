#!/usr/bin/env python3
"""Validate the frozen research-only 2026-09-16 B19R2R V4 pre-capture bundle."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

import materialize_modelb_b19r2r_v4_bundle_20260916 as builder


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE = builder.OUT_ROOT / "pre_capture_v4"
TWII_FEATURES = {
    "TWII_ret20",
    "TWII_ret60",
    "TWII_close_vs_MA60",
    "TWII_close_vs_MA120",
    "market_volatility20",
    "market_drawdown60",
}


class ValidationError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError("B19V3V_E_JSON", str(path)) from exc
    if not isinstance(value, dict):
        raise ValidationError("B19V3V_E_JSON", str(path))
    return value


def parse_time(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError("B19V3V_E_TIME", str(value)) from exc
    if parsed.tzinfo is None:
        raise ValidationError("B19V3V_E_TIME", str(value))
    return parsed.astimezone(timezone.utc)


def check(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        raise ValidationError(code, detail)


def validate_model_binding() -> list[str]:
    check(builder.sha256(builder.MODEL_B) == builder.MODEL_B_SHA, "B19V3V_E_MODEL_HASH")
    training = read_json(builder.TRAINING_MANIFEST)
    check(
        training.get("model_id") == builder.MODEL_B_ID
        and training.get("selected_candidate_id") == 14
        and training.get("feature_count") == 78,
        "B19V3V_E_MODEL_IDENTITY",
    )
    model = joblib.load(builder.MODEL_B)
    order = list(model.booster_.feature_name())
    check(order == builder.feature_order(), "B19V3V_E_MODEL_FEATURE_ORDER")
    return order


def validate_history_source(source: dict[str, Any]) -> None:
    path = ROOT / source.get("path", "__missing__")
    check(path.is_file() and builder.sha256(path) == source.get("sha256"), "B19V3V_E_HISTORY_SOURCE_HASH", str(path))
    source_date = source.get("date")
    claimed_available_at = source.get("available_at")
    if path.name == "prediction.csv":
        check(
            path.resolve().is_relative_to((ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal").resolve()),
            "B19V3V_E_HISTORY_SOURCE_TYPE",
            str(path),
        )
        metadata_path = path.parent / "run_metadata.json"
        artifact_path = path.parent / "artifact_manifest.json"
        metadata = read_json(metadata_path)
        artifact = read_json(artifact_path)
        prediction_entry = next(
            (
                entry
                for entry in artifact.get("entries", [])
                if isinstance(entry, dict) and entry.get("key") == "prediction"
            ),
            None,
        )
        actual_available_at = metadata.get("created_at")
        check(
            source.get("availability_metadata") == builder.rel(metadata_path)
            and source.get("availability_metadata_sha256") == builder.sha256(metadata_path)
            and metadata.get("run_id") == path.parent.name
            and artifact.get("run_id") == metadata.get("run_id")
            and metadata.get("status") == "accepted"
            and artifact.get("status") == "accepted"
            and metadata.get("asof") == source_date
            and artifact.get("created_at") == actual_available_at
            and isinstance(prediction_entry, dict)
            and prediction_entry.get("sha256") == builder.sha256(path),
            "B19V3V_E_HISTORY_PREDICTION_METADATA",
            str(path),
        )
    elif path.name == "signals.csv":
        check(
            path.resolve().is_relative_to(builder.MODEL_A_SIGNAL_ROOT.resolve()),
            "B19V3V_E_HISTORY_SOURCE_TYPE",
            str(path),
        )
        metadata_path = path.parent / "manifest.json"
        metadata = read_json(metadata_path)
        actual_available_at = metadata.get("created_at")
        check(
            source.get("availability_metadata") == builder.rel(metadata_path)
            and source.get("availability_metadata_sha256") == builder.sha256(metadata_path)
            and metadata.get("model_id") == builder.MODEL_A_ID
            and metadata.get("asof") == source_date
            and metadata.get("status") == "READY"
            and metadata.get("row_count") == 150,
            "B19V3V_E_HISTORY_SIGNAL_METADATA",
            str(path),
        )
    else:
        raise ValidationError("B19V3V_E_HISTORY_SOURCE_TYPE", str(path))
    check(
        claimed_available_at == actual_available_at
        and parse_time(actual_available_at) <= parse_time(builder.CUTOFF),
        "B19V3V_E_HISTORY_AVAILABILITY",
        str(path),
    )


def validate_bundle(bundle_dir: Path) -> dict[str, Any]:
    try:
        inside = bundle_dir.resolve().is_relative_to(builder.OUT_ROOT.resolve())
    except OSError as exc:
        raise ValidationError("B19V3V_E_OUTPUT") from exc
    check(inside and bundle_dir.is_dir(), "B19V3V_E_OUTPUT", str(bundle_dir))

    attempt_path = bundle_dir / "MATERIALIZATION_ATTEMPT.json"
    exact_path = bundle_dir / "MODEL_A_EXACT50.csv"
    exact_manifest_path = bundle_dir / "MODEL_A_EXACT50_MANIFEST.json"
    feature_path = bundle_dir / "FEATURES_78_CANDIDATE.csv"
    feature_manifest_path = bundle_dir / "FEATURES_78_CANDIDATE_MANIFEST.json"
    score_path = bundle_dir / "CANDIDATE14_MODEL_B_SCORES.csv"
    score_manifest_path = bundle_dir / "CANDIDATE14_MODEL_B_SCORES_MANIFEST.json"
    required = [
        attempt_path, exact_path, exact_manifest_path, feature_path, feature_manifest_path,
        score_path, score_manifest_path,
    ]
    check(all(path.is_file() for path in required), "B19V3V_E_REQUIRED_FILE")

    attempt = read_json(attempt_path)
    exact_manifest = read_json(exact_manifest_path)
    feature_manifest = read_json(feature_manifest_path)
    score_manifest = read_json(score_manifest_path)
    source = builder.composite_binding()
    expected_shared = builder.shared_source_binding()
    for name, value in (
        ("attempt", attempt),
        ("exact", exact_manifest),
        ("features", feature_manifest),
        ("scores", score_manifest),
    ):
        check(all(value.get(key) == expected for key, expected in expected_shared.items()), "B19V4V_E_SHARED_SOURCE", name)
    order = validate_model_binding()
    check(len(order) == 78, "B19V3V_E_FEATURE_COUNT")
    check(parse_time(attempt.get("decision_cutoff")) >= parse_time(attempt.get("final_model_frozen_at")), "B19V3V_E_BEFORE_FINAL_FREEZE")
    check(
        attempt.get("asof") == builder.ASOF
        and attempt.get("source_run_id") == builder.SOURCE_RUN
        and attempt.get("decision_cutoff") == builder.CUTOFF
        and attempt.get("final_model_frozen_at") == builder.FINAL_MODEL_FROZEN_AT,
        "B19V3V_E_BUNDLE_BINDING",
    )
    check(
        attempt.get("model_a_id") == builder.MODEL_A_ID
        and attempt.get("model_id") == builder.MODEL_B_ID
        and attempt.get("model_sha256") == builder.MODEL_B_SHA
        and attempt.get("candidate_id") == 14
        and attempt.get("feature_count") == 78
        and attempt.get("feature_order_sha256") == builder.FEATURE_ORDER_SHA,
        "B19V3V_E_MODEL_BINDING",
    )

    exact = pd.read_csv(exact_path)
    check(list(exact.columns) == ["date", "instrument", "rank", "model_a_score"], "B19V3V_E_EXACT50_SCHEMA")
    check(
        len(exact) == 50
        and set(exact.date.astype(str)) == {builder.ASOF}
        and not exact.instrument.duplicated().any()
        and exact["rank"].tolist() == list(range(1, 51))
        and np.isfinite(pd.to_numeric(exact.model_a_score, errors="coerce")).all(),
        "B19V3V_E_EXACT50_SCOPE",
    )
    check(not set(exact.instrument) & builder.EXCLUDED, "B19V3V_E_EXCLUDED_SYMBOL")
    source_prediction = pd.read_csv(builder.MODEL_A_PRE_CUTOFF_PREDICTION)
    source_prediction["date"] = source_prediction.datetime.astype(str).str[:10]
    source_prediction["instrument"] = source_prediction.instrument.map(builder.normalize_symbol)
    source_prediction = source_prediction.sort_values(
        ["score", "instrument"], ascending=[False, True], kind="mergesort"
    ).head(50).reset_index(drop=True)
    check(
        exact[["date", "instrument"]].reset_index(drop=True).equals(source_prediction[["date", "instrument"]])
        and np.array_equal(exact["rank"].to_numpy(), np.arange(1, 51))
        and np.array_equal(exact.model_a_score.to_numpy(), source_prediction.score.to_numpy()),
        "B19V3V_E_EXACT50_SOURCE_PARITY",
    )
    _, availability_evidence = builder.prediction_availability(builder.MODEL_A_PRE_CUTOFF_PREDICTION)
    model_a_child = next(item for item in source["children"] if item.get("role") == "model_a_inference")
    check(
        exact_manifest.get("schema_version") == "modelb_b19r2r.v4.model_a_exact50.v1"
        and exact_manifest.get("asof") == builder.ASOF
        and exact_manifest.get("model_id") == builder.MODEL_A_ID
        and exact_manifest.get("source_run_id") == builder.SOURCE_RUN
        and exact_manifest.get("decision_cutoff") == builder.CUTOFF
        and exact_manifest.get("available_at") == model_a_child.get("available_at")
        and exact_manifest.get("primary_available_at") == model_a_child.get("primary_inference", {}).get("available_at")
        and exact_manifest.get("primary_physical_run_id") == model_a_child.get("physical_run_id")
        and parse_time(exact_manifest.get("available_at")) <= parse_time(builder.CUTOFF)
        and exact_manifest.get("pit_status") == "PIT_SAFE"
        and exact_manifest.get("row_count") == 50
        and exact_manifest.get("selection_semantics") == "model_a_rank_1_through_50_no_substitution"
        and exact_manifest.get("excluded_symbol_present") is False
        and exact_manifest.get("production_allowed") is False,
        "B19V3V_E_EXACT50_MANIFEST",
    )
    check(exact_manifest.get("artifact_sha256") == builder.sha256(exact_path), "B19V3V_E_ARTIFACT_HASH", "exact50")
    check(
        exact_manifest.get("source_artifact") == builder.rel(builder.MODEL_A_PRE_CUTOFF_PREDICTION)
        and exact_manifest.get("source_artifact_sha256") == builder.sha256(builder.MODEL_A_PRE_CUTOFF_PREDICTION)
        and exact_manifest.get("formal_model_a_artifact") == builder.rel(builder.MODEL_A_SIGNALS)
        and exact_manifest.get("formal_model_a_artifact_sha256") == builder.sha256(builder.MODEL_A_SIGNALS)
        and exact_manifest.get("availability_metadata") == availability_evidence["availability_metadata"]
        and exact_manifest.get("availability_metadata_sha256") == availability_evidence["availability_metadata_sha256"],
        "B19V3V_E_SOURCE_HASH",
        "model_a",
    )

    features = pd.read_csv(feature_path)
    expected_columns = ["date", "instrument", *order, "rsi_ready", "feature_raw_complete_78", "raw_missing_features"]
    check(list(features.columns) == expected_columns, "B19V3V_E_FEATURE_SCHEMA")
    check(len(features) == 50 and not features[["date", "instrument"]].duplicated().any(), "B19V3V_E_FEATURE_KEYS")
    exact_keys = set(map(tuple, exact[["date", "instrument"]].itertuples(index=False, name=None)))
    feature_keys = set(map(tuple, features[["date", "instrument"]].itertuples(index=False, name=None)))
    check(feature_keys == exact_keys, "B19V3V_E_KEY_MISMATCH")
    check(not builder.forbidden_columns(features.columns.astype(str).tolist()), "B19V3V_E_FUTURE_FIELD")

    numeric = features[order].apply(pd.to_numeric, errors="coerce")
    finite = np.isfinite(numeric.to_numpy(float))
    rsi_ready = features.rsi_ready.astype(str).str.lower().map({"true": True, "false": False})
    check(not rsi_ready.isna().any(), "B19V3V_E_RSI_READY")
    complete = finite.all(axis=1) & rsi_ready.to_numpy(bool)
    recorded_complete = features.feature_raw_complete_78.astype(str).str.lower().map({"true": True, "false": False})
    check(not recorded_complete.isna().any() and np.array_equal(recorded_complete.to_numpy(bool), complete), "B19V3V_E_COMPLETENESS")
    recorded_missing = features.raw_missing_features.fillna("").map(lambda value: set(filter(None, str(value).split("|"))))
    computed_missing = [set(np.asarray(order)[~row]) for row in finite]
    check(all(left == right for left, right in zip(recorded_missing, computed_missing, strict=True)), "B19V3V_E_MISSING_AUDIT")
    all_complete = bool(complete.all())
    check(
        feature_manifest.get("schema_version") == "modelb_b19r2r.v4.feature_candidate.v1"
        and feature_manifest.get("asof") == builder.ASOF
        and feature_manifest.get("source_run_id") == builder.SOURCE_RUN
        and feature_manifest.get("decision_cutoff") == builder.CUTOFF
        and feature_manifest.get("feature_columns") == order
        and feature_manifest.get("feature_order_sha256") == builder.FEATURE_ORDER_SHA
        and feature_manifest.get("feature_count") == 78
        and feature_manifest.get("all_finite") is all_complete
        and feature_manifest.get("rsi_ready") is bool(rsi_ready.all())
        and feature_manifest.get("no_fill_or_imputation") is True
        and feature_manifest.get("canonical_78f_emitted") is all_complete
        and feature_manifest.get("production_allowed") is False,
        "B19V3V_E_FEATURE_MANIFEST",
    )
    check(feature_manifest.get("artifact_sha256") == builder.sha256(feature_path), "B19V3V_E_ARTIFACT_HASH", "features")
    history_sources = feature_manifest.get("audit", {}).get("model_a_history_sources", [])
    check(bool(history_sources), "B19V3V_E_HISTORY_LINEAGE")
    check(
        {source.get("date") for source in history_sources}
        == {
            "2026-09-02", "2026-09-03", "2026-09-04", "2026-09-07", "2026-09-08", "2026-09-09",
            "2026-09-10", "2026-09-11", "2026-09-14", "2026-09-15", builder.ASOF,
        },
        "B19V3V_E_HISTORY_DATES",
    )
    for source in history_sources:
        validate_history_source(source)

    hashes = attempt.get("artifact_hashes", {})
    check(
        hashes.get("model_a_exact50") == builder.sha256(exact_path)
        and hashes.get("feature_candidate") == builder.sha256(feature_path),
        "B19V3V_E_ARTIFACT_HASH",
        "attempt",
    )
    check(
        attempt.get("accepted_ledger_event_written") is False
        and attempt.get("training_performed") is False
        and attempt.get("tuning_performed") is False
        and attempt.get("production_allowed") is False
        and attempt.get("future_or_outcome_fields_consumed") == []
        and attempt.get("tw7769_excluded") is True,
        "B19V3V_E_SAFETY_BOUNDARY",
    )
    check(attempt.get("protected_before") == attempt.get("protected_after"), "B19V3V_E_PROTECTED_DRIFT")
    check(attempt.get("protected_after") == builder.fingerprints(), "B19V3V_E_PROTECTED_DRIFT", "current")
    check(attempt.get("protected_unchanged") is True, "B19V3V_E_PROTECTED_DRIFT", "flag")

    adapter_summaries = attempt.get("adapters", {})
    for name, path, allow_blocked in (
        ("daily_price", builder.PRICE_ADAPTER, False),
        ("institutional", builder.INSTITUTIONAL_ADAPTER, False),
        ("margin", builder.MARGIN_ADAPTER, False),
    ):
        adapter = builder.validate_adapter(path, allow_blocked=allow_blocked)
        expected = {field: adapter.get(field) for field in ("acquisition_run_id", "available_at", "pit_status", "validator_status", "trade_date")}
        check(adapter_summaries.get(name) == expected, "B19V3V_E_ADAPTER_BINDING", name)

    check(all_complete, "B19V4V_E_INCOMPLETE_78F")
    if all_complete:
        check(
            attempt.get("status") == "PASS_PRECAPTURE_CANDIDATE_AWAITING_INDEPENDENT_REVIEW",
            "B19V4V_E_READY_STATUS",
        )
        check(
            attempt.get("materialization_complete") is True
            and attempt.get("eligible_for_capture") is False
            and attempt.get("capture_authorized") is False
            and score_path.is_file(),
            "B19V4V_E_SCORE_REQUIRED",
        )
        scores = pd.read_csv(score_path)
        check(list(scores.columns) == ["date", "instrument", "rank", "model_b_score"], "B19V3V_E_SCORE_SCHEMA")
        check(
            len(scores) == 50
            and scores["rank"].tolist() == list(range(1, 51))
            and np.isfinite(pd.to_numeric(scores.model_b_score, errors="coerce")).all()
            and set(map(tuple, scores[["date", "instrument"]].itertuples(index=False, name=None))) == exact_keys,
            "B19V3V_E_SCORE_SCOPE",
        )
        check(hashes.get("candidate14_scores") == builder.sha256(score_path), "B19V3V_E_ARTIFACT_HASH", "scores")
        check(
            score_manifest.get("schema_version") == "modelb_b19r2r.v4.candidate14_model_b_scores.v1"
            and score_manifest.get("artifact_sha256") == builder.sha256(score_path)
            and score_manifest.get("model_id") == builder.MODEL_B_ID
            and score_manifest.get("model_sha256") == builder.MODEL_B_SHA
            and score_manifest.get("candidate_id") == 14
            and score_manifest.get("feature_count") == 78
            and score_manifest.get("feature_order_sha256") == builder.FEATURE_ORDER_SHA
            and score_manifest.get("exact50_artifact_sha256") == builder.sha256(exact_path)
            and score_manifest.get("feature_artifact_sha256") == builder.sha256(feature_path)
            and score_manifest.get("excluded_symbol_present") is False
            and score_manifest.get("production_allowed") is False,
            "B19V4V_E_SCORE_MANIFEST",
        )

    check(
        bundle_dir.stat().st_mode & 0o777 == 0o555
        and all(path.stat().st_mode & 0o777 == 0o444 for path in bundle_dir.iterdir()),
        "B19V4V_E_FROZEN_MODE",
    )

    return {
        "schema_version": "modelb_b19r2r.v4.bundle_validation.v1",
        "validated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "PASS",
        "bundle_status": attempt["status"],
        "eligible_for_capture": attempt["eligible_for_capture"],
        "rows": len(features),
        "complete_78_rows": int(complete.sum()),
        "score_artifact_present": score_path.is_file(),
        "accepted_ledger_event_written": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", default=str(DEFAULT_BUNDLE))
    args = parser.parse_args()
    try:
        result = validate_bundle(Path(args.bundle))
    except (ValidationError, builder.MaterializationError) as exc:
        print(json.dumps({"status": "FAIL", "error_code": exc.code, "detail": exc.detail}, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
