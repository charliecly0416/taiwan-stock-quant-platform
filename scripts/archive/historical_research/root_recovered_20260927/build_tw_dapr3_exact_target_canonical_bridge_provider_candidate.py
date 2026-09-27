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
DAPR1_DIR = DAPR_ROOT / "dapr1_canonical_bridge_contract"
DAPR2_DIR = DAPR_ROOT / "dapr2_isolated_bridge_candidate_or_blocker"
OUT_DIR = DAPR_ROOT / "dapr3_exact_target_canonical_bridge_provider_candidate"

PROVIDER_ROOT = ROOT / "data_tw/experiments/provider_bridge_productionization"
ARTIFACT_ROOT = ROOT / "data_tw/artifacts"
FORMAL_CALENDAR = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt"
FORMAL_INSTRUMENTS = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt"

SCAN_ROOTS = [
    PROVIDER_ROOT,
    DAPR_ROOT,
    ARTIFACT_ROOT / "shadow_readiness",
]

READINESS_NAME_HINTS = (
    "provider_candidate_readiness",
    "canonical_bridge_readiness",
    "bridge_readiness",
    "candidate_or_blocker_decision",
    "source_readiness",
    "input_readiness",
    "manifest",
)

FORBIDDEN_ACTIONS = {
    "provider_pull_triggered": False,
    "provider_publish_triggered": False,
    "formal_provider_or_calendar_mutated": False,
    "accepted_latest_switch_triggered": False,
    "qlib_refresh_triggered": False,
    "readonly_latest_published": False,
    "agent_prompt_built_or_published": False,
    "openai_called": False,
    "monitor_triggered_or_written": False,
    "broker_order_or_quick_trade_triggered": False,
    "order_intent_or_target_generated": False,
    "target_position_weight_or_quantity_output": False,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file() or path.stat().st_size == 0:
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


def file_summary(path: Path) -> dict[str, Any]:
    return {
        "path": rel(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() and path.is_file() else None,
        "sha256": sha256(path),
    }


def is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def read_calendar(path: Path, target_asof: str) -> dict[str, Any]:
    if not path.exists():
        return {
            "path": rel(path),
            "exists": False,
            "date_min": "",
            "date_max": "",
            "row_count": 0,
            "has_target_asof": False,
            "sha256": "",
        }
    rows = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {
        "path": rel(path),
        "exists": True,
        "date_min": rows[0] if rows else "",
        "date_max": rows[-1] if rows else "",
        "row_count": len(rows),
        "has_target_asof": target_asof in set(rows),
        "sha256": sha256(path),
    }


def count_instruments(path: Path) -> int:
    if not path.exists():
        return 0
    return len([line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()])


def nested_get(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def first_text(payload: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def status_pass(payload: dict[str, Any]) -> bool:
    values = [
        payload.get("validator_status"),
        payload.get("status"),
        payload.get("artifact_status"),
        nested_get(payload, "validator", "status"),
        nested_get(payload, "validation", "status"),
        nested_get(payload, "validation", "ok"),
    ]
    pass_values = {"pass", "passed", "ready", "ok", "true", "accepted_pbpr2_controlled_ac_root_only", "pass_provider_candidate_readiness_accepted_for_pbpr3_workdoc_only"}
    for value in values:
        if isinstance(value, bool) and value:
            return True
        if isinstance(value, str) and value.strip().lower() in pass_values:
            return True
    return False


def coverage_summary(payload: dict[str, Any]) -> dict[str, Any]:
    coverage = payload.get("coverage") if isinstance(payload.get("coverage"), dict) else {}
    return {
        "calendar_has_target_asof": bool(coverage.get("calendar_has_target_asof")),
        "symbols_expected": coverage.get("symbols_expected"),
        "symbols_success": coverage.get("symbols_success"),
        "symbols_with_asof": coverage.get("symbols_with_asof"),
        "active_universe_count": coverage.get("active_universe_count"),
        "candidate_normalized_csv_count": coverage.get("candidate_normalized_csv_count"),
        "staged_qlib_bin_file_count": coverage.get("staged_qlib_bin_file_count"),
    }


def forbidden_summary(payload: dict[str, Any]) -> dict[str, Any]:
    direct = payload.get("forbidden_action_summary")
    if isinstance(direct, dict):
        return {
            "all_false": all(value is False for value in direct.values()),
            "source": "forbidden_action_summary",
            "actions": direct,
        }
    forbidden = payload.get("forbidden_actions")
    if isinstance(forbidden, dict):
        actions = forbidden.get("actions") if isinstance(forbidden.get("actions"), dict) else forbidden
        return {
            "all_false": bool(forbidden.get("all_false")) if "all_false" in forbidden else all(value is False for value in actions.values()),
            "source": "forbidden_actions",
            "actions": actions,
        }
    return {"all_false": None, "source": "", "actions": {}}


def candidate_type_from_path(path: Path, payload: dict[str, Any]) -> str:
    text = f"{rel(path)} {payload.get('source_type', '')} {payload.get('schema_version', '')}".lower()
    if "provider_candidate_readiness" in text or "same_lineage_yahoo" in text or "provider_candidate" in text:
        return "validated_same_lineage_yahoo_scrapling_provider_candidate"
    if "canonical_bridge_readiness" in text or "bridge_asof" in payload:
        return "validated_canonical_same_lineage_local_immutable_bridge"
    return "unknown_local_readiness_or_manifest"


def contract_fit(candidate_type: str, payload: dict[str, Any], target_asof: str) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    asof = first_text(payload, ("target_asof", "candidate_asof", "bridge_asof", "asof", "signal_asof"))
    coverage = coverage_summary(payload)
    forbidden = forbidden_summary(payload)
    validator_ok = status_pass(payload)

    if asof != target_asof:
        reasons.append(f"asof mismatch: observed={asof or '<missing>'}, target={target_asof}")
    if not validator_ok:
        reasons.append("validator/status is not pass")

    if candidate_type == "validated_same_lineage_yahoo_scrapling_provider_candidate":
        if not bool(coverage.get("calendar_has_target_asof")):
            reasons.append("coverage.calendar_has_target_asof is not true")
        if coverage.get("symbols_success") != 150:
            reasons.append("coverage.symbols_success != 150")
        if coverage.get("symbols_with_asof") != 150:
            reasons.append("coverage.symbols_with_asof != 150")
        verification = nested_get(payload, "checksums", "verification")
        if isinstance(verification, dict):
            if verification.get("missing_count") != 0 or verification.get("mismatch_count") != 0:
                reasons.append("checksum verification has missing or mismatched entries")
        else:
            reasons.append("post-finalization checksum verification is missing")

    elif candidate_type == "validated_canonical_same_lineage_local_immutable_bridge":
        bridge_asof = first_text(payload, ("bridge_asof", "target_asof", "asof"))
        if bridge_asof != target_asof:
            reasons.append(f"bridge_asof mismatch: observed={bridge_asof or '<missing>'}, target={target_asof}")
        if coverage.get("symbols_with_asof") != 150:
            reasons.append("coverage.symbols_with_asof != 150")
        model_compat = payload.get("model_compatibility") if isinstance(payload.get("model_compatibility"), dict) else {}
        if model_compat.get("model_a_feature_compatible") is not True:
            reasons.append("model_a_feature_compatible is not true")
        if forbidden.get("all_false") is not True:
            reasons.append("forbidden_actions.all_false is not true")
        checksums = payload.get("checksums") if isinstance(payload.get("checksums"), dict) else {}
        entries = checksums.get("entries")
        if not checksums or ("entries" in checksums and not isinstance(entries, list)):
            reasons.append("immutable checksum entries are missing or malformed")
    else:
        reasons.append("artifact is not a DAPR1 accepted input type")

    return len(reasons) == 0, reasons


def should_scan_json(path: Path) -> bool:
    text = rel(path).lower()
    return any(hint in text for hint in READINESS_NAME_HINTS)


def scan_local_candidates(target_asof: str) -> dict[str, Any]:
    scanned = 0
    relevant = 0
    exact_target_matches: list[dict[str, Any]] = []
    accepted_candidates: list[dict[str, Any]] = []
    near_misses: list[dict[str, Any]] = []
    older_pass_candidates: list[dict[str, Any]] = []

    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.json")):
            if is_under(path, OUT_DIR):
                continue
            if not should_scan_json(path):
                continue
            scanned += 1
            payload = read_json(path)
            if not payload:
                continue
            candidate_type = candidate_type_from_path(path, payload)
            asof = first_text(payload, ("target_asof", "candidate_asof", "bridge_asof", "asof", "signal_asof"))
            validator_ok = status_pass(payload)
            if candidate_type == "unknown_local_readiness_or_manifest" and not asof:
                continue
            relevant += 1
            accepted, reasons = contract_fit(candidate_type, payload, target_asof)
            entry = {
                "path": rel(path),
                "sha256": sha256(path),
                "candidate_type": candidate_type,
                "observed_asof": asof,
                "validator_or_status_pass": validator_ok,
                "coverage": coverage_summary(payload),
                "forbidden": forbidden_summary(payload),
                "accepted_by_dapr1_contract": accepted,
                "rejection_reasons": reasons,
            }
            if asof == target_asof:
                exact_target_matches.append(entry)
            if accepted:
                accepted_candidates.append(entry)
            elif validator_ok and asof and asof < target_asof and candidate_type != "unknown_local_readiness_or_manifest":
                older_pass_candidates.append(entry)
            elif asof == target_asof or candidate_type != "unknown_local_readiness_or_manifest":
                near_misses.append(entry)

    return {
        "scan_roots": [rel(root) for root in SCAN_ROOTS],
        "json_files_scanned": scanned,
        "relevant_json_files": relevant,
        "exact_target_match_count": len(exact_target_matches),
        "accepted_candidate_count": len(accepted_candidates),
        "exact_target_matches": exact_target_matches[:50],
        "accepted_candidates": accepted_candidates,
        "older_pass_candidate_sample": older_pass_candidates[:20],
        "near_miss_sample": near_misses[:50],
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
    dapr2_decision = read_json(DAPR2_DIR / "candidate_or_blocker_decision.json")
    contract = read_json(DAPR1_DIR / "bridge_contract.json")

    target_asof = str(inventory.get("target_asof") or pointer_inventory.get("target_asof") or "2026-07-17")
    formal_calendar = read_calendar(FORMAL_CALENDAR, target_asof)
    formal_instrument_summary = file_summary(FORMAL_INSTRUMENTS)
    formal_instrument_count = count_instruments(FORMAL_INSTRUMENTS)
    formal_ready = bool(formal_calendar["has_target_asof"] and formal_instrument_count == 150)

    source_inventory = pointer_inventory.get("daily_source_inventory") if isinstance(pointer_inventory.get("daily_source_inventory"), dict) else {}
    sources = source_inventory.get("sources") if isinstance(source_inventory.get("sources"), dict) else {}
    raw_daily = sources.get("finmind_raw_daily_price") if isinstance(sources.get("finmind_raw_daily_price"), dict) else {}
    raw_covers_target = bool(str(raw_daily.get("source_max_date") or "") >= target_asof and int(raw_daily.get("symbol_count") or 0) >= 150)

    candidate_scan = scan_local_candidates(target_asof)
    accepted_candidates = candidate_scan["accepted_candidates"]
    accepted_from_scan = accepted_candidates[0] if accepted_candidates else None

    accepted_input: dict[str, Any] | None = None
    if formal_ready:
        accepted_input = {
            "type": "formal_qlib_provider_calendar_covers_target_asof",
            "source": "formal_provider",
            "path": formal_calendar["path"],
            "coverage": {
                "calendar_has_target_asof": True,
                "calendar_max": formal_calendar["date_max"],
                "instrument_count": formal_instrument_count,
            },
        }
    elif accepted_from_scan:
        accepted_input = accepted_from_scan

    contract_mapping = {
        "schema_version": "dapr3.contract_mapping.v1",
        "created_at": created_at,
        "target_asof": target_asof,
        "contract_source": rel(DAPR1_DIR / "bridge_contract.json"),
        "accepted_input_types": contract.get("accepted_input_types", []),
        "observed_mapping": [
            {
                "type": "formal_qlib_provider_calendar_covers_target_asof",
                "status": "pass" if formal_ready else "blocked",
                "observed": {
                    "calendar_has_target_asof": formal_calendar["has_target_asof"],
                    "calendar_max": formal_calendar["date_max"],
                    "instrument_count": formal_instrument_count,
                    "calendar_sha256": formal_calendar["sha256"],
                    "instrument_sha256": formal_instrument_summary["sha256"],
                },
                "rejection_reasons": [] if formal_ready else [
                    reason for reason in [
                        "formal provider calendar does not include target_asof" if not formal_calendar["has_target_asof"] else "",
                        "formal instrument count is not 150" if formal_instrument_count != 150 else "",
                    ]
                    if reason
                ],
            },
            {
                "type": "validated_same_lineage_yahoo_scrapling_provider_candidate",
                "status": "pass" if any(c["candidate_type"] == "validated_same_lineage_yahoo_scrapling_provider_candidate" for c in accepted_candidates) else "blocked",
                "exact_target_matches": [
                    c for c in candidate_scan["exact_target_matches"]
                    if c["candidate_type"] == "validated_same_lineage_yahoo_scrapling_provider_candidate"
                ],
                "older_pass_candidate_sample": [
                    c for c in candidate_scan["older_pass_candidate_sample"]
                    if c["candidate_type"] == "validated_same_lineage_yahoo_scrapling_provider_candidate"
                ],
            },
            {
                "type": "validated_canonical_same_lineage_local_immutable_bridge",
                "status": "pass" if any(c["candidate_type"] == "validated_canonical_same_lineage_local_immutable_bridge" for c in accepted_candidates) else "blocked",
                "exact_target_matches": [
                    c for c in candidate_scan["exact_target_matches"]
                    if c["candidate_type"] == "validated_canonical_same_lineage_local_immutable_bridge"
                ],
                "near_miss_sample": [
                    c for c in candidate_scan["near_miss_sample"]
                    if c["candidate_type"] == "validated_canonical_same_lineage_local_immutable_bridge"
                ][:20],
            },
            {
                "type": "finmind_raw_daily_price",
                "status": "observed_not_accepted_input",
                "observed": {
                    "source_max_date": str(raw_daily.get("source_max_date") or ""),
                    "symbol_count": raw_daily.get("symbol_count"),
                    "row_count": raw_daily.get("row_count"),
                    "evidence_path": raw_daily.get("evidence_path"),
                    "covers_target_asof": raw_covers_target,
                },
                "rejection_reasons": [
                    "FinMind raw alone is explicitly excluded by DAPR1 because it lacks same-lineage adjusted OHLCV/factor/vwap and Model A feature compatibility validation"
                ],
            },
        ],
    }

    local_inventory = {
        "schema_version": "dapr3.local_inventory.v1",
        "created_at": created_at,
        "target_asof": target_asof,
        "source_documents": {
            "dapr0_inventory_summary": rel(DAPR0_DIR / "inventory_summary.json"),
            "dapr1_bridge_contract": rel(DAPR1_DIR / "bridge_contract.json"),
            "dapr2_decision": rel(DAPR2_DIR / "candidate_or_blocker_decision.json"),
        },
        "daily_auto_evidence": {
            "target_job": pointer_inventory.get("readiness_target_job", {}),
            "latest_daily_job": pointer_inventory.get("latest_daily_job", {}),
            "dapr2_decision": dapr2_decision.get("decision"),
            "dapr2_blocker_reasons": dapr2_decision.get("blocker_reasons", []),
        },
        "formal_provider": {
            "calendar": formal_calendar,
            "instruments": {**formal_instrument_summary, "instrument_count": formal_instrument_count},
            "accepted_by_dapr1_contract": formal_ready,
        },
        "raw_evidence": {
            "finmind_raw_daily_price": raw_daily,
            "covers_target_asof": raw_covers_target,
            "accepted_by_dapr1_contract": False,
        },
        "candidate_scan": candidate_scan,
    }

    blocker_reasons: list[str] = []
    if not accepted_input:
        if not formal_ready:
            blocker_reasons.append("formal provider calendar/instrument contract does not cover target_asof")
        if not accepted_candidates:
            blocker_reasons.append("no exact-target validated provider candidate or canonical immutable bridge was found locally")
        if raw_covers_target:
            blocker_reasons.append("FinMind raw covers target_asof but remains non-accepted without canonical bridge and Model A feature compatibility validation")

    decision = {
        "schema_version": "dapr3.candidate_or_blocker_decision.v1",
        "created_at": created_at,
        "target_asof": target_asof,
        "decision": "READY_EXACT_TARGET_CANONICAL_BRIDGE_OR_PROVIDER_CANDIDATE_NO_PUBLISH" if accepted_input else "BLOCKED_NEEDS_VALIDATED_EXACT_TARGET_PROVIDER_OR_BRIDGE",
        "candidate_available": bool(accepted_input),
        "accepted_input": accepted_input or {},
        "blocker_reasons": blocker_reasons,
        "ready_for_model_a_no_publish_dry_run": bool(accepted_input),
        "ready_for_provider_publish": False,
        "ready_for_accepted_latest_switch": False,
        "ready_for_readonly_latest_publish": False,
        "ready_for_agent_prompt": False,
        "next_required_action": "run an explicitly authorized Model A no-publish dry-run against this isolated input" if accepted_input else "create or accept an exact-target validated same-lineage provider candidate or canonical immutable bridge, then rerun DAPR3",
        "forbidden_actions_all_false": True,
    }

    forbidden_action_audit = {
        "schema_version": "dapr.forbidden_action_audit.v1",
        "created_at": created_at,
        "route": "DAPR3_EXACT_TARGET_CANONICAL_BRIDGE_PROVIDER_CANDIDATE",
        "all_false": all(value is False for value in FORBIDDEN_ACTIONS.values()),
        "actions": FORBIDDEN_ACTIONS,
        "read_only_inputs": [
            rel(DAPR0_DIR),
            rel(DAPR1_DIR),
            rel(DAPR2_DIR),
            rel(PROVIDER_ROOT),
            rel(ARTIFACT_ROOT / "shadow_readiness"),
            rel(FORMAL_CALENDAR),
            rel(FORMAL_INSTRUMENTS),
        ],
        "write_scope": [rel(OUT_DIR)],
    }

    paths = [
        write_json("local_inventory.json", local_inventory),
        write_json("contract_mapping.json", contract_mapping),
        write_json("candidate_or_blocker_decision.json", decision),
        write_json("forbidden_action_audit.json", forbidden_action_audit),
    ]
    if accepted_input:
        paths.append(write_json("exact_target_candidate.json", {
            "schema_version": "dapr3.exact_target_candidate.v1",
            "created_at": created_at,
            "target_asof": target_asof,
            "status": "candidate_available_no_publish",
            "candidate": accepted_input,
            "production_allowed": False,
            "not_published_latest": True,
        }))
    else:
        paths.append(write_json("exact_target_blocker.json", {
            "schema_version": "dapr3.exact_target_blocker.v1",
            "created_at": created_at,
            "target_asof": target_asof,
            "status": "blocked",
            "blocker_reasons": blocker_reasons,
            "local_inventory_path": rel(OUT_DIR / "local_inventory.json"),
            "contract_mapping_path": rel(OUT_DIR / "contract_mapping.json"),
            "production_allowed": False,
            "not_published_latest": True,
        }))

    manifest_path = write_json("artifact_manifest.json", build_manifest(paths))
    print(json.dumps({
        "status": "pass",
        "decision": decision["decision"],
        "target_asof": target_asof,
        "output_dir": rel(OUT_DIR),
        "manifest": rel(manifest_path),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
