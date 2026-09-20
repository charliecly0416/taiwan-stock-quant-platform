from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import validate_tw_modular_m_contracts as portfolio_validator
ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "scripts/validate_tw_modular_m_contracts.py"
GOLDEN = ROOT / "data_tw/golden_samples/modular_contracts/m1/portfolio_state"


def run_validator(artifact: Path) -> tuple[int, dict]:
    proc = subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--contract",
            "portfolio_state",
            "--artifact-path",
            str(artifact),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.stdout.strip(), proc.stderr
    return proc.returncode, json.loads(proc.stdout)


def error_codes(result: dict) -> set[str]:
    return {item["code"] for item in result["errors"]}


@pytest.mark.parametrize("raises", [False, True])
def test_compatibility_facade_restores_child_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, raises: bool
) -> None:
    child = portfolio_validator.portfolio_state_validator
    names = (
        "ROOT",
        "DEFAULT_GOLDEN_ROOT",
        "PORTFOLIO_SOURCE_ADMISSIONS",
        "SCHEMA_VERSION",
        "replay_artifact_validator",
    )
    child_config = (
        tmp_path / "child-root",
        tmp_path / "child-golden",
        tmp_path / "child-admissions.yaml",
        "child-schema",
        object(),
    )
    expected_active = (
        portfolio_validator.ROOT,
        portfolio_validator.DEFAULT_GOLDEN_ROOT,
        portfolio_validator.PORTFOLIO_SOURCE_ADMISSIONS,
        portfolio_validator.SCHEMA_VERSION,
        portfolio_validator.replay_artifact_validator,
    )
    for name, value in zip(names, child_config, strict=True):
        monkeypatch.setattr(child, name, value)

    observed: list[tuple[object, ...]] = []

    def fake_validate(*_args: object) -> None:
        observed.append(tuple(getattr(child, name) for name in names))
        if raises:
            raise RuntimeError("validator failure")

    monkeypatch.setattr(child, "validate_portfolio_state", fake_validate)
    if raises:
        with pytest.raises(RuntimeError, match="validator failure"):
            portfolio_validator.validate_portfolio_state({}, tmp_path, tmp_path, [], [])
    else:
        portfolio_validator.validate_portfolio_state({}, tmp_path, tmp_path, [], [])

    assert observed == [expected_active]
    assert tuple(getattr(child, name) for name in names) == child_config


@pytest.fixture
def nonempty_artifact(tmp_path: Path) -> Path:
    target = tmp_path / "portfolio_state"
    shutil.copytree(GOLDEN / "pass_owner_independent", target)
    return target


@pytest.fixture
def empty_artifact(tmp_path: Path) -> Path:
    target = tmp_path / "portfolio_state"
    shutil.copytree(GOLDEN / "pass_verified_empty", target)
    return target


def read_manifest(artifact: Path) -> dict:
    return json.loads((artifact / "manifest.json").read_text(encoding="utf-8"))


def write_manifest(artifact: Path, manifest: dict) -> None:
    (artifact / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


def file_identity(path: Path) -> tuple[str, int]:
    return hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def isolate_golden_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample: str
) -> Path:
    isolated_root = tmp_path / "repo"
    isolated_golden = (
        isolated_root / "data_tw/golden_samples/modular_contracts/m1/portfolio_state"
    )
    shutil.copytree(GOLDEN, isolated_golden)
    monkeypatch.setattr(portfolio_validator, "ROOT", isolated_root)
    monkeypatch.setattr(
        portfolio_validator,
        "DEFAULT_GOLDEN_ROOT",
        isolated_root / "data_tw/golden_samples/modular_contracts/m1",
    )
    monkeypatch.setattr(
        portfolio_validator.replay_artifact_validator, "ROOT", isolated_root
    )
    return isolated_golden / sample


def resolve_isolated(artifact: Path, raw_path: str) -> Path:
    relative = Path(raw_path)
    if len(relative.parts) > 1:
        return portfolio_validator.ROOT / relative
    return artifact / relative


def rebind_portfolio_checksums(artifact: Path) -> None:
    checksum_path = artifact / "checksum_manifest.json"
    checksum = json.loads(checksum_path.read_text(encoding="utf-8"))
    for item in checksum["files"]:
        digest, size = file_identity(resolve_isolated(artifact, item["path"]))
        item["sha256"] = digest
        item["bytes"] = size
    write_json(checksum_path, checksum)


