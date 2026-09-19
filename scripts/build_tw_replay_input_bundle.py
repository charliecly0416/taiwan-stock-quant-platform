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

DEFAULT_ASOF = "2026-06-25"
DEFAULT_BUNDLE_ID = "top50_exit_one_worst_sell_dng4_replay_contract"
DEFAULT_RUN_ID = "dng4_replay_input_bundle_20260625"
DEFAULT_STRATEGY_ID = "top50_exit_one_worst_sell"

PRICE_ROOT = ROOT / "data_tw/canonical/price_store/tw_equity_daily/dng2_r_price_market_calendar_20260625"
MARKET_CALENDAR = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt"
PRICE_READINESS = ROOT / "data_tw/catalog/readiness_matrix/2026-06-25/price_market_calendar.json"
ORTHOGONAL_READINESS = ROOT / "data_tw/catalog/readiness_matrix/2026-06-25/orthogonal_feature_store.json"

FORBIDDEN_ACTION_FLAGS = {
    "real_data_fetch_triggered": False,
    "provider_refresh_triggered": False,
    "provider_publish_triggered": False,
    "qlib_accepted_latest_switched": False,
    "readonly_latest_published": False,
    "agent_prompt_published": False,
    "model_training_triggered": False,
    "model_inference_triggered": False,
    "strategy_replay_triggered": False,
    "broker_order_quick_trade_triggered": False,
    "target_position_or_weight_generated": False,
}

ORDER_INTENT_FIELDS = [
    "signal_date",
    "instrument",
    "intent_action",
    "intent_reason",
    "strategy_rule",
    "candidate_rank",
    "buy_rank",
    "full_qlib_rank",
    "max_buy_count",
    "max_sell_count",
    "model_name",
    "signal_artifact",
    "readonly_only",
    "not_order",
    "not_target_position",
    "not_investment_advice",
    "placeholder_status",
    "placeholder_reason",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path | str) -> str:
    path_obj = Path(path)
    try:
        return str(path_obj.resolve().relative_to(ROOT.resolve()))
    except (ValueError, FileNotFoundError):
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
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def csv_header_and_count(path: Path) -> tuple[list[str], int]:
    if not path.exists():
        return [], 0
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return [], 0
        return header, sum(1 for _ in reader)


def write_empty_order_intents(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ORDER_INTENT_FIELDS)
        writer.writeheader()


def write_calendar(src: Path, dst: Path, asof: str) -> int:
    dst.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with src.open("r", encoding="utf-8") as in_f, dst.open("w", encoding="utf-8", newline="") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=["date"])
        writer.writeheader()
        for line in in_f:
            value = line.strip()
            if value and value <= asof:
                writer.writerow({"date": value})
                count += 1
    return count


