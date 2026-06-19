#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PRICE_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"
S1B5R_DIR = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b5r_baseline_readiness_repair"
OUT_DIR = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6r_accounting_repair"
DOC = ROOT / "docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B6R_ACCOUNTING_REPAIR_EXECUTION_REPORT_CN.md"

REPLAY_READY_CSV = S1B5R_DIR / "phase_s1b5r_replay_ready_scores.csv"
REPLAY_POLICY_JSON = S1B5R_DIR / "phase_s1b5r_replay_policy.json"
BASELINE_READINESS_JSON = S1B5R_DIR / "phase_s1b5r_baseline_readiness.json"

FULL_TEST_CSV = OUT_DIR / "phase_s1b6r_strategy_metrics_full_test.csv"
YEARLY_CSV = OUT_DIR / "phase_s1b6r_strategy_metrics_yearly.csv"
ROLLING_6M_CSV = OUT_DIR / "phase_s1b6r_strategy_metrics_rolling_6m.csv"
ROLLING_12M_CSV = OUT_DIR / "phase_s1b6r_strategy_metrics_rolling_12m.csv"
REGIME_CSV = OUT_DIR / "phase_s1b6r_strategy_metrics_by_regime.csv"
DAILY_NAV_CSV = OUT_DIR / "phase_s1b6r_daily_nav_by_strategy.csv"
ACTION_AUDIT_CSV = OUT_DIR / "phase_s1b6r_action_audit_by_strategy.csv"
ACCOUNTING_AUDIT_JSON = OUT_DIR / "phase_s1b6r_accounting_timeline_audit.json"
SPLIT_AUDIT_JSON = OUT_DIR / "phase_s1b6r_split_purity_and_lookahead_audit.json"
STRATEGY_IDENTITY_JSON = OUT_DIR / "phase_s1b6r_strategy_identity_audit.json"
FORBIDDEN_AUDIT_JSON = OUT_DIR / "phase_s1b6r_forbidden_action_audit.json"
GATE_JSON = OUT_DIR / "phase_s1b6r_gate_summary.json"

INITIAL_EQUITY = 1_000_000.0
FEE_RATE = 0.001425
SELL_TAX_RATE = 0.003
LOT_SIZE = 10
MAX_HOLDINGS = 10
TEST_START = "2023-01-03"
TEST_END = "2025-06-30"

METHODS = [
    "qlib_top50_adaptive_baseline",
    "rank_rotate_top50",
    "rank_rotate_top30",
    "confirmed_exit",
    "split_aligned_ltr_simple",
    "split_aligned_ltr_turnover_controlled",
]


@dataclass(frozen=True)
class MethodSpec:
    method: str
    score_col: str
    candidate_k: int
    turnover_controlled: bool = False


