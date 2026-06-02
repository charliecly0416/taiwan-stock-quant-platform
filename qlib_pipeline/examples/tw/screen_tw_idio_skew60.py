from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import qlib
from qlib.data import D

from screen_tw_academic_factors import (
    ROOT,
    PROVIDER,
    MARKET,
    START,
    END,
    SEGMENTS,
    fetch_alpha158,
    fetch_raw,
    calc_daily_ic,
    summarize_ic,
    calc_alpha158_corr,
)

FACTOR = "TW_IDIO_SKEW60"
BENCHMARK = "TWII"
WINDOW = 60
MIN_OBS = 40
OUT_DIR_DEFAULT = "data_tw/experiments/yahoo_primary_tw_idio_skew60_screen"
REPORT_PATH = ROOT / "docs/tw_audit/21_tw_idio_skew60_screening_report.md"


def fetch_benchmark_return() -> pd.Series:
    bench = D.features(
        [BENCHMARK],
        ["$close", "Ref($close, 1)"],
        start_time=START,
        end_time=END,
        freq="day",
    )
    bench = bench.droplevel("instrument")
    ret = bench["$close"] / bench["Ref($close, 1)"] - 1
    ret.name = "MKT_RET"
    return ret.replace([np.inf, -np.inf], np.nan)


