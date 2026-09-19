from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


builder = load(
    "materialize_modelb_b19r2r_v5_bundle_20260916",
    "scripts/materialize_modelb_b19r2r_v5_bundle_20260916.py",
)
validator = load(
    "validate_modelb_b19r2r_v5_bundle_20260916",
    "scripts/validate_modelb_b19r2r_v5_bundle_20260916.py",
)


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_real_composite_review_and_calendar_binding_pass() -> None:
    value = builder.composite_binding()
    assert value["manifest"]["logical_source_run_id"] == builder.SOURCE_RUN
    assert [item["role"] for item in value["children"]] == [
        "daily_price", "institutional", "margin", "model_a_inference", "twii_yahoo",
    ]
    dates = builder.calendar_dates()
    assert dates[-1] == builder.ASOF
    assert "2026-07-10" not in dates


def test_composite_manifest_digest_tamper_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "manifest.json"
    path.write_bytes(builder.COMPOSITE_MANIFEST.read_bytes())
    value = json.loads(path.read_text(encoding="utf-8"))
    value["child_inventory_sha256"] = "0" * 64
    write_json(path, value)
    monkeypatch.setattr(builder, "COMPOSITE_MANIFEST", path)
    monkeypatch.setattr(builder, "COMPOSITE_MANIFEST_SHA", builder.sha256(path))
    with pytest.raises(builder.MaterializationError) as caught:
        builder.composite_binding()
    assert caught.value.code == "B19V4M_E_COMPOSITE_BINDING"


def test_review_authorization_tamper_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "review.json"
    value = json.loads(builder.COMPOSITE_REVIEW.read_text(encoding="utf-8"))
    value["authorization"]["model_b_score_precapture_materialization_authorized"] = False
    write_json(path, value)
    monkeypatch.setattr(builder, "COMPOSITE_REVIEW", path)
    monkeypatch.setattr(builder, "COMPOSITE_REVIEW_SHA", builder.sha256(path))
    with pytest.raises(builder.MaterializationError) as caught:
        builder.composite_binding()
    assert caught.value.code == "B19V4M_E_COMPOSITE_BINDING"


def test_calendar_placeholder_reintroduction_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "calendar.txt"
    path.write_text("2026-07-10\n2026-09-16\n", encoding="ascii")
    monkeypatch.setattr(builder, "EXTENDED_CALENDAR", path)
    monkeypatch.setattr(builder, "EXTENDED_CALENDAR_SHA", builder.sha256(path))
    with pytest.raises(builder.MaterializationError) as caught:
        builder.calendar_dates()
    assert caught.value.code == "B19V4M_E_CALENDAR_CONTENT"


def test_exact50_uses_primary_145712_without_substitution() -> None:
    exact, binding = builder.model_a_exact50()
    assert len(exact) == 50
    assert exact["rank"].tolist() == list(range(1, 51))
    assert "TW7769" not in set(exact.instrument)
    assert binding["physical_run_id"] == builder.MODEL_A_PRE_CUTOFF_DIR.name


def test_twii_v5_rolling_on_extended_calendar_is_finite() -> None:
    features, evidence = builder.twii_features()
    assert evidence["last_120_calendar_rows_complete"] is True
    assert evidence["normalized_sha256"] == "05d95807405592aeb67fe247322ab36ab130618b740fa27aedc397e9c0f6824a"
    assert len(features) == 6
    assert np.isfinite(np.asarray(list(features.values()), dtype=float)).all()


def test_real_78f_and_candidate14_are_complete_and_finite() -> None:
    exact, _ = builder.model_a_exact50()
    features, audit = builder.assemble_features(exact)
    model, order = builder.model_identity()
    assert len(features) == 50
    assert audit["complete_78_rows"] == 50
    assert np.isfinite(features[order].to_numpy(float)).all()
    scores = np.asarray(model.predict(features[order]), dtype=float)
    assert len(scores) == 50 and np.isfinite(scores).all()


def test_shared_source_binding_contains_exact_digests() -> None:
    value = builder.shared_source_binding("2026-09-16T19:30:00+00:00")
    assert value["child_inventory_sha256"] == builder.CHILD_INVENTORY_SHA
    assert value["composite_independent_review_sha256"] == builder.COMPOSITE_REVIEW_SHA
    assert value["extended_clean_calendar_sha256"] == builder.EXTENDED_CALENDAR_SHA


def test_backdated_output_and_after_open_capture_cutoff_are_rejected() -> None:
    with pytest.raises(builder.MaterializationError) as backdated:
        builder.validate_output_time_order(
            ["2026-09-16T18:29:00+00:00"],
            "2026-09-16T19:30:00+00:00",
        )
    assert backdated.value.code == "B19V5M_E_OUTPUT_TIME_ORDER"
    with pytest.raises(builder.MaterializationError) as after_open:
        builder.validate_output_time_order(
            ["2026-09-16T19:30:00+00:00"],
            builder.NEXT_OPEN,
        )
    assert after_open.value.code == "B19V5M_E_OUTPUT_TIME_ORDER"


def test_output_escape_and_no_overwrite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(builder, "OUT_ROOT", tmp_path / "allowed")
    with pytest.raises(builder.MaterializationError) as escaped:
        builder.materialize(tmp_path / "outside")
    assert escaped.value.code == "B19V3M_E_OUTPUT_ESCAPE"
    output = builder.OUT_ROOT / "pre_capture_v5"
    output.mkdir(parents=True)
    (output / "existing").write_text("stable\n", encoding="ascii")
    with pytest.raises(builder.MaterializationError) as duplicate:
        builder.materialize(output)
    assert duplicate.value.code == "B19V3M_E_NO_OVERWRITE"
