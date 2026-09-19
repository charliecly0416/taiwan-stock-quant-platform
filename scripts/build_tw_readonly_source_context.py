#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

ASOF = "2026-06-25"
STRATEGY_ID = "top50_exit_one_worst_sell"
STRATEGY_BUNDLE_ID = "top50_exit_one_worst_sell_dng10_modela"
STRATEGY_RUN_ID = "dng10_strategy_input_bundle_20260625"
SOURCE_CONTEXT_RUN_ID = "dng10_modela_20260625"
MODEL_A_ID = "e4_frozen_qlib_2018_2022"
MODEL_B_ID = "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025"

SIGNAL_ROOT = ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/dng7_modela_20260625"
PRICE_ROOT = ROOT / "data_tw/canonical/price_store/tw_equity_daily/dng2_r_price_market_calendar_20260625"
MARKET_ROOT = ROOT / "data_tw/canonical/market_feature_store/twii_daily/dng2_r_price_market_calendar_20260625"
PRICE_READINESS = ROOT / "data_tw/catalog/readiness_matrix/2026-06-25/price_market_calendar.json"
ORTHOGONAL_READINESS = ROOT / "data_tw/catalog/readiness_matrix/2026-06-25/orthogonal_feature_store.json"
MODEL_B_SCORE_JOB = ROOT / "data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/dng8_modelb_ltr_20260625"
CALENDAR_PATH = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt"

FORBIDDEN_ACTION_FLAGS = {
    "real_data_fetch_triggered": False,
    "provider_refresh_triggered": False,
    "provider_publish_triggered": False,
    "qlib_accepted_latest_switched": False,
    "readonly_latest_published": False,
    "agent_prompt_published": False,
    "model_training_triggered": False,
    "model_tuning_triggered": False,
    "model_inference_triggered": False,
    "model_score_generated": False,
    "ltr_score_generated": False,
    "strategy_replay_triggered": False,
    "replay_result_nav_generated": False,
    "broker_order_quick_trade_triggered": False,
    "target_position_or_weight_generated": False,
}

SIGNAL_REQUIRED_FIELDS = [
    "date",
    "instrument",
    "model_name",
    "model_family",
    "candidate_rank",
    "buy_score",
    "raw_score",
    "score_rank",
    "full_qlib_rank",
    "signal_asof",
    "available_at",
    "source_artifact",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path | str) -> str:
    path_obj = Path(path)
    try:
        return str(path_obj.resolve().relative_to(ROOT.resolve()))
    except (FileNotFoundError, ValueError):
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def csv_header_and_count(path: Path) -> tuple[list[str], int]:
    if not path.exists():
        return [], 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration:
            return [], 0
        return header, sum(1 for _ in reader)


def read_signal_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows.sort(key=lambda row: (int(float(row.get("candidate_rank") or 999999)), row.get("instrument", "")))
    return rows


def compact_signal(row: dict[str, str]) -> dict[str, Any]:
    return {
        "instrument": row.get("instrument"),
        "candidate_rank": int(float(row.get("candidate_rank") or 0)),
        "buy_score": float(row.get("buy_score") or 0.0),
        "raw_score": float(row.get("raw_score") or 0.0),
        "score_rank": int(float(row.get("score_rank") or 0)),
        "full_qlib_rank": int(float(row.get("full_qlib_rank") or 0)),
        "model_name": row.get("model_name"),
        "signal_asof": row.get("signal_asof"),
    }


def copy_csv_rows_for_date(src: Path, dst: Path, date_field: str, asof: str) -> int:
    dst.parent.mkdir(parents=True, exist_ok=True)
    with src.open("r", encoding="utf-8", newline="") as in_handle, dst.open("w", encoding="utf-8", newline="") as out_handle:
        reader = csv.DictReader(in_handle)
        writer = csv.DictWriter(out_handle, fieldnames=reader.fieldnames or [])
        writer.writeheader()
        count = 0
        for row in reader:
            if row.get(date_field) == asof:
                writer.writerow(row)
                count += 1
    return count


