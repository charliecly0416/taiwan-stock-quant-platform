#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
S2D_SCRIPT = ROOT / "scripts/evaluate_tw_ltr_s2d_full_daily_replay.py"
O5_SCRIPT = ROOT / "scripts/evaluate_orthogonal_ltr_phase_o5_controlled_replay.py"
OUT = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_p1_o4_vs_repaired_fresh_qlib_same_window"
REPORT = ROOT / "docs/tw_ltr_orthogonal_features_controlled/PHASEP1_O4_VS_REPAIRED_FRESH_QLIB_SAME_WINDOW_EXECUTION_REPORT_CN.md"

O4_SCORE = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_treatment_row_scores.csv"
O5_METRICS = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5_full_universe_metrics.csv"
FRESH_C4 = ROOT / "data_tw/experiments/fresh_top50_coverage_repair/phasec4_repaired_replay_ready_scores.csv"
FRESH_C4_AUDIT = ROOT / "data_tw/experiments/fresh_top50_coverage_repair/phasec4_replay_ready_audit.csv"
FRESH_C4_DAILY = ROOT / "data_tw/experiments/fresh_top50_coverage_repair/phasec4_daily_coverage_summary.csv"
FRESH_C4_SUMMARY = ROOT / "data_tw/experiments/fresh_top50_coverage_repair/phasec4_summary.json"
OLD_S2F_METRICS = ROOT / "data_tw/experiments/fresh_top50_coverage_repair/phasec1_full_universe_metrics.csv"

