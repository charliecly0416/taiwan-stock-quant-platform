#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import pickle
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from tw_modela_score_common import (
    CATALOG_VALIDATION_PATH,
    E1_TRAINING_MANIFEST,
    EXECUTION_REPORT_PATH,
    FORBIDDEN_ACTIONS_FALSE,
    MODEL_ID,
    ModelARuntimeConfig,
    QLIB_DAILY_SIGNAL_SCRIPT,
    QLIB_DAILY_SIGNAL_ROOT,
    QLIB_MODEL_PATH,
    QLIB_PIPELINE_ROOT,
    QLIB_PROVIDER,
    SCORE_BASE,
    SIGNAL_BASE,
    SIGNAL_FIELDS,
    TARGET_ASOF,
    default_run_id,
    file_entry,
    make_modela_runtime_config,
    parse_run_json,
    read_json,
    rel,
    sha256_file,
    utc_now,
    validate_signal_frame,
    validate_modela_runtime_config,
    write_csv,
    write_json,
)
from validate_tw_model_inference_input import validate as validate_input


def qlib_python_executable() -> str:
    return os.getenv("TW_MODELA_SCORE_JOB_PYTHON") or sys.executable


def qlib_subprocess_command(asof: str) -> list[str]:
    return [
        qlib_python_executable(),
        "examples/tw/run_option_c_daily_signal_option_c_provider.py",
        "--asof",
        asof,
        "--normal",
    ]


