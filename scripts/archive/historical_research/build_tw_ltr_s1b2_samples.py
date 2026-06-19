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
S1B1_SCORE = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/phase_s1b1_qlib_wf_scores.csv"
FEATURE_SOURCE = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_input_feature_list.json"
OUT_DIR = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples"

SAMPLE_CSV = OUT_DIR / "phase_s1b2_ltr_samples.csv"
SCHEMA_JSON = OUT_DIR / "phase_s1b2_sample_schema.json"
FEATURE_LIST_JSON = OUT_DIR / "phase_s1b2_feature_list.json"
SPLIT_SUMMARY_JSON = OUT_DIR / "phase_s1b2_split_summary.json"
LABEL_AUDIT_JSON = OUT_DIR / "phase_s1b2_label_audit_summary.json"
FEATURE_COVERAGE_CSV = OUT_DIR / "phase_s1b2_feature_coverage.csv"
FORBIDDEN_AUDIT_CSV = OUT_DIR / "phase_s1b2_forbidden_feature_audit.csv"
LEAKAGE_JSON = OUT_DIR / "phase_s1b2_leakage_boundary_audit.json"
GATE_JSON = OUT_DIR / "phase_s1b2_gate_summary.json"
LABEL_BUCKET_THRESHOLDS = [0.20, 0.40, 0.60, 0.80]

EXCLUDED_WHITE_LIST_FEATURES = {
    "trend_score": "default_excluded_by_phase1_review_until_stable_existing_definition_is_proven",
}
FORBIDDEN_FEATURES = {
    "institutional_net_buy",
    "margin_balance",
    "short_balance",
    "monthly_revenue_yoy_mom",
    "valuation_PER_PBR",
    "trend_score",
}
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
]
BASE_COLUMNS = [
    "date",
    "instrument",
    "split",
    "fold_id",
    "qlib_score_raw",
    "qlib_rank",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_input_features() -> list[str]:
    payload = json.loads(FEATURE_SOURCE.read_text(encoding="utf-8"))
    feats = payload["input_features"]
    if "trend_score" in feats:
        raise RuntimeError("trend_score must not be present in S1B2 input feature list")
    return feats


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


def split_for_date(date_s: pd.Series) -> pd.Series:
    out = pd.Series("out_of_scope", index=date_s.index, dtype=object)
    out = out.mask((date_s >= pd.Timestamp("2017-01-01")) & (date_s <= pd.Timestamp("2020-12-31")), "train_scored")
    out = out.mask((date_s >= pd.Timestamp("2021-01-01")) & (date_s <= pd.Timestamp("2022-12-31")), "validation")
    out = out.mask((date_s >= pd.Timestamp("2023-01-01")) & (date_s <= pd.Timestamp("2025-06-30")), "test")
    return out


def load_scores() -> pd.DataFrame:
    df = pd.read_csv(S1B1_SCORE)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "instrument", "qlib_score_raw", "qlib_rank", "fold_id"]).copy()
    df["instrument"] = df["instrument"].astype(str)
    df["split"] = split_for_date(df["date"])
    expected = {"train_scored", "validation", "test"}
    found = set(df["split"].unique())
    if not expected.issubset(found):
        raise RuntimeError(f"S1B1 score file missing required splits: expected {expected}, found {found}")
    return df[["date", "instrument", "qlib_score_raw", "qlib_rank", "fold_id", "split"]].sort_values(["date", "qlib_rank", "instrument"])


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
        keep = ["date", "instrument", "close"] + [c for c in input_features if c in df.columns] + [
            "future_return_5d", "future_return_10d", "future_return_20d"
        ]
        frames.append(df[keep])
    if not frames:
        raise RuntimeError("No local OHLCV files matched S1B1 symbols")
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
        "date", "TWII_ret20", "TWII_ret60", "TWII_close_vs_MA60", "TWII_close_vs_MA120",
        "market_volatility20", "market_drawdown60", "market_return_5d", "market_return_10d", "market_return_20d"
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


