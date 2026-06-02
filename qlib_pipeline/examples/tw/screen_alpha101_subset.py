from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import qlib
from qlib.contrib.data.handler import Alpha158
from qlib.data.dataset.handler import DataHandlerLP
from qlib.data.dataset.loader import QlibDataLoader
from qlib.data.dataset.processor import DropnaLabel
from qlib.data.dataset import DataHandlerLP as BaseDataHandlerLP


ROOT = Path(__file__).resolve().parents[2]
PROVIDER = "data_tw/experiments/yahoo_adjusted_primary/qlib_bin"
MARKET = "tw_liquid_dyn"
START = "2015-05-04"
END = "2025-06-30"
FIT_END = "2020-12-31"
SEGMENTS = {
    "train": ("2015-05-04", "2020-12-31"),
    "valid": ("2021-01-01", "2022-12-31"),
    "test": ("2023-01-01", "2025-06-30"),
}


ALPHA101_SUBSET: list[tuple[str, str, str]] = [
    (
        "A101_002",
        "-1 * Corr(Rank(Delta(Log($volume + 1), 2), 6), Rank(($close - $open) / ($open + 1e-12), 6), 6)",
        "volume shock versus intraday return correlation",
    ),
    (
        "A101_003",
        "-1 * Corr(Rank($open, 10), Rank($volume, 10), 10)",
        "open-volume rolling rank correlation",
    ),
    (
        "A101_004",
        "-1 * Rank(Rank($low, 9), 9)",
        "low-price rolling rank decay proxy",
    ),
    (
        "A101_006",
        "-1 * Corr($open, $volume, 10)",
        "open-volume rolling correlation",
    ),
    (
        "A101_012",
        "Sign(Delta($volume, 1)) * (-1 * Delta($close, 1))",
        "volume direction times one-day reversal",
    ),
    (
        "A101_013",
        "-1 * Rank(Cov(Rank($close, 5), Rank($volume, 5), 5), 5)",
        "ranked price-volume covariance",
    ),
    (
        "A101_015",
        "-1 * Sum(Rank(Corr(Rank($high, 3), Rank($volume, 3), 3), 3), 3)",
        "summed high-volume rank correlation",
    ),
    (
        "A101_016",
        "-1 * Rank(Cov(Rank($high, 5), Rank($volume, 5), 5), 5)",
        "ranked high-volume covariance",
    ),
    (
        "A101_018",
        "-1 * Rank(Std(Abs($close - $open), 5) + ($close - $open) + Corr($close, $open, 10), 10)",
        "intraday spread volatility and close-open correlation",
    ),
    (
        "A101_020",
        "-1 * Rank($open - Ref($high, 1), 10) * Rank($open - Ref($close, 1), 10) * Rank($open - Ref($low, 1), 10)",
        "gap from prior high close low",
    ),
    (
        "A101_024",
        "If(Delta(Mean($close, 100), 100) / (Ref($close, 100) + 1e-12) <= 0.05, -1 * ($close - Min($close, 100)), -1 * Delta($close, 3))",
        "long trend conditional short reversal",
    ),
    (
        "A101_021",
        "If(Mean($close, 8) + Std($close, 8) < Mean($close, 2), -1, If(Mean($close, 2) < Mean($close, 8) - Std($close, 8), 1, If($volume / (Mean($volume, 20) + 1e-12) >= 1, 1, -1)))",
        "conditional mean-reversion and volume regime",
    ),
    (
        "A101_022",
        "-1 * Delta(Corr($high, $volume, 5), 5) * Rank(Std($close, 20), 20)",
        "change in high-volume correlation times volatility rank",
    ),
    (
        "A101_025",
        "Rank((-1 * ($close / Ref($close, 1) - 1)) * Mean($volume, 20) * $vwap * ($high - $close), 20)",
        "reversal weighted by ADV proxy and high-close gap",
    ),
    (
        "A101_026",
        "-1 * Max(Corr(Rank($volume, 5), Rank($high, 5), 5), 3)",
        "max recent ranked volume-high correlation",
    ),
    (
        "A101_033",
        "Rank(-1 + $open / ($close + 1e-12), 10)",
        "open-close ratio rank",
    ),
    (
        "A101_034",
        "Rank((1 - Rank(Std($close / Ref($close, 1) - 1, 2), 5)) + (1 - Rank(Delta($close, 1), 5)), 10)",
        "low short vol plus reversal rank",
    ),
    (
        "A101_035",
        "Rank($volume, 32) * (1 - Rank($close + $high - $low, 16)) * (1 - Rank($close / Ref($close, 1) - 1, 32))",
        "volume rank times price-location and return reversal",
    ),
    (
        "A101_041",
        "Power($high * $low, 0.5) - $vwap",
        "geometric high-low price minus vwap",
    ),
    (
        "A101_042",
        "Rank($vwap - $close, 10) / (Rank($vwap + $close, 10) + 1e-12)",
        "vwap-close relative rank",
    ),
    (
        "A101_043",
        "Rank($volume / (Mean($volume, 20) + 1e-12), 20) * Rank(-1 * Delta($close, 7), 8)",
        "volume acceleration times seven-day reversal",
    ),
    (
        "A101_044",
        "-1 * Corr($high, Rank($volume, 5), 5)",
        "high versus ranked volume correlation",
    ),
    (
        "A101_045",
        "-1 * Rank(Mean(Ref($close, 5), 20), 10) * Corr($close, $volume, 2) * Rank(Corr(Sum($close, 5), Sum($close, 20), 2), 10)",
        "lagged close rank times short price-volume and trend correlation",
    ),
    (
        "A101_053",
        "-1 * Delta((($close - $low) - ($high - $close)) / ($close - $low + 1e-12), 9)",
        "nine-day change in close location inside bar",
    ),
    (
        "A101_054",
        "-1 * (($low - $close) * Power($open, 5)) / (($low - $high) * Power($close, 5) + 1e-12)",
        "powered open-close-low-high bar shape",
    ),
    (
        "A101_101",
        "($close - $open) / ($high - $low + 0.001)",
        "intraday close-open location",
    ),
]


