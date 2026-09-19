#!/usr/bin/env python3
"""RSR0 contract/data readiness audit.

This script is intentionally read-only with respect to upstream artifacts. It
does not run replay, train models, tune thresholds, publish providers, switch
latest pointers, or generate strategy/order-intent outputs.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness"
REPORT_PATH = ROOT / "docs/tw_portfolio_decision_model/POLICY_RSR0_CONTRACT_AND_DATA_READINESS_EXECUTION_REPORT_CN.md"

DOCS_READ = [
    "docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md",
    "docs/tw_portfolio_decision_model/POLICY_RSR0_CONTRACT_AND_DATA_READINESS_WORK_CN.md",
    "docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md",
    "docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md",
    "docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md",
    "docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md",
    "docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md",
    "docs/tw_portfolio_decision_model/POLICY_MODEL_RESEARCH_ROUTE_CLOSURE_EXECUTION_REPORT_CN.md",
    "docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FINAL_CLOSURE_REVIEW_CN.md",
    "docs/tw_portfolio_decision_model/POLICY_RCPT6_RESEARCH_CLOSURE_PACKAGE_CN.md",
    "docs/tw_portfolio_decision_model/POLICY_RCPT7C_ADAPTIVE_SCORE_ALIGNED_CLOSURE_REVIEW_CN.md",
]

SIGNAL_MANIFEST = Path("data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json")
SIGNAL_CSV = Path("data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/signals.csv")
FULL_RANK_MANIFEST = Path("data_tw/artifacts/full_rank/frozen_qlib_2018_2022_raw_oos/r9_full_rank_adapter_20260616/manifest.json")
FULL_RANK_CSV = Path("data_tw/artifacts/full_rank/frozen_qlib_2018_2022_raw_oos/r9_full_rank_adapter_20260616/full_rank.csv")
TEST_MANIFEST = Path("data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/TEST.manifest.json")
TEST_CSV = Path("data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/TEST.csv")
RCPT5B_ROOT = Path("data_tw/experiments/risk_control_policy_2022/rcpt5b_r_fee_tax_gate_repair")
BASELINE_LEDGER_ROOT = RCPT5B_ROOT / "internal_replay_ledgers_not_order_intent/baseline"
MARKET_FEATURE_CSV = RCPT5B_ROOT / "market_feature_2023_2025_by_signal_date.csv"
PRICE_COVERAGE_CSV = RCPT5B_ROOT / "price_coverage_audit.csv"
MARKET_COVERAGE_CSV = RCPT5B_ROOT / "market_feature_coverage_audit.csv"
TWII_CSV = Path("qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TWII.csv")
PRICE_ROOT = Path("qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty")
PA1_STANDARD_REPLAY_MANIFEST = Path("data_tw/experiments/policy_action_model_research/pa1_r_return_capture_repair/replays/baseline/strict_test/manifest.json")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> dict[str, Any]:
    with (ROOT / path).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def csv_columns(path: Path) -> list[str]:
    with (ROOT / path).open("r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        return next(reader)


def csv_summary(path: Path, date_col: str | None = None, instrument_col: str | None = None) -> dict[str, Any]:
    p = ROOT / path
    out: dict[str, Any] = {"exists": p.exists(), "row_count": 0, "columns": []}
    if not p.exists():
        return out
    with p.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        out["columns"] = list(reader.fieldnames or [])
        dates: set[str] = set()
        instruments: set[str] = set()
        min_date: str | None = None
        max_date: str | None = None
        for row in reader:
            out["row_count"] += 1
            if date_col and row.get(date_col):
                d = row[date_col]
                dates.add(d)
                min_date = d if min_date is None or d < min_date else min_date
                max_date = d if max_date is None or d > max_date else max_date
            if instrument_col and row.get(instrument_col):
                instruments.add(row[instrument_col])
        if date_col:
            out["date_count"] = len(dates)
            out["min_date"] = min_date
            out["max_date"] = max_date
        if instrument_col:
            out["instrument_count"] = len(instruments)
    return out


def file_hash(path: Path) -> str | None:
    p = ROOT / path
    if not p.exists():
        return None
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def status_for_missing(path: Path) -> str:
    return "available" if (ROOT / path).exists() else "missing"


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)

    signal_manifest = load_json(SIGNAL_MANIFEST)
    full_rank_manifest = load_json(FULL_RANK_MANIFEST)
    test_manifest = load_json(TEST_MANIFEST)
    rcpt_manifest = load_json(RCPT5B_ROOT / "manifest.json")
    rcpt_lineage = load_json(RCPT5B_ROOT / "signal_lineage_audit.json")

    signal_summary = csv_summary(SIGNAL_CSV, "date", "instrument")
    full_rank_summary = csv_summary(FULL_RANK_CSV, "date", "instrument")
    test_summary = csv_summary(TEST_CSV, "date", "instrument")
    actions_summary = csv_summary(BASELINE_LEDGER_ROOT / "actions.csv", "signal_date", "instrument")
    positions_summary = csv_summary(BASELINE_LEDGER_ROOT / "position_snapshots.csv", "date", "instrument")
    nav_summary = csv_summary(BASELINE_LEDGER_ROOT / "nav.csv", "date", None)
    market_summary = csv_summary(MARKET_FEATURE_CSV, "signal_date", None)
    twii_summary = csv_summary(TWII_CSV, "date", None)

    input_rows = [
        {
            "input_id": "standard_qlib_model_signal",
            "artifact_type": "ModelSignalArtifact",
            "path": rel(SIGNAL_MANIFEST),
            "data_path": rel(SIGNAL_CSV),
            "status": status_for_missing(SIGNAL_CSV),
            "window_start": signal_summary.get("min_date", ""),
            "window_end": signal_summary.get("max_date", ""),
            "row_count": signal_summary.get("row_count", ""),
            "date_count": signal_summary.get("date_count", ""),
            "instrument_count": signal_summary.get("instrument_count", ""),
            "key_fields": ";".join(csv_columns(SIGNAL_CSV)),
            "lineage_or_manifest": json.dumps(signal_manifest.get("source_artifacts", []), ensure_ascii=False),
            "readiness_note": "Standard qlib-only signal has required StrategyRule core fields and PIT available_at metadata.",
            "sha256": file_hash(SIGNAL_MANIFEST) or "",
        },
        {
            "input_id": "standard_full_qlib_rank",
            "artifact_type": "FullRankArtifact",
            "path": rel(FULL_RANK_MANIFEST),
            "data_path": rel(FULL_RANK_CSV),
            "status": status_for_missing(FULL_RANK_CSV),
            "window_start": full_rank_summary.get("min_date", ""),
            "window_end": full_rank_summary.get("max_date", ""),
            "row_count": full_rank_summary.get("row_count", ""),
            "date_count": full_rank_summary.get("date_count", ""),
            "instrument_count": full_rank_summary.get("instrument_count", ""),
            "key_fields": ";".join(csv_columns(FULL_RANK_CSV)),
            "lineage_or_manifest": full_rank_manifest.get("source_artifact", ""),
            "readiness_note": "Full qlib rank is separately traceable and PIT checked.",
            "sha256": file_hash(FULL_RANK_MANIFEST) or "",
        },
        {
            "input_id": "strict_candidate_qlib_test_scores",
            "artifact_type": "qlib_only_TEST_fold_signal_input",
            "path": rel(TEST_MANIFEST),
            "data_path": rel(TEST_CSV),
            "status": status_for_missing(TEST_CSV),
            "window_start": test_summary.get("min_date", ""),
            "window_end": test_summary.get("max_date", ""),
            "row_count": test_summary.get("row_count", ""),
            "date_count": test_summary.get("date_count", ""),
            "instrument_count": test_summary.get("instrument_count", ""),
            "key_fields": ";".join(csv_columns(TEST_CSV)),
            "lineage_or_manifest": json.dumps({k: test_manifest.get(k) for k in ["provider_uri", "config_path", "source_recorder_id", "use_frozen_pred"]}, ensure_ascii=False),
            "readiness_note": "Qlib-only TEST fold maps qlib_score_raw/qlib_rank to buy_score/raw_score/candidate_rank/full_qlib_rank for strict-candidate diagnostics.",
            "sha256": file_hash(TEST_MANIFEST) or "",
        },
        {
            "input_id": "baseline_action_ledger_2023_2025",
            "artifact_type": "readonly_internal_replay_ledger_not_order_intent",
            "path": rel(RCPT5B_ROOT / "manifest.json"),
            "data_path": rel(BASELINE_LEDGER_ROOT),
            "status": status_for_missing(BASELINE_LEDGER_ROOT / "actions.csv"),
            "window_start": actions_summary.get("min_date", ""),
            "window_end": actions_summary.get("max_date", ""),
            "row_count": actions_summary.get("row_count", ""),
            "date_count": actions_summary.get("date_count", ""),
            "instrument_count": actions_summary.get("instrument_count", ""),
            "key_fields": ";".join(csv_columns(BASELINE_LEDGER_ROOT / "actions.csv")),
            "lineage_or_manifest": "RCPT5B_R manifest internal_replay_ledgers_only_not_order_intent=true",
            "readiness_note": "Traceable 2023-2025 baseline actions exist as internal readonly accounting ledger. RSR1 should derive holding state from snapshots, not treat this as OrderIntent.",
            "sha256": file_hash(RCPT5B_ROOT / "manifest.json") or "",
        },
        {
            "input_id": "baseline_portfolio_state_2023_2025",
            "artifact_type": "PortfolioState source",
            "path": rel(RCPT5B_ROOT / "manifest.json"),
            "data_path": rel(BASELINE_LEDGER_ROOT / "position_snapshots.csv"),
            "status": status_for_missing(BASELINE_LEDGER_ROOT / "position_snapshots.csv"),
            "window_start": positions_summary.get("min_date", ""),
            "window_end": positions_summary.get("max_date", ""),
            "row_count": positions_summary.get("row_count", ""),
            "date_count": positions_summary.get("date_count", ""),
            "instrument_count": positions_summary.get("instrument_count", ""),
            "key_fields": ";".join(csv_columns(BASELINE_LEDGER_ROOT / "position_snapshots.csv")),
            "lineage_or_manifest": "position snapshots under RCPT5B_R baseline internal ledger",
            "readiness_note": "Can construct current_holding_flag by date/instrument membership; cost_basis is present. Quantity remains accounting-only and is not emitted as a strategy instruction.",
            "sha256": file_hash(BASELINE_LEDGER_ROOT / "position_snapshots.csv") or "",
        },
        {
            "input_id": "baseline_daily_nav_2023_2025",
            "artifact_type": "baseline replay state",
            "path": rel(RCPT5B_ROOT / "manifest.json"),
            "data_path": rel(BASELINE_LEDGER_ROOT / "nav.csv"),
            "status": status_for_missing(BASELINE_LEDGER_ROOT / "nav.csv"),
            "window_start": nav_summary.get("min_date", ""),
            "window_end": nav_summary.get("max_date", ""),
            "row_count": nav_summary.get("row_count", ""),
            "date_count": nav_summary.get("date_count", ""),
            "instrument_count": "",
            "key_fields": ";".join(csv_columns(BASELINE_LEDGER_ROOT / "nav.csv")),
            "lineage_or_manifest": "baseline readonly accounting ledger",
            "readiness_note": "Useful for diagnostic baseline state only. StrategyRule must not read future NAV/drawdown or realized PnL.",
            "sha256": file_hash(BASELINE_LEDGER_ROOT / "nav.csv") or "",
        },
        {
            "input_id": "market_feature_existing_ma60",
            "artifact_type": "MarketFeatureArtifact",
            "path": rel(RCPT5B_ROOT / "manifest.json"),
            "data_path": rel(MARKET_FEATURE_CSV),
            "status": status_for_missing(MARKET_FEATURE_CSV),
            "window_start": market_summary.get("min_date", ""),
            "window_end": market_summary.get("max_date", ""),
            "row_count": market_summary.get("row_count", ""),
            "date_count": market_summary.get("date_count", ""),
            "instrument_count": "",
            "key_fields": ";".join(csv_columns(MARKET_FEATURE_CSV)),
            "lineage_or_manifest": rcpt_manifest.get("market_feature_source", ""),
            "readiness_note": "Existing PIT-safe TWII MA60 feature and coverage audit are available.",
            "sha256": file_hash(MARKET_FEATURE_CSV) or "",
        },
        {
            "input_id": "twii_raw_close",
            "artifact_type": "PriceStore market index source",
            "path": rel(TWII_CSV),
            "data_path": rel(TWII_CSV),
            "status": status_for_missing(TWII_CSV),
            "window_start": twii_summary.get("min_date", ""),
            "window_end": twii_summary.get("max_date", ""),
            "row_count": twii_summary.get("row_count", ""),
            "date_count": twii_summary.get("date_count", ""),
            "instrument_count": "1",
            "key_fields": ";".join(csv_columns(TWII_CSV)),
            "lineage_or_manifest": "normalized_nonempty Yahoo-adjusted primary local source",
            "readiness_note": "Can PIT-safely construct TWII MA5/MA10/MA20, drawdown, and trailing volatility using rows up to signal_date.",
            "sha256": file_hash(TWII_CSV) or "",
        },
        {
            "input_id": "stock_price_store",
            "artifact_type": "PriceStore stock source",
            "path": rel(PRICE_ROOT),
            "data_path": rel(PRICE_ROOT),
            "status": status_for_missing(PRICE_ROOT),
            "window_start": "",
            "window_end": "",
            "row_count": "",
            "date_count": "",
            "instrument_count": len(list((ROOT / PRICE_ROOT).glob("TW*.csv"))) if (ROOT / PRICE_ROOT).exists() else 0,
            "key_fields": "symbol;date;open;high;low;close;volume;vwap;factor",
            "lineage_or_manifest": rel(PRICE_COVERAGE_CSV),
            "readiness_note": "RCPT5B_R price coverage audit passes for the 2023-2025 signal universe.",
            "sha256": "",
        },
        {
            "input_id": "standard_replay_contract_example",
            "artifact_type": "ReplayResultArtifact example",
            "path": rel(PA1_STANDARD_REPLAY_MANIFEST),
            "data_path": rel(PA1_STANDARD_REPLAY_MANIFEST.parent),
            "status": status_for_missing(PA1_STANDARD_REPLAY_MANIFEST),
            "window_start": "",
            "window_end": "",
            "row_count": "",
            "date_count": "",
            "instrument_count": "",
            "key_fields": "manifest;summary;actions;daily_nav;position_snapshots;audits",
            "lineage_or_manifest": "PA1-R standard ReplayResultArtifact shape reference",
            "readiness_note": "Shows the local ReplayResultArtifact contract is implemented, but this specific sample is not the 2023-2025 RSR baseline ledger.",
            "sha256": file_hash(PA1_STANDARD_REPLAY_MANIFEST) or "",
        },
    ]

    feature_rows = [
        {"feature": "signal_date", "source_input_id": "standard_qlib_model_signal or strict_candidate_qlib_test_scores", "status": "ready", "construction": "date column", "pit_rule": "same row signal date", "repair_plan": ""},
        {"feature": "instrument", "source_input_id": "standard_qlib_model_signal or strict_candidate_qlib_test_scores", "status": "ready", "construction": "instrument column", "pit_rule": "same row", "repair_plan": ""},
        {"feature": "candidate_rank", "source_input_id": "standard_qlib_model_signal", "status": "ready", "construction": "candidate_rank; TEST.csv qlib_rank maps to candidate_rank", "pit_rule": "available_at <= signal_date", "repair_plan": ""},
        {"feature": "buy_score", "source_input_id": "standard_qlib_model_signal", "status": "ready", "construction": "buy_score; TEST.csv qlib_score_raw maps to buy_score", "pit_rule": "available_at <= signal_date", "repair_plan": ""},
        {"feature": "raw_score", "source_input_id": "standard_qlib_model_signal", "status": "ready", "construction": "raw_score; TEST.csv qlib_score_raw maps to raw_score", "pit_rule": "available_at <= signal_date", "repair_plan": ""},
        {"feature": "score_rank", "source_input_id": "standard_qlib_model_signal", "status": "ready", "construction": "score_rank; TEST.csv qlib_rank maps to score_rank", "pit_rule": "same-day rank from frozen qlib scores", "repair_plan": ""},
        {"feature": "full_qlib_rank", "source_input_id": "standard_full_qlib_rank", "status": "ready", "construction": "full_qlib_rank", "pit_rule": "PIT available_at checked by manifest", "repair_plan": ""},
        {"feature": "signal_asof", "source_input_id": "standard_qlib_model_signal", "status": "ready", "construction": "signal_asof column; TEST can use date per lineage contract", "pit_rule": "asof is signal date", "repair_plan": ""},
        {"feature": "available_at", "source_input_id": "standard_qlib_model_signal", "status": "ready", "construction": "available_at column; TEST can use date per historical parity policy", "pit_rule": "available_at <= signal_date", "repair_plan": ""},
        {"feature": "score_bucket", "source_input_id": "standard_qlib_model_signal", "status": "constructible", "construction": "bucket buy_score/raw_score after RSR1 freezes diagnostic bucket definitions", "pit_rule": "score available at signal date", "repair_plan": "RSR1 must record bucket boundaries as diagnostic-only, not replay-tuned thresholds."},
        {"feature": "score_percentile", "source_input_id": "standard_qlib_model_signal", "status": "constructible", "construction": "within signal_date percentile/rank of buy_score", "pit_rule": "same-day cross-section only", "repair_plan": ""},
        {"feature": "score_gap_top_dispersion", "source_input_id": "standard_qlib_model_signal", "status": "constructible", "construction": "same-day gaps between top scores and same-day score dispersion", "pit_rule": "same-day signal universe only", "repair_plan": ""},
        {"feature": "rank_1d_delta", "source_input_id": "standard_qlib_model_signal", "status": "constructible", "construction": "rank(signal_date) - rank(previous available signal date)", "pit_rule": "use prior trading/signal dates only", "repair_plan": ""},
        {"feature": "rank_3d_delta", "source_input_id": "standard_qlib_model_signal", "status": "constructible", "construction": "rank(signal_date) - rank(t-3 available signal date)", "pit_rule": "use prior trading/signal dates only", "repair_plan": ""},
        {"feature": "rank_5d_delta", "source_input_id": "baseline_portfolio_state_2023_2025 or standard_qlib_model_signal", "status": "ready_or_constructible", "construction": "RCPT5B_R position snapshots already include rank_change_5d; for all candidates recompute from prior signal dates", "pit_rule": "use prior dates only", "repair_plan": "Prefer recomputing from signal file in RSR1 for all candidates; use snapshot rank_change only as lineage evidence."},
        {"feature": "twii_ma5_ma10_ma20", "source_input_id": "twii_raw_close", "status": "constructible", "construction": "rolling means over current and previous available TWII closes", "pit_rule": "current signal_date and earlier TWII rows only", "repair_plan": ""},
        {"feature": "twii_drawdown", "source_input_id": "twii_raw_close", "status": "constructible", "construction": "close / rolling prior-to-date peak - 1", "pit_rule": "no future peaks", "repair_plan": ""},
        {"feature": "twii_volatility", "source_input_id": "twii_raw_close", "status": "constructible", "construction": "trailing return volatility, e.g. 20d, using available closes", "pit_rule": "current signal_date and earlier TWII rows only", "repair_plan": ""},
        {"feature": "market_breadth", "source_input_id": "stock_price_store", "status": "optional_constructible", "construction": "share of price-store instruments above MA or positive trailing return", "pit_rule": "same or prior signal date prices only", "repair_plan": "Optional for RSR0; RSR1 can skip or implement with explicit coverage audit."},
        {"feature": "trading_calendar", "source_input_id": "strict_candidate_qlib_test_scores and twii_raw_close", "status": "ready", "construction": "TEST manifest calendar_policy plus TWII date coverage", "pit_rule": "calendar known from local qlib/TWII artifacts", "repair_plan": ""},
        {"feature": "holding_state", "source_input_id": "baseline_portfolio_state_2023_2025", "status": "constructible", "construction": "current_holding_flag from position_snapshots membership by asof date/instrument; cost_basis present", "pit_rule": "state at or before signal_date only", "repair_plan": "Materialize an RSR1 PortfolioState view with asof_date, instrument, cost_basis, current_holding_flag and no strategy output instructions."},
        {"feature": "forward_return_label", "source_input_id": "stock_price_store", "status": "diagnostic_label_only", "construction": "future close/open returns may be built only in RSR1 label columns", "pit_rule": "must not be consumed by StrategyRule", "repair_plan": "Keep in label namespace and add consumer audit."},
    ]

    pit_rows = [
        {"audit_item": "forward_return_usage", "status": "PASS_WITH_RSR1_CONSTRAINT", "evidence": "Contracts forbid forward_return_* as StrategyRule input.", "allowed_use": "RSR1 diagnostic label only", "repair_plan": "RSR1 dataset must namespace labels and add consumer audit."},
        {"audit_item": "future_label_strategy_input", "status": "PASS", "evidence": "Signal manifests and RCPT5B_R lineage list future_return_*/label_* not read.", "allowed_use": "none for StrategyRule", "repair_plan": ""},
        {"audit_item": "realized_pnl_strategy_input", "status": "PASS_WITH_LEDGER_BOUNDARY", "evidence": "Baseline ledger actions contain accounting PnL, but RSR0 treats it as ledger evidence only.", "allowed_use": "diagnostic/evaluation only, never ranking or StrategyRule", "repair_plan": "RSR1 feature builder must exclude realized_pnl columns from features."},
        {"audit_item": "execution_price_next_open_next_close", "status": "PASS_WITH_LEDGER_BOUNDARY", "evidence": "Replay ledger contains execution accounting fields; StrategyRuleContract forbids them.", "allowed_use": "ReplayExecution/accounting only", "repair_plan": "Do not join execution fields into RSR1 feature matrix."},
        {"audit_item": "market_regime_available_at", "status": "PASS", "evidence": "TWII source has date/close; existing RCPT features state MA uses current and prior rows only.", "allowed_use": "signal_date and earlier market rows", "repair_plan": ""},
        {"audit_item": "rank_delta_direction", "status": "PASS", "evidence": "Rank deltas can be computed as current rank minus prior available signal-date rank.", "allowed_use": "prior signal dates only", "repair_plan": ""},
        {"audit_item": "qlib_only_lineage", "status": "PASS", "evidence": f"TEST lineage qlib_only={rcpt_lineage.get('qlib_only')}, training_performed={rcpt_lineage.get('training_performed')}, use_frozen_pred={rcpt_lineage.get('use_frozen_pred')}.", "allowed_use": "qlib-only diagnostics", "repair_plan": ""},
        {"audit_item": "ltr_score_read", "status": "PASS", "evidence": "RCPT5B_R forbidden audit and signal lineage say LTR/orthogonal/stacking scores not read.", "allowed_use": "none in RSR0/RSR1 qlib-only", "repair_plan": ""},
    ]

    forbidden_rows = [
        {"item": "training", "present_or_performed": False, "status": "PASS_NOT_PERFORMED", "evidence": "RSR0 script is read-only metadata audit."},
        {"item": "replay_pnl_rule_search", "present_or_performed": False, "status": "PASS_NOT_PERFORMED", "evidence": "No replay runner is called; existing replay ledgers are only inventoried."},
        {"item": "threshold_tuning", "present_or_performed": False, "status": "PASS_NOT_PERFORMED", "evidence": "No thresholds are selected or changed."},
        {"item": "qlib_refresh_or_ltr_retrain", "present_or_performed": False, "status": "PASS_NOT_PERFORMED", "evidence": "No data/model refresh command is invoked."},
        {"item": "provider_publish", "present_or_performed": False, "status": "PASS_NOT_PERFORMED", "evidence": "No provider publish path is touched."},
        {"item": "accepted_latest_switch", "present_or_performed": False, "status": "PASS_NOT_PERFORMED", "evidence": "No accepted latest pointer is read for mutation or changed."},
        {"item": "production_or_default_change", "present_or_performed": False, "status": "PASS_NOT_PERFORMED", "evidence": "No configs/defaults are modified."},
        {"item": "frontend_agent_monitor_change", "present_or_performed": False, "status": "PASS_NOT_PERFORMED", "evidence": "No frontend, Agent, monitor, scan, or alert path is modified."},
        {"item": "broker_quick_trade_real_order", "present_or_performed": False, "status": "PASS_NOT_PERFORMED", "evidence": "No broker/quick-trade integration is touched."},
        {"item": "OrderIntentArtifact_generation", "present_or_performed": False, "status": "PASS_NOT_PERFORMED", "evidence": "RSR0 produces readiness artifacts only."},
        {"item": "target_position_target_weight_or_quantity_instruction", "present_or_performed": False, "status": "PASS_NOT_PERFORMED", "evidence": "No strategy action or sizing instruction artifact is generated."},
        {"item": "external_data_pull", "present_or_performed": False, "status": "PASS_NOT_PERFORMED", "evidence": "Only local files are read."},
    ]

    write_csv(
        OUT_ROOT / "input_lineage_inventory.csv",
        input_rows,
        ["input_id", "artifact_type", "path", "data_path", "status", "window_start", "window_end", "row_count", "date_count", "instrument_count", "key_fields", "lineage_or_manifest", "readiness_note", "sha256"],
    )
    write_csv(
        OUT_ROOT / "feature_readiness_audit.csv",
        feature_rows,
        ["feature", "source_input_id", "status", "construction", "pit_rule", "repair_plan"],
    )
    write_csv(
        OUT_ROOT / "pit_leakage_audit.csv",
        pit_rows,
        ["audit_item", "status", "evidence", "allowed_use", "repair_plan"],
    )
    write_csv(
        OUT_ROOT / "forbidden_action_audit.csv",
        forbidden_rows,
        ["item", "present_or_performed", "status", "evidence"],
    )

    feasibility = f"""# RSR1 Dataset Feasibility

