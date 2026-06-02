#!/usr/bin/env python3
"""Fixed-scope Option C daily signal validation against the dedicated provider.

This wrapper accepts only dry-run or normal modes for the dedicated Option C
provider. It does not accept arbitrary provider paths and never writes
latest_signal.json, refreshes data, publishes providers, or connects to trading.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.tw.run_option_c_daily_signal import (  # noqa: E402
    OUT_ROOT as ACCEPTED_SIGNAL_ROOT,
    REQUIRED_FIELDS,
    accepted_prediction_universe,
    artifact_entry,
    latest_wait_state_evidence,
    signal_frame,
    write_manifest,
)
from examples.tw.run_option_c_daily_prediction import (  # noqa: E402
    BENCHMARK,
    CONFIG_PATH,
    MARKET,
    MODEL_PATH,
    RECORDER_DIR,
    RECORDER_ID,
    alpha158_names,
    rejected_hits,
    rel,
    score_stats,
    write_json,
)

OPTION_C_PROVIDER = ROOT / "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin"
OPTION_C_NORMALIZED = ROOT / "data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized"
OUT_ROOT = ROOT / "data_tw/experiments/option_c_daily_signal_option_c_provider"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def provider_calendar_max(provider: Path = OPTION_C_PROVIDER) -> str | None:
    path = provider / "calendars/day.txt"
    if not path.exists():
        return None
    rows = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return max(rows) if rows else None


def provider_field_inventory(symbols: list[str]) -> dict[str, Any]:
    counts = {field: 0 for field in sorted(REQUIRED_FIELDS)}
    unexpected: set[str] = set()
    missing_symbols: list[str] = []
    for symbol in symbols:
        feature_dir = OPTION_C_PROVIDER / "features" / symbol.lower()
        if not feature_dir.exists():
            missing_symbols.append(symbol)
            continue
        fields = {p.name.split(".")[0] for p in feature_dir.glob("*.day.bin")}
        for field in fields:
            if field in counts:
                counts[field] += 1
            else:
                unexpected.add(field)
    return {
        "expected_field_counts": counts,
        "unexpected_fields": sorted(unexpected),
        "missing_feature_symbols": missing_symbols,
        "status": "pass" if not unexpected and not missing_symbols and all(v == len(symbols) for v in counts.values()) else "fail",
    }


def source_symbol_summary(asof: str, symbols: list[str]) -> dict[str, Any]:
    import pandas as pd
    rows = []
    missing_files = []
    missing_asof = []
    for symbol in symbols:
        path = OPTION_C_NORMALIZED / f"{symbol}.csv"
        if not path.exists():
            missing_files.append(symbol)
            continue
        dates = pd.read_csv(path, usecols=["date"])["date"].astype(str)
        date_max = str(dates.max()) if not dates.empty else None
        has_asof = bool((dates == asof).any())
        if not has_asof:
            missing_asof.append(symbol)
        rows.append({"instrument": symbol, "date_max": date_max, "has_asof": has_asof})
    frame = pd.DataFrame(rows)
    return {
        "symbols_expected": len(symbols),
        "symbols_found": len(rows),
        "symbols_with_asof": int(frame["has_asof"].sum()) if not frame.empty else 0,
        "min_date_max": str(frame["date_max"].min()) if not frame.empty else None,
        "max_date_max": str(frame["date_max"].max()) if not frame.empty else None,
        "missing_files": missing_files,
        "missing_asof": missing_asof,
    }


def formal_validation(asof: str, symbols: list[str]) -> dict[str, Any]:
    source = source_symbol_summary(asof, symbols)
    calendar_max = provider_calendar_max()
    inventory = provider_field_inventory(symbols)
    handler_rejected = rejected_hits(alpha158_names())
    errors = []
    if source["symbols_with_asof"] != len(symbols):
        errors.append("option_c_formal_source_missing_asof")
    if calendar_max is None or calendar_max < asof:
        errors.append("option_c_provider_calendar_stale")
    if inventory["status"] != "pass":
        errors.append("option_c_provider_field_inventory_failed")
    if handler_rejected:
        errors.append("handler_rejected_fields_present")
    return {
        "status": "pass" if not errors else "fail",
        "asof": asof,
        "errors": errors,
        "provider_uri": rel(OPTION_C_PROVIDER),
        "normalized_source": rel(OPTION_C_NORMALIZED),
        "active_universe_count": len(symbols),
        "formal_source": source,
        "provider_calendar_max": calendar_max,
        "provider_field_inventory": inventory,
        "handler_rejected_hits": handler_rejected,
    }


def generate_prediction_for_symbols(asof: str, symbols: list[str]):
    """Generate predictions from the fixed dedicated Option C provider only."""
    import pickle

    import qlib
    from qlib.contrib.model.gbdt import LGBModel
    from qlib.data.dataset import DatasetH

    qlib.init(provider_uri=str(OPTION_C_PROVIDER), region="tw", expression_cache=None, dataset_cache=None)
    handler_conf = {
        "class": "Alpha158",
        "module_path": "qlib.contrib.data.handler",
        "kwargs": {
            "start_time": "2015-05-04",
            "end_time": asof,
            "fit_start_time": "2015-05-04",
            "fit_end_time": "2020-12-31",
            "instruments": sorted(symbols),
        },
    }
    dataset = DatasetH(handler=handler_conf, segments={"snapshot": (asof, asof)})
    model = pickle.load(MODEL_PATH.open("rb"))
    if not isinstance(model, LGBModel):
        raise TypeError(f"unexpected model type: {type(model)}")
    pred = model.predict(dataset, segment="snapshot")
    return pred.rename("score").to_frame()


def latest_dry_run_evidence() -> dict[str, Any]:
    candidates: list[tuple[float, Path]] = []
    for path in OUT_ROOT.glob("option_c_provider_dry_run_*/run_metadata.json"):
        try:
            meta = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if meta.get("dry_run") is True and meta.get("status") == "dry_run_preflight_pass":
            candidates.append((path.stat().st_mtime, path.parent))
    if not candidates:
        return {"status": "not_found", "note": "run the dedicated Option C provider --dry-run before --normal"}
    run_dir = max(candidates, key=lambda item: item[0])[1]
    meta = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))
    return {
        "status": "found",
        "dry_run_run_id": run_dir.name,
        "dry_run_status": meta.get("status"),
        "dry_run_formal_validation_path": rel(run_dir / "formal_validation.json"),
        "dry_run_signal_summary_path": rel(run_dir / "signal_summary.json"),
        "dry_run_mutation_flags": {
            "formal_source_mutated": False,
            "formal_provider_mutated": False,
            "latest_signal_updated": False,
        },
    }


def write_normal_report(report_path: Path, run_dir: Path, metadata: dict[str, Any], signal_summary: dict[str, Any]) -> None:
    lines = [
        "---",
        f"created_at: {utc_now()}",
        f"status: {metadata.get('status')}",
        "scope: option_c_provider_daily_signal_normal_smoke_report",
        f"run_dir: {rel(run_dir)}",
        "---",
        "",
        "# Option C Provider Daily Signal Normal Smoke Report",
        "",
        f"- run_id: `{metadata.get('run_id')}`",
        f"- status: `{metadata.get('status')}`",
        f"- asof: `{metadata.get('asof')}`",
        f"- provider: `{metadata.get('provider_uri')}`",
        f"- normalized_source: `{metadata.get('normalized_source')}`",
        f"- frozen_recorder: `{metadata.get('frozen_recorder')}`",
        f"- top30_signals: `{signal_summary.get('top30_path', 'not_generated')}`",
        f"- top50_signals: `{signal_summary.get('top50_path', 'not_generated')}`",
        "",
        "This is a research signal artifact, not an order file.",
        "No refresh, provider publish, provider rebuild, model retraining, tuning, broker connection, or orders were performed.",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_normal(asof: str) -> int:
    symbols = accepted_prediction_universe()
    run_id = f"option_c_daily_signal_{asof.replace('-', '')}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    run_dir = ACCEPTED_SIGNAL_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    artifacts: dict[str, Path] = {
        "run_metadata": run_dir / "run_metadata.json",
        "formal_validation": run_dir / "formal_validation.json",
        "signal_summary": run_dir / "signal_summary.json",
        "implementation_report": run_dir / "implementation_report.md",
    }
    errors: list[str] = []
    status = "failed"
    signal_summary: dict[str, Any] = {}
    try:
        validation = formal_validation(asof, symbols)
        write_json(artifacts["formal_validation"], validation)
        if validation["status"] != "pass":
            status = "blocked_formal_validation_failed"
            errors.extend(validation.get("errors", []))
            raise RuntimeError("formal validation failed")
        prediction = generate_prediction_for_symbols(asof, symbols)
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
            "top30_rows": int(top30.shape[0]),
            "top50_rows": int(top50.shape[0]),
            "finite_prediction_share": stats["finite_count"] / stats["count"] if stats["count"] else 0.0,
            "score_distribution": stats,
            "top30_path": rel(top30_path),
            "top50_path": rel(top50_path),
            "recorder_id": RECORDER_ID,
            "diagnostic_only": True,
            "research_signal_not_order": True,
            "paper_trading_started": False,
            "live_trading_started": False,
            "target_trades_generated": False,
            "executable_orders_generated": False,
        }
        write_json(artifacts["signal_summary"], signal_summary)
    except Exception as exc:
        if not errors:
            errors.append(str(exc))
        signal_summary = {
            "status": status,
            "prediction_generated": False,
            "top30_generated": False,
            "top50_generated": False,
            "errors": errors,
            "diagnostic_only": True,
            "research_signal_not_order": True,
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
            "command": " ".join(sys.argv),
            "frozen_recorder": RECORDER_ID,
            "recorder_path": rel(RECORDER_DIR),
            "model_path": rel(MODEL_PATH),
            "config": rel(CONFIG_PATH),
            "provider_uri": rel(OPTION_C_PROVIDER),
            "normalized_source": rel(OPTION_C_NORMALIZED),
            "market": MARKET,
            "benchmark": BENCHMARK,
            "errors": errors,
            "dry_run_evidence": latest_dry_run_evidence(),
            "stale_data_evidence": latest_wait_state_evidence(ACCEPTED_SIGNAL_ROOT, run_dir),
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
        write_normal_report(artifacts["implementation_report"], run_dir, metadata, signal_summary)
        write_manifest(run_dir, status, artifacts)
        print(json.dumps({"run_id": run_id, "status": status, "run_dir": rel(run_dir), "errors": errors}, indent=2))
    return 0 if status == "accepted" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Fixed-scope Option C signal validation with dedicated Option C provider.")
    parser.add_argument("--asof", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Run preflight/formal validation only; do not generate predictions.")
    mode.add_argument("--normal", action="store_true", help="Generate accepted research signal artifacts from the fixed Option C provider; do not update latest_signal.json.")
    args = parser.parse_args()
    if args.normal:
        return run_normal(args.asof)
    symbols = accepted_prediction_universe()
    run_id = f"option_c_provider_dry_run_{args.asof.replace('-', '')}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    run_dir = OUT_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    validation = formal_validation(args.asof, symbols)
    status = "dry_run_preflight_pass" if validation["status"] == "pass" else "blocked_formal_validation_failed"
    payload = {
        "run_id": run_id,
        "created_at": utc_now(),
        "status": status,
        "asof": args.asof,
        "dry_run": True,
        "provider_scope": "option_c_150",
        "provider_uri": rel(OPTION_C_PROVIDER),
        "normalized_source": rel(OPTION_C_NORMALIZED),
        "recorder_id": RECORDER_ID,
        "model_path": rel(MODEL_PATH),
        "config_path": rel(CONFIG_PATH),
        "formal_validation": validation,
        "latest_signal_updated": False,
        "normal_signal_run": False,
        "refresh_triggered": False,
        "publish_triggered": False,
        "provider_mutation_triggered": False,
        "diagnostic_only": True,
        "research_signal_not_order": True,
    }
    write_json(run_dir / "run_metadata.json", payload)
    write_json(run_dir / "formal_validation.json", validation)
    write_json(run_dir / "signal_summary.json", {"status": status, "prediction_generated": False, "top30_generated": False, "top50_generated": False, "latest_signal_updated": False})
    print(json.dumps({"run_id": run_id, "status": status, "run_dir": rel(run_dir), "errors": validation.get("errors", [])}, indent=2))
    return 0 if status == "dry_run_preflight_pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
