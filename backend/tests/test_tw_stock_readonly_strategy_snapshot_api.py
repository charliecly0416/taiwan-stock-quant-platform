"""R14 readonly strategy snapshot API tests."""
from __future__ import annotations

import json
from pathlib import Path

from flask import Flask

from app.routes.readonly_strategy_snapshot import readonly_strategy_snapshot_bp


LATEST_POINTER = Path("data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json")


def _client():
    app = Flask(__name__)
    app.register_blueprint(readonly_strategy_snapshot_bp, url_prefix="/api/tw-stock")
    return app.test_client()


def test_readonly_strategy_snapshot_latest_get_returns_readonly_payload():
    resp = _client().get("/api/tw-stock/readonly-strategy-snapshot")
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["code"] == 1
    data = payload["data"]
    assert data["ok"] is True
    assert data["schema_version"] == "readonly_strategy_snapshot_api_r14_v1"
    assert data["readonly_only"] is True
    assert data["not_order"] is True
    assert data["no_order_action"] is True
    assert data["not_target_position"] is True
    assert data["not_investment_advice"] is True
    assert data["production_trade_enabled"] is False
    latest = json.loads(LATEST_POINTER.read_text(encoding="utf-8"))
    assert data["asof"] == latest["asof"]
    assert data["manifest"]["artifact_type"] == "readonly_strategy_snapshot"
    assert data["snapshot"]["display_role"] == "primary_readonly_candidate"
    assert data["snapshot"]["model_id"] == "e4_frozen_qlib_2018_2022"
    assert data["snapshot"]["strategy_rule"] == "candidate_only_no_strategy_replay"
    assert data["validation"]["ok"] is True
    assert data["checksum"]["ok"] is True
    assert data["checksum"]["checked_file_count"] == 4
    assert data["checksum"]["self_included"] is False
    assert data["forbidden_scope_audit"]["no_provider_publish"] is True
    assert data["forbidden_scope_audit"]["no_accepted_latest_switch"] is True
    assert data["forbidden_scope_audit"]["no_monitor_broker_order"] is True
    assert data["no_write_guarantees"]["read_only_http_method"] is True
    assert data["no_write_guarantees"]["does_not_touch_broker_or_orders"] is True


def test_readonly_strategy_snapshot_asof_get_returns_same_artifact():
    resp = _client().get("/api/tw-stock/readonly-strategy-snapshot/2026-06-18")
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["code"] == 1
    assert payload["data"]["asof"] == "2026-06-18"
    assert payload["data"]["sources"]["manifest"].endswith("/2026-06-18/manifest.json")
    assert payload["data"]["checksum"]["ok"] is True
    assert payload["data"]["checksum"]["checked_file_count"] == 12


def test_readonly_strategy_snapshot_routes_have_no_write_methods():
    client = _client()
    for path in [
        "/api/tw-stock/readonly-strategy-snapshot",
        "/api/tw-stock/readonly-strategy-snapshot/2026-06-18",
    ]:
        for method in ["post", "put", "patch", "delete"]:
            assert getattr(client, method)(path).status_code == 405


def test_readonly_strategy_snapshot_route_source_is_get_only_and_readonly():
    source = Path("backend/app/routes/readonly_strategy_snapshot.py").read_text(encoding="utf-8")
    assert '@readonly_strategy_snapshot_bp.route("/readonly-strategy-snapshot", methods=["GET"])' in source
    assert '@readonly_strategy_snapshot_bp.route("/readonly-strategy-snapshot/<asof>", methods=["GET"])' in source
    forbidden = [
        'methods=["POST"]',
        'methods=["PUT"]',
        'methods=["PATCH"]',
        'methods=["DELETE"]',
        'provider_publish',
        'accepted_latest_switch',
        'scan_symbol',
        'config_save',
        'quick_trade',
        'place_order',
    ]
    for item in forbidden:
        assert item not in source
