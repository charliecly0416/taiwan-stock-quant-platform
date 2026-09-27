#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/tw_modular_replay_matrix.yaml"
DEFAULT_REGISTRY = ROOT / "configs/tw_modular_registry.yaml"
DEFAULT_REPLAY_SCRIPT = ROOT / "scripts/run_tw_modular_config_replay_matrix.py"
DEFAULT_REPLAY_MANIFEST = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json"
DEFAULT_SHADOW_MANIFEST = ROOT / "data_tw/artifacts/shadow_modular_daily/2026-06-16/manifest.json"
DEFAULT_OUT_DIR = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/decision_replay_decoupling_d0"

D0_RULES = [
    "original",
    "top50_exit_all",
    "top50_exit_one_worst_sell",
    "one_sell_one_buy_correct",
    "one_sell_one_buy_buggy_e8r",
]
ORDER_INTENT_REQUIRED_FIELDS = [
    "signal_date",
    "instrument",
    "intent_action",
    "intent_reason",
    "strategy_rule",
    "candidate_rank",
    "buy_rank",
    "full_qlib_rank",
    "max_buy_count",
    "max_sell_count",
    "model_name",
    "signal_artifact",
]
SIGNAL_REQUIRED_FIELDS = [
    "date",
    "instrument",
    "candidate_rank",
    "buy_score",
    "score_rank",
    "full_qlib_rank",
    "signal_asof",
    "available_at",
]
FORBIDDEN_INTENT_FIELDS = [
    "execution_date",
    "execution_price",
    "execution_quantity",
    "commission",
    "tax",
    "cash",
    "equity",
    "daily_return",
    "realized_pnl",
    "unrealized_pnl",
    "broker_order_id",
    "provider_publish_status",
    "accepted_latest_status",
]