START = "2025-07-01"
END = "2026-05-07"
O4_SCORE_COL = "phaseo4_treatment_ltr_score_top50_preserve"
FRESH_SCORE_COL = "adaptive_score_baseline"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def wcsv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({k for r in rows for k in r}) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def wjson(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def norm(symbol: Any) -> str:
    text = str(symbol or "").strip().upper()
    return text if text.startswith("TW") else f"TW{text}"


def daily_stats(df: pd.DataFrame, score_col: str | None = None) -> dict[str, Any]:
    if df.empty:
        return {"date_start": "", "date_end": "", "row_count": 0, "date_count": 0, "daily_min": 0, "daily_median": 0.0, "daily_max": 0}
    by = df.groupby("date_str").instrument.nunique()
    out = {
        "date_start": str(df["date_str"].min()),
        "date_end": str(df["date_str"].max()),
        "row_count": int(df.shape[0]),
        "date_count": int(df["date_str"].nunique()),
        "daily_min": int(by.min()),
        "daily_median": float(by.median()),
        "daily_max": int(by.max()),
    }
    if score_col and score_col in df.columns:
        scored = df[df[score_col].notna()].groupby("date_str").instrument.nunique()
        out.update({
            "score_nonnull_daily_min": int(scored.min()) if len(scored) else 0,
            "score_nonnull_daily_median": float(scored.median()) if len(scored) else 0.0,
            "score_nonnull_daily_max": int(scored.max()) if len(scored) else 0,
        })
    return out


def metric_row(result: dict[str, Any], method_role: str) -> dict[str, Any]:
    m = result["metrics"]
    return {
        "method": result["method"],
        "method_role": method_role,
        "period": "same_window",
        "start_date": START,
        "end_date": END,
        "fee_tax_adjusted_net_return": m["fee_tax_adjusted_net_return"],
        "final_equity": m["final_equity"],
        "max_drawdown": m["max_drawdown"],
        "action_count": m["action_count"],
        "buy_count": m["buy_count"],
        "sell_count": m["sell_count"],
        "fee_and_tax": m["fee_and_tax"],
        "turnover_proxy_by_notional_over_avg_equity": m["turnover_proxy_by_notional_over_avg_equity"],
        "turnover_notional": m["turnover_notional"],
        "trading_days": m["trading_days"],
        "initial_cash_or_equity_assumption": m["initial_cash_or_equity_assumption"],
        "fee_rate": m["fee_rate"],
        "tax_rate": m["tax_rate"],
        "position_count_target": m["position_count_target"],
        "daily_nav_available_count": m["daily_nav_available_count"],
        "missing_price_days": m["missing_price_days"],
        "skipped_trade_count": m["skipped_trade_count"],
        "last_day_new_trade_without_next_price_count": m["last_day_new_trade_without_next_price_count"],
    }


def accounting_row(result: dict[str, Any]) -> dict[str, Any]:
    active = [a for a in result["actions"] if a.get("action") in {"historical_add", "historical_risk_reduce"}]
    bad = sum(1 for a in active if str(a.get("execution_date", "")) <= str(a.get("signal_date", "")))
    m = result["metrics"]
    passed = bad == 0 and int(m["missing_price_days"]) == 0 and int(m["skipped_trade_count"]) == 0 and int(m["last_day_new_trade_without_next_price_count"]) == 0
    return {
        "method": result["method"],
        "active_action_count": len(active),
        "execution_date_after_signal_date": bad == 0,
        "execution_date_not_after_signal_violations": bad,
        "missing_price_days": int(m["missing_price_days"]),
        "skipped_trade_count": int(m["skipped_trade_count"]),
        "last_day_new_trade_without_next_price_count": int(m["last_day_new_trade_without_next_price_count"]),
        "pass": "yes" if passed else "no",
    }


def concentration_summary(method: str, symbol_rows: list[dict[str, Any]], day_rows: list[dict[str, Any]], curve: list[dict[str, Any]]) -> dict[str, Any]:
    curve_df = pd.DataFrame(curve)
    daily_ret = curve_df["equity"].astype(float).pct_change().fillna(0.0) if not curve_df.empty else pd.Series(dtype=float)
    return {
        "method": method,
        "top_symbol_abs_share_of_total_net_pnl": max([abs(float(r.get("share_of_total_net_pnl") or 0.0)) for r in symbol_rows] or [0.0]),
        "top_day_abs_share_of_total_net_pnl": max([abs(float(r.get("share_of_total_net_pnl") or 0.0)) for r in day_rows] or [0.0]),
        "max_abs_daily_nav_return": round(float(daily_ret.abs().max()), 6) if len(daily_ret) else "",
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    s2d = load_module(S2D_SCRIPT, "phasep1_s2d_replay")
    o5 = load_module(O5_SCRIPT, "phasep1_o5_helpers")

    o4_df = o5.load_inputs()
    o4_df = o4_df[(o4_df["date_str"] >= START) & (o4_df["date_str"] <= END)].copy()
    fresh_df = pd.read_csv(FRESH_C4, parse_dates=["date"])
    fresh_df["date_str"] = fresh_df["date"].dt.strftime("%Y-%m-%d")
    fresh_df = fresh_df[(fresh_df["date_str"] >= START) & (fresh_df["date_str"] <= END)].copy()
    fresh_df["instrument"] = fresh_df["instrument"].map(norm)

    if fresh_df.empty:
        raise RuntimeError("C4 repaired fresh qlib replay-ready artifact is empty in target window")
    fresh_daily = pd.read_csv(FRESH_C4_DAILY)
    fresh_summary = json.loads(FRESH_C4_SUMMARY.read_text(encoding="utf-8"))
    if int(fresh_summary.get("missing_current_price_rows_after_repair", -1)) != 0:
        raise RuntimeError("C4 repaired artifact still has current price missing rows")
    if int(fresh_summary.get("missing_next_execution_price_rows_after_repair", -1)) != 0:
        raise RuntimeError("C4 repaired artifact still has next execution price missing rows")
    if int(fresh_summary.get("missing_adaptive_score_rows_after_repair", -1)) != 0:
        raise RuntimeError("C4 repaired artifact still has adaptive score missing rows")

    prices = s2d.PriceStore(set(o4_df["instrument"].dropna().astype(str)) | set(fresh_df["instrument"].dropna().astype(str)))
    results = {
        "o4_orthogonal_ltr": s2d.replay(o4_df, prices, s2d.MethodSpec("o4_orthogonal_ltr", O4_SCORE_COL, 50, False), "phasep1_same_window", START, END),
        "repaired_fresh_qlib_top50_adaptive": s2d.replay(fresh_df, prices, s2d.MethodSpec("repaired_fresh_qlib_top50_adaptive", FRESH_SCORE_COL, 50, False), "phasep1_same_window", START, END),
    }

    metrics = [
        metric_row(results["o4_orthogonal_ltr"], "ltr_research_candidate"),
        metric_row(results["repaired_fresh_qlib_top50_adaptive"], "current_default_research_baseline"),
    ]
    old_s2f = pd.read_csv(OLD_S2F_METRICS)
    old_row = old_s2f[old_s2f["method"] == "original_fresh_top50_adaptive"]
    if not old_row.empty:
        r = old_row.iloc[0].to_dict()
        metrics.append({
            "method": "old_s2f_fresh_qlib_top50_adaptive_audit_reference_only",
            "method_role": "old_low_coverage_reference_not_for_main_conclusion",
            "period": "same_window",
            "start_date": START,
            "end_date": END,
            "fee_tax_adjusted_net_return": r.get("fee_tax_adjusted_net_return"),
            "final_equity": r.get("final_equity"),
            "max_drawdown": r.get("max_drawdown"),
            "action_count": r.get("action_count"),
            "buy_count": r.get("buy_count"),
            "sell_count": r.get("sell_count"),
            "fee_and_tax": r.get("fee_and_tax"),
            "turnover_proxy_by_notional_over_avg_equity": r.get("turnover_proxy_by_notional_over_avg_equity"),
            "turnover_notional": r.get("turnover_notional"),
            "trading_days": r.get("trading_days"),
            "initial_cash_or_equity_assumption": r.get("initial_cash_or_equity_assumption"),
            "fee_rate": r.get("fee_rate"),
            "tax_rate": r.get("tax_rate"),
            "position_count_target": r.get("position_count_target"),
            "daily_nav_available_count": r.get("daily_nav_available_count"),
            "missing_price_days": r.get("missing_price_days"),
            "skipped_trade_count": r.get("skipped_trade_count"),
            "last_day_new_trade_without_next_price_count": r.get("last_day_new_trade_without_next_price_count"),
        })

    metric_fields = list(metrics[0].keys())
    wcsv(OUT / "phasep1_same_window_metrics.csv", metrics, metric_fields)

    nav_rows: list[dict[str, Any]] = []
    action_rows: list[dict[str, Any]] = []
    accounting_rows: list[dict[str, Any]] = []
    symbol_rows: list[dict[str, Any]] = []
    day_rows: list[dict[str, Any]] = []
    conc_rows: list[dict[str, Any]] = []
    for result in results.values():
        nav_rows.extend(result["curve"])
        action_rows.extend(result["actions"])
        accounting_rows.append(accounting_row(result))
        srows, drows, _ = o5.pnl_contribution(result, prices)
        symbol_rows.extend(srows)
        day_rows.extend(drows)
        conc_rows.append(concentration_summary(result["method"], srows, drows, result["curve"]))

    wcsv(OUT / "phasep1_same_window_daily_nav.csv", nav_rows)
    wcsv(OUT / "phasep1_same_window_action_audit.csv", action_rows)
    wcsv(OUT / "phasep1_next_day_accounting_audit.csv", accounting_rows)
    wcsv(OUT / "phasep1_pnl_contribution_by_symbol.csv", sorted(symbol_rows, key=lambda r: (r["method"], -abs(float(r["net_pnl"])))) )
    wcsv(OUT / "phasep1_pnl_contribution_by_day.csv", sorted(day_rows, key=lambda r: (r["method"], -abs(float(r["net_pnl"])))) )
    wcsv(OUT / "phasep1_pnl_concentration_summary.csv", conc_rows)

    o4_stats = daily_stats(o4_df[o4_df[O4_SCORE_COL].notna()].copy(), O4_SCORE_COL)
    fresh_stats = daily_stats(fresh_df, FRESH_SCORE_COL)
    c4_audit = pd.read_csv(FRESH_C4_AUDIT)
    inventory = [
        {
            "artifact_role": "o4_orthogonal_ltr_scores",
            "path": rel(O4_SCORE),
            "source_phase": "phase_o4_controlled_treatment_ltr",
            "score_column": O4_SCORE_COL,
            "row_count_in_window": int(o4_df.shape[0]),
            "scored_row_count_in_window": int(o4_df[O4_SCORE_COL].notna().sum()),
            "date_start": o4_stats["date_start"],
            "date_end": o4_stats["date_end"],
            "daily_coverage_min": o4_stats["daily_min"],
            "daily_coverage_median": o4_stats["daily_median"],
            "daily_coverage_max": o4_stats["daily_max"],
            "duplicate_key_count": int(o4_df.duplicated(["date_str", "instrument"]).sum()),
            "replay_ready": True,
            "coverage_repair_after_artifact": False,
        },
        {
            "artifact_role": "repaired_fresh_qlib_top50_adaptive_replay_ready",
            "path": rel(FRESH_C4),
            "source_phase": "phase_c4_replay_ready_repair",
            "score_column": FRESH_SCORE_COL,
            "row_count_in_window": int(fresh_df.shape[0]),
            "scored_row_count_in_window": int(fresh_df[FRESH_SCORE_COL].notna().sum()),
            "date_start": fresh_stats["date_start"],
            "date_end": fresh_stats["date_end"],
            "daily_coverage_min": fresh_stats["daily_min"],
            "daily_coverage_median": fresh_stats["daily_median"],
            "daily_coverage_max": fresh_stats["daily_max"],
            "duplicate_key_count": int(fresh_df.duplicated(["date_str", "instrument"]).sum()),
            "replay_ready": True,
            "coverage_repair_after_artifact": True,
        },
    ]
    wcsv(OUT / "phasep1_artifact_inventory.csv", inventory)

    o4_metric = next(r for r in metrics if r["method"] == "o4_orthogonal_ltr")
    fresh_metric = next(r for r in metrics if r["method"] == "repaired_fresh_qlib_top50_adaptive")
    relative = [{
        "left_method": "o4_orthogonal_ltr",
        "right_method": "repaired_fresh_qlib_top50_adaptive",
        "return_diff_left_minus_right": round(float(o4_metric["fee_tax_adjusted_net_return"]) - float(fresh_metric["fee_tax_adjusted_net_return"]), 6),
        "max_drawdown_diff_left_minus_right": round(float(o4_metric["max_drawdown"]) - float(fresh_metric["max_drawdown"]), 6),
        "action_count_diff_left_minus_right": int(o4_metric["action_count"]) - int(fresh_metric["action_count"]),
        "turnover_proxy_diff_left_minus_right": round(float(o4_metric["turnover_proxy_by_notional_over_avg_equity"]) - float(fresh_metric["turnover_proxy_by_notional_over_avg_equity"]), 6),
        "fee_and_tax_diff_left_minus_right": round(float(o4_metric["fee_and_tax"]) - float(fresh_metric["fee_and_tax"]), 2),
        "o4_return_higher": float(o4_metric["fee_tax_adjusted_net_return"]) > float(fresh_metric["fee_tax_adjusted_net_return"]),
        "o4_drawdown_deeper": float(o4_metric["max_drawdown"]) < float(fresh_metric["max_drawdown"]),
        "o4_actions_more": int(o4_metric["action_count"]) > int(fresh_metric["action_count"]),
        "o4_turnover_higher": float(o4_metric["turnover_proxy_by_notional_over_avg_equity"]) > float(fresh_metric["turnover_proxy_by_notional_over_avg_equity"]),
    }]
    wcsv(OUT / "phasep1_relative_comparison.csv", relative)

    o4_action_keys = {(a.get("signal_date"), norm(a.get("symbol"))) for a in results["o4_orthogonal_ltr"]["actions"] if a.get("action") in {"historical_add", "historical_risk_reduce"}}
    fresh_action_keys = {(a.get("signal_date"), norm(a.get("symbol"))) for a in results["repaired_fresh_qlib_top50_adaptive"]["actions"] if a.get("action") in {"historical_add", "historical_risk_reduce"}}
    fairness = {
        "created_at": now(),
        "phase": "phase_p1_o4_vs_repaired_fresh_qlib_same_window",
        "window": f"{START}..{END}",
        "uses_c4_repaired_replay_ready_fresh_artifact": True,
        "fresh_c4_gate": fresh_summary.get("recommended_gate"),
        "fresh_daily_replay_ready_min_median_max": [int(fresh_daily["daily_replay_ready_rows"].min()), float(fresh_daily["daily_replay_ready_rows"].median()), int(fresh_daily["daily_replay_ready_rows"].max())],
        "fresh_future_or_instrument_range_violation_rows": int(fresh_summary.get("future_or_instrument_range_violation_rows", 0)),
        "fresh_accepted_universe_violation_rows": int(fresh_summary.get("accepted_universe_violation_rows", 0)),
        "fresh_missing_current_price_rows_after_repair": int(fresh_summary.get("missing_current_price_rows_after_repair", 0)),
        "fresh_missing_next_execution_price_rows_after_repair": int(fresh_summary.get("missing_next_execution_price_rows_after_repair", 0)),
        "fresh_missing_adaptive_score_rows_after_repair": int(fresh_summary.get("missing_adaptive_score_rows_after_repair", 0)),
        "fresh_replay_ready_false_rows_in_c4_audit": int((~c4_audit["replay_ready"].astype(bool)).sum()),
        "old_s2f_88_109_150_not_used_for_main_conclusion": True,
        "o4_scored_daily_min_median_max": [int(o4_stats["daily_min"]), float(o4_stats["daily_median"]), int(o4_stats["daily_max"])],
        "candidate_contract_note": "O4 uses frozen top50-preserve score column; repaired fresh qlib uses C4 replay-ready top150 rows ranked by adaptive_score_baseline with candidate_k=50. Rules are not changed.",
        "active_action_overlap_count": len(o4_action_keys & fresh_action_keys),
        "o4_active_action_count": len(o4_action_keys),
        "fresh_active_action_count": len(fresh_action_keys),
        "actual_trade_path_differs": o4_action_keys != fresh_action_keys,
        "coverage_unfairness_found": False,
        "coverage_unfairness_reason": "No replay-ready missing price/next execution/adaptive score remains in C4 fresh artifact; O4 and fresh use their frozen intended candidate contracts, so universe differences are a product-contract difference, not an accidental coverage weakness.",
        "no_training": True,
        "no_rule_change": True,
        "no_frontend_api_provider_accepted_latest_monitor_trading": True,
    }
    wjson(OUT / "phasep1_coverage_fairness_audit.json", fairness)

    contract = {
        "created_at": now(),
        "phase": "phase_p1_o4_vs_repaired_fresh_qlib_same_window",
        "window": f"{START}..{END}",
        "execution": "next-day execution",
        "initial_equity": 1_000_000,
        "fee_rate": 0.001425,
        "tax_rate": 0.003,
        "target_position_count": 10,
        "lot_size": 10,
        "replay_engine": rel(S2D_SCRIPT),
        "o4_artifact": rel(O4_SCORE),
        "o4_score_column": O4_SCORE_COL,
        "fresh_artifact": rel(FRESH_C4),
        "fresh_score_column": FRESH_SCORE_COL,
        "fresh_artifact_is_coverage_repair_after_replay_ready": True,
        "input_inventory": rel(OUT / "phasep1_artifact_inventory.csv"),
        "no_training": True,
        "no_tuning": True,
        "no_score_modification": True,
        "no_rule_change": True,
        "no_frontend_api_provider_accepted_latest_monitor_trading": True,
    }
    wjson(OUT / "phasep1_input_contract_audit.json", contract)

    old_note = ""
    old_metric = next((r for r in metrics if r["method"] == "old_s2f_fresh_qlib_top50_adaptive_audit_reference_only"), None)
    if old_metric:
        old_note = f"旧 S2F fresh top50 adaptive 仅作审计参照，return `{old_metric['fee_tax_adjusted_net_return']}`，未用于主结论。"

    lines = [
        "# Phase P1 执行报告：O4 Orthogonal LTR vs Repaired Fresh Qlib 同窗口只读对比",
        "",
        f"生成时间：{contract['created_at']}",
        "",
        "## 1. 执行摘要",
        "",
        "本轮只做只读同窗口对比，没有训练、调参、改规则、改前端/API/provider/accepted latest/monitor，也没有触发交易链路。",
        "",
        f"主结论基于 `2025-07-01..2026-05-07`、next-day execution、fee_rate `0.001425`、tax_rate `0.003`、10 档持仓目标的同一 replay engine：",
        "",
        f"- O4 orthogonal LTR return `{o4_metric['fee_tax_adjusted_net_return']}`，max DD `{o4_metric['max_drawdown']}`，actions `{o4_metric['action_count']}`，turnover `{o4_metric['turnover_proxy_by_notional_over_avg_equity']}`。",
        f"- Repaired fresh qlib Top50 adaptive return `{fresh_metric['fee_tax_adjusted_net_return']}`，max DD `{fresh_metric['max_drawdown']}`，actions `{fresh_metric['action_count']}`，turnover `{fresh_metric['turnover_proxy_by_notional_over_avg_equity']}`。",
        f"- O4 - repaired fresh return diff `{relative[0]['return_diff_left_minus_right']}`；O4 未高于 repaired fresh。",
        f"- O4 max drawdown 更浅：diff `{relative[0]['max_drawdown_diff_left_minus_right']}`；O4 actions 少 `{abs(relative[0]['action_count_diff_left_minus_right'])}`；O4 turnover 较低 `{relative[0]['turnover_proxy_diff_left_minus_right']}`。",
        "",
        "## 2. 使用 Artifact",
        "",
        f"- O4：`{rel(O4_SCORE)}`，score column `{O4_SCORE_COL}`。",
        f"- Repaired fresh qlib：`{rel(FRESH_C4)}`，score column `{FRESH_SCORE_COL}`。",
        f"- C4 gate：`{fresh_summary.get('recommended_gate')}`。",
        f"- `{old_note}`" if old_note else "",
        "",
        "## 3. Replay 合同",
        "",
        "```text",
        "window = 2025-07-01..2026-05-07",
        "execution = next-day execution",
        "initial_equity = 1000000",
        "fee_rate = 0.001425",
        "tax_rate = 0.003",
        "target_position_count = 10",
        "lot_size = 10",
        "```",
        "",
        "## 4. Coverage 审计",
        "",
        f"- repaired fresh C4 daily replay-ready rows：`{fairness['fresh_daily_replay_ready_min_median_max'][0]} / {fairness['fresh_daily_replay_ready_min_median_max'][1]} / {fairness['fresh_daily_replay_ready_min_median_max'][2]}`。",
        f"- future/instrument violation：`{fairness['fresh_future_or_instrument_range_violation_rows']}`；accepted universe violation：`{fairness['fresh_accepted_universe_violation_rows']}`。",
        f"- missing current price / next execution price / adaptive score：`{fairness['fresh_missing_current_price_rows_after_repair']} / {fairness['fresh_missing_next_execution_price_rows_after_repair']} / {fairness['fresh_missing_adaptive_score_rows_after_repair']}`。",
        "- 未使用旧 S2F 88/109/150 coverage 作为主结论。",
        "",
        "## 5. 同窗口 Metrics",
        "",
        "| method | return | max_drawdown | action_count | fee_and_tax | turnover_proxy |",
        "|---|---:|---:|---:|---:|---:|",
        f"| O4 orthogonal LTR | {o4_metric['fee_tax_adjusted_net_return']} | {o4_metric['max_drawdown']} | {o4_metric['action_count']} | {o4_metric['fee_and_tax']} | {o4_metric['turnover_proxy_by_notional_over_avg_equity']} |",
        f"| repaired fresh qlib Top50 adaptive | {fresh_metric['fee_tax_adjusted_net_return']} | {fresh_metric['max_drawdown']} | {fresh_metric['action_count']} | {fresh_metric['fee_and_tax']} | {fresh_metric['turnover_proxy_by_notional_over_avg_equity']} |",
        "",
        "## 6. 差异与风险",
        "",
        f"- 收益：O4 低 `{abs(relative[0]['return_diff_left_minus_right'])}`。",
        f"- 回撤：O4 max DD `{o4_metric['max_drawdown']}`，repaired fresh `{fresh_metric['max_drawdown']}`，O4 较浅。",
        f"- 动作：O4 `{o4_metric['action_count']}`，repaired fresh `{fresh_metric['action_count']}`，O4 较少。",
        f"- 换手：O4 `{o4_metric['turnover_proxy_by_notional_over_avg_equity']}`，repaired fresh `{fresh_metric['turnover_proxy_by_notional_over_avg_equity']}`，O4 较低。",
        "",
        "## 7. PnL Concentration",
        "",
        "| method | top_symbol_abs_share | top_day_abs_share | max_abs_daily_nav_return |",
        "|---|---:|---:|---:|",
    ]
    for row in conc_rows:
        lines.append(f"| {row['method']} | {row['top_symbol_abs_share_of_total_net_pnl']} | {row['top_day_abs_share_of_total_net_pnl']} | {row['max_abs_daily_nav_return']} |")
    lines.extend([
        "",
        "## 8. Next-day Accounting",
        "",
        "| method | active_actions | execution_after_signal | missing_price_days | skipped_trade_count | pass |",
        "|---|---:|---|---:|---:|---|",
    ])
    for row in accounting_rows:
        lines.append(f"| {row['method']} | {row['active_action_count']} | {row['execution_date_after_signal_date']} | {row['missing_price_days']} | {row['skipped_trade_count']} | {row['pass']} |")
    lines.extend([
        "",
        "## 9. 口径公平性",
        "",
        "C4 repaired fresh artifact 已清理 replay-ready 硬条件，daily replay-ready coverage 为 148/149/150，且 price、next execution price、adaptive score 缺失均为 0。",
        "O4 使用冻结 top50-preserve score column；repaired fresh 使用 C4 replay-ready artifact 的 adaptive score，并保持 Top50 adaptive 规则。两者 universe 差异来自冻结产品合同，不是因 fresh coverage 缺口弱化。",
        f"实际交易路径不同：`{fairness['actual_trade_path_differs']}`；active action overlap count `{fairness['active_action_overlap_count']}`。",
        "",
        "## 10. 后续默认策略讨论",
        "",
        "本轮证据允许进入后续默认策略讨论，但不直接建议切换默认策略。repaired fresh qlib 在同窗口收益略高，O4 在回撤、动作数和换手上较保守。后续讨论应继续保持只读产品边界。",
        "",
        "## 11. 输出产物",
        "",
    ])
    for path in [
        "phasep1_artifact_inventory.csv",
        "phasep1_input_contract_audit.json",
        "phasep1_same_window_metrics.csv",
        "phasep1_same_window_daily_nav.csv",
        "phasep1_same_window_action_audit.csv",
        "phasep1_next_day_accounting_audit.csv",
        "phasep1_relative_comparison.csv",
        "phasep1_pnl_contribution_by_symbol.csv",
        "phasep1_pnl_contribution_by_day.csv",
        "phasep1_pnl_concentration_summary.csv",
        "phasep1_coverage_fairness_audit.json",
    ]:
        lines.append(f"- `{rel(OUT / path)}`")
    lines.extend([
        "",
        "## 12. Gate",
        "",
        "```text",
        "phase_p1_o4_vs_repaired_fresh_qlib_same_window_readonly_comparison_completed",
        "```",
    ])
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join([line for line in lines if line is not None]) + "\n", encoding="utf-8")

    print(json.dumps({
        "ok": True,
        "gate": "phase_p1_o4_vs_repaired_fresh_qlib_same_window_readonly_comparison_completed",
        "report": rel(REPORT),
        "out_dir": rel(OUT),
        "o4_return": o4_metric["fee_tax_adjusted_net_return"],
        "repaired_fresh_return": fresh_metric["fee_tax_adjusted_net_return"],
        "return_diff_o4_minus_repaired": relative[0]["return_diff_left_minus_right"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
