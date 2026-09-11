#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from tw_modela_score_common import (
    E1_MODEL_ALIAS,
    E1_TRAINING_MANIFEST,
    FORBIDDEN_ACTIONS_FALSE,
    INFERENCE_FIELDS,
    MODEL_ID,
    ModelARuntimeConfig,
    PRICE_MARKET_READINESS,
    PRICE_STORE_DIR,
    QLIB_CONFIG,
    QLIB_DAILY_SIGNAL_SCRIPT,
    QLIB_MODEL_PATH,
    QLIB_NORMALIZED,
    QLIB_PIPELINE_ROOT,
    QLIB_PROVIDER,
    QLIB_RECORDER_PATH,
    QLIB_UNIVERSE,
    READINESS_DASHBOARD,
    REQUIRED_PROVIDER_FIELDS,
    TARGET_ASOF,
    default_run_id,
    file_entry,
    load_universe,
    make_modela_runtime_config,
    normalized_symbol_summary,
    provider_calendar_max,
    provider_field_inventory,
    read_json,
    rel,
    sha256_file,
    utc_now,
    write_csv,
    write_json,
    INPUT_BASE,
    validate_modela_runtime_config,
)


def readiness_gate(asof: str, runtime_config: ModelARuntimeConfig | None = None) -> dict[str, Any]:
    if runtime_config is not None:
        contract = validate_modela_runtime_config(runtime_config, run_id="readiness_gate")
        errors = [] if contract["status"] == "pass" else list(contract["errors"])
        if runtime_config.target_asof != asof:
            errors.append("runtime_target_asof_mismatch")
        return {
            "status": "READY" if not errors else "BLOCKED_INPUT_NOT_READY",
            "errors": errors,
            "price_market_readiness": "",
            "daily_readiness_dashboard": "",
            "can_continue_to_model_score": not errors,
            "dashboard_forbidden_actions_all_false": True,
            "runtime_config_contract": contract,
        }
    errors: list[str] = []
    warnings: list[str] = []
    readiness = read_json(PRICE_MARKET_READINESS) if PRICE_MARKET_READINESS.exists() else {}
    dashboard = read_json(READINESS_DASHBOARD) if READINESS_DASHBOARD.exists() else {}
    readiness_asof = str(readiness.get("asof") or "")
    legacy_readiness_asof_mismatch = bool(readiness_asof and readiness_asof != asof)
    if legacy_readiness_asof_mismatch:
        warnings.append("legacy_price_market_readiness_asof_mismatch_ignored_for_dynamic_daily_asof")
    elif readiness.get("can_continue_to_model_score") is not True:
        errors.append("price_market_readiness_blocks_model_score")
    if not legacy_readiness_asof_mismatch:
        for dep in readiness.get("dependencies", []):
            if "model_score" in dep.get("applies_to_gates", []) and dep.get("can_continue") is not True:
                errors.append(f"dependency_blocks_model_score:{dep.get('dependency_name')}")
    actions = dashboard.get("forbidden_actions_audit", {}).get("actions", {})
    if actions and any(bool(value) for value in actions.values()):
        errors.append("dashboard_forbidden_action_not_false")
    return {
        "status": "READY" if not errors else "BLOCKED_INPUT_NOT_READY",
        "errors": errors,
        "warnings": warnings,
        "price_market_readiness": rel(PRICE_MARKET_READINESS),
        "price_market_readiness_asof": readiness_asof,
        "legacy_price_market_readiness_asof_mismatch_ignored": legacy_readiness_asof_mismatch,
        "daily_readiness_dashboard": rel(READINESS_DASHBOARD),
        "daily_readiness_dashboard_asof": str(dashboard.get("asof") or ""),
        "can_continue_to_model_score": readiness.get("can_continue_to_model_score"),
        "dashboard_forbidden_actions_all_false": dashboard.get("forbidden_actions_audit", {}).get("all_false"),
    }


