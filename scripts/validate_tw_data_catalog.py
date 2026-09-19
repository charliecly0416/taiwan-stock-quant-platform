#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

STATUS_ENUM = {
    "READY",
    "PARTIAL_READY",
    "MISSING",
    "STALE",
    "BLOCKED_PROVIDER",
    "BLOCKED_SCHEMA",
    "BLOCKED_PIT",
    "BLOCKED_COVERAGE",
    "BLOCKED_VALIDATOR",
    "RESEARCH_ONLY",
    "LEGACY_UNCATALOGED",
    "TEMPORARY_BRIDGE",
}

REQUIRED_TOP_LEVEL = [
    "catalog_version",
    "generated_at",
    "source_inventory",
    "entries",
    "summary",
    "forbidden_action_audit",
]

REQUIRED_ENTRY_FIELDS = [
    "dataset_id",
    "layer",
    "asof",
    "date_min",
    "date_max",
    "symbol_count",
    "row_count",
    "path",
    "manifest_path",
    "schema_path",
    "coverage_audit_path",
    "lineage_path",
    "validator_report_path",
    "status",
    "status_reason",
    "source_provider",
    "source_run_id",
    "checksum",
    "pit_policy",
    "available_at_policy",
    "canonicality",
    "latest_concept",
    "forbidden_action_flags",
]

REQUIRED_LATEST_CONCEPTS = [
    "provider_raw_latest",
    "normalized_latest",
    "price_store_latest",
    "feature_store_latest",
    "qlib_accepted_latest",
    "model_signal_latest",
    "readonly_bridge_latest",
    "readonly_snapshot_latest",
    "agent_prompt_latest",
    "temporary_research_bridge_latest",
]

FORBIDDEN_ACTION_KEYS = [
    "real_data_fetch_triggered",
    "provider_refresh_triggered",
    "provider_publish_triggered",
    "qlib_accepted_latest_switched",
    "readonly_latest_published",
    "agent_prompt_published",
    "model_training_triggered",
    "model_inference_triggered",
    "strategy_replay_triggered",
    "broker_order_quick_trade_triggered",
    "target_position_or_weight_generated",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def issue(code: str, message: str, path: str = "", field: str = "", severity: str = "error") -> dict[str, str]:
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "path": path,
        "field": field,
    }


def path_exists(path_text: str) -> bool:
    return bool(path_text) and (ROOT / path_text).exists()


def check_forbidden_flags(
    flags: Any,
    errors: list[dict[str, str]],
    path_label: str,
    field_prefix: str,
) -> None:
    if not isinstance(flags, dict):
        errors.append(issue("forbidden_flags_not_object", "forbidden_action_flags/actions must be an object", path_label, field_prefix))
        return
    for key in FORBIDDEN_ACTION_KEYS:
        if flags.get(key) is True:
            errors.append(issue("forbidden_action_triggered", f"{key} must be false in DNG1", path_label, f"{field_prefix}.{key}"))


