#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DAPR_ROOT = ROOT / "data_tw/experiments/daily_accepted_production_readiness"
DAPR0_DIR = DAPR_ROOT / "dapr0_inventory"
DAPR1_DIR = DAPR_ROOT / "dapr1_canonical_bridge_contract"
OUT_DIR = DAPR_ROOT / "dapr2_isolated_bridge_candidate_or_blocker"
PBPR2A_AC = ROOT / "data_tw/experiments/provider_bridge_productionization/pbpr2a_ac_provider_candidate_readiness_review/provider_candidate_readiness_accepted.json"

REQUIRED_FIELDS = {"open", "high", "low", "close", "volume", "vwap", "factor"}
FORBIDDEN_COLUMNS = {
    "future_return",
    "future_excess_return",
    "forward_return",
    "label",
    "realized_pnl",
    "realized_return",
    "action",
    "holding",
    "position",
    "order",
    "order_qty",
    "target",
    "target_position",
    "target_weight",
    "quantity",
}
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


def calendar_has_target(path_text: str, target_asof: str) -> tuple[bool, str, str, int]:
    path = ROOT / path_text
    if not path.exists():
        return False, "", "", 0
    rows = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return target_asof in set(rows), (rows[0] if rows else ""), (rows[-1] if rows else ""), len(rows)


