from __future__ import annotations

import csv
import hashlib
import json
import sys
from argparse import Namespace
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import build_tw_mbcds35_prospective_oos_ledger as ledger  # noqa: E402
import tw_mbcds35_signal_time_regime as regime_contract  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


@pytest.fixture
def case(tmp_path, monkeypatch):
    isolated = tmp_path / "isolated"
    out = isolated / "ledger"
    monkeypatch.setattr(ledger, "ISOLATED_ROOT", isolated)
    monkeypatch.setattr(ledger, "PROTECTED", ())
    asof = "2026-09-07"
    cutoff = "2026-09-07T10:30:00+00:00"
    source_run = "acquisition-20260907"
    model_a = tmp_path / "model_a.csv"
    a_rows = [
        {"date": asof, "instrument": f"TW{i:04d}", "full_qlib_rank": i, "raw_score": 151 - i}
        for i in range(1, 151)
    ]
    write_csv(model_a, a_rows)
    model_b = tmp_path / "model_b.csv"
    b_rows = []
    for i in range(1, 51):
        qlib_percentile = (51 - i) / 50
        model_b_percentile = i / 50
        buy_score = 0.7 * qlib_percentile + 0.3 * model_b_percentile
        b_rows.append({
            "date": asof, "instrument": f"TW{i:04d}", "score_rank": i,
            "buy_score": buy_score, "full_qlib_rank": i, "qlib_score_raw": 151 - i,
            "model_b_raw_score": i, "qlib_percentile": qlib_percentile,
            "model_b_percentile": model_b_percentile,
        })
    write_csv(model_b, b_rows)
    a_manifest = tmp_path / "a_manifest.json"
    b_manifest = tmp_path / "b_manifest.json"
    regime_path = tmp_path / "signal_time_regime.json"
    write_json(regime_path, {
        "schema_version": "mbcds35.signal_time_regime.v1", "asof": asof,
        "decision_cutoff": cutoff, "source_available_at": "2026-09-07T10:00:00+00:00",
        "source_run_id": source_run, "regime": "risk_on",
        "feature_values": {"TWII_close_vs_MA60": 0.01, "TWII_ret20": 0.02, "market_drawdown60": -0.01},
        "regime_contract_sha256": regime_contract.sha256(regime_contract.DEFAULT_CONTRACT),
        "signal_time_only": True, "outcome_fields_consumed": [],
    })
    common = {"asof": asof, "source_run_id": source_run, "decision_cutoff": cutoff, "production_allowed": False}
    write_json(a_manifest, {**common, "model_id": ledger.MODEL_A_ID, "artifact_sha256": digest(model_a)})
    write_json(b_manifest, {
        **common, "model_id": ledger.MODEL_B_ID, "artifact_sha256": digest(model_b),
        "training_performed": False, "candidate_id": ledger.MODEL_B_CANDIDATE_ID,
        "model_family": "lightgbm_lambdarank", "blend_alpha": 0.7,
        "preserve_scope": "top50_only", "feature_count": 34,
        "model_sha256": ledger.MODEL_B_ARTIFACT_SHA256,
        "contract_sha256": ledger.MODEL_B_CONTRACT_SHA256,
        "training_medians_sha256": ledger.MODEL_B_MEDIANS_SHA256,
        "candidate_aliases": [ledger.MODEL_B_CANDIDATE_ALIAS],
        "candidate_identity_policy": "canonical_id_plus_non_binding_alias; frozen artifact bytes unchanged",
        "percentile_direction": "higher_score_is_better",
        "percentile_tie_method": "first_after_qlib_rank_then_symbol",
        "missing_rule": "fail_closed_no_fill",
        "model_a_signals_sha256": digest(model_a),
        "signal_time_regime": "risk_on", "signal_time_regime_artifact": str(regime_path),
        "signal_time_regime_artifact_sha256": digest(regime_path),
        "signal_time_regime_contract_sha256": regime_contract.sha256(regime_contract.DEFAULT_CONTRACT),
    })
    valid = tmp_path / "accumulator.csv"
    valid_rows = [{
        "asof": f"2026-08-{day:02d}", "state": "VALID_DAY_ACCEPTED", "warmup_counted": True,
        "available_at": "2026-08-01T10:00:00+00:00", "decision_cutoff": cutoff,
        "source_run_id": f"warmup-{day}", "ranking_path": "unused",
    } for day in range(1, 20)]
    valid_rows.append({
        "asof": asof, "state": "VALID_DAY_ACCEPTED", "warmup_counted": True,
        "available_at": "2026-09-07T10:00:00+00:00", "decision_cutoff": cutoff,
        "source_run_id": source_run, "ranking_path": str(model_a),
    })
    write_csv(valid, valid_rows)
    calendar = tmp_path / "day.txt"
    calendar.write_text("2026-09-07\n2026-09-08\n2026-09-09\n2026-09-10\n", encoding="utf-8")
    signal_args = Namespace(
        out=str(out), asof=asof, valid_day_inventory=str(valid),
        model_a_signals=str(model_a), model_a_manifest=str(a_manifest),
        model_b_signals=str(model_b), model_b_manifest=str(b_manifest),
    )
    return {
        "out": out, "asof": asof, "signal_args": signal_args, "valid": valid,
        "model_a": model_a, "model_b": model_b, "a_manifest": a_manifest, "b_manifest": b_manifest,
        "calendar": calendar,
    }


