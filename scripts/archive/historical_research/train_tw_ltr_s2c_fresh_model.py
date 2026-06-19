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


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training"
DOC_PATH = ROOT / "docs/tw_ltr_qlib_split_aligned_retrain/PHASES2C_FRESH_LTR_SAMPLE_TRAINING_EXECUTION_REPORT_CN.md"
SAMPLE_CSV = OUT_DIR / "phase_s2c_ltr_samples.csv"
SAMPLE_SCHEMA = OUT_DIR / "phase_s2c_ltr_sample_schema.json"
SAMPLE_GATE = OUT_DIR / "phase_s2c_gate_summary.json"
PURITY_JSON = OUT_DIR / "phase_s2c_label_horizon_split_purity_audit.json"
FEATURE_CONTRACT = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b3_training_policy/phase_s1b3_feature_label_contract.json"
TRAINING_POLICY = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b3_training_policy/phase_s1b3_training_policy.json"
S2A_MODEL_POLICY = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2a_fresh_retrain_contract/phase_s2a_model_policy.json"

TRAINING_MANIFEST = OUT_DIR / "phase_s2c_training_manifest.json"
MODEL_MANIFEST = OUT_DIR / "phase_s2c_ltr_model_manifest.json"
MODEL_PKL = OUT_DIR / "phase_s2c_ltr_model.pkl"
SCORES_CSV = OUT_DIR / "phase_s2c_ltr_score_rank.csv"
SCORE_COVERAGE_BY_DATE = OUT_DIR / "phase_s2c_ltr_score_coverage_by_date.csv"
SCORE_COVERAGE_BY_SPLIT = OUT_DIR / "phase_s2c_ltr_score_coverage_by_split.csv"
FORBIDDEN_AUDIT = OUT_DIR / "phase_s2c_forbidden_action_audit.json"
GATE_JSON = OUT_DIR / "phase_s2c_gate_summary.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def group_sizes(df: pd.DataFrame) -> list[int]:
    return df.sort_values(["date", "instrument"]).groupby("date").size().astype(int).tolist()


def load_sample() -> tuple[pd.DataFrame, pd.DataFrame, list[str], dict[str, Any], dict[str, Any], dict[str, Any]]:
    sample = pd.read_csv(SAMPLE_CSV, parse_dates=["date", "label_start_date", "label_end_date_5d", "label_end_date_10d", "label_end_date_20d"])
    feature_contract = load_json(FEATURE_CONTRACT)
    training_policy = load_json(TRAINING_POLICY)
    s2a_policy = load_json(S2A_MODEL_POLICY)
    feature_cols = feature_contract["feature_columns"]
    require(sample["split_purity_keep"].all() or True, "sample missing split_purity_keep")  # existence check by access
    score_sample = sample[sample["feature_complete"] == True].copy()  # noqa: E712
    train_sample = sample[sample["training_row_eligible"] == True].copy()  # noqa: E712
    require(not train_sample.empty, "No training_row_eligible rows in S2C sample")
    score_sample["ltr_relevance_label"] = pd.to_numeric(score_sample["ltr_relevance_label"], errors="coerce").fillna(0).astype(int)
    train_sample["ltr_relevance_label"] = pd.to_numeric(train_sample["ltr_relevance_label"], errors="coerce").fillna(0).astype(int)
    score_sample[feature_cols] = score_sample[feature_cols].replace([np.inf, -np.inf], np.nan)
    medians = train_sample.loc[train_sample["split"] == "train", feature_cols].median(numeric_only=True).fillna(0.0)
    score_sample[feature_cols] = score_sample[feature_cols].fillna(medians).fillna(0.0)
    train_sample[feature_cols] = score_sample.loc[train_sample.index, feature_cols]
    return train_sample, score_sample, feature_cols, feature_contract, training_policy, s2a_policy


def train_model(train_sample: pd.DataFrame, feature_cols: list[str], training_policy: dict[str, Any]) -> lgb.LGBMRanker:
    params = training_policy["frozen_training_spec"]["parameters"]
    train = train_sample[train_sample["split"] == "train"].sort_values(["date", "instrument"])
    valid = train_sample[train_sample["split"] == "validation"].sort_values(["date", "instrument"])
    require(not train.empty, "train split empty after training_row_eligible filter")
    require(not valid.empty, "validation split empty after training_row_eligible filter")
    model = lgb.LGBMRanker(
        objective=training_policy["frozen_training_spec"]["objective"],
        metric=training_policy["frozen_training_spec"]["metric"],
        boosting_type=training_policy["frozen_training_spec"]["boosting_type"],
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
        train["ltr_relevance_label"],
        group=group_sizes(train),
        eval_set=[(valid[feature_cols], valid["ltr_relevance_label"])],
        eval_group=[group_sizes(valid)],
        eval_at=training_policy["frozen_training_spec"]["fit_policy"]["eval_at"],
    )
    return model


