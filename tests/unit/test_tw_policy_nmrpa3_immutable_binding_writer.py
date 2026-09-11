from __future__ import annotations

import base64
import copy
import errno
import json
import os
import shutil
import stat
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import tw_policy_nmrpa3_immutable_binding_writer as writer
import tw_policy_nmrpa3_real_trust_bootstrap as trust


SCHEMA = ROOT / "scripts/schemas/tw_policy_nmrpa3_immutable_binding_writer.schema.json"
PLAN_SCHEMA = ROOT / "scripts/schemas/tw_policy_nmrpa3_immutable_binding_transaction_plan.schema.json"


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(trust.canonical_json(value))


def materialize_synthetic_root(tmp_path: Path):
    descriptor = trust.expected_descriptor()
    for store in descriptor["trust_stores"]:
        (tmp_path / store["project_relative_path"]).mkdir(parents=True, exist_ok=True)
    for root in descriptor["root_reservations"]:
        (tmp_path / root["root_project_relative_path"]).mkdir(parents=True, exist_ok=True)
    heads = {}
    for log in descriptor["fixed_logs"]:
        storage = tmp_path / log["storage_project_relative_path"]
        storage.mkdir(parents=True, exist_ok=True)
        (tmp_path / log["journal_locator"]).mkdir(exist_ok=True)
        (tmp_path / log["commit_marker_locator"]).mkdir(exist_ok=True)
        genesis = {
            "schema_version": "nmrpa.log_genesis.v1", "logical_name": log["logical_name"],
            "log_kind": log["log_kind"], "log_id": log["log_id"], "owner_role": trust.OWNER_ROLE,
            "sequence": 0, "previous_head_sha256": None,
        }
        genesis["genesis_sha256"] = trust.digest(genesis, "nmrpa.log.genesis.v1")
        head = {
            "schema_version": "nmrpa.log_head.v1", "logical_name": log["logical_name"],
            "log_id": log["log_id"], "sequence": 0, "previous_head_sha256": None,
            "record_sha256": genesis["genesis_sha256"],
        }
        head["head_sha256"] = trust.digest(head, "nmrpa.log.head.v1")
        write_json(tmp_path / log["genesis_locator"], genesis)
        write_json(tmp_path / log["current_head_locator"], head)
        write_json(tmp_path / log["historical_heads_locator"], [head])
        heads[log["logical_name"]] = head
    return descriptor, heads


def build_intent(descriptor, previous_head, *, suffix="first", target="2099-06-02", authorization_id=None, binding_id=None):
    log = next(row for row in descriptor["fixed_logs"] if row["logical_name"] == "capture_recorder_registration_log")
    tx = f"txn_synthetic_binding_{suffix}"
    binding_id = binding_id or f"synthetic_binding_{suffix}"
    rows = []
    for root in descriptor["root_reservations"]:
        index = root["order"]
        rows.append({
            "order": index,
            "root_ref": {key: root[key] for key in ("root_kind", "root_id", "base_id", "root_project_relative_path", "locator_token")},
            "payload_sha256": trust.digest({"sealed_payload_metadata": root["root_kind"], "suffix": suffix}),
            "payload_size": 1000 + index,
            "media_type": "application/json",
            "schema_identity": {"schema_id": f"synthetic_schema_{root['root_kind']}", "schema_sha256": trust.digest({"schema": root["root_kind"]})},
            "external_anchor": {"anchor_id": f"synthetic_anchor_{root['root_kind']}_{suffix}", "anchor_sha256": trust.digest({"external_anchor": root["root_kind"], "suffix": suffix}), "anchored_at": f"{target}T12:00:00Z"},
        })
    auth = {
        "authorization_id": authorization_id or f"synthetic_authorization_{suffix}", "allowed_binding_id": binding_id,
        "allowed_target_asof": target, "expected_previous_head_sha256": previous_head["head_sha256"],
        "max_consumptions": 1, "consumption_count": 0, "terminal": False,
    }
    auth["authorization_sha256"] = trust.digest(auth, "nmrpa.immutable_binding.authorization.synthetic.v1")
    issuer = {
        "issuer_identity_id": "synthetic_identity_binding_writer",
        "issuer_credential_id": "synthetic_credential_binding_writer",
        "payload_schema_id": "synthetic_schema_binding_transaction",
    }
    intent = {
        "artifact_kind": "binding_intent", "schema_version": writer.INTENT_SCHEMA_VERSION,
        "mode": "synthetic_metadata_only_no_payload_read", "transaction_id": tx,
        "binding_id": binding_id, "target_asof": target, "available_at": f"{target}T12:01:00Z",
        "descriptor_sha256": descriptor["descriptor_sha256"],
        "log_ref": {
            "bootstrap_order": log["bootstrap_order"], "logical_name": log["logical_name"],
            "log_kind": log["log_kind"], "log_id": log["log_id"],
            "head_locator": log["current_head_locator"], "history_locator": log["historical_heads_locator"],
            "journal_locator": log["journal_locator"], "commit_marker_locator": log["commit_marker_locator"],
        },
        "expected_previous_head": previous_head, "authorization": auth, "ordered_bindings": rows,
        "issuer": issuer, "signature": {}, "prepared_at": f"{target}T12:02:00Z",
        "committed_at": f"{target}T12:03:00Z",
    }
    binding_record = {
        "schema_version": writer.RECORD_SCHEMA_VERSION, "binding_id": binding_id,
        "transaction_id": tx, "target_asof": target, "available_at": intent["available_at"],
        "authorization_id": auth["authorization_id"], "authorization_sha256": auth["authorization_sha256"],
        "descriptor_sha256": descriptor["descriptor_sha256"], "ordered_bindings": rows,
    }
    binding_record["binding_record_sha256"] = trust.digest(binding_record, "nmrpa.immutable_binding.record.v1")
    anchor_record = {
        "schema_version": writer.ANCHOR_SCHEMA_VERSION, "anchor_record_id": f"synthetic_anchor_record_{binding_id}",
        "binding_id": binding_id, "binding_record_sha256": binding_record["binding_record_sha256"],
        "ordered_external_anchor_sha256": [row["external_anchor"]["anchor_sha256"] for row in rows],
        "committed_at": intent["committed_at"],
    }
    anchor_record["anchor_record_sha256"] = trust.digest(anchor_record, "nmrpa.immutable_binding.anchor.v1")
    sequence = previous_head["sequence"] + 1
    body = {
        "schema_version": writer.BODY_SCHEMA_VERSION, "log_kind": log["log_kind"], "log_id": log["log_id"],
        "transaction_id": tx, "sequence": sequence,
        "previous_commit_sha256": None if sequence == 1 else previous_head["commit_sha256"],
        "event_type": "immutable_binding_committed", "issued_at": intent["available_at"],
        "issuer_identity_id": issuer["issuer_identity_id"], "issuer_credential_id": issuer["issuer_credential_id"],
        "payload_schema_id": issuer["payload_schema_id"],
        "payload": {"binding_record_sha256": binding_record["binding_record_sha256"], "anchor_record_sha256": anchor_record["anchor_record_sha256"]},
    }
    intent["signature"] = {
        "algorithm": "ed25519", "credential_id": issuer["issuer_credential_id"],
        "signed_digest": trust.digest(body, "nmrpa.commit_record_body.digest.v1"),
        "signature_base64": base64.b64encode(bytes(range(64))).decode(),
    }
    intent["intent_sha256"] = trust.digest(intent, "nmrpa.immutable_binding.intent.synthetic.v1")
    return intent


