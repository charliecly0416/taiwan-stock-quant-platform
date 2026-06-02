from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import qlib
from qlib.contrib.data.tw_handler import TWAlpha158Custom
from qlib.data.dataset.handler import DataHandlerLP


SEGMENTS = {
    "train": ("2015-01-01", "2021-12-31"),
    "valid": ("2022-01-01", "2023-12-31"),
    "test": ("2024-01-01", "2026-05-21"),
}


def segment_mask(index: pd.MultiIndex, start: str, end: str) -> np.ndarray:
    dates = index.get_level_values("datetime")
    return (dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))


def calc_daily_ic_all(features: pd.DataFrame, label: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    data = features.copy()
    data["__label__"] = label
    ic_rows = []
    ric_rows = []
    ic_dates = []
    ric_dates = []

    for date, group in data.groupby(level="datetime", sort=True):
        group = group.droplevel("datetime")
        y = group.pop("__label__")
        valid = y.notna()
        x = group.loc[valid]
        y = y.loc[valid]
        if len(y) < 3 or y.nunique(dropna=True) < 2:
            continue

        ic = x.corrwith(y, axis=0, method="pearson")
        if ic.notna().any():
            ic_rows.append(ic)
            ic_dates.append(date)

        x_rank = x.rank(axis=0)
        y_rank = y.rank()
        ric = x_rank.corrwith(y_rank, axis=0, method="pearson")
        if ric.notna().any():
            ric_rows.append(ric)
            ric_dates.append(date)

    ic_df = pd.DataFrame(ic_rows, index=pd.Index(ic_dates, name="datetime"))
    ric_df = pd.DataFrame(ric_rows, index=pd.Index(ric_dates, name="datetime"))
    return ic_df, ric_df


def summarize_series(s: pd.Series, prefix: str) -> dict[str, float | int]:
    s = s.dropna()
    std = s.std()
    return {
        f"{prefix}_mean": float(s.mean()) if len(s) else np.nan,
        f"{prefix}_std": float(std) if len(s) else np.nan,
        f"{prefix}_ir": float(s.mean() / std) if len(s) and std else np.nan,
        f"{prefix}_positive_rate": float((s > 0).mean()) if len(s) else np.nan,
    }


def build_summary(features: pd.DataFrame, label: pd.Series) -> pd.DataFrame:
    rows: list[dict[str, str | float | int]] = []
    for segment, (start, end) in SEGMENTS.items():
        mask = segment_mask(features.index, start, end)
        seg_features = features.loc[mask]
        seg_label = label.loc[mask]
        ic_df, ric_df = calc_daily_ic_all(seg_features, seg_label)
        for factor in features.columns:
            ic = ic_df[factor] if factor in ic_df else pd.Series(dtype=float)
            ric = ric_df[factor] if factor in ric_df else pd.Series(dtype=float)
            row: dict[str, str | float | int] = {
                "factor": factor,
                "segment": segment,
                "n_days": int(ic.dropna().shape[0]),
            }
            row.update(summarize_series(ic, "ic"))
            row.update(summarize_series(ric, "rank_ic"))
            rows.append(row)
    summary = pd.DataFrame(rows)
    summary["abs_rank_ic_mean"] = summary["rank_ic_mean"].abs()
    return summary.sort_values(["segment", "abs_rank_ic_mean"], ascending=[True, False])


def to_markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "(empty)"
    display = df.copy()
    for col in display.columns:
        if pd.api.types.is_float_dtype(display[col]):
            display[col] = display[col].map(lambda x: "" if pd.isna(x) else f"{x:.6f}")
        else:
            display[col] = display[col].map(lambda x: "" if pd.isna(x) else str(x))
    header = "| " + " | ".join(display.columns) + " |"
    sep = "| " + " | ".join(["---"] * len(display.columns)) + " |"
    rows = ["| " + " | ".join(row) + " |" for row in display.to_numpy(dtype=str)]
    return '\\n'.join([header, sep] + rows)


def analyze(output_dir: Path, provider_uri: str, market: str) -> None:
    qlib.init(provider_uri=provider_uri, region="tw", expression_cache=None, dataset_cache=None)
    handler = TWAlpha158Custom(
        instruments=market,
        start_time="2015-01-01",
        end_time="2026-05-21",
        fit_start_time="2015-01-01",
        fit_end_time="2021-12-31",
    )
    raw = handler.fetch(col_set=DataHandlerLP.CS_RAW, data_key=DataHandlerLP.DK_R)
    feature_df = raw["feature"]
    label = raw["label"]["LABEL0"]

    output_dir.mkdir(parents=True, exist_ok=True)
    summary = build_summary(feature_df, label)
    summary.to_csv(output_dir / "factor_ic_summary.csv", index=False)

    custom_factors = [c for c in feature_df.columns if c.startswith("TW_")]
    custom = summary[summary["factor"].isin(custom_factors)].copy()
    custom.to_csv(output_dir / "custom_factor_ic_summary.csv", index=False)

    pivot = summary.pivot(index="factor", columns="segment", values="rank_ic_mean").reset_index()
    for col in ["train", "valid", "test"]:
        if col not in pivot:
            pivot[col] = np.nan
    pivot["same_sign_valid_test"] = np.sign(pivot["valid"]) == np.sign(pivot["test"])
    pivot["min_abs_valid_test_rank_ic"] = pivot[["valid", "test"]].abs().min(axis=1)
    pivot = pivot.sort_values("min_abs_valid_test_rank_ic", ascending=False)
    pivot.to_csv(output_dir / "factor_rank_ic_stability.csv", index=False)

    report_path = output_dir / "factor_ic_report.md"
    top_valid_test = pivot[pivot["same_sign_valid_test"]].head(20)
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# TW Factor IC Report\n\n")
        f.write("## Top Stable Factors by Rank IC\n\n")
        f.write(to_markdown_table(top_valid_test))
        f.write("\n\n## Custom Factors\n\n")
        f.write(custom.sort_values(["factor", "segment"]).to_markdown(index=False))
        f.write("\n")

    print(f"wrote {output_dir / 'factor_ic_summary.csv'}")
    print(f"wrote {output_dir / 'custom_factor_ic_summary.csv'}")
    print(f"wrote {output_dir / 'factor_rank_ic_stability.csv'}")
    print(f"wrote {report_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze TW factor IC and Rank IC.")
    parser.add_argument("--provider-uri", default="~/.qlib/qlib_data/tw_data")
    parser.add_argument("--market", default="tw_demo")
    parser.add_argument("--output-dir", default="data_tw/experiments/factor_analysis")
    args = parser.parse_args()
    analyze(Path(args.output_dir), args.provider_uri, args.market)


if __name__ == "__main__":
    main()
