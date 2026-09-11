#!/usr/bin/env python3
"""Controlled Yahoo-only Scrapling refresh for Option C staged validation.

This script intentionally writes only candidate/staged artifacts. It never
mutates the formal normalized source, formal provider, or latest_signal.json.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import sys
import time
from collections import Counter
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from scrapling.fetchers import Fetcher

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.tw.run_option_c_daily_signal import (  # noqa: E402
    accepted_prediction_universe,
    generate_prediction_for_symbols,
)
from examples.tw.run_option_c_daily_prediction import (  # noqa: E402
    RECORDER_ID,
    CONFIG_PATH,
    MODEL_PATH,
    MARKET,
    BENCHMARK,
    REJECTED_FIELDS,
    score_stats,
)
from scripts.dump_bin import DumpDataAll  # noqa: E402

COLUMNS = ["symbol", "date", "open", "high", "low", "close", "volume", "vwap", "factor"]
REQUIRED_FIELDS = {"open", "high", "low", "close", "volume", "vwap", "factor"}
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
YAHOO_QUOTE_URL = "https://finance.yahoo.com/quote/{ticker}"
DEFAULT_OUTPUT_ROOT = ROOT / "data_tw/experiments/option_c_ops"
DEFAULT_REPORT_PATH = ROOT / "docs/tw_audit/167_option_c_yahoo_scrapling_staged_refresh_report.md"
REPO_ROOT = ROOT.parent
PBPR_PROVIDER_BRIDGE_ARTIFACT_ROOT = REPO_ROOT / "data_tw/experiments/provider_bridge_productionization"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def parse_yahoo_headers(header_values: list[str] | None) -> dict[str, str]:
    headers: dict[str, str] = {}
    for item in header_values or []:
        if ":" in item:
            key, value = item.split(":", 1)
        elif "=" in item:
            key, value = item.split("=", 1)
        else:
            raise ValueError(f"bad yahoo header override, expected Name=Value or Name:Value: {item}")
        key = key.strip()
        value = value.strip()
        if not key or not value:
            raise ValueError(f"bad yahoo header override, empty name/value: {item}")
        headers[key] = value
    return headers


def build_yahoo_access_adapter(args: argparse.Namespace) -> dict[str, Any]:
    headers = parse_yahoo_headers(getattr(args, "yahoo_header", None))
    cookie = (getattr(args, "yahoo_cookie", "") or "").strip()
    crumb = (getattr(args, "yahoo_crumb", "") or "").strip()
    proxy = (getattr(args, "proxy", "") or "").strip()
    if cookie:
        headers["Cookie"] = cookie
    request_kwargs: dict[str, Any] = {}
    if proxy:
        request_kwargs["proxy"] = proxy
    if headers:
        request_kwargs["headers"] = headers
    return {
        "source_family": "Yahoo Finance chart API via Scrapling",
        "source_policy": "Yahoo-only; no yfinance; no FinMind fallback; no mixed provider; no cached prior-asof fill",
        "request_kwargs": request_kwargs,
        "proxy": proxy,
        "proxy_used": bool(proxy),
        "header_names": sorted(headers),
        "cookie_provided": bool(cookie),
        "crumb": crumb,
        "crumb_provided": bool(crumb),
        "quote_page_warmup_enabled": bool(getattr(args, "yahoo_quote_page_warmup", False)),
        "session_warmup_enabled": bool(getattr(args, "yahoo_session_warmup", False)),
        "http_403_backoff_seconds": float(getattr(args, "http_403_backoff_seconds", 0.0) or 0.0),
        "provider_fallback_allowed": False,
    }


def describe_yahoo_access_adapter(adapter: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_family": adapter["source_family"],
        "source_policy": adapter["source_policy"],
        "proxy_used": adapter["proxy_used"],
        "proxy": adapter["proxy"],
        "header_names": adapter["header_names"],
        "cookie_provided": adapter["cookie_provided"],
        "crumb_provided": adapter["crumb_provided"],
        "quote_page_warmup_enabled": adapter["quote_page_warmup_enabled"],
        "session_warmup_enabled": adapter["session_warmup_enabled"],
        "http_403_backoff_seconds": adapter["http_403_backoff_seconds"],
        "provider_fallback_allowed": False,
        "fallback_provider": "",
    }


def classify_yahoo_fetch_failure(status: int | None, error: str | None) -> dict[str, Any]:
    error_text = error or ""
    if status == 403 or "http_status:403" in error_text:
        return {
            "category": "yahoo_http_403_access_blocked",
            "http_status": 403,
            "retry_scope": "same_yahoo_chart_request_only",
            "backoff_advice": "Use reviewer-approved Yahoo header/cookie/crumb/proxy/session controls and slower retry spacing; do not switch providers.",
            "provider_fallback_allowed": False,
            "provider_fallback_attempted": False,
            "fallback_provider": "",
        }
    if status and status >= 400:
        return {
            "category": "yahoo_http_error",
            "http_status": status,
            "retry_scope": "same_yahoo_chart_request_only",
            "backoff_advice": "Retry only within Yahoo chart access controls if reviewer-approved; do not switch providers.",
            "provider_fallback_allowed": False,
            "provider_fallback_attempted": False,
            "fallback_provider": "",
        }
    return {
        "category": "yahoo_fetch_error",
        "http_status": status,
        "retry_scope": "same_yahoo_chart_request_only",
        "backoff_advice": "Inspect Yahoo-only access diagnostics; do not switch providers.",
        "provider_fallback_allowed": False,
        "provider_fallback_attempted": False,
        "fallback_provider": "",
    }


def no_provider_fallback_flags() -> dict[str, Any]:
    return {
        "provider_fallback_allowed": False,
        "provider_fallback_attempted": False,
        "fallback_provider": "",
    }


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def validate_pbpr_material_paths(output_root_arg: str, report_path_arg: str, *, material: bool) -> dict[str, Any]:
    output_input = Path(output_root_arg).expanduser()
    report_input = Path(report_path_arg).expanduser()
    output_resolved = (output_input if output_input.is_absolute() else ROOT / output_input).resolve()
    report_resolved = (report_input if report_input.is_absolute() else ROOT / report_input).resolve()
    required_root = PBPR_PROVIDER_BRIDGE_ARTIFACT_ROOT.resolve()
    guard = {
        "status": "pass",
        "material_pbpr_provider_only": material,
        "required_artifact_root": str(required_root),
        "output_root_input": output_root_arg,
        "report_path_input": report_path_arg,
        "resolved_output_root": str(output_resolved),
        "resolved_report_path": str(report_resolved),
        "output_root_is_absolute_input": output_input.is_absolute(),
        "report_path_is_absolute_input": report_input.is_absolute(),
        "output_root_contained": _is_relative_to(output_resolved, required_root),
        "report_path_contained": _is_relative_to(report_resolved, required_root),
        "local_non_material_mode_required_for_relative_or_external_paths": not material,
    }
    if not material:
        guard["status"] = "skipped_non_material_local_mode"
        return guard
    errors: list[str] = []
    if not output_input.is_absolute():
        errors.append("material_pbpr_output_root_must_be_absolute")
    if not report_input.is_absolute():
        errors.append("material_pbpr_report_path_must_be_absolute")
    if not guard["output_root_contained"]:
        errors.append("material_pbpr_output_root_outside_required_artifact_root")
    if not guard["report_path_contained"]:
        errors.append("material_pbpr_report_path_outside_required_artifact_root")
    if errors:
        guard["status"] = "fail"
        guard["errors"] = errors
        raise ValueError(f"PBPR material path containment failed: {', '.join(errors)}")
    guard["errors"] = []
    return guard


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def to_epoch(day: str, *, end: bool = False) -> int:
    dt = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=UTC)
    if end:
        dt += timedelta(days=1)
    return int(dt.timestamp())


def yahoo_tickers(symbol: str, suffix: str) -> list[str]:
    code = symbol.removeprefix("TW")
    if suffix == "TW":
        return [f"{code}.TW"]
    if suffix == "TWO":
        return [f"{code}.TWO"]
    return [f"{code}.TW", f"{code}.TWO"]


def clean_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        val = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(val) or math.isinf(val):
        return None
    return val


def fetch_chart(
    ticker: str,
    start: str,
    end: str,
    *,
    yahoo_access_adapter: dict[str, Any],
    timeout: float,
    retries: int,
) -> tuple[dict[str, Any] | None, str | None, int | None]:
    params = {
        "period1": str(to_epoch(start)),
        "period2": str(to_epoch(end, end=True)),
        "interval": "1d",
        "events": "history",
        "includeAdjustedClose": "true",
    }
    if yahoo_access_adapter.get("crumb"):
        params["crumb"] = str(yahoo_access_adapter["crumb"])
    kwargs = dict(yahoo_access_adapter.get("request_kwargs") or {})
    http_403_backoff_seconds = float(yahoo_access_adapter.get("http_403_backoff_seconds") or 0.0)
    last_error: str | None = None
    last_status: int | None = None
    for attempt in range(max(retries, 1)):
        try:
            page = Fetcher.get(
                YAHOO_CHART_URL.format(ticker=ticker),
                params=params,
                timeout=timeout,
                retries=1,
                impersonate="chrome",
                **kwargs,
            )
            last_status = int(page.status)
            if page.status >= 400:
                diagnostic = classify_yahoo_fetch_failure(last_status, f"http_status:{page.status}")
                last_error = f"{diagnostic['category']}:http_status:{page.status}:{page.text[:120]}"
                if page.status == 403 and attempt + 1 < max(retries, 1) and http_403_backoff_seconds > 0:
                    time.sleep(http_403_backoff_seconds * (attempt + 1))
                    continue
                return None, last_error, last_status
            payload = page.json()
        except Exception as exc:  # pragma: no cover - network dependent
            last_error = f"{type(exc).__name__}:{exc}"
            if attempt + 1 < max(retries, 1):
                time.sleep(1.0 + attempt)
                continue
            return None, last_error, last_status
        error = payload.get("chart", {}).get("error") if isinstance(payload, dict) else "bad_payload"
        if error:
            return None, f"chart_error:{error}", last_status
        result = (payload.get("chart", {}).get("result") or [None])[0]
        if not result:
            return None, "empty_result", last_status
        return result, None, last_status
    return None, last_error or "unknown_error", last_status


def warmup_yahoo_session(args: argparse.Namespace, symbols: list[str], yahoo_access_adapter: dict[str, Any]) -> dict[str, Any]:
    if not (yahoo_access_adapter.get("quote_page_warmup_enabled") or yahoo_access_adapter.get("session_warmup_enabled")):
        return {"status": "not_run", "reason": "yahoo_session_warmup_not_requested"}
    ticker = yahoo_tickers(symbols[0], args.suffix)[0] if symbols else "2330.TW"
    try:
        page = Fetcher.get(
            YAHOO_QUOTE_URL.format(ticker=ticker),
            timeout=args.timeout,
            retries=1,
            impersonate="chrome",
            **dict(yahoo_access_adapter.get("request_kwargs") or {}),
        )
        status = int(page.status)
        diagnostic = classify_yahoo_fetch_failure(status, f"http_status:{status}") if status >= 400 else {"category": "ok", "http_status": status}
        return {
            "status": "pass" if status < 400 else "fail",
            "ticker": ticker,
            "http_status": status,
            "diagnostic": diagnostic,
            "source_family": "Yahoo quote page via Scrapling warmup for Yahoo chart access only",
            "provider_fallback_attempted": False,
        }
    except Exception as exc:  # pragma: no cover - network dependent
        return {
            "status": "fail",
            "ticker": ticker,
            "error": f"{type(exc).__name__}:{exc}",
            "diagnostic": classify_yahoo_fetch_failure(None, str(exc)),
            "provider_fallback_attempted": False,
        }


def result_to_frame(symbol: str, result: dict[str, Any]) -> pd.DataFrame:
    timestamps = result.get("timestamp") or []
    quote = (result.get("indicators", {}).get("quote") or [{}])[0]
    adj = (result.get("indicators", {}).get("adjclose") or [{}])[0]
    rows: list[dict[str, Any]] = []
    for i, ts in enumerate(timestamps):
        open_raw = clean_float((quote.get("open") or [None] * len(timestamps))[i])
        high_raw = clean_float((quote.get("high") or [None] * len(timestamps))[i])
        low_raw = clean_float((quote.get("low") or [None] * len(timestamps))[i])
        close_raw = clean_float((quote.get("close") or [None] * len(timestamps))[i])
        volume_raw = (quote.get("volume") or [None] * len(timestamps))[i]
        adj_close = clean_float((adj.get("adjclose") or [None] * len(timestamps))[i])
        if None in {open_raw, high_raw, low_raw, close_raw, adj_close}:
            continue
        if min(open_raw, high_raw, low_raw, close_raw, adj_close) <= 0:
            continue
        try:
            volume = int(volume_raw or 0)
        except (TypeError, ValueError):
            volume = 0
        factor = adj_close / close_raw
        if factor <= 0 or math.isnan(factor) or math.isinf(factor):
            continue
        open_adj = open_raw * factor
        high_adj = max(high_raw * factor, open_adj, close_raw * factor)
        low_adj = min(low_raw * factor, open_adj, close_raw * factor)
        close_adj = close_raw * factor
        rows.append(
            {
                "symbol": symbol,
                "date": datetime.fromtimestamp(int(ts), UTC).date().isoformat(),
                "open": open_adj,
                "high": high_adj,
                "low": low_adj,
                "close": close_adj,
                "volume": volume,
                "vwap": (open_adj + high_adj + low_adj + close_adj) / 4,
                "factor": factor,
            }
        )
    df = pd.DataFrame(rows, columns=COLUMNS)
    if not df.empty:
        df = df.drop_duplicates(subset=["symbol", "date"]).sort_values("date")
    return df


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, columns=COLUMNS, quoting=csv.QUOTE_MINIMAL)


def fetch_candidate(args: argparse.Namespace, symbols: list[str], candidate_dir: Path, yahoo_access_adapter: dict[str, Any] | None = None) -> dict[str, Any]:
    success: list[str] = []
    existing_reused: list[str] = []
    empty: list[str] = []
    failed: dict[str, list[dict[str, Any]]] = {}
    suffix_used: dict[str, str] = {}
    status_counts: Counter[str] = Counter()
    diagnostic_counts: Counter[str] = Counter()
    rows_written = 0
    rows_existing_reused = 0
    per_symbol: list[dict[str, Any]] = []
    yahoo_access_adapter = yahoo_access_adapter or build_yahoo_access_adapter(args)
    for index, symbol in enumerate(symbols, start=1):
        out_path = candidate_dir / f"{symbol}.csv"
        attempts: list[dict[str, Any]] = []
        df = pd.DataFrame(columns=COLUMNS)
        used_ticker = ""
        reused_existing = False
        attempted_fetch = False
        if args.skip_existing and out_path.exists() and out_path.stat().st_size > 0:
            try:
                df = pd.read_csv(out_path)
            except Exception as exc:
                diagnostic = {
                    "category": "existing_candidate_read_error",
                    "http_status": None,
                    **no_provider_fallback_flags(),
                }
                attempts.append(
                    {
                        "ticker": "existing",
                        "status": None,
                        "http_status": None,
                        "error": f"{type(exc).__name__}:{exc}",
                        "diagnostic": diagnostic,
                        **no_provider_fallback_flags(),
                    }
                )
                diagnostic_counts["existing_candidate_read_error"] += 1
                df = pd.DataFrame(columns=COLUMNS)
            if not df.empty:
                used_ticker = "existing"
                reused_existing = True
                existing_reused.append(symbol)
                diagnostic_counts["existing_candidate_reused"] += 1
                print(f"[existing] {symbol} rows={len(df)} max={df['date'].max()}", flush=True)
        else:
            attempted_fetch = True
            for ticker in yahoo_tickers(symbol, args.suffix):
                print(f"[fetch {index}/{len(symbols)}] {symbol} ticker={ticker}", flush=True)
                result, error, status = fetch_chart(
                    ticker,
                    args.start,
                    args.asof,
                    yahoo_access_adapter=yahoo_access_adapter,
                    timeout=args.timeout,
                    retries=args.retries,
                )
                status_counts[str(status or "none")] += 1
                if result is None:
                    diagnostic = classify_yahoo_fetch_failure(status, error)
                    diagnostic_counts[str(diagnostic["category"])] += 1
                    attempts.append(
                        {
                            "ticker": ticker,
                            "status": status,
                            "http_status": status,
                            "error": error,
                            "diagnostic": diagnostic,
                            **no_provider_fallback_flags(),
                        }
                    )
                    continue
                df = result_to_frame(symbol, result)
                if not df.empty:
                    used_ticker = ticker
                    break
                diagnostic_counts["no_rows_after_parse"] += 1
                attempts.append(
                    {
                        "ticker": ticker,
                        "status": status,
                        "http_status": status,
                        "error": "no_rows_after_parse",
                        "diagnostic": {"category": "no_rows_after_parse", **no_provider_fallback_flags()},
                        **no_provider_fallback_flags(),
                    }
                )
        if not df.empty:
            if not reused_existing:
                write_csv(out_path, df)
                rows_written += int(len(df))
            else:
                rows_existing_reused += int(len(df))
            success.append(symbol)
            suffix_used[symbol] = used_ticker
            per_symbol.append(
                {
                    "symbol": symbol,
                    "status": "existing_reused" if reused_existing else "success",
                    "ticker": used_ticker,
                    "attempted_fetch": attempted_fetch,
                    "existing_reused": reused_existing,
                    "rows": int(len(df)),
                    "date_min": str(df["date"].min()),
                    "date_max": str(df["date"].max()),
                    "attempts": attempts,
                    **no_provider_fallback_flags(),
                }
            )
            print(f"[ok] {symbol} ticker={used_ticker} rows={len(df)} max={df['date'].max()}", flush=True)
        else:
            empty.append(symbol)
            failed[symbol] = attempts
            per_symbol.append(
                {
                    "symbol": symbol,
                    "status": "empty_or_failed",
                    "ticker": "",
                    "attempted_fetch": attempted_fetch,
                    "existing_reused": False,
                    "rows": 0,
                    "date_min": "",
                    "date_max": "",
                    "attempts": attempts,
                    **no_provider_fallback_flags(),
                }
            )
            print(f"[empty] {symbol} attempts={attempts}", flush=True)
            if not args.continue_on_error:
                break
        if args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)
    unattempted = [symbol for symbol in symbols if symbol not in {item["symbol"] for item in per_symbol}]
    for symbol in unattempted:
        per_symbol.append(
            {
                "symbol": symbol,
                "status": "unattempted",
                "ticker": "",
                "attempted_fetch": False,
                "existing_reused": False,
                "rows": 0,
                "date_min": "",
                "date_max": "",
                "attempts": [],
                **no_provider_fallback_flags(),
            }
        )
    return {
        "status": "pass" if len(success) == len(symbols) and not failed else "fail",
        "source": "Yahoo Finance chart API via Scrapling",
        "source_policy": "Yahoo-only; no yfinance; no FinMind fallback; no mixed provider; no cached prior-asof fill",
        "start": args.start,
        "end": args.asof,
        "yahoo_access_adapter": describe_yahoo_access_adapter(yahoo_access_adapter),
        "proxy_used": bool(yahoo_access_adapter.get("proxy_used")),
        "proxy": yahoo_access_adapter.get("proxy") or "",
        "sleep_seconds": args.sleep_seconds,
        "skip_existing": bool(args.skip_existing),
        "continue_on_error": bool(args.continue_on_error),
        "symbols_expected": len(symbols),
        "symbols_success": len(success),
        "symbols_success_list": success,
        "symbols_existing_reused": existing_reused,
        "symbols_existing_reused_count": len(existing_reused),
        "symbols_empty": empty,
        "symbols_failed": failed,
        "symbols_unattempted": unattempted,
        "symbols_unattempted_count": len(unattempted),
        "rows_written": rows_written,
        "rows_existing_reused": rows_existing_reused,
        "suffix_used": suffix_used,
        "http_status_counts": dict(status_counts),
        "http_diagnostic_counts": dict(diagnostic_counts),
        "per_symbol": per_symbol,
        "per_symbol_sample": per_symbol[:20],
        "adjustment": "yahoo_adjusted_ohlc_factor_adjclose_over_close",
        **no_provider_fallback_flags(),
    }


def build_symbol_failure_ledger(
    symbols: list[str],
    fetch_report: dict[str, Any],
    normalized_validation: dict[str, Any] | None,
    provider_validation: dict[str, Any] | None,
    *,
    skip_existing: bool,
    continue_on_error: bool,
) -> dict[str, Any]:
    per_symbol = list(fetch_report.get("per_symbol") or [])
    success_symbols = list(fetch_report.get("symbols_success_list") or [])
    existing_reused = list(fetch_report.get("symbols_existing_reused") or [])
    failed_map = dict(fetch_report.get("symbols_failed") or {})
    empty_symbols = list(fetch_report.get("symbols_empty") or [])
    unattempted = list(fetch_report.get("symbols_unattempted") or [])
    normalized_validation = normalized_validation or {"status": "not_run"}
    provider_validation = provider_validation or {"status": "not_run"}
    normalized_issue_symbols = sorted((normalized_validation.get("issues_sample") or {}).keys())
    normalized_missing = list(normalized_validation.get("missing_symbols") or [])
    normalized_empty = list(normalized_validation.get("empty_symbols") or [])
    failed_symbols = sorted(set(failed_map) | set(normalized_issue_symbols) | set(normalized_missing) | set(normalized_empty))
    coverage_complete = (
        len(success_symbols) == len(symbols)
        and not empty_symbols
        and not unattempted
        and fetch_report.get("status") == "pass"
        and normalized_validation.get("status") == "pass"
        and provider_validation.get("status") == "pass"
    )
    return {
        "status": "pass" if coverage_complete else "partial_or_failed",
        "created_at": utc_now(),
        "symbols_expected": len(symbols),
        "expected_symbols": symbols,
        "symbols_success": success_symbols,
        "symbols_success_count": len(success_symbols),
        "symbols_existing_reused": existing_reused,
        "symbols_existing_reused_count": len(existing_reused),
        "symbols_failed": failed_symbols,
        "symbols_failed_count": len(failed_symbols),
        "symbols_empty": empty_symbols,
        "symbols_empty_count": len(empty_symbols),
        "symbols_unattempted": unattempted,
        "symbols_unattempted_count": len(unattempted),
        "per_symbol": per_symbol,
        "http_status_counts": dict(fetch_report.get("http_status_counts") or {}),
        "http_diagnostic_counts": dict(fetch_report.get("http_diagnostic_counts") or {}),
        "normalized_validation_status": normalized_validation.get("status"),
        "provider_validation_status": provider_validation.get("status"),
        "resume_safe": True,
        "resume_requires_skip_existing": True,
        "skip_existing": bool(skip_existing),
        "continue_on_error": bool(continue_on_error),
        "partial_candidate_only": not coverage_complete,
        "readiness_ready": False,
        "provider_candidate_readiness_written": False,
        "canonical_bridge_readiness_written": False,
        "pbpr3_authorized": False,
        **no_provider_fallback_flags(),
    }


def build_readiness_gate(symbol_failure_ledger: dict[str, Any] | None) -> dict[str, Any]:
    partial_candidate_only = True
    if symbol_failure_ledger:
        partial_candidate_only = bool(symbol_failure_ledger.get("partial_candidate_only", True))
    return {
        "readiness_ready": False,
        "partial_candidate_only": partial_candidate_only,
        "provider_candidate_readiness_written": False,
        "canonical_bridge_readiness_written": False,
        "provider_only_boundary_allowed": not partial_candidate_only,
        "pbpr3_authorized": False,
        "reason": "partial_candidate_only_or_provider_only_boundary_evidence_not_pbpr3_authorization",
    }


def validate_normalized(candidate_dir: Path, symbols: list[str], asof: str) -> dict[str, Any]:
    summaries: list[dict[str, Any]] = []
    issue_map: dict[str, list[str]] = {}
    missing: list[str] = []
    empty: list[str] = []
    missing_asof: list[str] = []
    date_max_values: list[str] = []
    for symbol in symbols:
        path = candidate_dir / f"{symbol}.csv"
        if not path.exists():
            missing.append(symbol)
            continue
        issues: list[str] = []
        try:
            df = pd.read_csv(path)
        except Exception as exc:
            issue_map[symbol] = [f"read_error:{exc}"]
            continue
        if list(df.columns) != COLUMNS:
            issues.append(f"bad_columns:{list(df.columns)}")
        if df.empty:
            empty.append(symbol)
            issues.append("empty")
        else:
            if (df["symbol"].astype(str).str.upper() != symbol).any():
                issues.append("symbol_mismatch")
            dates = pd.to_datetime(df["date"], errors="coerce")
            if dates.isna().any():
                issues.append("bad_date")
            if not dates.is_monotonic_increasing:
                issues.append("date_not_ascending")
            if dates.duplicated().any():
                issues.append("duplicate_dates")
            if asof not in set(df["date"].astype(str)):
                missing_asof.append(symbol)
            date_max_values.append(str(df["date"].max()))
            for col in ["open", "high", "low", "close", "vwap", "factor"]:
                vals = pd.to_numeric(df[col], errors="coerce") if col in df.columns else pd.Series(dtype=float)
                if vals.isna().any():
                    issues.append(f"{col}_nan_or_non_numeric")
                if (vals <= 0).any():
                    issues.append(f"{col}_non_positive")
                if not pd.Series(vals).map(math.isfinite).all():
                    issues.append(f"{col}_non_finite")
            vol = pd.to_numeric(df.get("volume"), errors="coerce")
            if vol.isna().any():
                issues.append("volume_nan_or_non_numeric")
            if (vol < 0).any():
                issues.append("volume_negative")
            o = pd.to_numeric(df["open"], errors="coerce")
            h = pd.to_numeric(df["high"], errors="coerce")
            l = pd.to_numeric(df["low"], errors="coerce")
            c = pd.to_numeric(df["close"], errors="coerce")
            if (h < pd.concat([o, l, c], axis=1).max(axis=1)).any():
                issues.append("high_below_ohlc")
            if (l > pd.concat([o, h, c], axis=1).min(axis=1)).any():
                issues.append("low_above_ohlc")
        summaries.append({"symbol": symbol, "rows": int(len(df)), "date_min": str(df["date"].min()) if not df.empty else "", "date_max": str(df["date"].max()) if not df.empty else ""})
        if issues:
            issue_map[symbol] = sorted(set(issues))
    errors: list[str] = []
    if missing:
        errors.append("missing_files")
    if empty:
        errors.append("empty_files")
    if issue_map:
        errors.append("normalized_quality_issues")
    if missing_asof:
        errors.append("missing_selected_asof")
    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "data_dir": rel(candidate_dir),
        "symbols_expected": len(symbols),
        "files_found": len(summaries),
        "missing_count": len(missing),
        "empty_count": len(empty),
        "issue_symbol_count": len(issue_map),
        "symbols_with_asof": len(symbols) - len(set(missing_asof) | set(missing)),
        "missing_asof_count": len(missing_asof),
        "date_max_min": min(date_max_values) if date_max_values else None,
        "date_max_max": max(date_max_values) if date_max_values else None,
        "total_rows": sum(item["rows"] for item in summaries),
        "missing_symbols": missing[:200],
        "empty_symbols": empty[:200],
        "missing_asof_symbols": missing_asof[:200],
        "issues_sample": dict(list(issue_map.items())[:100]),
        "per_symbol_sample": summaries[:20],
    }


def rebuild_staged_provider(candidate_dir: Path, staged_provider: Path, max_workers: int) -> dict[str, Any]:
    if staged_provider.exists():
        shutil.rmtree(staged_provider)
    dumper = DumpDataAll(
        data_path=str(candidate_dir),
        qlib_dir=str(staged_provider),
        freq="day",
        max_workers=max_workers,
        date_field_name="date",
        symbol_field_name="symbol",
        include_fields=",".join(COLUMNS[2:]),
    )
    dumper.dump()
    return {"status": "pass", "provider": rel(staged_provider), "max_workers": max_workers}


def validate_provider(provider: Path, symbols: list[str], asof: str) -> dict[str, Any]:
    calendar_path = provider / "calendars/day.txt"
    errors: list[str] = []
    if not calendar_path.exists():
        return {"status": "fail", "errors": ["missing_calendar"], "provider": rel(provider)}
    calendars = [line.strip() for line in calendar_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    counts = {field: 0 for field in sorted(REQUIRED_FIELDS)}
    missing_feature_symbols: list[str] = []
    unexpected: dict[str, list[str]] = {}
    for symbol in symbols:
        feature_dir = provider / "features" / symbol.lower()
        if not feature_dir.exists():
            missing_feature_symbols.append(symbol)
            continue
        fields = {p.name.split(".")[0] for p in feature_dir.glob("*.day.bin")}
        for field in REQUIRED_FIELDS:
            if field in fields:
                counts[field] += 1
        extra = sorted(fields - REQUIRED_FIELDS)
        if extra:
            unexpected[symbol] = extra
    rejected = sorted((set(counts) | {field for values in unexpected.values() for field in values}) & REJECTED_FIELDS)
    if not calendars or max(calendars) < asof:
        errors.append("provider_calendar_before_asof")
    if asof not in calendars:
        errors.append("provider_calendar_missing_asof")
    if missing_feature_symbols:
        errors.append("missing_feature_symbols")
    if unexpected:
        errors.append("unexpected_fields")
    if rejected:
        errors.append("rejected_fields_present")
    if any(v != len(symbols) for v in counts.values()):
        errors.append("expected_field_count_not_150")
    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "provider": rel(provider),
        "calendar_min": min(calendars) if calendars else None,
        "calendar_max": max(calendars) if calendars else None,
        "calendar_count": len(calendars),
        "calendar_has_asof": asof in calendars,
        "active_universe_count": len(symbols),
        "expected_field_counts": counts,
        "missing_feature_symbols": missing_feature_symbols[:200],
        "unexpected_fields_sample": dict(list(unexpected.items())[:20]),
        "rejected_fields_present": rejected,
    }


def staged_model_smoke(provider: Path, asof: str, symbols: list[str], out_dir: Path) -> dict[str, Any]:
    pred = generate_prediction_for_symbols(provider, asof, symbols)
    out_path = out_dir / "staged_prediction.csv"
    pred.reset_index().to_csv(out_path, index=False)
    stats = score_stats(pred["score"])
    finite_share = stats["finite_count"] / stats["count"] if stats["count"] else 0.0
    status = "pass" if int(pred.shape[0]) == len(symbols) and finite_share == 1.0 else "fail"
    return {
        "status": status,
        "provider": rel(provider),
        "asof": asof,
        "symbols": len(symbols),
        "prediction_rows": int(pred.shape[0]),
        "finite_prediction_share": finite_share,
        "score_stats": stats,
        "output": rel(out_path),
        "published_latest_signal": False,
        "formal_provider_mutated": False,
    }


def skipped_model_smoke_provider_only(provider: Path, asof: str, symbols: list[str]) -> dict[str, Any]:
    return {
        "status": "skipped_provider_only",
        "reason": "provider_only_mode_stops_before_staged_model_smoke",
        "provider": rel(provider),
        "asof": asof,
        "symbols": len(symbols),
        "prediction_rows": 0,
        "finite_prediction_share": None,
        "score_stats": {},
        "output": "",
        "published_latest_signal": False,
        "formal_provider_mutated": False,
        "model_inference_input_built": False,
        "score_job_built": False,
        "model_signal_artifact_built": False,
    }


def artifact_manifest(job_dir: Path) -> dict[str, Any]:
    entries = []
    for path in sorted(job_dir.rglob("*")):
        if path.is_file():
            entries.append({"path": rel(path), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return {"status": "pass", "job_dir": rel(job_dir), "entries": entries}


def write_markdown_report(path: Path, payload: dict[str, Any]) -> None:
    fetch = payload.get("fetch", {})
    validation = payload.get("normalized_validation", {})
    provider = payload.get("provider_validation", {})
    smoke = payload.get("model_smoke", {})
    lines = [
        "---",
        f"created_at: {utc_now()}",
        f"status: {payload.get('status')}",
        "scope: option_c_yahoo_scrapling_staged_refresh_report",
        "---",
        "",
        "# Option C Yahoo Scrapling Staged Refresh Report",
        "",
        "## Summary",
        "",
        f"- job_id: `{payload.get('job_id')}`",
        f"- status: `{payload.get('status')}`",
        f"- asof: `{payload.get('asof')}`",
        f"- job_dir: `{payload.get('job_dir')}`",
        f"- universe_count: `{payload.get('universe_count')}`",
        f"- proxy_used: `{fetch.get('proxy_used')}`",
        f"- fetch_status: `{fetch.get('status')}`",
        f"- symbols_success: `{fetch.get('symbols_success')}` / `{fetch.get('symbols_expected')}`",
        f"- normalized_validation: `{validation.get('status')}`",
        f"- provider_validation: `{provider.get('status')}`",
        f"- model_smoke: `{smoke.get('status')}`",
        f"- formal_provider_mutated: `{payload.get('formal_provider_mutated')}`",
        f"- latest_signal_updated: `{payload.get('latest_signal_updated')}`",
        "",
        "## Fetch",
        "",
        "```json",
        json.dumps(fetch, ensure_ascii=False, indent=2, default=str),
        "```",
        "",
        "## Normalized Validation",
        "",
        "```json",
        json.dumps(validation, ensure_ascii=False, indent=2, default=str),
        "```",
        "",
        "## Provider Validation",
        "",
        "```json",
        json.dumps(provider, ensure_ascii=False, indent=2, default=str),
        "```",
        "",
        "## Model Smoke",
        "",
        "```json",
        json.dumps(smoke, ensure_ascii=False, indent=2, default=str),
        "```",
        "",
        "## Explicit Non-Actions",
        "",
        "- No FinMind fallback or mixed-provider fill was used.",
        "- No formal normalized directory was overwritten.",
        "- No formal qlib provider was overwritten.",
        "- No latest_signal.json was updated.",
        "- No paper/live trading, broker connection, orders, target positions, retraining, tuning, recorder switch, or universe expansion was performed.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run controlled Yahoo-only Scrapling refresh into Option C staged artifacts.")
    parser.add_argument("--asof", required=True, help="Selected signal/data asof date, YYYY-MM-DD.")
    parser.add_argument("--start", default="2015-01-01", help="Historical fetch start date.")
    parser.add_argument("--universe", choices=["option_c_accepted_150"], default="option_c_accepted_150")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT), help="Option C ops root or explicit job directory.")
    parser.add_argument("--job-id", default=None)
    parser.add_argument("--proxy", default="http://127.0.0.1:7890")
    parser.add_argument("--yahoo-header", action="append", default=[], help="Explicit Yahoo request header override, Name=Value or Name:Value. Repeatable.")
    parser.add_argument("--yahoo-cookie", default="", help="Explicit Yahoo Cookie header value for a reviewer-approved live rerun.")
    parser.add_argument("--yahoo-crumb", default="", help="Explicit Yahoo crumb query parameter for a reviewer-approved live rerun.")
    parser.add_argument("--yahoo-quote-page-warmup", action="store_true", help="Warm up a Yahoo quote page via Scrapling before chart fetches.")
    parser.add_argument("--yahoo-session-warmup", action="store_true", help="Alias-style session warmup flag recorded with Yahoo-only access diagnostics.")
    parser.add_argument("--http-403-backoff-seconds", type=float, default=0.0, help="Backoff between same-Yahoo chart retries after HTTP 403; never switches provider.")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--suffix", choices=["auto", "TW", "TWO"], default="auto")
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument(
        "--provider-only",
        "--no-model-smoke",
        dest="provider_only",
        action="store_true",
        help="Stop after staged provider rebuild/validation and artifact reports; do not run staged_model_smoke.",
    )
    parser.add_argument(
        "--local-non-material-paths",
        action="store_true",
        help="Allow relative or external paths only for explicit local non-material rehearsal; material PBPR provider-only runs must not set this.",
    )
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    exact_argv = list(sys.argv if argv is None else [str(Path(__file__)), *argv])
    pd.Timestamp(args.asof)  # validates date format
    job_id = args.job_id or f"option_c_yahoo_scrapling_refresh_{args.asof.replace('-', '')}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    material_path_guard_enabled = bool(args.provider_only and not args.local_non_material_paths)
    path_containment_guard = validate_pbpr_material_paths(
        args.output_root,
        args.report_path,
        material=material_path_guard_enabled,
    )
    yahoo_access_adapter = build_yahoo_access_adapter(args)
    output_root = Path(path_containment_guard["resolved_output_root"])
    job_dir = output_root if output_root.name == job_id else output_root / job_id
    candidate_dir = job_dir / "candidate_normalized"
    staged_provider = job_dir / "staged_qlib_bin"
    reports_dir = job_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    candidate_dir.mkdir(parents=True, exist_ok=True)

    symbols = accepted_prediction_universe()
    payload: dict[str, Any] = {
        "job_id": job_id,
        "created_at": utc_now(),
        "status": "started",
        "asof": args.asof,
        "start": args.start,
        "job_dir": rel(job_dir),
        "candidate_dir": rel(candidate_dir),
        "staged_provider": rel(staged_provider),
        "universe": args.universe,
        "universe_count": len(symbols),
        "recorder_id": RECORDER_ID,
        "model_path": rel(MODEL_PATH),
        "config_path": rel(CONFIG_PATH),
        "market": MARKET,
        "benchmark": BENCHMARK,
        "provider_only": bool(args.provider_only),
        "provider_only_mode": bool(args.provider_only),
        "refresh_mode": "provider_only" if args.provider_only else "staged_refresh_with_model_smoke",
        "model_smoke_enabled": not bool(args.provider_only),
        "exact_argv": exact_argv,
        "proxy_value": yahoo_access_adapter.get("proxy") or "",
        "cookie_provided": bool(yahoo_access_adapter.get("cookie_provided")),
        "header_override_provided": bool(getattr(args, "yahoo_header", None)),
        "header_names": list(yahoo_access_adapter.get("header_names") or []),
        "crumb_provided": bool(yahoo_access_adapter.get("crumb_provided")),
        "skip_existing": bool(args.skip_existing),
        "continue_on_error": bool(args.continue_on_error),
        "pbpr3_authorized": False,
        "readiness_ready": False,
        "provider_candidate_readiness_written": False,
        "canonical_bridge_readiness_written": False,
        "path_containment_guard": path_containment_guard,
        "yahoo_access_adapter": describe_yahoo_access_adapter(yahoo_access_adapter),
        "formal_provider_mutated": False,
        "formal_normalized_mutated": False,
        "latest_signal_updated": False,
        "forbidden_actions": {
            "provider_publish_triggered": False,
            "formal_provider_mutated": False,
            "formal_normalized_mutated": False,
            "accepted_latest_switched": False,
            "qlib_refresh_triggered": False,
            "model_scoring_triggered": False,
            "model_inference_input_built": False,
            "score_job_built": False,
            "model_signal_artifact_built": False,
            "readonly_latest_published": False,
            "agent_prompt_built_or_published": False,
            "production_default_changed": False,
            "frontend_default_changed": False,
            "monitor_write_triggered": False,
            "broker_order_quick_trade_triggered": False,
            "order_intent_generated": False,
            "target_position_or_weight_or_quantity_output": False,
            "pbpr3_executed": False,
            "all_false": True,
        },
        "trading": {
            "orders_enabled": False,
            "connects_to_broker": False,
            "paper_orders_enabled": False,
            "live_trading_enabled": False,
            "quick_trade_enabled": False,
            "writes_orders": False,
            "writes_positions": False,
            "research_signal_not_order": True,
        },
        "errors": [],
    }
    status = "failed"
    try:
        payload["yahoo_session_warmup"] = warmup_yahoo_session(args, symbols, yahoo_access_adapter)
        payload["fetch"] = fetch_candidate(args, symbols, candidate_dir, yahoo_access_adapter)
        write_json(reports_dir / "fetch_report.json", payload["fetch"])
        payload["normalized_validation"] = validate_normalized(candidate_dir, symbols, args.asof)
        write_json(reports_dir / "normalized_validation.json", payload["normalized_validation"])
        if payload["fetch"].get("status") != "pass" or payload["normalized_validation"].get("status") != "pass":
            status = "candidate_validation_failed"
            raise RuntimeError("candidate fetch or normalized validation failed")
        payload["provider_rebuild"] = rebuild_staged_provider(candidate_dir, staged_provider, args.max_workers)
        write_json(reports_dir / "provider_rebuild.json", payload["provider_rebuild"])
        payload["provider_validation"] = validate_provider(staged_provider, symbols, args.asof)
        write_json(reports_dir / "provider_validation.json", payload["provider_validation"])
        if payload["provider_validation"].get("status") != "pass":
            status = "staged_provider_validation_failed"
            raise RuntimeError("staged provider validation failed")
        if args.provider_only:
            payload["model_smoke"] = skipped_model_smoke_provider_only(staged_provider, args.asof, symbols)
            payload["provider_only_boundary"] = {
                "status": "stopped_before_staged_model_smoke",
                "stop_after": "fetch_normalized_validation_staged_provider_rebuild_provider_validation",
                "staged_model_smoke_called": False,
                "pbpr3_authorized": False,
                "readiness_ready": False,
                "provider_candidate_readiness_written": False,
                "canonical_bridge_readiness_written": False,
                "model_smoke_status": payload["model_smoke"]["status"],
                "provider_validation_status": payload["provider_validation"].get("status"),
                "target_asof": args.asof,
                "symbol_coverage": {
                    "symbols_expected": payload["normalized_validation"].get("symbols_expected"),
                    "symbols_with_asof": payload["normalized_validation"].get("symbols_with_asof"),
                    "missing_asof_count": payload["normalized_validation"].get("missing_asof_count"),
                    "provider_active_universe_count": payload["provider_validation"].get("active_universe_count"),
                },
                "lineage_paths": {
                    "candidate_dir": rel(candidate_dir),
                    "staged_provider": rel(staged_provider),
                    "reports_dir": rel(reports_dir),
                },
                "forbidden_actions": payload["forbidden_actions"],
            }
            write_json(reports_dir / "model_smoke.json", payload["model_smoke"])
            write_json(reports_dir / "provider_only_boundary.json", payload["provider_only_boundary"])
            status = "provider_only_refresh_complete_waiting_for_review"
        else:
            payload["model_smoke"] = staged_model_smoke(staged_provider, args.asof, symbols, reports_dir)
            write_json(reports_dir / "model_smoke.json", payload["model_smoke"])
            if payload["model_smoke"].get("status") != "pass":
                status = "staged_model_smoke_failed"
                raise RuntimeError("staged model smoke failed")
            status = "staged_refresh_complete_waiting_for_review"
    except Exception as exc:
        payload["errors"].append(str(exc))
        payload.setdefault("provider_rebuild", {"status": "not_run"})
        payload.setdefault("provider_validation", {"status": "not_run"})
        payload.setdefault("model_smoke", {"status": "not_run"})
    finally:
        payload["status"] = status
        payload["completed_at"] = utc_now()
        payload.setdefault(
            "fetch",
            {
                "status": "not_run",
                "symbols_expected": len(symbols),
                "symbols_success": 0,
                "symbols_success_list": [],
                "symbols_existing_reused": [],
                "symbols_existing_reused_count": 0,
                "symbols_empty": [],
                "symbols_failed": {},
                "symbols_unattempted": symbols,
                "symbols_unattempted_count": len(symbols),
                "per_symbol": [
                    {
                        "symbol": symbol,
                        "status": "unattempted",
                        "ticker": "",
                        "attempted_fetch": False,
                        "existing_reused": False,
                        "rows": 0,
                        "date_min": "",
                        "date_max": "",
                        "attempts": [],
                        **no_provider_fallback_flags(),
                    }
                    for symbol in symbols
                ],
                **no_provider_fallback_flags(),
            },
        )
        payload.setdefault("normalized_validation", {"status": "not_run"})
        payload.setdefault("provider_validation", {"status": "not_run"})
        payload["symbol_failure_ledger"] = build_symbol_failure_ledger(
            symbols,
            payload["fetch"],
            payload.get("normalized_validation"),
            payload.get("provider_validation"),
            skip_existing=bool(args.skip_existing),
            continue_on_error=bool(args.continue_on_error),
        )
        write_json(reports_dir / "symbol_failure_ledger.json", payload["symbol_failure_ledger"])
        payload["readiness_gate"] = build_readiness_gate(payload["symbol_failure_ledger"])
        payload["readiness_ready"] = bool(payload["readiness_gate"]["readiness_ready"])
        payload["provider_candidate_readiness_written"] = bool(payload["readiness_gate"]["provider_candidate_readiness_written"])
        payload["canonical_bridge_readiness_written"] = bool(payload["readiness_gate"]["canonical_bridge_readiness_written"])
        write_json(reports_dir / "execution_summary.json", payload)
        payload["artifact_manifest"] = artifact_manifest(job_dir)
        write_json(reports_dir / "artifact_manifest.json", payload["artifact_manifest"])
        report_path = Path(path_containment_guard["resolved_report_path"])
        write_markdown_report(report_path, payload)
        write_markdown_report(reports_dir / "staged_refresh_report.md", payload)
        print(json.dumps({"status": status, "job_id": job_id, "job_dir": rel(job_dir), "report": rel(report_path), "errors": payload["errors"]}, ensure_ascii=False, indent=2))
    success_statuses = {
        "staged_refresh_complete_waiting_for_review",
        "provider_only_refresh_complete_waiting_for_review",
    }
    return 0 if status in success_statuses else 1


if __name__ == "__main__":
    raise SystemExit(main())
