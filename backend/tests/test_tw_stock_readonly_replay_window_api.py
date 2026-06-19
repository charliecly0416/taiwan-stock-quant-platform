"""Readonly replay window API tests."""
from __future__ import annotations

from pathlib import Path

from flask import Flask

from app.services import readonly_replay_window as replay_service
from app.services import readonly_replay_window_index as replay_index

from app.routes.readonly_replay_window import readonly_replay_window_bp
from app.routes.readonly_replay_window_index import readonly_replay_window_index_bp


def _client():
    app = Flask(__name__)
    app.register_blueprint(readonly_replay_window_bp, url_prefix="/api/tw-stock")
    app.register_blueprint(readonly_replay_window_index_bp, url_prefix="/api/tw-stock")
    return app.test_client()


def test_readonly_replay_window_clean_model_a_detail_ok():
    resp = _client().get(
        "/api/tw-stock/readonly-replay-window",
        query_string={
            "model_id": "e4_frozen_qlib_2018_2022",
            "strategy_rule": "top50_exit_one_worst_sell",
            "start": "2026-01-01",
            "end": "2026-05-07",
        },
    )
    payload = resp.get_json()
    assert resp.status_code == 200
    data = payload["data"]
    assert data["ok"] is True
    assert data["readonly_only"] is True
    assert data["model_id"] == "e4_frozen_qlib_2018_2022"
    assert data["strategy_rule"] == "top50_exit_one_worst_sell"
    assert data["execution_price_mode"] == "next_open"
    assert data["checksum"]["ok"] is True
    assert data["summary"]


def test_readonly_replay_window_clean_model_b_detail_ok():
    resp = _client().get(
        "/api/tw-stock/readonly-replay-window",
        query_string={
            "model_id": "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025",
            "strategy_rule": "top50_exit_one_worst_sell",
            "start": "2026-01-01",
            "end": "2026-05-07",
        },
    )
    payload = resp.get_json()
    assert resp.status_code == 200
    data = payload["data"]
    assert data["ok"] is True
    assert data["model_id"] == "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025"
    assert data["execution_price_mode"] == "next_open"
    assert data["checksum"]["ok"] is True
    assert data["summary"]


def test_readonly_replay_window_rejects_training_window_by_backend():
    resp = _client().get(
        "/api/tw-stock/readonly-replay-window",
        query_string={
            "model_id": "e4_frozen_qlib_2018_2022",
            "strategy_rule": "top50_exit_one_worst_sell",
            "start": "2025-01-01",
            "end": "2025-12-31",
        },
    )
    payload = resp.get_json()
    assert resp.status_code == 400
    assert payload["code"] == 0
    assert payload["data"]["ok"] is False
    assert payload["data"]["status"] in {
        "requested_window_before_allowed_replay_start",
        "requested_window_overlaps_ltr_training_window",
    }
    assert payload["data"]["allowed_replay_start_min"] == "2026-01-01"


def test_readonly_replay_window_rejects_diagnostic_rule_as_valid_strategy():
    resp = _client().get(
        "/api/tw-stock/readonly-replay-window",
        query_string={
            "model_id": "e4_frozen_qlib_2018_2022",
            "strategy_rule": "one_sell_one_buy_buggy_e8r",
            "start": "2026-01-01",
            "end": "2026-05-07",
        },
    )
    payload = resp.get_json()
    assert resp.status_code == 400
    assert payload["data"]["status"] == "research_only_strategy_not_valid_strategy_evidence"


def test_readonly_replay_window_rejects_old_model_generated_window():
    resp = _client().get(
        "/api/tw-stock/readonly-replay-window",
        query_string={
            "model_id": "e4_frozen_qlib_2023_2025_ltr",
            "strategy_rule": "top50_exit_one_worst_sell",
            "start": "2026-01-02",
            "end": "2026-05-07",
        },
    )
    payload = resp.get_json()
    assert resp.status_code == 400
    assert payload["code"] == 0
    assert payload["data"]["status"] == "deprecated_model_id"


def test_readonly_replay_window_index_get_returns_clean_windows_only():
    resp = _client().get("/api/tw-stock/readonly-replay-window-index")
    payload = resp.get_json()
    assert resp.status_code == 200
    assert payload["code"] == 1
    data = payload["data"]
    assert data["ok"] is True
    assert data["schema_version"] == "readonly_replay_window_index_d7_v1"
    assert "e4_frozen_qlib_2023_2025_ltr" not in str(data["windows"])
    assert len(data["windows"]) == 2
    assert {row["model_id"] for row in data["windows"]} == {"e4_frozen_qlib_2018_2022", "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025"}
    assert all(row["strategy_rule"] == "top50_exit_one_worst_sell" for row in data["windows"])
    assert all(row["checksum"]["ok"] is True for row in data["windows"])


