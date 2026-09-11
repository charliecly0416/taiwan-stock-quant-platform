#!/usr/bin/env python3
"""Read-only MBCDS3 daily shadow wiring discovery and preflight.

This stage deliberately does not import or execute the production orchestrator.
It inventories its callable boundaries and existing evidence, then records the
smallest future insertion contract.  It must remain safe to run from cron,
but is not itself a cron entry and never writes a protected path.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = ROOT / "scripts/run_daily_tw_stock_auto_update.py"
CRON = ROOT / "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron"
CONTRACT_ROOT = ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow/mbcds3_contract_freeze_20260905"
RANKING_ROOT = ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow/mbcds2_ranking_chain_20260905"
FEATURE_ROOT = ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow/mbcds2_feature_input_20260905"
INVESTIGATION_ROOT = ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow/mbcds2_missing_date_source_investigation_20260905"
DEFAULT_OUT = ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow/mbcds3_wiring_preflight_20260905"

PROTECTED = (
    ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json",
    ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt",
    CRON,
)


def sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError:
        return None


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def protected_fingerprints() -> list[dict[str, Any]]:
    return [{"path": rel(path), "status": "PRESENT" if path.exists() else "ABSENT", "sha256": sha256(path)} for path in PROTECTED]


def function_inventory(tree: ast.Module) -> list[dict[str, Any]]:
    names = {
        "run_provider_candidate_refresh_gate",
        "run_model_signal_gate",
        "build_daily_chain_status_payload",
        "write_daily_chain_status_and_ledger",
        "run_daily_update",
    }
    result = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            calls = sorted({
                call.func.id if isinstance(call.func, ast.Name) else call.func.attr
                for call in ast.walk(node) if isinstance(call, ast.Call) and isinstance(call.func, (ast.Name, ast.Attribute))
            })
            result.append({"name": node.name, "line": node.lineno, "end_line": getattr(node, "end_lineno", node.lineno), "calls": calls})
    return sorted(result, key=lambda item: item["line"])


def call_sites(tree: ast.Module) -> list[dict[str, Any]]:
    wanted = {"run_provider_candidate_refresh_gate", "run_model_signal_gate", "build_daily_chain_status_payload"}
    rows = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ""
            if name in wanted:
                rows.append({"call": name, "line": node.lineno})
    return sorted(rows, key=lambda item: item["line"])


def evidence_inventory() -> dict[str, Any]:
    ranking = read_json(RANKING_ROOT / "readiness.json")
    feature = read_json(FEATURE_ROOT / "input_readiness.json")
    investigation = read_json(INVESTIGATION_ROOT / "all_attempts_summary.json")
    ranking_missing = ranking.get("missing_or_ambiguous_dates") or ranking.get("missing_dates") or []
    feature_blocked = feature.get("strict_missing_features") or feature.get("blocked_features") or []
    investigation_dates = investigation.get("dates") or investigation.get("target_dates") or list((investigation.get("by_date") or {}).keys())
    return {
        "ranking_readiness": {
            "status": ranking.get("status") or ranking.get("decision"),
            "can_score": ranking.get("can_score"),
            "can_train": ranking.get("can_train"),
            "missing_or_ambiguous_dates": ranking_missing,
        },
        "feature_input_readiness": {
            "status": feature.get("status") or feature.get("decision") or feature.get("phase"),
            "can_score": feature.get("can_score"),
            "strict_missing_features": feature_blocked,
        },
        "missing_date_investigation": {
            "status": investigation.get("status") or investigation.get("decision"),
            "dates": investigation_dates,
            "source": rel(INVESTIGATION_ROOT),
            "decision": investigation.get("decision"),
        },
        "contract": {
            "schema": rel(CONTRACT_ROOT / "contract_schema.json"),
            "state_machine": rel(CONTRACT_ROOT / "state_machine.json"),
            "valid_day_policy": rel(CONTRACT_ROOT / "valid_day_policy.json"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build isolated, read-only MBCDS3 daily wiring preflight")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    out = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    if out.resolve() != DEFAULT_OUT.resolve():
        raise SystemExit(f"output must be the isolated MBCDS3 preflight root: {DEFAULT_OUT}")
    out.mkdir(parents=True, exist_ok=True)

    before = protected_fingerprints()
    source_text = ORCHESTRATOR.read_text(encoding="utf-8")
    cron_text = CRON.read_text(encoding="utf-8")
    tree = ast.parse(source_text, filename=str(ORCHESTRATOR))
    env_flags = sorted(line.split("=", 1)[0] for line in cron_text.splitlines() if line and not line.startswith("#") and "=" in line and not line.lstrip().startswith("*/"))
    inventory = {
        "schema_version": "mbcds3.daily_shadow_wiring_inventory.v1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "orchestrator": rel(ORCHESTRATOR),
        "cron": rel(CRON),
        "functions": function_inventory(tree),
        "call_sites": call_sites(tree),
        "cron_env_flags": env_flags,
        "existing_mbc3_flag_present": any("MBCDS3" in line for line in cron_text.splitlines()),
        "read_only": True,
    }
    write_json(out / "entrypoint_inventory.json", inventory)
    evidence = evidence_inventory()
    write_json(out / "evidence_inventory.json", evidence)
    write_json(out / "readiness.json", {
        "schema_version": "mbcds3.wiring_preflight.v1",
        "route": "MBCDS3-1_ISOLATED_DAILY_SHADOW_WIRING_DESIGN_PREFLIGHT",
        "generated_at": inventory["generated_at"],
        "status": "BLOCKED_PRODUCTION_WIRING_REQUIRES_SEPARATE_AUTHORIZATION",
        "design_ready": True,
        "daily_wiring": "NOT_STARTED",
        "ranking_chain_status": evidence["ranking_readiness"]["status"],
        "feature_input_status": evidence["feature_input_readiness"]["status"],
        "can_score": False,
        "can_train": False,
        "production_allowed": False,
        "no_publish": True,
        "blockers": [
            "MBCDS3 callback/accumulator is not wired into the production daily runner; separate authorization is required.",
            "MBCDS2 ranking chain is not closed for the three missing dates.",
            "Existing ranking candidates lack available_at and cannot count toward warm-up.",
        ],
    })

    insertion = {
        "schema_version": "mbcds3.daily_shadow_insertion_design.v1",
        "status": "DESIGN_ONLY_REQUIRES_FUTURE_PRODUCTION_WIRING_AUTHORIZATION",
        "safe_insertion_point": {
            "after": "same-run provider candidate and Model A ranking have passed",
            "before": "daily_chain_status persistence / DAPR18 downstream publication decisions",
            "reason": "MBCDS3 must observe the same run identity before downstream status is finalized",
        },
        "required_isolated_callback": "build_mbcds3_daily_shadow_candidate(asof, source_run_id, upstream_artifacts, output_root)",
        "required_outputs": [
            "daily_manifest.json", "model_a_ranking_ref.json", "model_b_feature_input_ref.json",
            "state.json", "pit_lineage.json", "checksum_manifest.json", "forbidden_scope_audit.json",
        ],
        "current_gap": "No MBCDS3 callback or accumulator is present in the production orchestrator.",
        "production_script_change_required": True,
        "blocker": "MBCDS3-1 cannot be considered wired until a separately authorized isolated callback is added; this preflight does not modify it.",
    }
    write_json(out / "insertion_point_design.json", insertion)

    state_matrix = {
        "schema_version": "mbcds3.daily_shadow_failure_matrix.v1",
        "terminal_states": ["VALID_DAY_ACCEPTED", "VALID_DAY_QUARANTINED", "BLOCKED"],
        "rows": [
            {"condition": "provider/source or same-run handoff missing", "state": "BLOCKED", "warmup_count_delta": 0, "downstream": "continue existing baseline; record isolated status"},
            {"condition": "non-trading or explicit historical unknown", "state": "VALID_DAY_QUARANTINED", "warmup_count_delta": 0, "downstream": "continue existing baseline"},
            {"condition": "Model A ranking incomplete, duplicate, mixed-date, or non-finite", "state": "BLOCKED", "warmup_count_delta": 0, "downstream": "no Model B input"},
            {"condition": "feature PIT/lineage/checksum gate fails", "state": "BLOCKED", "warmup_count_delta": 0, "downstream": "no score; never fallback"},
            {"condition": "all daily gates pass", "state": "VALID_DAY_ACCEPTED", "warmup_count_delta": 1, "downstream": "isolated accumulation only; score eligibility remains threshold-gated"},
        ],
        "invariants": ["no previous-day carry", "no fill or fallback", "no production/latest/provider/cron writes", "baseline status is independent of shadow status"],
    }
    write_json(out / "state_failure_matrix.json", state_matrix)

    future_safe = {
        "schema_version": "mbcds3.future_safe_boundary.v1",
        "allowed_in_future_wiring": ["isolated output root under mbcds3_*", "read-only upstream artifact references", "append-only accepted-day records", "explicit BLOCKED/QUARANTINED status"],
        "must_remain_forbidden": ["Model B scoring before warm-up gate", "training", "latest/provider/cron mutation", "strategy replay/order/target", "future labels or realized returns", "fallback across gaps"],
        "authorization_needed_before_change": ["production orchestrator source", "installed cron or actual crontab"],
    }
    write_json(out / "future_safe_boundary.json", future_safe)
    write_json(out / "protected_before.json", {"fingerprints": before})
    after = protected_fingerprints()
    write_json(out / "protected_after.json", {"fingerprints": after, "unchanged": before == after})

    forbidden = {
        "schema_version": "mbcds3.wiring_preflight.forbidden_scope.v1",
        "production_allowed": False, "scoring_performed": False, "training_performed": False,
        "cron_installed": False, "network_accessed": False, "production_paths_written": False,
        "output_root": rel(out), "protected_unchanged": before == after,
    }
    write_json(out / "forbidden_scope_audit.json", forbidden)
    report = "\n".join([
        "# MBCDS3-1 Daily Shadow Wiring Design/Preflight Execution Report", "",
        f"- generated_at: `{inventory['generated_at']}`", f"- output: `{rel(out)}`", "",
        "## Result", "",
        "- isolated discovery and wiring design completed",
        "- production wiring: `NOT_STARTED`",
        "- blocker: existing daily orchestrator has no MBCDS3 callback/accumulator; changing it requires separate authorization",
        "- Model B scoring/training: `NOT_PERFORMED`",
        "- cron/provider/latest/frontend/backend writes: `NONE`",
        f"- protected fingerprints unchanged: `{before == after}`", "",
        "## Future insertion", "",
        "The future callback belongs after same-run Model A ranking validation and before downstream status/publication decisions. It must emit an isolated terminal state for every run and never alter the existing baseline path.", "",
        "## Evidence", "",
        "- entrypoint_inventory.json", "- evidence_inventory.json", "- insertion_point_design.json", "- state_failure_matrix.json", "- future_safe_boundary.json", "- forbidden_scope_audit.json", "",
        f"Current gates remain ranking=`{evidence['ranking_readiness']['status']}` and feature=`{evidence['feature_input_readiness']['status']}`; no readiness is promoted by this preflight.", "",
    ])
    (out / "execution_report.md").write_text(report + "\n", encoding="utf-8")

    manifest = {}
    for path in sorted(out.iterdir()):
        if path.name == "checksum_manifest.json" or not path.is_file():
            continue
        manifest[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    write_json(out / "checksum_manifest.json", {"schema_version": "mbcds3.wiring_preflight.checksum.v1", "files": manifest})
    print(json.dumps({"status": "PASS_WITH_BLOCKER", "output": rel(out), "production_wiring_required": True, "protected_unchanged": before == after}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
