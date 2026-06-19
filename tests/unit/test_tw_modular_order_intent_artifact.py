from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "scripts/build_tw_modular_order_intent_artifact.py"
VALIDATOR = ROOT / "scripts/validate_tw_modular_order_intent_artifact.py"


def run_build(tmp_path: Path, *args: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(BUILDER), "--out-root", str(tmp_path / "order_intents"), *args, "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(proc.stdout)


def run_validate(manifest: str | Path, *, check: bool = True) -> dict:
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), "--artifact", str(manifest), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=check,
    )
    return json.loads(proc.stdout)


def test_decision_functions_exist() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_tw_modular_order_intent_artifact as builder

    expected = {
        "original",
        "top50_exit_all",
        "top50_exit_one_worst_sell",
        "one_sell_one_buy_correct",
        "one_sell_one_buy_buggy_e8r",
    }
    assert expected == set(builder.DECISION_FUNCTIONS)
    for rule in expected:
        assert builder.DECISION_FUNCTIONS[rule].__name__ == f"decide_{rule}"


def test_build_default_order_intent_artifact_validates(tmp_path: Path) -> None:
    result = run_build(tmp_path)
    assert result["ok"] is True
    validation = run_validate(ROOT / result["manifest"])
    assert validation["ok"] is True
    check_names = {row["name"]: row["status"] for row in validation["checks"]}
    assert check_names["buy_rank_mapping_validated"] == "pass"
    assert check_names["legacy_portfolio_state_boundary"] == "pass"
    assert check_names["not_used_for_replay_result"] == "pass"
    assert check_names["not_parity_evidence"] == "pass"


def test_diagnostic_rule_artifact_keeps_diagnostic_boundary(tmp_path: Path) -> None:
    result = run_build(tmp_path, "--rule", "one_sell_one_buy_buggy_e8r")
    validation = run_validate(ROOT / result["manifest"])
    assert validation["ok"] is True
    manifest = json.loads((ROOT / result["manifest"]).read_text(encoding="utf-8"))
    assert manifest["diagnostic_only"] is True
    assert manifest["not_valid_strategy_evidence"] is True
    checks = {row["name"]: row["status"] for row in validation["checks"]}
    assert checks["diagnostic_rule_boundary"] == "pass"


def test_validator_rejects_forbidden_execution_field(tmp_path: Path) -> None:
    result = run_build(tmp_path)
    src_manifest = ROOT / result["manifest"]
    src_dir = src_manifest.parent
    dst_dir = tmp_path / "mutated"
    shutil.copytree(src_dir, dst_dir)
    manifest = json.loads((dst_dir / "manifest.json").read_text(encoding="utf-8"))
    manifest["output_files"]["order_intents"] = str(dst_dir / "order_intents.csv")
    manifest["output_files"]["schema"] = str(dst_dir / "schema.json")
    manifest["output_files"]["strategy_decision_audit"] = str(dst_dir / "strategy_decision_audit.csv")
    manifest["output_files"]["forbidden_action_audit"] = str(dst_dir / "forbidden_action_audit.json")
    (dst_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    frame = pd.read_csv(dst_dir / "order_intents.csv")
    frame["execution_price"] = 100.0
    frame.to_csv(dst_dir / "order_intents.csv", index=False)

    validation = run_validate(dst_dir / "manifest.json", check=False)
    assert validation["ok"] is False
    checks = {row["name"]: row for row in validation["checks"]}
    assert checks["forbidden_fields_absent"]["status"] == "fail"
    assert "execution_price" in checks["forbidden_fields_absent"]["details"]


def test_validator_rejects_buy_rank_mapping_break(tmp_path: Path) -> None:
    result = run_build(tmp_path)
    src_manifest = ROOT / result["manifest"]
    src_dir = src_manifest.parent
    dst_dir = tmp_path / "rank_mutated"
    shutil.copytree(src_dir, dst_dir)
    manifest = json.loads((dst_dir / "manifest.json").read_text(encoding="utf-8"))
    manifest["output_files"]["order_intents"] = str(dst_dir / "order_intents.csv")
    manifest["output_files"]["schema"] = str(dst_dir / "schema.json")
    manifest["output_files"]["strategy_decision_audit"] = str(dst_dir / "strategy_decision_audit.csv")
    manifest["output_files"]["forbidden_action_audit"] = str(dst_dir / "forbidden_action_audit.json")
    (dst_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    frame = pd.read_csv(dst_dir / "order_intents.csv")
    idx = frame[pd.to_numeric(frame["buy_rank"], errors="coerce") >= 0].index[0]
    frame.loc[idx, "buy_rank"] = 999
    frame.to_csv(dst_dir / "order_intents.csv", index=False)

    validation = run_validate(dst_dir / "manifest.json", check=False)
    assert validation["ok"] is False
    checks = {row["name"]: row for row in validation["checks"]}
    assert checks["buy_rank_mapping_validated"]["status"] == "fail"
