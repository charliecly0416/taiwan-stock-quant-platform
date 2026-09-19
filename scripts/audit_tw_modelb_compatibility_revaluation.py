#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "data_tw/experiments/model_b_compatibility_baseline_reinstatement/phase1c_compatibility_20260905"
SOURCE = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv"
FULL = ROOT / "data_tw/experiments/archive/historical_research/phase1c_anchor_reproduction/phasea1_anchor_metrics.csv"
COMMON = ROOT / "data_tw/experiments/archive/historical_research/phase1c_anchor_reproduction/phasea1_common_universe_metrics.csv"
OUT = ARTIFACT / "revaluation_report.json"


def metric(path: Path, method: str) -> dict:
    frame = pd.read_csv(path)
    row = frame.loc[frame["method"] == method].iloc[0]
    return {
        "fee_tax_adjusted_net_return": float(row["fee_tax_adjusted_net_return"]),
        "max_drawdown": float(row["max_drawdown"]),
        "action_count": int(row["action_count"]),
        "period": str(row["period"]),
        "pass": str(row["pass"]).lower() == "yes",
    }


def main() -> None:
    source = pd.read_csv(SOURCE, usecols=["date", "instrument", "qlib_rank", "score_head10_all_l31_alpha0.7_top50_only"])
    artifact = pd.read_csv(ARTIFACT / "signals.csv")
    merged = source[(source["date"] >= "2025-07-01") & (source["date"] <= "2026-05-07")].copy()
    merged["date"] = pd.to_datetime(merged["date"]).dt.strftime("%Y-%m-%d")
    artifact["date"] = pd.to_datetime(artifact["date"]).dt.strftime("%Y-%m-%d")
    joined = merged.merge(artifact, on=["date", "instrument"], how="outer", suffixes=("_source", "_artifact"), indicator=True)
    mapping_ok = bool(
        joined["_merge"].eq("both").all()
        and (pd.to_numeric(joined["qlib_rank"], errors="coerce") == pd.to_numeric(joined["candidate_rank"], errors="coerce")).all()
        and (pd.to_numeric(joined["score_head10_all_l31_alpha0.7_top50_only"], errors="coerce") == pd.to_numeric(joined["buy_score"], errors="coerce")).all()
    )
    full_ab = metric(FULL, "old_qlib_new_ltr_phase1c_simple")
    full_a = metric(FULL, "fresh_qlib_top50_adaptive_baseline")
    common_ab = metric(COMMON, "old_qlib_new_ltr_phase1c_simple")
    common_a = metric(COMMON, "fresh_qlib_top50_adaptive_baseline")
    result = {
        "schema_version": "model_ab_compatibility_revaluation.v1",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "artifact": str(ARTIFACT.relative_to(ROOT)),
        "evaluation_window": "2025-07-01..2026-05-07",
        "mapping": {"ok": mapping_ok, "source_rows": int(len(merged)), "artifact_rows": int(len(artifact)), "joined_rows": int(len(joined)), "duplicate_artifact_keys": int(artifact[["date", "instrument"]].duplicated().sum())},
        "full_universe": {"model_a_plus_b": full_ab, "model_a_only": full_a, "return_delta": round(full_ab["fee_tax_adjusted_net_return"] - full_a["fee_tax_adjusted_net_return"], 6), "drawdown_delta": round(full_ab["max_drawdown"] - full_a["max_drawdown"], 6), "action_delta": full_ab["action_count"] - full_a["action_count"]},
        "common_universe": {"model_a_plus_b": common_ab, "model_a_only": common_a, "return_delta": round(common_ab["fee_tax_adjusted_net_return"] - common_a["fee_tax_adjusted_net_return"], 6), "drawdown_delta": round(common_ab["max_drawdown"] - common_a["max_drawdown"], 6), "action_delta": common_ab["action_count"] - common_a["action_count"]},
        "revaluation_basis": "existing audited next-day replay artifacts reread under the restored standard adapter; no replay rule or metric input changed",
        "strict_pit_oos": False,
        "legacy_compatible": True,
        "production_allowed": False,
        "default_switch_allowed": False,
        "conclusion": "RESTORED_RESEARCH_BASELINE_MODEL_A_PLUS_B; HOLD_OUTSIDE_PRODUCTION_DEFAULT_PENDING_STRICT_PIT_LINEAGE",
    }
    OUT.write_text(json.dumps(result, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
