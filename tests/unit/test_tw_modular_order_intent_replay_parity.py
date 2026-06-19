from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts/run_tw_modular_order_intent_replay_parity.py"
VALIDATOR = ROOT / "scripts/validate_tw_modular_order_intent_replay_parity.py"
RULES = {
    "original",
    "top50_exit_all",
    "top50_exit_one_worst_sell",
    "one_sell_one_buy_correct",
    "one_sell_one_buy_buggy_e8r",
}


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def run_parity(tmp_path: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(RUNNER), "--out-dir", str(tmp_path / "d3_parity"), "--json"],
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


def copy_artifact(src_manifest: Path, dst_dir: Path) -> Path:
    shutil.copytree(src_manifest.parent, dst_dir)
    manifest_path = dst_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for key, rel_path in list(manifest["artifacts"].items()):
        manifest["artifacts"][key] = str(dst_dir / Path(rel_path).name)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def statuses(validation: dict) -> dict[str, str]:
    return {row["name"]: row["status"] for row in validation["checks"]}


def mutate_status_csv(path: Path, details: str = "mutated") -> None:
    frame = pd.read_csv(path)
    if "details" not in frame.columns:
        frame["details"] = ""
    frame["details"] = frame["details"].fillna("").astype(str)
    frame.loc[0, "status"] = "fail"
    frame.loc[0, "details"] = details
    frame.to_csv(path, index=False)


def test_d3_parity_artifact_validates(tmp_path: Path) -> None:
    result = run_parity(tmp_path)
    assert result["ok"] is True
    manifest = resolve_path(result["manifest"])
    validation = run_validate(manifest)
    assert validation["ok"] is True
    checks = statuses(validation)
    assert checks["five_rules_all_present"] == "pass"
    assert checks["summary_parity_all_pass"] == "pass"
    assert checks["daily_nav_parity_all_pass"] == "pass"
    assert checks["actions_parity_all_pass"] == "pass"
    assert checks["action_key_parity_all_pass"] == "pass"
    assert checks["position_snapshot_parity_all_pass"] == "pass"


def test_d3_five_rules_present(tmp_path: Path) -> None:
    result = run_parity(tmp_path)
    manifest = json.loads(resolve_path(result["manifest"]).read_text(encoding="utf-8"))
    assert set(manifest["rules_present"]) == RULES
    assert set(manifest["rules"]) == RULES
    assert manifest["window"] == "2026_ytd"


def test_d3_rejects_missing_rule(tmp_path: Path) -> None:
    result = run_parity(tmp_path)
    dst_manifest = copy_artifact(resolve_path(result["manifest"]), tmp_path / "missing_rule")
    manifest = json.loads(dst_manifest.read_text(encoding="utf-8"))
    manifest["rules_present"] = [rule for rule in manifest["rules_present"] if rule != "top50_exit_all"]
    dst_manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    validation = run_validate(dst_manifest, check=False)
    assert validation["ok"] is False
    assert statuses(validation)["five_rules_all_present"] == "fail"


def test_d3_rejects_summary_mismatch(tmp_path: Path) -> None:
    result = run_parity(tmp_path)
    dst_manifest = copy_artifact(resolve_path(result["manifest"]), tmp_path / "summary_mismatch")
    manifest = json.loads(dst_manifest.read_text(encoding="utf-8"))
    mutate_status_csv(Path(manifest["artifacts"]["summary_parity"]), "forced summary mismatch")
    validation = run_validate(dst_manifest, check=False)
    assert validation["ok"] is False
    assert statuses(validation)["summary_parity_all_pass"] == "fail"


def test_d3_rejects_daily_nav_mismatch(tmp_path: Path) -> None:
    result = run_parity(tmp_path)
    dst_manifest = copy_artifact(resolve_path(result["manifest"]), tmp_path / "daily_nav_mismatch")
    manifest = json.loads(dst_manifest.read_text(encoding="utf-8"))
    mutate_status_csv(Path(manifest["artifacts"]["daily_nav_parity"]), "forced daily nav mismatch")
    validation = run_validate(dst_manifest, check=False)
    assert validation["ok"] is False
    assert statuses(validation)["daily_nav_parity_all_pass"] == "fail"


