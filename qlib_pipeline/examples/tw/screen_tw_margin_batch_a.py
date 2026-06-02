#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import qlib
from qlib.data import D

from screen_tw_academic_factors import (
    END,
    MARKET,
    PROVIDER,
    ROOT,
    SEGMENTS,
    START,
    calc_daily_ic,
    fetch_alpha158,
    fetch_raw,
    summarize_ic,
)

SOURCE_DIR = ROOT / "data_tw/experiments/tw_margin_batch_a_materialized/features_by_symbol"
OUT_DIR_DEFAULT = "data_tw/experiments/tw_margin_batch_a_screen"
REPORT_PATH = ROOT / "docs/tw_audit/40_tw_margin_batch_a_screening_report.md"
FACTORS = ["TW_MARGIN_UTIL", "TW_MARGIN_DELTA_5D"]
FIELD_MAP = {
    "TW_MARGIN_UTIL": "tw_margin_util",
    "TW_MARGIN_DELTA_5D": "tw_margin_delta_5d",
}


def load_calendar(provider: Path) -> list[pd.Timestamp]:
    return pd.to_datetime(pd.read_csv(provider / "calendars/day.txt", header=None).iloc[:, 0]).tolist()


def load_source_features() -> pd.DataFrame:
    frames = []
    for path in sorted(SOURCE_DIR.glob("TW*.csv")):
        df = pd.read_csv(
            path,
            usecols=["qlib_symbol", "date", "TW_MARGIN_UTIL", "TW_MARGIN_DELTA_5D"],
            parse_dates=["date"],
        )
        frames.append(df.rename(columns={"qlib_symbol": "instrument", "date": "datetime"}))
    if not frames:
        raise FileNotFoundError(f"no materialized source CSVs under {SOURCE_DIR}")
    data = pd.concat(frames, ignore_index=True)
    idx = pd.MultiIndex.from_frame(data[["datetime", "instrument"]])
    return pd.DataFrame({factor: data[factor].to_numpy(dtype=float) for factor in FACTORS}, index=idx).sort_index()


def write_feature_bins(source: pd.DataFrame, provider: Path) -> pd.DataFrame:
    calendar = load_calendar(provider)
    cal_index = pd.Index(calendar)
    scoped_dates = cal_index[(cal_index >= pd.Timestamp(START)) & (cal_index <= pd.Timestamp(END))]
    if scoped_dates.empty:
        raise ValueError("no provider calendar dates in requested scope")
    date_index = calendar.index(scoped_dates[0])
    rows = []
    for instrument, group in source.groupby(level="instrument", sort=True):
        g = group.droplevel("instrument").sort_index().reindex(scoped_dates)
        feature_dir = provider / "features" / instrument.lower()
        feature_dir.mkdir(parents=True, exist_ok=True)
        for factor in FACTORS:
            field = FIELD_MAP[factor]
            out_path = feature_dir / f"{field}.day.bin"
            values = g[factor].to_numpy(dtype=np.float32)
            np.hstack([np.array([date_index], dtype=np.float32), values]).astype("<f").tofile(out_path)
            finite = np.isfinite(values)
            rows.append(
                {
                    "instrument": instrument,
                    "factor": factor,
                    "field": field,
                    "path": str(out_path.relative_to(ROOT)),
                    "start": scoped_dates[0].strftime("%Y-%m-%d"),
                    "end": scoped_dates[-1].strftime("%Y-%m-%d"),
                    "n_values": int(values.shape[0]),
                    "finite_values": int(finite.sum()),
                    "finite_share": float(finite.mean()) if len(finite) else np.nan,
                }
            )
    return pd.DataFrame(rows)


def validate_bins(source: pd.DataFrame, provider: Path, sample_n: int) -> pd.DataFrame:
    qlib.init(provider_uri=str(provider), region="tw", expression_cache=None, dataset_cache=None)
    finite = source.dropna(how="all").reset_index().sort_values(["datetime", "instrument"])
    positions = np.linspace(0, len(finite) - 1, min(sample_n, len(finite)), dtype=int)
    sample = finite.iloc[positions]
    rows = []
    for _, row in sample.iterrows():
        instrument = str(row["instrument"])
        date = pd.Timestamp(row["datetime"])
        fields = [f"${FIELD_MAP[factor]}" for factor in FACTORS]
        loaded = D.features([instrument], fields, start_time=date, end_time=date, freq="day")
        for factor, field in zip(FACTORS, fields, strict=True):
            expected = row[factor]
            actual = np.nan if loaded.empty else float(loaded.iloc[0][field])
            expected_f32 = float(np.float32(expected)) if pd.notna(expected) else np.nan
            rows.append(
                {
                    "instrument": instrument,
                    "datetime": date.strftime("%Y-%m-%d"),
                    "factor": factor,
                    "source_value": expected,
                    "source_value_float32": expected_f32,
                    "qlib_value": actual,
                    "abs_diff_vs_float32": abs(actual - expected_f32) if np.isfinite(actual) and np.isfinite(expected_f32) else np.nan,
                    "pass_float32_tolerance_1e_8": bool(np.isfinite(actual) and np.isfinite(expected_f32) and abs(actual - expected_f32) < 1e-8),
                }
            )
    return pd.DataFrame(rows)


