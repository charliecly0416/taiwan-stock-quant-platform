from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "scripts/tw_policy_nmrpa3_source_adapter.py"
SPEC = importlib.util.spec_from_file_location("tw_policy_nmrpa3_source_adapter", MODULE)
assert SPEC and SPEC.loader
nmrpa3 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = nmrpa3
SPEC.loader.exec_module(nmrpa3)
CONFIG = ROOT / "tests/fixtures/nmrpa3/synthetic_source_config.json"


def fixture():
    return nmrpa3.build_synthetic_fixture(json.loads(CONFIG.read_text()))


def assert_code(code, fn):
    with pytest.raises(nmrpa3.ContractError) as exc:
        fn()
    assert exc.value.code == code


def reseal(obj, field):
    obj[field] = nmrpa3.checksum_without(obj, field)


def with_objects(store, objects):
    return nmrpa3.InjectedObjectStore(objects, store.pinned_trust)


def replace_member_bytes(package, store, root_kind, role, value):
    root = next(root for root in package["source_roots"] if root["root_kind"] == root_kind)
    member = next(member for member in root["ordered_members"] if member["file_role"] == role)
    raw = nmrpa3.canonical_json(value)
    objects = dict(store.objects)
    objects[member["object_token"]] = raw
    member["byte_size"] = len(raw)
    member["bytes_sha256"] = nmrpa3.sha256_bytes(raw)
    member["ordered_objects"][0]["canonical_object_sha256"] = nmrpa3.digest(value)
    member["object_index_sha256"] = nmrpa3.digest({
        "schema_version": "nmrpa.object_index.v1",
        "member_id": member["member_id"],
        "ordered_objects": member["ordered_objects"],
    })
    reseal(root, "root_inventory_sha256")
    return with_objects(store, objects)


ROTATION_CASES = (
    ("trusted_service_registration_log", "service_credential_rotated", "service"),
    ("publication_authority_registration_log", "authority_credential_rotated", "authority"),
    ("capture_recorder_registration_log", "recorder_credential_rotated", "recorder"),
)


def registration_rotation_fixture(logical_name, event, registration_role, mutate=None):
    package, store = fixture()
    credential_log = package["governance_logs"]["credential_registry_log"]
    old_credential = credential_log["transactions"][0]["record"]["body"]["payload"]
    new_key = bytes(reversed(range(32)))
    new_credential_state = copy.deepcopy(old_credential["state"])
    new_credential_state.update({
        "credential_id": "credential_trust_registry_rotation",
        "public_key_base64": nmrpa3.base64.b64encode(new_key).decode(),
        "public_key_fingerprint_sha256": nmrpa3.sha256_bytes(new_key),
    })
    new_credential = nmrpa3._transition(
        "credential_registered", "credential_trust_registry_rotation",
        new_credential_state, 2,
    )
    credential_log = nmrpa3._log(
        "credential_registry_log", [old_credential, new_credential],
    )
    package["governance_logs"]["credential_registry_log"] = credential_log

    registration_log = package["governance_logs"][logical_name]
    registered = registration_log["transactions"][0]["record"]["body"]["payload"]
    rotation_state = {
        "principal_id": registered["state"]["principal_id"],
        "identity_id": registered["state"]["identity_id"],
        "credential_id": new_credential["subject_id"],
        "scope": copy.deepcopy(registered["state"]["scope"]),
        "prior_registration_ref": nmrpa3._registration_ref(registered, 1, registration_role),
        "prior_credential_ref": nmrpa3._credential_ref(old_credential, 1),
        "new_credential_ref": nmrpa3._credential_ref(new_credential, 2),
    }
    if mutate is not None:
        mutate(rotation_state)
    rotated = nmrpa3._transition(event, registered["subject_id"], rotation_state, 2)
    package["governance_logs"][logical_name] = nmrpa3._log(
        logical_name, [registered, rotated],
    )

    package["bootstrap"]["fixed_log_heads"] = {
        name: copy.deepcopy(log["current_head"])
        for name, log in package["governance_logs"].items()
    }
    reseal(package["bootstrap"], "bootstrap_sha256")
    pins = nmrpa3.PinnedTrust(
        bootstrap_sha256=package["bootstrap"]["bootstrap_sha256"],
        fixed_log_heads=copy.deepcopy(package["bootstrap"]["fixed_log_heads"]),
        contract_digests=store.pinned_trust.contract_digests,
        authorization_sha256=store.pinned_trust.authorization_sha256,
        anchor_sha256=store.pinned_trust.anchor_sha256,
    )
    return package, nmrpa3.InjectedObjectStore(dict(store.objects), pins)


