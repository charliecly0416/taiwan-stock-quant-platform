from __future__ import annotations

import base64
import copy
import json
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import tw_policy_nmrpa3_immutable_binding_writer as tx_writer
import tw_policy_nmrpa3_optional_source_binding as optional
import tw_policy_nmrpa3_optional_source_trust as trust

INTENT_SCHEMA = ROOT / "scripts/schemas/tw_policy_nmrpa3_optional_source_binding_intent.schema.json"
PLAN_SCHEMA = ROOT / "scripts/schemas/tw_policy_nmrpa3_optional_source_binding_plan.schema.json"


def seal(value, field, domain):
    value[field] = trust.digest({k: v for k, v in value.items() if k != field}, domain)


def ref(name):
    return {"id": f"synthetic_{name}", "sha256": trust.digest({"ref": name}, "test.ref"), "head_sha256": trust.digest({"head": name}, "test.head")}


def simple_ref(name):
    return {"id": f"synthetic_{name}", "sha256": trust.digest({"ref": name}, "test.ref")}


def descriptor():
    value = trust.descriptor()
    value["descriptor_sha256"] = trust.digest(value, "nmrpa.optional_source.trust.descriptor.v1")
    return value


def genesis_head():
    genesis = {"schema_version": "nmrpa.optional_source.binding_log_genesis.v1", "log_id": trust.LOG_ID, "sequence": 0, "previous_head_sha256": None, "profile_id": trust.PROFILE, "state": "genesis_only", "payload_evidence_state": "not_bound", "real_payload_read": False}
    genesis["genesis_sha256"] = trust.digest(genesis, "nmrpa.optional_source.binding.genesis.v1")
    head = {"schema_version": "nmrpa.optional_source.binding_log_head.v1", "log_id": trust.LOG_ID, "sequence": "0", "previous_head_sha256": None, "record_sha256": genesis["genesis_sha256"]}
    head["head_sha256"] = trust.digest(head, "nmrpa.optional_source.binding.head.v1")
    return genesis, head


def materialize(tmp_path):
    desc = descriptor(); genesis, head = genesis_head()
    directories = [
        optional.LOG_BASE, f"{optional.LOG_BASE}/journals", f"{optional.LOG_BASE}/commit_markers",
        f"{trust.BASE}/stores/optional_source_profile_registry", f"{trust.BASE}/stores/response_evidence_store",
        f"{trust.BASE}/stores/binding_store", f"{trust.BASE}/stores/anchor_ledger",
        f"{trust.BASE}/stores/capture_attempt_store", f"{trust.BASE}/stores/sealed_object_store",
        f"{trust.BASE}/stores/authorization_ledger",
    ]
    for relative in directories: (tmp_path / relative).mkdir(parents=True, exist_ok=True)
    (tmp_path / f"{trust.BASE}/descriptor.json").write_bytes(trust.canonical_json(desc))
    (tmp_path / f"{optional.LOG_BASE}/genesis.json").write_bytes(trust.canonical_json(genesis))
    (tmp_path / f"{optional.LOG_BASE}/head.json").write_bytes(trust.canonical_json(head))
    history = {"schema_version": "nmrpa.optional_source.binding_log_history.v1", "log_id": trust.LOG_ID, "heads": [head], "state": "genesis_only"}
    (tmp_path / f"{optional.LOG_BASE}/historical_heads.json").write_bytes(trust.canonical_json(history))
    return desc, head


def build_row(source, day, index):
    if source == "institutional":
        row = {"date": day, "source_asof": day, "available_at": f"{day}T08:00:00Z", "foreign_net_buy": index, "investment_trust_net_buy": index + 1, "dealer_net_buy": index + 2}
    else:
        row = {"date": day, "source_asof": day, "available_at": f"{day}T08:00:00Z", "margin_balance": 1000 + index * 10, "margin_balance_change": 10 if index else 0, "short_balance": 500 + index * 5, "short_balance_change": 5 if index else 0}
    seal(row, "normalized_row_sha256", f"nmrpa.optional_source.{source}.row.v1")
    return row


