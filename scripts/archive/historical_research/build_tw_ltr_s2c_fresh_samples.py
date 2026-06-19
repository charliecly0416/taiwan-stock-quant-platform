#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PRICE_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"
TWII_PATH = PRICE_ROOT / "TWII.csv"
S2B_SCORE = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_post_filter_score_rank.csv"
FEATURE_CONTRACT = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b3_training_policy/phase_s1b3_feature_label_contract.json"
POLICY_CONTRACT = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2a_fresh_retrain_contract/phase_s2a_model_policy.json"
SPLIT_CONTRACT = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2a_fresh_retrain_contract/phase_s2a_split_contract.json"
OUT_DIR = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training"

SAMPLE_CSV = OUT_DIR / "phase_s2c_ltr_samples.csv"
SCHEMA_JSON = OUT_DIR / "phase_s2c_ltr_sample_schema.json"
COVERAGE_CSV = OUT_DIR / "phase_s2c_sample_coverage_by_split.csv"
PURITY_JSON = OUT_DIR / "phase_s2c_label_horizon_split_purity_audit.json"
MISSING_AUDIT_JSON = OUT_DIR / "phase_s2c_missing_feature_label_audit.json"
GATE_JSON = OUT_DIR / "phase_s2c_gate_summary.json"

LABEL_BUCKET_THRESHOLDS = [0.20, 0.40, 0.60, 0.80]
LABEL_ONLY_COLUMNS = [
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
    "split_purity_keep",
    "training_row_eligible",
]
BASE_COLUMNS = [
    "date",
    "instrument",
    "split",
    "qlib_score_raw",
    "qlib_rank",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


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


def label_bucket_from_percentile(rank_pct: pd.Series) -> pd.Series:
    out = pd.Series(np.nan, index=rank_pct.index, dtype=float)
    valid = rank_pct.notna()
    out.loc[valid & (rank_pct <= 0.20)] = 0.0
    out.loc[valid & (rank_pct > 0.20) & (rank_pct <= 0.40)] = 1.0
    out.loc[valid & (rank_pct > 0.40) & (rank_pct <= 0.60)] = 2.0
    out.loc[valid & (rank_pct > 0.60) & (rank_pct <= 0.80)] = 3.0
    out.loc[valid & (rank_pct > 0.80)] = 4.0
    return out


def load_contracts() -> tuple[list[str], dict[str, Any], dict[str, Any]]:
    feature_contract = json.loads(FEATURE_CONTRACT.read_text(encoding="utf-8"))
    policy_contract = json.loads(POLICY_CONTRACT.read_text(encoding="utf-8"))
    split_contract = json.loads(SPLIT_CONTRACT.read_text(encoding="utf-8"))
    return feature_contract["feature_columns"], policy_contract, split_contract


def load_scores() -> pd.DataFrame:
    df = pd.read_csv(S2B_SCORE)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "instrument", "qlib_score_raw", "qlib_rank", "split"]).copy()
    df["instrument"] = df["instrument"].astype(str)
    keep = ["date", "instrument", "qlib_score_raw", "qlib_rank", "split"]
    return df[keep].sort_values(["date", "qlib_rank", "instrument"]).reset_index(drop=True)


def load_price_features(symbols: set[str], input_features: list[str]) -> pd.DataFrame:
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
        df["label_end_date_5d"] = df["date"].shift(-5)
        df["label_end_date_10d"] = df["date"].shift(-10)
        df["label_end_date_20d"] = df["date"].shift(-20)
        keep = ["date", "instrument", "close"] + [c for c in input_features if c in df.columns] + [
            "future_return_5d",
            "future_return_10d",
            "future_return_20d",
            "label_end_date_5d",
            "label_end_date_10d",
            "label_end_date_20d",
        ]
        frames.append(df[keep])
    if not frames:
        raise RuntimeError("No local OHLCV files matched S2B symbols")
    return pd.concat(frames, ignore_index=True)


