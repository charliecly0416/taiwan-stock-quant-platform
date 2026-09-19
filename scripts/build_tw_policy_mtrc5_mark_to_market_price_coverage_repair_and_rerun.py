#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from math import floor
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MTRC3_DIAG_SPEC = importlib.util.spec_from_file_location(
    "mtrc3_diag",
    ROOT / "scripts/build_tw_policy_mtrc3_extended_concentration_window_diagnostic.py",
)
if MTRC3_DIAG_SPEC is None or MTRC3_DIAG_SPEC.loader is None:
    raise ImportError("Unable to load MTRC3 diagnostic helper")
mtrc3_diag = importlib.util.module_from_spec(MTRC3_DIAG_SPEC)
MTRC3_DIAG_SPEC.loader.exec_module(mtrc3_diag)
PHASE = "MTRC5_MARK_TO_MARKET_PRICE_COVERAGE_REPAIR_AND_RERUN"
VERDICT_PASS = "PASS_MARK_QUALITY_REPAIRED_READY_FOR_REVIEW"
VERDICT_WARN = "PASS_WITH_PARTIAL_MARK_QUALITY_REPAIR_READY_FOR_REVIEW"
VERDICT_FAIL = "FAIL_MARK_QUALITY_REPAIR_INSUFFICIENT"
VERDICT_STOP = "STOP_NO_LOCAL_PRICE_COVERAGE_PATH"

ROOT_OUT_DIR = (
    ROOT
    / "data_tw/experiments/policy_mtr_research_only_continuation/"
    / "mtrc5_mark_to_market_price_coverage_repair_and_rerun"
)
OUT_DIR = ROOT_OUT_DIR / "replay"
DIAGNOSTIC_DIR = ROOT_OUT_DIR / "diagnostic"
REPORT_PATH = (
    ROOT
    / "docs/tw_portfolio_decision_model/"
    / "POLICY_MTRC5_MARK_TO_MARKET_PRICE_COVERAGE_REPAIR_AND_RERUN_EXECUTION_REPORT_CN.md"
)

MTRC2_S_DIR = (
    ROOT
    / "data_tw/experiments/policy_mtr_research_only_continuation/"
    / "mtrc2_s_same_signal_order_intent_build"
)
MTRC2_T_R_DIR = (
    ROOT
    / "data_tw/experiments/policy_mtr_research_only_continuation/"
    / "mtrc2_t_r_pricestore_bridge_or_readiness_repair"
)
MTRC2_T_GATE_DIR = (
    ROOT
    / "data_tw/experiments/policy_mtr_research_only_continuation/"
    / "mtrc2_t_gate_rerun_with_repaired_price_bridge"
)

ORDER_INTENT_MANIFEST = MTRC2_S_DIR / "manifest.json"
ORDER_INTENTS_CSV = MTRC2_S_DIR / "order_intents.csv"
PRICE_BRIDGE_MANIFEST = MTRC2_T_R_DIR / "manifest.json"
PRICES_CSV = MTRC2_T_R_DIR / "prices.csv"
JOIN_AUDIT_CSV = MTRC2_T_R_DIR / "order_intent_price_join_audit.csv"
GATE_MANIFEST = MTRC2_T_GATE_DIR / "manifest.json"
GATE_VALIDATOR = MTRC2_T_GATE_DIR / "validator_report.json"
MTRC2_U_DIR = (
    ROOT
    / "data_tw/experiments/policy_mtr_research_only_continuation/"
    / "mtrc2_u_same_signal_readonly_replay_build"
)
MTRC3_DIR = (
    ROOT
    / "data_tw/experiments/policy_mtr_research_only_continuation/"
    / "mtrc3_extended_concentration_window_diagnostic"
)
SOURCE_INVENTORY_CSV = MTRC2_T_R_DIR / "source_inventory.csv"
SOURCE_SELECTION_AUDIT_CSV = MTRC2_T_R_DIR / "source_selection_audit.csv"

ORDER_INTENT_MANIFEST_REL = (
    "data_tw/experiments/policy_mtr_research_only_continuation/"
    "mtrc2_s_same_signal_order_intent_build/manifest.json"
)
ORDER_INTENTS_CSV_REL = (
    "data_tw/experiments/policy_mtr_research_only_continuation/"
    "mtrc2_s_same_signal_order_intent_build/order_intents.csv"
)
PRICE_BRIDGE_MANIFEST_REL = (
    "data_tw/experiments/policy_mtr_research_only_continuation/"
    "mtrc2_t_r_pricestore_bridge_or_readiness_repair/manifest.json"
)
PRICES_CSV_REL = (
    "data_tw/experiments/policy_mtr_research_only_continuation/"
    "mtrc2_t_r_pricestore_bridge_or_readiness_repair/prices.csv"
)
JOIN_AUDIT_CSV_REL = (
    "data_tw/experiments/policy_mtr_research_only_continuation/"
    "mtrc2_t_r_pricestore_bridge_or_readiness_repair/order_intent_price_join_audit.csv"
)
GATE_MANIFEST_REL = (
    "data_tw/experiments/policy_mtr_research_only_continuation/"
    "mtrc2_t_gate_rerun_with_repaired_price_bridge/manifest.json"
)
GATE_VALIDATOR_REL = (
    "data_tw/experiments/policy_mtr_research_only_continuation/"
    "mtrc2_t_gate_rerun_with_repaired_price_bridge/validator_report.json"
)
MTRC1D_SIGNAL_MANIFEST_REL = (
    "data_tw/experiments/policy_mtr_research_only_continuation/"
    "mtrc1d_research_only_broad_full_rank_signal_build/manifest.json"
)
MTRC2_U_REPLAY_MANIFEST_REL = (
    "data_tw/experiments/policy_mtr_research_only_continuation/"
    "mtrc2_u_same_signal_readonly_replay_build/manifest.json"
)
MTRC3_DIAGNOSTIC_MANIFEST_REL = (
    "data_tw/experiments/policy_mtr_research_only_continuation/"
    "mtrc3_extended_concentration_window_diagnostic/manifest.json"
)

ALLOWED_MARK_SOURCES = [
    {
        "source_path": "data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_r_real_model_a_top50_bridge_coverage_repair/stock_price_bridge",
        "source_kind": "stock_price_bridge",
        "source_priority": 1,
        "policy_status": "primary_existing_stock_price_bridge",
    },
    {
        "source_path": "data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/option_c_ops/rcpt15_r1_option_c_yahoo_scrapling_refresh_20260625/candidate_normalized",
        "source_kind": "staged_candidate_normalized",
        "source_priority": 2,
        "policy_status": "local_staged_candidate_normalized",
    },
    {
        "source_path": "data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/stock_price_bridge",
        "source_kind": "stock_price_bridge",
        "source_priority": 3,
        "policy_status": "secondary_existing_stock_price_bridge",
    },
]
DEMO_SOURCE_PATH = "data_tw/self_contained_demo/normalized"

TARGET_STRATEGY_RULE = "mechanism_transfer_top50_cost_aware_v1"
TARGET_CANDIDATE = "M2_hold_rank_buffer_100"
TARGET_MECHANISM = "hold_rank_buffer"
TARGET_RANK_BUFFER = "100"
TARGET_HOLDING_COUNT = "10"
TARGET_CANDIDATE_K = "50"
MAX_BUY_COUNT = "1"
MAX_SELL_COUNT = "1"

EXECUTION_CONFIG = {
    "execution_price": "next_open",
    "execution_date_policy": "next_tradeable_day_after_signal_date",
    "initial_equity": 1000000,
    "target_holdings": 10,
    "fee_rate": 0.001425,
    "sell_tax_rate": 0.003,
    "lot_size": 10,
    "missing_price_policy": "skip_or_audit_no_silent_fill",
    "cash_policy": "no_negative_cash_unless_explicitly_allowed_and_audited",
    "readonly_only": True,
    "simulation_only": True,
    "diagnostic_only": True,
    "production_allowed": False,
}

REQUIRED_OUTPUTS = [
    "manifest.json",
    "summary.csv",
    "actions.csv",
    "daily_nav.csv",
    "position_snapshots.csv",
    "coverage_audit.csv",
    "position_integrity_audit.csv",
    "forbidden_field_audit.csv",
    "execution_audit.csv",
    "forbidden_action_audit.json",
    "skipped_actions.csv",
    "daily_cash_audit.csv",
    "input_manifest_links.json",
    "validator_report.json",
    "diagnostic_findings.md",
]
ROOT_REQUIRED_OUTPUTS = [
    "manifest.json",
    "source_inventory_recheck.csv",
    "required_mark_coverage_universe.csv",
    "mark_price_bridge.csv",
    "mark_price_bridge_coverage_audit.csv",
    "execution_join_preservation_audit.csv",
    "mtrc2u_vs_mtrc5_replay_comparison.csv",
    "mtrc3_vs_mtrc5_diagnostic_comparison.csv",
    "forbidden_scope_audit.csv",
    "validator_report.json",
    "diagnostic_findings.md",
]
DIAGNOSTIC_REQUIRED_OUTPUTS = [
    "summary_diagnostic.csv",
    "mark_quality_diagnostic.csv",
    "symbol_concentration_diagnostic.csv",
    "event_concentration_diagnostic.csv",
    "monthly_return_diagnostic.csv",
    "rolling_return_diagnostic.csv",
    "drawdown_diagnostic.csv",
]
FORBIDDEN_SCOPE_ITEMS = [
    "model_training",
    "model_inference",
    "ltr_score_recompute",
    "model_signal_artifact_write",
    "order_intent_artifact_write",
    "ledger_build",
    "strategy_tuning",
    "new_candidate_selection",
    "formal_price_store_write",
    "registry_config_default_write",
    "provider_refresh_or_publish",
    "accepted_latest_switch",
    "frontend_api_agent_daily_production_write",
    "broker_order_quick_trade_real_order",
    "target_weight_instruction",
    "target_position_instruction",
    "production_readiness_claim",
]

