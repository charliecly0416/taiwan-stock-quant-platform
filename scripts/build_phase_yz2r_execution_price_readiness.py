#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SIGNAL_ROOT = ROOT / "data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals"
YZ2_PRICE = ROOT / "data_tw/artifacts/phase_yz/yz2_execution_price_readiness"
DEFAULT_OUT_ROOT = ROOT / "data_tw/artifacts/phase_yz/yz2r_execution_price_readiness"
PRICE_DIR = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"
CALENDAR = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt"
TARGET_NEXT_DAY = "2026-06-18"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_top50(signal_asof: str) -> list[str]:
    manifest = read_json(SIGNAL_ROOT / signal_asof / "model_a/manifest.json")
    signals = SIGNAL_ROOT / signal_asof / "model_a" / manifest["files"]["signals"]
    df = pd.read_csv(signals)
    df["candidate_rank_num"] = pd.to_numeric(df["candidate_rank"], errors="coerce")
    top50 = df[df["candidate_rank_num"].between(1, 50)].sort_values(["candidate_rank_num", "instrument"])
    if len(top50) != 50:
        raise ValueError(f"strict E4 top50 expected 50 rows, got {len(top50)}")
    return top50["instrument"].astype(str).tolist()


def calendar_next_day(signal_asof: str) -> str | None:
    days = [line.strip() for line in CALENDAR.read_text(encoding="utf-8").splitlines() if line.strip()]
    future = [d for d in days if d > signal_asof]
    return min(future) if future else None


def read_price(symbol: str) -> pd.DataFrame:
    path = PRICE_DIR / f"{symbol}.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for col in ["open", "high", "low", "close", "volume", "vwap", "factor"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(subset=["date"]).sort_values("date")


