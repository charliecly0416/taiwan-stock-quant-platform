#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLDEN_ROOT = ROOT / "data_tw/golden_samples/modular_contracts/m3"
DEFAULT_SCRIPT = ROOT / "scripts/run_daily_tw_stock_auto_update.py"
SCHEMA_VERSION = "m3.0.0"
CONTRACTS = {"daily_orchestrator", "run_registry", "auto_update"}
FORBIDDEN_ACTION_KEYS = {
    "provider_publish",
    "provider_refresh",
    "accepted_latest_switch",
    "qlib_accepted_latest_switch",
    "monitor_write",
    "monitor_scan",
    "broker_order",
    "quick_trade",
    "order_action",
    "default_strategy_switch",
    "agent_tool_expansion",
    "agent_prompt_expansion",
    "agent_action_expansion",
}
SCRIPT_FORBIDDEN_RUNTIME_PATTERNS = {
    "broker_order": ["broker_order", "submitOrder", "placeOrder", "quick-trade", "quickTrade"],
    "monitor_write": ["saveTwStockMonitorConfig", "scanTwStockMonitor", "scanAllTwStockMonitors", "updateTwStockAlert"],
}
LEGACY_PROVIDER_GATE_FLAG = "--enable-legacy-provider-publish"
LEGACY_PROVIDER_GATE_ENV = "TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH"
STRICT_E4_GATE_FLAG = "--enable-strict-e4-readonly-chain"
STRICT_E4_GATE_ENV = "TW_DAILY_AUTO_ENABLE_STRICT_E4_READONLY_CHAIN"
MODEL_SIGNAL_GATE_FLAG = "--enable-model-signal-gate"
MODEL_SIGNAL_GATE_ENV = "TW_DAILY_AUTO_ENABLE_MODEL_SIGNAL_GATE"
PBPR0_DAILY_CHAIN_REQUIRED_PATTERNS = {
    "state",
    "required_inputs",
    "refined_blocker",
    "provider_bridge_readiness_state",
    "RAW_READY_PROVIDER_STALE",
    "BLOCKED_NEEDS_TARGET_ASOF_PROVIDER_OR_BRIDGE",
    "validated_provider_candidate_or_existing_isolated_modela_artifact",
}
DAILY_FULL_CAPTURE_REQUIRED_PATTERNS = {
    "stock_ohlcv_adjusted_price",
    "twii_market_index",
    "finmind_raw_daily_price",
    "institutional_flow",
    "margin_short",
    "orthogonal_raw_archive",
    "daily_ltr_source_freshness",
    "readonly_price_twii_calendar_bridge",
    "execution_price_readiness",
    "schema_coverage_holiday_pending_evidence",
}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def err(code: str, message: str, path: Path, field: str = "") -> dict[str, str]:
    return {"code": code, "message": message, "path": rel(path), "field": field}


def resolve(base: Path, value: str) -> Path:
    p = Path(str(value))
    return p if p.is_absolute() else base / p


def validate_forbidden_action_audit(path: Path) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if not path.exists():
        return [err("audit_missing", "forbidden_action_audit is required", path, "forbidden_action_audit")]
    payload = load_json(path)
    actions = payload.get("actions")
    if not isinstance(actions, dict):
        return [err("audit_invalid", "forbidden action audit must contain actions object", path, "actions")]
    for key in FORBIDDEN_ACTION_KEYS:
        if bool(actions.get(key, False)):
            errors.append(err("forbidden_action", f"forbidden action {key} is true", path, key))
    return errors


def validators_passed(manifest: dict[str, Any]) -> bool:
    rows = manifest.get("validation_results") or []
    return isinstance(rows, list) and all(bool(row.get("ok")) for row in rows)


