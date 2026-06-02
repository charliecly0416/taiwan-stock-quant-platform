"""API tests for qlib Option C TWStock research signals."""
from __future__ import annotations

from pathlib import Path

import pytest

from tests.test_tw_stock_qlib_option_c_signals import RUN_ID, make_artifact


def test_latest_quant_signals_api_top30_top50_all(client, monkeypatch, tmp_path):
    root = make_artifact(tmp_path)
    monkeypatch.setenv("QLIB_TW_OPTION_C_ROOT", str(root))

    for bucket, expected in [("top30", 30), ("top50", 50)]:
        resp = client.get(f"/api/tw-stock/quant/signals/latest?bucket={bucket}")
        payload = resp.get_json()
        assert resp.status_code == 200
        assert payload["code"] == 1
        data = payload["data"]
        assert data["bucket"] == bucket
        assert len(data["signals"]) == expected
        assert data["signals"][0]["symbol"] == "2330"
        assert data["signals"][0]["instrument"] == "TW2330"
        assert "qlib_score" in data["signals"][0]
        assert data["trading"]["orders_enabled"] is False
        assert data["trading"]["connects_to_broker"] is False
        assert "root" not in data["source"]
        assert all(not value.startswith("/") for value in data["source"].values())
        assert data["trading"]["research_signal_not_order"] is True

    resp = client.get("/api/tw-stock/quant/signals/latest?bucket=all")
    payload = resp.get_json()
    assert resp.status_code == 200
    assert payload["code"] == 1
    assert len(payload["data"]["top30"]) == 30
    assert len(payload["data"]["top50"]) == 50
    assert "signals" not in payload["data"]


def test_latest_quant_signals_api_invalid_bucket_returns_400(client, monkeypatch, tmp_path):
    root = make_artifact(tmp_path)
    monkeypatch.setenv("QLIB_TW_OPTION_C_ROOT", str(root))

    resp = client.get("/api/tw-stock/quant/signals/latest?bucket=bad")
    payload = resp.get_json()

    assert resp.status_code == 400
    assert payload["code"] == 0
    assert payload["data"]["status"] == "invalid_bucket"
    assert payload["data"]["trading"]["orders_enabled"] is False


def test_latest_quant_signals_api_blocked_run_does_not_return_signals(client, monkeypatch, tmp_path):
    root = make_artifact(tmp_path, summary_overrides={"status": "wait_state_data_refresh_needed"})
    monkeypatch.setenv("QLIB_TW_OPTION_C_ROOT", str(root))

    resp = client.get("/api/tw-stock/quant/signals/latest?bucket=top30")
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["code"] == 0
    assert payload["data"]["status"] == "wait_state_data_refresh_needed"
    assert payload["data"]["signals"] == []
    assert payload["data"]["trading"]["orders_enabled"] is False


class ApiFakeTrendService:
    def __init__(self) -> None:
        self.calls = []

    def analyze_symbol(self, *, symbol: str, limit: int = 120, as_of=None):
        self.calls.append((symbol, limit))
        return {
            "ok": True,
            "latest": {"date": "2026-06-01", "close": 222.2},
            "trend": {"label": "sideways", "score": 61.5},
            "quality": {"warnings": []},
        }


def test_latest_quant_signals_api_enrich_trend_returns_trend_fields(client, monkeypatch, tmp_path):
    root = make_artifact(tmp_path)
    monkeypatch.setenv("QLIB_TW_OPTION_C_ROOT", str(root))
    fake = ApiFakeTrendService()
    from app.routes import tw_stock as tw_stock_route
    monkeypatch.setattr(tw_stock_route, "trend_service", fake)

    resp = client.get("/api/tw-stock/quant/signals/latest?bucket=top30&enrichTrend=true&trendLimit=77")
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["code"] == 1
    data = payload["data"]
    assert data["enrichTrend"]["enabled"] is True
    assert data["enrichTrend"]["trendLimit"] == 77
    assert data["trading"]["orders_enabled"] is False
    assert data["trading"]["connects_to_broker"] is False
    first = data["signals"][0]
    assert "qlib_score" in first
    assert first["trend"]["ok"] is True
    assert first["trend"]["trend_label"] == "sideways"
    assert first["trend"]["trend_score"] == 61.5
    assert first["trend"]["latest_close"] == 222.2
    assert fake.calls[0] == ("2330", 77)