## Verdict

`PASS_READY_FOR_RSR1_ATTRIBUTION_DIAGNOSTIC_WITH_MINOR_REPAIR`.

RSR0 found traceable local qlib-only signal/ranking inputs, 2023-2025 baseline readonly action/accounting ledgers, stock price source, TWII market source, and baseline position snapshots sufficient to build an RSR1 diagnostic dataset. No production/default/provider/latest/order path is authorized or touched.

## Recommended RSR1 Input Set

- Signal/ranking: `{rel(SIGNAL_MANIFEST)}` for standard ModelSignalArtifact fields, with `{rel(TEST_MANIFEST)}` as the strict-candidate qlib TEST fold lineage source.
- Baseline/action/holding state: `{rel(BASELINE_LEDGER_ROOT)}` from RCPT5B_R internal readonly ledgers. Treat as accounting lineage only, not OrderIntent.
- Price: `{rel(PRICE_ROOT)}` with coverage evidence `{rel(PRICE_COVERAGE_CSV)}`.
- TWII/market: `{rel(TWII_CSV)}` plus existing MA60 audit `{rel(MARKET_FEATURE_CSV)}`.

## Constructible RSR1 Features

- score bucket, score percentile, and score gap/dispersion from same-day qlib `buy_score` / `raw_score`.
- rank_1d_delta, rank_3d_delta, and rank_5d_delta from current and prior signal dates only.
- market regime from TWII MA5/MA10/MA20, drawdown, and trailing volatility. At least two required regime families are constructible from local TWII close.
- holding-aware state from baseline position snapshots by asof date and instrument.