def test_synthetic_positive_package_and_boundary():
    package, store = fixture()
    result = nmrpa3.validate_package(package, store)
    assert result["ok"] is True
    assert result["root_count"] == 5
    assert result["formal_active_count"] == 2
    assert result["no_run"] and result["no_candidate"] and result["no_metric"]
    assert package["runtime_overrides"] == {}


def test_first_success_capture_positive_and_attempt_bytes_binding():
    config = json.loads(CONFIG.read_text()); config["fixture_id"] = "synthetic_capture_v1"; config["evidence_mode"] = "first_successful_capture"
    package, store = nmrpa3.build_synthetic_fixture(config)
    assert nmrpa3.validate_package(package, store)["ok"] is True
    package["pit_bindings"][0]["ordered_attempts"][0]["http_status"] = 201
    reseal(package["pit_bindings"][0], "evidence_sha256")
    assert_code("NMRPA_E_FIRST_SUCCESS_ORDER", lambda: nmrpa3.validate_package(package, store))


def test_exact_top_level_and_no_runtime_override():
    package, store = fixture()
    package["unknown"] = True
    assert_code("NMRPA_E_SCHEMA", lambda: nmrpa3.validate_package(package, store))
    package, store = fixture()
    package["runtime_overrides"] = {"root_path": "/tmp/fake"}
    assert_code("NMRPA_E_RUNTIME_OVERRIDE", lambda: nmrpa3.validate_package(package, store))


def test_real_date_and_default_date_are_not_available():
    config = json.loads(CONFIG.read_text())
    config["target_asof"] = "2026-08-22"
    assert_code("NMRPA_E_REAL_INPUT", lambda: nmrpa3.build_synthetic_fixture(config))
    config = json.loads(CONFIG.read_text()); del config["target_asof"]
    assert_code("NMRPA_E_SCHEMA", lambda: nmrpa3.build_synthetic_fixture(config))


def test_store_is_bytes_only_and_has_no_path_fallback(tmp_path):
    assert_code("NMRPA_E_REAL_INPUT", lambda: nmrpa3.InjectedObjectStore({"/tmp/data.json": b"{}"}))
    assert not any(name in nmrpa3.__dict__ for name in ("requests", "psycopg", "sqlalchemy", "DEFAULT_ROOT", "LATEST"))


@pytest.mark.parametrize("field", ["base_id", "root_id", "locator_token"])
def test_trusted_locator_cannot_be_replaced_even_with_resigned_inventory(field):
    package, store = fixture()
    package["source_roots"][0][field] = "SYNTHETIC_OVERRIDE"
    reseal(package["source_roots"][0], "root_inventory_sha256")
    assert_code("NMRPA_E_TRUSTED_BASE_MISMATCH", lambda: nmrpa3.validate_package(package, store))


def test_inventory_bytes_and_unreferenced_object_fail_closed():
    package, store = fixture()
    objects = dict(store.objects)
    token = next(iter(objects)); objects[token] += b" "
    assert_code("NMRPA_E_INVENTORY_BYTES", lambda: nmrpa3.validate_package(package, with_objects(store, objects)))
    package, store = fixture(); objects = dict(store.objects); objects["SYNTHETIC_OBJECT_EXTRA"] = b"{}"
    assert_code("NMRPA_E_INVENTORY", lambda: nmrpa3.validate_package(package, with_objects(store, objects)))