def build_authoritative_closure(root, source, suffix, scope, response, trusted_variant="capture"):
    closure_id = f"synthetic_authoritative_{source}_{suffix}"
    object_ids = {kind: f"synthetic_{kind}_{source}_{suffix}" for kind in optional.AUTHORITATIVE_RECORD_KINDS}
    common = {"source_kind": source, "decision_date": scope["decision_date"], "request_scope_sha256": scope["request_scope_sha256"]}
    genesis = trust.digest({"closure_id": closure_id, "source_kind": source}, "nmrpa.optional_source.authoritative_genesis.v1")
    records = []
    previous = genesis

    def append(kind, payload, object_id=None):
        nonlocal previous
        record = {"schema_version": "nmrpa.optional_source_authoritative_record.v1", "record_kind": kind, "store_kind": optional.AUTHORITATIVE_STORE_BY_KIND[kind], "source_kind": source, "object_id": object_id or object_ids[kind], "sequence": str(len(records) + 1), "previous_record_sha256": previous, "payload": payload}
        seal(record, "record_sha256", "nmrpa.optional_source.authoritative_record.v1")
        records.append(record)
        previous = record["record_sha256"]
        return record

    issuer = append("issuer_registration", {**common, "registration_id": object_ids["issuer_registration"], "principal_registration_id": f"synthetic_principal_{source}", "identity_binding_id": f"synthetic_identity_binding_{source}", "credential_activation_id": f"synthetic_credential_{source}", "trusted_service_registration_id": f"synthetic_trusted_service_{source}", "identity_id": f"synthetic_issuer_identity_{source}", "status": "active", "committed_at": f"{scope['decision_date']}T09:00:00Z", "valid_from": f"{scope['decision_date']}T09:00:00Z", "valid_until_or_null": None})
    recorder = append("recorder_registration", {**common, "registration_id": object_ids["recorder_registration"], "recorder_id": f"synthetic_recorder_{source}", "issuer_registration_id": object_ids["issuer_registration"], "status": "active", "committed_at": f"{scope['decision_date']}T09:10:00Z", "valid_from": f"{scope['decision_date']}T09:10:00Z", "valid_until_or_null": None})
    profile = append("profile_registration", {**common, "registration_id": object_ids["profile_registration"], "profile_id": trust.PROFILE, "issuer_registration_id": object_ids["issuer_registration"], "recorder_registration_id": object_ids["recorder_registration"], "status": "active", "committed_at": f"{scope['decision_date']}T09:20:00Z", "valid_from": f"{scope['decision_date']}T09:20:00Z", "valid_until_or_null": None})
    authorization = append("authorization", {**common, "authorization_id": object_ids["authorization"], "allowed_sealed_response_object_id": response["sealed_response_object_id"], "issuer_registration_id": object_ids["issuer_registration"], "recorder_registration_id": object_ids["recorder_registration"], "profile_registration_id": object_ids["profile_registration"], "issued_at": f"{scope['decision_date']}T09:25:00Z", "committed_at": f"{scope['decision_date']}T09:30:00Z", "committed_under_head_sha256": profile["record_sha256"], "max_consumptions": "1", "consumption_count": "0", "terminal": False})
    attempt_specs = [
        ("transport_failed", "09:40:00", "09:41:00", None),
        ("rate_limited", "09:45:00", "09:46:00", "429"),
        ("authoritative_success", "09:59:00", "10:00:00", "200"),
    ]
    attempts = []
    for index, (result, started, completed, status) in enumerate(attempt_specs, 1):
        attempt = {"schema_version": "nmrpa.optional_source_capture_attempt.v1", "capture_run_id": f"synthetic_capture_run_{source}_{suffix}", "attempt_id": f"synthetic_attempt_{source}_{suffix}_{index}", "source_kind": source, "request_scope_id": scope["request_scope_id"], "request_scope_sha256": scope["request_scope_sha256"], "sequence": str(index), "request_identity_sha256": trust.digest({"source": source, "scope": scope["request_scope_sha256"]}, "test.request_identity"), "started_at": f"{scope['decision_date']}T{started}Z", "completed_at": f"{scope['decision_date']}T{completed}Z", "result_class": result, "http_status_or_null": status, "sealed_response_object_id_or_null": response["sealed_response_object_id"] if result == "authoritative_success" else None, "sealed_response_raw_sha256_or_null": response["sealed_response_raw_sha256"] if result == "authoritative_success" else None, "issuer_registration_ref": {"id": object_ids["issuer_registration"], "sha256": issuer["record_sha256"]}, "capture_recorder_head_ref": {"id": object_ids["recorder_registration"], "sha256": recorder["record_sha256"]}}
        seal(attempt, "attempt_sha256", "nmrpa.optional_source.capture_attempt.v1")
        attempts.append(attempt)
    chain_sha = trust.digest([attempt["attempt_sha256"] for attempt in attempts], "nmrpa.optional_source.capture_attempt_chain.v1")
    capture = append("capture_attempt", {**common, "capture_run_id": f"synthetic_capture_run_{source}_{suffix}", "ordered_attempts": attempts, "capture_attempt_chain_sha256": chain_sha})
    success = attempts[-1]
    sealed_response = append("sealed_response", {**common, "object_id": response["sealed_response_object_id"], "raw_sha256": response["sealed_response_raw_sha256"], "payload_sha256": response["payload_sha256"], "payload_byte_size": response["payload_byte_size"], "inventory_id": object_ids["inventory"], "attempt_id": success["attempt_id"]}, response["sealed_response_object_id"])
    inventory = append("inventory", {**common, "inventory_id": object_ids["inventory"], "normalized_inventory_sha256": response["normalized_inventory_sha256"], "ordered_returned_instruments": response["ordered_returned_instruments"], "ordered_absent_instruments": response["ordered_absent_instruments"], "sealed_response_object_id": response["sealed_response_object_id"]})
    publication = None
    if trusted_variant == "publication":
        publication = {"schema_version": "nmrpa.optional_source_publication_record.v1", "store_kind": "response_evidence_store", "publication_record_id": f"synthetic_publication_{source}_{suffix}", "source_kind": source, "request_scope_id": scope["request_scope_id"], "source_asof": response["source_asof"], "published_at": response["available_at"], "issuer_registration_ref": {"id": object_ids["issuer_registration"], "sha256": issuer["record_sha256"]}, "publication_head_ref": {"id": object_ids["recorder_registration"], "sha256": recorder["record_sha256"]}, "publication_anchor_ref": {"id": object_ids["authorization"], "sha256": authorization["record_sha256"]}}
        seal(publication, "publication_record_sha256", "nmrpa.optional_source.publication_record.v1")
    trusted_evidence = {"schema_version": "nmrpa.optional_source_trusted_time.v1", "evidence_type": "trusted_publication" if publication else "first_successful_capture", "source_kind": source, "request_scope_id": scope["request_scope_id"], "source_asof": response["source_asof"], "available_at": response["available_at"], "publication_record_ref_or_null": {"id": publication["publication_record_id"], "sha256": publication["publication_record_sha256"]} if publication else None, "first_success_attempt_ref_or_null": None if publication else {"id": success["attempt_id"], "sha256": success["attempt_sha256"]}, "trusted_time_issuer_ref": {"id": object_ids["issuer_registration"], "sha256": issuer["record_sha256"]}, "trusted_time_head_ref": {"id": object_ids["recorder_registration"], "sha256": recorder["record_sha256"]}, "trusted_time_anchor_ref": {"id": object_ids["authorization"], "sha256": authorization["record_sha256"]}}
    seal(trusted_evidence, "trusted_time_evidence_sha256", "nmrpa.optional_source.trusted_time.v1")
    trusted = append("trusted_time", {**common, "trusted_time_evidence": trusted_evidence, "publication_record_or_null": publication})
    anchor = append("response_anchor", {**common, "anchor_id": object_ids["response_anchor"], "sealed_response_record_sha256": sealed_response["record_sha256"], "inventory_record_sha256": inventory["record_sha256"], "authorization_record_sha256": authorization["record_sha256"], "historical_head_id": object_ids["historical_head"]})
    append("historical_head", {**common, "head_id": object_ids["historical_head"], "state": "committed", "last_authoritative_record_sha256": anchor["record_sha256"], "ordered_record_sha256": [item["record_sha256"] for item in records]})
    head_value = {"schema_version": "nmrpa.optional_source_authoritative_head.v1", "closure_id": closure_id, "source_kind": source, "sequence": str(len(records)), "last_record_sha256": records[-1]["record_sha256"], "history_sha256": trust.digest([item["record_sha256"] for item in records], "nmrpa.optional_source.authoritative_history.v1")}
    seal(head_value, "head_sha256", "nmrpa.optional_source.authoritative_head.v1")
    closure = {"schema_version": "nmrpa.optional_source_authoritative_closure.v1", "closure_id": closure_id, "source_kind": source, "genesis_sha256": genesis, "ordered_records": records, "current_head": head_value}
    seal(closure, "closure_sha256", "nmrpa.optional_source.authoritative_closure.v1")
    record_by_kind = {record["record_kind"]: record for record in records}
    response["capture_attempt_chain_sha256"] = chain_sha
    response["trusted_time_evidence_ref"] = {"id": trusted["object_id"], "sha256": trusted["record_sha256"]}
    for field, kind in (("issuer_registration_ref", "issuer_registration"), ("capture_recorder_registration_ref", "recorder_registration"), ("authorization_ref", "authorization"), ("response_anchor_ref", "response_anchor")):
        response[field] = {"id": record_by_kind[kind]["object_id"], "sha256": record_by_kind[kind]["record_sha256"], "head_sha256": head_value["head_sha256"]}
    for record in records:
        path = root / optional._authoritative_record_path(closure, record)
        path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(trust.canonical_json(record))
    index = root / f"{trust.BASE}/stores/response_evidence_store/{closure_id}.authoritative_closure.json"
    index.write_bytes(trust.canonical_json(closure))
    return closure


