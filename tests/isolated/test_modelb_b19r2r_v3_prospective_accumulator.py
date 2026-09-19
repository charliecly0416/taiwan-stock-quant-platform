from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from argparse import Namespace
from datetime import date, timedelta
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import build_modelb_b19r2r_v3_prospective_accumulator as ledger  # noqa: E402
import validate_modelb_b19r2r_v3_prospective_accumulator as validator  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture
def case(tmp_path, monkeypatch):
    isolated = tmp_path / "isolated"
    out = isolated / "run"
    monkeypatch.setattr(ledger, "ISOLATED_ROOT", isolated)
    monkeypatch.setattr(ledger, "PROTECTED", ())
    asof = "2026-09-16"
    source_run = "source-20260916"
    cutoff = "2026-09-16T14:00:00+00:00"
    available = "2026-09-16T13:59:00+00:00"
    symbols = [f"TW{i:04d}" for i in range(1, 51)]
    model_a = tmp_path / "model_a.csv"
    features = tmp_path / "features.csv"
    model_b = tmp_path / "model_b.csv"
    write_csv(model_a, [{"date": asof, "instrument": symbol, "rank": index} for index, symbol in enumerate(symbols, 1)])
    columns = [f"f{i:02d}" for i in range(78)]
    write_csv(features, [
        {"date": asof, "instrument": symbol, **{column: index + offset / 100 for offset, column in enumerate(columns)}}
        for index, symbol in enumerate(symbols, 1)
    ])
    write_csv(model_b, [
        {"date": asof, "instrument": symbol, "rank": index, "model_b_score": 51 - index}
        for index, symbol in enumerate(symbols, 1)
    ])
    manifests = []
    for name, artifact in (("a", model_a), ("f", features), ("b", model_b)):
        path = tmp_path / f"{name}.json"
        payload = {
            "asof": asof,
            "source_run_id": source_run,
            "decision_cutoff": cutoff,
            "available_at": available,
            "pit_status": "PASS",
            "artifact_sha256": digest(artifact),
            "production_allowed": False,
        }
        if name == "f":
            payload["feature_columns"] = columns
        if name == "a":
            payload["model_id"] = ledger.MODEL_A_ID
        if name == "b":
            payload.update({
                "model_id": ledger.MODEL_ID,
                "model_sha256": ledger.MODEL_SHA256,
                "candidate_id": ledger.CANDIDATE_ID,
                "feature_count": ledger.FEATURE_COUNT,
            })
        write_json(path, payload)
        manifests.append(path)
    calendar = tmp_path / "day.txt"
    full_calendar = [
        "2026-09-16", "2026-09-17", "2026-09-18", "2026-09-21", "2026-09-22", "2026-09-23",
        "2026-09-24", "2026-09-25", "2026-09-28", "2026-09-29", "2026-09-30",
    ]
    calendar.write_text(full_calendar[0] + "\n", encoding="utf-8")
    args = Namespace(
        out=str(out), asof=asof, model_a=str(model_a), model_a_manifest=str(manifests[0]),
        features=str(features), features_manifest=str(manifests[1]), model_b=str(model_b),
        model_b_manifest=str(manifests[2]),
        calendar=str(calendar),
    )
    return {
        "out": out, "asof": asof, "symbols": symbols, "args": args, "model_a": model_a,
        "features": features, "model_b": model_b, "manifests": manifests, "calendar": calendar,
        "full_calendar": full_calendar,
    }


def make_prices(case, *, missing_close: bool = False):
    case["calendar"].write_text("\n".join(case["full_calendar"][:2]) + "\n", encoding="utf-8")
    path = case["out"].parent / "prices.csv"
    rows = []
    for symbol in case["symbols"]:
        row = {"instrument": symbol, "execution_date": "2026-09-17", "next_open": 100.0, "next_close": 101.0}
        if missing_close:
            row["next_close"] = ""
        rows.append(row)
    write_csv(path, rows)
    manifest = case["out"].parent / "prices.json"
    write_json(manifest, {
        "artifact_sha256": digest(path), "execution_date": "2026-09-17",
        "available_at": "2026-09-17T10:00:00+00:00", "source_run_id": "prices-20260917",
    })
    return Namespace(out=str(case["out"]), asof=case["asof"], prices=str(path), prices_manifest=str(manifest), calendar=str(case["calendar"]))