class Alpha101SubsetHandler(BaseDataHandlerLP):
    def __init__(self, instruments: str, start_time: str, end_time: str, fit_start_time: str, fit_end_time: str):
        fields = [expr for _, expr, _ in ALPHA101_SUBSET]
        names = [name for name, _, _ in ALPHA101_SUBSET]
        loader = {
            "class": "QlibDataLoader",
            "kwargs": {
                "config": {
                    "feature": (fields, names),
                    "label": (["Ref($close, -2)/Ref($close, -1) - 1"], ["LABEL0"]),
                },
                "freq": "day",
            },
        }
        super().__init__(
            instruments=instruments,
            start_time=start_time,
            end_time=end_time,
            data_loader=loader,
            learn_processors=[DropnaLabel()],
            infer_processors=[],
            process_type=DataHandlerLP.PTYPE_A,
        )


def rank_corr_matrix(x_rank: pd.DataFrame, y_rank: pd.Series) -> pd.Series:
    x = x_rank.to_numpy(dtype=float)
    y = y_rank.to_numpy(dtype=float)
    mask = ~np.isnan(y)
    x = x[mask]
    y = y[mask]
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


def calc_daily_rank_ic(features: pd.DataFrame, label: pd.Series) -> pd.DataFrame:
    data = features.copy()
    data["__label__"] = label
    rows = []
    dates = []
    for date, group in data.groupby(level="datetime", sort=True):
        group = group.droplevel("datetime")
        y = group.pop("__label__")
        valid = y.notna()
        if valid.sum() < 10 or y[valid].nunique(dropna=True) < 2:
            continue
        rows.append(rank_corr_matrix(group.loc[valid].rank(axis=0), y.loc[valid].rank()))
        dates.append(pd.Timestamp(date))
    return pd.DataFrame(rows, index=pd.Index(dates, name="datetime"))