def test_fixed_window_requires_d7_index_latest(monkeypatch, tmp_path):
    monkeypatch.setattr(replay_index, "LATEST_PATH", tmp_path / "missing_latest.json")
    resp = _client().get(
        "/api/tw-stock/readonly-replay-window",
        query_string={
            "model_id": "e4_frozen_qlib_2018_2022",
            "strategy_rule": "top50_exit_one_worst_sell",
            "start": "2026-01-01",
            "end": "2026-05-07",
        },
    )
    payload = resp.get_json()
    assert resp.status_code == 404
    assert payload["data"]["status"] == "missing_artifact"


def test_fixed_window_rejects_when_index_entry_missing(monkeypatch):
    def fake_index():
        return {
            "ok": True,
            "schema_version": "readonly_replay_window_index_d7_v1",
            "windows": [
                {
                    "window_key": "20260102_20260507",
                    "window_type": "generated_readonly",
                    "model_id": "e4_frozen_qlib_2018_2022",
                    "strategy_rule": "top50_exit_one_worst_sell",
                    "start": "2026-01-02",
                    "end": "2026-05-07",
                }
            ],
            "manifest": {"windows": []},
            "sources": {"manifest": "data_tw/artifacts/readonly_replay_windows/d7/manifest.json"},
        }

    monkeypatch.setattr(replay_index, "load_readonly_replay_window_index", fake_index)
    resp = _client().get(
        "/api/tw-stock/readonly-replay-window",
        query_string={
            "model_id": "e4_frozen_qlib_2018_2022",
            "strategy_rule": "top50_exit_one_worst_sell",
            "start": "2026-01-01",
            "end": "2026-05-07",
        },
    )
    payload = resp.get_json()
    assert resp.status_code == 404
    assert payload["data"]["status"] == "no_audited_replay_artifact_for_window"


def test_fixed_window_clean_request_does_not_fallback_to_old_index_entry():
    payload = replay_service.load_readonly_replay_window(
        model_id="e4_frozen_qlib_2018_2022",
        strategy_rule="top50_exit_one_worst_sell",
        start="2026-01-01",
        end="2026-05-07",
    )
    assert payload["ok"] is True
    assert payload["model_id"] == "e4_frozen_qlib_2018_2022"
    assert "e4_frozen_qlib_2023_2025_ltr" not in str(payload)


def test_readonly_replay_window_route_has_no_write_methods():
    client = _client()
    for method in ["post", "put", "patch", "delete"]:
        assert getattr(client, method)("/api/tw-stock/readonly-replay-window").status_code == 405


def test_readonly_replay_window_route_source_is_get_only_and_readonly():
    source = Path("backend/app/routes/readonly_replay_window.py").read_text(encoding="utf-8")
    assert '@readonly_replay_window_bp.route("/readonly-replay-window", methods=["GET"])' in source
    forbidden = ['methods=["POST"]', 'methods=["PUT"]', 'methods=["PATCH"]', 'methods=["DELETE"]', 'provider_publish', 'accepted_latest_switch', 'scan_symbol', 'config_save', 'quick_trade', 'place_order']
    for item in forbidden:
        assert item not in source


def test_readonly_replay_window_rejects_old_model_id():
    resp = _client().get(
        "/api/tw-stock/readonly-replay-window",
        query_string={
            "model_id": "e4_frozen_qlib_2023_2025_ltr",
            "strategy_rule": "top50_exit_one_worst_sell",
            "start": "2026-01-01",
            "end": "2026-05-07",
        },
    )
    payload = resp.get_json()
    assert resp.status_code == 400
    assert payload["code"] == 0
    assert payload["data"]["status"] == "deprecated_model_id"


def test_readonly_replay_window_index_filters_old_model_defaults():
    data = replay_index.load_readonly_replay_window_index()
    serialized = str(data.get("windows"))
    assert "e4_frozen_qlib_2023_2025_ltr" not in serialized
    assert len(data["windows"]) == 2
    assert {row["model_id"] for row in data["windows"]} == {"e4_frozen_qlib_2018_2022", "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025"}
    assert all(row["strategy_rule"] == "top50_exit_one_worst_sell" for row in data["windows"])
    assert all(row["checksum"]["ok"] is True for row in data["windows"])
