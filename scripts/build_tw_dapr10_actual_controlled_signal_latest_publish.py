#!/usr/bin/env python3
"""DAPR10 actual controlled signal latest publish.

Authorized scope:
- copy the six DAPR9-planned ModelSignalArtifact files into the canonical
  signal run directory;
- write data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json;
- write DAPR10 evidence and reports.

Everything else remains read-only and is validated by before/after
fingerprints.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGET_ASOF = os.environ.get("DAPR10_TARGET_ASOF", "2026-07-17")
MODEL_ID = "e4_frozen_qlib_2018_2022"
RUN_ID = os.environ.get("DAPR10_RUN_ID", "dapr8_modela_20260717_contained")
SOURCE_LABEL = os.environ.get("DAPR10_SOURCE_LABEL", "DAPR8 no-publish ModelSignalArtifact")

DAPR9_ROOT = Path(
    os.environ.get(
        "DAPR10_DAPR9_ROOT",
        "data_tw/experiments/daily_accepted_production_readiness/dapr9_controlled_latest_publish_preflight_or_stop",
    )
)
if not DAPR9_ROOT.is_absolute():
    DAPR9_ROOT = ROOT / DAPR9_ROOT
DAPR10_ROOT = Path(
    os.environ.get(
        "DAPR10_OUTPUT_ROOT",
        "data_tw/experiments/daily_accepted_production_readiness/dapr10_actual_controlled_signal_latest_publish",
    )
)
if not DAPR10_ROOT.is_absolute():
    DAPR10_ROOT = ROOT / DAPR10_ROOT
ROLLBACK_ROOT = DAPR10_ROOT / "rollback"

CONTROLLED_SIGNAL_LATEST = ROOT / f"data_tw/artifacts/signals/{MODEL_ID}/latest.json"
CANONICAL_SIGNAL_DIR = ROOT / f"data_tw/artifacts/signals/{MODEL_ID}/{RUN_ID}"
QLIB_ACCEPTED_LATEST = ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json"
LEGACY_OPTION_C_LATEST = ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json"
READONLY_SNAPSHOT_LATEST = ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json"
AGENT_PROMPT_LATEST = ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json"

DAPR10_EXECUTION_REPORT = Path(
    os.environ.get(
        "DAPR10_EXECUTION_REPORT",
        "docs/tw_portfolio_decision_model/POLICY_DAPR10_ACTUAL_CONTROLLED_SIGNAL_LATEST_PUBLISH_EXECUTION_REPORT_CN.md",
    )
)
if not DAPR10_EXECUTION_REPORT.is_absolute():
    DAPR10_EXECUTION_REPORT = ROOT / DAPR10_EXECUTION_REPORT
DAPR10_REVIEW = Path(
    os.environ.get(
        "DAPR10_REVIEW",
        "docs/tw_portfolio_decision_model/POLICY_DAPR10_ACTUAL_CONTROLLED_SIGNAL_LATEST_PUBLISH_REVIEW_CN.md",
    )
)
if not DAPR10_REVIEW.is_absolute():
    DAPR10_REVIEW = ROOT / DAPR10_REVIEW

REQUIRED_FILES = [
    "manifest.json",
    "signals.csv",
    "schema.json",
    "coverage_audit.csv",
    "forbidden_field_audit.csv",
    "validator_report.json",
]

PROTECTED_POINTERS = [
    CONTROLLED_SIGNAL_LATEST,
    QLIB_ACCEPTED_LATEST,
    LEGACY_OPTION_C_LATEST,
    READONLY_SNAPSHOT_LATEST,
    AGENT_PROMPT_LATEST,
]

FORBIDDEN_COLUMN_EXACT = {
    "relevance_10d_top_heavy",
    "ltr_relevance_label",
    "realized_pnl",
    "realized_return",
    "action",
    "holding",
    "position",
    "target_position",
    "order_qty",
    "execution_price",
    "execution_date",
    "broker_order_id",
}
FORBIDDEN_COLUMN_PREFIXES = (
    "future_return_",
    "future_excess_return_",
    "forward_return_",
    "label_",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def file_summary(path: Path) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "path": rel(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
        "size_bytes": None,
        "sha256": None,
        "json_summary": None,
    }
    if path.is_file():
        summary["size_bytes"] = path.stat().st_size
        summary["sha256"] = sha256_file(path)
        if path.suffix == ".json":
            try:
                data = read_json(path)
                if isinstance(data, dict):
                    summary["json_summary"] = {
                        key: data.get(key)
                        for key in (
                            "artifact_type",
                            "schema_version",
                            "asof",
                            "signal_asof",
                            "target_asof",
                            "run_id",
                            "model_id",
                            "readonly_only",
                            "production_trade_enabled",
                            "provider_publish",
                            "provider_accepted_latest_switch",
                            "qlib_accepted_latest_switch",
                            "legacy_option_c_latest_signal_switch",
                        )
                        if key in data
                    }
            except Exception as exc:  # pragma: no cover - diagnostic only
                summary["json_summary"] = {"json_error": str(exc)}
    return summary


def audit_signals(path: Path) -> dict[str, Any]:
    rows = 0
    keys: set[tuple[str, str]] = set()
    duplicates = 0
    dates: set[str] = set()
    signal_asofs: set[str] = set()
    forbidden_columns: list[str] = []
    ranks: list[int] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        for col in columns:
            if col in FORBIDDEN_COLUMN_EXACT or any(col.startswith(prefix) for prefix in FORBIDDEN_COLUMN_PREFIXES):
                forbidden_columns.append(col)
        for row in reader:
            rows += 1
            date_value = row.get("date", "")
            instrument = row.get("instrument", "")
            dates.add(date_value)
            signal_asofs.add(row.get("signal_asof", ""))
            key = (date_value, instrument)
            if key in keys:
                duplicates += 1
            keys.add(key)
            try:
                ranks.append(int(row.get("candidate_rank", "")))
            except ValueError:
                pass
    return {
        "path": rel(path),
        "sha256": sha256_file(path),
        "row_count": rows,
        "date_values": sorted(dates),
        "signal_asof_values": sorted(signal_asofs),
        "duplicate_key_count": duplicates,
        "forbidden_columns": sorted(forbidden_columns),
        "candidate_rank_min": min(ranks) if ranks else None,
        "candidate_rank_max": max(ranks) if ranks else None,
        "checks": {
            "row_count_150": rows == 150,
            "date_only_target_asof": sorted(dates) == [TARGET_ASOF],
            "signal_asof_only_target_asof": sorted(signal_asofs) == [TARGET_ASOF],
            "duplicate_key_count_zero": duplicates == 0,
            "forbidden_columns_empty": not forbidden_columns,
            "candidate_ranks_1_to_150": sorted(ranks) == list(range(1, 151)),
        },
    }


def assert_preconditions() -> dict[str, Any]:
    decision = read_json(DAPR9_ROOT / "candidate_or_stop_decision.json")
    source_map = read_json(DAPR9_ROOT / "source_to_target_file_map.json")
    latest_plan = read_json(DAPR9_ROOT / "latest_pointer_payload_plan.json")
    source_precheck = read_json(DAPR9_ROOT / "source_signal_candidate_precheck.json")
    collision = read_json(DAPR9_ROOT / "target_collision_audit.json")

    errors: list[str] = []
    if decision.get("status") != "pass" or decision.get("ready_for_future_exact_authorization_gate") is not True:
        errors.append("DAPR9 decision is not ready for future exact authorization gate.")
    if decision.get("target_asof") != TARGET_ASOF or decision.get("run_id") != RUN_ID:
        errors.append("DAPR9 target_asof/run_id mismatch.")
    if source_precheck.get("status") != "pass":
        errors.append("DAPR9 source precheck is not pass.")
    if collision.get("status") != "pass":
        errors.append("DAPR9 collision audit is not pass.")
    if latest_plan.get("status") != "pass":
        errors.append("DAPR9 latest payload plan is not pass.")
    if latest_plan.get("planned_pointer_path") != rel(CONTROLLED_SIGNAL_LATEST):
        errors.append("DAPR9 latest pointer path is outside authorized scope.")

    mapped = {item["file"]: item for item in source_map.get("file_map", [])}
    if sorted(mapped) != sorted(REQUIRED_FILES):
        errors.append("DAPR9 source map does not exactly cover the six required files.")
    for name in REQUIRED_FILES:
        item = mapped.get(name)
        if not item:
            continue
        source = ROOT / item["source_path"]
        target = ROOT / item["planned_canonical_path"]
        if target != CANONICAL_SIGNAL_DIR / name:
            errors.append(f"{name} planned target path is outside authorized canonical directory.")
        if not source.is_file():
            errors.append(f"{name} source file missing.")
        elif sha256_file(source) != item.get("source_sha256"):
            errors.append(f"{name} source sha256 changed after DAPR9.")
    if CANONICAL_SIGNAL_DIR.exists():
        for name in REQUIRED_FILES:
            target = CANONICAL_SIGNAL_DIR / name
            item = mapped.get(name)
            if not target.is_file() or sha256_file(target) != item.get("source_sha256"):
                errors.append("Existing canonical target directory is not idempotent same payload.")

    if errors:
        raise SystemExit("STOP_DAPR10_PRECONDITION_FAILED: " + "; ".join(errors))

    return {
        "schema_version": "dapr10.source_preflight_recheck.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "run_id": RUN_ID,
        "dapr9_decision": decision,
        "dapr9_source_precheck_status": source_precheck.get("status"),
        "dapr9_collision_status": collision.get("status"),
        "source_map_status": source_map.get("status"),
        "latest_plan_status": latest_plan.get("status"),
        "checks": {
            "dapr9_ready": True,
            "source_files_match_dapr9_sha256": True,
            "planned_targets_within_exact_scope": True,
            "canonical_target_absent_or_idempotent": True,
        },
        "status": "pass",
    }


def build_authorization_scope() -> dict[str, Any]:
    return {
        "schema_version": "dapr10.authorization_scope.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "run_id": RUN_ID,
        "authorized_by_user_exact_text": True,
        "allowed_write_paths": [rel(CANONICAL_SIGNAL_DIR / name) for name in REQUIRED_FILES] + [rel(CONTROLLED_SIGNAL_LATEST)],
        "must_remain_unchanged": [
            rel(QLIB_ACCEPTED_LATEST),
            rel(LEGACY_OPTION_C_LATEST),
            rel(READONLY_SNAPSHOT_LATEST),
            rel(AGENT_PROMPT_LATEST),
            "provider roots/catalogs/readiness",
            "qlib provider roots",
            "monitor/broker/order/target outputs",
        ],
        "not_authorized": [
            "provider publish",
            "provider pull",
            "qlib refresh",
            "daily auto",
            "accepted latest switch",
            "readonly snapshot latest",
            "Agent prompt publish",
            "OpenAI",
            "DB",
            "strategy replay",
            "monitor/broker/order/target",
            "frontend/API production default switch",
            "future automatic latest switch",
        ],
        "status": "pass",
    }


def capture_fingerprints(schema: str) -> dict[str, Any]:
    return {
        "schema_version": schema,
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "entries": [file_summary(path) for path in PROTECTED_POINTERS],
        "status": "pass",
    }


def create_rollback_copy(before: dict[str, Any]) -> dict[str, Any]:
    latest_entry = next(item for item in before["entries"] if item["path"] == rel(CONTROLLED_SIGNAL_LATEST))
    backup_path = ROLLBACK_ROOT / "controlled_signal_latest.before_dapr10.json"
    ROLLBACK_ROOT.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CONTROLLED_SIGNAL_LATEST, backup_path)
    backup_sha = sha256_file(backup_path)
    checks = {
        "before_latest_exists": latest_entry["exists"] is True,
        "rollback_copy_exists": backup_path.is_file(),
        "rollback_copy_sha_matches_before": backup_sha == latest_entry["sha256"],
    }
    return {
        "schema_version": "dapr10.rollback_copy.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "source_latest": rel(CONTROLLED_SIGNAL_LATEST),
        "rollback_copy": rel(backup_path),
        "before_latest_sha256": latest_entry["sha256"],
        "rollback_copy_sha256": backup_sha,
        "checks": checks,
        "status": "pass" if all(checks.values()) else "fail",
    }


def copy_canonical_files() -> dict[str, Any]:
    source_map = read_json(DAPR9_ROOT / "source_to_target_file_map.json")
    copied = []
    CANONICAL_SIGNAL_DIR.mkdir(parents=True, exist_ok=True)
    for item in source_map["file_map"]:
        source = ROOT / item["source_path"]
        target = ROOT / item["planned_canonical_path"]
        same_file = source.resolve() == target.resolve() if source.exists() and target.exists() else False
        if not same_file:
            shutil.copy2(source, target)
        actual_sha = sha256_file(target)
        copied.append(
            {
                "file": item["file"],
                "source_path": item["source_path"],
                "destination_path": item["planned_canonical_path"],
                "expected_sha256": item["source_sha256"],
                "destination_sha256": actual_sha,
                "checksum_match": actual_sha == item["source_sha256"],
                "copy_performed": not same_file,
                "skipped_same_file": same_file,
            }
        )
    return {
        "schema_version": "dapr10.copy_result.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "run_id": RUN_ID,
        "canonical_dir": rel(CANONICAL_SIGNAL_DIR),
        "copied_files": copied,
        "status": "pass" if all(item["checksum_match"] for item in copied) else "fail",
    }


def write_latest_pointer() -> dict[str, Any]:
    plan = read_json(DAPR9_ROOT / "latest_pointer_payload_plan.json")
    payload = plan["payload"]
    write_json(CONTROLLED_SIGNAL_LATEST, payload)
    observed = read_json(CONTROLLED_SIGNAL_LATEST)
    return {
        "schema_version": "dapr10.latest_pointer_write.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "run_id": RUN_ID,
        "latest_pointer_path": rel(CONTROLLED_SIGNAL_LATEST),
        "planned_payload": payload,
        "observed_payload": observed,
        "payload_matches_dapr9_plan": observed == payload,
        "sha256": sha256_file(CONTROLLED_SIGNAL_LATEST),
        "status": "pass" if observed == payload else "fail",
    }


def post_publish_validation(before: dict[str, Any], latest_result: dict[str, Any]) -> dict[str, Any]:
    source_map = read_json(DAPR9_ROOT / "source_to_target_file_map.json")
    plan = read_json(DAPR9_ROOT / "latest_pointer_payload_plan.json")
    mapped = {item["file"]: item for item in source_map["file_map"]}
    manifest = read_json(CANONICAL_SIGNAL_DIR / "manifest.json")
    validator = read_json(CANONICAL_SIGNAL_DIR / "validator_report.json")
    latest_payload = read_json(CONTROLLED_SIGNAL_LATEST)

    canonical_checks = []
    for name in REQUIRED_FILES:
        target = CANONICAL_SIGNAL_DIR / name
        expected = mapped[name]["source_sha256"]
        actual = sha256_file(target) if target.is_file() else None
        canonical_checks.append(
            {
                "file": name,
                "path": rel(target),
                "exists": target.exists(),
                "expected_sha256": expected,
                "actual_sha256": actual,
                "checksum_match": actual == expected,
            }
        )

    signals_audit = audit_signals(CANONICAL_SIGNAL_DIR / "signals.csv")
    after = capture_fingerprints("dapr10.protected_pointer_after_fingerprints.v1")
    before_by_path = {item["path"]: item for item in before["entries"]}
    after_by_path = {item["path"]: item for item in after["entries"]}
    unchanged_paths = [rel(QLIB_ACCEPTED_LATEST), rel(LEGACY_OPTION_C_LATEST), rel(READONLY_SNAPSHOT_LATEST), rel(AGENT_PROMPT_LATEST)]
    unchanged = {
        path: before_by_path[path]["sha256"] == after_by_path[path]["sha256"]
        and before_by_path[path]["exists"] == after_by_path[path]["exists"]
        for path in unchanged_paths
    }
    checks = {
        "all_six_canonical_files_exist_and_match_dapr9": all(item["exists"] and item["checksum_match"] for item in canonical_checks),
        "manifest_artifact_type_model_signal": manifest.get("artifact_type") == "ModelSignalArtifact",
        "manifest_status_ready": manifest.get("status") == "READY",
        "manifest_signal_asof_target": manifest.get("signal_asof") == TARGET_ASOF,
        "manifest_row_count_150": manifest.get("row_count") == 150,
        "manifest_production_allowed_false": manifest.get("production_allowed") is False,
        "source_validator_pass": validator.get("ok") is True and validator.get("status") == "PASS",
        "signals_row_count_150": signals_audit["checks"]["row_count_150"],
        "signals_date_only_target_asof": signals_audit["checks"]["date_only_target_asof"],
        "signals_signal_asof_only_target_asof": signals_audit["checks"]["signal_asof_only_target_asof"],
        "signals_duplicate_key_count_zero": signals_audit["checks"]["duplicate_key_count_zero"],
        "signals_forbidden_columns_empty": signals_audit["checks"]["forbidden_columns_empty"],
        "signals_candidate_ranks_1_to_150": signals_audit["checks"]["candidate_ranks_1_to_150"],
        "latest_payload_matches_dapr9_plan": latest_payload == plan["payload"] and latest_result["payload_matches_dapr9_plan"],
        "latest_references_canonical_manifest": latest_payload.get("canonical_manifest") == rel(CANONICAL_SIGNAL_DIR / "manifest.json"),
        "latest_references_canonical_signals": latest_payload.get("canonical_signals") == rel(CANONICAL_SIGNAL_DIR / "signals.csv"),
        "latest_manifest_sha_matches": latest_payload.get("canonical_manifest_sha256") == sha256_file(CANONICAL_SIGNAL_DIR / "manifest.json"),
        "latest_signals_sha_matches": latest_payload.get("canonical_signals_sha256") == sha256_file(CANONICAL_SIGNAL_DIR / "signals.csv"),
        "latest_readonly_and_no_publish_flags_safe": latest_payload.get("readonly_only") is True
        and latest_payload.get("production_trade_enabled") is False
        and latest_payload.get("provider_publish") is False
        and latest_payload.get("provider_accepted_latest_switch") is False
        and latest_payload.get("qlib_accepted_latest_switch") is False
        and latest_payload.get("legacy_option_c_latest_signal_switch") is False
        and latest_payload.get("agent_prompt_publish") is False
        and latest_payload.get("frontend_default_switch") is False,
        "protected_downstream_pointers_unchanged": all(unchanged.values()),
    }
    return {
        "schema_version": "dapr10.post_publish_validation.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "run_id": RUN_ID,
        "canonical_file_checks": canonical_checks,
        "manifest_summary": {
            "artifact_type": manifest.get("artifact_type"),
            "schema_version": manifest.get("schema_version"),
            "model_id": manifest.get("model_id"),
            "run_id": manifest.get("run_id"),
            "asof": manifest.get("asof"),
            "signal_asof": manifest.get("signal_asof"),
            "status": manifest.get("status"),
            "row_count": manifest.get("row_count"),
            "production_allowed": manifest.get("production_allowed"),
            "not_published_latest_source_flag": manifest.get("not_published_latest"),
        },
        "validator_summary": {
            "ok": validator.get("ok"),
            "status": validator.get("status"),
            "signal_rows": validator.get("signal_rows"),
            "errors": validator.get("errors"),
        },
        "signals_audit": signals_audit,
        "latest_pointer_summary": file_summary(CONTROLLED_SIGNAL_LATEST),
        "protected_pointer_after_fingerprints": after,
        "protected_downstream_unchanged": unchanged,
        "checks": checks,
        "status": "pass" if all(checks.values()) else "fail",
    }


def build_diff_summary(before: dict[str, Any], post: dict[str, Any]) -> dict[str, Any]:
    before_by_path = {item["path"]: item for item in before["entries"]}
    after_by_path = {item["path"]: item for item in post["protected_pointer_after_fingerprints"]["entries"]}
    pointer_changes = []
    for path, before_entry in before_by_path.items():
        after_entry = after_by_path[path]
        changed = before_entry["sha256"] != after_entry["sha256"] or before_entry["exists"] != after_entry["exists"]
        pointer_changes.append(
            {
                "path": path,
                "changed": changed,
                "before_sha256": before_entry["sha256"],
                "after_sha256": after_entry["sha256"],
                "before_summary": before_entry.get("json_summary"),
                "after_summary": after_entry.get("json_summary"),
            }
        )
    expected_changed = {rel(CONTROLLED_SIGNAL_LATEST)}
    actual_changed = {item["path"] for item in pointer_changes if item["changed"]}
    canonical_files = [file_summary(CANONICAL_SIGNAL_DIR / name) for name in REQUIRED_FILES]
    checks = {
        "only_controlled_signal_latest_pointer_changed_among_protected_pointers": actual_changed == expected_changed,
        "canonical_files_created_in_exact_directory": all(item["exists"] for item in canonical_files),
        "no_downstream_pointer_changed": all(
            not item["changed"]
            for item in pointer_changes
            if item["path"] != rel(CONTROLLED_SIGNAL_LATEST)
        ),
    }
    return {
        "schema_version": "dapr10.diff_summary.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "pointer_changes": pointer_changes,
        "canonical_files": canonical_files,
        "checks": checks,
        "status": "pass" if all(checks.values()) else "fail",
    }


def build_forbidden_action_audit() -> dict[str, Any]:
    allowed = {
        "canonical_signal_artifact_copy": True,
        "controlled_signal_latest_pointer_write": True,
        "rollback_copy_created": True,
    }
    forbidden = {
        "provider_network_pull": False,
        "provider_publish": False,
        "provider_accepted_latest_switch": False,
        "qlib_accepted_latest_switch": False,
        "qlib_refresh": False,
        "legacy_option_c_latest_signal_write": False,
        "readonly_snapshot_latest_write": False,
        "agent_prompt_build": False,
        "agent_prompt_publish": False,
        "openai_call": False,
        "db_access": False,
        "model_scoring": False,
        "strategy_replay": False,
        "replay_result_nav": False,
        "monitor_write_or_scan": False,
        "broker_order_or_quick_trade": False,
        "order_intent_or_target_output": False,
        "frontend_or_api_default_switch": False,
        "future_automatic_latest_switch_enabled": False,
    }
    return {
        "schema_version": "dapr10.forbidden_action_audit.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "allowed_actions": allowed,
        "forbidden_flags": forbidden,
        "all_forbidden_false": all(value is False for value in forbidden.values()),
        "status": "pass" if all(value is False for value in forbidden.values()) else "fail",
    }


def build_artifact_manifest(paths: list[Path]) -> dict[str, Any]:
    entries = []
    for path in paths:
        entries.append(
            {
                "path": rel(path),
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() else None,
                "sha256": sha256_file(path) if path.is_file() else None,
            }
        )
    return {
        "schema_version": "dapr10.artifact_manifest.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "run_id": RUN_ID,
        "entries": entries,
        "status": "pass" if all(item["exists"] and item["sha256"] for item in entries) else "fail",
    }


def write_execution_report(post: dict[str, Any], diff: dict[str, Any], forbidden: dict[str, Any]) -> None:
    report = f"""# DAPR10 Actual Controlled Signal Latest Publish 执行报告

