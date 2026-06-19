#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check(name: str, ok: bool, details: str = "") -> dict[str, Any]:
    return {"name": name, "status": "pass" if ok else "fail", "details": details}


def checksum_ok(manifest: dict[str, Any]) -> tuple[bool, str]:
    path = resolve(str(manifest.get("checksum_manifest", "")))
    if not path.exists():
        return False, "missing checksum_manifest"
    payload = load_json(path)
    bad = []
    for item in payload.get("files", []):
        target = resolve(str(item.get("path", "")))
        if not target.exists() or sha256_file(target) != item.get("sha256"):
            bad.append(str(item.get("path", "")))
    return not bad and bool(payload.get("files")), f"checked={len(payload.get('files', []))}; bad={'|'.join(bad)}"


def validate_artifact(manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    artifacts = manifest.get("artifacts") or {}
    order_paths = [resolve(str(path)) for path in manifest.get("order_intent_artifacts", [])]
    forbidden_path = resolve(str(manifest.get("forbidden_scope_audit_json", "")))
    forbidden = load_json(forbidden_path) if forbidden_path.exists() else {}
    validation = manifest.get("replay_window_policy_validation") or {}
    required_artifacts = ["summary", "daily_nav", "actions", "snapshots", "decision_source_audit", "forbidden_scope_audit", "action_lineage_audit"]
    missing_artifacts = [key for key in required_artifacts if not artifacts.get(key) or not resolve(str(artifacts.get(key))).exists()]
    checksum_pass, checksum_details = checksum_ok(manifest)
    checks = [
        check("artifact_type", manifest.get("artifact_type") == "replay_result", str(manifest.get("artifact_type"))),
        check("schema_version", manifest.get("schema_version") == "readonly_replay_result_d6_v1", str(manifest.get("schema_version"))),
        check("readonly_only", manifest.get("readonly_only") is True),
        check("not_order", manifest.get("not_order") is True and manifest.get("no_order_action") is True),
        check("not_target_position", manifest.get("not_target_position") is True),
        check("not_investment_advice", manifest.get("not_investment_advice") is True),
        check("production_trade_enabled_false", manifest.get("production_trade_enabled") is False),
        check("generated_by_replay_execution_engine", manifest.get("generated_by") == "replay_execution_engine", str(manifest.get("generated_by"))),
        check("execution_input_source_order_intent", manifest.get("execution_input_source") == "order_intent_artifact", str(manifest.get("execution_input_source"))),
        check("decision_source_order_intent", manifest.get("decision_source") == "order_intent_artifact", str(manifest.get("decision_source"))),
        check("not_copied_from_legacy_replay", manifest.get("not_copied_from_legacy_replay") is True),
        check("not_generated_in_api_handler", manifest.get("not_generated_in_api_handler") is True),
        check("policy_validation_ok", validation.get("ok") is True and validation.get("model_training_windows_traceable") is True),
        check("source_order_intents_exist", bool(order_paths) and all(path.exists() for path in order_paths), f"count={len(order_paths)}"),
        check("required_artifacts_exist", not missing_artifacts, "|".join(missing_artifacts)),
        check("forbidden_scope_audit_exists", forbidden_path.exists(), rel(forbidden_path) if forbidden_path.exists() else "missing"),
        check("forbidden_scope_audit_pass", forbidden.get("status") == "pass", str(forbidden.get("status"))),
        check("no_provider_publish", manifest.get("no_provider_publish") is True and forbidden.get("no_provider_publish") is True),
        check("no_accepted_latest_switch", manifest.get("no_accepted_latest_switch") is True and forbidden.get("no_accepted_latest_switch") is True),
        check("no_monitor_broker_order", manifest.get("no_monitor_broker_order") is True and forbidden.get("no_monitor_broker_order") is True),
        check("checksum_ok", checksum_pass, checksum_details),
    ]
    return {"ok": all(row["status"] == "pass" for row in checks), "artifact": rel(manifest_path), "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate D6 audited readonly replay artifact.")
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = validate_artifact(resolve(args.artifact))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']}")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
