#!/usr/bin/env python3
"""Synthetic-only immutable binding transaction writer for NMRPA3 T_R-E.

The writer accepts sealed payload metadata, never payload locations or bytes.
Planning and validation are pure. Commit is restricted to a capability-bound
canonical directory below /tmp and explicitly rejects this repository root.
"""

from __future__ import annotations

import base64
import binascii
import fcntl
import json
import math
import os
import re
import stat
import secrets
import hashlib
import unicodedata
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping

from tw_policy_nmrpa3_real_trust_bootstrap import (
    FIXED_LOGS,
    ROOT_KINDS,
    TRUST_BASE_PATH,
    canonical_json,
    digest,
    expected_descriptor,
)


INTENT_SCHEMA_VERSION = "nmrpa.immutable_binding_intent.synthetic.v1"
PLAN_SCHEMA_VERSION = "nmrpa.immutable_binding_transaction_plan.synthetic.v1"
RECORD_SCHEMA_VERSION = "nmrpa.immutable_binding_record.v1"
ANCHOR_SCHEMA_VERSION = "nmrpa.immutable_binding_anchor.v1"
BODY_SCHEMA_VERSION = "nmrpa.commit_record_body.v1"
SIGNED_SCHEMA_VERSION = "nmrpa.signed_record.v1"
JOURNAL_SCHEMA_VERSION = "nmrpa.transaction_journal.v1"
MARKER_SCHEMA_VERSION = "nmrpa.commit_marker.v1"
HEAD_SCHEMA_VERSION = "nmrpa.committed_head.v1"
CAPABILITY_NAME = "NMRPA3_T_R_E_SYNTHETIC_TEST_COMMIT_V1"
ACTUAL_PROJECT_ROOT = Path(__file__).resolve().parents[1]

SHA_RE = re.compile(r"^[0-9a-f]{64}$")
ID_RE = re.compile(r"^[a-z][a-z0-9_.-]{2,127}$")
TX_RE = re.compile(r"^txn_synthetic_[a-z0-9._-]{8,96}$")
FORBIDDEN_ALIAS = {"latest", "current", "accepted", "publish"}
FORBIDDEN_KEY_PARTS = {
    "payload_path", "payload_bytes", "file_handle", "label", "metric",
    "outcome", "candidate", "event", "training",
}
ROOT_IDS = {kind: f"nmrpa_{kind}_root_v1" for kind in ROOT_KINDS}
LOG_BY_NAME = {row[0]: row for row in FIXED_LOGS}


class ContractError(ValueError):
    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


class SyntheticTestCapability:
    __slots__ = ("project_root_realpath", "capability_name", "_nonce", "_sealed")

    def __new__(cls, *args: Any, **kwargs: Any) -> "SyntheticTestCapability":
        if kwargs.pop("_issuer_secret", None) is not _CAPABILITY_ISSUER_SECRET:
            raise TypeError("SyntheticTestCapability may only be issued by the writer")
        return super().__new__(cls)

    def __init__(self, project_root_realpath: str, capability_name: str, nonce: str, **_: Any) -> None:
        object.__setattr__(self, "project_root_realpath", project_root_realpath)
        object.__setattr__(self, "capability_name", capability_name)
        object.__setattr__(self, "_nonce", nonce)
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("capability is immutable")

    def __copy__(self) -> "SyntheticTestCapability":
        raise TypeError("capability cannot be copied")

    def __deepcopy__(self, memo: Any) -> "SyntheticTestCapability":
        raise TypeError("capability cannot be deep-copied")


_CAPABILITY_ISSUER_SECRET = object()
_ISSUED_CAPABILITIES: dict[SyntheticTestCapability, dict[str, Any]] = {}
_TAINTED_ROOT_IDENTITIES: set[tuple[int, int]] = set()


def _fail(code: str, detail: str) -> None:
    raise ContractError(code, detail)


def _exact(value: Any, fields: set[str], where: str) -> None:
    if type(value) is not dict or set(value) != fields:
        _fail("NMRPA_TR_E_SCHEMA", f"{where} exact fields differ")


def _str(value: Any, where: str) -> str:
    if type(value) is not str or not value or unicodedata.normalize("NFC", value) != value:
        _fail("NMRPA_TR_E_SCHEMA", f"{where} must be a non-empty NFC string")
    return value


def _identifier(value: Any, where: str) -> str:
    value = _str(value, where)
    if not ID_RE.fullmatch(value) or value.casefold() in FORBIDDEN_ALIAS:
        _fail("NMRPA_TR_E_SCHEMA", f"invalid {where}")
    return value


def _sha(value: Any, where: str) -> str:
    if type(value) is not str or not SHA_RE.fullmatch(value):
        _fail("NMRPA_TR_E_SCHEMA", f"{where} must be lowercase sha256")
    return value