def reseal(value, field, domain):
    value[field] = trust.digest({key: child for key, child in value.items() if key != field}, domain)


def assert_code(code, callback):
    with pytest.raises(writer.ContractError) as exc:
        callback()
    assert exc.value.code == code


def test_schema_is_valid_and_accepts_exact_intent(tmp_path):
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator.check_schema(json.loads(PLAN_SCHEMA.read_text(encoding="utf-8")))
    descriptor, heads = materialize_synthetic_root(tmp_path)
    intent = build_intent(descriptor, heads["capture_recorder_registration_log"])
    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(intent))
    assert errors == []


def test_plan_is_pure_and_has_exact_five_root_order(tmp_path):
    descriptor, heads = materialize_synthetic_root(tmp_path)
    before = sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*"))
    intent = build_intent(descriptor, heads["capture_recorder_registration_log"])
    plan = writer.plan_binding_transaction(intent, descriptor, descriptor["descriptor_sha256"])
    after = sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*"))
    assert before == after
    assert [row["root_ref"]["root_kind"] for row in plan["binding_record"]["ordered_bindings"]] == list(trust.ROOT_KINDS)
    assert writer.validate_binding_transaction_plan(plan, descriptor, descriptor["descriptor_sha256"])["write_permitted"] is False
    intent_schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    plan_schema = json.loads(PLAN_SCHEMA.read_text(encoding="utf-8"))
    registry = Registry().with_resource(SCHEMA.name, Resource.from_contents(intent_schema))
    errors = list(Draft202012Validator(plan_schema, registry=registry, format_checker=FormatChecker()).iter_errors(plan))
    assert errors == []


@pytest.mark.parametrize("root_kind", trust.ROOT_KINDS)
def test_each_frozen_root_metadata_is_bound(tmp_path, root_kind):
    descriptor, heads = materialize_synthetic_root(tmp_path)
    plan = writer.plan_binding_transaction(build_intent(descriptor, heads["capture_recorder_registration_log"]), descriptor, descriptor["descriptor_sha256"])
    row = next(item for item in plan["binding_record"]["ordered_bindings"] if item["root_ref"]["root_kind"] == root_kind)
    assert row["root_ref"]["root_id"] == f"nmrpa_{root_kind}_root_v1"
    assert set(row) == {"order", "root_ref", "payload_sha256", "payload_size", "media_type", "schema_identity", "external_anchor"}


def test_commit_and_second_append_are_cas_chained(tmp_path):
    descriptor, heads = materialize_synthetic_root(tmp_path)
    cap = writer.issue_synthetic_test_capability(tmp_path.resolve())
    first = writer.plan_binding_transaction(build_intent(descriptor, heads["capture_recorder_registration_log"]), descriptor, descriptor["descriptor_sha256"])
    result = writer.commit_binding_transaction(first, descriptor, descriptor["descriptor_sha256"], tmp_path.resolve(), cap)
    assert result["sequence"] == 1 and result["payload_bytes_read"] == 0
    second_intent = build_intent(descriptor, first["new_head"], suffix="second", target="2099-06-03")
    second = writer.plan_binding_transaction(second_intent, descriptor, descriptor["descriptor_sha256"])
    result2 = writer.commit_binding_transaction(second, descriptor, descriptor["descriptor_sha256"], tmp_path.resolve(), cap)
    assert result2["sequence"] == 2
    history = json.loads((tmp_path / second["paths"]["history"]).read_text())
    assert [row["sequence"] for row in history] == [0, 1, 2]
    assert second["signed_record"]["record_body"]["previous_commit_sha256"] == first["commit_marker"]["commit_sha256"]


