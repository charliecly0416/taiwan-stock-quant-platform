from __future__ import annotations

import importlib.util
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def load_module():
    name = "capture_modelb_b19r2r_twii_yahoo_20260916"
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts/capture_modelb_b19r2r_twii_yahoo_20260916.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


capture = load_module()


class StepClock:
    def __init__(self, *values: str) -> None:
        self.values = [datetime.fromisoformat(value) for value in values]
        self.index = 0

    def __call__(self) -> datetime:
        value = self.values[min(self.index, len(self.values) - 1)]
        self.index += 1
        return value


def yahoo_payload(*, include_target: bool = True, malformed: str | None = None) -> dict:
    end = datetime(2026, 9, 16 if include_target else 15, tzinfo=UTC)
    days = [end - timedelta(days=offset) for offset in reversed(range(130))]
    timestamps = [int(day.timestamp()) for day in days]
    size = len(timestamps)
    quote = {
        "open": [100.0 + index for index in range(size)],
        "high": [102.0 + index for index in range(size)],
        "low": [99.0 + index for index in range(size)],
        "close": [101.0 + index for index in range(size)],
        "volume": [1000 + index for index in range(size)],
    }
    if malformed == "missing_close":
        quote.pop("close")
    if malformed == "short_close":
        quote["close"] = quote["close"][:-1]
    return {
        "chart": {
            "error": None,
            "result": [
                {
                    "meta": {
                        "symbol": "^TWII",
                        "exchangeName": "TAI",
                        "exchangeTimezoneName": "Asia/Taipei",
                        "instrumentType": "INDEX",
                        "gmtoffset": 28800,
                        "dataGranularity": "1d",
                    },
                    "timestamp": timestamps,
                    "indicators": {
                        "quote": [quote],
                        "adjclose": [{"adjclose": [101.0 + index for index in range(size)]}],
                    },
                }
            ],
        }
    }


def intraday_payload() -> dict:
    first = datetime(2026, 9, 16, 1, 0, tzinfo=UTC)
    timestamps = [int((first + timedelta(minutes=index)).timestamp()) for index in range(271)]
    size = len(timestamps)
    opens = [200.0 + index / 10 for index in range(size)]
    closes = [value + 0.05 for value in opens]
    return {
        "chart": {
            "error": None,
            "result": [
                {
                    "meta": {
                        "symbol": "^TWII",
                        "exchangeName": "TAI",
                        "exchangeTimezoneName": "Asia/Taipei",
                        "gmtoffset": 28800,
                        "dataGranularity": "1m",
                        "regularMarketPrice": closes[-1],
                        "regularMarketTime": int(datetime(2026, 9, 16, 5, 33, tzinfo=UTC).timestamp()),
                    },
                    "timestamp": timestamps,
                    "indicators": {
                        "quote": [
                            {
                                "open": opens,
                                "high": [value + 0.1 for value in opens],
                                "low": [value - 0.1 for value in opens],
                                "close": closes,
                                "volume": [0] * size,
                            }
                        ]
                    },
                }
            ],
        }
    }


def http_result(payload: dict, url: str | None = None) -> capture.HttpResult:
    return capture.HttpResult(
        status=200,
        url=url or capture.request_url(),
        headers={"date": "Wed, 16 Sep 2026 18:20:00 GMT", "content-type": "application/json"},
        body=json.dumps(payload, separators=(",", ":")).encode(),
    )


def daily_incomplete_stub_payload() -> dict:
    payload = yahoo_payload(include_target=True)
    result = payload["chart"]["result"][0]
    quote = result["indicators"]["quote"][0]
    minute_result = intraday_payload()["chart"]["result"][0]
    minute_quote = minute_result["indicators"]["quote"][0]
    quote["open"][-1] = minute_quote["open"][0]
    quote["high"][-1] = max(minute_quote["high"])
    quote["low"][-1] = min(minute_quote["low"])
    quote["close"][-1] = None
    quote["volume"][-1] = 0
    result["indicators"]["adjclose"][0]["adjclose"][-1] = None
    return payload


@pytest.fixture
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    research_root = tmp_path / "manual_source"
    research_root.mkdir()
    protected = tmp_path / "protected.json"
    protected.write_text('{"stable":true}\n', encoding="utf-8")
    monkeypatch.setattr(capture, "RESEARCH_ROOT", research_root)
    monkeypatch.setattr(capture, "PROTECTED", (protected,))
    return research_root, protected


