from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/tw_policy_nmrpa2.py"
SPEC = importlib.util.spec_from_file_location("tw_policy_nmrpa2", MODULE_PATH)
assert SPEC and SPEC.loader
nmrpa = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(nmrpa)
FIXTURE = ROOT / "tests/fixtures/nmrpa2/synthetic_positive.json"
EXPECTED_INPUT_SHA256 = "c399232f56765c3eb09e7c0f3760f6a798afb1a16def8315a19f8bebd941135b"


def fixture() -> dict:
    return json.loads(FIXTURE.read_text())


def anchor_for(root: Path) -> Path:
    return root.parent / f"{root.name}_EXTERNAL_CHAIN_ANCHOR.json"


def build_candidate(root: Path) -> dict:
    return nmrpa.build(
        FIXTURE,
        root,
        expected_input_sha256=EXPECTED_INPUT_SHA256,
        chain_anchor_path=anchor_for(root),
    )


def validate_candidate(root: Path) -> dict:
    return nmrpa.validate_candidate_root(
        root,
        expected_input_sha256=EXPECTED_INPUT_SHA256,
        expected_chain_anchor=anchor_for(root),
    )


def candidate_event_body(decision: str, payload_sha256: str) -> dict:
    return {
        "artifact_type": "prospective_accumulation_event",
        "schema_version": nmrpa.SCHEMA_VERSION,
        "contract_id": "SYNTHETIC_CONTRACT",
        "decision_date": decision,
        "event_type": "candidate_valid",
        "attempt_id": f"SYNTHETIC_ATTEMPT_{decision.removeprefix('SYNTHETIC_')}",
        "event_time": "SYNTHETIC_TIME_EVENT",
        "payload_sha256": payload_sha256,
        **nmrpa.contract_refs(),
    }


def cohort_row(sequence: int) -> dict:
    decision = f"SYNTHETIC_DECISION_{sequence:03d}"
    dates = [decision] + [f"SYNTHETIC_FUTURE_{sequence:03d}_{i:02d}" for i in range(1, 11)]
    calendar = {
        "artifact_type": "synthetic_calendar_binding", "schema_version": nmrpa.SCHEMA_VERSION,
        "decision_date": decision, "prefix_dates": [decision], "full_dates": dates,
        "prefix_sha256": nmrpa.digest([decision]), "full_sha256": nmrpa.digest(dates),
        "maturity_horizon_td": 10, "maturity_endpoint": dates[-1],
    }
    candidate_sha = nmrpa.digest({"decision": decision, "instrument": "SYNTHETIC_SYMBOL_A"})
    candidates = [{"instrument": "SYNTHETIC_SYMBOL_A", "candidate_sha256": candidate_sha}]
    candidate_set_sha = nmrpa.digest(candidates)
    identity = {
        "contract_id": "SYNTHETIC_CONTRACT", "decision_date": decision,
        "instrument": "SYNTHETIC_SYMBOL_A", "candidate_sha256": candidate_sha,
        "calendar_prefix_sha256": calendar["prefix_sha256"], "calendar_full_sha256": calendar["full_sha256"],
        "maturity_endpoint": calendar["maturity_endpoint"],
    }
    history = []
    for state in ("candidate_pending", "label_pending", "matured", "sealed"):
        history.append(nmrpa.append_state(history, state, identity=identity))
    event = nmrpa._new_event(candidate_event_body(decision, candidate_set_sha), 1, None)
    source = {"decision_date": decision, "external_input_sha256": nmrpa.digest({"immutable_input": decision}), "calendar_binding": calendar, **nmrpa.contract_refs()}
    source["manifest_sha256"] = nmrpa.checksum_without(source, "manifest_sha256")
    eligibility = {"decision_date": decision, "included_symbols": ["SYNTHETIC_SYMBOL_A"], "candidate_set_sha256": candidate_set_sha, "source_manifest_sha256": source["manifest_sha256"]}
    eligibility["eligibility_sha256"] = nmrpa.checksum_without(eligibility, "eligibility_sha256")
    protected = {"SYNTHETIC_PROTECTED_PATH": {"exists": False, "sha256": None}}
    acl = {"protected_unchanged": True, "synthetic_only": True, "protected_before": protected, "protected_after": protected, "protected_current": protected}
    acl["audit_sha256"] = nmrpa.checksum_without(acl, "audit_sha256")
    return {
        "prospective_sequence": sequence, "decision_identity": decision,
        "candidate_event": event, "candidate_set": candidates, "included_symbols": ["SYNTHETIC_SYMBOL_A"], "eligibility_audit": eligibility,
        "maturity_histories": {"SYNTHETIC_SYMBOL_A": history},
        "source_manifest": source, "calendar_binding": calendar,
        "contract_refs": nmrpa.contract_refs(), "acl_audit": acl,
    }


def committed_completion_evidence(rows: list[dict], root: Path) -> tuple[dict, Path, Path]:
    store = root / "event_store"
    for directory in (store / "events", store / "journals", store / "commits"):
        directory.mkdir(parents=True, exist_ok=True)
    bodies = []
    for row in rows:
        event = row["candidate_event"]
        bodies.append({key: value for key, value in event.items() if key not in {"chain_sequence", "previous_event_hash", "event_body_sha256", "event_hash"}})
    committed = nmrpa._append_transaction_locked(store, bodies)
    assert isinstance(committed, list)
    for row, event in zip(rows, committed):
        row["candidate_event"] = event
    chain_anchor_path = root / "EXTERNAL_CHAIN_ANCHOR.json"
    chain_anchor = nmrpa.write_external_chain_anchor(store, chain_anchor_path)
    return completion_anchor(rows, chain_anchor), store, chain_anchor_path


def completion_anchor(rows: list[dict], chain_anchor: dict) -> dict:
    references = []
    for row in rows[:126]:
        event = row["candidate_event"]
        source = row["source_manifest"]
        calendar = row["calendar_binding"]
        references.append({
            "prospective_sequence": row["prospective_sequence"],
            "decision_identity": row["decision_identity"],
            "candidate_event_hash": event["event_hash"],
            "candidate_payload_sha256": event["payload_sha256"],
            "candidate_set_sha256": nmrpa.digest(row["candidate_set"]),
            "eligibility_sha256": row["eligibility_audit"]["eligibility_sha256"],
            "source_manifest_sha256": source["manifest_sha256"],
            "external_input_sha256": source["external_input_sha256"],
            "calendar_prefix_sha256": calendar["prefix_sha256"],
            "calendar_full_sha256": calendar["full_sha256"],
            "acl_audit_sha256": row["acl_audit"]["audit_sha256"],
        })
    anchor = {
        "artifact_type": "synthetic_external_completion_anchor",
        "schema_version": nmrpa.SCHEMA_VERSION,
        "contract_id": "SYNTHETIC_CONTRACT",
        "ordered_decision_references": references,
        "protected_fingerprint_set": copy.deepcopy(rows[0]["acl_audit"]["protected_current"]),
        "committed_chain_anchor_sha256": nmrpa.digest(chain_anchor),
        "committed_chain_head_sequence": chain_anchor["head_sequence"],
        "committed_chain_head_hash": chain_anchor["head_hash"],
        "frozen_at_chain_sequence": rows[125]["candidate_event"]["chain_sequence"],
    }
    anchor["anchor_sha256"] = nmrpa.checksum_without(anchor, "anchor_sha256")
    return anchor


def assert_code(code: str, fn) -> None:
    with pytest.raises(nmrpa.ContractError) as exc:
        fn()
    assert exc.value.code == code


