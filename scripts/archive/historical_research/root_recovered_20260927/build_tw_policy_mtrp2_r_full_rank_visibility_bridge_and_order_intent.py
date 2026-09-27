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

import yaml


ROOT = Path(__file__).resolve().parents[1]

PHASE = "MTRP2_R_FULL_RANK_VISIBILITY_BRIDGE_AND_ORDER_INTENT"
STRATEGY_RULE = "top50_hold_rank_buffer_100"
BRIDGE_NAME = "top50_hold_rank_buffer_100_full_rank_visibility_bridge"
SOURCE_LINEAGE = "existing_audited_broad_reference_repackaged_for_production_candidate_readiness"

VERDICT_PASS = "PASS_FULL_RANK_VISIBILITY_BRIDGE_AND_ORDER_INTENT_READY_FOR_P3_REPLAY"
VERDICT_BRIDGE_ONLY = "PASS_BRIDGE_READY_BUT_ORDER_INTENT_BLOCKED"
VERDICT_STOP_LINEAGE = "STOP_SOURCE_LINEAGE_NOT_ACCEPTABLE_FOR_PRODUCTION_CANDIDATE"
VERDICT_FAIL = "FAIL_NEEDS_MTRP2_R_REPAIR"

WINDOW_START = "2026-01-02"
WINDOW_END = "2026-05-07"
TARGET_HOLDING_COUNT = 10
CANDIDATE_K = 50
HOLD_RANK_BUFFER = 100
MAX_BUY_COUNT = 1
MAX_SELL_COUNT = 1

SOURCE_DIR = (
    ROOT
    / "data_tw/artifacts/signals/"
    / "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025_broad_full_rank_mtr2_r/"
    / "r1_broad_full_rank_visibility_repair_20260628"
)
SOURCE_MANIFEST = SOURCE_DIR / "manifest.json"
SOURCE_SIGNALS = SOURCE_DIR / "signals.csv"

DEPENDENCY = ROOT / "configs/strategy_dependencies/top50_hold_rank_buffer_100.yaml"
BRIDGE_BASE = ROOT / f"data_tw/artifacts/signals/{BRIDGE_NAME}"
ORDER_BASE = ROOT / f"data_tw/artifacts/strategies/{STRATEGY_RULE}"
REPORT_PATH = (
    ROOT
    / "docs/tw_portfolio_decision_model/"
    / "POLICY_MTRP2_R_FULL_RANK_VISIBILITY_BRIDGE_AND_ORDER_INTENT_EXECUTION_REPORT_CN.md"
)

REQUIRED_READ_FILES = [
    "docs/tw_portfolio_decision_model/POLICY_MTRC6_COORDINATOR_DECISION_AND_PRODUCTION_GATE_CN.md",
    "docs/tw_portfolio_decision_model/POLICY_MTRP0_P2_PRODUCTION_CANDIDATE_ORDER_INTENT_EXECUTION_REPORT_CN.md",
    "docs/tw_portfolio_decision_model/POLICY_MTRP0_P2_PRODUCTION_CANDIDATE_ORDER_INTENT_REVIEW_CN.md",
    "configs/strategy_dependencies/top50_hold_rank_buffer_100.yaml",
    "scripts/build_tw_policy_mtrp0_p2_production_candidate_order_intent.py",
    "docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md",
    "docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md",
    "docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md",
    "docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md",
    "docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md",
    "docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md",
]

SIGNAL_FIELDS = [
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
    "source_model_artifact",
    "source_feature_artifact",
    "ext_ltr_top50_flag",
    "ext_broad_rank_visibility_only",
    "ext_buy_ranking_allowed",
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
    "hold_rank_buffer",
    "tie_breaker",
    "readonly_only",
    "simulation_only",
    "production_allowed",
    "production_candidate",
    "not_order",
    "not_target_position",
    "not_investment_advice",
    "model_family",
    "signal_asof",
    "available_at",
    "source_lineage",
]

