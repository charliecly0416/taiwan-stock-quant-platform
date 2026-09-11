#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DAPR_ROOT = ROOT / "data_tw/experiments/daily_accepted_production_readiness"
DAPR0_DIR = DAPR_ROOT / "dapr0_inventory"
OUT_DIR = DAPR_ROOT / "dapr1_canonical_bridge_contract"

FORBIDDEN_ACTIONS = {
    "provider_pull_triggered": False,
    "provider_publish_triggered": False,
    "formal_provider_or_calendar_mutated": False,
    "accepted_latest_switch_triggered": False,
    "qlib_refresh_triggered": False,
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
    payload = json.loads(path.read_text(encoding="utf-8"))
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


def main() -> int:
    created_at = utc_now()
    inventory = read_json(DAPR0_DIR / "inventory_summary.json")
    target_asof = str(inventory.get("target_asof") or "")

    bridge_contract = {
        "schema_version": "dapr1.daily_accepted_production_readiness_contract.v1",
        "created_at": created_at,
        "target_asof_from_dapr0": target_asof,
        "purpose": "Define the exact no-publish input contract required before daily auto can advance from raw-ready to Model A score/latest readiness.",
        "accepted_input_types": [
            {
                "type": "formal_qlib_provider_calendar_covers_target_asof",
                "required": ["calendar_max >= target_asof", "instrument_count == 150", "formal provider checksum recorded"],
                "publish_status": "already_formal_readonly_evidence_only",
            },
            {
                "type": "validated_same_lineage_yahoo_scrapling_provider_candidate",
                "required": ["candidate_asof == target_asof", "symbols_success == 150", "symbols_with_asof == 150", "validator_status == pass", "post-finalization checksum manifest pass"],
                "publish_status": "isolated_candidate_only_until_explicit_publish_gate",
            },
            {
                "type": "validated_canonical_same_lineage_local_immutable_bridge",
                "required": ["bridge_asof == target_asof", "full history through target_asof for all 150 instruments", "Model A feature compatibility true", "checksums immutable", "forbidden_actions.all_false"],
                "publish_status": "isolated_bridge_only_until explicit publish/latest gate",
            },
        ],
        "not_accepted_as_modela_ready_inputs": [
            "FinMind raw evidence alone",
            "old PBPR2A-AC candidate when candidate_asof != target_asof",
            "mixed provider fill without explicit compatibility validation",
            "prior-asof cached files used as target-asof fill",
            "any artifact that required provider publish, qlib refresh, accepted latest switch, readonly latest publish, Agent prompt publish, OpenAI, monitor, broker/order, or target output in this route",
        ],
        "state_transition": {
            "from": "RAW_READY_PROVIDER_STALE",
            "to_if_ready": "PROVIDER_OR_BRIDGE_READY_MODEL_INPUT_PENDING",
            "to_if_blocked": "BLOCKED_NEEDS_TARGET_ASOF_PROVIDER_OR_BRIDGE",
        },
        "no_publish_boundary": FORBIDDEN_ACTIONS,
    }

    canonical_bridge_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "dapr1.canonical_bridge_readiness_schema.v1",
        "title": "DAPR Canonical Bridge Readiness",
        "type": "object",
        "additionalProperties": True,
        "required": [
            "schema_version",
            "bridge_asof",
            "target_asof",
            "bridge_type",
            "source_paths",
            "lineage",
            "coverage",
            "model_compatibility",
            "checksums",
            "validator_status",
            "forbidden_actions",
            "production_allowed",
            "not_published_latest",
        ],
        "properties": {
            "schema_version": {"const": "dapr2.canonical_bridge_readiness.v1"},
            "bridge_asof": {"type": "string", "pattern": "^20[0-9]{2}-[0-9]{2}-[0-9]{2}$"},
            "target_asof": {"type": "string", "pattern": "^20[0-9]{2}-[0-9]{2}-[0-9]{2}$"},
            "bridge_type": {"enum": ["canonical_same_lineage_bridge_from_local_immutable_normalized_source"]},
            "source_paths": {
                "type": "object",
                "required": ["raw_or_normalized_source", "bridge_root", "calendar_path", "instrument_path", "feature_path"],
            },
            "lineage": {
                "type": "object",
                "required": ["source_type", "source_run_id", "source_manifest", "calendar_source", "instrument_source"],
            },
            "coverage": {
                "type": "object",
                "required": ["calendar_has_target_asof", "symbols_expected", "symbols_with_asof", "required_price_fields_present", "required_feature_fields_present"],
            },
            "model_compatibility": {
                "type": "object",
                "required": ["model_a_feature_compatible", "feature_history_policy", "no_future_columns"],
            },
            "checksums": {"type": "object", "required": ["algorithm", "entries"]},
            "validator_status": {"const": "pass"},
            "forbidden_actions": {"type": "object", "required": ["all_false"]},
            "production_allowed": {"const": False},
            "not_published_latest": {"const": True},
        },
    }

    validator_requirements = {
        "schema_version": "dapr1.validator_requirements.v1",
        "created_at": created_at,
        "target_asof_from_dapr0": target_asof,
        "hard_gates": [
            "target_asof exact match",
            "150 expected symbols and 150 symbols_with_asof",
            "calendar includes target_asof",
            "required fields: open, high, low, close, volume, vwap, factor",
            "full history available through target_asof for feature construction",
            "no forbidden columns: future_return, label, action, order, target_position, target_weight, quantity",
            "forbidden actions all false",
            "all source and output checksums recorded",
        ],
        "daily_auto_consumable_outputs": [
            "candidate_or_blocker_decision.json",
            "canonical_bridge_readiness.json when ready",
            "canonical_bridge_readiness_blocker.json when blocked",
            "forbidden_action_audit.json",
            "artifact_manifest.json",
        ],
    }

    source_selection_policy = {
        "schema_version": "dapr1.source_selection_policy.v1",
        "created_at": created_at,
        "preferred_order": [
            "formal provider/calendar already covers target_asof",
            "exact target_asof validated same-lineage Yahoo/Scrapling isolated candidate",
            "exact target_asof validated canonical same-lineage local immutable bridge",
            "blocked: raw FinMind evidence requires a separately validated bridge and model compatibility proof before Model A scoring",
        ],
        "why_finmind_raw_alone_is_not_enough": "It proves local raw freshness but does not by itself prove same-lineage adjusted OHLCV, factor/vwap compatibility, full feature history, or Model A feature-space compatibility.",
    }

    forbidden_action_audit = {
        "schema_version": "dapr.forbidden_action_audit.v1",
        "created_at": created_at,
        "route": "DAPR1",
        "all_false": all(value is False for value in FORBIDDEN_ACTIONS.values()),
        "actions": FORBIDDEN_ACTIONS,
        "write_scope": [rel(OUT_DIR)],
    }

    paths = [
        write_json("bridge_contract.json", bridge_contract),
        write_json("canonical_bridge_schema.json", canonical_bridge_schema),
        write_json("validator_requirements.json", validator_requirements),
        write_json("source_selection_policy.json", source_selection_policy),
        write_json("forbidden_action_audit.json", forbidden_action_audit),
    ]
    summary = {
        "schema_version": "dapr1.contract_summary.v1",
        "created_at": created_at,
        "target_asof_from_dapr0": target_asof,
        "status": "contract_ready",
        "next_route_state": "DAPR2_ISOLATED_CANDIDATE_OR_BLOCKER_READY",
        "no_publish_boundary_intact": forbidden_action_audit["all_false"],
    }
    paths.append(write_json("contract_summary.json", summary))
    manifest_path = write_json("artifact_manifest.json", build_manifest(paths))
    print(json.dumps({"status": "pass", "target_asof": target_asof, "output_dir": rel(OUT_DIR), "manifest": rel(manifest_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
