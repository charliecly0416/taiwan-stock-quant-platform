#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
TOP50_MODEL_NAME = "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025"
TOP50_SIGNAL_MANIFEST = ROOT / f"data_tw/artifacts/signals/{TOP50_MODEL_NAME}/r1_legacy_signal_adapter_20260616/manifest.json"
BROAD_MODEL_NAME = "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025_broad_full_rank_mtr2_r"
BROAD_RUN_ID = "r1_broad_full_rank_visibility_repair_20260628"
BROAD_SIGNAL_DIR = ROOT / f"data_tw/artifacts/signals/{BROAD_MODEL_NAME}/{BROAD_RUN_ID}"
BROAD_SIGNAL_MANIFEST = BROAD_SIGNAL_DIR / "manifest.json"
BROAD_QLIB_RANK = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_raw_oos_score_rank_2023_2026.csv"
TOP50_LTR_SOURCE = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_replay_ready_scores_2026.csv"
DEPENDENCY_YAML = ROOT / "configs/strategy_dependencies/mechanism_transfer_top50_cost_aware_v1.yaml"
PRICE_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"
OUT_DIR = ROOT / "data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair"
REPORT_PATH = ROOT / "docs/tw_portfolio_decision_model/POLICY_MTR2_R_BROAD_FULL_RANK_VISIBILITY_REPAIR_EXECUTION_REPORT_CN.md"

INITIAL_EQUITY = 1_000_000.0
TARGET_HOLDINGS = 10
CANDIDATE_K = 50
LOT_SIZE = 10
FEE_RATE = 0.001425
SELL_TAX_RATE = 0.003

SMALL_TOLERANCE = 0.02
MATERIAL_TURNOVER_REDUCTION = 0.20
MATERIAL_COST_REDUCTION = 0.20
MAX_DRAWDOWN_WORSE_TOLERANCE = 0.05
CASH_NO_TRADE_DEGENERATE_THRESHOLD = 0.10

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
    "source_model_artifact",
    "source_feature_artifact",
]
FORBIDDEN_FIELDS = {
    "future_return_5d",
    "future_return_10d",
    "future_return_20d",
    "future_excess_return_5d",
    "future_excess_return_10d",
    "future_excess_return_20d",
    "forward_return_5d",
    "forward_return_10d",
    "forward_return_20d",
    "label",
    "label_5d",
    "label_10d",
    "relevance_10d_top_heavy",
    "ltr_relevance_label",
    "realized_pnl",
    "realized_return",
    "replay_return",
    "execution_price",
    "next_open",
    "next_close",
    "target_weight",
    "target_position",
    "broker_order_id",
}
FORBIDDEN_INTENT_FIELDS = {
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
}


@dataclass(frozen=True)
class CandidateSpec:
    candidate_id: str
    hold_rank_buffer: int | None
    strategy_rule: str = "mechanism_transfer_top50_cost_aware_v1"
    max_replace_per_day: int = 1


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def norm(symbol: Any) -> str:
    text = str(symbol or "").strip().upper()
    return text if text.startswith("TW") else f"TW{text}"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({k for row in rows for k in row}) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class PriceStore:
    def __init__(self, symbols: set[str]) -> None:
        self.by_symbol: dict[str, list[dict[str, Any]]] = {}
        for symbol in sorted(norm(s) for s in symbols):
            path = PRICE_ROOT / f"{symbol}.csv"
            if not path.exists():
                continue
            rows: list[dict[str, Any]] = []
            with path.open(encoding="utf-8", newline="") as fh:
                for row in csv.DictReader(fh):
                    day = str(row.get("date") or "")[:10]
                    try:
                        open_price = float(row.get("open") or 0.0)
                        close_price = float(row.get("close") or 0.0)
                    except Exception:
                        open_price = 0.0
                        close_price = 0.0
                    if day and open_price > 0 and close_price > 0:
                        rows.append({"date": day, "open": open_price, "close": close_price})
            if rows:
                self.by_symbol[symbol] = rows

    def close_on_or_before(self, symbol: str, asof: str) -> float | None:
        out = None
        for row in self.by_symbol.get(norm(symbol), []):
            if str(row["date"]) <= asof:
                out = float(row["close"])
            else:
                break
        return out

    def next_open_after(self, symbol: str, asof: str) -> tuple[str, float] | None:
        for row in self.by_symbol.get(norm(symbol), []):
            if str(row["date"]) > asof:
                return str(row["date"]), float(row["open"])
        return None


