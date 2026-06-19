#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
ALLOWED_HOSTS = {"query1.finance.yahoo.com", "api.finmindtrade.com"}
DEFAULT_SYMBOLS_FILE = ROOT / "data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260617_20260617T103001Z/finmind_symbols.txt"
OUT_ROOT = ROOT / "data_tw/artifacts/provider_staging_external"


def now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def normalize_symbol(raw: str) -> str:
    text = str(raw or "").strip().upper()
    if not text:
        return ""
    if text.startswith("TW") and text[2:].isdigit():
        return text
    if text.isdigit():
        return f"TW{text}"
    return text


def query_symbol(symbol: str) -> str:
    normalized = normalize_symbol(symbol)
    return normalized[2:] if normalized.startswith("TW") else normalized


def load_symbols(args: argparse.Namespace) -> list[str]:
    symbols: list[str] = []
    for raw in args.symbol or []:
        for part in str(raw).replace("\n", ",").split(","):
            symbol = normalize_symbol(part)
            if symbol and symbol not in symbols:
                symbols.append(symbol)
    path = Path(args.symbols_file) if args.symbols_file else DEFAULT_SYMBOLS_FILE
    if not symbols and path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            symbol = normalize_symbol(line.split("#", 1)[0])
            if symbol and symbol not in symbols:
                symbols.append(symbol)
    if not symbols:
        symbols = ["TW2330", "TW2317", "TW2454", "TW2303", "TW2881"]
    if args.max_symbols and args.max_symbols > 0:
        symbols = symbols[: args.max_symbols]
    return symbols


def clean_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(out) or math.isinf(out) else out


def clean_int(value: Any) -> int:
    out = clean_float(value)
    return int(round(out or 0))


def to_epoch(day: str, end: bool = False) -> int:
    dt = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=UTC)
    if end:
        dt += timedelta(days=1)
    return int(dt.timestamp())


def audit_request(audit: list[dict[str, Any]], *, provider: str, source_id: str, url: str, params: dict[str, Any], timeout: float, retries: int, sleep: float) -> tuple[dict[str, Any] | None, str]:
    host = urlparse(url).hostname or ""
    entry: dict[str, Any] = {
        "provider": provider,
        "source_id": source_id,
        "method": "GET",
        "url": url,
        "host": host,
        "allowed_host": host in ALLOWED_HOSTS,
        "params_redacted": {k: ("***" if k == "token" else v) for k, v in params.items()},
        "attempts": [],
    }
    payload: dict[str, Any] | None = None
    error = ""
    for attempt in range(1, max(1, retries) + 1):
        started = now()
        try:
            response = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": "Mozilla/5.0 provider-staging-readonly"})
            status = response.status_code
            attempt_row = {"attempt": attempt, "started_at": started, "http_status": status, "ok": 200 <= status < 400}
            entry["attempts"].append(attempt_row)
            if not (200 <= status < 400):
                error = f"http_status:{status}:{response.text[:160]}"
            else:
                payload = response.json()
                error = ""
                break
        except Exception as exc:
            error = f"{type(exc).__name__}:{exc}"
            entry["attempts"].append({"attempt": attempt, "started_at": started, "http_status": None, "ok": False, "error": error})
        if attempt < max(1, retries) and sleep > 0:
            delay = sleep * attempt
            entry.setdefault("backoff_seconds", []).append(delay)
            time.sleep(delay)
    entry["ok"] = payload is not None and not error and entry["allowed_host"] is True
    entry["error"] = error
    audit.append(entry)
    return payload, error


def yahoo_tickers(symbol: str) -> list[str]:
    code = query_symbol(symbol)
    return [f"{code}.TW", f"{code}.TWO"]


