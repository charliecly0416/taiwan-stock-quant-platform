from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yfinance as yf


DEFAULT_SYMBOLS = {
    "TWII": "^TWII",
    "TW0050": "0050.TW",
    "TW2330": "2330.TW",
    "TW2317": "2317.TW",
    "TW2454": "2454.TW",
    "TW2308": "2308.TW",
    "TW2412": "2412.TW",
    "TW2881": "2881.TW",
    "TW2882": "2882.TW",
    "TW1301": "1301.TW",
    "TW1303": "1303.TW",
    "TW2002": "2002.TW",
    "TW2303": "2303.TW",
    "TW2357": "2357.TW",
    "TW2382": "2382.TW",
    "TW2891": "2891.TW",
    "TW3711": "3711.TW",
    "TW3008": "3008.TW",
    "TW1216": "1216.TW",
    "TW1326": "1326.TW",
    "TW5871": "5871.TW",
    "TW5880": "5880.TW",
}


def normalize_history(symbol: str, yahoo_symbol: str, start: str, end: str) -> pd.DataFrame:
    hist = yf.download(
        yahoo_symbol,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
        actions=False,
        threads=False,
    )
    if hist.empty:
        return pd.DataFrame()

    if isinstance(hist.columns, pd.MultiIndex):
        hist.columns = hist.columns.get_level_values(0)

    hist = hist.reset_index()
    hist.columns = [str(c).strip().lower().replace(" ", "_") for c in hist.columns]
    date_col = "date" if "date" in hist.columns else "datetime"
    out = pd.DataFrame(
        {
            "symbol": symbol,
            "date": pd.to_datetime(hist[date_col]).dt.strftime("%Y-%m-%d"),
            "open": hist["open"].astype(float),
            "high": hist["high"].astype(float),
            "low": hist["low"].astype(float),
            "close": hist["close"].astype(float),
            "volume": hist["volume"].fillna(0).astype(float),
        }
    )
    out["vwap"] = (out["open"] + out["high"] + out["low"] + out["close"]) / 4.0
    out["factor"] = 1.0
    out = out.dropna(subset=["open", "high", "low", "close"]).drop_duplicates(["symbol", "date"])
    out = out.sort_values("date")
    return out


def write_instrument_file(data_dir: Path, data_by_symbol: dict[str, pd.DataFrame]) -> None:
    meta_dir = data_dir / "meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for symbol, df in sorted(data_by_symbol.items()):
        if df.empty:
            continue
        rows.append(
            {
                "symbol": symbol,
                "start_datetime": df["date"].min(),
                "end_datetime": df["date"].max(),
                "rows": len(df),
            }
        )
    pd.DataFrame(rows).to_csv(meta_dir / "download_summary.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download a small Taiwan equity prototype dataset from Yahoo Finance.")
    parser.add_argument("--start", default="2015-01-01")
    parser.add_argument("--end", default="2025-01-01")
    parser.add_argument("--output_dir", default="data_tw/normalized")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    symbols = list(DEFAULT_SYMBOLS.items())
    if args.limit is not None:
        symbols = symbols[: args.limit]

    data_by_symbol = {}
    for symbol, yahoo_symbol in symbols:
        df = normalize_history(symbol, yahoo_symbol, args.start, args.end)
        if df.empty:
            print(f"skip empty: {symbol} ({yahoo_symbol})")
            continue
        df.to_csv(output_dir / f"{symbol}.csv", index=False)
        data_by_symbol[symbol] = df
        print(f"wrote {symbol}: {len(df)} rows")

    write_instrument_file(Path("data_tw"), data_by_symbol)
    print(f"done: {len(data_by_symbol)} instruments")


if __name__ == "__main__":
    main()
