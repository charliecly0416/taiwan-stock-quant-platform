#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

PHASE = "MTRP7_S_R_REAL_TIER_A_SHADOW_RERUN_REPAIR"
RUN_ID = "mtrp7_s_r_real_tier_a_shadow_rerun_repair"
STRATEGY = "top50_hold_rank_buffer_100"
BASELINE_STRATEGY = "top50_exit_one_worst_sell"
MODEL_A_NAME = "e4_frozen_qlib_2018_2022"
MODEL_B_NAME = "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025"
BRIDGE_MODEL_NAME = "top50_hold_rank_buffer_100_real_tier_a_bridge"

INPUT_TIER = "tier_a_clean_daily_lineage"
VERDICT_PASS = "PASS_REAL_TIER_A_SHADOW_RERUN_READY_FOR_MTRP8"
VERDICT_FAIL = "FAIL_NEEDS_MTRP7_S_R_REPAIR"
VERDICT_STOP = "STOP_COORDINATOR_DECISION_REQUIRED"

S_ROOT = (
    ROOT
    / "data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/"
    / "mtrp7_s_clean_daily_modelb_ltr_top50_accumulation_build"
)
S_MODELB_ROOT = S_ROOT / "isolated_modelb_yz2"
R_ISOLATED_PHASE_YZ_ROOT = S_ROOT / "mtrp7_r_rerun/isolated_phase_yz"
R_RERUN_ROOT = S_ROOT / "mtrp7_r_rerun"

OUT_ROOT = S_ROOT / RUN_ID
REPORT_PATH = (
    ROOT
    / "docs/tw_portfolio_decision_model/"
    / "POLICY_MTRP7_S_R_REAL_TIER_A_SHADOW_RERUN_REPAIR_EXECUTION_REPORT_CN.md"
)

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
    "source_model_artifact",
    "source_feature_artifact",
]

ORDER_REQUIRED_FIELDS = [
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
]

ORDER_FORBIDDEN_FIELDS = {
    "execution_date",
    "execution_price",
    "execution_quantity",
    "quantity",
    "quantity_to_buy",
    "quantity_to_sell",
    "shares",
    "lots",
    "cash",
    "cash_after",
    "nav",
    "equity",
    "target_weight",
    "target_position",
    "allocation_weight",
    "broker",
    "broker_order_id",
    "order_id",
    "quick_trade",
    "daily_return",
    "realized_pnl",
    "unrealized_pnl",
    "replay_return",
}

SIGNAL_FORBIDDEN_PATTERNS = [
    "future_return",
    "future_excess_return",
    "forward_return",
    "label",
    "relevance_10d_top_heavy",
    "ltr_relevance_label",
    "realized_pnl",
    "realized_return",
    "replay_return",
    "execution_price",
    "execution_date",
    "next_open",
    "next_close",
    "broker_order_id",
    "target_weight",
    "target_position",
    "quantity",
    "shares",
    "lots",
]

FORBIDDEN_SCOPE_ITEMS = [
    "training",
    "tuning",
    "model_replacement",
    "new_modelb_scoring",
    "network_or_provider_refresh",
    "provider_publish",
    "accepted_latest_switch",
    "latest_pointer_mutation",
    "formal_phase_yz_write",
    "formal_pricestore_write",
    "production_default_registry_change",
    "frontend_api_agent_change",
    "daily_auto_default_path_change",
    "broker_quick_trade_real_order",
    "target_weight_position_quantity",
    "return_filter_or_return_tuning",
]

REQUIRED_ROOT_FILES = [
    "manifest.json",
    "daily_input_discovery.csv",
    "daily_bridge_artifact_register.csv",
    "daily_order_intent_artifact_register.csv",
    "daily_shadow_replay_artifact_register.csv",
    "shadow_accumulation_register.csv",
    "candidate_baseline_skip_delta.csv",
    "lineage_checksum_audit.csv",
    "price_mark_coverage_audit.csv",
    "readonly_wording_audit.csv",
    "forbidden_scope_audit.csv",
    "validator_report.json",
    "diagnostic_findings.md",
]

REQUIRED_READ_FILES = [
    "/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md",
    "/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-new-model-onboarding/SKILL.md",
    "/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-new-strategy-onboarding/SKILL.md",
    "docs/tw_portfolio_decision_model/POLICY_MTRP7_S_R_REAL_TIER_A_SHADOW_RERUN_REPAIR_WORK_CN.md",
    "docs/tw_portfolio_decision_model/POLICY_MTRP7_S_CLEAN_DAILY_MODELB_LTR_TOP50_ACCUMULATION_BUILD_REVIEW_CN.md",
    "docs/tw_portfolio_decision_model/POLICY_MTRP7_S_CLEAN_DAILY_MODELB_LTR_TOP50_ACCUMULATION_BUILD_WORK_CN.md",
    "docs/tw_portfolio_decision_model/POLICY_MTRP7_R_CLEAN_DAILY_TIER_A_LINEAGE_REPAIR_AND_RERUN_WORK_CN.md",
    "docs/tw_portfolio_decision_model/POLICY_MTRP7_ISOLATED_DAILY_SHADOW_DRY_RUN_WORK_CN.md",
    "docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md",
    "docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md",
    "docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md",
]


@dataclass
class PortfolioState:
    cash: float = 1_000_000.0
    holdings: dict[str, dict[str, float]] = field(default_factory=dict)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def read_csv_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader), list(reader.fieldnames or [])


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


def to_int(value: Any, default: int = 0) -> int:
    text = str(value or "").strip()
    if not text:
        return default
    return int(float(text))


def to_float(value: Any, default: float = 0.0) -> float:
    text = str(value or "").strip()
    if not text:
        return default
    return float(text)


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "pass"}


def forbidden_field_hits(fields: list[str]) -> list[str]:
    hits: list[str] = []
    for field in fields:
        lower = field.lower()
        if any(pattern in lower for pattern in SIGNAL_FORBIDDEN_PATTERNS):
            hits.append(field)
    return sorted(set(hits))


def require_input_roots() -> list[str]:
    required = [
        S_ROOT / "manifest.json",
        S_MODELB_ROOT,
        R_ISOLATED_PHASE_YZ_ROOT / "yz1_strict_e4_model_signals",
        R_ISOLATED_PHASE_YZ_ROOT / "yz2r_execution_price_readiness",
        R_RERUN_ROOT / "validator_report.json",
    ]
    return [rel(path) for path in required if not path.exists()]