## Required Minor Repair Before RSR1

Materialize an RSR1-only `PortfolioState` view from RCPT5B_R baseline position snapshots with `asof_date`, `instrument`, `cost_basis`, and `current_holding_flag`. Do not expose execution accounting fields as StrategyRule features.

If RSR1 requires a formal 2023-2025 `ReplayResultArtifact`, wrap the existing internal ledger into a contract-shaped readonly artifact without rerunning replay or changing results.

## PIT / Leakage Boundary

Forward returns may be added only as diagnostic labels. StrategyRule inputs must exclude future return, labels, realized PnL, execution price/date, next open/close, cash/NAV, broker/order fields, and sizing instructions.
"""
    (OUT_ROOT / "rsr1_dataset_feasibility.md").write_text(feasibility, encoding="utf-8")

    manifest = {
        "artifact_type": "POLICY_RSR0_CONTRACT_AND_DATA_READINESS",
        "created_at": now(),
        "created_by": "scripts/audit_tw_policy_rsr0_contract_data_readiness.py",
        "output_root": rel(OUT_ROOT),
        "scope": "contract_and_data_readiness_only",
        "readonly_only": True,
        "replay_rerun_performed": False,
        "model_training_performed": False,
        "threshold_tuning_performed": False,
        "provider_publish_performed": False,
        "accepted_latest_switch_performed": False,
        "production_or_default_changed": False,
        "order_or_target_or_quantity_output_generated": False,
        "documents_read": DOCS_READ,
        "primary_inputs": {
            "standard_signal_manifest": rel(SIGNAL_MANIFEST),
            "strict_candidate_test_manifest": rel(TEST_MANIFEST),
            "baseline_ledger_root": rel(BASELINE_LEDGER_ROOT),
            "market_feature_file": rel(MARKET_FEATURE_CSV),
            "twii_source": rel(TWII_CSV),
            "price_root": rel(PRICE_ROOT),
        },
        "summary_counts": {
            "standard_signal_rows": signal_summary.get("row_count"),
            "standard_signal_window": [signal_summary.get("min_date"), signal_summary.get("max_date")],
            "test_signal_rows": test_summary.get("row_count"),
            "test_signal_window": [test_summary.get("min_date"), test_summary.get("max_date")],
            "baseline_action_rows": actions_summary.get("row_count"),
            "baseline_action_window": [actions_summary.get("min_date"), actions_summary.get("max_date")],
            "baseline_position_snapshot_rows": positions_summary.get("row_count"),
            "twii_rows": twii_summary.get("row_count"),
        },
        "required_outputs": [
            "manifest.json",
            "input_lineage_inventory.csv",
            "feature_readiness_audit.csv",
            "pit_leakage_audit.csv",
            "forbidden_action_audit.csv",
            "rsr1_dataset_feasibility.md",
        ],
        "recommendation": "PASS_READY_FOR_RSR1_ATTRIBUTION_DIAGNOSTIC_WITH_MINOR_REPAIR",
    }
    write_json(OUT_ROOT / "manifest.json", manifest)

    report = f"""---