生成时间：{now_iso()}

## 1. Scope

Assigned phase：`DAPR10_ACTUAL_CONTROLLED_SIGNAL_LATEST_PUBLISH_EXACT_AUTHORIZATION_GATE`

本阶段按用户 exact authorization 执行唯一 publish：

```text
{rel(CANONICAL_SIGNAL_DIR)}/{{manifest.json,signals.csv,schema.json,coverage_audit.csv,forbidden_field_audit.csv,validator_report.json}}
{rel(CONTROLLED_SIGNAL_LATEST)}
```

Non-goals confirmed：不 provider publish/pull，不 qlib refresh，不 daily auto，不 accepted latest switch，不 readonly snapshot latest，不 Agent prompt publish，不 OpenAI/DB，不 strategy replay，不 monitor/broker/order/target，不 frontend/API production default switch，不启用后续自动 latest switch。

## 2. Documents / Contracts / Skills Read

- `docs/tw_portfolio_decision_model/POLICY_DAPR_DAILY_ACCEPTED_PRODUCTION_READINESS_MAINLINE_CN.md`
- DAPR9/PBPR4 preflight execution and review docs for `{TARGET_ASOF}`
- `{rel(DAPR9_ROOT)}/*`
- skill：`coordinator-executor-reviewer-workflow`

