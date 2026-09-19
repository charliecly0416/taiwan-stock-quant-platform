from __future__ import annotations

import copy
import importlib.util
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


builder = load(
    "build_modelb_b19r2r_v4_composite_source_run_20260916",
    "scripts/build_modelb_b19r2r_v4_composite_source_run_20260916.py",
)
validator = load(
    "validate_modelb_b19r2r_v4_composite_source_run_20260916",
    "scripts/validate_modelb_b19r2r_v4_composite_source_run_20260916.py",
)


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def thaw(output: Path) -> None:
    os.chmod(output, 0o755)
    for path in output.iterdir():
        os.chmod(path, 0o644)


@pytest.fixture
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    output_root = tmp_path / "composite"
    output_root.mkdir()
    protected = tmp_path / "protected.json"
    protected.write_text("stable\n", encoding="ascii")
    monkeypatch.setattr(builder, "OUT_ROOT", output_root)
    monkeypatch.setattr(builder, "PROTECTED", (protected,))
    roles = list(builder.REQUIRED_ROLES)
    times = ["2026-09-16T10:33:29+00:00", "2026-09-16T14:48:33+00:00", "2026-09-16T14:52:13+00:00", "2026-09-16T14:57:25+00:00", "2026-09-16T18:29:00.785090+00:00"]
    children = [
        {
            "role": role,
            "provider": "fixture",
            "source_id": role,
            "physical_run_id": builder.FINMIND_RUN_ID if index < 3 else f"physical.{role}",
            "asof": builder.ASOF,
            "trade_date": builder.ASOF,
            "fetched_at": times[index],
            "available_at": times[index],
            "pit_status": "PASS",
            "validator_status": "PASS",
        }
        for index, role in enumerate(roles)
    ]
    children[3] = {
        **children[3],
        "source_id": builder.MODEL_A_ID,
        "physical_run_id": builder.MODEL_A_RUN.name,
        "supporting_physical_run_ids": [
            builder.MODEL_A_SECONDARY_RUN.name,
            "dng9_daily_auto_model_signal_gate_fixture",
        ],
        "available_at": "2026-09-16T14:57:47+00:00",
        "primary_inference": {
            "physical_run_id": builder.MODEL_A_RUN.name,
            "available_at": "2026-09-16T14:57:25+00:00",
            "selection_role": "exact50_scoring_source",
        },
        "model_identity": {"model_id": builder.MODEL_A_ID},
        "secondary_identity_attestation": {
            "physical_run_id": "dng9_daily_auto_model_signal_gate_fixture",
            "upstream_physical_run_id": builder.MODEL_A_SECONDARY_RUN.name,
            "upstream_available_at": "2026-09-16T14:57:46+00:00",
            "available_at": "2026-09-16T14:57:47+00:00",
            "allowed_use": "canonical_model_id_and_exact_prediction_parity_attestation_only",
            "pit_timing_authority": False,
            "source_prediction_equals_primary": True,
        },
    }
    calendar_lineage = {
        "base_row_count": 2846,
        "base_last_date": "2026-09-15",
        "appended_dates": [builder.ASOF],
        "removed_nontrading_placeholders": ["2026-07-10"],
        "target_finmind_price_present": True,
        "target_model_a_prediction_present": True,
        "extended_row_count": 2847,
    }

    def finmind(role: str, unused: Path):
        return dict(children[roles.index(role)])

    monkeypatch.setattr(builder, "finmind_child", finmind)
    monkeypatch.setattr(builder, "model_a_child", lambda: dict(children[3]))
    monkeypatch.setattr(builder, "yahoo_child", lambda: dict(children[4]))
    monkeypatch.setattr(
        builder,
        "extended_calendar",
        lambda: (["2026-09-15", builder.ASOF], dict(calendar_lineage)),
    )
    return output_root, children


def test_build_and_independent_validator_bind_children_and_calendar(isolated) -> None:
    output_root, _ = isolated
    output = output_root / "logical_composite_v1"
    result = builder.build(output, "2026-09-16T18:30:00+00:00")
    assert result["source_run_kind"] == "logical_composite"
    assert result["capture_authorized"] is False
    checked = validator.validate(output)
    assert checked["status"] == "PASS"
    assert checked["child_count"] == 5
    assert output.stat().st_mode & 0o777 == 0o555
    assert all(path.stat().st_mode & 0o777 == 0o444 for path in output.iterdir())


def test_arbitrary_shared_logical_id_is_rejected(isolated) -> None:
    output_root, _ = isolated
    output = output_root / "logical_composite_v1"
    builder.build(output, "2026-09-16T18:30:00+00:00")
    thaw(output)
    path = output / "COMPOSITE_SOURCE_RUN_MANIFEST.json"
    manifest = builder.read_json(path)
    manifest["logical_source_run_id"] = "arbitrary.same.string"
    write_json(path, manifest)
    with pytest.raises(validator.ValidationError) as caught:
        validator.validate(output)
    assert caught.value.code == "B19V4IV_E_MANIFEST_BINDING"


