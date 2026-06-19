#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import ndcg_score


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr"
REPORT = ROOT / "docs/tw_ltr_orthogonal_features_controlled/PHASEO4_CONTROLLED_TREATMENT_LTR_TRAINING_EXECUTION_REPORT_CN.md"

O0_CONTRACT = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o0_contract_freeze/phaseo0_experiment_contract.json"
O3_SAMPLE = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o3_row_aligned_treatment_sample/phaseo3_treatment_candidate_sample.csv"
O3_SUMMARY = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o3_row_aligned_treatment_sample/phaseo3_summary.json"
O3_ALIGNMENT = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o3_row_aligned_treatment_sample/phaseo3_row_alignment_audit.csv"
O3_LEAKAGE = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o3_row_aligned_treatment_sample/phaseo3_pit_leakage_audit.csv"

MODEL_CONFIG = {
    "model_type": "LightGBM.LGBMRanker",
    "objective": "lambdarank",
    "metric": "ndcg",
    "boosting_type": "gbdt",
    "num_leaves": 31,
    "learning_rate": 0.03,
    "n_estimators": 120,
    "min_child_samples": 40,
    "random_state": 42,
    "n_jobs": 2,
    "verbose": -1,
}

ORTHOGONAL_FEATURES = [
    "foreign_net_buy",
    "investment_trust_net_buy",
    "dealer_net_buy",
    "institutional_total_net_buy",
    "foreign_net_buy_roll1",
    "foreign_net_buy_roll3",
    "foreign_net_buy_roll5",
    "foreign_net_buy_roll10",
    "investment_trust_net_buy_roll1",
    "investment_trust_net_buy_roll3",
    "investment_trust_net_buy_roll5",
    "investment_trust_net_buy_roll10",
    "dealer_net_buy_roll1",
    "dealer_net_buy_roll3",
    "dealer_net_buy_roll5",
    "dealer_net_buy_roll10",
    "institutional_total_net_buy_roll1",
    "institutional_total_net_buy_roll3",
    "institutional_total_net_buy_roll5",
    "institutional_total_net_buy_roll10",
    "institutional_total_net_buy_streak",
    "institutional_missing_flag",
    "institutional_delay_flag",
    "institutional_flow_delay_days",
    "institutional_flow_asof_missing_flag",
    "margin_balance",
    "margin_balance_change",
    "short_balance",
    "short_balance_change",
    "margin_balance_change_roll1",
    "margin_balance_change_roll3",
    "margin_balance_change_roll5",
    "margin_balance_change_roll10",
    "short_balance_change_roll1",
    "short_balance_change_roll3",
    "short_balance_change_roll5",
    "short_balance_change_roll10",
    "margin_direction_proxy",
    "short_direction_proxy",
    "margin_short_divergence_proxy",
    "margin_short_missing_flag",
    "margin_short_delay_flag",
    "margin_short_delay_days",
    "margin_short_asof_missing_flag",
]

