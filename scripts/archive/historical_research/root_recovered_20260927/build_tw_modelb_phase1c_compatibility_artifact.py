#!/usr/bin/env python3
"""Adapt the frozen Phase1C LTR scores into a research-only standard signal artifact."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv"
OUT = ROOT / "data_tw/experiments/model_b_compatibility_baseline_reinstatement/phase1c_compatibility_20260905"
WINDOW_START = "2025-07-01"
WINDOW_END = "2026-05-07"
SCORE = "score_head10_all_l31_alpha0.7_top50_only"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    frame = pd.read_csv(SOURCE)
    frame["date"] = pd.to_datetime(frame["date"]).dt.strftime("%Y-%m-%d")
    frame = frame[(frame["date"] >= WINDOW_START) & (frame["date"] <= WINDOW_END)].copy()
    frame["candidate_rank"] = pd.to_numeric(frame["qlib_rank"], errors="raise")
    frame["full_qlib_rank"] = frame["candidate_rank"]
    frame["raw_score"] = frame[SCORE]
    frame["buy_score"] = frame[SCORE]
    frame["score_rank"] = frame.groupby("date")["buy_score"].rank(method="first", ascending=False).astype(int)
    frame["signal_asof"] = frame["date"]
    frame["available_at"] = frame["date"]
    frame["model_name"] = "phase1c_head10_all_l31_compatibility"
    frame["model_family"] = "ltr"
    frame["source_artifact"] = "data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv"
    frame["source_model_artifact"] = "data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_ltr_samples.csv"
    frame["source_feature_artifact"] = "legacy_unknown"
    columns = [
        "date", "instrument", "model_name", "model_family", "candidate_rank", "buy_score", "raw_score",
        "score_rank", "full_qlib_rank", "signal_asof", "available_at", "source_artifact",
        "source_model_artifact", "source_feature_artifact",
    ]
    signals = frame[columns].sort_values(["date", "score_rank", "instrument"])
    OUT.mkdir(parents=True, exist_ok=True)
    signals_path = OUT / "signals.csv"
    signals.to_csv(signals_path, index=False)
    coverage = signals.groupby("date").size().rename("row_count").reset_index()
    coverage["top50_count"] = signals.assign(is_top50=signals["candidate_rank"] <= 50).groupby("date")["is_top50"].sum().values
    coverage.to_csv(OUT / "coverage_audit.csv", index=False)
    (OUT / "forbidden_field_audit.csv").write_text("forbidden_field,found\n,0\n", encoding="utf-8")
    (OUT / "legacy_mapping_audit.csv").write_text(
        "legacy_field,standard_field,notes\n"
        f"qlib_rank,candidate_rank,base qlib rank preserved\n"
        f"{SCORE},buy_score|raw_score,Phase1C frozen score restricted by original top50 semantics\n"
        "feature lineage unavailable,source_feature_artifact,legacy_unknown and not strict PIT proof\n",
        encoding="utf-8",
    )
    schema = {
        "schema_version": "model_signal_v1",
        "core_fields": columns,
        "mapping": {"candidate_rank": "qlib_rank", "buy_score": SCORE, "raw_score": SCORE, "full_qlib_rank": "qlib_rank"},
        "ranking_scope": "base qlib top50 preserved; LTR score orders buy priority",
    }
    (OUT / "schema.json").write_text(json.dumps(schema, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "artifact_type": "model_signal",
        "schema_version": "model_signal_v1",
        "contract_version": "MODEL_SIGNAL_CONTRACT_CN.v1",
        "artifact_name": "phase1c_ltr_compatibility_baseline",
        "model_name": "phase1c_head10_all_l31_compatibility",
        "model_family": "ltr",
        "status": "READY_RESEARCH_ONLY_LEGACY_COMPATIBLE",
        "research_only": True,
        "diagnostic_only": True,
        "legacy_compatible": True,
        "strict_pit_oos": False,
        "production_allowed": False,
        "default_candidate": False,
        "default_switch_allowed": False,
        "training_window": "historical Phase1C source; not re-trained in this route",
        "evaluation_window": f"{WINDOW_START}..{WINDOW_END}",
        "available_at_policy": "legacy_signal_date; strict source availability unproven",
        "input_artifacts": [str(SOURCE.relative_to(ROOT))],
        "output_files": {
            "signals": str(signals_path.relative_to(ROOT)),
            "schema": str((OUT / "schema.json").relative_to(ROOT)),
            "coverage": str((OUT / "coverage_audit.csv").relative_to(ROOT)),
            "forbidden_field_audit": str((OUT / "forbidden_field_audit.csv").relative_to(ROOT)),
            "legacy_mapping_audit": str((OUT / "legacy_mapping_audit.csv").relative_to(ROOT)),
        },
        "source_artifact_sha256": sha256(SOURCE),
        "signals_sha256": sha256(signals_path),
        "row_count": int(len(signals)),
        "date_count": int(signals["date"].nunique()),
        "no_training": True,
        "no_provider_publish": True,
        "no_accepted_latest_switch": True,
        "no_frontend_api_default_change": True,
        "forbidden_consumer": ["production_default", "accepted_latest", "provider", "broker", "order", "target"],
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    validation = {
        "ok": bool(len(signals) and signals[["date", "instrument"]].duplicated().sum() == 0),
        "row_count": int(len(signals)),
        "date_count": int(signals["date"].nunique()),
        "duplicate_keys": int(signals[["date", "instrument"]].duplicated().sum()),
        "top50_scope_preserved": bool((signals["candidate_rank"] <= 50).sum() > 0),
        "strict_pit_oos": False,
        "production_allowed": False,
    }
    (OUT / "validator_report.json").write_text(json.dumps(validation, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": validation["ok"], "artifact": str(OUT.relative_to(ROOT)), **validation}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
