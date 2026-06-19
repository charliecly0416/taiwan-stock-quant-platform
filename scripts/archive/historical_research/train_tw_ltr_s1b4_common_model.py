#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import ndcg_score


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples"
POLICY_DIR = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b3_training_policy"
OUT_DIR = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b4_ltr_training"
DOC_DIR = ROOT / "docs/tw_ltr_qlib_split_aligned_retrain"

SAMPLE_CSV = SAMPLE_DIR / "phase_s1b2_ltr_samples.csv"
SCHEMA_JSON = SAMPLE_DIR / "phase_s1b2_sample_schema.json"
FEATURE_LIST_JSON = SAMPLE_DIR / "phase_s1b2_feature_list.json"
POLICY_JSON = POLICY_DIR / "phase_s1b3_training_policy.json"
FEATURE_LABEL_CONTRACT_JSON = POLICY_DIR / "phase_s1b3_feature_label_contract.json"
SPLIT_USAGE_CONTRACT_JSON = POLICY_DIR / "phase_s1b3_split_usage_contract.json"

MODEL_PKL = OUT_DIR / "phase_s1b4_ltr_model.pkl"
SCORES_CSV = OUT_DIR / "phase_s1b4_ltr_scores.csv"
SCORE_SCHEMA_JSON = OUT_DIR / "phase_s1b4_ltr_score_schema.json"
TRAINING_DIAGNOSTICS_JSON = OUT_DIR / "phase_s1b4_training_diagnostics.json"
METRIC_BY_SPLIT_CSV = OUT_DIR / "phase_s1b4_metric_by_split.csv"
FEATURE_IMPORTANCE_CSV = OUT_DIR / "phase_s1b4_feature_importance.csv"
LEAKAGE_AUDIT_JSON = OUT_DIR / "phase_s1b4_leakage_boundary_audit.json"
GATE_SUMMARY_JSON = OUT_DIR / "phase_s1b4_gate_summary.json"
REPORT_DOC = DOC_DIR / "PHASES1B4_LTR_TRAINING_EXECUTION_REPORT_CN.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_sample(schema: dict[str, Any], feature_contract: dict[str, Any]) -> tuple[pd.DataFrame, list[str]]:
    df = pd.read_csv(SAMPLE_CSV, parse_dates=["date"])
    require("sample_complete" in df.columns, "sample_complete column missing from S1B2 sample")
    df = df[df["sample_complete"] == True].copy()  # noqa: E712
    feature_cols = feature_contract["feature_columns"]
    require(feature_cols == schema["input_columns"], "feature contract and sample schema input_columns mismatch")
    missing_cols = [col for col in feature_cols if col not in df.columns]
    require(not missing_cols, f"sample missing required feature columns: {missing_cols}")
    require("ltr_relevance_label" in df.columns, "ltr_relevance_label missing from S1B2 sample")
    df["ltr_relevance_label"] = pd.to_numeric(df["ltr_relevance_label"], errors="coerce").fillna(0).astype(int)
    df[feature_cols] = df[feature_cols].replace([np.inf, -np.inf], np.nan)
    train_mask = df["split"] == "train_scored"
    medians = df.loc[train_mask, feature_cols].median(numeric_only=True).fillna(0.0)
    df[feature_cols] = df[feature_cols].fillna(medians).fillna(0.0)
    return df, feature_cols


def group_sizes(df: pd.DataFrame) -> list[int]:
    return df.sort_values(["date", "instrument"]).groupby("date").size().astype(int).tolist()


def train_model(df: pd.DataFrame, policy: dict[str, Any], feature_cols: list[str]) -> lgb.LGBMRanker:
    params = policy["frozen_training_spec"]["parameters"]
    fit_policy = policy["frozen_training_spec"]["fit_policy"]
    require(fit_policy["early_stopping_enabled"] is False, "policy violation: early stopping must remain disabled")
    require(fit_policy["parameter_search"] is False, "policy violation: parameter search must remain disabled")
    train = df[df["split"] == "train_scored"].sort_values(["date", "instrument"])
    valid = df[df["split"] == "validation"].sort_values(["date", "instrument"])
    require(not train.empty, "train_scored split is empty after sample_complete filter")
    require(not valid.empty, "validation split is empty after sample_complete filter")
    model = lgb.LGBMRanker(
        objective=policy["frozen_training_spec"]["objective"],
        metric=policy["frozen_training_spec"]["metric"],
        boosting_type=policy["frozen_training_spec"]["boosting_type"],
        n_estimators=params["n_estimators"],
        learning_rate=params["learning_rate"],
        num_leaves=params["num_leaves"],
        min_child_samples=params["min_child_samples"],
        random_state=params["random_state"],
        n_jobs=params["n_jobs"],
        verbose=params["verbose"],
    )
    model.fit(
        train[feature_cols],
        train[policy["frozen_training_spec"]["label_column"]],
        group=group_sizes(train),
        eval_set=[(valid[feature_cols], valid[policy["frozen_training_spec"]["label_column"]])],
        eval_group=[group_sizes(valid)],
        eval_at=fit_policy["eval_at"],
    )
    return model