def make_labels(case, *, extend_calendar: bool = True):
    if extend_calendar:
        case["calendar"].write_text("\n".join(case["full_calendar"]) + "\n", encoding="utf-8")
    path = case["out"].parent / "labels.csv"
    write_csv(path, [{"instrument": symbol, "return_t10": index / 1000} for index, symbol in enumerate(case["symbols"])])
    manifest = case["out"].parent / "labels.json"
    write_json(manifest, {
        "artifact_sha256": digest(path), "label_date": "2026-09-30",
        "available_at": "2026-09-30T10:00:00+00:00", "source_run_id": "labels-20260930",
    })
    return Namespace(out=str(case["out"]), asof=case["asof"], labels=str(path), labels_manifest=str(manifest), calendar=str(case["calendar"]))


def test_capture_is_append_only_and_identical_retry_is_idempotent(case):
    first = ledger.capture(case["args"])
    before = (case["out"] / "events.jsonl").read_bytes()
    second = ledger.capture(case["args"])
    assert first == second
    assert (case["out"] / "events.jsonl").read_bytes() == before
    assert len(ledger.load_events(case["out"] / "events.jsonl")) == 1


def test_same_day_different_hash_is_rejected(case):
    ledger.capture(case["args"])
    rows = ledger.read_csv(case["model_b"])
    rows[0]["model_b_score"] = "999"
    write_csv(case["model_b"], rows)
    manifest = ledger.read_json(case["manifests"][2])
    manifest["artifact_sha256"] = digest(case["model_b"])
    write_json(case["manifests"][2], manifest)
    with pytest.raises(ledger.ContractError) as captured:
        ledger.capture(case["args"])
    assert captured.value.code == "B19V3_E_CONFLICTING_EVENT"


def test_missing_exact50_is_rejected(case):
    rows = ledger.read_csv(case["model_a"])[:-1]
    write_csv(case["model_a"], rows)
    manifest = ledger.read_json(case["manifests"][0])
    manifest["artifact_sha256"] = digest(case["model_a"])
    write_json(case["manifests"][0], manifest)
    with pytest.raises(ledger.ContractError) as captured:
        ledger.capture(case["args"])
    assert captured.value.code == "B19V3_E_EXACT50"


def test_incomplete_78f_is_rejected(case):
    manifest = ledger.read_json(case["manifests"][1])
    manifest["feature_columns"] = manifest["feature_columns"][:-1]
    write_json(case["manifests"][1], manifest)
    with pytest.raises(ledger.ContractError) as captured:
        ledger.capture(case["args"])
    assert captured.value.code == "B19V3_E_78F_DECLARATION"


@pytest.mark.parametrize("field", ["decision_cutoff", "available_at", "pit_status"])
def test_missing_pit_or_cutoff_is_rejected(case, field):
    manifest = ledger.read_json(case["manifests"][1])
    manifest.pop(field)
    write_json(case["manifests"][1], manifest)
    with pytest.raises(ledger.ContractError) as captured:
        ledger.capture(case["args"])
    assert captured.value.code in {"B19V3_E_CUTOFF_BINDING", "B19V3_E_AVAILABLE_AT", "B19V3_E_PIT_STATUS"}


def test_future_label_field_at_capture_is_rejected(case):
    rows = ledger.read_csv(case["model_b"])
    for row in rows:
        row["future_label"] = "0.1"
    write_csv(case["model_b"], rows)
    manifest = ledger.read_json(case["manifests"][2])
    manifest["artifact_sha256"] = digest(case["model_b"])
    write_json(case["manifests"][2], manifest)
    with pytest.raises(ledger.ContractError) as captured:
        ledger.capture(case["args"])
    assert captured.value.code == "B19V3_E_FUTURE_FIELD_AT_CAPTURE"


def test_capture_before_final_model_freeze_is_rejected(case):
    for path in case["manifests"]:
        manifest = ledger.read_json(path)
        manifest["decision_cutoff"] = "2026-09-16T13:15:59+00:00"
        manifest["available_at"] = "2026-09-16T13:15:58+00:00"
        write_json(path, manifest)
    with pytest.raises(ledger.ContractError) as captured:
        ledger.capture(case["args"])
    assert captured.value.code == "B19V3_E_BEFORE_FINAL_MODEL_FREEZE"


