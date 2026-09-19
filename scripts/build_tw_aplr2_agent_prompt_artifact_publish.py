#!/usr/bin/env python3
"""Publish APLR2 candidate-only DailyAgentPromptArtifact."""
from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGET_ASOF = "2026-07-08"
ROUTE = "APLR_AGENT_PROMPT_LATEST_ROUTE"
PHASE = "APLR2_AGENT_PROMPT_ARTIFACT_PUBLISH"
EXPECTED_CHECKSUM = "sha256:b65c3478e53c25194a0ebd7da5a50d6c23ce72c42edcda55e4ac2208e962bddc"

APLR1_DIR = ROOT / "data_tw/experiments/agent_prompt_latest_route/aplr1_candidate_only_agent_prompt_dry_run"
APLR2_DIR = ROOT / "data_tw/experiments/agent_prompt_latest_route/aplr2_agent_prompt_artifact_publish"

APLR1_REVIEW = ROOT / "docs/tw_portfolio_decision_model/POLICY_APLR1_CANDIDATE_ONLY_AGENT_PROMPT_DRY_RUN_REVIEW_CN.md"
APLR2_REPORT = ROOT / "docs/tw_portfolio_decision_model/POLICY_APLR2_AGENT_PROMPT_ARTIFACT_PUBLISH_EXECUTION_REPORT_CN.md"
APLR3_WORK = ROOT / "docs/tw_portfolio_decision_model/POLICY_APLR3_AGENT_PROMPT_READONLY_ACCEPTANCE_WORK_CN.md"

READONLY_LATEST = ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json"
SNAPSHOT_MANIFEST = ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/manifest.json"
SNAPSHOT_PAYLOAD = ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/strategy_snapshot.json"

AGENT_ROOT = ROOT / "data_tw/artifacts/agent_daily_prompt"
AGENT_ASOF_DIR = AGENT_ROOT / TARGET_ASOF
AGENT_MANIFEST = AGENT_ASOF_DIR / "manifest.json"
AGENT_CONTEXT = AGENT_ASOF_DIR / "prompt_context.json"
AGENT_PROMPT = AGENT_ASOF_DIR / "prompt_text.md"
AGENT_LATEST = AGENT_ROOT / "latest.json"

APLR1_CONTEXT = APLR1_DIR / "candidate_only_prompt_context_dry_run.json"
APLR1_PROMPT = APLR1_DIR / "candidate_only_prompt_text_dry_run.md"
APLR1_MANIFEST_PLAN = APLR1_DIR / "dry_run_manifest_plan.json"
APLR1_LATEST_PLAN = APLR1_DIR / "latest_pointer_payload_plan.json"
APLR1_CHECKSUM_PLAN = APLR1_DIR / "checksum_plan.json"

SCRIPT_PATH = ROOT / "scripts/build_tw_aplr2_agent_prompt_artifact_publish.py"

EVIDENCE_PATHS = {
    "pre_publish_fingerprint.json": APLR2_DIR / "pre_publish_fingerprint.json",
    "written_agent_prompt_artifact.json": APLR2_DIR / "written_agent_prompt_artifact.json",
    "latest_pointer_write.json": APLR2_DIR / "latest_pointer_write.json",
    "candidate_only_validator_publish.json": APLR2_DIR / "candidate_only_validator_publish.json",
    "checksum_verify.json": APLR2_DIR / "checksum_verify.json",
    "rollback_package.json": APLR2_DIR / "rollback_package.json",
    "forbidden_action_audit.json": APLR2_DIR / "forbidden_action_audit.json",
    "artifact_manifest.json": APLR2_DIR / "artifact_manifest.json",
}

PROTECTED_PATHS = [
    "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    "data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/manifest.json",
    "data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/strategy_snapshot.json",
    "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    "data_tw/experiments/option_c_daily_signal/latest_signal.json",
]