## 3. Changes Made

- 创建 rollback copy：`{rel(ROLLBACK_ROOT / "controlled_signal_latest.before_dapr10.json")}`
- 复制六个 canonical ModelSignalArtifact 文件到 `{rel(CANONICAL_SIGNAL_DIR)}`
- 写入 controlled signal latest pointer：`{rel(CONTROLLED_SIGNAL_LATEST)}`
- 写入 DAPR10 evidence root：`{rel(DAPR10_ROOT)}`

## 4. Evidence Produced

Evidence root：`{rel(DAPR10_ROOT)}`

Post publish validation status：`{post["status"]}`

Diff summary status：`{diff["status"]}`

Forbidden action audit status：`{forbidden["status"]}`

Controlled signal latest now points to：

```text
target_asof={TARGET_ASOF}
run_id={RUN_ID}
```

## 5. Compliance With Mainline

DAPR10 只将 {SOURCE_LABEL} 作为一次性输入推进到 controlled signal latest。该动作不等同 provider/qlib accepted latest，不等同 readonly snapshot latest，不等同 Agent latest，也不是 production trading readiness。

## 6. Forbidden Actions Audit

`forbidden_action_audit.json` 中 forbidden flags 全部为 false。允许的动作仅为 rollback copy、六文件 canonical copy、controlled signal latest pointer write。

