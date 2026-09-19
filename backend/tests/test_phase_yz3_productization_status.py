"""Phase YZ3 clean productization status tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import app.services.phase_yz3_productization_status as yz3_status
from app.services.phase_yz3_productization_status import (
    MODEL_A,
    MODEL_B,
    load_yz3_productization_status,
    resolve_latest_yz_signal_asof,
)




def _write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_signal_fixture(root: Path, asof: str):
    _write_json(root / asof / "model_a/manifest.json", {
        "artifact_type": "daily_model_signal",
        "model_id": MODEL_A,
        "signal_asof": asof,
        "row_count": 1,
        "files": {"signals": "signals.csv"},
        "readonly_only": True,
    })
    (root / asof / "model_a/signals.csv").write_text("instrument,score_rank,buy_score,candidate_rank,full_qlib_rank\nTW0001,1,0.9,1,1\n", encoding="utf-8")
    _write_json(root / asof / "model_b_yz2/manifest.json", {
        "artifact_type": "daily_model_signal",
        "model_id": MODEL_B,
        "signal_asof": asof,
        "row_count": 1,
        "files": {"signals": "signals.csv"},
        "readonly_only": True,
    })
    (root / asof / "model_b_yz2/signals.csv").write_text("instrument,score_rank,buy_score,candidate_rank,full_qlib_rank\nTW0002,1,0.8,1,2\n", encoding="utf-8")


def _patch_yz_paths(monkeypatch, tmp_path: Path):
    signal_root = tmp_path / "signals"
    readiness_root = tmp_path / "readiness"
    monkeypatch.setattr(yz3_status, "SIGNAL_ROOT", signal_root)
    monkeypatch.setattr(yz3_status, "YZ2R_ROOT", readiness_root)
    return signal_root, readiness_root


@pytest.mark.parametrize("model_a_allowed", [True, False])
def test_research_default_never_bypasses_production_admission(monkeypatch, tmp_path, model_a_allowed):
    signal_root, _ = _patch_yz_paths(monkeypatch, tmp_path)
    _write_signal_fixture(signal_root, "2026-06-19")
    original_load_yaml = yz3_status.load_yaml

    def configured_yaml(path):
        payload = original_load_yaml(path)
        if path == yz3_status.POLICY:
            payload["default_model_id"] = MODEL_B
            if not model_a_allowed:
                payload["models"][MODEL_A]["production_selectable"] = False
        return payload

    monkeypatch.setattr(yz3_status, "load_yaml", configured_yaml)
    payload = load_yz3_productization_status("2026-06-19")
    assert payload["selected_model_id"] == (MODEL_A if model_a_allowed else "")
    assert payload["selected_model_id"] != MODEL_B
    if not model_a_allowed:
        assert payload["ok"] is False
        assert payload["paper_apply_allowed"] is False
        assert payload["paper_apply_blocked_reason"] == "production_model_unavailable"

OLD_EXPOSED_TOKENS = [
    "origin",
    "original",
    "P3",
    "O4",
    "fresh qlib adaptive",
    "fresh qlib 2025 LTR",
    "bridge",
    "e4_frozen_qlib_2023_2025_ltr",
    "buggy_e8r",
]


def test_yz3_status_exposes_only_clean_models_and_strategy():
    payload = load_yz3_productization_status("2026-06-17")

    assert payload["ok"] is True
    assert payload["schema_version"] == "yz3_productization_status_v1"
    assert payload["signal_asof"] == "2026-06-17"
    assert [item["model_id"] for item in payload["models"]] == [MODEL_A]
    assert [item["strategy_rule_id"] for item in payload["production_strategies"]] == ["top50_exit_one_worst_sell"]
    assert payload["selected_model_id"] == MODEL_A
    assert payload["selected_strategy_rule_id"] == "top50_exit_one_worst_sell"

    serialized = json.dumps(payload, ensure_ascii=False)
    for token in OLD_EXPOSED_TOKENS:
        assert token not in serialized


def test_yz3_pending_execution_price_blocks_paper_apply_without_fallback():
    payload = load_yz3_productization_status("2026-06-17")

    assert payload["execution_price_mode"] == "next_open"
    assert payload["execution_price_status"] == "execution_price_unavailable"
    assert payload["paper_apply_allowed"] is False
    assert payload["paper_apply_blocked_reason"] == "next_open_unavailable"
    assert payload["paper_portfolio"]["status"] == "pending_execution_price"
    assert payload["paper_portfolio"]["apply_allowed"] is False
    assert payload["strategy_preview"]["realized_return_available"] is False
    assert payload["strategy_preview"]["current_signal_executable_replay_allowed"] is False
    assert "次一交易日开盘价" in payload["execution_price_message"]
    assert "2026-06-18 行情暂不可用" in payload["execution_price_message"]
    assert payload["execution_price_readiness"]["target_next_trading_day"] == "2026-06-18"
    assert payload["execution_price_readiness"]["no_fallback_to_next_close"] is True
    assert payload["safety_flags"]["no_next_close_fallback"] is True


def test_yz3_status_safety_flags_are_readonly_and_clean():
    payload = load_yz3_productization_status("2026-06-17")
    flags = payload["safety_flags"]

    for key in [
        "readonly_only",
        "no_broker_order",
        "no_quick_trade",
        "no_provider_publish",
        "no_accepted_latest_switch",
        "no_monitor_write",
    ]:
        assert flags[key] is True
    assert flags["old_models_exposed"] is False
    assert flags["old_strategies_exposed"] is False


def test_yz3_productization_route_is_get_only(client):
    resp = client.get("/api/tw-stock/phase-yz/productization-status")
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["code"] == 1
    data = payload["data"]
    assert data["execution_price_mode"] == "next_open"
    assert data["execution_price_status"] == "execution_price_unavailable"
    assert data["paper_apply_allowed"] is False
    assert data["paper_apply_blocked_reason"] == "next_open_unavailable"
    assert [item["model_id"] for item in data["models"]] == [MODEL_A]

    for method in ["post", "put", "patch", "delete"]:
        assert getattr(client, method)("/api/tw-stock/phase-yz/productization-status").status_code == 405


def test_yz3_route_source_has_no_forbidden_write_or_ops_calls():
    source = Path("backend/app/routes/tw_stock_context_routes.py").read_text(encoding="utf-8")
    route_start = source.index('@tw_stock_context_bp.route("/phase-yz/productization-status", methods=["GET"])')
    route_end = source.find("\n\n@", route_start)
    route_source = source[route_start:route_end if route_end != -1 else len(source)]

    assert 'methods=["GET"]' in route_source
    forbidden = [
        'methods=["POST"]',
        'provider_refresh',
        'provider_publish',
        'accepted_latest_switch',
        'monitor_scan',
        'quick_trade',
        'broker',
        'applyTwStockPaperPortfolioDecision',
        'reset',
        'target_position',
        'target_weight',
    ]
    for token in forbidden:
        assert token not in route_source


def test_yz3_default_signal_asof_resolves_latest_clean_artifact(monkeypatch, tmp_path):
    signal_root, readiness_root = _patch_yz_paths(monkeypatch, tmp_path)
    _write_signal_fixture(signal_root, "2026-06-17")
    _write_signal_fixture(signal_root, "2026-06-19")
    _write_json(readiness_root / "2026-06-19/manifest.json", {
        "status": "execution_price_unavailable",
        "target_next_trading_day": "2026-06-22",
        "next_open_available_count": 0,
        "next_close_available_count": 0,
        "missing_next_open_count": 1,
        "missing_next_close_count": 1,
        "no_fallback_to_next_close": True,
        "no_fallback_to_signal_close": True,
    })

    assert resolve_latest_yz_signal_asof() == "2026-06-19"
    payload = load_yz3_productization_status()

    assert payload["ok"] is True
    assert payload["signal_asof"] == "2026-06-19"
    assert payload["execution_price_readiness"]["target_next_trading_day"] == "2026-06-22"
    assert "2026-06-22 行情暂不可用" in payload["execution_price_message"]
    assert "2026-06-18" not in payload["execution_price_message"]
    assert payload["paper_apply_allowed"] is False
    assert payload["paper_apply_blocked_reason"] == "next_open_unavailable"


def test_yz3_explicit_signal_asof_overrides_latest(monkeypatch, tmp_path):
    signal_root, readiness_root = _patch_yz_paths(monkeypatch, tmp_path)
    _write_signal_fixture(signal_root, "2026-06-17")
    _write_signal_fixture(signal_root, "2026-06-19")
    _write_json(readiness_root / "2026-06-17/manifest.json", {
        "status": "execution_price_unavailable",
        "target_next_trading_day": "2026-06-18",
        "next_open_available_count": 0,
        "missing_next_open_count": 1,
        "no_fallback_to_next_close": True,
        "no_fallback_to_signal_close": True,
    })
    _write_json(readiness_root / "2026-06-19/manifest.json", {
        "status": "execution_price_unavailable",
        "target_next_trading_day": "2026-06-22",
        "next_open_available_count": 0,
        "missing_next_open_count": 1,
        "no_fallback_to_next_close": True,
        "no_fallback_to_signal_close": True,
    })

    payload = load_yz3_productization_status("2026-06-17")

    assert payload["signal_asof"] == "2026-06-17"
    assert payload["execution_price_readiness"]["target_next_trading_day"] == "2026-06-18"
    assert "2026-06-18 行情暂不可用" in payload["execution_price_message"]


def test_yz3_readiness_missing_returns_pending_without_fixed_date(monkeypatch, tmp_path):
    signal_root, _ = _patch_yz_paths(monkeypatch, tmp_path)
    _write_signal_fixture(signal_root, "2026-06-19")

    payload = load_yz3_productization_status()

    assert payload["ok"] is True
    assert payload["signal_asof"] == "2026-06-19"
    assert payload["execution_price_status"] == "execution_price_unavailable"
    assert payload["paper_apply_allowed"] is False
    assert payload["paper_apply_blocked_reason"] == "execution_price_readiness_missing"
    assert payload["execution_price_readiness"]["target_next_trading_day"] == ""
    assert payload["execution_price_message"] == "成交口径：次一交易日开盘价。成交价可用性尚未生成，等待下一轮数据更新。"
    assert "2026-06-18" not in payload["execution_price_message"]
