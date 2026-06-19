from __future__ import annotations

import json
import subprocess
import sys

import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "scripts/validate_tw_modular_registry_m2.py"


def test_m2_registry_validator_passes_and_reports_coverage() -> None:
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    result = json.loads(proc.stdout)
    assert result["ok"] is True
    assert result["schema_version"] == "m1.0.0"
    assert result["registry_count"] == 4
    assert result["entry_count"] >= 11
    assert result["template_count"] == 9
    assert all(row["status"] == "pass" for row in result["entries"])
    assert all(row["status"] == "pass" for row in result["templates"])
    assert any(row["artifact_type"] == "agent_readonly_context" for row in result["entries"])



def run_m2_registry(path: Path) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), "--registry", str(path), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.stdout.strip(), proc.stderr
    return proc.returncode, json.loads(proc.stdout)


def write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def base_registry_entry() -> dict:
    return {
        "artifact_type": "data_source",
        "schema_version": "m1.0.0",
        "contract_doc": "docs/tw_modular_contracts/DATA_SOURCE_CONTRACT_CN.md",
        "validator": "scripts/validate_tw_modular_m_contracts.py",
        "golden_sample": "data_tw/golden_samples/modular_contracts/m1/data_source/pass_minimal",
        "capabilities": ["raw_source_declared"],
        "dependencies": [],
        "allowed_consumers": ["data_ingestion"],
        "forbidden_consumers": ["broker"],
        "production_allowed": False,
        "diagnostic_only": False,
        "owner_or_stage": "test",
    }


def test_registry_contract_mismatch_fails(tmp_path: Path) -> None:
    entry = base_registry_entry()
    entry["golden_sample"] = "data_tw/golden_samples/modular_contracts/m1/feature_artifact/pass_pit_safe"
    registry = tmp_path / "registry.yaml"
    write_yaml(registry, {"entries": {"bad_entry": entry}})
    code, result = run_m2_registry(registry)
    assert code != 0
    assert any(err["code"] == "registry_contract_mismatch" for err in result["errors"])


def test_registry_validator_contract_unsupported_fails(tmp_path: Path) -> None:
    sample = tmp_path / "unknown_sample"
    sample.mkdir()
    (sample / "expected_result.json").write_text(
        json.dumps({"contract": "unknown_contract", "schema_version": "m1.0.0", "expected_ok": True, "expected_error_codes": []}),
        encoding="utf-8",
    )
    entry = base_registry_entry()
    entry["artifact_type"] = "unknown_contract"
    entry["contract_doc"] = "docs/tw_modular_contracts/DATA_SOURCE_CONTRACT_CN.md"
    entry["golden_sample"] = str(sample)
    registry = tmp_path / "registry.yaml"
    write_yaml(registry, {"entries": {"bad_entry": entry}})
    code, result = run_m2_registry(registry)
    assert code != 0
    assert any(err["code"] == "registry_validator_contract_unsupported" for err in result["errors"])


def test_registry_actual_golden_validation_failure_fails(tmp_path: Path) -> None:
    sample = tmp_path / "bad_data_source"
    sample.mkdir()
    (sample / "expected_result.json").write_text(
        json.dumps({"contract": "data_source", "schema_version": "m1.0.0", "expected_ok": True, "expected_error_codes": []}),
        encoding="utf-8",
    )
    (sample / "manifest.json").write_text(json.dumps({"artifact_type": "data_source", "schema_version": "m1.0.0"}), encoding="utf-8")
    entry = base_registry_entry()
    entry["golden_sample"] = str(sample)
    registry = tmp_path / "registry.yaml"
    write_yaml(registry, {"entries": {"bad_entry": entry}})
    code, result = run_m2_registry(registry)
    assert code != 0
    assert any(err["code"] == "registry_golden_validation_failed" for err in result["errors"])