def rebind_source_and_portfolio_checksums(artifact: Path) -> None:
    manifest = read_manifest(artifact)
    source_binding = manifest["source_artifacts"][0]
    source_manifest_path = resolve_isolated(artifact, source_binding["manifest_path"])

    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    source_checksum_path = portfolio_validator.ROOT / source_manifest["checksum_manifest"]["path"]
    source_checksum = json.loads(source_checksum_path.read_text(encoding="utf-8"))
    source_checksum["run_id"] = source_manifest["run_id"]
    for item in source_checksum["files"]:
        digest, size = file_identity(portfolio_validator.ROOT / item["path"])
        item["sha256"] = digest
        item["bytes"] = size
    write_json(source_checksum_path, source_checksum)

    source_checksum_digest, source_checksum_size = file_identity(source_checksum_path)
    source_manifest["checksum_manifest"] = {
        "path": source_manifest["checksum_manifest"]["path"],
        "sha256": source_checksum_digest,
        "bytes": source_checksum_size,
    }
    write_json(source_manifest_path, source_manifest)

    source_digest, source_size = file_identity(source_manifest_path)
    source_binding = {
        "admission_id": source_binding["admission_id"],
        "artifact_type": "replay_result",
        "run_id": source_manifest["run_id"],
        "manifest_path": source_binding["manifest_path"],
        "sha256": source_digest,
        "bytes": source_size,
    }
    manifest["source_artifacts"] = [source_binding]
    write_manifest(artifact, manifest)

    lineage_path = artifact / "source_lineage.json"
    lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
    lineage["source_artifacts"] = [source_binding]
    write_json(lineage_path, lineage)
    rebind_portfolio_checksums(artifact)


def test_canonical_nonempty_and_verified_empty_samples_pass() -> None:
    for sample in ("pass_owner_independent", "pass_verified_empty"):
        code, result = run_validator(GOLDEN / sample)
        assert code == 0
        assert result["ok"] is True


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("missing_source", "portfolio_source_lineage_invalid"),
        ("wrong_cutoff_date", "portfolio_cutoff_asof_mismatch"),
        ("per_user_state", "portfolio_state_kind_invalid"),
        ("nonopaque_portfolio_id", "portfolio_identity_invalid"),
        ("pii_field", "portfolio_forbidden_field"),
        ("paper_account_field", "portfolio_manifest_fields_invalid"),
        ("cash_field", "portfolio_forbidden_field"),
        ("source_path_traversal", "portfolio_path_invalid"),
        ("action_audit_path_traversal", "portfolio_path_invalid"),
        ("wrong_timezone", "portfolio_timestamp_invalid"),
    ],
)
def test_manifest_boundary_mutations_fail_closed(
    nonempty_artifact: Path, mutation: str, expected_code: str
) -> None:
    manifest = read_manifest(nonempty_artifact)
    if mutation == "missing_source":
        manifest["source_artifacts"] = []
    elif mutation == "wrong_cutoff_date":
        manifest["decision_cutoff"] = "2026-09-19T10:30:00+08:00"
    elif mutation == "per_user_state":
        manifest["state_kind"] = "per_user_paper"
    elif mutation == "nonopaque_portfolio_id":
        manifest["portfolio_id"] = "user-account-42"
    elif mutation == "pii_field":
        manifest["user_id"] = "42"
    elif mutation == "paper_account_field":
        manifest["paper_account_id"] = "paper-42"
    elif mutation == "cash_field":
        manifest["cash"] = 1_000_000
    elif mutation == "source_path_traversal":
        manifest["source_artifacts"][0]["manifest_path"] = "../manifest.json"
    elif mutation == "action_audit_path_traversal":
        manifest["forbidden_action_audit"] = "/etc/passwd"
    elif mutation == "wrong_timezone":
        manifest["available_at"] = "2026-09-18T02:00:00+00:00"
    write_manifest(nonempty_artifact, manifest)

    code, result = run_validator(nonempty_artifact)

    assert code != 0
    assert result["ok"] is False
    assert expected_code in error_codes(result)


