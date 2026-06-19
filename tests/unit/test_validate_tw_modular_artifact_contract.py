from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "scripts/validate_tw_modular_artifact_contract.py"
ARTIFACT = ROOT / "data_tw/artifacts/signals/fresh_qlib_adaptive/r1_legacy_signal_adapter_20260616/manifest.json"
REGISTRY = ROOT / "configs/tw_modular_registry.yaml"
FULL_RANK_ARTIFACT = ROOT / "data_tw/artifacts/full_rank/fresh_qlib_s2b_post_filter/r9_full_rank_adapter_20260616/manifest.json"


def run_validator(*args: str) -> dict:
    proc = subprocess.run([sys.executable, str(VALIDATOR), *args, "--json"], cwd=ROOT, text=True, capture_output=True, check=True)
    return json.loads(proc.stdout)


def run_validator_allow_fail(*args: str) -> dict:
    proc = subprocess.run([sys.executable, str(VALIDATOR), *args, "--json"], cwd=ROOT, text=True, capture_output=True, check=False)
    return json.loads(proc.stdout)


def copy_artifact(tmp_path: Path) -> Path:
    src_dir = ARTIFACT.parent
    dst = tmp_path / "artifact"
    shutil.copytree(src_dir, dst)
    manifest = json.loads((dst / "manifest.json").read_text())
    manifest["output_files"]["signals"] = str(dst / "signals.csv")
    (dst / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return dst / "manifest.json"


def check_status(result: dict, name: str) -> str:
    checks = {row["name"]: row for row in result["checks"]}
    return checks[name]["status"]


def test_registry_dependency_paths_exist() -> None:
    result = run_validator("--artifact", str(ARTIFACT), "--registry", str(REGISTRY))
    assert result["ok"] is True


def test_core_artifact_validates_without_strategy_dependency() -> None:
    result = run_validator("--artifact", str(ARTIFACT))
    assert result["ok"] is True


def test_all_base_strategy_dependencies_validate_against_core_artifact() -> None:
    dependencies = [
        "configs/strategy_dependencies/original.yaml",
        "configs/strategy_dependencies/top50_exit_all.yaml",
        "configs/strategy_dependencies/top50_exit_one_worst_sell.yaml",
        "configs/strategy_dependencies/one_sell_one_buy_correct.yaml",
        "configs/strategy_dependencies/one_sell_one_buy_buggy_e8r.yaml",
    ]
    for dep in dependencies:
        result = run_validator("--artifact", str(ARTIFACT), "--strategy-dependency", dep)
        assert result["ok"] is True, dep


def test_buggy_e8r_dependency_remains_diagnostic_only() -> None:
    result = run_validator("--artifact", str(ARTIFACT), "--strategy-dependency", "configs/strategy_dependencies/one_sell_one_buy_buggy_e8r.yaml")
    assert check_status(result, "diagnostic_boundary") == "pass"


def test_replay_result_manifest_validates() -> None:
    result = run_validator("--artifact", "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json")
    assert result["ok"] is True


def test_full_rank_artifact_validates() -> None:
    result = run_validator("--artifact", str(FULL_RANK_ARTIFACT))
    assert result["ok"] is True
    assert check_status(result, "core_fields") == "pass"
    assert check_status(result, "available_at_lte_signal_asof") == "pass"


def test_forbidden_extension_fails(tmp_path: Path) -> None:
    manifest_path = copy_artifact(tmp_path)
    manifest = json.loads(manifest_path.read_text())
    signals_path = Path(manifest["output_files"]["signals"])
    df = pd.read_csv(signals_path)
    df["future_return_10d"] = 0.0
    df.to_csv(signals_path, index=False)
    result = run_validator_allow_fail("--artifact", str(manifest_path))
    assert result["ok"] is False
    assert check_status(result, "forbidden_fields") == "fail"


def test_missing_capability_fails(tmp_path: Path) -> None:
    manifest_path = copy_artifact(tmp_path)
    manifest = json.loads(manifest_path.read_text())
    manifest["capabilities"].pop("full_rank_exit", None)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    result = run_validator_allow_fail("--artifact", str(manifest_path), "--strategy-dependency", "configs/strategy_dependencies/top50_exit_one_worst_sell.yaml")
    assert result["ok"] is False
    assert check_status(result, "strategy_required_capabilities") == "fail"


def test_bad_dtype_and_pit_policy_fail(tmp_path: Path) -> None:
    manifest_path = copy_artifact(tmp_path)
    manifest = json.loads(manifest_path.read_text())
    signals_path = Path(manifest["output_files"]["signals"])
    df = pd.read_csv(signals_path)
    df["ext_bad_number"] = "not-a-number"
    df.to_csv(signals_path, index=False)
    manifest["extensions"] = {"schema_version": "model_signal_extension_v1", "fields": {"ext_bad_number": {"dtype": "float", "semantic_role": "risk_score", "availability_policy": "future_visible", "producer": "unit_test", "allowed_consumers": ["risk_filter"], "ranking_allowed": False, "required_for_core_replay": False, "description": "bad dtype and policy"}}}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    result = run_validator_allow_fail("--artifact", str(manifest_path))
    assert result["ok"] is False
    assert check_status(result, "extension_dtype_parseable") == "fail"
    assert check_status(result, "extension_availability_policy") == "fail"


def test_undeclared_and_declared_missing_extensions_fail(tmp_path: Path) -> None:
    manifest_path = copy_artifact(tmp_path)
    manifest = json.loads(manifest_path.read_text())
    signals_path = Path(manifest["output_files"]["signals"])
    df = pd.read_csv(signals_path)
    df["ext_undeclared"] = 1.0
    df.to_csv(signals_path, index=False)
    manifest["extensions"] = {"schema_version": "model_signal_extension_v1", "fields": {"ext_missing": {"dtype": "float", "semantic_role": "risk_score", "availability_policy": "available_at_lte_signal_asof", "producer": "unit_test", "allowed_consumers": ["risk_filter"], "ranking_allowed": False, "required_for_core_replay": False, "description": "missing in csv"}}}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    result = run_validator_allow_fail("--artifact", str(manifest_path))
    assert result["ok"] is False
    assert check_status(result, "extension_fields_declared") == "fail"
    assert check_status(result, "declared_extensions_exist") == "fail"


def test_ranking_not_allowed_extension_fails_when_dependency_uses_ranking(tmp_path: Path) -> None:
    manifest_path = copy_artifact(tmp_path)
    manifest = json.loads(manifest_path.read_text())
    signals_path = Path(manifest["output_files"]["signals"])
    df = pd.read_csv(signals_path)
    df["ext_risk_score"] = 1.0
    df.to_csv(signals_path, index=False)
    manifest["extensions"] = {"schema_version": "model_signal_extension_v1", "fields": {"ext_risk_score": {"dtype": "float", "semantic_role": "risk_score", "availability_policy": "available_at_lte_signal_asof", "producer": "unit_test", "allowed_consumers": ["buy_ordering"], "ranking_allowed": False, "required_for_core_replay": False, "description": "not ranking allowed"}}}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    dep = tmp_path / "dep.yaml"
    dep.write_text(yaml.safe_dump({"strategy_rule": "unit_test_strategy", "required_core_fields": ["date", "instrument", "candidate_rank", "buy_score"], "required_capabilities": ["core_signal_v1"], "required_extensions": [{"field": "ext_risk_score", "semantic_role": "risk_score", "usage": "buy_ordering"}], "ranking_usage": [{"field": "ext_risk_score", "usage": "buy_ordering"}]}))
    result = run_validator_allow_fail("--artifact", str(manifest_path), "--strategy-dependency", str(dep))
    assert result["ok"] is False
    assert check_status(result, "ranking_allowed") == "fail"


def test_buggy_e8r_missing_not_valid_evidence_fails(tmp_path: Path) -> None:
    dep = tmp_path / "buggy.yaml"
    dep.write_text(yaml.safe_dump({"strategy_rule": "one_sell_one_buy_buggy_e8r", "required_core_fields": ["date", "instrument", "candidate_rank", "buy_score", "full_qlib_rank"], "required_capabilities": ["core_signal_v1"], "diagnostic_only": True, "not_valid_strategy_evidence": False}))
    result = run_validator_allow_fail("--artifact", str(ARTIFACT), "--strategy-dependency", str(dep))
    assert result["ok"] is False
    assert check_status(result, "diagnostic_boundary") == "fail"


def test_registry_missing_dependency_path_fails(tmp_path: Path) -> None:
    registry = tmp_path / "registry.yaml"
    registry.write_text(yaml.safe_dump({"registry_version": "unit_test", "strategies": {"missing": {"dependency_path": "configs/strategy_dependencies/nope.yaml"}}, "contracts": {}}))
    result = run_validator_allow_fail("--artifact", str(ARTIFACT), "--registry", str(registry))
    assert result["ok"] is False
    assert check_status(result, "registry_dependency_paths") == "fail"



def test_r15_readonly_frontend_diff_scope_audit_passes_current_authorized_diff() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    import run_tw_modular_contract_regression as regression

    rows = regression.build_forbidden_scope_audit()
    frontend = next(row for row in rows if row["scope"] == regression.R15_READONLY_FRONTEND_PATH)
    assert frontend["status"] == "pass"
    if frontend["changed_path_count"]:
        assert frontend["audit_mode"] == "r15_readonly_frontend_content_audit"
        assert frontend["authorized_readonly_frontend_diff"] is True
        assert frontend["required_missing"] == ""
        assert frontend["forbidden_matches"] == ""
        assert frontend["static_check_exists"] is True
        assert frontend["e2e_check_exists"] is True

def test_r16_daily_readonly_diff_scope_audit_passes_current_authorized_diff() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    import run_tw_modular_contract_regression as regression

    rows = regression.build_forbidden_scope_audit()
    daily = next(row for row in rows if row["scope"] == regression.R16_DAILY_READONLY_PATH)
    assert daily["status"] == "pass"
    if daily["changed_path_count"]:
        assert daily["audit_mode"] == "r16_daily_readonly_content_audit"
        assert daily["required_missing"] == ""
        assert daily["forbidden_matches"] == ""
        assert daily["unit_test_exists"] is True

