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
S2D_SCRIPT = ROOT / "scripts/evaluate_tw_ltr_s2d_full_daily_replay.py"

CONTROL_SCORE = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv"
TREATMENT_SCORE = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_treatment_row_scores.csv"
TREATMENT_SAMPLE = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o3_row_aligned_treatment_sample/phaseo3_treatment_candidate_sample.csv"
O4_IMPORTANCE = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_feature_importance.csv"
O4_SUMMARY = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_summary.json"
S2F_COMMON = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2f_old_vs_fresh_same_window_recheck/phase_s2f_same_window_common_universe_metrics.csv"

OUT = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation"
REPORT = ROOT / "docs/tw_ltr_orthogonal_features_controlled/PHASEO5_CONTROLLED_REPLAY_EVALUATION_EXECUTION_REPORT_CN.md"

START = "2025-07-01"
END = "2026-05-07"
CONTROL_COL = "score_head10_all_l31_alpha0.7_top50_only"
TREATMENT_COL = "phaseo4_treatment_ltr_score"
TREATMENT_REPLAY_COL = "phaseo4_treatment_ltr_score_top50_preserve"
LOW_COVERAGE = {"TW7769", "TW6919", "TW3131", "TW6683", "TW4749", "TW6805", "TW6446", "TW6789", "TW6770"}


