#!/usr/bin/env python3
"""Run the daily TWStock archive + official validation workflow.

This is the operational wrapper for Phase 2. It is dry-run by default. With
--apply it writes FinMind daily bars to qd_tw_stock_daily_bars and then updates
TWSE official validation fields for matching archived rows.
"""
from __future__ import annotations

import argparse
import csv
import ctypes
import hashlib
import json
import os
import stat
import subprocess
import sys
import time
from pathlib import Path
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.data_sources.tw_stock import FINMIND_BASE_URL  # noqa: E402

os.environ.setdefault("SECRET_KEY", "update-tw-stock-daily")
os.environ.setdefault("ADMIN_USER", "update")
os.environ.setdefault("ADMIN_PASSWORD", "updatepass")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _capture_file_bindings(paths: Sequence[str], role: str) -> list[dict[str, str]]:
    return [{"path": str(path), "role": role, "sha256": _file_sha256(Path(path))} for path in paths]


def _canonical_capture_metadata(capture: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "provider", "source_id", "trade_date", "http_status", "validator_status", "pit_status",
        "expected_scope", "returned_scope", "absent_scope", "unknown_scope", "endpoint",
        "endpoint_version", "request_parameters", "acquisition_run_id", "target_asof",
        "raw_files", "normalized_files",
    )
    metadata = {field: capture.get(field) for field in fields}
    if "availability_evidence" in capture:
        metadata["availability_evidence"] = capture["availability_evidence"]
    return metadata


