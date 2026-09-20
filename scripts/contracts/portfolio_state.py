"""Validate the frozen PortfolioState artifact and its admitted replay source."""

from __future__ import annotations

import csv
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any

import yaml
from yaml.constructor import ConstructorError

try:
    import validate_tw_readonly_replay_window_artifact as replay_artifact_validator
except ModuleNotFoundError:
    from scripts import validate_tw_readonly_replay_window_artifact as replay_artifact_validator

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GOLDEN_ROOT = ROOT / "data_tw/golden_samples/modular_contracts/m1"
SCHEMA_VERSION = "m1.0.0"
PORTFOLIO_SOURCE_ADMISSIONS = (
    ROOT / "configs/tw_portfolio_state_replay_source_admissions.yaml"
)

PORTFOLIO_REQUIRED_MANIFEST = (
    "artifact_type", "schema_version", "artifact_id", "run_id",
    "portfolio_id", "state_kind", "status", "asof", "available_at",
    "decision_cutoff", "portfolio_path", "schema", "row_count", "empty_state",
    "state_status", "empty_reason", "empty_state_evidence",
    "source_artifacts", "source_lineage", "checksum_manifest",
    "max_holding_policy", "pending_state", "pending_intents_path",
    "readonly_only", "simulation_only", "not_order",
    "not_target_position", "not_target_weight", "not_investment_advice",
    "no_broker", "production_allowed", "contains_account_identifier",
    "contains_pii", "contains_credentials", "no_provider_publish",
    "no_accepted_latest_switch", "forbidden_field_audit",
    "forbidden_action_audit",
)

class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: yaml.SafeLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)

PORTFOLIO_FORBIDDEN_ACTION_KEYS = {
    "provider_publish",
    "provider_refresh",
    "accepted_latest_switch",
    "qlib_accepted_latest_switch",
    "monitor_write",
    "monitor_scan",
    "broker_order",
    "quick_trade",
    "order_action",
    "default_strategy_switch",
    "agent_tool_expansion",
    "agent_prompt_expansion",
    "agent_action_expansion",
}

PORTFOLIO_COLUMNS = {
    "asof_date": "date",
    "instrument": "string",
    "quantity": "integer",
    "cost_basis": "number",
    "current_holding_flag": "boolean",
}
PORTFOLIO_STATE_KINDS = {"owner_independent_replay_simulation"}
PORTFOLIO_SOURCE_ARTIFACT_TYPES = {"replay_result"}
TAIPEI_UTC_OFFSET = timedelta(hours=8)
REPLAY_SOURCE_MANIFEST_FIELDS = {
    "artifact_type", "schema_version", "contract_version", "run_id", "asof",
    "status", "generated_by", "decision_source", "source_inputs", "artifacts",
    "checksum_manifest", "readonly_only", "simulation_only", "production_allowed",
    "product_index_admission", "runtime_admission", "no_training",
    "no_score_recompute", "no_provider_publish", "no_accepted_latest_switch",
    "no_order_action",
}
REPLAY_SOURCE_ARTIFACT_FILES = {
    "summary", "daily_nav", "actions", "snapshots", "coverage_audit",
    "position_integrity_audit", "forbidden_field_audit", "execution_audit",
    "forbidden_action_audit", "decision_source_audit", "forbidden_scope_audit",
    "action_lineage_audit", "source_identity_audit",
}
REPLAY_SNAPSHOT_COLUMNS = [
    "date", "instrument", "quantity", "cost_basis", "mark_price", "market_value",
    "unrealized_pnl", "strategy_rule", "model_name",
]
REPLAY_DAILY_NAV_COLUMNS = [
    "date", "cash", "market_value", "equity", "daily_return", "holding_count",
    "missing_price_count",
]
PENDING_INTENT_COLUMNS = [
    "instrument",
    "action",
    "source_signal_date",
    "source_intent_id",
]
PENDING_INTENT_SCHEMA = {
    "instrument": "string",
    "action": "enum:buy|sell",
    "source_signal_date": "date",
    "source_intent_id": "string",
}
PORTFOLIO_SAFETY_TRUE = {
    "readonly_only",
    "simulation_only",
    "not_order",
    "not_target_position",
    "not_target_weight",
    "not_investment_advice",
    "no_broker",
    "no_provider_publish",
    "no_accepted_latest_switch",
}
PORTFOLIO_SAFETY_FALSE = {
    "production_allowed",
    "contains_account_identifier",
    "contains_pii",
    "contains_credentials",
}
PORTFOLIO_FORBIDDEN_NAMES = (
    re.compile(r"^(account|account_id|broker_account)$", re.IGNORECASE),
    re.compile(r"^(user_id|user_name|owner_name|email|phone)$", re.IGNORECASE),
    re.compile(r".*(password|secret|credential|api_key|access_token).*$", re.IGNORECASE),
    re.compile(r"^(future_.*|forward_return.*|label_.*|relevance_.*)$", re.IGNORECASE),
    re.compile(r"^(execution_.*|price|open|close|mark_price|last_price)$", re.IGNORECASE),
    re.compile(r"^(cash|cash_balance|nav|equity|fee|fees|realized_pnl|unrealized_pnl|daily_return|replay_return)$", re.IGNORECASE),
    re.compile(r"^(high|low|volume|turnover|adj_factor)$", re.IGNORECASE),
    re.compile(r"^(target_position|target_weight|allocation_weight)$", re.IGNORECASE),
    re.compile(r"^(broker_order_id|order_id|quick_trade)$", re.IGNORECASE),
)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def error(
    code: str, message: str, path: Path, field: str = ""
) -> dict[str, str]:
    return {"code": code, "message": message, "path": rel(path), "field": field}


def iter_field_names(obj: Any) -> list[str]:
    names: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            names.append(str(key))
            names.extend(iter_field_names(value))
    elif isinstance(obj, list):
        for item in obj:
            names.extend(iter_field_names(item))
    return names


