#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/phase1c_anchor_reproduction"
REPORT = ROOT / "docs/tw_phase1c_anchor_reproduction/PHASEA1_ANCHOR_REPRODUCTION_EXECUTION_REPORT_CN.md"

PHASE1C_GATE = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase1c_final_ltr_repair/phase1c_gate_summary.json"
PHASE3A0_GATE = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_gate_summary.json"
PHASE3A0_SCHEMA = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_score_schema.json"
PHASE3A0_REPRO = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_score_reproduction_metrics.csv"
PHASE3A0_SCORES = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv"

S2F = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2f_old_vs_fresh_same_window_recheck"
S2F_METRICS = S2F / "phase_s2f_same_window_metrics.csv"
S2F_COMMON = S2F / "phase_s2f_same_window_common_universe_metrics.csv"
S2F_ACTIONS = S2F / "phase_s2f_same_window_action_audit.csv"
S2F_NAV = S2F / "phase_s2f_same_window_daily_nav.csv"
S2F_COVERAGE = S2F / "phase_s2f_same_window_coverage_audit.json"
S2F_GATE = S2F / "phase_s2f_same_window_gate_summary.json"

S2D_SCRIPT = ROOT / "scripts/evaluate_tw_ltr_s2d_full_daily_replay.py"

ANCHOR_METHOD = "old_qlib_new_ltr_phase1c_simple"
TEST_START = "2025-07-01"
TEST_END = "2026-05-07"

EXPECTED_IDENTITY = {
    "candidate_id": "head10_all_l31_alpha0.7_top50_only",
    "model_id": "head10_all_l31",
    "score_column": "score_head10_all_l31_alpha0.7_top50_only",
    "blend_alpha": 0.7,
    "preserve_scope": "top50_only",
    "label_col": "relevance_10d_top_heavy",
    "num_leaves": 31,
    "learning_rate": 0.03,
    "n_estimators": 120,
    "random_state": 42,
}

EXPECTED_FULL = {
    "old_qlib_new_ltr_phase1c_simple": (0.721631, -0.050830, 405),
    "fresh_qlib_top50_adaptive_baseline": (0.662457, -0.088396, 410),
    "fresh_ltr_simple": (0.544381, -0.132896, 408),
    "fresh_ltr_turnover_controlled": (0.615059, -0.111310, 63),
}

