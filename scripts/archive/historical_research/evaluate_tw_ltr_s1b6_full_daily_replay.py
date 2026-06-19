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
OUT_DIR = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6_full_daily_replay"
DOC = ROOT / "docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B6_FULL_DAILY_REPLAY_EXECUTION_REPORT_CN.md"

REPLAY_READY_CSV = S1B5R_DIR / "phase_s1b5r_replay_ready_scores.csv"
REPLAY_POLICY_JSON = S1B5R_DIR / "phase_s1b5r_replay_policy.json"
BASELINE_READINESS_JSON = S1B5R_DIR / "phase_s1b5r_baseline_readiness.json"

FULL_TEST_CSV = OUT_DIR / "phase_s1b6_strategy_metrics_full_test.csv"
YEARLY_CSV = OUT_DIR / "phase_s1b6_strategy_metrics_yearly.csv"
ROLLING_6M_CSV = OUT_DIR / "phase_s1b6_strategy_metrics_rolling_6m.csv"
ROLLING_12M_CSV = OUT_DIR / "phase_s1b6_strategy_metrics_rolling_12m.csv"
REGIME_CSV = OUT_DIR / "phase_s1b6_strategy_metrics_by_regime.csv"
DAILY_NAV_CSV = OUT_DIR / "phase_s1b6_daily_nav_by_strategy.csv"
ACTION_AUDIT_CSV = OUT_DIR / "phase_s1b6_action_audit_by_strategy.csv"
SPLIT_AUDIT_JSON = OUT_DIR / "phase_s1b6_split_purity_and_lookahead_audit.json"
FORBIDDEN_AUDIT_JSON = OUT_DIR / "phase_s1b6_forbidden_action_audit.json"
GATE_JSON = OUT_DIR / "phase_s1b6_gate_summary.json"

INITIAL_EQUITY = 1_000_000.0
FEE_RATE = 0.001425
SELL_TAX_RATE = 0.003
LOT_SIZE = 10
MAX_HOLDINGS = 10

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
        self.dates: set[str] = set()
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
                        self.dates.add(day)
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
    test = df[df["split"] == "test"].copy()
    test = test[(test["date_str"] >= "2023-01-03") & (test["date_str"] <= "2025-06-30")].copy()
    if test.empty:
        raise RuntimeError("S1B6 test replay input is empty")
    if test.duplicated(["date_str", "instrument"]).any():
        raise RuntimeError("S1B6 replay input has duplicate date/instrument keys")
    return test


def candidates_for_day(group: pd.DataFrame, spec: MethodSpec) -> list[str]:
    ascending = spec.score_col in {"qlib_rank", "ltr_rank"}
    ranked = group.sort_values([spec.score_col, "instrument"], ascending=[ascending, True])
    return [norm(symbol) for symbol in ranked.head(spec.candidate_k)["instrument"].tolist()]


def mark_to_market(cash: float, holdings: dict[str, int], prices: PriceStore, asof: str) -> tuple[float, int]:
    value = cash
    missing = 0
    for symbol, qty in holdings.items():
        close = prices.close_on_or_before(symbol, asof)
        if close is None:
            missing += 1
            continue
        value += qty * close
    return value, missing


def active_action(action: dict[str, Any]) -> bool:
    return action["action"] in {"historical_add", "historical_risk_reduce"}