def run_qlib(asof: str, runtime_config: ModelARuntimeConfig | None = None, run_id: str | None = None) -> tuple[dict[str, Any], str, str]:
    if runtime_config is not None:
        if runtime_config.allow_real_execution is not True:
            raise RuntimeError("contained_runtime_real_execution_not_enabled")
        contract = validate_modela_runtime_config(runtime_config, run_id=run_id or default_run_id(asof))
        if contract["status"] != "pass":
            raise RuntimeError(json.dumps({"contained_runtime_contract": contract}, ensure_ascii=True))

        import qlib
        from qlib.contrib.model.gbdt import LGBModel
        from qlib.data.dataset import DatasetH

        symbols = []
        instruments = runtime_config.provider_root / "instruments/all.txt"
        if instruments.exists():
            symbols = [
                line.split()[0].strip().upper()
                for line in instruments.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        symbols = sorted(symbols)
        qlib_run_dir = runtime_config.qlib_run_dir(run_id or default_run_id(asof))
        qlib_run_dir.mkdir(parents=True, exist_ok=True)
        qlib.init(provider_uri=str(runtime_config.provider_root), region="tw", expression_cache=None, dataset_cache=None)
        handler_conf = {
            "class": "Alpha158",
            "module_path": "qlib.contrib.data.handler",
            "kwargs": {
                "start_time": "2015-05-04",
                "end_time": asof,
                "fit_start_time": "2015-05-04",
                "fit_end_time": "2020-12-31",
                "instruments": symbols,
            },
        }
        dataset = DatasetH(handler=handler_conf, segments={"snapshot": (asof, asof)})
        model = pickle.load(QLIB_MODEL_PATH.open("rb"))
        if not isinstance(model, LGBModel):
            raise TypeError(f"unexpected model type: {type(model)}")
        prediction = model.predict(dataset, segment="snapshot").rename("score").to_frame().reset_index()
        prediction.to_csv(qlib_run_dir / "prediction.csv", index=False)
        payload = {
            "run_id": qlib_run_dir.name,
            "run_dir": str(qlib_run_dir),
            "artifacts": {"prediction": str(qlib_run_dir / "prediction.csv")},
            "provider_uri": rel(runtime_config.provider_root),
            "normalized_source": rel(runtime_config.normalized_root),
            "contained_runtime": True,
            "provider_switch_performed": False,
            "provider_mutation_triggered": False,
            "latest_write_performed": False,
        }
        write_json(qlib_run_dir / "run_metadata.json", payload)
        return payload, json.dumps(payload, ensure_ascii=True), ""

    cmd = qlib_subprocess_command(asof)
    proc = subprocess.run(
        cmd,
        cwd=QLIB_PIPELINE_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        payload = {}
        try:
            payload = parse_run_json(proc.stdout)
        except Exception:
            pass
        raise RuntimeError(json.dumps({"qlib_returncode": proc.returncode, "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-4000:], "payload": payload}))
    return parse_run_json(proc.stdout), proc.stdout, proc.stderr


def adapt_prediction(
    prediction_path: Path,
    asof: str,
    score_dir: Path,
    signal_dir: Path,
    runtime_config: ModelARuntimeConfig | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    pred = pd.read_csv(prediction_path)
    if "datetime" not in pred.columns or "instrument" not in pred.columns or "score" not in pred.columns:
        raise RuntimeError("qlib prediction.csv must contain datetime,instrument,score")
    raw = pred.rename(columns={"datetime": "date", "score": "raw_score"}).copy()
    raw["date"] = raw["date"].astype(str)
    raw = raw[raw["date"] == asof].copy()
    raw["raw_score"] = pd.to_numeric(raw["raw_score"], errors="coerce")
    raw = raw.sort_values(["raw_score", "instrument"], ascending=[False, True]).reset_index(drop=True)
    raw["score_rank"] = raw.index + 1
    raw["full_qlib_rank"] = raw["score_rank"]
    raw["candidate_rank"] = raw["score_rank"]
    raw["buy_score"] = raw["raw_score"]
    raw_scores = raw[["date", "instrument", "raw_score", "score_rank", "full_qlib_rank"]].copy()
    raw_scores.to_csv(score_dir / "raw_scores.csv", index=False)

    signals = pd.DataFrame(
        {
            "date": raw["date"],
            "instrument": raw["instrument"],
            "model_name": MODEL_ID,
            "model_family": "qlib",
            "candidate_rank": raw["candidate_rank"],
            "buy_score": raw["buy_score"],
            "raw_score": raw["raw_score"],
            "score_rank": raw["score_rank"],
            "full_qlib_rank": raw["full_qlib_rank"],
            "signal_asof": asof,
            "available_at": asof,
            "source_artifact": rel(prediction_path),
            "source_model_artifact": rel(QLIB_MODEL_PATH),
            "source_feature_artifact": rel(runtime_config.provider_root if runtime_config else QLIB_PROVIDER),
        }
    )
    signals = signals[SIGNAL_FIELDS]
    signals.to_csv(signal_dir / "signals.csv", index=False)
    rank_rows = [
        {
            "date": asof,
            "row_count": int(len(raw)),
            "min_rank": int(raw["score_rank"].min()) if len(raw) else 0,
            "max_rank": int(raw["score_rank"].max()) if len(raw) else 0,
            "top_rank_instrument": str(raw.iloc[0]["instrument"]) if len(raw) else "",
            "candidate_top50_count": int((raw["candidate_rank"] <= 50).sum()) if len(raw) else 0,
            "rank_policy": "raw_score descending, instrument ascending tie-break",
        }
    ]
    write_csv(score_dir / "rank_audit.csv", rank_rows, ["date", "row_count", "min_rank", "max_rank", "top_rank_instrument", "candidate_top50_count", "rank_policy"])
    return raw_scores, signals


def write_signal_sidecars(
    signal_dir: Path,
    signals: pd.DataFrame,
    asof: str,
    run_id: str,
    source_run: dict[str, Any],
    runtime_config: ModelARuntimeConfig | None = None,
    source_acquisition_run_id: str = "",
    decision_cutoff: str = "",
) -> dict[str, Any]:
    errors, summary = validate_signal_frame(signals, asof)
    validator_report = {
        "ok": not errors,
        "status": "PASS" if not errors else "FAIL",
        "artifact_type": "ModelSignalArtifact",
        "target_asof": asof,
        "signal_dir": rel(signal_dir),
        "checked_at": utc_now(),
        "errors": errors,
        "signal_rows": int(len(signals)),
        "signal_summary": summary,
    }
    schema = {
        "schema_version": "model_signal_contract_v1.dng7",
        "contract_doc": "docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md",
        "primary_key": ["date", "instrument"],
        "required_fields": SIGNAL_FIELDS,
        "field_types": {
            "date": "YYYY-MM-DD",
            "instrument": "string",
            "model_name": "string",
            "model_family": "string",
            "candidate_rank": "numeric",
            "buy_score": "numeric",
            "raw_score": "numeric",
            "score_rank": "numeric",
            "full_qlib_rank": "numeric",
            "signal_asof": "YYYY-MM-DD",
            "available_at": "YYYY-MM-DD",
            "source_artifact": "path",
            "source_model_artifact": "path",
        "source_feature_artifact": "path",
        "source_acquisition_run_id": "string; same-run source acquisition binding",
        "decision_cutoff": "RFC3339 UTC; captured before scoring",
        },
    }
    write_json(signal_dir / "schema.json", schema)
    coverage_rows = [
        {
            "date": asof,
            "row_count": int(len(signals)),
            "instrument_count": int(signals["instrument"].nunique()),
            "top50_candidate_count": int((pd.to_numeric(signals["candidate_rank"], errors="coerce") <= 50).sum()),
            "status": "READY" if not errors and len(signals) == 150 else "BLOCKED_VALIDATOR",
        }
    ]
    write_csv(signal_dir / "coverage_audit.csv", coverage_rows, ["date", "row_count", "instrument_count", "top50_candidate_count", "status"])
    write_csv(
        signal_dir / "forbidden_field_audit.csv",
        [{"field_name": "", "present": False, "status": "PASS", "details": "no forbidden fields present in signals.csv"}],
        ["field_name", "present", "status", "details"],
    )
    manifest = {
        "artifact_type": "ModelSignalArtifact",
        "schema_version": "model_signal_contract_v1.dng7",
        "contract_version": "MODEL_SIGNAL_CONTRACT_CN.md@2026-06-16",
        "model_id": MODEL_ID,
        "model_name": MODEL_ID,
        "model_family": "qlib",
        "run_id": run_id,
        "created_at": utc_now(),
        "created_by": "scripts/run_tw_model_score_job.py",
        "asof": asof,
        "signal_asof": asof,
        "available_at_policy": "available_at equals signal_asof; readonly same-day score artifact",
        "status": "READY" if not errors and len(signals) == 150 else "BLOCKED_VALIDATOR",
        "score_status": "SCORED_ASOF_TARGET" if not errors and len(signals) == 150 else "BLOCKED_VALIDATOR",
        "row_count": int(len(signals)),
        "source_artifact": source_run.get("artifacts", {}).get("prediction", source_run.get("run_dir", "")),
        "source_model_artifact": rel(QLIB_MODEL_PATH),
        "source_feature_artifact": rel(runtime_config.provider_root if runtime_config else QLIB_PROVIDER),
        "source_acquisition_run_id": source_acquisition_run_id,
        "decision_cutoff": decision_cutoff,
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
        "production_allowed": False,
        "not_published_latest": True,
        "no_catalog": runtime_config.no_catalog if runtime_config else False,
        "no_latest": runtime_config.no_latest if runtime_config else True,
        "no_target_output": runtime_config.no_target_output if runtime_config else True,
        "extensions": {"schema_version": "model_signal_extension_v1", "fields": {}},
        "validation_summary": summary,
        "errors": errors,
    }
    write_json(signal_dir / "manifest.json", manifest)
    write_json(signal_dir / "validator_report.json", validator_report)
    return manifest


def write_report(
    run_id: str,
    asof: str,
    status: str,
    input_report: dict[str, Any],
    score_report: dict[str, Any],
    signal_manifest: dict[str, Any],
    normal_run: dict[str, Any],
    runtime_config: ModelARuntimeConfig | None = None,
) -> None:
    input_path = (
        rel(runtime_config.model_inference_input_dir(run_id))
        if runtime_config
        else f"data_tw/canonical/model_inference_input/{MODEL_ID}/{run_id}"
    )
    score_path = rel(runtime_config.score_job_dir(run_id)) if runtime_config else f"data_tw/artifacts/score_jobs/{MODEL_ID}/{run_id}"
    signal_path = rel(runtime_config.model_signal_dir(run_id)) if runtime_config else f"data_tw/artifacts/signals/{MODEL_ID}/{run_id}"
    lines = [
        "# DNG7 ModelA Score Pipeline 执行报告",
        "",
        f"生成时间：{utc_now()}",
        "",
        "## 1. 结论",
        "",
        f"- 执行状态：`{status}`",
        f"- run_id：`{run_id}`",
        f"- 目标 asof：`{asof}`",
        f"- 路径：`TRUE_LOCAL_INFERENCE`",
        f"- 是否生成 {asof} qlib Model A score：`{'YES' if status == 'SCORED_ASOF_TARGET' else 'NO'}`",
        "",
        "## 2. ModelInferenceInput",
        "",
        f"- validator：`{input_report.get('status')}`",
        f"- rows：`{input_report.get('row_count')}`",
        f"- path：`{input_path}`",
        "",
        "## 3. ScoreJob",
        "",
        f"- validator：`{score_report.get('status')}`",
        f"- qlib source run：`{normal_run.get('run_id')}`",
        f"- raw_scores rows：`{score_report.get('raw_score_rows')}`",
        f"- path：`{score_path}`",
        "",
        "## 4. ModelSignalArtifact",
        "",
        f"- status：`{signal_manifest.get('status')}`",
        f"- rows：`{signal_manifest.get('row_count')}`",
        f"- path：`{signal_path}`",
        "",
        "## 5. Forbidden Action Audit",
        "",
        "- 未训练、未调参、未触发 LTR Model B。",
        "- 未抓数、未 provider refresh/publish、未切 qlib accepted latest。",
        "- 未 publish readonly/Agent latest。",
        "- 未回放、未生成 ReplayResult/NAV、未 broker/order/quick-trade、未生成 target_position/target_weight。",
        "",
        "## 6. DNG8 建议",
        "",
        "ModelSignalArtifact validator 通过后，可进入 DNG8 的只读策略输入合同阶段；仍不得默认接入 readonly/Agent/latest 或 replay。",
        "",
    ]
    report_path = runtime_config.execution_report_path(run_id) if runtime_config else EXECUTION_REPORT_PATH
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def run(
    asof: str,
    run_id: str,
    input_dir: Path,
    runtime_config: ModelARuntimeConfig | None = None,
    source_acquisition_run_id: str = "",
    decision_cutoff: str = "",
) -> dict[str, Any]:
    score_dir = runtime_config.score_job_dir(run_id) if runtime_config else SCORE_BASE / run_id
    signal_dir = runtime_config.model_signal_dir(run_id) if runtime_config else SIGNAL_BASE / run_id
    score_dir.mkdir(parents=True, exist_ok=True)
    signal_dir.mkdir(parents=True, exist_ok=True)

    input_report = validate_input(input_dir, asof)
    if not input_report["ok"]:
        raise RuntimeError(f"ModelInferenceInput validator failed: {input_report['errors']}")

    normal_payload, stdout, stderr = run_qlib(asof, runtime_config, run_id)
    normal_run_dir = Path(normal_payload["run_dir"])
    if not normal_run_dir.is_absolute():
        normal_run_dir = QLIB_PIPELINE_ROOT / normal_run_dir
    source_meta = read_json(normal_run_dir / "run_metadata.json")
    prediction_path = normal_run_dir / "prediction.csv"
    raw_scores, signals = adapt_prediction(prediction_path, asof, score_dir, signal_dir, runtime_config)
    signal_manifest = write_signal_sidecars(
        signal_dir,
        signals,
        asof,
        run_id,
        source_meta,
        runtime_config,
        source_acquisition_run_id,
        decision_cutoff,
    )

    model_load_audit = {
        "status": "PASS",
        "model_id": MODEL_ID,
        "model_artifact_path": rel(QLIB_MODEL_PATH),
        "model_artifact_sha256": sha256_file(QLIB_MODEL_PATH),
        "qlib_source_run_id": normal_payload["run_id"],
        "qlib_source_run_dir": normal_payload["run_dir"],
        "qlib_command": (
            "direct qlib DatasetH scoring with injected contained provider_root"
            if runtime_config
            else " ".join(qlib_subprocess_command(asof))
        ),
        "stdout_tail": stdout[-2000:],
        "stderr_tail": stderr[-2000:],
        "loaded_by": rel(QLIB_DAILY_SIGNAL_SCRIPT),
        "provider_root": rel(runtime_config.provider_root if runtime_config else QLIB_PROVIDER),
        "normalized_root": rel(runtime_config.normalized_root) if runtime_config else "",
        "no_training": True,
        "no_tuning": True,
    }
    write_json(score_dir / "model_load_audit.json", model_load_audit)
    write_json(score_dir / "input_readiness.json", input_report)
    write_json(score_dir / "output_model_signal_manifest.json", signal_manifest)

    score_status = "SCORED_ASOF_TARGET" if signal_manifest["status"] == "READY" else "BLOCKED_VALIDATOR"
    manifest = {
        "artifact_type": "ScoreJob",
        "schema_version": "dng7.score_job.v1",
        "model_id": MODEL_ID,
        "model_name": MODEL_ID,
        "model_family": "qlib",
        "run_id": run_id,
        "created_at": utc_now(),
        "created_by": "scripts/run_tw_model_score_job.py",
        "asof": asof,
        "status": score_status,
        "score_status": score_status,
        "inference_input": rel(input_dir),
        "qlib_source_run": normal_payload,
        "source_acquisition_run_id": source_acquisition_run_id,
        "decision_cutoff": decision_cutoff,
        "row_count": int(len(raw_scores)),
        "signal_artifact": rel(signal_dir),
        "source_model_artifact": rel(QLIB_MODEL_PATH),
        "source_feature_artifact": rel(runtime_config.provider_root if runtime_config else QLIB_PROVIDER),
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
        "production_allowed": False,
        "not_published_latest": True,
        "required_file_entries": [
            file_entry(score_dir / "raw_scores.csv", "raw_scores"),
            file_entry(signal_dir / "signals.csv", "signals"),
            file_entry(QLIB_MODEL_PATH, "source_model_artifact"),
            file_entry((runtime_config.provider_root if runtime_config else QLIB_PROVIDER) / "calendars/day.txt", "qlib_provider_calendar"),
        ],
        "contained_runtime_config": validate_modela_runtime_config(runtime_config, run_id=run_id)
        if runtime_config
        else None,
    }
    write_json(score_dir / "manifest.json", manifest)

    score_report = {
        "ok": score_status == "SCORED_ASOF_TARGET",
        "status": "PASS" if score_status == "SCORED_ASOF_TARGET" else "FAIL",
        "score_status": score_status,
        "run_id": run_id,
        "asof": asof,
        "score_job_dir": rel(score_dir),
        "signal_dir": rel(signal_dir),
        "raw_score_rows": int(len(raw_scores)),
        "signal_rows": int(len(signals)),
        "qlib_source_run_id": normal_payload["run_id"],
        "errors": signal_manifest.get("errors", []),
    }
    write_json(score_dir / "validator_report.json", score_report)
    catalog = {
        "generated_at": utc_now(),
        "run_id": run_id,
        "asof": asof,
        "model_id": MODEL_ID,
        "pipeline_status": score_status,
        "target_asof_score_generated": score_status == "SCORED_ASOF_TARGET",
        "true_20260625_score_generated": score_status == "SCORED_ASOF_TARGET" if asof == "2026-06-25" else False,
        "mode": "TRUE_LOCAL_INFERENCE",
        "model_inference_input_validator": input_report,
        "score_job_validator": score_report,
        "model_signal_status": signal_manifest["status"],
        "artifacts": {
            "model_inference_input": rel(input_dir),
            "score_job": rel(score_dir),
            "model_signal": rel(signal_dir),
            "qlib_source_run": normal_payload.get("run_dir"),
        },
        "forbidden_actions": FORBIDDEN_ACTIONS_FALSE,
        "blockers": [],
    }
    validation_path = runtime_config.pipeline_validation_path(run_id) if runtime_config else CATALOG_VALIDATION_PATH
    write_json(validation_path, catalog)
    write_report(run_id, asof, score_status, input_report, score_report, signal_manifest, normal_payload, runtime_config)
    return catalog


def main() -> int:
    parser = argparse.ArgumentParser(description="Run DNG7 qlib Model A ScoreJob.")
    parser.add_argument("--asof", default=TARGET_ASOF)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--source-acquisition-run-id", default="")
    parser.add_argument(
        "--decision-cutoff",
        default="",
        help="RFC3339 UTC cutoff captured before source-backed scoring; empty means PIT cutoff is unproven.",
    )
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--provider-root", default=None)
    parser.add_argument("--normalized-root", default=None)
    parser.add_argument("--output-root", default=None)
    parser.add_argument("--no-publish", action="store_true")
    parser.add_argument("--no-catalog", action="store_true")
    parser.add_argument("--no-latest", action="store_true")
    parser.add_argument("--no-target-output", action="store_true")
    parser.add_argument("--allow-contained-real-execution", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    runtime_config = None
    if args.provider_root or args.normalized_root or args.output_root:
        if not (args.provider_root and args.normalized_root and args.output_root):
            parser.error("--provider-root, --normalized-root, and --output-root must be supplied together")
        runtime_config = make_modela_runtime_config(
            target_asof=args.asof,
            provider_root=args.provider_root,
            normalized_root=args.normalized_root,
            output_root=args.output_root,
            no_publish=args.no_publish,
            no_catalog=args.no_catalog,
            no_latest=args.no_latest,
            no_target_output=args.no_target_output,
            allow_real_execution=args.allow_contained_real_execution,
        )
        contract = validate_modela_runtime_config(runtime_config, run_id=args.run_id)
        if contract["status"] != "pass":
            if args.json:
                print(json.dumps(contract, ensure_ascii=True, indent=2))
            return 2
    result = run(
        args.asof,
        args.run_id,
        Path(args.input_dir),
        runtime_config,
        args.source_acquisition_run_id,
        args.decision_cutoff,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=True, indent=2))
    else:
        print(f"{result['pipeline_status']} {result['artifacts']['score_job']}")
    return 0 if result["pipeline_status"] == "SCORED_ASOF_TARGET" else 1


if __name__ == "__main__":
    raise SystemExit(main())
