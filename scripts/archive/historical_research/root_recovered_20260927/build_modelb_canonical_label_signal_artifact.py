#!/usr/bin/env python3
"""Build an isolated ModelSignalArtifact for the canonical-label B5 model."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b6_canonical_label_signal_artifact_v2_20260914"
B5 = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b5_canonical_label_lgbm_20260914"
B3 = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b3_frozen_modela_oos_score_20260913"
B1 = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b1_same_run_handoff_20260913"
B2 = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b2_canonical_pit_features_20260913"
CANDIDATE_ID = "head10_all_l31_alpha0.7_top50_only"
FIELDS = ["date", "instrument", "model_name", "model_family", "candidate_rank", "buy_score", "raw_score", "score_rank", "full_qlib_rank", "signal_asof", "available_at", "source_artifact", "source_model_artifact", "source_feature_artifact"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    scores = pd.read_parquet(B5 / "CANONICAL_B5_RAW_SCORES.parquet")
    scores["date"] = pd.to_datetime(scores.date).dt.strftime("%Y-%m-%d")
    scores["instrument"] = scores.instrument.astype(str).str.upper()
    scores = scores.rename(columns={"score": "raw_score"})
    b2_keys = pd.read_parquet(B2 / "FEATURE_ARTIFACT_RAW.parquet", columns=["date", "instrument", "candidate_id", "is_dynamic_top50", "qlib_rank"])
    b2_keys["date"] = pd.to_datetime(b2_keys.date).dt.strftime("%Y-%m-%d")
    b2_keys["instrument"] = b2_keys.instrument.astype(str).str.upper()
    b2_keys = b2_keys.rename(columns={"qlib_rank": "candidate_rank"})
    scores = scores.merge(b2_keys, on=["date", "instrument"], how="left", validate="one_to_one")
    scores = scores[(scores.candidate_id == CANDIDATE_ID) & scores.is_dynamic_top50.astype(bool)].copy()
    if scores.candidate_rank.isna().any() or (scores.candidate_rank > 50).any():
        raise RuntimeError("missing or non-top50 canonical candidate rank")
    if scores.duplicated(["date", "instrument"]).any(): raise RuntimeError("duplicate B5 top50 score keys")
    counts = scores.groupby("date").size(); valid_dates = sorted(counts[counts == 50].index.tolist()); blocked_dates = sorted(counts[counts != 50].index.tolist())
    if not valid_dates: raise RuntimeError("no complete top50 dates")
    scores = scores[scores.date.isin(valid_dates)].copy()
    a = pd.read_parquet(B3 / "MODEL_A_FROZEN_OOS_SCORE.parquet", columns=["date", "instrument", "qlib_rank", "dynamic_qlib_rank", "is_dynamic_top50"])
    a["date"] = pd.to_datetime(a.date).dt.strftime("%Y-%m-%d"); a.instrument = a.instrument.astype(str).str.upper(); a = a.rename(columns={"qlib_rank": "full_qlib_rank", "dynamic_qlib_rank": "a_dynamic_rank", "is_dynamic_top50": "a_is_dynamic_top50"})
    out = scores.merge(a, on=["date", "instrument"], how="left", validate="one_to_one")
    if out.full_qlib_rank.isna().any() or out.a_dynamic_rank.isna().any(): raise RuntimeError("missing Model A ranks")
    if (out.candidate_rank != out.a_dynamic_rank).any(): raise RuntimeError("B2 and B3 dynamic candidate ranks diverge")
    if (~out.a_is_dynamic_top50.astype(bool)).any(): raise RuntimeError("B2 candidate key outside Model A dynamic top50")
    b2_keys_by_date = {d: set(g.instrument) for d, g in scores.groupby("date")}
    b3_dynamic = a[a.a_is_dynamic_top50.astype(bool)].copy()
    b3_keys_by_date = {d: set(g.instrument) for d, g in b3_dynamic.groupby("date")}
    if any(b2_keys_by_date.get(d, set()) != b3_keys_by_date.get(d, set()) for d in valid_dates):
        raise RuntimeError("B2 and B3 dynamic candidate key sets diverge")
    out["score_rank"] = out.sort_values(["date", "raw_score", "instrument"], ascending=[True, False, True]).groupby("date").cumcount().add(1).reindex(out.index)
    out["buy_score"] = out["raw_score"]
    out["model_name"] = "modelb_canonical_label_lgbm_20260914"
    out["model_family"] = "ltr"
    out["raw_score"] = out["buy_score"]
    out["signal_asof"] = out["date"]; out["available_at"] = out["date"]
    out["source_artifact"] = str((B5 / "CANONICAL_B5_RAW_SCORES.parquet").relative_to(ROOT))
    out["source_model_artifact"] = str((B5 / "MODEL_B_CANONICAL_LGBM_RANKER.pkl").relative_to(ROOT))
    out["source_feature_artifact"] = str((B2 / "FEATURE_ARTIFACT_RAW.parquet").relative_to(ROOT))
    signals = out[FIELDS].sort_values(["date", "score_rank", "instrument"]).reset_index(drop=True)
    if signals.score_rank.isna().any() or signals.available_at.gt(signals.signal_asof).any(): raise RuntimeError("signal contract check failed")
    rank_audit = signals.groupby("date").candidate_rank.agg(lambda s: sorted(pd.to_numeric(s).astype(int).tolist()))
    if not rank_audit.map(lambda x: x == list(range(1, 51))).all(): raise RuntimeError("candidate ranks are not exactly 1..50")
    signals.to_csv(OUT / "signals.csv", index=False)
    coverage = signals.groupby("date").size().reset_index(name="rows"); coverage["complete_50_of_50"] = coverage.rows.eq(50); coverage.to_csv(OUT / "coverage_audit.csv", index=False)
    schema = {"artifact_type": "ModelSignalArtifact", "schema_version": "model_signal_contract_v1", "required_fields": FIELDS, "primary_key": ["date", "instrument"], "model_name": "modelb_canonical_label_lgbm_20260914", "model_family": "ltr", "candidate_id": CANDIDATE_ID, "research_only": True, "diagnostic_only": True, "production_allowed": False}
    (OUT / "schema.json").write_text(json.dumps(schema, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    manifest = {"schema_version": "modelb.b6.canonical_label.signal_artifact.v1", "status": "EXECUTED_AWAITING_INDEPENDENT_REVIEW", "handoff": False, "can_continue_to_B7": False, "model_name": "modelb_canonical_label_lgbm_20260914", "model_family": "ltr", "candidate_id": CANDIDATE_ID, "rows": int(len(signals)), "dates": int(signals.date.nunique()), "valid_50_of_50_dates": int(len(valid_dates)), "blocked_dates": int(len(blocked_dates)), "blocked_date_list": blocked_dates, "upstream_hashes": {"b5_manifest": sha256(B5 / "B5_CANONICAL_EXECUTOR_MANIFEST.json"), "b5_model": sha256(B5 / "MODEL_B_CANONICAL_LGBM_RANKER.pkl"), "b5_scores": sha256(B5 / "CANONICAL_B5_RAW_SCORES.parquet"), "b3_score": sha256(B3 / "MODEL_A_FROZEN_OOS_SCORE.parquet"), "b2_features": sha256(B2 / "FEATURE_ARTIFACT_RAW.parquet")}, "research_only": True, "diagnostic_only": True, "production_allowed": False, "no_replay": True, "no_baseline_admission": True, "no_default_switch": True, "independent_review_required": True}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=True, default=str) + "\n", encoding="utf-8")
    forbidden = [c for c in signals.columns if c.lower().startswith(("future_", "forward_", "label_")) or c.lower() in {"relevance_10d_top_heavy", "realized_pnl", "action", "holding", "position", "target_position", "target_weight", "order_qty", "execution_price", "execution_date", "broker_order_id"}]
    b2_bound = signals.merge(b2_keys[["date", "instrument", "candidate_rank"]], on=["date", "instrument"], how="left", suffixes=("_signal", "_b2"), validate="one_to_one")
    b3_bound = signals.merge(a[["date", "instrument", "full_qlib_rank"]], on=["date", "instrument"], how="left", suffixes=("_signal", "_b3"), validate="one_to_one")
    checks = {"required_fields": list(signals.columns) == FIELDS, "duplicate_keys": int(signals.duplicated(["date", "instrument"]).sum()) == 0, "daily_50": bool((signals.groupby("date").size() == 50).all()), "score_rank_1_to_50": bool((signals.groupby("date").score_rank.agg(list).map(lambda x: x == list(range(1, 51)))).all()), "candidate_rank_1_to_50": bool((signals.groupby("date").candidate_rank.agg(lambda s: sorted(pd.to_numeric(s).astype(int).tolist())).map(lambda x: x == list(range(1, 51)))).all()), "candidate_rank_bound_to_b2": bool((b2_bound.candidate_rank_signal == b2_bound.candidate_rank_b2).all()), "full_rank_bound_to_b3": bool((b3_bound.full_qlib_rank_signal == b3_bound.full_qlib_rank_b3).all()), "candidate_key_set_matches_b3_dynamic": bool(all(set(g.instrument) == b3_keys_by_date.get(d, set()) for d, g in signals.groupby("date"))), "forbidden_fields": not forbidden, "no_production_write": True}
    validator = {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "details": {"candidate_equals_full_rank_rows": int((signals.candidate_rank == signals.full_qlib_rank).sum()), "forbidden_fields": forbidden}}
    (OUT / "validator_report.json").write_text(json.dumps(validator, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (OUT / "B6_CANONICAL_EXECUTOR_MANIFEST.json").write_text(json.dumps({"status": manifest["status"], "executor_self_check": validator["status"], "handoff": False, "can_continue_to_B7": False, "manifest_sha256": sha256(OUT / "manifest.json")}, indent=2) + "\n", encoding="utf-8")
    (OUT / "B6_CANONICAL_EXECUTION_REPORT_CN.md").write_text(f"# B6 canonical-label ModelSignalArtifact\n\n- 状态：`{manifest['status']}`。\n- 有效日期：`{len(valid_dates)}`；每日严格 50 行。\n- blocked dates：`{len(blocked_dates)}`，不补行、不填充。\n- 只允许在 Model A Top50 内重排；`candidate_rank/full_qlib_rank` 保持 Model A。\n- research/diagnostic only；未 replay、未 baseline admission、未切换 default/latest。\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "rows": len(signals), "dates": len(valid_dates), "blocked_dates": len(blocked_dates), "validator": validator["status"]}, ensure_ascii=True))
    return 0 if validator["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
