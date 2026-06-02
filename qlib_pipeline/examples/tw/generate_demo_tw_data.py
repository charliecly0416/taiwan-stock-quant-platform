from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


SYMBOLS = [
    "TWII",
    "TW0050",
    "TW2330",
    "TW2317",
    "TW2454",
    "TW2308",
    "TW2412",
    "TW2881",
    "TW2882",
    "TW1301",
    "TW1303",
    "TW2002",
    "TW2303",
    "TW2357",
    "TW2382",
    "TW2891",
    "TW3711",
    "TW3008",
    "TW1216",
    "TW1326",
]


def make_symbol_frame(symbol: str, dates: pd.DatetimeIndex, idx: int, rng: np.random.Generator) -> pd.DataFrame:
    drift = 0.00015 + idx * 0.00001
    volatility = 0.012 + (idx % 5) * 0.0015
    returns = rng.normal(drift, volatility, size=len(dates))
    if symbol == "TWII":
        returns = rng.normal(0.00012, 0.008, size=len(dates))

    base_price = 10000.0 if symbol == "TWII" else 40.0 + idx * 12.0
    close = base_price * np.exp(np.cumsum(returns))
    overnight = rng.normal(0, volatility / 3, size=len(dates))
    open_ = close * (1 + overnight)
    spread = np.abs(rng.normal(volatility, volatility / 3, size=len(dates)))
    high = np.maximum(open_, close) * (1 + spread)
    low = np.minimum(open_, close) * (1 - spread)
    volume_base = 0 if symbol == "TWII" else 1_000_000 + idx * 130_000
    volume = rng.lognormal(np.log(max(volume_base, 1)), 0.35, len(dates)).round()
    if symbol == "TWII":
        volume = np.zeros(len(dates))

    df = pd.DataFrame(
        {
            "symbol": symbol,
            "date": dates.strftime("%Y-%m-%d"),
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        }
    )
    df["vwap"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4.0
    df["factor"] = 1.0
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic demo Taiwan-market data for Qlib smoke tests.")
    parser.add_argument("--start", default="2015-01-01")
    parser.add_argument("--end", default="2024-12-31")
    parser.add_argument("--output_dir", default="data_tw/normalized")
    parser.add_argument("--seed", type=int, default=20260523)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    dates = pd.bdate_range(args.start, args.end)
    rng = np.random.default_rng(args.seed)

    rows = []
    for idx, symbol in enumerate(SYMBOLS):
        df = make_symbol_frame(symbol, dates, idx, rng)
        df.to_csv(output_dir / f"{symbol}.csv", index=False)
        rows.append(
            {
                "symbol": symbol,
                "start_datetime": df["date"].min(),
                "end_datetime": df["date"].max(),
                "rows": len(df),
                "source": "demo_synthetic",
            }
        )
        print(f"wrote {symbol}: {len(df)} rows")

    meta_dir = Path("data_tw/meta")
    meta_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(meta_dir / "download_summary.csv", index=False)
    print("done: demo_synthetic")


if __name__ == "__main__":
    main()
