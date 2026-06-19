#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SIGNAL_ROOT = ROOT / "data_tw/artifacts/signals"
MODEL_IDS = [
    "e4_frozen_qlib_2023_2025_ltr",
    "fresh_qlib_2025_ltr",
    "fresh_qlib_adaptive",
    "frozen_qlib_2018_2022",
    "frozen_qlib_2025_ltr",
]
LTR_MODELS = {"e4_frozen_qlib_2023_2025_ltr", "fresh_qlib_2025_ltr", "frozen_qlib_2025_ltr"}
STRATEGIES = [
    "original",
    "top50_exit_all",
    "top50_exit_one_worst_sell",
    "one_sell_one_buy_correct",
    "one_sell_one_buy_buggy_e8r",
    "sector_extension_analysis_smoke",
    "dummy_new_strategy_dependency_smoke",
]
DEFAULT_MODEL_ID = "e4_frozen_qlib_2023_2025_ltr"
DEFAULT_STRATEGY_RULE_ID = "top50_exit_one_worst_sell"
ALLOWED_GATE_STATUSES = {
    "all_required_ready",
    "partial_data_pending",
    "no_new_data",
    "provider_failed",
    "validator_failed",
    "deadline_missed_keep_previous_latest",
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def choose_gate_status(sources: list[dict[str, Any]], validation: dict[str, Any], scenario: str) -> tuple[str, list[str], list[str]]:
    failure_reasons: list[str] = []
    retryable_sources: list[str] = []
    if scenario == "deadline_missed_keep_previous_latest":
        return "deadline_missed_keep_previous_latest", ["decision deadline missed; previous readonly latest preserved"], retryable_sources
    if scenario == "no_new_data":
        return "no_new_data", ["providers returned no new target_asof data; previous readonly latest preserved"], retryable_sources
    if scenario == "provider_failed":
        failed_sources = [s for s in sources if s.get("status") == "failed"]
        return (
            "provider_failed",
            [f"{s.get('source_id')}: {s.get('failure_reason')}" for s in failed_sources] or ["provider failed"],
            [str(s.get("source_id")) for s in failed_sources if s.get("retryable")],
        )
    if validation.get("ok") is not True:
        codes = {err.get("code") for err in validation.get("errors", [])}
        for source in sources:
            if source.get("failure_reason"):
                failure_reasons.append(f"{source.get('source_id')}: {source.get('failure_reason')}")
            if source.get("retryable") and source.get("status") in {"failed", "partial", "deadline_missed"}:
                retryable_sources.append(str(source.get("source_id")))
        if "forbidden_action_triggered" in codes or "available_at_after_decision_cutoff" in codes or "orthogonal_pit_audit_failed" in codes or "symbol_mapping_missing" in codes:
            return "validator_failed", failure_reasons or ["validator failed"], retryable_sources
        if "required_source_missing" in codes:
            return "validator_failed", failure_reasons or ["required source missing"], retryable_sources
        if "coverage_ratio_below_threshold" in codes:
            return "partial_data_pending", failure_reasons or ["partial data pending"], retryable_sources
        return "provider_failed", failure_reasons or ["provider staging validation failed"], retryable_sources
    provider_failed = [s for s in sources if s.get("status") == "failed"]
    if provider_failed:
        return "provider_failed", [f"{s.get('source_id')}: {s.get('failure_reason')}" for s in provider_failed], [str(s.get("source_id")) for s in provider_failed if s.get("retryable")]
    required_no_new_data = [s for s in sources if s.get("required") and s.get("status") == "no_new_data"]
    if required_no_new_data:
        return "no_new_data", [f"{s.get('source_id')}: {s.get('failure_reason') or 'no new target_asof data'}" for s in required_no_new_data], [str(s.get("source_id")) for s in required_no_new_data if s.get("retryable")]
    partial = [s for s in sources if s.get("required") and (s.get("status") == "partial" or float(s.get("coverage_ratio") or 0) < 1.0)]
    if partial:
        return "partial_data_pending", [f"{s.get('source_id')}: coverage incomplete" for s in partial], [str(s.get("source_id")) for s in partial if s.get("retryable")]
    return "all_required_ready", [], []


def model_row(model_id: str, gate_status: str, source_ids: set[str]) -> dict[str, Any]:
    model_type = "ltr" if model_id in LTR_MODELS else "qlib"
    required_sources = ["existing_signal_manifest"]
    if model_type == "ltr":
        required_sources += ["finmind_institutional_flow", "finmind_margin_short", "orthogonal_o2_features"]
    missing_sources = sorted(set(required_sources) - source_ids)
    manifest = SIGNAL_ROOT / model_id / "r1_legacy_signal_adapter_20260616/manifest.json"
    unavailable: list[str] = []
    if gate_status != "all_required_ready":
        unavailable.append(f"gate_status={gate_status}")
    if missing_sources:
        unavailable.append("missing_sources=" + ",".join(missing_sources))
    if not manifest.exists():
        unavailable.append("signal_manifest_missing")
    can_run = not unavailable
    return {
        "model_id": model_id,
        "model_type": model_type,
        "required_data_sources": required_sources,
        "required_feature_artifacts": ["orthogonal_o2_features"] if model_type == "ltr" else [],
        "required_signal_artifacts": [rel(manifest)],
        "train_window": "see configs/tw_replay_window_policy.yaml",
        "allowed_signal_window": "2026_ytd",
        "can_run_today": can_run,
        "unavailable_reason": "; ".join(unavailable),
    }


def strategy_row(strategy_rule_id: str, gate_status: str, model_types_ready: set[str]) -> dict[str, Any]:
    diagnostic_only = strategy_rule_id == "one_sell_one_buy_buggy_e8r"
    smoke_only = strategy_rule_id in {"sector_extension_analysis_smoke", "dummy_new_strategy_dependency_smoke"}
    production_selectable = not diagnostic_only and not smoke_only
    compatible_model_types = ["ltr", "qlib"]
    unavailable: list[str] = []
    if gate_status != "all_required_ready":
        unavailable.append(f"gate_status={gate_status}")
    if production_selectable and not model_types_ready:
        unavailable.append("no_ready_model_type")
    if diagnostic_only:
        unavailable.append("diagnostic_only_not_production_selectable")
    if smoke_only:
        unavailable.append("smoke_only_not_production_selectable")
    can_run = gate_status == "all_required_ready" and (production_selectable or diagnostic_only or smoke_only)
    return {
        "strategy_rule_id": strategy_rule_id,
        "strategy_role": "diagnostic" if diagnostic_only else ("smoke" if smoke_only else "production_candidate"),
        "required_inputs": ["date", "instrument", "candidate_rank", "buy_score", "full_qlib_rank", "signal_asof", "available_at", "price_fields", "fee_slippage_assumptions"],
        "compatible_model_types": compatible_model_types,
        "decision_output_schema": "readonly_order_intent_only",
        "can_run_today": can_run and bool(model_types_ready),
        "unavailable_reason": "; ".join(unavailable),
        "production_selectable": production_selectable,
        "diagnostic_only": diagnostic_only,
        "smoke_only": smoke_only,
    }


def build(staging_dir: Path, validation: dict[str, Any]) -> dict[str, Any]:
    pull_manifest = load_json(staging_dir / "provider_staging_pull_manifest.json")
    sources = pull_manifest.get("sources") or []
    scenario = str(pull_manifest.get("scenario", ""))
    gate_status, failure_reasons, retryable_sources = choose_gate_status(sources, validation, scenario)
    if gate_status not in ALLOWED_GATE_STATUSES:
        gate_status = "validator_failed"
        failure_reasons.append("invalid gate status normalized to validator_failed")
    previous_latest = str(pull_manifest.get("previous_readonly_latest", ""))
    proposed_readiness_asof = str(pull_manifest.get("target_asof", ""))
    committed_latest = previous_latest
    source_ids = {str(s.get("source_id")) for s in sources}
    models = [model_row(model_id, gate_status, source_ids) for model_id in MODEL_IDS]
    ready_model_types = {m["model_type"] for m in models if m["can_run_today"]}
    strategies = [strategy_row(rule_id, gate_status, ready_model_types) for rule_id in STRATEGIES]
    forbidden = load_json(staging_dir / "forbidden_action_audit.json") if (staging_dir / "forbidden_action_audit.json").exists() else {"actions": {}}
    price_source_policy = pull_manifest.get("price_source_policy") or {}
    manifest = {
        "schema_version": "v1.data_readiness_manifest.v1",
        "artifact_type": "data_readiness_gate",
        "run_id": pull_manifest.get("run_id"),
        "target_asof": pull_manifest.get("target_asof"),
        "decision_for": pull_manifest.get("decision_for"),
        "decision_cutoff": pull_manifest.get("decision_cutoff"),
        "gate_status": gate_status,
        "previous_readonly_latest": previous_latest,
        "committed_readonly_latest": committed_latest,
        "gate_allows_downstream_readonly_latest_update": gate_status == "all_required_ready",
        "proposed_readiness_asof": proposed_readiness_asof if gate_status == "all_required_ready" else "",
        "actual_readonly_latest_updated": False,
        "sources": sources,
        "price_source_policy": price_source_policy,
        "price_fallback_used": bool(price_source_policy.get("fallback_used")),
        "forbidden_action_audit": forbidden,
        "failure_reasons": failure_reasons,
        "retryable_sources": sorted(set(retryable_sources)),
        "created_at": now(),
        "created_by": "scripts/build_tw_data_readiness_gate.py",
        "staging_only": True,
        "updates_readonly_latest": False,
        "readonly_latest_preserved": True,
    }
    matrix = {
        "schema_version": "v1.model_strategy_availability_matrix.v1",
        "artifact_type": "model_strategy_availability_matrix",
        "run_id": pull_manifest.get("run_id"),
        "target_asof": pull_manifest.get("target_asof"),
        "decision_for": pull_manifest.get("decision_for"),
        "default_model_id": DEFAULT_MODEL_ID,
        "default_strategy_rule_id": DEFAULT_STRATEGY_RULE_ID,
        "models": models,
        "strategies": strategies,
    }
    write_json(staging_dir / "data_readiness_manifest.json", manifest)
    write_json(staging_dir / "model_strategy_availability_matrix.json", matrix)
    return {"ok": True, "gate_status": gate_status, "manifest": rel(staging_dir / "data_readiness_manifest.json"), "matrix": rel(staging_dir / "model_strategy_availability_matrix.json")}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Phase V1 DataReadinessGate artifacts from provider staging data.")
    parser.add_argument("--staging-dir", "--artifact-path", dest="staging_dir", required=True)
    parser.add_argument("--validation-result", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    staging_dir = Path(args.staging_dir)
    if not staging_dir.is_absolute():
        staging_dir = ROOT / staging_dir
    validation = load_json(Path(args.validation_result)) if args.validation_result else {"ok": True, "errors": []}
    result = build(staging_dir, validation)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result["manifest"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
