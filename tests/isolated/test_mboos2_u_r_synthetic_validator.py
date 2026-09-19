import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import synthetic_mboos2_u_r_structural_absence_validator as validator


def record(status="confirmed_absent"):
    evidence = {
        "complete_scope": True, "request_scope_id": "SYNTHETIC_SCOPE_001", "request_scope_sha256": "SYNTHETIC_SCOPE_HASH",
        "expected_set": [["SYNTHETIC_TRADE_DAY_001", "SYNTHETIC_SYMBOL_A"]],
        "returned_set": [], "absent_set": [["SYNTHETIC_TRADE_DAY_001", "SYNTHETIC_SYMBOL_A"]],
        "effective_interval_verified": True, "pit_available_at": "SYNTHETIC_TIME_BEFORE_CUTOFF", "source_asof": "SYNTHETIC_TRADE_DAY_001",
        "evidence_path": "SYNTHETIC_EVIDENCE_PATH", "manifest_sha256": "SYNTHETIC_MANIFEST_HASH",
        "immutable_lineage": "SYNTHETIC_LINEAGE_001", "lineage": "SYNTHETIC_LINEAGE_001", "binding_ok": True,
    }
    base = {"schema_version": validator.SCHEMA_VERSION, "record_id": "SYNTHETIC_RECORD_001", "sample_date": "SYNTHETIC_TRADE_DAY_001", "instrument": "SYNTHETIC_SYMBOL_A", "source_kind": "SYNTHETIC_MARGIN", "status": status, "request_scope_id": "SYNTHETIC_SCOPE_001", "request_scope_sha256": "SYNTHETIC_SCOPE_HASH", "effective_start_or_null": "SYNTHETIC_TRADE_DAY_000", "effective_end_or_null": None, "decision_time": "SYNTHETIC_TIME_CUTOFF", "pit_available_at": "SYNTHETIC_TIME_BEFORE_CUTOFF", "authoritative_evidence": evidence, "classification_reason_code": "SYNTHETIC_CONFIRMED_ABSENCE", "unique_join_key": ["SYNTHETIC_TRADE_DAY_001", "SYNTHETIC_SYMBOL_A"], "lineage": "SYNTHETIC_LINEAGE_001", "eligibility_layers": {"active_set": "formal_bound", "listing_status": "eligible", "trading_status": "tradable", "margin_eligibility": "eligible", "source_completeness": "complete"}}
    base["record_sha256"] = validator.canonical_sha256(base, exclude="record_sha256")
    return base


def test_confirmed_absent_eight_gates_and_mapping_boundary():
    item = record()
    result = validator.validate_record(item)
    assert len(result["checks"]) == 8 and all(result["checks"].values())
    mapped = validator.synthetic_absence_mapping(item)
    assert mapped["missing_flag"] is True and mapped["numeric_value"] is None


@pytest.mark.parametrize("status", sorted(validator.STATUSES))
def test_status_closed_set(status):
    item = record(status)
    if status != "confirmed_absent":
        item["feature_mapping"] = "blocked"
    assert validator.validate_record(item)["status"] == status


def test_rejects_real_path_date_payload_and_invalid_status():
    with pytest.raises(validator.SyntheticContractError, match="REAL_PATH"):
        validator.validate_input_path("/home/project/2026-08-24/payload.json")
    item = record(); item["sample_date"] = "2026-08-24"
    with pytest.raises(validator.SyntheticContractError): validator.validate_record(item)


def test_rejects_real_payload_field_shape():
    item = record(); item["future_return"] = 0.1
    with pytest.raises(validator.SyntheticContractError, match="REAL_PAYLOAD_FIELD"):
        validator.validate_record(item)
    item = record(); item["status"] = "neutral"
    with pytest.raises(validator.SyntheticContractError): validator.validate_record(item)


@pytest.mark.parametrize("field", ["complete_scope", "effective_interval_verified", "binding_ok"])
def test_confirmed_absent_gate_is_fail_closed(field):
    item = record(); item["authoritative_evidence"][field] = False
    item["record_sha256"] = validator.canonical_sha256(item, exclude="record_sha256")
    with pytest.raises(validator.SyntheticContractError, match="CONFIRMED_ABSENT_GATE_FAILED"):
        validator.validate_record(item)


def test_four_layers_are_independent_and_fail_closed():
    item = record(); item["eligibility_layers"]["margin_eligibility"] = "unknown"
    item["record_sha256"] = validator.canonical_sha256(item, exclude="record_sha256")
    with pytest.raises(validator.SyntheticContractError, match="CONFIRMED_ABSENT_GATE_FAILED"):
        validator.validate_record(item)
    item = record(); del item["eligibility_layers"]["trading_status"]
    with pytest.raises(validator.SyntheticContractError, match="ELIGIBILITY_LAYERS_INCOMPLETE"):
        validator.validate_record(item)