def validate_manifest(contract: str, artifact_path: Path) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    checked: list[str] = []
    if contract not in CONTRACTS:
        errors.append(err("unknown_contract", f"unknown M3 contract {contract}", artifact_path, "contract"))
        return {"ok": False, "contract": contract, "status": "failed", "errors": errors, "warnings": warnings, "checked_files": checked, "schema_version": ""}
    manifest_path = artifact_path / "manifest.json"
    if not manifest_path.exists():
        errors.append(err("manifest_missing", "manifest.json is required", manifest_path))
        return {"ok": False, "contract": contract, "status": "failed", "errors": errors, "warnings": warnings, "checked_files": checked, "schema_version": ""}
    checked.append(rel(manifest_path))
    manifest = load_json(manifest_path)
    schema_version = str(manifest.get("schema_version", ""))
    required = ["artifact_type", "schema_version", "run_id", "run_asof", "schedule_interval", "trigger_reason", "data_freshness_check_result", "input_artifacts", "output_artifacts", "validation_results", "latest_pointer_policy", "failure_mode", "rollback_policy", "keep_previous_latest_on_failure", "previous_latest", "proposed_latest", "committed_latest", "forbidden_action_audit"]
    if contract == "run_registry":
        required.append("checksum")
    if contract == "auto_update":
        required.extend(["poll_interval_hours", "fresh_data_detected", "no_new_data_noop", "module_call_sequence", "module_result_status", "failure_closes_without_publish", "previous_latest_preserved", "readonly_latest_update_only_after_all_validators_pass", "does_not_switch_provider_accepted_latest", "does_not_place_orders"])
    for field in required:
        if field not in manifest:
            errors.append(err("required_field_missing", f"required field {field} missing", manifest_path, field))
    if manifest.get("artifact_type") != contract:
        errors.append(err("artifact_type_mismatch", f"artifact_type must be {contract}", manifest_path, "artifact_type"))
    if schema_version != SCHEMA_VERSION:
        errors.append(err("schema_version_mismatch", f"schema_version must be {SCHEMA_VERSION}", manifest_path, "schema_version"))
    previous = manifest.get("previous_latest")
    proposed = manifest.get("proposed_latest")
    committed = manifest.get("committed_latest")
    freshness = manifest.get("data_freshness_check_result")
    failure_mode = manifest.get("failure_mode")
    passed = validators_passed(manifest)
    if freshness == "no_new_data" and committed != previous:
        errors.append(err("latest_pointer_changed_on_noop", "no_new_data must preserve previous latest", manifest_path, "committed_latest"))
    if failure_mode in {"validator_failed", "module_failed"} and committed != previous:
        errors.append(err("latest_pointer_changed_on_failure", "failed run must preserve previous latest", manifest_path, "committed_latest"))
    if failure_mode == "success" and freshness != "no_new_data":
        if not passed:
            errors.append(err("validators_not_passed", "success requires all validators to pass", manifest_path, "validation_results"))
        if committed != proposed:
            errors.append(err("latest_pointer_not_committed_on_success", "success must commit proposed readonly latest", manifest_path, "committed_latest"))
    if bool(manifest.get("provider_accepted_latest_changed")) or bool(manifest.get("qlib_accepted_latest_changed")):
        errors.append(err("accepted_latest_changed", "readonly latest must not switch provider or qlib accepted latest", manifest_path, "provider_accepted_latest_changed"))
    if contract == "auto_update":
        if manifest.get("does_not_switch_provider_accepted_latest") is not True:
            errors.append(err("accepted_latest_changed", "auto update must not switch provider accepted latest", manifest_path, "does_not_switch_provider_accepted_latest"))
        if manifest.get("does_not_place_orders") is not True:
            errors.append(err("forbidden_action", "auto update must not place orders", manifest_path, "does_not_place_orders"))
    audit_path = resolve(artifact_path, str(manifest.get("forbidden_action_audit", "forbidden_action_audit.json")))
    checked.append(rel(audit_path))
    errors.extend(validate_forbidden_action_audit(audit_path))
    return {
        "ok": not errors,
        "contract": contract,
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "warnings": warnings,
        "checked_files": checked,
        "schema_version": schema_version,
        "run_id": manifest.get("run_id", ""),
        "previous_latest": previous,
        "proposed_latest": proposed,
        "committed_latest": committed,
        "latest_pointer_policy": manifest.get("latest_pointer_policy", ""),
        "forbidden_action_audit": rel(audit_path),
    }


def validate_golden_sample(sample_dir: Path) -> dict[str, Any]:
    expected_path = sample_dir / "expected_result.json"
    if not expected_path.exists():
        return {"ok": False, "contract": "", "status": "failed", "errors": [err("expected_missing", "expected_result.json missing", expected_path)], "warnings": [], "checked_files": [], "schema_version": ""}
    expected = load_json(expected_path)
    result = validate_manifest(str(expected.get("contract", "")), sample_dir)
    actual_codes = sorted({e["code"] for e in result["errors"]})
    expected_codes = sorted(expected.get("expected_error_codes", []))
    expectation_errors = []
    if bool(result.get("ok")) != bool(expected.get("expected_ok")):
        expectation_errors.append(err("expected_ok_mismatch", "actual ok does not match expected_ok", expected_path, "expected_ok"))
    if not expected.get("expected_ok") and actual_codes != expected_codes:
        expectation_errors.append(err("expected_error_code_mismatch", f"actual={actual_codes} expected={expected_codes}", expected_path, "expected_error_codes"))
    return {**result, "sample": rel(sample_dir), "expected_ok": expected.get("expected_ok"), "expected_error_codes": expected_codes, "actual_error_codes": actual_codes, "expectation_ok": not expectation_errors, "expectation_errors": expectation_errors}