def add_scores(df: pd.DataFrame, model: lgb.LGBMRanker) -> pd.DataFrame:
    out = df.copy()
    out["ltr_score"] = model.predict(out[FEATURE_CONTRACT["feature_columns"]])
    out = out.sort_values(["date", "ltr_score", "instrument"], ascending=[True, False, True]).copy()
    out["ltr_rank"] = out.groupby("date")["ltr_score"].rank(ascending=False, method="first").astype(int)
    return out


def mean_spearman_by_date(df: pd.DataFrame, score_col: str, label_col: str) -> tuple[float, int]:
    values: list[float] = []
    for _, group in df.groupby("date"):
        if group[score_col].nunique() < 2 or group[label_col].nunique() < 2:
            continue
        corr = spearmanr(group[score_col], group[label_col]).correlation
        if pd.notna(corr):
            values.append(float(corr))
    return (float(np.mean(values)), len(values)) if values else (0.0, 0)


def mean_ndcg_by_date(df: pd.DataFrame, score_col: str, label_col: str, k: int) -> float:
    values: list[float] = []
    for _, group in df.groupby("date"):
        if group.shape[0] < 2:
            continue
        y_true = group[label_col].to_numpy(dtype=float).reshape(1, -1)
        y_score = group[score_col].to_numpy(dtype=float).reshape(1, -1)
        try:
            values.append(float(ndcg_score(y_true, y_score, k=min(k, group.shape[0]))))
        except Exception:
            continue
    return float(np.mean(values)) if values else 0.0


def topk_label_mean(df: pd.DataFrame, score_col: str, label_col: str, k: int) -> float:
    selected = []
    for _, group in df.groupby("date"):
        selected.append(group.nlargest(min(k, group.shape[0]), score_col))
    top = pd.concat(selected, ignore_index=True) if selected else pd.DataFrame()
    return float(top[label_col].mean()) if not top.empty else 0.0


def metrics_by_split(df: pd.DataFrame, model: lgb.LGBMRanker) -> pd.DataFrame:
    evals_result = getattr(model, "evals_result_", {})
    valid_eval = evals_result.get("valid_0", {})
    rows: list[dict[str, Any]] = []
    for split in ["train_scored", "validation", "test"]:
        sub = df[df["split"] == split].copy()
        rank_ic, rank_ic_dates = mean_spearman_by_date(sub, "ltr_score", "future_excess_return_rank_10d")
        row = {
            "split": split,
            "row_count": int(sub.shape[0]),
            "date_count": int(sub["date"].nunique()),
            "feature_count": len(FEATURE_CONTRACT["feature_columns"]),
            "label_mean": float(sub["ltr_relevance_label"].mean()),
            "ltr_score_missing_count": int(sub["ltr_score"].isna().sum()),
            "ltr_rank_missing_count": int(sub["ltr_rank"].isna().sum()),
            "duplicate_date_instrument_count": int(sub.duplicated(["date", "instrument"]).sum()),
            "ndcg_at_10": mean_ndcg_by_date(sub, "ltr_score", "ltr_relevance_label", 10),
            "ndcg_at_30": mean_ndcg_by_date(sub, "ltr_score", "ltr_relevance_label", 30),
            "ndcg_at_50": mean_ndcg_by_date(sub, "ltr_score", "ltr_relevance_label", 50),
            "rank_ic_audit_future_excess_rank_10d": rank_ic,
            "rank_ic_audit_date_count": int(rank_ic_dates),
            "top10_label_mean": topk_label_mean(sub, "ltr_score", "ltr_relevance_label", 10),
            "top30_label_mean": topk_label_mean(sub, "ltr_score", "ltr_relevance_label", 30),
            "top50_label_mean": topk_label_mean(sub, "ltr_score", "ltr_relevance_label", 50),
            "eval_metric_source": "validation_only_for_training_fit" if split == "validation" else "post_fit_one_pass_diagnostic",
            "lightgbm_valid_ndcg_last_at_10": float(valid_eval.get("ndcg@10", [np.nan])[-1]) if valid_eval.get("ndcg@10") else np.nan,
            "lightgbm_valid_ndcg_last_at_30": float(valid_eval.get("ndcg@30", [np.nan])[-1]) if valid_eval.get("ndcg@30") else np.nan,
            "lightgbm_valid_ndcg_last_at_50": float(valid_eval.get("ndcg@50", [np.nan])[-1]) if valid_eval.get("ndcg@50") else np.nan,
        }
        rows.append(row)
    return pd.DataFrame(rows)


