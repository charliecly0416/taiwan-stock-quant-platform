#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

PHASE = "MTRP3_SAME_WINDOW_REPLAY_COMPARISON"
RUN_ID = "mtrp3_same_window_replay_comparison"
BASELINE_RULE = "top50_exit_one_worst_sell"
CANDIDATE_RULE = "top50_hold_rank_buffer_100"
BRIDGE_NAME = "top50_hold_rank_buffer_100_full_rank_visibility_bridge"
SOURCE_LINEAGE = "existing_audited_broad_reference_repackaged_for_production_candidate_readiness"

WINDOW_START = "2026-01-02"
WINDOW_END = "2026-05-07"

VERDICT_CANDIDATE_OUTPERFORMS = "PASS_CANDIDATE_OUTPERFORMS_BASELINE_READY_FOR_REVIEW"
VERDICT_CANDIDATE_NOT_OUTPERFORMING = "PASS_REPLAY_BUILT_CANDIDATE_NOT_OUTPERFORMING"
VERDICT_FAIL_MARK = "FAIL_REPLAY_ACCOUNTING_OR_MARK_QUALITY"
VERDICT_STOP_LINEAGE = "STOP_PRICE_COVERAGE_OR_LINEAGE_BLOCKER"

BRIDGE_MANIFEST = (
    ROOT
    / "data_tw/artifacts/signals/top50_hold_rank_buffer_100_full_rank_visibility_bridge/"
    / "mtrp2_r_20260628T181347Z/manifest.json"
)
BRIDGE_SIGNALS = BRIDGE_MANIFEST.parent / "signals.csv"
CANDIDATE_ORDER_MANIFEST = (
    ROOT / "data_tw/artifacts/strategies/top50_hold_rank_buffer_100/mtrp2_r_20260628T181347Z/manifest.json"
)
CANDIDATE_ORDER_INTENTS = CANDIDATE_ORDER_MANIFEST.parent / "order_intents.csv"

BASELINE_DEPENDENCY = ROOT / "configs/strategy_dependencies/top50_exit_one_worst_sell.yaml"
CANDIDATE_DEPENDENCY = ROOT / "configs/strategy_dependencies/top50_hold_rank_buffer_100.yaml"

OUT_ROOT = (
    ROOT
    / "data_tw/artifacts/replays/top50_hold_rank_buffer_100/"
    / "mtrp3_same_window_replay_comparison"
)
BASELINE_ORDER_DIR = OUT_ROOT / "baseline_order_intent"
BASELINE_REPLAY_DIR = OUT_ROOT / "baseline_replay"
CANDIDATE_REPLAY_DIR = OUT_ROOT / "candidate_replay"
REPORT_PATH = (
    ROOT
    / "docs/tw_portfolio_decision_model/"
    / "POLICY_MTRP3_SAME_WINDOW_REPLAY_COMPARISON_EXECUTION_REPORT_CN.md"
)

EXECUTION_CONFIG = {
    "initial_equity": 1000000,
    "target_holdings": 10,
    "fee_rate": 0.001425,
    "sell_tax_rate": 0.003,
    "lot_size": 10,
    "execution_price": "next_open",
    "execution_date_policy": "next_tradeable_day_after_signal_date",
    "cash_policy": "no_negative_cash",
    "mark_price": "close",
    "mark_policy": "same_day_required_fallback_audited",
    "readonly_only": True,
    "simulation_only": True,
    "production_allowed": False,
}

ALLOWED_PRICE_SOURCES = [
    {
        "source_path": "data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_r_real_model_a_top50_bridge_coverage_repair/stock_price_bridge",
        "source_kind": "stock_price_bridge",
        "source_priority": 1,
    },
    {
        "source_path": "data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/option_c_ops/rcpt15_r1_option_c_yahoo_scrapling_refresh_20260625/candidate_normalized",
        "source_kind": "staged_candidate_normalized",
        "source_priority": 2,
    },
    {
        "source_path": "data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/stock_price_bridge",
        "source_kind": "stock_price_bridge",
        "source_priority": 3,
    },
]
DEMO_SOURCE_PATH = "data_tw/self_contained_demo/normalized"

REQUIRED_READ_FILES = [
    "docs/tw_portfolio_decision_model/POLICY_MTRC6_COORDINATOR_DECISION_AND_PRODUCTION_GATE_CN.md",
    "docs/tw_portfolio_decision_model/POLICY_MTRP2_R_FULL_RANK_VISIBILITY_BRIDGE_AND_ORDER_INTENT_REVIEW_CN.md",
    "docs/tw_portfolio_decision_model/POLICY_MTRP2_R_FULL_RANK_VISIBILITY_BRIDGE_AND_ORDER_INTENT_EXECUTION_REPORT_CN.md",
    "configs/strategy_dependencies/top50_hold_rank_buffer_100.yaml",
    "configs/strategy_dependencies/top50_exit_one_worst_sell.yaml",
    "docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md",
    "docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md",
    "docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md",
    "docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md",
    "docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md",
    "scripts/build_tw_policy_mtrp2_r_full_rank_visibility_bridge_and_order_intent.py",
    "scripts/build_tw_policy_mtrc5_mark_to_market_price_coverage_repair_and_rerun.py",
]

ORDER_FIELDS = [
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
    "portfolio_state_artifact",
    "current_holding_flag",
    "target_holding_count",
    "candidate_k",
    "sell_boundary",
    "buy_order",
    "tie_breaker",
    "readonly_only",
    "simulation_only",
    "production_allowed",
    "not_order",
    "not_investment_advice",
    "model_family",
    "signal_asof",
    "available_at",
    "source_lineage",
]

SUMMARY_FIELDS = [
    "window",
    "signal_window_start",
    "signal_window_end",
    "execution_start_date",
    "execution_end_date",
    "model_name",
    "model_family",
    "strategy_rule",
    "initial_cash",
    "final_equity",
    "total_return",
    "max_drawdown",
    "action_count",
    "buy_count",
    "sell_count",
    "skipped_action_count",
    "max_holding_count",
    "duplicate_position_count",
    "negative_cash_count",
    "missing_price_count",
    "same_day_mark_coverage_ratio",
    "final_date_same_day_mark_coverage_ratio",
    "max_mark_lag_days",
    "diagnostic_only",
]

ACTION_FIELDS = [
    "signal_date",
    "execution_date",
    "instrument",
    "action",
    "quantity",
    "execution_price",
    "commission",
    "tax",
    "cash_after",
    "position_after",
    "intent_reason",
    "strategy_rule",
    "model_name",
    "order_intent_artifact",
]

SKIPPED_FIELDS = [
    "signal_date",
    "execution_date",
    "instrument",
    "intent_action",
    "skip_reason",
    "execution_price",
    "cash",
    "holding_quantity",
    "intent_reason",
    "strategy_rule",
    "model_name",
    "order_intent_artifact",
]

NAV_FIELDS = ["date", "cash", "market_value", "equity", "daily_return", "holding_count", "missing_price_count"]
SNAPSHOT_FIELDS = [
    "date",
    "instrument",
    "quantity",
    "cost_basis",
    "mark_price",
    "market_value",
    "unrealized_pnl",
    "strategy_rule",
    "model_name",
    "mark_price_date",
    "mark_price_policy",
]

FORBIDDEN_SCOPE_ITEMS = [
    "production_registry_default_change",
    "frontend_api_agent_daily_change",
    "provider_refresh_or_publish",
    "accepted_latest_switch",
    "formal_price_store_write",
    "broker_connection",
    "quick_trade",
    "real_order",
    "target_weight_instruction",
    "target_position_instruction",
    "production_ready_claim",
    "model_training",
    "model_score_recompute",
    "strategy_tuning",
    "self_contained_demo_price_source",
]

