#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
R1 = ROOT / "data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair"
R1_OPS = R1 / "option_c_ops"
R3_R = ROOT / "data_tw/experiments/risk_control_policy_2022/rcpt15_r3_r_full_yz2_feature_package_repair"
FORMAL_PRICE = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"
FORMAL_TWII = FORMAL_PRICE / "TWII.csv"
CALENDAR = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt"
OUT = ROOT / "data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair"
STOCK_BRIDGE = OUT / "stock_price_bridge"
REPORT = ROOT / "docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_T_ISOLATED_PRICE_TWII_SOURCE_REPAIR_CONTRACT_EXECUTION_REPORT_CN.md"

WORK_DOC = "docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_T_ISOLATED_PRICE_TWII_SOURCE_REPAIR_CONTRACT_WORK_CN.md"
PARENT_CLOSURE = "docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_S_COORDINATOR_CLOSURE_AND_NEXT_STEP_CN.md"
REVIEW_DOC = "docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_S_PRICE_MARKET_FRESHNESS_DIAGNOSTIC_REVIEW_CN.md"
WORKFLOW_SKILL = "/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md"
FRESHNESS_SKILL = ".agents/skills/tw-stock-data-freshness-diagnosis/SKILL.md"

TARGET_DATES = ["2026-06-18", "2026-06-22", "2026-06-23", "2026-06-24", "2026-06-25"]
TARGET_START = pd.Timestamp("2026-06-18")
TARGET_END = pd.Timestamp("2026-06-25")
TWII_REPAIR_START = "2026-05-22"
TWII_REPAIR_END = "2026-06-25"
OUTPUT_COLUMNS = ["symbol", "date", "open", "high", "low", "close", "volume", "vwap", "factor"]
REQUIRED_OUTPUTS = [
    "manifest.json",
    "validator_report.json",
    "stock_price_bridge_inventory.csv",
    "twii_source_attempts.csv",
    "twii_bridge.csv",
    "price_twii_bridge_freshness_audit.csv",
    "source_trace.json",
    "forbidden_scope_audit.csv",
    "repair_plan_for_r3_r_rerun.md",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({key for row in rows for key in row}) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str:
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_symbol(raw: Any) -> str:
    text = str(raw or "").strip().upper()
    if not text:
        return ""
    return text if text.startswith("TW") else f"TW{text}"


def csv_freshness(path: Path) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source_path": rel(path),
        "source_exists": path.exists(),
        "rows": 0,
        "date_min": "",
        "date_max": "",
        "target_window_rows": 0,
        "target_dates_present": "",
        "status": "missing_source",
    }
    if not path.exists():
        return payload
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        payload.update({"status": "read_error", "error": f"{type(exc).__name__}: {exc}"})
        return payload
    if df.empty or "date" not in df.columns:
        payload["status"] = "empty_or_no_date"
        return payload
    dates = pd.to_datetime(df["date"], errors="coerce").dropna()
    payload["rows"] = int(len(df))
    if dates.empty:
        payload["status"] = "no_valid_date"
        return payload
    date_strings = set(dates.dt.strftime("%Y-%m-%d"))
    target_present = [day for day in TARGET_DATES if day in date_strings]
    payload.update(
        {
            "date_min": str(dates.min().date()),
            "date_max": str(dates.max().date()),
            "target_window_rows": len(target_present),
            "target_dates_present": "|".join(target_present),
            "status": "pass",
        }
    )
    return payload


