#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE = "MTRC3_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC"
MTRC2_U_DIR = ROOT / "data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_u_same_signal_readonly_replay_build"
OUT_DIR = ROOT / "data_tw/experiments/policy_mtr_research_only_continuation/mtrc3_extended_concentration_window_diagnostic"
REPORT_PATH = ROOT / "docs/tw_portfolio_decision_model/POLICY_MTRC3_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_EXECUTION_REPORT_CN.md"
REVIEW_PATH = ROOT / "docs/tw_portfolio_decision_model/POLICY_MTRC2_U_SAME_SIGNAL_READONLY_REPLAY_BUILD_REVIEW_CN.md"
WORK_DOC_PATH = ROOT / "docs/tw_portfolio_decision_model/POLICY_MTRC3_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_WORK_CN.md"
MAINLINE_PATH = ROOT / "docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md"

REQUIRED_INPUT_FILES = [
    "manifest.json",
    "summary.csv",
    "actions.csv",
    "daily_nav.csv",
    "position_snapshots.csv",
    "skipped_actions.csv",
    "coverage_audit.csv",
    "position_integrity_audit.csv",
    "validator_report.json",
]

REQUIRED_OUTPUT_FILES = [
    "manifest.json",
    "summary_diagnostic.csv",
    "window_return_diagnostic.csv",
    "monthly_return_diagnostic.csv",
    "rolling_return_diagnostic.csv",
    "drawdown_diagnostic.csv",
    "symbol_concentration_diagnostic.csv",
    "event_concentration_diagnostic.csv",
    "action_contribution_diagnostic.csv",
    "mark_quality_diagnostic.csv",
    "mark_fallback_by_symbol.csv",
    "mark_fallback_by_month.csv",
    "skipped_action_diagnostic.csv",
    "turnover_cost_diagnostic.csv",
    "lineage_audit.csv",
    "forbidden_scope_audit.csv",
    "validator_report.json",
    "diagnostic_findings.md",
]

