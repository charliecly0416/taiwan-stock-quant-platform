#!/usr/bin/env python3
"""Read-only probe for Taiwan stock intraday data sources.

This script does not write business databases, qlib providers, accepted latest,
orders, broker state, monitor configs, alerts, or target positions. It only
writes probe artifacts under data_tw/ops/intraday_probe by default.
"""
from __future__ import annotations

import argparse
import csv
import contextlib
import importlib.util
import io
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlencode

try:
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SYMBOLS = ["2330", "2317", "2454", "2308", "2412", "2881", "2882", "0050", "0056", "6488"]
FINMIND_ENDPOINT = "https://api.finmindtrade.com/api/v4/data"
FINMIND_DATASETS = ["TaiwanStockKBar", "TaiwanStockPriceMinute", "TaiwanStockPriceTick"]
TW_TIMEZONE = timezone(timedelta(hours=8))


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_local_env() -> None:
    for env_path in (ROOT / ".env", ROOT / "backend" / ".env"):
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not key or key in os.environ:
                continue
            value = value.strip().strip('"').strip("'")
            os.environ[key] = value


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


def parse_symbols(raw_symbols: Iterable[str]) -> list[str]:
    out: list[str] = []
    for raw in raw_symbols:
        for part in str(raw or "").replace("\n", ",").split(","):
            sym = normalize_symbol(part)
            if sym and sym not in out:
                out.append(sym)
    return out


def load_symbols_file(path: str) -> list[str]:
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        return []
    return parse_symbols(line for line in p.read_text(encoding="utf-8").splitlines() if line.strip() and not line.strip().startswith("#"))


def safe_json_dump(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    candidates = [raw, raw.replace("/", "-"), raw.replace("T", " ")]
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
    ]
    for candidate in candidates:
        for fmt in formats:
            try:
                dt = datetime.strptime(candidate[:19], fmt)
                return dt.replace(tzinfo=TW_TIMEZONE)
            except Exception:
                pass
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.astimezone(TW_TIMEZONE) if dt.tzinfo else dt.replace(tzinfo=TW_TIMEZONE)
    except Exception:
        return None


def row_datetime(row: dict[str, Any]) -> datetime | None:
    date = row.get("date") or row.get("Date") or row.get("交易日期")
    time_value = row.get("time") or row.get("Time") or row.get("Trading_time") or row.get("TickType")
    for key in ("datetime", "timestamp", "Time", "time", "Trading_time"):
        dt = parse_dt(row.get(key))
        if dt:
            return dt
    if date and time_value:
        dt = parse_dt(f"{date} {time_value}")
        if dt:
            return dt
    return parse_dt(date)


def as_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(str(value).replace(",", ""))
    except Exception:
        return None


def price_from_row(row: dict[str, Any]) -> float | None:
    for key in ("close", "Close", "price", "Price", "deal_price", "Trading_price"):
        value = as_float(row.get(key))
        if value and value > 0:
            return value
    return None


def has_ohlcv(row: dict[str, Any]) -> bool:
    keys = {str(k).lower() for k in row.keys()}
    return bool({"open", "max", "high"} & keys) and bool({"min", "low"} & keys) and "close" in keys