def test_model_a_identity_is_frozen(case):
    manifest = ledger.read_json(case["manifests"][0])
    manifest["model_id"] = "another_model"
    write_json(case["manifests"][0], manifest)
    with pytest.raises(ledger.ContractError) as captured:
        ledger.capture(case["args"])
    assert captured.value.code == "B19V3_E_MODELA_IDENTITY"


def test_tw7769_cannot_enter_exact50(case):
    rows = ledger.read_csv(case["model_a"])
    rows[-1]["instrument"] = "TW7769"
    write_csv(case["model_a"], rows)
    manifest = ledger.read_json(case["manifests"][0])
    manifest["artifact_sha256"] = digest(case["model_a"])
    write_json(case["manifests"][0], manifest)
    with pytest.raises(ledger.ContractError) as captured:
        ledger.capture(case["args"])
    assert captured.value.code == "B19V3_E_TW7769_EXCLUDED"


def test_production_boundary_and_output_escape(case, tmp_path):
    manifest = ledger.read_json(case["manifests"][0])
    manifest["production_allowed"] = True
    write_json(case["manifests"][0], manifest)
    with pytest.raises(ledger.ContractError) as captured:
        ledger.capture(case["args"])
    assert captured.value.code == "B19V3_E_PRODUCTION_BOUNDARY"
    case["args"].out = str(tmp_path / "outside")
    with pytest.raises(ledger.ContractError) as captured:
        ledger.capture(case["args"])
    assert captured.value.code == "B19V3_E_OUTPUT_ESCAPE"


def test_missing_next_open_or_close_is_rejected(case):
    ledger.capture(case["args"])
    with pytest.raises(ledger.ContractError) as captured:
        ledger.settle_execution(make_prices(case, missing_close=True))
    assert captured.value.code == "B19V3_E_NEXT_CLOSE"


def test_t10_before_maturity_is_rejected(case):
    ledger.capture(case["args"])
    ledger.settle_execution(make_prices(case))
    with pytest.raises(ledger.ContractError) as captured:
        ledger.mature_label(make_labels(case, extend_calendar=False))
    assert captured.value.code == "B19V3_E_LABEL_NOT_MATURE"


def test_settlement_requires_calendar_strictly_extend_snapshot(case):
    ledger.capture(case["args"])
    args = make_prices(case)
    case["calendar"].write_text("2026-09-16\n", encoding="utf-8")
    with pytest.raises(ledger.ContractError) as captured:
        ledger.settle_execution(args)
    assert captured.value.code == "B19V3_E_CALENDAR_NOT_STRICT_EXTENSION"


def test_complete_lifecycle_seals_outcomes_and_validates(case):
    ledger.capture(case["args"])
    execution = ledger.settle_execution(make_prices(case))
    label = ledger.mature_label(make_labels(case))
    assert "prices" not in execution and "labels" not in label
    assert validator.validate_accumulator(case["out"])["status"] == "PASS"
    sealed = case["out"] / "sealed_outcomes"
    assert os.stat(sealed).st_mode & 0o777 == 0o700
    assert all(os.stat(path).st_mode & 0o777 == 0o600 for path in sealed.glob("*.json"))
    snapshots = case["out"] / "calendar_snapshots"
    assert all(os.stat(path).st_mode & 0o777 == 0o444 for path in snapshots.glob("*.txt"))


def test_event_chain_tamper_is_detected(case):
    ledger.capture(case["args"])
    path = case["out"] / "events.jsonl"
    event = json.loads(path.read_text())
    event["asof"] = "2026-09-17"
    path.write_text(json.dumps(event) + "\n", encoding="utf-8")
    with pytest.raises(ledger.ContractError) as captured:
        ledger.load_events(path)
    assert captured.value.code == "B19V3_E_LEDGER_CHAIN"


def test_thirty_nonconsecutive_captures_do_not_open_v3_window(tmp_path, monkeypatch):
    isolated = tmp_path / "isolated"
    out = isolated / "run"
    out.mkdir(parents=True)
    monkeypatch.setattr(ledger, "ISOLATED_ROOT", isolated)
    days = [(date(2026, 1, 1) + timedelta(days=index)).isoformat() for index in range(60)]
    calendar = out / "calendar_snapshots" / "calendar.txt"
    calendar.parent.mkdir()
    calendar.write_text("\n".join(days) + "\n", encoding="utf-8")
    os.chmod(calendar, 0o444)
    events = []
    for asof in days[::2]:
        event, changed = ledger.append_locked(out, {
            "schema_version": ledger.SCHEMA,
            "event_type": "SIGNAL_CAPTURED",
            "asof": asof,
            "created_at": "2026-01-01T00:00:00+00:00",
            "trading_calendar": str(calendar),
            "trading_calendar_sha256": digest(calendar),
            "production_allowed": False,
        }, events)
        assert changed
        events.append(event)
    ledger.materialize(out)
    summary = ledger.read_json(out / "summary.json")
    assert summary["v3_captured_day_count"] == 30
    assert summary["v3_longest_consecutive_capture_days"] == 1
    assert summary["v3_window_ready"] is False


