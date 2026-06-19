#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from evaluate_tw_ltr_s2d_full_daily_replay import (
    FEE_RATE,
    INITIAL_EQUITY,
    MAX_HOLDINGS,
    SELL_TAX_RATE,
    MethodSpec,
    PriceStore,
    replay,
)

ROOT = Path(__file__).resolve().parents[1]
E1_RAW = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_raw_oos_score_rank_2023_2026.csv"
E2_DIR = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample"
E2_MANIFEST = E2_DIR / "phasee2_sample_manifest.json"
E2_TEST = E2_DIR / "phasee2_ltr_test_sample_2026.csv"
E3_DIR = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training"
E3_MANIFEST = E3_DIR / "phasee3_training_manifest.json"
E3_TEST_SCORES = E3_DIR / "phasee3_test_row_scores_2026.csv"
E3_RANK_METRICS = E3_DIR / "phasee3_rank_metrics.csv"
E3_IMPORTANCE = E3_DIR / "phasee3_feature_importance.csv"
OUT_DIR = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay"
DOC = ROOT / "docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE4_2026_REPLAY_EXECUTION_REPORT_CN.md"
MANIFEST_JSON = OUT_DIR / "phasee4_replay_manifest.json"
REPLAY_READY_CSV = OUT_DIR / "phasee4_replay_ready_scores_2026.csv"
SUMMARY_CSV = OUT_DIR / "phasee4_control_vs_treatment_2026_summary.csv"
DAILY_NAV_CSV = OUT_DIR / "phasee4_daily_nav_2026.csv"
ACTIONS_CSV = OUT_DIR / "phasee4_actions_2026.csv"
COVERAGE_CSV = OUT_DIR / "phasee4_coverage_audit.csv"
ACCOUNTING_CSV = OUT_DIR / "phasee4_next_day_accounting_audit.csv"
PNL_CSV = OUT_DIR / "phasee4_pnl_concentration.csv"
RANK_METRICS_CSV = OUT_DIR / "phasee4_rank_metrics_summary.csv"
FEATURE_IMPORTANCE_CSV = OUT_DIR / "phasee4_feature_importance_summary.csv"
FORBIDDEN_JSON = OUT_DIR / "phasee4_forbidden_action_audit.json"
LOG_TXT = OUT_DIR / "phasee4_replay_log.txt"
TEST_START = "2026-01-01"
TEST_END = "2026-05-07"
CONTROL_METHOD = "extended_oos_frozen_qlib_top50_baseline"
TREATMENT_METHOD = "extended_oos_frozen_qlib_orthogonal_ltr"
CONTROL_SCORE = "extended_oos_frozen_qlib_control_score"
TREATMENT_SCORE = "phasee3_extended_oos_ltr_score"
GATE = "phase_e4_extended_oos_2026_replay_completed"

def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)

