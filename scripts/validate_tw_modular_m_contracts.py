#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLDEN_ROOT = ROOT / "data_tw/golden_samples/modular_contracts/m1"
SCHEMA_VERSION = "m1.0.0"

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
FORBIDDEN_FIELD_PATTERNS = [
    r"^future_return_.*",
    r"^future_excess_return_.*",
    r"^forward_return_.*",
    r"^label_.*",
    r"^relevance_.*",
    r"realized_pnl",
    r"target_position",
    r"target_weight",
    r"order_qty",
    r"execution_price",
    r"broker_order_id",
    r"provider_publish_status",
    r"accepted_latest_status",
    r"provider_accepted_latest_switched",
    r"qlib_accepted_latest_switched",
    r"default_strategy_selected",
]
FORBIDDEN_FRONTEND_TEXT = ["买入建议", "卖出建议", "目标仓位", "目标权重", "保证收益", "胜率保证", "自动下单", "实盘已执行"]
FORBIDDEN_AGENT_SEMANTICS = ["应该买入", "应该卖出", "目标仓位", "目标权重", "保证收益", "胜率承诺", "自动下单"]
FORBIDDEN_REQUEST_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
FORBIDDEN_REQUEST_PATH_PARTS = ["monitor", "broker", "quick-trade", "orders", "provider/publish", "accepted-latest"]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_columns(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        return next(reader, [])


@dataclass(frozen=True)
class ContractSpec:
    name: str
    artifact_type: str
    required_manifest: list[str]
    required_columns: list[str] = field(default_factory=list)
    data_file_key: str | None = None
    required_audits: list[str] = field(default_factory=lambda: ["forbidden_action_audit"])
    state_machine: str | None = None
    frontend: bool = False
    agent: bool = False
    default_candidate: bool = False


SPECS: dict[str, ContractSpec] = {
    "data_source": ContractSpec("data_source", "data_source", ["artifact_type", "schema_version", "source_name", "provider", "raw_path", "symbol_mapping_version", "asof_date", "available_at", "coverage_audit", "schema_audit", "no_provider_publish", "no_accepted_latest_switch"]),
    "data_ingestion": ContractSpec("data_ingestion", "data_ingestion", ["artifact_type", "schema_version", "run_id", "source_name", "provider", "raw_path", "normalized_path", "symbol_mapping_version", "asof_date", "available_at", "coverage_audit", "schema_audit", "no_provider_publish", "no_accepted_latest_switch"], ["date", "instrument", "open", "close"], "normalized_path"),
    "feature_artifact": ContractSpec("feature_artifact", "feature_artifact", ["artifact_type", "schema_version", "feature_set_name", "run_id", "source_data_artifact", "lookback_window", "signal_asof", "available_at", "pit_policy", "forbidden_future_field_audit", "coverage_audit", "output_path"], ["feature_date", "instrument", "feature_name", "feature_value", "source_data_artifact", "lookback_window", "signal_asof", "available_at", "pit_policy"], "output_path", ["forbidden_action_audit", "forbidden_future_field_audit"]),
    "price_store": ContractSpec("price_store", "price_store", ["artifact_type", "schema_version", "run_id", "price_source", "source_data_artifact", "price_path", "adjustment_policy", "coverage_audit", "execution_availability_audit", "no_provider_publish", "no_accepted_latest_switch"], ["price_date", "instrument", "open", "close", "adj_factor", "tradable_flag", "halt_flag", "next_day_execution_availability", "price_source", "adjustment_policy"], "price_path"),
    "model_signal": ContractSpec("model_signal", "model_signal", ["artifact_type", "schema_version", "model_name", "model_family", "source_feature_artifact", "model_adapter", "output_artifact", "no_provider_publish", "no_accepted_latest_switch"]),
    "strategy_rule": ContractSpec("strategy_rule", "strategy_rule", ["artifact_type", "schema_version", "strategy_rule", "dependency_yaml", "required_core_fields", "allowed_consumers", "forbidden_consumers", "production_allowed", "diagnostic_only"]),
    "readonly_replay_window": ContractSpec("readonly_replay_window", "readonly_replay_window", ["artifact_type", "schema_version", "window_name", "replay_window_policy", "order_intent_artifact", "price_store_artifact", "execution_config", "readonly_index_update", "get_only_api", "no_provider_publish", "no_accepted_latest_switch"]),
    "daily_orchestrator": ContractSpec("daily_orchestrator", "daily_orchestrator_run", ["artifact_type", "schema_version", "run_id", "run_asof", "schedule_interval", "trigger_reason", "data_freshness_check_result", "input_artifacts", "output_artifacts", "validation_results", "latest_pointer_policy", "failure_mode", "rollback_policy", "keep_previous_latest_on_failure", "previous_latest", "committed_latest"], state_machine="daily"),
    "run_registry": ContractSpec("run_registry", "run_registry_record", ["artifact_type", "schema_version", "run_id", "run_asof", "schedule_interval", "trigger_reason", "data_freshness_check_result", "input_artifacts", "output_artifacts", "validation_results", "latest_pointer_policy", "failure_mode", "rollback_policy", "keep_previous_latest_on_failure", "previous_latest", "committed_latest", "checksum"], state_machine="registry"),
    "auto_update": ContractSpec("auto_update", "auto_update_orchestrator_run", ["artifact_type", "schema_version", "poll_interval_hours", "fresh_data_detected", "no_new_data_noop", "module_call_sequence", "module_result_status", "retry_policy", "failure_closes_without_publish", "previous_latest_preserved", "readonly_latest_update_only_after_all_validators_pass", "does_not_switch_provider_accepted_latest", "does_not_place_orders", "previous_latest", "committed_latest"], state_machine="auto"),
    "analysis_artifact": ContractSpec("analysis_artifact", "analysis_artifact", ["artifact_type", "schema_version", "analysis_name", "run_id", "input_artifacts", "output_report", "quality_status", "no_replay", "no_strategy_return_conclusion", "not_valid_strategy_evidence", "claim_support_audit"]),
    "frontend_readonly_display": ContractSpec("frontend_readonly_display", "frontend_readonly_display", ["artifact_type", "schema_version", "allowed_primary_fields", "allowed_audit_fields", "hidden_audit_fields", "forbidden_text", "forbidden_requests", "component_boundary", "get_only_api_dependency", "network_request_audit", "readonly_boundary_audit"], ["method", "path"], None, ["network_request_audit", "readonly_boundary_audit"], frontend=True),
    "agent_readonly_context": ContractSpec("agent_readonly_context", "agent_readonly_context", ["artifact_type", "schema_version", "allowed_context_sources", "readonly_artifact_only", "allowed_question_types", "forbidden_answer_semantics", "forbidden_tool_calls", "no_order_action", "no_target_position", "no_provider_publish", "no_accepted_latest_switch", "no_monitor_write", "no_broker_or_order", "not_in_m0_m6_implementation_scope", "future_agent_phase_required", "agent_tool_audit", "response_semantics_audit"], ["tool_name", "allowed"], None, ["agent_tool_audit", "response_semantics_audit"], agent=True),
    "frontend_agent_panel": ContractSpec("frontend_agent_panel", "frontend_agent_panel", ["artifact_type", "schema_version", "readonly_artifact_only", "allowed_context_sources", "allowed_question_types", "forbidden_answer_semantics", "forbidden_tool_calls", "no_order_action", "no_target_position", "no_provider_publish", "no_accepted_latest_switch", "no_monitor_write", "no_broker_or_order", "not_in_m0_m6_implementation_scope", "future_agent_phase_required", "panel_boundary_audit"], None, None, ["panel_boundary_audit"], agent=True),
    "default_candidate_decision": ContractSpec("default_candidate_decision", "default_candidate_decision", ["artifact_type", "schema_version", "candidate_id", "model_name", "strategy_rule", "comparison_window", "required_oos_evidence", "risk_metrics", "diagnostic_only", "not_valid_strategy_evidence", "current_default_preserved", "rollback_policy", "user_confirmation_required"], default_candidate=True),
}


def error(code: str, message: str, path: Path, field: str = "") -> dict[str, str]:
    return {"code": code, "message": message, "path": rel(path), "field": field}


def resolve_artifact_file(base: Path, value: Any) -> Path:
    path = Path(str(value))
    if path.is_absolute():
        return path
    return base / path


def iter_field_names(obj: Any) -> list[str]:
    names: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            names.append(str(key))
            names.extend(iter_field_names(value))
    elif isinstance(obj, list):
        for item in obj:
            names.extend(iter_field_names(item))
    return names


def forbidden_field_matches(fields: list[str]) -> list[str]:
    matches: list[str] = []
    for field_name in fields:
        for pattern in FORBIDDEN_FIELD_PATTERNS:
            if re.fullmatch(pattern, field_name) or pattern == field_name:
                matches.append(field_name)
    return sorted(set(matches))


def validate_forbidden_action_audit(audit_path: Path, errors: list[dict[str, str]]) -> None:
    if not audit_path.exists():
        errors.append(error("audit_missing", "forbidden action audit is required", audit_path))
        return
    audit = load_json(audit_path)
    actions = audit.get("actions")
    if not isinstance(actions, dict):
        errors.append(error("audit_invalid", "forbidden action audit must contain actions object", audit_path, "actions"))
        return
    for key in FORBIDDEN_ACTION_KEYS:
        if bool(actions.get(key, False)):
            errors.append(error("forbidden_action", f"forbidden action {key} is true", audit_path, key))


def validate_state_machine(spec: ContractSpec, manifest: dict[str, Any], manifest_path: Path, errors: list[dict[str, str]]) -> None:
    previous = manifest.get("previous_latest")
    committed = manifest.get("committed_latest")
    proposed = manifest.get("proposed_latest")
    validation_results = manifest.get("validation_results") or []
    validators_passed = all(bool(item.get("ok")) for item in validation_results) if isinstance(validation_results, list) else False
    freshness = manifest.get("data_freshness_check_result")
    failure_mode = manifest.get("failure_mode")
    if spec.state_machine in {"daily", "registry"}:
        if freshness == "no_new_data" and committed != previous:
            errors.append(error("latest_pointer_changed_on_noop", "no_new_data must preserve previous latest", manifest_path, "committed_latest"))
        if failure_mode in {"validator_failed", "module_failed"} and committed != previous:
            errors.append(error("latest_pointer_changed_on_failure", "failed run must preserve previous latest", manifest_path, "committed_latest"))
        if failure_mode == "success" and proposed and committed != proposed:
            errors.append(error("latest_pointer_not_committed_on_success", "successful run should commit proposed readonly latest", manifest_path, "committed_latest"))
        if failure_mode == "success" and not validators_passed:
            errors.append(error("validators_not_passed", "success requires all validators to pass", manifest_path, "validation_results"))
    if spec.state_machine == "auto":
        if freshness == "no_new_data" and (not manifest.get("no_new_data_noop") or committed != previous):
            errors.append(error("latest_pointer_changed_on_noop", "auto no_new_data must noop and preserve latest", manifest_path, "committed_latest"))
        if failure_mode in {"validator_failed", "module_failed"} and committed != previous:
            errors.append(error("latest_pointer_changed_on_failure", "auto failed run must preserve previous latest", manifest_path, "committed_latest"))
        if failure_mode == "success" and (not manifest.get("readonly_latest_update_only_after_all_validators_pass") or not validators_passed):
            errors.append(error("validators_not_passed", "auto success requires all validators to pass before readonly latest update", manifest_path, "validation_results"))
        if not manifest.get("does_not_switch_provider_accepted_latest"):
            errors.append(error("forbidden_action", "auto update attempted provider accepted latest switch", manifest_path, "does_not_switch_provider_accepted_latest"))
        if not manifest.get("does_not_place_orders"):
            errors.append(error("forbidden_action", "auto update attempted order action", manifest_path, "does_not_place_orders"))


def validate_frontend(manifest: dict[str, Any], base: Path, errors: list[dict[str, str]]) -> None:
    forbidden_text = manifest.get("visible_text", [])
    for text in forbidden_text:
        for banned in FORBIDDEN_FRONTEND_TEXT:
            if banned in str(text):
                errors.append(error("forbidden_text", f"forbidden frontend text: {banned}", base / "manifest.json", "visible_text"))
    audit_path = resolve_artifact_file(base, manifest.get("network_request_audit", "network_request_audit.json"))
    if audit_path.exists():
        audit = load_json(audit_path)
        for idx, req in enumerate(audit.get("requests", [])):
            method = str(req.get("method", "GET")).upper()
            path = str(req.get("path", ""))
            if method in FORBIDDEN_REQUEST_METHODS:
                errors.append(error("forbidden_request", f"forbidden method {method}", audit_path, f"requests[{idx}].method"))
            if any(part in path for part in FORBIDDEN_REQUEST_PATH_PARTS) and method != "GET":
                errors.append(error("forbidden_request", f"forbidden request path {path}", audit_path, f"requests[{idx}].path"))
    boundary_path = resolve_artifact_file(base, manifest.get("readonly_boundary_audit", "readonly_boundary_audit.json"))
    if boundary_path.exists():
        boundary = load_json(boundary_path)
        for field in ["local_replay", "local_ranking", "local_signal_compute"]:
            if field not in boundary:
                errors.append(error("boundary_audit_missing_field", f"readonly boundary audit missing {field}", boundary_path, field))
            elif boundary.get(field) is not False:
                errors.append(error("readonly_boundary_violation", f"{field} must be false", boundary_path, field))


def validate_agent(manifest: dict[str, Any], base: Path, errors: list[dict[str, str]]) -> None:
    for flag in ["readonly_artifact_only", "no_order_action", "no_target_position", "no_provider_publish", "no_accepted_latest_switch", "no_monitor_write", "no_broker_or_order", "not_in_m0_m6_implementation_scope", "future_agent_phase_required"]:
        if manifest.get(flag) is not True:
            errors.append(error("required_flag_false", f"{flag} must be true", base / "manifest.json", flag))
    for item in manifest.get("answer_samples", []):
        for banned in FORBIDDEN_AGENT_SEMANTICS:
            if banned in str(item):
                errors.append(error("forbidden_semantics", f"forbidden agent semantics: {banned}", base / "manifest.json", "answer_samples"))
    for key in ["agent_tool_audit", "response_semantics_audit", "panel_boundary_audit"]:
        if key not in manifest:
            continue
        path = resolve_artifact_file(base, manifest[key])
        if not path.exists():
            continue
        audit = load_json(path)
        if key == "response_semantics_audit" and int(audit.get("forbidden_semantics_count", 0)) > 0:
            errors.append(error("forbidden_semantics", "response semantics audit contains forbidden semantics", path, "forbidden_semantics_count"))
        for idx, tool in enumerate(audit.get("tools", [])):
            if tool.get("allowed") is not True:
                errors.append(error("forbidden_tool_call", "forbidden or expanded tool/action is present", path, f"tools[{idx}]"))
        for field in ["prompt_expanded", "tool_permissions_expanded", "action_entry_expanded"]:
            if audit.get(field) is True:
                errors.append(error("agent_boundary_expanded", f"{field} must not be true in M0-M6", path, field))


def validate_default_candidate(manifest: dict[str, Any], manifest_path: Path, errors: list[dict[str, str]]) -> None:
    if manifest.get("user_confirmation_required") is not True:
        errors.append(error("user_confirmation_missing", "default candidate decision requires user confirmation", manifest_path, "user_confirmation_required"))
    if manifest.get("current_default_preserved") is not True:
        errors.append(error("default_not_preserved", "current default must be preserved unless separately approved", manifest_path, "current_default_preserved"))
    if manifest.get("diagnostic_only") and not manifest.get("not_valid_strategy_evidence"):
        errors.append(error("diagnostic_used_as_strategy_evidence", "diagnostic-only candidate must not be valid strategy evidence", manifest_path, "not_valid_strategy_evidence"))


def validate_contract(contract: str, artifact_path: Path) -> dict[str, Any]:
    if contract not in SPECS:
        return {"ok": False, "contract": contract, "status": "unknown_contract", "errors": [error("unknown_contract", f"unknown contract {contract}", artifact_path)], "warnings": [], "checked_files": [], "schema_version": ""}
    spec = SPECS[contract]
    base = artifact_path.resolve()
    manifest_path = base / "manifest.json"
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    checked: list[str] = []
    schema_version = ""
    if not manifest_path.exists():
        errors.append(error("manifest_missing", "manifest.json is required", manifest_path))
        return {"ok": False, "contract": contract, "status": "failed", "errors": errors, "warnings": warnings, "checked_files": checked, "schema_version": schema_version}
    checked.append(rel(manifest_path))
    manifest = load_json(manifest_path)
    schema_version = str(manifest.get("schema_version", ""))
    if manifest.get("artifact_type") != spec.artifact_type:
        errors.append(error("artifact_type_mismatch", f"artifact_type must be {spec.artifact_type}", manifest_path, "artifact_type"))
    if schema_version != SCHEMA_VERSION:
        errors.append(error("schema_version_mismatch", f"schema_version must be {SCHEMA_VERSION}", manifest_path, "schema_version"))
    for field_name in spec.required_manifest:
        if field_name not in manifest:
            errors.append(error("required_field_missing", "required manifest field is missing", manifest_path, field_name))
    for field_name in ["no_provider_publish", "no_accepted_latest_switch"]:
        if field_name in manifest and manifest.get(field_name) is not True:
            errors.append(error("required_flag_false", f"{field_name} must be true", manifest_path, field_name))

    schema_path = base / "schema.json"
    if schema_path.exists():
        checked.append(rel(schema_path))
        schema = load_json(schema_path)
        schema_fields = [str(col.get("name", col)) if isinstance(col, dict) else str(col) for col in schema.get("columns", [])]
        if spec.required_columns:
            for col in spec.required_columns:
                if col not in schema_fields:
                    errors.append(error("required_column_missing", "required data column is missing from schema", schema_path, col))
        for match in forbidden_field_matches(schema_fields):
            errors.append(error("forbidden_field", f"forbidden schema field {match}", schema_path, match))
    elif spec.required_columns:
        errors.append(error("schema_missing", "schema.json is required for data-bearing contracts", schema_path))

    if spec.data_file_key and spec.data_file_key in manifest:
        data_path = resolve_artifact_file(base, manifest[spec.data_file_key])
        if data_path.exists():
            checked.append(rel(data_path))
            if data_path.suffix == ".csv":
                columns = read_csv_columns(data_path)
                for col in spec.required_columns:
                    if col not in columns:
                        errors.append(error("required_column_missing", "required data column is missing from data file", data_path, col))
                for match in forbidden_field_matches(columns):
                    errors.append(error("forbidden_field", f"forbidden data field {match}", data_path, match))
        else:
            errors.append(error("file_missing", "declared data file is missing", data_path, spec.data_file_key))

    for audit_key in spec.required_audits:
        audit_value = manifest.get(audit_key, f"{audit_key}.json")
        audit_path = resolve_artifact_file(base, audit_value)
        if not audit_path.exists():
            errors.append(error("audit_missing", f"{audit_key} is required", audit_path, audit_key))
            continue
        checked.append(rel(audit_path))
        if audit_key == "forbidden_action_audit":
            validate_forbidden_action_audit(audit_path, errors)

    for match in forbidden_field_matches(iter_field_names(manifest)):
        errors.append(error("forbidden_field", f"forbidden manifest field {match}", manifest_path, match))

    if spec.state_machine:
        validate_state_machine(spec, manifest, manifest_path, errors)
    if spec.frontend:
        validate_frontend(manifest, base, errors)
    if spec.agent:
        validate_agent(manifest, base, errors)
    if spec.default_candidate:
        validate_default_candidate(manifest, manifest_path, errors)

    status = "passed" if not errors else "failed"
    return {"ok": not errors, "contract": contract, "status": status, "errors": errors, "warnings": warnings, "checked_files": checked, "schema_version": schema_version}


def validate_golden_sample(sample_dir: Path) -> dict[str, Any]:
    expected_path = sample_dir / "expected_result.json"
    if not expected_path.exists():
        return {"ok": False, "contract": "", "status": "expected_missing", "errors": [error("expected_missing", "expected_result.json is required", expected_path)], "warnings": [], "checked_files": [], "schema_version": ""}
    expected = load_json(expected_path)
    contract = expected.get("contract", "")
    result = validate_contract(contract, sample_dir)
    actual_codes = sorted({item["code"] for item in result["errors"]})
    expected_codes = sorted(expected.get("expected_error_codes", []))
    expected_ok = bool(expected.get("expected_ok"))
    mismatch_errors: list[dict[str, str]] = []
    if result["ok"] != expected_ok:
        mismatch_errors.append(error("expected_ok_mismatch", "actual ok does not match expected_ok", expected_path, "expected_ok"))
    if not expected_ok and actual_codes != expected_codes:
        mismatch_errors.append(error("expected_error_code_mismatch", f"actual={actual_codes} expected={expected_codes}", expected_path, "expected_error_codes"))
    if expected.get("schema_version") and result.get("schema_version") != expected.get("schema_version"):
        mismatch_errors.append(error("expected_schema_version_mismatch", "schema_version does not match expected_result", expected_path, "schema_version"))
    return {**result, "sample": rel(sample_dir), "expected_ok": expected_ok, "expected_error_codes": expected_codes, "actual_error_codes": actual_codes, "expectation_ok": not mismatch_errors, "expectation_errors": mismatch_errors}


def iter_sample_dirs(root: Path, contract: str | None = None) -> list[Path]:
    dirs: list[Path] = []
    if contract and contract != "all":
        parents = [root / contract]
    else:
        parents = [p for p in root.iterdir() if p.is_dir()] if root.exists() else []
    for parent in sorted(parents):
        if not parent.exists():
            continue
        dirs.extend(sorted([p for p in parent.iterdir() if p.is_dir() and (p / "expected_result.json").exists()]))
    return dirs


def run_golden(root: Path, contract: str | None = None) -> dict[str, Any]:
    sample_dirs = iter_sample_dirs(root, contract)
    results = [validate_golden_sample(path) for path in sample_dirs]
    ok = all(item.get("expectation_ok") and item.get("ok") == item.get("expected_ok") for item in results)
    return {"ok": ok, "contract": contract or "all", "status": "passed" if ok else "failed", "errors": [err for item in results for err in item.get("expectation_errors", [])], "warnings": [], "checked_files": [item.get("sample", "") for item in results], "schema_version": SCHEMA_VERSION, "sample_count": len(results), "results": results}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase M modular contracts and golden samples.")
    parser.add_argument("--contract", default="all", help="Contract name or all")
    parser.add_argument("--artifact-path", help="Artifact/sample directory containing manifest.json")
    parser.add_argument("--golden-root", default=str(DEFAULT_GOLDEN_ROOT), help="Golden sample root")
    parser.add_argument("--run-golden", action="store_true", help="Validate golden samples and expected_result.json")
    parser.add_argument("--list-contracts", action="store_true", help="List supported contracts")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()

    if args.list_contracts:
        result: dict[str, Any] = {"ok": True, "contracts": sorted(SPECS)}
    elif args.run_golden:
        result = run_golden(Path(args.golden_root), args.contract)
    else:
        if not args.artifact_path:
            result = {"ok": False, "contract": args.contract, "status": "artifact_path_required", "errors": [error("artifact_path_required", "--artifact-path is required unless --run-golden is used", ROOT)], "warnings": [], "checked_files": [], "schema_version": SCHEMA_VERSION}
        elif args.contract == "all":
            result = {"ok": False, "contract": "all", "status": "contract_required", "errors": [error("contract_required", "single artifact validation requires --contract", Path(args.artifact_path))], "warnings": [], "checked_files": [], "schema_version": SCHEMA_VERSION}
        else:
            result = validate_contract(args.contract, Path(args.artifact_path))

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result.get('ok')}")
        print(f"status={result.get('status')}")
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
