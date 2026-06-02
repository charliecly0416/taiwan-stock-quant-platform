"""Tests for read-only qlib/TWStock cross analysis service."""
from __future__ import annotations

from app.services.tw_stock_cross_analysis import TWStockCrossAnalysisService
from app.services.tw_stock_qlib_option_c import QlibOptionCSignalError


def _row(rank: int, *, bucket: str = "top30", symbol: str | None = None) -> dict:
    clean = symbol or str(2300 + rank)
    if rank == 1 and symbol is None:
        clean = "2330"
    return {
        "asof": "2026-06-01",
        "instrument": f"TW{clean}",
        "symbol": clean,
        "qlib_score": 0.2 - rank / 1000,
        "rank": rank,
        "bucket": bucket,
    }


def _payload() -> dict:
    top30 = [_row(rank, bucket="top30") for rank in range(1, 31)]
    top50 = [_row(rank, bucket="top50") for rank in range(1, 51)]
    return {
        "ok": True,
        "status": "accepted",
        "asof": "2026-06-01",
        "run_id": "option_c_daily_signal_20260601_20260602T090715Z",
        "recorder_id": "950741cfd5f14ee5a05464fec3e12e0a",
        "target_horizon": "next_trading_day_research_ranking",
        "target_date": None,
        "signal_semantics": "research_only_cross_sectional_ranking",
        "recommendation_semantics": "watchlist_not_trade_advice",
        "summary": {
            "status": "accepted",
            "prediction_rows": 150,
            "top30_rows": 30,
            "top50_rows": 50,
            "finite_prediction_share": 1.0,
            "diagnostic_only": True,
            "research_signal_not_order": True,
        },
        "signals": top30,
        "top30": top30,
        "top50": top50,
        "trading": {"orders_enabled": False, "research_signal_not_order": True},
    }


class FakeQlibReader:
    def __init__(self, *, blocked: bool = False) -> None:
        self.blocked = blocked
        self.calls = []

    def latest(self, *, bucket: str = "top30", enrich_trend: bool = False):
        self.calls.append((bucket, enrich_trend))
        if self.blocked:
            raise QlibOptionCSignalError("blocked_validation_failed", "fixture blocked", warnings=["bad_fixture"])
        payload = _payload()
        if bucket == "top30":
            payload["signals"] = payload["top30"]
            payload["bucket"] = "top30"
        elif bucket == "top50":
            payload["signals"] = payload["top50"]
            payload["bucket"] = "top50"
        else:
            payload.pop("signals", None)
            payload["bucket"] = "all"
        return payload


class FakeTrendService:
    def __init__(self, labels: dict[str, str] | None = None, warnings: dict[str, list[str]] | None = None, fail: set[str] | None = None) -> None:
        self.labels = labels or {}
        self.warnings = warnings or {}
        self.fail = fail or set()
        self.calls = []

    def analyze_symbol(self, *, symbol: str, limit: int = 120, as_of=None):
        self.calls.append((symbol, limit))
        if symbol in self.fail:
            raise RuntimeError("trend fixture failure")
        label = self.labels.get(symbol, "uptrend")
        warnings = self.warnings.get(symbol, [])
        if label == "unavailable":
            return {
                "ok": False,
                "error": "no_daily_bars",
                "quality": {"warnings": warnings or ["no_daily_bars"], "source": "KlineService:TWStock:1D"},
            }
        return {
            "ok": True,
            "latest": {"date": "2026-06-01", "close": 123.4},
            "trend": {"label": label, "score": 72.5},
            "quality": {"warnings": warnings, "source": "KlineService:TWStock:1D"},
        }


def _service(**kwargs) -> TWStockCrossAnalysisService:
    return TWStockCrossAnalysisService(qlib_reader=kwargs.get("reader") or FakeQlibReader(), trend_service=kwargs.get("trend") or FakeTrendService())


def test_latest_top30_top50_reuses_accepted_reader_and_returns_contract():
    reader = FakeQlibReader()
    service = _service(reader=reader)

    top30 = service.latest(bucket="top30", max_items=3, limit=10)
    top50 = service.latest(bucket="top50", max_items=2, include_raw_trend=True, limit=999)

    assert reader.calls[0] == ("top30", False)
    assert reader.calls[1] == ("top50", False)
    assert top30["qlib"]["asof"] == "2026-06-01"
    assert top30["qlib"]["target_horizon"] == "next_trading_day_research_ranking"
    assert top30["freshness"]["qlib"]["asof"] == "2026-06-01"
    assert top30["freshness"]["quantdinger"]["latest_date_min"] == "2026-06-01"
    assert top30["freshness"]["quantdinger"]["latest_date_max"] == "2026-06-01"
    assert top30["freshness"]["date_gap_days_min"] == 0
    assert top30["freshness"]["date_gap_days_max"] == 0
    assert top30["freshness"]["status"] == "historical"
    assert top30["basis"]["qlib_source"] == "Yahoo adjusted model signal"
    assert top30["basis"]["quantdinger_source"] == "raw TWStock daily KlineService data"
    assert len(top30["items"]) == 3
    assert top30["limit"] == 20
    assert top50["limit"] == 500
    assert "rawTrend" in top50["items"][0]
    assert top30["trading"]["orders_enabled"] is False
    assert top30["trading"]["research_signal_not_order"] is True


