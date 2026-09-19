#!/usr/bin/env python3
"""Synthetic-only institutional/margin optional-source binding adapter.

Inputs are caller-sealed metadata and digests. Payload locations, bytes and
file handles are deliberately outside the public contract.
"""
from __future__ import annotations

import base64
import binascii
import math
import os
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping

import tw_policy_nmrpa3_immutable_binding_writer as tx_writer
from tw_policy_nmrpa3_optional_source_trust import (
    BASE, LOG_ID, PROFILE, digest, validate_descriptor,
)

INTENT_SCHEMA_VERSION = "nmrpa.optional_source_binding_intent.synthetic.v1"
PLAN_SCHEMA_VERSION = "nmrpa.optional_source_binding_plan.synthetic.v1"
MODE = "synthetic_metadata_only_no_payload_read"
SOURCE_KINDS = ("institutional", "margin")
AUTHORITATIVE_RECORD_KINDS = (
    "issuer_registration", "recorder_registration", "profile_registration",
    "authorization", "capture_attempt", "sealed_response", "inventory",
    "trusted_time", "response_anchor", "historical_head",
)
AUTHORITATIVE_STORE_BY_KIND = {
    "capture_attempt": "capture_attempt_store",
    "trusted_time": "capture_attempt_store",
    "sealed_response": "sealed_object_store",
    "inventory": "sealed_object_store",
    "issuer_registration": "response_evidence_store",
    "recorder_registration": "response_evidence_store",
    "profile_registration": "optional_source_profile_registry",
    "authorization": "authorization_ledger",
    "response_anchor": "anchor_ledger",
    "historical_head": "response_evidence_store",
}
RESULTS = {
    "authoritative_complete_all_rows": (150, 0),
    "authoritative_complete_zero_rows": (0, 150),
    "authoritative_complete_partial_rows": None,
}
ATTEMPT_RESULTS = {
    "authoritative_success", "access_failed", "auth_failed", "rate_limited",
    "timeout", "transport_failed", "parse_failed", "scope_incomplete",
}
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
ID_RE = re.compile(r"^[a-z][a-z0-9_.-]{2,127}$")
TX_RE = re.compile(r"^txn_synthetic_[a-z0-9._-]{8,96}$")
SYMBOL_RE = re.compile(r"^TW[0-9A-Z]{4,10}$")
FORBIDDEN_KEY_PARTS = ("payload_path", "payload_bytes", "file_handle", "checkpoint", "cache", "latest")
LOG_BASE = f"{BASE}/fixed_logs/optional_source_binding_log"


class ContractError(tx_writer.ContractError):
    pass


def _fail(code: str, detail: str) -> None:
    raise ContractError(code, detail)


def _walk(value: Any, where: str = "value") -> None:
    kind = type(value)
    if kind is dict:
        for key, child in value.items():
            if type(key) is not str:
                _fail("NMRPA_TR_H_SCHEMA", f"{where} key must be exact str")
            folded = key.casefold()
            if any(part in folded for part in FORBIDDEN_KEY_PARTS):
                _fail("NMRPA_TR_H_PAYLOAD_INPUT", f"forbidden field {where}.{key}")
            _walk(child, f"{where}.{key}")
    elif kind is list:
        for index, child in enumerate(value):
            _walk(child, f"{where}[{index}]")
    elif kind is float:
        if not math.isfinite(value):
            _fail("NMRPA_TR_H_SCHEMA", f"non-finite number at {where}")
    elif kind not in {str, int, bool, type(None)}:
        _fail("NMRPA_TR_H_PAYLOAD_INPUT", f"non-JSON or subclass value at {where}")


