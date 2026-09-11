from __future__ import annotations

import copy
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "scripts/tw_policy_nmrpa3_real_trust_bootstrap.py"
SPEC = importlib.util.spec_from_file_location("tw_policy_nmrpa3_real_trust_bootstrap", MODULE)
assert SPEC and SPEC.loader
trust = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = trust
SPEC.loader.exec_module(trust)


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")), encoding="utf-8")


def materialize(tmp_path: Path):
    descriptor = trust.expected_descriptor()
    for root in descriptor["root_reservations"]:
        (tmp_path / root["root_project_relative_path"]).mkdir(parents=True)
    for store in descriptor["trust_stores"]:
        (tmp_path / store["project_relative_path"]).mkdir(parents=True)

    marker_store = next(row for row in descriptor["trust_stores"] if row["store_kind"] == "project_root_identity_marker")
    marker = {
        "schema_version": "nmrpa.project_root_identity.v1",
        "bootstrap_id": descriptor["bootstrap_id"],
        "project_root_id": trust.PROJECT_ROOT_ID,
    }
    marker["identity_sha256"] = trust.digest(marker, "nmrpa.project.root.v1")
    write_json(tmp_path / marker_store["project_relative_path"] / "identity.json", marker)

    heads = {}
    for log in descriptor["fixed_logs"]:
        storage = tmp_path / log["storage_project_relative_path"]
        storage.mkdir(parents=True)
        (tmp_path / log["journal_locator"]).mkdir()
        (tmp_path / log["commit_marker_locator"]).mkdir()
        genesis = {
            "schema_version": "nmrpa.log_genesis.v1",
            "logical_name": log["logical_name"],
            "log_kind": log["log_kind"],
            "log_id": log["log_id"],
            "owner_role": trust.OWNER_ROLE,
            "sequence": 0,
            "previous_head_sha256": None,
        }
        genesis["genesis_sha256"] = trust.digest(genesis, "nmrpa.log.genesis.v1")
        head = {
            "schema_version": "nmrpa.log_head.v1",
            "logical_name": log["logical_name"],
            "log_id": log["log_id"],
            "sequence": 0,
            "previous_head_sha256": None,
            "record_sha256": genesis["genesis_sha256"],
        }
        head["head_sha256"] = trust.digest(head, "nmrpa.log.head.v1")
        write_json(tmp_path / log["genesis_locator"], genesis)
        write_json(tmp_path / log["current_head_locator"], head)
        write_json(tmp_path / log["historical_heads_locator"], [head])
        heads[log["logical_name"]] = head["head_sha256"]

    contract_digests = {name: trust.digest({"synthetic_contract": name}) for name in trust.CONTRACT_DIGEST_NAMES}
    pins = trust.CallerPinnedTrust(
        descriptor_sha256=descriptor["descriptor_sha256"],
        project_root_realpath=str(tmp_path.resolve()),
        project_root_identity_sha256=marker["identity_sha256"],
        contract_digests=contract_digests,
        fixed_log_heads=heads,
    )
    return descriptor, pins


def assert_code(code, callback):
    with pytest.raises(trust.ContractError) as exc:
        callback()
    assert exc.value.code == code


