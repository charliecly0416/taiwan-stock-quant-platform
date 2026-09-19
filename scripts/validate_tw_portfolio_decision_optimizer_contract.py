#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import json
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEPENDENCY = ROOT / "configs/strategy_dependencies/portfolio_decision_optimizer_v1.yaml"
DEFAULT_GOLDEN_ROOT = ROOT / "data_tw/golden_samples/portfolio_decision_optimizer_v1"

REQUIRED_CORE_FIELDS = {
    "date",
    "instrument",
    "model_name",
    "model_family",
    "candidate_rank",
    "buy_score",
    "raw_score",
    "score_rank",
    "full_qlib_rank",
    "signal_asof",
    "available_at",
    "source_artifact",
}
REQUIRED_CAPABILITIES = {
    "core_signal_v1",
    "candidate_boundary:qlib_top50",
    "buy_ordering:buy_score_desc",
    "full_rank_exit:full_qlib_rank",
    "pit_available_at_checked",
}
REQUIRED_PORTFOLIO_STATE_FIELDS = {
    "asof_date",
    "instrument",
    "quantity",
    "cost_basis",
    "current_holding_flag",
    "holding_days",
    "cash",
}
REQUIRED_EXECUTION_READINESS_FIELDS = {"next_open_ready", "execution_price_status"}
REQUIRED_EXECUTION_CONFIG_FIELDS = {"execution_price_mode", "fee_rate", "tax_rate", "min_lot_policy"}
FORBIDDEN_MODEL_SIGNAL_FIELDS = {
    "cash",
    "current_holdings",
    "next_open_ready",
    "execution_price_status",
    "fee_rate",
    "tax_rate",
    "min_lot_policy",
    "execution_price",
    "next_open",
    "next_close",
}
FORBIDDEN_ORDER_INTENT_FIELDS = {
    "execution_date",
    "execution_price",
    "execution_quantity",
    "commission",
    "tax",
    "cash",
    "cash_after",
    "equity",
    "daily_return",
    "realized_pnl",
    "unrealized_pnl",
    "broker_order_id",
    "target_position",
    "target_weight",

    "quantity_to_buy",
    "quantity_to_sell",
    "shares",
    "lots",
    "allocation_weight",
    "nav",
    "fee",
    "broker",
    "order_id",
    "quick_trade",
    "replay_return",}
FORBIDDEN_FIELD_PATTERNS = {
    "future_return_*",
    "future_excess_return_*",
    "forward_return_*",
    "label_*",
}
REQUIRED_FORBIDDEN_ACTIONS = {
    "train_model",
    "tune_model",
    "read_model_private_file",
    "read_future_price",
    "read_future_label",
    "write_broker_order",
    "quick_trade",
    "provider_publish",
    "accepted_latest_switch",
    "monitor_write",
    "default_model_switch",
    "default_strategy_switch",
    "frontend_default_switch",
}
REQUIRED_GOLDEN_SAMPLES = {
    "pass_blocked_next_open_unavailable": True,
    "fail_execution_price_in_order_intent": False,
    "fail_target_weight_output": False,
    "fail_future_return_field": False,
    "fail_all_gates_at_once_strategy_config": False,
    "fail_turnover_only_pass_claim": False,
    "pass_p1b_a_ready_matches_baseline": True,
    "pass_p1b_a_blocked_next_open_skip": True,
    "fail_p1b_a_next_open_price_value_input": False,
    "fail_p1b_a_execution_price_in_order_intent": False,
    "fail_p1b_a_altered_baseline_when_ready": False,
    "pass_p1b_b_tiny_gap_blocks_trade": True,
    "pass_p1b_b_large_gap_keeps_baseline": True,
    "fail_p1b_b_uses_execution_price_gate": False,
    "fail_p1b_b_blocks_strong_signal": False,
    "fail_p1b_b_future_return_or_replay_return_input": False,
    "pass_p1b_c_gap_blocks_weak_replacement": True,
    "pass_p1b_c_large_gap_keeps_baseline": True,
    "fail_p1b_c_uses_tiny_no_trade_buffer": False,
    "fail_p1b_c_uses_execution_price_gate": False,
    "fail_p1b_c_blocks_strong_signal": False,
    "fail_p1b_c_future_return_or_replay_return_input": False,
    "pass_p1b_d_short_holding_blocks_replacement": True,
    "pass_p1b_d_deep_exit_exception_keeps_baseline": True,
    "pass_p1b_d_mature_holding_keeps_baseline": True,
    "fail_p1b_d_uses_confidence_gap": False,
    "fail_p1b_d_uses_execution_price_or_tiny_buffer": False,
    "fail_p1b_d_blocks_exception": False,
    "fail_p1b_d_future_return_or_pnl_input": False,
    "pass_p1b_e_budget_allows_when_under_budget": True,
    "pass_p1b_e_budget_blocks_low_priority_when_exceeded": True,
    "pass_p1b_e_strong_signal_exception_keeps_baseline": True,
    "fail_p1b_e_uses_prior_gates": False,
    "fail_p1b_e_blocks_strong_signal": False,
    "fail_p1b_e_future_return_or_pnl_input": False,
    "pass_p1b_f_normal_regime_keeps_baseline": True,
    "pass_p1b_f_risk_off_blocks_weak_signal": True,
    "pass_p1b_f_risk_off_strong_signal_keeps_baseline": True,
    "fail_p1b_f_uses_prior_gates": False,
    "fail_p1b_f_blocks_all_risk_off_buys": False,
    "fail_p1b_f_future_return_or_pnl_input": False,
    "pass_p1b_g0_simulated_buy_small_intent_contract": True,
    "pass_p1b_g0_simulated_reduce_partial_intent_contract": True,
    "fail_p1b_g0_partial_intent_with_execution_quantity": False,
    "fail_p1b_g0_partial_intent_with_target_weight": False,
    "fail_p1b_g0_partial_intent_with_cash_nav_or_pnl": False,
    "fail_p1b_g0_partial_intent_claims_real_order": False,
    "pass_p1b_g_partial_adjustment_maps_sell_buy_to_simulated_partial": True,
    "pass_p1b_g_non_trade_rows_keep_baseline": True,
    "fail_p1b_g_uses_prior_gates": False,
    "fail_p1b_g_outputs_quantity_or_weight": False,
    "fail_p1b_g_claims_real_order": False,
    "fail_p1b_g_future_return_or_pnl_input": False,
    "fail_p1b_g_unknown_partial_reason": False,
}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def check(name: str, ok: bool, details: str = "") -> dict[str, Any]:
    return {"name": name, "status": "pass" if ok else "fail", "details": details}


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def as_set(value: Any) -> set[str]:
    if value is None:
        return set()
    if not isinstance(value, list):
        return {str(value)}
    return {str(item) for item in value}


