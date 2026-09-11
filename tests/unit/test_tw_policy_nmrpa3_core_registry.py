from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

import pytest
import numpy as np
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import tw_policy_nmrpa3_core_registry as core
import tw_policy_nmrpa3_immutable_binding_writer as writer
from tw_policy_nmrpa3_real_trust_bootstrap import OWNER_ROLE, canonical_json, digest, expected_descriptor


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(value))


def materialize(root: Path):
    descriptor = expected_descriptor()
    for reservation in descriptor["root_reservations"]:
        (root / reservation["root_project_relative_path"]).mkdir(parents=True)
    for store in descriptor["trust_stores"]:
        (root / store["project_relative_path"]).mkdir(parents=True)
    marker_store = next(row for row in descriptor["trust_stores"] if row["store_kind"] == "project_root_identity_marker")
    marker = {"schema_version": "nmrpa.project_root_identity.v1", "bootstrap_id": descriptor["bootstrap_id"], "project_root_id": "synthetic_tmp_project_root_v1"}
    marker["identity_sha256"] = digest(marker, "nmrpa.project.root.v1")
    write_json(root / marker_store["project_relative_path"] / "identity.json", marker)
    for log in descriptor["fixed_logs"]:
        (root / log["journal_locator"]).mkdir(parents=True)
        (root / log["commit_marker_locator"]).mkdir(parents=True)
        genesis = {"schema_version": "nmrpa.log_genesis.v1", "logical_name": log["logical_name"], "log_kind": log["log_kind"], "log_id": log["log_id"], "owner_role": OWNER_ROLE, "sequence": 0, "previous_head_sha256": None}
        genesis["genesis_sha256"] = digest(genesis, "nmrpa.log.genesis.v1")
        head = {"schema_version": "nmrpa.log_head.v1", "logical_name": log["logical_name"], "log_id": log["log_id"], "sequence": 0, "previous_head_sha256": None, "record_sha256": genesis["genesis_sha256"]}
        head["head_sha256"] = digest(head, "nmrpa.log.head.v1")
        write_json(root / log["genesis_locator"], genesis); write_json(root / log["current_head_locator"], head); write_json(root / log["historical_heads_locator"], [head])
    cap = writer.issue_synthetic_test_capability(root.resolve())
    commitment = writer.describe_synthetic_test_capability(cap, root.resolve())
    return descriptor, cap, commitment


def key_bytes(private: Ed25519PrivateKey) -> bytes:
    return private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def signature(private: Ed25519PrivateKey, signed_digest: str, *, credential_id=core.BOOTSTRAP_ID, credential_ref=None, mode="synthetic_genesis_bootstrap"):
    message = b"nmrpa.core_registry.ed25519.message.v1\x00" + bytes.fromhex(signed_digest)
    return {"schema_version": "nmrpa.core_registry.signature.synthetic.v1", "signer_mode": mode, "credential_id": credential_id, "credential_registration_ref": credential_ref, "algorithm": "ed25519", "signed_digest": signed_digest, "signature_hex": private.sign(message).hex()}


def seal_domain(value: dict, branch: str) -> dict:
    value["domain_object_sha256"] = digest(value, core.DOMAIN_DIGESTS[branch])
    return value


def make_intent(root: Path, descriptor: dict, commitment: dict, bootstrap_private: Ed25519PrivateKey, domain: dict, refs: list[dict], *, signer_private: Ed25519PrivateKey | None = None, signer_identity_id=core.BOOTSTRAP_ID, signer_credential_id=core.BOOTSTRAP_ID, signer_credential_ref=None, serial=1, issued_at=None, prepared_at=None, committed_at=None):
    branch = domain["event_kind"]
    log = next(row for row in descriptor["fixed_logs"] if row["logical_name"] == core.BRANCHES[branch][0])
    previous = json.loads((root / log["current_head_locator"]).read_text())
    sequence = previous["sequence"] + 1
    tx = f"tx_{serial:032x}"
    object_id = domain[core.BRANCHES[branch][2]]
    paths = core._paths(log, branch, tx, sequence, object_id)
    default_times = ("2099-01-01T00:00:01Z", "2099-01-01T00:00:02Z", "2099-01-01T00:00:03Z") if signer_credential_ref is None else ("2099-01-01T00:00:04Z", "2099-01-01T00:00:05Z", "2099-01-01T00:00:06Z")
    issued_at = issued_at or default_times[0]
    prepared_at = prepared_at or default_times[1]
    committed_at = committed_at or default_times[2]
    body = {"schema_version": "nmrpa.core_registry.record_body.v1", "descriptor_sha256": descriptor["descriptor_sha256"], "project_root_identity_sha256": commitment["project_identity_marker_sha256"], "root_instance": commitment, "logical_name": log["logical_name"], "log_kind": log["log_kind"], "log_id": log["log_id"], "transaction_id": tx, "sequence": sequence, "previous_head_sha256": previous["head_sha256"], "previous_commit_sha256": None if sequence == 1 else previous["commit_sha256"], "event_kind": branch, "issued_at": issued_at, "domain_object_kind": core.BRANCHES[branch][1], "domain_object_id": object_id, "domain_object_relative_path": paths["domain_object"], "domain_object_sha256": domain["domain_object_sha256"], "ordered_prerequisite_refs": refs, "issuer_identity_id": signer_identity_id, "issuer_credential_id": signer_credential_id}
    body_sha = digest(body, "nmrpa.core_registry.record_body.digest.v1")
    signer_private = signer_private or bootstrap_private
    issuer_sig = signature(signer_private, body_sha, credential_id=signer_credential_id, credential_ref=signer_credential_ref, mode="synthetic_genesis_bootstrap" if signer_credential_ref is None else "committed_registry_issuer")
    signed = {"schema_version": "nmrpa.core_registry.signed_record.v1", "record_body": body, "record_body_sha256": body_sha, "signature": issuer_sig, "root_instance": commitment}
    signed["signed_record_sha256"] = digest(signed, "nmrpa.core_registry.signed_record.digest.v1")
    journal_base = {"schema_version": "nmrpa.core_registry.transaction_journal.v1", "descriptor_sha256": descriptor["descriptor_sha256"], "project_root_identity_sha256": commitment["project_identity_marker_sha256"], "root_instance": commitment, "logical_name": log["logical_name"], "log_kind": log["log_kind"], "log_id": log["log_id"], "transaction_id": tx, "sequence": sequence, "previous_commit_sha256": body["previous_commit_sha256"], "expected_previous_head_sha256": previous["head_sha256"], "domain_object_sha256": domain["domain_object_sha256"], "signed_record_sha256": signed["signed_record_sha256"], "journal_state": "prepared", "prepared_at": prepared_at}
    journal_attestation = digest(journal_base, "nmrpa.core_registry.transaction_journal.commit_attestation.v1")
    journal_sig = signature(bootstrap_private, journal_attestation)
    journal = {**journal_base, "synthetic_commit_signature": journal_sig}; journal["journal_sha256"] = digest(journal, "nmrpa.core_registry.transaction_journal.digest.v1")
    marker_base = {"schema_version": "nmrpa.core_registry.commit_marker.v1", "descriptor_sha256": descriptor["descriptor_sha256"], "project_root_identity_sha256": commitment["project_identity_marker_sha256"], "root_instance": commitment, "logical_name": log["logical_name"], "log_kind": log["log_kind"], "log_id": log["log_id"], "transaction_id": tx, "sequence": sequence, "previous_commit_sha256": body["previous_commit_sha256"], "expected_previous_head_sha256": previous["head_sha256"], "domain_object_sha256": domain["domain_object_sha256"], "record_body_sha256": body_sha, "signed_record_sha256": signed["signed_record_sha256"], "journal_sha256": journal["journal_sha256"], "prepared_at": prepared_at, "committed_at": committed_at}
    marker_attestation = digest(marker_base, "nmrpa.core_registry.commit_marker.commit_attestation.v1")
    marker_sig = signature(bootstrap_private, marker_attestation)
    intent = {"artifact_kind": "core_registry_intent", "schema_version": core.INTENT_SCHEMA_VERSION, "mode": "synthetic_bootstrap_compatible_no_actual_write", "transition_branch": branch, "transaction_id": tx, "descriptor_sha256": descriptor["descriptor_sha256"], "project_root_identity_sha256": commitment["project_identity_marker_sha256"], "root_instance": commitment, "expected_previous_head": previous, "domain_object": domain, "ordered_prerequisite_refs": refs, "issuer_signature": issuer_sig, "synthetic_bootstrap_public_key_hex": key_bytes(bootstrap_private).hex(), "synthetic_journal_signature": journal_sig, "synthetic_marker_signature": marker_sig, "issued_at": issued_at, "prepared_at": prepared_at, "committed_at": committed_at}
    intent["intent_sha256"] = digest(intent, "nmrpa.core_registry.intent.synthetic.v1")
    return intent