def _portfolio_forbidden_names(value: Any) -> list[str]:
    declared_absence_flags = {
        "contains_account_identifier",
        "contains_pii",
        "contains_credentials",
    }
    return sorted(
        {
            name
            for name in iter_field_names(value)
            if name not in declared_absence_flags
            if any(pattern.fullmatch(name) for pattern in PORTFOLIO_FORBIDDEN_NAMES)
        }
    )


def _aware_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value or value != value.strip():
        return None
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if "T" not in value or parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def _path_has_symlink(candidate: Path, stop: Path) -> bool:
    current = candidate
    while current != stop:
        if current.is_symlink():
            return True
        if current.parent == current:
            return True
        current = current.parent
    return stop.is_symlink()


def _portfolio_owned_path(
    base: Path,
    raw: Any,
    manifest_path: Path,
    field_name: str,
    errors: list[dict[str, str]],
) -> Path | None:
    if not isinstance(raw, str) or not raw or raw != raw.strip():
        errors.append(error("portfolio_path_invalid", "path must be a non-empty relative path", manifest_path, field_name))
        return None
    relative = Path(raw)
    if relative.is_absolute() or ".." in relative.parts:
        errors.append(error("portfolio_path_invalid", "absolute paths and traversal are forbidden", manifest_path, field_name))
        return None
    resolved_base = base.resolve()
    candidate = base / relative
    resolved = candidate.resolve()
    try:
        resolved.relative_to(resolved_base)
    except ValueError:
        errors.append(error("portfolio_path_invalid", "owned path escapes the artifact directory", candidate, field_name))
        return None
    if _path_has_symlink(candidate.absolute(), base.absolute()):
        errors.append(error("portfolio_symlink_forbidden", "portfolio contract paths must not contain symlinks", candidate, field_name))
        return None
    return resolved


def _portfolio_source_path(
    base: Path,
    raw: Any,
    manifest_path: Path,
    field_name: str,
    errors: list[dict[str, str]],
) -> Path | None:
    if not isinstance(raw, str) or not raw or raw != raw.strip():
        errors.append(error("portfolio_path_invalid", "source path must be a non-empty relative path", manifest_path, field_name))
        return None
    relative = Path(raw)
    if relative.is_absolute() or ".." in relative.parts:
        errors.append(error("portfolio_path_invalid", "absolute source paths and traversal are forbidden", manifest_path, field_name))
        return None
    local = base / relative
    is_golden = base.resolve().is_relative_to(DEFAULT_GOLDEN_ROOT.resolve())
    if local.exists() and is_golden:
        resolved = local.resolve()
        allowed_root = base.resolve()
        candidate = local
    else:
        candidate = ROOT / relative
        resolved = candidate.resolve()
        golden_root = DEFAULT_GOLDEN_ROOT.resolve()
        allowed_root = (
            golden_root
            if is_golden and resolved.is_relative_to(golden_root)
            else (ROOT / "data_tw/artifacts").resolve()
        )
    try:
        resolved.relative_to(allowed_root)
    except ValueError:
        errors.append(error("portfolio_source_path_forbidden", "source path must be local evidence or a standard artifact", candidate, field_name))
        return None
    if _path_has_symlink(candidate.absolute(), allowed_root.absolute()):
        errors.append(error("portfolio_symlink_forbidden", "source paths must not contain symlinks", candidate, field_name))
        return None
    return resolved


def _portfolio_replay_file_path(
    base: Path,
    raw: Any,
    manifest_path: Path,
    field_name: str,
    errors: list[dict[str, str]],
) -> Path | None:
    if not isinstance(raw, str) or not raw or raw != raw.strip():
        errors.append(error("portfolio_source_path_forbidden", "replay file path must be a non-empty repository-relative path", manifest_path, field_name))
        return None
    relative = Path(raw)
    if relative.is_absolute() or ".." in relative.parts:
        errors.append(error("portfolio_source_path_forbidden", "absolute replay paths and traversal are forbidden", manifest_path, field_name))
        return None
    candidate = ROOT / relative
    resolved = candidate.resolve()
    golden_root = DEFAULT_GOLDEN_ROOT.resolve()
    artifact_root = (ROOT / "data_tw/artifacts").resolve()
    if not (
        resolved.is_relative_to(artifact_root)
        or (base.resolve().is_relative_to(golden_root) and resolved.is_relative_to(golden_root))
    ):
        errors.append(error("portfolio_source_path_forbidden", "replay file must stay in its golden fixture or standard artifact root", candidate, field_name))
        return None
    allowed_root = golden_root if resolved.is_relative_to(golden_root) else artifact_root
    if _path_has_symlink(candidate.absolute(), allowed_root.absolute()):
        errors.append(error("portfolio_symlink_forbidden", "replay source paths must not contain symlinks", candidate, field_name))
        return None
    return resolved


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _portfolio_require_file(
    path: Path | None,
    field_name: str,
    errors: list[dict[str, str]],
    checked: list[str],
) -> bool:
    if path is None:
        return False
    if not path.is_file():
        errors.append(error("portfolio_file_missing", "declared portfolio contract file is missing", path, field_name))
        return False
    checked.append(rel(path))
    return True


