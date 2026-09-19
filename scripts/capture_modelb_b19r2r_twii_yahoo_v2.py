#!/usr/bin/env python3
"""Capture Yahoo Finance ^TWII history in a write-once research namespace."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from itertools import pairwise
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
RESEARCH_ROOT = Path(os.environ.get("B19YTWII_RESEARCH_ROOT", str(ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_v3_manual_source_20260916"))).resolve()
DEFAULT_OUTPUT = RESEARCH_ROOT / "twii_acquisition_v5_yahoo_scrapling"
ENDPOINT = "https://query1.finance.yahoo.com/v8/finance/chart/%5ETWII"
TICKER = "^TWII"
TARGET = os.environ.get("B19YTWII_TARGET_ASOF", "2026-09-16")
START = "2025-12-01"
NEXT_OPEN_UTC = os.environ.get("B19YTWII_NEXT_OPEN_UTC", "2026-09-17T01:00:00+00:00")
SESSION_CLOSE_UTC = os.environ.get("B19YTWII_SESSION_CLOSE_UTC", "2026-09-16T05:30:00+00:00")
MIN_ROWS = 120
NORMALIZED_COLUMNS = ["date", "open", "high", "low", "close", "volume", "vwap", "factor", "source"]
SOURCE_VALUE = "yahoo_finance_chart_^TWII"
INTRADAY_SOURCE_VALUE = "yahoo_finance_chart_1m_aggregated_^TWII"
SCRAPLING_PROXY = "http://127.0.0.1:7890"
PROTECTED = (
    ROOT / "configs/tw_modular_registry.yaml",
    ROOT / "configs/active_baseline_descriptor.yaml",
    ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json",
    RESEARCH_ROOT / "twii_acquisition_v1",
    RESEARCH_ROOT / "twii_acquisition_v2",
    RESEARCH_ROOT / "twii_acquisition_v3_yahoo",
    RESEARCH_ROOT / "twii_acquisition_v4_yahoo",
    ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_v3_bundle_20260916",
)


class CaptureError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class HttpResult:
    status: int
    url: str
    headers: dict[str, str]
    body: bytes
    transport: str = "test_or_urllib"


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise CaptureError("B19YTWII_E_TIMEZONE", str(value))
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def parse_time(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise CaptureError("B19YTWII_E_TIME", str(value)) from exc
    if parsed.tzinfo is None:
        raise CaptureError("B19YTWII_E_TIMEZONE", str(value))
    return parsed.astimezone(UTC)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def fingerprint_path(path: Path) -> str | None:
    if path.is_file():
        return sha256(path)
    if not path.is_dir():
        return None
    entries: list[dict[str, Any]] = []
    for child in sorted(item for item in path.rglob("*") if item.is_file()):
        entries.append(
            {
                "path": str(child.relative_to(path)),
                "bytes": child.stat().st_size,
                "sha256": sha256(child),
            }
        )
    return sha256_bytes(json.dumps(entries, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def fingerprints() -> dict[str, str | None]:
    return {rel(path): fingerprint_path(path) for path in PROTECTED}


def request_parameters() -> dict[str, str]:
    start = datetime.strptime(START, "%Y-%m-%d").replace(tzinfo=UTC)
    end_exclusive = datetime.strptime(TARGET, "%Y-%m-%d").replace(tzinfo=UTC) + timedelta(days=1)
    return {
        "period1": str(int(start.timestamp())),
        "period2": str(int(end_exclusive.timestamp())),
        "interval": "1d",
        "events": "history",
        "includeAdjustedClose": "true",
    }


def intraday_request_parameters() -> dict[str, str]:
    start = datetime.strptime(TARGET, "%Y-%m-%d").replace(tzinfo=UTC)
    return {
        "period1": str(int(start.timestamp())),
        "period2": str(int((start + timedelta(days=1)).timestamp())),
        "interval": "1m",
        "events": "history",
        "includePrePost": "false",
    }


def request_url(parameters: dict[str, str] | None = None) -> str:
    return ENDPOINT + "?" + urllib.parse.urlencode(parameters or request_parameters())


def fetch_url(url: str, timeout: float = 30.0) -> HttpResult:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json,text/plain,*/*",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return HttpResult(
                status=int(getattr(response, "status", 200)),
                url=str(response.geturl()),
                headers={str(key).lower(): str(value) for key, value in response.headers.items()},
                body=response.read(),
                transport="urllib_direct_chart",
            )
    except urllib.error.HTTPError as exc:
        return HttpResult(
            status=int(exc.code),
            url=str(exc.geturl()),
            headers={str(key).lower(): str(value) for key, value in exc.headers.items()},
            body=exc.read(),
            transport="urllib_direct_chart",
        )
    except Exception as exc:
        raise CaptureError("B19YTWII_E_NETWORK", f"{type(exc).__name__}:{exc}") from exc


def fetch_scrapling(url: str, timeout: float = 30.0) -> HttpResult:
    try:
        from scrapling.fetchers import Fetcher

        page = Fetcher.get(
            url,
            timeout=timeout,
            retries=1,
            impersonate="chrome",
            proxy=SCRAPLING_PROXY,
        )
        return HttpResult(
            status=int(page.status),
            url=str(page.url),
            headers={str(key).lower(): str(value) for key, value in page.headers.items()},
            body=page.body,
            transport="scrapling_fetcher_chrome_proxy",
        )
    except Exception as exc:
        raise CaptureError("B19YTWII_E_NETWORK", f"scrapling:{type(exc).__name__}:{exc}") from exc


def clean_float(value: Any, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise CaptureError("B19YTWII_E_VALUE", field) from exc
    if not math.isfinite(result) or result <= 0:
        raise CaptureError("B19YTWII_E_VALUE", field)
    return result


def yahoo_payload_to_rows(
    payload: Any,
    *,
    require_target: bool = True,
    minimum_rows: int = MIN_ROWS,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("chart"), dict):
        raise CaptureError("B19YTWII_E_SCHEMA", "chart")
    chart = payload["chart"]
    if chart.get("error") is not None:
        raise CaptureError("B19YTWII_E_PROVIDER", json.dumps(chart.get("error"), sort_keys=True))
    results = chart.get("result")
    if not isinstance(results, list) or len(results) != 1 or not isinstance(results[0], dict):
        raise CaptureError("B19YTWII_E_SCHEMA", "result")
    result = results[0]
    timestamps = result.get("timestamp")
    indicators = result.get("indicators")
    if not isinstance(timestamps, list) or not timestamps or not isinstance(indicators, dict):
        raise CaptureError("B19YTWII_E_SCHEMA", "timestamp_or_indicators")
    quotes = indicators.get("quote")
    adjusted = indicators.get("adjclose")
    if not isinstance(quotes, list) or len(quotes) != 1 or not isinstance(quotes[0], dict):
        raise CaptureError("B19YTWII_E_SCHEMA", "quote")
    if not isinstance(adjusted, list) or len(adjusted) != 1 or not isinstance(adjusted[0], dict):
        raise CaptureError("B19YTWII_E_SCHEMA", "adjclose")
    quote = quotes[0]
    arrays: dict[str, list[Any]] = {}
    for field in ("open", "high", "low", "close", "volume"):
        values = quote.get(field)
        if not isinstance(values, list) or len(values) != len(timestamps):
            raise CaptureError("B19YTWII_E_SCHEMA", f"quote.{field}.length")
        arrays[field] = values
    adj_values = adjusted[0].get("adjclose")
    if not isinstance(adj_values, list) or len(adj_values) != len(timestamps):
        raise CaptureError("B19YTWII_E_SCHEMA", "adjclose.length")

    rows: list[dict[str, Any]] = []
    skipped_null_rows = 0
    seen: set[str] = set()
    for index, timestamp in enumerate(timestamps):
        values = [arrays[name][index] for name in ("open", "high", "low", "close")]
        if any(value is None for value in (*values, adj_values[index])):
            skipped_null_rows += 1
            continue
        try:
            day = datetime.fromtimestamp(int(timestamp), tz=UTC).strftime("%Y-%m-%d")
        except (TypeError, ValueError, OSError) as exc:
            raise CaptureError("B19YTWII_E_SCHEMA", f"timestamp[{index}]") from exc
        if day in seen:
            raise CaptureError("B19YTWII_E_DUPLICATE_DATE", day)
        if day > TARGET:
            raise CaptureError("B19YTWII_E_FUTURE_DATE", day)
        seen.add(day)
        open_raw = clean_float(values[0], f"open[{index}]")
        high_raw = clean_float(values[1], f"high[{index}]")
        low_raw = clean_float(values[2], f"low[{index}]")
        close_raw = clean_float(values[3], f"close[{index}]")
        adj_close = clean_float(adj_values[index], f"adjclose[{index}]")
        try:
            volume = int(float(arrays["volume"][index] or 0))
        except (TypeError, ValueError) as exc:
            raise CaptureError("B19YTWII_E_VALUE", f"volume[{index}]") from exc
        if volume < 0:
            raise CaptureError("B19YTWII_E_VALUE", f"volume[{index}]")
        factor = adj_close / close_raw
        open_adj, high_adj, low_adj, close_adj = (
            open_raw * factor,
            high_raw * factor,
            low_raw * factor,
            close_raw * factor,
        )
        high_adj = max(high_adj, open_adj, close_adj)
        low_adj = min(low_adj, open_adj, close_adj)
        rows.append(
            {
                "date": day,
                "open": open_adj,
                "high": high_adj,
                "low": low_adj,
                "close": close_adj,
                "volume": volume,
                "vwap": (open_adj + high_adj + low_adj + close_adj) / 4.0,
                "factor": factor,
                "source": SOURCE_VALUE,
            }
        )
    rows.sort(key=lambda row: row["date"])
    target_rows = [row for row in rows if row["date"] == TARGET]
    if require_target and len(target_rows) != 1:
        raise CaptureError("B19YTWII_E_TARGET_DATE", str(len(target_rows)))
    if len(rows) < minimum_rows:
        raise CaptureError("B19YTWII_E_HISTORY_ROWS", str(len(rows)))
    meta = result.get("meta") if isinstance(result.get("meta"), dict) else {}
    if (
        meta.get("symbol") != TICKER
        or meta.get("exchangeName") != "TAI"
        or meta.get("exchangeTimezoneName") != "Asia/Taipei"
        or meta.get("gmtoffset") != 28800
        or meta.get("dataGranularity") != "1d"
    ):
        raise CaptureError("B19YTWII_E_DAILY_IDENTITY")
    return rows, {
        "input_timestamp_count": len(timestamps),
        "normalized_row_count": len(rows),
        "skipped_null_rows": skipped_null_rows,
        "date_min": rows[0]["date"],
        "date_max": rows[-1]["date"],
        "target_row_count": len(target_rows),
        "exchange_name": meta.get("exchangeName"),
        "exchange_timezone_name": meta.get("exchangeTimezoneName"),
        "instrument_type": meta.get("instrumentType"),
        "symbol": meta.get("symbol"),
        "gmtoffset": meta.get("gmtoffset"),
        "data_granularity": meta.get("dataGranularity"),
        "array_lengths": {field: len(values) for field, values in arrays.items()} | {"adjclose": len(adj_values)},
    }


def yahoo_intraday_to_target_row(payload: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("chart"), dict):
        raise CaptureError("B19YTWII_E_INTRADAY_SCHEMA", "chart")
    chart = payload["chart"]
    if chart.get("error") is not None:
        raise CaptureError("B19YTWII_E_INTRADAY_PROVIDER", json.dumps(chart.get("error"), sort_keys=True))
    results = chart.get("result")
    if not isinstance(results, list) or len(results) != 1 or not isinstance(results[0], dict):
        raise CaptureError("B19YTWII_E_INTRADAY_SCHEMA", "result")
    result = results[0]
    timestamps = result.get("timestamp")
    indicators = result.get("indicators")
    if not isinstance(timestamps, list) or not isinstance(indicators, dict):
        raise CaptureError("B19YTWII_E_INTRADAY_SCHEMA", "timestamp_or_indicators")
    quotes = indicators.get("quote")
    if not isinstance(quotes, list) or len(quotes) != 1 or not isinstance(quotes[0], dict):
        raise CaptureError("B19YTWII_E_INTRADAY_SCHEMA", "quote")
    quote = quotes[0]
    arrays: dict[str, list[Any]] = {}
    for field in ("open", "high", "low", "close", "volume"):
        values = quote.get(field)
        if not isinstance(values, list) or len(values) != len(timestamps):
            raise CaptureError("B19YTWII_E_INTRADAY_SCHEMA", f"quote.{field}.length")
        arrays[field] = values
    expected_first = parse_time(f"{TARGET}T01:00:00+00:00")
    expected_last = parse_time(SESSION_CLOSE_UTC)
    parsed_times: list[datetime] = []
    for index, value in enumerate(timestamps):
        try:
            parsed = datetime.fromtimestamp(int(value), tz=UTC)
        except (TypeError, ValueError, OSError) as exc:
            raise CaptureError("B19YTWII_E_INTRADAY_SCHEMA", f"timestamp[{index}]") from exc
        if parsed.strftime("%Y-%m-%d") != TARGET:
            raise CaptureError("B19YTWII_E_INTRADAY_TARGET_DATE", iso(parsed))
        if not expected_first <= parsed <= expected_last:
            raise CaptureError("B19YTWII_E_INTRADAY_SESSION_BOUNDS", iso(parsed))
        parsed_times.append(parsed)
    if len(parsed_times) != 271 or len(set(parsed_times)) != len(parsed_times):
        raise CaptureError("B19YTWII_E_INTRADAY_POINT_COUNT", str(len(parsed_times)))
    if parsed_times != sorted(parsed_times):
        raise CaptureError("B19YTWII_E_INTRADAY_TIME_ORDER")
    if any((right - left).total_seconds() != 60 for left, right in pairwise(parsed_times)):
        raise CaptureError("B19YTWII_E_INTRADAY_DELTA")
    taipei = ZoneInfo("Asia/Taipei")
    if any(value.astimezone(taipei).date().isoformat() != TARGET for value in parsed_times):
        raise CaptureError("B19YTWII_E_INTRADAY_TAIPEI_DATE")
    if parsed_times[0] != expected_first or parsed_times[-1] != expected_last:
        raise CaptureError(
            "B19YTWII_E_INTRADAY_SESSION_ENDPOINTS",
            f"{iso(parsed_times[0])}|{iso(parsed_times[-1])}",
        )
    opens: list[float] = []
    highs: list[float] = []
    lows: list[float] = []
    closes: list[float] = []
    volumes: list[int] = []
    for index in range(len(parsed_times)):
        opens.append(clean_float(arrays["open"][index], f"intraday.open[{index}]"))
        highs.append(clean_float(arrays["high"][index], f"intraday.high[{index}]"))
        lows.append(clean_float(arrays["low"][index], f"intraday.low[{index}]"))
        closes.append(clean_float(arrays["close"][index], f"intraday.close[{index}]"))
        try:
            volume = int(float(arrays["volume"][index] or 0))
        except (TypeError, ValueError) as exc:
            raise CaptureError("B19YTWII_E_VALUE", f"intraday.volume[{index}]") from exc
        if volume < 0:
            raise CaptureError("B19YTWII_E_VALUE", f"intraday.volume[{index}]")
        volumes.append(volume)
    open_price, high, low, close = opens[0], max(highs), min(lows), closes[-1]
    if any(highs[index] < max(opens[index], closes[index]) for index in range(len(parsed_times))):
        raise CaptureError("B19YTWII_E_INTRADAY_OHLC", "high")
    if any(lows[index] > min(opens[index], closes[index]) for index in range(len(parsed_times))):
        raise CaptureError("B19YTWII_E_INTRADAY_OHLC", "low")
    meta = result.get("meta") if isinstance(result.get("meta"), dict) else {}
    if (
        meta.get("symbol") != TICKER
        or meta.get("exchangeName") != "TAI"
        or meta.get("exchangeTimezoneName") != "Asia/Taipei"
        or meta.get("gmtoffset") != 28800
        or meta.get("dataGranularity") != "1m"
    ):
        raise CaptureError("B19YTWII_E_INTRADAY_IDENTITY")
    meta_price = clean_float(meta.get("regularMarketPrice"), "meta.regularMarketPrice")
    meta_time = datetime.fromtimestamp(int(meta.get("regularMarketTime")), tz=UTC)
    meta_tolerance = 0.01
    if meta_time.strftime("%Y-%m-%d") != TARGET or not expected_last <= meta_time < parse_time(NEXT_OPEN_UTC):
        raise CaptureError("B19YTWII_E_INTRADAY_META_TIME", iso(meta_time))
    rounded_close_difference = abs(round(close, 2) - meta_price)
    if rounded_close_difference > meta_tolerance:
        raise CaptureError("B19YTWII_E_INTRADAY_META_PRICE", f"{meta_price}|{close}")
    row = {
        "date": TARGET,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": sum(volumes),
        "vwap": (open_price + high + low + close) / 4.0,
        "factor": 1.0,
        "source": INTRADAY_SOURCE_VALUE,
    }
    return row, {
        "point_count": len(parsed_times),
        "date": TARGET,
        "first_timestamp_utc": iso(parsed_times[0]),
        "last_timestamp_utc": iso(parsed_times[-1]),
        "session_bounds_valid": True,
        "adjacent_delta_seconds": 60,
        "all_taipei_dates_equal_target": True,
        "all_ohlc_non_null_positive": True,
        "aggregated_open": open_price,
        "aggregated_high": high,
        "aggregated_low": low,
        "aggregated_close": close,
        "aggregated_volume": sum(volumes),
        "meta_regular_market_price": meta_price,
        "meta_regular_market_time_utc": iso(meta_time),
        "meta_close_absolute_difference": abs(meta_price - close),
        "rounded_close_meta_absolute_difference": rounded_close_difference,
        "meta_close_tolerance": meta_tolerance,
        "gmtoffset": meta.get("gmtoffset"),
        "data_granularity": meta.get("dataGranularity"),
        "array_lengths": {field: len(values) for field, values in arrays.items()},
    }


def validate_daily_target_stub(
    daily_payload: Any,
    intraday_target_row: dict[str, Any],
    *,
    tolerance: float = 1e-9,
) -> dict[str, Any]:
    try:
        result = daily_payload["chart"]["result"][0]
        timestamps = result["timestamp"]
        quote = result["indicators"]["quote"][0]
        adjusted = result["indicators"]["adjclose"][0]["adjclose"]
    except (KeyError, IndexError, TypeError) as exc:
        raise CaptureError("B19YTWII_E_DAILY_STUB_SCHEMA") from exc
    target_indices = [
        index
        for index, value in enumerate(timestamps)
        if datetime.fromtimestamp(int(value), tz=UTC).strftime("%Y-%m-%d") == TARGET
    ]
    if len(target_indices) != 1:
        raise CaptureError("B19YTWII_E_DAILY_STUB_COUNT", str(len(target_indices)))
    index = target_indices[0]
    values = {field: quote[field][index] for field in ("open", "high", "low", "close", "volume")}
    if any(values[field] is None for field in ("open", "high", "low")):
        raise CaptureError("B19YTWII_E_DAILY_STUB_OHL_NULL")
    target_complete = values["close"] is not None and adjusted[index] is not None
    target_incomplete = values["close"] is None and adjusted[index] is None
    if not (target_complete or target_incomplete):
        raise CaptureError("B19YTWII_E_DAILY_STUB_NOT_INCOMPLETE")
    differences: dict[str, float] = {}
    for field in ("open", "high", "low"):
        differences[field] = abs(clean_float(values[field], f"daily_stub.{field}") - float(intraday_target_row[field]))
        if differences[field] > tolerance:
            raise CaptureError("B19YTWII_E_DAILY_INTRADAY_MISMATCH", field)
    if target_complete:
        differences["close"] = abs(clean_float(values["close"], "daily_target.close") - float(intraday_target_row["close"]))
        if differences["close"] > tolerance:
            raise CaptureError("B19YTWII_E_DAILY_INTRADAY_MISMATCH", "close")
    factors: list[float] = []
    for row_index, (close, adjclose) in enumerate(zip(quote["close"], adjusted, strict=True)):
        if close is None and adjclose is None:
            continue
        if close is None or adjclose is None:
            raise CaptureError("B19YTWII_E_DAILY_FACTOR_PAIR", str(row_index))
        factors.append(clean_float(adjclose, f"adjclose[{row_index}]") / clean_float(close, f"close[{row_index}]"))
    max_factor_deviation = max((abs(value - 1.0) for value in factors), default=math.inf)
    if not factors or max_factor_deviation > tolerance:
        raise CaptureError("B19YTWII_E_DAILY_FACTOR_NOT_ONE", str(max_factor_deviation))
    return {
        "target_timestamp_count": 1,
        "target_timestamp_utc": iso(datetime.fromtimestamp(int(timestamps[index]), tz=UTC)),
        "daily_stub_open": float(values["open"]),
        "daily_stub_high": float(values["high"]),
        "daily_stub_low": float(values["low"]),
        "daily_stub_close": float(values["close"]) if target_complete else None,
        "daily_stub_adjclose": float(adjusted[index]) if target_complete else None,
        "daily_stub_volume": values["volume"],
        "daily_stub_is_explicitly_incomplete": target_incomplete,
        "daily_target_mode": "complete_daily_row" if target_complete else "incomplete_daily_stub",
        "daily_vs_intraday_ohl_absolute_differences": differences,
        "ohl_tolerance": tolerance,
        "complete_daily_factor_count": len(factors),
        "complete_daily_factor_min": min(factors),
        "complete_daily_factor_max": max(factors),
        "complete_daily_factor_max_deviation_from_one": max_factor_deviation,
        "target_factor": 1.0,
        "target_factor_semantics_consistent": True,
    }


def validate_timeline(started_at: str, fetched_at: str, completed_at: str, available_at: str) -> None:
    started = parse_time(started_at)
    fetched = parse_time(fetched_at)
    completed = parse_time(completed_at)
    available = parse_time(available_at)
    if available != fetched:
        raise CaptureError("B19YTWII_E_FORGED_AVAILABLE_AT")
    if not started <= fetched <= completed:
        raise CaptureError("B19YTWII_E_BACKDATED_TIMELINE")
    if started < parse_time(SESSION_CLOSE_UTC):
        raise CaptureError("B19YTWII_E_BEFORE_SESSION_CLOSE", started_at)
    if fetched >= parse_time(NEXT_OPEN_UTC):
        raise CaptureError("B19YTWII_E_AFTER_NEXT_OPEN", fetched_at)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, default=str) + "\n", encoding="utf-8")


def artifact(path: Path) -> dict[str, Any]:
    return {"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256(path)}


def freeze(output: Path) -> None:
    for path in output.iterdir():
        if path.is_file():
            os.chmod(path, 0o444)
    os.chmod(output, 0o555)


def failure_record(
    output: Path,
    error: CaptureError,
    started_at: str,
    completed_at: str,
    before: dict[str, str | None],
) -> None:
    after = fingerprints()
    evidence = [artifact(path) for path in sorted(output.iterdir()) if path.is_file()]
    write_json(
        output / "CAPTURE_FAILURE.json",
        {
            "schema_version": "modelb_b19r2r.yahoo_twii_capture_failure.v1",
            "status": "FAIL_CLOSED",
            "error_code": error.code,
            "detail": error.detail,
            "started_at": started_at,
            "completed_at": completed_at,
            "target_asof": TARGET,
            "provider": "Yahoo Finance",
            "official_source": False,
            "evidence": evidence,
            "protected_before": before,
            "protected_after": after,
            "protected_unchanged": before == after,
            "no_publish": True,
            "no_latest_write": True,
            "production_allowed": False,
        },
    )
    freeze(output)


def capture(
    output: Path = DEFAULT_OUTPUT,
    *,
    fetcher: Callable[[str, float], HttpResult] = fetch_scrapling,
    clock: Callable[[], datetime] = utc_now,
) -> dict[str, Any]:
    output = output.resolve()
    if output.parent != RESEARCH_ROOT.resolve():
        raise CaptureError("B19YTWII_E_OUTPUT", str(output))
    if output.exists():
        raise CaptureError("B19YTWII_E_NO_OVERWRITE", str(output))
    before = fingerprints()
    output.mkdir(parents=True, mode=0o700, exist_ok=False)
    started_at = iso(clock())
    acquisition_run_id = os.environ.get("B19YTWII_ACQUISITION_RUN_ID", "").strip() or (
        "research.yahoo_twii.20260916." + parse_time(started_at).strftime("%Y%m%dT%H%M%S%fZ")
    )
    daily_parameters = request_parameters()
    daily_url = request_url(daily_parameters)
    daily_request_path = output / "REQUEST_DAILY.json"
    write_json(
        daily_request_path,
        {
            "endpoint": ENDPOINT,
            "request_url": daily_url,
            "request_parameters": daily_parameters,
            "ticker": TICKER,
            "target_asof": TARGET,
            "history_start": START,
            "role": "adjusted_daily_history",
            "transport": "Scrapling Fetcher impersonate=chrome",
            "proxy": SCRAPLING_PROXY,
            "started_at": started_at,
            "timeout_seconds": 30.0,
            "timestamp_source": "process_system_clock_utc",
            "caller_supplied_timestamps_allowed": False,
        },
    )
    try:
        if parse_time(started_at) < parse_time(SESSION_CLOSE_UTC):
            raise CaptureError("B19YTWII_E_BEFORE_SESSION_CLOSE", started_at)
        if parse_time(started_at) >= parse_time(NEXT_OPEN_UTC):
            raise CaptureError("B19YTWII_E_AFTER_NEXT_OPEN", started_at)
        try:
            daily_response = fetcher(daily_url, 30.0)
        except CaptureError:
            raise
        except Exception as exc:
            raise CaptureError("B19YTWII_E_NETWORK", f"{type(exc).__name__}:{exc}") from exc
        daily_fetched_at = iso(clock())
        daily_raw_path = output / "twii_daily_raw.json"
        daily_raw_path.write_bytes(daily_response.body)
        daily_headers_path = output / "RESPONSE_HEADERS_DAILY.json"
        write_json(daily_headers_path, daily_response.headers)
        if daily_response.status != 200:
            raise CaptureError("B19YTWII_E_HTTP", f"daily:{daily_response.status}")
        try:
            daily_payload = json.loads(daily_response.body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CaptureError("B19YTWII_E_JSON", f"daily:{type(exc).__name__}:{exc}") from exc
        daily_rows, daily_coverage = yahoo_payload_to_rows(daily_payload, require_target=False)

        intraday_started_at = iso(clock())
        intraday_parameters = intraday_request_parameters()
        intraday_url = request_url(intraday_parameters)
        intraday_request_path = output / "REQUEST_INTRADAY.json"
        write_json(
            intraday_request_path,
            {
                "endpoint": ENDPOINT,
                "request_url": intraday_url,
                "request_parameters": intraday_parameters,
                "ticker": TICKER,
                "target_asof": TARGET,
                "role": "target_day_1m_ohlc_aggregation",
                "transport": "Scrapling Fetcher impersonate=chrome",
                "proxy": SCRAPLING_PROXY,
                "started_at": intraday_started_at,
                "timeout_seconds": 30.0,
                "timestamp_source": "process_system_clock_utc",
                "caller_supplied_timestamps_allowed": False,
            },
        )
        try:
            intraday_response = fetcher(intraday_url, 30.0)
        except CaptureError:
            raise
        except Exception as exc:
            raise CaptureError("B19YTWII_E_NETWORK", f"intraday:{type(exc).__name__}:{exc}") from exc
        intraday_fetched_at = iso(clock())
        intraday_raw_path = output / "twii_intraday_1m_raw.json"
        intraday_raw_path.write_bytes(intraday_response.body)
        intraday_headers_path = output / "RESPONSE_HEADERS_INTRADAY.json"
        write_json(intraday_headers_path, intraday_response.headers)
        if intraday_response.status != 200:
            raise CaptureError("B19YTWII_E_HTTP", f"intraday:{intraday_response.status}")
        try:
            intraday_payload = json.loads(intraday_response.body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CaptureError("B19YTWII_E_JSON", f"intraday:{type(exc).__name__}:{exc}") from exc
        target_row, intraday_coverage = yahoo_intraday_to_target_row(intraday_payload)
        daily_stub_evidence = validate_daily_target_stub(daily_payload, target_row)
        rows = [row for row in daily_rows if row["date"] != TARGET]
        rows.append(target_row)
        rows.sort(key=lambda row: row["date"])
        if len(rows) < MIN_ROWS or rows[-1]["date"] != TARGET:
            raise CaptureError("B19YTWII_E_COMBINED_COVERAGE")
        coverage = {
            "normalized_row_count": len(rows),
            "date_min": rows[0]["date"],
            "date_max": rows[-1]["date"],
            "target_row_count": sum(row["date"] == TARGET for row in rows),
            "daily": daily_coverage,
            "daily_target_stub": daily_stub_evidence,
            "intraday_target_aggregation": intraday_coverage,
        }
        normalized_path = output / "TWII_NORMALIZED.csv"
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=NORMALIZED_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        normalized_path.write_text(buffer.getvalue(), encoding="utf-8")
        schema_path = output / "NORMALIZED_SCHEMA.json"
        write_json(
            schema_path,
            {
                "schema_version": "modelb_b19r2r.yahoo_twii_dual_interval_normalized.v1",
                "columns": NORMALIZED_COLUMNS,
                "primary_key": ["date"],
                "ticker": TICKER,
                "provider": "Yahoo Finance",
                "official_source": False,
                "date_semantics": "UTC calendar date from Yahoo chart timestamps",
                "history_semantics": "1d rows use the prior project parser mapping and adjusted OHLC",
                "target_semantics": f"{TARGET} is aggregated from exact 01:00-05:30Z Yahoo 1m OHLC; factor=1.0",
                "adjustment_semantics": "1d factor=adjclose/close; target 1m aggregation has no adjusted series and uses factor=1.0",
                "vwap_semantics": "derived adjusted OHLC4; not provider trade VWAP",
                "source_values": [SOURCE_VALUE, INTRADAY_SOURCE_VALUE],
                "independent_review_required": True,
                "future_or_outcome_fields": [],
            },
        )
        completed_at = iso(clock())
        validate_timeline(started_at, intraday_fetched_at, completed_at, intraday_fetched_at)
        if not (
            parse_time(started_at)
            <= parse_time(daily_fetched_at)
            <= parse_time(intraday_started_at)
            <= parse_time(intraday_fetched_at)
            <= parse_time(completed_at)
        ):
            raise CaptureError("B19YTWII_E_BACKDATED_TIMELINE")
        after = fingerprints()
        if before != after:
            raise CaptureError("B19YTWII_E_PROTECTED_DRIFT")
        server_dates: dict[str, str | None] = {}
        for role, headers in (("daily", daily_response.headers), ("intraday", intraday_response.headers)):
            value = headers.get("date")
            try:
                server_dates[role] = parsedate_to_datetime(value).astimezone(UTC).isoformat(timespec="seconds") if value else None
            except (TypeError, ValueError, OverflowError):
                server_dates[role] = None
        manifest = {
            "schema_version": "modelb_b19r2r.yahoo_twii_dual_interval_capture.v2",
            "status": "PASS_REVIEWABLE_CANDIDATE",
            "acquisition_run_id": acquisition_run_id,
            "source_family": "market_index_daily_price",
            "source_id": "yahoo.finance.chart.^TWII.dual_interval.v2",
            "implementation": {
                "path": rel(Path(__file__)),
                "sha256": sha256(Path(__file__)),
            },
            "provider": "Yahoo Finance",
            "official_source": False,
            "provider_description": "third-party Yahoo Finance chart endpoint; not an official TWSE source",
            "endpoint": ENDPOINT,
            "requests": {
                "daily": {
                    "url": daily_url,
                    "parameters": daily_parameters,
                    "transport": daily_response.transport,
                },
                "intraday": {
                    "url": intraday_url,
                    "parameters": intraday_parameters,
                    "transport": intraday_response.transport,
                },
            },
            "proxy": SCRAPLING_PROXY,
            "proxy_used": True,
            "target_asof": TARGET,
            "trade_date": TARGET,
            "history_start": START,
            "started_at": started_at,
            "daily_fetched_at": daily_fetched_at,
            "intraday_started_at": intraday_started_at,
            "intraday_fetched_at": intraday_fetched_at,
            "fetched_at": intraday_fetched_at,
            "completed_at": completed_at,
            "available_at": intraday_fetched_at,
            "availability_policy": "maximum first-successful observation time across bound daily and intraday responses",
            "timestamp_source": "process_system_clock_utc",
            "caller_supplied_timestamps_allowed": False,
            "next_session_open_utc": NEXT_OPEN_UTC,
            "available_before_next_session_open": True,
            "http_status": {"daily": daily_response.status, "intraday": intraday_response.status},
            "response_url": {"daily": daily_response.url, "intraday": intraday_response.url},
            "server_date_utc": server_dates,
            "coverage": coverage,
            "minimum_history_rows": MIN_ROWS,
            "normalized_columns": NORMALIZED_COLUMNS,
            "parser_semantics_reference": "scripts/build_tw_policy_rcpt15_r3_t_isolated_price_twii_source_repair.py:yahoo_payload_to_frame",
            "target_materialization": "Yahoo Finance 1m exact-session OHLC aggregation; no meta price fill",
            "independent_review_required": True,
            "same_run_contract_decision": "NOT_MADE",
            "upper_layer_materialization_authorized": False,
            "artifacts": {
                "daily_request": artifact(daily_request_path),
                "daily_response_headers": artifact(daily_headers_path),
                "daily_raw_response": artifact(daily_raw_path),
                "intraday_request": artifact(intraday_request_path),
                "intraday_response_headers": artifact(intraday_headers_path),
                "intraday_raw_response": artifact(intraday_raw_path),
                "normalized_csv": artifact(normalized_path),
                "normalized_schema": artifact(schema_path),
            },
            "raw_sha256": {"daily": sha256(daily_raw_path), "intraday": sha256(intraday_raw_path)},
            "normalized_sha256": sha256(normalized_path),
            "pit_status": "PASS",
            "validator_status": "PASS_CANDIDATE_AWAITING_INDEPENDENT_REVIEW",
            "future_or_outcome_fields": [],
            "protected_before": before,
            "protected_after": after,
            "protected_unchanged": True,
            "write_once": True,
            "research_only": True,
            "training_performed": False,
            "scoring_performed": False,
            "capture_or_ledger_append_performed": False,
            "no_publish": True,
            "no_latest_write": True,
            "production_allowed": False,
        }
        manifest_path = output / "TWII_CAPTURE_MANIFEST.json"
        write_json(manifest_path, manifest)
        freeze(output)
        return manifest
    except CaptureError as error:
        failure_record(output, error, started_at, iso(clock()), before)
        raise
    except Exception as exc:
        error = CaptureError("B19YTWII_E_UNEXPECTED", f"{type(exc).__name__}:{exc}")
        failure_record(output, error, started_at, iso(clock()), before)
        raise error from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        result = capture(args.output)
    except CaptureError as exc:
        print(json.dumps({"status": "FAIL", "error_code": exc.code, "detail": exc.detail}, sort_keys=True))
        return 2
    print(
        json.dumps(
            {
                "status": result["status"],
                "acquisition_run_id": result["acquisition_run_id"],
                "available_at": result["available_at"],
                "rows": result["coverage"]["normalized_row_count"],
                "date_max": result["coverage"]["date_max"],
                "raw_sha256": result["raw_sha256"],
                "normalized_sha256": result["normalized_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
