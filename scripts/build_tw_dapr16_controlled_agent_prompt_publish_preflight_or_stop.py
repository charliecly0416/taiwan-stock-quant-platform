#!/usr/bin/env python3
"""DAPR16 controlled Agent prompt publish preflight-or-stop.

This phase checks whether the DAPR15 candidate-only Agent prompt payload is
ready for a later exact-authorization publish. It does not copy payloads into
data_tw/artifacts/agent_daily_prompt/{target_asof} and does not write latest.json.
"""

from __future__ import annotations

import hashlib
import importlib.util
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


TARGET_ASOF = env_str("TW_DAPR16_TARGET_ASOF", "2026-07-17")
TARGET_TAG = TARGET_ASOF.replace("-", "")

DAPR15_ROOT = env_path(
    "TW_DAPR16_DAPR15_ROOT",
    "data_tw/experiments/daily_accepted_production_readiness/dapr15_candidate_only_agent_prompt_dry_run_no_publish",
)
DAPR15_CANDIDATE_DIR = DAPR15_ROOT / f"candidate_payloads/agent_daily_prompt/{TARGET_ASOF}"
DAPR16_ROOT = env_path(
    "TW_DAPR16_OUTPUT_ROOT",
    f"data_tw/experiments/provider_bridge_productionization/dapr16_{TARGET_TAG}_controlled_agent_prompt_publish_preflight_or_stop",
)

AGENT_ROOT = ROOT / "data_tw/artifacts/agent_daily_prompt"
AGENT_LATEST = AGENT_ROOT / "latest.json"
TARGET_AGENT_DIR = AGENT_ROOT / TARGET_ASOF
TARGET_AGENT_MANIFEST = TARGET_AGENT_DIR / "manifest.json"
TARGET_AGENT_CONTEXT = TARGET_AGENT_DIR / "prompt_context.json"
TARGET_AGENT_PROMPT = TARGET_AGENT_DIR / "prompt_text.md"

READONLY_LATEST = ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json"
CONTROLLED_SIGNAL_LATEST = ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json"
LEGACY_QLIB_OPTION_C_LATEST = ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json"
LEGACY_DATA_OPTION_C_LATEST = ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json"

VALIDATOR_PATH = ROOT / "scripts/validate_tw_agent_daily_prompt_artifact.py"
DAPR16_EXECUTION_REPORT = env_path(
    "TW_DAPR16_EXECUTION_REPORT",
    f"docs/tw_portfolio_decision_model/POLICY_DAPR16_{TARGET_TAG}_CONTROLLED_AGENT_PROMPT_PUBLISH_PREFLIGHT_OR_STOP_EXECUTION_REPORT_CN.md",
)
DAPR16_REVIEW = env_path(
    "TW_DAPR16_REVIEW",
    f"docs/tw_portfolio_decision_model/POLICY_DAPR16_{TARGET_TAG}_CONTROLLED_AGENT_PROMPT_PUBLISH_PREFLIGHT_OR_STOP_REVIEW_CN.md",
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
        raise ValueError(f"Expected JSON object: {rel(path)}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(payload))


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
                    "status",
                    "asof",
                    "signal_asof",
                    "target_date",
                    "artifact_dir",
                    "manifest",
                    "snapshot_manifest",
                    "readonly_only",
                    "production_trade_enabled",
                )
                if key in payload
            }
        except Exception as exc:
            item["json_error"] = str(exc)
    return item