def write_calendar(src: Path, dst: Path, asof: str) -> int:
    dst.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with src.open("r", encoding="utf-8") as in_handle, dst.open("w", encoding="utf-8", newline="") as out_handle:
        writer = csv.DictWriter(out_handle, fieldnames=["date"])
        writer.writeheader()
        for line in in_handle:
            value = line.strip()
            if value and value <= asof:
                writer.writerow({"date": value})
                count += 1
    return count


def write_placeholder_holdings(dst: Path) -> None:
    fields = ["asof_date", "instrument", "quantity", "cost_basis", "current_holding_flag", "source_artifact", "status", "reason"]
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow(
            {
                "asof_date": ASOF,
                "instrument": "",
                "quantity": "",
                "cost_basis": "",
                "current_holding_flag": "",
                "source_artifact": "",
                "status": "SOURCE_CONTEXT_PLACEHOLDER",
                "reason": "no_current_holdings_or_order_intents_generated_in_dng10",
            }
        )


def build_dependency_readiness(price_rows: int, market_rows: int) -> dict[str, Any]:
    signal_manifest = read_json(SIGNAL_ROOT / "manifest.json")
    model_b_manifest = read_json(MODEL_B_SCORE_JOB / "manifest.json")
    return {
        "schema_version": "v1.dng10.strategy_input_bundle.dependency_readiness",
        "generated_at": utc_now(),
        "route_id": "dng10_strategy_readonly_context",
        "asof": ASOF,
        "status": "READY_FOR_SOURCE_CONTEXT_DRY_RUN",
        "can_continue_to_source_context": True,
        "can_continue_to_order_intent": False,
        "can_continue_to_replay": False,
        "can_continue_to_publish_latest": False,
        "model_a_ready": True,
        "model_b_ltr_ready": False,
        "fallback_model": "qlib_only_model_a",
        "fallback_allowed": "qlib_only_if_strategy_contract_allows",
        "blocking_reasons": [
            "model_b_ltr_blocked_by_orthogonal_feature_store",
            "no_current_holdings_or_order_intents_generated_in_dng10",
            "latest_next_day_execution_pending_blocks_replay",
        ],
        "dependencies": [
            {
                "dependency_name": "dng7_model_a_signal",
                "required_layer": "model_signal_store",
                "required_dataset_id": MODEL_A_ID,
                "required_date_max": ASOF,
                "source_artifact": rel(SIGNAL_ROOT / "manifest.json"),
                "catalog_status": signal_manifest.get("status", "READY"),
                "coverage_status": "READY",
                "schema_status": "READY",
                "pit_status": "READY",
                "latest_status": "artifact_asof_2026-06-25; not_published_latest",
                "can_continue": True,
                "blocker_reason": "",
            },
            {
                "dependency_name": "model_b_ltr_score_job",
                "required_layer": "score_job",
                "required_dataset_id": MODEL_B_ID,
                "required_date_max": ASOF,
                "source_artifact": rel(MODEL_B_SCORE_JOB / "manifest.json"),
                "catalog_status": model_b_manifest.get("status", "BLOCKED_INPUT_NOT_READY"),
                "coverage_status": "BLOCKED_INPUT_NOT_READY",
                "schema_status": "READY",
                "pit_status": "BLOCKED_INPUT_NOT_READY",
                "latest_status": "no Model B signal generated; qlib-only fallback must be shown",
                "can_continue": False,
                "blocker_reason": ";".join(model_b_manifest.get("blocker_reasons") or []),
            },
            {
                "dependency_name": "canonical_price_context",
                "required_layer": "canonical_price_store",
                "required_dataset_id": "tw_equity_daily",
                "required_date_max": ASOF,
                "source_artifact": rel(PRICE_ROOT / "prices.csv"),
                "catalog_status": read_json(PRICE_ROOT / "manifest.json").get("status", "PARTIAL_READY"),
                "coverage_status": "READY" if price_rows > 0 else "MISSING",
                "schema_status": "READY",
                "pit_status": "READY",
                "latest_status": "canonical artifact only; latest pointer not updated",
                "can_continue": price_rows > 0,
                "blocker_reason": "" if price_rows > 0 else "missing_price_context_rows",
            },
            {
                "dependency_name": "market_context",
                "required_layer": "canonical_market_feature_store",
                "required_dataset_id": "twii_daily",
                "required_date_max": ASOF,
                "source_artifact": rel(MARKET_ROOT / "twii.csv"),
                "catalog_status": read_json(MARKET_ROOT / "manifest.json").get("status", "PARTIAL_READY_WITH_DECLARED_GAP"),
                "coverage_status": "READY" if market_rows > 0 else "MISSING",
                "schema_status": "READY",
                "pit_status": "READY",
                "latest_status": "canonical artifact only; latest pointer not updated",
                "can_continue": market_rows > 0,
                "blocker_reason": "" if market_rows > 0 else "missing_market_context_rows",
            },
        ],
        "source_readiness_matrices": [rel(PRICE_READINESS), rel(ORTHOGONAL_READINESS)],
        "forbidden_action_flags": FORBIDDEN_ACTION_FLAGS,
    }