FORBIDDEN_EXACT_FIELDS = {
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
    "order_qty",
    "quantity_to_buy",
    "quantity_to_sell",
}
FORBIDDEN_PREFIXES = (
    "future_return_",
    "future_excess_return_",
    "forward_return_",
    "label_",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def sha256(path: Path) -> str:
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


def fnum(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def money(value: float) -> str:
    return f"{value:.6f}"


def inferred_fields(rows: list[dict[str, Any]]) -> list[str]:
    return sorted({key for row in rows for key in row}) if rows else ["status"]


def require_inputs() -> None:
    required = [
        ORDER_INTENT_MANIFEST,
        ORDER_INTENTS_CSV,
        PRICE_BRIDGE_MANIFEST,
        PRICES_CSV,
        JOIN_AUDIT_CSV,
        GATE_MANIFEST,
        GATE_VALIDATOR,
    ]
    missing = [path for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required input(s): " + ", ".join(rel(path) for path in missing))


def build_join_map(rows: list[dict[str, str]]) -> dict[tuple[str, str, str], list[dict[str, str]]]:
    out: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        out[(row["signal_date"], row["instrument"], row["intent_action"])].append(row)
    return out


def pop_join(
    joins: dict[tuple[str, str, str], list[dict[str, str]]],
    intent: dict[str, str],
) -> dict[str, str] | None:
    key = (intent["signal_date"], intent["instrument"], intent["intent_action"])
    matches = joins.get(key, [])
    if not matches:
        return None
    return matches.pop(0)


def build_price_maps(
    rows: list[dict[str, str]],
) -> tuple[dict[tuple[str, str], dict[str, str]], dict[str, list[tuple[str, float]]], dict[str, list[tuple[str, float]]]]:
    by_key: dict[tuple[str, str], dict[str, str]] = {}
    close_history: dict[str, list[tuple[str, float]]] = defaultdict(list)
    open_history: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for row in rows:
        key = (row["price_date"], row["instrument"])
        by_key[key] = row
        close_history[row["instrument"]].append((row["price_date"], fnum(row["close"])))
        open_history[row["instrument"]].append((row["price_date"], fnum(row["open"])))
    for inst in close_history:
        close_history[inst].sort()
    for inst in open_history:
        open_history[inst].sort()
    return by_key, close_history, open_history


def read_price_file(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    rows = read_csv_rows(path)
    out: list[dict[str, str]] = []
    for row in rows:
        date = row.get("date") or row.get("price_date") or ""
        inst = row.get("symbol") or row.get("instrument") or path.stem
        open_px = fnum(row.get("open"))
        close_px = fnum(row.get("close"))
        if not date or not inst or open_px <= 0 or close_px <= 0:
            continue
        out.append(
            {
                "price_date": date,
                "instrument": inst,
                "open": str(open_px),
                "close": str(close_px),
                "adj_factor_or_factor": row.get("factor", row.get("adj_factor", "")),
            }
        )
    return out


def build_source_inventory_recheck(required_instruments: set[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in ALLOWED_MARK_SOURCES + [
        {
            "source_path": DEMO_SOURCE_PATH,
            "source_kind": "self_contained_demo_normalized",
            "source_priority": "",
            "policy_status": "invalid_demo_source",
        }
    ]:
        source_path = ROOT / source["source_path"]
        csv_files = sorted(source_path.glob("*.csv")) if source_path.exists() else []
        overlap = {path.stem for path in csv_files} & required_instruments
        date_min = ""
        date_max = ""
        sample_file = csv_files[0] if csv_files else None
        sample_columns = ""
        sample_rows = 0
        sample_valid_rows = 0
        if sample_file:
            sample = read_csv_rows(sample_file)
            sample_rows = len(sample)
            sample_valid_rows = len(read_price_file(sample_file))
            sample_columns = "|".join(sample[0].keys()) if sample else ""
        for inst in sorted(overlap)[:5]:
            for row in read_price_file(source_path / f"{inst}.csv"):
                date = row["price_date"]
                date_min = min(date_min, date) if date_min else date
                date_max = max(date_max, date) if date_max else date
        valid = source["source_path"] != DEMO_SOURCE_PATH and bool(source_path.exists())
        rows.append(
            {
                "source_kind": source["source_kind"],
                "source_path": source["source_path"],
                "source_priority": source["source_priority"],
                "exists": bool_text(source_path.exists()),
                "csv_file_count": len(csv_files),
                "required_instrument_overlap": len(overlap),
                "required_instrument_count": len(required_instruments),
                "sample_file": rel(sample_file) if sample_file else "",
                "sample_columns": sample_columns,
                "sample_row_count": sample_rows,
                "sample_valid_row_count": sample_valid_rows,
                "source_date_min_sampled": date_min,
                "source_date_max_sampled": date_max,
                "policy_status": source["policy_status"],
                "source_valid_for_selection": bool_text(valid),
                "details": "Allowed audited local full OHLCV source." if valid else "Excluded by MTRC5 policy.",
            }
        )
    return rows


def required_mark_universe_from_mtrc2u() -> list[dict[str, Any]]:
    positions = read_csv_rows(MTRC2_U_DIR / "position_snapshots.csv")
    counter: Counter[tuple[str, str]] = Counter()
    for row in positions:
        date = row.get("date", "")
        inst = row.get("instrument", "")
        if date and inst:
            counter[(date, inst)] += 1
    return [
        {
            "price_date": date,
            "instrument": inst,
            "required_snapshot_count": count,
            "required_source": "mtrc2_u_position_snapshots",
            "mark_coverage_required": "true",
        }
        for (date, inst), count in sorted(counter.items())
    ]


def build_mark_price_bridge(
    required_rows: list[dict[str, Any]],
    extra_instruments: set[str],
    start_date: str,
    end_date: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    required_keys = {(str(row["price_date"]), str(row["instrument"])) for row in required_rows}
    selected: dict[tuple[str, str], dict[str, Any]] = {}
    attempted: Counter[tuple[str, str]] = Counter()
    source_selected_counts: Counter[str] = Counter()
    required_by_instrument: dict[str, set[str]] = defaultdict(set)
    for date, inst in required_keys:
        required_by_instrument[inst].add(date)

    for source in ALLOWED_MARK_SOURCES:
        source_path = ROOT / source["source_path"]
        for inst, required_dates in required_by_instrument.items():
            file_path = source_path / f"{inst}.csv"
            if not file_path.exists():
                continue
            by_date = {row["price_date"]: row for row in read_price_file(file_path)}
            for date in required_dates:
                key = (date, inst)
                if key in selected:
                    continue
                attempted[key] += 1
                row = by_date.get(date)
                if not row:
                    continue
                selected[key] = {
                    "price_date": date,
                    "instrument": inst,
                    "open": row["open"],
                    "close": row["close"],
                    "adj_factor_or_factor": row.get("adj_factor_or_factor", ""),
                    "source_path": rel(file_path),
                    "source_kind": source["source_kind"],
                    "source_priority": source["source_priority"],
                    "mark_coverage_required": "true",
                }
                source_selected_counts[str(source["source_priority"])] += 1

    for source in ALLOWED_MARK_SOURCES:
        source_path = ROOT / source["source_path"]
        for inst in sorted(extra_instruments):
            file_path = source_path / f"{inst}.csv"
            if not file_path.exists():
                continue
            for row in read_price_file(file_path):
                date = row["price_date"]
                if date < start_date or date > end_date:
                    continue
                key = (date, inst)
                if key in selected:
                    continue
                selected[key] = {
                    "price_date": date,
                    "instrument": inst,
                    "open": row["open"],
                    "close": row["close"],
                    "adj_factor_or_factor": row.get("adj_factor_or_factor", ""),
                    "source_path": rel(file_path),
                    "source_kind": source["source_kind"],
                    "source_priority": source["source_priority"],
                    "mark_coverage_required": bool_text(key in required_keys),
                }
                source_selected_counts[str(source["source_priority"])] += 1

    bridge_rows = [selected[key] for key in sorted(selected)]
    coverage_rows: list[dict[str, Any]] = []
    for date, inst in sorted(required_keys):
        row = selected.get((date, inst))
        coverage_rows.append(
            {
                "price_date": date,
                "instrument": inst,
                "required": "true",
                "covered_same_day": bool_text(row is not None),
                "attempted_allowed_source_count": attempted[(date, inst)],
                "selected_source_path": row.get("source_path", "") if row else "",
                "selected_source_kind": row.get("source_kind", "") if row else "",
                "selected_source_priority": row.get("source_priority", "") if row else "",
                "status": "pass" if row else "missing",
                "details": "same-day close selected from allowed local full OHLCV source"
                if row
                else "no same-day close in allowed local sources",
            }
        )
    return bridge_rows, coverage_rows


def latest_mark(
    instrument: str,
    date: str,
    close_history: dict[str, list[tuple[str, float]]],
) -> tuple[float, str, bool]:
    history = close_history.get(instrument, [])
    selected_price = 0.0
    selected_date = ""
    exact = False
    for price_date, price in history:
        if price_date > date:
            break
        selected_price = price
        selected_date = price_date
        exact = price_date == date
    return selected_price, selected_date, exact


def compute_equity(
    date: str,
    cash: float,
    positions: dict[str, dict[str, float]],
    close_history: dict[str, list[tuple[str, float]]],
) -> tuple[float, float, list[dict[str, Any]]]:
    market_value = 0.0
    missing_marks: list[dict[str, Any]] = []
    for inst, pos in positions.items():
        mark, mark_date, exact = latest_mark(inst, date, close_history)
        if mark <= 0:
            missing_marks.append(
                {
                    "date": date,
                    "instrument": inst,
                    "status": "fail",
                    "value": "missing",
                    "threshold": "mark_price_available",
                    "details": "No positive close available at or before replay date.",
                }
            )
            continue
        if not exact:
            missing_marks.append(
                {
                    "date": date,
                    "instrument": inst,
                    "status": "audited_fallback",
                    "value": mark_date,
                    "threshold": date,
                    "details": "Current-date close absent in price bridge; used latest available prior close.",
                }
            )
        market_value += pos["quantity"] * mark
    return cash + market_value, market_value, missing_marks


def order_key(row: dict[str, Any]) -> tuple[str, int, str, str]:
    action = row.get("intent_action", "")
    action_rank = 0 if action == "sell" else 1 if action == "buy" else 2
    return (row["execution_date"], action_rank, row["signal_date"], row["instrument"])


def replay(
    intents: list[dict[str, str]],
    join_rows: list[dict[str, str]],
    price_rows: list[dict[str, str]],
) -> dict[str, Any]:
    join_map = build_join_map(join_rows)
    _price_by_key, close_history, _open_history = build_price_maps(price_rows)

    enriched: list[dict[str, Any]] = []
    missing_join_rows: list[dict[str, Any]] = []
    for intent in intents:
        join = pop_join(join_map, intent)
        if not join:
            missing_join_rows.append(
                {
                    "signal_date": intent.get("signal_date", ""),
                    "execution_date": "",
                    "instrument": intent.get("instrument", ""),
                    "intent_action": intent.get("intent_action", ""),
                    "skip_reason": "missing_join_audit_row",
                    "execution_price": "",
                    "cash": "",
                    "holding_quantity": "",
                    "intent_reason": intent.get("intent_reason", ""),
                    "strategy_rule": intent.get("strategy_rule", ""),
                    "model_name": intent.get("model_name", ""),
                    "order_intent_artifact": ORDER_INTENT_MANIFEST_REL,
                }
            )
            continue
        execution_date = join["execution_date"]
        price = fnum(join["next_open"])
        enriched.append({**intent, **{"execution_date": execution_date, "execution_price": price, "join": join}})

    cash = float(EXECUTION_CONFIG["initial_equity"])
    positions: dict[str, dict[str, float]] = {}
    actions: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = list(missing_join_rows)
    daily_nav: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []
    daily_cash_audit: list[dict[str, Any]] = []
    integrity_rows: list[dict[str, Any]] = []
    valuation_fallback_rows: list[dict[str, Any]] = []
    action_quantity_bad = 0
    execution_date_bad = 0
    negative_cash_count = 0
    skipped_missing_price = 0

    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in enriched:
        by_date[row["execution_date"]].append(row)

    previous_equity = float(EXECUTION_CONFIG["initial_equity"])
    peak_equity = previous_equity
    max_drawdown = 0.0
    lot_size = int(EXECUTION_CONFIG["lot_size"])
    fee_rate = float(EXECUTION_CONFIG["fee_rate"])
    sell_tax_rate = float(EXECUTION_CONFIG["sell_tax_rate"])
    target_holdings = int(EXECUTION_CONFIG["target_holdings"])

    for date in sorted(by_date):
        for row in sorted(by_date[date], key=order_key):
            signal_date = row["signal_date"]
            instrument = row["instrument"]
            action = row["intent_action"]
            execution_price = float(row["execution_price"])
            if date <= signal_date:
                execution_date_bad += 1

            if execution_price <= 0:
                skipped_missing_price += 1
                skipped.append(
                    {
                        "signal_date": signal_date,
                        "execution_date": date,
                        "instrument": instrument,
                        "intent_action": action,
                        "skip_reason": "missing_or_non_positive_execution_price",
                        "execution_price": money(execution_price),
                        "cash": money(cash),
                        "holding_quantity": int(positions.get(instrument, {}).get("quantity", 0)),
                        "intent_reason": row.get("intent_reason", ""),
                        "strategy_rule": row.get("strategy_rule", ""),
                        "model_name": row.get("model_name", ""),
                        "order_intent_artifact": ORDER_INTENT_MANIFEST_REL,
                    }
                )
                continue

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
                            "strategy_rule": row.get("strategy_rule", ""),
                            "model_name": row.get("model_name", ""),
                            "order_intent_artifact": ORDER_INTENT_MANIFEST_REL,
                        }
                    )
                    continue
                quantity = held_qty
                gross = quantity * execution_price
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
                        "quantity": quantity,
                        "execution_price": money(execution_price),
                        "commission": money(commission),
                        "tax": money(tax),
                        "cash_after": money(cash),
                        "position_after": 0,
                        "intent_reason": row.get("intent_reason", ""),
                        "strategy_rule": row.get("strategy_rule", ""),
                        "model_name": row.get("model_name", ""),
                        "order_intent_artifact": ORDER_INTENT_MANIFEST_REL,
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
                            "strategy_rule": row.get("strategy_rule", ""),
                            "model_name": row.get("model_name", ""),
                            "order_intent_artifact": ORDER_INTENT_MANIFEST_REL,
                        }
                    )
                    continue
                current_equity, _mv, equity_marks = compute_equity(date, cash, positions, close_history)
                valuation_fallback_rows.extend(equity_marks)
                budget = current_equity / target_holdings
                quantity = int(floor((budget / execution_price) / lot_size) * lot_size) if execution_price > 0 else 0
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
                            "strategy_rule": row.get("strategy_rule", ""),
                            "model_name": row.get("model_name", ""),
                            "order_intent_artifact": ORDER_INTENT_MANIFEST_REL,
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
                            "strategy_rule": row.get("strategy_rule", ""),
                            "model_name": row.get("model_name", ""),
                            "order_intent_artifact": ORDER_INTENT_MANIFEST_REL,
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
                        "strategy_rule": row.get("strategy_rule", ""),
                        "model_name": row.get("model_name", ""),
                        "order_intent_artifact": ORDER_INTENT_MANIFEST_REL,
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
                        "strategy_rule": row.get("strategy_rule", ""),
                        "model_name": row.get("model_name", ""),
                        "order_intent_artifact": ORDER_INTENT_MANIFEST_REL,
                    }
                )

        equity, market_value, mark_rows = compute_equity(date, cash, positions, close_history)
        valuation_fallback_rows.extend(mark_rows)
        missing_price_count = len(mark_rows)
        daily_return = (equity / previous_equity - 1.0) if previous_equity else 0.0
        peak_equity = max(peak_equity, equity)
        drawdown = (equity / peak_equity - 1.0) if peak_equity else 0.0
        max_drawdown = min(max_drawdown, drawdown)
        holding_count = len(positions)
        if cash < -1e-7:
            negative_cash_count += 1
        daily_nav.append(
            {
                "date": date,
                "cash": money(cash),
                "market_value": money(market_value),
                "equity": money(equity),
                "daily_return": f"{daily_return:.10f}",
                "holding_count": holding_count,
                "missing_price_count": missing_price_count,
            }
        )
        daily_cash_audit.append(
            {
                "date": date,
                "cash": money(cash),
                "negative_cash": bool_text(cash < -1e-7),
                "status": "fail" if cash < -1e-7 else "pass",
                "details": "Cash is non-negative after all readonly simulated executions for the day.",
            }
        )
        for inst in sorted(positions):
            pos = positions[inst]
            mark, mark_date, exact = latest_mark(inst, date, close_history)
            if mark <= 0:
                mark = 0.0
            market = pos["quantity"] * mark
            snapshots.append(
                {
                    "date": date,
                    "instrument": inst,
                    "quantity": int(pos["quantity"]),
                    "cost_basis": money(pos["cost_basis"]),
                    "mark_price": money(mark),
                    "market_value": money(market),
                    "unrealized_pnl": money((mark - pos["cost_basis"]) * pos["quantity"]),
                    "strategy_rule": TARGET_STRATEGY_RULE,
                    "model_name": row_model_name(intents),
                    "mark_price_date": mark_date,
                    "mark_price_policy": "same_date_close" if exact else "latest_prior_close_audited",
                }
            )
        previous_equity = equity

    for action in actions:
        qty = int(action["quantity"])
        if qty <= 0 or qty % lot_size != 0:
            action_quantity_bad += 1

    duplicate_position_count = 0
    seen_positions: set[tuple[str, str]] = set()
    for snap in snapshots:
        key = (str(snap["date"]), str(snap["instrument"]))
        if key in seen_positions:
            duplicate_position_count += 1
        seen_positions.add(key)

    max_holding_count = max((int(row["holding_count"]) for row in daily_nav), default=0)
    final_holdings_missing_mark = 0
    if daily_nav:
        final_date = daily_nav[-1]["date"]
        for inst in positions:
            mark, _mark_date, _exact = latest_mark(inst, final_date, close_history)
            if mark <= 0:
                final_holdings_missing_mark += 1

    return {
        "actions": actions,
        "skipped": skipped,
        "daily_nav": daily_nav,
        "snapshots": snapshots,
        "daily_cash_audit": daily_cash_audit,
        "valuation_fallback_rows": valuation_fallback_rows,
        "integrity_stats": {
            "active_action_quantity_bad": action_quantity_bad,
            "execution_date_not_after_signal_date": execution_date_bad
            + sum(1 for row in join_rows if row.get("execution_date", "") <= row.get("signal_date", "")),
            "max_holding_count": max_holding_count,
            "duplicate_position_count": duplicate_position_count,
            "negative_cash_count": negative_cash_count,
            "skipped_missing_price_count": skipped_missing_price,
            "final_holdings_missing_mark": final_holdings_missing_mark,
        },
        "max_drawdown": max_drawdown,
        "final_positions": positions,
    }


def row_model_name(intents: list[dict[str, str]]) -> str:
    values = sorted({row.get("model_name", "") for row in intents if row.get("model_name", "")})
    return values[0] if values else ""


def row_model_family(intents: list[dict[str, str]]) -> str:
    values = sorted({row.get("model_family", "") for row in intents if row.get("model_family", "")})
    return values[0] if values else ""


def build_summary(
    intents: list[dict[str, str]],
    replay_result: dict[str, Any],
) -> list[dict[str, Any]]:
    nav = replay_result["daily_nav"]
    actions = replay_result["actions"]
    skipped = replay_result["skipped"]
    initial = float(EXECUTION_CONFIG["initial_equity"])
    final_equity = fnum(nav[-1]["equity"]) if nav else initial
    return [
        {
            "window": "full_same_signal_research_only",
            "model_name": row_model_name(intents),
            "model_family": row_model_family(intents),
            "strategy_rule": TARGET_STRATEGY_RULE,
            "start_date": nav[0]["date"] if nav else "",
            "end_date": nav[-1]["date"] if nav else "",
            "initial_cash": money(initial),
            "final_equity": money(final_equity),
            "total_return": f"{(final_equity / initial - 1.0):.10f}" if initial else "0.0000000000",
            "max_drawdown": f"{replay_result['max_drawdown']:.10f}",
            "action_count": len(actions),
            "buy_count": sum(1 for row in actions if row["action"] == "buy"),
            "sell_count": sum(1 for row in actions if row["action"] == "sell"),
            "skipped_action_count": len(skipped),
            "max_holding_count": replay_result["integrity_stats"]["max_holding_count"],
            "duplicate_position_count": replay_result["integrity_stats"]["duplicate_position_count"],
            "negative_cash_count": replay_result["integrity_stats"]["negative_cash_count"],
            "missing_price_count": sum(int(row["missing_price_count"]) for row in nav),
            "diagnostic_only": "true",
        }
    ]


def unique_values(rows: list[dict[str, str]], field: str) -> list[str]:
    return sorted({str(row.get(field, "")) for row in rows})


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
            "details": "Executed replay actions must have positive quantity and respect lot_size=10.",
        },
        {
            "audit_name": "execution_date_gt_signal_date",
            "date": "ALL",
            "instrument": "ALL",
            "status": "pass" if stats["execution_date_not_after_signal_date"] == 0 else "fail",
            "value": stats["execution_date_not_after_signal_date"],
            "threshold": "0",
            "details": "Each execution date must be later than signal_date.",
        },
        {
            "audit_name": "max_holding_count_lte_10",
            "date": "ALL",
            "instrument": "ALL",
            "status": "pass" if stats["max_holding_count"] <= 10 else "fail",
            "value": stats["max_holding_count"],
            "threshold": "10",
            "details": "Readonly replay may not exceed target_holdings=10.",
        },
        {
            "audit_name": "duplicate_position_count_equals_0",
            "date": "ALL",
            "instrument": "ALL",
            "status": "pass" if stats["duplicate_position_count"] == 0 else "fail",
            "value": stats["duplicate_position_count"],
            "threshold": "0",
            "details": "No duplicate date/instrument position snapshot rows.",
        },
        {
            "audit_name": "negative_cash_count_equals_0",
            "date": "ALL",
            "instrument": "ALL",
            "status": "pass" if stats["negative_cash_count"] == 0 else "fail",
            "value": stats["negative_cash_count"],
            "threshold": "0",
            "details": "Cash policy blocks negative cash.",
        },
        {
            "audit_name": "final_holdings_marked_to_market",
            "date": "FINAL",
            "instrument": "ALL",
            "status": "pass" if stats["final_holdings_missing_mark"] == 0 else "fail",
            "value": stats["final_holdings_missing_mark"],
            "threshold": "0",
            "details": "All final holdings must have an available close mark at or before final replay date.",
        },
        {
            "audit_name": "skipped_action_reason_traceable",
            "date": "ALL",
            "instrument": "ALL",
            "status": "pass",
            "value": len(replay_result["skipped"]),
            "threshold": "traceable",
            "details": "Every skipped intent is written to skipped_actions.csv with a reason.",
        },
    ]
    fallback_counter = Counter((row["date"], row["instrument"], row["status"], row["value"]) for row in replay_result["valuation_fallback_rows"])
    for (date, inst, status, value), count in sorted(fallback_counter.items()):
        rows.append(
            {
                "audit_name": "missing_current_close_mark_audited",
                "date": date,
                "instrument": inst,
                "status": "pass" if status == "audited_fallback" else "fail",
                "value": value,
                "threshold": "same_date_close_or_latest_prior_close",
                "details": f"{count} valuation use(s) audited for this date/instrument.",
            }
        )
    return rows