def build_intent(desc, head, root, suffix="first", authorization_id=None, returned_count=1, trusted_variant="capture"):
    decision = "2099-06-10"; decision_time = f"{decision}T12:00:00Z"
    grid = [f"2099-06-{day:02d}" for day in range(1, 11)]
    active = [f"TW{index:04d}" for index in range(1, 151)]
    scope = {"schema_version": "nmrpa.optional_source_request_scope.v1", "profile_id": trust.PROFILE, "request_scope_id": f"synthetic_scope_{suffix}", "decision_date": decision, "decision_time": decision_time, "calendar_binding_id": "synthetic_parent_binding", "calendar_binding_sha256": trust.digest({"calendar": suffix}, "test.calendar"), "formal_instruments_binding_id": "synthetic_parent_binding", "formal_instruments_binding_sha256": trust.digest({"instruments": suffix}, "test.instruments"), "trading_date_grid_10": grid, "trading_date_grid_10_sha256": trust.digest(grid, "nmrpa.optional_source.grid_10.v1"), "ordered_active_instruments": active, "active_instrument_set_sha256": trust.digest(active, "nmrpa.optional_source.active_set.v1"), "ordered_source_kinds": ["institutional", "margin"], "requested_source_asof": decision, "cutoff_policy_id": "nmrpa.optional_source.pit_cutoff.asia_taipei.v1"}
    seal(scope, "request_scope_sha256", "nmrpa.optional_source.request_scope.v1")
    components = []
    for source in optional.SOURCE_KINDS:
        returned, absent = active[:returned_count], active[returned_count:]
        result_class = "authoritative_complete_all_rows" if returned_count == 150 else "authoritative_complete_zero_rows" if returned_count == 0 else "authoritative_complete_partial_rows"
        response = {"schema_version": "nmrpa.optional_source_response_evidence.v1", "response_evidence_id": f"synthetic_response_{source}_{suffix}", "source_kind": source, "request_scope_id": scope["request_scope_id"], "request_scope_sha256": scope["request_scope_sha256"], "decision_date": decision, "requested_source_asof": decision, "source_asof": decision, "available_at": f"{decision}T10:00:00Z", "result_class": result_class, "sealed_response_object_id": f"synthetic_object_{source}_{suffix}", "sealed_response_raw_sha256": trust.digest({"raw": source, "suffix": suffix}, "test.raw"), "normalized_inventory_sha256": trust.digest({"inventory": source, "suffix": suffix}, "test.inventory"), "payload_sha256": trust.digest({"payload_metadata": source, "suffix": suffix}, "test.payload_metadata"), "payload_byte_size": "100", "returned_instrument_count": str(returned_count), "ordered_returned_instruments": returned, "returned_instrument_set_sha256": trust.digest(returned, "nmrpa.optional_source.returned_set.v1"), "ordered_absent_instruments": absent, "absent_instrument_set_sha256": trust.digest(absent, "nmrpa.optional_source.absent_set.v1"), "capture_attempt_chain_sha256": trust.digest({"attempts": source, "suffix": suffix}, "test.attempts"), "trusted_time_evidence_ref": simple_ref(f"trusted_time_{source}_{suffix}"), "issuer_registration_ref": ref(f"issuer_{source}_{suffix}"), "capture_recorder_registration_ref": ref(f"recorder_{source}_{suffix}"), "authorization_ref": ref(f"response_auth_{source}_{suffix}"), "response_anchor_ref": ref(f"response_anchor_{source}_{suffix}")}
        closure = build_authoritative_closure(root, source, suffix, scope, response, trusted_variant)
        seal(response, "response_evidence_sha256", "nmrpa.optional_source.response_evidence.v1")
        evidence = []
        for instrument in active:
            common = {"schema_version": "nmrpa.optional_source_instrument_evidence.v1", "source_kind": source, "instrument": instrument, "decision_date": decision, "request_scope_ref": {"id": scope["request_scope_id"], "sha256": scope["request_scope_sha256"]}, "response_evidence_ref": {"id": response["response_evidence_id"], "sha256": response["response_evidence_sha256"]}, "source_asof": decision, "available_at": response["available_at"], "payload_inventory_sha256": response["normalized_inventory_sha256"], "capture_attempt_chain_sha256": response["capture_attempt_chain_sha256"], "trusted_time_ref": response["trusted_time_evidence_ref"], "issuer_ref": response["issuer_registration_ref"], "head_ref": response["capture_recorder_registration_ref"], "anchor_ref": response["response_anchor_ref"]}
            if instrument in returned:
                rows = [build_row(source, day, index) for index, day in enumerate(grid)]
                item = {**common, "evidence_state": "present", "ordered_rows": rows, "row_key_set_sha256": trust.digest([[instrument, day] for day in grid], "nmrpa.optional_source.row_keys.v1"), "normalized_row_set_sha256": trust.digest([row["normalized_row_sha256"] for row in rows], "nmrpa.optional_source.normalized_rows.v1")}
            else:
                item = {**common, "evidence_state": "confirmed_absent", "checked_at": response["available_at"], "absence_reason": "authoritative_complete_scope_no_rows_for_instrument", "returned_instrument_set_sha256": response["returned_instrument_set_sha256"], "absent_instrument_set_sha256": response["absent_instrument_set_sha256"], "sealed_response_raw_sha256": response["sealed_response_raw_sha256"]}
            seal(item, "instrument_evidence_sha256", "nmrpa.optional_source.instrument_evidence.v1")
            evidence.append(item)
        component = {"source_kind": source, "authoritative_closure": closure, "response_evidence": response, "ordered_instrument_evidence": evidence, "component_inventory_sha256": trust.digest([x["instrument_evidence_sha256"] for x in evidence], "nmrpa.optional_source.component_inventory.v1")}
        seal(component, "component_sha256", "nmrpa.optional_source.component.v1"); components.append(component)
    binding_id = f"synthetic_optional_binding_{suffix}"
    auth = {"authorization_id": authorization_id or f"synthetic_optional_auth_{suffix}", "allowed_binding_id": binding_id, "allowed_decision_date": decision, "expected_previous_head_sha256": head["head_sha256"], "max_consumptions": "1", "consumption_count": "0", "terminal": False}
    seal(auth, "authorization_sha256", "nmrpa.optional_source.authorization.synthetic.v1")
    issuer = {"issuer_identity_id": "synthetic_optional_issuer", "issuer_credential_id": "synthetic_optional_credential", "registry_head_sha256": trust.digest({"registry": suffix}, "test.registry")}
    intent = {"artifact_kind": "optional_source_binding_intent", "schema_version": optional.INTENT_SCHEMA_VERSION, "mode": optional.MODE, "transaction_id": f"txn_synthetic_optional_{suffix}", "binding_id": binding_id, "decision_date": decision, "decision_time": decision_time, "descriptor_sha256": desc["descriptor_sha256"], "expected_previous_head": head, "authorization": auth, "five_root_parent_binding_ref": {"binding_id": "synthetic_parent_binding", "binding_record_sha256": trust.digest({"parent": suffix}, "test.parent"), "head_sha256": trust.digest({"parent_head": suffix}, "test.parent_head")}, "request_scope": scope, "ordered_components": components, "issuer": issuer, "signature": {}, "prepared_at": f"{decision}T12:01:00Z", "committed_at": f"{decision}T12:02:00Z"}
    sequence = int(head["sequence"]) + 1
    sequence_text = str(sequence)
    body = {"schema_version": "nmrpa.optional_source_commit_body.v1", "log_id": trust.LOG_ID, "transaction_id": intent["transaction_id"], "sequence": sequence_text, "previous_commit_sha256": None if sequence == 1 else head["commit_sha256"], "event_type": "optional_source_binding_committed", "issued_at": decision_time, "issuer_identity_id": issuer["issuer_identity_id"], "issuer_credential_id": issuer["issuer_credential_id"], "payload": {"binding_record_sha256": "0" * 64, "anchor_sha256": "0" * 64}}
    # Plan's binding and anchor digests are deterministic; derive the signature
    # by first reproducing those two records without touching a substrate.
    provisional = copy.deepcopy(intent); provisional["signature"] = {"algorithm": "ed25519", "credential_id": issuer["issuer_credential_id"], "signed_digest": "0" * 64, "signature_base64": base64.b64encode(bytes(range(64))).decode()}; seal(provisional, "intent_sha256", "nmrpa.optional_source.binding_intent.synthetic.v1")
    # Build the same records as the adapter to obtain the signed body digest.
    scope_ref = {"request_scope_id": scope["request_scope_id"], "request_scope_sha256": scope["request_scope_sha256"]}
    binding = {"schema_version": "nmrpa.optional_source_daily_binding.v1", "profile_id": trust.PROFILE, "binding_id": binding_id, "transaction_id": intent["transaction_id"], "decision_date": decision, "decision_time": decision_time, "five_root_parent_binding_ref": intent["five_root_parent_binding_ref"], "request_scope_ref": scope_ref, "ordered_components": [{"source_kind": c["source_kind"], "response_evidence_ref": {"id": c["response_evidence"]["response_evidence_id"], "sha256": c["response_evidence"]["response_evidence_sha256"]}, "result_class": c["response_evidence"]["result_class"], "source_asof": decision, "available_at": c["response_evidence"]["available_at"], "active_instrument_set_sha256": scope["active_instrument_set_sha256"], "trading_date_grid_10_sha256": scope["trading_date_grid_10_sha256"], "ordered_instrument_evidence_refs": [{"instrument": e["instrument"], "state": e["evidence_state"], "sha256": e["instrument_evidence_sha256"]} for e in c["ordered_instrument_evidence"]], "present_instrument_set_sha256": c["response_evidence"]["returned_instrument_set_sha256"], "confirmed_absent_instrument_set_sha256": c["response_evidence"]["absent_instrument_set_sha256"], "component_inventory_sha256": c["component_inventory_sha256"], "component_sha256": c["component_sha256"]} for c in components], "authorization_ref": {"id": auth["authorization_id"], "sha256": auth["authorization_sha256"]}, "registry_ref": {"id": issuer["issuer_identity_id"], "sha256": issuer["registry_head_sha256"]}, "descriptor_sha256": desc["descriptor_sha256"]}
    binding["binding_record_sha256"] = trust.digest(binding, "nmrpa.optional_source.daily_binding.v1")
    anchor = {"schema_version": "nmrpa.optional_source_binding_anchor.v1", "anchor_id": f"synthetic_anchor_{binding_id}", "binding_record_sha256": binding["binding_record_sha256"], "request_scope_sha256": scope["request_scope_sha256"], "ordered_response_evidence_sha256": [c["response_evidence"]["response_evidence_sha256"] for c in components], "parent_head_sha256": intent["five_root_parent_binding_ref"]["head_sha256"], "committed_at": intent["committed_at"]}
    anchor["anchor_sha256"] = trust.digest(anchor, "nmrpa.optional_source.binding_anchor.v1")
    body["payload"] = {"binding_record_sha256": binding["binding_record_sha256"], "anchor_sha256": anchor["anchor_sha256"]}
    intent["signature"] = {"algorithm": "ed25519", "credential_id": issuer["issuer_credential_id"], "signed_digest": trust.digest(body, "nmrpa.optional_source.commit_body.v1"), "signature_base64": base64.b64encode(bytes(range(64))).decode()}
    seal(intent, "intent_sha256", "nmrpa.optional_source.binding_intent.synthetic.v1")
    return intent


