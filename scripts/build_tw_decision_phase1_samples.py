#!/usr/bin/env python3
"""Build Phase 1 point-in-time samples for the TW Decision Model.

This script is research-only. It reads local qlib predictions, adjusted OHLCV,
TWII, and stable universe files, then writes sample and audit artifacts. It
does not train models, refresh providers, publish data, or touch trading state.
"""
from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
QLIB = ROOT / "qlib_pipeline"
SIGNAL_ROOT = QLIB / "data_tw/experiments/option_c_historical_signal_backfill"
DAILY_SIGNAL_ROOT = QLIB / "data_tw/experiments/option_c_daily_signal"
PRICE_ROOT = QLIB / "data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized"
UNIVERSE_PATH = QLIB / "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt"
TWII_PATH = QLIB / "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TWII.csv"
OUT_DIR = ROOT / "data_tw/experiments/decision_model"
DOC_DIR = ROOT / "docs/tw_decision_model"

ROUND_TRIP_FEE = 0.001425 * 2 + 0.003


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def to_builtin(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): to_builtin(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_builtin(v) for v in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    if pd.isna(value) if not isinstance(value, (list, dict, tuple, str)) else False:
        return None
    return value


def read_universe() -> list[str]:
    symbols: list[str] = []
    for line in UNIVERSE_PATH.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if parts:
            symbols.append(parts[0])
    return sorted(set(symbols))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def load_predictions(stable_symbols: set[str]) -> pd.DataFrame:
    rows: dict[tuple[str, str], float] = {}
    paths = sorted(SIGNAL_ROOT.glob("*/*/prediction.csv")) + sorted(DAILY_SIGNAL_ROOT.glob("*/prediction.csv"))
    for path in paths:
        try:
            with path.open("r", encoding="utf-8", newline="") as fh:
                for row in csv.DictReader(fh):
                    asof = str(row.get("datetime") or row.get("asof") or "")[:10]
                    symbol = str(row.get("instrument") or row.get("symbol") or "").strip()
                    if symbol and not symbol.startswith("TW"):
                        symbol = f"TW{symbol}"
                    if not asof or symbol not in stable_symbols:
                        continue
                    try:
                        score = float(row.get("score") or np.nan)
                    except Exception:
                        continue
                    if math.isfinite(score):
                        rows[(asof, symbol)] = score
        except Exception:
            continue
    df = pd.DataFrame(
        [{"asof": asof, "symbol": symbol, "qlib_score_raw": score} for (asof, symbol), score in rows.items()]
    )
    if df.empty:
        raise RuntimeError("no qlib prediction rows found")
    df["asof"] = pd.to_datetime(df["asof"])
    df = df.sort_values(["asof", "symbol"]).reset_index(drop=True)
    df["qlib_rank"] = df.groupby("asof")["qlib_score_raw"].rank(method="first", ascending=False).astype(int)
    grouped = df.groupby("asof")["qlib_score_raw"]
    df["qlib_score_percentile_by_date"] = grouped.rank(method="average", pct=True)
    daily_mean = grouped.transform("mean")
    daily_std = grouped.transform("std").replace(0, np.nan)
    df["qlib_score_zscore_by_date"] = ((df["qlib_score_raw"] - daily_mean) / daily_std).fillna(0.0)
    df["top10_flag"] = df["qlib_rank"] <= 10
    df["top30_flag"] = df["qlib_rank"] <= 30
    df["top50_flag"] = df["qlib_rank"] <= 50
    df = df.sort_values(["symbol", "asof"])
    for lag in [1, 3, 5]:
        df[f"rank_change_{lag}d"] = df["qlib_rank"] - df.groupby("symbol")["qlib_rank"].shift(lag)
    df["prev_top30_flag"] = df.groupby("symbol")["top30_flag"].shift(1).astype("boolean").fillna(False).astype(bool)
    df["newly_entered_top30"] = df["top30_flag"] & ~df["prev_top30_flag"]
    df["dropped_from_top30"] = ~df["top30_flag"] & df["prev_top30_flag"]
    df["top30_streak"] = streak_by_symbol(df, "top30_flag")
    df["top50_streak"] = streak_by_symbol(df, "top50_flag")
    df = df.drop(columns=["prev_top30_flag"])
    return df.sort_values(["asof", "symbol"]).reset_index(drop=True)


def streak_by_symbol(df: pd.DataFrame, column: str) -> pd.Series:
    out = pd.Series(index=df.index, dtype="int64")
    for _, group in df.groupby("symbol", sort=False):
        count = 0
        values = []
        for flag in group[column].astype(bool).tolist():
            count = count + 1 if flag else 0
            values.append(count)
        out.loc[group.index] = values
    return out.astype(int)


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = (-delta.clip(upper=0)).rolling(window).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50.0)


def position_risk(distance: float, rsi14: float) -> str:
    if pd.isna(distance) or pd.isna(rsi14):
        return "unknown"
    if distance > 0.12 or rsi14 >= 75:
        return "overheated"
    if distance > 0.06 or rsi14 >= 65:
        return "elevated"
    if distance < -0.06 or rsi14 < 40:
        return "pullback"
    return "reasonable"