def make_outcome(case, *, available_at="2026-09-09T10:00:00+00:00"):
    # A selects TW0001..10; A+B selects TW0050..41.
    symbols = [f"TW{i:04d}" for i in range(1, 151)]
    path = case["out"].parent / "outcomes.csv"
    rows = []
    for symbol in symbols:
        number = int(symbol[2:])
        exit_open = 103.0 if number >= 41 else 101.0
        rows.append({
            "instrument": symbol, "entry_date": "2026-09-08", "entry_open": 100.0,
            "exit_date": "2026-09-09", "exit_open": exit_open,
        })
    write_csv(path, rows)
    manifest = case["out"].parent / "outcome_manifest.json"
    write_json(manifest, {
        "available_at": available_at, "entry_date": "2026-09-08", "exit_date": "2026-09-09",
        "artifact_sha256": digest(path), "trading_calendar_sha256": digest(case["calendar"]),
        "source_run_id": "outcome-acquisition-20260909", "source_asof": "2026-09-09",
    })
    return Namespace(out=str(case["out"]), asof=case["asof"], outcomes=str(path),
                     outcome_manifest=str(manifest), trading_calendar=str(case["calendar"]))


def test_signal_and_future_outcome_are_separate_events(case):
    signal = ledger.record_signal(case["signal_args"])
    assert signal["signal_time_contains_outcome"] is False
    assert signal["model_a_target"] == [f"TW{i:04d}" for i in range(1, 11)]
    assert signal["model_ab_target"] == [f"TW{i:04d}" for i in range(1, 11)]
    assert signal["valid_input_day_count"] == 20
    assert signal["signal_time_regime"] == "risk_on"
    before = json.loads((case["out"] / "comparison_summary.json").read_text())
    assert before["settled_oos_days"] == 0
    assert before["pending_outcome_days"] == [case["asof"]]

    outcome = ledger.settle(make_outcome(case))
    assert outcome["complete_universe_size"] == 150
    after = json.loads((case["out"] / "comparison_summary.json").read_text())
    assert after["settled_oos_days"] == 1
    assert after["model_ab_cumulative_net_return"] == after["model_a_cumulative_net_return"]
    assert after["production_baseline_switch_allowed"] is False
    assert after["regime_stability_ready"] is True
    assert after["regime_stability"]["risk_on"]["paired_days"] == 1
    assert len(ledger.load_events(case["out"] / "events.jsonl")) == 2


def test_duplicate_signal_rejected_without_append(case):
    ledger.record_signal(case["signal_args"])
    before = (case["out"] / "events.jsonl").read_bytes()
    with pytest.raises(ledger.ContractError) as captured:
        ledger.record_signal(case["signal_args"])
    assert captured.value.code == "MBCDS35_E_DUPLICATE_EVENT"
    assert (case["out"] / "events.jsonl").read_bytes() == before


def test_quarantined_day_cannot_register(case):
    rows = list(csv.DictReader(case["valid"].open(encoding="utf-8")))
    rows[-1]["state"] = "VALID_DAY_QUARANTINED"
    write_csv(case["valid"], rows)
    with pytest.raises(ledger.ContractError) as captured:
        ledger.record_signal(case["signal_args"])
    assert captured.value.code == "MBCDS35_E_DAY_NOT_ACCEPTED"


