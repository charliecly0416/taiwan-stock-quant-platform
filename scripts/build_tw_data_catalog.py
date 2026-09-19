#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOG_DIR = ROOT / "data_tw/catalog"

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

ENTRY_FIELDS = [
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


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def safe_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(str(value))
    except ValueError:
        return None


def first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def walk_candidates(base: Path, max_depth: int = 3, max_files: int = 5000) -> list[Path]:
    if not base.exists():
        return []
    if base.is_file():
        return [base]
    out: list[Path] = []
    base_depth = len(base.parts)
    for path in base.rglob("*"):
        if len(path.parts) - base_depth > max_depth:
            continue
        if path.is_file():
            out.append(path)
            if len(out) >= max_files:
                break
    return out


def find_evidence(path_text: str) -> dict[str, str]:
    base = ROOT / path_text
    files = walk_candidates(base)
    by_name = {p.name.lower(): p for p in files}

    manifest = first_existing([
        base if base.is_file() and base.name == "manifest.json" else base / "manifest.json",
        by_name.get("manifest.json") or Path("__missing__"),
        by_name.get("latest.json") or Path("__missing__"),
    ])
    if manifest is None and base.is_file() and base.suffix.lower() == ".json" and "latest" in base.name.lower():
        manifest = base

    schema = first_existing([
        base / "schema.json",
        by_name.get("schema.json") or Path("__missing__"),
        by_name.get("feature_schema_alignment_audit.csv") or Path("__missing__"),
    ])
    coverage = first_existing([
        base / "coverage_audit.csv",
        base / "coverage_audit.json",
        by_name.get("coverage_audit.csv") or Path("__missing__"),
        by_name.get("coverage_audit.json") or Path("__missing__"),
        by_name.get("strict_e4_top50_coverage_audit.csv") or Path("__missing__"),
        by_name.get("source_freshness_audit.json") or Path("__missing__"),
    ])
    lineage = first_existing([
        base / "lineage.json",
        base / "source_trace.json",
        base / "source_artifact_trace.json",
        by_name.get("lineage.json") or Path("__missing__"),
        by_name.get("source_trace.json") or Path("__missing__"),
        by_name.get("source_artifact_trace.json") or Path("__missing__"),
    ])
    validator = first_existing([
        base / "validator_report.json",
        base / "validator_result.json",
        base / "validation_report.json",
        by_name.get("validator_report.json") or Path("__missing__"),
        by_name.get("validator_result.json") or Path("__missing__"),
        by_name.get("validation_report.json") or Path("__missing__"),
    ])
    return {
        "manifest_path": rel(manifest),
        "schema_path": rel(schema),
        "coverage_audit_path": rel(coverage),
        "lineage_path": rel(lineage),
        "validator_report_path": rel(validator),
    }


def path_checksum(path_text: str) -> str:
    path = ROOT / path_text
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    if path.is_file():
        digest.update(path.read_bytes())
        return digest.hexdigest()
    files = walk_candidates(path, max_depth=2, max_files=200)
    for child in sorted(files, key=lambda p: rel(p)):
        digest.update(rel(child).encode("utf-8"))
        try:
            stat = child.stat()
            digest.update(str(stat.st_size).encode("utf-8"))
        except OSError:
            pass
    return digest.hexdigest()


def infer_symbol_count(row: dict[str, str], path_text: str) -> int | None:
    layer = row.get("layer", "")
    dataset = row.get("dataset_or_artifact", "")
    path = ROOT / path_text
    if "option_c_150" in dataset or "option_c_150" in path_text:
        return 150
    if path.exists() and path.is_dir() and layer in {"normalized", "model_signal"}:
        try:
            return sum(1 for child in path.iterdir() if child.is_file() and child.suffix.lower() in {".csv", ".txt"})
        except OSError:
            return safe_int(row.get("file_count"))
    return safe_int(row.get("file_count"))


def infer_row_count(row: dict[str, str]) -> int | None:
    return safe_int(row.get("file_count"))


def has_complete_evidence(evidence: dict[str, str]) -> bool:
    return all(bool(evidence.get(key)) for key in ["manifest_path", "schema_path", "coverage_audit_path", "lineage_path"])


def classify_status(row: dict[str, str], evidence: dict[str, str], actual_exists: bool) -> tuple[str, list[str]]:
    original = (row.get("status") or "").strip() or "MISSING"
    path_text = row.get("path", "")
    canonicality = (row.get("canonicality") or "").strip()
    latest_concept = (row.get("latest_pointer_type") or "").strip()
    reason_bits: list[str] = []

    if not actual_exists:
        return "MISSING", ["path missing in current workspace"]
    if original in {"STALE", "BLOCKED_PROVIDER", "BLOCKED_SCHEMA", "BLOCKED_PIT", "BLOCKED_COVERAGE", "BLOCKED_VALIDATOR"}:
        return original, [f"preserved DNG0 blocker/stale status={original}"]
    if canonicality == "temporary_bridge" or latest_concept == "temporary_research_bridge" or "bridge" in path_text:
        return "TEMPORARY_BRIDGE", ["temporary/readonly bridge must not be READY"]
    if canonicality in {"experiment", "demo", "experiment_artifact", "temporary_cache", "ops_history"} or path_text.startswith("data_tw/experiments/"):
        return "RESEARCH_ONLY", ["experiment/demo/ops-history path is not canonical"]
    if canonicality in {"legacy_standard_candidate", "missing_layer"}:
        if not has_complete_evidence(evidence):
            return "LEGACY_UNCATALOGED", ["legacy candidate lacks full manifest/schema/coverage/lineage evidence"]
    if original == "RESEARCH_ONLY":
        return "RESEARCH_ONLY", ["preserved DNG0 research-only classification"]
    if original == "MISSING":
        return "MISSING", ["preserved DNG0 missing classification"]
    if not has_complete_evidence(evidence):
        reason_bits.append("missing one or more manifest/schema/coverage/lineage evidence files")
        if canonicality in {"canonical_candidate", "standard_artifact", "registry_contract", "contract_source", "ops_run_registry_like", "dng0_output"}:
            return "PARTIAL_READY", reason_bits
        return "LEGACY_UNCATALOGED", reason_bits
    if canonicality in {"temporary_bridge", "experiment", "demo"}:
        return "RESEARCH_ONLY", ["non-canonical path with complete evidence remains non-production"]
    return "READY", ["complete local evidence found and no bridge/research downgrade applied"]


def source_provider_for(row: dict[str, str]) -> str:
    text = (row.get("path", "") + " " + row.get("dataset_or_artifact", "")).lower()
    if "finmind" in text:
        return "FinMind"
    if "yahoo" in text or "option_c" in text or "qlib" in text:
        return "Yahoo/qlib_pipeline"
    if "twii" in text:
        return "TWII_normalized_source"
    return "local_artifact"


def infer_source_run_id(row: dict[str, str]) -> str:
    path = row.get("path", "")
    for part in reversed(Path(path).parts):
        if "2026" in part or part.startswith(("mtr", "d")):
            return part
    return ""


def safety_flags(status: str, canonicality: str) -> dict[str, Any]:
    flags: dict[str, Any] = {key: False for key in FORBIDDEN_ACTION_KEYS}
    flags.update(
        {
            "read_only_scan": True,
            "production_allowed": status == "READY" and canonicality in {"standard_artifact", "canonical_candidate"},
            "not_order": True,
            "not_latest_switch": True,
        }
    )
    return flags


def build_entries(inventory_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for row in inventory_rows:
        path_text = row.get("path", "")
        actual_exists = (ROOT / path_text).exists()
        evidence = find_evidence(path_text)
        status, downgrade_reasons = classify_status(row, evidence, actual_exists)
        date_min = row.get("date_min") or ""
        date_max = row.get("date_max") or ""
        latest_concept = row.get("latest_pointer_type") or ""
        canonicality = row.get("canonicality") or ""
        original_reason = row.get("status_reason") or ""
        status_reason = original_reason
        if downgrade_reasons:
            status_reason = f"{original_reason} DNG1 conservative classification: {'; '.join(downgrade_reasons)}".strip()
        entry: dict[str, Any] = {
            "dataset_id": row.get("dataset_or_artifact") or "",
            "layer": row.get("layer") or "",
            "asof": date_max or date_min,
            "date_min": date_min,
            "date_max": date_max,
            "symbol_count": infer_symbol_count(row, path_text),
            "row_count": infer_row_count(row),
            "path": path_text,
            **evidence,
            "status": status,
            "status_reason": status_reason,
            "source_provider": source_provider_for(row),
            "source_run_id": infer_source_run_id(row),
            "checksum": path_checksum(path_text),
            "pit_policy": "unknown_requires_DNG2_contract" if status != "READY" else "manifest_or_local_evidence",
            "available_at_policy": "unknown_requires_DNG2_contract" if status != "READY" else "manifest_or_local_evidence",
            "canonicality": canonicality,
            "latest_concept": latest_concept,
            "forbidden_action_flags": safety_flags(status, canonicality),
            "dng0_status": row.get("status") or "",
            "dng0_recommended_next_action": row.get("recommended_next_action") or "",
        }
        for field in ENTRY_FIELDS:
            entry.setdefault(field, "")
        entries.append(entry)
    return entries


def normalize_pointer_status(row: dict[str, str]) -> str:
    path_text = row.get("path", "")
    status = row.get("status") or "MISSING"
    concept = row.get("latest_concept") or ""
    lower_path = path_text.lower()
    if not boolish(row.get("exists")) or not (ROOT / path_text).exists():
        return "MISSING"
    if concept in {"readonly_bridge_latest", "temporary_research_bridge_latest"} or "bridge" in lower_path:
        return "TEMPORARY_BRIDGE"
    if lower_path.startswith("data_tw/experiments/") or "experiment" in (row.get("status_reason") or "").lower():
        return "RESEARCH_ONLY"
    if concept in {"provider_raw_latest", "normalized_latest", "price_store_latest", "qlib_accepted_latest", "model_signal_latest"} and status == "READY":
        return "PARTIAL_READY"
    return status if status in STATUS_ENUM else "PARTIAL_READY"


def build_latest_status(pointer_rows: list[dict[str, str]]) -> dict[str, Any]:
    generated_at = now()
    by_concept: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in pointer_rows:
        concept = row.get("latest_concept") or ""
        if not concept:
            continue
        candidate = {
            "latest_concept": concept,
            "path": row.get("path") or "",
            "exists": boolish(row.get("exists")),
            "asof": row.get("asof") or "",
            "run_id": row.get("run_id") or "",
            "target_path": row.get("target_path") or "",
            "status": normalize_pointer_status(row),
            "status_reason": row.get("status_reason") or "",
            "downstream_surface": row.get("downstream_surface") or "",
            "forbidden_action_flags": {key: False for key in FORBIDDEN_ACTION_KEYS},
        }
        by_concept[concept].append(candidate)

    latest_by_concept: dict[str, Any] = {}
    for concept in REQUIRED_LATEST_CONCEPTS:
        candidates = by_concept.get(concept, [])
        if not candidates:
            latest_by_concept[concept] = {
                "status": "MISSING",
                "asof": "",
                "path": "",
                "target_path": "",
                "run_id": "",
                "status_reason": "No DNG0 pointer row found for required latest concept.",
                "candidates": [],
            }
            continue
        selected = sorted(candidates, key=lambda r: (r.get("asof") or "", r.get("path") or ""), reverse=True)[0]
        latest_by_concept[concept] = {
            "status": selected["status"],
            "asof": selected.get("asof") or "",
            "path": selected.get("path") or "",
            "target_path": selected.get("target_path") or "",
            "run_id": selected.get("run_id") or "",
            "status_reason": selected.get("status_reason") or "",
            "candidates": candidates,
        }

    known_mismatch = [
        {
            "mismatch_id": "provider_normalized_vs_qlib_accepted",
            "description": "provider_raw_latest/normalized_latest reach 2026-06-25 while qlib_accepted_latest remains 2026-06-17.",
            "severity": "expected_governance_gap",
        },
        {
            "mismatch_id": "readonly_snapshot_asof_vs_signal_asof",
            "description": "readonly_snapshot_latest points to snapshot asof 2026-06-18 but source signal/data asof remains 2026-06-17.",
            "severity": "expected_governance_gap",
        },
        {
            "mismatch_id": "agent_prompt_latest_missing",
            "description": "agent_prompt_latest is MISSING and must not be inferred from readonly snapshot or strategy context.",
            "severity": "blocker_for_agent_prompt_publish",
        },
        {
            "mismatch_id": "price_store_latest_is_bridge",
            "description": "price_store_latest evidence is execution readiness bridge only, not canonical PriceStore latest.",
            "severity": "blocks_DNG2_until_canonicalized",
        },
    ]
    return {
        "schema_version": "v1.tw_data_latest_status.dng1",
        "generated_at": generated_at,
        "latest_by_concept": latest_by_concept,
        "known_mismatch": known_mismatch,
        "recommended_next_actions": [
            "DNG2 should define canonical manifests/schema/coverage/lineage for NormalizedStore, PriceStore, FeatureStore, and provider views.",
            "Keep qlib accepted latest, readonly latest, and Agent prompt latest behind separate gates.",
            "Represent temporary bridges as bridge evidence only; do not route default strategy inputs through them.",
        ],
        "forbidden_action_audit": {
            "scope": "DNG1 read-only catalog build",
            "actions": {key: False for key in FORBIDDEN_ACTION_KEYS},
        },
    }


def build_summary(entries: list[dict[str, Any]], latest_status: dict[str, Any]) -> dict[str, Any]:
    status_counts = Counter(str(e.get("status")) for e in entries)
    layer_counts = Counter(str(e.get("layer")) for e in entries)
    latest_counts = Counter(
        str(item.get("status"))
        for item in latest_status.get("latest_by_concept", {}).values()
    )
    return {
        "entry_count": len(entries),
        "status_counts": dict(sorted(status_counts.items())),
        "layer_counts": dict(sorted(layer_counts.items())),
        "latest_concept_status_counts": dict(sorted(latest_counts.items())),
        "ready_entry_count": status_counts.get("READY", 0),
        "conservative_non_ready_count": len(entries) - status_counts.get("READY", 0),
    }


def write_summary_csv(path: Path, entries: list[dict[str, Any]]) -> None:
    columns = [
        "layer",
        "dataset_id",
        "status",
        "canonicality",
        "latest_concept",
        "asof",
        "date_min",
        "date_max",
        "path",
        "status_reason",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for entry in entries:
            writer.writerow({col: entry.get(col, "") for col in columns})


def build_catalog(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    inventory_path = ROOT / args.inventory
    pointer_path = ROOT / args.latest_inventory
    route_path = ROOT / args.route_dependency_sample
    inventory_rows = load_csv(inventory_path)
    pointer_rows = load_csv(pointer_path)
    entries = build_entries(inventory_rows)
    latest_status = build_latest_status(pointer_rows)
    summary = build_summary(entries, latest_status)
    catalog = {
        "catalog_version": "v1.tw_data_catalog.dng1",
        "generated_at": now(),
        "source_inventory": {
            "current_data_inventory": rel(inventory_path),
            "latest_pointer_inventory": rel(pointer_path),
            "route_dependency_sample": rel(route_path),
            "input_row_counts": {
                "current_data_inventory": len(inventory_rows),
                "latest_pointer_inventory": len(pointer_rows),
                "route_dependency_sample": len(load_csv(route_path)),
            },
        },
        "entries": entries,
        "summary": summary,
        "forbidden_action_audit": {
            "scope": "DNG1 read-only scanner",
            "actions": {key: False for key in FORBIDDEN_ACTION_KEYS},
            "notes": [
                "Scanner reads DNG0 CSVs and local evidence files only.",
                "No fetch, publish, latest switch, model run, strategy replay, broker/order, or target position/weight action is invoked.",
            ],
        },
    }
    return catalog, latest_status


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build conservative Taiwan data catalog from DNG0 inventory.")
    parser.add_argument("--inventory", default="data_tw/catalog/dng0_current_data_inventory.csv")
    parser.add_argument("--latest-inventory", default="data_tw/catalog/dng0_latest_pointer_inventory.csv")
    parser.add_argument("--route-dependency-sample", default="data_tw/catalog/dng0_route_dependency_sample.csv")
    parser.add_argument("--catalog-out", default="data_tw/catalog/data_catalog.json")
    parser.add_argument("--latest-status-out", default="data_tw/catalog/latest_status.json")
    parser.add_argument("--summary-out", default="data_tw/catalog/data_catalog_summary.csv")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    catalog, latest_status = build_catalog(args)
    catalog_path = ROOT / args.catalog_out
    latest_status_path = ROOT / args.latest_status_out
    summary_path = ROOT / args.summary_out
    write_json(catalog_path, catalog)
    write_json(latest_status_path, latest_status)
    write_summary_csv(summary_path, catalog["entries"])
    result = {
        "ok": True,
        "catalog": rel(catalog_path),
        "latest_status": rel(latest_status_path),
        "summary_csv": rel(summary_path),
        "entry_count": catalog["summary"]["entry_count"],
        "status_counts": catalog["summary"]["status_counts"],
        "latest_concept_status_counts": catalog["summary"]["latest_concept_status_counts"],
        "forbidden_action_audit": catalog["forbidden_action_audit"],
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"wrote {rel(catalog_path)}, {rel(latest_status_path)}, {rel(summary_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