def fetch_yahoo(symbols: list[str], args: argparse.Namespace, out_dir: Path, audit: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    failures: dict[str, Any] = {}
    suffix_used: dict[str, str] = {}
    for symbol in symbols:
        symbol_rows: list[dict[str, Any]] = []
        attempts: list[dict[str, Any]] = []
        for ticker in yahoo_tickers(symbol):
            params = {"period1": str(to_epoch(args.start)), "period2": str(to_epoch(args.end, end=True)), "interval": "1d", "events": "history", "includeAdjustedClose": "true"}
            payload, error = audit_request(audit, provider="Yahoo", source_id="yahoo_daily_price", url=YAHOO_CHART_URL.format(ticker=ticker), params=params, timeout=args.timeout, retries=args.retries, sleep=args.retry_sleep_seconds)
            attempts.append({"ticker": ticker, "error": error})
            result = (((payload or {}).get("chart") or {}).get("result") or [None])[0]
            chart_error = ((payload or {}).get("chart") or {}).get("error")
            if chart_error or not result:
                continue
            timestamps = result.get("timestamp") or []
            quote = (result.get("indicators", {}).get("quote") or [{}])[0]
            adj = (result.get("indicators", {}).get("adjclose") or [{}])[0]
            for idx, ts in enumerate(timestamps):
                open_raw = clean_float((quote.get("open") or [None] * len(timestamps))[idx])
                high_raw = clean_float((quote.get("high") or [None] * len(timestamps))[idx])
                low_raw = clean_float((quote.get("low") or [None] * len(timestamps))[idx])
                close_raw = clean_float((quote.get("close") or [None] * len(timestamps))[idx])
                adj_close = clean_float((adj.get("adjclose") or [None] * len(timestamps))[idx])
                if None in {open_raw, high_raw, low_raw, close_raw, adj_close} or min(open_raw, high_raw, low_raw, close_raw, adj_close) <= 0:
                    continue
                factor = adj_close / close_raw
                volume = clean_int((quote.get("volume") or [0] * len(timestamps))[idx])
                day = datetime.fromtimestamp(int(ts), UTC).date().isoformat()
                symbol_rows.append({"date": day, "instrument": symbol, "open": open_raw * factor, "high": high_raw * factor, "low": low_raw * factor, "close": close_raw * factor, "volume": volume, "adjusted_close": adj_close, "factor": factor, "ticker": ticker})
            if symbol_rows:
                suffix_used[symbol] = ticker
                break
        if symbol_rows:
            rows.extend(symbol_rows)
        else:
            failures[symbol] = attempts
        if args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)
    rows.sort(key=lambda item: (item["instrument"], item["date"]))
    write_csv(out_dir / "yahoo" / "daily_price.csv", rows, ["date", "instrument", "open", "high", "low", "close", "volume", "adjusted_close", "factor", "ticker"])
    latest = max([str(r["date"]) for r in rows], default="")
    symbols_with_rows = sorted({str(r["instrument"]) for r in rows})
    return {"source_id": "yahoo_daily_price", "provider": "Yahoo", "rows": len(rows), "latest": latest, "symbols_success": len(symbols_with_rows), "symbols_requested": len(symbols), "symbols_failed": failures, "suffix_used": suffix_used, "fallback_used": False, "fallback_reason": "", "output": rel(out_dir / "yahoo" / "daily_price.csv")}


def fetch_finmind_dataset(symbols: list[str], args: argparse.Namespace, out_dir: Path, audit: list[dict[str, Any]], *, dataset: str, source_id: str, subdir: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw_rows: list[dict[str, Any]] = []
    failures: dict[str, Any] = {}
    token = os.getenv("FINMIND_TOKEN") or os.getenv("FINMIND_API_TOKEN")
    for symbol in symbols:
        params: dict[str, Any] = {"dataset": dataset, "data_id": query_symbol(symbol), "start_date": args.start, "end_date": args.end}
        if token:
            params["token"] = token.strip()
        payload, error = audit_request(audit, provider="FinMind", source_id=source_id, url=FINMIND_URL, params=params, timeout=args.timeout, retries=args.retries, sleep=args.retry_sleep_seconds)
        status = (payload or {}).get("status")
        data = (payload or {}).get("data")
        if error or status not in (None, 200, "200", True) or not isinstance(data, list):
            failures[symbol] = {"error": error or (payload or {}).get("msg") or "bad_payload", "finmind_status": status}
        else:
            for row in data:
                if isinstance(row, dict):
                    raw_rows.append({**row, "instrument": symbol})
        if args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)
    raw_path = out_dir / subdir / "raw_rows.json"
    write_json(raw_path, {"dataset": dataset, "rows": raw_rows})
    latest = max([str(r.get("date") or "") for r in raw_rows], default="")
    return raw_rows, {"source_id": source_id, "provider": "FinMind", "dataset": dataset, "raw_rows": len(raw_rows), "latest": latest, "symbols_requested": len(symbols), "symbols_success": len({normalize_symbol(r.get("instrument", "")) for r in raw_rows}), "symbols_failed": failures, "raw_output": rel(raw_path)}