def unavailable_ranges(frame: pd.DataFrame, flag_col: str) -> list[str]:
    missing_dates = frame.loc[~frame[flag_col], "date"].dropna().sort_values().drop_duplicates().tolist()
    if not missing_dates:
        return []
    ranges: list[str] = []
    start = prev = missing_dates[0]
    for cur in missing_dates[1:]:
        if (cur - prev).days <= 4:
            prev = cur
            continue
        ranges.append(f"{start.date().isoformat()}..{prev.date().isoformat()}")
        start = prev = cur
    ranges.append(f"{start.date().isoformat()}..{prev.date().isoformat()}")
    return ranges


def label_bucket_from_percentile(rank_pct: pd.Series) -> pd.Series:
    out = pd.Series(np.nan, index=rank_pct.index, dtype=float)
    valid = rank_pct.notna()
    out.loc[valid & (rank_pct <= 0.20)] = 0.0
    out.loc[valid & (rank_pct > 0.20) & (rank_pct <= 0.40)] = 1.0
    out.loc[valid & (rank_pct > 0.40) & (rank_pct <= 0.60)] = 2.0
    out.loc[valid & (rank_pct > 0.60) & (rank_pct <= 0.80)] = 3.0
    out.loc[valid & (rank_pct > 0.80)] = 4.0
    return out


def missing_reason_judgement(group: pd.DataFrame, flag_col: str) -> str:
    missing = group.loc[~group[flag_col]].copy()
    if missing.empty:
        return ""
    reasons = []
    if missing["feature_complete"].eq(False).any():
        reasons.append("feature_history_or_price_gap")
    if missing["sample_complete"].eq(False).any() and group[flag_col].sum() < len(group):
        reasons.append("future_price_segment_unavailable_for_some_rows")
    if not reasons:
        reasons.append("localized_price_or_future_horizon_gap")
    return ";".join(sorted(set(reasons)))


def derivation_rule(feature: str) -> str:
    if feature.startswith("qlib_") or feature.startswith("rank_change") or feature.startswith("top"):
        return "derived from same-date qlib walk-forward score/rank and historical rank membership only"
    if feature in {"MA5", "MA10", "MA20", "MA60", "RSI14", "MACD", "Bollinger_position", "ret20", "volatility20", "volume_ratio20"}:
        return "derived from same-date and historical local OHLCV rolling windows"
    if feature in {"avg_trading_value_20d", "volume_stability20", "missing_rate20", "suspension_proxy", "slippage_proxy"}:
        return "derived from same-date and historical local volume/value liquidity proxies"
    return "derived from same-date and historical local TWII/cross-sectional market data"


def build_sample() -> tuple[pd.DataFrame, list[str]]:
    input_features = load_input_features()
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
    symbols = set(scores["instrument"].unique().tolist())
    price_features = load_price_features(symbols, input_features)
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
    sample["regime_segment"] = sample.apply(regime_segment, axis=1)
    output_columns = BASE_COLUMNS + [c for c in input_features if c not in {"qlib_score_raw", "qlib_rank"}] + LABEL_ONLY_COLUMNS + AUDIT_COLUMNS + ["regime_segment"]
    sample = sample[output_columns].sort_values(["date", "qlib_rank", "instrument"]).reset_index(drop=True)
    return sample, input_features


