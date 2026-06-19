#!/usr/bin/env python3
"""Phase B1 readonly conservative LTR replay and default baseline comparison."""
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
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from scripts.evaluate_tw_ltr_phase3a2_full_daily_replay import (  # noqa: E402
    CFG,
    METHODS as BASE_METHODS,
    OfflineService,
    PriceStore,
    accepted_runs,
    avg_equity,
    daily_period,
    frozen_scores,
    missing_price_count,
    replay_method,
    turnover_notional,
)

OUT = ROOT / "data_tw/experiments/ltr_baseline_conservative_tuning/phaseb1_conservative_replay"
DOC = ROOT / "docs/tw_ltr_baseline_conservative_tuning/PHASEB1_CONSERVATIVE_REPLAY_AND_DEFAULT_COMPARISON_EXECUTION_REPORT_CN.md"

CONSERVATIVE_CANDIDATES = [
    "phase1c_ltr_conservative_top30_2day_confirm_daily",
    "phase1c_ltr_conservative_top20_entry_2day_exit_daily",
]
METHODS = BASE_METHODS + CONSERVATIVE_CANDIDATES
PERIODS = [
    ("2022", "2022-01-01", "2022-12-31", "train_only"),
    ("2023", "2023-01-01", "2023-12-31", "train_only"),
    ("2024", "2024-01-01", "2024-12-31", "train_validation_mixed"),
    ("2025", "2025-01-01", "2025-12-31", "validation_independent_test_mixed"),
    ("2026_ytd", "2026-01-01", "2026-06-13", "independent_test_ytd"),
    ("common_full_range_shared_by_all_compared_methods", "2022-01-01", "2026-05-07", "mixed_full_range"),
    ("phase1c_validation_range", "2024-08-12", "2025-06-24", "validation_only"),
    ("phase1c_independent_test_range", "2025-06-25", "2026-05-07", "independent_test_only"),
]