def normal_clock() -> StepClock:
    return StepClock(
        "2026-09-16T18:20:00+00:00",
        "2026-09-16T18:20:01+00:00",
        "2026-09-16T18:20:02+00:00",
        "2026-09-16T18:20:03+00:00",
        "2026-09-16T18:20:04+00:00",
        "2026-09-16T18:20:05+00:00",
    )


def successful_fetcher(url: str, timeout: float) -> capture.HttpResult:
    payload = intraday_payload() if "interval=1m" in url else daily_incomplete_stub_payload()
    return http_result(payload, url)


def test_success_writes_complete_readonly_evidence(isolated) -> None:
    research_root, _ = isolated
    output = research_root / "capture_v1"
    result = capture.capture(output, fetcher=successful_fetcher, clock=normal_clock())
    assert result["status"] == "PASS_REVIEWABLE_CANDIDATE"
    assert result["provider"] == "Yahoo Finance"
    assert result["official_source"] is False
    assert result["available_at"] == result["fetched_at"]
    assert result["coverage"]["normalized_row_count"] == 130
    assert result["coverage"]["target_row_count"] == 1
    assert result["coverage"]["date_max"] == capture.TARGET
    assert result["protected_unchanged"] is True
    assert result["training_performed"] is False
    assert result["scoring_performed"] is False
    assert set(path.name for path in output.iterdir()) == {
        "REQUEST_DAILY.json",
        "RESPONSE_HEADERS_DAILY.json",
        "twii_daily_raw.json",
        "REQUEST_INTRADAY.json",
        "RESPONSE_HEADERS_INTRADAY.json",
        "twii_intraday_1m_raw.json",
        "TWII_NORMALIZED.csv",
        "NORMALIZED_SCHEMA.json",
        "TWII_CAPTURE_MANIFEST.json",
    }
    manifest = json.loads((output / "TWII_CAPTURE_MANIFEST.json").read_text())
    assert manifest["raw_sha256"]["daily"] == capture.sha256(output / "twii_daily_raw.json")
    assert manifest["raw_sha256"]["intraday"] == capture.sha256(output / "twii_intraday_1m_raw.json")
    assert manifest["normalized_sha256"] == capture.sha256(output / "TWII_NORMALIZED.csv")
    assert output.stat().st_mode & 0o777 == 0o555
    assert all(path.stat().st_mode & 0o777 == 0o444 for path in output.iterdir())


def test_network_failure_is_preserved_fail_closed(isolated) -> None:
    research_root, _ = isolated
    output = research_root / "network_failure"

    def fail(url: str, timeout: float):
        raise OSError("offline")

    with pytest.raises(capture.CaptureError) as caught:
        capture.capture(output, fetcher=fail, clock=normal_clock())
    assert caught.value.code == "B19YTWII_E_NETWORK"
    failure = json.loads((output / "CAPTURE_FAILURE.json").read_text())
    assert failure["status"] == "FAIL_CLOSED"
    assert failure["error_code"] == "B19YTWII_E_NETWORK"
    assert failure["protected_unchanged"] is True
    assert output.stat().st_mode & 0o777 == 0o555


def test_target_date_missing_fails_closed(isolated) -> None:
    research_root, _ = isolated
    output = research_root / "target_missing"

    def fetch(url: str, timeout: float):
        payload = intraday_payload() if "interval=1m" in url else daily_incomplete_stub_payload()
        if "interval=1m" in url:
            payload["chart"]["result"][0]["timestamp"][0] -= 86400
        return http_result(payload, url)

    with pytest.raises(capture.CaptureError) as caught:
        capture.capture(output, fetcher=fetch, clock=normal_clock())
    assert caught.value.code == "B19YTWII_E_INTRADAY_TARGET_DATE"
    assert json.loads((output / "CAPTURE_FAILURE.json").read_text())["error_code"] == "B19YTWII_E_INTRADAY_TARGET_DATE"


def test_after_next_open_is_rejected(isolated) -> None:
    research_root, _ = isolated
    output = research_root / "late"
    late_clock = StepClock(
        "2026-09-17T00:59:58+00:00",
        "2026-09-17T00:59:58.500000+00:00",
        "2026-09-17T00:59:59+00:00",
        "2026-09-17T01:00:00+00:00",
        "2026-09-17T01:00:01+00:00",
        "2026-09-17T01:00:02+00:00",
    )
    with pytest.raises(capture.CaptureError) as caught:
        capture.capture(output, fetcher=successful_fetcher, clock=late_clock)
    assert caught.value.code == "B19YTWII_E_AFTER_NEXT_OPEN"


