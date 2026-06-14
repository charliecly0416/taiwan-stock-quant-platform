#!/usr/bin/env python3
"""Freeze Phase2C manual rule cards from Phase2B readonly artifacts.

This script only reads Phase2B rule outputs and writes Phase2C documentation
artifacts. It does not train models, call network APIs, write providers, or
touch trading paths.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data_tw/experiments/decision_orthogonal"
DOC_DIR = ROOT / "docs/tw_decision_model_orthogonal"

DEFINITIONS_PATH = OUT_DIR / "phase2b_rules_definitions.json"
GROUP_METRICS_PATH = OUT_DIR / "phase2b_rules_group_metrics.csv"
TURNOVER_PATH = OUT_DIR / "phase2b_rules_turnover_summary.csv"
COMPARISON_PATH = OUT_DIR / "phase2b_rules_candidate_comparison.csv"
GATE_PATH = OUT_DIR / "phase2b_rules_gate_summary.json"

CARDS_PATH = OUT_DIR / "phase2c_manual_rule_cards.json"
SUMMARY_PATH = OUT_DIR / "phase2c_manual_rule_freeze_summary.json"
REPORT_PATH = DOC_DIR / "PHASE2C_MANUAL_RULE_FREEZE_EXECUTION_REPORT_CN.md"

READONLY_SAFETY_NOTE = (
    "只读研究解释标签；不是交易建议、不是买入/卖出信号、不是目标仓位、"
    "不是收益承诺、不是上涨概率承诺；不触发订单、broker、quick-trade、"
    "monitor config save、monitor scan 或 alerts write。"
)

NOT_INTENDED_USE = [
    "不是交易建议。",
    "不是买入/卖出信号。",
    "不是目标仓位。",
    "不是收益承诺。",
    "不是上涨概率承诺。",
    "不触发订单、broker、quick-trade 或 monitor 写入。",
    "不作为 Risk Filter Model 训练 gate。",
]

FREEZE_SPECS = [
    {
        "rule_id": "margin_crowding_top50_p85_caution",
        "status": "manual_caution_explanation",
        "intended_use": "人工解释 Top50 中融资余额相对拥挤的 caution 状态。",
        "not_intended_extra": ["不作为自动风险过滤模型规则。"],
        "known_caveats": [
            "2025 年分段方向反向。",
            "selected downside q10 未优于 baseline Top50。",
            "只能作为人工解释风险标签，不能作为模型训练通过证据。",
        ],
    },
    {
        "rule_id": "flow_crowding_conflict_top50_p80_weak30_review",
        "status": "manual_review_explanation",
        "intended_use": "人工解释融资拥挤但外资/自营商 20 日流向偏弱的冲突状态。",
        "not_intended_extra": ["不能单独作为模型 gate。"],
        "known_caveats": [
            "2025 年分段方向反向。",
            "coverage 只有 797 days，窄于主 caution 规则。",
            "不能单独作为模型 gate。",
        ],
    },
    {
        "rule_id": "foreign_flow_non_crowded_top150_explanation",
        "status": "manual_explanation_feature",
        "intended_use": "只解释非拥挤条件下外资流入背景。",
        "not_intended_extra": ["不得升级为 confirmed watch。", "不得作为风险过滤或买卖含义。"],
        "known_caveats": [
            "counts_for_gate=false。",
            "不得恢复为 confirmed watch。",
            "只能作为背景解释字段。",
        ],
    },
    {
        "rule_id": "margin_change_non_crowded_top150_auxiliary",
        "status": "manual_auxiliary_feature",
        "intended_use": "只作为非拥挤条件下融资变化的辅助确认。",
        "not_intended_extra": ["不得单独输出强研究状态。"],
        "known_caveats": [
            "counts_for_gate=false。",
            "不能独立支撑 Phase3。",
            "只能作为 auxiliary feature。",
        ],
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def clean_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def row_to_dict(row: pd.Series, keys: list[str]) -> dict[str, Any]:
    return {key: clean_value(row.get(key)) for key in keys}


def find_rule_definition(definitions: dict[str, Any], rule_id: str) -> dict[str, Any]:
    for rule in definitions["rules"]:
        if rule["rule_id"] == rule_id:
            return rule
    raise KeyError(f"missing rule definition: {rule_id}")


def metric_row(group_metrics: pd.DataFrame, rule_id: str, group: str) -> dict[str, Any]:
    rows = group_metrics[
        (group_metrics["rule_id"] == rule_id)
        & (group_metrics["group"] == group)
        & (group_metrics["segment_type"] == "all")
        & (group_metrics["segment"] == "all")
        & (group_metrics["horizon"] == 20)
    ]
    if rows.empty:
        return {}
    return row_to_dict(
        rows.iloc[0],
        [
            "coverage_rows",
            "coverage_days",
            "coverage_symbols",
            "daily_size_mean",
            "mean",
            "median",
            "downside_q10",
            "worst_decile_mean",
            "historical_positive_rate",
        ],
    )


def turnover_row(turnover: pd.DataFrame, group: str) -> dict[str, Any]:
    rows = turnover[turnover["group"] == group]
    if rows.empty:
        return {}
    return row_to_dict(
        rows.iloc[0],
        [
            "days",
            "mean_daily_member_count",
            "mean_daily_symmetric_change",
            "median_daily_symmetric_change",
            "mean_jaccard_with_previous_day",
        ],
    )


def comparison_row(comparison: pd.DataFrame, rule_id: str) -> dict[str, Any]:
    rows = comparison[comparison["rule_id"] == rule_id]
    if rows.empty:
        return {}
    return row_to_dict(
        rows.iloc[0],
        [
            "selected_20d_mean",
            "excluded_20d_mean",
            "baseline_20d_mean",
            "selected_20d_downside_q10",
            "baseline_20d_downside_q10",
            "coverage_rows",
            "coverage_days",
            "year_direction_share",
            "reverse_years",
            "y2025_aligned",
            "passes_phase2b_gate_check",
            "eligible_manual_freeze",
        ],
    )


def build_cards() -> tuple[list[dict[str, Any]], dict[str, Any], str]:
    generated_at = utc_now()
    definitions = load_json(DEFINITIONS_PATH)
    gate = load_json(GATE_PATH)
    group_metrics = pd.read_csv(GROUP_METRICS_PATH)
    turnover = pd.read_csv(TURNOVER_PATH)
    comparison = pd.read_csv(COMPARISON_PATH)

    cards: list[dict[str, Any]] = []
    for spec in FREEZE_SPECS:
        rule_id = spec["rule_id"]
        definition = find_rule_definition(definitions, rule_id)
        selected_key = f"{rule_id}__selected"
        card = {
            "rule_id": rule_id,
            "status": spec["status"],
            "condition": definition["selected_expr"],
            "baseline_group": definition["baseline_group"],
            "source_phase2b_status": definition["status"],
            "rule_family": definition["rule_family"],
            "intended_use": spec["intended_use"],
            "not_intended_use": NOT_INTENDED_USE + spec["not_intended_extra"],
            "key_metrics": {
                "selected_20d": metric_row(group_metrics, rule_id, "rule_selected"),
                "excluded_20d": metric_row(group_metrics, rule_id, "rule_excluded"),
                "candidate_comparison_20d": comparison_row(comparison, rule_id),
                "turnover_proxy": turnover_row(turnover, selected_key),
            },
            "known_caveats": spec["known_caveats"],
            "pit_note": (
                "沿用 Phase1B repaired full 与 Phase2B 产物的 point-in-time 约束；"
                "available_at = next_trading_day(trade_date) 仍是 conservative visibility proxy，"
                "不是官方发布时间证明。"
            ),
            "readonly_safety_note": READONLY_SAFETY_NOTE,
        }
        cards.append(card)

    summary = {
        "generated_at": generated_at,
        "scope": "phase2c_manual_rule_freeze_readonly",
        "inputs": [
            rel(DEFINITIONS_PATH),
            rel(GROUP_METRICS_PATH),
            rel(TURNOVER_PATH),
            rel(COMPARISON_PATH),
            rel(GATE_PATH),
        ],
        "outputs": [rel(CARDS_PATH), rel(SUMMARY_PATH), rel(REPORT_PATH)],
        "phase2b_gate": gate.get("gate"),
        "phase3_allowed": False,
        "risk_filter_model_training_allowed": False,
        "provider_write_allowed": False,
        "accepted_latest_switching_allowed": False,
        "trading_or_order_allowed": False,
        "manual_rules_ready_for_later_review": True,
        "stop_before_phase3": True,
        "frozen_rule_count": len(cards),
        "frozen_rule_ids": [card["rule_id"] for card in cards],
        "manual_caution_rule": "margin_crowding_top50_p85_caution",
        "manual_review_rule": "flow_crowding_conflict_top50_p80_weak30_review",
        "explanation_feature": "foreign_flow_non_crowded_top150_explanation",
        "auxiliary_feature": "margin_change_non_crowded_top150_auxiliary",
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
            "monitor_writes": False,
            "trading_actions": False,
            "target_position_or_weight": False,
        },
    }
    return cards, summary, generated_at


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "|" + "|".join(["---" for _ in columns]) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(fmt(row.get(col)) for col in columns) + " |")
    return "\n".join(lines)


def write_report(cards: list[dict[str, Any]], summary: dict[str, Any], generated_at: str) -> None:
    rows = []
    for card in cards:
        cmp = card["key_metrics"]["candidate_comparison_20d"]
        rows.append(
            {
                "rule_id": card["rule_id"],
                "status": card["status"],
                "baseline_group": card["baseline_group"],
                "selected_20d_mean": cmp.get("selected_20d_mean"),
                "baseline_20d_mean": cmp.get("baseline_20d_mean"),
                "selected_20d_downside_q10": cmp.get("selected_20d_downside_q10"),
                "baseline_20d_downside_q10": cmp.get("baseline_20d_downside_q10"),
                "coverage_days": cmp.get("coverage_days"),
                "reverse_years": cmp.get("reverse_years"),
            }
        )

    report = f"""# Phase 2C Manual Rule Freeze 执行报告

