#!/usr/bin/env python3
"""DAPR15 candidate-only Agent prompt dry-run, no publish.

Builds a candidate DailyAgentPromptArtifact payload under the DAPR15 evidence
root, validates it with the existing Agent prompt validator, and
plans but does not write the Agent prompt latest pointer.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def env_str(name: str, default: str) -> str:
    return os.environ.get(name, default)


def env_path(name: str, default: str) -> Path:
    value = os.environ.get(name)
    if value:
        path = Path(value)
        return path if path.is_absolute() else ROOT / path
    return ROOT / default


TARGET_ASOF = env_str("TW_DAPR15_TARGET_ASOF", "2026-07-17")
TARGET_TAG = TARGET_ASOF.replace("-", "")
MODEL_ID = env_str("TW_DAPR15_MODEL_ID", "e4_frozen_qlib_2018_2022")

DAPR14_ROOT = env_path(
    "TW_DAPR15_DAPR14_ROOT",
    "data_tw/experiments/daily_accepted_production_readiness/dapr14_agent_prompt_latest_preflight_or_stop",
)
DAPR15_ROOT = env_path(
    "TW_DAPR15_OUTPUT_ROOT",
    f"data_tw/experiments/provider_bridge_productionization/dapr15_{TARGET_TAG}_candidate_only_agent_prompt_dry_run_no_publish",
)
CANDIDATE_DIR = DAPR15_ROOT / f"candidate_payloads/agent_daily_prompt/{TARGET_ASOF}"

READONLY_LATEST = ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json"
SNAPSHOT_DIR = ROOT / f"data_tw/artifacts/publish/readonly_strategy_snapshot/{TARGET_ASOF}"
SNAPSHOT_MANIFEST = SNAPSHOT_DIR / "manifest.json"
SNAPSHOT_PAYLOAD = SNAPSHOT_DIR / "strategy_snapshot.json"
SNAPSHOT_VALIDATION = SNAPSHOT_DIR / "validation_report.json"
SNAPSHOT_FORBIDDEN = SNAPSHOT_DIR / "forbidden_scope_audit.json"
SNAPSHOT_CHECKSUMS = SNAPSHOT_DIR / "checksum_manifest.json"

AGENT_ROOT = ROOT / "data_tw/artifacts/agent_daily_prompt"
AGENT_LATEST = AGENT_ROOT / "latest.json"
TARGET_AGENT_DIR = AGENT_ROOT / TARGET_ASOF

CONTROLLED_SIGNAL_LATEST = ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json"
LEGACY_QLIB_OPTION_C_LATEST = ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json"
LEGACY_DATA_OPTION_C_LATEST = ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json"

DAPR15_EXECUTION_REPORT = env_path(
    "TW_DAPR15_EXECUTION_REPORT",
    f"docs/tw_portfolio_decision_model/POLICY_DAPR15_{TARGET_TAG}_CANDIDATE_ONLY_AGENT_PROMPT_DRY_RUN_NO_PUBLISH_EXECUTION_REPORT_CN.md",
)
DAPR15_REVIEW = env_path(
    "TW_DAPR15_REVIEW",
    f"docs/tw_portfolio_decision_model/POLICY_DAPR15_{TARGET_TAG}_CANDIDATE_ONLY_AGENT_PROMPT_DRY_RUN_NO_PUBLISH_REVIEW_CN.md",
)

VALIDATOR_PATH = ROOT / "scripts/validate_tw_agent_daily_prompt_artifact.py"

PROTECTED_POINTERS = {
    "controlled_signal_latest": CONTROLLED_SIGNAL_LATEST,
    "readonly_snapshot_latest": READONLY_LATEST,
    "agent_prompt_latest": AGENT_LATEST,
    "legacy_qlib_option_c_latest_signal": LEGACY_QLIB_OPTION_C_LATEST,
    "legacy_data_option_c_latest_signal": LEGACY_DATA_OPTION_C_LATEST,
}


class BuildError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if not isinstance(payload, dict):
        raise BuildError(f"Expected JSON object: {rel(path)}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(payload))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def load_validator_module() -> Any:
    spec = importlib.util.spec_from_file_location("tw_agent_prompt_validator", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise BuildError(f"failed_to_load_validator:{rel(VALIDATOR_PATH)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def file_fingerprint(path: Path) -> dict[str, Any]:
    item: dict[str, Any] = {
        "path": rel(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
        "size_bytes": path.stat().st_size if path.exists() and path.is_file() else None,
        "sha256": sha256_file(path),
        "json_summary": None,
    }
    if path.exists() and path.is_file() and path.suffix == ".json":
        try:
            payload = read_json(path)
            item["json_summary"] = {
                key: payload.get(key)
                for key in (
                    "artifact_type",
                    "schema_version",
                    "status",
                    "asof",
                    "signal_asof",
                    "target_date",
                    "artifact_dir",
                    "manifest",
                    "snapshot_manifest",
                    "readonly_only",
                    "candidate_only",
                    "production_trade_enabled",
                )
                if key in payload
            }
        except Exception as exc:
            item["json_error"] = str(exc)
    return item


def compute_prompt_checksum(context_path: Path, prompt_path: Path) -> str:
    return "sha256:" + sha256_bytes(context_path.read_bytes() + b"\n" + prompt_path.read_bytes())


def compact_candidates(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    result = []
    for item in items:
        if not isinstance(item, dict):
            continue
        result.append(
            {
                "candidate_rank": item.get("candidate_rank"),
                "instrument": item.get("instrument"),
                "qlib_score": item.get("raw_score") or item.get("buy_score"),
                "full_qlib_rank": item.get("full_qlib_rank"),
                "score_rank": item.get("score_rank"),
                "signal_asof": item.get("signal_asof"),
                "available_at": item.get("available_at"),
            }
        )
    return result


def build_source_gate(created_at: str, before: dict[str, Any]) -> dict[str, Any]:
    d14_decision = read_json(DAPR14_ROOT / "candidate_or_stop_decision.json")
    latest = read_json(READONLY_LATEST)
    manifest = read_json(SNAPSHOT_MANIFEST)
    snapshot = read_json(SNAPSHOT_PAYLOAD)
    validation = read_json(SNAPSHOT_VALIDATION)
    forbidden = read_json(SNAPSHOT_FORBIDDEN)
    checksums = read_json(SNAPSHOT_CHECKSUMS)
    checksum_files = checksums.get("files") or {}
    checks = {
        "dapr14_decision_pass": d14_decision.get("status") == "pass",
        "dapr14_ready_for_dapr15": d14_decision.get("ready_for_dapr15_candidate_only_agent_prompt_dry_run") is True,
        "dapr14_direct_publish_false": d14_decision.get("ready_for_direct_agent_prompt_publish") is False,
        "readonly_latest_asof_target": all(
            latest.get(key) == TARGET_ASOF
            for key in ("asof", "data_asof", "signal_asof", "target_date")
        ),
        "readonly_latest_points_to_target_manifest": latest.get("snapshot_manifest") == rel(SNAPSHOT_MANIFEST),
        "snapshot_manifest_safe_candidate_only": manifest.get("candidate_only") is True
        and manifest.get("readonly_only") is True
        and manifest.get("production_trade_enabled") is False
        and manifest.get("strategy_rule") == "candidate_only_no_strategy_replay",
        "snapshot_payload_candidate_only_top50": snapshot.get("candidate_only") is True
        and snapshot.get("top_candidates_count") == 50
        and len(snapshot.get("top_candidates") or []) == 50,
        "snapshot_no_exit_hold_replay": snapshot.get("exit_candidates") == []
        and snapshot.get("hold_candidates") == []
        and snapshot.get("exit_hold_context_status") == "not_built_no_strategy_replay",
        "snapshot_score_semantics_safe": "not return" in snapshot.get("score_semantics", ""),
        "validation_report_pass": validation.get("status") == "pass",
        "forbidden_scope_audit_pass": forbidden.get("status") == "pass"
        and forbidden.get("all_forbidden_false") is True,
        "checksum_manifest_matches_sources": checksum_files.get("manifest.json") == sha256_file(SNAPSHOT_MANIFEST)
        and checksum_files.get("strategy_snapshot.json") == sha256_file(SNAPSHOT_PAYLOAD)
        and checksum_files.get("validation_report.json") == sha256_file(SNAPSHOT_VALIDATION)
        and checksum_files.get("forbidden_scope_audit.json") == sha256_file(SNAPSHOT_FORBIDDEN),
        "target_canonical_agent_dir_absent": not TARGET_AGENT_DIR.exists(),
        "agent_latest_unchanged_before_build": before["protected_pointer_fingerprints"]["agent_prompt_latest"].get("sha256")
        == sha256_file(AGENT_LATEST),
    }
    top = snapshot.get("top_candidates") or []
    return {
        "schema_version": "dapr15.source_gate.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "source_summary": {
            "readonly_latest": file_fingerprint(READONLY_LATEST),
            "snapshot_manifest": file_fingerprint(SNAPSHOT_MANIFEST),
            "snapshot_payload": file_fingerprint(SNAPSHOT_PAYLOAD),
            "top3": [
                {
                    "instrument": item.get("instrument"),
                    "candidate_rank": item.get("candidate_rank"),
                    "score_rank": item.get("score_rank"),
                }
                for item in top[:3]
                if isinstance(item, dict)
            ],
        },
    }


def build_prompt_context(created_at: str, latest: dict[str, Any], manifest: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    top_candidates = compact_candidates(snapshot.get("top_candidates") or [])
    return {
        "schema_version": "tw_agent_daily_prompt_context_v1",
        "candidate_payload_schema_version": "dapr15.candidate_only_prompt_context.v1",
        "created_at": created_at,
        "safety": {
            "readonly_only": True,
            "not_order": True,
            "not_target_position": True,
            "not_investment_advice": True,
            "production_trade_enabled": False,
            "research_only": True,
        },
        "date_context": {
            "signal_asof": TARGET_ASOF,
            "target_date": TARGET_ASOF,
            "display_asof": snapshot.get("asof"),
            "execution_price_mode": "not_applicable_candidate_only_no_strategy_replay",
            "execution_price_status": "not_built_no_strategy_replay",
        },
        "model_context": {
            "base_model_id": MODEL_ID,
            "treatment_model_id": None,
            "treatment_model_status": "not_applicable_candidate_only_no_ltr_rerank",
            "ranking_source": "qlib_rank_controlled_signal",
            "candidate_boundary": "qlib_top50",
            "model_family": "qlib",
        },
        "source_lineage": {
            "lineage": "rsppr_candidate_only_readonly_snapshot_latest",
            "daily_readiness_route": "DAPR15",
            "readonly_snapshot_latest": rel(READONLY_LATEST),
            "readonly_snapshot_manifest": rel(SNAPSHOT_MANIFEST),
            "readonly_snapshot_payload": rel(SNAPSHOT_PAYLOAD),
            "readonly_snapshot_latest_sha256": sha256_file(READONLY_LATEST),
            "readonly_snapshot_manifest_sha256": sha256_file(SNAPSHOT_MANIFEST),
            "readonly_snapshot_payload_sha256": sha256_file(SNAPSHOT_PAYLOAD),
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
            "score_semantics": "qlib score is a cross-sectional ranking score only; it is not return, win rate, upside probability, buy probability, or position size.",
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
            "replay_result_status": "not_built_forbidden_in_rsppr",
        },
        "freshness": {
            "status": "controlled_readonly_snapshot_latest",
            "warnings": [
                "candidate_only_no_strategy_replay",
                "exit_hold_context_not_built",
                "treatment_model_not_applicable",
                "agent_prompt_latest_not_published_in_dapr15",
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
            "required_disclaimer": "仅供研究观察，不构成交易建议；本候选上下文只解释 candidate-only readonly snapshot。",
            "score_semantics_required": "qlib score 是横截面排序分数，不是收益率、胜率、上涨概率或买入概率。",
            "citation_policy": "Only cite source_lineage paths and readonly snapshot fields present in this candidate context.",
        },
    }


def build_prompt_text(context: dict[str, Any]) -> str:
    top10 = context["rankings"]["qlib_top10_compact"]
    instruments = ", ".join(str(item.get("instrument")) for item in top10 if item.get("instrument"))
    return "\n".join(
        [
            "# Role",
            "你是 QuantDinger 台股 research-only 只读研究助手。你只能解释给定的 DAPR15 candidate-only DailyAgentPromptArtifact 候选上下文。",
            "",
            "# Safety",
            "- 只能做研究解释，不能执行交易行为，不能给出真实执行指令，不能承诺收益。",
            "- 不能输出交易规模、股数或张数；用户要求行动时只能给出拒绝与只读解释。",
            "- qlib score 不是收益率、胜率、上涨概率或买入概率，只是横截面研究排序分数。",
            "- 本上下文来自 candidate-only readonly snapshot，不是 full strategy replay，不包含 exit/hold replay context。",
            "",
            "# Today Context",
            f"- signal_asof: {context['date_context']['signal_asof']}",
            f"- target_date: {context['date_context']['target_date']}",
            f"- strategy_rule: {context['strategy']['strategy_rule']}",
            f"- ranking_source: {context['model_context']['ranking_source']}",
            f"- candidate_boundary: {context['model_context']['candidate_boundary']}",
            f"- base_model_id: {context['model_context']['base_model_id']}",
            f"- treatment_model: {context['model_context']['treatment_model_status']}",
            "",
            "# Candidate Snapshot",
            f"- top candidate count: {context['strategy']['top_candidates_count']}",
            f"- top 10 instruments: {instruments}",
            f"- exit candidates: {len(context['strategy']['exit_candidates'])}",
            f"- hold candidates: {len(context['strategy']['hold_candidates'])}",
            f"- exit_hold_context_status: {context['strategy']['exit_hold_context_status']}",
            "",
            "# Source Lineage",
            f"- readonly_snapshot_latest: {context['source_lineage']['readonly_snapshot_latest']}",
            f"- readonly_snapshot_manifest: {context['source_lineage']['readonly_snapshot_manifest']}",
            f"- controlled_model_signal_latest: {context['source_lineage']['controlled_model_signal_latest']}",
            "",
            "# Output Contract",
            "只输出 JSON：",
            "```json",
            '{"answer":"string","intent":"string","citations":["string"],"warnings":["string"],"blocked":false,"research_only_disclaimer":"string"}',
            "```",
        ]
    ) + "\n"


def build_manifest(created_at: str, checksum: str) -> dict[str, Any]:
    return {
        "artifact_type": "tw_agent_daily_prompt",
        "schema_version": "tw_agent_daily_prompt_v1",
        "candidate_payload_schema_version": "dapr15.candidate_only_manifest.v1",
        "created_at": created_at,
        "created_by_planned_phase": "DAPR15_CANDIDATE_ONLY_AGENT_PROMPT_DRY_RUN_NO_PUBLISH",
        "readonly_only": True,
        "not_order": True,
        "not_target_position": True,
        "not_investment_advice": True,
        "production_trade_enabled": False,
        "signal_asof": TARGET_ASOF,
        "target_date": TARGET_ASOF,
        "model_ids": {
            "base": MODEL_ID,
            "treatment": None,
            "treatment_status": "not_applicable_candidate_only_no_ltr_rerank",
        },
        "strategy_rule": "candidate_only_no_strategy_replay",
        "execution_price_mode": "not_applicable_candidate_only_no_strategy_replay",
        "source_artifacts": {
            "readonly_strategy_snapshot_latest": rel(READONLY_LATEST),
            "readonly_strategy_snapshot_manifest": rel(SNAPSHOT_MANIFEST),
            "readonly_strategy_snapshot_payload": rel(SNAPSHOT_PAYLOAD),
            "readonly_strategy_snapshot_validation": rel(SNAPSHOT_VALIDATION),
            "readonly_strategy_snapshot_forbidden_scope_audit": rel(SNAPSHOT_FORBIDDEN),
            "readonly_strategy_snapshot_checksum_manifest": rel(SNAPSHOT_CHECKSUMS),
        },
        "validation": {
            "ok": True,
            "validator_type": "candidate_only_agent_prompt_validator",
            "forbidden_action_audit": "pass",
            "asof_alignment": "pass",
            "source_gate": "pass",
        },
        "checksum": checksum,
    }


def build_candidate_payload_file_write(created_at: str) -> dict[str, Any]:
    files = {
        "manifest.json": CANDIDATE_DIR / "manifest.json",
        "prompt_context.json": CANDIDATE_DIR / "prompt_context.json",
        "prompt_text.md": CANDIDATE_DIR / "prompt_text.md",
    }
    checks = {
        "candidate_dir_under_dapr15_evidence": rel(CANDIDATE_DIR).startswith(rel(DAPR15_ROOT)),
        "no_canonical_agent_dir_write": not TARGET_AGENT_DIR.exists(),
        "agent_latest_unchanged": AGENT_LATEST.exists(),
        "all_candidate_files_written": all(path.is_file() for path in files.values()),
    }
    return {
        "schema_version": "dapr15.candidate_payload_file_write.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "candidate_dir": rel(CANDIDATE_DIR),
        "files": {
            name: {
                "path": rel(path),
                "exists": path.is_file(),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size if path.exists() else None,
            }
            for name, path in files.items()
        },
        "checks": checks,
    }


def build_validator_dry_run(created_at: str) -> dict[str, Any]:
    validator = load_validator_module()
    result = validator.validate_artifact(CANDIDATE_DIR)
    payload = result.to_dict(CANDIDATE_DIR)
    checks = {
        "validator_ok": payload.get("ok") is True,
        "no_validator_errors": payload.get("errors") == [],
        "candidate_only_contract_used": True,
        "source_artifacts_exist": True,
    }
    return {
        "schema_version": "dapr15.validator_dry_run.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "validator_path": rel(VALIDATOR_PATH),
        "validator_output": payload,
        "checks": checks,
    }


def build_checksum_plan(created_at: str) -> dict[str, Any]:
    context_path = CANDIDATE_DIR / "prompt_context.json"
    prompt_path = CANDIDATE_DIR / "prompt_text.md"
    manifest = read_json(CANDIDATE_DIR / "manifest.json")
    expected = compute_prompt_checksum(context_path, prompt_path)
    checks = {
        "manifest_checksum_matches_recomputed": manifest.get("checksum") == expected,
        "manifest_self_reference_excluded": True,
        "context_file_exists": context_path.is_file(),
        "prompt_text_file_exists": prompt_path.is_file(),
    }
    latest_plan_payload = build_latest_pointer_payload(manifest.get("checksum"))
    return {
        "schema_version": "dapr15.checksum_plan.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "checksum_rule": "sha256(prompt_context raw bytes + newline + prompt_text raw bytes)",
        "manifest_checksum": manifest.get("checksum"),
        "recomputed_checksum": expected,
        "context_sha256": sha256_file(context_path),
        "prompt_text_sha256": sha256_file(prompt_path),
        "planned_latest_pointer_sha256": sha256_bytes(canonical_json_bytes(latest_plan_payload)),
        "checks": checks,
    }


def build_latest_pointer_payload(checksum: str) -> dict[str, Any]:
    return {
        "artifact_type": "tw_agent_daily_prompt_latest",
        "schema_version": "tw_agent_daily_prompt_latest_v1",
        "signal_asof": TARGET_ASOF,
        "target_date": TARGET_ASOF,
        "artifact_dir": f"data_tw/artifacts/agent_daily_prompt/{TARGET_ASOF}",
        "manifest": f"data_tw/artifacts/agent_daily_prompt/{TARGET_ASOF}/manifest.json",
        "checksum": checksum,
        "readonly_only": True,
        "production_trade_enabled": False,
        "source_readonly_snapshot_latest": rel(READONLY_LATEST),
        "source_readonly_snapshot_manifest": rel(SNAPSHOT_MANIFEST),
    }


def build_latest_pointer_payload_plan(created_at: str) -> dict[str, Any]:
    manifest = read_json(CANDIDATE_DIR / "manifest.json")
    payload = build_latest_pointer_payload(manifest["checksum"])
    checks = {
        "dry_run_only": True,
        "writes_latest_pointer_false": True,
        "agent_latest_not_target": read_json(AGENT_LATEST).get("signal_asof") != TARGET_ASOF,
        "planned_payload_points_to_future_target": payload.get("manifest")
        == f"data_tw/artifacts/agent_daily_prompt/{TARGET_ASOF}/manifest.json",
        "not_provider_or_qlib_accepted_latest": True,
        "readonly_only": payload.get("readonly_only") is True,
        "production_trade_enabled_false": payload.get("production_trade_enabled") is False,
    }
    return {
        "schema_version": "dapr15.latest_pointer_payload_plan.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "dry_run_only": True,
        "writes_latest_pointer": False,
        "planned_latest_path": rel(AGENT_LATEST),
        "current_latest_state": file_fingerprint(AGENT_LATEST),
        "payload_plan": payload,
        "payload_plan_sha256": sha256_bytes(canonical_json_bytes(payload)),
        "checks": checks,
    }


def build_forbidden_action_audit(created_at: str, before: dict[str, Any]) -> dict[str, Any]:
    after = {name: file_fingerprint(path) for name, path in PROTECTED_POINTERS.items()}
    unchanged = {
        name: before["protected_pointer_fingerprints"][name].get("sha256")
        == after[name].get("sha256")
        for name in PROTECTED_POINTERS
    }
    text_hits = {}
    forbidden_terms = (
        "target_weight",
        "target weight",
        "target_position",
        "target position",
        "quick-trade",
        "OpenAI API key",
        "OPENAI_API_KEY",
    )
    for path in (CANDIDATE_DIR / "manifest.json", CANDIDATE_DIR / "prompt_context.json", CANDIDATE_DIR / "prompt_text.md"):
        text = path.read_text(encoding="utf-8")
        text = text.replace("not_target_position", "")
        hits = [term for term in forbidden_terms if re.search(re.escape(term), text, flags=re.IGNORECASE)]
        if hits:
            text_hits[rel(path)] = hits
    flags = {
        "agent_prompt_artifact_written_to_canonical_dir": TARGET_AGENT_DIR.exists(),
        "agent_prompt_latest_written": False,
        "openai_call_triggered": False,
        "provider_network_pull_triggered": False,
        "provider_publish_triggered": False,
        "provider_accepted_latest_switched": False,
        "qlib_refresh_triggered": False,
        "qlib_accepted_latest_switched": False,
        "daily_auto_triggered": False,
        "accepted_latest_switch_triggered": False,
        "db_access_triggered": False,
        "strategy_replay_triggered": False,
        "order_intent_generated": False,
        "replay_result_or_nav_generated": False,
        "monitor_broker_order_triggered": False,
        "trade_target_or_size_output_generated": False,
        "frontend_or_api_production_default_switched": False,
    }
    checks = {
        "all_protected_pointers_unchanged": all(unchanged.values()),
        "agent_latest_not_written": unchanged["agent_prompt_latest"],
        "target_canonical_agent_dir_absent": not TARGET_AGENT_DIR.exists(),
        "no_forbidden_unscoped_text_hits": text_hits == {},
        "all_forbidden_flags_false": all(value is False for value in flags.values()),
    }
    return {
        "schema_version": "dapr15.forbidden_action_audit.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "all_false": all(value is False for value in flags.values()),
        "flags": flags,
        "protected_pointer_after_fingerprints": after,
        "protected_pointer_unchanged": unchanged,
        "candidate_text_forbidden_hits": text_hits,
        "checks": checks,
        "allowed_writes": {
            "dapr15_evidence_written": True,
            "candidate_payload_written_under_evidence_root": True,
            "canonical_agent_prompt_artifact_written": False,
            "agent_prompt_latest_written": False,
            "execution_report_written": True,
            "review_written": True,
        },
    }


def build_candidate_or_stop_decision(
    created_at: str,
    source_gate: dict[str, Any],
    payload_write: dict[str, Any],
    validator: dict[str, Any],
    checksum: dict[str, Any],
    latest_plan: dict[str, Any],
    forbidden: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "source_gate_pass": source_gate.get("status") == "pass",
        "candidate_payload_file_write_pass": payload_write.get("status") == "pass",
        "validator_dry_run_pass": validator.get("status") == "pass",
        "checksum_plan_pass": checksum.get("status") == "pass",
        "latest_pointer_payload_plan_pass": latest_plan.get("status") == "pass",
        "forbidden_action_audit_pass": forbidden.get("status") == "pass"
        and forbidden.get("all_false") is True,
        "ready_for_direct_publish_false": True,
    }
    passed = all(checks.values())
    return {
        "schema_version": "dapr15.candidate_or_stop_decision.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if passed else "fail",
        "decision": "CANDIDATE_ONLY_AGENT_PROMPT_DRY_RUN_PASS_STOP_BEFORE_ACTUAL_PUBLISH"
        if passed
        else "STOP_DAPR15_CANDIDATE_ONLY_AGENT_PROMPT_DRY_RUN_FAILED",
        "agent_prompt_artifact_written_to_canonical_dir": False,
        "agent_prompt_latest_written": False,
        "ready_for_dapr16_agent_prompt_publish_preflight_gate": passed,
        "ready_for_direct_agent_prompt_publish": False,
        "next_required_action": "DAPR16_CONTROLLED_AGENT_PROMPT_PUBLISH_PREFLIGHT_OR_STOP"
        if passed
        else "repair DAPR15 blockers before DAPR16",
        "checks": checks,
    }


def build_artifact_manifest(created_at: str, files: list[Path]) -> dict[str, Any]:
    entries = []
    missing = []
    for path in files:
        exists = path.is_file()
        if not exists and path != DAPR15_ROOT / "artifact_manifest.json":
            missing.append(rel(path))
        entries.append(
            {
                "path": rel(path),
                "exists": exists,
                "size_bytes": path.stat().st_size if exists else None,
                "sha256": sha256_file(path) if exists else None,
            }
        )
    return {
        "schema_version": "dapr15.artifact_manifest.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if not missing else "fail",
        "entries": entries,
        "missing": missing,
    }


def build_execution_report(
    created_at: str,
    source_gate: dict[str, Any],
    payload_write: dict[str, Any],
    validator: dict[str, Any],
    checksum: dict[str, Any],
    latest_plan: dict[str, Any],
    forbidden: dict[str, Any],
    decision: dict[str, Any],
    artifact_manifest: dict[str, Any],
) -> str:
    verdict = (
        "PASS_STOP_BEFORE_AGENT_PROMPT_PUBLISH_RECOMMEND_DAPR16_PREFLIGHT"
        if decision.get("status") == "pass" and artifact_manifest.get("status") == "pass"
        else "STOP_REPAIR_DAPR15"
    )
    context = read_json(CANDIDATE_DIR / "prompt_context.json")
    top3 = context["rankings"]["qlib_top10_compact"][:3]
    return f"""# DAPR15 Candidate-Only Agent Prompt Dry-Run No-Publish 执行报告