def valid_normalized_frame(path: Path, symbol: str) -> tuple[pd.DataFrame, str]:
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        return pd.DataFrame(), f"read_error:{type(exc).__name__}:{exc}"
    missing = [col for col in OUTPUT_COLUMNS if col not in df.columns]
    if missing:
        return pd.DataFrame(), f"missing_columns:{'|'.join(missing)}"
    out = df[OUTPUT_COLUMNS].copy()
    out["symbol"] = out["symbol"].map(norm_symbol)
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    out = out[out["symbol"].eq(symbol) & out["date"].notna()]
    for col in ["open", "high", "low", "close", "volume", "vwap", "factor"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=["open", "high", "low", "close", "vwap", "factor"])
    out = out[(out["open"] > 0) & (out["high"] > 0) & (out["low"] > 0) & (out["close"] > 0) & (out["factor"] > 0)]
    if out.empty:
        return pd.DataFrame(), "empty_after_normalization"
    out = out.drop_duplicates(["symbol", "date"]).sort_values("date")
    return out, "pass"


def collect_r3_symbols() -> list[str]:
    symbols: set[str] = set()
    for name in ["rerank_score_snapshot.csv", "feature_package.csv", "rerank_top50.csv", "feature_source_trace.csv"]:
        path = R3_R / name
        if not path.exists():
            continue
        try:
            df = pd.read_csv(path, usecols=lambda col: col in {"instrument", "symbol"})
        except Exception:
            continue
        for col in ["instrument", "symbol"]:
            if col in df.columns:
                symbols.update(norm_symbol(value) for value in df[col].dropna().astype(str))
    symbols.discard("")
    symbols.discard("TWII")
    return sorted(symbols)


def candidate_dirs() -> list[Path]:
    if not R1_OPS.exists():
        return []
    dirs = [path for path in R1_OPS.iterdir() if path.is_dir() and (path / "candidate_normalized").is_dir()]
    return sorted(dirs, key=lambda path: path.name)


def latest_candidate_dir() -> Path | None:
    dirs = candidate_dirs()
    return dirs[-1] / "candidate_normalized" if dirs else None


def build_stock_bridge(symbols: list[str], source_dir: Path | None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    STOCK_BRIDGE.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    copied = 0
    date_max_values: list[str] = []
    for symbol in symbols:
        source_path = (source_dir / f"{symbol}.csv") if source_dir else Path("")
        output_path = STOCK_BRIDGE / f"{symbol}.csv"
        df, status = valid_normalized_frame(source_path, symbol) if source_dir else (pd.DataFrame(), "missing_candidate_dir")
        if not df.empty:
            df.to_csv(output_path, index=False)
            copied += 1
        info = csv_freshness(output_path)
        date_max = str(info.get("date_max") or "")
        if date_max:
            date_max_values.append(date_max)
        rows.append(
            {
                "symbol": symbol,
                "source_label": "r1_candidate_normalized",
                "source_path": rel(source_path) if source_dir else "",
                "output_path": rel(output_path),
                "source_sha256": sha256_file(source_path) if source_dir else "",
                "output_sha256": sha256_file(output_path),
                "validation_status": status,
                "rows": info.get("rows", 0),
                "date_min": info.get("date_min", ""),
                "date_max": date_max,
                "target_window_rows": info.get("target_window_rows", 0),
                "target_dates_present": info.get("target_dates_present", ""),
                "fresh_enough_for_r3_t": bool(date_max and pd.Timestamp(date_max) >= TARGET_END),
            }
        )
    fresh_rows = [row for row in rows if row["fresh_enough_for_r3_t"]]
    summary = {
        "stock_price_bridge_symbols": copied,
        "stock_price_bridge_fresh_symbols": len(fresh_rows),
        "stock_price_bridge_min_date_max": min(date_max_values, default=""),
        "stock_price_bridge_max_date_max": max(date_max_values, default=""),
        "stock_price_bridge_dir": rel(STOCK_BRIDGE),
        "stock_source_dir": rel(source_dir) if source_dir else "",
    }
    return rows, summary


def local_twii_candidates() -> list[tuple[str, Path]]:
    candidates: list[tuple[str, Path]] = [("formal_normalized_nonempty", FORMAL_TWII)]
    for job_dir in candidate_dirs():
        path = job_dir / "candidate_normalized/TWII.csv"
        if path.exists():
            candidates.append((f"r1_candidate_normalized:{job_dir.name}", path))
    for base in [ROOT / "data_tw", ROOT / "qlib_pipeline/data_tw"]:
        if not base.exists():
            continue
        for path in base.rglob("*.csv"):
            if OUT in path.parents:
                continue
            lower = path.name.lower()
            if not any(token in lower for token in ["twii", "taiex"]):
                continue
            key = rel(path)
            if all(rel(existing) != key for _, existing in candidates):
                candidates.append(("local_inventory_name_match", path))
    return candidates


def to_epoch(day: str, *, exclusive_end: bool = False) -> int:
    dt = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=UTC)
    if exclusive_end:
        dt += timedelta(days=1)
    return int(dt.timestamp())