def test_closure_duplicate_and_hash_tamper_rejected():
    item = record(); item["authoritative_evidence"]["absent_set"] = []
    item["record_sha256"] = validator.canonical_sha256(item, exclude="record_sha256")
    with pytest.raises(validator.SyntheticContractError): validator.validate_record(item)
    item = record(); item["record_sha256"] = "0" * 64
    with pytest.raises(validator.SyntheticContractError): validator.validate_record(item)


@pytest.mark.parametrize("set_name", ["expected_set", "returned_set", "absent_set"])
def test_closure_rejects_duplicate_pair_before_set_normalization(set_name):
    item = record()
    item["authoritative_evidence"][set_name] = [
        ["SYNTHETIC_TRADE_DAY_001", "SYNTHETIC_SYMBOL_A"],
        ["SYNTHETIC_TRADE_DAY_001", "SYNTHETIC_SYMBOL_A"],
    ]
    item["record_sha256"] = validator.canonical_sha256(item, exclude="record_sha256")
    with pytest.raises(validator.SyntheticContractError, match="DUPLICATE_SET_PAIR"):
        validator.validate_record(item)


@pytest.mark.parametrize("pit_value", ["SYNTHETIC_TIME_AFTER_CUTOFF", "SYNTHETIC_TIME_UNKNOWN"])
def test_future_or_unknown_pit_is_not_absence(pit_value):
    item = record(); item["pit_available_at"] = pit_value; item["authoritative_evidence"]["pit_available_at"] = pit_value
    item["record_sha256"] = validator.canonical_sha256(item, exclude="record_sha256")
    with pytest.raises(validator.SyntheticContractError, match="CONFIRMED_ABSENT_GATE_FAILED"):
        validator.validate_record(item)


def test_non_absence_neutral_and_feature_boundary():
    item = record("unknown_source_coverage"); item["feature_mapping"] = "neutral"
    with pytest.raises(validator.SyntheticContractError, match="NEUTRAL_FILL"):
        validator.validate_record(item)
    with pytest.raises(validator.SyntheticContractError, match="MAPPING"):
        validator.synthetic_absence_mapping(record("present"))


def test_date_invalid_quarantine_and_duplicate_key():
    item = record("unknown_source_coverage"); item["feature_mapping"] = "blocked"
    summary = {"date": "SYNTHETIC_TRADE_DAY_001", "status": "quarantined", "quarantine_reason": "SYNTHETIC_SOURCE_UNKNOWN", "records": [item]}
    assert validator.validate_date_summary(summary)["status"] == "quarantined"
    duplicate = {**summary, "records": [item, copy.deepcopy(item)]}
    with pytest.raises(validator.SyntheticContractError, match="DUPLICATE"):
        validator.validate_date_summary(duplicate)


def test_valid_date_rejects_unresolved_record():
    item = record("unknown_source_coverage"); item["feature_mapping"] = "blocked"
    summary = {"date": "SYNTHETIC_TRADE_DAY_001", "status": "valid", "records": [item]}
    with pytest.raises(validator.SyntheticContractError): validator.validate_date_summary(summary)


def test_date_summary_rejects_record_sample_date_mismatch():
    item = record("present")
    item["sample_date"] = "SYNTHETIC_TRADE_DAY_002"
    item["unique_join_key"] = [item["sample_date"], item["instrument"]]
    item["record_sha256"] = validator.canonical_sha256(item, exclude="record_sha256")
    summary = {"date": "SYNTHETIC_TRADE_DAY_001", "status": "valid", "records": [item]}
    with pytest.raises(validator.SyntheticContractError, match="DATE_RECORD_MISMATCH"):
        validator.validate_date_summary(summary)


def test_append_only_recovery_and_version_migration():
    old = {"version_id": "SYNTHETIC_VERSION_001", "status": "quarantined", "date": "SYNTHETIC_TRADE_DAY_001", "quarantine_reason": "SYNTHETIC_SOURCE_UNKNOWN", "records": []}
    present = record("present"); present["authoritative_evidence"] = {}; present["record_sha256"] = validator.canonical_sha256(present, exclude="record_sha256")
    new = {"version_id": "SYNTHETIC_VERSION_002", "supersedes": old["version_id"], "status": "recovered", "date": old["date"], "records": [present]}
    validator.validate_recovery(old, new)
    with pytest.raises(validator.SyntheticContractError): validator.validate_recovery(old, {**new, "version_id": old["version_id"]})
    validator.validate_version_migration({"schema_version": "SYNTHETIC_SCHEMA_V1"}, {"schema_version": "SYNTHETIC_SCHEMA_V2"}, {"from": "SYNTHETIC_SCHEMA_V1", "to": "SYNTHETIC_SCHEMA_V2", "reviewer_approval": "SYNTHETIC_REVIEW", "new_canonical_hash": "SYNTHETIC_HASH"})


def test_input_path_requires_isolated_synthetic_tmp():
    validator.validate_input_path("/tmp/SYNTHETIC_MBOOS2_U_R/payload.json")
    with pytest.raises(validator.SyntheticContractError): validator.validate_input_path("/tmp/payload.json")