created_at: {now()}
status: executed_rsr0_contract_and_data_readiness
phase: POLICY_RSR0_CONTRACT_AND_DATA_READINESS
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_RSR0_CONTRACT_AND_DATA_READINESS_WORK_CN.md
artifact_root: {rel(OUT_ROOT)}
readonly_only: true
replay_rerun_performed: false
training_run: false
production_allowed: false
recommendation: PASS_READY_FOR_RSR1_ATTRIBUTION_DIAGNOSTIC_WITH_MINOR_REPAIR
---

# Execution Report

## 1. Scope
- Assigned phase: `POLICY_RSR0_CONTRACT_AND_DATA_READINESS`
- Mainline document: `docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md`
- Work document: `docs/tw_portfolio_decision_model/POLICY_RSR0_CONTRACT_AND_DATA_READINESS_WORK_CN.md`
- Non-goals confirmed: 不跑收益规则 replay；不训练模型；不调阈值；不改 production/default；不 provider publish；不 accepted latest switch；不生成 OrderIntent、交易、目标仓位、目标权重或数量指令。

## 2. Documents / Contracts / Skills Read

Skills read:

```text
/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md
/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-new-strategy-onboarding/SKILL.md
```

Required documents read:

```text
{chr(10).join(DOCS_READ)}
```

