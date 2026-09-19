#!/usr/bin/env python3
"""Acquire an isolated Yahoo execution-outcome candidate for 2026-09-17."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import urllib.parse
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable

import build_modelb_b19r2r_v5_prospective_accumulator as accumulator
import validate_modelb_b19r2r_v5_prospective_accumulator as accumulator_validator


ROOT = Path(__file__).resolve().parents[1]
RESEARCH_ROOT = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_v5_execution_outcome_20260917"
DEFAULT_OUTPUT = RESEARCH_ROOT / "execution_outcome_candidate_v1"
DEFAULT_ACCUMULATOR = (
    ROOT / "data_tw/experiments/modelb_b19r2r_v5_prospective_accumulator/accepted_prospective_events"
)
SIGNAL_ASOF = "2026-09-16"
EXECUTION_DATE = "2026-09-17"
SESSION_OPEN_UTC = "2026-09-17T01:00:00+00:00"
SESSION_CLOSE_UTC = "2026-09-17T05:30:00+00:00"
YAHOO_ENDPOINT = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
SCRAPLING_PROXY = "http://127.0.0.1:7890"
CSV_NAME = "EXECUTION_PRICES.csv"
MANIFEST_NAME = "EXECUTION_PRICES_MANIFEST.json"
CALENDAR_NAME = "CONFIRMED_CURRENT_CALENDAR.txt"
AVAILABILITY_NAME = "AVAILABILITY_EVIDENCE.json"
SOURCE_EVENTS_NAME = "SOURCE_EVENTS_SNAPSHOT.jsonl"
PROTECTED = (
    ROOT / "configs/tw_modular_registry.yaml",
    ROOT / "configs/active_baseline_descriptor.yaml",
    ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json",
    DEFAULT_ACCUMULATOR / "events.jsonl",
    DEFAULT_ACCUMULATOR / "summary.json",
)


class AcquisitionError(RuntimeError):
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
    transport: str = "test"


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise AcquisitionError("B19V5X_E_TIMEZONE", str(value))
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def parse_time(value: Any, code: str = "B19V5X_E_TIME") -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise AcquisitionError(code, str(value)) from exc
    if parsed.tzinfo is None:
        raise AcquisitionError(code, "timezone required")
    return parsed.astimezone(UTC)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AcquisitionError("B19V5X_E_JSON", str(path)) from exc
    if not isinstance(value, dict):
        raise AcquisitionError("B19V5X_E_JSON", str(path))
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, default=str) + "\n",
        encoding="utf-8",
    )


def atomic_write(path: Path, value: bytes) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def fingerprint(path: Path) -> str | None:
    return sha256(path) if path.is_file() else None


def fingerprints() -> dict[str, str | None]:
    return {rel(path): fingerprint(path) for path in PROTECTED}


def accumulator_fingerprints(path: Path) -> dict[str, str]:
    names = ["events.jsonl", "summary.json", ".events.lock"]
    files = [path / name for name in names]
    for directory in (path / "calendar_snapshots", path / "sealed_outcomes"):
        if directory.is_dir():
            files.extend(item for item in directory.rglob("*") if item.is_file())
    return {str(item.resolve()): sha256(item) for item in sorted(files) if item.is_file()}


def freeze(path: Path) -> None:
    for child in path.rglob("*"):
        if child.is_file():
            os.chmod(child, 0o444)
    for child in sorted((item for item in path.rglob("*") if item.is_dir()), reverse=True):
        os.chmod(child, 0o555)
    os.chmod(path, 0o555)


def request_parameters() -> dict[str, str]:
    start = datetime.strptime(EXECUTION_DATE, "%Y-%m-%d").replace(tzinfo=UTC)
    return {
        "period1": str(int(start.timestamp())),
        "period2": str(int((start + timedelta(days=1)).timestamp())),
        "interval": "1d",
        "events": "history",
        "includeAdjustedClose": "false",
    }


def request_url(ticker: str) -> str:
    endpoint = YAHOO_ENDPOINT.format(ticker=urllib.parse.quote(ticker, safe=""))
    return endpoint + "?" + urllib.parse.urlencode(request_parameters())


def fetch_scrapling(url: str, timeout: float) -> HttpResult:
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
        raise AcquisitionError("B19V5X_E_NETWORK", f"{type(exc).__name__}:{exc}") from exc


def yahoo_tickers(instrument: str) -> list[str]:
    if not instrument.startswith("TW") or not instrument[2:].isdigit():
        raise AcquisitionError("B19V5X_E_SYMBOL", instrument)
    code = instrument[2:]
    return [f"{code}.TW", f"{code}.TWO"]


def positive_number(value: Any, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise AcquisitionError("B19V5X_E_NONFINITE_PRICE", field) from exc
    if not math.isfinite(result) or result <= 0:
        raise AcquisitionError("B19V5X_E_NONFINITE_PRICE", field)
    return result


def provider_datetime(value: Any, field: str, code: str) -> datetime:
    try:
        if isinstance(value, bool):
            raise ValueError("boolean timestamp")
        if isinstance(value, float) and not value.is_integer():
            raise ValueError("fractional timestamp")
        timestamp = int(value)
        return datetime.fromtimestamp(timestamp, UTC)
    except (TypeError, ValueError, OverflowError, OSError) as exc:
        raise AcquisitionError(code, field) from exc


def parse_target_bar(payload: Any, ticker: str) -> dict[str, Any] | None:
    if not isinstance(payload, dict) or not isinstance(payload.get("chart"), dict):
        raise AcquisitionError("B19V5X_E_PROVIDER_SCHEMA", ticker)
    chart = payload["chart"]
    if chart.get("error") is not None:
        return None
    results = chart.get("result")
    if not isinstance(results, list) or len(results) != 1 or not isinstance(results[0], dict):
        return None
    result = results[0]
    timestamps = result.get("timestamp")
    indicators = result.get("indicators")
    if not isinstance(indicators, dict):
        raise AcquisitionError("B19V5X_E_PROVIDER_SCHEMA", f"{ticker}:indicators")
    quotes = indicators.get("quote")
    if not isinstance(timestamps, list) or not isinstance(quotes, list) or len(quotes) != 1:
        raise AcquisitionError("B19V5X_E_PROVIDER_SCHEMA", ticker)
    quote = quotes[0]
    if not isinstance(quote, dict):
        raise AcquisitionError("B19V5X_E_PROVIDER_SCHEMA", f"{ticker}:quote")
    opens = quote.get("open")
    closes = quote.get("close")
    if not isinstance(opens, list) or not isinstance(closes, list) or len(opens) != len(timestamps) or len(closes) != len(timestamps):
        raise AcquisitionError("B19V5X_E_PROVIDER_SCHEMA", ticker)
    timestamp_values = [
        provider_datetime(stamp, f"{ticker}:timestamp[{index}]", "B19V5X_E_PROVIDER_TIMESTAMP")
        for index, stamp in enumerate(timestamps)
    ]
    matching = [
        index
        for index, timestamp in enumerate(timestamp_values)
        if timestamp.date().isoformat() == EXECUTION_DATE
    ]
    if len(matching) > 1:
        raise AcquisitionError("B19V5X_E_DUPLICATE_TARGET_BAR", ticker)
    if not matching:
        if timestamps:
            raise AcquisitionError("B19V5X_E_WRONG_DATE", ticker)
        return None
    meta = result.get("meta")
    if not isinstance(meta, dict):
        raise AcquisitionError("B19V5X_E_PROVIDER_SCHEMA", ticker)
    if meta.get("symbol") != ticker:
        raise AcquisitionError("B19V5X_E_PROVIDER_SYMBOL", f"{ticker}:{meta.get('symbol')}")
    regular_market_time = provider_datetime(
        meta.get("regularMarketTime"),
        f"{ticker}:regularMarketTime",
        "B19V5X_E_FINAL_CLOSE_UNPROVEN",
    )
    if regular_market_time < parse_time(SESSION_CLOSE_UTC):
        raise AcquisitionError("B19V5X_E_FINAL_CLOSE_UNPROVEN", ticker)
    index = matching[0]
    return {
        "next_open": positive_number(opens[index], f"{ticker}:open"),
        "next_close": positive_number(closes[index], f"{ticker}:close"),
        "regular_market_time": regular_market_time.isoformat(timespec="seconds"),
    }


def load_source_signal(path: Path) -> dict[str, Any]:
    try:
        validation = accumulator_validator.validate_accumulator(path)
        events = accumulator.load_events(path / "events.jsonl")
    except accumulator.ContractError as exc:
        raise AcquisitionError("B19V5X_E_SOURCE_ACCUMULATOR", exc.code) from exc
    signals = [
        event
        for event in events
        if event.get("event_type") == "SIGNAL_CAPTURED" and event.get("asof") == SIGNAL_ASOF
    ]
    if validation.get("status") != "PASS" or len(signals) != 1:
        raise AcquisitionError("B19V5X_E_SOURCE_SIGNAL", f"count={len(signals)}")
    event = signals[0]
    symbols = event.get("exact50_symbols")
    if (
        not isinstance(symbols, list)
        or len(symbols) != accumulator.EXACT_COUNT
        or len(set(symbols)) != accumulator.EXACT_COUNT
        or accumulator.EXCLUDED_SYMBOL in symbols
        or event.get("source_run_id") == ""
    ):
        raise AcquisitionError("B19V5X_E_SOURCE_EXACT50")
    calendar = accumulator.resolve(str(event.get("trading_calendar") or ""))
    if not calendar.is_file() or sha256(calendar) != event.get("trading_calendar_sha256"):
        raise AcquisitionError("B19V5X_E_FROZEN_CALENDAR")
    dates = accumulator.calendar_dates(calendar)
    if dates[-1] != SIGNAL_ASOF or EXECUTION_DATE in dates:
        raise AcquisitionError("B19V5X_E_FROZEN_CALENDAR")
    return {
        "event": event,
        "symbols": sorted(str(item) for item in symbols),
        "events_path": path / "events.jsonl",
        "events_sha256": sha256(path / "events.jsonl"),
        "calendar": calendar,
        "calendar_dates": dates,
    }


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    buffer = io.StringIO(newline="")
    fields = ["asof", "instrument", "execution_date", "next_open", "next_close"]
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def artifact_entry(path: Path) -> dict[str, Any]:
    return {"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256(path)}


def preserve_failure(
    stage: Path | None,
    output: Path,
    error: AcquisitionError,
    started_at: str,
    *,
    protected_before: dict[str, str | None],
    accumulator_before: dict[str, str],
    source_accumulator: Path,
) -> Path | None:
    if stage is None or not stage.exists():
        return None
    write_json(
        stage / "CAPTURE_FAILURE.json",
        {
            "schema_version": "modelb_b19r2r.v5.execution_outcome_failure.v1",
            "status": "FAIL_CLOSED",
            "error_code": error.code,
            "detail": error.detail,
            "started_at": started_at,
            "failed_at": iso(utc_now()),
            "signal_asof": SIGNAL_ASOF,
            "execution_date": EXECUTION_DATE,
            "protected_before": protected_before,
            "protected_after": fingerprints(),
            "protected_unchanged": fingerprints() == protected_before,
            "accumulator_before": accumulator_before,
            "accumulator_after": accumulator_fingerprints(source_accumulator),
            "accumulator_unchanged": accumulator_fingerprints(source_accumulator) == accumulator_before,
            "ledger_event_written": False,
            "settlement_performed": False,
            "production_allowed": False,
        },
    )
    failed = output.with_name(f"{output.name}.failed.{stage.name.rsplit('.', 1)[-1]}")
    freeze(stage)
    os.replace(stage, failed)
    return failed


def capture(
    output: Path = DEFAULT_OUTPUT,
    *,
    source_accumulator: Path = DEFAULT_ACCUMULATOR,
    fetcher: Callable[[str, float], HttpResult] = fetch_scrapling,
    clock: Callable[[], datetime] = utc_now,
    timeout: float = 30.0,
) -> dict[str, Any]:
    output = output.resolve()
    if output.parent != RESEARCH_ROOT.resolve():
        raise AcquisitionError("B19V5X_E_OUTPUT", str(output))
    if output.exists() or any(output.parent.glob(f"{output.name}.partial.*")):
        raise AcquisitionError("B19V5X_E_NO_OVERWRITE", str(output))
    started_at = iso(clock())
    started = parse_time(started_at)
    if started < parse_time(SESSION_OPEN_UTC):
        raise AcquisitionError("B19V5X_E_PREOPEN", started_at)
    if started < parse_time(SESSION_CLOSE_UTC):
        raise AcquisitionError("B19V5X_E_INTRADAY", started_at)

    before = fingerprints()
    accumulator_before = accumulator_fingerprints(source_accumulator.resolve())
    source = load_source_signal(source_accumulator.resolve())
    if fingerprints() != before or accumulator_fingerprints(source_accumulator.resolve()) != accumulator_before:
        raise AcquisitionError("B19V5X_E_PROTECTED_DRIFT", "source validation")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = output.with_name(f"{output.name}.partial.{uuid.uuid4().hex}")
    stage.mkdir(mode=0o700)
    source_run_id = "research.yahoo_execution_prices.20260917." + started.strftime("%Y%m%dT%H%M%S%fZ")
    rows: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []
    fetch_times: list[str] = []
    try:
        for instrument in source["symbols"]:
            selected: dict[str, Any] | None = None
            for attempt_number, ticker in enumerate(yahoo_tickers(instrument), start=1):
                request_started_at = iso(clock())
                url = request_url(ticker)
                stem = f"{instrument}.{attempt_number}.{ticker}"
                request_path = stage / "requests" / f"{stem}.json"
                write_json(
                    request_path,
                    {
                        "method": "GET",
                        "url": url,
                        "parameters": request_parameters(),
                        "instrument": instrument,
                        "ticker": ticker,
                        "attempt": attempt_number,
                        "started_at": request_started_at,
                        "transport": "Scrapling Fetcher impersonate=chrome",
                        "proxy": SCRAPLING_PROXY,
                        "timeout_seconds": timeout,
                    },
                )
                try:
                    response = fetcher(url, timeout)
                except AcquisitionError:
                    raise
                except Exception as exc:
                    raise AcquisitionError("B19V5X_E_NETWORK", f"{instrument}:{type(exc).__name__}:{exc}") from exc
                fetched_at = iso(clock())
                fetch_times.append(fetched_at)
                raw_path = stage / "raw" / f"{stem}.json"
                headers_path = stage / "headers" / f"{stem}.json"
                raw_path.parent.mkdir(parents=True, exist_ok=True)
                raw_path.write_bytes(response.body)
                write_json(headers_path, {str(key).lower(): str(value) for key, value in response.headers.items()})
                attempt = {
                    "instrument": instrument,
                    "ticker": ticker,
                    "attempt": attempt_number,
                    "request_started_at": request_started_at,
                    "request": str(request_path.relative_to(stage)),
                    "request_sha256": sha256(request_path),
                    "raw": str(raw_path.relative_to(stage)),
                    "raw_sha256": sha256(raw_path),
                    "headers": str(headers_path.relative_to(stage)),
                    "headers_sha256": sha256(headers_path),
                    "http_status": response.status,
                    "response_url": response.url,
                    "transport": response.transport,
                    "fetched_at": fetched_at,
                }
                attempts.append(attempt)
                if response.status != 200:
                    continue
                try:
                    payload = json.loads(response.body)
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise AcquisitionError("B19V5X_E_JSON", ticker) from exc
                selected = parse_target_bar(payload, ticker)
                if selected is not None:
                    attempt["selected"] = True
                    attempt["regular_market_time"] = selected["regular_market_time"]
                    break
            if selected is None:
                raise AcquisitionError("B19V5X_E_MISSING_SYMBOL", instrument)
            rows.append(
                {
                    "asof": SIGNAL_ASOF,
                    "instrument": instrument,
                    "execution_date": EXECUTION_DATE,
                    "next_open": selected["next_open"],
                    "next_close": selected["next_close"],
                }
            )

        instruments = [row["instrument"] for row in rows]
        if (
            len(rows) != accumulator.EXACT_COUNT
            or len(set(instruments)) != accumulator.EXACT_COUNT
            or set(instruments) != set(source["symbols"])
            or accumulator.EXCLUDED_SYMBOL in instruments
        ):
            raise AcquisitionError("B19V5X_E_EXACT50_SCOPE")
        fetch_completed_at = iso(clock())
        fetch_timeline = [
            parse_time(started_at),
            *[parse_time(value) for value in fetch_times],
            parse_time(fetch_completed_at),
        ]
        if fetch_timeline != sorted(fetch_timeline):
            raise AcquisitionError("B19V5X_E_TIMELINE")
        if (
            fingerprints() != before
            or accumulator_fingerprints(source_accumulator.resolve()) != accumulator_before
        ):
            raise AcquisitionError("B19V5X_E_PROTECTED_DRIFT", "after fetch")

        calendar_path = stage / CALENDAR_NAME
        calendar_content = "\n".join([*source["calendar_dates"], EXECUTION_DATE]) + "\n"
        atomic_write(calendar_path, calendar_content.encode("ascii"))
        csv_path = stage / CSV_NAME
        atomic_write(csv_path, csv_bytes(rows))
        source_events_path = stage / SOURCE_EVENTS_NAME
        atomic_write(source_events_path, source["events_path"].read_bytes())
        csv_committed_at = iso(clock())
        available_at = iso(clock())
        if not (
            parse_time(SESSION_CLOSE_UTC)
            <= parse_time(fetch_completed_at)
            <= parse_time(csv_committed_at)
            <= parse_time(available_at)
        ):
            raise AcquisitionError("B19V5X_E_TIMELINE")
        availability_path = stage / AVAILABILITY_NAME
        write_json(
            availability_path,
            {
                "schema_version": "modelb_b19r2r.v5.execution_outcome_availability.v1",
                "source_run_id": source_run_id,
                "signal_asof": SIGNAL_ASOF,
                "execution_date": EXECUTION_DATE,
                "started_at": started_at,
                "fetch_completed_at": fetch_completed_at,
                "csv_committed_at": csv_committed_at,
                "available_at": available_at,
                "timestamp_source": "process_system_clock_utc",
                "caller_supplied_timestamps_allowed": False,
            },
        )
        manifest_path = stage / MANIFEST_NAME
        event = source["event"]
        manifest = {
            "schema_version": "modelb_b19r2r.v5.execution_outcome_candidate.v1",
            "status": "PASS_REVIEWABLE_CANDIDATE",
            "source_run_id": source_run_id,
            "signal_asof": SIGNAL_ASOF,
            "execution_date": EXECUTION_DATE,
            "started_at": started_at,
            "fetch_completed_at": fetch_completed_at,
            "csv_committed_at": csv_committed_at,
            "available_at": available_at,
            "availability_policy": "system clock after atomic CSV fsync/replace and all successful Yahoo responses",
            "availability_evidence": AVAILABILITY_NAME,
            "availability_evidence_sha256": sha256(availability_path),
            "artifact": CSV_NAME,
            "artifact_sha256": sha256(csv_path),
            "row_count": len(rows),
            "provider": "Yahoo Finance",
            "official_source": False,
            "source_policy": "Yahoo chart via Scrapling; .TW then .TWO suffix only; no provider fallback",
            "request_attempt_count": len(attempts),
            "attempts": attempts,
            "source_accumulator": rel(source_accumulator.resolve()),
            "source_ledger": rel(source["events_path"]),
            "source_events_snapshot": SOURCE_EVENTS_NAME,
            "source_ledger_sha256": sha256(source_events_path),
            "source_signal_event_hash": event["event_hash"],
            "source_signal_run_id": event["source_run_id"],
            "source_model_id": event["model_id"],
            "source_model_sha256": event["model_sha256"],
            "exact50_symbols_sha256": canonical_hash(source["symbols"]),
            "frozen_calendar": rel(source["calendar"]),
            "frozen_calendar_sha256": sha256(source["calendar"]),
            "current_calendar": CALENDAR_NAME,
            "current_calendar_sha256": sha256(calendar_path),
            "calendar_extension": {
                "frozen_last_date": source["calendar_dates"][-1],
                "appended_confirmed_trade_date": EXECUTION_DATE,
                "confirmation": "50_of_50_final_yahoo_daily_bars_after_formal_session_close",
            },
            "exact50_complete": True,
            "all_prices_finite_positive": True,
            "tw7769_excluded": True,
            "protected_before": before,
            "protected_after": fingerprints(),
            "protected_unchanged": fingerprints() == before,
            "accumulator_before": accumulator_before,
            "accumulator_after": accumulator_fingerprints(source_accumulator.resolve()),
            "accumulator_unchanged": accumulator_fingerprints(source_accumulator.resolve()) == accumulator_before,
            "ledger_event_written": False,
            "settlement_performed": False,
            "label_maturation_performed": False,
            "training_performed": False,
            "production_allowed": False,
        }
        atomic_write(
            manifest_path,
            (json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8"),
        )
        validate_candidate(stage, source_accumulator=source_accumulator.resolve())
        freeze(stage)
        os.replace(stage, output)
        return read_json(output / MANIFEST_NAME)
    except AcquisitionError as error:
        preserve_failure(
            stage,
            output,
            error,
            started_at,
            protected_before=before,
            accumulator_before=accumulator_before,
            source_accumulator=source_accumulator.resolve(),
        )
        raise
    except Exception as exc:
        error = AcquisitionError("B19V5X_E_UNEXPECTED", type(exc).__name__)
        preserve_failure(
            stage,
            output,
            error,
            started_at,
            protected_before=before,
            accumulator_before=accumulator_before,
            source_accumulator=source_accumulator.resolve(),
        )
        raise error from exc


def validate_candidate(output: Path, *, source_accumulator: Path = DEFAULT_ACCUMULATOR) -> dict[str, Any]:
    manifest_path = output / MANIFEST_NAME
    csv_path = output / CSV_NAME
    availability_path = output / AVAILABILITY_NAME
    calendar_path = output / CALENDAR_NAME
    source_events_path = output / SOURCE_EVENTS_NAME
    if not all(
        path.is_file()
        for path in (manifest_path, csv_path, availability_path, calendar_path, source_events_path)
    ):
        raise AcquisitionError("B19V5X_E_REQUIRED_FILE")
    manifest = read_json(manifest_path)
    availability = read_json(availability_path)
    source = load_source_signal(source_accumulator.resolve())
    if (
        manifest.get("schema_version") != "modelb_b19r2r.v5.execution_outcome_candidate.v1"
        or manifest.get("status") != "PASS_REVIEWABLE_CANDIDATE"
        or manifest.get("signal_asof") != SIGNAL_ASOF
        or manifest.get("execution_date") != EXECUTION_DATE
        or manifest.get("source_signal_event_hash") != source["event"]["event_hash"]
        or manifest.get("source_ledger_sha256") != sha256(source_events_path)
        or manifest.get("source_signal_run_id") != source["event"]["source_run_id"]
        or manifest.get("source_accumulator") != rel(source_accumulator.resolve())
        or manifest.get("source_ledger") != rel(source["events_path"])
        or manifest.get("source_model_id") != source["event"]["model_id"]
        or manifest.get("source_model_sha256") != source["event"]["model_sha256"]
        or manifest.get("artifact_sha256") != sha256(csv_path)
        or manifest.get("availability_evidence_sha256") != sha256(availability_path)
        or manifest.get("current_calendar_sha256") != sha256(calendar_path)
        or manifest.get("frozen_calendar_sha256") != sha256(source["calendar"])
        or manifest.get("artifact") != CSV_NAME
        or manifest.get("availability_evidence") != AVAILABILITY_NAME
        or manifest.get("current_calendar") != CALENDAR_NAME
        or manifest.get("source_events_snapshot") != SOURCE_EVENTS_NAME
        or manifest.get("exact50_symbols_sha256") != canonical_hash(source["symbols"])
        or manifest.get("exact50_complete") is not True
        or manifest.get("all_prices_finite_positive") is not True
        or manifest.get("tw7769_excluded") is not True
        or manifest.get("ledger_event_written") is not False
        or manifest.get("settlement_performed") is not False
        or manifest.get("production_allowed") is not False
    ):
        raise AcquisitionError("B19V5X_E_MANIFEST_BINDING")
    try:
        snapshot_events = accumulator.load_events(source_events_path)
    except accumulator.ContractError as exc:
        raise AcquisitionError("B19V5X_E_SOURCE_LEDGER_SNAPSHOT", exc.code) from exc
    current_lines = source["events_path"].read_bytes().splitlines()
    snapshot_lines = source_events_path.read_bytes().splitlines()
    if (
        not snapshot_events
        or current_lines[: len(snapshot_lines)] != snapshot_lines
        or not any(
            event.get("event_type") == "SIGNAL_CAPTURED"
            and event.get("asof") == SIGNAL_ASOF
            and event.get("event_hash") == manifest.get("source_signal_event_hash")
            for event in snapshot_events
        )
    ):
        raise AcquisitionError("B19V5X_E_SOURCE_LEDGER_SNAPSHOT")
    if (
        availability.get("source_run_id") != manifest.get("source_run_id")
        or availability.get("started_at") != manifest.get("started_at")
        or availability.get("fetch_completed_at") != manifest.get("fetch_completed_at")
        or availability.get("csv_committed_at") != manifest.get("csv_committed_at")
        or availability.get("available_at") != manifest.get("available_at")
        or availability.get("caller_supplied_timestamps_allowed") is not False
    ):
        raise AcquisitionError("B19V5X_E_AVAILABLE_AT_BINDING")
    started = parse_time(manifest.get("started_at"))
    fetched = parse_time(manifest.get("fetch_completed_at"))
    committed = parse_time(manifest.get("csv_committed_at"))
    available = parse_time(manifest.get("available_at"))
    attempts = manifest.get("attempts")
    if not isinstance(attempts, list) or not attempts:
        raise AcquisitionError("B19V5X_E_ATTEMPT_INVENTORY")
    fetched_attempts = [parse_time(item.get("fetched_at")) for item in attempts]
    if not (
        parse_time(SESSION_CLOSE_UTC) <= started
        and fetched_attempts
        and max(fetched_attempts) <= fetched <= committed <= available
    ):
        raise AcquisitionError("B19V5X_E_TIMELINE")
    if (
        manifest.get("protected_before") != manifest.get("protected_after")
        or manifest.get("protected_unchanged") is not True
        or manifest.get("accumulator_before") != manifest.get("accumulator_after")
        or manifest.get("accumulator_unchanged") is not True
    ):
        raise AcquisitionError("B19V5X_E_PROTECTED_DRIFT", "manifest")
    with csv_path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    expected_fields = ["asof", "instrument", "execution_date", "next_open", "next_close"]
    if not rows or list(rows[0]) != expected_fields:
        raise AcquisitionError("B19V5X_E_CSV_SCHEMA")
    symbols: list[str] = []
    rows_by_symbol: dict[str, dict[str, str]] = {}
    for row in rows:
        if row["asof"] != SIGNAL_ASOF or row["execution_date"] != EXECUTION_DATE:
            raise AcquisitionError("B19V5X_E_WRONG_DATE")
        positive_number(row["next_open"], f"{row['instrument']}:open")
        positive_number(row["next_close"], f"{row['instrument']}:close")
        symbols.append(row["instrument"])
        rows_by_symbol[row["instrument"]] = row
    if (
        len(rows) != accumulator.EXACT_COUNT
        or len(set(symbols)) != accumulator.EXACT_COUNT
        or set(symbols) != set(source["symbols"])
        or accumulator.EXCLUDED_SYMBOL in symbols
        or manifest.get("row_count") != accumulator.EXACT_COUNT
    ):
        raise AcquisitionError("B19V5X_E_EXACT50_SCOPE")
    try:
        current_dates = accumulator.calendar_dates(calendar_path)
    except accumulator.ContractError as exc:
        raise AcquisitionError("B19V5X_E_CALENDAR_EXTENSION", exc.code) from exc
    if current_dates[:-1] != source["calendar_dates"] or current_dates[-1] != EXECUTION_DATE:
        raise AcquisitionError("B19V5X_E_CALENDAR_EXTENSION")
    if manifest.get("request_attempt_count") != len(attempts):
        raise AcquisitionError("B19V5X_E_ATTEMPT_INVENTORY", "count")
    selected_symbols: list[str] = []
    grouped: dict[str, list[dict[str, Any]]] = {}
    previous_fetched_at = started
    for attempt in attempts:
        instrument = str(attempt.get("instrument") or "")
        grouped.setdefault(instrument, []).append(attempt)
        for path_key, hash_key in (("request", "request_sha256"), ("raw", "raw_sha256"), ("headers", "headers_sha256")):
            raw_path = Path(str(attempt.get(path_key) or ""))
            path = (output / raw_path).resolve()
            if (
                raw_path.is_absolute()
                or not path.is_relative_to(output.resolve())
                or not path.is_file()
                or sha256(path) != attempt.get(hash_key)
            ):
                raise AcquisitionError("B19V5X_E_ATTEMPT_INVENTORY", str(path))
        request_path = (output / str(attempt["request"])).resolve()
        raw_path = (output / str(attempt["raw"])).resolve()
        headers_path = (output / str(attempt["headers"])).resolve()
        request = read_json(request_path)
        headers = read_json(headers_path)
        ticker = str(attempt.get("ticker") or "")
        expected_attempt = int(attempt.get("attempt") or -1)
        if (
            request.get("method") != "GET"
            or request.get("url") != request_url(ticker)
            or request.get("parameters") != request_parameters()
            or request.get("instrument") != instrument
            or request.get("ticker") != ticker
            or request.get("attempt") != expected_attempt
            or request.get("started_at") != attempt.get("request_started_at")
            or attempt.get("response_url") != request.get("url")
            or not str(attempt.get("transport") or "")
            or not isinstance(headers, dict)
        ):
            raise AcquisitionError("B19V5X_E_ATTEMPT_BINDING", ticker)
        request_started = parse_time(attempt.get("request_started_at"))
        response_fetched = parse_time(attempt.get("fetched_at"))
        if not previous_fetched_at <= request_started <= response_fetched <= fetched:
            raise AcquisitionError("B19V5X_E_TIMELINE", ticker)
        previous_fetched_at = response_fetched
        parsed_bar: dict[str, Any] | None = None
        if attempt.get("http_status") == 200:
            try:
                payload = json.loads(raw_path.read_bytes())
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise AcquisitionError("B19V5X_E_JSON", ticker) from exc
            parsed_bar = parse_target_bar(payload, ticker)
        if attempt.get("selected") is True:
            if parsed_bar is None or instrument not in rows_by_symbol:
                raise AcquisitionError("B19V5X_E_SELECTED_RAW_BINDING", ticker)
            csv_row = rows_by_symbol[instrument]
            if (
                positive_number(csv_row["next_open"], f"{instrument}:open") != parsed_bar["next_open"]
                or positive_number(csv_row["next_close"], f"{instrument}:close") != parsed_bar["next_close"]
                or attempt.get("regular_market_time") != parsed_bar["regular_market_time"]
            ):
                raise AcquisitionError("B19V5X_E_SELECTED_RAW_BINDING", ticker)
            selected_symbols.append(instrument)
        elif parsed_bar is not None:
            raise AcquisitionError("B19V5X_E_ATTEMPT_BINDING", f"unselected usable:{ticker}")
    for instrument, instrument_attempts in grouped.items():
        tickers = yahoo_tickers(instrument)
        observed = [str(item.get("ticker") or "") for item in instrument_attempts]
        numbers = [int(item.get("attempt") or -1) for item in instrument_attempts]
        selected_positions = [index for index, item in enumerate(instrument_attempts) if item.get("selected") is True]
        if (
            instrument not in source["symbols"]
            or observed != tickers[: len(observed)]
            or numbers != list(range(1, len(observed) + 1))
            or selected_positions != [len(instrument_attempts) - 1]
        ):
            raise AcquisitionError("B19V5X_E_ATTEMPT_ORDER", instrument)
    if sorted(selected_symbols) != source["symbols"] or len(selected_symbols) != accumulator.EXACT_COUNT:
        raise AcquisitionError("B19V5X_E_ATTEMPT_INVENTORY", "selected exact50")
    return {
        "status": "PASS",
        "row_count": len(rows),
        "source_run_id": manifest["source_run_id"],
        "artifact_sha256": manifest["artifact_sha256"],
        "current_calendar_sha256": manifest["current_calendar_sha256"],
        "available_at": manifest["available_at"],
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    item = commands.add_parser("capture")
    item.add_argument("--out", default=str(DEFAULT_OUTPUT))
    item.add_argument("--source-accumulator", default=str(DEFAULT_ACCUMULATOR))
    item.add_argument("--timeout", type=float, default=30.0)
    item = commands.add_parser("validate")
    item.add_argument("--candidate", default=str(DEFAULT_OUTPUT))
    item.add_argument("--source-accumulator", default=str(DEFAULT_ACCUMULATOR))
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "capture":
            value = capture(
                Path(args.out),
                source_accumulator=Path(args.source_accumulator),
                timeout=args.timeout,
            )
        else:
            value = validate_candidate(
                Path(args.candidate).resolve(),
                source_accumulator=Path(args.source_accumulator),
            )
    except AcquisitionError as exc:
        print(json.dumps({"status": "FAIL", "error_code": exc.code, "detail": exc.detail}, sort_keys=True))
        return 2
    print(json.dumps({"status": "PASS", "result": value}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