def iter_samples(root: Path, contract: str = "all") -> list[Path]:
    parents = [root / contract] if contract != "all" else sorted([p for p in root.iterdir() if p.is_dir()])
    samples = []
    for parent in parents:
        if parent.exists():
            samples.extend(sorted([p for p in parent.iterdir() if (p / "expected_result.json").exists()]))
    return samples


def run_golden(root: Path, contract: str = "all") -> dict[str, Any]:
    results = [validate_golden_sample(p) for p in iter_samples(root, contract)]
    ok = all(r.get("expectation_ok") and r.get("ok") == r.get("expected_ok") for r in results)
    return {"ok": ok, "status": "passed" if ok else "failed", "contract": contract, "schema_version": SCHEMA_VERSION, "errors": [e for r in results for e in r.get("expectation_errors", [])], "warnings": [], "checked_files": [r.get("sample", "") for r in results], "sample_count": len(results), "results": results}


def expression_contains_attr(node: ast.AST, attr: str) -> bool:
    return any(isinstance(child, ast.Attribute) and child.attr == attr for child in ast.walk(node))


def expression_contains_not_attr(node: ast.AST, attr: str) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.UnaryOp) and isinstance(child.op, ast.Not):
            if expression_contains_attr(child.operand, attr):
                return True
    return False


def guarded_ranges(tree: ast.AST) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        if expression_contains_attr(node.test, "enable_legacy_provider_publish") and expression_contains_not_attr(node.test, "skip_qlib"):
            end_lineno = getattr(node, "end_lineno", node.lineno)
            ranges.append((node.lineno, end_lineno))
    return ranges


def function_range_if_contains_enabled_gate(tree: ast.AST, function_name: str) -> tuple[int, int] | None:
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != function_name:
            continue
        has_enabled_gate = any(
            isinstance(child, ast.If)
            and isinstance(child.test, ast.UnaryOp)
            and isinstance(child.test.op, ast.Not)
            and isinstance(child.test.operand, ast.Name)
            and child.test.operand.id == "enabled"
            for child in ast.walk(node)
        )
        if has_enabled_gate:
            return (node.lineno, getattr(node, "end_lineno", node.lineno))
    return None


def line_in_ranges(line: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= line <= end for start, end in ranges)


def pattern_lines(text: str, pattern: str) -> list[int]:
    return [idx for idx, line in enumerate(text.splitlines(), start=1) if pattern in line]


def ignore_provider_refresh_constant_line(text: str, line_no: int) -> bool:
    line = text.splitlines()[line_no - 1].strip()
    return line.startswith("DNG17_PROVIDER_CANDIDATE_REFRESH_SCRIPT = ")


def is_false_safety_declaration_line(line: str, pattern: str) -> bool:
    stripped = line.strip()
    return bool(
        re.match(
            rf"^[\"'][A-Za-z0-9_]*{re.escape(pattern)}[A-Za-z0-9_]*[\"']\s*:\s*False\s*,?\s*(#.*)?$",
            stripped,
        )
    )


