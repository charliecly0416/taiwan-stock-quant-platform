#!/usr/bin/env python3
"""Read-only post-output validator repair for the frozen V2 comparison output.

This validator does not replace the V2 frozen validator.  It preserves the
original HOLD and changes only three scoped CSV round-trip comparisons documented by
the post-output incident record.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_comparative_evaluation_20260916"
PROTOCOL = RUN / "B19R2R_COMPARATIVE_FREEZE.json"
ADAPTER = RUN / "B19R2R_COMPARATIVE_FREEZE_AMENDMENT_01.json"
FREEZE = RUN / "B19R2R_COMPARATIVE_IMPLEMENTATION_FREEZE_V2.json"
AUTH = RUN / "B19R2R_COMPARATIVE_EXECUTION_AUTHORIZATION_V2.json"
OUTPUT = RUN / "evaluation_output_v2"
EVALUATOR = ROOT / "scripts/run_modelb_b19r2r_development_comparison.py"
OLD_VALIDATOR = ROOT / "scripts/validate_modelb_b19r2r_development_comparison.py"
REPAIR_FREEZE = RUN / "B19R2R_POST_OUTPUT_VALIDATOR_REPAIR_FREEZE.json"
REPAIR_AUTH = RUN / "B19R2R_POST_OUTPUT_VALIDATOR_REPAIR_AUTHORIZATION.json"
INCIDENT = RUN / "B19R2R_POST_OUTPUT_VALIDATOR_HOLD_DIAGNOSTIC.json"
INITIAL = 1_000_000.0
MODEL_A_SCORE_PARITY_RTOL = 0.0
MODEL_A_SCORE_PARITY_ATOL = 1e-15
EXECUTION_PRICE_CSV_ROUNDTRIP_ATOL = 1e-12
RECONCILIATION_CSV_ROUNDTRIP_ATOL = 1e-6
KEY = ["date", "instrument"]
SCOPES = {"combined_development": 40, "outer_1": 20, "outer_2": 20}
METHODS = {"A_ONLY", "A_PLUS_B"}
RESERVED = {
    "confirmation_after_cost_return_delta_b_minus_a",
    "confirmation_paired_moving_block_bootstrap_95pct_lower_bound",
}
FORBIDDEN_PATH_TOKENS = ("sealed_embargo", "sealed_confirmation", "EMBARGO_", "CONFIRMATION_")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def close(left: Any, right: Any, *, tolerance: float = 1e-12) -> bool:
    try:
        return math.isclose(float(left), float(right), rel_tol=tolerance, abs_tol=tolerance)
    except (TypeError, ValueError):
        return False


def execution_price_roundtrip_matches(serialized: Any, frozen: Any) -> bool:
    """Compare CSV-decoded prices to frozen float64 prices after text round-trip."""
    return bool(np.allclose(
        serialized,
        frozen,
        rtol=0.0,
        atol=EXECUTION_PRICE_CSV_ROUNDTRIP_ATOL,
    ))


def reconciliation_roundtrip_matches(serialized: Any, recomputed: Any) -> bool:
    """Require both reconciliation residuals and their CSV delta within 1e-6."""
    try:
        serialized_value = float(serialized)
        recomputed_value = float(recomputed)
    except (TypeError, ValueError):
        return False
    return bool(
        math.isfinite(serialized_value)
        and math.isfinite(recomputed_value)
        and abs(serialized_value) <= RECONCILIATION_CSV_ROUNDTRIP_ATOL
        and abs(recomputed_value) <= RECONCILIATION_CSV_ROUNDTRIP_ATOL
        and abs(serialized_value - recomputed_value) <= RECONCILIATION_CSV_ROUNDTRIP_ATOL
    )


def model_a_score_roundtrip_matches(serialized: Any, canonical: Any) -> bool:
    """Apply the already-frozen Model A score parity tolerance after CSV I/O."""
    return bool(np.isclose(
        serialized,
        canonical,
        rtol=MODEL_A_SCORE_PARITY_RTOL,
        atol=MODEL_A_SCORE_PARITY_ATOL,
    ).all())


def finite_ratio(numerator: float, denominator: float) -> tuple[float | None, str | None]:
    if not math.isfinite(numerator) or not math.isfinite(denominator):
        return None, "NONFINITE_RATIO_INPUT"
    if denominator == 0:
        return None, "ZERO_DENOMINATOR_FAIL_GATE"
    return float(numerator / denominator), None


def compare(actual: Any, operator: str, threshold: Any) -> bool:
    if isinstance(actual, (bool, np.bool_)):
        return bool(actual) is bool(threshold)
    if operator == "==" and (isinstance(actual, str) or isinstance(threshold, str)):
        return actual == threshold
    if actual is None or not math.isfinite(float(actual)):
        return False
    if operator == ">":
        return float(actual) > float(threshold)
    if operator == ">=":
        return float(actual) >= float(threshold)
    if operator == "<=":
        return float(actual) <= float(threshold)
    if operator == "==":
        return actual == threshold
    raise RuntimeError(f"unsupported gate operator: {operator}")


def csv_bool(value: Any) -> bool | None:
    if pd.isna(value):
        return None
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    text = str(value).strip().lower()
    if text == "true":
        return True
    if text == "false":
        return False
    raise RuntimeError(f"invalid serialized boolean: {value!r}")


def protocol_checks(*, pristine: bool) -> dict[str, bool]:
    checks = {
        "freeze_exists": FREEZE.is_file(),
        "protocol_exists": PROTOCOL.is_file(),
        "adapter_exists": ADAPTER.is_file(),
        "evaluator_exists": EVALUATOR.is_file(),
        "old_validator_exists": OLD_VALIDATOR.is_file(),
        "repair_freeze_exists": REPAIR_FREEZE.is_file(),
        "incident_exists": INCIDENT.is_file(),
    }
    if not all(checks.values()):
        return checks
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    repair_freeze = json.loads(REPAIR_FREEZE.read_text(encoding="utf-8"))
    source = EVALUATOR.read_text(encoding="utf-8")
    ast.parse(source)
    source_bindings = freeze.get("source_bindings", {})
    paths = [item.get("path", "") for item in source_bindings.values()]
    bootstrap = freeze.get("bootstrap_contract", {})
    reserved = freeze.get("confirmation_only_reserved_gates", {})
    v1_failure = freeze.get("v1_failure_disposition", {})
    output_mkdir_after_compute = (
        source.index("OUTPUT.mkdir(parents=True, exist_ok=False)")
        > source.rindex("build_gate_table(protocol, paired, combined_nav, rank_summary, signals)")
    )
    checks.update({
        "freeze_closed": freeze.get("status") == "CLOSED_BEFORE_COMPARATIVE_EXECUTION",
        "freeze_v2_identity": (
            freeze.get("schema_version") == "modelb.b19r2r.comparative_implementation_freeze.v2"
            and freeze.get("execution_contract", {}).get("namespace") == "V2"
        ),
        "v1_failure_bound_no_retry": (
            v1_failure.get("v1_authorization_consumed") is True
            and v1_failure.get("v1_retry_allowed") is False
            and v1_failure.get("v2_namespace_required") is True
            and (ROOT / v1_failure.get("failure_report_path", "missing")).is_file()
            and sha256(ROOT / v1_failure.get("failure_report_path", "missing")) == v1_failure.get("failure_report_sha256")
        ),
        "all_implementation_hashes": all(
            (ROOT / item["path"]).is_file() and sha256(ROOT / item["path"]) == item["sha256"]
            for item in freeze.get("implementation_bindings", {}).values()
        ),
        "evaluator_hash": freeze["implementation_bindings"]["evaluator"]["sha256"] == sha256(EVALUATOR),
        "old_validator_hash": freeze["implementation_bindings"]["validator"]["sha256"] == sha256(OLD_VALIDATOR),
        "repair_freeze_identity": (
            repair_freeze.get("schema_version") == "modelb.b19r2r.post_output_validator_repair_freeze.v1"
            and repair_freeze.get("status") == "FROZEN_AWAITING_INDEPENDENT_READONLY_VALIDATION_AUTHORIZATION"
        ),
        "repair_freeze_v2_bindings": (
            repair_freeze.get("v2_implementation_freeze", {}).get("sha256") == sha256(FREEZE)
            and repair_freeze.get("v2_execution_authorization", {}).get("sha256") == sha256(AUTH)
            and repair_freeze.get("old_validator", {}).get("sha256") == sha256(OLD_VALIDATOR)
            and repair_freeze.get("output_manifest", {}).get("sha256") == sha256(OUTPUT / "MANIFEST.json")
            and repair_freeze.get("hold_diagnostic", {}).get("sha256") == sha256(INCIDENT)
        ),
        "repair_validator_hash": repair_freeze.get("repair_validator", {}).get("sha256") == sha256(Path(__file__)),
        "repair_is_validator_only": (
            repair_freeze.get("repair_scope", {}).get("evaluator_changed") is False
            and repair_freeze.get("repair_scope", {}).get("evaluation_output_changed") is False
            and repair_freeze.get("repair_scope", {}).get("gate_threshold_changed") is False
        ),
        "source_hashes": all(
            (ROOT / item["path"]).is_file() and sha256(ROOT / item["path"]) == item["sha256"]
            for item in source_bindings.values()
        ),
        "no_sealed_paths": not any(token in path for path in paths for token in FORBIDDEN_PATH_TOKENS),
        "no_final_pickle_path": "MODEL_B_B19R2R_LGBM_RANKER.pkl" not in source and "joblib" not in source,
        "outer_refit_static": all(token in source for token in (
            '"outer_1": ("2026-04-22"', '"outer_2": ("2026-05-22"',
            "fit_ranker(train, features, config)",
            "expected_train_rows = 39350 if fold == \"outer_1\" else 39850",
        )),
        "oof_prediction_static": "model.predict(valid[features])" in source and "oof.duplicated(KEY).any()" in source,
        "model_a_keyset_source_parity_static": all(token in source for token in (
            '"model_a_raw_score": "keyset_model_a_raw_score"',
            '"full_qlib_rank": "keyset_full_qlib_rank"',
            "MODEL_A_SCORE_PARITY_RTOL = 0.0",
            "MODEL_A_SCORE_PARITY_ATOL = 1e-15",
            "score_max_abs_diff",
            "score_bitwise_mismatch_count",
            "score_tolerance_failure_count",
            "np.array_equal(keyset_rank, canonical_rank)",
        )),
        "full_source_then_development_filter_static": all(token in source for token in (
            "len(model_a_source) != 12000", "model_a_source.date.nunique() != 80",
            "len(model_a) != 6000", "model_a.date.nunique() != 40",
            "len(feature_source) != 12000", "len(development_features) != 6000",
            "len(key_source) != 4000", "len(development_keys) != 2000",
            "len(development_labels) != 2000", "len(grid) != 6000",
        )),
        "finite_score_rank_metric_static": all(token in source for token in (
            "nonfinite canonical Model A score",
            "not np.isfinite(oof.model_b_oof_raw_score).all()",
            "nonfinite rank metric input",
            "nonfinite NDCG@10 output",
        )),
        "rank_metrics_static": all(token in source for token in (
            "spearmanr(score, continuous)",
            "ndcg_score(relevance[None, :], score[None, :], k=10)",
            "summarize_rank_metrics",
        )),
        "constant_rankic_fail_closed": "nonfinite or constant daily RankIC" in source,
        "paired_methods_static": '("A_ONLY", "a_only_buy_score")' in source and '("A_PLUS_B", "a_plus_b_buy_score")' in source,
        "execution_constants": all(token in source for token in (
            "INITIAL = 1_000_000.0", "FEE = 0.001425", "TAX = 0.003", "LOT = 10", "TARGET = 10",
        )),
        "every_day_nav_static": "Every signal day gets an exact next-close NAV mark" in source and "len(nav) != len(signal_days)" in source,
        "no_fallback_static": "missing next_open; no fallback" in source and '"fallback_used": False' in source,
        "terminal_next_close_static": "terminal_2026_09_02_close" not in source and "next_close" in source,
        "reconciliation_static": "PnL contribution does not reconcile" in source,
        "initial_equity_drawdown_static": "peaks = np.maximum.accumulate(np.r_[INITIAL, equity_values])[1:]" in source,
        "scoped_summaries_static": all(token in source for token in ('"scope": scope', "RANK_METRICS_SUMMARY.csv", "PAIRED_METRICS.csv")),
        "deep_gate_computation_static": all(token in source for token in (
            "monthly_outperformance_fraction", "negative_twii20_regime_return_delta",
            "rank_ic_delta_b_minus_a", "ndcg_at_10_delta_b_minus_a",
            "ZERO_DENOMINATOR_FAIL_GATE", "development_applicable_gate_verdict",
        )),
        "confirmation_reserved_static": "RESERVED_FOR_CONFIRMATION_NOT_EVALUATED" in source,
        "monthly_signal_date_static": 'paired_daily["month"] = paired_daily.signal_date.str[:7]' in source,
        "no_development_bootstrap_static": "development_bootstrap_performed\": False" in source and "default_rng" not in source and "PCG64" not in source,
        "freeze_confirmation_bootstrap_exact": (
            bootstrap.get("scope") == "sealed_confirmation_only"
            and bootstrap.get("series_length") == 30
            and bootstrap.get("block_length") == 10
            and bootstrap.get("valid_start_indices_inclusive") == [0, 20]
            and bootstrap.get("blocks_per_replication") == 3
            and bootstrap.get("development_bootstrap_allowed") is False
        ),
        "freeze_reserved_gate_split": set(reserved).issuperset(RESERVED) and reserved.get("development_admission_effect") == "NONE",
        "write_once_guard": "if OUTPUT.exists()" in source and "OUTPUT.mkdir(parents=True, exist_ok=False)" in source,
        "output_created_only_after_successful_computation": output_mkdir_after_compute,
        "authorization_bound": "implementation_freeze_sha256" in source and "attempts_authorized" in source,
        "preflight_mode_present": "--preflight-no-write" in source and "authorization_absent" in source,
        "execution_unauthorized_at_freeze": freeze["safety_at_close"]["comparison_execution_authorized"] is False,
        "production_forbidden": freeze["safety_at_close"]["baseline_or_production_write_authorized"] is False,
        "price_tolerance_scoped": (
            EXECUTION_PRICE_CSV_ROUNDTRIP_ATOL == 1e-12
            and "execution_price_roundtrip_matches" in Path(__file__).read_text(encoding="utf-8")
        ),
        "reconciliation_tolerance_scoped": (
            RECONCILIATION_CSV_ROUNDTRIP_ATOL == 1e-6
            and "reconciliation_roundtrip_matches" in Path(__file__).read_text(encoding="utf-8")
        ),
        "model_a_score_tolerance_scoped_to_frozen_parity": (
            MODEL_A_SCORE_PARITY_RTOL == 0.0
            and MODEL_A_SCORE_PARITY_ATOL == 1e-15
            and "model_a_score_roundtrip_matches" in Path(__file__).read_text(encoding="utf-8")
        ),
    })
    if pristine:
        checks.update({
            "v2_auth_present": AUTH.is_file(),
            "output_present": OUTPUT.is_dir(),
            "repair_auth_absent": not REPAIR_AUTH.exists(),
        })
    else:
        checks.update({
            "v2_auth_present": AUTH.is_file(),
            "output_present": OUTPUT.is_dir(),
            "repair_auth_present": REPAIR_AUTH.is_file(),
        })
        if REPAIR_AUTH.is_file():
            auth = json.loads(REPAIR_AUTH.read_text(encoding="utf-8"))
            checks["repair_authorization_single_bound_readonly_validation"] = (
                auth.get("authorized") is True
                and auth.get("attempts_authorized") == 1
                and auth.get("repair_freeze_sha256") == sha256(REPAIR_FREEZE)
                and auth.get("repair_validator_sha256") == sha256(Path(__file__))
                and auth.get("output_manifest_sha256") == sha256(OUTPUT / "MANIFEST.json")
                and auth.get("authorization_scope") == "ONE_READONLY_POST_OUTPUT_VALIDATION_ATTEMPT"
            )
    return checks


def artifact_frame(manifest: dict[str, Any], name: str) -> pd.DataFrame:
    item = manifest["artifacts"][name]
    path = ROOT / item["path"]
    if not path.is_file() or sha256(path) != item["sha256"] or path.stat().st_size != item["bytes"]:
        raise RuntimeError(f"artifact binding failed: {name}")
    frame = pd.read_csv(path)
    if len(frame) != item["rows"]:
        raise RuntimeError(f"artifact row count failed: {name}")
    return frame


def recompute_summary(actions: pd.DataFrame, nav: pd.DataFrame, contribution: pd.DataFrame) -> dict[str, Any]:
    buys = actions[actions.action.eq("buy")]
    sells = actions[actions.action.eq("sell")]
    notionals = float((actions.quantity * actions.execution_price).sum())
    absolute = contribution.total_contribution.abs()
    denominator = float(absolute.sum())
    shares = absolute / denominator if math.isfinite(denominator) and denominator > 0 else pd.Series(dtype=float)
    reconciliation = float(contribution.total_contribution.sum() - (nav.equity.iloc[-1] - INITIAL))
    return {
        "final_equity": float(nav.equity.iloc[-1]),
        "net_return": float(nav.equity.iloc[-1] / INITIAL - 1.0),
        "max_drawdown": float((nav.equity.to_numpy(float) / np.maximum.accumulate(np.r_[INITIAL, nav.equity.to_numpy(float)])[1:] - 1.0).min()),
        "turnover": notionals / INITIAL,
        "buy_count": int(len(buys)), "sell_count": int(len(sells)), "action_count": int(len(actions)),
        "commission": float(actions.commission.sum()), "sell_tax": float(actions.sell_tax.sum()),
        "fee_tax": float(actions.commission.sum() + actions.sell_tax.sum()),
        "contribution_denominator": denominator,
        "contribution_denominator_valid": bool(math.isfinite(denominator) and denominator > 0),
        "top1_abs_contribution_share": float(shares.nlargest(1).sum()) if len(shares) else None,
        "top5_abs_contribution_share": float(shares.nlargest(5).sum()) if len(shares) else None,
        "abs_contribution_hhi": float((shares**2).sum()) if len(shares) else None,
        "fallback_count": int(nav.fallback_count.sum()), "pending_count": int(nav.pending_count.sum()),
        "emitted_action_count": int(nav.emitted_action_count.sum()),
        "executed_action_count": int(nav.executed_action_count.sum()),
        "all_actions_executed": bool(
            len(actions) == int(nav.emitted_action_count.sum())
            and actions.status.eq("EXECUTED").all() and actions.quantity.gt(0).all()
        ),
        "reconciliation_delta": reconciliation,
    }


def validate_replay_artifacts(
    manifest: dict[str, Any], paired: pd.DataFrame, grid: pd.DataFrame,
) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[str, pd.DataFrame]]:
    summaries: dict[tuple[str, str], dict[str, Any]] = {}
    combined_nav: dict[str, pd.DataFrame] = {}
    grid = grid.copy()
    grid["date"] = grid.date.astype(str).str[:10]
    grid["instrument"] = grid.instrument.astype(str).str.upper()
    if len(grid) != 6000 or grid.duplicated(KEY).any() or grid.groupby("date").size().ne(150).any():
        raise RuntimeError("frozen execution grid shape failed")
    daily_execution = grid.groupby("date").next_trade_date.agg(lambda values: sorted(set(str(v)[:10] for v in values)))
    if daily_execution.map(len).ne(1).any():
        raise RuntimeError("execution grid has ambiguous next trade date")
    for scope, expected_days in SCOPES.items():
        for method in sorted(METHODS):
            prefix = f"{scope}_{method}"
            actions = artifact_frame(manifest, f"{prefix}_ACTIONS.csv")
            nav = artifact_frame(manifest, f"{prefix}_DAILY_NAV.csv")
            audit = artifact_frame(manifest, f"{prefix}_PRICE_AUDIT.csv")
            contribution = artifact_frame(manifest, f"{prefix}_CONTRIBUTION.csv")
            if (
                set(nav.scope) != {scope} or set(nav.method) != {method}
                or len(nav) != expected_days or nav.signal_date.nunique() != expected_days
                or nav.signal_date.duplicated().any()
                or nav[["cash", "market_value", "equity", "daily_return", "drawdown"]].isna().any().any()
                or not np.isfinite(nav[["cash", "market_value", "equity", "daily_return", "drawdown"]].to_numpy(float)).all()
                or not np.allclose(nav.equity, nav.cash + nav.market_value, rtol=0.0, atol=1e-8)
            ):
                raise RuntimeError(f"daily NAV contract failed: {prefix}")
            expected_execution_dates = nav.signal_date.map(lambda day: daily_execution.loc[day][0])
            if not nav.date.astype(str).str[:10].reset_index(drop=True).equals(expected_execution_dates.reset_index(drop=True)):
                raise RuntimeError(f"daily NAV execution dates failed: {prefix}")
            expected_returns = nav.equity.pct_change().fillna(nav.equity.iloc[0] / INITIAL - 1.0)
            equity_values = nav.equity.to_numpy(float)
            expected_drawdown = equity_values / np.maximum.accumulate(np.r_[INITIAL, equity_values])[1:] - 1.0
            if not np.allclose(nav.daily_return, expected_returns, rtol=0.0, atol=1e-12) or not np.allclose(nav.drawdown, expected_drawdown, rtol=0.0, atol=1e-12):
                raise RuntimeError(f"daily return/drawdown recomputation failed: {prefix}")
            buy_max = actions.groupby("signal_date").action.apply(lambda values: values.eq("buy").sum()).max()
            sell_max = actions.groupby("signal_date").action.apply(lambda values: values.eq("sell").sum()).max()
            if (
                set(actions.scope) != {scope} or set(actions.method) != {method}
                or not actions.status.eq("EXECUTED").all() or not actions.quantity.gt(0).all()
                or int(nav.emitted_action_count.sum()) != len(actions)
                or int(nav.executed_action_count.sum()) != len(actions)
                or int(nav.pending_count.sum()) != 0 or int(nav.fallback_count.sum()) != 0
                or buy_max > 1 or sell_max > 1
            ):
                raise RuntimeError(f"action completeness failed: {prefix}")
            if len(audit) != len(actions) or (len(audit) and audit.fallback_used.map(csv_bool).ne(False).any()):
                raise RuntimeError(f"price audit completeness failed: {prefix}")
            action_prices = actions.merge(
                grid[["date", "instrument", "next_trade_date", "next_open"]],
                left_on=["signal_date", "instrument"], right_on=["date", "instrument"],
                validate="many_to_one", suffixes=("", "_grid"),
            )
            if (
                not execution_price_roundtrip_matches(action_prices.execution_price, action_prices.next_open)
                or not action_prices.execution_date.astype(str).str[:10].reset_index(drop=True).equals(
                    action_prices.next_trade_date.astype(str).str[:10].reset_index(drop=True)
                )
            ):
                raise RuntimeError(f"frozen next-open execution mismatch: {prefix}")
            summary = recompute_summary(actions, nav, contribution)
            row = paired[(paired.scope == scope) & (paired.method == method)]
            if len(row) != 1:
                raise RuntimeError(f"paired summary identity failed: {prefix}")
            row = row.iloc[0]
            for field, actual in summary.items():
                serialized = row[field]
                if isinstance(actual, bool):
                    matches = csv_bool(serialized) is actual
                elif actual is None:
                    matches = pd.isna(serialized)
                elif isinstance(actual, int):
                    matches = int(serialized) == actual
                elif field == "reconciliation_delta":
                    matches = reconciliation_roundtrip_matches(serialized, actual)
                else:
                    matches = close(serialized, actual)
                if not matches:
                    raise RuntimeError(f"paired summary mismatch: {prefix} {field}")
            if abs(summary["reconciliation_delta"]) > 1e-6:
                raise RuntimeError(f"contribution reconciliation failed: {prefix}")
            summaries[(scope, method)] = summary
            if scope == "combined_development":
                combined_nav[method] = nav
    return summaries, combined_nav


def deep_output_checks() -> tuple[dict[str, bool], dict[str, Any]]:
    manifest_path = OUTPUT / "MANIFEST.json"
    checks = {"manifest_exists": manifest_path.is_file()}
    details: dict[str, Any] = {}
    if not manifest_path.is_file():
        return checks, details
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks.update({
        "schema_v2": manifest.get("schema_version") == "modelb.b19r2r.development_comparison.v2",
        "status": manifest.get("status") == "DEVELOPMENT_DIAGNOSTIC_AWAITING_INDEPENDENT_REVIEW",
        "oof_shape_manifest": manifest.get("oof_rows") == 2000 and manifest.get("oof_dates") == 40,
        "scope_manifest": manifest.get("paired_metric_rows") == 6 and manifest.get("paired_metric_identity") == "scope+method",
        "model_a_parity_manifest_present": isinstance(manifest.get("model_a_keyset_source_parity"), dict),
        "confirmation_reserved_manifest": set(manifest.get("confirmation_only_gates_reserved", [])) == RESERVED,
        "confirmation_not_adjudicated": manifest.get("confirmation_all_joint_verdict") == "NOT_EVALUATED",
        "development_bootstrap_not_performed": manifest.get("development_bootstrap_performed") is False,
        "final_pickle_not_used": manifest.get("final_pickle_used_for_development") is False,
        "safety": manifest.get("sealed_accessed") is False and manifest.get("baseline_admission_decided") is False and manifest.get("production_write_performed") is False,
        "artifact_hashes": all(
            (ROOT / item["path"]).is_file() and sha256(ROOT / item["path"]) == item["sha256"]
            and (ROOT / item["path"]).stat().st_size == item["bytes"]
            for item in manifest.get("artifacts", {}).values()
        ),
    })
    required_artifacts = {
        "OOF_SCORES.csv", "SIGNALS.csv", "RANK_METRICS_DAILY.csv", "RANK_METRICS_SUMMARY.csv",
        "PAIRED_METRICS.csv", "GATE_TABLE.csv", "PAIRED_DAILY_RETURNS.csv", "MONTHLY_DIAGNOSTICS.csv",
    }
    for scope in SCOPES:
        for method in METHODS:
            required_artifacts.update({
                f"{scope}_{method}_ACTIONS.csv", f"{scope}_{method}_DAILY_NAV.csv",
                f"{scope}_{method}_PRICE_AUDIT.csv", f"{scope}_{method}_CONTRIBUTION.csv",
            })
    checks["required_artifacts"] = required_artifacts.issubset(manifest.get("artifacts", {}))
    if not all(checks.values()):
        return checks, details

    oof = artifact_frame(manifest, "OOF_SCORES.csv")
    signals = artifact_frame(manifest, "SIGNALS.csv")
    rank_daily = artifact_frame(manifest, "RANK_METRICS_DAILY.csv")
    rank_summary = artifact_frame(manifest, "RANK_METRICS_SUMMARY.csv")
    paired = artifact_frame(manifest, "PAIRED_METRICS.csv")
    gate_table = artifact_frame(manifest, "GATE_TABLE.csv")
    paired_daily_file = artifact_frame(manifest, "PAIRED_DAILY_RETURNS.csv")
    monthly_file = artifact_frame(manifest, "MONTHLY_DIAGNOSTICS.csv")
    expected_identity = {(scope, method) for scope in SCOPES for method in METHODS}
    checks.update({
        "oof_unique_coverage": (
            len(oof) == 2000 and oof.date.nunique() == 40 and not oof.duplicated(KEY).any()
            and oof.groupby("fold").size().to_dict() == {"outer_1": 1000, "outer_2": 1000}
            and set(oof[oof.fold.eq("outer_1")].train_end) == {"2026-04-22"}
            and set(oof[oof.fold.eq("outer_2")].train_end) == {"2026-05-22"}
            and np.isfinite(oof.model_b_oof_raw_score.to_numpy(float)).all()
        ),
        "signals_unique_same_keys": (
            len(signals) == 2000 and not signals.duplicated(KEY).any()
            and signals[KEY].sort_values(KEY).reset_index(drop=True).equals(oof[KEY].sort_values(KEY).reset_index(drop=True))
            and np.array_equal(signals.a_plus_b_buy_score.to_numpy(float), signals.model_b_oof_raw_score.to_numpy(float))
            and np.array_equal(signals.a_only_buy_score.to_numpy(float), signals.model_a_raw_score.to_numpy(float))
            and np.isfinite(signals[[
                "model_a_raw_score", "model_b_oof_raw_score", "a_only_buy_score", "a_plus_b_buy_score",
                "full_qlib_rank", "relevance_10d_top_heavy_canonical", "future_excess_return_10d_canonical",
            ]].to_numpy(float)).all()
        ),
        "paired_scope_identity": set(map(tuple, paired[["scope", "method"]].to_numpy())) == expected_identity and len(paired) == 6,
        "rank_scope_identity": set(map(tuple, rank_summary[["scope", "method"]].to_numpy())) == expected_identity and len(rank_summary) == 6,
        "rank_daily_identity": (
            len(rank_daily) == 80
            and not rank_daily.duplicated(["date", "method"]).any()
            and np.isfinite(rank_daily[["rank_ic_continuous", "ndcg_at_10"]].to_numpy(float)).all()
        ),
    })
    if not all(checks.values()):
        return checks, details

    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    model_a_path = ROOT / freeze["source_bindings"]["model_a_development_scores"]["path"]
    keyset_path = ROOT / freeze["source_bindings"]["development_exact50_keys"]["path"]
    feature_path = ROOT / freeze["source_bindings"]["development_features_78f"]["path"]
    label_path = ROOT / freeze["source_bindings"]["development_exact50_labels"]["path"]
    grid_path = ROOT / freeze["source_bindings"]["development_execution_grid"]["path"]
    model_a = pd.read_parquet(model_a_path, columns=KEY + ["model_a_raw_score", "full_qlib_rank"])
    model_a["date"] = model_a.date.astype(str).str[:10]
    model_a["instrument"] = model_a.instrument.astype(str).str.upper()
    if (
        len(model_a) != 12000 or model_a.date.nunique() != 80 or model_a.duplicated(KEY).any()
        or model_a.groupby("date").size().ne(150).any()
        or not np.isfinite(model_a[["model_a_raw_score", "full_qlib_rank"]].to_numpy(float)).all()
    ):
        raise RuntimeError("V2 full Model A source shape failed")
    development_model_a = model_a[model_a.date.between("2026-05-11", "2026-07-06")].copy()
    if len(development_model_a) != 6000 or development_model_a.date.nunique() != 40 or development_model_a.groupby("date").size().ne(150).any():
        raise RuntimeError("V2 filtered Model A development shape failed")
    keyset = pd.read_csv(keyset_path)
    keyset["date"] = keyset.date.astype(str).str[:10]
    keyset["instrument"] = keyset.instrument.astype(str).str.upper()
    if len(keyset) != 4000 or keyset.date.nunique() != 80 or keyset.duplicated(KEY).any() or keyset.groupby("date").size().ne(50).any():
        raise RuntimeError("V2 full Exact-50 key source shape failed")
    keyset = keyset[keyset.date.between("2026-05-11", "2026-07-06")].copy().rename(columns={
        "model_a_raw_score": "keyset_model_a_raw_score",
        "full_qlib_rank": "keyset_full_qlib_rank",
    })
    if len(keyset) != 2000 or keyset.date.nunique() != 40 or keyset.groupby("date").size().ne(50).any():
        raise RuntimeError("V2 filtered Exact-50 development shape failed")
    feature_source = pd.read_parquet(feature_path, columns=KEY + ["feature_raw_complete_78"])
    feature_source["date"] = feature_source.date.astype(str).str[:10]
    feature_source["instrument"] = feature_source.instrument.astype(str).str.upper()
    development_features = feature_source[feature_source.date.between("2026-05-11", "2026-07-06")]
    labels = pd.read_parquet(label_path, columns=KEY + ["label_complete"])
    labels["date"] = labels.date.astype(str).str[:10]
    labels["instrument"] = labels.instrument.astype(str).str.upper()
    checks["v2_full_and_filtered_source_shapes"] = (
        len(feature_source) == 12000 and feature_source.date.nunique() == 80
        and not feature_source.duplicated(KEY).any() and feature_source.groupby("date").size().eq(150).all()
        and len(development_features) == 6000 and development_features.date.nunique() == 40
        and development_features.groupby("date").size().eq(150).all()
        and len(labels) == 2000 and labels.date.nunique() == 40
        and not labels.duplicated(KEY).any() and labels.groupby("date").size().eq(50).all()
    )
    keyset_source = keyset.merge(development_model_a, on=KEY, validate="one_to_one")
    keyset_score = keyset_source.keyset_model_a_raw_score.to_numpy(float)
    canonical_score = keyset_source.model_a_raw_score.to_numpy(float)
    score_close = np.isclose(
        keyset_score,
        canonical_score,
        rtol=MODEL_A_SCORE_PARITY_RTOL,
        atol=MODEL_A_SCORE_PARITY_ATOL,
    )
    score_max_abs_diff = float(np.max(np.abs(keyset_score - canonical_score)))
    rank_exact = np.array_equal(
        keyset_source.keyset_full_qlib_rank.to_numpy(float),
        keyset_source.full_qlib_rank.to_numpy(float),
    )
    parity = manifest["model_a_keyset_source_parity"]
    checks["keyset_canonical_model_a_parity_recomputed"] = (
        len(keyset_source) == 2000
        and not keyset_source.duplicated(KEY).any()
        and keyset_source.groupby("date").size().eq(50).all()
        and keyset_source.groupby("date").eligible_candidate_rank.nunique().eq(50).all()
        and keyset_source.eligible_candidate_rank.between(1, 50).all()
        and np.isfinite(keyset_source[["keyset_model_a_raw_score", "model_a_raw_score", "keyset_full_qlib_rank", "full_qlib_rank"]].to_numpy(float)).all()
        and score_close.all()
        and rank_exact
        and parity.get("rows") == 2000
        and parity.get("canonical_score_source") == freeze["source_bindings"]["model_a_development_scores"]["path"]
        and parity.get("keyset_score_audit_source") == freeze["source_bindings"]["development_exact50_keys"]["path"]
        and parity.get("score_rtol") == MODEL_A_SCORE_PARITY_RTOL
        and parity.get("score_atol") == MODEL_A_SCORE_PARITY_ATOL
        and parity.get("score_bitwise_mismatch_count") == int(np.sum(keyset_score != canonical_score))
        and parity.get("score_tolerance_failure_count") == int((~score_close).sum())
        and close(parity.get("score_max_abs_diff"), score_max_abs_diff)
        and parity.get("full_qlib_rank_exact_match") is True
        and parity.get("full_qlib_rank_semantics") == "canonical frozen Model A full-cross-section rank; keyset copy must match exactly"
        and parity.get("eligible_candidate_rank_semantics") == "Exact-50 membership/order audit only; it does not replace full_qlib_rank"
    )
    signal_source = signals[KEY + ["model_a_raw_score", "full_qlib_rank"]].merge(
        development_model_a, on=KEY, validate="one_to_one", suffixes=("", "_source"),
    )
    checks["model_a_score_and_rank_source_parity"] = (
        model_a_score_roundtrip_matches(
            signal_source.model_a_raw_score.to_numpy(float),
            signal_source.model_a_raw_score_source.to_numpy(float),
        )
        and np.array_equal(signal_source.full_qlib_rank.to_numpy(float), signal_source.full_qlib_rank_source.to_numpy(float))
        and np.array_equal(signals.model_a_raw_score.to_numpy(float), signals.qlib_score_raw.to_numpy(float))
        and close(parity.get("canonical_model_a_feature_score_max_abs_diff"), 0.0)
    )
    for scope, expected_days in SCOPES.items():
        source = rank_daily if scope == "combined_development" else rank_daily[rank_daily.fold.eq(scope)]
        recomputed = source.groupby("method").agg(
            date_count=("date", "nunique"), mean_rank_ic_continuous=("rank_ic_continuous", "mean"),
            mean_ndcg_at_10=("ndcg_at_10", "mean"),
        )
        for method in METHODS:
            row = rank_summary[(rank_summary.scope == scope) & (rank_summary.method == method)].iloc[0]
            if (
                int(row.date_count) != expected_days or int(row.date_count) != int(recomputed.loc[method, "date_count"])
                or not close(row.mean_rank_ic_continuous, recomputed.loc[method, "mean_rank_ic_continuous"])
                or not close(row.mean_ndcg_at_10, recomputed.loc[method, "mean_ndcg_at_10"])
            ):
                raise RuntimeError(f"rank summary recomputation failed: {scope} {method}")
    checks["rank_summary_recomputed"] = True

    grid = pd.read_parquet(grid_path)
    summaries, combined_nav = validate_replay_artifacts(manifest, paired, grid)
    checks["replay_and_paired_metrics_recomputed"] = True
    a = summaries[("combined_development", "A_ONLY")]
    b = summaries[("combined_development", "A_PLUS_B")]
    paired_daily = combined_nav["A_ONLY"][["signal_date", "date", "daily_return"]].rename(
        columns={"date": "execution_date", "daily_return": "a_return"}
    ).merge(
        combined_nav["A_PLUS_B"][["signal_date", "date", "daily_return"]].rename(
            columns={"date": "execution_date", "daily_return": "b_return"}
        ), on=["signal_date", "execution_date"], validate="one_to_one",
    )
    regime = signals.groupby("date", as_index=False).agg(
        twii_ret20=("TWII_ret20", "first"), regime_values=("TWII_ret20", "nunique")
    )
    if len(paired_daily) != 40 or regime.regime_values.ne(1).any() or regime.twii_ret20.isna().any():
        raise RuntimeError("paired daily or TWII20 regime contract failed")
    paired_daily = paired_daily.merge(
        regime[["date", "twii_ret20"]], left_on="signal_date", right_on="date", validate="one_to_one"
    )
    paired_daily["active_return_b_minus_a"] = paired_daily.b_return - paired_daily.a_return
    paired_daily["month"] = paired_daily.signal_date.astype(str).str[:7]
    columns = ["signal_date", "execution_date", "a_return", "b_return", "date", "twii_ret20", "active_return_b_minus_a", "month"]
    if list(paired_daily_file.columns) != columns:
        raise RuntimeError("paired daily serialized schema failed")
    for column in columns:
        if column in {"signal_date", "execution_date", "date", "month"}:
            matches = paired_daily_file[column].astype(str).reset_index(drop=True).equals(paired_daily[column].astype(str).reset_index(drop=True))
        else:
            matches = np.allclose(paired_daily_file[column], paired_daily[column], rtol=0.0, atol=1e-12)
        if not matches:
            raise RuntimeError(f"paired daily recomputation failed: {column}")
    checks["paired_daily_recomputed"] = True

    monthly = paired_daily.groupby("month").agg(
        a_return=("a_return", lambda values: float(np.prod(1.0 + values) - 1.0)),
        b_return=("b_return", lambda values: float(np.prod(1.0 + values) - 1.0)),
    ).reset_index()
    if (
        len(monthly) != len(monthly_file) or not monthly.month.astype(str).equals(monthly_file.month.astype(str))
        or not np.allclose(monthly[["a_return", "b_return"]], monthly_file[["a_return", "b_return"]], rtol=0.0, atol=1e-12)
    ):
        raise RuntimeError("monthly diagnostics recomputation failed")
    checks["monthly_recomputed"] = True
    monthly_fraction = float((monthly.b_return > monthly.a_return).mean()) if len(monthly) else None
    negative = paired_daily[paired_daily.twii_ret20 < 0]
    negative_delta = None if negative.empty else float(np.prod(1.0 + negative.b_return) - np.prod(1.0 + negative.a_return))
    negative_reason = "EMPTY_NEGATIVE_TWII20_REGIME_FAIL_GATE" if negative.empty else None
    rank_combined = rank_summary[rank_summary.scope.eq("combined_development")].set_index("method")
    ratios = {
        "turnover_ratio_b_over_a": finite_ratio(b["turnover"], a["turnover"]),
        "fee_tax_ratio_b_over_a": finite_ratio(b["fee_tax"], a["fee_tax"]),
        "executed_buy_count_ratio_b_over_a": finite_ratio(float(b["buy_count"]), float(a["buy_count"])),
        "executed_sell_count_ratio_b_over_a": finite_ratio(float(b["sell_count"]), float(a["sell_count"])),
        "executed_total_action_count_ratio_b_over_a": finite_ratio(float(b["action_count"]), float(a["action_count"])),
    }
    measured: dict[str, tuple[Any, str | None]] = {
        "max_drawdown_noninferiority_b_minus_a": (b["max_drawdown"] - a["max_drawdown"], None),
        "top1_abs_contribution_share": (b["top1_abs_contribution_share"], None if b["contribution_denominator_valid"] else "ZERO_CONTRIBUTION_DENOMINATOR_FAIL_GATE"),
        "top1_abs_contribution_share_vs_a_delta": ((b["top1_abs_contribution_share"] - a["top1_abs_contribution_share"]) if a["contribution_denominator_valid"] and b["contribution_denominator_valid"] else None, None if a["contribution_denominator_valid"] and b["contribution_denominator_valid"] else "ZERO_CONTRIBUTION_DENOMINATOR_FAIL_GATE"),
        "top5_abs_contribution_share": (b["top5_abs_contribution_share"], None if b["contribution_denominator_valid"] else "ZERO_CONTRIBUTION_DENOMINATOR_FAIL_GATE"),
        "top5_abs_contribution_share_vs_a_delta": ((b["top5_abs_contribution_share"] - a["top5_abs_contribution_share"]) if a["contribution_denominator_valid"] and b["contribution_denominator_valid"] else None, None if a["contribution_denominator_valid"] and b["contribution_denominator_valid"] else "ZERO_CONTRIBUTION_DENOMINATOR_FAIL_GATE"),
        "abs_contribution_hhi": (b["abs_contribution_hhi"], None if b["contribution_denominator_valid"] else "ZERO_CONTRIBUTION_DENOMINATOR_FAIL_GATE"),
        "abs_contribution_hhi_vs_a_delta": ((b["abs_contribution_hhi"] - a["abs_contribution_hhi"]) if a["contribution_denominator_valid"] and b["contribution_denominator_valid"] else None, None if a["contribution_denominator_valid"] and b["contribution_denominator_valid"] else "ZERO_CONTRIBUTION_DENOMINATOR_FAIL_GATE"),
        "monthly_outperformance_fraction": (monthly_fraction, None if monthly_fraction is not None else "EMPTY_MONTHLY_SERIES_FAIL_GATE"),
        "negative_twii20_regime_return_delta": (negative_delta, negative_reason),
        "rank_ic_delta_b_minus_a": (float(rank_combined.loc["A_PLUS_B", "mean_rank_ic_continuous"] - rank_combined.loc["A_ONLY", "mean_rank_ic_continuous"]), None),
        "ndcg_at_10_delta_b_minus_a": (float(rank_combined.loc["A_PLUS_B", "mean_ndcg_at_10"] - rank_combined.loc["A_ONLY", "mean_ndcg_at_10"]), None),
        "minimum_executed_buys_each_track": (min(a["buy_count"], b["buy_count"]), None),
        "minimum_executed_sells_each_track": (min(a["sell_count"], b["sell_count"]), None),
        "executed_total_action_count_absolute_delta_b_minus_a": (abs(b["action_count"] - a["action_count"]), None),
        "pending_or_fallback_actions_allowed": (a["pending_count"] + b["pending_count"] + a["fallback_count"] + b["fallback_count"], None),
        "all_emitted_positive_quantity_actions_must_execute": (a["all_actions_executed"] and b["all_actions_executed"], None),
        "engineering_tolerance": (max(abs(a["reconciliation_delta"]), abs(b["reconciliation_delta"])), None),
        "post_outcome_threshold_change_allowed": (False, None),
    }
    measured.update(ratios)
    frozen = json.loads(PROTOCOL.read_text(encoding="utf-8"))["preregistered_numeric_quality_gates"]
    if set(gate_table.gate) != set(frozen) or gate_table.gate.duplicated().any():
        raise RuntimeError("gate identity does not match frozen contract")
    applicable_passes: list[bool] = []
    for gate, contract in frozen.items():
        row = gate_table[gate_table.gate.eq(gate)].iloc[0]
        if gate in RESERVED:
            if (
                row.scope != "SEALED_CONFIRMATION_30_DAY_ONLY" or row.status != "RESERVED_FOR_CONFIRMATION_NOT_EVALUATED"
                or csv_bool(row["pass"]) is not None or not pd.isna(row.measured_value)
                or row.baseline_admission_effect != "NONE" or row.operator != contract["operator"]
                or not close(row.threshold, contract["threshold"])
            ):
                raise RuntimeError(f"confirmation-only gate reservation failed: {gate}")
            continue
        if gate == "all_gates_jointly_required":
            if row.scope != "SEALED_CONFIRMATION_POLICY" or row.status != "POLICY_PRESERVED_NOT_ADJUDICATED" or csv_bool(row["pass"]) is not None:
                raise RuntimeError("confirmation all-joint policy was improperly adjudicated")
            continue
        if gate == "zero_denominator_policy":
            actual, reason, operator, threshold = "FAIL_GATE", None, "==", "FAIL_GATE"
        else:
            actual, reason = measured[gate]
            operator = contract["operator"] if isinstance(contract, dict) else "=="
            threshold = contract["threshold"] if isinstance(contract, dict) else contract
        expected_pass = reason is None and compare(actual, operator, threshold)
        actual_cell = row.measured_value
        if isinstance(actual, bool):
            value_match = csv_bool(actual_cell) is actual
        elif actual is None:
            value_match = pd.isna(actual_cell)
        elif isinstance(actual, str):
            value_match = str(actual_cell) == actual
        else:
            value_match = close(actual_cell, actual)
        if isinstance(threshold, bool):
            threshold_match = csv_bool(row.threshold) is threshold
        elif isinstance(threshold, str):
            threshold_match = str(row.threshold) == threshold
        else:
            threshold_match = close(row.threshold, threshold)
        if (
            row.scope != "COMBINED_DEVELOPMENT_DIAGNOSTIC" or row.operator != operator
            or not threshold_match or not value_match or csv_bool(row["pass"]) is not expected_pass
            or row.status != ("PASS" if expected_pass else "FAIL")
            or str(row.reason) != (reason or ("threshold satisfied" if expected_pass else "threshold not satisfied"))
            or row.baseline_admission_effect != "NONE"
        ):
            raise RuntimeError(f"gate recomputation failed: {gate}")
        applicable_passes.append(expected_pass)
    checks["gate_table_independently_recomputed"] = True
    diagnostic = manifest["gate_diagnostic"]
    expected_verdict = "PASS_APPLICABLE_DEVELOPMENT_DIAGNOSTICS" if all(applicable_passes) else "FAIL_APPLICABLE_DEVELOPMENT_DIAGNOSTICS"
    checks["joint_development_diagnostic_recomputed"] = (
        diagnostic.get("scope") == "COMBINED_DEVELOPMENT_DIAGNOSTIC"
        and diagnostic.get("applicable_gate_count") == len(applicable_passes)
        and diagnostic.get("applicable_gate_pass_count") == sum(applicable_passes)
        and diagnostic.get("applicable_gate_fail_count") == len(applicable_passes) - sum(applicable_passes)
        and diagnostic.get("development_applicable_gate_verdict") == expected_verdict
        and diagnostic.get("confirmation_all_joint_verdict") == "NOT_EVALUATED"
        and diagnostic.get("baseline_admission_effect") == "NONE"
        and close(diagnostic.get("after_cost_return_delta_b_minus_a_diagnostic_only"), b["net_return"] - a["net_return"])
        and close(diagnostic.get("paired_daily_active_return_mean_b_minus_a"), paired_daily.active_return_b_minus_a.mean())
        and close(diagnostic.get("paired_daily_active_return_sum_b_minus_a"), paired_daily.active_return_b_minus_a.sum())
        and diagnostic.get("negative_twii20_date_count") == len(negative)
        and diagnostic.get("monthly_count") == len(monthly)
    )
    details.update({
        "recomputed_development_verdict": expected_verdict,
        "recomputed_applicable_gate_count": len(applicable_passes),
        "recomputed_applicable_gate_fail_count": len(applicable_passes) - sum(applicable_passes),
        "negative_twii20_date_count": len(negative),
        "confirmation_all_joint_verdict": "NOT_EVALUATED",
    })
    return checks, details


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--precheck", action="store_true")
    parser.add_argument("--validate-output", action="store_true")
    args = parser.parse_args()
    if args.precheck == args.validate_output:
        raise SystemExit("Select exactly one mode")
    protocol = protocol_checks(pristine=args.precheck)
    result: dict[str, Any] = {
        "protocol_checks": protocol,
        "protocol_verdict": "PASS" if protocol and all(protocol.values()) else "HOLD",
    }
    if args.validate_output:
        try:
            output, details = deep_output_checks()
            result["output_checks"] = output
            result["output_details"] = details
            result["output_verdict"] = "PASS" if output and all(output.values()) else "HOLD"
        except Exception as error:
            result["output_checks"] = {"deep_validation_completed": False}
            result["output_details"] = {"error": f"{type(error).__name__}: {error}"}
            result["output_verdict"] = "HOLD"
    print(json.dumps(result, indent=2, ensure_ascii=False))
    verdict = result.get("output_verdict", result["protocol_verdict"])
    return 0 if verdict == "PASS" and result["protocol_verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