def contains_forbidden(values: set[str], forbidden_exact: set[str]) -> list[str]:
    found: list[str] = []
    for value in values:
        if value in forbidden_exact or any(fnmatch.fnmatch(value, pattern) for pattern in FORBIDDEN_FIELD_PATTERNS):
            found.append(value)
    return sorted(found)


def validate_dependency(path: Path) -> dict[str, Any]:
    dep = load_yaml(path)
    checks: list[dict[str, Any]] = []

    required_core = as_set(dep.get("required_core_fields"))
    required_caps = as_set(dep.get("required_capabilities"))
    required_portfolio = as_set(dep.get("required_portfolio_state_fields"))
    required_readiness = as_set(dep.get("required_execution_readiness_fields"))
    required_config = as_set(dep.get("required_execution_config_fields"))
    forbidden_fields = as_set(dep.get("forbidden_fields"))
    order_intent_forbidden = as_set(dep.get("order_intent_forbidden_fields"))
    forbidden_actions = as_set(dep.get("forbidden_actions"))

    checks.append(check("dependency_yaml_exists", path.exists(), rel(path)))
    checks.append(check("strategy_rule", dep.get("strategy_rule") == "portfolio_decision_optimizer_v1", str(dep.get("strategy_rule"))))
    checks.append(check("dependency_version", dep.get("dependency_version") == "strategy_dependency_v1", str(dep.get("dependency_version"))))
    checks.append(check("required_core_fields_declared", REQUIRED_CORE_FIELDS <= required_core, ",".join(sorted(REQUIRED_CORE_FIELDS - required_core))))
    checks.append(check("required_capabilities_declared", REQUIRED_CAPABILITIES <= required_caps, ",".join(sorted(REQUIRED_CAPABILITIES - required_caps))))
    checks.append(check("ranking_usage_declared", bool(dep.get("ranking_usage")), "ranking_usage present"))
    checks.append(check("forbidden_fields_declared", {"execution_price", "next_open", "target_position", "target_weight"} <= forbidden_fields, ",".join(sorted({"execution_price", "next_open", "target_position", "target_weight"} - forbidden_fields))))
    checks.append(check("forbidden_actions_declared", REQUIRED_FORBIDDEN_ACTIONS <= forbidden_actions, ",".join(sorted(REQUIRED_FORBIDDEN_ACTIONS - forbidden_actions))))
    checks.append(check("readonly_flags_declared", dep.get("readonly_only") is True and dep.get("simulation_only") is True and dep.get("not_order") is True and dep.get("not_target_position") is True and dep.get("not_investment_advice") is True))
    checks.append(check("max_buy_sell_count_is_1_1", dep.get("max_buy_count") == 1 and dep.get("max_sell_count") == 1, f"{dep.get('max_buy_count')}/{dep.get('max_sell_count')}"))
    checks.append(check("portfolio_state_fields_not_model_signal_extensions", not (FORBIDDEN_MODEL_SIGNAL_FIELDS & required_core), ",".join(sorted(FORBIDDEN_MODEL_SIGNAL_FIELDS & required_core))))
    checks.append(check("portfolio_state_fields_declared", REQUIRED_PORTFOLIO_STATE_FIELDS <= required_portfolio, ",".join(sorted(REQUIRED_PORTFOLIO_STATE_FIELDS - required_portfolio))))
    checks.append(check("execution_readiness_fields_not_model_signal_extensions", not ({"next_open_ready", "execution_price_status"} & required_core), ",".join(sorted({"next_open_ready", "execution_price_status"} & required_core))))
    checks.append(check("execution_readiness_fields_declared", REQUIRED_EXECUTION_READINESS_FIELDS <= required_readiness, ",".join(sorted(REQUIRED_EXECUTION_READINESS_FIELDS - required_readiness))))
    checks.append(check("cost_lot_fields_not_model_signal_extensions", not ({"fee_rate", "tax_rate", "min_lot_policy"} & required_core), ",".join(sorted({"fee_rate", "tax_rate", "min_lot_policy"} & required_core))))
    checks.append(check("execution_config_fields_declared", REQUIRED_EXECUTION_CONFIG_FIELDS <= required_config, ",".join(sorted(REQUIRED_EXECUTION_CONFIG_FIELDS - required_config))))
    checks.append(check("next_open_price_value_forbidden", "next_open" in forbidden_fields and "execution_price" in forbidden_fields))
    checks.append(check("order_intent_forbidden_fields_declared", FORBIDDEN_ORDER_INTENT_FIELDS <= order_intent_forbidden, ",".join(sorted(FORBIDDEN_ORDER_INTENT_FIELDS - order_intent_forbidden))))
    checks.append(check("target_position_weight_forbidden", {"target_position", "target_weight"} <= forbidden_fields and {"target_position", "target_weight"} <= order_intent_forbidden))

    gate = dep.get("order_intent_extension_gate") or {}
    checks.append(check("order_intent_extension_schema_gate", gate.get("schema_required") is True and gate.get("validator_required") is True and gate.get("golden_sample_required") is True and gate.get("free_form_extension_forbidden") is True))
    partial_gate = gate.get("partial_intent_contract_support") or {}
    allowed_reasons = as_set(partial_gate.get("allowed_reason_codes"))
    allowed_diag = as_set(partial_gate.get("allowed_diagnostic_fields"))
    required_flags = partial_gate.get("required_flags") or {}
    forbidden_partial = as_set(partial_gate.get("forbidden_quantity_or_position_fields"))
    checks.append(check("partial_intent_reason_codes_declared", {"simulated_buy_small", "simulated_reduce_partial"} <= allowed_reasons, ",".join(sorted({"simulated_buy_small", "simulated_reduce_partial"} - allowed_reasons))))
    checks.append(check("partial_intent_diagnostic_fields_declared", {"partial_intent_kind", "partial_intent_policy", "partial_intent_note"} <= allowed_diag, ",".join(sorted({"partial_intent_kind", "partial_intent_policy", "partial_intent_note"} - allowed_diag))))
    checks.append(check("partial_intent_required_flags_declared", required_flags.get("readonly_only") is True and required_flags.get("simulation_only") is True and required_flags.get("not_order") is True and required_flags.get("not_target_position") is True and required_flags.get("not_investment_advice") is True))
    checks.append(check("partial_intent_quantity_position_forbidden", {"execution_quantity", "quantity_to_buy", "quantity_to_sell", "shares", "lots", "target_position", "target_weight", "allocation_weight"} <= forbidden_partial, ",".join(sorted({"execution_quantity", "quantity_to_buy", "quantity_to_sell", "shares", "lots", "target_position", "target_weight", "allocation_weight"} - forbidden_partial))))

    ablation = dep.get("ablation_policy") or {}
    checks.append(check("ablation_policy_declared", bool(ablation), "ablation_policy present"))
    checks.append(check("default_strategy_skeleton_declared", ablation.get("baseline_strategy_rule") == "top50_exit_one_worst_sell", str(ablation.get("baseline_strategy_rule"))))
    checks.append(check("all_gates_at_once_forbidden", ablation.get("forbid_all_gates_at_once") is True))
    checks.append(check("turnover_reduction_not_standalone_pass_standard", ablation.get("pass_standard_not_turnover_only") is True))

    ok = all(row["status"] == "pass" for row in checks)
    return {"ok": ok, "dependency": rel(path), "checks": checks}


