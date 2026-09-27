#!/usr/bin/env python3
"""Fail-closed, synthetic-only validator for the MBOOS2_U absence design.

This module deliberately accepts no filesystem payloads and no real calendar
dates. It validates contract semantics over in-memory SYNTHETIC_* values only.
"""
from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "nmrpa.structural_absence_record.v1"
STATUSES = frozenset({
    "unknown_source_coverage", "confirmed_absent", "present",
    "scope_incomplete", "access_failed", "stale", "conflicting",
})
CONFIRMED_ABSENT_REQUIREMENTS = (
    "complete_scope", "set_closure", "target_in_absent", "effective_interval",
    "pit_ok", "immutable_evidence", "binding_ok", "unique_key_and_hash",
)
REAL_DATE = re.compile(r"^20\\d{2}-\\d{2}-\\d{2}$")
SYNTHETIC = re.compile(r"^SYNTHETIC_[A-Z0-9_]+$")
FORBIDDEN_FIELD_NAMES = frozenset({"label", "future_return", "forward_return", "realized_return", "metric", "outcome", "price", "volume", "pnl", "target_weight", "order_qty"})
LAYER_VALUES = {
    "active_set": {"formal_bound", "unknown", "omitted"},
    "listing_status": {"eligible", "not_listed", "unknown", "conflicting"},
    "trading_status": {"tradable", "not_tradable", "unknown", "conflicting"},
    "margin_eligibility": {"eligible", "not_eligible", "unknown", "conflicting"},
    "source_completeness": {"complete", "incomplete", "failed", "stale"},
}


class SyntheticContractError(ValueError):
    pass


def _synthetic(value: Any, field: str) -> str:
    if not isinstance(value, str) or not SYNTHETIC.fullmatch(value):
        raise SyntheticContractError(f"REAL_INPUT_REJECTED:{field}")
    return value