def build_forbidden_audit(input_features: list[str]) -> pd.DataFrame:
    rows = []
    input_set = set(input_features)
    for feat in sorted(input_features):
        rows.append({
            "feature": feat,
            "is_input_feature": True,
            "is_forbidden": feat in FORBIDDEN_FEATURES,
            "forbidden_reason": "forbidden_by_s1b2_contract" if feat in FORBIDDEN_FEATURES else "",
            "is_label_only": feat in LABEL_ONLY_COLUMNS,
            "is_grouping_or_audit": feat in set(BASE_COLUMNS + AUDIT_COLUMNS + ["regime_segment"]),
        })
    for feat in sorted(FORBIDDEN_FEATURES - input_set):
        rows.append({
            "feature": feat,
            "is_input_feature": False,
            "is_forbidden": True,
            "forbidden_reason": "forbidden_by_s1b2_contract",
            "is_label_only": feat in LABEL_ONLY_COLUMNS,
            "is_grouping_or_audit": False,
        })
    return pd.DataFrame(rows).sort_values(["is_input_feature", "feature"], ascending=[False, True])


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    created_at = utc_now()
    sample, input_features = build_sample()
    sample.to_csv(SAMPLE_CSV, index=False)

    duplicate_count = int(sample.duplicated(subset=["date", "instrument"]).sum())
    score_missing_count = int(sample["qlib_score_raw"].isna().sum())
    rank_missing_count = int(sample["qlib_rank"].isna().sum())
    forbidden_hits = sorted(set(input_features) & FORBIDDEN_FEATURES)
    label_input_overlap = sorted(set(input_features) & set(LABEL_ONLY_COLUMNS))

    feature_cov_rows = []
    split_rows = []
    label_summaries: dict[str, Any] = {}
    for split, group in sample.groupby("split", sort=True):
        feature_complete_rows = int(group["feature_complete"].sum())
        label_avail_rows = int(group["label_complete_10d"].sum())
        split_rows.append({
            "split": split,
            "date_start": group["date"].min().date().isoformat(),
            "date_end": group["date"].max().date().isoformat(),
            "date_count": int(group["date"].nunique()),
            "row_count": int(group.shape[0]),
            "instrument_count": int(group["instrument"].nunique()),
            "feature_complete_row_count": feature_complete_rows,
            "label_available_row_count": label_avail_rows,
            "sample_complete_row_count": int(group["sample_complete"].sum()),
        })
        for feat in input_features:
            feature_cov_rows.append({
                "split": split,
                "feature": feat,
                "non_null_count": int(group[feat].notna().sum()),
                "row_count": int(group.shape[0]),
                "coverage_rate": float(group[feat].notna().mean()),
            })
        label_summaries[split] = {
            "row_count": int(group.shape[0]),
            "label_non_null_count": {
                "future_excess_return_5d": int(group["future_excess_return_5d"].notna().sum()),
                "future_excess_return_10d": int(group["future_excess_return_10d"].notna().sum()),
                "future_excess_return_20d": int(group["future_excess_return_20d"].notna().sum()),
                "ltr_relevance_label": int(group["ltr_relevance_label"].notna().sum()),
            },
            "label_complete_counts": {
                "label_complete_5d": int(group["label_complete_5d"].sum()),
                "label_complete_10d": int(group["label_complete_10d"].sum()),
                "label_complete_20d": int(group["label_complete_20d"].sum()),
            },
            "unavailable_label_ranges": {
                "5d": unavailable_ranges(group, "label_complete_5d"),
                "10d": unavailable_ranges(group, "label_complete_10d"),
                "20d": unavailable_ranges(group, "label_complete_20d"),
            },
            "missing_row_count_by_horizon": {
                "5d": int((~group["label_complete_5d"]).sum()),
                "10d": int((~group["label_complete_10d"]).sum()),
                "20d": int((~group["label_complete_20d"]).sum()),
            },
            "missing_reason_judgement": {
                "5d": missing_reason_judgement(group, "label_complete_5d"),
                "10d": missing_reason_judgement(group, "label_complete_10d"),
                "20d": missing_reason_judgement(group, "label_complete_20d"),
            },
            "label_distribution": {
                "ltr_relevance_label": {str(k): int(v) for k, v in group["ltr_relevance_label"].value_counts(dropna=False).sort_index().items()},
                "future_excess_return_10d": {
                    "mean": None if group["future_excess_return_10d"].dropna().empty else float(group["future_excess_return_10d"].mean()),
                    "std": None if group["future_excess_return_10d"].dropna().empty else float(group["future_excess_return_10d"].std()),
                    "min": None if group["future_excess_return_10d"].dropna().empty else float(group["future_excess_return_10d"].min()),
                    "max": None if group["future_excess_return_10d"].dropna().empty else float(group["future_excess_return_10d"].max()),
                },
            },
        }

    pd.DataFrame(feature_cov_rows).to_csv(FEATURE_COVERAGE_CSV, index=False)
    build_forbidden_audit(input_features).to_csv(FORBIDDEN_AUDIT_CSV, index=False)

    schema = {
        "created_at": created_at,
        "sample_path": str(SAMPLE_CSV),
        "input_columns": input_features,
        "label_only_columns": LABEL_ONLY_COLUMNS,
        "audit_columns": AUDIT_COLUMNS,
        "base_columns": BASE_COLUMNS + ["regime_segment"],
        "split_contract": {
            "train_scored": "2017-01-01..2020-12-31",
            "validation": "2021-01-01..2022-12-31",
            "test": "2023-01-01..2025-06-30",
        },
        "primary_training_label": "ltr_relevance_label",
        "primary_future_window": "10 trading days",
    }
    feature_list = {
        "created_at": created_at,
        "source_feature_list": str(FEATURE_SOURCE),
        "input_features": input_features,
        "excluded_whitelist_features": EXCLUDED_WHITE_LIST_FEATURES,
        "derivation_rules": {feature: derivation_rule(feature) for feature in input_features},
    }
    split_summary = {
        "created_at": created_at,
        "provider_uri_note": "WF-VAL came from remote handoff /lustre path; current sample build uses local existing normalized data only",
        "split_rows": split_rows,
        "duplicate_date_instrument_count": duplicate_count,
        "qlib_score_missing_count": score_missing_count,
        "qlib_rank_missing_count": rank_missing_count,
    }
    label_audit = {
        "created_at": created_at,
        "label_horizon": "10 trading days primary relevance label",
        "uses_twii_excess_return": True,
        "primary_label": "ltr_relevance_label",
        "label_only_columns": LABEL_ONLY_COLUMNS,
        "split_label_summary": label_summaries,
    }
    leakage = {
        "created_at": created_at,
        "phase": "phase_s1b2_ltr_sample_build",
        "train_scored_start": "2017-01-01",
        "label_bucket_policy": "fixed_percentile_thresholds",
        "label_bucket_thresholds": LABEL_BUCKET_THRESHOLDS,
        "label_bucket_fit_on_all_splits": False,
        "label_bucket_fit_on_validation_or_test": False,
        "s1_test_feedback_used_for_label_bucket": False,
        "early_train_2015_2016_scored": False,
        "forbidden_feature_hits": forbidden_hits,
        "label_input_overlap": label_input_overlap,
        "s1_test_feedback_used_for_feature_label_or_filtering": False,
        "ltr_training_performed": False,
        "ltr_sample_build_performed": True,
        "portfolio_replay_performed": False,
        "strategy_comparison_performed": False,
        "provider_refresh_publish_performed": False,
        "accepted_latest_switching_performed": False,
        "monitor_or_trading_chain_touched": False,
    }
    gate_ok = (
        duplicate_count == 0 and score_missing_count == 0 and rank_missing_count == 0 and not forbidden_hits and not label_input_overlap
        and {row["split"] for row in split_rows} == {"train_scored", "validation", "test"}
    )
    gate = {
        "created_at": created_at,
        "phase": "phase_s1b2_ltr_sample_build",
        "recommended_gate": "s1b2r_label_bucket_repair_pass_request_s1b3_training_policy_freeze" if gate_ok else "s1b2r_data_integrity_regression",
        "row_count": int(sample.shape[0]),
        "sample_complete_row_count": int(sample["sample_complete"].sum()),
        "duplicate_date_instrument_count": duplicate_count,
        "qlib_score_missing_count": score_missing_count,
        "qlib_rank_missing_count": rank_missing_count,
        "forbidden_feature_hits": forbidden_hits,
        "label_input_overlap": label_input_overlap,
        "no_ltr_training": True,
        "no_replay": True,
        "no_strategy_comparison": True,
        "no_provider_refresh_publish": True,
        "no_accepted_latest_switching": True,
        "no_monitor_or_trading_chain": True,
        "artifacts": {
            "samples": str(SAMPLE_CSV),
            "schema": str(SCHEMA_JSON),
            "feature_list": str(FEATURE_LIST_JSON),
            "split_summary": str(SPLIT_SUMMARY_JSON),
            "label_audit": str(LABEL_AUDIT_JSON),
            "feature_coverage": str(FEATURE_COVERAGE_CSV),
            "forbidden_feature_audit": str(FORBIDDEN_AUDIT_CSV),
            "leakage_boundary_audit": str(LEAKAGE_JSON),
            "gate_summary": str(GATE_JSON),
            "report": "docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B2_LTR_SAMPLE_BUILD_EXECUTION_REPORT_CN.md",
        },
    }

    for path, payload in [
        (SCHEMA_JSON, schema),
        (FEATURE_LIST_JSON, feature_list),
        (SPLIT_SUMMARY_JSON, split_summary),
        (LABEL_AUDIT_JSON, label_audit),
        (LEAKAGE_JSON, leakage),
        (GATE_JSON, gate),
    ]:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")

    print(json.dumps(gate, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