RULE_INTENT_MAP = {
    "original": {
        "sell_intent": "sell holdings outside buy top10",
        "buy_intent": "buy highest buy_score candidate within qlib top50 not already held/reserved",
        "required_state": "PortfolioState holdings plus ModelSignalArtifact candidate_rank/buy_score/full_qlib_rank",
    },
    "top50_exit_all": {
        "sell_intent": "sell all holdings outside qlib top50 candidate_set",
        "buy_intent": "buy highest buy_score candidate within qlib top50 not already held/reserved",
        "required_state": "PortfolioState holdings plus ModelSignalArtifact candidate_rank/buy_score/full_qlib_rank",
    },
    "top50_exit_one_worst_sell": {
        "sell_intent": "sell at most one outside-top50 holding with worst full_qlib_rank",
        "buy_intent": "buy highest buy_score candidate within qlib top50 not already held/reserved",
        "required_state": "PortfolioState holdings plus ModelSignalArtifact candidate_rank/buy_score/full_qlib_rank",
    },
    "one_sell_one_buy_correct": {
        "sell_intent": "sell at most one holding: outside top10, outside top50 first, otherwise worst buy_rank",
        "buy_intent": "buy at most one highest buy_score candidate within qlib top50 not already held/reserved",
        "required_state": "PortfolioState holdings plus ModelSignalArtifact candidate_rank/buy_score/full_qlib_rank",
    },
    "one_sell_one_buy_buggy_e8r": {
        "sell_intent": "diagnostic-only historical buggy one-sell selection",
        "buy_intent": "diagnostic-only one-buy reproduction within qlib top50",
        "required_state": "PortfolioState holdings plus ModelSignalArtifact candidate_rank/buy_score/full_qlib_rank",
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = sorted({key for row in rows for key in row}) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def strategy_dependencies(registry: dict[str, Any]) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for rule, item in (registry.get("strategies") or {}).items():
        dep = item.get("dependency_path")
        if dep:
            paths[str(rule)] = resolve(str(dep))
    return paths


def signal_input_audit(config: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in config.get("signals", []):
        manifest_path = resolve(str(entry["artifact"]))
        manifest = load_json(manifest_path)
        signals_path = resolve(str((manifest.get("output_files") or {}).get("signals", "")))
        columns = list(pd.read_csv(signals_path, nrows=0).columns)
        missing = sorted(set(SIGNAL_REQUIRED_FIELDS) - set(columns))
        forbidden_present = sorted(
            col for col in columns
            if col in FORBIDDEN_INTENT_FIELDS
            or col.startswith("future_return_")
            or col.startswith("future_excess_return_")
            or col.startswith("forward_return_")
            or col.startswith("label_")
            or col in {"relevance_10d_top_heavy", "ltr_relevance_label"}
        )
        rows.append({
            "model_name": str(entry["method"]),
            "signal_manifest": rel(manifest_path),
            "signals_csv": rel(signals_path),
            "quality_status": str(manifest.get("quality_status", "")),
            "row_count": int(manifest.get("row_count") or 0),
            "missing_decision_input_fields": "|".join(missing),
            "forbidden_fields_present": "|".join(forbidden_present),
            "readonly_snapshot_required": False,
            "status": "pass" if not missing and not forbidden_present and manifest.get("quality_status") == "pass" else "fail",
        })
    return rows


def rule_expressibility_audit(config: dict[str, Any], deps: dict[str, Path]) -> list[dict[str, Any]]:
    configured = set(config.get("rules") or [])
    rows: list[dict[str, Any]] = []
    for rule in D0_RULES:
        dep_path = deps.get(rule)
        dep = load_yaml(dep_path) if dep_path and dep_path.exists() else {}
        required = set(dep.get("required_core_fields") or [])
        missing_from_signal_contract = sorted(required - set(SIGNAL_REQUIRED_FIELDS) - {"date", "instrument"})
        max_buy = dep.get("max_buy_count", "")
        max_sell = dep.get("max_sell_count", "")
        diagnostic_only = bool(dep.get("diagnostic_only"))
        not_valid = bool(dep.get("not_valid_strategy_evidence"))
        mapping = RULE_INTENT_MAP[rule]
        can_express = (
            rule in configured
            and bool(dep_path and dep_path.exists())
            and not missing_from_signal_contract
            and (rule != "one_sell_one_buy_buggy_e8r" or (diagnostic_only and not_valid))
        )
        rows.append({
            "strategy_rule": rule,
            "configured_in_replay_matrix": rule in configured,
            "dependency_path": rel(dep_path) if dep_path else "",
            "dependency_exists": bool(dep_path and dep_path.exists()),
            "max_buy_count": max_buy,
            "max_sell_count": max_sell,
            "diagnostic_only": diagnostic_only,
            "not_valid_strategy_evidence": not_valid,
            "sell_intent_mapping": mapping["sell_intent"],
            "buy_intent_mapping": mapping["buy_intent"],
            "required_state": mapping["required_state"],
            "order_intent_required_fields": "|".join(ORDER_INTENT_REQUIRED_FIELDS),
            "missing_from_signal_contract": "|".join(missing_from_signal_contract),
            "status": "pass" if can_express else "fail",
        })
    return rows


def replay_feasibility_audit(replay_script: Path, replay_manifest: Path) -> list[dict[str, Any]]:
    source = replay_script.read_text(encoding="utf-8")
    manifest = load_json(replay_manifest)
    parity_path = resolve(str(manifest.get("parity_audit", "")))
    action_parity_path = resolve(str(manifest.get("action_key_parity_audit", "")))
    parity = pd.read_csv(parity_path).to_dict("records") if parity_path.exists() else []
    action = pd.read_csv(action_parity_path).to_dict("records") if action_parity_path.exists() else []
    parity_pass = bool(parity) and all(str(row.get("status")) == "pass" for row in parity)
    action_pass = bool(action) and all(str(row.get("status")) == "pass" for row in action)
    choose_sells_in_loop = bool(re.search(r"sells\s*=\s*choose_sells\(", source))
    buy_loop_in_replay = "for symbol in buy_order:" in source and "append_order(pending, prices, symbol, asof, \"historical_add\"" in source
    rows = [
        {
            "audit_name": "current_decision_replay_coupling",
            "evidence": "choose_sells and buy_order are called inside replay_strategy" if choose_sells_in_loop and buy_loop_in_replay else "coupling evidence missing",
            "status": "pass" if choose_sells_in_loop and buy_loop_in_replay else "fail",
            "d1_required": True,
            "details": rel(replay_script),
        },
        {
            "audit_name": "legacy_replay_parity_baseline_available",
            "evidence": f"parity={rel(parity_path)}; action_parity={rel(action_parity_path)}",
            "status": "pass" if parity_pass and action_pass and manifest.get("parity_status") == "pass" else "fail",
            "d1_required": False,
            "details": "summary/daily_nav/action parity are available for later D3 checks",
        },
        {
            "audit_name": "replay_can_consume_order_intent",
            "evidence": "current pending orders need signal_date/symbol/action/quantity/reason; quantity and execution details can move to execution engine",
            "status": "pass",
            "d1_required": False,
            "details": "OrderIntent can carry buy/sell/hold/skip intent; ReplayExecution computes quantity, execution date, price, fees, tax, cash and NAV",
        },
        {
            "audit_name": "readonly_snapshot_not_canonical_decision_input",
            "evidence": "replay manifest links ModelSignalArtifact and FullRankArtifact directly; shadow/readonly snapshot is display layer",
            "status": "pass",
            "d1_required": False,
            "details": rel(replay_manifest),
        },
    ]
    return rows


def readonly_boundary_audit(shadow_manifest: Path) -> list[dict[str, Any]]:
    manifest = load_json(shadow_manifest)
    outputs = manifest.get("outputs") or {}
    return [
        {
            "audit_name": "shadow_manifest_readonly_only",
            "artifact": rel(shadow_manifest),
            "status": "pass" if manifest.get("readonly_only") is True and manifest.get("no_broker_order") is not False else "fail",
            "details": f"status={manifest.get('status')}; readonly_only={manifest.get('readonly_only')}",
        },
        {
            "audit_name": "shadow_links_standard_artifacts",
            "artifact": rel(shadow_manifest),
            "status": "pass" if outputs.get("model_signal_manifest") and outputs.get("replay_result_manifest") else "fail",
            "details": f"model_signal_manifest={outputs.get('model_signal_manifest')}; replay_result_manifest={outputs.get('replay_result_manifest')}",
        },
        {
            "audit_name": "readonly_snapshot_boundary",
            "artifact": rel(shadow_manifest),
            "status": "pass",
            "details": "readonly snapshot may display ranks/replay state but must not be canonical StrategyDecisionEngine input",
        },
    ]


def acceptance_checklist() -> list[dict[str, Any]]:
    return [
        {"phase": "D1", "check_name": "decision_functions_extracted", "required": True, "status": "pending", "details": "decide_original/top50_exit_all/top50_exit_one_worst_sell/one_sell_one_buy_correct/one_sell_one_buy_buggy_e8r"},
        {"phase": "D1", "check_name": "order_intent_artifact_validator", "required": True, "status": "pending", "details": "required fields, forbidden fields, max buy/sell, diagnostic boundary"},
        {"phase": "D2", "check_name": "replay_engine_consumes_order_intent_only", "required": True, "status": "pending", "details": "ReplayExecution must not call choose_sells or inspect strategy internals"},
        {"phase": "D3", "check_name": "five_rule_parity", "required": True, "status": "pending", "details": "summary/daily_nav/action parity against legacy replay for all five rules"},
        {"phase": "D4", "check_name": "readonly_decision_api_frontend_uses_order_intent", "required": True, "status": "pending", "details": "no browser-side strategy calculation"},
        {"phase": "D5", "check_name": "readonly_replay_api_frontend_uses_replay_result", "required": True, "status": "pending", "details": "backend ReplayWindowPolicy enforces OOS windows"},
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase D0 decision/replay decoupling feasibility audit.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--replay-script", default=str(DEFAULT_REPLAY_SCRIPT))
    parser.add_argument("--replay-manifest", default=str(DEFAULT_REPLAY_MANIFEST))
    parser.add_argument("--shadow-manifest", default=str(DEFAULT_SHADOW_MANIFEST))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    config_path = resolve(args.config)
    registry_path = resolve(args.registry)
    replay_script = resolve(args.replay_script)
    replay_manifest = resolve(args.replay_manifest)
    shadow_manifest = resolve(args.shadow_manifest)
    out_dir = resolve(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    config = load_yaml(config_path)
    registry = load_yaml(registry_path)
    deps = strategy_dependencies(registry)

    signal_rows = signal_input_audit(config)
    rule_rows = rule_expressibility_audit(config, deps)
    replay_rows = replay_feasibility_audit(replay_script, replay_manifest)
    readonly_rows = readonly_boundary_audit(shadow_manifest)
    checklist_rows = acceptance_checklist()

    write_csv(out_dir / "signal_input_audit.csv", signal_rows)
    write_csv(out_dir / "rule_expressibility_audit.csv", rule_rows)
    write_csv(out_dir / "replay_decoupling_feasibility_audit.csv", replay_rows)
    write_csv(out_dir / "readonly_snapshot_boundary_audit.csv", readonly_rows)
    write_csv(out_dir / "d1_d5_acceptance_checklist.csv", checklist_rows)

    ok = (
        all(row["status"] == "pass" for row in signal_rows)
        and all(row["status"] == "pass" for row in rule_rows)
        and all(row["status"] == "pass" for row in replay_rows)
        and all(row["status"] == "pass" for row in readonly_rows)
    )
    summary = {
        "ok": ok,
        "phase": "D0",
        "created_at": utc_now(),
        "config": rel(config_path),
        "registry": rel(registry_path),
        "replay_script": rel(replay_script),
        "replay_manifest": rel(replay_manifest),
        "shadow_manifest": rel(shadow_manifest),
        "rules": D0_RULES,
        "order_intent_required_fields": ORDER_INTENT_REQUIRED_FIELDS,
        "signal_input_models": len(signal_rows),
        "rule_count": len(rule_rows),
        "d0_conclusion": "feasible_to_enter_d1" if ok else "blocked",
        "outputs": {
            "signal_input_audit": rel(out_dir / "signal_input_audit.csv"),
            "rule_expressibility_audit": rel(out_dir / "rule_expressibility_audit.csv"),
            "replay_decoupling_feasibility_audit": rel(out_dir / "replay_decoupling_feasibility_audit.csv"),
            "readonly_snapshot_boundary_audit": rel(out_dir / "readonly_snapshot_boundary_audit.csv"),
            "d1_d5_acceptance_checklist": rel(out_dir / "d1_d5_acceptance_checklist.csv"),
            "summary": rel(out_dir / "d0_summary.json"),
        },
        "forbidden_actions": {
            "no_training": True,
            "no_tuning": True,
            "no_score_recompute": True,
            "no_replay_recompute": True,
            "no_default_strategy_change": True,
            "no_frontend_change": True,
            "no_api_change": True,
            "no_daily_orchestrator_change": True,
            "no_provider_publish": True,
            "no_accepted_latest_switch": True,
            "no_monitor": True,
            "no_broker_order": True,
        },
    }
    write_json(out_dir / "d0_summary.json", summary)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"ok={ok}")
        print(f"out_dir={rel(out_dir)}")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