def test_latest_quant_signals_api_blocked_run_with_enrich_trend_does_not_return_signals(client, monkeypatch, tmp_path):
    root = make_artifact(tmp_path, summary_overrides={"status": "wait_state_data_refresh_needed"})
    monkeypatch.setenv("QLIB_TW_OPTION_C_ROOT", str(root))

    resp = client.get("/api/tw-stock/quant/signals/latest?bucket=top30&enrichTrend=true")
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["code"] == 0
    assert payload["data"]["status"] == "wait_state_data_refresh_needed"
    assert payload["data"]["signals"] == []
    assert payload["data"]["trading"]["orders_enabled"] is False


def test_latest_quant_signals_api_blocks_recorder_mismatch(client, monkeypatch, tmp_path):
    root = make_artifact(tmp_path, metadata_overrides={"frozen_recorder": "not-the-frozen-recorder"})
    monkeypatch.setenv("QLIB_TW_OPTION_C_ROOT", str(root))

    resp = client.get("/api/tw-stock/quant/signals/latest?bucket=top30")
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["code"] == 0
    assert payload["data"]["status"] == "blocked_validation_failed"
    assert payload["data"]["signals"] == []
    assert payload["data"]["trading"]["orders_enabled"] is False


def test_latest_quant_signals_api_blocks_summary_path_mismatch(client, monkeypatch, tmp_path):
    root = make_artifact(tmp_path, summary_overrides={"top30_path": f"data_tw/experiments/option_c_daily_signal/{RUN_ID}/top50_signals.csv"})
    monkeypatch.setenv("QLIB_TW_OPTION_C_ROOT", str(root))

    resp = client.get("/api/tw-stock/quant/signals/latest?bucket=top30")
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["code"] == 0
    assert payload["data"]["status"] == "blocked_validation_failed"
    assert payload["data"]["signals"] == []
    assert payload["data"]["trading"]["orders_enabled"] is False


def test_qlib_option_c_new_code_does_not_reference_trading_paths():
    root = Path(__file__).resolve().parents[1]
    service = (root / "app/services/tw_stock_qlib_option_c.py").read_text(encoding="utf-8").lower()
    forbidden = [
        "app.services.tw_stock_paper",
        "app.services.broker",
        "ib_insync",
        "alpaca",
        "mt5",
        "pending_orders",
        "submit_order(",
        "place_order(",
        "send_order(",
        "target_weight(",
        "target_position(",
    ]
    service_text = service
    # Safety response flag names are allowed; this checks for trading integrations/calls.
    for item in forbidden:
        assert item not in service_text, f"qlib reader references forbidden path/text: {item}"



def test_quant_signal_runs_api_lists_metadata_without_signals(client, monkeypatch, tmp_path):
    root = make_artifact(tmp_path, run_id=RUN_ID)
    blocked_id = "option_c_daily_signal_20260531_20260531T010203Z"
    make_artifact(
        tmp_path,
        run_id=blocked_id,
        summary_overrides={"status": "wait_state_data_refresh_needed", "reason": "fixture stale"},
        metadata_overrides={"run_id": blocked_id, "status": "wait_state_data_refresh_needed", "created_at": "2026-05-31T01:02:03+00:00"},
    )
    monkeypatch.setenv("QLIB_TW_OPTION_C_ROOT", str(root))

    resp = client.get("/api/tw-stock/quant/signals/runs?limit=20&status=all")
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["code"] == 1
    data = payload["data"]
    assert data["trading"]["orders_enabled"] is False
    assert len(data["items"]) == 2
    assert all("signals" not in item for item in data["items"])
    assert any(item["accepted_validated"] is True for item in data["items"] if item["run_id"] == RUN_ID)
    assert any(item["status"] == "wait_state_data_refresh_needed" for item in data["items"])


def test_quant_signal_runs_api_status_filter(client, monkeypatch, tmp_path):
    root = make_artifact(tmp_path, run_id=RUN_ID)
    blocked_id = "option_c_daily_signal_20260531_20260531T010203Z"
    make_artifact(
        tmp_path,
        run_id=blocked_id,
        summary_overrides={"status": "blocked_formal_validation_failed"},
        metadata_overrides={"run_id": blocked_id, "status": "blocked_formal_validation_failed", "created_at": "2026-05-31T01:02:03+00:00"},
    )
    monkeypatch.setenv("QLIB_TW_OPTION_C_ROOT", str(root))

    accepted = client.get("/api/tw-stock/quant/signals/runs?status=accepted").get_json()["data"]
    blocked = client.get("/api/tw-stock/quant/signals/runs?status=blocked").get_json()["data"]

    assert [item["run_id"] for item in accepted["items"]] == [RUN_ID]
    assert [item["run_id"] for item in blocked["items"]] == [blocked_id]