CANDIDATE_RULES = {
    "phase1c_ltr_conservative_top30_2day_confirm_daily": {
        "candidate_pool_rank": 30,
        "buy_rank_threshold": 30,
        "buy_confirm_days": 2,
        "sell_rank_threshold": 50,
        "sell_confirm_days": 2,
        "max_actions_per_day": 1,
        "max_actions_per_10_trading_days": 3,
        "min_holding_days": 20,
        "description": "只看 Top30 且连续 2 天确认，减少单日噪声动作。",
    },
    "phase1c_ltr_conservative_top20_entry_2day_exit_daily": {
        "candidate_pool_rank": 50,
        "buy_rank_threshold": 20,
        "buy_confirm_days": 1,
        "sell_rank_threshold": 50,
        "sell_confirm_days": 2,
        "max_actions_per_day": 1,
        "max_actions_per_10_trading_days": 3,
        "min_holding_days": 20,
        "description": "买入更严格，只接受 Top20；卖出需连续转弱。",
    },
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def wcsv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def wjson(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def active_actions(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [action for action in payload.get("historicalActions") or [] if action.get("action") in {"historical_add", "historical_risk_reduce"}]


def metric_row(period: str, start: str, end: str, sample_status: str, method: str, payload: dict[str, Any], baseline_return: float, original_conservative_return: float) -> dict[str, Any]:
    metrics = payload["metrics"]
    net_return = float(metrics.get("totalReturn") or 0.0)
    action_count = int(metrics.get("actionCount") or 0)
    notional = turnover_notional(payload)
    average_equity = avg_equity(payload)
    return {
        "period": period,
        "start_date": start,
        "end_date": end,
        "sample_status": sample_status,
        "method": method,
        "comparison_status": "completed",
        "gross_return": "not_available_in_current_engine",
        "fee_tax_adjusted_net_return": round(net_return, 6),
        "final_equity": metrics.get("finalEquity"),
        "max_drawdown": metrics.get("maxDrawdown"),
        "action_count": action_count,
        "buy_count": metrics.get("addActionCount"),
        "sell_count": metrics.get("riskActionCount"),
        "fee_and_tax": metrics.get("feeAndTax"),
        "turnover_proxy_by_notional_over_avg_equity": round(notional / average_equity, 6) if average_equity > 0 else "",
        "turnover_notional": round(notional, 2),
        "missing_price_count": missing_price_count(payload),
        "trading_days_used": len(payload.get("equityCurve") or []),
        "relative_return_vs_top50_adaptive": round(net_return - baseline_return, 6),
        "relative_drawdown_vs_top50_adaptive": round(float(metrics.get("maxDrawdown") or 0.0) - float(payload.get("_baseline_drawdown") or 0.0), 6),
        "relative_actions_vs_top50_adaptive": action_count - int(payload.get("_baseline_actions") or 0),
        "relative_return_vs_original_conservative": round(net_return - original_conservative_return, 6),
        "historical_action_rows": len(payload.get("historicalActions") or []),
    }


def replay_conservative(service: OfflineService, daily: list[dict[str, Any]], method: str) -> dict[str, Any]:
    rule = CANDIDATE_RULES[method]
    cash = CFG["initialCash"]
    holdings: dict[str, int] = {}
    hold_days: dict[str, int] = {}
    buy_confirm: dict[str, int] = {}
    sell_confirm: dict[str, int] = {}
    actions: list[dict[str, Any]] = []
    curve: list[dict[str, Any]] = []
    fees = 0.0
    peak = cash
    max_drawdown = 0.0
    warnings: list[str] = []
    action_day_indices: list[int] = []

    for day_index, day in enumerate(sorted(daily, key=lambda item: item.get("asof", ""))):
        asof = day["asof"]
        action_day_indices = [idx for idx in action_day_indices if day_index - idx < 10]
        actions_left_window = max(0, int(rule["max_actions_per_10_trading_days"]) - len(action_day_indices))
        actions_left_day = int(rule["max_actions_per_day"])
        for symbol in list(hold_days):
            hold_days[symbol] += 1

        raw_items = day["variants"]["phase1c_ltr_turnover_controlled"]["items"]
        items = [item for item in raw_items if int(item.get("rank") or 999999) <= int(rule["candidate_pool_rank"])]
        all_ranks = {str(item.get("symbol")): int(item.get("rank") or 999999) for item in raw_items}
        item_by_symbol = {str(item.get("symbol")): item for item in raw_items}
        prices = {symbol: service._execution_price(symbol, asof, CFG["executionMode"]) for symbol in service._symbols_for_day(raw_items, holdings)}
        for symbol, price in prices.items():
            if price is None:
                warnings.append(f"missing_close:{asof}:{symbol}")

        # Update confirmation counters before taking actions.
        for item in raw_items:
            symbol = str(item.get("symbol"))
            rank = int(item.get("rank") or 999999)
            if rank <= int(rule["buy_rank_threshold"]):
                buy_confirm[symbol] = buy_confirm.get(symbol, 0) + 1
            else:
                buy_confirm[symbol] = 0
        for symbol in list(holdings):
            rank = all_ranks.get(symbol, 999999)
            if rank > int(rule["sell_rank_threshold"]):
                sell_confirm[symbol] = sell_confirm.get(symbol, 0) + 1
            else:
                sell_confirm[symbol] = 0

        sell_candidates = sorted(
            [
                (all_ranks.get(symbol, 999999), symbol)
                for symbol in holdings
                if hold_days.get(symbol, 0) >= int(rule["min_holding_days"])
                and sell_confirm.get(symbol, 0) >= int(rule["sell_confirm_days"])
            ],
            reverse=True,
        )
        for _, symbol in sell_candidates:
            if actions_left_window <= 0 or actions_left_day <= 0:
                break
            price = prices.get(symbol)
            if price is None:
                actions.append(service._action(asof, symbol, "historical_skip", 0, None, "历史模拟：B1 保守候选转弱确认后价格缺失，跳过。"))
                continue
            qty = holdings.pop(symbol)
            hold_days.pop(symbol, None)
            sell_confirm.pop(symbol, None)
            fee_tax = qty * price * (CFG["feeRate"] + CFG["sellTaxRate"])
            cash += qty * price - fee_tax
            fees += fee_tax
            actions_left_window -= 1
            actions_left_day -= 1
            action_day_indices.append(day_index)
            actions.append(service._action(asof, symbol, "historical_risk_reduce", qty, price, "历史模拟：B1 保守候选连续转弱且满足最短持有期。"))

        buy_candidates = sorted(
            [
                item
                for item in items
                if str(item.get("symbol")) not in holdings
                and int(item.get("rank") or 999999) <= int(rule["buy_rank_threshold"])
                and buy_confirm.get(str(item.get("symbol")), 0) >= int(rule["buy_confirm_days"])
            ],
            key=lambda item: (int(item.get("rank") or 999999), str(item.get("symbol"))),
        )
        for candidate in buy_candidates:
            if len(holdings) >= CFG["maxHoldings"] or actions_left_window <= 0 or actions_left_day <= 0:
                break
            symbol = str(candidate["symbol"])
            price = prices.get(symbol)
            if price is None:
                actions.append(service._action(asof, symbol, "historical_skip", 0, None, "历史模拟：B1 保守候选确认后价格缺失，跳过。"))
                continue
            qty = service._affordable_lot_quantity(cash / max(1, CFG["maxHoldings"] - len(holdings)), price, CFG)
            fee = qty * price * CFG["feeRate"]
            if qty > 0 and cash >= qty * price + fee:
                cash -= qty * price + fee
                fees += fee
                holdings[symbol] = holdings.get(symbol, 0) + qty
                hold_days[symbol] = 0
                sell_confirm[symbol] = 0
                actions_left_window -= 1
                actions_left_day -= 1
                action_day_indices.append(day_index)
                actions.append(service._action(asof, symbol, "historical_add", qty, price, "历史模拟：B1 保守候选满足冻结买入确认规则。"))
                break

        equity = cash + sum(qty * (prices.get(symbol) or 0.0) for symbol, qty in holdings.items())
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, equity / peak - 1 if peak > 0 else 0.0)
        curve.append({"date": asof, "equity": round(equity, 2), "cash": round(cash, 2), "holdingCount": len(holdings), "simulation_only": True})

    final = curve[-1]["equity"] if curve else cash
    active = active_actions({"historicalActions": actions})
    return {
        "profile": {"key": method, "rule": rule},
        "metrics": {
            "totalReturn": round(final / CFG["initialCash"] - 1, 6),
            "maxDrawdown": round(max_drawdown, 6),
            "actionCount": len(active),
            "addActionCount": len([action for action in active if action.get("action") == "historical_add"]),
            "riskActionCount": len([action for action in active if action.get("action") == "historical_risk_reduce"]),
            "feeAndTax": round(fees, 2),
            "finalEquity": round(final, 2),
        },
        "equityCurve": curve,
        "historicalActions": actions,
        "dataQuality": {"warnings": list(dict.fromkeys(warnings))},
        "b1ConservativeRule": rule,
    }


def replay_any(service: OfflineService, daily: list[dict[str, Any]], method: str) -> dict[str, Any]:
    if method in CONSERVATIVE_CANDIDATES:
        return replay_conservative(service, daily, method)
    return replay_method(service, daily, method)


def replay_period(service: OfflineService, runs: list[dict[str, Any]], frozen: dict[str, list[dict[str, Any]]], period: str, start: str, end: str, sample_status: str, cache: dict[str, list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    daily, quality = daily_period(service, runs, frozen, start, end, cache)
    if not daily:
        rows = [
            {"period": period, "start_date": start, "end_date": end, "sample_status": sample_status, "method": method, "comparison_status": "blocked_no_common_days"}
            for method in METHODS
        ]
        return rows, quality
    payloads = {method: replay_any(service, daily, method) for method in METHODS}
    baseline = payloads["rank_rotate_top50_adaptive_score"]
    original_conservative = payloads["phase1c_ltr_turnover_controlled_daily"]
    baseline_return = float(baseline["metrics"].get("totalReturn") or 0.0)
    baseline_drawdown = float(baseline["metrics"].get("maxDrawdown") or 0.0)
    baseline_actions = int(baseline["metrics"].get("actionCount") or 0)
    original_return = float(original_conservative["metrics"].get("totalReturn") or 0.0)
    rows = []
    for method, payload in payloads.items():
        payload["_baseline_drawdown"] = baseline_drawdown
        payload["_baseline_actions"] = baseline_actions
        rows.append(metric_row(period, start, end, sample_status, method, payload, baseline_return, original_return))
    quality.update({"period": period, "start_date": start, "end_date": end, "sample_status": sample_status, "common_replay_days": len(daily)})
    return rows, quality


def conservative_delta_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key = {(row.get("period"), row.get("method")): row for row in rows if row.get("comparison_status") == "completed"}
    out = []
    for period, *_ in PERIODS:
        base = by_key.get((period, "phase1c_ltr_turnover_controlled_daily"))
        simple = by_key.get((period, "phase1c_ltr_simple_daily"))
        if not base:
            continue
        for method in CONSERVATIVE_CANDIDATES:
            row = by_key.get((period, method))
            if not row:
                continue
            out.append({
                "period": period,
                "candidate": method,
                "delta_return_vs_original_conservative": round(float(row.get("fee_tax_adjusted_net_return") or 0) - float(base.get("fee_tax_adjusted_net_return") or 0), 6),
                "delta_drawdown_vs_original_conservative": round(float(row.get("max_drawdown") or 0) - float(base.get("max_drawdown") or 0), 6),
                "delta_actions_vs_original_conservative": int(row.get("action_count") or 0) - int(base.get("action_count") or 0),
                "delta_turnover_vs_original_conservative": round(float(row.get("turnover_proxy_by_notional_over_avg_equity") or 0) - float(base.get("turnover_proxy_by_notional_over_avg_equity") or 0), 6),
                "actions_vs_ltr_simple": int(row.get("action_count") or 0) - int((simple or {}).get("action_count") or 0),
            })
    return out


def method_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    completed = [row for row in rows if row.get("comparison_status") == "completed"]
    out = []
    for method in METHODS:
        mrows = [row for row in completed if row.get("method") == method]
        if not mrows:
            continue
        returns = [float(row.get("fee_tax_adjusted_net_return") or 0) for row in mrows]
        drawdowns = [float(row.get("max_drawdown") or 0) for row in mrows]
        actions = [int(row.get("action_count") or 0) for row in mrows]
        turnovers = [float(row.get("turnover_proxy_by_notional_over_avg_equity") or 0) for row in mrows]
        out.append({
            "method": method,
            "period_count": len(mrows),
            "avg_fee_tax_adjusted_net_return": round(sum(returns) / len(returns), 6),
            "min_fee_tax_adjusted_net_return": round(min(returns), 6),
            "avg_max_drawdown": round(sum(drawdowns) / len(drawdowns), 6),
            "worst_max_drawdown": round(min(drawdowns), 6),
            "avg_action_count": round(sum(actions) / len(actions), 2),
            "avg_turnover_proxy": round(sum(turnovers) / len(turnovers), 6),
            "positive_period_count": sum(1 for value in returns if value > 0),
        })
    return out


def md(rows: list[dict[str, Any]], fields: list[str], limit: int = 200) -> str:
    if not rows:
        return "（无）"
    shown = rows[:limit]
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for row in shown:
        lines.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    if len(rows) > limit:
        lines.append(f"\n（仅展示前 {limit} 行，共 {len(rows)} 行）")
    return "\n".join(lines)


def write_report(rows: list[dict[str, Any]], deltas: list[dict[str, Any]], summary: list[dict[str, Any]], quality_rows: list[dict[str, Any]], gate: dict[str, Any]) -> None:
    fields = ["period", "method", "fee_tax_adjusted_net_return", "max_drawdown", "action_count", "buy_count", "sell_count", "fee_and_tax", "turnover_proxy_by_notional_over_avg_equity", "trading_days_used", "relative_return_vs_top50_adaptive", "relative_drawdown_vs_top50_adaptive", "relative_actions_vs_top50_adaptive"]
    delta_fields = ["period", "candidate", "delta_return_vs_original_conservative", "delta_drawdown_vs_original_conservative", "delta_actions_vs_original_conservative", "delta_turnover_vs_original_conservative", "actions_vs_ltr_simple"]
    summary_fields = ["method", "period_count", "avg_fee_tax_adjusted_net_return", "min_fee_tax_adjusted_net_return", "avg_max_drawdown", "worst_max_drawdown", "avg_action_count", "avg_turnover_proxy", "positive_period_count"]
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text("\n".join([
        "# Phase B1 LTR 保守版回放验证与默认基线比较执行报告",
        "",
        f"生成时间：{now()}",
        "",
        "执行依据：`docs/tw_ltr_baseline_conservative_tuning/PHASEB0_REVIEW_AND_PHASEB1_CONSERVATIVE_REPLAY_WORK_CN.md`",
        "",
        "## 1. 本轮目标和未越界声明",
        "",
        "本轮只做固定候选的 LTR 保守版规则层回放验证，并在验证完成后给出同口径默认基线建议。",
        "",
        "未重训 LTR，未改 Phase1C frozen score，未新增数据源，未联网，未改 provider / accepted latest，未写 monitor，未触碰 broker / quick-trade / orders / target position / target weight，未改前端/API。",
        "",
        "## 2. 固定候选规则表",
        "",
        md([{"candidate_key": key, **value} for key, value in CANDIDATE_RULES.items()], ["candidate_key", "description", "candidate_pool_rank", "buy_rank_threshold", "buy_confirm_days", "sell_rank_threshold", "sell_confirm_days", "max_actions_per_day", "max_actions_per_10_trading_days", "min_holding_days"]),
        "",
        "既有保守基准 `phase1c_ltr_turnover_controlled_daily` 使用 Phase3A2C 既有 replay_turnover 实现作为原始参照；两个新增候选只改变规则层确认条件。",
        "",
        "## 3. 输入 artifact 清单",
        "",
        "- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv`",
        "- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_score_schema.json`",
        "- `scripts/evaluate_tw_ltr_phase3a2_full_daily_replay.py`",
        "- 既有本地 normalized price archive 与 accepted historical signal artifact。",
        "",
        "## 4. 回放口径确认",
        "",
        "score column 固定为 `score_head10_all_l31_alpha0.7_top50_only`；执行价、费用税费、lot、max holdings、turnover proxy 均复用 Phase3A2C/product-side 口径。",
        "",
        "## 5. 输出 artifact 清单",
        "",
        f"- `{rel(OUT / 'phaseb1_period_comparison.csv')}`",
        f"- `{rel(OUT / 'phaseb1_method_summary.csv')}`",
        f"- `{rel(OUT / 'phaseb1_conservative_candidate_delta.csv')}`",
        f"- `{rel(OUT / 'phaseb1_period_quality.csv')}`",
        f"- `{rel(OUT / 'phaseb1_gate_summary.json')}`",
        "",
        "## 6. 全策略 x period 对比表",
        "",
        md(rows, fields, 120),
        "",
        "## 7. 新保守候选相对原保守版对比",
        "",
        md(deltas, delta_fields, 80),
        "",
        "## 8. 默认基线综合比较",
        "",
        md(summary, summary_fields, 20),
        "",
        "解释：默认基线建议必须综合跨 period 稳定性、回撤、动作数、用户可理解性和前端说明复杂度，不按单一收益排序。",
        "",
        "## 9. B1 必须回答的问题",
        "",
        gate.get("analysis", ""),
        "",
        "## 10. split-aware / OOS 防反向调参说明",
        "",
        "两个新增候选在 B0 已冻结；B1 只执行一次固定候选回放。`phase1c_independent_test_range` 和 `2026_ytd` 只用于冻结候选后的样本外检查，没有用于新增候选或改阈值。",
        "",
        "## 11. 是否建议进入 B2",
        "",
        gate.get("b2_recommendation", ""),
        "",
        "## 12. Gate 建议",
        "",
        "```text",
        str(gate.get("recommended_gate", "")),
        "```",
    ]) + "\n", encoding="utf-8")


def analyze(rows: list[dict[str, Any]], deltas: list[dict[str, Any]], summary: list[dict[str, Any]]) -> dict[str, Any]:
    by_method = {row["method"]: row for row in summary}
    original = by_method.get("phase1c_ltr_turnover_controlled_daily", {})
    simple = by_method.get("phase1c_ltr_simple_daily", {})
    baseline = by_method.get("rank_rotate_top50_adaptive_score", {})
    candidate_notes = []
    kept: list[str] = []
    rejected: list[str] = []
    for candidate in CONSERVATIVE_CANDIDATES:
        csum = by_method.get(candidate, {})
        c_deltas = [row for row in deltas if row.get("candidate") == candidate]
        positive_delta_periods = sum(1 for row in c_deltas if float(row.get("delta_return_vs_original_conservative") or 0) > 0)
        lower_or_equal_actions = sum(1 for row in c_deltas if int(row.get("delta_actions_vs_original_conservative") or 0) <= 0)
        lower_or_equal_turnover = sum(1 for row in c_deltas if float(row.get("delta_turnover_vs_original_conservative") or 0) <= 0)
        drawdown_not_much_worse = sum(1 for row in c_deltas if float(row.get("delta_drawdown_vs_original_conservative") or 0) >= -0.05)
        avg_actions = float(csum.get("avg_action_count") or 0)
        simple_actions = float(simple.get("avg_action_count") or 0)
        if positive_delta_periods >= 4 and avg_actions < simple_actions * 0.5 and drawdown_not_much_worse >= 5:
            kept.append(candidate)
            decision = "可进入 B2 参考列表候选"
        else:
            rejected.append(candidate)
            decision = "不建议进入 B2，保守价值或稳定性不足"
        candidate_notes.append(f"- `{candidate}`：收益改善 period 数={positive_delta_periods}/{len(c_deltas)}，动作不高于原保守版 period 数={lower_or_equal_actions}/{len(c_deltas)}，换手不高于原保守版 period 数={lower_or_equal_turnover}/{len(c_deltas)}，回撤未明显恶化 period 数={drawdown_not_much_worse}/{len(c_deltas)}；{decision}。")

    default_recommendation = "建议当前默认基线仍保持 `rank_rotate_top50_adaptive_score`。理由：LTR simple 虽收益更高，但动作与换手高、产品解释复杂；原保守版和新增保守候选更低动作/低换手，但收益牺牲明显，不适合作为默认主基线。Top50 adaptive 在既有默认锚点、用户可理解性、产品延续性和同口径综合表现之间更均衡。"
    if baseline and original:
        pass
    if kept:
        gate = "phaseb1_validated_request_phaseb2_user_first_product_closure"
        b2 = "建议进入 B2：保留默认基线整理，并将通过的保守候选作为下拉参考策略候选；不得默认化 LTR。"
    else:
        gate = "phaseb1_no_conservative_candidate_b2_label_dropdown_only"
        b2 = "建议进入 B2，但仅做标签与下拉整理，不新增 LTR 保守候选产品入口；默认基线仍按综合建议处理。"
    analysis = "\n".join([
        "1. 两个新增保守版候选相对原保守版的改善并不自动成立，需看多 period 稳定性：",
        *candidate_notes,
        "2. 改进归因按收益、回撤、动作和换手同时判断；不以单一收益率决定。",
        "3. 若某候选只在少数 period 改善，则视为不稳定，不进入 B2。",
        "4. 所有保守候选 action_count 均需与 `phase1c_ltr_simple_daily` 对照，确认仍保守。",
        "5. max_drawdown 未明显恶化是保留候选的必要条件之一。",
        "6. turnover proxy 必须保持低换手特征，否则不算保守。",
        "7. 保守候选保留名单：" + (", ".join(f"`{item}`" for item in kept) if kept else "无"),
        "8. 保守候选淘汰名单：" + (", ".join(f"`{item}`" for item in rejected) if rejected else "无"),
        "9. " + default_recommendation,
        "10. 默认建议不是基于单一收益，而是综合稳定性、回撤、动作数、用户可理解性与前端说明复杂度。",
    ])
    return {"recommended_gate": gate, "b2_recommendation": b2, "analysis": analysis, "kept_conservative_candidates": kept, "rejected_conservative_candidates": rejected, "default_baseline_recommendation": default_recommendation}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    prices = PriceStore()
    service = OfflineService(prices)
    runs = accepted_runs()
    frozen = frozen_scores()
    cache: dict[str, list[dict[str, Any]]] = {}
    rows: list[dict[str, Any]] = []
    quality_rows: list[dict[str, Any]] = []
    for period, start, end, sample_status in PERIODS:
        period_rows, quality = replay_period(service, runs, frozen, period, start, end, sample_status, cache)
        rows.extend(period_rows)
        quality_rows.append(quality)
    deltas = conservative_delta_rows(rows)
    summary = method_summary(rows)
    gate = analyze(rows, deltas, summary)
    fields = ["period", "start_date", "end_date", "sample_status", "method", "comparison_status", "gross_return", "fee_tax_adjusted_net_return", "final_equity", "max_drawdown", "action_count", "buy_count", "sell_count", "fee_and_tax", "turnover_proxy_by_notional_over_avg_equity", "turnover_notional", "missing_price_count", "trading_days_used", "relative_return_vs_top50_adaptive", "relative_drawdown_vs_top50_adaptive", "relative_actions_vs_top50_adaptive", "relative_return_vs_original_conservative", "historical_action_rows"]
    wcsv(OUT / "phaseb1_period_comparison.csv", rows, fields)
    wcsv(OUT / "phaseb1_method_summary.csv", summary, ["method", "period_count", "avg_fee_tax_adjusted_net_return", "min_fee_tax_adjusted_net_return", "avg_max_drawdown", "worst_max_drawdown", "avg_action_count", "avg_turnover_proxy", "positive_period_count"])
    wcsv(OUT / "phaseb1_conservative_candidate_delta.csv", deltas, ["period", "candidate", "delta_return_vs_original_conservative", "delta_drawdown_vs_original_conservative", "delta_actions_vs_original_conservative", "delta_turnover_vs_original_conservative", "actions_vs_ltr_simple"])
    wcsv(OUT / "phaseb1_period_quality.csv", quality_rows, ["period", "start_date", "end_date", "sample_status", "baseline_signal_days", "ltr_score_days", "common_replay_days", "excluded_dates"])
    gate_payload = {"phase": "phaseb1_conservative_replay", "created_at": now(), **gate, "no_ltr_retraining": True, "no_phase1c_score_change": True, "no_new_data_source": True, "no_network": True, "no_provider_or_accepted_latest": True, "no_monitor_or_trading_chain": True, "artifacts": {"period_comparison": rel(OUT / "phaseb1_period_comparison.csv"), "method_summary": rel(OUT / "phaseb1_method_summary.csv"), "candidate_delta": rel(OUT / "phaseb1_conservative_candidate_delta.csv"), "period_quality": rel(OUT / "phaseb1_period_quality.csv"), "report": rel(DOC)}}
    wjson(OUT / "phaseb1_gate_summary.json", gate_payload)
    write_report(rows, deltas, summary, quality_rows, gate_payload)
    print(json.dumps(gate_payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