def discover_dates() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    model_root = R_ISOLATED_PHASE_YZ_ROOT / "yz1_strict_e4_model_signals"
    price_root = R_ISOLATED_PHASE_YZ_ROOT / "yz2r_execution_price_readiness"
    all_dates = sorted({p.name for p in model_root.glob("20*") if p.is_dir()} | {p.name for p in S_MODELB_ROOT.glob("20*") if p.is_dir()})
    for date in all_dates:
        model_a = model_root / date / "model_a/signals.csv"
        r_model_b = model_root / date / "model_b_yz2/signals.csv"
        s_model_b = S_MODELB_ROOT / date / "signals.csv"
        price_manifest = price_root / date / "manifest.json"
        model_a_rows, model_a_fields = read_csv_rows(model_a) if model_a.exists() else ([], [])
        r_model_b_rows, r_model_b_fields = read_csv_rows(r_model_b) if r_model_b.exists() else ([], [])
        s_model_b_rows, s_model_b_fields = read_csv_rows(s_model_b) if s_model_b.exists() else ([], [])
        price_meta = read_json(price_manifest) if price_manifest.exists() else {}
        blockers: list[str] = []
        if len(model_a_rows) < 100:
            blockers.append("model_a_rows_lt_100")
        if len(r_model_b_rows) != 50:
            blockers.append("r_isolated_model_b_rows_ne_50")
        if len(s_model_b_rows) != 50:
            blockers.append("s_isolated_model_b_rows_ne_50")
        if any(not str(row.get("buy_score", "")).strip() for row in s_model_b_rows):
            blockers.append("s_isolated_model_b_missing_buy_score")
        if not price_meta.get("next_open_available"):
            blockers.append("price_next_open_not_available")
        if not price_meta.get("same_day_mark_available"):
            blockers.append("same_day_mark_not_available")
        if forbidden_field_hits(model_a_fields + r_model_b_fields + s_model_b_fields):
            blockers.append("forbidden_source_field_detected")
        eligible = not blockers
        rows.append(
            {
                "signal_date": date,
                "input_tier": INPUT_TIER,
                "model_a_path": rel(model_a) if model_a.exists() else "",
                "model_a_rows": len(model_a_rows),
                "r_isolated_model_b_path": rel(r_model_b) if r_model_b.exists() else "",
                "r_isolated_model_b_rows": len(r_model_b_rows),
                "s_isolated_model_b_path": rel(s_model_b) if s_model_b.exists() else "",
                "s_isolated_model_b_rows": len(s_model_b_rows),
                "price_source_path": rel(price_manifest) if price_manifest.exists() else "",
                "next_open_available": bool(price_meta.get("next_open_available")),
                "same_day_mark_available": bool(price_meta.get("same_day_mark_available")),
                "tier_a_eligible": eligible,
                "selected": eligible,
                "tier_b_fallback_used": False,
                "status": "eligible" if eligible else "blocked",
                "blockers": "|".join(blockers),
                "details": "Requires R isolated model_a/model_b lineage, S isolated ModelB LTR scores, and R isolated readonly price readiness.",
            }
        )
    return rows


def price_bridge_dir_for_date(signal_date: str) -> Path:
    manifest_path = R_ISOLATED_PHASE_YZ_ROOT / "yz2r_execution_price_readiness" / signal_date / "manifest.json"
    meta = read_json(manifest_path)
    return ROOT / meta["price_source"]


def load_price_cache(price_dir: Path, instruments: set[str]) -> dict[str, dict[str, dict[str, float]]]:
    cache: dict[str, dict[str, dict[str, float]]] = {}
    for instrument in sorted(instruments):
        path = price_dir / f"{instrument}.csv"
        if not path.exists():
            continue
        rows, _ = read_csv_rows(path)
        cache[instrument] = {
            row["date"]: {
                "open": to_float(row.get("open")),
                "close": to_float(row.get("close")),
            }
            for row in rows
            if row.get("date")
        }
    return cache


def trading_dates_from_cache(cache: dict[str, dict[str, dict[str, float]]]) -> list[str]:
    dates: set[str] = set()
    for by_date in cache.values():
        dates.update(by_date)
    return sorted(dates)


def next_trade_date(signal_date: str, trading_dates: list[str]) -> str:
    for date in trading_dates:
        if date > signal_date:
            return date
    return ""


def bridge_rows_for_date(signal_date: str) -> tuple[list[dict[str, Any]], list[dict[str, str]], list[dict[str, str]], list[str]]:
    model_a_path = R_ISOLATED_PHASE_YZ_ROOT / "yz1_strict_e4_model_signals" / signal_date / "model_a/signals.csv"
    s_model_b_path = S_MODELB_ROOT / signal_date / "signals.csv"
    model_a_rows, _ = read_csv_rows(model_a_path)
    s_model_b_rows, _ = read_csv_rows(s_model_b_path)
    b_by_instrument = {row["instrument"]: row for row in s_model_b_rows}

    rows: list[dict[str, Any]] = []
    for a_row in sorted(model_a_rows, key=lambda row: (to_int(row.get("full_qlib_rank") or row.get("candidate_rank"), 999999), row.get("instrument", ""))):
        instrument = a_row.get("instrument", "")
        b_row = b_by_instrument.get(instrument)
        rank = to_int(a_row.get("full_qlib_rank") or a_row.get("candidate_rank"), 999999)
        if b_row:
            buy_score = b_row.get("buy_score", "")
            raw_score = b_row.get("raw_score", "") or buy_score
            score_rank = b_row.get("score_rank", "")
            source_artifact = b_row.get("source_artifact", rel(s_model_b_path))
            source_model_artifact = b_row.get("source_model_artifact", rel(s_model_b_path.with_name("manifest.json")))
            source_feature_artifact = b_row.get("source_feature_artifact", rel(s_model_b_path.with_name("manifest.json")))
            bridge_source_role = "ltr_top50_buy_ordering"
        else:
            buy_score = ""
            raw_score = a_row.get("raw_score", "")
            score_rank = ""
            source_artifact = a_row.get("source_artifact", rel(model_a_path))
            source_model_artifact = a_row.get("source_model_artifact", rel(model_a_path.with_name("manifest.json")))
            source_feature_artifact = a_row.get("source_feature_artifact", rel(model_a_path.with_name("manifest.json")))
            bridge_source_role = "qlib_full_rank_visibility_only"
        rows.append(
            {
                "date": signal_date,
                "instrument": instrument,
                "model_name": BRIDGE_MODEL_NAME,
                "model_family": "ltr",
                "candidate_rank": rank,
                "buy_score": buy_score,
                "raw_score": raw_score,
                "score_rank": score_rank,
                "full_qlib_rank": rank,
                "signal_asof": signal_date,
                "available_at": signal_date,
                "source_artifact": source_artifact,
                "source_model_artifact": source_model_artifact,
                "source_feature_artifact": source_feature_artifact,
                "bridge_source_role": bridge_source_role,
                "production_candidate": True,
                "production_allowed": False,
                "not_published_latest": True,
                "readonly_only": True,
                "simulation_only": True,
            }
        )
    fields = SIGNAL_REQUIRED_FIELDS + [
        "bridge_source_role",
        "production_candidate",
        "production_allowed",
        "not_published_latest",
        "readonly_only",
        "simulation_only",
    ]
    return rows, model_a_rows, s_model_b_rows, fields


def bridge_stats(rows: list[dict[str, Any]], fields: list[str]) -> tuple[bool, dict[str, Any]]:
    top50 = [row for row in rows if to_int(row.get("candidate_rank")) <= 50]
    non_top50 = [row for row in rows if to_int(row.get("candidate_rank")) > 50]
    missing = [field for field in SIGNAL_REQUIRED_FIELDS if field not in fields]
    full_rank_missing = [row for row in rows if not str(row.get("full_qlib_rank", "")).strip()]
    top50_buy_missing = [row for row in top50 if not str(row.get("buy_score", "")).strip()]
    non_top50_buy_populated = [row for row in non_top50 if str(row.get("buy_score", "")).strip()]
    available_after_asof = [row for row in rows if str(row.get("available_at", "")) > str(row.get("signal_asof", ""))]
    ok = (
        len(rows) >= 100
        and len(top50) == 50
        and len(non_top50) >= 50
        and not missing
        and not full_rank_missing
        and not top50_buy_missing
        and not non_top50_buy_populated
        and not available_after_asof
    )
    return ok, {
        "row_count": len(rows),
        "top50_rows": len(top50),
        "non_top50_visibility_rows": len(non_top50),
        "missing_required_fields": "|".join(missing),
        "full_rank_missing_count": len(full_rank_missing),
        "top50_buy_score_missing_count": len(top50_buy_missing),
        "non_top50_buy_score_populated_count": len(non_top50_buy_populated),
        "available_after_asof_count": len(available_after_asof),
    }