def test_object_selector_and_cross_root_alias_fail_closed():
    package, store = fixture()
    package["source_roots"][0]["ordered_members"][0]["ordered_objects"][0]["selector"] = {"selector_type": "json_pointer", "json_pointer": "/x"}
    assert_code("NMRPA_E_OBJECT_SELECTOR", lambda: nmrpa3.validate_package(package, store))
    package, store = fixture()
    package["source_roots"][1]["ordered_members"][0]["object_token"] = package["source_roots"][0]["ordered_members"][0]["object_token"]
    assert_code("NMRPA_E_ROOT_ALIAS", lambda: nmrpa3.validate_package(package, store))


def test_pit_evidence_type_asof_time_and_coverage():
    package, store = fixture(); package["pit_bindings"][0]["evidence_type"] = "not_run"
    assert_code("NMRPA_E_EVIDENCE_TYPE", lambda: nmrpa3.validate_package(package, store))
    package, store = fixture(); package["pit_bindings"][0]["published_source_asof"] = "2099-06-27"
    reseal(package["pit_bindings"][0], "evidence_sha256")
    assert_code("NMRPA_E_SOURCE_ASOF", lambda: nmrpa3.validate_package(package, store))
    package, store = fixture(); package["pit_bindings"][0]["available_at"] = "2099-07-01T00:00:00Z"
    package["pit_bindings"][0]["published_at"] = "2099-07-01T00:00:00Z"; reseal(package["pit_bindings"][0], "evidence_sha256")
    assert_code("NMRPA_E_PIT", lambda: nmrpa3.validate_package(package, store))
    package, store = fixture(); package["pit_bindings"][0]["referenced_row_keys"].pop()
    reseal(package["pit_bindings"][0], "evidence_sha256")
    assert_code("NMRPA_E_EVIDENCE_SHARING", lambda: nmrpa3.validate_package(package, store))


def test_publication_requires_distinct_bound_members():
    package, store = fixture()
    evidence = package["pit_bindings"][0]
    evidence["publication_record_ref"] = copy.deepcopy(evidence["publication_payload_ref"])
    reseal(evidence, "evidence_sha256")
    assert_code("NMRPA_E_PUBLICATION_CARDINALITY", lambda: nmrpa3.validate_package(package, store))


def test_calendar_grid_and_model_price_cross_section():
    package, store = fixture(); package["calendar"]["ordered_dates"].pop(0)
    assert_code("NMRPA_E_CALENDAR", lambda: nmrpa3.validate_cross_section(package))
    package, store = fixture(); package["modela_rows"].pop()
    assert_code("NMRPA_E_MISSING_MODELA", lambda: nmrpa3.validate_cross_section(package))
    package, store = fixture(); package["price_rows"] = [r for r in package["price_rows"] if not (r["instrument"] == "SYNTHETIC_SYMBOL_B" and r["date"] == package["target_asof"])]
    assert_code("NMRPA_E_MISSING_PRICE", lambda: nmrpa3.validate_cross_section(package))
    package, store = fixture(); package["price_rows"].pop(20)
    assert_code("NMRPA_E_HISTORY_GRID", lambda: nmrpa3.validate_cross_section(package))


def test_price_adjustment_volume_and_variant_math():
    package, store = fixture(); package["price_rows"][0]["close"] += 1
    reseal(package["price_rows"][0], "normalized_row_sha256")
    assert_code("NMRPA_E_PRICE_MATH", lambda: nmrpa3.validate_price_row(package["price_rows"][0]))
    package, store = fixture(); package["price_rows"][0]["volume"] = 10
    reseal(package["price_rows"][0], "normalized_row_sha256")
    assert_code("NMRPA_E_PRICE_MATH", lambda: nmrpa3.validate_price_row(package["price_rows"][0]))
    package, store = fixture(); row = package["price_rows"][0]; row["row_state"] = "unknown"; reseal(row, "normalized_row_sha256")
    assert_code("NMRPA_E_PRICE_VARIANT", lambda: nmrpa3.validate_price_row(row))