def normalize_intent_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keep = [
        "signal_date",
        "instrument",
        "intent_action",
        "intent_reason",
        "primary_reason_code",
        "strategy_rule",
        "candidate_rank",
        "buy_rank",
        "full_qlib_rank",
        "max_buy_count",
        "max_sell_count",
        "model_name",
        "signal_artifact",
    ]
    normalized = []
    for row in rows:
        normalized.append({key: row.get(key, "") for key in keep})
    return sorted(normalized, key=lambda row: (str(row.get("instrument")), str(row.get("intent_action")), str(row.get("primary_reason_code"))))


def validate_p1b_a_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    readiness = payload.get("execution_readiness") or {}
    if any(key in readiness for key in ("next_open", "next_close", "execution_price", "fallback_price", "signal_close")):
        errors.append("p1b_a_execution_readiness_contains_price_value")
    baseline = payload.get("baseline_order_intents") or []
    candidate = payload.get("candidate_order_intents") or []
    if payload.get("expected_builder_matches_fixture") is True:
        try:
            from build_tw_portfolio_decision_optimizer_order_intent import build_from_fixture
            built = build_from_fixture(payload)
            if normalize_intent_rows(built.get("baseline_order_intents", [])) != normalize_intent_rows(baseline):
                errors.append("p1b_a_builder_baseline_mismatch")
            if normalize_intent_rows(built.get("candidate_order_intents", [])) != normalize_intent_rows(candidate):
                errors.append("p1b_a_builder_candidate_mismatch")
        except Exception as exc:
            errors.append(f"p1b_a_builder_error:{exc}")
    for row in candidate:
        forbidden = set(row) & FORBIDDEN_ORDER_INTENT_FIELDS
        if forbidden:
            errors.append(f"p1b_a_order_intent_forbidden:{'|'.join(sorted(forbidden))}")
    if readiness.get("next_open_ready") is True and normalize_intent_rows(candidate) != normalize_intent_rows(baseline):
        errors.append("p1b_a_altered_baseline_when_ready")
    if readiness.get("next_open_ready") is False:
        for base_row, cand_row in zip(baseline, candidate):
            if base_row.get("intent_action") in {"buy", "sell"}:
                if cand_row.get("intent_action") != "skip" or cand_row.get("primary_reason_code") != "blocked_execution_price_unavailable":
                    errors.append("p1b_a_blocked_next_open_not_skip")
    return errors


def validate_p1b_b_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("mechanism") != "tiny_no_trade_buffer":
        errors.append("p1b_b_wrong_mechanism")
    readiness = payload.get("execution_readiness") or {}
    if readiness.get("next_open_ready") is False:
        errors.append("p1b_b_uses_execution_price_gate")
    for key in ("next_open", "next_close", "execution_price", "fallback_price", "signal_close"):
        if key in readiness:
            errors.append("p1b_b_execution_readiness_contains_price_value")
    forbidden_inputs = {"replay_return", "realized_pnl", "net_return", "gross_return", "future_return_5d"}
    input_fields = as_set(payload.get("model_signal_fields")) | as_set(payload.get("strategy_input_fields"))
    bad_inputs = sorted(field for field in input_fields if field in forbidden_inputs or any(fnmatch.fnmatch(field, pattern) for pattern in FORBIDDEN_FIELD_PATTERNS))
    if bad_inputs:
        errors.append(f"p1b_b_forbidden_return_input:{'|'.join(bad_inputs)}")
    baseline = payload.get("baseline_order_intents") or []
    candidate = payload.get("candidate_order_intents") or []
    if payload.get("expected_builder_matches_fixture") is True:
        try:
            from build_tw_portfolio_decision_optimizer_order_intent import build_from_fixture
            built = build_from_fixture(payload)
            if normalize_intent_rows(built.get("baseline_order_intents", [])) != normalize_intent_rows(baseline):
                errors.append("p1b_b_builder_baseline_mismatch")
            if normalize_intent_rows(built.get("candidate_order_intents", [])) != normalize_intent_rows(candidate):
                errors.append("p1b_b_builder_candidate_mismatch")
        except Exception as exc:
            errors.append(f"p1b_b_builder_error:{exc}")
    for row in candidate:
        forbidden = set(row) & FORBIDDEN_ORDER_INTENT_FIELDS
        if forbidden:
            errors.append(f"p1b_b_order_intent_forbidden:{'|'.join(sorted(forbidden))}")
    if payload.get("strong_signal") is True and normalize_intent_rows(candidate) != normalize_intent_rows(baseline):
        errors.append("p1b_b_blocks_strong_signal")
    if payload.get("tiny_gap_expected_block") is True:
        for base_row, cand_row in zip(baseline, candidate):
            if base_row.get("intent_action") in {"buy", "sell"}:
                if cand_row.get("intent_action") != "skip" or cand_row.get("primary_reason_code") != "blocked_tiny_no_trade_buffer":
                    errors.append("p1b_b_tiny_gap_not_blocked")
    if payload.get("large_gap_expected_keep") is True and normalize_intent_rows(candidate) != normalize_intent_rows(baseline):
        errors.append("p1b_b_large_gap_altered_baseline")
    return errors


