#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
PHASE = "MTRP0_P2_PRODUCTION_CANDIDATE_ORDER_INTENT_READINESS"
STRATEGY_RULE = "top50_hold_rank_buffer_100"
VERDICT_PASS = "PASS_READY_ORDER_INTENT_ARTIFACT_BUILT"
VERDICT_STOP_VISIBILITY = "STOP_PRODUCTION_SIGNAL_FULL_RANK_VISIBILITY_MISSING"
VERDICT_STOP_CONTRACT = "STOP_READINESS_CONTRACT_FAILED"

PRODUCT_REGISTRY = ROOT / "configs/tw_product_artifact_registry.yaml"
MODULAR_REGISTRY = ROOT / "configs/tw_modular_registry.yaml"
REPLAY_POLICY = ROOT / "configs/tw_replay_window_policy.yaml"
DEPENDENCY = ROOT / "configs/strategy_dependencies/top50_hold_rank_buffer_100.yaml"
REPORT_PATH = (
    ROOT
    / "docs/tw_portfolio_decision_model/"
    / "POLICY_MTRP0_P2_PRODUCTION_CANDIDATE_ORDER_INTENT_EXECUTION_REPORT_CN.md"
)
OUT_BASE = ROOT / "data_tw/artifacts/strategies/top50_hold_rank_buffer_100"

TARGET_HOLDING_COUNT = 10
CANDIDATE_K = 50
HOLD_RANK_BUFFER = 100
MAX_BUY_COUNT = 1
MAX_SELL_COUNT = 1

REQUIRED_READ_FILES = [
    "docs/tw_portfolio_decision_model/POLICY_MTRC6_COORDINATOR_DECISION_AND_PRODUCTION_GATE_CN.md",
    "docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md",
    "docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md",
    "docs/tw_modular_contracts/STRATEGY_DEPENDENCY_CONTRACT_CN.md",
    "docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md",
    "docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md",
    "docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md",
    "docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md",
    "docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md",
    "configs/tw_product_artifact_registry.yaml",
    "configs/tw_modular_registry.yaml",
    "configs/tw_replay_window_policy.yaml",
]

REQUIRED_SIGNAL_FIELDS = [
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
]

FORBIDDEN_EXACT_FIELDS = {
    "execution_date",
    "execution_price",
    "execution_quantity",
    "quantity_to_buy",
    "quantity_to_sell",
    "shares",
    "lots",
    "target_position",
    "target_weight",
    "allocation_weight",
    "commission",
    "fee",
    "tax",
    "cash",
    "cash_after",
    "nav",
    "equity",
    "daily_return",
    "realized_pnl",
    "unrealized_pnl",
    "replay_return",
    "broker",
    "broker_order_id",
    "order_id",
    "quick_trade",
    "provider_publish_status",
    "accepted_latest_status",
    "ltr_relevance_label",
    "relevance_10d_top_heavy",
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
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


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


def read_csv_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader), list(reader.fieldnames or [])


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def parse_float(value: Any) -> float:
    try:
        text = str(value).strip()
        if text == "":
            return float("nan")
        return float(text)
    except Exception:
        return float("nan")


def is_nan(value: float) -> bool:
    return value != value


def format_rank(value: Any) -> str:
    number = parse_float(value)
    if is_nan(number):
        return ""
    if number.is_integer():
        return str(int(number))
    return f"{number:.6f}".rstrip("0").rstrip(".")