def test_fixed_log_identity_and_event_role_matrix_ek_lg():
    package, store = fixture(); log = package["governance_logs"]["credential_registry_log"]
    log["log_id"] = "nmrpa.identity_registry.v1"
    assert_code("NMRPA_E_LOG_IDENTITY", lambda: nmrpa3.validate_package(package, store))  # LG02
    package, store = fixture(); log = package["governance_logs"]["credential_registry_log"]
    log["transactions"][0]["record"]["body"]["event_type"] = "credential_rotate_alias"
    assert_code("NMRPA_E_EVENT_ROLE", lambda: nmrpa3.validate_package(package, store))  # EK01
    package, store = fixture(); log = package["governance_logs"]["identity_registry_log"]
    log["transactions"][0]["record"]["body"]["event_type"] = "credential_rotated"
    assert_code("NMRPA_E_EVENT_ROLE", lambda: nmrpa3.validate_package(package, store))  # EK02
    package, store = fixture(); log = package["governance_logs"]["credential_registry_log"]
    log["transactions"][0]["record"]["body"]["payload"]["transition_type"] = "credential_revoked"
    assert_code("NMRPA_E_EVENT_CROSS_BINDING", lambda: nmrpa3.validate_package(package, store))  # EK03


def test_principal_uniqueness_excludes_display_name_and_does_not_merge_different_keys():
    package, store = fixture(); log = package["governance_logs"]["principal_registry_log"]
    original = log["transactions"][0]["record"]["body"]["payload"]
    duplicate = copy.deepcopy(original); duplicate["transition_id"] = "transition_other_2"; duplicate["subject_id"] = "principal_other"; duplicate["state"]["canonical_identity"]["canonical_display_name"] = "Alias"; reseal(duplicate, "transition_sha256")
    log2 = nmrpa3._log("principal_registry_log", [original, duplicate]); package["governance_logs"]["principal_registry_log"] = log2
    package["bootstrap"]["fixed_log_heads"]["principal_registry_log"] = log2["current_head"]; reseal(package["bootstrap"], "bootstrap_sha256")
    assert_code("NMRPA_E_PRINCIPAL_ALIAS", lambda: nmrpa3.validate_package(package, store))  # PR01/2
    package, store = fixture(); log = package["governance_logs"]["principal_registry_log"]; original = log["transactions"][0]["record"]["body"]["payload"]
    other = copy.deepcopy(original); other["transition_id"] = "transition_other_2"; other["subject_id"] = "principal_other"; other["state"]["canonical_identity"]["canonical_subject_id"] = "nmrpa.synthetic.other"; reseal(other, "transition_sha256")
    nmrpa3.validate_log("principal_registry_log", nmrpa3._log("principal_registry_log", [original, other]))  # PR03: must not merge


def test_rotation_and_revoke_require_committed_genesis():
    key = "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8="
    state = {"owner_principal_id": "p", "owner_identity_id": "i", "owner_role": "trust_registry_issuer", "credential_id": "c2", "public_key_base64": key, "public_key_fingerprint_sha256": "630dcd2966c4336691125448bbb25b4ff412a49c732db2c8abc1b8581bd710dd", "prior_credential_id": "c1"}
    orphan = nmrpa3._transition("credential_rotated", "c2", state, 1)
    assert_code("NMRPA_E_CREDENTIAL_STATE", lambda: nmrpa3.validate_log("credential_registry_log", nmrpa3._log("credential_registry_log", [orphan])))
    registered_state = dict(state); registered_state.pop("prior_credential_id"); registered_state["credential_id"] = "c1"
    registered = nmrpa3._transition("credential_registered", "c1", registered_state, 1)
    rotated = nmrpa3._transition("credential_rotated", "c2", state, 2)
    nmrpa3.validate_log("credential_registry_log", nmrpa3._log("credential_registry_log", [registered, rotated]))

    principal_state = {"canonical_identity": {"identity_namespace": "project_service", "jurisdiction": "ZZ", "canonical_subject_id": "x", "canonical_display_name": "X"}}
    principal = nmrpa3._transition("principal_registered", "p", principal_state, 1)
    revoked = nmrpa3._transition("principal_revoked", "p", {"prior_transition_id": principal["transition_id"], **principal_state, "revocation_reason": "synthetic retirement"}, 2)
    nmrpa3.validate_log("principal_registry_log", nmrpa3._log("principal_registry_log", [principal, revoked]))


