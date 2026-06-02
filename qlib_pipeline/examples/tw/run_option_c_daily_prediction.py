from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import qlib
from qlib.contrib.data.loader import Alpha158DL
from qlib.contrib.model.gbdt import LGBModel
from qlib.data.dataset import DatasetH

from scripts.dump_bin import DumpDataAll


NORMALIZED_DIR = ROOT / "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"
RESEARCH_PROVIDER = ROOT / "data_tw/experiments/yahoo_adjusted_primary/qlib_bin"
UNIVERSE_PATH = ROOT / "data_tw/experiments/yahoo_adjusted_primary/universe/tw_liquid_dyn.txt"
RECORDER_DIR = ROOT / "mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a"
PRED_PATH = RECORDER_DIR / "artifacts/pred.pkl"
MODEL_PATH = RECORDER_DIR / "artifacts/params.pkl"
CONFIG_PATH = ROOT / "configs/tw_yahoo_primary_alpha158.yaml"
OUT_ROOT = ROOT / "data_tw/experiments/option_c_forward_smoke"
FORMAL_OUT_ROOT = ROOT / "data_tw/experiments/option_c_forward_validation"
REPORT_PATH = ROOT / "docs/tw_audit/54_option_c_min_daily_pipeline_report.md"
FORMAL_REPORT_PATH = ROOT / "docs/tw_audit/66_option_c_formal_forward_validation_first_snapshot_report.md"

RECORDER_ID = "950741cfd5f14ee5a05464fec3e12e0a"
EXPERIMENT_ID = "607910013167647574"
MARKET = "tw_liquid_dyn"
BENCHMARK = "TWII"
RESEARCH_START = "2023-01-01"
RESEARCH_END = "2025-06-30"
FREEZE_END = "2025-06-30"
REJECTED_FIELDS = {
    "tw_margin_util",
    "tw_margin_delta_5d",
    "tw_foreign_net_vol",
    "tw_trust_net_px",
    "tw_foreign_persist_5d",
    "tw_inst_consensus",
    "tw_idio_skew60",
}
INCLUDE_FIELDS = "open,high,low,close,volume,vwap"
BASELINE_COMMIT = "951fce62d9a1219a2cad9c8e4557e1bb3106f254"


class PipelineBlocker(RuntimeError):
    def __init__(self, category: str, message: str, next_action: str) -> None:
        super().__init__(message)
        self.category = category
        self.next_action = next_action


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def latest_local_date() -> str:
    latest: str | None = None
    for path in NORMALIZED_DIR.glob("TW*.csv"):
        try:
            dates = pd.read_csv(path, usecols=["date"])["date"].dropna()
        except Exception:
            continue
        if dates.empty:
            continue
        value = str(dates.iloc[-1])
        if latest is None or value > latest:
            latest = value
    if latest is None:
        raise PipelineBlocker(
            "missing_local_data",
            f"no local normalized CSV dates found in {rel(NORMALIZED_DIR)}",
            "restore normalized Yahoo adjusted primary CSV files before rerun",
        )
    return latest


def normalized_has_asof(asof: str) -> bool:
    for path in NORMALIZED_DIR.glob("TW*.csv"):
        try:
            dates = pd.read_csv(path, usecols=["date"])["date"].astype(str)
        except Exception:
            continue
        if (dates == asof).any():
            return True
    return False


def local_dates_after(asof: str) -> list[str]:
    values: set[str] = set()
    for path in NORMALIZED_DIR.glob("TW*.csv"):
        try:
            dates = pd.read_csv(path, usecols=["date"])["date"].astype(str)
        except Exception:
            continue
        values.update(d for d in dates if d > asof)
    return sorted(values)


def validate_inputs(asof: str, max_workers: int) -> None:
    if max_workers <= 0:
        raise PipelineBlocker("invalid_cli", "--max-workers must be positive", "rerun with --max-workers > 0")
    if not NORMALIZED_DIR.exists():
        raise PipelineBlocker("missing_local_data", f"normalized source directory missing: {rel(NORMALIZED_DIR)}", "restore local normalized data")
    if not any(NORMALIZED_DIR.glob("TW*.csv")):
        raise PipelineBlocker("missing_local_data", f"no TW*.csv files under {rel(NORMALIZED_DIR)}", "restore local normalized data")
    try:
        asof_ts = pd.Timestamp(asof)
    except Exception as exc:
        raise PipelineBlocker("invalid_asof", f"invalid --asof date {asof}: {exc}", "rerun with YYYY-MM-DD asof") from exc
    if asof_ts <= pd.Timestamp(FREEZE_END):
        raise PipelineBlocker(
            "pre_freeze_asof",
            f"asof {asof} is not post-freeze after {FREEZE_END}",
            "choose a local trading date after the research freeze boundary",
        )
    if not normalized_has_asof(asof):
        raise PipelineBlocker("missing_asof_data", f"asof {asof} not found in local normalized CSV data", "restore/update local data through the requested asof")
    missing = [p for p in [RECORDER_DIR, PRED_PATH, MODEL_PATH, CONFIG_PATH, UNIVERSE_PATH] if not p.exists()]
    if missing:
        detail = ", ".join(rel(p) for p in missing)
        raise PipelineBlocker("missing_frozen_artifact", f"required frozen artifacts missing: {detail}", "restore frozen model/config/universe artifacts")
    universe = active_universe(asof)
    if universe.empty:
        raise PipelineBlocker("empty_universe", f"no active universe members for {asof}", "restore or review universe file before rerun")
    OUT_ROOT.mkdir(parents=True, exist_ok=True)