def commit_intent(root, descriptor, cap, bootstrap_private, intent):
    public = key_bytes(bootstrap_private)
    assert core.validate_intent(intent, descriptor, descriptor["descriptor_sha256"], project_root=root.resolve(), capability=cap, synthetic_bootstrap_verification_public_key=public)["status"] == "PHYSICALLY_TRUSTED_INTENT"
    plan = core.plan(intent, descriptor, descriptor["descriptor_sha256"], project_root=root.resolve(), capability=cap, synthetic_bootstrap_verification_public_key=public)
    assert core.validate_plan(plan, descriptor, descriptor["descriptor_sha256"])["status"] == "LOGICALLY_VALID_UNTRUSTED_PLAN"
    result = core.commit(plan, descriptor, descriptor["descriptor_sha256"], project_root=root.resolve(), capability=cap, synthetic_bootstrap_verification_public_key=public)
    assert result["status"] == "PHYSICALLY_COMMITTED"
    return result["commit_ref"]


@pytest.fixture
def chain(tmp_path):
    descriptor, cap, commitment = materialize(tmp_path)
    bootstrap = Ed25519PrivateKey.from_private_bytes(b"B" * 32)
    issuer = Ed25519PrivateKey.from_private_bytes(b"I" * 32)
    principal = seal_domain({"schema_version": core.DOMAIN_VERSIONS["principal_registered"], "transition_id": "transition_" + "1" * 32, "event_kind": "principal_registered", "principal_id": "principal_" + "1" * 32, "canonical_identity": {"identity_namespace": "project_service", "jurisdiction": "ZZ", "canonical_subject_id": "crpg.synthetic.issuer", "canonical_display_name": "CRPG Synthetic Issuer"}, "canonical_identity_sha256": "", "status": "active", "effective_at": "2099-01-01T00:00:00Z"}, "principal_registered")
    principal["canonical_identity_sha256"] = digest(principal["canonical_identity"], "nmrpa.canonical_principal_identity.digest.v1"); principal["domain_object_sha256"] = digest({k:v for k,v in principal.items() if k != "domain_object_sha256"}, core.DOMAIN_DIGESTS["principal_registered"])
    pref = commit_intent(tmp_path, descriptor, cap, bootstrap, make_intent(tmp_path, descriptor, commitment, bootstrap, principal, [], serial=1))
    identity = seal_domain({"schema_version": core.DOMAIN_VERSIONS["identity_registered"], "transition_id": "transition_" + "2" * 32, "event_kind": "identity_registered", "identity_id": "identity_" + "2" * 32, "principal_id": principal["principal_id"], "principal_registration_ref": pref, "role": "trust_registry_issuer", "display_name": "Synthetic Registry Issuer", "valid_from": "2099-01-01T00:00:00Z", "valid_until": None, "status": "active", "effective_at": "2099-01-01T00:00:00Z"}, "identity_registered")
    iref = commit_intent(tmp_path, descriptor, cap, bootstrap, make_intent(tmp_path, descriptor, commitment, bootstrap, identity, [pref], serial=2))
    pub = key_bytes(issuer)
    credential = seal_domain({"schema_version": core.DOMAIN_VERSIONS["credential_activated"], "transition_id": "transition_" + "3" * 32, "event_kind": "credential_activated", "credential_id": "credential_" + "3" * 32, "owner_identity_id": identity["identity_id"], "owner_principal_id": principal["principal_id"], "owner_role": "trust_registry_issuer", "owner_identity_registration_ref": iref, "owner_principal_registration_ref": pref, "algorithm": "ed25519", "public_key_base64": base64.b64encode(pub).decode(), "public_key_fingerprint_sha256": hashlib.sha256(pub).hexdigest(), "valid_from": "2099-01-01T00:00:00Z", "valid_until": None, "status": "active", "effective_at": "2099-01-01T00:00:00Z"}, "credential_activated")
    cref = commit_intent(tmp_path, descriptor, cap, bootstrap, make_intent(tmp_path, descriptor, commitment, bootstrap, credential, [pref, iref], serial=3))
    return tmp_path, descriptor, cap, commitment, bootstrap, issuer, principal, pref, identity, iref, credential, cref


def test_b0_b3_sequence_and_advanced_head_ref(chain):
    root, descriptor, cap, commitment, bootstrap, issuer, principal, pref, identity, iref, credential, cref = chain
    assert pref["sequence"] == iref["sequence"] == cref["sequence"] == 1
    assert core.resolve_commit_ref(pref, descriptor, descriptor["descriptor_sha256"], project_root=root.resolve(), capability=cap, synthetic_bootstrap_verification_public_key=key_bytes(bootstrap))["status"] == "PHYSICALLY_TRUSTED_COMMIT_REF"
    resealed = copy.deepcopy(pref)
    resealed["record_relative_path"] = resealed["journal_relative_path"]
    resealed["commit_ref_sha256"] = digest({key: value for key, value in resealed.items() if key != "commit_ref_sha256"}, "nmrpa.core_registry.commit_ref.digest.v1")
    with pytest.raises(core.ContractError) as exc:
        core.resolve_commit_ref(resealed, descriptor, descriptor["descriptor_sha256"], project_root=root.resolve(), capability=cap, synthetic_bootstrap_verification_public_key=key_bytes(bootstrap))
    assert exc.value.code == "NMRPA_CRPG_COMMIT_REF_UNBACKED"
    replay = make_intent(root, descriptor, commitment, bootstrap, copy.deepcopy(principal), [], serial=99)
    with pytest.raises(core.ContractError) as exc:
        core.validate_intent(replay, descriptor, descriptor["descriptor_sha256"], project_root=root.resolve(), capability=cap, synthetic_bootstrap_verification_public_key=key_bytes(bootstrap))
    assert exc.value.code in {"NMRPA_CRPG_REPLAY", "NMRPA_CRPG_BOOTSTRAP_CLOSED"}