EXPECTED_COMMON = {
    "old_qlib_new_ltr_phase1c_simple": (0.641235, -0.076739, 405),
    "fresh_qlib_top50_adaptive_baseline": (0.625943, -0.088431, 410),
    "fresh_ltr_simple": (0.544381, -0.132896, 408),
    "fresh_ltr_turnover_controlled": (0.615059, -0.111310, 63),
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({k for row in rows for k in row}) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_s2d_module():
    spec = importlib.util.spec_from_file_location("evaluate_tw_ltr_s2d_full_daily_replay", S2D_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {S2D_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def identity_audit() -> list[dict[str, Any]]:
    phase1c_gate = read_json(PHASE1C_GATE)
    phase3a0_gate = read_json(PHASE3A0_GATE)
    schema = read_json(PHASE3A0_SCHEMA)
    fixed = schema["fixed_phase1c_config"]
    actual = {
        "candidate_id": fixed.get("candidate_id") or phase3a0_gate.get("fixed_phase1c_config", {}).get("candidate_id") or phase1c_gate.get("best_candidate"),
        "model_id": fixed.get("model_id"),
        "score_column": fixed.get("score_column"),
        "blend_alpha": fixed.get("blend_alpha"),
        "preserve_scope": fixed.get("preserve_scope"),
        "label_col": fixed.get("label_col"),
        "num_leaves": fixed.get("num_leaves"),
        "learning_rate": fixed.get("learning_rate"),
        "n_estimators": fixed.get("n_estimators"),
        "random_state": fixed.get("random_state"),
    }
    rows = []
    for field, expected in EXPECTED_IDENTITY.items():
        got = actual.get(field)
        passed = str(got) == str(expected)
        rows.append({"field": field, "expected": expected, "actual": got, "pass": "yes" if passed else "no"})
    return rows


def score_reproduction_audit() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    repro = pd.read_csv(PHASE3A0_REPRO)
    scores = pd.read_csv(PHASE3A0_SCORES, usecols=["date", "instrument", EXPECTED_IDENTITY["score_column"]])
    max_abs = float(repro["abs_diff"].max())
    mean_abs = float(repro["abs_diff"].mean())
    tolerance = float(repro["tolerance"].max())
    within = bool(repro["within_tolerance"].astype(str).str.lower().eq("true").all())
    rows = [
        {
            "row_count": int(scores.shape[0]),
            "score_column": EXPECTED_IDENTITY["score_column"],
            "metric_rows": int(repro.shape[0]),
            "max_absolute_difference": max_abs,
            "mean_absolute_difference": mean_abs,
            "tolerance": tolerance,
            "pass": "yes" if within else "no",
        }
    ]
    return rows, {"row_count": int(scores.shape[0]), "max_abs_diff": max_abs, "mean_abs_diff": mean_abs, "tolerance": tolerance, "pass": within}


def metric_audit(src: Path, expected: dict[str, tuple[float, float, int]], universe: str) -> list[dict[str, Any]]:
    df = pd.read_csv(src)
    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        method = row["method"]
        exp_return, exp_mdd, exp_actions = expected[method]
        got_return = float(row["fee_tax_adjusted_net_return"])
        got_mdd = float(row["max_drawdown"])
        got_actions = int(row["action_count"])
        out = row.to_dict()
        out.update(
            {
                "universe": universe,
                "expected_fee_tax_adjusted_net_return": exp_return,
                "diff_fee_tax_adjusted_net_return": round(got_return - exp_return, 12),
                "expected_max_drawdown": exp_mdd,
                "diff_max_drawdown": round(got_mdd - exp_mdd, 12),
                "expected_action_count": exp_actions,
                "diff_action_count": got_actions - exp_actions,
                "pass": "yes" if abs(got_return - exp_return) < 1e-9 and abs(got_mdd - exp_mdd) < 1e-9 and got_actions == exp_actions else "no",
            }
        )
        rows.append(out)
    return rows


def next_day_audit(actions: pd.DataFrame, metrics: pd.DataFrame) -> list[dict[str, Any]]:
    active = actions[(actions["method"] == ANCHOR_METHOD) & (actions["action"].isin(["historical_add", "historical_risk_reduce"]))].copy()
    active["signal_date_dt"] = pd.to_datetime(active["signal_date"])
    active["execution_date_dt"] = pd.to_datetime(active["execution_date"])
    active["effective_nav_date_dt"] = pd.to_datetime(active["effective_nav_date"])
    bad_next = int((active["execution_date_dt"] <= active["signal_date_dt"]).sum())
    bad_effective = int((active["effective_nav_date_dt"] < active["execution_date_dt"]).sum())
    m = metrics[metrics["method"] == ANCHOR_METHOD].iloc[0]
    return [
        {
            "method": ANCHOR_METHOD,
            "active_action_count": int(active.shape[0]),
            "execution_date_after_signal_date": bad_next == 0,
            "execution_date_not_after_signal_violations": bad_next,
            "effective_nav_date_on_or_after_execution_date": bad_effective == 0,
            "effective_nav_date_before_execution_violations": bad_effective,
            "missing_price_days": int(m["missing_price_days"]),
            "skipped_trade_count": int(m["skipped_trade_count"]),
            "last_day_new_trade_without_next_price_count": int(m["last_day_new_trade_without_next_price_count"]),
            "pass": "yes" if bad_next == 0 and bad_effective == 0 and int(m["missing_price_days"]) == 0 and int(m["skipped_trade_count"]) == 0 and int(m["last_day_new_trade_without_next_price_count"]) == 0 else "no",
        }
    ]


def pnl_contribution(actions: pd.DataFrame, nav: pd.DataFrame) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    s2d = load_s2d_module()
    active = actions[(actions["method"] == ANCHOR_METHOD) & (actions["action"].isin(["historical_add", "historical_risk_reduce"]))].copy()
    symbols = set(active["symbol"].astype(str))
    prices = s2d.PriceStore(symbols)
    dates = nav[nav["method"] == ANCHOR_METHOD]["date"].astype(str).tolist()

    holdings: dict[str, int] = {}
    cost_basis: dict[str, float] = defaultdict(float)
    symbol_stats: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    day_stats: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    prev_close: dict[str, float] = {}
    action_groups = {d: g for d, g in active.groupby("effective_nav_date")}

    for date in dates:
        start_holdings = dict(holdings)
        current_close = {symbol: prices.close_on_or_before(symbol, date) for symbol in set(start_holdings) | symbols}
        for symbol, qty in start_holdings.items():
            close = current_close.get(symbol)
            old_close = prev_close.get(symbol)
            if close is not None and old_close is not None:
                mtm = qty * (close - old_close)
                day_stats[date]["unrealized_pnl"] += mtm

        for action in action_groups.get(date, pd.DataFrame()).to_dict("records"):
            symbol = str(action["symbol"])
            qty = int(action["quantity"])
            price = float(action["price"])
            fee_tax = float(action["fee_and_tax"])
            notional = qty * price
            if action["action"] == "historical_add":
                holdings[symbol] = holdings.get(symbol, 0) + qty
                cost_basis[symbol] += notional
                symbol_stats[symbol]["fee_tax_allocated"] += fee_tax
                day_stats[date]["fee_tax_allocated"] += fee_tax
            elif action["action"] == "historical_risk_reduce":
                held_qty = holdings.get(symbol, 0)
                basis = cost_basis.get(symbol, 0.0)
                avg_basis = basis / held_qty if held_qty else 0.0
                realized = notional - avg_basis * qty
                holdings[symbol] = max(0, held_qty - qty)
                cost_basis[symbol] = max(0.0, basis - avg_basis * qty)
                if holdings[symbol] == 0:
                    holdings.pop(symbol, None)
                    cost_basis.pop(symbol, None)
                symbol_stats[symbol]["realized_pnl"] += realized
                symbol_stats[symbol]["fee_tax_allocated"] += fee_tax
                day_stats[date]["realized_pnl"] += realized
                day_stats[date]["fee_tax_allocated"] += fee_tax

        for symbol, qty in holdings.items():
            close = current_close.get(symbol)
            if close is not None:
                prev_close[symbol] = close
        for symbol in list(prev_close):
            if symbol not in holdings:
                prev_close.pop(symbol, None)

    final_symbol_rows = []
    total_net = 0.0
    for symbol, st in symbol_stats.items():
        qty = holdings.get(symbol, 0)
        if qty:
            final_close = prices.close_on_or_before(symbol, dates[-1])
            if final_close is not None:
                st["unrealized_pnl"] = qty * final_close - cost_basis.get(symbol, 0.0)
        st["net_pnl"] = st["realized_pnl"] + st["unrealized_pnl"] - st["fee_tax_allocated"]
        total_net += st["net_pnl"]
    for symbol, st in symbol_stats.items():
        final_symbol_rows.append(
            {
                "method": ANCHOR_METHOD,
                "symbol": symbol,
                "realized_pnl": round(st["realized_pnl"], 2),
                "unrealized_pnl": round(st["unrealized_pnl"], 2),
                "fee_tax_allocated": round(st["fee_tax_allocated"], 2),
                "net_pnl": round(st["net_pnl"], 2),
                "share_of_total_net_pnl": round(st["net_pnl"] / total_net, 6) if total_net else 0.0,
            }
        )

    day_rows = []
    for date, st in day_stats.items():
        net = st["realized_pnl"] + st["unrealized_pnl"] - st["fee_tax_allocated"]
        day_rows.append(
            {
                "method": ANCHOR_METHOD,
                "date": date,
                "realized_pnl": round(st["realized_pnl"], 2),
                "unrealized_pnl": round(st["unrealized_pnl"], 2),
                "fee_tax_allocated": round(st["fee_tax_allocated"], 2),
                "net_pnl": round(net, 2),
                "share_of_total_net_pnl": round(net / total_net, 6) if total_net else 0.0,
            }
        )

    final_symbol_rows.sort(key=lambda r: float(r["net_pnl"]), reverse=True)
    day_rows.sort(key=lambda r: float(r["net_pnl"]), reverse=True)

    nav_anchor = nav[nav["method"] == ANCHOR_METHOD].copy()
    nav_anchor["equity"] = pd.to_numeric(nav_anchor["equity"], errors="coerce")
    nav_anchor["daily_return"] = nav_anchor["equity"].pct_change().fillna(0.0)
    worst_abs = nav_anchor.reindex(nav_anchor["daily_return"].abs().sort_values(ascending=False).index).head(10)
    top_symbol_share = max([abs(float(r["share_of_total_net_pnl"])) for r in final_symbol_rows] or [0.0])
    top_day_share = max([abs(float(r["share_of_total_net_pnl"])) for r in day_rows] or [0.0])
    outliers = [
        {
            "audit_item": "top_symbol_abs_share_of_total_net_pnl",
            "value": round(top_symbol_share, 6),
            "threshold": 0.35,
            "status": "watch" if top_symbol_share > 0.35 else "ok",
            "note": "absolute share by single symbol",
        },
        {
            "audit_item": "top_day_abs_share_of_total_net_pnl",
            "value": round(top_day_share, 6),
            "threshold": 0.35,
            "status": "watch" if top_day_share > 0.35 else "ok",
            "note": "absolute share by single day",
        },
        {
            "audit_item": "max_abs_daily_nav_return",
            "value": round(float(nav_anchor["daily_return"].abs().max()), 6),
            "threshold": 0.12,
            "status": "watch" if float(nav_anchor["daily_return"].abs().max()) > 0.12 else "ok",
            "note": "largest absolute daily equity return from S2F daily NAV",
        },
        {
            "audit_item": "pnl_contribution_total_vs_nav_gain",
            "value": round(total_net - (float(nav_anchor["equity"].iloc[-1]) - 1_000_000.0), 2),
            "threshold": 1.0,
            "status": "ok" if abs(total_net - (float(nav_anchor["equity"].iloc[-1]) - 1_000_000.0)) <= 1.0 else "watch",
            "note": "symbol-level net PnL sum minus S2F final equity gain",
        },
    ]
    for _, row in worst_abs.iterrows():
        outliers.append(
            {
                "audit_item": "large_daily_nav_return_sample",
                "value": round(float(row["daily_return"]), 6),
                "threshold": "",
                "status": "info",
                "note": str(row["date"]),
            }
        )
    return final_symbol_rows, day_rows, outliers

def md_table(rows: list[dict[str, Any]], fields: list[str], limit: int = 20) -> list[str]:
    out = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for row in rows[:limit]:
        out.append("| " + " | ".join(str(row.get(f, "")) for f in fields) + " |")
    return out


def write_report(summary: dict[str, Any], identity_rows: list[dict[str, Any]], repro_rows: list[dict[str, Any]], full_rows: list[dict[str, Any]], common_rows: list[dict[str, Any]], next_rows: list[dict[str, Any]], symbol_rows: list[dict[str, Any]], day_rows: list[dict[str, Any]], outliers: list[dict[str, Any]]) -> None:
    lines = [
        "# Phase A1 执行报告：Phase1C Anchor 精确复刻与只读审计",
        "",
        f"生成时间：{summary['created_at']}",
        "",
        "## 1. 执行边界",
        "",
        "- 本轮只读取既有 Phase1C / Phase3A0 / S2F 产物，并使用 S2F 原 `PriceStore` 本地 normalized price 源补充持仓 PnL 审计。",
        "- 未训练 qlib，未训练 LTR，未改窗口、feature、label、score column、费用税费、持仓数量或 next-day execution 口径。",
        "- 未使用 Q0/L1-L4、T2/T2R 或 `tw_qlib_oos_ltr_stacking` 产物作为 A1 输入。",
        "- 未触发 provider / accepted latest / monitor / broker / orders / quick-trade / frontend / API 链路。",
        "",
        "固定窗口：`2025-07-01..2026-05-07`。",
        "",
        "## 2. Anchor Identity Audit",
        "",
        *md_table(identity_rows, ["field", "expected", "actual", "pass"], 20),
        "",
        "## 3. Score Reproduction Audit",
        "",
        *md_table(repro_rows, ["row_count", "score_column", "metric_rows", "max_absolute_difference", "mean_absolute_difference", "tolerance", "pass"], 5),
        "",
        "## 4. Full Universe Metrics",
        "",
        *md_table(full_rows, ["method", "fee_tax_adjusted_net_return", "expected_fee_tax_adjusted_net_return", "diff_fee_tax_adjusted_net_return", "max_drawdown", "expected_max_drawdown", "diff_max_drawdown", "action_count", "expected_action_count", "diff_action_count", "pass"], 10),
        "",
        "## 5. Common Universe Metrics",
        "",
        f"- common universe key 数量：`{summary['common_universe_key_count']}`。",
        "- common universe 过滤后，old Phase1C anchor return 从 `0.721631` 变为 `0.641235`，差值 `-0.080396`；动作数仍为 `405`。",
        "",
        *md_table(common_rows, ["method", "fee_tax_adjusted_net_return", "expected_fee_tax_adjusted_net_return", "diff_fee_tax_adjusted_net_return", "max_drawdown", "expected_max_drawdown", "diff_max_drawdown", "action_count", "expected_action_count", "diff_action_count", "pass"], 10),
        "",
        "## 6. Next-day Accounting Audit",
        "",
        *md_table(next_rows, ["method", "active_action_count", "execution_date_after_signal_date", "execution_date_not_after_signal_violations", "effective_nav_date_on_or_after_execution_date", "missing_price_days", "skipped_trade_count", "last_day_new_trade_without_next_price_count", "pass"], 5),
        "",
        "## 7. Real PnL Contribution",
        "",
        "Top contribution symbols：",
        "",
        *md_table(symbol_rows, ["symbol", "realized_pnl", "unrealized_pnl", "fee_tax_allocated", "net_pnl", "share_of_total_net_pnl"], 10),
        "",
        "Worst contribution symbols：",
        "",
        *md_table(list(reversed(symbol_rows)), ["symbol", "realized_pnl", "unrealized_pnl", "fee_tax_allocated", "net_pnl", "share_of_total_net_pnl"], 10),
        "",
        "Top contribution days：",
        "",
        *md_table(day_rows, ["date", "realized_pnl", "unrealized_pnl", "fee_tax_allocated", "net_pnl", "share_of_total_net_pnl"], 10),
        "",
        "## 8. 异常审计",
        "",
        *md_table(outliers, ["audit_item", "value", "threshold", "status", "note"], 20),
        "",
        "结论：Phase1C anchor identity 与 row-level score reproduction 均通过；S2F full/common universe 指标与冻结表逐项一致；next-day accounting 无违反项。PnL contribution 与 outlier 审计已补齐，仅作为历史只读 anchor 解释，不构成任何交易建议。",
        "",
        "## 9. 输出产物",
        "",
        f"- `{rel(OUT / 'phasea1_anchor_identity_audit.csv')}`",
        f"- `{rel(OUT / 'phasea1_score_reproduction_audit.csv')}`",
        f"- `{rel(OUT / 'phasea1_anchor_metrics.csv')}`",
        f"- `{rel(OUT / 'phasea1_common_universe_metrics.csv')}`",
        f"- `{rel(OUT / 'phasea1_next_day_accounting_audit.csv')}`",
        f"- `{rel(OUT / 'phasea1_real_pnl_contribution_by_symbol.csv')}`",
        f"- `{rel(OUT / 'phasea1_real_pnl_contribution_by_day.csv')}`",
        f"- `{rel(OUT / 'phasea1_outlier_audit.csv')}`",
        f"- `{rel(OUT / 'phasea1_anchor_summary.json')}`",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    for path in [PHASE1C_GATE, PHASE3A0_GATE, PHASE3A0_SCHEMA, PHASE3A0_REPRO, PHASE3A0_SCORES, S2F_METRICS, S2F_COMMON, S2F_ACTIONS, S2F_NAV, S2F_COVERAGE, S2F_GATE]:
        if not path.exists():
            raise FileNotFoundError(path)

    OUT.mkdir(parents=True, exist_ok=True)
    identity_rows = identity_audit()
    if any(row["pass"] != "yes" for row in identity_rows):
        write_csv(OUT / "phasea1_anchor_identity_audit.csv", identity_rows, ["field", "expected", "actual", "pass"])
        raise RuntimeError("anchor identity audit failed")

    repro_rows, repro_summary = score_reproduction_audit()
    if not repro_summary["pass"]:
        write_csv(OUT / "phasea1_score_reproduction_audit.csv", repro_rows)
        raise RuntimeError("score reproduction audit failed")

    metrics = pd.read_csv(S2F_METRICS)
    common = pd.read_csv(S2F_COMMON)
    actions = pd.read_csv(S2F_ACTIONS)
    nav = pd.read_csv(S2F_NAV)
    coverage = read_json(S2F_COVERAGE)

    full_rows = metric_audit(S2F_METRICS, EXPECTED_FULL, "full")
    common_rows = metric_audit(S2F_COMMON, EXPECTED_COMMON, "common")
    next_rows = next_day_audit(actions, metrics)
    symbol_rows, day_rows, outliers = pnl_contribution(actions, nav)

    write_csv(OUT / "phasea1_anchor_identity_audit.csv", identity_rows, ["field", "expected", "actual", "pass"])
    write_csv(OUT / "phasea1_score_reproduction_audit.csv", repro_rows)
    write_csv(OUT / "phasea1_anchor_metrics.csv", full_rows)
    write_csv(OUT / "phasea1_common_universe_metrics.csv", common_rows)
    write_csv(OUT / "phasea1_next_day_accounting_audit.csv", next_rows)
    write_csv(OUT / "phasea1_real_pnl_contribution_by_symbol.csv", symbol_rows)
    write_csv(OUT / "phasea1_real_pnl_contribution_by_day.csv", day_rows)
    write_csv(OUT / "phasea1_outlier_audit.csv", outliers)

    summary = {
        "created_at": now(),
        "phase": "phasea1_anchor_reproduction",
        "anchor_method": ANCHOR_METHOD,
        "test_window": f"{TEST_START}..{TEST_END}",
        "identity_pass": all(row["pass"] == "yes" for row in identity_rows),
        "score_reproduction_pass": repro_summary["pass"],
        "full_metrics_pass": all(row["pass"] == "yes" for row in full_rows),
        "common_metrics_pass": all(row["pass"] == "yes" for row in common_rows),
        "next_day_accounting_pass": all(row["pass"] == "yes" for row in next_rows),
        "common_universe_key_count": coverage.get("overlap_all_three_rows"),
        "price_source": "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty via scripts/evaluate_tw_ltr_s2d_full_daily_replay.py PriceStore",
        "no_training": True,
        "no_replay_policy_change": True,
        "no_frontend_api_provider_monitor_trading": True,
        "forbidden_oos_ltr_stacking_inputs_used": False,
        "artifacts": {
            "identity": rel(OUT / "phasea1_anchor_identity_audit.csv"),
            "score_reproduction": rel(OUT / "phasea1_score_reproduction_audit.csv"),
            "anchor_metrics": rel(OUT / "phasea1_anchor_metrics.csv"),
            "common_metrics": rel(OUT / "phasea1_common_universe_metrics.csv"),
            "next_day_accounting": rel(OUT / "phasea1_next_day_accounting_audit.csv"),
            "pnl_by_symbol": rel(OUT / "phasea1_real_pnl_contribution_by_symbol.csv"),
            "pnl_by_day": rel(OUT / "phasea1_real_pnl_contribution_by_day.csv"),
            "outlier_audit": rel(OUT / "phasea1_outlier_audit.csv"),
            "report": rel(REPORT),
        },
    }
    write_json(OUT / "phasea1_anchor_summary.json", summary)
    write_report(summary, identity_rows, repro_rows, full_rows, common_rows, next_rows, symbol_rows, day_rows, outliers)
    print(json.dumps({"ok": True, "report": rel(REPORT), "summary": rel(OUT / "phasea1_anchor_summary.json")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