def feature_importance(model: lgb.LGBMRanker) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "feature": FEATURE_CONTRACT["feature_columns"],
            "importance_gain": model.booster_.feature_importance(importance_type="gain"),
            "importance_split": model.booster_.feature_importance(importance_type="split"),
        }
    ).sort_values(["importance_gain", "importance_split", "feature"], ascending=[False, False, True])


def write_score_schema(df: pd.DataFrame) -> None:
    payload = {
        "created_at": utc_now(),
        "phase": "phase_s1b4_ltr_training",
        "artifact": rel(SCORES_CSV),
        "source_sample": rel(SAMPLE_CSV),
        "source_policy": rel(POLICY_JSON),
        "common_model_only": True,
        "candidate_mapping": {
            "split_aligned_ltr_simple": "common_ltr_score_direct_usage_candidate_only",
            "split_aligned_ltr_turnover_controlled": "same_common_ltr_score_plus_later_usage_constraint_candidate_only",
        },
        "columns": {
            "identity": ["date", "instrument", "split", "fold_id"],
            "base_score_inputs": ["qlib_score_raw", "qlib_rank"],
            "ltr_outputs": ["ltr_score", "ltr_rank"],
            "audit_only": [
                "regime_segment",
                "sample_complete",
                "feature_complete",
                "label_complete_10d",
                "future_excess_return_rank_10d",
                "topk_forward_bucket",
                "ltr_relevance_label",
            ],
        },
        "row_count": int(df.shape[0]),
        "duplicate_date_instrument_count": int(df.duplicated(["date", "instrument"]).sum()),
        "ltr_score_missing_count": int(df["ltr_score"].isna().sum()),
        "ltr_rank_missing_count": int(df["ltr_rank"].isna().sum()),
    }
    SCORE_SCHEMA_JSON.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def write_training_diagnostics(df: pd.DataFrame, model: lgb.LGBMRanker, metrics: pd.DataFrame) -> None:
    booster = model.booster_
    payload = {
        "created_at": utc_now(),
        "phase": "phase_s1b4_ltr_training",
        "training_policy_source": rel(POLICY_JSON),
        "model_family": "LightGBM.LGBMRanker",
        "objective": POLICY["frozen_training_spec"]["objective"],
        "group_key": POLICY["frozen_training_spec"]["group_key"],
        "label_column": POLICY["frozen_training_spec"]["label_column"],
        "feature_count": len(FEATURE_CONTRACT["feature_columns"]),
        "split_row_count": metrics.set_index("split")["row_count"].to_dict(),
        "split_date_count": metrics.set_index("split")["date_count"].to_dict(),
        "booster_best_iteration": int(getattr(booster, "current_iteration", lambda: 0)()),
        "evals_result": getattr(model, "evals_result_", {}),
        "model_params": POLICY["frozen_training_spec"]["parameters"],
        "sample_complete_filter": POLICY["input_contract"]["sample_filter"],
        "common_model_only": True,
        "turnover_control_not_implemented_in_s1b4": True,
    }
    TRAINING_DIAGNOSTICS_JSON.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def write_leakage_audit(df: pd.DataFrame) -> None:
    payload = {
        "created_at": utc_now(),
        "phase": "phase_s1b4_ltr_training",
        "input_sample": rel(SAMPLE_CSV),
        "input_policy": rel(POLICY_JSON),
        "sample_complete_only": bool(df["sample_complete"].all()),
        "feature_source_frozen": True,
        "label_source_column": FEATURE_CONTRACT["training_label_column"],
        "label_bucket_policy": FEATURE_CONTRACT["training_label_policy"]["bucket_policy"],
        "label_bucket_thresholds": FEATURE_CONTRACT["training_label_policy"]["bucket_thresholds"],
        "label_bucket_fit_on_validation_or_test": FEATURE_CONTRACT["training_label_policy"]["fit_on_validation_or_test"],
        "test_feedback_used_for_training": False,
        "parameter_search": False,
        "early_stopping_enabled": False,
        "common_model_only": True,
        "turnover_controlled_as_later_usage_layer_only": True,
        "forbidden_training_inputs": FEATURE_CONTRACT["forbidden_training_inputs"],
        "no_replay": True,
        "no_strategy_return_comparison": True,
        "no_provider_refresh_publish": True,
        "no_accepted_latest_switching": True,
        "no_monitor_or_trading_chain": True,
    }
    LEAKAGE_AUDIT_JSON.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def decide_gate(metrics: pd.DataFrame, scores: pd.DataFrame) -> tuple[str, str]:
    duplicates = int(scores.duplicated(["date", "instrument"]).sum())
    score_missing = int(scores["ltr_score"].isna().sum())
    rank_missing = int(scores["ltr_rank"].isna().sum())
    if duplicates != 0 or score_missing != 0 or rank_missing != 0:
        return (
            "s1b4_blocked_by_data_integrity_issue",
            f"duplicate={duplicates}, ltr_score_missing={score_missing}, ltr_rank_missing={rank_missing}",
        )
    return (
        "s1b4_ltr_training_pass_request_s1b5_score_diagnostics_and_replay_policy",
        "Common split-aligned LTR model trained once under frozen S1B3 policy and produced complete score/rank artifacts without replay or parameter search.",
    )


