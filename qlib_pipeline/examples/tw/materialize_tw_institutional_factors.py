#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import qlib

from screen_tw_academic_factors import PROVIDER, ROOT, SEGMENTS, calc_alpha158_corr, fetch_alpha158

RAW_DIR = ROOT / "data_tw/finmind_institutional/raw"
STATUS_PATH = ROOT / "data_tw/finmind_institutional/download_status.csv"
NORMALIZED_DIR = ROOT / "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"
START = "2015-05-04"
END = "2025-06-30"
PRIMARY_CATEGORIES = ["Foreign_Investor", "Investment_Trust"]
FACTORS = ["TW_FOREIGN_NET_VOL", "TW_TRUST_NET_PX", "TW_FOREIGN_PERSIST_5D", "TW_INST_CONSENSUS"]
REQUIRED_COLUMNS = ["date", "stock_id", "name", "buy", "sell", "qlib_symbol", "exchange"]
MOMENTUM_FEATURES = ["KMID", "ROC5", "ROC10", "MOM"]


def load_status() -> pd.DataFrame:
    status = pd.read_csv(STATUS_PATH)
    status["row_count"] = pd.to_numeric(status["row_count"], errors="coerce").fillna(0).astype(int)
    return status.sort_values("qlib_symbol").reset_index(drop=True)


def read_price_calendar(symbol: str) -> pd.DataFrame:
    path = NORMALIZED_DIR / f"{symbol}.csv"
    if not path.exists():
        return pd.DataFrame(columns=["qlib_symbol", "date", "close", "volume"])
    px = pd.read_csv(path, usecols=["symbol", "date", "close", "volume"]).rename(columns={"symbol": "qlib_symbol"})
    px["date"] = pd.to_datetime(px["date"])
    px["close"] = pd.to_numeric(px["close"], errors="coerce")
    px["volume"] = pd.to_numeric(px["volume"], errors="coerce")
    px = px[(px["date"] >= pd.Timestamp(START)) & (px["date"] <= pd.Timestamp(END))]
    return px.sort_values("date").reset_index(drop=True)


def read_raw_institutional(stock_id: str) -> pd.DataFrame:
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
    raw["buy"] = pd.to_numeric(raw["buy"], errors="coerce")
    raw["sell"] = pd.to_numeric(raw["sell"], errors="coerce")
    raw["name"] = raw["name"].astype(str)
    return raw.sort_values(["date", "name"]).reset_index(drop=True)


def summarize_schema(raw: pd.DataFrame, symbol: str, stock_id: str, exchange: str) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame(
            [
                {
                    "qlib_symbol": symbol,
                    "stock_id": stock_id,
                    "exchange": exchange,
                    "symbol_date_rows": 0,
                    "category_count_3": 0,
                    "category_count_4": 0,
                    "category_count_5": 0,
                    "category_count_other": 0,
                    "foreign_trust_both_present": 0,
                    "foreign_trust_missing": 0,
                    "primary_factor_schema_compatible": True,
                }
            ]
        )
    counts = raw.groupby("date")["name"].nunique()
    names = raw.groupby("date")["name"].agg(lambda s: set(s))
    both = names.map(lambda x: set(PRIMARY_CATEGORIES).issubset(x))
    return pd.DataFrame(
        [
            {
                "qlib_symbol": symbol,
                "stock_id": stock_id,
                "exchange": exchange,
                "symbol_date_rows": int(counts.shape[0]),
                "category_count_3": int((counts == 3).sum()),
                "category_count_4": int((counts == 4).sum()),
                "category_count_5": int((counts == 5).sum()),
                "category_count_other": int((~counts.isin([3, 4, 5])).sum()),
                "foreign_trust_both_present": int(both.sum()),
                "foreign_trust_missing": int((~both).sum()),
                "primary_factor_schema_compatible": bool((~both).sum() == 0),
            }
        ]
    )


