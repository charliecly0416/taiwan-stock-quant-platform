#!/usr/bin/env python3
"""Build a time-consistent dynamic Taiwan stock universe.

The default parameters reproduce the Yahoo-only `tw_liquid_dyn` universe used by
`docs/tw_audit/11_yahoo_adjusted_primary_status.md`:

- monthly re-selection
- trailing 60 trading days average amount
- amount = volume * vwap
- top 150 symbols
- next trading month effective period
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

import pandas as pd


def load_amount_data(data_dir: Path, calendar_symbol: str) -> pd.DataFrame:
    rows = []
    for path in sorted(data_dir.glob("TW*.csv")):
        symbol = path.stem.upper()
        if symbol == calendar_symbol.upper():
            continue
        df = pd.read_csv(path, parse_dates=["date"])
        if df.empty:
            continue
        df["symbol"] = symbol
        volume = pd.to_numeric(df["volume"], errors="coerce").fillna(0.0)
        vwap = pd.to_numeric(df["vwap"], errors="coerce").fillna(0.0)
        df["amount"] = volume * vwap
        rows.append(df[["symbol", "date", "amount"]])
    if not rows:
        raise ValueError(f"no stock CSV files found in {data_dir}")
    return pd.concat(rows, ignore_index=True)


def load_calendar(data_dir: Path, calendar_symbol: str) -> pd.DatetimeIndex:
    path = data_dir / f"{calendar_symbol.upper()}.csv"
    if not path.exists():
        raise FileNotFoundError(f"calendar file not found: {path}")
    dates = pd.read_csv(path, parse_dates=["date"])["date"].dropna().unique()
    return pd.DatetimeIndex(dates).sort_values()


def month_end_trading_dates(calendar: pd.DatetimeIndex) -> list[pd.Timestamp]:
    month_ends: list[pd.Timestamp] = []
    series = pd.Series(calendar)
    for _, group in series.groupby(series.dt.to_period("M")):
        month_ends.append(pd.Timestamp(group.iloc[-1]))
    return month_ends


def next_month_effective_period(calendar: pd.DatetimeIndex, asof: pd.Timestamp) -> tuple[pd.Timestamp, pd.Timestamp] | None:
    next_dates = calendar[calendar > asof]
    if len(next_dates) == 0:
        return None
    start = pd.Timestamp(next_dates[0])
    future_months = pd.Series(next_dates).dt.to_period("M")
    same_next_month = next_dates[future_months == future_months.iloc[0]]
    return start, pd.Timestamp(same_next_month[-1])


def build_raw_members(
    amount_df: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    *,
    lookback_days: int,
    topk: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    period_members = []
    turnover = []
    prev_members: set[str] = set()
    for asof in month_end_trading_dates(calendar):
        hist_dates = calendar[calendar <= asof][-lookback_days:]
        if len(hist_dates) < lookback_days:
            continue
        effective = next_month_effective_period(calendar, asof)
        if effective is None:
            continue
        start, end = effective
        hist = amount_df[amount_df["date"].isin(hist_dates)]
        rank = hist.groupby("symbol")["amount"].mean().sort_values(ascending=False).head(topk)
        members = set(rank.index)
        for symbol in rank.index:
            period_members.append((symbol, start, end))
        turnover.append({
            "asof": asof.date().isoformat(),
            "effective_start": start.date().isoformat(),
            "effective_end": end.date().isoformat(),
            "members": len(members),
            "in_count": len(members - prev_members) if prev_members else len(members),
            "out_count": len(prev_members - members) if prev_members else 0,
        })
        prev_members = members
    members_df = pd.DataFrame(period_members, columns=["symbol", "start_datetime", "end_datetime"])
    turnover_df = pd.DataFrame(turnover)
    return members_df, turnover_df


def merge_adjacent_segments(members_df: pd.DataFrame, *, max_gap_days: int) -> pd.DataFrame:
    segments = []
    if members_df.empty:
        return pd.DataFrame(columns=["symbol", "start_datetime", "end_datetime"])
    for symbol, group in members_df.sort_values(["symbol", "start_datetime"]).groupby("symbol"):
        cur_start = None
        cur_end = None
        for _, row in group.iterrows():
            start = pd.Timestamp(row["start_datetime"])
            end = pd.Timestamp(row["end_datetime"])
            if cur_start is None:
                cur_start, cur_end = start, end
            elif start <= cur_end + pd.Timedelta(days=max_gap_days):
                cur_end = max(cur_end, end)
            else:
                segments.append((symbol, cur_start.date().isoformat(), cur_end.date().isoformat()))
                cur_start, cur_end = start, end
        if cur_start is not None:
            segments.append((symbol, cur_start.date().isoformat(), cur_end.date().isoformat()))
    return pd.DataFrame(segments, columns=["symbol", "start_datetime", "end_datetime"]).sort_values(
        ["symbol", "start_datetime"]
    )


def write_outputs(
    segments: pd.DataFrame,
    turnover: pd.DataFrame,
    output_dir: Path,
    output_name: str,
    summary: dict,
    qlib_instruments_dir: Path | None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    universe_path = output_dir / f"{output_name}.txt"
    summary_path = output_dir / f"{output_name}_summary.json"
    turnover_path = output_dir / f"{output_name}_turnover.csv"
    segments.to_csv(universe_path, sep="	", header=False, index=False)
    turnover.to_csv(turnover_path, index=False)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if qlib_instruments_dir is not None:
        qlib_instruments_dir.mkdir(parents=True, exist_ok=True)
        segments.to_csv(qlib_instruments_dir / f"{output_name}.txt", sep="	", header=False, index=False)
    print(f"wrote {universe_path}")
    print(f"wrote {summary_path}")
    print(f"wrote {turnover_path}")


def build_summary(
    data_dir: Path,
    qlib_dir: str,
    amount_df: pd.DataFrame,
    members_df: pd.DataFrame,
    segments: pd.DataFrame,
    turnover: pd.DataFrame,
    *,
    lookback_days: int,
    topk: int,
    frequency: str,
) -> dict:
    return {
        "source": "yahoo_adjusted_primary",
        "source_dir": str(data_dir),
        "qlib_dir": qlib_dir,
        "lookback_days": lookback_days,
        "topk": topk,
        "frequency": frequency,
        "eligible_symbols": int(amount_df["symbol"].nunique()),
        "raw_monthly_rows": int(len(members_df)),
        "segments": int(len(segments)),
        "unique_symbols": int(segments["symbol"].nunique()) if not segments.empty else 0,
        "start_date": segments["start_datetime"].min() if not segments.empty else "",
        "end_date": segments["end_datetime"].max() if not segments.empty else "",
        "symbols_with_multiple_segments": int((segments.groupby("symbol").size() > 1).sum()) if not segments.empty else 0,
        "avg_members": float(turnover["members"].mean()) if not turnover.empty else 0.0,
        "avg_in_count": float(turnover["in_count"].iloc[1:].mean()) if len(turnover) > 1 else 0.0,
        "avg_out_count": float(turnover["out_count"].iloc[1:].mean()) if len(turnover) > 1 else 0.0,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build dynamic TW liquidity universe from normalized CSV files.")
    parser.add_argument("--data-dir", default="data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty")
    parser.add_argument("--calendar-symbol", default="TWII")
    parser.add_argument("--lookback-days", type=int, default=60)
    parser.add_argument("--topk", type=int, default=150)
    parser.add_argument("--frequency", choices=["month"], default="month")
    parser.add_argument("--max-merge-gap-days", type=int, default=4)
    parser.add_argument("--output-dir", default="data_tw/experiments/yahoo_adjusted_primary/universe")
    parser.add_argument("--output-name", default="tw_liquid_dyn")
    parser.add_argument("--qlib-instruments-dir", default="data_tw/experiments/yahoo_adjusted_primary/qlib_bin/instruments")
    parser.add_argument("--no-qlib-copy", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    data_dir = Path(args.data_dir)
    amount_df = load_amount_data(data_dir, args.calendar_symbol)
    calendar = load_calendar(data_dir, args.calendar_symbol)
    members_df, turnover_df = build_raw_members(
        amount_df,
        calendar,
        lookback_days=args.lookback_days,
        topk=args.topk,
    )
    segments = merge_adjacent_segments(members_df, max_gap_days=args.max_merge_gap_days)
    qlib_dir = "" if args.no_qlib_copy else str(Path(args.qlib_instruments_dir).parent)
    summary = build_summary(
        data_dir,
        qlib_dir,
        amount_df,
        members_df,
        segments,
        turnover_df,
        lookback_days=args.lookback_days,
        topk=args.topk,
        frequency=args.frequency,
    )
    write_outputs(
        segments,
        turnover_df,
        Path(args.output_dir),
        args.output_name,
        summary,
        None if args.no_qlib_copy else Path(args.qlib_instruments_dir),
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