def test_rewritten_physical_child_is_rejected_even_if_inventory_is_rehashed(isolated) -> None:
    output_root, _ = isolated
    output = output_root / "logical_composite_v1"
    builder.build(output, "2026-09-16T18:30:00+00:00")
    thaw(output)
    inventory_path = output / "CHILD_INVENTORY.json"
    manifest_path = output / "COMPOSITE_SOURCE_RUN_MANIFEST.json"
    inventory = builder.read_json(inventory_path)
    inventory["children"][0]["physical_run_id"] = "rewritten.physical.id"
    write_json(inventory_path, inventory)
    digest = builder.sha256(inventory_path)
    manifest = builder.read_json(manifest_path)
    manifest["logical_source_run_id"] = f"research.logical_composite.20260916.{digest[:20]}"
    manifest["physical_run_ids"][0] = "rewritten.physical.id"
    manifest["child_inventory"]["sha256"] = digest
    manifest["child_inventory"]["bytes"] = inventory_path.stat().st_size
    manifest["child_inventory_sha256"] = digest
    write_json(manifest_path, manifest)
    with pytest.raises(validator.ValidationError) as caught:
        validator.validate(output)
    assert caught.value.code == "B19V4IV_E_CHILD_LINEAGE"


def test_calendar_tamper_is_rejected(isolated) -> None:
    output_root, _ = isolated
    output = output_root / "logical_composite_v1"
    builder.build(output, "2026-09-16T18:30:00+00:00")
    thaw(output)
    (output / "EXTENDED_CLEAN_CALENDAR.txt").write_text("2026-09-15\n2026-07-10\n2026-09-16\n", encoding="ascii")
    with pytest.raises(validator.ValidationError) as caught:
        validator.validate(output)
    assert caught.value.code == "B19V4IV_E_CALENDAR_CONTENT"


def test_inventory_digest_mismatch_is_rejected(isolated) -> None:
    output_root, _ = isolated
    output = output_root / "logical_composite_v1"
    builder.build(output, "2026-09-16T18:30:00+00:00")
    thaw(output)
    path = output / "COMPOSITE_SOURCE_RUN_MANIFEST.json"
    manifest = builder.read_json(path)
    manifest["child_inventory"]["sha256"] = "0" * 64
    write_json(path, manifest)
    with pytest.raises(validator.ValidationError) as caught:
        validator.validate(output)
    assert caught.value.code == "B19V4IV_E_INVENTORY_HASH"


def test_freeze_at_or_after_next_open_is_rejected(isolated) -> None:
    output_root, _ = isolated
    output = output_root / "logical_composite_v1"
    builder.build(output, "2026-09-16T18:30:00+00:00")
    thaw(output)
    path = output / "COMPOSITE_SOURCE_RUN_MANIFEST.json"
    manifest = builder.read_json(path)
    manifest["created_at"] = builder.NEXT_OPEN
    manifest["frozen_at"] = builder.NEXT_OPEN
    write_json(path, manifest)
    with pytest.raises(validator.ValidationError) as caught:
        validator.validate(output)
    assert caught.value.code == "B19V4IV_E_FREEZE_TIME"


def test_child_after_cutoff_and_cross_asof_are_rejected(isolated) -> None:
    _, children = isolated
    late = [dict(item) for item in children]
    late[-1]["available_at"] = "2026-09-16T18:31:00+00:00"
    with pytest.raises(builder.InventoryError) as cutoff:
        builder.validate_children(late, "2026-09-16T18:30:00+00:00")
    assert cutoff.value.code == "B19V4I_E_CHILD_AFTER_CUTOFF"

    crossed = [dict(item) for item in children]
    crossed[0]["asof"] = "2026-09-15"
    with pytest.raises(builder.InventoryError) as asof:
        builder.validate_children(crossed, "2026-09-16T18:30:00+00:00")
    assert asof.value.code == "B19V4I_E_CHILD_ASOF"


def test_duplicate_or_unknown_role_is_rejected(isolated) -> None:
    _, children = isolated
    changed = [dict(item) for item in children]
    changed[-1]["role"] = "daily_price"
    with pytest.raises(builder.InventoryError) as caught:
        builder.validate_children(changed, "2026-09-16T18:30:00+00:00")
    assert caught.value.code == "B19V4I_E_CHILD_ROLES"


def test_model_a_mixed_secondary_physical_run_is_rejected(isolated) -> None:
    _, children = isolated
    changed = copy.deepcopy(children)
    model_a = changed[3]
    model_a["secondary_identity_attestation"]["upstream_physical_run_id"] = "mixed.hidden.run"
    with pytest.raises(builder.InventoryError) as caught:
        builder.validate_children(changed, "2026-09-16T18:30:00+00:00")
    assert caught.value.code == "B19V4I_E_MODELA_LINEAGE"


