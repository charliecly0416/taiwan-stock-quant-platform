#!/usr/bin/env python3
"""Freeze the development-only A versus A+B comparison protocol."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_comparative_evaluation_20260916"
FREEZE = OUT / "B19R2R_COMPARATIVE_FREEZE.json"
REPORT = OUT / "B19R2R_COMPARATIVE_FREEZE_CN.md"
PRECHECK = OUT / "B19R2R_COMPARATIVE_STATIC_PRECHECK.json"
VALIDATOR = ROOT / "scripts/validate_modelb_b19r2r_comparative_freeze.py"
R2R = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_pretraining_materialization_20260916"
TRAINING = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_training_20260916"

SOURCES = {
    "preoutcome_base_freeze": R2R / "B19R2R_PREOUTCOME_FREEZE.json",
    "effective_amendment_03": R2R / "B19R2R_PREOUTCOME_FREEZE_AMENDMENT_03.json",
    "effective_amendment_04": R2R / "B19R2R_PREOUTCOME_FREEZE_AMENDMENT_04.json",
    "outcome_grid_amendment_06": R2R / "B19R2R_PREOUTCOME_FREEZE_AMENDMENT_06.json",
    "effective_a7_errata": R2R / "B19R2R_PREOUTCOME_FREEZE_AMENDMENT_07_ERRATA.json",
    "split_protocol": R2R / "NESTED_WALK_FORWARD_SPLIT_AMENDMENT_03.csv",
    "model_a_development_scores": R2R / "MODEL_A_FULL_CROSS_SECTION.parquet",
    "development_features_78f": R2R / "FEATURE_ARTIFACT_78_RAW.parquet",
    "development_exact50_keys": R2R / "EXACT50_KEYSETS.csv",
    "development_exact50_labels": R2R / "outcome_materialization_v1/development/DEVELOPMENT_EXACT50_LABELS.parquet",
    "development_execution_grid": R2R / "outcome_materialization_v1/development/DEVELOPMENT_EXECUTION_GRID.parquet",
    "tie_aware_fixture": R2R / "TIE_AWARE_RANK_FIXTURE.csv",
    "feature_schema": ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b2_canonical_pit_features_20260913/FEATURE_SCHEMA.json",
    "training_freeze": TRAINING / "B19R2R_TRAINING_FREEZE.json",
    "training_manifest": TRAINING / "training_output_v1/TRAINING_MANIFEST.json",
    "post_training_review": TRAINING / "B19R2R_POST_TRAINING_INDEPENDENT_REVIEW.json",
    "trained_final_model": TRAINING / "training_output_v1/MODEL_B_B19R2R_LGBM_RANKER.pkl",
    "trainer_implementation": ROOT / "scripts/train_modelb_b19r2r_lambdarank.py",
    "strategy_dependency": ROOT / "configs/strategy_dependencies/top50_exit_one_worst_sell.yaml",
    "paired_replay_reference": ROOT / "scripts/run_modelb_b18_historical_pit_paired_replay.py",
    "modular_replay_engine": ROOT / "scripts/run_tw_modular_order_intent_replay.py",
}
FORBIDDEN_SOURCE_FRAGMENTS = ("sealed_embargo", "sealed_confirmation", "EMBARGO_", "CONFIRMATION_")
OUTER = {
    "outer_1": {
        "train_end": "2026-04-22",
        "validation_start": "2026-05-11",
        "validation_end": "2026-06-05",
        "validation_dates": 20,
        "validation_rows": 1000,
        "terminal_execution_date": "2026-06-08",
    },
    "outer_2": {
        "train_end": "2026-05-22",
        "validation_start": "2026-06-08",
        "validation_end": "2026-07-06",
        "validation_dates": 20,
        "validation_rows": 1000,
        "terminal_execution_date": "2026-07-07",
    },
}
NUMERIC_GATES = {
    "confirmation_after_cost_return_delta_b_minus_a": {"operator": ">", "threshold": 0.0},
    "confirmation_paired_moving_block_bootstrap_95pct_lower_bound": {"operator": ">", "threshold": 0.0},
    "max_drawdown_noninferiority_b_minus_a": {"operator": ">=", "threshold": -0.02},
    "turnover_ratio_b_over_a": {"operator": "<=", "threshold": 1.25},
    "fee_tax_ratio_b_over_a": {"operator": "<=", "threshold": 1.25},
    "top1_abs_contribution_share": {"operator": "<=", "threshold": 0.2},
    "top1_abs_contribution_share_vs_a_delta": {"operator": "<=", "threshold": 0.03},
    "top5_abs_contribution_share": {"operator": "<=", "threshold": 0.45},
    "top5_abs_contribution_share_vs_a_delta": {"operator": "<=", "threshold": 0.03},
    "abs_contribution_hhi": {"operator": "<=", "threshold": 0.06},
    "abs_contribution_hhi_vs_a_delta": {"operator": "<=", "threshold": 0.01},
    "monthly_outperformance_fraction": {"operator": ">=", "threshold": 0.6},
    "negative_twii20_regime_return_delta": {"operator": ">=", "threshold": -0.02},
    "rank_ic_delta_b_minus_a": {"operator": ">=", "threshold": 0.01},
    "ndcg_at_10_delta_b_minus_a": {"operator": ">=", "threshold": 0.01},
    "minimum_executed_buys_each_track": {"operator": ">=", "threshold": 10},
    "minimum_executed_sells_each_track": {"operator": ">=", "threshold": 0},
    "executed_buy_count_ratio_b_over_a": {"operator": "<=", "threshold": 1.25},
    "executed_sell_count_ratio_b_over_a": {"operator": "<=", "threshold": 1.25},
    "executed_total_action_count_ratio_b_over_a": {"operator": "<=", "threshold": 1.25},
    "executed_total_action_count_absolute_delta_b_minus_a": {"operator": "<=", "threshold": 5},
    "zero_denominator_policy": "FAIL_GATE",
    "pending_or_fallback_actions_allowed": 0,
    "all_emitted_positive_quantity_actions_must_execute": True,
    "engineering_tolerance": 0,
    "all_gates_jointly_required": True,
    "post_outcome_threshold_change_allowed": False,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def normalize(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["date"] = frame.date.astype(str).str[:10]
    frame["instrument"] = frame.instrument.astype(str).str.upper()
    return frame


def write_once(path: Path, payload: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        data = payload.encode("utf-8")
        written = 0
        while written < len(data):
            written += os.write(descriptor, data[written:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def inspect_readiness() -> dict[str, Any]:
    for role, path in SOURCES.items():
        if not path.is_file():
            raise RuntimeError(f"missing source: {role}: {rel(path)}")
        if any(fragment in rel(path) for fragment in FORBIDDEN_SOURCE_FRAGMENTS):
            raise RuntimeError(f"sealed source forbidden: {rel(path)}")

    training_freeze = json.loads(SOURCES["training_freeze"].read_text(encoding="utf-8"))
    training_manifest = json.loads(SOURCES["training_manifest"].read_text(encoding="utf-8"))
    post_review = json.loads(SOURCES["post_training_review"].read_text(encoding="utf-8"))
    if (
        training_manifest.get("selected_candidate_id") != 14
        or training_manifest.get("feature_count") != 78
        or training_manifest.get("rank_ic_label") != "future_excess_return_10d_canonical"
        or post_review.get("verdict") != "PASS_TRAINED_MODEL_ARTIFACT"
        or post_review.get("handoff_to_frozen_comparative_evaluation_design_allowed") is not True
    ):
        raise RuntimeError("training handoff contract failed")

    labels = normalize(pd.read_parquet(SOURCES["development_exact50_labels"]))
    features = normalize(pd.read_parquet(SOURCES["development_features_78f"]))
    model_a = normalize(pd.read_parquet(SOURCES["model_a_development_scores"]))
    exact50 = normalize(pd.read_csv(SOURCES["development_exact50_keys"]))
    grid = normalize(pd.read_parquet(SOURCES["development_execution_grid"]))
    development_dates = sorted(labels.date.unique().tolist())
    dev_keys = labels[["date", "instrument"]].sort_values(["date", "instrument"]).reset_index(drop=True)
    exact_dev = exact50[exact50.date.isin(development_dates)].sort_values(["date", "instrument"]).reset_index(drop=True)
    if (
        len(labels) != 2000
        or len(development_dates) != 40
        or labels.groupby("date").size().ne(50).any()
        or labels.duplicated(["date", "instrument"]).any()
        or not labels.label_complete.all()
        or not dev_keys.equals(exact_dev[["date", "instrument"]])
    ):
        raise RuntimeError("development Exact-50 key or label readiness failed")
    paired_inputs = (
        dev_keys.merge(
            model_a[["date", "instrument", "model_a_raw_score", "full_qlib_rank"]],
            on=["date", "instrument"], how="left", validate="one_to_one",
        )
        .merge(features, on=["date", "instrument"], how="left", validate="one_to_one")
        .sort_values(["date", "instrument"], kind="mergesort")
        .reset_index(drop=True)
    )
    if len(paired_inputs) != 2000 or not paired_inputs.feature_raw_complete_78.all():
        raise RuntimeError("development feature or Model A key readiness failed")
    feature_order = json.loads(SOURCES["feature_schema"].read_text(encoding="utf-8"))["feature_order"]
    if len(feature_order) != 78 or not np.isfinite(paired_inputs[feature_order].to_numpy(float)).all():
        raise RuntimeError("development 78F readiness failed")
    if not np.array_equal(
        paired_inputs.model_a_raw_score.to_numpy(float),
        paired_inputs.qlib_score_raw.to_numpy(float),
    ):
        raise RuntimeError("Model A score and 78F qlib score parity failed")

    required_grid = ["next_trade_date", "next_open", "next_close", "terminal_2026_09_02_close", "execution_grid_complete"]
    if (
        len(grid) != 6000
        or grid.date.nunique() != 40
        or grid.groupby("date").size().ne(150).any()
        or grid[required_grid].isna().any().any()
        or not grid.execution_grid_complete.all()
        or not np.isfinite(grid[["next_open", "next_close", "terminal_2026_09_02_close"]].to_numpy(float)).all()
        or (grid[["next_open", "next_close", "terminal_2026_09_02_close"]].to_numpy(float) <= 0).any()
    ):
        raise RuntimeError("development execution-grid readiness failed")

    outer_keys: dict[str, pd.DataFrame] = {}
    terminal_checks: dict[str, Any] = {}
    for name, fold in OUTER.items():
        keys = dev_keys[dev_keys.date.between(fold["validation_start"], fold["validation_end"])].copy()
        if len(keys) != fold["validation_rows"] or keys.date.nunique() != fold["validation_dates"]:
            raise RuntimeError(f"{name} validation-key coverage failed")
        outer_keys[name] = keys
        terminal_rows = grid[grid.date.eq(fold["validation_end"])]
        terminal_dates = sorted(terminal_rows.next_trade_date.astype(str).str[:10].unique().tolist())
        if (
            len(terminal_rows) != 150
            or terminal_dates != [fold["terminal_execution_date"]]
            or terminal_rows.next_open.isna().any()
            or terminal_rows.next_close.isna().any()
            or not np.isfinite(terminal_rows[["next_open", "next_close"]].to_numpy(float)).all()
            or (terminal_rows[["next_open", "next_close"]].to_numpy(float) <= 0).any()
        ):
            raise RuntimeError(f"{name} settlement or terminal-mark readiness failed")
        terminal_checks[name] = {
            "last_signal_date": fold["validation_end"],
            "execution_and_mark_date": fold["terminal_execution_date"],
            "terminal_mark_field": "next_close on last signal's next_trade_date",
            "rows_available": len(terminal_rows),
            "complete": True,
        }
    if not outer_keys["outer_1"].merge(outer_keys["outer_2"], on=["date", "instrument"]).empty:
        raise RuntimeError("outer validation keys overlap")
    if len(pd.concat(outer_keys.values()).drop_duplicates()) != 2000:
        raise RuntimeError("outer OOF keys do not uniquely cover development")

    trainer_source = SOURCES["trainer_implementation"].read_text(encoding="utf-8")
    if not all(token in trainer_source for token in ('for fold_name in ("outer_1", "outer_2")', "fit_model(train, features, selected)", "model.predict(valid[features])")):
        raise RuntimeError("outer refit reproducibility path missing from trainer")

    return {
        "verdict": "PASS_PROTOCOL_EXECUTABLE_NO_EVALUATION",
        "development_rows": 2000,
        "development_dates": 40,
        "development_date_range": [development_dates[0], development_dates[-1]],
        "outer_oof_unique_coverage_rows": 2000,
        "outer_oof_overlap_rows": 0,
        "feature_count": 78,
        "model_a_score_parity": True,
        "execution_grid_rows": 6000,
        "execution_grid_dates": 40,
        "terminal_checks": terminal_checks,
        "terminal_2026_09_02_close_allowed_for_development": False,
        "fit_or_predict_performed": False,
        "replay_performed": False,
        "metrics_computed": False,
    }


def build_freeze(readiness: dict[str, Any]) -> dict[str, Any]:
    source_bindings = {
        role: {"path": rel(path), "sha256": sha256(path), "bytes": path.stat().st_size}
        for role, path in SOURCES.items()
    }
    selected_config = json.loads(SOURCES["training_manifest"].read_text(encoding="utf-8"))["selected_config"]
    return {
        "schema_version": "modelb.b19r2r.comparative_freeze.v1",
        "status": "CLOSED_DEVELOPMENT_DIAGNOSTIC_COMPARISON_NOT_AUTHORIZED",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "scope": "Development-only paired A versus A+B diagnostic over outer_1 and outer_2 OOF keys.",
        "implementation_bindings": {
            "freeze_builder": {"path": rel(Path(__file__)), "sha256": sha256(Path(__file__)), "bytes": Path(__file__).stat().st_size},
            "static_validator": {"path": rel(VALIDATOR), "sha256": sha256(VALIDATOR), "bytes": VALIDATOR.stat().st_size},
        },
        "source_bindings": source_bindings,
        "model_roles": {
            "a_only_buy_score": "MODEL_A_FULL_CROSS_SECTION.model_a_raw_score on the frozen development Exact-50 keys",
            "a_plus_b_buy_score": "OOF prediction from fold-specific candidate-14 refit on the same 78F Exact-50 keys",
            "candidate_rank_and_full_qlib_rank": "always frozen Model A; Model B cannot change universe or exit boundary",
            "final_refit_pickle_development_use": "FORBIDDEN_IN_SAMPLE_LEAKAGE",
            "final_refit_pickle_allowed_role": "selected-config lineage and future separately authorized confirmation only",
        },
        "oof_contract": {
            "selected_candidate_id": 14,
            "selected_config": selected_config,
            "folds": OUTER,
            "refit_each_fold_required": True,
            "outer_1_train_rows": 39350,
            "outer_2_train_rows": 39850,
            "validation_key_union_rows": 2000,
            "validation_key_overlap_rows": 0,
            "each_development_key_predicted_once": True,
            "outer_predictions_may_select_or_change_hyperparameters": False,
        },
        "paired_comparison": {
            "same_exact50_keys": True,
            "same_candidate_and_exit_boundary": True,
            "tie_rule": "buy_score descending, instrument ascending",
            "rank_metrics": {
                "ndcg_at_10_label": "relevance_10d_top_heavy_canonical",
                "rank_ic_label": "future_excess_return_10d_canonical",
                "daily_nonfinite_or_constant_spearman": "FAIL_CLOSED",
            },
            "primary_replay": "chronological 40-day OOF stream with one initial portfolio; model changes only at the frozen outer-fold boundary",
            "fold_reports_required": ["outer_1", "outer_2", "combined_development"],
        },
        "execution_contract": {
            "strategy": "top50_exit_one_worst_sell",
            "execution": "next_open",
            "initial_equity": 1000000.0,
            "commission_rate": 0.001425,
            "sell_tax_rate": 0.003,
            "lot_size": 10,
            "target_holdings": 10,
            "daily_max_buy": 1,
            "daily_max_sell": 1,
            "sell_before_buy_and_sell_opens_buy_slot": True,
            "price_fallback_allowed": False,
            "terminal_mark": "next_close on the next_trade_date of each requested window's final signal",
            "terminal_2026_09_02_close_for_development_allowed": False,
            "readiness": readiness["terminal_checks"],
        },
        "preregistered_numeric_quality_gates": NUMERIC_GATES,
        "interpretation": {
            "training_development_overlap_disclosed": True,
            "development_results_are_final_oos_confirmation": False,
            "development_results_may_auto_admit_baseline": False,
            "development_results_role": "readiness and retrospective development diagnostic only",
            "sealed_confirmation_open_requires_new_independent_authorization": True,
            "all_numeric_gates_retained_without_change": True,
        },
        "readiness_precheck": readiness,
        "next_execution_gate": {
            "comparison_execution_authorized": False,
            "evaluator_implementation_and_hash_must_be_frozen": True,
            "independent_review_and_single_execution_authorization_required": True,
        },
        "forbidden": {
            "sealed_embargo_or_confirmation_access": True,
            "final_pickle_development_prediction": True,
            "training_or_tuning": True,
            "comparison_execution_or_prediction": True,
            "replay": True,
            "baseline_latest_provider_frontend_db_production_write": True,
        },
    }


def report_text() -> str:
    return """# B19R2R development-only A 与 A+B 比较协议冻结

