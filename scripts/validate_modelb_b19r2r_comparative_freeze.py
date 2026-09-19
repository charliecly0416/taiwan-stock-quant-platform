#!/usr/bin/env python3
"""Validate the frozen B19R2R development comparative protocol."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_comparative_evaluation_20260916"
FREEZE = OUT / "B19R2R_COMPARATIVE_FREEZE.json"
PRECHECK = OUT / "B19R2R_COMPARATIVE_STATIC_PRECHECK.json"
BUILDER = ROOT / "scripts/build_modelb_b19r2r_comparative_freeze.py"
FORBIDDEN = ("sealed_embargo", "sealed_confirmation", "EMBARGO_", "CONFIRMATION_")
EXPECTED_GATES = {
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


def check() -> dict[str, bool]:
    checks = {
        "freeze_exists": FREEZE.is_file(),
        "precheck_exists": PRECHECK.is_file(),
        "builder_exists": BUILDER.is_file(),
    }
    if not all(checks.values()):
        return checks
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    precheck = json.loads(PRECHECK.read_text(encoding="utf-8"))
    bindings = freeze.get("source_bindings", {})
    paths = [item.get("path", "") for item in bindings.values()]
    builder_source = BUILDER.read_text(encoding="utf-8")
    tree = ast.parse(builder_source)
    forbidden_calls = {"fit", "fit_model", "predict", "replay", "replay_from_order_intent"}
    called = {
        node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, (ast.Attribute, ast.Name))
    }
    checks.update({
        "freeze_closed": freeze.get("status") == "CLOSED_DEVELOPMENT_DIAGNOSTIC_COMPARISON_NOT_AUTHORIZED",
        "builder_hash": freeze["implementation_bindings"]["freeze_builder"]["sha256"] == sha256(BUILDER),
        "validator_hash": freeze["implementation_bindings"]["static_validator"]["sha256"] == sha256(Path(__file__)),
        "source_paths_unique": len(paths) == len(set(paths)) and len(paths) >= 15,
        "source_hashes_match": all(
            (ROOT / item["path"]).is_file()
            and sha256(ROOT / item["path"]) == item["sha256"]
            and (ROOT / item["path"]).stat().st_size == item["bytes"]
            for item in bindings.values()
        ),
        "sealed_paths_absent": not any(fragment in path for path in paths for fragment in FORBIDDEN),
        "no_fit_predict_replay_calls": not forbidden_calls.intersection(called),
        "oof_unique_coverage": (
            freeze["oof_contract"]["validation_key_union_rows"] == 2000
            and freeze["oof_contract"]["validation_key_overlap_rows"] == 0
            and freeze["oof_contract"]["each_development_key_predicted_once"] is True
        ),
        "final_pickle_leakage_blocked": (
            freeze["model_roles"]["final_refit_pickle_development_use"] == "FORBIDDEN_IN_SAMPLE_LEAKAGE"
            and freeze["oof_contract"]["refit_each_fold_required"] is True
        ),
        "fold_boundaries": (
            freeze["oof_contract"]["folds"]["outer_1"]["train_end"] == "2026-04-22"
            and freeze["oof_contract"]["folds"]["outer_2"]["train_end"] == "2026-05-22"
            and freeze["oof_contract"]["folds"]["outer_1"]["validation_rows"] == 1000
            and freeze["oof_contract"]["folds"]["outer_2"]["validation_rows"] == 1000
        ),
        "model_a_boundary_preserved": "always frozen Model A" in freeze["model_roles"]["candidate_rank_and_full_qlib_rank"],
        "rank_labels_correct": (
            freeze["paired_comparison"]["rank_metrics"]["ndcg_at_10_label"] == "relevance_10d_top_heavy_canonical"
            and freeze["paired_comparison"]["rank_metrics"]["rank_ic_label"] == "future_excess_return_10d_canonical"
            and freeze["paired_comparison"]["rank_metrics"]["daily_nonfinite_or_constant_spearman"] == "FAIL_CLOSED"
        ),
        "execution_contract_exact": freeze["execution_contract"] == {
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
            "readiness": freeze["readiness_precheck"]["terminal_checks"],
        },
        "numeric_gates_unchanged": freeze.get("preregistered_numeric_quality_gates") == EXPECTED_GATES,
        "diagnostic_not_admission": (
            freeze["interpretation"]["training_development_overlap_disclosed"] is True
            and freeze["interpretation"]["development_results_are_final_oos_confirmation"] is False
            and freeze["interpretation"]["development_results_may_auto_admit_baseline"] is False
            and freeze["interpretation"]["sealed_confirmation_open_requires_new_independent_authorization"] is True
        ),
        "readiness_pass_without_evaluation": (
            precheck.get("verdict") == "PASS_PROTOCOL_EXECUTABLE_NO_EVALUATION"
            and precheck.get("comparison_executed") is False
            and precheck.get("prediction_generated") is False
            and precheck.get("replay_executed") is False
            and precheck.get("sealed_accessed") is False
        ),
        "execution_still_unauthorized": freeze["next_execution_gate"]["comparison_execution_authorized"] is False,
        "production_writes_forbidden": freeze["forbidden"]["baseline_latest_provider_frontend_db_production_write"] is True,
    })
    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if not args.validate:
        raise SystemExit("Select --validate")
    checks = check()
    verdict = "PASS" if checks and all(checks.values()) else "HOLD"
    print(json.dumps({"checks": checks, "verdict": verdict}, indent=2, ensure_ascii=False))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