@pytest.mark.parametrize(
    ("row", "expected_code"),
    [
        ("2026-09-18,TW2330,0,975.5,true\n", "portfolio_numeric_value_invalid"),
        ("2026-09-18,TW2330,100,0,true\n", "portfolio_numeric_value_invalid"),
        ("2026-09-18,TW2330,100,975.5,false\n", "portfolio_row_state_inconsistent"),
        ("2026-09-18,TW2330,100,975.5,true,extra\n", "portfolio_columns_invalid"),
    ],
)
def test_invalid_position_rows_fail_closed(
    nonempty_artifact: Path, row: str, expected_code: str
) -> None:
    (nonempty_artifact / "portfolio_state.csv").write_text(
        "asof_date,instrument,quantity,cost_basis,current_holding_flag\n" + row,
        encoding="utf-8",
    )
    manifest = read_manifest(nonempty_artifact)
    manifest["row_count"] = 1
    write_manifest(nonempty_artifact, manifest)

    code, result = run_validator(nonempty_artifact)

    assert code != 0
    assert expected_code in error_codes(result)


@pytest.mark.parametrize(
    ("row", "expected_code"),
    [
        (
            "TW2330,buy,2026-09-17,oi_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n",
            "portfolio_pending_position_mismatch",
        ),
        (
            "TW2454,sell,2026-09-17,oi_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n",
            "portfolio_pending_position_mismatch",
        ),
        (
            "TW2454,buy,2026-09-18,oi_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n",
            "portfolio_pending_signal_date_invalid",
        ),
        (
            "TW2454,buy,2026-09-17,intent-readable-id\n",
            "portfolio_pending_intent_id_invalid",
        ),
    ],
)
def test_pending_projection_must_match_decision_boundary(
    nonempty_artifact: Path, row: str, expected_code: str
) -> None:
    (nonempty_artifact / "pending_intents.csv").write_text(
        "instrument,action,source_signal_date,source_intent_id\n" + row,
        encoding="utf-8",
    )
    manifest = read_manifest(nonempty_artifact)
    manifest["pending_state"]["row_count"] = 1
    write_manifest(nonempty_artifact, manifest)

    code, result = run_validator(nonempty_artifact)

    assert code != 0
    assert expected_code in error_codes(result)


def test_empty_state_rejects_nonempty_replay_snapshot_after_full_rebind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = isolate_golden_fixture(tmp_path, monkeypatch, "pass_verified_empty")
    (artifact / "source_position_snapshots.csv").write_text(
        "date,instrument,quantity,cost_basis,mark_price,market_value,unrealized_pnl,strategy_rule,model_name\n"
        "2026-09-18,TW9999,1,1.0,1.0,1.0,0.0,top50_exit_one_worst_sell,model_a\n",
        encoding="utf-8",
    )
    rebind_source_and_portfolio_checksums(artifact)

    result = portfolio_validator.validate_contract("portfolio_state", artifact)

    assert result["ok"] is False
    assert {
        "portfolio_source_not_admitted",
        "portfolio_source_snapshot_mismatch",
    }.issubset(error_codes(result))


def test_forged_portfolio_positions_fail_after_portfolio_checksum_rebind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = isolate_golden_fixture(tmp_path, monkeypatch, "pass_owner_independent")
    (artifact / "portfolio_state.csv").write_text(
        "asof_date,instrument,quantity,cost_basis,current_holding_flag\n"
        "2026-09-18,TW9999,999999,1.0,true\n",
        encoding="utf-8",
    )
    manifest = read_manifest(artifact)
    manifest["row_count"] = 1
    write_manifest(artifact, manifest)
    rebind_portfolio_checksums(artifact)

    result = portfolio_validator.validate_contract("portfolio_state", artifact)

    assert result["ok"] is False
    assert error_codes(result) == {"portfolio_source_snapshot_mismatch"}


def test_replay_snapshot_tamper_without_replay_checksum_rebind_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = isolate_golden_fixture(tmp_path, monkeypatch, "pass_owner_independent")
    (artifact / "source_position_snapshots.csv").write_text(
        "date,instrument,quantity,cost_basis,mark_price,market_value,unrealized_pnl,strategy_rule,model_name\n"
        "2026-09-18,TW9999,1,1.0,1.0,1.0,0.0,top50_exit_one_worst_sell,model_a\n",
        encoding="utf-8",
    )

    result = portfolio_validator.validate_contract("portfolio_state", artifact)

    assert result["ok"] is False
    assert {
        "portfolio_source_checksum_mismatch",
        "portfolio_source_snapshot_mismatch",
    }.issubset(error_codes(result))


