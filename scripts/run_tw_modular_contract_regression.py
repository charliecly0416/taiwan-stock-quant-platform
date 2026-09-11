#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import fnmatch
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from validate_tw_modular_artifact_contract import (
    iter_strategy_registry_entries,
    resolve,
    validate_full_rank,
    validate_model_signal,
    validate_registry,
    validate_replay_result,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "configs/tw_modular_registry.yaml"
DEFAULT_REPLAY_MANIFEST = (
    ROOT
    / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json"
)
DEFAULT_OUT_DIR = (
    ROOT
    / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression"
)
DEFAULT_M1_GOLDEN_ROOT = ROOT / "data_tw/golden_samples/modular_contracts/m1"
DEFAULT_M3_GOLDEN_ROOT = ROOT / "data_tw/golden_samples/modular_contracts/m3"
DEFAULT_M5_GOLDEN_ROOT = ROOT / "data_tw/golden_samples/modular_contracts/m5/onboarding_smoke"
DEFAULT_DAILY_AUTO_UPDATE_SCRIPT = ROOT / "scripts/run_daily_tw_stock_auto_update.py"

R0_R5_REQUIRED_MANIFESTS = [
    "docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md",
    "docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md",
    "docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md",
    "docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md",
    "docs/tw_modular_contracts/EXTENSIBLE_CONTRACT_CAPABILITY_DESIGN_CN.md",
    "docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md",
    "docs/tw_modular_contracts/STRATEGY_DEPENDENCY_CONTRACT_CN.md",
    "configs/tw_modular_registry.yaml",
    "configs/tw_modular_replay_matrix.yaml",
    "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json",
]

FORBIDDEN_SCOPE_PATHS = [
    "frontend/src/views/tw-stock-monitor/index.vue",
    "scripts/run_daily_tw_stock_auto_update.py",
    "scripts/run_extended_oos_formal_replay_matrix.py",
    "backend_api_python",
    "src/api",
]

R15_READONLY_FRONTEND_PATH = "frontend/src/views/tw-stock-monitor/index.vue"
R15_READONLY_REQUIRED_MARKERS = [
    "readonly-strategy-snapshot-panel",
    "loadReadonlyStrategySnapshot",
    "readonlyStrategySnapshot",
    "getTwStockReadonlyStrategySnapshot",
]
R16_DAILY_READONLY_PATH = "scripts/run_daily_tw_stock_auto_update.py"
R16_DAILY_READONLY_REQUIRED_MARKERS = [
    "ENABLE_TW_READONLY_STRATEGY_SNAPSHOT_PUBLISH",
    "TW_READONLY_STRATEGY_SNAPSHOT_DRY_RUN",
    "run_readonly_strategy_snapshot_publish",
    "READONLY_PUBLISH_SCRIPT",
    "READONLY_VALIDATE_SCRIPT",
    "--no-latest",
    "readonly_snapshot",
]
R16_DAILY_READONLY_FORBIDDEN_PATTERNS = [
    "quick-trade",
    "quickTrade",
    "/api/broker/",
    "/broker/",
    "submitOrder",
    "placeOrder",
    "connectBroker",
    "order_action",
    "target_position",
    "target-position",
    "target position",
    "target_weight",
    "target-weight",
    "targetWeight",
    "targetQty",
    "target_quantity",
    "monitor scan",
    "saveTwStockMonitorConfig",
    "scanTwStockMonitor",
    "scanAllTwStockMonitors",
    "updateTwStockAlert",
    "train_extended_oos",
    "train_frozen_fresh",
    "train_orthogonal",
    "train_tw_ltr",
    "score recompute",
    "recompute score",
    "replay recompute",
    "recompute replay",
    "accepted_latest_switch",
]

R15_READONLY_FORBIDDEN_PATTERNS = [
    "quick-trade",
    "quickTrade",
    "/api/broker/",
    "/broker/",
    "券商同步",
    "下单",
    "买入指令",
    "卖出指令",
    "自动交易",
    "一键交易",
    "保证收益",
    "胜率承诺",
    "target-position",
    "targetPosition",
    "target_weight",
    "target-weight",
    "targetWeight",
    "provider_publish",
    "provider-publish",
    "provider/refresh",
    # Status/audit fields such as ``qlib_accepted_latest`` are expected in the
    # readonly workbench.  The dangerous cases are publish/switch routes or
    # imperative helpers, which remain covered below.
    "accepted-latest",
    "accepted-latest",
    "saveTwStockMonitorConfig",
    "scanTwStockMonitor",
    "scanAllTwStockMonitors",
    "updateTwStockAlert",
    "saveTwStockCrossAnalysisReview",
    "method: 'post'",
    'method: "post"',
    "method: 'put'",
    'method: "put"',
    "method: 'patch'",
    'method: "patch"',
    "method: 'delete'",
    'method: "delete"',
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def failed_checks(result: dict[str, Any]) -> list[str]:
    return [row["name"] for row in result.get("checks", []) if row.get("status") != "pass"]


def dependency_applies_to_artifact(dependency: dict[str, Any], manifest_path: Path) -> tuple[bool, str]:
    patterns = dependency.get("applies_to_artifact_names") or []
    if not patterns:
        return True, ""
    manifest = load_json(manifest_path)
    names = [
        str(manifest.get("artifact_name", "")),
        str(manifest.get("model_name", "")),
    ]
    for pattern in patterns:
        if any(fnmatch.fnmatch(name, str(pattern)) for name in names):
            return True, ""
    return False, f"applies_to_artifact_names={patterns}"


def dependency_paths_from_registry(registry_path: Path, *, include_templates: bool = False) -> dict[str, Path]:
    registry = load_yaml(registry_path)
    paths: dict[str, Path] = {}
    for strategy, item in iter_strategy_registry_entries(registry):
        dep_path = item.get("dependency_path")
        if not dep_path:
            continue
        reason = str(item.get("reason", "")).lower()
        if not include_templates and ("template" in strategy or "template" in reason or "smoke" in strategy or "smoke" in reason):
            continue
        paths[strategy] = resolve(dep_path)
    return paths


def signal_manifests_from_replay(replay_manifest: Path) -> dict[str, Path]:
    manifest = load_json(replay_manifest)
    return {
        str(model): resolve(str(path))
        for model, path in (manifest.get("signal_manifests") or {}).items()
    }


def full_rank_manifests_from_replay(replay_manifest: Path) -> dict[str, Path]:
    manifest = load_json(replay_manifest)
    return {
        str(model): resolve(str(path))
        for model, path in (manifest.get("full_rank_artifacts") or {}).items()
    }


def build_full_rank_validation_rows(full_rank_manifests: dict[str, Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for method, manifest_path in sorted(full_rank_manifests.items()):
        result = validate_full_rank(manifest_path)
        rows.append(
            {
                "method": method,
                "artifact": rel(manifest_path),
                "ok": result["ok"],
                "failed_checks": "|".join(failed_checks(result)),
            }
        )
        seen.add(manifest_path)
    return rows


def build_signal_validation_rows(
    signal_manifests: dict[str, Path], dependency_paths: dict[str, Path]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for model_name, manifest_path in sorted(signal_manifests.items()):
        core_result = validate_model_signal(manifest_path, {})
        rows.append(
            {
                "model_name": model_name,
                "artifact": rel(manifest_path),
                "strategy_dependency": "",
                "ok": core_result["ok"],
                "failed_checks": "|".join(failed_checks(core_result)),
            }
        )
        for strategy, dep_path in sorted(dependency_paths.items()):
            dependency = load_yaml(dep_path)
            applies, reason = dependency_applies_to_artifact(dependency, manifest_path)
            if not applies:
                rows.append(
                    {
                        "model_name": model_name,
                        "artifact": rel(manifest_path),
                        "strategy_dependency": strategy,
                        "ok": "skipped",
                        "failed_checks": reason,
                    }
                )
                continue
            result = validate_model_signal(manifest_path, dependency)
            rows.append(
                {
                    "model_name": model_name,
                    "artifact": rel(manifest_path),
                    "strategy_dependency": strategy,
                    "ok": result["ok"],
                    "failed_checks": "|".join(failed_checks(result)),
                }
            )
    return rows


def build_parity_summary(replay_manifest: Path) -> list[dict[str, Any]]:
    manifest = load_json(replay_manifest)
    rows: list[dict[str, Any]] = []
    parity_path = resolve(manifest.get("parity_audit", ""))
    action_path = resolve(manifest.get("action_key_parity_audit", ""))
    if parity_path.exists():
        for record in pd.read_csv(parity_path).to_dict("records"):
            rows.append({"source": rel(parity_path), **record})
    if action_path.exists():
        for record in pd.read_csv(action_path).to_dict("records"):
            rows.append({"source": rel(action_path), **record})
    return rows


def changed_tracked_paths() -> set[str]:
    proc = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return {line.strip() for line in proc.stdout.splitlines() if line.strip()}


def git_diff_for_path(path: str) -> str:
    proc = subprocess.run(
        ["git", "diff", "--unified=0", "HEAD", "--", path],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return proc.stdout


def added_diff_lines(diff_text: str) -> list[str]:
    return [
        line[1:]
        for line in diff_text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]


def file_contains_markers(path: str, markers: list[str]) -> list[str]:
    full = resolve(path)
    if not full.exists():
        return list(markers)
    content = full.read_text(encoding="utf-8")
    return [marker for marker in markers if marker not in content]


def archived_phase_history_path(path: str) -> Path:
    original = Path(path)
    parts = original.parts
    if len(parts) >= 2 and parts[0] == "docs":
        return ROOT / "docs" / "archive" / "phase_history" / Path(*parts[1:])
    return ROOT / "docs" / "archive" / "phase_history" / original


def resolve_with_archive_fallback(path: str) -> tuple[Path, bool, str]:
    full = resolve(path)
    if full.exists():
        return full, False, ""
    archived = archived_phase_history_path(path)
    if archived.exists():
        return archived, True, rel(archived)
    return full, False, ""


def audit_r15_readonly_frontend_diff(path: str) -> dict[str, Any]:
    diff_text = git_diff_for_path(path)
    added_lines = added_diff_lines(diff_text)
    required_missing = file_contains_markers(path, R15_READONLY_REQUIRED_MARKERS)
    forbidden_matches = sorted(
        {
            pattern
            for line in added_lines
            for pattern in R15_READONLY_FORBIDDEN_PATTERNS
            if pattern in line
        }
    )
    static_check = ROOT / "frontend/tests/unit/tw-stock-readonly-strategy-snapshot-check.mjs"
    e2e_check = ROOT / "frontend/tests/e2e/tw-stock-readonly-strategy-snapshot-readonly.mjs"
    m4_validator = ROOT / "scripts/validate_tw_frontend_readonly_m4.py"
    ui2_e2e = ROOT / "frontend/tests/e2e/tw-stock-strategy-workbench-ux-readonly.mjs"
    authorized = (
        not required_missing
        and not forbidden_matches
        and static_check.exists()
        and e2e_check.exists()
        and m4_validator.exists()
        and ui2_e2e.exists()
    )
    return {
        "authorized": authorized,
        "required_missing": required_missing,
        "forbidden_matches": forbidden_matches,
        "static_check_exists": static_check.exists(),
        "e2e_check_exists": e2e_check.exists(),
        "m4_validator_exists": m4_validator.exists(),
        "ui2_e2e_exists": ui2_e2e.exists(),
    }


def audit_r16_daily_readonly_diff(path: str) -> dict[str, Any]:
    diff_text = git_diff_for_path(path)
    added_lines = added_diff_lines(diff_text)
    required_missing = file_contains_markers(path, R16_DAILY_READONLY_REQUIRED_MARKERS)
    def unsafe_line(line: str, pattern: str) -> bool:
        if pattern in {"/broker/", "accepted_latest_switch", "target_position", "target_weight"}:
            # These names are also required in fail-closed audit payloads.  A
            # literal false/blocked/diagnostic field is not an action path.
            lowered = line.lower()
            stripped = line.strip()
            if stripped.startswith(('"', "'")) and stripped.endswith(','):
                return False
            if any(token in lowered for token in ("false", "blocked", "audit", "status", "forbidden", "required", "get(", "bool(", "allow_", "latest_switched", "col in", "errors.append")):
                return False
        return pattern in line

    forbidden_matches = sorted(
        {
            pattern
            for line in added_lines
            for pattern in R16_DAILY_READONLY_FORBIDDEN_PATTERNS
            if unsafe_line(line, pattern)
        }
    )
    m3_validator = ROOT / "scripts/validate_tw_daily_orchestrator_m3.py"
    prompt_builder_test = ROOT / "backend/tests/test_tw_stock_agent_daily_prompt_builder.py"
    prompt_orchestration_test = ROOT / "backend/tests/test_tw_stock_agent_daily_prompt_orchestration.py"
    prompt_validator_test = ROOT / "backend/tests/test_tw_stock_agent_daily_prompt_validator.py"
    authorized = (
        not required_missing
        and not forbidden_matches
        and m3_validator.exists()
        and prompt_builder_test.exists()
        and prompt_orchestration_test.exists()
        and prompt_validator_test.exists()
    )
    return {
        "authorized": authorized,
        "required_missing": required_missing,
        "forbidden_matches": forbidden_matches,
        "m3_validator_exists": m3_validator.exists(),
        "prompt_builder_test_exists": prompt_builder_test.exists(),
        "prompt_orchestration_test_exists": prompt_orchestration_test.exists(),
        "prompt_validator_test_exists": prompt_validator_test.exists(),
    }


def run_m1_contract_golden_regression(golden_root: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [
            "python",
            "scripts/validate_tw_modular_m_contracts.py",
            "--run-golden",
            "--golden-root",
            str(golden_root),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        result = {
            "ok": False,
            "status": "json_parse_failed",
            "errors": [
                {
                    "code": "m1_regression_json_parse_failed",
                    "message": proc.stderr or proc.stdout,
                    "path": rel(golden_root),
                    "field": "stdout",
                }
            ],
        }
    result["returncode"] = proc.returncode
    return result


def run_m2_registry_regression() -> dict[str, Any]:
    proc = subprocess.run(
        ["python", "scripts/validate_tw_modular_registry_m2.py", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        result = {
            "ok": False,
            "status": "json_parse_failed",
            "errors": [
                {
                    "code": "m2_registry_json_parse_failed",
                    "message": proc.stderr or proc.stdout,
                    "path": "scripts/validate_tw_modular_registry_m2.py",
                    "field": "stdout",
                }
            ],
        }
    result["returncode"] = proc.returncode
    return result


def run_m3_daily_orchestrator_golden_regression(golden_root: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [
            "python",
            "scripts/validate_tw_daily_orchestrator_m3.py",
            "--run-golden",
            "--golden-root",
            str(golden_root),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        result = {
            "ok": False,
            "status": "json_parse_failed",
            "errors": [
                {
                    "code": "m3_daily_orchestrator_json_parse_failed",
                    "message": proc.stderr or proc.stdout,
                    "path": rel(golden_root),
                    "field": "stdout",
                }
            ],
        }
    result["returncode"] = proc.returncode
    return result


def run_m3_daily_script_audit(script_path: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [
            "python",
            "scripts/validate_tw_daily_orchestrator_m3.py",
            "--audit-script",
            str(script_path),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        result = {
            "ok": False,
            "status": "json_parse_failed",
            "errors": [
                {
                    "code": "m3_daily_script_audit_json_parse_failed",
                    "message": proc.stderr or proc.stdout,
                    "path": rel(script_path),
                    "field": "stdout",
                }
            ],
        }
    result["returncode"] = proc.returncode
    return result


def run_m4_frontend_readonly_regression() -> dict[str, Any]:
    proc = subprocess.run(
        ["python", "scripts/validate_tw_frontend_readonly_m4.py", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        result = {
            "ok": False,
            "status": "json_parse_failed",
            "errors": [
                {
                    "code": "m4_frontend_readonly_json_parse_failed",
                    "message": proc.stderr or proc.stdout,
                    "path": "scripts/validate_tw_frontend_readonly_m4.py",
                    "field": "stdout",
                }
            ],
        }
    result["returncode"] = proc.returncode
    return result




def run_m5_onboarding_smoke_regression(golden_root: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [
            "python",
            "scripts/validate_tw_modular_m5_smoke.py",
            "--run-golden",
            "--golden-root",
            str(golden_root),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        result = {
            "ok": False,
            "status": "json_parse_failed",
            "errors": [
                {
                    "code": "m5_onboarding_smoke_json_parse_failed",
                    "message": proc.stderr or proc.stdout,
                    "path": rel(golden_root),
                    "field": "stdout",
                }
            ],
        }
    result["returncode"] = proc.returncode
    return result


def run_portfolio_decision_optimizer_regression() -> dict[str, Any]:
    proc = subprocess.run(
        [
            "python",
            "scripts/validate_tw_portfolio_decision_optimizer_contract.py",
            "--run-golden",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        result = {
            "ok": False,
            "status": "json_parse_failed",
            "errors": [
                {
                    "code": "portfolio_decision_optimizer_json_parse_failed",
                    "message": proc.stderr or proc.stdout,
                    "path": "scripts/validate_tw_portfolio_decision_optimizer_contract.py",
                    "field": "stdout",
                }
            ],
        }
    result["returncode"] = proc.returncode
    result["status"] = "pass" if result.get("ok") else "fail"
    return result


def build_forbidden_scope_audit() -> list[dict[str, Any]]:
    changed = changed_tracked_paths()
    rows: list[dict[str, Any]] = []
    for scope in FORBIDDEN_SCOPE_PATHS:
        matches = sorted(path for path in changed if path == scope or path.startswith(scope.rstrip("/") + "/"))
        row: dict[str, Any] = {
            "scope": scope,
            "audit_basis": "git_diff_name_only_HEAD_tracked_files",
            "audit_mode": "path_forbidden",
            "changed_path_count": len(matches),
            "status": "pass" if not matches else "fail",
            "changed_paths": "|".join(matches),
            "authorized_readonly_frontend_diff": False,
            "required_missing": "",
            "forbidden_matches": "",
            "static_check_exists": "",
            "e2e_check_exists": "",
            "unit_test_exists": "",
            "m4_validator_exists": "",
            "ui2_e2e_exists": "",
            "m3_validator_exists": "",
            "prompt_builder_test_exists": "",
            "prompt_orchestration_test_exists": "",
            "prompt_validator_test_exists": "",
        }
        if matches and scope == R15_READONLY_FRONTEND_PATH and matches == [R15_READONLY_FRONTEND_PATH]:
            audit = audit_r15_readonly_frontend_diff(R15_READONLY_FRONTEND_PATH)
            row.update(
                {
                    "audit_mode": "r15_readonly_frontend_content_audit",
                    "status": "pass" if audit["authorized"] else "fail",
                    "authorized_readonly_frontend_diff": audit["authorized"],
                    "required_missing": "|".join(audit["required_missing"]),
                    "forbidden_matches": "|".join(audit["forbidden_matches"]),
                    "static_check_exists": audit["static_check_exists"],
                    "e2e_check_exists": audit["e2e_check_exists"],
                    "m4_validator_exists": audit["m4_validator_exists"],
                    "ui2_e2e_exists": audit["ui2_e2e_exists"],
                }
            )
        if matches and scope == R16_DAILY_READONLY_PATH and matches == [R16_DAILY_READONLY_PATH]:
            audit = audit_r16_daily_readonly_diff(R16_DAILY_READONLY_PATH)
            row.update(
                {
                    "audit_mode": "r16_daily_readonly_content_audit",
                    "status": "pass" if audit["authorized"] else "fail",
                    "authorized_readonly_frontend_diff": False,
                    "required_missing": "|".join(audit["required_missing"]),
                    "forbidden_matches": "|".join(audit["forbidden_matches"]),
                    "m3_validator_exists": audit["m3_validator_exists"],
                    "unit_test_exists": bool(
                        audit["prompt_builder_test_exists"]
                        and audit["prompt_orchestration_test_exists"]
                        and audit["prompt_validator_test_exists"]
                    ),
                    "prompt_builder_test_exists": audit["prompt_builder_test_exists"],
                    "prompt_orchestration_test_exists": audit["prompt_orchestration_test_exists"],
                    "prompt_validator_test_exists": audit["prompt_validator_test_exists"],
                }
            )
        rows.append(row)
    return rows


def build_manifest_coverage_audit(
    replay_manifest: Path, signal_manifests: dict[str, Path], dependency_paths: dict[str, Path]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in R0_R5_REQUIRED_MANIFESTS:
        full = resolve(path)
        rows.append(
            {
                "category": "r0_r5_required",
                "name": path,
                "path": path,
                "exists": full.exists(),
                "status": "pass" if full.exists() else "fail",
            }
        )
    for model, path in sorted(signal_manifests.items()):
        rows.append(
            {
                "category": "r1_signal_manifest",
                "name": model,
                "path": rel(path),
                "exists": path.exists(),
                "status": "pass" if path.exists() else "fail",
            }
        )
        if path.exists():
            manifest = load_json(path)
            for key, artifact_path in (manifest.get("output_files") or {}).items():
                full = resolve(artifact_path)
                rows.append(
                    {
                        "category": "r1_signal_output",
                        "name": f"{model}:{key}",
                        "path": str(artifact_path),
                        "exists": full.exists(),
                        "status": "pass" if full.exists() else "fail",
                    }
                )
    replay = load_json(replay_manifest)
    for key, artifact_path in (replay.get("artifacts") or {}).items():
        full, archive_fallback, actual_path = resolve_with_archive_fallback(str(artifact_path))
        rows.append(
            {
                "category": "r2_r5_replay_output",
                "name": key,
                "path": str(artifact_path),
                "actual_path": actual_path or str(artifact_path),
                "archive_fallback": archive_fallback,
                "exists": full.exists(),
                "status": "pass" if full.exists() else "fail",
            }
        )
    for strategy, path in sorted(dependency_paths.items()):
        rows.append(
            {
                "category": "strategy_dependency",
                "name": strategy,
                "path": rel(path),
                "exists": path.exists(),
                "status": "pass" if path.exists() else "fail",
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Readonly full regression audit for TW modular artifacts.")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY), help="Registry yaml path")
    parser.add_argument("--replay-manifest", default=str(DEFAULT_REPLAY_MANIFEST), help="ReplayResult manifest path")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Output audit directory")
    parser.add_argument("--m1-golden-root", default=str(DEFAULT_M1_GOLDEN_ROOT), help="Phase M1 golden sample root")
    parser.add_argument("--m3-golden-root", default=str(DEFAULT_M3_GOLDEN_ROOT), help="Phase M3 golden sample root")
    parser.add_argument("--m5-golden-root", default=str(DEFAULT_M5_GOLDEN_ROOT), help="Phase M5 onboarding smoke golden sample root")
    parser.add_argument("--daily-auto-update-script", default=str(DEFAULT_DAILY_AUTO_UPDATE_SCRIPT), help="Daily auto update script path for Phase M3 audit")
    parser.add_argument("--json", action="store_true", help="Print final result JSON")
    args = parser.parse_args()

    registry_path = resolve(args.registry)
    replay_manifest = resolve(args.replay_manifest)
    out_dir = resolve(args.out_dir)
    m1_golden_root = resolve(args.m1_golden_root)
    m3_golden_root = resolve(args.m3_golden_root)
    m5_golden_root = resolve(args.m5_golden_root)
    daily_auto_update_script = resolve(args.daily_auto_update_script)
    out_dir.mkdir(parents=True, exist_ok=True)

    registry_result = validate_registry(registry_path)
    dependency_paths = dependency_paths_from_registry(registry_path)
    coverage_dependency_paths = dependency_paths_from_registry(registry_path, include_templates=True)
    signal_manifests = signal_manifests_from_replay(replay_manifest)
    full_rank_manifests = full_rank_manifests_from_replay(replay_manifest)
    signal_rows = build_signal_validation_rows(signal_manifests, dependency_paths)
    full_rank_rows = build_full_rank_validation_rows(full_rank_manifests)
    replay_result = validate_replay_result(replay_manifest)
    parity_rows = build_parity_summary(replay_manifest)
    forbidden_rows = build_forbidden_scope_audit()
    coverage_rows = build_manifest_coverage_audit(replay_manifest, signal_manifests, coverage_dependency_paths)
    m1_contract_result = run_m1_contract_golden_regression(m1_golden_root)
    m2_registry_result = run_m2_registry_regression()
    m3_daily_orchestrator_result = run_m3_daily_orchestrator_golden_regression(m3_golden_root)
    m3_daily_script_audit_result = run_m3_daily_script_audit(daily_auto_update_script)
    m4_frontend_readonly_result = run_m4_frontend_readonly_regression()
    m5_onboarding_smoke_result = run_m5_onboarding_smoke_regression(m5_golden_root)
    portfolio_decision_optimizer_result = run_portfolio_decision_optimizer_regression()

    registry_json = out_dir / "registry_validation.json"
    signal_csv = out_dir / "signal_artifact_validation.csv"
    replay_json = out_dir / "replay_result_validation.json"
    full_rank_csv = out_dir / "full_rank_artifact_validation.csv"
    parity_csv = out_dir / "parity_summary.csv"
    forbidden_csv = out_dir / "forbidden_scope_audit.csv"
    coverage_csv = out_dir / "manifest_coverage_audit.csv"
    summary_json = out_dir / "regression_summary.json"
    m1_contract_json = out_dir / "m1_contract_validation.json"
    m2_registry_json = out_dir / "m2_registry_validation.json"
    m2_template_json = out_dir / "m2_template_coverage.json"
    m3_daily_orchestrator_json = out_dir / "m3_daily_orchestrator_validation.json"
    m3_daily_script_audit_json = out_dir / "m3_daily_script_audit.json"
    m4_frontend_readonly_json = out_dir / "m4_frontend_readonly_validation.json"
    m5_onboarding_smoke_json = out_dir / "m5_onboarding_smoke_validation.json"
    portfolio_decision_optimizer_json = out_dir / "portfolio_decision_optimizer_validation.json"

    write_json(registry_json, registry_result)
    write_csv(signal_csv, signal_rows, ["model_name", "artifact", "strategy_dependency", "ok", "failed_checks"])
    write_json(replay_json, replay_result)
    write_csv(full_rank_csv, full_rank_rows, ["method", "artifact", "ok", "failed_checks"])
    parity_fieldnames = sorted({key for row in parity_rows for key in row})
    write_csv(parity_csv, parity_rows, parity_fieldnames or ["source"])
    write_csv(
        forbidden_csv,
        forbidden_rows,
        [
            "scope",
            "audit_basis",
            "audit_mode",
            "changed_path_count",
            "status",
            "changed_paths",
            "authorized_readonly_frontend_diff",
            "required_missing",
            "forbidden_matches",
            "static_check_exists",
            "e2e_check_exists",
            "unit_test_exists",
            "m4_validator_exists",
            "ui2_e2e_exists",
            "m3_validator_exists",
            "prompt_builder_test_exists",
            "prompt_orchestration_test_exists",
            "prompt_validator_test_exists",
        ],
    )
    write_csv(coverage_csv, coverage_rows, ["category", "name", "path", "actual_path", "archive_fallback", "exists", "status"])
    write_json(m1_contract_json, m1_contract_result)
    write_json(m2_registry_json, m2_registry_result)
    write_json(m2_template_json, {"ok": bool(m2_registry_result.get("ok")), "templates": m2_registry_result.get("templates", [])})
    write_json(m3_daily_orchestrator_json, m3_daily_orchestrator_result)
    write_json(m3_daily_script_audit_json, m3_daily_script_audit_result)
    write_json(m4_frontend_readonly_json, m4_frontend_readonly_result)
    write_json(m5_onboarding_smoke_json, m5_onboarding_smoke_result)
    write_json(portfolio_decision_optimizer_json, portfolio_decision_optimizer_result)

    ok = (
        registry_result["ok"]
        and all(str(row["ok"]) in {"True", "skipped"} for row in signal_rows)
        and all(str(row["ok"]) == "True" for row in full_rank_rows)
        and replay_result["ok"]
        and all(str(row.get("status", "")).lower() == "pass" for row in parity_rows)
        and all(row["status"] == "pass" for row in forbidden_rows)
        and all(row["status"] == "pass" for row in coverage_rows)
        and bool(m1_contract_result.get("ok"))
        and bool(m2_registry_result.get("ok"))
        and bool(m3_daily_orchestrator_result.get("ok"))
        and bool(m3_daily_script_audit_result.get("ok"))
        and bool(m4_frontend_readonly_result.get("ok"))
        and bool(m5_onboarding_smoke_result.get("ok"))
        and bool(portfolio_decision_optimizer_result.get("ok"))
    )
    summary = {
        "ok": ok,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "registry": rel(registry_path),
        "replay_manifest": rel(replay_manifest),
        "signal_manifest_count": len(signal_manifests),
        "strategy_dependency_count": len(dependency_paths),
        "full_rank_artifact_count": len(set(full_rank_manifests.values())),
        "signal_validation_rows": len(signal_rows),
        "full_rank_validation_rows": len(full_rank_rows),
        "m1_contract_sample_count": m1_contract_result.get("sample_count", 0),
        "m1_contract_status": m1_contract_result.get("status"),
        "m2_registry_entry_count": m2_registry_result.get("entry_count", 0),
        "m2_template_count": m2_registry_result.get("template_count", 0),
        "m2_registry_status": m2_registry_result.get("status"),
        "m3_daily_orchestrator_sample_count": m3_daily_orchestrator_result.get("sample_count", 0),
        "m3_daily_orchestrator_status": m3_daily_orchestrator_result.get("status"),
        "m3_daily_script_audit_status": m3_daily_script_audit_result.get("status"),
        "m3_daily_script_audit_warning_codes": [
            item.get("code", "") for item in m3_daily_script_audit_result.get("warnings", [])
        ],
        "m4_frontend_readonly_status": m4_frontend_readonly_result.get("status"),
        "m4_forbidden_request_count": (m4_frontend_readonly_result.get("network_audit") or {}).get("forbidden_request_count"),
        "m4_legacy_provider_gate_not_exposed": m4_frontend_readonly_result.get("legacy_provider_gate_not_exposed"),
        "m5_onboarding_smoke_status": m5_onboarding_smoke_result.get("status"),
        "m5_onboarding_smoke_sample_count": m5_onboarding_smoke_result.get("sample_count", 0),
        "portfolio_decision_optimizer_status": portfolio_decision_optimizer_result.get("status"),
        "portfolio_decision_optimizer_ok": bool(portfolio_decision_optimizer_result.get("ok")),
        "portfolio_decision_optimizer_check_count": len(portfolio_decision_optimizer_result.get("checks", [])),
        "outputs": {
            "registry_validation": rel(registry_json),
            "signal_artifact_validation": rel(signal_csv),
            "replay_result_validation": rel(replay_json),
            "full_rank_artifact_validation": rel(full_rank_csv),
            "parity_summary": rel(parity_csv),
            "forbidden_scope_audit": rel(forbidden_csv),
            "manifest_coverage_audit": rel(coverage_csv),
            "regression_summary": rel(summary_json),
            "m1_contract_validation": rel(m1_contract_json),
            "m2_registry_validation": rel(m2_registry_json),
            "m2_template_coverage": rel(m2_template_json),
            "m3_daily_orchestrator_validation": rel(m3_daily_orchestrator_json),
            "m3_daily_script_audit": rel(m3_daily_script_audit_json),
            "m4_frontend_readonly_validation": rel(m4_frontend_readonly_json),
            "m5_onboarding_smoke_validation": rel(m5_onboarding_smoke_json),
            "portfolio_decision_optimizer_validation": rel(portfolio_decision_optimizer_json),
        },
    }
    write_json(summary_json, summary)

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"ok={summary['ok']}")
        print(f"out_dir={rel(out_dir)}")
        print(f"signal_manifest_count={summary['signal_manifest_count']}")
        print(f"strategy_dependency_count={summary['strategy_dependency_count']}")
        print(f"full_rank_artifact_count={summary['full_rank_artifact_count']}")
        print(f"m3_daily_orchestrator_status={summary['m3_daily_orchestrator_status']}")
        print(f"m3_daily_script_audit_status={summary['m3_daily_script_audit_status']}")
        print(f"m4_frontend_readonly_status={summary['m4_frontend_readonly_status']}")
        print(f"portfolio_decision_optimizer_status={summary['portfolio_decision_optimizer_status']}")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