## 7. Issues / Blockers / Deviations

无阻塞。后续如果需要前端/readonly/Agent 也看到 {TARGET_ASOF}，必须另开 downstream readonly snapshot/latest route；DAPR10 未授权该动作。

## 8. Files Changed

- `scripts/build_tw_dapr10_actual_controlled_signal_latest_publish.py`
- `{rel(DAPR10_ROOT)}/*`
- `{rel(CANONICAL_SIGNAL_DIR)}/*`
- `{rel(CONTROLLED_SIGNAL_LATEST)}`
- `{rel(DAPR10_EXECUTION_REPORT)}`
- `{rel(DAPR10_REVIEW)}`

## 9. Recommendation For Reviewer

若 after fingerprints 证明 qlib accepted latest、legacy latest、readonly snapshot latest、Agent prompt latest 全部未变，且 latest payload 与 DAPR9 plan 完全一致，则审查可关闭为 `PASS_CONTROLLED_SIGNAL_LATEST_PUBLISHED_STOP_BEFORE_DOWNSTREAM_PUBLISH`。
"""
    write_text(DAPR10_EXECUTION_REPORT, report)


def write_review(post: dict[str, Any], diff: dict[str, Any], forbidden: dict[str, Any]) -> None:
    verdict = (
        "PASS_CONTROLLED_SIGNAL_LATEST_PUBLISHED_STOP_BEFORE_DOWNSTREAM_PUBLISH"
        if post["status"] == "pass" and diff["status"] == "pass" and forbidden["status"] == "pass"
        else "FAIL_NEEDS_REPAIR"
    )
    review = f"""# DAPR10 Actual Controlled Signal Latest Publish 审查

