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
DAPR3_DIR = DAPR_ROOT / "dapr3_exact_target_provider_bridge_candidate_or_blocker"
OUT_DIR = DAPR_ROOT / "dapr4_local_file_canonical_bridge_feasibility"
EXPECTED_TARGET_ASOF = "2026-07-17"

REQUIRED_COLUMNS = {
    "symbol",
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "vwap",
    "factor",
}
FORBIDDEN_COLUMNS = {
    "future_return",
    "label",
    "order",
    "target_position",
    "target_weight",
    "quantity",
    "shares",
    "side",
    "action",
    "buy",
    "sell",
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
    "database_read_or_write_triggered": False,
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
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_bridge_roots() -> list[Path]:
    if not (ROOT / "data_tw").exists():
        return []
    roots: list[Path] = []
    for path in (ROOT / "data_tw").rglob("stock_price_bridge"):
        if path.is_dir():
            roots.append(path)
    return sorted(roots)


def audit_csv_file(path: Path, target_asof: str) -> dict[str, Any]:
    columns: list[str] = []
    missing_columns: list[str] = []
    forbidden_columns: list[str] = []
    date_min = ""
    date_max = ""
    has_target_asof = False
    symbols: set[str] = set()
    row_count = 0
    parse_error = ""

    try:
        with path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            columns = list(reader.fieldnames or [])
            column_set = set(columns)
            missing_columns = sorted(REQUIRED_COLUMNS - column_set)
            forbidden_columns = sorted(FORBIDDEN_COLUMNS & column_set)
            for row in reader:
                row_count += 1
                symbol = str(row.get("symbol") or "").strip()
                date = str(row.get("date") or "").strip()
                if symbol:
                    symbols.add(symbol)
                if date:
                    date_min = date if not date_min else min(date_min, date)
                    date_max = date if not date_max else max(date_max, date)
                    if date == target_asof:
                        has_target_asof = True
    except Exception as exc:  # pragma: no cover - evidence script should record bad files.
        parse_error = f"{type(exc).__name__}: {exc}"

    return {
        "path": rel(path),
        "columns": columns,
        "missing_columns": missing_columns,
        "forbidden_columns": forbidden_columns,
        "row_count": row_count,
        "date_min": date_min,
        "date_max": date_max,
        "has_target_asof": has_target_asof,
        "symbols": sorted(symbols),
        "parse_error": parse_error,
    }


def audit_bridge_root(root: Path, target_asof: str) -> dict[str, Any]:
    files = sorted(root.glob("TW*.csv"))
    missing_column_samples: list[dict[str, Any]] = []
    forbidden_column_samples: list[dict[str, Any]] = []
    parse_error_samples: list[dict[str, Any]] = []
    symbols: set[str] = set()
    symbols_with_target: set[str] = set()
    files_with_target = 0
    rows_total = 0
    date_min = ""
    date_max = ""
    required_columns_ok = True
    forbidden_columns_absent = True

    for file_path in files:
        audit = audit_csv_file(file_path, target_asof)
        rows_total += int(audit["row_count"])
        if audit["date_min"]:
            date_min = audit["date_min"] if not date_min else min(date_min, audit["date_min"])
        if audit["date_max"]:
            date_max = audit["date_max"] if not date_max else max(date_max, audit["date_max"])
        for symbol in audit["symbols"]:
            symbols.add(symbol)
            if audit["has_target_asof"]:
                symbols_with_target.add(symbol)
        if audit["has_target_asof"]:
            files_with_target += 1
        if audit["missing_columns"]:
            required_columns_ok = False
            if len(missing_column_samples) < 10:
                missing_column_samples.append(
                    {"path": audit["path"], "missing_columns": audit["missing_columns"]}
                )
        if audit["forbidden_columns"]:
            forbidden_columns_absent = False
            if len(forbidden_column_samples) < 10:
                forbidden_column_samples.append(
                    {"path": audit["path"], "forbidden_columns": audit["forbidden_columns"]}
                )
        if audit["parse_error"] and len(parse_error_samples) < 10:
            parse_error_samples.append({"path": audit["path"], "parse_error": audit["parse_error"]})

    feasible = (
        len(files) >= 150
        and len(symbols_with_target) >= 150
        and required_columns_ok
        and forbidden_columns_absent
        and not parse_error_samples
    )
    return {
        "path": rel(root),
        "file_count": len(files),
        "symbol_count": len(symbols),
        "symbols_sample": sorted(symbols)[:20],
        "row_count": rows_total,
        "date_min": date_min,
        "date_max": date_max,
        "files_with_target_asof": files_with_target,
        "symbols_with_target_asof": len(symbols_with_target),
        "symbols_with_target_asof_sample": sorted(symbols_with_target)[:20],
        "required_columns": sorted(REQUIRED_COLUMNS),
        "required_columns_ok": required_columns_ok,
        "missing_columns_samples": missing_column_samples,
        "forbidden_columns": sorted(FORBIDDEN_COLUMNS),
        "forbidden_columns_absent": forbidden_columns_absent,
        "forbidden_columns_samples": forbidden_column_samples,
        "parse_error_samples": parse_error_samples,
        "local_file_bridge_feasible": feasible,
        "failure_reasons": []
        if feasible
        else [
            reason
            for reason, failed in [
                ("file_count_below_150", len(files) < 150),
                ("symbols_with_target_asof_below_150", len(symbols_with_target) < 150),
                ("required_columns_not_ok", not required_columns_ok),
                ("forbidden_columns_present", not forbidden_columns_absent),
                ("parse_errors_present", bool(parse_error_samples)),
            ]
            if failed
        ],
    }


def build() -> dict[str, Any]:
    created_at = utc_now()
    dapr3_decision_path = DAPR3_DIR / "candidate_or_blocker_decision.json"
    dapr3_decision = read_json(DAPR3_DIR / "candidate_or_blocker_decision.json")
    inherited_target_asof = str(dapr3_decision.get("target_asof") or "")
    fallback_used = not bool(inherited_target_asof)
    if fallback_used:
        target_asof = EXPECTED_TARGET_ASOF
    else:
        target_asof = inherited_target_asof
    inherited_dapr3_decision = str(dapr3_decision.get("decision") or "")
    inherited_source_exists = dapr3_decision_path.exists()
    inherited_target_valid = bool(inherited_target_asof)

    roots = discover_bridge_roots()
    root_audits = [audit_bridge_root(root, target_asof) for root in roots]
    feasible_roots = [row for row in root_audits if row["local_file_bridge_feasible"]]
    decision = "BLOCKED_DAPR3_TARGET_ASOF_ABSENT_OR_MALFORMED"
    if not inherited_target_valid:
        feasible_roots = []
    elif feasible_roots:
        decision = "LOCAL_FILE_BRIDGE_FEASIBLE_WITH_ADDITIONAL_LINEAGE_REVIEW_REQUIRED"
    else:
        decision = "BLOCKED_NO_LOCAL_FILE_CANONICAL_BRIDGE_FOR_TARGET_ASOF"
    blocked = not feasible_roots

    inventory = {
        "schema_version": "dapr4.local_bridge_root_inventory.v1",
        "created_at": created_at,
        "target_asof": target_asof,
        "search_root": "data_tw",
        "bridge_root_count": len(roots),
        "bridge_roots": [rel(root) for root in roots],
        "inherited_dapr3_decision_path": rel(dapr3_decision_path),
        "inherited_dapr3_source_exists": inherited_source_exists,
        "inherited_dapr3_decision": inherited_dapr3_decision,
        "inherited_dapr3_target_asof": inherited_target_asof,
        "inherited_dapr3_target_valid": inherited_target_valid,
        "inherited_dapr3_target_fallback_used": fallback_used,
    }
    candidate_audit = {
        "schema_version": "dapr4.candidate_bridge_root_audit.v1",
        "created_at": created_at,
        "target_asof": target_asof,
        "required_columns": sorted(REQUIRED_COLUMNS),
        "forbidden_columns": sorted(FORBIDDEN_COLUMNS),
        "roots": root_audits,
    }
    decision_payload = {
        "schema_version": "dapr4.canonical_bridge_build_feasibility_decision.v1",
        "created_at": created_at,
        "target_asof": target_asof,
        "decision": decision,
        "ready_for_latest_switch": False,
        "ready_for_provider_publish": False,
        "ready_for_model_a_no_publish_dry_run": False,
        "local_file_bridge_feasible": bool(feasible_roots),
        "feasible_bridge_roots": [row["path"] for row in feasible_roots],
        "inherited_dapr3_decision": inherited_dapr3_decision,
        "inherited_dapr3_target_asof": inherited_target_asof,
        "inherited_dapr3_target_valid": inherited_target_valid,
        "inherited_dapr3_target_fallback_used": fallback_used,
        "inherited_dapr3_blocker_preserved": inherited_dapr3_decision.startswith("BLOCKED_"),
        "next_required_action": (
            "perform additional lineage/model compatibility review before any scoring or latest action"
            if feasible_roots
            else "repair DAPR3 target_asof evidence before continuing"
            if not inherited_target_valid
            else "authorize a readonly DB-backed exact-target export route or a controlled provider bridge build route"
        ),
        "forbidden_actions_all_false": all(value is False for value in FORBIDDEN_ACTIONS.values()),
    }
    forbidden_action_audit = {
        "schema_version": "dapr.forbidden_action_audit.v1",
        "created_at": created_at,
        "route": "DAPR4_LOCAL_FILE_CANONICAL_BRIDGE_FEASIBILITY",
        "all_false": all(value is False for value in FORBIDDEN_ACTIONS.values()),
        "actions": FORBIDDEN_ACTIONS,
        "write_scope": [rel(OUT_DIR)],
        "provider_pull_allowed": False,
        "provider_pull_attempted": False,
        "database_access_allowed": False,
        "database_access_attempted": False,
    }

    paths = [
        write_json("local_bridge_root_inventory.json", inventory),
        write_json("candidate_bridge_root_audit.json", candidate_audit),
        write_json("canonical_bridge_build_feasibility_decision.json", decision_payload),
        write_json("forbidden_action_audit.json", forbidden_action_audit),
    ]
    if blocked:
        blocker = {
            "schema_version": "dapr4.canonical_bridge_build_blocker.v1",
            "created_at": created_at,
            "target_asof": target_asof,
            "decision": decision,
            "blocker_reasons": [
                *(
                    ["DAPR3 decision target_asof is absent or malformed; DAPR4 used fail-closed blocker"]
                    if not inherited_target_valid
                    else []
                ),
                "no local stock_price_bridge root contains at least 150 symbols with target_asof",
                "existing local bridge roots are historical/stale for the exact target_asof",
                "DAPR3 exact-target provider/bridge readiness remains blocked",
            ],
            "next_allowed_without_new_authorization": "documentation/review only",
            "next_requires_explicit_authorization": [
                "readonly DB-backed exact-target OHLCV export to an isolated bridge candidate",
                "controlled provider bridge build",
                "live provider pull",
                "Model A no-publish scoring",
                "accepted latest switch",
            ],
        }
        paths.append(write_json("canonical_bridge_build_blocker.json", blocker))

    manifest_payload = {
        "schema_version": "dapr.artifact_manifest.v1",
        "created_at": utc_now(),
        "status": "pass",
        "artifact_manifest_status": "written",
        "route_decision": decision,
        "route_verdict": "PASS_WITH_BLOCKER" if blocked else "FEASIBILITY_CANDIDATE_ONLY",
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
    paths.append(write_json("artifact_manifest.json", manifest_payload))
    return decision_payload


def main() -> None:
    result = build()
    print(
        "DAPR4 local file canonical bridge feasibility: "
        f"decision={result['decision']} target_asof={result['target_asof']}"
    )


if __name__ == "__main__":
    main()
