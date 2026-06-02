
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import qlib
from qlib.contrib.data.tw_handler import TWAlpha158Custom
from qlib.data.dataset.handler import DataHandlerLP


ROOT = Path(__file__).resolve().parents[2]
PROVIDER = "data_tw/experiments/yahoo_adjusted_primary/qlib_bin"
MARKET = "tw_liquid_dyn"
START = "2015-05-04"
END = "2025-06-30"
FIT_END = "2020-12-31"
CANDIDATES = ["TW_RET_VOL20", "TW_MA20_GAP"]
SEGMENTS = {
    "train": ("2015-05-04", "2020-12-31"),
    "valid": ("2021-01-01", "2022-12-31"),
    "test": ("2023-01-01", "2025-06-30"),
    "test_2023": ("2023-01-01", "2023-12-31"),
    "test_2024": ("2024-01-01", "2024-12-31"),
    "test_2025h1": ("2025-01-01", "2025-06-30"),
}


def calc_daily_ic(features: pd.DataFrame, label: pd.Series, factors: list[str]) -> pd.DataFrame:
    data = features[factors].copy()
    data["__label__"] = label
    rows = []
    for date, group in data.groupby(level="datetime", sort=True):
        group = group.droplevel("datetime")
        y = group.pop("__label__")
        valid = y.notna()
        group = group.loc[valid]
        y = y.loc[valid]
        if len(y) < 5 or y.nunique(dropna=True) < 2:
            continue
        for factor in factors:
            x = group[factor]
            ok = x.notna() & y.notna()
            if ok.sum() < 5 or x[ok].nunique(dropna=True) < 2:
                continue
            rows.append(
                {
                    "date": pd.Timestamp(date),
                    "factor": factor,
                    "n": int(ok.sum()),
                    "coverage": float(ok.mean()),
                    "ic": float(x[ok].corr(y[ok], method="pearson")),
                    "rank_ic": float(x[ok].corr(y[ok], method="spearman")),
                }
            )
    return pd.DataFrame(rows)


def summarize_ic(daily: pd.DataFrame, name: str, start: str, end: str) -> pd.DataFrame:
    seg = daily[(daily["date"] >= pd.Timestamp(start)) & (daily["date"] <= pd.Timestamp(end))]
    rows = []
    for factor, g in seg.groupby("factor"):
        for col in ["ic", "rank_ic"]:
            s = g[col].dropna()
            std = s.std()
            rows.append(
                {
                    "segment": name,
                    "factor": factor,
                    "metric": col,
                    "n_days": int(s.shape[0]),
                    "mean": float(s.mean()) if len(s) else np.nan,
                    "std": float(std) if len(s) else np.nan,
                    "ir": float(s.mean() / std) if len(s) and std else np.nan,
                    "positive_rate": float((s > 0).mean()) if len(s) else np.nan,
                    "avg_coverage": float(g["coverage"].mean()) if len(g) else np.nan,
                    "avg_n": float(g["n"].mean()) if len(g) else np.nan,
                }
            )
    return pd.DataFrame(rows)


def add_liquidity_buckets(features: pd.DataFrame) -> pd.Series:
    amount = features["VOLUME0"] * features["VWAP0"]
    amt60 = amount.groupby(level="instrument").transform(lambda s: s.rolling(60, min_periods=20).mean())
    buckets = []
    for date, s in amt60.groupby(level="datetime", sort=True):
        valid = s.dropna()
        if valid.shape[0] < 30:
            continue
        ranks = valid.rank(pct=True, method="first")
        b = pd.Series("mid", index=valid.index, dtype="object")
        b[ranks <= 1 / 3] = "low"
        b[ranks > 2 / 3] = "high"
        buckets.append(b)
    if not buckets:
        return pd.Series(dtype="object", index=features.index)
    out = pd.concat(buckets).reindex(features.index)
    out.name = "liquidity_bucket"
    return out