def replay(df: pd.DataFrame, prices: PriceStore, spec: MethodSpec, period: str, start: str, end: str) -> dict[str, Any]:
    sub = df[(df["date_str"] >= start) & (df["date_str"] <= end)].copy()
    cash = INITIAL_EQUITY
    holdings: dict[str, int] = {}
    hold_days: dict[str, int] = {}
    actions: list[dict[str, Any]] = []
    curve: list[dict[str, Any]] = []
    fees = 0.0
    peak = INITIAL_EQUITY
    max_drawdown = 0.0
    missing_price_days = 0
    skipped_trade_count = 0
    action_day_indices: list[int] = []
    tcfg = {
        "max_actions_per_window": 3,
        "window_days": 10,
        "min_holding_days": 20,
        "turnover_budget": 0.2,
    }

    for day_index, (asof, group) in enumerate(sub.groupby("date_str", sort=True)):
        for symbol in list(hold_days):
            hold_days[symbol] += 1
        action_day_indices = [idx for idx in action_day_indices if day_index - idx < tcfg["window_days"]]
        actions_left_window = max(0, tcfg["max_actions_per_window"] - len(action_day_indices)) if spec.turnover_controlled else 999999
        actions_left_day = 3 if spec.turnover_controlled else 999999
        candidates = candidates_for_day(group, spec)
        candidate_set = set(candidates)
        target = candidates[:MAX_HOLDINGS]
        target_set = set(target)

        if spec.turnover_controlled:
            sell_limit = max(1, int(max(1, len(holdings)) * tcfg["turnover_budget"])) if holdings else 0
            sells = [
                symbol for symbol in holdings
                if symbol not in candidate_set and hold_days.get(symbol, 0) >= tcfg["min_holding_days"]
            ][:sell_limit]
        else:
            sells = [symbol for symbol in list(holdings) if symbol not in target_set]

        for symbol in list(sells):
            if actions_left_window <= 0 or actions_left_day <= 0:
                break
            quote = prices.next_after(symbol, asof)
            if quote is None:
                skipped_trade_count += 1
                actions.append({"asof": asof, "execution_date": "", "method": spec.method, "symbol": symbol, "action": "historical_skip", "quantity": 0, "price": "", "fee_and_tax": 0.0, "reason": "missing_next_close_for_sell"})
                continue
            execution_date, price = quote
            qty = holdings.pop(symbol)
            hold_days.pop(symbol, None)
            fee_tax = qty * price * (FEE_RATE + SELL_TAX_RATE)
            cash += qty * price - fee_tax
            fees += fee_tax
            actions_left_window -= 1
            actions_left_day -= 1
            action_day_indices.append(day_index)
            actions.append({"asof": asof, "execution_date": execution_date, "method": spec.method, "symbol": symbol, "action": "historical_risk_reduce", "quantity": qty, "price": round(price, 4), "fee_and_tax": round(fee_tax, 2), "reason": "left_frozen_candidate_pool"})

        for symbol in target:
            if len(holdings) >= MAX_HOLDINGS:
                break
            if symbol in holdings:
                continue
            if actions_left_window <= 0 or actions_left_day <= 0:
                break
            quote = prices.next_after(symbol, asof)
            if quote is None:
                skipped_trade_count += 1
                actions.append({"asof": asof, "execution_date": "", "method": spec.method, "symbol": symbol, "action": "historical_skip", "quantity": 0, "price": "", "fee_and_tax": 0.0, "reason": "missing_next_close_for_buy"})
                continue
            execution_date, price = quote
            allocation = cash / max(1, MAX_HOLDINGS - len(holdings))
            qty = int(allocation // (price * LOT_SIZE)) * LOT_SIZE
            fee = qty * price * FEE_RATE
            if qty <= 0 or cash < qty * price + fee:
                continue
            cash -= qty * price + fee
            fees += fee
            holdings[symbol] = holdings.get(symbol, 0) + qty
            hold_days[symbol] = 0
            actions_left_window -= 1
            actions_left_day -= 1
            action_day_indices.append(day_index)
            actions.append({"asof": asof, "execution_date": execution_date, "method": spec.method, "symbol": symbol, "action": "historical_add", "quantity": qty, "price": round(price, 4), "fee_and_tax": round(fee, 2), "reason": "entered_frozen_candidate_pool"})

        equity, missing = mark_to_market(cash, holdings, prices, asof)
        missing_price_days += 1 if missing else 0
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, equity / peak - 1.0 if peak > 0 else 0.0)
        regime = str(group["regime_segment"].mode().iloc[0]) if "regime_segment" in group and not group["regime_segment"].mode().empty else "unknown"
        curve.append(
            {
                "date": asof,
                "period": period,
                "method": spec.method,
                "equity": round(equity, 2),
                "cash": round(cash, 2),
                "holding_count": len(holdings),
                "regime_segment": regime,
                "missing_price_count": missing,
            }
        )

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


def yearly_periods() -> list[tuple[str, str, str]]:
    return [
        ("2023", "2023-01-03", "2023-12-31"),
        ("2024", "2024-01-01", "2024-12-31"),
        ("2025H1", "2025-01-01", "2025-06-30"),
    ]


def rolling_periods(dates: list[str], window: int, label: str) -> list[tuple[str, str, str]]:
    out = []
    step = 21
    if len(dates) < window:
        return out
    idx = 0
    while idx + window <= len(dates):
        start = dates[idx]
        end = dates[idx + window - 1]
        out.append((f"{label}_{start}_{end}", start, end))
        idx += step
    return out


