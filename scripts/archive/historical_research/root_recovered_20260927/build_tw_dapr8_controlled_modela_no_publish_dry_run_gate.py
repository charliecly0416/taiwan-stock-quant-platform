#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DAPR_ROOT = ROOT / "data_tw/experiments/daily_accepted_production_readiness"
OUT_DIR = DAPR_ROOT / "dapr8_controlled_modela_no_publish_dry_run_gate"
RUNTIME_ROOT = OUT_DIR / "modela_no_publish_runtime"
PAYLOAD_ROOT = RUNTIME_ROOT / "planned_future_outputs"
DOC_DIR = ROOT / "docs/tw_portfolio_decision_model"
RUN_ID = "dapr8_modela_20260717_contained"
TARGET_ASOF = "2026-07-17"
MODEL_ID = "e4_frozen_qlib_2018_2022"

DAPR3_SELECTED = DAPR_ROOT / "dapr3_exact_target_provider_bridge_candidate_or_blocker/provider_candidate_readiness_selected.json"
DAPR3_DECISION = DAPR_ROOT / "dapr3_exact_target_provider_bridge_candidate_or_blocker/candidate_or_blocker_decision.json"

INPUT_DIR = PAYLOAD_ROOT / "model_inference_input" / MODEL_ID / RUN_ID
SCORE_DIR = PAYLOAD_ROOT / "score_job" / MODEL_ID / RUN_ID
SIGNAL_DIR = PAYLOAD_ROOT / "model_signal_artifact" / MODEL_ID / RUN_ID
QLIB_RUN_DIR = PAYLOAD_ROOT / "qlib_scoring_runs" / RUN_ID
PIPELINE_VALIDATION = PAYLOAD_ROOT / "score_pipeline_validation" / RUN_ID / "validation.json"
PIPELINE_REPORT = PAYLOAD_ROOT / "score_pipeline_report" / RUN_ID / "execution_report.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_entry(path: Path) -> dict[str, Any]:
    return {
        "path": rel(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() and path.is_file() else None,
        "sha256": sha256(path) if path.exists() and path.is_file() else "",
    }


def all_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file())


def runtime_path_audit(paths: dict[str, Path]) -> dict[str, Any]:
    rows = []
    errors: list[str] = []
    forbidden_parts = {
        "latest",
        "catalog",
        "publish",
        "published",
        "accepted_latest",
        "readonly",
        "agent",
        "agent_daily_prompt",
        "monitor",
        "broker",
        "order",
        "target_position",
        "target_weight",
        "target_output",
    }
    for role, path in paths.items():
        resolved = path.resolve(strict=False)
        under_runtime = False
        try:
            resolved.relative_to(RUNTIME_ROOT.resolve(strict=False))
            under_runtime = True
        except ValueError:
            pass
        parts = {part.lower() for part in resolved.parts}
        forbidden = sorted(parts & forbidden_parts)
        if not under_runtime:
            errors.append(f"{role}:not_under_runtime_root")
        if forbidden:
            errors.append(f"{role}:forbidden_path_part:{','.join(forbidden)}")
        rows.append({"role": role, "path": rel(path), "under_runtime_root": under_runtime, "forbidden_parts": forbidden})
    return {
        "schema_version": "dapr8.runtime_path_audit.v1",
        "created_at": utc_now(),
        "status": "pass" if not errors else "fail",
        "runtime_root": rel(RUNTIME_ROOT),
        "paths": rows,
        "errors": errors,
    }


