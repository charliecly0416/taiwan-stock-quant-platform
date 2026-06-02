from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]


def load_report(recorder_id: str) -> pd.DataFrame:
    matches = list((ROOT / "mlruns").glob(f"*/*{recorder_id}*/artifacts/portfolio_analysis/report_normal_1day.pkl"))
    if not matches:
        matches = list((ROOT / "mlruns").glob(f"*/{recorder_id}/artifacts/portfolio_analysis/report_normal_1day.pkl"))
    if not matches:
        raise FileNotFoundError(f"report not found for recorder {recorder_id}")
    df = pd.read_pickle(matches[0]).reset_index().rename(columns={"datetime": "date"})
    df["excess"] = df["return"] - df["bench"]
    return df[["date", "excess"]]


def paired_ttest(a: pd.Series, b: pd.Series) -> tuple[float, float, int]:
    diff = (b - a).dropna()
    if len(diff) < 3:
        return np.nan, np.nan, int(len(diff))
    res = stats.ttest_1samp(diff, 0.0, nan_policy="omit")
    return float(diff.mean()), float(res.pvalue), int(len(diff))


def main() -> None:
    parser = argparse.ArgumentParser(description="Paired t-test for TW rolling recorder excess returns.")
    parser.add_argument("--baseline-summary", default="data_tw/experiments/rolling_alpha158_after_adjustment/summary.csv")
    parser.add_argument("--candidate-summary", default="data_tw/experiments/rolling_retvol_after_adjustment/summary.csv")
    parser.add_argument("--baseline-name", default="alpha158")
    parser.add_argument("--candidate-name", default="retvol")
    parser.add_argument("--output-dir", default="data_tw/experiments/significance_after_adjustment")
    args = parser.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    base = pd.read_csv(args.baseline_summary)
    cand = pd.read_csv(args.candidate_summary)
    rows = []
    daily_rows = []
    for _, b_row in base.iterrows():
        window = b_row["window"]
        c_match = cand[cand["window"] == window]
        if c_match.empty:
            continue
        c_row = c_match.iloc[0]
        b_daily = load_report(str(b_row["recorder_id"])).rename(columns={"excess": "baseline_excess"})
        c_daily = load_report(str(c_row["recorder_id"])).rename(columns={"excess": "candidate_excess"})
        merged = b_daily.merge(c_daily, on="date", how="inner")
        mean_diff, p_value, n = paired_ttest(merged["baseline_excess"], merged["candidate_excess"])
        merged["window"] = window
        daily_rows.append(merged)
        rows.append({
            "window": window,
            "n_days": n,
            "baseline_recorder": b_row["recorder_id"],
            "candidate_recorder": c_row["recorder_id"],
            "baseline_with_cost_ann": b_row.get("with_cost_annualized_return"),
            "candidate_with_cost_ann": c_row.get("with_cost_annualized_return"),
            "ann_diff": c_row.get("with_cost_annualized_return") - b_row.get("with_cost_annualized_return"),
            "daily_excess_mean_diff": mean_diff,
            "paired_t_p_value": p_value,
            "same_direction_positive": bool(mean_diff > 0),
        })
    result = pd.DataFrame(rows)
    daily = pd.concat(daily_rows, ignore_index=True) if daily_rows else pd.DataFrame()
    if not daily.empty:
        mean_diff, p_value, n = paired_ttest(daily["baseline_excess"], daily["candidate_excess"])
        overall = pd.DataFrame([{
            "window": "overall",
            "n_days": n,
            "daily_excess_mean_diff": mean_diff,
            "paired_t_p_value": p_value,
            "same_direction_positive": bool(mean_diff > 0),
        }])
    else:
        overall = pd.DataFrame(columns=["window", "n_days", "daily_excess_mean_diff", "paired_t_p_value", "same_direction_positive"])
    result.to_csv(out / "paired_ttest_summary.csv", index=False)
    overall.to_csv(out / "paired_ttest_overall.csv", index=False)
    daily.to_csv(out / "paired_daily_excess.csv", index=False)
    print(result.to_string(index=False))
    print(overall.to_string(index=False))


if __name__ == "__main__":
    main()