def _reject_real_payload_shape(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            lowered = str(key).lower()
            if lowered in FORBIDDEN_FIELD_NAMES:
                raise SyntheticContractError(f"REAL_PAYLOAD_FIELD_REJECTED:{key}")
            _reject_real_payload_shape(child)
    elif isinstance(value, list):
        for child in value:
            _reject_real_payload_shape(child)


def canonical_sha256(value: Any, *, exclude: str | None = None) -> str:
    if isinstance(value, Mapping):
        value = {k: v for k, v in value.items() if k != exclude}
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def _keys(values: Sequence[Mapping[str, Any]]) -> list[tuple[str, str]]:
    result = []
    for item in values:
        result.append((_synthetic(item["sample_date"], "sample_date"), _synthetic(item["instrument"], "instrument")))
    return result


def validate_status_closed(status: Any) -> str:
    if status not in STATUSES:
        raise SyntheticContractError("STATUS_NOT_CLOSED")
    return status


def _closure(evidence: Mapping[str, Any], key: tuple[str, str]) -> bool:
    def checked(values: Any) -> tuple[set[tuple[str, str]], bool]:
        result = []
        for pair in values:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                return set(), False
            result.append((_synthetic(pair[0], "set.sample_date"), _synthetic(pair[1], "set.instrument")))
        if len(result) != len(set(result)):
            raise SyntheticContractError("DUPLICATE_SET_PAIR")
        return set(result), True
    expected, expected_valid = checked(evidence.get("expected_set", []))
    returned, returned_valid = checked(evidence.get("returned_set", []))
    absent, absent_valid = checked(evidence.get("absent_set", []))
    if not all((expected_valid, returned_valid, absent_valid)):
        return False
    return bool(expected) and expected == returned | absent and returned.isdisjoint(absent) and key in absent


def _hash_valid(record: Mapping[str, Any]) -> bool:
    supplied = record.get("record_sha256")
    return isinstance(supplied, str) and supplied == canonical_sha256(record, exclude="record_sha256")


def _confirmed_checks(record: Mapping[str, Any]) -> dict[str, bool]:
    evidence = record.get("authoritative_evidence")
    if not isinstance(evidence, Mapping):
        evidence = {}
    key = (record.get("sample_date"), record.get("instrument"))
    layers = record["eligibility_layers"]
    scope = record.get("request_scope_sha256")
    lineage = record.get("lineage")
    checks = {
        "complete_scope": evidence.get("complete_scope") is True and layers["source_completeness"] == "complete" and bool(evidence.get("request_scope_id")) and scope == evidence.get("request_scope_sha256"),
        "set_closure": _closure(evidence, key),
        "target_in_absent": key in set(map(tuple, evidence.get("absent_set", []))),
        "effective_interval": bool(record.get("effective_start_or_null")) and layers["active_set"] == "formal_bound" and layers["listing_status"] in {"eligible", "not_listed"} and layers["trading_status"] in {"tradable", "not_tradable"} and layers["margin_eligibility"] in {"eligible", "not_eligible"} and bool(evidence.get("effective_interval_verified")),
        "pit_ok": evidence.get("pit_available_at") == "SYNTHETIC_TIME_BEFORE_CUTOFF" and record.get("pit_available_at") == "SYNTHETIC_TIME_BEFORE_CUTOFF" and evidence.get("source_asof") == record.get("sample_date"),
        "immutable_evidence": bool(evidence.get("evidence_path", "").startswith("SYNTHETIC_")) and bool(evidence.get("manifest_sha256")) and bool(evidence.get("immutable_lineage")),
        "binding_ok": bool(lineage) and lineage == evidence.get("lineage") and evidence.get("binding_ok") is True,
        "unique_key_and_hash": _synthetic(record.get("sample_date"), "sample_date") is not None and _synthetic(record.get("instrument"), "instrument") is not None and _hash_valid(record),
    }
    return checks


def validate_record(record: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise SyntheticContractError("RECORD_OBJECT_REQUIRED")
    _reject_real_payload_shape(record)
    required = {"schema_version", "record_id", "sample_date", "instrument", "source_kind", "status", "request_scope_id", "request_scope_sha256", "effective_start_or_null", "effective_end_or_null", "decision_time", "pit_available_at", "authoritative_evidence", "classification_reason_code", "unique_join_key", "record_sha256", "lineage"}
    if not required.issubset(record):
        raise SyntheticContractError("RECORD_FIELDS_INCOMPLETE")
    if record["schema_version"] != SCHEMA_VERSION:
        raise SyntheticContractError("SCHEMA_VERSION_UNSUPPORTED")
    for field in ("record_id", "sample_date", "instrument", "source_kind", "request_scope_id", "decision_time", "pit_available_at", "lineage"):
        _synthetic(record[field], field)
    for field in ("effective_start_or_null", "effective_end_or_null"):
        if record[field] is not None:
            _synthetic(record[field], field)
    if REAL_DATE.fullmatch(record["sample_date"]):
        raise SyntheticContractError("REAL_DATE_REJECTED")
    if tuple(record["unique_join_key"]) != (record["sample_date"], record["instrument"]):
        raise SyntheticContractError("UNIQUE_KEY_MISMATCH")
    layers = record.get("eligibility_layers")
    if not isinstance(layers, Mapping) or set(layers) != set(LAYER_VALUES):
        raise SyntheticContractError("ELIGIBILITY_LAYERS_INCOMPLETE")
    for name, allowed in LAYER_VALUES.items():
        if layers[name] not in allowed:
            raise SyntheticContractError(f"ELIGIBILITY_LAYER_INVALID:{name}")
    status = validate_status_closed(record["status"])
    checks = _confirmed_checks(record) if status == "confirmed_absent" else {}
    if status == "confirmed_absent" and not all(checks.values()):
        raise SyntheticContractError("CONFIRMED_ABSENT_GATE_FAILED:" + ",".join(k for k, v in checks.items() if not v))
    if status in {"unknown_source_coverage", "scope_incomplete", "access_failed", "stale", "conflicting"} and record.get("feature_mapping") in {"neutral", "trainable"}:
        raise SyntheticContractError("NON_ABSENCE_NEUTRAL_FILL_REJECTED")
    return {"status": status, "checks": checks, "record_sha256": record["record_sha256"]}


def validate_date_summary(summary: Mapping[str, Any]) -> dict[str, Any]:
    _synthetic(summary.get("date"), "date")
    status = summary.get("status")
    if status not in {"valid", "invalid", "quarantined", "recovered"}:
        raise SyntheticContractError("DATE_STATUS_NOT_CLOSED")
    records = summary.get("records", [])
    for record in records:
        if not isinstance(record, Mapping) or record.get("sample_date") != summary["date"]:
            raise SyntheticContractError("DATE_RECORD_MISMATCH")
    keys = _keys(records)
    if len(keys) != len(set(keys)):
        raise SyntheticContractError("DUPLICATE_UNIQUE_KEY")
    results = [validate_record(record) for record in records]
    if status == "valid" and any(item["status"] not in {"present", "confirmed_absent"} for item in results):
        raise SyntheticContractError("VALID_DATE_CONTAINS_UNRESOLVED_RECORD")
    if status in {"invalid", "quarantined"} and summary.get("quarantine_reason") is None:
        raise SyntheticContractError("QUARANTINE_REASON_REQUIRED")
    return {"status": status, "record_count": len(results)}


def validate_recovery(old: Mapping[str, Any], new: Mapping[str, Any]) -> None:
    if old.get("status") not in {"invalid", "quarantined"} or new.get("status") != "recovered":
        raise SyntheticContractError("RECOVERY_STATE_INVALID")
    if new.get("supersedes") != old.get("version_id") or new.get("version_id") == old.get("version_id"):
        raise SyntheticContractError("RECOVERY_NOT_APPEND_ONLY")
    validate_date_summary(new)


def validate_version_migration(old: Mapping[str, Any], new: Mapping[str, Any], migration: Mapping[str, Any]) -> None:
    if old.get("schema_version") == new.get("schema_version") or migration.get("from") != old.get("schema_version") or migration.get("to") != new.get("schema_version"):
        raise SyntheticContractError("VERSION_MIGRATION_INVALID")
    if not migration.get("reviewer_approval") or not migration.get("new_canonical_hash"):
        raise SyntheticContractError("VERSION_MIGRATION_NOT_REVIEWED")


def validate_input_path(path: str) -> None:
    if not path.startswith("/tmp/") or "SYNTHETIC_" not in path:
        raise SyntheticContractError("REAL_PATH_REJECTED")


def synthetic_absence_mapping(record: Mapping[str, Any]) -> dict[str, Any]:
    result = validate_record(record)
    if result["status"] != "confirmed_absent":
        raise SyntheticContractError("MAPPING_REQUIRES_CONFIRMED_ABSENT")
    return {"missing_flag": True, "absence_evidence_id": "SYNTHETIC_EVIDENCE_001", "status": "confirmed_absent", "numeric_value": None}