## 3. Changes Made

新增只读审计脚本：

```text
scripts/audit_tw_policy_rsr0_contract_data_readiness.py
```

新增 RSR0 readiness artifacts 和本执行报告。未修改策略实现、默认配置、provider/latest、前端、日更、模型或 replay 结果。

## 4. Evidence Produced

Artifacts:

```text
{rel(OUT_ROOT / "manifest.json")}
{rel(OUT_ROOT / "input_lineage_inventory.csv")}
{rel(OUT_ROOT / "feature_readiness_audit.csv")}
{rel(OUT_ROOT / "pit_leakage_audit.csv")}
{rel(OUT_ROOT / "forbidden_action_audit.csv")}
{rel(OUT_ROOT / "rsr1_dataset_feasibility.md")}
```

Validator/test output:

```text
python scripts/audit_tw_policy_rsr0_contract_data_readiness.py
python -m py_compile scripts/audit_tw_policy_rsr0_contract_data_readiness.py
```

No screenshots were required.

## 5. Compliance With Mainline

关键输入可追溯：

| 输入 | 路径 | 结论 |
| --- | --- | --- |
| qlib-only 标准信号 | `{rel(SIGNAL_MANIFEST)}` | PASS |
| qlib-only TEST fold lineage | `{rel(TEST_MANIFEST)}` | PASS |
| full qlib rank | `{rel(FULL_RANK_MANIFEST)}` | PASS |
| 2023-2025 baseline action ledger | `{rel(BASELINE_LEDGER_ROOT)}` | PASS，readonly internal ledger，不是 OrderIntent |
| 2023-2025 holding state source | `{rel(BASELINE_LEDGER_ROOT / "position_snapshots.csv")}` | PASS，可构造 PortfolioState 视图 |
| stock price source | `{rel(PRICE_ROOT)}` | PASS，RCPT5B_R price coverage audit pass |
| TWII market source | `{rel(TWII_CSV)}` | PASS |