def validate_p1b_c_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("mechanism") != "confidence_gap":
        errors.append("p1b_c_wrong_mechanism")
    readiness = payload.get("execution_readiness") or {}
    if readiness.get("next_open_ready") is False:
        errors.append("p1b_c_uses_execution_price_gate")
    for key in ("next_open", "next_close", "execution_price", "fallback_price", "signal_close"):
        if key in readiness:
            errors.append("p1b_c_execution_readiness_contains_price_value")
    strategy_config = payload.get("strategy_config") or {}
    if "tiny_no_trade_buffer" in strategy_config:
        errors.append("p1b_c_uses_tiny_no_trade_buffer")
    forbidden_inputs = {"replay_return", "realized_pnl", "net_return", "gross_return", "future_return_5d"}
    input_fields = as_set(payload.get("model_signal_fields")) | as_set(payload.get("strategy_input_fields"))
    bad_inputs = sorted(field for field in input_fields if field in forbidden_inputs or any(fnmatch.fnmatch(field, pattern) for pattern in FORBIDDEN_FIELD_PATTERNS))
    if bad_inputs:
        errors.append(f"p1b_c_forbidden_return_input:{'|'.join(bad_inputs)}")
    baseline = payload.get("baseline_order_intents") or []
    candidate = payload.get("candidate_order_intents") or []
    if payload.get("expected_builder_matches_fixture") is True:
        try:
            from build_tw_portfolio_decision_optimizer_order_intent import build_from_fixture
            built = build_from_fixture(payload)
            if normalize_intent_rows(built.get("baseline_order_intents", [])) != normalize_intent_rows(baseline):
                errors.append("p1b_c_builder_baseline_mismatch")
            if normalize_intent_rows(built.get("candidate_order_intents", [])) != normalize_intent_rows(candidate):
                errors.append("p1b_c_builder_candidate_mismatch")
        except Exception as exc:
            errors.append(f"p1b_c_builder_error:{exc}")
    for row in candidate:
        forbidden = set(row) & FORBIDDEN_ORDER_INTENT_FIELDS
        if forbidden:
            errors.append(f"p1b_c_order_intent_forbidden:{'|'.join(sorted(forbidden))}")
        if row.get("primary_reason_code") == "blocked_tiny_no_trade_buffer":
            errors.append("p1b_c_uses_tiny_no_trade_buffer")
        if row.get("primary_reason_code") == "blocked_execution_price_unavailable":
            errors.append("p1b_c_uses_execution_price_gate")
    if payload.get("strong_signal") is True and normalize_intent_rows(candidate) != normalize_intent_rows(baseline):
        errors.append("p1b_c_blocks_strong_signal")
    if payload.get("confidence_gap_expected_block") is True:
        for base_row, cand_row in zip(baseline, candidate):
            if base_row.get("intent_action") in {"buy", "sell"}:
                if cand_row.get("intent_action") != "skip" or cand_row.get("primary_reason_code") != "blocked_confidence_gap":
                    errors.append("p1b_c_weak_gap_not_blocked")
    if payload.get("large_gap_expected_keep") is True and normalize_intent_rows(candidate) != normalize_intent_rows(baseline):
        errors.append("p1b_c_large_gap_altered_baseline")
    return errors


def validate_p1b_d_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("mechanism") != "min_holding_days_with_exception":
        errors.append("p1b_d_wrong_mechanism")
    readiness = payload.get("execution_readiness") or {}
    if readiness.get("next_open_ready") is False:
        errors.append("p1b_d_uses_execution_price_gate")
    for key in ("next_open", "next_close", "execution_price", "fallback_price", "signal_close"):
        if key in readiness:
            errors.append("p1b_d_execution_readiness_contains_price_value")
    strategy_config = payload.get("strategy_config") or {}
    if "confidence_gap" in strategy_config:
        errors.append("p1b_d_uses_confidence_gap")
    if "tiny_no_trade_buffer" in strategy_config:
        errors.append("p1b_d_uses_tiny_no_trade_buffer")
    forbidden_inputs = {"replay_return", "realized_pnl", "unrealized_pnl", "net_return", "gross_return", "future_return_5d"}
    input_fields = as_set(payload.get("model_signal_fields")) | as_set(payload.get("strategy_input_fields")) | as_set(payload.get("portfolio_state_fields"))
    bad_inputs = sorted(field for field in input_fields if field in forbidden_inputs or any(fnmatch.fnmatch(field, pattern) for pattern in FORBIDDEN_FIELD_PATTERNS))
    if bad_inputs:
        errors.append(f"p1b_d_forbidden_return_or_pnl_input:{'|'.join(bad_inputs)}")
    baseline = payload.get("baseline_order_intents") or []
    candidate = payload.get("candidate_order_intents") or []
    if payload.get("expected_builder_matches_fixture") is True:
        try:
            from build_tw_portfolio_decision_optimizer_order_intent import build_from_fixture
            built = build_from_fixture(payload)
            if normalize_intent_rows(built.get("baseline_order_intents", [])) != normalize_intent_rows(baseline):
                errors.append("p1b_d_builder_baseline_mismatch")
            if normalize_intent_rows(built.get("candidate_order_intents", [])) != normalize_intent_rows(candidate):
                errors.append("p1b_d_builder_candidate_mismatch")
        except Exception as exc:
            errors.append(f"p1b_d_builder_error:{exc}")
    for row in candidate:
        forbidden = set(row) & FORBIDDEN_ORDER_INTENT_FIELDS
        if forbidden:
            errors.append(f"p1b_d_order_intent_forbidden:{'|'.join(sorted(forbidden))}")
        reason = row.get("primary_reason_code")
        if reason == "blocked_confidence_gap":
            errors.append("p1b_d_uses_confidence_gap")
        if reason == "blocked_tiny_no_trade_buffer":
            errors.append("p1b_d_uses_tiny_no_trade_buffer")
        if reason == "blocked_execution_price_unavailable":
            errors.append("p1b_d_uses_execution_price_gate")
    if payload.get("min_holding_expected_block") is True:
        for base_row, cand_row in zip(baseline, candidate):
            if base_row.get("intent_action") in {"buy", "sell"}:
                if cand_row.get("intent_action") != "skip" or cand_row.get("primary_reason_code") != "blocked_min_holding_days":
                    errors.append("p1b_d_short_holding_not_blocked")
    if payload.get("exception_expected_keep") is True and normalize_intent_rows(candidate) != normalize_intent_rows(baseline):
        errors.append("p1b_d_blocks_exception")
    if payload.get("mature_holding_expected_keep") is True and normalize_intent_rows(candidate) != normalize_intent_rows(baseline):
        errors.append("p1b_d_blocks_mature_holding")
    return errors


