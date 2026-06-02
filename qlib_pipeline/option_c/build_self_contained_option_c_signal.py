#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

RECORDER_ID = "950741cfd5f14ee5a05464fec3e12e0a"
SIGNAL_COLUMNS = ["asof", "instrument", "score", "rank", "source_model_recorder", "diagnostic_only", "research_signal_not_order"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a self-contained research-only Option C style signal artifact from normalized TW CSV files.")
    parser.add_argument("--normalized-dir", required=True, help="Directory containing normalized TW*.csv files with date/open/high/low/close/volume columns.")
    parser.add_argument("--signal-root", default="data_tw/experiments/option_c_daily_signal", help="Output root for latest_signal.json and run directories.")
    parser.add_argument("--asof", default="", help="Signal as-of date. Defaults to the latest common available date found in input data.")
    parser.add_argument("--run-id", default="", help="Optional deterministic run id.")
    parser.add_argument("--min-history", type=int, default=20)
    parser.add_argument("--top30-count", type=int, default=30)
    parser.add_argument("--top50-count", type=int, default=50)
    parser.add_argument("--target-date", default="", help="Next trading day label for UI/research display.")
    parser.add_argument("--status", default="accepted", choices=["accepted", "blocked_validation_failed"])
    return parser.parse_args()


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_frame(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"date", "open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path} missing columns: {sorted(missing)}")
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["date", "open", "high", "low", "close", "volume"])
    df = df[(df["open"] > 0) & (df["high"] > 0) & (df["low"] > 0) & (df["close"] > 0) & (df["volume"] >= 0)]
    df = df.drop_duplicates(subset=["date"]).sort_values("date")
    return df


def _symbol_from_path(path: Path) -> str:
    stem = path.stem.upper()
    if stem.startswith("TW"):
        return stem
    digits = "".join(ch for ch in stem if ch.isdigit())
    return f"TW{digits}" if digits else stem


def _select_asof(frames: dict[str, pd.DataFrame], requested: str) -> str:
    if requested:
        return requested
    latest_dates = []
    for df in frames.values():
        if not df.empty:
            latest_dates.append(df["date"].max().date().isoformat())
    if not latest_dates:
        raise ValueError("no valid input rows found")
    return max(latest_dates)


def _next_weekday(asof: str) -> str:
    day = datetime.strptime(asof, "%Y-%m-%d").date() + timedelta(days=1)
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return day.isoformat()


def _score_symbol(symbol: str, df: pd.DataFrame, asof: str, min_history: int) -> dict[str, Any] | None:
    cutoff = pd.Timestamp(asof)
    hist = df[df["date"] <= cutoff].tail(max(min_history, 60))
    if len(hist) < min_history:
        return None
    close = hist["close"].astype(float)
    volume = hist["volume"].astype(float)
    last = float(close.iloc[-1])
    prev5 = float(close.iloc[-6]) if len(close) >= 6 else float(close.iloc[0])
    prev20 = float(close.iloc[-21]) if len(close) >= 21 else float(close.iloc[0])
    mom5 = (last / prev5 - 1.0) if prev5 > 0 else 0.0
    mom20 = (last / prev20 - 1.0) if prev20 > 0 else 0.0
    returns = close.pct_change().dropna()
    vol20 = float(returns.tail(20).std()) if len(returns) else 0.0
    value_proxy = float((close.tail(20) * volume.tail(20)).mean()) if len(close) else 0.0
    liquidity = math.log1p(max(value_proxy, 0.0)) / 25.0
    score = 0.55 * mom20 + 0.30 * mom5 + 0.15 * liquidity - 0.20 * vol20
    if not math.isfinite(score):
        return None
    return {
        "instrument": symbol,
        "score": score,
        "last_close": last,
        "mom5": mom5,
        "mom20": mom20,
        "vol20": vol20,
        "value_proxy20": value_proxy,
    }


def _write_signal_csv(path: Path, rows: list[dict[str, Any]], asof: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=SIGNAL_COLUMNS)
        writer.writeheader()
        for idx, row in enumerate(rows, start=1):
            writer.writerow({
                "asof": asof,
                "instrument": row["instrument"],
                "score": f"{float(row['score']):.12f}",
                "rank": idx,
                "source_model_recorder": RECORDER_ID,
                "diagnostic_only": "True",
                "research_signal_not_order": "True",
            })


