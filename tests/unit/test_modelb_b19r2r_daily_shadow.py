from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import run_modelb_b19r2r_daily_shadow as shadow  # noqa: E402
import validate_tw_modular_artifact_contract as modular_validator  # noqa: E402


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def hsa_source(tmp_path: Path, family: str, run_id: str, asof: str) -> dict:
    normalized = tmp_path / family / "normalized.json"
    adapter = tmp_path / family / "adapter.json"
    write_json(normalized, {"records": [{"trade_date": asof, "symbol": "2330"}]})
    write_json(adapter, {
        "acquisition_run_id": run_id,
        "target_asof": asof,
        "pit_status": "PASS",
        "validator_status": "PASS",
    })
    return {
        "source_family": family,
        "acquisition_run_id": run_id,
        "target_asof": asof,
        "pit_status": "PASS",
        "source_validator_status": "PASS",
        "available_at": f"{asof}T06:00:00+00:00",
        "absent_scope": ["7769"],
        "unknown_scope": [],
        "normalized_files": [str(normalized)],
        "adapter_output_files": [str(adapter)],
        "artifacts": [
            {"path": str(normalized), "sha256": shadow.sha256(normalized)},
            {"path": str(adapter), "sha256": shadow.sha256(adapter)},
        ],
    }


def test_hsa_children_accept_valid_three_sources_when_parent_handoff_stopped_on_twii(tmp_path: Path) -> None:
    run_id = "finmind.logical.fixture"
    asof = "2026-09-17"
    sources = [
        hsa_source(tmp_path, "adjusted_price", run_id, asof),
        hsa_source(tmp_path, "institutional_flow", run_id, asof),
        hsa_source(tmp_path, "margin_short", run_id, asof),
        {
            "source_family": "twii",
            "provider": "TWSE OpenAPI",
            "pit_status": "BLOCKED_PUBLICATION_AND_AVAILABILITY_UNPROVEN",
            "source_validator_status": "BLOCKED_PROVIDER_SCHEMA",
        },
    ]
    handoff = tmp_path / "same_run_handoff_validation.json"
    write_json(handoff, {"ok": False, "status": "STOP", "sources": sources})

    selected = shadow.validate_hsa_children(
        handoff,
        asof,
        run_id,
        shadow.parse_time("2026-09-17T14:45:00+00:00"),
    )

    assert set(selected) == {"adjusted_price", "institutional_flow", "margin_short"}


def test_hsa_children_missing_input_fails_closed(tmp_path: Path) -> None:
    run_id = "finmind.logical.fixture"
    asof = "2026-09-17"
    handoff = tmp_path / "same_run_handoff_validation.json"
    write_json(handoff, {
        "sources": [
            hsa_source(tmp_path, "adjusted_price", run_id, asof),
            hsa_source(tmp_path, "institutional_flow", run_id, asof),
        ]
    })

    with pytest.raises(shadow.ShadowError) as error:
        shadow.validate_hsa_children(
            handoff,
            asof,
            run_id,
            shadow.parse_time("2026-09-17T14:45:00+00:00"),
        )

    assert error.value.code == "B19R2R_BLOCKED_HANDOFF_CHILD"


def test_hsa_children_null_scope_is_a_contract_blocker(tmp_path: Path) -> None:
    run_id = "finmind.logical.fixture"
    asof = "2026-09-17"
    source = hsa_source(tmp_path, "adjusted_price", run_id, asof)
    source["absent_scope"] = None
    handoff = tmp_path / "same_run_handoff_validation.json"
    write_json(
        handoff,
        {
            "sources": [
                source,
                hsa_source(tmp_path, "institutional_flow", run_id, asof),
                hsa_source(tmp_path, "margin_short", run_id, asof),
            ]
        },
    )

    with pytest.raises(shadow.ShadowError) as error:
        shadow.validate_hsa_children(
            handoff,
            asof,
            run_id,
            shadow.parse_time("2026-09-17T14:45:00+00:00"),
        )

    assert error.value.code == "B19R2R_BLOCKED_HANDOFF_CHILD_CONTRACT"


