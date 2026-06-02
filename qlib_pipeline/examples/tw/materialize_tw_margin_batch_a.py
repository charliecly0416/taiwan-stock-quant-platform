#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import qlib

from screen_tw_academic_factors import PROVIDER, ROOT, SEGMENTS, calc_alpha158_corr, fetch_alpha158

RAW_DIR = ROOT / "data_tw/finmind_margin/raw"
STATUS_PATH = ROOT / "data_tw/finmind_margin/download_status.csv"
COVERAGE_PATH = ROOT / "data_tw/finmind_margin/full_coverage_vs_price_calendar.csv"
NORMALIZED_DIR = ROOT / "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"
START = "2015-05-04"
END = "2025-06-30"
FACTORS = ["TW_MARGIN_UTIL", "TW_MARGIN_DELTA_5D"]
REQUIRED_COLUMNS = [
    "date",
    "stock_id",
    "MarginPurchaseTodayBalance",
    "MarginPurchaseLimit",
    "qlib_symbol",
    "exchange",
]


def load_status() -> pd.DataFrame:
    status = pd.read_csv(STATUS_PATH)
    status["row_count"] = pd.to_numeric(status["row_count"], errors="coerce").fillna(0).astype(int)
    return status.sort_values("qlib_symbol").reset_index(drop=True)


def read_price_calendar(symbol: str) -> pd.DataFrame:
    path = NORMALIZED_DIR / f"{symbol}.csv"
    if not path.exists():
        return pd.DataFrame(columns=["qlib_symbol", "date"])
    px = pd.read_csv(path, usecols=["symbol", "date"]).rename(columns={"symbol": "qlib_symbol"})
    px["date"] = pd.to_datetime(px["date"])
    px = px[(px["date"] >= pd.Timestamp(START)) & (px["date"] <= pd.Timestamp(END))]
    return px.sort_values("date").reset_index(drop=True)


def read_raw_margin(stock_id: str) -> pd.DataFrame:
    path = RAW_DIR / f"{stock_id}.csv"
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=REQUIRED_COLUMNS)
    raw = pd.read_csv(path)
    for col in REQUIRED_COLUMNS:
        if col not in raw.columns:
            raw[col] = np.nan
    if raw.empty:
        return pd.DataFrame(columns=REQUIRED_COLUMNS)
    raw = raw[REQUIRED_COLUMNS].copy()
    raw["date"] = pd.to_datetime(raw["date"])
    raw = raw.sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)
    for col in ["MarginPurchaseTodayBalance", "MarginPurchaseLimit"]:
        raw[col] = pd.to_numeric(raw[col], errors="coerce")
    return raw