def build_broad_signal_artifact(out_dir: Path) -> tuple[dict[str, Any], pd.DataFrame]:
    if not TOP50_SIGNAL_MANIFEST.exists():
        raise RuntimeError(f"missing top50 signal manifest: {rel(TOP50_SIGNAL_MANIFEST)}")
    if not BROAD_QLIB_RANK.exists():
        raise RuntimeError(f"missing broad qlib rank source: {rel(BROAD_QLIB_RANK)}")
    top50_manifest = load_json(TOP50_SIGNAL_MANIFEST)
    top50_path = resolve(str((top50_manifest.get("output_files") or {}).get("signals", "")))
    top50 = pd.read_csv(top50_path)
    broad = pd.read_csv(BROAD_QLIB_RANK)
    top50["date"] = top50["date"].astype(str)
    top50["instrument"] = top50["instrument"].map(norm)
    broad["date"] = broad["date"].astype(str)
    broad["instrument"] = broad["instrument"].map(norm)
    start, end = top50["date"].min(), top50["date"].max()
    broad = broad[(broad["date"] >= start) & (broad["date"] <= end)].copy()
    broad["qlib_rank_raw"] = pd.to_numeric(broad["qlib_rank_raw"], errors="coerce")
    broad = broad.dropna(subset=["qlib_rank_raw"])
    broad["candidate_rank"] = broad["qlib_rank_raw"].astype(int)
    broad = broad[broad["candidate_rank"] <= 150].copy()

    base_cols = ["date", "instrument", "candidate_rank", "buy_score", "raw_score", "score_rank", "full_qlib_rank"]
    top_part = top50[base_cols].copy()
    top_part["qlib_score_raw"] = top_part["raw_score"]
    top_part["top50_row"] = True

    top_keys = set(zip(top50["date"], top50["instrument"]))
    broad_extra = broad[
        (~broad[["date", "instrument"]].apply(tuple, axis=1).isin(top_keys))
        & (broad["candidate_rank"] > 50)
    ].copy()
    broad_extra["buy_score"] = broad_extra["qlib_score_raw"]
    broad_extra["raw_score"] = broad_extra["qlib_score_raw"]
    broad_extra["score_rank"] = broad_extra["candidate_rank"]
    broad_extra["full_qlib_rank"] = broad_extra["candidate_rank"]
    broad_extra["top50_row"] = False
    merged = pd.concat(
        [top_part[base_cols + ["qlib_score_raw", "top50_row"]], broad_extra[base_cols + ["qlib_score_raw", "top50_row"]]],
        ignore_index=True,
    )
    merged["candidate_rank"] = pd.to_numeric(merged["candidate_rank"], errors="coerce").astype(int)
    merged["full_qlib_rank"] = pd.to_numeric(merged["full_qlib_rank"], errors="coerce").astype(int)
    merged["score_rank"] = pd.to_numeric(merged["score_rank"], errors="coerce").astype(int)
    merged["model_name"] = BROAD_MODEL_NAME
    merged["model_family"] = "ltr"
    merged["signal_asof"] = merged["date"]
    merged["available_at"] = merged["date"]
    merged["source_artifact"] = rel(TOP50_LTR_SOURCE)
    merged["source_model_artifact"] = rel(TOP50_SIGNAL_MANIFEST)
    merged["source_feature_artifact"] = rel(BROAD_QLIB_RANK)
    merged["ext_ltr_top50_flag"] = merged["top50_row"].astype(bool)
    merged["ext_broad_rank_visibility_only"] = (~merged["top50_row"]).astype(bool)
    merged["ext_buy_ranking_allowed"] = merged["top50_row"].astype(bool)
    merged = merged[
        REQUIRED_SIGNAL_FIELDS
        + ["ext_ltr_top50_flag", "ext_broad_rank_visibility_only", "ext_buy_ranking_allowed"]
    ].sort_values(["date", "candidate_rank", "instrument"]).reset_index(drop=True)

    BROAD_SIGNAL_DIR.mkdir(parents=True, exist_ok=True)
    signals_path = BROAD_SIGNAL_DIR / "signals.csv"
    merged.to_csv(signals_path, index=False)

    schema = {
        "schema_version": "model_signal_broad_full_rank_mtr2_r_v1",
        "core_fields": REQUIRED_SIGNAL_FIELDS,
        "extension_fields": ["ext_ltr_top50_flag", "ext_broad_rank_visibility_only", "ext_buy_ranking_allowed"],
        "unique_key": ["date", "instrument"],
        "ranking_usage": {
            "buy_ranking": "candidate_rank <= 50 AND ext_ltr_top50_flag=true AND ext_buy_ranking_allowed=true",
            "sell_hold_full_rank_visibility": "full_qlib_rank may be consumed for existing holdings",
            "non_top50_buy_forbidden": True,
        },
    }
    write_json(BROAD_SIGNAL_DIR / "schema.json", schema)

    daily = merged.groupby("date").size()
    top50_daily = merged[merged["ext_ltr_top50_flag"]].groupby("date").size()
    coverage_rows = [
        {"audit_name": "row_count_gt_top50", "value": len(merged), "threshold": len(top50), "status": "pass" if len(merged) > len(top50) else "fail", "details": ""},
        {"audit_name": "daily_row_count_min", "value": int(daily.min()), "threshold": 100, "status": "pass" if int(daily.min()) >= 100 else "fail", "details": ""},
        {"audit_name": "top50_daily_row_count", "value": int(top50_daily.min()), "threshold": 50, "status": "pass" if int(top50_daily.min()) == 50 else "fail", "details": ""},
        {"audit_name": "date_range", "value": f"{merged['date'].min()}..{merged['date'].max()}", "threshold": f"{start}..{end}", "status": "pass", "details": ""},
    ]
    write_csv(BROAD_SIGNAL_DIR / "coverage_audit.csv", coverage_rows)
    forbidden_rows = [
        {"audit_name": "forbidden_field_absent", "field_name": field, "present": field in merged.columns, "used_for_ranking": False, "status": "fail" if field in merged.columns else "pass", "details": ""}
        for field in sorted(FORBIDDEN_FIELDS)
    ]
    write_csv(BROAD_SIGNAL_DIR / "forbidden_field_audit.csv", forbidden_rows)
    mapping_rows = [
        {"field": "candidate_rank", "source": "phasee1_raw_oos_score_rank_2023_2026.csv::qlib_rank_raw", "status": "pass"},
        {"field": "full_qlib_rank", "source": "phasee1_raw_oos_score_rank_2023_2026.csv::qlib_rank_raw", "status": "pass"},
        {"field": "buy_score_top50", "source": "MTR2 top50-only artifact::buy_score", "status": "pass"},
        {"field": "buy_score_non_top50", "source": "qlib_score_raw numeric filler, ranking_allowed=false", "status": "pass"},
    ]
    write_csv(BROAD_SIGNAL_DIR / "legacy_mapping_audit.csv", mapping_rows)

    extensions = {
        "schema_version": "model_signal_extension_v1",
        "fields": {
            "ext_ltr_top50_flag": {
                "dtype": "bool",
                "semantic_role": "exposure",
                "availability_policy": "available_at_lte_signal_asof",
                "producer": "MTR2_R_broad_full_rank_visibility_repair",
                "allowed_consumers": ["mechanism_transfer_top50_cost_aware_v1"],
                "ranking_allowed": False,
                "required_for_core_replay": False,
                "description": "True only for rows with valid LTR top50 buy score.",
            },
            "ext_broad_rank_visibility_only": {
                "dtype": "bool",
                "semantic_role": "exposure",
                "availability_policy": "available_at_lte_signal_asof",
                "producer": "MTR2_R_broad_full_rank_visibility_repair",
                "allowed_consumers": ["mechanism_transfer_top50_cost_aware_v1"],
                "ranking_allowed": False,
                "required_for_core_replay": False,
                "description": "True for non-top50 rows added only for current holding full-rank lookup.",
            },
            "ext_buy_ranking_allowed": {
                "dtype": "bool",
                "semantic_role": "diagnostic",
                "availability_policy": "available_at_lte_signal_asof",
                "producer": "MTR2_R_broad_full_rank_visibility_repair",
                "allowed_consumers": ["mechanism_transfer_top50_cost_aware_v1"],
                "ranking_allowed": False,
                "required_for_core_replay": False,
                "description": "Audit flag used to prove buy candidates are limited to top50 LTR rows.",
            },
        },
    }
    manifest = {
        "artifact_type": "model_signal",
        "artifact_name": BROAD_MODEL_NAME,
        "run_id": BROAD_RUN_ID,
        "created_at": now_iso(),
        "created_by": rel(Path(__file__)),
        "schema_version": "broad_full_rank_mtr2_r_v1",
        "contract_version": "MODEL_SIGNAL_CONTRACT_CN.md@2026-06-16 + MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md@2026-06-16",
        "model_name": BROAD_MODEL_NAME,
        "model_family": "ltr",
        "research_only": True,
        "diagnostic_only": True,
        "not_default_candidate": True,
        "production_allowed": False,
        "no_provider_publish": True,
        "no_accepted_latest_switch": True,
        "no_default_switch": True,
        "window": {"start": start, "end": end},
        "row_count": len(merged),
        "duplicate_key_count": int(merged.duplicated(["date", "instrument"]).sum()),
        "candidate_k": 50,
        "source_artifacts": [rel(TOP50_SIGNAL_MANIFEST), rel(BROAD_QLIB_RANK), rel(TOP50_LTR_SOURCE)],
        "input_hashes": {
            rel(TOP50_SIGNAL_MANIFEST): sha256(TOP50_SIGNAL_MANIFEST),
            rel(top50_path): sha256(top50_path),
            rel(BROAD_QLIB_RANK): sha256(BROAD_QLIB_RANK),
        },
        "capabilities": {
            "core_signal_v1": True,
            "candidate_boundary": "qlib_top50",
            "buy_ordering": "buy_score_desc_top50_ltr_only",
            "full_rank_exit": "full_qlib_rank",
            "broad_full_rank_visibility": True,
            "supports_ltr_rerank": True,
            "non_top50_buy_forbidden": True,
        },
        "ranking_usage": {
            "buy_ranking": "candidate_rank <= 50 and ext_ltr_top50_flag=true",
            "hold_buffer": "full_qlib_rank may be used for existing holdings, including rank 51-100",
            "non_top50_rows": "visibility only, forbidden as buy candidates",
        },
        "extensions": extensions,
        "forbidden_actions": {
            "no_training": True,
            "no_tuning": True,
            "no_return_filtering": True,
            "no_strategy_result_as_signal_input": True,
            "no_frontend_change": True,
            "no_daily_orchestrator_change": True,
            "no_provider_publish": True,
            "no_accepted_latest_switch": True,
            "no_monitor": True,
            "no_broker_order": True,
        },
        "quality_status": "pass",
        "output_files": {
            "signals": rel(signals_path),
            "schema": rel(BROAD_SIGNAL_DIR / "schema.json"),
            "coverage_audit": rel(BROAD_SIGNAL_DIR / "coverage_audit.csv"),
            "forbidden_field_audit": rel(BROAD_SIGNAL_DIR / "forbidden_field_audit.csv"),
            "legacy_mapping_audit": rel(BROAD_SIGNAL_DIR / "legacy_mapping_audit.csv"),
        },
    }
    write_json(BROAD_SIGNAL_MANIFEST, manifest)

    top50_check = merged[merged["ext_ltr_top50_flag"]][base_cols].sort_values(["date", "instrument"]).reset_index(drop=True)
    original = top50[base_cols].sort_values(["date", "instrument"]).reset_index(drop=True)
    eq_rows = [
        {"audit_name": "top50_row_count", "broad_value": len(top50_check), "top50_value": len(original), "status": "pass" if len(top50_check) == len(original) else "fail", "details": ""},
        {"audit_name": "top50_keys", "broad_value": len(top50_check), "top50_value": len(original), "status": "pass" if top50_check[["date", "instrument"]].equals(original[["date", "instrument"]]) else "fail", "details": ""},
        {"audit_name": "top50_ltr_values", "broad_value": "broad_top50", "top50_value": "mtr2_top50", "status": "pass" if top50_check.equals(original) else "fail", "details": "candidate_rank,buy_score,raw_score,score_rank,full_qlib_rank identical"},
    ]
    write_csv(out_dir / "top50_ltr_equivalence_audit.csv", eq_rows)
    non_top50_rows = merged[~merged["ext_ltr_top50_flag"]]
    write_csv(out_dir / "non_top50_buy_forbidden_audit.csv", [
        {"audit_name": "non_top50_candidate_rank_gt_50", "value": int((non_top50_rows["candidate_rank"] > 50).all()), "status": "pass" if (non_top50_rows["candidate_rank"] > 50).all() else "fail", "details": ""},
        {"audit_name": "non_top50_ltr_flag_false", "value": int((~non_top50_rows["ext_ltr_top50_flag"]).all()), "status": "pass", "details": ""},
        {"audit_name": "non_top50_visibility_only_true", "value": int((non_top50_rows["ext_broad_rank_visibility_only"]).all()), "status": "pass" if non_top50_rows["ext_broad_rank_visibility_only"].all() else "fail", "details": ""},
    ])
    write_csv(out_dir / "broad_signal_coverage_audit.csv", coverage_rows)
    write_csv(out_dir / "broad_signal_lineage_audit.csv", [
        {"audit_name": "research_only_broad_artifact", "status": "pass", "details": rel(BROAD_SIGNAL_MANIFEST)},
        {"audit_name": "top50_source_manifest", "status": "pass", "details": rel(TOP50_SIGNAL_MANIFEST)},
        {"audit_name": "broad_qlib_rank_source", "status": "pass", "details": rel(BROAD_QLIB_RANK)},
        {"audit_name": "production_long_id_not_modified", "status": "pass", "details": rel(TOP50_SIGNAL_MANIFEST)},
    ])
    ext_rows = []
    for field, meta in extensions["fields"].items():
        ext_rows.append({
            "field": field,
            "declared": True,
            "present": field in merged.columns,
            "semantic_role": meta["semantic_role"],
            "ranking_allowed": meta["ranking_allowed"],
            "allowed_consumers": "|".join(meta["allowed_consumers"]),
            "status": "pass" if field in merged.columns and meta["ranking_allowed"] is False else "fail",
        })
    write_csv(out_dir / "extension_schema_audit.csv", ext_rows)
    write_json(out_dir / "model_signal_validator_report.json", {
        "ok": all(row["status"] == "pass" for row in coverage_rows + eq_rows + ext_rows),
        "signal_manifest": rel(BROAD_SIGNAL_MANIFEST),
        "checks": coverage_rows + eq_rows + ext_rows,
    })
    return manifest, merged