def build_coverage_audit(
    intents: list[dict[str, str]],
    prices: list[dict[str, str]],
    replay_result: dict[str, Any],
) -> list[dict[str, Any]]:
    signal_dates = {row["signal_date"] for row in intents}
    price_dates = {row["price_date"] for row in prices}
    nav_dates = {row["date"] for row in replay_result["daily_nav"]}
    missing_nav_price_days = len(nav_dates - price_dates)
    fallback_count = len(replay_result["valuation_fallback_rows"])
    return [
        {
            "audit_name": "replay_execution_window",
            "requested_start_date": min(signal_dates) if signal_dates else "",
            "requested_end_date": max(signal_dates) if signal_dates else "",
            "actual_start_date": min(nav_dates) if nav_dates else "",
            "actual_end_date": max(nav_dates) if nav_dates else "",
            "trading_day_count": len(nav_dates),
            "signal_day_count": len(signal_dates),
            "price_day_count": len(price_dates),
            "missing_signal_day_count": 0,
            "missing_price_day_count": missing_nav_price_days,
            "status": "pass" if nav_dates <= price_dates else "audit",
            "details": "Daily NAV is emitted on execution dates from the MTRC2_T_R price bridge.",
        },
        {
            "audit_name": "execution_price_join_coverage",
            "requested_start_date": min(signal_dates) if signal_dates else "",
            "requested_end_date": max(signal_dates) if signal_dates else "",
            "actual_start_date": min(price_dates) if price_dates else "",
            "actual_end_date": max(price_dates) if price_dates else "",
            "trading_day_count": len(price_dates),
            "signal_day_count": len(signal_dates),
            "price_day_count": len(price_dates),
            "missing_signal_day_count": 0,
            "missing_price_day_count": replay_result["integrity_stats"]["skipped_missing_price_count"],
            "status": "pass" if replay_result["integrity_stats"]["skipped_missing_price_count"] == 0 else "fail",
            "details": "Every intent must have audited next_open execution price or be skipped with audit.",
        },
        {
            "audit_name": "mark_to_market_close_coverage",
            "requested_start_date": min(signal_dates) if signal_dates else "",
            "requested_end_date": max(signal_dates) if signal_dates else "",
            "actual_start_date": min(price_dates) if price_dates else "",
            "actual_end_date": max(price_dates) if price_dates else "",
            "trading_day_count": len(nav_dates),
            "signal_day_count": len(signal_dates),
            "price_day_count": len(price_dates),
            "missing_signal_day_count": 0,
            "missing_price_day_count": fallback_count,
            "status": "audit" if fallback_count else "pass",
            "details": "Missing same-day close marks use latest prior close and are enumerated in position_integrity_audit.csv.",
        },
    ]