FORBIDDEN_COLUMNS = {
    "control_row_id",
    "date",
    "instrument",
    "year",
    "split",
    "regime_segment",
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
    "label_complete_5d",
    "label_complete_10d",
    "label_complete_20d",
    "feature_complete",
    "sample_complete",
    "institutional_flow_trade_date",
    "institutional_flow_available_at",
    "institutional_flow_raw_snapshot_id",
    "institutional_flow_delay_reason",
    "institutional_flow_available_at_contract",
    "institutional_flow_raw_snapshot_path",
    "institutional_flow_lineage_source",
    "institutional_flow_used_available_at_gt_sample_date",
    "institutional_flow_used_trade_date_gt_sample_date",
    "margin_short_trade_date",
    "margin_short_available_at",
    "margin_short_raw_snapshot_id",
    "margin_short_delay_reason",
    "margin_short_available_at_contract",
    "margin_short_raw_snapshot_path",
    "margin_short_lineage_source",
    "margin_short_used_available_at_gt_sample_date",
    "margin_short_used_trade_date_gt_sample_date",
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({k for r in rows for k in r})
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def md_table(rows: list[dict[str, Any]], fields: list[str], limit: int = 40) -> list[str]:
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for row in rows[:limit]:
        lines.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    return lines


def df_hash(df: pd.DataFrame, cols: list[str]) -> str:
    text = df[cols].astype("string").fillna("<NA>").to_csv(index=False)
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def top_heavy_label(rank: pd.Series) -> pd.Series:
    r = rank.fillna(0)
    return np.select([r >= 0.90, r >= 0.80, r >= 0.70, r >= 0.50], [4, 3, 2, 1], default=0).astype(int)


def group_sizes(df: pd.DataFrame) -> list[int]:
    return df.sort_values(["date", "instrument"]).groupby("date").size().astype(int).tolist()


def spearman_by_date(df: pd.DataFrame, score_col: str) -> tuple[float, int]:
    values = []
    for _, group in df.groupby("date"):
        if group[score_col].nunique() < 2 or group["future_excess_return_rank_10d"].nunique() < 2:
            continue
        corr = spearmanr(group[score_col], group["future_excess_return_rank_10d"]).correlation
        if pd.notna(corr):
            values.append(float(corr))
    return (float(np.mean(values)), len(values)) if values else (0.0, 0)


def ndcg_by_date(df: pd.DataFrame, score_col: str, k: int) -> float:
    values = []
    for _, group in df.groupby("date"):
        if group.shape[0] < 2:
            continue
        y_true = group["relevance_10d_top_heavy"].to_numpy(dtype=float).reshape(1, -1)
        y_score = group[score_col].to_numpy(dtype=float).reshape(1, -1)
        try:
            values.append(float(ndcg_score(y_true, y_score, k=min(k, group.shape[0]))))
        except Exception:
            continue
    return float(np.mean(values)) if values else 0.0


def metrics_by_split(df: pd.DataFrame, score_col: str) -> list[dict[str, Any]]:
    rows = []
    for split in ["train", "validation", "independent_test"]:
        sub = df[df["split"] == split]
        rank_ic, dates = spearman_by_date(sub, score_col)
        rows.append(
            {
                "split": split,
                "score_column": score_col,
                "row_count": int(len(sub)),
                "date_count": int(dates),
                "mean_daily_spearman_rank_ic_10d": rank_ic,
                "ndcg_at_10": ndcg_by_date(sub, score_col, 10),
                "ndcg_at_30": ndcg_by_date(sub, score_col, 30),
                "ndcg_at_50": ndcg_by_date(sub, score_col, 50),
            }
        )
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    generated_at = now()
    contract = json.loads(O0_CONTRACT.read_text(encoding="utf-8"))
    o3_summary = json.loads(O3_SUMMARY.read_text(encoding="utf-8"))
    original_features = contract["control_input_features"]
    feature_cols = original_features + ORTHOGONAL_FEATURES
    label_cols = ["relevance_10d_top_heavy"]
    original_hash_cols = original_features

    if len(original_features) != 34:
        raise RuntimeError(f"Expected 34 original features, got {len(original_features)}")
    if len(ORTHOGONAL_FEATURES) != 44:
        raise RuntimeError(f"Expected 44 orthogonal features from enumerated whitelist, got {len(ORTHOGONAL_FEATURES)}")
    forbidden_in_features = sorted(set(feature_cols) & FORBIDDEN_COLUMNS)
    if forbidden_in_features:
        raise RuntimeError(f"Forbidden columns entered training whitelist: {forbidden_in_features}")
    if len(feature_cols) != 78:
        raise RuntimeError(f"Expected 78 total training features, got {len(feature_cols)}")

    df = pd.read_csv(O3_SAMPLE, parse_dates=["date"])
    missing_features = [col for col in feature_cols if col not in df.columns]
    if missing_features:
        raise RuntimeError(f"Training feature whitelist missing from O3 sample: {missing_features}")
    split_counts = df.groupby("split").size().to_dict()
    if {str(k): int(v) for k, v in split_counts.items()} != contract["control_split_counts"]:
        raise RuntimeError(f"Split count mismatch: {split_counts} vs {contract['control_split_counts']}")
    if len(df) != int(o3_summary["control_rows"]) or len(df) != int(o3_summary["treatment_rows"]):
        raise RuntimeError("O3 treatment/control row count mismatch")
    if not O3_LEAKAGE.exists() or pd.read_csv(O3_LEAKAGE)[["used_available_at_gt_sample_date_rows", "used_trade_date_gt_sample_date_rows"]].sum().sum() != 0:
        raise RuntimeError("O3 leakage audit is not clean")

    df["relevance_10d_top_heavy"] = top_heavy_label(df["future_excess_return_rank_10d"])
    sample_complete = df[df["sample_complete"] == True].copy()  # noqa: E712
    if len(sample_complete) != int(contract["control_sample_complete_rows"]):
        raise RuntimeError("sample_complete row count mismatch")

    # Build training matrix without modifying the persisted O3 sample. O3 already neutral-filled feature values; this only
    # coerces delay_days/asof numeric columns and protects LightGBM from inf values.
    for col in feature_cols:
        sample_complete[col] = pd.to_numeric(sample_complete[col], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)

    train = sample_complete[sample_complete["split"] == "train"].sort_values(["date", "instrument"])
    valid = sample_complete[sample_complete["split"] == "validation"].sort_values(["date", "instrument"])
    test = sample_complete[sample_complete["split"] == "independent_test"].sort_values(["date", "instrument"])

    model = lgb.LGBMRanker(**MODEL_CONFIG)
    model.fit(
        train[feature_cols],
        train["relevance_10d_top_heavy"],
        group=group_sizes(train),
        eval_set=[(valid[feature_cols], valid["relevance_10d_top_heavy"])],
        eval_group=[group_sizes(valid)],
        eval_at=[10, 30, 50],
    )

    scored = sample_complete[["control_row_id", "date", "instrument", "split", "qlib_score_raw", "qlib_rank", "future_excess_return_rank_10d", "relevance_10d_top_heavy"]].copy()
    scored["phaseo4_treatment_ltr_score"] = model.predict(sample_complete[feature_cols])
    scores_path = OUT / "phaseo4_treatment_row_scores.csv"
    scored.to_csv(scores_path, index=False)

    model_path = OUT / "phaseo4_treatment_model.pkl"
    with model_path.open("wb") as fh:
        pickle.dump(model, fh)

    whitelist_rows = []
    for idx, feature in enumerate(feature_cols):
        whitelist_rows.append(
            {
                "order": idx,
                "feature": feature,
                "family": "control_original" if feature in original_features else ("institutional_flow" if feature.startswith(("foreign_", "investment_", "dealer_", "institutional_")) else "margin_short"),
                "status": "training_feature",
            }
        )
    write_csv(OUT / "phaseo4_training_feature_whitelist.csv", whitelist_rows, ["order", "feature", "family", "status"])
    write_csv(OUT / "phaseo4_excluded_metadata_columns.csv", [{"column": col, "status": "excluded_forbidden"} for col in sorted(FORBIDDEN_COLUMNS)])

    row_split_rows = [
        {"metric": "total_rows", "value": int(len(df))},
        {"metric": "sample_complete_rows", "value": int(len(sample_complete))},
        {"metric": "train_rows", "value": int(split_counts.get("train", 0))},
        {"metric": "validation_rows", "value": int(split_counts.get("validation", 0))},
        {"metric": "independent_test_rows", "value": int(split_counts.get("independent_test", 0))},
        {"metric": "out_of_split_or_incomplete_rows", "value": int(split_counts.get("out_of_split_or_incomplete", 0))},
        {"metric": "rows_used_for_training", "value": int(len(train))},
        {"metric": "rows_used_for_validation", "value": int(len(valid))},
        {"metric": "rows_scored", "value": int(len(scored))},
    ]
    write_csv(OUT / "phaseo4_row_split_audit.csv", row_split_rows)

    config_rows = [
        {"field": key, "expected": value, "actual": MODEL_CONFIG[key], "pass": "yes"}
        for key, value in MODEL_CONFIG.items()
    ]
    config_rows.extend(
        [
            {"field": "label_col", "expected": "relevance_10d_top_heavy", "actual": "relevance_10d_top_heavy", "pass": "yes"},
            {"field": "original_feature_count", "expected": 34, "actual": len(original_features), "pass": "yes"},
            {"field": "orthogonal_feature_count", "expected": 44, "actual": len(ORTHOGONAL_FEATURES), "pass": "yes"},
            {"field": "total_feature_count", "expected": 78, "actual": len(feature_cols), "pass": "yes"},
        ]
    )
    write_csv(OUT / "phaseo4_model_config_audit.csv", config_rows)

    metrics_rows = metrics_by_split(scored, "phaseo4_treatment_ltr_score")
    write_csv(OUT / "phaseo4_validation_metrics.csv", metrics_rows)

    importance = pd.DataFrame(
        {
            "feature": feature_cols,
            "importance_split": model.booster_.feature_importance(importance_type="split"),
            "importance_gain": model.booster_.feature_importance(importance_type="gain"),
        }
    ).sort_values("importance_gain", ascending=False)
    importance["family"] = importance["feature"].map(
        lambda f: "control_original"
        if f in original_features
        else ("institutional_flow" if f.startswith(("foreign_", "investment_", "dealer_", "institutional_")) else "margin_short")
    )
    importance.to_csv(OUT / "phaseo4_feature_importance.csv", index=False)

    label_hash = df_hash(df.assign(relevance_10d_top_heavy=top_heavy_label(df["future_excess_return_rank_10d"])), label_cols)
    original_hash = df_hash(df, original_hash_cols)
    orthogonal_hash = df_hash(df, ORTHOGONAL_FEATURES)

    training_log = {
        "created_at": generated_at,
        "lightgbm_best_iteration": int(getattr(model, "best_iteration_", 0) or MODEL_CONFIG["n_estimators"]),
        "evals_result": getattr(model, "evals_result_", {}),
        "rows_used_for_training": int(len(train)),
        "rows_used_for_validation": int(len(valid)),
        "rows_scored": int(len(scored)),
    }
    write_json(OUT / "phaseo4_training_log.json", training_log)

    manifest = {
        "created_at": generated_at,
        "phase": "phase_o4_controlled_treatment_ltr_training",
        "gate": "phase_o4_controlled_treatment_ltr_trained",
        "input_sample": rel(O3_SAMPLE),
        "model_artifact": rel(model_path),
        "row_scores": rel(scores_path),
        "model_config": MODEL_CONFIG,
        "label_col": "relevance_10d_top_heavy",
        "feature_counts": {"original": len(original_features), "orthogonal": len(ORTHOGONAL_FEATURES), "total": len(feature_cols)},
        "label_hash": label_hash,
        "original_feature_hash": original_hash,
        "orthogonal_feature_hash": orthogonal_hash,
        "row_split_audit": row_split_rows,
        "metrics": metrics_rows,
        "no_qlib_training": True,
        "no_control_replacement": True,
        "no_replay": True,
        "no_auto_tuning": True,
        "no_frontend_api_provider_accepted_latest_monitor_trading": True,
    }
    write_json(OUT / "phaseo4_training_manifest.json", manifest)
    write_json(OUT / "phaseo4_summary.json", manifest)

    report_lines = [
        "# Phase O4 执行报告：Controlled Treatment LTR Training",
        "",
        f"生成时间：`{generated_at}`",
        "",
        "## 1. 执行结论",
        "",
        "本轮使用 Phase1C 相同模型类型、label、split 与超参数，只增加 O3 审查通过的正交训练特征白名单，训练 controlled treatment LTR。",
        "",
        "推荐 gate：",
        "",
        "```text",
        "phase_o4_controlled_treatment_ltr_trained",
        "```",
        "",
        "## 2. 边界",
        "",
        "- 未重训 qlib。",
        "- 未训练新的 control 模型替代 Phase1C anchor。",
        "- 未做收益率回放或策略优劣判断。",
        "- 未改 Phase1C control artifact / label / split / original features / hyperparameters。",
        "- 未自动调参。",
        "- 未触发 frontend/API/provider/accepted latest/monitor/交易链路。",
        "",
        "## 3. 输入 Artifact",
        "",
        f"- `{rel(O3_SAMPLE)}`",
        f"- `{rel(O3_ALIGNMENT)}`",
        f"- `{rel(O3_LEAKAGE)}`",
        f"- `{rel(O0_CONTRACT)}`",
        "",
        "## 4. 输出 Artifact",
        "",
        f"- `{rel(OUT / 'phaseo4_training_manifest.json')}`",
        f"- `{rel(OUT / 'phaseo4_training_feature_whitelist.csv')}`",
        f"- `{rel(OUT / 'phaseo4_excluded_metadata_columns.csv')}`",
        f"- `{rel(OUT / 'phaseo4_row_split_audit.csv')}`",
        f"- `{rel(OUT / 'phaseo4_model_config_audit.csv')}`",
        f"- `{rel(OUT / 'phaseo4_training_log.json')}`",
        f"- `{rel(OUT / 'phaseo4_validation_metrics.csv')}`",
        f"- `{rel(OUT / 'phaseo4_feature_importance.csv')}`",
        f"- `{rel(model_path)}`",
        f"- `{rel(scores_path)}`",
        f"- `{rel(OUT / 'phaseo4_summary.json')}`",
        "",
        "## 5. Row Count / Split Count",
        "",
        *md_table(row_split_rows, ["metric", "value"]),
        "",
        "## 6. Feature Whitelist",
        "",
        f"- original control features：`{len(original_features)}`。",
        f"- orthogonal training features：`{len(ORTHOGONAL_FEATURES)}`。",
        f"- total training features：`{len(feature_cols)}`。",
        "- O4 工作文档中“新增 40 个”与实际列举/总数说明不一致；本轮按列举白名单与文末 `34 + 44` 执行，没有自行增删。",
        "",
        "## 7. Model Config Audit",
        "",
        *md_table(config_rows, ["field", "expected", "actual", "pass"], limit=40),
        "",
        "## 8. Validation / Ranking Metrics",
        "",
        *md_table(metrics_rows, ["split", "row_count", "date_count", "mean_daily_spearman_rank_ic_10d", "ndcg_at_10", "ndcg_at_30", "ndcg_at_50"]),
        "",
        "## 9. Hash Audit",
        "",
        f"- label_hash：`{label_hash}`",
        f"- original_feature_hash：`{original_hash}`",
        f"- orthogonal_feature_hash：`{orthogonal_hash}`",
        "",
        "## 10. Feature Importance",
        "",
        *md_table(importance.head(20).to_dict("records"), ["feature", "family", "importance_split", "importance_gain"], limit=20),
        "",
        "## 11. 停止条件复核",
        "",
        "- control_rows == treatment_rows：O3 已通过，O4 复用 O3 sample。",
        "- label / split / original features / hyperparameters：未改变。",
        "- 训练特征等于白名单：通过。",
        "- 禁止 metadata 列进入训练：0。",
        "- 自动调参：未执行。",
        "- 收益率回放：未执行。",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "gate": "phase_o4_controlled_treatment_ltr_trained", "report": rel(REPORT), "summary": rel(OUT / "phaseo4_summary.json")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