def test_model_b_must_be_exact_same_model_a_top50(case):
    rows = list(csv.DictReader(case["model_b"].open(encoding="utf-8")))
    rows[-1]["instrument"] = "TW0051"
    write_csv(case["model_b"], rows)
    payload = json.loads(case["b_manifest"].read_text())
    payload["artifact_sha256"] = digest(case["model_b"])
    write_json(case["b_manifest"], payload)
    with pytest.raises(ledger.ContractError) as captured:
        ledger.record_signal(case["signal_args"])
    assert captured.value.code == "MBCDS35_E_MODELB_TOP50"


def test_same_run_mismatch_is_fail_closed(case):
    payload = json.loads(case["b_manifest"].read_text())
    payload["source_run_id"] = "other-run"
    write_json(case["b_manifest"], payload)
    with pytest.raises(ledger.ContractError) as captured:
        ledger.record_signal(case["signal_args"])
    assert captured.value.code == "MBCDS35_E_SAME_RUN"


def test_outcome_cannot_be_available_at_signal_cutoff(case):
    ledger.record_signal(case["signal_args"])
    args = make_outcome(case, available_at="2026-09-07T10:30:00+00:00")
    with pytest.raises(ledger.ContractError) as captured:
        ledger.settle(args)
    assert captured.value.code == "MBCDS35_E_OUTCOME_NOT_PROSPECTIVE"


def test_outcome_regime_injection_is_rejected_and_cannot_override_signal(case):
    ledger.record_signal(case["signal_args"])
    args = make_outcome(case)
    manifest = json.loads(Path(args.outcome_manifest).read_text())
    manifest["regime"] = "crash"
    write_json(Path(args.outcome_manifest), manifest)
    with pytest.raises(ledger.ContractError) as captured:
        ledger.settle(args)
    assert captured.value.code == "MBCDS35_E_OUTCOME_REGIME_FORBIDDEN"
    events = ledger.load_events(case["out"] / "events.jsonl")
    assert len(events) == 1 and events[0]["signal_time_regime"] == "risk_on"


def test_nested_outcome_regime_injection_is_rejected(case):
    ledger.record_signal(case["signal_args"])
    args = make_outcome(case)
    manifest = json.loads(Path(args.outcome_manifest).read_text())
    manifest["metadata"] = {"market_regime": "crash"}
    write_json(Path(args.outcome_manifest), manifest)
    with pytest.raises(ledger.ContractError) as captured:
        ledger.settle(args)
    assert captured.value.code == "MBCDS35_E_OUTCOME_REGIME_FORBIDDEN"


def test_outcome_csv_regime_injection_is_rejected(case):
    ledger.record_signal(case["signal_args"])
    args = make_outcome(case)
    rows = list(csv.DictReader(Path(args.outcomes).open(encoding="utf-8")))
    for row in rows:
        row["regime"] = "crash"
    write_csv(Path(args.outcomes), rows)
    manifest = json.loads(Path(args.outcome_manifest).read_text())
    manifest["artifact_sha256"] = digest(Path(args.outcomes))
    write_json(Path(args.outcome_manifest), manifest)
    with pytest.raises(ledger.ContractError) as captured:
        ledger.settle(args)
    assert captured.value.code == "MBCDS35_E_OUTCOME_REGIME_FORBIDDEN"


def test_signal_time_regime_checksum_drift_is_rejected(case):
    manifest = json.loads(case["b_manifest"].read_text())
    regime_path = Path(manifest["signal_time_regime_artifact"])
    regime_path.write_bytes(regime_path.read_bytes() + b" ")
    with pytest.raises(ledger.ContractError) as captured:
        ledger.record_signal(case["signal_args"])
    assert captured.value.code == "MBCDS35_E_REGIME_ARTIFACT_CHECKSUM"


def test_identical_settlement_retry_is_idempotent(case):
    ledger.record_signal(case["signal_args"])
    args = make_outcome(case)
    first = ledger.settle(args)
    before = (case["out"] / "events.jsonl").read_bytes()
    second = ledger.settle(args)
    assert second["event_hash"] == first["event_hash"]
    assert (case["out"] / "events.jsonl").read_bytes() == before


