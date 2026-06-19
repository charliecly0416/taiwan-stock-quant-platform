#!/usr/bin/env python3
"""Build Phase 1 LTR baseline samples for the TW LTR mainline.

Scope is intentionally narrow: local qlib predictions, local OHLCV, local TWII,
and Phase 0 whitelist only. No network, provider refresh, accepted-latest
switching, replay, frontend/API, monitor, or trading paths.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
QLIB_EXP = ROOT / "qlib_pipeline/data_tw/experiments"
SIGNAL_ROOTS = [
    QLIB_EXP / "option_c_historical_signal_backfill",
    QLIB_EXP / "option_c_daily_signal",
]
PRICE_ROOT = QLIB_EXP / "yahoo_adjusted_primary/normalized_nonempty"
TWII_PATH = PRICE_ROOT / "TWII.csv"
OUT_DIR = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline"

SAMPLE_CSV = OUT_DIR / "phase1_ltr_samples.csv"
SCHEMA_JSON = OUT_DIR / "phase1_sample_schema.json"
COVERAGE_JSON = OUT_DIR / "phase1_sample_coverage.json"
FEATURE_LIST_JSON = OUT_DIR / "phase1_input_feature_list.json"
LABEL_AUDIT_JSON = OUT_DIR / "phase1_label_audit_summary.json"
SPLIT_SUMMARY_JSON = OUT_DIR / "phase1_split_summary.json"
GATE_SUMMARY_JSON = OUT_DIR / "phase1_sample_build_gate_summary.json"

INPUT_FEATURES = [
    "qlib_score_raw",
    "qlib_rank",
    "qlib_score_percentile_by_date",
    "qlib_score_zscore_by_date",
    "rank_change_1d",
    "rank_change_3d",
    "rank_change_5d",
    "top10_flag",
    "top30_flag",
    "top50_flag",
    "top30_streak",
    "top50_streak",
    "MA5",
    "MA10",
    "MA20",
    "MA60",
    "RSI14",
    "MACD",
    "Bollinger_position",
    "ret20",
    "volatility20",
    "volume_ratio20",
    "avg_trading_value_20d",
    "volume_stability20",
    "missing_rate20",
    "suspension_proxy",
    "slippage_proxy",
    "TWII_ret20",
    "TWII_ret60",
    "TWII_close_vs_MA60",
    "TWII_close_vs_MA120",
    "market_volatility20",
    "market_drawdown60",
    "market_breadth20",
]

EXCLUDED_WHITE_LIST_FEATURES = {
    "trend_score": "default_excluded_by_phase1_review_until_stable_existing_definition_is_proven",
}

FORBIDDEN_FEATURES = {
    "institutional_net_buy",
    "margin_balance",
    "short_balance",
    "monthly_revenue_yoy_mom",
    "valuation_PER_PBR",
}

LABEL_COLUMNS = [
    "future_return_5d",
    "future_return_10d",
    "future_return_20d",
    "future_excess_return_5d",
    "future_excess_return_10d",
    "future_excess_return_20d",
    "future_excess_return_rank_5d",
    "future_excess_return_rank_10d",
    "future_excess_return_rank_20d",
    "topk_forward_bucket",
    "ltr_relevance_label",
]

AUDIT_COLUMNS = [
    "label_complete_5d",
    "label_complete_10d",
    "label_complete_20d",
    "feature_complete",
    "sample_complete",
]

GROUPING_COLUMNS = [
    "date",
    "instrument",
    "year",
    "split",
    "regime_segment",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def prediction_paths() -> list[Path]:
    paths: list[Path] = []
    for root in SIGNAL_ROOTS:
        if not root.exists():
            continue
        paths.extend(root.glob("*/*/prediction.csv"))
        paths.extend(root.glob("*/prediction.csv"))
    return sorted(set(paths))


def load_predictions() -> pd.DataFrame:
    frames = []
    for order, path in enumerate(prediction_paths()):
        try:
            df = pd.read_csv(path, usecols=["datetime", "instrument", "score"])
        except Exception:
            continue
        if df.empty:
            continue
        df["date"] = pd.to_datetime(df["datetime"], errors="coerce")
        df["instrument"] = df["instrument"].astype(str)
        df["qlib_score_raw"] = pd.to_numeric(df["score"], errors="coerce")
        df["source_order"] = order
        frames.append(df[["date", "instrument", "qlib_score_raw", "source_order"]])
    if not frames:
        raise RuntimeError("No local qlib prediction.csv files found.")
    pred = pd.concat(frames, ignore_index=True).dropna(subset=["date", "instrument", "qlib_score_raw"])
    pred = pred.sort_values(["date", "instrument", "source_order"])
    pred = pred.drop_duplicates(["date", "instrument"], keep="last")
    pred = pred.sort_values(["date", "qlib_score_raw"], ascending=[True, False])
    group = pred.groupby("date", sort=False)
    pred["qlib_rank"] = group["qlib_score_raw"].rank(method="first", ascending=False)
    pred["qlib_score_percentile_by_date"] = group["qlib_score_raw"].rank(pct=True, ascending=True)
    mean = group["qlib_score_raw"].transform("mean")
    std = group["qlib_score_raw"].transform("std").replace(0, np.nan)
    pred["qlib_score_zscore_by_date"] = ((pred["qlib_score_raw"] - mean) / std).fillna(0.0)
    pred["top10_flag"] = (pred["qlib_rank"] <= 10).astype(int)
    pred["top30_flag"] = (pred["qlib_rank"] <= 30).astype(int)
    pred["top50_flag"] = (pred["qlib_rank"] <= 50).astype(int)
    pred = pred.sort_values(["instrument", "date"])
    for lag in (1, 3, 5):
        pred[f"rank_change_{lag}d"] = pred.groupby("instrument")["qlib_rank"].diff(lag)
    pred["top30_streak"] = pred.groupby("instrument", group_keys=False)["top30_flag"].apply(streak_count)
    pred["top50_streak"] = pred.groupby("instrument", group_keys=False)["top50_flag"].apply(streak_count)
    return pred


def streak_count(flags: pd.Series) -> pd.Series:
    values = []
    current = 0
    for raw in flags.fillna(0).astype(int).tolist():
        current = current + 1 if raw else 0
        values.append(current)
    return pd.Series(values, index=flags.index)


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window, min_periods=window).mean()
    loss = (-delta.clip(upper=0)).rolling(window, min_periods=window).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).fillna(50.0)


def load_price_features(symbols: set[str]) -> pd.DataFrame:
    frames = []
    for symbol in sorted(symbols):
        path = PRICE_ROOT / f"{symbol}.csv"
        if not path.exists():
            continue
        try:
            df = pd.read_csv(path)
        except Exception:
            continue
        if df.empty or "date" not in df or "close" not in df:
            continue
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"]).sort_values("date")
        df["instrument"] = symbol
        for col in ["close", "volume", "vwap"]:
            if col in df:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        close = df["close"]
        volume = df["volume"] if "volume" in df else pd.Series(np.nan, index=df.index)
        vwap = df["vwap"] if "vwap" in df else close
        for window in (5, 10, 20, 60):
            df[f"MA{window}"] = close.rolling(window, min_periods=window).mean()
        df["RSI14"] = rsi(close)
        ema12 = close.ewm(span=12, adjust=False, min_periods=12).mean()
        ema26 = close.ewm(span=26, adjust=False, min_periods=26).mean()
        df["MACD"] = ema12 - ema26
        ma20 = close.rolling(20, min_periods=20).mean()
        std20 = close.rolling(20, min_periods=20).std()
        df["Bollinger_position"] = ((close - ma20) / (2 * std20.replace(0, np.nan))).clip(-5, 5)
        df["ret20"] = close.pct_change(20)
        df["volatility20"] = close.pct_change().rolling(20, min_periods=20).std()
        df["volume_ratio20"] = volume / volume.rolling(20, min_periods=20).mean().replace(0, np.nan)
        trading_value = volume * vwap
        df["avg_trading_value_20d"] = trading_value.rolling(20, min_periods=20).mean()
        df["volume_stability20"] = 1.0 / (1.0 + volume.pct_change().rolling(20, min_periods=20).std())
        df["missing_rate20"] = close.isna().astype(int).rolling(20, min_periods=1).mean()
        df["suspension_proxy"] = (volume.fillna(0) <= 0).astype(int)
        df["slippage_proxy"] = (1.0 / np.sqrt(trading_value.replace(0, np.nan))).replace([np.inf, -np.inf], np.nan)
        df["future_return_5d"] = close.shift(-5) / close - 1
        df["future_return_10d"] = close.shift(-10) / close - 1
        df["future_return_20d"] = close.shift(-20) / close - 1
        frames.append(df[["date", "instrument", "close"] + [col for col in INPUT_FEATURES if col in df] + [
            "future_return_5d",
            "future_return_10d",
            "future_return_20d",
        ]])
    if not frames:
        raise RuntimeError("No local OHLCV files matched prediction symbols.")
    return pd.concat(frames, ignore_index=True)


def load_market_features(stock_prices: pd.DataFrame) -> pd.DataFrame:
    if not TWII_PATH.exists():
        raise RuntimeError(f"Missing TWII local file: {rel(TWII_PATH)}")
    twii = pd.read_csv(TWII_PATH)
    twii["date"] = pd.to_datetime(twii["date"], errors="coerce")
    twii = twii.dropna(subset=["date"]).sort_values("date")
    twii["close"] = pd.to_numeric(twii["close"], errors="coerce")
    twii["TWII_ret20"] = twii["close"].pct_change(20)
    twii["TWII_ret60"] = twii["close"].pct_change(60)
    ma60 = twii["close"].rolling(60, min_periods=60).mean()
    ma120 = twii["close"].rolling(120, min_periods=120).mean()
    twii["TWII_close_vs_MA60"] = twii["close"] / ma60 - 1
    twii["TWII_close_vs_MA120"] = twii["close"] / ma120 - 1
    twii["market_volatility20"] = twii["close"].pct_change().rolling(20, min_periods=20).std()
    rolling_max60 = twii["close"].rolling(60, min_periods=20).max()
    twii["market_drawdown60"] = twii["close"] / rolling_max60 - 1
    twii["market_return_5d"] = twii["close"].shift(-5) / twii["close"] - 1
    twii["market_return_10d"] = twii["close"].shift(-10) / twii["close"] - 1
    twii["market_return_20d"] = twii["close"].shift(-20) / twii["close"] - 1

    breadth_source = stock_prices[["date", "instrument", "close", "MA20"]].dropna(subset=["MA20"])
    breadth = (
        breadth_source.assign(above_ma20=lambda x: (x["close"] > x["MA20"]).astype(float))
        .groupby("date")["above_ma20"]
        .mean()
        .rename("market_breadth20")
        .reset_index()
    )
    keep = [
        "date",
        "TWII_ret20",
        "TWII_ret60",
        "TWII_close_vs_MA60",
        "TWII_close_vs_MA120",
        "market_volatility20",
        "market_drawdown60",
        "market_return_5d",
        "market_return_10d",
        "market_return_20d",
    ]
    return twii[keep].merge(breadth, on="date", how="left")


def assign_splits(dates: list[pd.Timestamp]) -> dict[pd.Timestamp, str]:
    unique_dates = sorted(dates)
    if len(unique_dates) < 60:
        raise RuntimeError(f"Insufficient complete dates for train/validation/test split: {len(unique_dates)}")
    train_end = math.floor(len(unique_dates) * 0.60)
    valid_end = math.floor(len(unique_dates) * 0.80)
    mapping = {}
    for idx, day in enumerate(unique_dates):
        if idx < train_end:
            mapping[day] = "train"
        elif idx < valid_end:
            mapping[day] = "validation"
        else:
            mapping[day] = "independent_test"
    return mapping


def regime_segment(row: pd.Series) -> str:
    drawdown = row.get("market_drawdown60")
    volatility = row.get("market_volatility20")
    breadth = row.get("market_breadth20")
    ret60 = row.get("TWII_ret60")
    if pd.isna(drawdown) or pd.isna(volatility) or pd.isna(breadth):
        return "unknown"
    if drawdown <= -0.12 or (ret60 <= -0.08 if not pd.isna(ret60) else False) or breadth < 0.35:
        return "risk_off"
    if drawdown <= -0.06 or volatility >= 0.018 or breadth < 0.45:
        return "caution"
    return "normal"


def build_sample() -> pd.DataFrame:
    predictions = load_predictions()
    symbols = set(predictions["instrument"].unique().tolist())
    price_features = load_price_features(symbols)
    market_features = load_market_features(price_features)
    sample = predictions.merge(price_features, on=["date", "instrument"], how="left")
    sample = sample.merge(market_features, on="date", how="left")
    for window in (5, 10, 20):
        sample[f"future_excess_return_{window}d"] = sample[f"future_return_{window}d"] - sample[f"market_return_{window}d"]
        sample[f"label_complete_{window}d"] = sample[f"future_excess_return_{window}d"].notna()
        sample[f"future_excess_return_rank_{window}d"] = sample.groupby("date")[f"future_excess_return_{window}d"].rank(pct=True)
    sample["topk_forward_bucket"] = (
        pd.qcut(sample["future_excess_return_rank_10d"], 5, labels=False, duplicates="drop")
        .astype("float")
    )
    sample["ltr_relevance_label"] = sample["topk_forward_bucket"]
    sample["feature_complete"] = sample[INPUT_FEATURES].notna().all(axis=1)
    sample["sample_complete"] = sample["feature_complete"] & sample["label_complete_10d"]
    sample["year"] = sample["date"].dt.year
    sample["regime_segment"] = sample.apply(regime_segment, axis=1)
    complete_dates = sample.loc[sample["sample_complete"], "date"].drop_duplicates().sort_values().tolist()
    split_map = assign_splits(complete_dates)
    sample["split"] = sample["date"].map(split_map).fillna("out_of_split_or_incomplete")
    output_columns = GROUPING_COLUMNS + INPUT_FEATURES + LABEL_COLUMNS + AUDIT_COLUMNS
    return sample[output_columns].sort_values(["date", "qlib_rank", "instrument"])


def validate_sample(sample: pd.DataFrame) -> dict[str, Any]:
    input_set = set(INPUT_FEATURES)
    forbidden_hits = sorted(input_set & FORBIDDEN_FEATURES)
    label_input_overlap = sorted(input_set & set(LABEL_COLUMNS))
    audit_input_overlap = sorted(input_set & set(AUDIT_COLUMNS))
    grouping_input_overlap = sorted(input_set & set(GROUPING_COLUMNS))
    split_counts = sample.loc[sample["sample_complete"], "split"].value_counts().to_dict()
    group_sizes = sample.loc[sample["sample_complete"]].groupby("date")["instrument"].nunique()
    return {
        "input_feature_count": len(INPUT_FEATURES),
        "excluded_whitelist_features": EXCLUDED_WHITE_LIST_FEATURES,
        "forbidden_hits": forbidden_hits,
        "label_input_overlap": label_input_overlap,
        "audit_input_overlap": audit_input_overlap,
        "grouping_input_overlap": grouping_input_overlap,
        "complete_rows": int(sample["sample_complete"].sum()),
        "total_rows": int(sample.shape[0]),
        "complete_dates": int(sample.loc[sample["sample_complete"], "date"].nunique()),
        "split_counts": {str(key): int(value) for key, value in split_counts.items()},
        "group_size_min": int(group_sizes.min()) if not group_sizes.empty else 0,
        "group_size_median": float(group_sizes.median()) if not group_sizes.empty else 0,
        "group_size_max": int(group_sizes.max()) if not group_sizes.empty else 0,
        "passed": not forbidden_hits
        and not label_input_overlap
        and not audit_input_overlap
        and not grouping_input_overlap
        and all(split in split_counts for split in ["train", "validation", "independent_test"])
        and int(sample["sample_complete"].sum()) > 0,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    now = utc_now()
    sample = build_sample()
    sample.to_csv(SAMPLE_CSV, index=False)
    validation = validate_sample(sample)

    schema = {
        "created_at": now,
        "input_columns": INPUT_FEATURES,
        "label_columns": LABEL_COLUMNS,
        "audit_columns": AUDIT_COLUMNS,
        "grouping_columns": GROUPING_COLUMNS,
        "forbidden_columns": sorted(FORBIDDEN_FEATURES),
        "excluded_whitelist_features": EXCLUDED_WHITE_LIST_FEATURES,
        "primary_training_label": "ltr_relevance_label",
        "primary_future_window": "10 trading days",
    }
    coverage = {
        "created_at": now,
        "sample_path": rel(SAMPLE_CSV),
        "total_rows": int(sample.shape[0]),
        "complete_rows": int(sample["sample_complete"].sum()),
        "date_min": str(sample["date"].min().date()),
        "date_max": str(sample["date"].max().date()),
        "complete_date_min": str(sample.loc[sample["sample_complete"], "date"].min().date()),
        "complete_date_max": str(sample.loc[sample["sample_complete"], "date"].max().date()),
        "unique_instruments": int(sample["instrument"].nunique()),
        "feature_missing_rate": {
            feature: float(sample[feature].isna().mean()) for feature in INPUT_FEATURES
        },
    }
    feature_list = {
        "created_at": now,
        "input_features": INPUT_FEATURES,
        "derivation_rules": {feature: derivation_rule(feature) for feature in INPUT_FEATURES},
    }
    label_audit = {
        "created_at": now,
        "label_windows": {
            "future_excess_return_rank_5d": "future 5 trading day stock return minus TWII return, ranked within same date",
            "future_excess_return_rank_10d": "future 10 trading day stock return minus TWII return, ranked within same date",
            "future_excess_return_rank_20d": "future 20 trading day stock return minus TWII return, ranked within same date",
            "topk_forward_bucket": "5-bucket relevance label from 10d future excess return rank",
            "ltr_relevance_label": "same as topk_forward_bucket; integer relevance for LambdaMART",
        },
        "future_leakage_check": "future columns are label/audit only and excluded from input_features",
        "label_complete_counts": {
            column: int(sample[column].sum()) for column in ["label_complete_5d", "label_complete_10d", "label_complete_20d"]
        },
    }
    split_summary = {
        "created_at": now,
        "split_rule": "time ordered 60% train, 20% validation, 20% independent_test over complete label dates",
        "split_counts": validation["split_counts"],
        "regime_segment_counts": sample.loc[sample["sample_complete"], "regime_segment"].value_counts().to_dict(),
    }
    gate = {
        "created_at": now,
        "phase": "phase1_sample_build",
        "sample_build_passed": validation["passed"],
        "no_network": True,
        "no_provider_refresh_or_publish": True,
        "no_accepted_latest_switching": True,
        "no_frontend_or_api": True,
        "no_monitor_or_trading": True,
        "validation": validation,
    }

    write_json(SCHEMA_JSON, schema)
    write_json(COVERAGE_JSON, coverage)
    write_json(FEATURE_LIST_JSON, feature_list)
    write_json(LABEL_AUDIT_JSON, label_audit)
    write_json(SPLIT_SUMMARY_JSON, split_summary)
    write_json(GATE_SUMMARY_JSON, gate)

    if not validation["passed"]:
        raise SystemExit(json.dumps({"ok": False, "validation": validation}, ensure_ascii=False, indent=2))
    print(json.dumps({"ok": True, "sample_path": rel(SAMPLE_CSV), "validation": validation}, ensure_ascii=False, indent=2))


def derivation_rule(feature: str) -> str:
    if feature.startswith("qlib_") or feature.startswith("rank_change") or feature.startswith("top"):
        return "derived from same-date qlib prediction score/rank and prior-date rank membership only"
    if feature in {"MA5", "MA10", "MA20", "MA60", "RSI14", "MACD", "Bollinger_position", "ret20", "volatility20", "volume_ratio20"}:
        return "derived from same-date and historical local OHLCV rolling windows"
    if feature in {"avg_trading_value_20d", "volume_stability20", "missing_rate20", "suspension_proxy", "slippage_proxy"}:
        return "derived from same-date and historical local volume/value liquidity proxies"
    return "derived from same-date and historical local TWII/cross-sectional market data"


if __name__ == "__main__":
    main()