@pytest.mark.parametrize("step", range(1, 8))
def test_fault_at_every_commit_step_rolls_back(tmp_path, step):
    descriptor, heads = materialize_synthetic_root(tmp_path)
    cap = writer.issue_synthetic_test_capability(tmp_path.resolve())
    plan = writer.plan_binding_transaction(build_intent(descriptor, heads["capture_recorder_registration_log"], suffix=f"fault{step}"), descriptor, descriptor["descriptor_sha256"])
    before_head = (tmp_path / plan["paths"]["head"]).read_bytes()
    before_history = (tmp_path / plan["paths"]["history"]).read_bytes()
    assert_code("NMRPA_TR_E_SYNTHETIC_FAULT", lambda: writer.commit_binding_transaction(plan, descriptor, descriptor["descriptor_sha256"], tmp_path.resolve(), cap, synthetic_fail_after_step=step))
    assert (tmp_path / plan["paths"]["head"]).read_bytes() == before_head
    assert (tmp_path / plan["paths"]["history"]).read_bytes() == before_history
    assert all(not (tmp_path / rel).exists() for key, rel in plan["paths"].items() if key not in ("head", "history"))
    assert all(not (tmp_path / rel).exists() for rel in plan["staging_paths"].values())


def test_replay_and_stale_head_fail_closed(tmp_path):
    descriptor, heads = materialize_synthetic_root(tmp_path)
    cap = writer.issue_synthetic_test_capability(tmp_path.resolve())
    intent = build_intent(descriptor, heads["capture_recorder_registration_log"])
    plan = writer.plan_binding_transaction(intent, descriptor, descriptor["descriptor_sha256"])
    writer.commit_binding_transaction(plan, descriptor, descriptor["descriptor_sha256"], tmp_path.resolve(), cap)
    assert_code("NMRPA_TR_E_REPLAY", lambda: writer.commit_binding_transaction(plan, descriptor, descriptor["descriptor_sha256"], tmp_path.resolve(), cap))
    stale = writer.plan_binding_transaction(build_intent(descriptor, heads["capture_recorder_registration_log"], suffix="stale"), descriptor, descriptor["descriptor_sha256"])
    assert_code("NMRPA_TR_E_CAS", lambda: writer.commit_binding_transaction(stale, descriptor, descriptor["descriptor_sha256"], tmp_path.resolve(), cap))


def test_authorization_and_binding_id_are_one_shot_across_transactions(tmp_path):
    descriptor, heads = materialize_synthetic_root(tmp_path)
    cap = writer.issue_synthetic_test_capability(tmp_path.resolve())
    first = writer.plan_binding_transaction(build_intent(descriptor, heads["capture_recorder_registration_log"]), descriptor, descriptor["descriptor_sha256"])
    writer.commit_binding_transaction(first, descriptor, descriptor["descriptor_sha256"], tmp_path.resolve(), cap)
    reused_auth = build_intent(descriptor, first["new_head"], suffix="reuseauth", target="2099-06-03", authorization_id=first["binding_record"]["authorization_id"])
    reused_plan = writer.plan_binding_transaction(reused_auth, descriptor, descriptor["descriptor_sha256"])
    assert_code("NMRPA_TR_E_AUTH_REPLAY", lambda: writer.commit_binding_transaction(reused_plan, descriptor, descriptor["descriptor_sha256"], tmp_path.resolve(), cap))

    reused_binding = build_intent(descriptor, first["new_head"], suffix="reusebinding", target="2099-06-03", binding_id=first["binding_record"]["binding_id"])
    binding_plan = writer.plan_binding_transaction(reused_binding, descriptor, descriptor["descriptor_sha256"])
    assert_code("NMRPA_TR_E_REPLAY_CONFLICT", lambda: writer.commit_binding_transaction(binding_plan, descriptor, descriptor["descriptor_sha256"], tmp_path.resolve(), cap))


def test_orphan_and_partial_transaction_are_rejected(tmp_path):
    descriptor, heads = materialize_synthetic_root(tmp_path)
    cap = writer.issue_synthetic_test_capability(tmp_path.resolve())
    plan = writer.plan_binding_transaction(build_intent(descriptor, heads["capture_recorder_registration_log"]), descriptor, descriptor["descriptor_sha256"])
    orphan = tmp_path / plan["paths"]["signed_record"]
    write_json(orphan, plan["signed_record"])
    assert_code("NMRPA_TR_E_ORPHAN_TRANSACTION", lambda: writer.commit_binding_transaction(plan, descriptor, descriptor["descriptor_sha256"], tmp_path.resolve(), cap))


def test_actual_root_and_forged_capability_are_rejected(tmp_path):
    assert_code("NMRPA_TR_E_ACTUAL_ROOT_FORBIDDEN", lambda: writer.issue_synthetic_test_capability(ROOT))
    descriptor, heads = materialize_synthetic_root(tmp_path)
    plan = writer.plan_binding_transaction(build_intent(descriptor, heads["capture_recorder_registration_log"]), descriptor, descriptor["descriptor_sha256"])
    with pytest.raises(TypeError):
        writer.SyntheticTestCapability(str(tmp_path.resolve()), writer.CAPABILITY_NAME, object())


@pytest.mark.parametrize(
    "mutator,code",
    [
        (lambda value: value.update({"unknown": 1}), "NMRPA_TR_E_SCHEMA"),
        (lambda value: value["ordered_bindings"][0].update({"payload_path": "/tmp/source"}), "NMRPA_TR_E_PAYLOAD_INPUT"),
        (lambda value: value["ordered_bindings"][0].update({"payload_bytes": b"payload"}), "NMRPA_TR_E_PAYLOAD_INPUT"),
        (lambda value: value["ordered_bindings"][0].__setitem__("payload_size", True), "NMRPA_TR_E_SCHEMA"),
        (lambda value: value["ordered_bindings"][0].__setitem__("order", True), "NMRPA_TR_E_SCHEMA"),
        (lambda value: value["ordered_bindings"][0]["root_ref"].__setitem__("root_kind", "institutional"), "NMRPA_TR_E_ROOT_PIN"),
        (lambda value: value["ordered_bindings"].__setitem__(1, copy.deepcopy(value["ordered_bindings"][0])), "NMRPA_TR_E_ROOT_ORDER"),
        (lambda value: value.__setitem__("binding_id", "latest"), "NMRPA_TR_E_SCHEMA"),
        (lambda value: value["authorization"].__setitem__("max_consumptions", True), "NMRPA_TR_E_AUTH_REPLAY"),
        (lambda value: value["signature"].__setitem__("signed_digest", "0" * 64), "NMRPA_TR_E_SIGNATURE"),
    ],
)
def test_intent_mutations_fail_closed(tmp_path, mutator, code):
    descriptor, heads = materialize_synthetic_root(tmp_path)
    intent = build_intent(descriptor, heads["capture_recorder_registration_log"])
    mutator(intent)
    try:
        reseal(intent, "intent_sha256", "nmrpa.immutable_binding.intent.synthetic.v1")
    except TypeError:
        pass
    assert_code(code, lambda: writer.plan_binding_transaction(intent, descriptor, descriptor["descriptor_sha256"]))