def test_backdated_and_forged_times_are_rejected() -> None:
    with pytest.raises(capture.CaptureError) as backdated:
        capture.validate_timeline(
            "2026-09-16T18:20:01+00:00",
            "2026-09-16T18:20:00+00:00",
            "2026-09-16T18:20:02+00:00",
            "2026-09-16T18:20:00+00:00",
        )
    assert backdated.value.code == "B19YTWII_E_BACKDATED_TIMELINE"
    with pytest.raises(capture.CaptureError) as forged:
        capture.validate_timeline(
            "2026-09-16T18:20:00+00:00",
            "2026-09-16T18:20:01+00:00",
            "2026-09-16T18:20:02+00:00",
            "2026-09-16T18:19:00+00:00",
        )
    assert forged.value.code == "B19YTWII_E_FORGED_AVAILABLE_AT"


@pytest.mark.parametrize("malformed", ["missing_close", "short_close"])
def test_schema_errors_fail_closed(isolated, malformed: str) -> None:
    research_root, _ = isolated
    output = research_root / f"schema_{malformed}"
    with pytest.raises(capture.CaptureError) as caught:
        capture.capture(
            output,
            fetcher=lambda url, timeout: http_result(yahoo_payload(malformed=malformed), url),
            clock=normal_clock(),
        )
    assert caught.value.code == "B19YTWII_E_SCHEMA"


def test_existing_output_is_never_overwritten(isolated) -> None:
    research_root, _ = isolated
    output = research_root / "existing"
    output.mkdir()
    sentinel = output / "sentinel"
    sentinel.write_text("keep", encoding="utf-8")
    called = False

    def should_not_fetch(url: str, timeout: float):
        nonlocal called
        called = True
        return http_result(yahoo_payload(), url)

    with pytest.raises(capture.CaptureError) as caught:
        capture.capture(output, fetcher=should_not_fetch, clock=normal_clock())
    assert caught.value.code == "B19YTWII_E_NO_OVERWRITE"
    assert called is False
    assert sentinel.read_text() == "keep"


def test_protected_drift_blocks_success(isolated) -> None:
    research_root, protected = isolated
    output = research_root / "drift"

    def drift(url: str, timeout: float):
        protected.write_text('{"stable":false}\n', encoding="utf-8")
        return successful_fetcher(url, timeout)

    with pytest.raises(capture.CaptureError) as caught:
        capture.capture(output, fetcher=drift, clock=normal_clock())
    assert caught.value.code == "B19YTWII_E_PROTECTED_DRIFT"
    failure = json.loads((output / "CAPTURE_FAILURE.json").read_text())
    assert failure["protected_unchanged"] is False
    assert not (output / "TWII_CAPTURE_MANIFEST.json").exists()


def test_output_outside_research_root_is_rejected(isolated, tmp_path: Path) -> None:
    with pytest.raises(capture.CaptureError) as caught:
        capture.capture(tmp_path / "outside", fetcher=successful_fetcher, clock=normal_clock())
    assert caught.value.code == "B19YTWII_E_OUTPUT"


def test_request_window_is_exact_and_excludes_future_day() -> None:
    params = capture.request_parameters()
    assert datetime.fromtimestamp(int(params["period1"]), tz=UTC).date().isoformat() == capture.START
    assert datetime.fromtimestamp(int(params["period2"]), tz=UTC).date().isoformat() == "2026-09-17"
    assert params["interval"] == "1d"
    intraday = capture.intraday_request_parameters()
    assert intraday["interval"] == "1m"
    assert datetime.fromtimestamp(int(intraday["period1"]), tz=UTC).isoformat() == "2026-09-16T00:00:00+00:00"
    assert datetime.fromtimestamp(int(intraday["period2"]), tz=UTC).isoformat() == "2026-09-17T00:00:00+00:00"


def test_intraday_session_bounds_and_last_timestamp_are_strict() -> None:
    payload = intraday_payload()
    payload["chart"]["result"][0]["timestamp"][-1] -= 60
    with pytest.raises(capture.CaptureError) as caught:
        capture.yahoo_intraday_to_target_row(payload)
    assert caught.value.code in {"B19YTWII_E_INTRADAY_POINT_COUNT", "B19YTWII_E_INTRADAY_SESSION_ENDPOINTS"}