def validate_workspace_lifecycle(project_root: Path):
    project_root = project_root.resolve()
    config_path = project_root / "configs/tw_policy_nmrpa3_real_trust_bootstrap.json"
    nmrpa_root = project_root / "data_tw/artifacts/research/nmrpa"
    config_exists = os.path.lexists(config_path)
    root_exists = os.path.lexists(nmrpa_root)

    if not config_exists and not root_exists:
        return {"state": "pre_bootstrap", "payload_bytes_read": 0}
    assert config_exists and root_exists, "partial NMRPA bootstrap lifecycle state"
    assert config_path.is_file() and not config_path.is_symlink()
    assert nmrpa_root.is_dir() and not nmrpa_root.is_symlink()

    expected = trust.expected_descriptor()
    config_bytes = config_path.read_bytes()
    assert config_bytes == trust.canonical_json(expected)
    assert json.loads(config_bytes) == expected

    marker_store = next(
        row for row in expected["trust_stores"]
        if row["store_kind"] == "project_root_identity_marker"
    )
    marker_path = project_root / marker_store["project_relative_path"] / "identity.json"
    marker_bytes = marker_path.read_bytes()
    marker = json.loads(marker_bytes)
    assert marker_bytes == trust.canonical_json(marker)

    heads = {}
    final_json_paths = [marker_path, config_path]
    for log in expected["fixed_logs"]:
        head_path = project_root / log["current_head_locator"]
        head_bytes = head_path.read_bytes()
        head = json.loads(head_bytes)
        assert head_bytes == trust.canonical_json(head)
        heads[log["logical_name"]] = head["head_sha256"]
        final_json_paths.extend(
            project_root / log[field]
            for field in ("genesis_locator", "current_head_locator", "historical_heads_locator")
        )

    assert len(final_json_paths) == 20
    assert all(not os.path.lexists(Path(f"{path}.nmrpa3-tr-b-stage")) for path in final_json_paths)
    assert all(
        not any((project_root / root["root_project_relative_path"]).iterdir())
        for root in expected["root_reservations"]
    )

    contract_digests = {
        name: trust.digest({"synthetic_contract": name})
        for name in trust.CONTRACT_DIGEST_NAMES
    }
    pins = trust.CallerPinnedTrust(
        descriptor_sha256=expected["descriptor_sha256"],
        project_root_realpath=str(project_root),
        project_root_identity_sha256=marker["identity_sha256"],
        contract_digests=contract_digests,
        fixed_log_heads=heads,
    )
    result = trust.validate_storage_layout(expected, pins)
    assert result["ok"] is True
    assert result["reserved_empty_roots"] == 5
    assert len(result["validated_fixed_heads"]) == 6
    assert result["payload_bytes_read"] == 0
    return {"state": "post_bootstrap", **result}


def reseal_auth(auth):
    auth["authorization_sha256"] = trust.checksum_without(
        auth, "authorization_sha256", "nmrpa.synthetic.one_shot.authorization.v1",
    )


def test_positive_descriptor_storage_and_synthetic_authorization(tmp_path):
    descriptor, pins = materialize(tmp_path)
    assert trust.validate_bootstrap_descriptor(descriptor, pins)["root_count"] == 5
    result = trust.validate_storage_layout(descriptor, pins)
    assert result["reserved_empty_roots"] == 5
    assert result["payload_bytes_read"] == 0
    auth = trust.build_synthetic_authorization(descriptor, pins)
    assert trust.validate_one_shot_authorization(auth, descriptor, pins) == {
        "ok": True, "synthetic_only": True, "max_consumptions": 1, "real_target_bound": False,
    }


@pytest.mark.parametrize(
    "mutate,expected_code",
    [
        (lambda d: d.update({"unknown": True}), "NMRPA_TR_E_SCHEMA"),
        (lambda d: d.__setitem__("runtime_overrides", {"path": "/tmp"}), "NMRPA_TR_E_BOOTSTRAP_PIN"),
        (lambda d: d["root_reservations"].reverse(), "NMRPA_TR_E_BOOTSTRAP_PIN"),
        (lambda d: d["root_reservations"][0].__setitem__("root_id", "nmrpa_wrong_root_v1"), "NMRPA_TR_E_BOOTSTRAP_PIN"),
        (lambda d: d["root_reservations"][0].__setitem__("locator_token", "NMRPA_REAL_ROOT_WRONG_V1"), "NMRPA_TR_E_BOOTSTRAP_PIN"),
        (lambda d: d["fixed_logs"][0].__setitem__("log_id", "nmrpa.wrong.v1"), "NMRPA_TR_E_BOOTSTRAP_PIN"),
        (lambda d: d["fixed_logs"][0].__setitem__("owner_role", "source_owner"), "NMRPA_TR_E_BOOTSTRAP_PIN"),
        (lambda d: d["fixed_logs"][0].__setitem__("bootstrap_order", 2), "NMRPA_TR_E_BOOTSTRAP_PIN"),
        (lambda d: d["trust_stores"][0].__setitem__("env_override_allowed", True), "NMRPA_TR_E_BOOTSTRAP_PIN"),
        (lambda d: d["capabilities"].__setitem__("read_payload", True), "NMRPA_TR_E_BOOTSTRAP_PIN"),
    ],
)
def test_descriptor_exact_mapping_and_override_negatives(tmp_path, mutate, expected_code):
    descriptor, pins = materialize(tmp_path)
    mutate(descriptor)
    descriptor["descriptor_sha256"] = trust.checksum_without(
        descriptor, "descriptor_sha256", "nmrpa.real_trust.bootstrap.v1",
    )
    assert_code(expected_code, lambda: trust.validate_bootstrap_descriptor(descriptor, pins))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d["root_reservations"][0].__setitem__("order", True),
        lambda d: d["capabilities"].__setitem__("read_payload", 0),
    ],
)
def test_direct_descriptor_validator_rejects_bool_integer_equivalence(tmp_path, mutate):
    descriptor, pins = materialize(tmp_path)
    mutate(descriptor)
    descriptor["descriptor_sha256"] = trust.checksum_without(
        descriptor, "descriptor_sha256", "nmrpa.real_trust.bootstrap.v1",
    )
    assert_code("NMRPA_TR_E_SCHEMA", lambda: trust.validate_bootstrap_descriptor(descriptor, pins))