def test_feature_allowlist_and_exact_recomputation() -> None:
    rows = nmrpa.compute_features(fixture())
    assert len(nmrpa.FEATURE_NAMES) == 78
    assert len(rows) == 2
    assert tuple(rows[0]["feature_values"]) == nmrpa.FEATURE_NAMES
    assert rows[0]["feature_values"]["qlib_rank"] == 1
    assert rows[0]["feature_values"]["qlib_score_percentile_by_date"] == 1.0
    assert rows[1]["feature_values"]["qlib_score_percentile_by_date"] == 0.0
    assert rows[0]["feature_values"]["institutional_missing_flag"] == 1
    assert rows[0]["feature_row_sha256"] == nmrpa.checksum_without(rows[0], "feature_row_sha256")
    # Recompute representative formula records independently.
    close = [10 + 0.1 * i for i in range(121)]
    assert rows[0]["feature_values"]["MA60"] == pytest.approx(sum(close[-60:]) / 60, rel=1e-10, abs=1e-12)
    assert rows[0]["feature_values"]["ret20"] == pytest.approx(close[-1] / close[-21] - 1, rel=1e-10, abs=1e-12)


def test_score_tie_and_zero_variance_are_stable() -> None:
    data = fixture()
    data["symbols"]["SYNTHETIC_SYMBOL_B"]["score"] = 2.0
    rows = nmrpa.compute_features(data)
    assert [r["instrument"] for r in rows] == ["SYNTHETIC_SYMBOL_A", "SYNTHETIC_SYMBOL_B"]
    assert [r["feature_values"]["qlib_rank"] for r in rows] == [1, 2]
    assert all(r["feature_values"]["qlib_score_zscore_by_date"] == 0.0 for r in rows)


@pytest.mark.parametrize("state", ["not_run", "access_failed", "stale", "zero_row_unproven", "unknown"])
def test_unproven_absence_never_neutral_fills(state: str) -> None:
    data = fixture(); data["symbols"]["SYNTHETIC_SYMBOL_A"]["institutional"] = {"source_state": state}
    assert_code("NMRPA_E_ABSENCE_EVIDENCE", lambda: nmrpa.compute_features(data))


def test_absence_requires_checksums_and_late_available_at_fails() -> None:
    data = fixture(); del data["symbols"]["SYNTHETIC_SYMBOL_A"]["margin"]["absence_evidence"]["absent_symbol_set_sha256"]
    assert_code("NMRPA_E_ABSENCE_EVIDENCE", lambda: nmrpa.compute_features(data))
    data = fixture(); data["symbols"]["SYNTHETIC_SYMBOL_A"]["available_at"] = "SYNTHETIC_TIME_AFTER_CUTOFF"
    assert_code("NMRPA_E_PIT", lambda: nmrpa.compute_features(data))


def test_active_upstream_omission_invalidates_whole_date() -> None:
    data = fixture(); del data["symbols"]["SYNTHETIC_SYMBOL_B"]
    assert_code("NMRPA_E_UPSTREAM_OMISSION", lambda: nmrpa.compute_features(data))
    data = fixture(); del data["symbols"]["SYNTHETIC_SYMBOL_B"]["score"]
    assert_code("NMRPA_E_UPSTREAM_OMISSION", lambda: nmrpa.compute_features(data))


def test_contract_digests_are_non_self_referential_and_target_is_spec_only() -> None:
    objects = nmrpa.contract_objects(); refs = nmrpa.contract_refs()
    assert refs["target_contract_sha256"] == nmrpa.digest(objects["target"])
    assert "target_value" not in json.dumps(objects)
    assert set(refs) == {"feature_contract_sha256", "target_contract_sha256", "split_contract_sha256", "decision_time_policy_sha256"}
    obj = {"a": 1}; obj["manifest_sha256"] = nmrpa.checksum_without(obj, "manifest_sha256")
    assert obj["manifest_sha256"] != nmrpa.digest(obj)


def test_real_dates_and_unsafe_roots_are_rejected(tmp_path: Path) -> None:
    data = fixture(); data["decision_date"] = "2026-08-21"
    assert_code("NMRPA_E_REAL_INPUT", lambda: nmrpa.compute_features(data))
    assert_code("NMRPA_E_OUTPUT_BOUNDARY", lambda: nmrpa.validate_output_root(ROOT / "data_tw/artifacts/nmrpa"))
    assert_code("NMRPA_E_OUTPUT_BOUNDARY", lambda: nmrpa.validate_output_root(tmp_path / "latest"))
    assert_code("NMRPA_E_OUTPUT_BOUNDARY", lambda: nmrpa.validate_output_root(ROOT / "scripts"))
    existing = tmp_path / "SYNTHETIC_EXISTING_ROOT"; existing.mkdir()
    assert_code("NMRPA_E_OUTPUT_BOUNDARY", lambda: build_candidate(existing))


def test_event_retry_collision_and_crash_recovery(tmp_path: Path) -> None:
    root = tmp_path / "SYNTHETIC_EVENT_STORE"
    body = {"contract_id": "SYNTHETIC_CONTRACT", "decision_date": "SYNTHETIC_DATE_1", "event_type": "candidate_valid", "payload_sha256": "a" * 64}
    original = nmrpa.append_business_event(root, body)
    retry = nmrpa.append_business_event(root, body)
    assert original[0]["chain_sequence"] == 1
    assert retry[0]["event_type"] == "retry_observed" and retry[0]["counter_effect"] == 0
    changed = {**body, "payload_sha256": "b" * 64}
    events = nmrpa.append_business_event(root, changed)
    assert [e["event_type"] for e in events] == ["collision_rejected", "invalidation"]
    crash = tmp_path / "SYNTHETIC_CRASH_STORE"
    result = nmrpa.append_event(crash, body, crash_phase="after_event_rename")
    assert result["recovery_required"] and nmrpa.recover(crash) == "recovered"


def test_orphan_quarantine_and_concurrent_writer(tmp_path: Path) -> None:
    root = tmp_path / "SYNTHETIC_ORPHAN_STORE"
    (root / "journals").mkdir(parents=True)
    (root / "events").mkdir()
    (root / "journals/SYNTHETIC_TX_1.json").write_text(json.dumps({"transaction_id": "SYNTHETIC_TX_1", "planned_event_hash": "a" * 64, "phase": "planned"}))
    assert_code("NMRPA_E_QUARANTINE", lambda: nmrpa.recover(root))
    assert (root / "quarantine/SYNTHETIC_TX_1.json").is_file()
    lock_root = tmp_path / "SYNTHETIC_LOCK_STORE"; lock_root.mkdir()
    lock = (lock_root / "writer.lock").open("a+b")
    import fcntl
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    body = {"contract_id": "SYNTHETIC_CONTRACT", "decision_date": "SYNTHETIC_DATE_1", "event_type": "candidate_valid", "payload_sha256": "a" * 64}
    assert_code("NMRPA_E_CONCURRENT_WRITER", lambda: nmrpa.append_event(lock_root, body))
    lock.close()


def test_maturity_append_only_and_completion_all_126(tmp_path: Path) -> None:
    history = []
    for state in ("candidate_pending", "label_pending", "matured", "sealed"):
        history.append(nmrpa.append_state(history, state))
    assert_code("NMRPA_E_STATE_TRANSITION", lambda: nmrpa.append_state(history, "matured"))
    assert_code("NMRPA_E_STATE_TRANSITION", lambda: nmrpa.append_state(history, "sealed"))
    invalidated = nmrpa.append_state(history, "invalid")
    assert invalidated["from_state"] == "sealed" and invalidated["to_state"] == "invalid"
    dates = [cohort_row(i) for i in range(1, 127)]
    anchor, store, chain_anchor = committed_completion_evidence(dates, tmp_path / "SYNTHETIC_COMPLETION_A")
    expected_anchor = nmrpa.digest(anchor)
    assert nmrpa.completion(dates, anchor, expected_anchor_sha256=expected_anchor, committed_event_store=store, committed_chain_anchor=chain_anchor)
    dates[0]["maturity_histories"]["SYNTHETIC_SYMBOL_A"] = dates[0]["maturity_histories"]["SYNTHETIC_SYMBOL_A"][:-1]
    assert not nmrpa.completion(dates, anchor, expected_anchor_sha256=expected_anchor, committed_event_store=store, committed_chain_anchor=chain_anchor)
    dates = [cohort_row(i) for i in range(1, 127)]; anchor, store, chain_anchor = committed_completion_evidence(dates, tmp_path / "SYNTHETIC_COMPLETION_B"); dates[1]["included_symbols"] = []
    assert not nmrpa.completion(dates, anchor, expected_anchor_sha256=nmrpa.digest(anchor), committed_event_store=store, committed_chain_anchor=chain_anchor)
    dates = [cohort_row(i) for i in range(1, 128)]; anchor, store, chain_anchor = committed_completion_evidence(dates, tmp_path / "SYNTHETIC_COMPLETION_C"); dates[0]["candidate_event"]["payload_sha256"] = "f" * 64
    assert not nmrpa.completion(dates, anchor, expected_anchor_sha256=nmrpa.digest(anchor), committed_event_store=store, committed_chain_anchor=chain_anchor), "day 127 cannot replace a mutated first-cohort identity"


