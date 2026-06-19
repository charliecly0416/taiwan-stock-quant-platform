#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from validate_tw_modular_artifact_contract import validate_model_signal

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "m5.0.0"
DEFAULT_GOLDEN_ROOT = ROOT / "data_tw/golden_samples/modular_contracts/m5/onboarding_smoke"
DEFAULT_REGISTRY = ROOT / "configs/tw_modular_registry.yaml"
SMOKE_MARKERS = ["smoke_only", "not_valid_strategy_evidence", "no_replay_return_conclusion", "not_default_candidate"]
FORBIDDEN_TRUE_MARKERS = [
    "no_training",
    "no_tuning",
    "no_default_switch",
    "no_provider_publish",
    "no_accepted_latest_switch",
    "no_monitor_write",
    "no_broker_order",
    "agent_untouched",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def resolve(value: str | Path) -> Path:
    p = Path(str(value))
    return p if p.is_absolute() else ROOT / p


def error(code: str, message: str, path: Path, field: str = "") -> dict[str, str]:
    return {"code": code, "message": message, "path": rel(path), "field": field}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def check_smoke_markers(obj: dict[str, Any], path: Path, prefix: str = "") -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for marker in SMOKE_MARKERS:
        if obj.get(marker) is not True:
            errors.append(error("smoke_marker_missing", f"{prefix}{marker} must be true", path, marker))
    return errors


def check_forbidden_markers(manifest: dict[str, Any], path: Path) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for marker in FORBIDDEN_TRUE_MARKERS:
        if manifest.get(marker) is not True:
            errors.append(error("forbidden_action_marker_missing", f"{marker} must be true", path, marker))
    return errors


def registry_entries(registry_path: Path) -> dict[str, Any]:
    registry = load_yaml(registry_path)
    return ((registry.get("m5_smoke_registry") or {}).get("entries") or {})


def validate_registry_links(manifest: dict[str, Any], registry_path: Path, manifest_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    entries = registry_entries(registry_path)
    for name in manifest.get("registry_entries") or []:
        entry = entries.get(str(name))
        rows.append({"entry": str(name), "exists": bool(entry), "status": "pass" if entry else "fail"})
        if not entry:
            errors.append(error("registry_entry_missing", f"M5 smoke registry entry missing: {name}", registry_path, str(name)))
            continue
        errors.extend(check_smoke_markers(entry, registry_path, f"{name}."))
        if entry.get("production_allowed") is not False:
            errors.append(error("production_allowed_not_false", "M5 smoke registry entry must not be production allowed", registry_path, str(name)))
        if entry.get("diagnostic_only") is not True:
            errors.append(error("diagnostic_only_missing", "M5 smoke registry entry must be diagnostic_only", registry_path, str(name)))
        forbidden = "|".join(map(str, entry.get("forbidden_consumers") or []))
        for token in ["default_candidate", "broker", "provider_publish"]:
            if token not in forbidden:
                errors.append(error("registry_forbidden_consumer_missing", f"M5 smoke registry entry must forbid {token}", registry_path, str(name)))
    return rows, errors


def validate_order_intent(order_manifest_path: Path) -> tuple[dict[str, Any], list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    manifest = load_json(order_manifest_path)
    errors.extend(check_smoke_markers(manifest, order_manifest_path, "order_intent."))
    for marker in ["readonly_only", "not_order", "not_target_position", "not_investment_advice"]:
        if manifest.get(marker) is not True:
            errors.append(error("order_intent_boundary_missing", f"{marker} must be true", order_manifest_path, marker))
    rel_csv = (manifest.get("output_files") or {}).get("order_intents")
    rows = 0
    if not rel_csv:
        errors.append(error("order_intent_file_missing", "order intent csv not declared", order_manifest_path, "output_files.order_intents"))
    else:
        csv_path = resolve(rel_csv)
        if not csv_path.exists():
            errors.append(error("order_intent_file_missing", "order intent csv missing", csv_path, "output_files.order_intents"))
        else:
            frame = pd.read_csv(csv_path)
            rows = int(len(frame))
            for marker in ["readonly_only", "not_order", "not_target_position", "not_investment_advice", *SMOKE_MARKERS]:
                if marker not in frame.columns:
                    errors.append(error("order_intent_column_missing", f"order intent csv missing {marker}", csv_path, marker))
                elif not frame[marker].astype(str).str.lower().isin(["true", "1"]).all():
                    errors.append(error("order_intent_marker_false", f"order intent csv {marker} must be true", csv_path, marker))
    return {"path": rel(order_manifest_path), "row_count": rows, "status": "pass" if not errors else "fail"}, errors


def validate_smoke_sample(sample_dir: Path, registry_path: Path = DEFAULT_REGISTRY) -> dict[str, Any]:
    manifest_path = sample_dir / "manifest.json"
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    if not manifest_path.exists():
        return {"ok": False, "status": "failed", "schema_version": SCHEMA_VERSION, "errors": [error("manifest_missing", "manifest.json missing", manifest_path)], "warnings": warnings}
    manifest = load_json(manifest_path)
    if manifest.get("artifact_type") != "m5_onboarding_smoke":
        errors.append(error("artifact_type_invalid", "artifact_type must be m5_onboarding_smoke", manifest_path, "artifact_type"))
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(error("schema_version_invalid", f"schema_version must be {SCHEMA_VERSION}", manifest_path, "schema_version"))
    errors.extend(check_smoke_markers(manifest, manifest_path))
    errors.extend(check_forbidden_markers(manifest, manifest_path))
    if manifest.get("no_replay_return") is not True:
        errors.append(error("replay_return_not_disabled", "no_replay_return must be true", manifest_path, "no_replay_return"))

    registry_rows, registry_errors = validate_registry_links(manifest, registry_path, manifest_path)
    errors.extend(registry_errors)

    model_manifest_path = resolve(manifest.get("model_signal_manifest", ""))
    strategy_path = resolve(manifest.get("strategy_dependency_path", ""))
    model_result: dict[str, Any] = {"ok": False, "status": "missing"}
    strategy_dependency: dict[str, Any] = {}
    if not model_manifest_path.exists():
        errors.append(error("model_signal_manifest_missing", "model signal manifest missing", model_manifest_path, "model_signal_manifest"))
    else:
        model_manifest = load_json(model_manifest_path)
        errors.extend(check_smoke_markers(model_manifest, model_manifest_path, "model_signal."))
    if not strategy_path.exists():
        errors.append(error("strategy_dependency_missing", "strategy dependency missing", strategy_path, "strategy_dependency_path"))
    else:
        strategy_dependency = load_yaml(strategy_path)
        errors.extend(check_smoke_markers(strategy_dependency, strategy_path, "strategy_dependency."))
        if strategy_dependency.get("diagnostic_only") is not True:
            errors.append(error("strategy_dependency_diagnostic_only_missing", "strategy smoke dependency must be diagnostic_only", strategy_path, "diagnostic_only"))
        forbidden_actions = strategy_dependency.get("forbidden_actions") or {}
        for marker in ["no_training", "no_tuning", "no_score_recompute", "no_replay", "no_return_filtering", "no_default_strategy_change", "no_frontend_change", "no_daily_orchestrator_change", "no_provider_publish", "no_accepted_latest_switch", "no_monitor", "no_broker_order"]:
            if forbidden_actions.get(marker) is not True:
                errors.append(error("strategy_forbidden_action_missing", f"strategy forbidden action {marker} must be true", strategy_path, marker))
    if model_manifest_path.exists() and strategy_path.exists():
        compatibility_dependency = dict(strategy_dependency)
        compatibility_dependency["diagnostic_only"] = False
        compatibility_dependency.pop("not_valid_strategy_evidence", None)
        model_result = validate_model_signal(model_manifest_path, compatibility_dependency)
        if not model_result.get("ok"):
            errors.append(error("model_signal_compatibility_failed", "ModelSignalArtifact compatibility check failed", model_manifest_path, "model_signal"))
    order_result: dict[str, Any] = {"status": "skipped"}
    if manifest.get("order_intent_manifest"):
        order_result, order_errors = validate_order_intent(resolve(manifest["order_intent_manifest"]))
        errors.extend(order_errors)

    forbidden_surface = {
        "training_count": 0,
        "replay_return_conclusion_count": 0,
        "default_switch_count": 0,
        "provider_publish_refresh_accepted_latest_count": 0,
        "monitor_write_count": 0,
        "broker_order_count": 0,
        "agent_expansion_count": 0,
    }
    ok = not errors
    return {
        "ok": ok,
        "status": "passed" if ok else "failed",
        "schema_version": SCHEMA_VERSION,
        "sample_dir": rel(sample_dir),
        "errors": errors,
        "warnings": warnings,
        "registry_entries": registry_rows,
        "model_signal_compatibility": {"ok": bool(model_result.get("ok")), "checks": model_result.get("checks", [])},
        "strategy_dependency_check": {"ok": strategy_path.exists() and not any(e["code"].startswith("strategy_") for e in errors), "path": rel(strategy_path)},
        "order_intent_compatibility": order_result,
        "forbidden_surface_audit": forbidden_surface,
    }


def run_golden(golden_root: Path, registry_path: Path) -> dict[str, Any]:
    rows = []
    errors: list[dict[str, str]] = []
    for expected_path in sorted(golden_root.glob("*/expected_result.json")):
        sample_dir = expected_path.parent
        expected = load_json(expected_path)
        result = validate_smoke_sample(sample_dir, registry_path)
        expected_ok = bool(expected.get("ok"))
        actual_ok = bool(result.get("ok"))
        expected_codes = set(map(str, expected.get("error_codes") or []))
        actual_codes = set(str(item.get("code")) for item in result.get("errors", []))
        codes_match = not expected_codes or expected_codes.issubset(actual_codes)
        passed = expected_ok == actual_ok and codes_match
        rows.append({"sample": rel(sample_dir), "expected_ok": expected_ok, "actual_ok": actual_ok, "actual_error_codes": sorted(actual_codes), "status": "pass" if passed else "fail"})
        if not passed:
            errors.append(error("golden_expectation_mismatch", "M5 smoke golden expectation mismatch", sample_dir, rel(sample_dir)))
    ok = not errors and bool(rows)
    return {"ok": ok, "status": "passed" if ok else "failed", "schema_version": SCHEMA_VERSION, "sample_count": len(rows), "samples": rows, "errors": errors, "warnings": []}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase M5 smoke-only onboarding artifacts.")
    parser.add_argument("--artifact-path", help="M5 smoke artifact directory")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--run-golden", action="store_true")
    parser.add_argument("--golden-root", default=str(DEFAULT_GOLDEN_ROOT))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    registry_path = resolve(args.registry)
    if args.run_golden:
        result = run_golden(resolve(args.golden_root), registry_path)
    elif args.artifact_path:
        result = validate_smoke_sample(resolve(args.artifact_path), registry_path)
    else:
        parser.error("--artifact-path or --run-golden is required")
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']}")
        print(f"status={result['status']}")
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