def regime_metrics(full_results: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for method, result in full_results.items():
        curve = pd.DataFrame(result["curve"])
        if curve.empty:
            continue
        curve["daily_return"] = curve["equity"].pct_change().fillna(0.0)
        action_df = pd.DataFrame(result["actions"])
        for regime, group in curve.groupby("regime_segment"):
            if group.empty:
                continue
            equity = group["equity"].astype(float)
            compounded = float((1.0 + group["daily_return"]).prod() - 1.0)
            running_peak = equity.cummax()
            drawdown = (equity / running_peak - 1.0).min()
            if action_df.empty:
                actions = 0
                buys = 0
                sells = 0
            else:
                active = action_df[(action_df["asof"].isin(set(group["date"]))) & (action_df["action"].isin(["historical_add", "historical_risk_reduce"]))]
                actions = int(active.shape[0])
                buys = int((active["action"] == "historical_add").sum())
                sells = int((active["action"] == "historical_risk_reduce").sum())
            rows.append(
                {
                    "regime_segment": regime,
                    "method": method,
                    "comparison_status": "completed" if group.shape[0] >= 20 else "sample_too_small",
                    "trading_days": int(group.shape[0]),
                    "fee_tax_adjusted_net_return": round(compounded, 6),
                    "max_drawdown": round(float(drawdown), 6),
                    "action_count": actions,
                    "buy_count": buys,
                    "sell_count": sells,
                }
            )
    return rows


def run_period(df: pd.DataFrame, prices: PriceStore, period: str, start: str, end: str) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    results = {method: replay(df, prices, SPECS[method], period, start, end) for method in METHODS}
    baseline = results["qlib_top50_adaptive_baseline"]
    return [metric_row(result, baseline) for result in results.values()], results


def write_report(full_rows: list[dict[str, Any]], gate: dict[str, Any]) -> None:
    lines = [
        "# Phase S1B6 执行报告：Full Daily Replay",
        "",
        f"生成日期：{gate['created_at']}",
        "",
        "## 1. 本轮目标",
        "",
        "只用 S1B5R replay-ready scores 的 `split == test` 区间 `2023-01-03..2025-06-30`，对 6 个冻结策略做完整日频组合回放。",
        "",
        "## 2. 口径",
        "",
        "- 初始权益：`1,000,000`。",
        "- 手续费：`0.001425`。",
        "- 卖出税：`0.003`。",
        "- 目标持仓数：`10`。",
        "- 执行价：本地既有 normalized price 中 asof 后下一交易日 close。",
        "- 最终比较只使用 `split == test`。",
        "",
        "## 3. Full Test 指标",
        "",
        "| method | fee_tax_adjusted_net_return | max_drawdown | action_count | buy_count | sell_count | fee_and_tax | turnover_proxy | relative_return_vs_top50_adaptive |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in full_rows:
        lines.append(
            f"| {row['method']} | {row['fee_tax_adjusted_net_return']} | {row['max_drawdown']} | {row['action_count']} | {row['buy_count']} | {row['sell_count']} | {row['fee_and_tax']} | {row['turnover_proxy_by_notional_over_avg_equity']} | {row['relative_return_vs_top50_adaptive']} |"
        )
    lines.extend(
        [
            "",
            "## 4. Split / Lookahead 说明",
            "",
            "- `train_scored: 2017-01-10..2020-12-31` 只作训练期来源说明，不作为样本外结论。",
            "- `validation: 2021-01-04..2022-12-30` 只作旧窗口验证来源说明，不作为最终 test 结论。",
            "- `test: 2023-01-03..2025-06-30` 是本轮唯一用于样本外完整日频回放比较的区间。",
            "- replay-ready table 不含 future label 字段作为策略输入。",
            "",
            "## 5. 产物",
            "",
            f"- `{rel(FULL_TEST_CSV)}`",
            f"- `{rel(YEARLY_CSV)}`",
            f"- `{rel(ROLLING_6M_CSV)}`",
            f"- `{rel(ROLLING_12M_CSV)}`",
            f"- `{rel(REGIME_CSV)}`",
            f"- `{rel(DAILY_NAV_CSV)}`",
            f"- `{rel(ACTION_AUDIT_CSV)}`",
            f"- `{rel(SPLIT_AUDIT_JSON)}`",
            f"- `{rel(FORBIDDEN_AUDIT_JSON)}`",
            f"- `{rel(GATE_JSON)}`",
            "",
            "## 6. 禁止事项执行结果",
            "",
            "- 未训练 LTR / qlib。",
            "- 未调参，未改 feature / label / split / universe。",
            "- 未新增数据源，未联网。",
            "- 未改前端/API，未触发 provider / accepted latest / monitor / trading chain。",
            "- 未输出买卖、持有、仓位、收益承诺、胜率或上涨概率语义。",
            "",
            "## 7. 结论",
            "",
            "本轮只提交事实性完整日频回放结果，等待审查者决定 S1 结论。",
            "",
            "推荐 gate：",
            "",
            "```text",
            gate["recommended_gate"],
            "```",
        ]
    )
    DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    policy = load_json(REPLAY_POLICY_JSON)
    readiness = load_json(BASELINE_READINESS_JSON)
    if any(str(v["status"]).startswith("blocked") for v in readiness["baseline_readiness"].values()):
        raise RuntimeError("S1B6 cannot run with blocked mandatory baseline")
    df = load_replay_ready()
    prices = PriceStore(set(df["instrument"]))
    if not prices.by_symbol:
        raise RuntimeError("No local normalized price files available for S1B6")

    full_rows, full_results = run_period(df, prices, "full_test", "2023-01-03", "2025-06-30")
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
    nav_rows = [point for result in full_results.values() for point in result["curve"]]
    action_rows = [action for result in full_results.values() for action in result["actions"]]

    metric_fields = [
        "period", "method", "comparison_status", "fee_tax_adjusted_net_return", "final_equity", "max_drawdown",
        "action_count", "buy_count", "sell_count", "fee_and_tax", "turnover_proxy_by_notional_over_avg_equity",
        "turnover_notional", "start_date", "end_date", "trading_days", "initial_cash_or_equity_assumption",
        "fee_rate", "tax_rate", "position_count_target", "daily_nav_available_count", "missing_price_days",
        "skipped_trade_count", "relative_return_vs_top50_adaptive", "relative_drawdown_vs_top50_adaptive",
        "relative_actions_vs_top50_adaptive",
    ]
    wcsv(FULL_TEST_CSV, full_rows, metric_fields)
    wcsv(YEARLY_CSV, yearly_rows, metric_fields)
    wcsv(ROLLING_6M_CSV, rolling_6m_rows, metric_fields)
    wcsv(ROLLING_12M_CSV, rolling_12m_rows, metric_fields)
    wcsv(REGIME_CSV, regime_rows, ["regime_segment", "method", "comparison_status", "trading_days", "fee_tax_adjusted_net_return", "max_drawdown", "action_count", "buy_count", "sell_count"])
    wcsv(DAILY_NAV_CSV, nav_rows, ["date", "period", "method", "equity", "cash", "holding_count", "regime_segment", "missing_price_count"])
    wcsv(ACTION_AUDIT_CSV, action_rows, ["asof", "execution_date", "method", "symbol", "action", "quantity", "price", "fee_and_tax", "reason"])

    split_audit = {
        "created_at": now(),
        "phase": "phase_s1b6_full_daily_replay",
        "train_scored": "2017-01-10..2020-12-31 source only, not interpreted as out-of-sample replay evidence",
        "validation": "2021-01-04..2022-12-30 source only, not interpreted as final test conclusion",
        "test": "2023-01-03..2025-06-30 only split used for S1B6 final replay comparison",
        "input_rows_total": int(pd.read_csv(REPLAY_READY_CSV, usecols=["split"]).shape[0]),
        "test_rows_used": int(df.shape[0]),
        "future_label_fields_used_as_strategy_input": False,
        "test_feedback_used_for_tuning": False,
    }
    forbidden = {
        "created_at": now(),
        "phase": "phase_s1b6_full_daily_replay",
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
        "phase": "phase_s1b6_full_daily_replay",
        "recommended_gate": "s1b6_full_daily_replay_complete_request_reviewer_decision",
        "gate_reason": "Full daily replay completed for all six frozen strategies on test split only; reviewer must decide S1 conclusion.",
        "methods": METHODS,
        "test_period": "2023-01-03..2025-06-30",
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
            "split_audit": rel(SPLIT_AUDIT_JSON),
            "forbidden_action_audit": rel(FORBIDDEN_AUDIT_JSON),
            "report": rel(DOC),
        },
    }
    _ = policy
    wjson(SPLIT_AUDIT_JSON, split_audit)
    wjson(FORBIDDEN_AUDIT_JSON, forbidden)
    wjson(GATE_JSON, gate)
    write_report(full_rows, gate)
    print(json.dumps({"ok": True, "gate": gate["recommended_gate"], "report": rel(DOC)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