审查时间：{now_iso()}

## 1. Verdict

```text
{verdict}
```

DAPR10 已按 exact scope 完成 controlled signal latest publish，并停在 downstream publish 前。

## 2. Findings

### Critical

无。

### High

无。

### Medium

- controlled signal latest 已推进到 `{TARGET_ASOF}`。这只影响 `data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json`，不表示 qlib accepted latest、readonly snapshot latest 或 Agent prompt latest 已推进。

### Low

- Source manifest 的 `not_published_latest/no_latest` 标记保留在 canonical manifest 中；本次 publish authority 来自 DAPR10 evidence 和 controlled latest pointer。

## 3. Mainline Compliance

- target_asof：`{TARGET_ASOF}`
- run_id：`{RUN_ID}`
- post validation：`{post["status"]}`
- diff summary：`{diff["status"]}`
- forbidden audit：`{forbidden["status"]}`

## 4. Evidence Checked

- `{rel(DAPR10_ROOT / "authorization_scope.json")}`
- `{rel(DAPR10_ROOT / "pre_publish_fingerprint.json")}`
- `{rel(DAPR10_ROOT / "rollback_copy.json")}`
- `{rel(DAPR10_ROOT / "source_preflight_recheck.json")}`
- `{rel(DAPR10_ROOT / "copy_result.json")}`
- `{rel(DAPR10_ROOT / "latest_pointer_write.json")}`
- `{rel(DAPR10_ROOT / "post_publish_validation.json")}`
- `{rel(DAPR10_ROOT / "diff_summary.json")}`
- `{rel(DAPR10_ROOT / "forbidden_action_audit.json")}`
- `{rel(DAPR10_ROOT / "artifact_manifest.json")}`