def test_formal_replay_validator_failure_survives_full_checksum_rebind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = isolate_golden_fixture(tmp_path, monkeypatch, "pass_owner_independent")
    (artifact / "source_integrity_audit.csv").write_text(
        "audit_name,date,instrument,status,value,threshold,details\n"
        "duplicate_position_day_symbol,2026-09-18,TW2330,fail,1,0,duplicate\n",
        encoding="utf-8",
    )
    rebind_source_and_portfolio_checksums(artifact)

    result = portfolio_validator.validate_contract("portfolio_state", artifact)

    assert result["ok"] is False
    assert {
        "portfolio_source_not_admitted",
        "portfolio_source_validator_failed",
    }.issubset(error_codes(result))


def test_formal_replay_parser_failure_is_structured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = isolate_golden_fixture(tmp_path, monkeypatch, "pass_owner_independent")
    (artifact / "source_actions.csv").write_text("", encoding="utf-8")
    rebind_source_and_portfolio_checksums(artifact)

    result = portfolio_validator.validate_contract("portfolio_state", artifact)

    assert result["ok"] is False
    assert {
        "portfolio_source_not_admitted",
        "portfolio_source_validator_failed",
    }.issubset(error_codes(result))


def test_fully_resigned_source_and_portfolio_cannot_bypass_admission_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = isolate_golden_fixture(tmp_path, monkeypatch, "pass_owner_independent")
    (artifact / "source_position_snapshots.csv").write_text(
        "date,instrument,quantity,cost_basis,mark_price,market_value,unrealized_pnl,strategy_rule,model_name\n"
        "2026-09-18,TW9999,100,1.0,2.0,200.0,100.0,top50_exit_one_worst_sell,model_a\n",
        encoding="utf-8",
    )
    (artifact / "source_daily_nav.csv").write_text(
        "date,cash,market_value,equity,daily_return,holding_count,missing_price_count\n"
        "2026-09-18,1000000.0,200.0,1000200.0,0.0,1,0\n",
        encoding="utf-8",
    )
    (artifact / "source_summary.csv").write_text(
        "window,model_name,model_family,strategy_rule,start_date,end_date,initial_cash,fee_and_tax,final_equity,total_return,max_drawdown,action_count,buy_count,sell_count,skipped_action_count,max_holding_count,duplicate_position_count,negative_cash_count,missing_price_count,diagnostic_only\n"
        "wf5b,model_a,qlib,top50_exit_one_worst_sell,2026-09-18,2026-09-18,1000200.0,0.0,1000200.0,0.0,0.0,0,0,0,0,1,0,0,0,false\n",
        encoding="utf-8",
    )
    (artifact / "portfolio_state.csv").write_text(
        "asof_date,instrument,quantity,cost_basis,current_holding_flag\n"
        "2026-09-18,TW9999,100,1.0,true\n",
        encoding="utf-8",
    )
    manifest = read_manifest(artifact)
    manifest["row_count"] = 1
    write_manifest(artifact, manifest)
    rebind_source_and_portfolio_checksums(artifact)

    result = portfolio_validator.validate_contract("portfolio_state", artifact)

    assert result["ok"] is False
    assert error_codes(result) == {"portfolio_source_not_admitted"}


def test_fully_resigned_new_empty_run_id_is_not_admitted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = isolate_golden_fixture(tmp_path, monkeypatch, "pass_verified_empty")
    source_manifest_path = artifact / "source_manifest.json"
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    source_manifest["run_id"] = "source_empty_forged_002"
    write_json(source_manifest_path, source_manifest)
    rebind_source_and_portfolio_checksums(artifact)

    result = portfolio_validator.validate_contract("portfolio_state", artifact)

    assert result["ok"] is False
    assert error_codes(result) == {"portfolio_source_not_admitted"}


