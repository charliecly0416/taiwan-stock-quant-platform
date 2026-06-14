#!/usr/bin/env python3
"""Build Phase2D closure artifacts from Phase2C manual rule freeze outputs.

This is a readonly closure step. It reads Phase2C artifacts and the Phase2D
work document, then writes only Phase2D closure outputs.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data_tw/experiments/decision_orthogonal"
DOC_DIR = ROOT / "docs/tw_decision_model_orthogonal"

PHASE2C_REPORT = DOC_DIR / "PHASE2C_MANUAL_RULE_FREEZE_EXECUTION_REPORT_CN.md"
PHASE2C_CARDS = OUT_DIR / "phase2c_manual_rule_cards.json"
PHASE2C_SUMMARY = OUT_DIR / "phase2c_manual_rule_freeze_summary.json"
PHASE2D_WORK = DOC_DIR / "PHASE2C_MANUAL_RULE_FREEZE_REVIEW_AND_PHASE2D_CLOSURE_WORK_CN.md"

PHASE2D_REPORT = DOC_DIR / "PHASE2D_ORTHOGONAL_RULE_CLOSURE_REPORT_CN.md"
PHASE2D_SUMMARY = OUT_DIR / "phase2d_orthogonal_rule_closure_summary.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def metric(card: dict[str, Any], key: str) -> Any:
    return card["key_metrics"]["candidate_comparison_20d"].get(key)


def fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def md_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "|" + "|".join(["---" for _ in columns]) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(fmt(row.get(col, "")) for col in columns) + " |")
    return "\n".join(lines)


def build() -> None:
    generated_at = utc_now()
    cards = load_json(PHASE2C_CARDS)
    phase2c_summary = load_json(PHASE2C_SUMMARY)
    # Read required docs to make the dependency explicit for auditability.
    phase2c_report_present = PHASE2C_REPORT.read_text(encoding="utf-8") != ""
    phase2d_work_present = PHASE2D_WORK.read_text(encoding="utf-8") != ""

    rule_rows = [
        {
            "rule_id": card["rule_id"],
            "final_status": card["status"],
            "baseline_group": card["baseline_group"],
            "selected_20d_mean": metric(card, "selected_20d_mean"),
            "baseline_20d_mean": metric(card, "baseline_20d_mean"),
            "selected_20d_downside_q10": metric(card, "selected_20d_downside_q10"),
            "baseline_20d_downside_q10": metric(card, "baseline_20d_downside_q10"),
            "coverage_days": metric(card, "coverage_days"),
            "reverse_years": metric(card, "reverse_years"),
        }
        for card in cards
    ]

    summary = {
        "generated_at": generated_at,
        "scope": "phase2d_orthogonal_rule_closure_readonly",
        "inputs": [
            rel(PHASE2C_REPORT),
            rel(PHASE2C_CARDS),
            rel(PHASE2C_SUMMARY),
            rel(PHASE2D_WORK),
        ],
        "outputs": [rel(PHASE2D_REPORT), rel(PHASE2D_SUMMARY)],
        "input_presence_check": {
            "phase2c_report_present": phase2c_report_present,
            "phase2d_work_document_present": phase2d_work_present,
            "phase2c_frozen_rule_count": phase2c_summary.get("frozen_rule_count"),
        },
        "orthogonal_rule_exploration_closed": True,
        "manual_rule_cards_frozen": True,
        "phase3_allowed": False,
        "risk_filter_model_training_allowed": False,
        "frontend_api_integration_allowed": False,
        "provider_write_allowed": False,
        "accepted_latest_switching_allowed": False,
        "trading_or_order_allowed": False,
        "requires_user_decision_for_new_direction": True,
        "phase2b_pass_count": 0,
        "closure_reason": [
            "Phase2B pass_count=0。",
            "主 caution 规则存在 2025 反向且 downside q10 未优于 baseline。",
            "主 review 规则 coverage 较窄且 2025 反向。",
            "explanation/auxiliary 规则不计入模型 gate。",
        ],
        "final_frozen_rules": rule_rows,
        "pit_caveat": "available_at = next_trading_day(trade_date) 是 conservative visibility proxy，不是官方发布时间证明。",
        "readonly_safety_boundary": [
            "不是交易建议。",
            "不是买入/卖出信号。",
            "不是目标仓位。",
            "不是收益承诺。",
            "不是上涨概率承诺。",
            "不触发订单、broker、quick-trade、monitor config save、monitor scan 或 alerts write。",
        ],
        "forbidden_actions": {
            "parameter_tuning": False,
            "rule_sample_recompute": False,
            "network": False,
            "token": False,
            "data_redownload": False,
            "new_data_source": False,
            "monthly_revenue": False,
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

    report = f"""# Phase 2D Orthogonal Rule Closure 执行报告