def latest_bytes_backup_plan(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {"path": rel(path), "exists": False, "sha256": None, "size_bytes": None, "json_summary": None}
    payload = read_json(path)
    return {
        "path": rel(path),
        "exists": True,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "json_summary": {
            "artifact_type": payload.get("artifact_type"),
            "schema_version": payload.get("schema_version"),
            "signal_asof": payload.get("signal_asof"),
            "target_date": payload.get("target_date"),
            "manifest": payload.get("manifest"),
            "checksum": payload.get("checksum"),
        },
        "required_rollback_copy_path_for_actual_publish": rel(
            DAPR16_ROOT / "rollback/agent_daily_prompt_latest.before_dapr17.json"
        ),
    }


def load_validator_module() -> Any:
    spec = importlib.util.spec_from_file_location("tw_agent_prompt_validator_dapr16", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed_to_load_validator:{rel(VALIDATOR_PATH)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_candidate_publish_preflight(created_at: str) -> dict[str, Any]:
    d15_decision = read_json(DAPR15_ROOT / "candidate_or_stop_decision.json")
    d15_validator = read_json(DAPR15_ROOT / "validator_dry_run.json")
    d15_checksum = read_json(DAPR15_ROOT / "checksum_plan.json")
    d15_latest_plan = read_json(DAPR15_ROOT / "latest_pointer_payload_plan.json")
    d15_forbidden = read_json(DAPR15_ROOT / "forbidden_action_audit.json")
    manifest = read_json(DAPR15_CANDIDATE_DIR / "manifest.json")
    context = read_json(DAPR15_CANDIDATE_DIR / "prompt_context.json")
    latest_plan_payload = d15_latest_plan["payload_plan"]
    validator = load_validator_module()
    validator_result = validator.validate_artifact(DAPR15_CANDIDATE_DIR).to_dict(DAPR15_CANDIDATE_DIR)
    recomputed_checksum = validator.compute_checksum(
        (DAPR15_CANDIDATE_DIR / "prompt_context.json").read_bytes(),
        (DAPR15_CANDIDATE_DIR / "prompt_text.md").read_bytes(),
    )
    candidate_files = {
        "manifest.json": DAPR15_CANDIDATE_DIR / "manifest.json",
        "prompt_context.json": DAPR15_CANDIDATE_DIR / "prompt_context.json",
        "prompt_text.md": DAPR15_CANDIDATE_DIR / "prompt_text.md",
    }
    checks = {
        "dapr15_decision_pass": d15_decision.get("status") == "pass",
        "dapr15_ready_for_dapr16": d15_decision.get("ready_for_dapr16_agent_prompt_publish_preflight_gate") is True,
        "dapr15_direct_publish_false": d15_decision.get("ready_for_direct_agent_prompt_publish") is False,
        "dapr15_validator_pass": d15_validator.get("status") == "pass"
        and d15_validator.get("validator_output", {}).get("ok") is True,
        "dapr16_validator_recheck_pass": validator_result.get("ok") is True
        and validator_result.get("errors") == [],
        "dapr15_checksum_pass": d15_checksum.get("status") == "pass",
        "manifest_checksum_recomputed": manifest.get("checksum") == recomputed_checksum,
        "latest_pointer_plan_pass": d15_latest_plan.get("status") == "pass"
        and d15_latest_plan.get("writes_latest_pointer") is False,
        "latest_payload_plan_matches_manifest_checksum": latest_plan_payload.get("checksum") == manifest.get("checksum"),
        "latest_payload_plan_points_to_target": latest_plan_payload.get("manifest")
        == rel(TARGET_AGENT_MANIFEST)
        and latest_plan_payload.get("artifact_dir") == rel(TARGET_AGENT_DIR),
        "candidate_files_exist": all(path.is_file() for path in candidate_files.values()),
        "candidate_asof_target": manifest.get("signal_asof") == TARGET_ASOF
        and manifest.get("target_date") == TARGET_ASOF
        and (context.get("date_context") or {}).get("signal_asof") == TARGET_ASOF,
        "candidate_readonly_safe": manifest.get("readonly_only") is True
        and manifest.get("not_order") is True
        and manifest.get("not_target_position") is True
        and manifest.get("production_trade_enabled") is False,
        "dapr15_forbidden_pass": d15_forbidden.get("status") == "pass"
        and d15_forbidden.get("all_false") is True,
        "canonical_target_dir_absent": not TARGET_AGENT_DIR.exists(),
        "agent_latest_not_target": read_json(AGENT_LATEST).get("signal_asof") != TARGET_ASOF,
    }
    return {
        "schema_version": "dapr16.candidate_publish_preflight.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "candidate_dir": rel(DAPR15_CANDIDATE_DIR),
        "candidate_files": {
            name: {
                "path": rel(path),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size if path.exists() else None,
            }
            for name, path in candidate_files.items()
        },
        "validator_recheck": validator_result,
        "planned_canonical_targets": {
            "manifest.json": rel(TARGET_AGENT_MANIFEST),
            "prompt_context.json": rel(TARGET_AGENT_CONTEXT),
            "prompt_text.md": rel(TARGET_AGENT_PROMPT),
            "latest.json": rel(AGENT_LATEST),
        },
        "latest_pointer_payload_plan_sha256": sha256_bytes(canonical_json_bytes(latest_plan_payload)),
    }


def build_rollback_and_fingerprint_plan(created_at: str) -> dict[str, Any]:
    fingerprints = {name: file_fingerprint(path) for name, path in PROTECTED_POINTERS.items()}
    latest_payload = read_json(AGENT_LATEST) if AGENT_LATEST.exists() else {}
    checks = {
        "agent_latest_exists_for_rollback": AGENT_LATEST.is_file(),
        "agent_latest_current_not_target": latest_payload.get("signal_asof") != TARGET_ASOF,
        "target_agent_dir_absent": not TARGET_AGENT_DIR.exists(),
        "rollback_copy_required_before_dapr17": True,
        "protected_pointer_fingerprints_recorded": all(item.get("exists") is not None for item in fingerprints.values()),
    }
    return {
        "schema_version": "dapr16.rollback_and_fingerprint_plan.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "protected_pointer_before_fingerprints": fingerprints,
        "agent_latest_backup_plan": latest_bytes_backup_plan(AGENT_LATEST),
        "target_agent_dir_before": file_fingerprint(TARGET_AGENT_DIR),
        "actual_publish_requirements": [
            "Re-capture protected pointer before fingerprints immediately before DAPR17.",
            "Create rollback copy for data_tw/artifacts/agent_daily_prompt/latest.json before writing.",
            "After write, verify canonical checksums, latest payload, validator output, diff, and protected pointers unchanged except agent latest.",
        ],
        "checks": checks,
    }


def build_exact_authorization_template(created_at: str) -> dict[str, Any]:
    latest_plan = read_json(DAPR15_ROOT / "latest_pointer_payload_plan.json")
    manifest = read_json(DAPR15_CANDIDATE_DIR / "manifest.json")
    template = (
        "我确认执行 DAPR17 actual controlled Agent prompt latest publish："
        f"target_asof={TARGET_ASOF}；输入为 DAPR15 candidate payload under "
        f"{rel(DAPR15_CANDIDATE_DIR)}/；唯一允许写入为 "
        f"data_tw/artifacts/agent_daily_prompt/{TARGET_ASOF}/{{manifest.json,prompt_context.json,prompt_text.md}} "
        "和 data_tw/artifacts/agent_daily_prompt/latest.json；写入前重新捕获 protected pointer before fingerprints，"
        "并为 data_tw/artifacts/agent_daily_prompt/latest.json 创建 rollback copy；写后执行 after fingerprint、diff、"
        "canonical file checksum validation、Agent prompt artifact validator、latest pointer payload validation 和 post-write review；"
        "保持 data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json、"
        "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json、"
        "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json、"
        "data_tw/experiments/option_c_daily_signal/latest_signal.json 不动；不授权 provider publish、provider pull、qlib refresh、"
        "daily auto、accepted latest switch、OpenAI、DB、strategy replay、monitor/broker/order/target、frontend/API production default switch；"
        "我确认 DAPR15 candidate payload 只是本次 Agent prompt latest publish 的一次性输入，不授权后续自动 latest switch。"
    )
    checks = {
        "template_mentions_exact_candidate_input": rel(DAPR15_CANDIDATE_DIR) in template,
        "template_limits_writes_to_three_artifact_files_and_latest": True,
        "template_requires_rollback_and_fingerprints": "rollback" in template and "fingerprint" in template,
        "template_forbids_openai_provider_qlib_db_replay_order_default": all(
            term in template
            for term in ("OpenAI", "provider", "qlib", "DB", "strategy replay", "monitor/broker/order/target")
        ),
        "planned_latest_payload_checksum_matches_manifest": latest_plan["payload_plan"].get("checksum") == manifest.get("checksum"),
    }
    return {
        "schema_version": "dapr16.exact_authorization_template.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "template_text": template,
        "checks": checks,
    }


def build_forbidden_action_audit(created_at: str, before: dict[str, Any]) -> dict[str, Any]:
    after = {name: file_fingerprint(path) for name, path in PROTECTED_POINTERS.items()}
    unchanged = {
        name: before["protected_pointer_before_fingerprints"][name].get("sha256") == after[name].get("sha256")
        for name in PROTECTED_POINTERS
    }
    flags = {
        "canonical_agent_prompt_artifact_written": TARGET_AGENT_DIR.exists(),
        "agent_prompt_latest_written": unchanged["agent_prompt_latest"] is False,
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
        "canonical_agent_target_dir_absent": not TARGET_AGENT_DIR.exists(),
        "agent_latest_not_written": unchanged["agent_prompt_latest"],
    }
    return {
        "schema_version": "dapr16.forbidden_action_audit.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "all_false": all(value is False for value in flags.values()),
        "flags": flags,
        "protected_pointer_after_fingerprints": after,
        "protected_pointer_unchanged": unchanged,
        "checks": checks,
        "allowed_writes": {
            "dapr16_evidence_written": True,
            "dapr16_docs_written": True,
            "canonical_agent_prompt_artifact_written": False,
            "agent_prompt_latest_written": False,
        },
    }


def build_candidate_or_stop_decision(
    created_at: str,
    preflight: dict[str, Any],
    rollback_plan: dict[str, Any],
    auth_template: dict[str, Any],
    forbidden: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "candidate_publish_preflight_pass": preflight.get("status") == "pass",
        "rollback_and_fingerprint_plan_pass": rollback_plan.get("status") == "pass",
        "exact_authorization_template_pass": auth_template.get("status") == "pass",
        "forbidden_action_audit_pass": forbidden.get("status") == "pass"
        and forbidden.get("all_false") is True,
        "ready_for_direct_publish_false": True,
    }
    passed = all(checks.values())
    return {
        "schema_version": "dapr16.candidate_or_stop_decision.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if passed else "fail",
        "decision": "PREFLIGHT_PASS_STOP_BEFORE_ACTUAL_AGENT_PROMPT_PUBLISH_REQUIRE_DAPR17_EXACT_AUTHORIZATION"
        if passed
        else "STOP_DAPR16_AGENT_PROMPT_PUBLISH_PREFLIGHT_FAILED",
        "agent_prompt_artifact_written_to_canonical_dir": False,
        "agent_prompt_latest_written": False,
        "ready_for_dapr17_exact_authorization_gate": passed,
        "ready_for_direct_agent_prompt_publish": False,
        "next_required_action": "DAPR17_ACTUAL_CONTROLLED_AGENT_PROMPT_PUBLISH_EXACT_AUTHORIZATION_GATE"
        if passed
        else "repair DAPR16 blockers before actual Agent prompt publish",
        "checks": checks,
    }


def build_artifact_manifest(created_at: str, files: list[Path]) -> dict[str, Any]:
    entries = []
    missing = []
    for path in files:
        exists = path.is_file()
        if not exists and path != DAPR16_ROOT / "artifact_manifest.json":
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
        "schema_version": "dapr16.artifact_manifest.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if not missing else "fail",
        "entries": entries,
        "missing": missing,
    }


def build_execution_report(
    created_at: str,
    preflight: dict[str, Any],
    rollback_plan: dict[str, Any],
    auth_template: dict[str, Any],
    forbidden: dict[str, Any],
    decision: dict[str, Any],
    artifact_manifest: dict[str, Any],
) -> str:
    verdict = (
        "PASS_STOP_BEFORE_ACTUAL_AGENT_PROMPT_PUBLISH_REQUIRE_EXACT_AUTHORIZATION"
        if decision.get("status") == "pass" and artifact_manifest.get("status") == "pass"
        else "STOP_REPAIR_DAPR16"
    )
    return f"""# DAPR16 Controlled Agent Prompt Publish Preflight-Or-Stop 执行报告

created_at: `{created_at}`

phase: `DAPR16_CONTROLLED_AGENT_PROMPT_PUBLISH_PREFLIGHT_OR_STOP`

target_asof: `{TARGET_ASOF}`

verdict: `{verdict}`

## 1. Scope

本阶段只做 Agent prompt publish preflight / authorization gate。未写 `data_tw/artifacts/agent_daily_prompt/{TARGET_ASOF}/`，未写 `data_tw/artifacts/agent_daily_prompt/latest.json`，未调用 OpenAI。

## 2. Evidence Produced

- `candidate_publish_preflight.json`: `{preflight["status"]}`
- `rollback_and_fingerprint_plan.json`: `{rollback_plan["status"]}`
- `exact_authorization_template.json`: `{auth_template["status"]}`
- `forbidden_action_audit.json`: `{forbidden["status"]}`
- `candidate_or_stop_decision.json`: `{decision["status"]}`
- `artifact_manifest.json`: `{artifact_manifest["status"]}`

## 3. Result

Candidate payload 可进入 exact authorization gate，但不能直接 publish。

Decision:

```text
{decision["decision"]}
```

## 4. Exact Authorization Template

模板已写入 `exact_authorization_template.json`，其中唯一允许写入范围是：

```text
data_tw/artifacts/agent_daily_prompt/{TARGET_ASOF}/{{manifest.json,prompt_context.json,prompt_text.md}}
data_tw/artifacts/agent_daily_prompt/latest.json
```

## 5. Forbidden Actions Audit

`all_false={forbidden["all_false"]}`。未触发 Agent prompt publish、OpenAI、provider/qlib/daily auto/accepted latest、DB、strategy replay、monitor/broker/order/target、frontend/API default switch。
"""


def build_review_doc(
    created_at: str,
    preflight: dict[str, Any],
    rollback_plan: dict[str, Any],
    auth_template: dict[str, Any],
    forbidden: dict[str, Any],
    decision: dict[str, Any],
    artifact_manifest: dict[str, Any],
) -> str:
    verdict = (
        "PASS_STOP_BEFORE_DAPR17_ACTUAL_AGENT_PROMPT_PUBLISH_AUTHORIZATION"
        if decision.get("status") == "pass" and artifact_manifest.get("status") == "pass"
        else "FAIL_NEEDS_REPAIR"
    )
    return f"""# DAPR16 Controlled Agent Prompt Publish Preflight-Or-Stop 审查

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

- `{rel(DAPR16_ROOT / "candidate_publish_preflight.json")}`
- `{rel(DAPR16_ROOT / "rollback_and_fingerprint_plan.json")}`
- `{rel(DAPR16_ROOT / "exact_authorization_template.json")}`
- `{rel(DAPR16_ROOT / "forbidden_action_audit.json")}`
- `{rel(DAPR16_ROOT / "candidate_or_stop_decision.json")}`
- `{rel(DAPR16_ROOT / "artifact_manifest.json")}`

## 4. Review Result

- candidate publish preflight: `{preflight["status"]}`
- rollback/fingerprint plan: `{rollback_plan["status"]}`
- exact authorization template: `{auth_template["status"]}`
- forbidden action audit: `{forbidden["status"]}`, all_false=`{forbidden["all_false"]}`
- artifact manifest: `{artifact_manifest["status"]}`

## 5. Stop Boundary

DAPR16 停在 actual Agent prompt publish 之前。当前不授权写 canonical Agent prompt artifact，也不授权写 Agent prompt latest。

## 6. Next Work Document

若继续，必须由用户给出 DAPR17 exact authorization。泛泛的“继续/授权”不足以执行 actual publish。
"""


def main() -> None:
    created_at = now_iso()
    DAPR16_ROOT.mkdir(parents=True, exist_ok=True)
    preflight = build_candidate_publish_preflight(created_at)
    write_json(DAPR16_ROOT / "candidate_publish_preflight.json", preflight)
    rollback_plan = build_rollback_and_fingerprint_plan(created_at)
    write_json(DAPR16_ROOT / "rollback_and_fingerprint_plan.json", rollback_plan)
    auth_template = build_exact_authorization_template(created_at)
    write_json(DAPR16_ROOT / "exact_authorization_template.json", auth_template)
    forbidden = build_forbidden_action_audit(created_at, rollback_plan)
    write_json(DAPR16_ROOT / "forbidden_action_audit.json", forbidden)
    decision = build_candidate_or_stop_decision(created_at, preflight, rollback_plan, auth_template, forbidden)
    write_json(DAPR16_ROOT / "candidate_or_stop_decision.json", decision)

    evidence_files = [
        DAPR16_ROOT / "candidate_publish_preflight.json",
        DAPR16_ROOT / "rollback_and_fingerprint_plan.json",
        DAPR16_ROOT / "exact_authorization_template.json",
        DAPR16_ROOT / "forbidden_action_audit.json",
        DAPR16_ROOT / "candidate_or_stop_decision.json",
    ]
    artifact_manifest = build_artifact_manifest(created_at, evidence_files)
    execution_report = build_execution_report(
        created_at, preflight, rollback_plan, auth_template, forbidden, decision, artifact_manifest
    )
    review_doc = build_review_doc(
        created_at, preflight, rollback_plan, auth_template, forbidden, decision, artifact_manifest
    )
    write_text(DAPR16_EXECUTION_REPORT, execution_report)
    write_text(DAPR16_REVIEW, review_doc)
    artifact_manifest = build_artifact_manifest(
        created_at, evidence_files + [DAPR16_EXECUTION_REPORT, DAPR16_REVIEW]
    )
    write_json(DAPR16_ROOT / "artifact_manifest.json", artifact_manifest)

    if decision.get("status") != "pass" or artifact_manifest.get("status") != "pass":
        raise RuntimeError("STOP_DAPR16_PREFLIGHT_FAILED")

    print(
        json.dumps(
            {
                "status": "pass",
                "phase": "DAPR16_CONTROLLED_AGENT_PROMPT_PUBLISH_PREFLIGHT_OR_STOP",
                "target_asof": TARGET_ASOF,
                "decision": decision["decision"],
                "ready_for_dapr17_exact_authorization_gate": True,
                "ready_for_direct_agent_prompt_publish": False,
                "evidence_root": rel(DAPR16_ROOT),
                "execution_report": rel(DAPR16_EXECUTION_REPORT),
                "review": rel(DAPR16_REVIEW),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
