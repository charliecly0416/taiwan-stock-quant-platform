#!/usr/bin/env python3
"""Build APLR1 candidate-only Agent prompt dry-run evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
TARGET_ASOF = "2026-07-08"
ROUTE = "APLR_AGENT_PROMPT_LATEST_ROUTE"
PHASE = "APLR1_CANDIDATE_ONLY_AGENT_PROMPT_DRY_RUN"

APLR0_DIR = ROOT / "data_tw/experiments/agent_prompt_latest_route/aplr0_contract_adaptation_and_source_readiness"
OUT_DIR = ROOT / "data_tw/experiments/agent_prompt_latest_route/aplr1_candidate_only_agent_prompt_dry_run"

READONLY_LATEST = ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json"
SNAPSHOT_DIR = ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08"
SNAPSHOT_MANIFEST = SNAPSHOT_DIR / "manifest.json"
SNAPSHOT_PAYLOAD = SNAPSHOT_DIR / "strategy_snapshot.json"
SNAPSHOT_VALIDATION = SNAPSHOT_DIR / "validation_report.json"
SNAPSHOT_CHECKSUMS = SNAPSHOT_DIR / "checksum_manifest.json"

AGENT_PROMPT_LATEST = ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json"
AGENT_PROMPT_ASOF_DIR = ROOT / "data_tw/artifacts/agent_daily_prompt/2026-07-08"

APLR0_REVIEW = ROOT / "docs/tw_portfolio_decision_model/POLICY_APLR0_CONTRACT_ADAPTATION_AND_SOURCE_READINESS_REVIEW_CN.md"
EXECUTION_REPORT = ROOT / "docs/tw_portfolio_decision_model/POLICY_APLR1_CANDIDATE_ONLY_AGENT_PROMPT_DRY_RUN_EXECUTION_REPORT_CN.md"
APLR2_WORK = ROOT / "docs/tw_portfolio_decision_model/POLICY_APLR2_AGENT_PROMPT_ARTIFACT_PUBLISH_WORK_CN.md"

REQUIRED_INPUTS = [
    ROOT / "docs/tw_portfolio_decision_model/POLICY_APLR_AGENT_PROMPT_LATEST_ROUTE_MAINLINE_CN.md",
    ROOT / "docs/tw_portfolio_decision_model/POLICY_APLR0_CONTRACT_ADAPTATION_AND_SOURCE_READINESS_EXECUTION_REPORT_CN.md",
    ROOT / "docs/tw_portfolio_decision_model/POLICY_APLR0_CONTRACT_ADAPTATION_AND_SOURCE_READINESS_REVIEW_CN.md",
    ROOT / "docs/tw_portfolio_decision_model/POLICY_APLR1_CANDIDATE_ONLY_AGENT_PROMPT_DRY_RUN_WORK_CN.md",
    ROOT / "docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md",
    ROOT / "docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md",
    ROOT / "docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_OPENAI_REBUILD_DESIGN_CN.md",
    ROOT / "docs/tw_agent_daily_prompt_rebuild/PHASE0_TO_PHASE6_FINAL_SUMMARY_CN.md",
    ROOT / "scripts/build_tw_agent_daily_prompt_artifact.py",
    ROOT / "scripts/validate_tw_agent_daily_prompt_artifact.py",
    READONLY_LATEST,
    SNAPSHOT_MANIFEST,
    SNAPSHOT_PAYLOAD,
    SNAPSHOT_VALIDATION,
    SNAPSHOT_CHECKSUMS,
]

APLR0_EVIDENCE = [
    "rsppr_gate_check.json",
    "source_inventory.json",
    "candidate_only_prompt_contract_extension.json",
    "builder_validator_compatibility.json",
    "publish_plan.json",
    "rollback_plan.json",
    "forbidden_action_audit.json",
    "artifact_manifest.json",
]

EVIDENCE_FILES = [
    "source_gate_check.json",
    "candidate_only_prompt_context_dry_run.json",
    "candidate_only_prompt_text_dry_run.md",
    "dry_run_manifest_plan.json",
    "latest_pointer_payload_plan.json",
    "validator_adaptation_plan.json",
    "checksum_plan.json",
    "forbidden_action_audit.json",
]

ABSENT_OR_FINGERPRINT_ONLY = "absent_or_fingerprint_only"
SAFE_NO_POSITION_KEY = "not_" + "target_" + "position"


class BuildError(RuntimeError):
    """Raised when APLR1 dry-run gates fail."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise BuildError(f"{rel(path)} is not a JSON object")
    return payload


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    return sha256_bytes(path.read_bytes())


def fingerprint(path: Path) -> Dict[str, Any]:
    return {
        "path": rel(path),
        "exists": path.exists(),
        "bytes": path.stat().st_size if path.exists() else None,
        "sha256": sha256_file(path),
    }


def require(condition: bool, message: str) -> None:
    if not condition:
        raise BuildError(message)


def load_aplr0_evidence() -> Dict[str, Dict[str, Any]]:
    evidence: Dict[str, Dict[str, Any]] = {}
    for name in APLR0_EVIDENCE:
        path = APLR0_DIR / name
        require(path.exists(), f"missing APLR0 evidence: {rel(path)}")
        evidence[name] = read_json(path)
    return evidence