def test_caller_pins_cannot_be_replaced_by_resigned_package(tmp_path):
    descriptor, pins = materialize(tmp_path)
    changed = copy.deepcopy(descriptor)
    changed["bootstrap_id"] = "nmrpa.real_trust.bootstrap.v2"
    changed["descriptor_sha256"] = trust.checksum_without(changed, "descriptor_sha256", "nmrpa.real_trust.bootstrap.v1")
    replaced_pins = copy.copy(pins)
    object.__setattr__(replaced_pins, "descriptor_sha256", changed["descriptor_sha256"])
    assert_code("NMRPA_TR_E_BOOTSTRAP_PIN", lambda: trust.validate_bootstrap_descriptor(changed, replaced_pins))


@pytest.mark.parametrize("unsafe", ["/tmp/x", "../x", "data_tw/latest/x", "data_tw/current/x", "data_tw/accepted/x", "data_tw/publish/x", "data_tw/*/x", "data_tw\\x"])
def test_path_alias_escape_and_wildcard_rejected(unsafe):
    if "*" in unsafe:
        assert_code("NMRPA_TR_E_PATH", lambda: trust._relative_path(unsafe, "probe", expected="safe/path"))
    else:
        assert_code("NMRPA_TR_E_PATH", lambda: trust._relative_path(unsafe, "probe"))


def test_reserved_root_payload_file_rejected(tmp_path):
    descriptor, pins = materialize(tmp_path)
    root = tmp_path / descriptor["root_reservations"][0]["root_project_relative_path"]
    (root / "payload.bin").write_bytes(b"synthetic-only")
    assert_code("NMRPA_TR_E_PAYLOAD_PRESENT", lambda: trust.validate_storage_layout(descriptor, pins))


def test_symlink_and_wrong_file_types_rejected(tmp_path):
    descriptor, pins = materialize(tmp_path)
    root = tmp_path / descriptor["root_reservations"][0]["root_project_relative_path"]
    root.rmdir()
    root.symlink_to(tmp_path)
    assert_code("NMRPA_TR_E_SYMLINK", lambda: trust.validate_storage_layout(descriptor, pins))

    descriptor, pins = materialize(tmp_path / "second")
    log = descriptor["fixed_logs"][0]
    head = tmp_path / "second" / log["current_head_locator"]
    head.unlink()
    head.mkdir()
    assert_code("NMRPA_TR_E_FILE_TYPE", lambda: trust.validate_storage_layout(descriptor, pins))


def test_missing_store_genesis_and_head_fail_closed(tmp_path):
    descriptor, pins = materialize(tmp_path)
    os.unlink(tmp_path / descriptor["fixed_logs"][0]["genesis_locator"])
    assert_code("NMRPA_TR_E_MISSING_STORAGE", lambda: trust.validate_storage_layout(descriptor, pins))

    descriptor, pins = materialize(tmp_path / "second")
    os.unlink(tmp_path / "second" / descriptor["fixed_logs"][0]["current_head_locator"])
    assert_code("NMRPA_TR_E_MISSING_STORAGE", lambda: trust.validate_storage_layout(descriptor, pins))


def test_storage_marker_rejects_integer_project_root_id_after_reseal(tmp_path):
    descriptor, pins = materialize(tmp_path)
    marker_desc = next(
        row for row in descriptor["trust_stores"]
        if row["store_kind"] == "project_root_identity_marker"
    )
    marker_path = tmp_path / marker_desc["project_relative_path"] / "identity.json"
    marker = json.loads(marker_path.read_text())
    marker["project_root_id"] = 123
    marker["identity_sha256"] = trust.checksum_without(
        marker, "identity_sha256", "nmrpa.project.root.v1",
    )
    write_json(marker_path, marker)
    changed_pins = copy.copy(pins)
    object.__setattr__(changed_pins, "project_root_identity_sha256", marker["identity_sha256"])
    assert_code("NMRPA_TR_E_SCHEMA", lambda: trust.validate_storage_layout(descriptor, changed_pins))


