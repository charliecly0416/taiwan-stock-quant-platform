#!/usr/bin/env python3
"""Replay frozen O4 treatment scores on the current E1 candidate universe."""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import run_modelb_historical_exact_top50_replay as engine

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_o4_same_e1_top50_replay_20260908"
E1 = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_raw_oos_score_rank_2023_2026.csv"
O3 = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o3_row_aligned_treatment_sample/phaseo3_treatment_candidate_sample.csv"
O4 = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_treatment_row_scores.csv"
O4_MODEL = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_treatment_model.pkl"
O4_MANIFEST = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_manifest.json"
START, END = "2026-01-02", "2026-05-07"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({k for row in rows for k in row}) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    before = engine.fingerprints()
    e1 = pd.read_csv(E1, dtype={"instrument": str})
    o3 = pd.read_csv(O3, dtype={"instrument": str}, usecols=["date", "instrument", "sample_complete"])
    o4 = pd.read_csv(O4, dtype={"instrument": str}, usecols=["date", "instrument", "phaseo4_treatment_ltr_score"])
    for frame in (e1, o3, o4):
        frame["date"] = frame["date"].astype(str).str[:10]
        frame["instrument"] = frame["instrument"].astype(str).str.upper()
    e1 = e1[e1.date.between(START, END)].copy()
    o3 = o3[o3.date.between(START, END)].copy()
    o4 = o4[o4.date.between(START, END)].copy()
    if e1.duplicated(["date", "instrument"]).any() or o3.duplicated(["date", "instrument"]).any() or o4.duplicated(["date", "instrument"]).any():
        raise RuntimeError("duplicate date/instrument input key")
    complete = o3.set_index(["date", "instrument"])["sample_complete"].astype(bool)
    merged = e1.merge(o4, on=["date", "instrument"], how="inner", validate="one_to_one")
    merged["sample_complete"] = [bool(complete.get((d, s), False)) for d, s in zip(merged.date, merged.instrument)]
    full_ranks = {}
    signals: list[dict] = []
    coverage: list[dict] = []
    for day in sorted(e1.date.unique()):
        ag = e1[e1.date.eq(day)].copy()
        top = ag[ag.qlib_rank_raw <= 50]
        day = merged[merged.date.eq(day)]
        eligible = day[day.sample_complete & day.phaseo4_treatment_ltr_score.notna()]
        bound = top.merge(eligible[["instrument", "phaseo4_treatment_ltr_score"]], on="instrument", how="inner")
        keys = sorted(bound.instrument.astype(str))
        top_keys = set(top.instrument.astype(str))
        full_ranks[str(day.date.iloc[0]) if not day.empty else str(ag.date.iloc[0])] = {str(r.instrument): int(r.qlib_rank_raw) for r in ag.itertuples()}
        missing = sorted(top_keys - set(keys))
        coverage.append({
            "date": str(ag.date.iloc[0]), "e1_rows": len(ag), "e1_top50_count": len(top),
            "o3_complete_rows": int(merged[merged.date.eq(str(ag.date.iloc[0]))].sample_complete.sum()),
            "bound_rows": len(bound), "missing_symbols": "|".join(missing),
            "candidate_equal": set(keys).issubset(top_keys),
            "bound_hash": hashlib.sha256("|".join(keys).encode()).hexdigest(),
            "status": "PASS" if len(bound) in (49, 50) and set(keys).issubset(top_keys) else "BLOCKED",
        })
        for row in bound.itertuples(index=False):
            signals.append({"date": row.date, "instrument": row.instrument,
                            "candidate_rank": int(row.qlib_rank_raw), "full_qlib_rank": int(row.qlib_rank_raw),
                            "a_score": float(row.qlib_score_raw), "b_score": float(row.phaseo4_treatment_ltr_score)})
    counts = pd.Series([r["bound_rows"] for r in coverage]).value_counts().to_dict()
    if len(signals) != 3937 or not all(r["status"] == "PASS" for r in coverage):
        raise RuntimeError(f"unexpected O4 coverage: rows={len(signals)} counts={counts}")
    frame = pd.DataFrame(signals)
    prices = engine.Prices(set(frame.instrument))
    a_metrics, a_actions, a_nav = engine.replay(frame, prices, "a_score", "A_ONLY_E1_TOP50", full_ranks)
    b_metrics, b_actions, b_nav = engine.replay(frame, prices, "b_score", "O4_ORTHOGONAL_E1_TOP50", full_ranks)
    write_csv(OUT / "signals.csv", signals)
    write_csv(OUT / "coverage_audit.csv", coverage)
    write_csv(OUT / "A_ONLY_actions.csv", a_actions)
    write_csv(OUT / "O4_actions.csv", b_actions)
    write_csv(OUT / "A_ONLY_daily_nav.csv", a_nav)
    write_csv(OUT / "O4_daily_nav.csv", b_nav)
    write_csv(OUT / "metrics.csv", [a_metrics, b_metrics])
    after = engine.fingerprints()
    report = {
        "run_id": "modelb_o4_same_e1_top50_replay_20260908", "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "window": [START, END], "model": "phaseo4_treatment_model frozen row scores", "complete_only": True,
        "model_path": str(O4_MODEL.relative_to(ROOT)), "row_scores_path": str(O4.relative_to(ROOT)), "sample_path": str(O3.relative_to(ROOT)), "e1_path": str(E1.relative_to(ROOT)),
        "checksums": {"model": sha(O4_MODEL), "row_scores": sha(O4), "sample": sha(O3), "e1": sha(E1)},
        "feature_count": 78, "signals_rows": len(signals), "full50_days": int((pd.Series([r["bound_rows"] for r in coverage]) == 50).sum()),
        "partial49_days": int((pd.Series([r["bound_rows"] for r in coverage]) == 49).sum()), "candidate_equal_all": all(r["candidate_equal"] for r in coverage),
        "a_b_shared_intersection": True, "metrics": [a_metrics, b_metrics],
        "relative": {"o4_minus_a_return": b_metrics["net_return"] - a_metrics["net_return"], "o4_minus_a_drawdown": b_metrics["max_drawdown"] - a_metrics["max_drawdown"], "o4_minus_a_sharpe": b_metrics["sharpe_annualized"] - a_metrics["sharpe_annualized"]},
        "strategy_rule": "top50_exit_one_worst_sell", "execution_price_mode": "next_open", "baseline_admission": False,
        "status": "CONDITIONAL_HISTORICAL_DIAGNOSTIC_RESEARCH_ONLY", "no_publish": True, "no_baseline_switch": True,
        "protected_before": before, "protected_after": after, "protected_unchanged": before == after,
    }
    (OUT / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "safety_audit.json").write_text(json.dumps({"readonly_only": True, "production_allowed": False, "future_labels_consumed_for_scoring": False, "candidate_universe_from_e1_top50": True, "next_open_only": True}, indent=2) + "\n", encoding="utf-8")
    (OUT / "EXECUTION_REPORT_CN.md").write_text("# O4 正交 Model B 当前 E1 Top50 隔离 Replay\n\n" + json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