def test_d3_rejects_action_key_mismatch(tmp_path: Path) -> None:
    result = run_parity(tmp_path)
    dst_manifest = copy_artifact(resolve_path(result["manifest"]), tmp_path / "action_key_mismatch")
    manifest = json.loads(dst_manifest.read_text(encoding="utf-8"))
    mutate_status_csv(Path(manifest["artifacts"]["action_key_parity"]), "forced action key mismatch")
    validation = run_validate(dst_manifest, check=False)
    assert validation["ok"] is False
    assert statuses(validation)["action_key_parity_all_pass"] == "fail"


def test_d3_rejects_position_snapshot_mismatch(tmp_path: Path) -> None:
    result = run_parity(tmp_path)
    dst_manifest = copy_artifact(resolve_path(result["manifest"]), tmp_path / "position_mismatch")
    manifest = json.loads(dst_manifest.read_text(encoding="utf-8"))
    mutate_status_csv(Path(manifest["artifacts"]["position_snapshot_parity"]), "forced position snapshot mismatch")
    validation = run_validate(dst_manifest, check=False)
    assert validation["ok"] is False
    assert statuses(validation)["position_snapshot_parity_all_pass"] == "fail"


def test_d3_rejects_diagnostic_rule_as_valid_strategy_evidence(tmp_path: Path) -> None:
    result = run_parity(tmp_path)
    dst_manifest = copy_artifact(resolve_path(result["manifest"]), tmp_path / "diagnostic_invalid")
    manifest = json.loads(dst_manifest.read_text(encoding="utf-8"))
    manifest["diagnostic_rule_only_for_parity"] = False
    manifest["diagnostic_rule_not_valid_strategy_evidence"] = False
    dst_manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    validation = run_validate(dst_manifest, check=False)
    assert validation["ok"] is False
    assert statuses(validation)["diagnostic_rule_marked_diagnostic_only"] == "fail"


def test_d3_rejects_order_intent_replay_manifest_equal_to_baseline_manifest(tmp_path: Path) -> None:
    result = run_parity(tmp_path)
    dst_manifest = copy_artifact(resolve_path(result["manifest"]), tmp_path / "same_source")
    manifest = json.loads(dst_manifest.read_text(encoding="utf-8"))
    manifest["order_intent_replay_manifest"] = manifest["baseline_manifest"]
    dst_manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    validation = run_validate(dst_manifest, check=False)
    assert validation["ok"] is False
    assert statuses(validation)["order_intent_replay_manifest_not_equal_baseline_manifest"] == "fail"


def test_d3_rejects_legacy_formal_replay_manifest_as_order_intent_replay_source(tmp_path: Path) -> None:
    result = run_parity(tmp_path)
    dst_manifest = copy_artifact(resolve_path(result["manifest"]), tmp_path / "legacy_replay_source")
    manifest = json.loads(dst_manifest.read_text(encoding="utf-8"))
    manifest["order_intent_replay_manifest"] = manifest["baseline_manifest"]
    dst_manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    validation = run_validate(dst_manifest, check=False)
    checks = statuses(validation)
    assert validation["ok"] is False
    assert checks["reject_legacy_formal_replay_manifest_as_replay_source"] == "fail"


def test_d3_rejects_missing_order_intent_artifact(tmp_path: Path) -> None:
    result = run_parity(tmp_path)
    dst_manifest = copy_artifact(resolve_path(result["manifest"]), tmp_path / "missing_order_intent")
    manifest = json.loads(dst_manifest.read_text(encoding="utf-8"))
    replay_manifest_path = resolve_path(manifest["order_intent_replay_manifest"])
    replay_manifest = json.loads(replay_manifest_path.read_text(encoding="utf-8"))
    replay_manifest["order_intent_artifacts"] = replay_manifest["order_intent_artifacts"][:1] + [str(tmp_path / "missing_order_intent.json")]
    replay_manifest_path.write_text(json.dumps(replay_manifest, indent=2) + "\n", encoding="utf-8")
    validation = run_validate(dst_manifest, check=False)
    assert validation["ok"] is False
    assert statuses(validation)["order_intent_artifacts_exist"] == "fail"


def test_d3_rejects_replay_manifest_without_order_intent_decision_source(tmp_path: Path) -> None:
    result = run_parity(tmp_path)
    dst_manifest = copy_artifact(resolve_path(result["manifest"]), tmp_path / "bad_decision_source")
    manifest = json.loads(dst_manifest.read_text(encoding="utf-8"))
    replay_manifest_path = resolve_path(manifest["order_intent_replay_manifest"])
    replay_manifest = json.loads(replay_manifest_path.read_text(encoding="utf-8"))
    replay_manifest["decision_source"] = "legacy_formal_replay"
    replay_manifest_path.write_text(json.dumps(replay_manifest, indent=2) + "\n", encoding="utf-8")
    validation = run_validate(dst_manifest, check=False)
    assert validation["ok"] is False
    assert statuses(validation)["order_intent_replay_manifest_decision_source_order_intent"] == "fail"


