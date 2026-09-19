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
DEFAULT_BUNDLE_ID = "top50_exit_one_worst_sell_dng4_contract"
DEFAULT_RUN_ID = "dng4_strategy_input_bundle_20260625"
DEFAULT_STRATEGY_ID = "top50_exit_one_worst_sell"

PRICE_ROOT = ROOT / "data_tw/canonical/price_store/tw_equity_daily/dng2_r_price_market_calendar_20260625"
MARKET_ROOT = ROOT / "data_tw/canonical/market_feature_store/twii_daily/dng2_r_price_market_calendar_20260625"
ORTHOGONAL_ROOT = ROOT / "data_tw/canonical/orthogonal_feature_store/daily_orthogonal/dng3_orthogonal_feature_store_20260625"
SIGNAL_ROOT = ROOT / "data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_a"
CALENDAR_PATH = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt"
PRICE_READINESS = ROOT / "data_tw/catalog/readiness_matrix/2026-06-25/price_market_calendar.json"
ORTHOGONAL_READINESS = ROOT / "data_tw/catalog/readiness_matrix/2026-06-25/orthogonal_feature_store.json"
LATEST_STATUS = ROOT / "data_tw/catalog/latest_status.json"

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

SIGNAL_FIELDS = [
    "date",
    "instrument",
    "model_id",
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
    "source_model_artifact",
    "source_feature_artifact",
]

HOLDING_FIELDS = [
    "asof_date",
    "instrument",
    "quantity",
    "cost_basis",
    "current_holding_flag",
    "source_artifact",
    "status",
    "reason",
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


def copy_csv_rows_for_date(src: Path, dst: Path, date_field: str, asof: str) -> int:
    dst.parent.mkdir(parents=True, exist_ok=True)
    with src.open("r", encoding="utf-8", newline="") as in_f, dst.open("w", encoding="utf-8", newline="") as out_f:
        reader = csv.DictReader(in_f)
        writer = csv.DictWriter(out_f, fieldnames=reader.fieldnames or [])
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
    with src.open("r", encoding="utf-8") as in_f, dst.open("w", encoding="utf-8", newline="") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=["date"])
        writer.writeheader()
        for line in in_f:
            value = line.strip()
            if value and value <= asof:
                writer.writerow({"date": value})
                count += 1
    return count


def write_empty_holdings(dst: Path, asof: str) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HOLDING_FIELDS)
        writer.writeheader()
        writer.writerow(
            {
                "asof_date": asof,
                "instrument": "",
                "quantity": "",
                "cost_basis": "",
                "current_holding_flag": "",
                "source_artifact": "",
                "status": "PARTIAL_READY",
                "reason": "missing_current_holdings_or_order_intents",
            }
        )


