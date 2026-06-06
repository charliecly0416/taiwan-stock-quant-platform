"""API tests for qlib Option C TWStock research signals."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from tests.test_tw_stock_qlib_option_c_signals import RECORDER, RUN_ID, make_artifact


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



def _write_rank_change_csv(path: Path, *, asof: str, symbols: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["asof", "instrument", "score", "rank", "source_model_recorder", "diagnostic_only", "research_signal_not_order"],
        )
        writer.writeheader()
        for rank, symbol in enumerate(symbols, start=1):
            writer.writerow({
                "asof": asof,
                "instrument": f"TW{symbol}",
                "score": f"{0.25 - rank / 1000:.12f}",
                "rank": rank,
                "source_model_recorder": RECORDER,
                "diagnostic_only": "True",
                "research_signal_not_order": "True",
            })


def _write_rank_change_run(root: Path, *, run_id: str, asof: str, top30_symbols: list[str], top50_symbols: list[str], latest: bool = False) -> None:
    run_dir = root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    rel = f"data_tw/experiments/option_c_daily_signal/{run_id}"
    summary = {
        "status": "accepted",
        "asof": asof,
        "prediction_rows": 150,
        "top30_rows": 30,
        "top50_rows": 50,
        "finite_prediction_share": 1.0,
        "top30_path": f"{rel}/top30_signals.csv",
        "top50_path": f"{rel}/top50_signals.csv",
        "diagnostic_only": True,
        "research_signal_not_order": True,
        "paper_trading_started": False,
        "live_trading_started": False,
        "target_trades_generated": False,
        "executable_orders_generated": False,
    }
    metadata = {
        "run_id": run_id,
        "created_at": f"{asof}T12:00:00+00:00",
        "status": "accepted",
        "asof": asof,
        "dry_run": False,
        "allow_refresh": False,
        "frozen_recorder": RECORDER,
        "paper_trading_started": False,
        "live_trading_started": False,
        "target_trades_generated": False,
        "executable_orders_generated": False,
        "model_retraining_performed": False,
        "model_tuning_performed": False,
        "provider_switch_performed": False,
        "FinMind_fallback_used": False,
        "mixed_provider_fill_used": False,
    }
    (run_dir / "signal_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (run_dir / "run_metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    _write_rank_change_csv(run_dir / "top30_signals.csv", asof=asof, symbols=top30_symbols)
    _write_rank_change_csv(run_dir / "top50_signals.csv", asof=asof, symbols=top50_symbols)
    if latest:
        latest_doc = {
            "status": "accepted",
            "created_at": f"{asof}T12:01:00+00:00",
            "run_dir": rel,
            "asof": asof,
            "top30_signals": f"{rel}/top30_signals.csv",
            "top50_signals": f"{rel}/top50_signals.csv",
            "diagnostic_only": True,
            "research_signal_not_order": True,
        }
        (root / "latest_signal.json").write_text(json.dumps(latest_doc), encoding="utf-8")


def _symbols(start: int, count: int) -> list[str]:
    return [str(start + i) for i in range(count)]


def test_rank_changes_api_compares_latest_with_previous_accepted_run(client, monkeypatch, tmp_path):
    root = tmp_path
    older_top30 = ["2317", "2330"] + _symbols(2400, 28)
    prev_top30 = ["2454", "2317", "2330"] + _symbols(2500, 27)
    current_top30 = ["2317", "2330", "3008"] + _symbols(2600, 27)
    older_top50 = older_top30 + _symbols(3400, 20)
    prev_top50 = prev_top30 + ["3008"] + _symbols(3500, 19)
    current_top50 = current_top30 + ["2454"] + _symbols(3600, 19)
    _write_rank_change_run(root, run_id="option_c_daily_signal_20260531_20260531T120000Z", asof="2026-05-31", top30_symbols=older_top30, top50_symbols=older_top50)
    _write_rank_change_run(root, run_id="option_c_daily_signal_20260603_20260603T120000Z", asof="2026-06-03", top30_symbols=prev_top30, top50_symbols=prev_top50)
    _write_rank_change_run(root, run_id="option_c_daily_signal_20260604_20260604T120000Z", asof="2026-06-04", top30_symbols=current_top30, top50_symbols=current_top50, latest=True)
    monkeypatch.setenv("QLIB_TW_OPTION_C_ROOT", str(root))

    resp = client.get("/api/tw-stock/quant/signals/rank-changes?bucket=top30&lookback=10")
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["code"] == 1
    data = payload["data"]
    assert data["status"] == "ok"
    assert data["asof"] == "2026-06-04"
    assert data["previous_asof"] == "2026-06-03"
    assert data["summary"]["entered_count"] == 28
    assert data["summary"]["exited_count"] == 28
    assert data["summary"]["stayed_count"] == 2
    entered = {item["symbol"]: item for item in data["entered"]}
    exited = {item["symbol"]: item for item in data["exited"]}
    stayed = {item["symbol"]: item for item in data["stayed"]}
    assert entered["3008"]["change_type"] == "entered"
    assert exited["2454"]["change_type"] == "exited"
    assert exited["2454"]["current_top50_rank"] == 31
    assert stayed["2317"]["rank_delta"] == 1
    assert stayed["2317"]["streak_days"] == 3
    assert data["watch_candidates"][0]["current_rank"] == 31
    assert data["trading"]["orders_enabled"] is False
    assert data["trading"]["research_signal_not_order"] is True


def test_rank_changes_api_invalid_bucket_returns_400(client, monkeypatch, tmp_path):
    root = make_artifact(tmp_path)
    monkeypatch.setenv("QLIB_TW_OPTION_C_ROOT", str(root))

    resp = client.get("/api/tw-stock/quant/signals/rank-changes?bucket=all")
    payload = resp.get_json()

    assert resp.status_code == 400
    assert payload["code"] == 0
    assert payload["data"]["status"] == "invalid_bucket"
    assert payload["data"]["trading"]["orders_enabled"] is False