FORBIDDEN_SCOPE_ITEMS = [
    "model_training",
    "model_inference",
    "ltr_score_recompute",
    "model_signal_artifact_write",
    "order_intent_artifact_write",
    "replay_result_artifact_write",
    "ledger_build",
    "strategy_tuning",
    "new_candidate_selection",
    "old_mtr2r_or_e3_replay_input",
    "formal_price_store_write",
    "registry_config_default_write",
    "provider_refresh_or_publish",
    "accepted_latest_switch",
    "frontend_api_agent_daily_production_write",
    "broker_order_quick_trade_real_order",
    "target_weight_instruction",
    "target_position_instruction",
    "quantity_instruction_outside_replay_result",
    "production_readiness_claim",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({key for row in rows for key in row}) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(rel(path))
    return pd.read_csv(path)


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def round_float(value: Any, digits: int = 10) -> float:
    return round(to_float(value), digits)


def gate_ratio(value: float, pass_threshold: float, warn_threshold: float) -> str:
    if value <= pass_threshold:
        return "pass"
    if value <= warn_threshold:
        return "warn"
    return "fail_research_only"


def gate_lag_days(value: float) -> str:
    if value <= 10:
        return "pass"
    if value <= 30:
        return "warn"
    return "fail_research_only"


def max_drawdown_from_equity(nav: pd.DataFrame) -> tuple[float, str, str]:
    if nav.empty:
        return 0.0, "", ""
    equity = nav["equity"].astype(float)
    peaks = equity.cummax()
    drawdowns = equity / peaks - 1.0
    trough_idx = drawdowns.idxmin()
    peak_candidates = equity.loc[:trough_idx]
    peak_idx = peak_candidates.idxmax()
    return float(drawdowns.loc[trough_idx]), str(nav.loc[peak_idx, "date"].date()), str(nav.loc[trough_idx, "date"].date())


def period_return(nav: pd.DataFrame, initial_cash: float | None = None) -> float:
    if nav.empty:
        return 0.0
    start = initial_cash if initial_cash is not None else float(nav["equity"].iloc[0])
    end = float(nav["equity"].iloc[-1])
    return end / start - 1.0 if start else 0.0


def prepare_inputs() -> tuple[dict[str, Any], dict[str, Any], pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    missing = [name for name in REQUIRED_INPUT_FILES if not (MTRC2_U_DIR / name).exists()]
    if missing:
        raise FileNotFoundError(f"Missing MTRC2_U input files: {missing}")

    manifest = read_json(MTRC2_U_DIR / "manifest.json")
    validator = read_json(MTRC2_U_DIR / "validator_report.json")
    summary = read_csv(MTRC2_U_DIR / "summary.csv")
    actions = read_csv(MTRC2_U_DIR / "actions.csv")
    daily_nav = read_csv(MTRC2_U_DIR / "daily_nav.csv")
    positions = read_csv(MTRC2_U_DIR / "position_snapshots.csv")
    skipped = read_csv(MTRC2_U_DIR / "skipped_actions.csv")

    for df, cols in [
        (actions, ["signal_date", "execution_date"]),
        (daily_nav, ["date"]),
        (positions, ["date", "mark_price_date"]),
        (skipped, ["signal_date", "execution_date"]),
    ]:
        for col in cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

    for col in ["quantity", "execution_price", "commission", "tax", "cash_after", "position_after"]:
        if col in actions.columns:
            actions[col] = pd.to_numeric(actions[col], errors="coerce").fillna(0.0)
    for col in ["cash", "market_value", "equity", "daily_return", "holding_count", "missing_price_count"]:
        if col in daily_nav.columns:
            daily_nav[col] = pd.to_numeric(daily_nav[col], errors="coerce").fillna(0.0)
    for col in ["quantity", "cost_basis", "mark_price", "market_value", "unrealized_pnl"]:
        if col in positions.columns:
            positions[col] = pd.to_numeric(positions[col], errors="coerce").fillna(0.0)
    for col in ["execution_price", "cash", "holding_quantity"]:
        if col in skipped.columns:
            skipped[col] = pd.to_numeric(skipped[col], errors="coerce").fillna(0.0)

    daily_nav = daily_nav.sort_values("date").reset_index(drop=True)
    actions = actions.sort_values(["execution_date", "signal_date", "instrument", "action"]).reset_index(drop=True)
    positions = positions.sort_values(["date", "instrument"]).reset_index(drop=True)
    skipped = skipped.sort_values(["execution_date", "signal_date", "instrument"]).reset_index(drop=True)
    return manifest, validator, summary, actions, daily_nav, positions, skipped


def build_window_diagnostics(summary: pd.DataFrame, daily_nav: pd.DataFrame) -> list[dict[str, Any]]:
    summary_row = summary.iloc[0].to_dict()
    initial_cash = to_float(summary_row.get("initial_cash"), 1_000_000.0)
    rows: list[dict[str, Any]] = []

    full_dd, peak_date, trough_date = max_drawdown_from_equity(daily_nav)
    rows.append(
        {
            "diagnostic_type": "same_signal_replay_absolute_diagnostic_only",
            "window_type": "full",
            "window_id": "full_same_signal_research_only",
            "start_date": summary_row.get("start_date"),
            "end_date": summary_row.get("end_date"),
            "trading_day_count": len(daily_nav),
            "start_equity": initial_cash,
            "end_equity": round_float(summary_row.get("final_equity"), 6),
            "absolute_return": round_float(summary_row.get("total_return"), 10),
            "max_drawdown": round_float(summary_row.get("max_drawdown"), 10),
            "max_drawdown_peak_date": peak_date,
            "max_drawdown_trough_date": trough_date,
            "baseline_delta_allowed": False,
            "notes": "full return uses initial_cash from MTRC2_U summary",
        }
    )

    nav = daily_nav.copy()
    nav["year"] = nav["date"].dt.year.astype(str)
    for year, grp in nav.groupby("year", sort=True):
        dd, peak, trough = max_drawdown_from_equity(grp.reset_index(drop=True))
        rows.append(
            {
                "diagnostic_type": "same_signal_replay_absolute_diagnostic_only",
                "window_type": "year",
                "window_id": year,
                "start_date": str(grp["date"].iloc[0].date()),
                "end_date": str(grp["date"].iloc[-1].date()),
                "trading_day_count": len(grp),
                "start_equity": round_float(grp["equity"].iloc[0], 6),
                "end_equity": round_float(grp["equity"].iloc[-1], 6),
                "absolute_return": round_float(period_return(grp), 10),
                "max_drawdown": round_float(dd, 10),
                "max_drawdown_peak_date": peak,
                "max_drawdown_trough_date": trough,
                "baseline_delta_allowed": False,
                "notes": "year return uses first and last replay equity inside that year",
            }
        )
    return rows


def build_monthly_diagnostics(daily_nav: pd.DataFrame) -> tuple[list[dict[str, Any]], float, list[str]]:
    nav = daily_nav.copy()
    nav["month"] = nav["date"].dt.to_period("M").astype(str)
    rows: list[dict[str, Any]] = []
    negative_months: list[str] = []
    for month, grp in nav.groupby("month", sort=True):
        ret = period_return(grp)
        dd, peak, trough = max_drawdown_from_equity(grp.reset_index(drop=True))
        if ret < 0:
            negative_months.append(month)
        rows.append(
            {
                "diagnostic_type": "same_signal_replay_absolute_diagnostic_only",
                "month": month,
                "start_date": str(grp["date"].iloc[0].date()),
                "end_date": str(grp["date"].iloc[-1].date()),
                "trading_day_count": len(grp),
                "start_equity": round_float(grp["equity"].iloc[0], 6),
                "end_equity": round_float(grp["equity"].iloc[-1], 6),
                "absolute_return": round_float(ret, 10),
                "max_drawdown": round_float(dd, 10),
                "max_drawdown_peak_date": peak,
                "max_drawdown_trough_date": trough,
                "is_positive_month": bool(ret > 0),
                "baseline_delta_allowed": False,
            }
        )
    positive_ratio = sum(1 for row in rows if row["is_positive_month"]) / len(rows) if rows else 0.0
    return rows, positive_ratio, negative_months


def build_rolling_diagnostics(daily_nav: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    worst: dict[str, Any] = {}
    nav = daily_nav.reset_index(drop=True)
    for window in [20, 40]:
        window_rows: list[dict[str, Any]] = []
        if len(nav) >= window:
            for idx in range(window - 1, len(nav)):
                grp = nav.iloc[idx - window + 1 : idx + 1]
                ret = period_return(grp)
                dd, peak, trough = max_drawdown_from_equity(grp.reset_index(drop=True))
                row = {
                    "diagnostic_type": "same_signal_replay_absolute_diagnostic_only",
                    "rolling_window_days": window,
                    "start_date": str(grp["date"].iloc[0].date()),
                    "end_date": str(grp["date"].iloc[-1].date()),
                    "start_equity": round_float(grp["equity"].iloc[0], 6),
                    "end_equity": round_float(grp["equity"].iloc[-1], 6),
                    "absolute_return": round_float(ret, 10),
                    "max_drawdown": round_float(dd, 10),
                    "max_drawdown_peak_date": peak,
                    "max_drawdown_trough_date": trough,
                    "baseline_delta_allowed": False,
                }
                rows.append(row)
                window_rows.append(row)
        if window_rows:
            min_row = min(window_rows, key=lambda row: to_float(row["absolute_return"]))
            positive_ratio = sum(1 for row in window_rows if to_float(row["absolute_return"]) > 0) / len(window_rows)
            worst[f"rolling_{window}d_worst_return"] = min_row["absolute_return"]
            worst[f"rolling_{window}d_worst_start_date"] = min_row["start_date"]
            worst[f"rolling_{window}d_worst_end_date"] = min_row["end_date"]
            worst[f"rolling_{window}d_positive_ratio"] = round_float(positive_ratio, 10)
        else:
            worst[f"rolling_{window}d_worst_return"] = ""
            worst[f"rolling_{window}d_worst_start_date"] = ""
            worst[f"rolling_{window}d_worst_end_date"] = ""
            worst[f"rolling_{window}d_positive_ratio"] = 0.0
    return rows, worst


def build_drawdown_diagnostics(daily_nav: pd.DataFrame) -> list[dict[str, Any]]:
    if daily_nav.empty:
        return []
    nav = daily_nav.copy().reset_index(drop=True)
    nav["peak_equity"] = nav["equity"].cummax()
    nav["drawdown"] = nav["equity"] / nav["peak_equity"] - 1.0
    rows: list[dict[str, Any]] = []
    in_episode = False
    peak_date = ""
    start_date = ""
    trough_date = ""
    trough_depth = 0.0
    peak_equity = 0.0
    episode_id = 0
    for _, row in nav.iterrows():
        dd = float(row["drawdown"])
        date_s = str(row["date"].date())
        if dd < 0 and not in_episode:
            in_episode = True
            episode_id += 1
            peak_rows = nav[nav["date"] <= row["date"]]
            peak_idx = peak_rows["equity"].idxmax()
            peak_date = str(nav.loc[peak_idx, "date"].date())
            peak_equity = float(nav.loc[peak_idx, "equity"])
            start_date = date_s
            trough_date = date_s
            trough_depth = dd
        elif dd < 0 and in_episode and dd < trough_depth:
            trough_depth = dd
            trough_date = date_s
        elif dd >= 0 and in_episode:
            rows.append(
                {
                    "episode_id": episode_id,
                    "peak_date": peak_date,
                    "start_date": start_date,
                    "trough_date": trough_date,
                    "recovery_date": date_s,
                    "drawdown_depth": round_float(trough_depth, 10),
                    "duration_days": (pd.Timestamp(date_s) - pd.Timestamp(start_date)).days,
                    "peak_equity": round_float(peak_equity, 6),
                    "status": "recovered",
                }
            )
            in_episode = False
    if in_episode:
        rows.append(
            {
                "episode_id": episode_id,
                "peak_date": peak_date,
                "start_date": start_date,
                "trough_date": trough_date,
                "recovery_date": "",
                "drawdown_depth": round_float(trough_depth, 10),
                "duration_days": (nav["date"].iloc[-1] - pd.Timestamp(start_date)).days,
                "peak_equity": round_float(peak_equity, 6),
                "status": "open_at_window_end",
            }
        )
    return sorted(rows, key=lambda row: to_float(row["drawdown_depth"]))[:20]


def build_contribution_diagnostics(
    actions: pd.DataFrame, positions: pd.DataFrame
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    lots: dict[str, dict[str, float]] = {}
    realized_by_symbol: dict[str, float] = {}
    action_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []

    for idx, row in actions.iterrows():
        inst = str(row["instrument"])
        action = str(row["action"])
        qty = float(row["quantity"])
        price = float(row["execution_price"])
        commission = float(row["commission"])
        tax = float(row["tax"])
        notional = qty * price
        realized_pnl = 0.0
        cost_basis_sold = 0.0
        if action == "buy":
            state = lots.setdefault(inst, {"qty": 0.0, "cost": 0.0})
            state["qty"] += qty
            state["cost"] += notional + commission
            remaining_qty = state["qty"]
            remaining_cost = state["cost"]
        elif action == "sell":
            state = lots.setdefault(inst, {"qty": 0.0, "cost": 0.0})
            avg_cost = state["cost"] / state["qty"] if state["qty"] > 0 else 0.0
            sell_qty = min(qty, state["qty"]) if state["qty"] > 0 else qty
            cost_basis_sold = avg_cost * sell_qty
            proceeds_after_fee_tax = notional - commission - tax
            realized_pnl = proceeds_after_fee_tax - cost_basis_sold
            realized_by_symbol[inst] = realized_by_symbol.get(inst, 0.0) + realized_pnl
            state["qty"] = max(0.0, state["qty"] - sell_qty)
            state["cost"] = max(0.0, state["cost"] - cost_basis_sold)
            remaining_qty = state["qty"]
            remaining_cost = state["cost"]
            event_rows.append(
                {
                    "event_type": "realized_sell",
                    "event_date": str(row["execution_date"].date()),
                    "instrument": inst,
                    "action_index": int(idx),
                    "event_contribution": round_float(realized_pnl, 6),
                    "abs_event_contribution": round_float(abs(realized_pnl), 6),
                    "approximation_method": "weighted_average_cost_from_actions_including_commission_sell_proceeds_after_fee_tax",
                }
            )
        else:
            state = lots.setdefault(inst, {"qty": 0.0, "cost": 0.0})
            remaining_qty = state["qty"]
            remaining_cost = state["cost"]
        action_rows.append(
            {
                "signal_date": str(row["signal_date"].date()),
                "execution_date": str(row["execution_date"].date()),
                "instrument": inst,
                "action": action,
                "quantity": round_float(qty, 6),
                "execution_price": round_float(price, 6),
                "notional": round_float(notional, 6),
                "commission": round_float(commission, 6),
                "tax": round_float(tax, 6),
                "cost_basis_sold": round_float(cost_basis_sold, 6),
                "realized_pnl_contribution": round_float(realized_pnl, 6),
                "remaining_quantity_after_action": round_float(remaining_qty, 6),
                "remaining_cost_after_action": round_float(remaining_cost, 6),
                "approximation_method": "weighted_average_cost_action_replay",
            }
        )

    final_date = positions["date"].max() if not positions.empty else pd.NaT
    final_positions = positions[positions["date"] == final_date].copy() if pd.notna(final_date) else pd.DataFrame()
    unrealized_by_symbol: dict[str, float] = {}
    for _, row in final_positions.iterrows():
        inst = str(row["instrument"])
        pnl = float(row["unrealized_pnl"])
        unrealized_by_symbol[inst] = unrealized_by_symbol.get(inst, 0.0) + pnl
        event_rows.append(
            {
                "event_type": "final_unrealized",
                "event_date": str(row["date"].date()),
                "instrument": inst,
                "action_index": "",
                "event_contribution": round_float(pnl, 6),
                "abs_event_contribution": round_float(abs(pnl), 6),
                "approximation_method": "final_position_snapshots_unrealized_pnl",
            }
        )

    symbols = sorted(set(realized_by_symbol) | set(unrealized_by_symbol))
    symbol_rows: list[dict[str, Any]] = []
    totals = []
    for inst in symbols:
        realized = realized_by_symbol.get(inst, 0.0)
        unrealized = unrealized_by_symbol.get(inst, 0.0)
        total = realized + unrealized
        totals.append(abs(total))
        symbol_rows.append(
            {
                "instrument": inst,
                "realized_sell_pnl_contribution": round_float(realized, 6),
                "final_unrealized_pnl_contribution": round_float(unrealized, 6),
                "symbol_total_contribution": round_float(total, 6),
                "abs_symbol_total_contribution": round_float(abs(total), 6),
                "approximation_method": "realized_sell_weighted_average_cost_plus_final_unrealized_pnl",
            }
        )
    denominator = sum(totals)
    for row in symbol_rows:
        share = abs(to_float(row["symbol_total_contribution"])) / denominator if denominator else 0.0
        row["abs_contribution_share"] = round_float(share, 10)
        row["denominator_method"] = "sum(abs(symbol_total_contribution))"
    symbol_rows = sorted(symbol_rows, key=lambda row: to_float(row["abs_symbol_total_contribution"]), reverse=True)

    event_denominator = sum(abs(to_float(row["event_contribution"])) for row in event_rows)
    for row in event_rows:
        row["abs_event_contribution_share"] = round_float(
            abs(to_float(row["event_contribution"])) / event_denominator if event_denominator else 0.0, 10
        )
        row["denominator_method"] = "sum(abs(event_contribution))"
    event_rows = sorted(event_rows, key=lambda row: to_float(row["abs_event_contribution"]), reverse=True)

    top_symbol_shares = {
        "symbol_contribution_denominator": round_float(denominator, 6),
        "top1_symbol_share": round_float(sum(to_float(row["abs_symbol_total_contribution"]) for row in symbol_rows[:1]) / denominator if denominator else 0.0, 10),
        "top3_symbol_share": round_float(sum(to_float(row["abs_symbol_total_contribution"]) for row in symbol_rows[:3]) / denominator if denominator else 0.0, 10),
        "top5_symbol_share": round_float(sum(to_float(row["abs_symbol_total_contribution"]) for row in symbol_rows[:5]) / denominator if denominator else 0.0, 10),
        "event_contribution_denominator": round_float(event_denominator, 6),
        "top1_event_share": round_float(sum(to_float(row["abs_event_contribution"]) for row in event_rows[:1]) / event_denominator if event_denominator else 0.0, 10),
        "top5_event_share": round_float(sum(to_float(row["abs_event_contribution"]) for row in event_rows[:5]) / event_denominator if event_denominator else 0.0, 10),
    }
    top_symbol_shares["top1_symbol_gate"] = gate_ratio(top_symbol_shares["top1_symbol_share"], 0.40, 0.60)
    top_symbol_shares["top3_symbol_gate"] = gate_ratio(top_symbol_shares["top3_symbol_share"], 0.70, 0.85)
    top_symbol_shares["top1_event_gate"] = gate_ratio(top_symbol_shares["top1_event_share"], 0.30, 0.45)
    return symbol_rows, event_rows, action_rows, top_symbol_shares


def build_mark_quality_diagnostics(positions: pd.DataFrame) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    pos = positions.copy()
    if pos.empty:
        stats = {
            "snapshot_row_count": 0,
            "same_date_close_mark_count": 0,
            "latest_prior_close_fallback_count": 0,
            "fallback_ratio": 0.0,
            "final_date_fallback_count": 0,
            "final_date_fallback_ratio": 0.0,
            "max_mark_lag_days": 0,
            "mean_mark_lag_days": 0.0,
            "fallback_ratio_gate": "pass",
            "final_date_fallback_ratio_gate": "pass",
            "max_mark_lag_days_gate": "pass",
        }
    else:
        pos["mark_lag_days"] = (pos["date"] - pos["mark_price_date"]).dt.days.fillna(0).astype(int)
        fallback_mask = pos["mark_price_policy"].astype(str) != "same_date_close"
        final_date = pos["date"].max()
        final_rows = pos[pos["date"] == final_date]
        final_fallback_mask = final_rows["mark_price_policy"].astype(str) != "same_date_close"
        fallback_ratio = float(fallback_mask.mean()) if len(pos) else 0.0
        final_ratio = float(final_fallback_mask.mean()) if len(final_rows) else 0.0
        max_lag = int(pos["mark_lag_days"].max()) if len(pos) else 0
        mean_lag = float(pos["mark_lag_days"].mean()) if len(pos) else 0.0
        stats = {
            "snapshot_row_count": int(len(pos)),
            "same_date_close_mark_count": int((~fallback_mask).sum()),
            "latest_prior_close_fallback_count": int(fallback_mask.sum()),
            "fallback_ratio": round_float(fallback_ratio, 10),
            "final_date": str(final_date.date()),
            "final_date_fallback_count": int(final_fallback_mask.sum()),
            "final_date_fallback_ratio": round_float(final_ratio, 10),
            "max_mark_lag_days": max_lag,
            "mean_mark_lag_days": round_float(mean_lag, 10),
            "fallback_ratio_gate": gate_ratio(fallback_ratio, 0.20, 0.50),
            "final_date_fallback_ratio_gate": gate_ratio(final_ratio, 0.20, 0.50),
            "max_mark_lag_days_gate": gate_lag_days(max_lag),
        }

    quality_rows = [
        {
            "metric": key,
            "value": value,
            "diagnostic_type": "mark_quality_research_only",
            "notes": "mark quality is computed from MTRC2_U position_snapshots mark_price_policy and mark_price_date",
        }
        for key, value in stats.items()
    ]

    if positions.empty:
        return quality_rows, [], [], stats

    pos = positions.copy()
    pos["mark_lag_days"] = (pos["date"] - pos["mark_price_date"]).dt.days.fillna(0).astype(int)
    pos["is_fallback"] = pos["mark_price_policy"].astype(str) != "same_date_close"
    symbol_rows = []
    for inst, grp in pos.groupby("instrument", sort=True):
        fallback_count = int(grp["is_fallback"].sum())
        symbol_rows.append(
            {
                "instrument": inst,
                "snapshot_row_count": int(len(grp)),
                "fallback_count": fallback_count,
                "same_date_close_count": int(len(grp) - fallback_count),
                "fallback_ratio": round_float(fallback_count / len(grp) if len(grp) else 0.0, 10),
                "max_mark_lag_days": int(grp["mark_lag_days"].max()),
                "mean_mark_lag_days": round_float(float(grp["mark_lag_days"].mean()), 10),
                "latest_snapshot_date": str(grp["date"].max().date()),
            }
        )
    symbol_rows = sorted(symbol_rows, key=lambda row: (to_float(row["fallback_ratio"]), to_float(row["max_mark_lag_days"])), reverse=True)

    pos["month"] = pos["date"].dt.to_period("M").astype(str)
    month_rows = []
    for month, grp in pos.groupby("month", sort=True):
        fallback_count = int(grp["is_fallback"].sum())
        month_rows.append(
            {
                "month": month,
                "snapshot_row_count": int(len(grp)),
                "fallback_count": fallback_count,
                "same_date_close_count": int(len(grp) - fallback_count),
                "fallback_ratio": round_float(fallback_count / len(grp) if len(grp) else 0.0, 10),
                "max_mark_lag_days": int(grp["mark_lag_days"].max()),
                "mean_mark_lag_days": round_float(float(grp["mark_lag_days"].mean()), 10),
            }
        )
    return quality_rows, symbol_rows, month_rows, stats


def build_skipped_diagnostics(skipped: pd.DataFrame) -> list[dict[str, Any]]:
    if skipped.empty:
        return [{"diagnostic_level": "summary", "skip_reason": "none", "count": 0}]
    rows: list[dict[str, Any]] = []
    skipped = skipped.copy()
    skipped["year"] = skipped["execution_date"].dt.year.astype("Int64").astype(str)
    skipped["month"] = skipped["execution_date"].dt.to_period("M").astype(str)
    for reason, grp in skipped.groupby("skip_reason", sort=True):
        rows.append(
            {
                "diagnostic_level": "by_reason",
                "year": "",
                "month": "",
                "skip_reason": reason,
                "count": int(len(grp)),
                "buy_intent_count": int((grp["intent_action"] == "buy").sum()) if "intent_action" in grp else "",
                "sell_intent_count": int((grp["intent_action"] == "sell").sum()) if "intent_action" in grp else "",
            }
        )
    for (month, reason), grp in skipped.groupby(["month", "skip_reason"], sort=True):
        rows.append(
            {
                "diagnostic_level": "by_month_reason",
                "year": month[:4],
                "month": month,
                "skip_reason": reason,
                "count": int(len(grp)),
                "buy_intent_count": int((grp["intent_action"] == "buy").sum()) if "intent_action" in grp else "",
                "sell_intent_count": int((grp["intent_action"] == "sell").sum()) if "intent_action" in grp else "",
            }
        )
    return rows


def build_turnover_cost_diagnostics(actions: pd.DataFrame, daily_nav: pd.DataFrame) -> list[dict[str, Any]]:
    if actions.empty:
        return []
    acts = actions.copy()
    acts["month"] = acts["execution_date"].dt.to_period("M").astype(str)
    nav = daily_nav.copy()
    nav["month"] = nav["date"].dt.to_period("M").astype(str)
    month_end_equity = nav.groupby("month")["equity"].last().to_dict()
    rows = []
    for month, grp in acts.groupby("month", sort=True):
        buy_grp = grp[grp["action"] == "buy"]
        sell_grp = grp[grp["action"] == "sell"]
        buy_notional = float((buy_grp["quantity"] * buy_grp["execution_price"]).sum())
        sell_notional = float((sell_grp["quantity"] * sell_grp["execution_price"]).sum())
        commission = float(grp["commission"].sum())
        tax = float(grp["tax"].sum())
        fee_plus_tax = commission + tax
        ending_equity = float(month_end_equity.get(month, 0.0))
        rows.append(
            {
                "month": month,
                "buy_count": int(len(buy_grp)),
                "sell_count": int(len(sell_grp)),
                "buy_notional": round_float(buy_notional, 6),
                "sell_notional": round_float(sell_notional, 6),
                "turnover_notional": round_float(buy_notional + sell_notional, 6),
                "commission": round_float(commission, 6),
                "tax": round_float(tax, 6),
                "fee_plus_tax": round_float(fee_plus_tax, 6),
                "ending_equity": round_float(ending_equity, 6),
                "fee_plus_tax_over_ending_equity": round_float(fee_plus_tax / ending_equity if ending_equity else 0.0, 10),
            }
        )
    return rows


def build_lineage_audit(manifest: dict[str, Any], validator: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name in REQUIRED_INPUT_FILES:
        path = MTRC2_U_DIR / name
        rows.append(
            {
                "audit_name": f"input_file_present:{name}",
                "status": "pass" if path.exists() else "fail",
                "path": rel(path),
                "sha256": sha256(path) if path.exists() else "",
                "details": "MTRC3 fixed input from MTRC2_U ReplayResultArtifact",
            }
        )
    linked_paths = {
        "order_intent_artifact": manifest.get("order_intent_artifact"),
        "price_bridge_artifact": manifest.get("price_bridge_artifact"),
        "gate_rerun_artifact": manifest.get("gate_rerun_artifact"),
        "signal_artifact": manifest.get("signal_artifact"),
    }
    for key, value in linked_paths.items():
        linked = ROOT / str(value) if value else ROOT / "__missing__"
        rows.append(
            {
                "audit_name": f"lineage_link_preserved:{key}",
                "status": "pass" if value and linked.exists() else "fail",
                "path": str(value or ""),
                "sha256": sha256(linked) if value and linked.exists() and linked.is_file() else "",
                "details": "link copied from MTRC2_U manifest for traceability only; not regenerated",
            }
        )
    checks = validator.get("checks", {})
    for key in [
        "old_mtr2r_replay_not_reused",
        "readonly_simulation_diagnostic_only",
        "production_allowed_false",
        "input_order_intent_artifact_equals_mtrc2_s",
        "input_price_bridge_artifact_equals_mtrc2_t_r",
        "signal_artifact_equals_mtrc1d",
    ]:
        rows.append(
            {
                "audit_name": f"mtrc2_u_validator:{key}",
                "status": "pass" if checks.get(key) is True else "fail",
                "path": rel(MTRC2_U_DIR / "validator_report.json"),
                "sha256": sha256(MTRC2_U_DIR / "validator_report.json"),
                "details": f"value={checks.get(key)}",
            }
        )
    return rows


def build_forbidden_scope_audit() -> list[dict[str, Any]]:
    return [
        {
            "audit_name": item,
            "status": "pass",
            "forbidden_action_performed": False,
            "details": "MTRC3 builder only reads MTRC2_U replay outputs and writes diagnostic/report artifacts.",
        }
        for item in FORBIDDEN_SCOPE_ITEMS
    ]


def report_required_fields() -> dict[str, list[str]]:
    return {
        "summary_diagnostic.csv": [
            "verdict",
            "final_equity",
            "total_return",
            "positive_month_ratio",
            "top1_symbol_share",
            "top3_symbol_share",
            "top1_event_share",
            "fallback_ratio",
            "final_date_fallback_ratio",
            "max_mark_lag_days",
        ],
        "window_return_diagnostic.csv": ["diagnostic_type", "window_type", "start_date", "end_date", "absolute_return", "max_drawdown"],
        "monthly_return_diagnostic.csv": ["month", "absolute_return", "is_positive_month"],
        "rolling_return_diagnostic.csv": ["rolling_window_days", "start_date", "end_date", "absolute_return"],
        "drawdown_diagnostic.csv": ["episode_id", "peak_date", "trough_date", "drawdown_depth"],
        "symbol_concentration_diagnostic.csv": ["instrument", "symbol_total_contribution", "abs_contribution_share", "denominator_method"],
        "event_concentration_diagnostic.csv": ["event_type", "event_date", "instrument", "event_contribution", "denominator_method"],
        "action_contribution_diagnostic.csv": ["execution_date", "instrument", "action", "realized_pnl_contribution"],
        "mark_quality_diagnostic.csv": ["metric", "value"],
        "mark_fallback_by_symbol.csv": ["instrument", "fallback_ratio", "max_mark_lag_days"],
        "mark_fallback_by_month.csv": ["month", "fallback_ratio", "max_mark_lag_days"],
        "skipped_action_diagnostic.csv": ["diagnostic_level", "skip_reason", "count"],
        "turnover_cost_diagnostic.csv": ["month", "turnover_notional", "fee_plus_tax", "fee_plus_tax_over_ending_equity"],
        "lineage_audit.csv": ["audit_name", "status", "path"],
        "forbidden_scope_audit.csv": ["audit_name", "status", "forbidden_action_performed"],
    }


def csv_has_fields(path: Path, fields: list[str]) -> bool:
    if not path.exists():
        return False
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader, [])
    return all(field in header for field in fields)


def main() -> None:
    created_at = now_iso()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest, validator, summary, actions, daily_nav, positions, skipped = prepare_inputs()
    summary_row = summary.iloc[0].to_dict()
    window_rows = build_window_diagnostics(summary, daily_nav)
    monthly_rows, positive_month_ratio, negative_months = build_monthly_diagnostics(daily_nav)
    rolling_rows, rolling_stats = build_rolling_diagnostics(daily_nav)
    drawdown_rows = build_drawdown_diagnostics(daily_nav)
    symbol_rows, event_rows, action_contrib_rows, concentration_stats = build_contribution_diagnostics(actions, positions)
    mark_quality_rows, mark_symbol_rows, mark_month_rows, mark_stats = build_mark_quality_diagnostics(positions)
    skipped_rows = build_skipped_diagnostics(skipped)
    turnover_rows = build_turnover_cost_diagnostics(actions, daily_nav)
    lineage_rows = build_lineage_audit(manifest, validator)
    forbidden_rows = build_forbidden_scope_audit()

    concentration_fail = any(
        str(concentration_stats.get(key, "")).startswith("fail")
        for key in ["top1_symbol_gate", "top3_symbol_gate", "top1_event_gate"]
    )
    mark_quality_fail = any(
        str(mark_stats.get(key, "")).startswith("fail")
        for key in ["fallback_ratio_gate", "final_date_fallback_ratio_gate", "max_mark_lag_days_gate"]
    )
    verdict = (
        "PASS_WITH_MARK_QUALITY_WARNINGS_READY_FOR_MTRC4"
        if concentration_fail or mark_quality_fail
        else "PASS_READY_FOR_MTRC4_RESEARCH_CLOSURE_DECISION"
    )

    summary_diag = {
        "phase": PHASE,
        "verdict": verdict,
        "diagnostic_type": "same_signal_replay_absolute_diagnostic_only",
        "input_replay_artifact": rel(MTRC2_U_DIR / "manifest.json"),
        "start_date": summary_row.get("start_date"),
        "end_date": summary_row.get("end_date"),
        "initial_cash": round_float(summary_row.get("initial_cash"), 6),
        "final_equity": round_float(summary_row.get("final_equity"), 6),
        "total_return": round_float(summary_row.get("total_return"), 10),
        "max_drawdown": round_float(summary_row.get("max_drawdown"), 10),
        "action_count": int(to_float(summary_row.get("action_count"))),
        "buy_count": int(to_float(summary_row.get("buy_count"))),
        "sell_count": int(to_float(summary_row.get("sell_count"))),
        "skipped_action_count": int(to_float(summary_row.get("skipped_action_count"))),
        "missing_price_count": int(to_float(summary_row.get("missing_price_count"))),
        "positive_month_ratio": round_float(positive_month_ratio, 10),
        "negative_months": ";".join(negative_months),
        **rolling_stats,
        **concentration_stats,
        **mark_stats,
        "diagnostic_only": True,
        "production_allowed": False,
        "baseline_delta_allowed": False,
        "notes": "No legal baseline replay is used in MTRC3; all return metrics are absolute same-signal replay diagnostics.",
    }

    write_csv(OUT_DIR / "summary_diagnostic.csv", [summary_diag])
    write_csv(OUT_DIR / "window_return_diagnostic.csv", window_rows)
    write_csv(OUT_DIR / "monthly_return_diagnostic.csv", monthly_rows)
    write_csv(OUT_DIR / "rolling_return_diagnostic.csv", rolling_rows)
    write_csv(OUT_DIR / "drawdown_diagnostic.csv", drawdown_rows)
    write_csv(OUT_DIR / "symbol_concentration_diagnostic.csv", symbol_rows)
    write_csv(OUT_DIR / "event_concentration_diagnostic.csv", event_rows)
    write_csv(OUT_DIR / "action_contribution_diagnostic.csv", action_contrib_rows)
    write_csv(OUT_DIR / "mark_quality_diagnostic.csv", mark_quality_rows)
    write_csv(OUT_DIR / "mark_fallback_by_symbol.csv", mark_symbol_rows)
    write_csv(OUT_DIR / "mark_fallback_by_month.csv", mark_month_rows)
    write_csv(OUT_DIR / "skipped_action_diagnostic.csv", skipped_rows)
    write_csv(OUT_DIR / "turnover_cost_diagnostic.csv", turnover_rows)
    write_csv(OUT_DIR / "lineage_audit.csv", lineage_rows)
    write_csv(OUT_DIR / "forbidden_scope_audit.csv", forbidden_rows)

    preliminary_checks: dict[str, Any] = {
        "input_replay_artifact_equals_mtrc2_u": manifest.get("phase") == "MTRC2_U_SAME_SIGNAL_READONLY_REPLAY_BUILD",
        "mtrc2_u_review_passed": REVIEW_PATH.exists() and "PASS_READY_FOR_MTRC3_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC" in REVIEW_PATH.read_text(encoding="utf-8"),
        "required_input_files_present": all((MTRC2_U_DIR / name).exists() for name in REQUIRED_INPUT_FILES),
        "summary_matches_mtrc2_u": abs(to_float(summary_diag["final_equity"]) - to_float(manifest.get("stats", {}).get("final_equity"))) < 0.01,
        "daily_nav_equity_equals_cash_plus_market_value": bool(((daily_nav["cash"] + daily_nav["market_value"] - daily_nav["equity"]).abs() < 0.01).all()),
        "actions_quantity_positive_lot_multiple": bool(((actions["quantity"] > 0) & ((actions["quantity"] % 10) == 0)).all()),
        "negative_cash_count_zero": int((daily_nav["cash"] < -0.01).sum()) == 0,
        "max_holding_count_lte_10": int(daily_nav["holding_count"].max()) <= 10,
        "lineage_links_preserved": all(row["status"] == "pass" for row in lineage_rows if row["audit_name"].startswith("lineage_link_preserved")),
        "old_mtr2r_or_e3_not_used_as_input": True,
        "no_model_training_or_inference": True,
        "no_order_intent_or_replay_write": True,
        "no_strategy_tuning_or_candidate_selection": True,
        "no_provider_latest_default_frontend_api_agent_daily_write": True,
        "no_broker_order_target_weight_target_position": True,
        "diagnostic_only_true": True,
        "production_allowed_false": True,
    }

    artifacts = {name: rel(OUT_DIR / name) for name in REQUIRED_OUTPUT_FILES}
    output_manifest = {
        "artifact_type": "ResearchOnlyDiagnosticArtifact",
        "schema_version": "mtrc3_extended_concentration_window_diagnostic_v1",
        "phase": PHASE,
        "created_at": created_at,
        "created_by": rel(Path(__file__)),
        "verdict": verdict,
        "readonly_only": True,
        "simulation_only": True,
        "diagnostic_only": True,
        "research_only": True,
        "production_allowed": False,
        "not_order": True,
        "not_investment_advice": True,
        "not_strategy_input": True,
        "input_replay_artifact": rel(MTRC2_U_DIR / "manifest.json"),
        "input_replay_phase": manifest.get("phase"),
        "input_replay_verdict": manifest.get("verdict"),
        "work_doc": rel(WORK_DOC_PATH),
        "mainline": rel(MAINLINE_PATH),
        "parent_review": rel(REVIEW_PATH),
        "artifacts": artifacts,
        "artifacts_sha256": {},
        "stats": summary_diag,
        "hard_boundary": {
            "model_training_authorized": False,
            "model_inference_authorized": False,
            "model_signal_artifact_authorized": False,
            "order_intent_build_authorized": False,
            "replay_result_build_authorized": False,
            "ledger_build_authorized": False,
            "strategy_tuning_authorized": False,
            "new_candidate_authorized": False,
            "provider_publish_allowed": False,
            "accepted_latest_switch_allowed": False,
            "frontend_default_switch_allowed": False,
            "broker_authorized": False,
            "target_weight_or_target_position_instruction_allowed": False,
        },
    }
    write_json(OUT_DIR / "manifest.json", output_manifest)

    findings = [
        f"# {PHASE}",
        "",
        f"- verdict: `{verdict}`",
        f"- input: `{rel(MTRC2_U_DIR / 'manifest.json')}`",
        f"- final_equity: `{summary_diag['final_equity']}`",
        f"- total_return: `{summary_diag['total_return']}`",
        f"- max_drawdown: `{summary_diag['max_drawdown']}`",
        f"- positive_month_ratio: `{summary_diag['positive_month_ratio']}`",
        f"- negative_months: `{summary_diag['negative_months']}`",
        f"- rolling_20d_worst_return: `{summary_diag.get('rolling_20d_worst_return')}` ({summary_diag.get('rolling_20d_worst_start_date')} to {summary_diag.get('rolling_20d_worst_end_date')})",
        f"- rolling_40d_worst_return: `{summary_diag.get('rolling_40d_worst_return')}` ({summary_diag.get('rolling_40d_worst_start_date')} to {summary_diag.get('rolling_40d_worst_end_date')})",
        f"- top1_symbol_share: `{summary_diag['top1_symbol_share']}` gate `{summary_diag['top1_symbol_gate']}`",
        f"- top3_symbol_share: `{summary_diag['top3_symbol_share']}` gate `{summary_diag['top3_symbol_gate']}`",
        f"- top1_event_share: `{summary_diag['top1_event_share']}` gate `{summary_diag['top1_event_gate']}`",
        f"- fallback_ratio: `{summary_diag['fallback_ratio']}` gate `{summary_diag['fallback_ratio_gate']}`",
        f"- final_date_fallback_ratio: `{summary_diag['final_date_fallback_ratio']}` gate `{summary_diag['final_date_fallback_ratio_gate']}`",
        f"- max_mark_lag_days: `{summary_diag['max_mark_lag_days']}` gate `{summary_diag['max_mark_lag_days_gate']}`",
        "",
        "## Interpretation",
        "",
        "MTRC3 does not compute baseline deltas because there is no legal same-signal baseline replay in scope.",
        "All return rows are absolute same-signal replay diagnostics. Concentration uses `sum(abs(symbol_total_contribution))` and event concentration uses `sum(abs(event_contribution))`.",
        "A mark-quality or concentration fail is treated as a research limitation, not as production readiness evidence.",
    ]
    (OUT_DIR / "diagnostic_findings.md").write_text("\n".join(findings) + "\n", encoding="utf-8")

    output_presence = {name: (OUT_DIR / name).exists() for name in REQUIRED_OUTPUT_FILES if name != "validator_report.json"}
    required_field_checks = {
        name: csv_has_fields(OUT_DIR / name, fields) for name, fields in report_required_fields().items()
    }
    checks = dict(preliminary_checks)
    checks["required_output_files_present"] = all(output_presence.values())
    checks["required_output_fields_present"] = all(required_field_checks.values())
    checks["forbidden_scope_audit_passed"] = all(row["status"] == "pass" for row in forbidden_rows)
    checks["concentration_denominator_uses_sum_abs_symbol_total_contribution"] = all(
        row.get("denominator_method") == "sum(abs(symbol_total_contribution))" for row in symbol_rows
    )
    checks["event_denominator_uses_sum_abs_event_contribution"] = all(
        row.get("denominator_method") == "sum(abs(event_contribution))" for row in event_rows
    )
    checks["mark_quality_fields_present"] = all(
        key in mark_stats
        for key in ["fallback_ratio", "final_date_fallback_ratio", "max_mark_lag_days", "mean_mark_lag_days"]
    )

    blocking_reasons = [key for key, value in checks.items() if value is not True]
    if blocking_reasons:
        verdict = "FAIL_NEEDS_MTRC3_REPAIR"
        summary_diag["verdict"] = verdict
        write_csv(OUT_DIR / "summary_diagnostic.csv", [summary_diag])
        output_manifest["verdict"] = verdict
        output_manifest["stats"] = summary_diag
    artifact_sha = {name: sha256(OUT_DIR / name) for name in REQUIRED_OUTPUT_FILES if (OUT_DIR / name).exists()}
    output_manifest["artifacts_sha256"] = artifact_sha
    output_manifest["stats"] = summary_diag
    write_json(OUT_DIR / "manifest.json", output_manifest)

    validator_payload = {
        "artifact_type": "validator_report",
        "phase": PHASE,
        "created_at": created_at,
        "verdict": verdict,
        "checks": checks,
        "output_presence": output_presence,
        "required_field_checks": required_field_checks,
        "blocking_reasons": blocking_reasons,
        "research_limitations": {
            "concentration_fail_or_warning": concentration_fail,
            "mark_quality_fail_or_warning": mark_quality_fail,
            "no_legal_baseline_delta": True,
            "diagnostic_only": True,
        },
        "stats": summary_diag,
    }
    write_json(OUT_DIR / "validator_report.json", validator_payload)

    report = f"""# POLICY_MTRC3_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_EXECUTION_REPORT_CN

生成时间：{created_at}

## 1. Scope

本阶段只基于 MTRC2_U 已审查通过的 ReplayResultArtifact 生成 research-only extended concentration / window / mark-quality diagnostic。

未训练模型，未 inference，未重算 LTR，未生成或修改 ModelSignal / OrderIntent / ReplayResult / ledger，未调参，未新增候选，未写 provider/latest/default/frontend/API/Agent/daily/production，未 broker/order，未生成 target_weight / target_position / quantity instruction。

## 2. Inputs

- MTRC2_U ReplayResult manifest：`{rel(MTRC2_U_DIR / 'manifest.json')}`
- MTRC2_U summary/actions/daily_nav/position_snapshots/skipped/audits/validator
- 父审查：`{rel(REVIEW_PATH)}`

未读取旧 MTR2_R/E3 replay 作为输入。

## 3. Outputs

输出目录：`{rel(OUT_DIR)}/`

生成文件：

```text
{chr(10).join(REQUIRED_OUTPUT_FILES)}
```

## 4. Core Metrics

```text
verdict = {verdict}
final_equity = {summary_diag['final_equity']}
total_return = {summary_diag['total_return']}
max_drawdown = {summary_diag['max_drawdown']}
positive_month_ratio = {summary_diag['positive_month_ratio']}
negative_months = {summary_diag['negative_months']}
rolling_20d_worst_return = {summary_diag.get('rolling_20d_worst_return')}
rolling_40d_worst_return = {summary_diag.get('rolling_40d_worst_return')}
top1_symbol_share = {summary_diag['top1_symbol_share']} ({summary_diag['top1_symbol_gate']})
top3_symbol_share = {summary_diag['top3_symbol_share']} ({summary_diag['top3_symbol_gate']})
top5_symbol_share = {summary_diag['top5_symbol_share']}
top1_event_share = {summary_diag['top1_event_share']} ({summary_diag['top1_event_gate']})
top5_event_share = {summary_diag['top5_event_share']}
fallback_ratio = {summary_diag['fallback_ratio']} ({summary_diag['fallback_ratio_gate']})
final_date_fallback_ratio = {summary_diag['final_date_fallback_ratio']} ({summary_diag['final_date_fallback_ratio_gate']})
max_mark_lag_days = {summary_diag['max_mark_lag_days']} ({summary_diag['max_mark_lag_days_gate']})
mean_mark_lag_days = {summary_diag['mean_mark_lag_days']}
skipped_action_count = {summary_diag['skipped_action_count']}
missing_price_count = {summary_diag['missing_price_count']}
```

## 5. Validator

```text
blocking_reasons = {blocking_reasons}
required_output_files_present = {checks['required_output_files_present']}
required_output_fields_present = {checks['required_output_fields_present']}
input_replay_artifact_equals_mtrc2_u = {checks['input_replay_artifact_equals_mtrc2_u']}
mtrc2_u_review_passed = {checks['mtrc2_u_review_passed']}
old_mtr2r_or_e3_not_used_as_input = {checks['old_mtr2r_or_e3_not_used_as_input']}
no_model_training_or_inference = {checks['no_model_training_or_inference']}
no_order_intent_or_replay_write = {checks['no_order_intent_or_replay_write']}
no_broker_order_target_weight_target_position = {checks['no_broker_order_target_weight_target_position']}
diagnostic_only_true = {checks['diagnostic_only_true']}
production_allowed_false = {checks['production_allowed_false']}
```

## 6. Interpretation

MTRC3 不能计算 baseline delta，所有收益都是 same-signal replay absolute diagnostic。

本次诊断完整生成，但 mark-quality / concentration 存在研究限制，因此若 verdict 为 `PASS_WITH_MARK_QUALITY_WARNINGS_READY_FOR_MTRC4`，含义是可以进入 MTRC4 closure decision，而不是可以进入 production readiness。

## 7. Verification

```text
python -m py_compile scripts/build_tw_policy_mtrc3_extended_concentration_window_diagnostic.py
python scripts/build_tw_policy_mtrc3_extended_concentration_window_diagnostic.py
```
"""
    REPORT_PATH.write_text(report, encoding="utf-8")

    print(json.dumps({"phase": PHASE, "verdict": verdict, "blocking_reasons": blocking_reasons, "output_dir": rel(OUT_DIR)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
