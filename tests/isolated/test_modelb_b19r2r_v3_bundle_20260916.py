from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


builder = load_module(
    "materialize_modelb_b19r2r_v3_bundle_20260916",
    "scripts/materialize_modelb_b19r2r_v3_bundle_20260916.py",
)
validator = load_module(
    "validate_modelb_b19r2r_v3_bundle_20260916",
    "scripts/validate_modelb_b19r2r_v3_bundle_20260916.py",
)

TWII_FEATURES = [
    "TWII_ret20",
    "TWII_ret60",
    "TWII_close_vs_MA60",
    "TWII_close_vs_MA120",
    "market_volatility20",
    "market_drawdown60",
]
FEATURES = [f"feature_{index:02d}" for index in range(72)] + TWII_FEATURES


class FakeModel:
    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        return np.arange(len(frame), dtype=float)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


@pytest.fixture
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    output_root = tmp_path / "isolated"
    out = output_root / "pre_capture_v1"
    source_signal = tmp_path / "signals.csv"
    source_signal.write_text("date,instrument\n", encoding="utf-8")
    source_prediction = tmp_path / "prediction.csv"
    pd.DataFrame(
        {
            "datetime": [builder.ASOF] * 150,
            "instrument": [f"TW{1000 + index}" for index in range(150)],
            "score": np.linspace(1.0, -1.0, 150),
        }
    ).to_csv(source_prediction, index=False)
    history_root = tmp_path / "model_a_signals"
    history_entries = []
    history_days = [
        "2026-09-02", "2026-09-03", "2026-09-04", "2026-09-07", "2026-09-08", "2026-09-09",
        "2026-09-10", "2026-09-11", "2026-09-14", "2026-09-15", builder.ASOF,
    ]
    for day in history_days:
        run = history_root / f"run_{day.replace('-', '')}"
        run.mkdir(parents=True)
        history_source = run / "signals.csv"
        pd.DataFrame(
            {"date": [day] * 150, "instrument": [f"TW{1000 + index}" for index in range(150)], "raw_score": 1.0}
        ).to_csv(history_source, index=False)
        history_metadata = run / "manifest.json"
        available_at = f"{day}T12:00:00+00:00"
        write_json(
            history_metadata,
            {
                "model_id": builder.MODEL_A_ID,
                "asof": day,
                "status": "READY",
                "row_count": 150,
                "created_at": available_at,
            },
        )
        history_entries.append(
            {
                "date": day,
                "path": str(history_source),
                "sha256": builder.sha256(history_source),
                "available_at": available_at,
                "availability_metadata": str(history_metadata),
                "availability_metadata_sha256": builder.sha256(history_metadata),
            }
        )
    protected = []
    for index in range(3):
        path = tmp_path / f"protected_{index}.json"
        path.write_text(f"{index}\n", encoding="utf-8")
        protected.append(path)

    adapters = {}
    for name in ("price", "institutional", "margin", "twii"):
        path = tmp_path / f"{name}.adapter.json"
        value = {
            "acquisition_run_id": builder.SOURCE_RUN,
            "target_asof": builder.ASOF,
            "available_at": "2026-09-16T12:00:00+00:00",
            "pit_status": "PASS",
            "validator_status": "PASS",
            "trade_date": builder.ASOF,
        }
        if name == "twii":
            value.update(
                pit_status="BLOCKED_PUBLICATION_AND_AVAILABILITY_UNPROVEN",
                validator_status="BLOCKED_PROVIDER_SCHEMA",
                trade_date="",
            )
        write_json(path, value)
        adapters[name] = path

    exact = pd.DataFrame(
        {
            "date": [builder.ASOF] * 50,
            "instrument": [f"TW{1000 + index}" for index in range(50)],
            "rank": list(range(1, 51)),
            "model_a_score": np.linspace(1.0, -1.0, 150)[:50],
        }
    )
    feature_frame = exact[["date", "instrument"]].copy()
    for name in FEATURES:
        feature_frame[name] = np.nan if name in TWII_FEATURES else 1.0
    feature_frame["rsi_ready"] = True
    feature_frame["feature_raw_complete_78"] = False
    feature_frame["raw_missing_features"] = "|".join(TWII_FEATURES)
    feature_audit = {
        "rows": 50,
        "finite_78_rows": 0,
        "rsi_ready_rows": 50,
        "complete_78_rows": 0,
        "missing_feature_counts": {name: (50 if name in TWII_FEATURES else 0) for name in FEATURES},
        "nontrading_placeholder_removed_before_rolling": True,
        "twii": {
            "adapter_pit_status": "BLOCKED_PUBLICATION_AND_AVAILABILITY_UNPROVEN",
            "adapter_validator_status": "BLOCKED_PROVIDER_SCHEMA",
            "adapter_trade_date": "",
            "target_weighted_index_rows": 0,
        },
        "model_a_history_sources": history_entries,
    }

    monkeypatch.setattr(builder, "OUT_ROOT", output_root)
    monkeypatch.setattr(builder, "PROTECTED", tuple(protected))
    monkeypatch.setattr(builder, "PRICE_ADAPTER", adapters["price"])
    monkeypatch.setattr(builder, "INSTITUTIONAL_ADAPTER", adapters["institutional"])
    monkeypatch.setattr(builder, "MARGIN_ADAPTER", adapters["margin"])
    monkeypatch.setattr(builder, "TWII_ADAPTER", adapters["twii"])
    monkeypatch.setattr(builder, "MODEL_A_SIGNALS", source_signal)
    monkeypatch.setattr(builder, "MODEL_A_PRE_CUTOFF_PREDICTION", source_prediction)
    monkeypatch.setattr(builder, "MODEL_A_SIGNAL_ROOT", history_root)
    monkeypatch.setattr(builder, "feature_order", lambda: FEATURES)
    monkeypatch.setattr(
        builder,
        "model_a_exact50",
        lambda: (
            exact.copy(),
            {
                "available_at": "2026-09-16T14:57:25+00:00",
                "availability_metadata": str(history_entries[-1]["availability_metadata"]),
                "availability_metadata_sha256": str(history_entries[-1]["availability_metadata_sha256"]),
            },
        ),
    )
    monkeypatch.setattr(
        builder,
        "prediction_availability",
        lambda unused: (
            "2026-09-16T14:57:25+00:00",
            {
                "availability_metadata": builder.rel(history_metadata),
                "availability_metadata_sha256": str(history_entries[-1]["availability_metadata_sha256"]),
                "artifact_manifest": str(history_entries[-1]["availability_metadata"]),
                "artifact_manifest_sha256": str(history_entries[-1]["availability_metadata_sha256"]),
            },
        ),
    )
    monkeypatch.setattr(builder, "assemble_features", lambda unused: (feature_frame.copy(), feature_audit.copy()))
    monkeypatch.setattr(builder, "model_identity", lambda: (FakeModel(), FEATURES))
    monkeypatch.setattr(validator, "validate_model_binding", lambda: FEATURES)
    return SimpleNamespace(
        out=out,
        output_root=output_root,
        exact=exact,
        features=feature_frame,
        adapters=adapters,
        protected=protected,
    )


