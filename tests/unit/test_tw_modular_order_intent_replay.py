from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts/run_tw_modular_order_intent_replay.py"
VALIDATOR = ROOT / "scripts/validate_tw_modular_order_intent_replay.py"


def resolve_manifest(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def run_replay(tmp_path: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(RUNNER), "--out-dir", str(tmp_path / "d2_replay"), "--json"],
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


def load_replay_frames(result: dict) -> tuple[Path, dict, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    manifest_path = resolve_manifest(result["manifest"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    daily_nav = pd.read_csv(ROOT / manifest["artifacts"]["daily_nav"])
    snapshots = pd.read_csv(ROOT / manifest["artifacts"]["snapshots"])
    actions = pd.read_csv(ROOT / manifest["artifacts"]["actions"])
    return manifest_path, manifest, daily_nav, snapshots, actions


def copy_artifact_for_mutation(src_manifest: Path, dst_dir: Path) -> Path:
    shutil.copytree(src_manifest.parent, dst_dir)
    manifest_path = dst_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for key, rel_path in list(manifest["artifacts"].items()):
        manifest["artifacts"][key] = str(dst_dir / Path(rel_path).name)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def check_statuses(validation: dict) -> dict[str, str]:
    return {row["name"]: row["status"] for row in validation["checks"]}


def test_d2_replay_from_order_intent_validates(tmp_path: Path) -> None:
    result = run_replay(tmp_path)
    assert result["ok"] is True
    validation = run_validate(resolve_manifest(result["manifest"]))
    assert validation["ok"] is True
    checks = check_statuses(validation)
    assert checks["decision_source"] == "pass"
    assert checks["no_" + "choose_" + "sells_call"] == "pass"
    assert checks["no_model_signal_decision_read"] == "pass"
    assert checks["parity_not_claimed"] == "pass"
    assert checks["snapshots_required_columns"] == "pass"
    assert checks["daily_nav_holding_count_matches_snapshots"] == "pass"


def test_d2_runner_source_does_not_embed_strategy_decision() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    forbidden = [
        "def " + "choose_" + "sells",
        "choose_" + "sells(",
        "candidate_rank" + " <=",
        "buy" + "_score",
        "score" + "_rank",
    ]
    hits = [text for text in forbidden if text in source]
    assert hits == []
    assert "decision_source" in source
    assert "order_intent_artifact" in source


def test_d2_actions_reference_order_intent_artifact(tmp_path: Path) -> None:
    result = run_replay(tmp_path)
    _manifest_path, manifest, _daily_nav, _snapshots, actions = load_replay_frames(result)
    active = actions[actions["action"].isin(["historical_add", "historical_risk_reduce"])]
    assert not active.empty
    assert set(active["order_intent_artifact"].astype(str)) == {manifest["order_intent_artifact"]}


def test_d2_position_snapshots_are_date_specific(tmp_path: Path) -> None:
    result = run_replay(tmp_path)
    _manifest_path, _manifest, _daily_nav, snapshots, _actions = load_replay_frames(result)
    day0 = snapshots[snapshots["date"].astype(str) == "2026-05-06"]
    day1 = snapshots[snapshots["date"].astype(str) == "2026-05-07"]
    day0_state = dict(zip(day0["instrument"], day0["quantity"]))
    day1_state = dict(zip(day1["instrument"], day1["quantity"]))
    assert day0_state.get("TW2467") == 280
    assert "TW2337" not in day0_state
    assert day1_state.get("TW2337") == 820
    assert "TW2467" not in day1_state


def test_daily_nav_holding_count_matches_snapshot_rows(tmp_path: Path) -> None:
    result = run_replay(tmp_path)
    _manifest_path, _manifest, daily_nav, snapshots, _actions = load_replay_frames(result)
    positive = snapshots[pd.to_numeric(snapshots["quantity"], errors="coerce").fillna(0) > 0]
    counts = positive.groupby(positive["date"].astype(str)).size().to_dict()
    for row in daily_nav.to_dict("records"):
        assert int(row["holding_count"]) == int(counts.get(str(row["date"]), 0))


def test_validator_rejects_future_buy_backfilled_into_signal_date_snapshot(tmp_path: Path) -> None:
    result = run_replay(tmp_path)
    src_manifest = resolve_manifest(result["manifest"])
    dst_manifest = copy_artifact_for_mutation(src_manifest, tmp_path / "future_buy_mutated")
    manifest = json.loads(dst_manifest.read_text(encoding="utf-8"))
    snapshots_path = Path(manifest["artifacts"]["snapshots"])
    snapshots = pd.read_csv(snapshots_path)
    future_buy = snapshots[
        (snapshots["date"].astype(str) == "2026-05-07")
        & (snapshots["instrument"].astype(str) == "TW2337")
    ].copy()
    assert len(future_buy) == 1
    future_buy.loc[:, "date"] = "2026-05-06"
    snapshots = pd.concat([snapshots, future_buy], ignore_index=True)
    snapshots.to_csv(snapshots_path, index=False)
    validation = run_validate(dst_manifest, check=False)
    checks = check_statuses(validation)
    assert validation["ok"] is False
    assert checks["no_future_buy_in_signal_date_snapshot"] == "fail"


def test_validator_rejects_sell_symbol_remaining_after_execution_date(tmp_path: Path) -> None:
    result = run_replay(tmp_path)
    src_manifest = resolve_manifest(result["manifest"])
    dst_manifest = copy_artifact_for_mutation(src_manifest, tmp_path / "sell_mutated")
    manifest = json.loads(dst_manifest.read_text(encoding="utf-8"))
    snapshots_path = Path(manifest["artifacts"]["snapshots"])
    snapshots = pd.read_csv(snapshots_path)
    sold = snapshots[
        (snapshots["date"].astype(str) == "2026-05-06")
        & (snapshots["instrument"].astype(str) == "TW2467")
    ].copy()
    assert len(sold) == 1
    sold.loc[:, "date"] = "2026-05-07"
    snapshots = pd.concat([snapshots, sold], ignore_index=True)
    snapshots.to_csv(snapshots_path, index=False)
    validation = run_validate(dst_manifest, check=False)
    checks = check_statuses(validation)
    assert validation["ok"] is False
    assert checks["sell_action_removed_from_execution_snapshot"] == "fail"


def test_validator_rejects_daily_nav_holding_count_snapshot_mismatch(tmp_path: Path) -> None:
    result = run_replay(tmp_path)
    src_manifest = resolve_manifest(result["manifest"])
    dst_manifest = copy_artifact_for_mutation(src_manifest, tmp_path / "count_mutated")
    manifest = json.loads(dst_manifest.read_text(encoding="utf-8"))
    snapshots_path = Path(manifest["artifacts"]["snapshots"])
    snapshots = pd.read_csv(snapshots_path)
    snapshots = snapshots[~(
        (snapshots["date"].astype(str) == "2026-05-07")
        & (snapshots["instrument"].astype(str) == "TW2337")
    )]
    snapshots.to_csv(snapshots_path, index=False)
    validation = run_validate(dst_manifest, check=False)
    checks = check_statuses(validation)
    assert validation["ok"] is False
    assert checks["daily_nav_holding_count_matches_snapshots"] == "fail"


def test_validator_rejects_parity_claim(tmp_path: Path) -> None:
    result = run_replay(tmp_path)
    src_manifest = resolve_manifest(result["manifest"])
    dst_manifest = copy_artifact_for_mutation(src_manifest, tmp_path / "mutated")
    manifest = json.loads(dst_manifest.read_text(encoding="utf-8"))
    manifest["parity_status"] = "pass"
    manifest["not_d3_parity_evidence"] = False
    dst_manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    validation = run_validate(dst_manifest, check=False)
    assert validation["ok"] is False
    checks = {row["name"]: row for row in validation["checks"]}
    assert checks["not_d3_parity_evidence"]["status"] == "fail"
    assert checks["parity_not_claimed"]["status"] == "fail"