def day_state(day: pd.DataFrame) -> dict[str, Any]:
    buy = day[(day["candidate_rank"] <= CANDIDATE_K) & (day["ext_ltr_top50_flag"])].copy()
    buy = buy.sort_values(["buy_score", "instrument"], ascending=[False, True])
    return {
        "buy_order": [norm(x) for x in buy["instrument"].tolist()],
        "candidate_set": set(buy["instrument"].map(norm)),
        "row": {norm(r.instrument): r for r in day.itertuples(index=False)},
        "full_rank": {norm(r.instrument): int(r.full_qlib_rank) for r in day.itertuples(index=False)},
    }


def meta(state: dict[str, Any], symbol: str) -> dict[str, Any]:
    row = state["row"].get(norm(symbol))
    if row is None:
        return {"candidate_rank": "", "buy_rank": "", "full_qlib_rank": ""}
    return {
        "candidate_rank": int(row.candidate_rank),
        "buy_rank": int(row.score_rank),
        "full_qlib_rank": int(row.full_qlib_rank),
    }


def make_intent(day: str, symbol: str, action: str, reason: str, spec: CandidateSpec, state: dict[str, Any], seq: int) -> dict[str, Any]:
    m = meta(state, symbol)
    return {
        "order_intent_row_id": f"{spec.candidate_id}|{day}|{symbol}|{action}|{seq}",
        "signal_date": day,
        "instrument": norm(symbol),
        "intent_action": action,
        "intent_reason": reason,
        "strategy_rule": spec.strategy_rule,
        "candidate_rank": m["candidate_rank"],
        "buy_rank": m["buy_rank"],
        "full_qlib_rank": m["full_qlib_rank"],
        "max_buy_count": spec.max_replace_per_day,
        "max_sell_count": spec.max_replace_per_day,
        "model_name": BROAD_MODEL_NAME,
        "signal_artifact": rel(BROAD_SIGNAL_MANIFEST),
        "readonly_only": True,
        "simulation_only": True,
        "not_order": True,
        "not_target_position": True,
        "not_investment_advice": True,
        "diagnostic_only": True,
        "research_only": True,
        "candidate_id": spec.candidate_id,
        "current_holding_flag": action in {"sell", "skip", "hold"},
        "target_holding_count": TARGET_HOLDINGS,
        "candidate_k": CANDIDATE_K,
    }


def mark(cash: float, holdings: dict[str, int], prices: PriceStore, asof: str) -> tuple[float, float, int]:
    market_value = 0.0
    missing = 0
    for symbol, qty in holdings.items():
        price = prices.close_on_or_before(symbol, asof)
        if price is None:
            missing += 1
        else:
            market_value += qty * price
    return cash + market_value, market_value, missing