def validate_catalog(catalog_path: Path, latest_status_path: Path) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    catalog = load_json(catalog_path)
    latest = load_json(latest_status_path)

    for field in REQUIRED_TOP_LEVEL:
        if field not in catalog:
            errors.append(issue("catalog_top_level_field_missing", f"{field} is required", rel(catalog_path), field))

    entries = catalog.get("entries")
    if not isinstance(entries, list):
        errors.append(issue("entries_not_list", "entries must be a list", rel(catalog_path), "entries"))
        entries = []

    for idx, entry in enumerate(entries):
        path_label = f"entries[{idx}]"
        if not isinstance(entry, dict):
            errors.append(issue("entry_not_object", "entry must be an object", rel(catalog_path), path_label))
            continue
        for field in REQUIRED_ENTRY_FIELDS:
            if field not in entry:
                errors.append(issue("entry_field_missing", f"{field} is required", rel(catalog_path), f"{path_label}.{field}"))
        status = str(entry.get("status", ""))
        canonicality = str(entry.get("canonicality", ""))
        data_path = str(entry.get("path", ""))
        if status not in STATUS_ENUM:
            errors.append(issue("entry_status_invalid", f"{status} is not an allowed status", data_path, "status"))
        exists = path_exists(data_path)
        if status != "MISSING" and not exists:
            errors.append(issue("entry_path_missing", "non-MISSING entry path does not exist", data_path, "path"))
        if status == "MISSING" and exists:
            warnings.append(issue("missing_status_path_exists", "entry is MISSING but path exists", data_path, "status", "warning"))
        if status == "READY":
            if canonicality in {"temporary_bridge", "missing_layer"}:
                errors.append(issue("ready_forbidden_canonicality", "READY must not be used for temporary bridge or missing layer", data_path, "canonicality"))
            if status in {"TEMPORARY_BRIDGE", "LEGACY_UNCATALOGED"}:
                errors.append(issue("ready_forbidden_status", "READY must not be used for bridge or legacy uncataloged entry", data_path, "status"))
            for evidence_field in ["manifest_path", "schema_path", "coverage_audit_path", "lineage_path"]:
                evidence_path = str(entry.get(evidence_field, ""))
                if not path_exists(evidence_path):
                    errors.append(issue("ready_missing_evidence", f"READY requires existing {evidence_field}", data_path, evidence_field))
        if status == "READY" and ("bridge" in data_path.lower() or data_path.startswith("data_tw/experiments/")):
            errors.append(issue("ready_forbidden_path_class", "READY must not be used for bridge or data_tw/experiments path", data_path, "path"))
        check_forbidden_flags(entry.get("forbidden_action_flags"), errors, data_path, "forbidden_action_flags")

    catalog_audit = (catalog.get("forbidden_action_audit") or {}).get("actions", {})
    check_forbidden_flags(catalog_audit, errors, rel(catalog_path), "forbidden_action_audit.actions")

    latest_required = ["schema_version", "generated_at", "latest_by_concept", "known_mismatch", "recommended_next_actions", "forbidden_action_audit"]
    for field in latest_required:
        if field not in latest:
            errors.append(issue("latest_top_level_field_missing", f"{field} is required", rel(latest_status_path), field))
    latest_by_concept = latest.get("latest_by_concept") or {}
    if not isinstance(latest_by_concept, dict):
        errors.append(issue("latest_by_concept_not_object", "latest_by_concept must be an object", rel(latest_status_path), "latest_by_concept"))
        latest_by_concept = {}
    for concept in REQUIRED_LATEST_CONCEPTS:
        if concept not in latest_by_concept:
            errors.append(issue("latest_concept_missing", f"{concept} is required and must not be omitted", rel(latest_status_path), concept))
            continue
        item = latest_by_concept.get(concept) or {}
        status = str(item.get("status", ""))
        if status not in STATUS_ENUM:
            errors.append(issue("latest_status_invalid", f"{status} is not an allowed status", rel(latest_status_path), concept))
        if concept in {"readonly_bridge_latest", "temporary_research_bridge_latest"} and status == "READY":
            errors.append(issue("latest_bridge_marked_ready", f"{concept} must not be READY", rel(latest_status_path), concept))
        if concept == "agent_prompt_latest" and status != "MISSING":
            warnings.append(issue("agent_prompt_latest_present", "agent_prompt_latest is present; verify it was not inferred from readonly snapshot", rel(latest_status_path), concept, "warning"))
        for candidate_idx, candidate in enumerate(item.get("candidates") or []):
            candidate_status = str(candidate.get("status", ""))
            candidate_path = str(candidate.get("path", ""))
            if candidate_status not in STATUS_ENUM:
                errors.append(issue("latest_candidate_status_invalid", f"{candidate_status} is not allowed", candidate_path, f"{concept}.candidates[{candidate_idx}].status"))
            if candidate_status != "MISSING" and candidate_path and not path_exists(candidate_path):
                errors.append(issue("latest_candidate_path_missing", "latest candidate path does not exist", candidate_path, f"{concept}.candidates[{candidate_idx}].path"))
            check_forbidden_flags(candidate.get("forbidden_action_flags", {}), errors, candidate_path, f"{concept}.candidates[{candidate_idx}].forbidden_action_flags")
    latest_audit = (latest.get("forbidden_action_audit") or {}).get("actions", {})
    check_forbidden_flags(latest_audit, errors, rel(latest_status_path), "forbidden_action_audit.actions")

    status_counts = Counter(str(entry.get("status")) for entry in entries if isinstance(entry, dict))
    latest_counts = Counter(str(item.get("status")) for item in latest_by_concept.values() if isinstance(item, dict))
    ok = not errors
    return {
        "schema_version": "v1.tw_data_catalog_validator.dng1",
        "generated_at": now(),
        "ok": ok,
        "status": "passed" if ok else "failed",
        "catalog": rel(catalog_path),
        "latest_status": rel(latest_status_path),
        "entry_count": len(entries),
        "status_counts": dict(sorted(status_counts.items())),
        "latest_concept_status_counts": dict(sorted(latest_counts.items())),
        "errors": errors,
        "warnings": warnings,
        "checked_requirements": [
            "required top-level fields",
            "entry required fields",
            "status enum",
            "path existence",
            "latest concepts coverage",
            "forbidden action flags",
            "READY not used for temporary bridge or legacy uncataloged paths",
            "READY requires manifest/schema/coverage/lineage evidence",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate DNG1 Taiwan data catalog outputs.")
    parser.add_argument("--catalog", default="data_tw/catalog/data_catalog.json")
    parser.add_argument("--latest-status", default="data_tw/catalog/latest_status.json")
    parser.add_argument("--output", default="")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = validate_catalog(ROOT / args.catalog, ROOT / args.latest_status)
    if args.output:
        out = ROOT / args.output
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{report['status']}: {report['entry_count']} entries, {len(report['errors'])} errors")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
