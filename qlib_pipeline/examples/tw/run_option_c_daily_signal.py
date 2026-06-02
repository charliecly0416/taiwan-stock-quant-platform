from __future__ import annotations

import argparse
import json
import pickle
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.tw.run_option_c_daily_prediction import (  # noqa: E402
    BENCHMARK,
    CONFIG_PATH,
    MARKET,
    MODEL_PATH,
    NORMALIZED_DIR,
    RECORDER_DIR,
    RECORDER_ID,
    REJECTED_FIELDS,
    RESEARCH_PROVIDER,
    UNIVERSE_PATH,
    alpha158_names,
    latest_local_date,
    rejected_hits,
    rel,
    score_stats,
    sha256_file,
    utc_now,
    write_json,
)
import qlib  # noqa: E402
from qlib.contrib.model.gbdt import LGBModel  # noqa: E402
from qlib.data.dataset import DatasetH  # noqa: E402


OUT_ROOT = ROOT / "data_tw/experiments/option_c_daily_signal"
REPORT_PATH = ROOT / "docs/tw_audit/165_option_c_daily_signal_wrapper_v2_report.md"
REQUIRED_FIELDS = {"open", "high", "low", "close", "volume", "vwap", "factor"}
ACCEPTED_PREDICTION_UNIVERSE_PATH = (
    ROOT / "data_tw/experiments/option_c_forward_validation/timed_data_availability_retry_20260601T101323Z/symbols_accepted_prediction_universe.txt"
)


def provider_calendar_max(provider: Path = RESEARCH_PROVIDER) -> str | None:
    path = provider / "calendars/day.txt"
    if not path.exists():
        return None
    rows = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return max(rows) if rows else None


def accepted_prediction_universe() -> list[str]:
    if not ACCEPTED_PREDICTION_UNIVERSE_PATH.exists():
        raise FileNotFoundError(f"accepted prediction universe missing: {rel(ACCEPTED_PREDICTION_UNIVERSE_PATH)}")
    symbols = [line.strip() for line in ACCEPTED_PREDICTION_UNIVERSE_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(symbols) != len(set(symbols)):
        raise ValueError(f"accepted prediction universe has duplicate symbols: {rel(ACCEPTED_PREDICTION_UNIVERSE_PATH)}")
    return sorted(symbols)


def source_symbol_summary(asof: str, symbols: list[str]) -> dict[str, Any]:
    rows = []
    missing_files = []
    missing_asof = []
    for symbol in symbols:
        path = NORMALIZED_DIR / f"{symbol}.csv"
        if not path.exists():
            missing_files.append(symbol)
            continue
        try:
            dates = pd.read_csv(path, usecols=["date"])["date"].astype(str)
        except Exception:
            missing_files.append(symbol)
            continue
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


def provider_field_inventory(symbols: list[str]) -> dict[str, Any]:
    counts = {field: 0 for field in sorted(REQUIRED_FIELDS)}
    unexpected: set[str] = set()
    missing_symbols = []
    for symbol in symbols:
        feature_dir = RESEARCH_PROVIDER / "features" / symbol.lower()
        if not feature_dir.exists():
            missing_symbols.append(symbol)
            continue
        fields = {p.name.split(".")[0] for p in feature_dir.glob("*.day.bin")}
        for field in fields:
            if field in counts:
                counts[field] += 1
            else:
                unexpected.add(field)
    rejected = sorted((set(counts) | unexpected) & REJECTED_FIELDS)
    return {
        "expected_field_counts": counts,
        "unexpected_fields": sorted(unexpected),
        "rejected_fields_present": rejected,
        "missing_feature_symbols": missing_symbols,
        "status": "pass"
        if not rejected and not unexpected and not missing_symbols and all(v == len(symbols) for v in counts.values())
        else "fail",
    }


def git_staged_paths() -> list[str]:
    result = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=ROOT, text=True, stdout=subprocess.PIPE, check=False)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def formal_validation(asof: str, symbols: list[str]) -> dict[str, Any]:
    source = source_symbol_summary(asof, symbols)
    calendar_max = provider_calendar_max()
    inventory = provider_field_inventory(symbols)
    handler_rejected = rejected_hits(alpha158_names())
    staged = git_staged_paths()
    staged_provider_tree = [
        path
        for path in staged
        if "clean_forward_provider/" in path or "qlib_bin/features/" in path or "qlib_bin/calendars/" in path
    ]
    errors = []
    if source["symbols_with_asof"] != len(symbols):
        errors.append("formal_source_missing_asof")
    if calendar_max is None or calendar_max < asof:
        errors.append("formal_provider_calendar_stale")
    if not symbols:
        errors.append("empty_active_universe")
    if inventory["status"] != "pass":
        errors.append("provider_field_inventory_failed")
    if handler_rejected:
        errors.append("handler_rejected_fields_present")
    if staged_provider_tree:
        errors.append("provider_tree_staged_for_commit")
    return {
        "status": "pass" if not errors else "fail",
        "asof": asof,
        "errors": errors,
        "universe_source": rel(ACCEPTED_PREDICTION_UNIVERSE_PATH),
        "formal_source": source,
        "provider_calendar_max": calendar_max,
        "active_universe_count": len(symbols),
        "provider_field_inventory": inventory,
        "handler_rejected_hits": handler_rejected,
        "staged_provider_tree_paths": staged_provider_tree,
    }