def test_blocked_qlib_latest_returns_blocked_without_trend_calls():
    trend = FakeTrendService()
    payload = _service(reader=FakeQlibReader(blocked=True), trend=trend).latest()

    assert payload["ok"] is False
    assert payload["status"] == "blocked_validation_failed"
    assert payload["items"] == []
    assert payload["warnings"] == ["bad_fixture"]
    assert payload["freshness"]["status"] == "blocked"
    assert payload["basis"]["qlib_source"] == "Yahoo adjusted model signal"
    assert trend.calls == []
    assert payload["trading"]["orders_enabled"] is False


def test_cross_category_rules_for_top30():
    labels = {"2330": "uptrend", "2302": "downtrend", "2303": "sideways"}
    payload = _service(trend=FakeTrendService(labels=labels)).latest(bucket="top30", max_items=3)

    categories = [item["cross"]["category"] for item in payload["items"]]
    assert categories == ["focus_watch", "model_trend_divergence", "model_watch_trend_neutral"]
    assert payload["items"][0]["cross"]["priority"] == "high"
    assert payload["items"][1]["cross"]["alignment"] == "divergent"


def test_cross_category_rules_for_top50_and_quality_blocks():
    labels = {"2330": "rebound", "2302": "pullback"}
    warnings = {"2302": ["stale_daily_bar"]}
    payload = _service(trend=FakeTrendService(labels=labels, warnings=warnings)).latest(bucket="top50", max_items=2)

    assert payload["items"][0]["cross"]["category"] == "secondary_watch"
    assert payload["items"][1]["cross"]["category"] == "data_review_required"
    assert payload["items"][1]["cross"]["priority"] == "blocked"


def test_trend_service_exception_returns_trend_unavailable():
    payload = _service(trend=FakeTrendService(fail={"2330"})).latest(bucket="top30", max_items=1)

    item = payload["items"][0]
    assert item["cross"]["category"] == "trend_unavailable"
    assert item["quantdinger"]["quality_warnings"] == ["trend_service_error"]
    assert item["data_basis"]["data_basis_status"] == "quantdinger_raw_unavailable"


def test_freshness_status_fresh_when_target_date_exists():
    class TargetDateReader(FakeQlibReader):
        def latest(self, *, bucket: str = "top30", enrich_trend: bool = False):
            payload = super().latest(bucket=bucket, enrich_trend=enrich_trend)
            payload["target_date"] = "2026-06-02"
            return payload

    payload = _service(reader=TargetDateReader()).latest(bucket="top30", max_items=1)

    assert payload["freshness"]["status"] == "fresh"
    assert payload["freshness"]["warnings"] == []


def test_freshness_status_stale_and_unknown():
    stale = _service(trend=FakeTrendService()).latest(bucket="top30", max_items=1)
    stale["items"][0]["data_basis"]["date_gap_days"] = 3
    assert TWStockCrossAnalysisService._freshness_summary(qlib_payload=_payload(), items=stale["items"])["status"] == "stale"

    unknown = _service(trend=FakeTrendService(labels={"2330": "unavailable"})).latest(bucket="top30", max_items=1)
    assert unknown["freshness"]["status"] == "unknown"
    assert "raw_latest_date_unavailable" in unknown["freshness"]["warnings"]


def test_data_basis_fields_and_include_raw_trend_false():
    payload = _service().latest(bucket="top30", max_items=1, include_raw_trend=False)
    item = payload["items"][0]

    assert "rawTrend" not in item
    assert item["data_basis"]["qlib_source"] == "Yahoo adjusted model signal"
    assert item["data_basis"]["quantdinger_source"] == "KlineService:TWStock:1D"
    assert item["data_basis"]["date_gap_days"] == 0
    assert item["data_basis"]["date_aligned"] is True


def test_symbol_detail_in_top50_and_not_in_top50():
    service = _service()

    in_top50 = service.symbol_detail(symbol="TW2331", include_raw_trend=False)
    missing = service.symbol_detail(symbol="9999", include_raw_trend=True)

    assert in_top50["ok"] is True
    assert in_top50["item"]["qlib"]["bucket"] == "top50"
    assert "rawTrend" not in in_top50["item"]
    assert missing["ok"] is False
    assert missing["status"] == "not_in_latest_qlib_top50"
    assert missing["trend"]["ok"] is True
    assert missing["trading"]["orders_enabled"] is False


def test_service_code_does_not_reference_trading_integrations():
    from pathlib import Path

    text = Path("app/services/tw_stock_cross_analysis.py").read_text(encoding="utf-8").lower()
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
    for item in forbidden:
        assert item not in text