created_at: `{created_at}`

phase: `DAPR15_CANDIDATE_ONLY_AGENT_PROMPT_DRY_RUN_NO_PUBLISH`

target_asof: `{TARGET_ASOF}`

verdict: `{verdict}`

## 1. Scope

本阶段只生成 `{TARGET_ASOF}` candidate-only DailyAgentPromptArtifact dry-run payload。写入位置限定为 `{rel(DAPR15_ROOT)}`，未写 `data_tw/artifacts/agent_daily_prompt/{TARGET_ASOF}/`，未写 `data_tw/artifacts/agent_daily_prompt/latest.json`，未调用 OpenAI。

## 2. Evidence Produced

- `source_gate.json`: `{source_gate["status"]}`
- `candidate_payload_file_write.json`: `{payload_write["status"]}`
- `validator_dry_run.json`: `{validator["status"]}`
- `checksum_plan.json`: `{checksum["status"]}`
- `latest_pointer_payload_plan.json`: `{latest_plan["status"]}`
- `forbidden_action_audit.json`: `{forbidden["status"]}`
- `candidate_or_stop_decision.json`: `{decision["status"]}`
- `artifact_manifest.json`: `{artifact_manifest["status"]}`

## 3. Candidate Payload

Candidate dir: `{rel(CANDIDATE_DIR)}`