def build_strategy_input_bundle() -> Path:
    out_dir = ROOT / "data_tw/artifacts/strategy_input_bundles" / STRATEGY_BUNDLE_ID / STRATEGY_RUN_ID
    out_dir.mkdir(parents=True, exist_ok=True)

    shutil.copyfile(SIGNAL_ROOT / "signals.csv", out_dir / "signals.csv")
    write_placeholder_holdings(out_dir / "current_holdings.csv")
    price_rows = copy_csv_rows_for_date(PRICE_ROOT / "prices.csv", out_dir / "price_context.csv", "price_date", ASOF)
    market_rows = copy_csv_rows_for_date(MARKET_ROOT / "twii.csv", out_dir / "market_context.csv", "date", ASOF)
    calendar_rows = write_calendar(CALENDAR_PATH, out_dir / "calendar.csv", ASOF)

    dependency = build_dependency_readiness(price_rows, market_rows)
    write_json(out_dir / "dependency_readiness.json", dependency)

    signal_manifest = read_json(SIGNAL_ROOT / "manifest.json")
    model_b_manifest = read_json(MODEL_B_SCORE_JOB / "manifest.json")
    files = {
        "manifest": "manifest.json",
        "signals": "signals.csv",
        "current_holdings": "current_holdings.csv",
        "price_context": "price_context.csv",
        "market_context": "market_context.csv",
        "calendar": "calendar.csv",
        "dependency_readiness": "dependency_readiness.json",
        "lineage": "lineage.json",
        "validator_report": "validator_report.json",
    }
    manifest = {
        "artifact_type": "strategy_input_bundle",
        "schema_version": "v1.dng10.strategy_input_bundle.manifest",
        "bundle_id": STRATEGY_BUNDLE_ID,
        "run_id": STRATEGY_RUN_ID,
        "strategy_id": STRATEGY_ID,
        "asof": ASOF,
        "signal_asof": signal_manifest.get("signal_asof"),
        "target_trade_date": "",
        "status": "READY_FOR_SOURCE_CONTEXT_DRY_RUN",
        "status_reason": "DNG10 source context only; Model A signal/price/market context ready, Model B LTR remains blocked and no order/replay/publish is generated.",
        "partial_reason": "not_order_intent_or_replay_artifact",
        "readonly_only": True,
        "not_order": True,
        "no_order": True,
        "not_replay_result": True,
        "no_broker": True,
        "no_quick_trade": True,
        "no_target_position": True,
        "no_target_weight": True,
        "not_investment_advice": True,
        "model_a_ready": True,
        "model_b_ltr_ready": False,
        "model_b_blocker_status": model_b_manifest.get("status"),
        "model_b_blocker_reasons": model_b_manifest.get("blocker_reasons") or [],
        "fallback_model": "qlib_only_model_a",
        "fallback_allowed": "qlib_only_if_strategy_contract_allows",
        "model_signal_artifact": rel(SIGNAL_ROOT / "manifest.json"),
        "model_signal_asof": signal_manifest.get("signal_asof"),
        "price_store_artifact": rel(PRICE_ROOT / "manifest.json"),
        "market_feature_artifact": rel(MARKET_ROOT / "manifest.json"),
        "model_b_score_job_artifact": rel(MODEL_B_SCORE_JOB / "manifest.json"),
        "portfolio_state_artifact": "",
        "dependency_readiness_matrix": rel(out_dir / "dependency_readiness.json"),
        "source_readiness_matrices": [rel(PRICE_READINESS), rel(ORTHOGONAL_READINESS)],
        "row_counts": {
            "signals": csv_header_and_count(out_dir / "signals.csv")[1],
            "current_holdings": csv_header_and_count(out_dir / "current_holdings.csv")[1],
            "price_context": price_rows,
            "market_context": market_rows,
            "calendar": calendar_rows,
        },
        "files": files,
        "latest_pointer_updated": False,
        "readonly_latest_updated": False,
        "agent_prompt_latest_updated": False,
        "input_hashes": {
            rel(SIGNAL_ROOT / "signals.csv"): sha256_file(SIGNAL_ROOT / "signals.csv"),
            rel(PRICE_ROOT / "prices.csv"): sha256_file(PRICE_ROOT / "prices.csv"),
            rel(MARKET_ROOT / "twii.csv"): sha256_file(MARKET_ROOT / "twii.csv"),
            rel(MODEL_B_SCORE_JOB / "manifest.json"): sha256_file(MODEL_B_SCORE_JOB / "manifest.json"),
        },
        "forbidden_action_flags": FORBIDDEN_ACTION_FLAGS,
        "created_at": utc_now(),
        "created_by": rel(Path(__file__)),
    }
    write_json(out_dir / "manifest.json", manifest)

    lineage = {
        "artifact_type": "strategy_input_bundle_lineage",
        "schema_version": "v1.dng10.strategy_input_bundle.lineage",
        "bundle_id": STRATEGY_BUNDLE_ID,
        "run_id": STRATEGY_RUN_ID,
        "lineage_type": "local_source_context_bundle_no_fetch_no_score_no_order",
        "source_artifacts": {
            "signals": rel(SIGNAL_ROOT / "signals.csv"),
            "signal_manifest": rel(SIGNAL_ROOT / "manifest.json"),
            "signal_validator": rel(SIGNAL_ROOT / "validator_report.json"),
            "price_context": rel(PRICE_ROOT / "prices.csv"),
            "market_context": rel(MARKET_ROOT / "twii.csv"),
            "calendar": rel(CALENDAR_PATH),
            "price_readiness": rel(PRICE_READINESS),
            "orthogonal_readiness": rel(ORTHOGONAL_READINESS),
            "model_b_score_job": rel(MODEL_B_SCORE_JOB / "manifest.json"),
        },
        "transformations": [
            "copy_existing_dng7_modela_signal_artifact",
            "filter_price_context_to_signal_asof",
            "filter_market_context_to_signal_asof",
            "materialize_calendar_to_signal_asof",
            "write_placeholder_holdings_for_source_context_only",
            "carry_forward_model_b_blocker_without_generating_ltr_signal",
        ],
        "latest_pointer_updated": False,
        "readonly_publish": False,
        "agent_prompt_publish": False,
        "model_training": False,
        "model_inference": False,
        "model_score_generation": False,
        "strategy_replay": False,
        "order_intent_generation": False,
        "target_position_or_weight_generation": False,
        "forbidden_action_flags": FORBIDDEN_ACTION_FLAGS,
        "created_at": utc_now(),
    }
    write_json(out_dir / "lineage.json", lineage)
    write_json(
        out_dir / "validator_report.json",
        {
            "schema_version": "v1.dng10.strategy_input_bundle.validation",
            "generated_at": utc_now(),
            "ok": False,
            "status": "NOT_VALIDATED",
            "status_reason": "Run scripts/validate_tw_strategy_input_bundle.py and scripts/validate_tw_readonly_source_context.py.",
            "bundle_root": rel(out_dir),
        },
    )
    return out_dir