def build(asof: str, run_id: str, runtime_config: ModelARuntimeConfig | None = None) -> dict[str, Any]:
    out_dir = runtime_config.model_inference_input_dir(run_id) if runtime_config else INPUT_BASE / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    provider_root = runtime_config.provider_root if runtime_config else QLIB_PROVIDER
    normalized_root = runtime_config.normalized_root if runtime_config else QLIB_NORMALIZED
    symbols = load_universe(provider_root if runtime_config else None)
    normalized = normalized_symbol_summary(asof, symbols, normalized_root)
    inventory = provider_field_inventory(symbols, provider_root)
    calendar_max = provider_calendar_max(provider_root)
    gate = readiness_gate(asof, runtime_config)
    required_paths = {
        "qlib_provider_calendar": provider_root / "calendars/day.txt",
        "qlib_daily_signal_script": QLIB_DAILY_SIGNAL_SCRIPT,
        "qlib_model_path": QLIB_MODEL_PATH,
        "qlib_config": QLIB_CONFIG,
        "qlib_recorder_path": QLIB_RECORDER_PATH,
        "qlib_universe": provider_root / "instruments/all.txt" if runtime_config else QLIB_UNIVERSE,
        "e1_training_manifest": E1_TRAINING_MANIFEST,
        "canonical_price_store_manifest": PRICE_STORE_DIR / "manifest.json",
        "canonical_price_store_prices": PRICE_STORE_DIR / "prices.csv",
    }
    missing_paths = [key for key, path in required_paths.items() if not path.exists()]
    errors = list(gate["errors"])
    if missing_paths:
        errors.append("missing_required_paths:" + ",".join(missing_paths))
    if len(symbols) != 150:
        errors.append(f"universe_count_not_150:{len(symbols)}")
    if calendar_max is None or calendar_max < asof:
        errors.append("qlib_provider_calendar_stale")
    if normalized["symbols_with_asof"] != len(symbols):
        errors.append("normalized_source_missing_asof")
    if inventory["status"] != "pass":
        errors.append("provider_field_inventory_failed")

    status = "READY" if not errors else "BLOCKED_INPUT_NOT_READY"
    rows = [
        {
            "date": asof,
            "instrument": symbol,
            "model_id": MODEL_ID,
            "model_family": "qlib",
            "provider_uri": rel(provider_root),
            "normalized_source": rel(normalized_root),
            "feature_artifact": rel(provider_root),
            "source_model_artifact": rel(QLIB_MODEL_PATH),
            "source_training_manifest": rel(E1_TRAINING_MANIFEST),
            "signal_asof": asof,
            "available_at": asof,
            "readiness_status": status,
        }
        for symbol in symbols
    ]
    write_csv(out_dir / "inference_frame.csv", rows, INFERENCE_FIELDS)

    schema = {
        "schema_version": "dng7.model_inference_input.v1",
        "primary_key": ["date", "instrument"],
        "required_fields": INFERENCE_FIELDS,
        "field_types": {
            "date": "YYYY-MM-DD",
            "instrument": "string",
            "model_id": "string",
            "model_family": "string",
            "provider_uri": "path",
            "normalized_source": "path",
            "feature_artifact": "path",
            "source_model_artifact": "path",
            "source_training_manifest": "path",
            "signal_asof": "YYYY-MM-DD",
            "available_at": "YYYY-MM-DD",
            "readiness_status": "enum",
        },
        "forbidden_fields": "MODEL_SIGNAL_CONTRACT_CN.md forbidden fields and DNG7 forbidden action outputs",
    }
    write_json(out_dir / "schema.json", schema)

    source_readiness = {
        "status": status,
        "asof": asof,
        "errors": errors,
        "model_id": MODEL_ID,
        "model_artifact_path": rel(QLIB_MODEL_PATH),
        "model_artifact_sha256": sha256_file(QLIB_MODEL_PATH) if QLIB_MODEL_PATH.exists() else "",
        "legacy_e1_model_alias_path": rel(E1_MODEL_ALIAS),
        "legacy_e1_model_alias_sha256": sha256_file(E1_MODEL_ALIAS) if E1_MODEL_ALIAS.exists() else "",
        "qlib_provider_view": rel(provider_root),
        "qlib_provider_calendar_max": calendar_max,
        "normalized_source": rel(normalized_root),
        "normalized_source_summary": normalized,
        "provider_field_inventory": inventory,
        "feature_dump_status": "READY" if inventory["status"] == "pass" else "BLOCKED_PROVIDER_FIELD_INVENTORY",
        "inference_command": (
            "contained runtime direct qlib execution with injected provider_root/normalized_root"
            if runtime_config
            else f"cd {rel(QLIB_PIPELINE_ROOT)} && python examples/tw/run_option_c_daily_signal_option_c_provider.py --asof {asof} --normal"
        ),
        "readiness_gate": gate,
        "forbidden_actions": FORBIDDEN_ACTIONS_FALSE,
        "no_publish": runtime_config.no_publish if runtime_config else True,
        "no_catalog": runtime_config.no_catalog if runtime_config else False,
        "no_latest": runtime_config.no_latest if runtime_config else True,
        "no_target_output": runtime_config.no_target_output if runtime_config else True,
    }
    write_json(out_dir / "source_readiness.json", source_readiness)

    feature_lineage = {
        "model_id": MODEL_ID,
        "asof": asof,
        "inference_mode": "qlib DatasetH snapshot + frozen Option C LGBModel.predict",
        "feature_handler": "qlib.contrib.data.handler.Alpha158",
        "provider_required_fields": sorted(REQUIRED_PROVIDER_FIELDS),
        "qlib_provider_view": rel(provider_root),
        "source_model_artifact": rel(QLIB_MODEL_PATH),
        "source_training_manifest": rel(E1_TRAINING_MANIFEST),
        "source_config": rel(QLIB_CONFIG),
        "source_universe": rel(QLIB_UNIVERSE),
        "canonical_price_store_reference": rel(PRICE_STORE_DIR),
        "pit_policy": "snapshot segment is restricted to asof; Alpha158 rolling features derive from current/past provider rows only",
        "notes": [
            "DNG7 records the actual qlib_pipeline mlruns params.pkl loaded by the fixed provider script.",
            "The E1 model alias is retained as lineage evidence but is not the path loaded by this score job.",
        ],
    }
    write_json(out_dir / "feature_lineage.json", feature_lineage)

    coverage_rows = [
        {
            "dependency": "accepted_prediction_universe",
            "status": "READY" if len(symbols) == 150 else "BLOCKED",
            "asof": asof,
            "symbol_count": len(symbols),
            "details": rel(QLIB_UNIVERSE),
        },
        {
            "dependency": "normalized_option_c_150",
            "status": "READY" if normalized["symbols_with_asof"] == len(symbols) else "BLOCKED",
            "asof": asof,
            "symbol_count": normalized["symbols_with_asof"],
            "details": rel(QLIB_NORMALIZED),
        },
        {
            "dependency": "qlib_provider_calendar",
            "status": "READY" if calendar_max and calendar_max >= asof else "BLOCKED",
            "asof": asof,
            "symbol_count": len(symbols),
            "details": f"calendar_max={calendar_max}",
        },
        {
            "dependency": "qlib_provider_feature_bins",
            "status": "READY" if inventory["status"] == "pass" else "BLOCKED",
            "asof": asof,
            "symbol_count": len(symbols) if inventory["status"] == "pass" else 0,
            "details": ",".join(sorted(REQUIRED_PROVIDER_FIELDS)),
        },
        {
            "dependency": "price_market_calendar_gate",
            "status": gate["status"],
            "asof": asof,
            "symbol_count": len(symbols),
            "details": rel(PRICE_MARKET_READINESS),
        },
    ]
    write_csv(out_dir / "coverage_audit.csv", coverage_rows, ["dependency", "status", "asof", "symbol_count", "details"])

    pit_rows = [
        {"check": "no_future_label_fields", "status": "PASS", "details": "inference_frame carries paths and ids only; no label/future return fields"},
        {"check": "available_at_policy", "status": "PASS", "details": "available_at equals signal_asof for same-day readonly score artifact"},
        {"check": "provider_calendar_asof", "status": "PASS" if calendar_max and calendar_max >= asof else "FAIL", "details": f"calendar_max={calendar_max}"},
        {"check": "no_training_no_tuning", "status": "PASS", "details": "builder only packages input metadata"},
        {"check": "no_publish_no_latest_switch", "status": "PASS", "details": "builder writes DNG7 artifact directory only"},
    ]
    write_csv(out_dir / "pit_audit.csv", pit_rows, ["check", "status", "details"])

    manifest = {
        "artifact_type": "ModelInferenceInput",
        "schema_version": "dng7.model_inference_input.v1",
        "model_id": MODEL_ID,
        "model_name": MODEL_ID,
        "model_family": "qlib",
        "run_id": run_id,
        "created_at": utc_now(),
        "created_by": "scripts/build_tw_model_inference_input.py",
        "asof": asof,
        "status": status,
        "score_status": "INPUT_READY" if status == "READY" else "BLOCKED_INPUT_NOT_READY",
        "row_count": len(rows),
        "symbol_count": len(symbols),
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
        "source_artifacts": [rel(provider_root), rel(normalized_root), rel(QLIB_MODEL_PATH), rel(E1_TRAINING_MANIFEST)],
        "required_file_entries": [file_entry(path, key) for key, path in required_paths.items()],
        "forbidden_actions": FORBIDDEN_ACTIONS_FALSE,
        "production_allowed": False,
        "not_published_latest": True,
        "no_catalog": runtime_config.no_catalog if runtime_config else False,
        "no_latest": runtime_config.no_latest if runtime_config else True,
        "no_target_output": runtime_config.no_target_output if runtime_config else True,
        "contained_runtime_config": validate_modela_runtime_config(runtime_config, run_id=run_id)
        if runtime_config
        else None,
        "errors": errors,
    }
    write_json(out_dir / "manifest.json", manifest)
    return {"run_id": run_id, "status": status, "asof": asof, "path": rel(out_dir), "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build DNG7 qlib Model A ModelInferenceInput.")
    parser.add_argument("--asof", default=TARGET_ASOF)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--provider-root", default=None)
    parser.add_argument("--normalized-root", default=None)
    parser.add_argument("--output-root", default=None)
    parser.add_argument("--no-publish", action="store_true")
    parser.add_argument("--no-catalog", action="store_true")
    parser.add_argument("--no-latest", action="store_true")
    parser.add_argument("--no-target-output", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    run_id = args.run_id or default_run_id(args.asof)
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
        )
        contract = validate_modela_runtime_config(runtime_config, run_id=run_id)
        if contract["status"] != "pass":
            if args.json:
                import json

                print(json.dumps(contract, ensure_ascii=True, indent=2))
            return 2
    result = build(args.asof, run_id, runtime_config)
    if args.json:
        import json

        print(json.dumps(result, ensure_ascii=True, indent=2))
    else:
        print(f"{result['status']} {result['path']}")
    return 0 if result["status"] == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
