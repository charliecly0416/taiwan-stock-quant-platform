#!/usr/bin/env python3
"""Synthetic-only CRPG core-registry adapter.

Logical validation is pure. Physical validation and commits require a live
capability for a bootstrap-compatible root below /tmp.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
import stat
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

import tw_policy_nmrpa3_immutable_binding_writer as writer
from tw_policy_nmrpa3_real_trust_bootstrap import canonical_json, digest, expected_descriptor


INTENT_SCHEMA_VERSION = "nmrpa.core_registry_intent.synthetic.v1"
PLAN_SCHEMA_VERSION = "nmrpa.core_registry_transaction_plan.synthetic.v1"
MAX_SEQUENCE = 99_999_999_999_999_999_999
BASE = "data_tw/artifacts/research/nmrpa/trust_bootstrap_v1"
P_STORE = f"{BASE}/stores/principal_identity_credential_registry_stores"
A_STORE = f"{BASE}/stores/trusted_actor_registry_stores"
SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"
ACTUAL_MARKER = writer.ACTUAL_PROJECT_ROOT / f"{BASE}/stores/project_root_identity_marker/identity.json"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX128 = re.compile(r"^[0-9a-f]{128}$")
UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
ID_PATTERNS = {
    "transaction_id": re.compile(r"^tx_[0-9a-f]{32}$"),
    "transition_id": re.compile(r"^transition_[0-9a-f]{32}$"),
    "principal_id": re.compile(r"^principal_[0-9a-f]{32}$"),
    "identity_id": re.compile(r"^identity_[0-9a-f]{32}$"),
    "credential_id": re.compile(r"^credential_[0-9a-f]{32}$"),
    "service_id": re.compile(r"^service_[0-9a-f]{32}$"),
    "authority_id": re.compile(r"^authority_[0-9a-f]{32}$"),
    "recorder_id": re.compile(r"^recorder_[0-9a-f]{32}$"),
}
STATIC_ID = re.compile(r"^[A-Za-z][A-Za-z0-9._:-]{7,191}$")
ROLES = (
    "trust_registry_issuer", "root_registry_issuer", "authorization_issuer", "anchor_issuer",
    "publication_authority", "capture_recorder", "trusted_time_authority", "commit_service",
    "source_snapshot_owner", "adapter", "validator",
)
LOG_KINDS = ("issuer_registry", "publication_authority_registry", "capture_recorder_registry")
ROOT_KINDS = ("sealed_calendar", "formal_instruments", "adjusted_price", "twii", "modela_signal")
BOOTSTRAP_ID = "synthetic_crpg_genesis_bootstrap_signer_v1"
BRANCHES = {
    "principal_registered": ("principal_registry_log", "principal", "principal_id", P_STORE, ".principal.json", 0),
    "identity_registered": ("identity_registry_log", "identity", "identity_id", P_STORE, ".identity.json", 1),
    "credential_activated": ("credential_registry_log", "credential", "credential_id", P_STORE, ".credential.json", 2),
    "trusted_service_registered": ("trusted_service_registration_log", "trusted_service", "registration_id", A_STORE, ".trusted_service.json", 3),
    "publication_authority_registered": ("publication_authority_registration_log", "publication_authority", "registration_id", A_STORE, ".publication_authority.json", 3),
    "capture_recorder_registered": ("capture_recorder_registration_log", "capture_recorder", "registration_id", A_STORE, ".capture_recorder.json", 3),
}
DOMAIN_VERSIONS = {
    "principal_registered": "nmrpa.core_registry.principal_registration.v1",
    "identity_registered": "nmrpa.core_registry.identity_registration.v1",
    "credential_activated": "nmrpa.core_registry.credential_activation.v1",
    "trusted_service_registered": "nmrpa.core_registry.trusted_service_registration.v1",
    "publication_authority_registered": "nmrpa.core_registry.publication_authority_registration.v1",
    "capture_recorder_registered": "nmrpa.core_registry.capture_recorder_registration.v1",
}
DOMAIN_DIGESTS = {key: value.replace(".v1", ".digest.v1") for key, value in DOMAIN_VERSIONS.items()}
REF_FIELDS = {
    "schema_version", "descriptor_sha256", "project_root_identity_sha256", "root_instance",
    "logical_name", "log_kind", "log_id", "sequence", "transaction_id", "event_kind",
    "domain_object_kind", "domain_object_id", "domain_object_relative_path", "domain_object_sha256",
    "record_relative_path", "record_body_sha256", "signed_record_sha256", "journal_relative_path",
    "journal_sha256", "marker_relative_path", "commit_sha256", "history_relative_path",
    "historical_head_sequence", "historical_head_sha256", "current_head_relative_path", "commit_ref_sha256",
}
ROOT_FIELDS = {
    "schema_version", "canonical_project_root", "st_dev", "st_ino", "capability_nonce_sha256",
    "project_identity_marker_sha256", "descriptor_sha256", "root_instance_sha256",
}
SIGNATURE_FIELDS = {
    "schema_version", "signer_mode", "credential_id", "credential_registration_ref", "algorithm",
    "signed_digest", "signature_hex",
}
HEAD_FIELDS = {
    "schema_version", "logical_name", "log_kind", "log_id", "sequence", "transaction_id",
    "previous_head_sha256", "previous_commit_sha256", "domain_object_kind", "domain_object_id",
    "domain_object_relative_path", "domain_object_sha256", "record_body_sha256", "signed_record_sha256",
    "journal_sha256", "commit_sha256", "committed_at", "root_instance", "head_sha256",
}
V1_HEAD_FIELDS = {"schema_version", "logical_name", "log_id", "sequence", "previous_head_sha256", "record_sha256", "head_sha256"}
BODY_FIELDS = {
    "schema_version", "descriptor_sha256", "project_root_identity_sha256", "root_instance", "logical_name",
    "log_kind", "log_id", "transaction_id", "sequence", "previous_head_sha256", "previous_commit_sha256",
    "event_kind", "issued_at", "domain_object_kind", "domain_object_id", "domain_object_relative_path",
    "domain_object_sha256", "ordered_prerequisite_refs", "issuer_identity_id", "issuer_credential_id",
}
JOURNAL_FIELDS = {
    "schema_version", "descriptor_sha256", "project_root_identity_sha256", "root_instance", "logical_name",
    "log_kind", "log_id", "transaction_id", "sequence", "previous_commit_sha256",
    "expected_previous_head_sha256", "domain_object_sha256", "signed_record_sha256", "journal_state",
    "prepared_at", "synthetic_commit_signature", "journal_sha256",
}
MARKER_FIELDS = {
    "schema_version", "descriptor_sha256", "project_root_identity_sha256", "root_instance", "logical_name",
    "log_kind", "log_id", "transaction_id", "sequence", "previous_commit_sha256",
    "expected_previous_head_sha256", "domain_object_sha256", "record_body_sha256", "signed_record_sha256",
    "journal_sha256", "prepared_at", "committed_at", "synthetic_commit_signature", "commit_sha256",
}


class ContractError(ValueError):
    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def _fail(code: str, detail: str) -> None:
    raise ContractError(code, detail)


def _exact(value: Any, fields: set[str], where: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        _fail("NMRPA_CRPG_SCHEMA", f"{where} exact fields differ")
    return value


def _string(value: Any, where: str) -> str:
    if type(value) is not str or not value or unicodedata.normalize("NFC", value) != value:
        _fail("NMRPA_CRPG_SCHEMA", f"{where} must be non-empty NFC string")
    return value


def _integer(value: Any, where: str, minimum: int = 1, maximum: int = MAX_SEQUENCE) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        _fail("NMRPA_CRPG_EXACT_INTEGER", f"{where} outside exact integer range")
    return value


def _sha(value: Any, where: str) -> str:
    if type(value) is not str or not HEX64.fullmatch(value):
        _fail("NMRPA_CRPG_SCHEMA", f"{where} must be lowercase sha256")
    return value


def _id(value: Any, kind: str, where: str) -> str:
    if type(value) is not str or not ID_PATTERNS[kind].fullmatch(value):
        _fail("NMRPA_CRPG_SCHEMA", f"invalid {where}")
    return value


def _time(value: Any, where: str) -> datetime:
    if type(value) is not str or not UTC.fullmatch(value):
        _fail("NMRPA_CRPG_SCHEMA", f"invalid {where}")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ContractError("NMRPA_CRPG_SCHEMA", f"invalid {where}") from exc


def _sealed(value: Mapping[str, Any], own: str, domain: str) -> bool:
    return value[own] == digest({key: child for key, child in value.items() if key != own}, domain)


def _reject_surfaces(value: Any, where: str = "root") -> None:
    if isinstance(value, (bytes, bytearray, memoryview)) or hasattr(value, "read"):
        _fail("NMRPA_CRPG_PAYLOAD_SURFACE", where)
    if type(value) is dict:
        for key, child in value.items():
            if type(key) is not str:
                _fail("NMRPA_CRPG_SCHEMA", "non-string key")
            folded = key.casefold()
            if any(term in folded for term in ("payload_path", "payload_bytes", "file_handle", "private_key", "private_seed", "checkpoint", "cache", "latest")):
                _fail("NMRPA_CRPG_PAYLOAD_SURFACE", key)
            _reject_surfaces(child, f"{where}.{key}")
    elif type(value) is list:
        for index, child in enumerate(value):
            _reject_surfaces(child, f"{where}[{index}]")


def validate_root_instance_commitment_shape(value: Any) -> dict[str, Any]:
    value = _exact(value, ROOT_FIELDS, "root_instance")
    if value["schema_version"] != "nmrpa.synthetic_root_instance.v1":
        _fail("NMRPA_CRPG_ROOT_INSTANCE_SCHEMA", "schema version")
    root = _string(value["canonical_project_root"], "canonical_project_root")
    if not root.startswith("/tmp/") or Path(root).as_posix() != root:
        _fail("NMRPA_CRPG_ROOT_INSTANCE_SCHEMA", "root must be canonical /tmp path")
    if type(value["st_dev"]) is not int or value["st_dev"] < 0 or type(value["st_ino"]) is not int or value["st_ino"] < 1:
        _fail("NMRPA_CRPG_ROOT_INSTANCE_SCHEMA", "root inode fields")
    for field in ("capability_nonce_sha256", "project_identity_marker_sha256", "descriptor_sha256", "root_instance_sha256"):
        if type(value[field]) is not str or not HEX64.fullmatch(value[field]):
            _fail("NMRPA_CRPG_ROOT_INSTANCE_SCHEMA", field)
    if not _sealed(value, "root_instance_sha256", "nmrpa.synthetic_root_instance.digest.v1"):
        _fail("NMRPA_CRPG_ROOT_INSTANCE_DIGEST", "root commitment digest")
    return dict(value)


def _root_equal(left: Any, right: Any) -> None:
    validate_root_instance_commitment_shape(left)
    validate_root_instance_commitment_shape(right)
    if left != right:
        _fail("NMRPA_CRPG_ROOT_INSTANCE_MISMATCH", "root commitments differ")


def _validate_ref(ref: Any, root_instance: Mapping[str, Any] | None = None) -> dict[str, Any]:
    ref = _exact(ref, REF_FIELDS, "commit_ref")
    if ref["schema_version"] != "nmrpa.core_registry.commit_ref.v1":
        _fail("NMRPA_CRPG_SCHEMA", "commit ref version")
    for field in ("descriptor_sha256", "project_root_identity_sha256", "domain_object_sha256", "record_body_sha256", "signed_record_sha256", "journal_sha256", "commit_sha256", "historical_head_sha256", "commit_ref_sha256"):
        _sha(ref[field], f"ref.{field}")
    sequence = _integer(ref["sequence"], "ref.sequence")
    if _integer(ref["historical_head_sequence"], "ref.historical_head_sequence") != sequence:
        _fail("NMRPA_CRPG_SCHEMA", "ref sequence mismatch")
    _id(ref["transaction_id"], "transaction_id", "ref.transaction_id")
    if ref["event_kind"] not in BRANCHES:
        _fail("NMRPA_CRPG_SCHEMA", "ref event")
    for field in ("logical_name", "log_kind", "log_id", "domain_object_kind", "domain_object_id", "domain_object_relative_path", "record_relative_path", "journal_relative_path", "marker_relative_path", "history_relative_path", "current_head_relative_path"):
        _string(ref[field], f"ref.{field}")
    validate_root_instance_commitment_shape(ref["root_instance"])
    if root_instance is not None:
        _root_equal(ref["root_instance"], root_instance)
    if not _sealed(ref, "commit_ref_sha256", "nmrpa.core_registry.commit_ref.digest.v1"):
        _fail("NMRPA_CRPG_DIGEST", "commit ref digest")
    return dict(ref)


def _validate_signature(value: Any, root_instance: Mapping[str, Any], *, bootstrap_only: bool = False) -> dict[str, Any]:
    value = _exact(value, SIGNATURE_FIELDS, "signature")
    if value["schema_version"] != "nmrpa.core_registry.signature.synthetic.v1" or value["algorithm"] != "ed25519":
        _fail("NMRPA_CRPG_SCHEMA", "signature envelope")
    if value["signer_mode"] not in ("synthetic_genesis_bootstrap", "committed_registry_issuer"):
        _fail("NMRPA_CRPG_SCHEMA", "signature signer mode")
    _sha(value["signed_digest"], "signature.signed_digest")
    if type(value["signature_hex"]) is not str or not HEX128.fullmatch(value["signature_hex"]):
        _fail("NMRPA_CRPG_SCHEMA", "signature hex")
    if value["signer_mode"] == "synthetic_genesis_bootstrap":
        if value["credential_id"] != BOOTSTRAP_ID or value["credential_registration_ref"] is not None:
            _fail("NMRPA_CRPG_SCHEMA", "bootstrap signature identity")
    else:
        if bootstrap_only:
            _fail("NMRPA_CRPG_SCHEMA", "bootstrap attestation required")
        _id(value["credential_id"], "credential_id", "signature.credential_id")
        if value["credential_registration_ref"] is None:
            _fail("NMRPA_CRPG_COMMITTED_KEY_REF_REQUIRED", "committed signer credential ref")
        _validate_ref(value["credential_registration_ref"], root_instance)
    return dict(value)


def _verify_signature(signature: Mapping[str, Any], key: bytes) -> None:
    message = b"nmrpa.core_registry.ed25519.message.v1\x00" + bytes.fromhex(signature["signed_digest"])
    try:
        Ed25519PublicKey.from_public_bytes(key).verify(bytes.fromhex(signature["signature_hex"]), message)
    except (ValueError, InvalidSignature) as exc:
        raise ContractError("NMRPA_CRPG_SIGNATURE_INVALID", "Ed25519 verification failed") from exc


def _validate_head(value: Any, log: Mapping[str, Any], root_instance: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if type(value) is not dict:
        _fail("NMRPA_CRPG_SCHEMA", "head must be object")
    sequence = value.get("sequence")
    if type(sequence) is not int:
        _fail("NMRPA_CRPG_EXACT_INTEGER", "head.sequence")
    if sequence == 0:
        _exact(value, V1_HEAD_FIELDS, "V1 head")
        if value["schema_version"] != "nmrpa.log_head.v1" or value["logical_name"] != log["logical_name"] or value["log_id"] != log["log_id"] or value["previous_head_sha256"] is not None:
            _fail("NMRPA_CRPG_CHAIN", "V1 head identity")
        _sha(value["record_sha256"], "V1 record")
        _sha(value["head_sha256"], "V1 head")
        if not _sealed(value, "head_sha256", "nmrpa.log.head.v1"):
            _fail("NMRPA_CRPG_DIGEST", "V1 head")
    else:
        _exact(value, HEAD_FIELDS, "committed head")
        _integer(sequence, "head.sequence")
        if value["schema_version"] != "nmrpa.core_registry_committed_head.v1" or value["logical_name"] != log["logical_name"] or value["log_kind"] != log["log_kind"] or value["log_id"] != log["log_id"]:
            _fail("NMRPA_CRPG_CHAIN", "committed head identity")
        _id(value["transaction_id"], "transaction_id", "head.transaction_id")
        for field in ("domain_object_kind", "domain_object_id", "domain_object_relative_path"):
            _string(value[field], f"head.{field}")
        _time(value["committed_at"], "head.committed_at")
        validate_root_instance_commitment_shape(value["root_instance"])
        if root_instance is not None:
            _root_equal(value["root_instance"], root_instance)
        for field in ("previous_head_sha256", "domain_object_sha256", "record_body_sha256", "signed_record_sha256", "journal_sha256", "commit_sha256", "head_sha256"):
            _sha(value[field], f"head.{field}")
        if sequence == 1 and value["previous_commit_sha256"] is not None:
            _fail("NMRPA_CRPG_CHAIN", "sequence one previous commit")
        if sequence > 1:
            _sha(value["previous_commit_sha256"], "head.previous_commit_sha256")
        if not _sealed(value, "head_sha256", "nmrpa.core_registry.committed_head.digest.v1"):
            _fail("NMRPA_CRPG_DIGEST", "head digest")
    return dict(value)


def _domain_fields(branch: str) -> set[str]:
    common = {"schema_version", "transition_id", "event_kind", "status", "effective_at", "domain_object_sha256"}
    if branch == "principal_registered":
        return common | {"principal_id", "canonical_identity", "canonical_identity_sha256"}
    if branch == "identity_registered":
        return common | {"identity_id", "principal_id", "principal_registration_ref", "role", "display_name", "valid_from", "valid_until"}
    if branch == "credential_activated":
        return common | {"credential_id", "owner_identity_id", "owner_principal_id", "owner_role", "owner_identity_registration_ref", "owner_principal_registration_ref", "algorithm", "public_key_base64", "public_key_fingerprint_sha256", "valid_from", "valid_until"}
    if branch == "trusted_service_registered":
        return common | {"registration_id", "service_type", "principal_id", "service_identity_id", "service_credential_id", "principal_registration_ref", "identity_registration_ref", "credential_registration_ref", "allowed_log_kinds", "valid_from", "valid_until"}
    if branch == "publication_authority_registered":
        return common | {"registration_id", "authority_id", "principal_id", "authority_identity_id", "authority_credential_id", "principal_registration_ref", "authority_identity_registration_ref", "authority_credential_registration_ref", "source_id", "allowed_root_kinds", "publication_contract_id", "valid_from", "valid_until"}
    return common | {"registration_id", "recorder_id", "principal_id", "recorder_identity_id", "recorder_credential_id", "principal_registration_ref", "recorder_identity_registration_ref", "recorder_credential_registration_ref", "allowed_scopes", "valid_from", "valid_until"}


def _validate_domain(value: Any, branch: str, root_instance: Mapping[str, Any]) -> dict[str, Any]:
    value = _exact(value, _domain_fields(branch), "domain_object")
    if value["schema_version"] != DOMAIN_VERSIONS[branch] or value["event_kind"] != branch or value["status"] != "active":
        _fail("NMRPA_CRPG_SCHEMA", "domain discriminator")
    _id(value["transition_id"], "transition_id", "transition_id")
    effective = _time(value["effective_at"], "effective_at")
    _, _, id_field, _, _, _ = BRANCHES[branch]
    kind = {"principal_id": "principal_id", "identity_id": "identity_id", "credential_id": "credential_id"}.get(id_field)
    if kind is None:
        kind = {"trusted_service_registered": "service_id", "publication_authority_registered": "authority_id", "capture_recorder_registered": "recorder_id"}[branch]
    _id(value[id_field], kind, id_field)
    ref_fields: list[str] = []
    if branch == "principal_registered":
        identity = _exact(value["canonical_identity"], {"identity_namespace", "jurisdiction", "canonical_subject_id", "canonical_display_name"}, "canonical_identity")
        if identity["identity_namespace"] not in ("tw_legal_entity", "tw_natural_person", "project_service") or (identity["identity_namespace"] == "project_service" and identity["jurisdiction"] != "ZZ"):
            _fail("NMRPA_CRPG_SCHEMA", "canonical identity")
        for field in identity:
            _string(identity[field], f"canonical_identity.{field}")
        _sha(value["canonical_identity_sha256"], "canonical identity digest")
        if value["canonical_identity_sha256"] != digest(identity, "nmrpa.canonical_principal_identity.digest.v1"):
            _fail("NMRPA_CRPG_DIGEST", "canonical identity")
    elif branch == "identity_registered":
        _id(value["identity_id"], "identity_id", "identity_id"); _id(value["principal_id"], "principal_id", "principal_id")
        if value["role"] not in ROLES or not 1 <= len(_string(value["display_name"], "display_name")) <= 128:
            _fail("NMRPA_CRPG_SCHEMA", "identity role/display")
        ref_fields = ["principal_registration_ref"]
    elif branch == "credential_activated":
        _id(value["credential_id"], "credential_id", "credential_id"); _id(value["owner_identity_id"], "identity_id", "owner_identity_id"); _id(value["owner_principal_id"], "principal_id", "owner_principal_id")
        if value["owner_role"] not in ROLES or value["algorithm"] != "ed25519":
            _fail("NMRPA_CRPG_SCHEMA", "credential role/algorithm")
        try:
            key = base64.b64decode(value["public_key_base64"], validate=True)
        except (ValueError, binascii.Error, TypeError) as exc:
            raise ContractError("NMRPA_CRPG_COMMITTED_KEY_ENCODING", "credential key") from exc
        if len(key) != 32 or base64.b64encode(key).decode() != value["public_key_base64"] or hashlib.sha256(key).hexdigest() != value["public_key_fingerprint_sha256"]:
            _fail("NMRPA_CRPG_COMMITTED_KEY_ENCODING", "credential key/fingerprint")
        ref_fields = ["owner_principal_registration_ref", "owner_identity_registration_ref"]
    else:
        if branch == "trusted_service_registered":
            if value["service_type"] not in ("trusted_time_authority", "commit_service") or value["allowed_log_kinds"] != [item for item in LOG_KINDS if item in value["allowed_log_kinds"]] or not value["allowed_log_kinds"]:
                _fail("NMRPA_CRPG_SCHEMA", "trusted service fields")
            refs = ("principal_registration_ref", "identity_registration_ref", "credential_registration_ref")
        elif branch == "publication_authority_registered":
            if value["registration_id"] != value["authority_id"] or value["allowed_root_kinds"] != [item for item in ROOT_KINDS if item in value["allowed_root_kinds"]] or not value["allowed_root_kinds"]:
                _fail("NMRPA_CRPG_SCHEMA", "authority fields")
            if not STATIC_ID.fullmatch(value["source_id"]) or not STATIC_ID.fullmatch(value["publication_contract_id"]):
                _fail("NMRPA_CRPG_SCHEMA", "authority contract ids")
            refs = ("principal_registration_ref", "authority_identity_registration_ref", "authority_credential_registration_ref")
        else:
            if value["registration_id"] != value["recorder_id"] or type(value["allowed_scopes"]) is not list or not value["allowed_scopes"]:
                _fail("NMRPA_CRPG_SCHEMA", "recorder fields")
            scope_keys = ("source_id", "endpoint_id", "method", "request_contract_id", "canonical_query_contract_id", "requested_scope_contract_id", "allowed_root_kinds", "allowed_response_media_types")
            order = []
            for scope in value["allowed_scopes"]:
                _exact(scope, set(scope_keys), "capture scope")
                if scope["method"] not in ("GET", "POST") or scope["allowed_root_kinds"] != [item for item in ROOT_KINDS if item in scope["allowed_root_kinds"]] or not scope["allowed_root_kinds"] or scope["allowed_response_media_types"] != sorted(set(scope["allowed_response_media_types"])) or not scope["allowed_response_media_types"]:
                    _fail("NMRPA_CRPG_SCHEMA", "capture scope order")
                for field in scope_keys[:2] + scope_keys[3:6]:
                    if not STATIC_ID.fullmatch(scope[field]): _fail("NMRPA_CRPG_SCHEMA", "capture scope id")
                order.append(tuple(scope[field] for field in scope_keys[:6]))
            if order != sorted(set(order)):
                _fail("NMRPA_CRPG_SCHEMA", "capture scopes not unique sorted")
            refs = ("principal_registration_ref", "recorder_identity_registration_ref", "recorder_credential_registration_ref")
        ref_fields = list(refs)
    for field in ref_fields:
        _validate_ref(value[field], root_instance)
    if branch != "principal_registered":
        start = _time(value["valid_from"], "valid_from")
        end = None if value["valid_until"] is None else _time(value["valid_until"], "valid_until")
        if end is not None and end <= start:
            _fail("NMRPA_CRPG_TIME", "validity interval")
        if start > effective:
            _fail("NMRPA_CRPG_TIME", "validity starts after effective time")
    _sha(value["domain_object_sha256"], "domain digest")
    if not _sealed(value, "domain_object_sha256", DOMAIN_DIGESTS[branch]):
        _fail("NMRPA_CRPG_DIGEST", "domain object")
    return dict(value)


def _schema(name: str) -> Draft202012Validator:
    with (SCHEMA_DIR / name).open("r", encoding="utf-8") as stream:
        schema = json.load(stream)
    Draft202012Validator.check_schema(schema)
    registry = Registry()
    for path in SCHEMA_DIR.glob("tw_policy_nmrpa3_core_registry_*.schema.json"):
        document = json.loads(path.read_text(encoding="utf-8"))
        registry = registry.with_resource(document["$id"], Resource.from_contents(document))
        registry = registry.with_resource(path.name, Resource.from_contents(document))
    return Draft202012Validator(schema, registry=registry)


def _descriptor(descriptor: Any, descriptor_sha256: Any) -> dict[str, Any]:
    expected = expected_descriptor()
    if type(descriptor) is not dict or descriptor != expected or descriptor_sha256 != expected["descriptor_sha256"]:
        _fail("NMRPA_CRPG_DESCRIPTOR", "descriptor pin differs")
    return expected


def _validate_intent_logical(intent: Any, descriptor: Mapping[str, Any], *, run_schema: bool = True) -> dict[str, Any]:
    _reject_surfaces(intent)
    fields = {"artifact_kind", "schema_version", "mode", "transition_branch", "transaction_id", "descriptor_sha256", "project_root_identity_sha256", "root_instance", "expected_previous_head", "domain_object", "ordered_prerequisite_refs", "issuer_signature", "synthetic_bootstrap_public_key_hex", "synthetic_journal_signature", "synthetic_marker_signature", "issued_at", "prepared_at", "committed_at", "intent_sha256"}
    intent = _exact(intent, fields, "intent")
    if intent["artifact_kind"] != "core_registry_intent" or intent["schema_version"] != INTENT_SCHEMA_VERSION or intent["mode"] != "synthetic_bootstrap_compatible_no_actual_write" or intent["transition_branch"] not in BRANCHES:
        _fail("NMRPA_CRPG_SCHEMA", "intent discriminator")
    branch = intent["transition_branch"]
    _id(intent["transaction_id"], "transaction_id", "transaction_id")
    _sha(intent["descriptor_sha256"], "descriptor_sha256"); _sha(intent["project_root_identity_sha256"], "project_root_identity_sha256")
    root_instance = validate_root_instance_commitment_shape(intent["root_instance"])
    if root_instance["descriptor_sha256"] != intent["descriptor_sha256"] or root_instance["project_identity_marker_sha256"] != intent["project_root_identity_sha256"]:
        _fail("NMRPA_CRPG_ROOT_INSTANCE_MISMATCH", "intent root pins")
    log = next(row for row in descriptor["fixed_logs"] if row["logical_name"] == BRANCHES[branch][0])
    previous = _validate_head(intent["expected_previous_head"], log, root_instance if intent["expected_previous_head"].get("sequence") else None)
    domain = _validate_domain(intent["domain_object"], branch, root_instance)
    if type(intent["ordered_prerequisite_refs"]) is not list or len(intent["ordered_prerequisite_refs"]) != BRANCHES[branch][5]:
        _fail("NMRPA_CRPG_SCHEMA", "prerequisite count")
    refs = [_validate_ref(ref, root_instance) for ref in intent["ordered_prerequisite_refs"]]
    domain_refs = {
        "principal_registered": [], "identity_registered": ["principal_registration_ref"],
        "credential_activated": ["owner_principal_registration_ref", "owner_identity_registration_ref"],
        "trusted_service_registered": ["principal_registration_ref", "identity_registration_ref", "credential_registration_ref"],
        "publication_authority_registered": ["principal_registration_ref", "authority_identity_registration_ref", "authority_credential_registration_ref"],
        "capture_recorder_registered": ["principal_registration_ref", "recorder_identity_registration_ref", "recorder_credential_registration_ref"],
    }[branch]
    if refs != [domain[field] for field in domain_refs]:
        _fail("NMRPA_CRPG_PREREQUISITE", "ordered refs differ from domain")
    issuer = _validate_signature(intent["issuer_signature"], root_instance)
    journal_sig = _validate_signature(intent["synthetic_journal_signature"], root_instance, bootstrap_only=True)
    marker_sig = _validate_signature(intent["synthetic_marker_signature"], root_instance, bootstrap_only=True)
    if type(intent["synthetic_bootstrap_public_key_hex"]) is not str or not HEX64.fullmatch(intent["synthetic_bootstrap_public_key_hex"]):
        _fail("NMRPA_CRPG_SCHEMA", "bootstrap public key")
    issued, prepared, committed = (_time(intent[field], field) for field in ("issued_at", "prepared_at", "committed_at"))
    if not (_time(domain["effective_at"], "effective_at") <= issued <= prepared <= committed):
        _fail("NMRPA_CRPG_TIME", "transaction time order")
    if run_schema:
        errors = sorted(_schema("tw_policy_nmrpa3_core_registry_intent.schema.json").iter_errors(intent), key=lambda item: list(item.path))
        if errors:
            _fail("NMRPA_CRPG_STRUCTURAL_SCHEMA", errors[0].message)
    _sha(intent["intent_sha256"], "intent_sha256")
    if not _sealed(intent, "intent_sha256", "nmrpa.core_registry.intent.synthetic.v1"):
        _fail("NMRPA_CRPG_DIGEST", "intent digest")
    return {"branch": branch, "log": log, "previous": previous, "domain": domain, "refs": refs, "issuer": issuer, "journal_signature": journal_sig, "marker_signature": marker_sig, "root_instance": root_instance}


def _read_json(root: Path, relative: str) -> Any:
    path = root / relative
    try:
        if path.is_symlink() or not stat.S_ISREG(os.lstat(path).st_mode):
            _fail("NMRPA_CRPG_FILE_TYPE", relative)
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            raw = b""
            while len(raw) <= 2_097_152:
                block = os.read(fd, 65_536)
                if not block: break
                raw += block
        finally: os.close(fd)
        value = json.loads(raw)
        if raw != canonical_json(value):
            _fail("NMRPA_CRPG_CANONICAL_BYTES", relative)
        return value
    except ContractError: raise
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        raise ContractError("NMRPA_CRPG_PHYSICAL", relative) from exc


def _paths(log: Mapping[str, Any], branch: str, tx: str, sequence: int, object_id: str) -> dict[str, str]:
    _, _, _, store, suffix, _ = BRANCHES[branch]
    stem = f"{sequence:020d}--{tx}"
    result = {
        "domain_object": f"{store}/{object_id}{suffix}",
        "signed_record": f"{log['journal_locator']}/{stem}.record.json",
        "journal": f"{log['journal_locator']}/{stem}.journal.json",
        "marker": f"{log['commit_marker_locator']}/{stem}.commit.json",
        "history": log["historical_heads_locator"], "head": log["current_head_locator"],
    }
    return result


def _validate_record_bundle(domain: Any, signed: Any, journal: Any, marker: Any, head: Any, log: Mapping[str, Any], root_instance: Mapping[str, Any]) -> None:
    signed = _exact(signed, {"schema_version", "record_body", "record_body_sha256", "signature", "root_instance", "signed_record_sha256"}, "signed_record")
    if signed["schema_version"] != "nmrpa.core_registry.signed_record.v1": _fail("NMRPA_CRPG_SCHEMA", "signed record version")
    _root_equal(signed["root_instance"], root_instance)
    body = _exact(signed["record_body"], BODY_FIELDS, "record_body")
    if body["schema_version"] != "nmrpa.core_registry.record_body.v1": _fail("NMRPA_CRPG_SCHEMA", "record body version")
    _root_equal(body["root_instance"], root_instance)
    _integer(body["sequence"], "record sequence")
    _sha(body["descriptor_sha256"], "record.descriptor_sha256")
    _sha(body["project_root_identity_sha256"], "record.project_root_identity_sha256")
    _id(body["transaction_id"], "transaction_id", "record.transaction_id")
    for field in ("logical_name", "log_kind", "log_id", "domain_object_kind", "domain_object_id", "domain_object_relative_path", "issuer_identity_id", "issuer_credential_id"):
        _string(body[field], f"record.{field}")
    branch = domain["event_kind"]
    if type(body["ordered_prerequisite_refs"]) is not list or len(body["ordered_prerequisite_refs"]) != BRANCHES[branch][5]:
        _fail("NMRPA_CRPG_SCHEMA", "record prerequisite count")
    body_refs = [_validate_ref(ref, root_instance) for ref in body["ordered_prerequisite_refs"]]
    domain_ref_fields = {
        "principal_registered": [], "identity_registered": ["principal_registration_ref"],
        "credential_activated": ["owner_principal_registration_ref", "owner_identity_registration_ref"],
        "trusted_service_registered": ["principal_registration_ref", "identity_registration_ref", "credential_registration_ref"],
        "publication_authority_registered": ["principal_registration_ref", "authority_identity_registration_ref", "authority_credential_registration_ref"],
        "capture_recorder_registered": ["principal_registration_ref", "recorder_identity_registration_ref", "recorder_credential_registration_ref"],
    }[branch]
    if body_refs != [domain[field] for field in domain_ref_fields]:
        _fail("NMRPA_CRPG_PREREQUISITE", "record/domain prerequisite refs differ")
    signature = _validate_signature(signed["signature"], root_instance)
    if signed["record_body_sha256"] != digest(body, "nmrpa.core_registry.record_body.digest.v1") or signature["signed_digest"] != signed["record_body_sha256"]:
        _fail("NMRPA_CRPG_SIGNED_CONTAINER_MISMATCH", "record body chain")
    if body["logical_name"] != log["logical_name"] or body["log_kind"] != log["log_kind"] or body["log_id"] != log["log_id"]:
        _fail("NMRPA_CRPG_SIGNED_CONTAINER_MISMATCH", "record/domain/log equality")
    if not _sealed(signed, "signed_record_sha256", "nmrpa.core_registry.signed_record.digest.v1"):
        _fail("NMRPA_CRPG_DIGEST", "signed record")
    journal = _exact(journal, JOURNAL_FIELDS, "journal")
    marker = _exact(marker, MARKER_FIELDS, "marker")
    for item, version, own, domain_name in ((journal, "nmrpa.core_registry.transaction_journal.v1", "journal_sha256", "nmrpa.core_registry.transaction_journal.digest.v1"), (marker, "nmrpa.core_registry.commit_marker.v1", "commit_sha256", "nmrpa.core_registry.commit_marker.digest.v1")):
        if item["schema_version"] != version: _fail("NMRPA_CRPG_SCHEMA", "control version")
        _root_equal(item["root_instance"], root_instance)
        _integer(item["sequence"], "control sequence")
        _validate_signature(item["synthetic_commit_signature"], root_instance, bootstrap_only=True)
        if not _sealed(item, own, domain_name): _fail("NMRPA_CRPG_DIGEST", own)
    if journal["journal_state"] != "prepared":
        _fail("NMRPA_CRPG_SIGNED_CONTAINER_MISMATCH", "journal state")
    cross_equal = {
        "logical_name": (body["logical_name"], journal["logical_name"], marker["logical_name"], head["logical_name"]),
        "log_kind": (body["log_kind"], journal["log_kind"], marker["log_kind"], head["log_kind"]),
        "log_id": (body["log_id"], journal["log_id"], marker["log_id"], head["log_id"]),
        "transaction_id": (body["transaction_id"], journal["transaction_id"], marker["transaction_id"], head["transaction_id"]),
        "sequence": (body["sequence"], journal["sequence"], marker["sequence"], head["sequence"]),
        "previous_commit_sha256": (body["previous_commit_sha256"], journal["previous_commit_sha256"], marker["previous_commit_sha256"], head["previous_commit_sha256"]),
        "previous_head_sha256": (body["previous_head_sha256"], journal["expected_previous_head_sha256"], marker["expected_previous_head_sha256"], head["previous_head_sha256"]),
        "domain_object_sha256": (domain["domain_object_sha256"], body["domain_object_sha256"], journal["domain_object_sha256"], marker["domain_object_sha256"], head["domain_object_sha256"]),
        "record_body_sha256": (signed["record_body_sha256"], marker["record_body_sha256"], head["record_body_sha256"]),
        "signed_record_sha256": (signed["signed_record_sha256"], journal["signed_record_sha256"], marker["signed_record_sha256"], head["signed_record_sha256"]),
        "journal_sha256": (journal["journal_sha256"], marker["journal_sha256"], head["journal_sha256"]),
        "commit_sha256": (marker["commit_sha256"], head["commit_sha256"]),
        "prepared_at": (journal["prepared_at"], marker["prepared_at"]),
        "committed_at": (marker["committed_at"], head["committed_at"]),
    }
    for field, values in cross_equal.items():
        if any(value != values[0] for value in values[1:]):
            _fail("NMRPA_CRPG_SIGNED_CONTAINER_MISMATCH", f"{field} cross equality")
    if (
        body["domain_object_kind"] != head["domain_object_kind"]
        or body["domain_object_id"] != head["domain_object_id"]
        or body["domain_object_relative_path"] != head["domain_object_relative_path"]
        or body["event_kind"] != domain["event_kind"]
        or body["domain_object_kind"] != BRANCHES[domain["event_kind"]][1]
        or body["domain_object_id"] != domain[BRANCHES[domain["event_kind"]][2]]
    ):
        _fail("NMRPA_CRPG_SIGNED_CONTAINER_MISMATCH", "domain identity/path equality")
    for item in (body, journal, marker):
        if item["descriptor_sha256"] != root_instance["descriptor_sha256"] or item["project_root_identity_sha256"] != root_instance["project_identity_marker_sha256"]:
            _fail("NMRPA_CRPG_ROOT_INSTANCE_MISMATCH", "bundle root pins")
    issued = _time(body["issued_at"], "record.issued_at")
    prepared = _time(journal["prepared_at"], "journal.prepared_at")
    committed = _time(marker["committed_at"], "marker.committed_at")
    if not (_time(domain["effective_at"], "domain.effective_at") <= issued <= prepared <= committed):
        _fail("NMRPA_CRPG_TIME", "physical bundle time order")
    if "valid_from" in domain:
        valid_from = _time(domain["valid_from"], "domain.valid_from")
        valid_until = None if domain["valid_until"] is None else _time(domain["valid_until"], "domain.valid_until")
        if valid_from > issued or (valid_until is not None and valid_until <= committed):
            _fail("NMRPA_CRPG_PREREQUISITE", "domain inactive at physical marker")
    journal_attestation = _attestation_digest(journal, "synthetic_commit_signature", "journal_sha256", "nmrpa.core_registry.transaction_journal.commit_attestation.v1")
    marker_attestation = _attestation_digest(marker, "synthetic_commit_signature", "commit_sha256", "nmrpa.core_registry.commit_marker.commit_attestation.v1")
    if journal["synthetic_commit_signature"]["signed_digest"] != journal_attestation or marker["synthetic_commit_signature"]["signed_digest"] != marker_attestation:
        _fail("NMRPA_CRPG_SIGNED_CONTAINER_MISMATCH", "attestation signed digest")


def _full_closure(root: Path, descriptor: Mapping[str, Any], commitment: Mapping[str, Any]) -> dict[str, Any]:
    transactions: list[tuple[str, int, str]] = []
    objects: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    logs: dict[str, dict[str, Any]] = {}
    bundles: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]] = {}
    for log in descriptor["fixed_logs"]:
        genesis = _read_json(root, log["genesis_locator"])
        _exact(genesis, {"schema_version", "logical_name", "log_kind", "log_id", "owner_role", "sequence", "previous_head_sha256", "genesis_sha256"}, "genesis")
        if type(genesis["sequence"]) is not int or genesis["sequence"] != 0 or genesis["schema_version"] != "nmrpa.log_genesis.v1" or genesis["logical_name"] != log["logical_name"] or genesis["log_kind"] != log["log_kind"] or genesis["log_id"] != log["log_id"] or genesis["owner_role"] != "trust_registry_issuer" or genesis["previous_head_sha256"] is not None or not _sealed(genesis, "genesis_sha256", "nmrpa.log.genesis.v1"):
            _fail("NMRPA_CRPG_CHAIN", "genesis")
        history = _read_json(root, log["historical_heads_locator"])
        current = _read_json(root, log["current_head_locator"])
        if type(history) is not list or not history: _fail("NMRPA_CRPG_CHAIN", "history")
        previous = _validate_head(history[0], log)
        if previous["record_sha256"] != genesis["genesis_sha256"]:
            _fail("NMRPA_CRPG_CHAIN", "genesis head binding")
        if history[-1] != current: _fail("NMRPA_CRPG_CHAIN", "head/history mismatch")
        expected_records: set[str] = set(); expected_markers: set[str] = set()
        for index, raw_head in enumerate(history[1:], 1):
            head = _validate_head(raw_head, log, commitment)
            if head["sequence"] != index or head["previous_head_sha256"] != previous["head_sha256"] or (index > 1 and head["previous_commit_sha256"] != previous["commit_sha256"]):
                _fail("NMRPA_CRPG_CHAIN", "history discontinuity")
            branch = head["event_kind"] if "event_kind" in head else next(key for key, row in BRANCHES.items() if row[1] == head["domain_object_kind"])
            paths = _paths(log, branch, head["transaction_id"], index, head["domain_object_id"])
            if paths["domain_object"] != head["domain_object_relative_path"]: _fail("NMRPA_CRPG_PATH", "domain path")
            domain = _read_json(root, paths["domain_object"]); signed = _read_json(root, paths["signed_record"]); journal = _read_json(root, paths["journal"]); marker = _read_json(root, paths["marker"])
            _validate_domain(domain, branch, commitment); _validate_record_bundle(domain, signed, journal, marker, head, log, commitment)
            transactions.append((log["logical_name"], index, head["transaction_id"]))
            if head["domain_object_id"] in objects: _fail("NMRPA_CRPG_REPLAY", "domain id reused")
            if head["transaction_id"] in bundles:
                _fail("NMRPA_CRPG_CROSS_LOG_TX_MULTIPLICITY", "duplicate transaction")
            objects[head["domain_object_id"]] = (domain, head)
            bundles[head["transaction_id"]] = (domain, signed, journal, marker, head)
            expected_records |= {Path(paths["signed_record"]).name, Path(paths["journal"]).name}; expected_markers.add(Path(paths["marker"]).name)
            previous = head
        for relative, expected in ((log["journal_locator"], expected_records), (log["commit_marker_locator"], expected_markers)):
            directory = root / relative
            names = set()
            for child in directory.iterdir():
                if child.is_symlink() or not child.is_file(): _fail("NMRPA_CRPG_ORPHAN", str(child))
                names.add(child.name)
            if names != expected: _fail("NMRPA_CRPG_ORPHAN", relative)
        logs[log["logical_name"]] = {"head": current, "history": history}
    counts = Counter(tx for _, _, tx in transactions)
    if any(value != 1 for value in counts.values()): _fail("NMRPA_CRPG_CROSS_LOG_TX_MULTIPLICITY", "duplicate transaction")
    expected_by_store = {P_STORE: set(), A_STORE: set()}
    for object_id, (_, head) in objects.items(): expected_by_store[next(row[3] for row in BRANCHES.values() if row[1] == head["domain_object_kind"])].add(Path(head["domain_object_relative_path"]).name)
    for relative, expected in expected_by_store.items():
        actual = set()
        for child in (root / relative).iterdir():
            if child.is_symlink() or not child.is_file(): _fail("NMRPA_CRPG_ORPHAN", str(child))
            actual.add(child.name)
        if actual != expected: _fail("NMRPA_CRPG_ORPHAN", relative)
    credentials = [item for item, _ in objects.values() if item.get("event_kind") == "credential_activated"]
    for field in ("credential_id", "public_key_base64", "public_key_fingerprint_sha256"):
        values = [item[field] for item in credentials]
        if len(values) != len(set(values)):
            _fail("NMRPA_CRPG_ROLE_KEY_REUSE", field)
    transitions = [item["transition_id"] for item, _ in objects.values()]
    if len(transitions) != len(set(transitions)):
        _fail("NMRPA_CRPG_REPLAY", "transition id reused")
    principals = [item for item, _ in objects.values() if item.get("event_kind") == "principal_registered"]
    principal_keys = [(item["canonical_identity"]["identity_namespace"], item["canonical_identity"]["jurisdiction"], item["canonical_identity"]["canonical_subject_id"]) for item in principals]
    if len(principal_keys) != len(set(principal_keys)):
        _fail("NMRPA_CRPG_REPLAY", "canonical principal reused")
    return {"logs": logs, "objects": objects, "transactions": transactions, "bundles": bundles, "descriptor_logs": {row["logical_name"]: row for row in descriptor["fixed_logs"]}}


def _ref_physical(ref: Mapping[str, Any], closure: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    pair = closure["objects"].get(ref["domain_object_id"])
    if pair is None:
        _fail("NMRPA_CRPG_COMMIT_REF_UNBACKED", "reference object is absent")
    domain, head = pair
    signed, journal, marker = closure["bundles"][head["transaction_id"]][1:4]
    branch = domain["event_kind"]
    log = closure["descriptor_logs"][head["logical_name"]]
    paths = _paths(log, branch, head["transaction_id"], head["sequence"], head["domain_object_id"])
    expected = {"schema_version": "nmrpa.core_registry.commit_ref.v1", "descriptor_sha256": head["root_instance"]["descriptor_sha256"], "project_root_identity_sha256": head["root_instance"]["project_identity_marker_sha256"], "root_instance": head["root_instance"], "logical_name": head["logical_name"], "log_kind": head["log_kind"], "log_id": head["log_id"], "sequence": head["sequence"], "transaction_id": head["transaction_id"], "event_kind": branch, "domain_object_kind": head["domain_object_kind"], "domain_object_id": head["domain_object_id"], "domain_object_relative_path": paths["domain_object"], "domain_object_sha256": head["domain_object_sha256"], "record_relative_path": paths["signed_record"], "record_body_sha256": signed["record_body_sha256"], "signed_record_sha256": signed["signed_record_sha256"], "journal_relative_path": paths["journal"], "journal_sha256": journal["journal_sha256"], "marker_relative_path": paths["marker"], "commit_sha256": marker["commit_sha256"], "history_relative_path": paths["history"], "historical_head_sequence": head["sequence"], "historical_head_sha256": head["head_sha256"], "current_head_relative_path": paths["head"]}
    expected["commit_ref_sha256"] = digest(expected, "nmrpa.core_registry.commit_ref.digest.v1")
    if dict(ref) != expected:
        _fail("NMRPA_CRPG_COMMIT_REF_UNBACKED", "reference differs from committed object")
    return domain, head


def _validate_prerequisite_semantics(branch: str, domain: Mapping[str, Any], refs: list[Mapping[str, Any]], closure: Mapping[str, Any], issued_at: str, committed_at: str) -> None:
    resolved = [_ref_physical(ref, closure)[0] for ref in refs]
    if any(_time(item["effective_at"], "prerequisite effective_at") > _time(issued_at, "issued_at") for item in resolved):
        _fail("NMRPA_CRPG_PREREQUISITE", "future prerequisite")
    end_point = _time(committed_at, "committed_at")
    for item in resolved:
        if "valid_from" in item and (_time(item["valid_from"], "valid_from") > _time(issued_at, "issued_at") or (item["valid_until"] is not None and _time(item["valid_until"], "valid_until") <= end_point)):
            _fail("NMRPA_CRPG_PREREQUISITE", "inactive prerequisite")
    if branch == "identity_registered":
        if resolved[0].get("principal_id") != domain["principal_id"]:
            _fail("NMRPA_CRPG_PREREQUISITE", "identity principal differs")
    elif branch == "credential_activated":
        principal, identity = resolved
        if principal.get("principal_id") != domain["owner_principal_id"] or identity.get("identity_id") != domain["owner_identity_id"] or identity.get("principal_id") != domain["owner_principal_id"] or identity.get("role") != domain["owner_role"]:
            _fail("NMRPA_CRPG_PREREQUISITE", "credential owner chain differs")
    elif branch in ("trusted_service_registered", "publication_authority_registered", "capture_recorder_registered"):
        principal, identity, credential = resolved
        identity_id_field = {"trusted_service_registered": "service_identity_id", "publication_authority_registered": "authority_identity_id", "capture_recorder_registered": "recorder_identity_id"}[branch]
        credential_id_field = {"trusted_service_registered": "service_credential_id", "publication_authority_registered": "authority_credential_id", "capture_recorder_registered": "recorder_credential_id"}[branch]
        expected_role = domain["service_type"] if branch == "trusted_service_registered" else "publication_authority" if branch == "publication_authority_registered" else "capture_recorder"
        if principal.get("principal_id") != domain["principal_id"] or identity.get("identity_id") != domain[identity_id_field] or identity.get("principal_id") != domain["principal_id"] or identity.get("role") != expected_role or credential.get("credential_id") != domain[credential_id_field] or credential.get("owner_identity_id") != domain[identity_id_field] or credential.get("owner_principal_id") != domain["principal_id"] or credential.get("owner_role") != expected_role:
            _fail("NMRPA_CRPG_PREREQUISITE", "role registration chain differs")


def _bundle_key(head: Mapping[str, Any]) -> tuple[str, int, str]:
    return head["logical_name"], head["sequence"], head["transaction_id"]


def _require_ancestor(ref_head: Mapping[str, Any], dependent_head: Mapping[str, Any], closure: Mapping[str, Any]) -> None:
    if _bundle_key(ref_head) == _bundle_key(dependent_head):
        _fail("NMRPA_CRPG_COMMITTED_KEY_REF_CYCLE", "self reference")
    if ref_head["logical_name"] == dependent_head["logical_name"] and ref_head["sequence"] >= dependent_head["sequence"]:
        _fail("NMRPA_CRPG_COMMITTED_KEY_REF_UNTRUSTED", "same-log future reference")
    ref_marker = closure["bundles"][ref_head["transaction_id"]][3]
    dependent_marker = closure["bundles"][dependent_head["transaction_id"]][3]
    if _time(ref_marker["committed_at"], "ancestor.committed_at") > _time(dependent_marker["committed_at"], "dependent.committed_at"):
        _fail("NMRPA_CRPG_COMMITTED_KEY_REF_UNTRUSTED", "future committed reference")


def _decode_committed_issuer_key(
    signature: Mapping[str, Any], credential: Mapping[str, Any], body: Mapping[str, Any], marker: Mapping[str, Any],
) -> bytes:
    if (
        credential.get("event_kind") != "credential_activated"
        or credential.get("owner_role") != "trust_registry_issuer"
        or credential.get("credential_id") != signature["credential_id"]
        or body["issuer_credential_id"] != credential.get("credential_id")
        or body["issuer_identity_id"] != credential.get("owner_identity_id")
    ):
        _fail("NMRPA_CRPG_COMMITTED_KEY_ROLE", "signer credential owner/role")
    issued = _time(body["issued_at"], "record.issued_at")
    committed = _time(marker["committed_at"], "marker.committed_at")
    valid_from = _time(credential["valid_from"], "credential.valid_from")
    valid_until = None if credential["valid_until"] is None else _time(credential["valid_until"], "credential.valid_until")
    if valid_from > issued or valid_from > committed or (valid_until is not None and (valid_until <= issued or valid_until <= committed)):
        _fail("NMRPA_CRPG_COMMITTED_KEY_INACTIVE", "signer credential inactive at record or marker")
    try:
        key = base64.b64decode(credential["public_key_base64"], validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ContractError("NMRPA_CRPG_COMMITTED_KEY_ENCODING", "signer key") from exc
    if len(key) != 32 or base64.b64encode(key).decode() != credential["public_key_base64"] or hashlib.sha256(key).hexdigest() != credential["public_key_fingerprint_sha256"]:
        _fail("NMRPA_CRPG_COMMITTED_KEY_ENCODING", "signer key")
    return key


def _validate_physical_bundle(
    head: Mapping[str, Any], closure: Mapping[str, Any], bootstrap_key: bytes,
    validated: set[tuple[str, int, str]], stack: list[tuple[str, int, str]],
) -> None:
    """Authoritative V4 validator for one physically committed bundle."""
    key_id = _bundle_key(head)
    if key_id in validated:
        return
    if key_id in stack:
        _fail("NMRPA_CRPG_COMMITTED_KEY_REF_CYCLE", "recursive committed reference")
    stack.append(key_id)
    try:
        domain, signed, journal, marker, stored_head = closure["bundles"][head["transaction_id"]]
        if stored_head != head:
            _fail("NMRPA_CRPG_SIGNED_CONTAINER_MISMATCH", "bundle head identity")
        body = signed["record_body"]
        refs = body["ordered_prerequisite_refs"]
        for ref in refs:
            _ref_domain, ref_head = _ref_physical(ref, closure)
            _require_ancestor(ref_head, head, closure)
            _validate_physical_bundle(ref_head, closure, bootstrap_key, validated, stack)
        _validate_prerequisite_semantics(domain["event_kind"], domain, refs, closure, body["issued_at"], marker["committed_at"])

        signature = signed["signature"]
        if signature["signer_mode"] == "synthetic_genesis_bootstrap":
            branch = domain["event_kind"]
            if not (
                branch == "principal_registered"
                or (branch == "identity_registered" and domain.get("role") == "trust_registry_issuer")
                or (branch == "credential_activated" and domain.get("owner_role") == "trust_registry_issuer")
            ):
                _fail("NMRPA_CRPG_BOOTSTRAP_CLOSED", "non-foundational historical bootstrap signature")
            if body["issuer_identity_id"] != BOOTSTRAP_ID or body["issuer_credential_id"] != BOOTSTRAP_ID:
                _fail("NMRPA_CRPG_BOOTSTRAP_STATE", "bootstrap issuer identity")
            verification_key = bootstrap_key
        else:
            ref = signature.get("credential_registration_ref")
            if ref is None:
                _fail("NMRPA_CRPG_COMMITTED_KEY_REF_REQUIRED", "committed signer credential ref")
            try:
                credential, credential_head = _ref_physical(ref, closure)
            except ContractError as exc:
                if exc.code == "NMRPA_CRPG_COMMITTED_KEY_REF_CYCLE":
                    raise
                raise ContractError("NMRPA_CRPG_COMMITTED_KEY_REF_UNTRUSTED", "credential ref unresolved") from exc
            _require_ancestor(credential_head, head, closure)
            _validate_physical_bundle(credential_head, closure, bootstrap_key, validated, stack)
            verification_key = _decode_committed_issuer_key(signature, credential, body, marker)
        _verify_signature(signature, verification_key)
        _verify_signature(journal["synthetic_commit_signature"], bootstrap_key)
        _verify_signature(marker["synthetic_commit_signature"], bootstrap_key)
        validated.add(key_id)
    finally:
        stack.pop()


def _validate_physical_history(
    closure: Mapping[str, Any], bootstrap_key: bytes,
) -> set[tuple[str, int, str]]:
    """Run the authoritative V4 validator over the complete six-log history."""
    validated: set[tuple[str, int, str]] = set()
    ordered_bundles = sorted(
        closure["bundles"].values(),
        key=lambda item: (item[4]["committed_at"], item[4]["logical_name"], item[4]["sequence"]),
    )
    for _domain, _signed, _journal, _marker, historic_head in ordered_bundles:
        _validate_physical_bundle(historic_head, closure, bootstrap_key, validated, [])
    return validated


def _physical_key(
    signature: Mapping[str, Any], closure: Mapping[str, Any], bootstrap_key: bytes,
    body: Mapping[str, Any], committed_at: str,
    validated: set[tuple[str, int, str]], stack: list[tuple[str, int, str]],
) -> bytes:
    if signature["signer_mode"] == "synthetic_genesis_bootstrap":
        return bootstrap_key
    ref = signature.get("credential_registration_ref")
    if ref is None:
        _fail("NMRPA_CRPG_COMMITTED_KEY_REF_REQUIRED", "committed signer credential ref")
    try:
        credential, credential_head = _ref_physical(ref, closure)
    except ContractError as exc:
        raise ContractError("NMRPA_CRPG_COMMITTED_KEY_REF_UNTRUSTED", "credential ref unresolved") from exc
    _validate_physical_bundle(credential_head, closure, bootstrap_key, validated, stack)
    credential_marker = closure["bundles"][credential_head["transaction_id"]][3]
    if _time(credential_marker["committed_at"], "credential.committed_at") >= _time(committed_at, "candidate.committed_at"):
        _fail("NMRPA_CRPG_COMMITTED_KEY_REF_UNTRUSTED", "candidate signer credential is not a strict ancestor")
    marker = {"committed_at": committed_at}
    return _decode_committed_issuer_key(signature, credential, body, marker)


def _physical(intent_or_plan: Mapping[str, Any], descriptor: Mapping[str, Any], root: Path, capability: Any, bootstrap_key: Any) -> dict[str, Any]:
    if type(bootstrap_key) is not bytes: _fail("NMRPA_CRPG_BOOTSTRAP_KEY_SCHEMA" if bootstrap_key is not None else "NMRPA_CRPG_BOOTSTRAP_KEY_REQUIRED", "bootstrap key")
    if len(bootstrap_key) != 32: _fail("NMRPA_CRPG_BOOTSTRAP_KEY_SCHEMA", "bootstrap key length")
    current = writer.describe_synthetic_test_capability(capability, root)
    _root_equal(intent_or_plan["root_instance"], current)
    if intent_or_plan["synthetic_bootstrap_public_key_hex"] != bootstrap_key.hex(): _fail("NMRPA_CRPG_BOOTSTRAP_KEY_MISMATCH", "declared bootstrap key")
    closure = _full_closure(root, descriptor, current)
    # Replay and cryptographically validate every historical envelope before it
    # can supply a prerequisite or committed issuer key.
    validated_bundles = _validate_physical_history(closure, bootstrap_key)
    ordered_bundles = sorted(closure["bundles"].values(), key=lambda item: (item[4]["committed_at"], item[4]["logical_name"], item[4]["sequence"]))
    bootstrap_bundles = sorted(
        (item for item in ordered_bundles if item[1]["signature"]["signer_mode"] == "synthetic_genesis_bootstrap"),
        key=lambda item: BRANCHES[item[0]["event_kind"]][5],
    )
    bootstrap_branches = [item[0]["event_kind"] for item in bootstrap_bundles]
    expected_prefix = ["principal_registered", "identity_registered", "credential_activated"][:len(bootstrap_branches)]
    if bootstrap_branches != expected_prefix:
        _fail("NMRPA_CRPG_BOOTSTRAP_STATE", "historical bootstrap foundation is not exact B0-B2 prefix")
    if len(bootstrap_bundles) >= 2:
        principal, identity = bootstrap_bundles[0][0], bootstrap_bundles[1][0]
        if identity.get("role") != "trust_registry_issuer" or identity.get("principal_registration_ref", {}).get("domain_object_id") != principal.get("principal_id"):
            _fail("NMRPA_CRPG_BOOTSTRAP_STATE", "bootstrap identity foundation")
    if len(bootstrap_bundles) == 3:
        principal, identity, credential = (item[0] for item in bootstrap_bundles)
        if (
            credential.get("owner_role") != "trust_registry_issuer"
            or credential.get("owner_principal_id") != principal.get("principal_id")
            or credential.get("owner_identity_id") != identity.get("identity_id")
        ):
            _fail("NMRPA_CRPG_BOOTSTRAP_STATE", "bootstrap credential foundation")
    branch = intent_or_plan["transition_branch"]
    log_name = BRANCHES[branch][0]
    if closure["logs"][log_name]["head"] != intent_or_plan["expected_previous_head"]: _fail("NMRPA_CRPG_CAS", "selected head")
    domain = intent_or_plan["domain_object"]
    tx = intent_or_plan["transaction_id"]
    if tx in {item[2] for item in closure["transactions"]}: _fail("NMRPA_CRPG_REPLAY", "transaction")
    object_id = domain[BRANCHES[branch][2]]
    if object_id in closure["objects"]: _fail("NMRPA_CRPG_REPLAY", "domain object")
    signature = intent_or_plan["issuer_signature"] if "issuer_signature" in intent_or_plan else intent_or_plan["signed_record"]["signature"]
    refs = intent_or_plan["ordered_prerequisite_refs"] if "ordered_prerequisite_refs" in intent_or_plan else intent_or_plan["signed_record"]["record_body"]["ordered_prerequisite_refs"]
    issued_at = intent_or_plan["issued_at"] if "issued_at" in intent_or_plan else intent_or_plan["signed_record"]["record_body"]["issued_at"]
    committed_at = intent_or_plan["committed_at"] if "committed_at" in intent_or_plan else intent_or_plan["commit_marker"]["committed_at"]
    _validate_prerequisite_semantics(branch, domain, refs, closure, issued_at, committed_at)
    # Per-root historical B0-B3 gate.
    issuer_credentials = [obj for obj, _ in closure["objects"].values() if obj.get("event_kind") == "credential_activated" and obj.get("owner_role") == "trust_registry_issuer"]
    principal_count = sum(obj.get("event_kind") == "principal_registered" for obj, _ in closure["objects"].values())
    issuer_identity_count = sum(obj.get("event_kind") == "identity_registered" and obj.get("role") == "trust_registry_issuer" for obj, _ in closure["objects"].values())
    allowed_bootstrap = (branch == "principal_registered" and principal_count == 0) or (branch == "identity_registered" and principal_count == 1 and issuer_identity_count == 0) or (branch == "credential_activated" and issuer_identity_count == 1 and not issuer_credentials and domain.get("owner_role") == "trust_registry_issuer")
    if bool(issuer_credentials):
        if signature["signer_mode"] != "committed_registry_issuer": _fail("NMRPA_CRPG_BOOTSTRAP_CLOSED", "bootstrap signer permanently closed")
    elif not allowed_bootstrap or signature["signer_mode"] != "synthetic_genesis_bootstrap":
        _fail("NMRPA_CRPG_BOOTSTRAP_STATE", "invalid bootstrap transition")
    candidate_body = intent_or_plan if "issued_at" in intent_or_plan else intent_or_plan["signed_record"]["record_body"]
    if "issuer_identity_id" not in candidate_body:
        candidate_body = {
            "issued_at": intent_or_plan["issued_at"],
            "issuer_identity_id": intent_or_plan["issuer_signature"]["credential_id"] if signature["signer_mode"] == "synthetic_genesis_bootstrap" else _ref_physical(signature["credential_registration_ref"], closure)[0]["owner_identity_id"],
            "issuer_credential_id": signature["credential_id"],
        }
    key = _physical_key(signature, closure, bootstrap_key, candidate_body, committed_at, validated_bundles, [])
    _verify_signature(signature, key)
    journal_sig = intent_or_plan["synthetic_journal_signature"] if "synthetic_journal_signature" in intent_or_plan else intent_or_plan["journal"]["synthetic_commit_signature"]
    marker_sig = intent_or_plan["synthetic_marker_signature"] if "synthetic_marker_signature" in intent_or_plan else intent_or_plan["commit_marker"]["synthetic_commit_signature"]
    _verify_signature(journal_sig, bootstrap_key); _verify_signature(marker_sig, bootstrap_key)
    return closure


def validate_intent(intent: Mapping[str, Any], descriptor: Mapping[str, Any], descriptor_sha256: str, *, project_root: str | os.PathLike[str], capability: Any, synthetic_bootstrap_verification_public_key: bytes) -> dict[str, Any]:
    descriptor = _descriptor(descriptor, descriptor_sha256)
    logical = _validate_intent_logical(intent, descriptor)
    _physical(intent, descriptor, Path(project_root), capability, synthetic_bootstrap_verification_public_key)
    return {"ok": True, "status": "PHYSICALLY_TRUSTED_INTENT", "branch": logical["branch"], "payload_bytes_read": 0}


def _attestation_digest(value: Mapping[str, Any], signature_field: str, own: str, domain_name: str) -> str:
    return digest({key: child for key, child in value.items() if key not in (signature_field, own)}, domain_name)


def plan(intent: Mapping[str, Any], descriptor: Mapping[str, Any], descriptor_sha256: str, *, project_root: str | os.PathLike[str], capability: Any, synthetic_bootstrap_verification_public_key: bytes) -> dict[str, Any]:
    descriptor = _descriptor(descriptor, descriptor_sha256)
    validate_intent(intent, descriptor, descriptor_sha256, project_root=project_root, capability=capability, synthetic_bootstrap_verification_public_key=synthetic_bootstrap_verification_public_key)
    logical = _validate_intent_logical(intent, descriptor)
    branch, log, previous, domain, root_instance = logical["branch"], logical["log"], logical["previous"], logical["domain"], logical["root_instance"]
    sequence = previous["sequence"] + 1
    _, kind, id_field, _, _, _ = BRANCHES[branch]; object_id = domain[id_field]
    paths = _paths(log, branch, intent["transaction_id"], sequence, object_id)
    issuer_identity_id = BOOTSTRAP_ID
    if logical["issuer"]["signer_mode"] == "committed_registry_issuer":
        credential_path = logical["issuer"]["credential_registration_ref"]["domain_object_relative_path"]
        issuer_identity_id = _read_json(Path(project_root), credential_path)["owner_identity_id"]
    body = {"schema_version": "nmrpa.core_registry.record_body.v1", "descriptor_sha256": descriptor_sha256, "project_root_identity_sha256": intent["project_root_identity_sha256"], "root_instance": root_instance, "logical_name": log["logical_name"], "log_kind": log["log_kind"], "log_id": log["log_id"], "transaction_id": intent["transaction_id"], "sequence": sequence, "previous_head_sha256": previous["head_sha256"], "previous_commit_sha256": None if sequence == 1 else previous["commit_sha256"], "event_kind": branch, "issued_at": intent["issued_at"], "domain_object_kind": kind, "domain_object_id": object_id, "domain_object_relative_path": paths["domain_object"], "domain_object_sha256": domain["domain_object_sha256"], "ordered_prerequisite_refs": logical["refs"], "issuer_identity_id": issuer_identity_id, "issuer_credential_id": logical["issuer"]["credential_id"]}
    body_sha = digest(body, "nmrpa.core_registry.record_body.digest.v1")
    if logical["issuer"]["signed_digest"] != body_sha: _fail("NMRPA_CRPG_SIGNED_CONTAINER_MISMATCH", "issuer signed digest")
    signed = {"schema_version": "nmrpa.core_registry.signed_record.v1", "record_body": body, "record_body_sha256": body_sha, "signature": logical["issuer"], "root_instance": root_instance}
    signed["signed_record_sha256"] = digest(signed, "nmrpa.core_registry.signed_record.digest.v1")
    journal = {"schema_version": "nmrpa.core_registry.transaction_journal.v1", "descriptor_sha256": descriptor_sha256, "project_root_identity_sha256": intent["project_root_identity_sha256"], "root_instance": root_instance, "logical_name": log["logical_name"], "log_kind": log["log_kind"], "log_id": log["log_id"], "transaction_id": intent["transaction_id"], "sequence": sequence, "previous_commit_sha256": body["previous_commit_sha256"], "expected_previous_head_sha256": previous["head_sha256"], "domain_object_sha256": domain["domain_object_sha256"], "signed_record_sha256": signed["signed_record_sha256"], "journal_state": "prepared", "prepared_at": intent["prepared_at"], "synthetic_commit_signature": logical["journal_signature"]}
    attestation = _attestation_digest(journal, "synthetic_commit_signature", "journal_sha256", "nmrpa.core_registry.transaction_journal.commit_attestation.v1")
    if logical["journal_signature"]["signed_digest"] != attestation: _fail("NMRPA_CRPG_SIGNED_CONTAINER_MISMATCH", "journal signed digest")
    journal["journal_sha256"] = digest(journal, "nmrpa.core_registry.transaction_journal.digest.v1")
    marker = {"schema_version": "nmrpa.core_registry.commit_marker.v1", "descriptor_sha256": descriptor_sha256, "project_root_identity_sha256": intent["project_root_identity_sha256"], "root_instance": root_instance, "logical_name": log["logical_name"], "log_kind": log["log_kind"], "log_id": log["log_id"], "transaction_id": intent["transaction_id"], "sequence": sequence, "previous_commit_sha256": body["previous_commit_sha256"], "expected_previous_head_sha256": previous["head_sha256"], "domain_object_sha256": domain["domain_object_sha256"], "record_body_sha256": body_sha, "signed_record_sha256": signed["signed_record_sha256"], "journal_sha256": journal["journal_sha256"], "prepared_at": intent["prepared_at"], "committed_at": intent["committed_at"], "synthetic_commit_signature": logical["marker_signature"]}
    marker_attestation = _attestation_digest(marker, "synthetic_commit_signature", "commit_sha256", "nmrpa.core_registry.commit_marker.commit_attestation.v1")
    if logical["marker_signature"]["signed_digest"] != marker_attestation: _fail("NMRPA_CRPG_SIGNED_CONTAINER_MISMATCH", "marker signed digest")
    marker["commit_sha256"] = digest(marker, "nmrpa.core_registry.commit_marker.digest.v1")
    head = {"schema_version": "nmrpa.core_registry_committed_head.v1", "logical_name": log["logical_name"], "log_kind": log["log_kind"], "log_id": log["log_id"], "sequence": sequence, "transaction_id": intent["transaction_id"], "previous_head_sha256": previous["head_sha256"], "previous_commit_sha256": body["previous_commit_sha256"], "domain_object_kind": kind, "domain_object_id": object_id, "domain_object_relative_path": paths["domain_object"], "domain_object_sha256": domain["domain_object_sha256"], "record_body_sha256": body_sha, "signed_record_sha256": signed["signed_record_sha256"], "journal_sha256": journal["journal_sha256"], "commit_sha256": marker["commit_sha256"], "committed_at": intent["committed_at"], "root_instance": root_instance}
    head["head_sha256"] = digest(head, "nmrpa.core_registry.committed_head.digest.v1")
    history = _read_json(Path(project_root), log["historical_heads_locator"])
    result = {"artifact_kind": "core_registry_transaction_plan", "schema_version": PLAN_SCHEMA_VERSION, "mode": "synthetic_bootstrap_compatible_no_actual_write", "transition_branch": branch, "transaction_id": intent["transaction_id"], "authorization_id": intent["transaction_id"], "binding_id": object_id, "descriptor_sha256": descriptor_sha256, "project_root_identity_sha256": intent["project_root_identity_sha256"], "root_instance": root_instance, "synthetic_bootstrap_public_key_hex": intent["synthetic_bootstrap_public_key_hex"], "expected_previous_head": previous, "domain_object": domain, "signed_record": signed, "journal": journal, "commit_marker": marker, "new_head": head, "new_history": [*history, head], "paths": paths, "staging_paths": {key: f"{value}.nmrpa-crpg1-stage" for key, value in paths.items()}, "commit_order": ["domain_object", "signed_record", "journal", "marker", "history", "head"]}
    result["plan_sha256"] = digest(result, "nmrpa.core_registry.transaction_plan.synthetic.v1")
    validate_plan(result, descriptor, descriptor_sha256)
    _physical(result, descriptor, Path(project_root), capability, synthetic_bootstrap_verification_public_key)
    return result


def validate_plan(value: Mapping[str, Any], descriptor: Mapping[str, Any], descriptor_sha256: str) -> dict[str, Any]:
    descriptor = _descriptor(descriptor, descriptor_sha256); _reject_surfaces(value)
    fields = {"artifact_kind", "schema_version", "mode", "transition_branch", "transaction_id", "authorization_id", "binding_id", "descriptor_sha256", "project_root_identity_sha256", "root_instance", "synthetic_bootstrap_public_key_hex", "expected_previous_head", "domain_object", "signed_record", "journal", "commit_marker", "new_head", "new_history", "paths", "staging_paths", "commit_order", "plan_sha256"}
    plan_value = _exact(value, fields, "plan")
    if plan_value["artifact_kind"] != "core_registry_transaction_plan" or plan_value["schema_version"] != PLAN_SCHEMA_VERSION or plan_value["mode"] != "synthetic_bootstrap_compatible_no_actual_write" or plan_value["transition_branch"] not in BRANCHES: _fail("NMRPA_CRPG_SCHEMA", "plan discriminator")
    root_instance = validate_root_instance_commitment_shape(plan_value["root_instance"]); branch = plan_value["transition_branch"]
    domain = _validate_domain(plan_value["domain_object"], branch, root_instance)
    log = next(row for row in descriptor["fixed_logs"] if row["logical_name"] == BRANCHES[branch][0]); previous = _validate_head(plan_value["expected_previous_head"], log, root_instance if plan_value["expected_previous_head"].get("sequence") else None); head = _validate_head(plan_value["new_head"], log, root_instance)
    if head["sequence"] != previous["sequence"] + 1 or plan_value["transaction_id"] != plan_value["authorization_id"] or plan_value["binding_id"] != domain[BRANCHES[branch][2]]: _fail("NMRPA_CRPG_SCHEMA", "plan projection")
    if type(plan_value["new_history"]) is not list or not plan_value["new_history"] or plan_value["new_history"][-1] != head:
        _fail("NMRPA_CRPG_CHAIN", "new history")
    for index, item in enumerate(plan_value["new_history"]):
        validated = _validate_head(item, log, root_instance if index else None)
        if validated["sequence"] != index: _fail("NMRPA_CRPG_CHAIN", "history index")
    _validate_record_bundle(domain, plan_value["signed_record"], plan_value["journal"], plan_value["commit_marker"], head, log, root_instance)
    object_id = domain[BRANCHES[branch][2]]; expected_paths = _paths(log, branch, plan_value["transaction_id"], head["sequence"], object_id)
    if plan_value["paths"] != expected_paths or plan_value["staging_paths"] != {key: f"{path}.nmrpa-crpg1-stage" for key, path in expected_paths.items()} or plan_value["commit_order"] != ["domain_object", "signed_record", "journal", "marker", "history", "head"]:
        _fail("NMRPA_CRPG_PATH", "manifest")
    errors = sorted(_schema("tw_policy_nmrpa3_core_registry_plan.schema.json").iter_errors(plan_value), key=lambda item: list(item.path))
    if errors: _fail("NMRPA_CRPG_STRUCTURAL_SCHEMA", errors[0].message)
    _sha(plan_value["plan_sha256"], "plan_sha256")
    if not _sealed(plan_value, "plan_sha256", "nmrpa.core_registry.transaction_plan.synthetic.v1"): _fail("NMRPA_CRPG_DIGEST", "plan")
    return {"ok": True, "status": "LOGICALLY_VALID_UNTRUSTED_PLAN", "sequence": head["sequence"]}


def _make_ref(plan_value: Mapping[str, Any]) -> dict[str, Any]:
    body = plan_value["signed_record"]["record_body"]; head = plan_value["new_head"]; paths = plan_value["paths"]
    result = {"schema_version": "nmrpa.core_registry.commit_ref.v1", "descriptor_sha256": plan_value["descriptor_sha256"], "project_root_identity_sha256": plan_value["project_root_identity_sha256"], "root_instance": plan_value["root_instance"], "logical_name": body["logical_name"], "log_kind": body["log_kind"], "log_id": body["log_id"], "sequence": body["sequence"], "transaction_id": body["transaction_id"], "event_kind": body["event_kind"], "domain_object_kind": body["domain_object_kind"], "domain_object_id": body["domain_object_id"], "domain_object_relative_path": paths["domain_object"], "domain_object_sha256": body["domain_object_sha256"], "record_relative_path": paths["signed_record"], "record_body_sha256": plan_value["signed_record"]["record_body_sha256"], "signed_record_sha256": plan_value["signed_record"]["signed_record_sha256"], "journal_relative_path": paths["journal"], "journal_sha256": plan_value["journal"]["journal_sha256"], "marker_relative_path": paths["marker"], "commit_sha256": plan_value["commit_marker"]["commit_sha256"], "history_relative_path": paths["history"], "historical_head_sequence": body["sequence"], "historical_head_sha256": head["head_sha256"], "current_head_relative_path": paths["head"]}
    result["commit_ref_sha256"] = digest(result, "nmrpa.core_registry.commit_ref.digest.v1")
    return result


def commit(plan_value: Mapping[str, Any], descriptor: Mapping[str, Any], descriptor_sha256: str, *, project_root: str | os.PathLike[str], capability: Any, synthetic_bootstrap_verification_public_key: bytes, synthetic_fail_after_step: int | None = None) -> dict[str, Any]:
    descriptor = _descriptor(descriptor, descriptor_sha256); validate_plan(plan_value, descriptor, descriptor_sha256); root = Path(project_root)
    before = _physical(plan_value, descriptor, root, capability, synthetic_bootstrap_verification_public_key)
    branch = plan_value["transition_branch"]; log_name = BRANCHES[branch][0]
    def load_closure(where: Path) -> Mapping[str, Any]:
        closure = _full_closure(where, descriptor, plan_value["root_instance"]); selected = closure["logs"][log_name]
        txs = {item[2] for item in closure["transactions"]}; return {"current_head": selected["head"], "history": selected["history"], "transaction_ids": txs, "authorization_ids": set(txs), "binding_ids": set(closure["objects"])}
    def post(where: Path, _validated: Mapping[str, Any]) -> Mapping[str, Any]:
        closure = _full_closure(where, descriptor, plan_value["root_instance"])
        if closure["logs"][log_name]["head"] != plan_value["new_head"]: _fail("NMRPA_CRPG_POST_COMMIT", "head")
        return {"ok": True}
    result = writer.commit_schema_driven_transaction(plan_value, root, capability, validate_plan=lambda item: validate_plan(item, descriptor, descriptor_sha256), load_closure=load_closure, validate_post_commit=post, lock_relative_path=next(row["storage_project_relative_path"] for row in descriptor["fixed_logs"] if row["logical_name"] == log_name), immutable_values={key: plan_value[{"domain_object": "domain_object", "signed_record": "signed_record", "journal": "journal", "marker": "commit_marker"}[key]] for key in ("domain_object", "signed_record", "journal", "marker")}, mutable_values={"history": plan_value["new_history"], "head": plan_value["new_head"]}, synthetic_fail_after_step=synthetic_fail_after_step, immutable_final_no_clobber=True)
    ref = _make_ref(plan_value)
    resolve_commit_ref(ref, descriptor, descriptor_sha256, project_root=root, capability=capability, synthetic_bootstrap_verification_public_key=synthetic_bootstrap_verification_public_key)
    return {**result, "status": "PHYSICALLY_COMMITTED", "commit_ref": ref, "pre_transaction_count": len(before["transactions"])}


def resolve_commit_ref(ref: Mapping[str, Any], descriptor: Mapping[str, Any], descriptor_sha256: str, *, project_root: str | os.PathLike[str], capability: Any, synthetic_bootstrap_verification_public_key: bytes) -> dict[str, Any]:
    descriptor = _descriptor(descriptor, descriptor_sha256); validated = _validate_ref(ref); root = Path(project_root)
    if type(synthetic_bootstrap_verification_public_key) is not bytes or len(synthetic_bootstrap_verification_public_key) != 32: _fail("NMRPA_CRPG_BOOTSTRAP_KEY_SCHEMA", "bootstrap key")
    current = writer.describe_synthetic_test_capability(capability, root); _root_equal(validated["root_instance"], current)
    closure = _full_closure(root, descriptor, current)
    validated_bundles = _validate_physical_history(closure, synthetic_bootstrap_verification_public_key)
    _domain, target_head = _ref_physical(validated, closure)
    _validate_physical_bundle(target_head, closure, synthetic_bootstrap_verification_public_key, validated_bundles, [])
    return {"ok": True, "status": "PHYSICALLY_TRUSTED_COMMIT_REF", "commit_ref": dict(validated), "payload_bytes_read": 0}


__all__ = ["ContractError", "INTENT_SCHEMA_VERSION", "PLAN_SCHEMA_VERSION", "MAX_SEQUENCE", "validate_root_instance_commitment_shape", "validate_intent", "plan", "validate_plan", "commit", "resolve_commit_ref"]