def test_quant_signal_run_detail_api_accepted_all_and_enrich(client, monkeypatch, tmp_path):
    root = make_artifact(tmp_path)
    monkeypatch.setenv("QLIB_TW_OPTION_C_ROOT", str(root))
    fake = ApiFakeTrendService()
    from app.routes import tw_stock as tw_stock_route
    monkeypatch.setattr(tw_stock_route, "trend_service", fake)

    resp = client.get(f"/api/tw-stock/quant/signals/runs/{RUN_ID}?bucket=all&enrichTrend=true&trendLimit=77")
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["code"] == 1
    data = payload["data"]
    assert data["ok"] is True
    assert len(data["top30"]) == 30
    assert len(data["top50"]) == 50
    assert data["top30"][0]["trend"]["trend_label"] == "sideways"
    assert data["trading"]["research_signal_not_order"] is True
    assert fake.calls[0] == ("2330", 77)


def test_quant_signal_run_detail_api_blocked_returns_metadata_only(client, monkeypatch, tmp_path):
    root = make_artifact(
        tmp_path,
        summary_overrides={"status": "wait_state_data_refresh_needed", "reason": "fixture stale"},
        metadata_overrides={"status": "wait_state_data_refresh_needed"},
    )
    monkeypatch.setenv("QLIB_TW_OPTION_C_ROOT", str(root))

    resp = client.get(f"/api/tw-stock/quant/signals/runs/{RUN_ID}?bucket=top30&enrichTrend=true")
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["code"] == 1
    data = payload["data"]
    assert data["ok"] is False
    assert data["signals"] == []
    assert data["top30"] == []
    assert data["top50"] == []
    assert data["status"] == "wait_state_data_refresh_needed"
    assert data["summary"]["status"] == "wait_state_data_refresh_needed"
    assert data["trading"]["orders_enabled"] is False


def test_quant_signal_run_detail_api_rejects_invalid_run_id(client, monkeypatch, tmp_path):
    root = make_artifact(tmp_path)
    monkeypatch.setenv("QLIB_TW_OPTION_C_ROOT", str(root))

    resp = client.get("/api/tw-stock/quant/signals/runs/not_option_c_daily_signal")
    payload = resp.get_json()

    assert resp.status_code == 400
    assert payload["code"] == 0
    assert payload["data"]["status"] == "invalid_run_id"
    assert payload["data"]["signals"] == []
    assert payload["data"]["trading"]["orders_enabled"] is False


def test_quant_signal_runs_api_invalid_status_returns_400(client, monkeypatch, tmp_path):
    root = make_artifact(tmp_path)
    monkeypatch.setenv("QLIB_TW_OPTION_C_ROOT", str(root))

    resp = client.get("/api/tw-stock/quant/signals/runs?status=bad")
    payload = resp.get_json()

    assert resp.status_code == 400
    assert payload["code"] == 0
    assert payload["data"]["status"] == "invalid_status"



def test_quant_signal_health_api_accepted(client, monkeypatch, tmp_path):
    root = make_artifact(tmp_path)
    monkeypatch.setenv("QLIB_TW_OPTION_C_ROOT", str(root))

    resp = client.get("/api/tw-stock/quant/signals/health")
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["code"] == 1
    data = payload["data"]
    assert data["status"] == "accepted"
    assert data["latest"]["exists"] is True
    assert data["latest"]["accepted_validated"] is True
    assert data["dataAvailability"]["trend_data_dependency"] == "TWStock local daily bars"
    assert data["dataAvailability"]["backtest_data_dependency"] == "qd_tw_stock_daily_bars"
    assert data["trading"]["orders_enabled"] is False
    assert data["trading"]["research_signal_not_order"] is True
    assert "signals" not in data
    assert "top30" not in data
    assert "top50" not in data


def test_quant_signal_health_api_missing_latest(client, monkeypatch, tmp_path):
    monkeypatch.setenv("QLIB_TW_OPTION_C_ROOT", str(tmp_path))

    resp = client.get("/api/tw-stock/quant/signals/health")
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["code"] == 1
    data = payload["data"]
    assert data["ok"] is False
    assert data["status"] == "missing_latest_signal"
    assert data["latest"]["exists"] is False
    assert data["freshness"]["stale"] is True
    assert data["freshness"]["stale_reason"] == "missing_latest_signal"
    assert data["trading"]["connects_to_broker"] is False