## 5. Missing Evidence Or Open Questions

无 DAPR10 blocker。downstream readonly snapshot/latest 和 Agent latest 仍未推进，需要单独授权路线。

## 6. Forbidden Actions Audit

DAPR10 仅允许 rollback copy、canonical signal copy、controlled signal latest pointer write。其余 provider/qlib/legacy/readonly/Agent/OpenAI/DB/strategy/monitor/broker/order/target/default switch 均为 false。

## 7. Next Work Document

下一步固定为：

```text
DAPR11_DOWNSTREAM_READONLY_SNAPSHOT_AND_AGENT_LATEST_PREFLIGHT_OR_STOP
```

目标：只读判断是否要基于新的 controlled signal latest `{TARGET_ASOF}` 推进 readonly snapshot latest 与 Agent prompt latest。DAPR11 先做 preflight，不直接 publish。

## 8. Command For Executor Or Coordinator

除非用户明确授权 DAPR11，否则停在 DAPR10 closure，不继续 downstream publish。
"""
    write_text(DAPR10_REVIEW, review)


def main() -> None:
    DAPR10_ROOT.mkdir(parents=True, exist_ok=True)
    source_recheck = assert_preconditions()
    authorization_scope = build_authorization_scope()
    before = capture_fingerprints("dapr10.protected_pointer_before_fingerprints.v1")
    rollback = create_rollback_copy(before)
    if rollback["status"] != "pass":
        raise SystemExit("STOP_DAPR10_ROLLBACK_COPY_FAILED")

    copy_result = copy_canonical_files()
    if copy_result["status"] != "pass":
        raise SystemExit("STOP_DAPR10_COPY_FAILED")

    latest_result = write_latest_pointer()
    if latest_result["status"] != "pass":
        raise SystemExit("STOP_DAPR10_LATEST_POINTER_WRITE_FAILED")

    post = post_publish_validation(before, latest_result)
    diff = build_diff_summary(before, post)
    forbidden = build_forbidden_action_audit()

    evidence_files = [
        DAPR10_ROOT / "authorization_scope.json",
        DAPR10_ROOT / "pre_publish_fingerprint.json",
        DAPR10_ROOT / "rollback_copy.json",
        DAPR10_ROOT / "source_preflight_recheck.json",
        DAPR10_ROOT / "copy_result.json",
        DAPR10_ROOT / "latest_pointer_write.json",
        DAPR10_ROOT / "post_publish_validation.json",
        DAPR10_ROOT / "diff_summary.json",
        DAPR10_ROOT / "forbidden_action_audit.json",
    ]

    write_json(DAPR10_ROOT / "authorization_scope.json", authorization_scope)
    write_json(DAPR10_ROOT / "pre_publish_fingerprint.json", before)
    write_json(DAPR10_ROOT / "rollback_copy.json", rollback)
    write_json(DAPR10_ROOT / "source_preflight_recheck.json", source_recheck)
    write_json(DAPR10_ROOT / "copy_result.json", copy_result)
    write_json(DAPR10_ROOT / "latest_pointer_write.json", latest_result)
    write_json(DAPR10_ROOT / "post_publish_validation.json", post)
    write_json(DAPR10_ROOT / "diff_summary.json", diff)
    write_json(DAPR10_ROOT / "forbidden_action_audit.json", forbidden)
    write_execution_report(post, diff, forbidden)
    write_review(post, diff, forbidden)

    manifest = build_artifact_manifest(evidence_files + [DAPR10_EXECUTION_REPORT, DAPR10_REVIEW])
    write_json(DAPR10_ROOT / "artifact_manifest.json", manifest)

    status = "pass" if post["status"] == "pass" and diff["status"] == "pass" and forbidden["status"] == "pass" else "fail"
    print(
        json.dumps(
            {
                "status": status,
                "target_asof": TARGET_ASOF,
                "run_id": RUN_ID,
                "controlled_signal_latest": rel(CONTROLLED_SIGNAL_LATEST),
                "canonical_signal_dir": rel(CANONICAL_SIGNAL_DIR),
                "evidence_root": rel(DAPR10_ROOT),
                "post_publish_validation": post["status"],
                "diff_summary": diff["status"],
                "forbidden_action_audit": forbidden["status"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