FORBIDDEN_EXACT_FIELDS = {
    "action",
    "allocation_weight",
    "broker",
    "broker_order_id",
    "cash",
    "cash_after",
    "commission",
    "daily_return",
    "equity",
    "execution_date",
    "execution_price",
    "execution_quantity",
    "fee",
    "holding",
    "lots",
    "ltr_relevance_label",
    "nav",
    "next_close",
    "next_open",
    "order_id",
    "order_qty",
    "position",
    "quick_trade",
    "realized_pnl",
    "realized_return",
    "relevance_10d_top_heavy",
    "replay_return",
    "shares",
    "target_position",
    "target_weight",
    "tax",
    "unrealized_pnl",
}
FORBIDDEN_PREFIXES = (
    "future_return_",
    "future_excess_return_",
    "forward_return_",
    "label_",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_id() -> str:
    return "mtrp2_r_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def read_csv_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader), list(reader.fieldnames or [])


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_float(value: Any) -> float:
    text = str(value or "").strip()
    if text == "":
        return float("nan")
    try:
        return float(text)
    except ValueError:
        return float("nan")


def is_nan(value: float) -> bool:
    return math.isnan(value)


def format_number(value: Any) -> str:
    number = parse_float(value)
    if is_nan(number):
        return ""
    if number.is_integer():
        return str(int(number))
    return f"{number:.12g}"


def format_bool(value: bool) -> str:
    return "true" if value else "false"


def forbidden_names_present(names: set[str] | list[str]) -> list[str]:
    present: list[str] = []
    for name in names:
        lowered = str(name).strip().lower()
        if lowered in FORBIDDEN_EXACT_FIELDS or any(lowered.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
            present.append(str(name))
    return sorted(set(present))


def check(name: str, ok: bool, details: str = "", value: Any = "", threshold: Any = "") -> dict[str, Any]:
    return {
        "check_name": name,
        "status": "pass" if ok else "fail",
        "value": value,
        "threshold": threshold,
        "details": details,
    }


def require_inputs() -> None:
    missing = [ROOT / item for item in REQUIRED_READ_FILES if not (ROOT / item).exists()]
    missing.extend(path for path in [SOURCE_MANIFEST, SOURCE_SIGNALS] if not path.exists())
    if missing:
        raise FileNotFoundError("Missing required input(s): " + ", ".join(rel(path) for path in missing))
    for item in REQUIRED_READ_FILES:
        (ROOT / item).read_text(encoding="utf-8")
    read_json(SOURCE_MANIFEST)
    SOURCE_SIGNALS.read_text(encoding="utf-8")


def source_lineage_checks(source_manifest: dict[str, Any]) -> tuple[bool, list[dict[str, Any]]]:
    checks = [
        check(
            "source_is_expected_existing_broad_reference",
            source_manifest.get("artifact_name")
            == "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025_broad_full_rank_mtr2_r",
            rel(SOURCE_MANIFEST),
            source_manifest.get("artifact_name", ""),
            "expected broad reference artifact",
        ),
        check("source_quality_status_pass", source_manifest.get("quality_status") == "pass", "", source_manifest.get("quality_status", ""), "pass"),
        check("source_window_start_matches", (source_manifest.get("window") or {}).get("start") == WINDOW_START, "", (source_manifest.get("window") or {}).get("start", ""), WINDOW_START),
        check("source_window_end_matches", (source_manifest.get("window") or {}).get("end") == WINDOW_END, "", (source_manifest.get("window") or {}).get("end", ""), WINDOW_END),
        check("source_research_only_not_promoted", source_manifest.get("research_only") is True, "source remains research_only lineage", source_manifest.get("research_only"), True),
        check("source_production_allowed_false", source_manifest.get("production_allowed") is False, "", source_manifest.get("production_allowed"), False),
    ]
    return all(row["status"] == "pass" for row in checks), checks


def is_top50(row: dict[str, str]) -> bool:
    return parse_float(row.get("candidate_rank")) <= CANDIDATE_K


def bridge_signal_row(row: dict[str, str]) -> dict[str, Any]:
    top50 = is_top50(row)
    return {
        "date": row.get("date", ""),
        "instrument": row.get("instrument", ""),
        "model_name": BRIDGE_NAME,
        "model_family": row.get("model_family", "ltr") or "ltr",
        "candidate_rank": format_number(row.get("candidate_rank")),
        "buy_score": row.get("buy_score", "") if top50 else "",
        "raw_score": row.get("raw_score", "") if top50 else "",
        "score_rank": format_number(row.get("score_rank")) if top50 else "",
        "full_qlib_rank": format_number(row.get("full_qlib_rank")),
        "signal_asof": row.get("signal_asof", row.get("date", "")),
        "available_at": row.get("available_at", row.get("date", "")),
        "source_artifact": rel(SOURCE_MANIFEST),
        "source_model_artifact": rel(SOURCE_MANIFEST),
        "source_feature_artifact": SOURCE_LINEAGE,
        "ext_ltr_top50_flag": format_bool(top50),
        "ext_broad_rank_visibility_only": format_bool(not top50),
        "ext_buy_ranking_allowed": format_bool(top50),
    }


def build_bridge_rows(source_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = [
        bridge_signal_row(row)
        for row in source_rows
        if WINDOW_START <= row.get("date", "") <= WINDOW_END
    ]
    rows.sort(key=lambda row: (row["date"], parse_float(row["full_qlib_rank"]), row["instrument"]))
    return rows


def signal_stats(rows: list[dict[str, Any]], fields: list[str]) -> dict[str, Any]:
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    duplicates = 0
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (str(row.get("date", "")), str(row.get("instrument", "")))
        if key in seen:
            duplicates += 1
        seen.add(key)
        by_date[str(row.get("date", ""))].append(row)
    dates = sorted(day for day in by_date if day)
    daily_counts = [len(by_date[day]) for day in dates]
    top50_daily_counts = [
        sum(1 for row in by_date[day] if parse_float(row.get("candidate_rank")) <= CANDIDATE_K)
        for day in dates
    ]
    max_full_by_day = [
        max(parse_float(row.get("full_qlib_rank")) for row in by_date[day])
        for day in dates
    ]
    top50_rows = [row for row in rows if parse_float(row.get("candidate_rank")) <= CANDIDATE_K]
    non_top50_rows = [row for row in rows if parse_float(row.get("candidate_rank")) > CANDIDATE_K]
    return {
        "row_count": len(rows),
        "date_count": len(dates),
        "date_start": dates[0] if dates else "",
        "date_end": dates[-1] if dates else "",
        "duplicate_date_instrument": duplicates,
        "daily_min_row_count": min(daily_counts) if daily_counts else 0,
        "daily_max_row_count": max(daily_counts) if daily_counts else 0,
        "top50_row_count": len(top50_rows),
        "non_top50_row_count": len(non_top50_rows),
        "top50_daily_min_count": min(top50_daily_counts) if top50_daily_counts else 0,
        "top50_daily_max_count": max(top50_daily_counts) if top50_daily_counts else 0,
        "daily_min_max_full_qlib_rank": int(min(max_full_by_day)) if max_full_by_day else 0,
        "max_full_qlib_rank": int(max(max_full_by_day)) if max_full_by_day else 0,
        "top50_missing_buy_score_count": sum(1 for row in top50_rows if is_nan(parse_float(row.get("buy_score")))),
        "top50_ext_buy_ranking_not_true_count": sum(1 for row in top50_rows if str(row.get("ext_buy_ranking_allowed", "")).lower() != "true"),
        "non_top50_buy_score_present_count": sum(1 for row in non_top50_rows if str(row.get("buy_score", "")).strip()),
        "non_top50_ext_buy_ranking_not_false_count": sum(1 for row in non_top50_rows if str(row.get("ext_buy_ranking_allowed", "")).lower() != "false"),
        "forbidden_fields": forbidden_names_present(set(fields)),
    }


def build_coverage_audit(stats: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"audit_name": "date_range", "status": "pass" if stats["date_start"] == WINDOW_START and stats["date_end"] == WINDOW_END else "fail", "value": f"{stats['date_start']}..{stats['date_end']}", "threshold": f"{WINDOW_START}..{WINDOW_END}", "details": ""},
        {"audit_name": "daily_row_count_min", "status": "pass" if stats["daily_min_row_count"] >= HOLD_RANK_BUFFER else "fail", "value": stats["daily_min_row_count"], "threshold": f">={HOLD_RANK_BUFFER}", "details": ""},
        {"audit_name": "top50_daily_row_count", "status": "pass" if stats["top50_daily_min_count"] == CANDIDATE_K and stats["top50_daily_max_count"] == CANDIDATE_K else "fail", "value": f"{stats['top50_daily_min_count']}..{stats['top50_daily_max_count']}", "threshold": CANDIDATE_K, "details": ""},
        {"audit_name": "daily_full_rank_visibility_min", "status": "pass" if stats["daily_min_max_full_qlib_rank"] >= HOLD_RANK_BUFFER else "fail", "value": stats["daily_min_max_full_qlib_rank"], "threshold": f">={HOLD_RANK_BUFFER}", "details": ""},
        {"audit_name": "duplicate_date_instrument", "status": "pass" if stats["duplicate_date_instrument"] == 0 else "fail", "value": stats["duplicate_date_instrument"], "threshold": 0, "details": ""},
    ]


def build_forbidden_field_audit(fields: list[str], artifact: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    exact_fields = sorted(FORBIDDEN_EXACT_FIELDS | {"future_return_10d", "future_excess_return_10d", "forward_return_10d", "label_10d"})
    field_set = {field.lower() for field in fields}
    for name in exact_fields:
        present = name.lower() in field_set
        rows.append({
            "audit_name": "forbidden_field_absent",
            "artifact": artifact,
            "field_name": name,
            "field_category": "forbidden_contract_field",
            "present": format_bool(present),
            "used_for_ranking": "false",
            "status": "fail" if present else "pass",
            "details": "",
        })
    return rows


def build_lineage_audit(source_manifest: dict[str, Any], lineage_checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [{
        "audit_name": "source_lineage_policy",
        "status": "pass",
        "source_artifact": rel(SOURCE_MANIFEST),
        "source_research_only": format_bool(bool(source_manifest.get("research_only"))),
        "source_diagnostic_only": format_bool(bool(source_manifest.get("diagnostic_only"))),
        "source_lineage": SOURCE_LINEAGE,
        "details": "bridge is production-candidate readonly readiness only and is not declared production-ready",
    }]
    for item in lineage_checks:
        rows.append({
            "audit_name": item["check_name"],
            "status": item["status"],
            "source_artifact": rel(SOURCE_MANIFEST),
            "source_research_only": format_bool(bool(source_manifest.get("research_only"))),
            "source_diagnostic_only": format_bool(bool(source_manifest.get("diagnostic_only"))),
            "source_lineage": SOURCE_LINEAGE,
            "details": item["details"],
        })
    return rows


def bridge_schema() -> dict[str, Any]:
    return {
        "artifact_type": "schema",
        "schema_version": "mtrp2_r_full_rank_visibility_bridge_v1",
        "artifact_name": BRIDGE_NAME,
        "core_fields": SIGNAL_FIELDS[:14],
        "extension_fields": SIGNAL_FIELDS[14:],
        "unique_key": ["date", "instrument"],
        "ranking_usage": {
            "buy_ranking": "candidate_rank <= 50 AND ext_buy_ranking_allowed=true",
            "hold_buffer": "full_qlib_rank may be consumed for current holdings through hold_rank_buffer=100",
            "non_top50_buy_forbidden": True,
            "non_top50_buy_score_policy": "blank_or_ext_buy_ranking_allowed_false",
        },
        "forbidden_order_semantics": [
            "broker",
            "order",
            "target_weight",
            "target_position",
            "execution_price",
            "quantity",
        ],
    }


def validate_bridge(stats: dict[str, Any], lineage_ok: bool, coverage: list[dict[str, Any]], forbidden_audit: list[dict[str, Any]]) -> tuple[bool, list[dict[str, Any]]]:
    checks = [
        check("source_lineage_acceptable_for_readonly_repackaging", lineage_ok, SOURCE_LINEAGE),
        check("window_start", stats["date_start"] == WINDOW_START, "", stats["date_start"], WINDOW_START),
        check("window_end", stats["date_end"] == WINDOW_END, "", stats["date_end"], WINDOW_END),
        check("daily_rows_gte_100", stats["daily_min_row_count"] >= HOLD_RANK_BUFFER, "", stats["daily_min_row_count"], f">={HOLD_RANK_BUFFER}"),
        check("daily_top50_exactly_50", stats["top50_daily_min_count"] == CANDIDATE_K and stats["top50_daily_max_count"] == CANDIDATE_K, "", f"{stats['top50_daily_min_count']}..{stats['top50_daily_max_count']}", CANDIDATE_K),
        check("top50_buy_score_available", stats["top50_missing_buy_score_count"] == 0, "", stats["top50_missing_buy_score_count"], 0),
        check("top50_ext_buy_ranking_allowed_true", stats["top50_ext_buy_ranking_not_true_count"] == 0, "", stats["top50_ext_buy_ranking_not_true_count"], 0),
        check("non_top50_buy_score_blank", stats["non_top50_buy_score_present_count"] == 0, "", stats["non_top50_buy_score_present_count"], 0),
        check("non_top50_ext_buy_ranking_allowed_false", stats["non_top50_ext_buy_ranking_not_false_count"] == 0, "", stats["non_top50_ext_buy_ranking_not_false_count"], 0),
        check("duplicate_key_zero", stats["duplicate_date_instrument"] == 0, "", stats["duplicate_date_instrument"], 0),
        check("forbidden_fields_absent", not stats["forbidden_fields"], "|".join(stats["forbidden_fields"]), stats["forbidden_fields"], "none"),
    ]
    checks.extend(check(f"coverage_{row['audit_name']}", row["status"] == "pass", row.get("details", ""), row.get("value", ""), row.get("threshold", "")) for row in coverage)
    checks.append(check("forbidden_field_audit_pass", all(row["status"] == "pass" for row in forbidden_audit), "", "", "all pass"))
    return all(row["status"] == "pass" for row in checks), checks


def make_intent(row: dict[str, Any], action: str, reason: str, buy_rank: Any, current_holding: bool, bridge_manifest_rel: str) -> dict[str, Any]:
    return {
        "signal_date": row["date"],
        "instrument": row["instrument"],
        "intent_action": action,
        "intent_reason": reason,
        "strategy_rule": STRATEGY_RULE,
        "candidate_rank": format_number(row.get("candidate_rank")),
        "buy_rank": buy_rank,
        "full_qlib_rank": format_number(row.get("full_qlib_rank")),
        "max_buy_count": MAX_BUY_COUNT,
        "max_sell_count": MAX_SELL_COUNT,
        "model_name": row.get("model_name", BRIDGE_NAME),
        "signal_artifact": bridge_manifest_rel,
        "portfolio_state_artifact": "readonly_intent_state_from_prior_intents_no_execution_no_quantity",
        "current_holding_flag": format_bool(current_holding),
        "target_holding_count": TARGET_HOLDING_COUNT,
        "candidate_k": CANDIDATE_K,
        "hold_rank_buffer": HOLD_RANK_BUFFER,
        "tie_breaker": "buy_score_desc,full_qlib_rank_asc,instrument_asc",
        "readonly_only": "true",
        "simulation_only": "true",
        "production_allowed": "false",
        "production_candidate": "true",
        "not_order": "true",
        "not_target_position": "true",
        "not_investment_advice": "true",
        "model_family": row.get("model_family", "ltr"),
        "signal_asof": row.get("signal_asof", row["date"]),
        "available_at": row.get("available_at", row["date"]),
        "source_lineage": SOURCE_LINEAGE,
    }


def build_order_intents(bridge_rows: list[dict[str, Any]], bridge_manifest_rel: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in bridge_rows:
        by_date[str(row["date"])].append(row)

    holdings: set[str] = set()
    intents: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    stats = {
        "missing_visibility_days": 0,
        "max_holding_count": 0,
        "buy_intent_count": 0,
        "sell_intent_count": 0,
        "non_top50_buy_intent_count": 0,
        "sell_rank_lte_buffer_count": 0,
    }

    for day in sorted(by_date):
        day_rows = by_date[day]
        by_instrument = {row["instrument"]: row for row in day_rows}
        held_before = set(holdings)
        missing_visibility = sorted(inst for inst in held_before if inst not in by_instrument)

        day_intents: list[dict[str, Any]] = []
        sold_instrument = ""
        bought_instrument = ""
        status = "pass"
        details = "sell full_qlib_rank > 100 worst holding; buy top50 by buy_score desc/full_qlib_rank asc/instrument asc"

        if missing_visibility:
            status = "fail"
            details = "holding visibility missing; no assumed holding rank"
            stats["missing_visibility_days"] += 1
        else:
            sell_candidates = [
                by_instrument[inst]
                for inst in held_before
                if parse_float(by_instrument[inst].get("full_qlib_rank")) > HOLD_RANK_BUFFER
            ]
            sell_candidates.sort(key=lambda row: (-parse_float(row.get("full_qlib_rank")), row["instrument"]))
            for sell_row in sell_candidates[:MAX_SELL_COUNT]:
                sold_instrument = sell_row["instrument"]
                day_intents.append(make_intent(sell_row, "sell", "hold_rank_buffer_100_sell_worst_holding", "", True, bridge_manifest_rel))
                holdings.remove(sold_instrument)

            top50_candidates = [
                row for row in day_rows
                if parse_float(row.get("candidate_rank")) <= CANDIDATE_K
                and str(row.get("ext_buy_ranking_allowed", "")).lower() == "true"
                and not is_nan(parse_float(row.get("buy_score")))
            ]
            top50_candidates.sort(key=lambda row: (-parse_float(row.get("buy_score")), parse_float(row.get("full_qlib_rank")), row["instrument"]))
            buy_rank_by_instrument = {row["instrument"]: idx for idx, row in enumerate(top50_candidates, start=1)}
            open_slots = max(0, TARGET_HOLDING_COUNT - len(holdings))
            if open_slots > 0:
                for buy_row in top50_candidates:
                    if buy_row["instrument"] in holdings:
                        continue
                    bought_instrument = buy_row["instrument"]
                    day_intents.append(
                        make_intent(
                            buy_row,
                            "buy",
                            "top50_buy_score_best_unheld",
                            buy_rank_by_instrument[buy_row["instrument"]],
                            False,
                            bridge_manifest_rel,
                        )
                    )
                    holdings.add(bought_instrument)
                    break

        intents.extend(day_intents)
        stats["max_holding_count"] = max(stats["max_holding_count"], len(holdings))
        stats["buy_intent_count"] += sum(1 for row in day_intents if row["intent_action"] == "buy")
        stats["sell_intent_count"] += sum(1 for row in day_intents if row["intent_action"] == "sell")
        stats["non_top50_buy_intent_count"] += sum(
            1
            for row in day_intents
            if row["intent_action"] == "buy" and parse_float(row.get("candidate_rank")) > CANDIDATE_K
        )
        stats["sell_rank_lte_buffer_count"] += sum(
            1
            for row in day_intents
            if row["intent_action"] == "sell" and parse_float(row.get("full_qlib_rank")) <= HOLD_RANK_BUFFER
        )
        audit_rows.append({
            "signal_date": day,
            "status": status,
            "top50_row_count": sum(1 for row in day_rows if parse_float(row.get("candidate_rank")) <= CANDIDATE_K),
            "visible_row_count": len(day_rows),
            "holding_count_before": len(held_before),
            "holding_count_after": len(holdings),
            "sell_intent_count": sum(1 for row in day_intents if row["intent_action"] == "sell"),
            "buy_intent_count": sum(1 for row in day_intents if row["intent_action"] == "buy"),
            "sold_instrument": sold_instrument,
            "bought_instrument": bought_instrument,
            "missing_visibility_count": len(missing_visibility),
            "missing_visibility_instruments": "|".join(missing_visibility),
            "details": details,
        })
    return intents, audit_rows, stats


def order_schema() -> dict[str, Any]:
    return {
        "artifact_type": "schema",
        "schema_version": "mtrp2_r_order_intent_v1",
        "strategy_rule": STRATEGY_RULE,
        "required_order_intent_fields": ORDER_FIELDS,
        "allowed_actions": ["buy", "sell", "hold", "skip"],
        "rule": {
            "max_buy_count": MAX_BUY_COUNT,
            "max_sell_count": MAX_SELL_COUNT,
            "target_holding_count": TARGET_HOLDING_COUNT,
            "candidate_k": CANDIDATE_K,
            "hold_rank_buffer": HOLD_RANK_BUFFER,
            "sell": "sell worst current holding with full_qlib_rank > 100",
            "buy": "candidate_rank <= 50 and ext_buy_ranking_allowed=true; buy_score desc, full_qlib_rank asc, instrument asc",
        },
        "forbidden_order_intent_fields": sorted(FORBIDDEN_EXACT_FIELDS),
    }


def forbidden_action_audit(created_at: str) -> dict[str, Any]:
    return {
        "artifact_type": "forbidden_action_audit",
        "phase": PHASE,
        "created_at": created_at,
        "status": "pass",
        "actions": {
            "train_model": False,
            "tune_model": False,
            "score_recompute": False,
            "read_model_private_file": False,
            "read_mtrc_private_signal_csv_as_runtime_input": False,
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
            "quantity_output": False,
        },
        "details": "readonly/simulation/production-candidate artifact build only",
    }


def validate_order_intents(intents: list[dict[str, Any]], audit_rows: list[dict[str, Any]], stats: dict[str, Any]) -> tuple[bool, list[dict[str, Any]]]:
    fields = set(ORDER_FIELDS)
    forbidden = forbidden_names_present(fields)
    buy_counts = Counter(row["signal_date"] for row in intents if row["intent_action"] == "buy")
    sell_counts = Counter(row["signal_date"] for row in intents if row["intent_action"] == "sell")
    checks = [
        check("order_intents_present", bool(intents), "", len(intents), ">0"),
        check("order_intent_required_fields_present", set(ORDER_FIELDS).issubset(fields), "", "|".join(sorted(set(ORDER_FIELDS) - fields)), "none"),
        check("order_intent_forbidden_fields_absent", not forbidden, "|".join(forbidden), forbidden, "none"),
        check("daily_buy_count_lte_1", max(buy_counts.values() or [0]) <= MAX_BUY_COUNT, "", dict(buy_counts), f"<={MAX_BUY_COUNT}"),
        check("daily_sell_count_lte_1", max(sell_counts.values() or [0]) <= MAX_SELL_COUNT, "", dict(sell_counts), f"<={MAX_SELL_COUNT}"),
        check("buy_intents_top50_only", stats["non_top50_buy_intent_count"] == 0, "", stats["non_top50_buy_intent_count"], 0),
        check("sell_intents_rank_gt_buffer_only", stats["sell_rank_lte_buffer_count"] == 0, "", stats["sell_rank_lte_buffer_count"], 0),
        check("max_holding_count_lte_target", stats["max_holding_count"] <= TARGET_HOLDING_COUNT, "", stats["max_holding_count"], TARGET_HOLDING_COUNT),
        check("missing_holding_visibility_zero", stats["missing_visibility_days"] == 0, "", stats["missing_visibility_days"], 0),
        check("strategy_decision_audit_pass", all(row["status"] == "pass" for row in audit_rows), "", "", "all pass"),
    ]
    return all(row["status"] == "pass" for row in checks), checks


def validator_payload(verdict: str, bridge_checks: list[dict[str, Any]], order_checks: list[dict[str, Any]], bridge_ok: bool, order_ok: bool) -> dict[str, Any]:
    return {
        "artifact_type": "validator_report",
        "phase": PHASE,
        "ok": verdict == VERDICT_PASS and bridge_ok and order_ok,
        "verdict": verdict,
        "bridge_ready": bridge_ok,
        "order_intent_ready": order_ok,
        "checks": {
            "bridge": bridge_checks,
            "order_intent": order_checks,
        },
    }


def write_report(
    created_at: str,
    verdict: str,
    bridge_dir: Path,
    order_dir: Path,
    bridge_stats: dict[str, Any],
    order_stats: dict[str, Any],
    bridge_manifest_rel: str,
    order_manifest_rel: str,
) -> None:
    can_enter_p3 = verdict == VERDICT_PASS
    text = f"""---
created_at: {created_at}
phase: {PHASE}
strategy_rule: {STRATEGY_RULE}
readonly_only: true
simulation_only: true
production_candidate: true
production_allowed: false
not_default_candidate: true
not_published_latest: true
verdict: {verdict}
---

# POLICY_MTRP2_R_FULL_RANK_VISIBILITY_BRIDGE_AND_ORDER_INTENT_EXECUTION_REPORT_CN

## 1. Verdict

```text
{verdict}
```

Can enter P3 same-window readonly replay: `{str(can_enter_p3).lower()}`

## 2. Bridge Artifact

- path: `{rel(bridge_dir)}`
- manifest: `{bridge_manifest_rel}`
- source_lineage: `{SOURCE_LINEAGE}`
- source: `{rel(SOURCE_MANIFEST)}`
- row_count: `{bridge_stats['row_count']}`
- date_range: `{bridge_stats['date_start']}..{bridge_stats['date_end']}`
- daily_min_row_count: `{bridge_stats['daily_min_row_count']}`
- top50_row_count: `{bridge_stats['top50_row_count']}`
- non_top50_row_count: `{bridge_stats['non_top50_row_count']}`

Bridge 是 readonly production-candidate readiness 产物，不声明 production-ready，不发布 latest，不改默认链路。non-top50 行只保留 `full_qlib_rank` 可见性，`buy_score/raw_score/score_rank` 置空且 `ext_buy_ranking_allowed=false`。

## 3. OrderIntent Artifact

- path: `{rel(order_dir)}`
- manifest: `{order_manifest_rel}`
- order_intent_count: `{order_stats['buy_intent_count'] + order_stats['sell_intent_count']}`
- buy_intent_count: `{order_stats['buy_intent_count']}`
- sell_intent_count: `{order_stats['sell_intent_count']}`
- max_holding_count: `{order_stats['max_holding_count']}`
- date_range: `{bridge_stats['date_start']}..{bridge_stats['date_end']}`

规则固定：`max_sell_count=1`、`max_buy_count=1`、`target_holding_count=10`、`candidate_k=50`、`hold_rank_buffer=100`。卖出只针对当前持仓中 `full_qlib_rank > 100` 的最差标的；买入只允许 top50，排序为 `buy_score desc + full_qlib_rank asc + instrument asc`。

## 4. Boundary Statement

本阶段没有训练、推理或重算 LTR；没有读取 replay return、future label、future price 或 broker/order 数据作为输入；没有修改 production default、frontend/API/Agent/daily/latest/provider/PriceStore；没有输出 broker/order/quantity/target_weight/target_position。

## 5. P3 Readiness

```text
can_enter_p3 = {str(can_enter_p3).lower()}
```
"""
    write_text(REPORT_PATH, text)


def main() -> int:
    require_inputs()
    created_at = now_iso()
    this_run_id = run_id()
    bridge_dir = BRIDGE_BASE / this_run_id
    order_dir = ORDER_BASE / this_run_id

    source_manifest = read_json(SOURCE_MANIFEST)
    source_rows, source_fields = read_csv_rows(SOURCE_SIGNALS)
    dep = read_yaml(DEPENDENCY)
    lineage_ok, lineage_checks = source_lineage_checks(source_manifest)
    if not lineage_ok:
        verdict = VERDICT_STOP_LINEAGE
    elif dep.get("strategy_rule") != STRATEGY_RULE:
        verdict = VERDICT_FAIL
    else:
        verdict = VERDICT_PASS

    bridge_rows = build_bridge_rows(source_rows)
    bridge_stats = signal_stats(bridge_rows, SIGNAL_FIELDS)
    coverage_audit = build_coverage_audit(bridge_stats)
    signal_forbidden_audit = build_forbidden_field_audit(SIGNAL_FIELDS, "signals.csv")
    lineage_audit = build_lineage_audit(source_manifest, lineage_checks)
    bridge_ok, bridge_checks = validate_bridge(bridge_stats, lineage_ok, coverage_audit, signal_forbidden_audit)
    if verdict == VERDICT_PASS and not bridge_ok:
        verdict = VERDICT_FAIL

    bridge_output_files = {
        "manifest": rel(bridge_dir / "manifest.json"),
        "signals": rel(bridge_dir / "signals.csv"),
        "schema": rel(bridge_dir / "schema.json"),
        "coverage_audit": rel(bridge_dir / "coverage_audit.csv"),
        "forbidden_field_audit": rel(bridge_dir / "forbidden_field_audit.csv"),
        "lineage_audit": rel(bridge_dir / "lineage_audit.csv"),
        "validator_report": rel(bridge_dir / "validator_report.json"),
    }
    bridge_manifest = {
        "artifact_type": "model_signal_full_rank_visibility_bridge",
        "artifact_name": BRIDGE_NAME,
        "schema_version": "mtrp2_r_full_rank_visibility_bridge_v1",
        "phase": PHASE,
        "run_id": this_run_id,
        "created_at": created_at,
        "created_by": rel(Path(__file__)),
        "model_name": BRIDGE_NAME,
        "model_family": "ltr",
        "strategy_rule": STRATEGY_RULE,
        "production_candidate": True,
        "readonly_only": True,
        "simulation_only": True,
        "production_allowed": False,
        "not_default_candidate": True,
        "not_published_latest": True,
        "production_ready": False,
        "source_lineage": SOURCE_LINEAGE,
        "source_artifact": rel(SOURCE_MANIFEST),
        "source_signals": rel(SOURCE_SIGNALS),
        "source_research_only": bool(source_manifest.get("research_only")),
        "source_diagnostic_only": bool(source_manifest.get("diagnostic_only")),
        "window": {"start": WINDOW_START, "end": WINDOW_END},
        "row_count": bridge_stats["row_count"],
        "date_count": bridge_stats["date_count"],
        "candidate_k": CANDIDATE_K,
        "hold_rank_buffer": HOLD_RANK_BUFFER,
        "input_hashes": {
            rel(SOURCE_MANIFEST): sha256_file(SOURCE_MANIFEST),
            rel(SOURCE_SIGNALS): sha256_file(SOURCE_SIGNALS),
        },
        "capabilities": {
            "core_signal_v1": True,
            "candidate_boundary": "qlib_top50",
            "buy_ordering": "buy_score_desc_top50_only",
            "full_rank_exit": "full_qlib_rank",
            "full_rank_visibility_hold_buffer_100": True,
            "non_top50_buy_forbidden": True,
        },
        "ranking_usage": {
            "buy_ranking": "candidate_rank <= 50 and ext_buy_ranking_allowed=true",
            "hold_buffer": "full_qlib_rank visible for ranks beyond top50",
            "non_top50_rows": "visibility_only_for_hold_buffer",
        },
        "forbidden_actions": forbidden_action_audit(created_at)["actions"],
        "output_files": bridge_output_files,
    }

    write_csv(bridge_dir / "signals.csv", bridge_rows, SIGNAL_FIELDS)
    write_json(bridge_dir / "schema.json", bridge_schema())
    write_csv(bridge_dir / "coverage_audit.csv", coverage_audit, ["audit_name", "status", "value", "threshold", "details"])
    write_csv(
        bridge_dir / "forbidden_field_audit.csv",
        signal_forbidden_audit,
        ["audit_name", "artifact", "field_name", "field_category", "present", "used_for_ranking", "status", "details"],
    )
    write_csv(
        bridge_dir / "lineage_audit.csv",
        lineage_audit,
        ["audit_name", "status", "source_artifact", "source_research_only", "source_diagnostic_only", "source_lineage", "details"],
    )
    write_json(bridge_dir / "manifest.json", bridge_manifest)

    bridge_manifest_rel = rel(bridge_dir / "manifest.json")
    order_intents: list[dict[str, Any]] = []
    decision_audit: list[dict[str, Any]] = []
    order_stats = {
        "missing_visibility_days": 0,
        "max_holding_count": 0,
        "buy_intent_count": 0,
        "sell_intent_count": 0,
        "non_top50_buy_intent_count": 0,
        "sell_rank_lte_buffer_count": 0,
    }
    order_ok = False
    order_checks: list[dict[str, Any]] = []
    if bridge_ok and verdict == VERDICT_PASS:
        order_intents, decision_audit, order_stats = build_order_intents(bridge_rows, bridge_manifest_rel)
        order_ok, order_checks = validate_order_intents(order_intents, decision_audit, order_stats)
        if not order_ok:
            verdict = VERDICT_BRIDGE_ONLY
    else:
        order_checks = [check("order_intent_skipped_until_bridge_ready", False, "", "bridge_not_ready", "bridge_ready")]
        verdict = VERDICT_FAIL if verdict == VERDICT_PASS else verdict

    order_output_files = {
        "manifest": rel(order_dir / "manifest.json"),
        "order_intents": rel(order_dir / "order_intents.csv"),
        "schema": rel(order_dir / "schema.json"),
        "strategy_decision_audit": rel(order_dir / "strategy_decision_audit.csv"),
        "forbidden_action_audit": rel(order_dir / "forbidden_action_audit.json"),
        "validator_report": rel(order_dir / "validator_report.json"),
    }
    order_manifest = {
        "artifact_type": "order_intent",
        "schema_version": "mtrp2_r_order_intent_v1",
        "phase": PHASE,
        "run_id": this_run_id,
        "created_at": created_at,
        "created_by": rel(Path(__file__)),
        "strategy_rule": STRATEGY_RULE,
        "dependency": rel(DEPENDENCY),
        "signal_artifact": bridge_manifest_rel,
        "source_lineage": SOURCE_LINEAGE,
        "verdict": verdict,
        "readiness_pass": verdict == VERDICT_PASS,
        "can_enter_p3_same_window_baseline_replay": verdict == VERDICT_PASS,
        "readonly_only": True,
        "simulation_only": True,
        "production_candidate": True,
        "production_allowed": False,
        "not_default_candidate": True,
        "not_published_latest": True,
        "not_order": True,
        "not_target_position": True,
        "not_investment_advice": True,
        "max_buy_count": MAX_BUY_COUNT,
        "max_sell_count": MAX_SELL_COUNT,
        "target_holding_count": TARGET_HOLDING_COUNT,
        "candidate_k": CANDIDATE_K,
        "hold_rank_buffer": HOLD_RANK_BUFFER,
        "order_intent_count": len(order_intents),
        "buy_intent_count": order_stats["buy_intent_count"],
        "sell_intent_count": order_stats["sell_intent_count"],
        "portfolio_state_policy": "readonly_intent_state_from_prior_intents_no_execution_no_quantity",
        "forbidden_actions": forbidden_action_audit(created_at)["actions"],
        "output_files": order_output_files,
    }

    write_csv(order_dir / "order_intents.csv", order_intents, ORDER_FIELDS)
    decision_fields = [
        "signal_date",
        "status",
        "top50_row_count",
        "visible_row_count",
        "holding_count_before",
        "holding_count_after",
        "sell_intent_count",
        "buy_intent_count",
        "sold_instrument",
        "bought_instrument",
        "missing_visibility_count",
        "missing_visibility_instruments",
        "details",
    ]
    write_json(order_dir / "schema.json", order_schema())
    write_csv(order_dir / "strategy_decision_audit.csv", decision_audit, decision_fields)
    write_json(order_dir / "forbidden_action_audit.json", forbidden_action_audit(created_at))
    write_json(order_dir / "manifest.json", order_manifest)

    validator = validator_payload(verdict, bridge_checks, order_checks, bridge_ok, order_ok)
    write_json(bridge_dir / "validator_report.json", {
        "artifact_type": "validator_report",
        "phase": PHASE,
        "ok": bridge_ok,
        "verdict": verdict,
        "bridge_ready": bridge_ok,
        "checks": bridge_checks,
    })
    write_json(order_dir / "validator_report.json", validator)

    order_manifest_rel = rel(order_dir / "manifest.json")
    write_report(created_at, verdict, bridge_dir, order_dir, bridge_stats, order_stats, bridge_manifest_rel, order_manifest_rel)

    print(json.dumps({
        "verdict": verdict,
        "bridge_path": rel(bridge_dir),
        "order_intent_path": rel(order_dir),
        "bridge_rows": bridge_stats["row_count"],
        "order_intent_rows": len(order_intents),
        "date_range": f"{bridge_stats['date_start']}..{bridge_stats['date_end']}",
        "can_enter_p3": verdict == VERDICT_PASS,
        "report": rel(REPORT_PATH),
    }, ensure_ascii=False, indent=2))
    return 0 if verdict == VERDICT_PASS else 2


if __name__ == "__main__":
    raise SystemExit(main())