def build_dependency_readiness(asof: str) -> dict[str, Any]:
    price_readiness = read_json(PRICE_READINESS)
    orthogonal_readiness = read_json(ORTHOGONAL_READINESS)
    dependencies = [
        {
            "dependency_name": "order_intents",
            "required_layer": "order_intent_artifact",
            "required_dataset_id": "order_intents",
            "required_date_max": asof,
            "source_artifact": "",
            "catalog_status": "MISSING",
            "coverage_status": "MISSING",
            "schema_status": "PLACEHOLDER_SCHEMA_ONLY",
            "pit_status": "NOT_APPLICABLE",
            "latest_status": "empty_order_intents.csv generated as DNG4 placeholder",
            "can_continue": False,
            "blocker_reason": "missing_current_holdings_or_order_intents",
            "repair_recommendation": "Generate a standard OrderIntentArtifact in a later authorized gate; DNG4 must not generate one.",
        },
        {
            "dependency_name": "next_day_execution_availability",
            "required_layer": "canonical_price_store",
            "required_dataset_id": "tw_equity_daily",
            "required_date_max": asof,
            "source_artifact": rel(PRICE_ROOT / "execution_availability_audit.csv"),
            "catalog_status": "PARTIAL_READY",
            "coverage_status": "PARTIAL_READY",
            "schema_status": "READY",
            "pit_status": "READY",
            "latest_status": "latest asof pending_next_trade_date; no next local trading row",
            "can_continue": False,
            "blocker_reason": "latest_next_day_execution_pending",
            "repair_recommendation": "Rebuild after next local trading row is available before replay execution.",
        },
    ]
    return {
        "schema_version": "v1.dng4.replay_input_bundle.dependency_readiness",
        "generated_at": utc_now(),
        "route_id": "dng4_replay_input_bundle",
        "asof": asof,
        "status": "PARTIAL_READY",
        "status_reason": "Replay input contract materialized with empty order intents and no ReplayResult/NAV.",
        "can_continue": False,
        "can_continue_to_replay_execution": False,
        "can_continue_to_shadow_execution": False,
        "not_replay_result": True,
        "blocking_reasons": [
            "missing_current_holdings_or_order_intents",
            "latest_next_day_execution_pending",
            "orthogonal_feature_store_partial_ready",
        ],
        "dependencies": dependencies + price_readiness.get("dependencies", []) + orthogonal_readiness.get("dependencies", []),
        "forbidden_action_flags": FORBIDDEN_ACTION_FLAGS,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build DNG4 ReplayInputBundle from local audited artifacts.")
    parser.add_argument("--asof", default=DEFAULT_ASOF)
    parser.add_argument("--bundle-id", default=DEFAULT_BUNDLE_ID)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--strategy-id", default=DEFAULT_STRATEGY_ID)
    args = parser.parse_args()

    out_dir = ROOT / "data_tw/artifacts/replay_input_bundles" / args.bundle_id / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    write_empty_order_intents(out_dir / "empty_order_intents.csv")
    calendar_rows = write_calendar(MARKET_CALENDAR, out_dir / "market_calendar.csv", args.asof)
    shutil.copyfile(PRICE_ROOT / "execution_availability_audit.csv", out_dir / "execution_availability_audit.csv")

    price_ref = {
        "artifact_type": "price_store_ref",
        "price_store_manifest": rel(PRICE_ROOT / "manifest.json"),
        "prices_path": rel(PRICE_ROOT / "prices.csv"),
        "execution_availability_audit": rel(PRICE_ROOT / "execution_availability_audit.csv"),
        "asof": args.asof,
        "readonly_only": True,
        "not_published_latest": True,
    }
    write_json(out_dir / "price_store_ref.json", price_ref)

    cost_config = {
        "artifact_type": "replay_cost_config",
        "schema_version": "v1.dng4.replay_cost_config",
        "readonly_only": True,
        "not_replay_result": True,
        "execution_price_policy": "not_executed_in_dng4; future replay gate must define next-day execution price",
        "fee_tax_policy": "placeholder_contract_only_no_fee_tax_calculation",
        "mark_to_market_policy": "placeholder_contract_only_no_mark_to_market",
        "corporate_action_policy": "blocked_by_dng3_corporate_actions_partial_ready",
        "halt_suspension_policy": "use price_store halt/tradable flags in later replay gate",
        "missing_price_policy": "block_or_skip_in_later_replay_gate; no fills generated here",
        "forbidden_action_flags": FORBIDDEN_ACTION_FLAGS,
    }
    write_json(out_dir / "cost_config.json", cost_config)

    initial_state = {
        "artifact_type": "initial_portfolio_state",
        "schema_version": "v1.dng4.initial_portfolio_state.placeholder",
        "asof": args.asof,
        "status": "PARTIAL_READY",
        "reason": "missing_current_holdings_or_order_intents",
        "positions": [],
        "cash": None,
        "readonly_only": True,
        "not_replay_result": True,
        "not_order": True,
        "not_target_position": True,
        "not_target_weight": True,
    }
    write_json(out_dir / "initial_portfolio_state.json", initial_state)

    dependency_readiness = build_dependency_readiness(args.asof)
    write_json(out_dir / "dependency_readiness.json", dependency_readiness)

    files = {
        "manifest": "manifest.json",
        "empty_order_intents": "empty_order_intents.csv",
        "price_store_ref": "price_store_ref.json",
        "cost_config": "cost_config.json",
        "initial_portfolio_state": "initial_portfolio_state.json",
        "market_calendar": "market_calendar.csv",
        "execution_availability_audit": "execution_availability_audit.csv",
        "dependency_readiness": "dependency_readiness.json",
        "lineage": "lineage.json",
        "validator_report": "validator_report.json",
    }
    manifest = {
        "artifact_type": "replay_input_bundle",
        "schema_version": "v1.dng4.replay_input_bundle.manifest",
        "bundle_id": args.bundle_id,
        "run_id": args.run_id,
        "strategy_id": args.strategy_id,
        "asof": args.asof,
        "status": "PARTIAL_READY",
        "status_reason": "PARTIAL_READY placeholder: order intents/current holdings are missing and latest next-day execution is pending.",
        "partial_reason": "missing_current_holdings_or_order_intents",
        "readonly_only": True,
        "not_replay_result": True,
        "no_nav": True,
        "no_performance_metrics": True,
        "not_order": True,
        "no_order": True,
        "no_broker": True,
        "no_quick_trade": True,
        "no_target_position": True,
        "no_target_weight": True,
        "execution_price_policy": cost_config["execution_price_policy"],
        "fee_tax_policy": cost_config["fee_tax_policy"],
        "mark_to_market_policy": cost_config["mark_to_market_policy"],
        "corporate_action_policy": cost_config["corporate_action_policy"],
        "halt_suspension_policy": cost_config["halt_suspension_policy"],
        "missing_price_policy": cost_config["missing_price_policy"],
        "order_intents_artifact": "",
        "empty_order_intents_path": rel(out_dir / "empty_order_intents.csv"),
        "price_store_ref": rel(out_dir / "price_store_ref.json"),
        "dependency_readiness_matrix": rel(out_dir / "dependency_readiness.json"),
        "row_counts": {
            "empty_order_intents": csv_header_and_count(out_dir / "empty_order_intents.csv")[1],
            "market_calendar": calendar_rows,
            "execution_availability_audit": csv_header_and_count(out_dir / "execution_availability_audit.csv")[1],
        },
        "files": files,
        "input_hashes": {
            rel(PRICE_ROOT / "prices.csv"): sha256_file(PRICE_ROOT / "prices.csv"),
            rel(PRICE_ROOT / "execution_availability_audit.csv"): sha256_file(PRICE_ROOT / "execution_availability_audit.csv"),
            rel(MARKET_CALENDAR): sha256_file(MARKET_CALENDAR),
        },
        "forbidden_action_flags": FORBIDDEN_ACTION_FLAGS,
        "created_at": utc_now(),
        "created_by": rel(Path(__file__)),
    }
    write_json(out_dir / "manifest.json", manifest)

    lineage = {
        "artifact_type": "replay_input_bundle_lineage",
        "schema_version": "v1.dng4.replay_input_bundle.lineage",
        "bundle_id": args.bundle_id,
        "run_id": args.run_id,
        "lineage_type": "local_artifact_bundle_no_fetch_no_order_no_replay",
        "source_artifacts": {
            "price_store_manifest": rel(PRICE_ROOT / "manifest.json"),
            "execution_availability_audit": rel(PRICE_ROOT / "execution_availability_audit.csv"),
            "market_calendar": rel(MARKET_CALENDAR),
            "price_readiness": rel(PRICE_READINESS),
            "orthogonal_readiness": rel(ORTHOGONAL_READINESS),
        },
        "transformations": [
            "write_empty_order_intents_placeholder",
            "write_price_store_ref",
            "copy_execution_availability_audit",
            "materialize_calendar_to_asof",
            "write_placeholder_initial_portfolio_state",
        ],
        "no_provider_publish": True,
        "no_accepted_latest_switch": True,
        "readonly_publish": False,
        "agent_prompt_publish": False,
        "model_training": False,
        "model_inference": False,
        "model_score_generation": False,
        "strategy_replay": False,
        "replay_result_generation": False,
        "order_intent_generation": False,
        "target_position_or_weight_generation": False,
        "forbidden_action_flags": FORBIDDEN_ACTION_FLAGS,
        "created_at": utc_now(),
    }
    write_json(out_dir / "lineage.json", lineage)

    preliminary = {
        "schema_version": "v1.dng4.replay_input_bundle.validation",
        "generated_at": utc_now(),
        "ok": False,
        "status": "NOT_VALIDATED",
        "status_reason": "Run scripts/validate_tw_replay_input_bundle.py for final validation.",
        "bundle_root": rel(out_dir),
    }
    write_json(out_dir / "validator_report.json", preliminary)

    print(json.dumps({"bundle_root": rel(out_dir), "status": "PARTIAL_READY"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