def aggregate_count(rows: list[dict[str, Any]], minutes: int) -> tuple[int, str | None, str | None]:
    buckets: dict[datetime, int] = {}
    first_dt: datetime | None = None
    last_dt: datetime | None = None
    for row in rows:
        dt = row_datetime(row)
        price = price_from_row(row)
        if not dt or not price:
            continue
        bucket_minute = (dt.minute // minutes) * minutes
        bucket = dt.replace(minute=bucket_minute, second=0, microsecond=0)
        buckets[bucket] = buckets.get(bucket, 0) + 1
        first_dt = min(first_dt, dt) if first_dt else dt
        last_dt = max(last_dt, dt) if last_dt else dt
    return len(buckets), first_dt.isoformat() if first_dt else None, last_dt.isoformat() if last_dt else None


def latency_minutes(latest_bar_time: str | None) -> int | None:
    if not latest_bar_time:
        return None
    try:
        dt = datetime.fromisoformat(latest_bar_time)
        return max(0, int((datetime.now(TW_TIMEZONE) - dt.astimezone(TW_TIMEZONE)).total_seconds() // 60))
    except Exception:
        return None


def local_probe(symbols: list[str], timeframes: list[str]) -> dict[str, Any]:
    patterns = ["intraday", "15m", "60m", "minute", "tick"]
    roots = [ROOT / "data_tw", ROOT / "qlib_pipeline" / "data_tw"]
    matched_files: list[str] = []
    symbol_hits: dict[str, list[str]] = {s: [] for s in symbols}
    for base in roots:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            lower = path.name.lower()
            rel = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
            if any(p in lower for p in patterns):
                matched_files.append(rel)
            for sym in symbols:
                if sym in path.name and any(p in str(path).lower() for p in patterns):
                    symbol_hits[sym].append(rel)
    results = []
    for sym in symbols:
        for tf in timeframes:
            hits = symbol_hits.get(sym) or []
            results.append({
                "symbol": sym,
                "source": "local",
                "timeframe": tf,
                "ok": bool(hits),
                "bar_count": 0,
                "first_bar_time": None,
                "latest_bar_time": None,
                "latency_minutes": None,
                "warnings": [] if hits else ["no_local_intraday_files_found"],
                "error": None,
                "matched_files_sample": hits[:5],
            })
    return {"source": "local", "ok": any(r["ok"] for r in results), "matched_files_sample": matched_files[:50], "results": results}


def http_get_json(url: str, params: dict[str, Any], timeout: int) -> tuple[int | None, Any, str | None]:
    if requests is None:
        return None, None, "requests_not_available"
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        try:
            data = resp.json()
        except Exception:
            data = {"text_head": resp.text[:300]}
        return resp.status_code, data, None
    except Exception as exc:
        return None, None, f"{type(exc).__name__}: {exc}"


def finmind_probe(symbols: list[str], timeframes: list[str], start_date: str, end_date: str, timeout: int, sleep_seconds: float) -> dict[str, Any]:
    token = (os.getenv("FINMIND_TOKEN") or os.getenv("FINMIND_API_TOKEN") or os.getenv("TW_INTRADAY_SOURCE_TOKEN") or "").strip()
    results: list[dict[str, Any]] = []
    dataset_summaries: list[dict[str, Any]] = []
    for dataset in FINMIND_DATASETS:
        dataset_ok = False
        dataset_statuses: list[Any] = []
        for sym in symbols:
            params = {"dataset": dataset, "data_id": sym, "start_date": start_date, "end_date": end_date}
            if token:
                params["token"] = token
            status, data, error = http_get_json(FINMIND_ENDPOINT, params, timeout)
            rows = data.get("data") if isinstance(data, dict) else None
            rows = rows if isinstance(rows, list) else []
            api_status = data.get("status") if isinstance(data, dict) else status
            msg = data.get("msg") or data.get("message") if isinstance(data, dict) else None
            dataset_statuses.append(api_status)
            dataset_ok = dataset_ok or bool(rows)
            sample = rows[0] if rows else {}
            raw_granularity = "ohlcv" if isinstance(sample, dict) and has_ohlcv(sample) else "tick_or_quote" if rows else "unknown"
            for tf in timeframes:
                minutes = 15 if tf == "15m" else 60 if tf == "60m" else 15
                bar_count, first_time, latest_time = aggregate_count(rows, minutes)
                warnings = []
                if not token:
                    warnings.append("token_not_configured")
                if not rows:
                    warnings.append("no_intraday_rows_returned")
                if raw_granularity == "unknown":
                    warnings.append("no_intraday_dataset_confirmed")
                if rows and raw_granularity == "tick_or_quote":
                    warnings.append("requires_local_ohlcv_aggregation")
                results.append({
                    "symbol": sym,
                    "source": "finmind",
                    "dataset": dataset,
                    "timeframe": tf,
                    "ok": bool(bar_count > 0),
                    "raw_row_count": len(rows),
                    "bar_count": bar_count,
                    "first_bar_time": first_time,
                    "latest_bar_time": latest_time,
                    "latency_minutes": latency_minutes(latest_time),
                    "raw_granularity": raw_granularity,
                    "fields_sample": list(sample.keys())[:30] if isinstance(sample, dict) else [],
                    "warnings": warnings,
                    "http_status": status,
                    "api_status": api_status,
                    "error": error or msg,
                })
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
        dataset_summaries.append({"dataset": dataset, "ok": dataset_ok, "statuses_sample": dataset_statuses[:20]})
    return {"source": "finmind", "has_token": bool(token), "datasets": dataset_summaries, "results": results}


def classify_yfinance_attempt(row_count: int, stderr_text: str, error: str | None) -> str:
    combined = f"{stderr_text or ''}\n{error or ''}"
    if row_count > 0:
        return "ok"
    if "YFRateLimitError" in combined or "Rate limited" in combined or "Too Many Requests" in combined:
        return "rate_limited"
    if error:
        return "exception"
    if stderr_text.strip():
        return "empty_after_provider_warning"
    return "empty"


def yahoo_probe(symbols: list[str], timeframes: list[str], lookback_days: int, timeout: int) -> dict[str, Any]:
    if importlib.util.find_spec("yfinance") is None:
        results = []
        for sym in symbols:
            for tf in timeframes:
                results.append({
                    "symbol": sym,
                    "source": "yahoo_scrapling",
                    "provider": "yfinance",
                    "provider_symbol": None,
                    "provider_symbol_candidates": [f"{sym}.TW", f"{sym}.TWO"],
                    "provider_attempts": [],
                    "provider_status": "exception",
                    "timeframe": tf,
                    "ok": False,
                    "bar_count": 0,
                    "first_bar_time": None,
                    "latest_bar_time": None,
                    "latency_minutes": None,
                    "fields_sample": [],
                    "warnings": ["yfinance_not_installed"],
                    "error": "yfinance_not_installed",
                })
        return {"source": "yahoo_scrapling", "ok": False, "error": "yfinance_not_installed", "results": results}
    import yfinance as yf  # type: ignore
    results: list[dict[str, Any]] = []
    interval_map = {"15m": "15m", "60m": "60m"}
    for sym in symbols:
        yf_candidates = [f"{sym}.TW", f"{sym}.TWO"]
        for tf in timeframes:
            rows_count = 0
            first_time = None
            latest_time = None
            error = None
            used_symbol = None
            fields: list[str] = []
            attempts: list[dict[str, Any]] = []
            for yf_symbol in yf_candidates:
                attempt_error = None
                stderr_text = ""
                row_count = 0
                try:
                    stderr_buf = io.StringIO()
                    with contextlib.redirect_stderr(stderr_buf):
                        df = yf.download(
                            yf_symbol,
                            period=f"{max(1, lookback_days)}d",
                            interval=interval_map.get(tf, "15m"),
                            progress=False,
                            timeout=timeout,
                            auto_adjust=False,
                        )
                    stderr_text = stderr_buf.getvalue()
                    if df is not None and not df.empty:
                        row_count = int(len(df))
                        rows_count = row_count
                        idx = df.index
                        first_time = idx[0].to_pydatetime().isoformat() if len(idx) else None
                        latest_time = idx[-1].to_pydatetime().isoformat() if len(idx) else None
                        fields = [str(c) for c in df.columns]
                        used_symbol = yf_symbol
                except Exception as exc:
                    attempt_error = f"{type(exc).__name__}: {exc}"
                    error = attempt_error
                status = classify_yfinance_attempt(row_count, stderr_text, attempt_error)
                attempts.append({
                    "provider_symbol": yf_symbol,
                    "status": status,
                    "row_count": row_count,
                    "error": attempt_error,
                    "stderr_tail": stderr_text[-500:] if stderr_text else "",
                })
                if row_count > 0:
                    break
            provider_status = "ok" if rows_count > 0 else (
                "rate_limited" if any(a["status"] == "rate_limited" for a in attempts) else
                "exception" if any(a["status"] == "exception" for a in attempts) else
                "empty_after_provider_warning" if any(a["status"] == "empty_after_provider_warning" for a in attempts) else
                "empty"
            )
            warnings = [] if rows_count else ["no_intraday_rows_returned"]
            if provider_status != "ok":
                warnings.append(provider_status)
            if used_symbol and used_symbol.endswith(".TW") and sym.startswith("6"):
                warnings.append("tpex_symbol_may_require_two_suffix")
            results.append({
                "symbol": sym,
                "source": "yahoo_scrapling",
                "provider": "yfinance",
                "provider_symbol": used_symbol,
                "provider_symbol_candidates": yf_candidates,
                "provider_attempts": attempts,
                "provider_status": provider_status,
                "attempts_count": len(attempts),
                "timeframe": tf,
                "ok": rows_count > 0,
                "bar_count": rows_count,
                "first_bar_time": first_time,
                "latest_bar_time": latest_time,
                "latency_minutes": latency_minutes(latest_time),
                "fields_sample": fields[:30],
                "warnings": warnings,
                "error": error,
            })
    return {"source": "yahoo_scrapling", "ok": any(r["ok"] for r in results), "results": results}


def summarize_results(run_id: str, started_at: str, finished_at: str, symbols: list[str], sources: list[dict[str, Any]]) -> dict[str, Any]:
    all_results = [r for source in sources for r in source.get("results", [])]
    usable_sources = []
    for source in sources:
        source_name = source.get("source")
        results = source.get("results", [])
        if any(r.get("ok") for r in results):
            usable_sources.append(source_name)
    coverage_by_source = {}
    for source in sources:
        name = source.get("source")
        results = source.get("results", [])
        ok_symbols = {r.get("symbol") for r in results if r.get("ok")}
        coverage_by_source[name] = {
            "ok_symbol_count": len(ok_symbols),
            "coverage": round(len(ok_symbols) / max(1, len(symbols)), 4),
        }
    recommended_source = None
    for preferred in ("finmind", "yahoo_scrapling", "local"):
        cov = coverage_by_source.get(preferred, {}).get("coverage", 0)
        if cov >= 0.8:
            recommended_source = preferred
            break
    return {
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "symbols_requested": len(symbols),
        "sources_checked": [s.get("source") for s in sources],
        "usable_source_count": len(usable_sources),
        "usable_sources": usable_sources,
        "recommended_source": recommended_source,
        "coverage_by_source": coverage_by_source,
        "can_continue_to_step2": recommended_source is not None,
        "orders_enabled": False,
        "connects_to_broker": False,
        "writes_business_db": False,
        "result_count": len(all_results),
    }



def build_provider_diagnostics(sources: list[dict[str, Any]]) -> dict[str, Any]:
    diagnostics: dict[str, Any] = {
        "orders_enabled": False,
        "connects_to_broker": False,
        "writes_business_db": False,
        "providers": {},
    }
    for source in sources:
        name = source.get("source")
        results = source.get("results", [])
        provider: dict[str, Any] = {
            "result_count": len(results),
            "ok_count": sum(1 for r in results if r.get("ok")),
            "statuses": {},
            "errors_sample": [],
        }
        if name == "finmind":
            provider["has_token"] = bool(source.get("has_token"))
            provider["datasets"] = source.get("datasets", [])
            for r in results:
                status = str(r.get("api_status") or r.get("http_status") or "unknown")
                provider["statuses"][status] = provider["statuses"].get(status, 0) + 1
                if r.get("error") and len(provider["errors_sample"]) < 10:
                    provider["errors_sample"].append({
                        "dataset": r.get("dataset"),
                        "symbol": r.get("symbol"),
                        "error": r.get("error"),
                    })
        elif name == "yahoo_scrapling":
            for r in results:
                status = str(r.get("provider_status") or "unknown")
                provider["statuses"][status] = provider["statuses"].get(status, 0) + 1
                for attempt in r.get("provider_attempts") or []:
                    if attempt.get("status") != "ok" and len(provider["errors_sample"]) < 10:
                        provider["errors_sample"].append({
                            "symbol": r.get("symbol"),
                            "timeframe": r.get("timeframe"),
                            "provider_symbol": attempt.get("provider_symbol"),
                            "status": attempt.get("status"),
                            "error": attempt.get("error"),
                            "stderr_tail": attempt.get("stderr_tail"),
                        })
        else:
            for r in results:
                status = "ok" if r.get("ok") else "empty"
                provider["statuses"][status] = provider["statuses"].get(status, 0) + 1
        diagnostics["providers"][name] = provider
    return diagnostics

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only probe for TW stock intraday data sources.")
    parser.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS))
    parser.add_argument("--symbols-file", default="")
    parser.add_argument("--lookback-days", type=int, default=5)
    parser.add_argument("--timeframes", default="15m,60m")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--max-symbols", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--sleep-seconds", type=float, default=0.2)
    parser.add_argument("--skip-finmind", action="store_true")
    parser.add_argument("--skip-yahoo", action="store_true")
    args = parser.parse_args(argv)

    load_local_env()
    started_at = utc_now()
    run_id = f"intraday_probe_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    output_dir = Path(args.output_dir) if args.output_dir else ROOT / "data_tw" / "ops" / "intraday_probe" / run_id
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir

    symbols = parse_symbols([args.symbols])
    symbols.extend(sym for sym in load_symbols_file(args.symbols_file) if sym not in symbols)
    symbols = (symbols or DEFAULT_SYMBOLS)[: max(1, args.max_symbols)]
    timeframes = [tf.strip() for tf in args.timeframes.split(",") if tf.strip()]
    end_date = datetime.now(TW_TIMEZONE).date().isoformat()
    start_date = (datetime.now(TW_TIMEZONE).date() - timedelta(days=max(1, args.lookback_days))).isoformat()

    sources: list[dict[str, Any]] = []
    sources.append(local_probe(symbols, timeframes))
    if not args.skip_finmind:
        sources.append(finmind_probe(symbols, timeframes, start_date, end_date, args.timeout, args.sleep_seconds))
    if not args.skip_yahoo:
        sources.append(yahoo_probe(symbols, timeframes, args.lookback_days, args.timeout))

    finished_at = utc_now()
    summary = summarize_results(run_id, started_at, finished_at, symbols, sources)
    symbols_rows = [r for source in sources for r in source.get("results", [])]
    provider_diagnostics = build_provider_diagnostics(sources)
    safe_json_dump(output_dir / "summary.json", summary)
    safe_json_dump(output_dir / "sources.json", sources)
    safe_json_dump(output_dir / "symbols.json", symbols_rows)
    safe_json_dump(output_dir / "provider_diagnostics.json", provider_diagnostics)
    print(json.dumps({"summary": summary, "output_dir": str(output_dir)}, ensure_ascii=False, indent=2))
    return 0 if summary["can_continue_to_step2"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