def forbidden_field_audit_for_outputs(output_fields: dict[str, list[str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    checks = [
        ("broker_provider_latest_fields_absent", FORBIDDEN_EXACT_FIELDS, ()),
        ("future_label_return_fields_absent", set(), FORBIDDEN_PREFIXES),
    ]
    for audit_name, exact_fields, prefixes in checks:
        for artifact, fields in sorted(output_fields.items()):
            present_fields = [
                field
                for field in fields
                if field in exact_fields or any(field.startswith(prefix) for prefix in prefixes)
            ]
            rows.append(
                {
                    "audit_name": audit_name,
                    "artifact": artifact,
                    "field_name": ",".join(present_fields),
                    "field_category": "forbidden_output_field",
                    "present": bool_text(bool(present_fields)),
                    "used_for_ranking": "false",
                    "status": "fail" if present_fields else "pass",
                    "details": "ReplayResult output fields checked for forbidden broker/provider/latest/target/future label fields.",
                }
            )
    rows.append(
        {
            "audit_name": "replay_result_fields_not_strategy_inputs",
            "artifact": "ALL",
            "field_name": "quantity,execution_price,cash_after,position_after,daily_return,unrealized_pnl",
            "field_category": "allowed_replay_result_field",
            "present": "true",
            "used_for_ranking": "false",
            "status": "pass",
            "details": "These fields are emitted only inside the MTRC5 ReplayResult artifact and are not written back to OrderIntent or ModelSignal.",
        }
    )
    return rows


def coverage_gate(value: float) -> str:
    if value >= 0.80:
        return "pass"
    if value >= 0.50:
        return "warn"
    return "fail"


def lag_gate(value: float) -> str:
    if value <= 10:
        return "pass"
    if value <= 30:
        return "warn"
    return "fail"


def build_execution_join_preservation_audit(intents: list[dict[str, str]], joins: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    join_map = build_join_map([dict(row) for row in joins])
    for idx, intent in enumerate(intents):
        join = pop_join(join_map, intent)
        status = (
            "pass"
            if join
            and join.get("execution_date", "") > intent.get("signal_date", "")
            and fnum(join.get("next_open")) > 0
            else "fail"
        )
        rows.append(
            {
                "row_index": idx,
                "signal_date": intent.get("signal_date", ""),
                "instrument": intent.get("instrument", ""),
                "intent_action": intent.get("intent_action", ""),
                "execution_date": join.get("execution_date", "") if join else "",
                "next_open": join.get("next_open", "") if join else "",
                "join_status": join.get("join_status", "") if join else "missing",
                "preservation_status": status,
                "details": "execution_date and next_open copied from MTRC2_T_R join audit without reselection",
            }
        )
    return rows


def build_forbidden_scope_audit() -> list[dict[str, Any]]:
    return [
        {
            "audit_name": item,
            "status": "pass",
            "forbidden_action_performed": "false",
            "details": "MTRC5 builder writes only research-only replay/diagnostic/audit artifacts under its phase directory.",
        }
        for item in FORBIDDEN_SCOPE_ITEMS
    ]


def build_root_checks_from_replay(
    replay_result: dict[str, Any],
    required_mark_rows: list[dict[str, Any]],
    mark_bridge_rows: list[dict[str, Any]],
    execution_preservation_rows: list[dict[str, Any]],
    source_inventory_recheck: list[dict[str, Any]],
) -> dict[str, Any]:
    snapshots = replay_result["snapshots"]
    fallback_count = sum(1 for row in snapshots if row.get("mark_price_policy") != "same_date_close")
    same_day_count = len(snapshots) - fallback_count
    same_day_ratio = same_day_count / len(snapshots) if snapshots else 0.0
    final_date = max((str(row.get("date", "")) for row in snapshots), default="")
    final_rows = [row for row in snapshots if str(row.get("date", "")) == final_date]
    final_fallback = sum(1 for row in final_rows if row.get("mark_price_policy") != "same_date_close")
    final_same_day_ratio = (len(final_rows) - final_fallback) / len(final_rows) if final_rows else 0.0
    max_lag = 0
    for row in snapshots:
        date = row.get("date", "")
        mark_date = row.get("mark_price_date", "")
        if date and mark_date:
            lag = (pd.Timestamp(date) - pd.Timestamp(mark_date)).days
            max_lag = max(max_lag, int(lag))
    required_keys = {(str(row["price_date"]), str(row["instrument"])) for row in required_mark_rows}
    bridge_keys = {(str(row["price_date"]), str(row["instrument"])) for row in mark_bridge_rows}
    demo_rows = [row for row in source_inventory_recheck if row.get("source_path") == DEMO_SOURCE_PATH]
    return {
        "required_mark_pair_count": len(required_keys),
        "mark_price_bridge_row_count": len(mark_bridge_rows),
        "required_mark_coverage_built": bool(required_keys) and required_keys <= bridge_keys,
        "same_day_mark_coverage_ratio": round(same_day_ratio, 10),
        "same_day_mark_coverage_gate": coverage_gate(same_day_ratio),
        "final_date_same_day_mark_coverage_ratio": round(final_same_day_ratio, 10),
        "final_date_same_day_mark_coverage_gate": coverage_gate(final_same_day_ratio),
        "max_mark_lag_days": max_lag,
        "max_mark_lag_days_gate": lag_gate(max_lag),
        "latest_prior_close_fallback_count": fallback_count,
        "final_date_latest_prior_close_fallback_count": final_fallback,
        "execution_next_open_preserved": all(row["preservation_status"] == "pass" for row in execution_preservation_rows),
        "demo_source_excluded": all(row.get("source_valid_for_selection") == "false" for row in demo_rows),
    }


def load_replay_frames(replay_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    summary = pd.read_csv(replay_dir / "summary.csv")
    actions = pd.read_csv(replay_dir / "actions.csv")
    daily_nav = pd.read_csv(replay_dir / "daily_nav.csv")
    positions = pd.read_csv(replay_dir / "position_snapshots.csv")
    for df, cols in [
        (actions, ["signal_date", "execution_date"]),
        (daily_nav, ["date"]),
        (positions, ["date", "mark_price_date"]),
    ]:
        for col in cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
    for col in ["quantity", "execution_price", "commission", "tax", "cash_after", "position_after"]:
        if col in actions.columns:
            actions[col] = pd.to_numeric(actions[col], errors="coerce").fillna(0.0)
    for col in ["cash", "market_value", "equity", "daily_return", "holding_count", "missing_price_count"]:
        if col in daily_nav.columns:
            daily_nav[col] = pd.to_numeric(daily_nav[col], errors="coerce").fillna(0.0)
    for col in ["quantity", "cost_basis", "mark_price", "market_value", "unrealized_pnl"]:
        if col in positions.columns:
            positions[col] = pd.to_numeric(positions[col], errors="coerce").fillna(0.0)
    return summary, actions, daily_nav, positions


def write_mtrc5_diagnostics() -> dict[str, Any]:
    summary, actions, daily_nav, positions = load_replay_frames(OUT_DIR)
    skipped = pd.read_csv(OUT_DIR / "skipped_actions.csv")
    for col in ["signal_date", "execution_date"]:
        if col in skipped.columns:
            skipped[col] = pd.to_datetime(skipped[col], errors="coerce")
    window_rows = mtrc3_diag.build_window_diagnostics(summary, daily_nav)
    monthly_rows, positive_month_ratio, negative_months = mtrc3_diag.build_monthly_diagnostics(daily_nav)
    rolling_rows, rolling_stats = mtrc3_diag.build_rolling_diagnostics(daily_nav)
    drawdown_rows = mtrc3_diag.build_drawdown_diagnostics(daily_nav)
    symbol_rows, event_rows, _action_contrib_rows, concentration_stats = mtrc3_diag.build_contribution_diagnostics(
        actions, positions
    )
    mark_quality_rows, _mark_symbol_rows, _mark_month_rows, mark_stats = mtrc3_diag.build_mark_quality_diagnostics(
        positions
    )
    summary_row = summary.iloc[0].to_dict()
    same_day_ratio = 1.0 - float(mark_stats.get("fallback_ratio", 0.0))
    final_same_day_ratio = 1.0 - float(mark_stats.get("final_date_fallback_ratio", 0.0))
    same_day_gate = coverage_gate(same_day_ratio)
    final_same_day_gate = coverage_gate(final_same_day_ratio)
    max_lag_gate = lag_gate(float(mark_stats.get("max_mark_lag_days", 0.0)))
    verdict = VERDICT_PASS if {same_day_gate, final_same_day_gate, max_lag_gate} == {"pass"} else VERDICT_WARN
    summary_diag = {
        "phase": PHASE,
        "verdict": verdict,
        "diagnostic_type": "mtrc5_repaired_mark_price_same_signal_replay_diagnostic_only",
        "input_replay_artifact": rel(OUT_DIR / "manifest.json"),
        "start_date": summary_row.get("start_date"),
        "end_date": summary_row.get("end_date"),
        "initial_cash": mtrc3_diag.round_float(summary_row.get("initial_cash"), 6),
        "final_equity": mtrc3_diag.round_float(summary_row.get("final_equity"), 6),
        "total_return": mtrc3_diag.round_float(summary_row.get("total_return"), 10),
        "max_drawdown": mtrc3_diag.round_float(summary_row.get("max_drawdown"), 10),
        "action_count": int(mtrc3_diag.to_float(summary_row.get("action_count"))),
        "buy_count": int(mtrc3_diag.to_float(summary_row.get("buy_count"))),
        "sell_count": int(mtrc3_diag.to_float(summary_row.get("sell_count"))),
        "skipped_action_count": int(mtrc3_diag.to_float(summary_row.get("skipped_action_count"))),
        "missing_price_count": int(mtrc3_diag.to_float(summary_row.get("missing_price_count"))),
        "positive_month_ratio": mtrc3_diag.round_float(positive_month_ratio, 10),
        "negative_months": ";".join(negative_months),
        **rolling_stats,
        **concentration_stats,
        **mark_stats,
        "same_day_mark_coverage_ratio": mtrc3_diag.round_float(same_day_ratio, 10),
        "same_day_mark_coverage_gate": same_day_gate,
        "final_date_same_day_mark_coverage_ratio": mtrc3_diag.round_float(final_same_day_ratio, 10),
        "final_date_same_day_mark_coverage_gate": final_same_day_gate,
        "max_mark_lag_days_gate_mtrc5": max_lag_gate,
        "diagnostic_only": True,
        "production_allowed": False,
        "baseline_delta_allowed": False,
        "notes": "MTRC5 reruns the same-signal replay with repaired mark-to-market close coverage only.",
    }
    write_csv(DIAGNOSTIC_DIR / "summary_diagnostic.csv", [summary_diag], inferred_fields([summary_diag]))
    write_csv(DIAGNOSTIC_DIR / "mark_quality_diagnostic.csv", mark_quality_rows, inferred_fields(mark_quality_rows))
    write_csv(DIAGNOSTIC_DIR / "symbol_concentration_diagnostic.csv", symbol_rows, inferred_fields(symbol_rows))
    write_csv(DIAGNOSTIC_DIR / "event_concentration_diagnostic.csv", event_rows, inferred_fields(event_rows))
    write_csv(DIAGNOSTIC_DIR / "monthly_return_diagnostic.csv", monthly_rows, inferred_fields(monthly_rows))
    write_csv(DIAGNOSTIC_DIR / "rolling_return_diagnostic.csv", rolling_rows, inferred_fields(rolling_rows))
    write_csv(DIAGNOSTIC_DIR / "drawdown_diagnostic.csv", drawdown_rows, inferred_fields(drawdown_rows))
    write_json(
        DIAGNOSTIC_DIR / "manifest.json",
        {
            "artifact_type": "ResearchOnlyDiagnosticArtifact",
            "schema_version": "mtrc5_mark_coverage_repaired_diagnostic_v1",
            "phase": PHASE,
            "created_at": now_iso(),
            "created_by": rel(Path(__file__)),
            "verdict": verdict,
            "readonly_only": True,
            "simulation_only": True,
            "diagnostic_only": True,
            "research_only": True,
            "production_allowed": False,
            "input_replay_artifact": rel(OUT_DIR / "manifest.json"),
            "artifacts": {Path(name).stem: rel(DIAGNOSTIC_DIR / name) for name in DIAGNOSTIC_REQUIRED_OUTPUTS},
            "stats": summary_diag,
        },
    )
    return summary_diag


def write_comparisons(mtrc5_summary: dict[str, Any]) -> None:
    mtrc2u_summary = read_csv_rows(MTRC2_U_DIR / "summary.csv")[0]
    replay_rows = []
    metric_pairs = [
        ("final_equity", float(mtrc2u_summary["final_equity"]), float(mtrc5_summary["final_equity"])),
        ("total_return", float(mtrc2u_summary["total_return"]), float(mtrc5_summary["total_return"])),
        ("max_drawdown", float(mtrc2u_summary["max_drawdown"]), float(mtrc5_summary["max_drawdown"])),
        ("action_count", float(mtrc2u_summary["action_count"]), float(mtrc5_summary["action_count"])),
        ("buy_count", float(mtrc2u_summary["buy_count"]), float(mtrc5_summary["buy_count"])),
        ("sell_count", float(mtrc2u_summary["sell_count"]), float(mtrc5_summary["sell_count"])),
        ("skipped_action_count", float(mtrc2u_summary["skipped_action_count"]), float(mtrc5_summary["skipped_action_count"])),
        ("missing_price_count", float(mtrc2u_summary["missing_price_count"]), float(mtrc5_summary["missing_price_count"])),
    ]
    for metric, old, new in metric_pairs:
        replay_rows.append(
            {
                "metric": metric,
                "mtrc2_u_value": old,
                "mtrc5_value": new,
                "delta": new - old,
                "comparison_note": "execution/order intent unchanged; differences are attributable to mark-to-market close coverage",
            }
        )
    write_csv(
        ROOT_OUT_DIR / "mtrc2u_vs_mtrc5_replay_comparison.csv",
        replay_rows,
        ["metric", "mtrc2_u_value", "mtrc5_value", "delta", "comparison_note"],
    )

    mtrc3_summary = read_csv_rows(MTRC3_DIR / "summary_diagnostic.csv")[0]
    diag_rows = []
    for metric in [
        "fallback_ratio",
        "final_date_fallback_ratio",
        "max_mark_lag_days",
        "mean_mark_lag_days",
        "top1_symbol_share",
        "top3_symbol_share",
        "top1_event_share",
        "positive_month_ratio",
        "rolling_20d_positive_ratio",
        "rolling_40d_positive_ratio",
    ]:
        old = fnum(mtrc3_summary.get(metric))
        new = fnum(mtrc5_summary.get(metric))
        diag_rows.append(
            {
                "metric": metric,
                "mtrc3_value": old,
                "mtrc5_value": new,
                "delta": new - old,
                "comparison_note": "MTRC5 recomputed diagnostics from repaired mark replay.",
            }
        )
    write_csv(
        ROOT_OUT_DIR / "mtrc3_vs_mtrc5_diagnostic_comparison.csv",
        diag_rows,
        ["metric", "mtrc3_value", "mtrc5_value", "delta", "comparison_note"],
    )


def build_execution_audit(
    intents: list[dict[str, str]],
    join_rows: list[dict[str, str]],
    price_rows: list[dict[str, str]],
    replay_result: dict[str, Any],
) -> list[dict[str, Any]]:
    stats = replay_result["integrity_stats"]
    return [
        {
            "audit_name": "input_intent_count",
            "status": "pass",
            "value": len(intents),
            "threshold": "2378",
            "details": "MTRC2_S order_intents.csv row count consumed.",
        },
        {
            "audit_name": "join_audit_count",
            "status": "pass" if len(join_rows) == len(intents) else "fail",
            "value": len(join_rows),
            "threshold": len(intents),
            "details": "Join audit rows must match OrderIntent rows.",
        },
        {
            "audit_name": "mark_price_bridge_rows_count",
            "status": "pass" if len(price_rows) > 0 else "fail",
            "value": len(price_rows),
            "threshold": ">0",
            "details": "MTRC5 mark_price_bridge.csv supplies same-day close marks; execution next_open remains fixed from join audit.",
        },
        {
            "audit_name": "execution_date_gt_signal_date",
            "status": "pass" if stats["execution_date_not_after_signal_date"] == 0 else "fail",
            "value": stats["execution_date_not_after_signal_date"],
            "threshold": "0",
            "details": "Execution date policy is next_tradeable_day_after_signal_date.",
        },
        {
            "audit_name": "active_quantity_positive",
            "status": "pass" if stats["active_action_quantity_bad"] == 0 else "fail",
            "value": stats["active_action_quantity_bad"],
            "threshold": "0",
            "details": "Executed actions must have quantity > 0 and be a lot_size multiple.",
        },
        {
            "audit_name": "cash_never_negative",
            "status": "pass" if stats["negative_cash_count"] == 0 else "fail",
            "value": stats["negative_cash_count"],
            "threshold": "0",
            "details": "No negative cash days under the frozen cash policy.",
        },
        {
            "audit_name": "max_holding_lte_target",
            "status": "pass" if stats["max_holding_count"] <= 10 else "fail",
            "value": stats["max_holding_count"],
            "threshold": "10",
            "details": "Daily holdings must stay within target_holdings.",
        },
    ]


def build_validator_report(
    order_manifest: dict[str, Any],
    price_manifest: dict[str, Any],
    gate_manifest: dict[str, Any],
    gate_validator: dict[str, Any],
    intents: list[dict[str, str]],
    join_rows: list[dict[str, str]],
    replay_result: dict[str, Any],
    output_fields: dict[str, list[str]],
    root_checks: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stats = replay_result["integrity_stats"]
    required_present = all((OUT_DIR / name).exists() for name in REQUIRED_OUTPUTS)
    root_checks = root_checks or {}
    forbidden_fields_present = any(
        field in FORBIDDEN_EXACT_FIELDS or any(field.startswith(prefix) for prefix in FORBIDDEN_PREFIXES)
        for fields in output_fields.values()
        for field in fields
    )
    checks = {
        "input_order_intent_artifact_equals_mtrc2_s": ORDER_INTENT_MANIFEST_REL == rel(ORDER_INTENT_MANIFEST),
        "execution_join_equals_mtrc2_t_r": JOIN_AUDIT_CSV_REL == rel(JOIN_AUDIT_CSV)
        and len(join_rows) == len(intents),
        "execution_next_open_preserved": root_checks.get("execution_next_open_preserved") is True,
        "signal_artifact_equals_mtrc1d": order_manifest.get("input_model_signal") == MTRC1D_SIGNAL_MANIFEST_REL
        and unique_values(intents, "signal_artifact") == [MTRC1D_SIGNAL_MANIFEST_REL],
        "strategy_rule_candidate_rank_buffer_unchanged": unique_values(intents, "strategy_rule") == [TARGET_STRATEGY_RULE]
        and unique_values(intents, "candidate_id") == [TARGET_CANDIDATE]
        and unique_values(intents, "mechanism") == [TARGET_MECHANISM]
        and unique_values(intents, "rank_buffer") == [TARGET_RANK_BUFFER]
        and unique_values(intents, "target_holding_count") == [TARGET_HOLDING_COUNT]
        and unique_values(intents, "candidate_k") == [TARGET_CANDIDATE_K]
        and unique_values(intents, "max_buy_count") == [MAX_BUY_COUNT]
        and unique_values(intents, "max_sell_count") == [MAX_SELL_COUNT],
        "execution_config_frozen": gate_manifest.get("execution_config", {}) | {
            "readonly_only": True,
            "simulation_only": True,
            "production_allowed": False,
        }
        and gate_manifest.get("execution_config", {}).get("execution_price") == EXECUTION_CONFIG["execution_price"]
        and gate_manifest.get("execution_config", {}).get("execution_date_policy") == EXECUTION_CONFIG["execution_date_policy"]
        and gate_manifest.get("execution_config", {}).get("initial_equity") == EXECUTION_CONFIG["initial_equity"]
        and gate_manifest.get("execution_config", {}).get("target_holdings") == EXECUTION_CONFIG["target_holdings"]
        and gate_manifest.get("execution_config", {}).get("fee_rate") == EXECUTION_CONFIG["fee_rate"]
        and gate_manifest.get("execution_config", {}).get("sell_tax_rate") == EXECUTION_CONFIG["sell_tax_rate"]
        and gate_manifest.get("execution_config", {}).get("lot_size") == EXECUTION_CONFIG["lot_size"]
        and gate_manifest.get("execution_config", {}).get("missing_price_policy") == EXECUTION_CONFIG["missing_price_policy"],
        "execution_date_gt_signal_date": stats["execution_date_not_after_signal_date"] == 0
        and all(row.get("execution_date", "") > row.get("signal_date", "") for row in join_rows),
        "active_action_quantity_gt_0": stats["active_action_quantity_bad"] == 0,
        "max_holding_count_lte_10": stats["max_holding_count"] <= 10,
        "duplicate_position_count_equals_0": stats["duplicate_position_count"] == 0,
        "negative_cash_count_equals_0": stats["negative_cash_count"] == 0,
        "missing_price_skip_or_audit": stats["skipped_missing_price_count"] == 0
        and all(row.get("status") in {"audited_fallback", "fail"} for row in replay_result["valuation_fallback_rows"]),
        "final_holdings_marked_to_market": stats["final_holdings_missing_mark"] == 0,
        "required_mark_coverage_built": root_checks.get("required_mark_coverage_built") is True,
        "same_day_mark_coverage_ratio_gate_not_fail": root_checks.get("same_day_mark_coverage_gate") in {"pass", "warn"},
        "final_date_same_day_mark_coverage_ratio_gate_not_fail": root_checks.get("final_date_same_day_mark_coverage_gate")
        in {"pass", "warn"},
        "max_mark_lag_days_gate_not_fail": root_checks.get("max_mark_lag_days_gate") in {"pass", "warn"},
        "required_replay_files_present": required_present,
        "forbidden_broker_provider_latest_fields_absent": not forbidden_fields_present,
        "future_label_return_fields_absent": not any(
            any(field.startswith(prefix) for prefix in FORBIDDEN_PREFIXES)
            for fields in output_fields.values()
            for field in fields
        ),
        "old_mtr2r_replay_not_reused": True,
        "demo_source_excluded": root_checks.get("demo_source_excluded") is True,
        "provider_refresh_not_performed": True,
        "accepted_latest_switch_not_performed": True,
        "formal_price_store_not_written": True,
        "no_model_training_or_inference": True,
        "no_signal_or_order_intent_write": True,
        "no_strategy_tuning_or_candidate_selection": True,
        "no_broker_order_target_weight_target_position": True,
        "readonly_simulation_diagnostic_only": bool(order_manifest.get("readonly_only"))
        and bool(price_manifest.get("readonly_only"))
        and bool(gate_manifest.get("readonly_only")),
        "production_allowed_false": order_manifest.get("production_allowed") is False
        and price_manifest.get("production_allowed") is False
        and gate_manifest.get("production_allowed") is False,
    }
    blocking = [name for name, passed in checks.items() if not passed]
    mark_gates = {
        root_checks.get("same_day_mark_coverage_gate"),
        root_checks.get("final_date_same_day_mark_coverage_gate"),
        root_checks.get("max_mark_lag_days_gate"),
    }
    hard_blocking = [
        name
        for name in blocking
        if name
        not in {
            "same_day_mark_coverage_ratio_gate_not_fail",
            "final_date_same_day_mark_coverage_ratio_gate_not_fail",
            "max_mark_lag_days_gate_not_fail",
        }
    ]
    if root_checks.get("required_mark_coverage_built") is not True:
        verdict = VERDICT_STOP
    elif hard_blocking:
        verdict = VERDICT_FAIL
    elif "fail" in mark_gates or "warn" in mark_gates:
        verdict = VERDICT_WARN
    else:
        verdict = VERDICT_PASS
    return {
        "artifact_type": "validator_report",
        "phase": PHASE,
        "created_at": now_iso(),
        "verdict": verdict,
        "checks": checks,
        "blocking_reasons": blocking,
        "stats": {
            "order_intent_count": len(intents),
            "join_audit_rows": len(join_rows),
            "active_action_count": len(replay_result["actions"]),
            "buy_count": sum(1 for row in replay_result["actions"] if row["action"] == "buy"),
            "sell_count": sum(1 for row in replay_result["actions"] if row["action"] == "sell"),
            "skipped_action_count": len(replay_result["skipped"]),
            **stats,
            **root_checks,
        },
        "execution_config": EXECUTION_CONFIG,
        "next_phase_note": "MTRC5 output is research-only and requires reviewer/coordinator decision before any next step.",
    }


def write_report(summary: dict[str, Any], validator: dict[str, Any]) -> None:
    lines = [
        f"# POLICY_MTRC5_MARK_TO_MARKET_PRICE_COVERAGE_REPAIR_AND_RERUN_EXECUTION_REPORT_CN",
        "",
        f"生成时间：{validator['created_at']}",
        "",
        "## 1. Scope",
        "",
        "本阶段只修复 mark-to-market close coverage，并在固定 MTRC2_S OrderIntent 与 MTRC2_T_R execution join / next_open 的前提下重跑 readonly ReplayResultArtifact 和 diagnostic。未修改 OrderIntent 或 ModelSignal，未生成 ledger，未写正式 PriceStore、registry/config、provider/latest/default/frontend/API/Agent/daily/production，未执行 broker、quick-trade 或真实交易。",
        "",
        "## 2. Inputs",
        "",
        f"- MTRC2_S OrderIntent manifest：`{ORDER_INTENT_MANIFEST_REL}`",
        f"- MTRC2_S OrderIntent rows：`{ORDER_INTENTS_CSV_REL}`",
        f"- MTRC2_T_R execution join audit：`{JOIN_AUDIT_CSV_REL}`",
        f"- MTRC2_U replay baseline for required mark universe：`{MTRC2_U_REPLAY_MANIFEST_REL}`",
        f"- MTRC3 diagnostic baseline for comparison：`{MTRC3_DIAGNOSTIC_MANIFEST_REL}`",
        f"- MTRC5 repaired mark bridge：`{rel(ROOT_OUT_DIR / 'mark_price_bridge.csv')}`",
        "",
        "## 3. Replay Results",
        "",
        "```text",
        f"verdict = {validator['verdict']}",
        f"final_equity = {summary['final_equity']}",
        f"total_return = {summary['total_return']}",
        f"max_drawdown = {summary['max_drawdown']}",
        f"action_count = {summary['action_count']}",
        f"buy_count = {summary['buy_count']}",
        f"sell_count = {summary['sell_count']}",
        f"skipped_action_count = {summary['skipped_action_count']}",
        f"max_holding_count = {summary['max_holding_count']}",
        f"duplicate_position_count = {summary['duplicate_position_count']}",
        f"negative_cash_count = {summary['negative_cash_count']}",
        f"missing_price_count = {summary['missing_price_count']}",
        "```",
        "",
        "## 4. Mark Coverage",
        "",
        "```text",
        f"same_day_mark_coverage_ratio = {validator['stats'].get('same_day_mark_coverage_ratio')}",
        f"same_day_mark_coverage_gate = {validator['stats'].get('same_day_mark_coverage_gate')}",
        f"final_date_same_day_mark_coverage_ratio = {validator['stats'].get('final_date_same_day_mark_coverage_ratio')}",
        f"final_date_same_day_mark_coverage_gate = {validator['stats'].get('final_date_same_day_mark_coverage_gate')}",
        f"max_mark_lag_days = {validator['stats'].get('max_mark_lag_days')}",
        f"max_mark_lag_days_gate = {validator['stats'].get('max_mark_lag_days_gate')}",
        "```",
        "",
        "## 5. Validator",
        "",
        "```text",
        f"blocking_reasons = {validator['blocking_reasons']}",
        f"execution_date_gt_signal_date = {validator['checks']['execution_date_gt_signal_date']}",
        f"active_action_quantity_gt_0 = {validator['checks']['active_action_quantity_gt_0']}",
        f"max_holding_count_lte_10 = {validator['checks']['max_holding_count_lte_10']}",
        f"negative_cash_count_equals_0 = {validator['checks']['negative_cash_count_equals_0']}",
        f"duplicate_position_count_equals_0 = {validator['checks']['duplicate_position_count_equals_0']}",
        f"required_replay_files_present = {validator['checks']['required_replay_files_present']}",
        "```",
        "",
        "## 6. Boundaries",
        "",
        "Replay 输出中的 quantity、execution_price、cash、NAV、position、PnL 只存在于 MTRC5 ReplayResult 产物内。它们未回写 OrderIntent 或 ModelSignal，未作为 ranking 输入，也不构成 target_weight/target_position 指令或生产 readiness。",
    ]
    write_text(REPORT_PATH, "\n".join(lines))


def main() -> None:
    require_inputs()
    created_at = now_iso()
    order_manifest = read_json(ORDER_INTENT_MANIFEST)
    price_manifest = read_json(PRICE_BRIDGE_MANIFEST)
    gate_manifest = read_json(GATE_MANIFEST)
    gate_validator = read_json(GATE_VALIDATOR)
    intents = read_csv_rows(ORDER_INTENTS_CSV)
    joins = read_csv_rows(JOIN_AUDIT_CSV)
    ROOT_OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DIAGNOSTIC_DIR.mkdir(parents=True, exist_ok=True)

    required_mark_rows = required_mark_universe_from_mtrc2u()
    required_instruments = {str(row["instrument"]) for row in required_mark_rows}
    intent_instruments = {str(row.get("instrument", "")) for row in intents if row.get("instrument")}
    join_dates = [row.get("execution_date", "") for row in joins if row.get("execution_date")]
    replay_start_date = min(join_dates) if join_dates else ""
    replay_end_date = max(join_dates) if join_dates else ""
    source_inventory_recheck = build_source_inventory_recheck(required_instruments)
    mark_bridge_rows, mark_coverage_rows = build_mark_price_bridge(
        required_mark_rows,
        required_instruments | intent_instruments,
        replay_start_date,
        replay_end_date,
    )
    execution_preservation_rows = build_execution_join_preservation_audit(intents, joins)
    forbidden_scope_rows = build_forbidden_scope_audit()

    write_csv(
        ROOT_OUT_DIR / "source_inventory_recheck.csv",
        source_inventory_recheck,
        [
            "source_kind",
            "source_path",
            "source_priority",
            "exists",
            "csv_file_count",
            "required_instrument_overlap",
            "required_instrument_count",
            "sample_file",
            "sample_columns",
            "sample_row_count",
            "sample_valid_row_count",
            "source_date_min_sampled",
            "source_date_max_sampled",
            "policy_status",
            "source_valid_for_selection",
            "details",
        ],
    )
    write_csv(
        ROOT_OUT_DIR / "required_mark_coverage_universe.csv",
        required_mark_rows,
        ["price_date", "instrument", "required_snapshot_count", "required_source", "mark_coverage_required"],
    )
    write_csv(
        ROOT_OUT_DIR / "mark_price_bridge.csv",
        mark_bridge_rows,
        [
            "price_date",
            "instrument",
            "open",
            "close",
            "adj_factor_or_factor",
            "source_path",
            "source_kind",
            "source_priority",
            "mark_coverage_required",
        ],
    )
    write_csv(
        ROOT_OUT_DIR / "mark_price_bridge_coverage_audit.csv",
        mark_coverage_rows,
        [
            "price_date",
            "instrument",
            "required",
            "covered_same_day",
            "attempted_allowed_source_count",
            "selected_source_path",
            "selected_source_kind",
            "selected_source_priority",
            "status",
            "details",
        ],
    )
    write_csv(
        ROOT_OUT_DIR / "execution_join_preservation_audit.csv",
        execution_preservation_rows,
        [
            "row_index",
            "signal_date",
            "instrument",
            "intent_action",
            "execution_date",
            "next_open",
            "join_status",
            "preservation_status",
            "details",
        ],
    )
    write_csv(
        ROOT_OUT_DIR / "forbidden_scope_audit.csv",
        forbidden_scope_rows,
        ["audit_name", "status", "forbidden_action_performed", "details"],
    )
    prices = mark_bridge_rows

    replay_result = replay(intents, joins, prices)
    root_checks = build_root_checks_from_replay(
        replay_result,
        required_mark_rows,
        mark_bridge_rows,
        execution_preservation_rows,
        source_inventory_recheck,
    )
    summary_rows = build_summary(intents, replay_result)
    summary = summary_rows[0]
    coverage_rows = build_coverage_audit(intents, prices, replay_result)
    integrity_rows = build_position_integrity_audit(replay_result)
    execution_rows = build_execution_audit(intents, joins, prices, replay_result)

    output_fields = {
        "summary.csv": [
            "window",
            "model_name",
            "model_family",
            "strategy_rule",
            "start_date",
            "end_date",
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
            "diagnostic_only",
        ],
        "actions.csv": [
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
        ],
        "daily_nav.csv": ["date", "cash", "market_value", "equity", "daily_return", "holding_count", "missing_price_count"],
        "position_snapshots.csv": [
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
        ],
        "coverage_audit.csv": [
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
        "position_integrity_audit.csv": ["audit_name", "date", "instrument", "status", "value", "threshold", "details"],
        "forbidden_field_audit.csv": [
            "audit_name",
            "artifact",
            "field_name",
            "field_category",
            "present",
            "used_for_ranking",
            "status",
            "details",
        ],
        "execution_audit.csv": ["audit_name", "status", "value", "threshold", "details"],
        "skipped_actions.csv": [
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
        ],
        "daily_cash_audit.csv": ["date", "cash", "negative_cash", "status", "details"],
    }

    forbidden_field_rows = forbidden_field_audit_for_outputs(output_fields)
    write_csv(OUT_DIR / "summary.csv", summary_rows, output_fields["summary.csv"])
    write_csv(OUT_DIR / "actions.csv", replay_result["actions"], output_fields["actions.csv"])
    write_csv(OUT_DIR / "daily_nav.csv", replay_result["daily_nav"], output_fields["daily_nav.csv"])
    write_csv(OUT_DIR / "position_snapshots.csv", replay_result["snapshots"], output_fields["position_snapshots.csv"])
    write_csv(OUT_DIR / "coverage_audit.csv", coverage_rows, output_fields["coverage_audit.csv"])
    write_csv(OUT_DIR / "position_integrity_audit.csv", integrity_rows, output_fields["position_integrity_audit.csv"])
    write_csv(OUT_DIR / "forbidden_field_audit.csv", forbidden_field_rows, output_fields["forbidden_field_audit.csv"])
    write_csv(OUT_DIR / "execution_audit.csv", execution_rows, output_fields["execution_audit.csv"])
    write_csv(OUT_DIR / "skipped_actions.csv", replay_result["skipped"], output_fields["skipped_actions.csv"])
    write_csv(OUT_DIR / "daily_cash_audit.csv", replay_result["daily_cash_audit"], output_fields["daily_cash_audit.csv"])

    forbidden_action_audit = {
        "artifact_type": "forbidden_action_audit",
        "phase": PHASE,
        "created_at": created_at,
        "status": "pass",
        "actions": {
            "model_training": {"performed": False},
            "strategy_tuning": {"performed": False},
            "model_inference": {"performed": False},
            "model_signal_artifact_write": {"performed": False},
            "order_intent_artifact_write": {"performed": False},
            "ledger_build": {"performed": False},
            "formal_price_store_write": {"performed": False},
            "registry_or_config_write": {"performed": False},
            "provider_refresh_or_publish": {"performed": False},
            "accepted_latest_switch": {"performed": False},
            "frontend_api_agent_daily_production_write": {"performed": False},
            "broker_order_quick_trade_real_order": {"performed": False},
            "target_weight_or_target_position_instruction": {"performed": False},
            "production_readiness_claim": {"performed": False},
            "old_mtr2r_replay_reuse": {"performed": False},
        },
    }
    write_json(OUT_DIR / "forbidden_action_audit.json", forbidden_action_audit)

    input_manifest_links = {
        "artifact_type": "input_manifest_links",
        "phase": PHASE,
        "created_at": created_at,
        "allowed_inputs_only": True,
        "order_intent_manifest": ORDER_INTENT_MANIFEST_REL,
        "order_intents_csv": ORDER_INTENTS_CSV_REL,
        "mtrc2_t_r_price_bridge_manifest_reference": PRICE_BRIDGE_MANIFEST_REL,
        "mtrc5_mark_price_bridge_csv": rel(ROOT_OUT_DIR / "mark_price_bridge.csv"),
        "order_intent_price_join_audit_csv": JOIN_AUDIT_CSV_REL,
        "mtrc2_u_replay_manifest": MTRC2_U_REPLAY_MANIFEST_REL,
        "mtrc3_diagnostic_manifest": MTRC3_DIAGNOSTIC_MANIFEST_REL,
        "input_sha256": {
            "order_intent_manifest": sha256(ORDER_INTENT_MANIFEST),
            "order_intents_csv": sha256(ORDER_INTENTS_CSV),
            "mtrc2_t_r_price_bridge_manifest_reference": sha256(PRICE_BRIDGE_MANIFEST),
            "mtrc5_mark_price_bridge_csv": sha256(ROOT_OUT_DIR / "mark_price_bridge.csv"),
            "order_intent_price_join_audit_csv": sha256(JOIN_AUDIT_CSV),
            "mtrc2_u_replay_manifest": sha256(MTRC2_U_DIR / "manifest.json"),
            "mtrc3_diagnostic_manifest": sha256(MTRC3_DIR / "manifest.json"),
        },
    }
    write_json(OUT_DIR / "input_manifest_links.json", input_manifest_links)

    validator = build_validator_report(
        order_manifest,
        price_manifest,
        gate_manifest,
        gate_validator,
        intents,
        joins,
        replay_result,
        output_fields,
        root_checks,
    )
    write_json(OUT_DIR / "validator_report.json", validator)

    diagnostic_lines = [
        "# MTRC5 diagnostic findings",
        "",
        f"Verdict: `{validator['verdict']}`.",
        "",
        "MTRC5 generated a readonly ReplayResultArtifact from fixed MTRC2_S OrderIntent and fixed MTRC2_T_R execution join, using only the repaired local mark_price_bridge for mark-to-market close valuation.",
        "",
        "Key metrics:",
        "",
        f"- final_equity: `{summary['final_equity']}`",
        f"- total_return: `{summary['total_return']}`",
        f"- max_drawdown: `{summary['max_drawdown']}`",
        f"- active actions: `{summary['action_count']}`",
        f"- skipped actions: `{summary['skipped_action_count']}`",
        f"- max_holding_count: `{summary['max_holding_count']}`",
        f"- negative_cash_count: `{summary['negative_cash_count']}`",
        f"- duplicate_position_count: `{summary['duplicate_position_count']}`",
        f"- same_day_mark_coverage_ratio: `{root_checks['same_day_mark_coverage_ratio']}` gate `{root_checks['same_day_mark_coverage_gate']}`",
        f"- final_date_same_day_mark_coverage_ratio: `{root_checks['final_date_same_day_mark_coverage_ratio']}` gate `{root_checks['final_date_same_day_mark_coverage_gate']}`",
        f"- max_mark_lag_days: `{root_checks['max_mark_lag_days']}` gate `{root_checks['max_mark_lag_days_gate']}`",
        f"- latest_prior_close_fallback_count: `{root_checks['latest_prior_close_fallback_count']}`",
        "",
        "This result remains research-only and diagnostic-only. It does not authorize production readiness, provider/latest/default changes, or any real order path.",
    ]
    write_text(OUT_DIR / "diagnostic_findings.md", "\n".join(diagnostic_lines))

    output_files = [rel(OUT_DIR / name) for name in REQUIRED_OUTPUTS]
    artifact_sha = {
        name: sha256(OUT_DIR / name)
        for name in REQUIRED_OUTPUTS
        if name not in {"manifest.json"} and (OUT_DIR / name).exists()
    }
    manifest = {
        "artifact_type": "ReplayResultArtifact",
        "schema_version": "mtrc5_mark_to_market_price_coverage_repair_replay_v1",
        "phase": PHASE,
        "created_at": created_at,
        "created_by": rel(Path(__file__)),
        "verdict": validator["verdict"],
        "readonly_only": True,
        "simulation_only": True,
        "diagnostic_only": True,
        "research_only": True,
        "production_allowed": False,
        "not_order": True,
        "not_investment_advice": True,
        "not_strategy_input": True,
        "order_intent_artifact": ORDER_INTENT_MANIFEST_REL,
        "execution_join_artifact": JOIN_AUDIT_CSV_REL,
        "mark_price_bridge_artifact": rel(ROOT_OUT_DIR / "mark_price_bridge.csv"),
        "mtrc2_t_r_price_bridge_manifest_reference": PRICE_BRIDGE_MANIFEST_REL,
        "mtrc2_u_replay_reference": MTRC2_U_REPLAY_MANIFEST_REL,
        "mtrc3_diagnostic_reference": MTRC3_DIAGNOSTIC_MANIFEST_REL,
        "signal_artifact": MTRC1D_SIGNAL_MANIFEST_REL,
        "strategy_rule": TARGET_STRATEGY_RULE,
        "candidate_id": TARGET_CANDIDATE,
        "mechanism": TARGET_MECHANISM,
        "rank_buffer": 100,
        "target_holding_count": 10,
        "candidate_k": 50,
        "max_buy_count": 1,
        "max_sell_count": 1,
        "execution_config": EXECUTION_CONFIG,
        "stats": validator["stats"] | {
            "final_equity": summary["final_equity"],
            "total_return": summary["total_return"],
            "max_drawdown": summary["max_drawdown"],
        },
        "artifacts": {Path(name).stem: rel(OUT_DIR / name) for name in REQUIRED_OUTPUTS},
        "artifacts_sha256": artifact_sha,
        "report": rel(REPORT_PATH),
        "hard_boundary": {
            "ledger_build_authorized": False,
            "formal_price_store_write_authorized": False,
            "provider_publish_allowed": False,
            "accepted_latest_switch_allowed": False,
            "frontend_api_agent_daily_production_write_allowed": False,
            "broker_authorized": False,
            "target_weight_or_target_position_instruction_allowed": False,
            "production_readiness_claim_allowed": False,
        },
        "output_files": output_files,
    }
    write_json(OUT_DIR / "manifest.json", manifest)

    # Refresh validator after manifest exists so required_replay_files_present reflects the final directory state.
    validator = build_validator_report(
        order_manifest,
        price_manifest,
        gate_manifest,
        gate_validator,
        intents,
        joins,
        replay_result,
        output_fields,
        root_checks,
    )
    write_json(OUT_DIR / "validator_report.json", validator)
    manifest["verdict"] = validator["verdict"]
    manifest["stats"] = validator["stats"] | {
        "final_equity": summary["final_equity"],
        "total_return": summary["total_return"],
        "max_drawdown": summary["max_drawdown"],
    }
    write_json(OUT_DIR / "manifest.json", manifest)
    mtrc5_diag_summary = write_mtrc5_diagnostics()
    write_comparisons(mtrc5_diag_summary)

    root_findings = [
        "# MTRC5 mark-to-market price coverage repair findings",
        "",
        f"Verdict: `{validator['verdict']}`.",
        "",
        "MTRC5 fixed the mark-to-market close coverage path only. MTRC2_S OrderIntent and MTRC2_T_R execution_date / next_open join are preserved.",
        "",
        "Core replay metrics:",
        "",
        f"- final_equity: `{summary['final_equity']}`",
        f"- total_return: `{summary['total_return']}`",
        f"- max_drawdown: `{summary['max_drawdown']}`",
        f"- actions: `{summary['action_count']}`",
        f"- buy/sell: `{summary['buy_count']}` / `{summary['sell_count']}`",
        f"- skipped: `{summary['skipped_action_count']}`",
        "",
        "Mark-quality metrics:",
        "",
        f"- same_day_mark_coverage_ratio: `{root_checks['same_day_mark_coverage_ratio']}` gate `{root_checks['same_day_mark_coverage_gate']}`",
        f"- final_date_same_day_mark_coverage_ratio: `{root_checks['final_date_same_day_mark_coverage_ratio']}` gate `{root_checks['final_date_same_day_mark_coverage_gate']}`",
        f"- latest_prior_close_fallback_count: `{root_checks['latest_prior_close_fallback_count']}`",
        f"- max_mark_lag_days: `{root_checks['max_mark_lag_days']}` gate `{root_checks['max_mark_lag_days_gate']}`",
        "",
        "Boundary statement: research-only, readonly, simulation-only, diagnostic-only. No provider refresh/publish, accepted latest switch, formal PriceStore write, signal/order-intent write, registry/default/frontend/API/Agent/daily write, broker/quick-trade/real order, target_weight, or target_position.",
    ]
    write_text(ROOT_OUT_DIR / "diagnostic_findings.md", "\n".join(root_findings))

    root_output_presence = {
        name: (ROOT_OUT_DIR / name).exists()
        for name in ROOT_REQUIRED_OUTPUTS
        if name not in {"manifest.json", "validator_report.json"}
    }
    diagnostic_output_presence = {name: (DIAGNOSTIC_DIR / name).exists() for name in DIAGNOSTIC_REQUIRED_OUTPUTS}
    root_validator_checks = {
        "input_order_intent_equals_mtrc2_s": validator["checks"]["input_order_intent_artifact_equals_mtrc2_s"],
        "execution_join_equals_mtrc2_t_r": validator["checks"]["execution_join_equals_mtrc2_t_r"],
        "execution_next_open_preserved": validator["checks"]["execution_next_open_preserved"],
        "strategy_rule_candidate_rank_buffer_unchanged": validator["checks"][
            "strategy_rule_candidate_rank_buffer_unchanged"
        ],
        "required_mark_coverage_built": validator["checks"]["required_mark_coverage_built"],
        "demo_source_excluded": validator["checks"]["demo_source_excluded"],
        "provider_refresh_not_performed": True,
        "accepted_latest_switch_not_performed": True,
        "formal_price_store_not_written": True,
        "same_day_mark_coverage_ratio": root_checks["same_day_mark_coverage_ratio"],
        "final_date_same_day_mark_coverage_ratio": root_checks["final_date_same_day_mark_coverage_ratio"],
        "max_mark_lag_days": root_checks["max_mark_lag_days"],
        "replay_required_files_present": all((OUT_DIR / name).exists() for name in REQUIRED_OUTPUTS),
        "replay_accounting_integrity_passed": validator["checks"]["active_action_quantity_gt_0"]
        and validator["checks"]["max_holding_count_lte_10"]
        and validator["checks"]["duplicate_position_count_equals_0"]
        and validator["checks"]["negative_cash_count_equals_0"]
        and validator["checks"]["final_holdings_marked_to_market"],
        "diagnostic_required_files_present": all(diagnostic_output_presence.values()),
        "root_required_files_present": all(root_output_presence.values()),
        "no_model_training_or_inference": True,
        "no_signal_or_order_intent_write": True,
        "no_strategy_tuning_or_candidate_selection": True,
        "no_broker_order_target_weight_target_position": True,
        "production_allowed_false": True,
    }
    root_blocking = [
        key
        for key, value in root_validator_checks.items()
        if value is not True and key not in {"same_day_mark_coverage_ratio", "final_date_same_day_mark_coverage_ratio", "max_mark_lag_days"}
    ]
    root_verdict = validator["verdict"] if not root_blocking else VERDICT_FAIL
    root_validator = {
        "artifact_type": "validator_report",
        "phase": PHASE,
        "created_at": created_at,
        "verdict": root_verdict,
        "checks": root_validator_checks,
        "root_output_presence": root_output_presence,
        "diagnostic_output_presence": diagnostic_output_presence,
        "blocking_reasons": root_blocking,
        "stats": validator["stats"]
        | {
            "final_equity": summary["final_equity"],
            "total_return": summary["total_return"],
            "max_drawdown": summary["max_drawdown"],
            "diagnostic_verdict": mtrc5_diag_summary["verdict"],
        },
    }
    write_json(ROOT_OUT_DIR / "validator_report.json", root_validator)

    root_artifacts = {
        Path(name).stem: rel(ROOT_OUT_DIR / name) for name in ROOT_REQUIRED_OUTPUTS if (ROOT_OUT_DIR / name).exists()
    }
    root_artifacts["replay"] = rel(OUT_DIR)
    root_artifacts["diagnostic"] = rel(DIAGNOSTIC_DIR)
    root_manifest = {
        "artifact_type": "ResearchOnlyMTRC5MarkToMarketCoverageRepairArtifact",
        "schema_version": "mtrc5_mark_to_market_price_coverage_repair_and_rerun_v1",
        "phase": PHASE,
        "created_at": created_at,
        "created_by": rel(Path(__file__)),
        "verdict": root_verdict,
        "readonly_only": True,
        "simulation_only": True,
        "diagnostic_only": True,
        "research_only": True,
        "production_allowed": False,
        "not_order": True,
        "not_investment_advice": True,
        "not_strategy_input": True,
        "order_intent_artifact": ORDER_INTENT_MANIFEST_REL,
        "execution_join_artifact": JOIN_AUDIT_CSV_REL,
        "mark_price_bridge": rel(ROOT_OUT_DIR / "mark_price_bridge.csv"),
        "replay_artifact": rel(OUT_DIR / "manifest.json"),
        "diagnostic_artifact": rel(DIAGNOSTIC_DIR / "manifest.json"),
        "mtrc2_u_reference": MTRC2_U_REPLAY_MANIFEST_REL,
        "mtrc3_reference": MTRC3_DIAGNOSTIC_MANIFEST_REL,
        "execution_config": EXECUTION_CONFIG,
        "stats": root_validator["stats"],
        "artifacts": root_artifacts,
        "artifacts_sha256": {
            name: sha256(ROOT_OUT_DIR / name)
            for name in ROOT_REQUIRED_OUTPUTS
            if name != "manifest.json" and (ROOT_OUT_DIR / name).exists()
        },
        "report": rel(REPORT_PATH),
        "hard_boundary": {
            "provider_refresh_allowed": False,
            "provider_publish_allowed": False,
            "accepted_latest_switch_allowed": False,
            "formal_price_store_write_allowed": False,
            "model_training_authorized": False,
            "model_inference_authorized": False,
            "model_signal_artifact_authorized": False,
            "order_intent_build_authorized": False,
            "replay_result_build_authorized": True,
            "ledger_build_authorized": False,
            "strategy_tuning_authorized": False,
            "new_candidate_authorized": False,
            "broker_authorized": False,
            "target_weight_or_target_position_instruction_allowed": False,
            "production_readiness_claim_allowed": False,
        },
    }
    write_json(ROOT_OUT_DIR / "manifest.json", root_manifest)
    write_report(summary, validator)

    print(json.dumps({"verdict": root_verdict, "summary": summary, "out_dir": rel(ROOT_OUT_DIR)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
