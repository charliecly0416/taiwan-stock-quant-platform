#!/usr/bin/env python3
"""Restricted Phase 1B readonly analysis for TW decision orthogonal data.

Inputs are limited to Phase 0E normalized PIT archives and existing local
qlib/price artifacts. The script does not download data, write qlib providers,
switch accepted latest, train models, build rules, or touch trading paths.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
QLIB = ROOT / "qlib_pipeline"
OUT_DIR = ROOT / "data_tw/experiments/decision_orthogonal"
DOC_DIR = ROOT / "docs/tw_decision_model_orthogonal"
MANIFEST_PATH = OUT_DIR / "phase0e_pit_snapshot_manifest.csv"
COVERAGE_PATH = OUT_DIR / "phase0e_coverage_report.csv"
QUALITY_PATH = OUT_DIR / "phase0e_quality_flags_summary.csv"
PRICE_ROOT = QLIB / "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"
SIGNAL_ROOT = QLIB / "data_tw/experiments/option_c_historical_signal_backfill"
DAILY_SIGNAL_ROOT = QLIB / "data_tw/experiments/option_c_daily_signal"
REPAIRED_2023_2024_BATCH = "option_c_historical_backfill_20230101_20241231_asof_aware_research_only"
SAMPLES_PATH = OUT_DIR / "phase1b_samples.parquet"
PREVIEW_PATH = OUT_DIR / "phase1b_samples_preview.csv"
SCHEMA_PATH = OUT_DIR / "phase1b_schema.json"
METRICS_PATH = OUT_DIR / "phase1b_factor_metrics.csv"
SEGMENT_METRICS_PATH = OUT_DIR / "phase1b_segment_metrics.csv"
MONTHLY_SAMPLE_PATH = OUT_DIR / "phase1b_monthly_sample_size.csv"
LEAKAGE_REPORT_PATH = OUT_DIR / "phase1b_leakage_audit_report.md"
FACTOR_REPORT_PATH = OUT_DIR / "phase1b_factor_increment_report.md"
EXEC_REPORT_PATH = DOC_DIR / "PHASE1B_EXECUTION_REPORT_CN.md"


def apply_output_prefix(prefix: str) -> None:
    global SAMPLES_PATH, PREVIEW_PATH, SCHEMA_PATH, METRICS_PATH, SEGMENT_METRICS_PATH
    global MONTHLY_SAMPLE_PATH, LEAKAGE_REPORT_PATH, FACTOR_REPORT_PATH, EXEC_REPORT_PATH
    SAMPLES_PATH = OUT_DIR / f"{prefix}_samples.parquet"
    PREVIEW_PATH = OUT_DIR / f"{prefix}_samples_preview.csv"
    SCHEMA_PATH = OUT_DIR / f"{prefix}_schema.json"
    METRICS_PATH = OUT_DIR / f"{prefix}_factor_metrics.csv"
    SEGMENT_METRICS_PATH = OUT_DIR / f"{prefix}_segment_metrics.csv"
    MONTHLY_SAMPLE_PATH = OUT_DIR / f"{prefix}_monthly_sample_size.csv"
    LEAKAGE_REPORT_PATH = OUT_DIR / f"{prefix}_leakage_audit_report.md"
    FACTOR_REPORT_PATH = OUT_DIR / f"{prefix}_factor_increment_report.md"
    doc_name = "PHASE1B_EXECUTION_REPORT_CN.md" if prefix == "phase1b" else f"{prefix.upper()}_EXECUTION_REPORT_CN.md"
    EXEC_REPORT_PATH = DOC_DIR / doc_name
HORIZONS = [5, 10, 20]
ROLL_WINDOWS = [5, 10, 20]
INST_BASE = ["foreign_net_buy", "investment_trust_net_buy", "dealer_net_buy", "institutional_total_net_buy"]
MARGIN_BASE = ["margin_balance", "margin_balance_change", "short_balance", "short_balance_change"]
QLIB_FEATURES = ["qlib_score_raw", "qlib_rank", "qlib_score_percentile_by_date", "qlib_score_zscore_by_date"]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def ensure_dirs() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)


def parse_date_from_path(path: Path) -> pd.Timestamp | None:
    match = re.search(r"option_c_daily_signal_(\d{8})", str(path))
    if not match:
        return None
    return pd.Timestamp(datetime.strptime(match.group(1), "%Y%m%d")).normalize()


def load_manifest() -> pd.DataFrame:
    manifest = pd.read_csv(MANIFEST_PATH)
    required = {"category", "archive_path", "first_trade_date", "last_trade_date"}
    missing = required - set(manifest.columns)
    if missing:
        raise RuntimeError(f"Phase0E manifest missing columns: {sorted(missing)}")
    return manifest


def archive_path(manifest: pd.DataFrame, category: str) -> Path:
    rows = manifest[manifest["category"] == category]
    if rows.empty:
        raise RuntimeError(f"Phase0E manifest has no category={category}")
    path = ROOT / str(rows.iloc[0]["archive_path"])
    if not path.exists():
        raise RuntimeError(f"Phase0E archive missing: {path}")
    return path


def load_phase0e() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    manifest = load_manifest()
    inst = pd.read_csv(archive_path(manifest, "institutional_flow"), dtype={"stock_id": str})
    margin = pd.read_csv(archive_path(manifest, "margin_short"), dtype={"stock_id": str})
    for name, df in [("institutional_flow", inst), ("margin_short", margin)]:
        df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce").dt.normalize()
        df["available_at"] = pd.to_datetime(df["available_at"], errors="coerce").dt.normalize()
        df["symbol"] = df["symbol"].astype(str)
        missing_available = int(df["available_at"].isna().sum())
        if missing_available:
            raise RuntimeError(f"Phase0E normalized {name} has missing available_at rows: {missing_available}")
    return inst, margin, manifest


def rolling_zscore(s: pd.Series, window: int) -> pd.Series:
    mean = s.rolling(window, min_periods=3).mean()
    std = s.rolling(window, min_periods=3).std().replace(0, np.nan)
    return ((s - mean) / std).replace([np.inf, -np.inf], np.nan)


def add_feature_rolls(inst: pd.DataFrame, margin: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    inst = inst.sort_values(["symbol", "available_at", "trade_date"]).copy()
    margin = margin.sort_values(["symbol", "available_at", "trade_date"]).copy()
    features: list[str] = []
    for col in INST_BASE:
        inst[col] = pd.to_numeric(inst[col], errors="coerce")
        features.append(col)
        for window in ROLL_WINDOWS:
            sum_col = f"{col}_{window}d_sum"
            z_col = f"{col}_{window}d_zscore"
            inst[sum_col] = inst.groupby("symbol")[col].transform(lambda s, w=window: s.rolling(w, min_periods=1).sum())
            inst[z_col] = inst.groupby("symbol")[col].transform(lambda s, w=window: rolling_zscore(s, w))
            features.extend([sum_col, z_col])
    inst["foreign_trust_sync_direction"] = np.select(
        [
            (inst["foreign_net_buy"] > 0) & (inst["investment_trust_net_buy"] > 0),
            (inst["foreign_net_buy"] < 0) & (inst["investment_trust_net_buy"] < 0),
        ],
        [1, -1],
        default=0,
    )
    features.append("foreign_trust_sync_direction")
    for col in MARGIN_BASE:
        margin[col] = pd.to_numeric(margin[col], errors="coerce")
        features.append(col)
        for window in ROLL_WINDOWS:
            roll_col = f"{col}_{window}d_sum" if col.endswith("_change") else f"{col}_{window}d_mean"
            z_col = f"{col}_{window}d_zscore"
            if col.endswith("_change"):
                margin[roll_col] = margin.groupby("symbol")[col].transform(lambda s, w=window: s.rolling(w, min_periods=1).sum())
            else:
                margin[roll_col] = margin.groupby("symbol")[col].transform(lambda s, w=window: s.rolling(w, min_periods=1).mean())
            margin[z_col] = margin.groupby("symbol")[col].transform(lambda s, w=window: rolling_zscore(s, w))
            features.extend([roll_col, z_col])
    return inst, margin, sorted(set(features))


def prediction_paths(start: pd.Timestamp, end: pd.Timestamp) -> list[Path]:
    paths = [Path(p) for p in glob.glob(str(SIGNAL_ROOT / "*/*/prediction.csv"))]
    paths += [Path(p) for p in glob.glob(str(DAILY_SIGNAL_ROOT / "*/prediction.csv"))]
    out = []
    for path in paths:
        day = parse_date_from_path(path)
        if day is not None and start <= day <= end:
            out.append(path)
    return sorted(set(out))


def prediction_path_priority(path: Path) -> int:
    """Prefer the repaired asof-aware 2023-2024 artifact when duplicates exist."""
    text = str(path)
    if REPAIRED_2023_2024_BATCH in text:
        return 30
    if "pred_fast" in text:
        return -10
    if "research_only" in text:
        return 0
    return 10


def load_predictions(symbols: set[str], start: pd.Timestamp, end: pd.Timestamp) -> tuple[pd.DataFrame, int]:
    rows: dict[tuple[pd.Timestamp, str], tuple[float, str]] = {}
    paths = sorted(prediction_paths(start, end), key=lambda p: (parse_date_from_path(p) or pd.Timestamp.min, prediction_path_priority(p), str(p)))
    for path in paths:
        try:
            df = pd.read_csv(path, usecols=["datetime", "instrument", "score"])
        except Exception:
            continue
        df["asof"] = pd.to_datetime(df["datetime"], errors="coerce").dt.normalize()
        df["symbol"] = df["instrument"].astype(str)
        df["score"] = pd.to_numeric(df["score"], errors="coerce")
        df = df[(df["asof"] >= start) & (df["asof"] <= end) & (df["symbol"].isin(symbols)) & df["score"].notna()]
        for row in df.itertuples(index=False):
            rows[(row.asof, row.symbol)] = (float(row.score), rel(path))
    pred = pd.DataFrame(
        [
            {"asof": asof, "symbol": symbol, "qlib_score_raw": score, "qlib_prediction_path": path}
            for (asof, symbol), (score, path) in rows.items()
        ]
    )
    if pred.empty:
        return pred, len(paths)
    pred = pred.sort_values(["asof", "symbol"]).reset_index(drop=True)
    pred["qlib_rank"] = pred.groupby("asof")["qlib_score_raw"].rank(method="first", ascending=False).astype(int)
    grouped = pred.groupby("asof")["qlib_score_raw"]
    pred["qlib_score_percentile_by_date"] = grouped.rank(method="average", pct=True)
    daily_mean = grouped.transform("mean")
    daily_std = grouped.transform("std").replace(0, np.nan)
    pred["qlib_score_zscore_by_date"] = ((pred["qlib_score_raw"] - daily_mean) / daily_std).fillna(0.0)
    pred["top50_flag"] = pred["qlib_rank"] <= 50
    pred["top150_flag"] = pred["qlib_rank"] <= 150
    return pred, len(paths)


def load_price(symbol: str) -> pd.DataFrame:
    path = PRICE_ROOT / f"{symbol}.csv"
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, usecols=["date", "close", "volume"])
    except Exception:
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
    return df.dropna(subset=["date", "close"]).sort_values("date").reset_index(drop=True)


def add_forward_labels(samples: pd.DataFrame, symbols: set[str]) -> pd.DataFrame:
    price_rows = []
    for symbol in sorted(symbols):
        df = load_price(symbol)
        if df.empty:
            continue
        for horizon in HORIZONS:
            df[f"fwd_{horizon}d_return"] = df["close"].shift(-horizon) / df["close"] - 1.0
            df[f"fwd_{horizon}d_date"] = df["date"].shift(-horizon)
        df["symbol"] = symbol
        price_rows.append(df[["symbol", "date", "close", "volume"] + [f"fwd_{h}d_return" for h in HORIZONS] + [f"fwd_{h}d_date" for h in HORIZONS]])
    prices = pd.concat(price_rows, ignore_index=True) if price_rows else pd.DataFrame()
    if prices.empty:
        raise RuntimeError("no local price rows found for Phase1B symbols")
    twii = load_price("TWII")
    if twii.empty:
        raise RuntimeError("TWII local price file missing")
    for horizon in HORIZONS:
        twii[f"market_fwd_{horizon}d_return"] = twii["close"].shift(-horizon) / twii["close"] - 1.0
        twii[f"market_fwd_{horizon}d_date"] = twii["date"].shift(-horizon)
    twii = twii[["date"] + [f"market_fwd_{h}d_return" for h in HORIZONS] + [f"market_fwd_{h}d_date" for h in HORIZONS]]
    out = samples.merge(prices, left_on=["asof", "symbol"], right_on=["date", "symbol"], how="left")
    out = out.merge(twii, left_on="asof", right_on="date", how="left", suffixes=("", "_market"))
    for horizon in HORIZONS:
        out[f"fwd_{horizon}d_excess_return"] = out[f"fwd_{horizon}d_return"] - out[f"market_fwd_{horizon}d_return"]
    return out.drop(columns=[col for col in ["date", "date_market"] if col in out.columns])


def pit_join(base: pd.DataFrame, features: pd.DataFrame, suffix: str) -> pd.DataFrame:
    chunks = []
    right = features.sort_values(["symbol", "available_at", "trade_date"]).copy()
    for symbol, left_g in base.sort_values(["symbol", "asof"]).groupby("symbol"):
        right_g = right[right["symbol"] == symbol].copy()
        left_g = left_g.sort_values("asof").copy()
        if right_g.empty:
            chunks.append(left_g)
            continue
        merged = pd.merge_asof(
            left_g,
            right_g.sort_values("available_at"),
            left_on="asof",
            right_on="available_at",
            by="symbol",
            direction="backward",
            suffixes=("", suffix),
        )
        chunks.append(merged)
    return pd.concat(chunks, ignore_index=True) if chunks else base


def add_cross_sectional_ranks(samples: pd.DataFrame, feature_cols: list[str]) -> tuple[pd.DataFrame, list[str]]:
    rank_cols = []
    out = samples.copy()
    for col in feature_cols:
        if col in out.columns:
            rank_col = f"{col}_cs_rank_pct"
            out[rank_col] = out.groupby("asof")[col].rank(method="average", pct=True)
            rank_cols.append(rank_col)
    return out, rank_cols


def build_samples(args: argparse.Namespace) -> tuple[pd.DataFrame, dict[str, Any], list[str], pd.DataFrame]:
    inst, margin, manifest = load_phase0e()
    inst, margin, feature_cols = add_feature_rolls(inst, margin)
    symbols = set(inst["symbol"]) | set(margin["symbol"])
    start = max(inst["available_at"].min(), margin["available_at"].min(), pd.Timestamp(args.start))
    end = min(inst["available_at"].max(), margin["available_at"].max(), pd.Timestamp(args.end))
    predictions, path_count = load_predictions(symbols, start.normalize(), end.normalize())
    build_info: dict[str, Any] = {
        "generated_at": utc_now(),
        "phase": "phase1b_restricted_readonly",
        "symbols_in_phase0e_archive": len(symbols),
        "phase0e_available_start": start.strftime("%Y-%m-%d"),
        "phase0e_available_end": end.strftime("%Y-%m-%d"),
        "qlib_prediction_paths": path_count,
        "qlib_prediction_rows": int(len(predictions)),
        "coverage_input": rel(COVERAGE_PATH),
        "quality_input": rel(QUALITY_PATH),
        "manifest_input": rel(MANIFEST_PATH),
        "token_used": False,
        "network_used": False,
        "prediction_selection_rule": "latest duplicate by asof/symbol after sorting; repaired 2023-2024 asof-aware batch has highest priority, pred_fast has lowest priority",
        "repaired_2023_2024_batch": REPAIRED_2023_2024_BATCH,
    }
    if predictions.empty:
        return pd.DataFrame(), build_info, feature_cols, manifest
    inst_cols = ["symbol", "trade_date", "available_at", *[c for c in feature_cols if c in inst.columns], "data_source", "raw_snapshot_id"]
    margin_cols = ["symbol", "trade_date", "available_at", *[c for c in feature_cols if c in margin.columns], "data_source", "raw_snapshot_id"]
    samples = pit_join(predictions, inst[inst_cols], "_institutional")
    samples = samples.rename(columns={"trade_date": "institutional_trade_date", "available_at": "institutional_available_at", "data_source": "institutional_data_source", "raw_snapshot_id": "institutional_raw_snapshot_id"})
    samples = pit_join(samples, margin[margin_cols], "_margin")
    samples = samples.rename(columns={"trade_date": "margin_trade_date", "available_at": "margin_available_at", "data_source": "margin_data_source", "raw_snapshot_id": "margin_raw_snapshot_id"})
    samples = add_forward_labels(samples, symbols)
    samples["year"] = samples["asof"].dt.strftime("%Y")
    samples["quarter"] = samples["asof"].dt.to_period("Q").astype(str)
    samples["month"] = samples["asof"].dt.strftime("%Y-%m")
    samples["pit_join_valid"] = samples["institutional_available_at"].notna() & samples["margin_available_at"].notna() & (samples["institutional_available_at"] <= samples["asof"]) & (samples["margin_available_at"] <= samples["asof"])
    excluded_missing_pit_rows = int((~samples["pit_join_valid"]).sum())
    samples = samples[samples["pit_join_valid"]].copy()
    samples, rank_cols = add_cross_sectional_ranks(samples, feature_cols)
    build_info.update({
        "excluded_missing_pit_rows": excluded_missing_pit_rows,
        "sample_rows": int(len(samples)),
        "sample_asof_start": samples["asof"].min().strftime("%Y-%m-%d"),
        "sample_asof_end": samples["asof"].max().strftime("%Y-%m-%d"),
        "sample_symbol_count": int(samples["symbol"].nunique()),
        "top50_sample_rows": int(samples["top50_flag"].sum()),
        "top150_sample_rows": int(samples["top150_flag"].sum()),
        "feature_count": len(feature_cols),
        "rank_feature_count": len(rank_cols),
    })
    return samples.sort_values(["asof", "qlib_rank", "symbol"]).reset_index(drop=True), build_info, feature_cols + rank_cols, manifest


def safe_corr(df: pd.DataFrame, x: str, y: str, method: str) -> float:
    sub = df[[x, y]].dropna()
    if len(sub) < 5 or sub[x].nunique() < 2 or sub[y].nunique() < 2:
        return float("nan")
    return float(sub[x].corr(sub[y], method=method))


def valid_period_count(sub: pd.DataFrame, feature: str, label: str) -> int:
    counts = sub.groupby("asof")[[feature, label]].nunique(dropna=True)
    return int(((counts[feature] >= 2) & (counts[label] >= 2)).sum())


def pooled_rankic(seg_df: pd.DataFrame, feature: str, label: str) -> tuple[float, int, int]:
    sub = seg_df[["asof", feature, label]].dropna().copy()
    if len(sub) < 5:
        return float("nan"), 0, 0
    periods = valid_period_count(sub, feature, label)
    if periods == 0:
        return float("nan"), 0, 0
    sub["feature_rank"] = sub.groupby("asof")[feature].rank(method="average")
    sub["label_rank"] = sub.groupby("asof")[label].rank(method="average")
    return safe_corr(sub, "feature_rank", "label_rank", "pearson"), int(len(sub)), periods


def pooled_ic(seg_df: pd.DataFrame, feature: str, label: str) -> tuple[float, int, int]:
    sub = seg_df[["asof", feature, label]].dropna()
    periods = valid_period_count(sub, feature, label) if len(sub) else 0
    return safe_corr(sub, feature, label, "pearson"), int(len(sub)), periods


def daily_corr_mean(seg_df: pd.DataFrame, feature: str, label: str, method: str) -> tuple[float, int, int]:
    values: list[float] = []
    n_total = 0
    for _, g in seg_df[["asof", feature, label]].dropna().groupby("asof", sort=False):
        if len(g) < 5 or g[feature].nunique() < 2 or g[label].nunique() < 2:
            continue
        corr = safe_corr(g, feature, label, method)
        if pd.notna(corr) and math.isfinite(float(corr)):
            values.append(float(corr))
            n_total += len(g)
    return (float(np.mean(values)) if values else float("nan"), int(n_total), len(values))


def rankic_metrics(samples: pd.DataFrame, features: list[str], segment_col: str | None = None, metrics_mode: str = "fast") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    segment_items = [("all", samples)] if segment_col is None else list(samples.groupby(segment_col, sort=True))
    for segment, seg_df in segment_items:
        for feature in features + QLIB_FEATURES:
            if feature not in seg_df.columns:
                continue
            for horizon in HORIZONS:
                label = f"fwd_{horizon}d_excess_return"
                if metrics_mode == "full":
                    value, n_total, periods = daily_corr_mean(seg_df, feature, label, "spearman")
                    rows.append({"metric_type": "rankic_spearman_daily_mean", "feature": feature, "label": label, "segment_type": segment_col or "all", "segment": str(segment), "n": n_total, "valid_periods": periods, "value": value})
                    value, n_total, periods = daily_corr_mean(seg_df, feature, label, "pearson")
                    rows.append({"metric_type": "ic_pearson_daily_mean", "feature": feature, "label": label, "segment_type": segment_col or "all", "segment": str(segment), "n": n_total, "valid_periods": periods, "value": value})
                else:
                    value, n_total, periods = pooled_rankic(seg_df, feature, label)
                    rows.append({"metric_type": "rankic_spearman_pooled_by_asof", "feature": feature, "label": label, "segment_type": segment_col or "all", "segment": str(segment), "n": n_total, "valid_periods": periods, "value": value})
                    value, n_total, periods = pooled_ic(seg_df, feature, label)
                    rows.append({"metric_type": "ic_pearson_pooled", "feature": feature, "label": label, "segment_type": segment_col or "all", "segment": str(segment), "n": n_total, "valid_periods": periods, "value": value})
    return rows


def quantile_and_hit_metrics(samples: pd.DataFrame, features: list[str], segment_col: str | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    segment_items = [("all", samples)] if segment_col is None else list(samples.groupby(segment_col, sort=True))
    for segment, seg_df in segment_items:
        for feature in features:
            if feature not in seg_df.columns:
                continue
            for horizon in HORIZONS:
                label = f"fwd_{horizon}d_excess_return"
                sub = seg_df[[feature, label]].dropna()
                if len(sub) < 30 or sub[feature].nunique() < 3:
                    continue
                try:
                    sub = sub.copy()
                    sub["bucket"] = pd.qcut(sub[feature], q=3, labels=["low", "mid", "high"], duplicates="drop")
                except Exception:
                    continue
                high = sub[sub["bucket"].astype(str) == "high"]
                low = sub[sub["bucket"].astype(str) == "low"]
                if len(high) and len(low):
                    rows.append({"metric_type": "high_minus_low_mean_excess_return", "feature": feature, "label": label, "segment_type": segment_col or "all", "segment": str(segment), "n": int(len(high) + len(low)), "valid_periods": int(seg_df["asof"].nunique()), "value": float(high[label].mean() - low[label].mean())})
                    rows.append({"metric_type": "high_bucket_historical_positive_rate", "feature": feature, "label": label, "segment_type": segment_col or "all", "segment": str(segment), "n": int(len(high)), "valid_periods": int(seg_df["asof"].nunique()), "value": float((high[label] > 0).mean())})
    return rows


def qlib_relation_metrics(samples: pd.DataFrame, features: list[str], topn_features: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for feature in features:
        if feature not in samples.columns:
            continue
        for qlib_col in ["qlib_score_raw", "qlib_rank", "qlib_score_percentile_by_date"]:
            rows.append({"metric_type": "feature_vs_qlib_spearman", "feature": feature, "label": qlib_col, "segment_type": "all", "segment": "all", "n": int(len(samples[[feature, qlib_col]].dropna())), "valid_periods": int(samples["asof"].nunique()), "value": safe_corr(samples, feature, qlib_col, "spearman")})
    for feature in topn_features:
        if feature not in samples.columns:
            continue
        for top_col in ["top50_flag", "top150_flag"]:
            for flag_value, seg_name in [(True, f"{top_col}=inside"), (False, f"{top_col}=outside")]:
                seg_df = samples[samples[top_col] == flag_value]
                seg_rows = quantile_and_hit_metrics(seg_df, [feature], None)
                for row in seg_rows:
                    row["segment_type"] = top_col
                    row["segment"] = seg_name
                rows.extend(seg_rows)
    return rows


def build_metrics(samples: pd.DataFrame, features: list[str], metrics_mode: str = "fast") -> tuple[pd.DataFrame, pd.DataFrame]:
    topn_features = features if metrics_mode == "full" else features[:4]
    rows: list[dict[str, Any]] = []
    rows.extend(rankic_metrics(samples, features, metrics_mode=metrics_mode))
    rows.extend(quantile_and_hit_metrics(samples, features))
    rows.extend(qlib_relation_metrics(samples, features, topn_features))
    metrics = pd.DataFrame(rows)
    if not metrics.empty:
        metrics = metrics.sort_values(["metric_type", "feature", "label", "segment_type", "segment"]).reset_index(drop=True)
    segment_rows: list[dict[str, Any]] = []
    for segment_col in ["year", "quarter", "month"]:
        segment_rows.extend(rankic_metrics(samples, features, segment_col, metrics_mode=metrics_mode))
        segment_rows.extend(quantile_and_hit_metrics(samples, features, segment_col))
    segment_metrics = pd.DataFrame(segment_rows)
    if not segment_metrics.empty:
        segment_metrics = segment_metrics.sort_values(["segment_type", "segment", "metric_type", "feature", "label"]).reset_index(drop=True)
    return metrics, segment_metrics


def monthly_sample_size(samples: pd.DataFrame) -> pd.DataFrame:
    if samples.empty:
        return pd.DataFrame()
    return samples.groupby("month").agg(sample_rows=("symbol", "size"), symbol_count=("symbol", "nunique"), top50_rows=("top50_flag", "sum"), top150_rows=("top150_flag", "sum"), valid_pit_rows=("pit_join_valid", "sum")).reset_index()


def schema_doc(samples: pd.DataFrame, build_info: dict[str, Any], features: list[str]) -> dict[str, Any]:
    return {
        "generated_at": utc_now(),
        "phase": "phase1b_restricted_readonly",
        "grain": "asof + symbol",
        "build_info": build_info,
        "feature_alignment": "orthogonal feature rows are joined by latest available_at <= asof",
        "labels": [f"fwd_{h}d_excess_return" for h in HORIZONS],
        "orthogonal_features": features,
        "fields": [{"name": col, "dtype": str(samples[col].dtype), "non_null_count": int(samples[col].notna().sum()), "pit_note": "available_at <= asof required" if "available_at" in col else ""} for col in samples.columns],
        "forbidden_outputs": {"network": False, "token": False, "qlib_provider_write": False, "model_training": False, "rules_baseline": False, "phase2_auto_entry": False, "trading_actions": False},
    }


def leakage_audit(samples: pd.DataFrame, build_info: dict[str, Any]) -> dict[str, Any]:
    if samples.empty:
        return {"status": "fail", "checks": [{"check": "samples_present", "bad_rows": 1, "pass": False}]}
    checks: list[dict[str, Any]] = []
    inst_bad = int((samples["institutional_available_at"] > samples["asof"]).sum())
    margin_bad = int((samples["margin_available_at"] > samples["asof"]).sum())
    missing_pit = int((~samples["pit_join_valid"]).sum())
    same_day_inst_visible = int(((samples["institutional_trade_date"] == samples["asof"]) & samples["institutional_available_at"].notna()).sum())
    same_day_margin_visible = int(((samples["margin_trade_date"] == samples["asof"]) & samples["margin_available_at"].notna()).sum())
    checks.extend([
        {"check": "institutional_available_at_lte_asof", "bad_rows": inst_bad, "pass": inst_bad == 0},
        {"check": "margin_available_at_lte_asof", "bad_rows": margin_bad, "pass": margin_bad == 0},
        {"check": "all_feature_rows_have_pit_join", "bad_rows": missing_pit, "pass": missing_pit == 0},
        {"check": "same_day_institutional_trade_date_not_visible_same_day", "bad_rows": same_day_inst_visible, "pass": same_day_inst_visible == 0},
        {"check": "same_day_margin_trade_date_not_visible_same_day", "bad_rows": same_day_margin_visible, "pass": same_day_margin_visible == 0},
        {"check": "qlib_predictions_present", "bad_rows": 0 if build_info.get("qlib_prediction_rows", 0) else 1, "pass": build_info.get("qlib_prediction_rows", 0) > 0},
    ])
    for horizon in HORIZONS:
        date_col = f"fwd_{horizon}d_date"
        label_col = f"fwd_{horizon}d_excess_return"
        valid = samples[label_col].notna()
        bad = int((valid & (samples[date_col] <= samples["asof"])).sum())
        checks.append({"check": f"fwd_{horizon}d_label_date_gt_asof", "bad_rows": bad, "pass": bad == 0 and bool(valid.any())})
    return {"status": "pass" if all(c["pass"] for c in checks) else "fail", "checks": checks}


def format_metric(value: Any) -> str:
    try:
        if pd.isna(value):
            return "nan"
        if isinstance(value, (int, np.integer)):
            return str(int(value))
        return f"{float(value):.6f}"
    except Exception:
        return str(value)


def md_table(rows: list[dict[str, Any]], cols: list[str]) -> str:
    if not rows:
        return "_no rows_"
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---" for _ in cols]) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(format_metric(row.get(col, "")) for col in cols) + " |")
    return "\n".join(lines)


def phase1b_conclusion(samples: pd.DataFrame, metrics: pd.DataFrame, segment_metrics: pd.DataFrame, audit: dict[str, Any]) -> dict[str, Any]:
    if samples.empty or audit.get("status") != "pass":
        return {"gate": "request_more_data_or_repair=true", "reason": "样本为空或泄露审计未通过。"}
    rankic = metrics[(metrics["metric_type"].str.startswith("rankic_spearman")) & (~metrics["feature"].isin(QLIB_FEATURES)) & (metrics["valid_periods"] >= 20)].copy()
    corr = metrics[(metrics["metric_type"] == "feature_vs_qlib_spearman") & (metrics["label"] == "qlib_score_raw")].copy()
    if rankic.empty or corr.empty:
        return {"gate": "request_more_data_or_repair=true", "reason": "RankIC 或 qlib 相关性统计不足。"}
    stable_features = []
    for row in rankic.itertuples(index=False):
        seg = segment_metrics[(segment_metrics["metric_type"].str.startswith("rankic_spearman")) & (segment_metrics["segment_type"].isin(["year", "quarter"])) & (segment_metrics["feature"] == row.feature) & (segment_metrics["label"] == row.label) & (segment_metrics["valid_periods"] >= 5)]
        seg_values = seg["value"].dropna()
        if seg_values.empty:
            continue
        same_sign_share = float((np.sign(seg_values) == np.sign(row.value)).mean()) if row.value != 0 else 0.0
        qcorr = corr[corr["feature"] == row.feature]["value"].abs().dropna()
        qcorr_min = float(qcorr.min()) if not qcorr.empty else 1.0
        if abs(float(row.value)) >= 0.02 and same_sign_share >= 0.55 and qcorr_min <= 0.70:
            stable_features.append({"feature": row.feature, "label": row.label, "rankic": float(row.value), "same_sign_share": same_sign_share, "abs_qlib_corr_min": qcorr_min})
    if stable_features:
        return {"gate": "request_phase2_rules_baseline=true", "reason": "扩展窗口下存在多个分段同向、与 qlib score 低到中等相关且泄露审计为 0 的候选特征；仅请求审查者授权 Phase2，不自动进入。", "stable_features": stable_features[:10]}
    return {"gate": "request_more_data_or_repair=true", "reason": "扩展窗口样本已构建且泄露审计通过，但当前稳定性或 qlib 低相关条件不足以直接请求 Phase2。"}


def write_reports(samples: pd.DataFrame, metrics: pd.DataFrame, segment_metrics: pd.DataFrame, monthly: pd.DataFrame, audit: dict[str, Any], conclusion: dict[str, Any], build_info: dict[str, Any], manifest: pd.DataFrame) -> None:
    LEAKAGE_REPORT_PATH.write_text("\n".join(["# Phase 1B Leakage Audit", "", f"- status: `{audit['status']}`", "- T+1 available_at is a conservative visibility proxy, not official publication proof.", "", md_table(audit["checks"], ["check", "bad_rows", "pass"]), ""]), encoding="utf-8")
    rankic = metrics[(metrics["metric_type"].str.startswith("rankic_spearman")) & (~metrics["feature"].isin(QLIB_FEATURES))]
    qcorr = metrics[metrics["metric_type"] == "feature_vs_qlib_spearman"]
    highlow = metrics[metrics["metric_type"] == "high_minus_low_mean_excess_return"]
    FACTOR_REPORT_PATH.write_text("\n".join([
        "# Phase 1B Factor Increment Report", "", f"- sample_rows: `{len(samples)}`", f"- conclusion: `{json.dumps(conclusion, ensure_ascii=False)}`", "", "## RankIC Top Absolute", "",
        md_table(rankic.sort_values("value", key=lambda s: s.abs(), ascending=False).head(20).to_dict("records"), ["feature", "label", "n", "valid_periods", "value"]), "", "## High-Low Mean Excess Return Top Absolute", "",
        md_table(highlow.sort_values("value", key=lambda s: s.abs(), ascending=False).head(20).to_dict("records"), ["feature", "label", "segment_type", "segment", "n", "value"]), "", "## Feature vs Qlib Spearman Top Absolute", "",
        md_table(qcorr.sort_values("value", key=lambda s: s.abs(), ascending=False).head(20).to_dict("records"), ["feature", "label", "n", "value"]), ""]), encoding="utf-8")
    manifest_table = manifest[["category", "symbol_count", "row_count", "first_trade_date", "last_trade_date", "archive_path"]].to_dict("records")
    report_lines = [
        "# Phase 1B 执行报告：扩展窗口正交数据只读验证", "", f"- 生成时间：`{utc_now()}`", f"- 指标模式：`{build_info.get('metrics_mode', 'fast')}`", f"- 阶段结论：`{conclusion['gate']}`", f"- 结论理由：{conclusion['reason']}",
        "- 本阶段没有联网、没有使用 token、没有重拉 Phase0E、没有写入 qlib/provider、没有训练模型、没有规则 baseline、没有进入 Phase2。", "- 注：脚本文件写入时 `apply_patch` 受当前沙箱 bwrap loopback 限制失败，改用受控本地 Python 写入；该问题只影响编辑方式，不影响只读数据边界。", "",
        "## 1. 输入与边界", "", "- 输入限定为 Phase0E normalized PIT archive、本地 qlib ranking/score artifact、本地价格与 TWII。", "- 未使用 Phase0E excluded tail rows。", "- `available_at = next_trading_day(trade_date)` 仅作为 conservative visibility proxy，不是官方发布时间证明。", "", md_table(manifest_table, ["category", "symbol_count", "row_count", "first_trade_date", "last_trade_date", "archive_path"]), "",
        "## 2. 样本构建口径", "", f"- asof 范围：`{build_info.get('sample_asof_start', '')}` 至 `{build_info.get('sample_asof_end', '')}`", f"- Phase0E archive symbol 数：`{build_info.get('symbols_in_phase0e_archive')}`", f"- 样本 symbol 数：`{build_info.get('sample_symbol_count', 0)}`", f"- 样本行数：`{build_info.get('sample_rows', 0)}`",
        f"- 因两类 PIT feature 未同时可见而排除行数：`{build_info.get('excluded_missing_pit_rows', 0)}`", f"- Top50 子集样本量：`{build_info.get('top50_sample_rows', 0)}`", f"- Top150 子集样本量：`{build_info.get('top150_sample_rows', 0)}`", f"- qlib prediction rows：`{build_info.get('qlib_prediction_rows', 0)}`；prediction file count：`{build_info.get('qlib_prediction_paths', 0)}`", f"- PIT 可见性断言：`{audit['status']}`；`available_at <= asof` 违反行见泄露审计。", "", "### 每月样本量", "", md_table(monthly.to_dict("records"), ["month", "sample_rows", "symbol_count", "top50_rows", "top150_rows", "valid_pit_rows"]), "",
        "## 3. 标签", "", "- 标签来自本地 `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/*.csv` 价格文件。", "- 已生成 `fwd_5d_excess_return`、`fwd_10d_excess_return`、`fwd_20d_excess_return`，以个股 forward return 减 TWII forward return。", "- forward label date 必须大于 asof，审计见 `phase1b_leakage_audit_report.md`。", "",
        "## 4. 特征", "", "- 法人字段：外资、投信、自营商与合计净买超；对各字段生成 5/10/20 日 rolling sum、rolling zscore 与横截面 rank pct。", "- 融资融券字段：融资余额、融资变化、融券余额、融券变化；对余额生成 rolling mean/zscore，对变化生成 rolling sum/zscore，并生成横截面 rank pct。", "- 每个样本点只取 `available_at <= asof` 的最近一笔 PIT row。", "",
        "## 5. 单因子与分段稳定性", "", "### 全样本 RankIC 摘要", "", md_table(rankic.sort_values("value", key=lambda s: s.abs(), ascending=False).head(20).to_dict("records"), ["feature", "label", "n", "valid_periods", "value"]), "", "### 年度/季度/月度分段", "", f"- 分段指标输出：`{rel(SEGMENT_METRICS_PATH)}`", "- hit-rate 只作为历史样本统计，不代表未来胜率或收益承诺。", "",
        "## 6. 与 qlib 排名关系", "", "- 已计算正交特征与 `qlib_score_raw`、`qlib_rank`、`qlib_score_percentile_by_date` 的 Spearman 相关。", "- 已对 qlib Top50/Top150 内外分别计算特征 high-low 与历史正样本比例。", "", md_table(qcorr.sort_values("value", key=lambda s: s.abs(), ascending=False).head(20).to_dict("records"), ["feature", "label", "n", "value"]), "",
        "## 7. 泄露审计", "", md_table(audit["checks"], ["check", "bad_rows", "pass"]), "",
        "## 8. 产物", "", f"- 样本：`{rel(SAMPLES_PATH)}`", f"- 样本预览：`{rel(PREVIEW_PATH)}`", f"- schema：`{rel(SCHEMA_PATH)}`", f"- 每月样本量：`{rel(MONTHLY_SAMPLE_PATH)}`", f"- 全样本指标：`{rel(METRICS_PATH)}`", f"- 分段指标：`{rel(SEGMENT_METRICS_PATH)}`", f"- 因子增量摘要：`{rel(FACTOR_REPORT_PATH)}`", f"- 泄露审计：`{rel(LEAKAGE_REPORT_PATH)}`", "",
        "## 9. Phase 1B Gate", "", f"- `{conclusion['gate']}`", "- 即使请求 Phase2 rules baseline，也必须等待审查者授权；本脚本和本报告没有自动进入 Phase2。", ""]
    EXEC_REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")


def select_metric_features(features: list[str], metrics_mode: str) -> list[str]:
    """Choose metric features without changing the full sample schema."""
    if metrics_mode == "full":
        return list(features)
    wanted = [
        "foreign_net_buy",
        "investment_trust_net_buy",
        "institutional_total_net_buy",
        "institutional_total_net_buy_20d_sum",
        "institutional_total_net_buy_20d_zscore",
        "institutional_total_net_buy_20d_sum_cs_rank_pct",
        "margin_balance_change_20d_sum",
        "short_balance_change_20d_sum",
    ]
    return [f for f in wanted if f in features]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run restricted Phase1B readonly orthogonal analysis.")
    parser.add_argument("--start", default="2022-01-01")
    parser.add_argument("--end", default="2026-05-29")
    parser.add_argument("--preview-rows", type=int, default=500)
    parser.add_argument("--metrics-mode", choices=["fast", "full"], default="fast")
    parser.add_argument("--output-prefix", default=None, help="Defaults to phase1b for fast and phase1b_full for full.")
    args = parser.parse_args()
    prefix = args.output_prefix or ("phase1b_full" if args.metrics_mode == "full" else "phase1b")
    apply_output_prefix(prefix)
    ensure_dirs()
    samples, build_info, features, manifest = build_samples(args)
    build_info["metrics_mode"] = args.metrics_mode
    build_info["output_prefix"] = prefix
    print(json.dumps({"stage": "samples_built", "rows": len(samples), "features": len(features), "metrics_mode": args.metrics_mode, "output_prefix": prefix}, ensure_ascii=False), flush=True)
    if samples.empty:
        raise RuntimeError("Phase1B sample is empty; see local qlib prediction coverage.")
    metric_features = select_metric_features(features, args.metrics_mode)
    print(json.dumps({"stage": "metrics_start", "metric_features": len(metric_features), "metrics_mode": args.metrics_mode}, ensure_ascii=False), flush=True)
    metrics, segment_metrics = build_metrics(samples, metric_features, args.metrics_mode)
    print(json.dumps({"stage": "metrics_done", "metrics": len(metrics), "segment_metrics": len(segment_metrics)}, ensure_ascii=False), flush=True)
    monthly = monthly_sample_size(samples)
    audit = leakage_audit(samples, build_info)
    result = phase1b_conclusion(samples, metrics, segment_metrics, audit)
    print(json.dumps({"stage": "write_outputs_start"}, ensure_ascii=False), flush=True)
    samples.to_parquet(SAMPLES_PATH, index=False)
    samples.head(args.preview_rows).to_csv(PREVIEW_PATH, index=False)
    metrics.to_csv(METRICS_PATH, index=False)
    segment_metrics.to_csv(SEGMENT_METRICS_PATH, index=False)
    monthly.to_csv(MONTHLY_SAMPLE_PATH, index=False)
    schema = schema_doc(samples, build_info, features)
    schema["metric_features"] = metric_features
    SCHEMA_PATH.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
    write_reports(samples, metrics, segment_metrics, monthly, audit, result, build_info, manifest)
    print(json.dumps({"build_info": build_info, "audit": audit, "conclusion": result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
