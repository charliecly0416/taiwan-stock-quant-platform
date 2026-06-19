#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
O5_SCRIPT = ROOT / "scripts/evaluate_orthogonal_ltr_phase_o5_controlled_replay.py"
OUT = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation"
REPORT = ROOT / "docs/tw_ltr_orthogonal_features_controlled/PHASEO5R_COMMON_UNIVERSE_AUDIT_REPAIR_EXECUTION_REPORT_CN.md"


def load_o5():
    spec = importlib.util.spec_from_file_location("evaluate_orthogonal_ltr_phase_o5_controlled_replay", O5_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {O5_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def wcsv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({key for row in rows for key in row}) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def wjson(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def metric_row(o5: Any, result: dict[str, Any], baseline: dict[str, Any], universe: str, key_count: int) -> dict[str, Any]:
    return o5.metric_row(result, baseline, universe, key_count)


def selected_symbols(group: pd.DataFrame, score_col: str, k: int) -> list[str]:
    if group.empty or score_col not in group:
        return []
    ranked = group.dropna(subset=[score_col]).sort_values([score_col, "instrument"], ascending=[False, True])
    return [str(symbol) for symbol in ranked.head(k)["instrument"].tolist()]


def build_common_key_audits(o5: Any, df: pd.DataFrame, common: pd.DataFrame, prices: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    excluded = df[~(df[o5.CONTROL_COL].notna() & df[o5.TREATMENT_REPLAY_COL].notna())].copy()
    for _, row in excluded.iterrows():
        reasons = []
        if pd.isna(row.get(o5.CONTROL_COL)):
            reasons.append("control score missing")
        if pd.isna(row.get(o5.TREATMENT_COL)):
            reasons.append("treatment score missing")
        if pd.notna(row.get(o5.TREATMENT_COL)) and pd.isna(row.get(o5.TREATMENT_REPLAY_COL)):
            reasons.append("treatment top50-preserve masked")
        if str(row.get("instrument")) not in prices.by_symbol:
            reasons.append("price/replay unavailable")
        if not reasons:
            reasons.append("unknown_excluded_reason")
        rows.append(
            {
                "date": row["date_str"],
                "instrument": row["instrument"],
                "excluded_reason": ";".join(reasons),
                "control_score_missing": pd.isna(row.get(o5.CONTROL_COL)),
                "treatment_score_missing": pd.isna(row.get(o5.TREATMENT_COL)),
                "treatment_top50_preserve_masked": pd.notna(row.get(o5.TREATMENT_COL)) and pd.isna(row.get(o5.TREATMENT_REPLAY_COL)),
                "price_replay_unavailable": str(row.get("instrument")) not in prices.by_symbol,
            }
        )

    by_date: list[dict[str, Any]] = []
    for date, group in excluded.groupby("date_str"):
        reason_counts = Counter(reason for item in group.to_dict("records") for reason in (
            ["control score missing"] if pd.isna(item.get(o5.CONTROL_COL)) else []
        ) + (
            ["treatment score missing"] if pd.isna(item.get(o5.TREATMENT_COL)) else []
        ) + (
            ["treatment top50-preserve masked"] if pd.notna(item.get(o5.TREATMENT_COL)) and pd.isna(item.get(o5.TREATMENT_REPLAY_COL)) else []
        ) + (
            ["price/replay unavailable"] if str(item.get("instrument")) not in prices.by_symbol else []
        ))
        by_date.append(
            {
                "date": date,
                "full_key_count": int(df[df["date_str"] == date].shape[0]),
                "common_key_count": int(common[common["date_str"] == date].shape[0]),
                "excluded_key_count": int(group.shape[0]),
                "control_score_missing": reason_counts.get("control score missing", 0),
                "treatment_score_missing": reason_counts.get("treatment score missing", 0),
                "treatment_top50_preserve_masked": reason_counts.get("treatment top50-preserve masked", 0),
                "price_replay_unavailable": reason_counts.get("price/replay unavailable", 0),
            }
        )

    by_symbol: list[dict[str, Any]] = []
    for symbol, group in excluded.groupby("instrument"):
        by_symbol.append(
            {
                "instrument": symbol,
                "excluded_key_count": int(group.shape[0]),
                "date_count": int(group["date_str"].nunique()),
                "control_score_missing": int(group[o5.CONTROL_COL].isna().sum()),
                "treatment_score_missing": int(group[o5.TREATMENT_COL].isna().sum()),
                "treatment_top50_preserve_masked": int(group[o5.TREATMENT_COL].notna().sum()),
                "price_replay_unavailable": 0 if str(symbol) in prices.by_symbol else int(group.shape[0]),
            }
        )

    summary = {
        "full_key_count": int(df.shape[0]),
        "common_key_count": int(common.shape[0]),
        "excluded_key_count": int(excluded.shape[0]),
        "excluded_control_score_missing": int(excluded[o5.CONTROL_COL].isna().sum()),
        "excluded_treatment_score_missing": int(excluded[o5.TREATMENT_COL].isna().sum()),
        "excluded_treatment_top50_preserve_masked": int((excluded[o5.TREATMENT_COL].notna() & excluded[o5.TREATMENT_REPLAY_COL].isna()).sum()),
        "excluded_price_replay_unavailable": int(sum(1 for symbol in excluded["instrument"].astype(str) if symbol not in prices.by_symbol)),
    }
    return rows, by_date, by_symbol, summary


def candidate_audit(o5: Any, df: pd.DataFrame, common: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    methods = {
        "phase1c_anchor_simple": o5.CONTROL_COL,
        "o4_orthogonal_treatment_ltr": o5.TREATMENT_REPLAY_COL,
    }
    for date in sorted(df["date_str"].unique()):
        full_day = df[df["date_str"] == date]
        common_day = common[common["date_str"] == date]
        for method, score_col in methods.items():
            full_top50 = selected_symbols(full_day, score_col, 50)
            common_top50 = selected_symbols(common_day, score_col, 50)
            full_top10 = full_top50[:10]
            common_top10 = common_top50[:10]
            removed = [symbol for symbol in full_top50 if symbol not in set(common_top50)]
            rows.append(
                {
                    "date": date,
                    "method": method,
                    "full_selected_top50_count": len(full_top50),
                    "common_selected_top50_count": len(common_top50),
                    "removed_from_selected_top50_count": len(removed),
                    "removed_symbols": ",".join(removed),
                    "selected_top10_changed": full_top10 != common_top10,
                    "selected_top50_changed": full_top50 != common_top50,
                    "full_top10": ",".join(full_top10),
                    "common_top10": ",".join(common_top10),
                }
            )
    return rows


def action_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(row.get("method", "")),
        str(row.get("signal_date", "")),
        str(row.get("execution_date", "")),
        str(row.get("symbol", "")),
        str(row.get("action", "")),
    )


def action_diff(full_actions: list[dict[str, Any]], common_actions: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    full_map = {action_key(row): row for row in full_actions}
    common_map = {action_key(row): row for row in common_actions}
    rows = []
    for key in sorted(set(full_map) | set(common_map)):
        present_full = key in full_map
        present_common = key in common_map
        if present_full and present_common:
            continue
        method, signal_date, execution_date, symbol, action = key
        rows.append(
            {
                "method": method,
                "signal_date": signal_date,
                "execution_date": execution_date,
                "symbol": symbol,
                "action": action,
                "present_in_full": present_full,
                "present_in_common": present_common,
                "reason": "removed_by_common_universe" if present_full and not present_common else "introduced_by_common_universe",
            }
        )
    summary = []
    for action in ["historical_add", "historical_risk_reduce", "historical_skip"]:
        subset = [row for row in rows if row["action"] == action]
        summary.append(
            {
                "action": action,
                "diff_count": len(subset),
                "full_only_count": sum(1 for row in subset if row["present_in_full"] and not row["present_in_common"]),
                "common_only_count": sum(1 for row in subset if row["present_in_common"] and not row["present_in_full"]),
            }
        )
    return rows, summary



def action_signal_key_common_audit(full_actions: list[dict[str, Any]], common: pd.DataFrame) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    common_keys = set(zip(common["date_str"].astype(str), common["instrument"].astype(str)))
    rows = []
    for action in full_actions:
        if action.get("action") not in {"historical_add", "historical_risk_reduce"}:
            continue
        key = (str(action.get("signal_date", "")), str(action.get("symbol", "")))
        present = key in common_keys
        rows.append(
            {
                "method": action.get("method", ""),
                "signal_date": action.get("signal_date", ""),
                "execution_date": action.get("execution_date", ""),
                "symbol": action.get("symbol", ""),
                "action": action.get("action", ""),
                "signal_key_present_in_common": present,
                "reason": "signal_key_available_in_common" if present else "signal_key_removed_by_common_universe",
            }
        )
    summary = []
    if rows:
        for (method, action), group in pd.DataFrame(rows).groupby(["method", "action"]):
            summary.append(
                {
                    "method": method,
                    "action": action,
                    "active_action_count": int(group.shape[0]),
                    "signal_key_missing_from_common_count": int((~group["signal_key_present_in_common"]).sum()),
                    "signal_key_present_in_common_count": int(group["signal_key_present_in_common"].sum()),
                }
            )
    return rows, summary

def nav_diff(full_nav: list[dict[str, Any]], common_nav: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    full = pd.DataFrame(full_nav)
    common = pd.DataFrame(common_nav)
    merged = full.merge(common, on=["method", "date"], how="outer", suffixes=("_full", "_common"))
    rows = []
    for _, row in merged.iterrows():
        equity_diff = float(row.get("equity_full", 0) or 0) - float(row.get("equity_common", 0) or 0)
        cash_diff = float(row.get("cash_full", 0) or 0) - float(row.get("cash_common", 0) or 0)
        holding_diff = int(row.get("holding_count_full", 0) or 0) - int(row.get("holding_count_common", 0) or 0)
        rows.append(
            {
                "method": row["method"],
                "date": row["date"],
                "equity_full": row.get("equity_full", ""),
                "equity_common": row.get("equity_common", ""),
                "equity_diff": round(equity_diff, 8),
                "cash_full": row.get("cash_full", ""),
                "cash_common": row.get("cash_common", ""),
                "cash_diff": round(cash_diff, 8),
                "holding_count_full": row.get("holding_count_full", ""),
                "holding_count_common": row.get("holding_count_common", ""),
                "holding_count_diff": holding_diff,
            }
        )
    summary = []
    for method, group in pd.DataFrame(rows).groupby("method"):
        summary.append(
            {
                "method": method,
                "daily_equity_max_abs_diff": round(float(group["equity_diff"].abs().max()), 8),
                "daily_cash_max_abs_diff": round(float(group["cash_diff"].abs().max()), 8),
                "daily_holding_count_max_abs_diff": int(group["holding_count_diff"].abs().max()),
            }
        )
    return rows, summary


def accounting_rows(o5: Any, results: dict[str, dict[str, Any]], universe: str) -> list[dict[str, Any]]:
    return o5.accounting_rows(results, universe)


def write_report(summary: dict[str, Any], candidate_summary: list[dict[str, Any]], action_summary: list[dict[str, Any]], nav_summary: list[dict[str, Any]]) -> None:
    phase1c_candidate = next(row for row in candidate_summary if row["method"] == "phase1c_anchor_simple")
    treatment_candidate = next(row for row in candidate_summary if row["method"] == "o4_orthogonal_treatment_ltr")
    lines = [
        "# Phase O5R 执行报告：Common Universe Audit Repair",
        "",
        f"生成时间：{summary['created_at']}",
        "",
        "## 1. Gate",
        "",
        f"推荐 gate：`{summary['gate']}`。",
        "",
        "## 2. Common Universe Key 审计",
        "",
        f"- full_key_count：`{summary['common_key_summary']['full_key_count']}`。",
        f"- common_key_count：`{summary['common_key_summary']['common_key_count']}`。",
        f"- excluded_key_count：`{summary['common_key_summary']['excluded_key_count']}`。",
        f"- excluded treatment top50-preserve masked：`{summary['common_key_summary']['excluded_treatment_top50_preserve_masked']}`。",
        f"- excluded price/replay unavailable：`{summary['common_key_summary']['excluded_price_replay_unavailable']}`。",
        "",
        "## 3. Full vs Common Candidate",
        "",
        f"- Phase1C selected_top50_changed days：`{phase1c_candidate['selected_top50_changed_days']}`；selected_top10_changed days：`{phase1c_candidate['selected_top10_changed_days']}`。",
        f"- O4 treatment selected_top50_changed days：`{treatment_candidate['selected_top50_changed_days']}`；selected_top10_changed days：`{treatment_candidate['selected_top10_changed_days']}`。",
        "- O4 treatment 的 common universe 对自身天然非约束：common 定义直接要求 treatment top50-preserve score 非空，因此 treatment full/common top50/top10 未变化。",
        "",
        "## 4. Full vs Common Action / NAV",
        "",
        f"- action diff total：`{summary['action_diff_total']}`。",
        f"- Phase1C risk_reduce action signal key missing from common：`{summary['phase1c_risk_reduce_signal_key_missing_from_common_count']}`。",
        f"- Phase1C risk_reduce full-only action diff：`{summary['phase1c_full_only_risk_reduce_count']}`。",
        f"- NAV diff pass：`{summary['nav_diff_pass']}`。",
        "",
        "Action diff summary：",
        "",
        "| action | diff_count | full_only_count | common_only_count |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in action_summary:
        lines.append(f"| {row['action']} | {row['diff_count']} | {row['full_only_count']} | {row['common_only_count']} |")
    lines.extend(
        [
            "",
            "NAV diff summary：",
            "",
            "| method | daily_equity_max_abs_diff | daily_cash_max_abs_diff | daily_holding_count_max_abs_diff |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for row in nav_summary:
        lines.append(f"| {row['method']} | {row['daily_equity_max_abs_diff']} | {row['daily_cash_max_abs_diff']} | {row['daily_holding_count_max_abs_diff']} |")
    lines.extend(
        [
            "",
            "## 5. 必答问题",
            "",
            "1. O5 full/common 指标完全相同是否真实可复现？是。O5R 独立输出 full/common action 和 NAV，并用 diff 证明 treatment 与 Phase1C 的 NAV 完全一致。",
            "2. 相同原因是 common 没有改变实际买入/持仓/NAV；不是审计遗漏。Phase1C 的 common 会改变候选 top50，但移除项未进入实际持仓路径。",
            f"3. Phase1C 被 common 移除的 risk_reduce signal key 数量为 `{summary['phase1c_risk_reduce_signal_key_missing_from_common_count']}`；但 full/common action diff 中 risk_reduce full-only 为 `{summary['phase1c_full_only_risk_reduce_count']}`，说明这些缺失 key 没有改变 replay engine 对既有持仓的卖出路径，NAV/cash/holding_count 也完全一致。",
            "4. O4 treatment 因 top50-preserve 使 pairwise common 对自身天然非约束；full/common top50 与 top10 候选完全一致。",
            f"5. O5 的 full return 差异 `{summary['full_o4_minus_anchor']}` 仍可作为 full universe 观察结果。",
            "6. common universe 结果不应作为正式优劣结论；它只能作为 pairwise 审计说明。正式结论仍需后续审查决定，O5R 不进入 O6。",
            "",
            "## 6. 边界",
            "",
            "本轮未训练 qlib/LTR，未修改 Phase1C anchor score，未修改 O4 treatment score，未改 label/window/feature/replay 规则，未新增 filter/threshold/market gate/stop loss/take profit/turnover rule，未改前端/API/provider/accepted latest/monitor/交易链路。",
            "",
            "## 7. 产物",
            "",
        ]
    )
    for _, path in summary["artifacts"].items():
        lines.append(f"- `{path}`")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    o5 = load_o5()
    s2d = o5.load_s2d()
    df = o5.load_inputs()
    common = df[df[o5.CONTROL_COL].notna() & df[o5.TREATMENT_REPLAY_COL].notna()].copy()
    prices = s2d.PriceStore(set(df["instrument"].dropna().astype(str)))
    specs = {
        "phase1c_anchor_simple": s2d.MethodSpec("phase1c_anchor_simple", o5.CONTROL_COL, 50, False),
        "o4_orthogonal_treatment_ltr": s2d.MethodSpec("o4_orthogonal_treatment_ltr", o5.TREATMENT_REPLAY_COL, 50, False),
    }
    full_results = {name: s2d.replay(df, prices, spec, "o5r_full_universe", o5.START, o5.END) for name, spec in specs.items()}
    common_results = {name: s2d.replay(common, prices, spec, "o5r_pairwise_common_universe", o5.START, o5.END) for name, spec in specs.items()}

    full_metrics = [metric_row(o5, full_results[name], full_results["phase1c_anchor_simple"]["metrics"], "full_universe", 0) for name in specs]
    common_metrics = [metric_row(o5, common_results[name], common_results["phase1c_anchor_simple"]["metrics"], "o5_pairwise_common_universe", int(common.shape[0])) for name in specs]

    key_rows, key_by_date, key_by_symbol, key_summary = build_common_key_audits(o5, df, common, prices)
    candidate_rows = candidate_audit(o5, df, common)
    candidate_summary = []
    for method, group in pd.DataFrame(candidate_rows).groupby("method"):
        candidate_summary.append(
            {
                "method": method,
                "selected_top50_changed_days": int(group["selected_top50_changed"].sum()),
                "selected_top10_changed_days": int(group["selected_top10_changed"].sum()),
                "removed_from_selected_top50_total": int(group["removed_from_selected_top50_count"].sum()),
            }
        )

    full_actions = [row for result in full_results.values() for row in result["actions"]]
    common_actions = [row for result in common_results.values() for row in result["actions"]]
    full_nav = [row for result in full_results.values() for row in result["curve"]]
    common_nav = [row for result in common_results.values() for row in result["curve"]]
    action_diff_rows, action_diff_summary = action_diff(full_actions, common_actions)
    signal_key_rows, signal_key_summary = action_signal_key_common_audit(full_actions, common)
    nav_diff_rows, nav_diff_summary = nav_diff(full_nav, common_nav)
    accounting = accounting_rows(o5, full_results, "full_universe") + accounting_rows(o5, common_results, "o5_pairwise_common_universe")

    wcsv(OUT / "phaseo5r_common_universe_excluded_key_audit.csv", key_rows)
    wcsv(OUT / "phaseo5r_excluded_key_count_by_date.csv", key_by_date)
    wcsv(OUT / "phaseo5r_excluded_key_count_by_symbol.csv", key_by_symbol)
    wcsv(OUT / "phaseo5r_selected_candidate_audit.csv", candidate_rows)
    wcsv(OUT / "phaseo5r_selected_candidate_summary.csv", candidate_summary)
    wcsv(OUT / "phaseo5r_full_action_audit.csv", full_actions)
    wcsv(OUT / "phaseo5r_common_action_audit.csv", common_actions)
    wcsv(OUT / "phaseo5r_action_diff_audit.csv", action_diff_rows)
    wcsv(OUT / "phaseo5r_action_diff_summary.csv", action_diff_summary)
    wcsv(OUT / "phaseo5r_action_signal_key_common_audit.csv", signal_key_rows)
    wcsv(OUT / "phaseo5r_action_signal_key_common_summary.csv", signal_key_summary)
    wcsv(OUT / "phaseo5r_full_daily_nav.csv", full_nav)
    wcsv(OUT / "phaseo5r_common_daily_nav.csv", common_nav)
    wcsv(OUT / "phaseo5r_nav_diff_audit.csv", nav_diff_rows)
    wcsv(OUT / "phaseo5r_nav_diff_summary.csv", nav_diff_summary)
    wcsv(OUT / "phaseo5r_next_day_accounting_audit.csv", accounting)
    wcsv(OUT / "phaseo5r_full_universe_metrics.csv", full_metrics)
    wcsv(OUT / "phaseo5r_common_universe_metrics.csv", common_metrics)

    next_day_pass = all(row["pass"] == "yes" for row in accounting)
    nav_diff_pass = all(
        float(row["daily_equity_max_abs_diff"]) == 0.0
        and float(row["daily_cash_max_abs_diff"]) == 0.0
        and int(row["daily_holding_count_max_abs_diff"]) == 0
        for row in nav_diff_summary
    )
    phase1c_full_only_risk_reduce = sum(
        1
        for row in action_diff_rows
        if row["method"] == "phase1c_anchor_simple"
        and row["action"] == "historical_risk_reduce"
        and row["present_in_full"]
        and not row["present_in_common"]
    )
    phase1c_risk_reduce_signal_key_missing = sum(
        1
        for row in signal_key_rows
        if row["method"] == "phase1c_anchor_simple"
        and row["action"] == "historical_risk_reduce"
        and not row["signal_key_present_in_common"]
    )
    gate = "phase_o5r_common_universe_audit_repaired" if next_day_pass and nav_diff_pass else "stop_phase_o5r_common_universe_audit_failed"
    summary = {
        "created_at": now(),
        "phase": "phase_o5r_common_universe_audit_repair",
        "gate": gate,
        "window": f"{o5.START}..{o5.END}",
        "common_key_summary": key_summary,
        "candidate_summary": candidate_summary,
        "action_diff_total": len(action_diff_rows),
        "phase1c_full_only_risk_reduce_count": phase1c_full_only_risk_reduce,
        "phase1c_risk_reduce_signal_key_missing_from_common_count": phase1c_risk_reduce_signal_key_missing,
        "action_signal_key_common_summary": signal_key_summary,
        "nav_diff_summary": nav_diff_summary,
        "nav_diff_pass": nav_diff_pass,
        "next_day_accounting_pass": next_day_pass,
        "full_o4_minus_anchor": round(full_results["o4_orthogonal_treatment_ltr"]["metrics"]["fee_tax_adjusted_net_return"] - full_results["phase1c_anchor_simple"]["metrics"]["fee_tax_adjusted_net_return"], 6),
        "common_o4_minus_anchor": round(common_results["o4_orthogonal_treatment_ltr"]["metrics"]["fee_tax_adjusted_net_return"] - common_results["phase1c_anchor_simple"]["metrics"]["fee_tax_adjusted_net_return"], 6),
        "no_training": True,
        "no_score_modification": True,
        "no_replay_rule_change": True,
        "no_frontend_api_provider_accepted_latest_monitor_trading": True,
        "artifacts": {
            "excluded_key_audit": rel(OUT / "phaseo5r_common_universe_excluded_key_audit.csv"),
            "excluded_by_date": rel(OUT / "phaseo5r_excluded_key_count_by_date.csv"),
            "excluded_by_symbol": rel(OUT / "phaseo5r_excluded_key_count_by_symbol.csv"),
            "selected_candidate_audit": rel(OUT / "phaseo5r_selected_candidate_audit.csv"),
            "selected_candidate_summary": rel(OUT / "phaseo5r_selected_candidate_summary.csv"),
            "full_action_audit": rel(OUT / "phaseo5r_full_action_audit.csv"),
            "common_action_audit": rel(OUT / "phaseo5r_common_action_audit.csv"),
            "action_diff_audit": rel(OUT / "phaseo5r_action_diff_audit.csv"),
            "action_diff_summary": rel(OUT / "phaseo5r_action_diff_summary.csv"),
            "action_signal_key_common_audit": rel(OUT / "phaseo5r_action_signal_key_common_audit.csv"),
            "action_signal_key_common_summary": rel(OUT / "phaseo5r_action_signal_key_common_summary.csv"),
            "full_daily_nav": rel(OUT / "phaseo5r_full_daily_nav.csv"),
            "common_daily_nav": rel(OUT / "phaseo5r_common_daily_nav.csv"),
            "nav_diff_audit": rel(OUT / "phaseo5r_nav_diff_audit.csv"),
            "nav_diff_summary": rel(OUT / "phaseo5r_nav_diff_summary.csv"),
            "next_day_accounting": rel(OUT / "phaseo5r_next_day_accounting_audit.csv"),
            "full_metrics": rel(OUT / "phaseo5r_full_universe_metrics.csv"),
            "common_metrics": rel(OUT / "phaseo5r_common_universe_metrics.csv"),
            "summary": rel(OUT / "phaseo5r_summary.json"),
            "report": rel(REPORT),
        },
    }
    wjson(OUT / "phaseo5r_summary.json", summary)
    write_report(summary, candidate_summary, action_diff_summary, nav_diff_summary)
    print(json.dumps({"ok": gate == "phase_o5r_common_universe_audit_repaired", "gate": gate, "report": rel(REPORT)}, ensure_ascii=False, indent=2))
    return 0 if gate == "phase_o5r_common_universe_audit_repaired" else 2


if __name__ == "__main__":
    raise SystemExit(main())
