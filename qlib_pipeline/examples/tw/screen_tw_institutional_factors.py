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
    PROVIDER,
    ROOT,
    SEGMENTS,
    START,
    calc_alpha158_corr,
    calc_daily_ic,
    fetch_alpha158,
    fetch_raw,
    summarize_ic,
)

SOURCE_DIR = ROOT / "data_tw/experiments/tw_institutional_factors_materialized/features_by_symbol"
MATERIALIZED_DIR = ROOT / "data_tw/experiments/tw_institutional_factors_materialized"
OUT_DIR_DEFAULT = "data_tw/experiments/tw_institutional_factor_screen"
REPORT_PATH = ROOT / "docs/tw_audit/46_tw_institutional_screening_report.md"
FACTORS = ["TW_FOREIGN_NET_VOL", "TW_TRUST_NET_PX", "TW_FOREIGN_PERSIST_5D", "TW_INST_CONSENSUS"]
FIELD_MAP = {
    "TW_FOREIGN_NET_VOL": "tw_foreign_net_vol",
    "TW_TRUST_NET_PX": "tw_trust_net_px",
    "TW_FOREIGN_PERSIST_5D": "tw_foreign_persist_5d",
    "TW_INST_CONSENSUS": "tw_inst_consensus",
}
FACTOR_PRIORITY = {
    "TW_FOREIGN_NET_VOL": 1,
    "TW_TRUST_NET_PX": 2,
    "TW_FOREIGN_PERSIST_5D": 3,
    "TW_INST_CONSENSUS": 4,
}
EXPECTED_DIRECTION = {factor: "positive" for factor in FACTORS}


def load_calendar(provider: Path) -> list[pd.Timestamp]:
    return pd.to_datetime(pd.read_csv(provider / "calendars/day.txt", header=None).iloc[:, 0]).tolist()


def load_source_features() -> pd.DataFrame:
    frames = []
    usecols = ["qlib_symbol", "date", *FACTORS]
    for path in sorted(SOURCE_DIR.glob("TW*.csv")):
        df = pd.read_csv(path, usecols=usecols, parse_dates=["date"])
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
    rank_ic = segment_ic[segment_ic["metric"] == "rank_ic"]
    raw_ic = segment_ic[segment_ic["metric"] == "ic"]
    rank_mean = rank_ic.pivot(index="factor", columns="segment", values="mean").reset_index()
    rank_ir = rank_ic.pivot(index="factor", columns="segment", values="ir").reset_index()
    raw_mean = raw_ic.pivot(index="factor", columns="segment", values="mean").reset_index()
    out = rank_mean.rename(
        columns={
            "train": "train_rank_ic",
            "valid": "valid_rank_ic",
            "test": "test_rank_ic",
            "test_2023": "test_2023_rank_ic",
            "test_2024": "test_2024_rank_ic",
            "test_2025h1": "test_2025h1_rank_ic",
        }
    )
    out = out.merge(raw_mean[["factor", "test"]].rename(columns={"test": "test_ic"}), on="factor", how="left")
    out = out.merge(rank_ir[["factor", "test"]].rename(columns={"test": "test_rank_ic_ir"}), on="factor", how="left")
    out = out.merge(corr, on="factor", how="left")
    segment_cols = ["valid_rank_ic", "test_rank_ic", "test_2023_rank_ic", "test_2024_rank_ic", "test_2025h1_rank_ic"]
    out["expected_raw_direction"] = out["factor"].map(EXPECTED_DIRECTION)
    out["positive_direction_count_5"] = out[segment_cols].apply(lambda r: int(r.dropna().gt(0).sum()), axis=1)
    out["direction_stable_positive_4of5"] = out["positive_direction_count_5"] >= 4
    out["abs_test_rank_ic"] = out["test_rank_ic"].abs()
    out["priority"] = out["factor"].map(FACTOR_PRIORITY)

    def decision(row: pd.Series) -> str:
        if row.get("corr_gate") in {"reject_hard_top20_corr", "reject_soft_all158_corr"}:
            return row.get("corr_gate")
        if pd.isna(row.get("test_rank_ic")) or abs(row.get("test_rank_ic")) < 0.01:
            return "reject_rankic_below_0.01"
        if row.get("test_rank_ic") <= 0:
            return "reject_wrong_raw_direction"
        if not row.get("direction_stable_positive_4of5", False):
            return "reject_direction_unstable"
        return "pass_single_factor_screen"

    out["screen_decision"] = out.apply(decision, axis=1)
    return out.sort_values("priority").reset_index(drop=True)