def materialize_finmind_daily(raw_rows: list[dict[str, Any]], out_dir: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for item in raw_rows:
        open_ = clean_float(item.get("open")); high = clean_float(item.get("max")); low = clean_float(item.get("min")); close = clean_float(item.get("close")); volume = clean_int(item.get("Trading_Volume"))
        if None in {open_, high, low, close} or min(open_, high, low, close) <= 0:
            continue
        rows.append({"date": item.get("date"), "instrument": normalize_symbol(item.get("instrument") or item.get("stock_id")), "open": open_, "high": max(high, open_, close), "low": min(low, open_, close), "close": close, "volume": max(volume, 0)})
    path = out_dir / "finmind" / "daily_price" / "daily_price.csv"
    write_csv(path, rows, ["date", "instrument", "open", "high", "low", "close", "volume"])
    return {"rows": len(rows), "latest": max([str(r["date"]) for r in rows], default=""), "output": rel(path)}


def materialize_institutional(raw_rows: list[dict[str, Any]], out_dir: Path) -> dict[str, Any]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    category_map = {"Foreign_Investor": "foreign", "Foreign_Dealer_Self": "foreign", "Investment_Trust": "investment_trust", "Dealer_self": "dealer", "Dealer_Hedging": "dealer"}
    for row in raw_rows:
        symbol = normalize_symbol(row.get("instrument") or row.get("stock_id")); day = str(row.get("date") or "")
        if not symbol or not day:
            continue
        bucket = grouped.setdefault((symbol, day), {"instrument": symbol, "date": day, "foreign_net_buy": 0, "investment_trust_net_buy": 0, "dealer_net_buy": 0})
        category = category_map.get(str(row.get("name") or ""))
        if category:
            bucket[f"{category}_net_buy"] += clean_int(row.get("buy")) - clean_int(row.get("sell"))
    rows = []
    for bucket in grouped.values():
        total = bucket["foreign_net_buy"] + bucket["investment_trust_net_buy"] + bucket["dealer_net_buy"]
        rows.append({**bucket, "institutional_total_net_buy": total, "rolling_sums": "external_raw_pending_feature_builder", "streak": "external_raw_pending_feature_builder", "missing_flag": False, "delay_flag": False})
    rows.sort(key=lambda x: (x["instrument"], x["date"]))
    path = out_dir / "finmind" / "institutional_flow" / "institutional_flow.csv"
    write_csv(path, rows, ["date", "instrument", "foreign_net_buy", "investment_trust_net_buy", "dealer_net_buy", "institutional_total_net_buy", "rolling_sums", "streak", "missing_flag", "delay_flag"])
    return {"rows": len(rows), "latest": max([str(r["date"]) for r in rows], default=""), "output": rel(path)}


def materialize_margin(raw_rows: list[dict[str, Any]], out_dir: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for row in raw_rows:
        symbol = normalize_symbol(row.get("instrument") or row.get("stock_id")); day = str(row.get("date") or "")
        if not symbol or not day:
            continue
        margin_balance = clean_int(row.get("MarginPurchaseTodayBalance")); margin_yesterday = clean_int(row.get("MarginPurchaseYesterdayBalance")); short_balance = clean_int(row.get("ShortSaleTodayBalance")); short_yesterday = clean_int(row.get("ShortSaleYesterdayBalance"))
        rows.append({"date": day, "instrument": symbol, "margin_balance": margin_balance, "margin_balance_change": margin_balance - margin_yesterday, "short_balance": short_balance, "short_balance_change": short_balance - short_yesterday, "rolling_sums": "external_raw_pending_feature_builder", "direction_proxy": "external_raw", "divergence_proxy": "external_raw", "missing_flag": False, "delay_flag": False})
    rows.sort(key=lambda x: (x["instrument"], x["date"]))
    path = out_dir / "finmind" / "margin_short" / "margin_short.csv"
    write_csv(path, rows, ["date", "instrument", "margin_balance", "margin_balance_change", "short_balance", "short_balance_change", "rolling_sums", "direction_proxy", "divergence_proxy", "missing_flag", "delay_flag"])
    return {"rows": len(rows), "latest": max([str(r["date"]) for r in rows], default=""), "output": rel(path)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch external Yahoo/FinMind provider data into staging-only artifacts.")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--out-root", default=str(OUT_ROOT))
    parser.add_argument("--target-asof", default="2026-06-10")
    parser.add_argument("--start", default="2026-06-01")
    parser.add_argument("--end", default="2026-06-17")
    parser.add_argument("--symbol", action="append")
    parser.add_argument("--symbols-file", default=str(DEFAULT_SYMBOLS_FILE))
    parser.add_argument("--max-symbols", type=int, default=int(os.getenv("TW_EXTERNAL_PROVIDER_MAX_SYMBOLS", "5") or 5))
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--retry-sleep-seconds", type=float, default=0.5)
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    run_id = args.run_id or f"external_provider_{args.target_asof.replace('-', '')}_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    out_dir = Path(args.out_root) / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    symbols = load_symbols(args)
    audit: list[dict[str, Any]] = []
    sources: dict[str, Any] = {}
    sources["yahoo_daily_price"] = fetch_yahoo(symbols, args, out_dir, audit)
    raw, summary = fetch_finmind_dataset(symbols, args, out_dir, audit, dataset="TaiwanStockPrice", source_id="finmind_daily_price", subdir="finmind/daily_price")
    sources["finmind_daily_price"] = {**summary, **materialize_finmind_daily(raw, out_dir)}
    raw, summary = fetch_finmind_dataset(symbols, args, out_dir, audit, dataset="TaiwanStockInstitutionalInvestorsBuySell", source_id="finmind_institutional_flow", subdir="finmind/institutional_flow")
    sources["finmind_institutional_flow"] = {**summary, **materialize_institutional(raw, out_dir)}
    raw, summary = fetch_finmind_dataset(symbols, args, out_dir, audit, dataset="TaiwanStockMarginPurchaseShortSale", source_id="finmind_margin_short", subdir="finmind/margin_short")
    sources["finmind_margin_short"] = {**summary, **materialize_margin(raw, out_dir)}

    forbidden = {
        "schema_version": "v1.forbidden_action_audit.v1",
        "actions": {
            "provider_publish_triggered": False,
            "provider_refresh_official_path_triggered": False,
            "accepted_latest_switched": False,
            "qlib_accepted_latest_switched": False,
            "monitor_config_written": False,
            "monitor_scan_triggered": False,
            "alerts_written": False,
            "broker_connected": False,
            "quick_trade_triggered": False,
            "orders_created_or_sent": False,
            "agent_prompt_or_tool_modified": False,
            "readonly_latest_updated": False,
        },
    }
    network_audit = {
        "schema_version": "v1.provider_network_audit.v1",
        "allowed_hosts": sorted(ALLOWED_HOSTS),
        "request_count": len(audit),
        "actual_external_request_count": len(audit),
        "unauthorized_request_count": sum(1 for row in audit if not row.get("allowed_host")),
        "successful_request_count": sum(1 for row in audit if row.get("ok")),
        "failed_request_count": sum(1 for row in audit if not row.get("ok")),
        "retry_policy": {"retries": args.retries, "timeout_seconds": args.timeout, "retry_sleep_seconds": args.retry_sleep_seconds},
        "requests": audit,
        "forbidden_action_audit": forbidden,
    }
    manifest = {
        "schema_version": "v1.external_provider_fetch.v1",
        "artifact_type": "external_provider_fetch",
        "run_id": run_id,
        "mode": "external_provider_reader",
        "target_asof": args.target_asof,
        "start": args.start,
        "end": args.end,
        "symbols": symbols,
        "symbols_requested": len(symbols),
        "sources": sources,
        "network_audit": rel(out_dir / "provider_network_audit.json"),
        "forbidden_action_audit": rel(out_dir / "forbidden_action_audit.json"),
        "staging_only": True,
        "provider_publish_triggered": False,
        "accepted_latest_switched": False,
        "created_at": now(),
    }
    write_json(out_dir / "provider_network_audit.json", network_audit)
    write_json(out_dir / "forbidden_action_audit.json", forbidden)
    write_json(out_dir / "external_provider_manifest.json", manifest)
    result = {"ok": True, "run_id": run_id, "staging_dir": rel(out_dir), "manifest": rel(out_dir / "external_provider_manifest.json"), "network_audit": rel(out_dir / "provider_network_audit.json"), "request_count": len(audit), "unauthorized_request_count": network_audit["unauthorized_request_count"]}
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result["manifest"])
    return 0 if network_audit["unauthorized_request_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