def build_screen_summary(segment_ic: pd.DataFrame, corr: pd.DataFrame) -> pd.DataFrame:
    ric = segment_ic[segment_ic["metric"] == "rank_ic"]
    mean_pivot = ric.pivot(index="factor", columns="segment", values="mean").reset_index()
    ir_pivot = ric.pivot(index="factor", columns="segment", values="ir").reset_index()
    out = mean_pivot.rename(
        columns={
            "train": "train_rank_ic",
            "valid": "valid_rank_ic",
            "test": "test_rank_ic",
            "test_2023": "test_2023_rank_ic",
            "test_2024": "test_2024_rank_ic",
            "test_2025h1": "test_2025h1_rank_ic",
        }
    )
    out = out.merge(ir_pivot[["factor", "test"]].rename(columns={"test": "test_rank_ic_ir"}), on="factor", how="left")
    out = out.merge(corr, on="factor", how="left")
    segment_cols = ["valid_rank_ic", "test_rank_ic", "test_2023_rank_ic", "test_2024_rank_ic", "test_2025h1_rank_ic"]
    out["expected_raw_direction"] = "negative"
    out["direction_stable_negative"] = out[segment_cols].apply(lambda r: bool(r.dropna().lt(0).all()), axis=1)
    out["abs_test_rank_ic"] = out["test_rank_ic"].abs()

    def decision(row: pd.Series) -> str:
        if row.get("corr_gate") in {"reject_hard_top20_corr", "reject_soft_all158_corr"}:
            return row.get("corr_gate")
        if pd.isna(row.get("test_rank_ic")) or abs(row.get("test_rank_ic")) < 0.01:
            return "reject_rankic_below_0.01"
        if row.get("test_rank_ic") >= 0:
            return "reject_wrong_raw_direction"
        if not row.get("direction_stable_negative", False):
            return "reject_direction_unstable"
        return "pass_single_factor_screen"

    out["screen_decision"] = out.apply(decision, axis=1)
    return out


def calc_conditional_std60_ic(candidates: pd.DataFrame, label: pd.Series, alpha158: pd.DataFrame, quantiles: int = 5) -> pd.DataFrame:
    data = candidates[["TW_MARGIN_UTIL"]].copy()
    data["LABEL0"] = label.reindex(data.index)
    data["STD60"] = alpha158["STD60"].reindex(data.index)
    rows = []
    for date, group in data.groupby(level="datetime", sort=True):
        g = group.droplevel("datetime").dropna()
        if g.shape[0] < 30 or g["STD60"].nunique() < quantiles:
            continue
        try:
            bucket = pd.qcut(g["STD60"].rank(method="first"), quantiles, labels=False)
        except ValueError:
            continue
        demeaned_factor = g["TW_MARGIN_UTIL"] - g.groupby(bucket)["TW_MARGIN_UTIL"].transform("mean")
        demeaned_label = g["LABEL0"] - g.groupby(bucket)["LABEL0"].transform("mean")
        ok = demeaned_factor.notna() & demeaned_label.notna()
        if ok.sum() < 10 or demeaned_factor[ok].nunique(dropna=True) < 2 or demeaned_label[ok].nunique(dropna=True) < 2:
            continue
        rows.append(
            {
                "date": pd.Timestamp(date),
                "factor": "TW_MARGIN_UTIL",
                "control": "STD60_quantile5_demean",
                "n": int(ok.sum()),
                "rank_ic": float(demeaned_factor[ok].corr(demeaned_label[ok], method="spearman")),
            }
        )
    return pd.DataFrame(rows)