- 生成时间：`{generated_at}`
- 执行范围：只读整理 Phase2B 规则产物，冻结人工研究解释规则卡。
- 禁止范围：未联网、未使用 token、未重拉数据、未新增数据源、未月营收、未训练模型、未 Risk Filter Model、未写 provider、未 refresh/publish、未 accepted latest switching、未前端/API、未 monitor 写入、未交易相关操作。
- phase3_allowed=false
- risk_filter_model_training_allowed=false
- provider_write_allowed=false
- accepted_latest_switching_allowed=false
- trading_or_order_allowed=false
- manual_rules_ready_for_later_review=true
- stop_before_phase3=true

## 1. 输入与边界

- 输入只使用 Phase2B 产物：
  - `{rel(DEFINITIONS_PATH)}`
  - `{rel(GROUP_METRICS_PATH)}`
  - `{rel(TURNOVER_PATH)}`
  - `{rel(COMPARISON_PATH)}`
  - `{rel(GATE_PATH)}`
- 本阶段没有读取样本 parquet，没有重新计算规则样本，没有新增字段或数据源。
- Phase2B gate：`{summary["phase2b_gate"]}`。
- Phase2C 只冻结人工解释规则，不进入 Phase3。

## 2. 冻结规则卡

{markdown_table(rows, ["rule_id", "status", "baseline_group", "selected_20d_mean", "baseline_20d_mean", "selected_20d_downside_q10", "baseline_20d_downside_q10", "coverage_days", "reverse_years"])}

