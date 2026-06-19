from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASOF = "2026-06-17"
MANIFEST = ROOT / f"data_tw/artifacts/phase_yz/yz2r_execution_price_readiness/{ASOF}/manifest.json"
MODEL_A = ROOT / f"data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/{ASOF}/model_a/manifest.json"
MODEL_B = ROOT / f"data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/{ASOF}/model_b_yz2/manifest.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_yz2r_blocks_when_next_open_missing_and_never_fallbacks():
    manifest = read_json(MANIFEST)
    assert manifest["artifact_type"] == "YZ2RExecutionPriceReadiness"
    assert manifest["target_next_trading_day"] == "2026-06-18"
    assert manifest["row_count"] == 50
    assert manifest["next_open_available_count"] == 0
    assert manifest["missing_next_open_count"] == 50
    assert manifest["status"] == "execution_price_unavailable"
    assert manifest["recommended_gate"] == "blocked_before_yz3"
    assert manifest["no_fallback_to_next_close"] is True
    assert manifest["no_fallback_to_signal_close"] is True


def test_yz2r_price_audit_has_required_fields_and_no_close_as_open_fill():
    manifest = read_json(MANIFEST)
    audit_path = MANIFEST.parent / manifest["price_availability_audit"]
    with audit_path.open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 50
    required = {"target_next_trading_day", "next_trading_day_open", "next_trading_day_close", "close_on_or_before_signal_asof", "fallback_to_next_close", "fallback_to_signal_close", "open_equals_signal_close"}
    assert required.issubset(rows[0].keys())
    assert all(str(row["fallback_to_next_close"]).lower() == "false" for row in rows)
    assert all(str(row["fallback_to_signal_close"]).lower() == "false" for row in rows)
    assert all(str(row["open_equals_signal_close"]).lower() == "false" for row in rows)
    assert all(row["next_trading_day_open"] == "" for row in rows)


def test_yz2r_source_trace_documents_local_only_no_provider_actions():
    manifest = read_json(MANIFEST)
    trace = read_json(MANIFEST.parent / manifest["source_trace"])
    assert trace["target_next_trading_day"] == "2026-06-18"
    assert trace["external_network_used"] is False
    assert trace["provider_refresh_triggered"] is False
    assert trace["provider_publish_triggered"] is False
    assert trace["accepted_latest_switch_triggered"] is False
    assert trace["fallback_to_next_close"] is False
    assert trace["fallback_to_signal_close"] is False
    assert trace["manual_or_synthetic_ohlc"] is False
    assert trace["blocked_reason"] == "local_2026_06_18_ohlc_not_found"


def test_yz2r_forbidden_actions_and_model_manifests_preserved():
    manifest = read_json(MANIFEST)
    actions = read_json(MANIFEST.parent / manifest["forbidden_action_audit"])["actions"]
    assert all(value is False for value in actions.values())
    model_a = read_json(MODEL_A)
    model_b = read_json(MODEL_B)
    assert model_a["model_id"] == "e4_frozen_qlib_2018_2022"
    assert model_a["row_count"] == 150
    assert model_b["model_id"] == "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025"
    assert model_b["row_count"] == 50
