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


def line_in_ranges(line: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= line <= end for start, end in ranges)


def pattern_lines(text: str, pattern: str) -> list[int]:
    return [idx for idx, line in enumerate(text.splitlines(), start=1) if pattern in line]


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
    refresh_lines = pattern_lines(text, "run_option_c_yahoo_scrapling_refresh.py")
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
        "provider_refresh_guarded": bool(refresh_lines) and all(line_in_ranges(line, ranges) for line in refresh_lines),
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
        "monitor_write_patterns_present": [],
    }
    for category, patterns in SCRIPT_FORBIDDEN_RUNTIME_PATTERNS.items():
        matched = [p for p in patterns if p in text]
        if category == "broker_order":
            findings["broker_order_patterns_present"] = matched
        if category == "monitor_write":
            findings["monitor_write_patterns_present"] = matched
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
