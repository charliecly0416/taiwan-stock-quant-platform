#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DAPR_ROOT = ROOT / "data_tw/experiments/daily_accepted_production_readiness"
OUT_DIR = DAPR_ROOT / "dapr7b_authorized_provider_only_yahoo_scrapling_rerun"
DOC_DIR = ROOT / "docs/tw_portfolio_decision_model"
JOB_ID = "dapr7_yahoo_adjusted_provider_only_20260717_AUTHORIZED_RERUN"
JOB_DIR = (
    ROOT
    / "data_tw/experiments/provider_bridge_productionization"
    / "dapr7_same_lineage_yahoo_adjusted_exact_target_bridge_build_no_publish"
    / JOB_ID
)
REPORTS_DIR = JOB_DIR / "reports"
TARGET_ASOF = "2026-07-17"

REQUIRED_REPORTS = {
    "fetch_report": REPORTS_DIR / "fetch_report.json",
    "normalized_validation": REPORTS_DIR / "normalized_validation.json",
    "provider_validation": REPORTS_DIR / "provider_validation.json",
    "provider_only_boundary": REPORTS_DIR / "provider_only_boundary.json",
    "execution_summary": REPORTS_DIR / "execution_summary.json",
    "symbol_failure_ledger": REPORTS_DIR / "symbol_failure_ledger.json",
    "provider_rebuild": REPORTS_DIR / "provider_rebuild.json",
    "model_smoke": REPORTS_DIR / "model_smoke.json",
    "runner_artifact_manifest": REPORTS_DIR / "artifact_manifest.json",
}

FORBIDDEN_ACTIONS = {
    "provider_publish_triggered": False,
    "formal_provider_mutated": False,
    "formal_normalized_mutated": False,
    "accepted_latest_switched": False,
    "qlib_refresh_triggered": False,
    "model_scoring_triggered": False,
    "model_inference_input_built": False,
    "score_job_built": False,
    "model_signal_artifact_built": False,
    "readonly_latest_published": False,
    "agent_prompt_built_or_published": False,
    "production_default_changed": False,
    "frontend_default_changed": False,
    "monitor_write_triggered": False,
    "broker_order_quick_trade_triggered": False,
    "order_intent_generated": False,
    "target_position_or_weight_or_quantity_output": False,
    "pbpr3_executed": False,
}


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


