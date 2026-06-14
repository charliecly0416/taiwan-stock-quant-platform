#!/usr/bin/env python3
"""Phase V1 yearly replay validation for frozen LTR candidates.

Readonly, local-only validation. This script reuses the Phase3A2C repaired
portfolio replay authority and limits output to yearly slices only.
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evaluate_tw_ltr_phase3a2_full_daily_replay import (  # noqa: E402
    CFG,
    METHODS,
    OfflineService,
    PriceStore,
    accepted_runs,
    daily_period,
    frozen_scores,
    md,
    rel,
    replay_method,
    result_row,
    wcsv,
    wjson,
)

OUT = ROOT / "data_tw/experiments/ltr_strategy_validation/phasev1_yearly_replay"
DOC = ROOT / "docs/tw_ltr_strategy_validation/PHASEV1_YEARLY_REPLAY_EXECUTION_REPORT_CN.md"
PERIODS = [
    ("2022", "2022-01-01", "2022-12-31"),
    ("2023", "2023-01-01", "2023-12-31"),
    ("2024", "2024-01-01", "2024-12-31"),
    ("2025", "2025-01-01", "2025-12-31"),
    ("2026_ytd", "2026-01-01", "2026-06-13"),
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def comparison_status(quality: dict[str, Any]) -> str:
    if int(quality.get("common_replay_days") or 0) <= 0:
        return "insufficient_data"
    return "completed"


def yearly_result_row(period: str, start: str, end: str, method: str, payload: dict[str, Any], baseline_payload: dict[str, Any]) -> dict[str, Any]:
    baseline_metrics = baseline_payload["metrics"]
    row = result_row(
        period=period,
        start=start,
        end=end,
        method=method,
        payload=payload,
        baseline=float(baseline_metrics.get("totalReturn") or 0.0),
        ltr=0.0,
    )
    metrics = payload["metrics"]
    row.pop("delta_vs_phase1c_ltr_simple_daily", None)
    row["buy_count"] = row.pop("add_action_count")
    row["relative_return_vs_top50_adaptive"] = row.pop("delta_vs_rank_rotate_top50_adaptive_score")
    row["relative_drawdown_vs_top50_adaptive"] = round(
        float(metrics.get("maxDrawdown") or 0.0) - float(baseline_metrics.get("maxDrawdown") or 0.0),
        6,
    )
    row["relative_actions_vs_top50_adaptive"] = int(metrics.get("actionCount") or 0) - int(baseline_metrics.get("actionCount") or 0)
    return row


def write_report(gate: dict[str, Any], rows: list[dict[str, Any]], quality_rows: list[dict[str, Any]], price_audit_rows: list[dict[str, Any]]) -> None:
    candidate_rows = [
        row
        for row in rows
        if row["method"] in {"rank_rotate_top50_adaptive_score", "phase1c_ltr_simple_daily", "phase1c_ltr_turnover_controlled_daily"}
    ]
    lines = [
        "# Phase V1 分年完整日频回放验证执行报告",
        "",
        f"生成时间：{gate['created_at']}",
        "",
        "## 1. 本轮目标",
        "",
        "按 Phase V0 冻结合同，只做 2022 / 2023 / 2024 / 2025 / 2026 YTD 分年完整日频回放验证。候选策略、baseline、分数字段、产品侧回放 authority、执行价、费用税费、共同日期集合与指标均沿用 Phase3A2C 修复口径。",
        "",
        "本轮未执行 rolling 验证、未执行市况分段、未调参、未重训 LTR、未改前端/API、未联网、未新增数据源、未触发 provider / accepted latest / monitor / 交易链路。",
        "",
        "## 2. 冻结对象",
        "",
        "- 候选策略：`phase1c_ltr_simple_daily`、`phase1c_ltr_turnover_controlled_daily`。",
        "- 冻结分数：`score_head10_all_l31_alpha0.7_top50_only`。",
        "- 主 baseline：`rank_rotate_top50_adaptive_score`。",
        "- 其他 baseline：`rank_rotate_top50`、`rank_rotate_top30`、`confirmed_exit`。",
        "- 权威回放路径：产品侧 `TWStockPortfolioReplayService` / `_replay_variant()`；turnover-controlled 候选沿用 Phase3A2C 已修复只读实现。",
        "- 执行价：asof 后第一个真实交易日 close。",
        "- gross return：`not_available_in_current_engine`。",
        "",
        "## 3. 年度数据质量",
        "",
        md(quality_rows, ["period", "start_date", "end_date", "baseline_signal_days", "ltr_score_days", "common_replay_days", "excluded_dates", "comparison_status", "reason"], 10),
        "",
        "## 4. 主候选与主基线年度结果",
        "",
        md(candidate_rows, ["period", "method", "comparison_status", "gross_return", "fee_tax_adjusted_net_return", "final_equity", "max_drawdown", "action_count", "buy_count", "sell_count", "turnover_proxy_by_notional_over_avg_equity", "fee_and_tax", "missing_price_count", "trading_days_used", "relative_return_vs_top50_adaptive", "relative_drawdown_vs_top50_adaptive", "relative_actions_vs_top50_adaptive"], 30),
        "",
        "## 5. 全部 baseline 与候选年度结果",
        "",
        md(rows, ["period", "method", "comparison_status", "fee_tax_adjusted_net_return", "final_equity", "max_drawdown", "action_count", "buy_count", "sell_count", "turnover_proxy_by_notional_over_avg_equity", "fee_and_tax", "missing_price_count", "trading_days_used", "relative_return_vs_top50_adaptive", "relative_drawdown_vs_top50_adaptive", "relative_actions_vs_top50_adaptive"], 40),
        "",
        "## 6. Price Execution Audit 摘要",
        "",
        md(price_audit_rows, ["sample_asof", "symbol", "expected_next_trade_date", "actual_execution_date", "actual_execution_price", "days_to_execution", "status"], 20),
        "",
        "## 7. 产物",
        "",
        f"- 年度结果：`{gate['artifacts']['yearly_comparison']}`",
        f"- 数据质量：`{gate['artifacts']['data_quality']}`",
        f"- 执行价审计：`{gate['artifacts']['price_execution_audit']}`",
        f"- gate summary：`{gate['artifacts']['gate_summary']}`",
        "",
        "## 8. Safety Boundary",
        "",
        "本轮仅运行本地只读历史验证脚本。所有 add / reduce / action count 均为历史模拟统计，不是交易指令；报告不包含买入、卖出、持有、仓位建议，不包含收益承诺、胜率承诺或上涨概率语义。",
        "",
        "## 9. Gate",
        "",
        f"`{gate['recommended_gate']}`",
        "",
        "等待审查者确认后，才可进入下一阶段；本轮不自动启动 rolling 或市况验证。",
        "",
    ]
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    prices = PriceStore()
    runs = accepted_runs()
    frozen = frozen_scores()
    service = OfflineService(prices)
    cache: dict[str, list[dict[str, Any]]] = {}
    rows: list[dict[str, Any]] = []
    quality_rows: list[dict[str, Any]] = []

    for period, start, end in PERIODS:
        daily, quality = daily_period(service, runs, frozen, start, end, cache)
        status = comparison_status(quality)
        quality_rows.append({
            "period": period,
            "start_date": start,
            "end_date": end,
            "baseline_signal_days": quality["baseline_signal_days"],
            "ltr_score_days": quality["ltr_score_days"],
            "common_replay_days": quality["common_replay_days"],
            "excluded_dates": ",".join(quality["excluded_dates"][:60]),
            "comparison_status": status,
            "reason": "excluded dates removed from all methods" if quality["excluded_dates"] else "",
        })
        if status != "completed":
            for method in METHODS:
                rows.append({
                    "period": period,
                    "start_date": start,
                    "end_date": end,
                    "method": method,
                    "comparison_status": status,
                    "gross_return": "not_available_in_current_engine",
                    "fee_tax_adjusted_net_return": "",
                    "final_equity": "",
                    "max_drawdown": "",
                    "action_count": "",
                    "buy_count": "",
                    "risk_action_count": "",
                    "sell_count": "",
                    "turnover_proxy_by_notional_over_avg_equity": "",
                    "turnover_notional": "",
                    "fee_and_tax": "",
                    "missing_price_count": "",
                    "trading_days_used": "",
                    "relative_return_vs_top50_adaptive": "",
                    "relative_drawdown_vs_top50_adaptive": "",
                    "relative_actions_vs_top50_adaptive": "",
                    "historical_action_rows": "",
                })
            continue
        results = {method: replay_method(service, daily, method) for method in METHODS}
        baseline_payload = results["rank_rotate_top50_adaptive_score"]
        for method in METHODS:
            rows.append(yearly_result_row(period, start, end, method, results[method], baseline_payload))

    price_audit_rows = service.execution_audit_rows
    if not price_audit_rows:
        price_audit_rows = [{"sample_asof": "", "symbol": "", "expected_next_trade_date": "", "actual_execution_date": "", "actual_execution_price": "", "days_to_execution": "", "status": "blocked_no_execution_samples"}]
    max_gap = max([int(row.get("days_to_execution") or 0) for row in price_audit_rows if str(row.get("days_to_execution") or "").isdigit()] or [0])
    bad_gaps = [row for row in price_audit_rows if row.get("status") != "ok"]
    completed_periods = [row["period"] for row in quality_rows if row["comparison_status"] == "completed"]
    insufficient_periods = [row["period"] for row in quality_rows if row["comparison_status"] != "completed"]
    gate_name = "phasev1_yearly_replay_completed_hold_for_review" if not bad_gaps else "stop_phasev1_price_execution_audit_failed"

    fieldnames = [
        "period",
        "start_date",
        "end_date",
        "method",
        "comparison_status",
        "gross_return",
        "fee_tax_adjusted_net_return",
        "final_equity",
        "max_drawdown",
        "action_count",
        "buy_count",
        "risk_action_count",
        "sell_count",
        "turnover_proxy_by_notional_over_avg_equity",
        "turnover_notional",
        "fee_and_tax",
        "missing_price_count",
        "trading_days_used",
        "relative_return_vs_top50_adaptive",
        "relative_drawdown_vs_top50_adaptive",
        "relative_actions_vs_top50_adaptive",
        "historical_action_rows",
    ]
    wcsv(OUT / "phasev1_yearly_comparison.csv", rows, fieldnames)
    wcsv(OUT / "phasev1_yearly_data_quality.csv", quality_rows, ["period", "start_date", "end_date", "baseline_signal_days", "ltr_score_days", "common_replay_days", "excluded_dates", "comparison_status", "reason"])
    wcsv(OUT / "phasev1_price_execution_audit.csv", price_audit_rows, ["sample_asof", "symbol", "expected_next_trade_date", "actual_execution_date", "actual_execution_price", "days_to_execution", "status"])

    gate = {
        "phase": "phasev1_yearly_replay_validation",
        "created_at": now(),
        "recommended_gate": gate_name,
        "authority_choice": "phase3a2c_repaired_product_side_portfolio_replay_authority",
        "scope": "yearly_only_2022_2023_2024_2025_2026_ytd",
        "forbidden_scope_not_run": ["rolling", "regime", "parameter_tuning", "ltr_retraining", "frontend_api", "network", "new_data_source", "provider", "accepted_latest", "monitor", "trading_chain"],
        "methods": METHODS,
        "completed_periods": completed_periods,
        "insufficient_periods": insufficient_periods,
        "price_execution_audit_sample_count": len(price_audit_rows),
        "price_execution_max_days_to_execution": max_gap,
        "gross_return_policy": "not_available_in_current_engine",
        "artifacts": {
            "yearly_comparison": rel(OUT / "phasev1_yearly_comparison.csv"),
            "data_quality": rel(OUT / "phasev1_yearly_data_quality.csv"),
            "price_execution_audit": rel(OUT / "phasev1_price_execution_audit.csv"),
            "gate_summary": rel(OUT / "phasev1_gate_summary.json"),
            "report": rel(DOC),
        },
    }
    wjson(OUT / "phasev1_gate_summary.json", gate)
    write_report(gate, rows, quality_rows, price_audit_rows)
    print(json.dumps({"ok": gate_name == "phasev1_yearly_replay_completed_hold_for_review", "gate": gate_name, "report": gate["artifacts"]["report"]}, ensure_ascii=False, indent=2))
    return 0 if gate_name == "phasev1_yearly_replay_completed_hold_for_review" else 2


if __name__ == "__main__":
    raise SystemExit(main())
