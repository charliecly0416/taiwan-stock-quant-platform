import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

import sys
sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))
import tw_policy_nmrpa3_optional_source_trust as trust


def package():
    base = Path(__file__).parents[2] / trust.BASE
    return [
        json.loads((base / "descriptor.json").read_text()),
        json.loads((base / "fixed_logs/optional_source_binding_log/genesis.json").read_text()),
        json.loads((base / "fixed_logs/optional_source_binding_log/head.json").read_text()),
        json.loads((base / "fixed_logs/optional_source_binding_log/historical_heads.json").read_text()),
        json.loads((Path(__file__).parents[2] / "configs/tw_policy_nmrpa3_optional_source_trust.json").read_text()),
    ]


def rejects(mutator):
    values = package()
    mutator(values)
    with pytest.raises(trust.OptionalSourceValidationError):
        trust.validate_package(*values)


class StrSubclass(str):
    pass


class IntSubclass(int):
    pass


class ListSubclass(list):
    pass


class DictSubclass(dict):
    pass


def test_existing_genesis_package_validates_directly():
    assert trust.validate_package(*package())["sequence"] == 0


@pytest.mark.parametrize("mutator", [
    lambda p: p[0]["profile_roles"].update({"institutional": StrSubclass("institutional_source_profile")}),
    lambda p: p[0]["future_companion_paths"].update({"binding_store": StrSubclass(p[0]["future_companion_paths"]["binding_store"])}),
    lambda p: p[0].update({"source_kinds": ListSubclass(p[0]["source_kinds"])}),
    lambda p: p[0].update({"profile_roles": DictSubclass(p[0]["profile_roles"])}),
    lambda p: p[1].update({"sequence": IntSubclass(0)}),
    lambda p: p[2].update({"record_sha256": StrSubclass(p[2]["record_sha256"])}),
    lambda p: p[3]["heads"][0].update({"log_id": StrSubclass(p[3]["heads"][0]["log_id"])}),
    lambda p: p[3].update({"heads": ListSubclass(p[3]["heads"])}),
    lambda p: p[4].update({"descriptor_path": StrSubclass(p[4]["descriptor_path"])}),
    lambda p: p[4].update({"payload_read_allowed": IntSubclass(0)}),
])
def test_recursive_python_subclasses_rejected(mutator):
    rejects(mutator)


@pytest.mark.parametrize("mutator", [
    lambda p: p[0]["profile_roles"].update({"unknown": "x"}),
    lambda p: p[0]["profile_roles"].pop("margin"),
    lambda p: p[0]["source_kinds"].__setitem__(0, 1),
    lambda p: p[1].update({"sequence": False}),
    lambda p: p[1].update({"unknown": None}),
    lambda p: p[2].pop("record_sha256"),
    lambda p: p[2].update({"sequence": False}),
    lambda p: p[3].update({"heads": {"0": p[2]}}),
    lambda p: p[3]["heads"][0].update({"unknown": "x"}),
    lambda p: p[4].pop("activation"),
    lambda p: p[4].update({"payload_read_allowed": 0}),
    lambda p: p[4].update({"unknown": []}),
])
def test_json_native_mutation_matrix_python_and_schema_agree(mutator):
    values = package()
    mutator(values)
    candidate = dict(zip(("descriptor", "genesis", "head", "historical_heads", "config"), values))
    schema = json.loads((Path(__file__).parents[2] / "scripts/schemas/tw_policy_nmrpa3_optional_source_trust.schema.json").read_text())
    assert list(Draft202012Validator(schema).iter_errors(candidate))
    with pytest.raises(trust.OptionalSourceValidationError):
        trust.validate_package(*values)


@pytest.mark.parametrize("mutator", [
    lambda p: p[0].update({"target_asof": "2026-08-22"}),
    lambda p: p[0].update({"payload": {"bytes": 1}}),
    lambda p: p[0].update({"credential": "x"}),
    lambda p: p[0]["real_payload_read"] if False else p[0].update({"real_payload_read": 1}),
    lambda p: p[1].update({"sequence": True}),
    lambda p: p[1].update({"binding": {}}),
    lambda p: p[2].update({"sequence": 1}),
    lambda p: p[3]["heads"].append(copy.deepcopy(p[2])),
    lambda p: p[4].update({"authorization": {}}),
    lambda p: p[4].update({"payload_read_allowed": 1}),
])
def test_forbidden_or_exact_type_mutations_rejected(mutator):
    rejects(mutator)


def test_descriptor_schema_is_draft_2020_12():
    schema = json.loads((Path(__file__).parents[2] / "scripts/schemas/tw_policy_nmrpa3_optional_source_trust.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