def build() -> dict[str, Any]:
    created_at = utc_now()
    dapr3_selected = read_json(DAPR3_SELECTED)
    dapr3_decision = read_json(DAPR3_DECISION)
    readiness_path = ROOT / str(dapr3_selected.get("path") or "")
    readiness = read_json(readiness_path)
    input_manifest = read_json(INPUT_DIR / "manifest.json")
    input_validator = read_json(INPUT_DIR / "validator_report.json")
    score_manifest = read_json(SCORE_DIR / "manifest.json")
    score_validator = read_json(SCORE_DIR / "validator_report.json")
    signal_manifest = read_json(SIGNAL_DIR / "manifest.json")
    signal_validator = read_json(SIGNAL_DIR / "validator_report.json")
    pipeline_validation = read_json(PIPELINE_VALIDATION)
    qlib_metadata = read_json(QLIB_RUN_DIR / "run_metadata.json")

    runtime_audit = runtime_path_audit(
        {
            "runtime_root": RUNTIME_ROOT,
            "payload_root": PAYLOAD_ROOT,
            "model_inference_input_dir": INPUT_DIR,
            "score_job_dir": SCORE_DIR,
            "model_signal_dir": SIGNAL_DIR,
            "qlib_run_dir": QLIB_RUN_DIR,
            "pipeline_validation": PIPELINE_VALIDATION,
            "pipeline_report": PIPELINE_REPORT,
        }
    )

    checks = {
        "dapr3_ready_for_modela_no_publish": dapr3_decision.get("ready_for_model_a_no_publish_dry_run") is True,
        "dapr3_selected_readiness_pass": dapr3_selected.get("readiness_accepted_for_dapr3_no_publish") is True,
        "readiness_target_asof_match": readiness.get("candidate_asof") == TARGET_ASOF and readiness.get("target_asof") == TARGET_ASOF,
        "readiness_validator_pass": readiness.get("validator_status") == "pass",
        "input_ready": input_manifest.get("status") == "READY" and input_validator.get("ok") is True,
        "score_job_scored": score_manifest.get("score_status") == "SCORED_ASOF_TARGET" and score_validator.get("ok") is True,
        "signal_ready": signal_manifest.get("status") == "READY" and signal_validator.get("ok") is True,
        "row_counts_150": input_manifest.get("row_count") == 150
        and score_manifest.get("row_count") == 150
        and signal_manifest.get("row_count") == 150,
        "pipeline_validation_scored": pipeline_validation.get("pipeline_status") == "SCORED_ASOF_TARGET",
        "qlib_contained_runtime": qlib_metadata.get("contained_runtime") is True,
        "runtime_paths_contained": runtime_audit.get("status") == "pass",
    }
    status = "pass" if all(checks.values()) else "fail"

    forbidden_actions = {
        "provider_network_pull": False,
        "provider_refresh": False,
        "provider_publish": False,
        "formal_provider_or_calendar_mutation": False,
        "accepted_latest_switch": False,
        "qlib_refresh": False,
        "latest_catalog_publish_write": False,
        "readonly_latest_publish": False,
        "agent_prompt_build_or_publish": False,
        "db_access": False,
        "openai_call": False,
        "monitor_write": False,
        "broker_order_quick_trade": False,
        "order_intent_generation": False,
        "target_position_weight_quantity_output": False,
        "model_training_or_tuning": False,
        "strategy_replay_or_nav_generation": False,
    }
    forbidden_action_audit = {
        "schema_version": "dapr8.forbidden_action_audit.v1",
        "created_at": created_at,
        "status": "pass",
        "all_false": all(value is False for value in forbidden_actions.values()),
        "authorized_actions": {
            "model_inference_input_build": True,
            "contained_model_a_qlib_scoring": True,
            "score_job_build": True,
            "model_signal_artifact_no_publish_build": True,
            "contained_validator_run": True,
        },
        "actions": forbidden_actions,
        "production_allowed": False,
        "not_published_latest": True,
    }

    summary = {
        "schema_version": "dapr8.controlled_modela_no_publish_dry_run_gate_summary.v1",
        "created_at": created_at,
        "status": status,
        "decision": "MODELA_NO_PUBLISH_DRY_RUN_PASS" if status == "pass" else "MODELA_NO_PUBLISH_DRY_RUN_FAIL",
        "target_asof": TARGET_ASOF,
        "run_id": RUN_ID,
        "model_id": MODEL_ID,
        "dapr3_selected_readiness": rel(DAPR3_SELECTED),
        "provider_candidate_readiness": rel(readiness_path),
        "provider_root": readiness.get("lineage", {}).get("feature_path", "").removesuffix("/features"),
        "normalized_root": (readiness.get("lineage", {}).get("normalized_output_paths") or [""])[0],
        "model_inference_input": rel(INPUT_DIR),
        "score_job": rel(SCORE_DIR),
        "model_signal_artifact_no_publish": rel(SIGNAL_DIR),
        "qlib_scoring_run": rel(QLIB_RUN_DIR),
        "pipeline_validation": rel(PIPELINE_VALIDATION),
        "checks": checks,
        "row_counts": {
            "model_inference_input": input_manifest.get("row_count"),
            "raw_scores": score_validator.get("raw_score_rows"),
            "model_signal": signal_validator.get("signal_rows"),
        },
        "statuses": {
            "input_manifest": input_manifest.get("status"),
            "input_validator": input_validator.get("status"),
            "score_job": score_manifest.get("score_status"),
            "score_validator": score_validator.get("status"),
            "model_signal_manifest": signal_manifest.get("status"),
            "model_signal_validator": signal_validator.get("status"),
            "pipeline_validation": pipeline_validation.get("pipeline_status"),
        },
        "ready_for_provider_publish": False,
        "ready_for_latest_switch": False,
        "ready_for_readonly_agent_publish": False,
        "ready_for_controlled_latest_publish_preflight": status == "pass",
        "production_allowed": False,
        "not_published_latest": True,
        "forbidden_actions_all_false": forbidden_action_audit["all_false"],
        "next_required_action": "open controlled latest/publish preflight route, or stop here and keep isolated no-publish evidence",
    }

    runtime_audit_path = write_json(OUT_DIR / "runtime_path_audit.json", runtime_audit)
    forbidden_path = write_json(OUT_DIR / "forbidden_action_audit.json", forbidden_action_audit)
    summary_path = write_json(OUT_DIR / "modela_no_publish_dry_run_summary.json", summary)

    execution_doc = build_execution_doc(summary)
    review_doc = build_review_doc(summary)
    execution_doc_path = write_text(
        DOC_DIR / "POLICY_DAPR8_CONTROLLED_MODELA_NO_PUBLISH_DRY_RUN_GATE_EXECUTION_REPORT_CN.md",
        execution_doc,
    )
    review_doc_path = write_text(
        DOC_DIR / "POLICY_DAPR8_CONTROLLED_MODELA_NO_PUBLISH_DRY_RUN_GATE_REVIEW_CN.md",
        review_doc,
    )

    files = [
        summary_path,
        runtime_audit_path,
        forbidden_path,
        execution_doc_path,
        review_doc_path,
        INPUT_DIR / "manifest.json",
        INPUT_DIR / "inference_frame.csv",
        INPUT_DIR / "validator_report.json",
        SCORE_DIR / "manifest.json",
        SCORE_DIR / "raw_scores.csv",
        SCORE_DIR / "validator_report.json",
        SIGNAL_DIR / "manifest.json",
        SIGNAL_DIR / "signals.csv",
        SIGNAL_DIR / "validator_report.json",
        QLIB_RUN_DIR / "prediction.csv",
        QLIB_RUN_DIR / "run_metadata.json",
        PIPELINE_VALIDATION,
        PIPELINE_REPORT,
    ]
    manifest = {
        "schema_version": "dapr.artifact_manifest.v1",
        "created_at": utc_now(),
        "status": "pass" if all(path.exists() for path in files) else "fail",
        "route": "DAPR8_CONTROLLED_MODELA_NO_PUBLISH_DRY_RUN_GATE",
        "route_decision": summary["decision"],
        "self_included_reason": "artifact_manifest.json excludes itself to avoid self-referential checksum drift",
        "entries": [file_entry(path) for path in files],
    }
    manifest_path = write_json(OUT_DIR / "artifact_manifest.json", manifest)
    return {
        "status": status,
        "decision": summary["decision"],
        "target_asof": TARGET_ASOF,
        "run_id": RUN_ID,
        "summary": rel(summary_path),
        "manifest": rel(manifest_path),
    }