def test_published_model_a_reuse_requires_same_logical_acquisition_and_cutoff(tmp_path: Path) -> None:
    asof = "2026-09-18"
    run_id = "finmind.logical.same_date_and_universe"
    model_a_dir = tmp_path / "published_model_a"
    write_json(model_a_dir / "manifest.json", {
        "artifact_type": "ModelSignalArtifact", "model_id": shadow.MODEL_A_ID,
        "asof": asof, "status": "READY", "row_count": 150,
        "source_acquisition_run_id": run_id,
        "created_at": f"{asof}T14:46:00+00:00",
        "decision_cutoff": f"{asof}T14:45:00+00:00",
    })
    write_json(model_a_dir / "validator_report.json", {"ok": True})
    instruments = [f"TW{1000 + index}" for index in range(1, 151)]
    instruments[24] = "TW7769"
    pd.DataFrame({
        "date": asof, "instrument": instruments,
        "candidate_rank": np.arange(1, 151), "full_qlib_rank": np.arange(1, 151),
        "raw_score": np.arange(150, 0, -1, dtype=float),
    }).to_csv(model_a_dir / "signals.csv", index=False)
    cutoff = shadow.parse_time(f"{asof}T14:45:00+00:00")
    exact, manifest = shadow.validate_model_a(model_a_dir, asof, run_id, cutoff)
    assert manifest["source_acquisition_run_id"] == run_id
    assert len(exact) == 49
    assert 25 not in exact.candidate_rank.tolist()
    for source_id, decision_cutoff in (
        ("finmind.logical.different_universe", cutoff),
        (run_id, shadow.parse_time(f"{asof}T07:59:00+00:00")),
    ):
        with pytest.raises(shadow.ShadowError) as error:
            shadow.validate_model_a(model_a_dir, asof, source_id, decision_cutoff)
        assert error.value.code == "B19R2R_BLOCKED_MODELA_CONTRACT"


def test_twii_snapshot_requires_same_acquisition_run(tmp_path: Path) -> None:
    asof = "2026-09-18"
    csv_path = tmp_path / "TWII_NORMALIZED.csv"
    csv_path.write_text("date,close\n2026-09-18,25000\n", encoding="utf-8")
    manifest_path = tmp_path / "TWII_CAPTURE_MANIFEST.json"
    write_json(manifest_path, {
        "schema_version": "modelb_b19r2r.yahoo_twii_dual_interval_capture.v2",
        "target_asof": asof,
        "acquisition_run_id": "different-source-run",
        "source_id": "yahoo.finance.chart.^TWII.dual_interval.v2",
        "provider": "Yahoo Finance",
        "pit_status": "PASS",
        "validator_status": "PASS",
        "production_allowed": False,
        "available_at": f"{asof}T06:00:00+00:00",
        "artifacts": {"normalized_csv": {"sha256": shadow.sha256(csv_path)}},
        "implementation": {
            "path": str(shadow.TWII_CAPTURE_SCRIPT),
            "sha256": shadow.sha256(shadow.TWII_CAPTURE_SCRIPT),
        },
    })

    with pytest.raises(shadow.ShadowError) as error:
        shadow._validate_yahoo_twii(
            manifest_path,
            csv_path,
            asof,
            "expected-source-run",
            shadow.parse_time(f"{asof}T14:45:00+00:00"),
            shadow.parse_time("2026-09-21T01:00:00+00:00"),
        )

    assert error.value.code == "B19R2R_BLOCKED_TWII_CONTRACT"


