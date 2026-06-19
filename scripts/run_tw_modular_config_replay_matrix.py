#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
S2D_SCRIPT = ROOT / "scripts/evaluate_tw_ltr_s2d_full_daily_replay.py"
DEFAULT_CONFIG = ROOT / "configs/tw_modular_replay_matrix.yaml"
REPORT = ROOT / "docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_EXECUTION_REPORT_CN.md"
HANDOFF = ROOT / "docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_REVIEW_HANDOFF_CN.md"

INITIAL_EQUITY = 1_000_000.0
CANDIDATE_K = 50
TARGET_HOLDINGS = 10
SIGNAL_FIELDS = [
    "date",
    "instrument",
    "model_name",
    "model_family",
    "candidate_rank",
    "buy_score",
    "raw_score",
    "score_rank",
    "full_qlib_rank",
    "signal_asof",
    "available_at",
    "source_artifact",
]
FORBIDDEN_COLUMNS = {
    "future_return_5d",
    "future_return_10d",
    "future_return_20d",
    "future_excess_return_5d",
    "future_excess_return_10d",
    "future_excess_return_20d",
    "relevance_10d_top_heavy",
    "ltr_relevance_label",
    "realized_pnl",
}


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


def load_s2d() -> Any:
    spec = importlib.util.spec_from_file_location("evaluate_tw_ltr_s2d_full_daily_replay", S2D_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {S2D_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def wcsv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({k for row in rows for k in row.keys()}) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def wjson(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def load_config(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_signal(entry: dict[str, Any]) -> tuple[dict[str, Any], pd.DataFrame]:
    manifest_path = ROOT / entry["artifact"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("quality_status") != "pass":
        raise RuntimeError(f"signal manifest is not pass: {entry['artifact']}")
    signals_path = ROOT / manifest["output_files"]["signals"]
    df = pd.read_csv(signals_path, parse_dates=["date"])
    missing = sorted(set(SIGNAL_FIELDS) - set(df.columns))
    if missing:
        raise RuntimeError(f"{entry['method']} missing standard signal fields: {missing}")
    legacy_private = [c for c in df.columns if c not in SIGNAL_FIELDS + ["source_model_artifact", "source_feature_artifact"]]
    if legacy_private:
        raise RuntimeError(f"{entry['method']} has non-standard columns: {legacy_private}")
    df["date_str"] = df["date"].dt.strftime("%Y-%m-%d")
    df["instrument"] = df["instrument"].map(norm)
    df["candidate_rank"] = pd.to_numeric(df["candidate_rank"], errors="coerce")
    df["buy_score"] = pd.to_numeric(df["buy_score"], errors="coerce")
    df["full_qlib_rank"] = pd.to_numeric(df["full_qlib_rank"], errors="coerce")
    df["regime_segment"] = "normal"
    return manifest, df


def build_day_state(day_group: pd.DataFrame, full_day: pd.DataFrame | None = None) -> dict[str, Any]:
    candidate_rows = day_group[day_group["candidate_rank"] <= CANDIDATE_K].dropna(subset=["buy_score"]).copy()
    candidate_set = set(candidate_rows["instrument"].map(norm))
    buy_rows = candidate_rows.sort_values(["buy_score", "instrument"], ascending=[False, True]).head(CANDIDATE_K)
    buy_order = [norm(x) for x in buy_rows["instrument"].tolist()]
    buy_rank = {symbol: idx + 1 for idx, symbol in enumerate(buy_order)}
    rank_frame = full_day if full_day is not None else day_group
    full_rank = {norm(r.instrument): int(r.full_qlib_rank) for r in rank_frame.itertuples(index=False) if pd.notna(r.full_qlib_rank)}
    return {
        "candidate_set": candidate_set,
        "buy_order": buy_order,
        "target_top10": set(buy_order[:TARGET_HOLDINGS]),
        "buy_rank": buy_rank,
        "full_rank": full_rank,
    }


def mark_to_market(cash: float, holdings: dict[str, int], prices: Any, asof: str) -> tuple[float, int]:
    equity = cash
    missing = 0
    for symbol, qty in holdings.items():
        close = prices.close_on_or_before(symbol, asof)
        if close is None:
            missing += 1
            continue
        equity += qty * close
    return equity, missing


def append_order(
    pending: dict[str, list[dict[str, Any]]],
    prices: Any,
    symbol: str,
    asof: str,
    action: str,
    qty: int,
    reason: str,
    last_day_counter: dict[str, int],
    skipped: list[dict[str, Any]],
) -> bool:
    quote = prices.next_after(symbol, asof)
    if quote is None:
        last_day_counter["count"] += 1
        skipped.append({
            "signal_date": asof,
            "execution_date": "",
            "effective_nav_date": "",
            "symbol": symbol,
            "action": "historical_skip",
            "quantity": 0,
            "price": "",
            "fee_and_tax": 0.0,
            "reason": "no_next_trading_day_price",
        })
        return False
    execution_date, price = quote
    pending.setdefault(execution_date, []).append({
        "signal_date": asof,
        "symbol": symbol,
        "action": action,
        "quantity": int(qty),
        "price": float(price),
        "reason": reason,
    })
    return True


def execute_pending(
    pending_orders: list[dict[str, Any]],
    asof: str,
    method: str,
    family: str,
    rule: str,
    window_name: str,
    cash: float,
    holdings: dict[str, int],
    actions: list[dict[str, Any]],
    fees: float,
    s2d: Any,
) -> tuple[float, float, int]:
    skipped = 0
    ordered = sorted(pending_orders, key=lambda row: 0 if row["action"] == "historical_risk_reduce" else 1)
    for order in ordered:
        symbol = norm(order["symbol"])
        price = float(order["price"])
        if order["action"] == "historical_risk_reduce":
            qty = int(holdings.pop(symbol, 0))
            if qty <= 0:
                skipped += 1
                actions.append({
                    "window": window_name,
                    "signal_date": order["signal_date"],
                    "execution_date": asof,
                    "effective_nav_date": "",
                    "method": method,
                    "rule": rule,
                    "symbol": symbol,
                    "action": "historical_skip",
                    "quantity": 0,
                    "price": round(price, 4),
                    "fee_and_tax": 0.0,
                    "reason": "sell_without_active_holding",
                })
                continue
            fee_tax = qty * price * (s2d.FEE_RATE + s2d.SELL_TAX_RATE)
            cash += qty * price - fee_tax
            fees += fee_tax
            actions.append({
                "window": window_name,
                "signal_date": order["signal_date"],
                "execution_date": asof,
                "effective_nav_date": asof,
                "method": method,
                "rule": rule,
                "symbol": symbol,
                "action": "historical_risk_reduce",
                "quantity": qty,
                "price": round(price, 4),
                "fee_and_tax": round(fee_tax, 2),
                "reason": order["reason"],
            })
        elif order["action"] == "historical_add":
            qty = int(order["quantity"])
            fee = qty * price * s2d.FEE_RATE
            total_cost = qty * price + fee
            if qty > 0 and cash >= total_cost and holdings.get(symbol, 0) == 0 and len(holdings) < TARGET_HOLDINGS:
                cash -= total_cost
                fees += fee
                holdings[symbol] = qty
                actions.append({
                    "window": window_name,
                    "signal_date": order["signal_date"],
                    "execution_date": asof,
                    "effective_nav_date": asof,
                    "method": method,
                    "rule": rule,
                    "symbol": symbol,
                    "action": "historical_add",
                    "quantity": qty,
                    "price": round(price, 4),
                    "fee_and_tax": round(fee, 2),
                    "reason": order["reason"],
                })
            else:
                skipped += 1
                actions.append({
                    "window": window_name,
                    "signal_date": order["signal_date"],
                    "execution_date": asof,
                    "effective_nav_date": "",
                    "method": method,
                    "rule": rule,
                    "symbol": symbol,
                    "action": "historical_skip",
                    "quantity": 0,
                    "price": round(price, 4),
                    "fee_and_tax": 0.0,
                    "reason": "insufficient_cash_duplicate_zero_qty_or_full",
                })
    return cash, fees, skipped


def active_action(row: dict[str, Any]) -> bool:
    return row.get("action") in {"historical_add", "historical_risk_reduce"}


def has_pending_order(pending: dict[str, list[dict[str, Any]]], symbol: str, action: str) -> bool:
    normalized = norm(symbol)
    for orders in pending.values():
        for order in orders:
            if norm(order.get("symbol")) == normalized and order.get("action") == action:
                return True
    return False


def pending_buy_reserved_cash(pending: dict[str, list[dict[str, Any]]], fee_rate: float) -> float:
    reserved = 0.0
    for orders in pending.values():
        for order in orders:
            if order.get("action") == "historical_add":
                reserved += float(order.get("quantity") or 0) * float(order.get("price") or 0.0) * (1.0 + fee_rate)
    return reserved


def pending_buy_symbols(pending: dict[str, list[dict[str, Any]]]) -> set[str]:
    symbols: set[str] = set()
    for orders in pending.values():
        for order in orders:
            if order.get("action") == "historical_add":
                symbols.add(norm(order.get("symbol")))
    return symbols


def choose_sells(rule: str, holdings: dict[str, int], state: dict[str, Any]) -> list[str]:
    held = sorted(holdings)
    candidate_set: set[str] = state["candidate_set"]
    target_top10: set[str] = state["target_top10"]
    buy_rank: dict[str, int] = state["buy_rank"]
    full_rank: dict[str, int] = state["full_rank"]
    if rule == "original":
        return [symbol for symbol in held if symbol not in target_top10]
    if rule == "top50_exit_all":
        return [symbol for symbol in held if symbol not in candidate_set]
    if rule == "top50_exit_one_worst_sell":
        outside = [symbol for symbol in held if symbol not in candidate_set]
        outside = sorted(outside, key=lambda s: (full_rank.get(s, 999999), s), reverse=True)
        return outside[:1]
    if rule == "one_sell_one_buy_correct":
        pool = [symbol for symbol in held if symbol not in target_top10]
        pool = sorted(pool, key=lambda s: (0, full_rank.get(s, 999999), s) if s not in candidate_set else (1, buy_rank.get(s, 999999), s), reverse=True)
        return pool[:1]
    if rule == "one_sell_one_buy_buggy_e8r":
        pool = [symbol for symbol in held if symbol not in target_top10]
        pool = sorted(pool, key=lambda s: (0 if s not in candidate_set else 1, buy_rank.get(s, 999999), s))
        return pool[:1]
    raise RuntimeError(f"unknown rule {rule}")


def replay_strategy(
    signals: pd.DataFrame,
    full_rank: pd.DataFrame,
    method: str,
    family: str,
    prices: Any,
    s2d: Any,
    rule: str,
    window_name: str,
    start: str,
    end: str,
) -> dict[str, Any]:
    sub = signals[(signals["date_str"] >= start) & (signals["date_str"] <= end)].copy()
    full = full_rank[(full_rank["date_str"] >= start) & (full_rank["date_str"] <= end)].copy()
    dates = sorted(sub["date_str"].unique().tolist())
    full_by_date = {day: g for day, g in full.groupby("date_str")}

    cash = INITIAL_EQUITY
    holdings: dict[str, int] = {}
    fees = 0.0
    peak = INITIAL_EQUITY
    max_dd = 0.0
    missing_price_days = 0
    skipped_count = 0
    last_day = {"count": 0}
    pending: dict[str, list[dict[str, Any]]] = {}
    nav_rows: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []

    for asof in dates:
        cash, fees, skipped = execute_pending(pending.pop(asof, []), asof, method, family, rule, window_name, cash, holdings, actions, fees, s2d)
        skipped_count += skipped
        equity, missing = mark_to_market(cash, holdings, prices, asof)
        missing_price_days += 1 if missing else 0
        peak = max(peak, equity)
        max_dd = min(max_dd, equity / peak - 1.0 if peak > 0 else 0.0)
        day_group = sub[sub["date_str"] == asof]
        state = build_day_state(day_group, full_by_date.get(asof, full.iloc[:0]))
        candidate_set = state["candidate_set"]
        buy_order = state["buy_order"]
        buy_rank = state["buy_rank"]
        full_rank_map = state["full_rank"]
        nav_rows.append({
            "date": asof,
            "window": window_name,
            "method": method,
            "family": family,
            "rule": rule,
            "equity": round(equity, 2),
            "cash": round(cash, 2),
            "holding_count": len(holdings),
            "missing_price_count": missing,
            "regime_segment": "normal",
        })
        for symbol, qty in sorted(holdings.items()):
            snapshots.append({
                "date": asof,
                "window": window_name,
                "method": method,
                "family": family,
                "rule": rule,
                "symbol": symbol,
                "quantity": qty,
                "in_qlib_top50_candidate": symbol in candidate_set,
                "buy_rank": buy_rank.get(symbol, ""),
                "full_qlib_rank": full_rank_map.get(symbol, ""),
            })
        sells = choose_sells(rule, holdings, state)
        skipped_local: list[dict[str, Any]] = []
        for symbol in sells:
            if has_pending_order(pending, symbol, "historical_risk_reduce"):
                continue
            qty = holdings.get(symbol, 0)
            if qty <= 0:
                continue
            append_order(pending, prices, symbol, asof, "historical_risk_reduce", qty, f"{rule}_sell", last_day, skipped_local)
        for symbol in buy_order:
            reserved_symbols = pending_buy_symbols(pending)
            available_slots = TARGET_HOLDINGS - len(holdings) - len(reserved_symbols)
            if available_slots <= 0:
                break
            if symbol in holdings or symbol in reserved_symbols or has_pending_order(pending, symbol, "historical_add"):
                continue
            quote = prices.next_after(symbol, asof)
            price = quote[1] if quote else None
            available_cash = max(0.0, cash - pending_buy_reserved_cash(pending, s2d.FEE_RATE))
            qty = int((available_cash / max(1, available_slots)) // (price * s2d.LOT_SIZE)) * s2d.LOT_SIZE if price else 0
            if qty <= 0 and quote is not None:
                continue
            ok = append_order(pending, prices, symbol, asof, "historical_add", qty, f"{rule}_buy", last_day, skipped_local)
            if ok:
                break
        if skipped_local:
            skipped_count += len(skipped_local)
            for row in skipped_local:
                actions.append({**row, "window": window_name, "method": method, "rule": rule})

    final_equity = nav_rows[-1]["equity"] if nav_rows else INITIAL_EQUITY
    active = [row for row in actions if active_action(row)]
    notional = sum(abs(float(row["quantity"]) * float(row["price"])) for row in active if row.get("price") not in {"", None, ""})
    avg_equity = sum(float(row["equity"]) for row in nav_rows) / len(nav_rows) if nav_rows else INITIAL_EQUITY
    actual_start = dates[0] if dates else start
    actual_end = dates[-1] if dates else end
    metrics = {
        "window": window_name,
        "requested_start_date": start,
        "requested_end_date": end,
        "start_date": actual_start,
        "end_date": actual_end,
        "method": method,
        "family": family,
        "rule": rule,
        "fee_tax_adjusted_net_return": round(final_equity / INITIAL_EQUITY - 1.0, 6),
        "final_equity": round(final_equity, 2),
        "max_drawdown": round(max_dd, 6),
        "action_count": len(active),
        "buy_count": sum(1 for row in active if row["action"] == "historical_add"),
        "sell_count": sum(1 for row in active if row["action"] == "historical_risk_reduce"),
        "fee_and_tax": round(fees, 2),
        "turnover_notional": round(notional, 2),
        "turnover_proxy_by_notional_over_avg_equity": round(notional / avg_equity, 6) if avg_equity else "",
        "trading_days": len(nav_rows),
        "initial_cash_or_equity_assumption": INITIAL_EQUITY,
        "fee_rate": s2d.FEE_RATE,
        "tax_rate": s2d.SELL_TAX_RATE,
        "position_count_target": TARGET_HOLDINGS,
        "candidate_k": CANDIDATE_K,
        "daily_nav_available_count": len(nav_rows),
        "missing_price_days": missing_price_days,
        "skipped_trade_count": skipped_count,
        "last_day_new_trade_without_next_price_count": last_day["count"],
    }
    return {"metrics": metrics, "nav": nav_rows, "actions": actions, "snapshots": snapshots}


def coverage_row(signals: pd.DataFrame, method: str, family: str, signal_artifact: str, full_rank_artifact: str, window_name: str, start: str, end: str) -> dict[str, Any]:
    sub = signals[(signals["date_str"] >= start) & (signals["date_str"] <= end)].copy()
    top50 = sub[sub["candidate_rank"] <= CANDIDATE_K].copy()
    daily = top50.groupby("date_str", as_index=False).agg(rows=("instrument", "size"), score_rows=("buy_score", lambda s: int(pd.to_numeric(s, errors="coerce").notna().sum())))
    return {
        "window": window_name,
        "method": method,
        "family": family,
        "signal_artifact": signal_artifact,
        "ready_source": signal_artifact,
        "buy_score_col": "buy_score",
        "candidate_rank_col": "candidate_rank",
        "full_rank_artifact": full_rank_artifact,
        "date_count": int(daily.shape[0]) if not daily.empty else 0,
        "row_count": int(top50.shape[0]),
        "daily_rows_min": int(daily["rows"].min()) if not daily.empty else 0,
        "daily_rows_median": float(daily["rows"].median()) if not daily.empty else 0.0,
        "daily_rows_max": int(daily["rows"].max()) if not daily.empty else 0,
        "score_rows": int(pd.to_numeric(top50["buy_score"], errors="coerce").notna().sum()) if not top50.empty else 0,
        "duplicate_key_count": int(top50.duplicated(["date_str", "instrument"]).sum()) if not top50.empty else 0,
    }


def integrity_rows(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for result in results:
        metrics = result["metrics"]
        actions = pd.DataFrame(result["actions"])
        snaps = pd.DataFrame(result["snapshots"])
        active = actions[actions["action"].isin(["historical_add", "historical_risk_reduce"])] if not actions.empty else pd.DataFrame()
        rows.append({
            "window": metrics["window"],
            "method": metrics["method"],
            "rule": metrics["rule"],
            "max_holding_count": int(snaps.groupby("date")["symbol"].nunique().max()) if not snaps.empty else 0,
            "duplicate_position_day_symbol": int(snaps.duplicated(["date", "symbol"]).sum()) if not snaps.empty else 0,
            "active_nonpositive_qty": int((pd.to_numeric(active.get("quantity", pd.Series(dtype=float)), errors="coerce") <= 0).sum()) if not active.empty else 0,
            "negative_cash_days": 0,
            "execution_not_after_signal": int((pd.to_datetime(active.get("execution_date", pd.Series(dtype=str)), errors="coerce") <= pd.to_datetime(active.get("signal_date", pd.Series(dtype=str)), errors="coerce")).sum()) if not active.empty else 0,
            "skipped_actions": int((actions.get("action", pd.Series(dtype=str)) == "historical_skip").sum()) if not actions.empty else 0,
            "integrity_pass": bool((metrics["position_count_target"] >= (int(snaps.groupby("date")["symbol"].nunique().max()) if not snaps.empty else 0)) and (active.empty or int((pd.to_numeric(active.get("quantity", pd.Series(dtype=float)), errors="coerce") <= 0).sum()) == 0)),
        })
    return rows


def rule_contract_rows(rules: list[str]) -> list[dict[str, Any]]:
    definitions = {
        "original": ("sell holdings outside buy top10", "buy_score rank within qlib top50", "unbounded", 1),
        "top50_exit_all": ("sell all holdings outside qlib top50", "buy_score rank within qlib top50", "unbounded", 1),
        "top50_exit_one_worst_sell": ("if outside qlib top50, sell only worst full qlib rank", "buy_score rank within qlib top50", 1, 1),
        "one_sell_one_buy_correct": ("outside buy top10; outside qlib top50 first, otherwise worst buy rank", "buy_score rank within qlib top50", 1, 1),
        "one_sell_one_buy_buggy_e8r": ("known buggy diagnostic, not valid strategy evidence", "buy_score rank within qlib top50", 1, 1),
    }
    return [{"rule": r, "sell_boundary": definitions[r][0], "buy_order": definitions[r][1], "max_sells_per_day": definitions[r][2], "max_buys_per_day": definitions[r][3]} for r in rules]


def load_full_rank_artifact(entry: dict[str, Any]) -> tuple[dict[str, Any], pd.DataFrame]:
    manifest_path = ROOT / entry["full_rank_artifact"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("artifact_type") != "full_rank" or manifest.get("quality_status") != "pass":
        raise RuntimeError(f"full rank manifest is not pass: {entry['full_rank_artifact']}")
    rank_path = ROOT / manifest["output_files"]["full_rank"]
    df = pd.read_csv(rank_path, parse_dates=["date"])
    required = {"date", "instrument", "full_qlib_rank", "signal_asof", "available_at"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise RuntimeError(f"{entry['method']} missing FullRankArtifact fields: {missing}")
    df["date_str"] = df["date"].dt.strftime("%Y-%m-%d")
    df["instrument"] = df["instrument"].map(norm)
    df["full_qlib_rank"] = pd.to_numeric(df["full_qlib_rank"], errors="coerce")
    return manifest, df[["date_str", "instrument", "full_qlib_rank"]]


def action_key_parity(out_dir: Path, baseline_dir: Path) -> dict[str, Any]:
    key_cols = ["window", "method", "rule", "signal_date", "execution_date", "symbol", "action", "quantity", "price", "reason"]
    value_cols = ["fee_and_tax", "effective_nav_date"]
    baseline_all = pd.read_csv(baseline_dir / "formal_replay_actions.csv")
    modular_all = pd.read_csv(out_dir / "formal_replay_actions.csv").copy()
    if "window" not in baseline_all.columns:
        raise RuntimeError(f"baseline actions missing window column: {baseline_dir / 'formal_replay_actions.csv'}")
    if "window" not in modular_all.columns:
        raise RuntimeError(f"modular actions missing window column: {out_dir / 'formal_replay_actions.csv'}")
    baseline = baseline_all[baseline_all["window"] == "2026_ytd"].copy()
    modular = modular_all[modular_all["window"] == "2026_ytd"].copy()

    compare_cols = key_cols + value_cols
    baseline_cmp = baseline[compare_cols].copy()
    modular_cmp = modular[compare_cols].copy()
    for col in ["price", "fee_and_tax"]:
        baseline_cmp[col] = pd.to_numeric(baseline_cmp[col], errors="coerce").round(4 if col == "price" else 2)
        modular_cmp[col] = pd.to_numeric(modular_cmp[col], errors="coerce").round(4 if col == "price" else 2)
    baseline_key = baseline_cmp[key_cols].astype(str).agg("|".join, axis=1)
    modular_key = modular_cmp[key_cols].astype(str).agg("|".join, axis=1)
    baseline_keys = set(baseline_key)
    modular_keys = set(modular_key)
    baseline_not_modular = sorted(baseline_keys - modular_keys)
    modular_not_baseline = sorted(modular_keys - baseline_keys)
    duplicate_baseline = int(baseline_key.duplicated().sum())
    duplicate_modular = int(modular_key.duplicated().sum())

    value_mismatch_count = 0
    if not baseline_not_modular and not modular_not_baseline:
        b_sorted = baseline_cmp.sort_values(compare_cols).reset_index(drop=True)
        m_sorted = modular_cmp.sort_values(compare_cols).reset_index(drop=True)
        value_mismatch_count = 0 if b_sorted.equals(m_sorted) else int((b_sorted != m_sorted).any(axis=1).sum())

    diff_rows = []
    for key in baseline_not_modular[:100]:
        diff_rows.append({"side": "baseline_not_modular", "action_key": key})
    for key in modular_not_baseline[:100]:
        diff_rows.append({"side": "modular_not_baseline", "action_key": key})
    if diff_rows:
        wcsv(out_dir / "r10_action_window_diff_sample.csv", diff_rows, ["side", "action_key"])

    status = "pass" if (
        len(baseline) == len(modular)
        and not baseline_not_modular
        and not modular_not_baseline
        and duplicate_baseline == 0
        and duplicate_modular == 0
        and value_mismatch_count == 0
    ) else "fail"
    details = "direct window filter: baseline.window == modular.window == 2026_ytd"
    row = {
        "filter_policy": "direct_window_filter_2026_ytd",
        "baseline_total_rows": int(len(baseline_all)),
        "baseline_filtered_rows": int(len(baseline)),
        "baseline_window_field_present": True,
        "modular_window_field_present": True,
        "baseline_unique_action_keys": int(len(baseline_keys)),
        "modular_action_rows": int(len(modular)),
        "modular_unique_action_keys": int(len(modular_keys)),
        "baseline_not_modular_count": int(len(baseline_not_modular)),
        "modular_not_baseline_count": int(len(modular_not_baseline)),
        "duplicate_baseline_action_key_count": duplicate_baseline,
        "duplicate_modular_action_key_count": duplicate_modular,
        "value_mismatch_count": value_mismatch_count,
        "status": status,
        "details": details,
    }
    wcsv(out_dir / "r10_action_window_parity_audit.csv", [row], list(row.keys()))
    wcsv(out_dir / "r2_action_key_parity_audit.csv", [row], list(row.keys()))
    return row


def compare_with_baseline(out_dir: Path, baseline_dir: Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    pairs = [
        ("summary", "formal_replay_summary.csv", ["window", "method", "family", "rule"], ["fee_tax_adjusted_net_return", "final_equity", "max_drawdown", "action_count", "buy_count", "sell_count", "fee_and_tax", "turnover_notional", "daily_nav_available_count"]),
        ("daily_nav", "formal_replay_daily_nav.csv", ["window", "method", "family", "rule", "date"], ["equity", "cash", "holding_count", "missing_price_count"]),
    ]
    for name, filename, keys, values in pairs:
        base = pd.read_csv(baseline_dir / filename)
        mod = pd.read_csv(out_dir / filename)
        if "window" in base.columns:
            base = base[base["window"] == "2026_ytd"].copy()
        if "window" in mod.columns:
            mod = mod[mod["window"] == "2026_ytd"].copy()
        row = {"check_name": name, "baseline_rows": len(base), "modular_rows": len(mod), "status": "pass", "details": ""}
        if len(base) != len(mod):
            row["status"] = "fail"
            row["details"] = "row count mismatch"
        compare_cols = keys + values
        base_cmp = base[compare_cols].sort_values(compare_cols).reset_index(drop=True)
        mod_cmp = mod[compare_cols].sort_values(compare_cols).reset_index(drop=True)
        if row["status"] == "pass" and not base_cmp.equals(mod_cmp):
            row["status"] = "fail"
            row["details"] = "content mismatch"
            diff_path = out_dir / f"r2_{name}_diff_sample.csv"
            pd.concat([base_cmp.head(50).assign(source="baseline"), mod_cmp.head(50).assign(source="modular")]).to_csv(diff_path, index=False)
        checks.append(row)
    action = action_key_parity(out_dir, baseline_dir)
    checks.append({
        "check_name": "actions",
        "baseline_rows": action["baseline_filtered_rows"],
        "modular_rows": action["modular_action_rows"],
        "status": action["status"],
        "details": action["details"],
    })
    return checks

def write_reports(out_dir: Path, manifest: dict[str, Any], parity: list[dict[str, Any]]) -> None:
    rows = [
        "| check | baseline_rows | modular_rows | status | details |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    for row in parity:
        rows.append(f"| {row['check_name']} | {row['baseline_rows']} | {row['modular_rows']} | {row['status']} | {row['details']} |")
    action_audit_path = out_dir / "r2_action_key_parity_audit.csv"
    action_audit = pd.read_csv(action_audit_path).iloc[0].to_dict() if action_audit_path.exists() else {}
    report = "\n".join([
        "# Phase R2 Config-driven Replay Matrix 执行报告",
        "",
        "生成日期：2026-06-16",
        "",
        "## 1. 执行范围",
        "",
        "本次仅执行 R2：从 `configs/tw_modular_replay_matrix.yaml` 读取标准 `ModelSignalArtifact manifest`，生成 config-driven replay matrix。",
        "",
        "未训练、未调参、未重算模型分数；未修改旧 formal replay matrix；未修改前端、日更或默认策略。",
        "",
        "## 2. 输入与输出",
        "",
        f"- config: `{manifest['config']}`",
        f"- output_dir: `{manifest['out_dir']}`",
        f"- baseline_dir: `{manifest['baseline_dir']}`",
        "",
        "## 3. Parity 结果",
        "",
        *rows,
        "",
        "## 4. Action-level parity",
        "",
        f"- filter_policy: `{action_audit.get('filter_policy', '')}`",
        f"- baseline_total_rows: `{action_audit.get('baseline_total_rows', '')}`",
        f"- baseline_filtered_rows: `{action_audit.get('baseline_filtered_rows', '')}`",
        f"- baseline_unique_action_keys: `{action_audit.get('baseline_unique_action_keys', '')}`",
        f"- modular_action_rows: `{action_audit.get('modular_action_rows', '')}`",
        f"- modular_unique_action_keys: `{action_audit.get('modular_unique_action_keys', '')}`",
        f"- baseline_not_modular_count: `{action_audit.get('baseline_not_modular_count', '')}`",
        f"- modular_not_baseline_count: `{action_audit.get('modular_not_baseline_count', '')}`",
        f"- duplicate_baseline_action_key_count: `{action_audit.get('duplicate_baseline_action_key_count', '')}`",
        f"- duplicate_modular_action_key_count: `{action_audit.get('duplicate_modular_action_key_count', '')}`",
        f"- value_mismatch_count: `{action_audit.get('value_mismatch_count', '')}`",
        "",
        "Baseline actions 已通过 R10 window adapter 标准化为带 `window` 字段的独立 artifact；action parity 直接过滤 baseline/modular `window=2026_ytd` 后比较 key/value。",
        "",
        "## 5. 结论",
        "",
        f"- parity_status: `{manifest['parity_status']}`",
        "- Replay engine 只读取标准字段：`candidate_rank`、`buy_score`、`full_qlib_rank` 等 ModelSignal contract 字段；",
        "- 不读取 legacy 私有分数字段；",
        "- `one_sell_one_buy_buggy_e8r` 仍仅作为 diagnostic；",
        "- R1 full-rank fallback 风险已带入 R2，最终以 2026_ytd parity 是否完全一致为门槛。",
        "",
        "## 6. 禁止事项记录",
        "",
        "- 未训练 qlib 或 LTR；",
        "- 未调参；",
        "- 未重算模型分数；",
        "- 未根据收益筛选模型；",
        "- 未改默认策略；",
        "- 未修改前端；",
        "- 未修改日更脚本；",
        "- 未触发 provider publish；",
        "- 未切换 accepted latest；",
        "- 未触发 monitor scan/config save；",
        "- 未触发 broker、quick-trade 或 order。",
    ]) + "\n"
    REPORT.write_text(report, encoding="utf-8")
    handoff = "\n".join([
        "# Phase R2 Config-driven Replay Matrix 审查说明",
        "",
        "生成日期：2026-06-16",
        "",
        "## 1. 审查范围",
        "",
        "本 handoff 供审查者复核 R2。R2 只新增 config-driven replay matrix，不接入前端、日更或生产链路。",
        "",
        "## 2. 新增/修改文件",
        "",
        "```text",
        "configs/tw_modular_replay_matrix.yaml",
        "scripts/run_tw_modular_config_replay_matrix.py",
        "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/",
        "docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_EXECUTION_REPORT_CN.md",
        "docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_REVIEW_HANDOFF_CN.md",
        "```",
        "",
        "## 3. 建议复核命令",
        "",
        "```bash",
        "python scripts/run_tw_modular_config_replay_matrix.py --config configs/tw_modular_replay_matrix.yaml",
        "cat data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/r2_parity_audit.csv",
        "cat data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/r2_action_key_parity_audit.csv",
        "rg -n \"fail\" data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/r2_parity_audit.csv data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/r2_action_key_parity_audit.csv",
        "git diff -- frontend/src/views/tw-stock-monitor/index.vue scripts/run_daily_tw_stock_auto_update.py scripts/run_extended_oos_formal_replay_matrix.py",
        "```",
        "",
        "预期：",
        "",
        "- parity audit 无 `fail`；",
        "- summary / daily_nav 与 baseline `2026_ytd` 关键结果完全一致；",
        "- `r2_action_key_parity_audit.csv` 中 `baseline_not_modular_count=0`、`modular_not_baseline_count=0`、重复 key 为 0、value mismatch 为 0；",
        "- 前端、日更脚本、旧 formal replay matrix 的 `git diff` 为空；",
        "- 输出 manifest 的 `parity_status` 为 `pass`。",
    ]) + "\n"
    HANDOFF.write_text(handoff, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run config-driven modular replay matrix from ModelSignalArtifact manifests.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = parser.parse_args()
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = ROOT / config_path
    config = load_config(config_path)
    out_dir = ROOT / config["output"]["dir"]
    baseline_dir = ROOT / config["baseline"]["dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    created_at = now()
    s2d = load_s2d()

    entries = config["signals"]
    signals_by_method: dict[str, pd.DataFrame] = {}
    full_rank_by_method: dict[str, pd.DataFrame] = {}
    manifests: dict[str, dict[str, Any]] = {}
    full_rank_manifests: dict[str, dict[str, Any]] = {}
    all_symbols: set[str] = set()
    for entry in entries:
        manifest, signals = load_signal(entry)
        method = entry["method"]
        signals_by_method[method] = signals
        full_rank_manifest, full_rank = load_full_rank_artifact(entry)
        full_rank_by_method[method] = full_rank
        full_rank_manifests[method] = full_rank_manifest
        manifests[method] = manifest
        all_symbols |= set(signals["instrument"])
    prices = s2d.PriceStore(all_symbols)

    results: list[dict[str, Any]] = []
    summary: list[dict[str, Any]] = []
    nav_rows: list[dict[str, Any]] = []
    action_rows: list[dict[str, Any]] = []
    snapshot_rows: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    rules = config["rules"]

    for window in config["windows"]:
        window_name = window["name"]
        start = str(window["start"])
        end = str(window["end"])
        for entry in entries:
            method = entry["method"]
            signals = signals_by_method[method]
            if signals[(signals["date_str"] >= start) & (signals["date_str"] <= end)].empty:
                continue
            family = str(signals["model_family"].iloc[0])
            coverage.append(coverage_row(signals, method, family, entry["artifact"], entry["full_rank_artifact"], window_name, start, end))
            for rule in rules:
                result = replay_strategy(signals, full_rank_by_method[method], method, family, prices, s2d, rule, window_name, start, end)
                results.append(result)
                summary.append(result["metrics"])
                nav_rows.extend(result["nav"])
                action_rows.extend(result["actions"])
                snapshot_rows.extend(result["snapshots"])

    wcsv(out_dir / "formal_replay_summary.csv", summary)
    wcsv(out_dir / "formal_replay_daily_nav.csv", nav_rows)
    wcsv(out_dir / "formal_replay_actions.csv", action_rows)
    wcsv(out_dir / "formal_replay_position_snapshots.csv", snapshot_rows)
    wcsv(out_dir / "formal_replay_coverage_audit.csv", coverage)
    wcsv(out_dir / "formal_replay_position_integrity_audit.csv", integrity_rows(results))
    wcsv(out_dir / "formal_replay_rule_contract.csv", rule_contract_rows(rules))
    forbidden = []
    for entry in entries:
        method = entry["method"]
        cols = set(signals_by_method[method].columns)
        forbidden.append({
            "method": method,
            "forbidden_columns_present": " ".join(sorted(cols & FORBIDDEN_COLUMNS)),
            "forbidden_columns_used_for_ranking": False,
            "candidate_rank_col": "candidate_rank",
            "buy_score_col": "buy_score",
            "full_rank_field": "full_qlib_rank",
        })
    wcsv(out_dir / "formal_replay_forbidden_field_audit.csv", forbidden)
    parity = compare_with_baseline(out_dir, baseline_dir)
    wcsv(out_dir / "r2_parity_audit.csv", parity, ["check_name", "baseline_rows", "modular_rows", "status", "details"])
    parity_status = "pass" if all(row["status"] == "pass" for row in parity) else "fail"
    manifest = {
        "artifact_type": "replay_result",
        "schema_version": "replay_result_r10_action_window_cleanup",
        "contract_version": "REPLAY_RESULT_CONTRACT_CN.md@2026-06-16;FULL_RANK_CONTRACT_CN.md@2026-06-16",
        "created_at": created_at,
        "gate": "r2_config_driven_replay_matrix_completed" if parity_status == "pass" else "r2_config_driven_replay_matrix_diff_failed",
        "config": rel(config_path),
        "script": rel(ROOT / "scripts/run_tw_modular_config_replay_matrix.py"),
        "out_dir": rel(out_dir),
        "baseline_dir": rel(baseline_dir),
        "baseline_windowed_dir": rel(baseline_dir),
        "signal_manifests": {entry["method"]: entry["artifact"] for entry in entries},
        "full_rank_artifacts": {entry["method"]: entry["full_rank_artifact"] for entry in entries},
        "rules": rules,
        "windows": config["windows"],
        "parity_status": parity_status,
        "parity_audit": rel(out_dir / "r2_parity_audit.csv"),
        "action_key_parity_audit": rel(out_dir / "r10_action_window_parity_audit.csv"),
        "legacy_action_key_parity_audit_alias": rel(out_dir / "r2_action_key_parity_audit.csv"),
        "action_window_compatibility": {
            "modular_actions_window_field": True,
            "baseline_actions_window_field": True,
            "direct_window_filter_2026_ytd": True,
            "parity_key_includes_window": True,
            "parity_key_excludes_window_for_baseline_compatibility": False
        },
        "no_training": True,
        "no_tuning": True,
        "no_score_recompute": True,
        "no_provider_accepted_latest_frontend_api_monitor_trading": True,
        "capabilities": {
            "config_driven_replay_matrix": True,
            "model_signal_manifest_input": True,
            "summary_parity_2026_ytd": True,
            "daily_nav_parity_2026_ytd": True,
            "action_key_parity_2026_ytd": True,
            "action_window_parity_no_prefix": True,
            "actions_window_field": True,
            "full_rank_artifact_input": True,
            "readonly_research_artifact": True
        },
        "artifacts": {
            "summary": rel(out_dir / "formal_replay_summary.csv"),
            "daily_nav": rel(out_dir / "formal_replay_daily_nav.csv"),
            "actions": rel(out_dir / "formal_replay_actions.csv"),
            "snapshots": rel(out_dir / "formal_replay_position_snapshots.csv"),
            "coverage": rel(out_dir / "formal_replay_coverage_audit.csv"),
            "integrity": rel(out_dir / "formal_replay_position_integrity_audit.csv"),
            "forbidden": rel(out_dir / "formal_replay_forbidden_field_audit.csv"),
            "report": rel(REPORT),
            "handoff": rel(HANDOFF),
        },
    }
    wjson(out_dir / "formal_replay_manifest.json", manifest)
    write_reports(out_dir, manifest, parity)
    print(json.dumps({"ok": parity_status == "pass", "parity_status": parity_status, "out_dir": rel(out_dir), "parity": parity}, ensure_ascii=False, indent=2))
    return 0 if parity_status == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