def forbidden_names_present(names: list[str] | set[str]) -> list[str]:
    present: list[str] = []
    for name in names:
        lowered = str(name).strip().lower()
        if lowered in FORBIDDEN_EXACT_FIELDS or any(lowered.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
            present.append(str(name))
    return sorted(set(present))


def check_row(name: str, ok: bool, observed: Any, expected: Any, details: str) -> dict[str, Any]:
    return {
        "audit_name": name,
        "status": "pass" if ok else "fail",
        "observed": observed,
        "expected": expected,
        "details": details,
    }


def require_read_files() -> None:
    missing = [ROOT / item for item in REQUIRED_READ_FILES if not (ROOT / item).exists()]
    missing.append(DEPENDENCY) if not DEPENDENCY.exists() else None
    if missing:
        raise FileNotFoundError("Missing required input(s): " + ", ".join(rel(path) for path in missing))
    for item in REQUIRED_READ_FILES:
        (ROOT / item).read_text(encoding="utf-8")
    DEPENDENCY.read_text(encoding="utf-8")


def production_signal_manifest_path(signal_date: str) -> Path:
    product = read_yaml(PRODUCT_REGISTRY)
    signal_root = resolve(product["artifacts"]["signal_root"])
    subdir = product["artifacts"].get("model_b_preferred_subdir", "model_b_yz2")
    return signal_root / signal_date / subdir / "manifest.json"


def manifest_file(manifest: dict[str, Any], key: str, default: str) -> str:
    files = manifest.get("files") or manifest.get("output_files") or {}
    return str(files.get(key, default))


def load_signal_artifact(signal_manifest_path: Path) -> tuple[dict[str, Any], Path, list[dict[str, str]], list[str]]:
    manifest = read_json(signal_manifest_path)
    signal_path = resolve(signal_manifest_path.parent / manifest_file(manifest, "signals", "signals.csv"))
    if not signal_path.exists():
        signal_path = signal_manifest_path.parent / manifest_file(manifest, "signals", "signals.csv")
    rows, fields = read_csv_rows(signal_path)
    return manifest, signal_path, rows, fields


def signal_stats(rows: list[dict[str, str]], fields: list[str]) -> dict[str, Any]:
    dates = sorted({str(row.get("date", "")) for row in rows if row.get("date", "")})
    key_counter = Counter((row.get("date", ""), row.get("instrument", "")) for row in rows)
    duplicate_count = sum(count - 1 for count in key_counter.values() if count > 1)
    candidate_ranks = [parse_float(row.get("candidate_rank", "")) for row in rows]
    full_ranks = [parse_float(row.get("full_qlib_rank", "")) for row in rows]
    visible_candidate_ranks = [rank for rank in candidate_ranks if not is_nan(rank)]
    visible_full_ranks = [rank for rank in full_ranks if not is_nan(rank)]
    top50_count = sum(1 for rank in visible_candidate_ranks if rank <= CANDIDATE_K)
    non_top50_count = sum(1 for rank in visible_candidate_ranks if rank > CANDIDATE_K)
    max_full_rank = max(visible_full_ranks) if visible_full_ranks else float("nan")
    max_candidate_rank = max(visible_candidate_ranks) if visible_candidate_ranks else float("nan")
    visibility_columns = [
        field for field in fields
        if "visibility" in field.lower() or "holding" in field.lower() or "portfolio" in field.lower()
    ]
    return {
        "row_count": len(rows),
        "field_count": len(fields),
        "date_count": len(dates),
        "date_start": dates[0] if dates else "",
        "date_end": dates[-1] if dates else "",
        "duplicate_date_instrument": duplicate_count,
        "top50_count": top50_count,
        "non_top50_count": non_top50_count,
        "max_candidate_rank": "" if is_nan(max_candidate_rank) else int(max_candidate_rank),
        "max_full_qlib_rank": "" if is_nan(max_full_rank) else int(max_full_rank),
        "visibility_columns": visibility_columns,
        "forbidden_fields": forbidden_names_present(set(fields)),
    }


def dependency_readiness(dep: dict[str, Any]) -> list[dict[str, Any]]:
    required_flags = {
        "readonly_only": True,
        "simulation_only": True,
        "diagnostic_only": False,
        "research_only": False,
        "production_allowed": False,
        "production_candidate": True,
        "frontend_selectable": False,
        "production_default": False,
        "not_order": True,
        "not_target_position": True,
        "not_investment_advice": True,
    }
    rows: list[dict[str, Any]] = []
    rows.append(check_row("dependency_strategy_rule", dep.get("strategy_rule") == STRATEGY_RULE, dep.get("strategy_rule"), STRATEGY_RULE, "new production-candidate strategy dependency"))
    for key, expected in required_flags.items():
        rows.append(check_row(f"dependency_{key}", dep.get(key) is expected, dep.get(key), expected, "required production-candidate boundary flag"))
    for key, expected in {
        "max_buy_count": MAX_BUY_COUNT,
        "max_sell_count": MAX_SELL_COUNT,
        "target_holding_count": TARGET_HOLDING_COUNT,
        "candidate_k": CANDIDATE_K,
        "hold_rank_buffer": HOLD_RANK_BUFFER,
    }.items():
        rows.append(check_row(f"dependency_{key}", int(dep.get(key) or -1) == expected, dep.get(key), expected, "strategy parameter freeze"))
    required = set(REQUIRED_SIGNAL_FIELDS)
    observed = set(dep.get("required_core_fields") or [])
    rows.append(check_row("dependency_required_core_fields", required.issubset(observed), "|".join(sorted(observed)), "|".join(sorted(required)), "ModelSignal core field dependency"))
    actions = set(dep.get("forbidden_actions") or [])
    for action in [
        "read_mtrc_private_signal_csv",
        "read_replay_return_as_input",
        "provider_publish",
        "accepted_latest_switch",
        "quick_trade",
        "write_broker_order",
        "output_target_weight_or_position",
    ]:
        rows.append(check_row(f"dependency_forbids_{action}", action in actions, action if action in actions else "", action, "forbidden action must be declared"))
    return rows


def registry_readiness() -> list[dict[str, Any]]:
    product = read_yaml(PRODUCT_REGISTRY)
    modular = read_yaml(MODULAR_REGISTRY)
    replay = read_yaml(REPLAY_POLICY)
    selectable = (modular.get("strategies") or {}).get("production_selectable") or {}
    return [
        check_row("product_default_strategy_unchanged", product.get("strategies", {}).get("default_strategy_rule") == "top50_exit_one_worst_sell", product.get("strategies", {}).get("default_strategy_rule"), "top50_exit_one_worst_sell", "task does not change production default"),
        check_row("replay_policy_default_strategy_unchanged", replay.get("default_strategy_rule") == "top50_exit_one_worst_sell", replay.get("default_strategy_rule"), "top50_exit_one_worst_sell", "task does not change replay policy default"),
        check_row("new_strategy_not_production_selectable", STRATEGY_RULE not in selectable, STRATEGY_RULE if STRATEGY_RULE in selectable else "", "absent", "task does not modify registry selectable/default"),
    ]


def signal_readiness(
    signal_manifest_path: Path,
    manifest: dict[str, Any],
    signal_path: Path,
    rows: list[dict[str, str]],
    fields: list[str],
    stats: dict[str, Any],
) -> list[dict[str, Any]]:
    missing_fields = sorted(set(REQUIRED_SIGNAL_FIELDS) - set(fields))
    expected_path = "data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_b_yz2/manifest.json"
    max_full = parse_float(stats["max_full_qlib_rank"])
    non_top50_visible = int(stats["non_top50_count"] or 0) > 0
    only_top50 = int(stats["row_count"] or 0) == CANDIDATE_K and int(stats["top50_count"] or 0) == CANDIDATE_K
    has_visibility_bridge = bool(stats["visibility_columns"]) or non_top50_visible
    return [
        check_row("production_signal_manifest_path", rel(signal_manifest_path) == expected_path, rel(signal_manifest_path), expected_path, "uses current production product registry signal lineage"),
        check_row("signal_file_exists", signal_path.exists(), rel(signal_path), "exists", "signals.csv must be readable"),
        check_row("signal_required_core_fields", not missing_fields, "|".join(missing_fields), "none", "ModelSignalArtifact core fields"),
        check_row("signal_duplicate_date_instrument", stats["duplicate_date_instrument"] == 0, stats["duplicate_date_instrument"], 0, "ModelSignal unique key"),
        check_row("signal_forbidden_fields_absent", not stats["forbidden_fields"], "|".join(stats["forbidden_fields"]), "none", "no future/position/execution/broker fields"),
        check_row("signal_manifest_row_count_matches", int(manifest.get("row_count") or len(rows)) == len(rows), len(rows), manifest.get("row_count"), "manifest row count consistency"),
        check_row("signal_candidate_k_matches_top50", int(manifest.get("candidate_k") or CANDIDATE_K) == CANDIDATE_K, manifest.get("candidate_k"), CANDIDATE_K, "production top50 candidate boundary"),
        check_row("signal_not_research_mtrc_private", "policy_mtr_research_only_continuation" not in rel(signal_path) and "mtrc1d" not in rel(signal_path).lower(), rel(signal_path), "production ModelSignalArtifact", "do not read MTRC private signal CSV"),
        check_row("full_rank_visibility_min_rank_100", (not is_nan(max_full)) and max_full >= HOLD_RANK_BUFFER, stats["max_full_qlib_rank"], f">={HOLD_RANK_BUFFER}", "hold_rank_buffer_100 needs ranks through 100"),
        check_row("non_top50_visibility_rows_present", non_top50_visible, stats["non_top50_count"], ">0", "sell boundary cannot be evaluated from top50-only rows"),
        check_row("not_only_top50_visible", not only_top50, f"row_count={stats['row_count']};top50_count={stats['top50_count']}", "not exactly top50-only", "STOP if production signal only exposes qlib top50"),
        check_row("holding_visibility_bridge_present", has_visibility_bridge, ",".join(stats["visibility_columns"]), "full-rank rows or explicit holding visibility bridge", "do not assume held names are visible when absent"),
    ]


def load_portfolio_state(path: Path | None) -> tuple[list[dict[str, Any]], str]:
    if path is None:
        return [], ""
    rows, fields = read_csv_rows(path)
    missing = sorted({"asof_date", "instrument", "quantity", "current_holding_flag"} - set(fields))
    if missing:
        raise ValueError("PortfolioState missing required field(s): " + ", ".join(missing))
    holdings = []
    for row in rows:
        if str(row.get("current_holding_flag", "")).strip().lower() not in {"true", "1", "yes"}:
            continue
        if parse_float(row.get("quantity", "")) <= 0:
            continue
        holdings.append(row)
    return holdings, rel(path)


def build_order_intents(
    signal_manifest_rel: str,
    rows: list[dict[str, str]],
    portfolio_rows: list[dict[str, Any]],
    portfolio_artifact: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not rows:
        return [], []
    signal_date = sorted({row["date"] for row in rows})[-1]
    day_rows = [row for row in rows if row.get("date") == signal_date]
    by_instrument = {row["instrument"]: row for row in day_rows}
    holdings = sorted({row["instrument"] for row in portfolio_rows})
    missing_holding_visibility = sorted(inst for inst in holdings if inst not in by_instrument)
    if missing_holding_visibility:
        audit = [{
            "signal_date": signal_date,
            "audit_name": "missing_holding_visibility",
            "status": "stop",
            "instrument": ",".join(missing_holding_visibility),
            "details": "holding rank absent; do not assume still visible",
        }]
        return [], audit

    sell_candidates = []
    for inst in holdings:
        row = by_instrument[inst]
        full_rank = parse_float(row.get("full_qlib_rank"))
        if not is_nan(full_rank) and full_rank > HOLD_RANK_BUFFER:
            sell_candidates.append(row)
    sell_candidates.sort(key=lambda row: (-parse_float(row.get("full_qlib_rank")), row.get("instrument", "")))
    sell_rows = sell_candidates[:MAX_SELL_COUNT]
    sold = {row["instrument"] for row in sell_rows}
    after_sell_holdings = set(holdings) - sold

    buy_candidates = [
        row for row in day_rows
        if parse_float(row.get("candidate_rank")) <= CANDIDATE_K and row["instrument"] not in after_sell_holdings
    ]
    buy_candidates.sort(
        key=lambda row: (-parse_float(row.get("buy_score")), parse_float(row.get("full_qlib_rank")), row.get("instrument", ""))
    )
    open_slots = max(0, TARGET_HOLDING_COUNT - len(after_sell_holdings))
    buy_rows = buy_candidates[: min(MAX_BUY_COUNT, open_slots)]

    intents: list[dict[str, Any]] = []
    for row in sell_rows:
        intents.append(make_intent(row, "sell", "hold_rank_buffer_100_sell_worst_visible_holding", "", True, signal_manifest_rel, portfolio_artifact))
    for row in buy_rows:
        intents.append(make_intent(row, "buy", "top50_buy_score_best_unheld", row.get("score_rank", ""), False, signal_manifest_rel, portfolio_artifact))
    audit = [{
        "signal_date": signal_date,
        "audit_name": "strategy_decision",
        "status": "pass",
        "holding_count_before": len(holdings),
        "sell_intent_count": len(sell_rows),
        "buy_intent_count": len(buy_rows),
        "missing_holding_visibility_count": 0,
        "details": "sell full_qlib_rank > 100; buy top50 unheld by buy_score desc/full_qlib_rank asc/instrument asc",
    }]
    return intents, audit


def make_intent(
    row: dict[str, str],
    action: str,
    reason: str,
    buy_rank: Any,
    current_holding: bool,
    signal_manifest_rel: str,
    portfolio_artifact: str,
) -> dict[str, Any]:
    return {
        "signal_date": row["date"],
        "instrument": row["instrument"],
        "intent_action": action,
        "intent_reason": reason,
        "strategy_rule": STRATEGY_RULE,
        "candidate_rank": format_rank(row.get("candidate_rank")),
        "buy_rank": buy_rank,
        "full_qlib_rank": format_rank(row.get("full_qlib_rank")),
        "max_buy_count": MAX_BUY_COUNT,
        "max_sell_count": MAX_SELL_COUNT,
        "model_name": row.get("model_name", ""),
        "signal_artifact": signal_manifest_rel,
        "portfolio_state_artifact": portfolio_artifact,
        "current_holding_flag": bool_text(current_holding),
        "target_holding_count": TARGET_HOLDING_COUNT,
        "candidate_k": CANDIDATE_K,
        "hold_rank_buffer": HOLD_RANK_BUFFER,
        "tie_breaker": "full_qlib_rank_asc,instrument_asc",
        "readonly_only": "true",
        "simulation_only": "true",
        "production_allowed": "false",
        "production_candidate": "true",
        "not_order": "true",
        "not_target_position": "true",
        "not_investment_advice": "true",
    }


def schema_payload(order_intent_generated: bool) -> dict[str, Any]:
    return {
        "artifact_type": "schema",
        "schema_version": "mtrp0_p2_production_candidate_order_intent_v1",
        "strategy_rule": STRATEGY_RULE,
        "order_intent_generated": order_intent_generated,
        "required_order_intent_fields": ORDER_FIELDS,
        "allowed_actions": ["buy", "sell", "hold", "skip"],
        "stop_fields": ["verdict", "blocker", "next_required_input"],
        "forbidden_order_intent_fields": sorted(FORBIDDEN_EXACT_FIELDS),
    }


def forbidden_action_audit(created_at: str) -> dict[str, Any]:
    actions = {
        "train_model": False,
        "tune_model": False,
        "score_recompute": False,
        "read_mtrc_private_signal_csv": False,
        "read_replay_return_as_input": False,
        "provider_publish": False,
        "accepted_latest_switch": False,
        "frontend_or_api_or_agent_change": False,
        "daily_auto_latest_pointer_switch": False,
        "formal_pricestore_write": False,
        "broker_connection": False,
        "quick_trade": False,
        "real_order": False,
        "target_weight_or_target_position_output": False,
    }
    return {
        "artifact_type": "forbidden_action_audit",
        "phase": PHASE,
        "created_at": created_at,
        "status": "pass",
        "actions": actions,
        "details": "readonly/simulation artifact build only; no production default/selectable/latest/provider/broker action",
    }


def validate_outputs(
    verdict: str,
    readiness_rows: list[dict[str, Any]],
    order_intents: list[dict[str, Any]],
    output_files: dict[str, str],
) -> dict[str, Any]:
    readiness_failures = [row for row in readiness_rows if row["status"] != "pass"]
    fields = set(order_intents[0].keys()) if order_intents else set()
    forbidden_output_fields = forbidden_names_present(fields)
    checks = [
        {"name": "readiness_verdict_consistent", "status": "pass" if (verdict != VERDICT_PASS or not readiness_failures) else "fail", "details": verdict},
        {"name": "stop_has_no_order_intents_csv", "status": "pass" if (verdict == VERDICT_PASS or "order_intents" not in output_files) else "fail", "details": "STOP artifact must not masquerade as OrderIntentArtifact"},
        {"name": "order_intent_forbidden_fields_absent", "status": "pass" if not forbidden_output_fields else "fail", "details": "|".join(forbidden_output_fields)},
        {"name": "daily_buy_count_lte_1", "status": "pass", "details": ""},
        {"name": "daily_sell_count_lte_1", "status": "pass", "details": ""},
    ]
    if order_intents:
        buy_counts = Counter(row["signal_date"] for row in order_intents if row["intent_action"] == "buy")
        sell_counts = Counter(row["signal_date"] for row in order_intents if row["intent_action"] == "sell")
        checks[-2] = {"name": "daily_buy_count_lte_1", "status": "pass" if max(buy_counts.values() or [0]) <= 1 else "fail", "details": str(dict(buy_counts))}
        checks[-1] = {"name": "daily_sell_count_lte_1", "status": "pass" if max(sell_counts.values() or [0]) <= 1 else "fail", "details": str(dict(sell_counts))}
    ok = all(row["status"] == "pass" for row in checks)
    return {
        "artifact_type": "validator_report",
        "phase": PHASE,
        "ok": ok,
        "verdict": verdict,
        "readiness_pass": verdict == VERDICT_PASS,
        "order_intent_generated": bool(order_intents),
        "readiness_failure_count": len(readiness_failures),
        "checks": checks,
    }


def choose_verdict(readiness_rows: list[dict[str, Any]]) -> str:
    failed_names = {row["audit_name"] for row in readiness_rows if row["status"] != "pass"}
    visibility_failures = {
        "full_rank_visibility_min_rank_100",
        "non_top50_visibility_rows_present",
        "not_only_top50_visible",
        "holding_visibility_bridge_present",
    }
    if failed_names & visibility_failures:
        return VERDICT_STOP_VISIBILITY
    if failed_names:
        return VERDICT_STOP_CONTRACT
    return VERDICT_PASS


def write_report(
    created_at: str,
    out_dir: Path,
    verdict: str,
    signal_manifest: Path,
    signal_stats_payload: dict[str, Any],
    readiness_rows: list[dict[str, Any]],
    order_intents: list[dict[str, Any]],
    output_files: dict[str, str],
) -> None:
    readiness_pass = verdict == VERDICT_PASS
    blocker = "none" if readiness_pass else "production ModelSignalArtifact only exposes top50; full-rank/holding visibility for hold_rank_buffer_100 is missing"
    failed = [row for row in readiness_rows if row["status"] != "pass"]
    failed_lines = "\n".join(
        f"- {row['audit_name']}: observed={row['observed']} expected={row['expected']}"
        for row in failed
    ) or "- none"
    files_lines = "\n".join(f"- `{path}`" for path in output_files.values())
    text = f"""---
created_at: {created_at}
phase: {PHASE}
strategy_rule: {STRATEGY_RULE}
readonly_only: true
simulation_only: true
production_allowed: false
production_candidate: true
verdict: {verdict}
---

# POLICY_MTRP0_P2_PRODUCTION_CANDIDATE_ORDER_INTENT_EXECUTION_REPORT_CN

## 1. Verdict

```text
{verdict}
```

Readiness pass: `{str(readiness_pass).lower()}`
OrderIntent generated: `{str(bool(order_intents)).lower()}`
Can enter P3 same-window baseline replay: `{str(readiness_pass and bool(order_intents)).lower()}`

## 2. Input

- strategy dependency: `configs/strategy_dependencies/top50_hold_rank_buffer_100.yaml`
- production signal manifest: `{rel(signal_manifest)}`
- signal rows: `{signal_stats_payload['row_count']}`
- top50 rows: `{signal_stats_payload['top50_count']}`
- non-top50 rows: `{signal_stats_payload['non_top50_count']}`
- max full_qlib_rank visible: `{signal_stats_payload['max_full_qlib_rank']}`

## 3. Blocker

```text
{blocker}
```

Failed readiness checks:

{failed_lines}

## 4. Boundary Statement

本阶段没有修改 `configs/tw_product_artifact_registry.yaml`、`configs/tw_modular_registry.yaml` 或 `configs/tw_replay_window_policy.yaml` 的默认策略/selectable。
本阶段没有修改 frontend/API/Agent/daily latest pointer，没有训练/推理/重算 LTR，没有 provider refresh/publish，没有 accepted latest switch，没有正式 PriceStore 写入。
本阶段没有 broker、quick-trade、real order、target_weight、target_position、quantity 输出，也没有读取 replay return 或 MTRC 私有 signal CSV 作为 production-candidate runtime 输入。

## 5. Next Required Input

若要进入 P2 OrderIntent build 和 P3 same-window baseline replay，需要生产 `ModelSignalArtifact` 增加以下之一：

1. full-rank rows 至少覆盖 `full_qlib_rank <= 100`，并能让当前持仓查到当日 rank；
2. daily signal artifact 增加持仓可见行/holding visibility bridge，且这些行只用于卖出边界审计，不得扩大买入 top50 universe。

## 6. Files

{files_lines}
"""
    write_text(REPORT_PATH, text)


def main() -> int:
    parser = argparse.ArgumentParser(description="MTRP0-P2 production-candidate readiness/order-intent builder.")
    parser.add_argument("--signal-date", default="2026-06-17")
    parser.add_argument("--portfolio-state", default="", help="Optional standard PortfolioState CSV; only used after readiness passes.")
    args = parser.parse_args()

    require_read_files()
    created_at = now_iso()
    run_id = "mtrp0_p2_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = OUT_BASE / run_id

    dep = read_yaml(DEPENDENCY)
    signal_manifest_path = production_signal_manifest_path(args.signal_date)
    signal_manifest, signal_path, signal_rows, signal_fields = load_signal_artifact(signal_manifest_path)
    stats = signal_stats(signal_rows, signal_fields)

    readiness_rows: list[dict[str, Any]] = []
    readiness_rows.extend(dependency_readiness(dep))
    readiness_rows.extend(registry_readiness())
    readiness_rows.extend(signal_readiness(signal_manifest_path, signal_manifest, signal_path, signal_rows, signal_fields, stats))
    verdict = choose_verdict(readiness_rows)

    portfolio_rows: list[dict[str, Any]] = []
    portfolio_artifact = ""
    order_intents: list[dict[str, Any]] = []
    decision_audit: list[dict[str, Any]] = []
    if verdict == VERDICT_PASS:
        portfolio_path = resolve(args.portfolio_state) if args.portfolio_state else None
        portfolio_rows, portfolio_artifact = load_portfolio_state(portfolio_path)
        if not portfolio_artifact:
            readiness_rows.append(check_row("portfolio_state_supplied", False, "", "standard PortfolioState CSV", "OrderIntent build requires explicit current holdings; no assumed empty portfolio"))
            verdict = VERDICT_STOP_CONTRACT
        else:
            order_intents, decision_audit = build_order_intents(rel(signal_manifest_path), signal_rows, portfolio_rows, portfolio_artifact)
            if not order_intents and decision_audit and decision_audit[0].get("status") == "stop":
                readiness_rows.append(check_row("holding_visibility_for_portfolio_state", False, decision_audit[0].get("instrument", ""), "all holdings visible", "holding rank absent; stop instead of assuming visibility"))
                verdict = VERDICT_STOP_VISIBILITY

    if verdict != VERDICT_PASS:
        decision_audit = [{
            "signal_date": stats["date_end"],
            "audit_name": "readiness_stop",
            "status": "stop",
            "verdict": verdict,
            "strategy_rule": STRATEGY_RULE,
            "details": "OrderIntentArtifact not generated because production signal lacks full-rank/holding visibility required by hold_rank_buffer_100.",
        }]
        order_intents = []

    output_files = {
        "manifest": rel(out_dir / "manifest.json"),
        "readiness_audit": rel(out_dir / "readiness_audit.csv"),
        "strategy_decision_audit": rel(out_dir / "strategy_decision_audit.csv"),
        "schema": rel(out_dir / "schema.json"),
        "forbidden_action_audit": rel(out_dir / "forbidden_action_audit.json"),
        "validator_report": rel(out_dir / "validator_report.json"),
        "stop_artifact": rel(out_dir / "stop_artifact.json"),
    }
    if order_intents:
        output_files["order_intents"] = rel(out_dir / "order_intents.csv")
        write_csv(out_dir / "order_intents.csv", order_intents, ORDER_FIELDS)
        output_files.pop("stop_artifact", None)

    validator = validate_outputs(verdict, readiness_rows, order_intents, output_files)
    forbidden_audit = forbidden_action_audit(created_at)
    stop_artifact = {
        "artifact_type": "production_candidate_order_intent_stop_artifact",
        "phase": PHASE,
        "strategy_rule": STRATEGY_RULE,
        "verdict": verdict,
        "readiness_pass": verdict == VERDICT_PASS,
        "order_intent_generated": bool(order_intents),
        "blocker": "" if verdict == VERDICT_PASS else "production signal lacks full-rank/holding visibility for hold_rank_buffer_100",
        "next_required_input": "production ModelSignalArtifact full-rank rows through rank 100 or explicit holding visibility bridge",
    }
    manifest = {
        "artifact_type": "production_candidate_order_intent_readiness" if not order_intents else "order_intent",
        "schema_version": "mtrp0_p2_production_candidate_order_intent_v1",
        "phase": PHASE,
        "run_id": run_id,
        "created_at": created_at,
        "strategy_rule": STRATEGY_RULE,
        "source_research_mechanism": "M2_hold_rank_buffer_100",
        "signal_artifact": rel(signal_manifest_path),
        "signal_file": rel(signal_path),
        "dependency": rel(DEPENDENCY),
        "portfolio_state_artifact": portfolio_artifact,
        "verdict": verdict,
        "readiness_pass": verdict == VERDICT_PASS,
        "order_intent_generated": bool(order_intents),
        "can_enter_p3_same_window_baseline_replay": verdict == VERDICT_PASS and bool(order_intents),
        "readonly_only": True,
        "simulation_only": True,
        "production_allowed": False,
        "production_candidate": True,
        "frontend_selectable": False,
        "production_default": False,
        "not_order": True,
        "not_target_position": True,
        "not_investment_advice": True,
        "no_training": True,
        "no_tuning": True,
        "no_score_recompute": True,
        "no_provider_publish": True,
        "no_accepted_latest_switch": True,
        "no_broker_order": True,
        "signal_stats": stats,
        "output_files": output_files,
    }

    readiness_fields = ["audit_name", "status", "observed", "expected", "details"]
    decision_fields = sorted({key for row in decision_audit for key in row.keys()}) or ["audit_name", "status", "details"]
    write_csv(out_dir / "readiness_audit.csv", readiness_rows, readiness_fields)
    write_csv(out_dir / "strategy_decision_audit.csv", decision_audit, decision_fields)
    write_json(out_dir / "schema.json", schema_payload(bool(order_intents)))
    write_json(out_dir / "forbidden_action_audit.json", forbidden_audit)
    if not order_intents:
        write_json(out_dir / "stop_artifact.json", stop_artifact)
    write_json(out_dir / "manifest.json", manifest)
    write_json(out_dir / "validator_report.json", validator)
    write_report(created_at, out_dir, verdict, signal_manifest_path, stats, readiness_rows, order_intents, output_files)

    print(json.dumps({
        "verdict": verdict,
        "readiness_pass": verdict == VERDICT_PASS,
        "order_intent_generated": bool(order_intents),
        "artifact_dir": rel(out_dir),
        "report": rel(REPORT_PATH),
    }, ensure_ascii=False, indent=2))
    return 0 if validator["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
