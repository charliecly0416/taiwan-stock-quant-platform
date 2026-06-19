#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "m1.0.0"
DEFAULT_REGISTRIES = [
    ROOT / "configs/tw_modular_registry.yaml",
    ROOT / "configs/data_source_registry.yaml",
    ROOT / "configs/feature_registry.yaml",
    ROOT / "configs/price_store_registry.yaml",
]
TEMPLATE_DIR = ROOT / "docs/tw_modular_contracts/templates"
REQUIRED_TEMPLATES = [
    "NEW_DATA_SOURCE_WORK_TEMPLATE_CN.md",
    "NEW_FEATURE_WORK_TEMPLATE_CN.md",
    "NEW_MODEL_WORK_TEMPLATE_CN.md",
    "NEW_STRATEGY_WORK_TEMPLATE_CN.md",
    "NEW_REPLAY_WINDOW_WORK_TEMPLATE_CN.md",
    "NEW_FRONTEND_READONLY_DISPLAY_WORK_TEMPLATE_CN.md",
    "NEW_AGENT_READONLY_CONTEXT_WORK_TEMPLATE_CN.md",
    "EXECUTION_REPORT_TEMPLATE_CN.md",
    "REVIEW_REPORT_TEMPLATE_CN.md",
]
REQUIRED_TEMPLATE_MARKERS = [
    "contract_doc",
    "schema_version",
    "input_artifacts",
    "output_artifacts",
    "validator_command",
    "golden_sample_path",
    "allowed_consumers",
    "forbidden_consumers",
    "readonly_boundary",
    "forbidden_actions_audit",
    "production_allowed: false",
]
AGENT_TEMPLATE_MARKERS = [
    "not_in_m0_m6_implementation_scope: true",
    "future_agent_phase_required: true",
    "no_order_action: true",
    "no_broker_or_order: true",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def err(code: str, message: str, path: Path, field: str = "") -> dict[str, str]:
    return {"code": code, "message": message, "path": rel(path), "field": field}


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def resolve(value: str) -> Path:
    p = Path(str(value))
    return p if p.is_absolute() else ROOT / p


def collect_entries(registry_path: Path, data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if registry_path.name == "tw_modular_registry.yaml":
        return (data.get("m2_registry") or {}).get("entries") or {}
    return data.get("entries") or {}


def validator_contracts(validator: Path) -> tuple[bool, set[str], str]:
    proc = subprocess.run(
        ["python", str(validator), "--list-contracts", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return False, set(), proc.stderr or proc.stdout
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return False, set(), str(exc)
    return bool(payload.get("ok")), set(map(str, payload.get("contracts", []))), ""


def run_entry_validator(validator: Path, contract: str, golden: Path) -> tuple[bool, str]:
    proc = subprocess.run(
        ["python", str(validator), "--contract", contract, "--artifact-path", str(golden), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return False, proc.stdout or proc.stderr
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return False, str(exc)
    return bool(payload.get("ok")), ""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_entry(name: str, entry: dict[str, Any], registry_path: Path, validator_cache: dict[str, tuple[bool, set[str], str]]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    required = [
        "artifact_type",
        "schema_version",
        "contract_doc",
        "validator",
        "golden_sample",
        "capabilities",
        "dependencies",
        "allowed_consumers",
        "forbidden_consumers",
        "production_allowed",
        "diagnostic_only",
        "owner_or_stage",
    ]
    for field in required:
        if field not in entry:
            errors.append(err("registry_required_field_missing", f"entry {name} missing {field}", registry_path, f"{name}.{field}"))
    if entry.get("schema_version") != SCHEMA_VERSION:
        errors.append(err("schema_version_mismatch", "M2 registry entries must use M1 schema version", registry_path, f"{name}.schema_version"))
    contract_doc = resolve(entry.get("contract_doc", ""))
    if not contract_doc.exists():
        errors.append(err("contract_doc_missing", "contract_doc does not exist", contract_doc, f"{name}.contract_doc"))
    validator = resolve(entry.get("validator", ""))
    supported_contracts: set[str] = set()
    validator_available = False
    if not validator.exists():
        errors.append(err("validator_missing", "validator does not exist", validator, f"{name}.validator"))
    else:
        key = str(validator)
        if key not in validator_cache:
            validator_cache[key] = validator_contracts(validator)
        validator_available, supported_contracts, detail = validator_cache[key]
        if not validator_available:
            errors.append(err("validator_json_unavailable", f"validator --json failed: {detail}", validator, f"{name}.validator"))
    golden = resolve(entry.get("golden_sample", ""))
    expected_path = golden / "expected_result.json"
    expected_contract = ""
    validator_contract = str(entry.get("validator_contract") or entry.get("artifact_type") or "")
    if not golden.exists() or not expected_path.exists():
        errors.append(err("golden_sample_missing", "golden_sample or expected_result.json does not exist", golden, f"{name}.golden_sample"))
    else:
        expected = load_json(expected_path)
        expected_contract = str(expected.get("contract", ""))
        if expected_contract != validator_contract:
            errors.append(err("registry_contract_mismatch", f"golden contract {expected_contract} does not match validator contract {validator_contract}", expected_path, f"{name}.golden_sample"))
    if validator_available and validator_contract not in supported_contracts:
        errors.append(err("registry_validator_contract_unsupported", f"validator does not support contract {validator_contract}", validator, f"{name}.validator_contract"))
    if validator_available and expected_contract == validator_contract and validator_contract in supported_contracts:
        ok, detail = run_entry_validator(validator, validator_contract, golden)
        if not ok:
            errors.append(err("registry_golden_validation_failed", f"validator failed for registry golden sample: {detail}", golden, f"{name}.golden_sample"))
    for list_field in ["capabilities", "allowed_consumers", "forbidden_consumers"]:
        if not isinstance(entry.get(list_field), list) or not entry.get(list_field):
            errors.append(err("registry_list_empty", f"{list_field} must be a non-empty list", registry_path, f"{name}.{list_field}"))
    if entry.get("production_allowed") is not False:
        errors.append(err("production_allowed_not_false", "production_allowed must default to false", registry_path, f"{name}.production_allowed"))
    if entry.get("diagnostic_only") is True and "default_strategy" in "|".join(map(str, entry.get("allowed_consumers", []))):
        errors.append(err("diagnostic_default_strategy", "diagnostic_only entry cannot feed default strategy", registry_path, f"{name}.allowed_consumers"))
    if entry.get("artifact_type") in {"agent_readonly_context", "frontend_agent_panel"}:
        forbidden = "|".join(map(str, entry.get("forbidden_consumers", [])))
        caps = "|".join(map(str, entry.get("capabilities", [])))
        if "agent_tool_action_prompt_expansion" not in forbidden and "agent_placeholder" not in caps:
            errors.append(err("agent_placeholder_boundary_missing", "Agent entry must remain placeholder and forbid tool/action/prompt expansion", registry_path, name))
    return errors


def validate_templates(template_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for name in REQUIRED_TEMPLATES:
        path = template_dir / name
        exists = path.exists()
        text = path.read_text(encoding="utf-8") if exists else ""
        missing = [marker for marker in REQUIRED_TEMPLATE_MARKERS if marker not in text]
        if "AGENT" in name:
            missing.extend([marker for marker in AGENT_TEMPLATE_MARKERS if marker not in text])
        status = "pass" if exists and not missing else "fail"
        rows.append({"template": name, "path": rel(path), "exists": exists, "missing_markers": missing, "status": status})
        if not exists:
            errors.append(err("template_missing", "required template is missing", path, name))
        for marker in missing:
            errors.append(err("template_marker_missing", f"template missing marker {marker}", path, marker))
    return rows, errors


def validate_registries(registry_paths: list[Path]) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    checked: list[str] = []
    entry_rows: list[dict[str, Any]] = []
    validator_cache: dict[str, tuple[bool, set[str], str]] = {}
    for registry_path in registry_paths:
        if not registry_path.exists():
            errors.append(err("registry_missing", "registry file does not exist", registry_path))
            continue
        checked.append(rel(registry_path))
        data = load_yaml(registry_path)
        entries = collect_entries(registry_path, data)
        if not entries:
            errors.append(err("registry_entries_missing", "registry has no M2 entries", registry_path, "entries"))
        for name, entry in sorted(entries.items()):
            before = len(errors)
            errors.extend(validate_entry(name, entry or {}, registry_path, validator_cache))
            entry_rows.append({
                "registry": rel(registry_path),
                "entry": name,
                "artifact_type": (entry or {}).get("artifact_type"),
                "schema_version": (entry or {}).get("schema_version"),
                "production_allowed": (entry or {}).get("production_allowed"),
                "diagnostic_only": (entry or {}).get("diagnostic_only"),
                "status": "pass" if len(errors) == before else "fail",
            })
    template_rows, template_errors = validate_templates(TEMPLATE_DIR)
    errors.extend(template_errors)
    checked.extend(row["path"] for row in template_rows if row["exists"])
    ok = not errors
    return {
        "ok": ok,
        "status": "passed" if ok else "failed",
        "schema_version": SCHEMA_VERSION,
        "errors": errors,
        "warnings": warnings,
        "checked_files": checked,
        "registry_count": len(registry_paths),
        "entry_count": len(entry_rows),
        "template_count": len(template_rows),
        "entries": entry_rows,
        "templates": template_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase M2 registries and onboarding templates.")
    parser.add_argument("--registry", action="append", help="Registry yaml path; may be repeated")
    parser.add_argument("--json", action="store_true", help="Print JSON")
    args = parser.parse_args()
    paths = [resolve(p) for p in args.registry] if args.registry else DEFAULT_REGISTRIES
    result = validate_registries(paths)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']}")
        print(f"entry_count={result['entry_count']}")
        print(f"template_count={result['template_count']}")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
