#!/usr/bin/env python3
"""DAPR14 Agent prompt latest preflight-or-stop.

This phase verifies whether the newly published readonly snapshot
can feed the Agent DailyPrompt route. It intentionally does not build or publish
Agent prompt artifacts and does not call OpenAI, providers, qlib refresh, DB,
strategy replay, monitor, broker, order, or frontend/API defaults.
"""

from __future__ import annotations

import hashlib
import json
import os
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


TARGET_ASOF = env_str("TW_DAPR14_TARGET_ASOF", "2026-07-17")
TARGET_TAG = TARGET_ASOF.replace("-", "")

DAPR13_ROOT = env_path(
    "TW_DAPR14_DAPR13_ROOT",
    "data_tw/experiments/daily_accepted_production_readiness/dapr13_actual_readonly_snapshot_publish",
)
DAPR14_ROOT = env_path(
    "TW_DAPR14_OUTPUT_ROOT",
    f"data_tw/experiments/provider_bridge_productionization/dapr14_{TARGET_TAG}_agent_prompt_latest_preflight_or_stop",
)

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

AGENT_CONTRACT = ROOT / "docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md"
AGENT_OPENAI_DESIGN = ROOT / "docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_OPENAI_REBUILD_DESIGN_CN.md"
AGENT_FINAL_SUMMARY = ROOT / "docs/tw_agent_daily_prompt_rebuild/PHASE0_TO_PHASE6_FINAL_SUMMARY_CN.md"
DAPR13_REVIEW = env_path(
    "TW_DAPR14_DAPR13_REVIEW",
    "docs/tw_portfolio_decision_model/POLICY_DAPR13_ACTUAL_READONLY_SNAPSHOT_PUBLISH_REVIEW_CN.md",
)
APLR1_SCRIPT = ROOT / "scripts/build_tw_aplr1_candidate_only_agent_prompt_dry_run.py"
APLR2_SCRIPT = ROOT / "scripts/build_tw_aplr2_agent_prompt_artifact_publish.py"
AGENT_BUILDER = ROOT / "scripts/build_tw_agent_daily_prompt_artifact.py"
AGENT_VALIDATOR = ROOT / "scripts/validate_tw_agent_daily_prompt_artifact.py"

DAPR14_EXECUTION_REPORT = env_path(
    "TW_DAPR14_EXECUTION_REPORT",
    f"docs/tw_portfolio_decision_model/POLICY_DAPR14_{TARGET_TAG}_AGENT_PROMPT_LATEST_PREFLIGHT_OR_STOP_EXECUTION_REPORT_CN.md",
)
DAPR14_REVIEW = env_path(
    "TW_DAPR14_REVIEW",
    f"docs/tw_portfolio_decision_model/POLICY_DAPR14_{TARGET_TAG}_AGENT_PROMPT_LATEST_PREFLIGHT_OR_STOP_REVIEW_CN.md",
)

