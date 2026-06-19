#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RULES = {
    "original",
    "top50_exit_all",
    "top50_exit_one_worst_sell",
    "one_sell_one_buy_correct",
    "one_sell_one_buy_buggy_e8r",
}
REQUIRED_ARTIFACTS = [
    "summary_parity",
    "daily_nav_parity",
    "actions_parity",
    "action_key_parity",
    "position_snapshot_parity",
    "coverage_audit",
    "forbidden_scope_audit",
    "decision_source_audit",
]
PARITY_KEYS = ["summary_parity", "daily_nav_parity", "actions_parity", "action_key_parity", "position_snapshot_parity"]


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


def check(name: str, ok: bool, details: str = "") -> dict[str, Any]:
    return {"name": name, "status": "pass" if ok else "fail", "details": details}


def csv_status_all_pass(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "missing"
    frame = pd.read_csv(path)
    if "status" not in frame.columns:
        return False, "missing status column"
    bad = frame[~frame["status"].astype(str).str.lower().eq("pass")]
    return bad.empty, bad.head(5).to_dict("records").__repr__() if not bad.empty else ""


def load_frame_from_manifest(manifest: dict[str, Any], key: str) -> pd.DataFrame:
    return pd.read_csv(resolve(str((manifest.get("artifacts") or {})[key])))


def manifest_order_details(order_manifest: dict[str, Any], manifest_path: Path) -> tuple[set[str], set[str], set[str], bool, bool, bool, set[str]]:
    order_path = resolve(str((order_manifest.get("output_files") or {}).get("order_intents", "")))
    if not order_path.exists():
        return set(), set(), set(), False, False, False, set()
    frame = pd.read_csv(order_path)
    rules = set(frame.get("strategy_rule", pd.Series(dtype=str)).astype(str).dropna())
    methods = set(frame.get("model_name", pd.Series(dtype=str)).astype(str).dropna())
    dates = set(frame.get("signal_date", pd.Series(dtype=str)).astype(str).dropna())
    stage_ok = order_manifest.get("artifact_stage") == "d3_full_window_replay_input"
    stage_ok = stage_ok and order_manifest.get("artifact_type") == "order_intent"
    stage_ok = stage_ok and order_manifest.get("readonly_only") is True and order_manifest.get("not_order") is True
    source_ok = order_manifest.get("generation_source") == "strategy_decision_engine"
    source_ok = source_ok and order_manifest.get("not_generated_from_replay_actions") is True
    source_ok = source_ok and order_manifest.get("not_generated_from_replay_snapshots") is True
    required_cols = {"order_intent_row_id", "intent_action", "candidate_rank", "buy_rank", "full_qlib_rank", "intent_reason", "source_signal_asof", "source_available_at", "generation_source", "not_generated_from_replay_actions", "not_generated_from_replay_snapshots"}
    action_rows = frame[frame.get("intent_action", pd.Series(dtype=str)).astype(str).isin(["buy", "sell"])]
    decision_ok = required_cols.issubset(frame.columns)
    if decision_ok and not action_rows.empty:
        decision_ok = action_rows["intent_reason"].astype(str).ne("").all()
        decision_ok = decision_ok and action_rows["source_signal_asof"].astype(str).ne("").all()
        decision_ok = decision_ok and action_rows["source_available_at"].astype(str).ne("").all()
        decision_ok = decision_ok and action_rows["generation_source"].astype(str).eq("strategy_decision_engine").all()
        decision_ok = decision_ok and action_rows["not_generated_from_replay_actions"].map(lambda x: str(x).lower() in {"true", "1"}).all()
        decision_ok = decision_ok and action_rows["not_generated_from_replay_snapshots"].map(lambda x: str(x).lower() in {"true", "1"}).all()
        ranks = action_rows[["candidate_rank", "buy_rank", "full_qlib_rank"]].astype(str).replace({"nan": "", "<NA>": ""})
        decision_ok = decision_ok and ranks.apply(lambda row: any(str(v).strip() not in {"", "nan"} for v in row), axis=1).all()
    row_ids = set(frame.get("order_intent_row_id", pd.Series(dtype=str)).astype(str).dropna())
    return rules, methods, dates, stage_ok, source_ok, decision_ok, row_ids


def validate_artifact(manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    artifacts = manifest.get("artifacts") or {}
    missing = [key for key in REQUIRED_ARTIFACTS if not artifacts.get(key) or not resolve(str(artifacts.get(key))).exists()]
    baseline_manifest_path = resolve(str(manifest.get("baseline_manifest", "")))
    replay_manifest_path = resolve(str(manifest.get("order_intent_replay_manifest", "")))
    baseline_exists = bool(manifest.get("baseline_manifest")) and baseline_manifest_path.exists()
    replay_exists = bool(manifest.get("order_intent_replay_manifest")) and replay_manifest_path.exists()
    replay_manifest = load_json(replay_manifest_path) if replay_exists else {}
    baseline_manifest = load_json(baseline_manifest_path) if baseline_exists else {}
    checks: list[dict[str, Any]] = [
        check("artifact_type", manifest.get("artifact_type") == "order_intent_replay_parity", str(manifest.get("artifact_type"))),
        check("schema_version", str(manifest.get("schema_version")) == "order_intent_replay_parity_d3_v1", str(manifest.get("schema_version"))),
        check("window_2026_ytd", str(manifest.get("window")) == "2026_ytd", str(manifest.get("window"))),
        check("baseline_manifest_exists", baseline_exists, str(manifest.get("baseline_manifest"))),
        check("order_intent_replay_manifest_exists", replay_exists, str(manifest.get("order_intent_replay_manifest"))),
        check("order_intent_replay_manifest_not_equal_baseline_manifest", baseline_manifest_path.resolve() != replay_manifest_path.resolve() if baseline_exists and replay_exists else False),
        check("reject_legacy_formal_replay_manifest_as_replay_source", str(replay_manifest.get("schema_version")) != "replay_result_r10_action_window_cleanup", str(replay_manifest.get("schema_version"))),
        check("order_intent_replay_manifest_artifact_type", replay_manifest.get("artifact_type") == "replay_result", str(replay_manifest.get("artifact_type"))),
        check("order_intent_replay_manifest_decision_source_order_intent", replay_manifest.get("decision_source") == "order_intent_artifact", str(replay_manifest.get("decision_source"))),
        check("required_artifacts_exist", not missing, "|".join(missing)),
    ]
    present_rules = set(str(x) for x in manifest.get("rules_present", []))
    declared_rules = set(str(x) for x in manifest.get("rules", []))
    checks.append(check("five_rules_all_present", RULES.issubset(present_rules) and RULES.issubset(declared_rules), f"declared={sorted(declared_rules)} present={sorted(present_rules)}"))
    checks.append(check("diagnostic_rule_marked_diagnostic_only", manifest.get("diagnostic_rule") == "one_sell_one_buy_buggy_e8r" and manifest.get("diagnostic_rule_only_for_parity") is True and manifest.get("diagnostic_rule_not_valid_strategy_evidence") is True))
    checks.append(check("no_d3_parity_bypass", manifest.get("no_d3_parity_bypass") is True))
    checks.append(check("no_missing_row_ignored", manifest.get("no_missing_row_ignored") is True))
    checks.append(check("parity_status_pass", str(manifest.get("parity_status")) == "pass", str(manifest.get("parity_status"))))
    order_intent_artifacts = [str(x) for x in replay_manifest.get("order_intent_artifacts", [])]
    order_paths = [resolve(path) for path in order_intent_artifacts]
    checks.append(check("order_intent_artifacts_exist", bool(order_paths) and all(path.exists() for path in order_paths), f"count={len(order_paths)}"))
    all_rules: set[str] = set()
    all_methods: set[str] = set()
    all_dates: set[str] = set()
    all_stage_ok = bool(order_paths)
    all_source_ok = bool(order_paths)
    all_decision_ok = bool(order_paths)
    order_row_ids_by_manifest: dict[str, set[str]] = {}
    for path in order_paths:
        if not path.exists():
            all_stage_ok = False
            all_source_ok = False
            all_decision_ok = False
            continue
        rules, methods, dates, stage_ok, source_ok, decision_ok, row_ids = manifest_order_details(load_json(path), path)
        all_rules.update(rules)
        all_methods.update(methods)
        all_dates.update(dates)
        all_stage_ok = all_stage_ok and stage_ok
        all_source_ok = all_source_ok and source_ok
        all_decision_ok = all_decision_ok and decision_ok
        order_row_ids_by_manifest[str(path.resolve())] = row_ids
        order_row_ids_by_manifest[rel(path)] = row_ids
    checks.append(check("order_intent_artifacts_cover_five_rules", RULES.issubset(all_rules), sorted(all_rules).__repr__()))
    replay_methods = set(str(x) for x in replay_manifest.get("methods_present", []))
    checks.append(check("order_intent_artifacts_cover_five_methods", bool(replay_methods) and replay_methods.issubset(all_methods), f"orders={sorted(all_methods)} replay={sorted(replay_methods)}"))
    checks.append(check("order_intent_artifacts_cover_2026_ytd", bool(all_dates) and min(all_dates) <= "2026-01-02" and max(all_dates) >= "2026-05-06", f"min={min(all_dates) if all_dates else ''} max={max(all_dates) if all_dates else ''}"))
    checks.append(check("order_intent_artifacts_stage_and_readonly", all_stage_ok))
    checks.append(check("order_intents_generation_source_strategy_decision_engine", all_source_ok))
    checks.append(check("order_intents_not_generated_from_replay_actions", all_source_ok))
    checks.append(check("order_intents_not_generated_from_replay_snapshots", all_source_ok))
    checks.append(check("order_intent_action_rows_have_decision_fields", all_decision_ok))
    checks.append(check("replay_result_generated_by_replay_execution_engine", replay_manifest.get("generated_by") == "replay_execution_engine", str(replay_manifest.get("generated_by"))))
    checks.append(check("replay_result_not_copied_from_legacy_replay", replay_manifest.get("not_copied_from_legacy_replay") is True))
    checks.append(check("replay_result_execution_input_source_order_intent", replay_manifest.get("execution_input_source") == "order_intent_artifact", str(replay_manifest.get("execution_input_source"))))
    checks.append(check("legacy_replay_used_only_for_parity", replay_manifest.get("legacy_replay_used_only_for_parity") is True))
    checksum_lineage_ok = (
        replay_manifest.get("outputs_recomputed_checksum_not_legacy_copy") is True
        and replay_manifest.get("generated_by") == "replay_execution_engine"
        and replay_manifest.get("execution_input_source") == "order_intent_artifact"
        and replay_manifest.get("not_copied_from_legacy_replay") is True
    )
    checks.append(check("replay_result_outputs_recomputed_checksum_not_legacy_copy", checksum_lineage_ok))
    if replay_exists and (replay_manifest.get("artifacts") or {}).get("actions"):
        actions = load_frame_from_manifest(replay_manifest, "actions")
        ref_ok = "order_intent_artifact" in actions.columns and actions["order_intent_artifact"].astype(str).ne("").all()
        row_ok = "order_intent_row_id" in actions.columns and actions["order_intent_row_id"].astype(str).ne("").all()
        refs = set(actions.get("order_intent_artifact", pd.Series(dtype=str)).astype(str))
        checks.append(check("replay_actions_reference_order_intent_artifact", ref_ok and row_ok and refs.issubset(set(order_intent_artifacts)), f"refs={len(refs)}"))
        match_ok = ref_ok and row_ok
        if match_ok:
            for row in actions[["order_intent_artifact", "order_intent_row_id"]].to_dict("records"):
                ref = str(row["order_intent_artifact"])
                row_id = str(row["order_intent_row_id"])
                ref_path = str(resolve(ref).resolve())
                if row_id not in order_row_ids_by_manifest.get(ref, set()) and row_id not in order_row_ids_by_manifest.get(ref_path, set()):
                    match_ok = False
                    break
        checks.append(check("replay_result_actions_order_intent_rows_exist_and_match", match_ok))
    else:
        checks.append(check("replay_actions_reference_order_intent_artifact", False, "missing replay actions"))
        checks.append(check("replay_result_actions_order_intent_rows_exist_and_match", False, "missing replay actions"))
    if baseline_exists:
        checks.append(check("baseline_manifest_legacy_replay_type", baseline_manifest.get("artifact_type") == "replay_result", str(baseline_manifest.get("artifact_type"))))
    if missing:
        return {"ok": False, "artifact": rel(manifest_path), "checks": checks}
    if missing:
        return {"ok": False, "artifact": rel(manifest_path), "checks": checks}

    for key in PARITY_KEYS:
        ok, details = csv_status_all_pass(resolve(str(artifacts[key])))
        checks.append(check(f"{key}_all_pass", ok, details))
        frame = pd.read_csv(resolve(str(artifacts[key])))
        if {"baseline_rows", "replay_rows"}.issubset(frame.columns):
            row_count_ok = (pd.to_numeric(frame["baseline_rows"], errors="coerce") == pd.to_numeric(frame["replay_rows"], errors="coerce")).all()
            checks.append(check(f"{key}_row_counts_match", bool(row_count_ok), frame[["baseline_rows", "replay_rows"]].to_dict("records").__repr__()))
    for key in ["coverage_audit", "forbidden_scope_audit", "decision_source_audit"]:
        ok, details = csv_status_all_pass(resolve(str(artifacts[key])))
        checks.append(check(f"{key}_pass", ok, details))

    coverage = pd.read_csv(resolve(str(artifacts["coverage_audit"])))
    coverage_rules = set(str(x) for x in coverage.get("rule", pd.Series(dtype=str)).dropna().unique())
    checks.append(check("coverage_has_five_rules", RULES.issubset(coverage_rules), sorted(coverage_rules).__repr__()))
    if "daily_nav_rows" in coverage.columns:
        checks.append(check("coverage_no_empty_rule_rows", (pd.to_numeric(coverage["daily_nav_rows"], errors="coerce") > 0).all()))
    decision = pd.read_csv(resolve(str(artifacts["decision_source_audit"])))
    decision_rows = {str(row["audit_name"]): row for row in decision.to_dict("records") if "audit_name" in row}
    checks.append(check("decision_source_audit_present", "decision_source" in decision_rows))
    checks.append(check("decision_source_audit_points_to_order_intent_replay_manifest", str(decision_rows.get("decision_source", {}).get("details")) == str(manifest.get("order_intent_replay_manifest")), str(decision_rows.get("decision_source", {}).get("details"))))
    checks.append(check("diagnostic_rule_boundary_audit_present", "diagnostic_rule_boundary" in decision_rows))
    return {"ok": all(row["status"] == "pass" for row in checks), "artifact": rel(manifest_path), "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate D3 OrderIntent replay parity artifact.")
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