状态：`PASS_PROTOCOL_EXECUTABLE_NO_EVALUATION`。本阶段只冻结协议和验证输入可执行性，没有生成预测、指标或回放结果。

## 公平比较

A-only 在冻结 exact50 上使用 Model A `model_a_raw_score`。A+B 必须用 candidate 14 分别在 outer_1 与 outer_2 的各自训练截止日重拟合，然后只预测该 fold 的 validation keys；2,000 个 development keys 必须被 OOF 唯一覆盖一次。最终 `2026-07-06` refit pickle 对 development 是 in-sample，明确禁止用于本次比较。

Model B 只能重排同一 Model A exact50 的买入顺序。`candidate_rank` 和 `full_qlib_rank` 始终来自 Model A，不能改变 universe 或退出边界。

## 执行与结算

比较固定使用 `top50_exit_one_worst_sell`、next-open、初始资金 1,000,000、手续费 0.001425、卖出税 0.003、lot 10、持仓 10、每日最多买卖各 1，且缺价直接阻断。Development grid 足以结算：outer_1 最后信号在 2026-06-08 执行并以当日 next_close 标记；outer_2 在 2026-07-07 执行并标记。禁止使用 `terminal_2026_09_02_close` 做 development 期末估值。

## 解释边界

outer development 与训练流程存在已披露的开发用途，结果只能用于 readiness 和 retrospective diagnostic，不能自动纳入 baseline。原预注册数值门槛全部保留且不可事后修改；一次性打开 sealed confirmation 仍需新的独立审查与授权。

下一阶段必须先实现并冻结比较 evaluator，再获一次独立执行授权。本冻结本身不授权 fit、predict、比较、回放或任何 baseline/latest/provider/frontend/DB/生产写入。
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    args = parser.parse_args()
    if not args.freeze:
        raise SystemExit("Select --freeze")
    if OUT.exists():
        raise RuntimeError("refusing to overwrite comparative freeze directory")
    readiness = inspect_readiness()
    freeze = build_freeze(readiness)
    precheck = {
        "schema_version": "modelb.b19r2r.comparative_static_precheck.v1",
        "verdict": readiness["verdict"],
        "checks": readiness,
        "comparison_executed": False,
        "prediction_generated": False,
        "replay_executed": False,
        "sealed_accessed": False,
    }
    OUT.mkdir(parents=True, exist_ok=False)
    write_once(FREEZE, json.dumps(freeze, indent=2, ensure_ascii=True) + "\n")
    write_once(REPORT, report_text())
    write_once(PRECHECK, json.dumps(precheck, indent=2, ensure_ascii=True) + "\n")
    print(json.dumps({"status": freeze["status"], "verdict": readiness["verdict"], "output": rel(OUT)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