def test_file_handle_is_rejected_before_planning(tmp_path):
    descriptor, heads = materialize_synthetic_root(tmp_path)
    intent = build_intent(descriptor, heads["capture_recorder_registration_log"])
    with SCHEMA.open("rb") as handle:
        intent["ordered_bindings"][0]["payload_handle"] = handle
        assert_code("NMRPA_TR_E_PAYLOAD_INPUT", lambda: writer.plan_binding_transaction(intent, descriptor, descriptor["descriptor_sha256"]))


def test_plan_path_digest_signature_and_unknown_mutations_fail(tmp_path):
    descriptor, heads = materialize_synthetic_root(tmp_path)
    plan = writer.plan_binding_transaction(build_intent(descriptor, heads["capture_recorder_registration_log"]), descriptor, descriptor["descriptor_sha256"])
    variants = []
    path_drift = copy.deepcopy(plan); path_drift["paths"]["binding"] = "latest/binding.json"; reseal(path_drift, "plan_sha256", "nmrpa.immutable_binding.transaction_plan.synthetic.v1"); variants.append((path_drift, "NMRPA_TR_E_PATH"))
    unknown = copy.deepcopy(plan); unknown["new_head"]["extra"] = 1; reseal(unknown, "plan_sha256", "nmrpa.immutable_binding.transaction_plan.synthetic.v1"); variants.append((unknown, "NMRPA_TR_E_SCHEMA"))
    bad_sig = copy.deepcopy(plan); bad_sig["signed_record"]["signature"]["credential_id"] = "synthetic_other"; reseal(bad_sig["signed_record"], "signed_record_sha256", "nmrpa.signed_record.digest.v1"); reseal(bad_sig, "plan_sha256", "nmrpa.immutable_binding.transaction_plan.synthetic.v1"); variants.append((bad_sig, "NMRPA_TR_E_SIGNATURE"))
    bad_marker = copy.deepcopy(plan); bad_marker["commit_marker"]["journal_sha256"] = "0" * 64; reseal(bad_marker["commit_marker"], "commit_sha256", "nmrpa.commit_marker.digest.v1"); reseal(bad_marker, "plan_sha256", "nmrpa.immutable_binding.transaction_plan.synthetic.v1"); variants.append((bad_marker, "NMRPA_TR_E_MARKER"))
    bad_size = copy.deepcopy(plan); bad_size["binding_record"]["ordered_bindings"][0]["payload_size"] = True; reseal(bad_size["binding_record"], "binding_record_sha256", "nmrpa.immutable_binding.record.v1"); reseal(bad_size, "plan_sha256", "nmrpa.immutable_binding.transaction_plan.synthetic.v1"); variants.append((bad_size, "NMRPA_TR_E_SCHEMA"))
    for value, code in variants:
        assert_code(code, lambda value=value: writer.validate_binding_transaction_plan(value, descriptor, descriptor["descriptor_sha256"]))


def test_symlink_path_is_rejected(tmp_path):
    descriptor, heads = materialize_synthetic_root(tmp_path)
    plan = writer.plan_binding_transaction(build_intent(descriptor, heads["capture_recorder_registration_log"]), descriptor, descriptor["descriptor_sha256"])
    cap = writer.issue_synthetic_test_capability(tmp_path.resolve())
    binding_store = tmp_path / f"{trust.TRUST_BASE_PATH}/stores/binding_store"
    binding_store.rmdir()
    binding_store.symlink_to(tmp_path)
    assert_code("NMRPA_TR_E_SYMLINK", lambda: writer.commit_binding_transaction(plan, descriptor, descriptor["descriptor_sha256"], tmp_path.resolve(), cap))


def test_module_has_no_cli_env_network_or_payload_open_surface():
    source = (ROOT / "scripts/tw_policy_nmrpa3_immutable_binding_writer.py").read_text(encoding="utf-8")
    assert "if __name__" not in source
    assert "argparse" not in source
    assert "os.environ" not in source
    assert "requests" not in source
    assert "payload_path" not in "\n".join(line for line in source.splitlines() if line.startswith("def "))


def test_capability_lifetime_copy_revoke_and_same_path_replacement(tmp_path):
    descriptor, heads = materialize_synthetic_root(tmp_path)
    plan = writer.plan_binding_transaction(build_intent(descriptor, heads["capture_recorder_registration_log"]), descriptor, descriptor["descriptor_sha256"])
    cap = writer.issue_synthetic_test_capability(tmp_path.resolve())
    with pytest.raises(TypeError):
        copy.copy(cap)
    with pytest.raises(TypeError):
        copy.deepcopy(cap)
    with pytest.raises(AttributeError):
        cap._nonce = "forged"
    moved = tmp_path.with_name(tmp_path.name + "-moved")
    tmp_path.rename(moved)
    tmp_path.mkdir()
    materialize_synthetic_root(tmp_path)
    assert_code("NMRPA_TR_E_CAPABILITY", lambda: writer.commit_binding_transaction(plan, descriptor, descriptor["descriptor_sha256"], tmp_path.resolve(), cap))
    writer.revoke_synthetic_test_capability(cap)
    assert_code("NMRPA_TR_E_CAPABILITY", lambda: writer.commit_binding_transaction(plan, descriptor, descriptor["descriptor_sha256"], tmp_path.resolve(), cap))
    shutil.rmtree(moved)


