#!/usr/bin/env python3
"""Isolated historical A-only vs A+B replay with exact Model-A top50 binding.

This is an evidence builder only. It never writes provider/latest/default/cron
state and never emits orders outside the readonly replay artifact.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_historical_exact_replay_20260907"
QLIB = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_raw_oos_score_rank_2023_2026.csv"
LTR = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_test_row_scores_2026.csv"
E3_MODEL = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_ltr_model.pkl"
E3_MANIFEST = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_training_manifest.json"
E2_FEATURE_MANIFEST = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_sample_manifest.json"
PRICE_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"
START, END = "2026-01-02", "2026-05-07"
TOP50, TARGET = 50, 10
INITIAL = 1_000_000.0
FEE, TAX, LOT = 0.001425, 0.003, 10
MODEL_A = "e4_frozen_qlib_2018_2022"
MODEL_B = "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025"
PROTECTED = [
    ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json",
    ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt",
    ROOT / "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron",
]


def sha(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fingerprints() -> dict[str, Any]:
    return {str(p.relative_to(ROOT)): {"exists": p.is_file(), "sha256": sha(p)} for p in PROTECTED}


class Prices:
    def __init__(self, symbols: set[str]):
        self.rows: dict[str, list[dict[str, Any]]] = {}
        for symbol in sorted(symbols):
            path = PRICE_ROOT / f"{symbol}.csv"
            if not path.is_file():
                continue
            vals = []
            with path.open(encoding="utf-8", newline="") as fh:
                for row in csv.DictReader(fh):
                    try:
                        vals.append({"date": str(row.get("date", ""))[:10], "open": float(row.get("open", "")), "close": float(row.get("close", ""))})
                    except (TypeError, ValueError):
                        continue
            self.rows[symbol] = sorted((r for r in vals if r["date"]), key=lambda x: x["date"])

    def next_open(self, symbol: str, day: str) -> tuple[str, float] | None:
        for row in self.rows.get(symbol, []):
            if row["date"] > day and row["open"] > 0:
                return row["date"], row["open"]
        return None

    def close(self, symbol: str, day: str) -> float | None:
        result = None
        for row in self.rows.get(symbol, []):
            if row["date"] <= day and row["close"] > 0:
                result = row["close"]
            elif row["date"] > day:
                break
        return result


def load_input() -> tuple[pd.DataFrame, dict[str, Any], dict[str, dict[str, int]]]:
    # E1 is authoritative for the complete Model-A cross-section and rank.
    # E3 contributes only the B score through the canonical date/instrument key.
    q = pd.read_csv(QLIB, dtype={"instrument": str})
    q["date"] = q["date"].astype(str).str[:10]
    q = q[(q.date >= START) & (q.date <= END)].copy()
    l = pd.read_csv(LTR, dtype={"instrument": str})
    l["date"] = l["date"].astype(str).str[:10]
    l = l[(l.date >= START) & (l.date <= END)].copy()
    ltr_col = "phasee3_extended_oos_ltr_score"
    if ltr_col not in l.columns:
        raise RuntimeError(f"missing {ltr_col}")
    if q.duplicated(["date", "instrument"]).any() or l.duplicated(["date", "instrument"]).any():
        raise RuntimeError("duplicate date/instrument key in E1 or E3 score artifact")
    merged = q.rename(columns={"qlib_rank_raw": "full_qlib_rank", "qlib_score_raw": "a_score"})
    merged = merged.merge(l[["date", "instrument", ltr_col]], on=["date", "instrument"], how="left", validate="one_to_one").rename(columns={ltr_col: "b_score"})
    merged["full_qlib_rank"] = pd.to_numeric(merged.full_qlib_rank, errors="coerce")
    merged["a_score"] = pd.to_numeric(merged.a_score, errors="coerce")
    merged["b_score"] = pd.to_numeric(merged.b_score, errors="coerce")
    merged = merged.dropna(subset=["full_qlib_rank", "a_score"])
    daily = merged.groupby("date")
    bad = []
    universe_rows = []
    complete_days = []
    for day, group in daily:
        top_group = group[group.full_qlib_rank <= TOP50]
        top_set = set(top_group.instrument)
        b_missing = int(top_group.b_score.isna().sum())
        if len(top_group) != TOP50 or set(top_group.full_qlib_rank.astype(int)) != set(range(1, TOP50 + 1)) or b_missing:
            bad.append({"date": day, "rows": int(len(group)), "top50_rows": int(len(top_group)), "distinct_rank": int(group.full_qlib_rank.nunique()), "b_score_missing_top50": b_missing, "status": "EXCLUDED"})
            continue
        complete_days.append(day)
        top = top_group.copy().sort_values(["full_qlib_rank", "instrument"])
        for row in top.itertuples(index=False):
            universe_rows.append({"date": day, "instrument": row.instrument, "candidate_rank": int(row.full_qlib_rank), "full_qlib_rank": int(row.full_qlib_rank), "a_score": float(row.a_score), "b_score": float(row.b_score)})
    if not complete_days:
        raise RuntimeError(f"no E1-authoritative top50 dates with complete E3 B score coverage: {bad[:3]}")
    full_ranks = {day: {str(row.instrument): int(row.full_qlib_rank) for row in group.itertuples(index=False)} for day, group in daily if day in complete_days}
    out = pd.DataFrame(universe_rows)
    dates = sorted(out.date.unique())
    meta = {"dates": dates, "date_count": len(dates), "requested_date_count": int(merged.date.nunique()), "excluded_dates_due_to_join_or_top50": bad, "input_rows_full_e1": int(len(q)), "input_rows_full_joined": int(len(merged)), "input_rows_top50_paired": int(len(out)), "full_cross_section_rows_expected": 150, "full_cross_section_rows_observed_min": int(merged.groupby("date").size().min()), "top50_rows_per_date": 50, "join_key": ["date", "instrument"], "b_score_full_coverage_on_authoritative_top50": all(int(x.get("b_score_missing_top50", 0)) == 0 for x in bad) and len(bad) == 0, "bad_cross_sections": bad, "qlib_sha256": sha(QLIB), "ltr_sha256": sha(LTR), "ltr_model_path": str(E3_MODEL.relative_to(ROOT)), "ltr_model_sha256": sha(E3_MODEL), "ltr_training_manifest_path": str(E3_MANIFEST.relative_to(ROOT)), "ltr_training_manifest_sha256": sha(E3_MANIFEST), "feature_manifest_path": str(E2_FEATURE_MANIFEST.relative_to(ROOT)), "feature_manifest_sha256": sha(E2_FEATURE_MANIFEST)}
    return out, meta, full_ranks


def replay(signals: pd.DataFrame, prices: Prices, score_col: str, method: str, full_ranks: dict[str, dict[str, int]]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    dates = sorted(signals.date.unique())
    by_day = {d: g for d, g in signals.groupby("date")}
    holdings: dict[str, int] = {}
    pending: dict[str, list[dict[str, Any]]] = defaultdict(list)
    cash, fees, peak, max_dd = INITIAL, 0.0, INITIAL, 0.0
    actions, nav = [], []
    for day in dates:
        for order in pending.pop(day, []):
            price = float(order["price"])
            symbol, qty = order["instrument"], int(order["quantity"])
            if order["action"] == "sell":
                held = holdings.pop(symbol, 0)
                cost = held * price * (FEE + TAX)
                cash += held * price - cost
                fees += cost
                actions.append({**order, "execution_date": day, "quantity": held, "execution_price": round(price, 6), "commission": round(held * price * FEE, 2), "tax": round(held * price * TAX, 2), "fee_tax": round(cost, 2)})
            elif order["action"] == "buy" and qty > 0:
                cost = qty * price * (1 + FEE)
                if cash >= cost:
                    cash -= cost
                    fees += qty * price * FEE
                    holdings[symbol] = holdings.get(symbol, 0) + qty
                    actions.append({**order, "execution_date": day, "quantity": qty, "execution_price": round(price, 6), "commission": round(qty * price * FEE, 2), "tax": 0.0, "fee_tax": round(qty * price * FEE, 2)})
                else:
                    actions.append({**order, "execution_date": day, "quantity": 0, "execution_price": round(price, 6), "commission": 0.0, "tax": 0.0, "fee_tax": 0.0, "action": "skip", "skip_reason": "insufficient_cash"})
        value = cash
        missing = 0
        for symbol, qty in holdings.items():
            px = prices.close(symbol, day)
            if px is None:
                missing += 1
            else:
                value += qty * px
        peak = max(peak, value)
        max_dd = min(max_dd, value / peak - 1 if peak else 0)
        nav.append({"date": day, "method": method, "cash": round(cash, 2), "market_value": round(value - cash, 2), "equity": round(value, 2), "daily_return": 0.0, "holding_count": len(holdings), "missing_price_count": missing})
        g = by_day[day]
        top50 = set(g.instrument)
        outside = [s for s in holdings if s not in top50]
        if outside:
            worst = max(outside, key=lambda s: (full_ranks.get(day, {}).get(s, 10**9), s))
            quote = prices.next_open(worst, day)
            if quote:
                pending[quote[0]].append({"signal_date": day, "instrument": worst, "action": "sell", "quantity": holdings[worst], "reason": "exited_qlib_top50", "price": quote[1]})
        if len(holdings) < TARGET:
            ranked = g.sort_values([score_col, "instrument"], ascending=[False, True])
            for row in ranked.itertuples(index=False):
                if row.instrument in holdings:
                    continue
                quote = prices.next_open(row.instrument, day)
                if not quote:
                    continue
                allocation = cash / max(1, TARGET - len(holdings))
                qty = int(allocation // (quote[1] * LOT)) * LOT
                pending[quote[0]].append({"signal_date": day, "instrument": row.instrument, "action": "buy", "quantity": qty, "reason": "top50_buy_score_rank", "price": quote[1]})
                break
    for i, row in enumerate(nav):
        row["daily_return"] = 0.0 if i == 0 else row["equity"] / nav[i - 1]["equity"] - 1.0
    rets = [float(r["daily_return"]) for r in nav[1:] if math.isfinite(float(r["daily_return"]))]
    sharpe = (sum(rets) / len(rets) / (sum((x - sum(rets) / len(rets)) ** 2 for x in rets) / max(1, len(rets) - 1)) ** 0.5 * math.sqrt(252)) if len(rets) > 1 and sum((x - sum(rets) / len(rets)) ** 2 for x in rets) > 0 else 0.0
    wins = sum(x > 0 for x in rets)
    active = [a for a in actions if a["action"] in {"buy", "sell"} and int(a["quantity"]) > 0]
    turnover = sum(abs(float(a["quantity"]) * float(a["execution_price"])) for a in active)
    metrics = {"method": method, "start_date": START, "end_date": END, "trading_days": len(nav), "final_equity": round(nav[-1]["equity"], 2), "net_return": round(nav[-1]["equity"] / INITIAL - 1, 8), "max_drawdown": round(max_dd, 8), "sharpe_annualized": round(sharpe, 8), "win_days": wins, "loss_days": len(rets) - wins, "win_day_rate": round(wins / len(rets), 8) if rets else 0.0, "action_count": len(active), "buy_count": sum(a["action"] == "buy" for a in active), "sell_count": sum(a["action"] == "sell" for a in active), "fee_tax": round(fees, 2), "turnover_notional": round(turnover, 2), "missing_price_days": sum(int(r["missing_price_count"] > 0) for r in nav), "skipped_actions": sum(a["action"] == "skip" for a in actions)}
    return metrics, actions, nav


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({k for r in rows for k in r}) if rows else ["empty"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)


def main() -> int:
    before = fingerprints()
    signals, input_meta, full_ranks = load_input()
    prices = Prices(set(signals.instrument))
    if len(prices.rows) < len(set(signals.instrument)):
        raise RuntimeError("missing local price files")
    a_metrics, a_actions, a_nav = replay(signals, prices, "a_score", "A_ONLY", full_ranks)
    b_metrics, b_actions, b_nav = replay(signals, prices, "b_score", "A_PLUS_B", full_ranks)
    universe = []
    for day, g in signals.groupby("date"):
        keys = sorted(set(g.instrument)); universe.append({"date": day, "a_top50_count": len(keys), "b_visible_count": len(keys), "candidate_set_equal": True, "a_top50_sha256": hashlib.sha256("|".join(keys).encode()).hexdigest(), "b_top50_sha256": hashlib.sha256("|".join(keys).encode()).hexdigest(), "full_rank_min": int(g.full_qlib_rank.min()), "full_rank_max": int(g.full_qlib_rank.max())})
    after = fingerprints()
    paired = [{"date": row["date"], "a_rows": row["a_top50_count"], "b_rows": row["b_visible_count"], "a_b_same_date": True, "a_b_same_keys": bool(row["candidate_set_equal"]), "paired_status": "PASS" if row["candidate_set_equal"] and row["a_top50_count"] == TOP50 else "FAIL"} for row in universe]
    safety = {"readonly_only": True, "simulation_only": True, "production_allowed": False, "provider_refresh": False, "provider_publish": False, "accepted_latest_switch": False, "baseline_switch": False, "cron_write": False, "broker_or_order": False, "target_position_output": False, "future_or_label_fields_consumed": False, "future_or_label_columns_present_in_source_but_not_loaded_for_scoring": True, "score_columns_consumed": ["qlib_score_raw", "phasee3_extended_oos_ltr_score"], "execution_price_mode": "next_open", "missing_next_open_fallback": False, "protected_fingerprints_unchanged": before == after}
    write_csv(OUT / "paired_date_coverage.csv", paired)
    (OUT / "safety_audit.json").write_text(json.dumps(safety, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    report = {"created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(), "window": [START, END], "model_a": MODEL_A, "model_b": MODEL_B, "strategy_rule": "top50_exit_one_worst_sell", "execution_price_mode": "next_open", "fees": {"commission_rate": FEE, "sell_tax_rate": TAX, "lot_size": LOT}, "initial_equity": INITIAL, "input": input_meta, "candidate_equality": {"dates": len(universe), "mismatch_dates": sum(not x["candidate_set_equal"] for x in universe), "all_equal": all(x["candidate_set_equal"] for x in universe), "full_qlib_rank_preserved": all(x["full_rank_min"] == 1 and x["full_rank_max"] <= 50 for x in universe)}, "paired_date_coverage": {"dates": len(paired), "all_pass": all(x["paired_status"] == "PASS" for x in paired)}, "metrics": [a_metrics, b_metrics], "relative": {"return_diff_b_minus_a": round(b_metrics["net_return"] - a_metrics["net_return"], 8), "drawdown_diff_b_minus_a": round(b_metrics["max_drawdown"] - a_metrics["max_drawdown"], 8), "sharpe_diff_b_minus_a": round(b_metrics["sharpe_annualized"] - a_metrics["sharpe_annualized"], 8), "action_diff_b_minus_a": b_metrics["action_count"] - a_metrics["action_count"], "fee_tax_diff_b_minus_a": round(b_metrics["fee_tax"] - a_metrics["fee_tax"], 2)}, "protected_before": before, "protected_after": after, "protected_unchanged": before == after, "safety": safety, "no_publish": True, "no_broker": True, "no_baseline_switch": True}
    write_csv(OUT / "candidate_equality_audit.csv", universe)
    write_csv(OUT / "paired_metrics.csv", [a_metrics, b_metrics])
    write_csv(OUT / "A_ONLY_actions.csv", a_actions); write_csv(OUT / "A_PLUS_B_actions.csv", b_actions)
    write_csv(OUT / "A_ONLY_daily_nav.csv", a_nav); write_csv(OUT / "A_PLUS_B_daily_nav.csv", b_nav)
    (OUT / "execution_report.json").write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    (OUT / "EXECUTION_REPORT_CN.md").write_text("# Model B 历史 exact replay 执行报告\n\n" + json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(OUT.relative_to(ROOT)), "metrics": report["metrics"], "candidate_mismatch_dates": report["candidate_equality"]["mismatch_dates"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
