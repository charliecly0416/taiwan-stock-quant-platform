#!/usr/bin/env python3
"""NMRPA3 isolated PriceStore/TWII source adapter contract.

The module has no filesystem source discovery and no runtime defaults.  It only
validates caller-injected synthetic objects against bootstrap-pinned identities.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import math
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator


SCHEMA_VERSION = "nmrpa.pricestore_twii_isolated.v1"
FIXTURE_MODE = "synthetic_injected_only"
ROOT_KINDS = (
    "sealed_calendar",
    "formal_instruments",
    "adjusted_price",
    "twii",
    "modela_signal",
)
FIXED_LOGS = {
    "principal_registry_log": ("issuer_registry", "nmrpa.principal_registry.v1"),
    "identity_registry_log": ("issuer_registry", "nmrpa.identity_registry.v1"),
    "credential_registry_log": ("issuer_registry", "nmrpa.credential_registry.v1"),
    "trusted_service_registration_log": ("issuer_registry", "nmrpa.trusted_service_registration.v1"),
    "publication_authority_registration_log": (
        "publication_authority_registry",
        "nmrpa.publication_authority_registration.v1",
    ),
    "capture_recorder_registration_log": (
        "capture_recorder_registry",
        "nmrpa.capture_recorder_registration.v1",
    ),
}
EVENTS = {
    "principal_registry_log": ("principal_registered", "principal_revoked"),
    "identity_registry_log": ("identity_registered", "identity_revoked"),
    "credential_registry_log": ("credential_registered", "credential_rotated", "credential_revoked"),
    "trusted_service_registration_log": (
        "service_registered", "service_log_scope_extended",
        "service_credential_rotated", "service_revoked",
    ),
    "publication_authority_registration_log": (
        "authority_registered", "authority_credential_rotated", "authority_revoked",
    ),
    "capture_recorder_registration_log": (
        "recorder_registered", "recorder_scope_extended",
        "recorder_credential_rotated", "recorder_revoked",
    ),
}
REGISTRATION_ROTATION_ROLES = {
    "service_credential_rotated": "service",
    "authority_credential_rotated": "authority",
    "recorder_credential_rotated": "recorder",
}
ROOT_LOCATORS = {
    kind: {
        "base_id": f"nmrpa.synthetic.base.{kind}.v1",
        "root_id": f"synthetic_{kind}_root_v1",
        "locator_token": f"SYNTHETIC_LOCATOR_{kind.upper()}",
    }
    for kind in ROOT_KINDS
}
TRUSTED_LOG_OWNER_ROLE = "trust_registry_issuer"
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
ID_RE = re.compile(r"^[a-z][a-z0-9_.-]{2,127}$")
SYNTHETIC_DATE_MIN = date(2099, 1, 1)
SYNTHETIC_DATE_MAX = date(2099, 12, 31)
DECISION_CUTOFF = "23:59:59+08:00"
CONTRACT_DIGEST_NAMES = (
    "feature_contract_sha256", "target_contract_sha256",
    "split_contract_sha256", "decision_time_policy_sha256",
)
PINNED_CONTRACT_DIGESTS = {
    name: digest_value
    for name, digest_value in (
        (name, hashlib.sha256(json.dumps(
            {"contract": name, "version": "frozen_v1"},
            sort_keys=True, separators=(",", ":"),
        ).encode()).hexdigest())
        for name in CONTRACT_DIGEST_NAMES
    )
}
REQUIRED_ROLES = {
    kind: frozenset({"normalized_payload", "publication_payload", "publication_record", "source_native_manifest"})
    for kind in ROOT_KINDS
}
REQUIRED_ROLES["adjusted_price"] = REQUIRED_ROLES["adjusted_price"] | {"tradability_payload"}
CAPTURE_ROLES = {
    kind: frozenset({"normalized_payload", "raw_response", "attempt_ledger", "source_native_manifest"})
    for kind in ROOT_KINDS
}
CAPTURE_ROLES["adjusted_price"] = CAPTURE_ROLES["adjusted_price"] | {"tradability_payload"}
FORBIDDEN_PATH_SEGMENTS = {"", ".", "..", "latest", "current", "accepted", "publish"}


class ContractError(ValueError):
    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def canonical_json(value: Any) -> bytes:
    def walk(item: Any) -> None:
        if isinstance(item, float) and not math.isfinite(item):
            raise ContractError("NMRPA_E_NONFINITE", "non-finite JSON number")
        if isinstance(item, dict):
            for key, child in item.items():
                if not isinstance(key, str) or unicodedata.normalize("NFC", key) != key:
                    raise ContractError("NMRPA_E_SCHEMA", "object keys must be NFC strings")
                walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)

    walk(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest(value: Any, domain: str | None = None) -> str:
    payload = canonical_json(value)
    if domain is not None:
        payload = (domain + "\n").encode() + payload
    return sha256_bytes(payload)


def checksum_without(value: Mapping[str, Any], field: str, domain: str | None = None) -> str:
    return digest({k: v for k, v in value.items() if k != field}, domain)


def exact(obj: Any, required: set[str], where: str) -> None:
    if not isinstance(obj, dict):
        raise ContractError("NMRPA_E_SCHEMA", f"{where} must be an object")
    keys = set(obj)
    if keys != required:
        raise ContractError("NMRPA_E_SCHEMA", f"{where} fields differ: missing={required-keys}, extra={keys-required}")


def require_sha(value: Any, where: str) -> None:
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise ContractError("NMRPA_E_SCHEMA", f"{where} must be lowercase sha256")


def parse_synthetic_date(value: str, where: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ContractError("NMRPA_E_SCHEMA", f"invalid {where}") from exc
    if not SYNTHETIC_DATE_MIN <= parsed <= SYNTHETIC_DATE_MAX:
        raise ContractError("NMRPA_E_REAL_INPUT", f"{where} is outside reserved synthetic year 2099")
    return parsed


def parse_time(value: str, where: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ContractError("NMRPA_E_SCHEMA", f"invalid {where}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ContractError("NMRPA_E_SCHEMA", f"invalid {where}") from exc
    if parsed.tzinfo is None or parsed.microsecond:
        raise ContractError("NMRPA_E_SCHEMA", f"{where} must be timezone-aware at whole-second precision")
    return parsed


def synthetic_trading_dates(end: date, count: int) -> list[str]:
    rows: list[str] = []
    cursor = end
    while len(rows) < count:
        if cursor.weekday() < 5:
            rows.append(cursor.isoformat())
        cursor -= timedelta(days=1)
    return list(reversed(rows))


@dataclass(frozen=True)
class PinnedTrust:
    bootstrap_sha256: str
    fixed_log_heads: Mapping[str, Mapping[str, Any]]
    contract_digests: Mapping[str, str]
    authorization_sha256: str
    anchor_sha256: str


@dataclass(frozen=True)
class InjectedObjectStore:
    """Explicit byte store; tokens are opaque and never interpreted as paths."""

    objects: Mapping[str, bytes]
    pinned_trust: PinnedTrust | None = None

    def __post_init__(self) -> None:
        for token, value in self.objects.items():
            if not token.startswith("SYNTHETIC_OBJECT_") or not isinstance(value, bytes):
                raise ContractError("NMRPA_E_REAL_INPUT", "only synthetic byte tokens are accepted")

    def get(self, token: str) -> bytes:
        try:
            return self.objects[token]
        except KeyError as exc:
            raise ContractError("NMRPA_E_OBJECT_SELECTOR", f"missing injected object {token}") from exc


TOP_LEVEL_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "nmrpa.pricestore_twii_isolated.v1",
    "x-runtime-exact-schema-registry": {
        "validator": "tw_policy_nmrpa3_source_adapter.validate_package",
        "recursive": True,
        "closed_domains": [
            "bootstrap", "governance_logs", "source_roots", "pit_bindings",
            "calendar", "formal_instruments", "modela_rows", "price_rows",
            "twii_rows", "binding", "authorization", "anchor",
        ],
    },
    "type": "object",
    "additionalProperties": False,
    "required": [
        "schema_version", "fixture_mode", "target_asof", "runtime_overrides",
        "bootstrap", "governance_logs", "source_roots", "pit_bindings",
        "calendar", "formal_instruments", "modela_rows", "price_rows",
        "twii_rows", "binding", "authorization", "anchor",
    ],
    "properties": {
        "schema_version": {"const": SCHEMA_VERSION},
        "fixture_mode": {"const": FIXTURE_MODE},
        "target_asof": {"type": "string", "format": "date"},
        "runtime_overrides": {"type": "object", "maxProperties": 0},
        "bootstrap": {"type": "object"},
        "governance_logs": {"type": "object"},
        "source_roots": {"type": "array", "minItems": 5, "maxItems": 5},
        "pit_bindings": {"type": "array", "minItems": 5},
        "calendar": {"type": "object"},
        "formal_instruments": {"type": "array", "minItems": 1},
        "modela_rows": {"type": "array", "minItems": 1},
        "price_rows": {"type": "array", "minItems": 1},
        "twii_rows": {"type": "array", "minItems": 60},
        "binding": {"type": "object"},
        "authorization": {"type": "object"},
        "anchor": {"type": "object"},
    },
}


def _require_string(value: Any, where: str, *, nullable: bool = False) -> None:
    if nullable and value is None:
        return
    if not isinstance(value, str) or not value:
        raise ContractError("NMRPA_E_SCHEMA", f"{where} must be a non-empty string")


def _require_id(value: Any, where: str) -> None:
    _require_string(value, where)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*(?:_[A-Za-z0-9_.-]+)*", value):
        raise ContractError("NMRPA_E_SCHEMA", f"{where} has invalid ID grammar")


def _require_sequence(value: Any, where: str, *, expected: int | None = None) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ContractError("NMRPA_E_SCHEMA", f"{where} must be a positive integer")
    if expected is not None and value != expected:
        raise ContractError("NMRPA_E_LEDGER_CHAIN", f"{where} is not contiguous")


def _require_sorted_strings(value: Any, where: str, *, allow_empty: bool = False) -> None:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ContractError("NMRPA_E_SCHEMA", f"{where} must be a string array")
    if (not allow_empty and not value) or value != sorted(set(value)):
        raise ContractError("NMRPA_E_SCHEMA", f"{where} must be sorted and unique")


def _require_nullable_sha(value: Any, where: str) -> None:
    if value is not None:
        require_sha(value, where)


def _require_number(value: Any, where: str, *, nullable: bool = False) -> None:
    if nullable and value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ContractError("NMRPA_E_SCHEMA", f"{where} must be a finite number")


def _validate_calendar(value: Any) -> None:
    exact(value, {"calendar_id", "genesis_policy_id", "target_asof", "ordered_dates", "calendar_prefix_sha256"}, "calendar")
    for key in ("calendar_id", "genesis_policy_id", "target_asof"):
        _require_string(value[key], f"calendar.{key}")
    if not isinstance(value["ordered_dates"], list) or not all(isinstance(item, str) for item in value["ordered_dates"]):
        raise ContractError("NMRPA_E_SCHEMA", "calendar.ordered_dates must be string array")
    require_sha(value["calendar_prefix_sha256"], "calendar.calendar_prefix_sha256")


def _validate_formal_row(row: Any) -> None:
    exact(row, {"instrument", "effective_start", "effective_end", "row_sha256"}, "formal instrument")
    _require_string(row["instrument"], "formal.instrument")
    parse_synthetic_date(row["effective_start"], "effective_start")
    if row["effective_end"] is not None:
        parse_synthetic_date(row["effective_end"], "effective_end")
        if row["effective_end"] < row["effective_start"]:
            raise ContractError("NMRPA_E_FORMAL_ACTIVE", "formal interval ends before start")
    require_sha(row["row_sha256"], "formal.row_sha256")


def _validate_modela_row(row: Any) -> None:
    exact(row, {"instrument", "signal_asof", "source_asof", "available_at", "availability_evidence_id", "raw_score", "row_sha256"}, "Model A row")
    for key in ("instrument", "signal_asof", "source_asof", "available_at", "availability_evidence_id"):
        _require_string(row[key], f"modela.{key}")
    parse_synthetic_date(row["signal_asof"], "modela signal_asof")
    parse_synthetic_date(row["source_asof"], "modela source_asof")
    parse_time(row["available_at"], "modela available_at")
    _require_number(row["raw_score"], "modela.raw_score")
    require_sha(row["row_sha256"], "modela.row_sha256")
    if row["row_sha256"] != checksum_without(row, "row_sha256"):
        raise ContractError("NMRPA_E_DIGEST", "Model A row digest mismatch")


def _validate_twii_row(row: Any) -> None:
    exact(row, {"date", "source_asof", "available_at", "availability_evidence_id", "close", "row_sha256"}, "TWII row")
    parse_synthetic_date(row["date"], "TWII date")
    parse_synthetic_date(row["source_asof"], "TWII source_asof")
    parse_time(row["available_at"], "TWII available_at")
    _require_string(row["availability_evidence_id"], "TWII availability_evidence_id")
    _require_number(row["close"], "TWII close")
    if row["close"] <= 0 or row["row_sha256"] != checksum_without(row, "row_sha256"):
        raise ContractError("NMRPA_E_DIGEST", "TWII row invalid")


def _validate_normalized_rows(kind: str, rows: Any) -> None:
    if kind == "sealed_calendar":
        _validate_calendar(rows)
        return
    if not isinstance(rows, list) or not rows:
        raise ContractError("NMRPA_E_SCHEMA", f"{kind} rows must be a non-empty array")
    validator = {
        "formal_instruments": _validate_formal_row,
        "adjusted_price": validate_price_row,
        "twii": _validate_twii_row,
        "modela_signal": _validate_modela_row,
    }[kind]
    for row in rows:
        validator(row)


def _validate_selected_object(kind: str, role: str, obj: Any) -> None:
    if role in ("normalized_payload", "publication_payload", "raw_response"):
        exact(obj, {"source_id", "source_asof", "rows"}, f"{role} object")
        _require_string(obj["source_id"], f"{role}.source_id")
        parse_synthetic_date(obj["source_asof"], f"{role}.source_asof")
        _validate_normalized_rows(kind, obj["rows"])
    elif role == "publication_record":
        exact(obj, {"authority_id", "publication_record_id", "published_at", "source_asof", "source_id", "payload_sha256"}, "publication record")
        for key in ("authority_id", "publication_record_id", "source_id"):
            _require_string(obj[key], f"publication_record.{key}")
        parse_time(obj["published_at"], "publication_record.published_at")
        parse_synthetic_date(obj["source_asof"], "publication_record.source_asof")
        require_sha(obj["payload_sha256"], "publication_record.payload_sha256")
    elif role == "source_native_manifest":
        exact(obj, {"source_run_id", "target_asof", "source_id"}, "source manifest")
        for key in ("source_run_id", "source_id"):
            _require_string(obj[key], f"source_manifest.{key}")
        parse_synthetic_date(obj["target_asof"], "source manifest target_asof")
    elif role == "attempt_ledger":
        exact(obj, {"recorder_id", "source_id", "ordered_attempts"}, "attempt ledger")
        _require_string(obj["recorder_id"], "attempt_ledger.recorder_id")
        _require_string(obj["source_id"], "attempt_ledger.source_id")
        if not isinstance(obj["ordered_attempts"], list) or not obj["ordered_attempts"]:
            raise ContractError("NMRPA_E_SCHEMA", "attempt ledger must contain attempts")
    elif role == "tradability_payload":
        exact(obj, {"source_id", "source_asof", "explicit_non_trade"}, "tradability payload")
        _require_string(obj["source_id"], "tradability.source_id")
        parse_synthetic_date(obj["source_asof"], "tradability.source_asof")
        if not isinstance(obj["explicit_non_trade"], list):
            raise ContractError("NMRPA_E_SCHEMA", "tradability explicit_non_trade must be array")
    else:
        raise ContractError("NMRPA_E_INVENTORY", f"unknown file role {role}")


def _member_object(member: Mapping[str, Any], store: InjectedObjectStore) -> Any:
    exact(member, {
        "member_id", "root_kind", "root_id", "file_role", "relative_path", "file_type",
        "media_type", "object_token", "byte_size", "bytes_sha256", "ordered_objects",
        "object_index_sha256",
    }, "inventory member")
    path = member["relative_path"]
    if not isinstance(path, str) or path.startswith("/") or "\\" in path or unicodedata.normalize("NFC", path) != path:
        raise ContractError("NMRPA_E_ROOT_ALIAS", "unsafe relative path")
    segments = path.split("/")
    if any(segment.casefold() in FORBIDDEN_PATH_SEGMENTS for segment in segments):
        raise ContractError("NMRPA_E_ROOT_ALIAS", "unsafe relative path")
    raw = store.get(member["object_token"])
    if len(raw) != member["byte_size"] or sha256_bytes(raw) != member["bytes_sha256"]:
        raise ContractError("NMRPA_E_INVENTORY_BYTES", "injected bytes do not match inventory")
    objects = member["ordered_objects"]
    if not isinstance(objects, list) or len(objects) != 1:
        raise ContractError("NMRPA_E_OBJECT_SELECTOR", "isolated member requires one whole-document object")
    obj_ref = objects[0]
    exact(obj_ref, {"object_id", "selector", "canonical_schema_id", "canonical_object_sha256"}, "object member")
    if obj_ref["selector"] != {"selector_type": "whole_document"}:
        raise ContractError("NMRPA_E_OBJECT_SELECTOR", "only exact whole-document selector is implemented")
    try:
        selected = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("NMRPA_E_OBJECT_SELECTOR", "invalid canonical JSON bytes") from exc
    if canonical_json(selected) != raw or digest(selected) != obj_ref["canonical_object_sha256"]:
        raise ContractError("NMRPA_E_OBJECT_SELECTOR", "canonical object mismatch")
    index_obj = {"schema_version": "nmrpa.object_index.v1", "member_id": member["member_id"], "ordered_objects": objects}
    if digest(index_obj) != member["object_index_sha256"]:
        raise ContractError("NMRPA_E_OBJECT_SELECTOR", "object index mismatch")
    expected_schema_id = f"nmrpa.synthetic.{member['file_role']}.v1"
    if obj_ref["canonical_schema_id"] != expected_schema_id:
        raise ContractError("NMRPA_E_SCHEMA", "canonical schema ID is not bootstrap-pinned")
    _validate_selected_object(member["root_kind"], member["file_role"], selected)
    return selected


def validate_source_roots(package: Mapping[str, Any], store: InjectedObjectStore) -> dict[str, dict[str, Any]]:
    roots = package["source_roots"]
    if [root.get("root_kind") for root in roots] != list(ROOT_KINDS):
        raise ContractError("NMRPA_E_ROOT_LOCATOR_MISMATCH", "five roots must use fixed order")
    selected: dict[str, dict[str, Any]] = {}
    seen_tokens: set[str] = set()
    for root in roots:
        exact(root, {
            "schema_version", "root_kind", "root_id", "base_id", "locator_token",
            "ordered_members", "member_count", "root_inventory_sha256",
        }, "root inventory")
        kind = root["root_kind"]
        pin = ROOT_LOCATORS[kind]
        for field in ("root_id", "base_id", "locator_token"):
            if root[field] != pin[field]:
                raise ContractError("NMRPA_E_TRUSTED_BASE_MISMATCH", f"{kind} {field} override")
        if root["schema_version"] != "nmrpa.root_inventory.v3":
            raise ContractError("NMRPA_E_SCHEMA", "root schema version mismatch")
        members = root["ordered_members"]
        if not isinstance(members, list):
            raise ContractError("NMRPA_E_SCHEMA", "ordered_members must be an array")
        if root["member_count"] != len(members) or members != sorted(members, key=lambda x: x["relative_path"].encode()):
            raise ContractError("NMRPA_E_INVENTORY", "inventory count/order mismatch")
        roles = [member.get("file_role") for member in members]
        role_set = set(roles)
        if role_set not in (set(REQUIRED_ROLES[kind]), set(CAPTURE_ROLES[kind])) or len(roles) != len(role_set):
            raise ContractError("NMRPA_E_INVENTORY", f"{kind} required role/cardinality mismatch")
        paths = [m["relative_path"].casefold() for m in members]
        if len(paths) != len(set(paths)):
            raise ContractError("NMRPA_E_ROOT_ALIAS", "case-folded path alias")
        for member in members:
            if member["root_kind"] != kind or member["root_id"] != root["root_id"]:
                raise ContractError("NMRPA_E_ROOT_LOCATOR_MISMATCH", "member root mismatch")
            if member["file_type"] != "json" or member["media_type"] != "application/json":
                raise ContractError("NMRPA_E_SCHEMA", "member media/file type mismatch")
            if member["member_id"] in selected:
                raise ContractError("NMRPA_E_ROOT_ALIAS", "duplicate member ID")
            if member["object_token"] in seen_tokens:
                raise ContractError("NMRPA_E_ROOT_ALIAS", "cross-root object token reuse")
            seen_tokens.add(member["object_token"])
            selected[member["member_id"]] = {"member": member, "object": _member_object(member, store), "root_kind": kind}
        expected = checksum_without(root, "root_inventory_sha256")
        if root["root_inventory_sha256"] != expected:
            raise ContractError("NMRPA_E_INVENTORY", "root inventory digest mismatch")
    if set(store.objects) != seen_tokens:
        raise ContractError("NMRPA_E_INVENTORY", "unreferenced injected object")
    return selected


def validate_normalized_views(package: Mapping[str, Any], selected: Mapping[str, dict[str, Any]]) -> dict[str, str]:
    package_fields = {
        "sealed_calendar": "calendar",
        "formal_instruments": "formal_instruments",
        "adjusted_price": "price_rows",
        "twii": "twii_rows",
        "modela_signal": "modela_rows",
    }
    payload_digests: dict[str, str] = {}
    for kind, field in package_fields.items():
        payload = _selected_by_role(selected, kind, "normalized_payload")["object"]
        if package[field] != payload["rows"]:
            raise ContractError("NMRPA_E_NORMALIZED_VIEW", f"package {field} differs from selected inventory bytes")
        payload_digests[f"{kind}_payload_sha256"] = digest(payload)
    return payload_digests


def _validate_evidence_ref(ref: Mapping[str, Any], selected: Mapping[str, dict[str, Any]], root_kind: str, expected_role: str | None = None) -> None:
    exact(ref, {"member_id", "bytes_sha256", "object_id", "canonical_object_sha256"}, "evidence ref")
    if ref["member_id"] not in selected:
        raise ContractError("NMRPA_E_OBJECT_SELECTOR", "unknown evidence member")
    hit = selected[ref["member_id"]]
    obj_ref = hit["member"]["ordered_objects"][0]
    if hit["root_kind"] != root_kind or (expected_role is not None and hit["member"]["file_role"] != expected_role) or ref["bytes_sha256"] != hit["member"]["bytes_sha256"] or ref["object_id"] != obj_ref["object_id"] or ref["canonical_object_sha256"] != obj_ref["canonical_object_sha256"]:
        raise ContractError("NMRPA_E_CROSS_BINDING", "evidence ref does not bind unique member/object")


def _selected_by_role(selected: Mapping[str, dict[str, Any]], kind: str, role: str) -> dict[str, Any]:
    hits = [hit for hit in selected.values() if hit["root_kind"] == kind and hit["member"]["file_role"] == role]
    if len(hits) != 1:
        raise ContractError("NMRPA_E_INVENTORY", f"{kind}/{role} cardinality mismatch")
    return hits[0]


def validate_pit(package: Mapping[str, Any], selected: Mapping[str, dict[str, Any]], governance: Mapping[str, Any]) -> None:
    target = parse_synthetic_date(package["target_asof"], "target_asof")
    cutoff = datetime.fromisoformat(f"{target.isoformat()}T{DECISION_CUTOFF}").astimezone(timezone.utc)
    seen_rows: set[str] = set()
    evidence_by_id: dict[str, Mapping[str, Any]] = {}
    for evidence in package["pit_bindings"]:
        common = {
            "schema_version", "evidence_id", "evidence_type", "root_kind", "root_id", "source_id",
            "requested_source_asof", "referenced_row_keys", "available_at", "evidence_sha256",
        }
        if evidence.get("evidence_type") == "trusted_publication":
            required = common | {"authority_id", "publication_record_id", "published_source_asof", "published_at", "publication_payload_ref", "publication_record_ref"}
        elif evidence.get("evidence_type") == "first_successful_capture":
            required = common | {"capture_run_id", "request_identity", "request_identity_sha256", "attempt_ledger_ref", "ordered_attempts", "first_success_attempt_id", "first_successful_capture_at", "first_success_raw_response_ref"}
        else:
            raise ContractError("NMRPA_E_EVIDENCE_TYPE", "unknown PIT evidence variant")
        exact(evidence, required, "PIT evidence")
        for key in ("schema_version", "evidence_id", "evidence_type", "root_kind", "root_id", "source_id"):
            _require_string(evidence[key], f"evidence.{key}")
        if evidence["evidence_id"] in evidence_by_id:
            raise ContractError("NMRPA_E_EVIDENCE_SHARING", "duplicate PIT evidence ID")
        evidence_by_id[evidence["evidence_id"]] = evidence
        parse_synthetic_date(evidence["requested_source_asof"], "source_asof")
        available = parse_time(evidence["available_at"], "available_at")
        if available > cutoff:
            raise ContractError("NMRPA_E_PIT", "evidence arrives after decision cutoff")
        keys = evidence["referenced_row_keys"]
        if keys != sorted(set(keys)) or any(key in seen_rows for key in keys):
            raise ContractError("NMRPA_E_EVIDENCE_SHARING", "row evidence coverage must be exact and unique")
        seen_rows.update(keys)
        kind = evidence["root_kind"]
        if kind not in ROOT_KINDS:
            raise ContractError("NMRPA_E_ROOT_LOCATOR_MISMATCH", "unknown PIT root kind")
        if evidence["root_id"] != ROOT_LOCATORS[kind]["root_id"]:
            raise ContractError("NMRPA_E_ROOT_LOCATOR_MISMATCH", "PIT root mismatch")
        normalized = _selected_by_role(selected, kind, "normalized_payload")["object"]
        if evidence["source_id"] != normalized["source_id"] or evidence["requested_source_asof"] != normalized["source_asof"]:
            raise ContractError("NMRPA_E_SOURCE_ASOF", "PIT source does not bind normalized bytes")
        if evidence["evidence_type"] == "trusted_publication":
            if not (evidence["requested_source_asof"] == evidence["published_source_asof"]):
                raise ContractError("NMRPA_E_SOURCE_ASOF", "publication asof mismatch")
            if evidence["available_at"] != evidence["published_at"]:
                raise ContractError("NMRPA_E_PIT", "publication time mismatch")
            if evidence["publication_payload_ref"]["member_id"] == evidence["publication_record_ref"]["member_id"]:
                raise ContractError("NMRPA_E_PUBLICATION_CARDINALITY", "publication members must be distinct")
            _validate_evidence_ref(evidence["publication_payload_ref"], selected, kind, "publication_payload")
            _validate_evidence_ref(evidence["publication_record_ref"], selected, kind, "publication_record")
            publication_payload = _selected_by_role(selected, kind, "publication_payload")["object"]
            publication_record = _selected_by_role(selected, kind, "publication_record")["object"]
            if publication_payload != normalized:
                raise ContractError("NMRPA_E_CROSS_BINDING", "publication and normalized payload bytes differ")
            authority = governance["authorities"].get(evidence["authority_id"])
            if authority is None or authority["status"] != "active" or kind not in authority["state"]["scope"]:
                raise ContractError("NMRPA_E_PIT_AUTHORITY", "publication authority is not committed/active/in scope")
            expected_record = {
                "authority_id": evidence["authority_id"],
                "publication_record_id": evidence["publication_record_id"],
                "published_at": evidence["published_at"],
                "source_asof": evidence["published_source_asof"],
                "source_id": evidence["source_id"],
                "payload_sha256": digest(publication_payload),
            }
            if publication_record != expected_record:
                raise ContractError("NMRPA_E_PIT_AUTHORITY", "publication record bytes do not match evidence/source")
        else:
            request = evidence["request_identity"]
            exact(request, {"source_id", "endpoint_id", "method", "canonical_query", "requested_scope_id", "requested_source_asof", "request_contract_id"}, "request identity")
            for key in ("source_id", "endpoint_id", "method", "canonical_query", "requested_scope_id", "request_contract_id"):
                _require_string(request[key], f"request_identity.{key}")
            parse_synthetic_date(request["requested_source_asof"], "request_identity.requested_source_asof")
            require_sha(evidence["request_identity_sha256"], "evidence.request_identity_sha256")
            source_manifest = _selected_by_role(selected, kind, "source_native_manifest")["object"]
            attempt_object = _selected_by_role(selected, kind, "attempt_ledger")["object"]
            if (
                request["method"] not in ("GET", "POST")
                or request["source_id"] != evidence["source_id"]
                or request["source_id"] != source_manifest["source_id"]
                or request["source_id"] != attempt_object["source_id"]
                or request["requested_scope_id"] != kind
                or request["requested_source_asof"] != evidence["requested_source_asof"]
                or digest({"schema_version": "nmrpa.request_identity.v3", **request}) != evidence["request_identity_sha256"]
            ):
                raise ContractError("NMRPA_E_SOURCE_ASOF", "request identity mismatch")
            _validate_evidence_ref(evidence["attempt_ledger_ref"], selected, kind, "attempt_ledger")
            recorder = governance["recorders"].get("recorder_synthetic_capture")
            if recorder is None or recorder["status"] != "active" or "synthetic_capture" not in recorder["state"]["scope"]:
                raise ContractError("NMRPA_E_PIT_AUTHORITY", "capture recorder is not committed/active")
            attempts = evidence["ordered_attempts"]
            if not isinstance(attempts, list) or not attempts:
                raise ContractError("NMRPA_E_SCHEMA", "ordered attempts must be a non-empty array")
            if attempt_object["ordered_attempts"] != attempts or attempt_object["source_id"] != evidence["source_id"] or attempt_object["recorder_id"] != "recorder_synthetic_capture":
                raise ContractError("NMRPA_E_FIRST_SUCCESS_ORDER", "ordered attempts differ from selected ledger bytes")
            for attempt in attempts:
                expected_fields = {"attempt_id", "sequence", "request_identity_sha256", "started_at", "completed_at", "result_class", "response_bytes_present", "http_status", "raw_response_ref"}
                exact(attempt, expected_fields, "capture attempt")
                _require_id(attempt["attempt_id"], "attempt.attempt_id")
                _require_sequence(attempt["sequence"], "attempt.sequence")
                require_sha(attempt["request_identity_sha256"], "attempt.request_identity_sha256")
                if attempt["request_identity_sha256"] != evidence["request_identity_sha256"]:
                    raise ContractError("NMRPA_E_CAPTURE_REQUEST_BINDING", "attempt request digest differs from evidence")
                started = parse_time(attempt["started_at"], "attempt.started_at")
                completed = parse_time(attempt["completed_at"], "attempt.completed_at")
                if started > completed or completed > cutoff:
                    raise ContractError("NMRPA_E_CAPTURE_TIME", "attempt time order/cutoff invalid")
                if not isinstance(attempt["response_bytes_present"], bool):
                    raise ContractError("NMRPA_E_SCHEMA", "attempt.response_bytes_present must be bool")
                status = attempt["http_status"]
                if status is not None and (isinstance(status, bool) or not isinstance(status, int) or not 100 <= status <= 599):
                    raise ContractError("NMRPA_E_SCHEMA", "attempt.http_status must be null or an HTTP integer")
                _require_string(attempt["result_class"], "attempt.result_class")
                has_bytes = attempt["response_bytes_present"]
                if has_bytes != (attempt["raw_response_ref"] is not None):
                    raise ContractError("NMRPA_E_ATTEMPT_VARIANT", "capture bytes/ref mismatch")
                result_class = attempt["result_class"]
                response_results = {"authoritative_success", "authoritative_empty", "parse_failed", "stale", "zero_row_unproven"}
                no_response_results = {"access_failed", "auth_failed", "rate_limited", "timeout", "network_error", "not_run"}
                if result_class in response_results:
                    if not has_bytes or status is None or not 200 <= status <= 299:
                        raise ContractError("NMRPA_E_ATTEMPT_VARIANT", "response result requires 2xx bytes")
                elif result_class == "http_error":
                    if not has_bytes or status is None or status < 400:
                        raise ContractError("NMRPA_E_ATTEMPT_VARIANT", "HTTP error requires response bytes and 4xx/5xx status")
                elif result_class in no_response_results:
                    if has_bytes or status is not None:
                        raise ContractError("NMRPA_E_ATTEMPT_VARIANT", "transport/non-run result cannot claim response")
                else:
                    raise ContractError("NMRPA_E_ATTEMPT_VARIANT", "unknown capture result class")
                if has_bytes:
                    _validate_evidence_ref(attempt["raw_response_ref"], selected, kind, "raw_response")
            success = [i for i, row in enumerate(attempts) if row["result_class"] == "authoritative_success"]
            if success != [len(attempts) - 1] or [a["sequence"] for a in attempts] != list(range(1, len(attempts) + 1)):
                raise ContractError("NMRPA_E_FIRST_SUCCESS_ORDER", "first-success sequence invalid")
            chosen = attempts[-1]
            if chosen["attempt_id"] != evidence["first_success_attempt_id"] or chosen["completed_at"] != evidence["first_successful_capture_at"] or evidence["available_at"] != chosen["completed_at"] or chosen["raw_response_ref"] != evidence["first_success_raw_response_ref"]:
                raise ContractError("NMRPA_E_FIRST_SUCCESS_ORDER", "first-success cross-binding mismatch")
            selected_raw = _selected_by_role(selected, kind, "raw_response")["object"]
            if selected_raw != normalized or selected_raw["source_id"] != request["source_id"]:
                raise ContractError("NMRPA_E_CAPTURE_REQUEST_BINDING", "selected first-success bytes differ from normalized source")
        if checksum_without(evidence, "evidence_sha256") != evidence["evidence_sha256"]:
            raise ContractError("NMRPA_E_DIGEST", "PIT evidence digest mismatch")
    expected = set()
    expected.update(f"calendar:{d}" for d in package["calendar"]["ordered_dates"])
    expected.update(f"instrument:{r['instrument']}" for r in package["formal_instruments"])
    expected.update(f"modela:{r['instrument']}" for r in package["modela_rows"])
    expected.update(f"price:{r['date']}:{r['instrument']}" for r in package["price_rows"])
    expected.update(f"twii:{r['date']}" for r in package["twii_rows"])
    if seen_rows != expected:
        raise ContractError("NMRPA_E_EVIDENCE_SHARING", "PIT evidence does not cover every row exactly once")
    row_groups = (
        ("modela", package["modela_rows"], lambda row: f"modela:{row['instrument']}"),
        ("price", package["price_rows"], lambda row: f"price:{row['date']}:{row['instrument']}"),
        ("twii", package["twii_rows"], lambda row: f"twii:{row['date']}"),
    )
    for row_kind, rows, key_builder in row_groups:
        for row in rows:
            evidence = evidence_by_id.get(row["availability_evidence_id"])
            row_key = key_builder(row)
            if evidence is None or row_key not in evidence["referenced_row_keys"]:
                raise ContractError("NMRPA_E_ROW_PIT_BINDING", f"{row_kind} row lacks unique PIT evidence")
            row_available = parse_time(row["available_at"], f"{row_kind}.available_at")
            if row_available > cutoff:
                raise ContractError("NMRPA_E_ROW_PIT", f"{row_kind} row arrives after decision cutoff")
            if row["available_at"] != evidence["available_at"] or row["source_asof"] != evidence["requested_source_asof"]:
                raise ContractError("NMRPA_E_ROW_PIT_BINDING", f"{row_kind} row availability/source differs from evidence")


def _set_digest(kind: str, target: str, symbols: Sequence[str]) -> str:
    return digest({"schema_version": "nmrpa.symbol_set.v2", "set_kind": kind, "target_asof": target, "ordered_symbols": sorted(symbols)})


def validate_cross_section(package: Mapping[str, Any]) -> dict[str, str]:
    target = package["target_asof"]
    calendar = package["calendar"]
    exact(calendar, {"calendar_id", "genesis_policy_id", "target_asof", "ordered_dates", "calendar_prefix_sha256"}, "calendar")
    dates = calendar["ordered_dates"]
    if dates != sorted(set(dates)) or dates[-1] != target or len(dates) < 121:
        raise ContractError("NMRPA_E_CALENDAR", "calendar must be a unique 121+ prefix ending at target")
    for item in dates:
        parse_synthetic_date(item, "calendar date")
    expected_calendar_sha = digest({"schema_version": "nmrpa.calendar_prefix.v2", "calendar_id": calendar["calendar_id"], "genesis_policy_id": calendar["genesis_policy_id"], "target_asof": target, "ordered_dates": dates})
    if calendar["calendar_prefix_sha256"] != expected_calendar_sha:
        raise ContractError("NMRPA_E_CALENDAR", "calendar digest mismatch")
    instruments = package["formal_instruments"]
    symbols = [r.get("instrument") for r in instruments]
    if symbols != sorted(set(symbols)):
        raise ContractError("NMRPA_E_FORMAL_ACTIVE", "formal instruments duplicate/order mismatch")
    for row in instruments:
        _validate_formal_row(row)
        if row["row_sha256"] != checksum_without(row, "row_sha256"):
            raise ContractError("NMRPA_E_DIGEST", "instrument digest mismatch")
    active = [r["instrument"] for r in instruments if r["effective_start"] <= target and (r["effective_end"] is None or target <= r["effective_end"])]
    modela = package["modela_rows"]
    for row in modela:
        _validate_modela_row(row)
        if row["signal_asof"] != target or row["source_asof"] != target or row["availability_evidence_id"] != "evidence_modela_signal":
            raise ContractError("NMRPA_E_MODELA_ASOF", "Model A row asof/evidence mismatch")
    model_symbols = [r.get("instrument") for r in modela]
    if sorted(model_symbols) != active or len(model_symbols) != len(set(model_symbols)):
        raise ContractError("NMRPA_E_MISSING_MODELA", "Model A target set must equal formal active set")
    target_prices = [r for r in package["price_rows"] if r.get("date") == target]
    price_symbols = [r.get("instrument") for r in target_prices]
    if sorted(price_symbols) != active or len(price_symbols) != len(set(price_symbols)):
        raise ContractError("NMRPA_E_MISSING_PRICE", "price target set must equal formal active set")
    date_index = {value: i for i, value in enumerate(dates)}
    complete121: list[str] = []
    complete60: list[str] = []
    insufficient: list[str] = []
    not_tradable: list[str] = []
    by_symbol: dict[str, list[dict[str, Any]]] = {symbol: [] for symbol in active}
    for row in package["price_rows"]:
        validate_price_row(row)
        if row["instrument"] not in by_symbol:
            raise ContractError("NMRPA_E_FORMAL_ACTIVE", "price contains inactive/unknown instrument")
        if row["source_asof"] != target or row["availability_evidence_id"] != "evidence_adjusted_price":
            raise ContractError("NMRPA_E_SOURCE_ASOF", "price row asof/evidence mismatch")
        by_symbol[row["instrument"]].append(row)
    for instrument in instruments:
        symbol = instrument["instrument"]
        listed_dates = [d for d in dates if d >= instrument["effective_start"]]
        rows = by_symbol[symbol]
        keys = [(r["date"], r["instrument"]) for r in rows]
        if len(keys) != len(set(keys)) or sorted(r["date"] for r in rows) != listed_dates:
            raise ContractError("NMRPA_E_HISTORY_GRID", f"listed-period grid incomplete for {symbol}")
        rows_by_date = {row["date"]: row for row in rows}
        for index, listed_date in enumerate(listed_dates):
            row = rows_by_date[listed_date]
            if row["row_state"] == "explicit_non_trade":
                if index == 0 or row["carry_forward_source_row_sha256"] != rows_by_date[listed_dates[index - 1]]["normalized_row_sha256"]:
                    raise ContractError("NMRPA_E_PRICE_VARIANT", "non-trade carry-forward is not bound to prior listed row")
        if len(listed_dates) >= 121:
            complete121.append(symbol)
        if len(listed_dates) >= 60:
            complete60.append(symbol)
        target_row = next(r for r in rows if r["date"] == target)
        if target_row["row_state"] == "explicit_non_trade":
            not_tradable.append(symbol)
        elif len(listed_dates) < 121:
            insufficient.append(symbol)
    eligible = sorted(set(active) - set(not_tradable) - set(insufficient))
    breadth = sorted(r["instrument"] for r in instruments if len([d for d in dates if d >= r["effective_start"]]) >= 20)
    twii = package["twii_rows"]
    for row in twii:
        _validate_twii_row(row)
        if row["source_asof"] != target or row["availability_evidence_id"] != "evidence_twii":
            raise ContractError("NMRPA_E_SOURCE_ASOF", "TWII row asof/evidence mismatch")
    if [row["date"] for row in twii] != dates[-60:] or len({row["date"] for row in twii}) != 60:
        raise ContractError("NMRPA_E_TWII_GRID", "TWII must match exact final 60-date calendar grid")
    return {
        "calendar_prefix_sha256": expected_calendar_sha,
        "formal_active_set_sha256": _set_digest("formal_active", target, active),
        "modela_target_set_sha256": _set_digest("modela_target", target, model_symbols),
        "price_target_set_sha256": _set_digest("price_target", target, price_symbols),
        "history_121_expected_set_sha256": _set_digest("history_121_expected", target, complete121),
        "history_60_expected_set_sha256": _set_digest("history_60_expected", target, complete60),
        "complete_121_set_sha256": _set_digest("history_121_complete", target, complete121),
        "complete_60_set_sha256": _set_digest("history_60_complete", target, complete60),
        "not_tradable_set_sha256": _set_digest("not_tradable", target, not_tradable),
        "insufficient_history_set_sha256": _set_digest("insufficient_history", target, insufficient),
        "eligible_set_sha256": _set_digest("eligible", target, eligible),
        "breadth_history_expected_set_sha256": _set_digest("breadth_history_expected", target, breadth),
    }


def validate_price_row(row: Mapping[str, Any]) -> None:
    common = {
        "row_schema_version", "date", "instrument", "row_state", "source_asof", "availability_evidence_id",
        "available_at", "raw_payload_sha256", "raw_row_identity_sha256", "normalization_policy_id",
        "normalized_row_sha256", "source_id", "adjustment_policy_id", "factor_policy_id",
        "tradability_policy_id", "halt_policy_id", "factor", "raw_open", "raw_high", "raw_low",
        "raw_close", "raw_volume", "raw_vwap", "raw_trading_value", "open", "high", "low",
        "close", "volume", "vwap", "tradable_flag", "halt_flag", "non_trade_reason",
        "carry_forward_source_row_sha256",
    }
    exact(row, common, "price row")
    for key in (
        "row_schema_version", "date", "instrument", "row_state", "source_asof",
        "availability_evidence_id", "available_at", "raw_payload_sha256",
        "raw_row_identity_sha256", "normalization_policy_id", "source_id",
        "adjustment_policy_id", "factor_policy_id", "tradability_policy_id", "halt_policy_id",
    ):
        _require_string(row[key], f"price.{key}")
    parse_synthetic_date(row["date"], "price date")
    parse_synthetic_date(row["source_asof"], "price source_asof")
    parse_time(row["available_at"], "price available_at")
    for key in ("raw_payload_sha256", "raw_row_identity_sha256", "normalized_row_sha256"):
        require_sha(row[key], f"price.{key}")
    if type(row["tradable_flag"]) is not bool or type(row["halt_flag"]) is not bool:
        raise ContractError("NMRPA_E_SCHEMA", "price tradable/halt flags must be booleans")
    factor = row["factor"]
    if not isinstance(factor, (int, float)) or isinstance(factor, bool) or factor <= 0 or not math.isfinite(factor):
        raise ContractError("NMRPA_E_PRICE_MATH", "invalid factor")
    if row["row_state"] == "traded":
        if row["tradable_flag"] is not True or row["halt_flag"] is not False or row["non_trade_reason"] is not None or row["carry_forward_source_row_sha256"] is not None:
            raise ContractError("NMRPA_E_PRICE_VARIANT", "traded flags invalid")
        for key in ("raw_open", "raw_high", "raw_low", "raw_close", "raw_volume", "raw_vwap", "raw_trading_value", "open", "high", "low", "close", "volume", "vwap"):
            _require_number(row[key], f"price.{key}")
        for raw_name, adjusted_name in (("raw_open", "open"), ("raw_high", "high"), ("raw_low", "low"), ("raw_close", "close")):
            if row[raw_name] <= 0 or not math.isclose(row[adjusted_name], row[raw_name] * factor, rel_tol=1e-12, abs_tol=1e-12):
                raise ContractError("NMRPA_E_PRICE_MATH", "adjusted price mismatch")
        if row["volume"] != row["raw_volume"] or row["raw_volume"] < 0:
            raise ContractError("NMRPA_E_PRICE_MATH", "volume must remain unadjusted")
        if row["raw_volume"] == 0:
            if row["raw_vwap"] is not None or row["vwap"] is not None or row["raw_trading_value"] != 0:
                raise ContractError("NMRPA_E_PRICE_MATH", "zero-volume semantics invalid")
        elif row["raw_vwap"] <= 0 or not math.isclose(row["vwap"], row["raw_vwap"] * factor, rel_tol=1e-12, abs_tol=1e-12) or not math.isclose(row["raw_trading_value"], row["raw_vwap"] * row["raw_volume"], rel_tol=1e-12, abs_tol=1e-8):
            raise ContractError("NMRPA_E_PRICE_MATH", "VWAP/trading value mismatch")
    elif row["row_state"] == "explicit_non_trade":
        for key in ("raw_close", "raw_volume", "raw_trading_value", "close", "volume"):
            _require_number(row[key], f"price.{key}")
        if row["tradable_flag"] is not False or row["raw_volume"] != 0 or row["volume"] != 0 or row["raw_trading_value"] != 0 or row["non_trade_reason"] not in ("halt", "suspension", "no_trade_official"):
            raise ContractError("NMRPA_E_PRICE_VARIANT", "non-trade semantics invalid")
        if any(row[key] is not None for key in ("raw_open", "raw_high", "raw_low", "raw_vwap", "open", "high", "low", "vwap")) or not SHA_RE.fullmatch(str(row["carry_forward_source_row_sha256"])):
            raise ContractError("NMRPA_E_PRICE_VARIANT", "non-trade null/carry fields invalid")
        if not math.isclose(row["close"], row["raw_close"] * factor, rel_tol=1e-12, abs_tol=1e-12):
            raise ContractError("NMRPA_E_PRICE_MATH", "non-trade close mismatch")
    else:
        raise ContractError("NMRPA_E_PRICE_VARIANT", "unknown price row state")
    if checksum_without(row, "normalized_row_sha256") != row["normalized_row_sha256"]:
        raise ContractError("NMRPA_E_DIGEST", "price row digest mismatch")


def _payloads(log: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [tx["record"]["body"]["payload"] for tx in log["transactions"]]


def _registration_ref(
    payload: Mapping[str, Any], sequence: int, registration_role: str,
) -> dict[str, Any]:
    state = payload["state"]
    return {
        "transition_id": payload["transition_id"],
        "transition_sha256": payload["transition_sha256"],
        "sequence": sequence,
        "subject_id": payload["subject_id"],
        "principal_id": state["principal_id"],
        "identity_id": state["identity_id"],
        "credential_id": state["credential_id"],
        "registration_role": registration_role,
    }


def _credential_ref(payload: Mapping[str, Any], sequence: int) -> dict[str, Any]:
    state = payload["state"]
    return {
        "transition_id": payload["transition_id"],
        "transition_sha256": payload["transition_sha256"],
        "sequence": sequence,
        "credential_id": state["credential_id"],
        "owner_principal_id": state["owner_principal_id"],
        "owner_identity_id": state["owner_identity_id"],
        "owner_role": state["owner_role"],
    }


def _validate_registration_rotation_replay(
    state: Mapping[str, Any], prior: Mapping[str, Any], prior_sequence: int,
    registration_role: str, credentials: Mapping[str, Mapping[str, Any]] | None = None,
    credential_sequences: Mapping[str, int] | None = None,
) -> None:
    if state["prior_registration_ref"] != _registration_ref(prior, prior_sequence, registration_role):
        raise ContractError("NMRPA_E_REGISTRATION_STATE", "rotation prior registration ref mismatch")
    prior_credential_id = prior["state"]["credential_id"]
    if state["prior_credential_ref"]["credential_id"] != prior_credential_id:
        raise ContractError("NMRPA_E_REGISTRATION_STATE", "rotation prior credential mismatch")
    for key in ("principal_id", "identity_id", "scope"):
        if state[key] != prior["state"][key]:
            raise ContractError("NMRPA_E_REGISTRATION_STATE", "rotation changes immutable registration state")
    if credentials is None or credential_sequences is None:
        return
    old_credential = credentials.get(prior_credential_id)
    new_credential = credentials.get(state["credential_id"])
    if (
        old_credential is None
        or new_credential is None
        or old_credential["status"] != "active"
        or new_credential["status"] != "active"
    ):
        raise ContractError("NMRPA_E_REGISTRATION_STATE", "rotation lacks committed active credential")
    if state["prior_credential_ref"] != _credential_ref(
        old_credential, credential_sequences[prior_credential_id]
    ) or state["new_credential_ref"] != _credential_ref(
        new_credential, credential_sequences[state["credential_id"]]
    ):
        raise ContractError("NMRPA_E_REGISTRATION_STATE", "rotation credential ref mismatch")
    old_state, new_state = old_credential["state"], new_credential["state"]
    if any(
        state[key] != old_state[owner_key]
        or state[key] != new_state[owner_key]
        for key, owner_key in (
            ("principal_id", "owner_principal_id"),
            ("identity_id", "owner_identity_id"),
        )
    ) or old_state["owner_role"] != new_state["owner_role"]:
        raise ContractError("NMRPA_E_REGISTRATION_STATE", "rotation credential owner equality mismatch")


def validate_governance(package: Mapping[str, Any], store: InjectedObjectStore) -> dict[str, Any]:
    if store.pinned_trust is None:
        raise ContractError("NMRPA_E_CALLER_TRUST_OVERRIDE", "external pinned trust is required")
    bootstrap = package["bootstrap"]
    exact(bootstrap, {"bootstrap_id", "root_locators", "fixed_log_heads", "trusted_owner_role", "bootstrap_sha256"}, "bootstrap")
    if bootstrap["root_locators"] != ROOT_LOCATORS or bootstrap["trusted_owner_role"] != TRUSTED_LOG_OWNER_ROLE:
        raise ContractError("NMRPA_E_BOOTSTRAP_PIN", "bootstrap identity override")
    logs = package["governance_logs"]
    if set(logs) != set(FIXED_LOGS):
        raise ContractError("NMRPA_E_CALLER_TRUST_OVERRIDE", "fixed log set mismatch")
    principal_keys: dict[tuple[str, str, str], str] = {}
    principals: dict[str, Mapping[str, Any]] = {}
    identities: dict[str, Mapping[str, Any]] = {}
    credentials: dict[str, Mapping[str, Any]] = {}
    credential_sequences: dict[str, int] = {}
    services: dict[str, Mapping[str, Any]] = {}
    authorities: dict[str, Mapping[str, Any]] = {}
    recorders: dict[str, Mapping[str, Any]] = {}
    for logical_name in FIXED_LOGS:
        log = logs[logical_name]
        validate_log(logical_name, log)
        for sequence, payload in enumerate(_payloads(log), 1):
            event = payload["transition_type"]
            if event == "principal_registered":
                identity = payload["state"]["canonical_identity"]
                key = (identity["identity_namespace"], identity["jurisdiction"], identity["canonical_subject_id"])
                principal_id = payload["subject_id"]
                if key in principal_keys and principal_keys[key] != principal_id:
                    raise ContractError("NMRPA_E_PRINCIPAL_ALIAS", "principal uniqueness key reused")
                if principal_id in principals:
                    raise ContractError("NMRPA_E_PRINCIPAL_STATE", "principal ID reused")
                principal_keys[key] = principal_id
                principals[principal_id] = payload
            elif event == "principal_revoked":
                if payload["subject_id"] not in principals or principals[payload["subject_id"]]["status"] != "active":
                    raise ContractError("NMRPA_E_PRINCIPAL_STATE", "principal revoke lacks active prior")
                prior = principals[payload["subject_id"]]
                if payload["state"]["prior_transition_id"] != prior["transition_id"] or payload["state"]["canonical_identity"] != prior["state"]["canonical_identity"]:
                    raise ContractError("NMRPA_E_PRINCIPAL_STATE", "principal revoke changes immutable identity")
                principals[payload["subject_id"]] = payload
            elif event == "identity_registered":
                state = payload["state"]
                if state["principal_id"] not in principals or principals[state["principal_id"]]["status"] != "active" or payload["subject_id"] in identities:
                    raise ContractError("NMRPA_E_IDENTITY_STATE", "identity registration lacks active unique principal")
                identities[payload["subject_id"]] = payload
            elif event == "identity_revoked":
                if payload["subject_id"] not in identities or identities[payload["subject_id"]]["status"] != "active":
                    raise ContractError("NMRPA_E_IDENTITY_STATE", "identity revoke lacks active prior")
                prior = identities[payload["subject_id"]]
                if payload["state"]["prior_transition_id"] != prior["transition_id"] or payload["state"]["immutable_state_sha256"] != digest(prior["state"]):
                    raise ContractError("NMRPA_E_IDENTITY_STATE", "identity revoke immutable state mismatch")
                identities[payload["subject_id"]] = payload
            elif event == "credential_registered":
                state = payload["state"]
                if state["owner_principal_id"] not in principals or state["owner_identity_id"] not in identities or state["credential_id"] != payload["subject_id"] or payload["subject_id"] in credentials:
                    raise ContractError("NMRPA_E_CREDENTIAL_STATE", "credential registration cross-binding failed")
                credentials[payload["subject_id"]] = payload
                credential_sequences[payload["subject_id"]] = sequence
            elif event == "credential_rotated":
                state = payload["state"]
                prior = credentials.get(state["prior_credential_id"])
                if prior is None or prior["status"] != "active" or payload["subject_id"] in credentials:
                    raise ContractError("NMRPA_E_CREDENTIAL_STATE", "rotation lacks active prior credential")
                old = prior["state"]
                for old_key, new_key in (("owner_principal_id", "owner_principal_id"), ("owner_identity_id", "owner_identity_id"), ("owner_role", "owner_role")):
                    if old[old_key] != state[new_key]:
                        raise ContractError("NMRPA_E_CREDENTIAL_STATE", "rotation changes immutable owner")
                credentials[state["prior_credential_id"]] = {**prior, "status": "superseded"}
                credentials[payload["subject_id"]] = payload
                credential_sequences[payload["subject_id"]] = sequence
            elif event == "credential_revoked":
                prior = credentials.get(payload["subject_id"])
                if prior is None or prior["status"] != "active":
                    raise ContractError("NMRPA_E_CREDENTIAL_STATE", "credential revoke lacks active prior")
                state = payload["state"]
                if state["prior_transition_id"] != prior["transition_id"] or any(state[key] != prior["state"][key] for key in ("owner_principal_id", "owner_identity_id", "owner_role", "credential_id", "public_key_base64", "public_key_fingerprint_sha256")):
                    raise ContractError("NMRPA_E_CREDENTIAL_STATE", "credential revoke changes immutable state")
                credentials[payload["subject_id"]] = payload
    registry_specs = (
        ("trusted_service_registration_log", "service", services),
        ("publication_authority_registration_log", "authority", authorities),
        ("capture_recorder_registration_log", "recorder", recorders),
    )
    for logical_name, prefix, state_map in registry_specs:
        state_sequences: dict[str, int] = {}
        for sequence, payload in enumerate(_payloads(logs[logical_name]), 1):
            event, subject, state = payload["transition_type"], payload["subject_id"], payload["state"]
            if event == f"{prefix}_registered":
                if subject in state_map or state["principal_id"] not in principals or state["identity_id"] not in identities or state["credential_id"] not in credentials:
                    raise ContractError("NMRPA_E_REGISTRATION_STATE", "registration lacks active identity/credential")
                if any(item[state[state_key]]["status"] != "active" for item, state_key in ((principals, "principal_id"), (identities, "identity_id"), (credentials, "credential_id"))):
                    raise ContractError("NMRPA_E_REGISTRATION_STATE", "registration uses inactive identity/credential")
                state_map[subject] = payload
                state_sequences[subject] = sequence
            elif event.endswith("scope_extended"):
                prior = state_map.get(subject)
                if prior is None or prior["status"] != "active" or state["prior_transition_id"] != prior["transition_id"] or state["old_scope"] != prior["state"]["scope"]:
                    raise ContractError("NMRPA_E_REGISTRATION_STATE", "scope extension lacks active prior")
                merged = copy.deepcopy(prior["state"]); merged["scope"] = state["new_scope"]
                state_map[subject] = {**payload, "state": merged}
                state_sequences[subject] = sequence
            elif event.endswith("credential_rotated"):
                prior = state_map.get(subject)
                if prior is None or prior["status"] != "active":
                    raise ContractError("NMRPA_E_REGISTRATION_STATE", "service rotation lacks active prior/new credential")
                _validate_registration_rotation_replay(
                    state, prior, state_sequences[subject], prefix,
                    credentials, credential_sequences,
                )
                state_map[subject] = payload
                state_sequences[subject] = sequence
            elif event.endswith("revoked"):
                prior = state_map.get(subject)
                if prior is None or prior["status"] != "active":
                    raise ContractError("NMRPA_E_REGISTRATION_STATE", "revocation lacks active prior")
                if state["prior_transition_id"] != prior["transition_id"] or state["immutable_state_sha256"] != digest(prior["state"]):
                    raise ContractError("NMRPA_E_REGISTRATION_STATE", "revocation immutable state mismatch")
                state_map[subject] = payload
                state_sequences[subject] = sequence
    heads = {name: log["current_head"] for name, log in logs.items()}
    if bootstrap["fixed_log_heads"] != heads or bootstrap["bootstrap_sha256"] != checksum_without(bootstrap, "bootstrap_sha256"):
        raise ContractError("NMRPA_E_BOOTSTRAP_PIN", "bootstrap head/digest mismatch")
    pins = store.pinned_trust
    if bootstrap["bootstrap_sha256"] != pins.bootstrap_sha256 or heads != pins.fixed_log_heads:
        raise ContractError("NMRPA_E_BOOTSTRAP_PIN", "package governance differs from external pinned heads")
    issuer_credential = credentials.get("credential_trust_registry_issuer")
    if issuer_credential is None or issuer_credential["status"] != "active":
        raise ContractError("NMRPA_E_CREDENTIAL_STATE", "bootstrap issuer credential is not active")
    for identity in identities.values():
        if identity["status"] == "active":
            state = identity["state"]
            credential = credentials.get(state["credential_id"])
            if credential is None or credential["status"] != "active" or credential["state"]["owner_identity_id"] != state["identity_id"] or credential["state"]["owner_principal_id"] != state["principal_id"]:
                raise ContractError("NMRPA_E_IDENTITY_STATE", "active identity is not bound to its active credential")
    time_service = services.get("service_synthetic_time")
    if time_service is None or time_service["status"] != "active" or "issuer_registry" not in time_service["state"]["scope"]:
        raise ContractError("NMRPA_E_TRUSTED_TIME", "trusted time service is not committed and active")
    for log in logs.values():
        for transaction in log["transactions"]:
            body = transaction["record"]["body"]
            if body["issuer_identity_id"] != "identity_trust_registry_issuer" or body["issuer_credential_id"] != "credential_trust_registry_issuer":
                raise ContractError("NMRPA_E_SIGNATURE", "record issuer is not externally pinned")
    return {"principals": principals, "identities": identities, "credentials": credentials, "services": services, "authorities": authorities, "recorders": recorders}


def validate_log(logical_name: str, log: Mapping[str, Any]) -> None:
    exact(log, {"logical_log_name", "log_kind", "log_id", "owner_role", "transactions", "historical_heads", "current_head"}, "governance log")
    expected_kind, expected_id = FIXED_LOGS[logical_name]
    for key in ("logical_log_name", "log_kind", "log_id", "owner_role"):
        _require_string(log[key], f"log.{key}")
    if not isinstance(log["transactions"], list) or not isinstance(log["historical_heads"], list):
        raise ContractError("NMRPA_E_SCHEMA", "log transactions/heads must be arrays")
    if (log["logical_log_name"], log["log_kind"], log["log_id"], log["owner_role"]) != (logical_name, expected_kind, expected_id, TRUSTED_LOG_OWNER_ROLE):
        raise ContractError("NMRPA_E_LOG_IDENTITY", "fixed log identity mismatch")
    previous_hash = None
    heads = []
    committed: dict[str, Mapping[str, Any]] = {}
    committed_sequences: dict[str, int] = {}
    for sequence, tx in enumerate(log["transactions"], 1):
        exact(tx, {"record", "journal", "marker", "historical_head"}, "transaction")
        record = tx["record"]
        exact(record, {"body", "body_sha256", "signature", "record_sha256"}, "signed record")
        body = record["body"]
        exact(body, {"log_kind", "log_id", "sequence", "previous_record_sha256", "event_type", "issuer_role", "issuer_identity_id", "issuer_credential_id", "payload", "payload_sha256", "trusted_time", "trusted_time_service_id"}, "record body")
        for key in ("log_kind", "log_id", "event_type", "issuer_role", "issuer_identity_id", "issuer_credential_id", "trusted_time_service_id"):
            _require_string(body[key], f"record.body.{key}")
        _require_sequence(body["sequence"], "record.body.sequence", expected=sequence)
        _require_nullable_sha(body["previous_record_sha256"], "record.body.previous_record_sha256")
        require_sha(body["payload_sha256"], "record.body.payload_sha256")
        trusted_time = parse_time(body["trusted_time"], "record.body.trusted_time")
        if body["log_kind"] != expected_kind or body["log_id"] != expected_id or body["sequence"] != sequence or body["previous_record_sha256"] != previous_hash:
            raise ContractError("NMRPA_E_LEDGER_CHAIN", "record sequence/previous/log mismatch")
        if body["event_type"] not in EVENTS[logical_name] or body["issuer_role"] != TRUSTED_LOG_OWNER_ROLE or body["trusted_time_service_id"] != "service_synthetic_time":
            raise ContractError("NMRPA_E_EVENT_ROLE", "closed event/role matrix violation")
        payload = body["payload"]
        if payload.get("transition_type") != body["event_type"]:
            raise ContractError("NMRPA_E_EVENT_CROSS_BINDING", "event/payload mismatch")
        validate_transition_payload(logical_name, payload)
        if parse_time(payload["effective_at"], "transition.effective_at") > trusted_time:
            raise ContractError("NMRPA_E_TRUSTED_TIME", "transition is effective after its trusted record time")
        event = payload["transition_type"]
        subject = payload["subject_id"]
        registration_event = {
            "principal_registry_log": "principal_registered",
            "identity_registry_log": "identity_registered",
            "credential_registry_log": "credential_registered",
            "trusted_service_registration_log": "service_registered",
            "publication_authority_registration_log": "authority_registered",
            "capture_recorder_registration_log": "recorder_registered",
        }[logical_name]
        if event == registration_event:
            if subject in committed:
                raise ContractError("NMRPA_E_REGISTRATION_STATE", "duplicate registration")
            committed[subject] = payload
            committed_sequences[subject] = sequence
        elif event == "credential_rotated":
            prior_id = payload["state"]["prior_credential_id"]
            if prior_id not in committed or committed[prior_id]["status"] != "active" or subject in committed:
                raise ContractError("NMRPA_E_CREDENTIAL_STATE", "rotation lacks active committed prior")
            committed[prior_id] = {**committed[prior_id], "status": "superseded"}
            committed[subject] = payload
        elif event in REGISTRATION_ROTATION_ROLES:
            prior = committed.get(subject)
            if prior is None or prior["status"] != "active":
                raise ContractError("NMRPA_E_REGISTRATION_STATE", "rotation lacks active committed prior")
            _validate_registration_rotation_replay(
                payload["state"], prior, committed_sequences[subject],
                REGISTRATION_ROTATION_ROLES[event],
            )
            committed[subject] = payload
            committed_sequences[subject] = sequence
        else:
            prior = committed.get(subject)
            if prior is None or prior["status"] != "active":
                raise ContractError("NMRPA_E_REGISTRATION_STATE", "transition lacks active committed prior")
            prior_transition_id = payload["state"].get("prior_transition_id")
            if prior_transition_id is not None and prior_transition_id != prior["transition_id"]:
                raise ContractError("NMRPA_E_REGISTRATION_STATE", "prior transition ID mismatch")
            committed[subject] = payload
            committed_sequences[subject] = sequence
        if body["payload_sha256"] != digest(payload) or record["body_sha256"] != digest(body):
            raise ContractError("NMRPA_E_DIGEST", "record body/payload digest mismatch")
        expected_signature = digest({"credential_id": body["issuer_credential_id"], "body_sha256": record["body_sha256"]}, "nmrpa.synthetic.signature.v1")
        if record["signature"] != expected_signature or record["record_sha256"] != checksum_without(record, "record_sha256"):
            raise ContractError("NMRPA_E_SIGNATURE", "synthetic signature/record mismatch")
        journal, marker, head = tx["journal"], tx["marker"], tx["historical_head"]
        exact(journal, {"log_id", "sequence", "expected_previous_head", "record_sha256", "prepared_at", "journal_sha256"}, "journal")
        exact(marker, {"log_id", "sequence", "journal_sha256", "record_sha256", "committed_at", "marker_sha256"}, "marker")
        exact(head, {"log_id", "sequence", "previous_head_sha256", "record_sha256", "marker_sha256", "head_sha256"}, "historical head")
        for obj_name, obj in (("journal", journal), ("marker", marker), ("head", head)):
            _require_string(obj["log_id"], f"{obj_name}.log_id")
            _require_sequence(obj["sequence"], f"{obj_name}.sequence", expected=sequence)
        _require_nullable_sha(journal["expected_previous_head"], "journal.expected_previous_head")
        _require_nullable_sha(head["previous_head_sha256"], "head.previous_head_sha256")
        for obj, fields in ((record, ("body_sha256", "signature", "record_sha256")), (journal, ("record_sha256", "journal_sha256")), (marker, ("journal_sha256", "record_sha256", "marker_sha256")), (head, ("record_sha256", "marker_sha256", "head_sha256"))):
            for field in fields:
                require_sha(obj[field], field)
        previous_head = heads[-1]["head_sha256"] if heads else None
        if journal["expected_previous_head"] != previous_head or journal["record_sha256"] != record["record_sha256"] or marker["journal_sha256"] != journal["journal_sha256"] or marker["record_sha256"] != record["record_sha256"] or head["previous_head_sha256"] != previous_head or head["record_sha256"] != record["record_sha256"] or head["marker_sha256"] != marker["marker_sha256"]:
            raise ContractError("NMRPA_E_LEDGER_CHAIN", "journal/marker/head cross-binding mismatch")
        for obj, field in ((journal, "journal_sha256"), (marker, "marker_sha256"), (head, "head_sha256")):
            if obj[field] != checksum_without(obj, field):
                raise ContractError("NMRPA_E_LEDGER_CHAIN", f"{field} mismatch")
        prepared = parse_time(journal["prepared_at"], "prepared_at")
        committed_at = parse_time(marker["committed_at"], "committed_at")
        if trusted_time > prepared or prepared > committed_at:
            raise ContractError("NMRPA_E_TRUSTED_TIME", "trusted/prepare/commit time order invalid")
        previous_hash = record["record_sha256"]
        heads.append(head)
    if log["historical_heads"] != heads or not heads or log["current_head"] != heads[-1]:
        raise ContractError("NMRPA_E_LEDGER_CHAIN", "historical/current head mismatch")


def validate_transition_payload(logical_name: str, payload: Mapping[str, Any]) -> None:
    event = payload.get("transition_type")
    common = {"schema_version", "transition_id", "transition_type", "subject_id", "status", "effective_at", "state", "transition_sha256"}
    exact(payload, common, "transition payload")
    if payload["schema_version"] != "nmrpa.synthetic.transition.v1":
        raise ContractError("NMRPA_E_TRANSITION_SCHEMA", "transition schema version mismatch")
    for key in ("transition_id", "transition_type", "subject_id", "status"):
        _require_id(payload[key], f"transition.{key}")
    parse_time(payload["effective_at"], "transition.effective_at")
    require_sha(payload["transition_sha256"], "transition.transition_sha256")
    state = payload["state"]
    if not isinstance(state, dict):
        raise ContractError("NMRPA_E_SCHEMA", "transition state must be object")
    terminal = event.endswith("_revoked") or event in ("principal_revoked", "identity_revoked", "credential_revoked", "service_revoked", "authority_revoked", "recorder_revoked")
    if payload["status"] != ("revoked" if terminal else "active"):
        raise ContractError("NMRPA_E_TRANSITION_SCHEMA", "transition/status mismatch")
    if event == "principal_registered":
        exact(state, {"canonical_identity"}, "principal state")
        identity = state["canonical_identity"]
        exact(identity, {"identity_namespace", "jurisdiction", "canonical_subject_id", "canonical_display_name"}, "canonical identity")
        for key in identity:
            _require_string(identity[key], f"canonical_identity.{key}")
    elif event == "principal_revoked":
        exact(state, {"prior_transition_id", "canonical_identity", "revocation_reason"}, "principal revoke state")
        _require_id(state["prior_transition_id"], "principal_revoke.prior_transition_id")
        identity = state["canonical_identity"]
        exact(identity, {"identity_namespace", "jurisdiction", "canonical_subject_id", "canonical_display_name"}, "canonical identity")
        for key in identity:
            _require_string(identity[key], f"canonical_identity.{key}")
        _require_string(state["revocation_reason"], "principal_revoke.revocation_reason")
    elif event in ("credential_registered", "credential_rotated", "credential_revoked"):
        required = {"owner_principal_id", "owner_identity_id", "owner_role", "credential_id", "public_key_base64", "public_key_fingerprint_sha256"}
        if event == "credential_rotated": required |= {"prior_credential_id"}
        if event == "credential_revoked": required |= {"prior_transition_id", "revocation_reason"}
        exact(state, required, "credential state")
        for key in required:
            _require_string(state[key], f"credential.{key}")
        require_sha(state["public_key_fingerprint_sha256"], "credential.public_key_fingerprint_sha256")
        try:
            key = base64.b64decode(state["public_key_base64"], validate=True)
        except Exception as exc:
            raise ContractError("NMRPA_E_CREDENTIAL", "invalid public key") from exc
        if len(key) != 32 or sha256_bytes(key) != state["public_key_fingerprint_sha256"]:
            raise ContractError("NMRPA_E_CREDENTIAL", "credential fingerprint mismatch")
    elif event in REGISTRATION_ROTATION_ROLES:
        exact(
            state,
            {
                "principal_id", "identity_id", "credential_id", "scope",
                "prior_registration_ref", "prior_credential_ref", "new_credential_ref",
            },
            "registration credential rotation state",
        )
        for key in ("principal_id", "identity_id", "credential_id"):
            _require_id(state[key], f"registration_rotation.{key}")
        _require_sorted_strings(state["scope"], "registration_rotation.scope")
        if state["scope"] != sorted(set(state["scope"])):
            raise ContractError("NMRPA_E_SCOPE_TRANSITION", "rotation scope must be sorted unique")
        registration_ref = state["prior_registration_ref"]
        exact(
            registration_ref,
            {
                "transition_id", "transition_sha256", "sequence", "subject_id",
                "principal_id", "identity_id", "credential_id", "registration_role",
            },
            "prior registration ref",
        )
        for key in ("transition_id", "subject_id", "principal_id", "identity_id", "credential_id", "registration_role"):
            _require_id(registration_ref[key], f"prior_registration_ref.{key}")
        require_sha(registration_ref["transition_sha256"], "prior_registration_ref.transition_sha256")
        _require_sequence(registration_ref["sequence"], "prior_registration_ref.sequence")
        if registration_ref["registration_role"] != REGISTRATION_ROTATION_ROLES[event]:
            raise ContractError("NMRPA_E_REGISTRATION_STATE", "rotation registration role mismatch")
        for ref_name in ("prior_credential_ref", "new_credential_ref"):
            ref = state[ref_name]
            exact(
                ref,
                {
                    "transition_id", "transition_sha256", "sequence", "credential_id",
                    "owner_principal_id", "owner_identity_id", "owner_role",
                },
                ref_name,
            )
            for key in ("transition_id", "credential_id", "owner_principal_id", "owner_identity_id", "owner_role"):
                _require_id(ref[key], f"{ref_name}.{key}")
            require_sha(ref["transition_sha256"], f"{ref_name}.transition_sha256")
            _require_sequence(ref["sequence"], f"{ref_name}.sequence")
    elif "scope_extended" in event or "log_scope_extended" in event:
        exact(state, {"prior_transition_id", "old_scope", "added_scope", "new_scope"}, "scope extension state")
        _require_id(state["prior_transition_id"], "scope_extension.prior_transition_id")
        for key in ("old_scope", "added_scope", "new_scope"):
            _require_sorted_strings(state[key], f"scope_extension.{key}")
        old, added, new = state["old_scope"], state["added_scope"], state["new_scope"]
        if not added or set(old) & set(added) or sorted(set(old) | set(added)) != new or old != sorted(set(old)) or added != sorted(set(added)):
            raise ContractError("NMRPA_E_SCOPE_TRANSITION", "scope extension is not a strict canonical union")
    elif terminal:
        exact(state, {"prior_transition_id", "immutable_state_sha256", "revocation_reason"}, "revocation state")
        _require_id(state["prior_transition_id"], "revocation.prior_transition_id")
        require_sha(state["immutable_state_sha256"], "revocation.immutable_state_sha256")
        _require_string(state["revocation_reason"], "revocation.revocation_reason")
    else:
        exact(state, {"principal_id", "identity_id", "credential_id", "scope"}, "registration state")
        for key in ("principal_id", "identity_id", "credential_id"):
            _require_id(state[key], f"registration.{key}")
        _require_sorted_strings(state["scope"], "registration.scope")
        if state["scope"] != sorted(set(state["scope"])):
            raise ContractError("NMRPA_E_SCOPE_TRANSITION", "registration scope must be sorted unique")
    if payload["transition_sha256"] != checksum_without(payload, "transition_sha256"):
        raise ContractError("NMRPA_E_DIGEST", "transition digest mismatch")


def validate_binding(
    package: Mapping[str, Any], selected: Mapping[str, dict[str, Any]],
    cross: Mapping[str, str], payload_digests: Mapping[str, str], store: InjectedObjectStore,
) -> None:
    binding = package["binding"]
    exact(binding, {"schema_version", "binding_id", "target_asof", "decision_time", "source_root_inventory_sha256", "cross_binding", "contract_digests", "created_by", "created_at", "binding_sha256"}, "binding")
    if binding["schema_version"] != "nmrpa.pricestore_twii_binding.v3" or binding["target_asof"] != package["target_asof"]:
        raise ContractError("NMRPA_E_SCHEMA", "binding identity mismatch")
    if binding["decision_time"] != f"{package['target_asof']}T15:59:59Z":
        raise ContractError("NMRPA_E_PIT", "decision time must equal 23:59:59 Asia/Taipei")
    all_root_digest = digest({"schema_version": "nmrpa.all_roots_inventory.v3", "ordered_roots": [[r["root_kind"], r["root_id"], r["root_inventory_sha256"]] for r in package["source_roots"]]})
    expected_cross = {**cross, **payload_digests, "all_roots_inventory_sha256": all_root_digest, "pit_evidence_set_sha256": digest({"schema_version": "nmrpa.pit_evidence_set.v3", "binding_id": binding["binding_id"], "ordered_bindings": package["pit_bindings"]})}
    if binding["source_root_inventory_sha256"] != all_root_digest or binding["cross_binding"] != expected_cross:
        raise ContractError("NMRPA_E_CROSS_BINDING", "binding cross-section digest mismatch")
    if binding["binding_sha256"] != checksum_without(binding, "binding_sha256"):
        raise ContractError("NMRPA_E_DIGEST", "binding digest mismatch")
    if binding["contract_digests"] != PINNED_CONTRACT_DIGESTS or store.pinned_trust is None or binding["contract_digests"] != dict(store.pinned_trust.contract_digests):
        raise ContractError("NMRPA_E_CONTRACT_DIGEST", "NMRPA1_R contract digests differ from external pins")
    authorization = package["authorization"]
    exact(authorization, {"authorization_id", "target_asof", "binding_id", "allowed_root_kinds", "no_run", "no_candidate", "no_publish", "no_metric", "no_training", "authorization_sha256"}, "authorization")
    if authorization["target_asof"] != package["target_asof"] or authorization["binding_id"] != binding["binding_id"] or authorization["allowed_root_kinds"] != list(ROOT_KINDS) or not all(authorization[k] is True for k in ("no_run", "no_candidate", "no_publish", "no_metric", "no_training")) or authorization["authorization_sha256"] != checksum_without(authorization, "authorization_sha256"):
        raise ContractError("NMRPA_E_AUTHORIZATION", "isolated authorization mismatch")
    if authorization["authorization_sha256"] != store.pinned_trust.authorization_sha256:
        raise ContractError("NMRPA_E_AUTHORIZATION", "authorization differs from external pin")
    anchor = package["anchor"]
    exact(anchor, {"anchor_id", "authorization_sha256", "binding_sha256", "all_roots_inventory_sha256", "calendar_prefix_sha256", "created_at", "anchor_sha256"}, "anchor")
    if anchor["authorization_sha256"] != authorization["authorization_sha256"] or anchor["binding_sha256"] != binding["binding_sha256"] or anchor["all_roots_inventory_sha256"] != all_root_digest or anchor["calendar_prefix_sha256"] != cross["calendar_prefix_sha256"] or anchor["anchor_sha256"] != checksum_without(anchor, "anchor_sha256"):
        raise ContractError("NMRPA_E_ANCHOR_MISMATCH", "external anchor mismatch")
    if anchor["anchor_sha256"] != store.pinned_trust.anchor_sha256:
        raise ContractError("NMRPA_E_ANCHOR_MISMATCH", "anchor differs from external pin")


def validate_package(package: Mapping[str, Any], store: InjectedObjectStore) -> dict[str, Any]:
    if isinstance(package, Mapping) and package.get("runtime_overrides"):
        raise ContractError("NMRPA_E_RUNTIME_OVERRIDE", "runtime overrides are forbidden")
    errors = sorted(Draft202012Validator(TOP_LEVEL_SCHEMA).iter_errors(package), key=lambda e: list(e.path))
    if errors:
        raise ContractError("NMRPA_E_SCHEMA", errors[0].message)
    try:
        parse_synthetic_date(package["target_asof"], "target_asof")
        governance = validate_governance(package, store)
        selected = validate_source_roots(package, store)
        payload_digests = validate_normalized_views(package, selected)
        validate_pit(package, selected, governance)
        cross = validate_cross_section(package)
        validate_binding(package, selected, cross, payload_digests, store)
    except ContractError:
        raise
    except (KeyError, TypeError, ValueError, IndexError, AttributeError) as exc:
        raise ContractError("NMRPA_E_SCHEMA", "nested exact-schema validation failed") from exc
    forbidden = ("label", "metric", "outcome", "candidate", "latest", "provider_path", "root_path", "base_path")
    normalized = json.dumps(package, sort_keys=True).casefold()
    if any(f'"{token}"' in normalized for token in forbidden):
        raise ContractError("NMRPA_E_FORBIDDEN_CONTENT", "forbidden output or path field")
    return {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "fixture_mode": FIXTURE_MODE,
        "target_asof": package["target_asof"],
        "root_count": len(ROOT_KINDS),
        "formal_active_count": len(package["formal_instruments"]),
        "eligible_set_sha256": cross["eligible_set_sha256"],
        "no_run": True,
        "no_candidate": True,
        "no_metric": True,
    }


def recover_log(log: Mapping[str, Any], orphan_transaction: Mapping[str, Any] | None) -> dict[str, Any]:
    """Readonly recovery decision; never mutates a log."""
    validate_log(log["logical_log_name"], log)
    if orphan_transaction is None:
        return {"action": "none", "quarantine": False}
    tx = orphan_transaction
    if not isinstance(tx, Mapping) or tx.get("marker") is None:
        return {"action": "quarantine_uncommitted", "quarantine": True}
    expected = log["current_head"]
    if tx.get("journal", {}).get("expected_previous_head") != expected["head_sha256"]:
        return {"action": "quarantine_fork", "quarantine": True}
    try:
        candidate = copy.deepcopy(log)
        candidate["transactions"].append(copy.deepcopy(tx))
        candidate["historical_heads"].append(copy.deepcopy(tx["historical_head"]))
        candidate["current_head"] = copy.deepcopy(tx["historical_head"])
        validate_log(candidate["logical_log_name"], candidate)
    except (ContractError, KeyError, TypeError):
        return {"action": "quarantine_invalid_orphan", "quarantine": True}
    return {"action": "eligible_readonly_recovery_after_full_validation", "quarantine": False}


def _seal(obj: dict[str, Any], field: str) -> dict[str, Any]:
    obj[field] = checksum_without(obj, field)
    return obj


def _transition(event: str, subject: str, state: dict[str, Any], sequence: int) -> dict[str, Any]:
    payload = {
        "schema_version": "nmrpa.synthetic.transition.v1", "transition_id": f"transition_{subject}_{sequence}",
        "transition_type": event, "subject_id": subject,
        "status": "revoked" if event.endswith("revoked") else "active",
        "effective_at": f"2099-06-01T00:00:{sequence:02d}Z", "state": state,
    }
    return _seal(payload, "transition_sha256")


def _log(logical_name: str, payloads: Sequence[dict[str, Any]]) -> dict[str, Any]:
    kind, log_id = FIXED_LOGS[logical_name]
    transactions = []
    previous_record = None
    previous_head = None
    heads = []
    for sequence, payload in enumerate(payloads, 1):
        body = {
            "log_kind": kind, "log_id": log_id, "sequence": sequence,
            "previous_record_sha256": previous_record, "event_type": payload["transition_type"],
            "issuer_role": TRUSTED_LOG_OWNER_ROLE, "issuer_identity_id": "identity_trust_registry_issuer",
            "issuer_credential_id": "credential_trust_registry_issuer",
            "payload": payload, "payload_sha256": digest(payload),
            "trusted_time": f"2099-06-01T00:01:{sequence:02d}Z",
            "trusted_time_service_id": "service_synthetic_time",
        }
        record = {"body": body, "body_sha256": digest(body)}
        record["signature"] = digest({"credential_id": body["issuer_credential_id"], "body_sha256": record["body_sha256"]}, "nmrpa.synthetic.signature.v1")
        _seal(record, "record_sha256")
        journal = _seal({"log_id": log_id, "sequence": sequence, "expected_previous_head": previous_head, "record_sha256": record["record_sha256"], "prepared_at": f"2099-06-01T00:02:{sequence:02d}Z"}, "journal_sha256")
        marker = _seal({"log_id": log_id, "sequence": sequence, "journal_sha256": journal["journal_sha256"], "record_sha256": record["record_sha256"], "committed_at": f"2099-06-01T00:03:{sequence:02d}Z"}, "marker_sha256")
        head = _seal({"log_id": log_id, "sequence": sequence, "previous_head_sha256": previous_head, "record_sha256": record["record_sha256"], "marker_sha256": marker["marker_sha256"]}, "head_sha256")
        transactions.append({"record": record, "journal": journal, "marker": marker, "historical_head": head})
        heads.append(head); previous_head = head["head_sha256"]; previous_record = record["record_sha256"]
    return {"logical_log_name": logical_name, "log_kind": kind, "log_id": log_id, "owner_role": TRUSTED_LOG_OWNER_ROLE, "transactions": transactions, "historical_heads": heads, "current_head": heads[-1]}


def _member(kind: str, role: str, name: str, obj: Any, objects: dict[str, bytes]) -> dict[str, Any]:
    token = f"SYNTHETIC_OBJECT_{kind.upper()}_{name.upper()}"
    raw = canonical_json(obj); objects[token] = raw
    object_ref = {"object_id": f"object_{kind}_{name}", "selector": {"selector_type": "whole_document"}, "canonical_schema_id": f"nmrpa.synthetic.{role}.v1", "canonical_object_sha256": digest(obj)}
    member = {
        "member_id": f"member_{kind}_{name}", "root_kind": kind, "root_id": ROOT_LOCATORS[kind]["root_id"],
        "file_role": role, "relative_path": f"synthetic/{name}.json", "file_type": "json",
        "media_type": "application/json", "object_token": token, "byte_size": len(raw), "bytes_sha256": sha256_bytes(raw),
        "ordered_objects": [object_ref],
    }
    member["object_index_sha256"] = digest({"schema_version": "nmrpa.object_index.v1", "member_id": member["member_id"], "ordered_objects": member["ordered_objects"]})
    return member


def build_synthetic_fixture(config: Mapping[str, Any]) -> tuple[dict[str, Any], InjectedObjectStore]:
    exact(config, {"fixture_id", "target_asof", "symbols", "evidence_mode"}, "fixture config")
    target = parse_synthetic_date(config["target_asof"], "target_asof")
    symbols = config["symbols"]
    if symbols != sorted(set(symbols)) or not symbols:
        raise ContractError("NMRPA_E_SCHEMA", "symbols must be sorted unique")
    if config["evidence_mode"] not in ("trusted_publication", "first_successful_capture"):
        raise ContractError("NMRPA_E_SCHEMA", "unsupported synthetic evidence mode")
    dates = synthetic_trading_dates(target, 121)
    available = f"{target.isoformat()}T12:00:00Z"
    calendar = {"calendar_id": "synthetic_twse_calendar_v1", "genesis_policy_id": "nmrpa_twse_calendar_genesis_v1", "target_asof": target.isoformat(), "ordered_dates": dates}
    calendar["calendar_prefix_sha256"] = digest({"schema_version": "nmrpa.calendar_prefix.v2", **calendar})
    instruments = []
    for symbol in symbols:
        instruments.append(_seal({"instrument": symbol, "effective_start": dates[0], "effective_end": None}, "row_sha256"))
    modela = [_seal({"instrument": symbol, "signal_asof": target.isoformat(), "source_asof": target.isoformat(), "available_at": available, "availability_evidence_id": "evidence_modela_signal", "raw_score": float(len(symbols) - i)}, "row_sha256") for i, symbol in enumerate(symbols)]
    prices = []
    for sidx, symbol in enumerate(symbols):
        previous_sha = None
        for didx, day in enumerate(dates):
            raw = 50.0 + sidx + didx * 0.1
            row = {
                "row_schema_version": "nmrpa.adjusted_price_row.v2", "date": day, "instrument": symbol,
                "row_state": "traded", "source_asof": target.isoformat(), "availability_evidence_id": "evidence_adjusted_price",
                "available_at": available, "raw_payload_sha256": digest({"symbol": symbol, "day": day}),
                "raw_row_identity_sha256": digest([symbol, day]), "normalization_policy_id": "nmrpa_price_normalization_v2",
                "source_id": "synthetic_adjusted_price", "adjustment_policy_id": "nmrpa_adjusted_v2",
                "factor_policy_id": "nmrpa_factor_v2", "tradability_policy_id": "nmrpa_tradability_v2",
                "halt_policy_id": "nmrpa_halt_v2", "factor": 1.0,
                "raw_open": raw, "raw_high": raw + 1, "raw_low": raw - 1, "raw_close": raw + 0.5,
                "raw_volume": 1000.0, "raw_vwap": raw + 0.25, "raw_trading_value": (raw + 0.25) * 1000.0,
                "open": raw, "high": raw + 1, "low": raw - 1, "close": raw + 0.5,
                "volume": 1000.0, "vwap": raw + 0.25, "tradable_flag": True, "halt_flag": False,
                "non_trade_reason": None, "carry_forward_source_row_sha256": None,
            }
            _seal(row, "normalized_row_sha256"); previous_sha = row["normalized_row_sha256"]; prices.append(row)
    twii = [_seal({"date": day, "source_asof": target.isoformat(), "available_at": available, "availability_evidence_id": "evidence_twii", "close": 10000.0 + i}, "row_sha256") for i, day in enumerate(dates[-60:])]
    objects: dict[str, bytes] = {}
    payloads = {"sealed_calendar": calendar, "formal_instruments": instruments, "adjusted_price": prices, "twii": twii, "modela_signal": modela}
    roots = []
    evidence = []
    row_keys = {
        "sealed_calendar": [f"calendar:{d}" for d in dates],
        "formal_instruments": [f"instrument:{s}" for s in symbols],
        "adjusted_price": [f"price:{r['date']}:{r['instrument']}" for r in prices],
        "twii": [f"twii:{r['date']}" for r in twii],
        "modela_signal": [f"modela:{s}" for s in symbols],
    }
    for kind in ROOT_KINDS:
        payload = {"source_id": f"synthetic_{kind}", "source_asof": target.isoformat(), "rows": payloads[kind]}
        record = {"authority_id": "authority_synthetic_publication", "publication_record_id": f"publication_{kind}", "published_at": available, "source_asof": target.isoformat(), "source_id": f"synthetic_{kind}", "payload_sha256": digest(payload)}
        native = {"source_run_id": f"synthetic_{kind}_run", "target_asof": target.isoformat(), "source_id": f"synthetic_{kind}"}
        members = [_member(kind, "normalized_payload", "normalized", payload, objects), _member(kind, "source_native_manifest", "source_manifest", native, objects)]
        attempts = None
        if config["evidence_mode"] == "trusted_publication":
            members.extend((_member(kind, "publication_payload", "publication_payload", payload, objects), _member(kind, "publication_record", "publication_record", record, objects)))
        else:
            raw_member = _member(kind, "raw_response", "raw_response", payload, objects)
            raw_ref = {
                "member_id": raw_member["member_id"], "bytes_sha256": raw_member["bytes_sha256"],
                "object_id": raw_member["ordered_objects"][0]["object_id"],
                "canonical_object_sha256": raw_member["ordered_objects"][0]["canonical_object_sha256"],
            }
            request_identity = {"source_id": f"synthetic_{kind}", "endpoint_id": f"synthetic_{kind}_endpoint", "method": "GET", "canonical_query": f"asof={target.isoformat()}", "requested_scope_id": kind, "requested_source_asof": target.isoformat(), "request_contract_id": "nmrpa.synthetic.request.v1"}
            request_sha = digest({"schema_version": "nmrpa.request_identity.v3", **request_identity})
            attempts = [{"attempt_id": f"attempt_{kind}_1", "sequence": 1, "request_identity_sha256": request_sha, "started_at": f"{target.isoformat()}T11:59:00Z", "completed_at": available, "result_class": "authoritative_success", "response_bytes_present": True, "http_status": 200, "raw_response_ref": raw_ref}]
            ledger = {"recorder_id": "recorder_synthetic_capture", "source_id": f"synthetic_{kind}", "ordered_attempts": attempts}
            members.extend((raw_member, _member(kind, "attempt_ledger", "attempt_ledger", ledger, objects)))
        if kind == "adjusted_price": members.append(_member(kind, "tradability_payload", "tradability", {"source_id": "synthetic_adjusted_price", "source_asof": target.isoformat(), "explicit_non_trade": []}, objects))
        members.sort(key=lambda m: m["relative_path"].encode())
        root = {"schema_version": "nmrpa.root_inventory.v3", "root_kind": kind, **ROOT_LOCATORS[kind], "ordered_members": members, "member_count": len(members)}
        _seal(root, "root_inventory_sha256"); roots.append(root)
        by_role = {m["file_role"]: m for m in members}
        def ref(member: Mapping[str, Any]) -> dict[str, Any]:
            obj = member["ordered_objects"][0]
            return {"member_id": member["member_id"], "bytes_sha256": member["bytes_sha256"], "object_id": obj["object_id"], "canonical_object_sha256": obj["canonical_object_sha256"]}
        if config["evidence_mode"] == "trusted_publication":
            ev = {
                "schema_version": "nmrpa.trusted_publication_evidence.v3", "evidence_id": f"evidence_{kind}",
                "evidence_type": "trusted_publication", "root_kind": kind, "root_id": ROOT_LOCATORS[kind]["root_id"],
                "source_id": f"synthetic_{kind}", "requested_source_asof": target.isoformat(),
                "referenced_row_keys": sorted(row_keys[kind]), "available_at": available,
                "authority_id": "authority_synthetic_publication", "publication_record_id": f"publication_{kind}",
                "published_source_asof": target.isoformat(), "published_at": available,
                "publication_payload_ref": ref(by_role["publication_payload"]), "publication_record_ref": ref(by_role["publication_record"]),
            }
        else:
            request_identity = {"source_id": f"synthetic_{kind}", "endpoint_id": f"synthetic_{kind}_endpoint", "method": "GET", "canonical_query": f"asof={target.isoformat()}", "requested_scope_id": kind, "requested_source_asof": target.isoformat(), "request_contract_id": "nmrpa.synthetic.request.v1"}
            ev = {
                "schema_version": "nmrpa.first_successful_capture_evidence.v3", "evidence_id": f"evidence_{kind}",
                "evidence_type": "first_successful_capture", "root_kind": kind, "root_id": ROOT_LOCATORS[kind]["root_id"],
                "source_id": f"synthetic_{kind}", "requested_source_asof": target.isoformat(),
                "referenced_row_keys": sorted(row_keys[kind]), "available_at": available,
                "capture_run_id": f"capture_{kind}", "request_identity": request_identity,
                "request_identity_sha256": digest({"schema_version": "nmrpa.request_identity.v3", **request_identity}),
                "attempt_ledger_ref": ref(by_role["attempt_ledger"]), "ordered_attempts": attempts,
                "first_success_attempt_id": attempts[-1]["attempt_id"], "first_successful_capture_at": available,
                "first_success_raw_response_ref": attempts[-1]["raw_response_ref"],
            }
        _seal(ev, "evidence_sha256"); evidence.append(ev)
    principal_identity = {"identity_namespace": "project_service", "jurisdiction": "ZZ", "canonical_subject_id": "nmrpa.synthetic.trust", "canonical_display_name": "NMRPA Synthetic Trust"}
    principal = _transition("principal_registered", "principal_synthetic_trust", {"canonical_identity": principal_identity}, 1)
    key = bytes(range(32)); cred_state = {"owner_principal_id": "principal_synthetic_trust", "owner_identity_id": "identity_trust_registry_issuer", "owner_role": TRUSTED_LOG_OWNER_ROLE, "credential_id": "credential_trust_registry_issuer", "public_key_base64": base64.b64encode(key).decode(), "public_key_fingerprint_sha256": sha256_bytes(key)}
    logs = {
        "principal_registry_log": _log("principal_registry_log", [principal]),
        "identity_registry_log": _log("identity_registry_log", [_transition("identity_registered", "identity_trust_registry_issuer", {"principal_id": "principal_synthetic_trust", "identity_id": "identity_trust_registry_issuer", "credential_id": "credential_trust_registry_issuer", "scope": ["trust_registry"]}, 1)]),
        "credential_registry_log": _log("credential_registry_log", [_transition("credential_registered", "credential_trust_registry_issuer", cred_state, 1)]),
        "trusted_service_registration_log": _log("trusted_service_registration_log", [_transition("service_registered", "service_synthetic_time", {"principal_id": "principal_synthetic_trust", "identity_id": "identity_trust_registry_issuer", "credential_id": "credential_trust_registry_issuer", "scope": ["issuer_registry"]}, 1)]),
        "publication_authority_registration_log": _log("publication_authority_registration_log", [_transition("authority_registered", "authority_synthetic_publication", {"principal_id": "principal_synthetic_trust", "identity_id": "identity_trust_registry_issuer", "credential_id": "credential_trust_registry_issuer", "scope": sorted(ROOT_KINDS)}, 1)]),
        "capture_recorder_registration_log": _log("capture_recorder_registration_log", [_transition("recorder_registered", "recorder_synthetic_capture", {"principal_id": "principal_synthetic_trust", "identity_id": "identity_trust_registry_issuer", "credential_id": "credential_trust_registry_issuer", "scope": ["synthetic_capture"]}, 1)]),
    }
    bootstrap = {"bootstrap_id": "nmrpa.synthetic.bootstrap.v1", "root_locators": copy.deepcopy(ROOT_LOCATORS), "fixed_log_heads": {name: copy.deepcopy(log["current_head"]) for name, log in logs.items()}, "trusted_owner_role": TRUSTED_LOG_OWNER_ROLE}
    _seal(bootstrap, "bootstrap_sha256")
    contract_digests = dict(PINNED_CONTRACT_DIGESTS)
    package: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "fixture_mode": FIXTURE_MODE, "target_asof": target.isoformat(), "runtime_overrides": {},
        "bootstrap": bootstrap, "governance_logs": logs, "source_roots": roots, "pit_bindings": evidence,
        "calendar": calendar, "formal_instruments": instruments, "modela_rows": modela, "price_rows": prices, "twii_rows": twii,
    }
    cross = validate_cross_section(package)
    all_root_digest = digest({"schema_version": "nmrpa.all_roots_inventory.v3", "ordered_roots": [[r["root_kind"], r["root_id"], r["root_inventory_sha256"]] for r in roots]})
    binding_id = f"binding_{config['fixture_id']}"
    payload_digests = {f"{kind}_payload_sha256": digest({"source_id": f"synthetic_{kind}", "source_asof": target.isoformat(), "rows": payloads[kind]}) for kind in ROOT_KINDS}
    expected_cross = {**cross, **payload_digests, "all_roots_inventory_sha256": all_root_digest, "pit_evidence_set_sha256": digest({"schema_version": "nmrpa.pit_evidence_set.v3", "binding_id": binding_id, "ordered_bindings": evidence})}
    binding = {"schema_version": "nmrpa.pricestore_twii_binding.v3", "binding_id": binding_id, "target_asof": target.isoformat(), "decision_time": f"{target.isoformat()}T15:59:59Z", "source_root_inventory_sha256": all_root_digest, "cross_binding": expected_cross, "contract_digests": contract_digests, "created_by": "adapter_nmrpa3_isolated", "created_at": f"{target.isoformat()}T13:00:00Z"}
    _seal(binding, "binding_sha256")
    authorization = {"authorization_id": f"authorization_{config['fixture_id']}", "target_asof": target.isoformat(), "binding_id": binding_id, "allowed_root_kinds": list(ROOT_KINDS), "no_run": True, "no_candidate": True, "no_publish": True, "no_metric": True, "no_training": True}
    _seal(authorization, "authorization_sha256")
    anchor = {"anchor_id": f"anchor_{config['fixture_id']}", "authorization_sha256": authorization["authorization_sha256"], "binding_sha256": binding["binding_sha256"], "all_roots_inventory_sha256": all_root_digest, "calendar_prefix_sha256": cross["calendar_prefix_sha256"], "created_at": f"{target.isoformat()}T14:00:00Z"}
    _seal(anchor, "anchor_sha256")
    package.update({"binding": binding, "authorization": authorization, "anchor": anchor})
    pins = PinnedTrust(
        bootstrap_sha256=bootstrap["bootstrap_sha256"],
        fixed_log_heads=copy.deepcopy(bootstrap["fixed_log_heads"]),
        contract_digests=dict(PINNED_CONTRACT_DIGESTS),
        authorization_sha256=authorization["authorization_sha256"],
        anchor_sha256=anchor["anchor_sha256"],
    )
    return package, InjectedObjectStore(objects, pins)


__all__ = [
    "ContractError", "InjectedObjectStore", "PinnedTrust", "TOP_LEVEL_SCHEMA", "ROOT_KINDS", "ROOT_LOCATORS",
    "FIXED_LOGS", "EVENTS", "build_synthetic_fixture", "validate_package", "validate_log",
    "validate_transition_payload", "validate_price_row", "recover_log", "digest", "checksum_without",
]
