#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data_tw/experiments/daily_accepted_production_readiness/dapr0_inventory"
OPS_ROOT = ROOT / "data_tw/ops/daily_auto_update"
FORMAL_CALENDAR = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt"
FORMAL_INSTRUMENTS = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt"
ACCEPTED_LATEST = ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json"
LEGACY_LATEST = ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json"
READONLY_LATEST = ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json"
AGENT_LATEST = ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json"
PBPR2A_AC = ROOT / "data_tw/experiments/provider_bridge_productionization/pbpr2a_ac_provider_candidate_readiness_review/provider_candidate_readiness_accepted.json"

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


def file_summary(path: Path) -> dict[str, Any]:
    return {
        "path": rel(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() and path.is_file() else None,
        "sha256": sha256(path),
    }


def read_calendar_max(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": rel(path), "exists": False, "date_min": "", "date_max": "", "row_count": 0, "sha256": ""}
    rows = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {
        "path": rel(path),
        "exists": True,
        "date_min": rows[0] if rows else "",
        "date_max": rows[-1] if rows else "",
        "row_count": len(rows),
        "sha256": sha256(path),
    }


def job_dirs_by_mtime_desc() -> list[Path]:
    jobs = [p.parent for p in OPS_ROOT.glob("daily_tw_stock_auto_update_*/job.json") if p.is_file()]
    if not jobs:
        return []
    return sorted(jobs, key=lambda p: (p / "job.json").stat().st_mtime, reverse=True)


def latest_raw_ready_job_dir() -> Path | None:
    for job_dir in job_dirs_by_mtime_desc():
        chain = read_json(job_dir / "daily_chain_status.json")
        if chain.get("raw_status") == "READY" or chain.get("state") == "RAW_READY_PROVIDER_STALE":
            return job_dir
    jobs = job_dirs_by_mtime_desc()
    return jobs[0] if jobs else None


def latest_pointer(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    return {
        "path": rel(path),
        "exists": path.exists(),
        "asof": str(payload.get("asof") or payload.get("target_asof") or ""),
        "status": str(payload.get("status") or ""),
        "run_id": str(payload.get("run_id") or payload.get("run_dir") or ""),
        "sha256": sha256(path),
    }


def build_manifest(paths: list[Path]) -> dict[str, Any]:
    entries = [file_summary(path) for path in paths]
    return {
        "schema_version": "dapr.artifact_manifest.v1",
        "created_at": utc_now(),
        "status": "pass" if all(entry["exists"] for entry in entries if "forbidden_action_audit" not in entry["path"]) else "pass_with_missing_optional",
        "entries": entries,
    }


def main() -> int:
    created_at = utc_now()
    latest_observation_dir = job_dirs_by_mtime_desc()[0] if job_dirs_by_mtime_desc() else None
    target_job_dir = latest_raw_ready_job_dir()
    latest_observation_job = read_json(latest_observation_dir / "job.json") if latest_observation_dir else {}
    latest_observation_chain = read_json(latest_observation_dir / "daily_chain_status.json") if latest_observation_dir else {}
    job = read_json(target_job_dir / "job.json") if target_job_dir else {}
    chain = read_json(target_job_dir / "daily_chain_status.json") if target_job_dir else {}
    ledger = read_json(target_job_dir / "skipped_asof_ledger.json") if target_job_dir else {}
    source_inventory = read_json(target_job_dir / "daily_source_inventory.json") if target_job_dir else {}
    pbpr2a_ac = read_json(PBPR2A_AC)

    target_asof = str(job.get("asof") or chain.get("asof") or ledger.get("asof") or "")
    formal_calendar = read_calendar_max(FORMAL_CALENDAR)
    formal_instruments = file_summary(FORMAL_INSTRUMENTS)
    accepted_latest = latest_pointer(ACCEPTED_LATEST)

    source_pointer_inventory = {
        "schema_version": "dapr0.source_pointer_inventory.v1",
        "created_at": created_at,
        "target_asof": target_asof,
        "latest_daily_job": {
            "job_dir": rel(latest_observation_dir) if latest_observation_dir else "",
            "job_id": str(latest_observation_job.get("job_id") or ""),
            "status": str(latest_observation_job.get("status") or ""),
            "asof": str(latest_observation_job.get("asof") or latest_observation_chain.get("asof") or ""),
            "state": str(latest_observation_chain.get("state") or ""),
            "raw_status": str(latest_observation_chain.get("raw_status") or ""),
            "job_json": rel(latest_observation_dir / "job.json") if latest_observation_dir else "",
            "daily_chain_status": rel(latest_observation_dir / "daily_chain_status.json") if latest_observation_dir else "",
            "skipped_asof_ledger": rel(latest_observation_dir / "skipped_asof_ledger.json") if latest_observation_dir else "",
        },
        "readiness_target_job": {
            "selection_policy": "latest job with raw_status READY or state RAW_READY_PROVIDER_STALE; this avoids treating weekend/non-trading observations as the bridge target",
            "job_dir": rel(target_job_dir) if target_job_dir else "",
            "job_id": str(job.get("job_id") or ""),
            "status": str(job.get("status") or ""),
            "asof": target_asof,
            "state": str(chain.get("state") or ""),
            "raw_status": str(chain.get("raw_status") or ""),
            "job_json": rel(target_job_dir / "job.json") if target_job_dir else "",
            "daily_chain_status": rel(target_job_dir / "daily_chain_status.json") if target_job_dir else "",
            "skipped_asof_ledger": rel(target_job_dir / "skipped_asof_ledger.json") if target_job_dir else "",
        },
        "formal_provider": {
            "calendar": formal_calendar,
            "instruments": formal_instruments,
            "covers_target_asof": bool(formal_calendar.get("date_max") and formal_calendar["date_max"] >= target_asof),
        },
        "latest_pointers": {
            "qlib_accepted_latest": accepted_latest,
            "legacy_latest": latest_pointer(LEGACY_LATEST),
            "readonly_snapshot_latest": latest_pointer(READONLY_LATEST),
            "agent_prompt_latest": latest_pointer(AGENT_LATEST),
        },
        "daily_source_inventory": source_inventory,
    }

    current_blocker = {
        "schema_version": "dapr0.current_blocker.v1",
        "created_at": created_at,
        "target_asof": target_asof,
        "state": str(chain.get("state") or ledger.get("state") or ""),
        "provider_bridge_readiness_state": str(chain.get("provider_bridge_readiness_state") or ledger.get("provider_bridge_readiness_state") or ""),
        "blocked_at": str(chain.get("blocked_at") or ""),
        "blocker_reason": str(chain.get("blocker_reason") or ""),
        "refined_blocker": chain.get("refined_blocker") or ledger.get("refined_blocker") or {},
        "raw_status": str(chain.get("raw_status") or ""),
        "qlib_provider_view_status": str(chain.get("qlib_provider_view_status") or ""),
        "model_a_score_status": str(chain.get("model_a_score_status") or ""),
        "skipped_asof_ledger_row_count": ledger.get("row_count"),
        "next_required_action": ((ledger.get("ledger_rows") or [{}])[0] if isinstance(ledger.get("ledger_rows"), list) and ledger.get("ledger_rows") else {}).get("next_required_action", ""),
    }

    pbpr_reuse_assessment = {
        "schema_version": "dapr0.pbpr_reuse_assessment.v1",
        "created_at": created_at,
        "target_asof": target_asof,
        "pbpr2a_ac_path": rel(PBPR2A_AC),
        "pbpr2a_ac_exists": PBPR2A_AC.exists(),
        "pbpr2a_ac_candidate_asof": str(pbpr2a_ac.get("candidate_asof") or ""),
        "pbpr2a_ac_target_asof": str(pbpr2a_ac.get("target_asof") or ""),
        "pbpr2a_ac_validator_status": str(pbpr2a_ac.get("validator_status") or ""),
        "pbpr2a_ac_scope": str(pbpr2a_ac.get("artifact_scope") or ""),
        "pbpr2a_ac_not_final_production_readiness": bool(pbpr2a_ac.get("not_final_production_readiness")),
        "reusable_for_current_target_asof": bool(pbpr2a_ac.get("target_asof") == target_asof and pbpr2a_ac.get("validator_status") == "pass"),
        "reuse_boundary": "PBPR2A-AC can be evidence only for the exact same target_asof and remains non-production/non-latest unless a later explicit gate authorizes promotion.",
    }

    forbidden_action_audit = {
        "schema_version": "dapr.forbidden_action_audit.v1",
        "created_at": created_at,
        "route": "DAPR0",
        "all_false": all(value is False for value in FORBIDDEN_ACTIONS.values()),
        "actions": FORBIDDEN_ACTIONS,
        "write_scope": [rel(OUT_DIR)],
    }

    paths = [
        write_json("source_pointer_inventory.json", source_pointer_inventory),
        write_json("current_blocker.json", current_blocker),
        write_json("pbpr_reuse_assessment.json", pbpr_reuse_assessment),
        write_json("forbidden_action_audit.json", forbidden_action_audit),
    ]
    summary = {
        "schema_version": "dapr0.inventory_summary.v1",
        "created_at": created_at,
        "target_asof": target_asof,
        "latest_observation_asof": source_pointer_inventory["latest_daily_job"]["asof"],
        "latest_observation_state": source_pointer_inventory["latest_daily_job"]["state"],
        "target_job_status": source_pointer_inventory["readiness_target_job"]["status"],
        "raw_status": current_blocker["raw_status"],
        "formal_calendar_max": formal_calendar.get("date_max", ""),
        "accepted_latest_asof": accepted_latest["asof"],
        "provider_bridge_readiness_state": current_blocker["provider_bridge_readiness_state"],
        "pbpr2a_ac_reusable_for_current_target_asof": pbpr_reuse_assessment["reusable_for_current_target_asof"],
        "next_route_state": "DAPR1_CONTRACT_READY_FOR_BUILD",
        "no_publish_boundary_intact": forbidden_action_audit["all_false"],
    }
    paths.append(write_json("inventory_summary.json", summary))
    manifest_path = write_json("artifact_manifest.json", build_manifest(paths))
    print(json.dumps({"status": "pass", "target_asof": target_asof, "output_dir": rel(OUT_DIR), "manifest": rel(manifest_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