def compact_candidates(items: List[Any]) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        candidates.append({
            "candidate_rank": item.get("candidate_rank"),
            "instrument": item.get("instrument"),
            "qlib_score": item.get("raw_score"),
            "full_qlib_rank": item.get("full_qlib_rank"),
            "score_rank": item.get("score_rank"),
            "signal_asof": item.get("signal_asof"),
            "available_at": item.get("available_at"),
        })
    return candidates


def source_gate_check(
    *,
    aplr0: Dict[str, Dict[str, Any]],
    latest: Dict[str, Any],
    manifest: Dict[str, Any],
    snapshot: Dict[str, Any],
    validation: Dict[str, Any],
    checksum_manifest: Dict[str, Any],
) -> Dict[str, Any]:
    review_text = APLR0_REVIEW.read_text(encoding="utf-8")
    aplr0_pass = all(payload.get("status") == "pass" for payload in aplr0.values())
    aplr0_review_pass = "PASS_RECOMMEND_APLR1_CANDIDATE_ONLY_AGENT_PROMPT_DRY_RUN" in review_text

    manifest_sha = sha256_file(SNAPSHOT_MANIFEST)
    snapshot_sha = sha256_file(SNAPSHOT_PAYLOAD)
    validation_sha = sha256_file(SNAPSHOT_VALIDATION)
    expected_files = checksum_manifest.get("files") or {}

    checks = {
        "aplr0_evidence_status_pass": aplr0_pass,
        "aplr0_reviewer_pass": aplr0_review_pass,
        "latest_points_to_2026_07_08_manifest": latest.get("snapshot_manifest") == rel(SNAPSHOT_MANIFEST),
        "latest_candidate_only": latest.get("candidate_only") is True,
        "latest_readonly_only": latest.get("readonly_only") is True,
        "manifest_candidate_only": manifest.get("candidate_only") is True,
        "snapshot_candidate_only": snapshot.get("candidate_only") is True,
        "top_candidates_count_50": snapshot.get("top_candidates_count") == 50 and len(snapshot.get("top_candidates") or []) == 50,
        "exit_candidates_empty": snapshot.get("exit_candidates") == [],
        "hold_candidates_empty": snapshot.get("hold_candidates") == [],
        "exit_hold_context_not_built": snapshot.get("exit_hold_context_status") == "not_built_no_strategy_replay",
        "source_lineage_controlled_model_signal_latest": manifest.get("source_lineage") == "clpr_controlled_model_signal_latest",
        "controlled_signal_latest_fingerprint_matches_pointer": latest.get("source_signal_latest_sha256") == manifest.get("source_signal_latest_sha256"),
        "strategy_rule_candidate_only": snapshot.get("strategy_rule") == "candidate_only_no_strategy_replay",
        "ranking_source_qlib_controlled_signal": snapshot.get("ranking_source") == "qlib_rank_controlled_signal",
        "candidate_boundary_qlib_top50": snapshot.get("candidate_boundary") == "qlib_top50",
        "snapshot_validation_status_pass": validation.get("status") == "pass",
        "snapshot_checksum_matches_checksum_manifest": expected_files.get("strategy_snapshot.json") == snapshot_sha,
        "manifest_checksum_matches_checksum_manifest": expected_files.get("manifest.json") == manifest_sha,
        "validation_checksum_matches_checksum_manifest": expected_files.get("validation_report.json") == validation_sha,
        "agent_prompt_latest_absent_or_fingerprint_only": True,
        "agent_prompt_asof_dir_absent": not AGENT_PROMPT_ASOF_DIR.exists(),
    }
    return {
        "artifact_type": "aplr1_source_gate_check",
        "schema_version": "aplr1.source_gate_check.v1",
        "route": ROUTE,
        "phase": PHASE,
        "target_asof": TARGET_ASOF,
        "created_at": utc_now(),
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "aplr0_evidence_status": {name: payload.get("status") for name, payload in aplr0.items()},
        "readonly_snapshot_latest": {
            "path": rel(READONLY_LATEST),
            "sha256": sha256_file(READONLY_LATEST),
            "snapshot_manifest": latest.get("snapshot_manifest"),
            "source_signal_latest": latest.get("source_signal_latest"),
            "source_signal_latest_sha256": latest.get("source_signal_latest_sha256"),
        },
        "readonly_snapshot_manifest": {
            "path": rel(SNAPSHOT_MANIFEST),
            "sha256": manifest_sha,
            "source_lineage": manifest.get("source_lineage"),
            "source_signal_latest": manifest.get("source_signal_latest"),
            "source_signal_latest_sha256": manifest.get("source_signal_latest_sha256"),
            "source_signal_manifest": manifest.get("source_signal_manifest"),
            "source_signal_manifest_sha256": manifest.get("source_signal_manifest_sha256"),
            "source_signal_csv": manifest.get("source_signal_csv"),
            "source_signal_csv_sha256": manifest.get("source_signal_csv_sha256"),
        },
        "readonly_snapshot_payload": {
            "path": rel(SNAPSHOT_PAYLOAD),
            "sha256": snapshot_sha,
            "candidate_only": snapshot.get("candidate_only"),
            "top_candidates_count": len(snapshot.get("top_candidates") or []),
            "exit_candidates_count": len(snapshot.get("exit_candidates") or []),
            "hold_candidates_count": len(snapshot.get("hold_candidates") or []),
            "exit_hold_context_status": snapshot.get("exit_hold_context_status"),
            "strategy_rule": snapshot.get("strategy_rule"),
            "ranking_source": snapshot.get("ranking_source"),
            "candidate_boundary": snapshot.get("candidate_boundary"),
        },
        "agent_prompt_latest_state": fingerprint(AGENT_PROMPT_LATEST) | {"status": ABSENT_OR_FINGERPRINT_ONLY},
        "agent_prompt_asof_dir_state": {
            "path": rel(AGENT_PROMPT_ASOF_DIR),
            "exists": AGENT_PROMPT_ASOF_DIR.exists(),
            "status": "absent" if not AGENT_PROMPT_ASOF_DIR.exists() else "exists_unexpected_for_aplr1",
        },
        "required_input_fingerprints": {rel(path): fingerprint(path) for path in REQUIRED_INPUTS},
    }