def build_dependency_readiness(asof: str, signal_manifest: dict[str, Any], price_rows: int, market_rows: int) -> dict[str, Any]:
    price_readiness = read_json(PRICE_READINESS)
    orthogonal_readiness = read_json(ORTHOGONAL_READINESS)
    latest_status = read_json(LATEST_STATUS)
    signal_asof = signal_manifest.get("signal_asof") or signal_manifest.get("asof_date", "")
    dependencies = [
        {
            "dependency_name": "model_signal_artifact",
            "required_layer": "model_signal_store",
            "required_dataset_id": signal_manifest.get("model_id", ""),
            "required_date_max": asof,
            "source_artifact": rel(SIGNAL_ROOT / "manifest.json"),
            "catalog_status": "PARTIAL_READY",
            "coverage_status": "PARTIAL_READY",
            "schema_status": "READY",
            "pit_status": "READY",
            "latest_status": "model_signal_latest is 2026-06-17; does not match 2026-06-25 price/market asof",
            "can_continue": False,
            "blocker_reason": "model_signal_asof_lags_price_market_asof",
            "repair_recommendation": "Generate a standard ModelSignalArtifact for target asof after upstream score gate; DNG4 must not run model inference.",
        },
        {
            "dependency_name": "current_holdings",
            "required_layer": "portfolio_state_artifact",
            "required_dataset_id": "portfolio_state",
            "required_date_max": asof,
            "source_artifact": "",
            "catalog_status": "MISSING",
            "coverage_status": "MISSING",
            "schema_status": "PLACEHOLDER_SCHEMA_ONLY",
            "pit_status": "NOT_APPLICABLE",
            "latest_status": "no standard current holdings artifact for DNG4 target asof",
            "can_continue": False,
            "blocker_reason": "missing_current_holdings_or_order_intents",
            "repair_recommendation": "Provide a standard readonly PortfolioState artifact before strategy execution.",
        },
        {
            "dependency_name": "canonical_price_context",
            "required_layer": "canonical_price_store",
            "required_dataset_id": "tw_equity_daily",
            "required_date_max": asof,
            "source_artifact": rel(PRICE_ROOT / "prices.csv"),
            "catalog_status": read_json(PRICE_ROOT / "manifest.json").get("status", "PARTIAL_READY"),
            "coverage_status": "READY" if price_rows > 0 else "MISSING",
            "schema_status": "READY",
            "pit_status": "READY",
            "latest_status": "canonical artifact only; not published latest",
            "can_continue": price_rows > 0,
            "blocker_reason": "" if price_rows > 0 else "missing_price_context_rows",
            "repair_recommendation": "",
        },
        {
            "dependency_name": "market_context",
            "required_layer": "canonical_market_feature_store",
            "required_dataset_id": "twii_daily",
            "required_date_max": asof,
            "source_artifact": rel(MARKET_ROOT / "twii.csv"),
            "catalog_status": read_json(MARKET_ROOT / "manifest.json").get("status", "PARTIAL_READY_WITH_DECLARED_GAP"),
            "coverage_status": "READY" if market_rows > 0 else "MISSING",
            "schema_status": "READY",
            "pit_status": "READY",
            "latest_status": "canonical artifact only; not published latest",
            "can_continue": market_rows > 0,
            "blocker_reason": "" if market_rows > 0 else "missing_market_context_rows",
            "repair_recommendation": "",
        },
        {
            "dependency_name": "orthogonal_feature_store",
            "required_layer": "canonical_orthogonal_feature_store",
            "required_dataset_id": "daily_orthogonal",
            "required_date_max": asof,
            "source_artifact": rel(ORTHOGONAL_ROOT / "manifest.json"),
            "catalog_status": orthogonal_readiness.get("status", "PARTIAL_READY"),
            "coverage_status": "PARTIAL_READY",
            "schema_status": "READY_WITH_BLOCKERS",
            "pit_status": "READY_WITH_BLOCKERS",
            "latest_status": "canonical artifact only; not published latest",
            "can_continue": False,
            "blocker_reason": "corporate_actions/monthly_revenue/valuation blocked; can_continue_to_model_b_ltr=false",
            "repair_recommendation": "Repair DNG3 blockers before any Model B LTR route.",
        },
    ]
    return {
        "schema_version": "v1.dng4.strategy_input_bundle.dependency_readiness",
        "generated_at": utc_now(),
        "route_id": "dng4_strategy_input_bundle",
        "asof": asof,
        "status": "PARTIAL_READY",
        "status_reason": "model signal and current holdings are not ready for target asof; DNG3 orthogonal blockers are carried forward",
        "can_continue": False,
        "can_continue_to_strategy_contract": True,
        "can_continue_to_order_intent": False,
        "can_continue_to_replay": False,
        "model_b_ltr_ready": False,
        "fallback_allowed": "qlib_only_if_strategy_contract_allows",
        "latest_status_summary": {
            "model_signal_latest": latest_status.get("latest_by_concept", {}).get("model_signal_latest", {}),
            "price_store_source": rel(PRICE_ROOT / "manifest.json"),
            "orthogonal_feature_store_source": rel(ORTHOGONAL_ROOT / "manifest.json"),
        },
        "dependencies": dependencies + price_readiness.get("dependencies", []) + orthogonal_readiness.get("dependencies", []),
        "blocking_reasons": [
            "model_signal_asof_lags_price_market_asof",
            "missing_current_holdings_or_order_intents",
            "orthogonal_feature_store_partial_ready",
            "can_continue_to_model_b_ltr_false",
        ],
        "forbidden_action_flags": FORBIDDEN_ACTION_FLAGS,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build DNG4 StrategyInputBundle from local audited artifacts.")
    parser.add_argument("--asof", default=DEFAULT_ASOF)
    parser.add_argument("--bundle-id", default=DEFAULT_BUNDLE_ID)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--strategy-id", default=DEFAULT_STRATEGY_ID)
    args = parser.parse_args()

    out_dir = ROOT / "data_tw/artifacts/strategy_input_bundles" / args.bundle_id / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    signal_manifest = read_json(SIGNAL_ROOT / "manifest.json")
    shutil.copyfile(SIGNAL_ROOT / "signals.csv", out_dir / "signals.csv")
    write_empty_holdings(out_dir / "current_holdings.csv", args.asof)
    price_rows = copy_csv_rows_for_date(PRICE_ROOT / "prices.csv", out_dir / "price_context.csv", "price_date", args.asof)
    market_rows = copy_csv_rows_for_date(MARKET_ROOT / "twii.csv", out_dir / "market_context.csv", "date", args.asof)
    calendar_rows = write_calendar(CALENDAR_PATH, out_dir / "calendar.csv", args.asof)

    dependency_readiness = build_dependency_readiness(args.asof, signal_manifest, price_rows, market_rows)
    write_json(out_dir / "dependency_readiness.json", dependency_readiness)

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
    status_reason = (
        "PARTIAL_READY placeholder: target asof has canonical price/market context, but standard current holdings are missing, "
        "model_signal_latest remains 2026-06-17, and DNG3 blocks Model B LTR."
    )
    manifest = {
        "artifact_type": "strategy_input_bundle",
        "schema_version": "v1.dng4.strategy_input_bundle.manifest",
        "bundle_id": args.bundle_id,
        "run_id": args.run_id,
        "strategy_id": args.strategy_id,
        "asof": args.asof,
        "target_trade_date": "",
        "status": "PARTIAL_READY",
        "status_reason": status_reason,
        "partial_reason": "missing_current_holdings_or_order_intents",
        "readonly_only": True,
        "not_order": True,
        "no_order": True,
        "no_broker": True,
        "no_quick_trade": True,
        "no_target_position": True,
        "no_target_weight": True,
        "not_investment_advice": True,
        "model_b_ltr_ready": False,
        "fallback_allowed": "qlib_only_if_strategy_contract_allows",
        "model_signal_artifact": rel(SIGNAL_ROOT / "manifest.json"),
        "model_signal_asof": signal_manifest.get("signal_asof"),
        "price_store_artifact": rel(PRICE_ROOT / "manifest.json"),
        "market_feature_artifact": rel(MARKET_ROOT / "manifest.json"),
        "orthogonal_feature_store_artifact": rel(ORTHOGONAL_ROOT / "manifest.json"),
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
        "input_hashes": {
            rel(SIGNAL_ROOT / "signals.csv"): sha256_file(SIGNAL_ROOT / "signals.csv"),
            rel(PRICE_ROOT / "prices.csv"): sha256_file(PRICE_ROOT / "prices.csv"),
            rel(MARKET_ROOT / "twii.csv"): sha256_file(MARKET_ROOT / "twii.csv"),
            rel(ORTHOGONAL_ROOT / "manifest.json"): sha256_file(ORTHOGONAL_ROOT / "manifest.json"),
        },
        "forbidden_action_flags": FORBIDDEN_ACTION_FLAGS,
        "created_at": utc_now(),
        "created_by": rel(Path(__file__)),
    }
    write_json(out_dir / "manifest.json", manifest)

    lineage = {
        "artifact_type": "strategy_input_bundle_lineage",
        "schema_version": "v1.dng4.strategy_input_bundle.lineage",
        "bundle_id": args.bundle_id,
        "run_id": args.run_id,
        "lineage_type": "local_artifact_bundle_no_fetch_no_score_no_order",
        "source_artifacts": {
            "signals": rel(SIGNAL_ROOT / "signals.csv"),
            "signal_manifest": rel(SIGNAL_ROOT / "manifest.json"),
            "price_context": rel(PRICE_ROOT / "prices.csv"),
            "market_context": rel(MARKET_ROOT / "twii.csv"),
            "calendar": rel(CALENDAR_PATH),
            "price_readiness": rel(PRICE_READINESS),
            "orthogonal_readiness": rel(ORTHOGONAL_READINESS),
        },
        "transformations": [
            "copy_existing_standard_signal_artifact",
            "filter_price_context_to_asof",
            "filter_market_context_to_asof",
            "materialize_calendar_to_asof",
            "write_placeholder_current_holdings_with_partial_reason",
        ],
        "no_provider_publish": True,
        "no_accepted_latest_switch": True,
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

    preliminary = {
        "schema_version": "v1.dng4.strategy_input_bundle.validation",
        "generated_at": utc_now(),
        "ok": False,
        "status": "NOT_VALIDATED",
        "status_reason": "Run scripts/validate_tw_strategy_input_bundle.py for final validation.",
        "bundle_root": rel(out_dir),
    }
    write_json(out_dir / "validator_report.json", preliminary)

    print(json.dumps({"bundle_root": rel(out_dir), "status": "PARTIAL_READY"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