def test_calendar_prefix_extension_and_mutation() -> None:
    prefix = ["SYNTHETIC_DATE_1", "SYNTHETIC_DATE_2"]
    assert nmrpa.calendar_extends(prefix, prefix + ["SYNTHETIC_DATE_3"])
    assert not nmrpa.calendar_extends(prefix, ["SYNTHETIC_DATE_0", "SYNTHETIC_DATE_2", "SYNTHETIC_DATE_3"])
    assert not nmrpa.calendar_extends(prefix, prefix + ["SYNTHETIC_DATE_4", "SYNTHETIC_DATE_3"])


def test_visible_status_is_date_level_redacted() -> None:
    status = nmrpa.visible_status("SYNTHETIC_CONTRACT", "SYNTHETIC_DATE_1", 1)
    aggregate = {"attempted_date_count": 1, "valid_date_count": 1, "pending_date_count": 1, "sealed_date_count": 0, "invalid_date_count": 0}
    nmrpa.validate_visible(status, aggregate)
    assert status["pending_date_count"] == "suppressed"
    leaked = {**status, "restricted_path": "SYNTHETIC_PATH"}
    assert_code("NMRPA_E_VISIBLE_LEAK", lambda: nmrpa.validate_visible(leaked, aggregate))
    exact = {**status, "pending_date_count": 1}
    assert_code("NMRPA_E_VISIBLE_LEAK", lambda: nmrpa.validate_visible(exact, aggregate))


def test_nfkc_filename_and_parquet_metadata_forbidden_content() -> None:
    assert_code("NMRPA_E_FORBIDDEN_CONTENT", lambda: nmrpa.validate_untrusted_text("ＦＵＴＵＲＥ－ＲＥＴＵＲＮ.csv"))
    assert_code("NMRPA_E_FORBIDDEN_CONTENT", lambda: nmrpa.validate_metadata({"custom": {"hidden": "Rank/IC"}}))
    nmrpa.validate_metadata({"technical": "Bollinger_position", "value": 1.25})