def generate_prediction_for_symbols(provider: Path, asof: str, symbols: list[str]) -> pd.DataFrame:
    qlib.init(provider_uri=str(provider), region="tw", expression_cache=None, dataset_cache=None)
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


def artifact_entry(path: Path, key: str, committed_expected: bool, required: bool, local_only: bool = False) -> dict[str, Any]:
    exists = path.exists()
    return {
        "key": key,
        "path": rel(path),
        "exists": exists,
        "size_bytes": path.stat().st_size if exists and path.is_file() else None,
        "sha256": sha256_file(path) if exists and path.is_file() else None,
        "committed_expected": committed_expected,
        "required_for_acceptance": required,
        "local_only": local_only,
    }


def write_manifest(run_dir: Path, status: str, artifacts: dict[str, Path]) -> None:
    manifest = run_dir / "artifact_manifest.json"
    entries = [
        artifact_entry(path, key, committed_expected=False, required=True, local_only=True)
        for key, path in sorted(artifacts.items())
        if key != "artifact_manifest"
    ]
    entries.append(
        {
            "key": "artifact_manifest",
            "path": rel(manifest),
            "exists": True,
            "size_bytes": None,
            "sha256": None,
            "committed_expected": False,
            "required_for_acceptance": True,
            "local_only": True,
            "self_sha256_note": "omitted to avoid self-referential hashing",
        }
    )
    write_json(
        manifest,
        {
            "run_id": run_dir.name,
            "created_at": utc_now(),
            "status": status,
            "schema_version": 1,
            "entries": entries,
        },
    )


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def latest_dry_run_evidence(output_root: Path, current_run_dir: Path) -> dict[str, Any]:
    candidates: list[tuple[float, Path]] = []
    for path in output_root.glob("option_c_daily_signal_*/run_metadata.json"):
        run_dir = path.parent
        if run_dir == current_run_dir:
            continue
        try:
            meta = load_json(path)
        except Exception:
            continue
        if meta.get("dry_run") is True and meta.get("status") == "dry_run_preflight_pass":
            candidates.append((path.stat().st_mtime, run_dir))
    if not candidates:
        return {
            "status": "not_found",
            "note": "run --dry-run before normal mode to attach dry-run evidence",
        }
    run_dir = max(candidates, key=lambda item: item[0])[1]
    preflight_path = run_dir / "preflight_status.json"
    validation_path = run_dir / "formal_validation.json"
    summary_path = run_dir / "signal_summary.json"
    meta_path = run_dir / "run_metadata.json"
    summary = load_json(summary_path) if summary_path.exists() else {}
    metadata = load_json(meta_path) if meta_path.exists() else {}
    return {
        "status": "found",
        "dry_run_run_id": run_dir.name,
        "dry_run_status": metadata.get("status"),
        "dry_run_preflight_path": rel(preflight_path),
        "dry_run_formal_validation_path": rel(validation_path),
        "dry_run_signal_summary_path": rel(summary_path),
        "dry_run_mutation_flags": {
            "formal_source_mutated": False,
            "formal_provider_mutated": False,
            "latest_signal_updated": False,
        },
        "prediction_generated": bool(summary.get("prediction_generated", False)),
        "top30_generated": bool(summary.get("top30_generated", False)),
        "top50_generated": bool(summary.get("top50_generated", False)),
    }