FORBIDDEN_REPLAY_FIELDS = {
    "broker_order_id",
    "broker_account",
    "quick_trade_status",
    "real_order_status",
    "provider_publish_status",
    "accepted_latest_status",
    "monitor_config_write_status",
    "target_weight",
    "target_position",
    "allocation_weight",
}
FORBIDDEN_PREFIXES = ("future_return_", "future_excess_return_", "forward_return_", "label_")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def fnum(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or str(value).strip() == "":
            return default
        number = float(value)
        if math.isnan(number):
            return default
        return number
    except (TypeError, ValueError):
        return default


def money(value: float) -> str:
    return f"{value:.6f}"


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def fmt_rank(value: Any) -> str:
    number = fnum(value, float("nan"))
    if math.isnan(number):
        return ""
    return str(int(number)) if number.is_integer() else f"{number:.12g}"


def require_inputs() -> None:
    required = [
        BRIDGE_MANIFEST,
        BRIDGE_SIGNALS,
        CANDIDATE_ORDER_MANIFEST,
        CANDIDATE_ORDER_INTENTS,
        BASELINE_DEPENDENCY,
        CANDIDATE_DEPENDENCY,
    ]
    missing = [rel(path) for path in required if not path.exists()]
    missing += [item for item in REQUIRED_READ_FILES if not (ROOT / item).exists()]
    if missing:
        raise FileNotFoundError("Missing required MTRP3 input(s): " + ", ".join(missing))


def filter_window(rows: list[dict[str, str]], date_field: str) -> list[dict[str, str]]:
    return [row for row in rows if WINDOW_START <= str(row.get(date_field, "")) <= WINDOW_END]


def bridge_rows_by_date(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in filter_window(rows, "date"):
        by_date[row["date"]].append(row)
    return dict(sorted(by_date.items()))


def make_baseline_intent(
    row: dict[str, str],
    action: str,
    reason: str,
    buy_rank: str | int,
    current_holding: bool,
) -> dict[str, Any]:
    return {
        "signal_date": row["date"],
        "instrument": row["instrument"],
        "intent_action": action,
        "intent_reason": reason,
        "strategy_rule": BASELINE_RULE,
        "candidate_rank": fmt_rank(row.get("candidate_rank")),
        "buy_rank": buy_rank,
        "full_qlib_rank": fmt_rank(row.get("full_qlib_rank")),
        "max_buy_count": 1,
        "max_sell_count": 1,
        "model_name": BRIDGE_NAME,
        "signal_artifact": rel(BRIDGE_MANIFEST),
        "portfolio_state_artifact": "readonly_intent_state_from_prior_intents_no_execution_no_quantity",
        "current_holding_flag": bool_text(current_holding),
        "target_holding_count": 10,
        "candidate_k": 50,
        "sell_boundary": "full_qlib_rank_gt_50_or_candidate_rank_gt_50",
        "buy_order": "buy_score_desc_full_qlib_rank_asc_instrument_asc",
        "tie_breaker": "full_qlib_rank_desc,instrument_asc_for_sell;buy_score_desc,full_qlib_rank_asc,instrument_asc_for_buy",
        "readonly_only": "true",
        "simulation_only": "true",
        "production_allowed": "false",
        "not_order": "true",
        "not_investment_advice": "true",
        "model_family": row.get("model_family", ""),
        "signal_asof": row.get("signal_asof", ""),
        "available_at": row.get("available_at", ""),
        "source_lineage": SOURCE_LINEAGE,
    }


def build_baseline_order_intent(bridge_rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    by_date = bridge_rows_by_date(bridge_rows)
    holdings: set[str] = set()
    intents: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    stats = Counter()

    for day, day_rows in by_date.items():
        by_inst = {row["instrument"]: row for row in day_rows}
        held_before = set(holdings)
        missing_visibility = sorted(inst for inst in held_before if inst not in by_inst)
        day_intents: list[dict[str, Any]] = []
        sold = ""
        bought = ""
        status = "pass"
        details = "sell worst current holding outside qlib top50; buy highest buy_score top50 unheld"

        if missing_visibility:
            status = "fail"
            details = "holding visibility missing; baseline OrderIntent cannot assume rank"
            stats["missing_visibility_days"] += 1
        else:
            sell_candidates = []
            for inst in held_before:
                row = by_inst[inst]
                full_rank = fnum(row.get("full_qlib_rank"), 10**9)
                candidate_rank = fnum(row.get("candidate_rank"), 10**9)
                if full_rank > 50 or candidate_rank > 50:
                    sell_candidates.append(row)
            sell_candidates.sort(
                key=lambda row: (
                    -fnum(row.get("full_qlib_rank"), -1.0),
                    -fnum(row.get("candidate_rank"), -1.0),
                    row["instrument"],
                )
            )
            for sell_row in sell_candidates[:1]:
                sold = sell_row["instrument"]
                day_intents.append(
                    make_baseline_intent(sell_row, "sell", "top50_exit_one_worst_sell_worst_outside_top50", "", True)
                )
                holdings.remove(sold)

            top50 = [
                row
                for row in day_rows
                if fnum(row.get("candidate_rank"), 10**9) <= 50
                and str(row.get("ext_buy_ranking_allowed", "")).lower() == "true"
                and str(row.get("buy_score", "")).strip() != ""
            ]
            top50.sort(key=lambda row: (-fnum(row.get("buy_score")), fnum(row.get("full_qlib_rank")), row["instrument"]))
            buy_rank_by_inst = {row["instrument"]: idx for idx, row in enumerate(top50, start=1)}
            if len(holdings) < 10:
                for buy_row in top50:
                    if buy_row["instrument"] in holdings:
                        continue
                    bought = buy_row["instrument"]
                    day_intents.append(
                        make_baseline_intent(
                            buy_row,
                            "buy",
                            "top50_buy_score_best_unheld",
                            buy_rank_by_inst[buy_row["instrument"]],
                            False,
                        )
                    )
                    holdings.add(bought)
                    break

        intents.extend(day_intents)
        stats["buy_intent_count"] += sum(1 for row in day_intents if row["intent_action"] == "buy")
        stats["sell_intent_count"] += sum(1 for row in day_intents if row["intent_action"] == "sell")
        stats["max_holding_count"] = max(stats["max_holding_count"], len(holdings))
        stats["non_top50_buy_intent_count"] += sum(
            1 for row in day_intents if row["intent_action"] == "buy" and fnum(row.get("candidate_rank"), 10**9) > 50
        )
        stats["sell_inside_top50_count"] += sum(
            1
            for row in day_intents
            if row["intent_action"] == "sell"
            and fnum(row.get("candidate_rank"), 10**9) <= 50
            and fnum(row.get("full_qlib_rank"), 10**9) <= 50
        )

        audit.append(
            {
                "signal_date": day,
                "status": status,
                "visible_row_count": len(day_rows),
                "top50_row_count": sum(1 for row in day_rows if fnum(row.get("candidate_rank"), 10**9) <= 50),
                "holding_count_before": len(held_before),
                "holding_count_after": len(holdings),
                "sell_intent_count": sum(1 for row in day_intents if row["intent_action"] == "sell"),
                "buy_intent_count": sum(1 for row in day_intents if row["intent_action"] == "buy"),
                "sold_instrument": sold,
                "bought_instrument": bought,
                "missing_visibility_count": len(missing_visibility),
                "missing_visibility_instruments": "|".join(missing_visibility),
                "details": details,
            }
        )

    return intents, audit, dict(stats)


def validate_order_intents(intents: list[dict[str, Any]], audit: list[dict[str, Any]], stats: dict[str, Any]) -> dict[str, Any]:
    fields = set(ORDER_FIELDS)
    forbidden_present = sorted(
        field
        for field in fields
        if field in FORBIDDEN_REPLAY_FIELDS or any(field.startswith(prefix) for prefix in FORBIDDEN_PREFIXES)
    )
    checks = {
        "order_intents_present": bool(intents),
        "required_fields_present": all(set(row) >= fields for row in intents),
        "daily_buy_lte_1": max(Counter(row["signal_date"] for row in intents if row["intent_action"] == "buy").values() or [0]) <= 1,
        "daily_sell_lte_1": max(Counter(row["signal_date"] for row in intents if row["intent_action"] == "sell").values() or [0]) <= 1,
        "non_top50_buy_intent_count_zero": int(stats.get("non_top50_buy_intent_count", 0)) == 0,
        "sell_inside_top50_count_zero": int(stats.get("sell_inside_top50_count", 0)) == 0,
        "strategy_decision_audit_no_fail": all(row.get("status") != "fail" for row in audit),
        "forbidden_fields_absent": not forbidden_present,
    }
    return {
        "schema_version": "mtrp3_baseline_order_intent_validator_v1",
        "created_at": now_iso(),
        "checks": checks,
        "stats": stats,
        "forbidden_fields_present": forbidden_present,
        "status": "pass" if all(checks.values()) else "fail",
    }


def write_baseline_order_intent(
    intents: list[dict[str, Any]],
    audit: list[dict[str, Any]],
    stats: dict[str, Any],
    validator: dict[str, Any],
) -> None:
    write_csv(BASELINE_ORDER_DIR / "order_intents.csv", intents, ORDER_FIELDS)
    write_csv(
        BASELINE_ORDER_DIR / "strategy_decision_audit.csv",
        audit,
        [
            "signal_date",
            "status",
            "visible_row_count",
            "top50_row_count",
            "holding_count_before",
            "holding_count_after",
            "sell_intent_count",
            "buy_intent_count",
            "sold_instrument",
            "bought_instrument",
            "missing_visibility_count",
            "missing_visibility_instruments",
            "details",
        ],
    )
    write_json(
        BASELINE_ORDER_DIR / "schema.json",
        {
            "artifact_type": "schema",
            "schema_version": "mtrp3_baseline_order_intent_v1",
            "required_order_intent_fields": ORDER_FIELDS,
            "allowed_actions": ["buy", "sell", "hold", "skip"],
            "forbidden_execution_fields": sorted(FORBIDDEN_REPLAY_FIELDS),
            "rule": {
                "strategy_rule": BASELINE_RULE,
                "target_holding_count": 10,
                "candidate_k": 50,
                "max_buy_count": 1,
                "max_sell_count": 1,
                "sell_boundary": "full_qlib_rank_gt_50_or_candidate_rank_gt_50",
                "buy_order": "buy_score_desc_full_qlib_rank_asc_instrument_asc",
            },
        },
    )
    write_json(
        BASELINE_ORDER_DIR / "forbidden_action_audit.json",
        {
            "train_model": False,
            "tune_model": False,
            "score_recompute": False,
            "read_model_private_file": False,
            "read_replay_return_as_input": False,
            "read_future_price_or_label": False,
            "provider_publish": False,
            "accepted_latest_switch": False,
            "frontend_or_api_or_agent_change": False,
            "daily_auto_latest_pointer_switch": False,
            "formal_pricestore_write": False,
            "broker_connection": False,
            "quick_trade": False,
            "real_order": False,
            "target_weight_or_target_position_output": False,
        },
    )
    write_json(BASELINE_ORDER_DIR / "validator_report.json", validator)
    write_json(
        BASELINE_ORDER_DIR / "manifest.json",
        {
            "artifact_type": "order_intent",
            "schema_version": "mtrp3_baseline_order_intent_v1",
            "phase": PHASE,
            "run_id": RUN_ID,
            "created_at": now_iso(),
            "created_by": rel(Path(__file__)),
            "strategy_rule": BASELINE_RULE,
            "dependency": rel(BASELINE_DEPENDENCY),
            "signal_artifact": rel(BRIDGE_MANIFEST),
            "source_lineage": SOURCE_LINEAGE,
            "readonly_only": True,
            "simulation_only": True,
            "production_allowed": False,
            "not_default_switch": True,
            "not_published_latest": True,
            "not_investment_advice": True,
            "max_buy_count": 1,
            "max_sell_count": 1,
            "target_holding_count": 10,
            "candidate_k": 50,
            "order_intent_count": len(intents),
            "buy_intent_count": stats.get("buy_intent_count", 0),
            "sell_intent_count": stats.get("sell_intent_count", 0),
            "validator_status": validator["status"],
            "output_files": {
                "manifest": rel(BASELINE_ORDER_DIR / "manifest.json"),
                "order_intents": rel(BASELINE_ORDER_DIR / "order_intents.csv"),
                "schema": rel(BASELINE_ORDER_DIR / "schema.json"),
                "strategy_decision_audit": rel(BASELINE_ORDER_DIR / "strategy_decision_audit.csv"),
                "forbidden_action_audit": rel(BASELINE_ORDER_DIR / "forbidden_action_audit.json"),
                "validator_report": rel(BASELINE_ORDER_DIR / "validator_report.json"),
            },
        },
    )


def read_price_file(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = read_csv_rows(path)
    out: list[dict[str, Any]] = []
    for row in rows:
        date = str(row.get("date") or row.get("price_date") or "")
        instrument = str(row.get("symbol") or row.get("instrument") or path.stem)
        open_px = fnum(row.get("open"))
        close_px = fnum(row.get("close"))
        if not date or not instrument or open_px <= 0 or close_px <= 0:
            continue
        out.append(
            {
                "price_date": date,
                "instrument": instrument,
                "open": open_px,
                "close": close_px,
                "source_path": rel(path),
            }
        )
    return out


def load_price_rows(required_instruments: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    selected: dict[tuple[str, str], dict[str, Any]] = {}
    source_audit: list[dict[str, Any]] = []
    for source in ALLOWED_PRICE_SOURCES:
        source_path = ROOT / source["source_path"]
        csv_files = sorted(source_path.glob("*.csv")) if source_path.exists() else []
        overlap = required_instruments & {path.stem for path in csv_files}
        source_audit.append(
            {
                "source_path": source["source_path"],
                "source_kind": source["source_kind"],
                "source_priority": source["source_priority"],
                "exists": bool_text(source_path.exists()),
                "csv_file_count": len(csv_files),
                "required_instrument_overlap": len(overlap),
                "required_instrument_count": len(required_instruments),
                "policy_status": "allowed_local_audited_ohlcv_source",
                "status": "pass" if source_path.exists() else "missing",
            }
        )
        for inst in sorted(required_instruments):
            file_path = source_path / f"{inst}.csv"
            if not file_path.exists():
                continue
            for row in read_price_file(file_path):
                key = (row["price_date"], row["instrument"])
                if key in selected:
                    continue
                selected[key] = {
                    **row,
                    "source_kind": source["source_kind"],
                    "source_priority": source["source_priority"],
                }
    demo_path = ROOT / DEMO_SOURCE_PATH
    source_audit.append(
        {
            "source_path": DEMO_SOURCE_PATH,
            "source_kind": "self_contained_demo",
            "source_priority": "",
            "exists": bool_text(demo_path.exists()),
            "csv_file_count": len(list(demo_path.glob("*.csv"))) if demo_path.exists() else 0,
            "required_instrument_overlap": 0,
            "required_instrument_count": len(required_instruments),
            "policy_status": "forbidden_not_used",
            "status": "pass",
        }
    )
    return [selected[key] for key in sorted(selected)], source_audit


def build_price_maps(
    rows: list[dict[str, Any]],
) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    by_inst: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_key[(row["price_date"], row["instrument"])] = row
        by_inst[row["instrument"]].append(row)
    for inst in by_inst:
        by_inst[inst].sort(key=lambda row: row["price_date"])
    return by_key, by_inst


def next_open_after(
    instrument: str,
    signal_date: str,
    price_by_inst: dict[str, list[dict[str, Any]]],
) -> dict[str, Any] | None:
    for row in price_by_inst.get(instrument, []):
        if row["price_date"] > signal_date and fnum(row["open"]) > 0:
            return row
    return None


def latest_mark(
    instrument: str,
    date: str,
    price_by_inst: dict[str, list[dict[str, Any]]],
) -> tuple[float, str, str]:
    selected: dict[str, Any] | None = None
    for row in price_by_inst.get(instrument, []):
        if row["price_date"] > date:
            break
        selected = row
    if not selected:
        return 0.0, "", "missing"
    policy = "same_date_close" if selected["price_date"] == date else "latest_prior_close_audited"
    return fnum(selected["close"]), selected["price_date"], policy


def build_execution_plan(
    strategy_rule: str,
    intents: list[dict[str, Any]],
    order_manifest_rel: str,
    price_by_inst: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    plan: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    for idx, intent in enumerate(intents):
        row = next_open_after(intent["instrument"], intent["signal_date"], price_by_inst)
        status = "pass" if row else "missing"
        execution_date = row["price_date"] if row else ""
        next_open = fnum(row["open"]) if row else 0.0
        plan_row = {
            **intent,
            "execution_date": execution_date,
            "execution_price": next_open,
            "execution_price_source": row.get("source_path", "") if row else "",
            "execution_price_source_kind": row.get("source_kind", "") if row else "",
            "execution_price_source_priority": row.get("source_priority", "") if row else "",
            "order_intent_artifact": order_manifest_rel,
            "_intent_index": idx,
        }
        plan.append(plan_row)
        audit.append(
            {
                "strategy_rule": strategy_rule,
                "signal_date": intent["signal_date"],
                "execution_date": execution_date,
                "instrument": intent["instrument"],
                "intent_action": intent["intent_action"],
                "execution_price_policy": EXECUTION_CONFIG["execution_price"],
                "execution_date_policy": EXECUTION_CONFIG["execution_date_policy"],
                "next_open": money(next_open) if row else "",
                "source_path": row.get("source_path", "") if row else "",
                "source_kind": row.get("source_kind", "") if row else "",
                "source_priority": row.get("source_priority", "") if row else "",
                "status": status,
                "details": "next open selected from allowed local OHLCV source"
                if row
                else "no next tradeable open available in allowed local OHLCV source",
            }
        )
    return plan, audit


def compute_equity(
    date: str,
    cash: float,
    positions: dict[str, dict[str, float]],
    price_by_inst: dict[str, list[dict[str, Any]]],
) -> tuple[float, float, list[dict[str, Any]]]:
    market_value = 0.0
    mark_rows: list[dict[str, Any]] = []
    for inst, pos in positions.items():
        mark, mark_date, policy = latest_mark(inst, date, price_by_inst)
        if mark <= 0:
            mark_rows.append(
                {
                    "date": date,
                    "instrument": inst,
                    "status": "fail",
                    "value": "missing",
                    "threshold": "same_day_close_required_or_fallback_audited",
                    "details": "No close price available at or before replay date.",
                }
            )
            continue
        if policy != "same_date_close":
            mark_rows.append(
                {
                    "date": date,
                    "instrument": inst,
                    "status": "audited_fallback",
                    "value": mark_date,
                    "threshold": date,
                    "details": "Same-day close missing; latest prior close used and audited.",
                }
            )
        market_value += pos["quantity"] * mark
    return cash + market_value, market_value, mark_rows


def replay_sort_key(row: dict[str, Any]) -> tuple[str, int, str, int]:
    action_rank = 0 if row["intent_action"] == "sell" else 1 if row["intent_action"] == "buy" else 2
    return (row["execution_date"], action_rank, row["signal_date"], int(row.get("_intent_index", 0)))


def run_replay(
    strategy_rule: str,
    intents: list[dict[str, Any]],
    execution_plan: list[dict[str, Any]],
    order_manifest_rel: str,
    price_by_inst: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    cash = float(EXECUTION_CONFIG["initial_equity"])
    target_holdings = int(EXECUTION_CONFIG["target_holdings"])
    fee_rate = float(EXECUTION_CONFIG["fee_rate"])
    sell_tax_rate = float(EXECUTION_CONFIG["sell_tax_rate"])
    lot_size = int(EXECUTION_CONFIG["lot_size"])

    positions: dict[str, dict[str, float]] = {}
    actions: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    daily_nav: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []
    daily_cash_audit: list[dict[str, Any]] = []
    fallback_rows: list[dict[str, Any]] = []

    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in execution_plan:
        if not row.get("execution_date") or fnum(row.get("execution_price")) <= 0:
            skipped.append(
                {
                    "signal_date": row.get("signal_date", ""),
                    "execution_date": row.get("execution_date", ""),
                    "instrument": row.get("instrument", ""),
                    "intent_action": row.get("intent_action", ""),
                    "skip_reason": "missing_next_open_execution_price",
                    "execution_price": "",
                    "cash": money(cash),
                    "holding_quantity": int(positions.get(row.get("instrument", ""), {}).get("quantity", 0)),
                    "intent_reason": row.get("intent_reason", ""),
                    "strategy_rule": strategy_rule,
                    "model_name": row.get("model_name", ""),
                    "order_intent_artifact": order_manifest_rel,
                }
            )
            continue
        by_date[row["execution_date"]].append(row)

    previous_equity = cash
    peak_equity = cash
    max_drawdown = 0.0
    execution_date_bad = 0
    quantity_bad = 0
    negative_cash_count = 0

    for date in sorted(by_date):
        for row in sorted(by_date[date], key=replay_sort_key):
            signal_date = row["signal_date"]
            instrument = row["instrument"]
            action = row["intent_action"]
            execution_price = fnum(row["execution_price"])
            if date <= signal_date:
                execution_date_bad += 1

            if action == "sell":
                held_qty = int(positions.get(instrument, {}).get("quantity", 0))
                if held_qty <= 0:
                    skipped.append(
                        {
                            "signal_date": signal_date,
                            "execution_date": date,
                            "instrument": instrument,
                            "intent_action": action,
                            "skip_reason": "sell_intent_without_current_holding",
                            "execution_price": money(execution_price),
                            "cash": money(cash),
                            "holding_quantity": 0,
                            "intent_reason": row.get("intent_reason", ""),
                            "strategy_rule": strategy_rule,
                            "model_name": row.get("model_name", ""),
                            "order_intent_artifact": order_manifest_rel,
                        }
                    )
                    continue
                gross = held_qty * execution_price
                commission = gross * fee_rate
                tax = gross * sell_tax_rate
                cash += gross - commission - tax
                del positions[instrument]
                actions.append(
                    {
                        "signal_date": signal_date,
                        "execution_date": date,
                        "instrument": instrument,
                        "action": "sell",
                        "quantity": held_qty,
                        "execution_price": money(execution_price),
                        "commission": money(commission),
                        "tax": money(tax),
                        "cash_after": money(cash),
                        "position_after": 0,
                        "intent_reason": row.get("intent_reason", ""),
                        "strategy_rule": strategy_rule,
                        "model_name": row.get("model_name", ""),
                        "order_intent_artifact": order_manifest_rel,
                    }
                )
            elif action == "buy":
                if instrument in positions:
                    skipped.append(
                        {
                            "signal_date": signal_date,
                            "execution_date": date,
                            "instrument": instrument,
                            "intent_action": action,
                            "skip_reason": "buy_intent_duplicate_existing_position",
                            "execution_price": money(execution_price),
                            "cash": money(cash),
                            "holding_quantity": int(positions[instrument]["quantity"]),
                            "intent_reason": row.get("intent_reason", ""),
                            "strategy_rule": strategy_rule,
                            "model_name": row.get("model_name", ""),
                            "order_intent_artifact": order_manifest_rel,
                        }
                    )
                    continue
                current_equity, _market_value, mark_rows = compute_equity(date, cash, positions, price_by_inst)
                fallback_rows.extend(mark_rows)
                budget = current_equity / target_holdings
                quantity = int(math.floor((budget / execution_price) / lot_size) * lot_size)
                gross = quantity * execution_price
                commission = gross * fee_rate
                total_cost = gross + commission
                if quantity <= 0:
                    skipped.append(
                        {
                            "signal_date": signal_date,
                            "execution_date": date,
                            "instrument": instrument,
                            "intent_action": action,
                            "skip_reason": "buy_quantity_zero_after_lot_rounding",
                            "execution_price": money(execution_price),
                            "cash": money(cash),
                            "holding_quantity": 0,
                            "intent_reason": row.get("intent_reason", ""),
                            "strategy_rule": strategy_rule,
                            "model_name": row.get("model_name", ""),
                            "order_intent_artifact": order_manifest_rel,
                        }
                    )
                    continue
                if cash + 1e-9 < total_cost:
                    skipped.append(
                        {
                            "signal_date": signal_date,
                            "execution_date": date,
                            "instrument": instrument,
                            "intent_action": action,
                            "skip_reason": "insufficient_cash_for_budget_quantity",
                            "execution_price": money(execution_price),
                            "cash": money(cash),
                            "holding_quantity": 0,
                            "intent_reason": row.get("intent_reason", ""),
                            "strategy_rule": strategy_rule,
                            "model_name": row.get("model_name", ""),
                            "order_intent_artifact": order_manifest_rel,
                        }
                    )
                    continue
                cash -= total_cost
                positions[instrument] = {"quantity": float(quantity), "cost_basis": total_cost / quantity}
                actions.append(
                    {
                        "signal_date": signal_date,
                        "execution_date": date,
                        "instrument": instrument,
                        "action": "buy",
                        "quantity": quantity,
                        "execution_price": money(execution_price),
                        "commission": money(commission),
                        "tax": money(0.0),
                        "cash_after": money(cash),
                        "position_after": quantity,
                        "intent_reason": row.get("intent_reason", ""),
                        "strategy_rule": strategy_rule,
                        "model_name": row.get("model_name", ""),
                        "order_intent_artifact": order_manifest_rel,
                    }
                )
            else:
                skipped.append(
                    {
                        "signal_date": signal_date,
                        "execution_date": date,
                        "instrument": instrument,
                        "intent_action": action,
                        "skip_reason": "non_trade_intent_action",
                        "execution_price": money(execution_price),
                        "cash": money(cash),
                        "holding_quantity": int(positions.get(instrument, {}).get("quantity", 0)),
                        "intent_reason": row.get("intent_reason", ""),
                        "strategy_rule": strategy_rule,
                        "model_name": row.get("model_name", ""),
                        "order_intent_artifact": order_manifest_rel,
                    }
                )

        equity, market_value, mark_rows = compute_equity(date, cash, positions, price_by_inst)
        fallback_rows.extend(mark_rows)
        daily_return = (equity / previous_equity - 1.0) if previous_equity else 0.0
        previous_equity = equity
        peak_equity = max(peak_equity, equity)
        max_drawdown = min(max_drawdown, (equity / peak_equity - 1.0) if peak_equity else 0.0)
        if cash < -1e-7:
            negative_cash_count += 1
        missing_price_count = len(mark_rows)
        daily_nav.append(
            {
                "date": date,
                "cash": money(cash),
                "market_value": money(market_value),
                "equity": money(equity),
                "daily_return": f"{daily_return:.10f}",
                "holding_count": len(positions),
                "missing_price_count": missing_price_count,
            }
        )
        daily_cash_audit.append(
            {
                "date": date,
                "cash": money(cash),
                "negative_cash": bool_text(cash < -1e-7),
                "status": "fail" if cash < -1e-7 else "pass",
                "details": "Cash remains non-negative after readonly simulated executions.",
            }
        )
        for inst in sorted(positions):
            pos = positions[inst]
            mark, mark_date, policy = latest_mark(inst, date, price_by_inst)
            market = pos["quantity"] * mark if mark > 0 else 0.0
            snapshots.append(
                {
                    "date": date,
                    "instrument": inst,
                    "quantity": int(pos["quantity"]),
                    "cost_basis": money(pos["cost_basis"]),
                    "mark_price": money(mark),
                    "market_value": money(market),
                    "unrealized_pnl": money((mark - pos["cost_basis"]) * pos["quantity"]) if mark > 0 else money(0.0),
                    "strategy_rule": strategy_rule,
                    "model_name": row_model_name(intents),
                    "mark_price_date": mark_date,
                    "mark_price_policy": policy,
                }
            )

    for action in actions:
        qty = int(action["quantity"])
        if qty <= 0 or qty % lot_size != 0:
            quantity_bad += 1

    duplicate_position_count = 0
    seen_positions: set[tuple[str, str]] = set()
    for snap in snapshots:
        key = (snap["date"], snap["instrument"])
        if key in seen_positions:
            duplicate_position_count += 1
        seen_positions.add(key)

    final_holdings_missing_mark = 0
    if daily_nav:
        final_date = daily_nav[-1]["date"]
        for inst in positions:
            mark, _mark_date, _policy = latest_mark(inst, final_date, price_by_inst)
            if mark <= 0:
                final_holdings_missing_mark += 1

    return {
        "actions": actions,
        "skipped": skipped,
        "daily_nav": daily_nav,
        "snapshots": snapshots,
        "daily_cash_audit": daily_cash_audit,
        "fallback_rows": fallback_rows,
        "max_drawdown": max_drawdown,
        "final_positions": positions,
        "integrity_stats": {
            "active_action_quantity_bad": quantity_bad,
            "execution_date_not_after_signal_date": execution_date_bad,
            "max_holding_count": max((int(row["holding_count"]) for row in daily_nav), default=0),
            "duplicate_position_count": duplicate_position_count,
            "negative_cash_count": negative_cash_count,
            "final_holdings_missing_mark": final_holdings_missing_mark,
        },
    }


def row_model_name(intents: list[dict[str, Any]]) -> str:
    values = sorted({str(row.get("model_name", "")) for row in intents if row.get("model_name", "")})
    return values[0] if values else BRIDGE_NAME


def row_model_family(intents: list[dict[str, Any]]) -> str:
    values = sorted({str(row.get("model_family", "")) for row in intents if row.get("model_family", "")})
    return values[0] if values else "ltr"


def mark_stats(replay_result: dict[str, Any]) -> dict[str, Any]:
    snapshots = replay_result["snapshots"]
    total = len(snapshots)
    same_day = sum(1 for row in snapshots if row.get("mark_price_policy") == "same_date_close")
    final_same_day = 0
    final_total = 0
    max_lag = 0
    if snapshots:
        final_date = max(row["date"] for row in snapshots)
        final_rows = [row for row in snapshots if row["date"] == final_date]
        final_total = len(final_rows)
        final_same_day = sum(1 for row in final_rows if row.get("mark_price_policy") == "same_date_close")
    for row in snapshots:
        date = row.get("date", "")
        mark_date = row.get("mark_price_date", "")
        if date and mark_date:
            max_lag = max(max_lag, (pd.Timestamp(date) - pd.Timestamp(mark_date)).days)
    return {
        "snapshot_count": total,
        "same_day_mark_coverage_ratio": round(same_day / total, 10) if total else 1.0,
        "final_date_same_day_mark_coverage_ratio": round(final_same_day / final_total, 10) if final_total else 1.0,
        "max_mark_lag_days": max_lag,
        "fallback_mark_count": total - same_day,
        "final_date_fallback_mark_count": final_total - final_same_day,
    }


def build_summary(strategy_rule: str, intents: list[dict[str, Any]], replay_result: dict[str, Any]) -> dict[str, Any]:
    nav = replay_result["daily_nav"]
    initial = float(EXECUTION_CONFIG["initial_equity"])
    final_equity = fnum(nav[-1]["equity"], initial) if nav else initial
    marks = mark_stats(replay_result)
    return {
        "window": f"{WINDOW_START}..{WINDOW_END}",
        "signal_window_start": WINDOW_START,
        "signal_window_end": WINDOW_END,
        "execution_start_date": nav[0]["date"] if nav else "",
        "execution_end_date": nav[-1]["date"] if nav else "",
        "model_name": row_model_name(intents),
        "model_family": row_model_family(intents),
        "strategy_rule": strategy_rule,
        "initial_cash": money(initial),
        "final_equity": money(final_equity),
        "total_return": f"{(final_equity / initial - 1.0):.10f}" if initial else "0.0000000000",
        "max_drawdown": f"{replay_result['max_drawdown']:.10f}",
        "action_count": len(replay_result["actions"]),
        "buy_count": sum(1 for row in replay_result["actions"] if row["action"] == "buy"),
        "sell_count": sum(1 for row in replay_result["actions"] if row["action"] == "sell"),
        "skipped_action_count": len(replay_result["skipped"]),
        "max_holding_count": replay_result["integrity_stats"]["max_holding_count"],
        "duplicate_position_count": replay_result["integrity_stats"]["duplicate_position_count"],
        "negative_cash_count": replay_result["integrity_stats"]["negative_cash_count"],
        "missing_price_count": sum(int(row["missing_price_count"]) for row in nav),
        "same_day_mark_coverage_ratio": marks["same_day_mark_coverage_ratio"],
        "final_date_same_day_mark_coverage_ratio": marks["final_date_same_day_mark_coverage_ratio"],
        "max_mark_lag_days": marks["max_mark_lag_days"],
        "diagnostic_only": "false",
    }


def build_position_integrity_audit(replay_result: dict[str, Any]) -> list[dict[str, Any]]:
    stats = replay_result["integrity_stats"]
    rows = [
        {
            "audit_name": "active_action_quantity_gt_0_and_lot_multiple",
            "date": "ALL",
            "instrument": "ALL",
            "status": "pass" if stats["active_action_quantity_bad"] == 0 else "fail",
            "value": stats["active_action_quantity_bad"],
            "threshold": "0",
            "details": "Executed actions must have positive quantity and lot_size=10 multiple.",
        },
        {
            "audit_name": "execution_date_gt_signal_date",
            "date": "ALL",
            "instrument": "ALL",
            "status": "pass" if stats["execution_date_not_after_signal_date"] == 0 else "fail",
            "value": stats["execution_date_not_after_signal_date"],
            "threshold": "0",
            "details": "Execution date follows next_tradeable_day_after_signal_date.",
        },
        {
            "audit_name": "max_holding_count_lte_10",
            "date": "ALL",
            "instrument": "ALL",
            "status": "pass" if stats["max_holding_count"] <= 10 else "fail",
            "value": stats["max_holding_count"],
            "threshold": "10",
            "details": "Replay must respect target_holdings=10.",
        },
        {
            "audit_name": "duplicate_position_count_equals_0",
            "date": "ALL",
            "instrument": "ALL",
            "status": "pass" if stats["duplicate_position_count"] == 0 else "fail",
            "value": stats["duplicate_position_count"],
            "threshold": "0",
            "details": "No duplicate date/instrument position snapshots.",
        },
        {
            "audit_name": "negative_cash_count_equals_0",
            "date": "ALL",
            "instrument": "ALL",
            "status": "pass" if stats["negative_cash_count"] == 0 else "fail",
            "value": stats["negative_cash_count"],
            "threshold": "0",
            "details": "No negative cash under MTRP3 cash policy.",
        },
        {
            "audit_name": "final_holdings_marked_to_market",
            "date": "FINAL",
            "instrument": "ALL",
            "status": "pass" if stats["final_holdings_missing_mark"] == 0 else "fail",
            "value": stats["final_holdings_missing_mark"],
            "threshold": "0",
            "details": "All final holdings have close mark at or before final replay date.",
        },
    ]
    fallback_counter = Counter((row["date"], row["instrument"], row["status"], row["value"]) for row in replay_result["fallback_rows"])
    for (date, inst, status, value), count in sorted(fallback_counter.items()):
        rows.append(
            {
                "audit_name": "mark_fallback_audited",
                "date": date,
                "instrument": inst,
                "status": "pass" if status == "audited_fallback" else "fail",
                "value": value,
                "threshold": date,
                "details": f"{count} mark fallback event(s) audited.",
            }
        )
    return rows


def build_coverage_audit(intents: list[dict[str, Any]], replay_result: dict[str, Any]) -> list[dict[str, Any]]:
    signal_dates = {row["signal_date"] for row in intents}
    nav_dates = {row["date"] for row in replay_result["daily_nav"]}
    marks = mark_stats(replay_result)
    return [
        {
            "audit_name": "signal_window_fixed",
            "requested_start_date": WINDOW_START,
            "requested_end_date": WINDOW_END,
            "actual_start_date": min(signal_dates) if signal_dates else "",
            "actual_end_date": max(signal_dates) if signal_dates else "",
            "trading_day_count": len(nav_dates),
            "signal_day_count": len(signal_dates),
            "price_day_count": len(nav_dates),
            "missing_signal_day_count": 0,
            "missing_price_day_count": 0,
            "status": "pass" if signal_dates and min(signal_dates) >= WINDOW_START and max(signal_dates) <= WINDOW_END else "fail",
            "details": "OrderIntent signal dates are fixed to the requested same-window interval.",
        },
        {
            "audit_name": "mark_to_market_close_same_day_coverage",
            "requested_start_date": WINDOW_START,
            "requested_end_date": WINDOW_END,
            "actual_start_date": min(nav_dates) if nav_dates else "",
            "actual_end_date": max(nav_dates) if nav_dates else "",
            "trading_day_count": len(nav_dates),
            "signal_day_count": len(signal_dates),
            "price_day_count": len(nav_dates),
            "missing_signal_day_count": 0,
            "missing_price_day_count": marks["fallback_mark_count"],
            "status": "pass" if marks["same_day_mark_coverage_ratio"] >= 0.99 and marks["max_mark_lag_days"] == 0 else "fail",
            "details": "Position snapshots require same-day close marks; fallback rows are audited.",
        },
    ]


def forbidden_field_audit(output_fields: dict[str, list[str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for artifact, fields in sorted(output_fields.items()):
        forbidden = [
            field
            for field in fields
            if field in FORBIDDEN_REPLAY_FIELDS or any(field.startswith(prefix) for prefix in FORBIDDEN_PREFIXES)
        ]
        rows.append(
            {
                "audit_name": "forbidden_replay_output_fields_absent",
                "artifact": artifact,
                "field_name": ",".join(forbidden),
                "field_category": "forbidden_output_field",
                "present": bool_text(bool(forbidden)),
                "used_for_ranking": "false",
                "status": "fail" if forbidden else "pass",
                "details": "Broker/provider/latest/target/future label fields are forbidden in MTRP3 replay outputs.",
            }
        )
    rows.append(
        {
            "audit_name": "replay_accounting_fields_not_strategy_inputs",
            "artifact": "ALL",
            "field_name": "quantity,execution_price,cash_after,position_after,daily_return,unrealized_pnl",
            "field_category": "allowed_replay_result_field",
            "present": "true",
            "used_for_ranking": "false",
            "status": "pass",
            "details": "Replay accounting fields are emitted only inside ReplayResult artifacts and are not used for ranking.",
        }
    )
    return rows


def build_execution_audit(execution_plan: list[dict[str, Any]], replay_result: dict[str, Any]) -> list[dict[str, Any]]:
    missing = sum(1 for row in execution_plan if not row.get("execution_date") or fnum(row.get("execution_price")) <= 0)
    stats = replay_result["integrity_stats"]
    return [
        {
            "audit_name": "execution_next_open_available",
            "status": "pass" if missing == 0 else "fail",
            "value": missing,
            "threshold": "0",
            "details": "Each OrderIntent must map to next tradeable open from allowed local OHLCV.",
        },
        {
            "audit_name": "execution_date_after_signal_date",
            "status": "pass" if stats["execution_date_not_after_signal_date"] == 0 else "fail",
            "value": stats["execution_date_not_after_signal_date"],
            "threshold": "0",
            "details": "Execution date policy is next_tradeable_day_after_signal_date.",
        },
        {
            "audit_name": "cash_never_negative",
            "status": "pass" if stats["negative_cash_count"] == 0 else "fail",
            "value": stats["negative_cash_count"],
            "threshold": "0",
            "details": "Buy sizing skips insufficient-cash actions instead of allowing negative cash.",
        },
    ]


def write_diagnostics(replay_dir: Path, summary: dict[str, Any], replay_result: dict[str, Any]) -> None:
    nav = replay_result["daily_nav"]
    snapshots = replay_result["snapshots"]
    monthly: list[dict[str, Any]] = []
    by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in nav:
        by_month[row["date"][:7]].append(row)
    for month, rows in sorted(by_month.items()):
        start_equity = fnum(rows[0]["equity"])
        end_equity = fnum(rows[-1]["equity"])
        monthly.append(
            {
                "month": month,
                "start_equity": money(start_equity),
                "end_equity": money(end_equity),
                "monthly_return": f"{(end_equity / start_equity - 1.0):.10f}" if start_equity else "0.0000000000",
                "day_count": len(rows),
            }
        )
    drawdowns: list[dict[str, Any]] = []
    peak = float(EXECUTION_CONFIG["initial_equity"])
    for row in nav:
        equity = fnum(row["equity"])
        peak = max(peak, equity)
        drawdowns.append(
            {
                "date": row["date"],
                "equity": row["equity"],
                "peak_equity": money(peak),
                "drawdown": f"{(equity / peak - 1.0):.10f}" if peak else "0.0000000000",
            }
        )
    concentration: list[dict[str, Any]] = []
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in snapshots:
        by_date[row["date"]].append(row)
    for date, rows in sorted(by_date.items()):
        total_mv = sum(fnum(row["market_value"]) for row in rows)
        max_mv = max((fnum(row["market_value"]) for row in rows), default=0.0)
        concentration.append(
            {
                "date": date,
                "holding_count": len(rows),
                "largest_position_market_value": money(max_mv),
                "total_market_value": money(total_mv),
                "largest_position_share": f"{(max_mv / total_mv):.10f}" if total_mv else "0.0000000000",
            }
        )
    write_csv(replay_dir / "monthly_return_diagnostic.csv", monthly, ["month", "start_equity", "end_equity", "monthly_return", "day_count"])
    write_csv(replay_dir / "drawdown_diagnostic.csv", drawdowns, ["date", "equity", "peak_equity", "drawdown"])
    write_csv(
        replay_dir / "concentration_diagnostic.csv",
        concentration,
        ["date", "holding_count", "largest_position_market_value", "total_market_value", "largest_position_share"],
    )
    write_text(
        replay_dir / "diagnostic_findings.md",
        "\n".join(
            [
                f"# {summary['strategy_rule']} MTRP3 replay diagnostic findings",
                "",
                f"- final_equity: `{summary['final_equity']}`",
                f"- total_return: `{summary['total_return']}`",
                f"- max_drawdown: `{summary['max_drawdown']}`",
                f"- actions: `{summary['action_count']}`",
                f"- skipped: `{summary['skipped_action_count']}`",
                f"- same_day_mark_coverage_ratio: `{summary['same_day_mark_coverage_ratio']}`",
                f"- max_mark_lag_days: `{summary['max_mark_lag_days']}`",
            ]
        ),
    )


def write_replay_artifact(
    replay_dir: Path,
    strategy_rule: str,
    intents: list[dict[str, Any]],
    execution_plan: list[dict[str, Any]],
    replay_result: dict[str, Any],
    order_manifest_rel: str,
    input_manifest_links: dict[str, Any],
) -> dict[str, Any]:
    summary = build_summary(strategy_rule, intents, replay_result)
    coverage_rows = build_coverage_audit(intents, replay_result)
    position_integrity_rows = build_position_integrity_audit(replay_result)
    execution_rows = build_execution_audit(execution_plan, replay_result)
    output_fields = {
        "summary.csv": SUMMARY_FIELDS,
        "actions.csv": ACTION_FIELDS,
        "daily_nav.csv": NAV_FIELDS,
        "position_snapshots.csv": SNAPSHOT_FIELDS,
        "skipped_actions.csv": SKIPPED_FIELDS,
    }
    forbidden_rows = forbidden_field_audit(output_fields)
    checks = {
        "required_files_written": True,
        "execution_next_open_available": all(row["status"] == "pass" for row in execution_rows if row["audit_name"] == "execution_next_open_available"),
        "execution_date_after_signal_date": replay_result["integrity_stats"]["execution_date_not_after_signal_date"] == 0,
        "same_day_mark_coverage_ratio_gte_0_99": fnum(summary["same_day_mark_coverage_ratio"]) >= 0.99,
        "max_mark_lag_days_eq_0": int(summary["max_mark_lag_days"]) == 0,
        "negative_cash_count_eq_0": int(summary["negative_cash_count"]) == 0,
        "duplicate_position_count_eq_0": int(summary["duplicate_position_count"]) == 0,
        "missing_price_count_eq_0": int(summary["missing_price_count"]) == 0,
        "max_holding_count_lte_10": int(summary["max_holding_count"]) <= 10,
        "forbidden_fields_absent": all(row["status"] == "pass" for row in forbidden_rows),
    }
    validator = {
        "schema_version": "mtrp3_replay_validator_v1",
        "created_at": now_iso(),
        "strategy_rule": strategy_rule,
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "summary": summary,
    }

    write_csv(replay_dir / "summary.csv", [summary], SUMMARY_FIELDS)
    write_csv(replay_dir / "actions.csv", replay_result["actions"], ACTION_FIELDS)
    write_csv(replay_dir / "daily_nav.csv", replay_result["daily_nav"], NAV_FIELDS)
    write_csv(replay_dir / "position_snapshots.csv", replay_result["snapshots"], SNAPSHOT_FIELDS)
    write_csv(
        replay_dir / "coverage_audit.csv",
        coverage_rows,
        [
            "audit_name",
            "requested_start_date",
            "requested_end_date",
            "actual_start_date",
            "actual_end_date",
            "trading_day_count",
            "signal_day_count",
            "price_day_count",
            "missing_signal_day_count",
            "missing_price_day_count",
            "status",
            "details",
        ],
    )
    write_csv(
        replay_dir / "position_integrity_audit.csv",
        position_integrity_rows,
        ["audit_name", "date", "instrument", "status", "value", "threshold", "details"],
    )
    write_csv(
        replay_dir / "forbidden_field_audit.csv",
        forbidden_rows,
        ["audit_name", "artifact", "field_name", "field_category", "present", "used_for_ranking", "status", "details"],
    )
    write_csv(replay_dir / "execution_audit.csv", execution_rows, ["audit_name", "status", "value", "threshold", "details"])
    write_csv(replay_dir / "skipped_actions.csv", replay_result["skipped"], SKIPPED_FIELDS)
    write_csv(replay_dir / "daily_cash_audit.csv", replay_result["daily_cash_audit"], ["date", "cash", "negative_cash", "status", "details"])
    write_json(replay_dir / "input_manifest_links.json", input_manifest_links)
    write_json(replay_dir / "forbidden_action_audit.json", {item: {"performed": False} for item in FORBIDDEN_SCOPE_ITEMS})
    write_json(replay_dir / "validator_report.json", validator)
    write_json(
        replay_dir / "manifest.json",
        {
            "artifact_type": "replay_result",
            "schema_version": "mtrp3_same_window_replay_v1",
            "phase": PHASE,
            "run_id": RUN_ID,
            "created_at": now_iso(),
            "created_by": rel(Path(__file__)),
            "strategy_rule": strategy_rule,
            "order_intent_artifact": order_manifest_rel,
            "signal_artifact": rel(BRIDGE_MANIFEST),
            "execution_config": EXECUTION_CONFIG,
            "source_lineage_warning": SOURCE_LINEAGE,
            "readonly_only": True,
            "simulation_only": True,
            "production_allowed": False,
            "not_published_latest": True,
            "not_default_switch": True,
            "validator_status": validator["status"],
            "summary": summary,
            "output_files": {
                "summary": rel(replay_dir / "summary.csv"),
                "actions": rel(replay_dir / "actions.csv"),
                "daily_nav": rel(replay_dir / "daily_nav.csv"),
                "position_snapshots": rel(replay_dir / "position_snapshots.csv"),
                "coverage_audit": rel(replay_dir / "coverage_audit.csv"),
                "position_integrity_audit": rel(replay_dir / "position_integrity_audit.csv"),
                "forbidden_field_audit": rel(replay_dir / "forbidden_field_audit.csv"),
                "execution_audit": rel(replay_dir / "execution_audit.csv"),
                "skipped_actions": rel(replay_dir / "skipped_actions.csv"),
                "validator_report": rel(replay_dir / "validator_report.json"),
            },
        },
    )
    write_diagnostics(replay_dir, summary, replay_result)
    return {"summary": summary, "validator": validator}


def build_mark_coverage_audit(
    baseline_result: dict[str, Any],
    candidate_result: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, result in [(BASELINE_RULE, baseline_result), (CANDIDATE_RULE, candidate_result)]:
        stats = mark_stats(result)
        rows.append(
            {
                "strategy_rule": name,
                "snapshot_count": stats["snapshot_count"],
                "same_day_mark_coverage_ratio": stats["same_day_mark_coverage_ratio"],
                "final_date_same_day_mark_coverage_ratio": stats["final_date_same_day_mark_coverage_ratio"],
                "fallback_mark_count": stats["fallback_mark_count"],
                "final_date_fallback_mark_count": stats["final_date_fallback_mark_count"],
                "max_mark_lag_days": stats["max_mark_lag_days"],
                "status": "pass"
                if stats["same_day_mark_coverage_ratio"] >= 0.99 and stats["max_mark_lag_days"] == 0
                else "fail",
                "details": "Same-day close mark coverage required for MTRP3 hard gate.",
            }
        )
    return rows


def build_comparison_rows(baseline: dict[str, Any], candidate: dict[str, Any]) -> list[dict[str, Any]]:
    metrics = [
        "final_equity",
        "total_return",
        "max_drawdown",
        "action_count",
        "buy_count",
        "sell_count",
        "skipped_action_count",
        "same_day_mark_coverage_ratio",
        "max_mark_lag_days",
    ]
    rows: list[dict[str, Any]] = []
    for metric in metrics:
        b = fnum(baseline.get(metric))
        c = fnum(candidate.get(metric))
        rows.append(
            {
                "metric": metric,
                "baseline_strategy": BASELINE_RULE,
                "baseline_value": baseline.get(metric, ""),
                "candidate_strategy": CANDIDATE_RULE,
                "candidate_value": candidate.get(metric, ""),
                "candidate_minus_baseline": f"{(c - b):.10f}" if metric not in {"action_count", "buy_count", "sell_count", "skipped_action_count", "max_mark_lag_days"} else int(c - b),
                "preferred_direction": "higher" if metric in {"final_equity", "total_return", "same_day_mark_coverage_ratio"} else "lower_or_not_materially_worse",
            }
        )
    return rows


def build_forbidden_scope_audit(source_audit: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [
        {
            "scope_item": item,
            "performed": "false",
            "status": "pass",
            "details": "MTRP3 script writes only readonly comparison artifacts and execution report.",
        }
        for item in FORBIDDEN_SCOPE_ITEMS
    ]
    demo_used = any(row["source_path"] == DEMO_SOURCE_PATH and row.get("policy_status") != "forbidden_not_used" for row in source_audit)
    if demo_used:
        rows.append(
            {
                "scope_item": "self_contained_demo_price_source",
                "performed": "true",
                "status": "fail",
                "details": "Demo source must not be used.",
            }
        )
    return rows


def determine_verdict(
    baseline_summary: dict[str, Any],
    candidate_summary: dict[str, Any],
    baseline_validator: dict[str, Any],
    candidate_validator: dict[str, Any],
    mark_rows: list[dict[str, Any]],
    lineage_ok: bool,
) -> str:
    if not lineage_ok or any(row["status"] != "pass" for row in mark_rows):
        return VERDICT_STOP_LINEAGE
    if baseline_validator["status"] != "pass" or candidate_validator["status"] != "pass":
        return VERDICT_FAIL_MARK
    if int(baseline_summary["negative_cash_count"]) or int(candidate_summary["negative_cash_count"]):
        return VERDICT_FAIL_MARK
    if int(baseline_summary["duplicate_position_count"]) or int(candidate_summary["duplicate_position_count"]):
        return VERDICT_FAIL_MARK
    candidate_return = fnum(candidate_summary["total_return"])
    baseline_return = fnum(baseline_summary["total_return"])
    candidate_dd = fnum(candidate_summary["max_drawdown"])
    baseline_dd = fnum(baseline_summary["max_drawdown"])
    drawdown_materially_worse = candidate_dd < baseline_dd - 0.05
    if candidate_return > baseline_return and not drawdown_materially_worse:
        return VERDICT_CANDIDATE_OUTPERFORMS
    return VERDICT_CANDIDATE_NOT_OUTPERFORMING


def write_report(
    verdict: str,
    baseline_summary: dict[str, Any],
    candidate_summary: dict[str, Any],
    mark_rows: list[dict[str, Any]],
    validator: dict[str, Any],
) -> None:
    recommend_p4 = verdict == VERDICT_CANDIDATE_OUTPERFORMS
    text = "\n".join(
        [
            "---",
            f"created_at: {now_iso()}",
            f"phase: {PHASE}",
            f"strategy_candidate: {CANDIDATE_RULE}",
            f"baseline_strategy: {BASELINE_RULE}",
            "readonly_only: true",
            "simulation_only: true",
            "production_allowed: false",
            f"verdict: {verdict}",
            "---",
            "",
            "# POLICY_MTRP3_SAME_WINDOW_REPLAY_COMPARISON_EXECUTION_REPORT_CN",
            "",
            "## 1. Verdict",
            "",
            "```text",
            verdict,
            "```",
            "",
            f"是否建议进入 P4 readonly shadow/readiness：`{str(recommend_p4).lower()}`",
            "",
            "本阶段仅执行 same-window readonly replay comparison，未修改 production registry/default/frontend/API/Agent/daily/latest/provider/PriceStore，未执行 broker、quick-trade 或真实交易，未输出生产 ready 结论。",
            "",
            "## 2. 固定输入",
            "",
            f"- signal window: `{WINDOW_START}..{WINDOW_END}`",
            f"- full-rank visibility bridge: `{rel(BRIDGE_MANIFEST)}`",
            f"- candidate OrderIntent: `{rel(CANDIDATE_ORDER_MANIFEST)}`",
            f"- baseline OrderIntent: `{rel(BASELINE_ORDER_DIR / 'manifest.json')}`",
            f"- output root: `{rel(OUT_ROOT)}`",
            "",
            "P2_R lineage warning 保留：bridge 来源是 existing audited broad reference repackaged for production-candidate readiness，不等同 production-ready ModelSignalArtifact。",
            "",
            "## 3. Replay 口径",
            "",
            "```text",
            "initial_equity = 1000000",
            "target_holdings = 10",
            "fee_rate = 0.001425",
            "sell_tax_rate = 0.003",
            "lot_size = 10",
            "execution_price = next_open",
            "execution_date_policy = next_tradeable_day_after_signal_date",
            "cash_policy = no_negative_cash",
            "mark_to_market = close same-day required / fallback audited",
            "```",
            "",
            "价格仅来自 MTRC5 允许的本地已审计 OHLCV 源；未 provider refresh/publish、未 accepted latest switch、未 formal PriceStore write，未使用 self_contained_demo。",
            "",
            "## 4. Baseline vs Candidate",
            "",
            "| metric | baseline | candidate |",
            "| --- | ---: | ---: |",
            f"| final_equity | {baseline_summary['final_equity']} | {candidate_summary['final_equity']} |",
            f"| total_return | {baseline_summary['total_return']} | {candidate_summary['total_return']} |",
            f"| max_drawdown | {baseline_summary['max_drawdown']} | {candidate_summary['max_drawdown']} |",
            f"| actions | {baseline_summary['action_count']} | {candidate_summary['action_count']} |",
            f"| skipped | {baseline_summary['skipped_action_count']} | {candidate_summary['skipped_action_count']} |",
            "",
            "## 5. Mark Coverage",
            "",
            "| strategy | same_day_mark_coverage_ratio | final_date_same_day_mark_coverage_ratio | max_mark_lag_days | status |",
            "| --- | ---: | ---: | ---: | --- |",
            *[
                f"| {row['strategy_rule']} | {row['same_day_mark_coverage_ratio']} | {row['final_date_same_day_mark_coverage_ratio']} | {row['max_mark_lag_days']} | {row['status']} |"
                for row in mark_rows
            ],
            "",
            "## 6. Validator",
            "",
            f"- root validator status: `{validator['status']}`",
            f"- baseline replay validator: `{validator['checks']['baseline_replay_validator_pass']}`",
            f"- candidate replay validator: `{validator['checks']['candidate_replay_validator_pass']}`",
            f"- forbidden scope clean: `{validator['checks']['forbidden_scope_clean']}`",
            "",
            "## 7. Boundary Statement",
            "",
            "本报告不得解读为 production-ready、default switch 或真实交易授权。候选若进入下一步，也只能进入 P4 readonly shadow/readiness 观察，并继续保留 P2_R lineage warning。",
        ]
    )
    write_text(REPORT_PATH, text)


def main() -> None:
    require_inputs()
    bridge_manifest = read_json(BRIDGE_MANIFEST)
    candidate_order_manifest = read_json(CANDIDATE_ORDER_MANIFEST)
    lineage_ok = (
        bridge_manifest.get("source_lineage") == SOURCE_LINEAGE
        and bridge_manifest.get("production_allowed") is False
        and candidate_order_manifest.get("production_allowed") is False
        and candidate_order_manifest.get("can_enter_p3_same_window_baseline_replay") is True
    )

    bridge_rows = read_csv_rows(BRIDGE_SIGNALS)
    baseline_intents, baseline_decision_audit, baseline_stats = build_baseline_order_intent(bridge_rows)
    baseline_oi_validator = validate_order_intents(baseline_intents, baseline_decision_audit, baseline_stats)
    write_baseline_order_intent(baseline_intents, baseline_decision_audit, baseline_stats, baseline_oi_validator)

    candidate_intents = filter_window(read_csv_rows(CANDIDATE_ORDER_INTENTS), "signal_date")

    required_instruments = {
        row["instrument"]
        for row in [*baseline_intents, *candidate_intents]
        if row.get("instrument")
    }
    price_rows, source_audit = load_price_rows(required_instruments)
    _price_by_key, price_by_inst = build_price_maps(price_rows)

    baseline_plan, baseline_exec_audit = build_execution_plan(
        BASELINE_RULE,
        baseline_intents,
        rel(BASELINE_ORDER_DIR / "manifest.json"),
        price_by_inst,
    )
    candidate_plan, candidate_exec_audit = build_execution_plan(
        CANDIDATE_RULE,
        candidate_intents,
        rel(CANDIDATE_ORDER_MANIFEST),
        price_by_inst,
    )

    baseline_result = run_replay(
        BASELINE_RULE,
        baseline_intents,
        baseline_plan,
        rel(BASELINE_ORDER_DIR / "manifest.json"),
        price_by_inst,
    )
    candidate_result = run_replay(
        CANDIDATE_RULE,
        candidate_intents,
        candidate_plan,
        rel(CANDIDATE_ORDER_MANIFEST),
        price_by_inst,
    )

    common_links = {
        "bridge_manifest": rel(BRIDGE_MANIFEST),
        "candidate_order_manifest": rel(CANDIDATE_ORDER_MANIFEST),
        "baseline_order_manifest": rel(BASELINE_ORDER_DIR / "manifest.json"),
        "allowed_price_sources": ALLOWED_PRICE_SOURCES,
        "source_lineage_warning": SOURCE_LINEAGE,
    }
    baseline_artifact = write_replay_artifact(
        BASELINE_REPLAY_DIR,
        BASELINE_RULE,
        baseline_intents,
        baseline_plan,
        baseline_result,
        rel(BASELINE_ORDER_DIR / "manifest.json"),
        common_links,
    )
    candidate_artifact = write_replay_artifact(
        CANDIDATE_REPLAY_DIR,
        CANDIDATE_RULE,
        candidate_intents,
        candidate_plan,
        candidate_result,
        rel(CANDIDATE_ORDER_MANIFEST),
        common_links,
    )

    baseline_summary = baseline_artifact["summary"]
    candidate_summary = candidate_artifact["summary"]
    mark_rows = build_mark_coverage_audit(baseline_result, candidate_result)
    comparison_rows = build_comparison_rows(baseline_summary, candidate_summary)
    forbidden_scope_rows = build_forbidden_scope_audit(source_audit)
    execution_price_rows = baseline_exec_audit + candidate_exec_audit

    write_csv(
        OUT_ROOT / "comparison.csv",
        comparison_rows,
        [
            "metric",
            "baseline_strategy",
            "baseline_value",
            "candidate_strategy",
            "candidate_value",
            "candidate_minus_baseline",
            "preferred_direction",
        ],
    )
    write_csv(
        OUT_ROOT / "mark_coverage_audit.csv",
        mark_rows,
        [
            "strategy_rule",
            "snapshot_count",
            "same_day_mark_coverage_ratio",
            "final_date_same_day_mark_coverage_ratio",
            "fallback_mark_count",
            "final_date_fallback_mark_count",
            "max_mark_lag_days",
            "status",
            "details",
        ],
    )
    write_csv(
        OUT_ROOT / "execution_price_audit.csv",
        execution_price_rows,
        [
            "strategy_rule",
            "signal_date",
            "execution_date",
            "instrument",
            "intent_action",
            "execution_price_policy",
            "execution_date_policy",
            "next_open",
            "source_path",
            "source_kind",
            "source_priority",
            "status",
            "details",
        ],
    )
    write_csv(
        OUT_ROOT / "forbidden_scope_audit.csv",
        forbidden_scope_rows,
        ["scope_item", "performed", "status", "details"],
    )
    write_csv(
        OUT_ROOT / "price_source_inventory.csv",
        source_audit,
        [
            "source_path",
            "source_kind",
            "source_priority",
            "exists",
            "csv_file_count",
            "required_instrument_overlap",
            "required_instrument_count",
            "policy_status",
            "status",
        ],
    )

    baseline_validator = baseline_artifact["validator"]
    candidate_validator = candidate_artifact["validator"]
    verdict = determine_verdict(
        baseline_summary,
        candidate_summary,
        baseline_validator,
        candidate_validator,
        mark_rows,
        lineage_ok,
    )
    root_checks = {
        "baseline_order_intent_validator_pass": baseline_oi_validator["status"] == "pass",
        "baseline_replay_validator_pass": baseline_validator["status"] == "pass",
        "candidate_replay_validator_pass": candidate_validator["status"] == "pass",
        "same_window_signal_dates": True,
        "same_execution_config": True,
        "same_price_source_policy": True,
        "lineage_warning_preserved": lineage_ok,
        "mark_quality_gate_pass": all(row["status"] == "pass" for row in mark_rows),
        "execution_price_gate_pass": all(row["status"] == "pass" for row in execution_price_rows),
        "forbidden_scope_clean": all(row["status"] == "pass" and row["performed"] == "false" for row in forbidden_scope_rows),
    }
    validator = {
        "schema_version": "mtrp3_same_window_replay_comparison_validator_v1",
        "created_at": now_iso(),
        "phase": PHASE,
        "verdict": verdict,
        "status": "pass" if all(root_checks.values()) and verdict not in {VERDICT_FAIL_MARK, VERDICT_STOP_LINEAGE} else "fail",
        "checks": root_checks,
        "baseline_summary": baseline_summary,
        "candidate_summary": candidate_summary,
        "mark_coverage": mark_rows,
        "p2_r_lineage_warning": SOURCE_LINEAGE,
    }
    write_json(OUT_ROOT / "validator_report.json", validator)

    write_text(
        OUT_ROOT / "diagnostic_findings.md",
        "\n".join(
            [
                "# MTRP3 same-window replay comparison findings",
                "",
                f"- verdict: `{verdict}`",
                f"- baseline final_equity: `{baseline_summary['final_equity']}`",
                f"- candidate final_equity: `{candidate_summary['final_equity']}`",
                f"- baseline total_return: `{baseline_summary['total_return']}`",
                f"- candidate total_return: `{candidate_summary['total_return']}`",
                f"- baseline max_drawdown: `{baseline_summary['max_drawdown']}`",
                f"- candidate max_drawdown: `{candidate_summary['max_drawdown']}`",
                f"- baseline actions/skipped: `{baseline_summary['action_count']}` / `{baseline_summary['skipped_action_count']}`",
                f"- candidate actions/skipped: `{candidate_summary['action_count']}` / `{candidate_summary['skipped_action_count']}`",
                f"- mark quality gate pass: `{root_checks['mark_quality_gate_pass']}`",
                "",
                "P2_R lineage warning is preserved. This artifact is readonly/simulation-only and is not production-ready.",
            ]
        ),
    )

    write_json(
        OUT_ROOT / "manifest.json",
        {
            "artifact_type": "mtrp3_same_window_replay_comparison",
            "schema_version": "mtrp3_same_window_replay_comparison_v1",
            "phase": PHASE,
            "run_id": RUN_ID,
            "created_at": now_iso(),
            "created_by": rel(Path(__file__)),
            "verdict": verdict,
            "window": {"start": WINDOW_START, "end": WINDOW_END},
            "baseline_strategy": BASELINE_RULE,
            "candidate_strategy": CANDIDATE_RULE,
            "execution_config": EXECUTION_CONFIG,
            "bridge_manifest": rel(BRIDGE_MANIFEST),
            "candidate_order_intent_manifest": rel(CANDIDATE_ORDER_MANIFEST),
            "baseline_order_intent_manifest": rel(BASELINE_ORDER_DIR / "manifest.json"),
            "p2_r_lineage_warning": SOURCE_LINEAGE,
            "readonly_only": True,
            "simulation_only": True,
            "production_allowed": False,
            "not_default_switch": True,
            "not_published_latest": True,
            "production_ready": False,
            "baseline_summary": baseline_summary,
            "candidate_summary": candidate_summary,
            "validator_status": validator["status"],
            "input_hashes": {
                rel(BRIDGE_MANIFEST): sha256_file(BRIDGE_MANIFEST),
                rel(BRIDGE_SIGNALS): sha256_file(BRIDGE_SIGNALS),
                rel(CANDIDATE_ORDER_MANIFEST): sha256_file(CANDIDATE_ORDER_MANIFEST),
                rel(CANDIDATE_ORDER_INTENTS): sha256_file(CANDIDATE_ORDER_INTENTS),
                rel(BASELINE_DEPENDENCY): sha256_file(BASELINE_DEPENDENCY),
                rel(CANDIDATE_DEPENDENCY): sha256_file(CANDIDATE_DEPENDENCY),
            },
            "output_files": {
                "baseline_order_intent": rel(BASELINE_ORDER_DIR),
                "candidate_replay": rel(CANDIDATE_REPLAY_DIR),
                "baseline_replay": rel(BASELINE_REPLAY_DIR),
                "comparison": rel(OUT_ROOT / "comparison.csv"),
                "mark_coverage_audit": rel(OUT_ROOT / "mark_coverage_audit.csv"),
                "execution_price_audit": rel(OUT_ROOT / "execution_price_audit.csv"),
                "forbidden_scope_audit": rel(OUT_ROOT / "forbidden_scope_audit.csv"),
                "validator_report": rel(OUT_ROOT / "validator_report.json"),
                "diagnostic_findings": rel(OUT_ROOT / "diagnostic_findings.md"),
                "execution_report": rel(REPORT_PATH),
            },
        },
    )
    write_report(verdict, baseline_summary, candidate_summary, mark_rows, validator)
    print(
        json.dumps(
            {
                "verdict": verdict,
                "baseline": baseline_summary,
                "candidate": candidate_summary,
                "out_dir": rel(OUT_ROOT),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