def list_provider_fields(provider: Path) -> pd.DataFrame:
    rows = []
    features = provider / "features"
    for path in sorted(features.glob("*/*.day.bin")):
        rows.append({"instrument": path.parent.name.upper(), "field": path.name.removesuffix(".day.bin"), "path": rel(path)})
    return pd.DataFrame(rows)


def rejected_hits(fields: list[str]) -> list[str]:
    lowered = {f.lower().replace("$", "") for f in fields}
    return sorted(lowered & REJECTED_FIELDS)


def alpha158_names() -> list[str]:
    return list(Alpha158DL.get_feature_config()[1])


def active_universe(asof: str) -> pd.DataFrame:
    seg = pd.read_csv(
        UNIVERSE_PATH,
        sep="\t",
        names=["instrument", "start_datetime", "end_datetime"],
        parse_dates=["start_datetime", "end_datetime"],
    )
    dt = pd.Timestamp(asof)
    return seg[(seg["start_datetime"] <= dt) & (seg["end_datetime"] >= dt)].copy()


def score_stats(series: pd.Series) -> dict[str, float | int]:
    finite = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    out: dict[str, float | int] = {"count": int(series.shape[0]), "finite_count": int(finite.shape[0])}
    if finite.empty:
        for k in ["min", "p1", "p5", "p50", "p95", "p99", "max", "mean", "std"]:
            out[k] = float("nan")
        return out
    qs = finite.quantile([0.01, 0.05, 0.5, 0.95, 0.99])
    out.update(
        {
            "min": float(finite.min()),
            "p1": float(qs.loc[0.01]),
            "p5": float(qs.loc[0.05]),
            "p50": float(qs.loc[0.5]),
            "p95": float(qs.loc[0.95]),
            "p99": float(qs.loc[0.99]),
            "max": float(finite.max()),
            "mean": float(finite.mean()),
            "std": float(finite.std(ddof=0)),
        }
    )
    return out


def materialize_score_reference(run_dir: Path) -> dict[str, Any]:
    pred = pickle.load(PRED_PATH.open("rb"))
    if isinstance(pred, pd.Series):
        scores = pred.rename("score").to_frame()
    else:
        scores = pred.copy()
    if "score" not in scores.columns:
        scores.columns = ["score"]
    dates = scores.index.get_level_values("datetime")
    ref = scores[(dates >= pd.Timestamp(RESEARCH_START)) & (dates <= pd.Timestamp(RESEARCH_END))]
    daily = []
    for dt, group in ref.groupby(level="datetime"):
        stats = score_stats(group["score"])
        stats["datetime"] = pd.Timestamp(dt).date().isoformat()
        top = group["score"].dropna().sort_values(ascending=False).head(30)
        stats["top30_spread"] = float(top.max() - top.min()) if len(top) else float("nan")
        daily.append(stats)
    daily_df = pd.DataFrame(daily)
    daily_path = run_dir / "score_reference_daily.csv"
    ref_path = run_dir / "score_reference.json"
    daily_df.to_csv(daily_path, index=False)
    payload = {
        "source_recorder_id": RECORDER_ID,
        "source_experiment_id": EXPERIMENT_ID,
        "source_prediction_artifact": rel(PRED_PATH),
        "research_test_range": f"{RESEARCH_START}..{RESEARCH_END}",
        "rows": int(ref.shape[0]),
        "daily_rows": int(daily_df.shape[0]),
        "whole_window": score_stats(ref["score"]),
        "daily_summary_path": rel(daily_path),
        "created_at": utc_now(),
    }
    write_json(ref_path, payload)
    return {"path": ref_path, "daily_path": daily_path, "payload": payload}