def summarize_rank_ic(daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for segment, (start, end) in SEGMENTS.items():
        seg = daily.loc[(daily.index >= pd.Timestamp(start)) & (daily.index <= pd.Timestamp(end))]
        for factor in daily.columns:
            s = seg[factor].dropna()
            std = s.std()
            rows.append(
                {
                    "factor": factor,
                    "segment": segment,
                    "n_days": int(s.shape[0]),
                    "rank_ic_mean": float(s.mean()) if len(s) else np.nan,
                    "rank_ic_std": float(std) if len(s) else np.nan,
                    "rank_ic_ir": float(s.mean() / std) if len(s) and std else np.nan,
                    "positive_rate": float((s > 0).mean()) if len(s) else np.nan,
                }
            )
    return pd.DataFrame(rows)


def load_alpha101_subset() -> tuple[pd.DataFrame, pd.Series]:
    handler = Alpha101SubsetHandler(MARKET, START, END, START, FIT_END)
    raw = handler.fetch(col_set=DataHandlerLP.CS_RAW, data_key=DataHandlerLP.DK_R)
    return raw["feature"], raw["label"]["LABEL0"]


def load_alpha158_features() -> pd.DataFrame:
    handler = Alpha158(instruments=MARKET, start_time=START, end_time=END, fit_start_time=START, fit_end_time=FIT_END)
    raw = handler.fetch(col_set=DataHandlerLP.CS_RAW, data_key=DataHandlerLP.DK_R)
    return raw["feature"]


def calc_alpha158_corr(candidates: pd.DataFrame, alpha158: pd.DataFrame) -> pd.DataFrame:
    test_idx = (slice(pd.Timestamp("2023-01-01"), pd.Timestamp("2025-06-30")), slice(None))
    cand_test = candidates.loc[test_idx, :]
    alpha_test = alpha158.loc[test_idx, :]
    rows = []
    for factor in cand_test.columns:
        daily = []
        best_feature_daily = []
        for date, xg in cand_test[[factor]].groupby(level="datetime", sort=True):
            if date not in alpha_test.index.get_level_values("datetime"):
                continue
            x = xg.droplevel("datetime")[factor]
            ag = alpha_test.xs(date, level="datetime")
            joined = ag.join(x, how="inner")
            y = joined.pop(factor)
            valid = y.notna()
            if valid.sum() < 10 or y[valid].nunique(dropna=True) < 2:
                continue
            corr = rank_corr_matrix(joined.loc[valid].rank(axis=0), y.loc[valid].rank())
            daily.append(corr.abs().max())
            if corr.notna().any():
                best_feature_daily.append(corr.abs().idxmax())
        rows.append(
            {
                "factor": factor,
                "max_abs_corr_to_alpha158": float(np.nanmean(daily)) if daily else np.nan,
                "most_common_nearest_alpha158": pd.Series(best_feature_daily).mode().iloc[0] if best_feature_daily else "",
            }
        )
    return pd.DataFrame(rows)


def write_report(out_dir: Path, merged: pd.DataFrame) -> None:
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

    ranked = merged.sort_values(["pass_screen", "abs_test_rank_ic"], ascending=[False, False])
    lines = [
        "---",
        "created_at: 2026-05-27",
        "status: screening_complete",
        "scope: alpha101_subset_single_factor_screen",
        "related_docs:",
        "  - docs/tw_audit/16_claude_audit_round_4_new_factor_strategy.md",
        "  - docs/tw_audit/16b_alpha158_importance_diagnostic.md",
        "---",
        "",
        "# Alpha101 Subset Screening Report",
        "",
        "## Scope",
        "",
        "This is a narrow Tier 1 screen of a hand-mapped Alpha101-style OHLCV subset. It does not add a handler to the baseline model, does not run portfolio backtests, does not tune strategy parameters, and does not access data after 2025-06-30.",
        "",
        "The formulas are Alpha101-inspired mappings using currently available OHLCV fields. Formulas requiring unavailable fundamentals or market cap are excluded from this first pass.",
        "",
        "## Screen Rules",
        "",
        "- Candidate passes only if `abs(test RankIC) >= 0.01` and `max_abs_corr_to_alpha158 < 0.5`.",
        "- Passing this screen is not evidence of baseline improvement; it only marks candidates for possible paired tests and ablation.",
        "- Any future model ablation still treats IC/RankIC improvement below 0.005 as noise unless paired tests and rolling robustness agree.",
        "",
        "## Results",
        "",
        table(
            ranked,
            [
                "factor",
                "test_rank_ic",
                "test_rank_ic_ir",
                "valid_rank_ic",
                "max_abs_corr_to_alpha158",
                "nearest_alpha158",
                "pass_screen",
                "note",
            ],
        ),
        "",
        "## Interpretation",
        "",
        "- This screen is deliberately conservative because the current Alpha158 baseline is weak and many Alpha101-style price/volume formulas overlap with Alpha158 rolling statistics.",
        "- Candidates with high Alpha158 correlation should not be promoted into a combined handler without a distinct economic rationale.",
        "- The next step is to inspect passed candidates, if any, then run a small fixed-parameter ablation with paired daily-return tests.",
        "",
        "## Artifacts",
        "",
        f"- `{out_dir / 'alpha101_subset_daily_rankic.csv'}`",
        f"- `{out_dir / 'alpha101_subset_summary.csv'}`",
        f"- `{out_dir / 'alpha101_subset_alpha158_corr.csv'}`",
        f"- `{out_dir / 'alpha101_subset_screen.csv'}`",
    ]
    (ROOT / "docs/tw_audit/16c_alpha101_screening_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Screen Alpha101-style OHLCV subset on Yahoo-only TW data.")
    parser.add_argument("--output-dir", default="data_tw/experiments/yahoo_primary_alpha101_subset_screen")
    args = parser.parse_args()
    out_dir = ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    qlib.init(provider_uri=PROVIDER, region="tw", expression_cache=None, dataset_cache=None)
    candidate_features, label = load_alpha101_subset()
    alpha158_features = load_alpha158_features()

    daily = calc_daily_rank_ic(candidate_features, label)
    summary = summarize_rank_ic(daily)
    corr = calc_alpha158_corr(candidate_features, alpha158_features)

    pivot = summary.pivot(index="factor", columns="segment", values="rank_ic_mean").reset_index()
    ir_pivot = summary.pivot(index="factor", columns="segment", values="rank_ic_ir").reset_index()
    merged = pivot.merge(ir_pivot[["factor", "test"]].rename(columns={"test": "test_rank_ic_ir"}), on="factor")
    merged = merged.rename(columns={"train": "train_rank_ic", "valid": "valid_rank_ic", "test": "test_rank_ic"})
    merged["abs_test_rank_ic"] = merged["test_rank_ic"].abs()
    merged = merged.merge(corr, on="factor", how="left")
    meta = pd.DataFrame(
        [{"factor": name, "expression": expr, "note": note} for name, expr, note in ALPHA101_SUBSET]
    )
    merged = merged.merge(meta, on="factor", how="left")
    merged = merged.rename(columns={"most_common_nearest_alpha158": "nearest_alpha158"})
    merged["pass_screen"] = (merged["abs_test_rank_ic"] >= 0.01) & (merged["max_abs_corr_to_alpha158"] < 0.5)
    merged = merged.sort_values(["pass_screen", "abs_test_rank_ic"], ascending=[False, False])

    daily.to_csv(out_dir / "alpha101_subset_daily_rankic.csv")
    summary.to_csv(out_dir / "alpha101_subset_summary.csv", index=False)
    corr.to_csv(out_dir / "alpha101_subset_alpha158_corr.csv", index=False)
    merged.to_csv(out_dir / "alpha101_subset_screen.csv", index=False)
    write_report(out_dir.relative_to(ROOT), merged)

    print(f"candidates={candidate_features.shape[1]}")
    print(f"rows={candidate_features.shape[0]}")
    print(f"pass_screen={int(merged['pass_screen'].sum())}")
    print(f"wrote {out_dir.relative_to(ROOT)}")
    print("wrote docs/tw_audit/16c_alpha101_screening_report.md")


if __name__ == "__main__":
    main()