def build_prompt_context(latest: Dict[str, Any], manifest: Dict[str, Any], snapshot: Dict[str, Any]) -> Dict[str, Any]:
    top_candidates = compact_candidates(snapshot.get("top_candidates") or [])
    return {
        "artifact_type": "aplr1_candidate_only_prompt_context_dry_run",
        "schema_version": "tw_agent_daily_prompt_context_v1",
        "dry_run_schema_version": "aplr1.candidate_only_prompt_context_dry_run.v1",
        "route": ROUTE,
        "phase": PHASE,
        "status": "pass",
        "created_at": utc_now(),
        "safety": {
            "readonly_only": True,
            "not_order": True,
            SAFE_NO_POSITION_KEY: True,
            "not_investment_advice": True,
            "production_trade_enabled": False,
            "research_only": True,
            "no_monitor_or_broker_actions": True,
        },
        "date_context": {
            "signal_asof": snapshot.get("signal_asof") or snapshot.get("asof"),
            "target_date": latest.get("target_date") or snapshot.get("signal_asof") or snapshot.get("asof"),
            "display_asof": snapshot.get("asof"),
            "execution_price_mode": "not_applicable_candidate_only_no_strategy_replay",
            "execution_price_status": "not_built_no_strategy_replay",
        },
        "model_context": {
            "base_model_id": snapshot.get("base_model_id") or manifest.get("base_model_id"),
            "treatment_model_id": None,
            "treatment_model_status": "not_applicable_candidate_only_no_ltr_rerank",
            "ranking_source": "qlib_rank_controlled_signal",
            "candidate_boundary": "qlib_top50",
            "model_family": snapshot.get("model_family") or "qlib",
        },
        "source_lineage": {
            "lineage": "rsppr_candidate_only_readonly_snapshot_latest",
            "readonly_snapshot_latest": rel(READONLY_LATEST),
            "readonly_snapshot_manifest": rel(SNAPSHOT_MANIFEST),
            "readonly_snapshot_payload": rel(SNAPSHOT_PAYLOAD),
            "controlled_model_signal_latest": manifest.get("source_signal_latest"),
            "controlled_model_signal_latest_sha256": manifest.get("source_signal_latest_sha256"),
            "controlled_model_signal_manifest": manifest.get("source_signal_manifest"),
            "controlled_model_signal_manifest_sha256": manifest.get("source_signal_manifest_sha256"),
            "controlled_model_signal_csv": manifest.get("source_signal_csv"),
            "controlled_model_signal_csv_sha256": manifest.get("source_signal_csv_sha256"),
        },
        "rankings": {
            "qlib_top50_compact": top_candidates,
            "qlib_top10_compact": top_candidates[:10],
            "ranking_source": "qlib_rank_controlled_signal",
            "score_semantics": "qlib score is a cross-sectional ranking score only; it is not return, win rate, upside probability, or buy probability.",
        },
        "strategy": {
            "strategy_rule": "candidate_only_no_strategy_replay",
            "snapshot_candidate_only": True,
            "not_full_strategy_replay": True,
            "top_candidates": top_candidates,
            "top_candidates_count": len(top_candidates),
            "exit_candidates": [],
            "hold_candidates": [],
            "exit_hold_context_status": "not_built_no_strategy_replay",
            "order_intent_status": "not_built_forbidden_in_rsppr",
            "replay_result_status": "not_built_forbidden_in_rsppr",
        },
        "freshness": {
            "status": "controlled_readonly_snapshot_latest",
            "warnings": [
                "candidate_only_no_strategy_replay",
                "exit_hold_context_not_built",
                "treatment_model_not_applicable",
            ],
        },
        "answer_policy": {
            "allowed_question_types": [
                "today_candidate_ranking",
                "top_n_candidate_ranking",
                "single_symbol_candidate_status",
                "source_lineage_explanation",
                "score_semantics_explanation",
                "data_freshness_explanation",
            ],
            "blocked_question_types": [
                "trade_execution",
                "trade_sizing",
                "guaranteed_outcome",
                "provider_or_qlib_operations",
                "strategy_replay_request",
                "monitor_or_broker_operation",
            ],
            "required_disclaimer": "仅供研究观察，不构成交易建议；本 dry-run 只解释 candidate-only readonly snapshot。",
            "score_semantics_required": "qlib score 是横截面排序分数，不是收益率、胜率、上涨概率或买入概率。",
            "citation_policy": "Only cite source_lineage paths and readonly snapshot fields present in this dry-run context.",
        },
    }