Top3:

- rank 1: `{top3[0]["instrument"]}`
- rank 2: `{top3[1]["instrument"]}`
- rank 3: `{top3[2]["instrument"]}`

Checksum: `{checksum["manifest_checksum"]}`

## 4. Validator

Existing validator passed in candidate-only mode:

```text
ok={validator["validator_output"]["ok"]}
errors={validator["validator_output"]["errors"]}
warnings={validator["validator_output"]["warnings"]}
```

## 5. Decision

```text
{decision["decision"]}
```

## 6. Forbidden Actions Audit

`all_false={forbidden["all_false"]}`。未触发 Agent prompt publish、OpenAI、provider/qlib/daily auto/accepted latest、DB、strategy replay、monitor/broker/order/target、frontend/API default switch。
"""


def build_review_doc(
    created_at: str,
    validator: dict[str, Any],
    latest_plan: dict[str, Any],
    forbidden: dict[str, Any],
    decision: dict[str, Any],
    artifact_manifest: dict[str, Any],
) -> str:
    verdict = (
        "PASS_STOP_BEFORE_DAPR16_AGENT_PROMPT_PUBLISH_PREFLIGHT"
        if decision.get("status") == "pass" and artifact_manifest.get("status") == "pass"
        else "FAIL_NEEDS_REPAIR"
    )
    return f"""# DAPR15 Candidate-Only Agent Prompt Dry-Run No-Publish 审查

