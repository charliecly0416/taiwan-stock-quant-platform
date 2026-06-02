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
DEFAULT_OUTPUT_ROOT = ROOT / "data_tw/experiments/option_c_ops"
DEFAULT_REPORT_PATH = ROOT / "docs/tw_audit/167_option_c_yahoo_scrapling_staged_refresh_report.md"


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
    proxy: str | None,
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
    kwargs: dict[str, Any] = {"proxy": proxy} if proxy else {}
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
                return None, f"http_status:{page.status}:{page.text[:120]}", last_status
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


def fetch_candidate(args: argparse.Namespace, symbols: list[str], candidate_dir: Path) -> dict[str, Any]:
    success: list[str] = []
    empty: list[str] = []
    failed: dict[str, list[dict[str, Any]]] = {}
    suffix_used: dict[str, str] = {}
    status_counts: Counter[str] = Counter()
    rows_written = 0
    per_symbol: list[dict[str, Any]] = []
    proxy = args.proxy.strip() or None
    for index, symbol in enumerate(symbols, start=1):
        out_path = candidate_dir / f"{symbol}.csv"
        attempts: list[dict[str, Any]] = []
        df = pd.DataFrame(columns=COLUMNS)
        used_ticker = ""
        if args.skip_existing and out_path.exists() and out_path.stat().st_size > 0:
            df = pd.read_csv(out_path)
            used_ticker = "existing"
        else:
            for ticker in yahoo_tickers(symbol, args.suffix):
                print(f"[fetch {index}/{len(symbols)}] {symbol} ticker={ticker}", flush=True)
                result, error, status = fetch_chart(ticker, args.start, args.asof, proxy=proxy, timeout=args.timeout, retries=args.retries)
                status_counts[str(status or "none")] += 1
                if result is None:
                    attempts.append({"ticker": ticker, "status": status, "error": error})
                    continue
                df = result_to_frame(symbol, result)
                if not df.empty:
                    used_ticker = ticker
                    break
                attempts.append({"ticker": ticker, "status": status, "error": "no_rows_after_parse"})
        if not df.empty:
            write_csv(out_path, df)
            success.append(symbol)
            suffix_used[symbol] = used_ticker
            rows_written += int(len(df))
            per_symbol.append({"symbol": symbol, "ticker": used_ticker, "rows": int(len(df)), "date_min": str(df["date"].min()), "date_max": str(df["date"].max())})
            print(f"[ok] {symbol} ticker={used_ticker} rows={len(df)} max={df['date'].max()}", flush=True)
        else:
            empty.append(symbol)
            failed[symbol] = attempts
            print(f"[empty] {symbol} attempts={attempts}", flush=True)
            if not args.continue_on_error:
                break
        if args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)
    return {
        "status": "pass" if len(success) == len(symbols) and not failed else "fail",
        "source": "Yahoo Finance chart API via Scrapling",
        "source_policy": "Yahoo-only; no yfinance; no FinMind fallback; no mixed provider",
        "start": args.start,
        "end": args.asof,
        "proxy_used": bool(proxy),
        "proxy": proxy or "",
        "sleep_seconds": args.sleep_seconds,
        "symbols_expected": len(symbols),
        "symbols_success": len(success),
        "symbols_empty": empty,
        "symbols_failed": failed,
        "rows_written": rows_written,
        "suffix_used": suffix_used,
        "http_status_counts": dict(status_counts),
        "per_symbol_sample": per_symbol[:20],
        "adjustment": "yahoo_adjusted_ohlc_factor_adjclose_over_close",
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
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--suffix", choices=["auto", "TW", "TWO"], default="auto")
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    pd.Timestamp(args.asof)  # validates date format
    job_id = args.job_id or f"option_c_yahoo_scrapling_refresh_{args.asof.replace('-', '')}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    output_root = Path(args.output_root)
    if not output_root.is_absolute():
        output_root = ROOT / output_root
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
        "formal_provider_mutated": False,
        "formal_normalized_mutated": False,
        "latest_signal_updated": False,
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
        payload["fetch"] = fetch_candidate(args, symbols, candidate_dir)
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
        write_json(reports_dir / "execution_summary.json", payload)
        payload["artifact_manifest"] = artifact_manifest(job_dir)
        write_json(reports_dir / "artifact_manifest.json", payload["artifact_manifest"])
        report_path = Path(args.report_path)
        if not report_path.is_absolute():
            report_path = ROOT / report_path
        write_markdown_report(report_path, payload)
        write_markdown_report(reports_dir / "staged_refresh_report.md", payload)
        print(json.dumps({"status": status, "job_id": job_id, "job_dir": rel(job_dir), "report": rel(report_path), "errors": payload["errors"]}, ensure_ascii=False, indent=2))
    return 0 if status == "staged_refresh_complete_waiting_for_review" else 1


if __name__ == "__main__":
    raise SystemExit(main())
