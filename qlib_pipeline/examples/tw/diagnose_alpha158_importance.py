from __future__ import annotations

import argparse
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

import qlib
from qlib.contrib.data.handler import Alpha158
from qlib.data.dataset.handler import DataHandlerLP


ROOT = Path(__file__).resolve().parents[2]
PROVIDER = "data_tw/experiments/yahoo_adjusted_primary/qlib_bin"
MARKET = "tw_liquid_dyn"
RECORDER_ID = "950741cfd5f14ee5a05464fec3e12e0a"
EXPERIMENT_ID = "607910013167647574"
START = "2015-05-04"
END = "2025-06-30"
FIT_END = "2020-12-31"
SEGMENTS = {
    "train": ("2015-05-04", "2020-12-31"),
    "valid": ("2021-01-01", "2022-12-31"),
    "test": ("2023-01-01", "2025-06-30"),
}


def load_baseline_model(recorder_id: str, experiment_id: str):
    model_path = ROOT / "mlruns" / experiment_id / recorder_id / "artifacts" / "params.pkl"
    with model_path.open("rb") as f:
        return pickle.load(f)


def load_alpha158_features() -> tuple[pd.DataFrame, pd.Series]:
    qlib.init(provider_uri=PROVIDER, region="tw", expression_cache=None, dataset_cache=None)
    handler = Alpha158(
        instruments=MARKET,
        start_time=START,
        end_time=END,
        fit_start_time=START,
        fit_end_time=FIT_END,
    )
    raw = handler.fetch(col_set=DataHandlerLP.CS_RAW, data_key=DataHandlerLP.DK_R)
    return raw["feature"], raw["label"]["LABEL0"]


def rank_corr_matrix(x_rank: pd.DataFrame, y_rank: pd.Series) -> pd.Series:
    x = x_rank.to_numpy(dtype=float)
    y = y_rank.to_numpy(dtype=float)
    y_mask = ~np.isnan(y)
    x = x[y_mask]
    y = y[y_mask]
    y = y - y.mean()
    y_std = np.sqrt(np.sum(y * y))
    if y_std == 0 or x.shape[0] < 10:
        return pd.Series(np.nan, index=x_rank.columns)
    x_mean = np.nanmean(x, axis=0)
    x_centered = x - x_mean
    x_centered[np.isnan(x_centered)] = 0.0
    x_std = np.sqrt(np.sum(x_centered * x_centered, axis=0))
    denom = x_std * y_std
    num = np.dot(y, x_centered)
    out = np.full(x.shape[1], np.nan, dtype=float)
    ok = denom > 0
    out[ok] = num[ok] / denom[ok]
    return pd.Series(out, index=x_rank.columns)


def calc_daily_rank_ic_by_loop(features: pd.DataFrame, label: pd.Series) -> pd.DataFrame:
    data = features.copy()
    data["__label__"] = label
    rows = []
    dates = []
    for date, group in data.groupby(level="datetime", sort=True):
        group = group.droplevel("datetime")
        y = group.pop("__label__")
        valid_y = y.notna()
        if valid_y.sum() < 10 or y[valid_y].nunique(dropna=True) < 2:
            continue
        x_rank = group.loc[valid_y].rank(axis=0)
        y_rank = y.loc[valid_y].rank()
        rows.append(rank_corr_matrix(x_rank, y_rank))
        dates.append(pd.Timestamp(date))
    return pd.DataFrame(rows, index=pd.Index(dates, name="datetime"))


