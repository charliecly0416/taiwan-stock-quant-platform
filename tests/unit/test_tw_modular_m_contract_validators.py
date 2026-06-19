from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "scripts/validate_tw_modular_m_contracts.py"
GOLDEN_ROOT = ROOT / "data_tw/golden_samples/modular_contracts/m1"


def run_validator(*args: str) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), *args, "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.stdout.strip(), proc.stderr
    return proc.returncode, json.loads(proc.stdout)


def sample_dirs() -> list[Path]:
    return sorted(path.parent for path in GOLDEN_ROOT.glob("*/*/expected_result.json"))


def test_m1_golden_batch_passes_and_json_is_parseable() -> None:
    code, result = run_validator("--run-golden")
    assert code == 0
    assert result["ok"] is True
    assert result["schema_version"] == "m1.0.0"
    assert result["sample_count"] == len(sample_dirs())
    assert result["sample_count"] >= 24


def test_each_golden_sample_matches_expected_error_codes() -> None:
    for sample_dir in sample_dirs():
        expected = json.loads((sample_dir / "expected_result.json").read_text(encoding="utf-8"))
        code, result = run_validator("--contract", expected["contract"], "--artifact-path", str(sample_dir))
        assert (code == 0) is expected["expected_ok"], sample_dir
        assert result["ok"] is expected["expected_ok"], sample_dir
        assert result["contract"] == expected["contract"]
        assert result["schema_version"] == expected["schema_version"]
        actual_codes = sorted({item["code"] for item in result["errors"]})
        assert actual_codes == sorted(expected["expected_error_codes"]), sample_dir
        for err in result["errors"]:
            assert {"code", "message", "path", "field"}.issubset(err), err


def test_contract_list_includes_all_m0_contracts() -> None:
    code, result = run_validator("--list-contracts")
    assert code == 0
    assert set(result["contracts"]) >= {
        "data_source",
        "data_ingestion",
        "feature_artifact",
        "price_store",
        "daily_orchestrator",
        "run_registry",
        "auto_update",
        "analysis_artifact",
        "frontend_readonly_display",
        "agent_readonly_context",
        "frontend_agent_panel",
        "default_candidate_decision",
        "model_signal",
        "strategy_rule",
        "readonly_replay_window",
    }


def test_response_semantics_audit_count_fails_without_answer_text_match() -> None:
    sample_dir = GOLDEN_ROOT / "agent_readonly_context/fail_response_semantics_audit_count"
    code, result = run_validator("--contract", "agent_readonly_context", "--artifact-path", str(sample_dir))
    assert code != 0
    assert result["ok"] is False
    assert sorted({item["code"] for item in result["errors"]}) == ["forbidden_semantics"]
    assert all("应该买入" not in item["message"] for item in result["errors"])
