import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import synthetic_mboos2_u_r_structural_absence_validator as validator
import synthetic_mboos2_v_source_absence_integration as integration


def record(status="confirmed_absent"):
    evidence = {
        "complete_scope": True,
        "request_scope_id": "SYNTHETIC_SCOPE_001",
        "request_scope_sha256": "SYNTHETIC_SCOPE_HASH",
        "expected_set": [["SYNTHETIC_TRADE_DAY_001", "SYNTHETIC_SYMBOL_A"]],
        "returned_set": [],
        "absent_set": [["SYNTHETIC_TRADE_DAY_001", "SYNTHETIC_SYMBOL_A"]],
        "effective_interval_verified": True,
        "pit_available_at": "SYNTHETIC_TIME_BEFORE_CUTOFF",
        "source_asof": "SYNTHETIC_TRADE_DAY_001",
        "evidence_path": "SYNTHETIC_EVIDENCE_PATH",
        "manifest_sha256": "SYNTHETIC_MANIFEST_HASH",
        "immutable_lineage": "SYNTHETIC_LINEAGE_001",
        "lineage": "SYNTHETIC_LINEAGE_001",
        "binding_ok": True,
    }
    item = {
        "schema_version": validator.SCHEMA_VERSION,
        "record_id": "SYNTHETIC_RECORD_001",
        "sample_date": "SYNTHETIC_TRADE_DAY_001",
        "instrument": "SYNTHETIC_SYMBOL_A",
        "source_kind": "SYNTHETIC_MARGIN",
        "status": status,
        "request_scope_id": "SYNTHETIC_SCOPE_001",
        "request_scope_sha256": "SYNTHETIC_SCOPE_HASH",
        "effective_start_or_null": "SYNTHETIC_TRADE_DAY_000",
        "effective_end_or_null": None,
        "decision_time": "SYNTHETIC_TIME_CUTOFF",
        "pit_available_at": "SYNTHETIC_TIME_BEFORE_CUTOFF",
        "authoritative_evidence": evidence,
        "classification_reason_code": "SYNTHETIC_CLASSIFICATION",
        "unique_join_key": ["SYNTHETIC_TRADE_DAY_001", "SYNTHETIC_SYMBOL_A"],
        "lineage": "SYNTHETIC_LINEAGE_001",
        "eligibility_layers": {
            "active_set": "formal_bound",
            "listing_status": "eligible",
            "trading_status": "tradable",
            "margin_eligibility": "eligible",
            "source_completeness": "complete",
        },
    }
    if status not in {"confirmed_absent", "present"}:
        item["feature_mapping"] = "blocked"
    item["record_sha256"] = validator.canonical_sha256(item, exclude="record_sha256")
    return item


def envelope(source_state, status):
    return {
        "adapter_schema_version": integration.ADAPTER_SCHEMA_VERSION,
        "adapter_id": "SYNTHETIC_ADAPTER_001",
        "input_path": "/tmp/SYNTHETIC_MBOOS2_V/metadata.json",
        "source_state": source_state,
        "record": record(status),
    }


@pytest.mark.parametrize("source_state,status", integration.SOURCE_STATE_TO_STATUS.items())
def test_adapter_maps_all_seven_states(source_state, status):
    result = integration.adapt_source_metadata(envelope(source_state, status))
    assert result["status"] == status


def test_confirmed_absent_is_neutral_but_not_trainable():
    result = integration.adapt_source_metadata(
        envelope("SYNTHETIC_SOURCE_CONFIRMED_ABSENT", "confirmed_absent")
    )
    assert result["neutral"] is True
    assert result["trainable"] is False
    assert result["feature_value"] is None


def test_present_is_trainable_but_not_neutral():
    result = integration.adapt_source_metadata(
        envelope("SYNTHETIC_SOURCE_PRESENT", "present")
    )
    assert result["trainable"] is True
    assert result["neutral"] is False