## 3. 规则用途与禁止用途

- `margin_crowding_top50_p85_caution`：冻结为 `manual_caution_explanation`，用于人工解释 Top50 中融资余额相对拥挤。必须同时提示 2025 反向，以及 downside q10 未优于 baseline。
- `flow_crowding_conflict_top50_p80_weak30_review`：冻结为 `manual_review_explanation`，用于人工解释融资拥挤但外资/自营商流向偏弱的冲突状态。必须同时提示 2025 反向、coverage 只有 797 days，不能单独作为模型 gate。
- `foreign_flow_non_crowded_top150_explanation`：冻结为 `manual_explanation_feature`，只解释非拥挤条件下外资流入背景，不得升级为 confirmed watch。
- `margin_change_non_crowded_top150_auxiliary`：冻结为 `manual_auxiliary_feature`，只作为辅助确认，不得单独输出强研究状态。

每张规则卡均明确：不是交易建议、不是买入/卖出信号、不是目标仓位、不是收益承诺、不是上涨概率承诺，不触发订单、broker、quick-trade 或 monitor 写入。

## 4. Point-in-Time 说明

- Phase2C 不新增 PIT 逻辑，只继承 Phase1B repaired full 与 Phase2B 的只读产物。
- `available_at = next_trading_day(trade_date)` 仍是 conservative visibility proxy，不是官方发布时间证明。
- 本阶段没有重新解释该 proxy，也没有把它包装为官方公告时间。

## 5. 产物

- 规则卡：`{rel(CARDS_PATH)}`
- freeze summary：`{rel(SUMMARY_PATH)}`
- 执行报告：`{rel(REPORT_PATH)}`
- 只读整理脚本：`scripts/freeze_tw_decision_orthogonal_phase2c_manual_rules.py`

## 6. 结论

- `manual_rules_ready_for_later_review=true`
- `stop_before_phase3=true`
- 当前证据只支持人工研究解释规则卡，不支持 Phase3、Risk Filter Model 训练、前端/API 接入、provider 写入或任何交易路径。

## 7. 风险与待审查问题

- 主 caution 规则仍存在 2025 反向，且 downside q10 未优于 baseline。
- 主 review 规则 coverage 较窄，不能单独作为模型 gate。
- explanation/auxiliary 两类字段不得被后续误升级为 confirmed watch 或强研究状态。
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> None:
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cards, summary, generated_at = build_cards()
    CARDS_PATH.write_text(json.dumps(cards, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(cards, summary, generated_at)
    print(f"wrote {rel(CARDS_PATH)}")
    print(f"wrote {rel(SUMMARY_PATH)}")
    print(f"wrote {rel(REPORT_PATH)}")


if __name__ == "__main__":
    main()
