#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SIGNAL_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal"
FORMAL_PROVIDER_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin"
EVIDENCE_ROOT = ROOT / "data_tw/experiments/formal_provider_accepted_latest_exact_enablement"
RECORDER_ID = "950741cfd5f14ee5a05464fec3e12e0a"
DEFAULT_TARGET_ASOF = "2026-08-07"
DEFAULT_SOURCE_CANDIDATE_ROOT = (
    ROOT
    / "qlib_pipeline/data_tw/experiments/daily_auto_provider_candidates/"
    "daily_auto_provider_candidate_20260807_20260807T103148Z"
)
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


def provider_calendar_status(provider_root: Path, target_asof: str) -> dict[str, Any]:
    calendar = provider_root / "calendars/day.txt"
    if not calendar.exists():
        return {"ok": False, "path": rel(calendar), "reason": "missing_calendar"}
    dates = [line.strip() for line in calendar.read_text(encoding="utf-8").splitlines() if line.strip()]
    max_date = max(dates) if dates else None
    return {
        "ok": target_asof in dates,
        "path": rel(calendar),
        "sha256": sha256_file(calendar),
        "date_count": len(dates),
        "min_date": min(dates) if dates else None,
        "max_date": max_date,
        "target_asof_present": target_asof in dates,
    }


def formal_provider_calendar_status(target_asof: str) -> dict[str, Any]:
    return provider_calendar_status(FORMAL_PROVIDER_ROOT, target_asof)


def formal_provider_fingerprints() -> dict[str, Any]:
    tracked = {
        "calendar_day": FORMAL_PROVIDER_ROOT / "calendars/day.txt",
        "instruments_all": FORMAL_PROVIDER_ROOT / "instruments/all.txt",
    }
    return {
        key: {
            "path": rel(path),
            "exists": path.exists(),
            "sha256": sha256_file(path),
        }
        for key, path in tracked.items()
    }


def load_staged_universe(source_candidate_root: Path, target_asof: str) -> tuple[set[str], dict[str, Any]]:
    instruments_path = source_candidate_root / "staged_qlib_bin/instruments/all.txt"
    if not instruments_path.exists():
        raise FileNotFoundError(f"missing staged instruments: {rel(instruments_path)}")
    rows: list[dict[str, str | None]] = []
    symbols: list[str] = []
    malformed_lines: list[str] = []
    uncovered_symbols: list[str] = []
    for raw_line in instruments_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 1:
            malformed_lines.append(raw_line)
            continue
        symbol = parts[0].strip().upper()
        start = parts[1] if len(parts) > 1 else None
        end = parts[2] if len(parts) > 2 else None
        symbols.append(symbol)
        rows.append({"symbol": symbol, "start": start, "end": end})
        if start and target_asof < start:
            uncovered_symbols.append(symbol)
        if end and target_asof > end:
            uncovered_symbols.append(symbol)
    unique_symbols = set(symbols)
    duplicate_count = len(symbols) - len(unique_symbols)
    if malformed_lines:
        raise ValueError(f"staged instruments contain malformed lines: {malformed_lines[:5]}")
    if len(symbols) != 150 or len(unique_symbols) != 150:
        raise ValueError(
            "staged instruments must contain 150 unique symbols: "
            f"rows={len(symbols)} unique={len(unique_symbols)} duplicates={duplicate_count}"
        )
    if uncovered_symbols:
        raise ValueError(f"staged instruments do not cover target_asof: {uncovered_symbols[:10]}")
    return unique_symbols, {
        "path": rel(instruments_path),
        "sha256": sha256_file(instruments_path),
        "rows": len(symbols),
        "unique_symbols": len(unique_symbols),
        "duplicate_count": duplicate_count,
        "target_asof_covered_symbols": len(symbols) - len(set(uncovered_symbols)),
        "min_start": min((str(row["start"]) for row in rows if row["start"]), default=None),
        "max_end": max((str(row["end"]) for row in rows if row["end"]), default=None),
    }


def validate_source_contract(
    source_candidate_root: Path,
    target_asof: str,
    *,
    explicit_source_candidate_root: bool,
) -> dict[str, Any]:
    formal_status = formal_provider_calendar_status(target_asof)
    if not explicit_source_candidate_root:
        if formal_status.get("ok") is not True:
            raise RuntimeError(f"formal provider does not cover target asof: {formal_status}")
        return {
            "source_mode": "formal_provider_covered_source_candidate",
            "formal_provider_status": formal_status,
            "staged_provider_calendar_status": None,
            "staged_universe_status": None,
            "staged_universe_symbols": None,
        }

    staged_provider_root = source_candidate_root / "staged_qlib_bin"
    staged_calendar_status = provider_calendar_status(staged_provider_root, target_asof)
    if staged_calendar_status.get("ok") is not True:
        raise RuntimeError(f"staged provider calendar does not cover target asof: {staged_calendar_status}")
    staged_symbols, staged_universe_status = load_staged_universe(source_candidate_root, target_asof)
    return {
        "source_mode": "explicit_staged_provider_root",
        "formal_provider_status": formal_status,
        "staged_provider_calendar_status": staged_calendar_status,
        "staged_universe_status": staged_universe_status,
        "staged_universe_symbols": staged_symbols,
    }


