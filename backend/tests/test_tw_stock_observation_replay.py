"""Tests for observation-only TWStock research queue comparison."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from app.services.tw_stock_observation_replay import TWStockObservationReplayService
from app.services.tw_stock_rank_tech_cross import TWStockRankTechCrossService
from app.services.tw_stock_technical_status import TWStockTechnicalStatusService
from app.services.tw_stock_trend import TWStockTrendService


class FutureAwareKlineService:
    def __init__(self):
        self.calls = []

    def get_kline(self, market, symbol, timeframe, limit):
        self.calls.append((market, symbol, timeframe, limit))
        rows = []
        for index in range(25):
            day = index + 1
            rows.append({"date": f"2026-05-{day:02d}", "time": index + 1, "close": 80 + index, "volume": 1000})
        rows.extend([
            {"date": "2026-05-28", "time": 28, "close": 100, "volume": 1000},
            {"date": "2026-05-29", "time": 29, "close": 101, "volume": 1000},
            {"date": "2026-06-01", "time": 30, "close": 102, "volume": 1000},
            {"date": "2026-06-02", "time": 31, "close": 150, "volume": 1000},
        ])
        return rows[-limit:]


class FakeQlibReader:
    def list_runs(self, *, limit: int = 100, status: str = "accepted"):
        return {
            "items": [
                {"run_id": "run-20260601", "asof": "2026-06-01", "status": "accepted", "accepted_validated": True},
                {"run_id": "run-20260602", "asof": "2026-06-02", "status": "accepted", "accepted_validated": True},
            ]
        }

    def run_detail(self, run_id: str, *, bucket: str = "top30", enrich_trend: bool = False):
        assert enrich_trend is False
        asof = "2026-06-01" if run_id == "run-20260601" else "2026-06-02"
        return {
            "ok": True,
            "status": "accepted",
            "asof": asof,
            "run_id": run_id,
            "bucket": bucket,
            "signals": [
                {"symbol": "2330", "instrument": "TW2330", "rank": 1, "bucket": bucket, "qlib_score": 0.9},
                {"symbol": "2357", "instrument": "TW2357", "rank": 12, "bucket": bucket, "qlib_score": 0.7},
            ],
        }


class FakeTrendService:
    def analyze_symbol(self, *, symbol: str, limit: int = 120, as_of=None):
        label = "uptrend" if symbol == "2330" else "downtrend"
        return {
            "ok": True,
            "symbol": symbol,
            "latest": {"date": as_of.isoformat() if as_of else "2026-06-02"},
            "trend": {"label": label, "score": 70},
            "quality": {"warnings": [], "latest_date": as_of.isoformat() if as_of else "2026-06-02"},
        }


class FakeTechnicalService:
    def analyze_symbol(self, *, symbol: str, limit: int = 120, strategies=None, as_of=None):
        status = "technical_strong" if symbol == "2330" else "technical_data_insufficient"
        state = "supportive" if status == "technical_strong" else "data_insufficient"
        return {
            "ok": True,
            "status": status,
            "summary": {
                "supportive_count": 4 if status == "technical_strong" else 0,
                "neutral_count": 0,
                "caution_count": 0,
                "data_insufficient_count": 0 if status == "technical_strong" else 4,
            },
            "strategies": [{"id": item, "state": state, "warnings": []} for item in ["ma", "rsi", "macd", "bollinger"]],
            "positionRisk": {"status": "reasonable", "label": "位置合理", "score": 35, "reason": "fixture", "metrics": {}, "warnings": []},
            "warnings": [] if status == "technical_strong" else ["fixture_data_insufficient"],
        }


def test_technical_and_trend_point_in_time_do_not_use_future_bars():
    kline = FutureAwareKlineService()
    technical = TWStockTechnicalStatusService(kline_service=kline).analyze_symbol(
        symbol="2330",
        strategies=["ma"],
        as_of=date(2026, 6, 1),
    )
    trend = TWStockTrendService(kline_service=kline).analyze_symbol(symbol="2330", limit=20, as_of=date(2026, 6, 1))

    assert technical["strategies"][0]["metrics"].get("close") == 102
    assert trend["latest"]["date"] == "2026-06-01"


def test_observation_replay_returns_four_observation_variants_without_metrics():
    rank_service = TWStockRankTechCrossService(
        qlib_reader=FakeQlibReader(),
        trend_service=FakeTrendService(),
        technical_service=FakeTechnicalService(),
    )
    service = TWStockObservationReplayService(qlib_reader=FakeQlibReader(), rank_tech_service=rank_service)
    payload = service.compare(start_date="2026-06-01", end_date="2026-06-01", bucket="top30", max_items=2)

    assert payload["ok"] is True
    assert payload["simulation_only"] is True
    assert payload["research_signal_not_order"] is True
    assert payload["replay_type"] == "observation_only"
    assert payload["performance_metrics_included"] is False
    assert payload["range"]["runCount"] == 1
    variants = payload["daily"][0]["variants"]
    assert set(variants) == {"qlib_only", "qlib_plus_trend", "qlib_plus_trend_indicators", "qlib_plus_trend_position_risk"}
    assert variants["qlib_only"]["summary"]["new_watch"] == 1
    assert variants["qlib_plus_trend"]["summary"]["manual_review"] == 1
    assert variants["qlib_plus_trend_indicators"]["summary"]["item_count"] == 2
    assert variants["qlib_plus_trend_position_risk"]["summary"]["item_count"] == 2
    assert "fixture_data_insufficient" in payload["dataQuality"]["warnings"]
    assert payload["comparison"]["qlib_only"]["item_count"] == 2
    text = repr(payload)
    forbidden = ["totalReturn", "maxDrawdown", "winRate", "turnover", "equityCurve", "target weight", "target position"]
    assert not any(term in text for term in forbidden)


def test_observation_replay_source_has_no_write_or_performance_paths():
    source = Path("backend/app/services/tw_stock_observation_replay.py").read_text()
    forbidden = [
        "BacktestService",
        "equityCurve",
        "totalReturn",
        "maxDrawdown",
        "winRate",
        "turnover",
        "qd_tw_sim_orders",
        "qd_tw_sim_trades",
        "qd_tw_sim_positions",
        "target_position",
        "target_weight",
        "order instruction",
    ]

    assert not any(term in source for term in forbidden)
