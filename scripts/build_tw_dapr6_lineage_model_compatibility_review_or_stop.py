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
DAPR1_DIR = DAPR_ROOT / "dapr1_canonical_bridge_contract"
DAPR5_DIR = DAPR_ROOT / "dapr5_readonly_db_backed_exact_target_bridge_export_or_blocker"
OUT_DIR = DAPR_ROOT / "dapr6_lineage_model_compatibility_review_or_stop"

MODELA_COMMON = ROOT / "scripts/tw_modela_score_common.py"
MODELA_INPUT_BUILDER = ROOT / "scripts/build_tw_model_inference_input.py"
MODELA_SCORE_JOB = ROOT / "scripts/run_tw_model_score_job.py"
FORMAL_PROVIDER = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin"
FORMAL_NORMALIZED = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized"
DAPR5_BRIDGE = DAPR5_DIR / "stock_price_bridge"

TARGET_ASOF_FALLBACK = "2026-07-17"
MODELA_HANDLER_START = "2015-05-04"
REQUIRED_BRIDGE_COLUMNS = ["symbol", "date", "open", "high", "low", "close", "volume", "vwap", "factor"]
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
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_calendar_bounds(provider_root: Path) -> dict[str, Any]:
    path = provider_root / "calendars/day.txt"
    if not path.exists():
        return {"exists": False, "date_min": "", "date_max": "", "row_count": 0}
    rows = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {
        "exists": True,
        "path": rel(path),
        "date_min": min(rows) if rows else "",
        "date_max": max(rows) if rows else "",
        "row_count": len(rows),
        "sha256": sha256(path),
    }


