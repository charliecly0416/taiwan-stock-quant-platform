from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_runtime_physical_slimming_manifest as builder  # noqa: E402
import validate_runtime_physical_slimming_manifest as validator  # noqa: E402


@pytest.fixture(scope="module")
def golden_runtime(tmp_path_factory: pytest.TempPathFactory) -> dict:
    root = tmp_path_factory.mktemp("runtime_manifest_repo")
    targets = set(
        builder.ACTIVE_ROOTS
        + builder.CONFIG_ROOTS
        + builder.PROTECTED_PATHS
        + builder.DAPR_TARGETS
        + builder.CONTROL_PATHS
    )
    for target in targets:
        path = root / target
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".json":
            content = "{}\n"
        elif path.suffix in {".yaml", ".yml"}:
            content = "{}\n"
        else:
            content = "# fixture\n"
        path.write_text(content, encoding="utf-8")

    archive_target = "data_tw/experiments/archive/historical_research/fixture.csv"
    archive = root / archive_target
    archive.parent.mkdir(parents=True, exist_ok=True)
    archive.write_text("value\n1\n", encoding="utf-8")
    (root / "backend/run.py").write_text("import flask\n", encoding="utf-8")
    (root / "scripts/run_daily_tw_stock_auto_update.py").write_text(
        f'ARCHIVE_INPUT = "{archive_target}"\n', encoding="utf-8"
    )

    installed = root / "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron"
    installed.write_text(
        "0 1 * * * python scripts/run_daily_tw_stock_auto_update.py --one\n"
        "0 2 * * * python scripts/run_daily_tw_stock_auto_update.py --two\n",
        encoding="utf-8",
    )
    actual = root / "actual.cron"
    actual.write_bytes(installed.read_bytes())
    git_entries = [{"path": "untracked.txt", "state": "??"}]
    with patch.object(builder, "git_states", return_value=(True, {}, git_entries)):
        manifest = builder.build_manifest(
            root,
            installed,
            actual,
            "2026-09-10T00:00:00+00:00",
        )
    return {"root": root, "installed": installed, "actual": actual, "manifest": manifest}


def validate(payload: dict, runtime: dict) -> dict:
    return validator.validate(
        payload,
        runtime["root"],
        installed_cron=runtime["installed"],
        actual_cron=runtime["actual"],
        check_git_state=False,
    )


def test_golden_runtime_manifest_and_schema_pass(golden_runtime: dict) -> None:
    current_manifest = golden_runtime["manifest"]
    result = validate(current_manifest, golden_runtime)
    assert result == {
        "ok": True,
        "status": "PASS",
        "schema_validation": "PASS",
        "errors": [],
        "record_count": len(current_manifest["records"]),
    }


def test_dapr_targets_are_exactly_ordered_and_unique(golden_runtime: dict) -> None:
    current_manifest = golden_runtime["manifest"]
    assert current_manifest["dapr_targets"] == builder.DAPR_TARGETS
    records = [item for item in current_manifest["records"] if item["reference_type"] == "dapr_subprocess"]
    assert len(records) == 9
    ordered = sorted(records, key=lambda item: item["evidence"]["dapr_order"])
    assert [item["target_path"] for item in ordered] == builder.DAPR_TARGETS

    reordered = copy.deepcopy(current_manifest)
    reordered["dapr_targets"][0], reordered["dapr_targets"][1] = (
        reordered["dapr_targets"][1], reordered["dapr_targets"][0]
    )
    assert validate(reordered, golden_runtime)["status"] == "FAIL"

    duplicate = copy.deepcopy(current_manifest)
    duplicate["records"].append(copy.deepcopy(records[0]))
    result = validate(duplicate, golden_runtime)
    assert result["status"] == "FAIL"
    assert "duplicate_record_key" in result["errors"]


def test_missing_active_target_fails(golden_runtime: dict) -> None:
    current_manifest = golden_runtime["manifest"]
    payload = copy.deepcopy(current_manifest)
    target = builder.ACTIVE_ROOTS[0]
    payload["records"] = [item for item in payload["records"] if item["target_path"] != target]
    result = validate(payload, golden_runtime)
    assert result["status"] == "FAIL"
    assert f"required_active_keep_missing:{target}" in result["errors"]


def test_archive_dependencies_are_quarantined_and_cannot_move(golden_runtime: dict) -> None:
    current_manifest = golden_runtime["manifest"]
    archive_records = [
        item for item in current_manifest["records"]
        if "archive" in Path(item["target_path"]).parts
    ]
    assert archive_records
    assert all(item["classification"] == "unknown_do_not_move" for item in archive_records)
    assert all(item["move_eligible"] is False for item in archive_records)
    assert any("data_tw/experiments/archive/historical_research" in item["target_path"] for item in archive_records)

    payload = copy.deepcopy(current_manifest)
    target = archive_records[0]["target_path"]
    changed = next(item for item in payload["records"] if item["target_path"] == target)
    changed["classification"] = "active_keep"
    changed["move_eligible"] = True
    result = validate(payload, golden_runtime)
    assert result["status"] == "FAIL"
    assert f"archive_reference_not_quarantined:{target}" in result["errors"]


