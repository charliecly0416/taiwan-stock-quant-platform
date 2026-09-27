#!/usr/bin/env python3
"""Synthetic-only source-to-absence integration harness for MBOOS2_V."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

import synthetic_mboos2_u_r_structural_absence_validator as absence

ADAPTER_SCHEMA_VERSION = "SYNTHETIC_MBOOS2_V_SOURCE_ADAPTER_V1"
SOURCE_STATE_TO_STATUS = {
    "SYNTHETIC_SOURCE_COVERAGE_UNKNOWN": "unknown_source_coverage",
    "SYNTHETIC_SOURCE_CONFIRMED_ABSENT": "confirmed_absent",
    "SYNTHETIC_SOURCE_PRESENT": "present",
    "SYNTHETIC_SOURCE_SCOPE_INCOMPLETE": "scope_incomplete",
    "SYNTHETIC_SOURCE_ACCESS_FAILED": "access_failed",
    "SYNTHETIC_SOURCE_STALE": "stale",
    "SYNTHETIC_SOURCE_CONFLICTING": "conflicting",
}
UNRESOLVED_STATUSES = frozenset({
    "unknown_source_coverage",
    "scope_incomplete",
    "access_failed",
    "stale",
    "conflicting",
})


class SyntheticIntegrationError(absence.SyntheticContractError):
    pass


def _require_exact_fields(value: Mapping[str, Any], expected: set[str]) -> None:
    if set(value) != expected:
        raise SyntheticIntegrationError("ADAPTER_ENVELOPE_FIELDS_INVALID")


def adapt_source_metadata(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Map one synthetic source envelope through the absence validator."""
    if not isinstance(envelope, Mapping):
        raise SyntheticIntegrationError("ADAPTER_ENVELOPE_OBJECT_REQUIRED")
    _require_exact_fields(
        envelope,
        {"adapter_schema_version", "adapter_id", "input_path", "source_state", "record"},
    )
    if envelope["adapter_schema_version"] != ADAPTER_SCHEMA_VERSION:
        raise SyntheticIntegrationError("ADAPTER_SCHEMA_VERSION_UNSUPPORTED")
    absence._synthetic(envelope["adapter_id"], "adapter_id")
    absence.validate_input_path(envelope["input_path"])
    absence._reject_real_payload_shape(envelope)

    source_state = envelope["source_state"]
    if source_state not in SOURCE_STATE_TO_STATUS:
        raise SyntheticIntegrationError("SOURCE_STATE_NOT_CLOSED")
    mapped_status = SOURCE_STATE_TO_STATUS[source_state]
    record = deepcopy(envelope["record"])
    if not isinstance(record, Mapping):
        raise SyntheticIntegrationError("SOURCE_RECORD_OBJECT_REQUIRED")
    if record.get("status") != mapped_status:
        raise SyntheticIntegrationError("SOURCE_STATE_STATUS_MISMATCH")

    validated = absence.validate_record(record)
    if validated["status"] == "confirmed_absent":
        mapped = absence.synthetic_absence_mapping(record)
        return {
            "status": validated["status"],
            "trainable": False,
            "neutral": True,
            "quarantine": False,
            "feature_value": mapped["numeric_value"],
            "record_sha256": validated["record_sha256"],
        }
    if validated["status"] == "present":
        return {
            "status": validated["status"],
            "trainable": True,
            "neutral": False,
            "quarantine": False,
            "feature_value": "SYNTHETIC_PRESENT_VALUE_BOUND_ELSEWHERE",
            "record_sha256": validated["record_sha256"],
        }
    if validated["status"] not in UNRESOLVED_STATUSES:
        raise SyntheticIntegrationError("UNMAPPED_VALIDATOR_STATUS")
    return {
        "status": validated["status"],
        "trainable": False,
        "neutral": False,
        "quarantine": True,
        "feature_value": None,
        "record_sha256": validated["record_sha256"],
    }


def validate_integrated_date(summary: Mapping[str, Any]) -> dict[str, Any]:
    """Validate date metadata and derive a fail-closed aggregate decision."""
    result = absence.validate_date_summary(summary)
    statuses = {record["status"] for record in summary.get("records", [])}
    unresolved = bool(statuses & UNRESOLVED_STATUSES)
    if unresolved and result["status"] not in {"invalid", "quarantined"}:
        raise SyntheticIntegrationError("UNRESOLVED_DATE_NOT_QUARANTINED")
    return {
        **result,
        "trainable": result["status"] in {"valid", "recovered"} and not unresolved,
        "quarantine": result["status"] in {"invalid", "quarantined"},
    }


def validate_integrated_recovery(old: Mapping[str, Any], new: Mapping[str, Any]) -> dict[str, Any]:
    absence.validate_recovery(old, new)
    result = validate_integrated_date(new)
    if not result["trainable"]:
        raise SyntheticIntegrationError("RECOVERY_NOT_TRAINABLE")
    return result