def assert_code(code, callback):
    with pytest.raises(tx_writer.ContractError) as exc: callback()
    assert exc.value.code == code


def validate_intent(intent, desc, root):
    cap = tx_writer.issue_synthetic_test_capability(root.resolve())
    try:
        return optional.validate_intent(intent, desc, desc["descriptor_sha256"], root.resolve(), cap)
    finally:
        tx_writer.close_synthetic_test_capability(cap)


def make_plan(intent, desc, root):
    cap = tx_writer.issue_synthetic_test_capability(root.resolve())
    try:
        return optional.plan(intent, desc, desc["descriptor_sha256"], root.resolve(), cap)
    finally:
        tx_writer.close_synthetic_test_capability(cap)


def reseal_unbacked_reference(intent, component_index, record_kind):
    component = intent["ordered_components"][component_index]
    closure = component["authoritative_closure"]
    records = {record["record_kind"]: record for record in closure["ordered_records"]}
    target = records[record_kind]
    target["object_id"] = f"synthetic_unbacked_{record_kind}_{component_index}"
    identity_fields = {"capture_attempt": "capture_run_id", "sealed_response": "object_id", "inventory": "inventory_id", "issuer_registration": "registration_id", "recorder_registration": "registration_id", "profile_registration": "registration_id", "authorization": "authorization_id", "response_anchor": "anchor_id", "historical_head": "head_id"}
    if record_kind in identity_fields:
        target["payload"][identity_fields[record_kind]] = target["object_id"]
    response = component["response_evidence"]
    response["sealed_response_object_id"] = records["sealed_response"]["object_id"]
    attempts = records["capture_attempt"]["payload"]["ordered_attempts"]
    success = next(item for item in attempts if item["result_class"] == "authoritative_success")
    success["sealed_response_object_id_or_null"] = records["sealed_response"]["object_id"]
    records["sealed_response"]["payload"].update(object_id=records["sealed_response"]["object_id"], inventory_id=records["inventory"]["object_id"], attempt_id=success["attempt_id"])
    records["inventory"]["payload"].update(inventory_id=records["inventory"]["object_id"], sealed_response_object_id=records["sealed_response"]["object_id"])
    records["issuer_registration"]["payload"]["registration_id"] = records["issuer_registration"]["object_id"]
    records["recorder_registration"]["payload"].update(registration_id=records["recorder_registration"]["object_id"], issuer_registration_id=records["issuer_registration"]["object_id"])
    records["profile_registration"]["payload"].update(registration_id=records["profile_registration"]["object_id"], issuer_registration_id=records["issuer_registration"]["object_id"], recorder_registration_id=records["recorder_registration"]["object_id"])
    records["authorization"]["payload"].update(authorization_id=records["authorization"]["object_id"], allowed_sealed_response_object_id=records["sealed_response"]["object_id"], issuer_registration_id=records["issuer_registration"]["object_id"], recorder_registration_id=records["recorder_registration"]["object_id"], profile_registration_id=records["profile_registration"]["object_id"])
    records["response_anchor"]["payload"].update(anchor_id=records["response_anchor"]["object_id"], historical_head_id=records["historical_head"]["object_id"])
    records["historical_head"]["payload"]["head_id"] = records["historical_head"]["object_id"]
    previous = closure["genesis_sha256"]
    ordered = closure["ordered_records"]
    for index, record in enumerate(ordered):
        record["previous_record_sha256"] = previous
        if record["record_kind"] == "profile_registration":
            record["payload"].update(issuer_registration_id=records["issuer_registration"]["object_id"], recorder_registration_id=records["recorder_registration"]["object_id"])
        if record["record_kind"] == "authorization":
            record["payload"]["committed_under_head_sha256"] = records["profile_registration"]["record_sha256"]
        if record["record_kind"] == "capture_attempt":
            for attempt in attempts:
                attempt["capture_run_id"] = record["payload"]["capture_run_id"]
                attempt["issuer_registration_ref"] = {"id": records["issuer_registration"]["object_id"], "sha256": records["issuer_registration"]["record_sha256"]}
                attempt["capture_recorder_head_ref"] = {"id": records["recorder_registration"]["object_id"], "sha256": records["recorder_registration"]["record_sha256"]}
                seal(attempt, "attempt_sha256", "nmrpa.optional_source.capture_attempt.v1")
            record["payload"]["capture_attempt_chain_sha256"] = trust.digest([item["attempt_sha256"] for item in attempts], "nmrpa.optional_source.capture_attempt_chain.v1")
        if record["record_kind"] == "trusted_time":
            evidence = record["payload"]["trusted_time_evidence"]
            evidence["first_success_attempt_ref_or_null"] = {"id": success["attempt_id"], "sha256": success["attempt_sha256"]}
            evidence["trusted_time_issuer_ref"] = {"id": records["issuer_registration"]["object_id"], "sha256": records["issuer_registration"]["record_sha256"]}
            evidence["trusted_time_head_ref"] = {"id": records["recorder_registration"]["object_id"], "sha256": records["recorder_registration"]["record_sha256"]}
            evidence["trusted_time_anchor_ref"] = {"id": records["authorization"]["object_id"], "sha256": records["authorization"]["record_sha256"]}
            seal(evidence, "trusted_time_evidence_sha256", "nmrpa.optional_source.trusted_time.v1")
        if record["record_kind"] == "response_anchor":
            record["payload"].update(sealed_response_record_sha256=records["sealed_response"]["record_sha256"], inventory_record_sha256=records["inventory"]["record_sha256"], authorization_record_sha256=records["authorization"]["record_sha256"])
        if record["record_kind"] == "historical_head":
            record["payload"].update(last_authoritative_record_sha256=records["response_anchor"]["record_sha256"], ordered_record_sha256=[item["record_sha256"] for item in ordered[:index]])
        seal(record, "record_sha256", "nmrpa.optional_source.authoritative_record.v1"); previous = record["record_sha256"]
    head_value = closure["current_head"]
    head_value.update(last_record_sha256=previous, history_sha256=trust.digest([item["record_sha256"] for item in ordered], "nmrpa.optional_source.authoritative_history.v1"))
    seal(head_value, "head_sha256", "nmrpa.optional_source.authoritative_head.v1")
    seal(closure, "closure_sha256", "nmrpa.optional_source.authoritative_closure.v1")
    response["capture_attempt_chain_sha256"] = records["capture_attempt"]["payload"]["capture_attempt_chain_sha256"]
    response["trusted_time_evidence_ref"] = {"id": records["trusted_time"]["object_id"], "sha256": records["trusted_time"]["record_sha256"]}
    for field, kind in (("issuer_registration_ref", "issuer_registration"), ("capture_recorder_registration_ref", "recorder_registration"), ("authorization_ref", "authorization"), ("response_anchor_ref", "response_anchor")):
        response[field] = {"id": records[kind]["object_id"], "sha256": records[kind]["record_sha256"], "head_sha256": head_value["head_sha256"]}
    seal(response, "response_evidence_sha256", "nmrpa.optional_source.response_evidence.v1")
    for item in component["ordered_instrument_evidence"]:
        item["response_evidence_ref"] = {"id": response["response_evidence_id"], "sha256": response["response_evidence_sha256"]}
        item["capture_attempt_chain_sha256"] = response["capture_attempt_chain_sha256"]
        item["trusted_time_ref"] = response["trusted_time_evidence_ref"]
        item["issuer_ref"] = response["issuer_registration_ref"]
        item["head_ref"] = response["capture_recorder_registration_ref"]
        item["anchor_ref"] = response["response_anchor_ref"]
        seal(item, "instrument_evidence_sha256", "nmrpa.optional_source.instrument_evidence.v1")
    component["component_inventory_sha256"] = trust.digest([item["instrument_evidence_sha256"] for item in component["ordered_instrument_evidence"]], "nmrpa.optional_source.component_inventory.v1")
    seal(component, "component_sha256", "nmrpa.optional_source.component.v1")
    seal(intent, "intent_sha256", "nmrpa.optional_source.binding_intent.synthetic.v1")