def build_source_context_payload(strategy_bundle_root: Path) -> dict[str, Any]:
    signal_manifest = read_json(SIGNAL_ROOT / "manifest.json")
    signal_validation = read_json(SIGNAL_ROOT / "validator_report.json")
    price_manifest = read_json(PRICE_ROOT / "manifest.json")
    market_manifest = read_json(MARKET_ROOT / "manifest.json")
    model_b_manifest = read_json(MODEL_B_SCORE_JOB / "manifest.json")
    model_b_input_readiness = read_json(MODEL_B_SCORE_JOB / "input_readiness.json")
    strategy_manifest = read_json(strategy_bundle_root / "manifest.json")
    signals = read_signal_rows(SIGNAL_ROOT / "signals.csv")
    top10 = [compact_signal(row) for row in signals[:10]]
    top50 = [compact_signal(row) for row in signals[:50]]

    return {
        "schema_version": "v1.dng10.readonly_source_context",
        "generated_at": utc_now(),
        "run_id": SOURCE_CONTEXT_RUN_ID,
        "signal_asof": ASOF,
        "target_date": ASOF,
        "strategy_id": STRATEGY_ID,
        "readonly_only": True,
        "not_order": True,
        "not_target_position": True,
        "not_target_weight": True,
        "not_replay_result": True,
        "latest_pointer_updated": False,
        "agent_prompt_latest_updated": False,
        "model_context": {
            "model_a_id": MODEL_A_ID,
            "model_a_ready": True,
            "model_a_signal_artifact": rel(SIGNAL_ROOT / "manifest.json"),
            "model_a_signal_rows": signal_manifest.get("row_count"),
            "model_a_validation_ok": signal_validation.get("ok"),
            "model_b_id": MODEL_B_ID,
            "model_b_ltr_ready": False,
            "model_b_status": model_b_manifest.get("status"),
            "model_b_blocker_reasons": model_b_manifest.get("blocker_reasons") or [],
            "model_b_blocking_datasets": model_b_manifest.get("blocking_datasets") or [],
            "fallback_model": "qlib_only_model_a",
            "fallback_signal_artifact": model_b_manifest.get("fallback_signal_artifact") or rel(SIGNAL_ROOT),
            "do_not_substitute_qlib_score_as_ltr_score": True,
        },
        "ranking_context": {
            "ranking_source": "qlib_only_model_a",
            "candidate_boundary": "qlib_top50",
            "qlib_top10": top10,
            "qlib_top50_compact": top50,
            "top_candidates": top10,
            "exit_candidates": [],
            "blocked_or_skipped": [
                {
                    "name": "model_b_ltr",
                    "status": model_b_manifest.get("status"),
                    "reason": "orthogonal_feature_store_not_ready; qlib-only fallback is shown explicitly",
                },
                {
                    "name": "order_intent",
                    "status": "NOT_GENERATED",
                    "reason": "DNG10 source context dry-run does not generate OrderIntentArtifact",
                },
                {
                    "name": "replay_result",
                    "status": "NOT_GENERATED",
                    "reason": "DNG10 source context dry-run does not generate ReplayResult/NAV",
                },
            ],
        },
        "data_context": {
            "price_store": {
                "path": rel(PRICE_ROOT / "manifest.json"),
                "asof": price_manifest.get("asof"),
                "status": price_manifest.get("status"),
                "row_count": price_manifest.get("row_count"),
                "symbol_count": price_manifest.get("symbol_count"),
            },
            "market_feature_store": {
                "path": rel(MARKET_ROOT / "manifest.json"),
                "asof": market_manifest.get("asof"),
                "status": market_manifest.get("status"),
                "row_count": market_manifest.get("row_count"),
            },
            "price_readiness": rel(PRICE_READINESS),
            "orthogonal_readiness": rel(ORTHOGONAL_READINESS),
            "model_b_input_readiness_status": model_b_input_readiness.get("status"),
        },
        "strategy_input_bundle": {
            "path": rel(strategy_bundle_root / "manifest.json"),
            "status": strategy_manifest.get("status"),
            "row_counts": strategy_manifest.get("row_counts"),
        },
        "source_artifacts": {
            "strategy_input_bundle": rel(strategy_bundle_root / "manifest.json"),
            "model_a_signal": rel(SIGNAL_ROOT / "manifest.json"),
            "price_store": rel(PRICE_ROOT / "manifest.json"),
            "market_feature_store": rel(MARKET_ROOT / "manifest.json"),
            "price_readiness": rel(PRICE_READINESS),
            "orthogonal_readiness": rel(ORTHOGONAL_READINESS),
            "model_b_score_job": rel(MODEL_B_SCORE_JOB / "manifest.json"),
        },
        "forbidden_action_flags": FORBIDDEN_ACTION_FLAGS,
    }


