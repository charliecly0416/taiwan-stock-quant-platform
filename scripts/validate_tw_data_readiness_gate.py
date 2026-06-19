#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_GATE_STATUSES = {
    "all_required_ready",
    "partial_data_pending",
    "no_new_data",
    "provider_failed",
    "validator_failed",
    "deadline_missed_keep_previous_latest",
}
MODEL_IDS = {
    "e4_frozen_qlib_2023_2025_ltr",
    "fresh_qlib_2025_ltr",
    "fresh_qlib_adaptive",
    "frozen_qlib_2018_2022",
    "frozen_qlib_2025_ltr",
}
STRATEGY_IDS = {
    "original",
    "top50_exit_all",
    "top50_exit_one_worst_sell",
    "one_sell_one_buy_correct",
    "one_sell_one_buy_buggy_e8r",
    "sector_extension_analysis_smoke",
    "dummy_new_strategy_dependency_smoke",
}
FORBIDDEN_ACTION_KEYS = [
    "provider_publish_triggered",
    "provider_refresh_official_path_triggered",
    "accepted_latest_switched",
    "qlib_accepted_latest_switched",
    "monitor_config_written",
    "monitor_scan_triggered",
    "alerts_written",
    "broker_connected",
    "quick_trade_triggered",
    "orders_created_or_sent",
    "agent_prompt_or_tool_modified",
]
SCENARIO_EXPECTATIONS = {
    "all_required_ready": {"ok": True, "gate_status": "all_required_ready", "error_codes": set()},
    "no_new_data": {"ok": True, "gate_status": "no_new_data", "error_codes": set()},
    "partial_data_pending": {"ok": True, "gate_status": "partial_data_pending", "error_codes": set()},
    "provider_failed": {"ok": True, "gate_status": "provider_failed", "error_codes": set()},
    "validator_failed_future_available_at": {"ok": True, "gate_status": "validator_failed", "error_codes": set()},
    "deadline_missed_keep_previous_latest": {"ok": True, "gate_status": "deadline_missed_keep_previous_latest", "error_codes": set()},
    "missing_orthogonal_required_source": {"ok": True, "gate_status": "validator_failed", "error_codes": set()},
    "missing_symbol_mapping": {"ok": True, "gate_status": "validator_failed", "error_codes": set()},
    "provider_publish_triggered": {"ok": False, "gate_status": "validator_failed", "error_codes": {"forbidden_action_triggered"}},
    "accepted_latest_switched": {"ok": False, "gate_status": "validator_failed", "error_codes": {"forbidden_action_triggered"}},
    "monitor_or_broker_action": {"ok": False, "gate_status": "validator_failed", "error_codes": {"forbidden_action_triggered"}},
}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def err(code: str, message: str, path: Path, field: str = "") -> dict[str, str]:
    return {"code": code, "message": message, "path": rel(path), "field": field}


def validate(staging_dir: Path) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    manifest_path = staging_dir / "data_readiness_manifest.json"
    matrix_path = staging_dir / "model_strategy_availability_matrix.json"
    if not manifest_path.exists():
        return {"ok": False, "status": "failed", "errors": [err("manifest_missing", "data_readiness_manifest.json missing", manifest_path)], "warnings": warnings}
    if not matrix_path.exists():
        return {"ok": False, "status": "failed", "errors": [err("matrix_missing", "model_strategy_availability_matrix.json missing", matrix_path)], "warnings": warnings}
    manifest = load_json(manifest_path)
    matrix = load_json(matrix_path)
    for field in ["run_id", "target_asof", "decision_for", "decision_cutoff", "gate_status", "previous_readonly_latest", "committed_readonly_latest", "sources", "forbidden_action_audit", "failure_reasons", "retryable_sources", "created_at"]:
        if field not in manifest:
            errors.append(err("manifest_field_missing", f"{field} is required", manifest_path, field))
    gate_status = str(manifest.get("gate_status", ""))
    if gate_status not in ALLOWED_GATE_STATUSES:
        errors.append(err("gate_status_invalid", "gate_status is not in allowed enum", manifest_path, "gate_status"))
    if gate_status != "all_required_ready" and manifest.get("committed_readonly_latest") != manifest.get("previous_readonly_latest"):
        errors.append(err("non_ready_updates_readonly_latest", "non-ready gate must preserve previous readonly latest", manifest_path, "committed_readonly_latest"))
    if gate_status != "all_required_ready" and manifest.get("updates_readonly_latest") is True:
        errors.append(err("non_ready_updates_readonly_latest", "non-ready gate must not update readonly latest", manifest_path, "updates_readonly_latest"))
    if manifest.get("staging_only") is not True:
        errors.append(err("not_staging_only", "data readiness gate must be staging-only", manifest_path, "staging_only"))
    actions = (manifest.get("forbidden_action_audit") or {}).get("actions") or {}
    for key in FORBIDDEN_ACTION_KEYS:
        if actions.get(key) is True:
            errors.append(err("forbidden_action_triggered", f"{key} must be false", manifest_path, f"forbidden_action_audit.actions.{key}"))
    source_ids = {str(source.get("source_id")) for source in manifest.get("sources") or []}
    if "orthogonal_o2_features" not in source_ids and gate_status != "validator_failed":
        errors.append(err("missing_orthogonal_required_source_not_blocked", "missing orthogonal required source must be validator_failed", manifest_path, "sources"))
    for field in ["models", "strategies", "default_model_id", "default_strategy_rule_id", "target_asof", "decision_for"]:
        if field not in matrix:
            errors.append(err("matrix_field_missing", f"{field} is required", matrix_path, field))
    model_ids = {str(model.get("model_id")) for model in matrix.get("models") or []}
    missing_models = sorted(MODEL_IDS - model_ids)
    if missing_models:
        errors.append(err("matrix_model_missing", f"missing models: {missing_models}", matrix_path, "models"))
    strategy_ids = {str(strategy.get("strategy_rule_id")) for strategy in matrix.get("strategies") or []}
    missing_strategies = sorted(STRATEGY_IDS - strategy_ids)
    if missing_strategies:
        errors.append(err("matrix_strategy_missing", f"missing strategies: {missing_strategies}", matrix_path, "strategies"))
    for strategy in matrix.get("strategies") or []:
        sid = strategy.get("strategy_rule_id")
        if sid in {"one_sell_one_buy_buggy_e8r"} and strategy.get("production_selectable") is True:
            errors.append(err("diagnostic_strategy_marked_production", "diagnostic strategy must not be production selectable", matrix_path, str(sid)))
        if sid in {"sector_extension_analysis_smoke", "dummy_new_strategy_dependency_smoke"} and strategy.get("production_selectable") is True:
            errors.append(err("smoke_strategy_marked_production", "smoke strategy must not be production selectable", matrix_path, str(sid)))
    ok = not errors
    return {"ok": ok, "status": "passed" if ok else "failed", "schema_version": "v1.data_readiness_gate_validator.v1", "gate_status": gate_status, "staging_dir": rel(staging_dir), "errors": errors, "warnings": warnings}


