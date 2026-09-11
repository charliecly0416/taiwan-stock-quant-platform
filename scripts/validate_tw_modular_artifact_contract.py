#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]

CORE_SIGNAL_FIELDS = {
    "date",
    "instrument",
    "model_name",
    "model_family",
    "candidate_rank",
    "buy_score",
    "raw_score",
    "score_rank",
    "full_qlib_rank",
    "signal_asof",
    "available_at",
    "source_artifact",
    "source_model_artifact",
    "source_feature_artifact",
}

ALLOWED_DTYPES = {"float", "int", "string", "bool", "category"}
REQUIRED_EXTENSION_METADATA = {
    "dtype",
    "semantic_role",
    "availability_policy",
    "producer",
    "allowed_consumers",
    "ranking_allowed",
    "required_for_core_replay",
    "description",
}
PIT_POLICIES = {"available_at_lte_signal_asof", "legacy_signal_date", "static_reference", "not_strategy_visible"}
RANKING_USAGES = {"buy_ordering", "exit_worst_rank", "ranking", "rerank", "score_ordering"}

FORBIDDEN_PATTERNS = [
    "future_return_*",
    "future_excess_return_*",
    "forward_return_*",
    "label_*",
    "relevance_10d_top_heavy",
    "ltr_relevance_label",
    "realized_pnl",
    "realized_return",
    "action",
    "holding",
    "position",
    "target_position",
    "order_qty",
    "execution_price",
    "execution_date",
    "broker_order_id",
    "phasee6_branch_a_fresh_ltr_score",
    "phasee6_branch_b_frozen_ltr_score",
    "phasee3_extended_oos_ltr_score",
    "adaptive_score_baseline",
    "qlib_score_raw",
    "qlib_rank_raw",
]

CORE_FULL_RANK_FIELDS = {
    "date",
    "instrument",
    "rank_source_name",
    "rank_family",
    "full_qlib_rank",
    "signal_asof",
    "available_at",
    "source_artifact",
}


def resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def check(name: str, ok: bool, details: str = "") -> dict[str, Any]:
    return {"name": name, "status": "pass" if ok else "fail", "details": details}


def forbidden_columns(columns: list[str]) -> list[str]:
    found = []
    for col in columns:
        if any(fnmatch.fnmatch(col, pattern) for pattern in FORBIDDEN_PATTERNS):
            found.append(col)
    return sorted(found)