def forbidden_runtime_pattern_matches(
    text: str,
    *,
    patterns: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    matches: list[dict[str, Any]] = []
    ignored: list[dict[str, Any]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for pattern in patterns:
            if pattern not in line:
                continue
            if is_false_safety_declaration_line(line, pattern):
                ignored.append({"pattern": pattern, "line": line_no, "reason": "false_safety_declaration"})
                continue
            matches.append({"pattern": pattern, "line": line_no, "line_text": line.strip()[:180]})
    return matches, ignored


def legacy_gate_default_disabled_by_ast(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not any(isinstance(arg, ast.Constant) and arg.value == LEGACY_PROVIDER_GATE_FLAG for arg in node.args):
            continue
        for keyword in node.keywords:
            if keyword.arg != "default":
                continue
            value = keyword.value
            if not isinstance(value, ast.Call):
                continue
            if not isinstance(value.func, ast.Name) or value.func.id != "env_flag":
                continue
            if len(value.args) >= 2:
                first, second = value.args[:2]
                if isinstance(first, ast.Constant) and first.value == LEGACY_PROVIDER_GATE_ENV:
                    return isinstance(second, ast.Constant) and second.value is False
    return False


def env_gate_default_disabled_by_ast(tree: ast.AST, flag: str, env_name: str) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not any(isinstance(arg, ast.Constant) and arg.value == flag for arg in node.args):
            continue
        for keyword in node.keywords:
            if keyword.arg != "default":
                continue
            value = keyword.value
            if not isinstance(value, ast.Call):
                continue
            if not isinstance(value.func, ast.Name) or value.func.id != "env_flag":
                continue
            if len(value.args) >= 2:
                first, second = value.args[:2]
                if isinstance(first, ast.Constant) and first.value == env_name:
                    return isinstance(second, ast.Constant) and second.value is False
    return False


def legacy_gate_audit(text: str) -> dict[str, Any]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {
            "legacy_provider_gate_default_disabled": False,
            "legacy_provider_block_guarded": False,
            "provider_refresh_guarded": False,
            "provider_publish_guarded": False,
            "accepted_latest_call_guarded": False,
            "parse_error": True,
        }
    ranges = guarded_ranges(tree)
    provider_candidate_range = function_range_if_contains_enabled_gate(tree, "run_provider_candidate_refresh_gate")
    non_default_refresh_ranges = ranges + ([provider_candidate_range] if provider_candidate_range else [])
    refresh_lines = [
        line_no
        for line_no in pattern_lines(text, "run_option_c_yahoo_scrapling_refresh.py")
        if not ignore_provider_refresh_constant_line(text, line_no)
    ]
    publish_lines = pattern_lines(text, "publish_option_c_yahoo_scrapling_refresh.py")
    accepted_call_lines = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "publish_accepted_latest"
    ]
    return {
        "legacy_provider_gate_default_disabled": legacy_gate_default_disabled_by_ast(tree),
        "legacy_provider_block_guarded": bool(ranges),
        "provider_refresh_guarded": bool(refresh_lines) and all(line_in_ranges(line, non_default_refresh_ranges) for line in refresh_lines),
        "provider_publish_guarded": bool(publish_lines) and all(line_in_ranges(line, ranges) for line in publish_lines),
        "accepted_latest_call_guarded": bool(accepted_call_lines) and all(line_in_ranges(line, ranges) for line in accepted_call_lines),
        "parse_error": False,
    }


def audit_script(script_path: Path) -> dict[str, Any]:
    text = script_path.read_text(encoding="utf-8")
    checked = [rel(script_path)]
    production_provider_refresh_path_present = "run_option_c_yahoo_scrapling_refresh.py" in text
    production_provider_publish_path_present = (
        "provider_publish_triggered" in text and "publish_option_c_yahoo_scrapling_refresh.py" in text
    )
    production_accepted_latest_path_present = (
        "publish_accepted_latest" in text and "confirm_accepted_latest_scheduler" in text
    )
    legacy_gate_present = LEGACY_PROVIDER_GATE_FLAG in text and LEGACY_PROVIDER_GATE_ENV in text
    strict_e4_gate_present = STRICT_E4_GATE_FLAG in text and STRICT_E4_GATE_ENV in text
    model_signal_gate_present = MODEL_SIGNAL_GATE_FLAG in text and MODEL_SIGNAL_GATE_ENV in text
    daily_full_capture_patterns_present = sorted([pattern for pattern in DAILY_FULL_CAPTURE_REQUIRED_PATTERNS if pattern in text])
    daily_full_capture_missing_patterns = sorted(DAILY_FULL_CAPTURE_REQUIRED_PATTERNS - set(daily_full_capture_patterns_present))
    pbpr0_daily_chain_patterns_present = sorted([pattern for pattern in PBPR0_DAILY_CHAIN_REQUIRED_PATTERNS if pattern in text])
    pbpr0_daily_chain_missing_patterns = sorted(PBPR0_DAILY_CHAIN_REQUIRED_PATTERNS - set(pbpr0_daily_chain_patterns_present))
    daily_source_inventory_required_patterns = {
        "daily_source_inventory_v1",
        "write_daily_source_inventory",
        "summarize_finmind_stdout",
        "source_max_date",
        "row_count",
        "symbol_count",
        "archived_count",
        "evidence_path",
        "daily_source_inventory_path",
    }
    daily_source_inventory_patterns_present = sorted([pattern for pattern in daily_source_inventory_required_patterns if pattern in text])
    daily_source_inventory_missing_patterns = sorted(daily_source_inventory_required_patterns - set(daily_source_inventory_patterns_present))
    gate_audit = legacy_gate_audit(text)
    legacy_gate_default_disabled = bool(gate_audit["legacy_provider_gate_default_disabled"])
    legacy_block_guarded = bool(gate_audit["legacy_provider_block_guarded"])
    provider_refresh_guarded = bool(gate_audit["provider_refresh_guarded"])
    provider_publish_guarded = bool(gate_audit["provider_publish_guarded"])
    accepted_latest_call_guarded = bool(gate_audit["accepted_latest_call_guarded"])
    default_provider_paths_reachable = (
        (production_provider_refresh_path_present and not provider_refresh_guarded)
        or (production_provider_publish_path_present and not provider_publish_guarded)
        or (production_accepted_latest_path_present and not accepted_latest_call_guarded)
    )
    findings = {
        "trigger_interval_source": "external_cron_or_systemd; script exposes schedule_interval mapping only in M3 fixtures",
        "has_wait_noop": "today_data_window_wait" in text and "weekend_no_pending_wait" in text,
        "has_already_up_to_date_noop": "already_up_to_date" in text,
        "has_pending_retry": "set_pending_asof" in text,
        "has_readonly_snapshot_dry_run_default": "TW_READONLY_STRATEGY_SNAPSHOT_DRY_RUN" in text and "--no-latest" in text,
        "production_provider_refresh_path_present": production_provider_refresh_path_present,
        "production_provider_publish_path_present": production_provider_publish_path_present,
        "production_accepted_latest_path_present": production_accepted_latest_path_present,
        "legacy_provider_gate_present": legacy_gate_present,
        "legacy_provider_gate_default_disabled": legacy_gate_default_disabled,
        "strict_e4_readonly_gate_present": strict_e4_gate_present,
        "strict_e4_readonly_gate_default_disabled": env_gate_default_disabled_by_ast(ast.parse(text), STRICT_E4_GATE_FLAG, STRICT_E4_GATE_ENV),
        "model_signal_gate_present": model_signal_gate_present,
        "model_signal_gate_default_disabled": env_gate_default_disabled_by_ast(ast.parse(text), MODEL_SIGNAL_GATE_FLAG, MODEL_SIGNAL_GATE_ENV),
        "model_signal_gate_dry_run_summary_present": "dng9_model_signal_gate_dry_run" in text and "model_signal_gate_summary.json" in text,
        "model_signal_gate_summary_validation_present": "dng9_model_signal_gate_validation.json" in text and "validate_model_signal_gate_summary_payload" in text,
        "model_signal_gate_default_unreachable_recorded": '"model_signal_gate_default_reachable": False' in text,
        "model_signal_gate_calls_modela_pipeline": "build_tw_model_inference_input.py" in text and "run_tw_model_score_job.py" in text,
        "model_signal_gate_calls_modelb_blocker_pipeline": "build_tw_modelb_ltr_inference_input.py" in text and "run_tw_modelb_ltr_score_job.py" in text,
        "model_signal_gate_modelb_blocked_until_dng3_repair": "model_b_must_remain_blocked_until_dng3_external_source_repair" in text and "BLOCKED_INPUT_NOT_READY" in text,
        "model_signal_gate_forbidden_actions_audit_present": "MODEL_SIGNAL_GATE_FORBIDDEN_ACTIONS_FALSE" in text and '"accepted_latest_switch_triggered": False' in text and '"target_position_or_weight_generated": False' in text,
        "pbpr0_daily_chain_schema_fields_present": not pbpr0_daily_chain_missing_patterns,
        "pbpr0_daily_chain_schema_patterns_present": pbpr0_daily_chain_patterns_present,
        "pbpr0_daily_chain_schema_missing_patterns": pbpr0_daily_chain_missing_patterns,
        "pbpr0_daily_chain_refined_blocker_present": "PBPR0_REFINED_PROVIDER_BLOCKER" in text and "validated_provider_candidate_or_existing_isolated_modela_artifact" in text,
        "pbpr0_daily_chain_provider_bridge_state_present": "BLOCKED_NEEDS_TARGET_ASOF_PROVIDER_OR_BRIDGE" in text,
        "pbpr0_skipped_asof_ledger_schema_fields_present": '"refined_blocker": chain_status.get("refined_blocker", {})' in text and '"provider_bridge_readiness_state": chain_status.get("provider_bridge_readiness_state", "")' in text,
        "strict_e4_forces_orthogonal_finmind_full_scope": "finmind_scope_overridden_for_strict_e4" in text and "--no-institutional" in text and "--no-margin" in text,
        "strict_e4_missing_model_a_blocks_without_synthesis": "blocked_missing_model_a" in text and "daily auto does not synthesize qlib base signals" in text,
        "strict_e4_yz2r_calendar_next_day_script": "build_phase_yz2r_execution_price_readiness.py" in text,
        "daily_full_capture_accounting_present": "daily_full_capture_accounting" in text and "DAILY_FULL_CAPTURE_ACCOUNTING_SCHEMA_VERSION" in text,
        "daily_full_capture_categories_present": daily_full_capture_patterns_present,
        "daily_full_capture_missing_categories": daily_full_capture_missing_patterns,
        "daily_full_capture_finalized_before_returns": "finalize_job(job, job_dir=job_dir, asof=asof, args=args)" in text,
        "daily_full_capture_blocks_production_trade": '"production_trade_enabled": False' in text,
        "daily_full_capture_records_accepted_latest_boundary": '"accepted_latest_switch_triggered"' in text,
        "daily_source_inventory_present": "daily_source_inventory_v1" in text and "write_daily_source_inventory" in text,
        "daily_source_inventory_patterns_present": daily_source_inventory_patterns_present,
        "daily_source_inventory_missing_patterns": daily_source_inventory_missing_patterns,
        "daily_source_inventory_reads_finmind_stdout": "parse_stdout_json" in text and "finmind_stdout.txt" in text,
        "daily_source_inventory_has_source_metrics": all(pattern in text for pattern in ["source_max_date", "row_count", "symbol_count", "checksum", "evidence_path"]),
        "finmind_segmented_tolerant_update_present": "run_finmind_segmented_update" in text and "segment_results" in text and "finmind_update_warning" in text,
        "finmind_segmented_merged_stdout_present": "merge_finmind_segment_payloads" in text and "finmind_stdout.txt" in text and "segment_status" in text,
        "finmind_quota_scope_control_present": "finmind_quota_scope_control_v1" in text and "provider_402_quota_or_payment_required" in text and "cooldown_until" in text,
        "finmind_segment_cache_present": "FINMIND_SEGMENT_CACHE_ROOT" in text and "reuse_success_cache" in text and "TW_DAILY_AUTO_FINMIND_PROVIDER_ERROR_COOLDOWN_HOURS" in text,
        "finmind_segment_cache_origin_gate_present": "finmind_segment_cache_origin_issue" in text and "outside_repo" in text and "outside_daily_auto_ops" in text,
        "legacy_provider_block_guarded": legacy_block_guarded,
        "provider_refresh_guarded": provider_refresh_guarded,
        "provider_publish_guarded": provider_publish_guarded,
        "accepted_latest_call_guarded": accepted_latest_call_guarded,
        "legacy_gate_parse_error": bool(gate_audit["parse_error"]),
        "default_provider_refresh_reachable": production_provider_refresh_path_present and not provider_refresh_guarded,
        "default_provider_publish_reachable": production_provider_publish_path_present and not provider_publish_guarded,
        "default_accepted_latest_reachable": production_accepted_latest_path_present and not accepted_latest_call_guarded,
        "readonly_latest_pointer_distinct": "not_provider_accepted_latest" in text and "not_trade_target_latest" in text,
        "broker_order_patterns_present": [],
        "broker_order_runtime_matches": [],
        "broker_order_ignored_safety_declarations": [],
        "monitor_write_patterns_present": [],
        "monitor_write_runtime_matches": [],
        "monitor_write_ignored_safety_declarations": [],
    }
    for category, patterns in SCRIPT_FORBIDDEN_RUNTIME_PATTERNS.items():
        matched_details, ignored_details = forbidden_runtime_pattern_matches(text, patterns=patterns)
        matched = sorted({str(row.get("pattern") or "") for row in matched_details if row.get("pattern")})
        if category == "broker_order":
            findings["broker_order_patterns_present"] = matched
            findings["broker_order_runtime_matches"] = matched_details
            findings["broker_order_ignored_safety_declarations"] = ignored_details
        if category == "monitor_write":
            findings["monitor_write_patterns_present"] = matched
            findings["monitor_write_runtime_matches"] = matched_details
            findings["monitor_write_ignored_safety_declarations"] = ignored_details
    warnings = []
    if production_provider_refresh_path_present or production_provider_publish_path_present:
        warnings.append(err("legacy_provider_publish_path_present", "legacy provider refresh/publish code exists but must remain behind an explicit non-default gate", script_path, "provider_publish"))
    if production_accepted_latest_path_present:
        warnings.append(err("legacy_accepted_latest_path_present", "legacy accepted latest code exists but must remain behind an explicit non-default gate", script_path, "accepted_latest"))
    errors = []
    if findings["default_provider_refresh_reachable"]:
        errors.append(err("default_provider_refresh_reachable", "M3 default path must not reach provider refresh", script_path, "provider_refresh"))
    if findings["default_provider_publish_reachable"]:
        errors.append(err("default_provider_publish_reachable", "M3 default path must not reach provider publish", script_path, "provider_publish"))
    if findings["default_accepted_latest_reachable"]:
        errors.append(err("default_accepted_latest_reachable", "M3 default path must not reach accepted latest switching", script_path, "accepted_latest"))
    if (production_provider_refresh_path_present or production_provider_publish_path_present or production_accepted_latest_path_present) and not legacy_gate_present:
        errors.append(err("legacy_provider_gate_missing", "legacy provider/latest path must require an explicit non-default gate", script_path, "enable_legacy_provider_publish"))
    if legacy_gate_present and not legacy_gate_default_disabled:
        errors.append(err("legacy_provider_gate_default_enabled", "legacy provider/latest gate must default to disabled", script_path, "enable_legacy_provider_publish"))
    if strict_e4_gate_present and not findings["strict_e4_readonly_gate_default_disabled"]:
        errors.append(err("strict_e4_gate_default_enabled", "strict E4 readonly chain gate must default to disabled", script_path, "enable_strict_e4_readonly_chain"))
    if model_signal_gate_present and not findings["model_signal_gate_default_disabled"]:
        errors.append(err("model_signal_gate_default_enabled", "DNG9 model signal gate must default to disabled", script_path, "enable_model_signal_gate"))
    if model_signal_gate_present and not findings["model_signal_gate_dry_run_summary_present"]:
        errors.append(err("model_signal_gate_dry_run_summary_missing", "DNG9 model signal gate must emit dry-run summary evidence", script_path, "model_signal_gate_summary"))
    if model_signal_gate_present and not findings["model_signal_gate_summary_validation_present"]:
        errors.append(err("model_signal_gate_validation_missing", "DNG9 model signal gate summary must have validation output", script_path, "dng9_model_signal_gate_validation"))
    if model_signal_gate_present and not findings["model_signal_gate_default_unreachable_recorded"]:
        errors.append(err("model_signal_gate_default_boundary_missing", "daily auto job must record model_signal_gate_default_reachable false", script_path, "model_signal_gate_default_reachable"))
    if model_signal_gate_present and not findings["model_signal_gate_calls_modela_pipeline"]:
        errors.append(err("model_signal_gate_modela_pipeline_missing", "enabled DNG9 gate must call DNG7 Model A input/score pipeline", script_path, "model_a_score_job"))
    if model_signal_gate_present and not findings["model_signal_gate_calls_modelb_blocker_pipeline"]:
        errors.append(err("model_signal_gate_modelb_pipeline_missing", "enabled DNG9 gate must call DNG8 Model B blocker/score pipeline", script_path, "model_b_ltr_score_job"))
    if model_signal_gate_present and not findings["model_signal_gate_modelb_blocked_until_dng3_repair"]:
        errors.append(err("model_signal_gate_modelb_blocker_missing", "DNG9 must keep Model B LTR signal blocked until DNG3 external source repair passes", script_path, "model_b_status"))
    if model_signal_gate_present and not findings["model_signal_gate_forbidden_actions_audit_present"]:
        errors.append(err("model_signal_gate_forbidden_audit_missing", "DNG9 model signal gate must explicitly audit forbidden actions false", script_path, "forbidden_actions_audit"))
    if not findings["pbpr0_daily_chain_schema_fields_present"]:
        errors.append(err("pbpr0_daily_chain_schema_missing", "daily_chain_status must emit PBPR0/DASF state, required_inputs, refined_blocker, and provider_bridge_readiness_state", script_path, ",".join(findings["pbpr0_daily_chain_schema_missing_patterns"])))
    if not findings["pbpr0_daily_chain_refined_blocker_present"]:
        errors.append(err("pbpr0_refined_blocker_missing", "daily_chain_status must expose the DASF2 refined blocker for target-asof provider/bridge readiness", script_path, "refined_blocker"))
    if not findings["pbpr0_daily_chain_provider_bridge_state_present"]:
        errors.append(err("pbpr0_provider_bridge_state_missing", "daily_chain_status must expose provider bridge readiness state", script_path, "provider_bridge_readiness_state"))
    if not findings["pbpr0_skipped_asof_ledger_schema_fields_present"]:
        errors.append(err("pbpr0_skipped_asof_ledger_schema_missing", "skipped_asof_ledger must summarize PBPR0 state/refined blocker/readiness fields", script_path, "skipped_asof_ledger"))
    if strict_e4_gate_present and not findings["strict_e4_forces_orthogonal_finmind_full_scope"]:
        errors.append(err("strict_e4_orthogonal_source_scope_missing", "strict E4 readonly chain must not use FinMind daily scope that skips institutional/margin", script_path, "finmind_scope"))
    if strict_e4_gate_present and not findings["strict_e4_missing_model_a_blocks_without_synthesis"]:
        errors.append(err("strict_e4_model_a_blocker_missing", "strict E4 readonly chain must block when YZ1 model_a is missing instead of synthesizing it", script_path, "model_a_manifest"))
    if not findings["daily_full_capture_accounting_present"]:
        errors.append(err("daily_full_capture_accounting_missing", "daily auto must emit daily_full_capture_accounting evidence", script_path, "daily_full_capture_accounting"))
    if findings["daily_full_capture_missing_categories"]:
        errors.append(err("daily_full_capture_categories_missing", "daily_full_capture_accounting must enumerate all required capture categories", script_path, ",".join(findings["daily_full_capture_missing_categories"])))
    if not findings["daily_full_capture_finalized_before_returns"]:
        errors.append(err("daily_full_capture_finalizer_missing", "daily auto must finalize accounting before terminal job writes", script_path, "finalize_job"))
    if not findings["daily_full_capture_blocks_production_trade"]:
        errors.append(err("daily_full_capture_trade_boundary_missing", "daily_full_capture_accounting must explicitly keep production_trade_enabled false", script_path, "production_trade_enabled"))
    if not findings["daily_full_capture_records_accepted_latest_boundary"]:
        errors.append(err("daily_full_capture_latest_boundary_missing", "daily_full_capture_accounting must record accepted latest boundary", script_path, "accepted_latest_switch_triggered"))
    if not findings["daily_source_inventory_present"]:
        errors.append(err("daily_source_inventory_missing", "daily auto must emit daily_source_inventory evidence", script_path, "daily_source_inventory"))
    if findings["daily_source_inventory_missing_patterns"]:
        errors.append(err("daily_source_inventory_patterns_missing", "daily_source_inventory must include source metrics and FinMind stdout parsing", script_path, ",".join(findings["daily_source_inventory_missing_patterns"])))
    if not findings["daily_source_inventory_reads_finmind_stdout"]:
        errors.append(err("daily_source_inventory_finmind_stdout_missing", "daily_source_inventory must parse FinMind stdout evidence", script_path, "finmind_stdout"))
    if not findings["daily_source_inventory_has_source_metrics"]:
        errors.append(err("daily_source_inventory_metrics_missing", "daily_source_inventory must include source_max_date,row_count,symbol_count,checksum,evidence_path", script_path, "source_metrics"))
    if not findings["finmind_segmented_tolerant_update_present"]:
        errors.append(err("finmind_segmented_update_missing", "daily auto must run FinMind capture as segmented tolerant steps so one timeout does not erase other source evidence", script_path, "finmind_segmented_update"))
    if not findings["finmind_segmented_merged_stdout_present"]:
        errors.append(err("finmind_segmented_merged_stdout_missing", "daily auto must emit merged finmind_stdout.txt with per-segment status evidence", script_path, "finmind_stdout"))
    if not findings["finmind_quota_scope_control_present"]:
        errors.append(err("finmind_quota_scope_control_missing", "daily auto must classify FinMind 402/rate-limit and write cooldown evidence", script_path, "finmind_quota_scope_control"))
    if not findings["finmind_segment_cache_present"]:
        errors.append(err("finmind_segment_cache_missing", "daily auto must support segment cache reuse to avoid repeating successful or cooled-down FinMind calls", script_path, "finmind_segment_cache"))
    if not findings["finmind_segment_cache_origin_gate_present"]:
        errors.append(err("finmind_segment_cache_origin_gate_missing", "daily auto must reject cache stdout/stderr outside daily auto ops or from pytest/temp origins", script_path, "finmind_segment_cache_origin"))
    if legacy_gate_present and not legacy_block_guarded:
        errors.append(err("legacy_provider_block_not_guarded", "legacy provider/latest block must be guarded by enable_legacy_provider_publish", script_path, "enable_legacy_provider_publish"))
    if gate_audit["parse_error"]:
        errors.append(err("script_parse_error", "script could not be parsed for legacy gate audit", script_path, "ast"))
    if findings["broker_order_patterns_present"]:
        errors.append(err("script_broker_order_pattern", "script contains broker/order runtime pattern", script_path, "broker_order"))
    if findings["monitor_write_patterns_present"]:
        errors.append(err("script_monitor_write_pattern", "script contains monitor write runtime pattern", script_path, "monitor_write"))
    return {"ok": not errors, "status": "passed" if not errors else "failed", "errors": errors, "warnings": warnings, "checked_files": checked, "script_audit": findings}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase M3 daily orchestrator dry-run and latest pointer boundary.")
    parser.add_argument("--contract", default="all", choices=["all", *sorted(CONTRACTS)])
    parser.add_argument("--artifact-path", default="")
    parser.add_argument("--golden-root", default=str(DEFAULT_GOLDEN_ROOT))
    parser.add_argument("--run-golden", action="store_true")
    parser.add_argument("--audit-script", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.audit_script:
        result = audit_script(Path(args.audit_script))
    elif args.run_golden:
        result = run_golden(Path(args.golden_root), args.contract)
    elif args.artifact_path and args.contract != "all":
        result = validate_manifest(args.contract, Path(args.artifact_path))
    else:
        result = {"ok": False, "status": "failed", "errors": [err("arguments_invalid", "use --run-golden, --audit-script, or --contract with --artifact-path", ROOT)], "warnings": [], "checked_files": []}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result.get('ok')}")
        print(f"status={result.get('status')}")
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
