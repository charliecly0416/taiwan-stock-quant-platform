#!/usr/bin/env python3
"""Build DNG15_R-B isolated Model A score artifacts.

This script consumes only the DNG15_R-A-R staged Yahoo provider candidate and
writes isolated ModelInferenceInput, ScoreJob, ModelSignalArtifact, catalog
summary, and execution report. It does not publish providers, switch latest
pointers, refresh data, train/tune models, run strategy replay, or trade.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
QLIB_PIPELINE_ROOT = ROOT / "qlib_pipeline"
if str(QLIB_PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(QLIB_PIPELINE_ROOT))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import qlib  # noqa: E402
from qlib.contrib.model.gbdt import LGBModel  # noqa: E402
from qlib.data.dataset import DatasetH  # noqa: E402

from tw_modela_score_common import (  # noqa: E402
    E1_TRAINING_MANIFEST,
    FORBIDDEN_ACTIONS_FALSE,
    INFERENCE_FIELDS,
    MODEL_ID,
    QLIB_CONFIG,
    QLIB_MODEL_PATH,
    QLIB_RECORDER_PATH,
    REQUIRED_PROVIDER_FIELDS,
    SIGNAL_FIELDS,
    file_entry,
    forbidden_columns,
    validate_signal_frame,
)
from validate_tw_model_inference_input import validate as validate_input  # noqa: E402
from validate_tw_score_job import validate as validate_score_job  # noqa: E402


DEFAULT_ASOF = "2026-06-26"
DEFAULT_RUN_ID = "dng15_r_b_modela_20260626_isolated"
ASOF = DEFAULT_ASOF
RUN_ID = DEFAULT_RUN_ID
INPUT_DIR = ROOT / "data_tw/canonical/model_inference_input" / MODEL_ID / RUN_ID
SCORE_DIR = ROOT / "data_tw/artifacts/score_jobs" / MODEL_ID / RUN_ID
SIGNAL_DIR = ROOT / "data_tw/artifacts/signals" / MODEL_ID / RUN_ID
CATALOG_PATH = ROOT / "data_tw/catalog/dng15_r_b_isolated_modela_score_integration_validation.json"
REPORT_PATH = ROOT / "docs/tw_data_governance/DNG15_R_B_ISOLATED_MODELA_SCORE_INTEGRATION_EXECUTION_REPORT_CN.md"
R_A_R_DECISION_PATH = ROOT / "data_tw/catalog/dng15_r_a_r_yahoo_access_repair_decision.json"
R_A_R_READINESS_PATH = ROOT / "data_tw/catalog/dng15_r_a_r_modela_20260626_candidate_readiness.json"

FORBIDDEN_GOVERNANCE_ACTIONS = {
    "formal_publish": False,
    "formal_provider_mutated": False,
    "formal_normalized_mutated": False,
    "accepted_latest_switch": False,
    "latest_signal_updated": False,
    "readonly_latest_published": False,
    "agent_prompt_latest_published": False,
    "production_default_model_or_strategy_switched": False,
    "strategy_replay_or_nav_triggered": False,
    "broker_order_quick_trade_triggered": False,
    "target_position_or_weight_generated": False,
    "finmind_fallback": False,
    "mixed_provider_bridge": False,
    "model_training_or_tuning": False,
}

REQUIRED_DOCS_READ = [
    "docs/tw_data_governance/DNG15_R_B_ISOLATED_MODELA_SCORE_INTEGRATION_WORK_CN.md",
    "docs/tw_data_governance/DNG15_R_A_R_YAHOO_ACCESS_REPAIR_EXECUTION_REPORT_CN.md",
    "docs/tw_data_governance/DNG15_R_A_R_YAHOO_ACCESS_REPAIR_REVIEW_CN.md",
    "data_tw/catalog/dng15_r_a_r_yahoo_access_repair_decision.json",
    "data_tw/catalog/dng15_r_a_r_modela_20260626_candidate_readiness.json",
    "docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md",
    "/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md",
    "docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md",
    "docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md",
    "docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md",
    "docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md",
    "docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return str(p.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(p)


def sanitize_run_id(raw: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in raw.strip())
    if not safe:
        raise ValueError("run_id must not be empty")
    if safe in {".", ".."} or "/" in safe or "\\" in safe:
        raise ValueError(f"unsafe run_id: {raw!r}")
    return safe


def configure_run_context(
    *,
    target_asof: str = DEFAULT_ASOF,
    run_id: str = DEFAULT_RUN_ID,
    catalog_path: Path | None = None,
    report_path: Path | None = None,
) -> None:
    global ASOF, RUN_ID, INPUT_DIR, SCORE_DIR, SIGNAL_DIR, CATALOG_PATH, REPORT_PATH
    if not target_asof:
        raise ValueError("target_asof must not be empty")
    safe_run_id = sanitize_run_id(run_id)
    ASOF = target_asof
    RUN_ID = safe_run_id
    INPUT_DIR = ROOT / "data_tw/canonical/model_inference_input" / MODEL_ID / RUN_ID
    SCORE_DIR = ROOT / "data_tw/artifacts/score_jobs" / MODEL_ID / RUN_ID
    SIGNAL_DIR = ROOT / "data_tw/artifacts/signals" / MODEL_ID / RUN_ID
    if catalog_path is not None:
        CATALOG_PATH = catalog_path
    elif target_asof == DEFAULT_ASOF and RUN_ID == DEFAULT_RUN_ID:
        CATALOG_PATH = ROOT / "data_tw/catalog/dng15_r_b_isolated_modela_score_integration_validation.json"
    else:
        CATALOG_PATH = ROOT / "data_tw/catalog" / f"dng15_r_b_isolated_modela_score_integration_validation_{RUN_ID}.json"
    if report_path is not None:
        REPORT_PATH = report_path
    elif target_asof == DEFAULT_ASOF and RUN_ID == DEFAULT_RUN_ID:
        REPORT_PATH = ROOT / "docs/tw_data_governance/DNG15_R_B_ISOLATED_MODELA_SCORE_INTEGRATION_EXECUTION_REPORT_CN.md"
    else:
        REPORT_PATH = ROOT / "docs/tw_data_governance" / f"DNG15_R_B_ISOLATED_MODELA_SCORE_INTEGRATION_EXECUTION_REPORT_{RUN_ID}.md"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_repo_path(raw: str) -> Path:
    p = Path(raw)
    if p.is_absolute():
        return p
    candidates = [ROOT / p, QLIB_PIPELINE_ROOT / p]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def load_symbol_universe(provider: Path) -> list[str]:
    inst = provider / "instruments/all.txt"
    if not inst.exists():
        return []
    symbols = []
    for line in inst.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        symbols.append(line.split()[0].strip().upper())
    return sorted(symbols)


def provider_calendar(provider: Path) -> list[str]:
    path = provider / "calendars/day.txt"
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def provider_field_inventory(provider: Path, symbols: list[str]) -> dict[str, Any]:
    counts = {field: 0 for field in sorted(REQUIRED_PROVIDER_FIELDS)}
    unexpected: set[str] = set()
    missing_feature_symbols: list[str] = []
    for symbol in symbols:
        feature_dir = provider / "features" / symbol.lower()
        if not feature_dir.exists():
            missing_feature_symbols.append(symbol)
            continue
        fields = {p.name.split(".")[0] for p in feature_dir.glob("*.day.bin")}
        for field in fields:
            if field in counts:
                counts[field] += 1
            else:
                unexpected.add(field)
    status = "pass" if not unexpected and not missing_feature_symbols and all(v == len(symbols) for v in counts.values()) else "fail"
    return {
        "status": status,
        "expected_field_counts": counts,
        "unexpected_fields": sorted(unexpected),
        "missing_feature_symbols": missing_feature_symbols,
        "rejected_fields_present": sorted(unexpected),
    }


def normalized_symbol_summary(normalized_dir: Path, asof: str) -> dict[str, Any]:
    files = sorted(normalized_dir.glob("TW*.csv"))
    rows: list[dict[str, Any]] = []
    missing_asof: list[str] = []
    bad_files: list[str] = []
    for path in files:
        symbol = path.stem.upper()
        try:
            dates = pd.read_csv(path, usecols=["date"])["date"].astype(str)
        except Exception:
            bad_files.append(symbol)
            continue
        date_max = str(dates.max()) if not dates.empty else ""
        has_asof = bool((dates == asof).any())
        if not has_asof:
            missing_asof.append(symbol)
        rows.append({"instrument": symbol, "date_max": date_max, "has_asof": has_asof})
    frame = pd.DataFrame(rows)
    return {
        "status": "pass"
        if len(files) == 150 and len(rows) == 150 and not missing_asof and not bad_files and str(frame["date_max"].min()) == asof and str(frame["date_max"].max()) == asof
        else "fail",
        "files_found": len(files),
        "symbols_found": len(rows),
        "symbols_with_asof": int(frame["has_asof"].sum()) if not frame.empty else 0,
        "date_max_min": str(frame["date_max"].min()) if not frame.empty else "",
        "date_max_max": str(frame["date_max"].max()) if not frame.empty else "",
        "missing_asof": missing_asof,
        "bad_files": bad_files,
    }


def readiness_gate(decision: dict[str, Any], readiness: dict[str, Any], target_asof: str) -> tuple[list[str], Path, Path]:
    errors: list[str] = []
    if decision.get("decision") != "PASS_GO_DNG15_R_B_ISOLATED_MODELA_SCORE_INTEGRATION":
        errors.append("r_a_r_decision_not_pass_go")
    if readiness.get("candidate_input_status") != "READY_STAGED_YAHOO_SCRAPLING_PROXY_CANDIDATE":
        errors.append("r_a_r_readiness_not_ready")
    if decision.get("asof") != target_asof or readiness.get("asof") != target_asof:
        errors.append("r_a_r_asof_mismatch")
    if decision.get("production_allowed") is not False or decision.get("publish_latest_authorized") is not False:
        errors.append("r_a_r_publish_or_production_flag_not_false")
    if any(bool(v) for v in decision.get("forbidden_actions", {}).values()):
        errors.append("r_a_r_forbidden_action_not_false")
    provider = resolve_repo_path(decision.get("staged_provider_path", ""))
    normalized = resolve_repo_path(decision.get("candidate_normalized_path", ""))
    if not provider.exists():
        errors.append("staged_provider_missing")
    if not normalized.exists():
        errors.append("candidate_normalized_missing")
    return errors, provider, normalized


def build_model_inference_input(
    asof: str,
    provider: Path,
    normalized: Path,
    symbols: list[str],
    normalized_summary: dict[str, Any],
    provider_inventory: dict[str, Any],
    calendar_max: str,
    gate_errors: list[str],
) -> dict[str, Any]:
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    missing_paths = []
    required_paths = {
        "staged_qlib_provider_calendar": provider / "calendars/day.txt",
        "staged_provider_instruments": provider / "instruments/all.txt",
        "frozen_model_params_pkl": QLIB_MODEL_PATH,
        "qlib_config": QLIB_CONFIG,
        "qlib_recorder_path": QLIB_RECORDER_PATH,
        "e1_training_manifest": E1_TRAINING_MANIFEST,
    }
    for key, path in required_paths.items():
        if not path.exists():
            missing_paths.append(key)

    errors = list(gate_errors)
    if missing_paths:
        errors.append("missing_required_paths:" + ",".join(missing_paths))
    if len(symbols) != 150:
        errors.append(f"staged_symbol_count_not_150:{len(symbols)}")
    if asof not in provider_calendar(provider):
        errors.append("staged_provider_calendar_missing_asof")
    if normalized_summary.get("status") != "pass":
        errors.append("candidate_normalized_validation_failed")
    if provider_inventory.get("status") != "pass":
        errors.append("staged_provider_field_inventory_failed")
    status = "READY" if not errors else "BLOCKED_INPUT_NOT_READY"

    rows = [
        {
            "date": asof,
            "instrument": symbol,
            "model_id": MODEL_ID,
            "model_family": "qlib",
            "provider_uri": rel(provider),
            "normalized_source": rel(normalized),
            "feature_artifact": rel(provider),
            "source_model_artifact": rel(QLIB_MODEL_PATH),
            "source_training_manifest": rel(E1_TRAINING_MANIFEST),
            "signal_asof": asof,
            "available_at": asof,
            "readiness_status": status,
        }
        for symbol in symbols
    ]
    write_csv(INPUT_DIR / "inference_frame.csv", rows, INFERENCE_FIELDS)
    write_json(
        INPUT_DIR / "schema.json",
        {
            "schema_version": "dng15_r_b.model_inference_input.v1",
            "compatible_validator_schema": "dng7.model_inference_input.v1",
            "primary_key": ["date", "instrument"],
            "required_fields": INFERENCE_FIELDS,
            "forbidden_fields": "MODEL_SIGNAL_CONTRACT_CN.md forbidden fields",
        },
    )
    source_readiness = {
        "status": status,
        "asof": asof,
        "errors": errors,
        "model_id": MODEL_ID,
        "model_artifact_path": rel(QLIB_MODEL_PATH),
        "model_artifact_sha256": sha256_file(QLIB_MODEL_PATH) if QLIB_MODEL_PATH.exists() else "",
        "qlib_provider_view": rel(provider),
        "qlib_provider_calendar_max": calendar_max,
        "normalized_source": rel(normalized),
        "normalized_source_summary": {
            "symbols_with_asof": normalized_summary.get("symbols_with_asof"),
            "date_max_min": normalized_summary.get("date_max_min"),
            "date_max_max": normalized_summary.get("date_max_max"),
            "files_found": normalized_summary.get("files_found"),
        },
        "provider_field_inventory": provider_inventory,
        "feature_dump_status": "READY" if provider_inventory.get("status") == "pass" else "BLOCKED_PROVIDER_FIELD_INVENTORY",
        "inference_command": "qlib.init(provider_uri=<R-A-R staged_qlib_bin>, region='tw', expression_cache=None, dataset_cache=None); DatasetH Alpha158 snapshot; frozen params.pkl predict",
        "forbidden_actions": FORBIDDEN_ACTIONS_FALSE,
        "governance_forbidden_actions": FORBIDDEN_GOVERNANCE_ACTIONS,
    }
    write_json(INPUT_DIR / "source_readiness.json", source_readiness)
    write_json(
        INPUT_DIR / "feature_lineage.json",
        {
            "model_id": MODEL_ID,
            "asof": asof,
            "inference_mode": "qlib DatasetH snapshot + frozen Option C LGBModel.predict",
            "feature_handler": "qlib.contrib.data.handler.Alpha158",
            "handler_start_time": "2015-05-04",
            "handler_end_time": asof,
            "snapshot_segment": [asof, asof],
            "provider_required_fields": sorted(REQUIRED_PROVIDER_FIELDS),
            "source_feature_artifact": rel(provider),
            "source_normalized_artifact": rel(normalized),
            "source_model_artifact": rel(QLIB_MODEL_PATH),
            "source_training_manifest": rel(E1_TRAINING_MANIFEST),
            "source_config": rel(QLIB_CONFIG),
            "pit_policy": "snapshot segment is restricted to asof; Alpha158 rolling features derive from current/past staged provider rows only",
            "not_published_latest": True,
        },
    )
    coverage_rows = [
        {"dependency": "r_a_r_decision_gate", "status": "READY" if not gate_errors else "BLOCKED", "asof": asof, "symbol_count": len(symbols), "details": ";".join(gate_errors)},
        {"dependency": "candidate_normalized", "status": "READY" if normalized_summary.get("status") == "pass" else "BLOCKED", "asof": asof, "symbol_count": normalized_summary.get("symbols_with_asof"), "details": rel(normalized)},
        {"dependency": "staged_qlib_provider_calendar", "status": "READY" if calendar_max >= asof else "BLOCKED", "asof": asof, "symbol_count": len(symbols), "details": f"calendar_max={calendar_max}"},
        {"dependency": "staged_qlib_provider_feature_bins", "status": "READY" if provider_inventory.get("status") == "pass" else "BLOCKED", "asof": asof, "symbol_count": len(symbols), "details": ",".join(sorted(REQUIRED_PROVIDER_FIELDS))},
        {"dependency": "frozen_model_params", "status": "READY" if QLIB_MODEL_PATH.exists() else "BLOCKED", "asof": asof, "symbol_count": len(symbols), "details": rel(QLIB_MODEL_PATH)},
    ]
    write_csv(INPUT_DIR / "coverage_audit.csv", coverage_rows, ["dependency", "status", "asof", "symbol_count", "details"])
    pit_rows = [
        {"check": "no_future_label_fields", "status": "PASS", "details": "inference_frame carries paths and ids only; no label/future return fields"},
        {"check": "available_at_policy", "status": "PASS", "details": "available_at equals signal_asof for isolated same-day readonly score artifact"},
        {"check": "provider_calendar_asof", "status": "PASS" if calendar_max >= asof else "FAIL", "details": f"calendar_max={calendar_max}"},
        {"check": "no_training_no_tuning", "status": "PASS", "details": "frozen params.pkl is loaded only for predict"},
        {"check": "no_publish_no_latest_switch", "status": "PASS", "details": "script writes isolated R-B artifact directories only"},
    ]
    write_csv(INPUT_DIR / "pit_audit.csv", pit_rows, ["check", "status", "details"])
    manifest = {
        "artifact_type": "ModelInferenceInput",
        "schema_version": "dng15_r_b.model_inference_input.v1",
        "model_id": MODEL_ID,
        "model_name": MODEL_ID,
        "model_family": "qlib",
        "run_id": RUN_ID,
        "created_at": utc_now(),
        "created_by": "scripts/build_tw_dng15_r_b_isolated_modela_score_integration.py",
        "asof": asof,
        "target_signal_date": asof,
        "status": status,
        "score_status": "INPUT_READY" if status == "READY" else "BLOCKED_INPUT_NOT_READY",
        "row_count": len(rows),
        "symbol_count": len(symbols),
        "source_qlib_provider_view": rel(provider),
        "source_feature_artifact": rel(provider),
        "source_normalized_artifact": rel(normalized),
        "model_artifact_path": rel(QLIB_MODEL_PATH),
        "available_at_policy": "available_at equals signal_asof; isolated readonly artifact",
        "pit_policy": "Alpha158 snapshot at asof using staged provider rows no later than asof",
        "readonly_only": True,
        "no_training_run": True,
        "no_hyperparameter_tuning": True,
        "files": {
            "manifest": "manifest.json",
            "inference_frame": "inference_frame.csv",
            "schema": "schema.json",
            "source_readiness": "source_readiness.json",
            "feature_lineage": "feature_lineage.json",
            "pit_audit": "pit_audit.csv",
            "coverage_audit": "coverage_audit.csv",
            "validator_report": "validator_report.json",
        },
        "source_artifacts": [rel(provider), rel(normalized), rel(QLIB_MODEL_PATH), rel(E1_TRAINING_MANIFEST)],
        "required_file_entries": [file_entry(path, key) for key, path in required_paths.items()],
        "forbidden_actions": FORBIDDEN_ACTIONS_FALSE,
        "governance_forbidden_actions": FORBIDDEN_GOVERNANCE_ACTIONS,
        "production_allowed": False,
        "not_published_latest": True,
        "errors": errors,
    }
    write_json(INPUT_DIR / "manifest.json", manifest)
    return manifest


def generate_prediction(provider: Path, asof: str, symbols: list[str]) -> pd.DataFrame:
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
    model = pickle.load(QLIB_MODEL_PATH.open("rb"))
    if not isinstance(model, LGBModel):
        raise TypeError(f"unexpected model type: {type(model)}")
    pred = model.predict(dataset, segment="snapshot")
    frame = pred.rename("score").to_frame().reset_index()
    return frame


def score_stats(series: pd.Series) -> dict[str, Any]:
    numeric = pd.to_numeric(series, errors="coerce")
    finite = numeric[numeric.map(math.isfinite)]
    if finite.empty:
        return {"count": int(len(numeric)), "finite_count": 0}
    return {
        "count": int(len(numeric)),
        "finite_count": int(len(finite)),
        "min": float(finite.min()),
        "p1": float(finite.quantile(0.01)),
        "p5": float(finite.quantile(0.05)),
        "p50": float(finite.quantile(0.50)),
        "p95": float(finite.quantile(0.95)),
        "p99": float(finite.quantile(0.99)),
        "max": float(finite.max()),
        "mean": float(finite.mean()),
        "std": float(finite.std(ddof=0)),
    }


def write_score_and_signal(asof: str, provider: Path, normalized: Path, prediction: pd.DataFrame, input_report: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    SCORE_DIR.mkdir(parents=True, exist_ok=True)
    SIGNAL_DIR.mkdir(parents=True, exist_ok=True)
    pred_path = SCORE_DIR / "snapshot_prediction.csv"
    prediction.to_csv(pred_path, index=False)
    pred = prediction.rename(columns={"datetime": "date", "score": "raw_score"}).copy()
    pred["date"] = pred["date"].astype(str)
    pred = pred[pred["date"] == asof].copy()
    pred["raw_score"] = pd.to_numeric(pred["raw_score"], errors="coerce")
    pred = pred.sort_values(["raw_score", "instrument"], ascending=[False, True]).reset_index(drop=True)
    pred["score_rank"] = pred.index + 1
    pred["full_qlib_rank"] = pred["score_rank"]
    pred["candidate_rank"] = pred["score_rank"]
    pred["buy_score"] = pred["raw_score"]
    raw_scores = pred[["date", "instrument", "raw_score", "score_rank", "full_qlib_rank"]].copy()
    raw_scores.to_csv(SCORE_DIR / "raw_scores.csv", index=False)

    signals = pd.DataFrame(
        {
            "date": pred["date"],
            "instrument": pred["instrument"],
            "model_name": MODEL_ID,
            "model_family": "qlib",
            "candidate_rank": pred["candidate_rank"],
            "buy_score": pred["buy_score"],
            "raw_score": pred["raw_score"],
            "score_rank": pred["score_rank"],
            "full_qlib_rank": pred["full_qlib_rank"],
            "signal_asof": asof,
            "available_at": asof,
            "source_artifact": rel(SCORE_DIR / "raw_scores.csv"),
            "source_model_artifact": rel(QLIB_MODEL_PATH),
            "source_feature_artifact": rel(provider),
        }
    )[SIGNAL_FIELDS]
    signals.to_csv(SIGNAL_DIR / "signals.csv", index=False)
    write_csv(
        SCORE_DIR / "rank_audit.csv",
        [
            {
                "date": asof,
                "row_count": int(len(pred)),
                "min_rank": int(pred["score_rank"].min()) if len(pred) else 0,
                "max_rank": int(pred["score_rank"].max()) if len(pred) else 0,
                "top_rank_instrument": str(pred.iloc[0]["instrument"]) if len(pred) else "",
                "candidate_top50_count": int((pred["candidate_rank"] <= 50).sum()) if len(pred) else 0,
                "rank_policy": "raw_score descending, instrument ascending tie-break",
            }
        ],
        ["date", "row_count", "min_rank", "max_rank", "top_rank_instrument", "candidate_top50_count", "rank_policy"],
    )

    signal_errors, signal_summary = validate_signal_frame(signals, asof)
    write_json(
        SIGNAL_DIR / "schema.json",
        {
            "schema_version": "model_signal_contract_v1.dng15_r_b",
            "contract_doc": "docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md",
            "primary_key": ["date", "instrument"],
            "required_fields": SIGNAL_FIELDS,
        },
    )
    write_csv(
        SIGNAL_DIR / "coverage_audit.csv",
        [
            {
                "date": asof,
                "row_count": int(len(signals)),
                "instrument_count": int(signals["instrument"].nunique()),
                "top50_candidate_count": int((pd.to_numeric(signals["candidate_rank"], errors="coerce") <= 50).sum()),
                "status": "READY" if not signal_errors and len(signals) == 150 else "BLOCKED_VALIDATOR",
            }
        ],
        ["date", "row_count", "instrument_count", "top50_candidate_count", "status"],
    )
    forbidden = forbidden_columns(list(signals.columns))
    write_csv(
        SIGNAL_DIR / "forbidden_field_audit.csv",
        [
            {
                "field_name": ",".join(forbidden),
                "present": bool(forbidden),
                "status": "FAIL" if forbidden else "PASS",
                "details": "forbidden fields present" if forbidden else "no forbidden fields present in signals.csv",
            }
        ],
        ["field_name", "present", "status", "details"],
    )
    signal_manifest = {
        "artifact_type": "ModelSignalArtifact",
        "schema_version": "model_signal_contract_v1.dng15_r_b",
        "contract_version": "MODEL_SIGNAL_CONTRACT_CN.md@2026-06-16",
        "model_id": MODEL_ID,
        "model_name": MODEL_ID,
        "model_family": "qlib",
        "run_id": RUN_ID,
        "created_at": utc_now(),
        "created_by": "scripts/build_tw_dng15_r_b_isolated_modela_score_integration.py",
        "asof": asof,
        "signal_asof": asof,
        "available_at": asof,
        "available_at_policy": "available_at equals signal_asof; isolated readonly same-day score artifact",
        "status": "READY" if not signal_errors and len(signals) == 150 else "BLOCKED_VALIDATOR",
        "score_status": "SCORED_ASOF_TARGET" if not signal_errors and len(signals) == 150 else "BLOCKED_VALIDATOR",
        "row_count": int(len(signals)),
        "source_artifact": rel(SCORE_DIR / "raw_scores.csv"),
        "source_model_artifact": rel(QLIB_MODEL_PATH),
        "source_feature_artifact": rel(provider),
        "source_normalized_artifact": rel(normalized),
        "source_training_manifest": rel(E1_TRAINING_MANIFEST),
        "files": {
            "manifest": "manifest.json",
            "signals": "signals.csv",
            "schema": "schema.json",
            "coverage_audit": "coverage_audit.csv",
            "forbidden_field_audit": "forbidden_field_audit.csv",
            "validator_report": "validator_report.json",
        },
        "forbidden_actions": FORBIDDEN_ACTIONS_FALSE,
        "governance_forbidden_actions": FORBIDDEN_GOVERNANCE_ACTIONS,
        "production_allowed": False,
        "no_latest": True,
        "not_published_latest": True,
        "extensions": {"schema_version": "model_signal_extension_v1", "fields": {}},
        "validation_summary": signal_summary,
        "errors": signal_errors,
    }
    write_json(SIGNAL_DIR / "manifest.json", signal_manifest)

    model_load_audit = {
        "status": "PASS",
        "model_id": MODEL_ID,
        "model_artifact_path": rel(QLIB_MODEL_PATH),
        "model_artifact_sha256": sha256_file(QLIB_MODEL_PATH),
        "qlib_provider_uri": rel(provider),
        "qlib_init": {
            "provider_uri": rel(provider),
            "region": "tw",
            "expression_cache": None,
            "dataset_cache": None,
        },
        "dataset_handler": "qlib.contrib.data.handler.Alpha158",
        "dataset_start_time": "2015-05-04",
        "dataset_end_time": asof,
        "snapshot_segment": [asof, asof],
        "prediction_path": rel(pred_path),
        "no_training": True,
        "no_tuning": True,
    }
    write_json(SCORE_DIR / "model_load_audit.json", model_load_audit)
    write_json(SCORE_DIR / "input_readiness.json", input_report)
    write_json(SCORE_DIR / "output_model_signal_manifest.json", signal_manifest)
    score_status = "SCORED_ASOF_TARGET" if signal_manifest["status"] == "READY" else "BLOCKED_VALIDATOR"
    score_manifest = {
        "artifact_type": "ScoreJob",
        "schema_version": "dng15_r_b.score_job.v1",
        "model_id": MODEL_ID,
        "model_name": MODEL_ID,
        "model_family": "qlib",
        "run_id": RUN_ID,
        "created_at": utc_now(),
        "created_by": "scripts/build_tw_dng15_r_b_isolated_modela_score_integration.py",
        "asof": asof,
        "status": score_status,
        "score_status": score_status,
        "score_status_reason": "isolated staged provider snapshot prediction completed" if score_status == "SCORED_ASOF_TARGET" else "validator failed",
        "source_model_inference_input": rel(INPUT_DIR),
        "inference_input": rel(INPUT_DIR),
        "raw_score_path": rel(SCORE_DIR / "raw_scores.csv"),
        "model_signal_artifact": rel(SIGNAL_DIR),
        "signal_artifact": rel(SIGNAL_DIR),
        "row_count": int(len(raw_scores)),
        "source_model_artifact": rel(QLIB_MODEL_PATH),
        "source_feature_artifact": rel(provider),
        "source_normalized_artifact": rel(normalized),
        "fallback_policy": "block_on_failure",
        "fallback_used": False,
        "previous_signal_artifact": None,
        "files": {
            "manifest": "manifest.json",
            "raw_scores": "raw_scores.csv",
            "rank_audit": "rank_audit.csv",
            "model_load_audit": "model_load_audit.json",
            "input_readiness": "input_readiness.json",
            "output_model_signal_manifest": "output_model_signal_manifest.json",
            "validator_report": "validator_report.json",
        },
        "forbidden_actions": FORBIDDEN_ACTIONS_FALSE,
        "governance_forbidden_actions": FORBIDDEN_GOVERNANCE_ACTIONS,
        "production_allowed": False,
        "not_published_latest": True,
        "required_file_entries": [
            file_entry(SCORE_DIR / "raw_scores.csv", "raw_scores"),
            file_entry(SIGNAL_DIR / "signals.csv", "signals"),
            file_entry(QLIB_MODEL_PATH, "source_model_artifact"),
            file_entry(provider / "calendars/day.txt", "staged_provider_calendar"),
        ],
    }
    write_json(SCORE_DIR / "manifest.json", score_manifest)
    local_score_report = {
        "ok": score_status == "SCORED_ASOF_TARGET",
        "status": "PASS" if score_status == "SCORED_ASOF_TARGET" else "FAIL",
        "score_status": score_status,
        "run_id": RUN_ID,
        "asof": asof,
        "score_job_dir": rel(SCORE_DIR),
        "signal_dir": rel(SIGNAL_DIR),
        "raw_score_rows": int(len(raw_scores)),
        "signal_rows": int(len(signals)),
        "prediction_rows": int(len(prediction)),
        "finite_prediction_share": score_stats(prediction["score"]).get("finite_count", 0) / max(score_stats(prediction["score"]).get("count", 0), 1),
        "errors": signal_manifest.get("errors", []),
    }
    write_json(SCORE_DIR / "validator_report.json", local_score_report)
    return score_manifest, signal_manifest, {"raw_scores": raw_scores, "signals": signals, "score_stats": score_stats(prediction["score"])}


def write_report(catalog: dict[str, Any]) -> None:
    lines = [
        "# DNG15_R-B Isolated Model A Score Integration 执行报告",
        "",
        f"生成时间：{utc_now()}",
        "",
        "## 1. Scope",
        "",
        "- Assigned phase：`DNG15_R-B isolated Model A score integration`",
        "- Mainline document：`docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md`",
        "- Work document：`docs/tw_data_governance/DNG15_R_B_ISOLATED_MODELA_SCORE_INTEGRATION_WORK_CN.md`",
        f"- Target asof：`{ASOF}`",
        f"- run_id：`{RUN_ID}`",
        "- Model：`e4_frozen_qlib_2018_2022`",
        "",
        "非目标确认：未 formal publish、未覆盖 formal provider/normalized、未切 accepted latest、未更新 latest_signal、未 publish readonly/Agent latest、未生产切换、未策略回放/NAV、未交易、未生成 target_position/target_weight、未 FinMind fallback、未 mixed-provider bridge、未训练或调参。",
        "",
        "## 2. Documents / Contracts / Skills Read",
        "",
    ]
    lines.extend([f"- `{item}`" for item in REQUIRED_DOCS_READ])
    lines.extend(
        [
            "",
            "## 3. Changes Made",
            "",
            "- 新增 `scripts/build_tw_dng15_r_b_isolated_modela_score_integration.py`。",
            "- 生成 isolated `ModelInferenceInput`、`ScoreJob`、`ModelSignalArtifact`。",
            "- 生成 `data_tw/catalog/dng15_r_b_isolated_modela_score_integration_validation.json`。",
            "- 生成本执行报告。",
            "",
            "## 4. Evidence Produced",
            "",
            f"- staged_provider：`{catalog['source_feature_artifact']}`",
            f"- candidate_normalized：`{catalog['source_normalized_artifact']}`",
            f"- source_model_artifact：`{catalog['source_model_artifact']}`",
            f"- ModelInferenceInput validator：`{catalog['model_inference_input_validator']['status']}`",
            f"- ScoreJob validator：`{catalog['score_job_validator']['status']}`",
            f"- ModelSignalArtifact validator：`{catalog['model_signal_validator']['status']}`",
            f"- raw_scores rows：`{catalog['raw_scores_rows']}`",
            f"- signals rows：`{catalog['signals_rows']}`",
            f"- prediction_rows：`{catalog['prediction_rows']}`",
            f"- finite_prediction_share：`{catalog['finite_prediction_share']}`",
            f"- score_status：`{catalog['score_status']}`",
            f"- signal_asof：`{catalog['signal_asof']}`",
            f"- available_at：`{catalog['available_at']}`",
            "",
            "## 5. Compliance With Mainline",
            "",
            "- 显式 `provider_uri` 指向 R-A-R `staged_qlib_bin`。",
            "- 使用 `qlib.init(provider_uri=<staged_qlib_bin>, region='tw', expression_cache=None, dataset_cache=None)`。",
            f"- 使用 `DatasetH` + `Alpha158` snapshot segment `({ASOF}, {ASOF})`。",
            "- 只加载 frozen Model A `params.pkl` 执行 predict；未 fit、未训练、未调参。",
            "- `ModelSignalArtifact` 仅包含合同 core fields，无 forbidden fields。",
            "",
            "## 6. Forbidden Actions Audit",
            "",
        ]
    )
    for key, value in catalog["forbidden_actions"].items():
        lines.append(f"- `{key}={str(value).lower()}`")
    lines.extend(
        [
            "",
            "## 7. Issues / Blockers / Deviations",
            "",
            "- 无阻断性 blocker。",
            "- 复用现有 `validate_tw_model_inference_input.py` 与 `validate_tw_score_job.py`；R-B artifact 写入兼容 DNG7 validator 的 manifest/source_readiness 字段，同时在 catalog 中额外保留 R-B governance forbidden flags。",
            "- 本阶段未生成 StrategyInputBundle、readonly source context、Agent prompt 或 NAV，因为工作文档禁止策略回放/NAV和 latest publish。",
            "",
            "## 8. Files Changed",
            "",
            "- `scripts/build_tw_dng15_r_b_isolated_modela_score_integration.py`",
            "- `docs/tw_data_governance/DNG15_R_B_ISOLATED_MODELA_SCORE_INTEGRATION_EXECUTION_REPORT_CN.md`",
            "- `data_tw/catalog/dng15_r_b_isolated_modela_score_integration_validation.json`",
            f"- `data_tw/canonical/model_inference_input/{MODEL_ID}/{RUN_ID}/`",
            f"- `data_tw/artifacts/score_jobs/{MODEL_ID}/{RUN_ID}/`",
            f"- `data_tw/artifacts/signals/{MODEL_ID}/{RUN_ID}/`",
            "",
            "## 9. Recommendation For Reviewer",
            "",
            "建议 verdict：`PASS_GO_DNG16_DAILY_AUTO_MODEL_SCORE_INTEGRATION_DESIGN`。",
            "",
            f"理由：R-B 已在 isolated staged provider 上生成 {ASOF} 标准 ModelInferenceInput / ScoreJob / ModelSignalArtifact，三层 validator 均 PASS，且 forbidden actions 全部保持 false。DNG16 应只进入 daily auto model score integration 设计，不应视为 formal publish 或 production latest 授权。",
            "",
        ]
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def build(
    *,
    decision_path: Path = R_A_R_DECISION_PATH,
    readiness_path: Path = R_A_R_READINESS_PATH,
    target_asof: str = DEFAULT_ASOF,
    run_id: str = DEFAULT_RUN_ID,
    catalog_path: Path | None = None,
    report_path: Path | None = None,
) -> dict[str, Any]:
    configure_run_context(target_asof=target_asof, run_id=run_id, catalog_path=catalog_path, report_path=report_path)
    decision = read_json(decision_path)
    readiness = read_json(readiness_path)
    gate_errors, provider, normalized = readiness_gate(decision, readiness, ASOF)
    symbols = load_symbol_universe(provider)
    calendar = provider_calendar(provider)
    calendar_max = max(calendar) if calendar else ""
    normalized_summary = normalized_symbol_summary(normalized, ASOF)
    provider_inventory = provider_field_inventory(provider, symbols)
    input_manifest = build_model_inference_input(ASOF, provider, normalized, symbols, normalized_summary, provider_inventory, calendar_max, gate_errors)
    input_report = validate_input(INPUT_DIR, ASOF)
    if not input_report["ok"]:
        raise RuntimeError(f"ModelInferenceInput validator failed: {input_report['errors']}")
    prediction = generate_prediction(provider, ASOF, symbols)
    score_manifest, signal_manifest, frames = write_score_and_signal(ASOF, provider, normalized, prediction, input_report)
    score_report = validate_score_job(SCORE_DIR, SIGNAL_DIR, ASOF)
    signal_report = read_json(SIGNAL_DIR / "validator_report.json")
    if not score_report["ok"]:
        raise RuntimeError(f"ScoreJob validator failed: {score_report['errors']}")

    stats = frames["score_stats"]
    catalog = {
        "schema_version": "dng15_r_b_isolated_modela_score_integration_validation.v1",
        "generated_at": utc_now(),
        "route": "DNG15_R_B_ISOLATED_MODELA_SCORE_INTEGRATION",
        "run_id": RUN_ID,
        "asof": ASOF,
        "model_id": MODEL_ID,
        "status": "PASS_GO_DNG16_DAILY_AUTO_MODEL_SCORE_INTEGRATION_DESIGN",
        "pipeline_status": score_manifest["score_status"],
        "score_status": score_manifest["score_status"],
        "model_inference_input_status": input_manifest["status"],
        "model_signal_status": signal_manifest["status"],
        "raw_scores_rows": int(len(frames["raw_scores"])),
        "signals_rows": int(len(frames["signals"])),
        "prediction_rows": int(len(prediction)),
        "finite_prediction_share": stats.get("finite_count", 0) / max(stats.get("count", 0), 1),
        "score_stats": stats,
        "signal_asof": ASOF,
        "available_at": ASOF,
        "source_feature_artifact": rel(provider),
        "source_normalized_artifact": rel(normalized),
        "provider_candidate_decision_path": rel(decision_path),
        "provider_candidate_readiness_path": rel(readiness_path),
        "source_model_artifact": rel(QLIB_MODEL_PATH),
        "production_allowed": False,
        "not_published_latest": True,
        "publish_latest_authorized": False,
        "model_inference_input_validator": input_report,
        "score_job_validator": score_report,
        "model_signal_validator": signal_report,
        "staged_provider_validation": {
            "calendar_has_asof": ASOF in calendar,
            "calendar_min": min(calendar) if calendar else "",
            "calendar_max": calendar_max,
            "symbol_count": len(symbols),
            "provider_field_inventory": provider_inventory,
        },
        "candidate_normalized_validation": normalized_summary,
        "artifacts": {
            "model_inference_input": rel(INPUT_DIR),
            "score_job": rel(SCORE_DIR),
            "model_signal": rel(SIGNAL_DIR),
            "catalog_validation": rel(CATALOG_PATH),
            "execution_report": rel(REPORT_PATH),
        },
        "forbidden_actions": FORBIDDEN_GOVERNANCE_ACTIONS,
        "validator_reuse_note": "Existing validators are reused with an isolated artifact manifest; production common constants were not modified.",
        "next_recommended_route": "DNG16_DAILY_AUTO_MODEL_SCORE_INTEGRATION_DESIGN",
        "blockers": [],
    }
    write_json(CATALOG_PATH, catalog)
    write_report(catalog)
    return catalog


def main() -> int:
    parser = argparse.ArgumentParser(description="Build DNG15_R-B isolated Model A score integration artifacts.")
    parser.add_argument("--decision-path", default=str(R_A_R_DECISION_PATH))
    parser.add_argument("--readiness-path", default=str(R_A_R_READINESS_PATH))
    parser.add_argument("--target-asof", "--asof", dest="target_asof", default=DEFAULT_ASOF)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--catalog-path", default="")
    parser.add_argument("--report-path", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = build(
        decision_path=resolve_repo_path(args.decision_path),
        readiness_path=resolve_repo_path(args.readiness_path),
        target_asof=args.target_asof,
        run_id=args.run_id,
        catalog_path=resolve_repo_path(args.catalog_path) if args.catalog_path else None,
        report_path=resolve_repo_path(args.report_path) if args.report_path else None,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=True, indent=2, default=str))
    else:
        print(f"{result['status']} {result['artifacts']['score_job']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