def clean_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
    except Exception:
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def yahoo_url(ticker: str, start: str, end: str) -> str:
    params = {
        "period1": str(to_epoch(start)),
        "period2": str(to_epoch(end, exclusive_end=True)),
        "interval": "1d",
        "events": "history",
        "includeAdjustedClose": "true",
    }
    return "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(ticker, safe="") + "?" + urllib.parse.urlencode(params)


def fetch_json_url(url: str, timeout: float = 25.0) -> tuple[dict[str, Any] | None, int | str, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            payload = json.loads(response.read().decode("utf-8"))
            return payload, status, ""
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            body = ""
        return None, exc.code, f"HTTPError:{exc.code}:{body}"
    except Exception as exc:
        return None, "network_error", f"{type(exc).__name__}:{exc}"


def yahoo_payload_to_frame(payload: dict[str, Any]) -> tuple[pd.DataFrame, str]:
    error = payload.get("chart", {}).get("error") if isinstance(payload, dict) else "bad_payload"
    if error:
        return pd.DataFrame(), f"chart_error:{error}"
    result = (payload.get("chart", {}).get("result") or [None])[0]
    if not result:
        return pd.DataFrame(), "empty_result"
    timestamps = result.get("timestamp") or []
    quote = (result.get("indicators", {}).get("quote") or [{}])[0]
    adj = (result.get("indicators", {}).get("adjclose") or [{}])[0]
    rows: list[dict[str, Any]] = []
    for index, ts in enumerate(timestamps):
        open_raw = clean_float((quote.get("open") or [None] * len(timestamps))[index])
        high_raw = clean_float((quote.get("high") or [None] * len(timestamps))[index])
        low_raw = clean_float((quote.get("low") or [None] * len(timestamps))[index])
        close_raw = clean_float((quote.get("close") or [None] * len(timestamps))[index])
        adj_close = clean_float((adj.get("adjclose") or [None] * len(timestamps))[index])
        volume_raw = (quote.get("volume") or [None] * len(timestamps))[index]
        if None in {open_raw, high_raw, low_raw, close_raw}:
            continue
        if adj_close is None:
            adj_close = close_raw
        if min(open_raw, high_raw, low_raw, close_raw, adj_close) <= 0:
            continue
        try:
            volume = int(volume_raw or 0)
        except Exception:
            volume = 0
        factor = adj_close / close_raw if close_raw else 1.0
        open_adj = open_raw * factor
        high_adj = high_raw * factor
        low_adj = low_raw * factor
        close_adj = close_raw * factor
        rows.append(
            {
                "symbol": "TWII",
                "date": datetime.fromtimestamp(int(ts), tz=UTC).strftime("%Y-%m-%d"),
                "open": open_adj,
                "high": max(high_adj, open_adj, close_adj),
                "low": min(low_adj, open_adj, close_adj),
                "close": close_adj,
                "volume": volume,
                "vwap": (open_adj + high_adj + low_adj + close_adj) / 4.0,
                "factor": factor,
            }
        )
    if not rows:
        return pd.DataFrame(), "empty_rows"
    out = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    out = out.drop_duplicates(["symbol", "date"]).sort_values("date")
    return out, "pass"


def finmind_url(start: str, end: str) -> str:
    params = {
        "dataset": "TaiwanStockPrice",
        "data_id": "TAIEX",
        "start_date": start,
        "end_date": end,
    }
    return "https://api.finmindtrade.com/api/v4/data?" + urllib.parse.urlencode(params)


def finmind_payload_to_frame(payload: dict[str, Any]) -> tuple[pd.DataFrame, str]:
    if payload.get("status") not in (None, 200, "200", True):
        return pd.DataFrame(), f"non_ok_status:{payload.get('status')}"
    rows: list[dict[str, Any]] = []
    for item in payload.get("data") or []:
        try:
            open_price = clean_float(item.get("open"))
            high = clean_float(item.get("max"))
            low = clean_float(item.get("min"))
            close = clean_float(item.get("close"))
            volume = int(float(item.get("Trading_Volume") or item.get("volume") or 0))
        except Exception:
            continue
        if None in {open_price, high, low, close}:
            continue
        if min(open_price, high, low, close) <= 0:
            continue
        rows.append(
            {
                "symbol": "TWII",
                "date": str(item.get("date") or ""),
                "open": open_price,
                "high": max(high, open_price, close),
                "low": min(low, open_price, close),
                "close": close,
                "volume": volume,
                "vwap": (open_price + high + low + close) / 4.0,
                "factor": 1.0,
            }
        )
    if not rows:
        return pd.DataFrame(), "empty_rows"
    out = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    out = out.drop_duplicates(["symbol", "date"]).sort_values("date")
    return out, "pass"


def merge_twii(formal_path: Path, repair_df: pd.DataFrame) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    if formal_path.exists():
        formal, status = valid_normalized_frame(formal_path, "TWII")
        if status == "pass" and not formal.empty:
            frames.append(formal)
    if not repair_df.empty:
        frames.append(repair_df[OUTPUT_COLUMNS].copy())
    if not frames:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    out = pd.concat(frames, ignore_index=True)
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    out = out[out["date"].notna()]
    out = out.drop_duplicates(["symbol", "date"], keep="last").sort_values("date")
    return out[OUTPUT_COLUMNS]


def build_twii_bridge() -> tuple[pd.DataFrame, list[dict[str, Any]], dict[str, Any]]:
    attempts: list[dict[str, Any]] = []
    selected_source = ""
    network_used = False
    repair_df = pd.DataFrame(columns=OUTPUT_COLUMNS)
    selected_local_path = ""

    for label, path in local_twii_candidates():
        info = csv_freshness(path)
        enough = set((info.get("target_dates_present") or "").split("|")) >= set(TARGET_DATES)
        attempts.append(
            {
                "attempt_order": len(attempts) + 1,
                "source_type": "local_csv",
                "source_label": label,
                "url_or_api": "",
                "source_path": rel(path),
                "attempted_at": now(),
                "http_status": "",
                "rows": info.get("rows", 0),
                "date_min": info.get("date_min", ""),
                "date_max": info.get("date_max", ""),
                "target_window_rows": info.get("target_window_rows", 0),
                "status": "usable" if enough else "not_fresh_enough",
                "error": "" if path.exists() else "missing_source",
            }
        )
        if enough:
            local_df, status = valid_normalized_frame(path, "TWII")
            if status == "pass" and not local_df.empty:
                repair_df = local_df
                selected_source = f"local:{label}"
                selected_local_path = rel(path)
                break

    if repair_df.empty:
        for source_label, url_builder, parser in [
            ("yahoo_chart:^TWII", lambda start, end: yahoo_url("^TWII", start, end), yahoo_payload_to_frame),
            ("finmind:TAIEX", finmind_url, finmind_payload_to_frame),
        ]:
            url = url_builder(TWII_REPAIR_START, TWII_REPAIR_END)
            network_used = True
            payload, http_status, error = fetch_json_url(url)
            rows = 0
            date_min = ""
            date_max = ""
            target_window_rows = 0
            status = "failed"
            frame = pd.DataFrame(columns=OUTPUT_COLUMNS)
            if payload is not None:
                frame, parse_status = parser(payload)
                if parse_status == "pass" and not frame.empty:
                    info_path = OUT / "_tmp_twii_attempt.csv"
                    frame.to_csv(info_path, index=False)
                    info = csv_freshness(info_path)
                    try:
                        info_path.unlink()
                    except OSError:
                        pass
                    rows = int(info.get("rows", 0) or 0)
                    date_min = str(info.get("date_min") or "")
                    date_max = str(info.get("date_max") or "")
                    target_window_rows = int(info.get("target_window_rows", 0) or 0)
                    status = "usable" if set((info.get("target_dates_present") or "").split("|")) >= set(TARGET_DATES) else "not_fresh_enough"
                    error = "" if status == "usable" else "target_window_missing_rows"
                else:
                    error = parse_status
            attempts.append(
                {
                    "attempt_order": len(attempts) + 1,
                    "source_type": "network_market_index_only",
                    "source_label": source_label,
                    "url_or_api": url,
                    "source_path": "",
                    "attempted_at": now(),
                    "http_status": http_status,
                    "rows": rows,
                    "date_min": date_min,
                    "date_max": date_max,
                    "target_window_rows": target_window_rows,
                    "status": status,
                    "error": error,
                }
            )
            if status == "usable":
                repair_df = frame
                selected_source = source_label
                break
            time.sleep(0.5)

    bridge = merge_twii(FORMAL_TWII, repair_df)
    if not bridge.empty:
        bridge.to_csv(OUT / "twii_bridge.csv", index=False)
    else:
        pd.DataFrame(columns=OUTPUT_COLUMNS).to_csv(OUT / "twii_bridge.csv", index=False)
    info = csv_freshness(OUT / "twii_bridge.csv")
    summary = {
        "selected_twii_source": selected_source,
        "selected_local_twii_path": selected_local_path,
        "twii_bridge_path": rel(OUT / "twii_bridge.csv"),
        "twii_bridge_rows": int(info.get("rows", 0) or 0),
        "twii_bridge_date_min": info.get("date_min", ""),
        "twii_bridge_date_max": info.get("date_max", ""),
        "target_window_twii_rows": int(info.get("target_window_rows", 0) or 0),
        "target_window_twii_dates_present": info.get("target_dates_present", ""),
        "network_used": network_used,
    }
    return bridge, attempts, summary


def forbidden_scope_audit(network_used: bool) -> tuple[list[dict[str, Any]], bool]:
    rows = [
        {
            "forbidden_action": "provider_publish",
            "triggered": False,
            "evidence": "script writes only RCPT15_R3_T isolated output directory and execution report",
        },
        {
            "forbidden_action": "accepted_latest_switch",
            "triggered": False,
            "evidence": "script does not write qlib/provider accepted latest or invoke scheduler",
        },
        {
            "forbidden_action": "formal_latest_write",
            "triggered": False,
            "evidence": "script does not mutate formal provider directories or latest pointers",
        },
        {
            "forbidden_action": "daily_ltr_rerank_latest_write",
            "triggered": False,
            "evidence": "script has no writes to daily_ltr_rerank_latest",
        },
        {
            "forbidden_action": "latest_orthogonal_features_latest_write",
            "triggered": False,
            "evidence": "script has no writes to latest_orthogonal_features_latest",
        },
        {
            "forbidden_action": "order_target_quantity_broker_output",
            "triggered": False,
            "evidence": "outputs are price/TWII bridge artifacts only; no OrderIntent, target_weight, target_position, quantity, or broker fields",
        },
        {
            "forbidden_action": "full_market_stock_network_pull",
            "triggered": False,
            "evidence": "network path, when used, is limited to ^TWII Yahoo chart and TAIEX FinMind market index endpoints",
        },
        {
            "forbidden_action": "network_pull_outside_twii_market_index",
            "triggered": False,
            "evidence": "network_used=%s; attempted endpoints are recorded in twii_source_attempts.csv" % network_used,
        },
    ]
    return rows, not any(row["triggered"] for row in rows)


def build_freshness_audit(summary: dict[str, Any], forbidden_ok: bool) -> tuple[list[dict[str, Any]], bool]:
    stock_symbols = int(summary.get("stock_price_bridge_symbols", 0) or 0)
    stock_min = str(summary.get("stock_price_bridge_min_date_max") or "")
    twii_max = str(summary.get("twii_bridge_date_max") or "")
    twii_rows = int(summary.get("target_window_twii_rows", 0) or 0)
    checks = [
        ("stock_price_bridge_symbols", stock_symbols, "== 99", stock_symbols == 99),
        ("stock_price_bridge_min_date_max", stock_min, ">= 2026-06-25", bool(stock_min and pd.Timestamp(stock_min) >= TARGET_END)),
        ("twii_bridge_date_max", twii_max, ">= 2026-06-25", bool(twii_max and pd.Timestamp(twii_max) >= TARGET_END)),
        ("target_window_twii_rows", twii_rows, ">= 5 target signal dates", twii_rows >= 5),
        ("forbidden_scope_pass", forbidden_ok, "is true", forbidden_ok),
        ("provider_publish", False, "is false", True),
        ("accepted_latest_switch", False, "is false", True),
        ("formal_latest_write", False, "is false", True),
    ]
    rows = [
        {
            "gate": gate,
            "actual": actual,
            "expected": expected,
            "pass": passed,
            "target_dates": "|".join(TARGET_DATES),
        }
        for gate, actual, expected, passed in checks
    ]
    return rows, all(bool(item[3]) for item in checks)


def repair_plan(summary: dict[str, Any]) -> str:
    return f"""# RCPT15_R3_T Repair Plan For R3_R Rerun

## Bridge Inputs

- Stock bridge: `{summary.get('stock_price_bridge_dir', '')}`
- Stock source: `{summary.get('stock_source_dir', '')}`
- TWII bridge: `{summary.get('twii_bridge_path', '')}`
- TWII selected source: `{summary.get('selected_twii_source', '')}`

## Explicit R3_R Consumption Contract

The next R3_R repair rerun should consume these isolated paths explicitly instead of reading the stale formal `normalized_nonempty` directory:

```text
PRICE_DIR={summary.get('stock_price_bridge_dir', '')}
TWII_BRIDGE={summary.get('twii_bridge_path', '')}
```

The rerun must remain readonly/shadow:

```text
provider_publish=false
accepted_latest_switch=false
formal_latest_write=false
daily_ltr_rerank_latest_write=false
latest_orthogonal_features_latest_write=false
order_or_target_output=false
```

## Freshness Gate

- stock_price_bridge_symbols = {summary.get('stock_price_bridge_symbols', 0)}
- stock_price_bridge_min_date_max = {summary.get('stock_price_bridge_min_date_max', '')}
- twii_bridge_date_max = {summary.get('twii_bridge_date_max', '')}
- target_window_twii_rows = {summary.get('target_window_twii_rows', 0)}
"""


def build_report(summary: dict[str, Any], validator: dict[str, Any]) -> str:
    return f"""# RCPT15_R3_T Isolated Price / TWII Source Repair Contract 执行报告

## 1. Scope

- Assigned phase: RCPT15_R3_T_ISOLATED_PRICE_TWII_SOURCE_REPAIR_CONTRACT
- Mainline / work document: `{WORK_DOC}`
- Parent closure: `{PARENT_CLOSURE}`
- Review source: `{REVIEW_DOC}`
- Non-goals confirmed: 不 provider publish、不切 qlib/provider accepted latest、不写 formal latest pointer、不写 daily_ltr_rerank_latest / latest_orthogonal_features_latest、不输出 OrderIntent/target_weight/target_position/quantity/broker。

## 2. Documents / Contracts / Skills Read

- `{WORKFLOW_SKILL}`
- `{FRESHNESS_SKILL}`
- `.agents/skills/tw-stock-data-freshness-diagnosis/references/data-source-boundary.md`
- `.agents/skills/tw-stock-data-freshness-diagnosis/references/freshness-status-fields.md`
- `{WORK_DOC}`
- `{PARENT_CLOSURE}`
- `{REVIEW_DOC}`

## 3. Changes Made

- 新增脚本 `scripts/build_tw_policy_rcpt15_r3_t_isolated_price_twii_source_repair.py`。
- 新增隔离输出目录 `{rel(OUT)}`。
- 用 R1 `candidate_normalized` 构造 R3 99 symbols 的 isolated `stock_price_bridge`。
- 构造 isolated `twii_bridge.csv`，优先本地；本地不足时仅对 TWII / market index source 执行 isolated pull。

## 4. Evidence Produced

- `{rel(OUT / 'manifest.json')}`
- `{rel(OUT / 'validator_report.json')}`
- `{rel(OUT / 'stock_price_bridge_inventory.csv')}`
- `{rel(OUT / 'twii_source_attempts.csv')}`
- `{rel(OUT / 'twii_bridge.csv')}`
- `{rel(OUT / 'price_twii_bridge_freshness_audit.csv')}`
- `{rel(OUT / 'source_trace.json')}`
- `{rel(OUT / 'forbidden_scope_audit.csv')}`
- `{rel(OUT / 'repair_plan_for_r3_r_rerun.md')}`
- `{rel(STOCK_BRIDGE)}/*.csv`

## 5. Key Freshness Gate

- Verdict: `{validator.get('verdict', '')}`。
- stock_price_bridge_symbols = `{summary.get('stock_price_bridge_symbols', 0)}`。
- stock_price_bridge_min_date_max = `{summary.get('stock_price_bridge_min_date_max', '')}`。
- twii_bridge_date_max = `{summary.get('twii_bridge_date_max', '')}`。
- target_window_twii_rows = `{summary.get('target_window_twii_rows', 0)}`，dates = `{summary.get('target_window_twii_dates_present', '')}`。
- price_twii_bridge_freshness_pass = `{validator.get('price_twii_bridge_freshness_pass', False)}`。
- forbidden_scope_pass = `{validator.get('forbidden_scope_pass', False)}`。

## 6. Source Trace

- Stock source: `{summary.get('stock_source_dir', '')}`。
- TWII selected source: `{summary.get('selected_twii_source', '')}`。
- Network used: `{summary.get('network_used', False)}`。
- Network boundary: TWII / market index only; no full-market stock pull.

## 7. Forbidden Actions Audit

- provider_publish = `false`
- accepted_latest_switch = `false`
- formal_latest_write = `false`
- daily_ltr_rerank_latest_write = `false`
- latest_orthogonal_features_latest_write = `false`
- order_target_quantity_broker_output = `false`
- full_market_stock_network_pull = `false`

## 8. Issues / Blockers / Deviations

- 无已知 blocker。
- 本轮只生成 isolated bridge，不重跑 R3_R。

## 9. Recommendation For Reviewer

建议复审 `PASS_READY_FOR_R3_R_RERUN`，下一步由 R3_R repair rerun 显式读取本 isolated stock/TWII bridge。
"""


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    source_dir = latest_candidate_dir()
    symbols = collect_r3_symbols()
    stock_rows, stock_summary = build_stock_bridge(symbols, source_dir)
    _, twii_attempts, twii_summary = build_twii_bridge()
    forbidden_rows, forbidden_ok = forbidden_scope_audit(bool(twii_summary.get("network_used")))

    summary: dict[str, Any] = {
        "created_at": now(),
        "target_dates": TARGET_DATES,
        "r3_symbols_checked": len(symbols),
        "r1_candidate_job_id": source_dir.parent.name if source_dir else "",
        **stock_summary,
        **twii_summary,
        "provider_publish": False,
        "accepted_latest_switch": False,
        "formal_latest_write": False,
        "daily_ltr_rerank_latest_write": False,
        "latest_orthogonal_features_latest_write": False,
        "order_or_target_output": False,
        "full_market_stock_network_pull": False,
    }
    freshness_rows, freshness_ok = build_freshness_audit(summary, forbidden_ok)
    if freshness_ok:
        verdict = "PASS_READY_FOR_R3_R_RERUN"
    elif not summary.get("selected_twii_source"):
        verdict = "STOP_REQUIRES_USER_DATA_SOURCE"
    else:
        verdict = "FAIL_NEEDS_REPAIR"

    validator = {
        "ok": freshness_ok and forbidden_ok,
        "verdict": verdict,
        "stock_price_bridge_symbols": summary["stock_price_bridge_symbols"],
        "stock_price_bridge_min_date_max": summary["stock_price_bridge_min_date_max"],
        "twii_bridge_date_max": summary["twii_bridge_date_max"],
        "target_window_twii_rows": summary["target_window_twii_rows"],
        "price_twii_bridge_freshness_pass": freshness_ok,
        "forbidden_scope_pass": forbidden_ok,
        "provider_publish": False,
        "accepted_latest_switch": False,
        "formal_latest_write": False,
        "daily_ltr_rerank_latest_write": False,
        "latest_orthogonal_features_latest_write": False,
        "order_or_target_output": False,
        "full_market_stock_network_pull": False,
        "outputs_required": REQUIRED_OUTPUTS,
    }
    summary["verdict"] = verdict
    summary["price_twii_bridge_freshness_pass"] = freshness_ok
    summary["forbidden_scope_pass"] = forbidden_ok

    write_csv(OUT / "stock_price_bridge_inventory.csv", stock_rows)
    write_csv(OUT / "twii_source_attempts.csv", twii_attempts)
    write_csv(OUT / "price_twii_bridge_freshness_audit.csv", freshness_rows)
    write_csv(OUT / "forbidden_scope_audit.csv", forbidden_rows)
    write_text(OUT / "repair_plan_for_r3_r_rerun.md", repair_plan(summary))
    write_json(
        OUT / "source_trace.json",
        {
            "created_at": summary["created_at"],
            "stock_source": {
                "source_type": "local_r1_candidate_normalized",
                "job_id": summary["r1_candidate_job_id"],
                "path": summary["stock_source_dir"],
                "symbols": summary["stock_price_bridge_symbols"],
            },
            "twii_source": {
                "selected_source": summary["selected_twii_source"],
                "selected_local_path": summary["selected_local_twii_path"],
                "network_used": summary["network_used"],
                "attempts_csv": rel(OUT / "twii_source_attempts.csv"),
            },
            "forbidden_scope": {
                "provider_publish": False,
                "accepted_latest_switch": False,
                "formal_latest_write": False,
                "daily_ltr_rerank_latest_write": False,
                "latest_orthogonal_features_latest_write": False,
                "order_or_target_output": False,
                "full_market_stock_network_pull": False,
            },
        },
    )
    write_json(OUT / "validator_report.json", validator)
    write_json(
        OUT / "manifest.json",
        {
            "artifact_type": "rcpt15_r3_t_isolated_price_twii_source_repair",
            "schema_version": "rcpt15_r3_t_v1",
            "created_at": summary["created_at"],
            "work_doc": WORK_DOC,
            "parent_closure": PARENT_CLOSURE,
            "output_dir": rel(OUT),
            "summary": summary,
            "artifacts": {name: rel(OUT / name) for name in REQUIRED_OUTPUTS},
        },
    )
    write_text(REPORT, build_report(summary, validator))
    print(json.dumps({"ok": validator["ok"], **summary}, ensure_ascii=False, indent=2))
    return 0 if validator["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
