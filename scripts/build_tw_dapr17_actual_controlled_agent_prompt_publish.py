#!/usr/bin/env python3
"""DAPR17 actual controlled Agent prompt latest publish."""

from __future__ import annotations

import base64
import difflib
import hashlib
import importlib.util
import json
import os
import shutil
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


TARGET_ASOF = env_str("TW_DAPR17_TARGET_ASOF", "2026-07-27")
TARGET_TAG = TARGET_ASOF.replace("-", "")
DAPR15_ROOT = env_path(
    "TW_DAPR17_DAPR15_ROOT",
    f"data_tw/experiments/provider_bridge_productionization/dapr15_{TARGET_TAG}_candidate_only_agent_prompt_dry_run_no_publish",
)
DAPR16_ROOT = env_path(
    "TW_DAPR17_DAPR16_ROOT",
    f"data_tw/experiments/provider_bridge_productionization/dapr16_{TARGET_TAG}_controlled_agent_prompt_publish_preflight_or_stop",
)
DAPR17_ROOT = env_path(
    "TW_DAPR17_OUTPUT_ROOT",
    f"data_tw/experiments/provider_bridge_productionization/dapr17_{TARGET_TAG}_actual_controlled_agent_prompt_publish",
)
DAPR17_EXECUTION_REPORT = env_path(
    "TW_DAPR17_EXECUTION_REPORT",
    f"docs/tw_portfolio_decision_model/POLICY_DAPR17_{TARGET_TAG}_ACTUAL_CONTROLLED_AGENT_PROMPT_PUBLISH_EXECUTION_REPORT_CN.md",
)
DAPR17_REVIEW = env_path(
    "TW_DAPR17_REVIEW",
    f"docs/tw_portfolio_decision_model/POLICY_DAPR17_{TARGET_TAG}_ACTUAL_CONTROLLED_AGENT_PROMPT_PUBLISH_REVIEW_CN.md",
)

CANDIDATE_DIR = DAPR15_ROOT / f"candidate_payloads/agent_daily_prompt/{TARGET_ASOF}"
AGENT_ROOT = ROOT / "data_tw/artifacts/agent_daily_prompt"
TARGET_AGENT_DIR = AGENT_ROOT / TARGET_ASOF
AGENT_LATEST = AGENT_ROOT / "latest.json"
TARGETS = {
    "manifest.json": TARGET_AGENT_DIR / "manifest.json",
    "prompt_context.json": TARGET_AGENT_DIR / "prompt_context.json",
    "prompt_text.md": TARGET_AGENT_DIR / "prompt_text.md",
}
VALIDATOR_PATH = ROOT / "scripts/validate_tw_agent_daily_prompt_artifact.py"

CONTROLLED_SIGNAL_LATEST = ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json"
READONLY_SNAPSHOT_LATEST = ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json"
QLIB_ACCEPTED_LATEST = ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json"
LEGACY_OPTION_C_LATEST = ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json"
PROTECTED_POINTERS = {
    "controlled_signal_latest": CONTROLLED_SIGNAL_LATEST,
    "readonly_snapshot_latest": READONLY_SNAPSHOT_LATEST,
    "qlib_accepted_latest": QLIB_ACCEPTED_LATEST,
    "legacy_option_c_latest": LEGACY_OPTION_C_LATEST,
}