def build_pa56_decision(screen: pd.DataFrame, pa56_corr: pd.DataFrame) -> pd.DataFrame:
    foreign = screen[screen["factor"].eq("TW_FOREIGN_NET_VOL")]
    consensus = screen[screen["factor"].eq("TW_INST_CONSENSUS")]
    corr = float(pa56_corr["mean_spearman_corr"].iloc[0]) if not pa56_corr.empty and "mean_spearman_corr" in pa56_corr.columns else np.nan
    if foreign.empty or consensus.empty:
        decision = "missing_required_factor"
        ratio = np.nan
        eligible = False
    else:
        f_pass = foreign["screen_decision"].iloc[0] == "pass_single_factor_screen"
        c_pass = consensus["screen_decision"].iloc[0] == "pass_single_factor_screen"
        f_abs = abs(float(foreign["test_rank_ic"].iloc[0])) if pd.notna(foreign["test_rank_ic"].iloc[0]) else np.nan
        c_abs = abs(float(consensus["test_rank_ic"].iloc[0])) if pd.notna(consensus["test_rank_ic"].iloc[0]) else np.nan
        ratio = c_abs / f_abs if np.isfinite(f_abs) and f_abs > 0 and np.isfinite(c_abs) else np.nan
        if f_pass and c_pass and np.isfinite(ratio) and ratio <= 1.5:
            decision = "prefer_foreign_net_vol_only"
            eligible = False
        elif f_pass and c_pass and np.isfinite(ratio) and ratio > 1.5:
            decision = "consensus_materially_stronger_allow_review"
            eligible = True
        elif c_pass and not f_pass:
            decision = "foreign_failed_consensus_may_proceed_to_review"
            eligible = True
        else:
            decision = "consensus_not_ablation_candidate"
            eligible = False
    return pd.DataFrame(
        [
            {
                "left": "TW_INST_CONSENSUS",
                "right": "TW_FOREIGN_NET_VOL",
                "mean_spearman_corr": corr,
                "consensus_abs_rankic_vs_foreign_abs_rankic": ratio,
                "consensus_ablation_eligible_under_pa56": eligible,
                "pa56_decision": decision,
            }
        ]
    )