def test_head_rollback_history_rewrite_and_orphans_rejected(tmp_path):
    descriptor, pins = materialize(tmp_path)
    log = descriptor["fixed_logs"][0]
    head_path = tmp_path / log["current_head_locator"]
    head = json.loads(head_path.read_text())
    head["head_sha256"] = "0" * 64
    write_json(head_path, head)
    assert_code("NMRPA_TR_E_HEAD_HISTORY", lambda: trust.validate_storage_layout(descriptor, pins))

    descriptor, pins = materialize(tmp_path / "second")
    log = descriptor["fixed_logs"][0]
    history_path = tmp_path / "second" / log["historical_heads_locator"]
    write_json(history_path, [])
    assert_code("NMRPA_TR_E_HEAD_HISTORY", lambda: trust.validate_storage_layout(descriptor, pins))

    descriptor, pins = materialize(tmp_path / "third")
    log = descriptor["fixed_logs"][0]
    (tmp_path / "third" / log["journal_locator"] / "orphan.json").write_text("{}")
    assert_code("NMRPA_TR_E_ORPHAN_TRANSACTION", lambda: trust.validate_storage_layout(descriptor, pins))

    descriptor, pins = materialize(tmp_path / "fourth")
    log = descriptor["fixed_logs"][0]
    (tmp_path / "fourth" / log["commit_marker_locator"] / "orphan.json").write_text("{}")
    assert_code("NMRPA_TR_E_ORPHAN_TRANSACTION", lambda: trust.validate_storage_layout(descriptor, pins))


@pytest.mark.parametrize(
    "mutate,code",
    [
        (lambda a: a.update({"unknown": True}), "NMRPA_TR_E_SCHEMA"),
        (lambda a: a.__setitem__("authorization_id", "real_authorization"), "NMRPA_TR_E_REAL_AUTH"),
        (lambda a: a.__setitem__("target_placeholder", "2026-08-22"), "NMRPA_TR_E_REAL_TARGET"),
        (lambda a: a["ordered_root_refs"].reverse(), "NMRPA_TR_E_AUTH_SCOPE"),
        (lambda a: a["ordered_root_refs"][0].__setitem__("locator_token", "OVERRIDE"), "NMRPA_TR_E_AUTH_SCOPE"),
        (lambda a: a["required_log_heads"][0].__setitem__("head_sha256", "0" * 64), "NMRPA_TR_E_AUTH_PIN"),
        (lambda a: a["contract_digests"].__setitem__("feature_contract_sha256", "0" * 64), "NMRPA_TR_E_AUTH_PIN"),
        (lambda a: a.__setitem__("allowed_output_root", "data_tw/artifacts/research/nmrpa/output"), "NMRPA_TR_E_LOCATOR"),
        (lambda a: a.__setitem__("external_input_anchor_locator", "package://self-reported"), "NMRPA_TR_E_AUTH_ANCHOR"),
        (lambda a: a.__setitem__("expires_at", "2098-01-01T00:00:00Z"), "NMRPA_TR_E_AUTH_TIME"),
        (lambda a: a.__setitem__("max_consumptions", 2), "NMRPA_TR_E_AUTH_REUSE"),
        (lambda a: a.__setitem__("consumption_count", 1), "NMRPA_TR_E_AUTH_REUSE"),
        (lambda a: a.__setitem__("terminal", True), "NMRPA_TR_E_AUTH_REUSE"),
        (lambda a: a["allow_payload_read"].__setitem__("sealed_only", False), "NMRPA_TR_E_AUTH_SCOPE"),
        (lambda a: a["capabilities"].__setitem__("binding", True), "NMRPA_TR_E_AUTH_CAPABILITY"),
        (lambda a: a["capabilities"].__setitem__("network", True), "NMRPA_TR_E_AUTH_CAPABILITY"),
        (lambda a: a["issuer_proof"].__setitem__("issuer_identity_id", "identity_real"), "NMRPA_TR_E_REAL_AUTH"),
        (lambda a: a["issuer_proof"].__setitem__("credential_status", "revoked"), "NMRPA_TR_E_ISSUER_PROOF"),
        (lambda a: a["issuer_proof"].__setitem__("commit_proof_sha256", "0" * 64), "NMRPA_TR_E_ISSUER_PROOF"),
    ],
)
def test_one_shot_authorization_negative_matrix(tmp_path, mutate, code):
    descriptor, pins = materialize(tmp_path)
    auth = trust.build_synthetic_authorization(descriptor, pins)
    mutate(auth)
    reseal_auth(auth)
    assert_code(code, lambda: trust.validate_one_shot_authorization(auth, descriptor, pins))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda a: a["ordered_root_refs"][0].__setitem__("order", True),
        lambda a: a.__setitem__("max_consumptions", True),
        lambda a: a["capabilities"].__setitem__("network", 0),
    ],
)
def test_direct_authorization_validator_rejects_bool_integer_equivalence(tmp_path, mutate):
    descriptor, pins = materialize(tmp_path)
    auth = trust.build_synthetic_authorization(descriptor, pins)
    mutate(auth)
    reseal_auth(auth)
    assert_code("NMRPA_TR_E_SCHEMA", lambda: trust.validate_one_shot_authorization(auth, descriptor, pins))


