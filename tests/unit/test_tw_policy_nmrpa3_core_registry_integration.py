from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import tw_policy_nmrpa3_core_registry as core
import tw_policy_nmrpa3_immutable_binding_writer as writer
from tw_policy_nmrpa3_real_trust_bootstrap import digest


SUPPORT_PATH = Path(__file__).with_name("test_tw_policy_nmrpa3_core_registry.py")
SPEC = importlib.util.spec_from_file_location("crpg2_core_test_support", SUPPORT_PATH)
assert SPEC is not None and SPEC.loader is not None
support = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(support)


def fresh_chain(root: Path):
    root.mkdir()
    return support.chain.__wrapped__(root)


def public_resolve(chain, ref):
    root, descriptor, capability, _, bootstrap, *_ = chain
    return core.resolve_commit_ref(
        ref,
        descriptor,
        descriptor["descriptor_sha256"],
        project_root=root.resolve(),
        capability=capability,
        synthetic_bootstrap_verification_public_key=support.key_bytes(bootstrap),
    )


def assert_code(code: str, callback) -> None:
    with pytest.raises((core.ContractError, writer.ContractError)) as exc:
        callback()
    assert exc.value.code == code


def test_full_role_pack_all_refs_advanced_history_and_two_store_six_log_closure(tmp_path, monkeypatch):
    chain = fresh_chain(tmp_path / "role-pack")
    captured = [chain[7], chain[9], chain[11]]
    original_commit_intent = support.commit_intent

    def capturing_commit(*args, **kwargs):
        ref = original_commit_intent(*args, **kwargs)
        captured.append(ref)
        return ref

    monkeypatch.setattr(support, "commit_intent", capturing_commit)
    support.test_six_branch_role_pack_uses_distinct_identity_credential_and_keys(chain)
    support.test_same_log_advanced_head_keeps_historical_ref_trusted(chain)

    assert {ref["event_kind"] for ref in captured} == {
        "principal_registered",
        "identity_registered",
        "credential_activated",
        "trusted_service_registered",
        "publication_authority_registered",
        "capture_recorder_registered",
    }
    assert len(captured) == 13
    assert max(ref["sequence"] for ref in captured) >= 4
    for ref in captured:
        resolved = public_resolve(chain, ref)
        assert resolved["status"] == "PHYSICALLY_TRUSTED_COMMIT_REF"
        assert resolved["payload_bytes_read"] == 0

    root, descriptor, *_ = chain
    histories = [json.loads((root / row["historical_heads_locator"]).read_text()) for row in descriptor["fixed_logs"]]
    assert len(histories) == 6
    assert all(history[0]["sequence"] == 0 and history[-1]["sequence"] >= 1 for history in histories)
    assert any(history[-1]["sequence"] >= 2 for history in histories)
    stores = {row["store_kind"]: root / row["project_relative_path"] for row in descriptor["trust_stores"]}
    assert any(stores["principal_identity_credential_registry_stores"].glob("*.json"))
    assert any(stores["trusted_actor_registry_stores"].glob("*.json"))