def test_expanding_calendar_snapshots_accumulate_consecutive_days(tmp_path, monkeypatch):
    isolated = tmp_path / "isolated"
    out = isolated / "run"
    out.mkdir(parents=True)
    monkeypatch.setattr(ledger, "ISOLATED_ROOT", isolated)
    source = tmp_path / "source_calendar.txt"
    events = []
    for days in (("2026-09-16",), ("2026-09-16", "2026-09-17")):
        source.write_text("\n".join(days) + "\n", encoding="utf-8")
        snapshot = ledger.snapshot_calendar(out, source)
        event, _ = ledger.append_locked(out, {
            "schema_version": ledger.SCHEMA,
            "event_type": "SIGNAL_CAPTURED",
            "asof": days[-1],
            "created_at": "2026-09-17T00:00:00+00:00",
            "trading_calendar": str(snapshot),
            "trading_calendar_sha256": digest(snapshot),
            "production_allowed": False,
        }, events)
        events.append(event)
    ledger.materialize(out)
    summary = ledger.read_json(out / "summary.json")
    assert summary["v3_longest_consecutive_capture_days"] == 2
    assert len(summary["trading_calendar_snapshots"]) == 2


def test_calendar_snapshot_tamper_and_mode_are_detected(case):
    ledger.capture(case["args"])
    snapshot = next((case["out"] / "calendar_snapshots").glob("*.txt"))
    os.chmod(snapshot, 0o644)
    with pytest.raises(ledger.ContractError) as captured:
        validator.validate_accumulator(case["out"])
    assert captured.value.code == "B19V3V_E_CALENDAR_SNAPSHOT_MODE"
    snapshot.write_text(snapshot.read_text() + "2026-09-17\n", encoding="utf-8")
    with pytest.raises(ledger.ContractError) as captured:
        ledger.materialize(case["out"])
    assert captured.value.code == "B19V3_E_CALENDAR_CHECKSUM"


