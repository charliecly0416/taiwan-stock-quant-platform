from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASOF = "2026-06-17"
FEATURE_MANIFEST = ROOT / f"data_tw/artifacts/phase_yz/yz2_orthogonal_feature_package/{ASOF}/manifest.json"
MODEL_B_MANIFEST = ROOT / f"data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/{ASOF}/model_b_yz2/manifest.json"
PRICE_MANIFEST = ROOT / f"data_tw/artifacts/phase_yz/yz2_execution_price_readiness/{ASOF}/manifest.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_yz2_orthogonal_package_strict_e4_top50_coverage_and_no_p3_readiness():
    manifest = read_json(FEATURE_MANIFEST)
    assert manifest["artifact_type"] == "YZ2StrictE4OrthogonalFeaturePackage"
    assert manifest["universe_source"] == f"data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/{ASOF}/model_a/manifest.json"
    assert manifest["scoped_model_id"] == "e4_frozen_qlib_2018_2022"
    assert manifest["row_count"] == 50
    assert len(manifest["covered_symbols"]) == 50
    assert manifest["missing_symbols"] == []
    assert manifest["coverage_ratio"] == 1.0
    assert manifest["p3_daily_ltr_rerank_latest_used_as_readiness"] is False
    assert manifest["no_fallback"] is True


def test_yz2_feature_schema_pit_and_forbidden_field_audits_pass():
    manifest = read_json(FEATURE_MANIFEST)
    assert manifest["feature_schema_column_count"] == 78
    assert manifest["pit_violation_count"] == 0
    schema_audit = (FEATURE_MANIFEST.parent / manifest["feature_schema_alignment_audit"]).read_text(encoding="utf-8")
    assert "pass" in schema_audit
    pit_audit = (FEATURE_MANIFEST.parent / manifest["pit_available_at_audit"]).read_text(encoding="utf-8")
    assert ",0,pass" in pit_audit
    forbidden_audit = (FEATURE_MANIFEST.parent / manifest["forbidden_field_audit"]).read_text(encoding="utf-8")
    assert "0,,pass" in forbidden_audit


def test_yz2_model_b_sources_and_row_semantics():
    manifest = read_json(MODEL_B_MANIFEST)
    assert manifest["artifact_type"] == "daily_model_signal"
    assert manifest["model_id"] == "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025"
    assert manifest["row_count"] == 50
    assert manifest["source_model_a_manifest"] == f"data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/{ASOF}/model_a/manifest.json"
    assert manifest["source_model_artifact"] == "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_ltr_model.pkl"
    assert manifest["source_feature_artifact"] == f"data_tw/artifacts/phase_yz/yz2_orthogonal_feature_package/{ASOF}/manifest.json"
    source_trace = read_json(MODEL_B_MANIFEST.parent / manifest["source_trace"])
    assert source_trace["input_scope"] == "YZ1 Model A qlib top50 only"
    assert source_trace["fallback_to_p3_fresh_o4_bridge"] is False
    with (MODEL_B_MANIFEST.parent / "signals.csv").open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 50
    assert sorted(int(r["candidate_rank"]) for r in rows) == list(range(1, 51))
    assert sorted(int(r["full_qlib_rank"]) for r in rows) == list(range(1, 51))


def test_yz2_execution_price_readiness_has_required_fields_and_no_next_close_fallback():
    manifest = read_json(PRICE_MANIFEST)
    assert manifest["artifact_type"] == "YZ2ExecutionPriceReadiness"
    assert manifest["execution_price_mode_planned_for_yz3"] == "next_open"
    assert manifest["row_count"] == 50
    assert manifest["close_on_or_before_signal_asof_available_count"] == 50
    assert manifest["missing_signal_close_count"] == 0
    assert manifest["no_fallback_to_next_close"] is True
    assert manifest["status"] in {"pass", "execution_price_unavailable"}
    with (PRICE_MANIFEST.parent / manifest["price_availability_audit"]).open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert rows
    required = {"next_trading_day", "next_trading_day_open", "next_trading_day_close", "close_on_or_before_signal_asof", "fallback_to_next_close"}
    assert required.issubset(rows[0].keys())
    assert all(str(r["fallback_to_next_close"]).lower() == "false" for r in rows)
    if manifest["missing_next_open_count"] > 0:
        assert manifest["status"] == "execution_price_unavailable"