def test_six_branch_role_pack_uses_distinct_identity_credential_and_keys(chain):
    root, descriptor, cap, commitment, bootstrap, issuer, principal, pref, issuer_identity, _, issuer_credential, issuer_cref = chain
    serial = 10

    def add_role(role: str, token: str):
        nonlocal serial
        identity = seal_domain({"schema_version": core.DOMAIN_VERSIONS["identity_registered"], "transition_id": "transition_" + token * 32, "event_kind": "identity_registered", "identity_id": "identity_" + token * 32, "principal_id": principal["principal_id"], "principal_registration_ref": pref, "role": role, "display_name": f"Synthetic {role}", "valid_from": "2099-01-01T00:00:00Z", "valid_until": None, "status": "active", "effective_at": "2099-01-01T00:00:00Z"}, "identity_registered")
        intent = make_intent(root, descriptor, commitment, bootstrap, identity, [pref], signer_private=issuer, signer_identity_id=issuer_identity["identity_id"], signer_credential_id=issuer_credential["credential_id"], signer_credential_ref=issuer_cref, serial=serial); serial += 1
        iref = commit_intent(root, descriptor, cap, bootstrap, intent)
        private = Ed25519PrivateKey.from_private_bytes(token.encode() * 32)
        public = key_bytes(private)
        credential = seal_domain({"schema_version": core.DOMAIN_VERSIONS["credential_activated"], "transition_id": "transition_" + chr(ord(token) + 3) * 32, "event_kind": "credential_activated", "credential_id": "credential_" + token * 32, "owner_identity_id": identity["identity_id"], "owner_principal_id": principal["principal_id"], "owner_role": role, "owner_identity_registration_ref": iref, "owner_principal_registration_ref": pref, "algorithm": "ed25519", "public_key_base64": base64.b64encode(public).decode(), "public_key_fingerprint_sha256": hashlib.sha256(public).hexdigest(), "valid_from": "2099-01-01T00:00:00Z", "valid_until": None, "status": "active", "effective_at": "2099-01-01T00:00:00Z"}, "credential_activated")
        intent = make_intent(root, descriptor, commitment, bootstrap, credential, [pref, iref], signer_private=issuer, signer_identity_id=issuer_identity["identity_id"], signer_credential_id=issuer_credential["credential_id"], signer_credential_ref=issuer_cref, serial=serial); serial += 1
        cref = commit_intent(root, descriptor, cap, bootstrap, intent)
        return identity, iref, credential, cref

    service_identity, service_iref, service_credential, service_cref = add_role("trusted_time_authority", "4")
    authority_identity, authority_iref, authority_credential, authority_cref = add_role("publication_authority", "5")
    recorder_identity, recorder_iref, recorder_credential, recorder_cref = add_role("capture_recorder", "6")

    service = seal_domain({"schema_version": core.DOMAIN_VERSIONS["trusted_service_registered"], "transition_id": "transition_" + "7" * 32, "event_kind": "trusted_service_registered", "registration_id": "service_" + "7" * 32, "service_type": "trusted_time_authority", "principal_id": principal["principal_id"], "service_identity_id": service_identity["identity_id"], "service_credential_id": service_credential["credential_id"], "principal_registration_ref": pref, "identity_registration_ref": service_iref, "credential_registration_ref": service_cref, "allowed_log_kinds": ["issuer_registry", "publication_authority_registry", "capture_recorder_registry"], "valid_from": "2099-01-01T00:00:00Z", "valid_until": None, "status": "active", "effective_at": "2099-01-01T00:00:00Z"}, "trusted_service_registered")
    service["transition_id"] = "transition_" + "a" * 32; service["domain_object_sha256"] = digest({key: value for key, value in service.items() if key != "domain_object_sha256"}, core.DOMAIN_DIGESTS["trusted_service_registered"])
    service_ref = commit_intent(root, descriptor, cap, bootstrap, make_intent(root, descriptor, commitment, bootstrap, service, [pref, service_iref, service_cref], signer_private=issuer, signer_identity_id=issuer_identity["identity_id"], signer_credential_id=issuer_credential["credential_id"], signer_credential_ref=issuer_cref, serial=serial)); serial += 1

    authority = seal_domain({"schema_version": core.DOMAIN_VERSIONS["publication_authority_registered"], "transition_id": "transition_" + "8" * 32, "event_kind": "publication_authority_registered", "registration_id": "authority_" + "8" * 32, "authority_id": "authority_" + "8" * 32, "principal_id": principal["principal_id"], "authority_identity_id": authority_identity["identity_id"], "authority_credential_id": authority_credential["credential_id"], "principal_registration_ref": pref, "authority_identity_registration_ref": authority_iref, "authority_credential_registration_ref": authority_cref, "source_id": "Source.CRPG1", "allowed_root_kinds": list(core.ROOT_KINDS), "publication_contract_id": "Contract.CRPG1.Publication", "valid_from": "2099-01-01T00:00:00Z", "valid_until": None, "status": "active", "effective_at": "2099-01-01T00:00:00Z"}, "publication_authority_registered")
    authority["transition_id"] = "transition_" + "b" * 32; authority["domain_object_sha256"] = digest({key: value for key, value in authority.items() if key != "domain_object_sha256"}, core.DOMAIN_DIGESTS["publication_authority_registered"])
    authority_ref = commit_intent(root, descriptor, cap, bootstrap, make_intent(root, descriptor, commitment, bootstrap, authority, [pref, authority_iref, authority_cref], signer_private=issuer, signer_identity_id=issuer_identity["identity_id"], signer_credential_id=issuer_credential["credential_id"], signer_credential_ref=issuer_cref, serial=serial)); serial += 1

    recorder = seal_domain({"schema_version": core.DOMAIN_VERSIONS["capture_recorder_registered"], "transition_id": "transition_" + "9" * 32, "event_kind": "capture_recorder_registered", "registration_id": "recorder_" + "9" * 32, "recorder_id": "recorder_" + "9" * 32, "principal_id": principal["principal_id"], "recorder_identity_id": recorder_identity["identity_id"], "recorder_credential_id": recorder_credential["credential_id"], "principal_registration_ref": pref, "recorder_identity_registration_ref": recorder_iref, "recorder_credential_registration_ref": recorder_cref, "allowed_scopes": [{"source_id": "Source.CRPG1", "endpoint_id": "Endpoint.CRPG1", "method": "GET", "request_contract_id": "Request.CRPG1", "canonical_query_contract_id": "Query.CRPG1", "requested_scope_contract_id": "Scope.CRPG1", "allowed_root_kinds": list(core.ROOT_KINDS), "allowed_response_media_types": ["application/json"]}], "valid_from": "2099-01-01T00:00:00Z", "valid_until": None, "status": "active", "effective_at": "2099-01-01T00:00:00Z"}, "capture_recorder_registered")
    recorder["transition_id"] = "transition_" + "c" * 32; recorder["domain_object_sha256"] = digest({key: value for key, value in recorder.items() if key != "domain_object_sha256"}, core.DOMAIN_DIGESTS["capture_recorder_registered"])
    recorder_ref = commit_intent(root, descriptor, cap, bootstrap, make_intent(root, descriptor, commitment, bootstrap, recorder, [pref, recorder_iref, recorder_cref], signer_private=issuer, signer_identity_id=issuer_identity["identity_id"], signer_credential_id=issuer_credential["credential_id"], signer_credential_ref=issuer_cref, serial=serial))
    assert {service_ref["event_kind"], authority_ref["event_kind"], recorder_ref["event_kind"]} == {"trusted_service_registered", "publication_authority_registered", "capture_recorder_registered"}
    assert len({service_credential["public_key_base64"], authority_credential["public_key_base64"], recorder_credential["public_key_base64"], issuer_credential["public_key_base64"]}) == 4


@pytest.mark.parametrize("bad", [True, 1.0, Decimal("1"), type("IntChild", (int,), {})(1)])
def test_root_instance_exact_integer_rejects_non_builtin(chain, bad):
    value = copy.deepcopy(chain[3]); value["st_ino"] = bad
    with pytest.raises(core.ContractError) as exc: core.validate_root_instance_commitment_shape(value)
    assert exc.value.code == "NMRPA_CRPG_ROOT_INSTANCE_SCHEMA"


