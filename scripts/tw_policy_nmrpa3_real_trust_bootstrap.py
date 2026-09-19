#!/usr/bin/env python3
"""Isolated NMRPA3 real-trust bootstrap contract.

This module validates caller-pinned descriptors and synthetic bootstrap layouts.
It does not discover sources, read payloads, issue authorizations, or activate a
runtime configuration.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "nmrpa.real_trust_bootstrap.v1"
AUTH_SCHEMA_VERSION = "nmrpa.real_trust_one_shot_authorization.synthetic.v1"
BASE_ID = "nmrpa_isolated_source_base_v1"
BASE_PATH = "data_tw/artifacts/research/nmrpa/immutable_source_roots"
TRUST_BASE_PATH = "data_tw/artifacts/research/nmrpa/trust_bootstrap_v1"
ROOT_KINDS = (
    "sealed_calendar",
    "formal_instruments",
    "adjusted_price",
    "twii",
    "modela_signal",
)
FIXED_LOGS = (
    ("principal_registry_log", "issuer_registry", "nmrpa.principal_registry.v1", 1),
    ("identity_registry_log", "issuer_registry", "nmrpa.identity_registry.v1", 2),
    ("credential_registry_log", "issuer_registry", "nmrpa.credential_registry.v1", 3),
    ("trusted_service_registration_log", "issuer_registry", "nmrpa.trusted_service_registration.v1", 4),
    ("publication_authority_registration_log", "publication_authority_registry", "nmrpa.publication_authority_registration.v1", 5),
    ("capture_recorder_registration_log", "capture_recorder_registry", "nmrpa.capture_recorder_registration.v1", 6),
)
OWNER_ROLE = "trust_registry_issuer"
TRUST_STORE_KINDS = (
    "root_locator_registry",
    "principal_identity_credential_registry_stores",
    "trusted_actor_registry_stores",
    "authorization_ledger",
    "anchor_ledger",
    "binding_store",
    "immutable_historical_head_storage",
    "project_root_identity_marker",
    "preopened_descriptor_policy",
)
CONTRACT_DIGEST_NAMES = (
    "feature_contract_sha256",
    "target_contract_sha256",
    "split_contract_sha256",
    "decision_time_policy_sha256",
)
FORBIDDEN_SEGMENTS = {"", ".", "..", "latest", "current", "accepted", "publish"}
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
ID_RE = re.compile(r"^[a-z][a-z0-9_.-]{2,127}$")
SYNTHETIC_PREFIX = "synthetic_"
PROJECT_ROOT_ID = "synthetic_tmp_project_root_v1"


class ContractError(ValueError):
    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class CallerPinnedTrust:
    descriptor_sha256: str
    project_root_realpath: str
    project_root_identity_sha256: str
    contract_digests: Mapping[str, str]
    fixed_log_heads: Mapping[str, str]


def canonical_json(value: Any) -> bytes:
    def walk(item: Any) -> None:
        if isinstance(item, float) and not math.isfinite(item):
            raise ContractError("NMRPA_TR_E_NONFINITE", "non-finite JSON number")
        if isinstance(item, dict):
            for key, child in item.items():
                if not isinstance(key, str) or unicodedata.normalize("NFC", key) != key:
                    raise ContractError("NMRPA_TR_E_SCHEMA", "keys must be NFC strings")
                walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)

    walk(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value: Any, domain: str | None = None) -> str:
    raw = canonical_json(value)
    if domain:
        raw = (domain + "\n").encode() + raw
    return hashlib.sha256(raw).hexdigest()


def checksum_without(value: Mapping[str, Any], field: str, domain: str | None = None) -> str:
    return digest({key: child for key, child in value.items() if key != field}, domain)


def _exact(value: Any, fields: set[str], where: str) -> None:
    if type(value) is not dict:
        raise ContractError("NMRPA_TR_E_SCHEMA", f"{where} must be object")
    if set(value) != fields:
        raise ContractError("NMRPA_TR_E_SCHEMA", f"{where} fields differ")


def _exact_json_types(value: Any, template: Any, where: str) -> None:
    """Recursively enforce JSON types without Python bool/int equivalence."""
    if type(value) is not type(template):
        raise ContractError("NMRPA_TR_E_SCHEMA", f"{where} has wrong type")
    if type(template) is dict:
        if set(value) != set(template):
            raise ContractError("NMRPA_TR_E_SCHEMA", f"{where} fields differ")
        for key in template:
            _exact_json_types(value[key], template[key], f"{where}.{key}")
    elif type(template) is list:
        if len(value) != len(template):
            raise ContractError("NMRPA_TR_E_SCHEMA", f"{where} length differs")
        for index, (child, expected) in enumerate(zip(value, template)):
            _exact_json_types(child, expected, f"{where}[{index}]")


def _sha(value: Any, where: str) -> None:
    if type(value) is not str or not SHA_RE.fullmatch(value):
        raise ContractError("NMRPA_TR_E_SCHEMA", f"{where} must be sha256")


def _identifier(value: Any, where: str) -> None:
    if type(value) is not str or not ID_RE.fullmatch(value):
        raise ContractError("NMRPA_TR_E_SCHEMA", f"invalid {where}")


def _time(value: Any, where: str) -> datetime:
    if type(value) is not str:
        raise ContractError("NMRPA_TR_E_SCHEMA", f"invalid {where}")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError("NMRPA_TR_E_SCHEMA", f"invalid {where}") from exc
    if result.tzinfo is None or result.microsecond:
        raise ContractError("NMRPA_TR_E_SCHEMA", f"{where} must be timezone-aware whole seconds")
    return result


def _relative_path(value: Any, where: str, *, expected: str | None = None) -> str:
    if (
        type(value) is not str
        or "\\" in value
        or "*" in value
        or "?" in value
        or "//" in value
        or value != value.strip()
    ):
        raise ContractError("NMRPA_TR_E_PATH", f"invalid {where}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part.lower() in FORBIDDEN_SEGMENTS for part in path.parts):
        raise ContractError("NMRPA_TR_E_PATH", f"unsafe {where}")
    if expected is not None and value != expected:
        raise ContractError("NMRPA_TR_E_LOCATOR", f"{where} drift")
    return value


def expected_descriptor() -> dict[str, Any]:
    roots = []
    for order, kind in enumerate(ROOT_KINDS, 1):
        root_id = f"nmrpa_{kind}_root_v1"
        roots.append({
            "order": order,
            "base_id": BASE_ID,
            "base_project_relative_path": BASE_PATH,
            "root_kind": kind,
            "root_id": root_id,
            "root_project_relative_path": f"{BASE_PATH}/{kind}/{root_id}",
            "locator_token": f"NMRPA_REAL_ROOT_{kind.upper()}_V1",
            "reservation_status": "reserved_empty",
            "payload_present": False,
            "activation_ref": None,
            "seal_ref": None,
        })
    logs = []
    for logical, kind, log_id, order in FIXED_LOGS:
        base = f"{TRUST_BASE_PATH}/fixed_logs/{logical}"
        logs.append({
            "bootstrap_order": order,
            "logical_name": logical,
            "log_kind": kind,
            "log_id": log_id,
            "owner_role": OWNER_ROLE,
            "storage_id": f"nmrpa.storage.{logical}.v1",
            "storage_project_relative_path": base,
            "genesis_locator": f"{base}/genesis.json",
            "current_head_locator": f"{base}/head.json",
            "historical_heads_locator": f"{base}/historical_heads.json",
            "journal_locator": f"{base}/journals",
            "commit_marker_locator": f"{base}/commit_markers",
        })
    stores = []
    for order, kind in enumerate(TRUST_STORE_KINDS, 1):
        stores.append({
            "order": order,
            "store_kind": kind,
            "store_id": f"nmrpa.store.{kind}.v1",
            "project_relative_path": f"{TRUST_BASE_PATH}/stores/{kind}",
            "caller_pinned": True,
            "runtime_override_allowed": False,
            "env_override_allowed": False,
            "package_override_allowed": False,
        })
    descriptor = {
        "schema_version": SCHEMA_VERSION,
        "bootstrap_id": "nmrpa.real_trust.bootstrap.v1",
        "mode": "descriptor_only_no_payload_read",
        "runtime_overrides": {},
        "root_reservations": roots,
        "fixed_logs": logs,
        "trust_stores": stores,
        "capabilities": {
            "create_storage": False,
            "read_payload": False,
            "issue_authorization": False,
            "record_trust": False,
            "run_real_date": False,
        },
    }
    descriptor["descriptor_sha256"] = digest(descriptor, "nmrpa.real_trust.bootstrap.v1")
    return descriptor


def validate_bootstrap_descriptor(descriptor: Mapping[str, Any], pins: CallerPinnedTrust) -> dict[str, Any]:
    _exact(descriptor, {
        "schema_version", "bootstrap_id", "mode", "runtime_overrides", "root_reservations",
        "fixed_logs", "trust_stores", "capabilities", "descriptor_sha256",
    }, "descriptor")
    if descriptor["runtime_overrides"] != {}:
        raise ContractError("NMRPA_TR_E_BOOTSTRAP_PIN", "runtime overrides forbidden")
    _exact_json_types(descriptor, expected_descriptor(), "descriptor")
    if descriptor != expected_descriptor():
        raise ContractError("NMRPA_TR_E_BOOTSTRAP_PIN", "descriptor differs from frozen mapping")
    if descriptor["descriptor_sha256"] != pins.descriptor_sha256:
        raise ContractError("NMRPA_TR_E_CALLER_PIN", "caller descriptor pin mismatch")
    _sha(pins.descriptor_sha256, "descriptor pin")
    _sha(pins.project_root_identity_sha256, "project root identity pin")
    if type(pins.descriptor_sha256) is not str or type(pins.project_root_realpath) is not str:
        raise ContractError("NMRPA_TR_E_CALLER_PIN", "caller string pins have wrong type")
    if type(pins.contract_digests) is not dict or set(pins.contract_digests) != set(CONTRACT_DIGEST_NAMES):
        raise ContractError("NMRPA_TR_E_CALLER_PIN", "contract digest pins differ")
    for value in pins.contract_digests.values():
        _sha(value, "contract digest pin")
    if type(pins.fixed_log_heads) is not dict or set(pins.fixed_log_heads) != {row[0] for row in FIXED_LOGS}:
        raise ContractError("NMRPA_TR_E_CALLER_PIN", "fixed head pins differ")
    for value in pins.fixed_log_heads.values():
        _sha(value, "fixed log head pin")
    root_real = os.path.realpath(pins.project_root_realpath)
    if root_real != pins.project_root_realpath or not os.path.isabs(root_real):
        raise ContractError("NMRPA_TR_E_CALLER_PIN", "project root pin must be canonical absolute path")
    return {"ok": True, "root_count": 5, "fixed_log_count": 6, "trust_store_count": len(TRUST_STORE_KINDS)}


def _open_confined(project_root: Path, relative: str, expected_type: str) -> Path:
    _relative_path(relative, "storage locator")
    current = project_root
    for part in PurePosixPath(relative).parts:
        current = current / part
        try:
            mode = os.lstat(current).st_mode
        except FileNotFoundError as exc:
            raise ContractError("NMRPA_TR_E_MISSING_STORAGE", relative) from exc
        if stat.S_ISLNK(mode):
            raise ContractError("NMRPA_TR_E_SYMLINK", relative)
    final_mode = os.lstat(current).st_mode
    if expected_type == "directory" and not stat.S_ISDIR(final_mode):
        raise ContractError("NMRPA_TR_E_FILE_TYPE", relative)
    if expected_type == "file" and not stat.S_ISREG(final_mode):
        raise ContractError("NMRPA_TR_E_FILE_TYPE", relative)
    if os.path.commonpath((str(project_root), str(current.resolve()))) != str(project_root):
        raise ContractError("NMRPA_TR_E_PATH_ESCAPE", relative)
    return current


def _read_json_file(project_root: Path, relative: str) -> Any:
    path = _open_confined(project_root, relative, "file")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        raw = os.read(fd, 1_048_577)
    finally:
        os.close(fd)
    if len(raw) > 1_048_576:
        raise ContractError("NMRPA_TR_E_FILE_SIZE", relative)
    try:
        return json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("NMRPA_TR_E_STORAGE_JSON", relative) from exc


def _validate_genesis(log: Mapping[str, Any], genesis: Any, head: Any, history: Any) -> str:
    _exact(genesis, {"schema_version", "logical_name", "log_kind", "log_id", "owner_role", "sequence", "previous_head_sha256", "genesis_sha256"}, "genesis")
    _exact(head, {"schema_version", "logical_name", "log_id", "sequence", "previous_head_sha256", "record_sha256", "head_sha256"}, "head")
    if not isinstance(history, list) or len(history) != 1 or history[0] != head:
        raise ContractError("NMRPA_TR_E_HEAD_HISTORY", "genesis history mismatch")
    expected_genesis = {
        "schema_version": "nmrpa.log_genesis.v1", "logical_name": log["logical_name"],
        "log_kind": log["log_kind"], "log_id": log["log_id"], "owner_role": OWNER_ROLE,
        "sequence": 0, "previous_head_sha256": None,
    }
    _exact_json_types(genesis, {**expected_genesis, "genesis_sha256": "0" * 64}, "genesis")
    if {k: v for k, v in genesis.items() if k != "genesis_sha256"} != expected_genesis:
        raise ContractError("NMRPA_TR_E_LOG_IDENTITY", "genesis identity drift")
    if genesis["genesis_sha256"] != digest(expected_genesis, "nmrpa.log.genesis.v1"):
        raise ContractError("NMRPA_TR_E_DIGEST", "genesis digest mismatch")
    expected_head = {
        "schema_version": "nmrpa.log_head.v1", "logical_name": log["logical_name"],
        "log_id": log["log_id"], "sequence": 0, "previous_head_sha256": None,
        "record_sha256": genesis["genesis_sha256"],
    }
    _exact_json_types(head, {**expected_head, "head_sha256": "0" * 64}, "head")
    _exact_json_types(history, [{**expected_head, "head_sha256": "0" * 64}], "historical heads")
    if {k: v for k, v in head.items() if k != "head_sha256"} != expected_head:
        raise ContractError("NMRPA_TR_E_HEAD_CHAIN", "head identity/chain mismatch")
    expected_sha = digest(expected_head, "nmrpa.log.head.v1")
    if head["head_sha256"] != expected_sha:
        raise ContractError("NMRPA_TR_E_DIGEST", "head digest mismatch")
    return expected_sha


def validate_storage_layout(descriptor: Mapping[str, Any], pins: CallerPinnedTrust) -> dict[str, Any]:
    validate_bootstrap_descriptor(descriptor, pins)
    project_root = Path(pins.project_root_realpath)
    if not project_root.is_dir() or project_root.is_symlink() or project_root.resolve() != project_root:
        raise ContractError("NMRPA_TR_E_PROJECT_ROOT", "project root identity invalid")
    marker_desc = next(item for item in descriptor["trust_stores"] if item["store_kind"] == "project_root_identity_marker")
    marker_path = f"{marker_desc['project_relative_path']}/identity.json"
    marker = _read_json_file(project_root, marker_path)
    _exact(marker, {"schema_version", "bootstrap_id", "project_root_id", "identity_sha256"}, "project root marker")
    marker_template = {
        "schema_version": "nmrpa.project_root_identity.v1",
        "bootstrap_id": descriptor["bootstrap_id"],
        "project_root_id": PROJECT_ROOT_ID,
        "identity_sha256": "0" * 64,
    }
    _exact_json_types(marker, marker_template, "project root marker")
    if (
        marker["schema_version"] != "nmrpa.project_root_identity.v1"
        or marker["bootstrap_id"] != descriptor["bootstrap_id"]
        or marker["project_root_id"] != PROJECT_ROOT_ID
    ):
        raise ContractError("NMRPA_TR_E_PROJECT_ROOT", "project marker identity mismatch")
    if marker["identity_sha256"] != checksum_without(marker, "identity_sha256", "nmrpa.project.root.v1") or marker["identity_sha256"] != pins.project_root_identity_sha256:
        raise ContractError("NMRPA_TR_E_PROJECT_ROOT", "project marker pin mismatch")

    for root in descriptor["root_reservations"]:
        root_path = _open_confined(project_root, root["root_project_relative_path"], "directory")
        if any(root_path.iterdir()):
            raise ContractError("NMRPA_TR_E_PAYLOAD_PRESENT", root["root_kind"])

    seen_paths: set[str] = set()
    for store in descriptor["trust_stores"]:
        path = store["project_relative_path"]
        if path in seen_paths:
            raise ContractError("NMRPA_TR_E_CROSS_STORE_ALIAS", path)
        seen_paths.add(path)
        _open_confined(project_root, path, "directory")

    heads = {}
    for log in descriptor["fixed_logs"]:
        _open_confined(project_root, log["storage_project_relative_path"], "directory")
        journal = _open_confined(project_root, log["journal_locator"], "directory")
        markers = _open_confined(project_root, log["commit_marker_locator"], "directory")
        if any(journal.iterdir()) or any(markers.iterdir()):
            raise ContractError("NMRPA_TR_E_ORPHAN_TRANSACTION", log["logical_name"])
        genesis = _read_json_file(project_root, log["genesis_locator"])
        head = _read_json_file(project_root, log["current_head_locator"])
        history = _read_json_file(project_root, log["historical_heads_locator"])
        head_sha = _validate_genesis(log, genesis, head, history)
        if pins.fixed_log_heads[log["logical_name"]] != head_sha:
            raise ContractError("NMRPA_TR_E_HEAD_ROLLBACK", log["logical_name"])
        heads[log["logical_name"]] = head_sha
    return {"ok": True, "reserved_empty_roots": 5, "validated_fixed_heads": heads, "payload_bytes_read": 0}


def validate_one_shot_authorization(auth: Mapping[str, Any], descriptor: Mapping[str, Any], pins: CallerPinnedTrust) -> dict[str, Any]:
    validate_bootstrap_descriptor(descriptor, pins)
    _exact(auth, {
        "schema_version", "authorization_id", "target_placeholder", "authorization_state",
        "ordered_root_refs", "required_log_heads", "contract_digests", "allowed_output_root",
        "external_input_anchor_locator", "event_anchor_locator", "issued_at", "not_before",
        "expires_at", "max_consumptions", "consumption_count", "terminal",
        "allow_payload_read", "capabilities", "issuer_proof", "authorization_sha256",
    }, "authorization")
    _exact_json_types(auth, build_synthetic_authorization(descriptor, pins), "authorization")
    if auth["schema_version"] != AUTH_SCHEMA_VERSION or not auth["authorization_id"].startswith(SYNTHETIC_PREFIX):
        raise ContractError("NMRPA_TR_E_REAL_AUTH", "only synthetic authorization fixtures are accepted")
    if auth["target_placeholder"] != "__NMRPA_EXACT_SINGLE_TARGET_NOT_BOUND__":
        raise ContractError("NMRPA_TR_E_REAL_TARGET", "real target is not authorized")
    expected_roots = [{
        "order": root["order"], "root_kind": root["root_kind"], "root_id": root["root_id"],
        "locator_token": root["locator_token"], "reservation_status": "reserved_empty",
    } for root in descriptor["root_reservations"]]
    if auth["ordered_root_refs"] != expected_roots:
        raise ContractError("NMRPA_TR_E_AUTH_SCOPE", "ordered root scope mismatch")
    expected_heads = [{
        "bootstrap_order": log["bootstrap_order"], "logical_name": log["logical_name"],
        "log_id": log["log_id"], "head_sha256": pins.fixed_log_heads[log["logical_name"]],
    } for log in descriptor["fixed_logs"]]
    if auth["required_log_heads"] != expected_heads or auth["contract_digests"] != dict(pins.contract_digests):
        raise ContractError("NMRPA_TR_E_AUTH_PIN", "head or contract digest mismatch")
    _relative_path(auth["allowed_output_root"], "allowed output root", expected="SYNTHETIC_TMP_ONLY/nmrpa/no_output")
    for field in ("external_input_anchor_locator", "event_anchor_locator"):
        if auth[field] not in ("synthetic://external-input-anchor/not-bound", "synthetic://event-anchor/not-bound"):
            raise ContractError("NMRPA_TR_E_AUTH_ANCHOR", f"invalid {field}")
    issued, not_before, expires = (_time(auth[key], key) for key in ("issued_at", "not_before", "expires_at"))
    if not (issued <= not_before < expires) or any(value.year != 2099 for value in (issued, not_before, expires)):
        raise ContractError("NMRPA_TR_E_AUTH_TIME", "synthetic trusted-time window invalid")
    if auth["authorization_state"] != "reserved" or auth["max_consumptions"] != 1 or auth["consumption_count"] != 0 or auth["terminal"] is not False:
        raise ContractError("NMRPA_TR_E_AUTH_REUSE", "one-shot state invalid")
    if auth["allow_payload_read"] != {"allowed": True, "root_kinds": list(ROOT_KINDS), "sealed_only": True, "max_roots": 5}:
        raise ContractError("NMRPA_TR_E_AUTH_SCOPE", "payload read scope is not exact")
    expected_capabilities = {
        "binding": False, "candidate": False, "event": False, "metric": False,
        "training": False, "publish": False, "network": False, "database": False,
    }
    if auth["capabilities"] != expected_capabilities:
        raise ContractError("NMRPA_TR_E_AUTH_CAPABILITY", "forbidden capability enabled")
    proof = auth["issuer_proof"]
    _exact(proof, {"proof_mode", "issuer_principal_id", "issuer_identity_id", "issuer_credential_id", "issuer_role", "credential_status", "credential_transition_sha256", "issuer_registry_head_sha256", "commit_proof_sha256"}, "issuer proof")
    for field in ("issuer_principal_id", "issuer_identity_id", "issuer_credential_id"):
        _identifier(proof[field], field)
        if not proof[field].startswith(SYNTHETIC_PREFIX):
            raise ContractError("NMRPA_TR_E_REAL_AUTH", "real issuer proof forbidden")
    if proof["proof_mode"] != "synthetic_unissued_fixture" or proof["issuer_role"] != OWNER_ROLE or proof["credential_status"] != "active":
        raise ContractError("NMRPA_TR_E_ISSUER_PROOF", "issuer proof state invalid")
    for field in ("credential_transition_sha256", "issuer_registry_head_sha256", "commit_proof_sha256"):
        _sha(proof[field], field)
    if proof["issuer_registry_head_sha256"] != pins.fixed_log_heads["credential_registry_log"]:
        raise ContractError("NMRPA_TR_E_ISSUER_PROOF", "issuer head not caller pinned")
    expected_commit = digest({k: v for k, v in proof.items() if k != "commit_proof_sha256"}, "nmrpa.synthetic.issuer.proof.v1")
    if proof["commit_proof_sha256"] != expected_commit:
        raise ContractError("NMRPA_TR_E_ISSUER_PROOF", "issuer commit proof mismatch")
    if auth["authorization_sha256"] != checksum_without(auth, "authorization_sha256", "nmrpa.synthetic.one_shot.authorization.v1"):
        raise ContractError("NMRPA_TR_E_DIGEST", "authorization digest mismatch")
    return {"ok": True, "synthetic_only": True, "max_consumptions": 1, "real_target_bound": False}


def build_synthetic_authorization(descriptor: Mapping[str, Any], pins: CallerPinnedTrust) -> dict[str, Any]:
    proof = {
        "proof_mode": "synthetic_unissued_fixture",
        "issuer_principal_id": "synthetic_principal_trust_issuer",
        "issuer_identity_id": "synthetic_identity_trust_issuer",
        "issuer_credential_id": "synthetic_credential_trust_issuer",
        "issuer_role": OWNER_ROLE,
        "credential_status": "active",
        "credential_transition_sha256": digest("synthetic credential transition"),
        "issuer_registry_head_sha256": pins.fixed_log_heads["credential_registry_log"],
    }
    proof["commit_proof_sha256"] = digest(proof, "nmrpa.synthetic.issuer.proof.v1")
    auth = {
        "schema_version": AUTH_SCHEMA_VERSION,
        "authorization_id": "synthetic_one_shot_authorization_fixture_v1",
        "target_placeholder": "__NMRPA_EXACT_SINGLE_TARGET_NOT_BOUND__",
        "authorization_state": "reserved",
        "ordered_root_refs": [{
            "order": root["order"], "root_kind": root["root_kind"], "root_id": root["root_id"],
            "locator_token": root["locator_token"], "reservation_status": "reserved_empty",
        } for root in descriptor["root_reservations"]],
        "required_log_heads": [{
            "bootstrap_order": log["bootstrap_order"], "logical_name": log["logical_name"],
            "log_id": log["log_id"], "head_sha256": pins.fixed_log_heads[log["logical_name"]],
        } for log in descriptor["fixed_logs"]],
        "contract_digests": dict(pins.contract_digests),
        "allowed_output_root": "SYNTHETIC_TMP_ONLY/nmrpa/no_output",
        "external_input_anchor_locator": "synthetic://external-input-anchor/not-bound",
        "event_anchor_locator": "synthetic://event-anchor/not-bound",
        "issued_at": "2099-01-01T00:00:00Z",
        "not_before": "2099-01-01T00:00:00Z",
        "expires_at": "2099-01-01T00:05:00Z",
        "max_consumptions": 1,
        "consumption_count": 0,
        "terminal": False,
        "allow_payload_read": {"allowed": True, "root_kinds": list(ROOT_KINDS), "sealed_only": True, "max_roots": 5},
        "capabilities": {"binding": False, "candidate": False, "event": False, "metric": False, "training": False, "publish": False, "network": False, "database": False},
        "issuer_proof": proof,
    }
    auth["authorization_sha256"] = digest(auth, "nmrpa.synthetic.one_shot.authorization.v1")
    return auth


__all__ = [
    "AUTH_SCHEMA_VERSION", "BASE_PATH", "CallerPinnedTrust", "ContractError",
    "FIXED_LOGS", "ROOT_KINDS", "TRUST_BASE_PATH", "build_synthetic_authorization",
    "canonical_json", "checksum_without", "digest", "expected_descriptor",
    "validate_bootstrap_descriptor", "validate_one_shot_authorization", "validate_storage_layout",
]