@pytest.mark.parametrize("logical_name,event,registration_role", ROTATION_CASES)
def test_registration_credential_rotation_exact_variants_accept_committed_prior(
    logical_name, event, registration_role,
):
    package, store = registration_rotation_fixture(logical_name, event, registration_role)
    assert nmrpa3.validate_package(package, store)["ok"] is True


@pytest.mark.parametrize("logical_name,event,registration_role", ROTATION_CASES)
def test_registration_credential_rotation_requires_exact_prior_refs(
    logical_name, event, registration_role,
):
    package, store = registration_rotation_fixture(
        logical_name, event, registration_role,
        lambda state: state.pop("prior_registration_ref"),
    )
    assert_code("NMRPA_E_SCHEMA", lambda: nmrpa3.validate_package(package, store))


@pytest.mark.parametrize(
    "logical_name,event,registration_role,mutation",
    (
        (*ROTATION_CASES[0], lambda state: state["prior_registration_ref"].__setitem__("sequence", 2)),
        (*ROTATION_CASES[1], lambda state: state["prior_registration_ref"].__setitem__("registration_role", "service")),
        (*ROTATION_CASES[2], lambda state: state.__setitem__("scope", ["detached_scope"])),
    ),
)
def test_registration_credential_rotation_replay_rejects_resigned_semantic_tamper(
    logical_name, event, registration_role, mutation,
):
    package, store = registration_rotation_fixture(
        logical_name, event, registration_role, mutation,
    )
    assert_code("NMRPA_E_REGISTRATION_STATE", lambda: nmrpa3.validate_package(package, store))


def test_scope_extension_is_monotonic():
    payload = nmrpa3._transition("recorder_scope_extended", "x", {"prior_transition_id": "t", "old_scope": ["a", "b"], "added_scope": ["b"], "new_scope": ["a", "b"]}, 1)
    assert_code("NMRPA_E_SCOPE_TRANSITION", lambda: nmrpa3.validate_transition_payload("capture_recorder_registration_log", payload))


def test_journal_marker_head_and_bootstrap_tamper():
    package, store = fixture(); tx = package["governance_logs"]["identity_registry_log"]["transactions"][0]
    tx["marker"]["record_sha256"] = "0" * 64; reseal(tx["marker"], "marker_sha256")
    assert_code("NMRPA_E_LEDGER_CHAIN", lambda: nmrpa3.validate_package(package, store))
    package, store = fixture(); package["bootstrap"]["fixed_log_heads"]["identity_registry_log"]["head_sha256"] = "0" * 64; reseal(package["bootstrap"], "bootstrap_sha256")
    assert_code("NMRPA_E_BOOTSTRAP_PIN", lambda: nmrpa3.validate_package(package, store))


def test_recovery_quarantines_partial_and_fork():
    package, _ = fixture(); log = package["governance_logs"]["identity_registry_log"]
    assert nmrpa3.recover_log(log, None) == {"action": "none", "quarantine": False}
    assert nmrpa3.recover_log(log, {"journal": {}})["quarantine"] is True
    assert nmrpa3.recover_log(log, {"journal": {"expected_previous_head": "bad"}, "marker": {}})["action"] == "quarantine_fork"


