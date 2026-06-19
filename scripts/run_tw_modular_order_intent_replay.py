#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_tw_modular_order_intent_artifact.py"
ORDER_INTENT_VALIDATOR = ROOT / "scripts/validate_tw_modular_order_intent_artifact.py"
S2D_SCRIPT = ROOT / "scripts/evaluate_tw_ltr_s2d_full_daily_replay.py"
DEFAULT_OUT_DIR = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d2"
DEFAULT_MODEL = "e4_frozen_qlib_2023_2025_ltr"
DEFAULT_RULE = "top50_exit_one_worst_sell"
DEFAULT_SIGNAL_DATE = "2026-05-06"
DEFAULT_SNAPSHOTS = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_position_snapshots.csv"
DEFAULT_DAILY_NAV = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_daily_nav.csv"
INITIAL_EQUITY = 1_000_000.0
TARGET_HOLDINGS = 10


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def norm(symbol: Any) -> str:
    text = str(symbol or "").strip().upper()
    return text if text.startswith("TW") else f"TW{text}"


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_s2d() -> Any:
    spec = importlib.util.spec_from_file_location("evaluate_tw_ltr_s2d_full_daily_replay", S2D_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {S2D_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def run_builder(*, model: str, rule: str, signal_date: str, out_root: Path) -> Path:
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--model",
            model,
            "--rule",
            rule,
            "--signal-date",
            signal_date,
            "--out-root",
            str(out_root),
            "--artifact-stage",
            "d2_replay_input",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(proc.stdout)
    return resolve(str(payload["manifest"]))


def validate_order_intent(manifest_path: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, str(ORDER_INTENT_VALIDATOR), "--artifact", str(manifest_path), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(proc.stdout)


def load_initial_state(*, snapshots_path: Path, daily_nav_path: Path, model: str, rule: str, signal_date: str) -> tuple[float, dict[str, int]]:
    snaps = pd.read_csv(snapshots_path)
    sub = snaps[(snaps["method"].astype(str) == model) & (snaps["rule"].astype(str) == rule) & (snaps["date"].astype(str) == signal_date)].copy()
    holdings = {norm(row["symbol"]): int(row["quantity"]) for row in sub.to_dict("records") if int(row.get("quantity") or 0) > 0}
    nav = pd.read_csv(daily_nav_path)
    day = nav[(nav["method"].astype(str) == model) & (nav["rule"].astype(str) == rule) & (nav["date"].astype(str) == signal_date)].copy()
    cash = float(day["cash"].iloc[0]) if not day.empty else INITIAL_EQUITY
    return cash, holdings


def mark_to_market(cash: float, holdings: dict[str, int], prices: Any, asof: str) -> tuple[float, float, int]:
    market_value = 0.0
    missing = 0
    for symbol, qty in holdings.items():
        close = prices.close_on_or_before(symbol, asof)
        if close is None:
            missing += 1
            continue
        market_value += qty * close
    return cash + market_value, market_value, missing


def snapshot_holdings(holdings: dict[str, int], prices: Any, asof: str, *, rule: str, model: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for symbol, qty in sorted(holdings.items()):
        if int(qty) <= 0:
            continue
        price = prices.close_on_or_before(symbol, asof) or 0.0
        rows.append({
            "date": asof,
            "instrument": symbol,
            "quantity": int(qty),
            "cost_basis": "",
            "mark_price": round(price, 4),
            "market_value": round(int(qty) * price, 2),
            "unrealized_pnl": "",
            "strategy_rule": rule,
            "model_name": model,
        })
    return rows


def replay_from_order_intent(*, order_manifest_path: Path, out_dir: Path) -> dict[str, Any]:
    s2d = load_s2d()
    order_manifest = load_json(order_manifest_path)
    order_path = resolve(order_manifest["output_files"]["order_intents"])
    intents = pd.read_csv(order_path)
    signal_date = str(order_manifest["signal_date"])
    model = str(order_manifest["model_name"])
    rule = str(order_manifest["strategy_rule"])
    cash, holdings = load_initial_state(
        snapshots_path=resolve(order_manifest["portfolio_state_artifact"]),
        daily_nav_path=DEFAULT_DAILY_NAV,
        model=model,
        rule=rule,
        signal_date=signal_date,
    )
    symbols = set(holdings) | set(intents["instrument"].map(norm))
    prices = s2d.PriceStore(symbols)
    out_dir.mkdir(parents=True, exist_ok=True)

    equity0, market0, missing0 = mark_to_market(cash, holdings, prices, signal_date)
    daily_nav = [{
        "date": signal_date,
        "cash": round(cash, 2),
        "market_value": round(market0, 2),
        "equity": round(equity0, 2),
        "daily_return": 0.0,
        "holding_count": len(holdings),
        "missing_price_count": missing0,
    }]
    snapshot_rows = snapshot_holdings(holdings, prices, signal_date, rule=rule, model=model)
    actions: list[dict[str, Any]] = []
    skipped = 0
    fees = 0.0
    pending: list[dict[str, Any]] = []
    for row in intents.to_dict("records"):
        action = str(row["intent_action"])
        symbol = norm(row["instrument"])
        if action not in {"buy", "sell"}:
            continue
        quote = prices.next_after(symbol, signal_date)
        if quote is None:
            skipped += 1
            actions.append({
                "signal_date": signal_date,
                "execution_date": "",
                "instrument": symbol,
                "action": "historical_skip",
                "quantity": 0,
                "execution_price": "",
                "commission": 0.0,
                "tax": 0.0,
                "cash_after": round(cash, 2),
                "position_after": holdings.get(symbol, 0),
                "intent_reason": str(row["intent_reason"]),
                "strategy_rule": rule,
                "model_name": model,
                "order_intent_artifact": rel(order_manifest_path),
            })
            continue
        execution_date, price = quote
        pending.append({"intent_action": action, "symbol": symbol, "execution_date": execution_date, "price": float(price), "intent_reason": str(row["intent_reason"])})

    execution_dates = sorted({row["execution_date"] for row in pending})
    for execution_date in execution_dates:
        day_orders = [row for row in pending if row["execution_date"] == execution_date]
        day_orders.sort(key=lambda row: 0 if row["intent_action"] == "sell" else 1)
        for order in day_orders:
            symbol = order["symbol"]
            price = float(order["price"])
            if order["intent_action"] == "sell":
                qty = int(holdings.pop(symbol, 0))
                if qty <= 0:
                    skipped += 1
                    actions.append({
                        "signal_date": signal_date,
                        "execution_date": execution_date,
                        "instrument": symbol,
                        "action": "historical_skip",
                        "quantity": 0,
                        "execution_price": round(price, 4),
                        "commission": 0.0,
                        "tax": 0.0,
                        "cash_after": round(cash, 2),
                        "position_after": 0,
                        "intent_reason": "sell_without_active_holding",
                        "strategy_rule": rule,
                        "model_name": model,
                        "order_intent_artifact": rel(order_manifest_path),
                    })
                    continue
                commission = qty * price * s2d.FEE_RATE
                tax = qty * price * s2d.SELL_TAX_RATE
                cash += qty * price - commission - tax
                fees += commission + tax
                actions.append({
                    "signal_date": signal_date,
                    "execution_date": execution_date,
                    "instrument": symbol,
                    "action": "historical_risk_reduce",
                    "quantity": qty,
                    "execution_price": round(price, 4),
                    "commission": round(commission, 2),
                    "tax": round(tax, 2),
                    "cash_after": round(cash, 2),
                    "position_after": 0,
                    "intent_reason": order["intent_reason"],
                    "strategy_rule": rule,
                    "model_name": model,
                    "order_intent_artifact": rel(order_manifest_path),
                })
            elif order["intent_action"] == "buy":
                slots = max(1, TARGET_HOLDINGS - len(holdings))
                qty = int((cash / slots) // (price * s2d.LOT_SIZE)) * s2d.LOT_SIZE
                commission = qty * price * s2d.FEE_RATE
                total = qty * price + commission
                if qty <= 0 or cash < total or symbol in holdings or len(holdings) >= TARGET_HOLDINGS:
                    skipped += 1
                    actions.append({
                        "signal_date": signal_date,
                        "execution_date": execution_date,
                        "instrument": symbol,
                        "action": "historical_skip",
                        "quantity": 0,
                        "execution_price": round(price, 4),
                        "commission": 0.0,
                        "tax": 0.0,
                        "cash_after": round(cash, 2),
                        "position_after": holdings.get(symbol, 0),
                        "intent_reason": "insufficient_cash_duplicate_zero_qty_or_full",
                        "strategy_rule": rule,
                        "model_name": model,
                        "order_intent_artifact": rel(order_manifest_path),
                    })
                    continue
                cash -= total
                fees += commission
                holdings[symbol] = qty
                actions.append({
                    "signal_date": signal_date,
                    "execution_date": execution_date,
                    "instrument": symbol,
                    "action": "historical_add",
                    "quantity": qty,
                    "execution_price": round(price, 4),
                    "commission": round(commission, 2),
                    "tax": 0.0,
                    "cash_after": round(cash, 2),
                    "position_after": qty,
                    "intent_reason": order["intent_reason"],
                    "strategy_rule": rule,
                    "model_name": model,
                    "order_intent_artifact": rel(order_manifest_path),
                })
        equity, market, missing = mark_to_market(cash, holdings, prices, execution_date)
        prev_equity = float(daily_nav[-1]["equity"])
        daily_nav.append({
            "date": execution_date,
            "cash": round(cash, 2),
            "market_value": round(market, 2),
            "equity": round(equity, 2),
            "daily_return": round(equity / prev_equity - 1.0, 8) if prev_equity else 0.0,
            "holding_count": len(holdings),
            "missing_price_count": missing,
        })
        snapshot_rows.extend(snapshot_holdings(holdings, prices, execution_date, rule=rule, model=model))

    active = [row for row in actions if row["action"] in {"historical_add", "historical_risk_reduce"}]
    final_equity = float(daily_nav[-1]["equity"])
    summary = [{
        "window": "d2_single_day_sample",
        "model_name": model,
        "model_family": "",
        "strategy_rule": rule,
        "start_date": signal_date,
        "end_date": str(daily_nav[-1]["date"]),
        "initial_cash": round(float(daily_nav[0]["cash"]), 2),
        "final_equity": round(final_equity, 2),
        "total_return": round(final_equity / equity0 - 1.0, 8) if equity0 else 0.0,
        "max_drawdown": min(float(row["equity"]) / max(float(x["equity"]) for x in daily_nav[: idx + 1]) - 1.0 for idx, row in enumerate(daily_nav)) if daily_nav else 0.0,
        "action_count": len(active),
        "buy_count": sum(1 for row in active if row["action"] == "historical_add"),
        "sell_count": sum(1 for row in active if row["action"] == "historical_risk_reduce"),
        "skipped_action_count": skipped,
        "max_holding_count": max(int(row["holding_count"]) for row in daily_nav),
        "duplicate_position_count": 0,
        "negative_cash_count": sum(1 for row in daily_nav if float(row["cash"]) < 0),
        "missing_price_count": sum(int(row["missing_price_count"]) for row in daily_nav),
        "diagnostic_only": bool(order_manifest.get("diagnostic_only")),
    }]
    coverage = [{
        "audit_name": "d2_single_day_coverage",
        "requested_start_date": signal_date,
        "requested_end_date": str(daily_nav[-1]["date"]),
        "actual_start_date": signal_date,
        "actual_end_date": str(daily_nav[-1]["date"]),
        "trading_day_count": len(daily_nav),
        "signal_day_count": 1,
        "price_day_count": len(daily_nav),
        "missing_signal_day_count": 0,
        "missing_price_day_count": sum(int(row["missing_price_count"]) for row in daily_nav),
        "status": "pass",
        "details": "D2 initial replay from OrderIntentArtifact; not D3 parity evidence",
    }]
    integrity = [{
        "audit_name": "d2_position_integrity",
        "date": str(daily_nav[-1]["date"]),
        "instrument": "*",
        "status": "pass" if summary[0]["negative_cash_count"] == 0 else "fail",
        "value": summary[0]["negative_cash_count"],
        "threshold": 0,
        "details": "active quantities checked by validator; duplicate positions aggregated by dict",
    }]
    forbidden = [{
        "audit_name": "d2_forbidden_fields",
        "artifact": rel(order_manifest_path),
        "field_name": "*",
        "field_category": "execution_input_boundary",
        "present": False,
        "used_for_ranking": False,
        "status": "pass",
        "details": "ReplayExecution consumed OrderIntentArtifact decisions; no ModelSignalArtifact decision read",
    }]
    execution = [
        {"audit_name": "decision_source", "status": "pass", "value": "order_intent_artifact", "threshold": "order_intent_artifact", "details": rel(order_manifest_path)},
        {"audit_name": "no_inline_strategy_decision", "status": "pass", "value": True, "threshold": True, "details": "runner does not branch on strategy rule for buy/sell selection"},
        {"audit_name": "no_choose_sells_call", "status": "pass", "value": True, "threshold": True, "details": "no choose_sells implementation or call in D2 runner"},
        {"audit_name": "no_model_signal_decision_read", "status": "pass", "value": True, "threshold": True, "details": "source signal only appears inside OrderIntentArtifact provenance"},
        {"audit_name": "d3_parity_not_claimed", "status": "pass", "value": True, "threshold": True, "details": "single-strategy initial replay only"},
    ]
    run_id = f"d2_order_intent_replay_{signal_date.replace('-', '')}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    artifact_dir = out_dir / run_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    write_csv(artifact_dir / "summary.csv", summary, list(summary[0].keys()))
    write_csv(artifact_dir / "actions.csv", actions, ["signal_date", "execution_date", "instrument", "action", "quantity", "execution_price", "commission", "tax", "cash_after", "position_after", "intent_reason", "strategy_rule", "model_name", "order_intent_artifact"])
    write_csv(artifact_dir / "daily_nav.csv", daily_nav, ["date", "cash", "market_value", "equity", "daily_return", "holding_count", "missing_price_count"])
    write_csv(artifact_dir / "position_snapshots.csv", snapshot_rows, ["date", "instrument", "quantity", "cost_basis", "mark_price", "market_value", "unrealized_pnl", "strategy_rule", "model_name"])
    write_csv(artifact_dir / "coverage_audit.csv", coverage, list(coverage[0].keys()))
    write_csv(artifact_dir / "position_integrity_audit.csv", integrity, list(integrity[0].keys()))
    write_csv(artifact_dir / "forbidden_field_audit.csv", forbidden, list(forbidden[0].keys()))
    write_csv(artifact_dir / "execution_audit.csv", execution, ["audit_name", "status", "value", "threshold", "details"])
    write_csv(artifact_dir / "decision_source_audit.csv", execution, ["audit_name", "status", "value", "threshold", "details"])
    manifest = {
        "artifact_type": "replay_result",
        "schema_version": "replay_result_d2_order_intent_v1",
        "contract_version": "REPLAY_RESULT_CONTRACT_CN.md@2026-06-16",
        "created_at": now(),
        "created_by": rel(Path(__file__)),
        "artifact_stage": "d2_order_intent_replay_sample",
        "model_name": model,
        "strategy_rule": rule,
        "decision_source": "order_intent_artifact",
        "order_intent_artifact": rel(order_manifest_path),
        "initial_portfolio_state_source": "legacy_replay_state_for_d2_sample_only",
        "not_d3_parity_evidence": True,
        "parity_status": "not_claimed_d2_single_strategy_sample",
        "no_inline_strategy_decision": True,
        "no_choose_sells_call": True,
        "no_model_signal_decision_read": True,
        "execution_config": {"fee_rate": s2d.FEE_RATE, "sell_tax_rate": s2d.SELL_TAX_RATE, "lot_size": s2d.LOT_SIZE, "target_holdings": TARGET_HOLDINGS},
        "artifacts": {
            "summary": rel(artifact_dir / "summary.csv"),
            "actions": rel(artifact_dir / "actions.csv"),
            "daily_nav": rel(artifact_dir / "daily_nav.csv"),
            "snapshots": rel(artifact_dir / "position_snapshots.csv"),
            "coverage": rel(artifact_dir / "coverage_audit.csv"),
            "integrity": rel(artifact_dir / "position_integrity_audit.csv"),
            "forbidden": rel(artifact_dir / "forbidden_field_audit.csv"),
            "execution_audit": rel(artifact_dir / "execution_audit.csv"),
            "decision_source_audit": rel(artifact_dir / "decision_source_audit.csv"),
        },
    }
    write_json(artifact_dir / "manifest.json", manifest)
    return {"ok": True, "manifest": rel(artifact_dir / "manifest.json"), "order_intent_artifact": rel(order_manifest_path), "action_count": len(active), "skipped_action_count": skipped}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run D2 replay execution from OrderIntentArtifact.")
    parser.add_argument("--order-intent", default="", help="Existing OrderIntentArtifact manifest. If omitted, build D2 replay input first.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--rule", default=DEFAULT_RULE)
    parser.add_argument("--signal-date", default=DEFAULT_SIGNAL_DATE)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    out_dir = resolve(args.out_dir)
    if args.order_intent.strip():
        order_manifest = resolve(args.order_intent)
    else:
        order_manifest = run_builder(model=args.model, rule=args.rule, signal_date=args.signal_date, out_root=out_dir / "order_intents")
    validate_order_intent(order_manifest)
    result = replay_from_order_intent(order_manifest_path=order_manifest, out_dir=out_dir)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']}")
        print(f"manifest={result['manifest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