def run_json(cmd: list[str]) -> tuple[int, dict[str, Any]]:
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {"ok": False, "stdout": proc.stdout, "stderr": proc.stderr}
    return proc.returncode, payload


def run_golden() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory(prefix="phasev1_gate_golden_") as tmp:
        out_root = Path(tmp)
        for scenario, expected in SCENARIO_EXPECTATIONS.items():
            run_id = f"golden_{scenario}"
            pull_cmd = [
                sys.executable,
                "scripts/pull_tw_provider_staging_data.py",
                "--out-root",
                str(out_root),
                "--run-id",
                run_id,
                "--mode",
                "test_scenario",
                "--scenario",
                scenario,
                "--json",
            ]
            _, pull = run_json(pull_cmd)
            staging_dir = ROOT / str(pull.get("staging_dir", out_root / run_id))
            provider_rc, provider_validation = run_json([sys.executable, "scripts/validate_tw_provider_staging_data.py", "--staging-dir", str(staging_dir), "--json"])
            validation_file = staging_dir / "provider_validation_result.json"
            validation_file.write_text(json.dumps(provider_validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            run_json([sys.executable, "scripts/build_tw_data_readiness_gate.py", "--staging-dir", str(staging_dir), "--validation-result", str(validation_file), "--json"])
            result = validate(staging_dir)
            actual_codes = {e["code"] for e in result.get("errors", [])}
            passed = (
                bool(result.get("ok")) == bool(expected["ok"])
                and result.get("gate_status") == expected["gate_status"]
                and set(expected["error_codes"]).issubset(actual_codes)
            )
            if provider_rc != 0 and scenario not in {"partial_data_pending", "provider_failed", "validator_failed_future_available_at", "missing_orthogonal_required_source", "missing_symbol_mapping", "provider_publish_triggered", "accepted_latest_switched", "monitor_or_broker_action"}:
                passed = False
            row = {
                "scenario": scenario,
                "expected_ok": expected["ok"],
                "actual_ok": result.get("ok"),
                "expected_gate_status": expected["gate_status"],
                "actual_gate_status": result.get("gate_status"),
                "actual_error_codes": sorted(actual_codes),
                "status": "pass" if passed else "fail",
            }
            rows.append(row)
            if not passed:
                errors.append(err("golden_expectation_mismatch", f"golden scenario failed: {scenario}", staging_dir, scenario))
    return {"ok": bool(rows) and not errors, "status": "passed" if rows and not errors else "failed", "schema_version": "v1.data_readiness_gate_golden.v1", "sample_count": len(rows), "samples": rows, "errors": errors, "warnings": []}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase V1 DataReadinessGate artifacts.")
    parser.add_argument("--staging-dir", "--artifact-path", dest="staging_dir")
    parser.add_argument("--run-golden", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.run_golden:
        result = run_golden()
    else:
        if not args.staging_dir:
            raise SystemExit("--staging-dir is required unless --run-golden is used")
        staging_dir = Path(args.staging_dir)
        if not staging_dir.is_absolute():
            staging_dir = ROOT / staging_dir
        result = validate(staging_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else f"ok={result['ok']}\nstatus={result['status']}")
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