def test_authorization_digest_and_signature_are_non_self_referential(tmp_path):
    descriptor, pins = materialize(tmp_path)
    auth = trust.build_synthetic_authorization(descriptor, pins)
    auth["authorization_sha256"] = "0" * 64
    assert_code("NMRPA_TR_E_DIGEST", lambda: trust.validate_one_shot_authorization(auth, descriptor, pins))


def test_schema_is_closed_and_has_no_runtime_install_surface():
    schema = json.loads((ROOT / "scripts/schemas/tw_policy_nmrpa3_real_trust_bootstrap.schema.json").read_text())
    auth_schema = json.loads((ROOT / "scripts/schemas/tw_policy_nmrpa3_real_trust_one_shot_authorization.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator.check_schema(auth_schema)
    assert schema["additionalProperties"] is False
    assert schema["properties"]["runtime_overrides"]["maxProperties"] == 0
    forbidden = {"requests", "urllib", "psycopg", "sqlalchemy", "subprocess", "argparse"}
    assert forbidden.isdisjoint(trust.__dict__)
    assert not hasattr(trust, "main")


def test_static_schemas_accept_only_the_synthetic_positive_shapes(tmp_path):
    descriptor, pins = materialize(tmp_path)
    auth = trust.build_synthetic_authorization(descriptor, pins)
    descriptor_schema = json.loads((ROOT / "scripts/schemas/tw_policy_nmrpa3_real_trust_bootstrap.schema.json").read_text())
    auth_schema = json.loads((ROOT / "scripts/schemas/tw_policy_nmrpa3_real_trust_one_shot_authorization.schema.json").read_text())
    Draft202012Validator(descriptor_schema).validate(descriptor)
    Draft202012Validator(auth_schema).validate(auth)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d["root_reservations"][0].__setitem__("root_id", "arbitrary"),
        lambda d: d["fixed_logs"][0].__setitem__("log_id", "arbitrary"),
        lambda d: d["trust_stores"][0].__setitem__("store_id", "arbitrary"),
        lambda d: d["root_reservations"][1].__setitem__("order", 1),
    ],
)
def test_bootstrap_schema_rejects_static_mapping_drift(tmp_path, mutate):
    descriptor, _ = materialize(tmp_path)
    schema = json.loads(
        (ROOT / "scripts/schemas/tw_policy_nmrpa3_real_trust_bootstrap.schema.json").read_text()
    )
    mutate(descriptor)
    descriptor["descriptor_sha256"] = trust.checksum_without(
        descriptor, "descriptor_sha256", "nmrpa.real_trust.bootstrap.v1",
    )
    assert not Draft202012Validator(schema).is_valid(descriptor)


def test_actual_workspace_nmrpa_storage_lifecycle_is_fail_closed(tmp_path):
    assert validate_workspace_lifecycle(tmp_path) == {
        "state": "pre_bootstrap", "payload_bytes_read": 0,
    }

    config_only = tmp_path / "config_only"
    write_json(
        config_only / "configs/tw_policy_nmrpa3_real_trust_bootstrap.json",
        trust.expected_descriptor(),
    )
    with pytest.raises(AssertionError, match="partial NMRPA bootstrap lifecycle state"):
        validate_workspace_lifecycle(config_only)

    root_only = tmp_path / "root_only"
    (root_only / "data_tw/artifacts/research/nmrpa").mkdir(parents=True)
    with pytest.raises(AssertionError, match="partial NMRPA bootstrap lifecycle state"):
        validate_workspace_lifecycle(root_only)

    actual = validate_workspace_lifecycle(ROOT)
    assert actual["state"] == "post_bootstrap"
    assert actual["reserved_empty_roots"] == 5
    assert len(actual["validated_fixed_heads"]) == 6
    assert actual["payload_bytes_read"] == 0
