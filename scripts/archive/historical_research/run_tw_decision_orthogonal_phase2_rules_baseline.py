#!/usr/bin/env python3
"""Phase2 readonly rules baseline for TW decision orthogonal data.

This script only reads repaired Phase1B outputs and writes Phase2 research
artifacts. It does not train models, refresh/publish providers, switch accepted
latest, call networks, or touch trading paths.
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
FACTOR_METRICS_PATH = OUT_DIR / "phase1b_repaired_full_factor_metrics.csv"
SEGMENT_METRICS_PATH = OUT_DIR / "phase1b_repaired_full_segment_metrics.csv"
SCHEMA_PATH = OUT_DIR / "phase1b_repaired_full_schema.json"
REPAIR_SUMMARY_PATH = OUT_DIR / "phase1b_asof_aware_prediction_repair_summary.json"

RULE_DEFINITIONS_PATH = OUT_DIR / "phase2_rules_definitions.json"
GROUP_METRICS_PATH = OUT_DIR / "phase2_rules_group_metrics.csv"
SEGMENT_RULE_METRICS_PATH = OUT_DIR / "phase2_rules_segment_metrics.csv"
DAILY_MEMBERSHIP_PATH = OUT_DIR / "phase2_rules_daily_membership.csv"
TURNOVER_PATH = OUT_DIR / "phase2_rules_turnover_summary.csv"
GATE_SUMMARY_PATH = OUT_DIR / "phase2_rules_gate_summary.json"
REPORT_PATH = DOC_DIR / "PHASE2_RULES_BASELINE_EXECUTION_REPORT_CN.md"

HORIZONS = [5, 10, 20]
LABELS = [f"fwd_{horizon}d_excess_return" for horizon in HORIZONS]
BASELINE_GROUPS = {
    "baseline_top50": "top50_flag",
    "baseline_top150": "top150_flag",
}


@dataclass(frozen=True)
class RuleSpec:
    rule_id: str
    status: str
    scope: str
    description: str
    selected_expr: str
    excluded_expr: str
    expected_direction: str


RULES = [
    RuleSpec(
        rule_id="margin_crowding_caution_top50",
        status="caution_watch",
        scope="qlib Top50",
        description="qlib Top50 且融资余额 20 日均值处于当日横截面高分位，识别融资拥挤风险。",
        selected_expr="top50_flag and margin_balance_20d_mean_cs_rank_pct >= 0.80",
        excluded_expr="top50_flag and margin_balance_20d_mean_cs_rank_pct < 0.80",
        expected_direction="risk_selected_underperforms_excluded_or_top50",
    ),
    RuleSpec(
        rule_id="margin_change_confirmation_top150",
        status="confirmation_auxiliary",
        scope="qlib Top150",
        description="qlib Top150 且融资余额 20 日变化处于高分位，仅作为辅助确认，不单独形成强结论。",
        selected_expr="top150_flag and margin_balance_change_20d_sum_cs_rank_pct >= 0.80",
        excluded_expr="top150_flag and margin_balance_change_20d_sum_cs_rank_pct < 0.80",
        expected_direction="selected_improves_or_neutral_auxiliary",
    ),
    RuleSpec(
        rule_id="foreign_flow_confirmed_candidate_top150",
        status="confirmed_watch_candidate",
        scope="qlib Top150",
        description="qlib Top150 且外资 10/20 日连续买超分位较高，作为多源确认候选，不是买入建议。",
        selected_expr="top150_flag and (foreign_net_buy_10d_sum_cs_rank_pct >= 0.80 or foreign_net_buy_20d_sum_cs_rank_pct >= 0.80)",
        excluded_expr="top150_flag and not (foreign_net_buy_10d_sum_cs_rank_pct >= 0.80 or foreign_net_buy_20d_sum_cs_rank_pct >= 0.80)",
        expected_direction="selected_improves_top_bucket",
    ),
    RuleSpec(
        rule_id="flow_crowding_conflict_top50",
        status="review_watch",
        scope="qlib Top50",
        description="qlib Top50 但融资拥挤较高，同时外资和自营商 20 日流向偏弱，识别法人/融资冲突。",
        selected_expr="top50_flag and margin_balance_20d_mean_cs_rank_pct >= 0.80 and foreign_net_buy_20d_sum_cs_rank_pct <= 0.40 and dealer_net_buy_20d_sum_cs_rank_pct <= 0.40",
        excluded_expr="top50_flag and not (margin_balance_20d_mean_cs_rank_pct >= 0.80 and foreign_net_buy_20d_sum_cs_rank_pct <= 0.40 and dealer_net_buy_20d_sum_cs_rank_pct <= 0.40)",
        expected_direction="risk_selected_underperforms_excluded_or_top50",
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
        values = []
        for col in cols:
            val = row.get(col, "")
            if isinstance(val, float):
                values.append(f"{val:.6f}")
            else:
                values.append(str(val))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def load_inputs() -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    samples = pd.read_parquet(SAMPLES_PATH)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    factor_metrics = pd.read_csv(FACTOR_METRICS_PATH)
    segment_metrics = pd.read_csv(SEGMENT_METRICS_PATH)
    repair_summary = json.loads(REPAIR_SUMMARY_PATH.read_text(encoding="utf-8"))
    return samples, schema, factor_metrics, segment_metrics, repair_summary


def add_rule_masks(samples: pd.DataFrame) -> pd.DataFrame:
    out = samples.copy()
    for rule in RULES:
        out[f"{rule.rule_id}__selected"] = out.eval(rule.selected_expr, engine="python").fillna(False).astype(bool)
        out[f"{rule.rule_id}__excluded"] = out.eval(rule.excluded_expr, engine="python").fillna(False).astype(bool)
    return out


def downside_stats(series: pd.Series) -> dict[str, float]:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return {
            "mean": np.nan,
            "median": np.nan,
            "downside_q10": np.nan,
            "worst_decile_mean": np.nan,
            "historical_positive_rate": np.nan,
        }
    q10 = float(s.quantile(0.10))
    worst = s[s <= q10]
    return {
        "mean": float(s.mean()),
        "median": float(s.median()),
        "downside_q10": q10,
        "worst_decile_mean": float(worst.mean()) if not worst.empty else np.nan,
        "historical_positive_rate": float((s > 0).mean()),
    }


def group_metric_rows(df: pd.DataFrame, group_name: str, mask: pd.Series, *, rule_id: str = "baseline", segment_type: str = "all", segment: str = "all") -> list[dict[str, Any]]:
    sub = df[mask.fillna(False)].copy()
    rows: list[dict[str, Any]] = []
    coverage_rows = int(len(sub))
    coverage_days = int(sub["asof"].nunique()) if not sub.empty else 0
    coverage_symbols = int(sub["symbol"].nunique()) if not sub.empty else 0
    daily_size_mean = float(sub.groupby("asof")["symbol"].nunique().mean()) if not sub.empty else np.nan
    for horizon, label in zip(HORIZONS, LABELS):
        stats = downside_stats(sub[label]) if label in sub.columns else downside_stats(pd.Series(dtype=float))
        rows.append(
            {
                "rule_id": rule_id,
                "group": group_name,
                "segment_type": segment_type,
                "segment": str(segment),
                "horizon": horizon,
                "coverage_rows": coverage_rows,
                "coverage_days": coverage_days,
                "coverage_symbols": coverage_symbols,
                "daily_size_mean": daily_size_mean,
                **stats,
            }
        )
    return rows


def daily_membership_rows(samples: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    turnover_rows: list[dict[str, Any]] = []
    group_masks: dict[str, pd.Series] = {
        "baseline_top50": samples["top50_flag"].astype(bool),
        "baseline_top150": samples["top150_flag"].astype(bool),
    }
    for rule in RULES:
        group_masks[f"{rule.rule_id}__selected"] = samples[f"{rule.rule_id}__selected"].astype(bool)
        group_masks[f"{rule.rule_id}__excluded"] = samples[f"{rule.rule_id}__excluded"].astype(bool)

    for group, mask in group_masks.items():
        daily_sets: list[tuple[pd.Timestamp, set[str]]] = []
        for asof, g in samples[mask].groupby("asof", sort=True):
            symbols = set(g["symbol"].astype(str))
            daily_sets.append((asof, symbols))
            rows.append({"group": group, "asof": asof.strftime("%Y-%m-%d"), "member_count": len(symbols)})
        changes = []
        jaccards = []
        prev: set[str] | None = None
        for _, symbols in daily_sets:
            if prev is not None:
                changes.append(len(symbols.symmetric_difference(prev)))
                union = len(symbols | prev)
                jaccards.append(len(symbols & prev) / union if union else np.nan)
            prev = symbols
        turnover_rows.append(
            {
                "group": group,
                "days": len(daily_sets),
                "mean_daily_member_count": float(np.mean([len(s) for _, s in daily_sets])) if daily_sets else np.nan,
                "mean_daily_symmetric_change": float(np.mean(changes)) if changes else np.nan,
                "median_daily_symmetric_change": float(np.median(changes)) if changes else np.nan,
                "mean_jaccard_with_previous_day": float(np.nanmean(jaccards)) if jaccards else np.nan,
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(turnover_rows)


def build_metrics(samples: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    for group, col in BASELINE_GROUPS.items():
        rows.extend(group_metric_rows(samples, group, samples[col].astype(bool)))
    for rule in RULES:
        rows.extend(group_metric_rows(samples, "rule_selected", samples[f"{rule.rule_id}__selected"], rule_id=rule.rule_id))
        rows.extend(group_metric_rows(samples, "rule_excluded", samples[f"{rule.rule_id}__excluded"], rule_id=rule.rule_id))
    group_metrics = pd.DataFrame(rows)

    seg_rows: list[dict[str, Any]] = []
    for segment_type in ["year", "quarter"]:
        for segment, seg_df in samples.groupby(segment_type, sort=True):
            for group, col in BASELINE_GROUPS.items():
                seg_rows.extend(group_metric_rows(seg_df, group, seg_df[col].astype(bool), segment_type=segment_type, segment=segment))
            for rule in RULES:
                seg_rows.extend(group_metric_rows(seg_df, "rule_selected", seg_df[f"{rule.rule_id}__selected"], rule_id=rule.rule_id, segment_type=segment_type, segment=segment))
                seg_rows.extend(group_metric_rows(seg_df, "rule_excluded", seg_df[f"{rule.rule_id}__excluded"], rule_id=rule.rule_id, segment_type=segment_type, segment=segment))
    segment_rule_metrics = pd.DataFrame(seg_rows)
    daily, turnover = daily_membership_rows(samples)
    return group_metrics, segment_rule_metrics, daily, turnover


def metric_lookup(metrics: pd.DataFrame, rule_id: str, group: str, horizon: int, column: str) -> float:
    sub = metrics[(metrics["rule_id"] == rule_id) & (metrics["group"] == group) & (metrics["horizon"] == horizon)]
    if sub.empty:
        return float("nan")
    return float(sub.iloc[0][column])


def evaluate_gate(group_metrics: pd.DataFrame, segment_metrics: pd.DataFrame) -> dict[str, Any]:
    rule_evaluations = []
    stable_primary_rule_count = 0
    baseline_top50_mean = metric_lookup(group_metrics, "baseline", "baseline_top50", 20, "mean")
    baseline_top150_mean = metric_lookup(group_metrics, "baseline", "baseline_top150", 20, "mean")
    baseline_top50_q10 = metric_lookup(group_metrics, "baseline", "baseline_top50", 20, "downside_q10")
    baseline_top150_q10 = metric_lookup(group_metrics, "baseline", "baseline_top150", 20, "downside_q10")
    for rule in RULES:
        selected_20 = metric_lookup(group_metrics, rule.rule_id, "rule_selected", 20, "mean")
        excluded_20 = metric_lookup(group_metrics, rule.rule_id, "rule_excluded", 20, "mean")
        selected_q10 = metric_lookup(group_metrics, rule.rule_id, "rule_selected", 20, "downside_q10")
        excluded_q10 = metric_lookup(group_metrics, rule.rule_id, "rule_excluded", 20, "downside_q10")
        coverage_days = metric_lookup(group_metrics, rule.rule_id, "rule_selected", 20, "coverage_days")
        baseline_mean = baseline_top50_mean if "Top50" in rule.scope else baseline_top150_mean
        baseline_q10 = baseline_top50_q10 if "Top50" in rule.scope else baseline_top150_q10
        year_rows = segment_metrics[
            (segment_metrics["rule_id"] == rule.rule_id)
            & (segment_metrics["group"].isin(["rule_selected", "rule_excluded"]))
            & (segment_metrics["segment_type"] == "year")
            & (segment_metrics["horizon"] == 20)
        ]
        yearly: list[dict[str, Any]] = []
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
            total += 1
            if rule.status in {"caution_watch", "review_watch"}:
                ok = s_mean < e_mean
            else:
                ok = s_mean > e_mean
            aligned += int(ok)
            if not ok:
                reverse_years.append(str(year))
            yearly.append({"year": str(year), "selected_20d_mean": s_mean, "excluded_20d_mean": e_mean, "aligned": ok})
        same_direction_share = aligned / total if total else 0.0
        if rule.status in {"caution_watch", "review_watch"}:
            useful = selected_20 < excluded_20 and selected_20 < baseline_mean and selected_q10 <= baseline_q10 and same_direction_share >= 0.60 and coverage_days >= 100
        elif rule.status == "confirmed_watch_candidate":
            useful = selected_20 > excluded_20 and selected_20 > baseline_mean and same_direction_share >= 0.60 and coverage_days >= 100
        else:
            useful = selected_20 > excluded_20 and same_direction_share >= 0.60 and coverage_days >= 100
        primary_rule = rule.status in {"caution_watch", "review_watch", "confirmed_watch_candidate"}
        stable_primary_rule_count += int(useful and primary_rule)
        rule_evaluations.append(
            {
                "rule_id": rule.rule_id,
                "status": rule.status,
                "expected_direction": rule.expected_direction,
                "selected_20d_mean": selected_20,
                "excluded_20d_mean": excluded_20,
                "baseline_20d_mean": baseline_mean,
                "selected_20d_downside_q10": selected_q10,
                "excluded_20d_downside_q10": excluded_q10,
                "baseline_20d_downside_q10": baseline_q10,
                "coverage_days": coverage_days,
                "year_direction_share": same_direction_share,
                "reverse_years": reverse_years,
                "yearly_20d": yearly,
                "passes_rule_baseline_check": useful,
                "counts_for_phase3_gate": bool(useful and primary_rule),
            }
        )

    if stable_primary_rule_count >= 2:
        gate = "request_phase3_risk_filter_model=true"
        reason = "至少两条非辅助规则同时优于裸 qlib 与排除组，且年度方向较稳定；但仍需审查者授权，不能自行训练模型。"
    elif stable_primary_rule_count >= 1:
        gate = "request_phase2b_rule_repair=true"
        reason = "存在一条非辅助风险规则具备局部有效性，但辅助确认规则不能单独支撑 Phase3，且部分规则存在 2025 或跨年反向，需要修正规则或缩小适用范围。"
    else:
        gate = "stop_orthogonal_direction=true"
        reason = "本批规则未能稳定优于裸 qlib 对照或排除组，解释价值不足。"
    return {
        "generated_at": utc_now(),
        "gate": gate,
        "reason": reason,
        "stable_primary_rule_count": stable_primary_rule_count,
        "rule_evaluations": rule_evaluations,
        "forbidden_actions": {
            "network": False,
            "token": False,
            "data_redownload": False,
            "new_data_source": False,
            "model_training": False,
            "provider_write": False,
            "provider_refresh_publish": False,
            "accepted_latest_switching": False,
            "frontend_api": False,
            "trading_actions": False,
        },
    }


def write_outputs(
    samples: pd.DataFrame,
    schema: dict[str, Any],
    repair_summary: dict[str, Any],
    group_metrics: pd.DataFrame,
    segment_rule_metrics: pd.DataFrame,
    daily_membership: pd.DataFrame,
    turnover: pd.DataFrame,
    gate: dict[str, Any],
) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    rule_defs = {
        "generated_at": utc_now(),
        "scope": "phase2_rules_baseline_readonly",
        "inputs": {
            "samples": rel(SAMPLES_PATH),
            "factor_metrics": rel(FACTOR_METRICS_PATH),
            "segment_metrics": rel(SEGMENT_METRICS_PATH),
            "schema": rel(SCHEMA_PATH),
            "repair_summary": rel(REPAIR_SUMMARY_PATH),
        },
        "rules": [rule.__dict__ for rule in RULES],
        "notes": [
            "Rules are historical research labels only.",
            "confirmed_watch_candidate is not a buy recommendation.",
            "positive-rate is historical sample statistics only, not a win-rate promise.",
        ],
    }
    RULE_DEFINITIONS_PATH.write_text(json.dumps(rule_defs, ensure_ascii=False, indent=2), encoding="utf-8")
    group_metrics.to_csv(GROUP_METRICS_PATH, index=False)
    segment_rule_metrics.to_csv(SEGMENT_RULE_METRICS_PATH, index=False)
    daily_membership.to_csv(DAILY_MEMBERSHIP_PATH, index=False)
    turnover.to_csv(TURNOVER_PATH, index=False)
    GATE_SUMMARY_PATH.write_text(json.dumps(gate, ensure_ascii=False, indent=2), encoding="utf-8")

    top_rows = group_metrics[group_metrics["horizon"] == 20].copy()
    selected_rows = top_rows[top_rows["group"].isin(["baseline_top50", "baseline_top150", "rule_selected", "rule_excluded"])]
    selected_rows = selected_rows[
        ["rule_id", "group", "coverage_rows", "coverage_days", "coverage_symbols", "mean", "median", "downside_q10", "worst_decile_mean", "historical_positive_rate"]
    ]
    year_2025 = segment_rule_metrics[
        (segment_rule_metrics["segment_type"] == "year")
        & (segment_rule_metrics["segment"] == "2025")
        & (segment_rule_metrics["horizon"] == 20)
        & (segment_rule_metrics["group"].isin(["rule_selected", "rule_excluded"]))
    ][["rule_id", "group", "coverage_rows", "coverage_days", "mean", "downside_q10", "historical_positive_rate"]]
    q_summary = segment_rule_metrics[
        (segment_rule_metrics["segment_type"] == "quarter")
        & (segment_rule_metrics["horizon"] == 20)
        & (segment_rule_metrics["group"] == "rule_selected")
    ].copy()
    q_summary["abs_mean"] = q_summary["mean"].abs()
    q_summary = q_summary.sort_values(["rule_id", "abs_mean"], ascending=[True, False]).groupby("rule_id").head(4)
    q_summary = q_summary[["rule_id", "segment", "coverage_rows", "coverage_days", "mean", "downside_q10", "historical_positive_rate"]]

    lines = [
        "# Phase 2 Rules Baseline 执行报告",
        "",
        f"- 生成时间：`{utc_now()}`",
        "- 执行范围：基于 repaired Phase1B Full 样本的只读规则型风险过滤 baseline。",
        "- 禁止范围：未联网、未使用 token、未重拉数据、未新增数据源、未训练模型、未写 provider、未 refresh/publish、未 accepted latest switching、未前端/API、未交易相关操作。",
        f"- Phase2 gate：`{gate['gate']}`",
        f"- gate 理由：{gate['reason']}",
        "",
        "## 1. 输入与 PIT",
        "",
        f"- 样本：`{rel(SAMPLES_PATH)}`",
        f"- 样本行数：`{len(samples)}`",
        f"- 样本 asof：`{samples['asof'].min().strftime('%Y-%m-%d')}` 至 `{samples['asof'].max().strftime('%Y-%m-%d')}`",
        f"- repair prediction days：`{repair_summary.get('prediction_file_count')}` / `{repair_summary.get('calendar_days_2023_2024')}`",
        f"- schema prediction selection：`{schema.get('build_info', {}).get('prediction_selection_rule', '')}`",
        "- PIT 口径沿用 Phase1B：法人/融资字段只取 `available_at <= asof` 最近一笔；本阶段不引入新字段。",
        "",
        "## 2. 规则定义",
        "",
        md_table([rule.__dict__ for rule in RULES], ["rule_id", "status", "scope", "description", "selected_expr", "excluded_expr"]),
        "",
        "## 3. 20d 对照摘要",
        "",
        "- `historical_positive_rate` 仅为历史样本统计，不代表未来胜率或收益承诺。",
        md_table(selected_rows.to_dict("records"), ["rule_id", "group", "coverage_rows", "coverage_days", "coverage_symbols", "mean", "median", "downside_q10", "worst_decile_mean", "historical_positive_rate"]),
        "",
        "## 4. Turnover Proxy",
        "",
        md_table(turnover.to_dict("records"), ["group", "days", "mean_daily_member_count", "mean_daily_symmetric_change", "median_daily_symmetric_change", "mean_jaccard_with_previous_day"]),
        "",
        "## 5. 年度分段与 2025 反向年份",
        "",
        "- 2025 年单独列出，用于审查 margin balance 方向反转风险。",
        md_table(year_2025.to_dict("records"), ["rule_id", "group", "coverage_rows", "coverage_days", "mean", "downside_q10", "historical_positive_rate"]),
        "",
        "## 6. 季度分段摘要",
        "",
        md_table(q_summary.to_dict("records"), ["rule_id", "segment", "coverage_rows", "coverage_days", "mean", "downside_q10", "historical_positive_rate"]),
        "",
        "## 7. Rule Gate 明细",
        "",
        md_table(gate["rule_evaluations"], ["rule_id", "status", "selected_20d_mean", "excluded_20d_mean", "baseline_20d_mean", "selected_20d_downside_q10", "excluded_20d_downside_q10", "baseline_20d_downside_q10", "coverage_days", "year_direction_share", "reverse_years", "passes_rule_baseline_check", "counts_for_phase3_gate"]),
        "",
        "## 8. 产物",
        "",
        f"- 规则定义：`{rel(RULE_DEFINITIONS_PATH)}`",
        f"- 全样本组指标：`{rel(GROUP_METRICS_PATH)}`",
        f"- 年度/季度分段指标：`{rel(SEGMENT_RULE_METRICS_PATH)}`",
        f"- 每日 membership：`{rel(DAILY_MEMBERSHIP_PATH)}`",
        f"- turnover proxy：`{rel(TURNOVER_PATH)}`",
        f"- gate summary：`{rel(GATE_SUMMARY_PATH)}`",
        "",
        "## 9. 是否请求下一阶段",
        "",
        f"- `{gate['gate']}`",
        "- 即使 gate 请求 Phase3，也必须等待审查者授权；本阶段没有训练 Risk Filter Model。",
        "",
        "## 10. 风险与待审查问题",
        "",
        "- 规则阈值使用简单横截面分位数，未做参数搜索；若审查者认为稳定性不足，应进入 Phase2B 修正规则，而不是直接训练模型。",
        "- `available_at = next_trading_day(trade_date)` 仍是 conservative visibility proxy，不是官方发布时间证明。",
        "- 外资/融资确认类规则只作为研究状态，不构成买入/卖出建议。",
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    samples, schema, factor_metrics, segment_metrics, repair_summary = load_inputs()
    _ = factor_metrics, segment_metrics
    samples = add_rule_masks(samples)
    group_metrics, segment_rule_metrics, daily_membership, turnover = build_metrics(samples)
    gate = evaluate_gate(group_metrics, segment_rule_metrics)
    write_outputs(samples, schema, repair_summary, group_metrics, segment_rule_metrics, daily_membership, turnover, gate)
    print(json.dumps({"gate": gate, "artifacts": {
        "rules": rel(RULE_DEFINITIONS_PATH),
        "group_metrics": rel(GROUP_METRICS_PATH),
        "segment_metrics": rel(SEGMENT_RULE_METRICS_PATH),
        "daily_membership": rel(DAILY_MEMBERSHIP_PATH),
        "turnover": rel(TURNOVER_PATH),
        "gate_summary": rel(GATE_SUMMARY_PATH),
        "report": rel(REPORT_PATH),
    }}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