- 生成时间：`{generated_at}`
- 执行范围：只读汇总 Phase2C 冻结规则卡与审查工作文档，对正交特征规则探索做收尾归档。
- 禁止范围：未继续调参、未重新计算规则样本、未联网、未使用 token、未重拉数据、未新增数据源、未月营收、未训练模型、未 Risk Filter Model、未写 provider、未 refresh/publish、未 accepted latest switching、未前端/API、未 monitor 写入、未交易相关操作。
- orthogonal_rule_exploration_closed=true
- manual_rule_cards_frozen=true
- phase3_allowed=false
- risk_filter_model_training_allowed=false
- frontend_api_integration_allowed=false
- provider_write_allowed=false
- accepted_latest_switching_allowed=false
- trading_or_order_allowed=false
- requires_user_decision_for_new_direction=true

## 1. 输入与边界

- 输入只使用：
  - `{rel(PHASE2C_REPORT)}`
  - `{rel(PHASE2C_CARDS)}`
  - `{rel(PHASE2C_SUMMARY)}`
  - `{rel(PHASE2D_WORK)}`
- 本阶段没有读取样本 parquet，没有重新计算规则样本，没有新增字段、数据源或参数搜索。
- Phase2D 是 closure 阶段，不是继续探索阶段。

## 2. 最终冻结规则清单

{md_table(rule_rows, ["rule_id", "final_status", "baseline_group", "selected_20d_mean", "baseline_20d_mean", "selected_20d_downside_q10", "baseline_20d_downside_q10", "coverage_days", "reverse_years"])}

## 3. 不能进入 Phase3 的原因

- Phase2B `pass_count=0`。
- 主 caution 规则 `margin_crowding_top50_p85_caution` 存在 2025 反向，且 downside q10 未优于 baseline。
- 主 review 规则 `flow_crowding_conflict_top50_p80_weak30_review` coverage 较窄，只有 797 days，且存在 2025 反向。
- `foreign_flow_non_crowded_top150_explanation` 和 `margin_change_non_crowded_top150_auxiliary` 不计入模型 gate。
- 当前结果只支持人工研究解释规则卡，不支持 Risk Filter Model 训练。

## 4. PIT Caveat

- `available_at = next_trading_day(trade_date)` 是 conservative visibility proxy，不是官方发布时间证明。
- 后续任何引用这些规则卡的环节，都必须保留该 caveat。
- 本阶段没有重新解释该 proxy，也没有将其包装为官方公告时间。

## 5. 只读安全边界

- 不是交易建议。
- 不是买入/卖出信号。
- 不是目标仓位。
- 不是收益承诺。
- 不是上涨概率承诺。
- 不触发订单、broker、quick-trade、monitor config save、monitor scan 或 alerts write。
- 不支持 provider 写入、accepted latest switching、前端/API 接入或任何交易路径。

## 6. 产物

- Closure report：`{rel(PHASE2D_REPORT)}`
- Closure summary JSON：`{rel(PHASE2D_SUMMARY)}`
- 只读整理脚本：`scripts/summarize_tw_decision_orthogonal_phase2d_closure.py`

## 7. 结论

- `orthogonal_rule_exploration_closed=true`
- `manual_rule_cards_frozen=true`
- `requires_user_decision_for_new_direction=true`
- 本轮正交特征规则探索到 Phase2C/Phase2D 收尾为止，不得自动开启 Phase3 或任何新方向。

## 8. 风险与待审查问题

- 规则卡可用于后续人工复盘引用，但不能被误用为自动模型训练证据。
- 后续若要训练模型、接入前端/API、写 provider、切换 accepted latest、引入新数据源或输出交易含义，必须作为新方向提交用户确认。
"""

    PHASE2D_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    PHASE2D_REPORT.write_text(report, encoding="utf-8")
    print(f"wrote {rel(PHASE2D_SUMMARY)}")
    print(f"wrote {rel(PHASE2D_REPORT)}")


if __name__ == "__main__":
    build()