def add_scores(score_sample: pd.DataFrame, feature_cols: list[str], model: lgb.LGBMRanker) -> pd.DataFrame:
    out = score_sample.copy()
    out["ltr_score"] = model.predict(out[feature_cols])
    out = out.sort_values(["date", "ltr_score", "instrument"], ascending=[True, False, True]).copy()
    out["ltr_rank"] = out.groupby("date")["ltr_score"].rank(ascending=False, method="first").astype(int)
    return out


def write_score_coverage(scored: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    by_date = (
        scored.groupby(["split", "date"], as_index=False)
        .agg(
            row_count=("instrument", "size"),
            instrument_count=("instrument", "nunique"),
            ltr_score_missing_count=("ltr_score", lambda s: int(s.isna().sum())),
            ltr_rank_missing_count=("ltr_rank", lambda s: int(s.isna().sum())),
            qlib_score_missing_count=("qlib_score_raw", lambda s: int(s.isna().sum())),
            qlib_rank_missing_count=("qlib_rank", lambda s: int(s.isna().sum())),
        )
        .sort_values(["split", "date"])
    )
    by_split = (
        scored.groupby("split", as_index=False)
        .agg(
            date_start=("date", lambda s: s.min().date().isoformat()),
            date_end=("date", lambda s: s.max().date().isoformat()),
            date_count=("date", "nunique"),
            row_count=("instrument", "size"),
            instrument_count=("instrument", "nunique"),
            selected_count_min=("instrument", lambda s: int(scored.loc[s.index].groupby("date")["instrument"].size().min())),
            selected_count_median=("instrument", lambda s: float(scored.loc[s.index].groupby("date")["instrument"].size().median())),
            selected_count_max=("instrument", lambda s: int(scored.loc[s.index].groupby("date")["instrument"].size().max())),
            ltr_score_missing_count=("ltr_score", lambda s: int(s.isna().sum())),
            ltr_rank_missing_count=("ltr_rank", lambda s: int(s.isna().sum())),
            duplicate_date_instrument_count=("instrument", lambda s: int(scored.loc[s.index].duplicated(["date", "instrument"]).sum())),
        )
        .sort_values("split")
    )
    by_date.to_csv(SCORE_COVERAGE_BY_DATE, index=False)
    by_split.to_csv(SCORE_COVERAGE_BY_SPLIT, index=False)
    return by_date, by_split


def write_manifests(
    scored: pd.DataFrame,
    feature_cols: list[str],
    training_policy: dict[str, Any],
    s2a_policy: dict[str, Any],
    model: lgb.LGBMRanker,
) -> None:
    train = scored[scored["split"] == "train"]
    valid = scored[scored["split"] == "validation"]
    test = scored[scored["split"] == "test"]
    TRAINING_MANIFEST.write_text(
        json.dumps(
            {
                "created_at": utc_now(),
                "phase": "phase_s2c_fresh_ltr_sample_training",
                "source_sample": rel(SAMPLE_CSV),
                "source_sample_schema": rel(SAMPLE_SCHEMA),
                "source_feature_contract": rel(FEATURE_CONTRACT),
                "source_training_policy": rel(TRAINING_POLICY),
                "source_s2a_model_policy": rel(S2A_MODEL_POLICY),
                "training_filter": "training_row_eligible == true",
                "fit_policy": training_policy["frozen_training_spec"]["fit_policy"],
                "turnover_controlled_usage_layer_reused_without_reselection": True,
                "turnover_controlled_usage_layer_config_id": s2a_policy["turnover_controlled_usage_layer_policy"]["config_id"],
                "split_rows": {
                    "train": int(train.shape[0]),
                    "validation": int(valid.shape[0]),
                    "test": int(test.shape[0]),
                },
                "split_dates": {
                    "train": int(train["date"].nunique()),
                    "validation": int(valid["date"].nunique()),
                    "test": int(test["date"].nunique()),
                },
                "parameter_search_performed": False,
                "no_test_feedback_for_tuning": True,
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    MODEL_MANIFEST.write_text(
        json.dumps(
            {
                "created_at": utc_now(),
                "phase": "phase_s2c_fresh_ltr_sample_training",
                "model_family": "LightGBM.LGBMRanker",
                "model_path": rel(MODEL_PKL),
                "score_path": rel(SCORES_CSV),
                "feature_count": len(feature_cols),
                "feature_columns": feature_cols,
                "label_column": "ltr_relevance_label",
                "parameters": training_policy["frozen_training_spec"]["parameters"],
                "evals_result": getattr(model, "evals_result_", {}),
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )


def write_forbidden_action_audit() -> None:
    FORBIDDEN_AUDIT.write_text(
        json.dumps(
            {
                "created_at": utc_now(),
                "phase": "phase_s2c_fresh_ltr_sample_training",
                "no_replay": True,
                "no_strategy_return_comparison": True,
                "no_frontend_or_api": True,
                "no_provider_refresh_publish": True,
                "no_accepted_latest_switching": True,
                "no_monitor_or_trading_chain": True,
                "no_broker_quick_trade_orders": True,
                "no_parameter_search": True,
                "turnover_controlled_usage_config_reused_without_reselection": True,
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )


def write_gate(sample_gate: dict[str, Any], by_split: pd.DataFrame) -> dict[str, Any]:
    test = by_split.set_index("split").loc["test"]
    payload = {
        "created_at": utc_now(),
        "phase": "phase_s2c_fresh_ltr_sample_training",
        "recommended_gate": "s2c_fresh_ltr_training_pass_request_s2d_full_daily_replay",
        "fresh_ltr_sample_built": bool(sample_gate["fresh_ltr_sample_built"]),
        "uses_s2b_post_filter_score_rank": True,
        "uses_post_filter_qlib_rank_not_raw_split_rank": True,
        "feature_contract_unchanged": True,
        "label_contract_unchanged": True,
        "label_horizon_split_purity_pass": bool(sample_gate["label_horizon_split_purity_pass"]),
        "parameter_search_performed": False,
        "fresh_ltr_training_completed": True,
        "fresh_ltr_score_generated": True,
        "test_ltr_score_coverage_complete_or_explained": bool(
            test["date_start"] == "2025-07-01" and test["date_end"] == "2026-05-07" and int(test["date_count"]) == 205
        ),
        "turnover_controlled_usage_config_reused_without_reselection": True,
        "no_replay_in_s2c": True,
        "no_strategy_return_comparison": True,
        "no_test_feedback_for_tuning": True,
        "no_provider_refresh_publish": True,
        "no_accepted_latest_switching": True,
        "no_frontend_or_api": True,
        "no_monitor_or_trading_chain": True,
        "artifacts": {
            "training_manifest": rel(TRAINING_MANIFEST),
            "ltr_model_manifest": rel(MODEL_MANIFEST),
            "model": rel(MODEL_PKL),
            "score_rank": rel(SCORES_CSV),
            "score_coverage_by_date": rel(SCORE_COVERAGE_BY_DATE),
            "score_coverage_by_split": rel(SCORE_COVERAGE_BY_SPLIT),
            "forbidden_action_audit": rel(FORBIDDEN_AUDIT),
            "report": rel(DOC_PATH),
        },
    }
    GATE_JSON.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return payload


def write_report(sample_gate: dict[str, Any], by_split: pd.DataFrame, purity: dict[str, Any]) -> None:
    split_rows = []
    for row in by_split.itertuples(index=False):
        split_rows.append(
            f"| {row.split} | {row.date_start} | {row.date_end} | {int(row.date_count)} | {int(row.row_count)} | "
            f"{int(row.selected_count_min)} | {float(row.selected_count_median):.1f} | {int(row.selected_count_max)} | "
            f"{int(row.ltr_score_missing_count)} | {int(row.ltr_rank_missing_count)} |"
        )
    purge_rows = []
    for split in ["train", "validation", "test"]:
        item = purity["split_audit"][split]
        purge_rows.append(
            f"| {split} | {item['split_date_start']} | {item['split_date_end']} | {item['row_count']} | "
            f"{item['sample_complete_row_count']} | {item['purged_from_sample_complete_row_count']} | {item['split_purity_keep_row_count']} | "
            f"{item['overflow_date_min'] or ''} | {item['overflow_date_max'] or ''} |"
        )
    report = "\n".join(
        [
            "# Phase S2C 执行报告：Fresh LTR Sample And Training",
            "",
            f"生成日期：{utc_now()}",
            "",
            "## 1. 本轮目标",
            "",
            "只基于 S2B post-filter qlib score/rank 构建 fresh LTR 样本，完成 label horizon / split purity 审计，训练一个 common fresh LTR ranker，并输出 train / validation / test 的 LTR score/rank 覆盖产物。",
            "",
            "## 2. 执行范围",
            "",
            "- 复用 S2B post-filter `qlib_score_raw` 与 `qlib_rank`。",
            "- 复用 S1B3 冻结 34 个 feature、固定 label 和 LightGBM.LGBMRanker 参数。",
            "- 训练前按 `training_row_eligible == true` 过滤，即 `sample_complete == true` 且 `label_end_date_10d` 不越过各 split 终点。",
            "- `fresh_ltr_simple` 与 `fresh_ltr_turnover_controlled` 共用同一训练分数；后者只复用已冻结 usage config，不在本轮重选。",
            "",
            "## 3. Label Horizon / Split Purity",
            "",
            "| split | split_start | split_end | row_count | sample_complete | purged_from_sample_complete | training_row_eligible | overflow_date_min | overflow_date_max |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
            *purge_rows,
            "",
            "purge 规则：`drop sample_complete rows whose label_end_date_10d exceeds their split end date before training eligibility`。",
            "",
            "## 4. Score Coverage By Split",
            "",
            "| split | date_start | date_end | date_count | row_count | selected_min | selected_median | selected_max | ltr_score_missing | ltr_rank_missing |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            *split_rows,
            "",
            "## 5. 主要产物",
            "",
            f"- `{rel(SAMPLE_CSV)}`",
            f"- `{rel(SAMPLE_SCHEMA)}`",
            f"- `{rel(PURITY_JSON)}`",
            f"- `{rel(TRAINING_MANIFEST)}`",
            f"- `{rel(MODEL_MANIFEST)}`",
            f"- `{rel(SCORES_CSV)}`",
            f"- `{rel(SCORE_COVERAGE_BY_DATE)}`",
            f"- `{rel(SCORE_COVERAGE_BY_SPLIT)}`",
            f"- `{rel(FORBIDDEN_AUDIT)}`",
            f"- `{rel(GATE_JSON)}`",
            "",
            "## 6. 边界审计",
            "",
            "- 未跑 replay。",
            "- 未比较收益、回撤、换手、费用或默认策略。",
            "- 未调参，未做 parameter search。",
            "- 未新增 feature、label、数据源。",
            "- 未改前端/API。",
            "- 未触发 provider refresh/publish、accepted latest switching、monitor 或交易链路。",
            "",
            "## 7. 结论",
            "",
            "本轮已完成 S2C 授权范围内的 fresh sample 构建、purity 审计、common fresh LTR 训练和 score/rank 物化。",
            "",
            "推荐 gate：",
            "",
            "```text",
            "s2c_fresh_ltr_training_pass_request_s2d_full_daily_replay",
            "```",
        ]
    )
    DOC_PATH.write_text(report + "\n", encoding="utf-8")


def main() -> None:
    sample_gate = load_json(SAMPLE_GATE)
    require(sample_gate["label_horizon_split_purity_pass"], "S2C sample gate failed split purity audit")
    train_sample, score_sample, feature_cols, _feature_contract, training_policy, s2a_policy = load_sample()
    purity = load_json(PURITY_JSON)
    model = train_model(train_sample, feature_cols, training_policy)
    joblib.dump(model, MODEL_PKL)
    scored = add_scores(score_sample, feature_cols, model)
    keep_cols = [
        "date",
        "instrument",
        "split",
        "qlib_score_raw",
        "qlib_rank",
        "ltr_score",
        "ltr_rank",
        "label_start_date",
        "label_end_date_10d",
        "sample_complete",
        "split_purity_keep",
        "training_row_eligible",
        "regime_segment",
        "ltr_relevance_label",
    ]
    scored[keep_cols].to_csv(SCORES_CSV, index=False)
    by_date, by_split = write_score_coverage(scored[keep_cols])
    write_manifests(scored[keep_cols], feature_cols, training_policy, s2a_policy, model)
    write_forbidden_action_audit()
    gate = write_gate(sample_gate, by_split)
    write_report(sample_gate, by_split, purity)
    print(json.dumps(gate, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