def test_recovery_accepts_only_fully_valid_next_transaction_readonly():
    package, _ = fixture(); log = package["governance_logs"]["identity_registry_log"]
    first = log["transactions"][0]["record"]["body"]["payload"]
    second = nmrpa3._transition("identity_registered", "identity_synthetic_second", {"principal_id": "principal_synthetic_trust", "identity_id": "identity_synthetic_second", "credential_id": "credential_trust_registry_issuer", "scope": ["trust_registry"]}, 2)
    extended = nmrpa3._log("identity_registry_log", [first, second])
    result = nmrpa3.recover_log(log, extended["transactions"][1])
    assert result == {"action": "eligible_readonly_recovery_after_full_validation", "quarantine": False}


def test_binding_authorization_anchor_are_independently_bound():
    package, store = fixture(); package["binding"]["cross_binding"]["eligible_set_sha256"] = "0" * 64; reseal(package["binding"], "binding_sha256")
    assert_code("NMRPA_E_CROSS_BINDING", lambda: nmrpa3.validate_package(package, store))
    package, store = fixture(); package["anchor"]["binding_sha256"] = "0" * 64; reseal(package["anchor"], "anchor_sha256")
    assert_code("NMRPA_E_ANCHOR_MISMATCH", lambda: nmrpa3.validate_package(package, store))
    package, store = fixture(); package["authorization"]["no_publish"] = False; reseal(package["authorization"], "authorization_sha256")
    assert_code("NMRPA_E_AUTHORIZATION", lambda: nmrpa3.validate_package(package, store))


@pytest.mark.parametrize("mutation", ["unknown", "missing", "wrong_type", "wrong_null"])
def test_recursive_exact_modela_schema_rejects_nested_mutations(mutation):
    package, store = fixture()
    payload = copy.deepcopy(next(
        json.loads(store.get(member["object_token"]))
        for root in package["source_roots"] if root["root_kind"] == "modela_signal"
        for member in root["ordered_members"] if member["file_role"] == "normalized_payload"
    ))
    row = payload["rows"][0]
    if mutation == "unknown":
        row["unknown"] = True
    elif mutation == "missing":
        del row["raw_score"]
    elif mutation == "wrong_type":
        row["raw_score"] = "1.0"
    else:
        row["raw_score"] = None
    package["modela_rows"] = copy.deepcopy(payload["rows"])
    store = replace_member_bytes(package, store, "modela_signal", "normalized_payload", payload)
    assert_code("NMRPA_E_SCHEMA", lambda: nmrpa3.validate_package(package, store))


def test_package_rows_cannot_detach_from_selected_inventory_bytes():
    package, store = fixture()
    package["price_rows"][0]["raw_close"] += 1
    package["price_rows"][0]["close"] += 1
    reseal(package["price_rows"][0], "normalized_row_sha256")
    assert_code("NMRPA_E_NORMALIZED_VIEW", lambda: nmrpa3.validate_package(package, store))


def test_required_tradability_member_and_alias_paths_fail_closed():
    package, store = fixture()
    root = next(root for root in package["source_roots"] if root["root_kind"] == "adjusted_price")
    member = next(member for member in root["ordered_members"] if member["file_role"] == "tradability_payload")
    root["ordered_members"].remove(member); root["member_count"] -= 1; reseal(root, "root_inventory_sha256")
    objects = dict(store.objects); del objects[member["object_token"]]
    assert_code("NMRPA_E_INVENTORY", lambda: nmrpa3.validate_package(package, with_objects(store, objects)))
    for bad in ("synthetic/latest/value.json", "synthetic//value.json", "synthetic/./value.json", "synthetic/ALIAS/../value.json"):
        package, store = fixture(); member = package["source_roots"][0]["ordered_members"][0]
        member["relative_path"] = bad
        package["source_roots"][0]["ordered_members"].sort(key=lambda value: value["relative_path"].encode())
        reseal(package["source_roots"][0], "root_inventory_sha256")
        assert_code("NMRPA_E_ROOT_ALIAS", lambda: nmrpa3.validate_package(package, store))


