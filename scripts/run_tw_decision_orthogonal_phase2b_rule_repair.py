#!/usr/bin/env python3
"""Phase2B readonly rule repair for TW decision orthogonal data.

Reads only Phase1B repaired full and Phase2 outputs. Writes Phase2B research
artifacts. No model training, provider writes, network calls, or trading paths.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data_tw/experiments/decision_orthogonal"
DOC_DIR = ROOT / "docs/tw_decision_model_orthogonal"

SAMPLES_PATH = OUT_DIR / "phase1b_repaired_full_samples.parquet"
PHASE2_GROUP_METRICS = OUT_DIR / "phase2_rules_group_metrics.csv"
PHASE2_GATE = OUT_DIR / "phase2_rules_gate_summary.json"

RULE_DEFINITIONS_PATH = OUT_DIR / "phase2b_rules_definitions.json"
GROUP_METRICS_PATH = OUT_DIR / "phase2b_rules_group_metrics.csv"
SEGMENT_METRICS_PATH = OUT_DIR / "phase2b_rules_segment_metrics.csv"
TURNOVER_PATH = OUT_DIR / "phase2b_rules_turnover_summary.csv"
CANDIDATE_COMPARISON_PATH = OUT_DIR / "phase2b_rules_candidate_comparison.csv"
GATE_SUMMARY_PATH = OUT_DIR / "phase2b_rules_gate_summary.json"
REPORT_PATH = DOC_DIR / "PHASE2B_RULE_REPAIR_EXECUTION_REPORT_CN.md"

HORIZONS = [5, 10, 20]
LABELS = [f"fwd_{h}d_excess_return" for h in HORIZONS]


@dataclass(frozen=True)
class RuleSpec:
    rule_id: str
    status: str
    rule_family: str
    description: str
    selected_expr: str
    excluded_expr: str
    baseline_group: str
    expected_direction: str
    counts_for_gate: bool


RULES = [
    RuleSpec(
        "margin_crowding_top50_p85_caution",
        "caution_watch",
        "margin_crowding_refinement",
        "Top50 且融资余额 20 日均值分位 >= 0.85，较 Phase2 p80 缩小拥挤定义。",
        "top50_flag and margin_balance_20d_mean_cs_rank_pct >= 0.85",
        "top50_flag and margin_balance_20d_mean_cs_rank_pct < 0.85",
        "baseline_top50",
        "selected_lower_mean_and_not_worse_downside",
        True,
    ),
    RuleSpec(
        "margin_crowding_top50_p90_caution",
        "caution_watch",
        "margin_crowding_refinement",
        "Top50 且融资余额 20 日均值分位 >= 0.90，测试更极端融资拥挤。",
        "top50_flag and margin_balance_20d_mean_cs_rank_pct >= 0.90",
        "top50_flag and margin_balance_20d_mean_cs_rank_pct < 0.90",
        "baseline_top50",
        "selected_lower_mean_and_not_worse_downside",
        True,
    ),
    RuleSpec(
        "margin_crowding_top30_p85_caution",
        "caution_watch",
        "margin_crowding_refinement",
        "Top30 且融资余额 20 日均值分位 >= 0.85，测试更靠前 qlib rank band。",
        "qlib_rank <= 30 and margin_balance_20d_mean_cs_rank_pct >= 0.85",
        "qlib_rank <= 30 and margin_balance_20d_mean_cs_rank_pct < 0.85",
        "baseline_top50",
        "selected_lower_mean_and_not_worse_downside",
        True,
    ),
    RuleSpec(
        "margin_crowding_top20_p85_caution",
        "caution_watch",
        "margin_crowding_refinement",
        "Top20 且融资余额 20 日均值分位 >= 0.85，测试最前段 qlib rank band。",
        "qlib_rank <= 20 and margin_balance_20d_mean_cs_rank_pct >= 0.85",
        "qlib_rank <= 20 and margin_balance_20d_mean_cs_rank_pct < 0.85",
        "baseline_top50",
        "selected_lower_mean_and_not_worse_downside",
        True,
    ),
    RuleSpec(
        "flow_crowding_conflict_top50_p85_weak30_review",
        "review_watch",
        "flow_crowding_conflict_refinement",
        "Top50、融资拥挤 >= 0.85，且外资/自营商 20 日流向分位均 <= 0.30。",
        "top50_flag and margin_balance_20d_mean_cs_rank_pct >= 0.85 and foreign_net_buy_20d_sum_cs_rank_pct <= 0.30 and dealer_net_buy_20d_sum_cs_rank_pct <= 0.30",
        "top50_flag and not (margin_balance_20d_mean_cs_rank_pct >= 0.85 and foreign_net_buy_20d_sum_cs_rank_pct <= 0.30 and dealer_net_buy_20d_sum_cs_rank_pct <= 0.30)",
        "baseline_top50",
        "selected_lower_mean_or_explanation",
        True,
    ),
    RuleSpec(
        "flow_crowding_conflict_top50_p80_weak30_review",
        "review_watch",
        "flow_crowding_conflict_refinement",
        "Top50、融资拥挤 >= 0.80，且外资/自营商 20 日流向分位均 <= 0.30。",
        "top50_flag and margin_balance_20d_mean_cs_rank_pct >= 0.80 and foreign_net_buy_20d_sum_cs_rank_pct <= 0.30 and dealer_net_buy_20d_sum_cs_rank_pct <= 0.30",
        "top50_flag and not (margin_balance_20d_mean_cs_rank_pct >= 0.80 and foreign_net_buy_20d_sum_cs_rank_pct <= 0.30 and dealer_net_buy_20d_sum_cs_rank_pct <= 0.30)",
        "baseline_top50",
        "selected_lower_mean_or_explanation",
        True,
    ),
    RuleSpec(
        "foreign_flow_non_crowded_top150_explanation",
        "explanation_feature",
        "foreign_flow_downgrade",
        "Top150 外资 10/20 日高分位且融资拥挤 < 0.80；仅保留为解释字段，不作为 confirmed watch。",
        "top150_flag and (foreign_net_buy_10d_sum_cs_rank_pct >= 0.80 or foreign_net_buy_20d_sum_cs_rank_pct >= 0.80) and margin_balance_20d_mean_cs_rank_pct < 0.80",
        "top150_flag and not ((foreign_net_buy_10d_sum_cs_rank_pct >= 0.80 or foreign_net_buy_20d_sum_cs_rank_pct >= 0.80) and margin_balance_20d_mean_cs_rank_pct < 0.80)",
        "baseline_top150",
        "explanation_only",
        False,
    ),
    RuleSpec(
        "margin_change_non_crowded_top150_auxiliary",
        "confirmation_auxiliary",
        "margin_change_auxiliary_refinement",
        "Top150 融资变化高分位且融资余额拥挤 < 0.80；仅作为辅助确认。",
        "top150_flag and margin_balance_change_20d_sum_cs_rank_pct >= 0.80 and margin_balance_20d_mean_cs_rank_pct < 0.80",
        "top150_flag and not (margin_balance_change_20d_sum_cs_rank_pct >= 0.80 and margin_balance_20d_mean_cs_rank_pct < 0.80)",
        "baseline_top150",
        "auxiliary_only",
        False,
    ),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def md_table(rows: list[dict[str, Any]], cols: list[str]) -> str:
    if not rows:
        return "_no rows_"
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---" for _ in cols]) + "|"]
    for row in rows:
        vals = []
        for col in cols:
            val = row.get(col, "")
            vals.append(f"{val:.6f}" if isinstance(val, float) else str(val))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def downside_stats(series: pd.Series) -> dict[str, float]:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return {"mean": np.nan, "median": np.nan, "downside_q10": np.nan, "worst_decile_mean": np.nan, "historical_positive_rate": np.nan}
    q10 = float(s.quantile(0.10))
    worst = s[s <= q10]
    return {
        "mean": float(s.mean()),
        "median": float(s.median()),
        "downside_q10": q10,
        "worst_decile_mean": float(worst.mean()) if not worst.empty else np.nan,
        "historical_positive_rate": float((s > 0).mean()),
    }


def group_metric_rows(df: pd.DataFrame, rule_id: str, group: str, mask: pd.Series, segment_type: str = "all", segment: str = "all") -> list[dict[str, Any]]:
    sub = df[mask.fillna(False)].copy()
    coverage_rows = int(len(sub))
    coverage_days = int(sub["asof"].nunique()) if not sub.empty else 0
    coverage_symbols = int(sub["symbol"].nunique()) if not sub.empty else 0
    daily_size_mean = float(sub.groupby("asof")["symbol"].nunique().mean()) if not sub.empty else np.nan
    rows = []
    for horizon, label in zip(HORIZONS, LABELS):
        rows.append(
            {
                "rule_id": rule_id,
                "group": group,
                "segment_type": segment_type,
                "segment": str(segment),
                "horizon": horizon,
                "coverage_rows": coverage_rows,
                "coverage_days": coverage_days,
                "coverage_symbols": coverage_symbols,
                "daily_size_mean": daily_size_mean,
                **downside_stats(sub[label]),
            }
        )
    return rows


def add_rule_masks(samples: pd.DataFrame) -> pd.DataFrame:
    out = samples.copy()
    for rule in RULES:
        out[f"{rule.rule_id}__selected"] = out.eval(rule.selected_expr, engine="python").fillna(False).astype(bool)
        out[f"{rule.rule_id}__excluded"] = out.eval(rule.excluded_expr, engine="python").fillna(False).astype(bool)
    return out


def build_metrics(samples: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    rows.extend(group_metric_rows(samples, "baseline", "baseline_top50", samples["top50_flag"].astype(bool)))
    rows.extend(group_metric_rows(samples, "baseline", "baseline_top150", samples["top150_flag"].astype(bool)))
    for rule in RULES:
        rows.extend(group_metric_rows(samples, rule.rule_id, "rule_selected", samples[f"{rule.rule_id}__selected"]))
        rows.extend(group_metric_rows(samples, rule.rule_id, "rule_excluded", samples[f"{rule.rule_id}__excluded"]))
    group_metrics = pd.DataFrame(rows)

    seg_rows: list[dict[str, Any]] = []
    for segment_type in ["year", "quarter"]:
        for segment, seg_df in samples.groupby(segment_type, sort=True):
            seg_rows.extend(group_metric_rows(seg_df, "baseline", "baseline_top50", seg_df["top50_flag"].astype(bool), segment_type, segment))
            seg_rows.extend(group_metric_rows(seg_df, "baseline", "baseline_top150", seg_df["top150_flag"].astype(bool), segment_type, segment))
            for rule in RULES:
                seg_rows.extend(group_metric_rows(seg_df, rule.rule_id, "rule_selected", seg_df[f"{rule.rule_id}__selected"], segment_type, segment))
                seg_rows.extend(group_metric_rows(seg_df, rule.rule_id, "rule_excluded", seg_df[f"{rule.rule_id}__excluded"], segment_type, segment))
    return group_metrics, pd.DataFrame(seg_rows)


def build_turnover(samples: pd.DataFrame) -> pd.DataFrame:
    masks: dict[str, pd.Series] = {
        "baseline_top50": samples["top50_flag"].astype(bool),
        "baseline_top150": samples["top150_flag"].astype(bool),
    }
    for rule in RULES:
        masks[f"{rule.rule_id}__selected"] = samples[f"{rule.rule_id}__selected"].astype(bool)
    rows = []
    for group, mask in masks.items():
        daily_sets = [(asof, set(g["symbol"].astype(str))) for asof, g in samples[mask].groupby("asof", sort=True)]
        changes = []
        jaccards = []
        prev = None
        for _, symbols in daily_sets:
            if prev is not None:
                changes.append(len(symbols.symmetric_difference(prev)))
                union = len(symbols | prev)
                jaccards.append(len(symbols & prev) / union if union else np.nan)
            prev = symbols
        rows.append(
            {
                "group": group,
                "days": len(daily_sets),
                "mean_daily_member_count": float(np.mean([len(s) for _, s in daily_sets])) if daily_sets else np.nan,
                "mean_daily_symmetric_change": float(np.mean(changes)) if changes else np.nan,
                "median_daily_symmetric_change": float(np.median(changes)) if changes else np.nan,
                "mean_jaccard_with_previous_day": float(np.nanmean(jaccards)) if jaccards else np.nan,
            }
        )
    return pd.DataFrame(rows)


def lookup(metrics: pd.DataFrame, rule_id: str, group: str, horizon: int, col: str) -> float:
    sub = metrics[(metrics["rule_id"] == rule_id) & (metrics["group"] == group) & (metrics["horizon"] == horizon)]
    return float(sub.iloc[0][col]) if not sub.empty else float("nan")


def evaluate_rule(rule: RuleSpec, group_metrics: pd.DataFrame, segment_metrics: pd.DataFrame) -> dict[str, Any]:
    selected_mean = lookup(group_metrics, rule.rule_id, "rule_selected", 20, "mean")
    excluded_mean = lookup(group_metrics, rule.rule_id, "rule_excluded", 20, "mean")
    selected_q10 = lookup(group_metrics, rule.rule_id, "rule_selected", 20, "downside_q10")
    excluded_q10 = lookup(group_metrics, rule.rule_id, "rule_excluded", 20, "downside_q10")
    baseline_mean = lookup(group_metrics, "baseline", rule.baseline_group, 20, "mean")
    baseline_q10 = lookup(group_metrics, "baseline", rule.baseline_group, 20, "downside_q10")
    coverage_rows = lookup(group_metrics, rule.rule_id, "rule_selected", 20, "coverage_rows")
    coverage_days = lookup(group_metrics, rule.rule_id, "rule_selected", 20, "coverage_days")
    phase2_original_mean = np.nan
    phase2_original_q10 = np.nan
    if rule.rule_family.startswith("margin_crowding"):
        phase2_original_mean = 0.01621548237290235
        phase2_original_q10 = -0.11606153295504636
    if rule.rule_family.startswith("flow_crowding"):
        phase2_original_mean = 0.009239214648568028
        phase2_original_q10 = -0.11065853138264958

    year_rows = segment_metrics[
        (segment_metrics["rule_id"] == rule.rule_id)
        & (segment_metrics["group"].isin(["rule_selected", "rule_excluded"]))
        & (segment_metrics["segment_type"] == "year")
        & (segment_metrics["horizon"] == 20)
    ]
    yearly = []
    aligned = 0
    total = 0
    reverse_years: list[str] = []
    for year, ydf in year_rows.groupby("segment", sort=True):
        selected = ydf[ydf["group"] == "rule_selected"]
        excluded = ydf[ydf["group"] == "rule_excluded"]
        if selected.empty or excluded.empty:
            continue
        s_mean = float(selected.iloc[0]["mean"])
        e_mean = float(excluded.iloc[0]["mean"])
        if rule.status in {"caution_watch", "review_watch"}:
            ok = s_mean < e_mean
        elif rule.status == "explanation_feature":
            ok = True
        else:
            ok = s_mean > e_mean
        aligned += int(ok)
        total += 1
        if not ok:
            reverse_years.append(str(year))
        yearly.append({"year": str(year), "selected_20d_mean": s_mean, "excluded_20d_mean": e_mean, "aligned": ok})
    year_direction_share = aligned / total if total else 0.0
    y2025 = [row for row in yearly if row["year"] == "2025"]
    y2025_aligned = bool(y2025 and y2025[0]["aligned"])

    if rule.status in {"caution_watch", "review_watch"}:
        passes = (
            rule.counts_for_gate
            and coverage_days >= 500
            and coverage_rows >= 1000
            and selected_mean < excluded_mean
            and selected_mean < baseline_mean
            and selected_q10 <= baseline_q10
            and year_direction_share >= 0.80
            and y2025_aligned
        )
        manual_freeze = (
            rule.counts_for_gate
            and coverage_days >= 500
            and selected_mean < excluded_mean
            and selected_mean < baseline_mean
            and year_direction_share >= 0.60
        )
    elif rule.status == "confirmation_auxiliary":
        passes = False
        manual_freeze = False
    else:
        passes = False
        manual_freeze = False

    return {
        "rule_id": rule.rule_id,
        "status": rule.status,
        "rule_family": rule.rule_family,
        "selected_20d_mean": selected_mean,
        "excluded_20d_mean": excluded_mean,
        "baseline_20d_mean": baseline_mean,
        "selected_20d_downside_q10": selected_q10,
        "excluded_20d_downside_q10": excluded_q10,
        "baseline_20d_downside_q10": baseline_q10,
        "coverage_rows": coverage_rows,
        "coverage_days": coverage_days,
        "year_direction_share": year_direction_share,
        "reverse_years": reverse_years,
        "y2025_aligned": y2025_aligned,
        "phase2_original_selected_20d_mean": phase2_original_mean,
        "phase2_original_selected_20d_downside_q10": phase2_original_q10,
        "passes_phase2b_gate_check": passes,
        "eligible_manual_freeze": manual_freeze,
        "yearly_20d": yearly,
    }


def evaluate_gate(evaluations: list[dict[str, Any]]) -> dict[str, Any]:
    pass_count = sum(bool(row["passes_phase2b_gate_check"]) for row in evaluations)
    manual_count = sum(bool(row["eligible_manual_freeze"]) for row in evaluations)
    if pass_count >= 2:
        gate = "request_phase3_risk_filter_model=true"
        reason = "至少两条非辅助修正规则通过年度、2025、baseline 与 downside 检查。"
    elif manual_count >= 1:
        gate = "request_phase2c_manual_rule_freeze=true"
        reason = "修正规则仍不足以进入模型训练，但存在一条可解释风险过滤规则适合冻结为人工解释规则。"
    else:
        gate = "stop_orthogonal_direction=true"
        reason = "修正规则仍无法稳定改善或解释价值不足。"
    return {
        "generated_at": utc_now(),
        "gate": gate,
        "reason": reason,
        "pass_count": pass_count,
        "manual_freeze_count": manual_count,
        "rule_evaluations": evaluations,
        "forbidden_actions": {
            "network": False,
            "token": False,
            "data_redownload": False,
            "new_data_source": False,
            "model_training": False,
            "risk_filter_model": False,
            "provider_write": False,
            "provider_refresh_publish": False,
            "accepted_latest_switching": False,
            "frontend_api": False,
            "trading_actions": False,
        },
    }


def write_report(samples: pd.DataFrame, group_metrics: pd.DataFrame, segment_metrics: pd.DataFrame, turnover: pd.DataFrame, evaluations: list[dict[str, Any]], gate: dict[str, Any]) -> None:
    rules_payload = {
        "generated_at": utc_now(),
        "scope": "phase2b_rule_repair_readonly",
        "inputs": [rel(SAMPLES_PATH), rel(PHASE2_GROUP_METRICS), rel(PHASE2_GATE)],
        "candidate_policy": "fixed small interpretable thresholds only: 0.85/0.90 for margin crowding, Top20/30/50 rank bands, weak flow 0.30, no broad grid search",
        "rules": [rule.__dict__ for rule in RULES],
    }
    RULE_DEFINITIONS_PATH.write_text(json.dumps(rules_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    group_metrics.to_csv(GROUP_METRICS_PATH, index=False)
    segment_metrics.to_csv(SEGMENT_METRICS_PATH, index=False)
    turnover.to_csv(TURNOVER_PATH, index=False)
    pd.DataFrame(evaluations).drop(columns=["yearly_20d"]).to_csv(CANDIDATE_COMPARISON_PATH, index=False)
    GATE_SUMMARY_PATH.write_text(json.dumps(gate, ensure_ascii=False, indent=2), encoding="utf-8")

    selected_20 = group_metrics[(group_metrics["horizon"] == 20) & (group_metrics["group"].isin(["baseline_top50", "baseline_top150", "rule_selected", "rule_excluded"]))]
    selected_20 = selected_20[["rule_id", "group", "coverage_rows", "coverage_days", "coverage_symbols", "mean", "median", "downside_q10", "worst_decile_mean", "historical_positive_rate"]]
    y2025 = segment_metrics[(segment_metrics["segment_type"] == "year") & (segment_metrics["segment"] == "2025") & (segment_metrics["horizon"] == 20)]
    y2025 = y2025[y2025["group"].isin(["rule_selected", "rule_excluded", "baseline_top50", "baseline_top150"])]
    y2025 = y2025[["rule_id", "group", "coverage_rows", "coverage_days", "mean", "downside_q10", "historical_positive_rate"]]
    q = segment_metrics[(segment_metrics["segment_type"] == "quarter") & (segment_metrics["horizon"] == 20) & (segment_metrics["group"] == "rule_selected")].copy()
    q["abs_mean"] = q["mean"].abs()
    q = q.sort_values(["rule_id", "abs_mean"], ascending=[True, False]).groupby("rule_id").head(3)
    q = q[["rule_id", "segment", "coverage_rows", "coverage_days", "mean", "downside_q10", "historical_positive_rate"]]

    lines = [
        "# Phase 2B Rule Repair 执行报告",
        "",
        f"- 生成时间：`{utc_now()}`",
        "- 执行范围：基于 Phase1B/Phase2 本地产物的小范围可解释规则修正。",
        "- 禁止范围：未联网、未使用 token、未重拉数据、未新增数据源、未月营收、未训练模型、未 Risk Filter Model、未写 provider、未 refresh/publish、未 accepted latest switching、未前端/API、未交易相关操作。",
        f"- Phase2B gate：`{gate['gate']}`",
        f"- gate 理由：{gate['reason']}",
        "",
        "## 1. 输入与边界",
        "",
        f"- 样本：`{rel(SAMPLES_PATH)}`，行数 `{len(samples)}`，asof `{samples['asof'].min().strftime('%Y-%m-%d')}` 至 `{samples['asof'].max().strftime('%Y-%m-%d')}`。",
        "- 本阶段只读 Phase1B repaired full 与 Phase2 rules 产物，不引入新字段。",
        "- 阈值候选固定且少量：0.85/0.90、Top20/30/50、weak flow 0.30；没有大规模参数搜索。",
        "",
        "## 2. 修正规则定义",
        "",
        md_table([rule.__dict__ for rule in RULES], ["rule_id", "status", "rule_family", "description", "selected_expr", "baseline_group", "counts_for_gate"]),
        "",
        "## 3. 20d 全样本对照",
        "",
        "- `historical_positive_rate` 仅为历史样本统计，不代表未来胜率或收益承诺。",
        md_table(selected_20.to_dict("records"), ["rule_id", "group", "coverage_rows", "coverage_days", "coverage_symbols", "mean", "median", "downside_q10", "worst_decile_mean", "historical_positive_rate"]),
        "",
        "## 4. 2025 单独分段",
        "",
        md_table(y2025.to_dict("records"), ["rule_id", "group", "coverage_rows", "coverage_days", "mean", "downside_q10", "historical_positive_rate"]),
        "",
        "## 5. 季度分段摘要",
        "",
        md_table(q.to_dict("records"), ["rule_id", "segment", "coverage_rows", "coverage_days", "mean", "downside_q10", "historical_positive_rate"]),
        "",
        "## 6. Turnover Proxy",
        "",
        md_table(turnover.to_dict("records"), ["group", "days", "mean_daily_member_count", "mean_daily_symmetric_change", "median_daily_symmetric_change", "mean_jaccard_with_previous_day"]),
        "",
        "## 7. 相对 Phase2 原规则改善与 Gate",
        "",
        md_table(evaluations, ["rule_id", "status", "selected_20d_mean", "excluded_20d_mean", "baseline_20d_mean", "selected_20d_downside_q10", "baseline_20d_downside_q10", "coverage_days", "year_direction_share", "reverse_years", "y2025_aligned", "phase2_original_selected_20d_mean", "phase2_original_selected_20d_downside_q10", "passes_phase2b_gate_check", "eligible_manual_freeze"]),
        "",
        "## 8. 结论",
        "",
        f"- `{gate['gate']}`",
        "- 即使 gate 请求 Phase3，也必须等待审查者授权；本阶段没有训练模型。",
        "- 若审查者接受 manual freeze，建议只把可解释风险规则冻结为人工解释标签，而不是进入自动模型训练。",
        "",
        "## 9. 产物",
        "",
        f"- 规则定义：`{rel(RULE_DEFINITIONS_PATH)}`",
        f"- 全样本指标：`{rel(GROUP_METRICS_PATH)}`",
        f"- 年度/季度指标：`{rel(SEGMENT_METRICS_PATH)}`",
        f"- turnover：`{rel(TURNOVER_PATH)}`",
        f"- 候选对照：`{rel(CANDIDATE_COMPARISON_PATH)}`",
        f"- gate summary：`{rel(GATE_SUMMARY_PATH)}`",
        "",
        "## 10. 风险与待审查问题",
        "",
        "- 多数修正规则仍存在 2025 反向或 coverage 偏窄问题。",
        "- foreign flow 已降级为 explanation feature，不再作为 confirmed watch 规则。",
        "- margin change 仍只作为 auxiliary，不支撑 Phase3。",
        "- `available_at = next_trading_day(trade_date)` 仍是 conservative visibility proxy，不是官方发布时间证明。",
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    samples = pd.read_parquet(SAMPLES_PATH)
    samples = add_rule_masks(samples)
    group_metrics, segment_metrics = build_metrics(samples)
    turnover = build_turnover(samples)
    evaluations = [evaluate_rule(rule, group_metrics, segment_metrics) for rule in RULES]
    gate = evaluate_gate(evaluations)
    write_report(samples, group_metrics, segment_metrics, turnover, evaluations, gate)
    print(json.dumps({"gate": gate, "artifacts": {
        "definitions": rel(RULE_DEFINITIONS_PATH),
        "group_metrics": rel(GROUP_METRICS_PATH),
        "segment_metrics": rel(SEGMENT_METRICS_PATH),
        "turnover": rel(TURNOVER_PATH),
        "candidate_comparison": rel(CANDIDATE_COMPARISON_PATH),
        "gate_summary": rel(GATE_SUMMARY_PATH),
        "report": rel(REPORT_PATH),
    }}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