def test_capability_rejects_symlink_and_repository_child(tmp_path):
    link = tmp_path.with_name(tmp_path.name + "-link")
    link.symlink_to(tmp_path, target_is_directory=True)
    assert_code("NMRPA_TR_E_PROJECT_ROOT", lambda: writer.issue_synthetic_test_capability(link))
    assert_code("NMRPA_TR_E_ACTUAL_ROOT_FORBIDDEN", lambda: writer.issue_synthetic_test_capability(ROOT / "scripts"))


def test_capability_nonce_object_setattr_and_double_close_fail_closed(tmp_path):
    descriptor, heads = materialize_synthetic_root(tmp_path)
    plan = writer.plan_binding_transaction(build_intent(descriptor, heads["capture_recorder_registration_log"]), descriptor, descriptor["descriptor_sha256"])
    cap = writer.issue_synthetic_test_capability(tmp_path.resolve())
    original_nonce = cap._nonce
    object.__setattr__(cap, "_nonce", "0" * 64)
    assert_code("NMRPA_TR_E_CAPABILITY", lambda: writer.commit_binding_transaction(plan, descriptor, descriptor["descriptor_sha256"], tmp_path.resolve(), cap))
    object.__setattr__(cap, "_nonce", original_nonce)
    writer.close_synthetic_test_capability(cap)
    assert_code("NMRPA_TR_E_CAPABILITY", lambda: writer.close_synthetic_test_capability(cap))


def test_history_early_corruption_gap_and_digest_fail_closed(tmp_path):
    descriptor, heads = materialize_synthetic_root(tmp_path)
    cap = writer.issue_synthetic_test_capability(tmp_path.resolve())
    first = writer.plan_binding_transaction(build_intent(descriptor, heads["capture_recorder_registration_log"]), descriptor, descriptor["descriptor_sha256"])
    writer.commit_binding_transaction(first, descriptor, descriptor["descriptor_sha256"], tmp_path.resolve(), cap)
    second = writer.plan_binding_transaction(build_intent(descriptor, first["new_head"], suffix="second", target="2099-06-03"), descriptor, descriptor["descriptor_sha256"])
    writer.commit_binding_transaction(second, descriptor, descriptor["descriptor_sha256"], tmp_path.resolve(), cap)
    history_path = tmp_path / second["paths"]["history"]
    history = json.loads(history_path.read_text())
    history[1]["sequence"] = 99
    reseal(history[1], "head_sha256", "nmrpa.committed_head.digest.v1")
    write_json(history_path, history)
    third = writer.plan_binding_transaction(build_intent(descriptor, second["new_head"], suffix="third", target="2099-06-04"), descriptor, descriptor["descriptor_sha256"])
    assert_code("NMRPA_TR_E_CHAIN", lambda: writer.commit_binding_transaction(third, descriptor, descriptor["descriptor_sha256"], tmp_path.resolve(), cap))


@pytest.mark.parametrize("artifact", ["signed_record", "journal", "marker", "binding", "anchor"])
def test_historical_artifact_corruption_and_cross_store_orphan_fail_closed(tmp_path, artifact):
    descriptor, heads = materialize_synthetic_root(tmp_path)
    cap = writer.issue_synthetic_test_capability(tmp_path.resolve())
    first = writer.plan_binding_transaction(build_intent(descriptor, heads["capture_recorder_registration_log"]), descriptor, descriptor["descriptor_sha256"])
    writer.commit_binding_transaction(first, descriptor, descriptor["descriptor_sha256"], tmp_path.resolve(), cap)
    path = tmp_path / first["paths"][artifact]
    value = json.loads(path.read_text())
    value["corrupt"] = True
    write_json(path, value)
    second = writer.plan_binding_transaction(build_intent(descriptor, first["new_head"], suffix=f"after_{artifact}", target="2099-06-03"), descriptor, descriptor["descriptor_sha256"])
    assert_code("NMRPA_TR_E_SCHEMA", lambda: writer.commit_binding_transaction(second, descriptor, descriptor["descriptor_sha256"], tmp_path.resolve(), cap))


def test_replace_then_fsync_failure_is_recorded_and_rolled_back(tmp_path, monkeypatch):
    descriptor, heads = materialize_synthetic_root(tmp_path)
    cap = writer.issue_synthetic_test_capability(tmp_path.resolve())
    plan = writer.plan_binding_transaction(build_intent(descriptor, heads["capture_recorder_registration_log"], suffix="fsync"), descriptor, descriptor["descriptor_sha256"])
    original_replace = writer.os.replace
    original_fsync = writer.os.fsync
    replaced = {"value": False}
    failed = {"value": False}
    def tracked_replace(*args, **kwargs):
        result = original_replace(*args, **kwargs)
        replaced["value"] = True
        return result
    def fail_after_replace(fd):
        if replaced["value"] and not failed["value"]:
            failed["value"] = True
            raise OSError("fault after replace before directory durability")
        return original_fsync(fd)
    monkeypatch.setattr(writer.os, "replace", tracked_replace)
    monkeypatch.setattr(writer.os, "fsync", fail_after_replace)
    with pytest.raises(OSError):
        writer.commit_binding_transaction(plan, descriptor, descriptor["descriptor_sha256"], tmp_path.resolve(), cap)
    assert not (tmp_path / plan["paths"]["binding"]).exists()


