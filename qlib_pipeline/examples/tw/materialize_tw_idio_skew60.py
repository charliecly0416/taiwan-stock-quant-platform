from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import qlib
from qlib.data import D

from screen_tw_academic_factors import ROOT, PROVIDER, START, END, fetch_raw
from screen_tw_idio_skew60 import FACTOR, build_idio_skew, fetch_benchmark_return

FIELD = "tw_idio_skew60"
BIN_NAME = f"{FIELD}.day.bin"


def load_calendar(provider: Path) -> list[pd.Timestamp]:
    return pd.to_datetime(pd.read_csv(provider / "calendars/day.txt", header=None).iloc[:, 0]).tolist()


def write_feature_bins(factor: pd.DataFrame, provider: Path, start: str, end: str) -> pd.DataFrame:
    calendar = load_calendar(provider)
    cal_index = pd.Index(calendar)
    scoped_dates = cal_index[(cal_index >= pd.Timestamp(start)) & (cal_index <= pd.Timestamp(end))]
    if scoped_dates.empty:
        raise ValueError("no calendar dates in requested scope")
    date_index = calendar.index(scoped_dates[0])
    rows = []
    for instrument, group in factor[FACTOR].groupby(level="instrument", sort=True):
        s = group.droplevel("instrument").sort_index().reindex(scoped_dates)
        feature_dir = provider / "features" / instrument.lower()
        feature_dir.mkdir(parents=True, exist_ok=True)
        out_path = feature_dir / BIN_NAME
        values = s.to_numpy(dtype=np.float32)
        np.hstack([np.array([date_index], dtype=np.float32), values]).astype("<f").tofile(out_path)
        finite = np.isfinite(values)
        rows.append(
            {
                "instrument": instrument,
                "path": str(out_path.relative_to(ROOT)),
                "start": scoped_dates[0].strftime("%Y-%m-%d"),
                "end": scoped_dates[-1].strftime("%Y-%m-%d"),
                "n_values": int(values.shape[0]),
                "finite_values": int(finite.sum()),
                "finite_share": float(finite.mean()) if len(finite) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def deterministic_sample(factor: pd.DataFrame, n: int) -> pd.DataFrame:
    finite = factor[FACTOR].dropna().reset_index().sort_values(["datetime", "instrument"])
    if finite.empty:
        return finite
    positions = np.linspace(0, len(finite) - 1, min(n, len(finite)), dtype=int)
    return finite.iloc[positions].reset_index(drop=True)


def validate_materialized(factor: pd.DataFrame, provider: Path, sample_n: int) -> pd.DataFrame:
    sample = deterministic_sample(factor, sample_n)
    rows = []
    for _, row in sample.iterrows():
        instrument = str(row["instrument"])
        date = pd.Timestamp(row["datetime"])
        expected = float(row[FACTOR])
        loaded = D.features([instrument], [f"${FIELD}"], start_time=date, end_time=date, freq="day")
        if loaded.empty:
            actual = np.nan
        else:
            actual = float(loaded.iloc[0, 0])
        expected_f32 = float(np.float32(expected))
        rows.append(
            {
                "instrument": instrument,
                "datetime": date.strftime("%Y-%m-%d"),
                "screen_value": expected,
                "screen_value_float32": expected_f32,
                "materialized_value": actual,
                "abs_diff_vs_screen": abs(actual - expected) if np.isfinite(actual) else np.nan,
                "abs_diff_vs_float32_screen": abs(actual - expected_f32) if np.isfinite(actual) else np.nan,
                "pass_float32_tolerance_1e_8": bool(np.isfinite(actual) and abs(actual - expected_f32) < 1e-8),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Materialize TW_IDIO_SKEW60 into the local Qlib bin provider.")
    parser.add_argument("--provider", default=PROVIDER)
    parser.add_argument("--output-dir", default="data_tw/experiments/yahoo_primary_tw_idio_skew60_materialized")
    parser.add_argument("--sample-n", type=int, default=10)
    args = parser.parse_args()

    provider = ROOT / args.provider
    out_dir = ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    qlib.init(provider_uri=str(provider), region="tw", expression_cache=None, dataset_cache=None)
    features, _ = fetch_raw()
    market_ret = fetch_benchmark_return()
    factor, _ = build_idio_skew(features, market_ret)

    manifest = write_feature_bins(factor, provider, START, END)
    manifest.to_csv(out_dir / "tw_idio_skew60_materialization_manifest.csv", index=False)
    validation = validate_materialized(factor, provider, args.sample_n)
    validation.to_csv(out_dir / "tw_idio_skew60_materialization_validation.csv", index=False)

    max_diff = validation["abs_diff_vs_float32_screen"].max() if not validation.empty else np.nan
    print(f"instruments={manifest.shape[0]}")
    print(f"finite_values={int(manifest['finite_values'].sum())}")
    print(f"validation_max_abs_diff_vs_float32={max_diff}")
    print(f"validation_pass={bool(validation['pass_float32_tolerance_1e_8'].all()) if not validation.empty else False}")
    print(f"wrote {out_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