def test_new_capability_and_resealed_commitment_rejected(chain):
    root, descriptor, cap, commitment, bootstrap, *_ = chain
    new_cap = writer.issue_synthetic_test_capability(root.resolve())
    new_commitment = writer.describe_synthetic_test_capability(new_cap, root.resolve())
    assert new_commitment != commitment
    with pytest.raises(core.ContractError) as exc:
        core.resolve_commit_ref(chain[7], descriptor, descriptor["descriptor_sha256"], project_root=root.resolve(), capability=new_cap, synthetic_bootstrap_verification_public_key=key_bytes(bootstrap))
    assert exc.value.code == "NMRPA_CRPG_ROOT_INSTANCE_MISMATCH"


def test_helper_no_nonce_or_fd_and_actual_marker_hardlink_rejected(tmp_path, monkeypatch):
    descriptor, cap, _ = materialize(tmp_path)
    described = writer.describe_synthetic_test_capability(cap, tmp_path.resolve())
    rendered = json.dumps(described, sort_keys=True)
    assert "nonce\"" not in rendered and "root_fd" not in rendered and "private" not in rendered
    writer.close_synthetic_test_capability(cap)
    with pytest.raises(writer.ContractError): writer.describe_synthetic_test_capability(cap, tmp_path.resolve())
    if core.ACTUAL_MARKER.exists():
        other = tmp_path.parent / f"{tmp_path.name}-hardlink"
        descriptor2, cap2, _ = materialize(other)
        marker_rel = f"{core.BASE}/stores/project_root_identity_marker/identity.json"
        (other / marker_rel).unlink()
        try:
            os.link(core.ACTUAL_MARKER, other / marker_rel)
        except OSError as error:
            if error.errno != 18:
                raise
            # The workspace and /tmp are separate devices here. Reproduce the
            # forbidden inode relation on /tmp without weakening the helper.
            write_json(other / marker_rel, json.loads(core.ACTUAL_MARKER.read_text()))
            fake_actual = tmp_path.parent / f"{tmp_path.name}-actual-root"
            (fake_actual / Path(marker_rel).parent).mkdir(parents=True)
            os.link(other / marker_rel, fake_actual / marker_rel)
            monkeypatch.setattr(writer, "ACTUAL_PROJECT_ROOT", fake_actual)
        with pytest.raises(writer.ContractError) as exc: writer.describe_synthetic_test_capability(cap2, other.resolve())
        assert exc.value.code == "NMRPA_CRPG_ROOT_INSTANCE_MARKER"


def test_schemas_are_draft_2020_12_and_exact_top_level():
    for name in ("intent", "plan"):
        path = ROOT / f"scripts/schemas/tw_policy_nmrpa3_core_registry_{name}.schema.json"
        schema = json.loads(path.read_text())
        Draft202012Validator.check_schema(schema)
        assert schema["additionalProperties"] is False


def test_writer_no_clobber_default_type_gate_and_nominal(tmp_path):
    descriptor, cap, _ = materialize(tmp_path)
    with pytest.raises(writer.ContractError) as exc:
        writer.commit_schema_driven_transaction({}, tmp_path.resolve(), cap, validate_plan=lambda p: {}, load_closure=lambda p: {}, validate_post_commit=lambda p,v: {}, lock_relative_path=descriptor["fixed_logs"][0]["storage_project_relative_path"], immutable_values={}, mutable_values={}, immutable_final_no_clobber=1)
    assert exc.value.code == "NMRPA_TR_E_SCHEMA"


def test_actual_root_and_payload_surfaces_rejected(chain):
    with pytest.raises(writer.ContractError): writer.issue_synthetic_test_capability(ROOT)
    intent = make_intent(chain[0], chain[1], chain[3], chain[4], copy.deepcopy(chain[6]), [], serial=101)
    intent["payload_path"] = "/tmp/forbidden"
    with pytest.raises(core.ContractError) as exc: core.validate_plan(intent, chain[1], chain[1]["descriptor_sha256"])
    assert exc.value.code == "NMRPA_CRPG_PAYLOAD_SURFACE"


def _fresh_principal_case(tmp_path):
    descriptor, cap, commitment = materialize(tmp_path)
    bootstrap = Ed25519PrivateKey.from_private_bytes(b"B" * 32)
    domain = {"schema_version": core.DOMAIN_VERSIONS["principal_registered"], "transition_id": "transition_" + "a" * 32, "event_kind": "principal_registered", "principal_id": "principal_" + "a" * 32, "canonical_identity": {"identity_namespace": "project_service", "jurisdiction": "ZZ", "canonical_subject_id": "crpg.synthetic.fault", "canonical_display_name": "CRPG Fault Fixture"}, "canonical_identity_sha256": "", "status": "active", "effective_at": "2099-01-01T00:00:00Z"}
    domain["canonical_identity_sha256"] = digest(domain["canonical_identity"], "nmrpa.canonical_principal_identity.digest.v1")
    domain["domain_object_sha256"] = digest({key: value for key, value in domain.items() if key != "domain_object_sha256"}, core.DOMAIN_DIGESTS["principal_registered"])
    intent = make_intent(tmp_path, descriptor, commitment, bootstrap, domain, [], serial=500)
    return descriptor, cap, commitment, bootstrap, intent


@pytest.mark.parametrize("step", range(1, 7))
def test_core_six_stage_fault_rollback_is_clean(tmp_path, step):
    descriptor, cap, _, bootstrap, intent = _fresh_principal_case(tmp_path)
    public = key_bytes(bootstrap)
    plan = core.plan(intent, descriptor, descriptor["descriptor_sha256"], project_root=tmp_path.resolve(), capability=cap, synthetic_bootstrap_verification_public_key=public)
    before_head = (tmp_path / plan["paths"]["head"]).read_bytes(); before_history = (tmp_path / plan["paths"]["history"]).read_bytes()
    with pytest.raises(writer.ContractError) as exc:
        core.commit(plan, descriptor, descriptor["descriptor_sha256"], project_root=tmp_path.resolve(), capability=cap, synthetic_bootstrap_verification_public_key=public, synthetic_fail_after_step=step)
    assert exc.value.code == "NMRPA_TR_E_SYNTHETIC_FAULT"
    assert (tmp_path / plan["paths"]["head"]).read_bytes() == before_head
    assert (tmp_path / plan["paths"]["history"]).read_bytes() == before_history
    assert all(not (tmp_path / relative).exists() for key, relative in plan["paths"].items() if key not in ("head", "history"))


def test_wrong_bootstrap_key_and_wrong_ed25519_message_fail_physical(tmp_path):
    descriptor, cap, _, bootstrap, intent = _fresh_principal_case(tmp_path)
    with pytest.raises(core.ContractError) as exc:
        core.validate_intent(intent, descriptor, descriptor["descriptor_sha256"], project_root=tmp_path.resolve(), capability=cap, synthetic_bootstrap_verification_public_key=b"X" * 32)
    assert exc.value.code == "NMRPA_CRPG_BOOTSTRAP_KEY_MISMATCH"
    forged = copy.deepcopy(intent); forged["issuer_signature"]["signature_hex"] = bootstrap.sign(bytes.fromhex(forged["issuer_signature"]["signed_digest"])).hex(); forged["intent_sha256"] = digest({k:v for k,v in forged.items() if k != "intent_sha256"}, "nmrpa.core_registry.intent.synthetic.v1")
    with pytest.raises(core.ContractError) as exc:
        core.validate_intent(forged, descriptor, descriptor["descriptor_sha256"], project_root=tmp_path.resolve(), capability=cap, synthetic_bootstrap_verification_public_key=key_bytes(bootstrap))
    assert exc.value.code == "NMRPA_CRPG_SIGNATURE_INVALID"