def test_d3_rejects_actions_without_order_intent_artifact_reference(tmp_path: Path) -> None:
    result = run_parity(tmp_path)
    dst_manifest = copy_artifact(resolve_path(result["manifest"]), tmp_path / "missing_action_refs")
    manifest = json.loads(dst_manifest.read_text(encoding="utf-8"))
    replay_manifest = json.loads(resolve_path(manifest["order_intent_replay_manifest"]).read_text(encoding="utf-8"))
    actions_path = resolve_path(replay_manifest["artifacts"]["actions"])
    actions = pd.read_csv(actions_path)
    actions.loc[0, "order_intent_artifact"] = ""
    actions.to_csv(actions_path, index=False)
    validation = run_validate(dst_manifest, check=False)
    assert validation["ok"] is False
    assert statuses(validation)["replay_actions_reference_order_intent_artifact"] == "fail"


def test_d3_rejects_decision_source_audit_pointing_to_baseline_manifest(tmp_path: Path) -> None:
    result = run_parity(tmp_path)
    dst_manifest = copy_artifact(resolve_path(result["manifest"]), tmp_path / "bad_decision_audit")
    manifest = json.loads(dst_manifest.read_text(encoding="utf-8"))
    audit_path = Path(manifest["artifacts"]["decision_source_audit"])
    audit = pd.read_csv(audit_path)
    audit.loc[audit["audit_name"].astype(str) == "decision_source", "details"] = manifest["baseline_manifest"]
    audit.to_csv(audit_path, index=False)
    validation = run_validate(dst_manifest, check=False)
    assert validation["ok"] is False
    assert statuses(validation)["decision_source_audit_points_to_order_intent_replay_manifest"] == "fail"



def test_rejects_order_intents_generated_from_replay_actions(tmp_path: Path) -> None:
    result = run_parity(tmp_path)
    dst_manifest = copy_artifact(resolve_path(result["manifest"]), tmp_path / "order_intents_from_replay_actions")
    manifest = json.loads(dst_manifest.read_text(encoding="utf-8"))
    replay_manifest = json.loads(resolve_path(manifest["order_intent_replay_manifest"]).read_text(encoding="utf-8"))
    for order_manifest_path in replay_manifest["order_intent_artifacts"]:
        order_manifest_file = resolve_path(order_manifest_path)
        order_manifest = json.loads(order_manifest_file.read_text(encoding="utf-8"))
        order_manifest["generation_source"] = "replay_actions"
        order_manifest["not_generated_from_replay_actions"] = False
        order_manifest_file.write_text(json.dumps(order_manifest, indent=2) + "\n", encoding="utf-8")
    validation = run_validate(dst_manifest, check=False)
    assert validation["ok"] is False
    checks = statuses(validation)
    assert checks["order_intents_generation_source_strategy_decision_engine"] == "fail"


def test_rejects_order_intents_generated_from_replay_snapshots(tmp_path: Path) -> None:
    result = run_parity(tmp_path)
    dst_manifest = copy_artifact(resolve_path(result["manifest"]), tmp_path / "order_intents_from_replay_snapshots")
    manifest = json.loads(dst_manifest.read_text(encoding="utf-8"))
    replay_manifest = json.loads(resolve_path(manifest["order_intent_replay_manifest"]).read_text(encoding="utf-8"))
    for order_manifest_path in replay_manifest["order_intent_artifacts"]:
        order_manifest_file = resolve_path(order_manifest_path)
        order_manifest = json.loads(order_manifest_file.read_text(encoding="utf-8"))
        order_manifest["not_generated_from_replay_snapshots"] = False
        order_manifest_file.write_text(json.dumps(order_manifest, indent=2) + "\n", encoding="utf-8")
    validation = run_validate(dst_manifest, check=False)
    assert validation["ok"] is False
    assert statuses(validation)["order_intents_not_generated_from_replay_snapshots"] == "fail"