def test_unresolved_imports_are_dynamic_exceptions_not_fake_targets(golden_runtime: dict) -> None:
    current_manifest = golden_runtime["manifest"]
    dynamic = [item for item in current_manifest["records"] if item["reference_type"] == "dynamic_exception"]
    assert dynamic
    assert any(
        "flask" in item["dynamic_exception"]["references"].get("python_imports", [])
        for item in dynamic
    )
    assert all(item["target_path"] == "" for item in dynamic)
    assert all(item["classification"] == "unknown_do_not_move" for item in dynamic)
    assert not any(
        item["reference_type"] != "dynamic_exception" and not item["exists"]
        for item in current_manifest["records"]
    )


def test_generated_manifest_excludes_build_and_cache_trees(golden_runtime: dict) -> None:
    current_manifest = golden_runtime["manifest"]
    ignored = builder.IGNORED_PARTS
    assert not any(
        set(Path(item["source_path"]).parts).intersection(ignored)
        or set(Path(item["target_path"]).parts).intersection(ignored)
        for item in current_manifest["records"]
    )


def test_path_escape_and_cron_drift_fail(golden_runtime: dict) -> None:
    current_manifest = golden_runtime["manifest"]
    escaped = copy.deepcopy(current_manifest)
    record = next(item for item in escaped["records"] if item["reference_type"] == "manifest_control")
    record["target_path"] = "../outside.py"
    result = validate(escaped, golden_runtime)
    assert result["status"] == "FAIL"
    assert "invalid_or_escaping_target:../outside.py" in result["errors"]

    outside = golden_runtime["root"].parent / "outside.py"
    outside.write_text("# outside\n", encoding="utf-8")
    symlink = golden_runtime["root"] / "scripts/escape.py"
    symlink.symlink_to(outside)
    symlink_escape = copy.deepcopy(current_manifest)
    record = next(item for item in symlink_escape["records"] if item["reference_type"] == "manifest_control")
    record.update(
        target_path="scripts/escape.py",
        resolved_path=str(outside),
        exists=True,
        sha256=builder.sha256(outside),
    )
    result = validate(symlink_escape, golden_runtime)
    assert result["status"] == "FAIL"
    assert "invalid_or_escaping_target:scripts/escape.py" in result["errors"]

    cron_drift = copy.deepcopy(current_manifest)
    cron_drift["cron_parity"]["actual_sha256"] = "0" * 64
    result = validate(cron_drift, golden_runtime)
    assert result["status"] == "FAIL"
    assert "actual_cron_current_hash_mismatch" in result["errors"]


def test_schema_is_executed_and_worktree_state_is_recorded(golden_runtime: dict) -> None:
    current_manifest = golden_runtime["manifest"]
    assert current_manifest["worktree_dirty"] is True
    assert current_manifest["git_status_entries"]
    assert any(item["state"] == "??" for item in current_manifest["git_status_entries"])

    payload = copy.deepcopy(current_manifest)
    payload["unexpected"] = True
    result = validate(payload, golden_runtime)
    assert result["schema_validation"] == "FAIL"
    assert any(item.startswith("schema_validation:") for item in result["errors"])


def test_manifest_control_hashes_match_current_files(golden_runtime: dict) -> None:
    current_manifest = golden_runtime["manifest"]
    controls = {
        item["target_path"]: item
        for item in current_manifest["records"]
        if item["reference_type"] == "manifest_control"
    }
    assert set(controls) == set(builder.CONTROL_PATHS)
    for target, item in controls.items():
        assert item["sha256"] == builder.sha256(golden_runtime["root"] / target)


