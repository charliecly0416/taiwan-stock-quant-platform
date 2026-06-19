from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "scripts/build_tw_modular_readonly_standard_artifact_index.py"
VALIDATOR = ROOT / "scripts/validate_tw_modular_readonly_standard_artifact_index.py"
POLICY_VALIDATOR = ROOT / "scripts/validate_tw_replay_window_policy.py"
POLICY = ROOT / "configs/tw_replay_window_policy.yaml"
D3RR = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T062610Z/manifest.json"


def run_json(args: list[str], *, check: bool = True) -> dict:
    proc = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=check)
    return json.loads(proc.stdout)


def run_build(tmp_path: Path, policy: Path = POLICY) -> dict:
    return run_json([
        sys.executable,
        str(BUILDER),
        "--d3rr-manifest",
        str(D3RR),
        "--policy",
        str(policy),
        "--out-dir",
        str(tmp_path / "d4_index"),
        "--json",
    ])


def statuses(result: dict) -> dict[str, str]:
    return {row["name"]: row["status"] for row in result["checks"]}


def test_d4_policy_validates() -> None:
    result = run_json([sys.executable, str(POLICY_VALIDATOR), "--policy", str(POLICY), "--json"])
    assert result["ok"] is True
    checks = statuses(result)
    assert checks["fixed_window_only"] == "pass"
    assert checks["user_selectable_range_disabled"] == "pass"
    assert checks["fixed_window_does_not_overlap_training_windows"] == "pass"
    assert checks["diagnostic_rule_not_valid_strategy_evidence"] == "pass"


def test_build_d4_readonly_standard_artifact_index_validates(tmp_path: Path) -> None:
    result = run_build(tmp_path)
    assert result["ok"] is True
    manifest = ROOT / result["manifest"]
    validation = run_json([sys.executable, str(VALIDATOR), "--artifact", str(manifest), "--json"])
    assert validation["ok"] is True
    checks = statuses(validation)
    assert checks["readonly_only"] == "pass"
    assert checks["fixed_window_only"] == "pass"
    assert checks["user_selectable_range_disabled"] == "pass"
    assert checks["replay_result_generated_by_replay_execution_engine"] == "pass"
    assert checks["checksum_ok"] == "pass"


def test_d4_index_rejects_legacy_replay_as_replay_source(tmp_path: Path) -> None:
    result = run_build(tmp_path)
    manifest_path = ROOT / result["manifest"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["order_intent_replay_result_manifest"] = manifest["baseline_manifest"]
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    validation = run_json([sys.executable, str(VALIDATOR), "--artifact", str(manifest_path), "--json"], check=False)
    assert validation["ok"] is False
    assert statuses(validation)["order_intent_replay_manifest_not_equal_baseline_manifest"] == "fail"


def test_d4_index_rejects_user_selectable_range_without_backend_validator(tmp_path: Path) -> None:
    result = run_build(tmp_path)
    manifest_path = ROOT / result["manifest"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["user_selectable_range_enabled"] = True
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    validation = run_json([sys.executable, str(VALIDATOR), "--artifact", str(manifest_path), "--json"], check=False)
    assert validation["ok"] is False
    assert statuses(validation)["user_selectable_range_disabled"] == "fail"


def test_policy_rejects_training_window_overlap(tmp_path: Path) -> None:
    policy = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
    policy["fixed_window"] = {"name": "bad_train_window", "start": "2025-01-01", "end": "2025-12-31"}
    policy["allowed_windows"] = [{"name": "bad_train_window", "start": "2025-01-01", "end": "2025-12-31", "source": "unit_test"}]
    policy_path = tmp_path / "bad_policy.yaml"
    policy_path.write_text(yaml.safe_dump(policy, sort_keys=False), encoding="utf-8")
    validation = run_json([sys.executable, str(POLICY_VALIDATOR), "--policy", str(policy_path), "--json"], check=False)
    assert validation["ok"] is False
    checks = statuses(validation)
    assert checks["fixed_window_2026_ytd"] == "fail"
    assert checks["fixed_window_does_not_overlap_training_windows"] == "fail"


def test_d4_changed_files_do_not_define_write_api_or_trading_terms(tmp_path: Path) -> None:
    result = run_build(tmp_path)
    manifest = json.loads((ROOT / result["manifest"]).read_text(encoding="utf-8"))
    assert manifest["readonly_only"] is True
    assert manifest["not_order"] is True
    assert manifest["not_investment_advice"] is True
    assert manifest["not_target_position"] is True
    assert manifest["no_provider_publish"] is True
    assert manifest["no_accepted_latest_switch"] is True
    assert manifest["no_monitor_broker_order"] is True

    changed = [
        ROOT / "scripts/build_tw_modular_readonly_standard_artifact_index.py",
        ROOT / "scripts/validate_tw_modular_readonly_standard_artifact_index.py",
        ROOT / "scripts/validate_tw_replay_window_policy.py",
        ROOT / "configs/tw_replay_window_policy.yaml",
    ]
    forbidden = ["POST /api", "PUT /api", "PATCH /api", "DELETE /api", "broker.submit", "create_order", "requests.post", "requests.put", "requests.patch", "requests.delete"]
    for path in changed:
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text


def test_d5_query_validator_reads_generated_non_fixed_window_artifact() -> None:
    result = run_json([sys.executable, str(ROOT / "scripts/validate_tw_readonly_replay_window_query.py"), "--json"])
    assert result["ok"] is True
    checks = statuses(result)
    assert checks["valid_standard_window_ok"] == "pass"
    assert checks["generated_non_fixed_window_readable"] == "pass"
    assert checks["generated_non_fixed_window_not_on_demand"] == "pass"
    assert checks["illegal_training_window_rejected_by_backend"] == "pass"
    assert checks["diagnostic_rule_not_valid_strategy_evidence"] == "pass"


def test_d6_generated_artifact_validates(tmp_path: Path) -> None:
    manifest = ROOT / "data_tw/artifacts/readonly_replay_windows/d6/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/20260102_20260507/order_intent_replay_result/manifest.json"
    result = run_json([sys.executable, str(ROOT / "scripts/validate_tw_readonly_replay_window_artifact.py"), "--artifact", str(manifest), "--json"])
    assert result["ok"] is True
    checks = statuses(result)
    assert checks["readonly_only"] == "pass"
    assert checks["generated_by_replay_execution_engine"] == "pass"
    assert checks["execution_input_source_order_intent"] == "pass"
    assert checks["policy_validation_ok"] == "pass"
    assert checks["checksum_ok"] == "pass"