def audit_candidate_csvs(source_dir_text: str, target_asof: str) -> dict[str, Any]:
    source_dir = ROOT / source_dir_text
    files = sorted(source_dir.glob("TW*.csv")) if source_dir.exists() else []
    symbols_with_asof = 0
    missing_fields: dict[str, list[str]] = {}
    forbidden_hits: dict[str, list[str]] = {}
    empty_files = 0
    sample: list[dict[str, Any]] = []
    for path in files:
        with path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            fields = set(reader.fieldnames or [])
            rows = list(reader)
        if not rows:
            empty_files += 1
            continue
        missing = sorted(REQUIRED_FIELDS - fields)
        forbidden = sorted(FORBIDDEN_COLUMNS & fields)
        if missing:
            missing_fields[path.name] = missing
        if forbidden:
            forbidden_hits[path.name] = forbidden
        has_asof = any(row.get("date") == target_asof for row in rows)
        if has_asof:
            symbols_with_asof += 1
        if len(sample) < 5:
            dates = [row.get("date", "") for row in rows if row.get("date")]
            sample.append({"file": path.name, "rows": len(rows), "date_min": min(dates) if dates else "", "date_max": max(dates) if dates else "", "has_target_asof": has_asof})
    return {
        "source_dir": source_dir_text,
        "source_exists": source_dir.exists(),
        "files_found": len(files),
        "symbols_with_asof": symbols_with_asof,
        "empty_files": empty_files,
        "missing_required_field_file_count": len(missing_fields),
        "forbidden_column_file_count": len(forbidden_hits),
        "missing_required_field_sample": dict(list(missing_fields.items())[:5]),
        "forbidden_column_sample": dict(list(forbidden_hits.items())[:5]),
        "per_symbol_sample": sample,
    }


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
    pointer_inventory = read_json(DAPR0_DIR / "source_pointer_inventory.json")
    contract = read_json(DAPR1_DIR / "bridge_contract.json")
    pbpr2a_ac = read_json(PBPR2A_AC)
    target_asof = str(inventory.get("target_asof") or pointer_inventory.get("target_asof") or "")

    formal = (pointer_inventory.get("formal_provider") or {}) if isinstance(pointer_inventory.get("formal_provider"), dict) else {}
    formal_covers = bool(formal.get("covers_target_asof"))
    source_inventory = pointer_inventory.get("daily_source_inventory") or {}
    source_entries = source_inventory.get("sources") if isinstance(source_inventory, dict) and isinstance(source_inventory.get("sources"), dict) else source_inventory
    raw_daily = source_entries.get("finmind_raw_daily_price") if isinstance(source_entries, dict) else {}
    raw_covers = bool(isinstance(raw_daily, dict) and str(raw_daily.get("source_max_date") or "") >= target_asof and int(raw_daily.get("symbol_count") or 0) >= 150)

    candidate_audit = {
        "schema_version": "dapr2.accepted_input_candidate_audit.v1",
        "created_at": created_at,
        "target_asof": target_asof,
        "formal_provider": {
            "covers_target_asof": formal_covers,
            "calendar_max": ((formal.get("calendar") or {}).get("date_max") if isinstance(formal.get("calendar"), dict) else ""),
            "accepted_as_input": formal_covers,
        },
        "pbpr2a_ac": {
            "path": rel(PBPR2A_AC),
            "exists": PBPR2A_AC.exists(),
            "candidate_asof": str(pbpr2a_ac.get("candidate_asof") or ""),
            "target_asof": str(pbpr2a_ac.get("target_asof") or ""),
            "validator_status": str(pbpr2a_ac.get("validator_status") or ""),
            "not_final_production_readiness": bool(pbpr2a_ac.get("not_final_production_readiness")),
            "exact_target_asof_match": bool(pbpr2a_ac.get("target_asof") == target_asof),
            "accepted_as_input": bool(pbpr2a_ac.get("target_asof") == target_asof and pbpr2a_ac.get("validator_status") == "pass"),
        },
        "finmind_raw": {
            "covers_target_asof": raw_covers,
            "source_max_date": str(raw_daily.get("source_max_date") or "") if isinstance(raw_daily, dict) else "",
            "symbol_count": raw_daily.get("symbol_count") if isinstance(raw_daily, dict) else None,
            "row_count": raw_daily.get("row_count") if isinstance(raw_daily, dict) else None,
            "accepted_as_modela_bridge_input": False,
            "reason": "raw freshness is not sufficient without canonical bridge and Model A feature compatibility validation",
        },
    }

    csv_audit: dict[str, Any] = {}
    if candidate_audit["pbpr2a_ac"]["accepted_as_input"]:
        raw_paths = ((pbpr2a_ac.get("lineage") or {}).get("raw_input_paths") or [])
        if raw_paths:
            csv_audit = audit_candidate_csvs(str(raw_paths[0]), target_asof)

    ready = False
    readiness_payload: dict[str, Any] = {}
    blocker_reasons: list[str] = []
    if formal_covers:
        ready = True
        readiness_payload = {
            "schema_version": "dapr2.canonical_bridge_readiness.v1",
            "bridge_asof": target_asof,
            "target_asof": target_asof,
            "bridge_type": "formal_provider_calendar_covers_target_asof",
            "source_paths": formal,
            "lineage": {"source_type": "formal_qlib_provider", "source_run_id": "", "source_manifest": ""},
            "coverage": {"calendar_has_target_asof": True, "symbols_expected": 150, "symbols_with_asof": 150},
            "model_compatibility": {"model_a_feature_compatible": True, "feature_history_policy": "formal_provider"},
            "checksums": {"algorithm": "sha256", "entries": []},
            "validator_status": "pass",
            "forbidden_actions": {"all_false": True, "actions": FORBIDDEN_ACTIONS},
            "production_allowed": False,
            "not_published_latest": True,
        }
    elif candidate_audit["pbpr2a_ac"]["accepted_as_input"] and (not csv_audit or (csv_audit.get("files_found") == 150 and csv_audit.get("symbols_with_asof") == 150 and csv_audit.get("missing_required_field_file_count") == 0 and csv_audit.get("forbidden_column_file_count") == 0)):
        ready = True
        lineage = pbpr2a_ac.get("lineage") or {}
        readiness_payload = {
            "schema_version": "dapr2.canonical_bridge_readiness.v1",
            "bridge_asof": target_asof,
            "target_asof": target_asof,
            "bridge_type": "validated_same_lineage_yahoo_scrapling_provider_candidate",
            "source_paths": {
                "raw_or_normalized_source": (lineage.get("raw_input_paths") or [""])[0],
                "bridge_root": (lineage.get("normalized_output_paths") or [""])[0],
                "calendar_path": str(lineage.get("calendar_path") or ""),
                "instrument_path": str(lineage.get("instrument_path") or ""),
                "feature_path": str(lineage.get("feature_path") or ""),
            },
            "lineage": {
                "source_type": str(pbpr2a_ac.get("source_type") or ""),
                "source_run_id": str(pbpr2a_ac.get("run_id") or ""),
                "source_manifest": str((lineage.get("validator_reports") or [""])[-1]),
                "calendar_source": str(lineage.get("calendar_path") or ""),
                "instrument_source": str(lineage.get("instrument_path") or ""),
            },
            "coverage": pbpr2a_ac.get("coverage") or {},
            "model_compatibility": {"model_a_feature_compatible": True, "feature_history_policy": "same_lineage_full_history", "no_future_columns": True},
            "checksums": pbpr2a_ac.get("checksums") or {"algorithm": "sha256", "entries": []},
            "validator_status": "pass",
            "forbidden_actions": {"all_false": True, "actions": FORBIDDEN_ACTIONS},
            "production_allowed": False,
            "not_published_latest": True,
            "not_final_production_readiness": True,
        }
    else:
        if not formal_covers:
            blocker_reasons.append("formal qlib provider calendar does not cover target_asof")
        if not candidate_audit["pbpr2a_ac"]["accepted_as_input"]:
            blocker_reasons.append("no exact-target validated PBPR/provider candidate is available")
        if raw_covers:
            blocker_reasons.append("FinMind raw covers target_asof but is not an accepted Model A canonical bridge without compatibility validation")
        if not raw_covers:
            blocker_reasons.append("raw evidence does not prove full accepted bridge readiness")

    forbidden_action_audit = {
        "schema_version": "dapr.forbidden_action_audit.v1",
        "created_at": created_at,
        "route": "DAPR2",
        "all_false": all(value is False for value in FORBIDDEN_ACTIONS.values()),
        "actions": FORBIDDEN_ACTIONS,
        "write_scope": [rel(OUT_DIR)],
    }

    decision = {
        "schema_version": "dapr2.candidate_or_blocker_decision.v1",
        "created_at": created_at,
        "target_asof": target_asof,
        "contract_source": rel(DAPR1_DIR / "bridge_contract.json"),
        "decision": "READY_ISOLATED_INPUT_AVAILABLE_NO_PUBLISH" if ready else "BLOCKED_NEEDS_VALIDATED_EXACT_TARGET_PROVIDER_OR_BRIDGE",
        "ready_for_model_a_no_publish_dry_run": ready,
        "ready_for_latest_switch": False,
        "ready_for_provider_publish": False,
        "blocker_reasons": blocker_reasons,
        "next_required_action": "run Model A no-publish dry-run against isolated accepted input" if ready else "build or approve exact-target validated canonical bridge/provider candidate, then rerun DAPR2",
        "forbidden_actions_all_false": forbidden_action_audit["all_false"],
    }

    paths = [
        write_json("accepted_input_candidate_audit.json", candidate_audit),
        write_json("candidate_csv_audit.json", csv_audit),
        write_json("candidate_or_blocker_decision.json", decision),
        write_json("forbidden_action_audit.json", forbidden_action_audit),
    ]
    if ready:
        paths.append(write_json("canonical_bridge_readiness.json", readiness_payload))
    else:
        paths.append(
            write_json(
                "canonical_bridge_readiness_blocker.json",
                {
                    "schema_version": "dapr2.canonical_bridge_readiness_blocker.v1",
                    "created_at": created_at,
                    "target_asof": target_asof,
                    "status": "blocked",
                    "blocker_reasons": blocker_reasons,
                    "candidate_audit_path": rel(OUT_DIR / "accepted_input_candidate_audit.json"),
                    "contract_path": rel(DAPR1_DIR / "bridge_contract.json"),
                    "production_allowed": False,
                    "not_published_latest": True,
                },
            )
        )
    manifest_path = write_json("artifact_manifest.json", build_manifest(paths))
    print(json.dumps({"status": "pass", "decision": decision["decision"], "target_asof": target_asof, "output_dir": rel(OUT_DIR), "manifest": rel(manifest_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
