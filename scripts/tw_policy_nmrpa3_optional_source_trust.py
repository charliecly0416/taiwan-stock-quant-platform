#!/usr/bin/env python3
"""Independent validator for the synthetic optional-source trust substrate.

This module deliberately validates only bootstrap control JSON. It never opens
provider files or institutional/margin payloads.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import PurePosixPath
from typing import Any

BASE = "data_tw/artifacts/research/nmrpa/optional_source_trust_v1"
PROFILE = "nmrpa.institutional_margin.optional_daily.v1"
NAMESPACE = "independent_optional_source_daily_binding_v1"
LOG_ID = "nmrpa.optional_source_binding_log.v1"
SHA = re.compile(r"^[0-9a-f]{64}$")
FORBIDDEN = ("target", "date", "payload", "binding", "credential", "authorization", "anchor", "capture", "sealed", "post_genesis", "evidence")


class OptionalSourceValidationError(ValueError):
    pass


def _require_exact_json_types(value: Any, where: str) -> None:
    """Reject Python subclasses before any value or digest comparison."""
    value_type = type(value)
    if value_type is dict:
        for key, child in value.items():
            if type(key) is not str:
                raise OptionalSourceValidationError(f"{where}: object key must be exact str")
            _require_exact_json_types(child, f"{where}.{key}")
        return
    if value_type is list:
        for index, child in enumerate(value):
            _require_exact_json_types(child, f"{where}[{index}]")
        return
    if value_type is float:
        if not math.isfinite(value):
            raise OptionalSourceValidationError(f"{where}: non-finite number")
        return
    if value_type in {str, int, bool} or value is None:
        return
    raise OptionalSourceValidationError(f"{where}: non-exact JSON type {value_type.__name__}")


def canonical_json(value: Any) -> bytes:
    _require_exact_json_types(value, "canonical_json")
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value: Any, domain: str) -> str:
    return hashlib.sha256(domain.encode() + b"\n" + canonical_json(value)).hexdigest()


def _object(value: Any, keys: set[str], where: str) -> None:
    if type(value) is not dict or set(value) != keys:
        raise OptionalSourceValidationError(f"{where}: closed object mismatch")


def _str(value: Any, expected: str | None, where: str) -> None:
    if type(value) is not str or expected is not None and value != expected:
        raise OptionalSourceValidationError(f"{where}: exact string mismatch")


def _bool(value: Any, expected: bool, where: str) -> None:
    if type(value) is not bool or value is not expected:
        raise OptionalSourceValidationError(f"{where}: exact bool mismatch")


def _none(value: Any, where: str) -> None:
    if value is not None:
        raise OptionalSourceValidationError(f"{where}: must be null")


def _sha(value: Any, where: str) -> None:
    if type(value) is not str or not SHA.fullmatch(value):
        raise OptionalSourceValidationError(f"{where}: invalid sha256")


def _path(value: Any, expected: str, where: str) -> None:
    _str(value, expected, where)
    p = PurePosixPath(value)
    if p.is_absolute() or "\\" in value or any(part in {"", ".", ".."} for part in p.parts):
        raise OptionalSourceValidationError(f"{where}: unsafe path")


def descriptor() -> dict[str, Any]:
    return {
        "schema_version": "nmrpa.optional_source_trust_descriptor.v1",
        "namespace": NAMESPACE,
        "profile_id": PROFILE,
        "profile_roles": {"institutional": "institutional_source_profile", "margin": "margin_source_profile"},
        "source_kinds": ["institutional", "margin"],
        "decision_timezone": "Asia/Taipei",
        "pit_policy_id": "nmrpa.optional_source.pit_cutoff.asia_taipei.v1",
        "status": "bootstrap_genesis_only",
        "payload_evidence_state": "not_bound",
        "real_payload_read": False,
        "target_asof": None,
        "future_companion_paths": {
            "request_scope_store": f"{BASE}/stores/optional_source_profile_registry/",
            "authorization_store": f"{BASE}/stores/authorization_ledger/",
            "anchor_store": f"{BASE}/stores/anchor_ledger/",
            "binding_store": f"{BASE}/stores/binding_store/",
            "capture_store": f"{BASE}/stores/capture_attempt_store/",
            "response_evidence_store": f"{BASE}/stores/response_evidence_store/",
            "sealed_object_store": f"{BASE}/stores/sealed_object_store/",
        },
        "parent_binding_ref": {"kind": "five_root_binding", "mode": "one_way_reference_only", "value": "not_bound"},
        "forbidden_in_bootstrap": ["payload", "credential", "authorization", "anchor", "binding", "capture", "sealed_evidence", "post_genesis_record", "latest", "cron"],
    }


def _reject_forbidden_keys(value: Any, where: str = "root") -> None:
    if type(value) is dict:
        if where == "root.future_companion_paths" or where == "root.parent_binding_ref":
            return
        for key, child in value.items():
            # The descriptor's explicitly frozen control names are allowed; all
            # evidence-shaped names are rejected outside that exact contract.
            if key in {"payload_evidence_state", "real_payload_read", "target_asof", "future_companion_paths", "parent_binding_ref", "forbidden_in_bootstrap"}:
                _reject_forbidden_keys(child, f"{where}.{key}")
            elif any(token in key.casefold() for token in FORBIDDEN) and key not in {"payload_evidence_state"}:
                raise OptionalSourceValidationError(f"{where}.{key}: forbidden field")
            else:
                _reject_forbidden_keys(child, f"{where}.{key}")
    elif type(value) is list:
        for i, child in enumerate(value):
            _reject_forbidden_keys(child, f"{where}[{i}]")


def validate_descriptor(value: Any) -> dict[str, Any]:
    _require_exact_json_types(value, "descriptor")
    expected = descriptor()
    _object(value, set(expected) | {"descriptor_sha256"}, "descriptor")
    _reject_forbidden_keys(value)
    for key, expected_value in expected.items():
        if key == "descriptor_sha256":
            continue
        if value[key] != expected_value or type(value[key]) is not type(expected_value):
            raise OptionalSourceValidationError(f"descriptor.{key}: frozen value mismatch")
    # The bootstrap writer calculates the digest before adding this field.
    _sha(value.get("descriptor_sha256"), "descriptor.descriptor_sha256")
    if value["descriptor_sha256"] != digest({k: v for k, v in value.items() if k != "descriptor_sha256"}, "nmrpa.optional_source.trust.descriptor.v1"):
        raise OptionalSourceValidationError("descriptor digest mismatch")
    return {"ok": True, "artifact": "descriptor", "payload_evidence_state": "not_bound"}


def validate_genesis(value: Any) -> dict[str, Any]:
    _require_exact_json_types(value, "genesis")
    keys = {"schema_version", "log_id", "sequence", "previous_head_sha256", "profile_id", "state", "payload_evidence_state", "real_payload_read", "genesis_sha256"}
    _object(value, keys, "genesis")
    _str(value["schema_version"], "nmrpa.optional_source.binding_log_genesis.v1", "genesis.schema_version")
    _str(value["log_id"], LOG_ID, "genesis.log_id"); _str(value["profile_id"], PROFILE, "genesis.profile_id")
    if type(value["sequence"]) is not int or value["sequence"] != 0: raise OptionalSourceValidationError("genesis.sequence")
    _none(value["previous_head_sha256"], "genesis.previous_head_sha256"); _str(value["state"], "genesis_only", "genesis.state")
    _str(value["payload_evidence_state"], "not_bound", "genesis.payload_evidence_state"); _bool(value["real_payload_read"], False, "genesis.real_payload_read")
    _sha(value["genesis_sha256"], "genesis.genesis_sha256")
    expected = {k: v for k, v in value.items() if k != "genesis_sha256"}
    if value["genesis_sha256"] != digest(expected, "nmrpa.optional_source.binding.genesis.v1"): raise OptionalSourceValidationError("genesis digest")
    return {"ok": True, "artifact": "genesis", "sequence": 0}


def validate_head(value: Any, genesis_sha256: str) -> dict[str, Any]:
    _require_exact_json_types(value, "head")
    _require_exact_json_types(genesis_sha256, "genesis_sha256")
    keys = {"schema_version", "log_id", "sequence", "previous_head_sha256", "record_sha256", "head_sha256"}; _object(value, keys, "head")
    _str(value["schema_version"], "nmrpa.optional_source.binding_log_head.v1", "head.schema_version"); _str(value["log_id"], LOG_ID, "head.log_id")
    if type(value["sequence"]) is not int or value["sequence"] != 0: raise OptionalSourceValidationError("head.sequence")
    _none(value["previous_head_sha256"], "head.previous_head_sha256"); _sha(value["record_sha256"], "head.record_sha256")
    if value["record_sha256"] != genesis_sha256: raise OptionalSourceValidationError("head record link")
    _sha(value["head_sha256"], "head.head_sha256")
    if value["head_sha256"] != digest({k: v for k, v in value.items() if k != "head_sha256"}, "nmrpa.optional_source.binding.head.v1"): raise OptionalSourceValidationError("head digest")
    return {"ok": True, "artifact": "head", "sequence": 0}


def validate_history(value: Any, head: dict[str, Any]) -> dict[str, Any]:
    _require_exact_json_types(value, "historical_heads")
    _require_exact_json_types(head, "expected_head")
    keys = {"schema_version", "log_id", "heads", "state"}; _object(value, keys, "historical_heads")
    _str(value["schema_version"], "nmrpa.optional_source.binding_log_history.v1", "history.schema_version"); _str(value["log_id"], LOG_ID, "history.log_id")
    _str(value["state"], "genesis_only", "history.state")
    if type(value["heads"]) is not list or len(value["heads"]) != 1 or type(value["heads"][0]) is not dict: raise OptionalSourceValidationError("history.heads")
    if value["heads"][0] != head or type(value["heads"][0]["sequence"]) is not int: raise OptionalSourceValidationError("history head mismatch")
    return {"ok": True, "artifact": "historical_heads", "sequence": 0}


def validate_config(value: Any) -> dict[str, Any]:
    _require_exact_json_types(value, "config")
    keys = {"schema_version", "descriptor_path", "namespace", "profile_id", "activation", "payload_read_allowed", "target_asof"}; _object(value, keys, "config")
    _str(value["schema_version"], "nmrpa.optional_source.config.v1", "config.schema_version"); _path(value["descriptor_path"], f"{BASE}/descriptor.json", "config.descriptor_path")
    _str(value["namespace"], NAMESPACE, "config.namespace"); _str(value["profile_id"], PROFILE, "config.profile_id"); _str(value["activation"], "bootstrap_only", "config.activation"); _bool(value["payload_read_allowed"], False, "config.payload_read_allowed"); _none(value["target_asof"], "config.target_asof")
    return {"ok": True, "artifact": "config", "payload_evidence_state": "not_bound"}


def validate_package(descriptor_value: Any, genesis: Any, head: Any, history: Any, config: Any) -> dict[str, Any]:
    for where, value in (
        ("descriptor", descriptor_value),
        ("genesis", genesis),
        ("head", head),
        ("historical_heads", history),
        ("config", config),
    ):
        _require_exact_json_types(value, where)
    validate_descriptor(descriptor_value); validate_genesis(genesis); validate_head(head, genesis["genesis_sha256"]); validate_history(history, head); validate_config(config)
    return {"ok": True, "sequence": 0, "payload_evidence_state": "not_bound", "real_payload_read": False}