def test_public_v1_v5_order_and_v3_cannot_mask_v4_signature_failure(tmp_path):
    root = tmp_path / "v1-v5"
    root.mkdir()
    descriptor, capability, _, bootstrap, intent = support._fresh_principal_case(root)
    public_key = support.key_bytes(bootstrap)
    common = dict(
        project_root=root.resolve(),
        capability=capability,
        synthetic_bootstrap_verification_public_key=public_key,
    )

    assert core.validate_intent(intent, descriptor, descriptor["descriptor_sha256"], **common)["status"] == "PHYSICALLY_TRUSTED_INTENT"
    plan = core.plan(intent, descriptor, descriptor["descriptor_sha256"], **common)
    assert core.validate_plan(plan, descriptor, descriptor["descriptor_sha256"])["status"] == "LOGICALLY_VALID_UNTRUSTED_PLAN"

    forged = copy.deepcopy(plan)
    forged["signed_record"]["signature"]["signature_hex"] = "0" * 128
    forged["signed_record"]["signed_record_sha256"] = digest(
        {key: value for key, value in forged["signed_record"].items() if key != "signed_record_sha256"},
        "nmrpa.core_registry.signed_record.digest.v1",
    )
    forged["journal"]["signed_record_sha256"] = forged["signed_record"]["signed_record_sha256"]
    forged["journal"]["synthetic_commit_signature"] = support.signature(
        bootstrap,
        core._attestation_digest(
            forged["journal"], "synthetic_commit_signature", "journal_sha256",
            "nmrpa.core_registry.transaction_journal.commit_attestation.v1",
        ),
    )
    forged["journal"]["journal_sha256"] = digest(
        {key: value for key, value in forged["journal"].items() if key != "journal_sha256"},
        "nmrpa.core_registry.transaction_journal.digest.v1",
    )
    forged["commit_marker"].update({
        "signed_record_sha256": forged["signed_record"]["signed_record_sha256"],
        "journal_sha256": forged["journal"]["journal_sha256"],
    })
    forged["commit_marker"]["synthetic_commit_signature"] = support.signature(
        bootstrap,
        core._attestation_digest(
            forged["commit_marker"], "synthetic_commit_signature", "commit_sha256",
            "nmrpa.core_registry.commit_marker.commit_attestation.v1",
        ),
    )
    forged["commit_marker"]["commit_sha256"] = digest(
        {key: value for key, value in forged["commit_marker"].items() if key != "commit_sha256"},
        "nmrpa.core_registry.commit_marker.digest.v1",
    )
    forged["new_head"].update({
        "signed_record_sha256": forged["signed_record"]["signed_record_sha256"],
        "journal_sha256": forged["journal"]["journal_sha256"],
        "commit_sha256": forged["commit_marker"]["commit_sha256"],
    })
    forged["new_head"]["head_sha256"] = digest(
        {key: value for key, value in forged["new_head"].items() if key != "head_sha256"},
        "nmrpa.core_registry.committed_head.digest.v1",
    )
    forged["new_history"][-1] = forged["new_head"]
    forged["plan_sha256"] = digest(
        {key: value for key, value in forged.items() if key != "plan_sha256"},
        "nmrpa.core_registry.transaction_plan.synthetic.v1",
    )
    assert core.validate_plan(forged, descriptor, descriptor["descriptor_sha256"])["status"] == "LOGICALLY_VALID_UNTRUSTED_PLAN"
    assert_code(
        "NMRPA_CRPG_SIGNATURE_INVALID",
        lambda: core.commit(forged, descriptor, descriptor["descriptor_sha256"], **common),
    )

    committed = core.commit(plan, descriptor, descriptor["descriptor_sha256"], **common)
    assert committed["status"] == "PHYSICALLY_COMMITTED"
    assert core.resolve_commit_ref(
        committed["commit_ref"], descriptor, descriptor["descriptor_sha256"], **common,
    )["status"] == "PHYSICALLY_TRUSTED_COMMIT_REF"


def test_target_completes_fresh_authoritative_v4_before_exact_target_cache_hit(tmp_path, monkeypatch):
    chain = fresh_chain(tmp_path / "cache-order")
    target = chain[11]
    target_key = (target["logical_name"], target["sequence"], target["transaction_id"])
    observations = []
    original = core._validate_physical_bundle

    def traced(head, closure, bootstrap_key, validated, stack):
        key = (head["logical_name"], head["sequence"], head["transaction_id"])
        before = key in validated
        result = original(head, closure, bootstrap_key, validated, stack)
        observations.append((key, before, key in validated))
        return result

    monkeypatch.setattr(core, "_validate_physical_bundle", traced)
    assert public_resolve(chain, target)["status"] == "PHYSICALLY_TRUSTED_COMMIT_REF"

    target_events = [event for event in observations if event[0] == target_key]
    assert any(before is False and after is True for _, before, after in target_events)
    assert target_events[-1] == (target_key, True, True)
    exit_order = [key for key, before, after in observations if not before and after]
    assert exit_order.index((chain[7]["logical_name"], 1, chain[7]["transaction_id"])) < exit_order.index(target_key)
    assert exit_order.index((chain[9]["logical_name"], 1, chain[9]["transaction_id"])) < exit_order.index(target_key)


def test_public_attack_matrix_history_time_unbacked_duplicate_and_orphans(tmp_path):
    support.test_resolve_commit_ref_rejects_consistently_resealed_invalid_historical_signatures(
        fresh_chain(tmp_path / "forged-history")
    )
    support.test_future_candidate_issuer_is_rejected_by_all_public_v4_entrypoints(
        fresh_chain(tmp_path / "future-issuer")
    )
    support.test_b0_b3_sequence_and_advanced_head_ref(fresh_chain(tmp_path / "unbacked"))
    support.test_cross_log_duplicate_transaction_is_rejected_after_valid_reseal(
        fresh_chain(tmp_path / "cross-log")
    )
    support.test_two_store_orphan_closure_is_rejected(fresh_chain(tmp_path / "two-store-orphan"))
    orphan_root = tmp_path / "staging-orphan"
    orphan_root.mkdir()
    support.test_orphan_staging_and_root_copy_fail_closed(orphan_root)


