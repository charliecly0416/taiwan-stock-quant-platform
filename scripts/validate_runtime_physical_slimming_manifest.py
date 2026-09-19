#!/usr/bin/env python3
"""Fail-closed validator for the no-move runtime manifest."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from build_runtime_physical_slimming_manifest import (
    ACTIVE_ROOTS,
    CONFIG_ROOTS,
    CONTROL_PATHS,
    DAPR_TARGETS,
    IGNORED_PARTS,
    PROTECTED_PATHS,
    SCHEMA_VERSION,
    cron_commands,
    git_states,
    sha256,
    build_manifest,
)


DEFAULT_SCHEMA = Path(__file__).resolve().parents[1] / "schemas/runtime_physical_slimming_manifest.schema.json"


def _under_root(root: Path, path: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def _repo_path(root: Path, raw: str) -> Path | None:
    candidate = Path(raw)
    if not raw or candidate.is_absolute() or ".." in candidate.parts:
        return None
    path = root / candidate
    return path if _under_root(root, path) else None


def _safe_source_path(root: Path, raw: str) -> Path | None:
    """Resolve a dynamic exception source without allowing repo escape."""
    return _repo_path(root, raw)


def _canonical_records(records: list[dict[str, Any]]) -> list[str]:
    """Canonicalize every record so omission or reference-value edits are visible."""
    return [json.dumps(item, ensure_ascii=True, sort_keys=True, separators=(",", ":")) for item in records]


def _independent_expected_manifest(
    root: Path,
    manifest: dict[str, Any],
    installed_cron: Path | None,
    actual_cron: Path | None,
) -> dict[str, Any] | None:
    """Rebuild closure from source files; submitted records are never the oracle."""
    try:
        cron = installed_cron or root / "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron"
        actual = actual_cron or Path(str((manifest.get("cron_parity") or {}).get("actual_evidence_path") or ""))
        if not cron.is_file() or not actual.is_file():
            return None
        status_entries = manifest.get("git_status_entries") if isinstance(manifest.get("git_status_entries"), list) else []
        states = {
            str(item.get("path")): str(item.get("state"))
            for item in status_entries
            if isinstance(item, dict) and item.get("path")
        }
        snapshot = (bool(manifest.get("worktree_dirty")), states, status_entries)
        return build_manifest(
            root,
            cron.resolve(),
            actual.resolve(),
            str(manifest.get("observed_at") or "1970-01-01T00:00:00+00:00"),
            git_snapshot=snapshot,
        )
    except Exception as exc:  # pragma: no cover - fail closed in caller
        return {"_rebuild_error": f"{type(exc).__name__}:{exc}"}


def _add_schema_errors(errors: list[str], manifest: Any, schema_path: Path) -> None:
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        for issue in sorted(validator.iter_errors(manifest), key=lambda item: list(item.absolute_path)):
            location = "/".join(str(part) for part in issue.absolute_path) or "$"
            errors.append(f"schema_validation:{location}:{issue.message}")
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"schema_unavailable:{type(exc).__name__}")


def _validate_cron(
    errors: list[str], manifest: dict[str, Any], root: Path,
    installed_cron: Path | None, actual_cron: Path | None,
) -> None:
    cron = manifest.get("cron_parity") if isinstance(manifest.get("cron_parity"), dict) else {}
    expected_installed = installed_cron or root / "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron"
    raw_actual = str(cron.get("actual_evidence_path") or "")
    expected_actual = actual_cron or (Path(raw_actual) if raw_actual else None)
    if not expected_installed.is_file():
        errors.append("installed_cron_missing")
        return
    if expected_actual is None or not expected_actual.is_file():
        errors.append("actual_cron_evidence_missing")
        return

    installed_text = expected_installed.read_text(encoding="utf-8")
    actual_text = expected_actual.read_text(encoding="utf-8")
    installed_commands = cron_commands(installed_text)
    actual_commands = cron_commands(actual_text)
    expected_installed_rel = str(expected_installed.resolve().relative_to(root.resolve())) if _under_root(root, expected_installed) else ""
    if cron.get("installed_path") != expected_installed_rel:
        errors.append("installed_cron_path_mismatch")
    if cron.get("actual_evidence_path") != str(expected_actual.resolve()):
        errors.append("actual_cron_path_mismatch")
    if cron.get("installed_sha256") != sha256(expected_installed):
        errors.append("installed_cron_current_hash_mismatch")
    if cron.get("actual_sha256") != sha256(expected_actual):
        errors.append("actual_cron_current_hash_mismatch")
    if cron.get("installed_sha256") != cron.get("actual_sha256"):
        errors.append("cron_parity_hash_mismatch")
    if cron.get("installed_daily_commands") != installed_commands:
        errors.append("installed_cron_manifest_commands_mismatch")
    if cron.get("actual_daily_commands") != actual_commands:
        errors.append("actual_cron_manifest_commands_mismatch")
    if installed_commands != actual_commands:
        errors.append("cron_parity_command_mismatch")
    if len(installed_commands) != 2:
        errors.append("cron_daily_command_count_not_two")


def validate(
    manifest: dict[str, Any], root: Path, *, schema_path: Path = DEFAULT_SCHEMA,
    installed_cron: Path | None = None, actual_cron: Path | None = None,
    check_git_state: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    errors: list[str] = []
    _add_schema_errors(errors, manifest, schema_path)

    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if manifest.get("repository_root") != str(root):
        errors.append("repository_root_mismatch")
    _validate_cron(errors, manifest, root, installed_cron, actual_cron)
    if manifest.get("dapr_targets") != DAPR_TARGETS:
        errors.append("dapr_target_order_or_content_mismatch")

    records = manifest.get("records") if isinstance(manifest.get("records"), list) else []
    key_count: dict[tuple[str, str, str], int] = {}
    classifications: dict[tuple[str, str], set[str]] = {}
    dapr_records: list[dict[str, Any]] = []
    for index, item in enumerate(records):
        if not isinstance(item, dict):
            continue
        source = str(item.get("source_path") or "")
        target = str(item.get("target_path") or "")
        reference_type = str(item.get("reference_type") or "")
        runtime_scope = str(item.get("runtime_scope") or "")
        classification = str(item.get("classification") or "")
        key = (source, target, reference_type)
        key_count[key] = key_count.get(key, 0) + 1
        if target:
            classifications.setdefault((target, runtime_scope), set()).add(classification)

        source_parts = set(Path(source).parts)
        target_parts = set(Path(target).parts)
        if source_parts.intersection(IGNORED_PARTS) or target_parts.intersection(IGNORED_PARTS):
            errors.append(f"ignored_path_recorded:{index}")
        if item.get("move_eligible") is not False:
            errors.append(f"move_eligible_must_be_false:{target or source}")

        if reference_type == "dynamic_exception":
            source_path = _safe_source_path(root, source)
            if source_path is None or not source_path.is_file() or not _under_root(root, source_path):
                errors.append(f"dynamic_exception_source_invalid:{source}")
            elif set(source_path.relative_to(root).parts).intersection(IGNORED_PARTS):
                errors.append(f"dynamic_exception_source_ignored:{source}")
            if target or item.get("resolved_path") or item.get("sha256") or item.get("exists") is not False:
                errors.append(f"dynamic_exception_has_physical_target:{source}")
            detail = item.get("dynamic_exception")
            if (
                classification != "unknown_do_not_move"
                or not isinstance(detail, dict)
                or detail.get("quarantine") != "unknown_do_not_move"
                or not detail.get("references")
            ):
                errors.append(f"dynamic_exception_not_quarantined:{source}")
            elif any(
                not isinstance(category, str)
                or not category
                or not isinstance(values, list)
                or not values
                or any(not isinstance(value, str) or not value for value in values)
                for category, values in detail.get("references", {}).items()
            ):
                errors.append(f"dynamic_exception_references_invalid:{source}")
            continue

        path = _repo_path(root, target)
        if path is None:
            errors.append(f"invalid_or_escaping_target:{target}")
            continue
        if not path.is_file() or not _under_root(root, path):
            errors.append(f"missing_or_escaping_target:{target}")
            continue
        expected_resolved = str(path.resolve().relative_to(root))
        if item.get("resolved_path") != expected_resolved:
            errors.append(f"resolved_path_mismatch:{target}")
        if item.get("exists") is not True or item.get("sha256") != sha256(path):
            errors.append(f"changed_or_missing_target:{target}")
        if item.get("dynamic_exception") is not None:
            errors.append(f"physical_record_has_dynamic_exception:{target}")
        if "archive" in target_parts and classification != "unknown_do_not_move":
            errors.append(f"archive_reference_not_quarantined:{target}")
        if reference_type == "dapr_subprocess":
            dapr_records.append(item)

    if any(count != 1 for count in key_count.values()):
        errors.append("duplicate_record_key")
    if any(len(values) > 1 for values in classifications.values()):
        errors.append("conflicting_classification_in_scope")

    expected_dapr = list(enumerate(DAPR_TARGETS, start=1))
    actual_dapr: list[tuple[int, str]] = []
    for item in dapr_records:
        evidence = item.get("evidence") if isinstance(item.get("evidence"), dict) else {}
        actual_dapr.append((evidence.get("dapr_order"), item.get("target_path")))
        if (
            item.get("source_path") != "scripts/run_daily_tw_stock_auto_update.py"
            or item.get("runtime_scope") != "production_runtime"
            or item.get("classification") != "active_keep"
            or item.get("exists") is not True
            or evidence.get("expected_step_count") != len(DAPR_TARGETS)
        ):
            errors.append(f"dapr_record_invalid:{item.get('target_path')}")
    try:
        dapr_matches = sorted(actual_dapr) == expected_dapr
    except TypeError:
        dapr_matches = False
    if not dapr_matches or len(dapr_records) != len(DAPR_TARGETS):
        errors.append("dapr_records_missing_duplicate_or_reordered")

    for target in ACTIVE_ROOTS + CONFIG_ROOTS + PROTECTED_PATHS + DAPR_TARGETS:
        matches = [
            item for item in records
            if isinstance(item, dict)
            and item.get("target_path") == target
            and item.get("runtime_scope") == "production_runtime"
            and item.get("classification") == "active_keep"
            and item.get("exists") is True
        ]
        if not matches:
            errors.append(f"required_active_keep_missing:{target}")

    for target in CONTROL_PATHS:
        matches = [
            item for item in records
            if isinstance(item, dict)
            and item.get("target_path") == target
            and item.get("reference_type") == "manifest_control"
            and item.get("sha256") == sha256(root / target)
        ]
        if len(matches) != 1:
            errors.append(f"manifest_control_fingerprint_invalid:{target}")

    protected = manifest.get("protected_fingerprints") if isinstance(manifest.get("protected_fingerprints"), dict) else {}
    if set(protected) != set(PROTECTED_PATHS):
        errors.append("protected_fingerprint_keys_mismatch")
    for target in PROTECTED_PATHS:
        entry = protected.get(target) if isinstance(protected.get(target), dict) else {}
        path = root / target
        if not entry or entry.get("exists") is not True or entry.get("sha256") != sha256(path):
            errors.append(f"protected_fingerprint_invalid:{target}")

    # Independently rediscover production/test closure and compare every record.
    # This catches omission of a seed, archive literal, dynamic category/value,
    # or test-harness dependency even when the submitted manifest is internally
    # self-consistent.
    expected = _independent_expected_manifest(root, manifest, installed_cron, actual_cron)
    if expected is None:
        errors.append("independent_closure_rebuild_unavailable")
    elif expected.get("_rebuild_error"):
        errors.append(f"independent_closure_rebuild_failed:{expected['_rebuild_error']}")
    else:
        submitted_records = _canonical_records(records)
        expected_records = _canonical_records(expected.get("records") if isinstance(expected.get("records"), list) else [])
        if submitted_records != expected_records:
            errors.append("production_closure_records_mismatch")
        if manifest.get("closure_summary") != expected.get("closure_summary"):
            errors.append("independent_closure_summary_mismatch")
        for field in ("dapr_targets", "cron_parity", "protected_fingerprints"):
            if manifest.get(field) != expected.get(field):
                errors.append(f"independent_{field}_mismatch")

    if check_git_state:
        try:
            dirty, _, entries = git_states(root)
            if manifest.get("worktree_dirty") is not dirty:
                errors.append("worktree_dirty_state_mismatch")
            if manifest.get("git_status_entries") != entries:
                errors.append("git_status_entries_current_mismatch")
        except Exception as exc:  # pragma: no cover - defensive fail-closed boundary
            errors.append(f"git_status_check_failed:{type(exc).__name__}")

    unique_errors = sorted(set(errors))
    return {
        "ok": not unique_errors,
        "status": "PASS" if not unique_errors else "FAIL",
        "schema_validation": "PASS" if not any(item.startswith("schema_") for item in unique_errors) else "FAIL",
        "errors": unique_errors,
        "record_count": len(records),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate no-move runtime physical slimming manifest.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--installed-cron", type=Path, default=None)
    parser.add_argument("--actual-cron", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    result = validate(
        payload,
        args.root,
        schema_path=args.schema,
        installed_cron=args.installed_cron,
        actual_cron=args.actual_cron,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