def test_orphan_staging_and_root_copy_fail_closed(tmp_path):
    descriptor, cap, commitment, bootstrap, intent = _fresh_principal_case(tmp_path)
    log = descriptor["fixed_logs"][0]
    orphan = tmp_path / log["journal_locator"] / "unknown.nmrpa-crpg1-stage"
    orphan.write_text("{}")
    with pytest.raises(core.ContractError) as exc:
        core.validate_intent(intent, descriptor, descriptor["descriptor_sha256"], project_root=tmp_path.resolve(), capability=cap, synthetic_bootstrap_verification_public_key=key_bytes(bootstrap))
    assert exc.value.code == "NMRPA_CRPG_ORPHAN"
    orphan.unlink()
    copied = tmp_path.parent / f"{tmp_path.name}-copy"
    import shutil
    shutil.copytree(tmp_path, copied)
    copied_cap = writer.issue_synthetic_test_capability(copied.resolve())
    with pytest.raises(core.ContractError) as exc:
        core.validate_intent(intent, descriptor, descriptor["descriptor_sha256"], project_root=copied.resolve(), capability=copied_cap, synthetic_bootstrap_verification_public_key=key_bytes(bootstrap))
    assert exc.value.code == "NMRPA_CRPG_ROOT_INSTANCE_MISMATCH"


def test_plan_concrete_integer_selector_matrix_rejects_python_numeric_aliases(tmp_path):
    descriptor, cap, _, bootstrap, intent = _fresh_principal_case(tmp_path)
    plan = core.plan(intent, descriptor, descriptor["descriptor_sha256"], project_root=tmp_path.resolve(), capability=cap, synthetic_bootstrap_verification_public_key=key_bytes(bootstrap))
    selectors = [
        ("expected_previous_head", "sequence"), ("signed_record", "record_body", "sequence"),
        ("journal", "sequence"), ("commit_marker", "sequence"), ("new_head", "sequence"),
        ("new_history", 0, "sequence"), ("new_history", 1, "sequence"),
    ]
    bad_values = [True, 1.0, Decimal("1"), np.int64(1), type("IntChild", (int,), {})(1)]
    for selector in selectors:
        for bad in bad_values:
            candidate = copy.deepcopy(plan); cursor = candidate
            for key in selector[:-1]: cursor = cursor[key]
            cursor[selector[-1]] = bad
            with pytest.raises(core.ContractError):
                core.validate_plan(candidate, descriptor, descriptor["descriptor_sha256"])


def test_physical_head_marker_committed_at_cross_equality_attack_is_rejected(chain):
    root, descriptor, cap, _, bootstrap, *_, pref, identity, iref, credential, cref = chain
    log = next(row for row in descriptor["fixed_logs"] if row["logical_name"] == iref["logical_name"])
    head_path = root / log["current_head_locator"]
    history_path = root / log["historical_heads_locator"]
    head = json.loads(head_path.read_text())
    head["committed_at"] = "2099-01-01T00:00:59Z"
    head["head_sha256"] = digest({key: value for key, value in head.items() if key != "head_sha256"}, "nmrpa.core_registry.committed_head.digest.v1")
    history = json.loads(history_path.read_text())
    history[-1] = head
    write_json(head_path, head)
    write_json(history_path, history)
    with pytest.raises(core.ContractError) as exc:
        core.resolve_commit_ref(pref, descriptor, descriptor["descriptor_sha256"], project_root=root.resolve(), capability=cap, synthetic_bootstrap_verification_public_key=key_bytes(bootstrap))
    assert exc.value.code == "NMRPA_CRPG_SIGNED_CONTAINER_MISMATCH"


def test_resolve_commit_ref_rejects_consistently_resealed_invalid_historical_signatures(chain):
    root, descriptor, cap, _, bootstrap, *_, pref, identity, iref, credential, cref = chain
    log = next(row for row in descriptor["fixed_logs"] if row["logical_name"] == cref["logical_name"])
    paths = core._paths(log, "credential_activated", cref["transaction_id"], cref["sequence"], credential["credential_id"])
    signed = json.loads((root / paths["signed_record"]).read_text())
    journal = json.loads((root / paths["journal"]).read_text())
    marker = json.loads((root / paths["marker"]).read_text())
    head = json.loads((root / paths["head"]).read_text())

    signed["signature"]["signature_hex"] = "0" * 128
    signed["signed_record_sha256"] = digest(
        {key: value for key, value in signed.items() if key != "signed_record_sha256"},
        "nmrpa.core_registry.signed_record.digest.v1",
    )
    journal["signed_record_sha256"] = signed["signed_record_sha256"]
    journal["synthetic_commit_signature"]["signed_digest"] = core._attestation_digest(
        journal, "synthetic_commit_signature", "journal_sha256",
        "nmrpa.core_registry.transaction_journal.commit_attestation.v1",
    )
    journal["synthetic_commit_signature"]["signature_hex"] = "0" * 128
    journal["journal_sha256"] = digest(
        {key: value for key, value in journal.items() if key != "journal_sha256"},
        "nmrpa.core_registry.transaction_journal.digest.v1",
    )
    marker.update({"signed_record_sha256": signed["signed_record_sha256"], "journal_sha256": journal["journal_sha256"]})
    marker["synthetic_commit_signature"]["signed_digest"] = core._attestation_digest(
        marker, "synthetic_commit_signature", "commit_sha256",
        "nmrpa.core_registry.commit_marker.commit_attestation.v1",
    )
    marker["synthetic_commit_signature"]["signature_hex"] = "0" * 128
    marker["commit_sha256"] = digest(
        {key: value for key, value in marker.items() if key != "commit_sha256"},
        "nmrpa.core_registry.commit_marker.digest.v1",
    )
    head.update({
        "signed_record_sha256": signed["signed_record_sha256"],
        "journal_sha256": journal["journal_sha256"],
        "commit_sha256": marker["commit_sha256"],
    })
    head["head_sha256"] = digest(
        {key: value for key, value in head.items() if key != "head_sha256"},
        "nmrpa.core_registry.committed_head.digest.v1",
    )
    history = json.loads((root / paths["history"]).read_text())
    history[-1] = head
    write_json(root / paths["signed_record"], signed)
    write_json(root / paths["journal"], journal)
    write_json(root / paths["marker"], marker)
    write_json(root / paths["history"], history)
    write_json(root / paths["head"], head)

    with pytest.raises(core.ContractError) as exc:
        core.resolve_commit_ref(
            pref, descriptor, descriptor["descriptor_sha256"], project_root=root.resolve(),
            capability=cap, synthetic_bootstrap_verification_public_key=key_bytes(bootstrap),
        )
    assert exc.value.code == "NMRPA_CRPG_SIGNATURE_INVALID"


def _loaded_closure(chain):
    root, descriptor, _, commitment, *_ = chain
    return core._full_closure(root, descriptor, commitment)


def test_recursive_physical_bundle_rejects_explicit_self_cycle(chain):
    closure = _loaded_closure(chain)
    iref = chain[9]
    identity_head = closure["objects"][iref["domain_object_id"]][1]
    closure["bundles"][identity_head["transaction_id"]][1]["record_body"]["ordered_prerequisite_refs"] = [iref]
    with pytest.raises(core.ContractError) as exc:
        core._validate_physical_bundle(identity_head, closure, key_bytes(chain[4]), set(), [])
    assert exc.value.code == "NMRPA_CRPG_COMMITTED_KEY_REF_CYCLE"