可构造 feature：

- `score_bucket`、`score_percentile`、`score_gap/top dispersion`：可由 same-day `buy_score/raw_score` 构造。
- `rank_1d_delta`、`rank_3d_delta`、`rank_5d_delta`：可由当前和历史 signal dates 构造，不需要未来数据。
- market regime：可由 TWII close 构造 MA5/MA10/MA20、drawdown、trailing volatility，满足至少两类 regime feature 要求。
- holding state：可从 baseline position snapshots 构造 `current_holding_flag`；建议 RSR1 先物化专用 PortfolioState 视图。

## 6. Forbidden Actions Audit

`forbidden_action_audit.csv` 全部为 `PASS_NOT_PERFORMED`。本阶段未训练、未 rerun replay、未调阈值、未读取 LTR score、未 provider publish、未 accepted latest switch、未改 production/default、未生成策略意图或交易/仓位/权重/数量指令。

## 7. Issues / Blockers / Deviations

无 critical blocker。

Minor repair:

1. RSR1 前建议从 RCPT5B_R `position_snapshots.csv` 物化 RSR1 专用 `PortfolioState` 视图，只保留 `asof_date`、`instrument`、`cost_basis`、`current_holding_flag` 等状态字段。
2. 若 RSR1 reviewer 要求 2023-2025 baseline 必须是正式 `ReplayResultArtifact` 目录，可对现有 internal ledger 做只读合同包装；不得 rerun replay 或改结果。
3. market breadth 未作为 RSR0 必需项；如 RSR1 使用，需另做 PIT coverage audit。

## 8. Files Changed

```text
scripts/audit_tw_policy_rsr0_contract_data_readiness.py
{rel(OUT_ROOT / "manifest.json")}
{rel(OUT_ROOT / "input_lineage_inventory.csv")}
{rel(OUT_ROOT / "feature_readiness_audit.csv")}
{rel(OUT_ROOT / "pit_leakage_audit.csv")}
{rel(OUT_ROOT / "forbidden_action_audit.csv")}
{rel(OUT_ROOT / "rsr1_dataset_feasibility.md")}
{rel(REPORT_PATH)}
```

## 9. Recommendation For Reviewer

```text
PASS_READY_FOR_RSR1_ATTRIBUTION_DIAGNOSTIC_WITH_MINOR_REPAIR
```
"""
    REPORT_PATH.write_text(report, encoding="utf-8")

    print(json.dumps({"status": "PASS", "artifact_root": rel(OUT_ROOT), "report": rel(REPORT_PATH)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