def test_positive_plan_is_pure_and_schemas_valid(tmp_path):
    desc, head = materialize(tmp_path); intent = build_intent(desc, head, tmp_path)
    before = sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*"))
    assert validate_intent(intent, desc, tmp_path)["active_count"] == 150
    candidate = make_plan(intent, desc, tmp_path)
    assert optional.validate_plan(candidate, desc, desc["descriptor_sha256"])["sequence"] == 1
    assert before == sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*"))
    for schema_path in (INTENT_SCHEMA, PLAN_SCHEMA): Draft202012Validator.check_schema(json.loads(schema_path.read_text()))
    assert list(Draft202012Validator(json.loads(INTENT_SCHEMA.read_text()), format_checker=FormatChecker()).iter_errors(intent)) == []
    intent_schema = json.loads(INTENT_SCHEMA.read_text())
    registry = Registry().with_resource(intent_schema["$id"], Resource.from_contents(intent_schema))
    assert list(Draft202012Validator(json.loads(PLAN_SCHEMA.read_text()), registry=registry, format_checker=FormatChecker()).iter_errors(candidate)) == []


@pytest.mark.parametrize("mutation,code", [
    (lambda x: x["request_scope"]["ordered_active_instruments"].pop(), "NMRPA_TR_H_UNIVERSE"),
    (lambda x: x["request_scope"]["trading_date_grid_10"].pop(), "NMRPA_TR_H_GRID"),
    (lambda x: x["ordered_components"].reverse(), "NMRPA_TR_H_SOURCE"),
    (lambda x: x["ordered_components"][0]["response_evidence"].update(result_class="timeout"), "NMRPA_TR_H_FAILURE"),
    (lambda x: x["ordered_components"][0]["response_evidence"].update(source_asof="2099-06-09"), "NMRPA_TR_H_STALE"),
    (lambda x: x["ordered_components"][0]["response_evidence"].update(available_at="2099-06-10T13:00:00Z"), "NMRPA_TR_H_PIT"),
    (lambda x: x["ordered_components"][0]["ordered_instrument_evidence"][1].update(evidence_state="present"), "NMRPA_TR_H_STATE"),
    (lambda x: x["ordered_components"][0]["ordered_instrument_evidence"][0].update(head_ref=ref("wrong_capture_head")), "NMRPA_TR_H_CROSS_BINDING"),
    (lambda x: x.update(payload_path="/tmp/x"), "NMRPA_TR_H_PAYLOAD_INPUT"),
    (lambda x: x["authorization"].update(max_consumptions=True), "NMRPA_TR_H_SCHEMA"),
])
def test_optional_semantic_mutation_matrix(tmp_path, mutation, code):
    desc, head = materialize(tmp_path); intent = build_intent(desc, head, tmp_path); mutation(intent)
    assert_code(code, lambda: validate_intent(intent, desc, tmp_path))


def test_margin_grid_change_conflict_and_present_cardinality(tmp_path):
    desc, head = materialize(tmp_path); intent = build_intent(desc, head, tmp_path)
    row = intent["ordered_components"][1]["ordered_instrument_evidence"][0]["ordered_rows"][2]
    row["margin_balance_change"] = 999
    seal(row, "normalized_row_sha256", "nmrpa.optional_source.margin.row.v1")
    seal(intent["ordered_components"][1]["ordered_instrument_evidence"][0], "instrument_evidence_sha256", "nmrpa.optional_source.instrument_evidence.v1")
    assert_code("NMRPA_TR_H_CONFLICT", lambda: validate_intent(intent, desc, tmp_path))


def test_commit_replay_one_shot_cas_and_orphan(tmp_path):
    desc, head = materialize(tmp_path); intent = build_intent(desc, head, tmp_path); candidate = make_plan(intent, desc, tmp_path)
    cap = tx_writer.issue_synthetic_test_capability(tmp_path.resolve())
    result = optional.commit(candidate, desc, desc["descriptor_sha256"], tmp_path.resolve(), cap)
    assert result["ok"] and result["payload_bytes_read"] == 0
    assert_code("NMRPA_TR_E_REPLAY", lambda: optional.commit(candidate, desc, desc["descriptor_sha256"], tmp_path.resolve(), cap))
    (tmp_path / f"{optional.LOG_BASE}/journals/orphan.record.json").write_text("{}")
    assert_code("NMRPA_TR_H_ORPHAN", lambda: optional._closure(tmp_path.resolve()))
    tx_writer.close_synthetic_test_capability(cap)