def _validate_source_admission(
    *,
    source: dict[str, Any],
    source_path: Path,
    source_payload: dict[str, Any],
    errors: list[dict[str, str]],
    checked: list[str],
) -> None:
    if not PORTFOLIO_SOURCE_ADMISSIONS.is_file() or PORTFOLIO_SOURCE_ADMISSIONS.is_symlink():
        errors.append(error(
            "portfolio_source_admission_invalid",
            "the fixed replay source admission registry is missing or unsafe",
            PORTFOLIO_SOURCE_ADMISSIONS,
        ))
        return
    checked.append(rel(PORTFOLIO_SOURCE_ADMISSIONS))
    try:
        registry = yaml.load(
            PORTFOLIO_SOURCE_ADMISSIONS.read_text(encoding="utf-8"),
            Loader=_UniqueKeyLoader,
        )
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        errors.append(error(
            "portfolio_source_admission_invalid",
            f"the replay source admission registry is invalid: {type(exc).__name__}",
            PORTFOLIO_SOURCE_ADMISSIONS,
        ))
        return
    expected_registry_fields = {
        "schema_version", "runtime_admission", "production_allowed", "admissions"
    }
    admissions = registry.get("admissions") if isinstance(registry, dict) else None
    admission_id = source.get("admission_id")
    entry = admissions.get(admission_id) if isinstance(admissions, dict) else None
    expected_entry_fields = {
        "manifest_path", "manifest_sha256", "checksum_manifest_path",
        "checksum_manifest_sha256", "run_id", "asof", "schema_version",
        "contract_version", "validator_profile", "allowed_consumer",
        "production_allowed", "runtime_admission",
    }
    registry_ok = (
        isinstance(registry, dict)
        and set(registry) == expected_registry_fields
        and registry.get("schema_version") == "portfolio_state_replay_source_admissions_v1"
        and registry.get("runtime_admission") is False
        and registry.get("production_allowed") is False
        and isinstance(admissions, dict)
        and isinstance(admission_id, str)
        and isinstance(entry, dict)
        and set(entry) == expected_entry_fields
    )
    if not registry_ok:
        errors.append(error(
            "portfolio_source_not_admitted",
            "replay source admission is missing or malformed",
            PORTFOLIO_SOURCE_ADMISSIONS,
            str(admission_id or "admission_id"),
        ))
        return
    checksum_binding = source_payload.get("checksum_manifest")
    actual_source_ref = rel(source_path)
    admitted = (
        entry.get("manifest_path") == actual_source_ref
        and entry.get("manifest_sha256") == _sha256(source_path)
        and entry.get("manifest_sha256") == source.get("sha256")
        and entry.get("run_id") == source.get("run_id") == source_payload.get("run_id")
        and entry.get("asof") == source_payload.get("asof")
        and entry.get("schema_version") == source_payload.get("schema_version")
        and entry.get("contract_version") == source_payload.get("contract_version")
        and entry.get("validator_profile") == "portfolio_state_source_v1"
        and entry.get("allowed_consumer") == "portfolio_state"
        and entry.get("production_allowed") is False
        and entry.get("runtime_admission") is False
        and isinstance(checksum_binding, dict)
        and entry.get("checksum_manifest_path") == checksum_binding.get("path")
        and entry.get("checksum_manifest_sha256") == checksum_binding.get("sha256")
    )
    if not admitted:
        errors.append(error(
            "portfolio_source_not_admitted",
            "replay source identity does not match the fixed admission registry",
            source_path,
            str(admission_id),
        ))