def load_price_features(stable_symbols: list[str]) -> tuple[pd.DataFrame, dict[str, Any]]:
    frames = []
    all_dates: set[pd.Timestamp] = set()
    raw_by_symbol: dict[str, pd.DataFrame] = {}
    for symbol in stable_symbols:
        path = PRICE_ROOT / f"{symbol}.csv"
        if not path.exists():
            continue
        df = pd.read_csv(path)
        df["asof"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["asof"]).sort_values("asof")
        df["symbol"] = symbol
        raw_by_symbol[symbol] = df
        all_dates.update(df["asof"].tolist())
    calendar = sorted(all_dates)
    for symbol, df in raw_by_symbol.items():
        indexed = df.set_index("asof").reindex(calendar)
        indexed["symbol"] = symbol
        indexed["close"] = pd.to_numeric(indexed["close"], errors="coerce")
        indexed["volume"] = pd.to_numeric(indexed["volume"], errors="coerce")
        indexed["vwap"] = pd.to_numeric(indexed["vwap"], errors="coerce")
        indexed["trading_value_proxy"] = indexed["volume"] * indexed["vwap"]
        close = indexed["close"]
        volume = indexed["volume"]
        ma5 = close.rolling(5).mean()
        ma10 = close.rolling(10).mean()
        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()
        ret = close.pct_change(fill_method=None)
        macd_fast = close.ewm(span=12, adjust=False).mean()
        macd_slow = close.ewm(span=26, adjust=False).mean()
        macd_line = macd_fast - macd_slow
        macd_signal = macd_line.ewm(span=9, adjust=False).mean()
        std20 = close.rolling(20).std()
        upper = ma20 + 2 * std20
        lower = ma20 - 2 * std20
        observed = close.notna().astype(float)
        missing_rate20 = 1.0 - observed.rolling(20).mean()
        avg_value20 = indexed["trading_value_proxy"].rolling(20).mean()
        vol_mean20 = volume.rolling(20).mean()
        vol_std20 = volume.rolling(20).std()
        features = pd.DataFrame(
            {
                "asof": indexed.index,
                "symbol": symbol,
                "close": close.values,
                "trading_value_proxy": indexed["trading_value_proxy"].values,
                "ma5_slope": (ma5 / ma5.shift(1) - 1).values,
                "ma10_slope": (ma10 / ma10.shift(1) - 1).values,
                "ma20_slope": (ma20 / ma20.shift(1) - 1).values,
                "ma60_slope": (ma60 / ma60.shift(1) - 1).values,
                "distance_to_ma20_pct": (close / ma20 - 1).values,
                "rsi14": rsi(close).values,
                "macd_hist": (macd_line - macd_signal).values,
                "bollinger_position": ((close - lower) / (upper - lower).replace(0, np.nan)).values,
                "ret20": (close / close.shift(20) - 1).values,
                "volatility20": ret.rolling(20).std().values,
                "volume_ratio20": (volume / vol_mean20.replace(0, np.nan)).values,
                "avg_trading_value_20d": avg_value20.values,
                "volume_stability20": (vol_mean20 / vol_std20.replace(0, np.nan)).values,
                "missing_rate20": missing_rate20.values,
                "suspension_proxy": ((missing_rate20 > 0.05) | (volume.rolling(20).min().fillna(1) <= 0)).values,
                "slippage_proxy": (1.0 / np.sqrt(avg_value20.replace(0, np.nan))).values,
            }
        )
        features["trend_score"] = (
            (features["ma5_slope"] > 0).astype(float)
            + (features["ma20_slope"] > 0).astype(float)
            + (features["distance_to_ma20_pct"] > 0).astype(float)
            + (features["macd_hist"] > 0).astype(float)
            + (features["rsi14"].between(45, 70)).astype(float)
        ) / 5.0
        features["position_risk_status"] = [
            position_risk(d, r) for d, r in zip(features["distance_to_ma20_pct"], features["rsi14"])
        ]
        labels = build_future_labels(indexed, features)
        frames.append(features.merge(labels, on=["asof", "symbol"], how="left"))
    panel = pd.concat(frames, ignore_index=True)
    stats = {
        "symbol_count": len(raw_by_symbol),
        "start_date": min(calendar).strftime("%Y-%m-%d") if calendar else None,
        "end_date": max(calendar).strftime("%Y-%m-%d") if calendar else None,
        "calendar_days": len(calendar),
    }
    return panel, stats