def load_s2d():
    spec = importlib.util.spec_from_file_location("evaluate_tw_ltr_s2d_full_daily_replay", S2D_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {S2D_SCRIPT}")
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


def wcsv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({key for row in rows for key in row}) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def wjson(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def norm(symbol: Any) -> str:
    text = str(symbol or "").strip().upper()
    return text if text.startswith("TW") else f"TW{text}"


def metric_row(result: dict[str, Any], baseline: dict[str, Any] | None, universe: str, key_count: int) -> dict[str, Any]:
    m = result["metrics"]
    row = {
        "universe": universe,
        "common_universe_key_count": key_count if universe != "full_universe" else "",
        "period": "same_test_window",
        "start_date": START,
        "end_date": END,
        "method": result["method"],
        "comparison_status": "completed",
        **m,
    }
    if baseline is not None:
        row["relative_return_vs_phase1c_anchor"] = round(m["fee_tax_adjusted_net_return"] - baseline["fee_tax_adjusted_net_return"], 6)
        row["relative_drawdown_vs_phase1c_anchor"] = round(m["max_drawdown"] - baseline["max_drawdown"], 6)
        row["relative_actions_vs_phase1c_anchor"] = int(m["action_count"]) - int(baseline["action_count"])
    return row


def load_inputs() -> pd.DataFrame:
    control = pd.read_csv(
        CONTROL_SCORE,
        usecols=[
            "date",
            "instrument",
            "split",
            "regime_segment",
            "qlib_score_raw",
            "qlib_rank",
            CONTROL_COL,
            "future_excess_return_rank_10d",
            "relevance_10d_bucket",
        ],
        parse_dates=["date"],
    )
    control["date_str"] = control["date"].dt.strftime("%Y-%m-%d")
    control = control[(control["date_str"] >= START) & (control["date_str"] <= END)].copy()
    control = control.rename(columns={"relevance_10d_bucket": "relevance_10d_top_heavy"})

    treatment = pd.read_csv(TREATMENT_SCORE, parse_dates=["date"])
    treatment["date_str"] = treatment["date"].dt.strftime("%Y-%m-%d")
    treatment = treatment[(treatment["date_str"] >= START) & (treatment["date_str"] <= END)].copy()

    flags = pd.read_csv(
        TREATMENT_SAMPLE,
        usecols=[
            "date",
            "instrument",
            "institutional_missing_flag",
            "institutional_delay_flag",
            "institutional_flow_asof_missing_flag",
            "margin_short_missing_flag",
            "margin_short_delay_flag",
            "margin_short_asof_missing_flag",
        ],
        parse_dates=["date"],
    )
    flags["date_str"] = flags["date"].dt.strftime("%Y-%m-%d")
    flags = flags[(flags["date_str"] >= START) & (flags["date_str"] <= END)].copy()

    df = control.merge(
        treatment[["date_str", "instrument", TREATMENT_COL]],
        on=["date_str", "instrument"],
        how="outer",
        validate="one_to_one",
    )
    df = df.merge(
        flags.drop(columns=["date"], errors="ignore"),
        on=["date_str", "instrument"],
        how="left",
        validate="one_to_one",
    )
    df["date"] = pd.to_datetime(df["date_str"])
    df["split"] = df["split"].fillna("test")
    df["regime_segment"] = df["regime_segment"].fillna("unknown")
    df["instrument"] = df["instrument"].map(norm)
    df[TREATMENT_REPLAY_COL] = df[TREATMENT_COL].where(df["qlib_rank"].astype(float) <= 50)
    for col in [
        "institutional_missing_flag",
        "institutional_delay_flag",
        "institutional_flow_asof_missing_flag",
        "margin_short_missing_flag",
        "margin_short_delay_flag",
        "margin_short_asof_missing_flag",
    ]:
        df[col] = df[col].fillna(False).astype(bool)
    return df.sort_values(["date_str", "instrument"]).reset_index(drop=True)


def dcg(labels: list[float]) -> float:
    return sum(((2.0 ** relv) - 1.0) / math.log2(idx + 2.0) for idx, relv in enumerate(labels))


def ranking_metrics(df: pd.DataFrame, score_col: str, method: str, universe: str) -> dict[str, Any]:
    sub = df.dropna(subset=[score_col, "future_excess_return_rank_10d", "relevance_10d_top_heavy"]).copy()
    rank_ics: list[float] = []
    ndcgs = {10: [], 30: [], 50: []}
    top_future = {10: [], 30: [], 50: []}
    for _, group in sub.groupby("date_str"):
        if group.shape[0] < 5:
            continue
        corr = group[score_col].rank(ascending=True).corr(group["future_excess_return_rank_10d"].rank(ascending=True), method="pearson")
        if pd.notna(corr):
            rank_ics.append(float(corr))
        ordered = group.sort_values([score_col, "instrument"], ascending=[False, True])
        ideal = group.sort_values(["relevance_10d_top_heavy", "instrument"], ascending=[False, True])
        for k in [10, 30, 50]:
            got = ordered.head(k)["relevance_10d_top_heavy"].astype(float).tolist()
            best = ideal.head(k)["relevance_10d_top_heavy"].astype(float).tolist()
            denom = dcg(best)
            if denom > 0:
                ndcgs[k].append(dcg(got) / denom)
            top_future[k].append(float(ordered.head(k)["future_excess_return_rank_10d"].mean()))
    return {
        "universe": universe,
        "method": method,
        "score_column": score_col,
        "row_count": int(sub.shape[0]),
        "date_count": int(sub["date_str"].nunique()),
        "rank_ic_10d": round(sum(rank_ics) / len(rank_ics), 12) if rank_ics else "",
        "ndcg_at_10": round(sum(ndcgs[10]) / len(ndcgs[10]), 12) if ndcgs[10] else "",
        "ndcg_at_30": round(sum(ndcgs[30]) / len(ndcgs[30]), 12) if ndcgs[30] else "",
        "ndcg_at_50": round(sum(ndcgs[50]) / len(ndcgs[50]), 12) if ndcgs[50] else "",
        "top10_future_excess_return_rank_10d": round(sum(top_future[10]) / len(top_future[10]), 12) if top_future[10] else "",
        "top30_future_excess_return_rank_10d": round(sum(top_future[30]) / len(top_future[30]), 12) if top_future[30] else "",
        "top50_future_excess_return_rank_10d": round(sum(top_future[50]) / len(top_future[50]), 12) if top_future[50] else "",
    }


def active_actions(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [a for a in result["actions"] if a.get("action") in {"historical_add", "historical_risk_reduce"}]


def accounting_rows(results: dict[str, dict[str, Any]], universe: str) -> list[dict[str, Any]]:
    rows = []
    for method, result in results.items():
        active = active_actions(result)
        bad = sum(1 for action in active if str(action.get("execution_date", "")) <= str(action.get("signal_date", "")))
        m = result["metrics"]
        passed = bad == 0 and int(m["missing_price_days"]) == 0 and int(m["skipped_trade_count"]) == 0 and int(m["last_day_new_trade_without_next_price_count"]) == 0
        rows.append(
            {
                "universe": universe,
                "method": method,
                "active_action_count": len(active),
                "execution_date_after_signal_date": bad == 0,
                "execution_date_not_after_signal_violations": bad,
                "missing_price_days": int(m["missing_price_days"]),
                "skipped_trade_count": int(m["skipped_trade_count"]),
                "last_day_new_trade_without_next_price_count": int(m["last_day_new_trade_without_next_price_count"]),
                "pass": "yes" if passed else "no",
            }
        )
    return rows


def period_performance(nav_rows: list[dict[str, Any]], freq: str) -> list[dict[str, Any]]:
    nav = pd.DataFrame(nav_rows)
    if nav.empty:
        return []
    nav["date"] = pd.to_datetime(nav["date"])
    nav["bucket"] = nav["date"].dt.to_period(freq).astype(str)
    rows = []
    for (method, bucket), group in nav.sort_values("date").groupby(["method", "bucket"]):
        equity = group["equity"].astype(float)
        peak = equity.cummax()
        rows.append(
            {
                "method": method,
                "period": bucket,
                "start_date": group["date"].min().strftime("%Y-%m-%d"),
                "end_date": group["date"].max().strftime("%Y-%m-%d"),
                "trading_days": int(group.shape[0]),
                "period_return": round(float(equity.iloc[-1] / equity.iloc[0] - 1.0), 6) if equity.iloc[0] else "",
                "max_drawdown": round(float((equity / peak - 1.0).min()), 6),
            }
        )
    return rows


def pnl_contribution(result: dict[str, Any], prices: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    method = result["method"]
    dates = [str(row["date"]) for row in result["curve"]]
    active = active_actions(result)
    by_day_actions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for action in active:
        by_day_actions[str(action["effective_nav_date"])].append(action)

    holdings: dict[str, int] = {}
    basis: dict[str, float] = {}
    prev_close: dict[str, float] = {}
    by_symbol: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    by_day: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for day in dates:
        for symbol, qty in dict(holdings).items():
            close = prices.close_on_or_before(symbol, day)
            old_close = prev_close.get(symbol)
            if close is not None and old_close is not None:
                mtm = qty * (close - old_close)
                by_symbol[symbol]["unrealized_pnl"] += mtm
                by_day[day]["unrealized_pnl"] += mtm
        for action in by_day_actions.get(day, []):
            symbol = norm(action["symbol"])
            qty = int(action["quantity"])
            price = float(action["price"])
            fee_tax = float(action["fee_and_tax"])
            notional = qty * price
            if action["action"] == "historical_add":
                holdings[symbol] = holdings.get(symbol, 0) + qty
                basis[symbol] = basis.get(symbol, 0.0) + notional
                by_symbol[symbol]["fee_tax_allocated"] += fee_tax
                by_day[day]["fee_tax_allocated"] += fee_tax
            else:
                held = holdings.get(symbol, 0)
                avg_basis = basis.get(symbol, 0.0) / held if held else 0.0
                realized = notional - avg_basis * qty
                holdings[symbol] = max(0, held - qty)
                basis[symbol] = max(0.0, basis.get(symbol, 0.0) - avg_basis * qty)
                if holdings[symbol] == 0:
                    holdings.pop(symbol, None)
                    basis.pop(symbol, None)
                by_symbol[symbol]["realized_pnl"] += realized
                by_symbol[symbol]["fee_tax_allocated"] += fee_tax
                by_day[day]["realized_pnl"] += realized
                by_day[day]["fee_tax_allocated"] += fee_tax
        for symbol, qty in holdings.items():
            close = prices.close_on_or_before(symbol, day)
            if close is not None and qty:
                prev_close[symbol] = close

    symbol_rows = []
    total_net = 0.0
    for symbol, st in by_symbol.items():
        net = st["realized_pnl"] + st["unrealized_pnl"] - st["fee_tax_allocated"]
        total_net += net
        symbol_rows.append(
            {
                "method": method,
                "symbol": symbol,
                "realized_pnl": round(st["realized_pnl"], 2),
                "unrealized_pnl": round(st["unrealized_pnl"], 2),
                "fee_tax_allocated": round(st["fee_tax_allocated"], 2),
                "net_pnl": round(net, 2),
            }
        )
    for row in symbol_rows:
        row["share_of_total_net_pnl"] = round(float(row["net_pnl"]) / total_net, 6) if total_net else ""

    day_rows = []
    for day, st in by_day.items():
        net = st["realized_pnl"] + st["unrealized_pnl"] - st["fee_tax_allocated"]
        day_rows.append(
            {
                "method": method,
                "date": day,
                "realized_pnl": round(st["realized_pnl"], 2),
                "unrealized_pnl": round(st["unrealized_pnl"], 2),
                "fee_tax_allocated": round(st["fee_tax_allocated"], 2),
                "net_pnl": round(net, 2),
            }
        )
    total_day_net = sum(float(row["net_pnl"]) for row in day_rows)
    for row in day_rows:
        row["share_of_total_net_pnl"] = round(float(row["net_pnl"]) / total_day_net, 6) if total_day_net else ""

    curve = pd.DataFrame(result["curve"])
    curve["daily_return"] = curve["equity"].astype(float).pct_change().fillna(0.0)
    summary = {
        "method": method,
        "total_net_pnl": round(total_net, 2),
        "top_symbol_abs_share_of_total_net_pnl": max([abs(float(row["share_of_total_net_pnl"] or 0)) for row in symbol_rows] or [0.0]),
        "top_day_abs_share_of_total_net_pnl": max([abs(float(row["share_of_total_net_pnl"] or 0)) for row in day_rows] or [0.0]),
        "max_abs_daily_nav_return": round(float(curve["daily_return"].abs().max()), 6) if not curve.empty else "",
    }
    return symbol_rows, day_rows, summary


def low_coverage_audit(df: pd.DataFrame, result: dict[str, Any], symbol_pnl: list[dict[str, Any]]) -> list[dict[str, Any]]:
    active = active_actions(result)
    held_symbols = {norm(action["symbol"]) for action in active}
    pnl_by_symbol = {row["symbol"]: row for row in symbol_pnl if row["method"] == result["method"]}
    rows = []
    for symbol in sorted(LOW_COVERAGE):
        sub = df[df["instrument"] == symbol]
        act = [action for action in active if norm(action["symbol"]) == symbol]
        pnl = pnl_by_symbol.get(symbol, {})
        rows.append(
            {
                "method": result["method"],
                "symbol": symbol,
                "in_replay_rows": int(sub.shape[0]),
                "ever_traded_or_held": symbol in held_symbols,
                "action_count": len(act),
                "buy_count": sum(1 for a in act if a["action"] == "historical_add"),
                "sell_count": sum(1 for a in act if a["action"] == "historical_risk_reduce"),
                "net_pnl": pnl.get("net_pnl", 0.0),
                "share_of_total_net_pnl": pnl.get("share_of_total_net_pnl", 0.0),
                "institutional_missing_flag_ratio": round(float(sub["institutional_missing_flag"].mean()), 6) if not sub.empty else "",
                "institutional_delay_flag_ratio": round(float(sub["institutional_delay_flag"].mean()), 6) if not sub.empty else "",
                "margin_short_missing_flag_ratio": round(float(sub["margin_short_missing_flag"].mean()), 6) if not sub.empty else "",
                "margin_short_delay_flag_ratio": round(float(sub["margin_short_delay_flag"].mean()), 6) if not sub.empty else "",
            }
        )
    return rows


def flag_exposure(df: pd.DataFrame, result: dict[str, Any]) -> dict[str, Any]:
    active_symbols_by_signal: dict[str, set[str]] = defaultdict(set)
    for action in active_actions(result):
        active_symbols_by_signal[str(action["signal_date"])].add(norm(action["symbol"]))
    held_rows = []
    for day, symbols in active_symbols_by_signal.items():
        held_rows.append(df[(df["date_str"] == day) & (df["instrument"].isin(symbols))])
    held = pd.concat(held_rows, ignore_index=True) if held_rows else pd.DataFrame()
    out = {"method": result["method"], "held_flag_row_count": int(held.shape[0])}
    for col in ["institutional_missing_flag", "institutional_delay_flag", "margin_short_missing_flag", "margin_short_delay_flag"]:
        out[f"{col}_in_action_signal_rows_ratio"] = round(float(held[col].mean()), 6) if not held.empty else 0.0
    return out


def write_report(summary: dict[str, Any], full_rows: list[dict[str, Any]], common_rows: list[dict[str, Any]], rank_rows: list[dict[str, Any]], accounting: list[dict[str, Any]], concentration: list[dict[str, Any]], low_cov: list[dict[str, Any]]) -> None:
    treatment_full = next(row for row in full_rows if row["method"] == "o4_orthogonal_treatment_ltr")
    anchor_full = next(row for row in full_rows if row["method"] == "phase1c_anchor_simple")
    treatment_common = next(row for row in common_rows if row["method"] == "o4_orthogonal_treatment_ltr")
    anchor_common = next(row for row in common_rows if row["method"] == "phase1c_anchor_simple")
    lines = [
        "# Phase O5 执行报告：Controlled Replay Evaluation",
        "",
        f"生成时间：{summary['created_at']}",
        "",
        "## 1. Gate",
        "",
        f"推荐 gate：`{summary['gate']}`。",
        "",
        "## 2. 固定合同",
        "",
        f"- 窗口：`{START}..{END}`。",
        "- 回放：next-day execution、fee_rate `0.001425`、tax_rate `0.003`、target positions `10`。",
        f"- Control：`{CONTROL_COL}`，原 Phase1C anchor score column 未改。",
        f"- Treatment：`{TREATMENT_COL}`，回放候选按 `qlib_rank <= 50` 落实 `preserve_scope=top50_only`。",
        "- 本轮未训练 qlib/LTR，未修改 score artifact、窗口、label、特征、API、provider、accepted latest、monitor 或交易链路。",
        "",
        "## 3. Full Universe",
        "",
        f"- Phase1C anchor：return `{anchor_full['fee_tax_adjusted_net_return']}`，max DD `{anchor_full['max_drawdown']}`，actions `{anchor_full['action_count']}`。",
        f"- O4 treatment：return `{treatment_full['fee_tax_adjusted_net_return']}`，max DD `{treatment_full['max_drawdown']}`，actions `{treatment_full['action_count']}`，relative return `{treatment_full['relative_return_vs_phase1c_anchor']}`。",
        "",
        "## 4. O5 Pairwise Common Universe",
        "",
        f"- key count：`{summary['o5_pairwise_common_key_count']}`。",
        f"- Phase1C anchor：return `{anchor_common['fee_tax_adjusted_net_return']}`，max DD `{anchor_common['max_drawdown']}`，actions `{anchor_common['action_count']}`。",
        f"- O4 treatment：return `{treatment_common['fee_tax_adjusted_net_return']}`，max DD `{treatment_common['max_drawdown']}`，actions `{treatment_common['action_count']}`，relative return `{treatment_common['relative_return_vs_phase1c_anchor']}`。",
        "",
        "说明：O0/A1 冻结的 S2F common key count 为 `22474`，其 Phase1C common return 为 `0.641235`；O5 同时输出该来源说明，但主 common comparison 使用 Phase1C anchor 与 O4 treatment 的 pairwise replay key。",
        "",
        "## 5. Accounting",
        "",
        f"- next-day accounting pass：`{summary['next_day_accounting_pass']}`。",
        f"- full active actions：control `{anchor_full['action_count']}`，treatment `{treatment_full['action_count']}`。",
        "",
        "## 6. Ranking 与 PnL 审计",
        "",
        f"- treatment rank IC：`{next(row for row in rank_rows if row['method']=='o4_orthogonal_treatment_ltr' and row['universe']=='full_universe')['rank_ic_10d']}`。",
        f"- treatment NDCG@10/30/50：`{next(row for row in rank_rows if row['method']=='o4_orthogonal_treatment_ltr' and row['universe']=='full_universe')['ndcg_at_10']} / {next(row for row in rank_rows if row['method']=='o4_orthogonal_treatment_ltr' and row['universe']=='full_universe')['ndcg_at_30']} / {next(row for row in rank_rows if row['method']=='o4_orthogonal_treatment_ltr' and row['universe']=='full_universe')['ndcg_at_50']}`。",
        f"- treatment top symbol abs share：`{next(row for row in concentration if row['method']=='o4_orthogonal_treatment_ltr')['top_symbol_abs_share_of_total_net_pnl']}`。",
        f"- treatment top day abs share：`{next(row for row in concentration if row['method']=='o4_orthogonal_treatment_ltr')['top_day_abs_share_of_total_net_pnl']}`。",
        "",
        "## 7. Low Coverage",
        "",
        f"- low coverage audit rows：`{len(low_cov)}`。",
        "- 低覆盖股票持仓/交易/PnL 与 missing/delay flag 暴露已写入 `phaseo5_low_coverage_impact_audit.csv`。",
        "",
        "## 8. 输出产物",
        "",
    ]
    for name, path in summary["artifacts"].items():
        lines.append(f"- `{path}`")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    s2d = load_s2d()
    df = load_inputs()
    specs = {
        "phase1c_anchor_simple": s2d.MethodSpec("phase1c_anchor_simple", CONTROL_COL, 50, False),
        "o4_orthogonal_treatment_ltr": s2d.MethodSpec("o4_orthogonal_treatment_ltr", TREATMENT_REPLAY_COL, 50, False),
    }
    prices = s2d.PriceStore(set(df["instrument"].dropna().astype(str)))

    full_results = {name: s2d.replay(df, prices, spec, "o5_full_universe", START, END) for name, spec in specs.items()}
    anchor_full = full_results["phase1c_anchor_simple"]["metrics"]
    full_rows = [metric_row(full_results[name], anchor_full, "full_universe", 0) for name in specs]

    common = df[df[CONTROL_COL].notna() & df[TREATMENT_REPLAY_COL].notna()].copy()
    common_results = {name: s2d.replay(common, prices, spec, "o5_pairwise_common_universe", START, END) for name, spec in specs.items()}
    anchor_common = common_results["phase1c_anchor_simple"]["metrics"]
    common_rows = [metric_row(common_results[name], anchor_common, "o5_pairwise_common_universe", int(common.shape[0])) for name in specs]

    metric_fields = [
        "universe",
        "common_universe_key_count",
        "period",
        "start_date",
        "end_date",
        "method",
        "comparison_status",
        "fee_tax_adjusted_net_return",
        "final_equity",
        "max_drawdown",
        "action_count",
        "buy_count",
        "sell_count",
        "fee_and_tax",
        "turnover_proxy_by_notional_over_avg_equity",
        "turnover_notional",
        "trading_days",
        "initial_cash_or_equity_assumption",
        "fee_rate",
        "tax_rate",
        "position_count_target",
        "daily_nav_available_count",
        "missing_price_days",
        "skipped_trade_count",
        "last_day_new_trade_without_next_price_count",
        "relative_return_vs_phase1c_anchor",
        "relative_drawdown_vs_phase1c_anchor",
        "relative_actions_vs_phase1c_anchor",
    ]
    wcsv(OUT / "phaseo5_full_universe_metrics.csv", full_rows, metric_fields)
    wcsv(OUT / "phaseo5_common_universe_metrics.csv", common_rows, metric_fields)

    rank_rows = [
        ranking_metrics(df, CONTROL_COL, "phase1c_anchor_simple", "full_universe"),
        ranking_metrics(df, TREATMENT_REPLAY_COL, "o4_orthogonal_treatment_ltr", "full_universe"),
        ranking_metrics(common, CONTROL_COL, "phase1c_anchor_simple", "o5_pairwise_common_universe"),
        ranking_metrics(common, TREATMENT_REPLAY_COL, "o4_orthogonal_treatment_ltr", "o5_pairwise_common_universe"),
    ]
    wcsv(OUT / "phaseo5_rank_metrics.csv", rank_rows)

    nav_rows = []
    action_rows = []
    for result in full_results.values():
        nav_rows.extend(result["curve"])
        action_rows.extend(result["actions"])
    wcsv(OUT / "phaseo5_daily_nav.csv", nav_rows)
    wcsv(OUT / "phaseo5_action_audit.csv", action_rows)

    accounting = accounting_rows(full_results, "full_universe") + accounting_rows(common_results, "o5_pairwise_common_universe")
    wcsv(OUT / "phaseo5_next_day_accounting_audit.csv", accounting)
    wcsv(OUT / "phaseo5_monthly_performance.csv", period_performance(nav_rows, "M"))
    wcsv(OUT / "phaseo5_yearly_performance.csv", period_performance(nav_rows, "Y"))

    symbol_rows: list[dict[str, Any]] = []
    day_rows: list[dict[str, Any]] = []
    concentration: list[dict[str, Any]] = []
    for result in full_results.values():
        srows, drows, summary = pnl_contribution(result, prices)
        symbol_rows.extend(srows)
        day_rows.extend(drows)
        concentration.append(summary)
    wcsv(OUT / "phaseo5_pnl_contribution_by_symbol.csv", sorted(symbol_rows, key=lambda r: (r["method"], -abs(float(r["net_pnl"])))))
    wcsv(OUT / "phaseo5_pnl_contribution_by_day.csv", sorted(day_rows, key=lambda r: (r["method"], -abs(float(r["net_pnl"])))))
    wcsv(OUT / "phaseo5_pnl_concentration_summary.csv", concentration)

    low_cov = low_coverage_audit(df, full_results["o4_orthogonal_treatment_ltr"], symbol_rows)
    exposure_rows = [flag_exposure(df, result) for result in full_results.values()]
    low_cov.extend(exposure_rows)
    wcsv(OUT / "phaseo5_low_coverage_impact_audit.csv", low_cov)

    s2f_common_rows = pd.read_csv(S2F_COMMON).to_dict("records")
    key_audit = [
        {
            "common_universe_type": "o5_pairwise_common_universe",
            "definition": "Phase1C anchor score non-null and O4 treatment top50-preserve score non-null on same date/instrument",
            "key_count": int(common.shape[0]),
            "source": "recomputed in O5 from Phase3A0 frozen score and O4 row score",
            "phase1c_return": anchor_common["fee_tax_adjusted_net_return"],
            "phase1c_max_drawdown": anchor_common["max_drawdown"],
            "note": "Primary O5 common comparison universe.",
        },
        {
            "common_universe_type": "frozen_s2f_common_universe",
            "definition": "Phase1C anchor ∩ fresh top50 adaptive ∩ fresh LTR, frozen by S2F/A1",
            "key_count": 22474,
            "source": rel(S2F_COMMON),
            "phase1c_return": next(row for row in s2f_common_rows if row["method"] == "old_qlib_new_ltr_phase1c_simple")["fee_tax_adjusted_net_return"],
            "phase1c_max_drawdown": next(row for row in s2f_common_rows if row["method"] == "old_qlib_new_ltr_phase1c_simple")["max_drawdown"],
            "note": "Compatibility anchor from O0/A1; not the primary O5 pairwise treatment/control key set.",
        },
        {
            "common_universe_type": "full_universe",
            "definition": "method-specific available rows in 2025-07-01..2026-05-07",
            "key_count": int(df.shape[0]),
            "source": "merged Phase3A0 control and O4 treatment row scores",
            "phase1c_return": anchor_full["fee_tax_adjusted_net_return"],
            "phase1c_max_drawdown": anchor_full["max_drawdown"],
            "note": "Full universe metrics are not a common-key filter.",
        },
    ]
    wcsv(OUT / "phaseo5_common_universe_key_audit.csv", key_audit)

    importance = pd.read_csv(O4_IMPORTANCE).head(30)
    importance["source"] = rel(O4_IMPORTANCE)
    importance.to_csv(OUT / "phaseo5_o4_feature_importance_top30.csv", index=False)

    contract = {
        "created_at": now(),
        "phase": "phase_o5_controlled_replay_evaluation",
        "gate": "phase_o5_controlled_replay_evaluation_completed",
        "window": f"{START}..{END}",
        "replay_engine": rel(S2D_SCRIPT),
        "control_score_artifact": rel(CONTROL_SCORE),
        "control_score_column": CONTROL_COL,
        "treatment_score_artifact": rel(TREATMENT_SCORE),
        "treatment_score_column": TREATMENT_COL,
        "treatment_replay_score_column": TREATMENT_REPLAY_COL,
        "preserve_scope": "top50_only",
        "execution": "next-day execution",
        "fee_rate": 0.001425,
        "tax_rate": 0.003,
        "target_position_count": 10,
        "no_training": True,
        "no_score_modification": True,
        "no_frontend_api_provider_accepted_latest_monitor_trading": True,
    }
    wjson(OUT / "phaseo5_replay_manifest.json", contract)

    next_day_pass = all(row["pass"] == "yes" for row in accounting)
    summary = {
        **contract,
        "full_phase1c_anchor_return": anchor_full["fee_tax_adjusted_net_return"],
        "full_o4_treatment_return": full_results["o4_orthogonal_treatment_ltr"]["metrics"]["fee_tax_adjusted_net_return"],
        "full_o4_minus_anchor": round(full_results["o4_orthogonal_treatment_ltr"]["metrics"]["fee_tax_adjusted_net_return"] - anchor_full["fee_tax_adjusted_net_return"], 6),
        "o5_pairwise_common_key_count": int(common.shape[0]),
        "common_phase1c_anchor_return": anchor_common["fee_tax_adjusted_net_return"],
        "common_o4_treatment_return": common_results["o4_orthogonal_treatment_ltr"]["metrics"]["fee_tax_adjusted_net_return"],
        "common_o4_minus_anchor": round(common_results["o4_orthogonal_treatment_ltr"]["metrics"]["fee_tax_adjusted_net_return"] - anchor_common["fee_tax_adjusted_net_return"], 6),
        "frozen_s2f_common_key_count": 22474,
        "next_day_accounting_pass": next_day_pass,
        "artifacts": {
            "manifest": rel(OUT / "phaseo5_replay_manifest.json"),
            "full_universe_metrics": rel(OUT / "phaseo5_full_universe_metrics.csv"),
            "common_universe_metrics": rel(OUT / "phaseo5_common_universe_metrics.csv"),
            "rank_metrics": rel(OUT / "phaseo5_rank_metrics.csv"),
            "action_audit": rel(OUT / "phaseo5_action_audit.csv"),
            "next_day_accounting_audit": rel(OUT / "phaseo5_next_day_accounting_audit.csv"),
            "daily_nav": rel(OUT / "phaseo5_daily_nav.csv"),
            "monthly_performance": rel(OUT / "phaseo5_monthly_performance.csv"),
            "yearly_performance": rel(OUT / "phaseo5_yearly_performance.csv"),
            "pnl_contribution_by_symbol": rel(OUT / "phaseo5_pnl_contribution_by_symbol.csv"),
            "pnl_contribution_by_day": rel(OUT / "phaseo5_pnl_contribution_by_day.csv"),
            "pnl_concentration_summary": rel(OUT / "phaseo5_pnl_concentration_summary.csv"),
            "low_coverage_impact_audit": rel(OUT / "phaseo5_low_coverage_impact_audit.csv"),
            "common_universe_key_audit": rel(OUT / "phaseo5_common_universe_key_audit.csv"),
            "o4_feature_importance_top30": rel(OUT / "phaseo5_o4_feature_importance_top30.csv"),
            "summary": rel(OUT / "phaseo5_summary.json"),
            "report": rel(REPORT),
        },
    }
    wjson(OUT / "phaseo5_summary.json", summary)
    write_report(summary, full_rows, common_rows, rank_rows, accounting, concentration, low_cov)
    print(json.dumps({"ok": True, "gate": summary["gate"], "report": rel(REPORT)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