def validate_p1b_e_payload(payload: dict[str, Any], expected_payload: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    if payload.get("mechanism") != "turnover_budget":
        errors.append("p1b_e_wrong_mechanism")
    readiness = payload.get("execution_readiness") or {}
    if readiness.get("next_open_ready") is False:
        errors.append("p1b_e_uses_execution_price_gate")
    for key in ("next_open", "next_close", "execution_price", "fallback_price", "signal_close"):
        if key in readiness:
            errors.append("p1b_e_execution_readiness_contains_price_value")
    strategy_config = payload.get("strategy_config") or {}
    prior_gate_keys = {
        "execution_price_gate",
        "tiny_no_trade_buffer",
        "confidence_gap",
        "min_holding_days_with_exception",
        "risk_off_raised_threshold",
        "partial_adjustment",
    }
    prior_used = sorted(key for key in prior_gate_keys if key in strategy_config)
    if prior_used:
        errors.append(f"p1b_e_uses_prior_gates:{'|'.join(prior_used)}")
    forbidden_inputs = {"replay_return", "realized_pnl", "unrealized_pnl", "net_return", "gross_return", "future_return_5d"}
    input_fields = as_set(payload.get("model_signal_fields")) | as_set(payload.get("strategy_input_fields")) | as_set(payload.get("portfolio_state_fields")) | as_set(payload.get("turnover_state_fields"))
    bad_inputs = sorted(field for field in input_fields if field in forbidden_inputs or any(fnmatch.fnmatch(field, pattern) for pattern in FORBIDDEN_FIELD_PATTERNS))
    if bad_inputs:
        errors.append(f"p1b_e_forbidden_return_or_pnl_input:{'|'.join(bad_inputs)}")
    baseline = payload.get("baseline_order_intents") or []
    candidate = payload.get("candidate_order_intents") or []
    if payload.get("expected_builder_matches_fixture") is True:
        try:
            from build_tw_portfolio_decision_optimizer_order_intent import build_from_fixture
            built = build_from_fixture(payload)
            if normalize_intent_rows(built.get("baseline_order_intents", [])) != normalize_intent_rows(baseline):
                errors.append("p1b_e_builder_baseline_mismatch")
            if normalize_intent_rows(built.get("candidate_order_intents", [])) != normalize_intent_rows(candidate):
                errors.append("p1b_e_builder_candidate_mismatch")
            if expected_payload is not None and normalize_intent_rows(built.get("candidate_order_intents", [])) != normalize_intent_rows(expected_payload.get("candidate_order_intents", [])):
                errors.append("p1b_e_builder_expected_json_mismatch")
        except Exception as exc:
            errors.append(f"p1b_e_builder_error:{exc}")
    for row in candidate:
        forbidden = set(row) & FORBIDDEN_ORDER_INTENT_FIELDS
        if forbidden:
            errors.append(f"p1b_e_order_intent_forbidden:{'|'.join(sorted(forbidden))}")
        reason = row.get("primary_reason_code")
        if reason in {"blocked_execution_price_unavailable", "blocked_tiny_no_trade_buffer", "blocked_confidence_gap", "blocked_min_holding_days"}:
            errors.append(f"p1b_e_uses_prior_gate_reason:{reason}")
    if payload.get("turnover_budget_expected_block") is True:
        for base_row, cand_row in zip(baseline, candidate):
            if base_row.get("intent_action") in {"buy", "sell"}:
                if cand_row.get("intent_action") != "skip" or cand_row.get("primary_reason_code") != "blocked_turnover_budget":
                    errors.append("p1b_e_low_priority_not_blocked")
    if payload.get("under_budget_expected_keep") is True and normalize_intent_rows(candidate) != normalize_intent_rows(baseline):
        errors.append("p1b_e_under_budget_altered_baseline")
    if payload.get("strong_signal_expected_keep") is True and normalize_intent_rows(candidate) != normalize_intent_rows(baseline):
        errors.append("p1b_e_blocks_strong_signal")
    return errors


def validate_p1b_f_payload(payload: dict[str, Any], expected_payload: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    if payload.get("mechanism") != "risk_off_raised_threshold":
        errors.append("p1b_f_wrong_mechanism")
    readiness = payload.get("execution_readiness") or {}
    if readiness.get("next_open_ready") is False:
        errors.append("p1b_f_uses_execution_price_gate")
    for key in ("next_open", "next_close", "execution_price", "fallback_price", "signal_close"):
        if key in readiness:
            errors.append("p1b_f_execution_readiness_contains_price_value")
    strategy_config = payload.get("strategy_config") or {}
    prior_gate_keys = {
        "execution_price_gate",
        "tiny_no_trade_buffer",
        "confidence_gap",
        "min_holding_days_with_exception",
        "turnover_budget",
        "partial_adjustment",
    }
    prior_used = sorted(key for key in prior_gate_keys if key in strategy_config)
    if prior_used:
        errors.append("p1b_f_uses_prior_gates:" + "|".join(prior_used))
    forbidden_inputs = {"replay_return", "realized_pnl", "unrealized_pnl", "net_return", "gross_return", "future_return_5d"}
    input_fields = as_set(payload.get("model_signal_fields")) | as_set(payload.get("strategy_input_fields")) | as_set(payload.get("portfolio_state_fields")) | as_set(payload.get("market_regime_fields"))
    bad_inputs = sorted(field for field in input_fields if field in forbidden_inputs or any(fnmatch.fnmatch(field, pattern) for pattern in FORBIDDEN_FIELD_PATTERNS))
    if bad_inputs:
        errors.append("p1b_f_forbidden_return_or_pnl_input:" + "|".join(bad_inputs))
    baseline = payload.get("baseline_order_intents") or []
    candidate = payload.get("candidate_order_intents") or []
    if payload.get("expected_builder_matches_fixture") is True:
        try:
            from build_tw_portfolio_decision_optimizer_order_intent import build_from_fixture
            built = build_from_fixture(payload)
            if normalize_intent_rows(built.get("baseline_order_intents", [])) != normalize_intent_rows(baseline):
                errors.append("p1b_f_builder_baseline_mismatch")
            if normalize_intent_rows(built.get("candidate_order_intents", [])) != normalize_intent_rows(candidate):
                errors.append("p1b_f_builder_candidate_mismatch")
            if expected_payload is not None and normalize_intent_rows(built.get("candidate_order_intents", [])) != normalize_intent_rows(expected_payload.get("candidate_order_intents", [])):
                errors.append("p1b_f_builder_expected_json_mismatch")
        except Exception as exc:
            errors.append(f"p1b_f_builder_error:{exc}")
    for row in candidate:
        forbidden = set(row) & FORBIDDEN_ORDER_INTENT_FIELDS
        if forbidden:
            errors.append("p1b_f_order_intent_forbidden:" + "|".join(sorted(forbidden)))
        reason = row.get("primary_reason_code")
        if reason in {"blocked_execution_price_unavailable", "blocked_tiny_no_trade_buffer", "blocked_confidence_gap", "blocked_min_holding_days", "blocked_turnover_budget"}:
            errors.append(f"p1b_f_uses_prior_gate_reason:{reason}")
    if payload.get("risk_off_weak_signal_expected_block") is True:
        for base_row, cand_row in zip(baseline, candidate):
            if base_row.get("intent_action") in {"buy", "sell"}:
                if cand_row.get("intent_action") != "skip" or cand_row.get("primary_reason_code") != "blocked_risk_off_raised_threshold":
                    errors.append("p1b_f_weak_signal_not_blocked")
    if payload.get("normal_regime_expected_keep") is True and normalize_intent_rows(candidate) != normalize_intent_rows(baseline):
        errors.append("p1b_f_normal_regime_altered_baseline")
    if payload.get("risk_off_strong_signal_expected_keep") is True and normalize_intent_rows(candidate) != normalize_intent_rows(baseline):
        errors.append("p1b_f_blocks_strong_signal")
    return errors


def validate_p1b_g0_payload(payload: dict[str, Any], expected_payload: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    if payload.get("mechanism") == "partial_adjustment":
        errors.append("p1b_g0_partial_adjustment_mechanism_forbidden")
    if payload.get("mechanism") != "partial_intent_contract_support":
        errors.append("p1b_g0_wrong_mechanism")
    allowed_reasons = {"simulated_buy_small", "simulated_reduce_partial"}
    forbidden_fields = {
        "execution_quantity", "quantity_to_buy", "quantity_to_sell", "shares", "lots",
        "target_position", "target_weight", "allocation_weight",
        "cash", "cash_after", "nav", "fee", "tax", "commission",
        "execution_price", "execution_date",
        "realized_pnl", "unrealized_pnl", "replay_return", "net_return", "gross_return", "future_return_5d",
        "broker", "broker_order_id", "order_id", "quick_trade",
    }
    intent_fields = as_set(payload.get("order_intent_fields"))
    bad_fields = sorted(field for field in intent_fields if field in forbidden_fields or any(fnmatch.fnmatch(field, pattern) for pattern in FORBIDDEN_FIELD_PATTERNS))
    if bad_fields:
        errors.append("p1b_g0_forbidden_order_intent_fields:" + "|".join(bad_fields))
    rows = payload.get("candidate_order_intents") or payload.get("order_intents") or []
    for row in rows:
        reason = row.get("primary_reason_code") or row.get("intent_reason")
        if reason in allowed_reasons:
            if row.get("intent_reason") != reason or row.get("primary_reason_code") != reason:
                errors.append("p1b_g0_partial_reason_mismatch")
            if row.get("intent_action") not in {"buy", "sell"}:
                errors.append("p1b_g0_partial_action_invalid")
            for flag in ("readonly_only", "simulation_only", "not_order", "not_target_position", "not_investment_advice"):
                if row.get(flag) is not True:
                    errors.append(f"p1b_g0_partial_flag_missing:{flag}")
        else:
            errors.append("p1b_g0_unknown_partial_reason")
        row_bad = sorted(field for field in row if field in forbidden_fields or any(fnmatch.fnmatch(field, pattern) for pattern in FORBIDDEN_FIELD_PATTERNS))
        if row_bad:
            errors.append("p1b_g0_forbidden_order_intent_row_fields:" + "|".join(row_bad))
        if row.get("not_order") is not True or row.get("not_target_position") is not True:
            errors.append("p1b_g0_claims_order_or_target")
    pass_claim = payload.get("pass_claim") or {}
    forbidden_claims = [
        key for key in ("real_order_allowed", "broker_allowed", "quick_trade_allowed", "default_candidate", "production_default", "return_verified", "can_submit_order")
        if pass_claim.get(key) is True
    ]
    if forbidden_claims:
        errors.append("p1b_g0_forbidden_pass_claim:" + "|".join(sorted(forbidden_claims)))
    artifact_path = str(payload.get("artifact_output_path") or "")
    if artifact_path.startswith("data_tw/artifacts/"):
        errors.append("p1b_g0_artifact_output_path_forbidden")
    if expected_payload is not None and rows != expected_payload.get("candidate_order_intents", expected_payload.get("order_intents", rows)):
        errors.append("p1b_g0_expected_json_mismatch")
    return errors


def validate_p1b_g_payload(payload: dict[str, Any], expected_payload: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    if payload.get("mechanism") != "partial_adjustment":
        errors.append("p1b_g_wrong_mechanism")
    readiness = payload.get("execution_readiness") or {}
    if readiness.get("next_open_ready") is False:
        errors.append("p1b_g_uses_execution_price_gate")
    for key in ("next_open", "next_close", "execution_price", "fallback_price", "signal_close"):
        if key in readiness:
            errors.append("p1b_g_execution_readiness_contains_price_value")
    strategy_config = payload.get("strategy_config") or {}
    prior_gate_keys = {
        "execution_price_gate",
        "tiny_no_trade_buffer",
        "confidence_gap",
        "min_holding_days_with_exception",
        "turnover_budget",
        "risk_off_raised_threshold",
    }
    prior_used = sorted(key for key in prior_gate_keys if key in strategy_config)
    if prior_used:
        errors.append("p1b_g_uses_prior_gates:" + "|".join(prior_used))
    partial_config = strategy_config.get("partial_adjustment") or {}
    allowed_partial_reasons = {"simulated_reduce_partial", "simulated_buy_small"}
    if str(partial_config.get("sell_reason") or "simulated_reduce_partial") != "simulated_reduce_partial":
        errors.append("p1b_g_unknown_partial_sell_reason")
    if str(partial_config.get("buy_reason") or "simulated_buy_small") != "simulated_buy_small":
        errors.append("p1b_g_unknown_partial_buy_reason")
    forbidden_inputs = {"replay_return", "realized_pnl", "unrealized_pnl", "net_return", "gross_return", "future_return_5d"}
    input_fields = as_set(payload.get("model_signal_fields")) | as_set(payload.get("strategy_input_fields")) | as_set(payload.get("portfolio_state_fields"))
    bad_inputs = sorted(field for field in input_fields if field in forbidden_inputs or any(fnmatch.fnmatch(field, pattern) for pattern in FORBIDDEN_FIELD_PATTERNS))
    if bad_inputs:
        errors.append("p1b_g_forbidden_return_or_pnl_input:" + "|".join(bad_inputs))
    baseline = payload.get("baseline_order_intents") or []
    candidate = payload.get("candidate_order_intents") or []
    if payload.get("expected_builder_matches_fixture") is True:
        try:
            from build_tw_portfolio_decision_optimizer_order_intent import build_from_fixture
            built = build_from_fixture(payload)
            if normalize_intent_rows(built.get("baseline_order_intents", [])) != normalize_intent_rows(baseline):
                errors.append("p1b_g_builder_baseline_mismatch")
            if normalize_intent_rows(built.get("candidate_order_intents", [])) != normalize_intent_rows(candidate):
                errors.append("p1b_g_builder_candidate_mismatch")
            if expected_payload is not None and normalize_intent_rows(built.get("candidate_order_intents", [])) != normalize_intent_rows(expected_payload.get("candidate_order_intents", [])):
                errors.append("p1b_g_builder_expected_json_mismatch")
        except Exception as exc:
            errors.append(f"p1b_g_builder_error:{exc}")
    forbidden_reasons = {
        "blocked_execution_price_unavailable",
        "blocked_tiny_no_trade_buffer",
        "blocked_confidence_gap",
        "blocked_min_holding_days",
        "blocked_turnover_budget",
        "blocked_risk_off_raised_threshold",
    }
    forbidden_claim_fields = {
        "execution_quantity", "quantity_to_buy", "quantity_to_sell", "shares", "lots",
        "target_position", "target_weight", "allocation_weight",
        "cash", "cash_after", "nav", "fee", "tax", "commission",
        "execution_price", "execution_date",
        "realized_pnl", "unrealized_pnl", "replay_return",
        "broker", "broker_order_id", "order_id", "quick_trade",
    }
    for base_row, cand_row in zip(baseline, candidate):
        if base_row.get("instrument") != cand_row.get("instrument"):
            errors.append("p1b_g_changed_baseline_instrument")
        action = base_row.get("intent_action")
        if action == "sell":
            if cand_row.get("intent_action") != "sell" or cand_row.get("primary_reason_code") != "simulated_reduce_partial" or cand_row.get("intent_reason") != "simulated_reduce_partial":
                errors.append("p1b_g_sell_not_mapped_to_simulated_reduce_partial")
        elif action == "buy":
            if cand_row.get("intent_action") != "buy" or cand_row.get("primary_reason_code") != "simulated_buy_small" or cand_row.get("intent_reason") != "simulated_buy_small":
                errors.append("p1b_g_buy_not_mapped_to_simulated_buy_small")
        else:
            if normalize_intent_rows([base_row]) != normalize_intent_rows([cand_row]):
                errors.append("p1b_g_non_trade_row_altered")
        reason = cand_row.get("primary_reason_code")
        if reason in forbidden_reasons:
            errors.append(f"p1b_g_uses_prior_gate_reason:{reason}")
        if action in {"buy", "sell"}:
            for field in ("intent_reason", "primary_reason_code", "partial_intent_kind"):
                value = cand_row.get(field)
                if value not in allowed_partial_reasons:
                    errors.append(f"p1b_g_unknown_partial_reason_field:{field}={value}")
        forbidden = set(cand_row) & FORBIDDEN_ORDER_INTENT_FIELDS
        if forbidden:
            errors.append("p1b_g_order_intent_forbidden:" + "|".join(sorted(forbidden)))
        row_bad = sorted(field for field in cand_row if field in forbidden_claim_fields or any(fnmatch.fnmatch(field, pattern) for pattern in FORBIDDEN_FIELD_PATTERNS))
        if row_bad:
            errors.append("p1b_g_forbidden_order_intent_row_fields:" + "|".join(row_bad))
        for flag in ("readonly_only", "simulation_only", "not_order", "not_target_position", "not_investment_advice"):
            if cand_row.get(flag) is not True:
                errors.append(f"p1b_g_partial_flag_missing:{flag}")
    order_fields = as_set(payload.get("order_intent_fields"))
    bad_order_fields = sorted(field for field in order_fields if field in forbidden_claim_fields or any(fnmatch.fnmatch(field, pattern) for pattern in FORBIDDEN_FIELD_PATTERNS))
    if bad_order_fields:
        errors.append("p1b_g_forbidden_order_intent_fields:" + "|".join(bad_order_fields))
    pass_claim = payload.get("pass_claim") or {}
    forbidden_claims = [
        key for key in ("real_order_allowed", "broker_allowed", "quick_trade_allowed", "default_candidate", "production_default", "return_verified", "can_submit_order")
        if pass_claim.get(key) is True
    ]
    if forbidden_claims:
        errors.append("p1b_g_forbidden_pass_claim:" + "|".join(sorted(forbidden_claims)))
    return errors


def validate_fixture_payload(payload: dict[str, Any], expected_payload: dict[str, Any] | None = None) -> tuple[bool, list[str]]:
    errors: list[str] = []
    model_signal_fields = as_set(payload.get("model_signal_fields"))
    order_intent_fields = as_set(payload.get("order_intent_fields"))
    portfolio_fields = as_set(payload.get("portfolio_state_fields"))
    readiness = payload.get("execution_readiness") or {}
    config = payload.get("execution_config") or {}
    strategy_config = payload.get("strategy_config") or {}
    pass_claim = payload.get("pass_claim") or {}

    forbidden_signal = contains_forbidden(model_signal_fields, FORBIDDEN_MODEL_SIGNAL_FIELDS)
    if forbidden_signal:
        errors.append(f"model_signal_forbidden:{'|'.join(forbidden_signal)}")
    forbidden_order = contains_forbidden(order_intent_fields, FORBIDDEN_ORDER_INTENT_FIELDS)
    if forbidden_order:
        errors.append(f"order_intent_forbidden:{'|'.join(forbidden_order)}")
    if contains_forbidden(model_signal_fields | order_intent_fields, set()):
        errors.append("future_or_label_field_present")
    if not REQUIRED_PORTFOLIO_STATE_FIELDS <= portfolio_fields:
        errors.append(f"portfolio_state_missing:{'|'.join(sorted(REQUIRED_PORTFOLIO_STATE_FIELDS - portfolio_fields))}")
    if "next_open" in readiness or "execution_price" in readiness or "next_close" in readiness or "fallback_price" in readiness:
        errors.append("execution_readiness_contains_price_value")
    if readiness.get("next_open_ready") is False:
        expected = payload.get("expected_order_intent") or {}
        if expected.get("intent_action") != "skip" or expected.get("primary_reason_code") != "blocked_execution_price_unavailable":
            errors.append("blocked_next_open_expected_skip_missing")
    if config.get("execution_price_mode") != "next_open":
        errors.append("execution_price_mode_not_next_open")
    for key in ("fee_rate", "tax_rate", "min_lot_policy"):
        if key not in config:
            errors.append(f"execution_config_missing:{key}")
    if strategy_config.get("all_gates_enabled") is True:
        errors.append("all_gates_at_once_strategy_config")
    if pass_claim.get("turnover_reduction_only") is True and pass_claim.get("claims_phase_pass") is True:
        errors.append("turnover_only_pass_claim")
    if payload.get("p1b_a_fixture") is True:
        errors.extend(validate_p1b_a_payload(payload))
    if payload.get("p1b_b_fixture") is True:
        errors.extend(validate_p1b_b_payload(payload))
    if payload.get("p1b_c_fixture") is True:
        errors.extend(validate_p1b_c_payload(payload))
    if payload.get("p1b_d_fixture") is True:
        errors.extend(validate_p1b_d_payload(payload))
    if payload.get("p1b_e_fixture") is True:
        errors.extend(validate_p1b_e_payload(payload, expected_payload))
    if payload.get("p1b_f_fixture") is True:
        errors.extend(validate_p1b_f_payload(payload, expected_payload))
    if payload.get("p1b_g0_fixture") is True:
        errors.extend(validate_p1b_g0_payload(payload, expected_payload))
    if payload.get("p1b_g_fixture") is True:
        errors.extend(validate_p1b_g_payload(payload, expected_payload))
    return not errors, errors


def validate_golden(root: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    results: dict[str, Any] = {}
    for sample, expected_ok in REQUIRED_GOLDEN_SAMPLES.items():
        manifest_path = root / sample / "manifest.json"
        checks.append(check(f"{sample}_exists", manifest_path.exists(), rel(manifest_path)))
        if not manifest_path.exists():
            results[sample] = {"ok": False, "errors": ["missing_manifest"]}
            continue
        manifest = load_json(manifest_path)
        payload_path = root / sample / str(manifest.get("fixture", "fixture.json"))
        expected_path = root / sample / str(manifest.get("expected", "expected.json"))
        expected = bool(manifest.get("expected_validator_result", {}).get("ok"))
        payload = load_json(payload_path) if payload_path.exists() else {}
        expected_payload = load_json(expected_path) if expected_path.exists() else None
        actual_ok, errors = validate_fixture_payload(payload, expected_payload)
        checks.append(check(f"{sample}_expected_declared", expected == expected_ok, f"expected={expected} required={expected_ok}"))
        checks.append(check(f"{sample}_validator_result", actual_ok == expected_ok, "|".join(errors)))
        results[sample] = {"ok": actual_ok, "expected_ok": expected_ok, "errors": errors, "fixture": rel(payload_path)}
    return {"ok": all(row["status"] == "pass" for row in checks), "golden_root": rel(root), "checks": checks, "samples": results}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Portfolio Decision Optimizer v1 P1A contract scaffold.")
    parser.add_argument("--dependency", default=str(DEFAULT_DEPENDENCY))
    parser.add_argument("--golden-root", default=str(DEFAULT_GOLDEN_ROOT))
    parser.add_argument("--run-golden", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    dependency_result = validate_dependency(Path(args.dependency))
    checks = list(dependency_result["checks"])
    result: dict[str, Any] = {
        "ok": dependency_result["ok"],
        "dependency": dependency_result["dependency"],
        "checks": checks,
    }
    if args.run_golden:
        golden_result = validate_golden(Path(args.golden_root))
        result["golden"] = golden_result
        result["checks"] = checks + golden_result["checks"]
        result["ok"] = dependency_result["ok"] and golden_result["ok"]
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']}")
        for row in result["checks"]:
            print(f"{row['status']} {row['name']} {row.get('details', '')}")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