def test_recursive_physical_bundle_rejects_future_marker_reference(chain):
    closure = _loaded_closure(chain)
    identity_head = closure["objects"][chain[9]["domain_object_id"]][1]
    principal_head = closure["objects"][chain[7]["domain_object_id"]][1]
    closure["bundles"][principal_head["transaction_id"]][3]["committed_at"] = "2099-01-01T00:00:59Z"
    with pytest.raises(core.ContractError) as exc:
        core._validate_physical_bundle(identity_head, closure, key_bytes(chain[4]), set(), [])
    assert exc.value.code == "NMRPA_CRPG_COMMITTED_KEY_REF_UNTRUSTED"


def test_historical_credential_wrong_owner_is_rejected_before_key_use(chain):
    closure = _loaded_closure(chain)
    credential_head = closure["objects"][chain[11]["domain_object_id"]][1]
    closure["objects"][chain[11]["domain_object_id"]][0]["owner_identity_id"] = "identity_" + "f" * 32
    with pytest.raises(core.ContractError) as exc:
        core._validate_physical_bundle(credential_head, closure, key_bytes(chain[4]), set(), [])
    assert exc.value.code == "NMRPA_CRPG_PREREQUISITE"


def test_committed_issuer_key_rejects_inactive_at_marker(chain):
    credential = copy.deepcopy(chain[10])
    credential["valid_until"] = "2099-01-01T00:00:03Z"
    body = {"issued_at": "2099-01-01T00:00:01Z", "issuer_identity_id": credential["owner_identity_id"], "issuer_credential_id": credential["credential_id"]}
    signed = {"credential_id": credential["credential_id"]}
    with pytest.raises(core.ContractError) as exc:
        core._decode_committed_issuer_key(signed, credential, body, {"committed_at": "2099-01-01T00:00:03Z"})
    assert exc.value.code == "NMRPA_CRPG_COMMITTED_KEY_INACTIVE"


def test_recursive_credential_foundation_is_verified_before_descendant_key_consumption(chain, monkeypatch):
    closure = _loaded_closure(chain)
    credential_head = closure["objects"][chain[11]["domain_object_id"]][1]
    observed = []
    original = core._validate_physical_bundle

    def traced(head, closure_value, bootstrap_key, validated, stack):
        observed.append(("enter", core._bundle_key(head)))
        result = original(head, closure_value, bootstrap_key, validated, stack)
        observed.append(("exit", core._bundle_key(head)))
        return result

    monkeypatch.setattr(core, "_validate_physical_bundle", traced)
    descendant_body = {"issued_at": "2099-01-01T00:00:04Z", "issuer_identity_id": chain[8]["identity_id"], "issuer_credential_id": chain[10]["credential_id"]}
    key = core._physical_key(
        {"signer_mode": "committed_registry_issuer", "credential_id": chain[10]["credential_id"], "credential_registration_ref": chain[11]},
        closure, key_bytes(chain[4]), descendant_body, "2099-01-01T00:00:05Z", set(), [],
    )
    assert key == key_bytes(chain[5])
    assert observed[-1] == ("exit", core._bundle_key(credential_head))


def test_same_log_advanced_head_keeps_historical_ref_trusted(chain):
    root, descriptor, cap, commitment, bootstrap, issuer, principal, pref, issuer_identity, _, issuer_credential, issuer_cref = chain
    second = seal_domain({"schema_version": core.DOMAIN_VERSIONS["principal_registered"], "transition_id": "transition_" + "d" * 32, "event_kind": "principal_registered", "principal_id": "principal_" + "d" * 32, "canonical_identity": {"identity_namespace": "project_service", "jurisdiction": "ZZ", "canonical_subject_id": "crpg.synthetic.second", "canonical_display_name": "CRPG Second Principal"}, "canonical_identity_sha256": "", "status": "active", "effective_at": "2099-01-01T00:00:00Z"}, "principal_registered")
    second["canonical_identity_sha256"] = digest(second["canonical_identity"], "nmrpa.canonical_principal_identity.digest.v1")
    second["domain_object_sha256"] = digest({key: value for key, value in second.items() if key != "domain_object_sha256"}, core.DOMAIN_DIGESTS["principal_registered"])
    commit_intent(root, descriptor, cap, bootstrap, make_intent(root, descriptor, commitment, bootstrap, second, [], signer_private=issuer, signer_identity_id=issuer_identity["identity_id"], signer_credential_id=issuer_credential["credential_id"], signer_credential_ref=issuer_cref, serial=700))
    assert core.resolve_commit_ref(pref, descriptor, descriptor["descriptor_sha256"], project_root=root.resolve(), capability=cap, synthetic_bootstrap_verification_public_key=key_bytes(bootstrap))["status"] == "PHYSICALLY_TRUSTED_COMMIT_REF"


def test_two_store_orphan_closure_is_rejected(chain):
    root, descriptor, cap, _, bootstrap, *_, pref, identity, iref, credential, cref = chain
    write_json(root / core.A_STORE / ("service_" + "e" * 32 + ".trusted_service.json"), {})
    with pytest.raises(core.ContractError) as exc:
        core.resolve_commit_ref(pref, descriptor, descriptor["descriptor_sha256"], project_root=root.resolve(), capability=cap, synthetic_bootstrap_verification_public_key=key_bytes(bootstrap))
    assert exc.value.code == "NMRPA_CRPG_ORPHAN"


def test_cross_log_duplicate_transaction_is_rejected_after_valid_reseal(chain):
    root, descriptor, cap, commitment, bootstrap, *_, pref, identity, iref, credential, cref = chain
    log = next(row for row in descriptor["fixed_logs"] if row["logical_name"] == iref["logical_name"])
    old_paths = core._paths(log, "identity_registered", iref["transaction_id"], 1, identity["identity_id"])
    new_paths = core._paths(log, "identity_registered", pref["transaction_id"], 1, identity["identity_id"])
    signed = json.loads((root / old_paths["signed_record"]).read_text())
    journal = json.loads((root / old_paths["journal"]).read_text())
    marker = json.loads((root / old_paths["marker"]).read_text())
    head = json.loads((root / old_paths["head"]).read_text())
    body = signed["record_body"]
    body["transaction_id"] = pref["transaction_id"]
    signed["record_body_sha256"] = digest(body, "nmrpa.core_registry.record_body.digest.v1")
    signed["signature"] = signature(bootstrap, signed["record_body_sha256"])
    signed["signed_record_sha256"] = digest({key: value for key, value in signed.items() if key != "signed_record_sha256"}, "nmrpa.core_registry.signed_record.digest.v1")
    journal["transaction_id"] = pref["transaction_id"]
    journal["signed_record_sha256"] = signed["signed_record_sha256"]
    journal["synthetic_commit_signature"] = signature(bootstrap, core._attestation_digest(journal, "synthetic_commit_signature", "journal_sha256", "nmrpa.core_registry.transaction_journal.commit_attestation.v1"))
    journal["journal_sha256"] = digest({key: value for key, value in journal.items() if key != "journal_sha256"}, "nmrpa.core_registry.transaction_journal.digest.v1")
    marker["transaction_id"] = pref["transaction_id"]
    marker["record_body_sha256"] = signed["record_body_sha256"]
    marker["signed_record_sha256"] = signed["signed_record_sha256"]
    marker["journal_sha256"] = journal["journal_sha256"]
    marker["synthetic_commit_signature"] = signature(bootstrap, core._attestation_digest(marker, "synthetic_commit_signature", "commit_sha256", "nmrpa.core_registry.commit_marker.commit_attestation.v1"))
    marker["commit_sha256"] = digest({key: value for key, value in marker.items() if key != "commit_sha256"}, "nmrpa.core_registry.commit_marker.digest.v1")
    head.update({"transaction_id": pref["transaction_id"], "record_body_sha256": signed["record_body_sha256"], "signed_record_sha256": signed["signed_record_sha256"], "journal_sha256": journal["journal_sha256"], "commit_sha256": marker["commit_sha256"]})
    head["head_sha256"] = digest({key: value for key, value in head.items() if key != "head_sha256"}, "nmrpa.core_registry.committed_head.digest.v1")
    for key in ("signed_record", "journal", "marker"):
        (root / old_paths[key]).unlink()
    write_json(root / new_paths["signed_record"], signed)
    write_json(root / new_paths["journal"], journal)
    write_json(root / new_paths["marker"], marker)
    history = json.loads((root / old_paths["history"]).read_text())
    history[-1] = head
    write_json(root / old_paths["history"], history)
    write_json(root / old_paths["head"], head)
    with pytest.raises(core.ContractError) as exc:
        core.resolve_commit_ref(pref, descriptor, descriptor["descriptor_sha256"], project_root=root.resolve(), capability=cap, synthetic_bootstrap_verification_public_key=key_bytes(bootstrap))
    assert exc.value.code == "NMRPA_CRPG_CROSS_LOG_TX_MULTIPLICITY"