def test_pit_publication_authority_source_and_record_are_committed_and_bound():
    package, store = fixture(); evidence = package["pit_bindings"][0]
    evidence["authority_id"] = "authority_unregistered"; evidence["source_id"] = "synthetic_other"; reseal(evidence, "evidence_sha256")
    assert_code("NMRPA_E_SOURCE_ASOF", lambda: nmrpa3.validate_package(package, store))
    package, store = fixture()
    root = next(root for root in package["source_roots"] if root["root_kind"] == "sealed_calendar")
    member = next(member for member in root["ordered_members"] if member["file_role"] == "publication_record")
    record = json.loads(store.get(member["object_token"])); record["authority_id"] = "authority_unregistered"
    store = replace_member_bytes(package, store, "sealed_calendar", "publication_record", record)
    evidence = package["pit_bindings"][0]
    evidence["publication_record_ref"]["bytes_sha256"] = member["bytes_sha256"]
    evidence["publication_record_ref"]["canonical_object_sha256"] = member["ordered_objects"][0]["canonical_object_sha256"]
    reseal(evidence, "evidence_sha256")
    assert_code("NMRPA_E_PIT_AUTHORITY", lambda: nmrpa3.validate_package(package, store))


def test_twii_exact_60_calendar_grid_and_modela_asof():
    package, _ = fixture(); package["twii_rows"][1] = copy.deepcopy(package["twii_rows"][0])
    assert_code("NMRPA_E_TWII_GRID", lambda: nmrpa3.validate_cross_section(package))
    package, _ = fixture(); package["modela_rows"][0]["signal_asof"] = "2099-06-29"; reseal(package["modela_rows"][0], "row_sha256")
    assert_code("NMRPA_E_MODELA_ASOF", lambda: nmrpa3.validate_cross_section(package))


def test_package_resign_cannot_replace_external_heads_anchor_or_contracts():
    package, store = fixture()
    package["binding"]["contract_digests"]["feature_contract_sha256"] = "0" * 64
    reseal(package["binding"], "binding_sha256")
    package["anchor"]["binding_sha256"] = package["binding"]["binding_sha256"]; reseal(package["anchor"], "anchor_sha256")
    assert_code("NMRPA_E_CONTRACT_DIGEST", lambda: nmrpa3.validate_package(package, store))
    package, store = fixture(); package["bootstrap"]["bootstrap_id"] = "nmrpa.synthetic.replaced.v1"; reseal(package["bootstrap"], "bootstrap_sha256")
    assert_code("NMRPA_E_BOOTSTRAP_PIN", lambda: nmrpa3.validate_package(package, store))


def test_orphan_recovery_requires_full_transaction_validation():
    package, _ = fixture(); log = package["governance_logs"]["identity_registry_log"]
    junk = {"record": {"junk": True}, "journal": {"expected_previous_head": log["current_head"]["head_sha256"]}, "marker": {"junk": True}, "historical_head": {"junk": True}}
    result = nmrpa3.recover_log(log, junk)
    assert result == {"action": "quarantine_invalid_orphan", "quarantine": True}


def test_governance_recursive_types_reject_fully_resigned_transition_and_times():
    package, _ = fixture()
    original = package["governance_logs"]["principal_registry_log"]["transactions"][0]["record"]["body"]["payload"]

    malformed = copy.deepcopy(original)
    malformed["effective_at"] = None
    reseal(malformed, "transition_sha256")
    assert_code(
        "NMRPA_E_SCHEMA",
        lambda: nmrpa3.validate_log(
            "principal_registry_log",
            nmrpa3._log("principal_registry_log", [malformed]),
        ),
    )

    malformed = copy.deepcopy(original)
    malformed["state"]["canonical_identity"]["canonical_subject_id"] = 7
    reseal(malformed, "transition_sha256")
    assert_code(
        "NMRPA_E_SCHEMA",
        lambda: nmrpa3.validate_log(
            "principal_registry_log",
            nmrpa3._log("principal_registry_log", [malformed]),
        ),
    )

    resigned = nmrpa3._log("principal_registry_log", [copy.deepcopy(original)])
    resigned["transactions"][0]["record"]["body"]["sequence"] = True
    assert_code("NMRPA_E_SCHEMA", lambda: nmrpa3.validate_log("principal_registry_log", resigned))


