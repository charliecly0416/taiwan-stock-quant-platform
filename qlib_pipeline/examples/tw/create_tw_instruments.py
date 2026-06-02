from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a demo Taiwan stock universe file for Qlib.")
    parser.add_argument("--summary", default="data_tw/meta/download_summary.csv")
    parser.add_argument("--qlib_dir", default="~/.qlib/qlib_data/tw_data")
    parser.add_argument("--name", default="tw_demo")
    parser.add_argument("--exclude", default="TWII,TW0050")
    args = parser.parse_args()

    summary = pd.read_csv(args.summary)
    exclude = {x.strip().upper() for x in args.exclude.split(",") if x.strip()}
    summary = summary[~summary["symbol"].str.upper().isin(exclude)].copy()

    inst_dir = Path(args.qlib_dir).expanduser() / "instruments"
    inst_dir.mkdir(parents=True, exist_ok=True)
    out_path = inst_dir / f"{args.name}.txt"
    summary[["symbol", "start_datetime", "end_datetime"]].to_csv(out_path, header=False, index=False, sep="\t")
    print(f"wrote {out_path}: {len(summary)} instruments")


if __name__ == "__main__":
    main()
