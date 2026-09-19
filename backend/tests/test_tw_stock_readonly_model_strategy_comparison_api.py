import json
from pathlib import Path

from flask import Flask

from app.routes.readonly_model_strategy_comparison import readonly_model_strategy_comparison_bp
from app.services import readonly_model_strategy_comparison as comparison_service


ROOT = Path(__file__).resolve().parents[2]


def _client():
    app = Flask(__name__)
    app.register_blueprint(readonly_model_strategy_comparison_bp, url_prefix="/api/tw-stock")
    return app.test_client()


def test_default_selection_is_model_a_readonly_and_has_same_window_comparison():
    response = _client().get("/api/tw-stock/readonly/model-strategy-comparison")
    assert response.status_code == 200
    payload = response.get_json()["data"]

    assert payload["ok"] is True
    assert payload["readonly_only"] is True
    assert payload["no_apply"] is True
    assert payload["runtime_effect"] == "none"
    assert payload["selected"] == {
        "model_id": "model_a_only",
        "strategy_id": "top50_exit_one_worst_sell",
        "window_id": "b19r2r_retrospective_20260722_20260901",
        "combination_id": "model_a_only__top50_exit_one_worst_sell__b19r2r_30d",
    }
    assert payload["result"]["metrics"]["net_return"] == 0.009950961539552772
    assert {row["model_id"] for row in payload["comparison"]["results"]} == {
        "model_a_only",
        "model_a_plus_b_b19r2r",
    }
    assert all(row["no_apply"] is True and row["runtime_effect"] == "none" for row in payload["comparison"]["results"])
    assert next(row for row in payload["catalog"]["models"] if row["model_id"] == "model_a_only")["role"] == "active_baseline"
    assert payload["comparison"]["delta"]["net_return_b_minus_a"] == 0.07084610189805995
    diagnostics = payload["comparison"]["diagnostics"]
    assert diagnostics["bootstrap_95pct_lower_bound"]["measured_value"] == -0.0056257437697011005
    assert diagnostics["bootstrap_95pct_lower_bound"]["status"] == "FAIL"
    assert diagnostics["negative_twii20_regime_return_delta"]["measured_value"] == -0.048125452982926475
    assert diagnostics["concentration"]["top5_abs_contribution_share"]["status"] == "FAIL"
    assert diagnostics["concentration"]["abs_contribution_hhi"]["status"] == "FAIL"
    assert "negative_twii20_regime_return_delta" in diagnostics["failed_gate_ids"]
    assert payload["status"]["selection_changes_display_only"] is True
    assert payload["status"]["can_apply"] is False
    assert payload["safety"]["paper_portfolio_write"] is False
    assert payload["safety"]["latest_or_provider_write"] is False


def test_challenger_selection_exposes_failed_historical_gate_without_application():
    response = _client().get(
        "/api/tw-stock/readonly/model-strategy-comparison",
        query_string={
            "model_id": "model_a_plus_b_b19r2r",
            "strategy_id": "top50_exit_one_worst_sell",
            "window_id": "b19r2r_retrospective_20260722_20260901",
        },
    )
    assert response.status_code == 200
    payload = response.get_json()["data"]

    assert payload["result"]["metrics"]["net_return"] == 0.08079706343761273
    assert payload["result"]["gate_status"] == "FAIL_ALL_JOINT_CONFIRMATION_GATES_AS_HISTORICAL_DIAGNOSTIC"
    assert payload["result"]["historical_replay"] is True
    assert payload["result"]["prospective_pit_anchor"] is False
    assert payload["result"]["no_apply"] is True
    assert payload["status"]["baseline_admission_allowed"] is False
    assert payload["status"]["production_activation_allowed"] is False


def test_legacy_strategies_are_disclosed_but_cannot_be_misattributed_to_current_models():
    catalog_response = _client().get("/api/tw-stock/readonly/model-strategy-comparison")
    strategies = catalog_response.get_json()["data"]["catalog"]["strategies"]
    legacy = next(row for row in strategies if row["strategy_id"] == "phase1c_ltr_simple_daily")
    assert legacy["lineage"] == "legacy_phase1c_ltr_optional_sim"
    assert legacy["comparison_selectable"] is False
    assert legacy["compatible_model_ids"] == []

    response = _client().get(
        "/api/tw-stock/readonly/model-strategy-comparison",
        query_string={"model_id": "model_a_only", "strategy_id": "phase1c_ltr_simple_daily"},
    )
    assert response.status_code == 400
    error = response.get_json()["data"]
    assert error["status"] == "incompatible_legacy_lineage"
    assert error["lineage"] == "legacy_phase1c_ltr_optional_sim"


def test_route_has_no_write_methods():
    client = _client()
    for method in ("post", "put", "patch", "delete"):
        assert getattr(client, method)("/api/tw-stock/readonly/model-strategy-comparison").status_code == 405


def test_catalog_checksum_drift_fails_closed(monkeypatch, tmp_path):
    source_pointer = json.loads(comparison_service.LATEST_PATH.read_text(encoding="utf-8"))
    source_pointer["catalog_sha256"] = "0" * 64
    bad_pointer = tmp_path / "latest.json"
    bad_pointer.write_text(json.dumps(source_pointer), encoding="utf-8")
    monkeypatch.setattr(comparison_service, "LATEST_PATH", bad_pointer)

    response = _client().get("/api/tw-stock/readonly/model-strategy-comparison")
    assert response.status_code == 400
    assert response.get_json()["data"]["status"] == "checksum_failed"


def test_route_and_service_do_not_contain_write_or_execution_calls():
    route_source = (ROOT / "backend/app/routes/readonly_model_strategy_comparison.py").read_text(encoding="utf-8")
    service_source = (ROOT / "backend/app/services/readonly_model_strategy_comparison.py").read_text(encoding="utf-8")
    assert 'methods=["GET"]' in route_source
    for forbidden in (
        "requests.post",
        "provider_publish",
        "accepted_latest_switch",
        "paper_portfolio.save",
        "broker.place_order",
        "train(",
        "fit(",
    ):
        assert forbidden not in route_source
        assert forbidden not in service_source


def test_ratio_is_none_for_missing_or_zero_denominator():
    assert comparison_service._ratio(1.0, 0.0) is None
    assert comparison_service._ratio(1.0, None) is None
    assert comparison_service._ratio(None, 1.0) is None
    assert comparison_service._ratio(3.0, 2.0) == 1.5