def test_intraday_null_ohlc_is_rejected() -> None:
    payload = intraday_payload()
    payload["chart"]["result"][0]["indicators"]["quote"][0]["close"][10] = None
    with pytest.raises(capture.CaptureError) as caught:
        capture.yahoo_intraday_to_target_row(payload)
    assert caught.value.code == "B19YTWII_E_VALUE"


def test_intraday_meta_price_must_match_aggregated_close() -> None:
    payload = intraday_payload()
    payload["chart"]["result"][0]["meta"]["regularMarketPrice"] += 1.0
    with pytest.raises(capture.CaptureError) as caught:
        capture.yahoo_intraday_to_target_row(payload)
    assert caught.value.code == "B19YTWII_E_INTRADAY_META_PRICE"


def test_intraday_adjacent_timestamps_must_be_exactly_60_seconds() -> None:
    payload = intraday_payload()
    payload["chart"]["result"][0]["timestamp"][100] += 1
    with pytest.raises(capture.CaptureError) as caught:
        capture.yahoo_intraday_to_target_row(payload)
    assert caught.value.code == "B19YTWII_E_INTRADAY_DELTA"


def test_intraday_dropped_minute_is_rejected() -> None:
    payload = intraday_payload()
    result = payload["chart"]["result"][0]
    result["timestamp"].pop(100)
    for values in result["indicators"]["quote"][0].values():
        values.pop(100)
    with pytest.raises(capture.CaptureError) as caught:
        capture.yahoo_intraday_to_target_row(payload)
    assert caught.value.code == "B19YTWII_E_INTRADAY_POINT_COUNT"


def test_intraday_duplicate_minute_is_rejected() -> None:
    payload = intraday_payload()
    timestamps = payload["chart"]["result"][0]["timestamp"]
    timestamps[100] = timestamps[99]
    with pytest.raises(capture.CaptureError) as caught:
        capture.yahoo_intraday_to_target_row(payload)
    assert caught.value.code == "B19YTWII_E_INTRADAY_POINT_COUNT"


def test_intraday_outside_session_is_rejected() -> None:
    payload = intraday_payload()
    payload["chart"]["result"][0]["timestamp"][0] -= 60
    with pytest.raises(capture.CaptureError) as caught:
        capture.yahoo_intraday_to_target_row(payload)
    assert caught.value.code == "B19YTWII_E_INTRADAY_SESSION_BOUNDS"


def test_intraday_identity_and_granularity_are_strict() -> None:
    payload = intraday_payload()
    payload["chart"]["result"][0]["meta"]["dataGranularity"] = "5m"
    with pytest.raises(capture.CaptureError) as caught:
        capture.yahoo_intraday_to_target_row(payload)
    assert caught.value.code == "B19YTWII_E_INTRADAY_IDENTITY"


def test_daily_incomplete_stub_matches_intraday_and_proves_factor_one() -> None:
    daily = yahoo_payload(include_target=True)
    result = daily["chart"]["result"][0]
    result["indicators"]["quote"][0]["close"][-1] = None
    result["indicators"]["adjclose"][0]["adjclose"][-1] = None
    intraday_row = {
        "open": result["indicators"]["quote"][0]["open"][-1],
        "high": result["indicators"]["quote"][0]["high"][-1],
        "low": result["indicators"]["quote"][0]["low"][-1],
    }
    evidence = capture.validate_daily_target_stub(daily, intraday_row)
    assert evidence["daily_stub_is_explicitly_incomplete"] is True
    assert evidence["complete_daily_factor_max_deviation_from_one"] == 0.0
    assert evidence["target_factor_semantics_consistent"] is True


def test_daily_stub_ohl_mismatch_is_rejected() -> None:
    daily = yahoo_payload(include_target=True)
    result = daily["chart"]["result"][0]
    quote = result["indicators"]["quote"][0]
    quote["close"][-1] = None
    result["indicators"]["adjclose"][0]["adjclose"][-1] = None
    intraday_row = {"open": quote["open"][-1] + 1.0, "high": quote["high"][-1], "low": quote["low"][-1]}
    with pytest.raises(capture.CaptureError) as caught:
        capture.validate_daily_target_stub(daily, intraday_row)
    assert caught.value.code == "B19YTWII_E_DAILY_INTRADAY_MISMATCH"