def test_restore_failure_is_terminal_and_future_commit_fails_closed(tmp_path, monkeypatch):
    descriptor, heads = materialize_synthetic_root(tmp_path)
    cap = writer.issue_synthetic_test_capability(tmp_path.resolve())
    plan = writer.plan_binding_transaction(build_intent(descriptor, heads["capture_recorder_registration_log"], suffix="restore"), descriptor, descriptor["descriptor_sha256"])
    original_replace = writer.os.replace
    calls = {"count": 0}
    def fail_first_restore(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 8:
            raise OSError("restore replace failed")
        return original_replace(*args, **kwargs)
    monkeypatch.setattr(writer.os, "replace", fail_first_restore)
    assert_code("NMRPA_TR_E_ROLLBACK_FAILURE", lambda: writer.commit_binding_transaction(plan, descriptor, descriptor["descriptor_sha256"], tmp_path.resolve(), cap, synthetic_fail_after_step=7))
    assert_code("NMRPA_TR_E_ROLLBACK_FAILURE", lambda: writer.commit_binding_transaction(plan, descriptor, descriptor["descriptor_sha256"], tmp_path.resolve(), cap))


def test_cleanup_failure_is_terminal(tmp_path, monkeypatch):
    descriptor, heads = materialize_synthetic_root(tmp_path)
    cap = writer.issue_synthetic_test_capability(tmp_path.resolve())
    plan = writer.plan_binding_transaction(build_intent(descriptor, heads["capture_recorder_registration_log"], suffix="cleanup"), descriptor, descriptor["descriptor_sha256"])
    original_unlink = writer.os.unlink
    failed = {"value": False}
    def fail_cleanup(*args, **kwargs):
        if not failed["value"]:
            failed["value"] = True
            raise OSError("cleanup unlink failed")
        return original_unlink(*args, **kwargs)
    monkeypatch.setattr(writer.os, "unlink", fail_cleanup)
    assert_code("NMRPA_TR_E_ROLLBACK_FAILURE", lambda: writer.commit_binding_transaction(plan, descriptor, descriptor["descriptor_sha256"], tmp_path.resolve(), cap, synthetic_fail_after_step=1))


def test_post_validation_failure_and_sequence_two_rollback(tmp_path, monkeypatch):
    descriptor, heads = materialize_synthetic_root(tmp_path)
    cap = writer.issue_synthetic_test_capability(tmp_path.resolve())
    first = writer.plan_binding_transaction(build_intent(descriptor, heads["capture_recorder_registration_log"]), descriptor, descriptor["descriptor_sha256"])
    writer.commit_binding_transaction(first, descriptor, descriptor["descriptor_sha256"], tmp_path.resolve(), cap)
    second = writer.plan_binding_transaction(build_intent(descriptor, first["new_head"], suffix="postfail", target="2099-06-03"), descriptor, descriptor["descriptor_sha256"])
    original = writer._validate_all_substrate_closure
    calls = {"count": 0}
    def fail_post(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 2:
            raise writer.ContractError("NMRPA_TR_E_POST_COMMIT", "injected full closure validation failure")
        return original(*args, **kwargs)
    monkeypatch.setattr(writer, "_validate_all_substrate_closure", fail_post)
    assert_code("NMRPA_TR_E_POST_COMMIT", lambda: writer.commit_binding_transaction(second, descriptor, descriptor["descriptor_sha256"], tmp_path.resolve(), cap))
    history = json.loads((tmp_path / second["paths"]["history"]).read_text())
    assert [row["sequence"] for row in history] == [0, 1]


def test_python_and_schema_reject_bool_sequence_equivalently(tmp_path):
    descriptor, heads = materialize_synthetic_root(tmp_path)
    plan = writer.plan_binding_transaction(build_intent(descriptor, heads["capture_recorder_registration_log"]), descriptor, descriptor["descriptor_sha256"])
    plan["journal"]["sequence"] = True
    reseal(plan["journal"], "journal_sha256", "nmrpa.transaction_journal.digest.v1")
    reseal(plan, "plan_sha256", "nmrpa.immutable_binding.transaction_plan.synthetic.v1")
    assert_code("NMRPA_TR_E_SCHEMA", lambda: writer.validate_binding_transaction_plan(plan, descriptor, descriptor["descriptor_sha256"]))
    intent_schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    plan_schema = json.loads(PLAN_SCHEMA.read_text(encoding="utf-8"))
    registry = Registry().with_resource(SCHEMA.name, Resource.from_contents(intent_schema))
    assert list(Draft202012Validator(plan_schema, registry=registry).iter_errors(plan))


@pytest.mark.parametrize(
    "path,value",
    [
        (("expected_previous_head", "sequence"), False),
        (("binding_record", "ordered_bindings", 0, "payload_size"), True),
        (("anchor_record", "ordered_external_anchor_sha256", 0), False),
        (("signed_record", "record_body", "sequence"), True),
        (("journal", "sequence"), True),
        (("commit_marker", "sequence"), True),
        (("new_head", "sequence"), True),
        (("paths", "binding"), 1),
        (("staging_paths", "head"), False),
        (("commit_order", 0), True),
    ],
)
def test_plan_recursive_exact_type_python_schema_mutation_equivalence(tmp_path, path, value):
    descriptor, heads = materialize_synthetic_root(tmp_path)
    plan = writer.plan_binding_transaction(build_intent(descriptor, heads["capture_recorder_registration_log"]), descriptor, descriptor["descriptor_sha256"])
    cursor = plan
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    reseal(plan, "plan_sha256", "nmrpa.immutable_binding.transaction_plan.synthetic.v1")
    with pytest.raises(writer.ContractError):
        writer.validate_binding_transaction_plan(plan, descriptor, descriptor["descriptor_sha256"])
    intent_schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    plan_schema = json.loads(PLAN_SCHEMA.read_text(encoding="utf-8"))
    registry = Registry().with_resource(SCHEMA.name, Resource.from_contents(intent_schema))
    assert list(Draft202012Validator(plan_schema, registry=registry).iter_errors(plan))


def test_schema_rejects_cross_log_tuple_and_python_matches(tmp_path):
    descriptor, heads = materialize_synthetic_root(tmp_path)
    intent = build_intent(descriptor, heads["capture_recorder_registration_log"])
    intent["log_ref"]["log_kind"] = "issuer_registry"
    reseal(intent, "intent_sha256", "nmrpa.immutable_binding.intent.synthetic.v1")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(intent))
    assert_code("NMRPA_TR_E_LOG", lambda: writer.plan_binding_transaction(intent, descriptor, descriptor["descriptor_sha256"]))


def test_unknown_control_file_and_cross_log_orphan_are_rejected(tmp_path):
    descriptor, heads = materialize_synthetic_root(tmp_path)
    cap = writer.issue_synthetic_test_capability(tmp_path.resolve())
    plan = writer.plan_binding_transaction(build_intent(descriptor, heads["capture_recorder_registration_log"]), descriptor, descriptor["descriptor_sha256"])
    log = next(row for row in descriptor["fixed_logs"] if row["logical_name"] == "principal_registry_log")
    write_json(tmp_path / log["journal_locator"] / "txn_synthetic_crosslog12.record.json", {})
    assert_code("NMRPA_TR_E_ORPHAN_TRANSACTION", lambda: writer.commit_binding_transaction(plan, descriptor, descriptor["descriptor_sha256"], tmp_path.resolve(), cap))


def _generic_no_clobber_case(tmp_path):
    descriptor, _ = materialize_synthetic_root(tmp_path)
    cap = writer.issue_synthetic_test_capability(tmp_path.resolve())
    base = "data_tw/artifacts/research/nmrpa/trust_bootstrap_v1/stores/preopened_descriptor_policy"
    write_json(tmp_path / base / "history.json", [])
    write_json(tmp_path / base / "head.json", {"sequence": 0})
    paths = {"object": f"{base}/object.json", "record": f"{base}/record.json", "journal": f"{base}/journal.json", "marker": f"{base}/marker.json", "history": f"{base}/history.json", "head": f"{base}/head.json"}
    plan = {"transaction_id": "txn_synthetic_generic_no_clobber", "authorization_id": "auth_generic_no_clobber", "binding_id": "binding_generic_no_clobber", "expected_previous_head": {"sequence": 0}, "paths": paths, "staging_paths": {key: f"{path}.stage" for key, path in paths.items()}, "commit_order": ["object", "record", "journal", "marker", "history", "head"]}
    before = {"current_head": {"sequence": 0}, "history": [], "transaction_ids": set(), "authorization_ids": set(), "binding_ids": set()}
    def closure(root):
        committed = (root / plan["paths"]["marker"]).exists()
        return {"current_head": json.loads((root / plan["paths"]["head"]).read_text()), "history": json.loads((root / plan["paths"]["history"]).read_text()), "transaction_ids": {plan["transaction_id"]} if committed else set(), "authorization_ids": {plan["authorization_id"]} if committed else set(), "binding_ids": {plan["binding_id"]} if committed else set()}
    return cap, plan, before, closure


def _run_generic_no_clobber(tmp_path, cap, plan, closure, **kwargs):
    return writer.commit_schema_driven_transaction(
        plan, tmp_path.resolve(), cap, validate_plan=lambda value: {"ok": True}, load_closure=closure,
        validate_post_commit=lambda root, value: {"ok": closure(root)["current_head"] == {"sequence": 1}},
        lock_relative_path=Path(plan["paths"]["head"]).parent.as_posix(),
        immutable_values={key: {"key": key} for key in ("object", "record", "journal", "marker")},
        mutable_values={"history": [{"sequence": 1}], "head": {"sequence": 1}},
        immutable_final_no_clobber=True, **kwargs,
    )


def test_generic_immutable_no_clobber_nominal_hardlink_postcondition(tmp_path):
    cap, plan, _, closure = _generic_no_clobber_case(tmp_path)
    assert _run_generic_no_clobber(tmp_path, cap, plan, closure)["committed"] is True
    for key in ("object", "record", "journal", "marker"):
        assert os.lstat(tmp_path / plan["paths"][key]).st_nlink == 1


@pytest.mark.parametrize("error", [FileExistsError(), OSError(errno.EXDEV, "cross device"), OSError(errno.EPERM, "denied"), OSError(errno.EOPNOTSUPP, "unsupported")])
def test_generic_immutable_no_clobber_link_failure_has_no_fallback(tmp_path, monkeypatch, error):
    cap, plan, before, closure = _generic_no_clobber_case(tmp_path)
    monkeypatch.setattr(writer.os, "link", lambda *args, **kwargs: (_ for _ in ()).throw(error))
    with pytest.raises(writer.ContractError) as exc:
        _run_generic_no_clobber(tmp_path, cap, plan, closure)
    assert exc.value.code in {"NMRPA_TR_E_IMMUTABLE_FINAL_EXISTS", "NMRPA_TR_E_IMMUTABLE_LINK_UNSUPPORTED"}
    assert closure(tmp_path.resolve()) == before
    assert all(not (tmp_path / plan["paths"][key]).exists() for key in ("object", "record", "journal", "marker"))


@pytest.mark.parametrize("step", range(1, 7))
def test_generic_immutable_no_clobber_fault_rolls_back_all_six_steps(tmp_path, step):
    cap, plan, before, closure = _generic_no_clobber_case(tmp_path)
    with pytest.raises(writer.ContractError) as exc:
        _run_generic_no_clobber(tmp_path, cap, plan, closure, synthetic_fail_after_step=step)
    assert exc.value.code == "NMRPA_TR_E_SYNTHETIC_FAULT"
    assert closure(tmp_path.resolve()) == before


@pytest.mark.parametrize("parent_fsync_ordinal", [1, 2])
def test_generic_no_clobber_parent_fsync_failure_rolls_back(tmp_path, monkeypatch, parent_fsync_ordinal):
    cap, plan, before, closure = _generic_no_clobber_case(tmp_path)
    original = writer.os.fsync
    seen = 0

    def fail_selected_parent(fd):
        nonlocal seen
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            seen += 1
            if seen == parent_fsync_ordinal:
                raise OSError(errno.EIO, "injected parent fsync failure")
        return original(fd)

    monkeypatch.setattr(writer.os, "fsync", fail_selected_parent)
    with pytest.raises(OSError):
        _run_generic_no_clobber(tmp_path, cap, plan, closure)
    assert closure(tmp_path.resolve()) == before
    assert all(not (tmp_path / path).exists() for key, path in plan["paths"].items() if key not in ("history", "head"))


def test_generic_no_clobber_staging_unlink_failure_rolls_back(tmp_path, monkeypatch):
    cap, plan, before, closure = _generic_no_clobber_case(tmp_path)
    original = writer.os.unlink
    failed = False

    def fail_first_stage(name, *args, **kwargs):
        nonlocal failed
        if not failed and str(name).endswith(".stage"):
            failed = True
            raise OSError(errno.EIO, "injected staging unlink failure")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(writer.os, "unlink", fail_first_stage)
    with pytest.raises(OSError):
        _run_generic_no_clobber(tmp_path, cap, plan, closure)
    assert closure(tmp_path.resolve()) == before


@pytest.mark.parametrize("attack", ["type", "bytes", "inode", "nlink"])
def test_generic_no_clobber_postcondition_attack_rolls_back(tmp_path, monkeypatch, attack):
    cap, plan, before, closure = _generic_no_clobber_case(tmp_path)
    original_fstat = writer.os.fstat
    original_read = writer.os.read
    regular_fstat_calls = 0
    corrupt_read = False

    def attacked_fstat(fd):
        nonlocal regular_fstat_calls, corrupt_read
        result = original_fstat(fd)
        if stat.S_ISREG(result.st_mode):
            regular_fstat_calls += 1
            if regular_fstat_calls == 2:
                values = list(result)
                if attack == "type": values[0] = stat.S_IFDIR | 0o700
                elif attack == "inode": values[1] += 1
                elif attack == "nlink": values[3] += 1
                elif attack == "bytes": corrupt_read = True
                return os.stat_result(values)
        return result

    def attacked_read(fd, size):
        nonlocal corrupt_read
        value = original_read(fd, size)
        if corrupt_read and value:
            corrupt_read = False
            return bytes([value[0] ^ 1]) + value[1:]
        return value

    monkeypatch.setattr(writer.os, "fstat", attacked_fstat)
    monkeypatch.setattr(writer.os, "read", attacked_read)
    with pytest.raises(writer.ContractError) as exc:
        _run_generic_no_clobber(tmp_path, cap, plan, closure)
    assert exc.value.code == "NMRPA_TR_E_IMMUTABLE_POSTCONDITION"
    assert closure(tmp_path.resolve()) == before


def test_generic_no_clobber_rollback_identity_failure_taints_root(tmp_path, monkeypatch):
    cap, plan, _, closure = _generic_no_clobber_case(tmp_path)
    original = writer._remove_installed_immutable

    def reject_identity(*args, **kwargs):
        raise writer.ContractError("NMRPA_TR_E_ROLLBACK_FAILURE", "injected immutable identity mismatch")

    monkeypatch.setattr(writer, "_remove_installed_immutable", reject_identity)
    with pytest.raises(writer.ContractError) as exc:
        _run_generic_no_clobber(tmp_path, cap, plan, closure, synthetic_fail_after_step=1)
    assert exc.value.code == "NMRPA_TR_E_ROLLBACK_FAILURE"
    monkeypatch.setattr(writer, "_remove_installed_immutable", original)
    with pytest.raises(writer.ContractError) as tainted:
        writer.describe_synthetic_test_capability(cap, tmp_path.resolve())
    assert tainted.value.code == "NMRPA_TR_E_ROLLBACK_FAILURE"


def test_generic_no_clobber_rollback_closure_rescan_failure_taints_root(tmp_path):
    cap, plan, _, closure = _generic_no_clobber_case(tmp_path)
    calls = 0

    def failing_rescan(root):
        nonlocal calls
        calls += 1
        if calls >= 2:
            raise writer.ContractError("NMRPA_TR_E_ORPHAN_TRANSACTION", "injected closure rescan failure")
        return closure(root)

    with pytest.raises(writer.ContractError) as exc:
        writer.commit_schema_driven_transaction(
            plan, tmp_path.resolve(), cap, validate_plan=lambda value: {"ok": True}, load_closure=failing_rescan,
            validate_post_commit=lambda root, value: {"ok": True},
            lock_relative_path=Path(plan["paths"]["head"]).parent.as_posix(),
            immutable_values={key: {"key": key} for key in ("object", "record", "journal", "marker")},
            mutable_values={"history": [{"sequence": 1}], "head": {"sequence": 1}},
            immutable_final_no_clobber=True, synthetic_fail_after_step=1,
        )
    assert exc.value.code == "NMRPA_TR_E_ROLLBACK_FAILURE"
    with pytest.raises(writer.ContractError) as tainted:
        writer.describe_synthetic_test_capability(cap, tmp_path.resolve())
    assert tainted.value.code == "NMRPA_TR_E_ROLLBACK_FAILURE"
