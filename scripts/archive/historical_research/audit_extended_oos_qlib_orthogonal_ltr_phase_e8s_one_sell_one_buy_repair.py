#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
E8R_SCRIPT = ROOT / "scripts/audit_extended_oos_qlib_orthogonal_ltr_phase_e8r_replay_rule_attribution.py"
OUT = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8s_one_sell_one_buy_repair_and_anomaly_attribution"
DOC = ROOT / "docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE8S_ONE_SELL_ONE_BUY_REPAIR_AND_ANOMALY_ATTRIBUTION_EXECUTION_REPORT_CN.md"

START = "2026-01-01"
END = "2026-05-07"
GATE = "phase_e8s_one_sell_one_buy_repair_and_anomaly_attribution_completed"


def load_e8r() -> Any:
    spec = importlib.util.spec_from_file_location("phasee8r", E8R_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {E8R_SCRIPT}")
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


def wjson(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def wcsv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    import csv
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({k for row in rows for k in row.keys()}) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def price_return_to_end(prices: Any, symbol: str, asof: str, e8r: Any) -> float | str:
    quote = prices.next_after(symbol, asof)
    if quote is None:
        return ""
    _, entry = quote
    end_px = prices.close_on_or_before(symbol, END)
    if not end_px or not entry:
        return ""
    return round(end_px / entry - 1.0, 6)


def replay_one_sell_one_buy(df: pd.DataFrame, prices: Any, score_col: str, method: str, mode: str, s2d: Any, e8r: Any) -> dict[str, Any]:
    sub = df[(df["date_str"] >= START) & (df["date_str"] <= END)].copy()
    dates = sorted(sub["date_str"].unique().tolist())
    cash = e8r.INITIAL_EQUITY
    holdings: dict[str, int] = {}
    fees = 0.0
    peak = e8r.INITIAL_EQUITY
    max_dd = 0.0
    pending: dict[str, list[dict[str, Any]]] = {}
    curve: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []
    sell_decisions: list[dict[str, Any]] = []
    skipped_count = 0
    missing_price_days = 0
    last_day = {"count": 0}

    for asof in dates:
        cash, fees, skipped = e8r.execute_pending(pending.pop(asof, []), asof, method, cash, holdings, actions, fees, s2d)
        skipped_count += skipped
        equity, missing = e8r.mark_to_market(cash, holdings, prices, asof)
        missing_price_days += 1 if missing else 0
        peak = max(peak, equity)
        max_dd = min(max_dd, equity / peak - 1.0 if peak > 0 else 0.0)
        day_group = sub[sub["date_str"] == asof]
        cand = e8r.candidates(day_group, score_col)
        cand_set = set(cand)
        rank = {sym: idx + 1 for idx, sym in enumerate(cand)}
        target = cand[: e8r.MAX_HOLDINGS]
        target_set = set(target)
        holdings_before = sorted(holdings)
        sell_pool = [symbol for symbol in holdings_before if symbol not in target_set]

        if mode == "correct":
            sell_pool = sorted(sell_pool, key=lambda x: (0, 9999, x) if x not in cand_set else (1, -rank[x], x))
            reason = "one_sell_one_buy_correct_sell"
        elif mode == "buggy_e8r":
            sell_pool = sorted(sell_pool, key=lambda x: (0 if x not in cand_set else 1, rank[x] - 1 if x in cand_set else 9999, x))
            reason = "one_sell_one_buy_buggy_e8r_sell"
        else:
            raise RuntimeError(mode)
        sells = sell_pool[:1]

        if sell_pool:
            chosen = sells[0] if sells else ""
            sell_decisions.append({
                "signal_date": asof,
                "method": method,
                "mode": mode,
                "holdings_before_signal": " ".join(holdings_before),
                "candidate_rank_by_symbol": json.dumps({s: rank[s] for s in holdings_before if s in rank}, sort_keys=True),
                "target_top10": " ".join(target),
                "sell_symbol": chosen,
                "sell_rank": rank.get(chosen, ""),
                "sell_forward_return_to_end": price_return_to_end(prices, chosen, asof, e8r) if chosen else "",
            })

        curve.append({"date": asof, "period": f"one_sell_one_buy_{mode}", "method": method, "equity": round(equity, 2), "cash": round(cash, 2), "holding_count": len(holdings), "regime_segment": str(day_group["regime_segment"].mode().iloc[0]) if "regime_segment" in day_group and not day_group["regime_segment"].mode().empty else "unknown", "missing_price_count": missing})
        for symbol, qty in sorted(holdings.items()):
            snapshots.append({"date": asof, "method": method, "rule": f"one_sell_one_buy_{mode}", "symbol": symbol, "quantity": qty, "rank_in_candidate": rank.get(symbol, ""), "in_candidate_top50": symbol in cand_set, "in_target_top10": symbol in target_set, "cash": round(cash, 2), "equity": round(equity, 2)})

        skipped_local: list[dict[str, Any]] = []
        for symbol in sells:
            e8r.append_order(pending, prices, symbol, asof, "historical_risk_reduce", holdings.get(symbol, 0), reason, last_day, skipped_local)

        for symbol in target:
            if len(holdings) >= e8r.MAX_HOLDINGS:
                break
            if symbol in holdings:
                continue
            quote = prices.next_after(symbol, asof)
            price = quote[1] if quote else None
            qty = int((cash / max(1, e8r.MAX_HOLDINGS - len(holdings))) // (price * s2d.LOT_SIZE)) * s2d.LOT_SIZE if price else 0
            ok = e8r.append_order(pending, prices, symbol, asof, "historical_add", qty, f"one_sell_one_buy_{mode}_buy", last_day, skipped_local)
            if ok:
                break
        if skipped_local:
            skipped_count += len(skipped_local)
            actions.extend(skipped_local)

    final_equity = curve[-1]["equity"] if curve else e8r.INITIAL_EQUITY
    active = [a for a in actions if e8r.active(a)]
    notional = sum(abs(float(a["quantity"]) * float(a["price"])) for a in active if a.get("price") not in {"", None})
    avg_equity = sum(float(x["equity"]) for x in curve) / len(curve) if curve else e8r.INITIAL_EQUITY
    return {
        "method": method,
        "rule": f"one_sell_one_buy_{mode}",
        "metrics": {
            "fee_tax_adjusted_net_return": round(final_equity / e8r.INITIAL_EQUITY - 1.0, 6),
            "final_equity": round(final_equity, 2),
            "max_drawdown": round(max_dd, 6),
            "action_count": len(active),
            "buy_count": sum(1 for a in active if a["action"] == "historical_add"),
            "sell_count": sum(1 for a in active if a["action"] == "historical_risk_reduce"),
            "fee_and_tax": round(fees, 2),
            "turnover_proxy_by_notional_over_avg_equity": round(notional / avg_equity, 6) if avg_equity else "",
            "turnover_notional": round(notional, 2),
            "start_date": START,
            "end_date": END,
            "trading_days": len(curve),
            "initial_cash_or_equity_assumption": e8r.INITIAL_EQUITY,
            "fee_rate": s2d.FEE_RATE,
            "tax_rate": s2d.SELL_TAX_RATE,
            "position_count_target": e8r.MAX_HOLDINGS,
            "daily_nav_available_count": len(curve),
            "missing_price_days": missing_price_days,
            "skipped_trade_count": skipped_count,
            "last_day_new_trade_without_next_price_count": last_day["count"],
        },
        "curve": curve,
        "actions": actions,
        "snapshots": snapshots,
        "sell_decisions": sell_decisions,
        "final_holdings": holdings,
        "final_cash": cash,
    }


def metric_row(rule: str, result: dict[str, Any]) -> dict[str, Any]:
    return {"rule": rule, "method": result["method"], **result["metrics"]}


def sell_decision_diff(correct: dict[str, Any], buggy: dict[str, Any], prices: Any, e8r: Any) -> list[dict[str, Any]]:
    c = {(r["signal_date"], r["method"]): r for r in correct["sell_decisions"]}
    b = {(r["signal_date"], r["method"]): r for r in buggy["sell_decisions"]}
    rows = []
    for key in sorted(set(c) | set(b)):
        cr = c.get(key, {})
        br = b.get(key, {})
        cs = cr.get("sell_symbol", "")
        bs = br.get("sell_symbol", "")
        rows.append({
            "signal_date": key[0],
            "method": key[1],
            "holdings_before_signal": cr.get("holdings_before_signal") or br.get("holdings_before_signal", ""),
            "candidate_rank_by_symbol": cr.get("candidate_rank_by_symbol") or br.get("candidate_rank_by_symbol", ""),
            "target_top10": cr.get("target_top10") or br.get("target_top10", ""),
            "correct_sell_symbol": cs,
            "correct_sell_rank": cr.get("sell_rank", ""),
            "buggy_sell_symbol": bs,
            "buggy_sell_rank": br.get("sell_rank", ""),
            "same_sell": cs == bs,
            "next_execution_date": (prices.next_after(cs or bs, key[0]) or ["", ""])[0] if (cs or bs) else "",
            "correct_sell_forward_return_to_end": cr.get("sell_forward_return_to_end", ""),
            "buggy_sell_forward_return_to_end": br.get("sell_forward_return_to_end", ""),
        })
    return rows


def extra_hold_rows(correct: dict[str, Any], buggy: dict[str, Any], prices: Any, e8r: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cs = pd.DataFrame(correct["snapshots"])
    bs = pd.DataFrame(buggy["snapshots"])
    rows_extra = []
    rows_early = []
    if cs.empty and bs.empty:
        return rows_extra, rows_early
    all_symbols = sorted(set(cs.get("symbol", pd.Series(dtype=str))) | set(bs.get("symbol", pd.Series(dtype=str))))
    all_dates = sorted(set(cs.get("date", pd.Series(dtype=str))) | set(bs.get("date", pd.Series(dtype=str))))
    pnl_correct = {r["symbol"]: r for r in e8r.pnl_by_symbol(correct, prices)}
    pnl_buggy = {r["symbol"]: r for r in e8r.pnl_by_symbol(buggy, prices)}
    for symbol in all_symbols:
        cdates = set(cs[cs["symbol"] == symbol]["date"]) if not cs.empty else set()
        bdates = set(bs[bs["symbol"] == symbol]["date"]) if not bs.empty else set()
        extra = sorted(bdates - cdates)
        less = sorted(cdates - bdates)
        pnl_delta = round(float(pnl_buggy.get(symbol, {}).get("net_pnl_including_ending_mtm", 0.0)) - float(pnl_correct.get(symbol, {}).get("net_pnl_including_ending_mtm", 0.0)), 2)
        if extra:
            first = extra[0]
            rank_rows = bs[(bs["symbol"] == symbol) & (bs["date"] == first)]
            rank = rank_rows["rank_in_candidate"].iloc[0] if not rank_rows.empty else ""
            rows_extra.append({"symbol": symbol, "first_divergence_date": first, "days_extra_held_by_buggy": len(extra), "pnl_extra_vs_correct": pnl_delta, "max_drawdown_during_extra_hold": "", "whether_rank_worse_at_divergence": bool(rank != "" and int(rank) > 10), "rank_at_divergence": rank})
        if less:
            first = less[0]
            rows_early.append({"symbol": symbol, "first_divergence_date": first, "days_less_held_by_buggy": len(less), "pnl_avoided_or_missed": -pnl_delta, "forward_return_after_buggy_sell": price_return_to_end(prices, symbol, first, e8r)})
    return sorted(rows_extra, key=lambda r: abs(float(r["pnl_extra_vs_correct"])), reverse=True), sorted(rows_early, key=lambda r: abs(float(r["pnl_avoided_or_missed"])), reverse=True)


def rank_bucket_diagnostic(e4: pd.DataFrame, prices: Any, e8r: Any) -> list[dict[str, Any]]:
    rows = []
    df = e4[(e4["date_str"] >= START) & (e4["date_str"] <= END)].copy()
    for day, g in df.groupby("date_str"):
        ranked = g[g["qlib_rank"].astype(float) <= 50].dropna(subset=[e8r.E4_SCORE]).sort_values([e8r.E4_SCORE, "instrument"], ascending=[False, True]).copy()
        ranked["score_rank"] = range(1, len(ranked) + 1)
        for name, lo, hi in [("rank_1_10", 1, 10), ("rank_11_20", 11, 20), ("rank_21_30", 21, 30), ("rank_31_50", 31, 50)]:
            vals = []
            for row in ranked[(ranked["score_rank"] >= lo) & (ranked["score_rank"] <= hi)].itertuples(index=False):
                ret = price_return_to_end(prices, row.instrument, day, e8r)
                if ret != "":
                    vals.append(float(ret))
            rows.append({"signal_date": day, "rank_bucket": name, "row_count": len(vals), "mean_forward_return_to_end": round(sum(vals) / len(vals), 6) if vals else ""})
    summary = []
    d = pd.DataFrame(rows)
    for bucket, g in d.groupby("rank_bucket"):
        vals = pd.to_numeric(g["mean_forward_return_to_end"], errors="coerce").dropna()
        summary.append({"signal_date": "ALL", "rank_bucket": bucket, "row_count": int(g["row_count"].sum()), "mean_forward_return_to_end": round(float(vals.mean()), 6) if not vals.empty else ""})
    return rows + summary


def write_report(manifest: dict[str, Any], summary: list[dict[str, Any]], concentration: dict[str, Any], bucket_summary: list[dict[str, Any]]) -> None:
    def get(rule: str, method: str) -> float:
        return next(r["fee_tax_adjusted_net_return"] for r in summary if r["rule"] == rule and r["method"] == method)
    lines = [
        "# Phase E8S 执行报告：One-Sell-One-Buy 修复与异常归因",
        "",
        f"生成时间：`{manifest['created_at']}`",
        "",
        "## 1. 结论",
        "",
        f"- gate：`{manifest['gate']}`。",
        "- 已修复 one_sell_one_buy sell priority：top50 外优先卖；若仍在 top50，则卖 score 排名最差者。",
        "- E8R buggy one_sell_one_buy 已作为 anomaly case 复现，不作为默认候选收益证据。",
        "- 未训练 qlib/LTR，未调参，未改 score column，未触发 provider/accepted latest/frontend/API/monitor/broker/order 链路。",
        "",
        "## 2. Replay Rule Summary",
        "",
        "| rule | fresh | fresh+2025 LTR | E4 |",
        "| --- | ---: | ---: | ---: |",
        f"| original | {get('original', 'fresh_qlib_adaptive_original')} | {get('original', 'fresh_qlib_2025_ltr_original')} | {get('original', 'e4_frozen_qlib_2023_2025_ltr_original')} |",
        f"| top50_exit | {get('top50_exit', 'fresh_qlib_adaptive')} | {get('top50_exit', 'fresh_qlib_2025_ltr')} | {get('top50_exit', 'e4_frozen_qlib_2023_2025_ltr')} |",
        f"| one_sell_one_buy_correct | {get('one_sell_one_buy_correct', 'fresh_qlib_adaptive')} | {get('one_sell_one_buy_correct', 'fresh_qlib_2025_ltr')} | {get('one_sell_one_buy_correct', 'e4_frozen_qlib_2023_2025_ltr')} |",
        f"| one_sell_one_buy_buggy_e8r | {get('one_sell_one_buy_buggy_e8r', 'fresh_qlib_adaptive')} | {get('one_sell_one_buy_buggy_e8r', 'fresh_qlib_2025_ltr')} | {get('one_sell_one_buy_buggy_e8r', 'e4_frozen_qlib_2023_2025_ltr')} |",
        "",
        "## 3. Buggy E4 异常归因",
        "",
        f"- buggy E4 复现：`{get('one_sell_one_buy_buggy_e8r', 'e4_frozen_qlib_2023_2025_ltr')}`。",
        f"- correct E4：`{get('one_sell_one_buy_correct', 'e4_frozen_qlib_2023_2025_ltr')}`。",
        f"- largest single divergence contribution：`{concentration['largest_single_divergence_contribution']}`。",
        f"- top1/top3/top5/top10 positive pnl share：`{concentration['top1_positive_pnl_share']}` / `{concentration['top3_positive_pnl_share']}` / `{concentration['top5_positive_pnl_share']}` / `{concentration['top10_positive_pnl_share']}`。",
        "- buggy rule 错误地卖出 top50 内排名较好的股票，因此保留了部分排名较差但后续强势的持仓；这是 bug anomaly，不是已冻结策略假设。",
        "",
        "## 4. Rank Bucket Diagnostic",
        "",
        "| bucket | mean_forward_return_to_end |",
        "| --- | ---: |",
    ]
    for row in bucket_summary:
        lines.append(f"| {row['rank_bucket']} | {row['mean_forward_return_to_end']} |")
    lines.extend([
        "",
        "该诊断使用 future return 仅做事后归因，不进入 replay decision。",
        "",
        "## 5. 结论保护",
        "",
        "- `valid_controlled_result`：original、top50_exit、one_sell_one_buy_correct。",
        "- `bug_anomaly_result`：one_sell_one_buy_buggy_e8r，必须作废为策略收益证据。",
        "- `hypothesis_for_future_work`：若中位/较差 rank 长持有效，需要另开新支线验证，不得混入当前默认策略。",
        "- correct one_sell_one_buy 下：fresh+2025 LTR 高于 fresh；E4 高于 fresh/fresh+LTR，说明 LTR 在正确低换手规则下仍有支持，但须按该 replay rule 单独讨论。",
        "",
        "## 6. 是否允许回到默认策略讨论",
        "",
        "- 允许回到默认策略讨论，但必须先冻结 replay rule。",
        "- 不允许使用 buggy E4 96.18% 作为默认策略证据。",
        "- 可讨论 original E4、top50-exit fresh qlib、one_sell_one_buy_correct E4 等合同正确结果。",
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
    e8r = load_e8r()
    e8r.require_inputs()
    s2d = e8r.load_s2d()
    frames = e8r.load_frames()
    strategies = [
        e8r.Strategy(e8r.FRESH_METHOD, e8r.FRESH_SCORE, "fresh"),
        e8r.Strategy(e8r.FRESH_LTR_METHOD, e8r.FRESH_LTR_SCORE, "fresh_ltr"),
        e8r.Strategy(e8r.E4_METHOD, e8r.E4_SCORE, "e4"),
    ]
    prices = s2d.PriceStore(set().union(*(set(df["instrument"]) for df in frames.values())))
    original = [e8r.original_result(frames[st.frame_name], prices, st, s2d) for st in strategies]
    top50_exit = [e8r.custom_replay(frames[st.frame_name], prices, st.score_col, st.method, "top50_exit", s2d) for st in strategies]
    correct = [replay_one_sell_one_buy(frames[st.frame_name], prices, st.score_col, st.method, "correct", s2d, e8r) for st in strategies]
    buggy = [replay_one_sell_one_buy(frames[st.frame_name], prices, st.score_col, st.method, "buggy_e8r", s2d, e8r) for st in strategies]
    summary = [e8r.metric_row("original", r) for r in original] + [e8r.metric_row(r["rule"], r) for r in top50_exit] + [metric_row(r["rule"], r) for r in correct + buggy]
    wcsv(OUT / "phasee8s_replay_rule_summary.csv", summary)
    nav = []
    actions = []
    for res in original:
        nav.extend([{**r, "rule": "original"} for r in res["curve"]])
        actions.extend([{**r, "rule": "original"} for r in res["actions"]])
    for res in top50_exit + correct + buggy:
        nav.extend(res["curve"])
        actions.extend(res["actions"])
    wcsv(OUT / "phasee8s_daily_nav.csv", nav)
    wcsv(OUT / "phasee8s_actions.csv", actions)

    expected_buggy = {"fresh_qlib_adaptive": 0.48538, "fresh_qlib_2025_ltr": 0.527988, "e4_frozen_qlib_2023_2025_ltr": 0.96184}
    deviations = {r["method"]: round(r["metrics"]["fee_tax_adjusted_net_return"] - expected_buggy[r["method"]], 6) for r in buggy}
    severe = {k: v for k, v in deviations.items() if abs(v) > 0.002}
    if severe:
        raise RuntimeError(f"E8S stop: buggy E8R one_sell_one_buy not reproduced: {severe}")

    e4_correct = next(r for r in correct if r["method"] == e8r.E4_METHOD)
    e4_buggy = next(r for r in buggy if r["method"] == e8r.E4_METHOD)
    sell_diff = sell_decision_diff(e4_correct, e4_buggy, prices, e8r)
    wcsv(OUT / "phasee8s_correct_vs_buggy_sell_decision_diff.csv", sell_diff)
    extra, early = extra_hold_rows(e4_correct, e4_buggy, prices, e8r)
    wcsv(OUT / "phasee8s_buggy_extra_held_pnl.csv", extra)
    wcsv(OUT / "phasee8s_buggy_early_sold_pnl.csv", early)
    buggy_pnl = e8r.pnl_by_symbol(e4_buggy, prices)
    wcsv(OUT / "phasee8s_buggy_e4_pnl_concentration.csv", buggy_pnl)
    positive = [r for r in buggy_pnl if r["net_pnl_including_ending_mtm"] > 0]
    concentration = {
        "top1_positive_pnl_share": positive[0]["positive_pnl_share"] if positive else 0.0,
        "top3_positive_pnl_share": round(sum(r["positive_pnl_share"] for r in positive[:3]), 6),
        "top5_positive_pnl_share": round(sum(r["positive_pnl_share"] for r in positive[:5]), 6),
        "top10_positive_pnl_share": round(sum(r["positive_pnl_share"] for r in positive[:10]), 6),
        "largest_single_divergence_contribution": max(
            [abs(float(r.get("pnl_extra_vs_correct", 0.0))) for r in extra]
            + [abs(float(r.get("pnl_avoided_or_missed", 0.0))) for r in early]
            + [0.0]
        ),
    }
    bucket = rank_bucket_diagnostic(frames["e4"], prices, e8r)
    wcsv(OUT / "phasee8s_rank_bucket_forward_return_diagnostic.csv", bucket)
    bucket_summary = [r for r in bucket if r["signal_date"] == "ALL"]
    impl = [
        {"rule": "original", "status": "reused_s2d_e4_original", "validity": "valid_controlled_result"},
        {"rule": "top50_exit", "status": "reproduced_from_e8r", "validity": "valid_controlled_result"},
        {"rule": "one_sell_one_buy_correct", "status": "fixed_sell_worst_rank_first", "validity": "valid_controlled_result"},
        {"rule": "one_sell_one_buy_buggy_e8r", "status": "reproduced_buggy_sell_best_rank_first", "validity": "bug_anomaly_result"},
    ]
    wcsv(OUT / "phasee8s_rule_implementation_audit.csv", impl)
    accounting = [{"method": r["method"], "rule": r["rule"], "next_day_execution": True, "fee_rate": s2d.FEE_RATE, "tax_rate": s2d.SELL_TAX_RATE, "target_position_count": e8r.MAX_HOLDINGS, "candidate_k": e8r.CANDIDATE_K, "missing_price_days": r["metrics"]["missing_price_days"], "skipped_trade_count": r["metrics"]["skipped_trade_count"], "last_day_new_trade_without_next_price_count": r["metrics"]["last_day_new_trade_without_next_price_count"]} for r in correct + buggy]
    wcsv(OUT / "phasee8s_next_day_accounting_audit.csv", accounting)
    integrity = e8r.position_integrity(correct + buggy)
    wcsv(OUT / "phasee8s_position_integrity_audit.csv", integrity)
    forbidden = {"created_at": created_at, "no_training": True, "no_tuning": True, "no_score_column_change": True, "no_future_return_label_realized_pnl_in_replay_decision": True, "rank_bucket_future_return_diagnostic_only": True, "no_provider_accepted_latest_frontend_api_monitor_broker_order": True}
    wjson(OUT / "phasee8s_forbidden_action_audit.json", forbidden)
    manifest = {
        "created_at": created_at,
        "gate": GATE,
        "window": [START, END],
        "buggy_reproduced_deviation": deviations,
        "summary": summary,
        "buggy_e4_concentration": concentration,
        "rank_bucket_summary": bucket_summary,
        "default_discussion": "allowed only after replay rule is frozen; buggy result invalid as strategy evidence",
        "artifacts": {
            "manifest": rel(OUT / "phasee8s_manifest.json"),
            "summary": rel(OUT / "phasee8s_replay_rule_summary.csv"),
            "daily_nav": rel(OUT / "phasee8s_daily_nav.csv"),
            "actions": rel(OUT / "phasee8s_actions.csv"),
            "rule_implementation_audit": rel(OUT / "phasee8s_rule_implementation_audit.csv"),
            "next_day_accounting_audit": rel(OUT / "phasee8s_next_day_accounting_audit.csv"),
            "position_integrity_audit": rel(OUT / "phasee8s_position_integrity_audit.csv"),
            "sell_decision_diff": rel(OUT / "phasee8s_correct_vs_buggy_sell_decision_diff.csv"),
            "buggy_extra_held_pnl": rel(OUT / "phasee8s_buggy_extra_held_pnl.csv"),
            "buggy_early_sold_pnl": rel(OUT / "phasee8s_buggy_early_sold_pnl.csv"),
            "buggy_e4_pnl_concentration": rel(OUT / "phasee8s_buggy_e4_pnl_concentration.csv"),
            "rank_bucket_forward_return_diagnostic": rel(OUT / "phasee8s_rank_bucket_forward_return_diagnostic.csv"),
            "forbidden_action_audit": rel(OUT / "phasee8s_forbidden_action_audit.json"),
            "report": rel(DOC),
        },
    }
    wjson(OUT / "phasee8s_manifest.json", manifest)
    write_report(manifest, summary, concentration, bucket_summary)
    print(json.dumps({"ok": True, "gate": GATE, "report": rel(DOC), "out_dir": rel(OUT)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
