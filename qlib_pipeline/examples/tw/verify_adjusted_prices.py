from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.export_tw_qlib_normalized import fetch_corporate_actions, query_symbol_for_output


def verify_symbol(symbol: str, data_dir: Path, start: str, end: str, n_events: int) -> tuple[dict, list[dict]]:
    output_symbol = symbol.upper() if symbol.upper().startswith("TW") else f"TW{symbol}"
    query_symbol = query_symbol_for_output(output_symbol)
    df = pd.read_csv(data_dir / f"{output_symbol}.csv", parse_dates=["date"]).set_index("date")
    actions, flags = fetch_corporate_actions(query_symbol, start, end)
    summary = {
        "symbol": output_symbol,
        "rows": int(len(df)),
        "date_min": str(df.index.min().date()) if len(df) else "",
        "date_max": str(df.index.max().date()) if len(df) else "",
        "event_count": int(len(actions)),
        "factor_nunique": int(df["factor"].nunique()) if "factor" in df else 0,
        "factor_min": float(df["factor"].min()) if "factor" in df and len(df) else float("nan"),
        "factor_max": float(df["factor"].max()) if "factor" in df and len(df) else float("nan"),
        "corporate_action_flags": ",".join(flags),
    }
    event_rows: list[dict] = []
    for action in actions[-n_events:]:
        event_date = pd.Timestamp(action.date)
        if event_date not in df.index:
            continue
        pos = df.index.get_loc(event_date)
        if not isinstance(pos, int) or pos <= 0:
            continue
        prev_date = df.index[pos - 1]
        ret = df.loc[event_date, "close"] / df.loc[prev_date, "close"] - 1
        event_rows.append({
            "symbol": output_symbol,
            "event_date": action.date,
            "prev_trade_date": str(prev_date.date()),
            "adjusted_ret": float(ret),
            "event_factor": float(action.adjustment_factor),
            "factor_on_prev": float(df.loc[prev_date, "factor"]),
            "factor_on_event": float(df.loc[event_date, "factor"]),
        })
    return summary, event_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify adjusted TW normalized prices around corporate actions.")
    parser.add_argument("--data-dir", default="data_tw/normalized")
    parser.add_argument("--symbols", default="TW2330,TW2317,TW2882,TW1216,TW1301")
    parser.add_argument("--start", default="2015-01-01")
    parser.add_argument("--end", default="2026-05-21")
    parser.add_argument("--n-events", type=int, default=3)
    parser.add_argument("--output-dir", default="data_tw/experiments/data_fix")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]

    summaries = []
    events = []
    for symbol in symbols:
        summary, event_rows = verify_symbol(symbol, data_dir, args.start, args.end, args.n_events)
        summaries.append(summary)
        events.extend(event_rows)

    summary_df = pd.DataFrame(summaries)
    events_df = pd.DataFrame(events)
    summary_df.to_csv(output_dir / "adjustment_factor_summary.csv", index=False)
    events_df.to_csv(output_dir / "corporate_action_return_check.csv", index=False)
    print(summary_df.to_string(index=False))
    if not events_df.empty:
        display = events_df.copy()
        for col in ["adjusted_ret", "event_factor", "factor_on_prev", "factor_on_event"]:
            display[col] = display[col].map(lambda x: f"{x:.6f}")
        print(display.to_string(index=False))


if __name__ == "__main__":
    main()