def _validate_replay_source(
    *,
    base: Path,
    source_path: Path,
    source_payload: Any,
    asof: str,
    errors: list[dict[str, str]],
    checked: list[str],
) -> list[dict[str, str]]:
    if not isinstance(source_payload, dict) or set(source_payload) != REPLAY_SOURCE_MANIFEST_FIELDS:
        errors.append(error("portfolio_source_lineage_invalid", "replay source manifest must use the exact frozen field set", source_path))
        return []
    artifacts = source_payload.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != REPLAY_SOURCE_ARTIFACT_FILES:
        errors.append(error("portfolio_source_lineage_invalid", "replay source artifacts must use the exact required file set", source_path, "artifacts"))
        return []

    source_files: dict[str, Path] = {}
    declared_paths = {key: artifacts.get(key) for key in REPLAY_SOURCE_ARTIFACT_FILES}
    for field_name, raw_path in declared_paths.items():
        bound_path = _portfolio_replay_file_path(base, raw_path, source_path, field_name, errors)
        if _portfolio_require_file(bound_path, field_name, errors, checked):
            source_files[field_name] = bound_path

    checksum_binding = source_payload.get("checksum_manifest")
    if not isinstance(checksum_binding, dict) or set(checksum_binding) != {"path", "sha256", "bytes"}:
        errors.append(error("portfolio_source_checksum_mismatch", "replay checksum binding shape is invalid", source_path, "checksum_manifest"))
        checksum_binding = {}
    replay_checksum_path = _portfolio_replay_file_path(
        base, checksum_binding.get("path"), source_path, "checksum_manifest.path", errors
    )
    if _portfolio_require_file(replay_checksum_path, "checksum_manifest.path", errors, checked):
        if (
            not isinstance(checksum_binding.get("sha256"), str)
            or checksum_binding.get("sha256") != _sha256(replay_checksum_path)
            or type(checksum_binding.get("bytes")) is not int
            or checksum_binding.get("bytes") != replay_checksum_path.stat().st_size
        ):
            errors.append(error("portfolio_source_checksum_mismatch", "replay checksum manifest binding is invalid", replay_checksum_path))
        replay_checksum = load_json(replay_checksum_path)
        files = replay_checksum.get("files") if isinstance(replay_checksum, dict) else None
        if (
            not isinstance(replay_checksum, dict)
            or set(replay_checksum) != {"artifact_type", "schema_version", "run_id", "files"}
            or replay_checksum.get("artifact_type") != "portfolio_state_replay_source_checksum"
            or replay_checksum.get("schema_version") != "portfolio_state_replay_source_v1"
            or replay_checksum.get("run_id") != source_payload.get("run_id")
            or not isinstance(files, list)
        ):
            errors.append(error("portfolio_source_checksum_mismatch", "replay checksum manifest is invalid", replay_checksum_path))
            files = []
        declared_checksums: dict[str, dict[str, Any]] = {}
        for index, item in enumerate(files):
            if (
                not isinstance(item, dict)
                or set(item) != {"path", "sha256", "bytes"}
                or not isinstance(item.get("path"), str)
                or item["path"] in declared_checksums
            ):
                errors.append(error("portfolio_source_checksum_mismatch", "replay checksum entry is invalid or duplicated", replay_checksum_path, f"files[{index}]"))
                continue
            declared_checksums[item["path"]] = item
            bound_path = _portfolio_replay_file_path(base, item["path"], replay_checksum_path, f"files[{index}].path", errors)
            if _portfolio_require_file(bound_path, f"files[{index}].path", errors, checked):
                if (
                    not isinstance(item.get("sha256"), str)
                    or item["sha256"] != _sha256(bound_path)
                    or type(item.get("bytes")) is not int
                    or item["bytes"] != bound_path.stat().st_size
                ):
                    errors.append(error("portfolio_source_checksum_mismatch", "replay source file checksum mismatch", bound_path))
        if set(declared_checksums) != set(declared_paths.values()):
            errors.append(error("portfolio_source_checksum_mismatch", "replay checksum closure must exactly cover all replay evidence files", replay_checksum_path))

    if len(source_files) == len(declared_paths):
        try:
            formal_result = replay_artifact_validator.validate_portfolio_state_source_artifact(source_path)
        except Exception as exc:  # Formal validator is an external contract boundary.
            errors.append(error(
                "portfolio_source_validator_failed",
                f"formal ReplayResult validator could not parse the source: {type(exc).__name__}",
                source_path,
            ))
        else:
            if formal_result.get("ok") is not True:
                errors.append(error("portfolio_source_validator_failed", "formal ReplayResult validator rejected the source", source_path))

    daily_nav_path = source_files.get("daily_nav")
    if daily_nav_path is not None:
        with daily_nav_path.open("r", encoding="utf-8", newline="") as handle:
            nav_reader = csv.DictReader(handle, strict=True)
            if nav_reader.fieldnames != REPLAY_DAILY_NAV_COLUMNS:
                errors.append(error("portfolio_source_snapshot_mismatch", "replay daily NAV columns are invalid", daily_nav_path, "columns"))
            nav_rows = list(nav_reader)
        if (
            len([row for row in nav_rows if row.get("date") == asof]) != 1
            or any(set(row) != set(REPLAY_DAILY_NAV_COLUMNS) or None in row for row in nav_rows)
        ):
            errors.append(error("portfolio_source_snapshot_mismatch", "replay daily NAV must prove the portfolio existed at asof", daily_nav_path))

    snapshot_path = source_files.get("snapshots")
    if snapshot_path is None:
        return []
    with snapshot_path.open("r", encoding="utf-8", newline="") as handle:
        snapshot_reader = csv.DictReader(handle, strict=True)
        if snapshot_reader.fieldnames != REPLAY_SNAPSHOT_COLUMNS:
            errors.append(error("portfolio_source_snapshot_mismatch", "replay snapshots must use the frozen position columns", snapshot_path, "columns"))
        snapshot_rows = list(snapshot_reader)
    final_rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for index, row in enumerate(snapshot_rows):
        if set(row) != set(REPLAY_SNAPSHOT_COLUMNS) or None in row:
            errors.append(error("portfolio_source_snapshot_mismatch", "replay snapshot row has missing or extra cells", snapshot_path, f"rows[{index}]"))
            continue
        key = (row.get("date", ""), row.get("instrument", ""))
        if key in seen:
            errors.append(error("portfolio_source_snapshot_mismatch", "replay snapshot date/instrument must be unique", snapshot_path, f"rows[{index}]"))
        seen.add(key)
        if row.get("date") == asof:
            final_rows.append(row)
    return final_rows