def test_blocked_twii_materializes_auditable_bundle_without_scores(isolated: SimpleNamespace) -> None:
    result = builder.materialize(isolated.out)
    assert result["status"] == "NOT_ELIGIBLE_BLOCKED_TWII"
    assert result["eligible_for_capture"] is False
    assert not (isolated.out / "CANDIDATE14_MODEL_B_SCORES.csv").exists()
    checked = validator.validate_bundle(isolated.out)
    assert checked["status"] == "PASS"
    assert checked["complete_78_rows"] == 0
    assert checked["score_artifact_present"] is False


def test_cross_run_adapter_is_rejected_before_output(isolated: SimpleNamespace) -> None:
    adapter = builder.read_json(isolated.adapters["margin"])
    adapter["acquisition_run_id"] = "another.run"
    write_json(isolated.adapters["margin"], adapter)
    with pytest.raises(builder.MaterializationError) as captured:
        builder.materialize(isolated.out)
    assert captured.value.code == "B19V3M_E_CROSS_RUN"
    assert not isolated.out.exists()


def test_cutoff_before_final_model_freeze_is_rejected(isolated: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(builder, "CUTOFF", "2026-09-16T13:15:59+00:00")
    with pytest.raises(builder.MaterializationError) as captured:
        builder.materialize(isolated.out)
    assert captured.value.code == "B19V3M_E_BEFORE_FINAL_MODEL_FREEZE"
    assert not isolated.out.exists()


def test_key_mismatch_is_rejected() -> None:
    expected = pd.DataFrame({"date": [builder.ASOF] * 2, "instrument": ["TW1", "TW2"]})
    actual = pd.DataFrame({"date": [builder.ASOF], "instrument": ["TW1"]})
    with pytest.raises(builder.MaterializationError) as captured:
        builder.require_exact_keys(expected, actual, ["date", "instrument"], "price")
    assert captured.value.code == "B19V3M_E_KEY_MISMATCH"


def test_future_or_outcome_normalized_field_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "normalized.json"
    write_json(path, {"records": [{"trade_date": builder.ASOF, "symbol": "2330", "future_return_10d": 0.5}]})
    with pytest.raises(builder.MaterializationError) as captured:
        builder.load_records(path)
    assert captured.value.code == "B19V3M_E_FUTURE_FIELD"


def test_model_a_future_field_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = tmp_path / "manifest.json"
    prediction = tmp_path / "prediction.csv"
    write_json(
        manifest,
        {
            "asof": builder.ASOF,
            "model_id": builder.MODEL_A_ID,
            "source_acquisition_run_id": builder.SOURCE_RUN,
            "decision_cutoff": builder.CUTOFF,
        },
    )
    rows = pd.DataFrame(
        {
            "datetime": [builder.ASOF] * 150,
            "instrument": [f"TW{1000 + index}" for index in range(150)],
            "score": np.linspace(1, 0, 150),
            "label_10d": 1,
        }
    )
    rows.to_csv(prediction, index=False)
    monkeypatch.setattr(builder, "MODEL_A_MANIFEST", manifest)
    monkeypatch.setattr(builder, "MODEL_A_PRE_CUTOFF_PREDICTION", prediction)
    monkeypatch.setattr(builder, "prediction_availability", lambda unused: ("2026-09-16T14:57:25+00:00", {}))
    with pytest.raises(builder.MaterializationError) as captured:
        builder.model_a_exact50()
    assert captured.value.code == "B19V3M_E_FUTURE_FIELD"


def test_backdated_prediction_availability_is_rejected(tmp_path: Path) -> None:
    run = tmp_path / "option_c_daily_signal_20260916_20260916T145733Z"
    run.mkdir()
    prediction = run / "prediction.csv"
    prediction.write_text("datetime,instrument,score\n2026-09-16,TW2330,1\n", encoding="utf-8")
    write_json(
        run / "run_metadata.json",
        {"run_id": run.name, "created_at": "2026-09-16T14:57:46+00:00", "status": "accepted", "asof": builder.ASOF},
    )
    write_json(
        run / "artifact_manifest.json",
        {
            "run_id": run.name,
            "created_at": "2026-09-16T14:57:46+00:00",
            "status": "accepted",
            "entries": [{"key": "prediction", "sha256": builder.sha256(prediction)}],
        },
    )
    with pytest.raises(builder.MaterializationError) as captured:
        builder.prediction_availability(prediction)
    assert captured.value.code == "B19V3M_E_PREDICTION_AVAILABILITY"


def test_validator_rejects_backdated_model_signal_claim(isolated: SimpleNamespace) -> None:
    builder.materialize(isolated.out)
    path = isolated.out / "FEATURES_78_CANDIDATE_MANIFEST.json"
    manifest = builder.read_json(path)
    manifest["audit"]["model_a_history_sources"][0]["available_at"] = "2000-01-01T00:00:00+00:00"
    write_json(path, manifest)
    with pytest.raises(validator.ValidationError) as captured:
        validator.validate_bundle(isolated.out)
    assert captured.value.code == "B19V3V_E_HISTORY_AVAILABILITY"


def test_validator_rejects_backdated_prediction_claim(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    monkeypatch.setattr(builder, "ROOT", tmp_path)
    run = tmp_path / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260915_20260915T120000Z"
    run.mkdir(parents=True)
    prediction = run / "prediction.csv"
    prediction.write_text("datetime,instrument,score\n2026-09-15,TW2330,1\n", encoding="utf-8")
    metadata = run / "run_metadata.json"
    artifact = run / "artifact_manifest.json"
    write_json(
        metadata,
        {"run_id": run.name, "created_at": "2026-09-15T12:00:00+00:00", "status": "accepted", "asof": "2026-09-15"},
    )
    write_json(
        artifact,
        {
            "run_id": run.name,
            "created_at": "2026-09-15T12:00:00+00:00",
            "status": "accepted",
            "entries": [{"key": "prediction", "sha256": builder.sha256(prediction)}],
        },
    )
    source = {
        "date": "2026-09-15",
        "path": builder.rel(prediction),
        "sha256": builder.sha256(prediction),
        "available_at": "2000-01-01T00:00:00+00:00",
        "availability_metadata": builder.rel(metadata),
        "availability_metadata_sha256": builder.sha256(metadata),
    }
    with pytest.raises(validator.ValidationError) as captured:
        validator.validate_history_source(source)
    assert captured.value.code == "B19V3V_E_HISTORY_AVAILABILITY"


def test_model_hash_identity_and_feature_order_mismatches_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(builder, "sha256", lambda unused: "wrong")
    with pytest.raises(builder.MaterializationError) as captured:
        builder.model_identity()
    assert captured.value.code == "B19V3M_E_MODEL_HASH"

    monkeypatch.setattr(builder, "sha256", lambda unused: builder.MODEL_B_SHA)
    monkeypatch.setattr(builder, "read_json", lambda unused: {"model_id": "wrong", "selected_candidate_id": 14, "feature_count": 78})
    with pytest.raises(builder.MaterializationError) as captured:
        builder.model_identity()
    assert captured.value.code == "B19V3M_E_MODEL_IDENTITY"

    monkeypatch.setattr(
        builder,
        "read_json",
        lambda unused: {"model_id": builder.MODEL_B_ID, "selected_candidate_id": 14, "feature_count": 78},
    )
    monkeypatch.setattr(builder.joblib, "load", lambda unused: SimpleNamespace(booster_=SimpleNamespace(feature_name=lambda: ["wrong"])))
    monkeypatch.setattr(builder, "feature_order", lambda: FEATURES)
    with pytest.raises(builder.MaterializationError) as captured:
        builder.model_identity()
    assert captured.value.code == "B19V3M_E_MODEL_FEATURE_ORDER"


def test_nonfinite_feature_tamper_is_rejected_even_with_rehashed_manifests(isolated: SimpleNamespace) -> None:
    builder.materialize(isolated.out)
    path = isolated.out / "FEATURES_78_CANDIDATE.csv"
    frame = pd.read_csv(path)
    frame.loc[0, "feature_00"] = np.nan
    frame.loc[0, "raw_missing_features"] += "|feature_00"
    frame.to_csv(path, index=False)
    digest = builder.sha256(path)
    manifest_path = isolated.out / "FEATURES_78_CANDIDATE_MANIFEST.json"
    manifest = builder.read_json(manifest_path)
    manifest["artifact_sha256"] = digest
    write_json(manifest_path, manifest)
    attempt_path = isolated.out / "MATERIALIZATION_ATTEMPT.json"
    attempt = builder.read_json(attempt_path)
    attempt["artifact_hashes"]["feature_candidate"] = digest
    write_json(attempt_path, attempt)
    with pytest.raises(validator.ValidationError) as captured:
        validator.validate_bundle(isolated.out)
    assert captured.value.code == "B19V3V_E_UNEXPECTED_MISSING_FEATURE"


def test_artifact_hash_tamper_is_rejected(isolated: SimpleNamespace) -> None:
    builder.materialize(isolated.out)
    with (isolated.out / "MODEL_A_EXACT50.csv").open("a", encoding="utf-8") as stream:
        stream.write("2026-09-16,TW9999,51,0\n")
    with pytest.raises(validator.ValidationError) as captured:
        validator.validate_bundle(isolated.out)
    assert captured.value.code in {"B19V3V_E_EXACT50_SCOPE", "B19V3V_E_ARTIFACT_HASH"}


def test_protected_fingerprint_drift_is_rejected(isolated: SimpleNamespace) -> None:
    builder.materialize(isolated.out)
    isolated.protected[0].write_text("changed\n", encoding="utf-8")
    with pytest.raises(validator.ValidationError) as captured:
        validator.validate_bundle(isolated.out)
    assert captured.value.code == "B19V3V_E_PROTECTED_DRIFT"


def test_output_escape_and_no_overwrite(isolated: SimpleNamespace, tmp_path: Path) -> None:
    with pytest.raises(builder.MaterializationError) as captured:
        builder.materialize(tmp_path / "outside")
    assert captured.value.code == "B19V3M_E_OUTPUT_ESCAPE"
    builder.materialize(isolated.out)
    with pytest.raises(builder.MaterializationError) as captured:
        builder.materialize(isolated.out)
    assert captured.value.code == "B19V3M_E_NO_OVERWRITE"


def test_no_feature_imputation_in_blocked_artifact(isolated: SimpleNamespace) -> None:
    builder.materialize(isolated.out)
    frame = pd.read_csv(isolated.out / "FEATURES_78_CANDIDATE.csv")
    assert frame[TWII_FEATURES].isna().all().all()
    manifest = builder.read_json(isolated.out / "FEATURES_78_CANDIDATE_MANIFEST.json")
    assert manifest["no_fill_or_imputation"] is True
    assert manifest["canonical_78f_emitted"] is False


def test_model_signal_history_fills_days_without_prediction_csv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    history_path = tmp_path / "history.parquet"
    pd.DataFrame(
        [{"date": "2026-09-01", "instrument": "TW1000", "model_a_raw_score": 0.1, "full_qlib_rank": 1}]
    ).to_parquet(history_path, index=False)
    signal_root = tmp_path / "signals"
    prediction_root = tmp_path / "qlib_pipeline/data_tw/experiments/option_c_daily_signal"
    days = [
        "2026-09-02", "2026-09-03", "2026-09-04", "2026-09-07", "2026-09-08", "2026-09-09",
        "2026-09-10", "2026-09-11", "2026-09-14", "2026-09-15", builder.ASOF,
    ]
    for day in days:
        if day == builder.ASOF:
            continue
        run = signal_root / f"run_{day.replace('-', '')}"
        run.mkdir(parents=True)
        pd.DataFrame(
            {
                "date": [day] * 150,
                "instrument": [f"TW{1000 + index}" for index in range(150)],
                "raw_score": np.linspace(1.0, 0.0, 150),
            }
        ).to_csv(run / "signals.csv", index=False)
        manifest = {
            "model_id": builder.MODEL_A_ID,
            "asof": day,
            "status": "READY",
            "row_count": 150,
            "created_at": f"{day}T12:00:00+00:00",
        }
        if day == builder.ASOF:
            manifest["decision_cutoff"] = builder.CUTOFF
        write_json(run / "manifest.json", manifest)
    monkeypatch.setattr(builder, "MODEL_A_HISTORY", history_path)
    monkeypatch.setattr(builder, "MODEL_A_SIGNAL_ROOT", signal_root)
    monkeypatch.setattr(builder, "ROOT", tmp_path)
    current_run = prediction_root / f"option_c_daily_signal_{builder.ASOF.replace('-', '')}_20260916T145712Z"
    current_run.mkdir(parents=True)
    current_prediction = current_run / "prediction.csv"
    pd.DataFrame(
        {
            "datetime": [builder.ASOF] * 150,
            "instrument": [f"TW{1000 + index}" for index in range(150)],
            "score": np.linspace(1.0, 0.0, 150),
        }
    ).to_csv(current_prediction, index=False)
    write_json(
        current_run / "run_metadata.json",
        {"run_id": current_run.name, "created_at": "2026-09-16T14:57:25+00:00", "status": "accepted", "asof": builder.ASOF},
    )
    write_json(
        current_run / "artifact_manifest.json",
        {
            "run_id": current_run.name,
            "created_at": "2026-09-16T14:57:25+00:00",
            "status": "accepted",
            "entries": [{"key": "prediction", "sha256": builder.sha256(current_prediction)}],
        },
    )
    monkeypatch.setattr(builder, "MODEL_A_PRE_CUTOFF_PREDICTION", current_prediction)
    history, lineage = builder.prediction_history()
    assert len(history) == 1 + 11 * 150
    assert len(lineage) == 11
    assert {item["date"] for item in lineage} == set(days)