def build_readonly_context(strategy_bundle_root: Path) -> Path:
    out_dir = ROOT / "data_tw/artifacts/readonly_source_context" / SOURCE_CONTEXT_RUN_ID
    context = build_source_context_payload(strategy_bundle_root)
    write_json(out_dir / "context.json", context)
    manifest = {
        "artifact_type": "readonly_strategy_snapshot_source_context_dry_run",
        "schema_version": "v1.dng10.readonly_source_context.manifest",
        "run_id": SOURCE_CONTEXT_RUN_ID,
        "created_at": utc_now(),
        "created_by": rel(Path(__file__)),
        "signal_asof": ASOF,
        "model_a_ready": True,
        "model_b_ltr_ready": False,
        "fallback_model": "qlib_only_model_a",
        "readonly_only": True,
        "not_order": True,
        "not_target_position": True,
        "not_target_weight": True,
        "not_replay_result": True,
        "latest_pointer_updated": False,
        "readonly_latest_updated": False,
        "agent_prompt_latest_updated": False,
        "production_allowed": False,
        "context_path": "context.json",
        "context_sha256": sha256_file(out_dir / "context.json"),
        "source_artifacts": context["source_artifacts"],
        "forbidden_action_flags": FORBIDDEN_ACTION_FLAGS,
    }
    write_json(out_dir / "manifest.json", manifest)
    return out_dir