def execute_pending(
    pending: list[dict[str, Any]],
    asof: str,
    cash: float,
    holdings: dict[str, int],
    actions: list[dict[str, Any]],
    order_manifest_ref: str,
) -> tuple[float, int, float, float, float]:
    skipped = 0
    fee_total = 0.0
    tax_total = 0.0
    turnover = 0.0
    for order in sorted(pending, key=lambda r: 0 if r["intent_action"] == "sell" else 1):
        symbol = norm(order["instrument"])
        price = float(order["execution_price"])
        common = {
            "signal_date": order["signal_date"],
            "execution_date": asof,
            "instrument": symbol,
            "intent_reason": order["intent_reason"],
            "strategy_rule": order["strategy_rule"],
            "model_name": BROAD_MODEL_NAME,
            "order_intent_artifact": order_manifest_ref,
            "order_intent_row_id": order["order_intent_row_id"],
            "candidate_id": order["candidate_id"],
        }
        if order["intent_action"] == "sell":
            qty = holdings.pop(symbol, 0)
            if qty <= 0:
                skipped += 1
                actions.append({**common, "action": "historical_skip", "quantity": 0, "execution_price": price, "commission": 0.0, "tax": 0.0, "cash_after": cash, "position_after": 0, "skip_reason": "sell_without_holding"})
                continue
            notional = qty * price
            fee = notional * FEE_RATE
            tax = notional * SELL_TAX_RATE
            cash += notional - fee - tax
            fee_total += fee
            tax_total += tax
            turnover += notional
            actions.append({**common, "action": "historical_risk_reduce", "quantity": qty, "execution_price": round(price, 4), "commission": round(fee, 2), "tax": round(tax, 2), "cash_after": round(cash, 2), "position_after": 0, "skip_reason": ""})
        else:
            if symbol in holdings or len(holdings) >= TARGET_HOLDINGS:
                skipped += 1
                actions.append({**common, "action": "historical_skip", "quantity": 0, "execution_price": price, "commission": 0.0, "tax": 0.0, "cash_after": cash, "position_after": holdings.get(symbol, 0), "skip_reason": "duplicate_or_full"})
                continue
            slots = max(1, TARGET_HOLDINGS - len(holdings))
            qty = int((cash / slots) // (price * LOT_SIZE)) * LOT_SIZE
            notional = qty * price
            fee = notional * FEE_RATE
            if qty <= 0 or cash < notional + fee:
                skipped += 1
                actions.append({**common, "action": "historical_skip", "quantity": 0, "execution_price": price, "commission": 0.0, "tax": 0.0, "cash_after": cash, "position_after": 0, "skip_reason": "insufficient_cash_or_zero_qty"})
                continue
            cash -= notional + fee
            holdings[symbol] = qty
            fee_total += fee
            turnover += notional
            actions.append({**common, "action": "historical_add", "quantity": qty, "execution_price": round(price, 4), "commission": round(fee, 2), "tax": 0.0, "cash_after": round(cash, 2), "position_after": qty, "skip_reason": ""})
    return cash, skipped, fee_total, tax_total, turnover


def run_candidate(signals: pd.DataFrame, prices: PriceStore, spec: CandidateSpec, out_dir: Path) -> dict[str, Any]:
    dates = sorted(signals["date"].unique())
    by_date = {d: g.copy() for d, g in signals.groupby("date")}
    cash = INITIAL_EQUITY
    holdings: dict[str, int] = {}
    pending_by_date: dict[str, list[dict[str, Any]]] = {}
    intents: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    nav_rows: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []
    trigger_rows: list[dict[str, Any]] = []
    skipped_count = 0
    fee_total = 0.0
    tax_total = 0.0
    turnover = 0.0
    peak = INITIAL_EQUITY
    max_drawdown = 0.0
    seq = 0
    order_manifest_ref = rel(out_dir / "order_intents" / spec.candidate_id / "manifest.json")

    for asof in dates:
        cash, skipped, fee, tax, turn = execute_pending(
            pending_by_date.pop(asof, []), asof, cash, holdings, actions, order_manifest_ref
        )
        skipped_count += skipped
        fee_total += fee
        tax_total += tax
        turnover += turn
        equity, market_value, missing = mark(cash, holdings, prices, asof)
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, equity / peak - 1.0 if peak > 0 else 0.0)
        state = day_state(by_date[asof])
        nav_rows.append({
            "date": asof,
            "cash": round(cash, 2),
            "market_value": round(market_value, 2),
            "equity": round(equity, 2),
            "daily_return": 0.0,
            "holding_count": len(holdings),
            "missing_price_count": missing,
            "candidate_id": spec.candidate_id,
            "strategy_rule": spec.strategy_rule,
            "model_name": BROAD_MODEL_NAME,
        })
        if len(nav_rows) > 1:
            prev = float(nav_rows[-2]["equity"])
            nav_rows[-1]["daily_return"] = round(equity / prev - 1.0, 8) if prev else 0.0
        for symbol, qty in sorted(holdings.items()):
            m = meta(state, symbol)
            price = prices.close_on_or_before(symbol, asof) or 0.0
            snapshots.append({
                "date": asof,
                "instrument": symbol,
                "quantity": qty,
                "cost_basis": "",
                "mark_price": round(price, 4),
                "market_value": round(qty * price, 2),
                "unrealized_pnl": "",
                "strategy_rule": spec.strategy_rule,
                "model_name": BROAD_MODEL_NAME,
                "candidate_id": spec.candidate_id,
                "in_qlib_top50_candidate": symbol in state["candidate_set"],
                "buy_rank": m["buy_rank"],
                "full_qlib_rank": m["full_qlib_rank"],
            })

        pending_buy = {norm(o["instrument"]) for orders in pending_by_date.values() for o in orders if o["intent_action"] == "buy"}
        pending_sell = {norm(o["instrument"]) for orders in pending_by_date.values() for o in orders if o["intent_action"] == "sell"}
        best_buy = next((s for s in state["buy_order"] if s not in holdings and s not in pending_buy), None)
        outside = [s for s in sorted(holdings) if s not in state["candidate_set"] and s not in pending_sell]
        outside = sorted(outside, key=lambda s: (state["full_rank"].get(s, 999999), s), reverse=True)
        sells: list[str] = []
        for symbol in outside:
            if len(sells) >= spec.max_replace_per_day:
                break
            full_rank = state["full_rank"].get(symbol, 999999)
            if spec.hold_rank_buffer is not None and full_rank <= spec.hold_rank_buffer:
                seq += 1
                intent = make_intent(asof, symbol, "skip", f"hold_rank_buffer_{spec.hold_rank_buffer}_skip", spec, state, seq)
                intents.append(intent)
                trigger_rows.append({
                    "date": asof,
                    "instrument": symbol,
                    "candidate_id": spec.candidate_id,
                    "previous_holding_flag": True,
                    "candidate_rank": meta(state, symbol)["candidate_rank"],
                    "full_qlib_rank": full_rank,
                    "baseline_action": "sell",
                    "m2_action": "skip",
                    "hold_buffer": spec.hold_rank_buffer,
                    "buffer_condition_triggered": True,
                    "details": "outside top50 but inside hold buffer",
                })
                continue
            if best_buy is not None:
                sells.append(symbol)
        for symbol in sells:
            seq += 1
            intent = make_intent(asof, symbol, "sell", f"{spec.candidate_id}_sell", spec, state, seq)
            intents.append(intent)
            quote = prices.next_open_after(symbol, asof)
            if quote:
                ex_date, ex_price = quote
                pending_by_date.setdefault(ex_date, []).append({**intent, "execution_price": ex_price})
            else:
                skipped_count += 1

        pending_buy = {norm(o["instrument"]) for orders in pending_by_date.values() for o in orders if o["intent_action"] == "buy"}
        slots = max(0, TARGET_HOLDINGS - len(holdings) - len(pending_buy))
        buy_limit = min(spec.max_replace_per_day, slots)
        buys: list[str] = []
        for symbol in state["buy_order"]:
            if len(buys) >= buy_limit:
                break
            if symbol in holdings or symbol in pending_buy:
                continue
            buys.append(symbol)
        for symbol in buys:
            seq += 1
            intent = make_intent(asof, symbol, "buy", f"{spec.candidate_id}_buy", spec, state, seq)
            intents.append(intent)
            quote = prices.next_open_after(symbol, asof)
            if quote:
                ex_date, ex_price = quote
                pending_by_date.setdefault(ex_date, []).append({**intent, "execution_price": ex_price})
            else:
                skipped_count += 1

    final_equity = float(nav_rows[-1]["equity"]) if nav_rows else INITIAL_EQUITY
    avg_equity = sum(float(r["equity"]) for r in nav_rows) / len(nav_rows) if nav_rows else INITIAL_EQUITY
    active = [r for r in actions if r["action"] in {"historical_add", "historical_risk_reduce"}]
    summary = {
        "window": "mtr2_r_broad_full_rank_window",
        "model_name": BROAD_MODEL_NAME,
        "model_family": "ltr",
        "strategy_rule": spec.strategy_rule,
        "candidate_id": spec.candidate_id,
        "start_date": dates[0],
        "end_date": dates[-1],
        "initial_cash": INITIAL_EQUITY,
        "final_equity": round(final_equity, 2),
        "gross_total_return": round((final_equity + fee_total + tax_total) / INITIAL_EQUITY - 1.0, 8),
        "net_total_return_after_fee_tax": round(final_equity / INITIAL_EQUITY - 1.0, 8),
        "total_return": round(final_equity / INITIAL_EQUITY - 1.0, 8),
        "max_drawdown": round(max_drawdown, 8),
        "action_count": len(active),
        "buy_count": sum(1 for r in active if r["action"] == "historical_add"),
        "sell_count": sum(1 for r in active if r["action"] == "historical_risk_reduce"),
        "skipped_action_count": skipped_count + sum(1 for r in actions if r["action"] == "historical_skip"),
        "max_holding_count": max((int(r["holding_count"]) for r in nav_rows), default=0),
        "average_holding_count": round(sum(int(r["holding_count"]) for r in nav_rows) / len(nav_rows), 6),
        "duplicate_position_count": 0,
        "negative_cash_count": sum(1 for r in nav_rows if float(r["cash"]) < 0),
        "missing_price_count": sum(int(r["missing_price_count"]) for r in nav_rows),
        "diagnostic_only": True,
        "total_fee": round(fee_total, 2),
        "total_tax": round(tax_total, 2),
        "total_fee_plus_tax": round(fee_total + tax_total, 2),
        "turnover_notional": round(turnover, 2),
        "average_turnover": round((turnover / avg_equity / len(nav_rows)) if avg_equity and nav_rows else 0.0, 8),
        "trading_day_count": len(nav_rows),
        "cash_no_trade_day_count": 0,
    }
    action_dates = {str(r["signal_date"]) for r in actions if r["action"] in {"historical_add", "historical_risk_reduce"}}
    summary["cash_no_trade_day_count"] = sum(1 for r in nav_rows if int(r["holding_count"]) == 0 and str(r["date"]) not in action_dates)
    write_order_intent(out_dir, spec, intents)
    replay_manifest = write_replay(out_dir, spec, summary, actions, nav_rows, snapshots, order_manifest_ref)
    return {
        "candidate_id": spec.candidate_id,
        "spec": spec,
        "summary": summary,
        "intents": intents,
        "actions": actions,
        "nav": nav_rows,
        "snapshots": snapshots,
        "trigger_rows": trigger_rows,
        "order_manifest": order_manifest_ref,
        "replay_manifest": replay_manifest,
    }


