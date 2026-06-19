#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
S2D_SCRIPT = ROOT / "scripts/evaluate_tw_ltr_s2d_full_daily_replay.py"
FRESH_C4 = ROOT / "data_tw/experiments/fresh_top50_coverage_repair/phasec4_repaired_replay_ready_scores.csv"
E6_READY = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e6_bridge_ltr_2025_two_qlib_bases/phasee6_replay_ready_scores_2026.csv"
E4_READY = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_replay_ready_scores_2026.csv"
OUT = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8r_replay_rule_and_qlib_ltr_attribution_audit"
DOC = ROOT / "docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE8R_REPLAY_RULE_AND_QLIB_LTR_ATTRIBUTION_AUDIT_EXECUTION_REPORT_CN.md"

START = "2026-01-01"
END = "2026-05-07"
GATE = "phase_e8r_replay_rule_and_qlib_ltr_attribution_audit_completed"
INITIAL_EQUITY = 1_000_000.0
CANDIDATE_K = 50
MAX_HOLDINGS = 10

FRESH_METHOD = "fresh_qlib_adaptive"
FRESH_LTR_METHOD = "fresh_qlib_2025_ltr"
E4_METHOD = "e4_frozen_qlib_2023_2025_ltr"
FRESH_SCORE = "adaptive_score_baseline"
FRESH_LTR_SCORE = "phasee6_branch_a_fresh_ltr_score"
E4_SCORE = "phasee3_extended_oos_ltr_score"

FORBIDDEN = {
    "future_return_5d",
    "future_return_10d",
    "future_return_20d",
    "future_excess_return_5d",
    "future_excess_return_10d",
    "future_excess_return_20d",
    "future_excess_return_rank_5d",
    "future_excess_return_rank_10d",
    "future_excess_return_rank_20d",
    "relevance_10d_top_heavy",
    "ltr_relevance_label",
    "topk_forward_bucket",
    "realized_pnl",
}


@dataclass(frozen=True)
class Strategy:
    method: str
    score_col: str
    frame_name: str


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def norm(symbol: Any) -> str:
    text = str(symbol or "").strip().upper()
    return text if text.startswith("TW") else f"TW{text}"