def latest_wait_state_evidence(output_root: Path, current_run_dir: Path) -> dict[str, Any]:
    candidates: list[tuple[float, Path]] = []
    for path in output_root.glob("option_c_daily_signal_*/run_metadata.json"):
        run_dir = path.parent
        if run_dir == current_run_dir:
            continue
        try:
            meta = load_json(path)
        except Exception:
            continue
        if meta.get("status") == "wait_state_data_refresh_needed":
            candidates.append((path.stat().st_mtime, run_dir))
    if not candidates:
        return {
            "status": "not_found",
            "note": "run --asof <future-date> --dry-run to document stale-data wait-state evidence",
        }
    run_dir = max(candidates, key=lambda item: item[0])[1]
    refresh_path = run_dir / "data_refresh_status.json"
    preflight_path = run_dir / "preflight_status.json"
    validation_path = run_dir / "formal_validation.json"
    meta_path = run_dir / "run_metadata.json"
    metadata = load_json(meta_path) if meta_path.exists() else {}
    refresh = load_json(refresh_path) if refresh_path.exists() else {}
    return {
        "status": "found",
        "wait_state_run_id": run_dir.name,
        "wait_state_status": metadata.get("status"),
        "wait_state_asof": metadata.get("asof"),
        "wait_state_preflight_path": rel(preflight_path),
        "wait_state_formal_validation_path": rel(validation_path),
        "wait_state_data_refresh_status_path": rel(refresh_path),
        "refresh_branch": refresh.get("refresh_branch"),
        "allow_refresh": refresh.get("allow_refresh"),
        "formal_source_mutated": bool(refresh.get("formal_source_mutated", False)),
        "formal_provider_mutated": bool(refresh.get("formal_provider_mutated", False)),
        "yahoo_scrapling_refresh_performed": bool(refresh.get("yahoo_scrapling_refresh_performed", False)),
        "expected_next_action": refresh.get("expected_next_action"),
    }


def signal_frame(prediction: pd.DataFrame, asof: str, top_n: int) -> pd.DataFrame:
    frame = prediction.reset_index()
    if "datetime" not in frame.columns or "instrument" not in frame.columns:
        raise ValueError("prediction index must reset to datetime,instrument columns")
    frame = frame.sort_values("score", ascending=False).head(top_n).copy()
    frame.insert(0, "asof", asof)
    frame["rank"] = range(1, len(frame) + 1)
    frame["source_model_recorder"] = RECORDER_ID
    frame["diagnostic_only"] = True
    frame["research_signal_not_order"] = True
    return frame[["asof", "instrument", "score", "rank", "source_model_recorder", "diagnostic_only", "research_signal_not_order"]]