def test_distinct_transaction_reusing_authorization_and_stale_cas_fail(tmp_path):
    desc, head = materialize(tmp_path)
    first_intent = build_intent(desc, head, tmp_path, "auth_first")
    first = make_plan(first_intent, desc, tmp_path)
    cap = tx_writer.issue_synthetic_test_capability(tmp_path.resolve())
    optional.commit(first, desc, desc["descriptor_sha256"], tmp_path.resolve(), cap)
    current = optional._read(tmp_path.resolve(), f"{optional.LOG_BASE}/head.json")
    reused = build_intent(desc, current, tmp_path, "auth_second", first_intent["authorization"]["authorization_id"])
    reused_plan = make_plan(reused, desc, tmp_path)
    assert_code("NMRPA_TR_E_AUTH_REPLAY", lambda: optional.commit(reused_plan, desc, desc["descriptor_sha256"], tmp_path.resolve(), cap))
    stale_plan = make_plan(build_intent(desc, head, tmp_path, "stale_head"), desc, tmp_path)
    assert_code("NMRPA_TR_E_CAS", lambda: optional.commit(stale_plan, desc, desc["descriptor_sha256"], tmp_path.resolve(), cap))
    tx_writer.close_synthetic_test_capability(cap)


def test_sequence_two_full_history_closure(tmp_path):
    desc, head = materialize(tmp_path); cap = tx_writer.issue_synthetic_test_capability(tmp_path.resolve())
    first = make_plan(build_intent(desc, head, tmp_path, "sequence_one"), desc, tmp_path)
    optional.commit(first, desc, desc["descriptor_sha256"], tmp_path.resolve(), cap)
    current = optional._read(tmp_path.resolve(), f"{optional.LOG_BASE}/head.json")
    second = make_plan(build_intent(desc, current, tmp_path, "sequence_two"), desc, tmp_path)
    result = optional.commit(second, desc, desc["descriptor_sha256"], tmp_path.resolve(), cap)
    closure = optional._closure(tmp_path.resolve())
    assert result["sequence"] == 2 and closure["current_head"] == second["new_head"]
    assert closure["transaction_ids"] == {first["transaction_id"], second["transaction_id"]}
    tx_writer.close_synthetic_test_capability(cap)