def build(signal_asof: str, out_root: Path) -> dict[str, Any]:
    out_dir = out_root / signal_asof
    out_dir.mkdir(parents=True, exist_ok=True)
    symbols = load_top50(signal_asof)
    cal_next = calendar_next_day(signal_asof)
    next_day = TARGET_NEXT_DAY
    rows: list[dict[str, Any]] = []
    source_files = []
    for symbol in symbols:
        price_path = PRICE_DIR / f"{symbol}.csv"
        df = read_price(symbol)
        if price_path.exists():
            source_files.append(price_path)
        signal_hist = df[df["date"] <= pd.Timestamp(signal_asof)] if not df.empty else pd.DataFrame()
        signal_close = "" if signal_hist.empty else signal_hist.iloc[-1].get("close", "")
        signal_close_date = "" if signal_hist.empty else str(signal_hist.iloc[-1]["date"].date())
        next_rows = df[df["date"] == pd.Timestamp(next_day)] if not df.empty else pd.DataFrame()
        has_next_row = not next_rows.empty
        next_open = "" if not has_next_row else next_rows.iloc[0].get("open", "")
        next_close = "" if not has_next_row else next_rows.iloc[0].get("close", "")
        open_available = bool(has_next_row and pd.notna(next_open))
        close_available = bool(has_next_row and pd.notna(next_close))
        signal_close_available = bool(signal_close != "" and pd.notna(signal_close))
        rows.append({
            "signal_asof": signal_asof,
            "instrument": symbol,
            "target_next_trading_day": next_day,
            "calendar_next_trading_day": cal_next or "",
            "calendar_contains_target_next_day": cal_next == next_day,
            "price_source_file": rel(price_path) if price_path.exists() else "",
            "price_source_has_target_next_day_row": has_next_row,
            "next_trading_day_open": next_open,
            "next_trading_day_close": next_close,
            "close_on_or_before_signal_asof": signal_close,
            "close_on_or_before_signal_asof_date": signal_close_date,
            "next_open_available": open_available,
            "next_close_available": close_available,
            "signal_close_available": signal_close_available,
            "open_equals_signal_close": bool(open_available and signal_close_available and float(next_open) == float(signal_close)),
            "fallback_to_next_close": False,
            "fallback_to_signal_close": False,
            "status": "pass" if open_available and close_available and signal_close_available else "execution_price_unavailable",
        })
    fields = list(rows[0].keys())
    write_csv(out_dir / "price_availability_audit.csv", rows, fields)
    next_open_count = sum(1 for r in rows if r["next_open_available"])
    next_close_count = sum(1 for r in rows if r["next_close_available"])
    signal_close_count = sum(1 for r in rows if r["signal_close_available"])
    open_equals_signal_close_count = sum(1 for r in rows if r["open_equals_signal_close"])
    status = "pass" if next_open_count == 50 and next_close_count == 50 and signal_close_count == 50 else "execution_price_unavailable"
    source_trace = {
        "artifact_type": "YZ2RExecutionPriceSourceTrace",
        "signal_asof": signal_asof,
        "target_next_trading_day": next_day,
        "calendar_next_trading_day": cal_next,
        "calendar_contains_target_next_day": cal_next == next_day,
        "price_source": rel(PRICE_DIR),
        "source_file_count": len(source_files),
        "source_file_sha256_sample": [{"path": rel(p), "sha256": sha256(p)} for p in source_files[:5]],
        "local_csv_scan_found_2026_06_18": next_open_count > 0 or next_close_count > 0,
        "external_network_used": False,
        "provider_refresh_triggered": False,
        "provider_publish_triggered": False,
        "accepted_latest_switch_triggered": False,
        "fallback_to_next_close": False,
        "fallback_to_signal_close": False,
        "manual_or_synthetic_ohlc": False,
        "blocked_reason": "local_2026_06_18_ohlc_not_found" if status != "pass" else "",
    }
    write_json(out_dir / "source_trace.json", source_trace)
    write_json(out_dir / "forbidden_action_audit.json", {"actions": {"training": False, "tuning": False, "network_provider_fetch": False, "provider_refresh": False, "provider_publish": False, "accepted_latest_switch": False, "monitor_write": False, "monitor_scan": False, "broker_order": False, "quick_trade": False, "paper_apply_reset_write": False, "frontend_change": False}})
    manifest = {
        "artifact_type": "YZ2RExecutionPriceReadiness",
        "schema_version": "yz2r.execution_price_readiness.v1",
        "created_at": utc_now(),
        "signal_asof": signal_asof,
        "target_next_trading_day": next_day,
        "calendar_next_trading_day": cal_next,
        "calendar_contains_target_next_day": cal_next == next_day,
        "universe_source": rel(SIGNAL_ROOT / signal_asof / "model_a/manifest.json"),
        "model_b_source": rel(SIGNAL_ROOT / signal_asof / "model_b_yz2/manifest.json"),
        "previous_yz2_readiness": rel(YZ2_PRICE / signal_asof / "manifest.json"),
        "execution_price_mode_planned_for_yz3": "next_open",
        "row_count": len(rows),
        "next_open_available_count": next_open_count,
        "next_close_available_count": next_close_count,
        "close_on_or_before_signal_asof_available_count": signal_close_count,
        "missing_next_open_count": len(rows) - next_open_count,
        "missing_next_close_count": len(rows) - next_close_count,
        "missing_signal_close_count": len(rows) - signal_close_count,
        "open_equals_signal_close_count": open_equals_signal_close_count,
        "status": status,
        "recommended_gate": "allow_yz3" if status == "pass" else "blocked_before_yz3",
        "no_fallback_to_next_close": True,
        "no_fallback_to_signal_close": True,
        "price_source": rel(PRICE_DIR),
        "price_availability_audit": "price_availability_audit.csv",
        "source_trace": "source_trace.json",
        "forbidden_action_audit": "forbidden_action_audit.json",
    }
    write_json(out_dir / "manifest.json", manifest)
    return {"ok": True, "manifest": rel(out_dir / "manifest.json"), "status": status, "next_open_available_count": next_open_count, "missing_next_open_count": len(rows) - next_open_count, "recommended_gate": manifest["recommended_gate"]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair/check YZ2R execution price readiness using local audited price sources only.")
    parser.add_argument("--signal-asof", default="2026-06-17")
    parser.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = build(args.signal_asof, Path(args.out_root))
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result["manifest"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