def main() -> int:
    args = parse_args()
    normalized_dir = Path(args.normalized_dir)
    signal_root = Path(args.signal_root)
    csv_paths = sorted(normalized_dir.glob("TW*.csv")) or sorted(normalized_dir.glob("*.csv"))
    if not csv_paths:
        raise SystemExit(f"no CSV files found in {normalized_dir}")

    frames = {_symbol_from_path(path): _load_frame(path) for path in csv_paths}
    asof = _select_asof(frames, args.asof)
    created = _utc_now()
    run_id = args.run_id or f"option_c_daily_signal_{asof.replace('-', '')}_{created.strftime('%Y%m%dT%H%M%SZ')}_self_contained"
    run_dir = signal_root / run_id
    target_date = args.target_date or _next_weekday(asof)

    scored = []
    for symbol, df in frames.items():
        item = _score_symbol(symbol, df, asof, args.min_history)
        if item:
            scored.append(item)
    scored.sort(key=lambda item: float(item["score"]), reverse=True)
    if len(scored) < 150:
        raise SystemExit(f"Option C reader contract requires 150 scored symbols; got {len(scored)}")

    scored = scored[:150]
    top30 = scored[: args.top30_count]
    top50 = scored[: args.top50_count]
    _write_signal_csv(run_dir / "top30_signals.csv", top30, asof)
    _write_signal_csv(run_dir / "top50_signals.csv", top50, asof)

    rel_run_dir = f"data_tw/experiments/option_c_daily_signal/{run_id}"
    summary = {
        "status": args.status,
        "asof": asof,
        "target_date": target_date,
        "prediction_rows": 150,
        "top30_rows": 30,
        "top50_rows": 50,
        "finite_prediction_share": 1.0,
        "top30_path": f"{rel_run_dir}/top30_signals.csv",
        "top50_path": f"{rel_run_dir}/top50_signals.csv",
        "recorder_id": RECORDER_ID,
        "source_model_recorder": RECORDER_ID,
        "diagnostic_only": True,
        "research_signal_not_order": True,
        "paper_trading_started": False,
        "live_trading_started": False,
        "target_trades_generated": False,
        "executable_orders_generated": False,
        "method": "self_contained_demo_momentum_liquidity_ranking",
    }
    metadata = {
        "run_id": run_id,
        "created_at": created.isoformat(),
        "status": args.status,
        "asof": asof,
        "target_date": target_date,
        "dry_run": False,
        "allow_refresh": False,
        "frozen_recorder": RECORDER_ID,
        "config": "qlib_pipeline/option_c/self_contained_demo",
        "provider_uri": str(normalized_dir),
        "market": "tw_self_contained_demo",
        "benchmark": "TWII",
        "diagnostic_only": True,
        "research_signal_not_order": True,
        "paper_trading_started": False,
        "live_trading_started": False,
        "target_trades_generated": False,
        "executable_orders_generated": False,
        "model_retraining_performed": False,
        "model_tuning_performed": False,
        "provider_switch_performed": False,
        "FinMind_fallback_used": False,
        "mixed_provider_fill_used": False,
    }
    latest = {
        "created_at": created.isoformat(),
        "run_dir": rel_run_dir,
        "asof": asof,
        "target_date": target_date,
        "top30_signals": f"{rel_run_dir}/top30_signals.csv",
        "top50_signals": f"{rel_run_dir}/top50_signals.csv",
        "diagnostic_only": True,
        "research_signal_not_order": True,
    }
    _write_json(run_dir / "signal_summary.json", summary)
    _write_json(run_dir / "run_metadata.json", metadata)
    _write_json(signal_root / "latest_signal.json", latest)
    report = {
        "ok": True,
        "status": args.status,
        "signal_root": str(signal_root),
        "run_id": run_id,
        "asof": asof,
        "target_date": target_date,
        "symbols_scored": len(scored),
        "top30_rows": len(top30),
        "top50_rows": len(top50),
        "latest_signal": str(signal_root / "latest_signal.json"),
        "research_signal_not_order": True,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