def test_model_a_backdated_child_availability_is_rejected(isolated) -> None:
    _, children = isolated
    changed = copy.deepcopy(children)
    changed[3]["available_at"] = "2026-09-16T14:57:25+00:00"
    with pytest.raises(builder.InventoryError) as caught:
        builder.validate_children(changed, "2026-09-16T18:30:00+00:00")
    assert caught.value.code == "B19V4I_E_MODELA_LINEAGE"


def test_cutoff_at_next_open_is_rejected(isolated) -> None:
    _, children = isolated
    with pytest.raises(builder.InventoryError) as caught:
        builder.validate_children(children, builder.NEXT_OPEN)
    assert caught.value.code == "B19V4I_E_CUTOFF_AFTER_NEXT_OPEN"


def test_declared_artifact_hash_tamper_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "artifact.json"
    path.write_text("stable\n", encoding="ascii")
    with pytest.raises(builder.InventoryError) as caught:
        builder.declared_artifact({"path": str(path), "sha256": "0" * 64, "bytes": path.stat().st_size})
    assert caught.value.code == "B19V4I_E_ARTIFACT_HASH"


def test_real_yahoo_child_binds_exact_review_and_implementations() -> None:
    child = builder.yahoo_child()
    assert child["role"] == "twii_yahoo"
    assert child["independent_review"]["sha256"] == builder.TWII_INDEPENDENT_REVIEW_SHA


@pytest.mark.parametrize(
    ("target", "mutate"),
    [
        ("validation", lambda value: value.update({"status": "FAIL"})),
        ("review", lambda value: value["authorization"].update({"capture_authorized": True})),
    ],
)
def test_yahoo_validation_or_review_tamper_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
    mutate,
) -> None:
    validation = tmp_path / "validation.json"
    review = tmp_path / "review.json"
    validation.write_bytes(builder.TWII_VALIDATION.read_bytes())
    review.write_bytes(builder.TWII_INDEPENDENT_REVIEW.read_bytes())
    selected = validation if target == "validation" else review
    value = json.loads(selected.read_text(encoding="utf-8"))
    mutate(value)
    write_json(selected, value)
    monkeypatch.setattr(builder, "TWII_VALIDATION", validation)
    monkeypatch.setattr(builder, "TWII_INDEPENDENT_REVIEW", review)
    monkeypatch.setattr(builder, "TWII_INDEPENDENT_REVIEW_SHA", file_sha(review))
    with pytest.raises(builder.InventoryError) as caught:
        builder.yahoo_child()
    expected = "B19V4I_E_YAHOO_VALIDATION_BINDING" if target == "validation" else "B19V4I_E_YAHOO_REVIEW_BINDING"
    assert caught.value.code == expected


def test_yahoo_child_artifact_hash_tamper_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = json.loads(builder.TWII_MANIFEST.read_text(encoding="utf-8"))
    manifest["artifacts"]["normalized_csv"]["sha256"] = "0" * 64
    manifest_path = tmp_path / "manifest.json"
    write_json(manifest_path, manifest)
    validation = json.loads(builder.TWII_VALIDATION.read_text(encoding="utf-8"))
    validation["source_manifest"] = str(manifest_path)
    validation["source_manifest_sha256"] = file_sha(manifest_path)
    validation_path = tmp_path / "validation.json"
    write_json(validation_path, validation)
    review = json.loads(builder.TWII_INDEPENDENT_REVIEW.read_text(encoding="utf-8"))
    review["reviewed_capture_manifest"] = {"path": str(manifest_path), "sha256": file_sha(manifest_path)}
    review["reviewed_validation"] = {"path": str(validation_path), "sha256": file_sha(validation_path)}
    review_path = tmp_path / "review.json"
    write_json(review_path, review)
    monkeypatch.setattr(builder, "TWII_MANIFEST", manifest_path)
    monkeypatch.setattr(builder, "TWII_VALIDATION", validation_path)
    monkeypatch.setattr(builder, "TWII_INDEPENDENT_REVIEW", review_path)
    monkeypatch.setattr(builder, "TWII_INDEPENDENT_REVIEW_SHA", file_sha(review_path))
    with pytest.raises(builder.InventoryError) as caught:
        builder.yahoo_child()
    assert caught.value.code == "B19V4I_E_ARTIFACT_HASH"


def test_output_escape_and_no_overwrite(isolated, tmp_path: Path) -> None:
    output_root, _ = isolated
    with pytest.raises(builder.InventoryError) as escaped:
        builder.build(tmp_path / "outside", "2026-09-16T18:30:00+00:00")
    assert escaped.value.code == "B19V4I_E_OUTPUT"
    output = output_root / "logical_composite_v1"
    builder.build(output, "2026-09-16T18:30:00+00:00")
    with pytest.raises(builder.InventoryError) as duplicate:
        builder.build(output, "2026-09-16T18:30:00+00:00")
    assert duplicate.value.code == "B19V4I_E_NO_OVERWRITE"