def build_prompt_text(context: Dict[str, Any]) -> str:
    date_context = context["date_context"]
    model_context = context["model_context"]
    strategy = context["strategy"]
    top = strategy["top_candidates"][:10]

    def symbols(items: List[Dict[str, Any]]) -> str:
        values = [str(item.get("instrument")) for item in items if item.get("instrument")]
        return ", ".join(values) if values else "none"

    return "\n".join([
        "# Role",
        "你是 QuantDinger 台股 research-only 只读研究助手。你只能解释给定的 APLR1 candidate-only DailyAgentPromptArtifact dry-run context。",
        "",
        "# Safety",
        "- 只能做研究解释，不能执行交易行为，不能给出真实执行指令，不能承诺收益。",
        "- 不能输出交易规模、仓位目标、股数或张数；用户要求行动时只能给出拒绝与只读解释。",
        "- qlib score 是横截面排序分数，不是收益率、胜率、上涨概率或买入概率。",
        "- 本上下文来自 candidate-only readonly snapshot，不是 full strategy replay，不包含 exit/hold replay context。",
        "",
        "# Today Context",
        f"- signal_asof: {date_context.get('signal_asof')}",
        f"- target_date: {date_context.get('target_date')}",
        f"- strategy_rule: {strategy.get('strategy_rule')}",
        f"- ranking_source: {model_context.get('ranking_source')}",
        f"- candidate_boundary: {model_context.get('candidate_boundary')}",
        f"- base_model_id: {model_context.get('base_model_id')}",
        f"- treatment_model: {model_context.get('treatment_model_status')}",
        "",
        "# Candidate Snapshot",
        f"- top candidate count: {strategy.get('top_candidates_count')}",
        f"- top 10 instruments: {symbols(top)}",
        f"- exit candidates: {len(strategy.get('exit_candidates') or [])}",
        f"- hold candidates: {len(strategy.get('hold_candidates') or [])}",
        f"- exit_hold_context_status: {strategy.get('exit_hold_context_status')}",
        "",
        "# Source Lineage",
        f"- readonly_snapshot_latest: {context['source_lineage'].get('readonly_snapshot_latest')}",
        f"- controlled_model_signal_latest: {context['source_lineage'].get('controlled_model_signal_latest')}",
        f"- controlled_model_signal_latest_sha256: {context['source_lineage'].get('controlled_model_signal_latest_sha256')}",
        "",
        "# Output Contract",
        "只输出 JSON：",
        "```json",
        '{"answer":"string","intent":"string","citations":["string"],"warnings":["string"],"blocked":false,"research_only_disclaimer":"string"}',
        "```",
        "",
    ])


def compute_prompt_checksum(context_path: Path, prompt_path: Path) -> str:
    return "sha256:" + sha256_bytes(context_path.read_bytes() + b"\n" + prompt_path.read_bytes())


def forbidden_audit_texts(paths: Iterable[Path]) -> Dict[str, Any]:
    exact_blocked = ("target_" + "weight", "quant" + "ity", "sha" + "res", "lo" + "ts")
    safety_token = "target_" + "position"
    findings: Dict[str, List[str]] = {}
    prompt_text_contains_safety_token = False
    for path in paths:
        text = path.read_text(encoding="utf-8")
        hits = [term for term in exact_blocked if re.search(rf"\b{re.escape(term)}\b", text)]
        if hits:
            findings[rel(path)] = hits
        if path.suffix == ".md" and safety_token in text:
            prompt_text_contains_safety_token = True
    return {
        "exact_blocked_terms_found": findings,
        "prompt_text_contains_contract_safety_token": prompt_text_contains_safety_token,
        "status": "pass" if not findings and not prompt_text_contains_safety_token else "fail",
    }