def _rolling_idio_skew_one(y: np.ndarray, x: np.ndarray, window: int, min_obs: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    out = np.full(y.shape[0], np.nan, dtype=float)
    beta_out = np.full(y.shape[0], np.nan, dtype=float)
    resid_std_out = np.full(y.shape[0], np.nan, dtype=float)
    n_out = np.zeros(y.shape[0], dtype=float)
    if y.shape[0] < window:
        return out, beta_out, resid_std_out, n_out

    from numpy.lib.stride_tricks import sliding_window_view

    yw = sliding_window_view(y, window)
    xw = sliding_window_view(x, window)
    valid = np.isfinite(yw) & np.isfinite(xw)
    n = valid.sum(axis=1).astype(float)
    y0 = np.where(valid, yw, 0.0)
    x0 = np.where(valid, xw, 0.0)
    sx = x0.sum(axis=1)
    sy = y0.sum(axis=1)
    sx2 = (x0 * x0).sum(axis=1)
    sxy = (x0 * y0).sum(axis=1)

    ok_n = n >= min_obs
    denom = sx2 - sx * sx / np.where(n > 0, n, np.nan)
    ok = ok_n & np.isfinite(denom) & (np.abs(denom) > 1e-12)
    beta = np.full(n.shape[0], np.nan, dtype=float)
    alpha = np.full(n.shape[0], np.nan, dtype=float)
    beta[ok] = (sxy[ok] - sx[ok] * sy[ok] / n[ok]) / denom[ok]
    alpha[ok] = sy[ok] / n[ok] - beta[ok] * sx[ok] / n[ok]

    resid = yw - alpha[:, None] - beta[:, None] * xw
    resid = np.where(valid & ok[:, None], resid, np.nan)
    resid_mean = np.nanmean(resid, axis=1)
    centered = resid - resid_mean[:, None]
    m2 = np.nanmean(centered * centered, axis=1)
    m3 = np.nanmean(centered * centered * centered, axis=1)
    skew = m3 / np.power(m2, 1.5)
    std = np.sqrt(m2)
    ok_skew = ok & np.isfinite(skew) & np.isfinite(std) & (std > 1e-12)

    offset = window - 1
    out[offset:][ok_skew] = skew[ok_skew]
    beta_out[offset:][ok_skew] = beta[ok_skew]
    resid_std_out[offset:][ok_skew] = std[ok_skew]
    n_out[offset:] = n
    return out, beta_out, resid_std_out, n_out


def build_idio_skew(features: pd.DataFrame, market_ret: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    close = features["CLOSE0"].replace([np.inf, -np.inf], np.nan)
    ref1 = features["CLOSE_REF1"].replace([np.inf, -np.inf], np.nan)
    stock_ret = (close / ref1 - 1).replace([np.inf, -np.inf], np.nan)
    dates = features.index.get_level_values("datetime")
    mkt = pd.Series(dates.map(market_ret), index=features.index, name="MKT_RET")

    factor_parts = []
    diag_parts = []
    for instrument, y in stock_ret.groupby(level="instrument", sort=False):
        y = y.droplevel("instrument").sort_index()
        x = market_ret.reindex(y.index)
        skew, beta, resid_std, n_obs = _rolling_idio_skew_one(
            y.to_numpy(dtype=float),
            x.to_numpy(dtype=float),
            WINDOW,
            MIN_OBS,
        )
        idx = pd.MultiIndex.from_product([y.index, [instrument]], names=["datetime", "instrument"])
        factor_parts.append(pd.Series(skew, index=idx, name=FACTOR))
        diag_parts.append(
            pd.DataFrame(
                {
                    "STOCK_RET": y.to_numpy(dtype=float),
                    "MKT_RET": x.to_numpy(dtype=float),
                    "ROLLING_N_OBS": n_obs,
                    "ROLLING_BETA": beta,
                    "RESID_STD": resid_std,
                    "TW_IDIO_SKEW60": skew,
                },
                index=idx,
            )
        )

    factor = pd.concat(factor_parts).sort_index().to_frame()
    diagnostics = pd.concat(diag_parts).sort_index()
    diagnostics["VOLUME0"] = features["VOLUME0"].reindex(diagnostics.index)
    diagnostics["ABS_STOCK_RET"] = diagnostics["STOCK_RET"].abs()
    return factor, diagnostics


def segment_frame(df: pd.DataFrame, segment: str) -> pd.DataFrame:
    start, end = SEGMENTS[segment]
    return df.loc[(slice(pd.Timestamp(start), pd.Timestamp(end)), slice(None)), :]


def summarize_alignment(features: pd.DataFrame, diagnostics: pd.DataFrame, market_ret: pd.Series) -> pd.DataFrame:
    dates = pd.Index(features.index.get_level_values("datetime").unique()).sort_values()
    mkt = market_ret.reindex(dates)
    rows = []
    for segment, (start, end) in SEGMENTS.items():
        seg_dates = dates[(dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))]
        seg = segment_frame(diagnostics, segment)
        finite_stock = seg["STOCK_RET"].notna()
        finite_market = seg["MKT_RET"].notna()
        rows.append(
            {
                "segment": segment,
                "calendar_days": int(len(seg_dates)),
                "twii_finite_return_days": int(mkt.loc[seg_dates].notna().sum()),
                "twii_missing_return_days": int(mkt.loc[seg_dates].isna().sum()),
                "stock_return_rows": int(seg.shape[0]),
                "finite_stock_return_rows": int(finite_stock.sum()),
                "rows_dropped_missing_market": int((finite_stock & ~finite_market).sum()),
                "drop_missing_market_share": float((finite_stock & ~finite_market).mean()) if len(seg) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def summarize_missing_market_dates(diagnostics: pd.DataFrame, market_ret: pd.Series) -> pd.DataFrame:
    dates = pd.Index(diagnostics.index.get_level_values("datetime").unique()).sort_values()
    missing_dates = market_ret.reindex(dates)[market_ret.reindex(dates).isna()].index
    rows = []
    for date in missing_dates:
        seg_name = "outside_segments"
        for segment, (start, end) in SEGMENTS.items():
            if pd.Timestamp(start) <= date <= pd.Timestamp(end):
                seg_name = segment
                break
        g = diagnostics.xs(date, level="datetime")
        finite_stock = g["STOCK_RET"].notna()
        abs_ret = g.loc[finite_stock, "STOCK_RET"].abs()
        rows.append(
            {
                "date": pd.Timestamp(date).strftime("%Y-%m-%d"),
                "segment": seg_name,
                "n_rows": int(g.shape[0]),
                "finite_stock_return_rows": int(finite_stock.sum()),
                "zero_volume_share": float((g["VOLUME0"] <= 0).mean()) if len(g) else np.nan,
                "abs_stock_ret_p50": float(abs_ret.quantile(0.50)) if len(abs_ret) else np.nan,
                "abs_stock_ret_max": float(abs_ret.max()) if len(abs_ret) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def summarize_coverage(diagnostics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for segment in SEGMENTS:
        seg = segment_frame(diagnostics, segment)
        finite = seg[FACTOR].replace([np.inf, -np.inf], np.nan).notna()
        rows.append(
            {
                "segment": segment,
                "n_rows": int(seg.shape[0]),
                "finite_factor_rows": int(finite.sum()),
                "finite_factor_share": float(finite.mean()) if len(finite) else np.nan,
                "n_instruments_with_factor": int(seg.loc[finite].index.get_level_values("instrument").nunique()) if finite.any() else 0,
            }
        )
    return pd.DataFrame(rows)


def summarize_min_obs(diagnostics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for segment in SEGMENTS:
        seg = segment_frame(diagnostics, segment)
        n = seg["ROLLING_N_OBS"].replace(0, np.nan).dropna()
        rows.append(
            {
                "segment": segment,
                "p10": float(n.quantile(0.10)) if len(n) else np.nan,
                "p50": float(n.quantile(0.50)) if len(n) else np.nan,
                "p90": float(n.quantile(0.90)) if len(n) else np.nan,
                "share_below_min_obs": float((seg["ROLLING_N_OBS"] < MIN_OBS).mean()) if len(seg) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def summarize_residual_sanity(diagnostics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for segment in SEGMENTS:
        seg = segment_frame(diagnostics, segment)
        finite = seg[FACTOR].notna()
        beta = seg.loc[finite, "ROLLING_BETA"]
        resid_std = seg.loc[finite, "RESID_STD"]
        rows.append(
            {
                "segment": segment,
                "beta_p05": float(beta.quantile(0.05)) if len(beta) else np.nan,
                "beta_p50": float(beta.quantile(0.50)) if len(beta) else np.nan,
                "beta_p95": float(beta.quantile(0.95)) if len(beta) else np.nan,
                "resid_std_p05": float(resid_std.quantile(0.05)) if len(resid_std) else np.nan,
                "resid_std_p50": float(resid_std.quantile(0.50)) if len(resid_std) else np.nan,
                "resid_std_p95": float(resid_std.quantile(0.95)) if len(resid_std) else np.nan,
                "zero_variance_windows": int(((seg["ROLLING_N_OBS"] >= MIN_OBS) & (seg["RESID_STD"].fillna(0) <= 1e-12)).sum()),
            }
        )
    return pd.DataFrame(rows)


def summarize_outliers(diagnostics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for segment in SEGMENTS:
        seg = segment_frame(diagnostics, segment)
        s = seg[FACTOR].replace([np.inf, -np.inf], np.nan).dropna()
        rows.append(
            {
                "segment": segment,
                "n": int(s.shape[0]),
                "min": float(s.min()) if len(s) else np.nan,
                "p50": float(s.quantile(0.50)) if len(s) else np.nan,
                "p95": float(s.quantile(0.95)) if len(s) else np.nan,
                "p99": float(s.quantile(0.99)) if len(s) else np.nan,
                "p999": float(s.quantile(0.999)) if len(s) else np.nan,
                "max": float(s.max()) if len(s) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def summarize_zero_volume(diagnostics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for segment in SEGMENTS:
        seg = segment_frame(diagnostics, segment)
        zero = seg["VOLUME0"] <= 0
        for bucket, mask in {"zero_volume": zero, "nonzero_volume": ~zero}.items():
            scoped = seg[mask.fillna(False)]
            finite = scoped[FACTOR].notna()
            rows.append(
                {
                    "segment": segment,
                    "volume_bucket": bucket,
                    "n_rows": int(scoped.shape[0]),
                    "finite_factor_rows": int(finite.sum()),
                    "finite_factor_share": float(finite.mean()) if len(finite) else np.nan,
                }
            )
    return pd.DataFrame(rows)


def summarize_price_shocks(diagnostics: pd.DataFrame, limit: int = 50) -> pd.DataFrame:
    finite = diagnostics[FACTOR].notna() & diagnostics["ABS_STOCK_RET"].notna()
    cols = ["STOCK_RET", "MKT_RET", "ROLLING_N_OBS", "ROLLING_BETA", "RESID_STD", FACTOR, "VOLUME0"]
    out = diagnostics.loc[finite, cols].copy()
    out["abs_stock_ret"] = out["STOCK_RET"].abs()
    out = out.sort_values("abs_stock_ret", ascending=False).head(limit).reset_index()
    return out


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
    segment_cols = ["train_rank_ic", "valid_rank_ic", "test_rank_ic", "test_2023_rank_ic", "test_2024_rank_ic", "test_2025h1_rank_ic"]
    vals = out.loc[0, segment_cols].dropna() if not out.empty else pd.Series(dtype=float)
    vals = vals[vals != 0]
    out["direction_stable"] = bool(len(vals) and ((vals > 0).all() or (vals < 0).all())) if not out.empty else False
    out["expected_raw_direction"] = "negative"
    out["abs_test_rank_ic"] = out["test_rank_ic"].abs()

    def decision(row: pd.Series) -> str:
        if row.get("corr_gate") in {"reject_hard_top20_corr", "reject_soft_all158_corr"}:
            return row.get("corr_gate")
        if pd.isna(row.get("test_rank_ic")) or abs(row.get("test_rank_ic")) < 0.01:
            return "reject_rankic_below_0.01"
        if row.get("test_rank_ic") > 0:
            return "reject_wrong_raw_direction"
        if not row.get("direction_stable", False):
            return "reject_direction_unstable"
        if row.get("corr_gate") == "borderline_corr_requires_delta_0.008":
            return "pass_borderline_corr_ablation_delta_0.008"
        return "pass_single_factor_screen"

    out["screen_decision"] = out.apply(decision, axis=1) if not out.empty else []
    return out


def fmt_value(x):
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


def write_report(out_dir: Path, alignment: pd.DataFrame, missing_dates: pd.DataFrame, coverage: pd.DataFrame, min_obs: pd.DataFrame, residual: pd.DataFrame, outliers: pd.DataFrame, zero_volume: pd.DataFrame, shocks: pd.DataFrame, screen: pd.DataFrame | None, segment_ic: pd.DataFrame | None, corr_detail: pd.DataFrame | None) -> None:
    lines = [
        "---",
        "created_at: 2026-05-27",
        "status: screening_complete" if screen is not None else "status: diagnostics_blocked",
        "scope: tw_idio_skew60_script_based_screen",
        "related_docs:",
        "  - docs/tw_audit/20_tw_idio_skew60_design.md",
        "  - docs/tw_audit/19_claude_audit_round_7_amihud20_ablation.md",
        "---",
        "",
        "# TW_IDIO_SKEW60 Screening Report",
        "",
        "## Scope",
        "",
        "This report implements the script-based TW_IDIO_SKEW60 construction requested by `20_tw_idio_skew60_design.md`. It uses the fixed Yahoo adjusted primary provider, `tw_liquid_dyn`, `TWII`, and the 2025-06-30 cutoff. It does not add a handler, run ablation, tune strategy parameters, or access frozen OOS data.",
        "",
        "Implementation note: skewness is computed as population moment skewness of the 60-day OLS market-model residuals, using an intercept and `min_obs=40` paired stock/TWII returns.",
        "",
        "Alignment caveat: train has early TWII return gaps, but valid/test/test_2025h1 have zero rows dropped for missing market return. The screen therefore proceeds while documenting the train-only calendar mismatch.",
        "",
        "## Benchmark Alignment",
        "",
    ]
    lines.extend(table(alignment, ["segment", "calendar_days", "twii_finite_return_days", "twii_missing_return_days", "stock_return_rows", "finite_stock_return_rows", "rows_dropped_missing_market", "drop_missing_market_share"]))
    if not missing_dates.empty:
        lines += ["", "## Missing Market-Return Dates", ""]
        lines.extend(table(missing_dates.head(40), ["date", "segment", "n_rows", "finite_stock_return_rows", "zero_volume_share", "abs_stock_ret_p50", "abs_stock_ret_max"]))
    lines += ["", "## Rolling Coverage", ""]
    lines.extend(table(coverage, ["segment", "n_rows", "finite_factor_rows", "finite_factor_share", "n_instruments_with_factor"]))
    lines += ["", "## Min Obs Distribution", ""]
    lines.extend(table(min_obs, ["segment", "p10", "p50", "p90", "share_below_min_obs"]))
    lines += ["", "## Residual Sanity", ""]
    lines.extend(table(residual, ["segment", "beta_p05", "beta_p50", "beta_p95", "resid_std_p05", "resid_std_p50", "resid_std_p95", "zero_variance_windows"]))
    lines += ["", "## Outlier Sensitivity", ""]
    lines.extend(table(outliers, ["segment", "n", "min", "p50", "p95", "p99", "p999", "max"]))
    lines += ["", "## Zero-Volume Interaction", ""]
    lines.extend(table(zero_volume, ["segment", "volume_bucket", "n_rows", "finite_factor_rows", "finite_factor_share"]))
    lines += ["", "## Largest Adjusted-Price Shocks", ""]
    lines.extend(table(shocks.head(20), ["datetime", "instrument", "STOCK_RET", "MKT_RET", "ROLLING_N_OBS", "ROLLING_BETA", "RESID_STD", FACTOR, "VOLUME0", "abs_stock_ret"]))

    if screen is not None and segment_ic is not None:
        rank_ic = segment_ic[segment_ic["metric"] == "rank_ic"]
        lines += ["", "## Six-Segment RankIC", ""]
        lines.extend(table(rank_ic, ["factor", "segment", "n_days", "mean", "std", "ir", "positive_rate", "avg_n", "avg_coverage"]))
        lines += ["", "## Alpha158 Corr Gate", ""]
        lines.extend(table(screen, ["factor", "max_abs_corr_top20", "nearest_top20_alpha158", "max_abs_corr_all158", "nearest_all158_alpha158", "corr_gate"]))
        if corr_detail is not None and not corr_detail.empty:
            lines += ["", "## Nearest Alpha158 Features", ""]
            lines.extend(table(corr_detail.head(20), ["factor", "alpha158_feature", "mean_spearman_corr", "abs_mean_spearman_corr", "is_top20_gain"]))
        lines += ["", "## Decision", ""]
        lines.extend(table(screen, ["factor", "train_rank_ic", "valid_rank_ic", "test_rank_ic", "test_2023_rank_ic", "test_2024_rank_ic", "test_2025h1_rank_ic", "expected_raw_direction", "direction_stable", "screen_decision"]))
    else:
        lines += ["", "## Decision", "", "Diagnostics found a blocker, so IC/correlation screening was not run."]

    lines += [
        "",
        "## Artifacts",
        "",
        f"- `{out_dir / 'tw_idio_skew60_alignment.csv'}`",
        f"- `{out_dir / 'tw_idio_skew60_missing_market_dates.csv'}`",
        f"- `{out_dir / 'tw_idio_skew60_coverage.csv'}`",
        f"- `{out_dir / 'tw_idio_skew60_min_obs.csv'}`",
        f"- `{out_dir / 'tw_idio_skew60_residual_sanity.csv'}`",
        f"- `{out_dir / 'tw_idio_skew60_outliers.csv'}`",
        f"- `{out_dir / 'tw_idio_skew60_zero_volume.csv'}`",
        f"- `{out_dir / 'tw_idio_skew60_price_shocks.csv'}`",
    ]
    if screen is not None:
        lines += [
            f"- `{out_dir / 'tw_idio_skew60_daily_ic.csv'}`",
            f"- `{out_dir / 'tw_idio_skew60_segment_ic.csv'}`",
            f"- `{out_dir / 'tw_idio_skew60_alpha158_corr.csv'}`",
            f"- `{out_dir / 'tw_idio_skew60_alpha158_corr_detail.csv'}`",
            f"- `{out_dir / 'tw_idio_skew60_screen.csv'}`",
        ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def has_blocker(alignment: pd.DataFrame, coverage: pd.DataFrame) -> bool:
    # Train-only market-return gaps are documented as a calendar caveat. They do not
    # contaminate validation/test IC because factor construction uses only finite
    # paired stock/TWII observations inside each rolling window.
    eval_segments = {"valid", "test", "test_2023", "test_2024", "test_2025h1"}
    eval_alignment = alignment[alignment["segment"].isin(eval_segments)]
    if eval_alignment["rows_dropped_missing_market"].sum() > 0:
        return True
    test_2025 = coverage.loc[coverage["segment"] == "test_2025h1", "finite_factor_share"]
    return bool(test_2025.empty or test_2025.iloc[0] < 0.50)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TW_IDIO_SKEW60 script-based diagnostics and screen.")
    parser.add_argument("--output-dir", default=OUT_DIR_DEFAULT)
    parser.add_argument("--checks-only", action="store_true", help="Run diagnostics only and skip IC/corr screen.")
    args = parser.parse_args()

    out_dir = ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    qlib.init(provider_uri=PROVIDER, region="tw", expression_cache=None, dataset_cache=None)
    features, label = fetch_raw()
    market_ret = fetch_benchmark_return()
    candidates, diagnostics = build_idio_skew(features, market_ret)

    alignment = summarize_alignment(features, diagnostics, market_ret)
    missing_dates = summarize_missing_market_dates(diagnostics, market_ret)
    coverage = summarize_coverage(diagnostics)
    min_obs = summarize_min_obs(diagnostics)
    residual = summarize_residual_sanity(diagnostics)
    outliers = summarize_outliers(diagnostics)
    zero_volume = summarize_zero_volume(diagnostics)
    shocks = summarize_price_shocks(diagnostics)

    alignment.to_csv(out_dir / "tw_idio_skew60_alignment.csv", index=False)
    missing_dates.to_csv(out_dir / "tw_idio_skew60_missing_market_dates.csv", index=False)
    coverage.to_csv(out_dir / "tw_idio_skew60_coverage.csv", index=False)
    min_obs.to_csv(out_dir / "tw_idio_skew60_min_obs.csv", index=False)
    residual.to_csv(out_dir / "tw_idio_skew60_residual_sanity.csv", index=False)
    outliers.to_csv(out_dir / "tw_idio_skew60_outliers.csv", index=False)
    zero_volume.to_csv(out_dir / "tw_idio_skew60_zero_volume.csv", index=False)
    shocks.to_csv(out_dir / "tw_idio_skew60_price_shocks.csv", index=False)

    screen = None
    segment_ic = None
    corr_detail = None
    if not args.checks_only and not has_blocker(alignment, coverage):
        alpha158 = fetch_alpha158()
        daily_ic = calc_daily_ic(candidates, label, [FACTOR])
        segment_ic = summarize_ic(daily_ic, [FACTOR])
        corr, corr_detail = calc_alpha158_corr(candidates[[FACTOR]], alpha158, [FACTOR])
        screen = build_screen_summary(segment_ic, corr)
        daily_ic.to_csv(out_dir / "tw_idio_skew60_daily_ic.csv", index=False)
        segment_ic.to_csv(out_dir / "tw_idio_skew60_segment_ic.csv", index=False)
        corr.to_csv(out_dir / "tw_idio_skew60_alpha158_corr.csv", index=False)
        corr_detail.to_csv(out_dir / "tw_idio_skew60_alpha158_corr_detail.csv", index=False)
        screen.to_csv(out_dir / "tw_idio_skew60_screen.csv", index=False)

    write_report(out_dir.relative_to(ROOT), alignment, missing_dates, coverage, min_obs, residual, outliers, zero_volume, shocks, screen, segment_ic, corr_detail)

    print(f"rows={features.shape[0]}")
    print(f"finite_factor_rows={int(candidates[FACTOR].notna().sum())}")
    print(f"blocker={has_blocker(alignment, coverage)}")
    if screen is not None:
        print(f"test_rank_ic={screen['test_rank_ic'].iloc[0]:.6f}")
        print(f"screen_decision={screen['screen_decision'].iloc[0]}")
    print(f"wrote {out_dir.relative_to(ROOT)}")
    print(f"wrote {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
