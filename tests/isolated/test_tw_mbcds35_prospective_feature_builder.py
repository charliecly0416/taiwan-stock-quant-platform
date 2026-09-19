from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import build_tw_mbcds2_isolated_feature_input as builder  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_builder_uses_only_explicit_accepted_history_and_bound_source(tmp_path, monkeypatch):
    isolated = tmp_path / "isolated"
    monkeypatch.setattr(builder, "ISOLATED_ROOT", isolated)
    monkeypatch.setattr(builder, "PROTECTED", [])
    dates = pd.bdate_range("2026-01-01", periods=130).strftime("%Y-%m-%d").tolist()
    rank_dates = dates[-20:]
    asof = rank_dates[-1]
    symbols = [f"TW{i:04d}" for i in range(150)]
    accumulator = tmp_path / "accumulator.csv"
    inventory_rows = []
    for day_index, day in enumerate(rank_dates):
        path = tmp_path / f"rank-{day}.csv"
        scores = np.arange(150, 0, -1, dtype=float) + day_index * 0.001
        pd.DataFrame({"date": day, "instrument": symbols, "full_qlib_rank": range(1, 151), "raw_score": scores}).to_csv(path, index=False)
        inventory_rows.append({
            "asof": day, "state": "VALID_DAY_ACCEPTED", "warmup_counted": True,
            "ranking_path": str(path), "source_run_id": "run-1",
            "decision_cutoff": f"{asof}T10:30:00+00:00",
        })
    with accumulator.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(inventory_rows[0]))
        writer.writeheader(); writer.writerows(inventory_rows)
    records = []
    for day_index, day in enumerate(dates):
        for symbol_index, symbol in enumerate(symbols):
            close = 50 + symbol_index * 0.1 + day_index * 0.02 + np.sin(day_index / 5)
            records.append({"date": day, "stock_id": symbol, "open": close - 0.1, "close": close,
                            "Trading_Volume": 100000 + symbol_index * 10 + day_index, "vwap": close - 0.02})
        records.append({"date": day, "stock_id": "TWII", "open": 15000 + day_index,
                        "close": 15000 + day_index + np.sin(day_index / 7), "Trading_Volume": 1, "vwap": 15000 + day_index})
    # Missing data outside Model A top50 is retained in the 150-row frame as
    # a diagnostic, but cannot block the 50x34 scorer input contract.
    next(row for row in records if row["date"] == asof and row["stock_id"] == "TW0149")["close"] = None
    source = tmp_path / "source.json"
    source.write_text(json.dumps({"data": records}), encoding="utf-8")
    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps({"status": "PASS", "asof": asof, "acquisition_run_id": "run-1",
                                  "combined_available_at": f"{asof}T10:00:00+00:00",
                                  "decision_cutoff": f"{asof}T10:30:00+00:00", "artifact_checksums": {str(source): digest(source)}}), encoding="utf-8")
    model_a = Path(inventory_rows[-1]["ranking_path"])
    result = builder.build(asof=asof, model_a=model_a, source_ledger=ledger, accumulator=accumulator,
                           output=isolated / "features", contract=builder.CONTRACT)
    assert result["status"] == "PASS"
    assert result["accepted_rank_history_only"] is True
    assert result["feature_count"] == 34
    assert result["readiness_scope"] == "model_a_top50_50x34"
    assert result["all_universe_diagnostic_blocked_features"]
    assert result["signal_time_regime"] in {"crash", "risk_off", "risk_on", "neutral"}
    regime = json.loads((isolated / "features/signal_time_regime.json").read_text())
    assert regime["regime"] == result["signal_time_regime"]
    assert regime["outcome_fields_consumed"] == []


def test_unaccepted_target_is_blocked(tmp_path, monkeypatch):
    isolated = tmp_path / "isolated"
    monkeypatch.setattr(builder, "ISOLATED_ROOT", isolated)
    accumulator = tmp_path / "accumulator.csv"
    accumulator.write_text("asof,state,warmup_counted,ranking_path\n2026-09-08,VALID_DAY_QUARANTINED,False,x\n", encoding="utf-8")
    with pytest.raises(builder.FeatureBuildError, match="not_bound_to_accepted"):
        builder.load_rank_history(accumulator, "2026-09-08", tmp_path / "x")


def test_source_available_after_cutoff_is_blocked(tmp_path):
    source = tmp_path / "source.json"
    source.write_text(json.dumps({"data": []}), encoding="utf-8")
    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps({
        "status": "PASS", "asof": "2026-09-08", "acquisition_run_id": "run-1",
        "combined_available_at": "2026-09-08T11:00:00+00:00",
        "decision_cutoff": "2026-09-08T10:30:00+00:00",
        "artifact_checksums": {str(source): digest(source)},
    }), encoding="utf-8")
    with pytest.raises(builder.FeatureBuildError, match="source_available_at_after_decision_cutoff"):
        builder.load_bound_market_data(ledger, "2026-09-08")


def test_frozen_training_feature_semantics_are_preserved():
    rising = pd.Series(range(1, 21), dtype=float)
    assert builder.rsi(rising).iloc[-1] == 50.0
    tied = pd.DataFrame({"date": ["2026-09-08"] * 3, "score": [1.0, 1.0, 2.0]})
    percentiles = tied.groupby("date").score.rank(pct=True, method="average", ascending=True)
    assert percentiles.tolist() == pytest.approx([0.5, 0.5, 1.0])