def test_public_resolver_rejects_unbacked_cycle_and_recursive_guard_remains_closed(tmp_path):
    chain = fresh_chain(tmp_path / "cycle")
    root, descriptor, capability, _, bootstrap, issuer, _, _, identity, _, credential, credential_ref = chain
    ref = credential_ref
    signed_path = root / ref["record_relative_path"]
    journal_path = root / ref["journal_relative_path"]
    marker_path = root / ref["marker_relative_path"]
    head_path = root / ref["current_head_relative_path"]
    history_path = root / ref["history_relative_path"]
    signed = json.loads(signed_path.read_text())
    journal = json.loads(journal_path.read_text())
    marker = json.loads(marker_path.read_text())
    head = json.loads(head_path.read_text())

    signed["record_body"]["issuer_identity_id"] = identity["identity_id"]
    signed["record_body"]["issuer_credential_id"] = credential["credential_id"]
    signed["record_body_sha256"] = digest(signed["record_body"], "nmrpa.core_registry.record_body.digest.v1")
    signed["signature"] = support.signature(
        issuer,
        signed["record_body_sha256"],
        credential_id=credential["credential_id"],
        credential_ref=credential_ref,
        mode="committed_registry_issuer",
    )
    signed["signed_record_sha256"] = digest(
        {key: value for key, value in signed.items() if key != "signed_record_sha256"},
        "nmrpa.core_registry.signed_record.digest.v1",
    )
    journal["signed_record_sha256"] = signed["signed_record_sha256"]
    journal["synthetic_commit_signature"] = support.signature(
        bootstrap,
        core._attestation_digest(
            journal, "synthetic_commit_signature", "journal_sha256",
            "nmrpa.core_registry.transaction_journal.commit_attestation.v1",
        ),
    )
    journal["journal_sha256"] = digest(
        {key: value for key, value in journal.items() if key != "journal_sha256"},
        "nmrpa.core_registry.transaction_journal.digest.v1",
    )
    marker.update({
        "record_body_sha256": signed["record_body_sha256"],
        "signed_record_sha256": signed["signed_record_sha256"],
        "journal_sha256": journal["journal_sha256"],
    })
    marker["synthetic_commit_signature"] = support.signature(
        bootstrap,
        core._attestation_digest(
            marker, "synthetic_commit_signature", "commit_sha256",
            "nmrpa.core_registry.commit_marker.commit_attestation.v1",
        ),
    )
    marker["commit_sha256"] = digest(
        {key: value for key, value in marker.items() if key != "commit_sha256"},
        "nmrpa.core_registry.commit_marker.digest.v1",
    )
    head.update({
        "record_body_sha256": signed["record_body_sha256"],
        "signed_record_sha256": signed["signed_record_sha256"],
        "journal_sha256": journal["journal_sha256"],
        "commit_sha256": marker["commit_sha256"],
    })
    head["head_sha256"] = digest(
        {key: value for key, value in head.items() if key != "head_sha256"},
        "nmrpa.core_registry.committed_head.digest.v1",
    )
    history = json.loads(history_path.read_text())
    history[-1] = head
    for path, value in (
        (signed_path, signed), (journal_path, journal), (marker_path, marker),
        (history_path, history), (head_path, head),
    ):
        support.write_json(path, value)

    assert_code(
        "NMRPA_CRPG_COMMITTED_KEY_REF_UNTRUSTED",
        lambda: core.resolve_commit_ref(
            chain[7], descriptor, descriptor["descriptor_sha256"],
            project_root=root.resolve(), capability=capability,
            synthetic_bootstrap_verification_public_key=support.key_bytes(bootstrap),
        ),
    )
    support.test_recursive_physical_bundle_rejects_explicit_self_cycle(chain)


@pytest.mark.parametrize("stage", range(1, 7))
def test_public_commit_fault_stages_one_through_six_are_clean(tmp_path, stage):
    root = tmp_path / f"fault-{stage}"
    root.mkdir()
    support.test_core_six_stage_fault_rollback_is_clean(root, stage)


def test_commit_ref_readonly_handoff_shape_without_optional_route_artifacts(tmp_path):
    chain = fresh_chain(tmp_path / "handoff")
    ref = chain[11]
    resolved = public_resolve(chain, ref)
    handoff = json.loads(json.dumps(resolved["commit_ref"], sort_keys=True))
    expected_fields = {
        "schema_version", "descriptor_sha256", "project_root_identity_sha256", "root_instance",
        "logical_name", "log_kind", "log_id", "sequence", "transaction_id", "event_kind",
        "domain_object_kind", "domain_object_id", "domain_object_relative_path", "domain_object_sha256",
        "record_relative_path", "record_body_sha256", "signed_record_sha256", "journal_relative_path",
        "journal_sha256", "marker_relative_path", "commit_sha256", "history_relative_path",
        "historical_head_sequence", "historical_head_sha256", "current_head_relative_path",
        "commit_ref_sha256",
    }
    assert set(handoff) == expected_fields
    assert handoff["schema_version"] == "nmrpa.core_registry.commit_ref.v1"
    assert handoff["root_instance"] == chain[3]
    assert resolved["payload_bytes_read"] == 0

    root, descriptor, *_ = chain
    forbidden_stores = {"authorization_ledger", "anchor_ledger", "binding_store"}
    for store in descriptor["trust_stores"]:
        if store["store_kind"] in forbidden_stores:
            assert not any(path.is_file() for path in (root / store["project_relative_path"]).rglob("*"))