def test_rejects_replay_result_generated_by_parity_wrapper_copy(tmp_path: Path) -> None:
    result = run_parity(tmp_path)
    dst_manifest = copy_artifact(resolve_path(result["manifest"]), tmp_path / "parity_wrapper_copy")
    manifest = json.loads(dst_manifest.read_text(encoding="utf-8"))
    replay_manifest_path = resolve_path(manifest["order_intent_replay_manifest"])
    replay_manifest = json.loads(replay_manifest_path.read_text(encoding="utf-8"))
    replay_manifest["generated_by"] = "parity_wrapper_copy"
    replay_manifest_path.write_text(json.dumps(replay_manifest, indent=2) + "\n", encoding="utf-8")
    validation = run_validate(dst_manifest, check=False)
    assert validation["ok"] is False
    assert statuses(validation)["replay_result_generated_by_replay_execution_engine"] == "fail"


def test_rejects_replay_result_without_execution_input_source_order_intent(tmp_path: Path) -> None:
    result = run_parity(tmp_path)
    dst_manifest = copy_artifact(resolve_path(result["manifest"]), tmp_path / "no_order_intent_input")
    manifest = json.loads(dst_manifest.read_text(encoding="utf-8"))
    replay_manifest_path = resolve_path(manifest["order_intent_replay_manifest"])
    replay_manifest = json.loads(replay_manifest_path.read_text(encoding="utf-8"))
    replay_manifest["execution_input_source"] = "legacy_replay"
    replay_manifest_path.write_text(json.dumps(replay_manifest, indent=2) + "\n", encoding="utf-8")
    validation = run_validate(dst_manifest, check=False)
    assert validation["ok"] is False
    assert statuses(validation)["replay_result_execution_input_source_order_intent"] == "fail"


def test_rejects_action_refs_that_do_not_match_order_intent_rows(tmp_path: Path) -> None:
    result = run_parity(tmp_path)
    dst_manifest = copy_artifact(resolve_path(result["manifest"]), tmp_path / "bad_action_refs")
    manifest = json.loads(dst_manifest.read_text(encoding="utf-8"))
    replay_manifest = json.loads(resolve_path(manifest["order_intent_replay_manifest"]).read_text(encoding="utf-8"))
    actions_path = resolve_path(replay_manifest["artifacts"]["actions"])
    actions = pd.read_csv(actions_path)
    actions.loc[0, "order_intent_row_id"] = "missing-row-id"
    actions.to_csv(actions_path, index=False)
    validation = run_validate(dst_manifest, check=False)
    assert validation["ok"] is False
    assert statuses(validation)["replay_result_actions_order_intent_rows_exist_and_match"] == "fail"


def test_rejects_action_rows_with_blank_decision_fields_when_required(tmp_path: Path) -> None:
    result = run_parity(tmp_path)
    dst_manifest = copy_artifact(resolve_path(result["manifest"]), tmp_path / "blank_decision_fields")
    manifest = json.loads(dst_manifest.read_text(encoding="utf-8"))
    replay_manifest = json.loads(resolve_path(manifest["order_intent_replay_manifest"]).read_text(encoding="utf-8"))
    order_manifest_path = resolve_path(replay_manifest["order_intent_artifacts"][0])
    order_manifest = json.loads(order_manifest_path.read_text(encoding="utf-8"))
    order_path = resolve_path(order_manifest["output_files"]["order_intents"])
    frame = pd.read_csv(order_path)
    action_idx = frame[frame["intent_action"].astype(str).isin(["buy", "sell"])].index[0]
    frame.loc[action_idx, ["candidate_rank", "buy_rank", "full_qlib_rank"]] = ""
    frame.to_csv(order_path, index=False)
    validation = run_validate(dst_manifest, check=False)
    assert validation["ok"] is False
    assert statuses(validation)["order_intent_action_rows_have_decision_fields"] == "fail"


def test_rejects_legacy_replay_used_as_execution_source(tmp_path: Path) -> None:
    result = run_parity(tmp_path)
    dst_manifest = copy_artifact(resolve_path(result["manifest"]), tmp_path / "legacy_replay_exec_source")
    manifest = json.loads(dst_manifest.read_text(encoding="utf-8"))
    replay_manifest_path = resolve_path(manifest["order_intent_replay_manifest"])
    replay_manifest = json.loads(replay_manifest_path.read_text(encoding="utf-8"))
    replay_manifest["legacy_replay_used_only_for_parity"] = False
    replay_manifest_path.write_text(json.dumps(replay_manifest, indent=2) + "\n", encoding="utf-8")
    validation = run_validate(dst_manifest, check=False)
    assert validation["ok"] is False
    assert statuses(validation)["legacy_replay_used_only_for_parity"] == "fail"