@pytest.mark.parametrize(
    "source_state,status",
    [
        ("SYNTHETIC_SOURCE_COVERAGE_UNKNOWN", "unknown_source_coverage"),
        ("SYNTHETIC_SOURCE_SCOPE_INCOMPLETE", "scope_incomplete"),
        ("SYNTHETIC_SOURCE_ACCESS_FAILED", "access_failed"),
        ("SYNTHETIC_SOURCE_STALE", "stale"),
        ("SYNTHETIC_SOURCE_CONFLICTING", "conflicting"),
    ],
)
def test_unresolved_states_are_neither_neutral_nor_trainable(source_state, status):
    result = integration.adapt_source_metadata(envelope(source_state, status))
    assert result["neutral"] is False
    assert result["trainable"] is False
    assert result["quarantine"] is True


def test_adapter_rejects_state_mismatch_and_unknown_state():
    with pytest.raises(integration.SyntheticIntegrationError, match="STATUS_MISMATCH"):
        integration.adapt_source_metadata(
            envelope("SYNTHETIC_SOURCE_PRESENT", "confirmed_absent")
        )
    item = envelope("SYNTHETIC_SOURCE_PRESENT", "present")
    item["source_state"] = "SYNTHETIC_SOURCE_NOT_CLOSED"
    with pytest.raises(integration.SyntheticIntegrationError, match="STATE_NOT_CLOSED"):
        integration.adapt_source_metadata(item)


@pytest.mark.parametrize("set_name", ["expected_set", "returned_set", "absent_set"])
def test_duplicate_pairs_propagate_from_validator(set_name):
    item = envelope("SYNTHETIC_SOURCE_CONFIRMED_ABSENT", "confirmed_absent")
    pair = ["SYNTHETIC_TRADE_DAY_001", "SYNTHETIC_SYMBOL_A"]
    item["record"]["authoritative_evidence"][set_name] = [pair, pair]
    item["record"]["record_sha256"] = validator.canonical_sha256(
        item["record"], exclude="record_sha256"
    )
    with pytest.raises(validator.SyntheticContractError, match="DUPLICATE_SET_PAIR"):
        integration.adapt_source_metadata(item)


@pytest.mark.parametrize("attack", ["pit", "hash", "binding"])
def test_pit_hash_and_binding_attacks_are_rejected(attack):
    item = envelope("SYNTHETIC_SOURCE_CONFIRMED_ABSENT", "confirmed_absent")
    if attack == "pit":
        item["record"]["pit_available_at"] = "SYNTHETIC_TIME_AFTER_CUTOFF"
        item["record"]["authoritative_evidence"]["pit_available_at"] = "SYNTHETIC_TIME_AFTER_CUTOFF"
    elif attack == "binding":
        item["record"]["authoritative_evidence"]["lineage"] = "SYNTHETIC_LINEAGE_OTHER"
    item["record"]["record_sha256"] = validator.canonical_sha256(
        item["record"], exclude="record_sha256"
    )
    if attack == "hash":
        item["record"]["record_sha256"] = "0" * 64
    with pytest.raises(validator.SyntheticContractError, match="CONFIRMED_ABSENT_GATE_FAILED"):
        integration.adapt_source_metadata(item)


def test_all_eight_gates_propagate_fail_closed():
    baseline = envelope("SYNTHETIC_SOURCE_CONFIRMED_ABSENT", "confirmed_absent")
    result = validator.validate_record(baseline["record"])
    assert set(result["checks"]) == set(validator.CONFIRMED_ABSENT_REQUIREMENTS)
    assert all(result["checks"].values())