def compute_raw_factors(raw: pd.DataFrame, price: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    boundary_rows: list[dict[str, object]] = []
    if raw.empty:
        return pd.DataFrame(columns=["date", "raw_institutional_date", *FACTORS]), pd.DataFrame(), pd.DataFrame(boundary_rows)

    raw = raw.copy()
    raw["is_saturday"] = raw["date"].dt.weekday == 5
    saturday = raw[raw["is_saturday"]].copy()
    raw = raw[~raw["is_saturday"]].copy()

    primary = raw[raw["name"].isin(PRIMARY_CATEGORIES)].copy()
    negative_after_filter = primary[(primary["buy"] < 0) | (primary["sell"] < 0)]
    primary.loc[(primary["buy"] < 0) | (primary["sell"] < 0), ["buy", "sell"]] = np.nan

    pivot = primary.pivot_table(index="date", columns="name", values=["buy", "sell"], aggfunc="last")
    if pivot.empty:
        out = pd.DataFrame(columns=["date", "raw_institutional_date", *FACTORS])
    else:
        pivot.columns = [f"{name}_{field}" for field, name in pivot.columns]
        pivot = pivot.reset_index()
        out = pivot.merge(price[["date", "close", "volume"]], on="date", how="left")
        for col in [
            "Foreign_Investor_buy",
            "Foreign_Investor_sell",
            "Investment_Trust_buy",
            "Investment_Trust_sell",
        ]:
            if col not in out.columns:
                out[col] = np.nan
        foreign_buy = out["Foreign_Investor_buy"]
        foreign_sell = out["Foreign_Investor_sell"]
        trust_buy = out["Investment_Trust_buy"]
        trust_sell = out["Investment_Trust_sell"]
        volume = out["volume"]
        close = out["close"]
        traded_value = close * volume

        foreign_net = foreign_buy - foreign_sell
        trust_net = trust_buy - trust_sell
        valid_foreign = foreign_buy.notna() & foreign_sell.notna() & volume.notna() & (volume > 0)
        valid_trust_px = trust_buy.notna() & trust_sell.notna() & close.notna() & volume.notna() & (close > 0) & (volume > 0)
        valid_consensus = valid_foreign & trust_buy.notna() & trust_sell.notna()

        out["TW_FOREIGN_NET_VOL"] = np.where(valid_foreign, foreign_net / volume, np.nan)
        out["TW_TRUST_NET_PX"] = np.where(valid_trust_px, trust_net / traded_value, np.nan)
        out["TW_INST_CONSENSUS"] = np.where(valid_consensus, (foreign_net + trust_net) / volume, np.nan)
        persist_input = pd.Series(np.sign(foreign_net), index=out.index).where(foreign_buy.notna() & foreign_sell.notna())
        valid_obs = persist_input.rolling(5, min_periods=1).count()
        persist_sum = persist_input.rolling(5, min_periods=1).sum()
        out["TW_FOREIGN_PERSIST_5D"] = np.where(valid_obs >= 3, persist_sum / valid_obs, np.nan)
        out["raw_institutional_date"] = out["date"]
        out = out[["date", "raw_institutional_date", *FACTORS]]

        boundary_rows.extend(
            [
                {"metric": "raw_primary_rows_after_saturday_filter", "value": int(primary.shape[0])},
                {"metric": "negative_primary_rows_after_saturday_filter", "value": int(negative_after_filter.shape[0])},
                {"metric": "missing_or_nonpositive_volume_rows", "value": int((volume.isna() | (volume <= 0)).sum())},
                {"metric": "missing_or_nonpositive_close_rows", "value": int((close.isna() | (close <= 0)).sum())},
                {"metric": "missing_foreign_buy_sell_rows", "value": int((foreign_buy.isna() | foreign_sell.isna()).sum())},
                {"metric": "missing_trust_buy_sell_rows", "value": int((trust_buy.isna() | trust_sell.isna()).sum())},
                {"metric": "insufficient_persist_window_rows", "value": int((valid_obs < 3).sum())},
            ]
        )

    saturday_summary = (
        saturday.groupby("date")
        .size()
        .rename("filtered_rows")
        .reset_index()
        .assign(date=lambda df: df["date"].dt.strftime("%Y-%m-%d"))
    )
    return out, saturday_summary, pd.DataFrame(boundary_rows)


def materialize_symbol(row: pd.Series) -> tuple[pd.DataFrame, dict[str, object], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    symbol = str(row["qlib_symbol"])
    stock_id = str(row["stock_id"])
    exchange = str(row.get("exchange", "UNKNOWN"))
    price = read_price_calendar(symbol)
    raw = read_raw_institutional(stock_id)
    schema = summarize_schema(raw, symbol, stock_id, exchange)
    raw_factors, saturday_summary, boundary_metrics = compute_raw_factors(raw, price)

    if price.empty:
        aligned = pd.DataFrame(columns=["qlib_symbol", "stock_id", "exchange", "date", "raw_institutional_date", *FACTORS])
    else:
        aligned = price[["qlib_symbol", "date"]].merge(raw_factors, on="date", how="left")
        aligned["stock_id"] = stock_id
        aligned["exchange"] = exchange
        for col in ["raw_institutional_date", *FACTORS]:
            aligned[col] = aligned[col].shift(1)
        aligned = aligned[["qlib_symbol", "stock_id", "exchange", "date", "raw_institutional_date", *FACTORS]]

    if not saturday_summary.empty:
        saturday_summary.insert(0, "qlib_symbol", symbol)
        saturday_summary.insert(1, "stock_id", stock_id)
        saturday_summary.insert(2, "exchange", exchange)

    if not boundary_metrics.empty:
        boundary_metrics.insert(0, "qlib_symbol", symbol)
        boundary_metrics.insert(1, "stock_id", stock_id)
        boundary_metrics.insert(2, "exchange", exchange)

    summary = {
        "qlib_symbol": symbol,
        "stock_id": stock_id,
        "exchange": exchange,
        "price_rows": int(price.shape[0]),
        "raw_rows": int(raw.shape[0]),
        "raw_non_saturday_rows": int((raw["date"].dt.weekday != 5).sum()) if not raw.empty else 0,
        "same_day_raw_matches": int(price["date"].isin(raw.loc[raw["date"].dt.weekday != 5, "date"]).sum()) if not price.empty and not raw.empty else 0,
        "shifted_source_rows": int(aligned["raw_institutional_date"].notna().sum()) if not aligned.empty else 0,
        **{factor.lower() + "_finite": int(aligned[factor].notna().sum()) if not aligned.empty else 0 for factor in FACTORS},
    }
    return aligned, summary, schema, saturday_summary, boundary_metrics


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
    rows = [
        {"metric": "symbols_total", "value": int(status.shape[0])},
        {"metric": "true_empty_symbols", "value": int(true_empty.shape[0])},
        {"metric": "late_start_symbols_lt_50pct_same_day_match", "value": int(late_start.shape[0])},
        {"metric": "price_rows", "value": int(features.shape[0])},
        {"metric": "price_rows_without_shifted_institutional_source", "value": int(features["raw_institutional_date"].isna().sum())},
    ]
    for factor in FACTORS:
        rows.append({"metric": f"{factor.lower()}_missing_rows", "value": int(features[factor].isna().sum())})
    return pd.DataFrame(rows)


def summarize_schema_guard(schema: pd.DataFrame) -> pd.DataFrame:
    totals = schema[
        [
            "symbol_date_rows",
            "category_count_3",
            "category_count_4",
            "category_count_5",
            "category_count_other",
            "foreign_trust_both_present",
            "foreign_trust_missing",
        ]
    ].sum(numeric_only=True)
    return pd.DataFrame(
        [
            {"metric": "symbol_date_rows", "value": int(totals["symbol_date_rows"])},
            {"metric": "category_count_3", "value": int(totals["category_count_3"])},
            {"metric": "category_count_4", "value": int(totals["category_count_4"])},
            {"metric": "category_count_5", "value": int(totals["category_count_5"])},
            {"metric": "category_count_other", "value": int(totals["category_count_other"])},
            {"metric": "foreign_trust_both_present", "value": int(totals["foreign_trust_both_present"])},
            {"metric": "foreign_trust_missing", "value": int(totals["foreign_trust_missing"])},
            {"metric": "uses_dealer_categories", "value": 0},
            {"metric": "uses_foreign_dealer_self", "value": 0},
        ]
    )


def summarize_saturday_guard(saturday: pd.DataFrame) -> pd.DataFrame:
    if saturday.empty:
        return pd.DataFrame(columns=["date", "weekday", "filtered_rows", "symbols"])
    grouped = saturday.groupby("date").agg(filtered_rows=("filtered_rows", "sum"), symbols=("qlib_symbol", "nunique")).reset_index()
    grouped["weekday"] = "Saturday"
    return grouped[["date", "weekday", "filtered_rows", "symbols"]]


def summarize_boundary(boundary: pd.DataFrame) -> pd.DataFrame:
    if boundary.empty:
        return pd.DataFrame(columns=["metric", "value"])
    return boundary.groupby("metric", as_index=False)["value"].sum()


def build_pit_validation(features: pd.DataFrame, schema: pd.DataFrame, saturday_guard: pd.DataFrame) -> pd.DataFrame:
    rows = []
    targets = ["TW2330"]
    targets.extend(features.loc[features["exchange"].eq("TWSE"), "qlib_symbol"].drop_duplicates().head(2).tolist())
    targets.extend(features.loc[features["exchange"].eq("TPEX"), "qlib_symbol"].drop_duplicates().head(2).tolist())
    low_schema = schema.sort_values("symbol_date_rows").loc[lambda df: df["symbol_date_rows"] > 0, "qlib_symbol"].head(1).tolist()
    targets.extend(low_schema)
    targets = list(dict.fromkeys(targets))
    for symbol in targets:
        g = features[features["qlib_symbol"].eq(symbol)].sort_values("date")
        if g.empty:
            continue
        sample = g[g["raw_institutional_date"].notna()].head(2)
        for _, r in sample.iterrows():
            prev_price_date = g.loc[g["date"] < r["date"], "date"].max()
            rows.append(
                {
                    "case": "pit_shift_sample",
                    "qlib_symbol": symbol,
                    "exchange": r["exchange"],
                    "feature_date": r["date"].strftime("%Y-%m-%d"),
                    "previous_price_date": prev_price_date.strftime("%Y-%m-%d") if pd.notna(prev_price_date) else "",
                    "raw_institutional_date": r["raw_institutional_date"].strftime("%Y-%m-%d") if pd.notna(r["raw_institutional_date"]) else "",
                    "pit_pass": bool(pd.notna(prev_price_date) and pd.notna(r["raw_institutional_date"]) and prev_price_date == r["raw_institutional_date"]),
                    **{factor.lower(): r[factor] for factor in FACTORS},
                }
            )
    missing = features[features["raw_institutional_date"].isna()].head(5)
    for _, r in missing.iterrows():
        rows.append(
            {
                "case": "price_exists_institutional_missing",
                "qlib_symbol": r["qlib_symbol"],
                "exchange": r["exchange"],
                "feature_date": r["date"].strftime("%Y-%m-%d"),
                "previous_price_date": "",
                "raw_institutional_date": "",
                "pit_pass": True,
                **{factor.lower(): r[factor] for factor in FACTORS},
            }
        )
    for date in saturday_guard["date"].head(6) if not saturday_guard.empty else []:
        rows.append(
            {
                "case": "saturday_filtered",
                "qlib_symbol": "",
                "exchange": "",
                "feature_date": "",
                "previous_price_date": "",
                "raw_institutional_date": date,
                "pit_pass": True,
                **{factor.lower(): np.nan for factor in FACTORS},
            }
        )
    return pd.DataFrame(rows)


def write_feature_csvs(features: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    feature_dir = out_dir / "features_by_symbol"
    feature_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    cols = ["qlib_symbol", "date", "raw_institutional_date", "exchange"]
    for factor in FACTORS:
        cols.extend([factor, f"{factor}_rank", f"{factor}_zscore"])
    for symbol, g in features.groupby("qlib_symbol", sort=True):
        path = feature_dir / f"{symbol}.csv"
        out = g[cols].copy()
        out["date"] = out["date"].dt.strftime("%Y-%m-%d")
        out["raw_institutional_date"] = pd.to_datetime(out["raw_institutional_date"]).dt.strftime("%Y-%m-%d")
        out.to_csv(path, index=False)
        row = {"qlib_symbol": symbol, "path": str(path.relative_to(ROOT)), "rows": int(out.shape[0])}
        for factor in FACTORS:
            row[f"{factor.lower()}_finite"] = int(out[factor].notna().sum())
        rows.append(row)
    return pd.DataFrame(rows)


def to_candidate_frame(features: pd.DataFrame) -> pd.DataFrame:
    idx = pd.MultiIndex.from_frame(
        features[["date", "qlib_symbol"]].rename(columns={"date": "datetime", "qlib_symbol": "instrument"})
    )
    return pd.DataFrame({factor: features[factor].to_numpy() for factor in FACTORS}, index=idx).sort_index()


def calc_pairwise_daily_corr(candidates: pd.DataFrame, pairs: list[tuple[str, str]]) -> pd.DataFrame:
    rows = []
    for left, right in pairs:
        vals = []
        for _, g in candidates[[left, right]].groupby(level="datetime", sort=True):
            valid = g.dropna()
            if valid.shape[0] < 10 or valid[left].nunique() < 2 or valid[right].nunique() < 2:
                continue
            vals.append(valid[left].rank().corr(valid[right].rank()))
        rows.append(
            {
                "left": left,
                "right": right,
                "daily_observations": len(vals),
                "mean_spearman_corr": float(np.nanmean(vals)) if vals else np.nan,
                "abs_mean_spearman_corr": float(abs(np.nanmean(vals))) if vals else np.nan,
                "advisory": "pa56_high_corr" if left == "TW_INST_CONSENSUS" and right == "TW_FOREIGN_NET_VOL" and vals and abs(np.nanmean(vals)) > 0.8 else "",
            }
        )
    return pd.DataFrame(rows)


def calc_momentum_overlap(candidates: pd.DataFrame, alpha158: pd.DataFrame) -> pd.DataFrame:
    available = [col for col in MOMENTUM_FEATURES if col in alpha158.columns]
    rows = []
    test_idx = (slice(pd.Timestamp("2023-01-01"), pd.Timestamp("2025-06-30")), slice(None))
    cand_test = candidates.loc[test_idx, FACTORS]
    alpha_test = alpha158.loc[test_idx, available] if available else pd.DataFrame(index=cand_test.index)
    for factor in FACTORS:
        for alpha_col in available:
            vals = []
            for date, xg in cand_test[[factor]].groupby(level="datetime", sort=True):
                if date not in alpha_test.index.get_level_values("datetime"):
                    continue
                joined = alpha_test.xs(date, level="datetime")[[alpha_col]].join(xg.droplevel("datetime"), how="inner").dropna()
                if joined.shape[0] < 10 or joined[factor].nunique() < 2 or joined[alpha_col].nunique() < 2:
                    continue
                vals.append(joined[factor].rank().corr(joined[alpha_col].rank()))
            rows.append(
                {
                    "factor": factor,
                    "alpha158_feature": alpha_col,
                    "daily_observations": len(vals),
                    "mean_spearman_corr": float(np.nanmean(vals)) if vals else np.nan,
                    "abs_mean_spearman_corr": float(abs(np.nanmean(vals))) if vals else np.nan,
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Materialize TW institutional flow factors to CSV and diagnostics only.")
    parser.add_argument("--output-dir", default="data_tw/experiments/tw_institutional_factors_materialized")
    parser.add_argument("--skip-alpha158-corr", action="store_true")
    args = parser.parse_args()

    out_dir = ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    status = load_status()

    feature_frames = []
    summary_rows = []
    schema_frames = []
    saturday_frames = []
    boundary_frames = []
    for _, row in status.iterrows():
        features, summary, schema, saturday_summary, boundary_metrics = materialize_symbol(row)
        if not features.empty:
            feature_frames.append(features)
        summary_rows.append(summary)
        schema_frames.append(schema)
        if not saturday_summary.empty:
            saturday_frames.append(saturday_summary)
        if not boundary_metrics.empty:
            boundary_frames.append(boundary_metrics)

    all_features = pd.concat(feature_frames, ignore_index=True) if feature_frames else pd.DataFrame()
    all_features = add_normalized_features(all_features)
    symbol_summary = pd.DataFrame(summary_rows)
    schema = pd.concat(schema_frames, ignore_index=True) if schema_frames else pd.DataFrame()
    saturday = pd.concat(saturday_frames, ignore_index=True) if saturday_frames else pd.DataFrame(columns=["date", "filtered_rows"])
    boundary = pd.concat(boundary_frames, ignore_index=True) if boundary_frames else pd.DataFrame(columns=["metric", "value"])

    feature_manifest = write_feature_csvs(all_features, out_dir)
    coverage = summarize_coverage(all_features)
    distribution = summarize_distribution(all_features)
    missingness = summarize_missingness(all_features, symbol_summary, status)
    schema_guard = summarize_schema_guard(schema)
    saturday_guard = summarize_saturday_guard(saturday)
    boundary_summary = summarize_boundary(boundary)
    pit_validation = build_pit_validation(all_features, schema, saturday_guard)
    candidates = to_candidate_frame(all_features)
    pa56 = calc_pairwise_daily_corr(candidates, [("TW_INST_CONSENSUS", "TW_FOREIGN_NET_VOL")])

    symbol_summary.to_csv(out_dir / "symbol_materialization_summary.csv", index=False)
    feature_manifest.to_csv(out_dir / "feature_manifest.csv", index=False)
    coverage.to_csv(out_dir / "coverage_by_segment_exchange.csv", index=False)
    distribution.to_csv(out_dir / "distribution_by_segment_exchange.csv", index=False)
    missingness.to_csv(out_dir / "missingness_summary.csv", index=False)
    schema.to_csv(out_dir / "schema_by_symbol_summary.csv", index=False)
    schema_guard.to_csv(out_dir / "pa54_schema_guard.csv", index=False)
    saturday_guard.to_csv(out_dir / "pa55_saturday_filter_guard.csv", index=False)
    boundary_summary.to_csv(out_dir / "boundary_checks.csv", index=False)
    pit_validation.to_csv(out_dir / "pit_validation_samples.csv", index=False)
    pa56.to_csv(out_dir / "pa56_consensus_foreign_corr.csv", index=False)

    if args.skip_alpha158_corr:
        corr = pd.DataFrame({"factor": FACTORS, "corr_gate": "skipped"})
        detail = pd.DataFrame()
        momentum = pd.DataFrame()
    else:
        qlib.init(provider_uri=str(ROOT / PROVIDER), region="tw", expression_cache=None, dataset_cache=None)
        alpha158 = fetch_alpha158()
        corr, detail = calc_alpha158_corr(candidates, alpha158, FACTORS)
        momentum = calc_momentum_overlap(candidates, alpha158)
    corr.to_csv(out_dir / "institutional_alpha158_corr.csv", index=False)
    detail.to_csv(out_dir / "institutional_alpha158_corr_detail.csv", index=False)
    momentum.to_csv(out_dir / "institutional_momentum_overlap.csv", index=False)

    print(f"symbols={status.shape[0]}")
    print(f"feature_rows={all_features.shape[0]}")
    print(f"feature_files={feature_manifest.shape[0]}")
    print(f"pit_validation_pass={bool(pit_validation['pit_pass'].all()) if not pit_validation.empty else False}")
    print(f"pa54_foreign_trust_missing={int(schema_guard.loc[schema_guard['metric'].eq('foreign_trust_missing'), 'value'].iloc[0]) if not schema_guard.empty else -1}")
    print(f"pa55_saturday_filtered_rows={int(saturday_guard['filtered_rows'].sum()) if not saturday_guard.empty else 0}")
    print(f"pa56_consensus_foreign_corr={pa56['mean_spearman_corr'].iloc[0] if not pa56.empty else np.nan}")
    print(f"wrote {out_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