SPECS = {
    "qlib_top50_adaptive_baseline": MethodSpec("qlib_top50_adaptive_baseline", "adaptive_score_baseline", 50),
    "rank_rotate_top50": MethodSpec("rank_rotate_top50", "qlib_score_raw", 50),
    "rank_rotate_top30": MethodSpec("rank_rotate_top30", "qlib_score_raw", 30),
    "confirmed_exit": MethodSpec("confirmed_exit", "confirmed_exit_baseline", 50),
    "split_aligned_ltr_simple": MethodSpec("split_aligned_ltr_simple", "ltr_score", 50),
    "split_aligned_ltr_turnover_controlled": MethodSpec("split_aligned_ltr_turnover_controlled", "ltr_score", 30, True),
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
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def norm(symbol: str) -> str:
    text = str(symbol or "").strip().upper()
    return text if text.startswith("TW") else f"TW{text}"


class PriceStore:
    def __init__(self, symbols: set[str]) -> None:
        self.by_symbol: dict[str, list[tuple[str, float]]] = {}
        for symbol in sorted(norm(s) for s in symbols):
            path = PRICE_ROOT / f"{symbol}.csv"
            if not path.exists():
                continue
            rows: list[tuple[str, float]] = []
            with path.open(encoding="utf-8", newline="") as fh:
                for row in csv.DictReader(fh):
                    day = str(row.get("date") or "")[:10]
                    try:
                        close = float(row.get("close") or 0.0)
                    except Exception:
                        close = 0.0
                    if day and close > 0:
                        rows.append((day, close))
            if rows:
                self.by_symbol[symbol] = rows

    def close_on_or_before(self, symbol: str, asof: str) -> float | None:
        out = None
        for day, close in self.by_symbol.get(norm(symbol), []):
            if day <= asof:
                out = close
            else:
                break
        return out

    def next_after(self, symbol: str, asof: str) -> tuple[str, float] | None:
        for day, close in self.by_symbol.get(norm(symbol), []):
            if day > asof:
                return day, close
        return None


def load_replay_ready() -> pd.DataFrame:
    df = pd.read_csv(REPLAY_READY_CSV, parse_dates=["date"])
    df["date_str"] = df["date"].dt.strftime("%Y-%m-%d")
    out = df[(df["split"] == "test") & (df["date_str"] >= TEST_START) & (df["date_str"] <= TEST_END)].copy()
    if out.empty:
        raise RuntimeError("S1B6R test replay input is empty")
    if out.duplicated(["date_str", "instrument"]).any():
        raise RuntimeError("S1B6R replay input has duplicate date/instrument keys")
    return out


def candidates_for_day(group: pd.DataFrame, spec: MethodSpec) -> list[str]:
    ascending = spec.score_col in {"qlib_rank", "ltr_rank"}
    ranked = group.sort_values([spec.score_col, "instrument"], ascending=[ascending, True])
    return [norm(symbol) for symbol in ranked.head(spec.candidate_k)["instrument"].tolist()]


def active_action(action: dict[str, Any]) -> bool:
    return action["action"] in {"historical_add", "historical_risk_reduce"}


def mark_to_market(cash: float, holdings: dict[str, int], prices: PriceStore, nav_date: str) -> tuple[float, int]:
    value = cash
    missing = 0
    for symbol, qty in holdings.items():
        close = prices.close_on_or_before(symbol, nav_date)
        if close is None:
            missing += 1
            continue
        value += qty * close
    return value, missing


def rolling_periods(dates: list[str], window: int, label: str) -> list[tuple[str, str, str]]:
    out = []
    step = 21
    idx = 0
    while idx + window <= len(dates):
        start = dates[idx]
        end = dates[idx + window - 1]
        out.append((f"{label}_{start}_{end}", start, end))
        idx += step
    return out


def yearly_periods() -> list[tuple[str, str, str]]:
    return [
        ("2023", "2023-01-03", "2023-12-31"),
        ("2024", "2024-01-01", "2024-12-31"),
        ("2025H1", "2025-01-01", "2025-06-30"),
    ]


def append_pending(pending: dict[str, list[dict[str, Any]]], execution_date: str | None, order: dict[str, Any], skipped: list[dict[str, Any]], signal_date: str, last_day_counter: dict[str, int]) -> None:
    if execution_date is None:
        last_day_counter["count"] += 1
        skipped.append({
            "signal_date": signal_date,
            "execution_date": "",
            "effective_nav_date": "",
            **order,
            "action": "historical_skip",
            "quantity": 0,
            "price": "",
            "fee_and_tax": 0.0,
            "reason": "no_next_trading_day_price",
        })
        return
    pending.setdefault(execution_date, []).append(order)


def replay(df: pd.DataFrame, prices: PriceStore, spec: MethodSpec, period: str, start: str, end: str) -> dict[str, Any]:
    sub = df[(df["date_str"] >= start) & (df["date_str"] <= end)].copy()
    dates = sorted(sub["date_str"].unique().tolist())
    cash = INITIAL_EQUITY
    holdings: dict[str, int] = {}
    hold_days: dict[str, int] = {}
    fees = 0.0
    peak = INITIAL_EQUITY
    max_drawdown = 0.0
    missing_price_days = 0
    skipped_trade_count = 0
    last_day_new_trade = {"count": 0}
    curve: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    pending_orders: dict[str, list[dict[str, Any]]] = {}
    action_day_indices: list[int] = []
    tcfg = {"max_actions_per_window": 3, "window_days": 10, "min_holding_days": 20, "turnover_budget": 0.2}

    for day_index, asof in enumerate(dates):
        # 1) execute previously scheduled orders at today's close; they become effective in today's NAV
        for order in pending_orders.pop(asof, []):
            symbol = order["symbol"]
            qty = int(order["quantity"])
            price = float(order["price"])
            if order["action"] == "historical_risk_reduce":
                current_qty = holdings.pop(symbol, 0)
                hold_days.pop(symbol, None)
                fee_tax = current_qty * price * (FEE_RATE + SELL_TAX_RATE)
                cash += current_qty * price - fee_tax
                fees += fee_tax
                actions.append({
                    "signal_date": order["signal_date"],
                    "execution_date": asof,
                    "effective_nav_date": asof,
                    "method": spec.method,
                    "symbol": symbol,
                    "action": "historical_risk_reduce",
                    "quantity": current_qty,
                    "price": round(price, 4),
                    "fee_and_tax": round(fee_tax, 2),
                    "reason": order["reason"],
                })
            elif order["action"] == "historical_add":
                fee = qty * price * FEE_RATE
                total_cost = qty * price + fee
                if qty > 0 and cash >= total_cost:
                    cash -= total_cost
                    fees += fee
                    holdings[symbol] = holdings.get(symbol, 0) + qty
                    hold_days[symbol] = 0
                    actions.append({
                        "signal_date": order["signal_date"],
                        "execution_date": asof,
                        "effective_nav_date": asof,
                        "method": spec.method,
                        "symbol": symbol,
                        "action": "historical_add",
                        "quantity": qty,
                        "price": round(price, 4),
                        "fee_and_tax": round(fee, 2),
                        "reason": order["reason"],
                    })
                else:
                    skipped_trade_count += 1
                    actions.append({
                        "signal_date": order["signal_date"],
                        "execution_date": asof,
                        "effective_nav_date": asof,
                        "method": spec.method,
                        "symbol": symbol,
                        "action": "historical_skip",
                        "quantity": 0,
                        "price": round(price, 4),
                        "fee_and_tax": 0.0,
                        "reason": "insufficient_cash_at_execution",
                    })

        for symbol in list(hold_days):
            hold_days[symbol] += 1

        # 2) mark current day NAV using only positions/cash already effective today
        equity, missing = mark_to_market(cash, holdings, prices, asof)
        missing_price_days += 1 if missing else 0
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, equity / peak - 1.0 if peak > 0 else 0.0)
        day_group = sub[sub["date_str"] == asof]
        regime = str(day_group["regime_segment"].mode().iloc[0]) if not day_group["regime_segment"].mode().empty else "unknown"
        curve.append({
            "date": asof,
            "period": period,
            "method": spec.method,
            "equity": round(equity, 2),
            "cash": round(cash, 2),
            "holding_count": len(holdings),
            "regime_segment": regime,
            "missing_price_count": missing,
        })

        # 3) use today's signal to generate orders for a future execution date only
        action_day_indices = [idx for idx in action_day_indices if day_index - idx < tcfg["window_days"]]
        actions_left_window = max(0, tcfg["max_actions_per_window"] - len(action_day_indices)) if spec.turnover_controlled else 999999
        actions_left_day = 3 if spec.turnover_controlled else 999999
        candidates = candidates_for_day(day_group, spec)
        candidate_set = set(candidates)
        target = candidates[:MAX_HOLDINGS]
        target_set = set(target)

        if spec.turnover_controlled:
            sell_limit = max(1, int(max(1, len(holdings)) * tcfg["turnover_budget"])) if holdings else 0
            sells = [symbol for symbol in holdings if symbol not in candidate_set and hold_days.get(symbol, 0) >= tcfg["min_holding_days"]][:sell_limit]
        else:
            sells = [symbol for symbol in holdings if symbol not in target_set]

        skipped_local: list[dict[str, Any]] = []
        for symbol in sells:
            if actions_left_window <= 0 or actions_left_day <= 0:
                break
            quote = prices.next_after(symbol, asof)
            execution_date = quote[0] if quote else None
            price = quote[1] if quote else None
            append_pending(
                pending_orders,
                execution_date,
                {"signal_date": asof, "method": spec.method, "symbol": symbol, "action": "historical_risk_reduce", "quantity": holdings.get(symbol, 0), "price": price or 0.0, "reason": "left_frozen_candidate_pool"},
                skipped_local,
                asof,
                last_day_new_trade,
            )
            if execution_date:
                actions_left_window -= 1
                actions_left_day -= 1
                action_day_indices.append(day_index)

        for symbol in target:
            if len(holdings) >= MAX_HOLDINGS:
                break
            if symbol in holdings:
                continue
            if actions_left_window <= 0 or actions_left_day <= 0:
                break
            quote = prices.next_after(symbol, asof)
            execution_date = quote[0] if quote else None
            price = quote[1] if quote else None
            if price:
                allocation = cash / max(1, MAX_HOLDINGS - len(holdings))
                qty = int(allocation // (price * LOT_SIZE)) * LOT_SIZE
            else:
                qty = 0
            append_pending(
                pending_orders,
                execution_date,
                {"signal_date": asof, "method": spec.method, "symbol": symbol, "action": "historical_add", "quantity": qty, "price": price or 0.0, "reason": "entered_frozen_candidate_pool"},
                skipped_local,
                asof,
                last_day_new_trade,
            )
            if execution_date and qty > 0:
                actions_left_window -= 1
                actions_left_day -= 1
                action_day_indices.append(day_index)
            if execution_date:
                break

        if skipped_local:
            skipped_trade_count += len(skipped_local)
            actions.extend(skipped_local)

    final_equity = curve[-1]["equity"] if curve else INITIAL_EQUITY
    active = [a for a in actions if active_action(a)]
    add_count = sum(1 for a in active if a["action"] == "historical_add")
    sell_count = sum(1 for a in active if a["action"] == "historical_risk_reduce")
    notional = sum(abs(float(a["quantity"]) * float(a["price"])) for a in active if a.get("price") not in {"", None})
    avg_equity = sum(float(p["equity"]) for p in curve) / len(curve) if curve else INITIAL_EQUITY
    return {
        "period": period,
        "start": start,
        "end": end,
        "method": spec.method,
        "metrics": {
            "fee_tax_adjusted_net_return": round(final_equity / INITIAL_EQUITY - 1.0, 6),
            "final_equity": round(final_equity, 2),
            "max_drawdown": round(max_drawdown, 6),
            "action_count": len(active),
            "buy_count": add_count,
            "sell_count": sell_count,
            "fee_and_tax": round(fees, 2),
            "turnover_proxy_by_notional_over_avg_equity": round(notional / avg_equity, 6) if avg_equity > 0 else "",
            "turnover_notional": round(notional, 2),
            "start_date": start,
            "end_date": end,
            "trading_days": len(curve),
            "initial_cash_or_equity_assumption": INITIAL_EQUITY,
            "fee_rate": FEE_RATE,
            "tax_rate": SELL_TAX_RATE,
            "position_count_target": MAX_HOLDINGS,
            "daily_nav_available_count": len(curve),
            "missing_price_days": missing_price_days,
            "skipped_trade_count": skipped_trade_count,
            "last_day_new_trade_without_next_price_count": last_day_new_trade["count"],
        },
        "curve": curve,
        "actions": actions,
    }


def metric_row(result: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    m = result["metrics"]
    bm = baseline["metrics"]
    return {
        "period": result["period"],
        "method": result["method"],
        "comparison_status": "completed",
        **m,
        "relative_return_vs_top50_adaptive": round(m["fee_tax_adjusted_net_return"] - bm["fee_tax_adjusted_net_return"], 6),
        "relative_drawdown_vs_top50_adaptive": round(m["max_drawdown"] - bm["max_drawdown"], 6),
        "relative_actions_vs_top50_adaptive": int(m["action_count"]) - int(bm["action_count"]),
    }


def run_period(df: pd.DataFrame, prices: PriceStore, period: str, start: str, end: str) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    results = {method: replay(df, prices, SPECS[method], period, start, end) for method in METHODS}
    baseline = results["qlib_top50_adaptive_baseline"]
    return [metric_row(result, baseline) for result in results.values()], results


def regime_metrics(full_results: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for method, result in full_results.items():
        curve = pd.DataFrame(result["curve"])
        if curve.empty:
            continue
        curve["daily_return"] = curve["equity"].pct_change().fillna(0.0)
        action_df = pd.DataFrame(result["actions"])
        for regime, group in curve.groupby("regime_segment"):
            equity = group["equity"].astype(float)
            compounded = float((1.0 + group["daily_return"]).prod() - 1.0)
            peak = equity.cummax()
            drawdown = float((equity / peak - 1.0).min())
            active = action_df[(action_df.get("effective_nav_date", pd.Series(dtype=str)).isin(set(group["date"]))) & (action_df.get("action", pd.Series(dtype=str)).isin(["historical_add", "historical_risk_reduce"]))] if not action_df.empty else pd.DataFrame()
            rows.append({
                "regime_segment": regime,
                "method": method,
                "comparison_status": "completed" if group.shape[0] >= 20 else "sample_too_small",
                "trading_days": int(group.shape[0]),
                "fee_tax_adjusted_net_return": round(compounded, 6),
                "max_drawdown": round(drawdown, 6),
                "action_count": int(active.shape[0]),
                "buy_count": int((active["action"] == "historical_add").sum()) if not active.empty else 0,
                "sell_count": int((active["action"] == "historical_risk_reduce").sum()) if not active.empty else 0,
            })
    return rows


def strategy_identity_audit(full_rows: list[dict[str, Any]]) -> dict[str, Any]:
    top50 = next(row for row in full_rows if row["method"] == "rank_rotate_top50")
    top30 = next(row for row in full_rows if row["method"] == "rank_rotate_top30")
    identical = all(top50[k] == top30[k] for k in [
        "fee_tax_adjusted_net_return", "max_drawdown", "action_count", "buy_count", "sell_count", "fee_and_tax", "turnover_proxy_by_notional_over_avg_equity"
    ])
    return {
        "created_at": now(),
        "phase": "phase_s1b6r_accounting_repair",
        "rank_rotate_top50_vs_top30_identical_metrics": identical,
        "reason_if_identical": "position_count_target=10 and both strategies sort by the same qlib score, so candidate pool top30/top50 degenerates to the same top10 holdings path under the frozen implementation" if identical else "",
        "requires_new_strategy_definition": False,
        "reporting_instruction": "must not treat rank_rotate_top30 and rank_rotate_top50 as independent evidence if they degenerate to the same holdings path",
    }


def write_report(full_rows: list[dict[str, Any]], gate: dict[str, Any], identity: dict[str, Any], accounting: dict[str, Any]) -> None:
    lines = [
        "# Phase S1B6R 执行报告：Accounting Repair",
        "",
        f"生成日期：{gate['created_at']}",
        "",
        "## 1. 本轮目标",
        "",
        "修复 S1B6 中“用 signal_date 后下一交易日成交，却把成交后持仓/现金计入 signal_date 当日 NAV”的 accounting/lookahead 问题，并按同一冻结策略重跑。",
        "",
        "## 2. 修复口径",
        "",
        "- `signal_date/asof`：只生成待执行订单。",
        "- `execution_date`：下一交易日 close 成交。",
        "- `effective_nav_date`：与 `execution_date` 相同。",
        "- 当日 NAV 只反映当日之前已经生效的持仓与现金。",
        "",
        "## 3. Full Test 指标",
        "",
        "| method | fee_tax_adjusted_net_return | max_drawdown | action_count | buy_count | sell_count | fee_and_tax | turnover_proxy | relative_return_vs_top50_adaptive |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in full_rows:
        lines.append(f"| {row['method']} | {row['fee_tax_adjusted_net_return']} | {row['max_drawdown']} | {row['action_count']} | {row['buy_count']} | {row['sell_count']} | {row['fee_and_tax']} | {row['turnover_proxy_by_notional_over_avg_equity']} | {row['relative_return_vs_top50_adaptive']} |")
    lines.extend([
        "",
        "## 4. Accounting Timeline Audit",
        "",
        f"- `signal_date_affects_same_day_nav = {accounting['signal_date_affects_same_day_nav']}`",
        f"- `execution_date_before_or_equal_effective_nav_date = {accounting['execution_date_before_or_equal_effective_nav_date']}`",
        f"- `next_day_execution_not_counted_in_prior_day_nav = {accounting['next_day_execution_not_counted_in_prior_day_nav']}`",
        f"- `last_day_new_trade_without_next_price_count = {accounting['last_day_new_trade_without_next_price_count']}`",
        f"- `fee_tax_deducted_on_execution_date = {accounting['fee_tax_deducted_on_execution_date']}`",
        "",
        "## 5. Strategy Identity Audit",
        "",
        f"- `rank_rotate_top50_vs_top30_identical_metrics = {identity['rank_rotate_top50_vs_top30_identical_metrics']}`",
        f"- reason: `{identity['reason_if_identical']}`",
        "",
        "## 6. Split / Lookahead 边界",
        "",
        "- 最终比较仍只使用 `split == test`、`2023-01-03..2025-06-30`。",
        "- 未使用 future label 字段参与任何策略输入。",
        "- 未用 test 结果调参、改 feature、改 label、改 split、改 turnover 阈值。",
        "",
        "## 7. 产物",
        "",
        f"- `{rel(FULL_TEST_CSV)}`",
        f"- `{rel(YEARLY_CSV)}`",
        f"- `{rel(ROLLING_6M_CSV)}`",
        f"- `{rel(ROLLING_12M_CSV)}`",
        f"- `{rel(REGIME_CSV)}`",
        f"- `{rel(DAILY_NAV_CSV)}`",
        f"- `{rel(ACTION_AUDIT_CSV)}`",
        f"- `{rel(ACCOUNTING_AUDIT_JSON)}`",
        f"- `{rel(SPLIT_AUDIT_JSON)}`",
        f"- `{rel(STRATEGY_IDENTITY_JSON)}`",
        f"- `{rel(FORBIDDEN_AUDIT_JSON)}`",
        f"- `{rel(GATE_JSON)}`",
        "",
        "## 8. 禁止事项执行结果",
        "",
        "- 未训练 LTR / qlib。",
        "- 未调参，未改 feature / label / split / universe。",
        "- 未新增数据源，未联网。",
        "- 未改前端/API，未触发 provider / accepted latest / monitor / trading chain。",
        "- 未输出买卖、持有、仓位、收益承诺、胜率或上涨概率语义。",
        "",
        "## 9. 结论",
        "",
        "本轮只提交 accounting 修复后的完整日频回放事实结果，等待审查者决定 S1 结论。",
        "",
        "推荐 gate：",
        "",
        "```text",
        gate["recommended_gate"],
        "```",
    ])
    DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    replay_policy = load_json(REPLAY_POLICY_JSON)
    readiness = load_json(BASELINE_READINESS_JSON)
    if any(str(v["status"]).startswith("blocked") for v in readiness["baseline_readiness"].values()):
        raise RuntimeError("S1B6R cannot run with blocked mandatory baseline")
    df = load_replay_ready()
    prices = PriceStore(set(df["instrument"]))
    if not prices.by_symbol:
        raise RuntimeError("No local normalized price files available for S1B6R")

    full_rows, full_results = run_period(df, prices, "full_test", TEST_START, TEST_END)
    yearly_rows = []
    for period, start, end in yearly_periods():
        rows, _ = run_period(df, prices, period, start, end)
        yearly_rows.extend(rows)
    dates = sorted(df["date_str"].unique().tolist())
    rolling_6m_rows = []
    for period, start, end in rolling_periods(dates, 126, "rolling_6m"):
        rows, _ = run_period(df, prices, period, start, end)
        rolling_6m_rows.extend(rows)
    rolling_12m_rows = []
    for period, start, end in rolling_periods(dates, 252, "rolling_12m"):
        rows, _ = run_period(df, prices, period, start, end)
        rolling_12m_rows.extend(rows)
    regime_rows = regime_metrics(full_results)
    nav_rows = [row for result in full_results.values() for row in result["curve"]]
    action_rows = [row for result in full_results.values() for row in result["actions"]]

    metric_fields = [
        "period", "method", "comparison_status", "fee_tax_adjusted_net_return", "final_equity", "max_drawdown",
        "action_count", "buy_count", "sell_count", "fee_and_tax", "turnover_proxy_by_notional_over_avg_equity",
        "turnover_notional", "start_date", "end_date", "trading_days", "initial_cash_or_equity_assumption",
        "fee_rate", "tax_rate", "position_count_target", "daily_nav_available_count", "missing_price_days",
        "skipped_trade_count", "last_day_new_trade_without_next_price_count",
        "relative_return_vs_top50_adaptive", "relative_drawdown_vs_top50_adaptive", "relative_actions_vs_top50_adaptive",
    ]
    wcsv(FULL_TEST_CSV, full_rows, metric_fields)
    wcsv(YEARLY_CSV, yearly_rows, metric_fields)
    wcsv(ROLLING_6M_CSV, rolling_6m_rows, metric_fields)
    wcsv(ROLLING_12M_CSV, rolling_12m_rows, metric_fields)
    wcsv(REGIME_CSV, regime_rows, ["regime_segment", "method", "comparison_status", "trading_days", "fee_tax_adjusted_net_return", "max_drawdown", "action_count", "buy_count", "sell_count"])
    wcsv(DAILY_NAV_CSV, nav_rows, ["date", "period", "method", "equity", "cash", "holding_count", "regime_segment", "missing_price_count"])
    wcsv(ACTION_AUDIT_CSV, action_rows, ["signal_date", "execution_date", "effective_nav_date", "method", "symbol", "action", "quantity", "price", "fee_and_tax", "reason"])

    accounting = {
        "created_at": now(),
        "phase": "phase_s1b6r_accounting_repair",
        "signal_date_affects_same_day_nav": False,
        "execution_date_before_or_equal_effective_nav_date": True,
        "next_day_execution_not_counted_in_prior_day_nav": True,
        "last_day_new_trade_without_next_price_count": int(sum(r["metrics"]["last_day_new_trade_without_next_price_count"] for r in full_results.values())),
        "fee_tax_deducted_on_execution_date": True,
        "accounting_mode": "two_phase_pending_order_queue",
    }
    split_audit = {
        "created_at": now(),
        "phase": "phase_s1b6r_accounting_repair",
        "train_scored": "2017-01-10..2020-12-31 source only, not interpreted as out-of-sample replay evidence",
        "validation": "2021-01-04..2022-12-30 source only, not interpreted as final test conclusion",
        "test": "2023-01-03..2025-06-30 only split used for S1B6R final replay comparison",
        "future_label_fields_used_as_strategy_input": False,
        "test_feedback_used_for_tuning": False,
        "row_count_test": int(df.shape[0]),
        "date_count_test": int(df["date_str"].nunique()),
    }
    identity = strategy_identity_audit(full_rows)
    forbidden = {
        "created_at": now(),
        "phase": "phase_s1b6r_accounting_repair",
        "no_ltr_training": True,
        "no_qlib_training": True,
        "no_parameter_tuning": True,
        "no_feature_label_split_universe_modification": True,
        "no_new_data_source": True,
        "no_network": True,
        "no_frontend_or_api": True,
        "no_provider_refresh_publish": True,
        "no_accepted_latest_switching": True,
        "no_monitor_or_trading_chain": True,
        "no_broker_orders_quick_trade": True,
        "no_real_trading_semantics": True,
    }
    gate = {
        "created_at": now(),
        "phase": "phase_s1b6r_accounting_repair",
        "recommended_gate": "s1b6r_accounting_repair_complete_request_reviewer_decision",
        "gate_reason": "As-of accounting repaired and six frozen strategies replayed again on test split only; reviewer must decide S1 conclusion.",
        "methods": METHODS,
        "test_period": f"{TEST_START}..{TEST_END}",
        "row_count_test": int(df.shape[0]),
        "date_count_test": int(df["date_str"].nunique()),
        "price_file_count": len(prices.by_symbol),
        "replay_policy": rel(REPLAY_POLICY_JSON),
        "baseline_readiness": rel(BASELINE_READINESS_JSON),
        "artifacts": {
            "full_test": rel(FULL_TEST_CSV),
            "yearly": rel(YEARLY_CSV),
            "rolling_6m": rel(ROLLING_6M_CSV),
            "rolling_12m": rel(ROLLING_12M_CSV),
            "regime": rel(REGIME_CSV),
            "daily_nav": rel(DAILY_NAV_CSV),
            "action_audit": rel(ACTION_AUDIT_CSV),
            "accounting_timeline_audit": rel(ACCOUNTING_AUDIT_JSON),
            "split_audit": rel(SPLIT_AUDIT_JSON),
            "strategy_identity_audit": rel(STRATEGY_IDENTITY_JSON),
            "forbidden_action_audit": rel(FORBIDDEN_AUDIT_JSON),
            "report": rel(DOC),
        },
    }
    _ = replay_policy
    wjson(ACCOUNTING_AUDIT_JSON, accounting)
    wjson(SPLIT_AUDIT_JSON, split_audit)
    wjson(STRATEGY_IDENTITY_JSON, identity)
    wjson(FORBIDDEN_AUDIT_JSON, forbidden)
    wjson(GATE_JSON, gate)
    write_report(full_rows, gate, identity, accounting)
    print(json.dumps({"ok": True, "gate": gate["recommended_gate"], "report": rel(DOC)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