@pytest.mark.parametrize(
    "mutation",
    [
        "empty_summary",
        "daily_extra_cell",
        "arbitrary_schema",
        "arbitrary_contract",
        "legacy_four_column_snapshot",
    ],
)
def test_resigned_malformed_replay_sources_fail_strict_profile_and_admission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    artifact = isolate_golden_fixture(tmp_path, monkeypatch, "pass_owner_independent")
    source_manifest_path = artifact / "source_manifest.json"
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    if mutation == "empty_summary":
        header = (artifact / "source_summary.csv").read_text(encoding="utf-8").splitlines()[0]
        (artifact / "source_summary.csv").write_text(header + "\n", encoding="utf-8")
    elif mutation == "daily_extra_cell":
        path = artifact / "source_daily_nav.csv"
        lines = path.read_text(encoding="utf-8").splitlines()
        path.write_text(lines[0] + "\n" + lines[1] + ",extra\n", encoding="utf-8")
    elif mutation == "arbitrary_schema":
        source_manifest["schema_version"] = "future_schema"
        write_json(source_manifest_path, source_manifest)
    elif mutation == "arbitrary_contract":
        source_manifest["contract_version"] = "unreviewed_contract"
        write_json(source_manifest_path, source_manifest)
    elif mutation == "legacy_four_column_snapshot":
        (artifact / "source_position_snapshots.csv").write_text(
            "date,instrument,quantity,cost_basis\n2026-09-18,TW2330,100,975.5\n",
            encoding="utf-8",
        )
    rebind_source_and_portfolio_checksums(artifact)

    result = portfolio_validator.validate_contract("portfolio_state", artifact)

    assert result["ok"] is False
    assert {
        "portfolio_source_not_admitted",
        "portfolio_source_validator_failed",
    }.issubset(error_codes(result))


def test_unknown_admission_id_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = isolate_golden_fixture(tmp_path, monkeypatch, "pass_owner_independent")
    manifest = read_manifest(artifact)
    manifest["source_artifacts"][0]["admission_id"] = "unknown_replay"
    write_manifest(artifact, manifest)
    lineage_path = artifact / "source_lineage.json"
    lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
    lineage["source_artifacts"] = manifest["source_artifacts"]
    write_json(lineage_path, lineage)
    rebind_portfolio_checksums(artifact)

    result = portfolio_validator.validate_contract("portfolio_state", artifact)

    assert "portfolio_source_not_admitted" in error_codes(result)


def test_source_path_swap_between_admissions_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = isolate_golden_fixture(tmp_path, monkeypatch, "pass_owner_independent")
    swapped = artifact.parent / "pass_verified_empty/source_manifest.json"
    digest, size = file_identity(swapped)
    swapped_payload = json.loads(swapped.read_text(encoding="utf-8"))
    manifest = read_manifest(artifact)
    binding = manifest["source_artifacts"][0]
    binding.update(
        {
            "run_id": swapped_payload["run_id"],
            "manifest_path": portfolio_validator.rel(swapped),
            "sha256": digest,
            "bytes": size,
        }
    )
    write_manifest(artifact, manifest)
    lineage_path = artifact / "source_lineage.json"
    lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
    lineage["source_artifacts"] = manifest["source_artifacts"]
    write_json(lineage_path, lineage)
    rebind_portfolio_checksums(artifact)

    result = portfolio_validator.validate_contract("portfolio_state", artifact)

    assert "portfolio_source_not_admitted" in error_codes(result)


def test_duplicate_admission_registry_key_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = isolate_golden_fixture(tmp_path, monkeypatch, "pass_owner_independent")
    duplicate_registry = tmp_path / "duplicate_admissions.yaml"
    original = portfolio_validator.PORTFOLIO_SOURCE_ADMISSIONS.read_text(encoding="utf-8")
    duplicate_registry.write_text(
        original + "\nadmissions:\n  duplicate: {}\n", encoding="utf-8"
    )
    monkeypatch.setattr(
        portfolio_validator, "PORTFOLIO_SOURCE_ADMISSIONS", duplicate_registry
    )

    result = portfolio_validator.validate_contract("portfolio_state", artifact)

    assert "portfolio_source_admission_invalid" in error_codes(result)


def test_artifact_cannot_select_an_admission_registry(nonempty_artifact: Path) -> None:
    manifest = read_manifest(nonempty_artifact)
    manifest["source_admission_registry"] = "attacker-controlled.yaml"
    write_manifest(nonempty_artifact, manifest)

    code, result = run_validator(nonempty_artifact)

    assert code != 0
    assert "portfolio_manifest_fields_invalid" in error_codes(result)