def _exact(value: Any, fields: set[str], where: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        _fail("NMRPA_TR_H_SCHEMA", f"{where} exact fields differ")
    return value


def _str(value: Any, where: str) -> str:
    if type(value) is not str or not value or unicodedata.normalize("NFC", value) != value:
        _fail("NMRPA_TR_H_SCHEMA", f"{where} must be exact non-empty NFC str")
    return value


def _literal(value: Any, expected: str, where: str) -> None:
    if type(value) is not str or value != expected:
        _fail("NMRPA_TR_H_SCHEMA", f"{where} literal differs")


def _sha(value: Any, where: str) -> str:
    if type(value) is not str or not SHA_RE.fullmatch(value):
        _fail("NMRPA_TR_H_SCHEMA", f"{where} must be lower-case sha256")
    return value


def _identifier(value: Any, where: str, prefix: str | None = None) -> str:
    value = _str(value, where)
    if not ID_RE.fullmatch(value) or prefix is not None and not value.startswith(prefix):
        _fail("NMRPA_TR_H_SCHEMA", f"invalid {where}")
    return value


def _integer(value: Any, where: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        _fail("NMRPA_TR_H_SCHEMA", f"{where} must be exact int >= {minimum}")
    return value


def _canonical_uint(value: Any, where: str, minimum: int = 0) -> int:
    """Decode an exact JSON integer represented canonically as decimal text.

    Draft 2020-12 intentionally treats JSON 1 and 1.0 as the same integer.
    Decimal text keeps the public Python and schema acceptance sets identical.
    """
    if type(value) is not str or not re.fullmatch(r"0|[1-9][0-9]*", value):
        _fail("NMRPA_TR_H_SCHEMA", f"{where} must be canonical unsigned decimal text")
    parsed = int(value)
    if parsed < minimum:
        _fail("NMRPA_TR_H_SCHEMA", f"{where} must be >= {minimum}")
    return parsed


def _number(value: Any, where: str) -> float | int:
    if type(value) not in {int, float} or type(value) is float and not math.isfinite(value):
        _fail("NMRPA_TR_H_SCHEMA", f"{where} must be finite exact number")
    return value


def _date(value: Any, where: str) -> date:
    value = _str(value, where)
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ContractError("NMRPA_TR_H_SCHEMA", f"invalid {where}") from exc
    if parsed.isoformat() != value:
        _fail("NMRPA_TR_H_SCHEMA", f"non-canonical {where}")
    return parsed


def _time(value: Any, where: str) -> datetime:
    value = _str(value, where)
    if not value.endswith("Z"):
        _fail("NMRPA_TR_H_SCHEMA", f"{where} must be UTC Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ContractError("NMRPA_TR_H_SCHEMA", f"invalid {where}") from exc
    if parsed.microsecond:
        _fail("NMRPA_TR_H_SCHEMA", f"{where} must use whole seconds")
    return parsed


def _sealed(value: Mapping[str, Any], field: str, domain: str) -> None:
    _sha(value[field], field)
    if value[field] != digest({k: v for k, v in value.items() if k != field}, domain):
        _fail("NMRPA_TR_H_DIGEST", f"{field} mismatch")


def _ref(value: Any, where: str, id_field: str = "id") -> dict[str, Any]:
    _exact(value, {id_field, "sha256", "head_sha256"}, where)
    _identifier(value[id_field], f"{where}.{id_field}")
    _sha(value["sha256"], f"{where}.sha256"); _sha(value["head_sha256"], f"{where}.head_sha256")
    return value


def _simple_ref(value: Any, where: str, id_field: str = "id") -> dict[str, Any]:
    _exact(value, {id_field, "sha256"}, where)
    _identifier(value[id_field], f"{where}.{id_field}"); _sha(value["sha256"], f"{where}.sha256")
    return value


def _validate_descriptor_pin(value: Any, pin: Any) -> dict[str, Any]:
    validate_descriptor(value)
    _sha(pin, "descriptor_sha256")
    if value["descriptor_sha256"] != pin:
        _fail("NMRPA_TR_H_DESCRIPTOR", "descriptor pin mismatch")
    return value


def _validate_head(head: Any) -> dict[str, Any]:
    if type(head) is not dict:
        _fail("NMRPA_TR_H_SCHEMA", "head must be exact object")
    sequence = _canonical_uint(head.get("sequence"), "head.sequence")
    if sequence == 0:
        _exact(head, {"schema_version", "log_id", "sequence", "previous_head_sha256", "record_sha256", "head_sha256"}, "genesis head")
        _literal(head["schema_version"], "nmrpa.optional_source.binding_log_head.v1", "head.schema_version")
        _literal(head["log_id"], LOG_ID, "head.log_id")
        if head["previous_head_sha256"] is not None:
            _fail("NMRPA_TR_H_CHAIN", "genesis previous head must be null")
        _sha(head["record_sha256"], "head.record_sha256")
        _sealed(head, "head_sha256", "nmrpa.optional_source.binding.head.v1")
    else:
        _exact(head, {"schema_version", "log_id", "sequence", "transaction_id", "previous_head_sha256", "commit_sha256", "committed_at", "head_sha256"}, "committed head")
        _literal(head["schema_version"], "nmrpa.optional_source.binding_log_committed_head.v1", "head.schema_version")
        _literal(head["log_id"], LOG_ID, "head.log_id")
        if not TX_RE.fullmatch(_str(head["transaction_id"], "head.transaction_id")):
            _fail("NMRPA_TR_H_SCHEMA", "invalid head transaction")
        _sha(head["previous_head_sha256"], "head.previous_head_sha256"); _sha(head["commit_sha256"], "head.commit_sha256")
        _time(head["committed_at"], "head.committed_at")
        _sealed(head, "head_sha256", "nmrpa.optional_source.binding.committed_head.v1")
    return head


def _validate_scope(scope: Any, decision_date: str, decision_time: datetime) -> tuple[list[str], list[str]]:
    fields = {"schema_version", "profile_id", "request_scope_id", "decision_date", "decision_time", "calendar_binding_id", "calendar_binding_sha256", "formal_instruments_binding_id", "formal_instruments_binding_sha256", "trading_date_grid_10", "trading_date_grid_10_sha256", "ordered_active_instruments", "active_instrument_set_sha256", "ordered_source_kinds", "requested_source_asof", "cutoff_policy_id", "request_scope_sha256"}
    _exact(scope, fields, "request_scope")
    _literal(scope["schema_version"], "nmrpa.optional_source_request_scope.v1", "scope.schema_version")
    _literal(scope["profile_id"], PROFILE, "scope.profile_id"); _identifier(scope["request_scope_id"], "request_scope_id", "synthetic_")
    if scope["decision_date"] != decision_date or _date(scope["decision_date"], "scope.decision_date").isoformat() != decision_date:
        _fail("NMRPA_TR_H_DATE", "scope decision date mismatch")
    if _time(scope["decision_time"], "scope.decision_time") != decision_time:
        _fail("NMRPA_TR_H_TIME", "scope decision time mismatch")
    for field in ("calendar_binding_id", "formal_instruments_binding_id"):
        _identifier(scope[field], field)
    if scope["calendar_binding_id"] != scope["formal_instruments_binding_id"]:
        _fail("NMRPA_TR_H_PARENT", "calendar/instruments must share five-root binding")
    _sha(scope["calendar_binding_sha256"], "calendar_binding_sha256"); _sha(scope["formal_instruments_binding_sha256"], "formal_instruments_binding_sha256")
    grid = scope["trading_date_grid_10"]
    if type(grid) is not list or len(grid) != 10 or any(type(item) is not str for item in grid):
        _fail("NMRPA_TR_H_GRID", "grid must contain exact 10 dates")
    parsed = [_date(item, "grid date") for item in grid]
    if parsed != sorted(set(parsed)) or grid[-1] != decision_date:
        _fail("NMRPA_TR_H_GRID", "grid order/end differs")
    if scope["trading_date_grid_10_sha256"] != digest(grid, "nmrpa.optional_source.grid_10.v1"):
        _fail("NMRPA_TR_H_DIGEST", "grid digest mismatch")
    active = scope["ordered_active_instruments"]
    if type(active) is not list or len(active) != 150 or any(type(item) is not str or not SYMBOL_RE.fullmatch(item) for item in active):
        _fail("NMRPA_TR_H_UNIVERSE", "active universe must contain 150 canonical symbols")
    if active != sorted(set(active)):
        _fail("NMRPA_TR_H_UNIVERSE", "active universe must be sorted unique")
    if scope["active_instrument_set_sha256"] != digest(active, "nmrpa.optional_source.active_set.v1"):
        _fail("NMRPA_TR_H_DIGEST", "active set digest mismatch")
    if scope["ordered_source_kinds"] != list(SOURCE_KINDS) or any(type(x) is not str for x in scope["ordered_source_kinds"]):
        _fail("NMRPA_TR_H_SOURCE", "source tuple differs")
    if scope["requested_source_asof"] != decision_date:
        _fail("NMRPA_TR_H_STALE", "requested source asof must be same day")
    _literal(scope["cutoff_policy_id"], "nmrpa.optional_source.pit_cutoff.asia_taipei.v1", "scope.cutoff_policy_id")
    _sealed(scope, "request_scope_sha256", "nmrpa.optional_source.request_scope.v1")
    return active, grid


def _validate_response(response: Any, source: str, scope: Mapping[str, Any], active: list[str], cutoff: datetime) -> tuple[list[str], list[str], datetime]:
    fields = {"schema_version", "response_evidence_id", "source_kind", "request_scope_id", "request_scope_sha256", "decision_date", "requested_source_asof", "source_asof", "available_at", "result_class", "sealed_response_object_id", "sealed_response_raw_sha256", "normalized_inventory_sha256", "payload_sha256", "payload_byte_size", "returned_instrument_count", "ordered_returned_instruments", "returned_instrument_set_sha256", "ordered_absent_instruments", "absent_instrument_set_sha256", "capture_attempt_chain_sha256", "trusted_time_evidence_ref", "issuer_registration_ref", "capture_recorder_registration_ref", "authorization_ref", "response_anchor_ref", "response_evidence_sha256"}
    _exact(response, fields, f"{source}.response")
    _literal(response["schema_version"], "nmrpa.optional_source_response_evidence.v1", "response.schema_version")
    _identifier(response["response_evidence_id"], "response_evidence_id", "synthetic_"); _literal(response["source_kind"], source, "response.source_kind")
    if response["request_scope_id"] != scope["request_scope_id"] or response["request_scope_sha256"] != scope["request_scope_sha256"]:
        _fail("NMRPA_TR_H_SCOPE", "response scope ref mismatch")
    for field in ("decision_date", "requested_source_asof", "source_asof"):
        if response[field] != scope["decision_date"]:
            _fail("NMRPA_TR_H_STALE", f"response {field} must be same day")
    available = _time(response["available_at"], "response.available_at")
    if available > cutoff:
        _fail("NMRPA_TR_H_PIT", "response available after decision cutoff")
    result = response["result_class"]
    if type(result) is not str or result not in RESULTS:
        _fail("NMRPA_TR_H_FAILURE", "response is not authoritative complete")
    for field in ("sealed_response_object_id",): _identifier(response[field], field, "synthetic_")
    for field in ("sealed_response_raw_sha256", "normalized_inventory_sha256", "payload_sha256", "capture_attempt_chain_sha256"): _sha(response[field], field)
    _canonical_uint(response["payload_byte_size"], "payload_byte_size")
    count = _canonical_uint(response["returned_instrument_count"], "returned_instrument_count")
    returned, absent = response["ordered_returned_instruments"], response["ordered_absent_instruments"]
    if type(returned) is not list or type(absent) is not list or any(type(x) is not str for x in returned + absent):
        _fail("NMRPA_TR_H_SET", "response sets must be exact string arrays")
    if returned != sorted(set(returned)) or absent != sorted(set(absent)) or set(returned) & set(absent) or sorted(returned + absent) != active or count != len(returned):
        _fail("NMRPA_TR_H_SET", "returned/absent partition differs from active set")
    expected_counts = RESULTS[result]
    if expected_counts is not None and (len(returned), len(absent)) != expected_counts:
        _fail("NMRPA_TR_H_RESULT", "result class cardinality mismatch")
    if result.endswith("partial_rows") and not 0 < len(returned) < 150:
        _fail("NMRPA_TR_H_RESULT", "partial result cardinality invalid")
    if response["returned_instrument_set_sha256"] != digest(returned, "nmrpa.optional_source.returned_set.v1") or response["absent_instrument_set_sha256"] != digest(absent, "nmrpa.optional_source.absent_set.v1"):
        _fail("NMRPA_TR_H_DIGEST", "response set digest mismatch")
    _simple_ref(response["trusted_time_evidence_ref"], "trusted_time_evidence_ref")
    for field in ("issuer_registration_ref", "capture_recorder_registration_ref", "authorization_ref", "response_anchor_ref"):
        _ref(response[field], field)
    _sealed(response, "response_evidence_sha256", "nmrpa.optional_source.response_evidence.v1")
    return returned, absent, available


def _validate_present(evidence: Any, source: str, instrument: str, scope: Mapping[str, Any], response: Mapping[str, Any], grid: list[str], cutoff: datetime, available: datetime) -> None:
    fields = {"schema_version", "evidence_state", "source_kind", "instrument", "decision_date", "request_scope_ref", "response_evidence_ref", "source_asof", "available_at", "ordered_rows", "row_key_set_sha256", "normalized_row_set_sha256", "payload_inventory_sha256", "capture_attempt_chain_sha256", "trusted_time_ref", "issuer_ref", "head_ref", "anchor_ref", "instrument_evidence_sha256"}
    _exact(evidence, fields, f"present[{instrument}]")
    _literal(evidence["schema_version"], "nmrpa.optional_source_instrument_evidence.v1", "evidence.schema_version"); _literal(evidence["evidence_state"], "present", "evidence_state"); _literal(evidence["source_kind"], source, "source_kind"); _literal(evidence["instrument"], instrument, "instrument")
    if evidence["decision_date"] != scope["decision_date"] or evidence["source_asof"] != scope["decision_date"] or _time(evidence["available_at"], "evidence.available_at") != available:
        _fail("NMRPA_TR_H_STALE", "present same-day identity differs")
    if evidence["request_scope_ref"] != {"id": scope["request_scope_id"], "sha256": scope["request_scope_sha256"]} or evidence["response_evidence_ref"] != {"id": response["response_evidence_id"], "sha256": response["response_evidence_sha256"]}:
        _fail("NMRPA_TR_H_SCOPE", "present scope/response ref differs")
    rows = evidence["ordered_rows"]
    if type(rows) is not list or len(rows) != 10:
        _fail("NMRPA_TR_H_GRID", "present requires ten rows")
    expected_fields = {"date", "source_asof", "available_at", "normalized_row_sha256"} | ({"foreign_net_buy", "investment_trust_net_buy", "dealer_net_buy"} if source == "institutional" else {"margin_balance", "margin_balance_change", "short_balance", "short_balance_change"})
    for index, row in enumerate(rows):
        _exact(row, expected_fields, f"row[{index}]")
        if row["date"] != grid[index] or row["source_asof"] != grid[index] or _time(row["available_at"], "row.available_at") > cutoff:
            _fail("NMRPA_TR_H_GRID", "row date/asof/PIT differs")
        for field in expected_fields - {"date", "source_asof", "available_at", "normalized_row_sha256"}: _number(row[field], field)
        _sealed(row, "normalized_row_sha256", f"nmrpa.optional_source.{source}.row.v1")
    if source == "margin":
        for previous, current in zip(rows, rows[1:]):
            if abs(current["margin_balance_change"] - (current["margin_balance"] - previous["margin_balance"])) > 1e-9 or abs(current["short_balance_change"] - (current["short_balance"] - previous["short_balance"])) > 1e-9:
                _fail("NMRPA_TR_H_CONFLICT", "margin official change conflicts with balances")
    if evidence["row_key_set_sha256"] != digest([[instrument, day] for day in grid], "nmrpa.optional_source.row_keys.v1") or evidence["normalized_row_set_sha256"] != digest([row["normalized_row_sha256"] for row in rows], "nmrpa.optional_source.normalized_rows.v1"):
        _fail("NMRPA_TR_H_DIGEST", "present row inventory mismatch")
    if evidence["payload_inventory_sha256"] != response["normalized_inventory_sha256"] or evidence["capture_attempt_chain_sha256"] != response["capture_attempt_chain_sha256"]:
        _fail("NMRPA_TR_H_CROSS_BINDING", "present payload/attempt digest differs")
    for field in ("trusted_time_ref",): _simple_ref(evidence[field], field)
    for field in ("issuer_ref", "head_ref", "anchor_ref"): _ref(evidence[field], field)
    if evidence["trusted_time_ref"] != response["trusted_time_evidence_ref"] or evidence["issuer_ref"] != response["issuer_registration_ref"] or evidence["head_ref"] != response["capture_recorder_registration_ref"] or evidence["anchor_ref"] != response["response_anchor_ref"]:
        _fail("NMRPA_TR_H_CROSS_BINDING", "present trusted/issuer/head/anchor refs differ")
    _sealed(evidence, "instrument_evidence_sha256", "nmrpa.optional_source.instrument_evidence.v1")


def _validate_absent(evidence: Any, source: str, instrument: str, scope: Mapping[str, Any], response: Mapping[str, Any], available: datetime) -> None:
    fields = {"schema_version", "evidence_state", "source_kind", "instrument", "decision_date", "request_scope_ref", "response_evidence_ref", "source_asof", "checked_at", "available_at", "absence_reason", "returned_instrument_set_sha256", "absent_instrument_set_sha256", "sealed_response_raw_sha256", "payload_inventory_sha256", "capture_attempt_chain_sha256", "trusted_time_ref", "issuer_ref", "head_ref", "anchor_ref", "instrument_evidence_sha256"}
    _exact(evidence, fields, f"absent[{instrument}]")
    for field, expected in (("schema_version", "nmrpa.optional_source_instrument_evidence.v1"), ("evidence_state", "confirmed_absent"), ("source_kind", source), ("instrument", instrument), ("absence_reason", "authoritative_complete_scope_no_rows_for_instrument")): _literal(evidence[field], expected, field)
    if evidence["decision_date"] != scope["decision_date"] or evidence["source_asof"] != scope["decision_date"] or _time(evidence["checked_at"], "checked_at") != available or _time(evidence["available_at"], "available_at") != available:
        _fail("NMRPA_TR_H_STALE", "absence same-day/trusted time differs")
    if evidence["request_scope_ref"] != {"id": scope["request_scope_id"], "sha256": scope["request_scope_sha256"]} or evidence["response_evidence_ref"] != {"id": response["response_evidence_id"], "sha256": response["response_evidence_sha256"]}:
        _fail("NMRPA_TR_H_SCOPE", "absence scope/response ref differs")
    shared = {"returned_instrument_set_sha256": response["returned_instrument_set_sha256"], "absent_instrument_set_sha256": response["absent_instrument_set_sha256"], "sealed_response_raw_sha256": response["sealed_response_raw_sha256"], "payload_inventory_sha256": response["normalized_inventory_sha256"], "capture_attempt_chain_sha256": response["capture_attempt_chain_sha256"]}
    if any(evidence[key] != value for key, value in shared.items()):
        _fail("NMRPA_TR_H_ABSENCE", "absence immutable evidence differs")
    for field in ("trusted_time_ref",): _simple_ref(evidence[field], field)
    for field in ("issuer_ref", "head_ref", "anchor_ref"): _ref(evidence[field], field)
    if evidence["trusted_time_ref"] != response["trusted_time_evidence_ref"] or evidence["issuer_ref"] != response["issuer_registration_ref"] or evidence["head_ref"] != response["capture_recorder_registration_ref"] or evidence["anchor_ref"] != response["response_anchor_ref"]:
        _fail("NMRPA_TR_H_CROSS_BINDING", "absence trusted/issuer/head/anchor refs differ")
    _sealed(evidence, "instrument_evidence_sha256", "nmrpa.optional_source.instrument_evidence.v1")


def _validate_component(component: Any, source: str, scope: Mapping[str, Any], active: list[str], grid: list[str], cutoff: datetime) -> None:
    _exact(component, {"source_kind", "authoritative_closure", "response_evidence", "ordered_instrument_evidence", "component_inventory_sha256", "component_sha256"}, f"component.{source}")
    _literal(component["source_kind"], source, "component.source_kind")
    response = component["response_evidence"]
    returned, absent, available = _validate_response(response, source, scope, active, cutoff)
    _validate_authoritative_closure(component["authoritative_closure"], response, scope, source, cutoff)
    evidence = component["ordered_instrument_evidence"]
    if type(evidence) is not list or len(evidence) != 150:
        _fail("NMRPA_TR_H_UNIVERSE", "component requires exactly 150 evidence objects")
    for instrument, item in zip(active, evidence):
        if type(item) is not dict or item.get("instrument") != instrument:
            _fail("NMRPA_TR_H_UNIVERSE", "evidence order differs from active set")
        state = item.get("evidence_state")
        if instrument in returned and state == "present":
            _validate_present(item, source, instrument, scope, response, grid, cutoff, available)
        elif instrument in absent and state == "confirmed_absent":
            _validate_absent(item, source, instrument, scope, response, available)
        else:
            _fail("NMRPA_TR_H_STATE", "instrument state does not match authoritative sets")
    expected_inventory = digest([item["instrument_evidence_sha256"] for item in evidence], "nmrpa.optional_source.component_inventory.v1")
    if component["component_inventory_sha256"] != expected_inventory:
        _fail("NMRPA_TR_H_DIGEST", "component inventory digest mismatch")
    _sealed(component, "component_sha256", "nmrpa.optional_source.component.v1")


def _validate_authoritative_payload(
    kind: str, payload: Any, response: Mapping[str, Any], scope: Mapping[str, Any],
    source: str, cutoff: datetime, records: Mapping[str, Mapping[str, Any]],
) -> None:
    common = {"source_kind", "decision_date", "request_scope_sha256"}
    if type(payload) is not dict or payload.get("source_kind") != source or payload.get("decision_date") != scope["decision_date"] or payload.get("request_scope_sha256") != scope["request_scope_sha256"]:
        _fail("NMRPA_TR_H_REFERENCE_CLOSURE", f"{kind} identity/scope differs")
    if kind == "issuer_registration":
        fields = common | {"registration_id", "principal_registration_id", "identity_binding_id", "credential_activation_id", "trusted_service_registration_id", "identity_id", "status", "committed_at", "valid_from", "valid_until_or_null"}
        _exact(payload, fields, kind)
        for field in ("registration_id", "principal_registration_id", "identity_binding_id", "credential_activation_id", "trusted_service_registration_id", "identity_id"):
            _identifier(payload[field], field, "synthetic_")
        committed = _time(payload["committed_at"], "issuer.committed_at")
        valid_from = _time(payload["valid_from"], "issuer.valid_from")
        valid_until = None if payload["valid_until_or_null"] is None else _time(payload["valid_until_or_null"], "issuer.valid_until")
        if payload["registration_id"] != records[kind]["object_id"] or payload["status"] != "active" or committed > valid_from or valid_until is not None and valid_until < cutoff:
            _fail("NMRPA_TR_H_REGISTRATION", "issuer registration/credential validity differs")
    elif kind == "recorder_registration":
        fields = common | {"registration_id", "recorder_id", "issuer_registration_id", "status", "committed_at", "valid_from", "valid_until_or_null"}
        _exact(payload, fields, kind)
        committed = _time(payload["committed_at"], "recorder.committed_at")
        valid_from = _time(payload["valid_from"], "recorder.valid_from")
        valid_until = None if payload["valid_until_or_null"] is None else _time(payload["valid_until_or_null"], "recorder.valid_until")
        if payload["registration_id"] != records[kind]["object_id"] or payload["issuer_registration_id"] != records["issuer_registration"]["object_id"] or payload["status"] != "active" or committed > valid_from or valid_until is not None and valid_until < cutoff:
            _fail("NMRPA_TR_H_REGISTRATION", "recorder registration closure differs")
    elif kind == "profile_registration":
        fields = common | {"registration_id", "profile_id", "issuer_registration_id", "recorder_registration_id", "status", "committed_at", "valid_from", "valid_until_or_null"}
        _exact(payload, fields, kind)
        committed = _time(payload["committed_at"], "profile.committed_at")
        valid_from = _time(payload["valid_from"], "profile.valid_from")
        valid_until = None if payload["valid_until_or_null"] is None else _time(payload["valid_until_or_null"], "profile.valid_until")
        if payload["registration_id"] != records[kind]["object_id"] or payload["profile_id"] != PROFILE or payload["issuer_registration_id"] != records["issuer_registration"]["object_id"] or payload["recorder_registration_id"] != records["recorder_registration"]["object_id"] or payload["status"] != "active" or committed > valid_from or valid_until is not None and valid_until < cutoff:
            _fail("NMRPA_TR_H_REGISTRATION", "optional profile registration closure differs")
    elif kind == "authorization":
        fields = common | {"authorization_id", "allowed_sealed_response_object_id", "issuer_registration_id", "recorder_registration_id", "profile_registration_id", "issued_at", "committed_at", "committed_under_head_sha256", "max_consumptions", "consumption_count", "terminal"}
        _exact(payload, fields, kind)
        issued = _time(payload["issued_at"], "authorization.issued_at")
        committed = _time(payload["committed_at"], "authorization.committed_at")
        if payload["authorization_id"] != records[kind]["object_id"] or payload["allowed_sealed_response_object_id"] != response["sealed_response_object_id"] or payload["issuer_registration_id"] != records["issuer_registration"]["object_id"] or payload["recorder_registration_id"] != records["recorder_registration"]["object_id"] or payload["profile_registration_id"] != records["profile_registration"]["object_id"] or payload["committed_under_head_sha256"] != records["profile_registration"]["record_sha256"] or issued > committed or _canonical_uint(payload["max_consumptions"], "max_consumptions") != 1 or _canonical_uint(payload["consumption_count"], "consumption_count") != 0 or payload["terminal"] is not False:
            _fail("NMRPA_TR_H_AUTH", "response authorization closure differs")
    elif kind == "capture_attempt":
        fields = common | {"capture_run_id", "ordered_attempts", "capture_attempt_chain_sha256"}
        _exact(payload, fields, kind)
        _identifier(payload["capture_run_id"], "capture_run_id", "synthetic_")
        attempts = payload["ordered_attempts"]
        if type(attempts) is not list or not attempts:
            _fail("NMRPA_TR_H_ATTEMPT", "capture attempt chain must be non-empty")
        first_success = None
        previous_completed = None
        for index, attempt in enumerate(attempts, 1):
            if first_success is not None:
                _fail("NMRPA_TR_H_ATTEMPT", "authoritative success must terminate the attempt chain")
            attempt_fields = {"schema_version", "capture_run_id", "attempt_id", "source_kind", "request_scope_id", "request_scope_sha256", "sequence", "request_identity_sha256", "started_at", "completed_at", "result_class", "http_status_or_null", "sealed_response_object_id_or_null", "sealed_response_raw_sha256_or_null", "issuer_registration_ref", "capture_recorder_head_ref", "attempt_sha256"}
            _exact(attempt, attempt_fields, f"capture_attempt[{index}]")
            _literal(attempt["schema_version"], "nmrpa.optional_source_capture_attempt.v1", "attempt.schema_version")
            if attempt["capture_run_id"] != payload["capture_run_id"] or attempt["source_kind"] != source or attempt["request_scope_id"] != scope["request_scope_id"] or attempt["request_scope_sha256"] != scope["request_scope_sha256"] or _canonical_uint(attempt["sequence"], "attempt.sequence", 1) != index:
                _fail("NMRPA_TR_H_ATTEMPT", "attempt chain identity/sequence differs")
            _identifier(attempt["attempt_id"], "attempt_id", "synthetic_"); _sha(attempt["request_identity_sha256"], "request_identity_sha256")
            started, completed = _time(attempt["started_at"], "attempt.started_at"), _time(attempt["completed_at"], "attempt.completed_at")
            if started > completed or completed > cutoff or previous_completed is not None and started < previous_completed:
                _fail("NMRPA_TR_H_ATTEMPT", "attempt timestamps are not ordered")
            previous_completed = completed
            result = attempt["result_class"]
            if type(result) is not str or result not in ATTEMPT_RESULTS:
                _fail("NMRPA_TR_H_ATTEMPT", "unsupported attempt result")
            status = attempt["http_status_or_null"]
            if status is not None:
                status = _canonical_uint(status, "attempt.http_status", 100)
                if status > 599:
                    _fail("NMRPA_TR_H_ATTEMPT", "http status outside canonical range")
            success = result == "authoritative_success"
            if success:
                if first_success is not None or attempt["sealed_response_object_id_or_null"] != response["sealed_response_object_id"] or attempt["sealed_response_raw_sha256_or_null"] != response["sealed_response_raw_sha256"]:
                    _fail("NMRPA_TR_H_ATTEMPT", "success must be unique and bind the sealed response")
                first_success = attempt
            elif attempt["sealed_response_object_id_or_null"] is not None or attempt["sealed_response_raw_sha256_or_null"] is not None:
                _fail("NMRPA_TR_H_ATTEMPT", "failed attempt cannot bind response evidence")
            if attempt["issuer_registration_ref"] != {"id": records["issuer_registration"]["object_id"], "sha256": records["issuer_registration"]["record_sha256"]} or attempt["capture_recorder_head_ref"] != {"id": records["recorder_registration"]["object_id"], "sha256": records["recorder_registration"]["record_sha256"]}:
                _fail("NMRPA_TR_H_REGISTRATION", "attempt actor refs differ")
            _sealed(attempt, "attempt_sha256", "nmrpa.optional_source.capture_attempt.v1")
        if first_success is None or _time(records["authorization"]["payload"]["committed_at"], "authorization.committed_at") > _time(attempts[0]["started_at"], "first attempt started_at"):
            _fail("NMRPA_TR_H_AUTH", "authorization was not committed before capture")
        expected_chain = digest([attempt["attempt_sha256"] for attempt in attempts], "nmrpa.optional_source.capture_attempt_chain.v1")
        if payload["capture_attempt_chain_sha256"] != expected_chain or response["capture_attempt_chain_sha256"] != expected_chain:
            _fail("NMRPA_TR_H_ATTEMPT", "capture attempt chain digest differs")
    elif kind == "sealed_response":
        _exact(payload, common | {"object_id", "raw_sha256", "payload_sha256", "payload_byte_size", "inventory_id", "attempt_id"}, kind)
        if payload != {**payload, "source_kind": source, "decision_date": scope["decision_date"], "request_scope_sha256": scope["request_scope_sha256"]}:
            _fail("NMRPA_TR_H_REFERENCE_CLOSURE", "sealed response common identity differs")
        attempts = records["capture_attempt"]["payload"]["ordered_attempts"]
        first_success = next((item for item in attempts if item["result_class"] == "authoritative_success"), None)
        if payload["object_id"] != response["sealed_response_object_id"] or payload["raw_sha256"] != response["sealed_response_raw_sha256"] or payload["payload_sha256"] != response["payload_sha256"] or payload["payload_byte_size"] != response["payload_byte_size"] or first_success is None or payload["attempt_id"] != first_success["attempt_id"] or payload["inventory_id"] != records["inventory"]["object_id"]:
            _fail("NMRPA_TR_H_SEALED_RESPONSE", "sealed response object differs")
    elif kind == "inventory":
        _exact(payload, common | {"inventory_id", "normalized_inventory_sha256", "ordered_returned_instruments", "ordered_absent_instruments", "sealed_response_object_id"}, kind)
        if payload["inventory_id"] != records["inventory"]["object_id"] or payload["normalized_inventory_sha256"] != response["normalized_inventory_sha256"] or payload["ordered_returned_instruments"] != response["ordered_returned_instruments"] or payload["ordered_absent_instruments"] != response["ordered_absent_instruments"] or payload["sealed_response_object_id"] != response["sealed_response_object_id"]:
            _fail("NMRPA_TR_H_INVENTORY", "inventory/set closure differs")
    elif kind == "trusted_time":
        _exact(payload, common | {"trusted_time_evidence", "publication_record_or_null"}, kind)
        evidence = payload["trusted_time_evidence"]
        evidence_fields = {"schema_version", "evidence_type", "source_kind", "request_scope_id", "source_asof", "available_at", "publication_record_ref_or_null", "first_success_attempt_ref_or_null", "trusted_time_issuer_ref", "trusted_time_head_ref", "trusted_time_anchor_ref", "trusted_time_evidence_sha256"}
        _exact(evidence, evidence_fields, "trusted_time_evidence")
        _literal(evidence["schema_version"], "nmrpa.optional_source_trusted_time.v1", "trusted_time.schema_version")
        if evidence["source_kind"] != source or evidence["request_scope_id"] != scope["request_scope_id"] or evidence["source_asof"] != response["source_asof"] or _time(evidence["available_at"], "trusted_time.available_at") != _time(response["available_at"], "response.available_at") or _time(evidence["available_at"], "trusted_time.available_at") > cutoff:
            _fail("NMRPA_TR_H_TRUSTED_TIME", "trusted-time identity/PIT differs")
        attempts = records["capture_attempt"]["payload"]["ordered_attempts"]
        first_success = next(item for item in attempts if item["result_class"] == "authoritative_success")
        publication = payload["publication_record_or_null"]
        if evidence["evidence_type"] == "first_successful_capture":
            if publication is not None or evidence["publication_record_ref_or_null"] is not None or evidence["first_success_attempt_ref_or_null"] != {"id": first_success["attempt_id"], "sha256": first_success["attempt_sha256"]} or evidence["available_at"] != first_success["completed_at"]:
                _fail("NMRPA_TR_H_TRUSTED_TIME", "first-success tagged union differs")
        elif evidence["evidence_type"] == "trusted_publication":
            if type(publication) is not dict or evidence["first_success_attempt_ref_or_null"] is not None:
                _fail("NMRPA_TR_H_TRUSTED_TIME", "publication tagged union differs")
            publication_fields = {"schema_version", "store_kind", "publication_record_id", "source_kind", "request_scope_id", "source_asof", "published_at", "issuer_registration_ref", "publication_head_ref", "publication_anchor_ref", "publication_record_sha256"}
            _exact(publication, publication_fields, "publication_record")
            _literal(publication["schema_version"], "nmrpa.optional_source_publication_record.v1", "publication.schema_version")
            _literal(publication["store_kind"], "response_evidence_store", "publication.store_kind")
            _sealed(publication, "publication_record_sha256", "nmrpa.optional_source.publication_record.v1")
            expected_ref = {"id": publication["publication_record_id"], "sha256": publication["publication_record_sha256"]}
            if evidence["publication_record_ref_or_null"] != expected_ref or publication["source_kind"] != source or publication["request_scope_id"] != scope["request_scope_id"] or publication["source_asof"] != response["source_asof"] or evidence["available_at"] != publication["published_at"] or publication["issuer_registration_ref"] != {"id": records["issuer_registration"]["object_id"], "sha256": records["issuer_registration"]["record_sha256"]} or publication["publication_head_ref"] != {"id": records["recorder_registration"]["object_id"], "sha256": records["recorder_registration"]["record_sha256"]} or publication["publication_anchor_ref"] != {"id": records["authorization"]["object_id"], "sha256": records["authorization"]["record_sha256"]}:
                _fail("NMRPA_TR_H_TRUSTED_TIME", "publication committed closure differs")
        else:
            _fail("NMRPA_TR_H_TRUSTED_TIME", "unsupported trusted-time evidence type")
        if evidence["trusted_time_issuer_ref"] != {"id": records["issuer_registration"]["object_id"], "sha256": records["issuer_registration"]["record_sha256"]} or evidence["trusted_time_head_ref"] != {"id": records["recorder_registration"]["object_id"], "sha256": records["recorder_registration"]["record_sha256"]} or evidence["trusted_time_anchor_ref"] != {"id": records["authorization"]["object_id"], "sha256": records["authorization"]["record_sha256"]}:
            _fail("NMRPA_TR_H_TRUSTED_TIME", "trusted-time issuer/head/anchor closure differs")
        _sealed(evidence, "trusted_time_evidence_sha256", "nmrpa.optional_source.trusted_time.v1")
    elif kind == "response_anchor":
        _exact(payload, common | {"anchor_id", "sealed_response_record_sha256", "inventory_record_sha256", "authorization_record_sha256", "historical_head_id"}, kind)
        if payload["anchor_id"] != records[kind]["object_id"] or payload["sealed_response_record_sha256"] != records["sealed_response"]["record_sha256"] or payload["inventory_record_sha256"] != records["inventory"]["record_sha256"] or payload["authorization_record_sha256"] != records["authorization"]["record_sha256"] or payload["historical_head_id"] != records["historical_head"]["object_id"]:
            _fail("NMRPA_TR_H_ANCHOR", "response anchor closure differs")
    elif kind == "historical_head":
        _exact(payload, common | {"head_id", "state", "last_authoritative_record_sha256", "ordered_record_sha256"}, kind)
        prior = [records[item]["record_sha256"] for item in AUTHORITATIVE_RECORD_KINDS[:-1]]
        if payload["head_id"] != records[kind]["object_id"] or payload["state"] != "committed" or payload["last_authoritative_record_sha256"] != records["response_anchor"]["record_sha256"] or payload["ordered_record_sha256"] != prior:
            _fail("NMRPA_TR_H_HEAD", "historical head closure differs")


def _validate_authoritative_closure(
    closure: Any, response: Mapping[str, Any], scope: Mapping[str, Any], source: str,
    cutoff: datetime,
) -> dict[str, Any]:
    _exact(closure, {"schema_version", "closure_id", "source_kind", "genesis_sha256", "ordered_records", "current_head", "closure_sha256"}, f"{source}.authoritative_closure")
    _literal(closure["schema_version"], "nmrpa.optional_source_authoritative_closure.v1", "closure.schema_version")
    _identifier(closure["closure_id"], "closure_id", "synthetic_"); _literal(closure["source_kind"], source, "closure.source_kind"); _sha(closure["genesis_sha256"], "genesis_sha256")
    ordered = closure["ordered_records"]
    if type(ordered) is not list or len(ordered) != len(AUTHORITATIVE_RECORD_KINDS):
        _fail("NMRPA_TR_H_REFERENCE_CLOSURE", "authoritative record cardinality differs")
    records: dict[str, Mapping[str, Any]] = {}
    previous = closure["genesis_sha256"]
    for sequence, (expected_kind, record) in enumerate(zip(AUTHORITATIVE_RECORD_KINDS, ordered), 1):
        _exact(record, {"schema_version", "record_kind", "store_kind", "source_kind", "object_id", "sequence", "previous_record_sha256", "payload", "record_sha256"}, f"record[{sequence}]")
        _literal(record["schema_version"], "nmrpa.optional_source_authoritative_record.v1", "record.schema_version")
        _literal(record["record_kind"], expected_kind, "record.record_kind"); _literal(record["store_kind"], AUTHORITATIVE_STORE_BY_KIND[expected_kind], "record.store_kind"); _literal(record["source_kind"], source, "record.source_kind")
        _identifier(record["object_id"], "record.object_id", "synthetic_")
        if _canonical_uint(record["sequence"], "record.sequence", 1) != sequence or record["previous_record_sha256"] != previous:
            _fail("NMRPA_TR_H_HISTORY", "authoritative history gap/fork")
        _sealed(record, "record_sha256", "nmrpa.optional_source.authoritative_record.v1")
        records[expected_kind] = record; previous = record["record_sha256"]
    for kind in AUTHORITATIVE_RECORD_KINDS:
        _validate_authoritative_payload(kind, records[kind]["payload"], response, scope, source, cutoff, records)
    head = _exact(closure["current_head"], {"schema_version", "closure_id", "source_kind", "sequence", "last_record_sha256", "history_sha256", "head_sha256"}, "authoritative current_head")
    _literal(head["schema_version"], "nmrpa.optional_source_authoritative_head.v1", "head.schema_version")
    if head["closure_id"] != closure["closure_id"] or head["source_kind"] != source or _canonical_uint(head["sequence"], "authoritative_head.sequence", 1) != len(ordered) or head["last_record_sha256"] != previous or head["history_sha256"] != digest([r["record_sha256"] for r in ordered], "nmrpa.optional_source.authoritative_history.v1"):
        _fail("NMRPA_TR_H_HEAD", "authoritative current head differs")
    _sealed(head, "head_sha256", "nmrpa.optional_source.authoritative_head.v1")
    refs = {
        "trusted_time": response["trusted_time_evidence_ref"], "issuer_registration": response["issuer_registration_ref"],
        "recorder_registration": response["capture_recorder_registration_ref"], "authorization": response["authorization_ref"],
        "response_anchor": response["response_anchor_ref"],
    }
    if response["capture_attempt_chain_sha256"] != records["capture_attempt"]["payload"]["capture_attempt_chain_sha256"]:
        _fail("NMRPA_TR_H_ATTEMPT", "attempt ref is not backed by committed record")
    for kind, ref_value in refs.items():
        expected = {"id": records[kind]["object_id"], "sha256": records[kind]["record_sha256"]}
        if "head_sha256" in ref_value: expected["head_sha256"] = head["head_sha256"]
        if ref_value != expected:
            _fail("NMRPA_TR_H_REFERENCE_CLOSURE", f"unbacked {kind} reference")
    if response["sealed_response_object_id"] != records["sealed_response"]["object_id"] or response["normalized_inventory_sha256"] != records["inventory"]["payload"]["normalized_inventory_sha256"]:
        _fail("NMRPA_TR_H_REFERENCE_CLOSURE", "sealed response/inventory ref is unbacked")
    _sealed(closure, "closure_sha256", "nmrpa.optional_source.authoritative_closure.v1")
    return records


def _authoritative_record_path(closure: Mapping[str, Any], record: Mapping[str, Any]) -> str:
    name = f"{closure['closure_id']}.{_canonical_uint(record['sequence'], 'record.sequence', 1):02d}.{record['record_kind']}.json"
    return f"{BASE}/stores/{record['store_kind']}/{name}"


def _validate_authoritative_substrate(
    project_root: str | os.PathLike[str], capability: tx_writer.SyntheticTestCapability,
    components: list[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]],
) -> None:
    root = Path(project_root)
    if not root.is_absolute() or root.resolve() != root or root == tx_writer.ACTUAL_PROJECT_ROOT or root == (tx_writer.ACTUAL_PROJECT_ROOT / BASE).resolve():
        _fail("NMRPA_TR_H_ACTUAL_ROOT_FORBIDDEN", "authoritative lookup requires canonical synthetic /tmp root")
    tx_writer._validate_capability(capability, root)
    iterable = components.values() if type(components) is dict else components
    for component in iterable:
        closure = component["authoritative_closure"]
        for record in closure["ordered_records"]:
            if _read(root, _authoritative_record_path(closure, record)) != record:
                _fail("NMRPA_TR_H_UNBACKED_REFERENCE", f"committed {record['record_kind']} record differs")
        index_path = f"{BASE}/stores/response_evidence_store/{closure['closure_id']}.authoritative_closure.json"
        if _read(root, index_path) != closure:
            _fail("NMRPA_TR_H_UNBACKED_REFERENCE", "authoritative closure index differs")


def validate_intent(intent: Any, descriptor: Mapping[str, Any], descriptor_sha256: str, project_root: str | os.PathLike[str] | None = None, capability: tx_writer.SyntheticTestCapability | None = None) -> dict[str, Any]:
    _walk(intent, "intent")
    descriptor = _validate_descriptor_pin(descriptor, descriptor_sha256)
    fields = {"artifact_kind", "schema_version", "mode", "transaction_id", "binding_id", "decision_date", "decision_time", "descriptor_sha256", "expected_previous_head", "authorization", "five_root_parent_binding_ref", "request_scope", "ordered_components", "issuer", "signature", "prepared_at", "committed_at", "intent_sha256"}
    _exact(intent, fields, "intent")
    _literal(intent["artifact_kind"], "optional_source_binding_intent", "artifact_kind"); _literal(intent["schema_version"], INTENT_SCHEMA_VERSION, "schema_version"); _literal(intent["mode"], MODE, "mode")
    tx = _str(intent["transaction_id"], "transaction_id")
    if not TX_RE.fullmatch(tx): _fail("NMRPA_TR_H_SCHEMA", "transaction id must be synthetic")
    binding_id = _identifier(intent["binding_id"], "binding_id", "synthetic_")
    decision_date = _date(intent["decision_date"], "decision_date").isoformat(); decision_time = _time(intent["decision_time"], "decision_time")
    if intent["descriptor_sha256"] != descriptor_sha256: _fail("NMRPA_TR_H_DESCRIPTOR", "intent descriptor differs")
    previous = _validate_head(intent["expected_previous_head"])
    auth = _exact(intent["authorization"], {"authorization_id", "allowed_binding_id", "allowed_decision_date", "expected_previous_head_sha256", "max_consumptions", "consumption_count", "terminal", "authorization_sha256"}, "authorization")
    _identifier(auth["authorization_id"], "authorization_id", "synthetic_")
    if auth["allowed_binding_id"] != binding_id or auth["allowed_decision_date"] != decision_date or auth["expected_previous_head_sha256"] != previous["head_sha256"] or _canonical_uint(auth["max_consumptions"], "authorization.max_consumptions") != 1 or _canonical_uint(auth["consumption_count"], "authorization.consumption_count") != 0 or auth["terminal"] is not False:
        _fail("NMRPA_TR_H_AUTH", "one-shot authorization scope/state invalid")
    _sealed(auth, "authorization_sha256", "nmrpa.optional_source.authorization.synthetic.v1")
    parent = _exact(intent["five_root_parent_binding_ref"], {"binding_id", "binding_record_sha256", "head_sha256"}, "parent")
    _identifier(parent["binding_id"], "parent.binding_id"); _sha(parent["binding_record_sha256"], "parent.binding_record_sha256"); _sha(parent["head_sha256"], "parent.head_sha256")
    active, grid = _validate_scope(intent["request_scope"], decision_date, decision_time)
    if intent["request_scope"]["calendar_binding_id"] != parent["binding_id"]: _fail("NMRPA_TR_H_PARENT", "request scope parent differs")
    components = intent["ordered_components"]
    if type(components) is not list or len(components) != 2: _fail("NMRPA_TR_H_SOURCE", "exactly two ordered components required")
    if any(type(component) is not dict for component in components) or [component.get("source_kind") for component in components] != list(SOURCE_KINDS):
        _fail("NMRPA_TR_H_SOURCE", "component source order differs")
    for source, component in zip(SOURCE_KINDS, components): _validate_component(component, source, intent["request_scope"], active, grid, decision_time)
    if project_root is None or capability is None:
        _fail("NMRPA_TR_H_CAPABILITY", "authoritative substrate lookup capability is required")
    _validate_authoritative_substrate(project_root, capability, components)
    # Planning is meaningful only against a closed store. This scans every
    # canonical store before a plan can be emitted; commit repeats the check.
    _closure(Path(project_root))
    issuer = _exact(intent["issuer"], {"issuer_identity_id", "issuer_credential_id", "registry_head_sha256"}, "issuer")
    for field in issuer: _identifier(issuer[field], field, "synthetic_") if field != "registry_head_sha256" else _sha(issuer[field], field)
    signature = _exact(intent["signature"], {"algorithm", "credential_id", "signed_digest", "signature_base64"}, "signature")
    _literal(signature["algorithm"], "ed25519", "signature.algorithm")
    if signature["credential_id"] != issuer["issuer_credential_id"]: _fail("NMRPA_TR_H_SIGNATURE", "credential mismatch")
    _sha(signature["signed_digest"], "signature.signed_digest")
    try: raw = base64.b64decode(_str(signature["signature_base64"], "signature_base64"), validate=True)
    except (ValueError, binascii.Error) as exc: raise ContractError("NMRPA_TR_H_SIGNATURE", "invalid base64") from exc
    if len(raw) != 64 or base64.b64encode(raw).decode() != signature["signature_base64"]: _fail("NMRPA_TR_H_SIGNATURE", "signature must encode 64 bytes")
    prepared, committed = _time(intent["prepared_at"], "prepared_at"), _time(intent["committed_at"], "committed_at")
    if not decision_time <= prepared <= committed: _fail("NMRPA_TR_H_TIME", "transaction time order differs")
    _sealed(intent, "intent_sha256", "nmrpa.optional_source.binding_intent.synthetic.v1")
    return {"ok": True, "active_count": 150, "grid_count": 10, "source_kinds": list(SOURCE_KINDS), "payload_bytes_read": 0, "write_permitted": False}


def plan(intent: Mapping[str, Any], descriptor: Mapping[str, Any], descriptor_sha256: str, project_root: str | os.PathLike[str], capability: tx_writer.SyntheticTestCapability) -> dict[str, Any]:
    validate_intent(intent, descriptor, descriptor_sha256, project_root, capability)
    sequence = _canonical_uint(intent["expected_previous_head"]["sequence"], "expected_previous_head.sequence") + 1
    sequence_text = str(sequence)
    previous_commit = None if sequence == 1 else intent["expected_previous_head"]["commit_sha256"]
    scope = intent["request_scope"]
    components_by_source = {component["source_kind"]: component for component in intent["ordered_components"]}
    responses = {source: components_by_source[source]["response_evidence"] for source in SOURCE_KINDS}
    binding = {"schema_version": "nmrpa.optional_source_daily_binding.v1", "profile_id": PROFILE, "binding_id": intent["binding_id"], "transaction_id": intent["transaction_id"], "decision_date": intent["decision_date"], "decision_time": intent["decision_time"], "five_root_parent_binding_ref": intent["five_root_parent_binding_ref"], "request_scope_ref": {"request_scope_id": scope["request_scope_id"], "request_scope_sha256": scope["request_scope_sha256"]}, "ordered_components": [{"source_kind": c["source_kind"], "response_evidence_ref": {"id": c["response_evidence"]["response_evidence_id"], "sha256": c["response_evidence"]["response_evidence_sha256"]}, "result_class": c["response_evidence"]["result_class"], "source_asof": c["response_evidence"]["source_asof"], "available_at": c["response_evidence"]["available_at"], "active_instrument_set_sha256": scope["active_instrument_set_sha256"], "trading_date_grid_10_sha256": scope["trading_date_grid_10_sha256"], "ordered_instrument_evidence_refs": [{"instrument": e["instrument"], "state": e["evidence_state"], "sha256": e["instrument_evidence_sha256"]} for e in c["ordered_instrument_evidence"]], "present_instrument_set_sha256": c["response_evidence"]["returned_instrument_set_sha256"], "confirmed_absent_instrument_set_sha256": c["response_evidence"]["absent_instrument_set_sha256"], "component_inventory_sha256": c["component_inventory_sha256"], "component_sha256": c["component_sha256"]} for c in intent["ordered_components"]], "authorization_ref": {"id": intent["authorization"]["authorization_id"], "sha256": intent["authorization"]["authorization_sha256"]}, "registry_ref": {"id": intent["issuer"]["issuer_identity_id"], "sha256": intent["issuer"]["registry_head_sha256"]}, "descriptor_sha256": descriptor_sha256}
    binding["binding_record_sha256"] = digest(binding, "nmrpa.optional_source.daily_binding.v1")
    anchor = {"schema_version": "nmrpa.optional_source_binding_anchor.v1", "anchor_id": f"synthetic_anchor_{intent['binding_id']}", "binding_record_sha256": binding["binding_record_sha256"], "request_scope_sha256": scope["request_scope_sha256"], "ordered_response_evidence_sha256": [responses[s]["response_evidence_sha256"] for s in SOURCE_KINDS], "parent_head_sha256": intent["five_root_parent_binding_ref"]["head_sha256"], "committed_at": intent["committed_at"]}
    anchor["anchor_sha256"] = digest(anchor, "nmrpa.optional_source.binding_anchor.v1")
    body = {"schema_version": "nmrpa.optional_source_commit_body.v1", "log_id": LOG_ID, "transaction_id": intent["transaction_id"], "sequence": sequence_text, "previous_commit_sha256": previous_commit, "event_type": "optional_source_binding_committed", "issued_at": intent["decision_time"], "issuer_identity_id": intent["issuer"]["issuer_identity_id"], "issuer_credential_id": intent["issuer"]["issuer_credential_id"], "payload": {"binding_record_sha256": binding["binding_record_sha256"], "anchor_sha256": anchor["anchor_sha256"]}}
    body_sha = digest(body, "nmrpa.optional_source.commit_body.v1")
    if intent["signature"]["signed_digest"] != body_sha: _fail("NMRPA_TR_H_SIGNATURE", "signature does not bind commit body")
    signed = {"schema_version": "nmrpa.optional_source_signed_record.v1", "record_body": body, "record_body_sha256": body_sha, "signature": intent["signature"]}; signed["signed_record_sha256"] = digest(signed, "nmrpa.optional_source.signed_record.v1")
    journal = {"schema_version": "nmrpa.optional_source_transaction_journal.v1", "log_id": LOG_ID, "transaction_id": intent["transaction_id"], "sequence": sequence_text, "previous_commit_sha256": previous_commit, "expected_previous_head_sha256": intent["expected_previous_head"]["head_sha256"], "signed_record_sha256": signed["signed_record_sha256"], "state": "prepared", "prepared_at": intent["prepared_at"]}; journal["journal_sha256"] = digest(journal, "nmrpa.optional_source.journal.v1")
    marker = {"schema_version": "nmrpa.optional_source_commit_marker.v1", "log_id": LOG_ID, "transaction_id": intent["transaction_id"], "sequence": sequence_text, "previous_commit_sha256": previous_commit, "expected_previous_head_sha256": intent["expected_previous_head"]["head_sha256"], "record_body_sha256": body_sha, "signed_record_sha256": signed["signed_record_sha256"], "journal_sha256": journal["journal_sha256"], "committed_at": intent["committed_at"]}; marker["commit_sha256"] = digest(marker, "nmrpa.optional_source.commit_marker.v1")
    head = {"schema_version": "nmrpa.optional_source.binding_log_committed_head.v1", "log_id": LOG_ID, "sequence": sequence_text, "transaction_id": intent["transaction_id"], "previous_head_sha256": intent["expected_previous_head"]["head_sha256"], "commit_sha256": marker["commit_sha256"], "committed_at": intent["committed_at"]}; head["head_sha256"] = digest(head, "nmrpa.optional_source.binding.committed_head.v1")
    tx = intent["transaction_id"]
    paths = {"request_scope": f"{BASE}/stores/optional_source_profile_registry/{tx}.request_scope.json", "response_evidence": f"{BASE}/stores/response_evidence_store/{tx}.responses.json", "binding": f"{BASE}/stores/binding_store/{tx}.binding.json", "anchor": f"{BASE}/stores/anchor_ledger/{tx}.anchor.json", "signed_record": f"{LOG_BASE}/journals/{tx}.record.json", "journal": f"{LOG_BASE}/journals/{tx}.journal.json", "marker": f"{LOG_BASE}/commit_markers/{tx}.commit.json", "history": f"{LOG_BASE}/historical_heads.json", "head": f"{LOG_BASE}/head.json"}
    result = {"artifact_kind": "optional_source_binding_plan", "schema_version": PLAN_SCHEMA_VERSION, "mode": MODE, "transaction_id": tx, "binding_id": intent["binding_id"], "authorization_id": intent["authorization"]["authorization_id"], "descriptor_sha256": descriptor_sha256, "expected_previous_head": intent["expected_previous_head"], "request_scope": scope, "response_evidence": components_by_source, "binding_record": binding, "anchor_record": anchor, "signed_record": signed, "journal": journal, "commit_marker": marker, "new_head": head, "paths": paths, "staging_paths": {key: f"{value}.nmrpa-tr-h-stage" for key, value in paths.items()}, "commit_order": ["request_scope", "response_evidence", "binding", "anchor", "signed_record", "journal", "marker", "history", "head"]}
    result["plan_sha256"] = digest(result, "nmrpa.optional_source.binding_plan.synthetic.v1")
    validate_plan(result, descriptor, descriptor_sha256)
    return result


def validate_plan(value: Any, descriptor: Mapping[str, Any], descriptor_sha256: str) -> dict[str, Any]:
    _walk(value, "plan"); _validate_descriptor_pin(descriptor, descriptor_sha256)
    fields = {"artifact_kind", "schema_version", "mode", "transaction_id", "binding_id", "authorization_id", "descriptor_sha256", "expected_previous_head", "request_scope", "response_evidence", "binding_record", "anchor_record", "signed_record", "journal", "commit_marker", "new_head", "paths", "staging_paths", "commit_order", "plan_sha256"}
    _exact(value, fields, "plan"); _literal(value["artifact_kind"], "optional_source_binding_plan", "artifact_kind"); _literal(value["schema_version"], PLAN_SCHEMA_VERSION, "schema_version"); _literal(value["mode"], MODE, "mode")
    tx = value["transaction_id"]
    if not TX_RE.fullmatch(_str(tx, "transaction_id")): _fail("NMRPA_TR_H_SCHEMA", "invalid transaction")
    _identifier(value["binding_id"], "binding_id", "synthetic_"); _identifier(value["authorization_id"], "authorization_id", "synthetic_")
    if value["descriptor_sha256"] != descriptor_sha256: _fail("NMRPA_TR_H_DESCRIPTOR", "plan descriptor differs")
    previous = _validate_head(value["expected_previous_head"]); sequence = _canonical_uint(previous["sequence"], "previous.sequence") + 1; sequence_text = str(sequence); previous_commit = None if sequence == 1 else previous["commit_sha256"]
    scope = value["request_scope"]; active, grid = _validate_scope(scope, scope["decision_date"], _time(scope["decision_time"], "decision_time"))
    components = value["response_evidence"]
    _exact(components, set(SOURCE_KINDS), "response_evidence")
    for source in SOURCE_KINDS: _validate_component(components[source], source, scope, active, grid, _time(scope["decision_time"], "decision_time"))
    responses = {source: components[source]["response_evidence"] for source in SOURCE_KINDS}
    binding = value["binding_record"]
    _exact(binding, {"schema_version", "profile_id", "binding_id", "transaction_id", "decision_date", "decision_time", "five_root_parent_binding_ref", "request_scope_ref", "ordered_components", "authorization_ref", "registry_ref", "descriptor_sha256", "binding_record_sha256"}, "binding_record")
    _literal(binding["schema_version"], "nmrpa.optional_source_daily_binding.v1", "binding.schema_version"); _literal(binding["profile_id"], PROFILE, "binding.profile_id")
    _date(binding["decision_date"], "binding.decision_date"); _time(binding["decision_time"], "binding.decision_time")
    _sealed(binding, "binding_record_sha256", "nmrpa.optional_source.daily_binding.v1")
    if binding["transaction_id"] != tx or binding["binding_id"] != value["binding_id"] or binding["authorization_ref"]["id"] != value["authorization_id"] or binding["decision_date"] != scope["decision_date"] or binding["decision_time"] != scope["decision_time"] or binding["descriptor_sha256"] != descriptor_sha256 or binding["request_scope_ref"] != {"request_scope_id": scope["request_scope_id"], "request_scope_sha256": scope["request_scope_sha256"]} or binding["five_root_parent_binding_ref"]["binding_id"] != scope["calendar_binding_id"] or [c["source_kind"] for c in binding["ordered_components"]] != list(SOURCE_KINDS) or len(binding["ordered_components"]) != 2:
        _fail("NMRPA_TR_H_CROSS_BINDING", "daily binding identity/components differ")
    expected_binding_components = [{"source_kind": c["source_kind"], "response_evidence_ref": {"id": c["response_evidence"]["response_evidence_id"], "sha256": c["response_evidence"]["response_evidence_sha256"]}, "result_class": c["response_evidence"]["result_class"], "source_asof": c["response_evidence"]["source_asof"], "available_at": c["response_evidence"]["available_at"], "active_instrument_set_sha256": scope["active_instrument_set_sha256"], "trading_date_grid_10_sha256": scope["trading_date_grid_10_sha256"], "ordered_instrument_evidence_refs": [{"instrument": e["instrument"], "state": e["evidence_state"], "sha256": e["instrument_evidence_sha256"]} for e in c["ordered_instrument_evidence"]], "present_instrument_set_sha256": c["response_evidence"]["returned_instrument_set_sha256"], "confirmed_absent_instrument_set_sha256": c["response_evidence"]["absent_instrument_set_sha256"], "component_inventory_sha256": c["component_inventory_sha256"], "component_sha256": c["component_sha256"]} for c in (components["institutional"], components["margin"])]
    if binding["ordered_components"] != expected_binding_components:
        _fail("NMRPA_TR_H_CROSS_BINDING", "binding component refs differ from sealed evidence")
    for field in ("five_root_parent_binding_ref",):
        _exact(binding[field], {"binding_id", "binding_record_sha256", "head_sha256"}, field)
    for field in ("authorization_ref", "registry_ref"):
        _simple_ref(binding[field], field)
    anchor = value["anchor_record"]
    _exact(anchor, {"schema_version", "anchor_id", "binding_record_sha256", "request_scope_sha256", "ordered_response_evidence_sha256", "parent_head_sha256", "committed_at", "anchor_sha256"}, "anchor_record")
    _literal(anchor["schema_version"], "nmrpa.optional_source_binding_anchor.v1", "anchor.schema_version"); _time(anchor["committed_at"], "anchor.committed_at")
    _sealed(anchor, "anchor_sha256", "nmrpa.optional_source.binding_anchor.v1")
    if anchor["binding_record_sha256"] != binding["binding_record_sha256"] or anchor["request_scope_sha256"] != scope["request_scope_sha256"] or anchor["ordered_response_evidence_sha256"] != [responses[s]["response_evidence_sha256"] for s in SOURCE_KINDS] or anchor["parent_head_sha256"] != binding["five_root_parent_binding_ref"]["head_sha256"]: _fail("NMRPA_TR_H_CROSS_BINDING", "anchor refs differ")
    signed, journal, marker, head = value["signed_record"], value["journal"], value["commit_marker"], value["new_head"]
    _exact(signed, {"schema_version", "record_body", "record_body_sha256", "signature", "signed_record_sha256"}, "signed_record")
    _literal(signed["schema_version"], "nmrpa.optional_source_signed_record.v1", "signed.schema_version")
    _sealed(signed, "signed_record_sha256", "nmrpa.optional_source.signed_record.v1"); _sealed(journal, "journal_sha256", "nmrpa.optional_source.journal.v1"); _sealed(marker, "commit_sha256", "nmrpa.optional_source.commit_marker.v1"); _validate_head(head)
    body = signed["record_body"]
    _exact(body, {"schema_version", "log_id", "transaction_id", "sequence", "previous_commit_sha256", "event_type", "issued_at", "issuer_identity_id", "issuer_credential_id", "payload"}, "record_body")
    _literal(body["schema_version"], "nmrpa.optional_source_commit_body.v1", "body.schema_version"); _literal(body["log_id"], LOG_ID, "body.log_id"); _literal(body["event_type"], "optional_source_binding_committed", "body.event_type"); _canonical_uint(body["sequence"], "body.sequence", 1); _time(body["issued_at"], "body.issued_at")
    _exact(body["payload"], {"binding_record_sha256", "anchor_sha256"}, "record_body.payload")
    signature = signed["signature"]
    _exact(signature, {"algorithm", "credential_id", "signed_digest", "signature_base64"}, "signature")
    if signature["algorithm"] != "ed25519" or signature["credential_id"] != body["issuer_credential_id"] or signature["signed_digest"] != signed["record_body_sha256"]:
        _fail("NMRPA_TR_H_SIGNATURE", "plan signature refs differ")
    try: decoded = base64.b64decode(_str(signature["signature_base64"], "signature_base64"), validate=True)
    except (ValueError, binascii.Error) as exc: raise ContractError("NMRPA_TR_H_SIGNATURE", "invalid plan signature base64") from exc
    if len(decoded) != 64 or base64.b64encode(decoded).decode() != signature["signature_base64"]: _fail("NMRPA_TR_H_SIGNATURE", "plan signature length differs")
    if signed["record_body_sha256"] != digest(body, "nmrpa.optional_source.commit_body.v1") or body["transaction_id"] != tx or body["sequence"] != sequence_text or body["previous_commit_sha256"] != previous_commit or body["payload"] != {"binding_record_sha256": binding["binding_record_sha256"], "anchor_sha256": anchor["anchor_sha256"]}: _fail("NMRPA_TR_H_CHAIN", "signed body differs")
    _exact(journal, {"schema_version", "log_id", "transaction_id", "sequence", "previous_commit_sha256", "expected_previous_head_sha256", "signed_record_sha256", "state", "prepared_at", "journal_sha256"}, "journal")
    _exact(marker, {"schema_version", "log_id", "transaction_id", "sequence", "previous_commit_sha256", "expected_previous_head_sha256", "record_body_sha256", "signed_record_sha256", "journal_sha256", "committed_at", "commit_sha256"}, "marker")
    _literal(journal["schema_version"], "nmrpa.optional_source_transaction_journal.v1", "journal.schema_version"); _literal(journal["log_id"], LOG_ID, "journal.log_id"); _canonical_uint(journal["sequence"], "journal.sequence", 1); _time(journal["prepared_at"], "journal.prepared_at")
    _literal(marker["schema_version"], "nmrpa.optional_source_commit_marker.v1", "marker.schema_version"); _literal(marker["log_id"], LOG_ID, "marker.log_id"); _canonical_uint(marker["sequence"], "marker.sequence", 1); _time(marker["committed_at"], "marker.committed_at")
    shared = (LOG_ID, tx, sequence_text, previous_commit)
    if (journal["log_id"], journal["transaction_id"], journal["sequence"], journal["previous_commit_sha256"]) != shared or (marker["log_id"], marker["transaction_id"], marker["sequence"], marker["previous_commit_sha256"]) != shared or journal["expected_previous_head_sha256"] != previous["head_sha256"] or journal["signed_record_sha256"] != signed["signed_record_sha256"] or journal["state"] != "prepared" or marker["expected_previous_head_sha256"] != previous["head_sha256"] or marker["record_body_sha256"] != signed["record_body_sha256"] or marker["journal_sha256"] != journal["journal_sha256"] or marker["signed_record_sha256"] != signed["signed_record_sha256"] or head["commit_sha256"] != marker["commit_sha256"] or head["previous_head_sha256"] != previous["head_sha256"]:
        _fail("NMRPA_TR_H_CHAIN", "journal/marker/head chain differs")
    paths = value["paths"]; expected_paths = {"request_scope": f"{BASE}/stores/optional_source_profile_registry/{tx}.request_scope.json", "response_evidence": f"{BASE}/stores/response_evidence_store/{tx}.responses.json", "binding": f"{BASE}/stores/binding_store/{tx}.binding.json", "anchor": f"{BASE}/stores/anchor_ledger/{tx}.anchor.json", "signed_record": f"{LOG_BASE}/journals/{tx}.record.json", "journal": f"{LOG_BASE}/journals/{tx}.journal.json", "marker": f"{LOG_BASE}/commit_markers/{tx}.commit.json", "history": f"{LOG_BASE}/historical_heads.json", "head": f"{LOG_BASE}/head.json"}
    if paths != expected_paths or value["staging_paths"] != {k: f"{v}.nmrpa-tr-h-stage" for k, v in expected_paths.items()} or value["commit_order"] != ["request_scope", "response_evidence", "binding", "anchor", "signed_record", "journal", "marker", "history", "head"]:
        _fail("NMRPA_TR_H_PATH", "schema-driven path/order differs")
    _sealed(value, "plan_sha256", "nmrpa.optional_source.binding_plan.synthetic.v1")
    return {"ok": True, "sequence": sequence, "payload_bytes_read": 0, "write_permitted": False}


def _read(root: Path, relative: str) -> Any:
    return tx_writer._read_control_json(root, relative)


def _authoritative_store_names(root: Path) -> dict[str, set[str]]:
    names = {store: set() for store in set(AUTHORITATIVE_STORE_BY_KIND.values())}
    index_relative = f"{BASE}/stores/response_evidence_store"
    index_dir = tx_writer._confined(root, index_relative, must_exist=True)
    for child in index_dir.iterdir():
        if not child.name.endswith(".authoritative_closure.json"):
            continue
        closure = _read(root, f"{index_relative}/{child.name}")
        _walk(closure, "stored_authoritative_closure")
        _exact(closure, {"schema_version", "closure_id", "source_kind", "genesis_sha256", "ordered_records", "current_head", "closure_sha256"}, "stored authoritative closure")
        _literal(closure["schema_version"], "nmrpa.optional_source_authoritative_closure.v1", "closure.schema_version")
        if child.name != f"{closure['closure_id']}.authoritative_closure.json":
            _fail("NMRPA_TR_H_ORPHAN", "authoritative closure index filename differs")
        ordered = closure["ordered_records"]
        if type(ordered) is not list or len(ordered) != len(AUTHORITATIVE_RECORD_KINDS):
            _fail("NMRPA_TR_H_HISTORY", "stored authoritative history cardinality differs")
        previous = closure["genesis_sha256"]
        for sequence, (kind, record) in enumerate(zip(AUTHORITATIVE_RECORD_KINDS, ordered), 1):
            if record.get("record_kind") != kind or record.get("store_kind") != AUTHORITATIVE_STORE_BY_KIND[kind] or _canonical_uint(record.get("sequence"), "stored record.sequence", 1) != sequence or record.get("previous_record_sha256") != previous:
                _fail("NMRPA_TR_H_HISTORY", "stored authoritative history gap/fork")
            _sealed(record, "record_sha256", "nmrpa.optional_source.authoritative_record.v1")
            path = _authoritative_record_path(closure, record)
            if _read(root, path) != record:
                _fail("NMRPA_TR_H_UNBACKED_REFERENCE", "stored authoritative record differs")
            names[record["store_kind"]].add(Path(path).name)
            previous = record["record_sha256"]
        _sealed(closure["current_head"], "head_sha256", "nmrpa.optional_source.authoritative_head.v1")
        if closure["current_head"].get("last_record_sha256") != previous:
            _fail("NMRPA_TR_H_HEAD", "stored authoritative head does not close history")
        _sealed(closure, "closure_sha256", "nmrpa.optional_source.authoritative_closure.v1")
        names["response_evidence_store"].add(child.name)
    return names


def _closure(root: Path) -> dict[str, Any]:
    descriptor = _read(root, f"{BASE}/descriptor.json")
    _validate_descriptor_pin(descriptor, descriptor.get("descriptor_sha256"))
    head = _read(root, f"{LOG_BASE}/head.json"); history_obj = _read(root, f"{LOG_BASE}/historical_heads.json")
    _validate_head(head)
    if type(history_obj) is dict and history_obj.get("schema_version") == "nmrpa.optional_source.binding_log_history.v1": history = history_obj.get("heads")
    else: history = history_obj
    if type(history) is not list or not history or history[-1] != head: _fail("NMRPA_TR_H_HISTORY", "history/head closure differs")
    transactions: set[str] = set(); auths: set[str] = set(); bindings: set[str] = set(); previous = None
    for index, item in enumerate(history):
        _validate_head(item)
        if _canonical_uint(item["sequence"], "history.sequence") != index or index and item["previous_head_sha256"] != previous["head_sha256"]: _fail("NMRPA_TR_H_HISTORY", "history gap/fork")
        if index:
            tx = item["transaction_id"]; paths = {"request": f"{BASE}/stores/optional_source_profile_registry/{tx}.request_scope.json", "responses": f"{BASE}/stores/response_evidence_store/{tx}.responses.json", "binding": f"{BASE}/stores/binding_store/{tx}.binding.json", "anchor": f"{BASE}/stores/anchor_ledger/{tx}.anchor.json", "record": f"{LOG_BASE}/journals/{tx}.record.json", "journal": f"{LOG_BASE}/journals/{tx}.journal.json", "marker": f"{LOG_BASE}/commit_markers/{tx}.commit.json"}
            objects = {key: _read(root, path) for key, path in paths.items()}
            reconstructed_paths = {"request_scope": paths["request"], "response_evidence": paths["responses"], "binding": paths["binding"], "anchor": paths["anchor"], "signed_record": paths["record"], "journal": paths["journal"], "marker": paths["marker"], "history": f"{LOG_BASE}/historical_heads.json", "head": f"{LOG_BASE}/head.json"}
            candidate = {"artifact_kind": "optional_source_binding_plan", "schema_version": PLAN_SCHEMA_VERSION, "mode": MODE, "transaction_id": tx, "binding_id": objects["binding"].get("binding_id"), "authorization_id": objects["binding"].get("authorization_ref", {}).get("id"), "descriptor_sha256": objects["binding"].get("descriptor_sha256"), "expected_previous_head": previous, "request_scope": objects["request"], "response_evidence": objects["responses"], "binding_record": objects["binding"], "anchor_record": objects["anchor"], "signed_record": objects["record"], "journal": objects["journal"], "commit_marker": objects["marker"], "new_head": item, "paths": reconstructed_paths, "staging_paths": {key: f"{value}.nmrpa-tr-h-stage" for key, value in reconstructed_paths.items()}, "commit_order": ["request_scope", "response_evidence", "binding", "anchor", "signed_record", "journal", "marker", "history", "head"]}
            candidate["plan_sha256"] = digest(candidate, "nmrpa.optional_source.binding_plan.synthetic.v1")
            validate_plan(candidate, descriptor, descriptor["descriptor_sha256"])
            if objects["marker"]["commit_sha256"] != item["commit_sha256"] or objects["binding"]["transaction_id"] != tx: _fail("NMRPA_TR_H_ORPHAN", "historical artifact mismatch")
            transactions.add(tx); auths.add(objects["binding"]["authorization_ref"]["id"]); bindings.add(objects["binding"]["binding_id"])
        previous = item
    authoritative_names = _authoritative_store_names(root)
    expected_suffixes = {f"{LOG_BASE}/journals": {f"{tx}.record.json" for tx in transactions} | {f"{tx}.journal.json" for tx in transactions}, f"{LOG_BASE}/commit_markers": {f"{tx}.commit.json" for tx in transactions}, f"{BASE}/stores/binding_store": {f"{tx}.binding.json" for tx in transactions}, f"{BASE}/stores/anchor_ledger": {f"{tx}.anchor.json" for tx in transactions} | authoritative_names["anchor_ledger"], f"{BASE}/stores/optional_source_profile_registry": {f"{tx}.request_scope.json" for tx in transactions} | authoritative_names["optional_source_profile_registry"], f"{BASE}/stores/response_evidence_store": {f"{tx}.responses.json" for tx in transactions} | authoritative_names["response_evidence_store"], f"{BASE}/stores/capture_attempt_store": authoritative_names["capture_attempt_store"], f"{BASE}/stores/sealed_object_store": authoritative_names["sealed_object_store"], f"{BASE}/stores/authorization_ledger": authoritative_names["authorization_ledger"]}
    for relative, expected in expected_suffixes.items():
        directory = tx_writer._confined(root, relative, must_exist=True)
        names = {child.name for child in directory.iterdir()}
        if names != expected: _fail("NMRPA_TR_H_ORPHAN", f"store closure differs: {relative}")
    return {"current_head": head, "history": history_obj, "transaction_ids": transactions, "authorization_ids": auths, "binding_ids": bindings}


def commit(plan_value: Mapping[str, Any], descriptor: Mapping[str, Any], descriptor_sha256: str, project_root: str | os.PathLike[str], capability: tx_writer.SyntheticTestCapability, *, synthetic_fail_after_step: int | None = None) -> dict[str, Any]:
    actual_optional = (tx_writer.ACTUAL_PROJECT_ROOT / BASE).resolve()
    candidate = Path(project_root)
    if candidate.is_absolute() and candidate.resolve() == tx_writer.ACTUAL_PROJECT_ROOT or candidate.is_absolute() and candidate.resolve() == actual_optional:
        _fail("NMRPA_TR_H_ACTUAL_ROOT_FORBIDDEN", "actual repository/companion root forbidden")
    _validate_authoritative_substrate(project_root, capability, plan_value["response_evidence"])
    validation = lambda candidate_plan: validate_plan(candidate_plan, descriptor, descriptor_sha256)
    def post(root: Path, validated: Mapping[str, Any]) -> dict[str, Any]:
        closure = _closure(root)
        if closure["current_head"] != plan_value["new_head"] or plan_value["transaction_id"] not in closure["transaction_ids"]: _fail("NMRPA_TR_H_POST_COMMIT", "post-commit closure differs")
        return {"ok": True, "sequence": validated["sequence"], "head_sha256": closure["current_head"]["head_sha256"]}
    history_obj = _read(Path(project_root), f"{LOG_BASE}/historical_heads.json")
    existing_heads = history_obj["heads"] if type(history_obj) is dict else history_obj
    updated_history = {**history_obj, "heads": [*existing_heads, plan_value["new_head"]], "state": "active"} if type(history_obj) is dict else [*existing_heads, plan_value["new_head"]]
    immutable = {"request_scope": plan_value["request_scope"], "response_evidence": plan_value["response_evidence"], "binding": plan_value["binding_record"], "anchor": plan_value["anchor_record"], "signed_record": plan_value["signed_record"], "journal": plan_value["journal"], "marker": plan_value["commit_marker"]}
    mutable = {"history": updated_history, "head": plan_value["new_head"]}
    return tx_writer.commit_schema_driven_transaction(plan_value, project_root, capability, validate_plan=validation, load_closure=_closure, validate_post_commit=post, lock_relative_path=LOG_BASE, immutable_values=immutable, mutable_values=mutable, synthetic_fail_after_step=synthetic_fail_after_step)


__all__ = ["ContractError", "INTENT_SCHEMA_VERSION", "PLAN_SCHEMA_VERSION", "commit", "plan", "validate_intent", "validate_plan"]