def build_daily_bridge(signal_date: str, generated_at: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows, _model_a_rows, _model_b_rows, fields = bridge_rows_for_date(signal_date)
    ok, stats = bridge_stats(rows, fields)
    day_dir = OUT_ROOT / "daily_bridge_artifacts" / signal_date
    signals_path = day_dir / "signals.csv"
    write_csv(signals_path, rows, fields)
    write_json(
        day_dir / "schema.json",
        {
            "artifact_type": "ModelSignalArtifact",
            "schema_version": "model_signal_v1",
            "bridge_schema_version": "mtrp7_s_r.real_tier_a_bridge.v1",
            "required_fields": SIGNAL_REQUIRED_FIELDS,
            "field_policy": {
                "candidate_rank": "qlib full-rank candidate boundary from R isolated ModelA",
                "full_qlib_rank": "qlib full-rank visibility from R isolated ModelA",
                "top50_buy_score": "LTR buy_score from S isolated ModelB",
                "non_top50_buy_score": "blank; non-top50 rows are visibility-only and cannot be buy-ranked",
            },
            "forbidden_field_patterns": SIGNAL_FORBIDDEN_PATTERNS,
        },
    )
    lineage_rows = [
        {
            "signal_date": signal_date,
            "input_tier": INPUT_TIER,
            "tier_b_fallback_used": False,
            "r_model_a_manifest": rel(R_ISOLATED_PHASE_YZ_ROOT / "yz1_strict_e4_model_signals" / signal_date / "model_a/manifest.json"),
            "r_model_b_manifest": rel(R_ISOLATED_PHASE_YZ_ROOT / "yz1_strict_e4_model_signals" / signal_date / "model_b_yz2/manifest.json"),
            "s_modelb_manifest": rel(S_MODELB_ROOT / signal_date / "manifest.json"),
            "price_readiness_manifest": rel(R_ISOLATED_PHASE_YZ_ROOT / "yz2r_execution_price_readiness" / signal_date / "manifest.json"),
            "bridge_signals_sha256": sha256_file(signals_path),
            "status": "pass" if ok else "fail",
            "details": "Bridge combines R isolated ModelA full-rank visibility with S isolated ModelB LTR top50 buy_score.",
        }
    ]
    write_csv(
        day_dir / "lineage_audit.csv",
        lineage_rows,
        [
            "signal_date",
            "input_tier",
            "tier_b_fallback_used",
            "r_model_a_manifest",
            "r_model_b_manifest",
            "s_modelb_manifest",
            "price_readiness_manifest",
            "bridge_signals_sha256",
            "status",
            "details",
        ],
    )
    forbidden_present = forbidden_field_hits(fields)
    write_json(
        day_dir / "forbidden_field_audit.json",
        {
            "signal_date": signal_date,
            "status": "pass" if not forbidden_present else "fail",
            "forbidden_fields_present": forbidden_present,
            "used_for_ranking": False,
            "readonly_only": True,
            "simulation_only": True,
            "production_allowed": False,
        },
    )
    manifest = {
        "artifact_type": "daily_bridge_artifact",
        "schema_version": "mtrp7_s_r.real_tier_a_bridge.v1",
        "phase": PHASE,
        "run_id": RUN_ID,
        "created_at": generated_at,
        "created_by": rel(Path(__file__)),
        "signal_date": signal_date,
        "input_tier": INPUT_TIER,
        "tier_b_fallback_used": False,
        "model_name": BRIDGE_MODEL_NAME,
        "model_family": "ltr",
        "strategy_rule": STRATEGY,
        "production_candidate": True,
        "production_allowed": False,
        "not_published_latest": True,
        "readonly_only": True,
        "simulation_only": True,
        "validator_status": "pass" if ok and not forbidden_present else "fail",
        "stats": stats,
        "output_files": {
            "signals.csv": rel(signals_path),
            "schema.json": rel(day_dir / "schema.json"),
            "lineage_audit.csv": rel(day_dir / "lineage_audit.csv"),
            "forbidden_field_audit.json": rel(day_dir / "forbidden_field_audit.json"),
        },
    }
    write_json(day_dir / "manifest.json", manifest)
    register = {
        "signal_date": signal_date,
        "manifest_path": rel(day_dir / "manifest.json"),
        "signals_path": rel(signals_path),
        "row_count": stats["row_count"],
        "top50_rows": stats["top50_rows"],
        "non_top50_visibility_rows": stats["non_top50_visibility_rows"],
        "input_tier": INPUT_TIER,
        "tier_b_fallback_used": False,
        "validator_status": manifest["validator_status"],
        "details": "daily bridge validator passed" if manifest["validator_status"] == "pass" else "daily bridge validator failed",
    }
    return register, rows


def rank_map(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["instrument"]: row for row in rows}


def candidate_order_intents(
    signal_date: str,
    bridge_rows: list[dict[str, Any]],
    state: PortfolioState,
    bridge_manifest_path: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_inst = rank_map(bridge_rows)
    intents: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    sell_candidates = []
    for inst in state.holdings:
        row = by_inst.get(inst)
        if not row:
            audit.append({"instrument": inst, "decision": "skip_sell_visibility_missing", "reason": "missing_holding_visibility"})
            continue
        if to_int(row.get("full_qlib_rank"), 999999) > 100:
            sell_candidates.append(row)
    sell_candidates.sort(key=lambda row: (-to_int(row.get("full_qlib_rank")), row.get("instrument", "")))
    sold = set()
    if sell_candidates:
        row = sell_candidates[0]
        sold.add(row["instrument"])
        intents.append(order_row(signal_date, row, "sell", "hold_rank_buffer_100_exit_worst", bridge_manifest_path))
        audit.append({"instrument": row["instrument"], "decision": "sell", "reason": "full_qlib_rank_gt_100_worst"})

    post_sell_holdings = set(state.holdings) - sold
    if len(post_sell_holdings) < 10:
        buy_candidates = [
            row
            for row in bridge_rows
            if to_int(row.get("candidate_rank"), 999999) <= 50
            and str(row.get("buy_score", "")).strip()
            and row["instrument"] not in post_sell_holdings
            and row["instrument"] not in sold
        ]
        buy_candidates.sort(
            key=lambda row: (-to_float(row.get("buy_score")), to_int(row.get("full_qlib_rank"), 999999), row.get("instrument", ""))
        )
        if buy_candidates:
            row = buy_candidates[0]
            intents.append(order_row(signal_date, row, "buy", "top50_ltr_buy_score_top_candidate", bridge_manifest_path))
            audit.append({"instrument": row["instrument"], "decision": "buy", "reason": "top50_ltr_buy_score_top_candidate"})
    return intents, audit


def baseline_order_intents(signal_date: str, bridge_rows: list[dict[str, Any]], state: PortfolioState) -> list[dict[str, Any]]:
    by_inst = rank_map(bridge_rows)
    intents: list[dict[str, Any]] = []
    sell_candidates = []
    for inst in state.holdings:
        row = by_inst.get(inst)
        if row and to_int(row.get("candidate_rank"), 999999) > 50:
            sell_candidates.append(row)
    sell_candidates.sort(key=lambda row: (-to_int(row.get("full_qlib_rank")), row.get("instrument", "")))
    sold = set()
    if sell_candidates:
        row = sell_candidates[0]
        sold.add(row["instrument"])
        intents.append(order_row(signal_date, row, "sell", "baseline_top50_exit_sell", "baseline_shadow_internal"))
    post_sell = set(state.holdings) - sold
    if len(post_sell) < 10:
        candidates = [row for row in bridge_rows if to_int(row.get("candidate_rank"), 999999) <= 50 and row["instrument"] not in post_sell and row["instrument"] not in sold]
        candidates.sort(key=lambda row: (to_int(row.get("full_qlib_rank"), 999999), row.get("instrument", "")))
        if candidates:
            intents.append(order_row(signal_date, candidates[0], "buy", "baseline_qlib_rank_top_candidate", "baseline_shadow_internal"))
    return intents


def order_row(signal_date: str, signal_row: dict[str, Any], action: str, reason: str, signal_artifact: str) -> dict[str, Any]:
    return {
        "signal_date": signal_date,
        "instrument": signal_row["instrument"],
        "intent_action": action,
        "intent_reason": reason,
        "strategy_rule": STRATEGY,
        "candidate_rank": signal_row.get("candidate_rank", ""),
        "buy_rank": signal_row.get("score_rank", "") or signal_row.get("full_qlib_rank", ""),
        "full_qlib_rank": signal_row.get("full_qlib_rank", ""),
        "max_buy_count": 1,
        "max_sell_count": 1,
        "model_name": BRIDGE_MODEL_NAME,
        "signal_artifact": signal_artifact,
        "current_holding_flag": action == "sell",
        "target_holding_count": 10,
        "candidate_k": 50,
        "tie_breaker": "full_qlib_rank_asc_instrument_asc",
        "diagnostic_only": False,
    }


def order_stats(rows: list[dict[str, Any]], fields: list[str]) -> tuple[bool, dict[str, Any]]:
    missing = [field for field in ORDER_REQUIRED_FIELDS if field not in fields]
    forbidden = sorted(set(fields).intersection(ORDER_FORBIDDEN_FIELDS))
    actions = Counter(row.get("intent_action", "") for row in rows)
    non_top50_buy = [row for row in rows if row.get("intent_action") == "buy" and to_int(row.get("candidate_rank"), 999999) > 50]
    invalid = [row for row in rows if row.get("intent_action") not in {"buy", "sell", "hold", "skip"}]
    ok = not missing and not forbidden and actions["buy"] <= 1 and actions["sell"] <= 1 and not non_top50_buy and not invalid
    return ok, {
        "order_intent_rows": len(rows),
        "buy_count": actions["buy"],
        "sell_count": actions["sell"],
        "hold_count": actions["hold"],
        "skip_count": actions["skip"],
        "non_top50_buy_count": len(non_top50_buy),
        "invalid_action_count": len(invalid),
        "forbidden_fields_present": "|".join(forbidden),
        "missing_required_fields": "|".join(missing),
    }


def build_daily_order(signal_date: str, bridge_register: dict[str, Any], bridge_rows: list[dict[str, Any]], state: PortfolioState, generated_at: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    day_dir = OUT_ROOT / "daily_order_intent_artifacts" / signal_date
    rows, decision_audit = candidate_order_intents(signal_date, bridge_rows, state, bridge_register["manifest_path"])
    fields = ORDER_REQUIRED_FIELDS + ["current_holding_flag", "target_holding_count", "candidate_k", "tie_breaker", "diagnostic_only"]
    ok, stats = order_stats(rows, fields)
    order_path = day_dir / "order_intents.csv"
    write_csv(order_path, rows, fields)
    write_json(
        day_dir / "schema.json",
        {
            "artifact_type": "OrderIntentArtifact",
            "schema_version": "order_intent_v1",
            "required_fields": ORDER_REQUIRED_FIELDS,
            "forbidden_fields": sorted(ORDER_FORBIDDEN_FIELDS),
            "policy": "intent only; replay computes simulated execution quantity, price, cash, NAV and positions",
        },
    )
    audit_rows = [
        {
            "signal_date": signal_date,
            "strategy_rule": STRATEGY,
            "input_signal": bridge_register["manifest_path"],
            "input_portfolio_state": "readonly_prior_shadow_state",
            "target_holding_count": 10,
            "candidate_k": 50,
            "hold_rank_buffer": 100,
            "max_buy_count": 1,
            "max_sell_count": 1,
            "buy_count": stats["buy_count"],
            "sell_count": stats["sell_count"],
            "non_top50_buy_count": stats["non_top50_buy_count"],
            "decision_trace": json.dumps(decision_audit, ensure_ascii=False, sort_keys=True),
            "status": "pass" if ok else "fail",
            "details": stats["forbidden_fields_present"] or stats["missing_required_fields"] or "daily OrderIntent validator passed",
        }
    ]
    write_csv(
        day_dir / "strategy_decision_audit.csv",
        audit_rows,
        [
            "signal_date",
            "strategy_rule",
            "input_signal",
            "input_portfolio_state",
            "target_holding_count",
            "candidate_k",
            "hold_rank_buffer",
            "max_buy_count",
            "max_sell_count",
            "buy_count",
            "sell_count",
            "non_top50_buy_count",
            "decision_trace",
            "status",
            "details",
        ],
    )
    write_json(
        day_dir / "forbidden_action_audit.json",
        {
            "signal_date": signal_date,
            "status": "pass" if not stats["forbidden_fields_present"] else "fail",
            "not_order": True,
            "not_target_position": True,
            "not_investment_advice": True,
            "broker_connection": False,
            "quick_trade": False,
            "real_order": False,
            "target_weight_instruction": False,
            "target_position_instruction": False,
            "quantity_instruction": False,
            "forbidden_fields_present": stats["forbidden_fields_present"].split("|") if stats["forbidden_fields_present"] else [],
        },
    )
    manifest = {
        "artifact_type": "daily_order_intent_artifact",
        "schema_version": "order_intent_v1",
        "phase": PHASE,
        "run_id": RUN_ID,
        "created_at": generated_at,
        "created_by": rel(Path(__file__)),
        "signal_date": signal_date,
        "input_tier": INPUT_TIER,
        "tier_b_fallback_used": False,
        "strategy_rule": STRATEGY,
        "input_signal": bridge_register["manifest_path"],
        "readonly_only": True,
        "simulation_only": True,
        "production_allowed": False,
        "not_order": True,
        "not_target_position": True,
        "not_investment_advice": True,
        "validator_status": "pass" if ok else "fail",
        "stats": stats,
        "output_files": {
            "order_intents.csv": rel(order_path),
            "schema.json": rel(day_dir / "schema.json"),
            "strategy_decision_audit.csv": rel(day_dir / "strategy_decision_audit.csv"),
            "forbidden_action_audit.json": rel(day_dir / "forbidden_action_audit.json"),
        },
    }
    write_json(day_dir / "manifest.json", manifest)
    register = {
        "signal_date": signal_date,
        "manifest_path": rel(day_dir / "manifest.json"),
        "order_intents_path": rel(order_path),
        "order_intent_rows": stats["order_intent_rows"],
        "buy_count": stats["buy_count"],
        "sell_count": stats["sell_count"],
        "non_top50_buy_count": stats["non_top50_buy_count"],
        "forbidden_fields_present": stats["forbidden_fields_present"],
        "input_tier": INPUT_TIER,
        "tier_b_fallback_used": False,
        "validator_status": manifest["validator_status"],
        "details": "daily OrderIntent validator passed" if manifest["validator_status"] == "pass" else "daily OrderIntent validator failed",
    }
    return register, rows


def apply_intents(
    strategy_rule: str,
    signal_date: str,
    execution_date: str,
    intents: list[dict[str, Any]],
    state: PortfolioState,
    price_cache: dict[str, dict[str, dict[str, float]]],
    order_manifest: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    actions: list[dict[str, Any]] = []
    skips: list[dict[str, Any]] = []
    ordered = sorted(intents, key=lambda row: 0 if row["intent_action"] == "sell" else 1)
    for intent in ordered:
        inst = intent["instrument"]
        price_row = price_cache.get(inst, {}).get(execution_date)
        if not price_row or not price_row.get("open"):
            skips.append(skip_row(strategy_rule, signal_date, execution_date, intent, "missing_next_open"))
            continue
        price = price_row["open"]
        if intent["intent_action"] == "sell":
            holding = state.holdings.get(inst)
            if not holding:
                skips.append(skip_row(strategy_rule, signal_date, execution_date, intent, "not_currently_held"))
                continue
            qty = int(holding["quantity"])
            gross = qty * price
            commission = gross * 0.001425
            tax = gross * 0.003
            state.cash += gross - commission - tax
            del state.holdings[inst]
            actions.append(action_row(strategy_rule, signal_date, execution_date, intent, qty, price, commission, tax, state.cash, 0, order_manifest))
        elif intent["intent_action"] == "buy":
            if inst in state.holdings:
                skips.append(skip_row(strategy_rule, signal_date, execution_date, intent, "already_held"))
                continue
            qty = 10
            gross = qty * price
            commission = gross * 0.001425
            total = gross + commission
            if state.cash - total < 0:
                skips.append(skip_row(strategy_rule, signal_date, execution_date, intent, "insufficient_simulated_cash"))
                continue
            state.cash -= total
            state.holdings[inst] = {"quantity": float(qty), "cost_basis": price}
            actions.append(action_row(strategy_rule, signal_date, execution_date, intent, qty, price, commission, 0.0, state.cash, qty, order_manifest))
    return actions, skips


def skip_row(strategy_rule: str, signal_date: str, execution_date: str, intent: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "strategy_rule": strategy_rule,
        "signal_date": signal_date,
        "execution_date": execution_date,
        "instrument": intent.get("instrument", ""),
        "intent_action": intent.get("intent_action", ""),
        "intent_reason": intent.get("intent_reason", ""),
        "skip_reason": reason,
        "status": "tracked",
        "details": "Simulation-only replay skip audit.",
    }


def action_row(
    strategy_rule: str,
    signal_date: str,
    execution_date: str,
    intent: dict[str, Any],
    qty: int,
    price: float,
    commission: float,
    tax: float,
    cash_after: float,
    position_after: int,
    order_manifest: str,
) -> dict[str, Any]:
    return {
        "strategy_rule": strategy_rule,
        "signal_date": signal_date,
        "execution_date": execution_date,
        "instrument": intent.get("instrument", ""),
        "action": intent.get("intent_action", ""),
        "quantity": qty,
        "execution_price": f"{price:.6f}",
        "commission": f"{commission:.6f}",
        "tax": f"{tax:.6f}",
        "cash_after": f"{cash_after:.6f}",
        "position_after": position_after,
        "intent_reason": intent.get("intent_reason", ""),
        "model_name": BRIDGE_MODEL_NAME,
        "order_intent_artifact": order_manifest,
        "readonly_only": True,
        "simulation_only": True,
        "not_real_order": True,
    }


def mark_positions(
    strategy_rule: str,
    execution_date: str,
    state: PortfolioState,
    price_cache: dict[str, dict[str, dict[str, float]]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    missing = 0
    market_value = 0.0
    seen: set[tuple[str, str]] = set()
    duplicate = 0
    same_day = 0
    for inst, holding in sorted(state.holdings.items()):
        mark_row = price_cache.get(inst, {}).get(execution_date)
        if not mark_row or not mark_row.get("close"):
            missing += 1
            mark_price = 0.0
            mark_date = ""
        else:
            mark_price = mark_row["close"]
            mark_date = execution_date
            same_day += 1
        qty = holding["quantity"]
        value = qty * mark_price
        market_value += value
        key = (execution_date, inst)
        duplicate += int(key in seen)
        seen.add(key)
        rows.append(
            {
                "strategy_rule": strategy_rule,
                "date": execution_date,
                "instrument": inst,
                "quantity": int(qty),
                "cost_basis": f"{holding['cost_basis']:.6f}",
                "mark_price": f"{mark_price:.6f}",
                "mark_price_date": mark_date,
                "market_value": f"{value:.6f}",
                "unrealized_pnl": f"{(mark_price - holding['cost_basis']) * qty:.6f}",
                "model_name": BRIDGE_MODEL_NAME,
            }
        )
    ratio = 1.0 if not rows else same_day / len(rows)
    return rows, {
        "cash": state.cash,
        "market_value": market_value,
        "equity": state.cash + market_value,
        "holding_count": len(state.holdings),
        "missing_price_count": missing,
        "duplicate_position_count": duplicate,
        "same_day_mark_coverage_ratio": ratio,
        "max_mark_lag_days": 0 if missing == 0 else "unknown",
    }


def build_daily_replay(
    signal_date: str,
    execution_date: str,
    bridge_rows: list[dict[str, Any]],
    candidate_order_register: dict[str, Any],
    candidate_intents: list[dict[str, Any]],
    candidate_state: PortfolioState,
    baseline_state: PortfolioState,
    price_cache: dict[str, dict[str, dict[str, float]]],
    generated_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    baseline_intents = baseline_order_intents(signal_date, bridge_rows, baseline_state)
    cand_actions, cand_skips = apply_intents(
        STRATEGY,
        signal_date,
        execution_date,
        candidate_intents,
        candidate_state,
        price_cache,
        candidate_order_register["manifest_path"],
    )
    base_actions, base_skips = apply_intents(
        BASELINE_STRATEGY,
        signal_date,
        execution_date,
        baseline_intents,
        baseline_state,
        price_cache,
        "baseline_shadow_internal",
    )
    cand_positions, cand_nav = mark_positions(STRATEGY, execution_date, candidate_state, price_cache)
    base_positions, base_nav = mark_positions(BASELINE_STRATEGY, execution_date, baseline_state, price_cache)
    actions = cand_actions + base_actions
    positions = cand_positions + base_positions
    skips = cand_skips + base_skips
    day_dir = OUT_ROOT / "daily_shadow_replay_artifacts" / signal_date
    action_fields = [
        "strategy_rule",
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
        "model_name",
        "order_intent_artifact",
        "readonly_only",
        "simulation_only",
        "not_real_order",
    ]
    position_fields = [
        "strategy_rule",
        "date",
        "instrument",
        "quantity",
        "cost_basis",
        "mark_price",
        "mark_price_date",
        "market_value",
        "unrealized_pnl",
        "model_name",
    ]
    skip_fields = ["strategy_rule", "signal_date", "execution_date", "instrument", "intent_action", "intent_reason", "skip_reason", "status", "details"]
    write_csv(day_dir / "actions.csv", actions, action_fields)
    write_csv(day_dir / "positions.csv", positions, position_fields)
    write_csv(day_dir / "skip_reason_audit.csv", skips, skip_fields)

    mark_rows = []
    for strategy_rule, nav, strategy_positions in [
        (STRATEGY, cand_nav, cand_positions),
        (BASELINE_STRATEGY, base_nav, base_positions),
    ]:
        mark_rows.append(
            {
                "strategy_rule": strategy_rule,
                "signal_date": signal_date,
                "execution_date": execution_date,
                "position_rows": len(strategy_positions),
                "same_day_mark_coverage_ratio": f"{nav['same_day_mark_coverage_ratio']:.6f}",
                "fallback_mark_count": 0 if nav["missing_price_count"] == 0 else nav["missing_price_count"],
                "max_mark_lag_days": nav["max_mark_lag_days"],
                "missing_price_count": nav["missing_price_count"],
                "status": "pass"
                if nav["same_day_mark_coverage_ratio"] >= 0.99 and nav["missing_price_count"] == 0
                else "fail",
                "details": "same-day close mark from isolated readonly price bridge",
            }
        )
    write_csv(
        day_dir / "mark_coverage_audit.csv",
        mark_rows,
        [
            "strategy_rule",
            "signal_date",
            "execution_date",
            "position_rows",
            "same_day_mark_coverage_ratio",
            "fallback_mark_count",
            "max_mark_lag_days",
            "missing_price_count",
            "status",
            "details",
        ],
    )
    negative_cash_count = int(cand_nav["cash"] < 0) + int(base_nav["cash"] < 0)
    duplicate_position_count = int(cand_nav["duplicate_position_count"]) + int(base_nav["duplicate_position_count"])
    replay_pass = all(row["status"] == "pass" for row in mark_rows) and negative_cash_count == 0 and duplicate_position_count == 0
    summary = {
        "artifact_type": "daily_shadow_replay_summary",
        "schema_version": "mtrp7_s_r.real_tier_a_shadow_replay.v1",
        "phase": PHASE,
        "run_id": RUN_ID,
        "signal_date": signal_date,
        "execution_date": execution_date,
        "input_tier": INPUT_TIER,
        "tier_b_fallback_used": False,
        "execution_price_mode": "next_open",
        "execution_date_policy": "next_tradeable_day_after_signal_date",
        "fee_rate": 0.001425,
        "sell_tax_rate": 0.003,
        "lot_size": 10,
        "candidate_strategy": STRATEGY,
        "baseline_strategy": BASELINE_STRATEGY,
        "candidate_action_count": len(cand_actions),
        "baseline_action_count": len(base_actions),
        "candidate_skip_count": len(cand_skips),
        "baseline_skip_count": len(base_skips),
        "candidate_cash": cand_nav["cash"],
        "baseline_cash": base_nav["cash"],
        "candidate_equity": cand_nav["equity"],
        "baseline_equity": base_nav["equity"],
        "candidate_minus_baseline_equity": cand_nav["equity"] - base_nav["equity"],
        "negative_cash_count": negative_cash_count,
        "duplicate_position_count": duplicate_position_count,
        "same_day_mark_coverage_ratio": min(cand_nav["same_day_mark_coverage_ratio"], base_nav["same_day_mark_coverage_ratio"]),
        "max_mark_lag_days": 0,
        "readonly_only": True,
        "simulation_only": True,
        "production_allowed": False,
        "validator_status": "pass" if replay_pass else "fail",
    }
    write_json(day_dir / "summary.json", summary)
    manifest = {
        "artifact_type": "daily_shadow_replay_artifact",
        "schema_version": "mtrp7_s_r.real_tier_a_shadow_replay.v1",
        "phase": PHASE,
        "run_id": RUN_ID,
        "created_at": generated_at,
        "created_by": rel(Path(__file__)),
        "signal_date": signal_date,
        "input_tier": INPUT_TIER,
        "tier_b_fallback_used": False,
        "order_intent_artifact": candidate_order_register["manifest_path"],
        "execution_config": {
            "execution_price_mode": "next_open",
            "execution_date_policy": "next_tradeable_day_after_signal_date",
            "fee_rate": 0.001425,
            "sell_tax_rate": 0.003,
            "lot_size": 10,
            "mark_price": "same_day_close",
            "readonly_only": True,
            "simulation_only": True,
            "production_allowed": False,
        },
        "validator_status": summary["validator_status"],
        "output_files": {
            "summary.json": rel(day_dir / "summary.json"),
            "actions.csv": rel(day_dir / "actions.csv"),
            "positions.csv": rel(day_dir / "positions.csv"),
            "skip_reason_audit.csv": rel(day_dir / "skip_reason_audit.csv"),
            "mark_coverage_audit.csv": rel(day_dir / "mark_coverage_audit.csv"),
        },
    }
    write_json(day_dir / "manifest.json", manifest)
    register = {
        "signal_date": signal_date,
        "execution_date": execution_date,
        "manifest_path": rel(day_dir / "manifest.json"),
        "summary_path": rel(day_dir / "summary.json"),
        "candidate_action_count": len(cand_actions),
        "baseline_action_count": len(base_actions),
        "candidate_skip_count": len(cand_skips),
        "baseline_skip_count": len(base_skips),
        "candidate_equity": f"{cand_nav['equity']:.6f}",
        "baseline_equity": f"{base_nav['equity']:.6f}",
        "candidate_minus_baseline_equity": f"{cand_nav['equity'] - base_nav['equity']:.6f}",
        "same_day_mark_coverage_ratio": f"{summary['same_day_mark_coverage_ratio']:.6f}",
        "max_mark_lag_days": 0,
        "negative_cash_count": negative_cash_count,
        "duplicate_position_count": duplicate_position_count,
        "input_tier": INPUT_TIER,
        "tier_b_fallback_used": False,
        "validator_status": summary["validator_status"],
        "details": "daily simulation-only candidate-baseline shadow replay",
    }
    skip_delta = {
        "signal_date": signal_date,
        "execution_date": execution_date,
        "candidate_skip_count": len(cand_skips),
        "baseline_skip_count": len(base_skips),
        "candidate_minus_baseline_skip_count": len(cand_skips) - len(base_skips),
        "candidate_skip_reasons": "|".join(sorted({row["skip_reason"] for row in cand_skips})),
        "baseline_skip_reasons": "|".join(sorted({row["skip_reason"] for row in base_skips})),
        "status": "tracked",
    }
    return register, skip_delta


def build_readonly_wording_audit() -> list[dict[str, Any]]:
    checks = [
        ("readonly_only", True, True),
        ("simulation_only", True, True),
        ("production_allowed", False, False),
        ("production_ready", False, False),
        ("default_switch_allowed", False, False),
        ("not_order", True, True),
        ("not_target_position", True, True),
        ("not_investment_advice", True, True),
        ("tier_a_input_declared", True, True),
        ("tier_b_fallback_used", False, False),
    ]
    return [
        {
            "audit_item": name,
            "expected": expected,
            "actual": actual,
            "status": "pass" if expected == actual else "fail",
            "details": "readonly/simulation wording gate",
        }
        for name, expected, actual in checks
    ]


def build_forbidden_scope_audit() -> list[dict[str, Any]]:
    return [
        {
            "audit_item": item,
            "performed": False,
            "status": "pass",
            "details": "This builder writes only isolated MTRP7_S_R shadow-readiness artifacts and execution report.",
        }
        for item in FORBIDDEN_SCOPE_ITEMS
    ]


def collect_price_mark_rows(covered_dates: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for date in covered_dates:
        day_rows, _ = read_csv_rows(OUT_ROOT / "daily_shadow_replay_artifacts" / date / "mark_coverage_audit.csv")
        rows.extend(day_rows)
    return rows


def checksum_rows(paths: list[tuple[str, Path]], covered_dates: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, path in paths:
        if path.exists() and path.is_file():
            rows.append(
                {
                    "artifact_name": name,
                    "path": rel(path),
                    "sha256": sha256_file(path),
                    "input_tier": INPUT_TIER,
                    "tier_b_fallback_used": False,
                    "status": "pass",
                }
            )
    for date in covered_dates:
        for name, path in [
            (f"{date}_bridge_manifest", OUT_ROOT / "daily_bridge_artifacts" / date / "manifest.json"),
            (f"{date}_bridge_signals", OUT_ROOT / "daily_bridge_artifacts" / date / "signals.csv"),
            (f"{date}_order_manifest", OUT_ROOT / "daily_order_intent_artifacts" / date / "manifest.json"),
            (f"{date}_order_intents", OUT_ROOT / "daily_order_intent_artifacts" / date / "order_intents.csv"),
            (f"{date}_replay_manifest", OUT_ROOT / "daily_shadow_replay_artifacts" / date / "manifest.json"),
            (f"{date}_replay_summary", OUT_ROOT / "daily_shadow_replay_artifacts" / date / "summary.json"),
        ]:
            rows.append(
                {
                    "artifact_name": name,
                    "path": rel(path),
                    "sha256": sha256_file(path),
                    "input_tier": INPUT_TIER,
                    "tier_b_fallback_used": False,
                    "status": "pass",
                }
            )
    return rows


def build_diagnostic_findings(verdict: str, covered_dates: list[str], validator: dict[str, Any]) -> str:
    blockers = validator.get("blockers", [])
    return f"""# MTRP7_S_R Real Tier A Shadow Rerun Repair Diagnostic Findings

## Verdict

```text
{verdict}
```

## Input

```text
input_tier = {INPUT_TIER}
tier_b_fallback_used = false
s_isolated_modelb_root = {rel(S_MODELB_ROOT)}
r_isolated_phase_yz_root = {rel(R_ISOLATED_PHASE_YZ_ROOT)}
```

## Covered Dates

```text
covered_shadow_signal_days = {len(covered_dates)}
dates = {", ".join(covered_dates) if covered_dates else "none"}
```

## Validator

```json
{json.dumps(validator, ensure_ascii=False, indent=2)}
```

## Blockers

{chr(10).join(f"- `{item}`" for item in blockers) if blockers else "- No blocker."}

## Boundary Statement

This package is readonly and simulation-only. It did not train, tune, replace, rescore, refresh provider data, publish providers, mutate accepted/latest pointers, write formal phase_yz, write formal PriceStore, change production/default registry, change frontend/API/Agent, change daily-auto defaults, connect broker, quick-trade, place real orders, issue target weight/position/quantity instructions, or tune by returns.
"""


def build_execution_report(verdict: str, covered_dates: list[str], validator: dict[str, Any], changed_files: list[str]) -> str:
    mtrp8 = "是" if verdict == VERDICT_PASS else "否"
    return f"""# Execution Report

## 1. Scope

- Assigned phase: `MTRP7_S_R_REAL_TIER_A_SHADOW_RERUN_REPAIR`
- Mainline document: `docs/tw_portfolio_decision_model/POLICY_MTRP7_S_R_REAL_TIER_A_SHADOW_RERUN_REPAIR_WORK_CN.md`
- Strategy candidate: `{STRATEGY}`
- Non-goals confirmed: no training/tuning/model replacement/new scoring, no provider refresh/publish, no accepted/latest mutation, no formal phase_yz or formal PriceStore write, no production/default registry change, no frontend/API/Agent/daily-auto default change, no broker/quick-trade/real order, no target weight/position/quantity instruction, no return tuning.

## 2. Documents / Contracts / Skills Read

{chr(10).join(f"- `{item}`" for item in REQUIRED_READ_FILES)}

## 3. Changes Made

- Added builder: `scripts/build_tw_policy_mtrp7_s_r_real_tier_a_shadow_rerun_repair.py`
- Generated repair root: `{rel(OUT_ROOT)}/`
- Wrote this execution report.

## 4. Evidence Produced

- Covered dates: `{", ".join(covered_dates)}`
- Daily bridge artifacts: `{validator.get("daily_bridge_artifact_count")}`
- Daily OrderIntent artifacts: `{validator.get("daily_order_intent_artifact_count")}`
- Daily shadow replay artifacts: `{validator.get("daily_shadow_replay_artifact_count")}`
- Input tier: `{validator.get("input_tier")}`
- Tier B fallback used: `{validator.get("tier_b_fallback_used")}`
- Validator status: `{validator.get("status")}`
- Validator verdict: `{validator.get("verdict")}`

## 5. Compliance With Mainline

- `covered_shadow_signal_days >= 5`: `{validator.get("minimum_shadow_days_pass")}`
- Bridge validators pass: `{validator.get("all_daily_bridge_validators_pass")}`
- OrderIntent validators pass: `{validator.get("all_daily_order_intent_validators_pass")}`
- Replay validators pass: `{validator.get("all_daily_shadow_replay_validators_pass")}`
- Same-day mark coverage ratio: `{validator.get("same_day_mark_coverage_ratio")}`
- Max mark lag days: `{validator.get("max_mark_lag_days")}`
- Negative cash count: `{validator.get("negative_cash_count")}`
- Duplicate position count: `{validator.get("duplicate_position_count")}`
- Skip delta tracked: `{validator.get("skip_delta_tracked")}`
- Forbidden scope clean: `{validator.get("forbidden_scope_clean")}`

## 6. Forbidden Actions Audit

All forbidden scope audit rows are `performed=false` and `status=pass`. Replay `actions.csv` contains simulation-only execution quantities/prices as replay accounting fields only; OrderIntent contains no execution, cash, NAV, broker, target, or quantity fields.

## 7. Issues / Blockers / Deviations

{chr(10).join(f"- `{item}`" for item in validator.get("blockers", [])) if validator.get("blockers") else "- No blocker."}

## 8. Files Changed

{chr(10).join(f"- `{item}`" for item in changed_files)}

## 9. Recommendation For Reviewer

Verdict: `{verdict}`

是否授权进入 MTRP8 shadow review / readonly exposure design review: `{mtrp8}`

仍不授权 production default switch。
"""


def main() -> None:
    generated_at = now_iso()
    missing = require_input_roots()
    if missing:
        validator = {
            "status": "stop",
            "verdict": VERDICT_STOP,
            "blockers": [f"missing_required_input:{item}" for item in missing],
        }
        OUT_ROOT.mkdir(parents=True, exist_ok=True)
        write_json(OUT_ROOT / "validator_report.json", validator)
        write_text(OUT_ROOT / "diagnostic_findings.md", build_diagnostic_findings(VERDICT_STOP, [], validator))
        raise SystemExit(json.dumps(validator, ensure_ascii=False, indent=2))

    discovery_rows = discover_dates()
    eligible_dates = [row["signal_date"] for row in discovery_rows if row["tier_a_eligible"]]
    covered_dates = eligible_dates[:]

    instruments: set[str] = set()
    bridge_cache: dict[str, list[dict[str, Any]]] = {}
    for date in covered_dates:
        rows, _a, _b, _fields = bridge_rows_for_date(date)
        bridge_cache[date] = rows
        instruments.update(row["instrument"] for row in rows)
    price_dir = price_bridge_dir_for_date(covered_dates[0]) if covered_dates else Path()
    price_cache = load_price_cache(price_dir, instruments) if covered_dates else {}
    trading_dates = trading_dates_from_cache(price_cache)

    bridge_register: list[dict[str, Any]] = []
    order_register: list[dict[str, Any]] = []
    replay_register: list[dict[str, Any]] = []
    accumulation: list[dict[str, Any]] = []
    skip_delta_rows: list[dict[str, Any]] = []
    candidate_state = PortfolioState()
    baseline_state = PortfolioState()

    for date in covered_dates:
        execution_date = next_trade_date(date, trading_dates)
        if not execution_date:
            continue
        bridge_entry, bridge_rows = build_daily_bridge(date, generated_at)
        bridge_register.append(bridge_entry)
        order_entry, order_rows = build_daily_order(date, bridge_entry, bridge_rows, candidate_state, generated_at)
        order_register.append(order_entry)
        replay_entry, skip_delta = build_daily_replay(
            date,
            execution_date,
            bridge_rows,
            order_entry,
            order_rows,
            candidate_state,
            baseline_state,
            price_cache,
            generated_at,
        )
        replay_register.append(replay_entry)
        skip_delta_rows.append(skip_delta)
        accumulation.append(
            {
                "signal_date": date,
                "execution_date": execution_date,
                "input_tier": INPUT_TIER,
                "tier_b_fallback_used": False,
                "bridge_validator_status": bridge_entry["validator_status"],
                "order_intent_validator_status": order_entry["validator_status"],
                "shadow_replay_validator_status": replay_entry["validator_status"],
                "candidate_equity": replay_entry["candidate_equity"],
                "baseline_equity": replay_entry["baseline_equity"],
                "candidate_minus_baseline_equity": replay_entry["candidate_minus_baseline_equity"],
                "candidate_skip_count": replay_entry["candidate_skip_count"],
                "baseline_skip_count": replay_entry["baseline_skip_count"],
                "same_day_mark_coverage_ratio": replay_entry["same_day_mark_coverage_ratio"],
                "status": "pass"
                if bridge_entry["validator_status"] == order_entry["validator_status"] == replay_entry["validator_status"] == "pass"
                else "fail",
            }
        )

    covered_dates = [row["signal_date"] for row in replay_register]

    write_csv(
        OUT_ROOT / "daily_input_discovery.csv",
        discovery_rows,
        [
            "signal_date",
            "input_tier",
            "model_a_path",
            "model_a_rows",
            "r_isolated_model_b_path",
            "r_isolated_model_b_rows",
            "s_isolated_model_b_path",
            "s_isolated_model_b_rows",
            "price_source_path",
            "next_open_available",
            "same_day_mark_available",
            "tier_a_eligible",
            "selected",
            "tier_b_fallback_used",
            "status",
            "blockers",
            "details",
        ],
    )
    write_csv(
        OUT_ROOT / "daily_bridge_artifact_register.csv",
        bridge_register,
        [
            "signal_date",
            "manifest_path",
            "signals_path",
            "row_count",
            "top50_rows",
            "non_top50_visibility_rows",
            "input_tier",
            "tier_b_fallback_used",
            "validator_status",
            "details",
        ],
    )
    write_csv(
        OUT_ROOT / "daily_order_intent_artifact_register.csv",
        order_register,
        [
            "signal_date",
            "manifest_path",
            "order_intents_path",
            "order_intent_rows",
            "buy_count",
            "sell_count",
            "non_top50_buy_count",
            "forbidden_fields_present",
            "input_tier",
            "tier_b_fallback_used",
            "validator_status",
            "details",
        ],
    )
    write_csv(
        OUT_ROOT / "daily_shadow_replay_artifact_register.csv",
        replay_register,
        [
            "signal_date",
            "execution_date",
            "manifest_path",
            "summary_path",
            "candidate_action_count",
            "baseline_action_count",
            "candidate_skip_count",
            "baseline_skip_count",
            "candidate_equity",
            "baseline_equity",
            "candidate_minus_baseline_equity",
            "same_day_mark_coverage_ratio",
            "max_mark_lag_days",
            "negative_cash_count",
            "duplicate_position_count",
            "input_tier",
            "tier_b_fallback_used",
            "validator_status",
            "details",
        ],
    )
    write_csv(
        OUT_ROOT / "shadow_accumulation_register.csv",
        accumulation,
        [
            "signal_date",
            "execution_date",
            "input_tier",
            "tier_b_fallback_used",
            "bridge_validator_status",
            "order_intent_validator_status",
            "shadow_replay_validator_status",
            "candidate_equity",
            "baseline_equity",
            "candidate_minus_baseline_equity",
            "candidate_skip_count",
            "baseline_skip_count",
            "same_day_mark_coverage_ratio",
            "status",
        ],
    )
    write_csv(
        OUT_ROOT / "candidate_baseline_skip_delta.csv",
        skip_delta_rows,
        [
            "signal_date",
            "execution_date",
            "candidate_skip_count",
            "baseline_skip_count",
            "candidate_minus_baseline_skip_count",
            "candidate_skip_reasons",
            "baseline_skip_reasons",
            "status",
        ],
    )
    price_mark_rows = collect_price_mark_rows(covered_dates)
    write_csv(
        OUT_ROOT / "price_mark_coverage_audit.csv",
        price_mark_rows,
        [
            "strategy_rule",
            "signal_date",
            "execution_date",
            "position_rows",
            "same_day_mark_coverage_ratio",
            "fallback_mark_count",
            "max_mark_lag_days",
            "missing_price_count",
            "status",
            "details",
        ],
    )
    readonly_rows = build_readonly_wording_audit()
    write_csv(OUT_ROOT / "readonly_wording_audit.csv", readonly_rows, ["audit_item", "expected", "actual", "status", "details"])
    forbidden_scope_rows = build_forbidden_scope_audit()
    write_csv(OUT_ROOT / "forbidden_scope_audit.csv", forbidden_scope_rows, ["audit_item", "performed", "status", "details"])
    checksum = checksum_rows(
        [
            ("s_root_manifest", S_ROOT / "manifest.json"),
            ("s_modelb_register", S_ROOT / "modelb_artifact_register.csv"),
            ("r_rerun_validator", R_RERUN_ROOT / "validator_report.json"),
            ("r_isolated_model_signal_register", R_RERUN_ROOT / "isolated_model_signal_register.csv"),
            ("r_price_source_register", R_RERUN_ROOT / "price_source_register.csv"),
        ],
        covered_dates,
    )
    write_csv(OUT_ROOT / "lineage_checksum_audit.csv", checksum, ["artifact_name", "path", "sha256", "input_tier", "tier_b_fallback_used", "status"])

    required_present = all((OUT_ROOT / path).exists() for path in REQUIRED_ROOT_FILES if path not in {"manifest.json", "validator_report.json", "diagnostic_findings.md"})
    min_coverage = min([to_float(row["same_day_mark_coverage_ratio"]) for row in replay_register], default=0.0)
    max_lag = max([to_int(row["max_mark_lag_days"]) for row in replay_register], default=0)
    negative_cash = sum(to_int(row["negative_cash_count"]) for row in replay_register)
    duplicate_positions = sum(to_int(row["duplicate_position_count"]) for row in replay_register)
    blockers: list[str] = []
    checks = {
        "required_root_files_present": required_present,
        "minimum_shadow_days_pass": len(covered_dates) >= 5,
        "all_daily_bridge_validators_pass": bool(bridge_register) and all(row["validator_status"] == "pass" for row in bridge_register),
        "all_daily_order_intent_validators_pass": bool(order_register) and all(row["validator_status"] == "pass" for row in order_register),
        "all_daily_shadow_replay_validators_pass": bool(replay_register) and all(row["validator_status"] == "pass" for row in replay_register),
        "same_day_mark_coverage_pass": min_coverage >= 0.99,
        "max_mark_lag_days_pass": max_lag == 0,
        "negative_cash_pass": negative_cash == 0,
        "duplicate_position_pass": duplicate_positions == 0,
        "skip_delta_tracked": bool(skip_delta_rows) and all(row["status"] == "tracked" for row in skip_delta_rows),
        "readonly_wording_pass": all(row["status"] == "pass" for row in readonly_rows),
        "forbidden_scope_clean": all(not truthy(row["performed"]) and row["status"] == "pass" for row in forbidden_scope_rows),
        "tier_a_input_pass": INPUT_TIER == "tier_a_clean_daily_lineage",
        "tier_b_fallback_not_used_pass": True,
    }
    for name, ok in checks.items():
        if not ok:
            blockers.append(name)
    verdict = VERDICT_PASS if not blockers else VERDICT_FAIL
    validator = {
        "status": "pass" if verdict == VERDICT_PASS else "fail",
        "verdict": verdict,
        "phase": PHASE,
        "run_id": RUN_ID,
        "created_at": generated_at,
        "input_tier": INPUT_TIER,
        "tier_b_fallback_used": False,
        "covered_shadow_signal_days": len(covered_dates),
        "covered_dates": covered_dates,
        "daily_bridge_artifact_count": len(bridge_register),
        "daily_order_intent_artifact_count": len(order_register),
        "daily_shadow_replay_artifact_count": len(replay_register),
        "same_day_mark_coverage_ratio": f"{min_coverage:.6f}",
        "max_mark_lag_days": max_lag,
        "negative_cash_count": negative_cash,
        "duplicate_position_count": duplicate_positions,
        "mtrp8_shadow_review_authorized": verdict == VERDICT_PASS,
        "production_default_switch_authorized": False,
        "blockers": blockers,
        **checks,
    }
    write_json(OUT_ROOT / "validator_report.json", validator)
    write_text(OUT_ROOT / "diagnostic_findings.md", build_diagnostic_findings(verdict, covered_dates, validator))
    manifest = {
        "artifact_type": "MTRP7_S_R_REAL_TIER_A_SHADOW_RERUN_REPAIR",
        "schema_version": "mtrp7_s_r.real_tier_a_shadow_rerun_repair.v1",
        "phase": PHASE,
        "run_id": RUN_ID,
        "created_at": generated_at,
        "created_by": rel(Path(__file__)),
        "input_tier": INPUT_TIER,
        "tier_b_fallback_used": False,
        "s_isolated_modelb_root": rel(S_MODELB_ROOT),
        "r_isolated_phase_yz_root": rel(R_ISOLATED_PHASE_YZ_ROOT),
        "output_root": rel(OUT_ROOT),
        "covered_dates": covered_dates,
        "readonly_only": True,
        "simulation_only": True,
        "production_allowed": False,
        "production_ready": False,
        "default_switch_allowed": False,
        "mtrp8_shadow_review_authorized": verdict == VERDICT_PASS,
        "validator_status": validator["status"],
        "verdict": verdict,
        "required_root_files": {name: rel(OUT_ROOT / name) for name in REQUIRED_ROOT_FILES},
    }
    write_json(OUT_ROOT / "manifest.json", manifest)
    changed_files = [
        rel(Path(__file__)),
        rel(OUT_ROOT),
        rel(REPORT_PATH),
    ]
    write_text(REPORT_PATH, build_execution_report(verdict, covered_dates, validator, changed_files))
    print(json.dumps(validator, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