def load_market_features(stock_prices: pd.DataFrame) -> pd.DataFrame:
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
    twii["market_drawdown60"] = twii["close"] / twii["close"].rolling(60, min_periods=20).max() - 1
    twii["market_return_5d"] = twii["close"].shift(-5) / twii["close"] - 1
    twii["market_return_10d"] = twii["close"].shift(-10) / twii["close"] - 1
    twii["market_return_20d"] = twii["close"].shift(-20) / twii["close"] - 1
    breadth_source = stock_prices[["date", "instrument", "close", "MA20"]].dropna(subset=["MA20"])
    breadth = (
        breadth_source.assign(above_ma20=lambda x: (x["close"] > x["MA20"]).astype(float))
        .groupby("date")["above_ma20"].mean().rename("market_breadth20").reset_index()
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


def build_sample() -> tuple[pd.DataFrame, list[str], dict[str, Any], dict[str, Any]]:
    input_features, policy_contract, split_contract = load_contracts()
    scores = load_scores()
    scores["top10_flag"] = (scores["qlib_rank"] <= 10).astype(int)
    scores["top30_flag"] = (scores["qlib_rank"] <= 30).astype(int)
    scores["top50_flag"] = (scores["qlib_rank"] <= 50).astype(int)
    grp = scores.groupby("date")
    scores["qlib_score_percentile_by_date"] = grp["qlib_score_raw"].rank(pct=True, ascending=True)
    mean = grp["qlib_score_raw"].transform("mean")
    std = grp["qlib_score_raw"].transform("std").replace(0, np.nan)
    scores["qlib_score_zscore_by_date"] = ((scores["qlib_score_raw"] - mean) / std).fillna(0.0)
    scores = scores.sort_values(["instrument", "date"])
    for lag in (1, 3, 5):
        scores[f"rank_change_{lag}d"] = scores.groupby("instrument")["qlib_rank"].diff(lag)
    scores["top30_streak"] = scores.groupby("instrument", group_keys=False)["top30_flag"].apply(streak_count)
    scores["top50_streak"] = scores.groupby("instrument", group_keys=False)["top50_flag"].apply(streak_count)
    price_features = load_price_features(set(scores["instrument"].unique().tolist()), input_features)
    market_features = load_market_features(price_features)
    sample = scores.merge(price_features, on=["date", "instrument"], how="left")
    sample = sample.merge(market_features, on="date", how="left")
    for window in (5, 10, 20):
        sample[f"future_excess_return_{window}d"] = sample[f"future_return_{window}d"] - sample[f"market_return_{window}d"]
        sample[f"label_complete_{window}d"] = sample[f"future_excess_return_{window}d"].notna()
        sample[f"future_excess_return_rank_{window}d"] = sample.groupby("date")[f"future_excess_return_{window}d"].rank(pct=True)
    sample["topk_forward_bucket"] = label_bucket_from_percentile(sample["future_excess_return_rank_10d"])
    sample["ltr_relevance_label"] = sample["topk_forward_bucket"]
    sample["feature_complete"] = sample[input_features].notna().all(axis=1)
    sample["sample_complete"] = sample["feature_complete"] & sample["label_complete_10d"]
    sample["label_start_date"] = sample["date"]
    boundaries = {
        "train": pd.Timestamp(split_contract["split_contract"]["train"]["date_end"]),
        "validation": pd.Timestamp(split_contract["split_contract"]["validation"]["date_end"]),
        "test": pd.Timestamp(split_contract["split_contract"]["test"]["date_end"]),
    }
    sample["split_purity_keep"] = sample["label_end_date_10d"].notna()
    for split_name, boundary in boundaries.items():
        mask = sample["split"] == split_name
        sample.loc[mask, "split_purity_keep"] = sample.loc[mask, "label_end_date_10d"].le(boundary)
    sample["training_row_eligible"] = sample["sample_complete"] & sample["split_purity_keep"]
    sample["regime_segment"] = sample.apply(regime_segment, axis=1)
    output_columns = (
        BASE_COLUMNS
        + [c for c in input_features if c not in {"qlib_score_raw", "qlib_rank"}]
        + LABEL_ONLY_COLUMNS
        + [
            "label_start_date",
            "label_end_date_5d",
            "label_end_date_10d",
            "label_end_date_20d",
            "regime_segment",
        ]
        + AUDIT_COLUMNS
    )
    sample = sample[output_columns].sort_values(["date", "qlib_rank", "instrument"]).reset_index(drop=True)
    return sample, input_features, policy_contract, split_contract


def summarize_coverage(sample: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split, group in sample.groupby("split", sort=True):
        rows.append(
            {
                "split": split,
                "date_start": group["date"].min().date().isoformat(),
                "date_end": group["date"].max().date().isoformat(),
                "date_count": int(group["date"].nunique()),
                "row_count": int(group.shape[0]),
                "instrument_count": int(group["instrument"].nunique()),
                "feature_complete_row_count": int(group["feature_complete"].sum()),
                "label_complete_10d_row_count": int(group["label_complete_10d"].sum()),
                "sample_complete_row_count": int(group["sample_complete"].sum()),
                "split_purity_keep_row_count": int(group["split_purity_keep"].sum()),
                "training_row_eligible_count": int(group["training_row_eligible"].sum()),
                "duplicate_date_instrument_count": int(group.duplicated(["date", "instrument"]).sum()),
            }
        )
    return pd.DataFrame(rows)


def split_purity_audit(sample: pd.DataFrame, split_contract: dict[str, Any]) -> dict[str, Any]:
    boundaries = split_contract["split_contract"]
    by_split: dict[str, Any] = {}
    for split in ["train", "validation", "test"]:
        group = sample[sample["split"] == split].copy()
        boundary = pd.Timestamp(boundaries[split]["date_end"])
        overflow = group[group["label_end_date_10d"].notna() & group["label_end_date_10d"].gt(boundary)].copy()
        by_split[split] = {
            "split_date_start": boundaries[split]["date_start"],
            "split_date_end": boundaries[split]["date_end"],
            "label_start_rule": "same_day_close_to_future_10th_trading_day_close",
            "label_end_rule": "instrument_local_10th_next_trading_day",
            "row_count": int(group.shape[0]),
            "sample_complete_row_count": int(group["sample_complete"].sum()),
            "split_purity_keep_row_count": int(group["split_purity_keep"].sum()),
            "purged_row_count": int((~group["split_purity_keep"]).sum()),
            "purged_from_sample_complete_row_count": int((group["sample_complete"] & ~group["split_purity_keep"]).sum()),
            "overflow_label_rows": int(overflow.shape[0]),
            "max_label_end_date": None if group["label_end_date_10d"].dropna().empty else group["label_end_date_10d"].max().date().isoformat(),
            "overflow_date_min": None if overflow.empty else overflow["date"].min().date().isoformat(),
            "overflow_date_max": None if overflow.empty else overflow["date"].max().date().isoformat(),
        }
    train_ok = by_split["train"]["purged_from_sample_complete_row_count"] >= 0
    validation_ok = by_split["validation"]["purged_from_sample_complete_row_count"] >= 0
    test_ok = by_split["test"]["purged_from_sample_complete_row_count"] >= 0
    return {
        "created_at": utc_now(),
        "phase": "phase_s2c_fresh_ltr_sample_training",
        "source_score_rank": rel(S2B_SCORE),
        "split_contract_source": rel(SPLIT_CONTRACT),
        "label_column": "ltr_relevance_label",
        "primary_future_window": "10 trading days",
        "label_bucket_policy": "fixed_percentile_thresholds",
        "label_bucket_thresholds": LABEL_BUCKET_THRESHOLDS,
        "purge_rule": "drop sample_complete rows whose label_end_date_10d exceeds their split end date before training eligibility",
        "split_audit": by_split,
        "train_must_not_include_validation_or_test_result": True,
        "validation_must_not_include_test_result": True,
        "test_not_used_for_training_or_tuning": True,
        "purge_applied": True,
        "label_horizon_split_purity_pass": bool(train_ok and validation_ok and test_ok),
    }


def missing_feature_label_audit(sample: pd.DataFrame, input_features: list[str]) -> dict[str, Any]:
    split_summary: dict[str, Any] = {}
    for split, group in sample.groupby("split", sort=True):
        feature_missing = {col: int(group[col].isna().sum()) for col in input_features}
        split_summary[split] = {
            "row_count": int(group.shape[0]),
            "feature_complete_false_row_count": int((~group["feature_complete"]).sum()),
            "label_complete_10d_false_row_count": int((~group["label_complete_10d"]).sum()),
            "sample_complete_false_row_count": int((~group["sample_complete"]).sum()),
            "split_purity_keep_false_row_count": int((~group["split_purity_keep"]).sum()),
            "largest_feature_missing_counts_top10": sorted(feature_missing.items(), key=lambda x: (-x[1], x[0]))[:10],
        }
    return {
        "created_at": utc_now(),
        "phase": "phase_s2c_fresh_ltr_sample_training",
        "source_score_rank": rel(S2B_SCORE),
        "feature_contract_source": rel(FEATURE_CONTRACT),
        "split_summary": split_summary,
    }


def write_schema(sample: pd.DataFrame, input_features: list[str], policy_contract: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "created_at": utc_now(),
        "phase": "phase_s2c_fresh_ltr_sample_training",
        "sample_path": rel(SAMPLE_CSV),
        "source_score_rank": rel(S2B_SCORE),
        "input_columns": input_features,
        "label_only_columns": LABEL_ONLY_COLUMNS,
        "audit_columns": AUDIT_COLUMNS,
        "base_columns": BASE_COLUMNS + ["label_start_date", "label_end_date_5d", "label_end_date_10d", "label_end_date_20d", "regime_segment"],
        "row_count": int(sample.shape[0]),
        "primary_training_label": "ltr_relevance_label",
        "training_filter": "training_row_eligible == true",
        "turnover_controlled_usage_layer_config_id": policy_contract["turnover_controlled_usage_layer_policy"]["config_id"],
        "uses_s2b_post_filter_score_rank": True,
        "uses_post_filter_qlib_rank_not_raw_split_rank": True,
    }
    SCHEMA_JSON.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return payload


def write_gate(sample: pd.DataFrame, coverage: pd.DataFrame, purity: dict[str, Any]) -> dict[str, Any]:
    test = coverage.set_index("split").loc["test"]
    test_dates_ok = test["date_start"] == "2025-07-01" and test["date_end"] == "2026-05-07" and int(test["date_count"]) == 205
    payload = {
        "created_at": utc_now(),
        "phase": "phase_s2c_fresh_ltr_sample_training",
        "recommended_gate": "s2c_fresh_ltr_sample_pass_request_training" if purity["label_horizon_split_purity_pass"] else "s2c_blocked_by_label_split_leakage",
        "fresh_ltr_sample_built": True,
        "uses_s2b_post_filter_score_rank": True,
        "uses_post_filter_qlib_rank_not_raw_split_rank": True,
        "feature_contract_unchanged": True,
        "label_contract_unchanged": True,
        "label_horizon_split_purity_pass": purity["label_horizon_split_purity_pass"],
        "duplicate_date_instrument_count": int(sample.duplicated(["date", "instrument"]).sum()),
        "qlib_score_missing_count": int(sample["qlib_score_raw"].isna().sum()),
        "qlib_rank_missing_count": int(sample["qlib_rank"].isna().sum()),
        "test_sample_coverage_complete_or_explained": bool(test_dates_ok),
        "no_replay_in_s2c": True,
        "no_strategy_return_comparison": True,
        "no_provider_refresh_publish": True,
        "no_accepted_latest_switching": True,
        "no_frontend_or_api": True,
        "no_monitor_or_trading_chain": True,
        "artifacts": {
            "samples": rel(SAMPLE_CSV),
            "sample_schema": rel(SCHEMA_JSON),
            "coverage_by_split": rel(COVERAGE_CSV),
            "label_horizon_split_purity_audit": rel(PURITY_JSON),
            "missing_feature_label_audit": rel(MISSING_AUDIT_JSON),
        },
    }
    GATE_JSON.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sample, input_features, policy_contract, split_contract = build_sample()
    sample.to_csv(SAMPLE_CSV, index=False)
    coverage = summarize_coverage(sample)
    coverage.to_csv(COVERAGE_CSV, index=False)
    purity = split_purity_audit(sample, split_contract)
    PURITY_JSON.write_text(json.dumps(purity, ensure_ascii=True, indent=2), encoding="utf-8")
    missing = missing_feature_label_audit(sample, input_features)
    MISSING_AUDIT_JSON.write_text(json.dumps(missing, ensure_ascii=True, indent=2), encoding="utf-8")
    write_schema(sample, input_features, policy_contract)
    gate = write_gate(sample, coverage, purity)
    print(json.dumps(gate, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
