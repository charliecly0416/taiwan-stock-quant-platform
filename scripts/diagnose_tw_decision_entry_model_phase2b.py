#!/usr/bin/env python3
"""Diagnose Phase 2B Entry Model v1 for TW Decision Model research.

This script is limited to Phase 2B diagnostics: gate deltas, ensemble
calibration repair, predefined feature group ablation, and failure analysis.
It does not train exit models, run portfolio replay, refresh providers,
publish data, or touch trading state.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd

from train_tw_decision_entry_model_v1 import (
    SEED,
    SPLITS,
    SplitSpec,
    metric_row,
    prepare_x,
    safe_auc,
    safe_logloss,
    split_mask,
    topk_metrics,
)


ROOT = Path(__file__).resolve().parents[1]
IN_DIR = ROOT / "data_tw/experiments/decision_model"
OUT_DIR = IN_DIR / "phase2_entry_model_v1"
DOC_DIR = ROOT / "docs/tw_decision_model"
SAMPLE_PATH = IN_DIR / "phase1_samples.parquet"
SCHEMA_PATH = IN_DIR / "phase1_schema.json"
PRED_PATH = OUT_DIR / "phase2_predictions.parquet"
METRICS_PATH = OUT_DIR / "phase2_metrics.csv"

GATE_PATH = OUT_DIR / "phase2b_gate_deltas.csv"
CALIBRATION_COMPARE_PATH = OUT_DIR / "phase2b_ensemble_calibration_compare.csv"
ABLATION_PATH = OUT_DIR / "phase2b_feature_group_ablation.csv"
BINARY_DIAG_PATH = OUT_DIR / "phase2b_binary_diagnostics.csv"
REGRESSION_DIAG_PATH = OUT_DIR / "phase2b_regression_diagnostics.csv"
DIAG_REPORT_PATH = DOC_DIR / "PHASE2B_ENTRY_MODEL_DIAGNOSIS_REPORT_CN.md"
EXEC_REPORT_PATH = DOC_DIR / "PHASE2B_EXECUTION_REPORT_CN.md"

BASELINE_MODELS = [
    "baseline_qlib_raw",
    "baseline_qlib_percentile",
    "baseline_qlib_rank",
    "baseline_candidate_sort",
]
GATE_MODEL_COLS = {
    "binary": "entry_score_binary",
    "regression": "entry_score_regression",
    "ensemble_original": "entry_score_v1",
    "ensemble_fixed_trainval": "entry_score_ensemble_trainval",
    "ensemble_fixed_same_asof": "entry_score_ensemble_same_asof",
}


@dataclass
class TrainedGroup:
    split_name: str
    feature_group: str
    features: list[str]
    binary: lgb.LGBMClassifier
    regression: lgb.LGBMRegressor


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_no rows_"
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---" for _ in cols]) + "|"]
    for _, row in df.iterrows():
        values = []
        for col in cols:
            value = row[col]
            if isinstance(value, float):
                values.append("" if pd.isna(value) else f"{value:.6f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def minmax_apply(series: pd.Series, lo: float, hi: float, clip: bool = True) -> pd.Series:
    if not math.isfinite(float(lo)) or not math.isfinite(float(hi)) or hi == lo:
        return pd.Series(0.5, index=series.index)
    out = (series - lo) / (hi - lo)
    return out.clip(0.0, 1.0) if clip else out


def same_asof_minmax(df: pd.DataFrame, score_col: str) -> pd.Series:
    def normalize(s: pd.Series) -> pd.Series:
        lo = s.min()
        hi = s.max()
        if not math.isfinite(float(lo)) or not math.isfinite(float(hi)) or hi == lo:
            return pd.Series(0.5, index=s.index)
        return (s - lo) / (hi - lo)

    return df.groupby(["split_name", "split_part", "asof"], group_keys=False)[score_col].apply(normalize)


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any], list[str]]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    features = list(schema["input_features"])
    forbidden = {"market_regime", "candidate_reason_flags"}
    if forbidden.intersection(features):
        raise RuntimeError(f"forbidden fields in input_features: {sorted(forbidden.intersection(features))}")
    future_inputs = [col for col in features if col.startswith("future_")]
    if future_inputs:
        raise RuntimeError(f"future fields in input_features: {future_inputs}")

    samples = pd.read_parquet(SAMPLE_PATH)
    samples["asof"] = pd.to_datetime(samples["asof"])
    samples["year"] = samples["asof"].dt.year
    trainable = samples[(samples["is_labeled"]) & (samples["candidate_in_expanded_pool"]) & (samples["passes_liquidity_filter"])].copy()

    predictions = pd.read_parquet(PRED_PATH)
    predictions["asof"] = pd.to_datetime(predictions["asof"])
    metrics = pd.read_csv(METRICS_PATH)
    return trainable, predictions, metrics, schema, features


def add_fixed_ensembles(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    pred = predictions.copy()
    rows = []
    for split_name, split_df in pred.groupby("split_name"):
        fit = split_df[split_df["split_part"].isin(["train", "validation"])]
        b_lo, b_hi = float(fit["entry_score_binary"].min()), float(fit["entry_score_binary"].max())
        r_lo, r_hi = float(fit["entry_score_regression"].min()), float(fit["entry_score_regression"].max())
        mask = pred["split_name"].eq(split_name)
        pred.loc[mask, "_binary_trainval_norm"] = minmax_apply(pred.loc[mask, "entry_score_binary"], b_lo, b_hi)
        pred.loc[mask, "_regression_trainval_norm"] = minmax_apply(pred.loc[mask, "entry_score_regression"], r_lo, r_hi)
        rows.append({
            "split_name": split_name,
            "calibration_method": "trainval_fitted_minmax",
            "fit_parts": "train+validation",
            "binary_min": b_lo,
            "binary_max": b_hi,
            "regression_min": r_lo,
            "regression_max": r_hi,
            "uses_test_forward_whole_period_distribution": False,
        })

    pred["entry_score_ensemble_trainval"] = 0.5 * pred["_binary_trainval_norm"] + 0.5 * pred["_regression_trainval_norm"]
    pred["_binary_same_asof_norm"] = same_asof_minmax(pred, "entry_score_binary")
    pred["_regression_same_asof_norm"] = same_asof_minmax(pred, "entry_score_regression")
    pred["entry_score_ensemble_same_asof"] = 0.5 * pred["_binary_same_asof_norm"] + 0.5 * pred["_regression_same_asof_norm"]
    for split_name in sorted(pred["split_name"].unique()):
        rows.append({
            "split_name": split_name,
            "calibration_method": "same_asof_minmax",
            "fit_parts": "same asof candidates only",
            "binary_min": float("nan"),
            "binary_max": float("nan"),
            "regression_min": float("nan"),
            "regression_max": float("nan"),
            "uses_test_forward_whole_period_distribution": False,
        })
    return pred, pd.DataFrame(rows)


def metrics_for_scores(pred: pd.DataFrame, model_cols: dict[str, str]) -> pd.DataFrame:
    rows = []
    for split_name, split_df in pred.groupby("split_name"):
        for part, part_df in split_df.groupby("split_part"):
            for model, score_col in model_cols.items():
                rows.append(metric_row(part_df, split_name, part, model, score_col, include_auc=True))
    return pd.DataFrame(rows)


def gate_deltas(all_metrics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    gate_models = list(GATE_MODEL_COLS)
    metric_cols = {
        "RankIC": "rankic_delta",
        "NDCG@10": "ndcg10_delta",
        "precision@5": "precision5_delta",
        "top5_excess_return": "top5_delta",
        "top10_excess_return": "top10_delta",
    }
    gate = all_metrics[all_metrics["split_part"].isin(["test", "forward"])]
    key_cols = ["split_name", "split_part"]
    for (split_name, part), g in gate.groupby(key_cols):
        indexed = g.set_index("model")
        for model in gate_models:
            if model not in indexed.index:
                continue
            for baseline in BASELINE_MODELS:
                if baseline not in indexed.index:
                    continue
                row = {
                    "split_name": split_name,
                    "split_part": part,
                    "model": model,
                    "baseline": baseline,
                }
                for metric, out_col in metric_cols.items():
                    row[out_col] = float(indexed.loc[model, metric] - indexed.loc[baseline, metric])
                rows.append(row)
    return pd.DataFrame(rows)


def feature_groups(all_features: list[str]) -> dict[str, list[str]]:
    qlib = [
        "qlib_score_raw",
        "qlib_rank",
        "qlib_score_percentile_by_date",
        "qlib_score_zscore_by_date",
        "top10_flag",
        "top30_flag",
        "top50_flag",
        "rank_change_1d",
        "rank_change_3d",
        "rank_change_5d",
        "top30_streak",
        "top50_streak",
        "newly_entered_top30",
        "dropped_from_top30",
    ]
    technical = [
        "ma5_slope",
        "ma10_slope",
        "ma20_slope",
        "ma60_slope",
        "distance_to_ma20_pct",
        "rsi14",
        "macd_hist",
        "bollinger_position",
        "ret20",
        "volatility20",
        "volume_ratio20",
        "trend_score",
    ]
    liquidity = [
        "avg_trading_value_20d",
        "liquidity_percentile_by_date",
        "volume_stability20",
        "missing_rate20",
        "suspension_proxy",
        "slippage_proxy",
        "position_risk_status",
        "passes_liquidity_filter",
        "liquidity_penalty",
        "candidate_in_expanded_pool",
    ]
    market = [
        "twii_ret20",
        "twii_ret60",
        "twii_close_vs_ma60",
        "twii_close_vs_ma120",
        "market_volatility20",
        "market_drawdown60",
        "market_breadth_ma20",
        "market_breadth_ret20_positive",
    ]
    groups = {
        "qlib only": qlib,
        "qlib + technical": qlib + technical,
        "qlib + liquidity": qlib + liquidity,
        "qlib + market continuous": qlib + market,
        "qlib + technical + liquidity": qlib + technical + liquidity,
        "all input features": list(all_features),
    }
    available = set(all_features)
    return {name: [f for f in cols if f in available] for name, cols in groups.items()}


def train_models(train: pd.DataFrame, validation: pd.DataFrame, features: list[str]) -> tuple[lgb.LGBMClassifier, lgb.LGBMRegressor]:
    x_train = prepare_x(train, features)
    x_val = prepare_x(validation, features)
    binary = lgb.LGBMClassifier(
        objective="binary",
        n_estimators=300,
        learning_rate=0.03,
        num_leaves=31,
        min_child_samples=80,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_lambda=1.0,
        random_state=SEED,
        verbose=-1,
    )
    regression = lgb.LGBMRegressor(
        objective="regression",
        n_estimators=300,
        learning_rate=0.03,
        num_leaves=31,
        min_child_samples=80,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_lambda=1.0,
        random_state=SEED,
        verbose=-1,
    )
    binary.fit(
        x_train,
        train["entry_label_dynamic"].astype(int),
        eval_set=[(x_val, validation["entry_label_dynamic"].astype(int))],
        eval_metric="binary_logloss",
        callbacks=[lgb.early_stopping(30, verbose=False)],
    )
    regression.fit(
        x_train,
        train["entry_target_regression"],
        eval_set=[(x_val, validation["entry_target_regression"])],
        eval_metric="l2",
        callbacks=[lgb.early_stopping(30, verbose=False)],
    )
    return binary, regression


def add_baselines(out: pd.DataFrame) -> pd.DataFrame:
    out["baseline_qlib_raw"] = out["qlib_score_raw"]
    out["baseline_qlib_percentile"] = out["qlib_score_percentile_by_date"]
    out["baseline_qlib_rank"] = -out["qlib_rank"]
    out["baseline_candidate_sort"] = (
        out[["candidate_from_top50", "candidate_from_score_percentile", "candidate_from_rank_improvement", "candidate_from_trend_strength"]].astype(float).sum(axis=1)
        - out["liquidity_penalty"].fillna(0)
        + out["trend_score"].fillna(0)
    )
    return out


def run_feature_group_ablation(trainable: pd.DataFrame, groups: dict[str, list[str]]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    metrics_rows = []
    importance_rows = []
    best_rows = []
    for spec in SPLITS:
        parts = {part: trainable[split_mask(trainable, spec, part)].copy() for part in ["train", "validation", "test", "forward"]}
        for group_name, cols in groups.items():
            binary, regression = train_models(parts["train"], parts["validation"], cols)
            best_rows.append({
                "split_name": spec.name,
                "feature_group": group_name,
                "binary_best_iteration": int(binary.best_iteration_ or binary.n_estimators),
                "regression_best_iteration": int(regression.best_iteration_ or regression.n_estimators),
            })
            for model_name, model in [("binary", binary), ("regression", regression)]:
                booster = model.booster_
                for feature, gain, split_count in zip(
                    cols,
                    booster.feature_importance(importance_type="gain"),
                    booster.feature_importance(importance_type="split"),
                ):
                    importance_rows.append({
                        "split_name": spec.name,
                        "feature_group": group_name,
                        "model": model_name,
                        "feature": feature,
                        "importance_gain": float(gain),
                        "importance_split": int(split_count),
                    })
            scored_parts = []
            for part, part_df in parts.items():
                scored = part_df.copy()
                x = prepare_x(scored, cols)
                scored["entry_score_binary"] = binary.predict_proba(x)[:, 1]
                scored["entry_score_regression"] = regression.predict(x)
                scored["split_name"] = spec.name
                scored["split_part"] = part
                scored = add_baselines(scored)
                scored_parts.append(scored)
            scored_all = pd.concat(scored_parts, ignore_index=True)
            fit = scored_all[scored_all["split_part"].isin(["train", "validation"])]
            b_lo, b_hi = float(fit["entry_score_binary"].min()), float(fit["entry_score_binary"].max())
            r_lo, r_hi = float(fit["entry_score_regression"].min()), float(fit["entry_score_regression"].max())
            scored_all["entry_score_ensemble_trainval"] = 0.5 * minmax_apply(scored_all["entry_score_binary"], b_lo, b_hi) + 0.5 * minmax_apply(scored_all["entry_score_regression"], r_lo, r_hi)
            score_map = {
                "binary": "entry_score_binary",
                "regression": "entry_score_regression",
                "ensemble_fixed_trainval": "entry_score_ensemble_trainval",
            }
            for part, part_df in scored_all.groupby("split_part"):
                for model, score_col in score_map.items():
                    row = metric_row(part_df, spec.name, part, model, score_col, include_auc=True)
                    row["feature_group"] = group_name
                    row["feature_count"] = len(cols)
                    metrics_rows.append(row)
    return pd.DataFrame(metrics_rows), pd.DataFrame(importance_rows), pd.DataFrame(best_rows)


def binary_diagnostics(pred: pd.DataFrame, best_iterations: pd.DataFrame) -> pd.DataFrame:
    rows = []
    best_map = best_iterations[best_iterations["feature_group"].eq("all input features")].set_index("split_name")["binary_best_iteration"].to_dict()
    for (split_name, part), g in pred.groupby(["split_name", "split_part"]):
        y = g["entry_label_dynamic"].astype(int)
        score = g["entry_score_binary"]
        ndcg10, precision5, top5 = topk_metrics(g, "entry_score_binary", 5)
        ndcg10_metric = metric_row(g, split_name, part, "binary", "entry_score_binary", include_auc=True)["NDCG@10"]
        rows.append({
            "diagnostic_type": "score_distribution",
            "split_name": split_name,
            "split_part": part,
            "bucket": "",
            "rows": len(g),
            "best_iteration": int(best_map.get(split_name, -1)),
            "score_mean": float(score.mean()),
            "score_std": float(score.std()),
            "score_p05": float(score.quantile(0.05)),
            "score_p50": float(score.quantile(0.50)),
            "score_p95": float(score.quantile(0.95)),
            "label_positive_rate": float(y.mean()),
            "calibration_error_mean_minus_label": float(score.mean() - y.mean()),
            "auc": safe_auc(y, score),
            "logloss": safe_logloss(y, score),
            "rankic": metric_row(g, split_name, part, "binary", "entry_score_binary", include_auc=True)["RankIC"],
            "ndcg10": ndcg10_metric,
            "precision5": float(precision5),
            "top5_excess_return": float(top5),
            "summary": "binary AUC and sorting metrics are reported together to expose divergence.",
        })
        try:
            bins = pd.qcut(score, q=10, duplicates="drop")
            for bucket, bg in g.groupby(bins, observed=False):
                by = bg["entry_label_dynamic"].astype(int)
                bs = bg["entry_score_binary"]
                rows.append({
                    "diagnostic_type": "calibration_bin",
                    "split_name": split_name,
                    "split_part": part,
                    "bucket": str(bucket),
                    "rows": len(bg),
                    "best_iteration": int(best_map.get(split_name, -1)),
                    "score_mean": float(bs.mean()),
                    "score_std": float(bs.std()),
                    "score_p05": float(bs.quantile(0.05)),
                    "score_p50": float(bs.quantile(0.50)),
                    "score_p95": float(bs.quantile(0.95)),
                    "label_positive_rate": float(by.mean()),
                    "calibration_error_mean_minus_label": float(bs.mean() - by.mean()),
                    "auc": float("nan"),
                    "logloss": float("nan"),
                    "rankic": float("nan"),
                    "ndcg10": float("nan"),
                    "precision5": float("nan"),
                    "top5_excess_return": float("nan"),
                    "summary": "positive calibration error means over-estimation; negative means under-estimation.",
                })
        except Exception:
            pass
    return pd.DataFrame(rows)


def bucketize_for_regression(pred: pd.DataFrame) -> pd.DataFrame:
    out = pred.copy()
    out["month"] = out["asof"].dt.to_period("M").astype(str)
    out["qlib_rank_bucket"] = pd.cut(out["qlib_rank"], bins=[0, 10, 30, 50, 10_000], labels=["top10", "top11_30", "top31_50", "below50"], include_lowest=True).astype(str)
    out["liquidity_bucket"] = pd.qcut(out["liquidity_percentile_by_date"], q=4, labels=["low", "mid_low", "mid_high", "high"], duplicates="drop").astype(str)
    return out


def grouped_top_delta(g: pd.DataFrame, score_col: str, base_col: str) -> dict[str, float]:
    _, _, model_top5 = topk_metrics(g, score_col, 5)
    _, _, base_top5 = topk_metrics(g, base_col, 5)
    _, _, model_top10 = topk_metrics(g, score_col, 10)
    _, _, base_top10 = topk_metrics(g, base_col, 10)
    return {
        "top5_delta_vs_qlib_rank": float(model_top5 - base_top5),
        "top10_delta_vs_qlib_rank": float(model_top10 - base_top10),
    }


def regression_diagnostics(pred: pd.DataFrame, importance: pd.DataFrame) -> pd.DataFrame:
    rows = []
    data = bucketize_for_regression(pred)
    group_cols = ["year", "month", "market_regime", "qlib_rank_bucket", "liquidity_bucket", "position_risk_status"]
    target_parts = [
        ("main", "test"),
        ("main", "forward"),
        ("sensitivity", "test"),
        ("sensitivity", "forward"),
    ]
    for split_name, part in target_parts:
        part_df = data[(data["split_name"].eq(split_name)) & (data["split_part"].eq(part))]
        if part_df.empty:
            continue
        full_delta = grouped_top_delta(part_df, "entry_score_regression", "baseline_qlib_rank")
        rows.append({
            "diagnostic_type": "overall_delta",
            "split_name": split_name,
            "split_part": part,
            "group_col": "overall",
            "group_value": "all",
            "rows": len(part_df),
            "top5_delta_vs_qlib_rank": full_delta["top5_delta_vs_qlib_rank"],
            "top10_delta_vs_qlib_rank": full_delta["top10_delta_vs_qlib_rank"],
            "rankic_regression": metric_row(part_df, split_name, part, "regression", "entry_score_regression", include_auc=True)["RankIC"],
            "rankic_qlib_rank": metric_row(part_df, split_name, part, "baseline_qlib_rank", "baseline_qlib_rank", include_auc=True)["RankIC"],
            "summary": "positive top-k deltas indicate regression improves over qlib rank in this group.",
        })
        for group_col in group_cols:
            for value, g in part_df.groupby(group_col):
                if len(g) < 20 or g["asof"].nunique() < 3:
                    continue
                delta = grouped_top_delta(g, "entry_score_regression", "baseline_qlib_rank")
                rows.append({
                    "diagnostic_type": "group_delta",
                    "split_name": split_name,
                    "split_part": part,
                    "group_col": group_col,
                    "group_value": str(value),
                    "rows": len(g),
                    "top5_delta_vs_qlib_rank": delta["top5_delta_vs_qlib_rank"],
                    "top10_delta_vs_qlib_rank": delta["top10_delta_vs_qlib_rank"],
                    "rankic_regression": metric_row(g, split_name, part, "regression", "entry_score_regression", include_auc=True)["RankIC"],
                    "rankic_qlib_rank": metric_row(g, split_name, part, "baseline_qlib_rank", "baseline_qlib_rank", include_auc=True)["RankIC"],
                    "summary": "negative deltas identify concentrated degradation candidates.",
                })

    reg_imp = importance[(importance["feature_group"].eq("all input features")) & (importance["model"].eq("regression"))].copy()
    for split_name, g in reg_imp.groupby("split_name"):
        g = g.sort_values("importance_gain", ascending=False)
        total = g["importance_gain"].sum()
        for rank, (_, row) in enumerate(g.head(20).iterrows(), start=1):
            rows.append({
                "diagnostic_type": "feature_importance_top20",
                "split_name": split_name,
                "split_part": "all",
                "group_col": "feature",
                "group_value": row["feature"],
                "rows": 0,
                "top5_delta_vs_qlib_rank": float("nan"),
                "top10_delta_vs_qlib_rank": float("nan"),
                "rankic_regression": float(rank),
                "rankic_qlib_rank": float(row["importance_gain"] / total) if total else float("nan"),
                "summary": "rankic_regression column stores feature importance rank; rankic_qlib_rank stores gain share for this diagnostic row.",
            })
    if {"main", "sensitivity"}.issubset(set(reg_imp["split_name"].unique())):
        main_rank = reg_imp[reg_imp["split_name"].eq("main")].sort_values("importance_gain", ascending=False).reset_index(drop=True)
        sens_rank = reg_imp[reg_imp["split_name"].eq("sensitivity")].sort_values("importance_gain", ascending=False).reset_index(drop=True)
        main_map = {f: i + 1 for i, f in enumerate(main_rank["feature"])}
        sens_map = {f: i + 1 for i, f in enumerate(sens_rank["feature"])}
        for feature in sorted(set(main_map).intersection(sens_map)):
            if main_map[feature] <= 20 or sens_map[feature] <= 20:
                rows.append({
                    "diagnostic_type": "feature_rank_stability",
                    "split_name": "main_vs_sensitivity",
                    "split_part": "all",
                    "group_col": "feature",
                    "group_value": feature,
                    "rows": 0,
                    "top5_delta_vs_qlib_rank": float("nan"),
                    "top10_delta_vs_qlib_rank": float("nan"),
                    "rankic_regression": float(main_map[feature]),
                    "rankic_qlib_rank": float(sens_map[feature]),
                    "summary": "rankic_regression stores main importance rank; rankic_qlib_rank stores sensitivity rank.",
                })
    return pd.DataFrame(rows)


def write_reports(
    gate: pd.DataFrame,
    calibration_compare: pd.DataFrame,
    ablation: pd.DataFrame,
    binary_diag: pd.DataFrame,
    regression_diag: pd.DataFrame,
) -> None:
    gate_vs_rank = gate[gate["baseline"].eq("baseline_qlib_rank")].copy()
    gate_focus = gate_vs_rank[gate_vs_rank["model"].isin(["binary", "regression", "ensemble_original", "ensemble_fixed_trainval", "ensemble_fixed_same_asof"])]
    gate_summary = gate_focus[["split_name", "split_part", "model", "top5_delta", "top10_delta", "rankic_delta", "ndcg10_delta", "precision5_delta"]].sort_values(["split_name", "split_part", "model"])
    ablation_focus = ablation[
        (ablation["split_part"].isin(["test", "forward"]))
        & (ablation["model"].isin(["regression", "ensemble_fixed_trainval"]))
    ][["feature_group", "split_name", "split_part", "model", "RankIC", "NDCG@10", "precision@5", "top5_excess_return", "top10_excess_return"]]
    binary_dist = binary_diag[binary_diag["diagnostic_type"].eq("score_distribution")][
        ["split_name", "split_part", "best_iteration", "score_mean", "label_positive_rate", "calibration_error_mean_minus_label", "auc", "rankic", "ndcg10", "precision5"]
    ]
    regression_overall = regression_diag[regression_diag["diagnostic_type"].eq("overall_delta")][
        ["split_name", "split_part", "top5_delta_vs_qlib_rank", "top10_delta_vs_qlib_rank", "rankic_regression", "rankic_qlib_rank"]
    ]
    worst_groups = regression_diag[regression_diag["diagnostic_type"].eq("group_delta")].sort_values("top10_delta_vs_qlib_rank").head(12)[
        ["split_name", "split_part", "group_col", "group_value", "rows", "top5_delta_vs_qlib_rank", "top10_delta_vs_qlib_rank"]
    ]
    feature_stability = regression_diag[regression_diag["diagnostic_type"].eq("feature_rank_stability")].head(12)[
        ["group_value", "rankic_regression", "rankic_qlib_rank", "summary"]
    ]

    phase3_ok = False
    trainval_rank = gate_vs_rank[gate_vs_rank["model"].eq("ensemble_fixed_trainval")]
    if not trainval_rank.empty:
        required = trainval_rank[["top5_delta", "top10_delta"]].dropna()
        phase3_ok = bool((required > 0).all().all() and len(required) >= 4)

    diag_lines = [
        "# Phase 2B Entry Model v1 诊断报告",
        "",
        "## 1. 结论",
        "",
        "- 原 Phase 2 失败结论保留：不得进入 Phase 3。",
        "- Phase 2B 修复了 ensemble 评估口径：新增 `train+validation fitted minmax` 与 `same-asof minmax`，均不使用 test/forward 全区间分布。",
        f"- Phase 2B 是否建议进入 Phase 3：`{phase3_ok}`。本次未提出进入 Phase 3 建议，等待审查者复核。",
        "",
        "## 2. Gate Delta vs qlib rank",
        "",
        markdown_table(gate_summary),
        "",
        "## 3. Ensemble Calibration Compare",
        "",
        markdown_table(calibration_compare),
        "",
        "## 4. Feature Group Ablation",
        "",
        markdown_table(ablation_focus.head(72)),
        "",
        "## 5. Binary Failure Diagnosis",
        "",
        markdown_table(binary_dist),
        "",
        "## 6. Regression Robustness Diagnosis",
        "",
        "### Overall",
        "",
        markdown_table(regression_overall),
        "",
        "### Worst Concentrated Groups",
        "",
        markdown_table(worst_groups),
        "",
        "### Feature Stability",
        "",
        markdown_table(feature_stability),
        "",
        "## 7. Safety Boundary",
        "",
        "- Exit Risk Model：未训练。",
        "- LambdaRank：未训练。",
        "- 组合回放与前端：未执行。",
        "- broker/orders/quick-trade/target position：未触碰。",
        "- provider refresh/publish/accepted latest switching：未触碰。",
        "- monitor config/alerts：未触碰。",
        "- 真实交易建议语义：未生成。",
        "",
    ]
    DIAG_REPORT_PATH.write_text("\n".join(diag_lines), encoding="utf-8")

    exec_lines = [
        "# Phase 2B Entry Model 失败分析与有限修复执行报告",
        "",
        "## 1. 执行摘要",
        "",
        f"- 执行日期：`{utc_now()}`",
        "- 修改文件：新增 `scripts/diagnose_tw_decision_entry_model_phase2b.py`。",
        "- 生成文件：Phase2B gate delta、ensemble calibration compare、feature group ablation、binary diagnostics、regression diagnostics 与两份中文报告。",
        "- 是否训练 Exit Model：否。",
        "- 是否做组合回放：否。",
        "- 是否触碰只读边界：否。",
        "",
        "## 2. 原 Phase 2 Gate 复述",
        "",
        "- main test 结论：原 ensemble 相对 qlib rank 的 top5/top10 delta 为负，不通过。",
        "- main forward 结论：原 ensemble 相对 qlib rank 的 top5/top10 delta 为负，不通过。",
        "- sensitivity test 结论：原 ensemble 相对 qlib rank 的 top5/top10 delta 为负，不通过。",
        "- sensitivity forward 结论：原 ensemble 有改善但不足以抵消 test/main 失败。",
        "- 是否允许进入 Phase 3：否。",
        "",
        "## 3. Gate Delta 表",
        "",
        markdown_table(gate_summary),
        "",
        "## 4. Ensemble Calibration 修复",
        "",
        "- 原始 within split part minmax：仅作为 `ensemble_original` 保留，用于复述 Phase 2 失败，不作为修复口径。",
        "- train/validation fitted scaler：用 train+validation 的 binary/regression score min/max 拟合，并应用到 test/forward。",
        "- same-asof normalization：仅在同一 asof 候选池内归一化。",
        "- 是否使用 test/forward 分布：否，Phase2B 两个修复口径均未使用 test/forward 全区间分布。",
        "",
        "## 5. Feature Group Ablation",
        "",
        markdown_table(ablation_focus.head(72)),
        "",
        "## 6. Binary Failure Diagnosis",
        "",
        markdown_table(binary_dist),
        "",
        "## 7. Regression Robustness Diagnosis",
        "",
        "- main 改善来源：见 `phase2b_regression_diagnostics.csv` 的 overall/group delta；以 qlib rank 为基准。",
        "- sensitivity test 劣化来源：见 group_delta 中最负的 year/month/market_regime/rank/liquidity/position_risk_status 分组。",
        "- 分组失败点：",
        "",
        markdown_table(worst_groups),
        "",
        "- feature importance 稳定性：",
        "",
        markdown_table(feature_stability),
        "",
        "## 8. 安全边界",
        "",
        "- broker/orders/quick-trade：未触碰。",
        "- provider publish/refresh：未触碰。",
        "- accepted latest switching：未触碰。",
        "- monitor config/alerts：未触碰。",
        "- 真实交易建议语义：未生成。",
        "",
        "## 9. 风险与待审查问题",
        "",
        "- 必须修复：若审查者认为固定校准仍不稳，应停止 Entry Model v1 或重新定义 Phase 2C，不得自行进入 Phase 3。",
        "- 需要用户确认：进入 Phase 3、Exit Model、组合回放、前端、2024 回填或 provider 操作均需另行确认。",
        "- 可暂缓：Exit Risk Model、LambdaRank、组合回放、前端产品化、FinMind 暂缓字段、2024 数据补齐。",
        "",
        "## 10. Phase 3 准入建议",
        "",
        f"- 是否建议进入 Phase 3：`{phase3_ok}`。",
        "- 证据：Gate delta、feature group ablation、binary diagnostics 与 regression diagnostics 已写入 Phase2B 产物。",
        "- 若不建议，归档结论：Entry Model v1 继续归档为 failed/insufficient gate experiment，等待审查者意见。",
        "",
    ]
    EXEC_REPORT_PATH.write_text("\n".join(exec_lines), encoding="utf-8")


def main() -> int:
    trainable, predictions, phase2_metrics, schema, features = load_inputs()
    pred_fixed, calibration_meta = add_fixed_ensembles(predictions)
    fixed_metrics = metrics_for_scores(pred_fixed, {
        "ensemble_fixed_trainval": "entry_score_ensemble_trainval",
        "ensemble_fixed_same_asof": "entry_score_ensemble_same_asof",
    })
    phase2_subset = phase2_metrics[phase2_metrics["model"].isin(["binary", "regression", "ensemble", *BASELINE_MODELS])].copy()
    phase2_subset["model"] = phase2_subset["model"].replace({"ensemble": "ensemble_original"})
    all_metrics = pd.concat([phase2_subset, fixed_metrics], ignore_index=True)
    gate = gate_deltas(all_metrics)

    groups = feature_groups(features)
    forbidden_in_groups = sorted({f for cols in groups.values() for f in cols if f.startswith("future_") or f in {"market_regime", "candidate_reason_flags"}})
    if forbidden_in_groups:
        raise RuntimeError(f"forbidden fields in feature groups: {forbidden_in_groups}")

    ablation, ablation_importance, best_iterations = run_feature_group_ablation(trainable, groups)
    binary_diag = binary_diagnostics(pred_fixed, best_iterations)
    regression_diag = regression_diagnostics(pred_fixed, ablation_importance)

    gate.to_csv(GATE_PATH, index=False)
    calibration_meta.to_csv(CALIBRATION_COMPARE_PATH, index=False)
    ablation.to_csv(ABLATION_PATH, index=False)
    binary_diag.to_csv(BINARY_DIAG_PATH, index=False)
    regression_diag.to_csv(REGRESSION_DIAG_PATH, index=False)
    write_reports(gate, calibration_meta, ablation, binary_diag, regression_diag)

    print(json.dumps({
        "status": "ok",
        "phase2b_scope": "entry_model_diagnosis_only",
        "rows": {
            "gate_deltas": int(len(gate)),
            "calibration_compare": int(len(calibration_meta)),
            "feature_group_ablation": int(len(ablation)),
            "binary_diagnostics": int(len(binary_diag)),
            "regression_diagnostics": int(len(regression_diag)),
        },
        "outputs": [
            rel(Path("scripts/diagnose_tw_decision_entry_model_phase2b.py")),
            rel(GATE_PATH),
            rel(CALIBRATION_COMPARE_PATH),
            rel(ABLATION_PATH),
            rel(BINARY_DIAG_PATH),
            rel(REGRESSION_DIAG_PATH),
            rel(DIAG_REPORT_PATH),
            rel(EXEC_REPORT_PATH),
        ],
        "safety": {
            "exit_model": False,
            "portfolio_replay": False,
            "broker_orders_quick_trade_target_positions": False,
            "provider_refresh_publish_or_accepted_latest_switch": False,
            "monitor_config_alerts": False,
        },
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