def calc_bucket_ic(features: pd.DataFrame, label: pd.Series, factors: list[str], buckets: pd.Series) -> pd.DataFrame:
    data = features[factors].copy()
    data["__label__"] = label
    data["__bucket__"] = buckets
    rows = []
    for (date, bucket), group in data.groupby([data.index.get_level_values("datetime"), "__bucket__"], sort=True):
        if pd.isna(bucket):
            continue
        group = group.droplevel("datetime")
        y = group.pop("__label__")
        group = group.drop(columns=["__bucket__"])
        for factor in factors:
            x = group[factor]
            ok = x.notna() & y.notna()
            if ok.sum() < 5 or x[ok].nunique(dropna=True) < 2 or y[ok].nunique(dropna=True) < 2:
                continue
            rows.append(
                {
                    "date": pd.Timestamp(date),
                    "bucket": bucket,
                    "factor": factor,
                    "n": int(ok.sum()),
                    "ic": float(x[ok].corr(y[ok], method="pearson")),
                    "rank_ic": float(x[ok].corr(y[ok], method="spearman")),
                }
            )
    daily = pd.DataFrame(rows)
    test = daily[(daily["date"] >= pd.Timestamp("2023-01-01")) & (daily["date"] <= pd.Timestamp("2025-06-30"))]
    summary_rows = []
    for (factor, bucket), g in test.groupby(["factor", "bucket"]):
        for col in ["ic", "rank_ic"]:
            s = g[col].dropna()
            std = s.std()
            summary_rows.append(
                {
                    "factor": factor,
                    "bucket": bucket,
                    "metric": col,
                    "n_days": int(s.shape[0]),
                    "mean": float(s.mean()) if len(s) else np.nan,
                    "std": float(std) if len(s) else np.nan,
                    "ir": float(s.mean() / std) if len(s) and std else np.nan,
                    "positive_rate": float((s > 0).mean()) if len(s) else np.nan,
                    "avg_n": float(g["n"].mean()) if len(g) else np.nan,
                }
            )
    return pd.DataFrame(summary_rows)


def calc_alpha_corr(features: pd.DataFrame, factors: list[str]) -> pd.DataFrame:
    test = features.loc[(slice(pd.Timestamp("2023-01-01"), pd.Timestamp("2025-06-30")), slice(None)), :]
    alpha_cols = [c for c in test.columns if c not in set(factors) and not c.startswith("TW_")]
    rows = []
    for candidate in factors:
        daily_rows = []
        for date, group in test[[candidate] + alpha_cols].groupby(level="datetime", sort=True):
            group = group.droplevel("datetime")
            x = group[candidate]
            if x.notna().sum() < 5 or x.nunique(dropna=True) < 2:
                continue
            corr = group[alpha_cols].corrwith(x, method="spearman")
            daily_rows.append(corr)
        if not daily_rows:
            continue
        corr_df = pd.DataFrame(daily_rows)
        mean_corr = corr_df.mean().dropna()
        for alpha, value in mean_corr.abs().sort_values(ascending=False).head(12).items():
            rows.append(
                {
                    "candidate": candidate,
                    "alpha_feature": alpha,
                    "mean_spearman_corr": float(mean_corr[alpha]),
                    "abs_mean_spearman_corr": float(abs(mean_corr[alpha])),
                }
            )
    return pd.DataFrame(rows)


