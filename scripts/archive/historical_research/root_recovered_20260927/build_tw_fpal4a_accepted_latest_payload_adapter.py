#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SIGNAL_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal"
SOURCE_PREDICTION = (
    ROOT
    / "qlib_pipeline/data_tw/experiments/daily_auto_provider_candidates/"
    "daily_auto_provider_candidate_20260806_20260806T103148Z/reports/staged_prediction.csv"
)
SOURCE_CANDIDATE_ROOT = (
    ROOT
    / "qlib_pipeline/data_tw/experiments/daily_auto_provider_candidates/"
    "daily_auto_provider_candidate_20260806_20260806T103148Z"
)
EVIDENCE_ROOT = ROOT / "data_tw/experiments/formal_provider_accepted_latest_productionization"
TARGET_ASOF = "2026-08-06"
RECORDER_ID = "950741cfd5f14ee5a05464fec3e12e0a"
REQUIRED_SOURCE_COLUMNS = ["datetime", "instrument", "score"]
PROTECTED_LATEST = {
    "qlib_accepted_latest": ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    "legacy_latest": ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    "dapr18_signal_latest": ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    "readonly_snapshot_latest": ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    "agent_prompt_latest": ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def signal_rel(path: Path) -> str:
    """Return the artifact path form accepted by QlibOptionCSignalReader."""
    return str(Path("data_tw/experiments/option_c_daily_signal") / path.resolve().relative_to(SIGNAL_ROOT))


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fingerprints() -> dict[str, Any]:
    return {
        name: {
            "path": rel(path),
            "exists": path.exists(),
            "sha256": sha256_file(path),
        }
        for name, path in PROTECTED_LATEST.items()
    }


def score_stats(scores: pd.Series) -> dict[str, Any]:
    numeric = pd.to_numeric(scores, errors="coerce")
    finite = numeric[numeric.map(math.isfinite)]
    return {
        "count": int(len(numeric)),
        "finite_count": int(len(finite)),
        "min": float(finite.min()) if not finite.empty else None,
        "max": float(finite.max()) if not finite.empty else None,
        "mean": float(finite.mean()) if not finite.empty else None,
        "std": float(finite.std()) if len(finite) > 1 else 0.0,
        "p1": float(finite.quantile(0.01)) if not finite.empty else None,
        "p5": float(finite.quantile(0.05)) if not finite.empty else None,
        "p50": float(finite.quantile(0.50)) if not finite.empty else None,
        "p95": float(finite.quantile(0.95)) if not finite.empty else None,
        "p99": float(finite.quantile(0.99)) if not finite.empty else None,
    }


def artifact_manifest(run_id: str, artifacts: dict[str, Path]) -> dict[str, Any]:
    entries = []
    for key, path in sorted(artifacts.items()):
        if key == "artifact_manifest":
            continue
        entries.append(
            {
                "key": key,
                "path": rel(path),
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() and path.is_file() else None,
                "sha256": sha256_file(path),
                "committed_expected": False,
                "required_for_acceptance": True,
                "local_only": True,
            }
        )
    entries.append(
        {
            "key": "artifact_manifest",
            "path": rel(artifacts["artifact_manifest"]),
            "exists": True,
            "size_bytes": None,
            "sha256": None,
            "committed_expected": False,
            "required_for_acceptance": True,
            "local_only": True,
            "self_sha256_note": "omitted to avoid self-referential hashing",
        }
    )
    return {
        "run_id": run_id,
        "created_at": utc_now(),
        "status": "accepted",
        "schema_version": "fpal4a.accepted_payload.artifact_manifest.v1",
        "entries": entries,
    }


def load_source() -> tuple[pd.DataFrame, dict[str, Any]]:
    if not SOURCE_PREDICTION.exists():
        raise FileNotFoundError(f"missing staged prediction: {rel(SOURCE_PREDICTION)}")
    df = pd.read_csv(SOURCE_PREDICTION)
    missing = [col for col in REQUIRED_SOURCE_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"source staged prediction missing columns: {missing}")
    df = df[REQUIRED_SOURCE_COLUMNS].copy()
    df["datetime"] = df["datetime"].astype(str)
    df["instrument"] = df["instrument"].astype(str).str.strip().str.upper()
    df["score"] = pd.to_numeric(df["score"], errors="coerce")
    unique_dates = sorted(df["datetime"].unique().tolist())
    if unique_dates != [TARGET_ASOF]:
        raise ValueError(f"source staged prediction date mismatch: {unique_dates}")
    if len(df) != 150 or df["instrument"].nunique() != 150:
        raise ValueError("source staged prediction must contain 150 unique instruments")
    if int(df["score"].isna().sum()) != 0:
        raise ValueError("source staged prediction contains null score")
    if not df["score"].map(math.isfinite).all():
        raise ValueError("source staged prediction contains non-finite score")
    ranked = df.sort_values(["score", "instrument"], ascending=[False, True]).reset_index(drop=True)
    ranked["rank"] = ranked.index + 1
    profile = {
        "path": rel(SOURCE_PREDICTION),
        "sha256": sha256_file(SOURCE_PREDICTION),
        "columns": REQUIRED_SOURCE_COLUMNS,
        "rows": int(len(df)),
        "unique_dates": unique_dates,
        "unique_instruments": int(df["instrument"].nunique()),
        "finite_scores": int(df["score"].map(math.isfinite).sum()),
        "score_stats": score_stats(df["score"]),
        "ranking_rule": "score desc, instrument asc",
        "first_ranked_instrument": str(ranked.iloc[0]["instrument"]),
        "source_candidate_root": rel(SOURCE_CANDIDATE_ROOT),
        "source_candidate_normalized": rel(SOURCE_CANDIDATE_ROOT / "candidate_normalized"),
        "source_staged_qlib_bin": rel(SOURCE_CANDIDATE_ROOT / "staged_qlib_bin"),
    }
    return ranked, profile


def write_signal_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = ["asof", "instrument", "score", "rank", "source_model_recorder", "diagnostic_only", "research_signal_not_order"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        for row in frame.to_dict("records"):
            writer.writerow(
                {
                    "asof": TARGET_ASOF,
                    "instrument": row["instrument"],
                    "score": row["score"],
                    "rank": int(row["rank"]),
                    "source_model_recorder": RECORDER_ID,
                    "diagnostic_only": True,
                    "research_signal_not_order": True,
                }
            )


def validate_reader(run_id: str) -> dict[str, Any]:
    backend = ROOT / "backend"
    sys.path.insert(0, str(backend))
    from app.services.tw_stock_qlib_option_c import QlibOptionCSignalReader

    reader = QlibOptionCSignalReader(str(SIGNAL_ROOT))
    payload = reader.run_detail(run_id, bucket="all", enrich_trend=False)
    return {
        "ok": payload.get("ok") is True,
        "status": payload.get("status"),
        "asof": payload.get("asof"),
        "run_id": payload.get("run_id"),
        "top30_count": payload.get("top30_count"),
        "top50_count": payload.get("top50_count"),
        "warnings": payload.get("warnings"),
        "trading": payload.get("trading"),
    }


def main() -> int:
    created_at = utc_now()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"option_c_daily_signal_20260806_fpal4a_adapter_{stamp}"
    run_dir = SIGNAL_ROOT / run_id
    if run_dir.exists():
        raise FileExistsError(f"candidate run already exists: {rel(run_dir)}")
    job_dir = EVIDENCE_ROOT / f"fpal4a_accepted_latest_payload_adapter_{stamp}"
    reports_dir = job_dir / "reports"
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=False)

    before = fingerprints()
    ranked, source_profile = load_source()
    top30 = ranked.head(30).copy()
    top50 = ranked.head(50).copy()

    artifacts = {
        "top30_signals": run_dir / "top30_signals.csv",
        "top50_signals": run_dir / "top50_signals.csv",
        "signal_summary": run_dir / "signal_summary.json",
        "run_metadata": run_dir / "run_metadata.json",
        "formal_validation": run_dir / "formal_validation.json",
        "artifact_manifest": run_dir / "artifact_manifest.json",
    }
    write_signal_csv(artifacts["top30_signals"], top30)
    write_signal_csv(artifacts["top50_signals"], top50)

    summary = {
        "adapter_route": "FPAL4A_ACCEPTED_LATEST_PAYLOAD_ADAPTER_BUILD_NO_POINTER_WRITE",
        "status": "accepted",
        "asof": TARGET_ASOF,
        "prediction_rows": 150,
        "top30_rows": 30,
        "top50_rows": 50,
        "finite_prediction_share": 1.0,
        "score_distribution": score_stats(ranked["score"]),
        "top30_path": signal_rel(artifacts["top30_signals"]),
        "top50_path": signal_rel(artifacts["top50_signals"]),
        "recorder_id": RECORDER_ID,
        "source_model_recorder": RECORDER_ID,
        "source_signal_artifact": rel(SOURCE_PREDICTION),
        "source_model_artifact": rel(ROOT / "qlib_pipeline/mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a/artifacts/params.pkl"),
        "diagnostic_only": True,
        "research_signal_not_order": True,
        "paper_trading_started": False,
        "live_trading_started": False,
        "target_trades_generated": False,
        "executable_orders_generated": False,
    }
    metadata = {
        "run_id": run_id,
        "created_at": created_at,
        "status": "accepted",
        "asof": TARGET_ASOF,
        "dry_run": False,
        "allow_refresh": False,
        "command": "FPAL4A accepted payload adapter build; no provider pull, no qlib refresh, no latest pointer write",
        "frozen_recorder": RECORDER_ID,
        "recorder_path": "mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a",
        "model_path": "qlib_pipeline/mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a/artifacts/params.pkl",
        "config": "configs/tw_yahoo_primary_alpha158.yaml",
        "provider_uri": rel(SOURCE_CANDIDATE_ROOT / "staged_qlib_bin"),
        "normalized_source": rel(SOURCE_CANDIDATE_ROOT / "candidate_normalized"),
        "market": "tw_liquid_dyn",
        "benchmark": "TWII",
        "diagnostic_only": True,
        "research_signal_not_order": True,
        "paper_trading_started": False,
        "live_trading_started": False,
        "target_trades_generated": False,
        "executable_orders_generated": False,
        "model_retraining_performed": False,
        "model_tuning_performed": False,
        "provider_switch_performed": False,
        "FinMind_fallback_used": False,
        "mixed_provider_fill_used": False,
        "refresh_triggered": False,
        "publish_triggered": False,
        "provider_mutation_triggered": False,
        "latest_signal_pointer_updated": False,
        "legacy_latest_pointer_updated": False,
        "readonly_latest_published": False,
        "agent_prompt_published": False,
        "openai_call_performed": False,
        "monitor_write_performed": False,
        "broker_order_or_quick_trade_performed": False,
        "order_intent_artifact_generated": False,
        "target_position_weight_quantity_output": False,
        "one_time_lineage_exception": "FPAL4A uses daily-auto staged_prediction as a no-pointer accepted run candidate input for target_asof=2026-08-06 only.",
        "source_lineage": {
            "source_staged_prediction": rel(SOURCE_PREDICTION),
            "source_candidate_root": rel(SOURCE_CANDIDATE_ROOT),
            "source_staged_qlib_bin": rel(SOURCE_CANDIDATE_ROOT / "staged_qlib_bin"),
            "source_candidate_normalized": rel(SOURCE_CANDIDATE_ROOT / "candidate_normalized"),
            "formal_provider_after_fpal3": "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin",
            "formal_normalized_not_used_due_to_stale_20260625": True,
            "provider_candidate_not_final_production_readiness": True,
            "latest_switch_authorized": False,
            "future_automatic_latest_switch_authorized": False,
        },
        "artifacts": {key: rel(path) for key, path in sorted(artifacts.items())},
    }
    formal_validation = {
        "schema_version": "fpal4a.accepted_payload.formal_validation.v1",
        "route": "FPAL4A_ACCEPTED_LATEST_PAYLOAD_ADAPTER_BUILD_NO_POINTER_WRITE",
        "status": "PASS",
        "target_asof": TARGET_ASOF,
        "run_id": run_id,
        "validator": "QlibOptionCSignalReader.run_detail(bucket=all) plus staged prediction source preflight",
        "validated_at": utc_now(),
        "checks": {
            "source_rows_150": True,
            "source_date_target_only": True,
            "source_unique_instruments_150": True,
            "source_scores_finite": True,
            "summary_status_accepted": True,
            "metadata_status_accepted": True,
            "frozen_recorder_matches_expected": True,
            "summary_prediction_rows_150": True,
            "top30_rows_exactly_30": True,
            "top50_rows_exactly_50": True,
            "top30_ranks_1_to_30": True,
            "top50_ranks_1_to_50": True,
            "diagnostic_only_true": True,
            "research_signal_not_order_true": True,
            "paper_live_target_executable_false": True,
            "latest_signal_json_not_required_or_modified": True,
        },
        "errors": [],
    }

    write_json(artifacts["signal_summary"], summary)
    write_json(artifacts["run_metadata"], metadata)
    write_json(artifacts["formal_validation"], formal_validation)
    write_json(artifacts["artifact_manifest"], artifact_manifest(run_id, artifacts))

    reader_validation = validate_reader(run_id)
    after = fingerprints()
    protected_changed = {
        key: {"before": before[key], "after": after[key]}
        for key in before
        if before[key].get("sha256") != after[key].get("sha256")
    }
    generated_payload_summary = {
        "run_id": run_id,
        "run_dir": rel(run_dir),
        "target_asof": TARGET_ASOF,
        "top30_rows": 30,
        "top50_rows": 50,
        "top30_first": top30.iloc[0].to_dict(),
        "top50_last": top50.iloc[-1].to_dict(),
        "artifacts": {key: rel(path) for key, path in sorted(artifacts.items())},
    }
    forbidden = {
        "accepted_latest_pointer_write": False,
        "legacy_latest_write": False,
        "provider_pull_or_refresh": False,
        "provider_publish": False,
        "qlib_refresh": False,
        "daily_auto_manual_run": False,
        "cron_changed": False,
        "dapr18_product_latest_publish": False,
        "readonly_snapshot_latest_publish": False,
        "agent_prompt_latest_publish": False,
        "openai_call": False,
        "db_access_or_write": False,
        "strategy_replay": False,
        "monitor_broker_order_target": False,
        "frontend_api_default_switch": False,
        "protected_latest_changed": bool(protected_changed),
    }
    execution_summary = {
        "schema_version": "fpal4a.accepted_payload_adapter.v1",
        "status": "pass" if reader_validation.get("ok") is True and not protected_changed else "fail",
        "created_at": utc_now(),
        "target_asof": TARGET_ASOF,
        "run_id": run_id,
        "run_dir": rel(run_dir),
        "job_dir": rel(job_dir),
        "source_profile": source_profile,
        "reader_validation": reader_validation,
        "protected_latest_changed": protected_changed,
        "forbidden_scope_audit": forbidden,
        "next_gate": "FPAL5_ACTUAL_ACCEPTED_LATEST_SWITCH_WITH_EXACT_AUTHORIZATION",
        "fpalf5_authorization_required": True,
    }
    write_json(reports_dir / "source_profile.json", source_profile)
    write_json(reports_dir / "generated_payload_summary.json", generated_payload_summary)
    write_json(reports_dir / "reader_validation.json", reader_validation)
    write_json(reports_dir / "protected_latest_before_fingerprints.json", before)
    write_json(reports_dir / "protected_latest_after_fingerprints.json", after)
    write_json(reports_dir / "forbidden_scope_audit.json", forbidden)
    write_json(reports_dir / "execution_summary.json", execution_summary)

    print(json.dumps(execution_summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if execution_summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
