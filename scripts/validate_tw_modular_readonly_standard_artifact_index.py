#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "data_tw/artifacts/readonly_standard_artifact_index/d4/manifest.json"
FORBIDDEN_UNSAFE_KEYS = {
    "broker",
    "quick_trade",
    "quick-trade",
    "order_action",
    "target_position",
    "target-position",
    "targetposition",
    "target_weight",
    "target_qty",
    "target_quantity",
    "production_trade_instruction",
    "provider_publish",
    "accepted_latest",
}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check(name: str, ok: bool, details: str = "") -> dict[str, Any]:
    return {"name": name, "status": "pass" if ok else "fail", "details": details}


def contains_forbidden_key(obj: Any, path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            lowered = str(key).lower()
            if lowered in FORBIDDEN_UNSAFE_KEYS:
                hits.append(f"{path}.{key}" if path else str(key))
            hits.extend(contains_forbidden_key(value, f"{path}.{key}" if path else str(key)))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            hits.extend(contains_forbidden_key(value, f"{path}[{idx}]"))
    return hits


def validate_checksum(manifest: dict[str, Any]) -> tuple[bool, str]:
    checksum_path = resolve(str((manifest.get("artifacts") or {}).get("checksum_manifest", "")))
    if not checksum_path.exists():
        return False, "checksum manifest missing"
    payload = load_json(checksum_path)
    bad: list[str] = []
    for item in payload.get("files", []):
        path = resolve(str(item.get("path", "")))
        if not path.exists() or sha256_file(path) != item.get("sha256"):
            bad.append(str(item.get("path", "")))
    return not bad and bool(payload.get("files")), f"checked={len(payload.get('files', []))}; bad={'|'.join(bad)}"


def validate_index(manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    parity_path = resolve(str(manifest.get("order_intent_replay_parity_manifest", "")))
    replay_path = resolve(str(manifest.get("order_intent_replay_result_manifest", "")))
    baseline_path = resolve(str(manifest.get("baseline_manifest", "")))
    policy_path = resolve(str((manifest.get("replay_window_policy_metadata") or {}).get("policy_path", "")))
    parity = load_json(parity_path) if parity_path.exists() else {}
    replay = load_json(replay_path) if replay_path.exists() else {}
    policy = load_yaml(policy_path) if policy_path.exists() else {}
    order_paths = [resolve(str(path)) for path in manifest.get("order_intent_artifact_manifests", [])]
    checks = [
        check("artifact_type", manifest.get("artifact_type") == "readonly_standard_artifact_index", str(manifest.get("artifact_type"))),
        check("schema_version", manifest.get("schema_version") == "readonly_standard_artifact_index_d4_v1", str(manifest.get("schema_version"))),
        check("readonly_only", manifest.get("readonly_only") is True),
        check("not_order", manifest.get("not_order") is True and manifest.get("no_order_action") is True),
        check("not_investment_advice", manifest.get("not_investment_advice") is True),
        check("not_target_position", manifest.get("not_target_position") is True),
        check("production_trade_enabled_false", manifest.get("production_trade_enabled") is False),
        check("no_provider_publish", manifest.get("no_provider_publish") is True),
        check("no_accepted_latest_switch", manifest.get("no_accepted_latest_switch") is True),
        check("no_monitor_broker_order", manifest.get("no_monitor_broker_order") is True),
        check("standard_artifact_index_exists", manifest_path.exists()),
        check("all_referenced_manifests_exist", parity_path.exists() and replay_path.exists() and baseline_path.exists() and policy_path.exists() and all(path.exists() for path in order_paths), f"orders={len(order_paths)}"),
        check("order_intent_replay_manifest_not_equal_baseline_manifest", replay_path.resolve() != baseline_path.resolve() if replay_path.exists() and baseline_path.exists() else False),
        check("replay_result_generated_by_replay_execution_engine", replay.get("generated_by") == "replay_execution_engine", str(replay.get("generated_by"))),
        check("replay_result_execution_input_source_order_intent", replay.get("execution_input_source") == "order_intent_artifact", str(replay.get("execution_input_source"))),
        check("replay_result_decision_source_order_intent", replay.get("decision_source") == "order_intent_artifact", str(replay.get("decision_source"))),
        check("diagnostic_rule_not_valid_strategy_evidence", manifest.get("diagnostic_rule_only_for_parity") is True and manifest.get("diagnostic_rule_not_valid_strategy_evidence") is True),
        check("parity_status_pass", manifest.get("parity_status") == "pass", str(manifest.get("parity_status"))),
        check("row_count_consistency", manifest.get("row_counts") == parity.get("row_counts") and manifest.get("replay_result_row_counts") == replay.get("row_counts")),
        check("fixed_window_only", manifest.get("fixed_window_only") is True and policy.get("fixed_window_only") is True),
        check("user_selectable_range_disabled", manifest.get("user_selectable_range_enabled") is False and policy.get("user_selectable_range_enabled") is False),
        check("replay_window_policy_metadata_traceable", policy_path.exists() and bool(policy.get("models")) and policy.get("policy_version") == manifest.get("replay_window_policy_metadata", {}).get("policy_version")),
    ]
    unsafe_hits = contains_forbidden_key(manifest)
    checks.append(check("no_unsafe_field_names", not unsafe_hits, "|".join(unsafe_hits)))
    checksum_ok, checksum_details = validate_checksum(manifest)
    checks.append(check("checksum_ok", checksum_ok, checksum_details))
    return {"ok": all(row["status"] == "pass" for row in checks), "artifact": rel(manifest_path), "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate D4 readonly standard artifact index.")
    parser.add_argument("--artifact", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = validate_index(resolve(args.artifact))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']}")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