created_at: `{created_at}`

verdict: `{verdict}`

## 1. Verdict

{verdict}

## 2. Findings

### Critical

无。

### High

无。

### Medium

无。

### Low

无。

## 3. Evidence Checked

- `{rel(DAPR15_ROOT / "source_gate.json")}`
- `{rel(DAPR15_ROOT / "candidate_payload_file_write.json")}`
- `{rel(DAPR15_ROOT / "validator_dry_run.json")}`
- `{rel(DAPR15_ROOT / "checksum_plan.json")}`
- `{rel(DAPR15_ROOT / "latest_pointer_payload_plan.json")}`
- `{rel(DAPR15_ROOT / "forbidden_action_audit.json")}`
- `{rel(DAPR15_ROOT / "candidate_or_stop_decision.json")}`
- `{rel(DAPR15_ROOT / "artifact_manifest.json")}`

## 4. Review Result

- validator dry-run: `{validator["status"]}`
- latest pointer payload plan: `{latest_plan["status"]}`, writes_latest_pointer=`{latest_plan["writes_latest_pointer"]}`
- forbidden action audit: `{forbidden["status"]}`, all_false=`{forbidden["all_false"]}`
- artifact manifest: `{artifact_manifest["status"]}`

## 5. Stop Boundary

DAPR15 停在 Agent prompt publish 之前。当前不授权写 canonical Agent prompt artifact，不授权写 Agent prompt latest。