@pytest.mark.parametrize(
    "gate,mutate",
    [
        ("complete_scope", lambda item: item["record"]["authoritative_evidence"].update(complete_scope=False)),
        ("set_closure", lambda item: item["record"]["authoritative_evidence"].update(returned_set=[["SYNTHETIC_TRADE_DAY_001", "SYNTHETIC_SYMBOL_A"]])),
        ("target_in_absent", lambda item: item["record"]["authoritative_evidence"].update(absent_set=[])),
        ("effective_interval", lambda item: item["record"]["authoritative_evidence"].update(effective_interval_verified=False)),
        ("pit_ok", lambda item: item["record"]["authoritative_evidence"].update(pit_available_at="SYNTHETIC_TIME_AFTER_CUTOFF")),
        ("immutable_evidence", lambda item: item["record"]["authoritative_evidence"].update(evidence_path="")),
        ("binding_ok", lambda item: item["record"]["authoritative_evidence"].update(binding_ok=False)),
        ("unique_key_and_hash", lambda item: item["record"].update(record_sha256="0" * 64)),
    ],
)
def test_each_confirmed_absent_gate_rejects_through_adapter(gate, mutate):
    item = envelope("SYNTHETIC_SOURCE_CONFIRMED_ABSENT", "confirmed_absent")
    mutate(item)
    if gate != "unique_key_and_hash":
        item["record"]["record_sha256"] = validator.canonical_sha256(
            item["record"], exclude="record_sha256"
        )
    with pytest.raises(validator.SyntheticContractError, match="CONFIRMED_ABSENT_GATE_FAILED") as caught:
        integration.adapt_source_metadata(item)
    assert gate in str(caught.value)


def test_date_mismatch_is_rejected_even_with_matching_key_and_hash():
    item = record("present")
    item["sample_date"] = "SYNTHETIC_TRADE_DAY_002"
    item["unique_join_key"] = [item["sample_date"], item["instrument"]]
    item["record_sha256"] = validator.canonical_sha256(item, exclude="record_sha256")
    summary = {"date": "SYNTHETIC_TRADE_DAY_001", "status": "valid", "records": [item]}
    with pytest.raises(validator.SyntheticContractError, match="DATE_RECORD_MISMATCH"):
        integration.validate_integrated_date(summary)


def test_unresolved_date_must_be_quarantined():
    item = record("unknown_source_coverage")
    summary = {"date": item["sample_date"], "status": "recovered", "records": [item]}
    with pytest.raises(integration.SyntheticIntegrationError, match="NOT_QUARANTINED"):
        integration.validate_integrated_date(summary)


def test_quarantine_and_append_only_recovery():
    unresolved = record("unknown_source_coverage")
    old = {
        "version_id": "SYNTHETIC_VERSION_001",
        "status": "quarantined",
        "date": unresolved["sample_date"],
        "quarantine_reason": "SYNTHETIC_SOURCE_UNKNOWN",
        "records": [unresolved],
    }
    assert integration.validate_integrated_date(old)["quarantine"] is True
    present = record("present")
    new = {
        "version_id": "SYNTHETIC_VERSION_002",
        "supersedes": old["version_id"],
        "status": "recovered",
        "date": old["date"],
        "records": [present],
    }
    assert integration.validate_integrated_recovery(old, new)["trainable"] is True
    bad = copy.deepcopy(new)
    bad["version_id"] = old["version_id"]
    with pytest.raises(validator.SyntheticContractError, match="NOT_APPEND_ONLY"):
        integration.validate_integrated_recovery(old, bad)


@pytest.mark.parametrize(
    "mutate,error",
    [
        (lambda item: item.update(input_path="/real/source/payload.json"), "REAL_PATH"),
        (lambda item: item["record"].update(sample_date="2026-08-24"), "REAL_INPUT"),
        (lambda item: item["record"].update(future_return=0.1), "REAL_PAYLOAD_FIELD"),
        (lambda item: item.update(adapter_id="adapter-real"), "REAL_INPUT"),
    ],
)
def test_real_inputs_are_rejected(mutate, error):
    item = envelope("SYNTHETIC_SOURCE_PRESENT", "present")
    mutate(item)
    with pytest.raises(validator.SyntheticContractError, match=error):
        integration.adapt_source_metadata(item)


def test_envelope_is_exact_and_schema_is_synthetic_only():
    item = envelope("SYNTHETIC_SOURCE_PRESENT", "present")
    item["payload"] = "SYNTHETIC_FORBIDDEN_EXTRA"
    with pytest.raises(integration.SyntheticIntegrationError, match="FIELDS_INVALID"):
        integration.adapt_source_metadata(item)
    item = envelope("SYNTHETIC_SOURCE_PRESENT", "present")
    item["adapter_schema_version"] = "adapter.v1"
    with pytest.raises(integration.SyntheticIntegrationError, match="SCHEMA_VERSION"):
        integration.adapt_source_metadata(item)