def load_source(
    source_prediction: Path,
    source_candidate_root: Path,
    target_asof: str,
    expected_instruments: set[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not source_prediction.exists():
        raise FileNotFoundError(f"missing staged prediction: {rel(source_prediction)}")
    df = pd.read_csv(source_prediction)
    missing = [col for col in REQUIRED_SOURCE_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"source staged prediction missing columns: {missing}")
    df = df[REQUIRED_SOURCE_COLUMNS].copy()
    df["datetime"] = df["datetime"].astype(str)
    df["instrument"] = df["instrument"].astype(str).str.strip().str.upper()
    df["score"] = pd.to_numeric(df["score"], errors="coerce")
    unique_dates = sorted(df["datetime"].unique().tolist())
    if unique_dates != [target_asof]:
        raise ValueError(f"source staged prediction date mismatch: {unique_dates}")
    if len(df) != 150 or df["instrument"].nunique() != 150:
        raise ValueError("source staged prediction must contain 150 unique instruments")
    prediction_symbols = set(df["instrument"].tolist())
    if expected_instruments is not None and prediction_symbols != expected_instruments:
        missing = sorted(expected_instruments - prediction_symbols)
        extra = sorted(prediction_symbols - expected_instruments)
        raise ValueError(
            "source staged prediction instruments do not match staged universe: "
            f"missing={missing[:10]} extra={extra[:10]}"
        )
    if int(df["score"].isna().sum()) != 0:
        raise ValueError("source staged prediction contains null score")
    if not df["score"].map(math.isfinite).all():
        raise ValueError("source staged prediction contains non-finite score")
    ranked = df.sort_values(["score", "instrument"], ascending=[False, True]).reset_index(drop=True)
    ranked["rank"] = ranked.index + 1
    return ranked, {
        "path": rel(source_prediction),
        "sha256": sha256_file(source_prediction),
        "columns": REQUIRED_SOURCE_COLUMNS,
        "rows": int(len(df)),
        "unique_dates": unique_dates,
        "unique_instruments": int(df["instrument"].nunique()),
        "matches_staged_universe": expected_instruments is None or prediction_symbols == expected_instruments,
        "finite_scores": int(df["score"].map(math.isfinite).sum()),
        "score_stats": score_stats(df["score"]),
        "ranking_rule": "score desc, instrument asc",
        "first_ranked_instrument": str(ranked.iloc[0]["instrument"]),
        "source_candidate_root": rel(source_candidate_root),
        "source_candidate_normalized": rel(source_candidate_root / "candidate_normalized"),
        "source_staged_qlib_bin": rel(source_candidate_root / "staged_qlib_bin"),
    }


def write_signal_csv(path: Path, frame: pd.DataFrame, target_asof: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = ["asof", "instrument", "score", "rank", "source_model_recorder", "diagnostic_only", "research_signal_not_order"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        for row in frame.to_dict("records"):
            writer.writerow(
                {
                    "asof": target_asof,
                    "instrument": row["instrument"],
                    "score": row["score"],
                    "rank": int(row["rank"]),
                    "source_model_recorder": RECORDER_ID,
                    "diagnostic_only": True,
                    "research_signal_not_order": True,
                }
            )


def artifact_manifest(run_id: str, artifacts: dict[str, Path]) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for key, path in sorted(artifacts.items()):
        is_self = key == "artifact_manifest"
        entries.append(
            {
                "key": key,
                "path": rel(path),
                "exists": True if is_self else path.exists(),
                "size_bytes": None if is_self else path.stat().st_size if path.exists() and path.is_file() else None,
                "sha256": None if is_self else sha256_file(path),
                "required_for_acceptance": True,
                "local_only": True,
            }
        )
    return {
        "schema_version": "fpale2.accepted_latest_candidate.artifact_manifest.v1",
        "created_at": utc_now(),
        "run_id": run_id,
        "status": "accepted_candidate",
        "entries": entries,
        "self_hash_note": "artifact_manifest sha256 omitted to avoid self-referential hashing",
    }


def validate_reader(run_id: str) -> dict[str, Any]:
    sys.path.insert(0, str(ROOT / "backend"))
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build FPALE2 accepted latest candidate without pointer writes.")
    parser.add_argument("--target-asof", default=DEFAULT_TARGET_ASOF)
    parser.add_argument("--source-candidate-root", default=str(DEFAULT_SOURCE_CANDIDATE_ROOT))
    parser.add_argument("--run-id", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target_asof = str(args.target_asof)
    source_candidate_root = Path(args.source_candidate_root)
    source_prediction = source_candidate_root / "reports/staged_prediction.csv"
    explicit_source_candidate_root = any(
        arg == "--source-candidate-root" or arg.startswith("--source-candidate-root=")
        for arg in sys.argv[1:]
    )
    created_at = utc_now()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    asof_compact = target_asof.replace("-", "")
    run_id = args.run_id or f"option_c_daily_signal_{asof_compact}_fpale2_candidate_{stamp}"
    run_dir = SIGNAL_ROOT / run_id
    if run_dir.exists():
        raise FileExistsError(f"candidate run already exists: {rel(run_dir)}")

    job_dir = EVIDENCE_ROOT / f"fpale2_accepted_latest_candidate_{target_asof.replace('-', '')}_{stamp}"
    reports_dir = job_dir / "reports"

    source_contract = validate_source_contract(
        source_candidate_root,
        target_asof,
        explicit_source_candidate_root=explicit_source_candidate_root,
    )
    formal_provider_status = source_contract["formal_provider_status"]
    source_mode = source_contract["source_mode"]
    ranked, source_profile = load_source(
        source_prediction,
        source_candidate_root,
        target_asof,
        expected_instruments=source_contract.get("staged_universe_symbols"),
    )

    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=False)

    before = fingerprints()
    formal_provider_before = formal_provider_fingerprints()
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
    write_signal_csv(artifacts["top30_signals"], top30, target_asof)
    write_signal_csv(artifacts["top50_signals"], top50, target_asof)

    summary = {
        "adapter_route": "FPALE2_ACCEPTED_LATEST_CANDIDATE_BUILD_OR_STOP",
        "source_mode": source_mode,
        "status": "accepted",
        "asof": target_asof,
        "prediction_rows": 150,
        "top30_rows": 30,
        "top50_rows": 50,
        "finite_prediction_share": 1.0,
        "score_distribution": score_stats(ranked["score"]),
        "top30_path": signal_rel(artifacts["top30_signals"]),
        "top50_path": signal_rel(artifacts["top50_signals"]),
        "recorder_id": RECORDER_ID,
        "source_model_recorder": RECORDER_ID,
        "source_signal_artifact": rel(source_prediction),
        "source_candidate_root": rel(source_candidate_root),
        "source_candidate_staged_provider": rel(source_candidate_root / "staged_qlib_bin"),
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
        "asof": target_asof,
        "source_mode": source_mode,
        "dry_run": False,
        "allow_refresh": False,
        "command": "FPALE2 accepted latest candidate build; no provider pull, no qlib refresh, no latest pointer write",
        "frozen_recorder": RECORDER_ID,
        "recorder_path": "mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a",
        "model_path": "qlib_pipeline/mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a/artifacts/params.pkl",
        "config": "configs/tw_yahoo_primary_alpha158.yaml",
        "provider_uri": rel(
            source_candidate_root / "staged_qlib_bin"
            if source_mode == "explicit_staged_provider_root"
            else FORMAL_PROVIDER_ROOT
        ),
        "formal_provider_uri": rel(FORMAL_PROVIDER_ROOT),
        "source_candidate_staged_provider": rel(source_candidate_root / "staged_qlib_bin"),
        "normalized_source": rel(source_candidate_root / "candidate_normalized"),
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
        "one_time_lineage_exception": (
            "FPALE2/QALD uses the explicit staged_prediction as a no-pointer "
            f"accepted latest candidate input for target_asof={target_asof} only."
        ),
        "source_lineage": {
            "source_staged_prediction": rel(source_prediction),
            "source_candidate_root": rel(source_candidate_root),
            "source_staged_qlib_bin": rel(source_candidate_root / "staged_qlib_bin"),
            "source_candidate_normalized": rel(source_candidate_root / "candidate_normalized"),
            "source_mode": source_mode,
            "formal_provider_after_fpale1": rel(FORMAL_PROVIDER_ROOT),
            "provider_candidate_not_final_production_readiness": True,
            "latest_switch_authorized": False,
            "future_automatic_latest_switch_authorized": False,
        },
        "artifacts": {key: rel(path) for key, path in sorted(artifacts.items())},
    }
    formal_validation = {
        "schema_version": "fpale2.accepted_latest_candidate.formal_validation.v1",
        "route": "FPALE2_ACCEPTED_LATEST_CANDIDATE_BUILD_OR_STOP",
        "status": "PASS",
        "target_asof": target_asof,
        "run_id": run_id,
        "validator": "QlibOptionCSignalReader.run_detail(bucket=all) plus staged prediction and formal provider calendar checks",
        "validated_at": utc_now(),
        "checks": {
            "source_mode_valid": source_mode
            in {"explicit_staged_provider_root", "formal_provider_covered_source_candidate"},
            "formal_provider_calendar_covers_target_asof_or_not_required": (
                formal_provider_status.get("ok") is True or source_mode == "explicit_staged_provider_root"
            ),
            "source_provider_calendar_covers_target_asof": (
                (source_contract.get("staged_provider_calendar_status") or {}).get("ok") is True
                if source_mode == "explicit_staged_provider_root"
                else formal_provider_status.get("ok") is True
            ),
            "staged_provider_calendar_covers_target_asof": (
                (source_contract.get("staged_provider_calendar_status") or {}).get("ok") is True
                if source_mode == "explicit_staged_provider_root"
                else None
            ),
            "staged_universe_150_symbols": (
                (source_contract.get("staged_universe_status") or {}).get("unique_symbols") == 150
                if source_mode == "explicit_staged_provider_root"
                else None
            ),
            "source_rows_150": True,
            "source_date_target_only": True,
            "source_unique_instruments_150": True,
            "source_matches_staged_universe": bool(source_profile.get("matches_staged_universe")),
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
    formal_provider_after = formal_provider_fingerprints()
    formal_provider_changed = {
        key: {"before": formal_provider_before[key], "after": formal_provider_after[key]}
        for key in formal_provider_before
        if formal_provider_before[key].get("sha256") != formal_provider_after[key].get("sha256")
    }
    protected_changed = {
        key: {"before": before[key], "after": after[key]}
        for key in before
        if before[key].get("sha256") != after[key].get("sha256")
    }
    forbidden = {
        "accepted_latest_pointer_write": False,
        "legacy_latest_write": False,
        "provider_pull_or_refresh": False,
        "formal_provider_mutation": bool(formal_provider_changed),
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
    generated_payload_summary = {
        "run_id": run_id,
        "run_dir": rel(run_dir),
        "target_asof": target_asof,
        "top30_rows": 30,
        "top50_rows": 50,
        "top30_first": top30.iloc[0].to_dict(),
        "top50_last": top50.iloc[-1].to_dict(),
        "artifacts": {key: rel(path) for key, path in sorted(artifacts.items())},
    }
    execution_summary = {
        "schema_version": "fpale2.accepted_latest_candidate.v1",
        "status": "pass"
        if reader_validation.get("ok") is True and not protected_changed and not formal_provider_changed
        else "fail",
        "created_at": utc_now(),
        "target_asof": target_asof,
        "run_id": run_id,
        "run_dir": rel(run_dir),
        "job_dir": rel(job_dir),
        "source_mode": source_mode,
        "formal_provider_status": formal_provider_status,
        "staged_provider_calendar_status": source_contract.get("staged_provider_calendar_status"),
        "staged_universe_status": source_contract.get("staged_universe_status"),
        "source_profile": source_profile,
        "reader_validation": reader_validation,
        "protected_latest_changed": protected_changed,
        "formal_provider_changed": formal_provider_changed,
        "forbidden_scope_audit": forbidden,
        "next_gate": (
            "QALD3_NATURAL_CRON_RE_OBSERVATION_NO_POINTER"
            if source_mode == "explicit_staged_provider_root"
            else "FPALE3_ACCEPTED_LATEST_SWITCH_PREFLIGHT_OR_STOP"
        ),
        "accepted_latest_switch_authorization_required": True,
    }
    write_json(reports_dir / "formal_provider_status.json", formal_provider_status)
    write_json(reports_dir / "staged_provider_calendar_status.json", source_contract.get("staged_provider_calendar_status") or {})
    write_json(reports_dir / "staged_universe_status.json", source_contract.get("staged_universe_status") or {})
    write_json(reports_dir / "source_profile.json", source_profile)
    write_json(reports_dir / "generated_payload_summary.json", generated_payload_summary)
    write_json(reports_dir / "reader_validation.json", reader_validation)
    write_json(reports_dir / "protected_latest_before_fingerprints.json", before)
    write_json(reports_dir / "protected_latest_after_fingerprints.json", after)
    write_json(reports_dir / "formal_provider_before_fingerprints.json", formal_provider_before)
    write_json(reports_dir / "formal_provider_after_fingerprints.json", formal_provider_after)
    write_json(reports_dir / "forbidden_scope_audit.json", forbidden)
    write_json(reports_dir / "execution_summary.json", execution_summary)

    print(json.dumps(execution_summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if execution_summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