def test_ready_fixture_emits_valid_no_apply_artifact_without_pointer_change(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class Booster:
        @staticmethod
        def feature_name() -> list[str]:
            return shadow.feature_order()

    class Model:
        booster_ = Booster()

        @staticmethod
        def predict(frame: pd.DataFrame) -> np.ndarray:
            return np.arange(len(frame), dtype=float)

    protected = {"pointer": "unchanged"}
    monkeypatch.setattr(shadow, "load_frozen_model", lambda: (Model(), shadow.feature_order()))
    monkeypatch.setattr(shadow, "pointer_fingerprints", lambda: protected.copy())
    model_a_dir = tmp_path / "model_a"
    model_a_dir.mkdir()
    source_paths = {}
    for name in ("adjusted_price", "institutional_flow", "margin_short"):
        path = tmp_path / f"{name}.json"
        path.write_text("{}", encoding="utf-8")
        source_paths[name] = path
    twii_path = tmp_path / "twii.csv"
    twii_path.write_text("date,close\n2026-09-17,25000\n", encoding="utf-8")
    instruments = [f"TW{1000 + value}" for value in range(1, 51)]
    instruments[24] = "TW7769"
    exact50 = pd.DataFrame({
        "date": "2026-09-17",
        "instrument": instruments,
        "candidate_rank": np.arange(1, 51),
        "full_qlib_rank": np.arange(1, 51),
    })
    exact = exact50[exact50.instrument.ne("TW7769")].copy()
    features = exact[["date", "instrument"]].copy()
    for feature in shadow.feature_order():
        features[feature] = 1.0
    output = tmp_path / "shadow"
    output.mkdir()

    manifest = shadow.emit_artifact(
        output_dir=output,
        asof="2026-09-17",
        exact=exact,
        features=features,
        model_a_dir=model_a_dir,
        source_run_id="finmind.logical.fixture",
        source_paths=source_paths,
        twii_path=twii_path,
        history_lineage=[],
        decision_cutoff="2026-09-17T14:45:00+00:00",
        protected_before=protected,
        provider_inventory={"schema_version": "fixture", "field_files": []},
    )
    report = shadow.validate_artifact(output, exact)
    modular_report = modular_validator.validate_model_signal(output / "manifest.json", {})

    assert report["ok"] is True
    assert modular_report["ok"] is True
    assert manifest["status"] == "READY_RESEARCH_SHADOW"
    assert manifest["row_count"] == 49
    assert manifest["no_apply"] is True
    assert manifest["production_allowed"] is False
    assert manifest["tw7769_substitution_performed"] is False
    signals = pd.read_csv(output / "signals.csv")
    assert "TW7769" not in set(signals.instrument)
    assert set(signals.candidate_rank.astype(int)) == set(range(1, 51)) - {25}


def test_model_a_history_includes_accepted_prediction_only_days(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    frozen_path = tmp_path / "history.parquet"
    signal_root = tmp_path / "signals"
    prediction_root = tmp_path / "predictions"
    current = signal_root / "current"
    signal_root.mkdir()
    prediction_root.mkdir()
    rows = pd.DataFrame({
        "date": ["2026-09-01"] * 150,
        "instrument": [f"TW{1000 + value}" for value in range(150)],
        "model_a_raw_score": np.linspace(1, 0, 150),
        "full_qlib_rank": np.arange(1, 151),
    })
    rows.to_parquet(frozen_path, index=False)

    for day in ("2026-09-07", "2026-09-08"):
        run = prediction_root / f"option_c_daily_signal_{day.replace('-', '')}_fixture"
        run.mkdir()
        prediction = run / "prediction.csv"
        pd.DataFrame({
            "datetime": [day] * 150,
            "instrument": [f"TW{1000 + value}" for value in range(150)],
            "score": np.linspace(1, 0, 150),
        }).to_csv(prediction, index=False)
        write_json(run / "run_metadata.json", {"status": "accepted", "run_id": run.name, "created_at": f"{day}T10:00:00+00:00"})
        write_json(run / "artifact_manifest.json", {"status": "accepted", "run_id": run.name, "entries": [{"key": "prediction", "sha256": shadow.sha256(prediction)}]})

    current.mkdir()
    pd.DataFrame({
        "date": ["2026-09-09"] * 150,
        "instrument": [f"TW{1000 + value}" for value in range(150)],
        "raw_score": np.linspace(1, 0, 150),
        "full_qlib_rank": np.arange(1, 151),
    }).to_csv(current / "signals.csv", index=False)
    write_json(current / "manifest.json", {"model_id": shadow.MODEL_A_ID, "status": "READY", "row_count": 150, "created_at": "2026-09-09T10:00:00+00:00"})
    monkeypatch.setattr(shadow, "MODEL_A_HISTORY", frozen_path)
    monkeypatch.setattr(shadow, "MODEL_A_SIGNAL_ROOT", signal_root)
    monkeypatch.setattr(shadow, "MODEL_A_PREDICTION_ROOT", prediction_root)

    history, lineage = shadow.model_a_history(current, "2026-09-09", shadow.parse_time("2026-09-09T12:00:00+00:00"))

    assert set(history.date) == {"2026-09-01", "2026-09-07", "2026-09-08", "2026-09-09"}
    assert {row["date"] for row in lineage} == {"2026-09-07", "2026-09-08", "2026-09-09"}


def test_blocker_is_nonblocking_and_preserves_pointer_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    protected = {"pointer": "unchanged"}
    monkeypatch.setattr(shadow, "pointer_fingerprints", lambda: protected.copy())

    blocker = shadow.write_blocker(
        tmp_path,
        "2026-09-17",
        shadow.ShadowError("B19R2R_BLOCKED_INCOMPLETE_78F", "RSI14"),
        protected,
    )

    assert blocker["ok"] is False
    assert blocker["mainline_blocking"] is False
    assert blocker["protected_unchanged"] is True
    assert blocker["no_apply"] is True
    assert (tmp_path / "manifest.json").is_file()
    assert (tmp_path / "validator_report.json").is_file()


def test_prospective_event_is_idempotent_and_conflicts_are_quarantined(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = tmp_path / "events.jsonl"
    monkeypatch.setattr(shadow, "PROSPECTIVE_EVENT_LEDGER", ledger)
    monkeypatch.setattr(shadow, "PROSPECTIVE_EVENT_ROOT", tmp_path)
    output = tmp_path / "artifact"
    output.mkdir()
    (output / "signals.csv").write_text("date,instrument\n2026-09-17,TW2330\n", encoding="utf-8")
    (output / "manifest.json").write_text("{}\n", encoding="utf-8")
    manifest = {
        "asof": "2026-09-17",
        "source_acquisition_run_id": "finmind.logical.fixture",
        "decision_cutoff": "2026-09-17T14:45:00+00:00",
        "row_count": 49,
        "tw7769_excluded": True,
        "retrospective_fixture": False,
    }

    first = shadow.append_prospective_event(output, manifest)
    second = shadow.append_prospective_event(output, manifest)

    assert first["status"] == "APPENDED"
    assert second["status"] == "IDEMPOTENT_NOOP"
    assert second["event_hash"] == first["event_hash"]
    assert len(ledger.read_text(encoding="utf-8").splitlines()) == 1

    (output / "signals.csv").write_text("date,instrument\n2026-09-17,TW2331\n", encoding="utf-8")
    conflict = shadow.append_prospective_event(output, manifest)
    assert conflict["status"] == "CONFLICTING_SOURCE_QUARANTINED"
    assert len(ledger.read_text(encoding="utf-8").splitlines()) == 1
    assert (tmp_path / "quarantine").is_dir()


def test_retrospective_fixture_does_not_append_prospective_event(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shadow, "PROSPECTIVE_EVENT_LEDGER", tmp_path / "events.jsonl")
    monkeypatch.setattr(shadow, "PROSPECTIVE_EVENT_ROOT", tmp_path)
    output = tmp_path / "artifact"
    output.mkdir()
    (output / "signals.csv").write_text("date,instrument\n2026-09-16,TW2330\n", encoding="utf-8")
    (output / "manifest.json").write_text("{}\n", encoding="utf-8")
    event = shadow.append_prospective_event(output, {
        "asof": "2026-09-16",
        "source_acquisition_run_id": "fixture",
        "decision_cutoff": "2026-09-16T19:22:18+00:00",
        "row_count": 50,
        "tw7769_excluded": True,
        "retrospective_fixture": True,
    })
    assert event["status"] == "SKIPPED_RETROSPECTIVE_FIXTURE"
    assert not (tmp_path / "events.jsonl").exists()
    assert (output / "prospective_event.json").is_file()


def test_20260916_retrospective_fixture_matches_frozen_features_scores_and_validator() -> None:
    fixture = Path("/tmp/b19r2r_daily_shadow_20260916_probe_v5")
    frozen = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_v5_bundle_20260916/pre_capture_v5"
    if not fixture.is_dir():
        pytest.skip("9/16 retrospective fixture is not materialized")
    frozen_features = pd.read_csv(frozen / "FEATURES_78_CANDIDATE.csv").sort_values("instrument").reset_index(drop=True)
    shadow_features = pd.read_csv(fixture / "features_78.csv").sort_values("instrument").reset_index(drop=True)
    feature_columns = shadow.feature_order()
    assert frozen_features["instrument"].equals(shadow_features["instrument"])
    assert float((frozen_features[feature_columns].astype(float) - shadow_features[feature_columns].astype(float)).abs().to_numpy().max()) == 0.0

    frozen_scores = pd.read_csv(frozen / "CANDIDATE14_MODEL_B_SCORES.csv").sort_values("instrument").reset_index(drop=True)
    shadow_scores = pd.read_csv(fixture / "signals.csv").sort_values("instrument").reset_index(drop=True)
    assert frozen_scores["instrument"].equals(shadow_scores["instrument"])
    assert float((frozen_scores["model_b_score"].astype(float) - shadow_scores["buy_score"].astype(float)).abs().max()) == 0.0
    assert float((frozen_scores["model_b_score"].astype(float) - shadow_scores["raw_score"].astype(float)).abs().max()) == 0.0
    expected_rank = frozen_scores.set_index("instrument")["rank"].astype(int).sort_index()
    actual_rank = shadow_scores.set_index("instrument")["score_rank"].astype(int).sort_index()
    assert expected_rank.equals(actual_rank)
    validation = modular_validator.validate_model_signal(fixture / "manifest.json", {})
    assert validation["ok"] is True