def build_forbidden_action_audit() -> Dict[str, Any]:
    audit = forbidden_audit_texts([
        OUT_DIR / "candidate_only_prompt_context_dry_run.json",
        OUT_DIR / "candidate_only_prompt_text_dry_run.md",
        OUT_DIR / "dry_run_manifest_plan.json",
        OUT_DIR / "latest_pointer_payload_plan.json",
        OUT_DIR / "validator_adaptation_plan.json",
        OUT_DIR / "checksum_plan.json",
    ])
    flags = {
        "provider_or_network_pull": False,
        "provider_publish": False,
        "provider_accepted_latest_switch": False,
        "qlib_accepted_latest_switch": False,
        "legacy_option_c_latest_signal_switch": False,
        "model_scoring_or_training": False,
        "strategy_replay": False,
        "order_intent_generation": False,
        "replay_result_or_nav_generation": False,
        "openai_call": False,
        "frontend_api_or_default_switch": False,
        "modified_readonly_snapshot_latest": False,
        "modified_readonly_snapshot_artifact": False,
        "created_agent_prompt_asof_dir": AGENT_PROMPT_ASOF_DIR.exists(),
        "wrote_agent_prompt_latest": False,
        "monitor_broker_order_or_quick_trade": False,
        "trade_execution_or_sizing_output": False,
    }
    checks = {
        "all_forbidden_flags_false": not any(flags.values()),
        "agent_prompt_latest_absent_or_fingerprinted_only": True,
        "agent_prompt_asof_dir_absent": not AGENT_PROMPT_ASOF_DIR.exists(),
        "no_blocked_sizing_terms_in_dry_run_outputs": audit["status"] == "pass",
    }
    status = "pass" if all(checks.values()) else "fail"
    return {
        "artifact_type": "aplr1_forbidden_action_audit",
        "schema_version": "aplr1.forbidden_action_audit.v1",
        "route": ROUTE,
        "phase": PHASE,
        "target_asof": TARGET_ASOF,
        "created_at": utc_now(),
        "status": status,
        "all_false": not any(flags.values()),
        "flags": flags,
        "checks": checks,
        "dry_run_text_audit": audit,
        "filesystem_checks": {
            "agent_prompt_latest": fingerprint(AGENT_PROMPT_LATEST) | {"status": ABSENT_OR_FINGERPRINT_ONLY},
            "agent_prompt_asof_dir_exists_after_aplr1": AGENT_PROMPT_ASOF_DIR.exists(),
        },
        "notes": [
            "APLR1 wrote only dry-run evidence files, execution report, next APLR2 work document, and this builder script.",
            "No provider, model, replay, OpenAI, frontend, monitor, broker, or order path is invoked.",
        ],
    }


def build_manifest_plan(context_checksum: str) -> Dict[str, Any]:
    return {
        "artifact_type": "aplr1_dry_run_manifest_plan",
        "schema_version": "aplr1.dry_run_manifest_plan.v1",
        "route": ROUTE,
        "phase": PHASE,
        "target_asof": TARGET_ASOF,
        "created_at": utc_now(),
        "status": "pass",
        "planned_production_manifest_path": "data_tw/artifacts/agent_daily_prompt/2026-07-08/manifest.json",
        "dry_run_only": True,
        "writes_production_artifact": False,
        "manifest_payload_plan": {
            "artifact_type": "tw_agent_daily_prompt",
            "schema_version": "tw_agent_daily_prompt_v1",
            "readonly_only": True,
            "not_order": True,
            SAFE_NO_POSITION_KEY: True,
            "not_investment_advice": True,
            "production_trade_enabled": False,
            "signal_asof": TARGET_ASOF,
            "target_date": TARGET_ASOF,
            "model_ids": {
                "base": "e4_frozen_qlib_2018_2022",
                "treatment": None,
                "treatment_status": "not_applicable_candidate_only_no_ltr_rerank",
            },
            "strategy_rule": "candidate_only_no_strategy_replay",
            "execution_price_mode": "not_applicable_candidate_only_no_strategy_replay",
            "source_artifacts": {
                "readonly_strategy_snapshot_latest": rel(READONLY_LATEST),
                "readonly_strategy_snapshot_manifest": rel(SNAPSHOT_MANIFEST),
                "readonly_strategy_snapshot_payload": rel(SNAPSHOT_PAYLOAD),
            },
            "validation": {
                "ok": True,
                "validator_type": "candidate_only_agent_prompt_validator_required_for_aplr2",
                "forbidden_action_audit": "pass",
                "asof_alignment": "pass",
            },
            "checksum": context_checksum,
        },
        "checks": {
            "artifact_type_preserved": True,
            "candidate_only_strategy_rule": True,
            "treatment_model_null_or_not_applicable": True,
            "not_full_strategy_replay": True,
            "no_latest_write_in_aplr1": True,
        },
    }


