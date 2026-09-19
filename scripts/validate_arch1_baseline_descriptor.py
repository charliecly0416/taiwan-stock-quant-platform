#!/usr/bin/env python3
"""Offline ARCH-1 descriptor and runtime-truth convergence validator."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DESCRIPTOR = ROOT / "configs/active_baseline_descriptor.yaml"
DEFAULT_INVENTORY = ROOT / "data_tw/experiments/project_runtime_convergence/arch0_runtime_truth_inventory_20260907/ARCH0_RUNTIME_TRUTH_INVENTORY.json"
DEFAULT_ANNEX = ROOT / "data_tw/experiments/project_runtime_convergence/arch1_baseline_descriptor_20260907/ARCH1_RUNTIME_TRUTH_ANNEX.json"
DEFAULT_SCHEMA = ROOT / "schemas/active_baseline_descriptor.schema.json"
DRIFT_PROVENANCE = ROOT / "data_tw/experiments/project_runtime_convergence/candidate_binding_20260907/protected_drift_audit_20260907/protected_drift_audit_20260907.json"
DAPR10_EVIDENCE_ROOT = ROOT / "data_tw/ops/daily_auto_update"

MODEL_A = "e4_frozen_qlib_2018_2022"
MODEL_B = "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025"
FALLBACK_PROTECTED = {
    "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json": "624f0c16a1f7cf0f0b833938bd6b09d4dbdd163198755a79ccac796d944fe07a",
    "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json": "99ed52c869d658f83357344127fab43bca850b039b1c85f55b1f0078d93c18cb",
    "data_tw/artifacts/agent_daily_prompt/latest.json": "4c648ef5012255a93d6b54eae9361502c773e00bfa83d1e3ba30271e14030a43",
    "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json": "6b57a703c8cd0c7ee923e03d256d5ce2e4446cd56db517583bb3b15d34606291",
    "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt": "05d9b49c8afe50d7e1e70da1d34a3f117c949c9b5e018fddf1f03336c9b30b7c",
    "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt": "cde8fa6444149b0482fc7363b25000d25b844e6ff5dcf703d43cb9cdbb6f41d5",
    "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron": "2b371e283da1512810411b7c461e83563b445826cbc342adf016364fb8d6a15e",
}


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def result(name: str, ok: bool, details: str = "") -> dict[str, Any]:
    return {"name": name, "status": "pass" if ok else "fail", "details": details}


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def resolve_from(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def is_exact_safe_path(value: Any, expected: Path, *, root: Path) -> bool:
    raw = str(value or "")
    if not raw or ".." in Path(raw).parts:
        return False
    try:
        return resolve_from(root, raw).resolve() == expected.resolve()
    except OSError:
        return False


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return False
    return True


def valid_iso_date(value: Any) -> bool:
    try:
        date.fromisoformat(str(value))
    except ValueError:
        return False
    return True


def available_at_on_or_before_signal_asof(value: Any, signal_asof: str) -> bool:
    raw = str(value or "")
    try:
        available_date = date.fromisoformat(raw[:10])
        signal_date = date.fromisoformat(signal_asof)
    except ValueError:
        return False
    return available_date <= signal_date


def dapr10_evidence_directories(evidence_root: Path) -> list[Path]:
    candidates: list[Path] = []
    if not evidence_root.exists():
        return candidates
    for job_dir in evidence_root.iterdir():
        if not job_dir.is_dir():
            continue
        direct = job_dir / "dapr18p1_signal_only_dapr10"
        if direct.is_dir():
            candidates.append(direct)
        chain = job_dir / "dapr18p1_controlled_auto_publish_chain"
        if chain.is_dir():
            candidates.extend(path for path in chain.glob("dapr10_*") if path.is_dir())
    return sorted(candidates, reverse=True)


def validate_dapr10_publish_evidence(
    *,
    run_id: str,
    asof: str,
    latest: dict[str, Any],
    latest_path: Path,
    manifest_path: Path,
    signals_path: Path,
    runtime_root: Path,
    evidence_root: Path,
) -> dict[str, Any]:
    try:
        latest_relative = str(latest_path.resolve().relative_to(runtime_root.resolve()))
        manifest_relative = str(manifest_path.resolve().relative_to(runtime_root.resolve()))
        signals_relative = str(signals_path.resolve().relative_to(runtime_root.resolve()))
    except (OSError, ValueError):
        return {"ok": False, "path": "", "checks": {"runtime_path_scope": False}, "attempts": []}
    latest_digest = sha256(latest_path) if latest_path.is_file() else ""
    manifest_digest = sha256(manifest_path) if manifest_path.is_file() else ""
    signals_digest = sha256(signals_path) if signals_path.is_file() else ""
    attempts: list[dict[str, Any]] = []

    for directory in dapr10_evidence_directories(evidence_root):
        auth = read_json(directory / "authorization_scope.json")
        preflight = read_json(directory / "source_preflight_recheck.json")
        post = read_json(directory / "post_publish_validation.json")
        diff = read_json(directory / "diff_summary.json")
        rollback = read_json(directory / "rollback_copy.json")
        pointer_write = read_json(directory / "latest_pointer_write.json")
        forbidden = read_json(directory / "forbidden_action_audit.json")

        identity_payloads = (auth, preflight, post, pointer_write)
        identity_ok = all(
            payload.get("status") == "pass"
            and payload.get("target_asof") == asof
            and payload.get("run_id") == run_id
            for payload in identity_payloads
        )
        authorization_ok = auth.get("authorized_by_user_exact_text") is True
        allowed_paths = {str(item) for item in auth.get("allowed_write_paths", [])}
        authorization_scope_ok = {latest_relative, manifest_relative, signals_relative} <= allowed_paths

        preflight_checks = preflight.get("checks") if isinstance(preflight.get("checks"), dict) else {}
        preflight_ok = bool(preflight_checks) and all(value is True for value in preflight_checks.values())

        post_checks = post.get("checks") if isinstance(post.get("checks"), dict) else {}
        required_post_checks = {
            "latest_manifest_sha_matches",
            "latest_payload_matches_dapr9_plan",
            "latest_readonly_and_no_publish_flags_safe",
            "latest_references_canonical_manifest",
            "latest_references_canonical_signals",
            "latest_signals_sha_matches",
            "manifest_artifact_type_model_signal",
            "manifest_production_allowed_false",
            "manifest_signal_asof_target",
            "manifest_status_ready",
            "source_validator_pass",
        }
        post_files = {
            str(item.get("file")): item
            for item in post.get("canonical_file_checks", [])
            if isinstance(item, dict)
        }
        post_ok = (
            required_post_checks <= set(post_checks)
            and bool(post_checks)
            and all(value is True for value in post_checks.values())
            and all(post_checks.get(name) is True for name in required_post_checks)
            and (post.get("latest_pointer_summary") or {}).get("sha256") == latest_digest
            and (post_files.get("manifest.json") or {}).get("actual_sha256") == manifest_digest
            and (post_files.get("manifest.json") or {}).get("checksum_match") is True
            and (post_files.get("signals.csv") or {}).get("actual_sha256") == signals_digest
            and (post_files.get("signals.csv") or {}).get("checksum_match") is True
        )

        pointer_changes = diff.get("pointer_changes") if isinstance(diff.get("pointer_changes"), list) else []
        pointer_change = next(
            (
                item for item in pointer_changes
                if isinstance(item, dict) and item.get("path") == latest_relative
            ),
            {},
        )
        diff_checks = diff.get("checks") if isinstance(diff.get("checks"), dict) else {}
        transition_ok = (
            diff.get("status") == "pass"
            and diff.get("target_asof") == asof
            and bool(diff_checks)
            and all(value is True for value in diff_checks.values())
            and pointer_change.get("changed") is True
            and pointer_change.get("before_sha256") != pointer_change.get("after_sha256")
            and pointer_change.get("after_sha256") == latest_digest
            and (pointer_change.get("after_summary") or {}).get("run_id") == run_id
            and (pointer_change.get("after_summary") or {}).get("signal_asof") == asof
            and valid_iso_date((pointer_change.get("before_summary") or {}).get("signal_asof"))
            and date.fromisoformat((pointer_change.get("before_summary") or {}).get("signal_asof")) <= date.fromisoformat(asof)
        )

        rollback_path = resolve_from(runtime_root, str(rollback.get("rollback_copy") or ""))
        rollback_checks = rollback.get("checks") if isinstance(rollback.get("checks"), dict) else {}
        rollback_ok = (
            rollback.get("status") == "pass"
            and rollback.get("target_asof") == asof
            and bool(rollback_checks)
            and all(value is True for value in rollback_checks.values())
            and is_within(rollback_path, directory / "rollback")
            and rollback_path.is_file()
            and sha256(rollback_path) == rollback.get("rollback_copy_sha256")
            and rollback.get("rollback_copy_sha256") == rollback.get("before_latest_sha256")
            and rollback.get("before_latest_sha256") == pointer_change.get("before_sha256")
            and rollback.get("source_latest") == latest_relative
        )

        pointer_write_ok = (
            pointer_write.get("latest_pointer_path") == latest_relative
            and pointer_write.get("sha256") == latest_digest
            and pointer_write.get("observed_payload") == latest
            and pointer_write.get("payload_matches_dapr9_plan") is True
        )
        forbidden_flags = forbidden.get("forbidden_flags") if isinstance(forbidden.get("forbidden_flags"), dict) else {}
        forbidden_ok = (
            forbidden.get("status") == "pass"
            and forbidden.get("target_asof") == asof
            and forbidden.get("all_forbidden_false") is True
            and bool(forbidden_flags)
            and not any(bool(value) for value in forbidden_flags.values())
        )
        checks = {
            "identity": identity_ok,
            "authorization": authorization_ok,
            "authorization_scope": authorization_scope_ok,
            "preflight": preflight_ok,
            "post_publish_validation": post_ok,
            "pointer_transition": transition_ok,
            "rollback": rollback_ok,
            "pointer_write": pointer_write_ok,
            "forbidden_actions": forbidden_ok,
        }
        attempts.append({"path": str(directory), "checks": checks})
        if all(checks.values()):
            return {"ok": True, "path": str(directory), "checks": checks, "attempts": attempts}
    return {"ok": False, "path": "", "checks": {}, "attempts": attempts}


def validate_active_latest(
    *,
    descriptor: dict[str, Any],
    inventory: dict[str, Any],
    runtime_root: Path = ROOT,
    evidence_root: Path | None = None,
) -> list[dict[str, Any]]:
    active = descriptor.get("active_baseline") if isinstance(descriptor.get("active_baseline"), dict) else {}
    model_a = active.get("model_a") if isinstance(active.get("model_a"), dict) else {}
    model_id = str(model_a.get("model_id") or "")
    allowed_root = runtime_root / "data_tw/artifacts/signals" / model_id
    signals_root = runtime_root / "data_tw/artifacts/signals"
    expected_latest_path = allowed_root / "latest.json"
    latest_value = model_a.get("latest_pointer", "")
    latest_path = resolve_from(runtime_root, str(latest_value or ""))
    latest = read_json(latest_path) if latest_path.is_file() else {}
    run_id = str(latest.get("run_id") or "")
    asof = str(latest.get("asof") or "")
    signal_asof = str(latest.get("signal_asof") or "")
    expected_artifact_dir = allowed_root / run_id
    manifest_path = resolve_from(runtime_root, str(latest.get("canonical_manifest") or ""))
    signals_path = resolve_from(runtime_root, str(latest.get("canonical_signals") or ""))
    manifest = read_json(manifest_path) if manifest_path.is_file() else {}

    checks: list[dict[str, Any]] = []
    checks.append(result(
        "active_latest_pointer_path",
        is_exact_safe_path(latest_value, expected_latest_path, root=runtime_root)
        and is_within(allowed_root, signals_root)
        and is_within(latest_path, allowed_root),
    ))
    paths_ok = bool(run_id) and all(
        (
            is_exact_safe_path(latest.get("canonical_artifact_dir"), expected_artifact_dir, root=runtime_root),
            is_exact_safe_path(latest.get("source_artifact_dir"), expected_artifact_dir, root=runtime_root),
            is_exact_safe_path(latest.get("canonical_manifest"), expected_artifact_dir / "manifest.json", root=runtime_root),
            is_exact_safe_path(latest.get("canonical_signals"), expected_artifact_dir / "signals.csv", root=runtime_root),
            is_within(expected_artifact_dir, allowed_root),
            is_within(manifest_path, allowed_root),
            is_within(signals_path, allowed_root),
        )
    )
    checks.append(result("active_latest_canonical_paths", paths_ok))
    checks.append(result("active_latest_model_identity", latest.get("model_id") == MODEL_A and latest.get("model_name") == MODEL_A and model_id == MODEL_A))
    pointer_contract_ok = (
        latest.get("artifact_type") == "controlled_model_signal_latest_pointer"
        and latest.get("schema_version") == "clpr.controlled_signal_latest_pointer.v1"
        and latest.get("created_by_planned_phase") == "DAPR10_ACTUAL_CONTROLLED_SIGNAL_LATEST_PUBLISH"
    )
    checks.append(result("active_latest_pointer_contract", pointer_contract_ok))
    date_run_ok = bool(run_id) and valid_iso_date(asof) and asof == signal_asof
    checks.append(result("active_latest_date_run_coherence", date_run_ok, f"asof={asof};signal_asof={signal_asof};run_id={run_id}"))

    manifest_digest = sha256(manifest_path) if manifest_path.is_file() else ""
    signals_digest = sha256(signals_path) if signals_path.is_file() else ""
    digest_ok = bool(manifest_digest and signals_digest) and all(
        (
            latest.get("canonical_manifest_sha256") == manifest_digest,
            latest.get("canonical_signals_sha256") == signals_digest,
            latest.get("source_manifest_sha256", manifest_digest) == manifest_digest,
            latest.get("source_signals_sha256", signals_digest) == signals_digest,
        )
    )
    checks.append(result("active_latest_file_integrity", digest_ok, f"manifest={manifest_digest};signals={signals_digest}"))

    files = manifest.get("files") if isinstance(manifest.get("files"), dict) else {}
    manifest_forbidden = manifest.get("forbidden_actions") if isinstance(manifest.get("forbidden_actions"), dict) else {}
    governance_forbidden = manifest.get("governance_forbidden_actions") if isinstance(manifest.get("governance_forbidden_actions"), dict) else {}
    manifest_ok = all(
        (
            manifest.get("artifact_type") == "ModelSignalArtifact",
            manifest.get("model_id") == MODEL_A,
            manifest.get("model_name") == MODEL_A,
            manifest.get("asof") == asof,
            manifest.get("signal_asof") == signal_asof,
            manifest.get("run_id") == run_id,
            files.get("manifest") == "manifest.json",
            files.get("signals") == "signals.csv",
            manifest.get("status") == "READY",
            int(manifest.get("row_count") or 0) > 0,
            manifest.get("production_allowed") is False,
            bool(manifest_forbidden) and not any(bool(value) for value in manifest_forbidden.values()),
            not governance_forbidden or not any(bool(value) for value in governance_forbidden.values()),
        )
    )
    checks.append(result("active_latest_manifest_contract", manifest_ok))

    signal_rows: list[dict[str, str]] = []
    if signals_path.is_file():
        try:
            with signals_path.open(newline="", encoding="utf-8") as handle:
                signal_rows = list(csv.DictReader(handle))
        except OSError:
            signal_rows = []
    manifest_available_at = str(manifest.get("available_at") or "")
    available_at_policy = str(manifest.get("available_at_policy") or "")
    row_available_at_values = {str(row.get("available_at") or "") for row in signal_rows}
    availability_ok = bool(row_available_at_values) and "" not in row_available_at_values
    if manifest_available_at:
        availability_ok = availability_ok and row_available_at_values == {manifest_available_at}
    else:
        availability_ok = (
            availability_ok
            and bool(available_at_policy)
            and all(available_at_on_or_before_signal_asof(value, signal_asof) for value in row_available_at_values)
        )
    signals_ok = bool(signal_rows) and len(signal_rows) == int(manifest.get("row_count") or 0) and all(
        row.get("date") == asof
        and row.get("signal_asof") == signal_asof
        and row.get("model_name") == MODEL_A
        for row in signal_rows
    ) and availability_ok
    checks.append(result("active_latest_signals_contract", signals_ok, f"rows={len(signal_rows)}"))

    pointer_safety_ok = (
        latest.get("readonly_only") is True
        and latest.get("production_trade_enabled") is False
        and all(
            latest.get(field) is False
            for field in (
                "provider_publish",
                "provider_accepted_latest_switch",
                "qlib_accepted_latest_switch",
                "legacy_option_c_latest_signal_switch",
                "frontend_default_switch",
                "agent_prompt_publish",
            )
        )
    )
    checks.append(result("active_latest_readonly_safety", pointer_safety_ok))

    anchor = (inventory.get("active_baseline") or {}).get("signal_latest") or {}
    anchor_asof = str(anchor.get("signal_asof") or anchor.get("asof") or "")
    anchor_hashes = (
        str(anchor.get("canonical_manifest_sha256") or ""),
        str(anchor.get("canonical_signals_sha256") or ""),
        str(anchor.get("pointer_sha256") or ""),
    )
    # ARCH-0 is a point-in-time inventory, not a permanent 2026-09-04
    # constant. Validate its structural contract, then use the recorded
    # anchor date/run/checksums for monotonic and authorized-forward checks.
    anchor_identity_ok = (
        inventory.get("active_baseline", {}).get("model_id") == MODEL_A
        and inventory.get("active_baseline", {}).get("status") == "MODEL_A_ONLY"
        and inventory.get("active_baseline", {}).get("strategy_rule") == "top50_exit_one_worst_sell"
        and inventory.get("active_baseline", {}).get("execution_price_mode") == "next_open"
        and anchor.get("path") == str(latest_path.relative_to(runtime_root))
        and anchor.get("model_id") == MODEL_A
        and bool(anchor.get("run_id"))
        and valid_iso_date(anchor.get("asof"))
        and anchor.get("asof") == anchor.get("signal_asof")
        and all(len(value) == 64 and all(char in "0123456789abcdef" for char in value.lower()) for value in anchor_hashes)
    )
    anchor_same_date_match = (
        signal_asof != anchor_asof
        or (
            run_id == anchor.get("run_id")
            and manifest_digest == anchor.get("canonical_manifest_sha256")
            and signals_digest == anchor.get("canonical_signals_sha256")
            and sha256(latest_path) == anchor.get("pointer_sha256")
        )
    )
    anchor_identity_ok = anchor_identity_ok and anchor_same_date_match
    checks.append(result("active_latest_arch0_anchor_integrity", anchor_identity_ok))
    monotonic_ok = anchor_identity_ok and date_run_ok and date.fromisoformat(signal_asof) >= date.fromisoformat(anchor_asof)
    checks.append(result("active_latest_arch0_monotonic_anchor", monotonic_ok, f"anchor={anchor_asof};current={signal_asof}"))

    if monotonic_ok:
        provenance = validate_dapr10_publish_evidence(
            run_id=run_id,
            asof=signal_asof,
            latest=latest,
            latest_path=latest_path,
            manifest_path=manifest_path,
            signals_path=signals_path,
            runtime_root=runtime_root,
            evidence_root=evidence_root or (runtime_root / "data_tw/ops/daily_auto_update"),
        )
        # A non-DAPR10 historical pointer may be accepted from an immutable
        # ARCH-0 anchor, but a controlled DAPR10 pointer always requires its
        # authorization/preflight/post-publish/rollback evidence.
        if (
            not provenance.get("ok")
            and signal_asof == anchor_asof
            and latest.get("created_by_planned_phase") != "DAPR10_ACTUAL_CONTROLLED_SIGNAL_LATEST_PUBLISH"
        ):
            anchor_match = (
                run_id == anchor.get("run_id")
                and manifest_digest == anchor.get("canonical_manifest_sha256")
                and signals_digest == anchor.get("canonical_signals_sha256")
                and sha256(latest_path) == anchor.get("pointer_sha256")
            )
            provenance = {"ok": anchor_match, "path": "ARCH0_RUNTIME_TRUTH_INVENTORY", "checks": {"immutable_anchor_match": anchor_match}}
    else:
        provenance = {"ok": False, "path": "", "checks": {}}
    checks.append(result("active_latest_authorized_provenance", bool(provenance.get("ok")), json.dumps(provenance, sort_keys=True)))
    return checks


def scan_normalized() -> dict[str, Any]:
    directory = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"
    files = sorted(directory.glob("TW*.csv"))
    minimum = maximum = None
    for path in files:
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                value = str(row.get("date", ""))
                if value and (minimum is None or value < minimum):
                    minimum = value
                if value and (maximum is None or value > maximum):
                    maximum = value
    return {"directory": str(directory.relative_to(ROOT)), "file_count": len(files), "min_tail": minimum, "max_tail": maximum, "scan_method": "full_directory_all_csv_rows"}


def expected_job_paths() -> list[Path]:
    return sorted((ROOT / "data_tw/ops/daily_auto_update").glob("*/job.json"))[-20:]


def descriptor_protected_paths(descriptor: dict[str, Any]) -> dict[str, str]:
    """Read protected fingerprints from the descriptor; fallback is only for legacy fixtures."""
    configured = descriptor.get("protected_latest_paths")
    if isinstance(configured, dict) and configured:
        return {str(path): str(digest) for path, digest in configured.items()}
    return dict(FALLBACK_PROTECTED)


def protected_drift_paths(field: str) -> dict[str, str]:
    """Load one complete fingerprint mapping from the authorized drift audit."""
    if not DRIFT_PROVENANCE.exists():
        return {}
    try:
        payload = json.loads(DRIFT_PROVENANCE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {
        str(item.get("path")): str(item.get(field))
        for item in payload.get("protected_paths", [])
        if item.get("path") and item.get(field)
    }


def historical_protected_paths() -> dict[str, str]:
    """Load the preserved pre-rebaseline hashes, when provenance exists."""
    return protected_drift_paths("expected_sha256")


def authorized_rebaseline_protected_paths() -> dict[str, str]:
    """Load the descriptor hashes approved by the protected-drift rebaseline."""
    return protected_drift_paths("current_sha256")


def validate(descriptor_path: Path, inventory_path: Path, annex_path: Path, schema_path: Path = DEFAULT_SCHEMA) -> dict[str, Any]:
    descriptor = yaml.safe_load(descriptor_path.read_text(encoding="utf-8"))
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    annex = json.loads(annex_path.read_text(encoding="utf-8")) if annex_path.exists() else {}
    checks: list[dict[str, Any]] = []
    schema = json.loads(schema_path.read_text(encoding="utf-8")) if schema_path.exists() else {}
    schema_errors = list(Draft202012Validator(schema).iter_errors(descriptor)) if schema else ["schema_missing"]
    checks.append(result("json_schema_invocation", not schema_errors, "; ".join(error.message if hasattr(error, "message") else str(error) for error in schema_errors[:3])))
    active = descriptor.get("active_baseline", {})
    protected_expected = descriptor_protected_paths(descriptor)
    checks.append(result("descriptor_schema_version", descriptor.get("schema_version") == "arch1.active_baseline_descriptor.v1"))
    checks.append(result("descriptor_authority", descriptor.get("authority") == "canonical_runtime_baseline"))
    checks.append(result("readonly_simulation_boundary", descriptor.get("readonly_only") is True and descriptor.get("simulation_only") is True))
    checks.append(result("active_model_a_only", active.get("status") == "MODEL_A_ONLY" and active.get("model_a", {}).get("model_id") == MODEL_A and active.get("model_b") is None))
    checks.append(result("active_strategy_execution", active.get("strategy_rule") == "top50_exit_one_worst_sell" and active.get("execution_price_mode") == "next_open"))
    model_a = active.get("model_a", {})
    model_a_path = resolve(model_a.get("artifact_path", ""))
    checks.append(result("model_a_artifact_hash", model_a_path.exists() and sha256(model_a_path) == model_a.get("artifact_sha256", ""), str(model_a_path)))

    checks.extend(validate_active_latest(descriptor=descriptor, inventory=inventory))

    shadows = descriptor.get("shadow_models", [])
    shadow = next((item for item in shadows if item.get("canonical_id") == MODEL_B), None)
    checks.append(result("canonical_model_b_identity", shadow is not None and shadow.get("status") == "PROSPECTIVE_SHADOW" and shadow.get("production_default") is False and shadow.get("eligible_for_baseline") is False))
    aliases = (shadow or {}).get("aliases", {})
    expected_aliases = {"legacy_display_id": "e4_frozen_qlib_2023_2025_ltr", "compatibility_model_id": "head10_all_l31", "compatibility_candidate_id": "head10_all_l31_alpha0.7_top50_only", "compatibility_score_column": "score_head10_all_l31_alpha0.7_top50_only"}
    checks.append(result("model_b_alias_mapping", all(aliases.get(k) == v for k, v in expected_aliases.items()) and len(set(aliases.values())) == len(aliases), json.dumps(aliases, sort_keys=True)))
    artifacts = (shadow or {}).get("artifacts", {})
    for name, expected in (("canonical_model", "5623dda67772534aee3c8f96381813ecef36754fa1963876a428e7bfdf69bdbe"), ("materialized_shadow_model", "f833146520c942a9c2953ae382235ab0d1536ccc9d153c8db1ad500ca3117cd9")):
        item = artifacts.get(name, {})
        path = resolve(item.get("path", ""))
        checks.append(result(f"{name}_hash", path.exists() and sha256(path) == expected and item.get("sha256") == expected, str(path)))
    fallback = (shadow or {}).get("fallback", {})
    checks.append(result("fallback_relative_resolution", fallback.get("raw_registry_value") == "model_b" and fallback.get("resolution_pattern") == "<signal_root>/<asof>/model_b" and fallback.get("resolution_base") == "data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals"))
    checks.append(result("fallback_observation_truth", all(bool(item.get("exists")) == resolve(item.get("path", "")).exists() for item in fallback.get("resolved_observations", []))))
    constraints = (shadow or {}).get("constraints", {})
    checks.append(result("model_b_top50_only_constraint", constraints.get("candidate_universe") == "model_a_top50_only" and constraints.get("can_change_candidate_universe") is False and constraints.get("can_change_exit_boundary") is False))
    checks.append(result("model_b_required_pit_manifests", all(bool(constraints.get(key)) for key in ("signal_asof_required", "available_at_required", "source_manifest_required", "feature_manifest_required", "checksum_required"))))
    checks.append(result("forbidden_scope_all_false", bool(descriptor.get("forbidden_scope")) and all(value is False for value in descriptor["forbidden_scope"].values())))

    rows = annex.get("recent_jobs", [])
    # The annex is a point-in-time ARCH-1 evidence package.  It must not be
    # compared with the moving tail of today's daily jobs: every normal cron
    # run would otherwise invalidate this historical proof.  Validate the
    # immutable package shape and that its referenced jobs still exist.
    annex_paths = [str(row.get("path") or "") for row in rows]
    annex_paths_exist = all(bool(path) and resolve(path).is_file() for path in annex_paths)
    annex_paths_ordered = annex_paths == sorted(annex_paths)
    checks.append(result("C1_recent_20_job_annex", len(rows) == 20 and annex_paths_exist and annex_paths_ordered, f"rows={len(rows)}"))
    required_job_fields = {"path", "job_id", "status", "asof", "blocker", "latest_before", "latest_after", "provider_publish_triggered", "latest_signal_updated", "model_a_score_job_triggered", "model_b_ltr_score_job_triggered"}
    checks.append(result("C1_job_fields", all(required_job_fields <= set(row) for row in rows)))
    checks.append(result("C2_normalized_nonempty_full_scan", annex.get("normalized_nonempty_freshness", {}).get("scan_method") == "full_directory_all_csv_rows" and annex.get("normalized_nonempty_freshness", {}).get("max_tail") == "2026-06-01"))
    checks.append(result("C4_annex_identity", annex.get("model_b_identity", {}).get("canonical_id") == MODEL_B and annex.get("model_b_identity", {}).get("compatibility_model_id") == "head10_all_l31"))

    protected = annex.get("protected_latest_fingerprints", {})
    historical = historical_protected_paths()
    authorized_rebaseline = authorized_rebaseline_protected_paths()
    current_binding = protected == protected_expected and descriptor.get("protected_latest_paths") == protected_expected
    # ARCH-1 annexes are immutable point-in-time evidence.  After an
    # authorized descriptor rebaseline, a preserved annex may still carry the
    # prior hashes; accept it only when they exactly match the recorded drift
    # provenance.  Arbitrary or partially edited annex hashes remain invalid.
    historical_binding = (
        bool(historical)
        and bool(authorized_rebaseline)
        and protected == historical
        and descriptor.get("protected_latest_paths") == authorized_rebaseline
    )
    checks.append(result("protected_latest_unchanged", current_binding or historical_binding))
    forbidden = annex.get("forbidden_scope_audit", {})
    checks.append(result("no_publish_forbidden_scope", bool(forbidden) and all(value is False for value in forbidden.values())))
    return {"ok": all(item["status"] == "pass" for item in checks), "schema_version": "arch1.validator.v1", "descriptor": str(descriptor_path), "annex": str(annex_path), "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--descriptor", default=str(DEFAULT_DESCRIPTOR))
    parser.add_argument("--inventory", default=str(DEFAULT_INVENTORY))
    parser.add_argument("--annex", default=str(DEFAULT_ANNEX))
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    output = validate(resolve(args.descriptor), resolve(args.inventory), resolve(args.annex), resolve(args.schema))
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
