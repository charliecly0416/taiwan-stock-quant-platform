#!/usr/bin/env python3
"""Build an isolated exact-calendar open-price outcome candidate from a bound source ledger."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from build_tw_mbcds2_isolated_feature_input import ISOLATED_ROOT, load_bound_market_data, resolve

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(*, signal_asof: str, source_ledger: Path, calendar: Path, symbols_file: Path, output: Path) -> dict:
    if not output.resolve().is_relative_to(ISOLATED_ROOT.resolve()):
        raise ValueError("output_outside_isolated_root")
    days = sorted({line.strip()[:10] for line in calendar.read_text(encoding="utf-8").splitlines() if line.strip()})
    following = [day for day in days if day > signal_asof]
    if len(following) < 2:
        raise ValueError("pending_calendar_days")
    entry_date, exit_date = following[:2]
    prices, _, ledger = load_bound_market_data(source_ledger, str(json.loads(source_ledger.read_text())["asof"]))
    symbols = pd.read_csv(symbols_file)["instrument"].astype(str).str.upper().unique().tolist()
    selected = prices[prices.date.isin({entry_date, exit_date}) & prices.instrument.isin(symbols)]
    pivot = selected.pivot(index="instrument", columns="date", values="open")
    if set(pivot.index) != set(symbols) or entry_date not in pivot or exit_date not in pivot:
        raise ValueError("pending_exact_calendar_open_scope")
    if pivot[[entry_date, exit_date]].isna().any().any() or (pivot[[entry_date, exit_date]] <= 0).any().any():
        raise ValueError("pending_suspension_or_missing_open")
    rows = [{"instrument": symbol, "entry_date": entry_date, "entry_open": float(pivot.loc[symbol, entry_date]),
             "exit_date": exit_date, "exit_open": float(pivot.loc[symbol, exit_date])} for symbol in sorted(symbols)]
    output.mkdir(parents=True, exist_ok=True)
    path = output / "outcomes.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    manifest = {"schema_version": "mbcds35.outcome_candidate.v1", "signal_asof": signal_asof,
                "source_asof": ledger["asof"], "source_run_id": ledger["acquisition_run_id"],
                "available_at": ledger["combined_available_at"], "entry_date": entry_date, "exit_date": exit_date,
                "artifact_sha256": digest(path), "trading_calendar_sha256": digest(calendar),
                "complete_scope": len(rows), "published": False,
                "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--signal-asof", required=True)
    parser.add_argument("--source-ledger", required=True)
    parser.add_argument("--trading-calendar", required=True)
    parser.add_argument("--symbols-file", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    try:
        result = build(signal_asof=args.signal_asof, source_ledger=resolve(args.source_ledger), calendar=resolve(args.trading_calendar),
                       symbols_file=resolve(args.symbols_file), output=resolve(args.out))
    except Exception as exc:
        print(json.dumps({"status": "PENDING", "error": str(exc)}, ensure_ascii=True))
        return 2
    print(json.dumps({"status": "PASS", "manifest": result}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