def compute_raw_factors(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame(columns=["date", "raw_margin_date", *FACTORS])
    out = raw[["date", "MarginPurchaseTodayBalance", "MarginPurchaseLimit"]].copy()
    bal = out["MarginPurchaseTodayBalance"]
    limit = out["MarginPurchaseLimit"]
    out["TW_MARGIN_UTIL"] = np.where((limit > 0) & bal.notna() & (bal >= 0), bal / limit, np.nan)
    lag5 = bal.shift(5)
    valid_delta = bal.notna() & lag5.notna() & (bal >= 0) & (lag5 >= 0)
    out["TW_MARGIN_DELTA_5D"] = np.where(valid_delta, np.log1p(bal) - np.log1p(lag5), np.nan)
    out["raw_margin_date"] = out["date"]
    return out[["date", "raw_margin_date", *FACTORS]]


def materialize_symbol(row: pd.Series) -> tuple[pd.DataFrame, dict[str, object], pd.DataFrame]:
    symbol = str(row["qlib_symbol"])
    stock_id = str(row["stock_id"])
    exchange = str(row.get("exchange", "UNKNOWN"))
    price = read_price_calendar(symbol)
    raw = read_raw_margin(stock_id)
    raw_factors = compute_raw_factors(raw)

    if price.empty:
        aligned = pd.DataFrame(columns=["qlib_symbol", "stock_id", "exchange", "date", "raw_margin_date", *FACTORS])
    else:
        aligned = price.merge(raw_factors, on="date", how="left")
        aligned["stock_id"] = stock_id
        aligned["exchange"] = exchange
        # PIT: a model row on price date t uses the margin row from the previous price date.
        for col in ["raw_margin_date", *FACTORS]:
            aligned[col] = aligned[col].shift(1)
        aligned = aligned[["qlib_symbol", "stock_id", "exchange", "date", "raw_margin_date", *FACTORS]]

    if raw.empty:
        first5_ok = np.nan
        sixth_ok = np.nan
        sixth_raw_date = ""
        sixth_value = np.nan
    else:
        delta = compute_raw_factors(raw)["TW_MARGIN_DELTA_5D"]
        first5_ok = bool(delta.head(5).isna().all()) if len(delta) >= 5 else bool(delta.isna().all())
        sixth_ok = bool(pd.notna(delta.iloc[5])) if len(delta) >= 6 else np.nan
        sixth_raw_date = raw.iloc[5]["date"].strftime("%Y-%m-%d") if len(raw) >= 6 else ""
        sixth_value = float(delta.iloc[5]) if len(raw) >= 6 and pd.notna(delta.iloc[5]) else np.nan

    boundary = pd.DataFrame(
        [
            {
                "qlib_symbol": symbol,
                "stock_id": stock_id,
                "exchange": exchange,
                "raw_rows": int(raw.shape[0]),
                "raw_missing_balance": int(raw["MarginPurchaseTodayBalance"].isna().sum()) if not raw.empty else 0,
                "raw_negative_balance": int((raw["MarginPurchaseTodayBalance"] < 0).sum()) if not raw.empty else 0,
                "raw_missing_limit": int(raw["MarginPurchaseLimit"].isna().sum()) if not raw.empty else 0,
                "raw_nonpositive_limit": int((raw["MarginPurchaseLimit"] <= 0).sum()) if not raw.empty else 0,
                "util_invalid_rows": int(compute_raw_factors(raw)["TW_MARGIN_UTIL"].isna().sum()) if not raw.empty else 0,
                "delta_first5_nan_ok": first5_ok,
                "delta_sixth_observation_has_value": sixth_ok,
                "delta_sixth_raw_date": sixth_raw_date,
                "delta_sixth_value": sixth_value,
            }
        ]
    )
    summary = {
        "qlib_symbol": symbol,
        "stock_id": stock_id,
        "exchange": exchange,
        "price_rows": int(price.shape[0]),
        "raw_rows": int(raw.shape[0]),
        "same_day_raw_matches": int(price["date"].isin(raw["date"]).sum()) if not price.empty and not raw.empty else 0,
        "shifted_source_rows": int(aligned["raw_margin_date"].notna().sum()) if not aligned.empty else 0,
        "tw_margin_util_finite": int(aligned["TW_MARGIN_UTIL"].notna().sum()) if not aligned.empty else 0,
        "tw_margin_delta_5d_finite": int(aligned["TW_MARGIN_DELTA_5D"].notna().sum()) if not aligned.empty else 0,
    }
    return aligned, summary, boundary


def winsorized_zscore(s: pd.Series) -> pd.Series:
    valid = s.dropna()
    if valid.shape[0] < 30:
        return pd.Series(np.nan, index=s.index)
    lo = valid.quantile(0.01)
    hi = valid.quantile(0.99)
    clipped = s.clip(lo, hi)
    std = clipped.std(ddof=0)
    if not np.isfinite(std) or std == 0:
        return pd.Series(np.nan, index=s.index)
    return (clipped - clipped.mean()) / std


def add_normalized_features(all_features: pd.DataFrame) -> pd.DataFrame:
    out = all_features.copy()
    for factor in FACTORS:
        out[f"{factor}_rank"] = out.groupby("date", group_keys=False)[factor].transform(
            lambda s: s.rank(pct=True, method="average") if s.notna().sum() >= 30 else pd.Series(np.nan, index=s.index)
        )
        out[f"{factor}_zscore"] = out.groupby("date", group_keys=False)[factor].transform(winsorized_zscore)
    return out


def segment_mask(dates: pd.Series, start: str, end: str) -> pd.Series:
    return (dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))


