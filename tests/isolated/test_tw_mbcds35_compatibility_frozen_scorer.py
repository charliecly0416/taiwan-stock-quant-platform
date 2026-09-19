from __future__ import annotations

import hashlib
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import run_tw_mbcds35_compatibility_frozen_scorer as scorer  # noqa: E402
import tw_mbcds35_signal_time_regime as regime_contract  # noqa: E402


class DummyModel:
    def predict(self, frame):
        return frame.sum(axis=1).to_numpy()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def scoring_case(tmp_path, monkeypatch):
    isolated = tmp_path / "isolated"
    monkeypatch.setattr(scorer, "ISOLATED_ROOT", isolated)
    features = [*regime_contract.REQUIRED_FIELDS, *[f"f{i:02d}" for i in range(31)]]
    model, contract, medians = tmp_path / "model.pkl", tmp_path / "contract.json", tmp_path / "medians.json"
    model.write_bytes(pickle.dumps(DummyModel()))
    contract.write_text(json.dumps({"identity": {"model_id": scorer.MODEL_ID, "candidate_id": scorer.CANDIDATE_ID}, "features": features}), encoding="utf-8")
    medians.write_text(json.dumps({name: 0.0 for name in features}), encoding="utf-8")
    monkeypatch.setattr(scorer, "EXPECTED", {scorer.MODEL: digest(model), scorer.CONTRACT: digest(contract), scorer.MEDIANS: digest(medians)})
    asof, run_id = "2026-09-08", "run-1"
    model_a = tmp_path / "model_a.csv"
    pd.DataFrame({"date": [asof] * 150, "instrument": [f"TW{i:04d}" for i in range(150)],
                  "full_qlib_rank": range(1, 151), "raw_score": np.arange(150, 0, -1)}).to_csv(model_a, index=False)
    frame = tmp_path / "features.csv"
    values = pd.DataFrame(np.ones((150, 34)), columns=features)
    values["TWII_close_vs_MA60"] = 0.01
    values["TWII_ret20"] = 0.02
    values["market_drawdown60"] = -0.01
    values.insert(0, "instrument", [f"TW{i:04d}" for i in range(150)])
    values.insert(0, "date", asof)
    values.to_csv(frame, index=False)
    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps({
        "status": "PASS", "asof": asof, "acquisition_run_id": run_id,
        "combined_available_at": "2026-09-08T10:00:00+00:00",
        "decision_cutoff": "2026-09-08T10:30:00+00:00",
    }), encoding="utf-8")
    regime_path = tmp_path / "signal_time_regime.json"
    regime_path.write_text(json.dumps({
        "schema_version": "mbcds35.signal_time_regime.v1", "asof": asof,
        "decision_cutoff": "2026-09-08T10:30:00+00:00",
        "source_available_at": "2026-09-08T10:00:00+00:00", "source_run_id": run_id,
        "regime": "risk_on", "feature_values": {
            "TWII_close_vs_MA60": 0.01, "TWII_ret20": 0.02, "market_drawdown60": -0.01,
        },
        "regime_contract": str(regime_contract.DEFAULT_CONTRACT),
        "regime_contract_sha256": regime_contract.sha256(regime_contract.DEFAULT_CONTRACT),
        "feature_frame": str(frame), "feature_frame_sha256": digest(frame),
        "signal_time_only": True, "outcome_fields_consumed": [],
        "missing_rule": "fail_closed_no_classification_no_fill", "production_allowed": False,
    }), encoding="utf-8")
    manifest = tmp_path / "feature_manifest.json"
    manifest.write_text(json.dumps({
        "status": "PASS", "asof": asof, "source_run_id": run_id,
        "decision_cutoff": "2026-09-08T10:30:00+00:00",
        "feature_frame_sha256": digest(frame), "feature_order": features, "can_score": True,
        "model_a_signals_sha256": digest(model_a), "source_ledger_sha256": digest(ledger),
        "signal_time_regime": "risk_on", "signal_time_regime_artifact": str(regime_path),
        "signal_time_regime_artifact_sha256": digest(regime_path),
        "signal_time_regime_contract_sha256": regime_contract.sha256(regime_contract.DEFAULT_CONTRACT),
    }), encoding="utf-8")
    kwargs = dict(asof=asof, feature_frame=frame, feature_manifest=manifest, model_a_signals=model_a,
                  source_ledger=ledger, output=isolated / "run", model=model, contract=contract, medians=medians)
    return kwargs


