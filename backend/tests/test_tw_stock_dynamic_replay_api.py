from __future__ import annotations

import json

from app.services import tw_stock_dynamic_replay


def test_dynamic_replay_options_expose_only_policy_eligible_tracks(client):
    response = client.get("/api/tw-stock/readonly-replays/options")

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["readonly_only"] is True
    assert [item["track_id"] for item in payload["models"]] == ["model_a_only"]
    assert payload["strategies"][0]["strategy_rule"] == "top50_exit_one_worst_sell"
    assert payload["policy"]["allowed_replay_start_min"]
    assert payload["policy"]["latest_available_signal_date"]


def test_dynamic_replay_rejects_unregistered_payload_before_starting_task(client):
    response = client.post(
        "/api/tw-stock/readonly-replays",
        json={
            "model_track_id": "bad/track",
            "strategy_rule": "top50_exit_one_worst_sell",
            "start_date": "2026-01-01",
            "end_date": "2026-01-02",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["data"]["status"] == "invalid_request"


def test_dynamic_replay_status_rejects_invalid_task_id(client):
    response = client.get("/api/tw-stock/readonly-replays/not-a-task")

    assert response.status_code == 400
    assert response.get_json()["data"]["status"] == "invalid_job_id"


def test_reused_replay_execution_includes_audited_metrics(tmp_path, monkeypatch):
    monkeypatch.setattr(tw_stock_dynamic_replay, "ROOT", tmp_path)
    manifest = tmp_path / "manifest.json"
    metrics = tmp_path / "metrics.json"
    metrics.write_text(json.dumps({"total_return": "0.12", "trading_days": "5"}), encoding="utf-8")
    manifest.write_text(json.dumps({"artifacts": {"metrics": "metrics.json"}}), encoding="utf-8")

    enriched = tw_stock_dynamic_replay._enrich_execution({"artifact": {"manifest": "manifest.json"}})

    assert enriched["replay_metrics"] == {"total_return": "0.12", "trading_days": "5"}
    assert enriched["replay_manifest"] == "manifest.json"