def write_gate_summary(metrics: pd.DataFrame, scores: pd.DataFrame) -> dict[str, Any]:
    gate, reason = decide_gate(metrics, scores)
    payload = {
        "created_at": utc_now(),
        "phase": "phase_s1b4_ltr_training",
        "recommended_gate": gate,
        "gate_reason": reason,
        "checks": {
            "used_s1b3_frozen_parameters": True,
            "used_sample_complete_true": bool(scores["sample_complete"].all()),
            "common_model_only": True,
            "no_parameter_search": True,
            "no_early_stopping": True,
            "duplicate_date_instrument_count": int(scores.duplicated(["date", "instrument"]).sum()),
            "ltr_score_missing_count": int(scores["ltr_score"].isna().sum()),
            "ltr_rank_missing_count": int(scores["ltr_rank"].isna().sum()),
            "no_replay": True,
            "no_strategy_return_comparison": True,
            "no_frontend_or_api": True,
            "no_provider_refresh_publish": True,
            "no_accepted_latest_switching": True,
            "no_monitor_or_trading_chain": True,
            "no_real_trading_semantics": True,
        },
        "artifacts": {
            "model": rel(MODEL_PKL),
            "scores": rel(SCORES_CSV),
            "score_schema": rel(SCORE_SCHEMA_JSON),
            "training_diagnostics": rel(TRAINING_DIAGNOSTICS_JSON),
            "metric_by_split": rel(METRIC_BY_SPLIT_CSV),
            "feature_importance": rel(FEATURE_IMPORTANCE_CSV),
            "leakage_boundary_audit": rel(LEAKAGE_AUDIT_JSON),
            "report": rel(REPORT_DOC),
        },
    }
    GATE_SUMMARY_JSON.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return payload