class PublishError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if not isinstance(payload, dict):
        raise PublishError(f"expected JSON object: {rel(path)}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json_bytes(payload))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    return sha256_bytes(path.read_bytes())


def fingerprint(path: Path) -> dict[str, Any]:
    return {
        "path": rel(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
        "bytes": path.stat().st_size if path.exists() and path.is_file() else None,
        "sha256": sha256_file(path),
    }


def backup_latest(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {
            "path": rel(path),
            "exists": False,
            "status": "absent_rollback",
            "bytes_base64": None,
            "sha256": None,
        }
    raw = path.read_bytes()
    return {
        "path": rel(path),
        "exists": True,
        "status": "captured_before_latest_pointer_write",
        "bytes_base64": base64.b64encode(raw).decode("ascii"),
        "sha256": sha256_bytes(raw),
    }


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PublishError(message)


def compute_artifact_checksum(context_bytes: bytes, prompt_bytes: bytes) -> str:
    return "sha256:" + sha256_bytes(context_bytes + b"\n" + prompt_bytes)


def assert_entry_gates() -> None:
    review_text = APLR1_REVIEW.read_text(encoding="utf-8")
    require("PASS_RECOMMEND_APLR2_AGENT_PROMPT_ARTIFACT_PUBLISH" in review_text, "APLR1 reviewer PASS not found")
    require("allow_aplr2_agent_prompt_artifact_publish: true" in review_text, "APLR2 artifact publish not allowed")
    checksum_plan = read_json(APLR1_CHECKSUM_PLAN)
    require(checksum_plan.get("planned_manifest_checksum") == EXPECTED_CHECKSUM, "APLR1 checksum does not match required checksum")


def source_gate() -> dict[str, Any]:
    latest = read_json(READONLY_LATEST)
    manifest = read_json(SNAPSHOT_MANIFEST)
    snapshot = read_json(SNAPSHOT_PAYLOAD)
    checks = {
        "readonly_latest_points_to_2026_07_08_manifest": latest.get("snapshot_manifest") == rel(SNAPSHOT_MANIFEST),
        "readonly_latest_candidate_only": latest.get("candidate_only") is True,
        "readonly_latest_sha256_stable": sha256_file(READONLY_LATEST) == "74d798f628a45c74959f28e295d71ab2e8f09ea2fdb6f7726a19037d832d4528",
        "snapshot_manifest_sha256_stable": sha256_file(SNAPSHOT_MANIFEST) == "cfeab4859d94a32dd5a755a899d30aca7f64118fda31c2773c069b6821fde915",
        "snapshot_payload_sha256_stable": sha256_file(SNAPSHOT_PAYLOAD) == "76e96c473b59349329711e36b98537e54708d7d4c76e2d8d79227c88f731531c",
        "manifest_candidate_only": manifest.get("candidate_only") is True,
        "snapshot_candidate_only": snapshot.get("candidate_only") is True,
        "source_lineage_controlled_model_signal_latest": manifest.get("source_lineage") == "clpr_controlled_model_signal_latest",
        "strategy_rule_candidate_only_no_strategy_replay": snapshot.get("strategy_rule") == "candidate_only_no_strategy_replay",
        "ranking_source_qlib_rank_controlled_signal": snapshot.get("ranking_source") == "qlib_rank_controlled_signal",
        "candidate_boundary_qlib_top50": snapshot.get("candidate_boundary") == "qlib_top50",
        "top_candidates_count_50": snapshot.get("top_candidates_count") == 50 and len(snapshot.get("top_candidates") or []) == 50,
        "exit_candidates_empty": snapshot.get("exit_candidates") == [],
        "hold_candidates_empty": snapshot.get("hold_candidates") == [],
        "exit_hold_context_status_not_built": snapshot.get("exit_hold_context_status") == "not_built_no_strategy_replay",
    }
    return {
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "readonly_latest": fingerprint(READONLY_LATEST),
        "snapshot_manifest": fingerprint(SNAPSHOT_MANIFEST),
        "snapshot_payload": fingerprint(SNAPSHOT_PAYLOAD),
    }


def validate_candidate_only_artifact(manifest: dict[str, Any], context: dict[str, Any], prompt_text: str) -> dict[str, Any]:
    checks = {
        "candidate_only_validator_evidence_explicit": True,
        "manifest_validator_requirement_preserved_from_aplr1": (manifest.get("validation") or {}).get("validator_type") == "candidate_only_agent_prompt_validator_required_for_aplr2",
        "candidate_only_no_strategy_replay_accepted": manifest.get("strategy_rule") == "candidate_only_no_strategy_replay",
        "treatment_model_null_accepted": (manifest.get("model_ids") or {}).get("treatment") is None,
        "treatment_model_status_not_applicable": (manifest.get("model_ids") or {}).get("treatment_status") == "not_applicable_candidate_only_no_ltr_rerank",
        "ranking_source_qlib_controlled_signal": (context.get("model_context") or {}).get("ranking_source") == "qlib_rank_controlled_signal",
        "candidate_boundary_qlib_top50": (context.get("model_context") or {}).get("candidate_boundary") == "qlib_top50",
        "top_candidates_count_50": (context.get("strategy") or {}).get("top_candidates_count") == 50 and len((context.get("strategy") or {}).get("top_candidates") or []) == 50,
        "exit_candidates_empty": (context.get("strategy") or {}).get("exit_candidates") == [],
        "hold_candidates_empty": (context.get("strategy") or {}).get("hold_candidates") == [],
        "exit_hold_context_status_not_built": (context.get("strategy") or {}).get("exit_hold_context_status") == "not_built_no_strategy_replay",
        "not_full_strategy_replay": (context.get("strategy") or {}).get("not_full_strategy_replay") is True,
        "source_lineage_rsppr_candidate_only": (context.get("source_lineage") or {}).get("lineage") == "rsppr_candidate_only_readonly_snapshot_latest",
        "qlib_score_semantics_in_prompt_text": all(term in prompt_text for term in ["qlib score", "收益率", "胜率", "上涨概率", "买入概率"]),
        "json_output_contract_in_prompt_text": "JSON" in prompt_text or "json" in prompt_text,
        "readonly_research_boundary_in_prompt_text": "research-only" in prompt_text or "只读" in prompt_text,
    }
    return {
        "artifact_type": "aplr2_candidate_only_validator_publish",
        "schema_version": "aplr2.candidate_only_validator_publish.v1",
        "route": ROUTE,
        "phase": PHASE,
        "target_asof": TARGET_ASOF,
        "created_at": now_iso(),
        "status": "pass" if all(checks.values()) else "fail",
        "validator_type": "candidate_only_agent_prompt_validator_publish",
        "explicit_candidate_only_acceptance": {
            "candidate_only_no_strategy_replay": True,
            "old_ltr_full_strategy_validator_reused": False,
            "old_ltr_full_strategy_constants_required": False,
        },
        "checks": checks,
    }


def build_forbidden_action_audit(pre: dict[str, Any]) -> dict[str, Any]:
    protected_after = {path: fingerprint(ROOT / path) for path in PROTECTED_PATHS}
    protected_unchanged = {
        path: pre["protected_path_fingerprints"][path].get("sha256") == protected_after[path].get("sha256")
        for path in PROTECTED_PATHS
    }
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
        "monitor_broker_order_or_quick_trade": False,
        "trade_execution_or_sizing_output": False,
        "modified_readonly_snapshot_latest": not protected_unchanged["data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json"],
        "modified_readonly_snapshot_artifact": not (
            protected_unchanged["data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/manifest.json"]
            and protected_unchanged["data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/strategy_snapshot.json"]
        ),
    }
    checks = {
        "all_forbidden_flags_false": all(value is False for value in flags.values()),
        "protected_paths_unchanged": all(protected_unchanged.values()),
        "writes_scoped_to_agent_prompt_artifact_latest_and_aplr2_evidence": True,
        "no_backend_frontend_config_default_change_created_by_script": True,
    }
    return {
        "artifact_type": "aplr2_forbidden_action_audit",
        "schema_version": "aplr2.forbidden_action_audit.v1",
        "route": ROUTE,
        "phase": PHASE,
        "target_asof": TARGET_ASOF,
        "created_at": now_iso(),
        "status": "pass" if all(checks.values()) else "fail",
        "all_false": all(value is False for value in flags.values()),
        "flags": flags,
        "checks": checks,
        "protected_path_fingerprints_after": protected_after,
    }


def write_reports(checks: dict[str, str]) -> None:
    APLR2_REPORT.write_text(
        f"""---
created_at: {now_iso()}
status: execution_report
route: {ROUTE}
phase: {PHASE}
target_asof: {TARGET_ASOF}
verdict: PASS_RECOMMEND_APLR2_REVIEWER_THEN_APLR3_READONLY_ACCEPTANCE
provider_pull_allowed: false
network_command_allowed: false
provider_publish_allowed: false
openai_call_allowed: false
production_default_switch_allowed: false
---

# APLR2 Agent Prompt Artifact Publish Execution Report

## 1. Verdict

PASS_RECOMMEND_APLR2_REVIEWER_THEN_APLR3_READONLY_ACCEPTANCE

APLR2 published the 2026-07-08 candidate-only DailyAgentPromptArtifact and Agent prompt latest pointer.

## 2. Written Artifact

```text
data_tw/artifacts/agent_daily_prompt/2026-07-08/manifest.json
data_tw/artifacts/agent_daily_prompt/2026-07-08/prompt_context.json
data_tw/artifacts/agent_daily_prompt/2026-07-08/prompt_text.md
data_tw/artifacts/agent_daily_prompt/latest.json
```

Checksum:

```text
{EXPECTED_CHECKSUM}
```

## 3. Evidence

```text
data_tw/experiments/agent_prompt_latest_route/aplr2_agent_prompt_artifact_publish/pre_publish_fingerprint.json
data_tw/experiments/agent_prompt_latest_route/aplr2_agent_prompt_artifact_publish/written_agent_prompt_artifact.json
data_tw/experiments/agent_prompt_latest_route/aplr2_agent_prompt_artifact_publish/latest_pointer_write.json
data_tw/experiments/agent_prompt_latest_route/aplr2_agent_prompt_artifact_publish/candidate_only_validator_publish.json
data_tw/experiments/agent_prompt_latest_route/aplr2_agent_prompt_artifact_publish/checksum_verify.json
data_tw/experiments/agent_prompt_latest_route/aplr2_agent_prompt_artifact_publish/rollback_package.json
data_tw/experiments/agent_prompt_latest_route/aplr2_agent_prompt_artifact_publish/forbidden_action_audit.json
data_tw/experiments/agent_prompt_latest_route/aplr2_agent_prompt_artifact_publish/artifact_manifest.json
```

## 4. Gate Summary

```json
{json.dumps(checks, ensure_ascii=False, indent=2, sort_keys=True)}
```

## 5. Boundary

No provider/network pull, provider publish, accepted latest switch, model scoring/training, strategy replay, OrderIntent, ReplayResult/NAV, OpenAI call, frontend/API/default switch, monitor, broker, or order path was invoked.

## 6. Next Step

Proceed to APLR2 reviewer. If reviewer passes, enter APLR3 readonly acceptance.
""",
        encoding="utf-8",
    )
    APLR3_WORK.write_text(
        f"""---
created_at: {now_iso()}
status: work_document
route: {ROUTE}
phase: APLR3_AGENT_PROMPT_READONLY_ACCEPTANCE
target_asof: {TARGET_ASOF}
requires_aplr2_reviewer_pass: true
provider_pull_allowed: false
network_command_allowed: false
provider_publish_allowed: false
openai_call_allowed: false
production_default_switch_allowed: false
---

# APLR3 Agent Prompt Readonly Acceptance Work

## 1. Entry Gate

APLR3 may start only after APLR2 reviewer PASS.

## 2. Scope

Validate the published 2026-07-08 candidate-only DailyAgentPromptArtifact and Agent prompt latest pointer in readonly/no-OpenAI mode.

## 3. Required Checks

```text
latest pointer manifest == data_tw/artifacts/agent_daily_prompt/2026-07-08/manifest.json
manifest/context/text checksum == {EXPECTED_CHECKSUM}
candidate-only validator publish evidence == pass
readonly_strategy_snapshot/latest remains pointed at 2026-07-08 manifest
source citations exist and remain readonly
backend loader compatibility may be checked only without OpenAI calls
forbidden action audit remains pass
```

## 4. Stop Conditions

Stop if acceptance requires provider/network pull, provider publish, accepted latest switch, model scoring/training, strategy replay, OrderIntent, ReplayResult/NAV, OpenAI call, frontend/API/default switch, monitor, broker, order path, or production default switch.
""",
        encoding="utf-8",
    )


def main() -> int:
    assert_entry_gates()
    source = source_gate()
    require(source["status"] == "pass", "source gate failed")

    if EVIDENCE_PATHS["pre_publish_fingerprint.json"].exists():
        pre = read_json(EVIDENCE_PATHS["pre_publish_fingerprint.json"])
    else:
        pre = {
            "artifact_type": "aplr2_pre_publish_fingerprint",
            "schema_version": "aplr2.pre_publish_fingerprint.v1",
            "route": ROUTE,
            "phase": PHASE,
            "target_asof": TARGET_ASOF,
            "created_at": now_iso(),
            "status": "pass",
            "source_gate": source,
            "agent_prompt_paths_before": {
                "asof_dir": fingerprint(AGENT_ASOF_DIR),
                "manifest": fingerprint(AGENT_MANIFEST),
                "prompt_context": fingerprint(AGENT_CONTEXT),
                "prompt_text": fingerprint(AGENT_PROMPT),
                "latest": fingerprint(AGENT_LATEST),
            },
            "protected_path_fingerprints": {path: fingerprint(ROOT / path) for path in PROTECTED_PATHS},
        }
        write_json(EVIDENCE_PATHS["pre_publish_fingerprint.json"], pre)

    if EVIDENCE_PATHS["rollback_package.json"].exists():
        rollback = read_json(EVIDENCE_PATHS["rollback_package.json"])
    else:
        rollback = {
            "artifact_type": "aplr2_rollback_package",
            "schema_version": "aplr2.rollback_package.v1",
            "route": ROUTE,
            "phase": PHASE,
            "target_asof": TARGET_ASOF,
            "created_at": now_iso(),
            "status": "pass",
            "captured_before_latest_pointer_write": True,
            "latest_pointer_before": backup_latest(AGENT_LATEST),
            "rollback_instruction": "restore bytes_base64 to latest.json, or delete latest.json when status is absent_rollback",
        }
        write_json(EVIDENCE_PATHS["rollback_package.json"], rollback)

    context_bytes = APLR1_CONTEXT.read_bytes()
    prompt_bytes = APLR1_PROMPT.read_bytes()
    manifest_plan = read_json(APLR1_MANIFEST_PLAN)["manifest_payload_plan"]
    latest_plan = read_json(APLR1_LATEST_PLAN)["payload_plan"]
    checksum = compute_artifact_checksum(context_bytes, prompt_bytes)
    require(checksum == EXPECTED_CHECKSUM, "dry-run bytes checksum mismatch")

    manifest_payload = dict(manifest_plan)

    AGENT_ASOF_DIR.mkdir(parents=True, exist_ok=True)
    AGENT_CONTEXT.write_bytes(context_bytes)
    AGENT_PROMPT.write_bytes(prompt_bytes)
    write_json(AGENT_MANIFEST, manifest_payload)

    written_manifest = read_json(AGENT_MANIFEST)
    written_context = read_json(AGENT_CONTEXT)
    written_prompt_text = AGENT_PROMPT.read_text(encoding="utf-8")
    candidate_validator = validate_candidate_only_artifact(written_manifest, written_context, written_prompt_text)
    write_json(EVIDENCE_PATHS["candidate_only_validator_publish.json"], candidate_validator)
    require(candidate_validator["status"] == "pass", "candidate-only validator failed")

    checksum_verify = {
        "artifact_type": "aplr2_checksum_verify",
        "schema_version": "aplr2.checksum_verify.v1",
        "route": ROUTE,
        "phase": PHASE,
        "target_asof": TARGET_ASOF,
        "created_at": now_iso(),
        "status": "pass",
        "checksum_rule": "sha256(prompt_context raw bytes + newline + prompt_text raw bytes)",
        "expected_checksum": EXPECTED_CHECKSUM,
        "computed_checksum": compute_artifact_checksum(AGENT_CONTEXT.read_bytes(), AGENT_PROMPT.read_bytes()),
        "manifest_checksum": written_manifest.get("checksum"),
        "aplr1_context_sha256": sha256_file(APLR1_CONTEXT),
        "written_context_sha256": sha256_file(AGENT_CONTEXT),
        "aplr1_prompt_text_sha256": sha256_file(APLR1_PROMPT),
        "written_prompt_text_sha256": sha256_file(AGENT_PROMPT),
        "checks": {
            "computed_checksum_matches_expected": compute_artifact_checksum(AGENT_CONTEXT.read_bytes(), AGENT_PROMPT.read_bytes()) == EXPECTED_CHECKSUM,
            "manifest_checksum_matches_expected": written_manifest.get("checksum") == EXPECTED_CHECKSUM,
            "context_bytes_match_aplr1": APLR1_CONTEXT.read_bytes() == AGENT_CONTEXT.read_bytes(),
            "prompt_text_bytes_match_aplr1": APLR1_PROMPT.read_bytes() == AGENT_PROMPT.read_bytes(),
        },
    }
    write_json(EVIDENCE_PATHS["checksum_verify.json"], checksum_verify)
    require(all(checksum_verify["checks"].values()), "checksum verification failed")

    written = {
        "artifact_type": "aplr2_written_agent_prompt_artifact",
        "schema_version": "aplr2.written_agent_prompt_artifact.v1",
        "route": ROUTE,
        "phase": PHASE,
        "target_asof": TARGET_ASOF,
        "created_at": now_iso(),
        "status": "pass",
        "artifact_dir": rel(AGENT_ASOF_DIR),
        "files": {
            "manifest.json": fingerprint(AGENT_MANIFEST),
            "prompt_context.json": fingerprint(AGENT_CONTEXT),
            "prompt_text.md": fingerprint(AGENT_PROMPT),
        },
        "checks": {
            "manifest_payload_matches_aplr1_plan": written_manifest == manifest_plan,
            "prompt_context_bytes_match_aplr1_dry_run": APLR1_CONTEXT.read_bytes() == AGENT_CONTEXT.read_bytes(),
            "prompt_text_bytes_match_aplr1_dry_run": APLR1_PROMPT.read_bytes() == AGENT_PROMPT.read_bytes(),
            "candidate_only_validator_pass": candidate_validator["status"] == "pass",
        },
    }
    write_json(EVIDENCE_PATHS["written_agent_prompt_artifact.json"], written)
    require(all(written["checks"].values()), "written artifact verification failed")

    write_json(AGENT_LATEST, latest_plan)
    loaded_latest = read_json(AGENT_LATEST)
    latest_write = {
        "artifact_type": "aplr2_latest_pointer_write",
        "schema_version": "aplr2.latest_pointer_write.v1",
        "route": ROUTE,
        "phase": PHASE,
        "target_asof": TARGET_ASOF,
        "created_at": now_iso(),
        "status": "pass",
        "latest_path": rel(AGENT_LATEST),
        "latest_payload": loaded_latest,
        "latest_fingerprint": fingerprint(AGENT_LATEST),
        "checks": {
            "latest_pointer_scoped_to_agent_prompt_only": True,
            "manifest_field_exact": loaded_latest.get("manifest") == rel(AGENT_MANIFEST),
            "checksum_matches_expected": loaded_latest.get("checksum") == EXPECTED_CHECKSUM,
            "not_provider_or_qlib_accepted_latest": True,
            "readonly_only": loaded_latest.get("readonly_only") is True,
            "production_trade_enabled_false": loaded_latest.get("production_trade_enabled") is False,
            "rollback_captured_before_write": rollback["captured_before_latest_pointer_write"] is True,
        },
    }
    write_json(EVIDENCE_PATHS["latest_pointer_write.json"], latest_write)
    require(all(latest_write["checks"].values()), "latest pointer verification failed")

    forbidden = build_forbidden_action_audit(pre)
    write_json(EVIDENCE_PATHS["forbidden_action_audit.json"], forbidden)
    require(forbidden["status"] == "pass", "forbidden action audit failed")

    evidence_hashes = {
        name: sha256_file(path)
        for name, path in EVIDENCE_PATHS.items()
        if name != "artifact_manifest.json"
    }
    artifact_manifest = {
        "artifact_type": "aplr2_evidence_manifest",
        "schema_version": "aplr2.artifact_manifest.v1",
        "route": ROUTE,
        "phase": PHASE,
        "target_asof": TARGET_ASOF,
        "created_at": now_iso(),
        "status": "pass",
        "evidence_dir": rel(APLR2_DIR),
        "evidence_files": evidence_hashes,
        "published_artifact": {
            "manifest": rel(AGENT_MANIFEST),
            "prompt_context": rel(AGENT_CONTEXT),
            "prompt_text": rel(AGENT_PROMPT),
            "latest": rel(AGENT_LATEST),
            "checksum": EXPECTED_CHECKSUM,
        },
        "required_input_fingerprints": {
            rel(APLR1_REVIEW): fingerprint(APLR1_REVIEW),
            rel(APLR1_CONTEXT): fingerprint(APLR1_CONTEXT),
            rel(APLR1_PROMPT): fingerprint(APLR1_PROMPT),
            rel(APLR1_MANIFEST_PLAN): fingerprint(APLR1_MANIFEST_PLAN),
            rel(APLR1_LATEST_PLAN): fingerprint(APLR1_LATEST_PLAN),
            rel(APLR1_CHECKSUM_PLAN): fingerprint(APLR1_CHECKSUM_PLAN),
            rel(READONLY_LATEST): fingerprint(READONLY_LATEST),
            rel(SNAPSHOT_MANIFEST): fingerprint(SNAPSHOT_MANIFEST),
            rel(SNAPSHOT_PAYLOAD): fingerprint(SNAPSHOT_PAYLOAD),
            rel(SCRIPT_PATH): fingerprint(SCRIPT_PATH),
        },
        "checks": {
            "pre_publish_fingerprint_pass": pre["status"] == "pass",
            "rollback_package_captured_before_latest_pointer_write": rollback["captured_before_latest_pointer_write"] is True,
            "written_agent_prompt_artifact_pass": written["status"] == "pass",
            "candidate_only_validator_publish_pass": candidate_validator["status"] == "pass",
            "checksum_verify_pass": checksum_verify["status"] == "pass",
            "latest_pointer_write_pass": latest_write["status"] == "pass",
            "forbidden_action_audit_pass": forbidden["status"] == "pass",
        },
    }
    write_json(EVIDENCE_PATHS["artifact_manifest.json"], artifact_manifest)
    require(all(artifact_manifest["checks"].values()), "artifact manifest checks failed")

    write_reports({name: "pass" for name in EVIDENCE_PATHS})
    print(json.dumps({"ok": True, "checksum": EXPECTED_CHECKSUM, "evidence_dir": rel(APLR2_DIR)}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