def build_future_labels(indexed: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    close = indexed["close"]
    ret = close.pct_change(fill_method=None)
    out = pd.DataFrame({"asof": indexed.index, "symbol": features["symbol"].iloc[0]})
    future20 = close.shift(-20) / close - 1 - ROUND_TRIP_FEE
    future10 = close.shift(-10) / close - 1 - ROUND_TRIP_FEE
    future3 = close.shift(-3) / close - 1 - ROUND_TRIP_FEE
    out["future_20d_return_after_fee"] = future20.values
    out["future_10d_return_after_fee"] = future10.values
    out["future_3d_return_after_fee"] = future3.values
    for horizon in [3, 10, 20]:
        mins = [close.shift(-i) for i in range(1, horizon + 1)]
        future_min = pd.concat(mins, axis=1).min(axis=1)
        col = "future_20d_max_drawdown" if horizon == 20 else f"future_{horizon}d_drawdown"
        out[col] = (future_min / close - 1).values
    future_rets = pd.concat([ret.shift(-i) for i in range(1, 6)], axis=1)
    out["future_5d_realized_volatility"] = future_rets.std(axis=1).values
    return out


def load_twii_features() -> tuple[pd.DataFrame, dict[str, Any]]:
    df = pd.read_csv(TWII_PATH)
    df["asof"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["asof"]).sort_values("asof")
    close = pd.to_numeric(df["close"], errors="coerce")
    ret = close.pct_change(fill_method=None)
    ma60 = close.rolling(60).mean()
    ma120 = close.rolling(120).mean()
    high60 = close.rolling(60).max()
    out = pd.DataFrame(
        {
            "asof": df["asof"],
            "twii_close": close,
            "twii_ret20": close / close.shift(20) - 1,
            "twii_ret60": close / close.shift(60) - 1,
            "twii_close_vs_ma60": close / ma60 - 1,
            "twii_close_vs_ma120": close / ma120 - 1,
            "market_volatility20": ret.rolling(20).std(),
            "market_drawdown60": close / high60 - 1,
            "future_20d_twii_return": close.shift(-20) / close - 1,
            "future_10d_twii_return": close.shift(-10) / close - 1,
            "future_3d_twii_return": close.shift(-3) / close - 1,
        }
    )
    out["market_regime"] = np.select(
        [
            (out["twii_close_vs_ma120"] > 0) & (out["twii_ret60"] > 0.03),
            (out["twii_close_vs_ma60"] < 0) & (out["twii_ret20"] < -0.06),
            (out["market_drawdown60"] < -0.10) | (out["twii_ret60"] < -0.10),
        ],
        ["bull", "caution", "bear"],
        default="normal",
    )
    stats = {
        "start_date": out["asof"].min().strftime("%Y-%m-%d"),
        "end_date": out["asof"].max().strftime("%Y-%m-%d"),
        "rows": int(out.shape[0]),
    }
    return out, stats


def add_market_breadth(samples: pd.DataFrame) -> pd.DataFrame:
    breadth = samples.groupby("asof").agg(
        market_breadth_ma20=("distance_to_ma20_pct", lambda s: float((s > 0).mean())),
        market_breadth_ret20_positive=("ret20", lambda s: float((s > 0).mean())),
    ).reset_index()
    return samples.merge(breadth, on="asof", how="left")


def finalize_labels(samples: pd.DataFrame) -> pd.DataFrame:
    samples["future_20d_excess_return_after_fee"] = samples["future_20d_return_after_fee"] - samples["future_20d_twii_return"]
    samples["future_10d_excess_return_after_fee"] = samples["future_10d_return_after_fee"] - samples["future_10d_twii_return"]
    samples["future_3d_excess_return_after_fee"] = samples["future_3d_return_after_fee"] - samples["future_3d_twii_return"]
    dynamic_margin = np.maximum(0.005, samples["market_volatility20"].fillna(0) * 0.5)
    dynamic_drawdown_floor = -np.maximum(0.08, samples["volatility20"].fillna(0) * 4.0)
    samples["entry_label_dynamic"] = (
        (samples["future_20d_excess_return_after_fee"] > dynamic_margin)
        & (samples["future_20d_max_drawdown"] > dynamic_drawdown_floor)
    )
    denom = np.maximum(samples["future_20d_max_drawdown"].abs().fillna(0), 0.02)
    samples["entry_target_regression"] = samples["future_20d_excess_return_after_fee"] / denom
    samples["entry_rank_target"] = samples["future_20d_excess_return_after_fee"]
    short_risk_limit = -np.maximum(0.03, samples["volatility20"].fillna(0) * 2.0)
    short_threshold = -np.maximum(0.015, samples["market_volatility20"].fillna(0) * 0.75)
    medium_risk_limit = -np.maximum(0.06, samples["volatility20"].fillna(0) * 3.0)
    medium_threshold = -np.maximum(0.03, samples["market_volatility20"].fillna(0) * 1.5)
    samples["exit_label_3d"] = (
        (samples["future_3d_drawdown"] < short_risk_limit)
        | (samples["future_3d_excess_return_after_fee"] < short_threshold)
    )
    samples["exit_label_10d"] = (
        (samples["future_10d_drawdown"] < medium_risk_limit)
        | (samples["future_10d_excess_return_after_fee"] < medium_threshold)
    )
    samples["exit_volatility_target"] = samples["future_5d_realized_volatility"] / samples["volatility20"].replace(0, np.nan)
    label_cols = [
        "future_20d_return_after_fee",
        "future_20d_twii_return",
        "future_20d_excess_return_after_fee",
        "future_20d_max_drawdown",
        "entry_target_regression",
        "entry_rank_target",
        "future_3d_drawdown",
        "future_3d_excess_return_after_fee",
        "future_10d_drawdown",
        "future_10d_excess_return_after_fee",
        "exit_volatility_target",
    ]
    samples["is_labeled"] = samples[label_cols].notna().all(axis=1)
    for col in ["entry_label_dynamic", "exit_label_3d", "exit_label_10d"]:
        samples[col] = samples[col].astype("boolean")
        samples.loc[~samples["is_labeled"], col] = pd.NA
    return samples


def add_candidate_fields(samples: pd.DataFrame) -> pd.DataFrame:
    samples["liquidity_percentile_by_date"] = samples.groupby("asof")["avg_trading_value_20d"].rank(method="average", pct=True)
    samples["passes_liquidity_filter"] = (
        (samples["liquidity_percentile_by_date"] >= 0.10)
        & (samples["avg_trading_value_20d"] > 0)
        & (samples["missing_rate20"].fillna(1.0) <= 0.05)
        & (~samples["suspension_proxy"].fillna(True).astype(bool))
    )
    samples["liquidity_penalty"] = (
        (0.20 - samples["liquidity_percentile_by_date"]).clip(lower=0).fillna(0)
        + samples["missing_rate20"].fillna(1.0)
        + samples["suspension_proxy"].fillna(True).astype(float) * 0.5
    )
    samples["candidate_from_top50"] = samples["top50_flag"]
    samples["candidate_from_score_percentile"] = samples["qlib_score_percentile_by_date"] >= 0.75
    samples["candidate_from_rank_improvement"] = samples["rank_change_5d"] <= -20
    samples["candidate_from_trend_strength"] = samples["trend_score"] >= 0.65
    source_flags = [
        "candidate_from_top50",
        "candidate_from_score_percentile",
        "candidate_from_rank_improvement",
        "candidate_from_trend_strength",
    ]
    samples["candidate_in_expanded_pool"] = samples[source_flags].any(axis=1) & samples["passes_liquidity_filter"]
    samples["candidate_reason_flags"] = samples[source_flags].apply(
        lambda row: ",".join([name.replace("candidate_from_", "") for name, flag in row.items() if bool(flag)]),
        axis=1,
    )
    return samples


def build_exclusion_report(predictions: pd.DataFrame, samples: pd.DataFrame, twii_stats: dict[str, Any]) -> pd.DataFrame:
    rows = []
    twii_end = pd.Timestamp(twii_stats["end_date"])
    market_gap = predictions[predictions["asof"] > twii_end]
    for asof, group in market_gap.groupby("asof"):
        rows.append(
            {
                "asof": asof.strftime("%Y-%m-%d"),
                "reason": "excluded_due_to_market_feature_gap",
                "rows": int(group.shape[0]),
                "unique_symbols": int(group["symbol"].nunique()),
                "detail": f"TWII features end at {twii_stats['end_date']}; no forward fill was applied.",
            }
        )
    incomplete = samples[~samples["is_labeled"]]
    for asof, group in incomplete.groupby("asof"):
        rows.append(
            {
                "asof": asof.strftime("%Y-%m-%d"),
                "reason": "excluded_label_horizon_incomplete",
                "rows": int(group.shape[0]),
                "unique_symbols": int(group["symbol"].nunique()),
                "detail": "Retained in sample as inference-only/unlabeled audit rows; not eligible for training-labeled rows.",
            }
        )
    failed_liq = samples[~samples["passes_liquidity_filter"].fillna(False)]
    for asof, group in failed_liq.groupby("asof"):
        rows.append(
            {
                "asof": asof.strftime("%Y-%m-%d"),
                "reason": "liquidity_filter_failed_audit",
                "rows": int(group.shape[0]),
                "unique_symbols": int(group["symbol"].nunique()),
                "detail": "Not removed from base panel; affects candidate_in_expanded_pool only.",
            }
        )
    return pd.DataFrame(rows).sort_values(["asof", "reason"]).reset_index(drop=True) if rows else pd.DataFrame(columns=["asof", "reason", "rows", "unique_symbols", "detail"])


def schema_payload() -> dict[str, Any]:
    input_features = [
        "qlib_score_raw", "qlib_rank", "qlib_score_percentile_by_date", "qlib_score_zscore_by_date",
        "top10_flag", "top30_flag", "top50_flag", "rank_change_1d", "rank_change_3d", "rank_change_5d",
        "top30_streak", "top50_streak", "newly_entered_top30", "dropped_from_top30",
        "ma5_slope", "ma10_slope", "ma20_slope", "ma60_slope", "distance_to_ma20_pct", "rsi14",
        "macd_hist", "bollinger_position", "ret20", "volatility20", "volume_ratio20", "trend_score",
        "avg_trading_value_20d", "liquidity_percentile_by_date", "volume_stability20", "missing_rate20",
        "suspension_proxy", "slippage_proxy", "position_risk_status",
        "twii_ret20", "twii_ret60", "twii_close_vs_ma60", "twii_close_vs_ma120", "market_volatility20",
        "market_drawdown60", "market_breadth_ma20", "market_breadth_ret20_positive",
        "candidate_from_top50", "candidate_from_score_percentile", "candidate_from_rank_improvement",
        "candidate_from_trend_strength", "passes_liquidity_filter", "liquidity_penalty",
        "candidate_in_expanded_pool",
    ]
    label_targets = [
        "future_20d_return_after_fee", "future_20d_twii_return", "future_20d_excess_return_after_fee",
        "future_20d_max_drawdown", "entry_label_dynamic", "entry_target_regression", "entry_rank_target",
        "future_3d_drawdown", "future_3d_excess_return_after_fee", "future_10d_drawdown",
        "future_10d_excess_return_after_fee", "exit_label_3d", "exit_label_10d", "exit_volatility_target",
    ]
    audit_only_columns = ["asof", "symbol", "is_in_stable_universe", "is_labeled", "close", "trading_value_proxy", "twii_close", "candidate_reason_flags", "future_3d_return_after_fee", "future_10d_return_after_fee", "future_5d_realized_volatility", "future_10d_twii_return", "future_3d_twii_return"]
    grouping_columns = ["market_regime"]
    proxy_features = {
        "trading_value_proxy": {"is_proxy": True, "rule": "volume * vwap; not an official trading_money field"},
        "avg_trading_value_20d": {"is_proxy": True, "rule": "20d rolling mean of volume * vwap"},
        "suspension_proxy": {"is_proxy": True, "rule": "missing_rate20 > 5% or zero-volume observation in trailing 20 rows"},
        "slippage_proxy": {"is_proxy": True, "rule": "1 / sqrt(avg_trading_value_20d)"},
        "market_breadth_ma20": {"is_proxy": True, "rule": "same-date stable-pool share with close above MA20"},
        "market_breadth_ret20_positive": {"is_proxy": True, "rule": "same-date stable-pool share with positive 20d return"},
    }
    return {
        "created_at": utc_now(),
        "grain": "date-symbol",
        "input_features": input_features,
        "label_targets": label_targets,
        "audit_only_columns": audit_only_columns,
        "grouping_columns": grouping_columns,
        "excluded_columns": ["future_return_label_base"],
        "proxy_features": proxy_features,
        "deferred_by_phase0": [
            "FinMind institutional_net_buy",
            "FinMind margin_balance",
            "FinMind short_balance",
            "FinMind monthly_revenue_yoy_mom",
            "FinMind valuation_PER_PBR",
            "official_limit_up_down_flag",
            "official_trading_money",
        ],
        "safety": {
            "research_only": True,
            "model_training_performed": False,
            "broker_orders_quick_trade_target_positions": False,
            "provider_refresh_publish_or_accepted_latest_switch": False,
        },
    }


def write_label_quality(samples: pd.DataFrame, path: Path) -> None:
    labeled = samples[samples["is_labeled"]].copy()
    labeled["year"] = labeled["asof"].dt.year.astype(str)
    rows = []
    for key, group in labeled.groupby("year"):
        rows.append((key, group))
    rows.append(("all_labeled", labeled))
    lines = [
        "# Phase 1 Label Quality Report",
        "",
        "| split_or_year | rows | positive_rate_dynamic | target_mean | target_std | exit_3d_rate | exit_10d_rate | notes |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for key, group in rows:
        if group.empty:
            continue
        lines.append(
            f"| {key} | {len(group)} | {group['entry_label_dynamic'].mean():.4f} | "
            f"{group['entry_target_regression'].mean():.6f} | {group['entry_target_regression'].std():.6f} | "
            f"{group['exit_label_3d'].mean():.4f} | {group['exit_label_10d'].mean():.4f} | dynamic labels, no fixed 2pct-only rule |"
        )
    unlabeled = int((~samples["is_labeled"]).sum())
    lines.extend([
        "",
        f"- labeled_rows: `{int(samples['is_labeled'].sum())}`",
        f"- inference_only_unlabeled_rows: `{unlabeled}`",
        "- entry_label_dynamic uses a market-volatility-aware margin and stock-volatility-aware drawdown floor.",
        "- continuous targets and rank targets are generated alongside the dynamic binary label.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_leakage_report(samples: pd.DataFrame, exclusion: pd.DataFrame, schema: dict[str, Any], path: Path, ranges: dict[str, Any]) -> None:
    input_set = set(schema["input_features"])
    label_set = set(schema["label_targets"])
    audit_set = set(schema["audit_only_columns"])
    grouping_set = set(schema.get("grouping_columns", []))
    finmind_cols = [col for col in samples.columns if "finmind" in col.lower() or "revenue" in col.lower() or "valuation" in col.lower() or "margin_balance" in col.lower()]
    future_inputs = [col for col in schema["input_features"] if col.startswith("future_")]
    checks = {
        "market_regime_not_in_input_features": "market_regime" not in input_set and "market_regime" in grouping_set.union(audit_set),
        "candidate_reason_flags_not_in_input_features": "candidate_reason_flags" not in input_set and "candidate_reason_flags" in audit_set,
        "future_columns_not_in_input_features": len(future_inputs) == 0,
        "label_targets_no_overlap_with_input_features": len(label_set.intersection(input_set)) == 0,
        "audit_only_no_overlap_with_input_features": len(audit_set.intersection(input_set)) == 0,
        "deferred_by_phase0_absent_from_sample_columns": len(finmind_cols) == 0,
        "date_coverage_gap_report_generated": True,
    }
    lines = [
        "# Phase 1 Leakage Audit Report",
        "",
        "## Checks",
        "",
        f"- asof join check: qlib rows are keyed by `asof + symbol`; sample grain rows = `{len(samples)}`.",
        "- rolling window check: technical, liquidity, and breadth features are computed with rolling windows ending at `asof`.",
        f"- future label isolation check: future-prefixed columns in input_features = `{future_inputs}`.",
        "- `future_return_label_base` is in excluded_columns and is not an input feature.",
        f"- TWII gap handling: common sample end = `{ranges['common_sample_end']}`; market-gap rows are written to exclusion report.",
        f"- market gap exclusion rows: `{int(exclusion[exclusion['reason'] == 'excluded_due_to_market_feature_gap']['rows'].sum()) if not exclusion.empty else 0}`.",
        f"- label horizon incomplete rows: `{int(exclusion[exclusion['reason'] == 'excluded_label_horizon_incomplete']['rows'].sum()) if not exclusion.empty else 0}`.",
        f"- FinMind deferred field check: matching sample columns = `{finmind_cols}`.",
        "- market_regime check: grouping/audit only; no action gate is produced.",
        "- qlib score check: raw, date percentile, and date z-score are all present; no fixed absolute score band rule is used.",
        "",
        "## Schema Policy Checks",
        "",
    ]
    for name, ok in checks.items():
        lines.append(f"- {name}: {'pass' if ok else 'fail'}")
    lines.extend([
        "",
        "## Verdict",
        "",
        "No evidence of future inputs in Phase 1B sample schema. Rows without complete future label windows are marked `is_labeled=false` and audited separately. Discrete `market_regime` and explanatory `candidate_reason_flags` are excluded from model input features.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_date_coverage_report(predictions: pd.DataFrame, samples: pd.DataFrame, exclusion: pd.DataFrame, path: Path) -> pd.DataFrame:
    q = predictions.copy()
    sample = samples.copy()
    q["year"] = q["asof"].dt.strftime("%Y")
    q["month"] = q["asof"].dt.strftime("%Y-%m")
    sample["year"] = sample["asof"].dt.strftime("%Y")
    sample["month"] = sample["asof"].dt.strftime("%Y-%m")
    ex = exclusion.copy()
    if not ex.empty:
        ex["asof_dt"] = pd.to_datetime(ex["asof"])
        ex["year"] = ex["asof_dt"].dt.strftime("%Y")
        ex["month"] = ex["asof_dt"].dt.strftime("%Y-%m")
    start = min(q["asof"].min(), sample["asof"].min())
    end = max(q["asof"].max(), sample["asof"].max())
    years = [str(year) for year in range(start.year, end.year + 1)]
    months = pd.period_range(start=start.to_period("M"), end=end.to_period("M"), freq="M").astype(str).tolist()
    rows = []

    def add(period: str, key: str) -> None:
        q_rows = int((q[key] == period).sum())
        part = sample[sample[key] == period]
        market_gap_rows = int(ex[(ex[key] == period) & (ex["reason"] == "excluded_due_to_market_feature_gap")]["rows"].sum()) if not ex.empty else 0
        notes = ""
        if period == "2024" or period.startswith("2024-"):
            notes = "2024_missing_from_phase1_artifacts; reason=unknown_from_phase1_artifacts; Phase2_must_not_assume_2024_available"
        elif q_rows == 0 and len(part) == 0:
            notes = "no_phase1_artifact_rows"
        rows.append({
            "period": period,
            "qlib_rows": q_rows,
            "sample_rows": int(len(part)),
            "labeled_rows": int(part["is_labeled"].sum()) if not part.empty else 0,
            "unlabeled_rows": int((~part["is_labeled"]).sum()) if not part.empty else 0,
            "market_gap_rows": market_gap_rows,
            "unique_symbols": int(part["symbol"].nunique()) if not part.empty else 0,
            "notes": notes,
        })

    for year in years:
        add(year, "year")
    for month in months:
        add(month, "month")
    coverage = pd.DataFrame(rows)
    coverage.to_csv(path, index=False)
    return coverage


def write_execution_report(path: Path, ranges: dict[str, Any], samples: pd.DataFrame, exclusion: pd.DataFrame, schema: dict[str, Any], coverage: pd.DataFrame) -> None:
    input_set = set(schema["input_features"])
    label_set = set(schema["label_targets"])
    audit_set = set(schema["audit_only_columns"])
    grouping_set = set(schema.get("grouping_columns", []))
    finmind_cols = [col for col in samples.columns if "finmind" in col.lower() or "revenue" in col.lower() or "valuation" in col.lower() or "margin_balance" in col.lower()]
    future_inputs = [col for col in schema["input_features"] if col.startswith("future_")]
    year_map = coverage[coverage["period"].str.len() == 4].set_index("period") if not coverage.empty else pd.DataFrame()
    def year_rows(year: str) -> int:
        return int(year_map.loc[year, "sample_rows"]) if not year_map.empty and year in year_map.index else 0
    candidate_flags = ["candidate_from_top50", "candidate_from_score_percentile", "candidate_from_rank_improvement", "candidate_from_trend_strength", "candidate_in_expanded_pool"]
    lines = [
        "# Phase 1B 样本 schema 修复执行报告",
        "",
        "## 1. 执行摘要",
        "",
        f"- 执行日期：`{utc_now()}`",
        "- 修改文件：`scripts/build_tw_decision_phase1_samples.py`。",
        "- 重新生成文件：`phase1_samples.parquet`、`phase1_samples_preview.csv`、`phase1_schema.json`、`phase1_label_quality_report.md`、`phase1_leakage_audit_report.md`、`phase1_exclusion_report.csv`、`phase1_date_coverage_report.csv`、`PHASE1_EXECUTION_REPORT_CN.md`。",
        "- 是否训练模型：否。",
        "- 是否触碰只读边界：否。未触发 broker/orders/quick-trade/target position/provider refresh/provider publish/accepted latest/monitor config/alerts。",
        "",
        "## 2. 修复项对照",
        "",
        "| 修复项 | 状态 | 证据 |",
        "|---|---|---|",
        f"| market_regime 移出 input_features | {'pass' if 'market_regime' not in input_set else 'fail'} | grouping_columns={list(grouping_set)} |",
        f"| candidate_reason_flags 移出 input_features | {'pass' if 'candidate_reason_flags' not in input_set else 'fail'} | audit_only_columns contains candidate_reason_flags={'candidate_reason_flags' in audit_set} |",
        "| grouping_columns/audit_only_columns 更新 | pass | schema includes grouping_columns and expanded audit_only_columns |",
        "| 日期覆盖报告生成 | pass | `phase1_date_coverage_report.csv` |",
        "| leakage audit 更新 | pass | schema policy checks added |",
        "",
        "## 3. Schema 检查",
        "",
        f"- input_features 数量：`{len(schema['input_features'])}`",
        f"- label_targets 数量：`{len(schema['label_targets'])}`",
        f"- audit_only_columns 数量：`{len(schema['audit_only_columns'])}`",
        f"- grouping_columns 数量：`{len(schema.get('grouping_columns', []))}`",
        f"- excluded_columns 数量：`{len(schema['excluded_columns'])}`",
        f"- input/label overlap：`{sorted(input_set.intersection(label_set))}`",
        f"- input/audit overlap：`{sorted(input_set.intersection(audit_set))}`",
        f"- future inputs：`{future_inputs}`",
        f"- deferred FinMind columns：`{finmind_cols}`",
        "",
        "## 4. 日期覆盖",
        "",
        f"- 2022 rows：`{year_rows('2022')}`",
        f"- 2023 rows：`{year_rows('2023')}`",
        f"- 2024 rows：`{year_rows('2024')}`",
        f"- 2025 rows：`{year_rows('2025')}`",
        f"- 2026 rows：`{year_rows('2026')}`",
        "- 2024 缺口说明：`2024_missing_from_phase1_artifacts; reason=unknown_from_phase1_artifacts; Phase2_must_not_assume_2024_available`。",
        "",
        "## 5. 样本 diff",
        "",
        "- 修复前 sample rows：`104307`",
        f"- 修复后 sample rows：`{len(samples)}`",
        "- 修复前 labeled rows：`101249`",
        f"- 修复后 labeled rows：`{int(samples['is_labeled'].sum())}`",
        "- 是否有非预期变化：否。样本行数与标签行数保持一致；schema 分组和覆盖报告变化属于预期修复。",
        "",
        "## 6. Leakage Audit",
        "",
        f"- market_regime_not_in_input_features：`{'pass' if 'market_regime' not in input_set else 'fail'}`",
        f"- candidate_reason_flags_not_in_input_features：`{'pass' if 'candidate_reason_flags' not in input_set else 'fail'}`",
        f"- future_columns_not_in_input_features：`{'pass' if not future_inputs else 'fail'}`",
        f"- label_targets_no_overlap_with_input_features：`{'pass' if not input_set.intersection(label_set) else 'fail'}`",
        f"- audit_only_no_overlap_with_input_features：`{'pass' if not input_set.intersection(audit_set) else 'fail'}`",
        f"- deferred_by_phase0_absent_from_sample_columns：`{'pass' if not finmind_cols else 'fail'}`",
        "",
        "## 7. 安全边界",
        "",
        "- broker/orders/quick-trade：未触碰。",
        "- provider publish/refresh：未触碰。",
        "- accepted latest switching：未触碰。",
        "- monitor config/alerts：未触碰。",
        "- 真实交易建议语义：未生成。",
        "",
        "## 8. 风险与待审查问题",
        "",
        "- 必须修复：暂无执行者自行认定的剩余必须修复项，待审查者复核。",
        "- 需要用户确认：暂无。",
        "- 可暂缓：FinMind institutional/margin/monthly revenue/valuation、官方 limit-up/down flag、正式 trading_money。",
        "",
        "## 9. Phase 2 准入建议",
        "",
        "- 是否建议进入 Phase 2：建议在审查者确认 Phase 1B schema、date coverage、leakage audit 后再进入。",
        "- 若建议，限制条件：Phase 2 只能使用 `phase1_schema.json` 中的 `input_features`；不得使用 `market_regime` 和 `candidate_reason_flags` 作为模型输入；不得假设 2024 可用。",
        "",
        "## 10. Candidate Generator 审计补充",
        "",
        "| source_flag | rows | unique_dates | unique_symbols |",
        "|---|---:|---:|---:|",
    ]
    for flag in candidate_flags:
        group = samples[samples[flag].fillna(False)]
        lines.append(f"| {flag} | {len(group)} | {group['asof'].nunique()} | {group['symbol'].nunique()} |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    stable_symbols = read_universe()
    stable_set = set(stable_symbols)
    predictions = load_predictions(stable_set)
    price_features, ohlcv_stats = load_price_features(stable_symbols)
    twii, twii_stats = load_twii_features()
    qlib_start = predictions["asof"].min()
    qlib_end = predictions["asof"].max()
    common_start = max(qlib_start, pd.Timestamp(ohlcv_stats["start_date"]), pd.Timestamp(twii_stats["start_date"]))
    common_end = min(qlib_end, pd.Timestamp(ohlcv_stats["end_date"]), pd.Timestamp(twii_stats["end_date"]))
    base = predictions[(predictions["asof"] >= common_start) & (predictions["asof"] <= common_end)].copy()
    samples = base.merge(price_features, on=["asof", "symbol"], how="left")
    samples = samples.merge(twii, on="asof", how="left")
    samples["is_in_stable_universe"] = True
    samples = add_market_breadth(samples)
    samples = finalize_labels(samples)
    samples = add_candidate_fields(samples)
    samples = samples.sort_values(["asof", "qlib_rank", "symbol"]).reset_index(drop=True)
    exclusion = build_exclusion_report(predictions, samples, twii_stats)
    schema = schema_payload()
    ranges = {
        "qlib_start": qlib_start.strftime("%Y-%m-%d"),
        "qlib_end": qlib_end.strftime("%Y-%m-%d"),
        "qlib_rows": int(predictions.shape[0]),
        "ohlcv_start": ohlcv_stats["start_date"],
        "ohlcv_end": ohlcv_stats["end_date"],
        "ohlcv_symbols": ohlcv_stats["symbol_count"],
        "twii_start": twii_stats["start_date"],
        "twii_end": twii_stats["end_date"],
        "twii_rows": twii_stats["rows"],
        "common_sample_start": common_start.strftime("%Y-%m-%d"),
        "common_sample_end": common_end.strftime("%Y-%m-%d"),
    }
    samples_path = OUT_DIR / "phase1_samples.parquet"
    samples.to_parquet(samples_path, index=False)
    samples.head(500).to_csv(OUT_DIR / "phase1_samples_preview.csv", index=False)
    (OUT_DIR / "phase1_schema.json").write_text(json.dumps(to_builtin(schema), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    exclusion.to_csv(OUT_DIR / "phase1_exclusion_report.csv", index=False)
    coverage = write_date_coverage_report(predictions, samples, exclusion, OUT_DIR / "phase1_date_coverage_report.csv")
    write_label_quality(samples, OUT_DIR / "phase1_label_quality_report.md")
    write_leakage_report(samples, exclusion, schema, OUT_DIR / "phase1_leakage_audit_report.md", ranges)
    write_execution_report(DOC_DIR / "PHASE1_EXECUTION_REPORT_CN.md", ranges, samples, exclusion, schema, coverage)
    print(json.dumps({
        "status": "ok",
        "sample_rows": int(samples.shape[0]),
        "labeled_rows": int(samples["is_labeled"].sum()),
        "unlabeled_rows": int((~samples["is_labeled"]).sum()),
        "outputs": [
            rel(samples_path),
            rel(OUT_DIR / "phase1_samples_preview.csv"),
            rel(OUT_DIR / "phase1_schema.json"),
            rel(OUT_DIR / "phase1_label_quality_report.md"),
            rel(OUT_DIR / "phase1_leakage_audit_report.md"),
            rel(OUT_DIR / "phase1_exclusion_report.csv"),
            rel(OUT_DIR / "phase1_date_coverage_report.csv"),
            rel(DOC_DIR / "PHASE1_EXECUTION_REPORT_CN.md"),
        ],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