def test_scores_exact_model_a_top50(scoring_case):
    result = scorer.score(**scoring_case)
    rows = pd.read_csv(scoring_case["output"] / "model_b_shadow_signals.csv")
    assert len(rows) == 50
    assert set(rows.instrument) == {f"TW{i:04d}" for i in range(50)}
    assert result["percentile_direction"] == "higher_score_is_better"
    assert result["missing_rule"] == "fail_closed_no_fill"
    assert result["candidate_id"] == scorer.CANDIDATE_ID
    assert result["signal_time_regime"] == "risk_on"
    assert "score_head10_all_l31_alpha0.7_top50_only" in result["candidate_aliases"]
    expected = 0.7 * rows["qlib_percentile"] + 0.3 * rows["model_b_percentile"]
    assert np.allclose(rows["buy_score"], expected)


@pytest.mark.parametrize("mutation, message", [
    ("nan", "feature_missing_nan_or_infinite"),
    ("order", "feature_order_mismatch"),
    ("run", "same_run_mismatch"),
])
def test_contract_fail_closed(scoring_case, mutation, message):
    if mutation == "nan":
        frame = pd.read_csv(scoring_case["feature_frame"])
        frame.loc[0, "f00"] = np.nan
        frame.to_csv(scoring_case["feature_frame"], index=False)
        regime_path = Path(json.loads(scoring_case["feature_manifest"].read_text())["signal_time_regime_artifact"])
        regime = json.loads(regime_path.read_text())
        regime["feature_frame_sha256"] = digest(scoring_case["feature_frame"])
        regime_path.write_text(json.dumps(regime), encoding="utf-8")
        manifest = json.loads(scoring_case["feature_manifest"].read_text())
        manifest["feature_frame_sha256"] = digest(scoring_case["feature_frame"])
        manifest["signal_time_regime_artifact_sha256"] = digest(regime_path)
        scoring_case["feature_manifest"].write_text(json.dumps(manifest), encoding="utf-8")
    elif mutation == "order":
        manifest = json.loads(scoring_case["feature_manifest"].read_text())
        manifest["feature_order"] = list(reversed(manifest["feature_order"]))
        scoring_case["feature_manifest"].write_text(json.dumps(manifest), encoding="utf-8")
    else:
        manifest = json.loads(scoring_case["feature_manifest"].read_text())
        manifest["source_run_id"] = "other"
        scoring_case["feature_manifest"].write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(scorer.ScoringError, match=message):
        scorer.score(**scoring_case)


def test_model_checksum_drift_is_blocked(scoring_case):
    scoring_case["model"].write_bytes(scoring_case["model"].read_bytes() + b"x")
    with pytest.raises(scorer.ScoringError, match="checksum_mismatch"):
        scorer.score(**scoring_case)


def test_source_available_after_cutoff_is_blocked(scoring_case):
    ledger = json.loads(scoring_case["source_ledger"].read_text())
    ledger["combined_available_at"] = "2026-09-08T11:00:00+00:00"
    scoring_case["source_ledger"].write_text(json.dumps(ledger), encoding="utf-8")
    manifest = json.loads(scoring_case["feature_manifest"].read_text())
    manifest["source_ledger_sha256"] = digest(scoring_case["source_ledger"])
    scoring_case["feature_manifest"].write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(scorer.ScoringError, match="source_available_at_or_cutoff_binding_invalid"):
        scorer.score(**scoring_case)


def test_model_a_replaced_after_feature_build_is_blocked(scoring_case):
    model_a = pd.read_csv(scoring_case["model_a_signals"])
    model_a.loc[0, "raw_score"] += 1
    model_a.to_csv(scoring_case["model_a_signals"], index=False)
    with pytest.raises(scorer.ScoringError, match="model_a_signals_checksum_mismatch"):
        scorer.score(**scoring_case)


def test_source_ledger_replaced_after_feature_build_is_blocked(scoring_case):
    ledger = json.loads(scoring_case["source_ledger"].read_text())
    ledger["extra"] = "mutation"
    scoring_case["source_ledger"].write_text(json.dumps(ledger), encoding="utf-8")
    with pytest.raises(scorer.ScoringError, match="source_ledger_checksum_mismatch"):
        scorer.score(**scoring_case)


def test_signal_time_regime_artifact_checksum_drift_is_blocked(scoring_case):
    manifest = json.loads(scoring_case["feature_manifest"].read_text())
    path = Path(manifest["signal_time_regime_artifact"])
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(scorer.ScoringError, match="signal_time_regime_artifact_checksum_mismatch"):
        scorer.score(**scoring_case)
