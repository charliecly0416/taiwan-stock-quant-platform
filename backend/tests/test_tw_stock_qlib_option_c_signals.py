"""Tests for qlib Option C TWStock research signal reader."""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.services.tw_stock_qlib_option_c import QlibOptionCSignalError, QlibOptionCSignalReader

RECORDER = "950741cfd5f14ee5a05464fec3e12e0a"
RUN_ID = "option_c_daily_signal_20260601_20260601T121228Z"


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _write_csv(path: Path, count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["asof", "instrument", "score", "rank", "source_model_recorder", "diagnostic_only", "research_signal_not_order"],
        )
        writer.writeheader()
        for rank in range(1, count + 1):
            symbol = 2300 + rank
            if rank == 1:
                symbol = 2330
            writer.writerow({
                "asof": "2026-06-01",
                "instrument": f"TW{symbol}",
                "score": f"{0.2 - rank / 1000:.12f}",
                "rank": rank,
                "source_model_recorder": RECORDER,
                "diagnostic_only": "True",
                "research_signal_not_order": "True",
            })


def _rewrite_csv_rows(path: Path, mutate) -> None:
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    mutate(rows)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def make_artifact(root: Path, *, run_id: str = RUN_ID, summary_overrides: dict | None = None, metadata_overrides: dict | None = None, latest_overrides: dict | None = None) -> Path:
    run_dir = root / run_id
    latest = {
        "created_at": "2026-06-01T12:12:40+00:00",
        "run_dir": f"data_tw/experiments/option_c_daily_signal/{run_id}",
        "asof": "2026-06-01",
        "top30_signals": f"data_tw/experiments/option_c_daily_signal/{RUN_ID}/top30_signals.csv",
        "top50_signals": f"data_tw/experiments/option_c_daily_signal/{RUN_ID}/top50_signals.csv",
        "diagnostic_only": True,
        "research_signal_not_order": True,
    }
    latest.update(latest_overrides or {})
    summary = {
        "status": "accepted",
        "asof": "2026-06-01",
        "prediction_rows": 150,
        "top30_rows": 30,
        "top50_rows": 50,
        "finite_prediction_share": 1.0,
        "top30_path": f"data_tw/experiments/option_c_daily_signal/{RUN_ID}/top30_signals.csv",
        "top50_path": f"data_tw/experiments/option_c_daily_signal/{RUN_ID}/top50_signals.csv",
        "diagnostic_only": True,
        "research_signal_not_order": True,
        "paper_trading_started": False,
        "live_trading_started": False,
        "target_trades_generated": False,
        "executable_orders_generated": False,
    }
    summary.update(summary_overrides or {})
    metadata = {
        "run_id": run_id,
        "created_at": "2026-06-01T12:12:40+00:00",
        "status": "accepted",
        "asof": "2026-06-01",
        "dry_run": False,
        "allow_refresh": False,
        "frozen_recorder": RECORDER,
        "config": "configs/tw_yahoo_primary_alpha158.yaml",
        "provider_uri": "data_tw/experiments/yahoo_adjusted_primary/qlib_bin",
        "market": "tw_liquid_dyn",
        "benchmark": "TWII",
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
    metadata.update(metadata_overrides or {})
    _write_json(root / "latest_signal.json", latest)
    _write_json(run_dir / "signal_summary.json", summary)
    _write_json(run_dir / "run_metadata.json", metadata)
    _write_csv(run_dir / "top30_signals.csv", 30)
    _write_csv(run_dir / "top50_signals.csv", 50)
    return root


def test_reader_loads_accepted_top30_top50_and_normalizes_symbol(tmp_path):
    root = make_artifact(tmp_path)
    reader = QlibOptionCSignalReader(root=str(root))

    top30 = reader.latest(bucket="top30")
    top50 = reader.latest(bucket="top50")
    all_payload = reader.latest(bucket="all")

    assert top30["status"] == "accepted"
    assert len(top30["signals"]) == 30
    assert len(top50["signals"]) == 50
    assert len(all_payload["top30"]) == 30
    assert len(all_payload["top50"]) == 50
    first = top30["signals"][0]
    assert first["instrument"] == "TW2330"
    assert first["symbol"] == "2330"
    assert "qlib_score" in first
    assert "score" not in first
    assert first["source_model_recorder"] == RECORDER
    assert top30["trading"]["orders_enabled"] is False
    assert top30["trading"]["research_signal_not_order"] is True
    assert "run_metadata_missing_research_only_flags_verified_by_latest_and_summary" in top30["warnings"]




def test_reader_exposes_target_horizon_research_semantics(tmp_path):
    root = make_artifact(tmp_path, summary_overrides={"target_date": "2026-06-02"})
    payload = QlibOptionCSignalReader(root=str(root)).latest(bucket="top30")

    assert payload["target_horizon"] == "next_trading_day_research_ranking"
    assert payload["target_date"] == "2026-06-02"
    assert payload["signal_semantics"] == "research_only_cross_sectional_ranking"
    assert payload["recommendation_semantics"] == "watchlist_not_trade_advice"
    assert payload["trading"]["orders_enabled"] is False

@pytest.mark.parametrize("summary_overrides", [
    {"status": "blocked_formal_validation_failed"},
    {"prediction_rows": 149},
    {"top30_rows": 29},
    {"top50_rows": 49},
    {"finite_prediction_share": 0.99},
    {"diagnostic_only": False},
    {"research_signal_not_order": False},
    {"paper_trading_started": True},
    {"live_trading_started": True},
    {"target_trades_generated": True},
    {"executable_orders_generated": True},
])
def test_reader_blocks_invalid_summary_conditions(tmp_path, summary_overrides):
    root = make_artifact(tmp_path, summary_overrides=summary_overrides)

    with pytest.raises(QlibOptionCSignalError):
        QlibOptionCSignalReader(root=str(root)).latest(bucket="top30")


@pytest.mark.parametrize("metadata_overrides", [
    {"status": "failed"},
    {"paper_trading_started": True},
    {"live_trading_started": True},
    {"target_trades_generated": True},
    {"executable_orders_generated": True},
    {"model_retraining_performed": True},
    {"model_tuning_performed": True},
    {"provider_switch_performed": True},
    {"FinMind_fallback_used": True},
    {"mixed_provider_fill_used": True},
])
def test_reader_blocks_invalid_metadata_safety_flags(tmp_path, metadata_overrides):
    root = make_artifact(tmp_path, metadata_overrides=metadata_overrides)

    with pytest.raises(QlibOptionCSignalError):
        QlibOptionCSignalReader(root=str(root)).latest(bucket="top30")


def test_reader_missing_latest_returns_missing_status(tmp_path):
    reader = QlibOptionCSignalReader(root=str(tmp_path))

    with pytest.raises(QlibOptionCSignalError) as exc:
        reader.latest()

    assert exc.value.status == "missing_latest_signal"


def test_reader_blocks_csv_missing_and_path_escape(tmp_path):
    root = make_artifact(tmp_path)
    (root / RUN_ID / "top30_signals.csv").unlink()
    with pytest.raises(QlibOptionCSignalError, match="CSV"):
        QlibOptionCSignalReader(root=str(root)).latest(bucket="top30")

    root2 = make_artifact(tmp_path / "root2", latest_overrides={"top30_signals": "../outside.csv"})
    with pytest.raises(QlibOptionCSignalError) as exc:
        QlibOptionCSignalReader(root=str(root2)).latest(bucket="top30")
    assert exc.value.status == "path_outside_root"


def test_reader_blocks_malformed_csv_row(tmp_path):
    root = make_artifact(tmp_path)
    path = root / RUN_ID / "top30_signals.csv"
    text = path.read_text(encoding="utf-8")
    text = text.replace("TW2330", "2330", 1)
    path.write_text(text, encoding="utf-8")

    with pytest.raises(QlibOptionCSignalError, match="instrument"):
        QlibOptionCSignalReader(root=str(root)).latest(bucket="top30")


class FakeTrendService:
    def __init__(self, fail_symbols: set[str] | None = None) -> None:
        self.fail_symbols = fail_symbols or set()
        self.calls = []

    def analyze_symbol(self, *, symbol: str, limit: int = 120, as_of=None):
        self.calls.append((symbol, limit))
        if symbol in self.fail_symbols:
            raise RuntimeError("trend fixture failure")
        return {
            "ok": True,
            "latest": {"date": "2026-06-01", "close": 123.4},
            "trend": {"label": "uptrend", "score": 72.5},
            "quality": {"warnings": ["fixture_warning"] if symbol == "2330" else []},
        }


def test_reader_enrich_trend_false_keeps_original_shape(tmp_path):
    root = make_artifact(tmp_path)
    payload = QlibOptionCSignalReader(root=str(root)).latest(bucket="top30", enrich_trend=False)

    assert payload["enrichTrend"]["enabled"] is False
    assert "trend" not in payload["signals"][0]
    assert "qlib_score" in payload["signals"][0]


def test_reader_enriches_selected_bucket_with_independent_trend_fields(tmp_path):
    root = make_artifact(tmp_path)
    trend = FakeTrendService()

    payload = QlibOptionCSignalReader(root=str(root)).latest(bucket="top30", enrich_trend=True, trend_limit=88, trend_service=trend)

    assert payload["enrichTrend"] == {"enabled": True, "requested": True, "trendLimit": 88}
    assert len(trend.calls) == 30
    assert trend.calls[0] == ("2330", 88)
    first = payload["signals"][0]
    assert "qlib_score" in first
    assert first["trend"]["ok"] is True
    assert first["trend"]["trend_label"] == "uptrend"
    assert first["trend"]["trend_score"] == 72.5
    assert first["trend"]["latest_close"] == 123.4
    assert first["trend"]["latest_date"] == "2026-06-01"
    assert "combined_score" not in first
    assert "buy_score" not in first
    assert "target_weight" not in first
    assert "target_position" not in first


def test_reader_enrich_trend_partial_failure_keeps_accepted_payload(tmp_path):
    root = make_artifact(tmp_path)
    trend = FakeTrendService(fail_symbols={"2330"})

    payload = QlibOptionCSignalReader(root=str(root)).latest(bucket="top30", enrich_trend=True, trend_service=trend)

    assert payload["status"] == "accepted"
    first = payload["signals"][0]
    assert first["symbol"] == "2330"
    assert first["trend"]["ok"] is False
    assert "trend fixture failure" in first["trend"]["error"]
    assert first["trend"]["quality_warnings"] == ["trend_service_error"]


def test_reader_enrich_trend_limit_is_clamped(tmp_path):
    root = make_artifact(tmp_path)
    low = FakeTrendService()
    high = FakeTrendService()

    low_payload = QlibOptionCSignalReader(root=str(root)).latest(bucket="top30", enrich_trend=True, trend_limit=1, trend_service=low)
    high_payload = QlibOptionCSignalReader(root=str(root)).latest(bucket="top30", enrich_trend=True, trend_limit=9999, trend_service=high)

    assert low_payload["enrichTrend"]["trendLimit"] == 20
    assert high_payload["enrichTrend"]["trendLimit"] == 500
    assert low.calls[0][1] == 20
    assert high.calls[0][1] == 500


def test_reader_blocks_unexpected_metadata_recorder(tmp_path):
    root = make_artifact(tmp_path, metadata_overrides={"frozen_recorder": "not-the-frozen-recorder"})

    with pytest.raises(QlibOptionCSignalError, match="frozen_recorder"):
        QlibOptionCSignalReader(root=str(root)).latest(bucket="top30")


def test_reader_blocks_unexpected_csv_recorder(tmp_path):
    root = make_artifact(tmp_path)
    path = root / RUN_ID / "top30_signals.csv"
    _rewrite_csv_rows(path, lambda rows: rows[0].update({"source_model_recorder": "not-the-frozen-recorder"}))

    with pytest.raises(QlibOptionCSignalError, match="source_model_recorder"):
        QlibOptionCSignalReader(root=str(root)).latest(bucket="top30")


def test_reader_blocks_summary_recorder_mismatch_when_present(tmp_path):
    root = make_artifact(tmp_path, summary_overrides={"recorder_id": "not-the-frozen-recorder"})

    with pytest.raises(QlibOptionCSignalError, match="signal_summary.recorder_id"):
        QlibOptionCSignalReader(root=str(root)).latest(bucket="top30")


def test_reader_blocks_run_dir_and_metadata_run_id_mismatch(tmp_path):
    root = make_artifact(tmp_path, metadata_overrides={"run_id": "different_run_id"})

    with pytest.raises(QlibOptionCSignalError, match="run_metadata.run_id"):
        QlibOptionCSignalReader(root=str(root)).latest(bucket="top30")


def test_reader_blocks_signal_paths_outside_run_dir(tmp_path):
    root = make_artifact(tmp_path)
    outside = root / "other_run"
    outside.mkdir()
    (outside / "top30_signals.csv").write_text((root / RUN_ID / "top30_signals.csv").read_text(encoding="utf-8"), encoding="utf-8")
    latest_overrides = {"top30_signals": "data_tw/experiments/option_c_daily_signal/other_run/top30_signals.csv"}
    root = make_artifact(tmp_path / "case2", latest_overrides=latest_overrides)
    other = root / "other_run"
    other.mkdir()
    (other / "top30_signals.csv").write_text((root / RUN_ID / "top30_signals.csv").read_text(encoding="utf-8"), encoding="utf-8")

    with pytest.raises(QlibOptionCSignalError, match="under latest_signal.run_dir"):
        QlibOptionCSignalReader(root=str(root)).latest(bucket="top30")


def test_reader_blocks_summary_paths_that_do_not_match_latest(tmp_path):
    root = make_artifact(tmp_path, summary_overrides={"top50_path": f"data_tw/experiments/option_c_daily_signal/{RUN_ID}/top30_signals.csv"})

    with pytest.raises(QlibOptionCSignalError, match="signal_summary.top50_path"):
        QlibOptionCSignalReader(root=str(root)).latest(bucket="top30")


def test_reader_blocks_csv_asof_mismatch(tmp_path):
    root = make_artifact(tmp_path)
    path = root / RUN_ID / "top30_signals.csv"
    _rewrite_csv_rows(path, lambda rows: rows[0].update({"asof": "2026-05-31"}))

    with pytest.raises(QlibOptionCSignalError, match="asof"):
        QlibOptionCSignalReader(root=str(root)).latest(bucket="top30")


@pytest.mark.parametrize("bucket,filename,bad_rank", [
    ("top30", "top30_signals.csv", "2"),
    ("top30", "top30_signals.csv", "31"),
    ("top50", "top50_signals.csv", "2"),
    ("top50", "top50_signals.csv", "51"),
])
def test_reader_blocks_duplicate_or_out_of_range_ranks(tmp_path, bucket, filename, bad_rank):
    root = make_artifact(tmp_path)
    path = root / RUN_ID / filename
    _rewrite_csv_rows(path, lambda rows: rows[0].update({"rank": bad_rank}))

    with pytest.raises(QlibOptionCSignalError, match=f"{bucket} ranks"):
        QlibOptionCSignalReader(root=str(root)).latest(bucket=bucket)


def test_reader_source_paths_are_relative_to_artifact_root(tmp_path):
    root = make_artifact(tmp_path)
    payload = QlibOptionCSignalReader(root=str(root)).latest(bucket="top30")

    assert "root" not in payload["source"]
    assert all(not value.startswith("/") for value in payload["source"].values())
    assert payload["recorder_id"] == RECORDER



def test_reader_lists_historical_runs_without_full_signals(tmp_path):
    root = make_artifact(tmp_path, run_id=RUN_ID)
    blocked_id = "option_c_daily_signal_20260531_20260531T010203Z"
    make_artifact(
        tmp_path,
        run_id=blocked_id,
        summary_overrides={"status": "wait_state_data_refresh_needed", "reason": "fixture stale"},
        metadata_overrides={"run_id": blocked_id, "status": "wait_state_data_refresh_needed", "created_at": "2026-05-31T01:02:03+00:00"},
    )

    payload = QlibOptionCSignalReader(root=str(root)).list_runs(limit=20, status="all")

    assert payload["trading"]["orders_enabled"] is False
    assert len(payload["items"]) == 2
    accepted = next(item for item in payload["items"] if item["run_id"] == RUN_ID)
    blocked = next(item for item in payload["items"] if item["run_id"] == blocked_id)
    assert accepted["accepted_validated"] is True
    assert accepted["status"] == "accepted"
    assert blocked["status"] == "wait_state_data_refresh_needed"
    assert "signals" not in accepted
    assert "top30" not in accepted
    assert "top50" not in accepted


def test_reader_run_status_filters(tmp_path):
    root = make_artifact(tmp_path, run_id=RUN_ID)
    blocked_id = "option_c_daily_signal_20260531_20260531T010203Z"
    make_artifact(
        tmp_path,
        run_id=blocked_id,
        summary_overrides={"status": "blocked_formal_validation_failed"},
        metadata_overrides={"run_id": blocked_id, "status": "blocked_formal_validation_failed", "created_at": "2026-05-31T01:02:03+00:00"},
    )

    accepted = QlibOptionCSignalReader(root=str(root)).list_runs(status="accepted")
    blocked = QlibOptionCSignalReader(root=str(root)).list_runs(status="blocked")

    assert [item["run_id"] for item in accepted["items"]] == [RUN_ID]
    assert [item["run_id"] for item in blocked["items"]] == [blocked_id]


def test_reader_rejects_invalid_historical_run_id(tmp_path):
    root = make_artifact(tmp_path)
    reader = QlibOptionCSignalReader(root=str(root))

    for run_id in ["../outside", "option_c_daily_signal_../x", "not_option_c_daily_signal"]:
        with pytest.raises(QlibOptionCSignalError) as exc:
            reader.run_detail(run_id)
        assert exc.value.status == "invalid_run_id"


def test_reader_historical_run_detail_accepted_all_and_enrichment(tmp_path):
    root = make_artifact(tmp_path)
    trend = FakeTrendService()

    payload = QlibOptionCSignalReader(root=str(root)).run_detail(RUN_ID, bucket="all", enrich_trend=True, trend_limit=77, trend_service=trend)

    assert payload["ok"] is True
    assert payload["status"] == "accepted"
    assert len(payload["top30"]) == 30
    assert len(payload["top50"]) == 50
    assert payload["top30"][0]["trend"]["trend_label"] == "uptrend"
    assert trend.calls[0] == ("2330", 77)
    assert "latest_signal" not in payload["source"]
    assert payload["trading"]["connects_to_broker"] is False


def test_reader_historical_blocked_detail_returns_no_signals(tmp_path):
    root = make_artifact(
        tmp_path,
        summary_overrides={"status": "wait_state_data_refresh_needed", "reason": "fixture stale"},
        metadata_overrides={"status": "wait_state_data_refresh_needed"},
    )

    payload = QlibOptionCSignalReader(root=str(root)).run_detail(RUN_ID, bucket="top30", enrich_trend=True)

    assert payload["ok"] is False
    assert payload["status"] == "wait_state_data_refresh_needed"
    assert payload["signals"] == []
    assert payload["top30"] == []
    assert payload["top50"] == []
    assert payload["enrichTrend"]["enabled"] is False
    assert payload["trading"]["orders_enabled"] is False



def test_reader_health_latest_accepted_without_full_signals(tmp_path):
    root = make_artifact(tmp_path)
    payload = QlibOptionCSignalReader(root=str(root)).health(now=datetime(2026, 6, 1, tzinfo=timezone.utc))

    assert payload["ok"] is True
    assert payload["status"] == "accepted"
    assert payload["latest"]["exists"] is True
    assert payload["latest"]["asof"] == "2026-06-01"
    assert payload["latest"]["run_id"] == RUN_ID
    assert payload["latest"]["accepted_validated"] is True
    assert payload["freshness"]["asof_age_days"] == 0
    assert payload["freshness"]["stale"] is False
    assert payload["runs"]["accepted"] == 1
    assert payload["dataAvailability"]["trend_data_dependency"] == "TWStock local daily bars"
    assert payload["dataAvailability"]["backtest_data_dependency"] == "qd_tw_stock_daily_bars"
    assert payload["trading"]["orders_enabled"] is False
    assert payload["trading"]["research_signal_not_order"] is True
    assert "signals" not in payload
    assert "top30" not in payload
    assert "top50" not in payload


def test_reader_health_missing_latest(tmp_path):
    payload = QlibOptionCSignalReader(root=str(tmp_path)).health(now=datetime(2026, 6, 1, tzinfo=timezone.utc))

    assert payload["ok"] is False
    assert payload["status"] == "missing_latest_signal"
    assert payload["latest"]["exists"] is False
    assert payload["freshness"]["stale"] is True
    assert payload["freshness"]["stale_reason"] == "missing_latest_signal"
    assert payload["runs"]["total_scanned"] == 0
    assert payload["trading"]["connects_to_broker"] is False


def test_reader_health_stale_asof(tmp_path):
    root = make_artifact(
        tmp_path,
        latest_overrides={"asof": "2026-05-20"},
        summary_overrides={"asof": "2026-05-20"},
        metadata_overrides={"asof": "2026-05-20"},
    )

    payload = QlibOptionCSignalReader(root=str(root)).health(now=datetime(2026, 6, 1, tzinfo=timezone.utc))

    assert payload["ok"] is False
    assert payload["status"] == "accepted"
    assert payload["latest"]["accepted_validated"] is True
    assert payload["freshness"]["asof_age_days"] == 12
    assert payload["freshness"]["stale"] is True
    assert payload["freshness"]["stale_reason"] == "asof_age_gt_3"


def test_reader_health_newer_wait_state_warning(tmp_path):
    root = make_artifact(tmp_path)
    wait_id = "option_c_daily_signal_20260602_20260602T010203Z"
    make_artifact(
        tmp_path,
        run_id=wait_id,
        summary_overrides={"status": "wait_state_data_refresh_needed", "asof": "2026-06-02", "reason": "new data requires manual review"},
        metadata_overrides={"run_id": wait_id, "status": "wait_state_data_refresh_needed", "asof": "2026-06-02", "created_at": "2026-06-02T01:02:03+00:00"},
        latest_overrides={"run_dir": f"data_tw/experiments/option_c_daily_signal/{RUN_ID}"},
    )
    make_artifact(tmp_path, run_id=RUN_ID)

    payload = QlibOptionCSignalReader(root=str(root)).health(now=datetime(2026, 6, 1, tzinfo=timezone.utc))

    assert payload["ok"] is False
    assert payload["status"] == "accepted"
    assert payload["latest"]["accepted_validated"] is True
    assert payload["runs"]["accepted"] == 1
    assert payload["runs"]["wait_state"] == 1
    assert payload["freshness"]["stale"] is True
    assert payload["freshness"]["stale_reason"] == "fresh_data_wait_state_present"
    assert "fresh_data_wait_state_present" in payload["dataAvailability"]["warnings"]