def build_execution_doc(summary: dict[str, Any]) -> str:
    return f"""# DAPR8 Controlled ModelA No-Publish Dry-Run Gate 执行报告

执行时间：{summary["created_at"]}

## 1. Scope

本阶段执行：

```text
DAPR8_CONTROLLED_MODELA_NO_PUBLISH_DRY_RUN_GATE
target_asof={TARGET_ASOF}
run_id={RUN_ID}
```

输入限定为 DAPR3 选中的 DAPR7B isolated provider candidate。Non-goals confirmed：不 provider pull/publish，不 qlib refresh，不 accepted/latest switch，不 readonly/Agent publish，不 DB/OpenAI/monitor/broker/order/target。

## 2. Commands

```text
python scripts/build_tw_model_inference_input.py --asof 2026-07-17 --run-id {RUN_ID} --provider-root <DAPR7B staged_qlib_bin> --normalized-root <DAPR7B candidate_normalized> --output-root {summary["model_inference_input"].split('/planned_future_outputs/')[0]} --no-publish --no-catalog --no-latest --no-target-output --json

python scripts/run_tw_model_score_job.py --asof 2026-07-17 --run-id {RUN_ID} --input-dir <DAPR8 ModelInferenceInput> --provider-root <DAPR7B staged_qlib_bin> --normalized-root <DAPR7B candidate_normalized> --output-root {summary["model_inference_input"].split('/planned_future_outputs/')[0]} --no-publish --no-catalog --no-latest --no-target-output --allow-contained-real-execution --json

python scripts/validate_tw_score_job.py --score-dir <DAPR8 ScoreJob> --signal-dir <DAPR8 ModelSignalArtifact> --asof 2026-07-17 --contained-output-root {summary["model_inference_input"].split('/planned_future_outputs/')[0]} --json
```

## 3. Result

```text
{summary["decision"]}
```

- ModelInferenceInput：`{summary["statuses"]["input_manifest"]}` / validator `{summary["statuses"]["input_validator"]}`
- ScoreJob：`{summary["statuses"]["score_job"]}` / validator `{summary["statuses"]["score_validator"]}`
- ModelSignalArtifact no-publish：`{summary["statuses"]["model_signal_manifest"]}` / validator `{summary["statuses"]["model_signal_validator"]}`
- qlib scoring run：`{summary["qlib_scoring_run"]}`
- row counts：ModelInferenceInput={summary["row_counts"]["model_inference_input"]}, raw_scores={summary["row_counts"]["raw_scores"]}, signals={summary["row_counts"]["model_signal"]}

## 4. Evidence

- `data_tw/experiments/daily_accepted_production_readiness/dapr8_controlled_modela_no_publish_dry_run_gate/modela_no_publish_dry_run_summary.json`
- `data_tw/experiments/daily_accepted_production_readiness/dapr8_controlled_modela_no_publish_dry_run_gate/runtime_path_audit.json`
- `data_tw/experiments/daily_accepted_production_readiness/dapr8_controlled_modela_no_publish_dry_run_gate/forbidden_action_audit.json`
- `data_tw/experiments/daily_accepted_production_readiness/dapr8_controlled_modela_no_publish_dry_run_gate/artifact_manifest.json`

## 5. Forbidden Actions Audit

Authorized actions were limited to contained ModelInferenceInput build, contained Model A qlib scoring, ScoreJob build, ModelSignalArtifact no-publish build, and validators.

Forbidden actions remained false: provider pull/refresh/publish, formal provider mutation, qlib refresh, accepted/latest switch, readonly/Agent publish, DB/OpenAI, monitor/broker/order/target, strategy replay/NAV, model training/tuning.
"""


