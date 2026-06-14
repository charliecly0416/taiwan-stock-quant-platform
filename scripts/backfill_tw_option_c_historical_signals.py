#!/usr/bin/env python3
"""Backfill Option C daily research signals into an isolated local root.

The script generates historical qlib research signal artifacts for replay only.
It never updates latest_signal.json, refreshes data, publishes providers,
connects to brokers, or writes business state.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
QLIB_ROOT = ROOT / "qlib_pipeline"
if str(QLIB_ROOT) not in sys.path:
    sys.path.insert(0, str(QLIB_ROOT))

from examples.tw.run_option_c_daily_prediction import (  # noqa: E402
    BENCHMARK,
    CONFIG_PATH,
    MARKET,
    MODEL_PATH,
    RECORDER_DIR,
    RECORDER_ID,
    rel,
    score_stats,
    write_json,
)
from examples.tw.run_option_c_daily_signal import (  # noqa: E402
    accepted_prediction_universe,
    signal_frame,
    write_manifest,
)
from examples.tw.run_option_c_daily_signal_option_c_provider import (  # noqa: E402
    OPTION_C_PROVIDER,
    OPTION_C_NORMALIZED,
    formal_validation,
    generate_prediction_for_symbols,
)

DEFAULT_OUTPUT_ROOT = QLIB_ROOT / "data_tw/experiments/option_c_historical_signal_backfill"
CALENDAR_PATH = OPTION_C_PROVIDER / "calendars/day.txt"
REQUIRED_PROVIDER_FIELDS = {"open", "high", "low", "close", "volume", "vwap", "factor"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_date(raw: str) -> date:
    return date.fromisoformat(str(raw or "").strip()[:10])


def trading_days(start: date, end: date) -> list[str]:
    if not CALENDAR_PATH.exists():
        raise FileNotFoundError(f"missing provider calendar: {CALENDAR_PATH}")
    rows = [line.strip() for line in CALENDAR_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [item for item in rows if start <= parse_date(item) <= end]


def safe_batch_root(output_root: Path, batch_id: str) -> Path:
    clean = "".join(ch for ch in str(batch_id or "").strip() if ch.isalnum() or ch in "._-")
    if not clean:
        clean = f"option_c_historical_backfill_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    root = (output_root / clean).resolve(strict=False)
    base = output_root.resolve(strict=False)
    try:
        root.relative_to(base)
    except ValueError as exc:
        raise ValueError("batch output root escapes output-root") from exc
    return root


def run_id_for(asof: str, batch_id: str) -> str:
    safe_batch = "".join(ch for ch in batch_id if ch.isalnum() or ch in "._-")[:48] or "backfill"
    return f"option_c_daily_signal_{asof.replace('-', '')}_{safe_batch}_historical_backfill"


def provider_instrument_ranges() -> dict[str, tuple[str, str]]:
    path = OPTION_C_PROVIDER / "instruments/all.txt"
    ranges: dict[str, tuple[str, str]] = {}
    if not path.exists():
        return ranges
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split()
        if len(parts) >= 3:
            ranges[parts[0]] = (parts[1], parts[2])
    return ranges


def provider_feature_complete(symbol: str) -> bool:
    feature_dir = OPTION_C_PROVIDER / "features" / symbol.lower()
    if not feature_dir.exists():
        return False
    fields = {path.name.split(".")[0] for path in feature_dir.glob("*.day.bin")}
    return REQUIRED_PROVIDER_FIELDS.issubset(fields)


def normalized_has_asof(symbol: str, asof: str) -> bool:
    import pandas as pd

    path = OPTION_C_NORMALIZED / f"{symbol}.csv"
    if not path.exists():
        return False
    try:
        dates = pd.read_csv(path, usecols=["date"])["date"].astype(str)
    except Exception:
        return False
    return bool((dates == asof).any())


def asof_aware_universe(asof: str, candidate_symbols: list[str]) -> tuple[list[str], list[dict[str, Any]]]:
    """Return symbols visible in the dedicated Option C source at this asof."""
    ranges = provider_instrument_ranges()
    selected: list[str] = []
    excluded: list[dict[str, Any]] = []
    for symbol in sorted(candidate_symbols):
        reasons: list[str] = []
        inst_range = ranges.get(symbol)
        if inst_range is None:
            reasons.append("outside_instrument_date_range")
        else:
            start, end = inst_range
            if asof < start or asof > end:
                reasons.append("outside_instrument_date_range")
        if not normalized_has_asof(symbol, asof):
            reasons.append("missing_source_asof")
        if not provider_feature_complete(symbol):
            reasons.append("missing_provider_feature")
        if reasons:
            excluded.append({"symbol": symbol, "reasons": sorted(set(reasons))})
        else:
            selected.append(symbol)
    return selected, excluded


def write_report(batch_root: Path, payload: dict[str, Any]) -> None:
    lines = [
        "---",
        f"created_at: {utc_now()}",
        "scope: tw_option_c_historical_signal_backfill",
        f"status: {payload.get('status')}",
        "---",
        "",
        "# TW Option C Historical Signal Backfill Report",
        "",
        f"- range: `{payload.get('start_date')}` to `{payload.get('end_date')}`",
        f"- output_root: `{rel(batch_root)}`",
        f"- trading_days: `{payload.get('trading_day_count')}`",
        f"- generated: `{payload.get('generated_count')}`",
        f"- skipped_existing: `{payload.get('skipped_existing_count')}`",
        f"- failed: `{payload.get('failed_count')}`",
        f"- latest_signal_updated: `{payload.get('latest_signal_updated')}`",
        "",
        "These artifacts are for research-only historical replay. They are not orders, not target positions, and not production latest signal pointers.",
    ]
    (batch_root / "backfill_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_one(
    asof: str,
    *,
    batch_root: Path,
    batch_id: str,
    symbols: list[str],
    skip_existing: bool,
    research_only_skip_formal_validation: bool = False,
    asof_aware: bool = False,
) -> dict[str, Any]:
    run_id = run_id_for(asof, batch_id)
    run_dir = batch_root / run_id
    if skip_existing and (run_dir / "run_metadata.json").exists():
        return {"asof": asof, "run_id": run_id, "status": "skipped_existing", "run_dir": rel(run_dir)}
    run_dir.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, Path] = {
        "run_metadata": run_dir / "run_metadata.json",
        "formal_validation": run_dir / "formal_validation.json",
        "signal_summary": run_dir / "signal_summary.json",
        "implementation_report": run_dir / "implementation_report.md",
    }
    errors: list[str] = []
    status = "failed"
    signal_summary: dict[str, Any] = {}
    active_symbols = list(symbols)
    excluded_symbols: list[dict[str, Any]] = []
    try:
        if asof_aware:
            active_symbols, excluded_symbols = asof_aware_universe(asof, symbols)
            if not active_symbols:
                status = "blocked_empty_asof_aware_universe"
                errors.append("empty_asof_aware_universe")
                raise RuntimeError("empty asof-aware universe")
        if research_only_skip_formal_validation:
            validation = {
                "status": "research_only_bypassed",
                "asof": asof,
                "reason": "formal source asof coverage is unavailable for this historical stress-test period",
                "research_signal_not_order": True,
                "formal_validation_bypassed_for_research_only": True,
            }
        else:
            validation = formal_validation(asof, active_symbols)
        if asof_aware:
            validation["asof_aware_universe"] = {
                "enabled": True,
                "candidate_count": len(symbols),
                "active_count": len(active_symbols),
                "excluded_count": len(excluded_symbols),
                "excluded_symbols": excluded_symbols,
            }
        write_json(artifacts["formal_validation"], validation)
        if validation.get("status") != "pass" and not research_only_skip_formal_validation:
            status = "blocked_formal_validation_failed"
            errors.extend(validation.get("errors") or [])
            raise RuntimeError("formal validation failed")
        prediction = generate_prediction_for_symbols(asof, active_symbols)
        pred_path = run_dir / "prediction.csv"
        top30_path = run_dir / "top30_signals.csv"
        top50_path = run_dir / "top50_signals.csv"
        artifacts.update({"prediction": pred_path, "top30_signals": top30_path, "top50_signals": top50_path})
        prediction.reset_index().to_csv(pred_path, index=False)
        top30 = signal_frame(prediction, asof, 30)
        top50 = signal_frame(prediction, asof, 50)
        top30.to_csv(top30_path, index=False)
        top50.to_csv(top50_path, index=False)
        stats = score_stats(prediction["score"])
        status = "accepted"
        signal_summary = {
            "status": status,
            "asof": asof,
            "prediction_rows": int(prediction.shape[0]),
            "asof_aware_universe": bool(asof_aware),
            "candidate_universe_count": len(symbols),
            "active_universe_count": len(active_symbols),
            "excluded_universe_count": len(excluded_symbols),
            "top30_rows": int(top30.shape[0]),
            "top50_rows": int(top50.shape[0]),
            "finite_prediction_share": stats["finite_count"] / stats["count"] if stats["count"] else 0.0,
            "score_distribution": stats,
            "top30_path": str(Path(run_id) / "top30_signals.csv"),
            "top50_path": str(Path(run_id) / "top50_signals.csv"),
            "recorder_id": RECORDER_ID,
            "diagnostic_only": True,
            "research_signal_not_order": True,
            "paper_trading_started": False,
            "live_trading_started": False,
            "target_trades_generated": False,
            "executable_orders_generated": False,
            "historical_backfill": True,
        }
        write_json(artifacts["signal_summary"], signal_summary)
    except Exception as exc:
        if not errors:
            errors.append(str(exc))
        signal_summary = {
            "status": status,
            "asof": asof,
            "prediction_generated": False,
            "top30_generated": False,
            "top50_generated": False,
            "errors": errors,
            "asof_aware_universe": bool(asof_aware),
            "candidate_universe_count": len(symbols),
            "active_universe_count": len(active_symbols),
            "excluded_universe_count": len(excluded_symbols),
            "excluded_symbols": excluded_symbols,
            "diagnostic_only": True,
            "research_signal_not_order": True,
            "historical_backfill": True,
        }
        write_json(artifacts["signal_summary"], signal_summary)
    finally:
        metadata = {
            "run_id": run_id,
            "created_at": utc_now(),
            "status": status,
            "asof": asof,
            "dry_run": False,
            "allow_refresh": False,
            "historical_backfill": True,
            "asof_aware_universe": bool(asof_aware),
            "candidate_universe_count": len(symbols),
            "active_universe_count": len(active_symbols),
            "excluded_universe_count": len(excluded_symbols),
            "excluded_symbols": excluded_symbols,
            "formal_validation_bypassed_for_research_only": bool(research_only_skip_formal_validation),
            "frozen_recorder": RECORDER_ID,
            "recorder_path": rel(RECORDER_DIR),
            "model_path": rel(MODEL_PATH),
            "config": rel(CONFIG_PATH),
            "provider_uri": rel(OPTION_C_PROVIDER),
            "normalized_source": rel(OPTION_C_NORMALIZED),
            "market": MARKET,
            "benchmark": BENCHMARK,
            "errors": errors,
            "latest_signal_updated": False,
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
            "artifacts": {},
        }
        artifacts["artifact_manifest"] = run_dir / "artifact_manifest.json"
        metadata["artifacts"] = {key: rel(path) for key, path in sorted(artifacts.items())}
        write_json(artifacts["run_metadata"], metadata)
        (run_dir / "implementation_report.md").write_text(
            "\n".join([
                "# Historical Backfill Signal Run",
                "",
                f"- run_id: `{run_id}`",
                f"- asof: `{asof}`",
                f"- status: `{status}`",
                "- latest_signal_updated: `False`",
                "- research_signal_not_order: `True`",
            ]) + "\n",
            encoding="utf-8",
        )
        write_manifest(run_dir, status, artifacts)
    return {
        "asof": asof,
        "run_id": run_id,
        "status": status,
        "run_dir": rel(run_dir),
        "errors": errors,
        "active_universe_count": len(active_symbols),
        "excluded_universe_count": len(excluded_symbols),
        "excluded_symbols": excluded_symbols,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill historical Option C qlib signals for read-only replay.")
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--batch-id", default="")
    parser.add_argument("--max-days", type=int, default=0, help="Optional cap for smoke runs.")
    parser.add_argument("--dry-run", action="store_true", help="List trading days only; do not generate signal artifacts.")
    parser.add_argument("--no-skip-existing", action="store_true", help="Regenerate existing run directories in this batch.")
    parser.add_argument("--research-only-skip-formal-validation", action="store_true", help="Bypass formal source asof validation for older historical stress tests. Research-only; never production evidence.")
    parser.add_argument("--asof-aware-universe", action="store_true", help="Filter static accepted universe to symbols visible in the dedicated Option C source at each asof.")
    args = parser.parse_args()

    start = parse_date(args.start_date)
    end = parse_date(args.end_date)
    if end < start:
        start, end = end, start
    days = trading_days(start, end)
    if args.max_days and args.max_days > 0:
        days = days[: args.max_days]
    batch_id = args.batch_id or f"option_c_historical_backfill_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}"
    output_root = Path(args.output_root).expanduser().resolve(strict=False)
    batch_root = safe_batch_root(output_root, batch_id)
    payload: dict[str, Any] = {
        "ok": True,
        "status": "dry_run" if args.dry_run else "running",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "batch_id": batch_root.name,
        "output_root": rel(batch_root),
        "trading_days": days,
        "trading_day_count": len(days),
        "generated_count": 0,
        "skipped_existing_count": 0,
        "failed_count": 0,
        "latest_signal_updated": False,
        "refresh_triggered": False,
        "publish_triggered": False,
        "provider_mutation_triggered": False,
        "research_signal_not_order": True,
        "formal_validation_bypassed_for_research_only": bool(args.research_only_skip_formal_validation),
        "asof_aware_universe": bool(args.asof_aware_universe),
    }
    if args.dry_run:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    batch_root.mkdir(parents=True, exist_ok=True)
    symbols = accepted_prediction_universe()
    results = []
    for asof in days:
        item = generate_one(
            asof,
            batch_root=batch_root,
            batch_id=batch_root.name,
            symbols=symbols,
            skip_existing=not args.no_skip_existing,
            research_only_skip_formal_validation=bool(args.research_only_skip_formal_validation),
            asof_aware=bool(args.asof_aware_universe),
        )
        results.append(item)
        if item["status"] == "accepted":
            payload["generated_count"] += 1
        elif item["status"] == "skipped_existing":
            payload["skipped_existing_count"] += 1
        else:
            payload["failed_count"] += 1
    payload["status"] = "accepted" if payload["failed_count"] == 0 else "completed_with_failures"
    payload["results"] = results
    write_json(batch_root / "backfill_summary.json", payload)
    write_report(batch_root, payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload["failed_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