def summarize_conditional_ic(daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for segment, (start, end) in SEGMENTS.items():
        seg = daily[(daily["date"] >= pd.Timestamp(start)) & (daily["date"] <= pd.Timestamp(end))]
        s = seg["rank_ic"].dropna()
        rows.append(
            {
                "factor": "TW_MARGIN_UTIL",
                "control": "STD60_quantile5_demean",
                "segment": segment,
                "n_days": int(s.shape[0]),
                "mean_rank_ic": float(s.mean()) if len(s) else np.nan,
                "std": float(s.std(ddof=1)) if len(s) > 1 else np.nan,
                "ir": float(s.mean() / s.std(ddof=1)) if len(s) > 1 and s.std(ddof=1) > 0 else np.nan,
                "positive_rate": float((s > 0).mean()) if len(s) else np.nan,
                "avg_n": float(seg["n"].mean()) if len(seg) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def fmt_value(x: object) -> str:
    if pd.isna(x):
        return ""
    if isinstance(x, (float, np.floating)):
        return f"{x:.6f}"
    return str(x)


def table(df: pd.DataFrame, cols: list[str]) -> list[str]:
    if df.empty:
        return ["(empty)"]
    display = df[cols].copy()
    for col in display.columns:
        display[col] = display[col].map(fmt_value)
    lines = ["| " + " | ".join(display.columns) + " |", "| " + " | ".join(["---"] * len(display.columns)) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in display.to_numpy(dtype=str))
    return lines


def write_report(
    out_dir: Path,
    manifest: pd.DataFrame,
    validation: pd.DataFrame,
    screen: pd.DataFrame,
    segment_ic: pd.DataFrame,
    corr_detail: pd.DataFrame,
    conditional_summary: pd.DataFrame,
) -> None:
    rank_ic = segment_ic[segment_ic["metric"] == "rank_ic"]
    lines = [
        "---",
        "created_at: 2026-05-28",
        "status: margin_batch_a_screen_ready_for_audit",
        "scope: phase_d6_margin_batch_a_single_factor_screen",
        "related_docs:",
        "  - docs/tw_audit/39_tw_margin_batch_a_materialization_report.md",
        "  - docs/tw_audit/40_claude_audit_round_20_margin_batch_a_materialization.md",
        "script:",
        "  - examples/tw/screen_tw_margin_batch_a.py",
        "---",
        "",
        "# TW Margin Batch A Single-Factor Screen",
        "",
        "## Scope",
        "",
        "This report executes Phase D.6 for Batch A only. It converts the already validated CSV materialized features into Qlib bin files, validates Qlib reads, runs single-factor IC screening for `TW_MARGIN_UTIL` and `TW_MARGIN_DELTA_5D`, and adds the PA-52 `STD60` conditional IC diagnostic for `TW_MARGIN_UTIL`.",
        "",
        "It does not run ablation, strategy backtests, handler promotion, Batch B short-side factors, or strategy tuning.",
        "",
        "## Qlib Bin Materialization",
        "",
    ]
    manifest_summary = manifest.groupby("factor", as_index=False).agg(
        instruments=("instrument", "nunique"),
        finite_values=("finite_values", "sum"),
        n_values=("n_values", "sum"),
        mean_finite_share=("finite_share", "mean"),
    )
    lines.extend(table(manifest_summary, ["factor", "instruments", "finite_values", "n_values", "mean_finite_share"]))
    lines += ["", "Validation sample:", ""]
    val_summary = validation.groupby("factor", as_index=False).agg(
        samples=("pass_float32_tolerance_1e_8", "size"),
        passes=("pass_float32_tolerance_1e_8", "sum"),
        max_abs_diff_vs_float32=("abs_diff_vs_float32", "max"),
    )
    lines.extend(table(val_summary, ["factor", "samples", "passes", "max_abs_diff_vs_float32"]))
    lines += ["", "## Six-Segment RankIC", ""]
    lines.extend(table(rank_ic, ["factor", "segment", "n_days", "mean", "std", "ir", "positive_rate", "avg_n", "avg_coverage"]))
    lines += ["", "## Alpha158 Correlation Gate", ""]
    lines.extend(table(screen, ["factor", "max_abs_corr_top20", "nearest_top20_alpha158", "max_abs_corr_all158", "nearest_all158_alpha158", "corr_gate"]))
    lines += ["", "## PA-52 STD60 Conditional IC", ""]
    lines.extend(table(conditional_summary, ["factor", "control", "segment", "n_days", "mean_rank_ic", "ir", "positive_rate", "avg_n"]))
    lines += ["", "## Screen Decision", ""]
    lines.extend(
        table(
            screen,
            [
                "factor",
                "valid_rank_ic",
                "test_rank_ic",
                "test_2023_rank_ic",
                "test_2024_rank_ic",
                "test_2025h1_rank_ic",
                "expected_raw_direction",
                "direction_stable_negative",
                "abs_test_rank_ic",
                "screen_decision",
            ],
        )
    )
    lines += [
        "",
        "## Nearest Alpha158 Features",
        "",
    ]
    lines.extend(table(corr_detail.head(20), ["factor", "alpha158_feature", "mean_spearman_corr", "abs_mean_spearman_corr", "is_top20_gain"]))
    lines += [
        "",
        "## Artifacts",
        "",
        f"- `{out_dir / 'margin_batch_a_bin_manifest.csv'}`",
        f"- `{out_dir / 'margin_batch_a_bin_validation.csv'}`",
        f"- `{out_dir / 'margin_batch_a_daily_ic.csv'}`",
        f"- `{out_dir / 'margin_batch_a_segment_ic.csv'}`",
        f"- `{out_dir / 'margin_batch_a_screen.csv'}`",
        f"- `{out_dir / 'margin_batch_a_alpha158_corr.csv'}`",
        f"- `{out_dir / 'margin_batch_a_alpha158_corr_detail.csv'}`",
        f"- `{out_dir / 'margin_util_std60_conditional_daily_ic.csv'}`",
        f"- `{out_dir / 'margin_util_std60_conditional_segment_ic.csv'}`",
        "",
        "## Next Action",
        "",
        "Request Claude review of this screening report before any ablation or Batch B short-side work.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TW margin Batch A Qlib bin materialization and single-factor IC screen.")
    parser.add_argument("--output-dir", default=OUT_DIR_DEFAULT)
    parser.add_argument("--sample-n", type=int, default=20)
    args = parser.parse_args()

    out_dir = ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    provider = ROOT / PROVIDER

    source = load_source_features()
    manifest = write_feature_bins(source, provider)
    validation = validate_bins(source, provider, args.sample_n)

    features, label = fetch_raw()
    candidates = source.reindex(label.index)[FACTORS]
    alpha158 = fetch_alpha158()
    daily_ic = calc_daily_ic(candidates, label, FACTORS)
    segment_ic = summarize_ic(daily_ic, FACTORS)
    from screen_tw_academic_factors import calc_alpha158_corr

    corr, corr_detail = calc_alpha158_corr(candidates, alpha158, FACTORS)
    screen = build_screen_summary(segment_ic, corr)
    conditional_daily = calc_conditional_std60_ic(candidates, label, alpha158)
    conditional_summary = summarize_conditional_ic(conditional_daily)

    manifest.to_csv(out_dir / "margin_batch_a_bin_manifest.csv", index=False)
    validation.to_csv(out_dir / "margin_batch_a_bin_validation.csv", index=False)
    daily_ic.to_csv(out_dir / "margin_batch_a_daily_ic.csv", index=False)
    segment_ic.to_csv(out_dir / "margin_batch_a_segment_ic.csv", index=False)
    corr.to_csv(out_dir / "margin_batch_a_alpha158_corr.csv", index=False)
    corr_detail.to_csv(out_dir / "margin_batch_a_alpha158_corr_detail.csv", index=False)
    screen.to_csv(out_dir / "margin_batch_a_screen.csv", index=False)
    conditional_daily.to_csv(out_dir / "margin_util_std60_conditional_daily_ic.csv", index=False)
    conditional_summary.to_csv(out_dir / "margin_util_std60_conditional_segment_ic.csv", index=False)
    write_report(out_dir.relative_to(ROOT), manifest, validation, screen, segment_ic, corr_detail, conditional_summary)

    print(f"bin_fields={len(manifest)}")
    print(f"validation_pass={bool(validation['pass_float32_tolerance_1e_8'].all())}")
    for _, row in screen.iterrows():
        print(f"{row['factor']} test_rank_ic={row['test_rank_ic']:.6f} decision={row['screen_decision']}")
    cond_test = conditional_summary[conditional_summary["segment"] == "test"]
    if not cond_test.empty:
        print(f"TW_MARGIN_UTIL conditional_test_rank_ic={cond_test['mean_rank_ic'].iloc[0]:.6f}")
    print(f"wrote {out_dir.relative_to(ROOT)}")
    print(f"wrote {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
