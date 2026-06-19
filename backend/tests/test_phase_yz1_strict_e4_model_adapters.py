from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
ASOF = "2026-06-17"
MODEL_B_MANIFEST = ROOT / f"data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/{ASOF}/model_b_yz2/manifest.json"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_yz1_registry_keeps_only_two_strict_e4_production_models():
    registry = yaml.safe_load((ROOT / "configs/tw_modular_registry.yaml").read_text(encoding="utf-8"))
    expected = set(registry["production_models"]["production_selectable"].keys())
    assert expected == {
        "e4_frozen_qlib_2018_2022",
        "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025",
    }


def test_yz1_current_builder_source_has_no_old_model_hardcode():
    source = (ROOT / "scripts/build_phase_yz2_orthogonal_package.py").read_text(encoding="utf-8")
    assert "e4_frozen_qlib_2023_2025_ltr" not in source
    assert "P3_LATEST" in source
    assert "p3_daily_ltr_rerank_latest_used_as_readiness" in source
    assert "fallback_to_p3_fresh_o4_bridge" in source


def test_yz1_current_builder_uses_frozen_e3_ltr_and_not_legacy_signal_score_source():
    source = (ROOT / "scripts/build_phase_yz2_orthogonal_package.py").read_text(encoding="utf-8")
    assert "model.predict(package[features].astype(float))" in source
    registry = yaml.safe_load((ROOT / "configs/tw_product_artifact_registry.yaml").read_text(encoding="utf-8"))
    assert registry["rebuild_sources"]["e3_ltr_model"].endswith("phasee3_ltr_model.pkl")
    assert "registry_path(PRODUCT_REGISTRY, \"rebuild_sources\", \"e3_ltr_model\")" in source
    assert "source_model_a_manifest" in source
    assert "DEFAULT_SIGNAL_MANIFEST" not in source
    assert "r1_legacy_signal_adapter" not in source
    assert "e4_frozen_qlib_2023_2025_ltr" not in source


def test_yz1_model_b_artifact_preserves_qlib_top50_scope_and_readonly_boundary():
    manifest = _read_json(MODEL_B_MANIFEST)
    assert manifest["artifact_type"] == "daily_model_signal"
    assert manifest["model_id"] == "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025"
    assert manifest["candidate_k"] == 50
    assert manifest["row_count"] == 50
    assert manifest["source_model_a_manifest"] == f"data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/{ASOF}/model_a/manifest.json"
    assert manifest["source_model_artifact"] == "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_ltr_model.pkl"
    assert manifest["readonly_only"] is True
    assert manifest["updates_readonly_latest"] is False
    assert manifest["no_training"] is True
    assert manifest["no_tuning"] is True
    assert manifest["no_provider_publish"] is True
    assert manifest["no_accepted_latest_switch"] is True
    assert manifest["no_monitor_write"] is True
    assert manifest["no_broker_order"] is True

    with (MODEL_B_MANIFEST.parent / manifest["files"]["signals"]).open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 50
    assert sorted(int(row["candidate_rank"]) for row in rows) == list(range(1, 51))
    assert sorted(int(row["full_qlib_rank"]) for row in rows) == list(range(1, 51))