def build_clean_provider(provider: Path, log_path: Path, max_workers: int) -> None:
    if provider.exists():
        raise FileExistsError(f"run-specific provider already exists: {provider}")
    provider.mkdir(parents=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log:
        log.write(f"[{utc_now()}] dump clean provider start\n")
        dumper = DumpDataAll(
            data_path=str(NORMALIZED_DIR),
            qlib_dir=str(provider),
            freq="day",
            max_workers=max_workers,
            include_fields=INCLUDE_FIELDS,
            symbol_field_name="symbol",
        )
        dumper.dump()
        log.write(f"[{utc_now()}] dump clean provider done\n")
    instruments_dir = provider / "instruments"
    instruments_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(UNIVERSE_PATH, instruments_dir / "tw_liquid_dyn.txt")


def generate_prediction(provider: Path, asof: str) -> pd.DataFrame:
    qlib.init(provider_uri=str(provider), region="tw", expression_cache=None, dataset_cache=None)
    handler_conf = {
        "class": "Alpha158",
        "module_path": "qlib.contrib.data.handler",
        "kwargs": {
            "start_time": "2015-05-04",
            "end_time": asof,
            "fit_start_time": "2015-05-04",
            "fit_end_time": "2020-12-31",
            "instruments": MARKET,
        },
    }
    dataset = DatasetH(handler=handler_conf, segments={"snapshot": (asof, asof)})
    model = pickle.load(MODEL_PATH.open("rb"))
    if not isinstance(model, LGBModel):
        raise TypeError(f"unexpected model type: {type(model)}")
    pred = model.predict(dataset, segment="snapshot")
    return pred.rename("score").to_frame()


def artifact_entry(
    key: str,
    path: Path,
    kind: str,
    committed_expected: bool,
    required_for_acceptance: bool,
    local_only: bool = False,
    include_sha: bool = True,
) -> dict[str, Any]:
    exists = path.exists()
    is_file = path.is_file()
    size_bytes = path.stat().st_size if exists and is_file else None
    digest = sha256_file(path) if exists and is_file and include_sha else None
    return {
        "key": key,
        "path": rel(path),
        "kind": kind,
        "exists": exists,
        "size_bytes": size_bytes,
        "sha256": digest,
        "committed_expected": committed_expected,
        "required_for_acceptance": required_for_acceptance,
        "local_only": local_only,
    }


def write_artifact_manifest(manifest_path: Path, entries: list[dict[str, Any]], run_id: str, status: str) -> dict[str, Any]:
    payload = {
        "run_id": run_id,
        "created_at": utc_now(),
        "status": status,
        "schema_version": 1,
        "self_sha256_note": "artifact_manifest.json omits its own SHA-256 to avoid self-referential hashing",
        "entries": entries,
    }
    write_json(manifest_path, payload)
    return payload


def missing_required_from_manifest(payload: dict[str, Any]) -> list[str]:
    missing = []
    for entry in payload.get("entries", []):
        if not entry.get("required_for_acceptance"):
            continue
        if not entry.get("exists"):
            missing.append(entry.get("key", "unknown"))
            continue
        if entry.get("kind") != "directory" and entry.get("size_bytes") == 0:
            missing.append(entry.get("key", "unknown"))
    return missing


def write_provider_reconstruction(path: Path, run_id: str, asof: str, provider: Path, unique_fields: list[str]) -> None:
    lines = [
        "# Provider Reconstruction",
        "",
        f"- run_id: `{run_id}`",
        f"- as_of_date: `{asof}`",
        f"- provider_path: `{rel(provider)}`",
        "- provider_build_mode: `full_rebuild`",
        f"- source_normalized_dir: `{rel(NORMALIZED_DIR)}`",
        f"- include_fields: `{INCLUDE_FIELDS}`",
        f"- universe_source: `{rel(UNIVERSE_PATH)}`",
        f"- expected_provider_unique_fields: `{','.join(unique_fields) if unique_fields else 'pending'}`",
        f"- command: `python examples/tw/run_option_c_daily_prediction.py --asof {asof} --max-workers <N>`",
        "- rejected_field_expectation: provider=0, handler=0, prediction=0",
        "- clean_forward_provider_policy: local-only; intentionally excluded from git by default",
        "",
        "This artifact describes how to rebuild the run-specific clean provider from local Yahoo adjusted primary normalized CSV data without committing the provider bin tree.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Option C daily prediction or formal forward-validation snapshot.")
    parser.add_argument("--asof", default=None)
    parser.add_argument("--max-workers", type=int, default=8)
    parser.add_argument("--formal-forward-validation", action="store_true")
    parser.add_argument("--output-root", default=None)
    parser.add_argument("--report-path", default=None)
    args = parser.parse_args()

    local_max_date = latest_local_date()
    formal_forward_validation = bool(args.formal_forward_validation)
    if formal_forward_validation:
        if args.asof is not None and args.asof != local_max_date:
            raise PipelineBlocker(
                "non_mechanical_date_selection",
                f"formal mode requires latest local date selection; requested {args.asof}, local max {local_max_date}",
                "rerun without --asof or use the latest local date",
            )
        asof = local_max_date
        run_prefix = "option_c_forward_validation"
        default_out_root = FORMAL_OUT_ROOT
        default_report_path = FORMAL_REPORT_PATH
    else:
        asof = args.asof or local_max_date
        run_prefix = "option_c_smoke"
        default_out_root = OUT_ROOT
        default_report_path = REPORT_PATH
    output_root = Path(args.output_root) if args.output_root else default_out_root
    if not output_root.is_absolute():
        output_root = ROOT / output_root
    report_path = Path(args.report_path) if args.report_path else default_report_path
    if not report_path.is_absolute():
        report_path = ROOT / report_path
    formal_snapshot_ordinal = "first"
    if formal_forward_validation and "second_snapshot" in report_path.name:
        formal_snapshot_ordinal = "second"
    formal_snapshot_scope_text = f"single-date {formal_snapshot_ordinal} formal forward-validation snapshot"
    run_id = f"{run_prefix}_{asof.replace('-', '')}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    run_dir = output_root / run_id
    provider = run_dir / "clean_forward_provider"
    run_dir.mkdir(parents=True, exist_ok=False)

    status = "failed"
    blocker_category: str | None = None
    blocker_reason: str | None = None
    blocker_next_action: str | None = None
    failure_category: str | None = None
    errors: list[str] = []
    warnings: list[str] = []
    artifacts: dict[str, str] = {}
    checks: list[dict[str, str]] = []
    command = " ".join(sys.argv)
    git_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stdout=subprocess.PIPE, check=False).stdout.strip()

    field_df = pd.DataFrame(columns=["instrument", "field", "path"])
    provider_rejected: list[str] = []
    handler_rejected: list[str] = []
    snapshot_rejected: list[str] = []
    feature_names: list[str] = []
    ref: dict[str, Any] = {"path": run_dir / "score_reference.json", "daily_path": run_dir / "score_reference_daily.csv", "payload": {}}
    stats: dict[str, float | int] = {"count": 0, "finite_count": 0}
    finite_share = 0.0
    universe_count = 0
    prediction_count = 0

    log_path = run_dir / "run.log"
    field_path = run_dir / "provider_field_inventory.csv"
    handler_path = run_dir / "handler_feature_list.json"
    rejected_path = run_dir / "rejected_field_scan.json"
    provider_meta_path = run_dir / "provider_metadata.json"
    universe_path = run_dir / "universe_membership.csv"
    pred_path = run_dir / "prediction.csv"
    health_path = run_dir / "health_checks.json"
    monitoring_path = run_dir / "monitoring_summary.json"
    run_meta_path = run_dir / "run_metadata.json"
    implementation_report_path = run_dir / "implementation_report.md"
    manifest_path = run_dir / "artifact_manifest.json"
    reconstruction_path = run_dir / "provider_reconstruction.md"
    data_selection_path = run_dir / "data_selection_metadata.json"
    data_update_log_path = run_dir / "data_update_log.json"
    label_status_path = run_dir / "label_status.json"
    top30_path = run_dir / "top30_scores.csv"
    portfolio_observation_path = run_dir / "diagnostic_portfolio_status.json"

    def log(message: str) -> None:
        with log_path.open("a", encoding="utf-8") as f:
            f.write(f"[{utc_now()}] {message}\n")

    def run_metadata_payload() -> dict[str, Any]:
        return {
            "run_id": run_id,
            "created_at": utc_now(),
            "status": status,
            "asof": asof,
            "command": command,
            "git_commit": git_commit,
            "hardening_baseline_commit": BASELINE_COMMIT,
            "model_manifest": "docs/tw_audit/48_option_c_final_model_manifest.md",
            "recorder_id": RECORDER_ID,
            "experiment_id": EXPERIMENT_ID,
            "recorder_path": rel(RECORDER_DIR),
            "config": rel(CONFIG_PATH),
            "provider_path": rel(provider),
            "market": MARKET,
            "benchmark": BENCHMARK,
            "blocker_category": blocker_category,
            "blocker_reason": blocker_reason,
            "blocker_next_action": blocker_next_action,
            "failure_category": failure_category,
            "errors": errors,
            "warnings": warnings,
            "artifacts": artifacts,
            "formal_forward_validation": formal_forward_validation,
            "formal_snapshot_ordinal": formal_snapshot_ordinal if formal_forward_validation else None,
            "formal_snapshot_scope": formal_snapshot_scope_text if formal_forward_validation else None,
            "formal_observation_clock_start": formal_forward_validation and status in {"accepted", "accepted_with_warnings"},
            "local_max_date": local_max_date,
            "selection_rule": "latest_available_local_trading_date" if formal_forward_validation else "explicit_or_latest_local_date",
            "forward_validation_started": formal_forward_validation and status in {"accepted", "accepted_with_warnings"},
            "paper_trading_started": False,
            "live_trading_started": False,
        }

    def monitoring_payload() -> dict[str, Any]:
        return {
            "run_id": run_id,
            "run_status": status,
            "asof": asof,
            "target_effective_date": None,
            "model_recorder_id": RECORDER_ID,
            "provider_path": rel(provider),
            "universe_count": universe_count,
            "prediction_count": prediction_count,
            "finite_prediction_share": finite_share,
            "score_distribution": stats,
            "blocker_category": blocker_category,
            "blocker_reason": blocker_reason,
            "failure_category": failure_category,
            "exceptions": errors,
            "formal_forward_validation": formal_forward_validation,
            "formal_snapshot_ordinal": formal_snapshot_ordinal if formal_forward_validation else None,
            "formal_snapshot_scope": formal_snapshot_scope_text if formal_forward_validation else None,
            "local_max_date": local_max_date,
            "selection_rule": "latest_available_local_trading_date" if formal_forward_validation else "explicit_or_latest_local_date",
            "diagnostic_only": True,
            "executable_orders_generated": False,
            "forward_validation_started": formal_forward_validation and status in {"accepted", "accepted_with_warnings"},
            "paper_trading_started": False,
            "live_trading_started": False,
        }

    def build_manifest_entries(include_manifest_self: bool = True) -> list[dict[str, Any]]:
        entries = [
            artifact_entry("run_metadata", run_meta_path, "json", True, True),
            artifact_entry("provider_metadata", provider_meta_path, "json", True, status == "accepted"),
            artifact_entry("provider_field_inventory", field_path, "csv", True, status == "accepted"),
            artifact_entry("handler_feature_list", handler_path, "json", True, status == "accepted"),
            artifact_entry("rejected_field_scan", rejected_path, "json", True, status == "accepted"),
            artifact_entry("score_reference", Path(ref["path"]), "json", True, status == "accepted"),
            artifact_entry("score_reference_daily", Path(ref["daily_path"]), "csv", True, status == "accepted"),
            artifact_entry("universe_membership", universe_path, "csv", True, status == "accepted"),
            artifact_entry("prediction", pred_path, "csv", True, status == "accepted"),
            artifact_entry("health_checks", health_path, "json", True, True),
            artifact_entry("monitoring_summary", monitoring_path, "json", True, True),
            artifact_entry("run_log", log_path, "log", True, True),
            artifact_entry("implementation_report", implementation_report_path, "md", True, True),
            artifact_entry("provider_reconstruction", reconstruction_path, "md", True, status == "accepted"),
            artifact_entry("data_selection_metadata", data_selection_path, "json", True, formal_forward_validation),
            artifact_entry("data_update_log", data_update_log_path, "json", True, formal_forward_validation),
            artifact_entry("label_status", label_status_path, "json", True, formal_forward_validation),
            artifact_entry("top30_scores", top30_path, "csv", True, formal_forward_validation and status == "accepted"),
            artifact_entry("diagnostic_portfolio_status", portfolio_observation_path, "json", True, formal_forward_validation),
            artifact_entry("clean_forward_provider", provider, "provider_bin_tree", False, status == "accepted", local_only=True, include_sha=False),
        ]
        if include_manifest_self:
            entries.append(artifact_entry("artifact_manifest", manifest_path, "json", True, True, include_sha=False))
        return entries

    def write_reports() -> None:
        unique_fields = sorted(field_df["field"].unique().tolist()) if not field_df.empty else []
        ref_payload = ref.get("payload", {})
        ref_summary = ref_payload.get("whole_window", {})
        reconstruction_summary = rel(reconstruction_path) if reconstruction_path.exists() else "not_written_for_blocked_or_failed_run"
        recorder_identity = "pass" if PRED_PATH.exists() and MODEL_PATH.exists() and status != "blocked" else "not_evaluated"
        report_scope = (
            f"option_c_formal_forward_validation_{formal_snapshot_ordinal}_snapshot"
            if formal_forward_validation
            else "option_c_min_daily_prediction_pipeline_result"
        )
        report_title = (
            f"Option C Formal Forward Validation {formal_snapshot_ordinal.title()} Snapshot Report"
            if formal_forward_validation
            else "Option C Minimum Daily Prediction Pipeline Report"
        )
        lines = [
            "---",
            f"created_at: {utc_now()}",
            f"status: {status}",
            f"scope: {report_scope}",
            "---",
            "",
            f"# {report_title}",
            "",
            "## Summary",
            "",
            f"- command: `{command}`",
            f"- formal_forward_validation: `{str(formal_forward_validation).lower()}`",
            f"- local_max_date: `{local_max_date}`",
            f"- selection_rule: `{'latest_available_local_trading_date' if formal_forward_validation else 'explicit_or_latest_local_date'}`",
            f"- hardening_baseline_commit: `{BASELINE_COMMIT}`",
            f"- run_id: `{run_id}`",
            f"- as_of_date: `{asof}`",
            f"- status: `{status}`",
            f"- blocker_category: `{blocker_category or 'none'}`",
            f"- failure_category: `{failure_category or 'none'}`",
            f"- provider_path: `{rel(provider)}`",
            "- provider_build_mode: `full_rebuild`",
            f"- provider_field_inventory_rows: `{int(field_df.shape[0])}`",
            f"- provider_unique_fields: `{','.join(unique_fields) if unique_fields else 'none'}`",
            f"- rejected_field_scan: provider=`{len(provider_rejected)}`, handler=`{len(handler_rejected)}`, prediction=`{len(snapshot_rejected)}`",
            f"- artifact_manifest: `{rel(manifest_path)}`",
            f"- provider_reconstruction: `{reconstruction_summary}`",
            f"- recorder_id: `{RECORDER_ID}`",
            f"- recorder_identity_check: `{recorder_identity}`",
            f"- handler_feature_count: `{len(feature_names)}`",
            f"- score_reference_summary: `{json.dumps(ref_summary, default=str)}`",
            f"- prediction_count: `{prediction_count}`",
            f"- finite_prediction_share: `{finite_share:.6f}`",
            f"- score_distribution_summary: `{json.dumps(stats, default=str)}`",
            f"- universe_count: `{universe_count}`",
            f"- label_status: `{'see label_status.json' if formal_forward_validation else 'not_applicable'}`",
            f"- diagnostic_only: `{str(formal_forward_validation).lower()}`",
            (
                f"- formal_snapshot_scope: `{formal_snapshot_scope_text}`"
                if formal_forward_validation
                else "- hardening_validation_rerun: `same-date validation run only; not formal forward evidence`"
            ),
            f"- forward_validation_started: `{str(formal_forward_validation and status in {'accepted', 'accepted_with_warnings'}).lower()}`",
            "- paper_trading_started: `false`",
            "- live_trading_started: `false`",
            "",
            "## Health Checks",
            "",
            "| check | status | detail |",
            "| --- | --- | --- |",
        ]
        for check in checks:
            detail = str(check.get("detail", "")).replace("|", "\\|")
            lines.append(f"| {check.get('check', '')} | {check.get('status', '')} | {detail} |")
        lines.extend(["", "## Artifacts", ""])
        for key, artifact_path in sorted(artifacts.items()):
            lines.append(f"- {key}: `{artifact_path}`")
        lines.extend(["", "## Errors", ""])
        lines.extend([f"- {e}" for e in errors] or ["- none"])
        lines.extend(["", "## Warnings", ""])
        lines.extend([f"- {w}" for w in warnings] or ["- none"])
        lines.extend([
            "",
            "## Decision",
            "",
            (
                (
                    f"This is the {formal_snapshot_ordinal} accepted formal single-day forward-validation snapshot. "
                    "Paper trading and live trading were not started. No multi-day evidence, labels, "
                    "IC/RankIC, monthly aggregation, executable orders, or target trade file were generated."
                )
                if formal_forward_validation and status in {"accepted", "accepted_with_warnings"}
                else (
                    f"This {formal_snapshot_ordinal} formal single-day forward-validation snapshot attempt is {status}. "
                    "No accepted formal snapshot was generated. Paper trading and live trading were not started. "
                    "No multi-day evidence, labels, IC/RankIC, monthly aggregation, executable orders, or target trade file were generated."
                )
                if formal_forward_validation
                else "This is a single-day hardening validation snapshot only. Formal forward validation, paper trading, and live trading were not started."
            ),
            "",
            "This report is the next Codex audit stop point before commit.",
            "",
        ])
        text = "\n".join(lines)
        implementation_report_path.write_text(text, encoding="utf-8")
        artifacts["implementation_report"] = rel(implementation_report_path)
        report_path.write_text(text, encoding="utf-8")

    try:
        log(f"run_id={run_id}")
        log(f"asof={asof}")
        validate_inputs(asof, args.max_workers)
        if formal_forward_validation:
            write_json(data_selection_path, {
                "run_id": run_id,
                "selected_asof": asof,
                "local_max_date": local_max_date,
                "selection_rule": "latest_available_local_trading_date",
                "selection_reason": "round_43 requires mechanical latest local date selection when using existing post-freeze local data",
                "existing_post_freeze_local_data_used": True,
                "multi_day_backfill_performed": False,
                "smoke_or_hardening_runs_counted_as_formal_evidence": False,
                "created_at": utc_now(),
            })
            artifacts["data_selection_metadata"] = rel(data_selection_path)
            write_json(data_update_log_path, {
                "run_id": run_id,
                "data_update_performed": False,
                "vendor": "Yahoo adjusted primary",
                "reason": "using latest available local normalized data; no update/download performed",
                "freshness_date": local_max_date,
                "symbol_success_count": None,
                "symbol_failure_count": None,
                "partial_failure": False,
                "created_at": utc_now(),
            })
            artifacts["data_update_log"] = rel(data_update_log_path)

        build_clean_provider(provider, log_path, args.max_workers)
        artifacts["provider"] = rel(provider)

        field_df = list_provider_fields(provider)
        field_df.to_csv(field_path, index=False)
        artifacts["provider_field_inventory"] = rel(field_path)
        unique_fields = sorted(field_df["field"].unique().tolist())

        provider_rejected = rejected_hits(field_df["field"].tolist())
        feature_names = alpha158_names()
        handler_rejected = rejected_hits(feature_names)
        write_json(handler_path, {
            "handler": "qlib.contrib.data.handler.Alpha158",
            "feature_count": len(feature_names),
            "features": feature_names,
            "rejected_hits": handler_rejected,
        })
        artifacts["handler_feature_list"] = rel(handler_path)

        rejected_payload = {
            "rejected_fields": sorted(REJECTED_FIELDS),
            "provider_hits": provider_rejected,
            "handler_hits": handler_rejected,
            "prediction_hits": [],
            "prediction_scan_source": "pending prediction output columns",
            "provider_hit_count": len(provider_rejected),
            "handler_hit_count": len(handler_rejected),
            "prediction_hit_count": 0,
        }
        write_json(rejected_path, rejected_payload)
        artifacts["rejected_field_scan"] = rel(rejected_path)

        if provider_rejected or handler_rejected:
            failure_category = "rejected_field_detected"
            errors.append("rejected custom factor field detected")
            raise RuntimeError(errors[-1])
        if len(feature_names) != 158:
            failure_category = "handler_feature_count_mismatch"
            errors.append(f"Alpha158 feature count mismatch: {len(feature_names)}")
            raise RuntimeError(errors[-1])

        write_json(provider_meta_path, {
            "provider_path": rel(provider),
            "provider_build_mode": "full_rebuild",
            "source_normalized_dir": rel(NORMALIZED_DIR),
            "include_fields": INCLUDE_FIELDS.split(","),
            "field_inventory_rows": int(field_df.shape[0]),
            "unique_fields": unique_fields,
            "calendar_hash": sha256_file(provider / "calendars/day.txt"),
            "all_instruments_hash": sha256_file(provider / "instruments/all.txt"),
            "market_instruments_hash": sha256_file(provider / "instruments/tw_liquid_dyn.txt"),
            "clean_forward_provider_committed_expected": False,
            "created_at": utc_now(),
        })
        artifacts["provider_metadata"] = rel(provider_meta_path)
        write_provider_reconstruction(reconstruction_path, run_id, asof, provider, unique_fields)
        artifacts["provider_reconstruction"] = rel(reconstruction_path)

        universe = active_universe(asof)
        universe.to_csv(universe_path, index=False)
        artifacts["universe_membership"] = rel(universe_path)

        ref = materialize_score_reference(run_dir)
        artifacts["score_reference"] = rel(Path(ref["path"]))
        artifacts["score_reference_daily"] = rel(Path(ref["daily_path"]))

        pred = generate_prediction(provider, asof)
        pred.reset_index().to_csv(pred_path, index=False)
        artifacts["prediction"] = rel(pred_path)

        pred_fields = list(pred.columns)
        snapshot_rejected = rejected_hits(pred_fields)
        rejected_payload.update({
            "prediction_hits": snapshot_rejected,
            "prediction_scan_source": "prediction output columns",
            "prediction_columns": pred_fields,
            "prediction_hit_count": len(snapshot_rejected),
        })
        write_json(rejected_path, rejected_payload)

        if formal_forward_validation:
            top30 = pred["score"].dropna().sort_values(ascending=False).head(30).rename("score").reset_index()
            top30.to_csv(top30_path, index=False)
            artifacts["top30_scores"] = rel(top30_path)
            later_dates = local_dates_after(asof)
            label_available = bool(later_dates)
            write_json(label_status_path, {
                "run_id": run_id,
                "asof": asof,
                "label_availability_status": "available" if label_available else "pending_labels",
                "label_date": later_dates[0] if label_available else None,
                "availability_reason": "future local price exists" if label_available else "no local trading date after selected asof",
                "label_formula": "next available trading day return; not materialized in first formal slice",
                "label_artifact_written": False,
                "ic_rankic_artifact_written": False,
            })
            artifacts["label_status"] = rel(label_status_path)
            write_json(portfolio_observation_path, {
                "run_id": run_id,
                "diagnostic_only": True,
                "paper_trading_started": False,
                "live_trading_started": False,
                "executable_orders_generated": False,
                "target_trade_file_generated": False,
                "reason": "first formal slice records status only; no portfolio orders or paper execution",
            })
            artifacts["diagnostic_portfolio_status"] = rel(portfolio_observation_path)

        stats = score_stats(pred["score"])
        finite_share = stats["finite_count"] / stats["count"] if stats["count"] else 0.0
        universe_count = int(universe["instrument"].nunique())
        prediction_count = int(stats["count"])

        checks = [
            {"check": "input_validation", "status": "pass", "detail": "CLI, local data, frozen artifacts, and universe validated before provider build"},
            {"check": "model_identity", "status": "pass", "detail": f"recorder={RECORDER_ID}; path={rel(RECORDER_DIR)}"},
            {"check": "provider_policy", "status": "pass", "detail": "clean Yahoo-only provider from normalized OHLCV; provider bin tree local-only"},
            {"check": "rejected_field_scan", "status": "pass" if not (provider_rejected or handler_rejected or snapshot_rejected) else "fail", "detail": f"provider={provider_rejected}, handler={handler_rejected}, prediction={snapshot_rejected}"},
            {"check": "handler_feature_list", "status": "pass", "detail": f"{len(feature_names)} Alpha158 fields"},
            {"check": "universe_count", "status": "pass" if 120 <= universe_count <= 180 else "fail", "detail": f"{universe_count} active universe members"},
            {"check": "prediction_finite_share", "status": "pass" if finite_share >= 0.95 else "fail", "detail": f"{finite_share:.6f}"},
            {"check": "prediction_nan_count", "status": "pass" if (stats["count"] - stats["finite_count"]) <= stats["count"] * 0.05 else "fail", "detail": str(int(stats["count"] - stats["finite_count"]))},
            {"check": "score_distribution", "status": "pass", "detail": json.dumps(stats, default=str)},
            {"check": "score_reference", "status": "pass", "detail": rel(Path(ref["path"]))},
            {"check": "provider_reconstruction", "status": "pass", "detail": rel(reconstruction_path)},
        ]
        if formal_forward_validation:
            checks.extend([
                {"check": "formal_date_selection", "status": "pass", "detail": f"selected latest local date {asof}; local_max_date={local_max_date}"},
                {"check": "label_status", "status": "pass", "detail": "see label_status.json"},
                {"check": "diagnostic_portfolio_status", "status": "pass", "detail": "diagnostic_only=true; no orders generated"},
            ])
        failed_checks = [c for c in checks if c["status"] == "fail"]
        status = "accepted_with_warnings" if warnings else "accepted"
        if failed_checks:
            status = "failed"
            errors.extend([f"health check failed: {c['check']}" for c in failed_checks])
            failure_category = "health_check_failed"

    except PipelineBlocker as exc:
        status = "blocked"
        blocker_category = exc.category
        blocker_reason = str(exc)
        blocker_next_action = exc.next_action
        errors.append(str(exc))
        checks.append({"check": "input_validation", "status": "blocked", "detail": f"{exc.category}: {exc}"})
        log(f"blocked={exc.category}: {exc}")
    except Exception as exc:
        if status != "blocked":
            status = "failed"
        if failure_category is None:
            failure_category = "internal_exception"
        if not errors:
            errors.append(str(exc))
        checks.append({"check": "pipeline_exception", "status": "fail", "detail": f"{failure_category}: {exc}"})
        log(f"exception={failure_category}: {exc}")
    finally:
        if log_path.exists():
            artifacts["run_log"] = rel(log_path)
        artifacts["run_metadata"] = rel(run_meta_path)
        write_json(run_meta_path, run_metadata_payload())
        if not health_path.exists():
            write_json(health_path, {"checks": checks, "status": status, "errors": errors, "warnings": warnings})
            artifacts["health_checks"] = rel(health_path)
        if not monitoring_path.exists():
            write_json(monitoring_path, monitoring_payload())
            artifacts["monitoring_summary"] = rel(monitoring_path)
        if formal_forward_validation and not label_status_path.exists():
            write_json(label_status_path, {
                "run_id": run_id,
                "asof": asof,
                "label_availability_status": "not_evaluated",
                "availability_reason": "run did not reach prediction stage",
                "label_artifact_written": False,
                "ic_rankic_artifact_written": False,
            })
            artifacts["label_status"] = rel(label_status_path)
        if formal_forward_validation and not portfolio_observation_path.exists():
            write_json(portfolio_observation_path, {
                "run_id": run_id,
                "diagnostic_only": True,
                "paper_trading_started": False,
                "live_trading_started": False,
                "executable_orders_generated": False,
                "target_trade_file_generated": False,
                "reason": "run did not reach diagnostic portfolio observation stage",
            })
            artifacts["diagnostic_portfolio_status"] = rel(portfolio_observation_path)
        write_reports()
        artifacts["artifact_manifest"] = rel(manifest_path)
        if not manifest_path.exists():
            write_json(manifest_path, {"status": "manifest_placeholder", "created_at": utc_now()})
        manifest_payload = write_artifact_manifest(manifest_path, build_manifest_entries(), run_id, status)
        missing = missing_required_from_manifest(manifest_payload)
        artifact_status = "pass" if not missing else "fail"
        checks = [c for c in checks if c.get("check") != "artifact_completeness"]
        checks.append({
            "check": "artifact_completeness",
            "status": artifact_status,
            "detail": "manifest required artifacts present" if not missing else f"manifest missing required artifacts: {missing}",
        })
        if artifact_status == "fail" and status in {"accepted", "accepted_with_warnings"}:
            status = "failed"
            failure_category = "artifact_manifest_incomplete"
            errors.append(f"artifact manifest missing required artifacts: {missing}")
            manifest_payload = write_artifact_manifest(manifest_path, build_manifest_entries(), run_id, status)
        write_json(health_path, {"checks": checks, "status": status, "errors": errors, "warnings": warnings})
        write_json(monitoring_path, monitoring_payload())
        write_reports()
        manifest_payload = write_artifact_manifest(manifest_path, build_manifest_entries(), run_id, status)
        write_json(run_meta_path, run_metadata_payload())

    print(json.dumps({"run_id": run_id, "status": status, "run_dir": rel(run_dir), "errors": errors}, indent=2))
    return 0 if status in {"accepted", "accepted_with_warnings", "blocked"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
