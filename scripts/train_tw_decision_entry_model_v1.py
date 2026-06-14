#!/usr/bin/env python3
"""Train Phase 2 Entry Model v1 for TW Decision Model research.

This script trains only Entry Model binary/regression baselines from Phase 1B
samples. It does not train Exit Risk models, run portfolio replay, refresh
providers, publish data, or touch trading state.
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
from sklearn.metrics import log_loss, roc_auc_score


ROOT = Path(__file__).resolve().parents[1]
IN_DIR = ROOT / "data_tw/experiments/decision_model"
OUT_DIR = IN_DIR / "phase2_entry_model_v1"
DOC_DIR = ROOT / "docs/tw_decision_model"
SAMPLE_PATH = IN_DIR / "phase1_samples.parquet"
SCHEMA_PATH = IN_DIR / "phase1_schema.json"
COVERAGE_PATH = IN_DIR / "phase1_date_coverage_report.csv"
SEED = 20260610


@dataclass(frozen=True)
class SplitSpec:
    name: str
    train: str
    validation: str
    test: str
    forward: str


SPLITS = [
    SplitSpec("main", "year == 2022", "year == 2023", "year == 2025", "year == 2026"),
    SplitSpec("sensitivity", "year in [2022, 2023]", "2025H1", "2025H2", "year == 2026"),
]


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
    return value


def load_inputs() -> tuple[pd.DataFrame, dict[str, Any], list[str]]:
    df = pd.read_parquet(SAMPLE_PATH)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    features = list(schema["input_features"])
    forbidden = {"market_regime", "candidate_reason_flags"}
    if forbidden.intersection(features):
        raise RuntimeError(f"forbidden fields in input_features: {sorted(forbidden.intersection(features))}")
    future_inputs = [col for col in features if col.startswith("future_")]
    if future_inputs:
        raise RuntimeError(f"future fields in input_features: {future_inputs}")
    missing = sorted(set(features + ["entry_label_dynamic", "entry_target_regression", "entry_rank_target"]) - set(df.columns))
    if missing:
        raise RuntimeError(f"missing required columns: {missing}")
    df["asof"] = pd.to_datetime(df["asof"])
    df["year"] = df["asof"].dt.year
    trainable = df[(df["is_labeled"]) & (df["candidate_in_expanded_pool"]) & (df["passes_liquidity_filter"])].copy()
    return trainable, schema, features


def split_mask(df: pd.DataFrame, split: SplitSpec, part: str) -> pd.Series:
    if split.name == "main":
        year = {"train": 2022, "validation": 2023, "test": 2025, "forward": 2026}[part]
        return df["year"].eq(year)
    if part == "train":
        return df["year"].isin([2022, 2023])
    if part == "validation":
        return df["asof"].between("2025-01-01", "2025-06-30")
    if part == "test":
        return df["asof"].between("2025-07-01", "2025-12-31")
    return df["year"].eq(2026)


def prepare_x(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    x = df[features].copy()
    for col in x.columns:
        if pd.api.types.is_bool_dtype(x[col]) or str(x[col].dtype) == "boolean":
            x[col] = x[col].astype("int8")
        elif pd.api.types.is_object_dtype(x[col]):
            x[col] = x[col].astype("category")
    return x


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


def minmax_by_split(series: pd.Series) -> pd.Series:
    lo = series.min()
    hi = series.max()
    if not math.isfinite(float(lo)) or not math.isfinite(float(hi)) or hi == lo:
        return pd.Series(0.5, index=series.index)
    return (series - lo) / (hi - lo)


def add_predictions(df: pd.DataFrame, binary: lgb.LGBMClassifier, regression: lgb.LGBMRegressor, features: list[str], split_name: str, part: str) -> pd.DataFrame:
    out = df.copy()
    x = prepare_x(out, features)
    out["entry_score_binary"] = binary.predict_proba(x)[:, 1]
    out["entry_score_regression"] = regression.predict(x)
    out["entry_score_v1"] = 0.5 * minmax_by_split(out["entry_score_binary"]) + 0.5 * minmax_by_split(out["entry_score_regression"])
    rng = np.random.default_rng(SEED)
    out["baseline_random"] = rng.random(len(out))
    out["baseline_qlib_raw"] = out["qlib_score_raw"]
    out["baseline_qlib_percentile"] = out["qlib_score_percentile_by_date"]
    out["baseline_qlib_rank"] = -out["qlib_rank"]
    out["baseline_candidate_sort"] = (
        out[["candidate_from_top50", "candidate_from_score_percentile", "candidate_from_rank_improvement", "candidate_from_trend_strength"]].astype(float).sum(axis=1)
        - out["liquidity_penalty"].fillna(0)
        + out["trend_score"].fillna(0)
    )
    out["split_name"] = split_name
    out["split_part"] = part
    return out


def safe_auc(y: pd.Series, score: pd.Series) -> float:
    if y.nunique(dropna=True) < 2:
        return float("nan")
    return float(roc_auc_score(y.astype(int), score))


def safe_logloss(y: pd.Series, score: pd.Series) -> float:
    if y.nunique(dropna=True) < 2:
        return float("nan")
    return float(log_loss(y.astype(int), np.clip(score, 1e-6, 1 - 1e-6)))


def brier(y: pd.Series, score: pd.Series) -> float:
    return float(np.mean((y.astype(float) - score.astype(float)) ** 2))


def per_date_rank_ic(df: pd.DataFrame, score_col: str) -> float:
    vals = []
    for _, g in df.groupby("asof"):
        if len(g) >= 3 and g[score_col].nunique() > 1 and g["entry_rank_target"].nunique() > 1:
            vals.append(g[score_col].rank().corr(g["entry_rank_target"].rank()))
    return float(np.nanmean(vals)) if vals else float("nan")


def ndcg_for_group(g: pd.DataFrame, score_col: str, k: int) -> float:
    top = g.sort_values(score_col, ascending=False).head(k)
    ideal = g.sort_values("entry_rank_target", ascending=False).head(k)
    min_gain = min(g["entry_rank_target"].min(), 0.0)
    gains = (top["entry_rank_target"] - min_gain).clip(lower=0).to_numpy()
    ideal_gains = (ideal["entry_rank_target"] - min_gain).clip(lower=0).to_numpy()
    discounts = 1.0 / np.log2(np.arange(2, len(gains) + 2))
    dcg = float((gains * discounts).sum())
    idcg = float((ideal_gains * discounts[: len(ideal_gains)]).sum())
    return dcg / idcg if idcg > 0 else float("nan")


def topk_metrics(df: pd.DataFrame, score_col: str, k: int) -> tuple[float, float, float]:
    ndcgs = []
    precisions = []
    returns = []
    for _, g in df.groupby("asof"):
        if len(g) < k:
            continue
        top = g.sort_values(score_col, ascending=False).head(k)
        ndcgs.append(ndcg_for_group(g, score_col, k))
        precisions.append(float(top["entry_label_dynamic"].astype(int).mean()))
        returns.append(float(top["future_20d_excess_return_after_fee"].mean()))
    return (
        float(np.nanmean(ndcgs)) if ndcgs else float("nan"),
        float(np.nanmean(precisions)) if precisions else float("nan"),
        float(np.nanmean(returns)) if returns else float("nan"),
    )


def metric_row(df: pd.DataFrame, split_name: str, part: str, model: str, score_col: str, include_auc: bool = True) -> dict[str, Any]:
    ndcg5, precision5, top5_ret = topk_metrics(df, score_col, 5)
    ndcg10, _, top10_ret = topk_metrics(df, score_col, 10)
    return {
        "split_name": split_name,
        "split_part": part,
        "model": model,
        "rows": len(df),
        "AUC": safe_auc(df["entry_label_dynamic"], df[score_col]) if include_auc else float("nan"),
        "logloss": safe_logloss(df["entry_label_dynamic"], df[score_col]) if include_auc and df[score_col].between(0, 1).all() else float("nan"),
        "brier": brier(df["entry_label_dynamic"], df[score_col]) if include_auc and df[score_col].between(0, 1).all() else float("nan"),
        "regression_ic": float(df[score_col].corr(df["entry_target_regression"])) if df[score_col].nunique() > 1 else float("nan"),
        "RankIC": per_date_rank_ic(df, score_col),
        "NDCG@5": ndcg5,
        "NDCG@10": ndcg10,
        "precision@5": precision5,
        "top5_excess_return": top5_ret,
        "top10_excess_return": top10_ret,
    }


def split_summary(df: pd.DataFrame, split_name: str, part: str) -> dict[str, Any]:
    return {
        "split_name": split_name,
        "split_part": part,
        "rows": int(len(df)),
        "candidate_rows": int(len(df)),
        "positive_rate": float(df["entry_label_dynamic"].astype(int).mean()) if len(df) else float("nan"),
        "target_mean": float(df["entry_target_regression"].mean()) if len(df) else float("nan"),
        "target_std": float(df["entry_target_regression"].std()) if len(df) else float("nan"),
        "unique_dates": int(df["asof"].nunique()),
        "unique_symbols": int(df["symbol"].nunique()),
    }


def make_bucket(series: pd.Series, labels: list[str]) -> pd.Series:
    try:
        return pd.qcut(series, q=len(labels), labels=labels, duplicates="drop").astype(str)
    except Exception:
        return pd.Series("unknown", index=series.index)


def group_metrics(pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    data = pred.copy()
    data["qlib_rank_bucket"] = pd.cut(data["qlib_rank"], bins=[0, 10, 30, 50, 10_000], labels=["top10", "top11_30", "top31_50", "below50"], include_lowest=True).astype(str)
    data["liquidity_bucket"] = make_bucket(data["liquidity_percentile_by_date"], ["low", "mid_low", "mid_high", "high"])
    group_cols = ["year", "market_regime", "qlib_rank_bucket", "liquidity_bucket", "position_risk_status"]
    for split_name, split_df in data.groupby("split_name"):
        for part, part_df in split_df.groupby("split_part"):
            for group_col in group_cols:
                for value, g in part_df.groupby(group_col):
                    if len(g) < 20:
                        continue
                    row = metric_row(g, split_name, part, f"ensemble_by_{group_col}", "entry_score_v1", include_auc=True)
                    row["group_col"] = group_col
                    row["group_value"] = value
                    rows.append(row)
    return pd.DataFrame(rows)


def calibration(pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split_name, split_df in pred.groupby("split_name"):
        for part, part_df in split_df.groupby("split_part"):
            bins = pd.qcut(part_df["entry_score_binary"], q=10, duplicates="drop")
            for bucket, g in part_df.groupby(bins, observed=False):
                rows.append({
                    "split_name": split_name,
                    "split_part": part,
                    "score_bucket": str(bucket),
                    "rows": len(g),
                    "mean_score_binary": float(g["entry_score_binary"].mean()),
                    "positive_rate": float(g["entry_label_dynamic"].astype(int).mean()),
                    "mean_score_regression": float(g["entry_score_regression"].mean()),
                    "target_mean": float(g["entry_target_regression"].mean()),
                })
    return pd.DataFrame(rows)



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

def write_reports(metrics: pd.DataFrame, split_summary_df: pd.DataFrame, importance: pd.DataFrame, group_df: pd.DataFrame, calibration_df: pd.DataFrame, schema: dict[str, Any], predictions: pd.DataFrame) -> None:
    top_imp = importance.sort_values("importance_gain", ascending=False).head(15)
    forbidden = [c for c in schema["input_features"] if c.startswith("future_") or c in {"market_regime", "candidate_reason_flags"} or "revenue" in c.lower() or "valuation" in c.lower()]
    main = metrics[(metrics["split_name"] == "main") & (metrics["split_part"].isin(["test", "forward"]))]
    baseline_cmp = main[main["model"].isin(["ensemble", "baseline_qlib_rank", "baseline_qlib_percentile"])]
    lines = [
        "# Phase 2 Entry Model v1 Report",
        "",
        "## Summary",
        "",
        "- Scope: Entry Model v1 only; binary and regression LightGBM baselines plus equal-weight normalized ensemble.",
        "- No Exit Risk Model, no portfolio replay, no frontend integration, no real trading action.",
        "- 2024 is unavailable in Phase 1B artifacts and is not used.",
        "",
        "## Main Test/Forward Comparison",
        "",
        markdown_table(baseline_cmp[["split_part", "model", "RankIC", "NDCG@10", "precision@5", "top5_excess_return", "top10_excess_return"]]),
        "",
        "## Top Feature Importance",
        "",
        markdown_table(top_imp[["split_name", "model", "feature", "importance_gain", "importance_split"]]),
        "",
        "## Forbidden Feature Check",
        "",
        f"- forbidden_or_future_inputs: `{forbidden}`",
        "",
        "## Phase 3 Gate",
        "",
        "Phase 2 gate result: the main split ensemble underperforms qlib rank/percentile on test and forward TopK excess return. Sensitivity forward improves, but sensitivity test still underperforms qlib. Executor recommendation: do not enter Phase 3 directly; submit as a failed/insufficient Entry Model v1 experiment for reviewer decision.",
        "",
    ]
    (DOC_DIR / "PHASE2_ENTRY_MODEL_REPORT_CN.md").write_text("\n".join(lines), encoding="utf-8")

    exec_lines = [
        "# Phase 2 Entry Model v1 执行报告",
        "",
        "## 1. 执行摘要",
        "",
        f"- 执行日期：`{utc_now()}`",
        "- 修改文件：新增 `scripts/train_tw_decision_entry_model_v1.py`。",
        "- 生成文件：Phase 2 model、prediction、metrics、split、importance、calibration、group metrics 与报告。",
        "- 是否只训练 Entry Model：是。",
        "- 是否触碰只读边界：否。未触发 broker/orders/quick-trade/target position/provider refresh/provider publish/accepted latest/monitor config/alerts。",
        "",
        "## 2. 输入与 Schema",
        "",
        f"- samples path：`{rel(SAMPLE_PATH)}`",
        f"- schema path：`{rel(SCHEMA_PATH)}`",
        f"- input_features count：`{len(schema['input_features'])}`",
        "- label target：`entry_label_dynamic` / `entry_target_regression` / `entry_rank_target`",
        f"- market_regime 是否输入：`{'market_regime' in schema['input_features']}`",
        f"- candidate_reason_flags 是否输入：`{'candidate_reason_flags' in schema['input_features']}`",
        "- FinMind 暂缓字段是否输入：`False`",
        "",
        "## 3. 时间切分",
        "",
        "| split_name | train | validation | test | forward | notes |",
        "|---|---|---|---|---|---|",
        "| main | 2022 | 2023 | 2025 | 2026 labeled | 2024 unavailable |",
        "| sensitivity | 2022+2023 | 2025H1 | 2025H2 | 2026 labeled | no test/forward tuning |",
        "",
        "## 4. Split Coverage",
        "",
        markdown_table(split_summary_df),
        "",
        "## 5. 模型与参数",
        "",
        "- binary model：LightGBM objective=binary, fixed params, validation early stopping only。",
        "- regression model：LightGBM objective=regression, fixed params, validation early stopping only。",
        "- ensemble rule：minmax(binary)*0.5 + minmax(regression)*0.5 within split part。",
        f"- fixed random seed：`{SEED}`",
        "- 是否在 test/forward 调参：否。",
        "",
        "## 6. Metrics",
        "",
        markdown_table(metrics[metrics["model"].isin(["binary", "regression", "ensemble"])]),
        "",
        "## 7. Baseline 对比",
        "",
        markdown_table(metrics[metrics["model"].str.startswith("baseline_")]),
        "",
        "## 8. 分组评估",
        "",
        "- by year / market_regime / qlib rank bucket / liquidity bucket / position_risk_status：详见 `phase2_group_metrics.csv`。",
        "",
        "## 9. Feature Importance",
        "",
        markdown_table(top_imp[["split_name", "model", "feature", "importance_gain", "importance_split"]]),
        f"- 是否有 forbidden/future/deferred 字段：`{forbidden}`",
        "- 是否过度依赖单一特征：待审查者结合 importance 分布判断。",
        "",
        "## 10. Calibration",
        "",
        "- binary calibration：详见 `phase2_calibration.csv`。",
        "- regression score distribution：详见 `phase2_predictions.parquet`。",
        "- score drift by split：详见 predictions 与 calibration。",
        "",
        "## 11. 安全边界",
        "",
        "- broker/orders/quick-trade：未触碰。",
        "- provider publish/refresh：未触碰。",
        "- accepted latest switching：未触碰。",
        "- monitor config/alerts：未触碰。",
        "- 真实交易建议语义：未生成。",
        "",
        "## 12. 风险与待审查问题",
        "",
        "- 必须修复：暂无执行者自行认定的必须修复项，待审查者复核。",
        "- 需要用户确认：暂无。",
        "- 可暂缓：Exit Risk Model、LambdaRank、组合回放、前端产品化、FinMind 暂缓字段。",
        "",
        "## 13. Phase 3 准入建议",
        "",
        "- 是否建议进入 Phase 3：不建议直接进入。主切分 test/forward 未优于 qlib rank/percentile baseline；敏感性切分 forward 改善但 test 仍劣化，未满足第 12 条稳健准入要求。",
        "- 若审查者仍考虑放行，限制条件：需先解释 main split 劣化原因，并保持 research-only；不得接组合回放或前端。",
        "",
    ]
    (DOC_DIR / "PHASE2_EXECUTION_REPORT_CN.md").write_text("\n".join(exec_lines), encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df, schema, features = load_inputs()
    all_predictions = []
    all_metrics = []
    all_summaries = []
    all_importance = []
    saved_main = False
    for spec in SPLITS:
        parts = {part: df[split_mask(df, spec, part)].copy() for part in ["train", "validation", "test", "forward"]}
        if any(len(parts[p]) < 100 for p in parts):
            raise RuntimeError(f"split {spec.name} has too few rows: { {k: len(v) for k, v in parts.items()} }")
        binary, regression = train_models(parts["train"], parts["validation"], features)
        if spec.name == "main" and not saved_main:
            binary.booster_.save_model(str(OUT_DIR / "entry_model_binary.txt"))
            regression.booster_.save_model(str(OUT_DIR / "entry_model_regression.txt"))
            saved_main = True
        for model_name, model in [("binary", binary), ("regression", regression)]:
            booster = model.booster_
            gain = booster.feature_importance(importance_type="gain")
            split = booster.feature_importance(importance_type="split")
            for feature, gain_value, split_value in zip(features, gain, split):
                all_importance.append({
                    "split_name": spec.name,
                    "model": model_name,
                    "feature": feature,
                    "importance_gain": float(gain_value),
                    "importance_split": int(split_value),
                })
        for part, part_df in parts.items():
            all_summaries.append(split_summary(part_df, spec.name, part))
            pred = add_predictions(part_df, binary, regression, features, spec.name, part)
            all_predictions.append(pred)
            score_map = {
                "binary": "entry_score_binary",
                "regression": "entry_score_regression",
                "ensemble": "entry_score_v1",
                "baseline_qlib_raw": "baseline_qlib_raw",
                "baseline_qlib_percentile": "baseline_qlib_percentile",
                "baseline_qlib_rank": "baseline_qlib_rank",
                "baseline_candidate_sort": "baseline_candidate_sort",
                "baseline_random": "baseline_random",
            }
            for model, score_col in score_map.items():
                all_metrics.append(metric_row(pred, spec.name, part, model, score_col, include_auc=True))
    predictions = pd.concat(all_predictions, ignore_index=True)
    metrics = pd.DataFrame(all_metrics)
    split_summary_df = pd.DataFrame(all_summaries)
    importance = pd.DataFrame(all_importance)
    calibration_df = calibration(predictions)
    group_df = group_metrics(predictions)
    predictions.to_parquet(OUT_DIR / "phase2_predictions.parquet", index=False)
    metrics.to_csv(OUT_DIR / "phase2_metrics.csv", index=False)
    split_summary_df.to_csv(OUT_DIR / "phase2_split_summary.csv", index=False)
    importance.to_csv(OUT_DIR / "phase2_feature_importance.csv", index=False)
    calibration_df.to_csv(OUT_DIR / "phase2_calibration.csv", index=False)
    group_df.to_csv(OUT_DIR / "phase2_group_metrics.csv", index=False)
    write_reports(metrics, split_summary_df, importance, group_df, calibration_df, schema, predictions)
    print(json.dumps({
        "status": "ok",
        "rows": int(len(predictions)),
        "outputs": [
            rel(OUT_DIR / "entry_model_binary.txt"),
            rel(OUT_DIR / "entry_model_regression.txt"),
            rel(OUT_DIR / "phase2_predictions.parquet"),
            rel(OUT_DIR / "phase2_metrics.csv"),
            rel(OUT_DIR / "phase2_split_summary.csv"),
            rel(OUT_DIR / "phase2_feature_importance.csv"),
            rel(OUT_DIR / "phase2_calibration.csv"),
            rel(OUT_DIR / "phase2_group_metrics.csv"),
            rel(DOC_DIR / "PHASE2_ENTRY_MODEL_REPORT_CN.md"),
            rel(DOC_DIR / "PHASE2_EXECUTION_REPORT_CN.md"),
        ],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
