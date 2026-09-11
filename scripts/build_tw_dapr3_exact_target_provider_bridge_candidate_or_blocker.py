#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DAPR_ROOT = ROOT / "data_tw/experiments/daily_accepted_production_readiness"
DAPR0_DIR = DAPR_ROOT / "dapr0_inventory"
DAPR1_DIR = DAPR_ROOT / "dapr1_canonical_bridge_contract"
OUT_DIR = DAPR_ROOT / "dapr3_exact_target_provider_bridge_candidate_or_blocker"

READINESS_SEARCH_ROOTS = [
    ROOT / "data_tw/experiments",
    ROOT / "data_tw/ops",
    ROOT / "qlib_pipeline/data_tw/experiments",
]
READINESS_NAMES = {
    "provider_candidate_readiness.json",
    "provider_candidate_readiness_accepted.json",
    "canonical_bridge_readiness.json",
}

FORBIDDEN_ACTIONS = {
    "provider_pull_triggered": False,
    "provider_publish_triggered": False,
    "formal_provider_or_calendar_mutated": False,
    "formal_normalized_mutated": False,
    "accepted_latest_switch_triggered": False,
    "qlib_refresh_triggered": False,
    "model_scoring_triggered": False,
    "model_inference_input_built": False,
    "score_job_built": False,
    "model_signal_artifact_built": False,
    "readonly_latest_published": False,
    "agent_prompt_built_or_published": False,
    "openai_called": False,
    "monitor_broker_order_or_target_written": False,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(name: str, payload: Any) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def sha256(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(paths: list[Path]) -> dict[str, Any]:
    return {
        "schema_version": "dapr.artifact_manifest.v1",
        "created_at": utc_now(),
        "status": "pass",
        "entries": [
            {
                "path": rel(path),
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() else None,
                "sha256": sha256(path),
            }
            for path in paths
        ],
    }


def source_entries(pointer_inventory: dict[str, Any]) -> dict[str, Any]:
    daily_source_inventory = pointer_inventory.get("daily_source_inventory")
    if not isinstance(daily_source_inventory, dict):
        return {}
    sources = daily_source_inventory.get("sources")
    return sources if isinstance(sources, dict) else daily_source_inventory


def discover_readiness_artifacts(target_asof: str) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for root in READINESS_SEARCH_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*readiness*.json"):
            if path.name not in READINESS_NAMES:
                continue
            payload = read_json(path)
            kind = "canonical_bridge" if "canonical_bridge" in path.name else "provider_candidate"
            candidate_asof = str(payload.get("candidate_asof") or "")
            bridge_asof = str(payload.get("bridge_asof") or "")
            artifact_target = str(payload.get("target_asof") or payload.get("asof") or "")
            exact_match = (candidate_asof == target_asof) if kind == "provider_candidate" else (bridge_asof == target_asof)
            forbidden_actions = payload.get("forbidden_actions") if isinstance(payload.get("forbidden_actions"), dict) else {}
            forbidden_summary = payload.get("forbidden_action_summary") if isinstance(payload.get("forbidden_action_summary"), dict) else {}
            forbidden_all_false = bool(forbidden_actions.get("all_false")) or (
                bool(forbidden_summary) and all(value is False for value in forbidden_summary.values())
            )
            artifacts.append(
                {
                    "path": rel(path),
                    "kind": kind,
                    "schema_version": str(payload.get("schema_version") or ""),
                    "candidate_asof": candidate_asof,
                    "bridge_asof": bridge_asof,
                    "target_asof": artifact_target,
                    "validator_status": str(payload.get("validator_status") or ""),
                    "production_allowed": payload.get("production_allowed"),
                    "not_published_latest": payload.get("not_published_latest"),
                    "forbidden_actions_all_false": forbidden_all_false,
                    "exact_target_match": exact_match,
                    "sha256": sha256(path),
                }
            )
    return sorted(artifacts, key=lambda row: (not row["exact_target_match"], row["kind"], row["path"]))


def validate_local_artifact(row: dict[str, Any]) -> dict[str, Any]:
    readiness_pass = (
        row.get("exact_target_match") is True
        and row.get("validator_status") == "pass"
        and row.get("production_allowed") is False
        and row.get("not_published_latest") is True
        and row.get("forbidden_actions_all_false") is True
    )
    return {
        **row,
        "readiness_validation_status": "pass" if readiness_pass else "fail",
        "readiness_accepted_for_dapr3_no_publish": readiness_pass,
        "failure_reasons": []
        if readiness_pass
        else [
            reason
            for reason, failed in [
                ("target_asof_mismatch", row.get("exact_target_match") is not True),
                ("validator_status_not_pass", row.get("validator_status") != "pass"),
                ("production_allowed_not_false", row.get("production_allowed") is not False),
                ("not_published_latest_not_true", row.get("not_published_latest") is not True),
                ("forbidden_actions_all_false_missing", row.get("forbidden_actions_all_false") is not True),
            ]
            if failed
        ],
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    created_at = utc_now()
    dapr0_summary = read_json(DAPR0_DIR / "inventory_summary.json")
    pointer_inventory = read_json(DAPR0_DIR / "source_pointer_inventory.json")
    dapr2_decision = read_json(DAPR_ROOT / "dapr2_isolated_bridge_candidate_or_blocker/candidate_or_blocker_decision.json")
    target_asof = args.target_asof or str(dapr0_summary.get("target_asof") or dapr2_decision.get("target_asof") or "")

    sources = source_entries(pointer_inventory)
    raw_daily = sources.get("finmind_raw_daily_price", {}) if isinstance(sources.get("finmind_raw_daily_price"), dict) else {}
    formal = pointer_inventory.get("formal_provider") if isinstance(pointer_inventory.get("formal_provider"), dict) else {}
    formal_calendar = formal.get("calendar") if isinstance(formal.get("calendar"), dict) else {}
    formal_covers = bool(formal.get("covers_target_asof"))
    raw_covers = bool(
        str(raw_daily.get("source_max_date") or "") >= target_asof
        and int(raw_daily.get("symbol_count") or 0) >= 150
        and int(raw_daily.get("row_count") or 0) > 0
    )

    discovered = discover_readiness_artifacts(target_asof)
    provider_validations = [validate_local_artifact(row) for row in discovered if row["kind"] == "provider_candidate"]
    bridge_validations = [validate_local_artifact(row) for row in discovered if row["kind"] == "canonical_bridge"]
    ready_provider = [row for row in provider_validations if row["readiness_accepted_for_dapr3_no_publish"]]
    ready_bridge = [row for row in bridge_validations if row["readiness_accepted_for_dapr3_no_publish"]]
    ready = bool(ready_provider or ready_bridge or formal_covers)

    blocker_reasons: list[str] = []
    if not formal_covers:
        blocker_reasons.append("formal qlib provider calendar does not cover exact target_asof")
    if not ready_provider:
        blocker_reasons.append("no exact-target validated provider_candidate_readiness exists locally")
    if not ready_bridge:
        blocker_reasons.append("no exact-target validated canonical_bridge_readiness exists locally")
    if raw_covers and not ready:
        blocker_reasons.append("FinMind raw covers target_asof but raw alone is not Model A canonical bridge readiness")
    if not raw_covers:
        blocker_reasons.append("local raw evidence does not satisfy source coverage gate")

    forbidden_action_audit = {
        "schema_version": "dapr.forbidden_action_audit.v1",
        "created_at": created_at,
        "route": "DAPR3_EXACT_TARGET_PROVIDER_BRIDGE_CANDIDATE_OR_BLOCKER",
        "all_false": all(value is False for value in FORBIDDEN_ACTIONS.values()),
        "actions": FORBIDDEN_ACTIONS,
        "write_scope": [rel(OUT_DIR)],
        "provider_pull_allowed": False,
        "provider_pull_attempted": False,
    }

    local_inventory = {
        "schema_version": "dapr3.exact_target_local_evidence_inventory.v1",
        "created_at": created_at,
        "target_asof": target_asof,
        "dapr0_summary": rel(DAPR0_DIR / "inventory_summary.json"),
        "dapr1_contract": rel(DAPR1_DIR / "bridge_contract.json"),
        "dapr2_decision": rel(DAPR_ROOT / "dapr2_isolated_bridge_candidate_or_blocker/candidate_or_blocker_decision.json"),
        "formal_provider": {
            "calendar_max": str(formal_calendar.get("date_max") or ""),
            "covers_target_asof": formal_covers,
            "calendar_path": str(formal_calendar.get("path") or ""),
        },
        "finmind_raw_daily_price": {
            "covers_target_asof": raw_covers,
            "source_max_date": str(raw_daily.get("source_max_date") or ""),
            "symbol_count": raw_daily.get("symbol_count"),
            "row_count": raw_daily.get("row_count"),
            "evidence_path": str(raw_daily.get("evidence_path") or ""),
            "checksum": str(raw_daily.get("checksum") or ""),
        },
        "readiness_artifacts_found": discovered,
        "exact_target_provider_candidate_count": len([row for row in discovered if row["kind"] == "provider_candidate" and row["exact_target_match"]]),
        "exact_target_canonical_bridge_count": len([row for row in discovered if row["kind"] == "canonical_bridge" and row["exact_target_match"]]),
    }

    provider_validation_payload = {
        "schema_version": "dapr3.provider_candidate_readiness_validation_or_absent.v1",
        "created_at": created_at,
        "target_asof": target_asof,
        "status": "pass" if ready_provider else "absent_or_rejected",
        "accepted_provider_candidate_paths": [row["path"] for row in ready_provider],
        "validations": provider_validations,
    }
    bridge_validation_payload = {
        "schema_version": "dapr3.canonical_bridge_readiness_validation_or_absent.v1",
        "created_at": created_at,
        "target_asof": target_asof,
        "status": "pass" if ready_bridge else "absent_or_rejected",
        "accepted_canonical_bridge_paths": [row["path"] for row in ready_bridge],
        "validations": bridge_validations,
    }

    decision = {
        "schema_version": "dapr3.exact_target_candidate_or_blocker_decision.v1",
        "created_at": created_at,
        "target_asof": target_asof,
        "decision": "EXACT_TARGET_PROVIDER_OR_BRIDGE_READY_NO_PUBLISH" if ready else "BLOCKED_NO_EXACT_TARGET_PROVIDER_OR_BRIDGE",
        "ready_for_model_a_no_publish_dry_run": ready,
        "ready_for_provider_publish": False,
        "ready_for_latest_switch": False,
        "formal_provider_covers_target": formal_covers,
        "provider_candidate_ready": bool(ready_provider),
        "canonical_bridge_ready": bool(ready_bridge),
        "raw_daily_price_covers_target": raw_covers,
        "blocker_reasons": [] if ready else blocker_reasons,
        "next_required_action": "run Model A no-publish dry-run against exact-target isolated input"
        if ready
        else "obtain exact-target validated provider candidate or canonical bridge; live provider pull or bridge build requires separate explicit authorization",
        "forbidden_actions_all_false": forbidden_action_audit["all_false"],
    }

    paths = [
        write_json("local_exact_target_evidence_inventory.json", local_inventory),
        write_json("provider_candidate_readiness_validation_or_absent.json", provider_validation_payload),
        write_json("canonical_bridge_readiness_validation_or_absent.json", bridge_validation_payload),
        write_json("candidate_or_blocker_decision.json", decision),
        write_json("forbidden_action_audit.json", forbidden_action_audit),
    ]
    if ready_provider:
        paths.append(write_json("provider_candidate_readiness_selected.json", ready_provider[0]))
    if ready_bridge:
        paths.append(write_json("canonical_bridge_readiness_selected.json", ready_bridge[0]))
    paths.append(
        write_json(
            "exact_target_provider_bridge_blocker.json",
            {
                "schema_version": "dapr3.exact_target_provider_bridge_blocker.v1",
                "created_at": created_at,
                "target_asof": target_asof,
                "status": "not_blocked_superseded" if ready else "blocked",
                "blocker": "" if ready else "BLOCKED_NO_EXACT_TARGET_PROVIDER_OR_BRIDGE",
                "blocker_reasons": [] if ready else blocker_reasons,
                "raw_ready": raw_covers,
                "formal_calendar_max": str(formal_calendar.get("date_max") or ""),
                "exact_target_provider_candidate_exists": bool(ready_provider),
                "exact_target_canonical_bridge_exists": bool(ready_bridge),
                "selected_provider_candidate_path": ready_provider[0]["path"] if ready_provider else "",
                "selected_canonical_bridge_path": ready_bridge[0]["path"] if ready_bridge else "",
                "provider_pull_allowed": False,
                "provider_pull_attempted": False,
                "production_allowed": False,
                "not_published_latest": True,
            },
        )
    )
    manifest_path = write_json("artifact_manifest.json", build_manifest(paths))
    return {
        "status": "pass",
        "decision": decision["decision"],
        "target_asof": target_asof,
        "output_dir": rel(OUT_DIR),
        "manifest": rel(manifest_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build DAPR3 exact-target provider/bridge candidate-or-blocker evidence.")
    parser.add_argument("--target-asof", default="", help="Defaults to DAPR0 target_asof.")
    args = parser.parse_args()
    print(json.dumps(build(args), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
