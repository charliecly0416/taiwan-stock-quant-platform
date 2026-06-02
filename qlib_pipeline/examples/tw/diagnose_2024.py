from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def load_prices(data_dir: Path) -> pd.DataFrame:
    frames = []
    for path in sorted(data_dir.glob("TW*.csv")):
        symbol = path.stem.upper()
        if symbol in {"TWII", "TW0050"}:
            continue
        df = pd.read_csv(path, usecols=["date", "close", "volume"], parse_dates=["date"])
        df["instrument"] = symbol
        frames.append(df)
    data = pd.concat(frames, ignore_index=True)
    data = data.sort_values(["date", "instrument"])
    data["ret_1d"] = data.groupby("instrument")["close"].pct_change()
    data["vol20"] = data.groupby("instrument")["ret_1d"].transform(lambda s: s.rolling(20, min_periods=10).std())
    data["amount_proxy"] = data["close"] * data["volume"]
    data["amount60"] = data.groupby("instrument")["amount_proxy"].transform(lambda s: s.rolling(60, min_periods=20).mean())
    return data.set_index(["date", "instrument"]).sort_index()


def flatten_positions(positions: dict[Any, Any]) -> pd.DataFrame:
    rows = []
    for date, payload in positions.items():
        if isinstance(payload, dict):
            pos = payload.get("position", {})
        else:
            pos = getattr(payload, "position", {})
        for inst, item in pos.items():
            if inst in {"cash", "now_account_value"} or not isinstance(item, dict):
                continue
            rows.append({
                "date": pd.Timestamp(date),
                "instrument": inst,
                "amount": float(item.get("amount") or 0.0),
                "price": float(item.get("price") or 0.0),
                "weight": float(item.get("weight") or 0.0),
                "count_day": int(item.get("count_day") or 0),
            })
    return pd.DataFrame(rows)


def calc_contributions(holdings: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    rows = []
    dates = sorted(holdings["date"].unique())
    for date in dates:
        date = pd.Timestamp(date)
        h = holdings[holdings["date"] == date].copy()
        for _, row in h.iterrows():
            key = (date, row["instrument"])
            if key not in prices.index:
                continue
            try:
                loc = prices.index.get_loc(key)
            except KeyError:
                continue
            inst_df = prices.xs(row["instrument"], level="instrument")
            if date not in inst_df.index:
                continue
            pos = inst_df.index.get_loc(date)
            if not isinstance(pos, int) or pos + 1 >= len(inst_df.index):
                continue
            next_date = inst_df.index[pos + 1]
            next_ret = float(inst_df.iloc[pos + 1]["ret_1d"])
            if not np.isfinite(next_ret):
                continue
            rows.append({
                "date": date,
                "next_date": next_date,
                "instrument": row["instrument"],
                "weight": row["weight"],
                "next_ret": next_ret,
                "contribution": row["weight"] * next_ret,
                "vol20": float(prices.loc[key, "vol20"]),
                "amount60": float(prices.loc[key, "amount60"]),
            })
    return pd.DataFrame(rows)


def calc_daily_exposure(contrib: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for date, group in contrib.groupby("date"):
        try:
            day = prices.xs(pd.Timestamp(date), level="date").copy()
        except KeyError:
            continue
        vol_rank = day["vol20"].rank(pct=True)
        amount_rank = day["amount60"].rank(pct=True)
        g = group.copy()
        g["vol_rank"] = [vol_rank.get(inst, np.nan) for inst in g["instrument"]]
        g["amount_rank"] = [amount_rank.get(inst, np.nan) for inst in g["instrument"]]
        rows.append({
            "date": pd.Timestamp(date),
            "holdings": int(len(g)),
            "weight_sum": float(g["weight"].sum()),
            "weighted_next_ret": float(g["contribution"].sum()),
            "weighted_vol_rank": float((g["weight"] * g["vol_rank"]).sum() / g["weight"].sum()) if g["weight"].sum() else np.nan,
            "weighted_amount_rank": float((g["weight"] * g["amount_rank"]).sum() / g["weight"].sum()) if g["weight"].sum() else np.nan,
        })
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose TW 2024 portfolio failure from Qlib recorder artifacts.")
    parser.add_argument("--recorder-dir", default="mlruns/607910013167647574/84adf6e5bd4a4b15b39da57d565703d4")
    parser.add_argument("--data-dir", default="data_tw/normalized")
    parser.add_argument("--output-dir", default="data_tw/experiments/diagnose_2024")
    args = parser.parse_args()

    recorder = Path(args.recorder_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    pa_dir = recorder / "artifacts" / "portfolio_analysis"
    report = pd.read_pickle(pa_dir / "report_normal_1day.pkl")
    positions = pd.read_pickle(pa_dir / "positions_normal_1day.pkl")
    holdings = flatten_positions(positions)
    prices = load_prices(Path(args.data_dir))
    contrib = calc_contributions(holdings, prices)
    exposure = calc_daily_exposure(contrib, prices)

    top_loss = contrib.groupby("instrument", as_index=False)["contribution"].sum().sort_values("contribution").head(15)
    top_gain = contrib.groupby("instrument", as_index=False)["contribution"].sum().sort_values("contribution", ascending=False).head(15)
    daily = report.reset_index().rename(columns={"datetime": "date"})
    daily["excess_return_est"] = daily["return"] - daily["bench"]
    daily = daily.merge(exposure, on="date", how="left")

    holdings.to_csv(output_dir / "daily_holdings.csv", index=False)
    contrib.to_csv(output_dir / "holding_next_day_contributions.csv", index=False)
    daily.to_csv(output_dir / "daily_portfolio_exposure.csv", index=False)
    top_loss.to_csv(output_dir / "top_loss_contributors.csv", index=False)
    top_gain.to_csv(output_dir / "top_gain_contributors.csv", index=False)

    print("top loss contributors")
    print(top_loss.head(10).to_string(index=False))
    print("daily exposure summary")
    print(daily[["return", "bench", "excess_return_est", "weighted_vol_rank", "weighted_amount_rank"]].describe().to_string())


if __name__ == "__main__":
    main()