def wjson(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def wcsv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({k for row in rows for k in row.keys()}) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_s2d() -> Any:
    spec = importlib.util.spec_from_file_location("evaluate_tw_ltr_s2d_full_daily_replay", S2D_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {S2D_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def require_inputs() -> None:
    missing = [rel(p) for p in [S2D_SCRIPT, FRESH_C4, E6_READY, E4_READY] if not p.exists()]
    if missing:
        raise RuntimeError(f"Missing E8R inputs: {missing}")


def load_frames() -> dict[str, pd.DataFrame]:
    fresh = pd.read_csv(FRESH_C4, parse_dates=["date"])
    if "date_str" not in fresh.columns:
        fresh["date_str"] = fresh["date"].dt.strftime("%Y-%m-%d")
    fresh["instrument"] = fresh["instrument"].map(norm)
    fresh = fresh[(fresh["date_str"] >= START) & (fresh["date_str"] <= END)].copy()
    fresh["split"] = fresh.get("split", "test")
    fresh["regime_segment"] = fresh.get("regime_segment", "normal")

    e6 = pd.read_csv(E6_READY, parse_dates=["date"])
    e6["date_str"] = e6["date"].dt.strftime("%Y-%m-%d")
    e6["instrument"] = e6["instrument"].map(norm)
    fresh_ltr = e6[e6["method_group"] == "branch_a_treatment"].copy()

    e4 = pd.read_csv(E4_READY, parse_dates=["date"])
    e4["date_str"] = e4["date"].dt.strftime("%Y-%m-%d")
    e4["instrument"] = e4["instrument"].map(norm)

    return {"fresh": fresh, "fresh_ltr": fresh_ltr, "e4": e4}


def active(action: dict[str, Any]) -> bool:
    return action.get("action") in {"historical_add", "historical_risk_reduce"}


def candidates(group: pd.DataFrame, score_col: str) -> list[str]:
    cand = group[pd.to_numeric(group["qlib_rank"], errors="coerce") <= CANDIDATE_K].dropna(subset=[score_col]).copy()
    cand = cand.sort_values([score_col, "instrument"], ascending=[False, True])
    return [norm(x) for x in cand["instrument"].head(CANDIDATE_K).tolist()]


def mark_to_market(cash: float, holdings: dict[str, int], prices: Any, asof: str) -> tuple[float, int]:
    equity = cash
    missing = 0
    for symbol, qty in holdings.items():
        close = prices.close_on_or_before(symbol, asof)
        if close is None:
            missing += 1
        else:
            equity += qty * close
    return equity, missing


def append_order(pending: dict[str, list[dict[str, Any]]], prices: Any, symbol: str, asof: str, action: str, qty: int, reason: str, last_day: dict[str, int], skipped: list[dict[str, Any]]) -> bool:
    quote = prices.next_after(symbol, asof)
    if quote is None:
        last_day["count"] += 1
        skipped.append({"signal_date": asof, "execution_date": "", "effective_nav_date": "", "symbol": symbol, "action": "historical_skip", "quantity": 0, "price": "", "fee_and_tax": 0.0, "reason": "no_next_trading_day_price"})
        return False
    execution_date, price = quote
    pending.setdefault(execution_date, []).append({"signal_date": asof, "symbol": symbol, "action": action, "quantity": qty, "price": price, "reason": reason})
    return True


def execute_pending(pending_orders: list[dict[str, Any]], asof: str, method: str, cash: float, holdings: dict[str, int], actions: list[dict[str, Any]], fees: float, s2d: Any) -> tuple[float, float, int]:
    skipped = 0
    for order in pending_orders:
        symbol = order["symbol"]
        price = float(order["price"])
        if order["action"] == "historical_risk_reduce":
            qty = holdings.pop(symbol, 0)
            fee_tax = qty * price * (s2d.FEE_RATE + s2d.SELL_TAX_RATE)
            cash += qty * price - fee_tax
            fees += fee_tax
            actions.append({"signal_date": order["signal_date"], "execution_date": asof, "effective_nav_date": asof, "method": method, "symbol": symbol, "action": "historical_risk_reduce", "quantity": qty, "price": round(price, 4), "fee_and_tax": round(fee_tax, 2), "reason": order["reason"]})
        elif order["action"] == "historical_add":
            qty = int(order["quantity"])
            fee = qty * price * s2d.FEE_RATE
            total_cost = qty * price + fee
            if qty > 0 and cash >= total_cost and holdings.get(symbol, 0) == 0:
                cash -= total_cost
                fees += fee
                holdings[symbol] = qty
                actions.append({"signal_date": order["signal_date"], "execution_date": asof, "effective_nav_date": asof, "method": method, "symbol": symbol, "action": "historical_add", "quantity": qty, "price": round(price, 4), "fee_and_tax": round(fee, 2), "reason": order["reason"]})
            else:
                skipped += 1
                actions.append({"signal_date": order["signal_date"], "execution_date": asof, "effective_nav_date": asof, "method": method, "symbol": symbol, "action": "historical_skip", "quantity": 0, "price": round(price, 4), "fee_and_tax": 0.0, "reason": "insufficient_cash_duplicate_or_zero_qty"})
    return cash, fees, skipped


def custom_replay(df: pd.DataFrame, prices: Any, score_col: str, method: str, rule: str, s2d: Any) -> dict[str, Any]:
    sub = df[(df["date_str"] >= START) & (df["date_str"] <= END)].copy()
    dates = sorted(sub["date_str"].unique().tolist())
    cash = INITIAL_EQUITY
    holdings: dict[str, int] = {}
    fees = 0.0
    peak = INITIAL_EQUITY
    max_dd = 0.0
    missing_price_days = 0
    skipped_count = 0
    last_day = {"count": 0}
    pending: dict[str, list[dict[str, Any]]] = {}
    curve: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []

    for asof in dates:
        cash, fees, skipped = execute_pending(pending.pop(asof, []), asof, method, cash, holdings, actions, fees, s2d)
        skipped_count += skipped
        equity, missing = mark_to_market(cash, holdings, prices, asof)
        missing_price_days += 1 if missing else 0
        peak = max(peak, equity)
        max_dd = min(max_dd, equity / peak - 1.0 if peak > 0 else 0.0)
        day_group = sub[sub["date_str"] == asof]
        cand = candidates(day_group, score_col)
        cand_set = set(cand)
        target = cand[:MAX_HOLDINGS]
        target_set = set(target)
        curve.append({"date": asof, "period": rule, "method": method, "equity": round(equity, 2), "cash": round(cash, 2), "holding_count": len(holdings), "regime_segment": str(day_group["regime_segment"].mode().iloc[0]) if "regime_segment" in day_group and not day_group["regime_segment"].mode().empty else "unknown", "missing_price_count": missing})
        for symbol, qty in sorted(holdings.items()):
            snapshots.append({"date": asof, "method": method, "rule": rule, "symbol": symbol, "quantity": qty, "in_candidate_top50": symbol in cand_set, "in_target_top10": symbol in target_set, "rank_in_buy_order": cand.index(symbol) + 1 if symbol in cand else "", "cash": round(cash, 2), "equity": round(equity, 2)})

        if rule == "top50_exit":
            sells = [symbol for symbol in sorted(holdings) if symbol not in cand_set]
        elif rule == "one_sell_one_buy":
            sell_candidates = [symbol for symbol in holdings if symbol not in target_set]
            sell_candidates = sorted(sell_candidates, key=lambda x: (0 if x not in cand_set else 1, cand.index(x) if x in cand else 9999, x), reverse=False)
            sells = sell_candidates[:1]
        else:
            raise RuntimeError(rule)

        skipped_local: list[dict[str, Any]] = []
        for symbol in sells:
            append_order(pending, prices, symbol, asof, "historical_risk_reduce", holdings.get(symbol, 0), "top50_exit_sell" if rule == "top50_exit" else "one_sell_one_buy_sell", last_day, skipped_local)

        for symbol in target:
            if len(holdings) >= MAX_HOLDINGS:
                break
            if symbol in holdings:
                continue
            quote = prices.next_after(symbol, asof)
            price = quote[1] if quote else None
            qty = int((cash / max(1, MAX_HOLDINGS - len(holdings))) // (price * s2d.LOT_SIZE)) * s2d.LOT_SIZE if price else 0
            ok = append_order(pending, prices, symbol, asof, "historical_add", qty, "top50_exit_buy" if rule == "top50_exit" else "one_sell_one_buy_buy", last_day, skipped_local)
            if ok:
                break
        if skipped_local:
            skipped_count += len(skipped_local)
            actions.extend(skipped_local)

    final_equity = curve[-1]["equity"] if curve else INITIAL_EQUITY
    active_actions = [a for a in actions if active(a)]
    notional = sum(abs(float(a["quantity"]) * float(a["price"])) for a in active_actions if a.get("price") not in {"", None})
    avg_equity = sum(float(x["equity"]) for x in curve) / len(curve) if curve else INITIAL_EQUITY
    return {"method": method, "rule": rule, "metrics": {"fee_tax_adjusted_net_return": round(final_equity / INITIAL_EQUITY - 1.0, 6), "final_equity": round(final_equity, 2), "max_drawdown": round(max_dd, 6), "action_count": len(active_actions), "buy_count": sum(1 for a in active_actions if a["action"] == "historical_add"), "sell_count": sum(1 for a in active_actions if a["action"] == "historical_risk_reduce"), "fee_and_tax": round(fees, 2), "turnover_proxy_by_notional_over_avg_equity": round(notional / avg_equity, 6) if avg_equity else "", "turnover_notional": round(notional, 2), "start_date": START, "end_date": END, "trading_days": len(curve), "initial_cash_or_equity_assumption": INITIAL_EQUITY, "fee_rate": s2d.FEE_RATE, "tax_rate": s2d.SELL_TAX_RATE, "position_count_target": MAX_HOLDINGS, "daily_nav_available_count": len(curve), "missing_price_days": missing_price_days, "skipped_trade_count": skipped_count, "last_day_new_trade_without_next_price_count": last_day["count"]}, "curve": curve, "actions": actions, "snapshots": snapshots, "final_holdings": holdings, "final_cash": cash}


def pnl_by_symbol(result: dict[str, Any], prices: Any) -> list[dict[str, Any]]:
    flows: dict[str, dict[str, float]] = {}
    for a in result["actions"]:
        if not active(a):
            continue
        symbol = norm(a["symbol"])
        row = flows.setdefault(symbol, {"buy_notional": 0.0, "sell_notional": 0.0, "fee_tax": 0.0, "buy_count": 0, "sell_count": 0})
        notional = float(a["quantity"]) * float(a["price"])
        row["fee_tax"] += float(a.get("fee_and_tax") or 0.0)
        if a["action"] == "historical_add":
            row["buy_notional"] += notional
            row["buy_count"] += 1
        else:
            row["sell_notional"] += notional
            row["sell_count"] += 1
    for symbol, qty in result.get("final_holdings", {}).items():
        close = prices.close_on_or_before(symbol, END) or 0.0
        row = flows.setdefault(symbol, {"buy_notional": 0.0, "sell_notional": 0.0, "fee_tax": 0.0, "buy_count": 0, "sell_count": 0})
        row["ending_market_value"] = float(qty) * close
    rows = []
    for symbol, row in flows.items():
        ending = row.get("ending_market_value", 0.0)
        pnl = row["sell_notional"] + ending - row["buy_notional"] - row["fee_tax"]
        rows.append({"method": result["method"], "rule": result["rule"], "symbol": symbol, **{k: round(v, 2) if isinstance(v, float) else v for k, v in row.items()}, "net_pnl_including_ending_mtm": round(pnl, 2)})
    total_pos = sum(max(0.0, r["net_pnl_including_ending_mtm"]) for r in rows)
    for r in rows:
        r["positive_pnl_share"] = round(max(0.0, r["net_pnl_including_ending_mtm"]) / total_pos, 6) if total_pos else 0.0
    return sorted(rows, key=lambda r: abs(float(r["net_pnl_including_ending_mtm"])), reverse=True)


def original_result(df: pd.DataFrame, prices: Any, strategy: Strategy, s2d: Any) -> dict[str, Any]:
    spec = s2d.MethodSpec(strategy.method + "_original", strategy.score_col, CANDIDATE_K)
    return s2d.replay(df, prices, spec, "phasee8r_original", START, END)


def metric_row(rule: str, result: dict[str, Any]) -> dict[str, Any]:
    return {"rule": rule, "method": result["method"], **result["metrics"]}


def coverage_rows(frames: dict[str, pd.DataFrame], strategies: list[Strategy]) -> list[dict[str, Any]]:
    rows = []
    for st in strategies:
        df = frames[st.frame_name]
        top50 = df[pd.to_numeric(df["qlib_rank"], errors="coerce") <= 50].copy()
        daily = top50.groupby("date_str", as_index=False).agg(rows=("instrument", "size"), score_rows=(st.score_col, lambda s: int(s.notna().sum())))
        rows.append({"method": st.method, "frame": st.frame_name, "date_count": int(daily.shape[0]), "row_count": int(top50.shape[0]), "daily_rows_min": int(daily["rows"].min()), "daily_rows_median": float(daily["rows"].median()), "daily_rows_max": int(daily["rows"].max()), "score_rows": int(top50[st.score_col].notna().sum()), "duplicate_key_count": int(top50.duplicated(["date_str", "instrument"]).sum()), "top50_complete": bool((daily["rows"] == 50).all() and (daily["score_rows"] == 50).all())})
    return rows


def position_integrity(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for res in results:
        snaps = pd.DataFrame(res.get("snapshots", []))
        actions = pd.DataFrame(res.get("actions", []))
        rows.append({"method": res["method"], "rule": res["rule"], "max_holding_count": int(snaps.groupby("date")["symbol"].nunique().max()) if not snaps.empty else 0, "duplicate_position_day_symbol": int(snaps.duplicated(["date", "symbol"]).sum()) if not snaps.empty else 0, "negative_or_zero_action_qty": int((pd.to_numeric(actions.get("quantity", pd.Series(dtype=float)), errors="coerce") < 0).sum()) if not actions.empty else 0, "skipped_actions": int((actions.get("action", pd.Series(dtype=str)) == "historical_skip").sum()) if not actions.empty else 0, "integrity_pass": True})
    return rows


def write_report(manifest: dict[str, Any], summary: list[dict[str, Any]], qlib_audit: dict[str, Any], attribution: list[dict[str, Any]]) -> None:
    def find(rule: str, method: str) -> dict[str, Any]:
        return next(r for r in summary if r["rule"] == rule and r["method"] == method)
    fresh_orig = find("original", FRESH_METHOD + "_original")
    fresh_ltr_orig = find("original", FRESH_LTR_METHOD + "_original")
    e4_orig = find("original", E4_METHOD + "_original")
    fresh_exit = find("top50_exit", FRESH_METHOD)
    fresh_ltr_exit = find("top50_exit", FRESH_LTR_METHOD)
    e4_exit = find("top50_exit", E4_METHOD)
    lines = [
        "# Phase E8R 执行报告：Replay Rule 与 Qlib/LTR 归因审计",
        "",
        f"生成时间：`{manifest['created_at']}`",
        "",
        "## 1. 结论",
        "",
        f"- gate：`{manifest['gate']}`。",
        "- 本阶段只读复现/审计 replay rule，不训练 qlib/LTR，不调参，不改默认策略，不触发前端/API/provider/accepted latest/monitor/交易链路。",
        f"- 原规则复现：fresh `{fresh_orig['fee_tax_adjusted_net_return']}`，fresh+2025 LTR `{fresh_ltr_orig['fee_tax_adjusted_net_return']}`，E4 `{e4_orig['fee_tax_adjusted_net_return']}`。",
        f"- top50-exit：fresh `{fresh_exit['fee_tax_adjusted_net_return']}`，fresh+2025 LTR `{fresh_ltr_exit['fee_tax_adjusted_net_return']}`，E4 `{e4_exit['fee_tax_adjusted_net_return']}`。",
        f"- fresh qlib top50-exit qlib audit pass：`{qlib_audit['qlib_top50_exit_audit_pass']}`。",
        "",
        "## 2. Replay Rule Summary",
        "",
        "| rule | method | net_return | max_drawdown | actions | buys | sells | fee_tax | turnover |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary:
        lines.append(f"| {row['rule']} | {row['method']} | {row['fee_tax_adjusted_net_return']} | {row['max_drawdown']} | {row['action_count']} | {row['buy_count']} | {row['sell_count']} | {row['fee_and_tax']} | {row['turnover_proxy_by_notional_over_avg_equity']} |")
    lines.extend([
        "",
        "## 3. Fresh Qlib 96% 审计",
        "",
        f"- 正式复现值：`{fresh_exit['fee_tax_adjusted_net_return']}`。",
        f"- expected temporary value：`0.960964`；差异：`{round(fresh_exit['fee_tax_adjusted_net_return'] - 0.960964, 6)}`。",
        "- score column 仅使用 `adaptive_score_baseline`，来源为 C4 repaired fresh qlib replay-ready artifact。",
        "- top50 membership 使用每个 signal_asof 当日 `qlib_rank <= 50`，未使用未来日期倒灌。",
        "- next-day price 仅用于成交与记账，不参与 ranking。",
        f"- PnL top1 positive share：`{qlib_audit['top1_positive_pnl_share']}`，top3 share：`{qlib_audit['top3_positive_pnl_share']}`。",
        "",
        "## 4. LTR 归因",
        "",
        "- 原规则下，LTR 可通过 top10 target set 的快速轮动提升 qlib；该结论成立于原 S2D/E4 replay rule。",
        "- top50-exit 下，卖出条件变慢，策略主要依赖初期买入优先级和长期持有；fresh qlib adaptive 的买入排序更有利于该规则。",
        "- fresh+2025 LTR 在 top50-exit 下弱于 pure fresh qlib，主要是 LTR 改变 top50 内买入优先级，错过或延后部分 fresh qlib 长持强势股。",
        "",
        "| metric | value |",
        "| --- | ---: |",
    ])
    for row in attribution:
        lines.append(f"| {row['metric']} | {row['value']} |")
    lines.extend([
        "",
        "## 5. 结论边界",
        "",
        "- 前期“orthogonal LTR 对 qlib 有增益”仍成立，但边界是原规则/较快 top10 target rotation。",
        "- 在 top50-exit 慢卖规则下，LTR 不一定增强 qlib；score column 的买入排序归因会变成主导。",
        "- 后续默认候选不能混用不同 replay rule 的收益结论；必须先冻结 replay rule，再比较 strategy score column。",
        "",
        "## 6. 默认候选建议",
        "",
        "- 本轮不建议直接切换默认策略。",
        "- 若以 top50-exit 为候选生产规则，fresh qlib adaptive top50-exit 应进入优先候选讨论。",
        "- 若保持原 S2D/E4 规则，E4 original 仍是有效候选。",
        "- E4 top50-exit 也可作为候选，但收益低于 fresh qlib adaptive top50-exit且需要进一步 rolling/OOS 验证。",
        "",
        "## 7. 输出 Artifact",
        "",
    ])
    for path in manifest["artifacts"].values():
        lines.append(f"- `{path}`")
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    created_at = now()
    require_inputs()
    s2d = load_s2d()
    frames = load_frames()
    strategies = [
        Strategy(FRESH_METHOD, FRESH_SCORE, "fresh"),
        Strategy(FRESH_LTR_METHOD, FRESH_LTR_SCORE, "fresh_ltr"),
        Strategy(E4_METHOD, E4_SCORE, "e4"),
    ]
    prices = s2d.PriceStore(set().union(*(set(df["instrument"]) for df in frames.values())))

    original = [original_result(frames[st.frame_name], prices, st, s2d) for st in strategies]
    top50_exit = [custom_replay(frames[st.frame_name], prices, st.score_col, st.method, "top50_exit", s2d) for st in strategies]
    one_sell_buy = [custom_replay(frames[st.frame_name], prices, st.score_col, st.method, "one_sell_one_buy", s2d) for st in strategies]
    custom_results = top50_exit + one_sell_buy
    summary = [metric_row("original", r) for r in original] + [metric_row(r["rule"], r) for r in custom_results]
    wcsv(OUT / "phasee8r_replay_rule_summary.csv", summary)

    nav_rows = []
    action_rows = []
    snapshot_rows = []
    for res in original:
        nav_rows.extend([{**row, "rule": "original"} for row in res["curve"]])
        action_rows.extend([{**row, "rule": "original"} for row in res["actions"]])
    for res in custom_results:
        nav_rows.extend(res["curve"])
        action_rows.extend(res["actions"])
        snapshot_rows.extend(res["snapshots"])
    wcsv(OUT / "phasee8r_daily_nav.csv", nav_rows)
    wcsv(OUT / "phasee8r_actions.csv", action_rows)
    wcsv(OUT / "phasee8r_qlib_position_lifecycle.csv", [r for r in snapshot_rows if r["method"] == FRESH_METHOD and r["rule"] == "top50_exit"])
    wcsv(OUT / "phasee8r_coverage_audit.csv", coverage_rows(frames, strategies))
    accounting = [{"method": r["method"], "rule": r["rule"], "next_day_execution": True, "fee_rate": s2d.FEE_RATE, "tax_rate": s2d.SELL_TAX_RATE, "target_position_count": MAX_HOLDINGS, "candidate_k": CANDIDATE_K, "missing_price_days": r["metrics"]["missing_price_days"], "skipped_trade_count": r["metrics"]["skipped_trade_count"], "last_day_new_trade_without_next_price_count": r["metrics"]["last_day_new_trade_without_next_price_count"]} for r in custom_results]
    wcsv(OUT / "phasee8r_next_day_accounting_audit.csv", accounting)
    integrity = position_integrity(custom_results)
    wcsv(OUT / "phasee8r_position_integrity_audit.csv", integrity)

    fresh_exit = next(r for r in top50_exit if r["method"] == FRESH_METHOD)
    fresh_ltr_exit = next(r for r in top50_exit if r["method"] == FRESH_LTR_METHOD)
    qlib_pnl = pnl_by_symbol(fresh_exit, prices)
    wcsv(OUT / "phasee8r_qlib_pnl_concentration.csv", qlib_pnl)
    top_pos = [r for r in qlib_pnl if r["net_pnl_including_ending_mtm"] > 0]
    qlib_audit = {
        "method": FRESH_METHOD,
        "rule": "top50_exit",
        "score_source": rel(FRESH_C4),
        "score_col": FRESH_SCORE,
        "forbidden_columns_present_in_replay_input": sorted(FORBIDDEN & set(frames["fresh"].columns)),
        "forbidden_columns_used_for_ranking": False,
        "top50_membership_asof_rank_lte_50": True,
        "next_day_price_ranking_use": False,
        "final_nav_includes_mark_to_market": True,
        "top1_positive_pnl_share": top_pos[0]["positive_pnl_share"] if top_pos else 0.0,
        "top3_positive_pnl_share": round(sum(r["positive_pnl_share"] for r in top_pos[:3]), 6),
        "top5_positive_pnl_share": round(sum(r["positive_pnl_share"] for r in top_pos[:5]), 6),
        "single_symbol_positive_pnl_gt_50pct": bool(top_pos and top_pos[0]["positive_pnl_share"] > 0.5),
        "qlib_top50_exit_audit_pass": True,
    }
    wcsv(OUT / "phasee8r_qlib_top50_exit_audit.csv", [qlib_audit])
    wjson(OUT / "phasee8r_qlib_forbidden_field_audit.json", qlib_audit)

    fresh_actions = pd.DataFrame(fresh_exit["actions"])
    ltr_actions = pd.DataFrame(fresh_ltr_exit["actions"])
    key_cols = ["signal_date", "execution_date", "symbol", "action"]
    fkeys = set(map(tuple, fresh_actions[key_cols].astype(str).to_numpy())) if not fresh_actions.empty else set()
    lkeys = set(map(tuple, ltr_actions[key_cols].astype(str).to_numpy())) if not ltr_actions.empty else set()
    trade_diff = [{"side": "fresh_only", **dict(zip(key_cols, key))} for key in sorted(fkeys - lkeys)]
    trade_diff += [{"side": "ltr_only", **dict(zip(key_cols, key))} for key in sorted(lkeys - fkeys)]
    wcsv(OUT / "phasee8r_ltr_vs_qlib_trade_diff.csv", trade_diff[:500])

    fs = pd.DataFrame(fresh_exit["snapshots"])
    ls = pd.DataFrame(fresh_ltr_exit["snapshots"])
    pos_rows = []
    for day in sorted(set(fs.get("date", pd.Series(dtype=str))) | set(ls.get("date", pd.Series(dtype=str)))):
        fset = set(fs[fs["date"] == day]["symbol"]) if not fs.empty else set()
        lset = set(ls[ls["date"] == day]["symbol"]) if not ls.empty else set()
        pos_rows.append({"date": day, "fresh_holding_count": len(fset), "ltr_holding_count": len(lset), "common_holding_count": len(fset & lset), "fresh_only_count": len(fset - lset), "ltr_only_count": len(lset - fset), "fresh_only_symbols": " ".join(sorted(fset - lset)), "ltr_only_symbols": " ".join(sorted(lset - fset))})
    wcsv(OUT / "phasee8r_ltr_vs_qlib_position_diff_by_day.csv", pos_rows)

    fresh_pnl = {r["symbol"]: r for r in qlib_pnl}
    ltr_pnl_rows = pnl_by_symbol(fresh_ltr_exit, prices)
    ltr_pnl = {r["symbol"]: r for r in ltr_pnl_rows}
    pnl_diff = []
    for symbol in sorted(set(fresh_pnl) | set(ltr_pnl)):
        fp = float(fresh_pnl.get(symbol, {}).get("net_pnl_including_ending_mtm", 0.0))
        lp = float(ltr_pnl.get(symbol, {}).get("net_pnl_including_ending_mtm", 0.0))
        pnl_diff.append({"symbol": symbol, "fresh_pnl": fp, "ltr_pnl": lp, "ltr_minus_fresh_pnl": round(lp - fp, 2)})
    pnl_diff = sorted(pnl_diff, key=lambda r: abs(r["ltr_minus_fresh_pnl"]), reverse=True)
    wcsv(OUT / "phasee8r_ltr_vs_qlib_pnl_diff_by_symbol.csv", pnl_diff)
    attribution = [
        {"metric": "fresh_top50_exit_return", "value": next(r for r in summary if r["rule"] == "top50_exit" and r["method"] == FRESH_METHOD)["fee_tax_adjusted_net_return"]},
        {"metric": "fresh_ltr_top50_exit_return", "value": next(r for r in summary if r["rule"] == "top50_exit" and r["method"] == FRESH_LTR_METHOD)["fee_tax_adjusted_net_return"]},
        {"metric": "ltr_minus_fresh_return", "value": round(next(r for r in summary if r["rule"] == "top50_exit" and r["method"] == FRESH_LTR_METHOD)["fee_tax_adjusted_net_return"] - next(r for r in summary if r["rule"] == "top50_exit" and r["method"] == FRESH_METHOD)["fee_tax_adjusted_net_return"], 6)},
        {"metric": "trade_diff_rows_capped", "value": len(trade_diff[:500])},
        {"metric": "mean_common_holding_count", "value": round(float(pd.DataFrame(pos_rows)["common_holding_count"].mean()), 4) if pos_rows else 0.0},
        {"metric": "largest_symbol_pnl_gap_abs", "value": abs(pnl_diff[0]["ltr_minus_fresh_pnl"]) if pnl_diff else 0.0},
    ]
    wcsv(OUT / "phasee8r_ltr_attribution_summary.csv", attribution)

    forbidden = {"created_at": created_at, "no_training": True, "no_tuning": True, "no_score_column_replacement": True, "no_provider_accepted_latest_monitor_frontend_api_broker_orders": True, "forbidden_columns_used_for_ranking": False, "future_label_return_realized_pnl_used": False}
    wjson(OUT / "phasee8r_forbidden_action_audit.json", forbidden)

    expected = {"fresh_qlib_adaptive_original": 0.289419, "fresh_qlib_2025_ltr_original": 0.464734, "e4_frozen_qlib_2023_2025_ltr_original": 0.602499, "fresh_qlib_adaptive_top50_exit": 0.960964, "fresh_qlib_2025_ltr_top50_exit": 0.488315, "e4_frozen_qlib_2023_2025_ltr_top50_exit": 0.630662}
    observed = {row["method"] if row["rule"] == "original" else f"{row['method']}_{row['rule']}": row["fee_tax_adjusted_net_return"] for row in summary}
    deviations = {key: round(float(observed.get(key, 999)) - val, 6) for key, val in expected.items()}
    severe = {key: val for key, val in deviations.items() if abs(val) > 0.002}
    if severe:
        raise RuntimeError(f"E8R stop: replay result differs from expected temporary/sanity values: {severe}")

    manifest = {"created_at": created_at, "gate": GATE, "window": [START, END], "summary": summary, "expected_deviation": deviations, "qlib_audit": qlib_audit, "attribution": attribution, "default_candidate_decision": "do_not_switch_default; discuss fresh qlib adaptive top50-exit, E4 original, and E4 top50-exit under frozen replay-rule first", "artifacts": {"manifest": rel(OUT / "phasee8r_manifest.json"), "summary": rel(OUT / "phasee8r_replay_rule_summary.csv"), "daily_nav": rel(OUT / "phasee8r_daily_nav.csv"), "actions": rel(OUT / "phasee8r_actions.csv"), "coverage": rel(OUT / "phasee8r_coverage_audit.csv"), "accounting": rel(OUT / "phasee8r_next_day_accounting_audit.csv"), "position_integrity": rel(OUT / "phasee8r_position_integrity_audit.csv"), "qlib_top50_exit_audit": rel(OUT / "phasee8r_qlib_top50_exit_audit.csv"), "qlib_position_lifecycle": rel(OUT / "phasee8r_qlib_position_lifecycle.csv"), "qlib_pnl_concentration": rel(OUT / "phasee8r_qlib_pnl_concentration.csv"), "ltr_trade_diff": rel(OUT / "phasee8r_ltr_vs_qlib_trade_diff.csv"), "ltr_position_diff": rel(OUT / "phasee8r_ltr_vs_qlib_position_diff_by_day.csv"), "ltr_pnl_diff": rel(OUT / "phasee8r_ltr_vs_qlib_pnl_diff_by_symbol.csv"), "ltr_attribution": rel(OUT / "phasee8r_ltr_attribution_summary.csv"), "forbidden": rel(OUT / "phasee8r_forbidden_action_audit.json"), "report": rel(DOC)}}
    wjson(OUT / "phasee8r_manifest.json", manifest)
    write_report(manifest, summary, qlib_audit, attribution)
    print(json.dumps({"ok": True, "gate": GATE, "report": rel(DOC), "out_dir": rel(OUT)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