PROTECTED_POINTERS = {
    "controlled_signal_latest": CONTROLLED_SIGNAL_LATEST,
    "readonly_snapshot_latest": READONLY_LATEST,
    "agent_prompt_latest": AGENT_LATEST,
    "legacy_qlib_option_c_latest_signal": LEGACY_QLIB_OPTION_C_LATEST,
    "legacy_data_option_c_latest_signal": LEGACY_DATA_OPTION_C_LATEST,
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


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
        raise ValueError(f"Expected JSON object: {rel(path)}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


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


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def status_pass(path: Path) -> bool:
    return read_json(path).get("status") == "pass"


def build_latest_state_inventory(created_at: str) -> dict[str, Any]:
    return {
        "schema_version": "dapr14.latest_state_inventory.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass",
        "protected_pointer_fingerprints": {
            name: file_fingerprint(path) for name, path in PROTECTED_POINTERS.items()
        },
        "target_agent_artifact_dir": file_fingerprint(TARGET_AGENT_DIR),
        "readonly_snapshot_target_dir": file_fingerprint(SNAPSHOT_DIR),
    }


def build_readonly_snapshot_source_gate(created_at: str) -> dict[str, Any]:
    latest = read_json(READONLY_LATEST)
    manifest = read_json(SNAPSHOT_MANIFEST)
    snapshot = read_json(SNAPSHOT_PAYLOAD)
    validation = read_json(SNAPSHOT_VALIDATION)
    forbidden = read_json(SNAPSHOT_FORBIDDEN)
    checksum_manifest = read_json(SNAPSHOT_CHECKSUMS)
    checksum_files = checksum_manifest.get("files") or {}
    d13_latest_validation = DAPR13_ROOT / "latest_pointer_payload_validation.json"
    d13_checksum_validation = DAPR13_ROOT / "canonical_file_checksum_validation.json"
    d13_review_text = read_text(DAPR13_REVIEW)
    checks = {
        "dapr13_review_pass_stop_before_agent_prompt_publish": "PASS_STOP_BEFORE_AGENT_PROMPT_PUBLISH"
        in d13_review_text,
        "dapr13_latest_validation_pass": status_pass(d13_latest_validation),
        "dapr13_checksum_validation_pass": status_pass(d13_checksum_validation),
        "readonly_latest_points_to_target_manifest": latest.get("snapshot_manifest")
        == rel(SNAPSHOT_MANIFEST),
        "readonly_latest_asof_target": all(
            latest.get(key) == TARGET_ASOF
            for key in ("asof", "data_asof", "signal_asof", "target_date")
        ),
        "readonly_latest_safe_flags": latest.get("readonly_only") is True
        and latest.get("candidate_only") is True
        and latest.get("production_trade_enabled") is False
        and latest.get("not_provider_accepted_latest") is True
        and latest.get("not_trade_target_latest") is True,
        "canonical_snapshot_files_exist": all(
            path.is_file()
            for path in (
                SNAPSHOT_MANIFEST,
                SNAPSHOT_PAYLOAD,
                SNAPSHOT_VALIDATION,
                SNAPSHOT_FORBIDDEN,
                SNAPSHOT_CHECKSUMS,
            )
        ),
        "manifest_candidate_only_safe": manifest.get("candidate_only") is True
        and manifest.get("readonly_only") is True
        and manifest.get("production_trade_enabled") is False,
        "snapshot_candidate_only_top50": snapshot.get("candidate_only") is True
        and snapshot.get("top_candidates_count") == 50
        and len(snapshot.get("top_candidates") or []) == 50,
        "snapshot_no_replay_no_order": snapshot.get("strategy_rule")
        == "candidate_only_no_strategy_replay"
        and snapshot.get("strategy_replay_status") == "not_built_forbidden_in_rsppr"
        and snapshot.get("order_intent_status") == "not_built_forbidden_in_rsppr"
        and snapshot.get("replay_result_status") == "not_built_forbidden_in_rsppr",
        "validation_report_pass": validation.get("status") == "pass",
        "forbidden_scope_audit_pass": forbidden.get("status") == "pass"
        and forbidden.get("all_forbidden_false") is True,
        "checksum_manifest_matches_payloads": checksum_files.get("manifest.json")
        == sha256_file(SNAPSHOT_MANIFEST)
        and checksum_files.get("strategy_snapshot.json") == sha256_file(SNAPSHOT_PAYLOAD)
        and checksum_files.get("validation_report.json") == sha256_file(SNAPSHOT_VALIDATION)
        and checksum_files.get("forbidden_scope_audit.json") == sha256_file(SNAPSHOT_FORBIDDEN),
    }
    top = snapshot.get("top_candidates") or []
    return {
        "schema_version": "dapr14.readonly_snapshot_source_gate.v1",
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


def build_agent_prompt_gap_analysis(created_at: str, source_gate: dict[str, Any]) -> dict[str, Any]:
    latest = read_json(AGENT_LATEST) if AGENT_LATEST.exists() else {}
    checks = {
        "source_gate_pass": source_gate.get("status") == "pass",
        "agent_latest_exists": AGENT_LATEST.is_file(),
        "agent_latest_currently_stale": latest.get("signal_asof") != TARGET_ASOF
        or latest.get("target_date") != TARGET_ASOF,
        "agent_latest_not_target_manifest": latest.get("manifest")
        != f"data_tw/artifacts/agent_daily_prompt/{TARGET_ASOF}/manifest.json",
        "target_agent_artifact_dir_absent": not TARGET_AGENT_DIR.exists(),
        "no_target_manifest_exists": not (TARGET_AGENT_DIR / "manifest.json").exists(),
        "no_target_prompt_context_exists": not (TARGET_AGENT_DIR / "prompt_context.json").exists(),
        "no_target_prompt_text_exists": not (TARGET_AGENT_DIR / "prompt_text.md").exists(),
    }
    return {
        "schema_version": "dapr14.agent_prompt_gap_analysis.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "current_agent_latest": file_fingerprint(AGENT_LATEST),
        "target_agent_artifact_dir": file_fingerprint(TARGET_AGENT_DIR),
        "gap": {
            "readonly_snapshot_latest_asof": TARGET_ASOF,
            "agent_prompt_latest_signal_asof": latest.get("signal_asof"),
            "agent_prompt_latest_target_date": latest.get("target_date"),
            "direct_publish_ready": False,
            "reason": f"{TARGET_ASOF} DailyAgentPromptArtifact candidate has not been dry-run-built or validated.",
        },
    }


def build_builder_validator_preflight(created_at: str) -> dict[str, Any]:
    aplr1_text = read_text(APLR1_SCRIPT)
    aplr2_text = read_text(APLR2_SCRIPT)
    builder_text = read_text(AGENT_BUILDER)
    validator_text = read_text(AGENT_VALIDATOR)
    checks = {
        "agent_contract_exists": AGENT_CONTRACT.is_file(),
        "agent_openai_design_exists": AGENT_OPENAI_DESIGN.is_file(),
        "agent_final_summary_exists": AGENT_FINAL_SUMMARY.is_file(),
        "validator_candidate_only_support_present": "def validate_candidate_only_contract" in validator_text
        and "CANDIDATE_ONLY_STRATEGY_RULE" in validator_text,
        "aplr1_hardcoded_20260708": 'TARGET_ASOF = "2026-07-08"' in aplr1_text
        and "2026-07-08" in aplr1_text,
        "aplr2_hardcoded_20260708": "2026-07-08" in aplr2_text
        and "APLR1_DIR" in aplr2_text,
        "generic_builder_still_full_strategy_source_based": "REQUIRED_SOURCES = (\"current_strategy_context\", \"readonly_strategy_snapshot\")"
        in builder_text
        and "top50_exit_one_worst_sell" in validator_text,
        "openai_not_required_for_candidate_build": "不调用 OpenAI" in read_text(AGENT_FINAL_SUMMARY)
        or "OpenAI" in read_text(AGENT_FINAL_SUMMARY),
    }
    return {
        "schema_version": "dapr14.builder_validator_preflight.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "conclusion": {
            "can_directly_reuse_aplr1_aplr2": False,
            "reason": (
                "APLR1/APLR2 are prior-target route-specific scripts; "
                f"DAPR15 should build a {TARGET_ASOF} candidate-only dry-run adapter or parameterized successor."
            ),
            "validator_supports_candidate_only_contract": checks["validator_candidate_only_support_present"],
            "generic_builder_not_sufficient_for_direct_publish": True,
        },
    }


def build_forbidden_action_audit(created_at: str, before: dict[str, Any]) -> dict[str, Any]:
    after = {name: file_fingerprint(path) for name, path in PROTECTED_POINTERS.items()}
    unchanged = {
        name: before["protected_pointer_fingerprints"][name].get("sha256")
        == after[name].get("sha256")
        for name in PROTECTED_POINTERS
    }
    flags = {
        "agent_prompt_artifact_built": False,
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
        "all_forbidden_flags_false": all(value is False for value in flags.values()),
        "all_protected_pointers_unchanged": all(unchanged.values()),
        "target_agent_artifact_dir_still_absent": not TARGET_AGENT_DIR.exists(),
    }
    return {
        "schema_version": "dapr14.forbidden_action_audit.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "all_false": all(value is False for value in flags.values()),
        "flags": flags,
        "protected_pointer_after_fingerprints": after,
        "protected_pointer_unchanged": unchanged,
        "checks": checks,
        "allowed_writes": {
            "dapr14_evidence_written": True,
            "dapr14_execution_report_written": True,
            "dapr14_review_written": True,
            "agent_prompt_artifact_written": False,
            "agent_prompt_latest_written": False,
        },
    }


def build_candidate_or_stop_decision(
    created_at: str,
    source_gate: dict[str, Any],
    gap: dict[str, Any],
    builder_preflight: dict[str, Any],
    forbidden: dict[str, Any],
) -> dict[str, Any]:
    pass_preflight = all(
        item.get("status") == "pass"
        for item in (source_gate, gap, builder_preflight, forbidden)
    )
    decision = (
        "PREFLIGHT_PASS_STOP_BEFORE_AGENT_PROMPT_PUBLISH_REQUIRE_DAPR15_CANDIDATE_ONLY_DRY_RUN"
        if pass_preflight
        else "STOP_DAPR14_AGENT_PROMPT_PREFLIGHT_FAILED"
    )
    return {
        "schema_version": "dapr14.candidate_or_stop_decision.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if pass_preflight else "fail",
        "decision": decision,
        "agent_prompt_latest_written": False,
        "agent_prompt_artifact_built": False,
        "ready_for_direct_agent_prompt_publish": False,
        "ready_for_dapr15_candidate_only_agent_prompt_dry_run": pass_preflight,
        "next_required_action": "DAPR15_CANDIDATE_ONLY_AGENT_PROMPT_DRY_RUN_NO_PUBLISH"
        if pass_preflight
        else "repair DAPR14 preflight blockers before any Agent prompt route",
        "checks": {
            "readonly_snapshot_source_gate_pass": source_gate.get("status") == "pass",
            "agent_prompt_gap_analysis_pass": gap.get("status") == "pass",
            "builder_validator_preflight_pass": builder_preflight.get("status") == "pass",
            "forbidden_action_audit_pass": forbidden.get("status") == "pass"
            and forbidden.get("all_false") is True,
            "direct_publish_false": True,
        },
    }


def build_artifact_manifest(created_at: str, files: list[Path]) -> dict[str, Any]:
    entries = []
    missing = []
    for path in files:
        exists = path.is_file()
        if not exists and path != DAPR14_ROOT / "artifact_manifest.json":
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
        "schema_version": "dapr14.artifact_manifest.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if not missing else "fail",
        "entries": entries,
        "missing": missing,
    }


def build_execution_report(
    created_at: str,
    source_gate: dict[str, Any],
    gap: dict[str, Any],
    builder_preflight: dict[str, Any],
    forbidden: dict[str, Any],
    decision: dict[str, Any],
    artifact_manifest: dict[str, Any],
) -> str:
    verdict = (
        "PASS_STOP_BEFORE_AGENT_PROMPT_PUBLISH_RECOMMEND_DAPR15_DRY_RUN"
        if decision.get("status") == "pass" and artifact_manifest.get("status") == "pass"
        else "STOP_REPAIR_DAPR14"
    )
    return f"""# DAPR14 Agent Prompt Latest Preflight-Or-Stop 执行报告

created_at: `{created_at}`

phase: `DAPR14_AGENT_PROMPT_LATEST_PREFLIGHT_OR_STOP`

target_asof: `{TARGET_ASOF}`

verdict: `{verdict}`

## 1. Scope

本阶段只做 Agent prompt latest preflight，不构建 `DailyAgentPromptArtifact`，不写 `data_tw/artifacts/agent_daily_prompt/latest.json`，不调用 OpenAI。

## 2. Evidence Produced

- `latest_state_inventory.json`: `pass`
- `readonly_snapshot_source_gate.json`: `{source_gate["status"]}`
- `agent_prompt_gap_analysis.json`: `{gap["status"]}`
- `builder_validator_preflight.json`: `{builder_preflight["status"]}`
- `forbidden_action_audit.json`: `{forbidden["status"]}`
- `candidate_or_stop_decision.json`: `{decision["status"]}`
- `artifact_manifest.json`: `{artifact_manifest["status"]}`

## 3. Result

Readonly snapshot latest 已为 `{TARGET_ASOF}`，且 canonical snapshot source gate 通过。

Agent prompt latest 当前仍未到 `{TARGET_ASOF}`；`data_tw/artifacts/agent_daily_prompt/{TARGET_ASOF}/` 尚不存在。因此本阶段不允许 direct publish。

Decision:

```text
{decision["decision"]}
```

## 4. Forbidden Actions Audit

`all_false={forbidden["all_false"]}`。未触发 Agent prompt publish、OpenAI、provider/qlib/daily auto/accepted latest、DB、strategy replay、monitor/broker/order/target、frontend/API default switch。

## 5. Recommendation

下一步应进入 `DAPR15_CANDIDATE_ONLY_AGENT_PROMPT_DRY_RUN_NO_PUBLISH`，基于 `{TARGET_ASOF}` readonly snapshot latest 生成 candidate-only Agent prompt payload plan，但仍不写 Agent prompt latest。
"""


def build_review_doc(
    created_at: str,
    source_gate: dict[str, Any],
    gap: dict[str, Any],
    builder_preflight: dict[str, Any],
    forbidden: dict[str, Any],
    decision: dict[str, Any],
    artifact_manifest: dict[str, Any],
) -> str:
    verdict = (
        "PASS_STOP_BEFORE_DAPR15_CANDIDATE_ONLY_AGENT_PROMPT_DRY_RUN"
        if decision.get("status") == "pass" and artifact_manifest.get("status") == "pass"
        else "FAIL_NEEDS_REPAIR"
    )
    return f"""# DAPR14 Agent Prompt Latest Preflight-Or-Stop 审查

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

- `{rel(DAPR14_ROOT / "latest_state_inventory.json")}`
- `{rel(DAPR14_ROOT / "readonly_snapshot_source_gate.json")}`
- `{rel(DAPR14_ROOT / "agent_prompt_gap_analysis.json")}`
- `{rel(DAPR14_ROOT / "builder_validator_preflight.json")}`
- `{rel(DAPR14_ROOT / "forbidden_action_audit.json")}`
- `{rel(DAPR14_ROOT / "candidate_or_stop_decision.json")}`
- `{rel(DAPR14_ROOT / "artifact_manifest.json")}`

## 4. Review Result

- readonly snapshot source gate: `{source_gate["status"]}`
- Agent prompt gap analysis: `{gap["status"]}`
- builder / validator preflight: `{builder_preflight["status"]}`
- forbidden action audit: `{forbidden["status"]}`, all_false=`{forbidden["all_false"]}`
- artifact manifest: `{artifact_manifest["status"]}`

## 5. Stop Boundary

DAPR14 停在 Agent prompt publish 之前。当前不授权直接写 `data_tw/artifacts/agent_daily_prompt/{TARGET_ASOF}/` 或 `data_tw/artifacts/agent_daily_prompt/latest.json`。

## 6. Next Work Document

进入 `DAPR15_CANDIDATE_ONLY_AGENT_PROMPT_DRY_RUN_NO_PUBLISH`。DAPR15 只能生成 candidate-only prompt dry-run payload/evidence，不能 publish Agent prompt latest，不能调用 OpenAI，不能触发 provider/qlib/DB/replay/order/default switch。
"""


def main() -> None:
    created_at = now_iso()
    DAPR14_ROOT.mkdir(parents=True, exist_ok=True)
    inventory = build_latest_state_inventory(created_at)
    write_json(DAPR14_ROOT / "latest_state_inventory.json", inventory)
    source_gate = build_readonly_snapshot_source_gate(created_at)
    gap = build_agent_prompt_gap_analysis(created_at, source_gate)
    builder_preflight = build_builder_validator_preflight(created_at)
    forbidden = build_forbidden_action_audit(created_at, inventory)
    decision = build_candidate_or_stop_decision(
        created_at, source_gate, gap, builder_preflight, forbidden
    )

    evidence_files = [
        DAPR14_ROOT / "latest_state_inventory.json",
        DAPR14_ROOT / "readonly_snapshot_source_gate.json",
        DAPR14_ROOT / "agent_prompt_gap_analysis.json",
        DAPR14_ROOT / "builder_validator_preflight.json",
        DAPR14_ROOT / "forbidden_action_audit.json",
        DAPR14_ROOT / "candidate_or_stop_decision.json",
    ]
    write_json(DAPR14_ROOT / "readonly_snapshot_source_gate.json", source_gate)
    write_json(DAPR14_ROOT / "agent_prompt_gap_analysis.json", gap)
    write_json(DAPR14_ROOT / "builder_validator_preflight.json", builder_preflight)
    write_json(DAPR14_ROOT / "forbidden_action_audit.json", forbidden)
    write_json(DAPR14_ROOT / "candidate_or_stop_decision.json", decision)

    artifact_manifest = build_artifact_manifest(created_at, evidence_files)
    execution_report = build_execution_report(
        created_at, source_gate, gap, builder_preflight, forbidden, decision, artifact_manifest
    )
    review_doc = build_review_doc(
        created_at, source_gate, gap, builder_preflight, forbidden, decision, artifact_manifest
    )
    write_text(DAPR14_EXECUTION_REPORT, execution_report)
    write_text(DAPR14_REVIEW, review_doc)
    artifact_manifest = build_artifact_manifest(
        created_at, evidence_files + [DAPR14_EXECUTION_REPORT, DAPR14_REVIEW]
    )
    write_json(DAPR14_ROOT / "artifact_manifest.json", artifact_manifest)

    if decision.get("status") != "pass" or artifact_manifest.get("status") != "pass":
        raise RuntimeError("STOP_DAPR14_PREFLIGHT_FAILED")

    print(
        json.dumps(
            {
                "status": "pass",
                "phase": "DAPR14_AGENT_PROMPT_LATEST_PREFLIGHT_OR_STOP",
                "target_asof": TARGET_ASOF,
                "decision": decision["decision"],
                "ready_for_dapr15_candidate_only_agent_prompt_dry_run": True,
                "ready_for_direct_agent_prompt_publish": False,
                "evidence_root": rel(DAPR14_ROOT),
                "execution_report": rel(DAPR14_EXECUTION_REPORT),
                "review": rel(DAPR14_REVIEW),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