def test_first_capture_binds_registered_request_source_and_every_attempt_digest():
    config = json.loads(CONFIG.read_text())
    config["fixture_id"] = "synthetic_capture_binding_probe_v1"
    config["evidence_mode"] = "first_successful_capture"

    package, store = nmrpa3.build_synthetic_fixture(config)
    evidence = package["pit_bindings"][0]
    evidence["request_identity"]["source_id"] = "synthetic_detached_source"
    evidence["request_identity_sha256"] = nmrpa3.digest({
        "schema_version": "nmrpa.request_identity.v3",
        **evidence["request_identity"],
    })
    reseal(evidence, "evidence_sha256")
    selected = nmrpa3.validate_source_roots(package, store)
    governance = nmrpa3.validate_governance(package, store)
    assert_code("NMRPA_E_SOURCE_ASOF", lambda: nmrpa3.validate_pit(package, selected, governance))

    package, store = nmrpa3.build_synthetic_fixture(config)
    evidence = package["pit_bindings"][0]
    kind = evidence["root_kind"]
    attempts = copy.deepcopy(evidence["ordered_attempts"])
    attempts[0]["request_identity_sha256"] = "0" * 64
    ledger = {
        "recorder_id": "recorder_synthetic_capture",
        "source_id": evidence["source_id"],
        "ordered_attempts": attempts,
    }
    store = replace_member_bytes(package, store, kind, "attempt_ledger", ledger)
    member = next(
        member
        for root in package["source_roots"] if root["root_kind"] == kind
        for member in root["ordered_members"] if member["file_role"] == "attempt_ledger"
    )
    evidence["ordered_attempts"] = attempts
    evidence["attempt_ledger_ref"]["bytes_sha256"] = member["bytes_sha256"]
    evidence["attempt_ledger_ref"]["canonical_object_sha256"] = member["ordered_objects"][0]["canonical_object_sha256"]
    reseal(evidence, "evidence_sha256")
    selected = nmrpa3.validate_source_roots(package, store)
    governance = nmrpa3.validate_governance(package, store)
    assert_code(
        "NMRPA_E_CAPTURE_REQUEST_BINDING",
        lambda: nmrpa3.validate_pit(package, selected, governance),
    )


def test_modela_price_twii_rows_fail_closed_on_cutoff_and_evidence_mismatch():
    for field, index in (("modela_rows", 0), ("price_rows", 0), ("twii_rows", 0)):
        package, store = fixture()
        package[field][index]["available_at"] = f"{package['target_asof']}T16:00:00Z"
        checksum_field = "normalized_row_sha256" if field == "price_rows" else "row_sha256"
        reseal(package[field][index], checksum_field)
        selected = nmrpa3.validate_source_roots(package, store)
        governance = nmrpa3.validate_governance(package, store)
        assert_code("NMRPA_E_ROW_PIT", lambda: nmrpa3.validate_pit(package, selected, governance))

    package, store = fixture()
    package["modela_rows"][0]["source_asof"] = "2099-06-29"
    reseal(package["modela_rows"][0], "row_sha256")
    selected = nmrpa3.validate_source_roots(package, store)
    governance = nmrpa3.validate_governance(package, store)
    assert_code("NMRPA_E_ROW_PIT_BINDING", lambda: nmrpa3.validate_pit(package, selected, governance))


def test_schema_file_matches_embedded_top_level_schema():
    schema = json.loads((ROOT / "scripts/schemas/tw_policy_nmrpa3_source_adapter.schema.json").read_text())
    assert schema == nmrpa3.TOP_LEVEL_SCHEMA


def test_nmrpa2_synthetic_allowlist_is_not_changed():
    source = (ROOT / "scripts/tw_policy_nmrpa2.py").read_text()
    assert 'SYNTHETIC_RE = re.compile(r"^SYNTHETIC_[A-Z0-9_]+$")' in source
    assert "nmrpa3" not in source.casefold()