def read_instruments(provider_root: Path) -> dict[str, Any]:
    path = provider_root / "instruments/all.txt"
    if not path.exists():
        return {"exists": False, "symbols": [], "symbol_count": 0}
    symbols = [
        line.split()[0].strip().upper()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return {"exists": True, "path": rel(path), "symbols": symbols, "symbol_count": len(symbols), "sha256": sha256(path)}


def provider_feature_inventory(provider_root: Path, symbols: list[str]) -> dict[str, Any]:
    required_fields = {"open", "high", "low", "close", "volume", "vwap", "factor"}
    counts = {field: 0 for field in sorted(required_fields)}
    missing_symbols: list[str] = []
    for symbol in symbols:
        feature_dir = provider_root / "features" / symbol.lower()
        if not feature_dir.exists():
            missing_symbols.append(symbol)
            continue
        fields = {path.name.split(".")[0] for path in feature_dir.glob("*.day.bin")}
        for field in required_fields:
            if field in fields:
                counts[field] += 1
    return {
        "features_dir_exists": (provider_root / "features").exists(),
        "expected_field_counts": counts,
        "missing_feature_symbols_count": len(missing_symbols),
        "missing_feature_symbols_sample": missing_symbols[:20],
        "status": "pass" if len(symbols) == 150 and all(value == 150 for value in counts.values()) else "fail",
    }


def audit_bridge_dir(path: Path, target_asof: str) -> dict[str, Any]:
    files = sorted(path.glob("TW*.csv")) if path.exists() else []
    date_min = ""
    date_max = ""
    rows_total = 0
    files_with_target = 0
    symbols: set[str] = set()
    symbols_with_target: set[str] = set()
    missing_columns_samples: list[dict[str, Any]] = []
    forbidden_columns_samples: list[dict[str, Any]] = []
    factor_values: set[str] = set()
    forbidden = {
        "future_return",
        "label",
        "action",
        "order",
        "target_position",
        "target_weight",
        "quantity",
        "shares",
        "side",
        "buy",
        "sell",
    }
    for file_path in files:
        with file_path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            columns = list(reader.fieldnames or [])
            missing = sorted(set(REQUIRED_BRIDGE_COLUMNS) - set(columns))
            forbidden_hits = sorted(forbidden & set(columns))
            symbol_has_target = False
            file_symbols: set[str] = set()
            for row in reader:
                rows_total += 1
                symbol = str(row.get("symbol") or "").strip()
                date = str(row.get("date") or "").strip()
                factor = str(row.get("factor") or "").strip()
                if symbol:
                    symbols.add(symbol)
                    file_symbols.add(symbol)
                if factor:
                    factor_values.add(factor)
                if date:
                    date_min = date if not date_min else min(date_min, date)
                    date_max = date if not date_max else max(date_max, date)
                    if date == target_asof:
                        symbol_has_target = True
            if symbol_has_target:
                files_with_target += 1
                symbols_with_target.update(file_symbols)
            if missing and len(missing_columns_samples) < 10:
                missing_columns_samples.append({"path": rel(file_path), "missing_columns": missing})
            if forbidden_hits and len(forbidden_columns_samples) < 10:
                forbidden_columns_samples.append({"path": rel(file_path), "forbidden_columns": forbidden_hits})
    return {
        "bridge_dir": rel(path),
        "exists": path.exists(),
        "file_count": len(files),
        "symbol_count": len(symbols),
        "rows_total": rows_total,
        "date_min": date_min,
        "date_max": date_max,
        "files_with_target_asof": files_with_target,
        "symbols_with_target_asof": len(symbols_with_target),
        "required_columns": REQUIRED_BRIDGE_COLUMNS,
        "missing_columns_samples": missing_columns_samples,
        "forbidden_columns_samples": forbidden_columns_samples,
        "factor_values_sample": sorted(factor_values)[:10],
        "all_factor_one": bool(factor_values) and set(factor_values) <= {"1.0", "1", "1.000000"},
    }


def build() -> dict[str, Any]:
    created_at = utc_now()
    dapr1 = read_json(DAPR1_DIR / "bridge_contract.json")
    dapr5_decision = read_json(DAPR5_DIR / "candidate_or_blocker_decision.json")
    dapr5_readiness = read_json(DAPR5_DIR / "db_backed_bridge_candidate_readiness.json")
    target_asof = str(dapr5_decision.get("target_asof") or dapr5_readiness.get("target_asof") or TARGET_ASOF_FALLBACK)

    instruments = read_instruments(FORMAL_PROVIDER)
    symbols = list(instruments.get("symbols") or [])
    formal_calendar = read_calendar_bounds(FORMAL_PROVIDER)
    formal_features = provider_feature_inventory(FORMAL_PROVIDER, symbols)
    bridge_audit = audit_bridge_dir(DAPR5_BRIDGE, target_asof)

    modela_requirements = {
        "schema_version": "dapr6.modela_runtime_requirements.v1",
        "created_at": created_at,
        "target_asof": target_asof,
        "model_id": "e4_frozen_qlib_2018_2022",
        "evidence_files": {
            "tw_modela_score_common": rel(MODELA_COMMON),
            "model_inference_input_builder": rel(MODELA_INPUT_BUILDER),
            "model_score_job": rel(MODELA_SCORE_JOB),
        },
        "contained_runtime_requires": [
            "provider_root exists",
            "provider_root/calendars/day.txt exists and calendar_max >= target_asof",
            "provider_root/features exists with open/high/low/close/volume/vwap/factor day bins for all 150 symbols",
            "normalized_root exists with 150 TW*.csv files and target_asof rows",
            "Model A qlib DatasetH Alpha158 snapshot consumes qlib provider bin features",
        ],
        "handler_start_time": MODELA_HANDLER_START,
        "formal_lineage": "yahoo_adjusted_primary_option_c",
        "formal_provider": {
            "path": rel(FORMAL_PROVIDER),
            "calendar": formal_calendar,
            "instrument_count": instruments.get("symbol_count"),
            "feature_inventory": formal_features,
        },
        "formal_normalized": {"path": rel(FORMAL_NORMALIZED), "exists": FORMAL_NORMALIZED.exists()},
    }

    compatibility_gates = [
        {
            "gate": "candidate_export_exact_target_coverage",
            "status": "pass"
            if bridge_audit["file_count"] == 150 and bridge_audit["symbols_with_target_asof"] == 150
            else "fail",
            "evidence": {
                "file_count": bridge_audit["file_count"],
                "symbols_with_target_asof": bridge_audit["symbols_with_target_asof"],
            },
        },
        {
            "gate": "candidate_can_be_used_directly_as_modela_provider_root",
            "status": "fail",
            "evidence": {
                "reason": "DAPR5 bridge is CSV normalized-style files; it lacks qlib provider calendars/instruments/features day.bin layout",
                "candidate_bridge_dir": bridge_audit["bridge_dir"],
            },
        },
        {
            "gate": "same_lineage_with_formal_model_provider",
            "status": "fail",
            "evidence": {
                "candidate_source_lineage": "finmind_unadjusted_db_archive",
                "formal_model_lineage": "yahoo_adjusted_primary_option_c",
            },
        },
        {
            "gate": "adjustment_factor_policy_compatible",
            "status": "fail",
            "evidence": {
                "candidate_factor_policy": "factor=1.0 unadjusted export",
                "all_factor_one": bridge_audit["all_factor_one"],
                "formal_lineage": "yahoo_adjusted_primary adjusted OHLCV/factor provider",
            },
        },
        {
            "gate": "full_history_through_target_asof",
            "status": "fail",
            "evidence": {
                "candidate_date_min": bridge_audit["date_min"],
                "model_handler_start_time": MODELA_HANDLER_START,
                "formal_provider_date_min": formal_calendar.get("date_min"),
            },
        },
        {
            "gate": "dapr1_accepted_canonical_bridge_contract",
            "status": "fail",
            "evidence": {
                "accepted_input_types": dapr1.get("accepted_input_types", []),
                "candidate_readiness_accepted_for_dapr3_no_publish": dapr5_readiness.get("readiness_accepted_for_dapr3_no_publish"),
                "candidate_validator_status": dapr5_readiness.get("validator_status"),
            },
        },
    ]
    blocking_gates = [gate for gate in compatibility_gates if gate["status"] == "fail"]
    decision = "STOP_NOT_COMPATIBLE_REQUIRE_SAME_LINEAGE_YAHOO_ADJUSTED_BRIDGE"
    compatibility_audit = {
        "schema_version": "dapr6.candidate_compatibility_audit.v1",
        "created_at": created_at,
        "target_asof": target_asof,
        "dapr5_candidate": {
            "decision": dapr5_decision.get("decision"),
            "candidate_readiness_path": rel(DAPR5_DIR / "db_backed_bridge_candidate_readiness.json"),
            "candidate_bridge_dir": rel(DAPR5_BRIDGE),
            "readiness_accepted_for_dapr3_no_publish": dapr5_readiness.get("readiness_accepted_for_dapr3_no_publish"),
            "model_a_ready": dapr5_decision.get("model_a_ready"),
        },
        "bridge_audit": bridge_audit,
        "compatibility_gates": compatibility_gates,
        "blocking_gate_count": len(blocking_gates),
        "blocking_gates": [gate["gate"] for gate in blocking_gates],
    }
    decision_payload = {
        "schema_version": "dapr6.lineage_model_compatibility_decision.v1",
        "created_at": created_at,
        "target_asof": target_asof,
        "decision": decision,
        "finmind_adapter_path_rejected": True,
        "candidate_export_usable_as_evidence": True,
        "candidate_export_usable_for_modela": False,
        "adapter_build_recommended": False,
        "model_a_ready": False,
        "ready_for_model_a_no_publish_dry_run": False,
        "ready_for_latest_switch": False,
        "ready_for_provider_publish": False,
        "next_required_route": "DAPR7_SAME_LINEAGE_YAHOO_ADJUSTED_EXACT_TARGET_BRIDGE_BUILD_NO_PUBLISH",
        "rationale": [
            "Model A contained runtime consumes qlib provider bin features, not DAPR5 CSV bridge directly",
            "DAPR5 source is FinMind unadjusted DB archive with factor=1.0",
            "formal Model A lineage is yahoo_adjusted_primary Option C",
            "DAPR5 candidate begins at 2024-07-01 while Model A handler starts at 2015-05-04 and DAPR1 requires full history",
            "Building a FinMind adapter would create mixed-lineage model input and should not be used for production/latest",
        ],
    }
    forbidden_action_audit = {
        "schema_version": "dapr.forbidden_action_audit.v1",
        "created_at": created_at,
        "route": "DAPR6_LINEAGE_AND_MODEL_COMPATIBILITY_REVIEW_OR_STOP",
        "all_false": all(value is False for value in FORBIDDEN_ACTIONS.values()),
        "actions": FORBIDDEN_ACTIONS,
        "write_scope": [rel(OUT_DIR)],
        "provider_pull_allowed": False,
        "provider_pull_attempted": False,
        "db_access_allowed": False,
        "db_access_attempted": False,
    }

    paths = [
        write_json("modela_runtime_requirements.json", modela_requirements),
        write_json("candidate_compatibility_audit.json", compatibility_audit),
        write_json("lineage_model_compatibility_decision.json", decision_payload),
        write_json("forbidden_action_audit.json", forbidden_action_audit),
    ]
    manifest = {
        "schema_version": "dapr.artifact_manifest.v1",
        "created_at": utc_now(),
        "artifact_manifest_status": "written",
        "route_decision": decision,
        "route_verdict": "STOP_WITH_DETERMINISTIC_NEXT_ROUTE",
        "status": "pass",
        "entries": [
            {
                "path": rel(path),
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() else None,
                "sha256": sha256(path) if path.exists() else "",
            }
            for path in paths
        ],
    }
    write_json("artifact_manifest.json", manifest)
    return decision_payload


def main() -> int:
    result = build()
    print(
        "DAPR6 lineage/model compatibility review: "
        f"decision={result['decision']} target_asof={result['target_asof']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