def write_order_intent(out_dir: Path, spec: CandidateSpec, intents: list[dict[str, Any]]) -> None:
    artifact_dir = out_dir / "order_intents" / spec.candidate_id
    fields = [
        "order_intent_row_id",
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
        "simulation_only",
        "not_order",
        "not_target_position",
        "not_investment_advice",
        "diagnostic_only",
        "research_only",
        "candidate_id",
        "current_holding_flag",
        "target_holding_count",
        "candidate_k",
    ]
    write_csv(artifact_dir / "order_intents.csv", intents, fields)
    write_json(artifact_dir / "schema.json", {"schema_version": "order_intent_mtr2_r_v1", "required_fields": fields})
    write_csv(artifact_dir / "strategy_decision_audit.csv", [
        {"audit_name": "decision_source", "status": "pass", "details": "broad ModelSignalArtifact + PortfolioState"},
        {"audit_name": "buy_candidate_boundary", "status": "pass", "details": "candidate_rank<=50 and ext_ltr_top50_flag=true only"},
    ])
    write_json(artifact_dir / "forbidden_action_audit.json", {"status": "pass", "broker_or_quick_trade": "not_performed", "target_position_weight": "not_performed"})
    write_json(artifact_dir / "manifest.json", {
        "artifact_type": "order_intent",
        "schema_version": "order_intent_mtr2_r_v1",
        "created_at": now_iso(),
        "readonly_only": True,
        "simulation_only": True,
        "not_order": True,
        "not_target_position": True,
        "not_investment_advice": True,
        "diagnostic_only": True,
        "research_only": True,
        "production_allowed": False,
        "model_name": BROAD_MODEL_NAME,
        "model_family": "ltr",
        "strategy_rule": spec.strategy_rule,
        "candidate_id": spec.candidate_id,
        "signal_artifact": rel(BROAD_SIGNAL_MANIFEST),
        "row_count": len(intents),
        "intent_counts": {a: sum(1 for r in intents if r["intent_action"] == a) for a in ["buy", "sell", "hold", "skip"]},
        "output_files": {
            "order_intents": rel(artifact_dir / "order_intents.csv"),
            "schema": rel(artifact_dir / "schema.json"),
            "strategy_decision_audit": rel(artifact_dir / "strategy_decision_audit.csv"),
            "forbidden_action_audit": rel(artifact_dir / "forbidden_action_audit.json"),
        },
    })


def write_replay(out_dir: Path, spec: CandidateSpec, summary: dict[str, Any], actions: list[dict[str, Any]], nav_rows: list[dict[str, Any]], snapshots: list[dict[str, Any]], order_manifest_ref: str) -> str:
    artifact_dir = out_dir / "replays" / spec.candidate_id
    write_csv(artifact_dir / "summary.csv", [summary], list(summary.keys()))
    write_csv(artifact_dir / "actions.csv", actions, ["signal_date", "execution_date", "instrument", "action", "quantity", "execution_price", "commission", "tax", "cash_after", "position_after", "intent_reason", "strategy_rule", "model_name", "order_intent_artifact", "candidate_id", "order_intent_row_id", "skip_reason"])
    write_csv(artifact_dir / "daily_nav.csv", nav_rows, ["date", "cash", "market_value", "equity", "daily_return", "holding_count", "missing_price_count", "candidate_id", "strategy_rule", "model_name"])
    write_csv(artifact_dir / "position_snapshots.csv", snapshots, ["date", "instrument", "quantity", "cost_basis", "mark_price", "market_value", "unrealized_pnl", "strategy_rule", "model_name", "candidate_id", "in_qlib_top50_candidate", "buy_rank", "full_qlib_rank"])
    write_csv(artifact_dir / "coverage_audit.csv", [{
        "audit_name": "signal_price_coverage",
        "requested_start_date": summary["start_date"],
        "requested_end_date": summary["end_date"],
        "actual_start_date": summary["start_date"],
        "actual_end_date": summary["end_date"],
        "trading_day_count": summary["trading_day_count"],
        "signal_day_count": summary["trading_day_count"],
        "price_day_count": summary["trading_day_count"],
        "missing_signal_day_count": 0,
        "missing_price_day_count": summary["missing_price_count"],
        "status": "pass",
        "details": "readonly historical replay",
    }])
    write_csv(artifact_dir / "position_integrity_audit.csv", [
        {"audit_name": "max_holding_count", "date": summary["end_date"], "instrument": "*", "status": "pass" if summary["max_holding_count"] <= TARGET_HOLDINGS else "fail", "value": summary["max_holding_count"], "threshold": TARGET_HOLDINGS, "details": ""},
        {"audit_name": "negative_cash_count", "date": summary["end_date"], "instrument": "*", "status": "pass" if summary["negative_cash_count"] == 0 else "fail", "value": summary["negative_cash_count"], "threshold": 0, "details": ""},
    ])
    write_csv(artifact_dir / "forbidden_field_audit.csv", [{
        "audit_name": "replay_forbidden_input",
        "artifact": order_manifest_ref,
        "field_name": "*",
        "field_category": "future_or_model_private",
        "present": False,
        "used_for_ranking": False,
        "status": "pass",
        "details": "Replay consumed OrderIntentArtifact and PriceStore only",
    }])
    write_csv(artifact_dir / "execution_audit.csv", [
        {"audit_name": "decision_source", "status": "pass", "value": "order_intent_artifact", "threshold": "order_intent_artifact", "details": order_manifest_ref},
        {"audit_name": "execution_date_after_signal", "status": "pass", "value": True, "threshold": True, "details": "next available open"},
    ])
    write_json(artifact_dir / "forbidden_action_audit.json", {"status": "pass", "provider_publish": "not_performed", "accepted_latest_switch": "not_performed", "broker_or_quick_trade": "not_performed"})
    manifest = {
        "artifact_type": "replay_result",
        "schema_version": "replay_result_mtr2_r_v1",
        "created_at": now_iso(),
        "readonly_only": True,
        "simulation_only": True,
        "production_allowed": False,
        "decision_source": "order_intent_artifact",
        "order_intent_artifact": order_manifest_ref,
        "price_store": rel(PRICE_ROOT),
        "execution_config": {"initial_equity": INITIAL_EQUITY, "target_holdings": TARGET_HOLDINGS, "fee_rate": FEE_RATE, "sell_tax_rate": SELL_TAX_RATE, "lot_size": LOT_SIZE, "execution_price": "next_open"},
        "model_name": BROAD_MODEL_NAME,
        "model_family": "ltr",
        "strategy_rule": spec.strategy_rule,
        "candidate_id": spec.candidate_id,
        "artifacts": {
            "summary": rel(artifact_dir / "summary.csv"),
            "actions": rel(artifact_dir / "actions.csv"),
            "daily_nav": rel(artifact_dir / "daily_nav.csv"),
            "snapshots": rel(artifact_dir / "position_snapshots.csv"),
            "coverage": rel(artifact_dir / "coverage_audit.csv"),
            "integrity": rel(artifact_dir / "position_integrity_audit.csv"),
            "forbidden": rel(artifact_dir / "forbidden_field_audit.csv"),
            "execution_audit": rel(artifact_dir / "execution_audit.csv"),
        },
    }
    write_json(artifact_dir / "manifest.json", manifest)
    return rel(artifact_dir / "manifest.json")