def write_report(metrics: pd.DataFrame, gate: dict[str, Any]) -> None:
    metric_rows = []
    for _, row in metrics.iterrows():
        metric_rows.append(
            f"| {row['split']} | {int(row['row_count'])} | {int(row['date_count'])} | "
            f"{row['ndcg_at_10']:.6f} | {row['ndcg_at_30']:.6f} | {row['ndcg_at_50']:.6f} | "
            f"{row['rank_ic_audit_future_excess_rank_10d']:.6f} | {row['top10_label_mean']:.6f} | "
            f"{row['top30_label_mean']:.6f} | {row['top50_label_mean']:.6f} |"
        )
    feature_head = pd.read_csv(FEATURE_IMPORTANCE_CSV).head(10)
    feature_rows = [
        f"| {r.feature} | {float(r.importance_gain):.6f} | {int(r.importance_split)} |"
        for r in feature_head.itertuples(index=False)
    ]
    report = "\n".join(
        [
            "# Phase S1B4 执行报告：Split-Aligned LTR Training",
            "",
            f"生成日期：{utc_now()}",
            "",
            "## 1. 本轮目标",
            "",
            "按 `PHASES1B3_REVIEW_AND_PHASES1B4_TRAINING_WORK_CN.md` 要求，严格复用 S1B3 冻结政策训练一个 common split-aligned LTR model，并输出一次性 score/rank 与训练诊断。",
            "",
            "## 2. 执行范围",
            "",
            "- 使用唯一 S1B2R 样本、schema、feature list 和 S1B3 policy。",
            "- 训练前过滤 `sample_complete == true`。",
            "- 只训练一个 common `LightGBM.LGBMRanker objective=lambdarank` 模型。",
            "- 输出 train_scored / validation / test 的一次性 LTR score/rank、metric、feature importance、边界审计。",
            "",
            "## 3. 固定输入与参数",
            "",
            f"- sample: `{rel(SAMPLE_CSV)}`",
            f"- schema: `{rel(SCHEMA_JSON)}`",
            f"- feature list: `{rel(FEATURE_LIST_JSON)}`",
            f"- policy: `{rel(POLICY_JSON)}`",
            "- 过滤：`sample_complete == true`",
            "- 参数：`n_estimators=120, learning_rate=0.05, num_leaves=31, min_child_samples=20, random_state=42, n_jobs=2`",
            "- `early_stopping_enabled = false`",
            "- `parameter_search = false`",
            "",
            "## 4. Split 训练边界",
            "",
            "- `train_scored`：拟合。",
            "- `validation`：固定训练诊断。",
            "- `test`：一次性 holdout score/evaluation only，不回馈训练。",
            "- `split_aligned_ltr_simple` 与 `split_aligned_ltr_turnover_controlled` 共用同一训练分数；本轮未实现 turnover-control 使用层规则。",
            "",
            "## 5. Metric By Split",
            "",
            "| split | row_count | date_count | ndcg@10 | ndcg@30 | ndcg@50 | rank_ic_audit | top10_label_mean | top30_label_mean | top50_label_mean |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            *metric_rows,
            "",
            "## 6. Top Feature Importance",
            "",
            "| feature | importance_gain | importance_split |",
            "| --- | ---: | ---: |",
            *feature_rows,
            "",
            "## 7. 产物",
            "",
            f"- `{rel(MODEL_PKL)}`",
            f"- `{rel(SCORES_CSV)}`",
            f"- `{rel(SCORE_SCHEMA_JSON)}`",
            f"- `{rel(TRAINING_DIAGNOSTICS_JSON)}`",
            f"- `{rel(METRIC_BY_SPLIT_CSV)}`",
            f"- `{rel(FEATURE_IMPORTANCE_CSV)}`",
            f"- `{rel(LEAKAGE_AUDIT_JSON)}`",
            f"- `{rel(GATE_SUMMARY_JSON)}`",
            "",
            "## 8. 只读边界与禁止事项",
            "",
            "- 未训练 qlib。",
            "- 未跑组合回放。",
            "- 未比较策略收益、回撤、换手、动作次数。",
            "- 未调参，未改 feature / label / split / universe。",
            "- 未实现 turnover-controlled 使用层约束。",
            "- 未联网，未新增数据源。",
            "- 未改前端/API。",
            "- 未触发 provider refresh / publish、accepted latest switching、monitor 或交易链路。",
            "- 未输出买卖、持有、仓位、target position、target weight、收益承诺、胜率或上涨概率语义。",
            "",
            "## 9. 结论",
            "",
            "本轮完成 S1B4 授权范围内的一次性 LTR 训练与分 split score/rank 物化。",
            "",
            "推荐 gate：",
            "",
            "```text",
            gate["recommended_gate"],
            "```",
        ]
    )
    REPORT_DOC.write_text(report + "\n", encoding="utf-8")


POLICY = load_json(POLICY_JSON)
FEATURE_CONTRACT = load_json(FEATURE_LABEL_CONTRACT_JSON)
SPLIT_USAGE_CONTRACT = load_json(SPLIT_USAGE_CONTRACT_JSON)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    require(POLICY["frozen_training_spec"]["model_family"] == "LightGBM.LGBMRanker", "unexpected model family")
    require(POLICY["frozen_training_spec"]["label_column"] == "ltr_relevance_label", "unexpected label column")
    sample, feature_cols = load_sample(load_json(SCHEMA_JSON), FEATURE_CONTRACT)
    model = train_model(sample, POLICY, feature_cols)
    joblib.dump(model, MODEL_PKL)
    scored = add_scores(sample, model)
    keep_cols = [
        "date", "instrument", "split", "fold_id", "qlib_score_raw", "qlib_rank",
        "ltr_score", "ltr_rank", "sample_complete", "feature_complete", "label_complete_10d",
        "regime_segment", "topk_forward_bucket", "ltr_relevance_label", "future_excess_return_rank_10d",
    ]
    scored[keep_cols].to_csv(SCORES_CSV, index=False)
    metrics = metrics_by_split(scored, model)
    metrics.to_csv(METRIC_BY_SPLIT_CSV, index=False)
    feature_importance(model).to_csv(FEATURE_IMPORTANCE_CSV, index=False)
    write_score_schema(scored[keep_cols])
    write_training_diagnostics(scored, model, metrics)
    write_leakage_audit(scored)
    gate = write_gate_summary(metrics, scored[keep_cols])
    write_report(metrics, gate)


if __name__ == "__main__":
    main()