def test_committed_signature_missing_ref_has_frozen_error(chain):
    value = signature(chain[5], "0" * 64, credential_id=chain[10]["credential_id"], credential_ref=None, mode="committed_registry_issuer")
    with pytest.raises(core.ContractError) as exc:
        core._validate_signature(value, chain[3])
    assert exc.value.code == "NMRPA_CRPG_COMMITTED_KEY_REF_REQUIRED"


def test_committed_signature_wrong_role_has_frozen_error(chain):
    credential = copy.deepcopy(chain[10])
    credential["owner_role"] = "validator"
    body = {"issued_at": "2099-01-01T00:00:01Z", "issuer_identity_id": credential["owner_identity_id"], "issuer_credential_id": credential["credential_id"]}
    with pytest.raises(core.ContractError) as exc:
        core._decode_committed_issuer_key({"credential_id": credential["credential_id"]}, credential, body, {"committed_at": "2099-01-01T00:00:03Z"})
    assert exc.value.code == "NMRPA_CRPG_COMMITTED_KEY_ROLE"


def test_v3_logical_plan_pass_does_not_mask_v4_signature_failure(tmp_path):
    descriptor, cap, _, bootstrap, intent = _fresh_principal_case(tmp_path)
    plan = core.plan(intent, descriptor, descriptor["descriptor_sha256"], project_root=tmp_path.resolve(), capability=cap, synthetic_bootstrap_verification_public_key=key_bytes(bootstrap))
    forged = copy.deepcopy(plan)
    forged["signed_record"]["signature"]["signature_hex"] = "0" * 128
    forged["signed_record"]["signed_record_sha256"] = digest({key: value for key, value in forged["signed_record"].items() if key != "signed_record_sha256"}, "nmrpa.core_registry.signed_record.digest.v1")
    forged["journal"]["signed_record_sha256"] = forged["signed_record"]["signed_record_sha256"]
    forged["journal"]["synthetic_commit_signature"] = signature(bootstrap, core._attestation_digest(forged["journal"], "synthetic_commit_signature", "journal_sha256", "nmrpa.core_registry.transaction_journal.commit_attestation.v1"))
    forged["journal"]["journal_sha256"] = digest({key: value for key, value in forged["journal"].items() if key != "journal_sha256"}, "nmrpa.core_registry.transaction_journal.digest.v1")
    forged["commit_marker"]["signed_record_sha256"] = forged["signed_record"]["signed_record_sha256"]
    forged["commit_marker"]["journal_sha256"] = forged["journal"]["journal_sha256"]
    forged["commit_marker"]["synthetic_commit_signature"] = signature(bootstrap, core._attestation_digest(forged["commit_marker"], "synthetic_commit_signature", "commit_sha256", "nmrpa.core_registry.commit_marker.commit_attestation.v1"))
    forged["commit_marker"]["commit_sha256"] = digest({key: value for key, value in forged["commit_marker"].items() if key != "commit_sha256"}, "nmrpa.core_registry.commit_marker.digest.v1")
    head = forged["new_head"]
    head["signed_record_sha256"] = forged["signed_record"]["signed_record_sha256"]
    head["journal_sha256"] = forged["journal"]["journal_sha256"]
    head["commit_sha256"] = forged["commit_marker"]["commit_sha256"]
    head["head_sha256"] = digest({key: value for key, value in head.items() if key != "head_sha256"}, "nmrpa.core_registry.committed_head.digest.v1")
    forged["new_history"][-1] = head
    forged["plan_sha256"] = digest({key: value for key, value in forged.items() if key != "plan_sha256"}, "nmrpa.core_registry.transaction_plan.synthetic.v1")
    # The forged envelope remains structurally/logically coherent, but V4 must
    # reject the Ed25519 message before it can become physically trusted.
    assert core.validate_plan(forged, descriptor, descriptor["descriptor_sha256"])["status"] == "LOGICALLY_VALID_UNTRUSTED_PLAN"
    with pytest.raises(core.ContractError) as exc:
        core._physical(forged, descriptor, tmp_path.resolve(), cap, key_bytes(bootstrap))
    assert exc.value.code == "NMRPA_CRPG_SIGNATURE_INVALID"