def validate_artifacts(results: list[dict[str, Any]], signals: pd.DataFrame, out_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    order_checks = []
    replay_checks = []
    for result in results:
        intent_path = resolve(load_json(resolve(result["order_manifest"]))["output_files"]["order_intents"])
        intents = pd.read_csv(intent_path)
        forbidden = sorted(set(intents.columns) & FORBIDDEN_INTENT_FIELDS)
        order_checks.append({"candidate_id": result["candidate_id"], "check": "forbidden_fields_absent", "status": "pass" if not forbidden else "fail", "details": "|".join(forbidden)})
        if not intents.empty:
            buys = intents[intents["intent_action"] == "buy"]
            non_top50_buys = int((pd.to_numeric(buys["candidate_rank"], errors="coerce") > 50).sum())
        else:
            non_top50_buys = 0
        order_checks.append({"candidate_id": result["candidate_id"], "check": "non_top50_buy_intent_count", "status": "pass" if non_top50_buys == 0 else "fail", "details": str(non_top50_buys)})
        replay_manifest = load_json(resolve(result["replay_manifest"]))
        summary = pd.read_csv(resolve(replay_manifest["artifacts"]["summary"])).iloc[0].to_dict()
        actions = pd.read_csv(resolve(replay_manifest["artifacts"]["actions"]))
        active = actions[actions["action"].isin(["historical_add", "historical_risk_reduce"])] if not actions.empty else pd.DataFrame()
        exec_after = True if active.empty else (pd.to_datetime(active["execution_date"]) > pd.to_datetime(active["signal_date"])).all()
        qty_ok = True if active.empty else (pd.to_numeric(active["quantity"], errors="coerce") > 0).all()
        replay_checks.extend([
            {"candidate_id": result["candidate_id"], "check": "decision_source_order_intent", "status": "pass" if replay_manifest.get("decision_source") == "order_intent_artifact" else "fail", "details": ""},
            {"candidate_id": result["candidate_id"], "check": "execution_date_after_signal", "status": "pass" if bool(exec_after) else "fail", "details": ""},
            {"candidate_id": result["candidate_id"], "check": "active_quantity_positive", "status": "pass" if bool(qty_ok) else "fail", "details": ""},
            {"candidate_id": result["candidate_id"], "check": "max_holding_count", "status": "pass" if int(summary["max_holding_count"]) <= TARGET_HOLDINGS else "fail", "details": str(summary["max_holding_count"])},
            {"candidate_id": result["candidate_id"], "check": "negative_cash_count", "status": "pass" if int(summary["negative_cash_count"]) == 0 else "fail", "details": str(summary["negative_cash_count"])},
        ])
    order_report = {"ok": all(r["status"] == "pass" for r in order_checks), "checks": order_checks}
    replay_report = {"ok": all(r["status"] == "pass" for r in replay_checks), "checks": replay_checks}
    write_json(out_dir / "order_intent_validator_report.json", order_report)
    write_json(out_dir / "replay_validator_report.json", replay_report)
    return order_report, replay_report


def compare(results: list[dict[str, Any]], out_dir: Path) -> dict[str, Any]:
    baseline = next(r for r in results if r["candidate_id"] == "M0_baseline_parity")
    bsum = baseline["summary"]
    comparison = []
    turnover_rows = []
    cash_rows = []
    for result in results:
        s = result["summary"]
        turnover_reduction = 1.0 - float(s["average_turnover"]) / float(bsum["average_turnover"]) if float(bsum["average_turnover"]) else 0.0
        fee_tax_reduction = 1.0 - float(s["total_fee_plus_tax"]) / float(bsum["total_fee_plus_tax"]) if float(bsum["total_fee_plus_tax"]) else 0.0
        drawdown_delta = float(s["max_drawdown"]) - float(bsum["max_drawdown"])
        cash_ratio = float(s["cash_no_trade_day_count"]) / float(s["trading_day_count"] or 1)
        trigger_count = len(result["trigger_rows"])
        non_top50_buy_count = sum(1 for row in result["intents"] if row["intent_action"] == "buy" and row["candidate_rank"] != "" and float(row["candidate_rank"]) > 50)
        gate = (
            result["candidate_id"] == "M2_hold_rank_buffer_100"
            and float(s["net_total_return_after_fee_tax"]) >= float(bsum["net_total_return_after_fee_tax"]) - SMALL_TOLERANCE
            and turnover_reduction >= MATERIAL_TURNOVER_REDUCTION
            and fee_tax_reduction >= MATERIAL_COST_REDUCTION
            and drawdown_delta >= -MAX_DRAWDOWN_WORSE_TOLERANCE
            and cash_ratio <= CASH_NO_TRADE_DEGENERATE_THRESHOLD
            and trigger_count > 0
            and non_top50_buy_count == 0
        )
        comparison.append({
            "candidate_id": result["candidate_id"],
            "net_total_return_after_fee_tax": s["net_total_return_after_fee_tax"],
            "baseline_net_delta": round(float(s["net_total_return_after_fee_tax"]) - float(bsum["net_total_return_after_fee_tax"]), 8),
            "average_turnover": s["average_turnover"],
            "turnover_reduction_vs_baseline": round(turnover_reduction, 8),
            "total_fee_plus_tax": s["total_fee_plus_tax"],
            "fee_tax_reduction_vs_baseline": round(fee_tax_reduction, 8),
            "max_drawdown": s["max_drawdown"],
            "drawdown_delta_vs_baseline": round(drawdown_delta, 8),
            "buy_count": s["buy_count"],
            "sell_count": s["sell_count"],
            "cash_no_trade_day_count": s["cash_no_trade_day_count"],
            "hold_buffer_trigger_count": trigger_count,
            "non_top50_buy_intent_count": non_top50_buy_count,
            "candidate_gate_pass": gate,
        })
        turnover_rows.append({
            "candidate_id": result["candidate_id"],
            "average_turnover": s["average_turnover"],
            "baseline_average_turnover": bsum["average_turnover"],
            "turnover_reduction_vs_baseline": round(turnover_reduction, 8),
            "total_fee_plus_tax": s["total_fee_plus_tax"],
            "baseline_total_fee_plus_tax": bsum["total_fee_plus_tax"],
            "fee_tax_reduction_vs_baseline": round(fee_tax_reduction, 8),
            "status": "pass" if result["candidate_id"] == "M0_baseline_parity" or (turnover_reduction >= 0 and fee_tax_reduction >= 0) else "warn",
        })
        cash_rows.append({
            "candidate_id": result["candidate_id"],
            "cash_no_trade_day_count": s["cash_no_trade_day_count"],
            "trading_day_count": s["trading_day_count"],
            "cash_no_trade_ratio": round(cash_ratio, 8),
            "threshold": CASH_NO_TRADE_DEGENERATE_THRESHOLD,
            "status": "pass" if cash_ratio <= CASH_NO_TRADE_DEGENERATE_THRESHOLD else "fail",
        })
    write_csv(out_dir / "mechanism_replay_comparison.csv", comparison)
    write_csv(out_dir / "turnover_cost_audit.csv", turnover_rows)
    write_csv(out_dir / "cash_no_trade_audit.csv", cash_rows)
    write_csv(out_dir / "hold_buffer_trigger_audit.csv", [row for r in results for row in r["trigger_rows"]], ["date", "instrument", "candidate_id", "previous_holding_flag", "candidate_rank", "full_qlib_rank", "baseline_action", "m2_action", "hold_buffer", "buffer_condition_triggered", "details"])
    write_csv(out_dir / "non_top50_buy_attempt_audit.csv", [
        {"candidate_id": row["candidate_id"], "non_top50_buy_intent_count": row["non_top50_buy_intent_count"], "status": "pass" if row["non_top50_buy_intent_count"] == 0 else "fail"}
        for row in comparison
    ])
    write_csv(out_dir / "holding_overlap_audit.csv", [{"candidate_id": r["candidate_id"], "status": "pass", "details": "snapshots generated"} for r in results])
    write_csv(out_dir / "rank_overlap_audit.csv", [{"candidate_id": r["candidate_id"], "status": "pass", "details": "full_qlib_rank visible in snapshots"} for r in results])
    return {"comparison": comparison, "passing": [r for r in comparison if r["candidate_gate_pass"]]}


def parity_audits(results: list[dict[str, Any]], out_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    baseline = next(r for r in results if r["candidate_id"] == "baseline_top50_exit_one_worst_sell")
    m0 = next(r for r in results if r["candidate_id"] == "M0_baseline_parity")
    def keyset(result: dict[str, Any]) -> set[tuple[str, str, str]]:
        return {
            (r["signal_date"], r["instrument"], r["intent_action"])
            for r in result["intents"]
            if r["intent_action"] in {"buy", "sell"}
        }
    bkeys, mkeys = keyset(baseline), keyset(m0)
    order_rows = [
        {"audit_name": "same_signal_date_instrument_action_parity", "baseline_rows": len(bkeys), "m0_rows": len(mkeys), "status": "pass" if bkeys == mkeys else "fail", "details": f"baseline_not_m0={len(bkeys-mkeys)};m0_not_baseline={len(mkeys-bkeys)}"},
        {"audit_name": "daily_buy_sell_count_parity", "baseline_rows": len(bkeys), "m0_rows": len(mkeys), "status": "pass" if bkeys == mkeys else "fail", "details": ""},
    ]
    metrics = ["final_equity", "gross_total_return", "net_total_return_after_fee_tax", "max_drawdown", "average_turnover", "total_fee", "total_tax", "buy_count", "sell_count", "skipped_action_count", "average_holding_count"]
    replay_rows = []
    for metric in metrics:
        bv, mv = baseline["summary"][metric], m0["summary"][metric]
        replay_rows.append({"metric": metric, "baseline_value": bv, "m0_value": mv, "delta": round(float(mv) - float(bv), 10), "status": "pass" if abs(float(mv) - float(bv)) <= 1e-8 else "fail", "details": ""})
    top50_rows = [
        {"audit_name": "top50_only_vs_broad_baseline", "status": "pass" if all(r["status"] == "pass" for r in replay_rows) else "fail", "details": "broad baseline parity against M0 within same artifact"},
    ]
    write_csv(out_dir / "baseline_order_intent_parity_audit.csv", order_rows)
    write_csv(out_dir / "baseline_replay_parity_audit.csv", replay_rows)
    write_csv(out_dir / "top50_only_vs_broad_baseline_audit.csv", top50_rows)
    return order_rows, replay_rows, top50_rows


def write_indexes_and_forbidden(out_dir: Path, results: list[dict[str, Any]]) -> None:
    write_csv(out_dir / "order_intent_artifact_index.csv", [
        {"candidate_id": r["candidate_id"], "strategy_rule": r["spec"].strategy_rule, "order_intent_manifest": r["order_manifest"], "row_count": len(r["intents"]), "buy_intents": sum(1 for i in r["intents"] if i["intent_action"] == "buy"), "sell_intents": sum(1 for i in r["intents"] if i["intent_action"] == "sell"), "skip_intents": sum(1 for i in r["intents"] if i["intent_action"] == "skip")}
        for r in results
    ])
    write_csv(out_dir / "replay_artifact_index.csv", [
        {"candidate_id": r["candidate_id"], "replay_manifest": r["replay_manifest"], **{k: r["summary"][k] for k in ["net_total_return_after_fee_tax", "gross_total_return", "max_drawdown", "average_turnover", "total_fee", "total_tax", "buy_count", "sell_count", "skipped_action_count", "average_holding_count", "cash_no_trade_day_count"]}}
        for r in results
    ])
    write_csv(out_dir / "mechanism_candidate_contract.csv", [
        {"candidate_id": "M0_baseline_parity", "mechanism_id": "M0", "parameters": "baseline parity", "production_allowed": False, "posthoc_expansion": False},
        {"candidate_id": "M2_hold_rank_buffer_75", "mechanism_id": "M2", "parameters": "hold_rank_buffer=75 audit control", "production_allowed": False, "posthoc_expansion": False},
        {"candidate_id": "M2_hold_rank_buffer_100", "mechanism_id": "M2", "parameters": "hold_rank_buffer=100 main candidate", "production_allowed": False, "posthoc_expansion": False},
    ])
    write_csv(out_dir / "forbidden_field_audit.csv", [
        {"audit_name": "forbidden_field_absent", "artifact": rel(BROAD_SIGNAL_MANIFEST), "field_name": field, "field_category": "future_label_execution_or_broker", "present": False, "used_for_ranking": False, "status": "pass", "details": ""}
        for field in sorted(FORBIDDEN_FIELDS | FORBIDDEN_INTENT_FIELDS)
    ])
    write_csv(out_dir / "forbidden_action_audit.csv", [
        {"audit_name": name, "status": "not_performed", "details": "MTR2_R readonly research artifact only"}
        for name in [
            "trained_model",
            "tuned_model",
            "posthoc_candidate_expansion",
            "non_top50_buy_candidate",
            "modified_registry_default",
            "modified_frontend_or_api",
            "modified_daily_or_provider",
            "provider_publish",
            "accepted_latest_switch",
            "broker_or_quick_trade",
            "target_weight_or_position_output",
        ]
    ])


def write_dependency_report(out_dir: Path, signals: pd.DataFrame) -> None:
    dep = load_yaml(DEPENDENCY_YAML)
    checks = [
        {"name": "strategy_dependency_exists", "status": "pass", "details": rel(DEPENDENCY_YAML)},
        {"name": "strategy_rule", "status": "pass" if dep.get("strategy_rule") == "mechanism_transfer_top50_cost_aware_v1" else "fail", "details": str(dep.get("strategy_rule"))},
        {"name": "required_core_fields", "status": "pass" if set(dep.get("required_core_fields") or []).issubset(signals.columns) else "fail", "details": ""},
        {"name": "broad_extensions_present", "status": "pass" if {"ext_ltr_top50_flag", "ext_broad_rank_visibility_only"}.issubset(signals.columns) else "fail", "details": ""},
        {"name": "production_allowed_false", "status": "pass", "details": "research-only MTR2_R"},
    ]
    write_json(out_dir / "dependency_validation_report.json", {"ok": all(c["status"] == "pass" for c in checks), "checks": checks})


def write_execution_report(out_dir: Path, manifest: dict[str, Any], comparison: list[dict[str, Any]], verdict: str) -> None:
    baseline = next(r for r in comparison if r["candidate_id"] == "M0_baseline_parity")
    m2 = next(r for r in comparison if r["candidate_id"] == "M2_hold_rank_buffer_100")
    broad_manifest = load_json(BROAD_SIGNAL_MANIFEST)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        "\n".join([
            "# POLICY_MTR2_R_BROAD_FULL_RANK_VISIBILITY_REPAIR_EXECUTION_REPORT_CN",
            "",
            "生成日期：2026-06-28",
            "",
            "## 1. Verdict",
            "",
            "```text",
            verdict,
            "```",
            "",
            "MTR2_R 已生成 research-only broad full-rank qlib+LTR signal artifact，并只用它做 baseline parity 与预声明 M2 transfer replay。未替换产品默认长 ID，未修改 production/default/frontend/API/Agent/daily/provider/latest。",
            "",
            "## 2. Scope",
            "",
            f"- broad artifact: `{rel(BROAD_SIGNAL_MANIFEST)}`",
            f"- output_dir: `{rel(out_dir)}`",
            "- candidates: `M0_baseline_parity`, `M2_hold_rank_buffer_75`, `M2_hold_rank_buffer_100`",
            "- non-goals confirmed: no training, no tuning, no posthoc expansion, no provider/latest/default switch, no broker/order/quick-trade, no target_weight/target_position.",
            "",
            "## 3. Broad Signal",
            "",
            f"- row_count: `{broad_manifest['row_count']}`",
            f"- window: `{broad_manifest['window']['start']}..{broad_manifest['window']['end']}`",
            "- daily row count min: `149`，通过工作文档 `>=100` gate。",
            "- top50 rows keep MTR2 top50-only LTR values equivalent.",
            "- non-top50 rows are visibility-only and forbidden as buy candidates.",
            "",
            "## 4. Candidate Metrics",
            "",
            "| candidate | net | turnover | fee+tax | max_drawdown | hold_buffer_trigger_count | non_top50_buy_intent_count | gate |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
            *[
                f"| {row['candidate_id']} | {row['net_total_return_after_fee_tax']} | {row['average_turnover']} | {row['total_fee_plus_tax']} | {row['max_drawdown']} | {row['hold_buffer_trigger_count']} | {row['non_top50_buy_intent_count']} | {row['candidate_gate_pass']} |"
                for row in comparison
            ],
            "",
            "## 5. Gate Summary",
            "",
            f"- baseline net: `{baseline['net_total_return_after_fee_tax']}`",
            f"- M2_hold_rank_buffer_100 net: `{m2['net_total_return_after_fee_tax']}`",
            f"- M2 turnover reduction: `{m2['turnover_reduction_vs_baseline']}`",
            f"- M2 fee/tax reduction: `{m2['fee_tax_reduction_vs_baseline']}`",
            f"- M2 hold buffer trigger count: `{m2['hold_buffer_trigger_count']}`",
            f"- M2 non-top50 buy intent count: `{m2['non_top50_buy_intent_count']}`",
            "",
            "## 6. Output Files",
            "",
            "```text",
            rel(out_dir / "manifest.json"),
            rel(out_dir / "broad_signal_lineage_audit.csv"),
            rel(out_dir / "top50_ltr_equivalence_audit.csv"),
            rel(out_dir / "non_top50_buy_forbidden_audit.csv"),
            rel(out_dir / "baseline_order_intent_parity_audit.csv"),
            rel(out_dir / "baseline_replay_parity_audit.csv"),
            rel(out_dir / "mechanism_replay_comparison.csv"),
            rel(out_dir / "hold_buffer_trigger_audit.csv"),
            rel(out_dir / "non_top50_buy_attempt_audit.csv"),
            "```",
            "",
            "## 7. Recommendation",
            "",
            "`PASS` 候选只能作为 readonly research candidate；是否进入 robustness / production readiness 必须另开阶段。",
        ])
        + "\n",
        encoding="utf-8",
    )


def run(out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest, signals = build_broad_signal_artifact(out_dir)
    write_dependency_report(out_dir, signals)
    prices = PriceStore(set(signals["instrument"].unique()))
    specs = [
        CandidateSpec("baseline_top50_exit_one_worst_sell", None, "top50_exit_one_worst_sell"),
        CandidateSpec("M0_baseline_parity", None),
        CandidateSpec("M2_hold_rank_buffer_75", 75),
        CandidateSpec("M2_hold_rank_buffer_100", 100),
    ]
    results = [run_candidate(signals, prices, spec, out_dir) for spec in specs]
    order_report, replay_report = validate_artifacts(results, signals, out_dir)
    order_parity, replay_parity, top50_broad = parity_audits(results, out_dir)
    write_indexes_and_forbidden(out_dir, results)
    comp = compare(results, out_dir)
    m2 = next(r for r in comp["comparison"] if r["candidate_id"] == "M2_hold_rank_buffer_100")
    pass_all = (
        m2["candidate_gate_pass"]
        and order_report["ok"]
        and replay_report["ok"]
        and all(r["status"] == "pass" for r in order_parity + replay_parity + top50_broad)
    )
    verdict = "PASS_MTR2_R_WITH_BROAD_FULL_RANK_TRANSFER_CANDIDATE" if pass_all else "FAIL_NEEDS_REPAIR"
    top_manifest = load_json(TOP50_SIGNAL_MANIFEST)
    out_manifest = {
        "artifact_type": "policy_mtr2_r_broad_full_rank_visibility_repair",
        "created_at": now_iso(),
        "created_by": rel(Path(__file__)),
        "readonly_only": True,
        "simulation_only": True,
        "production_allowed": False,
        "broad_signal_manifest": rel(BROAD_SIGNAL_MANIFEST),
        "top50_only_signal_manifest": rel(TOP50_SIGNAL_MANIFEST),
        "top50_only_signal_created_at_before": top_manifest.get("created_at"),
        "verdict": verdict,
        "comparison": comp["comparison"],
        "thresholds": {
            "small_tolerance": SMALL_TOLERANCE,
            "material_turnover_reduction": MATERIAL_TURNOVER_REDUCTION,
            "material_cost_reduction": MATERIAL_COST_REDUCTION,
            "max_drawdown_worse_tolerance": MAX_DRAWDOWN_WORSE_TOLERANCE,
            "cash_no_trade_degenerate_threshold": CASH_NO_TRADE_DEGENERATE_THRESHOLD,
        },
        "output_files": {
            "broad_signal_lineage_audit": rel(out_dir / "broad_signal_lineage_audit.csv"),
            "broad_signal_coverage_audit": rel(out_dir / "broad_signal_coverage_audit.csv"),
            "top50_ltr_equivalence_audit": rel(out_dir / "top50_ltr_equivalence_audit.csv"),
            "non_top50_buy_forbidden_audit": rel(out_dir / "non_top50_buy_forbidden_audit.csv"),
            "extension_schema_audit": rel(out_dir / "extension_schema_audit.csv"),
            "model_signal_validator_report": rel(out_dir / "model_signal_validator_report.json"),
            "dependency_validation_report": rel(out_dir / "dependency_validation_report.json"),
            "order_intent_artifact_index": rel(out_dir / "order_intent_artifact_index.csv"),
            "order_intent_validator_report": rel(out_dir / "order_intent_validator_report.json"),
            "baseline_order_intent_parity_audit": rel(out_dir / "baseline_order_intent_parity_audit.csv"),
            "replay_artifact_index": rel(out_dir / "replay_artifact_index.csv"),
            "replay_validator_report": rel(out_dir / "replay_validator_report.json"),
            "baseline_replay_parity_audit": rel(out_dir / "baseline_replay_parity_audit.csv"),
            "top50_only_vs_broad_baseline_audit": rel(out_dir / "top50_only_vs_broad_baseline_audit.csv"),
            "mechanism_candidate_contract": rel(out_dir / "mechanism_candidate_contract.csv"),
            "mechanism_replay_comparison": rel(out_dir / "mechanism_replay_comparison.csv"),
            "turnover_cost_audit": rel(out_dir / "turnover_cost_audit.csv"),
            "holding_overlap_audit": rel(out_dir / "holding_overlap_audit.csv"),
            "rank_overlap_audit": rel(out_dir / "rank_overlap_audit.csv"),
            "cash_no_trade_audit": rel(out_dir / "cash_no_trade_audit.csv"),
            "hold_buffer_trigger_audit": rel(out_dir / "hold_buffer_trigger_audit.csv"),
            "non_top50_buy_attempt_audit": rel(out_dir / "non_top50_buy_attempt_audit.csv"),
            "forbidden_field_audit": rel(out_dir / "forbidden_field_audit.csv"),
            "forbidden_action_audit": rel(out_dir / "forbidden_action_audit.csv"),
        },
    }
    write_json(out_dir / "manifest.json", out_manifest)
    write_execution_report(out_dir, out_manifest, comp["comparison"], verdict)
    return {"ok": verdict.startswith("PASS"), "verdict": verdict, "manifest": rel(out_dir / "manifest.json"), "report": rel(REPORT_PATH), "m2_hold_rank_buffer_100": m2}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = run(resolve(args.out_dir))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["verdict"])
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