@pytest.mark.parametrize("step", range(1, 10))
def test_every_commit_stage_rolls_back(tmp_path, step):
    desc, head = materialize(tmp_path); candidate = make_plan(build_intent(desc, head, tmp_path, f"fault{step}"), desc, tmp_path)
    before = {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    cap = tx_writer.issue_synthetic_test_capability(tmp_path.resolve())
    assert_code("NMRPA_TR_E_SYNTHETIC_FAULT", lambda: optional.commit(candidate, desc, desc["descriptor_sha256"], tmp_path.resolve(), cap, synthetic_fail_after_step=step))
    after = {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after
    tx_writer.close_synthetic_test_capability(cap)


def test_exact_python_subclasses_and_schema_native_mutations(tmp_path):
    class Text(str): pass
    desc, head = materialize(tmp_path); intent = build_intent(desc, head, tmp_path); intent["request_scope"]["ordered_active_instruments"][0] = Text("TW0001")
    assert_code("NMRPA_TR_H_PAYLOAD_INPUT", lambda: validate_intent(intent, desc, tmp_path))
    native = build_intent(desc, head, tmp_path, "native"); native["authorization"]["max_consumptions"] = True
    assert list(Draft202012Validator(json.loads(INTENT_SCHEMA.read_text())).iter_errors(native))


@pytest.mark.parametrize("mutate", [
    lambda value: value["journal"].update(sequence=True),
    lambda value: value["signed_record"]["record_body"].update(extra="drift"),
    lambda value: value["response_evidence"]["margin"]["response_evidence"].update(returned_instrument_count=True),
    lambda value: value["binding_record"]["ordered_components"][0]["ordered_instrument_evidence_refs"][0].update(state=True),
])
def test_plan_python_schema_recursive_mutation_parity(tmp_path, mutate):
    desc, head = materialize(tmp_path); candidate = make_plan(build_intent(desc, head, tmp_path), desc, tmp_path); mutate(candidate)
    with pytest.raises(tx_writer.ContractError): optional.validate_plan(candidate, desc, desc["descriptor_sha256"])
    intent_schema = json.loads(INTENT_SCHEMA.read_text()); registry = Registry().with_resource(intent_schema["$id"], Resource.from_contents(intent_schema))
    assert list(Draft202012Validator(json.loads(PLAN_SCHEMA.read_text()), registry=registry).iter_errors(candidate))


def test_historical_component_tamper_is_rejected(tmp_path):
    desc, head = materialize(tmp_path); candidate = make_plan(build_intent(desc, head, tmp_path), desc, tmp_path)
    cap = tx_writer.issue_synthetic_test_capability(tmp_path.resolve()); optional.commit(candidate, desc, desc["descriptor_sha256"], tmp_path.resolve(), cap)
    response_path = tmp_path / candidate["paths"]["response_evidence"]
    stored = json.loads(response_path.read_text()); stored["margin"]["ordered_instrument_evidence"][0]["ordered_rows"][0]["margin_balance"] += 1
    response_path.write_bytes(trust.canonical_json(stored))
    assert_code("NMRPA_TR_H_DIGEST", lambda: optional._closure(tmp_path.resolve()))
    tx_writer.close_synthetic_test_capability(cap)


def test_optional_rollback_failure_terminal_taints_capability_root(tmp_path, monkeypatch):
    desc, head = materialize(tmp_path); candidate = make_plan(build_intent(desc, head, tmp_path, "terminal_taint"), desc, tmp_path)
    cap = tx_writer.issue_synthetic_test_capability(tmp_path.resolve()); original = tx_writer._atomic_json
    def fail_history_restore(*args, **kwargs):
        if args[1] == candidate["paths"]["history"] and kwargs.get("state") is None:
            raise OSError("synthetic restore failure")
        return original(*args, **kwargs)
    monkeypatch.setattr(tx_writer, "_atomic_json", fail_history_restore)
    assert_code("NMRPA_TR_E_ROLLBACK_FAILURE", lambda: optional.commit(candidate, desc, desc["descriptor_sha256"], tmp_path.resolve(), cap, synthetic_fail_after_step=8))
    assert_code("NMRPA_TR_E_ROLLBACK_FAILURE", lambda: optional.commit(candidate, desc, desc["descriptor_sha256"], tmp_path.resolve(), cap))
    tx_writer.close_synthetic_test_capability(cap)


def test_actual_roots_and_payload_surfaces_rejected(tmp_path):
    desc, head = materialize(tmp_path); candidate = make_plan(build_intent(desc, head, tmp_path), desc, tmp_path)
    assert_code("NMRPA_TR_E_ACTUAL_ROOT_FORBIDDEN", lambda: tx_writer.issue_synthetic_test_capability(ROOT))
    source = (SCRIPTS / "tw_policy_nmrpa3_optional_source_binding.py").read_text()
    assert "open(" not in source and "requests" not in source and "urllib" not in source
    assert all(name not in str(candidate) for name in ("payload_path", "payload_bytes", "file_handle", "checkpoint", "cache", "latest"))


@pytest.mark.parametrize("record_kind", optional.AUTHORITATIVE_RECORD_KINDS)
def test_each_internally_resealed_but_unbacked_reference_is_rejected(tmp_path, record_kind):
    desc, head = materialize(tmp_path)
    intent = build_intent(desc, head, tmp_path, f"unbacked_{record_kind}")
    reseal_unbacked_reference(intent, 0, record_kind)
    assert_code("NMRPA_TR_H_UNBACKED_REFERENCE", lambda: validate_intent(intent, desc, tmp_path))


@pytest.mark.parametrize("returned_count,expected_present,expected_absent", [(150, 150, 0), (1, 1, 149), (0, 0, 150)])
def test_positive_present_and_confirmed_absent_authoritative_closure(tmp_path, returned_count, expected_present, expected_absent):
    desc, head = materialize(tmp_path)
    intent = build_intent(desc, head, tmp_path, f"closure_{returned_count}", returned_count=returned_count)
    assert validate_intent(intent, desc, tmp_path)["active_count"] == 150
    for component in intent["ordered_components"]:
        states = [item["evidence_state"] for item in component["ordered_instrument_evidence"]]
        assert states.count("present") == expected_present
        assert states.count("confirmed_absent") == expected_absent
        assert len(component["authoritative_closure"]["ordered_records"]) == 10


@pytest.mark.parametrize("mutation,code", [
    (lambda record: record.update(store_kind="anchor_ledger"), "NMRPA_TR_H_SCHEMA"),
    (lambda record: record.update(record_kind="inventory"), "NMRPA_TR_H_SCHEMA"),
    (lambda record: record.update(sequence="7"), "NMRPA_TR_H_HISTORY"),
    (lambda record: record.update(previous_record_sha256="f" * 64), "NMRPA_TR_H_HISTORY"),
    (lambda record: record.update(record_sha256="f" * 64), "NMRPA_TR_H_DIGEST"),
])
def test_wrong_store_kind_sequence_history_and_digest_fail_closed(tmp_path, mutation, code):
    desc, head = materialize(tmp_path); intent = build_intent(desc, head, tmp_path, f"bad_{code.lower()}")
    mutation(intent["ordered_components"][0]["authoritative_closure"]["ordered_records"][0])
    assert_code(code, lambda: validate_intent(intent, desc, tmp_path))


def test_authoritative_store_orphan_is_rejected(tmp_path):
    desc, head = materialize(tmp_path); build_intent(desc, head, tmp_path, "orphan_authoritative")
    orphan = tmp_path / f"{trust.BASE}/stores/capture_attempt_store/orphan.json"
    orphan.write_text("{}\n")
    assert_code("NMRPA_TR_H_ORPHAN", lambda: optional._closure(tmp_path.resolve()))


@pytest.mark.parametrize("mutation", [
    lambda value: value["ordered_components"][0]["authoritative_closure"]["ordered_records"][3]["payload"].update(max_consumptions=1.0),
    lambda value: value["ordered_components"][0]["authoritative_closure"]["ordered_records"][0]["payload"].update(extra_field="forbidden"),
])
def test_authoritative_recursive_python_schema_exact_type_parity(tmp_path, mutation):
    desc, head = materialize(tmp_path); intent = build_intent(desc, head, tmp_path, "authoritative_parity")
    mutation(intent)
    with pytest.raises(tx_writer.ContractError):
        validate_intent(intent, desc, tmp_path)
    schema = json.loads(INTENT_SCHEMA.read_text())
    assert list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(intent))


@pytest.mark.parametrize("field,value,code", [
    ("result_class", "failure", "NMRPA_TR_H_ATTEMPT"),
    ("result_class", "not_run", "NMRPA_TR_H_ATTEMPT"),
    ("completed_at", "2099-06-10T13:00:00Z", "NMRPA_TR_H_ATTEMPT"),
])
def test_attempt_failure_not_run_scope_incomplete_and_late_rejected(tmp_path, field, value, code):
    desc, head = materialize(tmp_path); intent = build_intent(desc, head, tmp_path, f"attempt_{field}")
    component = intent["ordered_components"][0]
    records = {record["record_kind"]: record for record in component["authoritative_closure"]["ordered_records"]}
    records["capture_attempt"]["payload"]["ordered_attempts"][-1][field] = value
    assert_code(code, lambda: optional._validate_authoritative_payload("capture_attempt", records["capture_attempt"]["payload"], component["response_evidence"], intent["request_scope"], "institutional", optional._time(intent["decision_time"], "decision_time"), records))


def test_trusted_time_stale_conflict_and_publication_variant(tmp_path):
    desc, head = materialize(tmp_path); intent = build_intent(desc, head, tmp_path, "trusted_time_variants")
    component = intent["ordered_components"][0]
    records = {record["record_kind"]: record for record in component["authoritative_closure"]["ordered_records"]}
    payload = records["trusted_time"]["payload"]
    payload["trusted_time_evidence"]["source_asof"] = "2099-06-09"
    assert_code("NMRPA_TR_H_TRUSTED_TIME", lambda: optional._validate_authoritative_payload("trusted_time", payload, component["response_evidence"], intent["request_scope"], "institutional", optional._time(intent["decision_time"], "decision_time"), records))
    payload["trusted_time_evidence"]["source_asof"] = "2099-06-10"


def test_publication_variant_has_real_mutually_exclusive_backing(tmp_path):
    desc, head = materialize(tmp_path)
    intent = build_intent(desc, head, tmp_path, "publication_backed", trusted_variant="publication")
    assert validate_intent(intent, desc, tmp_path)["active_count"] == 150
    for component in intent["ordered_components"]:
        trusted = {record["record_kind"]: record for record in component["authoritative_closure"]["ordered_records"]}["trusted_time"]["payload"]
        evidence = trusted["trusted_time_evidence"]
        assert evidence["evidence_type"] == "trusted_publication"
        assert evidence["publication_record_ref_or_null"]["sha256"] == trusted["publication_record_or_null"]["publication_record_sha256"]
        assert evidence["first_success_attempt_ref_or_null"] is None


def append_post_success_attempt(payload):
    attempt = copy.deepcopy(payload["ordered_attempts"][0])
    attempt.update(attempt_id=f"{attempt['attempt_id']}_post_success", sequence="4", started_at="2099-06-10T10:01:00Z", completed_at="2099-06-10T10:02:00Z")
    seal(attempt, "attempt_sha256", "nmrpa.optional_source.capture_attempt.v1")
    payload["ordered_attempts"].append(attempt)


@pytest.mark.parametrize("mutation", [
    lambda p: p["ordered_attempts"][1].update(sequence="1"),
    lambda p: p["ordered_attempts"][1].update(sequence="4"),
    lambda p: p["ordered_attempts"].reverse(),
    lambda p: p["ordered_attempts"][1].update(result_class="authoritative_success", sealed_response_object_id_or_null="synthetic_duplicate", sealed_response_raw_sha256_or_null="f" * 64),
    lambda p: p["ordered_attempts"][0].update(attempt_sha256="f" * 64),
    append_post_success_attempt,
])
def test_ordered_attempt_chain_gap_duplicate_reorder_second_success_and_reseal_rejected(tmp_path, mutation):
    desc, head = materialize(tmp_path); intent = build_intent(desc, head, tmp_path, "attempt_chain_negative")
    component = intent["ordered_components"][0]
    records = {record["record_kind"]: record for record in component["authoritative_closure"]["ordered_records"]}
    mutation(records["capture_attempt"]["payload"])
    with pytest.raises(tx_writer.ContractError):
        optional._validate_authoritative_payload("capture_attempt", records["capture_attempt"]["payload"], component["response_evidence"], intent["request_scope"], "institutional", optional._time(intent["decision_time"], "decision_time"), records)


@pytest.mark.parametrize("mutation", [
    lambda p: p["trusted_time_evidence"].update(publication_record_ref_or_null=None),
    lambda p: p["trusted_time_evidence"].update(first_success_attempt_ref_or_null={"id":"synthetic_wrong","sha256":"f" * 64}),
    lambda p: p["publication_record_or_null"].update(store_kind="capture_attempt_store"),
    lambda p: p["publication_record_or_null"].update(published_at="2099-06-10T10:01:00Z"),
    lambda p: p["publication_record_or_null"].update(publication_head_ref={"id":"synthetic_wrong","sha256":"f" * 64}),
    lambda p: p["publication_record_or_null"].update(issuer_registration_ref={"id":"synthetic_wrong","sha256":"f" * 64}),
    lambda p: p["publication_record_or_null"].update(publication_anchor_ref={"id":"synthetic_wrong","sha256":"f" * 64}),
])
def test_publication_wrong_backing_kind_time_head_issuer_anchor_rejected(tmp_path, mutation):
    desc, head = materialize(tmp_path); intent = build_intent(desc, head, tmp_path, "publication_negative", trusted_variant="publication")
    component = intent["ordered_components"][0]
    records = {record["record_kind"]: record for record in component["authoritative_closure"]["ordered_records"]}
    mutation(records["trusted_time"]["payload"])
    with pytest.raises(tx_writer.ContractError):
        optional._validate_authoritative_payload("trusted_time", records["trusted_time"]["payload"], component["response_evidence"], intent["request_scope"], "institutional", optional._time(intent["decision_time"], "decision_time"), records)


@pytest.mark.parametrize("mutation", [
    lambda e: e.update(publication_record_ref_or_null={"id":"synthetic_both","sha256":"f" * 64}),
    lambda e: e.update(first_success_attempt_ref_or_null=None),
    lambda e: e.update(first_success_attempt_ref_or_null={"id":"synthetic_not_first","sha256":"f" * 64}),
])
def test_first_success_union_both_empty_or_wrong_attempt_rejected(tmp_path, mutation):
    desc, head = materialize(tmp_path); intent = build_intent(desc, head, tmp_path, "first_success_negative")
    component = intent["ordered_components"][0]
    records = {record["record_kind"]: record for record in component["authoritative_closure"]["ordered_records"]}
    mutation(records["trusted_time"]["payload"]["trusted_time_evidence"])
    assert_code("NMRPA_TR_H_TRUSTED_TIME", lambda: optional._validate_authoritative_payload("trusted_time", records["trusted_time"]["payload"], component["response_evidence"], intent["request_scope"], "institutional", optional._time(intent["decision_time"], "decision_time"), records))


@pytest.mark.parametrize("kind,field", [
    ("issuer_registration", "committed_at"),
    ("recorder_registration", "committed_at"),
    ("profile_registration", "committed_at"),
    ("authorization", "committed_at"),
])
def test_registration_profile_and_authorization_after_capture_rejected(tmp_path, kind, field):
    desc, head = materialize(tmp_path); intent = build_intent(desc, head, tmp_path, f"late_{kind}")
    component = intent["ordered_components"][0]
    records = {record["record_kind"]: record for record in component["authoritative_closure"]["ordered_records"]}
    records[kind]["payload"][field] = "2099-06-10T10:01:00Z"
    assert_code("NMRPA_TR_H_AUTH" if kind == "authorization" else "NMRPA_TR_H_REGISTRATION", lambda: optional._validate_authoritative_payload(kind, records[kind]["payload"], component["response_evidence"], intent["request_scope"], "institutional", optional._time(intent["decision_time"], "decision_time"), records) if kind != "authorization" else optional._validate_authoritative_payload("capture_attempt", records["capture_attempt"]["payload"], component["response_evidence"], intent["request_scope"], "institutional", optional._time(intent["decision_time"], "decision_time"), records))


@pytest.mark.parametrize("store", sorted(set(optional.AUTHORITATIVE_STORE_BY_KIND.values())))
def test_validate_intent_and_plan_reject_each_authoritative_store_orphan_without_write(tmp_path, store):
    desc, head = materialize(tmp_path); intent = build_intent(desc, head, tmp_path, f"orphan_{store}")
    orphan = tmp_path / f"{trust.BASE}/stores/{store}/unreferenced.json"
    orphan.write_text("{}\n")
    before = {str(path.relative_to(tmp_path)): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert_code("NMRPA_TR_H_ORPHAN", lambda: validate_intent(intent, desc, tmp_path))
    assert_code("NMRPA_TR_H_ORPHAN", lambda: make_plan(intent, desc, tmp_path))
    after = {str(path.relative_to(tmp_path)): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert before == after


@pytest.mark.parametrize("path", [
    ("authorization", "max_consumptions"),
    ("authorization", "consumption_count"),
    ("attempt", "sequence"),
    ("attempt", "http_status_or_null"),
])
def test_json_integral_float_rejected_by_python_and_schema(path, tmp_path):
    desc, head = materialize(tmp_path); intent = build_intent(desc, head, tmp_path, f"float_{path[0]}_{path[1]}")
    records = {record["record_kind"]: record for record in intent["ordered_components"][0]["authoritative_closure"]["ordered_records"]}
    target = records["authorization"]["payload"] if path[0] == "authorization" else records["capture_attempt"]["payload"]["ordered_attempts"][-1]
    target[path[1]] = 1.0 if path[1] != "http_status_or_null" else 200.0
    with pytest.raises(tx_writer.ContractError):
        validate_intent(intent, desc, tmp_path)
    assert list(Draft202012Validator(json.loads(INTENT_SCHEMA.read_text()), format_checker=FormatChecker()).iter_errors(intent))


@pytest.mark.parametrize("mutate", [
    lambda value: value["authorization"].update(max_consumptions=1.0),
    lambda value: value["authorization"].update(consumption_count=0.0),
    lambda value: value["expected_previous_head"].update(sequence=0.0),
    lambda value: value["ordered_components"][0]["response_evidence"].update(payload_byte_size=100.0),
    lambda value: value["ordered_components"][0]["response_evidence"].update(returned_instrument_count=1.0),
    lambda value: value["ordered_components"][0]["authoritative_closure"]["ordered_records"][0].update(sequence=1.0),
    lambda value: value["ordered_components"][0]["authoritative_closure"]["current_head"].update(sequence=10.0),
])
def test_all_intent_integral_float_surfaces_have_python_schema_parity(tmp_path, mutate):
    desc, head = materialize(tmp_path); intent = build_intent(desc, head, tmp_path, "intent_float_matrix")
    mutate(intent)
    with pytest.raises(tx_writer.ContractError):
        validate_intent(intent, desc, tmp_path)
    assert list(Draft202012Validator(json.loads(INTENT_SCHEMA.read_text()), format_checker=FormatChecker()).iter_errors(intent))


@pytest.mark.parametrize("mutate", [
    lambda value: value["expected_previous_head"].update(sequence=0.0),
    lambda value: value["signed_record"]["record_body"].update(sequence=1.0),
    lambda value: value["journal"].update(sequence=1.0),
    lambda value: value["commit_marker"].update(sequence=1.0),
    lambda value: value["new_head"].update(sequence=1.0),
])
def test_all_plan_integral_float_surfaces_have_python_schema_parity(tmp_path, mutate):
    desc, head = materialize(tmp_path); candidate = make_plan(build_intent(desc, head, tmp_path, "plan_float_matrix"), desc, tmp_path)
    mutate(candidate)
    with pytest.raises(tx_writer.ContractError):
        optional.validate_plan(candidate, desc, desc["descriptor_sha256"])
    intent_schema = json.loads(INTENT_SCHEMA.read_text())
    registry = Registry().with_resource(intent_schema["$id"], Resource.from_contents(intent_schema))
    assert list(Draft202012Validator(json.loads(PLAN_SCHEMA.read_text()), registry=registry, format_checker=FormatChecker()).iter_errors(candidate))
