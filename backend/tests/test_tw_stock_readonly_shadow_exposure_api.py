"""MTRP10 readonly shadow exposure API contract tests."""
from __future__ import annotations

from flask import Flask

from app.routes.tw_stock import tw_stock_bp
from app.services.readonly_shadow_exposure import FORBIDDEN_RESPONSE_FIELDS


def _client():
    app = Flask(__name__)
    app.register_blueprint(tw_stock_bp, url_prefix="/api/tw-stock")
    return app.test_client()


def _data(response):
    payload = response.get_json()
    return payload["data"]


def test_readonly_shadow_exposure_get_success():
    resp = _client().get("/api/tw-stock/readonly-shadow-exposure")
    data = _data(resp)
    assert resp.status_code == 200
    assert data["ok"] is True
    assert data["schema_version"] == "mtrp9_readonly_shadow_exposure_api_v1"
    assert data["strategy_candidate"] == "top50_hold_rank_buffer_100"
    assert data["baseline_strategy"] == "top50_exit_one_worst_sell"
    assert data["source_manifest"].endswith("mtrp8_shadow_review_readonly_exposure_design/manifest.json")
    assert data["gate"]["ok"] is True
    assert data["rows"]
    assert data["citations"]
    assert data["open_blockers"]


def test_readonly_shadow_exposure_contract_flags_are_non_default_safe():
    data = _data(_client().get("/api/tw-stock/readonly-shadow-exposure"))
    assert data["readonly_only"] is True
    assert data["simulation_only"] is True
    assert data["not_order"] is True
    assert data["not_target_position"] is True
    assert data["not_investment_advice"] is True
    assert data["production_allowed"] is False
    assert data["production_ready"] is False
    assert data["default_switch_allowed"] is False
    assert data["paper_apply_allowed"] is False


def test_readonly_shadow_exposure_include_rows_false_omits_rows():
    resp = _client().get(
        "/api/tw-stock/readonly-shadow-exposure",
        query_string={"include_rows": "false"},
    )
    data = _data(resp)
    assert resp.status_code == 200
    assert data["ok"] is True
    assert data["rows_included"] is False
    assert data["row_count"] > 0
    assert data["rows"] == []


def test_readonly_shadow_exposure_rejects_unknown_strategy():
    resp = _client().get(
        "/api/tw-stock/readonly-shadow-exposure",
        query_string={"strategy_rule": "top50_exit_one_worst_sell"},
    )
    data = _data(resp)
    assert resp.status_code == 404
    assert data["ok"] is False
    assert data["status"] == "unknown_strategy_rule"
    assert data["readonly_only"] is True
    assert data["production_allowed"] is False


def test_readonly_shadow_exposure_forbidden_response_fields_absent():
    data = _data(_client().get("/api/tw-stock/readonly-shadow-exposure"))
    for field in FORBIDDEN_RESPONSE_FIELDS:
        assert field not in data


def test_readonly_shadow_exposure_route_has_no_write_methods():
    client = _client()
    for method in ["post", "put", "patch", "delete"]:
        assert getattr(client, method)("/api/tw-stock/readonly-shadow-exposure").status_code == 405