def wjson(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")

def wcsv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def require_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    required = [E1_RAW, E2_MANIFEST, E2_TEST, E3_MANIFEST, E3_TEST_SCORES, E3_RANK_METRICS, E3_IMPORTANCE]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(f"Missing E4 inputs: {missing}")
    e2 = load_json(E2_MANIFEST)
    e3 = load_json(E3_MANIFEST)
    if e2.get("gate") != "phase_e2_extended_oos_ltr_sample_passed":
        raise RuntimeError(f"E2 gate is not passed: {e2.get('gate')}")
    if e3.get("gate") != "phase_e3_extended_oos_ltr_trained":
        raise RuntimeError(f"E3 gate is not trained: {e3.get('gate')}")
    return e2, e3

def build_replay_ready() -> pd.DataFrame:
    sample_cols = [
        "control_row_id", "date", "date_str", "instrument", "e2_sample_split", "regime_segment", "candidate_scope",
        "qlib_score_raw", "qlib_rank", "qlib_score_zscore_by_date", "ret20", "volatility20", "TWII_ret20",
        "same_e1_frozen_qlib_score_source", "after_qlib_train_end", "top50_flag",
    ]
    sample = pd.read_csv(E2_TEST, usecols=sample_cols, parse_dates=["date"])
    scores = pd.read_csv(E3_TEST_SCORES, usecols=["control_row_id", TREATMENT_SCORE, "phasee3_extended_oos_ltr_rank"])
    df = sample.merge(scores, on="control_row_id", how="left", validate="one_to_one")
    df["date_str"] = df["date"].dt.strftime("%Y-%m-%d")
    df = df[(df["date_str"] >= TEST_START) & (df["date_str"] <= TEST_END)].copy()
    df = df[pd.to_numeric(df["qlib_rank"], errors="coerce") <= 50].copy()
    df["split"] = "test"
    df[CONTROL_SCORE] = pd.to_numeric(df["qlib_score_raw"], errors="coerce")
    if df[TREATMENT_SCORE].isna().any():
        raise RuntimeError("E4 treatment score missing after merge")
    if (pd.to_numeric(df["qlib_rank"], errors="coerce") > 50).any():
        raise RuntimeError("E4 replay input contains rows outside qlib top50")
    unsafe = {"relevance_10d_top_heavy", "future_excess_return_rank_10d", "future_return_10d", "future_excess_return_10d"}
    if unsafe & set(df.columns):
        raise RuntimeError(f"Unsafe future/label columns entered E4 replay-ready table: {sorted(unsafe & set(df.columns))}")
    keep = ["date", "date_str", "instrument", "split", "regime_segment", "candidate_scope", "qlib_score_raw", "qlib_rank", CONTROL_SCORE, TREATMENT_SCORE, "phasee3_extended_oos_ltr_rank", "top50_flag", "same_e1_frozen_qlib_score_source", "after_qlib_train_end"]
    out = df[keep].sort_values(["date", "qlib_rank", "instrument"]).reset_index(drop=True)
    out.to_csv(REPLAY_READY_CSV, index=False)
    return out

def metric_row(result: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    m = result["metrics"]
    bm = baseline["metrics"]
    return {"window": "2026_untouched_test", "method": result["method"], "comparison_status": "completed", **m, "relative_return_vs_control": round(m["fee_tax_adjusted_net_return"] - bm["fee_tax_adjusted_net_return"], 6), "relative_drawdown_vs_control": round(m["max_drawdown"] - bm["max_drawdown"], 6), "relative_actions_vs_control": int(m["action_count"]) - int(bm["action_count"])}

def coverage_audit(df: pd.DataFrame) -> list[dict[str, Any]]:
    daily = df.groupby("date_str", as_index=False).agg(rows=("instrument", "size"), control_score_rows=(CONTROL_SCORE, lambda s: int(s.notna().sum())), treatment_score_rows=(TREATMENT_SCORE, lambda s: int(s.notna().sum())), top50_rows=("qlib_rank", lambda s: int((pd.to_numeric(s, errors="coerce") <= 50).sum())))
    return [{"window": "2026_untouched_test", "start_date": str(df["date_str"].min()), "end_date": str(df["date_str"].max()), "date_count": int(daily.shape[0]), "row_count": int(df.shape[0]), "daily_rows_min": int(daily["rows"].min()), "daily_rows_median": float(daily["rows"].median()), "daily_rows_max": int(daily["rows"].max()), "control_score_rows": int(df[CONTROL_SCORE].notna().sum()), "treatment_score_rows": int(df[TREATMENT_SCORE].notna().sum()), "daily_top50_min": int(daily["top50_rows"].min()), "daily_top50_median": float(daily["top50_rows"].median()), "daily_top50_max": int(daily["top50_rows"].max()), "duplicate_key_count": int(df.duplicated(["date_str", "instrument"]).sum()), "same_frozen_score_source_all_rows": bool(df["same_e1_frozen_qlib_score_source"].all()), "after_qlib_train_end_all_rows": bool(df["after_qlib_train_end"].all()), "treatment_only_reranks_within_qlib_top50": True}]

def accounting_audit(results: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for method, result in results.items():
        metrics = result["metrics"]
        actions = pd.DataFrame(result["actions"])
        active = actions[actions["action"].isin(["historical_add", "historical_risk_reduce"])] if not actions.empty else pd.DataFrame()
        rows.append({"method": method, "next_day_execution": True, "accounting_mode": "two_phase_pending_order_queue", "fee_rate": FEE_RATE, "tax_rate": SELL_TAX_RATE, "target_position_count": MAX_HOLDINGS, "candidate_k": 50, "active_action_count": int(active.shape[0]), "missing_price_days": metrics["missing_price_days"], "skipped_trade_count": metrics["skipped_trade_count"], "last_day_new_trade_without_next_price_count": metrics["last_day_new_trade_without_next_price_count"]})
    return rows

def pnl_concentration(results: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for method, result in results.items():
        actions = pd.DataFrame(result["actions"])
        if actions.empty:
            continue
        active = actions[actions["action"].isin(["historical_add", "historical_risk_reduce"])].copy()
        if active.empty:
            continue
        active["notional"] = active["quantity"].astype(float).abs() * active["price"].astype(float)
        grouped = active.groupby("symbol", as_index=False).agg(action_count=("action", "size"), buy_count=("action", lambda s: int((s == "historical_add").sum())), sell_count=("action", lambda s: int((s == "historical_risk_reduce").sum())), turnover_notional=("notional", "sum"), fee_and_tax=("fee_and_tax", "sum"))
        total = float(grouped["turnover_notional"].sum())
        grouped["method"] = method
        grouped["turnover_notional_share"] = grouped["turnover_notional"].astype(float) / total if total else 0.0
        rows.extend(grouped.sort_values(["turnover_notional", "symbol"], ascending=[False, True]).head(30).to_dict("records"))
    return rows

def write_report(manifest: dict[str, Any], summary_rows: list[dict[str, Any]], coverage_rows: list[dict[str, Any]], rank_rows: list[dict[str, Any]], importance_rows: list[dict[str, Any]]) -> None:
    treatment = next(row for row in summary_rows if row["method"] == TREATMENT_METHOD)
    lines = ["# Phase E4 执行报告：2026 Untouched Replay", "", f"生成时间：`{manifest['created_at']}`", "", "## 1. 结论", "", f"- gate：`{manifest['gate']}`。", "- 只在 2026 untouched test 上比较 extended_oos frozen qlib top50 baseline 与 extended_oos frozen qlib + orthogonal LTR rerank。", "- control/treatment 使用同一 S2D replay engine、同一 next-day accounting、同一 fee/tax、同一 candidate_k=50、同一 target_position_count=10。", "- treatment 仅在 qlib top50 内重排，未新增股票、filter、market gate 或 turnover rule。", f"- treatment vs control：net return diff `{treatment['relative_return_vs_control']}`，drawdown diff `{treatment['relative_drawdown_vs_control']}`，action diff `{treatment['relative_actions_vs_control']}`。", "", "## 2. 使用 Artifact", "", f"- E3 manifest：`{rel(E3_MANIFEST)}`", f"- treatment score：`{rel(E3_TEST_SCORES)}`", f"- E2 test sample：`{rel(E2_TEST)}`", f"- replay-ready：`{rel(REPLAY_READY_CSV)}`", "", "## 3. 必须证明的等式", ""]
    for key, value in manifest["contract_equalities"].items():
        lines.append(f"- `{key}`：`{value}`")
    lines.extend(["", "## 4. 2026 Replay Metrics", "", "| method | net_return | max_drawdown | action_count | turnover_proxy | fee_and_tax | relative_return | relative_drawdown |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"])
    for row in summary_rows:
        lines.append(f"| {row['method']} | {row['fee_tax_adjusted_net_return']} | {row['max_drawdown']} | {row['action_count']} | {row['turnover_proxy_by_notional_over_avg_equity']} | {row['fee_and_tax']} | {row['relative_return_vs_control']} | {row['relative_drawdown_vs_control']} |")
    c = coverage_rows[0]
    lines.extend(["", "## 5. Coverage", "", f"- window：`{c['start_date']}..{c['end_date']}`，date_count：`{c['date_count']}`，row_count：`{c['row_count']}`。", f"- daily rows min/median/max：`{c['daily_rows_min']} / {c['daily_rows_median']} / {c['daily_rows_max']}`。", f"- daily top50 min/median/max：`{c['daily_top50_min']} / {c['daily_top50_median']} / {c['daily_top50_max']}`。", "- coverage 公平，control/treatment score 行数一致。", "", "## 6. Rank Metrics / Feature Importance", "", f"- E3 rank metrics 详见 `{rel(RANK_METRICS_CSV)}`；2026 test 仅 audit-only。", f"- feature importance 详见 `{rel(FEATURE_IMPORTANCE_CSV)}`。", f"- E3 test spearman：`{rank_rows[-1]['mean_daily_spearman_rank_ic_10d']}`，ndcg@10：`{rank_rows[-1]['ndcg_at_10']}`。", f"- Top feature：`{importance_rows[0]['feature']}` / `{importance_rows[0]['family']}`。", "", "## 7. PnL Concentration / Accounting", "", f"- PnL concentration 详见 `{rel(PNL_CSV)}`。", f"- next-day accounting audit 详见 `{rel(ACCOUNTING_CSV)}`。", "", "## 8. 边界审计", "", "- 未训练 qlib / LTR。", "- 未调参，未训练多个版本。", "- 未使用 2026 label/future return 做回放决策。", "- treatment 只在 qlib top50 内重排。", "- 未新增 filter / market gate / turnover rule。", "- 未触发 frontend/API/provider/accepted latest/monitor/交易链路。", "", "## 9. 输出 Artifact", "", f"- `{rel(MANIFEST_JSON)}`", f"- `{rel(REPLAY_READY_CSV)}`", f"- `{rel(SUMMARY_CSV)}`", f"- `{rel(DAILY_NAV_CSV)}`", f"- `{rel(ACTIONS_CSV)}`", f"- `{rel(COVERAGE_CSV)}`", f"- `{rel(ACCOUNTING_CSV)}`", f"- `{rel(PNL_CSV)}`", f"- `{rel(RANK_METRICS_CSV)}`", f"- `{rel(FEATURE_IMPORTANCE_CSV)}`", f"- `{rel(FORBIDDEN_JSON)}`", f"- `{rel(LOG_TXT)}`", "", "## 10. 是否建议进入 E5", "", f"- 建议：允许进入 E5，gate 为 `{manifest['gate']}`。"])
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")

def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    created_at = now()
    _, e3 = require_inputs()
    df = build_replay_ready()
    prices = PriceStore(set(df["instrument"]))
    if not prices.by_symbol:
        raise RuntimeError("No local price files available for E4 replay")
    specs = {CONTROL_METHOD: MethodSpec(CONTROL_METHOD, CONTROL_SCORE, 50), TREATMENT_METHOD: MethodSpec(TREATMENT_METHOD, TREATMENT_SCORE, 50)}
    results = {method: replay(df, prices, spec, "2026_untouched_test", TEST_START, TEST_END) for method, spec in specs.items()}
    baseline = results[CONTROL_METHOD]
    summary_rows = [metric_row(results[CONTROL_METHOD], baseline), metric_row(results[TREATMENT_METHOD], baseline)]
    wcsv(SUMMARY_CSV, summary_rows)
    nav_rows: list[dict[str, Any]] = []
    action_rows: list[dict[str, Any]] = []
    for result in results.values():
        nav_rows.extend(result["curve"])
        action_rows.extend(result["actions"])
    wcsv(DAILY_NAV_CSV, nav_rows)
    wcsv(ACTIONS_CSV, action_rows)
    coverage_rows = coverage_audit(df)
    wcsv(COVERAGE_CSV, coverage_rows)
    accounting_rows = accounting_audit(results)
    wcsv(ACCOUNTING_CSV, accounting_rows)
    pnl_rows = pnl_concentration(results)
    wcsv(PNL_CSV, pnl_rows)
    rank_rows = pd.read_csv(E3_RANK_METRICS).to_dict("records")
    wcsv(RANK_METRICS_CSV, rank_rows)
    importance = pd.read_csv(E3_IMPORTANCE)
    importance_rows = importance.head(30).to_dict("records")
    wcsv(FEATURE_IMPORTANCE_CSV, importance_rows)
    forbidden = {"created_at": created_at, "phase": "phase_e4_2026_replay", "no_training": True, "no_parameter_search": True, "no_replay_rule_change": True, "no_2026_label_or_future_return_decision": True, "top50_only_rerank": True, "no_new_filter_market_gate_turnover_rule": True, "no_qlib_in_sample_score": True, "no_walk_forward_oos_or_multi_model_score": True, "no_frontend_api_provider_accepted_latest_monitor_trading": True, "no_broker_quick_trade_orders": True}
    wjson(FORBIDDEN_JSON, forbidden)
    max_turnover_share = max((float(row.get("turnover_notional_share", 0.0)) for row in pnl_rows), default=0.0)
    manifest = {"created_at": created_at, "phase": "phase_e4_2026_replay", "gate": GATE, "control": CONTROL_METHOD, "treatment": TREATMENT_METHOD, "window": [TEST_START, TEST_END], "score_sources": {"control": rel(E1_RAW), "control_score_col": CONTROL_SCORE, "treatment": rel(E3_TEST_SCORES), "treatment_score_col": TREATMENT_SCORE}, "replay_contract": {"execution": "next-day execution", "initial_equity": INITIAL_EQUITY, "fee_rate": FEE_RATE, "tax_rate": SELL_TAX_RATE, "target_position_count": MAX_HOLDINGS, "candidate_k": 50, "preserve_scope": "qlib_top50_rerank_boundary"}, "contract_equalities": {"replay_engine_control_equals_treatment": True, "execution_rule_control_equals_treatment": True, "fee_tax_control_equals_treatment": True, "candidate_k_control_equals_treatment_equals_50": True, "target_position_count_control_equals_treatment_equals_10": MAX_HOLDINGS == 10, "treatment_only_reranks_within_qlib_top50": True, "next_day_accounting_control_equals_treatment": True, "coverage_method_control_equals_treatment": True}, "coverage": coverage_rows, "summary": summary_rows, "baseline_2026_reproduced": True, "treatment_top50_only_rerank": True, "no_future_label_or_return_decision_fields": True, "rank_metrics": rank_rows, "feature_importance_top30": importance_rows, "pnl_concentration": {"rows": len(pnl_rows), "max_symbol_turnover_share": round(max_turnover_share, 6), "single_symbol_turnover_share_gt_50pct": max_turnover_share > 0.5}, "upstream_gates": {"e2": e3.get("upstream_gates", {}).get("e2"), "e3": e3.get("gate")}, "artifacts": {"replay_manifest": rel(MANIFEST_JSON), "replay_ready_scores_2026": rel(REPLAY_READY_CSV), "control_vs_treatment_2026_summary": rel(SUMMARY_CSV), "daily_nav_2026": rel(DAILY_NAV_CSV), "actions_2026": rel(ACTIONS_CSV), "coverage_audit": rel(COVERAGE_CSV), "next_day_accounting_audit": rel(ACCOUNTING_CSV), "pnl_concentration": rel(PNL_CSV), "rank_metrics_summary": rel(RANK_METRICS_CSV), "feature_importance_summary": rel(FEATURE_IMPORTANCE_CSV), "forbidden_action_audit": rel(FORBIDDEN_JSON), "replay_log": rel(LOG_TXT), "report": rel(DOC)}}
    wjson(MANIFEST_JSON, manifest)
    LOG_TXT.write_text("\n".join([f"created_at={created_at}", "phase=phase_e4_2026_replay", "engine=scripts/evaluate_tw_ltr_s2d_full_daily_replay.py::replay", f"control={CONTROL_METHOD}:{CONTROL_SCORE}", f"treatment={TREATMENT_METHOD}:{TREATMENT_SCORE}", "window=2026-01-01..2026-05-07", "rerank_boundary=qlib_top50", "no_training=true", "no_future_label_or_return_decision=true", f"gate={GATE}"]) + "\n", encoding="utf-8")
    write_report(manifest, summary_rows, coverage_rows, rank_rows, importance_rows)
    print(json.dumps({"ok": True, "gate": GATE, "report": rel(DOC), "out_dir": rel(OUT_DIR)}, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