def test_two_seed_closure_scans_are_stable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    (root / "data").mkdir()
    (root / "scripts/root.py").write_text("import requests\nfrom . import helper\n", encoding="utf-8")
    (root / "scripts/helper.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "data/latest.json").write_text("{}\n", encoding="utf-8")
    cron = root / "installed.cron"
    cron.write_text(
        "0 1 * * * python scripts/run_daily_tw_stock_auto_update.py --one\n"
        "0 2 * * * python scripts/run_daily_tw_stock_auto_update.py --two\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(builder, "ACTIVE_ROOTS", ["scripts/root.py"])
    monkeypatch.setattr(builder, "CONFIG_ROOTS", [])
    monkeypatch.setattr(builder, "PROTECTED_PATHS", ["data/latest.json"])
    monkeypatch.setattr(builder, "DAPR_TARGETS", [])
    monkeypatch.setattr(builder, "CONTROL_PATHS", [])
    monkeypatch.setattr(builder, "TEST_ROOTS", ())
    monkeypatch.setattr(builder, "git_states", lambda _root: (True, {"scripts/root.py": "??"}, [{"path": "scripts/root.py", "state": "??"}]))

    first = builder.build_manifest(root, cron, cron, "2026-09-10T00:00:00+00:00")
    second = builder.build_manifest(root, cron, cron, "2026-09-11T00:00:00+00:00")
    first.pop("observed_at")
    second.pop("observed_at")
    assert json.dumps(first, sort_keys=True, separators=(",", ":")) == json.dumps(second, sort_keys=True, separators=(",", ":"))
    dynamic = next(item for item in first["records"] if item["reference_type"] == "dynamic_exception")
    assert "requests" in dynamic["dynamic_exception"]["references"]["python_imports"]
    assert not any(item["target_path"] == "requests" for item in first["records"])


def test_independent_closure_rejects_omitted_production_archive_and_literal(golden_runtime: dict) -> None:
    current = golden_runtime["manifest"]
    archive = next(item for item in current["records"] if "archive" in Path(item["target_path"]).parts)
    payload = copy.deepcopy(current)
    payload["records"].remove(archive)
    result = validate(payload, golden_runtime)
    assert result["status"] == "FAIL"
    assert "production_closure_records_mismatch" in result["errors"]


def test_independent_closure_rejects_omitted_dynamic_exception_and_reference_value(golden_runtime: dict) -> None:
    current = golden_runtime["manifest"]
    dynamic = next(item for item in current["records"] if item["reference_type"] == "dynamic_exception")

    omitted = copy.deepcopy(current)
    omitted["records"].remove(dynamic)
    result = validate(omitted, golden_runtime)
    assert result["status"] == "FAIL"
    assert "production_closure_records_mismatch" in result["errors"]

    damaged = copy.deepcopy(current)
    detail = next(item for item in damaged["records"] if item["reference_type"] == "dynamic_exception")
    category = next(iter(detail["dynamic_exception"]["references"]))
    detail["dynamic_exception"]["references"][category].pop()
    if not detail["dynamic_exception"]["references"][category]:
        del detail["dynamic_exception"]["references"][category]
    result = validate(damaged, golden_runtime)
    assert result["status"] == "FAIL"
    assert "production_closure_records_mismatch" in result["errors"] or any(
        item.startswith("dynamic_exception_") for item in result["errors"]
    )


def test_dynamic_exception_source_path_traversal_and_symlink_fail(golden_runtime: dict) -> None:
    current = golden_runtime["manifest"]
    dynamic = next(item for item in current["records"] if item["reference_type"] == "dynamic_exception")

    traversal = copy.deepcopy(current)
    next(item for item in traversal["records"] if item["reference_type"] == "dynamic_exception")["source_path"] = "../outside.py"
    result = validate(traversal, golden_runtime)
    assert result["status"] == "FAIL"
    assert "dynamic_exception_source_invalid:../outside.py" in result["errors"]

    outside = golden_runtime["root"].parent / "dynamic-outside.py"
    outside.write_text("# outside\n", encoding="utf-8")
    escape = golden_runtime["root"] / "scripts/dynamic-escape.py"
    escape.symlink_to(outside)
    symlink = copy.deepcopy(current)
    next(item for item in symlink["records"] if item["reference_type"] == "dynamic_exception")["source_path"] = "scripts/dynamic-escape.py"
    result = validate(symlink, golden_runtime)
    assert result["status"] == "FAIL"
    assert "dynamic_exception_source_invalid:scripts/dynamic-escape.py" in result["errors"]


def test_test_only_local_dependency_is_recorded_without_production_expansion(
    golden_runtime: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = golden_runtime["root"]
    helper = root / "tests/local_helper.py"
    test_file = root / "tests/test_local_dependency.py"
    literal_target = root / "data_tw/test_only_fixture.json"
    helper.parent.mkdir(parents=True, exist_ok=True)
    literal_target.parent.mkdir(parents=True, exist_ok=True)
    helper.write_text("VALUE = 1\n", encoding="utf-8")
    literal_target.write_text("{}\n", encoding="utf-8")
    test_file.write_text(
        'import local_helper\nFIXTURE = "data_tw/test_only_fixture.json"\n',
        encoding="utf-8",
    )
    snapshot = (
        bool(golden_runtime["manifest"].get("worktree_dirty")),
        {},
        golden_runtime["manifest"].get("git_status_entries", []),
    )
    with patch.object(builder, "git_states", return_value=snapshot):
        rebuilt = builder.build_manifest(
            root,
            golden_runtime["installed"],
            golden_runtime["actual"],
            "2026-09-10T00:00:00+00:00",
            git_snapshot=snapshot,
        )
    matches = [
        item for item in rebuilt["records"]
        if item["target_path"] == "tests/local_helper.py"
    ]
    assert matches
    assert all(item["runtime_scope"] == "test_harness" for item in matches)
    assert all(item["classification"] == "unknown_do_not_move" for item in matches)
    assert not any(
        item["target_path"] == "tests/local_helper.py" and item["runtime_scope"] == "production_runtime"
        for item in rebuilt["records"]
    )
    literal_matches = [
        item for item in rebuilt["records"]
        if item["target_path"] == "data_tw/test_only_fixture.json"
    ]
    assert literal_matches
    assert all(item["runtime_scope"] == "test_harness" for item in literal_matches)
    assert all(item["classification"] == "unknown_do_not_move" for item in literal_matches)
    assert not any(
        item["target_path"] == "data_tw/test_only_fixture.json" and item["runtime_scope"] == "production_runtime"
        for item in rebuilt["records"]
    )