def _integer(value: Any, where: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        _fail("NMRPA_TR_E_SCHEMA", f"{where} must be integer >= {minimum}")
    return value


def _optional_sha(value: Any, where: str) -> str | None:
    if value is None:
        return None
    return _sha(value, where)


def _literal(value: Any, expected: str, where: str) -> str:
    if type(value) is not str or value != expected:
        _fail("NMRPA_TR_E_SCHEMA", f"{where} must equal frozen literal")
    return value


def _time(value: Any, where: str) -> datetime:
    value = _str(value, where)
    if not value.endswith("Z"):
        _fail("NMRPA_TR_E_SCHEMA", f"{where} must be UTC Z time")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ContractError("NMRPA_TR_E_SCHEMA", f"invalid {where}") from exc
    if parsed.microsecond:
        _fail("NMRPA_TR_E_SCHEMA", f"{where} must use whole seconds")
    return parsed


def _date(value: Any, where: str) -> date:
    value = _str(value, where)
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ContractError("NMRPA_TR_E_SCHEMA", f"invalid {where}") from exc
    if parsed.isoformat() != value:
        _fail("NMRPA_TR_E_SCHEMA", f"non-canonical {where}")
    return parsed


def _relative(value: Any, where: str, expected: str | None = None) -> str:
    value = _str(value, where)
    path = PurePosixPath(value)
    if (
        path.is_absolute() or "\\" in value or "//" in value or value != value.strip()
        or any(part.casefold() in FORBIDDEN_ALIAS | {"", ".", ".."} for part in path.parts)
    ):
        _fail("NMRPA_TR_E_PATH", f"unsafe {where}")
    if expected is not None and value != expected:
        _fail("NMRPA_TR_E_PIN", f"{where} differs from caller pin")
    return value


def _reject_forbidden_values(value: Any, where: str = "intent") -> None:
    if isinstance(value, (bytes, bytearray, memoryview)) or hasattr(value, "read"):
        _fail("NMRPA_TR_E_PAYLOAD_INPUT", f"bytes/file handle forbidden at {where}")
    if type(value) is float and not math.isfinite(value):
        _fail("NMRPA_TR_E_SCHEMA", f"non-finite number at {where}")
    if type(value) is dict:
        for key, child in value.items():
            if type(key) is not str:
                _fail("NMRPA_TR_E_SCHEMA", f"non-string key at {where}")
            folded = key.casefold()
            if folded in FORBIDDEN_KEY_PARTS or any(part in folded for part in ("payload_path", "payload_bytes", "file_handle")):
                _fail("NMRPA_TR_E_PAYLOAD_INPUT", f"forbidden field {key}")
            if any(part in folded for part in ("label", "metric", "outcome", "candidate", "training")):
                _fail("NMRPA_TR_E_FORBIDDEN_DOMAIN", f"forbidden field {key}")
            _reject_forbidden_values(child, f"{where}.{key}")
    elif type(value) is list:
        for index, child in enumerate(value):
            _reject_forbidden_values(child, f"{where}[{index}]")


def _without(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    return {key: child for key, child in value.items() if key != field}


def _sealed(value: Mapping[str, Any], field: str, domain: str) -> bool:
    return value[field] == digest(_without(value, field), domain)


def issue_synthetic_test_capability(project_root: str | os.PathLike[str]) -> SyntheticTestCapability:
    if isinstance(project_root, (bytes, bytearray)):
        _fail("NMRPA_TR_E_PROJECT_ROOT", "project root bytes forbidden")
    root = Path(project_root)
    if not root.is_absolute() or root.is_symlink() or not root.is_dir() or root.resolve() != root:
        _fail("NMRPA_TR_E_PROJECT_ROOT", "project root must be canonical absolute directory")
    if root == ACTUAL_PROJECT_ROOT or os.path.commonpath((str(root), str(ACTUAL_PROJECT_ROOT))) == str(ACTUAL_PROJECT_ROOT):
        _fail("NMRPA_TR_E_ACTUAL_ROOT_FORBIDDEN", "actual repository identity is forbidden")
    if os.path.commonpath((str(root), "/tmp")) != "/tmp":
        _fail("NMRPA_TR_E_SYNTHETIC_ONLY", "test capability is limited to /tmp")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    root_fd = os.open(root, flags)
    identity = os.fstat(root_fd)
    lstat_identity = os.lstat(root)
    if (identity.st_dev, identity.st_ino) != (lstat_identity.st_dev, lstat_identity.st_ino):
        os.close(root_fd)
        _fail("NMRPA_TR_E_CAPABILITY", "root identity changed while issuing capability")
    nonce = secrets.token_hex(32)
    token = SyntheticTestCapability(
        str(root), CAPABILITY_NAME, nonce, _issuer_secret=_CAPABILITY_ISSUER_SECRET,
    )
    _ISSUED_CAPABILITIES[token] = {
        "nonce": nonce, "root": str(root), "root_fd": root_fd,
        "st_dev": identity.st_dev, "st_ino": identity.st_ino, "revoked": False,
    }
    return token


def revoke_synthetic_test_capability(token: SyntheticTestCapability) -> None:
    state = _ISSUED_CAPABILITIES.pop(token, None)
    if state is None:
        _fail("NMRPA_TR_E_CAPABILITY", "capability is unknown or already revoked")
    state["revoked"] = True
    os.close(state["root_fd"])


def close_synthetic_test_capability(token: SyntheticTestCapability) -> None:
    revoke_synthetic_test_capability(token)


def _validate_capability(token: Any, project_root: Path) -> dict[str, Any]:
    if type(token) is not SyntheticTestCapability or token.capability_name != CAPABILITY_NAME:
        _fail("NMRPA_TR_E_CAPABILITY", "explicit synthetic test capability required")
    issued = _ISSUED_CAPABILITIES.get(token)
    if (
        issued is None or issued["revoked"] or issued["nonce"] != token._nonce
        or issued["root"] != str(project_root)
    ):
        _fail("NMRPA_TR_E_CAPABILITY", "capability is forged or bound to another root")
    if project_root == ACTUAL_PROJECT_ROOT or os.path.commonpath((str(project_root), str(ACTUAL_PROJECT_ROOT))) == str(ACTUAL_PROJECT_ROOT):
        _fail("NMRPA_TR_E_ACTUAL_ROOT_FORBIDDEN", "actual repository identity is forbidden")
    if os.path.commonpath((str(project_root), "/tmp")) != "/tmp":
        _fail("NMRPA_TR_E_SYNTHETIC_ONLY", "commit is limited to /tmp")
    try:
        opened = os.fstat(issued["root_fd"])
        current = os.lstat(project_root)
    except OSError as exc:
        raise ContractError("NMRPA_TR_E_CAPABILITY", "root identity is unavailable") from exc
    expected = (issued["st_dev"], issued["st_ino"])
    if (opened.st_dev, opened.st_ino) != expected or (current.st_dev, current.st_ino) != expected:
        _fail("NMRPA_TR_E_CAPABILITY", "same-path root replacement detected")
    if expected in _TAINTED_ROOT_IDENTITIES:
        _fail("NMRPA_TR_E_ROLLBACK_FAILURE", "root has terminal transaction residue")
    return issued


def describe_synthetic_test_capability(
    token: SyntheticTestCapability, project_root: str | os.PathLike[str],
) -> dict[str, object]:
    """Describe a live /tmp capability without exposing its nonce or root fd."""
    if isinstance(project_root, (bytes, bytearray)):
        _fail("NMRPA_TR_E_PROJECT_ROOT", "project root bytes forbidden")
    root = Path(project_root)
    state = _validate_capability(token, root)
    descriptor = expected_descriptor()
    if descriptor.get("descriptor_sha256") != digest(
        _without(descriptor, "descriptor_sha256"), "nmrpa.real_trust.bootstrap.v1",
    ):
        _fail("NMRPA_CRPG_ROOT_INSTANCE_DESCRIPTOR", "frozen descriptor digest differs")
    rows = [row for row in descriptor.get("trust_stores", []) if row.get("store_kind") == "project_root_identity_marker"]
    if len(rows) != 1:
        _fail("NMRPA_CRPG_ROOT_INSTANCE_DESCRIPTOR", "identity marker store is not unique")
    relative = f"{rows[0]['project_relative_path']}/identity.json"
    try:
        marker_path = _confined(root, relative, must_exist=True)
        marker_stat = os.lstat(marker_path)
        if not stat.S_ISREG(marker_stat.st_mode):
            _fail("NMRPA_CRPG_ROOT_INSTANCE_MARKER", "identity marker must be regular")
        actual_marker = ACTUAL_PROJECT_ROOT / relative
        if os.path.lexists(actual_marker):
            actual_stat = os.lstat(actual_marker)
            if (marker_stat.st_dev, marker_stat.st_ino) == (actual_stat.st_dev, actual_stat.st_ino):
                _fail("NMRPA_CRPG_ROOT_INSTANCE_MARKER", "actual identity-marker inode is forbidden")
        fd = os.open(marker_path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            raw = b""
            while len(raw) <= 1_048_576:
                block = os.read(fd, min(65_536, 1_048_577 - len(raw)))
                if not block:
                    break
                raw += block
        finally:
            os.close(fd)
        marker = json.loads(raw)
        _exact(marker, {"schema_version", "bootstrap_id", "project_root_id", "identity_sha256"}, "project identity marker")
        _literal(marker["schema_version"], "nmrpa.project_root_identity.v1", "marker.schema_version")
        _str(marker["bootstrap_id"], "marker.bootstrap_id")
        _str(marker["project_root_id"], "marker.project_root_id")
        _sha(marker["identity_sha256"], "marker.identity_sha256")
        if raw != canonical_json(marker) or marker["identity_sha256"] != digest(
            _without(marker, "identity_sha256"), "nmrpa.project.root.v1",
        ):
            _fail("NMRPA_CRPG_ROOT_INSTANCE_MARKER", "identity marker bytes or digest differ")
    except ContractError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ContractError("NMRPA_CRPG_ROOT_INSTANCE_MARKER", "identity marker is unavailable or invalid") from exc
    nonce = state.get("nonce")
    if type(nonce) is not str or not re.fullmatch(r"[0-9a-f]{64}", nonce):
        _fail("NMRPA_CRPG_ROOT_INSTANCE_NONCE", "issuer nonce encoding differs")
    try:
        nonce_bytes = bytes.fromhex(nonce)
    except ValueError as exc:
        raise ContractError("NMRPA_CRPG_ROOT_INSTANCE_NONCE", "issuer nonce encoding differs") from exc
    if len(nonce_bytes) != 32:
        _fail("NMRPA_CRPG_ROOT_INSTANCE_NONCE", "issuer nonce length differs")
    current = os.lstat(root)
    held = os.fstat(state["root_fd"])
    identity = (state["st_dev"], state["st_ino"])
    if identity != (current.st_dev, current.st_ino) or identity != (held.st_dev, held.st_ino):
        _fail("NMRPA_TR_E_CAPABILITY", "root identity changed")
    result: dict[str, object] = {
        "schema_version": "nmrpa.synthetic_root_instance.v1",
        "canonical_project_root": str(root),
        "st_dev": int(state["st_dev"]),
        "st_ino": int(state["st_ino"]),
        "capability_nonce_sha256": hashlib.sha256(b"nmrpa.capability.nonce.v1\x00" + nonce_bytes).hexdigest(),
        "project_identity_marker_sha256": marker["identity_sha256"],
        "descriptor_sha256": descriptor["descriptor_sha256"],
    }
    result["root_instance_sha256"] = digest(result, "nmrpa.synthetic_root_instance.digest.v1")
    return dict(result)


def _validate_descriptor_pin(descriptor: Any, descriptor_sha256: Any) -> dict[str, Any]:
    if type(descriptor) is not dict or descriptor != expected_descriptor():
        _fail("NMRPA_TR_E_DESCRIPTOR", "descriptor differs from frozen bootstrap mapping")
    _sha(descriptor_sha256, "descriptor_sha256")
    if descriptor["descriptor_sha256"] != descriptor_sha256:
        _fail("NMRPA_TR_E_DESCRIPTOR", "descriptor digest pin mismatch")
    return descriptor


def _validate_previous_head(head: Any, log: Mapping[str, Any]) -> dict[str, Any]:
    if type(head) is not dict:
        _fail("NMRPA_TR_E_SCHEMA", "expected_previous_head must be object")
    sequence = head.get("sequence")
    _integer(sequence, "head.sequence")
    if sequence == 0:
        _exact(head, {"schema_version", "logical_name", "log_id", "sequence", "previous_head_sha256", "record_sha256", "head_sha256"}, "genesis head")
        _literal(head["schema_version"], "nmrpa.log_head.v1", "head.schema_version")
        _str(head["logical_name"], "head.logical_name")
        _str(head["log_id"], "head.log_id")
        if head["logical_name"] != log["logical_name"] or head["log_id"] != log["log_id"]:
            _fail("NMRPA_TR_E_HEAD", "genesis head identity mismatch")
        if head["previous_head_sha256"] is not None:
            _fail("NMRPA_TR_E_HEAD", "genesis previous head must be null")
        _sha(head["record_sha256"], "head.record_sha256")
        _sha(head["head_sha256"], "head.head_sha256")
        body = _without(head, "head_sha256")
        if head["head_sha256"] != digest(body, "nmrpa.log.head.v1"):
            _fail("NMRPA_TR_E_DIGEST", "genesis head digest mismatch")
    else:
        _exact(head, {"schema_version", "log_kind", "log_id", "sequence", "transaction_id", "previous_head_sha256", "commit_sha256", "committed_at", "head_sha256"}, "committed head")
        _literal(head["schema_version"], HEAD_SCHEMA_VERSION, "head.schema_version")
        _str(head["log_kind"], "head.log_kind"); _str(head["log_id"], "head.log_id")
        if head["log_kind"] != log["log_kind"] or head["log_id"] != log["log_id"]:
            _fail("NMRPA_TR_E_HEAD", "committed head identity mismatch")
        if not TX_RE.fullmatch(_str(head["transaction_id"], "head.transaction_id")):
            _fail("NMRPA_TR_E_HEAD", "invalid prior transaction id")
        _sha(head["previous_head_sha256"], "head.previous_head_sha256")
        _sha(head["commit_sha256"], "head.commit_sha256")
        _time(head["committed_at"], "head.committed_at")
        _sha(head["head_sha256"], "head.head_sha256")
        if not _sealed(head, "head_sha256", "nmrpa.committed_head.digest.v1"):
            _fail("NMRPA_TR_E_DIGEST", "committed head digest mismatch")
    return dict(head)


def _validate_binding_rows(rows: Any, descriptor: Mapping[str, Any], available: datetime) -> None:
    if type(rows) is not list or len(rows) != len(ROOT_KINDS):
        _fail("NMRPA_TR_E_ROOT_SET", "exactly five bindings required")
    seen_roots: set[str] = set()
    seen_anchors: set[str] = set()
    for index, (row, root_kind) in enumerate(zip(rows, ROOT_KINDS), 1):
        _exact(row, {"order", "root_ref", "payload_sha256", "payload_size", "media_type", "schema_identity", "external_anchor"}, f"binding[{index}]")
        _integer(row["order"], f"binding[{index}].order", 1)
        if row["order"] != index:
            _fail("NMRPA_TR_E_ROOT_ORDER", "root order differs")
        ref = row["root_ref"]
        _exact(ref, {"root_kind", "root_id", "base_id", "root_project_relative_path", "locator_token"}, f"binding[{index}].root_ref")
        for field in ("root_kind", "root_id", "base_id", "root_project_relative_path", "locator_token"):
            _str(ref[field], f"binding[{index}].root_ref.{field}")
        frozen_root = descriptor["root_reservations"][index - 1]
        expected_ref = {key: frozen_root[key] for key in ("root_kind", "root_id", "base_id", "root_project_relative_path", "locator_token")}
        if ref != expected_ref or ref["root_kind"] != root_kind or ref["root_id"] != ROOT_IDS[root_kind]:
            _fail("NMRPA_TR_E_ROOT_PIN", f"root {index} differs from descriptor")
        if root_kind in seen_roots:
            _fail("NMRPA_TR_E_ROOT_SET", "duplicate root kind")
        seen_roots.add(root_kind)
        _sha(row["payload_sha256"], f"binding[{index}].payload_sha256")
        _integer(row["payload_size"], f"binding[{index}].payload_size", 1)
        media = _str(row["media_type"], f"binding[{index}].media_type")
        if "/" not in media or any(alias in media.casefold().split("/") for alias in FORBIDDEN_ALIAS):
            _fail("NMRPA_TR_E_SCHEMA", "invalid media type")
        schema = row["schema_identity"]
        _exact(schema, {"schema_id", "schema_sha256"}, "schema_identity")
        _identifier(schema["schema_id"], "schema_id")
        _sha(schema["schema_sha256"], "schema_sha256")
        anchor = row["external_anchor"]
        _exact(anchor, {"anchor_id", "anchor_sha256", "anchored_at"}, "external_anchor")
        anchor_id = _identifier(anchor["anchor_id"], "anchor_id")
        if anchor_id in seen_anchors:
            _fail("NMRPA_TR_E_ANCHOR", "anchor IDs must be unique")
        seen_anchors.add(anchor_id)
        _sha(anchor["anchor_sha256"], "anchor_sha256")
        if _time(anchor["anchored_at"], "anchored_at") > available:
            _fail("NMRPA_TR_E_TIME", "anchor is later than availability")


def _validate_intent(intent: Any, descriptor: Any) -> dict[str, Any]:
    _reject_forbidden_values(intent)
    _exact(intent, {
        "artifact_kind", "schema_version", "mode", "transaction_id", "binding_id",
        "target_asof", "available_at", "descriptor_sha256", "log_ref",
        "expected_previous_head", "authorization", "ordered_bindings",
        "issuer", "signature", "prepared_at", "committed_at", "intent_sha256",
    }, "intent")
    if intent["artifact_kind"] != "binding_intent" or intent["schema_version"] != INTENT_SCHEMA_VERSION or intent["mode"] != "synthetic_metadata_only_no_payload_read":
        _fail("NMRPA_TR_E_MODE", "intent mode/schema mismatch")
    tx = _str(intent["transaction_id"], "transaction_id")
    if not TX_RE.fullmatch(tx):
        _fail("NMRPA_TR_E_SCHEMA", "transaction_id must be synthetic")
    binding_id = _identifier(intent["binding_id"], "binding_id")
    if not binding_id.startswith("synthetic_"):
        _fail("NMRPA_TR_E_SYNTHETIC_ONLY", "binding_id must be synthetic")
    target = _date(intent["target_asof"], "target_asof")
    available = _time(intent["available_at"], "available_at")
    if available.date() < target:
        _fail("NMRPA_TR_E_TIME", "available_at precedes target")
    _sha(intent["descriptor_sha256"], "descriptor_sha256")
    if intent["descriptor_sha256"] != descriptor["descriptor_sha256"]:
        _fail("NMRPA_TR_E_DESCRIPTOR", "intent descriptor pin mismatch")

    log_ref = intent["log_ref"]
    _exact(log_ref, {"bootstrap_order", "logical_name", "log_kind", "log_id", "head_locator", "history_locator", "journal_locator", "commit_marker_locator"}, "log_ref")
    _integer(log_ref["bootstrap_order"], "log_ref.bootstrap_order", 1)
    for field in ("logical_name", "log_kind", "log_id", "head_locator", "history_locator", "journal_locator", "commit_marker_locator"):
        _str(log_ref[field], f"log_ref.{field}")
    logical = log_ref["logical_name"]
    if logical not in LOG_BY_NAME:
        _fail("NMRPA_TR_E_LOG", "log is not one of the six fixed logs")
    frozen = next(row for row in descriptor["fixed_logs"] if row["logical_name"] == logical)
    expected_log_ref = {
        "bootstrap_order": frozen["bootstrap_order"], "logical_name": frozen["logical_name"],
        "log_kind": frozen["log_kind"], "log_id": frozen["log_id"],
        "head_locator": frozen["current_head_locator"], "history_locator": frozen["historical_heads_locator"],
        "journal_locator": frozen["journal_locator"], "commit_marker_locator": frozen["commit_marker_locator"],
    }
    if log_ref != expected_log_ref:
        _fail("NMRPA_TR_E_LOG", "log refs differ from descriptor")
    previous = _validate_previous_head(intent["expected_previous_head"], frozen)

    auth = intent["authorization"]
    _exact(auth, {"authorization_id", "authorization_sha256", "allowed_binding_id", "allowed_target_asof", "expected_previous_head_sha256", "max_consumptions", "consumption_count", "terminal"}, "authorization")
    auth_id = _identifier(auth["authorization_id"], "authorization_id")
    if not auth_id.startswith("synthetic_"):
        _fail("NMRPA_TR_E_SYNTHETIC_ONLY", "authorization must be synthetic")
    _sha(auth["authorization_sha256"], "authorization_sha256")
    _identifier(auth["allowed_binding_id"], "authorization.allowed_binding_id")
    _date(auth["allowed_target_asof"], "authorization.allowed_target_asof")
    _sha(auth["expected_previous_head_sha256"], "authorization.expected_previous_head_sha256")
    if auth["allowed_binding_id"] != binding_id or auth["allowed_target_asof"] != intent["target_asof"] or auth["expected_previous_head_sha256"] != previous["head_sha256"]:
        _fail("NMRPA_TR_E_AUTH_SCOPE", "authorization scope mismatch")
    if type(auth["max_consumptions"]) is not int or auth["max_consumptions"] != 1 or type(auth["consumption_count"]) is not int or auth["consumption_count"] != 0 or auth["terminal"] is not False:
        _fail("NMRPA_TR_E_AUTH_REPLAY", "one-shot authorization state invalid")
    auth_body = _without(auth, "authorization_sha256")
    if auth["authorization_sha256"] != digest(auth_body, "nmrpa.immutable_binding.authorization.synthetic.v1"):
        _fail("NMRPA_TR_E_DIGEST", "authorization digest mismatch")

    rows = intent["ordered_bindings"]
    _validate_binding_rows(rows, descriptor, available)

    issuer = intent["issuer"]
    _exact(issuer, {"issuer_identity_id", "issuer_credential_id", "payload_schema_id"}, "issuer")
    for field in issuer:
        value = _identifier(issuer[field], field)
        if not value.startswith("synthetic_"):
            _fail("NMRPA_TR_E_SYNTHETIC_ONLY", f"{field} must be synthetic")
    signature = intent["signature"]
    _exact(signature, {"algorithm", "credential_id", "signed_digest", "signature_base64"}, "signature")
    if signature["algorithm"] != "ed25519" or signature["credential_id"] != issuer["issuer_credential_id"]:
        _fail("NMRPA_TR_E_SIGNATURE", "signature identity mismatch")
    _sha(signature["signed_digest"], "signature.signed_digest")
    try:
        raw_signature = base64.b64decode(_str(signature["signature_base64"], "signature_base64"), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ContractError("NMRPA_TR_E_SIGNATURE", "signature is not canonical base64") from exc
    if len(raw_signature) != 64 or base64.b64encode(raw_signature).decode() != signature["signature_base64"]:
        _fail("NMRPA_TR_E_SIGNATURE", "signature must encode exactly 64 bytes")
    prepared = _time(intent["prepared_at"], "prepared_at")
    committed = _time(intent["committed_at"], "committed_at")
    if not (available <= prepared <= committed):
        _fail("NMRPA_TR_E_TIME", "transaction times are out of order")
    _sha(intent["intent_sha256"], "intent_sha256")
    if not _sealed(intent, "intent_sha256", "nmrpa.immutable_binding.intent.synthetic.v1"):
        _fail("NMRPA_TR_E_DIGEST", "intent digest mismatch")
    return {"log": frozen, "previous": previous}


def plan_binding_transaction(intent: Mapping[str, Any], descriptor: Mapping[str, Any], descriptor_sha256: str) -> dict[str, Any]:
    descriptor = _validate_descriptor_pin(descriptor, descriptor_sha256)
    context = _validate_intent(intent, descriptor)
    previous = context["previous"]
    log = context["log"]
    sequence = previous["sequence"] + 1
    previous_commit = None if sequence == 1 else previous["commit_sha256"]

    binding_record = {
        "schema_version": RECORD_SCHEMA_VERSION,
        "binding_id": intent["binding_id"], "transaction_id": intent["transaction_id"],
        "target_asof": intent["target_asof"], "available_at": intent["available_at"],
        "authorization_id": intent["authorization"]["authorization_id"],
        "authorization_sha256": intent["authorization"]["authorization_sha256"],
        "descriptor_sha256": intent["descriptor_sha256"],
        "ordered_bindings": intent["ordered_bindings"],
    }
    binding_record["binding_record_sha256"] = digest(binding_record, "nmrpa.immutable_binding.record.v1")
    anchor_record = {
        "schema_version": ANCHOR_SCHEMA_VERSION,
        "anchor_record_id": f"synthetic_anchor_record_{intent['binding_id']}",
        "binding_id": intent["binding_id"], "binding_record_sha256": binding_record["binding_record_sha256"],
        "ordered_external_anchor_sha256": [row["external_anchor"]["anchor_sha256"] for row in intent["ordered_bindings"]],
        "committed_at": intent["committed_at"],
    }
    anchor_record["anchor_record_sha256"] = digest(anchor_record, "nmrpa.immutable_binding.anchor.v1")
    body = {
        "schema_version": BODY_SCHEMA_VERSION, "log_kind": log["log_kind"], "log_id": log["log_id"],
        "transaction_id": intent["transaction_id"], "sequence": sequence,
        "previous_commit_sha256": previous_commit, "event_type": "immutable_binding_committed",
        "issued_at": intent["available_at"], "issuer_identity_id": intent["issuer"]["issuer_identity_id"],
        "issuer_credential_id": intent["issuer"]["issuer_credential_id"],
        "payload_schema_id": intent["issuer"]["payload_schema_id"],
        "payload": {"binding_record_sha256": binding_record["binding_record_sha256"], "anchor_record_sha256": anchor_record["anchor_record_sha256"]},
    }
    body_sha = digest(body, "nmrpa.commit_record_body.digest.v1")
    if intent["signature"]["signed_digest"] != body_sha:
        _fail("NMRPA_TR_E_SIGNATURE", "signature digest does not cover record body")
    signed = {"schema_version": SIGNED_SCHEMA_VERSION, "record_body": body, "record_body_sha256": body_sha, "signature": intent["signature"]}
    signed["signed_record_sha256"] = digest(signed, "nmrpa.signed_record.digest.v1")
    journal = {
        "schema_version": JOURNAL_SCHEMA_VERSION, "log_kind": log["log_kind"], "log_id": log["log_id"],
        "transaction_id": intent["transaction_id"], "sequence": sequence, "previous_commit_sha256": previous_commit,
        "expected_previous_head_sha256": previous["head_sha256"], "signed_record_sha256": signed["signed_record_sha256"],
        "journal_state": "prepared", "prepared_at": intent["prepared_at"],
    }
    journal["journal_sha256"] = digest(journal, "nmrpa.transaction_journal.digest.v1")
    marker = {
        "schema_version": MARKER_SCHEMA_VERSION, "log_kind": log["log_kind"], "log_id": log["log_id"],
        "transaction_id": intent["transaction_id"], "sequence": sequence, "previous_commit_sha256": previous_commit,
        "expected_previous_head_sha256": previous["head_sha256"], "record_body_sha256": body_sha,
        "signed_record_sha256": signed["signed_record_sha256"], "journal_sha256": journal["journal_sha256"],
        "committed_at": intent["committed_at"],
    }
    marker["commit_sha256"] = digest(marker, "nmrpa.commit_marker.digest.v1")
    head = {
        "schema_version": HEAD_SCHEMA_VERSION, "log_kind": log["log_kind"], "log_id": log["log_id"],
        "sequence": sequence, "transaction_id": intent["transaction_id"],
        "previous_head_sha256": previous["head_sha256"], "commit_sha256": marker["commit_sha256"],
        "committed_at": intent["committed_at"],
    }
    head["head_sha256"] = digest(head, "nmrpa.committed_head.digest.v1")
    tx = intent["transaction_id"]
    paths = {
        "binding": f"{TRUST_BASE_PATH}/stores/binding_store/{tx}.binding.json",
        "anchor": f"{TRUST_BASE_PATH}/stores/anchor_ledger/{tx}.anchor.json",
        "signed_record": f"{log['journal_locator']}/{tx}.record.json",
        "journal": f"{log['journal_locator']}/{tx}.journal.json",
        "marker": f"{log['commit_marker_locator']}/{tx}.commit.json",
        "history": log["historical_heads_locator"], "head": log["current_head_locator"],
    }
    staging = {key: f"{value}.nmrpa-tr-e-stage" for key, value in paths.items()}
    plan = {
        "artifact_kind": "binding_transaction_plan", "schema_version": PLAN_SCHEMA_VERSION,
        "mode": "synthetic_metadata_only_no_payload_read", "transaction_id": tx,
        "descriptor_sha256": descriptor_sha256, "expected_previous_head": previous,
        "authorization_sha256": intent["authorization"]["authorization_sha256"],
        "binding_record": binding_record, "anchor_record": anchor_record, "signed_record": signed,
        "journal": journal, "commit_marker": marker, "new_head": head,
        "paths": paths, "staging_paths": staging,
        "commit_order": ["binding", "anchor", "signed_record", "journal", "marker", "history", "head"],
    }
    plan["plan_sha256"] = digest(plan, "nmrpa.immutable_binding.transaction_plan.synthetic.v1")
    validate_binding_transaction_plan(plan, descriptor, descriptor_sha256)
    return plan


def validate_binding_transaction_plan(plan: Any, descriptor: Mapping[str, Any], descriptor_sha256: str) -> dict[str, Any]:
    descriptor = _validate_descriptor_pin(descriptor, descriptor_sha256)
    _reject_forbidden_values(plan)
    _exact(plan, {"artifact_kind", "schema_version", "mode", "transaction_id", "descriptor_sha256", "expected_previous_head", "authorization_sha256", "binding_record", "anchor_record", "signed_record", "journal", "commit_marker", "new_head", "paths", "staging_paths", "commit_order", "plan_sha256"}, "plan")
    if plan["artifact_kind"] != "binding_transaction_plan" or plan["schema_version"] != PLAN_SCHEMA_VERSION or plan["mode"] != "synthetic_metadata_only_no_payload_read":
        _fail("NMRPA_TR_E_MODE", "plan mode/schema mismatch")
    tx = _str(plan["transaction_id"], "transaction_id")
    if not TX_RE.fullmatch(tx) or plan["descriptor_sha256"] != descriptor_sha256:
        _fail("NMRPA_TR_E_PIN", "plan identity pin mismatch")
    _sha(plan["authorization_sha256"], "authorization_sha256")
    signed_probe = plan["signed_record"]
    _exact(signed_probe, {"schema_version", "record_body", "record_body_sha256", "signature", "signed_record_sha256"}, "signed_record")
    body_probe = signed_probe["record_body"]
    _exact(body_probe, {"schema_version", "log_kind", "log_id", "transaction_id", "sequence", "previous_commit_sha256", "event_type", "issued_at", "issuer_identity_id", "issuer_credential_id", "payload_schema_id", "payload"}, "record_body")
    logical = _str(body_probe["log_id"], "body.log_id")
    log = next((row for row in descriptor["fixed_logs"] if row["log_id"] == logical), None)
    if log is None:
        _fail("NMRPA_TR_E_LOG", "plan log is not descriptor-pinned")
    previous = _validate_previous_head(plan["expected_previous_head"], log)
    sequence = previous["sequence"] + 1
    previous_commit = None if sequence == 1 else previous["commit_sha256"]

    binding = plan["binding_record"]
    _exact(binding, {"schema_version", "binding_id", "transaction_id", "target_asof", "available_at", "authorization_id", "authorization_sha256", "descriptor_sha256", "ordered_bindings", "binding_record_sha256"}, "binding_record")
    _literal(binding["schema_version"], RECORD_SCHEMA_VERSION, "binding.schema_version")
    _str(binding["transaction_id"], "binding.transaction_id")
    _identifier(binding["binding_id"], "binding.binding_id")
    _identifier(binding["authorization_id"], "binding.authorization_id")
    _sha(binding["authorization_sha256"], "binding.authorization_sha256")
    _sha(binding["descriptor_sha256"], "binding.descriptor_sha256")
    _sha(binding["binding_record_sha256"], "binding.binding_record_sha256")
    if binding["transaction_id"] != tx or binding["authorization_sha256"] != plan["authorization_sha256"] or binding["descriptor_sha256"] != descriptor_sha256:
        _fail("NMRPA_TR_E_CROSS_BINDING", "binding identity differs")
    _date(binding["target_asof"], "binding.target_asof"); _time(binding["available_at"], "binding.available_at")
    _validate_binding_rows(binding["ordered_bindings"], descriptor, _time(binding["available_at"], "binding.available_at"))
    if not _sealed(binding, "binding_record_sha256", "nmrpa.immutable_binding.record.v1"):
        _fail("NMRPA_TR_E_DIGEST", "binding digest mismatch")
    anchor = plan["anchor_record"]
    _exact(anchor, {"schema_version", "anchor_record_id", "binding_id", "binding_record_sha256", "ordered_external_anchor_sha256", "committed_at", "anchor_record_sha256"}, "anchor_record")
    _literal(anchor["schema_version"], ANCHOR_SCHEMA_VERSION, "anchor.schema_version")
    _identifier(anchor["anchor_record_id"], "anchor.anchor_record_id")
    _identifier(anchor["binding_id"], "anchor.binding_id")
    _sha(anchor["binding_record_sha256"], "anchor.binding_record_sha256")
    _time(anchor["committed_at"], "anchor.committed_at")
    _sha(anchor["anchor_record_sha256"], "anchor.anchor_record_sha256")
    if type(anchor["ordered_external_anchor_sha256"]) is not list or len(anchor["ordered_external_anchor_sha256"]) != 5:
        _fail("NMRPA_TR_E_SCHEMA", "anchor ordered digest tuple must contain five items")
    for index, value in enumerate(anchor["ordered_external_anchor_sha256"]):
        _sha(value, f"anchor.ordered_external_anchor_sha256[{index}]")
    if anchor["binding_id"] != binding["binding_id"] or anchor["binding_record_sha256"] != binding["binding_record_sha256"]:
        _fail("NMRPA_TR_E_CROSS_BINDING", "anchor differs from binding")
    expected_anchors = [row["external_anchor"]["anchor_sha256"] for row in binding["ordered_bindings"]]
    if anchor["ordered_external_anchor_sha256"] != expected_anchors or not _sealed(anchor, "anchor_record_sha256", "nmrpa.immutable_binding.anchor.v1"):
        _fail("NMRPA_TR_E_ANCHOR", "anchor digest/order mismatch")

    signed = plan["signed_record"]
    _exact(signed, {"schema_version", "record_body", "record_body_sha256", "signature", "signed_record_sha256"}, "signed_record")
    body = signed["record_body"]
    _exact(body, {"schema_version", "log_kind", "log_id", "transaction_id", "sequence", "previous_commit_sha256", "event_type", "issued_at", "issuer_identity_id", "issuer_credential_id", "payload_schema_id", "payload"}, "record_body")
    _literal(signed["schema_version"], SIGNED_SCHEMA_VERSION, "signed.schema_version")
    _sha(signed["record_body_sha256"], "signed.record_body_sha256")
    _sha(signed["signed_record_sha256"], "signed.signed_record_sha256")
    _literal(body["schema_version"], BODY_SCHEMA_VERSION, "body.schema_version")
    for field in ("log_kind", "log_id", "transaction_id", "issuer_identity_id", "issuer_credential_id", "payload_schema_id"):
        _str(body[field], f"body.{field}")
    _integer(body["sequence"], "body.sequence", 1)
    _optional_sha(body["previous_commit_sha256"], "body.previous_commit_sha256")
    _literal(body["event_type"], "immutable_binding_committed", "body.event_type")
    _time(body["issued_at"], "body.issued_at")
    if body["log_kind"] != log["log_kind"] or body["log_id"] != log["log_id"] or body["transaction_id"] != tx or body["sequence"] != sequence or body["previous_commit_sha256"] != previous_commit:
        _fail("NMRPA_TR_E_CHAIN", "record body chain differs")
    _exact(body["payload"], {"binding_record_sha256", "anchor_record_sha256"}, "record payload")
    _sha(body["payload"]["binding_record_sha256"], "body.payload.binding_record_sha256")
    _sha(body["payload"]["anchor_record_sha256"], "body.payload.anchor_record_sha256")
    if body["payload"] != {"binding_record_sha256": binding["binding_record_sha256"], "anchor_record_sha256": anchor["anchor_record_sha256"]}:
        _fail("NMRPA_TR_E_CROSS_BINDING", "record payload differs")
    if signed["record_body_sha256"] != digest(body, "nmrpa.commit_record_body.digest.v1"):
        _fail("NMRPA_TR_E_DIGEST", "body digest mismatch")
    signature = signed["signature"]
    _exact(signature, {"algorithm", "credential_id", "signed_digest", "signature_base64"}, "signature")
    _literal(signature["algorithm"], "ed25519", "signature.algorithm")
    _str(signature["credential_id"], "signature.credential_id")
    _sha(signature["signed_digest"], "signature.signed_digest")
    _str(signature["signature_base64"], "signature.signature_base64")
    if signature["credential_id"] != body["issuer_credential_id"] or signature["signed_digest"] != signed["record_body_sha256"]:
        _fail("NMRPA_TR_E_SIGNATURE", "signature cross-reference mismatch")
    try:
        decoded = base64.b64decode(signature["signature_base64"], validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ContractError("NMRPA_TR_E_SIGNATURE", "invalid signature base64") from exc
    if len(decoded) != 64 or base64.b64encode(decoded).decode() != signature["signature_base64"] or not _sealed(signed, "signed_record_sha256", "nmrpa.signed_record.digest.v1"):
        _fail("NMRPA_TR_E_SIGNATURE", "signed record invalid")

    journal = plan["journal"]
    _exact(journal, {"schema_version", "log_kind", "log_id", "transaction_id", "sequence", "previous_commit_sha256", "expected_previous_head_sha256", "signed_record_sha256", "journal_state", "prepared_at", "journal_sha256"}, "journal")
    _literal(journal["schema_version"], JOURNAL_SCHEMA_VERSION, "journal.schema_version")
    for field in ("log_kind", "log_id", "transaction_id"):
        _str(journal[field], f"journal.{field}")
    _integer(journal["sequence"], "journal.sequence", 1)
    _optional_sha(journal["previous_commit_sha256"], "journal.previous_commit_sha256")
    for field in ("expected_previous_head_sha256", "signed_record_sha256", "journal_sha256"):
        _sha(journal[field], f"journal.{field}")
    _literal(journal["journal_state"], "prepared", "journal.journal_state")
    _time(journal["prepared_at"], "journal.prepared_at")
    shared = (log["log_kind"], log["log_id"], tx, sequence, previous_commit)
    if (journal["log_kind"], journal["log_id"], journal["transaction_id"], journal["sequence"], journal["previous_commit_sha256"]) != shared or journal["schema_version"] != JOURNAL_SCHEMA_VERSION or journal["expected_previous_head_sha256"] != previous["head_sha256"] or journal["signed_record_sha256"] != signed["signed_record_sha256"] or journal["journal_state"] != "prepared" or not _sealed(journal, "journal_sha256", "nmrpa.transaction_journal.digest.v1"):
        _fail("NMRPA_TR_E_JOURNAL", "journal invalid")
    marker = plan["commit_marker"]
    _exact(marker, {"schema_version", "log_kind", "log_id", "transaction_id", "sequence", "previous_commit_sha256", "expected_previous_head_sha256", "record_body_sha256", "signed_record_sha256", "journal_sha256", "committed_at", "commit_sha256"}, "commit_marker")
    _literal(marker["schema_version"], MARKER_SCHEMA_VERSION, "marker.schema_version")
    for field in ("log_kind", "log_id", "transaction_id"):
        _str(marker[field], f"marker.{field}")
    _integer(marker["sequence"], "marker.sequence", 1)
    _optional_sha(marker["previous_commit_sha256"], "marker.previous_commit_sha256")
    for field in ("expected_previous_head_sha256", "record_body_sha256", "signed_record_sha256", "journal_sha256", "commit_sha256"):
        _sha(marker[field], f"marker.{field}")
    _time(marker["committed_at"], "marker.committed_at")
    if (marker["log_kind"], marker["log_id"], marker["transaction_id"], marker["sequence"], marker["previous_commit_sha256"]) != shared or marker["expected_previous_head_sha256"] != previous["head_sha256"] or marker["record_body_sha256"] != signed["record_body_sha256"] or marker["signed_record_sha256"] != signed["signed_record_sha256"] or marker["journal_sha256"] != journal["journal_sha256"] or not _sealed(marker, "commit_sha256", "nmrpa.commit_marker.digest.v1"):
        _fail("NMRPA_TR_E_MARKER", "commit marker invalid")
    head = plan["new_head"]
    _exact(head, {"schema_version", "log_kind", "log_id", "sequence", "transaction_id", "previous_head_sha256", "commit_sha256", "committed_at", "head_sha256"}, "new_head")
    _validate_previous_head(head, log)
    if (head["log_kind"], head["log_id"], head["transaction_id"], head["sequence"]) != shared[:4] or head["previous_head_sha256"] != previous["head_sha256"] or head["commit_sha256"] != marker["commit_sha256"] or head["committed_at"] != marker["committed_at"]:
        _fail("NMRPA_TR_E_HEAD", "new head invalid")

    paths = plan["paths"]
    _exact(paths, {"binding", "anchor", "signed_record", "journal", "marker", "history", "head"}, "paths")
    expected_paths = {
        "binding": f"{TRUST_BASE_PATH}/stores/binding_store/{tx}.binding.json",
        "anchor": f"{TRUST_BASE_PATH}/stores/anchor_ledger/{tx}.anchor.json",
        "signed_record": f"{log['journal_locator']}/{tx}.record.json",
        "journal": f"{log['journal_locator']}/{tx}.journal.json",
        "marker": f"{log['commit_marker_locator']}/{tx}.commit.json",
        "history": log["historical_heads_locator"], "head": log["current_head_locator"],
    }
    if paths != expected_paths:
        _fail("NMRPA_TR_E_PATH", "transaction paths differ from fixed mapping")
    staging = plan["staging_paths"]
    _exact(staging, set(paths), "staging_paths")
    if staging != {key: f"{value}.nmrpa-tr-e-stage" for key, value in paths.items()}:
        _fail("NMRPA_TR_E_PATH", "staging paths differ from fixed names")
    for key, value in {**paths, **{f"stage_{k}": v for k, v in staging.items()}}.items():
        _relative(value, key)
    if type(plan["commit_order"]) is not list or any(type(item) is not str for item in plan["commit_order"]) or plan["commit_order"] != ["binding", "anchor", "signed_record", "journal", "marker", "history", "head"]:
        _fail("NMRPA_TR_E_ORDER", "commit order differs")
    _sha(plan["plan_sha256"], "plan_sha256")
    if not _sealed(plan, "plan_sha256", "nmrpa.immutable_binding.transaction_plan.synthetic.v1"):
        _fail("NMRPA_TR_E_DIGEST", "plan digest mismatch")
    return {"ok": True, "root_count": 5, "sequence": sequence, "payload_bytes_read": 0, "write_permitted": False}


def _confined(project_root: Path, relative: str, *, must_exist: bool | None = None) -> Path:
    _relative(relative, "transaction path")
    current = project_root
    parts = PurePosixPath(relative).parts
    for index, part in enumerate(parts):
        current = current / part
        exists = os.path.lexists(current)
        if exists:
            mode = os.lstat(current).st_mode
            if stat.S_ISLNK(mode):
                _fail("NMRPA_TR_E_SYMLINK", relative)
            if index < len(parts) - 1 and not stat.S_ISDIR(mode):
                _fail("NMRPA_TR_E_PATH", f"non-directory ancestor for {relative}")
        elif index < len(parts) - 1:
            _fail("NMRPA_TR_E_PATH", f"missing pinned parent for {relative}")
    if must_exist is True and not os.path.lexists(current):
        _fail("NMRPA_TR_E_MISSING", relative)
    if must_exist is False and os.path.lexists(current):
        _fail("NMRPA_TR_E_REPLAY_CONFLICT", relative)
    parent_real = current.parent.resolve()
    if os.path.commonpath((str(project_root), str(parent_real))) != str(project_root):
        _fail("NMRPA_TR_E_PATH_ESCAPE", relative)
    return current


def _read_control_json(project_root: Path, relative: str) -> Any:
    path = _confined(project_root, relative, must_exist=True)
    if not stat.S_ISREG(os.lstat(path).st_mode):
        _fail("NMRPA_TR_E_FILE_TYPE", relative)
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        raw = os.read(fd, 1_048_577)
    finally:
        os.close(fd)
    if len(raw) > 1_048_576:
        _fail("NMRPA_TR_E_FILE_SIZE", relative)
    try:
        return json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("NMRPA_TR_E_CONTROL_JSON", relative) from exc


def _atomic_json(
    project_root: Path, final_rel: str, staging_rel: str, value: Any, *, replace: bool,
    state: dict[str, Any] | None = None, state_key: str | None = None,
) -> None:
    final = _confined(project_root, final_rel, must_exist=None if replace else False)
    staging = _confined(project_root, staging_rel, must_exist=False)
    if final.parent != staging.parent:
        _fail("NMRPA_TR_E_PATH", "staging must share final parent")
    raw = canonical_json(value)
    dir_fd = os.open(final.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
    try:
        fd = os.open(staging.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600, dir_fd=dir_fd)
        try:
            os.write(fd, raw)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(staging.name, final.name, src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
        if state is not None and state_key is not None:
            state["replaced"].append(state_key)
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def _atomic_json_no_clobber(
    project_root: Path, final_rel: str, staging_rel: str, value: Any, *,
    state: dict[str, Any], state_key: str,
) -> None:
    final = _confined(project_root, final_rel, must_exist=False)
    staging = _confined(project_root, staging_rel, must_exist=False)
    if final.parent != staging.parent:
        _fail("NMRPA_TR_E_PATH", "staging must share final parent")
    raw = canonical_json(value)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    dir_fd = os.open(final.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
    linked = False
    try:
        fd = os.open(staging.name, flags, 0o600, dir_fd=dir_fd)
        try:
            offset = 0
            while offset < len(raw):
                written = os.write(fd, raw[offset:])
                if written <= 0:
                    _fail("NMRPA_TR_E_IMMUTABLE_INSTALL", "short staging write")
                offset += written
            os.fsync(fd)
        finally:
            os.close(fd)
        try:
            os.link(
                staging.name, final.name, src_dir_fd=dir_fd, dst_dir_fd=dir_fd,
                follow_symlinks=False,
            )
        except FileExistsError as exc:
            raise ContractError("NMRPA_TR_E_IMMUTABLE_FINAL_EXISTS", final_rel) from exc
        except OSError as exc:
            if exc.errno in (getattr(os, "EXDEV", 18), getattr(os, "EPERM", 1), getattr(os, "EOPNOTSUPP", 95)):
                raise ContractError("NMRPA_TR_E_IMMUTABLE_LINK_UNSUPPORTED", final_rel) from exc
            raise ContractError("NMRPA_TR_E_IMMUTABLE_INSTALL", final_rel) from exc
        linked = True
        final_stat = os.stat(final.name, dir_fd=dir_fd, follow_symlinks=False)
        state.setdefault("immutable_installed", {})[state_key] = {
            "st_dev": final_stat.st_dev, "st_ino": final_stat.st_ino, "raw": raw,
        }
        state["replaced"].append(state_key)
        os.fsync(dir_fd)
        os.unlink(staging.name, dir_fd=dir_fd)
        os.fsync(dir_fd)
        fd = os.open(final.name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=dir_fd)
        try:
            check_stat = os.fstat(fd)
            check_raw = b""
            while len(check_raw) < len(raw) + 1:
                block = os.read(fd, len(raw) + 1 - len(check_raw))
                if not block:
                    break
                check_raw += block
        finally:
            os.close(fd)
        if (
            not stat.S_ISREG(check_stat.st_mode) or check_stat.st_nlink != 1
            or (check_stat.st_dev, check_stat.st_ino) != (final_stat.st_dev, final_stat.st_ino)
            or check_raw != raw
        ):
            _fail("NMRPA_TR_E_IMMUTABLE_POSTCONDITION", final_rel)
    except BaseException:
        if not linked and os.path.lexists(staging):
            try:
                os.unlink(staging.name, dir_fd=dir_fd)
                os.fsync(dir_fd)
            except OSError:
                pass
        raise
    finally:
        os.close(dir_fd)


def _remove_installed_immutable(
    project_root: Path, relative: str, installed: Mapping[str, Any],
) -> None:
    path = _confined(project_root, relative, must_exist=True)
    parent_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
    try:
        fd = os.open(path.name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=parent_fd)
        try:
            current = os.fstat(fd)
            raw = b""
            expected = installed["raw"]
            while len(raw) < len(expected) + 1:
                block = os.read(fd, len(expected) + 1 - len(raw))
                if not block:
                    break
                raw += block
        finally:
            os.close(fd)
        if (
            (current.st_dev, current.st_ino) != (installed["st_dev"], installed["st_ino"])
            or raw != expected
        ):
            _fail("NMRPA_TR_E_ROLLBACK_FAILURE", "immutable final identity changed")
        os.unlink(path.name, dir_fd=parent_fd)
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)


def _remove_control_file(project_root: Path, relative: str) -> None:
    path = _confined(project_root, relative, must_exist=True)
    parent_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
    try:
        os.unlink(path.name, dir_fd=parent_fd)
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)


def _validate_history_closure(
    root: Path, log: Mapping[str, Any], current: Any, history: Any,
) -> set[str]:
    if type(history) is not list or not history:
        _fail("NMRPA_TR_E_HEAD_HISTORY", "history must be a non-empty exact array")
    genesis = _read_control_json(root, log["genesis_locator"])
    _exact(genesis, {"schema_version", "logical_name", "log_kind", "log_id", "owner_role", "sequence", "previous_head_sha256", "genesis_sha256"}, "genesis")
    _literal(genesis["schema_version"], "nmrpa.log_genesis.v1", "genesis.schema_version")
    for field in ("logical_name", "log_kind", "log_id", "owner_role"):
        _str(genesis[field], f"genesis.{field}")
    _integer(genesis["sequence"], "genesis.sequence")
    if genesis["sequence"] != 0 or genesis["previous_head_sha256"] is not None:
        _fail("NMRPA_TR_E_CHAIN", "invalid genesis sequence")
    _sha(genesis["genesis_sha256"], "genesis.genesis_sha256")
    if (
        genesis["logical_name"] != log["logical_name"] or genesis["log_kind"] != log["log_kind"]
        or genesis["log_id"] != log["log_id"] or genesis["owner_role"] != log["owner_role"]
        or not _sealed(genesis, "genesis_sha256", "nmrpa.log.genesis.v1")
    ):
        _fail("NMRPA_TR_E_CHAIN", "genesis identity or digest differs")
    first = _validate_previous_head(history[0], log)
    if first["sequence"] != 0 or first["record_sha256"] != genesis["genesis_sha256"]:
        _fail("NMRPA_TR_E_CHAIN", "genesis head does not bind genesis record")

    committed: set[str] = set()
    previous = first
    for index, raw_head in enumerate(history[1:], 1):
        head = _validate_previous_head(raw_head, log)
        if head["sequence"] != index:
            _fail("NMRPA_TR_E_CHAIN", "history sequence gap or fork")
        if head["previous_head_sha256"] != previous["head_sha256"]:
            _fail("NMRPA_TR_E_CHAIN", "history previous-head chain differs")
        tx = head["transaction_id"]
        if tx in committed:
            _fail("NMRPA_TR_E_REPLAY", "duplicate historical transaction")
        paths = {
            "binding": f"{TRUST_BASE_PATH}/stores/binding_store/{tx}.binding.json",
            "anchor": f"{TRUST_BASE_PATH}/stores/anchor_ledger/{tx}.anchor.json",
            "signed_record": f"{log['journal_locator']}/{tx}.record.json",
            "journal": f"{log['journal_locator']}/{tx}.journal.json",
            "marker": f"{log['commit_marker_locator']}/{tx}.commit.json",
            "history": log["historical_heads_locator"], "head": log["current_head_locator"],
        }
        binding = _read_control_json(root, paths["binding"])
        _exact(binding, {"schema_version", "binding_id", "transaction_id", "target_asof", "available_at", "authorization_id", "authorization_sha256", "descriptor_sha256", "ordered_bindings", "binding_record_sha256"}, "historical binding_record")
        anchor = _read_control_json(root, paths["anchor"])
        signed = _read_control_json(root, paths["signed_record"])
        journal = _read_control_json(root, paths["journal"])
        marker = _read_control_json(root, paths["marker"])
        plan = {
            "artifact_kind": "binding_transaction_plan", "schema_version": PLAN_SCHEMA_VERSION,
            "mode": "synthetic_metadata_only_no_payload_read", "transaction_id": tx,
            "descriptor_sha256": binding.get("descriptor_sha256"), "expected_previous_head": previous,
            "authorization_sha256": binding.get("authorization_sha256"), "binding_record": binding,
            "anchor_record": anchor, "signed_record": signed, "journal": journal,
            "commit_marker": marker, "new_head": head, "paths": paths,
            "staging_paths": {key: f"{value}.nmrpa-tr-e-stage" for key, value in paths.items()},
            "commit_order": ["binding", "anchor", "signed_record", "journal", "marker", "history", "head"],
        }
        plan["plan_sha256"] = digest(plan, "nmrpa.immutable_binding.transaction_plan.synthetic.v1")
        validate_binding_transaction_plan(plan, expected_descriptor(), expected_descriptor()["descriptor_sha256"])
        if marker["commit_sha256"] != head["commit_sha256"]:
            _fail("NMRPA_TR_E_CHAIN", "head does not bind commit marker")
        if index > 1 and marker["previous_commit_sha256"] != previous["commit_sha256"]:
            _fail("NMRPA_TR_E_CHAIN", "previous-commit chain differs")
        committed.add(tx)
        previous = head
    if previous != current or history[-1] != current:
        _fail("NMRPA_TR_E_HEAD_HISTORY", "history does not close at current head")
    return committed


def _scan_transaction_sets(root: Path, log: Mapping[str, Any]) -> dict[str, set[str]]:
    locations = {
        "record": (log["journal_locator"], ".record.json"),
        "journal": (log["journal_locator"], ".journal.json"),
        "marker": (log["commit_marker_locator"], ".commit.json"),
    }
    result: dict[str, set[str]] = {}
    for key, (relative, suffix) in locations.items():
        directory = _confined(root, relative, must_exist=True)
        names = {child.name for child in directory.iterdir()}
        if any(name.endswith(".nmrpa-tr-e-stage") for name in names):
            _fail("NMRPA_TR_E_ORPHAN_TRANSACTION", "staging artifact exists")
        allowed_suffixes = (".record.json", ".journal.json") if key in ("record", "journal") else (suffix,)
        if any(not any(name.endswith(item) for item in allowed_suffixes) for name in names):
            _fail("NMRPA_TR_E_ORPHAN_TRANSACTION", "unknown control artifact exists")
        result[key] = {name.removesuffix(suffix) for name in names if name.endswith(suffix)}
    return result


def _validate_substrate_closure(root: Path, log: Mapping[str, Any]) -> tuple[dict[str, Any], list[Any], set[str]]:
    current = _read_control_json(root, log["current_head_locator"])
    history = _read_control_json(root, log["historical_heads_locator"])
    committed = _validate_history_closure(root, log, current, history)
    sets = _scan_transaction_sets(root, log)
    if any(value != committed for value in sets.values()):
        _fail("NMRPA_TR_E_ORPHAN_TRANSACTION", "record/journal/marker closure differs")
    return current, history, committed


def _validate_all_substrate_closure(
    root: Path, descriptor: Mapping[str, Any], target_log: Mapping[str, Any],
) -> tuple[dict[str, Any], list[Any], set[str]]:
    all_transactions: set[str] = set()
    target_result: tuple[dict[str, Any], list[Any], set[str]] | None = None
    for fixed_log in descriptor["fixed_logs"]:
        result = _validate_substrate_closure(root, fixed_log)
        if all_transactions & result[2]:
            _fail("NMRPA_TR_E_ORPHAN_TRANSACTION", "transaction appears in multiple fixed logs")
        all_transactions.update(result[2])
        if fixed_log["log_id"] == target_log["log_id"]:
            target_result = result
    store_sets: dict[str, set[str]] = {}
    for key, relative, suffix in (
        ("binding", f"{TRUST_BASE_PATH}/stores/binding_store", ".binding.json"),
        ("anchor", f"{TRUST_BASE_PATH}/stores/anchor_ledger", ".anchor.json"),
    ):
        directory = _confined(root, relative, must_exist=True)
        names = {child.name for child in directory.iterdir()}
        if any(name.endswith(".nmrpa-tr-e-stage") for name in names):
            _fail("NMRPA_TR_E_ORPHAN_TRANSACTION", "store staging artifact exists")
        if any(not name.endswith(suffix) for name in names):
            _fail("NMRPA_TR_E_ORPHAN_TRANSACTION", "unknown store artifact exists")
        store_sets[key] = {name.removesuffix(suffix) for name in names if name.endswith(suffix)}
    if any(value != all_transactions for value in store_sets.values()):
        _fail("NMRPA_TR_E_ORPHAN_TRANSACTION", "cross-log binding/anchor store closure differs")
    if target_result is None:
        _fail("NMRPA_TR_E_LOG", "target log is absent from descriptor")
    return target_result


def commit_schema_driven_transaction(
    plan: Mapping[str, Any], project_root: str | os.PathLike[str],
    capability: SyntheticTestCapability, *,
    validate_plan: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    load_closure: Callable[[Path], Mapping[str, Any]],
    validate_post_commit: Callable[[Path, Mapping[str, Any]], Mapping[str, Any]],
    lock_relative_path: str, immutable_values: Mapping[str, Any],
    mutable_values: Mapping[str, Any], synthetic_fail_after_step: int | None = None,
    immutable_final_no_clobber: bool = False,
) -> dict[str, Any]:
    """Execute a schema-driven synthetic transaction with the T_R-E state machine.

    Domain adapters own schemas and closure semantics. This primitive owns the
    capability boundary, CAS, fixed staging, fsync/replace, rollback and taint.
    """
    if type(immutable_values) is not dict or type(mutable_values) is not dict:
        _fail("NMRPA_TR_E_SCHEMA", "transaction values must be exact objects")
    if type(immutable_final_no_clobber) is not bool:
        _fail("NMRPA_TR_E_SCHEMA", "immutable_final_no_clobber must be exact bool")
    if isinstance(project_root, (bytes, bytearray)):
        _fail("NMRPA_TR_E_PROJECT_ROOT", "project root bytes forbidden")
    root = Path(project_root)
    if not root.is_absolute() or root.is_symlink() or not root.is_dir() or root.resolve() != root:
        _fail("NMRPA_TR_E_PROJECT_ROOT", "project root must be canonical absolute directory")
    capability_state = _validate_capability(capability, root)
    validated = dict(validate_plan(plan))
    paths = plan.get("paths")
    staging = plan.get("staging_paths")
    order = plan.get("commit_order")
    if type(paths) is not dict or type(staging) is not dict or type(order) is not list:
        _fail("NMRPA_TR_E_SCHEMA", "schema-driven transaction controls malformed")
    keys = set(immutable_values) | set(mutable_values)
    if set(paths) != keys or set(staging) != keys or set(order) != keys or len(order) != len(keys):
        _fail("NMRPA_TR_E_ORDER", "transaction key closure differs")
    if any(type(key) is not str for key in order) or len(set(order)) != len(order):
        _fail("NMRPA_TR_E_ORDER", "commit order must be exact unique strings")
    if synthetic_fail_after_step is not None and (
        type(synthetic_fail_after_step) is not int
        or not 1 <= synthetic_fail_after_step <= len(order)
    ):
        _fail("NMRPA_TR_E_SCHEMA", "synthetic fault step outside commit order")
    _relative(lock_relative_path, "lock_relative_path")
    lock_dir = _confined(root, lock_relative_path, must_exist=True)
    lock_fd = os.open(lock_dir, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        _validate_capability(capability, root)
        before = dict(load_closure(root))
        if set(before) != {"current_head", "history", "transaction_ids", "authorization_ids", "binding_ids"}:
            _fail("NMRPA_TR_E_SCHEMA", "closure callback returned unexpected fields")
        for field in ("transaction_ids", "authorization_ids", "binding_ids"):
            if type(before[field]) is not set or any(type(item) is not str for item in before[field]):
                _fail("NMRPA_TR_E_SCHEMA", f"closure {field} must be exact string set")
        if before["current_head"] != plan.get("expected_previous_head"):
            if type(before["current_head"]) is dict and before["current_head"].get("transaction_id") == plan.get("transaction_id"):
                _fail("NMRPA_TR_E_REPLAY", "transaction already committed")
            _fail("NMRPA_TR_E_CAS", "current head differs from expected head")
        if plan.get("transaction_id") in before["transaction_ids"]:
            _fail("NMRPA_TR_E_REPLAY", "transaction id already exists")
        if plan.get("authorization_id") in before["authorization_ids"]:
            _fail("NMRPA_TR_E_AUTH_REPLAY", "authorization ID was already consumed")
        if plan.get("binding_id") in before["binding_ids"]:
            _fail("NMRPA_TR_E_REPLAY_CONFLICT", "binding ID already exists")
        for key in immutable_values:
            _confined(root, paths[key], must_exist=False)
            _confined(root, staging[key], must_exist=False)
        for key in mutable_values:
            _confined(root, paths[key], must_exist=True)
            _confined(root, staging[key], must_exist=False)

        state: dict[str, Any] = {
            "phase": "prepared", "replaced": [],
            "immutable_installed": {},
            "backups": {key: _read_control_json(root, paths[key]) for key in mutable_values},
            "root_identity": (capability_state["st_dev"], capability_state["st_ino"]),
        }
        try:
            state["phase"] = "replacing"
            for step, key in enumerate(order, 1):
                _validate_capability(capability, root)
                if key in mutable_values and _read_control_json(root, paths["head"]) != plan["expected_previous_head"]:
                    _fail("NMRPA_TR_E_CAS", "head changed during commit")
                if key in immutable_values and immutable_final_no_clobber:
                    _atomic_json_no_clobber(
                        root, paths[key], staging[key], immutable_values[key],
                        state=state, state_key=key,
                    )
                else:
                    _atomic_json(
                        root, paths[key], staging[key],
                        mutable_values[key] if key in mutable_values else immutable_values[key],
                        replace=key in mutable_values, state=state, state_key=key,
                    )
                if synthetic_fail_after_step == step:
                    _fail("NMRPA_TR_E_SYNTHETIC_FAULT", f"fault after step {step}")
            state["phase"] = "validating"
            after = dict(validate_post_commit(root, validated))
            if after.get("ok") is not True:
                _fail("NMRPA_TR_E_POST_COMMIT", "domain post-commit validation failed")
            state["phase"] = "committed"
        except BaseException as original:
            state["phase"] = "rolling_back"
            rollback_errors: list[str] = []
            replaced = set(state["replaced"])
            for key in reversed(order):
                if key not in replaced:
                    continue
                try:
                    if key in mutable_values:
                        _atomic_json(root, paths[key], staging[key], state["backups"][key], replace=True)
                    elif immutable_final_no_clobber:
                        _remove_installed_immutable(root, paths[key], state["immutable_installed"][key])
                    else:
                        _remove_control_file(root, paths[key])
                except BaseException as exc:
                    rollback_errors.append(f"restore {key}: {type(exc).__name__}: {exc}")
            for key, relative in staging.items():
                try:
                    path = _confined(root, relative)
                    if os.path.lexists(path):
                        _remove_control_file(root, relative)
                except BaseException as exc:
                    rollback_errors.append(f"cleanup staging {key}: {type(exc).__name__}: {exc}")
            try:
                restored = dict(load_closure(root))
                if restored != before:
                    rollback_errors.append("closure re-scan differs from pre-transaction state")
            except BaseException as exc:
                rollback_errors.append(f"closure re-scan: {type(exc).__name__}: {exc}")
            if rollback_errors:
                state["phase"] = "terminal_rollback_failure"
                _TAINTED_ROOT_IDENTITIES.add(state["root_identity"])
                raise ContractError("NMRPA_TR_E_ROLLBACK_FAILURE", "; ".join(rollback_errors)) from original
            state["phase"] = "rolled_back"
            raise
    finally:
        os.close(lock_fd)
    return {"ok": True, "committed": True, "synthetic_only": True, "payload_bytes_read": 0, **after}


def commit_binding_transaction(
    plan: Mapping[str, Any], descriptor: Mapping[str, Any], descriptor_sha256: str,
    project_root: str | os.PathLike[str], capability: SyntheticTestCapability,
    *, synthetic_fail_after_step: int | None = None,
) -> dict[str, Any]:
    if synthetic_fail_after_step is not None and (type(synthetic_fail_after_step) is not int or not 1 <= synthetic_fail_after_step <= 7):
        _fail("NMRPA_TR_E_SCHEMA", "synthetic_fail_after_step must be integer 1..7")
    if isinstance(project_root, (bytes, bytearray)):
        _fail("NMRPA_TR_E_PROJECT_ROOT", "project root bytes forbidden")
    root = Path(project_root)
    if not root.is_absolute() or root.is_symlink() or not root.is_dir() or root.resolve() != root:
        _fail("NMRPA_TR_E_PROJECT_ROOT", "project root must be canonical absolute directory")
    capability_state = _validate_capability(capability, root)
    validated = validate_binding_transaction_plan(plan, descriptor, descriptor_sha256)
    paths = plan["paths"]
    staging = plan["staging_paths"]
    tx = plan["transaction_id"]
    log = next(row for row in descriptor["fixed_logs"] if row["log_id"] == plan["signed_record"]["record_body"]["log_id"])
    storage_dir = _confined(root, log["storage_project_relative_path"], must_exist=True)
    lock_fd = os.open(storage_dir, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        _validate_capability(capability, root)
        current, history, committed_transactions = _validate_all_substrate_closure(root, descriptor, log)
        if current != plan["expected_previous_head"]:
            if type(current) is dict and current.get("transaction_id") == tx:
                _fail("NMRPA_TR_E_REPLAY", "transaction already committed")
            _fail("NMRPA_TR_E_CAS", "current head differs from expected head")
        if tx in committed_transactions:
            _fail("NMRPA_TR_E_REPLAY", "transaction id already exists")
        for prior_tx in sorted(committed_transactions):
            prior = _read_control_json(root, f"{TRUST_BASE_PATH}/stores/binding_store/{prior_tx}.binding.json")
            if prior.get("authorization_id") == plan["binding_record"]["authorization_id"]:
                _fail("NMRPA_TR_E_AUTH_REPLAY", "authorization ID was already consumed")
            if prior.get("binding_id") == plan["binding_record"]["binding_id"]:
                _fail("NMRPA_TR_E_REPLAY_CONFLICT", "binding ID already exists")
        for key in ("binding", "anchor", "signed_record", "journal", "marker"):
            _confined(root, paths[key], must_exist=False)
            _confined(root, staging[key], must_exist=False)
        for key in ("history", "head"):
            _confined(root, staging[key], must_exist=False)

        values = {
            "binding": plan["binding_record"], "anchor": plan["anchor_record"],
            "signed_record": plan["signed_record"], "journal": plan["journal"],
            "marker": plan["commit_marker"], "history": [*history, plan["new_head"]],
            "head": plan["new_head"],
        }
        transaction_state: dict[str, Any] = {
            "phase": "prepared", "replaced": [], "backups": {"history": history, "head": current},
            "root_identity": (capability_state["st_dev"], capability_state["st_ino"]),
        }
        try:
            transaction_state["phase"] = "replacing"
            for step, key in enumerate(plan["commit_order"], 1):
                _validate_capability(capability, root)
                if key in ("history", "head"):
                    reread = _read_control_json(root, paths["head"])
                    if reread != plan["expected_previous_head"]:
                        _fail("NMRPA_TR_E_CAS", "head changed during commit")
                    _atomic_json(
                        root, paths[key], staging[key], values[key], replace=True,
                        state=transaction_state, state_key=key,
                    )
                else:
                    _atomic_json(
                        root, paths[key], staging[key], values[key], replace=False,
                        state=transaction_state, state_key=key,
                    )
                if synthetic_fail_after_step == step:
                    _fail("NMRPA_TR_E_SYNTHETIC_FAULT", f"fault after step {step}")
            transaction_state["phase"] = "validating"
            after, after_history, after_transactions = _validate_all_substrate_closure(root, descriptor, log)
            if (
                after != plan["new_head"] or len(after_history) != len(history) + 1
                or tx not in after_transactions
            ):
                _fail("NMRPA_TR_E_POST_COMMIT", "post-commit closure mismatch")
            transaction_state["phase"] = "committed"
        except BaseException as original:
            transaction_state["phase"] = "rolling_back"
            rollback_errors: list[str] = []
            replaced = set(transaction_state["replaced"])
            for key in ("head", "history"):
                if key in replaced:
                    try:
                        _atomic_json(root, paths[key], staging[key], transaction_state["backups"][key], replace=True)
                    except BaseException as exc:
                        rollback_errors.append(f"restore {key}: {type(exc).__name__}: {exc}")
            for key in reversed(("binding", "anchor", "signed_record", "journal", "marker")):
                if key in replaced:
                    try:
                        _remove_control_file(root, paths[key])
                    except BaseException as exc:
                        rollback_errors.append(f"cleanup {key}: {type(exc).__name__}: {exc}")
            for key, relative in staging.items():
                try:
                    path = _confined(root, relative)
                    if os.path.lexists(path):
                        _remove_control_file(root, relative)
                except BaseException as exc:
                    rollback_errors.append(f"cleanup staging {key}: {type(exc).__name__}: {exc}")
            try:
                closure_head, closure_history, closure_transactions = _validate_all_substrate_closure(root, descriptor, log)
                if closure_head != current or closure_history != history or closure_transactions != committed_transactions:
                    rollback_errors.append("closure re-scan differs from pre-transaction state")
            except BaseException as exc:
                rollback_errors.append(f"closure re-scan: {type(exc).__name__}: {exc}")
            if rollback_errors:
                transaction_state["phase"] = "terminal_rollback_failure"
                _TAINTED_ROOT_IDENTITIES.add(transaction_state["root_identity"])
                detail = "; ".join(rollback_errors)
                raise ContractError("NMRPA_TR_E_ROLLBACK_FAILURE", detail) from original
            transaction_state["phase"] = "rolled_back"
            raise
    finally:
        os.close(lock_fd)
    return {"ok": True, "committed": True, "synthetic_only": True, "sequence": validated["sequence"], "head_sha256": after["head_sha256"], "payload_bytes_read": 0}


__all__ = [
    "ACTUAL_PROJECT_ROOT", "CAPABILITY_NAME", "ContractError", "INTENT_SCHEMA_VERSION",
    "PLAN_SCHEMA_VERSION", "SyntheticTestCapability", "commit_binding_transaction",
    "commit_schema_driven_transaction",
    "describe_synthetic_test_capability",
    "close_synthetic_test_capability", "issue_synthetic_test_capability",
    "plan_binding_transaction", "revoke_synthetic_test_capability",
    "validate_binding_transaction_plan",
]