def test_conflicting_settlement_retry_is_rejected(case):
    ledger.record_signal(case["signal_args"])
    args = make_outcome(case)
    ledger.settle(args)
    rows = list(csv.DictReader(Path(args.outcomes).open(encoding="utf-8")))
    rows[0]["exit_open"] = "104"
    write_csv(Path(args.outcomes), rows)
    manifest = json.loads(Path(args.outcome_manifest).read_text())
    manifest["artifact_sha256"] = digest(Path(args.outcomes))
    write_json(Path(args.outcome_manifest), manifest)
    with pytest.raises(ledger.ContractError) as captured:
        ledger.settle(args)
    assert captured.value.code == "MBCDS35_E_CONFLICTING_EVENT"


def test_missing_open_stays_pending(case):
    ledger.record_signal(case["signal_args"])
    args = make_outcome(case)
    rows = list(csv.DictReader(Path(args.outcomes).open(encoding="utf-8")))
    rows[0]["entry_open"] = ""
    write_csv(Path(args.outcomes), rows)
    manifest = json.loads(Path(args.outcome_manifest).read_text())
    manifest["artifact_sha256"] = digest(Path(args.outcomes))
    write_json(Path(args.outcome_manifest), manifest)
    with pytest.raises(ledger.ContractError) as captured:
        ledger.settle(args)
    assert captured.value.code == "MBCDS35_E_OUTCOME_PENDING_OPEN"
    assert json.loads((case["out"] / "comparison_summary.json").read_text())["pending_outcome_days"] == [case["asof"]]


def test_calendar_weekend_is_not_accepted_as_execution_day(case):
    ledger.record_signal(case["signal_args"])
    args = make_outcome(case)
    case["calendar"].write_text("2026-09-07\n2026-09-09\n2026-09-10\n", encoding="utf-8")
    manifest = json.loads(Path(args.outcome_manifest).read_text())
    manifest["trading_calendar_sha256"] = digest(case["calendar"])
    write_json(Path(args.outcome_manifest), manifest)
    with pytest.raises(ledger.ContractError) as captured:
        ledger.settle(args)
    assert captured.value.code == "MBCDS35_E_NEXT_TRADING_DAY_BINDING"


def test_tampered_event_chain_is_rejected(case):
    ledger.record_signal(case["signal_args"])
    path = case["out"] / "events.jsonl"
    event = json.loads(path.read_text())
    event["source_run_id"] = "tampered"
    path.write_text(json.dumps(event) + "\n", encoding="utf-8")
    with pytest.raises(ledger.ContractError) as captured:
        ledger.load_events(path)
    assert captured.value.code == "MBCDS35_E_LEDGER_CHAIN"


def test_output_escape_rejected(case, tmp_path):
    case["signal_args"].out = str(tmp_path / "outside")
    with pytest.raises(ledger.ContractError) as captured:
        ledger.record_signal(case["signal_args"])
    assert captured.value.code == "MBCDS35_E_OUTPUT_ESCAPE"


def test_paired_oos_threshold_boundaries():
    assert ledger.evidence_status_for(59) == "SHADOW_DIAGNOSTIC_READY"
    assert ledger.evidence_status_for(60) == "OOS_REVIEWABLE"
    assert ledger.evidence_status_for(119) == "OOS_REVIEWABLE"
    assert ledger.evidence_status_for(120, 0.001, True) == "BASELINE_REVIEW_ELIGIBLE"
    assert ledger.evidence_status_for(120, -0.001, True) == "NO_STABLE_INCREMENTAL_BENEFIT"


def test_forged_blend_is_rejected(case):
    rows = list(csv.DictReader(case["model_b"].open(encoding="utf-8")))
    rows[0]["buy_score"] = str(float(rows[0]["buy_score"]) + 0.01)
    write_csv(case["model_b"], rows)
    manifest = json.loads(case["b_manifest"].read_text())
    manifest["artifact_sha256"] = digest(case["model_b"])
    write_json(case["b_manifest"], manifest)
    with pytest.raises(ledger.ContractError) as captured:
        ledger.record_signal(case["signal_args"])
    assert captured.value.code == "MBCDS35_E_MODELB_BLEND_RECOMPUTE"