def test_calendar_snapshot_fork_is_rejected(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    snapshots = out / "calendar_snapshots"
    snapshots.mkdir()
    left = snapshots / "left.txt"
    right = snapshots / "right.txt"
    left.write_text("2026-09-16\n2026-09-17\n", encoding="utf-8")
    right.write_text("2026-09-16\n2026-09-18\n", encoding="utf-8")
    os.chmod(left, 0o444)
    os.chmod(right, 0o444)
    events = []
    for asof, calendar in (("2026-09-17", left), ("2026-09-18", right)):
        event, _ = ledger.append_locked(out, {
            "schema_version": ledger.SCHEMA, "event_type": "SIGNAL_CAPTURED", "asof": asof,
            "created_at": "2026-09-18T00:00:00+00:00", "trading_calendar": str(calendar),
            "trading_calendar_sha256": digest(calendar), "production_allowed": False,
        }, events)
        events.append(event)
    with pytest.raises(ledger.ContractError) as captured:
        ledger.materialize(out)
    assert captured.value.code == "B19V3_E_CALENDAR_FORK"


def test_validator_recomputes_consecutive_capture_gate(case):
    ledger.capture(case["args"])
    summary_path = case["out"] / "summary.json"
    summary = ledger.read_json(summary_path)
    summary["v3_longest_consecutive_capture_days"] = 30
    summary["v3_window_ready"] = True
    write_json(summary_path, summary)
    with pytest.raises(ledger.ContractError) as captured:
        validator.validate_accumulator(case["out"])
    assert captured.value.code == "B19V3V_E_SUMMARY"


def test_validator_recomputes_mainline_and_capture_counts(case):
    ledger.capture(case["args"])
    summary_path = case["out"] / "summary.json"
    summary = ledger.read_json(summary_path)
    summary["mainline_settled_day_count"] = 10
    summary["mainline_gate_ready"] = True
    summary["v3_captured_day_count"] = 30
    write_json(summary_path, summary)
    with pytest.raises(ledger.ContractError) as captured:
        validator.validate_accumulator(case["out"])
    assert captured.value.code == "B19V3V_E_SUMMARY"


def run_synthetic_readiness(tmp_path, monkeypatch, job):
    audit_parent = tmp_path / "audits"
    out = audit_parent / "case"
    monkeypatch.setattr(ledger, "AUDIT_ROOT", audit_parent / "default")
    calendar = tmp_path / "audit_calendar.txt"
    calendar.write_text("2026-09-16\n", encoding="utf-8")
    jobs = tmp_path / "jobs"
    job_dir = jobs / "daily_tw_stock_auto_update_20260916_20260916T150000Z"
    job_dir.mkdir(parents=True)
    write_json(job_dir / "job.json", job)
    args = Namespace(out=str(out), calendar=str(calendar), jobs_root=str(jobs), start="2026-09-16", end="2026-09-16")
    ledger.readiness_audit(args)
    return list(csv.DictReader((out / "READINESS_BY_DAY.csv").open(encoding="utf-8")))[0]


def test_multiple_loose_runs_and_cutoffs_are_never_readiness_eligible(tmp_path, monkeypatch):
    job = {
        "asof": "2026-09-16",
        "model_signal": ledger.MODEL_A_ID,
        "model_id": ledger.MODEL_ID,
        "model_sha256": ledger.MODEL_SHA256,
        "feature_count": 78,
        "candidate_id": 14,
        "runs": [{"source_acquisition_run_id": "run-a"}, {"source_acquisition_run_id": "run-b"}],
        "cutoffs": [{"decision_cutoff": "2026-09-16T14:00:00+00:00"}, {"decision_cutoff": "2026-09-16T14:01:00+00:00"}],
    }
    row = run_synthetic_readiness(tmp_path, monkeypatch, job)
    assert row["status"] == "NOT_ELIGIBLE"
    assert row["strict_bundle_count"] == "0"
    assert "strict_input_bundle_unproven" in row["reasons"]


def test_bundle_without_pit_or_with_late_availability_is_not_eligible(tmp_path, monkeypatch):
    bundle = {
        "schema_version": "modelb_b19r2r.v3.materialized_input_bundle.v1",
        "asof": "2026-09-16", "source_run_id": "run-a",
        "decision_cutoff": "2026-09-16T14:00:00+00:00",
        "model_a_id": ledger.MODEL_A_ID, "model_id": ledger.MODEL_ID,
        "model_sha256": ledger.MODEL_SHA256, "candidate_id": 14, "feature_count": 78,
        "exact50_count": 50, "tw7769_excluded": True, "production_allowed": False,
        "inputs": [
            {"role": role, "source_run_id": "run-a", "available_at": "2026-09-16T14:01:00+00:00", "artifact_sha256": "a" * 64}
            for role in ("model_a_exact50", "canonical_78f", "candidate14_model_b_scores")
        ],
    }
    row = run_synthetic_readiness(tmp_path, monkeypatch, {"bundle": bundle})
    assert row["status"] == "NOT_ELIGIBLE"
    assert row["strict_pit_binding_proven"] == "False"


def test_bundle_cutoff_before_final_model_freeze_is_not_eligible(tmp_path, monkeypatch):
    bundle = {
        "schema_version": "modelb_b19r2r.v3.materialized_input_bundle.v1",
        "asof": "2026-09-16", "source_run_id": "run-a",
        "decision_cutoff": "2026-09-16T13:15:59+00:00",
        "model_a_id": ledger.MODEL_A_ID, "model_id": ledger.MODEL_ID,
        "model_sha256": ledger.MODEL_SHA256, "candidate_id": 14, "feature_count": 78,
        "exact50_count": 50, "tw7769_excluded": True, "production_allowed": False,
        "inputs": [
            {
                "role": role, "source_run_id": "run-a", "pit_status": "PASS",
                "available_at": "2026-09-16T13:15:58+00:00", "artifact_sha256": "a" * 64,
            }
            for role in ("model_a_exact50", "canonical_78f", "candidate14_model_b_scores")
        ],
    }
    row = run_synthetic_readiness(tmp_path, monkeypatch, {"bundle": bundle})
    assert row["status"] == "NOT_ELIGIBLE"
    assert row["strict_bundle_count"] == "0"
    assert row["strict_bundle_after_model_freeze"] == "False"