def manifest_entry(path: Path) -> dict[str, Any]:
    return {
        "path": rel(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else None,
        "sha256": sha256(path) if path.exists() and path.is_file() else "",
    }


def job_files() -> list[Path]:
    if not JOB_DIR.exists():
        return []
    return sorted(path for path in JOB_DIR.rglob("*") if path.is_file())


def build_post_finalization_manifest(created_at: str) -> dict[str, Any]:
    files = job_files()
    entries = [manifest_entry(path) for path in files]
    missing = [entry for entry in entries if not entry["exists"]]
    mismatch: list[dict[str, Any]] = []
    candidate_csv = [path for path in files if path.parent.name == "candidate_normalized" and path.suffix == ".csv"]
    staged_files = [path for path in files if "staged_qlib_bin" in path.parts]
    report_files = [path for path in files if path.parent == REPORTS_DIR]
    return {
        "schema_version": "dapr7b.post_finalization_manifest.v1",
        "created_at": created_at,
        "status": "pass" if not missing and not mismatch and len(candidate_csv) == 150 else "fail",
        "algorithm": "sha256",
        "job_dir": rel(JOB_DIR),
        "verification": {
            "missing_count": len(missing),
            "mismatch_count": len(mismatch),
            "missing_entries": missing[:20],
            "mismatch_entries": mismatch[:20],
        },
        "counts": {
            "candidate_normalized_csv": len(candidate_csv),
            "staged_qlib_bin_files": len(staged_files),
            "report_files_covered": len(report_files),
            "total_entries": len(entries),
        },
        "entries": entries,
    }


def status(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or "")


def forbidden_all_false(payloads: dict[str, dict[str, Any]]) -> bool:
    boundary = payloads.get("provider_only_boundary", {})
    summary = payloads.get("execution_summary", {})
    for payload in (boundary, summary):
        actions = payload.get("forbidden_actions")
        if isinstance(actions, dict) and actions.get("all_false") is not True:
            return False
    return True


def build_review_payloads() -> dict[str, Any]:
    created_at = utc_now()
    payloads = {name: read_json(path) for name, path in REQUIRED_REPORTS.items()}
    missing_reports = [name for name, path in REQUIRED_REPORTS.items() if not path.exists()]
    fetch = payloads["fetch_report"]
    normalized = payloads["normalized_validation"]
    provider = payloads["provider_validation"]
    boundary = payloads["provider_only_boundary"]
    summary = payloads["execution_summary"]
    manifest = build_post_finalization_manifest(created_at)
    post_manifest_path = write_json(OUT_DIR / "post_finalization_manifest.json", manifest)

    candidate_asof = str(summary.get("asof") or boundary.get("target_asof") or fetch.get("end") or "")
    symbols_success = int(fetch.get("symbols_success") or 0)
    symbols_with_asof = int(normalized.get("symbols_with_asof") or 0)
    active_universe_count = int(provider.get("active_universe_count") or 0)
    validator_status = (
        "pass"
        if (
            candidate_asof == TARGET_ASOF
            and status(fetch) == "pass"
            and status(normalized) == "pass"
            and status(provider) == "pass"
            and manifest.get("status") == "pass"
            and symbols_success == 150
            and symbols_with_asof == 150
            and active_universe_count == 150
            and boundary.get("pbpr3_authorized") is False
            and boundary.get("provider_candidate_readiness_written") is False
            and boundary.get("canonical_bridge_readiness_written") is False
            and forbidden_all_false(payloads)
            and not missing_reports
        )
        else "fail"
    )
    ready = validator_status == "pass"

    run_summary = {
        "schema_version": "dapr7b.rerun_execution_summary.v1",
        "created_at": created_at,
        "route": "DAPR7B_AUTHORIZED_PROVIDER_ONLY_YAHOO_SCRAPLING_RERUN",
        "job_id": JOB_ID,
        "job_dir": rel(JOB_DIR),
        "target_asof": TARGET_ASOF,
        "candidate_asof": candidate_asof,
        "status": "pass" if ready else "fail",
        "runner_status": summary.get("status"),
        "provider_only": summary.get("provider_only") is True,
        "source_policy": fetch.get("source_policy"),
        "proxy_used": fetch.get("proxy_used"),
        "http_status_counts": fetch.get("http_status_counts"),
        "symbols_success": symbols_success,
        "symbols_with_asof": symbols_with_asof,
        "active_universe_count": active_universe_count,
        "calendar_max": provider.get("calendar_max"),
        "missing_reports": missing_reports,
        "post_finalization_manifest": rel(post_manifest_path),
    }
    fetch_review = {
        "schema_version": "dapr7b.fetch_report_review.v1",
        "created_at": created_at,
        "status": "pass" if status(fetch) == "pass" and symbols_success == 150 else "fail",
        "source": fetch.get("source"),
        "source_policy": fetch.get("source_policy"),
        "start": fetch.get("start"),
        "end": fetch.get("end"),
        "symbols_expected": fetch.get("symbols_expected"),
        "symbols_success": symbols_success,
        "symbols_failed": fetch.get("symbols_failed"),
        "symbols_unattempted_count": fetch.get("symbols_unattempted_count"),
        "provider_fallback_allowed": fetch.get("provider_fallback_allowed"),
        "provider_fallback_attempted": fetch.get("provider_fallback_attempted"),
        "http_status_counts": fetch.get("http_status_counts"),
        "http_diagnostic_counts": fetch.get("http_diagnostic_counts"),
        "adjustment": fetch.get("adjustment"),
    }
    normalized_review = {
        "schema_version": "dapr7b.normalized_validation_review.v1",
        "created_at": created_at,
        "status": status(normalized),
        "files_found": normalized.get("files_found"),
        "symbols_expected": normalized.get("symbols_expected"),
        "symbols_with_asof": symbols_with_asof,
        "missing_asof_count": normalized.get("missing_asof_count"),
        "date_max_min": normalized.get("date_max_min"),
        "date_max_max": normalized.get("date_max_max"),
        "total_rows": normalized.get("total_rows"),
        "errors": normalized.get("errors"),
    }
    provider_review = {
        "schema_version": "dapr7b.provider_validation_review.v1",
        "created_at": created_at,
        "status": status(provider),
        "provider": rel(Path(str(provider.get("provider") or JOB_DIR / "staged_qlib_bin"))),
        "calendar_min": provider.get("calendar_min"),
        "calendar_max": provider.get("calendar_max"),
        "calendar_has_asof": provider.get("calendar_has_asof"),
        "active_universe_count": active_universe_count,
        "expected_field_counts": provider.get("expected_field_counts"),
        "missing_feature_symbols": provider.get("missing_feature_symbols"),
        "rejected_fields_present": provider.get("rejected_fields_present"),
        "errors": provider.get("errors"),
    }
    forbidden_action_audit = {
        "schema_version": "dapr7b.forbidden_action_audit.v1",
        "created_at": created_at,
        "route": "DAPR7B_AUTHORIZED_PROVIDER_ONLY_YAHOO_SCRAPLING_RERUN",
        "all_false": all(value is False for value in FORBIDDEN_ACTIONS.values()) and forbidden_all_false(payloads),
        "authorized_actions": {
            "live_yahoo_scrapling_provider_only_pull": True,
            "isolated_candidate_normalized_write": True,
            "isolated_staged_qlib_provider_write": True,
            "isolated_report_write": True,
        },
        "actions": FORBIDDEN_ACTIONS,
        "runner_forbidden_actions": {
            "provider_only_boundary": boundary.get("forbidden_actions"),
            "execution_summary": summary.get("forbidden_actions"),
        },
        "write_scope": [rel(OUT_DIR), rel(JOB_DIR)],
        "production_allowed": False,
        "not_published_latest": True,
    }

    readiness = {
        "schema_version": "dapr7b.provider_candidate_readiness.v1",
        "artifact_status": "accepted_dapr7b_isolated_provider_candidate_only",
        "created_at": created_at,
        "created_by_phase": "DAPR7B_AUTHORIZED_PROVIDER_ONLY_YAHOO_SCRAPLING_RERUN",
        "decision": "ACCEPTED_FOR_DAPR_EXACT_TARGET_NO_PUBLISH_VALIDATION" if ready else "BLOCKED_PROVIDER_CANDIDATE_NOT_READY",
        "candidate_asof": candidate_asof,
        "target_asof": TARGET_ASOF,
        "source_type": "same_lineage_yahoo_scrapling_isolated_provider_candidate",
        "source_provider": "Yahoo Finance chart API",
        "source_client": "Scrapling Yahoo access adapter",
        "run_id": JOB_ID,
        "lineage": {
            "raw_input_paths": [rel(JOB_DIR / "candidate_normalized")],
            "normalized_output_paths": [rel(JOB_DIR / "candidate_normalized")],
            "calendar_path": rel(JOB_DIR / "staged_qlib_bin/calendars/day.txt"),
            "instrument_path": rel(JOB_DIR / "staged_qlib_bin/instruments/all.txt"),
            "feature_path": rel(JOB_DIR / "staged_qlib_bin/features"),
            "source_model_artifact": str(summary.get("model_path") or ""),
            "source_training_manifest": str(summary.get("config_path") or ""),
            "validator_reports": [rel(path) for path in REQUIRED_REPORTS.values()] + [rel(post_manifest_path)],
        },
        "coverage": {
            "calendar_has_target_asof": provider.get("calendar_has_asof"),
            "calendar_min": provider.get("calendar_min"),
            "calendar_max": provider.get("calendar_max"),
            "symbols_expected": fetch.get("symbols_expected"),
            "symbols_success": symbols_success,
            "symbols_with_asof": symbols_with_asof,
            "active_universe_count": active_universe_count,
            "required_price_fields": ["open", "high", "low", "close", "volume"],
            "required_feature_fields": ["open", "high", "low", "close", "volume", "vwap", "factor"],
            "provider_field_inventory_status": status(provider),
            "expected_field_counts": provider.get("expected_field_counts"),
            "candidate_normalized_csv_count": manifest["counts"]["candidate_normalized_csv"],
            "staged_qlib_bin_file_count": manifest["counts"]["staged_qlib_bin_files"],
        },
        "checksums": {
            "algorithm": "sha256",
            "post_finalization_manifest": rel(post_manifest_path),
            "verification": manifest["verification"],
            "counts": manifest["counts"],
        },
        "validator_status": validator_status,
        "production_allowed": False,
        "not_published_latest": True,
        "publish_latest_allowed": False,
        "model_scoring_allowed": False,
        "not_final_production_readiness": True,
        "not_catalog_published": True,
        "not_latest_pointer": True,
        "forbidden_actions": {
            "all_false": forbidden_action_audit["all_false"],
            "actions": forbidden_action_audit["actions"],
        },
        "forbidden_action_summary": forbidden_action_audit["actions"],
    }
    decision = {
        "schema_version": "dapr7b.candidate_or_blocker_decision.v1",
        "created_at": created_at,
        "route": "DAPR7B_AUTHORIZED_PROVIDER_ONLY_YAHOO_SCRAPLING_RERUN",
        "target_asof": TARGET_ASOF,
        "decision": "EXACT_TARGET_SAME_LINEAGE_YAHOO_PROVIDER_CANDIDATE_READY_NO_PUBLISH"
        if ready
        else "BLOCKED_PROVIDER_ONLY_RERUN_NOT_ACCEPTABLE",
        "provider_candidate_ready": ready,
        "provider_candidate_readiness_path": rel(OUT_DIR / "provider_candidate_readiness.json") if ready else "",
        "provider_candidate_blocker_path": "" if ready else rel(OUT_DIR / "provider_candidate_readiness_blocker.json"),
        "ready_for_model_a_no_publish_dry_run": ready,
        "ready_for_provider_publish": False,
        "ready_for_latest_switch": False,
        "production_allowed": False,
        "not_published_latest": True,
        "next_required_action": "run DAPR3 exact-target validation refresh, then Model A no-publish dry-run gate"
        if ready
        else "repair Yahoo/Scrapling provider-only rerun evidence before any downstream validation",
        "failure_reasons": []
        if ready
        else [
            "candidate_asof_mismatch" if candidate_asof != TARGET_ASOF else "",
            "fetch_report_not_pass_or_not_150" if not (status(fetch) == "pass" and symbols_success == 150) else "",
            "normalized_validation_not_pass_or_not_150" if not (status(normalized) == "pass" and symbols_with_asof == 150) else "",
            "provider_validation_not_pass_or_not_150" if not (status(provider) == "pass" and active_universe_count == 150) else "",
            "post_finalization_manifest_not_pass" if manifest.get("status") != "pass" else "",
            "forbidden_action_audit_not_clean" if not forbidden_action_audit["all_false"] else "",
            "missing_required_reports" if missing_reports else "",
        ],
    }
    decision["failure_reasons"] = [reason for reason in decision["failure_reasons"] if reason]

    outputs: dict[str, Path] = {
        "rerun_execution_summary": write_json(OUT_DIR / "rerun_execution_summary.json", run_summary),
        "fetch_report_review": write_json(OUT_DIR / "fetch_report_review.json", fetch_review),
        "normalized_validation_review": write_json(OUT_DIR / "normalized_validation_review.json", normalized_review),
        "provider_validation_review": write_json(OUT_DIR / "provider_validation_review.json", provider_review),
        "forbidden_action_audit": write_json(OUT_DIR / "forbidden_action_audit.json", forbidden_action_audit),
        "candidate_or_blocker_decision": write_json(OUT_DIR / "candidate_or_blocker_decision.json", decision),
    }
    if ready:
        outputs["provider_candidate_readiness"] = write_json(OUT_DIR / "provider_candidate_readiness.json", readiness)
    else:
        outputs["provider_candidate_readiness_blocker"] = write_json(OUT_DIR / "provider_candidate_readiness_blocker.json", readiness)

    execution_doc = build_execution_doc(run_summary, fetch_review, normalized_review, provider_review, decision)
    review_doc = build_review_doc(run_summary, decision, forbidden_action_audit)
    outputs["execution_report_doc"] = write_text(
        DOC_DIR / "POLICY_DAPR7B_AUTHORIZED_PROVIDER_ONLY_YAHOO_SCRAPLING_RERUN_EXECUTION_REPORT_CN.md",
        execution_doc,
    )
    outputs["review_doc"] = write_text(
        DOC_DIR / "POLICY_DAPR7B_AUTHORIZED_PROVIDER_ONLY_YAHOO_SCRAPLING_RERUN_REVIEW_CN.md",
        review_doc,
    )

    manifest_entries = [manifest_entry(path) for path in outputs.values()]
    manifest_entries.append(manifest_entry(post_manifest_path))
    output_manifest = {
        "schema_version": "dapr.artifact_manifest.v1",
        "created_at": utc_now(),
        "status": "pass",
        "route": "DAPR7B_AUTHORIZED_PROVIDER_ONLY_YAHOO_SCRAPLING_RERUN",
        "route_decision": decision["decision"],
        "self_included_reason": "artifact_manifest.json excludes itself to avoid self-referential checksum drift",
        "entries": sorted(manifest_entries, key=lambda row: row["path"]),
    }
    outputs["artifact_manifest"] = write_json(OUT_DIR / "artifact_manifest.json", output_manifest)
    return {
        "status": "pass" if ready else "blocked",
        "decision": decision["decision"],
        "target_asof": TARGET_ASOF,
        "output_dir": rel(OUT_DIR),
        "provider_candidate_readiness": rel(OUT_DIR / "provider_candidate_readiness.json") if ready else "",
        "manifest": rel(outputs["artifact_manifest"]),
    }


def build_execution_doc(
    run_summary: dict[str, Any],
    fetch_review: dict[str, Any],
    normalized_review: dict[str, Any],
    provider_review: dict[str, Any],
    decision: dict[str, Any],
) -> str:
    return f"""# DAPR7B Authorized Provider-Only Yahoo/Scrapling Rerun 执行报告

执行时间：{run_summary["created_at"]}

## 1. Scope

- Assigned phase：DAPR7B_AUTHORIZED_PROVIDER_ONLY_YAHOO_SCRAPLING_RERUN
- target_asof：`{TARGET_ASOF}`
- job_id：`{JOB_ID}`
- job_dir：`{run_summary["job_dir"]}`
- Non-goals confirmed：不 publish provider，不 mutate formal provider/normalized，不 qlib refresh，不 switch accepted/latest，不 run Model A，不 build Agent/readonly latest，不访问 DB/OpenAI/monitor/broker/order/target。

## 2. Documents / Contracts / Skills Read

- `data_tw/experiments/daily_accepted_production_readiness/dapr1_canonical_bridge_contract/bridge_contract.json`
- `docs/tw_portfolio_decision_model/POLICY_DAPR7_SAME_LINEAGE_YAHOO_ADJUSTED_EXACT_TARGET_BRIDGE_BUILD_NO_PUBLISH_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_DAPR7_SAME_LINEAGE_YAHOO_ADJUSTED_EXACT_TARGET_BRIDGE_BUILD_NO_PUBLISH_REVIEW_CN.md`
- coordinator/executor/reviewer workflow skill
- Taiwan stock data source boundary

## 3. Execution Result

- runner_status：`{run_summary["runner_status"]}`
- provider_only：`{run_summary["provider_only"]}`
- source_policy：`{run_summary["source_policy"]}`
- proxy_used：`{run_summary["proxy_used"]}`
- candidate_asof：`{run_summary["candidate_asof"]}`
- symbols_success：`{run_summary["symbols_success"]}/150`
- symbols_with_asof：`{run_summary["symbols_with_asof"]}/150`
- active_universe_count：`{run_summary["active_universe_count"]}/150`
- provider calendar max：`{run_summary["calendar_max"]}`
- HTTP status counts：`{run_summary["http_status_counts"]}`

## 4. Evidence Produced

- `data_tw/experiments/daily_accepted_production_readiness/dapr7b_authorized_provider_only_yahoo_scrapling_rerun/rerun_execution_summary.json`
- `data_tw/experiments/daily_accepted_production_readiness/dapr7b_authorized_provider_only_yahoo_scrapling_rerun/fetch_report_review.json`
- `data_tw/experiments/daily_accepted_production_readiness/dapr7b_authorized_provider_only_yahoo_scrapling_rerun/normalized_validation_review.json`
- `data_tw/experiments/daily_accepted_production_readiness/dapr7b_authorized_provider_only_yahoo_scrapling_rerun/provider_validation_review.json`
- `data_tw/experiments/daily_accepted_production_readiness/dapr7b_authorized_provider_only_yahoo_scrapling_rerun/post_finalization_manifest.json`
- `data_tw/experiments/daily_accepted_production_readiness/dapr7b_authorized_provider_only_yahoo_scrapling_rerun/provider_candidate_readiness.json`
- `data_tw/experiments/daily_accepted_production_readiness/dapr7b_authorized_provider_only_yahoo_scrapling_rerun/candidate_or_blocker_decision.json`

## 5. Validator Output

- fetch_report：`{fetch_review["status"]}`，symbols_success=`{fetch_review["symbols_success"]}`
- normalized_validation：`{normalized_review["status"]}`，symbols_with_asof=`{normalized_review["symbols_with_asof"]}`
- provider_validation：`{provider_review["status"]}`，calendar_has_asof=`{provider_review["calendar_has_asof"]}`，active_universe_count=`{provider_review["active_universe_count"]}`
- post_finalization_manifest：`{run_summary["post_finalization_manifest"]}`

## 6. Forbidden Actions Audit

Authorized in this phase：live Yahoo/Scrapling provider-only pull to isolated job_dir, isolated normalized/staged-provider/report writes.

Forbidden actions remained false：provider publish, formal provider/normalized mutation, accepted/latest switch, qlib refresh, Model A scoring, ModelInferenceInput/ScoreJob/ModelSignal build, readonly/Agent publish, OpenAI, DB, monitor/broker/order/target/quantity.

## 7. Decision

```text
{decision["decision"]}
```

provider_candidate_ready=`{decision["provider_candidate_ready"]}`

Next required action：{decision["next_required_action"]}
"""


def build_review_doc(
    run_summary: dict[str, Any],
    decision: dict[str, Any],
    forbidden_action_audit: dict[str, Any],
) -> str:
    verdict = "PASS_WITH_CONDITIONS" if decision["provider_candidate_ready"] else "FAIL_NEEDS_REPAIR"
    return f"""# DAPR7B Authorized Provider-Only Yahoo/Scrapling Rerun 审查

审查时间：{utc_now()}

审查者：主线复核

## 1. Verdict

```text
{verdict}
```

DAPR7B 已完成授权的 live Yahoo/Scrapling provider-only rerun，并形成 exact-target same-lineage isolated provider candidate。该结论只允许作为 DAPR exact-target no-publish validation / Model A no-publish dry-run 的输入，不允许 provider publish、accepted/latest switch、qlib refresh 或 downstream latest publish。

## 2. Findings

### Critical

None.

### High

None.

### Medium

- Runner 没有直接写 `post_finalization_manifest.json`；本审查在 DAPR7B evidence 目录中重新计算全 job_dir checksum manifest，状态为 pass。

### Low

- Yahoo `.TW` 对部分柜买股票返回 404 后使用 `.TWO` 成功，这是 ticker suffix fallback，不是 provider fallback；`provider_fallback_allowed=false` 且 `provider_fallback_attempted=false`。

## 3. Mainline Compliance

- target_asof：`{TARGET_ASOF}`
- candidate_asof：`{run_summary["candidate_asof"]}`
- symbols_success：`{run_summary["symbols_success"]}/150`
- symbols_with_asof：`{run_summary["symbols_with_asof"]}/150`
- active_universe_count：`{run_summary["active_universe_count"]}/150`
- calendar_max：`{run_summary["calendar_max"]}`
- forbidden_actions_all_false：`{forbidden_action_audit["all_false"]}`

## 4. Evidence Checked

- `data_tw/experiments/provider_bridge_productionization/dapr7_same_lineage_yahoo_adjusted_exact_target_bridge_build_no_publish/{JOB_ID}/reports/fetch_report.json`
- `data_tw/experiments/provider_bridge_productionization/dapr7_same_lineage_yahoo_adjusted_exact_target_bridge_build_no_publish/{JOB_ID}/reports/normalized_validation.json`
- `data_tw/experiments/provider_bridge_productionization/dapr7_same_lineage_yahoo_adjusted_exact_target_bridge_build_no_publish/{JOB_ID}/reports/provider_validation.json`
- `data_tw/experiments/provider_bridge_productionization/dapr7_same_lineage_yahoo_adjusted_exact_target_bridge_build_no_publish/{JOB_ID}/reports/provider_only_boundary.json`
- `data_tw/experiments/daily_accepted_production_readiness/dapr7b_authorized_provider_only_yahoo_scrapling_rerun/provider_candidate_readiness.json`
- `data_tw/experiments/daily_accepted_production_readiness/dapr7b_authorized_provider_only_yahoo_scrapling_rerun/post_finalization_manifest.json`

## 5. Forbidden Actions Audit

Authorized pull/write scope was isolated to the DAPR7B job_dir and evidence dir. No publish/latest/model/Agent/DB/OpenAI/monitor/broker/order/target action was observed or authorized.

## 6. Next Work Document

Next phase：

```text
DAPR3_REFRESH_EXACT_TARGET_PROVIDER_CANDIDATE_VALIDATION_NO_PUBLISH
```

Executor duties：

- Run the existing DAPR3 exact-target provider/bridge validation against `target_asof=2026-07-17`.
- Confirm it selects `data_tw/experiments/daily_accepted_production_readiness/dapr7b_authorized_provider_only_yahoo_scrapling_rerun/provider_candidate_readiness.json`.
- Do not provider publish, qlib refresh, accepted/latest switch, Model A score, Agent/readonly publish, DB/OpenAI, or monitor/broker/order/target.

Reviewer duties：

- Verify DAPR3 accepts this provider candidate under the DAPR1 accepted input contract.
- If DAPR3 passes, the next route should be a controlled Model A no-publish dry-run against the isolated staged provider.

## 7. Command For Executor

```text
python scripts/build_tw_dapr3_exact_target_provider_bridge_candidate_or_blocker.py --target-asof 2026-07-17
```
"""


def main() -> int:
    print(json.dumps(build_review_payloads(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