def test_future_candidate_issuer_is_rejected_by_all_public_v4_entrypoints(chain):
    root, descriptor, cap, commitment, bootstrap, issuer, principal, pref, issuer_identity, _, issuer_credential, issuer_cref = chain
    identity = seal_domain({"schema_version": core.DOMAIN_VERSIONS["identity_registered"], "transition_id": "transition_" + "c" * 32, "event_kind": "identity_registered", "identity_id": "identity_" + "c" * 32, "principal_id": principal["principal_id"], "principal_registration_ref": pref, "role": "validator", "display_name": "Future Candidate Issuer Rejection", "valid_from": "2099-01-01T00:00:00Z", "valid_until": None, "status": "active", "effective_at": "2099-01-01T00:00:00Z"}, "identity_registered")
    common = dict(signer_private=issuer, signer_identity_id=issuer_identity["identity_id"], signer_credential_id=issuer_credential["credential_id"], signer_credential_ref=issuer_cref, serial=900)
    future_intent = make_intent(
        root, descriptor, commitment, bootstrap, identity, [pref],
        issued_at="2099-01-01T00:00:01Z", prepared_at="2099-01-01T00:00:02Z",
        committed_at="2099-01-01T00:00:03Z", **common,
    )
    public_key = key_bytes(bootstrap)
    for entrypoint in (
        lambda: core.validate_intent(future_intent, descriptor, descriptor["descriptor_sha256"], project_root=root.resolve(), capability=cap, synthetic_bootstrap_verification_public_key=public_key),
        lambda: core.plan(future_intent, descriptor, descriptor["descriptor_sha256"], project_root=root.resolve(), capability=cap, synthetic_bootstrap_verification_public_key=public_key),
    ):
        with pytest.raises(core.ContractError) as exc:
            entrypoint()
        assert exc.value.code == "NMRPA_CRPG_COMMITTED_KEY_REF_UNTRUSTED"

    valid_intent = make_intent(root, descriptor, commitment, bootstrap, identity, [pref], **common)
    future_plan = core.plan(valid_intent, descriptor, descriptor["descriptor_sha256"], project_root=root.resolve(), capability=cap, synthetic_bootstrap_verification_public_key=public_key)
    body = future_plan["signed_record"]["record_body"]
    body["issued_at"] = "2099-01-01T00:00:01Z"
    future_plan["signed_record"]["record_body_sha256"] = digest(body, "nmrpa.core_registry.record_body.digest.v1")
    future_plan["signed_record"]["signature"] = signature(
        issuer, future_plan["signed_record"]["record_body_sha256"],
        credential_id=issuer_credential["credential_id"], credential_ref=issuer_cref,
        mode="committed_registry_issuer",
    )
    future_plan["signed_record"]["signed_record_sha256"] = digest(
        {key: value for key, value in future_plan["signed_record"].items() if key != "signed_record_sha256"},
        "nmrpa.core_registry.signed_record.digest.v1",
    )
    journal = future_plan["journal"]
    journal.update({"prepared_at": "2099-01-01T00:00:02Z", "signed_record_sha256": future_plan["signed_record"]["signed_record_sha256"]})
    journal["synthetic_commit_signature"] = signature(
        bootstrap, core._attestation_digest(journal, "synthetic_commit_signature", "journal_sha256", "nmrpa.core_registry.transaction_journal.commit_attestation.v1"),
    )
    journal["journal_sha256"] = digest({key: value for key, value in journal.items() if key != "journal_sha256"}, "nmrpa.core_registry.transaction_journal.digest.v1")
    marker = future_plan["commit_marker"]
    marker.update({"prepared_at": "2099-01-01T00:00:02Z", "committed_at": "2099-01-01T00:00:03Z", "record_body_sha256": future_plan["signed_record"]["record_body_sha256"], "signed_record_sha256": future_plan["signed_record"]["signed_record_sha256"], "journal_sha256": journal["journal_sha256"]})
    marker["synthetic_commit_signature"] = signature(
        bootstrap, core._attestation_digest(marker, "synthetic_commit_signature", "commit_sha256", "nmrpa.core_registry.commit_marker.commit_attestation.v1"),
    )
    marker["commit_sha256"] = digest({key: value for key, value in marker.items() if key != "commit_sha256"}, "nmrpa.core_registry.commit_marker.digest.v1")
    head = future_plan["new_head"]
    head.update({"committed_at": "2099-01-01T00:00:03Z", "record_body_sha256": future_plan["signed_record"]["record_body_sha256"], "signed_record_sha256": future_plan["signed_record"]["signed_record_sha256"], "journal_sha256": journal["journal_sha256"], "commit_sha256": marker["commit_sha256"]})
    head["head_sha256"] = digest({key: value for key, value in head.items() if key != "head_sha256"}, "nmrpa.core_registry.committed_head.digest.v1")
    future_plan["new_history"][-1] = head
    future_plan["plan_sha256"] = digest({key: value for key, value in future_plan.items() if key != "plan_sha256"}, "nmrpa.core_registry.transaction_plan.synthetic.v1")
    assert core.validate_plan(future_plan, descriptor, descriptor["descriptor_sha256"])["status"] == "LOGICALLY_VALID_UNTRUSTED_PLAN"
    with pytest.raises(core.ContractError) as exc:
        core.commit(future_plan, descriptor, descriptor["descriptor_sha256"], project_root=root.resolve(), capability=cap, synthetic_bootstrap_verification_public_key=public_key)
    assert exc.value.code == "NMRPA_CRPG_COMMITTED_KEY_REF_UNTRUSTED"


def test_all_concrete_identity_plan_integer_selectors_reject_python_aliases(chain):
    root, descriptor, cap, commitment, bootstrap, issuer, principal, pref, issuer_identity, _, issuer_credential, issuer_cref = chain
    identity = seal_domain({"schema_version": core.DOMAIN_VERSIONS["identity_registered"], "transition_id": "transition_" + "e" * 32, "event_kind": "identity_registered", "identity_id": "identity_" + "e" * 32, "principal_id": principal["principal_id"], "principal_registration_ref": pref, "role": "validator", "display_name": "Concrete Selector Identity", "valid_from": "2099-01-01T00:00:00Z", "valid_until": None, "status": "active", "effective_at": "2099-01-01T00:00:00Z"}, "identity_registered")
    intent = make_intent(root, descriptor, commitment, bootstrap, identity, [pref], signer_private=issuer, signer_identity_id=issuer_identity["identity_id"], signer_credential_id=issuer_credential["credential_id"], signer_credential_ref=issuer_cref, serial=800)
    plan = core.plan(intent, descriptor, descriptor["descriptor_sha256"], project_root=root.resolve(), capability=cap, synthetic_bootstrap_verification_public_key=key_bytes(bootstrap))
    selectors = [
        ("root_instance", "st_dev"), ("root_instance", "st_ino"),
        ("expected_previous_head", "sequence"), ("expected_previous_head", "root_instance", "st_dev"), ("expected_previous_head", "root_instance", "st_ino"),
        ("domain_object", "principal_registration_ref", "sequence"), ("domain_object", "principal_registration_ref", "historical_head_sequence"),
        ("domain_object", "principal_registration_ref", "root_instance", "st_dev"), ("domain_object", "principal_registration_ref", "root_instance", "st_ino"),
        ("signed_record", "root_instance", "st_dev"), ("signed_record", "root_instance", "st_ino"),
        ("signed_record", "record_body", "sequence"), ("signed_record", "record_body", "root_instance", "st_dev"), ("signed_record", "record_body", "root_instance", "st_ino"),
        ("signed_record", "record_body", "ordered_prerequisite_refs", 0, "sequence"), ("signed_record", "record_body", "ordered_prerequisite_refs", 0, "historical_head_sequence"),
        ("signed_record", "record_body", "ordered_prerequisite_refs", 0, "root_instance", "st_dev"), ("signed_record", "record_body", "ordered_prerequisite_refs", 0, "root_instance", "st_ino"),
        ("signed_record", "signature", "credential_registration_ref", "sequence"), ("signed_record", "signature", "credential_registration_ref", "historical_head_sequence"),
        ("signed_record", "signature", "credential_registration_ref", "root_instance", "st_dev"), ("signed_record", "signature", "credential_registration_ref", "root_instance", "st_ino"),
        ("journal", "sequence"), ("journal", "root_instance", "st_dev"), ("journal", "root_instance", "st_ino"),
        ("commit_marker", "sequence"), ("commit_marker", "root_instance", "st_dev"), ("commit_marker", "root_instance", "st_ino"),
        ("new_head", "sequence"), ("new_head", "root_instance", "st_dev"), ("new_head", "root_instance", "st_ino"),
        ("new_history", 0, "sequence"),
        ("new_history", 1, "sequence"), ("new_history", 1, "root_instance", "st_dev"), ("new_history", 1, "root_instance", "st_ino"),
        ("new_history", 2, "sequence"), ("new_history", 2, "root_instance", "st_dev"), ("new_history", 2, "root_instance", "st_ino"),
    ]
    aliases = [True, 1.0, Decimal("1"), np.int64(1), type("SelectorIntChild", (int,), {})(1)]
    for selector in selectors:
        for alias in aliases:
            candidate = copy.deepcopy(plan)
            cursor = candidate
            for component in selector[:-1]:
                cursor = cursor[component]
            cursor[selector[-1]] = alias
            with pytest.raises(core.ContractError) as exc:
                core.validate_plan(candidate, descriptor, descriptor["descriptor_sha256"])
            assert exc.value.code in {"NMRPA_CRPG_EXACT_INTEGER", "NMRPA_CRPG_ROOT_INSTANCE_SCHEMA"}, (selector, alias, exc.value.code)