def write_report(out: Path, segment_summary: pd.DataFrame, bucket_summary: pd.DataFrame, corr: pd.DataFrame) -> None:
    def fmt(x):
        return "" if pd.isna(x) else f"{x:.6f}" if isinstance(x, float) else str(x)

    test_rank = segment_summary[(segment_summary["segment"].isin(["test", "test_2023", "test_2024", "test_2025h1"])) & (segment_summary["metric"] == "rank_ic")]
    lines = [
        "---",
        "created_at: 2026-05-26",
        "status: diagnostic_complete",
        "related_docs:",
        "  - docs/tw_audit/14_yahoo_primary_retvol_comparison.md",
        "---",
        "",
        "# Yahoo-only RetVol Narrow Diagnostic",
        "",
        "## Scope",
        "",
        "This diagnostic explains why old candidate factors failed under Yahoo-only adjusted primary + tw_liquid_dyn. It does not tune portfolio parameters, does not run rolling/significance, and does not access data after 2025-06-30.",
        "",
        "## Test RankIC By Period",
        "",
        "| segment | factor | n_days | mean_rank_ic | ir | positive_rate | avg_n |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, r in test_rank.iterrows():
        lines.append(
            "| {} | {} | {} | {} | {} | {} | {} |".format(r.get("segment"), r.get("factor"), int(r.get("n_days")), fmt(r.get("mean")), fmt(r.get("ir")), fmt(r.get("positive_rate")), fmt(r.get("avg_n")))
        )
    lines += ["", "## Liquidity Bucket RankIC", "", "| factor | bucket | n_days | mean_rank_ic | ir | positive_rate | avg_n |", "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    br = bucket_summary[bucket_summary["metric"] == "rank_ic"].sort_values(["factor", "bucket"])
    for _, r in br.iterrows():
        lines.append("| {} | {} | {} | {} | {} | {} | {} |".format(r.get("factor"), r.get("bucket"), int(r.get("n_days")), fmt(r.get("mean")), fmt(r.get("ir")), fmt(r.get("positive_rate")), fmt(r.get("avg_n"))))
    lines += ["", "## Strongest Alpha158 Correlations", "", "| candidate | alpha_feature | mean_spearman_corr |", "| --- | --- | ---: |"]
    for _, r in corr.groupby("candidate").head(6).iterrows():
        lines.append("| {} | {} | {} |".format(r.get("candidate"), r.get("alpha_feature"), fmt(r.get("mean_spearman_corr"))))
    lines += [
        "",
        "## Interpretation",
        "",
        "- TW_RET_VOL20 is weakly positive in the full 2023-2025H1 test period, but its RankIC is small and not enough to improve the Alpha158 model portfolio.",
        "- TW_MA20_GAP is weaker than TW_RET_VOL20 in the same period and degrades the combined model further.",
        "- Liquidity-bucket results show whether any residual signal is concentrated in a subset of the dynamic universe rather than broad across tradable names.",
        "- High correlation with existing Alpha158 features means the candidate may be redundant inside the model even when standalone IC is non-zero.",
        "",
        "## Artifacts",
        "",
        "- `" + str(out / "candidate_daily_ic.csv") + "`",
        "- `" + str(out / "candidate_segment_ic.csv") + "`",
        "- `" + str(out / "candidate_liquidity_bucket_ic.csv") + "`",
        "- `" + str(out / "candidate_alpha_feature_correlation.csv") + "`",
    ]
    Path("docs/tw_audit/15_yahoo_primary_retvol_diagnostic.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="data_tw/experiments/yahoo_primary_retvol_diagnostic")
    args = parser.parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    qlib.init(provider_uri=PROVIDER, region="tw", expression_cache=None, dataset_cache=None)
    handler = TWAlpha158Custom(
        instruments=MARKET,
        start_time=START,
        end_time=END,
        fit_start_time=START,
        fit_end_time=FIT_END,
    )
    raw = handler.fetch(col_set=DataHandlerLP.CS_RAW, data_key=DataHandlerLP.DK_R)
    features = raw["feature"]
    label = raw["label"]["LABEL0"]

    daily = calc_daily_ic(features, label, CANDIDATES)
    daily.to_csv(out / "candidate_daily_ic.csv", index=False)
    segment_summary = pd.concat([summarize_ic(daily, name, start, end) for name, (start, end) in SEGMENTS.items()], ignore_index=True)
    segment_summary.to_csv(out / "candidate_segment_ic.csv", index=False)

    buckets = add_liquidity_buckets(features)
    bucket_summary = calc_bucket_ic(features, label, CANDIDATES, buckets)
    bucket_summary.to_csv(out / "candidate_liquidity_bucket_ic.csv", index=False)

    corr = calc_alpha_corr(features, CANDIDATES)
    corr.to_csv(out / "candidate_alpha_feature_correlation.csv", index=False)

    write_report(out, segment_summary, bucket_summary, corr)
    print(f"wrote {out}")
    print("wrote docs/tw_audit/15_yahoo_primary_retvol_diagnostic.md")


if __name__ == "__main__":
    main()