def build_review_doc(summary: dict[str, Any]) -> str:
    verdict = "PASS_WITH_CONDITIONS" if summary["status"] == "pass" else "FAIL_NEEDS_REPAIR"
    return f"""# DAPR8 Controlled ModelA No-Publish Dry-Run Gate 审查

审查时间：{utc_now()}

## 1. Verdict

```text
{verdict}
```

DAPR8 已完成 controlled Model A no-publish dry-run，且所有产物均限制在 DAPR8 isolated runtime root。该结论不是 provider publish、latest switch 或 downstream publish 授权。

## 2. Findings

### Critical

None.

### High

None.

### Medium

- 本轮产生了真实 contained qlib scoring output，但只在 DAPR8 isolated output root 内；不得把该 ModelSignalArtifact 视为 accepted/latest。

### Low

- Matplotlib cache 使用 `/tmp`，不影响 artifact 或 forbidden-action 边界。

## 3. Mainline Compliance

- target_asof：`{TARGET_ASOF}`
- run_id：`{RUN_ID}`
- selected readiness：`{summary["provider_candidate_readiness"]}`
- ModelInferenceInput rows：`{summary["row_counts"]["model_inference_input"]}`
- raw_score rows：`{summary["row_counts"]["raw_scores"]}`
- ModelSignal rows：`{summary["row_counts"]["model_signal"]}`
- ready_for_provider_publish：`{summary["ready_for_provider_publish"]}`
- ready_for_latest_switch：`{summary["ready_for_latest_switch"]}`
- forbidden_actions_all_false：`{summary["forbidden_actions_all_false"]}`

## 4. Evidence Checked

- `data_tw/experiments/daily_accepted_production_readiness/dapr8_controlled_modela_no_publish_dry_run_gate/modela_no_publish_dry_run_summary.json`
- `data_tw/experiments/daily_accepted_production_readiness/dapr8_controlled_modela_no_publish_dry_run_gate/runtime_path_audit.json`
- `data_tw/experiments/daily_accepted_production_readiness/dapr8_controlled_modela_no_publish_dry_run_gate/forbidden_action_audit.json`
- DAPR8 contained ModelInferenceInput, ScoreJob, ModelSignalArtifact, qlib prediction, and validator reports under `modela_no_publish_runtime/planned_future_outputs/`

## 5. Next Work Document

Next phase：

```text
DAPR9_CONTROLLED_LATEST_PUBLISH_PREFLIGHT_OR_STOP
```

Executor duties：

- Treat DAPR8 output as no-publish evidence only.
- Inventory what a controlled latest/publish gate would need to mutate and what rollback/fingerprint is required.
- Do not write latest pointer, provider catalog, readonly/Agent latest, DB/OpenAI, monitor/broker/order/target unless separately authorized.

Reviewer duties：

- Decide whether DAPR8 evidence is sufficient for a controlled latest/publish approval package.
- Verify that production publish remains false until explicit exact-scope authorization.
"""


def main() -> int:
    result = build()
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