def test_zip_traversal_nested_and_ratio_are_rejected(tmp_path: Path) -> None:
    traversal = tmp_path / "SYNTHETIC_TRAVERSAL.zip"
    with zipfile.ZipFile(traversal, "w") as archive:
        archive.writestr("../SYNTHETIC_FILE.json", "{}")
    assert_code("NMRPA_E_ARCHIVE", lambda: nmrpa.validate_zip(traversal))
    nested = tmp_path / "SYNTHETIC_NESTED.zip"
    with zipfile.ZipFile(nested, "w") as archive:
        archive.writestr("SYNTHETIC_INNER.zip", "x")
    assert_code("NMRPA_E_ARCHIVE", lambda: nmrpa.validate_zip(nested))
    ratio = tmp_path / "SYNTHETIC_RATIO.zip"
    with zipfile.ZipFile(ratio, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("SYNTHETIC_BIG.txt", "0" * 100000)
    assert_code("NMRPA_E_ARCHIVE", lambda: nmrpa.validate_zip(ratio))


def test_exact_schema_definitions_validate_generated_artifacts(tmp_path: Path) -> None:
    out = tmp_path / "SYNTHETIC_CANDIDATE_ROOT"
    result = build_candidate(out)
    assert result["ok"] and result["feature_count"] == 78
    schema = json.loads((ROOT / "schemas/tw_policy_nmrpa2_candidate.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    mapping = {"input_snapshot": "synthetic_input_snapshot.json", "source_manifest": "source_manifest.json", "eligibility_audit": "eligibility_audit.json", "feature_candidate": "feature_candidates.json", "event": "event.json", "maturity_transition": "maturity_transitions.json", "visible_status": "visible_status.json", "forbidden_audit": "forbidden_action_audit.json"}
    for definition, name in mapping.items():
        value = json.loads((out / name).read_text())
        values = value if definition in {"feature_candidate", "maturity_transition"} else [value]
        validator = Draft202012Validator({"$ref": f"#/$defs/{definition}", "$defs": schema["$defs"]})
        assert all(not list(validator.iter_errors(item)) for item in values), definition


def test_validator_detects_tamper_and_protected_fingerprints_unchanged(tmp_path: Path) -> None:
    before = nmrpa.protected_fingerprints()
    out = tmp_path / "SYNTHETIC_CANDIDATE_ROOT"
    build_candidate(out)
    after = nmrpa.protected_fingerprints()
    assert before == after
    candidates = json.loads((out / "feature_candidates.json").read_text())
    candidates[0]["feature_values"]["MA5"] += 1
    (out / "feature_candidates.json").write_text(json.dumps(candidates))
    assert_code("NMRPA_E_CHECKSUM", lambda: validate_candidate(out))


def test_schema_root_and_nested_objects_are_exact(tmp_path: Path) -> None:
    schema = json.loads((ROOT / "schemas/tw_policy_nmrpa2_candidate.schema.json").read_text())
    validator = Draft202012Validator(schema)
    assert list(validator.iter_errors({}))
    out = tmp_path / "SYNTHETIC_SCHEMA_ROOT"
    build_candidate(out)
    event = json.loads((out / "event.json").read_text())
    event["rogue_field"] = {"nested": True}
    assert list(validator.iter_errors(event))
    candidate = json.loads((out / "feature_candidates.json").read_text())[0]
    candidate["feature_values"]["ARBITRARY_FEATURE"] = candidate["feature_values"].pop("MA5")
    assert list(validator.iter_errors(candidate))
    candidate = json.loads((out / "feature_candidates.json").read_text())[0]
    candidate["feature_values"]["qlib_rank"] = 1.5
    assert list(validator.iter_errors(candidate))


def test_validator_independently_recomputes_all_78_and_contract_refs(tmp_path: Path) -> None:
    out = tmp_path / "SYNTHETIC_RECOMPUTE_ROOT"
    build_candidate(out)
    rows = json.loads((out / "feature_candidates.json").read_text())
    rows[0]["feature_values"]["MA5"] += 999
    rows[0]["feature_row_sha256"] = nmrpa.checksum_without(rows[0], "feature_row_sha256")
    (out / "feature_candidates.json").write_text(json.dumps(rows))
    assert_code("NMRPA_E_FEATURE_RECOMPUTE", lambda: validate_candidate(out))

    out2 = tmp_path / "SYNTHETIC_CONTRACT_ROOT"
    build_candidate(out2)
    rows = json.loads((out2 / "feature_candidates.json").read_text())
    rows[0]["feature_contract_sha256"] = "d" * 64
    rows[0]["feature_row_sha256"] = nmrpa.checksum_without(rows[0], "feature_row_sha256")
    (out2 / "feature_candidates.json").write_text(json.dumps(rows))
    assert_code("NMRPA_E_FEATURE_RECOMPUTE", lambda: validate_candidate(out2))

    built = nmrpa.compute_features(fixture())
    oracle = nmrpa.independent_feature_oracle(fixture())
    for actual, expected in zip(built, oracle):
        assert set(actual["feature_values"]) == set(expected["feature_values"]) == set(nmrpa.FEATURE_NAMES)
        for name in nmrpa.FEATURE_NAMES:
            assert actual["feature_values"][name] == pytest.approx(expected["feature_values"][name], rel=1e-10, abs=1e-12)


def test_partial_absence_binds_returned_rows_sets_and_payloads() -> None:
    data = fixture()
    evidence = data["symbols"]["SYNTHETIC_SYMBOL_A"]["institutional"]["absence_evidence"]
    row = {"instrument": "SYNTHETIC_SYMBOL_B", "source_kind": "institutional", "decision_date": "SYNTHETIC_TD_120"}
    evidence.update({
        "result_class": "authoritative_complete_partial_rows",
        "returned_symbol_count": 1,
        "returned_rows": [row],
        "returned_symbol_set_sha256": nmrpa.digest(["SYNTHETIC_SYMBOL_B"]),
        "absent_symbol_set_sha256": nmrpa.digest(["SYNTHETIC_SYMBOL_A"]),
        "immutable_response_or_audit_payload": {"source_kind": "institutional", "decision_date": "SYNTHETIC_TD_120", "returned_rows": [row]},
        "immutable_response_or_audit_sha256": nmrpa.digest({"source_kind": "institutional", "decision_date": "SYNTHETIC_TD_120", "returned_rows": [row]}),
    })
    nmrpa.compute_features(data)
    evidence["returned_symbol_set_sha256"] = "d" * 64
    assert_code("NMRPA_E_ABSENCE_EVIDENCE", lambda: nmrpa.compute_features(data))
    evidence["returned_symbol_set_sha256"] = nmrpa.digest(["SYNTHETIC_SYMBOL_B"])
    evidence["immutable_response_or_audit_sha256"] = "e" * 64
    assert_code("NMRPA_E_ABSENCE_EVIDENCE", lambda: nmrpa.compute_features(data))


def test_present_source_exact_rows_missing_grid_and_denominators_fail_closed() -> None:
    data = fixture()
    dates = [f"SYNTHETIC_TD_{i:03d}" for i in range(111, 121)]
    inst = [{"date": date, "available_at": "SYNTHETIC_TIME_BEFORE_CUTOFF", "source_asof": date, "foreign_net_buy": i, "investment_trust_net_buy": i + 1, "dealer_net_buy": i + 2} for i, date in enumerate(dates)]
    margin = [{"date": date, "available_at": "SYNTHETIC_TIME_BEFORE_CUTOFF", "source_asof": date, "margin_balance": 100 + i, "margin_balance_change": 0 if i == 0 else 1, "short_balance": 50 + i, "short_balance_change": 0 if i == 0 else 1} for i, date in enumerate(dates)]
    for symbol in data["symbols"].values():
        symbol["institutional"] = {"source_state": "present", "rows": copy.deepcopy(inst), "delay_days": 0}
        symbol["margin"] = {"source_state": "present", "rows": copy.deepcopy(margin), "delay_days": 0}
    nmrpa.compute_features(data)
    broken = copy.deepcopy(data); del broken["symbols"]["SYNTHETIC_SYMBOL_A"]["institutional"]["rows"][0]["dealer_net_buy"]
    assert_code("NMRPA_E_SOURCE_SCHEMA", lambda: nmrpa.compute_features(broken))
    broken = copy.deepcopy(data); broken["symbols"]["SYNTHETIC_SYMBOL_A"]["margin"]["rows"][1]["extra"] = 1
    assert_code("NMRPA_E_SOURCE_SCHEMA", lambda: nmrpa.compute_features(broken))
    broken = copy.deepcopy(data); broken["symbols"]["SYNTHETIC_SYMBOL_A"]["institutional"]["rows"][1]["date"] = dates[0]
    assert_code("NMRPA_E_SOURCE_CONFLICT", lambda: nmrpa.compute_features(broken))
    broken = nmrpa.expand_fixture(copy.deepcopy(data)); broken["symbols"]["SYNTHETIC_SYMBOL_A"]["price"]["volume"][110] = 0
    assert_code("NMRPA_E_SOURCE_CONFLICT", lambda: nmrpa.compute_features(broken))
    broken = nmrpa.expand_fixture(copy.deepcopy(data)); broken["symbols"]["SYNTHETIC_SYMBOL_A"]["price"]["observed_close_date_grid_last20"].append("SYNTHETIC_TD_999")
    assert_code("NMRPA_E_SOURCE_SCHEMA", lambda: nmrpa.compute_features(broken))


def test_committed_chain_tamper_and_atomic_collision_recovery(tmp_path: Path) -> None:
    body = {"contract_id": "SYNTHETIC_CONTRACT", "decision_date": "SYNTHETIC_DATE_1", "event_type": "candidate_valid", "payload_sha256": "a" * 64}
    root = tmp_path / "SYNTHETIC_CHAIN_TAMPER"
    first = nmrpa.append_business_event(root, body)[0]
    event_path = next((root / "events").glob("*.json"))
    tampered = json.loads(event_path.read_text()); tampered["payload_sha256"] = "f" * 64
    event_path.write_text(json.dumps(tampered))
    assert_code("NMRPA_E_APPEND_ONLY_TAMPER", lambda: nmrpa.append_business_event(root, body))

    atomic = tmp_path / "SYNTHETIC_ATOMIC_COLLISION"
    nmrpa.append_business_event(atomic, body)
    changed = {**body, "payload_sha256": "b" * 64}
    crash = nmrpa.append_business_event(atomic, changed, crash_phase="after_event_rename")
    assert crash["recovery_required"]
    _, committed = nmrpa._verify_committed_chain(atomic)
    assert [event["event_type"] for event in committed] == ["candidate_valid"]
    assert nmrpa.recover(atomic) == "recovered"
    _, committed = nmrpa._verify_committed_chain(atomic)
    assert [event["event_type"] for event in committed] == ["candidate_valid", "collision_rejected", "invalidation"]
    assert committed[2]["trigger_event_hash"] == committed[1]["event_hash"]


def test_recovery_mismatch_quarantines_and_freezes(tmp_path: Path) -> None:
    body = {"contract_id": "SYNTHETIC_CONTRACT", "decision_date": "SYNTHETIC_DATE_1", "event_type": "candidate_valid", "payload_sha256": "a" * 64}
    root = tmp_path / "SYNTHETIC_RECOVERY_MISMATCH"
    nmrpa.append_event(root, body, crash_phase="after_event_rename")
    event_path = next((root / "events").glob("*.json"))
    event = json.loads(event_path.read_text()); event["payload_sha256"] = "b" * 64
    event_path.write_text(json.dumps(event))
    assert_code("NMRPA_E_QUARANTINE", lambda: nmrpa.recover(root))
    assert (root / "FROZEN").is_file()
    assert_code("NMRPA_E_QUARANTINE", lambda: nmrpa.append_event(root, body))


def test_illegal_rehashed_maturity_and_calendar_mutations_fail() -> None:
    state = nmrpa.append_state([], "candidate_pending")
    state["to_state"] = "matured"
    state["transition_body_sha256"] = nmrpa.checksum_without(state, "state_event_hash", "transition_body_sha256")
    state["state_event_hash"] = nmrpa.digest({"state_sequence": 1, "previous_state_hash": None, "transition_body_sha256": state["transition_body_sha256"]})
    assert_code("NMRPA_E_STATE_TRANSITION", lambda: nmrpa.validate_maturity_history([state]))

    binding = nmrpa.build_calendar_binding(nmrpa.expand_fixture(fixture()))
    nmrpa.validate_calendar_artifact(binding)
    bad = copy.deepcopy(binding); bad["full_dates"][1] = bad["full_dates"][0]; bad["full_sha256"] = nmrpa.digest(bad["full_dates"])
    assert_code("NMRPA_E_CONTRACT_DRIFT", lambda: nmrpa.validate_calendar_artifact(bad))
    bad = copy.deepcopy(binding); bad["maturity_endpoint"] = bad["full_dates"][-2]
    assert_code("NMRPA_E_MATURITY_CALENDAR", lambda: nmrpa.validate_calendar_artifact(bad))
    extended = copy.deepcopy(binding); extended["prefix_dates"][0] = "SYNTHETIC_TD_X"; extended["prefix_sha256"] = nmrpa.digest(extended["prefix_dates"])
    assert_code("NMRPA_E_CONTRACT_DRIFT", lambda: nmrpa.validate_calendar_artifact(extended, binding))


def test_forged_protected_evidence_is_rejected_even_when_rehashed(tmp_path: Path) -> None:
    out = tmp_path / "SYNTHETIC_PROTECTED_FORGE"
    build_candidate(out)
    audit = json.loads((out / "forbidden_action_audit.json").read_text())
    key = next(key for key, fingerprint in audit["protected_after"].items() if fingerprint.get("exists") is True)
    original = copy.deepcopy(audit["protected_after"][key])
    forged_sha256 = "0" * 64 if original.get("sha256") != "0" * 64 else "1" * 64
    audit["protected_after"][key] = {"exists": True, "sha256": forged_sha256}
    assert audit["protected_after"][key] != original
    audit["protected_unchanged"] = True
    audit["audit_sha256"] = nmrpa.checksum_without(audit, "audit_sha256")
    (out / "forbidden_action_audit.json").write_text(json.dumps(audit))
    assert_code("NMRPA_E_PROTECTED_BOUNDARY", lambda: validate_candidate(out))


def test_cli_build_and_readonly_validate(tmp_path: Path) -> None:
    out = tmp_path / "SYNTHETIC_CLI_ROOT"
    anchor = anchor_for(out)
    build = subprocess.run([sys.executable, str(ROOT / "scripts/build_tw_policy_nmrpa2_isolated_candidate.py"), "--fixture", str(FIXTURE), "--output-root", str(out), "--expected-input-sha256", EXPECTED_INPUT_SHA256, "--chain-anchor", str(anchor), "--json"], cwd=ROOT, text=True, capture_output=True)
    assert build.returncode == 0, build.stderr + build.stdout
    validate = subprocess.run([sys.executable, str(ROOT / "scripts/validate_tw_policy_nmrpa_candidate.py"), "--candidate-root", str(out), "--expected-input-sha256", EXPECTED_INPUT_SHA256, "--expected-chain-anchor", str(anchor), "--json"], cwd=ROOT, text=True, capture_output=True)
    assert validate.returncode == 0
    assert json.loads(validate.stdout)["real_accumulation_started"] is False


def test_external_input_anchor_rejects_unknown_and_fully_resigned_snapshot(tmp_path: Path) -> None:
    out = tmp_path / "SYNTHETIC_INPUT_ANCHOR"
    build_candidate(out)
    snapshot_path = out / "synthetic_input_snapshot.json"
    snapshot = json.loads(snapshot_path.read_text())
    snapshot["symbols"]["SYNTHETIC_SYMBOL_A"]["UNBOUND_INPUT_FIELD"] = 1
    snapshot_path.write_text(json.dumps(snapshot))
    manifest = nmrpa.build_source_manifest(snapshot)
    (out / "source_manifest.json").write_text(json.dumps(manifest))
    assert_code("NMRPA_E_INPUT_SCHEMA", lambda: validate_candidate(out))

    out2 = tmp_path / "SYNTHETIC_INPUT_RESIGN"
    build_candidate(out2)
    snapshot = json.loads((out2 / "synthetic_input_snapshot.json").read_text())
    snapshot["symbols"]["SYNTHETIC_SYMBOL_A"]["score"] = 9.0
    (out2 / "synthetic_input_snapshot.json").write_text(json.dumps(snapshot))
    candidates = nmrpa.compute_features(snapshot)
    for name, value in (
        ("source_manifest.json", nmrpa.build_source_manifest(snapshot)),
        ("feature_candidates.json", candidates),
        ("eligibility_audit.json", nmrpa.build_eligibility(snapshot, candidates)),
    ):
        (out2 / name).write_text(json.dumps(value))
    assert_code("NMRPA_E_INPUT_ANCHOR", lambda: validate_candidate(out2))


def test_committed_journal_orphan_and_numeric_transaction_ordering(tmp_path: Path) -> None:
    body = {"contract_id": "SYNTHETIC_CONTRACT", "decision_date": "SYNTHETIC_DATE_1", "event_type": "candidate_valid", "payload_sha256": "a" * 64}
    tamper = tmp_path / "SYNTHETIC_JOURNAL_TAMPER"
    nmrpa.append_event(tamper, body)
    journal_path = next((tamper / "journals").glob("*.json"))
    journal = json.loads(journal_path.read_text())
    journal["planned_event_hashes"][0] = "f" * 64
    journal_path.write_text(json.dumps(journal))
    assert_code("NMRPA_E_APPEND_ONLY_TAMPER", lambda: nmrpa._verify_committed_chain(tamper))

    orphan = tmp_path / "SYNTHETIC_UNINDEXED_EVENT"
    nmrpa.append_event(orphan, body)
    rogue = orphan / "events" / f"99999999_{'f' * 64}.json"
    rogue.write_text("{}")
    assert_code("NMRPA_E_APPEND_ONLY_TAMPER", lambda: nmrpa._verify_committed_chain(orphan))

    long_store = tmp_path / "SYNTHETIC_130_TRANSACTIONS"
    for i in range(130):
        nmrpa.append_event(long_store, {**body, "decision_date": f"SYNTHETIC_DATE_{i:03d}", "payload_sha256": f"{i:064x}"})
    index, events = nmrpa._verify_committed_chain(long_store)
    assert index["head_sequence"] == len(events) == 130


@pytest.mark.parametrize("phase", ["after_journal", "after_event_rename", "after_index", "after_marker"])
def test_all_single_event_crash_phases_recover(phase: str, tmp_path: Path) -> None:
    body = {"contract_id": "SYNTHETIC_CONTRACT", "decision_date": "SYNTHETIC_DATE_1", "event_type": "candidate_valid", "payload_sha256": "a" * 64}
    root = tmp_path / f"SYNTHETIC_CRASH_{phase.upper()}"
    result = nmrpa.append_event(root, body, crash_phase=phase)
    assert result["recovery_required"]
    assert nmrpa.recover(root) == "recovered"
    assert nmrpa._verify_committed_chain(root)[0]["head_sequence"] == 1


def test_multi_event_partial_rename_recovers_atomically(tmp_path: Path) -> None:
    body = {"contract_id": "SYNTHETIC_CONTRACT", "decision_date": "SYNTHETIC_DATE_1", "event_type": "candidate_valid", "payload_sha256": "a" * 64}
    root = tmp_path / "SYNTHETIC_PARTIAL_RENAME"
    nmrpa.append_business_event(root, body)
    result = nmrpa.append_business_event(root, {**body, "payload_sha256": "b" * 64}, crash_phase="after_event_rename_1")
    assert result["recovery_required"] and nmrpa.recover(root) == "recovered"
    _, events = nmrpa._verify_committed_chain(root)
    assert [event["event_type"] for event in events] == ["candidate_valid", "collision_rejected", "invalidation"]


def test_exact_source_time_dates_asof_delay_grid_and_partial_payload() -> None:
    base = fixture()
    base["calendar"]["available_at"] = "SYNTHETIC_TIME_UNKNOWN_LATE"
    assert_code("NMRPA_E_PIT", lambda: nmrpa.compute_features(base))
    base = fixture(); base["symbols"]["SYNTHETIC_SYMBOL_A"]["available_at"] = "SYNTHETIC_TIME_AFTER_CUTOFF"
    assert_code("NMRPA_E_PIT", lambda: nmrpa.compute_features(base))

    dates = [f"SYNTHETIC_TD_{i:03d}" for i in range(111, 121)]
    inst = [{"date": date, "available_at": "SYNTHETIC_TIME_BEFORE_CUTOFF", "source_asof": date, "foreign_net_buy": i, "investment_trust_net_buy": i + 1, "dealer_net_buy": i + 2} for i, date in enumerate(dates)]
    margin = [{"date": date, "available_at": "SYNTHETIC_TIME_BEFORE_CUTOFF", "source_asof": date, "margin_balance": 100 + i, "margin_balance_change": 0 if i == 0 else 1, "short_balance": 50 + i, "short_balance_change": 0 if i == 0 else 1} for i, date in enumerate(dates)]
    present = fixture()
    for symbol in present["symbols"].values():
        symbol["institutional"] = {"source_state": "present", "rows": copy.deepcopy(inst), "delay_days": 0}
        symbol["margin"] = {"source_state": "present", "rows": copy.deepcopy(margin), "delay_days": 0}
    wrong = copy.deepcopy(present); wrong["symbols"]["SYNTHETIC_SYMBOL_A"]["institutional"]["rows"][0]["source_asof"] = "SYNTHETIC_TD_999"
    assert_code("NMRPA_E_SOURCE_CONFLICT", lambda: nmrpa.compute_features(wrong))
    wrong = copy.deepcopy(present); wrong["symbols"]["SYNTHETIC_SYMBOL_A"]["institutional"]["delay_days"] = 1
    assert_code("NMRPA_E_SOURCE_CONFLICT", lambda: nmrpa.compute_features(wrong))
    wrong = copy.deepcopy(present)
    for row, i in zip(wrong["symbols"]["SYNTHETIC_SYMBOL_A"]["institutional"]["rows"], range(1, 11)):
        row["date"] = row["source_asof"] = f"SYNTHETIC_TD_{i:03d}"
    assert_code("NMRPA_E_SOURCE_COVERAGE", lambda: nmrpa.compute_features(wrong))
    wrong = nmrpa.expand_fixture(fixture())
    wrong["symbols"]["SYNTHETIC_SYMBOL_A"]["price"]["expected_date_grid_last20"] = wrong["symbols"]["SYNTHETIC_SYMBOL_A"]["price"]["expected_date_grid_last20"][-5:]
    wrong["symbols"]["SYNTHETIC_SYMBOL_A"]["price"]["observed_close_date_grid_last20"] = wrong["symbols"]["SYNTHETIC_SYMBOL_A"]["price"]["observed_close_date_grid_last20"][-5:]
    assert_code("NMRPA_E_SOURCE_SCHEMA", lambda: nmrpa.compute_features(wrong))

    partial = fixture()
    evidence = partial["symbols"]["SYNTHETIC_SYMBOL_A"]["institutional"]["absence_evidence"]
    row = {"instrument": "SYNTHETIC_SYMBOL_B", "source_kind": "institutional", "decision_date": "SYNTHETIC_TD_120"}
    evidence.update({"result_class": "authoritative_complete_partial_rows", "returned_symbol_count": 1, "returned_rows": [row], "returned_symbol_set_sha256": nmrpa.digest(["SYNTHETIC_SYMBOL_B"]), "absent_symbol_set_sha256": nmrpa.digest(["SYNTHETIC_SYMBOL_A"])})
    evidence["immutable_response_or_audit_payload"] = {"source_kind": "institutional", "decision_date": "SYNTHETIC_TD_120", "returned_rows": []}
    evidence["immutable_response_or_audit_sha256"] = nmrpa.digest(evidence["immutable_response_or_audit_payload"])
    assert_code("NMRPA_E_ABSENCE_EVIDENCE", lambda: nmrpa.compute_features(partial))


def test_conditional_event_visible_maturity_and_external_chain_anchor(tmp_path: Path) -> None:
    schema = json.loads((ROOT / "schemas/tw_policy_nmrpa2_candidate.schema.json").read_text())
    event_validator = Draft202012Validator({"$ref": "#/$defs/event", "$defs": schema["$defs"]})
    out = tmp_path / "SYNTHETIC_CONDITIONAL"
    build_candidate(out)
    event = json.loads((out / "event.json").read_text())
    event["original_event_hash"] = "a" * 64
    event["counter_effect"] = 0
    assert list(event_validator.iter_errors(event))
    status = nmrpa.visible_status("SYNTHETIC_CONTRACT", "SYNTHETIC_DATE_1", 20)
    status["valid_decision_date_count_bucket"] = "20_999"
    aggregate = {"attempted_date_count": 20, "valid_date_count": 20, "pending_date_count": 20, "sealed_date_count": 0, "invalid_date_count": 0}
    assert_code("NMRPA_E_VISIBLE_LEAK", lambda: nmrpa.validate_visible(status, aggregate))

    transitions = json.loads((out / "maturity_transitions.json").read_text())
    candidates = json.loads((out / "feature_candidates.json").read_text())
    calendar = json.loads((out / "source_manifest.json").read_text())["calendar_binding"]
    assert len(candidates) == len(transitions) == 2
    assert_code("NMRPA_E_STATE_TRANSITION", lambda: nmrpa.validate_maturity_set(transitions[:1], candidates, calendar))

    store = out / "event_store"
    for directory in ("events", "journals", "commits"):
        for path in (store / directory).glob("*.json"):
            path.unlink()
    (store / "chain_index.json").write_text(json.dumps(nmrpa._empty_index()))
    assert_code("NMRPA_E_CHAIN_ANCHOR", lambda: nmrpa.verify_external_chain_anchor(store, anchor_for(out)))


def test_completion_rejects_126_empty_symbol_dates_and_day127_replacement(tmp_path: Path) -> None:
    rows = [cohort_row(i) for i in range(1, 127)]
    anchor, store, chain_anchor = committed_completion_evidence(rows, tmp_path / "SYNTHETIC_EMPTY_COHORT")
    for row in rows:
        row["included_symbols"] = []
        row["maturity_histories"] = {}
    assert not nmrpa.completion(rows, anchor, expected_anchor_sha256=nmrpa.digest(anchor), committed_event_store=store, committed_chain_anchor=chain_anchor)
    rows = [cohort_row(i) for i in range(1, 128)]
    anchor, store, chain_anchor = committed_completion_evidence(rows, tmp_path / "SYNTHETIC_DAY127_COHORT")
    rows[0]["candidate_event"]["payload_sha256"] = "e" * 64
    assert not nmrpa.completion(rows, anchor, expected_anchor_sha256=nmrpa.digest(anchor), committed_event_store=store, committed_chain_anchor=chain_anchor)


def test_completion_cross_binds_external_candidate_source_acl_and_maturity(tmp_path: Path) -> None:
    rows = [cohort_row(i) for i in range(1, 127)]
    anchor, store, chain_anchor = committed_completion_evidence(rows, tmp_path / "SYNTHETIC_CROSS_BIND")
    expected_anchor = nmrpa.digest(anchor)

    replaced = copy.deepcopy(rows)
    row = replaced[0]
    row["included_symbols"] = ["SYNTHETIC_SYMBOL_B"]
    identity = {
        "contract_id": "SYNTHETIC_CONTRACT", "decision_date": row["decision_identity"],
        "instrument": "SYNTHETIC_SYMBOL_B", "candidate_sha256": row["candidate_set"][0]["candidate_sha256"],
        "calendar_prefix_sha256": row["calendar_binding"]["prefix_sha256"],
        "calendar_full_sha256": row["calendar_binding"]["full_sha256"],
        "maturity_endpoint": row["calendar_binding"]["maturity_endpoint"],
    }
    history = []
    for state in ("candidate_pending", "label_pending", "matured", "sealed"):
        history.append(nmrpa.append_state(history, state, identity=identity))
    row["maturity_histories"] = {"SYNTHETIC_SYMBOL_B": history}
    assert not nmrpa.completion(replaced, anchor, expected_anchor_sha256=expected_anchor, committed_event_store=store, committed_chain_anchor=chain_anchor), "symbol replacement cannot be repaired by re-signing maturity"

    replaced = copy.deepcopy(rows)
    row = replaced[0]
    new_sha = nmrpa.digest({"forged": "candidate"})
    row["candidate_set"] = [{"instrument": "SYNTHETIC_SYMBOL_A", "candidate_sha256": new_sha}]
    payload_sha = nmrpa.digest(row["candidate_set"])
    row["candidate_event"] = nmrpa._new_event({"contract_id": "SYNTHETIC_CONTRACT", "decision_date": row["decision_identity"], "event_type": "candidate_valid", "payload_sha256": payload_sha}, 1, None)
    row["eligibility_audit"]["candidate_set_sha256"] = payload_sha
    row["eligibility_audit"]["eligibility_sha256"] = nmrpa.checksum_without(row["eligibility_audit"], "eligibility_sha256")
    assert not nmrpa.completion(replaced, anchor, expected_anchor_sha256=expected_anchor, committed_event_store=store, committed_chain_anchor=chain_anchor), "locally re-signed candidate event cannot replace external sequence anchor"

    replaced = copy.deepcopy(rows)
    row = replaced[0]
    identity = copy.deepcopy(row["maturity_histories"]["SYNTHETIC_SYMBOL_A"][0])
    identity = {key: identity[key] for key in ("contract_id", "decision_date", "instrument", "candidate_sha256", "calendar_prefix_sha256", "calendar_full_sha256", "maturity_endpoint")}
    identity["candidate_sha256"] = "f" * 64
    history = []
    for state in ("candidate_pending", "label_pending", "matured", "sealed"):
        history.append(nmrpa.append_state(history, state, identity=identity))
    row["maturity_histories"]["SYNTHETIC_SYMBOL_A"] = history
    assert not nmrpa.completion(replaced, anchor, expected_anchor_sha256=expected_anchor, committed_event_store=store, committed_chain_anchor=chain_anchor), "maturity checksum must exist in committed candidate set"

    replaced = copy.deepcopy(rows)
    row = replaced[0]
    row["source_manifest"]["external_input_sha256"] = "e" * 64
    row["source_manifest"]["manifest_sha256"] = nmrpa.checksum_without(row["source_manifest"], "manifest_sha256")
    row["eligibility_audit"]["source_manifest_sha256"] = row["source_manifest"]["manifest_sha256"]
    row["eligibility_audit"]["eligibility_sha256"] = nmrpa.checksum_without(row["eligibility_audit"], "eligibility_sha256")
    assert not nmrpa.completion(replaced, anchor, expected_anchor_sha256=expected_anchor, committed_event_store=store, committed_chain_anchor=chain_anchor), "source cannot replace package-external input anchor"

    replaced = copy.deepcopy(rows)
    row = replaced[0]
    row["acl_audit"] = {"protected_unchanged": True, "synthetic_only": True}
    row["acl_audit"]["audit_sha256"] = nmrpa.checksum_without(row["acl_audit"], "audit_sha256")
    assert not nmrpa.completion(replaced, anchor, expected_anchor_sha256=expected_anchor, committed_event_store=store, committed_chain_anchor=chain_anchor), "ACL boolean cannot replace exact fingerprint evidence"

    resigned_rows = copy.deepcopy(rows)
    resigned_anchor = completion_anchor(resigned_rows, json.loads(chain_anchor.read_text()))
    resigned_anchor["protected_fingerprint_set"] = {"SYNTHETIC_FORGED": {"exists": True, "sha256": "a" * 64}}
    resigned_anchor["anchor_sha256"] = nmrpa.checksum_without(resigned_anchor, "anchor_sha256")
    assert not nmrpa.completion(resigned_rows, resigned_anchor, expected_anchor_sha256=expected_anchor, committed_event_store=store, committed_chain_anchor=chain_anchor), "local anchor re-sign cannot replace external expected digest"


def test_completion_rejects_self_signed_events_without_committed_store(tmp_path: Path) -> None:
    rows = [cohort_row(i) for i in range(1, 127)]
    fake_chain_anchor = nmrpa.chain_anchor({"head_sequence": 126, "head_hash": rows[-1]["candidate_event"]["event_hash"], "events": []})
    anchor = completion_anchor(rows, fake_chain_anchor)
    assert not nmrpa.completion(rows, anchor, expected_anchor_sha256=nmrpa.digest(anchor))


@pytest.mark.parametrize("damage", ["marker", "journal", "index", "event", "chain_anchor"])
def test_completion_fails_closed_on_committed_store_damage(damage: str, tmp_path: Path) -> None:
    rows = [cohort_row(i) for i in range(1, 127)]
    anchor, store, chain_anchor = committed_completion_evidence(rows, tmp_path / f"SYNTHETIC_STORE_DAMAGE_{damage.upper()}")
    if damage == "marker":
        next((store / "commits").glob("*.json")).unlink()
    elif damage == "journal":
        path = next((store / "journals").glob("*.json"))
        value = json.loads(path.read_text())
        value["planned_event_hashes"][0] = "f" * 64
        path.write_text(json.dumps(value))
    elif damage == "index":
        (store / "chain_index.json").unlink()
    elif damage == "event":
        path = next((store / "events").glob("*.json"))
        value = json.loads(path.read_text())
        value["payload_sha256"] = "e" * 64
        path.write_text(json.dumps(value))
    else:
        value = json.loads(chain_anchor.read_text())
        value["head_sequence"] -= 1
        value["anchor_sha256"] = nmrpa.checksum_without(value, "anchor_sha256")
        chain_anchor.write_text(json.dumps(value))
    assert not nmrpa.completion(rows, anchor, expected_anchor_sha256=nmrpa.digest(anchor), committed_event_store=store, committed_chain_anchor=chain_anchor)


def test_completion_rejects_valid_self_hash_not_present_in_committed_chain(tmp_path: Path) -> None:
    rows = [cohort_row(i) for i in range(1, 127)]
    anchor, store, chain_anchor = committed_completion_evidence(rows, tmp_path / "SYNTHETIC_DETACHED_EVENT")
    detached = copy.deepcopy(rows)
    original = detached[0]["candidate_event"]
    body = {key: value for key, value in original.items() if key not in {"chain_sequence", "previous_event_hash", "event_body_sha256", "event_hash"}}
    detached[0]["candidate_event"] = nmrpa._new_event(body, 999, None)
    assert nmrpa._event_hash_valid(detached[0]["candidate_event"])
    assert not nmrpa.completion(detached, anchor, expected_anchor_sha256=nmrpa.digest(anchor), committed_event_store=store, committed_chain_anchor=chain_anchor)


def test_completion_replay_retry_does_not_count_and_frozen_invalidation_fails(tmp_path: Path) -> None:
    retry_rows = [cohort_row(i) for i in range(1, 127)]
    retry_root = tmp_path / "SYNTHETIC_RETRY_REPLAY"
    store = retry_root / "event_store"
    for directory in (store / "events", store / "journals", store / "commits"):
        directory.mkdir(parents=True, exist_ok=True)
    bodies = [{key: value for key, value in row["candidate_event"].items() if key not in {"chain_sequence", "previous_event_hash", "event_body_sha256", "event_hash"}} for row in retry_rows]
    first = nmrpa._append_transaction_locked(store, bodies[:125])
    for row, event in zip(retry_rows[:125], first):
        row["candidate_event"] = event
    retry = nmrpa.append_business_event(store, bodies[0])
    assert isinstance(retry, list) and retry[0]["event_type"] == "retry_observed"
    assert nmrpa._replay_committed_completion_cohort(nmrpa._verify_committed_chain(store)[1]) is None
    retry_rows[125]["candidate_event"] = nmrpa.append_event(store, bodies[125])
    chain_anchor_path = retry_root / "EXTERNAL_CHAIN_ANCHOR.json"
    chain_anchor_value = nmrpa.write_external_chain_anchor(store, chain_anchor_path)
    anchor = completion_anchor(retry_rows, chain_anchor_value)
    assert anchor["frozen_at_chain_sequence"] == 127
    assert nmrpa.completion(retry_rows, anchor, expected_anchor_sha256=nmrpa.digest(anchor), committed_event_store=store, committed_chain_anchor=chain_anchor_path)

    invalid_rows = [cohort_row(i) for i in range(1, 128)]
    invalid_anchor, invalid_store, invalid_chain_anchor = committed_completion_evidence(invalid_rows[:126], tmp_path / "SYNTHETIC_FROZEN_INVALIDATION")
    original_body = {key: value for key, value in invalid_rows[0]["candidate_event"].items() if key not in {"chain_sequence", "previous_event_hash", "event_body_sha256", "event_hash"}}
    changed = {**original_body, "payload_sha256": "d" * 64}
    collision = nmrpa.append_business_event(invalid_store, changed)
    assert isinstance(collision, list) and [event["event_type"] for event in collision] == ["collision_rejected", "invalidation"]
    row127_body = {key: value for key, value in invalid_rows[126]["candidate_event"].items() if key not in {"chain_sequence", "previous_event_hash", "event_body_sha256", "event_hash"}}
    invalid_rows[126]["candidate_event"] = nmrpa.append_event(invalid_store, row127_body)
    invalid_chain_anchor.unlink()
    invalid_chain_value = nmrpa.write_external_chain_anchor(invalid_store, invalid_chain_anchor)
    invalid_anchor = completion_anchor(invalid_rows, invalid_chain_value)
    assert not nmrpa.completion(invalid_rows, invalid_anchor, expected_anchor_sha256=nmrpa.digest(invalid_anchor), committed_event_store=invalid_store, committed_chain_anchor=invalid_chain_anchor)


@pytest.mark.parametrize("mutation", ["missing_required", "unknown_field", "contract_digest"])
def test_completion_rejects_fully_committed_resigned_schema_invalid_event(mutation: str, tmp_path: Path) -> None:
    rows = [cohort_row(i) for i in range(1, 127)]
    event = rows[0]["candidate_event"]
    body = {key: value for key, value in event.items() if key not in {"chain_sequence", "previous_event_hash", "event_body_sha256", "event_hash"}}
    if mutation == "missing_required":
        body.pop("attempt_id")
        expected_code = "NMRPA_E_SCHEMA"
    elif mutation == "unknown_field":
        body["unknown_event_field"] = "SYNTHETIC_FORGED"
        expected_code = "NMRPA_E_SCHEMA"
    else:
        body["feature_contract_sha256"] = "f" * 64
        expected_code = "NMRPA_E_CONTRACT_DRIFT"
    rows[0]["candidate_event"] = nmrpa._new_event(body, 1, None)
    assert_code(expected_code, lambda: nmrpa._validate_exact_event_schema(rows[0]["candidate_event"]))
    anchor, store, chain_anchor = committed_completion_evidence(rows, tmp_path / f"SYNTHETIC_EVENT_PROBE_{mutation.upper()}")
    assert not nmrpa.completion(
        rows,
        anchor,
        expected_anchor_sha256=nmrpa.digest(anchor),
        committed_event_store=store,
        committed_chain_anchor=chain_anchor,
    )


@pytest.mark.parametrize(
    ("event_type", "exclusive_fields"),
    [
        ("retry_observed", {"rejected_payload_sha256": "e" * 64}),
        ("collision_rejected", {"original_business_key": ["SYNTHETIC_CONTRACT", "SYNTHETIC_DECISION_001", "candidate_valid"]}),
        ("invalidation", {"original_event_hash": "e" * 64}),
    ],
)
def test_completion_rejects_committed_event_with_cross_type_exclusive_field(
    event_type: str,
    exclusive_fields: dict,
    tmp_path: Path,
) -> None:
    rows = [cohort_row(i) for i in range(1, 127)]
    anchor, store, chain_anchor = committed_completion_evidence(rows, tmp_path / f"SYNTHETIC_EXCLUSIVE_{event_type.upper()}")
    original = rows[0]["candidate_event"]
    common = candidate_event_body(original["decision_date"], original["payload_sha256"])
    common["event_type"] = event_type
    if event_type == "retry_observed":
        common.update({"original_event_hash": original["event_hash"], "original_business_key": ["SYNTHETIC_CONTRACT", original["decision_date"], "candidate_valid"], "counter_effect": 0})
    elif event_type == "collision_rejected":
        common.update({"original_event_hash": original["event_hash"], "rejected_payload_sha256": "d" * 64, "counter_effect": 0})
    else:
        common.update({"invalidates_event_hash": original["event_hash"], "trigger_event_hash": "d" * 64, "counter_effect": -1})
    common.update(exclusive_fields)
    committed = nmrpa._append_transaction_locked(store, [common])
    assert isinstance(committed, list)
    assert_code("NMRPA_E_SCHEMA", lambda: nmrpa._validate_exact_event_schema(committed[0]))
    chain_anchor.unlink()
    chain_anchor_value = nmrpa.write_external_chain_anchor(store, chain_anchor)
    anchor = completion_anchor(rows, chain_anchor_value)
    assert not nmrpa.completion(
        rows,
        anchor,
        expected_anchor_sha256=nmrpa.digest(anchor),
        committed_event_store=store,
        committed_chain_anchor=chain_anchor,
    )


def test_visible_status_bucket_count_and_state_consistency() -> None:
    aggregate20 = {"attempted_date_count": 20, "valid_date_count": 20, "pending_date_count": 20, "sealed_date_count": 0, "invalid_date_count": 0}
    status20 = nmrpa.visible_status("SYNTHETIC_CONTRACT", "SYNTHETIC_DATE_20", 20)
    nmrpa.validate_visible(status20, aggregate20)

    wrong = {**status20, "valid_decision_date_count_bucket": "25_29"}
    assert_code("NMRPA_E_VISIBLE_COUNT", lambda: nmrpa.validate_visible(wrong, aggregate20))
    wrong = {**status20, "remaining_valid_dates": 101}
    assert_code("NMRPA_E_VISIBLE_COUNT", lambda: nmrpa.validate_visible(wrong, aggregate20))
    impossible = {"attempted_date_count": 20, "valid_date_count": 20, "pending_date_count": 999, "sealed_date_count": 0, "invalid_date_count": 0}
    assert_code("NMRPA_E_VISIBLE_COUNT", lambda: nmrpa.validate_visible(status20, impossible))
    impossible_total = {**aggregate20, "invalid_date_count": 1}
    assert_code("NMRPA_E_VISIBLE_COUNT", lambda: nmrpa.validate_visible(status20, impossible_total))
    for field, value in (("maturity_wait_state", "complete"), ("readiness_state", "isolated_complete"), ("integrity_state", "synthetic_invalid")):
        wrong = {**status20, field: value}
        assert_code("NMRPA_E_VISIBLE_COUNT", lambda wrong=wrong: nmrpa.validate_visible(wrong, aggregate20))

    small = nmrpa.visible_status("SYNTHETIC_CONTRACT", "SYNTHETIC_DATE_1", 1)
    exposed = {**small, "pending_date_count": 1}
    aggregate1 = {"attempted_date_count": 1, "valid_date_count": 1, "pending_date_count": 1, "sealed_date_count": 0, "invalid_date_count": 0}
    assert_code("NMRPA_E_VISIBLE_LEAK", lambda: nmrpa.validate_visible(exposed, aggregate1))

    complete = nmrpa.visible_status("SYNTHETIC_CONTRACT", "SYNTHETIC_DATE_126", 126)
    complete.update({"pending_date_count": 0, "sealed_date_count": 126, "maturity_wait_state": "complete", "readiness_state": "isolated_complete"})
    aggregate126 = {"attempted_date_count": 126, "valid_date_count": 126, "pending_date_count": 0, "sealed_date_count": 126, "invalid_date_count": 0}
    nmrpa.validate_visible(complete, aggregate126)