def _set_capture_digest(capture: dict[str, Any], raw_paths: Sequence[str], normalized_paths: Sequence[str]) -> None:
    capture["raw_files"] = _capture_file_bindings(raw_paths, "provider_raw_response")
    capture["normalized_files"] = _capture_file_bindings(normalized_paths, "provider_normalized_payload")
    canonical = json.dumps(_canonical_capture_metadata(capture), ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    capture["canonical_metadata_digest"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

from scripts.archive_tw_stock_daily import (  # noqa: E402
    DailyBarRecord,
    fetch_finmind_rows,
    parse_finmind_rows,
    summarize as summarize_archive,
    upsert_records,
)
from scripts.archive_tw_stock_corporate_actions import (  # noqa: E402
    archive_symbols as archive_corporate_action_symbols,
    summarize as summarize_corporate_actions,
    upsert_records as upsert_corporate_actions,
)
from scripts.archive_tw_stock_institutional_trades import (  # noqa: E402
    archive_symbols as archive_institutional_symbols,
    parse_finmind_rows as parse_institutional_rows,
    summarize as summarize_institutional_trades,
    upsert_records as upsert_institutional_trades,
)
from scripts.archive_tw_stock_margin_trading import (  # noqa: E402
    archive_symbols as archive_margin_symbols,
    parse_finmind_rows as parse_margin_rows,
    summarize as summarize_margin_trading,
    upsert_records as upsert_margin_trading,
)
from scripts.archive_tw_stock_monthly_revenue import (  # noqa: E402
    archive_symbols as archive_monthly_revenue_symbols,
    summarize as summarize_monthly_revenue,
    upsert_records as upsert_monthly_revenue,
)
from scripts.archive_tw_stock_valuation import (  # noqa: E402
    archive_symbols as archive_valuation_symbols,
    summarize as summarize_valuation,
    upsert_records as upsert_valuation,
)
from scripts.validate_tw_stock_daily import (  # noqa: E402
    compare_record_to_official,
    fetch_twse_rows,
    latest_records_by_symbol,
    summarize as summarize_validation,
    update_archive_validation,
)

DEFAULT_SYMBOLS = ("2330", "0050", "0056", "00878")


def _atomic_bytes(path: Path, payload: bytes) -> None:
    """Write capture bytes without following links or replacing an existing file."""
    parent_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    parent_before = os.fstat(parent_fd)
    parent_path_before = os.lstat(path.parent)
    parent_identity = (parent_before.st_dev, parent_before.st_ino)
    if not stat.S_ISDIR(parent_path_before.st_mode) or (parent_path_before.st_dev, parent_path_before.st_ino) != parent_identity:
        os.close(parent_fd)


        raise OSError("capture parent locator changed before write")
    stage_name = f".{path.name}.staging.{os.getpid()}"
    try:
        fd = os.open(stage_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o640, dir_fd=parent_fd)
    except Exception:
        os.close(parent_fd)
        raise
    try:
        view = memoryview(payload)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("short write")
            view = view[written:]
        os.fsync(fd)
    except Exception:
        try:
            os.unlink(stage_name, dir_fd=parent_fd)
        except FileNotFoundError:
            pass
        os.close(parent_fd)
        raise
    finally:
        os.close(fd)
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        os.unlink(stage_name, dir_fd=parent_fd)
        os.close(parent_fd)
        raise OSError("renameat2 unavailable")
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    if renameat2(parent_fd, os.fsencode(stage_name), parent_fd, os.fsencode(path.name), 1) != 0:
        error = ctypes.get_errno()
        try:
            os.unlink(stage_name, dir_fd=parent_fd)
        except FileNotFoundError:
            pass
        os.close(parent_fd)
        raise OSError(error, "renameat2 no-replace failed")
    parent_after = os.fstat(parent_fd)
    parent_path_after = os.lstat(path.parent)
    if (parent_after.st_dev, parent_after.st_ino) != parent_identity or not stat.S_ISDIR(parent_path_after.st_mode) or (parent_path_after.st_dev, parent_path_after.st_ino) != parent_identity:
        os.close(parent_fd)
        raise OSError("capture parent locator changed after write")
    os.fsync(parent_fd)
    os.close(parent_fd)


def _finmind_get(requests_module: Any, params: dict[str, Any], *, last_request_at: float) -> tuple[Any, float, int]:
    """Perform one paced FinMind request with bounded provider backoff."""
    interval = max(0.0, float(os.getenv("FINMIND_MIN_REQUEST_INTERVAL_SECONDS", "1.0")))
    retries = max(0, int(os.getenv("FINMIND_TRANSIENT_RETRIES", "2")))
    backoff = max(0.0, float(os.getenv("FINMIND_RETRY_BACKOFF_SECONDS", "5.0")))
    request_count = 0
    for attempt in range(retries + 1):
        wait = interval - (time.monotonic() - last_request_at)
        if last_request_at and wait > 0:
            time.sleep(wait)
        try:
            response = requests_module.get(FINMIND_BASE_URL, params=params, timeout=20)
        except Exception:
            request_count += 1
            if attempt >= retries:
                raise
            time.sleep(backoff * (2**attempt))
            last_request_at = time.monotonic()
            continue
        request_count += 1
        last_request_at = time.monotonic()
        if int(getattr(response, "status_code", 0) or 0) not in {402, 429}:
            response.raise_for_status()
            return response, last_request_at, request_count
        if attempt >= retries:
            response.raise_for_status()
        time.sleep(backoff * (2**attempt))
    raise RuntimeError("FinMind request retry loop exhausted")


def _real_hsa8_finmind_capture(*, segment: str, symbols: Sequence[str], start: str, end: str, output_dir: Optional[str], acquisition_run_id: str = "") -> tuple[list[Any], dict[str, Any]]:
    """Fetch and retain actual FinMind HTTP bytes for an HSA8-enabled invocation."""
    if not output_dir:
        return [], {"status": "disabled"}
    import requests

    parsers = {
        "daily_price": ("TaiwanStockPrice", parse_finmind_rows),
        "institutional": ("TaiwanStockInstitutionalInvestorsBuySell", parse_institutional_rows),
        "margin": ("TaiwanStockMarginPurchaseShortSale", parse_margin_rows),
    }
    dataset, parser = parsers[segment]
    source_families = {
        "daily_price": "adjusted_price",
        "institutional": "institutional_flow",
        "margin": "margin_short",
    }
    root = Path(output_dir)
    records: list[Any] = []
    raw_paths: list[str] = []
    fetched_at: list[str] = []
    http_statuses: list[int] = []
    response_timing_headers_by_symbol: dict[str, dict[str, str]] = {}
    trade_dates: set[str] = set()
    last_request_at = 0.0
    total_request_count = 0
    for symbol in symbols:
        params: dict[str, Any] = {"dataset": dataset, "data_id": symbol, "start_date": start, "end_date": end}
        token = os.getenv("FINMIND_TOKEN") or os.getenv("FINMIND_API_TOKEN")
        if token:
            params["token"] = token.strip()
        fetched = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        response, last_request_at, request_count = _finmind_get(
            requests,
            params,
            last_request_at=last_request_at,
        )
        total_request_count += request_count
        http_statuses.append(int(response.status_code))
        # Preserve provider timing hints as observations only.  These headers
        # are never promoted to PIT PASS without an explicit provider policy.
        response_headers = {
            key.lower(): str(response.headers.get(key) or "")
            for key in ("Date", "Last-Modified", "ETag", "Age")
            if getattr(response, "headers", None) is not None and response.headers.get(key)
        }
        response_timing_headers_by_symbol[str(symbol)] = response_headers
        raw_path = root / f"{segment}.{symbol}.http.raw"
        _atomic_bytes(raw_path, response.content)
        raw_paths.append(str(raw_path))
        fetched_at.append(fetched)
        payload = response.json()
        if payload.get("status") not in (None, 200, "200", True):
            raise ValueError(f"FinMind returned non-ok status for {symbol}: {payload.get('status')}")
        data = payload.get("data") or []
        if not isinstance(data, list):
            raise ValueError(f"FinMind data must be a list for {symbol}")
        trade_dates.update(str(row.get("date") or "").strip() for row in data if isinstance(row, dict) and row.get("date"))
        records.extend(parser(data, symbol=symbol))
    normalized_path = root / f"{segment}.normalized.json"
    normalized_payload = {
        "segment": segment,
        "artifact_kind": "provider_normalized_payload",
        "records": [asdict(item) for item in records],
    }
    _atomic_bytes(normalized_path, (json.dumps(normalized_payload, ensure_ascii=False, default=str, sort_keys=True) + "\n").encode("utf-8"))
    returned_scope = sorted({str(record.symbol).strip().upper() for record in records if str(record.trade_date) == end})
    expected_scope = sorted(set(symbols))
    unknown_scope = sorted(set(expected_scope) - set(returned_scope))
    scope_complete = bool(returned_scope) and not unknown_scope
    capture = {
        "source_family": source_families[segment],
        "acquisition_run_id": acquisition_run_id,
        "target_asof": end,
        "status": "captured",
        "provider": "FinMind",
        "source_id": f"finmind.{dataset.lower()}.v1",
        "dataset": dataset,
        "endpoint": FINMIND_BASE_URL,
        "endpoint_version": "api/v4/data",
        "request_parameters": {
            "dataset": dataset,
            "start_date": start,
            "end_date": end,
            "symbol_count": len(symbols),
            "request_count": total_request_count,
            "min_request_interval_seconds": max(0.0, float(os.getenv("FINMIND_MIN_REQUEST_INTERVAL_SECONDS", "1.0"))),
            "transient_retries": max(0, int(os.getenv("FINMIND_TRANSIENT_RETRIES", "2"))),
        },
        "http_status": max(http_statuses, default=599),
        "response_timing_headers_by_symbol": response_timing_headers_by_symbol,
        "parser_version": "daily-auto-hsa8-v2",
        "schema_version": "finmind-provider-records.v1",
        "transport_identity": "python-requests-response-content",
        "raw_paths": raw_paths,
        "normalized_paths": [str(normalized_path)],
        "fetched_at": max(fetched_at, default=""),
        "source_published_at": None,
        # This is an observed lower bound for future runs, not provider
        # publication time.  HSA8 still requires authoritative scope and
        # validator PASS before downstream use.
        "available_at": max(fetched_at, default="") or None,
        "availability_evidence": {
            "method": "first_successful_capture",
            "observed_at": max(fetched_at, default="") or None,
            "observation_scope": "segment_capture",
        },
        "http_response_bytes": True,
        "pit_status": "PASS" if scope_complete else "BLOCKED_PUBLICATION_AND_AVAILABILITY_UNPROVEN",
        # Scope is derived only from parsed records in this invocation and
        # only for the requested target date. Missing symbols remain unknown;
        # they are never silently classified as absent.
        "validator_status": "PASS" if scope_complete else "BLOCKED_SOURCE_SCOPE_OR_VALIDATOR_UNPROVEN",
        "trade_date": end if scope_complete else max(trade_dates, default=""),
        "expected_scope": expected_scope,
        "returned_scope": returned_scope,
        "absent_scope": [],
        "unknown_scope": unknown_scope,
    }
    _set_capture_digest(capture, raw_paths, [str(normalized_path)])
    capture_path = root / f"{segment}.adapter_output.json"
    _atomic_bytes(capture_path, (json.dumps(capture, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))
    capture["adapter_output_path"] = str(capture_path)
    return records, capture


def _real_hsa8_twii_capture(*, start: str, end: str, output_dir: Optional[str], acquisition_run_id: str = "") -> dict[str, Any]:
    """Capture TWII from TWSE, with an isolated Yahoo dual-interval fallback.

    The fallback is only eligible after the TWSE response fails the exact date
    and identity validator. It runs the frozen write-once Yahoo capture in the
    same job directory and never touches accepted latest/provider state.
    """
    if not output_dir:
        return {"status": "disabled"}
    import requests

    endpoint = "https://openapi.twse.com.tw/v1/exchangeReport/MI_INDEX"
    fetched = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    twse_path = root / "twii.http.raw"
    twse_normalized = root / "twii.normalized.json"
    twse_error = ""
    try:
        response = requests.get(endpoint, params={"date": end.replace("-", ""), "response": "json"}, timeout=20)
        response.raise_for_status()
    except Exception as exc:
        response = None
        twse_error = f"{type(exc).__name__}:{exc}"
    response_headers = {
        key.lower(): str(response.headers.get(key) or "")
        for key in ("Date", "Last-Modified", "ETag", "Age")
        if response is not None and getattr(response, "headers", None) is not None and response.headers.get(key)
    }
    if response is not None:
        _atomic_bytes(twse_path, response.content)
        try:
            payload = response.json()
            rows = payload if isinstance(payload, list) else payload.get("data", []) if isinstance(payload, dict) else []
            schema = validate_twii_response_rows(rows, target_asof=end)
        except Exception as exc:
            rows = []
            schema = {"ok": False, "errors": [f"response_parse:{type(exc).__name__}"], "trade_date": ""}
        data = json.dumps({"segment": "twii", "artifact_kind": "provider_normalized_payload", "records": rows if isinstance(rows, list) else []}, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n"
        _atomic_bytes(twse_normalized, data)
    else:
        rows = []
        schema = {"ok": False, "errors": ["request_failed"], "trade_date": ""}
    schema_ok = bool(schema["ok"])
    twse_capture = {
        "source_family": "twii",
        "acquisition_run_id": acquisition_run_id,
        "target_asof": end,
        "status": "captured",
        "provider": "TWSE OpenAPI",
        "source_id": "twse.mi_index.v1",
        "endpoint": endpoint,
        "endpoint_version": "v1/exchangeReport/MI_INDEX",
        "request_parameters": {"date": end.replace("-", ""), "response": "json"},
        "http_status": int(response.status_code) if response is not None else 599,
        "response_timing_headers": response_headers,
        "parser_version": "daily-auto-hsa8-twii-v1",
        "schema_version": "twse-mi-index.v1",
        "transport_identity": "python-requests-response-content",
        "raw_paths": [str(twse_path)] if response is not None else [],
        "normalized_paths": [str(twse_normalized)] if response is not None else [],
        "fetched_at": fetched,
        "source_published_at": None,
        "available_at": fetched,
        "availability_evidence": {
            "method": "first_successful_capture",
            "observed_at": fetched,
            "observation_scope": "twii_capture",
        },
        "http_response_bytes": True,
        "pit_status": "PASS" if schema_ok else "BLOCKED_PUBLICATION_AND_AVAILABILITY_UNPROVEN",
        "scope_status": "PASS_SCHEMA_AND_SCOPE" if schema_ok else "BLOCKED_PROVIDER_SCHEMA",
        "validator_status": "PASS" if schema_ok else "BLOCKED_PROVIDER_SCHEMA",
        "schema_errors": schema["errors"],
        "trade_date": schema.get("trade_date", ""),
        "expected_scope": ["TWII"],
        "returned_scope": ["TWII"] if schema_ok else [],
        "absent_scope": [],
        "unknown_scope": [] if schema_ok else ["TWII"],
    }
    if twse_error:
        twse_capture["schema_errors"] = [*twse_capture["schema_errors"], twse_error]
    if response is not None:
        _set_capture_digest(twse_capture, [str(twse_path)], [str(twse_normalized)])

    if schema_ok:
        capture_path = root / "twii.adapter_output.json"
        _atomic_bytes(capture_path, (json.dumps(twse_capture, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))
        twse_capture["adapter_output_path"] = str(capture_path)
        return twse_capture

    # Preserve the rejected TWSE evidence and try the already-reviewed Yahoo
    # dual-interval capture without modifying any accepted/latest path.
    failure_path = root / "twii.twse_failure.adapter_output.json"
    _atomic_bytes(failure_path, (json.dumps(twse_capture, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))
    yahoo_root = root / "twii_yahoo_scrapling"
    capture_script = Path(__file__).resolve().parents[2] / "scripts" / "capture_modelb_b19r2r_twii_yahoo_20260916.py"
    target_day = date.fromisoformat(end)
    next_day = target_day + timedelta(days=1)
    while next_day.weekday() >= 5:
        next_day += timedelta(days=1)
    env = os.environ.copy()
    env.update({
        "B19YTWII_RESEARCH_ROOT": str(root),
        "B19YTWII_TARGET_ASOF": end,
        "B19YTWII_ACQUISITION_RUN_ID": acquisition_run_id,
        "B19YTWII_SESSION_CLOSE_UTC": f"{end}T05:30:00+00:00",
        "B19YTWII_NEXT_OPEN_UTC": f"{next_day.isoformat()}T01:00:00+00:00",
    })
    command = [sys.executable, str(capture_script), "--output", str(yahoo_root)]
    try:
        result = subprocess.run(command, cwd=str(capture_script.parents[1]), env=env, text=True, capture_output=True, timeout=120, check=False)
    except Exception as exc:
        result = None
        fallback_error = f"{type(exc).__name__}:{exc}"
    else:
        fallback_error = (result.stderr or result.stdout or "").strip()[-2000:]
    _atomic_bytes(root / "twii_yahoo_capture.stdout.txt", ((result.stdout if result else "") or "").encode("utf-8"))
    _atomic_bytes(root / "twii_yahoo_capture.stderr.txt", ((result.stderr if result else fallback_error) or "").encode("utf-8"))
    manifest_path = yahoo_root / "TWII_CAPTURE_MANIFEST.json"
    if result is None or result.returncode != 0 or not manifest_path.is_file():
        twse_capture["fallback"] = {
            "attempted": True,
            "status": "BLOCKED",
            "error": fallback_error,
            "command": command,
            "output_dir": str(yahoo_root),
        }
        capture_path = root / "twii.adapter_output.json"
        _set_capture_digest(twse_capture, [str(twse_path)] if response is not None else [], [str(twse_normalized)] if response is not None else []) if response is not None else None
        _atomic_bytes(capture_path, (json.dumps(twse_capture, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))
        twse_capture["adapter_output_path"] = str(capture_path)
        return twse_capture

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("pit_status") != "PASS" or manifest.get("target_asof") != end or manifest.get("validator_status") not in {"PASS", "PASS_CANDIDATE_AWAITING_INDEPENDENT_REVIEW"}:
        twse_capture["fallback"] = {"attempted": True, "status": "BLOCKED", "error": "yahoo_manifest_contract_failed", "manifest": str(manifest_path)}
        capture_path = root / "twii.adapter_output.json"
        _set_capture_digest(twse_capture, [str(twse_path)] if response is not None else [], [str(twse_normalized)] if response is not None else []) if response is not None else None
        _atomic_bytes(capture_path, (json.dumps(twse_capture, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))
        twse_capture["adapter_output_path"] = str(capture_path)
        return twse_capture

    normalized_path = yahoo_root / "TWII_NORMALIZED.csv"
    rows_out: list[dict[str, Any]] = []
    with normalized_path.open(newline="", encoding="utf-8") as handle:
        rows_out = [dict(row) for row in csv.DictReader(handle)]
    if not rows_out or rows_out[-1].get("date") != end:
        raise RuntimeError("Yahoo TWII fallback normalized output has no target row")
    adapter = {
        "source_family": "twii",
        "acquisition_run_id": acquisition_run_id,
        "target_asof": end,
        "status": "captured",
        "provider": "Yahoo Finance",
        "source_id": "yahoo.finance.chart.twii.dual_interval.v1",
        "endpoint": manifest.get("endpoint"),
        "endpoint_version": "v8/finance/chart.dual_interval",
        "request_parameters": manifest.get("requests"),
        "http_status": 200,
        "response_timing_headers": manifest.get("server_date_utc"),
        "parser_version": "modelb-b19r2r-yahoo-dual-interval-v1",
        "schema_version": manifest.get("schema_version"),
        "transport_identity": "scrapling_fetcher_chrome_proxy",
        "raw_paths": [str(yahoo_root / "twii_daily_raw.json"), str(yahoo_root / "twii_intraday_1m_raw.json")],
        "normalized_paths": [str(normalized_path)],
        "fetched_at": manifest.get("fetched_at"),
        "source_published_at": None,
        "available_at": manifest.get("available_at"),
        "availability_evidence": {"method": "first_successful_capture", "observed_at": manifest.get("available_at"), "observation_scope": "twii_yahoo_dual_interval"},
        "http_response_bytes": True,
        "pit_status": "PASS",
        "scope_status": "PASS_SCHEMA_AND_SCOPE",
        "validator_status": "PASS_CANDIDATE_AWAITING_INDEPENDENT_REVIEW",
        "schema_errors": [],
        "trade_date": end,
        "expected_scope": ["TWII"],
        "returned_scope": ["TWII"],
        "absent_scope": [],
        "unknown_scope": [],
        "official_source": False,
        "independent_review_required": True,
        "fallback_from": {"provider": "TWSE OpenAPI", "schema_errors": twse_capture.get("schema_errors", []), "adapter_output": str(failure_path)},
    }
    _set_capture_digest(adapter, adapter["raw_paths"], adapter["normalized_paths"])
    capture_path = root / "twii.adapter_output.json"
    _atomic_bytes(capture_path, (json.dumps(adapter, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))
    adapter["adapter_output_path"] = str(capture_path)
    adapter["fallback"] = {"attempted": True, "status": "PASS_CANDIDATE", "manifest": str(manifest_path), "row_count": len(rows_out), "rejected_twse_adapter": str(failure_path)}
    return adapter


def validate_twii_response_rows(rows: Any, *, target_asof: str) -> dict[str, Any]:
    """Validate TWII response structure and target date only.

    Scope partitioning is an adapter responsibility.  This validator must not
    turn a schema match into a returned/absent/unknown claim.
    """
    errors: list[str] = []
    if not isinstance(rows, list) or not rows:
        return {"ok": False, "errors": ["rows_missing_or_empty"], "row_count": 0, "trade_date": ""}
    if any(not isinstance(row, dict) for row in rows):
        errors.append("row_not_object")
    date_keys = {"日期", "date", "Date"}
    value_keys = {"收盤指數", "ClosingIndex", "close", "closing_index"}
    if not errors and any(not date_keys.intersection(row) for row in rows):
        errors.append("date_field_missing")
    if not errors and any(not value_keys.intersection(row) for row in rows):
        errors.append("closing_index_field_missing")
    dates = set()
    def normalize_twse_date(value: Any) -> str:
        raw = str(value or "").replace("/", "-").strip()
        compact = raw.replace("-", "")
        # TWSE commonly returns Republic of China calendar dates (e.g. 1150828).
        if len(compact) == 7 and compact.isdigit():
            try:
                return f"{int(compact[:3]) + 1911:04d}-{compact[3:5]}-{compact[5:]}"
            except ValueError:
                return raw
        return raw

    for row in rows:
        value = next((row[key] for key in date_keys if key in row), "")
        dates.add(normalize_twse_date(value))
    normalized_target = normalize_twse_date(target_asof)
    if not errors and any(value != normalized_target for value in dates):
        errors.append("target_date_mismatch")
    identity_keys = {"指數", "指數名稱", "name", "Name", "instrument", "symbol"}
    # MI_INDEX also contains the weighted total-return index.  Select the
    # exact price index identity instead of treating both names as TWII.
    exact_twii = {"TWII", "發行量加權股價指數"}
    twii_rows = [row for row in rows if any(str(row.get(key, "")).strip() in exact_twii for key in identity_keys)]
    if not errors and len(twii_rows) != 1:
        errors.append("twii_identity_not_exactly_one")
    return {"ok": not errors, "errors": errors, "row_count": len(rows), "trade_date": target_asof if not errors else ""}


def _write_handoff_records(output_dir: Optional[str], segment: str, records: Sequence[Any]) -> None:
    """Persist this invocation's provider records for the caller's handoff gate."""
    if not output_dir:
        return
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    payload = {
        "segment": segment,
        "artifact_kind": "provider_record_capture_not_authoritative_raw",
        "records": [asdict(item) for item in records],
    }
    path = target / f"{segment}.raw.json"
    data = json.dumps(payload, ensure_ascii=False, default=str, sort_keys=True).encode("utf-8") + b"\n"
    with path.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    normalized = []
    for item in records:
        row = asdict(item)
        row.pop("raw_json", None)
        normalized.append(row)
    path = target / f"{segment}.normalized.json"
    data = json.dumps({"segment": segment, "artifact_kind": "provider_normalized_payload", "records": normalized}, ensure_ascii=False, default=str, sort_keys=True).encode("utf-8") + b"\n"
    with path.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def normalize_symbol(raw: str) -> str:
    symbol = str(raw or "").strip().upper()
    if symbol.startswith("TWSE:") or symbol.startswith("TPEX:"):
        symbol = symbol.split(":", 1)[1]
    if symbol.startswith("TW") and symbol[2:].isdigit():
        symbol = symbol[2:]
    for suffix in (".TWSE", ".TPEX", ".TWO", ".TW"):
        if symbol.endswith(suffix):
            symbol = symbol[: -len(suffix)]
            break
    return symbol


def parse_symbols(raw_symbols: Sequence[str]) -> List[str]:
    out: List[str] = []
    for raw in raw_symbols or []:
        for part in str(raw or "").replace("\n", ",").split(","):
            symbol = normalize_symbol(part)
            if symbol and symbol not in out:
                out.append(symbol)
    return out

def load_symbols_from_file(path: str) -> List[str]:
    if not path:
        return []
    symbols = []
    for line in open(path, "r", encoding="utf-8"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        symbols.extend(parse_symbols([stripped]))
    return symbols


def archive_symbols(symbols: Sequence[str], start: str, end: str) -> List[DailyBarRecord]:
    records: List[DailyBarRecord] = []
    for symbol in symbols:
        rows = fetch_finmind_rows(symbol, start, end)
        records.extend(parse_finmind_rows(rows, symbol=symbol))
    return records


def validate_latest(records: Sequence[DailyBarRecord]) -> List[Any]:
    official_by_symbol = fetch_twse_rows()
    latest = latest_records_by_symbol(records)
    results = []
    for symbol in sorted(latest):
        results.append(compare_record_to_official(latest[symbol], official_by_symbol.get(symbol)))
    return results


def run_workflow(
    *,
    symbols: Sequence[str],
    start: str,
    end: str,
    apply: bool = False,
    validate: bool = True,
    daily_price: bool = True,
    corporate_actions: bool = True,
    institutional: bool = True,
    margin: bool = True,
    monthly_revenue: bool = True,
    valuation: bool = True,
    handoff_output_dir: Optional[str] = None,
    acquisition_run_id: str = "",
) -> Dict[str, Any]:
    real_capture = bool(handoff_output_dir)
    if daily_price and real_capture:
        records, daily_capture = _real_hsa8_finmind_capture(segment="daily_price", symbols=symbols, start=start, end=end, output_dir=handoff_output_dir, acquisition_run_id=acquisition_run_id)
    else:
        records = archive_symbols(symbols, start, end) if daily_price else []
        daily_capture = {"status": "not_requested"}
    if not real_capture:
        _write_handoff_records(handoff_output_dir, "daily_price", records)
    archive_summary = summarize_archive(records)
    archived_count = upsert_records(records) if apply and records else 0

    validation_results = validate_latest(records) if validate and records else []
    validation_summary = summarize_validation(validation_results)
    updated_count = update_archive_validation(validation_results) if apply and validation_results else 0

    corporate_action_records = archive_corporate_action_symbols(symbols, start, end) if corporate_actions else []
    if not real_capture:
        _write_handoff_records(handoff_output_dir, "corporate_actions", corporate_action_records)
    corporate_action_summary = summarize_corporate_actions(corporate_action_records)
    corporate_action_archived_count = upsert_corporate_actions(corporate_action_records) if apply and corporate_action_records else 0

    if institutional and real_capture:
        institutional_records, institutional_capture = _real_hsa8_finmind_capture(segment="institutional", symbols=symbols, start=start, end=end, output_dir=handoff_output_dir, acquisition_run_id=acquisition_run_id)
    else:
        institutional_records = archive_institutional_symbols(symbols, start, end) if institutional else []
        institutional_capture = {"status": "not_requested"}
    if not real_capture:
        _write_handoff_records(handoff_output_dir, "institutional", institutional_records)
    institutional_summary = summarize_institutional_trades(institutional_records)
    institutional_archived_count = upsert_institutional_trades(institutional_records) if apply and institutional_records else 0

    if margin and real_capture:
        margin_records, margin_capture = _real_hsa8_finmind_capture(segment="margin", symbols=symbols, start=start, end=end, output_dir=handoff_output_dir, acquisition_run_id=acquisition_run_id)
    else:
        margin_records = archive_margin_symbols(symbols, start, end) if margin else []
        margin_capture = {"status": "not_requested"}
    if not real_capture:
        _write_handoff_records(handoff_output_dir, "margin", margin_records)
    margin_summary = summarize_margin_trading(margin_records)
    margin_archived_count = upsert_margin_trading(margin_records) if apply and margin_records else 0

    monthly_revenue_records = archive_monthly_revenue_symbols(symbols, start, end) if monthly_revenue else []
    if not real_capture:
        _write_handoff_records(handoff_output_dir, "monthly_revenue", monthly_revenue_records)
    monthly_revenue_summary = summarize_monthly_revenue(monthly_revenue_records)
    monthly_revenue_archived_count = upsert_monthly_revenue(monthly_revenue_records) if apply and monthly_revenue_records else 0

    valuation_records = archive_valuation_symbols(symbols, start, end) if valuation else []
    if not real_capture:
        _write_handoff_records(handoff_output_dir, "valuation", valuation_records)
    valuation_summary = summarize_valuation(valuation_records)
    valuation_archived_count = upsert_valuation(valuation_records) if apply and valuation_records else 0

    # TWII belongs to the daily-price acquisition segment.  Orthogonal
    # institutional/margin subprocesses must not request it again.
    twii_capture = (
        _real_hsa8_twii_capture(
            start=start,
            end=end,
            output_dir=handoff_output_dir,
            acquisition_run_id=acquisition_run_id,
        )
        if real_capture and daily_price
        else {"status": "not_requested"}
    )

    return {
        "symbols": list(symbols),
        "start": start,
        "end": end,
        "apply": bool(apply),
        "archive": archive_summary,
        "archived_count": archived_count,
        "validation": validation_summary,
        "validation_updated_count": updated_count,
        "corporate_actions": corporate_action_summary,
        "corporate_actions_archived_count": corporate_action_archived_count,
        "institutional_trades": institutional_summary,
        "institutional_trades_archived_count": institutional_archived_count,
        "margin_trading": margin_summary,
        "margin_trading_archived_count": margin_archived_count,
        "monthly_revenue": monthly_revenue_summary,
        "monthly_revenue_archived_count": monthly_revenue_archived_count,
        "valuation": valuation_summary,
        "valuation_archived_count": valuation_archived_count,
        "hsa8_capture": {"daily_price": daily_capture, "institutional": institutional_capture, "margin": margin_capture, "twii": twii_capture},
    }


def _default_start() -> str:
    return (date.today() - timedelta(days=10)).isoformat()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Daily TWStock archive + TWSE validation workflow.")
    parser.add_argument("--symbol", action="append", default=[], help="Taiwan stock code or comma-separated codes. Can be repeated.")
    parser.add_argument("--symbols-file", default="", help="Optional text file with one or comma-separated symbols per line.")
    parser.add_argument("--start", default=_default_start(), help="Start date YYYY-MM-DD. Default: today-10d.")
    parser.add_argument("--end", default=date.today().isoformat(), help="End date YYYY-MM-DD. Default: today.")
    parser.add_argument("--apply", action="store_true", help="Write archive and validation results to PostgreSQL.")
    parser.add_argument("--dry-run", action="store_true", help="Do not write DB. This is the default unless --apply is set.")
    parser.add_argument("--no-validate", action="store_true", help="Skip TWSE official validation step.")
    parser.add_argument("--no-daily-price", action="store_true", help="Skip FinMind daily OHLCV archive step.")
    parser.add_argument("--no-corporate-actions", action="store_true", help="Skip FinMind dividend/ex-right archive step.")
    parser.add_argument("--no-institutional", action="store_true", help="Skip FinMind institutional buy/sell archive step.")
    parser.add_argument("--no-margin", action="store_true", help="Skip FinMind margin purchase/short sale archive step.")
    parser.add_argument("--no-monthly-revenue", action="store_true", help="Skip FinMind monthly revenue archive step.")
    parser.add_argument("--no-valuation", action="store_true", help="Skip FinMind valuation archive step.")
    parser.add_argument("--handoff-output-dir", default="", help="Job-local raw/normalized handoff artifacts; no output when omitted.")
    parser.add_argument("--acquisition-run-id", default="", help="Authoritative same-run id embedded in HSA8 adapter output.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    symbols = parse_symbols(args.symbol)
    symbols.extend(s for s in load_symbols_from_file(args.symbols_file) if s not in symbols)
    if not symbols:
        symbols = list(DEFAULT_SYMBOLS)
    apply_changes = bool(args.apply and not args.dry_run)
    report = run_workflow(
        symbols=symbols,
        start=args.start,
        end=args.end,
        apply=apply_changes,
        validate=not args.no_validate,
        daily_price=not args.no_daily_price,
        corporate_actions=not args.no_corporate_actions,
        institutional=not args.no_institutional,
        margin=not args.no_margin,
        monthly_revenue=not args.no_monthly_revenue,
        valuation=not args.no_valuation,
        handoff_output_dir=args.handoff_output_dir,
        acquisition_run_id=args.acquisition_run_id,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    archive_count = int((report.get("archive") or {}).get("count") or 0)
    validation = report.get("validation") or {}
    mismatched = int(validation.get("mismatched") or 0)
    unchecked = int(validation.get("unchecked") or 0)
    enabled_non_price_counts = [
        int((report.get("corporate_actions") or {}).get("count") or 0) if not args.no_corporate_actions else 0,
        int((report.get("institutional_trades") or {}).get("count") or 0) if not args.no_institutional else 0,
        int((report.get("margin_trading") or {}).get("count") or 0) if not args.no_margin else 0,
        int((report.get("monthly_revenue") or {}).get("count") or 0) if not args.no_monthly_revenue else 0,
        int((report.get("valuation") or {}).get("count") or 0) if not args.no_valuation else 0,
    ]
    if archive_count <= 0 and not any(enabled_non_price_counts):
        return 2
    if not args.no_validate and (mismatched > 0 or unchecked > 0):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