def summarize_coverage(features: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for seg_name, (start, end) in SEGMENTS.items():
        seg = features[segment_mask(features["date"], start, end)]
        for exchange, g in seg.groupby("exchange", dropna=False):
            for factor in FACTORS:
                rows.append(
                    {
                        "segment": seg_name,
                        "exchange": exchange,
                        "factor": factor,
                        "rows": int(g.shape[0]),
                        "finite_rows": int(g[factor].notna().sum()),
                        "coverage": float(g[factor].notna().mean()) if len(g) else np.nan,
                    }
                )
    return pd.DataFrame(rows)


def summarize_distribution(features: pd.DataFrame) -> pd.DataFrame:
    rows = []
    quantiles = [0.01, 0.05, 0.5, 0.95, 0.99]
    for seg_name, (start, end) in SEGMENTS.items():
        seg = features[segment_mask(features["date"], start, end)]
        for exchange, g in seg.groupby("exchange", dropna=False):
            for factor in FACTORS:
                s = g[factor].dropna()
                row = {"segment": seg_name, "exchange": exchange, "factor": factor, "finite_rows": int(s.shape[0])}
                if s.empty:
                    row.update({"min": np.nan, "p1": np.nan, "p5": np.nan, "p50": np.nan, "p95": np.nan, "p99": np.nan, "max": np.nan})
                else:
                    qs = s.quantile(quantiles)
                    row.update(
                        {
                            "min": float(s.min()),
                            "p1": float(qs.loc[0.01]),
                            "p5": float(qs.loc[0.05]),
                            "p50": float(qs.loc[0.5]),
                            "p95": float(qs.loc[0.95]),
                            "p99": float(qs.loc[0.99]),
                            "max": float(s.max()),
                        }
                    )
                rows.append(row)
    return pd.DataFrame(rows)


def summarize_missingness(features: pd.DataFrame, symbol_summary: pd.DataFrame, status: pd.DataFrame) -> pd.DataFrame:
    true_empty = status[status["row_count"] == 0]
    late_start = symbol_summary[(symbol_summary["raw_rows"] > 0) & (symbol_summary["same_day_raw_matches"] < symbol_summary["price_rows"] * 0.5)]
    return pd.DataFrame(
        [
            {
                "metric": "symbols_total",
                "value": int(status.shape[0]),
            },
            {
                "metric": "true_empty_symbols",
                "value": int(true_empty.shape[0]),
            },
            {
                "metric": "late_start_symbols_lt_50pct_same_day_match",
                "value": int(late_start.shape[0]),
            },
            {
                "metric": "price_rows",
                "value": int(features.shape[0]),
            },
            {
                "metric": "price_rows_without_same_day_margin_source",
                "value": int(features["raw_margin_date"].isna().sum()),
            },
        ]
    )


def summarize_pa50(coverage: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for factor in FACTORS:
        overall = coverage[(coverage["factor"] == factor) & (coverage["segment"] == "test")]
        h1 = coverage[(coverage["factor"] == factor) & (coverage["segment"] == "test_2025h1")]
        overall_cov = overall["finite_rows"].sum() / overall["rows"].sum() if overall["rows"].sum() else np.nan
        h1_cov = h1["finite_rows"].sum() / h1["rows"].sum() if h1["rows"].sum() else np.nan
        rel = h1_cov / overall_cov if overall_cov and np.isfinite(overall_cov) else np.nan
        rows.append(
            {
                "factor": factor,
                "test_coverage": float(overall_cov),
                "test_2025h1_coverage": float(h1_cov),
                "test_2025h1_vs_test_coverage_ratio": float(rel),
                "catastrophic_drop": bool((np.isfinite(h1_cov) and h1_cov < 0.30) or (np.isfinite(rel) and rel < 0.50)),
                "rule": "catastrophic if test_2025h1 coverage < 30% absolute or < 50% of test coverage",
            }
        )
    return pd.DataFrame(rows)


def build_pit_validation(features: pd.DataFrame, boundary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    targets = ["TW2330"]
    targets.extend(features.loc[features["exchange"].eq("TWSE"), "qlib_symbol"].drop_duplicates().head(3).tolist())
    targets.extend(features.loc[features["exchange"].eq("TPEX"), "qlib_symbol"].drop_duplicates().head(3).tolist())
    true_empty_symbols = set(boundary.loc[boundary["raw_rows"].eq(0), "qlib_symbol"].head(2).astype(str))
    targets.extend(sorted(true_empty_symbols))
    targets = list(dict.fromkeys(targets))
    for symbol in targets:
        g = features[features["qlib_symbol"].eq(symbol)].sort_values("date")
        if g.empty:
            continue
        if symbol in true_empty_symbols:
            sample = g.head(2)
            for _, r in sample.iterrows():
                rows.append(
                    {
                        "case": "true_empty_symbol",
                        "qlib_symbol": symbol,
                        "exchange": r["exchange"],
                        "feature_date": r["date"].strftime("%Y-%m-%d"),
                        "previous_price_date": "",
                        "raw_margin_date": "",
                        "pit_pass": bool(pd.isna(r["raw_margin_date"]) and pd.isna(r["TW_MARGIN_UTIL"]) and pd.isna(r["TW_MARGIN_DELTA_5D"])),
                        "tw_margin_util": r["TW_MARGIN_UTIL"],
                        "tw_margin_delta_5d": r["TW_MARGIN_DELTA_5D"],
                    }
                )
            continue
        finite = g[g["raw_margin_date"].notna()]
        sample = finite.head(2)
        if sample.empty:
            continue
        for _, r in sample.iterrows():
            prev_price_date = g.loc[g["date"] < r["date"], "date"].max()
            rows.append(
                {
                    "case": "pit_shift_sample",
                    "qlib_symbol": symbol,
                    "exchange": r["exchange"],
                    "feature_date": r["date"].strftime("%Y-%m-%d"),
                    "previous_price_date": prev_price_date.strftime("%Y-%m-%d") if pd.notna(prev_price_date) else "",
                    "raw_margin_date": r["raw_margin_date"].strftime("%Y-%m-%d") if pd.notna(r["raw_margin_date"]) else "",
                    "pit_pass": bool(pd.notna(prev_price_date) and pd.notna(r["raw_margin_date"]) and prev_price_date == r["raw_margin_date"]),
                    "tw_margin_util": r["TW_MARGIN_UTIL"],
                    "tw_margin_delta_5d": r["TW_MARGIN_DELTA_5D"],
                }
            )
    missing = features[features["raw_margin_date"].isna()].head(5)
    for _, r in missing.iterrows():
        rows.append(
            {
                "case": "price_exists_margin_missing",
                "qlib_symbol": r["qlib_symbol"],
                "exchange": r["exchange"],
                "feature_date": r["date"].strftime("%Y-%m-%d"),
                "previous_price_date": "",
                "raw_margin_date": "",
                "pit_pass": True,
                "tw_margin_util": r["TW_MARGIN_UTIL"],
                "tw_margin_delta_5d": r["TW_MARGIN_DELTA_5D"],
            }
        )
    return pd.DataFrame(rows)


def write_feature_csvs(features: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    feature_dir = out_dir / "features_by_symbol"
    feature_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    cols = [
        "qlib_symbol",
        "date",
        "raw_margin_date",
        "exchange",
        "TW_MARGIN_UTIL",
        "TW_MARGIN_UTIL_rank",
        "TW_MARGIN_UTIL_zscore",
        "TW_MARGIN_DELTA_5D",
        "TW_MARGIN_DELTA_5D_rank",
        "TW_MARGIN_DELTA_5D_zscore",
    ]
    for symbol, g in features.groupby("qlib_symbol", sort=True):
        path = feature_dir / f"{symbol}.csv"
        out = g[cols].copy()
        out["date"] = out["date"].dt.strftime("%Y-%m-%d")
        out["raw_margin_date"] = pd.to_datetime(out["raw_margin_date"]).dt.strftime("%Y-%m-%d")
        out.to_csv(path, index=False)
        rows.append(
            {
                "qlib_symbol": symbol,
                "path": str(path.relative_to(ROOT)),
                "rows": int(out.shape[0]),
                "tw_margin_util_finite": int(out["TW_MARGIN_UTIL"].notna().sum()),
                "tw_margin_delta_5d_finite": int(out["TW_MARGIN_DELTA_5D"].notna().sum()),
            }
        )
    return pd.DataFrame(rows)


def to_candidate_frame(features: pd.DataFrame) -> pd.DataFrame:
    idx = pd.MultiIndex.from_frame(
        features[["date", "qlib_symbol"]].rename(columns={"date": "datetime", "qlib_symbol": "instrument"})
    )
    return pd.DataFrame({factor: features[factor].to_numpy() for factor in FACTORS}, index=idx).sort_index()


def main() -> None:
    parser = argparse.ArgumentParser(description="Materialize TW margin Batch A factors to CSV and diagnostics only.")
    parser.add_argument("--output-dir", default="data_tw/experiments/tw_margin_batch_a_materialized")
    parser.add_argument("--skip-alpha158-corr", action="store_true")
    args = parser.parse_args()

    out_dir = ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    status = load_status()

    feature_frames = []
    summary_rows = []
    boundary_frames = []
    for _, row in status.iterrows():
        features, summary, boundary = materialize_symbol(row)
        if not features.empty:
            feature_frames.append(features)
        summary_rows.append(summary)
        boundary_frames.append(boundary)

    all_features = pd.concat(feature_frames, ignore_index=True) if feature_frames else pd.DataFrame()
    all_features = add_normalized_features(all_features)
    symbol_summary = pd.DataFrame(summary_rows)
    boundary = pd.concat(boundary_frames, ignore_index=True) if boundary_frames else pd.DataFrame()
    feature_manifest = write_feature_csvs(all_features, out_dir)
    coverage = summarize_coverage(all_features)
    distribution = summarize_distribution(all_features)
    missingness = summarize_missingness(all_features, symbol_summary, status)
    pa50 = summarize_pa50(coverage)
    pit_validation = build_pit_validation(all_features, boundary)

    symbol_summary.to_csv(out_dir / "symbol_materialization_summary.csv", index=False)
    feature_manifest.to_csv(out_dir / "feature_manifest.csv", index=False)
    coverage.to_csv(out_dir / "coverage_by_segment_exchange.csv", index=False)
    distribution.to_csv(out_dir / "distribution_by_segment_exchange.csv", index=False)
    missingness.to_csv(out_dir / "missingness_summary.csv", index=False)
    boundary.to_csv(out_dir / "boundary_and_pa49_checks.csv", index=False)
    pa50.to_csv(out_dir / "pa50_coverage_drop_check.csv", index=False)
    pit_validation.to_csv(out_dir / "pit_validation_samples.csv", index=False)

    if args.skip_alpha158_corr:
        corr = pd.DataFrame({"factor": FACTORS, "corr_gate": "skipped"})
        detail = pd.DataFrame()
    else:
        qlib.init(provider_uri=str(ROOT / PROVIDER), region="tw", expression_cache=None, dataset_cache=None)
        alpha158 = fetch_alpha158()
        corr, detail = calc_alpha158_corr(to_candidate_frame(all_features), alpha158, FACTORS)
    corr.to_csv(out_dir / "margin_batch_a_alpha158_corr.csv", index=False)
    detail.to_csv(out_dir / "margin_batch_a_alpha158_corr_detail.csv", index=False)

    print(f"symbols={status.shape[0]}")
    print(f"feature_rows={all_features.shape[0]}")
    print(f"feature_files={feature_manifest.shape[0]}")
    print(f"pit_validation_pass={bool(pit_validation['pit_pass'].all()) if not pit_validation.empty else False}")
    print(f"pa49_first5_pass={bool(boundary['delta_first5_nan_ok'].dropna().all()) if not boundary.empty else False}")
    print(f"pa50_catastrophic_drop={bool(pa50['catastrophic_drop'].any()) if not pa50.empty else False}")
    print(f"wrote {out_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
