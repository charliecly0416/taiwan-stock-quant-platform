from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import run_daily_tw_stock_auto_update as daily  # noqa: E402


def test_shadow_not_called_before_20_valid_days(tmp_path):
    accumulator = tmp_path / "accumulator"
    accumulator.mkdir()
    (accumulator / "warmup_readiness.json").write_text(json.dumps({"valid_input_days": 19, "can_shadow_score": False}), encoding="utf-8")
    calls = []
    result = daily.run_mbcds35_prospective_shadow(
        asof="2026-09-08", job_id="job", job_dir=tmp_path, enabled=True,
        accumulator_dir=str(accumulator), inventory_path=str(tmp_path / "missing.csv"),
        source_ledger=tmp_path / "missing.json", command_runner=lambda *args, **kwargs: calls.append(args),
    )
    assert result["status"] == "WAITING_FOR_WARMUP"
    assert calls == []


def test_feature_failure_is_nonblocking_for_model_a(tmp_path):
    accumulator = tmp_path / "accumulator"
    accumulator.mkdir()
    (accumulator / "warmup_readiness.json").write_text(json.dumps({"valid_input_days": 20, "can_shadow_score": True}), encoding="utf-8")
    model_a_dir = tmp_path / "model_a"
    model_a_dir.mkdir()
    model_a = model_a_dir / "raw_scores.csv"
    model_a.write_text("date,instrument,full_qlib_rank,raw_score\n", encoding="utf-8")
    (model_a_dir / "manifest.json").write_text("{}", encoding="utf-8")
    inventory = tmp_path / "inventory.csv"
    with inventory.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["required_date", "path"])
        writer.writeheader()
        writer.writerow({"required_date": "2026-09-08", "path": str(model_a)})
    source = tmp_path / "source.json"
    source.write_text("{}", encoding="utf-8")
    result = daily.run_mbcds35_prospective_shadow(
        asof="2026-09-08", job_id="job", job_dir=tmp_path, enabled=True,
        accumulator_dir=str(accumulator), inventory_path=str(inventory), source_ledger=source,
        command_runner=lambda *args, **kwargs: {"ok": False, "returncode": 2},
    )
    assert result["status"] == "BLOCKED_FEATURES_NONBLOCKING"
    assert result["ok"] is True
    assert result["model_a_non_blocking"] is True


def test_old_pending_settlement_runs_before_today_feature_failure(tmp_path, monkeypatch):
    accumulator = tmp_path / "accumulator"
    accumulator.mkdir()
    (accumulator / "warmup_readiness.json").write_text(json.dumps({"valid_input_days": 20, "can_shadow_score": True}), encoding="utf-8")
    model_a_dir = tmp_path / "model_a"
    model_a_dir.mkdir()
    model_a = model_a_dir / "raw_scores.csv"
    model_a.write_text("date,instrument,full_qlib_rank,raw_score\n", encoding="utf-8")
    (model_a_dir / "manifest.json").write_text("{}", encoding="utf-8")
    inventory = tmp_path / "inventory.csv"
    inventory.write_text(f"required_date,path\n2026-09-08,{model_a}\n", encoding="utf-8")
    source = tmp_path / "source.json"
    source.write_text("{}", encoding="utf-8")
    ledger = tmp_path / "prospective"
    ledger.mkdir()
    (ledger / "comparison_summary.json").write_text(json.dumps({"pending_outcome_days": ["2026-09-05"]}), encoding="utf-8")
    (ledger / "events.jsonl").write_text(json.dumps({"event_type": "SIGNAL_REGISTERED", "asof": "2026-09-05", "model_a_signals": str(model_a)}) + "\n", encoding="utf-8")
    monkeypatch.setattr(daily, "MBCDS35_DEFAULT_LEDGER", ledger)
    calls = []
    def runner(command, **kwargs):
        calls.append(command)
        return {"ok": False, "returncode": 2}
    result = daily.run_mbcds35_prospective_shadow(
        asof="2026-09-08", job_id="job", job_dir=tmp_path, enabled=True,
        accumulator_dir=str(accumulator), inventory_path=str(inventory), source_ledger=source,
        command_runner=runner,
    )
    assert result["status"] == "BLOCKED_FEATURES_NONBLOCKING"
    assert result["settlement_attempts"][0]["asof"] == "2026-09-05"
    assert "build_tw_mbcds35_outcome_candidate.py" in calls[0][1]
    assert "build_tw_mbcds2_isolated_feature_input.py" in calls[1][1]


def test_old_pending_settlement_survives_today_scorer_failure(tmp_path, monkeypatch):
    accumulator = tmp_path / "accumulator"
    accumulator.mkdir()
    (accumulator / "warmup_readiness.json").write_text(
        json.dumps({"valid_input_days": 20, "can_shadow_score": True}), encoding="utf-8"
    )
    model_a_dir = tmp_path / "model_a"
    model_a_dir.mkdir()
    model_a = model_a_dir / "raw_scores.csv"
    model_a.write_text("date,instrument,full_qlib_rank,raw_score\n", encoding="utf-8")
    (model_a_dir / "manifest.json").write_text("{}", encoding="utf-8")
    inventory = tmp_path / "inventory.csv"
    inventory.write_text(f"required_date,path\n2026-09-08,{model_a}\n", encoding="utf-8")
    source = tmp_path / "source.json"
    source.write_text("{}", encoding="utf-8")
    ledger = tmp_path / "prospective"
    ledger.mkdir()
    (ledger / "comparison_summary.json").write_text(
        json.dumps({"pending_outcome_days": ["2026-09-05"]}), encoding="utf-8"
    )
    (ledger / "events.jsonl").write_text(
        json.dumps({"event_type": "SIGNAL_REGISTERED", "asof": "2026-09-05", "model_a_signals": str(model_a)}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(daily, "MBCDS35_DEFAULT_LEDGER", ledger)
    calls = []

    def runner(command, **kwargs):
        calls.append(command)
        if "run_tw_mbcds35_compatibility_frozen_scorer.py" in command[1]:
            return {"ok": False, "returncode": 2}
        return {"ok": True, "returncode": 0}

    result = daily.run_mbcds35_prospective_shadow(
        asof="2026-09-08", job_id="job", job_dir=tmp_path, enabled=True,
        accumulator_dir=str(accumulator), inventory_path=str(inventory), source_ledger=source,
        command_runner=runner,
    )
    assert result["status"] == "BLOCKED_SCORER_NONBLOCKING"
    assert result["ok"] is True and result["model_a_non_blocking"] is True
    assert result["settlement_attempts"] == [{"asof": "2026-09-05", "candidate_ready": True, "settled": True}]
    assert "settle-outcome" in calls[1]