def write_report(report_path: Path, run_dir: Path, status: str, metadata: dict[str, Any], signal_summary: dict[str, Any]) -> None:
    lines = [
        "---",
        f"created_at: {utc_now()}",
        f"status: {status}",
        "scope: option_c_daily_signal_wrapper_implementation_report",
        "related_work_order:",
        "  - docs/tw_audit/161_option_c_daily_signal_wrapper_work_order.md",
        "  - docs/tw_audit/164_option_c_daily_signal_wrapper_v2_optimization_work_order.md",
        "run_dir:",
        f"  - {rel(run_dir)}",
        "---",
        "",
        "# Option C Daily Signal Wrapper V2 Report",
        "",
        "## Summary",
        "",
        f"- run_id: `{run_dir.name}`",
        f"- status: `{status}`",
        f"- asof: `{metadata.get('asof')}`",
        f"- dry_run: `{str(metadata.get('dry_run')).lower()}`",
        f"- frozen_recorder: `{RECORDER_ID}`",
        f"- config: `{rel(CONFIG_PATH)}`",
        f"- provider: `{rel(RESEARCH_PROVIDER)}`",
        f"- market: `{MARKET}`",
        f"- benchmark: `{BENCHMARK}`",
        f"- top30_signals: `{signal_summary.get('top30_path', 'not_generated')}`",
        f"- top50_signals: `{signal_summary.get('top50_path', 'not_generated')}`",
        "",
        "## Dry-Run Evidence",
        "",
        f"- dry_run_run_id: `{metadata.get('dry_run_evidence', {}).get('dry_run_run_id', 'not_found')}`",
        f"- dry_run_status: `{metadata.get('dry_run_evidence', {}).get('dry_run_status', metadata.get('status') if metadata.get('dry_run') else 'not_found')}`",
        f"- dry_run_preflight_path: `{metadata.get('dry_run_evidence', {}).get('dry_run_preflight_path', metadata.get('artifacts', {}).get('preflight_status', 'not_found'))}`",
        f"- dry_run_formal_validation_path: `{metadata.get('dry_run_evidence', {}).get('dry_run_formal_validation_path', metadata.get('artifacts', {}).get('formal_validation', 'not_found'))}`",
        f"- dry_run_mutation_flags: `{json.dumps(metadata.get('dry_run_evidence', {}).get('dry_run_mutation_flags', {'formal_source_mutated': False, 'formal_provider_mutated': False, 'latest_signal_updated': False}), sort_keys=True)}`",
        f"- prediction_generated: `{str(metadata.get('dry_run_evidence', {}).get('prediction_generated', False)).lower()}`",
        "",
        "## Stale-Data Evidence",
        "",
        f"- wait_state_run_id: `{metadata.get('stale_data_evidence', {}).get('wait_state_run_id', 'not_found')}`",
        f"- wait_state_status: `{metadata.get('stale_data_evidence', {}).get('wait_state_status', 'not_found')}`",
        f"- wait_state_asof: `{metadata.get('stale_data_evidence', {}).get('wait_state_asof', 'not_found')}`",
        f"- wait_state_data_refresh_status_path: `{metadata.get('stale_data_evidence', {}).get('wait_state_data_refresh_status_path', 'not_found')}`",
        f"- refresh_branch: `{metadata.get('stale_data_evidence', {}).get('refresh_branch', 'not_found')}`",
        f"- yahoo_scrapling_refresh_performed: `{str(metadata.get('stale_data_evidence', {}).get('yahoo_scrapling_refresh_performed', False)).lower()}`",
        f"- formal_source_mutated: `{str(metadata.get('stale_data_evidence', {}).get('formal_source_mutated', False)).lower()}`",
        f"- formal_provider_mutated: `{str(metadata.get('stale_data_evidence', {}).get('formal_provider_mutated', False)).lower()}`",
        "",
        "## V2 Policies",
        "",
        f"- universe_policy: `{metadata.get('universe_policy')}`",
        f"- stale_data_policy: `{metadata.get('stale_data_policy')}`",
        f"- formal_refresh_gate: `{metadata.get('formal_refresh_gate')}`",
        f"- artifact_retention_policy: `{metadata.get('artifact_retention_policy')}`",
        "",
        "## Decision",
        "",
        "This is a research signal output, not an order file.",
        "No paper/live trading was started.",
        "No target trades or executable orders were generated.",
        "No model retraining, tuning, strategy change, provider switch, FinMind fallback, or mixed-provider fill was performed.",
        "Daily run artifacts are local operational outputs unless a separate packaging/commit work order is reviewed.",
        "latest_signal.json is a pointer only and is updated only for accepted normal runs.",
        "",
        "## Artifacts",
        "",
    ]
    for key, value in sorted(metadata.get("artifacts", {}).items()):
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Stop Point", "", "This report is the next review stop point."])
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Option C daily research signal wrapper.")
    parser.add_argument("--asof", default=None, help="Explicit signal asof date for review/testing.")
    parser.add_argument("--max-workers", type=int, default=8, help="Reserved for compatibility with daily prediction runner.")
    parser.add_argument("--dry-run", action="store_true", help="Run preflight/formal validation only; do not generate predictions.")
    parser.add_argument("--allow-refresh", action="store_true", help="Reserved guard for future Yahoo-only refresh; v2 Branch A still stops stale data as wait-state.")
    parser.add_argument("--output-root", default=str(OUT_ROOT))
    parser.add_argument("--report-path", default=str(REPORT_PATH))
    args = parser.parse_args()

    output_root = Path(args.output_root)
    if not output_root.is_absolute():
        output_root = ROOT / output_root
    report_path = Path(args.report_path)
    if not report_path.is_absolute():
        report_path = ROOT / report_path
    output_root.mkdir(parents=True, exist_ok=True)

    local_max = latest_local_date()
    asof = args.asof or local_max
    run_id = f"option_c_daily_signal_{asof.replace('-', '')}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    artifacts: dict[str, Path] = {
        "run_metadata": run_dir / "run_metadata.json",
        "preflight_status": run_dir / "preflight_status.json",
        "formal_validation": run_dir / "formal_validation.json",
        "signal_summary": run_dir / "signal_summary.json",
        "implementation_report": run_dir / "implementation_report.md",
    }
    status = "failed"
    errors: list[str] = []
    signal_summary: dict[str, Any] = {}

    try:
        symbols = accepted_prediction_universe()
        calendar_max = provider_calendar_max()
        preflight = {
            "created_at": utc_now(),
            "current_utc_time": utc_now(),
            "dry_run": args.dry_run,
            "allow_refresh": args.allow_refresh,
            "latest_local_normalized_source_date": local_max,
            "latest_formal_provider_calendar_date": calendar_max,
            "latest_active_universe_date_coverage": "accepted_prediction_universe_symbol_list",
            "active_universe_source": rel(ACCEPTED_PREDICTION_UNIVERSE_PATH),
            "expected_signal_asof_date": asof,
            "explicit_asof": args.asof,
            "active_universe_count": len(symbols),
            "data_refresh_needed": local_max < asof or calendar_max is None or calendar_max < asof,
            "data_refresh_policy": "v2_branch_a_wait_state_only; --allow-refresh is a reviewed guard but does not mutate data/provider in this implementation",
            "formal_refresh_gate_policy": "prediction requires candidate pass, 150-symbol coverage, OHLCV sanity, formal source/provider asof coverage, expected fields, no rejected PA-57 fields, and no staged provider-bin tree",
        }
        write_json(artifacts["preflight_status"], preflight)
        refresh_path = run_dir / ("data_refresh_skipped.json" if not preflight["data_refresh_needed"] else "data_refresh_status.json")
        artifacts["data_refresh_skipped" if not preflight["data_refresh_needed"] else "data_refresh_status"] = refresh_path
        write_json(
            refresh_path,
            {
                "created_at": utc_now(),
                "status": "skipped_fresh_enough" if not preflight["data_refresh_needed"] else "wait_state_refresh_not_executed",
                "reason": "formal source/provider already cover selected asof"
                if not preflight["data_refresh_needed"]
                else "selected asof is not covered; v2 Branch A stops as wait-state and does not mutate formal data/provider",
                "allow_refresh": args.allow_refresh,
                "refresh_branch": "branch_a_wait_state_only",
                "expected_next_action": "run a separately reviewed Yahoo-only refresh candidate/formal refresh work order if fresh data is required"
                if preflight["data_refresh_needed"]
                else "none",
                "formal_refresh_gate": {
                    "candidate_yahoo_refresh_status_pass_required": True,
                    "symbol_coverage_150_required": True,
                    "ohlcv_sanity_pass_required": True,
                    "formal_source_asof_coverage_required": True,
                    "formal_provider_calendar_asof_coverage_required": True,
                    "expected_fields_required": sorted(REQUIRED_FIELDS),
                    "pa57_rejected_fields_absent_required": True,
                    "provider_bin_tree_not_staged_required": True,
                },
                "yahoo_scrapling_refresh_performed": False,
                "formal_provider_mutated": False,
                "formal_source_mutated": False,
                "FinMind_fallback_used": False,
                "mixed_provider_fill_used": False,
            },
        )

        validation = formal_validation(asof, symbols)
        write_json(artifacts["formal_validation"], validation)
        if preflight["data_refresh_needed"]:
            status = "wait_state_data_refresh_needed"
            errors.append("data refresh needed before signal generation")
            raise RuntimeError(errors[-1])
        if validation["status"] != "pass":
            status = "blocked_formal_validation_failed"
            errors.extend(validation.get("errors", []))
            raise RuntimeError("formal validation failed")
        if args.dry_run:
            status = "dry_run_preflight_pass"
            signal_summary = {
                "status": status,
                "prediction_generated": False,
                "top30_generated": False,
                "top50_generated": False,
                "formal_source_mutated": False,
                "formal_provider_mutated": False,
                "latest_signal_updated": False,
                "reason": "dry-run mode stops after preflight/formal validation",
            }
            write_json(artifacts["signal_summary"], signal_summary)
        else:
            prediction = generate_prediction_for_symbols(RESEARCH_PROVIDER, asof, symbols)
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
                "diagnostic_only": True,
                "research_signal_not_order": True,
                "paper_trading_started": False,
                "live_trading_started": False,
                "target_trades_generated": False,
                "executable_orders_generated": False,
            }
            write_json(artifacts["signal_summary"], signal_summary)
            latest_path = output_root / "latest_signal.json"
            write_json(
                latest_path,
                {
                    "created_at": utc_now(),
                    "run_dir": rel(run_dir),
                    "asof": asof,
                    "top30_signals": rel(top30_path),
                    "top50_signals": rel(top50_path),
                    "diagnostic_only": True,
                    "research_signal_not_order": True,
                },
            )
    except Exception as exc:
        if status == "failed":
            status = "failed"
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
            "dry_run": args.dry_run,
            "allow_refresh": args.allow_refresh,
            "command": " ".join(sys.argv),
            "max_workers": args.max_workers,
            "frozen_recorder": RECORDER_ID,
            "recorder_path": rel(RECORDER_DIR),
            "model_path": rel(MODEL_PATH),
            "config": rel(CONFIG_PATH),
            "provider_uri": rel(RESEARCH_PROVIDER),
            "market": MARKET,
            "benchmark": BENCHMARK,
            "errors": errors,
            "paper_trading_started": False,
            "live_trading_started": False,
            "target_trades_generated": False,
            "executable_orders_generated": False,
            "model_retraining_performed": False,
            "model_tuning_performed": False,
            "provider_switch_performed": False,
            "FinMind_fallback_used": False,
            "mixed_provider_fill_used": False,
            "universe_policy": "default accepted 150-symbol Option C prediction universe; formal tw_liquid_dyn as-of membership is future-only and not enabled",
            "stale_data_policy": "Branch A wait-state only; no Yahoo/Scrapling refresh or formal source/provider mutation in v2 without a separate reviewed implementation",
            "formal_refresh_gate": "documented guard: candidate pass, 150-symbol coverage, OHLCV sanity, formal source/provider asof coverage, expected fields, PA-57 absent, provider-bin not staged",
            "artifact_retention_policy": "daily run artifacts are local operational outputs by default; latest_signal.json is a pointer only; packaging/commit requires separate review",
            "artifacts": {},
        }
        artifacts["artifact_manifest"] = run_dir / "artifact_manifest.json"
        metadata["artifacts"] = {key: rel(path) for key, path in sorted(artifacts.items())}
        if args.dry_run:
            metadata["dry_run_evidence"] = {
                "status": "self",
                "dry_run_run_id": run_id,
                "dry_run_status": status,
                "dry_run_preflight_path": metadata["artifacts"].get("preflight_status"),
                "dry_run_formal_validation_path": metadata["artifacts"].get("formal_validation"),
                "dry_run_signal_summary_path": metadata["artifacts"].get("signal_summary"),
                "dry_run_mutation_flags": {
                    "formal_source_mutated": False,
                    "formal_provider_mutated": False,
                    "latest_signal_updated": False,
                },
                "prediction_generated": False,
                "top30_generated": False,
                "top50_generated": False,
            }
        else:
            metadata["dry_run_evidence"] = latest_dry_run_evidence(output_root, run_dir)
        metadata["stale_data_evidence"] = latest_wait_state_evidence(output_root, run_dir)
        write_json(artifacts["run_metadata"], metadata)
        write_report(artifacts["implementation_report"], run_dir, status, metadata, signal_summary)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(artifacts["implementation_report"].read_text(encoding="utf-8"), encoding="utf-8")
        write_manifest(run_dir, status, artifacts)
        print(json.dumps({"run_id": run_id, "status": status, "run_dir": rel(run_dir), "errors": errors}, indent=2))
    return 0 if status in {"accepted", "dry_run_preflight_pass", "wait_state_data_refresh_needed", "blocked_formal_validation_failed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