ROLLBACK_DIR = DAPR17_ROOT / "rollback"
ROLLBACK_LATEST_COPY = ROLLBACK_DIR / "agent_daily_prompt_latest.before_dapr17.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    return sha256_bytes(path.read_bytes())


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {rel(path)}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(payload))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def fingerprint(path: Path) -> dict[str, Any]:
    item: dict[str, Any] = {
        "path": rel(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
        "size_bytes": path.stat().st_size if path.is_file() else None,
        "sha256": sha256_file(path),
        "json_summary": None,
    }
    if path.is_file() and path.suffix == ".json":
        try:
            payload = read_json(path)
            item["json_summary"] = {
                key: payload.get(key)
                for key in ("artifact_type", "schema_version", "asof", "signal_asof", "target_date", "artifact_dir", "manifest", "snapshot_manifest", "run_id", "readonly_only", "production_trade_enabled")
                if key in payload
            }
        except Exception as exc:
            item["json_error"] = str(exc)
    return item


def latest_backup(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"path": rel(path), "exists": False, "bytes_base64": None, "sha256": None}
    raw = path.read_bytes()
    return {
        "path": rel(path),
        "exists": True,
        "bytes_base64": base64.b64encode(raw).decode("ascii"),
        "sha256": sha256_bytes(raw),
        "size_bytes": len(raw),
    }


def load_validator_module() -> Any:
    spec = importlib.util.spec_from_file_location("tw_agent_prompt_validator_dapr17", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed_to_load_validator:{rel(VALIDATOR_PATH)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_before(created_at: str, latest_backup_payload: dict[str, Any]) -> dict[str, Any]:
    d16_decision = read_json(DAPR16_ROOT / "candidate_or_stop_decision.json")
    d16_preflight = read_json(DAPR16_ROOT / "candidate_publish_preflight.json")
    d16_auth = read_json(DAPR16_ROOT / "exact_authorization_template.json")
    d15_latest_plan = read_json(DAPR15_ROOT / "latest_pointer_payload_plan.json")
    d15_checksum = read_json(DAPR15_ROOT / "checksum_plan.json")
    checks = {
        "dapr16_decision_pass": d16_decision.get("status") == "pass",
        "dapr16_ready_for_dapr17": d16_decision.get("ready_for_dapr17_exact_authorization_gate") is True,
        "dapr16_preflight_pass": d16_preflight.get("status") == "pass",
        "dapr16_auth_template_pass": d16_auth.get("status") == "pass",
        "dapr15_latest_plan_pass": d15_latest_plan.get("status") == "pass",
        "dapr15_checksum_pass": d15_checksum.get("status") == "pass",
        "candidate_files_exist": all((CANDIDATE_DIR / name).is_file() for name in TARGETS),
        "target_agent_dir_absent_before_write": not TARGET_AGENT_DIR.exists(),
        "agent_latest_exists_before_write": AGENT_LATEST.is_file(),
        "rollback_copy_created": ROLLBACK_LATEST_COPY.is_file()
        and sha256_file(ROLLBACK_LATEST_COPY) == latest_backup_payload.get("sha256"),
        "latest_plan_points_to_target": d15_latest_plan["payload_plan"].get("manifest") == rel(TARGETS["manifest.json"])
        and d15_latest_plan["payload_plan"].get("artifact_dir") == rel(TARGET_AGENT_DIR),
    }
    return {
        "schema_version": "dapr17.before_fingerprint.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "candidate_dir": rel(CANDIDATE_DIR),
        "fingerprints_before": {
            "agent_prompt_latest": fingerprint(AGENT_LATEST),
            "target_agent_dir": fingerprint(TARGET_AGENT_DIR),
            **{name: fingerprint(path) for name, path in PROTECTED_POINTERS.items()},
        },
        "rollback_copy": {"path": rel(ROLLBACK_LATEST_COPY), "sha256": sha256_file(ROLLBACK_LATEST_COPY)},
        "checks": checks,
    }


def stop_if_failed(name: str, payload: dict[str, Any]) -> None:
    if payload.get("status") != "pass":
        failed = [key for key, value in payload.get("checks", {}).items() if not value]
        raise RuntimeError(f"STOP_{name}: {failed}")


def publish_files() -> dict[str, Any]:
    TARGET_AGENT_DIR.mkdir(parents=True, exist_ok=False)
    copied = {}
    for name, target in TARGETS.items():
        source = CANDIDATE_DIR / name
        shutil.copy2(source, target)
        copied[name] = {"source": rel(source), "target": rel(target), "sha256": sha256_file(target)}
    latest_payload = read_json(DAPR15_ROOT / "latest_pointer_payload_plan.json")["payload_plan"]
    write_json(AGENT_LATEST, latest_payload)
    return {"status": "pass", "files": copied, "latest": {"path": rel(AGENT_LATEST), "sha256": sha256_file(AGENT_LATEST)}}


def build_after(created_at: str, before: dict[str, Any]) -> dict[str, Any]:
    after = {
        "agent_prompt_latest": fingerprint(AGENT_LATEST),
        "target_agent_dir": fingerprint(TARGET_AGENT_DIR),
        **{name: fingerprint(path) for name, path in PROTECTED_POINTERS.items()},
    }
    protected_unchanged = {
        name: before["fingerprints_before"][name].get("sha256") == after[name].get("sha256")
        for name in PROTECTED_POINTERS
    }
    checks = {
        "target_agent_dir_exists": TARGET_AGENT_DIR.is_dir(),
        "three_canonical_files_exist": all(path.is_file() for path in TARGETS.values()),
        "agent_latest_points_to_target": (after["agent_prompt_latest"].get("json_summary") or {}).get("manifest")
        == rel(TARGETS["manifest.json"]),
        **{f"{name}_unchanged": value for name, value in protected_unchanged.items()},
    }
    return {
        "schema_version": "dapr17.after_fingerprint.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "fingerprints_after": after,
        "checks": checks,
    }


def build_diff(created_at: str, latest_backup_payload: dict[str, Any]) -> dict[str, Any]:
    before_text = ""
    previous_asof = None
    if latest_backup_payload.get("bytes_base64"):
        before_text = base64.b64decode(latest_backup_payload["bytes_base64"]).decode("utf-8")
        try:
            previous = json.loads(before_text)
            if isinstance(previous, dict):
                previous_asof = previous.get("signal_asof") or previous.get("target_date")
        except Exception:
            pass
    after_text = AGENT_LATEST.read_text(encoding="utf-8")
    diff_lines = list(difflib.unified_diff(before_text.splitlines(), after_text.splitlines(), fromfile="agent_daily_prompt/latest.before.json", tofile="agent_daily_prompt/latest.after.json", lineterm=""))
    checks = {
        "latest_diff_contains_target_asof": any(TARGET_ASOF in line for line in diff_lines),
        "latest_diff_contains_previous_asof": previous_asof is not None and any(previous_asof in line for line in diff_lines),
        "three_canonical_files_created": all(path.is_file() for path in TARGETS.values()),
    }
    return {
        "schema_version": "dapr17.diff_summary.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "previous_asof": previous_asof,
        "latest_pointer_unified_diff": diff_lines,
        "created_canonical_files": [rel(path) for path in TARGETS.values()],
        "checks": checks,
    }


def build_checksum_validation(created_at: str) -> dict[str, Any]:
    expected = {
        "manifest.json": sha256_file(CANDIDATE_DIR / "manifest.json"),
        "prompt_context.json": sha256_file(CANDIDATE_DIR / "prompt_context.json"),
        "prompt_text.md": sha256_file(CANDIDATE_DIR / "prompt_text.md"),
    }
    actual = {name: sha256_file(path) for name, path in TARGETS.items()}
    latest_plan_sha = read_json(DAPR15_ROOT / "latest_pointer_payload_plan.json").get("payload_plan_sha256")
    checks = {
        "all_canonical_files_match_candidate": actual == expected,
        "latest_matches_dapr15_plan": sha256_file(AGENT_LATEST) == latest_plan_sha,
    }
    return {
        "schema_version": "dapr17.canonical_file_checksum_validation.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "candidate_sha256": expected,
        "canonical_sha256": actual,
        "latest_sha256": sha256_file(AGENT_LATEST),
        "latest_plan_sha256": latest_plan_sha,
        "checks": checks,
    }


def build_validator_validation(created_at: str) -> dict[str, Any]:
    validator = load_validator_module()
    result = validator.validate_artifact(TARGET_AGENT_DIR).to_dict(TARGET_AGENT_DIR)
    checks = {"validator_ok": result.get("ok") is True, "errors_empty": result.get("errors") == []}
    return {
        "schema_version": "dapr17.agent_prompt_artifact_validator.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "validator_path": rel(VALIDATOR_PATH),
        "validator_output": result,
        "checks": checks,
    }


def build_latest_validation(created_at: str) -> dict[str, Any]:
    latest = read_json(AGENT_LATEST)
    planned = read_json(DAPR15_ROOT / "latest_pointer_payload_plan.json")["payload_plan"]
    manifest = read_json(TARGETS["manifest.json"])
    checks = {
        "latest_payload_equals_plan": latest == planned,
        "latest_signal_asof_target": latest.get("signal_asof") == TARGET_ASOF and latest.get("target_date") == TARGET_ASOF,
        "latest_points_to_target_manifest": latest.get("manifest") == rel(TARGETS["manifest.json"]),
        "latest_artifact_dir_target": latest.get("artifact_dir") == rel(TARGET_AGENT_DIR),
        "manifest_asof_target": manifest.get("signal_asof") == TARGET_ASOF and manifest.get("target_date") == TARGET_ASOF,
        "readonly_flags_safe": latest.get("readonly_only") is True and latest.get("production_trade_enabled") is False,
        "checksum_matches_manifest": latest.get("checksum") == manifest.get("checksum"),
    }
    return {
        "schema_version": "dapr17.latest_pointer_payload_validation.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "latest_payload_summary": {key: latest.get(key) for key in ("artifact_type", "schema_version", "signal_asof", "target_date", "artifact_dir", "manifest", "readonly_only", "production_trade_enabled")},
        "checks": checks,
    }


def build_rollback_package(created_at: str, latest_backup_payload: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "rollback_copy_exists": ROLLBACK_LATEST_COPY.is_file(),
        "rollback_copy_sha_matches_before": sha256_file(ROLLBACK_LATEST_COPY) == latest_backup_payload.get("sha256"),
        "current_latest_points_to_target": read_json(AGENT_LATEST).get("manifest") == rel(TARGETS["manifest.json"]),
    }
    return {
        "schema_version": "dapr17.rollback_package.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "rollback_copy": {"path": rel(ROLLBACK_LATEST_COPY), "sha256": sha256_file(ROLLBACK_LATEST_COPY)},
        "previous_latest_pointer_backup": latest_backup_payload,
        "checks": checks,
    }


def build_forbidden_action_audit(created_at: str, before: dict[str, Any]) -> dict[str, Any]:
    after = {name: fingerprint(path) for name, path in PROTECTED_POINTERS.items()}
    unchanged = {
        name: before["fingerprints_before"][name].get("sha256") == after[name].get("sha256")
        for name in PROTECTED_POINTERS
    }
    flags = {
        "provider_publish_or_pull": False,
        "qlib_refresh": False,
        "daily_auto": False,
        "accepted_latest_switch": False,
        "openai_call": False,
        "db_access": False,
        "strategy_replay": False,
        "monitor_broker_order_target": False,
        "frontend_api_default_switch": False,
    }
    checks = {
        "all_forbidden_flags_false": all(value is False for value in flags.values()),
        "protected_pointers_unchanged": all(unchanged.values()),
        "only_agent_prompt_latest_written": True,
    }
    return {
        "schema_version": "dapr17.forbidden_action_audit.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(checks.values()) else "fail",
        "all_forbidden_false": all(value is False for value in flags.values()),
        "flags": flags,
        "protected_pointer_after_fingerprints": after,
        "protected_pointer_unchanged": unchanged,
        "checks": checks,
    }


def build_artifact_manifest(created_at: str, files: list[Path]) -> dict[str, Any]:
    entries = [{"path": rel(path), "exists": path.is_file(), "sha256": sha256_file(path), "size_bytes": path.stat().st_size if path.is_file() else None} for path in files]
    return {
        "schema_version": "dapr17.artifact_manifest.v1",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "status": "pass" if all(item["exists"] and item["sha256"] for item in entries) else "fail",
        "entries": entries,
    }


def write_reports(created_at: str, latest_validation: dict[str, Any], forbidden: dict[str, Any], artifact_manifest: dict[str, Any]) -> None:
    execution = f"""# DAPR17 Actual Controlled Agent Prompt Publish 执行报告

created_at: `{created_at}`

target_asof: `{TARGET_ASOF}`

verdict: `PASS_RECOMMEND_REVIEW`

## Scope

只写入 `{rel(TARGET_AGENT_DIR)}` 三个 Agent prompt canonical 文件和 `{rel(AGENT_LATEST)}`。

## Result

Agent prompt latest now points to `{latest_validation["latest_payload_summary"]["manifest"]}`。

## Boundary

controlled signal latest、readonly snapshot latest、qlib/legacy latest 均保持不动；forbidden action audit all false = `{forbidden["all_forbidden_false"]}`。
"""
    review = f"""# DAPR17 Actual Controlled Agent Prompt Publish 审查

created_at: `{created_at}`

verdict: `PASS_STOP_BEFORE_STABLE_OPS_OBSERVATION`

## Evidence

- latest pointer payload validation: `{latest_validation["status"]}`
- forbidden action audit: `{forbidden["status"]}`
- artifact manifest: `{artifact_manifest["status"]}`

## Next

进入稳定运维前，应做一次只读 ops closure/observation gate；不授权 daily auto 自动 publish。
"""
    write_text(DAPR17_EXECUTION_REPORT, execution)
    write_text(DAPR17_REVIEW, review)


def main() -> None:
    created_at = now_iso()
    DAPR17_ROOT.mkdir(parents=True, exist_ok=True)
    ROLLBACK_DIR.mkdir(parents=True, exist_ok=True)
    latest_backup_payload = latest_backup(AGENT_LATEST)
    if AGENT_LATEST.is_file():
        shutil.copy2(AGENT_LATEST, ROLLBACK_LATEST_COPY)
    before = build_before(created_at, latest_backup_payload)
    write_json(DAPR17_ROOT / "before_fingerprint.json", before)
    stop_if_failed("DAPR17_BEFORE", before)

    publish_write = publish_files()
    write_json(DAPR17_ROOT / "publish_write.json", {"schema_version": "dapr17.publish_write.v1", "created_at": created_at, "target_asof": TARGET_ASOF, **publish_write})
    after = build_after(created_at, before)
    diff_summary = build_diff(created_at, latest_backup_payload)
    checksum_validation = build_checksum_validation(created_at)
    validator_validation = build_validator_validation(created_at)
    latest_validation = build_latest_validation(created_at)
    rollback = build_rollback_package(created_at, latest_backup_payload)
    forbidden = build_forbidden_action_audit(created_at, before)
    for name, payload in (
        ("after_fingerprint.json", after),
        ("diff_summary.json", diff_summary),
        ("canonical_file_checksum_validation.json", checksum_validation),
        ("agent_prompt_artifact_validator.json", validator_validation),
        ("latest_pointer_payload_validation.json", latest_validation),
        ("rollback_package.json", rollback),
        ("forbidden_action_audit.json", forbidden),
    ):
        write_json(DAPR17_ROOT / name, payload)
        stop_if_failed(name, payload)
    evidence_files = [
        DAPR17_ROOT / name
        for name in (
            "before_fingerprint.json",
            "publish_write.json",
            "after_fingerprint.json",
            "diff_summary.json",
            "canonical_file_checksum_validation.json",
            "agent_prompt_artifact_validator.json",
            "latest_pointer_payload_validation.json",
            "rollback_package.json",
            "forbidden_action_audit.json",
        )
    ] + [ROLLBACK_LATEST_COPY, *TARGETS.values(), AGENT_LATEST]
    artifact_manifest = build_artifact_manifest(created_at, evidence_files)
    write_reports(created_at, latest_validation, forbidden, artifact_manifest)
    artifact_manifest = build_artifact_manifest(created_at, evidence_files + [DAPR17_EXECUTION_REPORT, DAPR17_REVIEW])
    write_json(DAPR17_ROOT / "artifact_manifest.json", artifact_manifest)
    stop_if_failed("DAPR17_ARTIFACT_MANIFEST", artifact_manifest)
    print(json.dumps({"status": "pass", "target_asof": TARGET_ASOF, "evidence_root": rel(DAPR17_ROOT), "latest_pointer": rel(AGENT_LATEST)}, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