def load_materialization_reference(filename: str) -> pd.DataFrame:
    path = MATERIALIZED_DIR / filename
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


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
    pa56_decision: pd.DataFrame,
    momentum: pd.DataFrame,
) -> None:
    rank_ic = segment_ic[segment_ic["metric"] == "rank_ic"]
    raw_ic = segment_ic[segment_ic["metric"] == "ic"]
    manifest_summary = manifest.groupby("factor", as_index=False).agg(
        instruments=("instrument", "nunique"),
        finite_values=("finite_values", "sum"),
        n_values=("n_values", "sum"),
        mean_finite_share=("finite_share", "mean"),
    )
    val_summary = validation.groupby("factor", as_index=False).agg(
        samples=("pass_float32_tolerance_1e_8", "size"),
        passes=("pass_float32_tolerance_1e_8", "sum"),
        max_abs_diff_vs_float32=("abs_diff_vs_float32", "max"),
    )
    lines = [
        "---",
        "created_at: 2026-05-29",
        "status: institutional_screen_ready_for_audit",
        "scope: phase_e5_institutional_single_factor_screen",
        "related_docs:",
        "  - docs/tw_audit/45_tw_institutional_materialization_report.md",
        "  - docs/tw_audit/46_claude_audit_round_26_institutional_materialization.md",
        "script:",
        "  - examples/tw/screen_tw_institutional_factors.py",
        "---",
        "",
        "# TW Institutional Single-Factor Screen",
        "",
        "## Scope",
        "",
        "This report executes Phase E.5 only. It converts the four institutional materialized CSV factors into Qlib bin fields, validates Qlib reads, runs single-factor IC screening, independently recomputes Alpha158 correlation gates, and applies the PA-56 duplicate-factor rule.",
        "",
        "It does not run ablation, strategy backtests, handler promotion, or strategy tuning.",
        "",
        "## Qlib Bin Materialization",
        "",
    ]
    lines.extend(table(manifest_summary, ["factor", "instruments", "finite_values", "n_values", "mean_finite_share"]))
    lines += ["", "Validation sample:", ""]
    lines.extend(table(val_summary, ["factor", "samples", "passes", "max_abs_diff_vs_float32"]))
    lines += ["", "## Six-Segment RankIC", ""]
    lines.extend(table(rank_ic, ["factor", "segment", "n_days", "mean", "std", "ir", "positive_rate", "avg_n", "avg_coverage"]))
    lines += ["", "## Test IC And RankIC", ""]
    lines.extend(table(screen, ["factor", "priority", "test_ic", "test_rank_ic", "test_rank_ic_ir", "abs_test_rank_ic"]))
    lines += ["", "## Alpha158 Correlation Gate", ""]
    lines.extend(table(screen, ["factor", "max_abs_corr_top20", "nearest_top20_alpha158", "max_abs_corr_all158", "nearest_all158_alpha158", "corr_gate"]))
    lines += ["", "## Momentum Overlap", ""]
    if not momentum.empty:
        pivot = momentum.pivot(index="factor", columns="alpha158_feature", values="mean_spearman_corr").reset_index()
        cols = ["factor", *[c for c in ["KMID", "ROC5", "ROC10", "MOM"] if c in pivot.columns]]
        lines.extend(table(pivot, cols))
    else:
        lines.append("(empty)")
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
                "positive_direction_count_5",
                "abs_test_rank_ic",
                "screen_decision",
            ],
        )
    )
    lines += ["", "## PA-56 Decision", ""]
    lines.extend(
        table(
            pa56_decision,
            [
                "left",
                "right",
                "mean_spearman_corr",
                "consensus_abs_rankic_vs_foreign_abs_rankic",
                "consensus_ablation_eligible_under_pa56",
                "pa56_decision",
            ],
        )
    )
    lines += ["", "## Nearest Alpha158 Features", ""]
    lines.extend(table(corr_detail.head(24), ["factor", "alpha158_feature", "mean_spearman_corr", "abs_mean_spearman_corr", "is_top20_gain"]))
    lines += [
        "",
        "## Artifacts",
        "",
        f"- `{out_dir / 'institutional_bin_manifest.csv'}`",
        f"- `{out_dir / 'institutional_bin_validation.csv'}`",
        f"- `{out_dir / 'institutional_daily_ic.csv'}`",
        f"- `{out_dir / 'institutional_segment_ic.csv'}`",
        f"- `{out_dir / 'institutional_screen.csv'}`",
        f"- `{out_dir / 'institutional_alpha158_corr.csv'}`",
        f"- `{out_dir / 'institutional_alpha158_corr_detail.csv'}`",
        f"- `{out_dir / 'institutional_momentum_overlap_inherited.csv'}`",
        f"- `{out_dir / 'institutional_pa56_decision.csv'}`",
        "",
        "## Decision",
        "",
        "Phase E.5 single-factor IC screening is ready for Claude review. Do not run ablation or handler promotion until this report is reviewed.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TW institutional Qlib bin materialization and single-factor IC screen.")
    parser.add_argument("--output-dir", default=OUT_DIR_DEFAULT)
    parser.add_argument("--sample-n", type=int, default=20)
    args = parser.parse_args()

    out_dir = ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    provider = ROOT / PROVIDER

    source = load_source_features()
    manifest = write_feature_bins(source, provider)
    validation = validate_bins(source, provider, args.sample_n)

    _, label = fetch_raw()
    candidates = source.reindex(label.index)[FACTORS]
    alpha158 = fetch_alpha158()
    daily_ic = calc_daily_ic(candidates, label, FACTORS)
    segment_ic = summarize_ic(daily_ic, FACTORS)
    corr, corr_detail = calc_alpha158_corr(candidates, alpha158, FACTORS)
    screen = build_screen_summary(segment_ic, corr)
    pa56_corr = load_materialization_reference("pa56_consensus_foreign_corr.csv")
    pa56_decision = build_pa56_decision(screen, pa56_corr)
    momentum = load_materialization_reference("institutional_momentum_overlap.csv")

    manifest.to_csv(out_dir / "institutional_bin_manifest.csv", index=False)
    validation.to_csv(out_dir / "institutional_bin_validation.csv", index=False)
    daily_ic.to_csv(out_dir / "institutional_daily_ic.csv", index=False)
    segment_ic.to_csv(out_dir / "institutional_segment_ic.csv", index=False)
    corr.to_csv(out_dir / "institutional_alpha158_corr.csv", index=False)
    corr_detail.to_csv(out_dir / "institutional_alpha158_corr_detail.csv", index=False)
    screen.to_csv(out_dir / "institutional_screen.csv", index=False)
    momentum.to_csv(out_dir / "institutional_momentum_overlap_inherited.csv", index=False)
    pa56_decision.to_csv(out_dir / "institutional_pa56_decision.csv", index=False)
    write_report(out_dir.relative_to(ROOT), manifest, validation, screen, segment_ic, corr_detail, pa56_decision, momentum)

    print(f"bin_fields={len(manifest)}")
    print(f"validation_pass={bool(validation['pass_float32_tolerance_1e_8'].all())}")
    for _, row in screen.iterrows():
        print(f"{row['factor']} test_rank_ic={row['test_rank_ic']:.6f} test_ic={row['test_ic']:.6f} decision={row['screen_decision']}")
    print(f"pa56_decision={pa56_decision['pa56_decision'].iloc[0]}")
    print(f"wrote {out_dir.relative_to(ROOT)}")
    print(f"wrote {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