def summarize_rank_ic(daily_ric: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for segment, (start, end) in SEGMENTS.items():
        seg = daily_ric.loc[(daily_ric.index >= pd.Timestamp(start)) & (daily_ric.index <= pd.Timestamp(end))]
        for feature in daily_ric.columns:
            s = seg[feature].dropna()
            std = s.std()
            rows.append(
                {
                    "feature_name": feature,
                    "segment": segment,
                    "n_days": int(s.shape[0]),
                    "single_factor_rankic": float(s.mean()) if len(s) else np.nan,
                    "rankic_std": float(std) if len(s) else np.nan,
                    "rankic_ir": float(s.mean() / std) if len(s) and std else np.nan,
                    "rankic_positive_rate": float((s > 0).mean()) if len(s) else np.nan,
                }
            )
    return pd.DataFrame(rows)


def calc_importance(model, feature_names: list[str]) -> pd.DataFrame:
    gain = model.get_feature_importance(importance_type="gain").rename("gain")
    split = model.get_feature_importance(importance_type="split").rename("split")
    out = pd.concat([gain, split], axis=1).fillna(0.0).reset_index(names="feature_name")
    column_map = {f"Column_{i}": name for i, name in enumerate(feature_names)}
    out["model_feature_name"] = out["feature_name"]
    out["feature_name"] = out["feature_name"].map(lambda x: column_map.get(x, x))
    out["gain_rank"] = out["gain"].rank(method="min", ascending=False).astype(int)
    out["split_rank"] = out["split"].rank(method="min", ascending=False).astype(int)
    gain_sum = out["gain"].sum()
    split_sum = out["split"].sum()
    out["gain_share"] = out["gain"] / gain_sum if gain_sum else 0.0
    out["split_share"] = out["split"] / split_sum if split_sum else 0.0
    return out.sort_values(["gain_rank", "split_rank"])


def calc_corr_to_top(features: pd.DataFrame, top_features: list[str]) -> pd.DataFrame:
    test = features.loc[(slice(pd.Timestamp("2023-01-01"), pd.Timestamp("2025-06-30")), slice(None)), :]
    corr_frames = {top: [] for top in top_features}

    for _, group in test.groupby(level="datetime", sort=True):
        g = group.droplevel("datetime")
        if g.shape[0] < 10:
            continue
        ranks = g.rank(axis=0)
        for top in top_features:
            top_rank = ranks[top]
            if top_rank.notna().sum() < 10 or top_rank.nunique(dropna=True) < 2:
                continue
            corr_frames[top].append(rank_corr_matrix(ranks, top_rank))

    rows = []
    for feature in features.columns:
        row: dict[str, str | float] = {"feature_name": feature}
        max_abs = 0.0
        for top in top_features:
            if corr_frames[top]:
                mean_corr = float(pd.DataFrame(corr_frames[top])[feature].mean())
            else:
                mean_corr = np.nan
            row[f"corr_to_{top}"] = mean_corr
            if not np.isnan(mean_corr):
                max_abs = max(max_abs, abs(mean_corr))
        row["corr_to_top_3"] = max_abs
        rows.append(row)
    return pd.DataFrame(rows)


def write_report(out_dir: Path, merged: pd.DataFrame, top_features: list[str]) -> None:
    test = merged.sort_values("gain_rank")
    top = test.head(20)
    dead = test[(test["gain"] <= 0) | (test["split"] <= 0)]
    high_gain_weak_ic = test[(test["gain_rank"] <= 30) & (test["single_factor_rankic"].abs() < 0.005)]
    strong_ic_low_gain = test[(test["gain_rank"] > 80) & (test["single_factor_rankic"].abs() >= 0.015)]

    def table(df: pd.DataFrame, cols: list[str]) -> str:
        if df.empty:
            return "(empty)"
        display = df[cols].copy()
        for col in display.columns:
            if pd.api.types.is_float_dtype(display[col]):
                display[col] = display[col].map(lambda x: "" if pd.isna(x) else f"{x:.6f}")
            else:
                display[col] = display[col].map(lambda x: "" if pd.isna(x) else str(x))
        header = "| " + " | ".join(display.columns) + " |"
        sep = "| " + " | ".join(["---"] * len(display.columns)) + " |"
        rows = ["| " + " | ".join(row) + " |" for row in display.to_numpy(dtype=str)]
        return "\n".join([header, sep] + rows)

    lines = [
        "---",
        "created_at: 2026-05-27",
        "status: diagnostic_complete",
        "scope: alpha158_importance_tier0",
        "related_docs:",
        "  - docs/tw_audit/16_claude_audit_round_4_new_factor_strategy.md",
        "  - docs/tw_audit/13_yahoo_primary_baseline_report.md",
        "---",
        "",
        "# Alpha158 Importance Diagnostic",
        "",
        "## Scope",
        "",
        "This Tier 0 diagnostic explains the fixed Yahoo-only Alpha158 baseline. It uses provider `data_tw/experiments/yahoo_adjusted_primary/qlib_bin`, market `tw_liquid_dyn`, recorder `950741cfd5f14ee5a05464fec3e12e0a`, and data no later than 2025-06-30.",
        "",
        "No portfolio parameters were tuned, no candidate factors were added, and the frozen OOS beginning 2025-07-01 was not accessed.",
        "",
        "## Top Gain Features",
        "",
        table(
            top,
            [
                "feature_name",
                "gain_rank",
                "gain_share",
                "split_rank",
                "single_factor_rankic",
                "rankic_ir",
                "corr_to_top_3",
            ],
        ),
        "",
        "## Top-3 Gain Features",
        "",
        ", ".join(top_features),
        "",
        "## High Gain But Weak Single-Factor RankIC",
        "",
        table(
            high_gain_weak_ic.head(20),
            ["feature_name", "gain_rank", "gain_share", "single_factor_rankic", "rankic_ir", "corr_to_top_3"],
        ),
        "",
        "## Strong Single-Factor RankIC But Low Model Gain",
        "",
        table(
            strong_ic_low_gain.head(20),
            ["feature_name", "gain_rank", "gain_share", "single_factor_rankic", "rankic_ir", "corr_to_top_3"],
        ),
        "",
        "## Dead Weight Features",
        "",
        f"Features with zero gain or zero split count: {dead.shape[0]} / {test.shape[0]}.",
        "",
        "## Interpretation",
        "",
        "- Gain importance measures how the trained LightGBM baseline used a feature jointly with other features; single-factor RankIC measures standalone monotonic signal in the same fixed data split.",
        "- High gain with weak standalone RankIC suggests interaction or redundancy rather than a clean univariate alpha.",
        "- Strong standalone RankIC with low gain suggests potentially useful signal that the current model underuses, but it still requires paired tests before claiming improvement.",
        "- New factor work should avoid features highly correlated with the top gain cluster unless they add a distinct economic mechanism.",
        "",
        "## Artifacts",
        "",
        f"- `{out_dir / 'alpha158_feature_importance.csv'}`",
        f"- `{out_dir / 'alpha158_single_factor_rankic.csv'}`",
        f"- `{out_dir / 'alpha158_importance_rankic.csv'}`",
        f"- `{out_dir / 'alpha158_top3_correlation.csv'}`",
    ]
    (ROOT / "docs/tw_audit/16b_alpha158_importance_diagnostic.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose Alpha158 feature importance on Yahoo-only TW baseline.")
    parser.add_argument("--output-dir", default="data_tw/experiments/yahoo_primary_alpha158_importance")
    parser.add_argument("--recorder-id", default=RECORDER_ID)
    parser.add_argument("--experiment-id", default=EXPERIMENT_ID)
    args = parser.parse_args()

    out_dir = ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    model = load_baseline_model(args.recorder_id, args.experiment_id)
    features, label = load_alpha158_features()

    importance = calc_importance(model, list(features.columns))
    daily_ric = calc_daily_rank_ic_by_loop(features, label)
    rankic = summarize_rank_ic(daily_ric)
    test_rankic = rankic[rankic["segment"] == "test"].drop(columns=["segment"])

    top_features = importance.head(3)["feature_name"].tolist()
    corr = calc_corr_to_top(features, top_features)
    merged = importance.merge(test_rankic, on="feature_name", how="left").merge(corr, on="feature_name", how="left")
    merged = merged.sort_values(["gain_rank", "split_rank"])

    importance.to_csv(out_dir / "alpha158_feature_importance.csv", index=False)
    rankic.to_csv(out_dir / "alpha158_single_factor_rankic.csv", index=False)
    corr.to_csv(out_dir / "alpha158_top3_correlation.csv", index=False)
    merged.to_csv(out_dir / "alpha158_importance_rankic.csv", index=False)
    write_report(out_dir.relative_to(ROOT), merged, top_features)

    print(f"features={features.shape[1]}")
    print(f"rows={features.shape[0]}")
    print(f"top3={','.join(top_features)}")
    print(f"wrote {out_dir.relative_to(ROOT)}")
    print("wrote docs/tw_audit/16b_alpha158_importance_diagnostic.md")


if __name__ == "__main__":
    main()