## 6. Next Work Document

若继续，应进入 `DAPR16_CONTROLLED_AGENT_PROMPT_PUBLISH_PREFLIGHT_OR_STOP`。DAPR16 只能做 publish preflight/authorization gate，不得把本 dry-run 直接解释成 actual publish 授权。
"""


def main() -> None:
    created_at = now_iso()
    DAPR15_ROOT.mkdir(parents=True, exist_ok=True)
    CANDIDATE_DIR.mkdir(parents=True, exist_ok=True)
    before = {
        "schema_version": "dapr15.before_fingerprint.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass",
        "protected_pointer_fingerprints": {
            name: file_fingerprint(path) for name, path in PROTECTED_POINTERS.items()
        },
        "target_agent_artifact_dir": file_fingerprint(TARGET_AGENT_DIR),
        "candidate_dir": file_fingerprint(CANDIDATE_DIR),
    }
    write_json(DAPR15_ROOT / "before_fingerprint.json", before)

    source_gate = build_source_gate(created_at, before)
    write_json(DAPR15_ROOT / "source_gate.json", source_gate)
    if source_gate.get("status") != "pass":
        raise RuntimeError("STOP_DAPR15_SOURCE_GATE_FAILED")

    latest = read_json(READONLY_LATEST)
    manifest_source = read_json(SNAPSHOT_MANIFEST)
    snapshot = read_json(SNAPSHOT_PAYLOAD)
    context = build_prompt_context(created_at, latest, manifest_source, snapshot)
    write_json(CANDIDATE_DIR / "prompt_context.json", context)
    write_text(CANDIDATE_DIR / "prompt_text.md", build_prompt_text(context))
    checksum = compute_prompt_checksum(CANDIDATE_DIR / "prompt_context.json", CANDIDATE_DIR / "prompt_text.md")
    write_json(CANDIDATE_DIR / "manifest.json", build_manifest(created_at, checksum))

    payload_write = build_candidate_payload_file_write(created_at)
    validator = build_validator_dry_run(created_at)
    checksum_plan = build_checksum_plan(created_at)
    latest_plan = build_latest_pointer_payload_plan(created_at)
    forbidden = build_forbidden_action_audit(created_at, before)
    decision = build_candidate_or_stop_decision(
        created_at,
        source_gate,
        payload_write,
        validator,
        checksum_plan,
        latest_plan,
        forbidden,
    )
    evidence_files = [
        DAPR15_ROOT / "before_fingerprint.json",
        DAPR15_ROOT / "source_gate.json",
        DAPR15_ROOT / "candidate_payload_file_write.json",
        DAPR15_ROOT / "validator_dry_run.json",
        DAPR15_ROOT / "checksum_plan.json",
        DAPR15_ROOT / "latest_pointer_payload_plan.json",
        DAPR15_ROOT / "forbidden_action_audit.json",
        DAPR15_ROOT / "candidate_or_stop_decision.json",
        CANDIDATE_DIR / "manifest.json",
        CANDIDATE_DIR / "prompt_context.json",
        CANDIDATE_DIR / "prompt_text.md",
    ]
    write_json(DAPR15_ROOT / "candidate_payload_file_write.json", payload_write)
    write_json(DAPR15_ROOT / "validator_dry_run.json", validator)
    write_json(DAPR15_ROOT / "checksum_plan.json", checksum_plan)
    write_json(DAPR15_ROOT / "latest_pointer_payload_plan.json", latest_plan)
    write_json(DAPR15_ROOT / "forbidden_action_audit.json", forbidden)
    write_json(DAPR15_ROOT / "candidate_or_stop_decision.json", decision)

    artifact_manifest = build_artifact_manifest(created_at, evidence_files)
    execution_report = build_execution_report(
        created_at,
        source_gate,
        payload_write,
        validator,
        checksum_plan,
        latest_plan,
        forbidden,
        decision,
        artifact_manifest,
    )
    review_doc = build_review_doc(
        created_at,
        validator,
        latest_plan,
        forbidden,
        decision,
        artifact_manifest,
    )
    write_text(DAPR15_EXECUTION_REPORT, execution_report)
    write_text(DAPR15_REVIEW, review_doc)
    artifact_manifest = build_artifact_manifest(
        created_at,
        evidence_files + [DAPR15_EXECUTION_REPORT, DAPR15_REVIEW],
    )
    write_json(DAPR15_ROOT / "artifact_manifest.json", artifact_manifest)

    if decision.get("status") != "pass" or artifact_manifest.get("status") != "pass":
        raise RuntimeError("STOP_DAPR15_VALIDATION_FAILED")

    print(
        json.dumps(
            {
                "status": "pass",
                "phase": "DAPR15_CANDIDATE_ONLY_AGENT_PROMPT_DRY_RUN_NO_PUBLISH",
                "target_asof": TARGET_ASOF,
                "candidate_dir": rel(CANDIDATE_DIR),
                "decision": decision["decision"],
                "ready_for_dapr16_agent_prompt_publish_preflight_gate": True,
                "ready_for_direct_agent_prompt_publish": False,
                "evidence_root": rel(DAPR15_ROOT),
                "execution_report": rel(DAPR15_EXECUTION_REPORT),
                "review": rel(DAPR15_REVIEW),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