def build_agent_context(strategy_bundle_root: Path) -> Path:
    out_dir = ROOT / "data_tw/artifacts/agent_daily_prompt_source_context" / SOURCE_CONTEXT_RUN_ID
    base_context = build_source_context_payload(strategy_bundle_root)
    prompt_context = {
        "schema_version": "v1.dng10.agent_daily_prompt_source_context",
        "generated_at": utc_now(),
        "run_id": SOURCE_CONTEXT_RUN_ID,
        "safety": {
            "readonly_only": True,
            "not_order": True,
            "not_target_position": True,
            "not_target_weight": True,
            "not_investment_advice": True,
            "production_trade_enabled": False,
        },
        "date_context": {
            "signal_asof": ASOF,
            "target_date": ASOF,
            "display_asof": ASOF,
            "execution_price_mode": "not_executed_in_dng10",
            "execution_price_status": "pending_next_trade_date_for_replay_only",
        },
        "model_context": base_context["model_context"],
        "rankings": {
            "qlib_top10": base_context["ranking_context"]["qlib_top10"],
            "qlib_top50_compact": base_context["ranking_context"]["qlib_top50_compact"],
            "ltr_top10": [],
            "ltr_status": "BLOCKED_INPUT_NOT_READY",
            "fallback_model": "qlib_only_model_a",
        },
        "strategy": {
            "strategy_rule": STRATEGY_ID,
            "top_candidates": base_context["ranking_context"]["top_candidates"],
            "exit_candidates": [],
            "skipped_or_blocked": base_context["ranking_context"]["blocked_or_skipped"],
        },
        "freshness": {
            "status": "source_context_ready_modela_fallback_modelb_blocked",
            "warnings": [
                "Model B LTR blocked by DNG3 orthogonal feature store readiness.",
                "No readonly latest pointer or Agent prompt latest pointer was updated.",
                "No OrderIntentArtifact, ReplayResult, NAV, target position, or target weight was generated.",
            ],
        },
        "answer_policy": {
            "allowed_question_types": [
                "today_strategy",
                "top_ranked_stock",
                "top_n_rankings",
                "single_symbol_status",
                "data_freshness",
                "model_b_blocker_status",
            ],
            "blocked_question_types": [
                "place_order",
                "auto_trade",
                "target_position_request",
                "portfolio_weight",
                "guaranteed_profit",
                "qlib_ops_refresh_publish",
                "qlib_retrain_or_tune",
                "broker_operation",
                "monitor_write",
            ],
            "required_disclaimer": "仅供研究观察，不构成交易建议；qlib score 是横截面排序分数，不是收益率、胜率、涨幅或买入概率。",
        },
        "source_artifacts": base_context["source_artifacts"],
        "forbidden_action_flags": FORBIDDEN_ACTION_FLAGS,
    }
    write_json(out_dir / "prompt_source_context.json", prompt_context)
    manifest = {
        "artifact_type": "agent_daily_prompt_source_context_dry_run",
        "schema_version": "v1.dng10.agent_daily_prompt_source_context.manifest",
        "run_id": SOURCE_CONTEXT_RUN_ID,
        "created_at": utc_now(),
        "created_by": rel(Path(__file__)),
        "signal_asof": ASOF,
        "model_a_ready": True,
        "model_b_ltr_ready": False,
        "fallback_model": "qlib_only_model_a",
        "readonly_only": True,
        "not_order": True,
        "not_target_position": True,
        "not_target_weight": True,
        "not_replay_result": True,
        "latest_pointer_updated": False,
        "readonly_latest_updated": False,
        "agent_prompt_latest_updated": False,
        "production_allowed": False,
        "prompt_source_context_path": "prompt_source_context.json",
        "prompt_source_context_sha256": sha256_file(out_dir / "prompt_source_context.json"),
        "source_artifacts": prompt_context["source_artifacts"],
        "forbidden_action_flags": FORBIDDEN_ACTION_FLAGS,
    }
    write_json(out_dir / "manifest.json", manifest)
    return out_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Build DNG10 readonly source context artifacts from local DNG7/DNG8/DNG2 artifacts.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    strategy_bundle_root = build_strategy_input_bundle()
    readonly_root = build_readonly_context(strategy_bundle_root)
    agent_root = build_agent_context(strategy_bundle_root)
    payload = {
        "strategy_input_bundle": rel(strategy_bundle_root),
        "readonly_source_context": rel(readonly_root),
        "agent_daily_prompt_source_context": rel(agent_root),
        "signal_asof": ASOF,
        "model_a_ready": True,
        "model_b_ltr_ready": False,
        "fallback_model": "qlib_only_model_a",
        "latest_pointer_updated": False,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if args.json else payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