def load_dependency(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    return yaml.safe_load(resolve(path).read_text(encoding="utf-8"))


def capability_matches(capabilities: dict[str, Any], requirement: Any) -> bool:
    if isinstance(requirement, str):
        if ":" in requirement:
            key, value = requirement.split(":", 1)
            return str(capabilities.get(key)) == value
        return bool(capabilities.get(requirement))
    if isinstance(requirement, dict):
        return all(str(capabilities.get(k)) == str(v) for k, v in requirement.items())
    return False


def dtype_matches(series: pd.Series, dtype_name: str) -> bool:
    if dtype_name == "float":
        return pd.to_numeric(series, errors="coerce").notna().sum() == series.notna().sum()
    if dtype_name == "int":
        numeric = pd.to_numeric(series, errors="coerce")
        return numeric.notna().sum() == series.notna().sum() and ((numeric.dropna() % 1) == 0).all()
    if dtype_name in {"string", "category"}:
        return True
    if dtype_name == "bool":
        vals = set(str(v).lower() for v in series.dropna().unique())
        return vals <= {"true", "false", "0", "1"}
    return False


def iter_strategy_registry_entries(registry: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    entries: list[tuple[str, dict[str, Any]]] = []
    strategies = registry.get("strategies") or {}
    for name, item in strategies.items():
        if not isinstance(item, dict):
            continue
        if "dependency_path" in item:
            entries.append((str(name), item))
            continue
        for child_name, child_item in item.items():
            if isinstance(child_item, dict):
                entries.append((f"{name}.{child_name}", child_item))
    return entries


def validate_registry(registry_path: Path) -> dict[str, Any]:
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    checks: list[dict[str, Any]] = []
    checks.append(check("registry_version", bool(registry.get("registry_version")), str(registry.get("registry_version", ""))))
    missing_dependency_paths = []
    skipped_dependency_paths = []
    for name, item in iter_strategy_registry_entries(registry):
        dep_path = item.get("dependency_path")
        if not dep_path and item.get("reason"):
            skipped_dependency_paths.append(f"{name}:reason={item.get('reason')}")
            continue
        if not dep_path or not resolve(dep_path).exists():
            missing_dependency_paths.append(f"{name}:{dep_path}")
    checks.append(check("registry_dependency_paths", not missing_dependency_paths, ",".join(missing_dependency_paths)))
    checks.append(check("registry_dependency_skipped_aliases", True, ",".join(skipped_dependency_paths)))
    missing_contract_docs = []
    for _, item in (registry.get("contracts") or {}).items():
        for key in ("docs", "extension_docs"):
            doc = item.get(key)
            if doc and not resolve(doc).exists():
                missing_contract_docs.append(doc)
    checks.append(check("registry_contract_docs", not missing_contract_docs, ",".join(missing_contract_docs)))
    return {"ok": all(row["status"] == "pass" for row in checks), "registry": str(registry_path), "checks": checks}


def validate_model_signal(manifest_path: Path, dependency: dict[str, Any]) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks: list[dict[str, Any]] = []
    checks.append(check("artifact_type", manifest.get("artifact_type") == "model_signal", str(manifest.get("artifact_type"))))
    checks.append(check("schema_version", bool(manifest.get("schema_version")), str(manifest.get("schema_version", ""))))
    checks.append(check("contract_version", bool(manifest.get("contract_version")), str(manifest.get("contract_version", ""))))
    signals_rel = manifest.get("output_files", {}).get("signals")
    signals_path = resolve(signals_rel) if signals_rel else None
    checks.append(check("signals_file_declared", bool(signals_path), str(signals_rel)))
    if not signals_path or not signals_path.exists():
        checks.append(check("signals_file_exists", False, str(signals_path)))
        return {"ok": False, "artifact": str(manifest_path), "checks": checks}
    signals = pd.read_csv(signals_path, nrows=1000000)
    columns = list(signals.columns)
    missing_core = sorted(CORE_SIGNAL_FIELDS - set(columns))
    checks.append(check("core_fields", not missing_core, ",".join(missing_core)))
    duplicate_count = int(signals.duplicated(["date", "instrument"]).sum()) if {"date", "instrument"}.issubset(signals.columns) else -1
    checks.append(check("duplicate_key", duplicate_count == 0, str(duplicate_count)))
    found_forbidden = forbidden_columns(columns)
    checks.append(check("forbidden_fields", not found_forbidden, ",".join(found_forbidden)))

    extension_decl = manifest.get("extensions", {}).get("fields", {}) or {}
    extension_cols = [c for c in columns if c not in CORE_SIGNAL_FIELDS]
    undeclared_extensions = [c for c in extension_cols if c not in extension_decl]
    checks.append(check("extension_fields_declared", not undeclared_extensions, ",".join(undeclared_extensions)))
    declared_missing = [c for c in extension_decl if c not in columns]
    checks.append(check("declared_extensions_exist", not declared_missing, ",".join(declared_missing)))
    bad_extension_names = [c for c in extension_cols if not c.startswith("ext_")]
    checks.append(check("extension_name_prefix", not bad_extension_names, ",".join(bad_extension_names)))

    metadata_failures = []
    dtype_failures = []
    pit_failures = []
    allowed_consumer_failures = []
    ranking_failures = []
    for field, meta in extension_decl.items():
        missing_meta = sorted(REQUIRED_EXTENSION_METADATA - set(meta))
        if missing_meta:
            metadata_failures.append(f"{field}:missing:{'|'.join(missing_meta)}")
            continue
        dtype = str(meta.get("dtype"))
        if dtype not in ALLOWED_DTYPES:
            dtype_failures.append(f"{field}:bad_dtype:{dtype}")
        elif field in signals.columns and not dtype_matches(signals[field], dtype):
            dtype_failures.append(f"{field}:parse_failed:{dtype}")
        policy = str(meta.get("availability_policy"))
        if policy not in PIT_POLICIES:
            pit_failures.append(f"{field}:{policy}")
        if not isinstance(meta.get("allowed_consumers"), list):
            allowed_consumer_failures.append(f"{field}:allowed_consumers_not_list")
        if meta.get("ranking_allowed") is False:
            # Actual strategy ranking usage is checked below against dependency.
            pass
    checks.append(check("extension_metadata_complete", not metadata_failures, ",".join(metadata_failures)))
    checks.append(check("extension_dtype_parseable", not dtype_failures, ",".join(dtype_failures)))
    checks.append(check("extension_availability_policy", not pit_failures, ",".join(pit_failures)))
    checks.append(check("extension_allowed_consumers_shape", not allowed_consumer_failures, ",".join(allowed_consumer_failures)))

    required_core = set(dependency.get("required_core_fields", []))
    missing_required_core = sorted(required_core - set(columns))
    checks.append(check("strategy_required_core_fields", not missing_required_core, ",".join(missing_required_core)))

    capabilities = manifest.get("capabilities", {})
    missing_capabilities = [req for req in dependency.get("required_capabilities", []) if not capability_matches(capabilities, req)]
    checks.append(check("strategy_required_capabilities", not missing_capabilities, json.dumps(missing_capabilities, ensure_ascii=True)))

    missing_extensions = []
    for item in dependency.get("required_extensions", []) or []:
        field = item.get("field")
        role = item.get("semantic_role")
        usage = item.get("usage")
        if field not in columns:
            missing_extensions.append(f"{field}:missing_column")
            continue
        declared = extension_decl.get(field)
        if not declared:
            missing_extensions.append(f"{field}:missing_schema")
            continue
        if role and declared.get("semantic_role") != role:
            missing_extensions.append(f"{field}:semantic_role_mismatch")
        if usage and usage not in declared.get("allowed_consumers", []):
            missing_extensions.append(f"{field}:usage_not_allowed")
    checks.append(check("strategy_required_extensions", not missing_extensions, ",".join(missing_extensions)))

    for item in dependency.get("ranking_usage", []) or []:
        field = item.get("field")
        usage = str(item.get("usage", ""))
        meta = extension_decl.get(field)
        if meta and meta.get("ranking_allowed") is False and usage in RANKING_USAGES:
            ranking_failures.append(f"{field}:{usage}:ranking_not_allowed")
    checks.append(check("ranking_allowed", not ranking_failures, ",".join(ranking_failures)))

    dep_forbidden = dependency.get("forbidden_fields", []) or []
    dep_forbidden_present = [c for c in columns if any(fnmatch.fnmatch(c, pattern) for pattern in dep_forbidden)]
    checks.append(check("dependency_forbidden_fields", not dep_forbidden_present, ",".join(dep_forbidden_present)))

    dep_actions = dependency.get("forbidden_actions", {}) or {}
    forbidden_action_failures = [k for k, v in dep_actions.items() if v is not True]
    checks.append(check("dependency_forbidden_actions", not forbidden_action_failures, ",".join(forbidden_action_failures)))

    strategy_rule = dependency.get("strategy_rule", "")
    diagnostic_only = bool(dependency.get("diagnostic_only"))
    if strategy_rule == "one_sell_one_buy_buggy_e8r":
        checks.append(check("diagnostic_boundary", diagnostic_only and bool(dependency.get("not_valid_strategy_evidence")), "buggy_e8r must be diagnostic_only and not valid evidence"))
    elif diagnostic_only:
        checks.append(check("diagnostic_boundary", False, f"unexpected diagnostic_only strategy {strategy_rule}"))

    return {"ok": all(row["status"] == "pass" for row in checks), "artifact": str(manifest_path), "strategy_dependency": dependency.get("strategy_rule", ""), "checks": checks}

def audit_file_has_no_fail(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        df = pd.read_csv(path)
    except Exception:
        return False
    if "status" not in df.columns:
        return True
    return not (df["status"].astype(str).str.lower() == "fail").any()


def validate_replay_result(manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks: list[dict[str, Any]] = []
    checks.append(check("artifact_type", manifest.get("artifact_type") == "replay_result", str(manifest.get("artifact_type"))))
    checks.append(check("schema_version", bool(manifest.get("schema_version")), str(manifest.get("schema_version", ""))))
    checks.append(check("contract_version", bool(manifest.get("contract_version")), str(manifest.get("contract_version", ""))))
    artifacts = manifest.get("artifacts", {})
    required = {
        "summary": "formal_replay_summary.csv",
        "daily_nav": "formal_replay_daily_nav.csv",
        "actions": "formal_replay_actions.csv",
        "snapshots": "formal_replay_position_snapshots.csv",
        "coverage": "formal_replay_coverage_audit.csv",
        "integrity": "formal_replay_position_integrity_audit.csv",
        "forbidden": "formal_replay_forbidden_field_audit.csv",
    }
    missing = []
    paths: dict[str, Path] = {}
    for key in required:
        rel_path = artifacts.get(key)
        if not rel_path:
            missing.append(f"{key}:not_declared")
            continue
        path = resolve(rel_path)
        paths[key] = path
        if not path.exists():
            missing.append(f"{key}:missing_file")
    checks.append(check("required_replay_files", not missing, ",".join(missing)))
    if missing:
        return {"ok": False, "artifact": str(manifest_path), "checks": checks}

    actions = pd.read_csv(paths["actions"])
    checks.append(check("actions_window_field", "window" in actions.columns, "window" if "window" in actions.columns else "missing"))
    active = actions[actions["action"].isin(["historical_add", "historical_risk_reduce"])] if "action" in actions.columns else pd.DataFrame()
    if not active.empty:
        execution_ok = (pd.to_datetime(active["execution_date"], errors="coerce") > pd.to_datetime(active["signal_date"], errors="coerce")).all()
        qty_ok = (pd.to_numeric(active["quantity"], errors="coerce") > 0).all()
    else:
        execution_ok = True
        qty_ok = True
    checks.append(check("execution_date_after_signal_date", bool(execution_ok), "active actions only"))
    checks.append(check("active_quantity_positive", bool(qty_ok), "active actions only"))

    integrity = pd.read_csv(paths["integrity"])
    integrity_failures = []
    if "duplicate_position_day_symbol" in integrity.columns and int(pd.to_numeric(integrity["duplicate_position_day_symbol"], errors="coerce").fillna(0).sum()) != 0:
        integrity_failures.append("duplicate_position_day_symbol")
    if "active_nonpositive_qty" in integrity.columns and int(pd.to_numeric(integrity["active_nonpositive_qty"], errors="coerce").fillna(0).sum()) != 0:
        integrity_failures.append("active_nonpositive_qty")
    if "execution_not_after_signal" in integrity.columns and int(pd.to_numeric(integrity["execution_not_after_signal"], errors="coerce").fillna(0).sum()) != 0:
        integrity_failures.append("execution_not_after_signal")
    checks.append(check("position_integrity", not integrity_failures, ",".join(integrity_failures)))

    checks.append(check("coverage_audit_status", audit_file_has_no_fail(paths["coverage"]), str(paths["coverage"])))
    checks.append(check("forbidden_field_audit_status", audit_file_has_no_fail(paths["forbidden"]), str(paths["forbidden"])))
    parity_path = resolve(manifest.get("parity_audit", "")) if manifest.get("parity_audit") else None
    action_parity_path = resolve(manifest.get("action_key_parity_audit", "")) if manifest.get("action_key_parity_audit") else None
    checks.append(check("parity_audit_status", bool(parity_path and audit_file_has_no_fail(parity_path)), str(parity_path)))
    checks.append(check("action_key_parity_audit_status", bool(action_parity_path and audit_file_has_no_fail(action_parity_path)), str(action_parity_path)))
    checks.append(check("manifest_parity_status", manifest.get("parity_status") == "pass", str(manifest.get("parity_status"))))
    return {"ok": all(row["status"] == "pass" for row in checks), "artifact": str(manifest_path), "checks": checks}



def validate_full_rank(manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks: list[dict[str, Any]] = []
    checks.append(check("artifact_type", manifest.get("artifact_type") == "full_rank", str(manifest.get("artifact_type"))))
    checks.append(check("schema_version", bool(manifest.get("schema_version")), str(manifest.get("schema_version", ""))))
    checks.append(check("contract_version", bool(manifest.get("contract_version")), str(manifest.get("contract_version", ""))))
    rank_rel = manifest.get("output_files", {}).get("full_rank")
    rank_path = resolve(rank_rel) if rank_rel else None
    checks.append(check("full_rank_file_declared", bool(rank_path), str(rank_rel)))
    if not rank_path or not rank_path.exists():
        checks.append(check("full_rank_file_exists", False, str(rank_path)))
        return {"ok": False, "artifact": str(manifest_path), "checks": checks}
    rank = pd.read_csv(rank_path)
    columns = list(rank.columns)
    missing_core = sorted(CORE_FULL_RANK_FIELDS - set(columns))
    checks.append(check("core_fields", not missing_core, ",".join(missing_core)))
    duplicate_count = int(rank.duplicated(["date", "instrument"]).sum()) if {"date", "instrument"}.issubset(rank.columns) else -1
    checks.append(check("duplicate_key", duplicate_count == 0, str(duplicate_count)))
    found_forbidden = forbidden_columns(columns)
    checks.append(check("forbidden_fields", not found_forbidden, ",".join(found_forbidden)))
    non_null = int(pd.to_numeric(rank.get("full_qlib_rank", pd.Series(dtype=float)), errors="coerce").notna().sum())
    checks.append(check("full_qlib_rank_non_null", non_null == len(rank), f"{non_null}/{len(rank)}"))
    if {"available_at", "signal_asof"}.issubset(rank.columns):
        pit_violations = int((pd.to_datetime(rank["available_at"], errors="coerce") > pd.to_datetime(rank["signal_asof"], errors="coerce")).sum())
    else:
        pit_violations = -1
    checks.append(check("available_at_lte_signal_asof", pit_violations == 0, str(pit_violations)))
    checks.append(check("manifest_row_count", int(manifest.get("row_count", -1)) == len(rank), f"{manifest.get('row_count')} vs {len(rank)}"))
    checks.append(check("quality_status", manifest.get("quality_status") == "pass", str(manifest.get("quality_status"))))
    for key in ("schema", "coverage_audit", "forbidden_field_audit", "legacy_mapping_audit"):
        rel_path = manifest.get("output_files", {}).get(key)
        checks.append(check(f"{key}_exists", bool(rel_path and resolve(rel_path).exists()), str(rel_path)))
    return {"ok": all(row["status"] == "pass" for row in checks), "artifact": str(manifest_path), "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description="Readonly validator skeleton for TW modular artifact contracts.")
    parser.add_argument("--artifact", default="", help="Path to artifact manifest.json")
    parser.add_argument("--strategy-dependency", default="", help="Optional strategy dependency yaml")
    parser.add_argument("--registry", default="", help="Optional registry yaml to validate dependency paths")
    parser.add_argument("--json", action="store_true", help="Print JSON result")
    args = parser.parse_args()

    if args.registry:
        result = validate_registry(resolve(args.registry))
    else:
        if not args.artifact:
            parser.error("--artifact is required unless --registry is provided")
        artifact_path = resolve(args.artifact)
        manifest = json.loads(artifact_path.read_text(encoding="utf-8"))
        if manifest.get("artifact_type") == "replay_result":
            result = validate_replay_result(artifact_path)
        elif manifest.get("artifact_type") == "full_rank":
            result = validate_full_rank(artifact_path)
        else:
            dependency = load_dependency(args.strategy_dependency)
            result = validate_model_signal(artifact_path, dependency)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']} artifact={result['artifact']}")
        for row in result["checks"]:
            print(f"{row['status']} {row['name']} {row['details']}")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