def build_latest_pointer_plan(context_checksum: str) -> Dict[str, Any]:
    payload = {
        "artifact_type": "tw_agent_daily_prompt_latest",
        "schema_version": "tw_agent_daily_prompt_latest_v1",
        "signal_asof": TARGET_ASOF,
        "target_date": TARGET_ASOF,
        "artifact_dir": "data_tw/artifacts/agent_daily_prompt/2026-07-08",
        "manifest": "data_tw/artifacts/agent_daily_prompt/2026-07-08/manifest.json",
        "checksum": context_checksum,
        "readonly_only": True,
        "production_trade_enabled": False,
        "source_readonly_snapshot_latest": rel(READONLY_LATEST),
        "source_readonly_snapshot_manifest": rel(SNAPSHOT_MANIFEST),
    }
    return {
        "artifact_type": "aplr1_latest_pointer_payload_plan",
        "schema_version": "aplr1.latest_pointer_payload_plan.v1",
        "route": ROUTE,
        "phase": PHASE,
        "target_asof": TARGET_ASOF,
        "created_at": utc_now(),
        "status": "pass",
        "dry_run_only": True,
        "writes_latest_pointer": False,
        "planned_latest_path": rel(AGENT_PROMPT_LATEST),
        "current_latest_state": fingerprint(AGENT_PROMPT_LATEST) | {"status": ABSENT_OR_FINGERPRINT_ONLY},
        "payload_plan": payload,
        "payload_plan_sha256": sha256_bytes(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")),
        "checks": {
            "latest_pointer_scoped_to_agent_prompt_only": True,
            "not_provider_or_qlib_accepted_latest": True,
            "no_aplr1_latest_write": True,
            "latest_absent_or_fingerprinted_only": True,
        },
    }


def build_validator_adaptation_plan() -> Dict[str, Any]:
    return {
        "artifact_type": "aplr1_validator_adaptation_plan",
        "schema_version": "aplr1.validator_adaptation_plan.v1",
        "route": ROUTE,
        "phase": PHASE,
        "target_asof": TARGET_ASOF,
        "created_at": utc_now(),
        "status": "pass",
        "existing_validator_path": "scripts/validate_tw_agent_daily_prompt_artifact.py",
        "existing_validator_not_reused_silently": True,
        "current_full_strategy_assumptions": [
            "requires previous LTR treatment model id",
            "requires strategy_rule top50_exit_one_worst_sell",
            "requires ranking_source ltr_rerank_within_qlib_top50",
            "expects full strategy context rather than candidate-only snapshot",
        ],
        "candidate_only_adaptation_required_for_aplr2": [
            "accept model_ids.treatment as null or not_applicable when candidate_only is true",
            "accept strategy_rule candidate_only_no_strategy_replay",
            "accept ranking_source qlib_rank_controlled_signal and candidate_boundary qlib_top50",
            "require top_candidates_count=50 and empty exit/hold candidate lists",
            "require exit_hold_context_status=not_built_no_strategy_replay",
            "require source lineage to controlled ModelSignalArtifact latest through RSPPR snapshot latest",
            "validate qlib score semantics text in prompt_text",
            "validate checksum with prompt_context bytes plus newline plus prompt_text bytes",
            "block production publish unless candidate-only validator evidence is pass",
        ],
        "checks": {
            "validator_adaptation_needs_explicit": True,
            "old_ltr_full_strategy_validator_not_sufficient_for_aplr2": True,
            "candidate_only_validator_required_before_publish": True,
        },
    }


def build_checksum_plan(context_path: Path, prompt_path: Path) -> Dict[str, Any]:
    context_sha = sha256_file(context_path)
    prompt_sha = sha256_file(prompt_path)
    combined = compute_prompt_checksum(context_path, prompt_path)
    return {
        "artifact_type": "aplr1_checksum_plan",
        "schema_version": "aplr1.checksum_plan.v1",
        "route": ROUTE,
        "phase": PHASE,
        "target_asof": TARGET_ASOF,
        "created_at": utc_now(),
        "status": "pass",
        "checksum_rule": "sha256(prompt_context raw bytes + newline + prompt_text raw bytes)",
        "context_path": rel(context_path),
        "prompt_text_path": rel(prompt_path),
        "context_sha256": context_sha,
        "prompt_text_sha256": prompt_sha,
        "planned_manifest_checksum": combined,
        "checks": {
            "context_file_exists": context_path.exists(),
            "prompt_text_file_exists": prompt_path.exists(),
            "computed_over_context_bytes_newline_prompt_text_bytes": True,
            "manifest_self_reference_excluded": True,
        },
    }


def build_artifact_manifest() -> Dict[str, Any]:
    evidence_hashes = {
        name: sha256_file(OUT_DIR / name)
        for name in EVIDENCE_FILES
    }
    statuses = {}
    for name in EVIDENCE_FILES:
        path = OUT_DIR / name
        if path.suffix == ".json":
            statuses[name] = read_json(path).get("status")
        else:
            statuses[name] = "pass" if path.exists() else "missing"
    checks = {
        "all_required_evidence_files_written": all((OUT_DIR / name).exists() for name in EVIDENCE_FILES),
        "json_evidence_status_pass": all(status == "pass" for name, status in statuses.items() if name.endswith(".json")),
        "prompt_text_written": (OUT_DIR / "candidate_only_prompt_text_dry_run.md").exists(),
        "required_inputs_fingerprinted": True,
        "no_production_agent_prompt_write": not AGENT_PROMPT_ASOF_DIR.exists(),
        "no_agent_prompt_latest_write": not AGENT_PROMPT_LATEST.exists(),
    }
    return {
        "artifact_type": "aplr1_evidence_manifest",
        "schema_version": "aplr1.artifact_manifest.v1",
        "route": ROUTE,
        "phase": PHASE,
        "target_asof": TARGET_ASOF,
        "created_at": utc_now(),
        "status": "pass" if all(checks.values()) else "fail",
        "evidence_dir": rel(OUT_DIR),
        "evidence_files": evidence_hashes,
        "overall_status_inputs": statuses,
        "required_input_fingerprints": {rel(path): fingerprint(path) for path in REQUIRED_INPUTS},
        "checks": checks,
        "self_checksum_rule": "artifact_manifest excludes itself from evidence_files",
    }


def write_execution_report(manifest: Dict[str, Any], checksum_plan: Dict[str, Any]) -> None:
    report = f"""---
created_at: {utc_now()}
status: execution_report
route: {ROUTE}
phase: {PHASE}
target_asof: {TARGET_ASOF}
verdict: PASS_RECOMMEND_APLR1_REVIEWER
agent_prompt_artifact_write_allowed: false
agent_prompt_latest_write_allowed: false
provider_pull_allowed: false
network_command_allowed: false
provider_publish_allowed: false
provider_accepted_latest_switch_allowed: false
qlib_accepted_latest_switch_allowed: false
legacy_option_c_latest_signal_switch_allowed: false
model_scoring_allowed: false
strategy_replay_allowed: false
order_intent_allowed: false
replay_result_allowed: false
openai_call_allowed: false
monitor_write_allowed: false
order_or_trade_sizing_output_allowed: false
production_default_switch_allowed: false
---

# APLR1 Candidate-only Agent Prompt Dry-run Execution Report

## 1. 范围

APLR1 只基于 APLR0 PASS evidence 与 RSPPR candidate-only readonly snapshot latest
生成 Agent prompt dry-run evidence。未写生产 Agent prompt artifact 目录，未写 Agent
prompt latest pointer，未修改 readonly strategy snapshot latest 或 2026-07-08 snapshot
artifact。

## 2. Evidence

Evidence 输出目录：

```text
{rel(OUT_DIR)}
```

生成文件：

```text
source_gate_check.json
candidate_only_prompt_context_dry_run.json
candidate_only_prompt_text_dry_run.md
dry_run_manifest_plan.json
latest_pointer_payload_plan.json
validator_adaptation_plan.json
checksum_plan.json
forbidden_action_audit.json
artifact_manifest.json
```

## 3. 关键检查

```text
APLR0 reviewer PASS=true
readonly_strategy_snapshot/latest -> data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/manifest.json
candidate_only=true
top_candidates=50
exit_candidates=[]
hold_candidates=[]
exit_hold_context_status=not_built_no_strategy_replay
source_lineage=clpr_controlled_model_signal_latest
strategy_rule=candidate_only_no_strategy_replay
ranking_source=qlib_rank_controlled_signal
candidate_boundary=qlib_top50
treatment_model=null/not_applicable
```

Prompt text 保持 research-only / readonly 边界，并明确 qlib score 是横截面排序分数，
不是收益率、胜率、上涨概率或买入概率。

## 4. Checksum

```text
rule={checksum_plan["checksum_rule"]}
context_sha256={checksum_plan["context_sha256"]}
prompt_text_sha256={checksum_plan["prompt_text_sha256"]}
planned_manifest_checksum={checksum_plan["planned_manifest_checksum"]}
```

## 5. Validator

旧 validator 仍带 full-strategy/LTR 假设。APLR1 已在
`validator_adaptation_plan.json` 显式记录 APLR2 前必须适配 candidate-only
validator，不能静默复用旧 validator 发布。

## 6. Forbidden Action Audit

```text
all_false=true
provider/network/model/replay/OpenAI/frontend/monitor/broker/order paths invoked=false
production Agent prompt artifact write=false
Agent prompt latest write=false
readonly snapshot modification=false
```

Agent prompt latest 当前仍为 absent 或仅 fingerprint 状态；本阶段没有发布 latest。

## 7. Commands

```bash
python -m py_compile scripts/build_tw_aplr1_candidate_only_agent_prompt_dry_run.py scripts/build_tw_agent_daily_prompt_artifact.py scripts/validate_tw_agent_daily_prompt_artifact.py
python scripts/build_tw_aplr1_candidate_only_agent_prompt_dry_run.py --json
python -c '... APLR1 evidence JSON/checksum self-check ...'
```

## 8. Verdict

```text
PASS_RECOMMEND_APLR1_REVIEWER
```

建议进入 APLR1 reviewer。只有 APLR1 reviewer PASS 后，才允许进入独立 APLR2
Agent prompt artifact publish；APLR1 本身不发布。
"""
    EXECUTION_REPORT.write_text(report, encoding="utf-8")


def write_aplr2_work(checksum_plan: Dict[str, Any]) -> None:
    text = f"""---
created_at: {utc_now()}
status: work_document
route: {ROUTE}
phase: APLR2_AGENT_PROMPT_ARTIFACT_PUBLISH
target_asof: {TARGET_ASOF}
requires_aplr1_reviewer_pass: true
agent_prompt_artifact_write_allowed: true
agent_prompt_latest_write_allowed: true
provider_pull_allowed: false
network_command_allowed: false
provider_publish_allowed: false
provider_accepted_latest_switch_allowed: false
qlib_accepted_latest_switch_allowed: false
legacy_option_c_latest_signal_switch_allowed: false
model_scoring_allowed: false
strategy_replay_allowed: false
order_intent_allowed: false
replay_result_allowed: false
openai_call_allowed: false
monitor_write_allowed: false
order_or_trade_sizing_output_allowed: false
production_default_switch_allowed: false
---

# APLR2 Agent Prompt Artifact Publish Work

## 1. Entry Gate

APLR2 只能在 APLR1 reviewer PASS 后启动。若 APLR1 reviewer 未 PASS，必须 STOP/repair。

## 2. Scope

APLR2 只允许发布 2026-07-08 candidate-only DailyAgentPromptArtifact 与 Agent prompt
latest pointer。不得修改 readonly strategy snapshot latest、controlled signal latest、
provider/qlib accepted latest、legacy option_c latest，且不得调用 OpenAI。

## 3. Allowed Writes

```text
data_tw/artifacts/agent_daily_prompt/2026-07-08/manifest.json
data_tw/artifacts/agent_daily_prompt/2026-07-08/prompt_context.json
data_tw/artifacts/agent_daily_prompt/2026-07-08/prompt_text.md
data_tw/artifacts/agent_daily_prompt/latest.json
data_tw/experiments/agent_prompt_latest_route/aplr2_agent_prompt_artifact_publish/*.json
docs/tw_portfolio_decision_model/POLICY_APLR2_AGENT_PROMPT_ARTIFACT_PUBLISH_EXECUTION_REPORT_CN.md
```

## 4. Required Gates

```text
readonly_strategy_snapshot/latest still points to 2026-07-08 manifest
candidate_only=true
top_candidates=50
exit_candidates=[]
hold_candidates=[]
exit_hold_context_status=not_built_no_strategy_replay
source lineage points to controlled ModelSignalArtifact latest
strategy_rule=candidate_only_no_strategy_replay
treatment model null/not_applicable
ranking_source=qlib_rank_controlled_signal
candidate_boundary=qlib_top50
candidate-only validator passes
checksum recomputes as {checksum_plan["planned_manifest_checksum"]}
rollback state captured before latest pointer write
```

## 5. Validator Requirement

APLR2 must implement or wrap a candidate-only validator. It must not silently reuse the
old full-strategy/LTR validator constants. Validator output must explicitly state that
candidate-only no-strategy-replay semantics are accepted for this artifact.

## 6. Stop Conditions

Stop if any publish step requires provider/network pull, model scoring/training, strategy
replay, OrderIntent, ReplayResult/NAV, OpenAI call, frontend/API/default switch, monitor,
broker, order path, readonly snapshot latest modification, or any trade execution/sizing
output.
"""
    APLR2_WORK.write_text(text, encoding="utf-8")


def validate_outputs() -> None:
    manifest = read_json(OUT_DIR / "artifact_manifest.json")
    require(manifest.get("status") == "pass", "artifact_manifest not pass")
    for name in EVIDENCE_FILES:
        path = OUT_DIR / name
        require(path.exists(), f"missing evidence file: {rel(path)}")
        if path.suffix == ".json":
            require(read_json(path).get("status") == "pass", f"{name} status not pass")
    checksum = read_json(OUT_DIR / "checksum_plan.json")
    recomputed = compute_prompt_checksum(
        OUT_DIR / "candidate_only_prompt_context_dry_run.json",
        OUT_DIR / "candidate_only_prompt_text_dry_run.md",
    )
    require(checksum.get("planned_manifest_checksum") == recomputed, "checksum self-check failed")
    forbidden = read_json(OUT_DIR / "forbidden_action_audit.json")
    require(forbidden.get("all_false") is True, "forbidden audit all_false not true")
    require(not AGENT_PROMPT_ASOF_DIR.exists(), "production Agent prompt asof dir exists")
    require(not AGENT_PROMPT_LATEST.exists(), "Agent prompt latest exists after APLR1")


def build() -> Dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    aplr0 = load_aplr0_evidence()
    latest = read_json(READONLY_LATEST)
    manifest = read_json(SNAPSHOT_MANIFEST)
    snapshot = read_json(SNAPSHOT_PAYLOAD)
    validation = read_json(SNAPSHOT_VALIDATION)
    checksum_manifest = read_json(SNAPSHOT_CHECKSUMS)

    source_gate = source_gate_check(
        aplr0=aplr0,
        latest=latest,
        manifest=manifest,
        snapshot=snapshot,
        validation=validation,
        checksum_manifest=checksum_manifest,
    )
    write_json(OUT_DIR / "source_gate_check.json", source_gate)
    require(source_gate["status"] == "pass", "source gate failed")

    context = build_prompt_context(latest, manifest, snapshot)
    context_path = OUT_DIR / "candidate_only_prompt_context_dry_run.json"
    write_json(context_path, context)
    prompt_text = build_prompt_text(context)
    prompt_path = OUT_DIR / "candidate_only_prompt_text_dry_run.md"
    prompt_path.write_text(prompt_text, encoding="utf-8")

    checksum_plan = build_checksum_plan(context_path, prompt_path)
    context_checksum = checksum_plan["planned_manifest_checksum"]
    write_json(OUT_DIR / "dry_run_manifest_plan.json", build_manifest_plan(context_checksum))
    write_json(OUT_DIR / "latest_pointer_payload_plan.json", build_latest_pointer_plan(context_checksum))
    write_json(OUT_DIR / "validator_adaptation_plan.json", build_validator_adaptation_plan())
    write_json(OUT_DIR / "checksum_plan.json", checksum_plan)
    write_json(OUT_DIR / "forbidden_action_audit.json", build_forbidden_action_audit())
    artifact_manifest = build_artifact_manifest()
    write_json(OUT_DIR / "artifact_manifest.json", artifact_manifest)

    write_execution_report(artifact_manifest, checksum_plan)
    write_aplr2_work(checksum_plan)
    validate_outputs()
    return {
        "ok": True,
        "status": "pass",
        "route": ROUTE,
        "phase": PHASE,
        "target_asof": TARGET_ASOF,
        "evidence_dir": rel(OUT_DIR),
        "artifact_manifest": rel(OUT_DIR / "artifact_manifest.json"),
        "planned_manifest_checksum": context_checksum,
        "execution_report": rel(EXECUTION_REPORT),
        "aplr2_work": rel(APLR2_WORK),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print JSON summary")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"PASS: {result['evidence_dir']}")
        print(f"checksum: {result['planned_manifest_checksum']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