def validate_portfolio_state(
    manifest: dict[str, Any], base: Path, manifest_path: Path, errors: list[dict[str, str]], checked: list[str]
) -> None:
    expected_manifest_fields = set(PORTFOLIO_REQUIRED_MANIFEST)
    if set(manifest) != expected_manifest_fields:
        errors.append(error("portfolio_manifest_fields_invalid", "portfolio manifest must use the exact frozen field set", manifest_path))
    run_id = manifest.get("run_id")
    portfolio_id = manifest.get("portfolio_id")
    safe_id = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,127}$")
    if not isinstance(run_id, str) or safe_id.fullmatch(run_id) is None:
        errors.append(error("portfolio_identity_invalid", "run_id is invalid", manifest_path, "run_id"))
    if not isinstance(portfolio_id, str) or re.fullmatch(r"ps_[0-9a-f]{32}", portfolio_id) is None:
        errors.append(error("portfolio_identity_invalid", "portfolio_id must be an opaque ps_ plus 32-hex identifier", manifest_path, "portfolio_id"))
    asof = manifest.get("asof")
    try:
        canonical_asof = datetime.strptime(str(asof), "%Y-%m-%d").date().isoformat()
    except ValueError:
        canonical_asof = ""
    if canonical_asof != asof:
        errors.append(error("portfolio_asof_invalid", "asof must be canonical YYYY-MM-DD", manifest_path, "asof"))
    expected_id = f"portfolio_state:{portfolio_id}:{asof}:{run_id}"
    if manifest.get("artifact_id") != expected_id:
        errors.append(error("portfolio_artifact_id_mismatch", "artifact_id does not bind portfolio/asof/run_id", manifest_path, "artifact_id"))
    if manifest.get("state_kind") not in PORTFOLIO_STATE_KINDS:
        errors.append(error("portfolio_state_kind_invalid", "WF-5B only admits owner-independent replay simulation state", manifest_path, "state_kind"))
    if manifest.get("status") != "READY":
        errors.append(error("portfolio_status_invalid", "status must be READY", manifest_path, "status"))
    if manifest.get("state_status") != "complete":
        errors.append(error("portfolio_state_incomplete", "state_status must be complete", manifest_path, "state_status"))
    available = _aware_timestamp(manifest.get("available_at"))
    cutoff = _aware_timestamp(manifest.get("decision_cutoff"))
    if available is None or cutoff is None:
        errors.append(error("portfolio_timestamp_invalid", "available_at and decision_cutoff must be timezone-aware ISO-8601 timestamps", manifest_path, "available_at"))
    elif available.utcoffset() != TAIPEI_UTC_OFFSET or cutoff.utcoffset() != TAIPEI_UTC_OFFSET:
        errors.append(error("portfolio_timestamp_invalid", "available_at and decision_cutoff must use the Taiwan +08:00 offset", manifest_path, "available_at"))
    elif available > cutoff:
        errors.append(error("portfolio_not_available_at_cutoff", "available_at must not exceed decision_cutoff", manifest_path, "available_at"))
    elif canonical_asof and available.date().isoformat() < canonical_asof:
        errors.append(error("portfolio_timestamp_invalid", "available_at cannot precede portfolio asof", manifest_path, "available_at"))
    if cutoff is not None and canonical_asof and cutoff.date().isoformat() != canonical_asof:
        errors.append(error("portfolio_cutoff_asof_mismatch", "decision_cutoff local date must equal asof", manifest_path, "decision_cutoff"))

    for field_name in PORTFOLIO_SAFETY_TRUE:
        if manifest.get(field_name) is not True:
            errors.append(error("portfolio_safety_flag_invalid", f"{field_name} must be true", manifest_path, field_name))
    for field_name in PORTFOLIO_SAFETY_FALSE:
        if manifest.get(field_name) is not False:
            errors.append(error("portfolio_safety_flag_invalid", f"{field_name} must be false", manifest_path, field_name))

    action_audit_path = _portfolio_owned_path(
        base,
        manifest.get("forbidden_action_audit", "forbidden_action_audit.json"),
        manifest_path,
        "forbidden_action_audit",
        errors,
    )
    if _portfolio_require_file(action_audit_path, "forbidden_action_audit", errors, checked):
        action_audit = load_json(action_audit_path)
        actions = action_audit.get("actions") if isinstance(action_audit, dict) else None
        if (
            not isinstance(action_audit, dict)
            or set(action_audit) != {"schema_version", "actions"}
            or action_audit.get("schema_version") != SCHEMA_VERSION
            or not isinstance(actions, dict)
            or set(actions) != PORTFOLIO_FORBIDDEN_ACTION_KEYS
            or any(value is not False for value in actions.values())
        ):
            errors.append(error("portfolio_forbidden_action_audit_invalid", "forbidden-action audit must exactly declare every forbidden action false", action_audit_path))

    max_policy = manifest.get("max_holding_policy")
    if not isinstance(max_policy, dict) or set(max_policy) != {"mode", "max_holding_count"}:
        errors.append(error("portfolio_max_holding_policy_invalid", "max_holding_policy must contain only mode and max_holding_count", manifest_path, "max_holding_policy"))
        max_holdings = 0
    else:
        max_holdings = max_policy.get("max_holding_count")
        if max_policy.get("mode") != "hard_cap" or type(max_holdings) is not int or not 1 <= max_holdings <= 100:
            errors.append(error("portfolio_max_holding_policy_invalid", "hard cap must be an integer from 1 to 100", manifest_path, "max_holding_policy"))
            max_holdings = 0

    pending = manifest.get("pending_state")
    if not isinstance(pending, dict) or set(pending) != {
        "status", "row_count", "captured_after_due_execution", "captured_before_decision"
    }:
        errors.append(error("portfolio_pending_state_invalid", "pending_state shape is invalid", manifest_path, "pending_state"))
    elif (
        pending.get("status") != "complete"
        or type(pending.get("row_count")) is not int
        or pending["row_count"] < 0
        or pending.get("captured_after_due_execution") is not True
        or pending.get("captured_before_decision") is not True
    ):
        errors.append(error("portfolio_pending_state_invalid", "pending projection must be complete and captured at the decision boundary", manifest_path, "pending_state"))

    schema_path = _portfolio_owned_path(base, manifest.get("schema", "schema.json"), manifest_path, "schema", errors)
    if _portfolio_require_file(schema_path, "schema", errors, checked):
        schema = load_json(schema_path)
        columns = schema.get("columns")
        actual_schema = {
            item.get("name"): item.get("type")
            for item in columns
            if isinstance(item, dict)
        } if isinstance(columns, list) else {}
        pending_columns = schema.get("pending_columns")
        actual_pending_schema = {
            item.get("name"): item.get("type")
            for item in pending_columns
            if isinstance(item, dict)
        } if isinstance(pending_columns, list) else {}
        if (
            set(schema) != {"schema_version", "columns", "pending_columns"}
            or schema.get("schema_version") != SCHEMA_VERSION
            or actual_schema != PORTFOLIO_COLUMNS
            or len(columns or []) != len(PORTFOLIO_COLUMNS)
            or actual_pending_schema != PENDING_INTENT_SCHEMA
            or len(pending_columns or []) != len(PENDING_INTENT_SCHEMA)
        ):
            errors.append(error("portfolio_schema_invalid", "portfolio schema must exactly match the frozen columns and types", schema_path, "columns"))

    portfolio_path = _portfolio_owned_path(base, manifest.get("portfolio_path"), manifest_path, "portfolio_path", errors)
    row_count = manifest.get("row_count")
    if type(row_count) is not int or row_count < 0:
        errors.append(error("portfolio_row_count_invalid", "row_count must be a non-negative integer", manifest_path, "row_count"))
        row_count = -1
    rows: list[dict[str, str]] = []
    if _portfolio_require_file(portfolio_path, "portfolio_path", errors, checked):
        with portfolio_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, strict=True)
            if reader.fieldnames != list(PORTFOLIO_COLUMNS):
                errors.append(error("portfolio_columns_invalid", "portfolio CSV columns must exactly match the frozen order", portfolio_path, "columns"))
            rows = list(reader)
        if row_count != len(rows):
            errors.append(error("portfolio_row_count_mismatch", "manifest row_count does not match portfolio CSV", portfolio_path, "row_count"))
    instruments: set[str] = set()
    holding_count = 0
    for index, row in enumerate(rows):
        prefix = f"rows[{index}]"
        if set(row) != set(PORTFOLIO_COLUMNS) or None in row:
            errors.append(error("portfolio_columns_invalid", "portfolio row has missing or extra cells", portfolio_path or manifest_path, prefix))
        if row.get("asof_date") != asof:
            errors.append(error("portfolio_row_asof_mismatch", "row asof_date must equal manifest asof", portfolio_path or manifest_path, f"{prefix}.asof_date"))
        instrument = row.get("instrument", "")
        if not isinstance(instrument, str) or re.fullmatch(r"TW[0-9A-Z]{4,8}", instrument) is None:
            errors.append(error("portfolio_instrument_invalid", "instrument must use canonical TW format", portfolio_path or manifest_path, f"{prefix}.instrument"))
        elif instrument in instruments:
            errors.append(error("portfolio_duplicate_instrument", "portfolio instruments must be unique", portfolio_path or manifest_path, f"{prefix}.instrument"))
        instruments.add(instrument)
        quantity_raw = row.get("quantity", "")
        quantity = int(quantity_raw) if isinstance(quantity_raw, str) and re.fullmatch(r"0|[1-9][0-9]*", quantity_raw) else -1
        try:
            cost_basis = float(row.get("cost_basis", ""))
        except (TypeError, ValueError):
            cost_basis = -1.0
        if quantity <= 0 or not math.isfinite(cost_basis) or cost_basis <= 0:
            errors.append(error("portfolio_numeric_value_invalid", "position quantity and cost_basis must be strictly positive", portfolio_path or manifest_path, prefix))
        holding_raw = row.get("current_holding_flag")
        if holding_raw not in {"true", "false"}:
            errors.append(error("portfolio_boolean_invalid", "current_holding_flag must be strict lowercase true/false", portfolio_path or manifest_path, f"{prefix}.current_holding_flag"))
        else:
            holding = holding_raw == "true"
            if holding is not True:
                errors.append(error("portfolio_row_state_inconsistent", "every position row must be a current holding", portfolio_path or manifest_path, prefix))
            holding_count += int(holding)
    if max_holdings and holding_count > max_holdings:
        errors.append(error("portfolio_max_holding_exceeded", "holding count exceeds the declared hard cap", portfolio_path or manifest_path, "max_holding_policy"))

    empty_state = manifest.get("empty_state")
    if type(empty_state) is not bool or empty_state != (len(rows) == 0):
        errors.append(error("portfolio_empty_state_mismatch", "empty_state must exactly match a zero-row CSV", manifest_path, "empty_state"))
    empty_reason = manifest.get("empty_reason")
    evidence_raw = manifest.get("empty_state_evidence")
    if empty_state is True:
        if empty_reason != "verified_no_positions":
            errors.append(error("portfolio_empty_state_evidence_invalid", "empty state requires verified_no_positions", manifest_path, "empty_reason"))
        evidence_path = _portfolio_owned_path(base, evidence_raw, manifest_path, "empty_state_evidence", errors)
        if _portfolio_require_file(evidence_path, "empty_state_evidence", errors, checked):
            evidence = load_json(evidence_path)
            expected = {
                "schema_version": SCHEMA_VERSION,
                "portfolio_id": portfolio_id,
                "asof": asof,
                "row_count": 0,
                "reason": "verified_no_positions",
                "no_synthetic_row": True,
                "source_proof_required": True,
            }
            if (
                evidence != expected
                or type(evidence.get("row_count")) is not int
                or evidence.get("no_synthetic_row") is not True
                or evidence.get("source_proof_required") is not True
            ):
                errors.append(error("portfolio_empty_state_evidence_invalid", "empty-state evidence must prove a real zero-row bootstrap", evidence_path))
    elif empty_reason is not None or evidence_raw is not None:
        errors.append(error("portfolio_empty_state_evidence_invalid", "non-empty portfolio must use null empty reason/evidence", manifest_path, "empty_state_evidence"))

    pending_path = _portfolio_owned_path(base, manifest.get("pending_intents_path"), manifest_path, "pending_intents_path", errors)
    pending_rows: list[dict[str, str]] = []
    if _portfolio_require_file(pending_path, "pending_intents_path", errors, checked):
        with pending_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, strict=True)
            if reader.fieldnames != PENDING_INTENT_COLUMNS:
                errors.append(error("portfolio_pending_columns_invalid", "pending intent projection columns are invalid", pending_path, "columns"))
            pending_rows = list(reader)
        if isinstance(pending, dict) and pending.get("row_count") != len(pending_rows):
            errors.append(error("portfolio_pending_row_count_mismatch", "pending row_count does not match projection", pending_path, "row_count"))
    pending_ids: set[str] = set()
    pending_semantics: set[tuple[str, str, str]] = set()
    pending_actions: dict[str, str] = {}
    pending_instruments: set[str] = set()
    for index, row in enumerate(pending_rows):
        prefix = f"pending[{index}]"
        if set(row) != set(PENDING_INTENT_COLUMNS) or None in row:
            errors.append(error("portfolio_pending_columns_invalid", "pending row has missing or extra cells", pending_path or manifest_path, prefix))
        instrument = row.get("instrument", "")
        intent_id = row.get("source_intent_id", "")
        signal_date = row.get("source_signal_date", "")
        if not isinstance(instrument, str) or re.fullmatch(r"TW[0-9A-Z]{4,8}", instrument) is None:
            errors.append(error("portfolio_instrument_invalid", "pending instrument must use canonical TW format", pending_path or manifest_path, f"{prefix}.instrument"))
        if row.get("action") not in {"buy", "sell"}:
            errors.append(error("portfolio_pending_action_invalid", "pending action must be buy or sell", pending_path or manifest_path, f"{prefix}.action"))
        try:
            signal_date_value = datetime.strptime(signal_date, "%Y-%m-%d").date().isoformat()
        except ValueError:
            signal_date_value = ""
        if signal_date_value != signal_date or (canonical_asof and signal_date >= canonical_asof):
            errors.append(error("portfolio_pending_signal_date_invalid", "pending source_signal_date must be canonical and precede asof", pending_path or manifest_path, f"{prefix}.source_signal_date"))
        if not isinstance(intent_id, str) or re.fullmatch(r"oi_[0-9a-f]{32}", intent_id) is None or intent_id in pending_ids:
            errors.append(error("portfolio_pending_intent_id_invalid", "pending source_intent_id must be an opaque unique oi_ plus 32-hex identifier", pending_path or manifest_path, f"{prefix}.source_intent_id"))
        pending_ids.add(intent_id)
        semantic_key = (instrument, str(row.get("action")), signal_date)
        if semantic_key in pending_semantics:
            errors.append(error("portfolio_pending_duplicate_semantics", "pending semantic tuple must be unique", pending_path or manifest_path, prefix))
        pending_semantics.add(semantic_key)
        if instrument in pending_instruments:
            errors.append(error("portfolio_pending_duplicate_instrument", "one instrument may have only one unresolved pending intent", pending_path or manifest_path, prefix))
        pending_instruments.add(instrument)
        previous_action = pending_actions.get(instrument)
        if previous_action is not None and previous_action != row.get("action"):
            errors.append(error("portfolio_pending_action_conflict", "one instrument cannot have pending buy and sell", pending_path or manifest_path, prefix))
        pending_actions[instrument] = str(row.get("action"))
        if row.get("action") == "sell" and instrument not in instruments:
            errors.append(error("portfolio_pending_position_mismatch", "pending sell instrument must be held", pending_path or manifest_path, prefix))
        if row.get("action") == "buy" and instrument in instruments:
            errors.append(error("portfolio_pending_position_mismatch", "pending buy instrument must be unheld", pending_path or manifest_path, prefix))
    if pending_rows:
        errors.append(error("portfolio_pending_source_unbound", "WF-5B does not admit non-empty pending rows until OrderIntent source binding exists", pending_path or manifest_path))

    source_artifacts = manifest.get("source_artifacts")
    if not isinstance(source_artifacts, list):
        errors.append(error("portfolio_source_lineage_invalid", "source_artifacts must be a list", manifest_path, "source_artifacts"))
        source_artifacts = []
    source_paths: list[str] = []
    source_identities: set[tuple[str, str]] = set()
    replay_final_rows: list[dict[str, str]] = []
    if len(source_artifacts) != 1:
        errors.append(error("portfolio_source_lineage_invalid", "WF-5B requires exactly one ReplayResult source", manifest_path, "source_artifacts"))
    for index, source in enumerate(source_artifacts):
        if not isinstance(source, dict) or set(source) != {
            "admission_id", "artifact_type", "run_id", "manifest_path", "sha256", "bytes"
        }:
            errors.append(error("portfolio_source_lineage_invalid", "source artifact shape is invalid", manifest_path, f"source_artifacts[{index}]"))
            continue
        if (
            not isinstance(source.get("artifact_type"), str)
            or source["artifact_type"] not in PORTFOLIO_SOURCE_ARTIFACT_TYPES
            or not isinstance(source.get("admission_id"), str)
            or safe_id.fullmatch(source["admission_id"]) is None
            or not isinstance(source.get("run_id"), str)
            or safe_id.fullmatch(source["run_id"]) is None
            or not isinstance(source.get("sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", source["sha256"]) is None
            or type(source.get("bytes")) is not int
            or source["bytes"] < 0
        ):
            errors.append(error("portfolio_source_lineage_invalid", "source artifact identity is invalid", manifest_path, f"source_artifacts[{index}]"))
        identity = (str(source.get("artifact_type")), str(source.get("run_id")))
        if identity in source_identities or source.get("manifest_path") in source_paths:
            errors.append(error("portfolio_source_lineage_invalid", "source artifacts must have unique identities and paths", manifest_path, f"source_artifacts[{index}]"))
        source_identities.add(identity)
        source_path = _portfolio_source_path(base, source.get("manifest_path"), manifest_path, f"source_artifacts[{index}].manifest_path", errors)
        if _portfolio_require_file(source_path, f"source_artifacts[{index}].manifest_path", errors, checked):
            source_payload = load_json(source_path)
            if source.get("sha256") != _sha256(source_path) or source.get("bytes") != source_path.stat().st_size:
                errors.append(error("portfolio_source_checksum_mismatch", "source artifact checksum mismatch", source_path))
            source_paths.append(str(source["manifest_path"]))
            if (
                not isinstance(source_payload, dict)
                or source_payload.get("artifact_type") != source.get("artifact_type")
                or source_payload.get("run_id") != source.get("run_id")
                or source_payload.get("asof") != asof
                or source_payload.get("status") != "VERIFIED_COMPLETE"
            ):
                errors.append(error("portfolio_source_lineage_invalid", "source manifest identity, asof, or status is not bound", source_path))
            if isinstance(source_payload, dict):
                _validate_source_admission(
                    source=source,
                    source_path=source_path,
                    source_payload=source_payload,
                    errors=errors,
                    checked=checked,
                )
            replay_final_rows.extend(
                _validate_replay_source(
                    base=base,
                    source_path=source_path,
                    source_payload=source_payload,
                    asof=str(asof),
                    errors=errors,
                    checked=checked,
                )
            )
    if not source_artifacts:
        errors.append(error("portfolio_source_lineage_invalid", "portfolio state requires at least one source proof", manifest_path, "source_artifacts"))
    def position_identity(row: dict[str, str]) -> tuple[str, int, Decimal] | None:
        try:
            quantity = int(row.get("quantity", ""))
            cost_basis = Decimal(row.get("cost_basis", ""))
        except (InvalidOperation, TypeError, ValueError):
            return None
        if quantity <= 0 or not cost_basis.is_finite() or cost_basis <= 0:
            return None
        return row.get("instrument", ""), quantity, cost_basis

    portfolio_identities = {position_identity(row) for row in rows}
    replay_identities = {position_identity(row) for row in replay_final_rows}
    if None in portfolio_identities or None in replay_identities or portfolio_identities != replay_identities:
        errors.append(error("portfolio_source_snapshot_mismatch", "portfolio positions must exactly match the validated replay snapshot at asof", portfolio_path or manifest_path))

    lineage_path = _portfolio_owned_path(base, manifest.get("source_lineage"), manifest_path, "source_lineage", errors)
    if _portfolio_require_file(lineage_path, "source_lineage", errors, checked):
        lineage = load_json(lineage_path)
        lineage_kind = lineage.get("lineage_kind") if isinstance(lineage, dict) else None
        source_types = {
            item.get("artifact_type")
            for item in source_artifacts
            if isinstance(item, dict)
        }
        if (
            not isinstance(lineage, dict)
            or set(lineage) != {
                "schema_version", "portfolio_id", "state_kind", "asof",
                "lineage_kind", "source_artifacts",
            }
            or lineage.get("schema_version") != SCHEMA_VERSION
            or lineage.get("portfolio_id") != portfolio_id
            or lineage.get("state_kind") != manifest.get("state_kind")
            or lineage.get("asof") != asof
            or lineage.get("source_artifacts") != source_artifacts
            or lineage.get("lineage_kind") not in {"verified_empty_source", "replay_execution"}
            or (empty_state is True and lineage.get("lineage_kind") != "verified_empty_source")
            or (lineage_kind in {"verified_empty_source", "replay_execution"} and "replay_result" not in source_types)
        ):
            errors.append(error("portfolio_source_lineage_invalid", "source lineage does not bind the manifest identity", lineage_path))
        for name in _portfolio_forbidden_names(lineage):
            errors.append(error("portfolio_forbidden_field", f"forbidden lineage field {name}", lineage_path, name))

    owned_refs = {
        str(manifest.get("portfolio_path")),
        str(manifest.get("schema", "schema.json")),
        str(manifest.get("source_lineage")),
        str(manifest.get("pending_intents_path")),
        str(manifest.get("forbidden_action_audit", "forbidden_action_audit.json")),
        str(manifest.get("forbidden_field_audit")),
        *source_paths,
    }
    if empty_state is True and isinstance(evidence_raw, str):
        owned_refs.add(evidence_raw)
    checksum_path = _portfolio_owned_path(base, manifest.get("checksum_manifest"), manifest_path, "checksum_manifest", errors)
    if _portfolio_require_file(checksum_path, "checksum_manifest", errors, checked):
        checksum = load_json(checksum_path)
        if (
            not isinstance(checksum, dict)
            or set(checksum) != {"schema_version", "files"}
            or checksum.get("schema_version") != SCHEMA_VERSION
        ):
            errors.append(error("portfolio_checksum_manifest_invalid", "checksum manifest shape or schema version is invalid", checksum_path))
        files = checksum.get("files") if isinstance(checksum, dict) else None
        declared: dict[str, dict[str, Any]] = {}
        if not isinstance(files, list):
            errors.append(error("portfolio_checksum_manifest_invalid", "checksum files must be a list", checksum_path, "files"))
            files = []
        for index, item in enumerate(files):
            if (
                not isinstance(item, dict)
                or set(item) != {"path", "sha256", "bytes"}
                or not isinstance(item.get("path"), str)
                or item.get("path") in declared
            ):
                errors.append(error("portfolio_checksum_manifest_invalid", "checksum entry is invalid or duplicated", checksum_path, f"files[{index}]"))
                continue
            declared[item["path"]] = item
            if item["path"] in source_paths:
                bound_path = _portfolio_source_path(base, item["path"], checksum_path, f"files[{index}].path", errors)
            else:
                bound_path = _portfolio_owned_path(base, item["path"], checksum_path, f"files[{index}].path", errors)
            if _portfolio_require_file(bound_path, f"files[{index}].path", errors, checked):
                if (
                    item.get("sha256") != _sha256(bound_path)
                    or type(item.get("bytes")) is not int
                    or item.get("bytes") != bound_path.stat().st_size
                ):
                    errors.append(error("portfolio_checksum_mismatch", "checksum or byte count mismatch", bound_path))
        if set(declared) != owned_refs:
            errors.append(error("portfolio_checksum_closure_incomplete", "checksum closure must exactly cover all owned and source files", checksum_path, "files"))

    scan_values = [manifest]
    if schema_path and schema_path.is_file():
        scan_values.append(load_json(schema_path))
    for value in scan_values:
        for name in _portfolio_forbidden_names(value):
            errors.append(error("portfolio_forbidden_field", f"forbidden portfolio field {name}", manifest_path, name))

    field_audit_path = _portfolio_owned_path(base, manifest.get("forbidden_field_audit"), manifest_path, "forbidden_field_audit", errors)
    if _portfolio_require_file(field_audit_path, "forbidden_field_audit", errors, checked):
        field_audit = load_json(field_audit_path)
        expected_scanned = sorted(owned_refs - {str(manifest.get("forbidden_field_audit"))})
        if (
            set(field_audit) != {"schema_version", "status", "forbidden_fields", "scanned_files"}
            or field_audit.get("schema_version") != SCHEMA_VERSION
            or field_audit.get("status") != "pass"
            or field_audit.get("forbidden_fields") != []
            or field_audit.get("scanned_files") != expected_scanned
        ):
            errors.append(error("portfolio_forbidden_field_audit_invalid", "forbidden-field audit does not cover the declared closure", field_audit_path))