def test_symlinked_replay_source_manifest_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = isolate_golden_fixture(tmp_path, monkeypatch, "pass_owner_independent")
    source_manifest = artifact / "source_manifest.json"
    real_manifest = artifact / "source_manifest_real.json"
    source_manifest.rename(real_manifest)
    source_manifest.symlink_to(real_manifest.name)

    result = portfolio_validator.validate_contract("portfolio_state", artifact)

    assert "portfolio_symlink_forbidden" in error_codes(result)


def test_same_instrument_cannot_have_multiple_pending_rows(nonempty_artifact: Path) -> None:
    (nonempty_artifact / "pending_intents.csv").write_text(
        "instrument,action,source_signal_date,source_intent_id\n"
        "TW2454,buy,2026-09-16,oi_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
        "TW2454,buy,2026-09-17,oi_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\n",
        encoding="utf-8",
    )
    manifest = read_manifest(nonempty_artifact)
    manifest["pending_state"]["row_count"] = 2
    write_manifest(nonempty_artifact, manifest)

    code, result = run_validator(nonempty_artifact)

    assert code != 0
    assert "portfolio_pending_duplicate_instrument" in error_codes(result)


def test_checksum_tamper_and_missing_field_audit_fail(nonempty_artifact: Path) -> None:
    (nonempty_artifact / "schema.json").write_text("{}\n", encoding="utf-8")
    (nonempty_artifact / "forbidden_field_audit.json").unlink()

    code, result = run_validator(nonempty_artifact)

    assert code != 0
    assert {
        "portfolio_checksum_mismatch",
        "portfolio_file_missing",
        "portfolio_schema_invalid",
    }.issubset(error_codes(result))


def test_checksum_and_action_audit_require_exact_schemas(nonempty_artifact: Path) -> None:
    checksum = json.loads((nonempty_artifact / "checksum_manifest.json").read_text(encoding="utf-8"))
    checksum["schema_version"] = "future"
    (nonempty_artifact / "checksum_manifest.json").write_text(
        json.dumps(checksum, indent=2) + "\n", encoding="utf-8"
    )
    action_audit = json.loads((nonempty_artifact / "forbidden_action_audit.json").read_text(encoding="utf-8"))
    action_audit["actions"]["unexpected_action"] = False
    (nonempty_artifact / "forbidden_action_audit.json").write_text(
        json.dumps(action_audit, indent=2) + "\n", encoding="utf-8"
    )

    code, result = run_validator(nonempty_artifact)

    assert code != 0
    assert {
        "portfolio_checksum_manifest_invalid",
        "portfolio_forbidden_action_audit_invalid",
    }.issubset(error_codes(result))


def test_malformed_json_returns_structured_failure(nonempty_artifact: Path) -> None:
    (nonempty_artifact / "manifest.json").write_text("{broken", encoding="utf-8")

    code, result = run_validator(nonempty_artifact)

    assert code != 0
    assert result["ok"] is False
    assert error_codes(result) == {"portfolio_parse_error"}


def test_malformed_csv_returns_structured_failure(nonempty_artifact: Path) -> None:
    (nonempty_artifact / "portfolio_state.csv").write_text(
        'asof_date,instrument,quantity,cost_basis,current_holding_flag\n"unterminated',
        encoding="utf-8",
    )

    code, result = run_validator(nonempty_artifact)

    assert code != 0
    assert result["ok"] is False
    assert error_codes(result) == {"portfolio_parse_error"}


def test_fixture_local_source_is_rejected_outside_golden_root(nonempty_artifact: Path) -> None:
    code, result = run_validator(nonempty_artifact)

    assert code != 0
    assert "portfolio_source_path_forbidden" in error_codes(result)


@pytest.mark.parametrize(("target", "field"), [("source", "paper_account_id"), ("lineage", "broker_id")])
def test_source_and_lineage_unknown_identity_fields_fail(
    nonempty_artifact: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
    field: str,
) -> None:
    monkeypatch.setattr(portfolio_validator, "DEFAULT_GOLDEN_ROOT", tmp_path)
    path = nonempty_artifact / ("source_manifest.json" if target == "source" else "source_lineage.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload[field] = "private-identity"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    result = portfolio_validator.validate_contract("portfolio_state", nonempty_artifact)

    assert result["ok"] is False
    assert "portfolio_source_lineage_invalid" in error_codes(result)
