#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
PRODUCT_REGISTRY = yaml.safe_load((ROOT / "configs/tw_product_artifact_registry.yaml").read_text(encoding="utf-8")) or {}
MODEL = str((PRODUCT_REGISTRY.get("models") or {}).get("treatment_display_model_id") or (PRODUCT_REGISTRY.get("models") or {}).get("treatment_model_id"))
RULE = str((PRODUCT_REGISTRY.get("strategies") or {}).get("default_strategy_rule"))
DEFAULT_STRATEGY_SNAPSHOT_LATEST = ROOT / str((PRODUCT_REGISTRY.get("artifacts") or {}).get("readonly_strategy_latest"))
DEFAULT_STRATEGY = ROOT / "configs/strategy_dependencies" / f"{RULE}.yaml"
DEFAULT_OUT_ROOT = ROOT / "data_tw/artifacts/paper_portfolio" / MODEL / RULE
SCHEMA = "phase_x.paper_decision_bundle.v1"
STATE_SCHEMA = "phase_x.paper_portfolio_state.v1"
INTENT_SCHEMA = "phase_x.paper_order_intent.v1"
PREVIEW_SCHEMA = "phase_x.paper_apply_preview.v1"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def resolve(path: str | Path, base: Path | None = None) -> Path:
    p = Path(str(path))
    if p.is_absolute():
        return p
    if base is not None and (base / p).exists():
        return base / p
    return ROOT / p


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha_payload(payload: Any) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def bare_symbol(value: Any) -> str:
    text = str(value or "").strip().upper()
    if ":" in text:
        text = text.split(":", 1)[1]
    if text.startswith("TW"):
        text = text[2:]
    if "." in text:
        text = text.split(".", 1)[0]
    return text


def tw_symbol(value: Any) -> str:
    symbol = bare_symbol(value)
    return f"TW{symbol}" if symbol else ""


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def load_signal_manifest_from_latest(latest_path: Path = DEFAULT_STRATEGY_SNAPSHOT_LATEST) -> Path:
    latest = load_json(latest_path)
    snapshot_path = resolve(latest.get("snapshot_manifest") or "")
    snapshot_manifest = load_json(snapshot_path)
    signal_ref = snapshot_manifest.get("source_signal_manifest") or snapshot_manifest.get("source_model_signal_artifact") or ""
    if not signal_ref:
        raise RuntimeError(f"readonly strategy snapshot has no source signal manifest: {snapshot_path}")
    return resolve(signal_ref)


def load_signals(signal_manifest_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest = load_json(signal_manifest_path)
    base = signal_manifest_path.parent
    files = manifest.get("files") or {}
    signal_path = resolve(files.get("signals", "signals.csv"), base)
    with signal_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows = [row for row in rows if tw_symbol(row.get("instrument"))]
    return manifest, rows


def load_strategy(path: Path = DEFAULT_STRATEGY) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if payload.get("strategy_rule") != RULE:
        raise RuntimeError(f"strategy rule mismatch: {path}")
    return payload


def latest_by_symbol(signals: list[dict[str, Any]], explicit_asof: str = "") -> tuple[str, list[dict[str, Any]]]:
    if not signals:
        return explicit_asof, []
    asof = explicit_asof or max(str(row.get("date") or "") for row in signals)
    return asof, [row for row in signals if str(row.get("date") or "") == asof]


def load_account_state_from_json(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    account = dict(payload.get("account") or {})
    positions = [dict(item) for item in payload.get("positions") or []]
    prices = dict(payload.get("prices") or {})
    return {
        "account": account,
        "positions": positions,
        "prices": normalize_prices(prices),
        "source": {"mode": "json_fixture", "path": rel(path)},
    }


def normalize_prices(prices: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for key, value in prices.items():
        symbol = bare_symbol(key)
        if not symbol:
            continue
        if isinstance(value, dict):
            out[symbol] = {
                "last_price": as_float(value.get("last_price") or value.get("latest_close") or value.get("close")),
                "price_date": value.get("price_date") or value.get("latest_date") or value.get("trade_date") or "",
                "price_source": value.get("price_source") or value.get("source") or "fixture",
            }
        else:
            out[symbol] = {"last_price": as_float(value), "price_date": "", "price_source": "fixture"}
    return out


def load_account_state_from_db(*, account_uid: str, user_id: int) -> dict[str, Any]:
    backend = ROOT / "backend"
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))
    from app.utils.db import get_db_connection

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT account_uid, user_id, name, currency, initial_cash, cash, created_at, updated_at
            FROM qd_tw_sim_accounts
            WHERE account_uid = %s AND user_id = %s AND simulation_only = TRUE
            """,
            (account_uid, int(user_id)),
        )
        account = dict(cur.fetchone() or {})
        if not account:
            raise RuntimeError(f"simulation account not found: {account_uid}")
        cur.execute(
            """
            SELECT symbol, quantity, avg_cost, cost_value, created_at, updated_at
            FROM qd_tw_sim_positions
            WHERE account_uid = %s AND quantity > 0 AND simulation_only = TRUE
            ORDER BY symbol ASC
            """,
            (account_uid,),
        )
        positions = [dict(row) for row in (cur.fetchall() or [])]
        symbols = [bare_symbol(row.get("symbol")) for row in positions if bare_symbol(row.get("symbol"))]
        prices: dict[str, dict[str, Any]] = {}
        for symbol in symbols:
            cur.execute(
                """
                SELECT symbol, trade_date::text AS trade_date, close, source
                FROM qd_tw_stock_daily_bars
                WHERE symbol = %s AND close > 0 AND (quality_flags IS NULL OR quality_flags = '')
                ORDER BY trade_date DESC
                LIMIT 1
                """,
                (symbol,),
            )
            row = dict(cur.fetchone() or {})
            if row:
                prices[symbol] = {
                    "last_price": as_float(row.get("close")),
                    "price_date": row.get("trade_date") or "",
                    "price_source": row.get("source") or "qd_tw_stock_daily_bars",
                }
        cur.close()
    return {
        "account": account,
        "positions": positions,
        "prices": prices,
        "source": {
            "mode": "db_readonly",
            "account_table": "qd_tw_sim_accounts",
            "position_table": "qd_tw_sim_positions",
            "price_table": "qd_tw_stock_daily_bars",
        },
    }


def fill_missing_prices_from_db(prices: dict[str, dict[str, Any]], symbols: list[str]) -> dict[str, dict[str, Any]]:
    missing = [bare_symbol(symbol) for symbol in symbols if bare_symbol(symbol) and bare_symbol(symbol) not in prices]
    if not missing:
        return prices
    backend = ROOT / "backend"
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))
    from app.utils.db import get_db_connection

    with get_db_connection() as conn:
        cur = conn.cursor()
        for symbol in missing:
            cur.execute(
                """
                SELECT symbol, trade_date::text AS trade_date, close, source
                FROM qd_tw_stock_daily_bars
                WHERE symbol = %s AND close > 0 AND (quality_flags IS NULL OR quality_flags = '')
                ORDER BY trade_date DESC
                LIMIT 1
                """,
                (symbol,),
            )
            row = dict(cur.fetchone() or {})
            if row:
                prices[symbol] = {
                    "last_price": as_float(row.get("close")),
                    "price_date": row.get("trade_date") or "",
                    "price_source": row.get("source") or "qd_tw_stock_daily_bars",
                }
        cur.close()
    return prices


def build_portfolio_state(account_state: dict[str, Any], *, asof: str) -> dict[str, Any]:
    account = account_state["account"]
    prices = account_state.get("prices") or {}
    positions = []
    market_value_total = 0.0
    cost_value_total = 0.0
    for row in account_state.get("positions") or []:
        symbol = bare_symbol(row.get("symbol") or row.get("instrument"))
        qty = as_int(row.get("quantity"))
        if not symbol or qty <= 0:
            continue
        price = prices.get(symbol) or {}
        avg_cost = as_float(row.get("avg_cost") or row.get("avg_price"))
        cost_value = as_float(row.get("cost_value"), avg_cost * qty)
        last_price = as_float(price.get("last_price") or row.get("latest_close") or row.get("last_price"))
        market_value = last_price * qty if last_price > 0 else 0.0
        market_value_total += market_value
        cost_value_total += cost_value
        positions.append({
            "instrument": tw_symbol(symbol),
            "symbol": symbol,
            "quantity": qty,
            "avg_cost": avg_cost,
            "cost_value": round(cost_value, 2),
            "last_price": last_price,
            "price_date": price.get("price_date") or row.get("latest_date") or "",
            "market_value": round(market_value, 2),
            "unrealized_paper_pnl": round(market_value - cost_value, 2),
            "source": "qd_tw_sim_positions + qd_tw_stock_daily_bars" if account_state["source"]["mode"] == "db_readonly" else "json_fixture",
        })
    cash = as_float(account.get("cash"))
    initial_cash = as_float(account.get("initial_cash"), cash)
    state = {
        "artifact_type": "PaperPortfolioStateArtifact",
        "schema_version": STATE_SCHEMA,
        "paper_account_id": account.get("account_uid") or account.get("paper_account_id") or "paper_fixture_account",
        "user_id": as_int(account.get("user_id")),
        "paper_account_epoch": as_int(account.get("paper_account_epoch"), 1),
        "asof": asof,
        "market_scope": "TWStock",
        "base_currency": account.get("currency") or "TWD",
        "cash": round(cash, 2),
        "initial_cash": round(initial_cash, 2),
        "market_value": round(market_value_total, 2),
        "total_equity": round(cash + market_value_total, 2),
        "open_cost_value": round(cost_value_total, 2),
        "positions": positions,
        "source": account_state["source"],
        "readonly_state_only": True,
        "not_real_order": True,
        "created_at": now_iso(),
    }
    state["checksum"] = sha_payload({k: v for k, v in state.items() if k != "checksum"})
    return state


def build_day_state(signals: list[dict[str, Any]], candidate_k: int) -> dict[str, Any]:
    rows = []
    for row in signals:
        item = dict(row)
        item["instrument"] = tw_symbol(row.get("instrument"))
        item["symbol"] = bare_symbol(row.get("instrument"))
        item["_candidate_rank"] = as_float(row.get("candidate_rank"), 999999.0)
        item["_buy_score"] = as_float(row.get("buy_score"), -999999.0)
        item["_full_rank"] = as_float(row.get("full_qlib_rank"), 999999.0)
        rows.append(item)
    candidates = [row for row in rows if row["_candidate_rank"] <= candidate_k]
    buy_order = sorted(candidates, key=lambda row: (-row["_buy_score"], row["instrument"]))
    return {
        "candidate_set": {row["instrument"] for row in candidates},
        "buy_order": buy_order,
        "by_instrument": {row["instrument"]: row for row in rows},
    }


def decide_actions(
    *,
    portfolio_state: dict[str, Any],
    day_state: dict[str, Any],
    strategy: dict[str, Any],
    prices: dict[str, dict[str, Any]],
    lot_size: int,
    target_holding_count: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    max_buy = int(strategy.get("max_buy_count") or 1)
    max_sell = int(strategy.get("max_sell_count") or 1)
    positions = portfolio_state.get("positions") or []
    held = [row["instrument"] for row in positions if as_int(row.get("quantity")) > 0]
    held_set = set(held)
    pos_by_inst = {row["instrument"]: row for row in positions}
    by_inst = day_state["by_instrument"]
    outside = [instrument for instrument in held if instrument not in day_state["candidate_set"]]
    outside = sorted(
        outside,
        key=lambda instrument: (as_float((by_inst.get(instrument) or {}).get("full_qlib_rank"), 999999.0), instrument),
        reverse=True,
    )
    sell_candidates = outside[:max_sell]

    actions: list[dict[str, Any]] = []
    preview_rows: list[dict[str, Any]] = []
    cash_cursor = as_float(portfolio_state.get("cash"))
    applicable_sells: set[str] = set()

    for instrument in sell_candidates:
        pos = pos_by_inst[instrument]
        symbol = bare_symbol(instrument)
        qty = as_int(pos.get("quantity"))
        price_info = prices.get(symbol) or {}
        price = as_float(price_info.get("last_price") or pos.get("last_price"))
        gross = round(qty * price, 2) if price > 0 else 0.0
        fee = round(gross * 0.001425, 2)
        tax = round(gross * 0.003, 2)
        cash_effect = round(gross - fee - tax, 2) if price > 0 else 0.0
        applicability = "applicable" if price > 0 and qty > 0 else "unavailable"
        reason = f"{RULE}_sell_outside_top50_worst_rank"
        actions.append({
            "action_type": "paper_sell_intent",
            "instrument": instrument,
            "symbol": symbol,
            "quantity": qty,
            "reason": reason,
            "candidate_rank": (by_inst.get(instrument) or {}).get("candidate_rank", ""),
            "full_qlib_rank": (by_inst.get(instrument) or {}).get("full_qlib_rank", ""),
            "estimated_reference_price": price,
            "price_date": price_info.get("price_date") or pos.get("price_date") or "",
            "estimated_fee": fee,
            "estimated_tax": tax,
            "cash_effect_preview": cash_effect,
            "applicability": applicability,
        })
        if applicability == "applicable":
            cash_cursor += cash_effect
            applicable_sells.add(instrument)
        preview_rows.append({"instrument": instrument, "action_type": "paper_sell_intent", "cash_after_preview": round(cash_cursor, 2), "applicability": applicability})

    remaining = held_set - applicable_sells
    open_slots = max(0, target_holding_count - len(remaining))
    buy_limit = min(max_buy, open_slots)
    buys = []
    for row in day_state["buy_order"]:
        instrument = row["instrument"]
        if len(buys) >= buy_limit:
            break
        if instrument in remaining:
            continue
        buys.append(instrument)

    for instrument in buys:
        row = by_inst[instrument]
        symbol = bare_symbol(instrument)
        price_info = prices.get(symbol) or {}
        price = as_float(price_info.get("last_price"))
        qty = lot_size if price > 0 else 0
        gross = round(qty * price, 2) if qty else 0.0
        fee = round(gross * 0.001425, 2)
        tax = 0.0
        cash_required = round(gross + fee, 2)
        if price <= 0:
            applicability = "unavailable"
            reason = "missing_reference_price"
        elif cash_cursor < cash_required:
            applicability = "unavailable"
            reason = "cash_insufficient_for_one_lot_preview"
        else:
            applicability = "applicable"
            reason = f"{RULE}_buy_best_available_candidate"
            cash_cursor -= cash_required
        actions.append({
            "action_type": "paper_buy_intent",
            "instrument": instrument,
            "symbol": symbol,
            "quantity": qty,
            "reason": reason,
            "candidate_rank": row.get("candidate_rank", ""),
            "buy_rank": row.get("score_rank", ""),
            "buy_score": row.get("buy_score", ""),
            "full_qlib_rank": row.get("full_qlib_rank", ""),
            "estimated_reference_price": price,
            "price_date": price_info.get("price_date") or "",
            "estimated_fee": fee,
            "estimated_tax": tax,
            "cash_effect_preview": -cash_required if cash_required else 0.0,
            "applicability": applicability,
        })
        preview_rows.append({"instrument": instrument, "action_type": "paper_buy_intent", "cash_after_preview": round(cash_cursor, 2), "applicability": applicability})

    for instrument in sorted(remaining):
        actions.append({
            "action_type": "paper_skip",
            "instrument": instrument,
            "symbol": bare_symbol(instrument),
            "quantity": 0,
            "reason": "current_paper_holding_kept_by_strategy",
            "applicability": "not_applicable",
        })

    return actions, preview_rows


def build_artifact(
    *,
    account_state: dict[str, Any],
    signal_manifest_path: Path,
    strategy_path: Path,
    out_root: Path,
    run_id: str,
    signal_asof: str = "",
    lot_size: int = 10,
    target_holding_count: int = 10,
) -> dict[str, Any]:
    signal_manifest, signals = load_signals(signal_manifest_path)
    asof, day_signals = latest_by_symbol(signals, signal_asof or str(signal_manifest.get("asof_date") or ""))
    strategy = load_strategy(strategy_path)
    candidate_k = int(signal_manifest.get("candidate_k") or 50)
    day_state = build_day_state(day_signals, candidate_k)
    candidate_symbols = [bare_symbol(row["instrument"]) for row in day_state["buy_order"][: max(5, target_holding_count + 5)]]
    if account_state["source"]["mode"] == "db_readonly":
        account_state["prices"] = fill_missing_prices_from_db(account_state.get("prices") or {}, candidate_symbols)
    portfolio_state = build_portfolio_state(account_state, asof=asof)
    prices = account_state.get("prices") or {}
    actions, preview_rows = decide_actions(
        portfolio_state=portfolio_state,
        day_state=day_state,
        strategy=strategy,
        prices=prices,
        lot_size=lot_size,
        target_holding_count=target_holding_count,
    )
    input_payload = {
        "portfolio_state_checksum": portfolio_state["checksum"],
        "source_model_signal_artifact": rel(signal_manifest_path),
        "strategy_rule": RULE,
        "asof": asof,
        "actions": actions,
    }
    input_checksum = sha_payload(input_payload)
    decision_id = "paper_decision_" + input_checksum.split(":", 1)[1][:16]
    order_intent = {
        "artifact_type": "PaperOrderIntentArtifact",
        "schema_version": INTENT_SCHEMA,
        "decision_id": decision_id,
        "model_id": MODEL,
        "strategy_rule": RULE,
        "paper_account_id": portfolio_state["paper_account_id"],
        "user_id": portfolio_state["user_id"],
        "paper_account_epoch": portfolio_state["paper_account_epoch"],
        "asof": asof,
        "source_portfolio_state_artifact": "paper_portfolio_state.json",
        "source_model_signal_artifact": rel(signal_manifest_path),
        "input_checksum": input_checksum,
        "readonly_decision_only": True,
        "not_real_order": True,
        "not_target_position": True,
        "not_investment_advice": True,
        "actions": actions,
        "reason": "generated from current paper holdings and readonly model signal",
        "created_at": now_iso(),
    }
    apply_preview = {
        "artifact_type": "PaperApplyPreviewArtifact",
        "schema_version": PREVIEW_SCHEMA,
        "decision_id": decision_id,
        "paper_account_id": portfolio_state["paper_account_id"],
        "paper_account_epoch": portfolio_state["paper_account_epoch"],
        "asof": asof,
        "cash_before": portfolio_state["cash"],
        "cash_after_preview": preview_rows[-1]["cash_after_preview"] if preview_rows else portfolio_state["cash"],
        "preview_rows": preview_rows,
        "readonly_preview_only": True,
        "not_applied": True,
        "not_real_order": True,
        "created_at": now_iso(),
    }
    forbidden = {
        "artifact_type": "paper_decision_forbidden_action_audit",
        "schema_version": SCHEMA,
        "status": "pass",
        "actions": {
            "sim_account_write": False,
            "paper_order_write": False,
            "paper_execution_write": False,
            "reset": False,
            "broker_order": False,
            "quick_trade": False,
            "real_order": False,
            "provider_publish": False,
            "provider_accepted_latest_switch": False,
            "qlib_accepted_latest_switch": False,
            "monitor_write": False,
            "monitor_scan": False,
            "agent_tool_action_expansion": False,
            "training": False,
            "tuning": False,
        },
    }
    run_id = run_id or f"x1_paper_decision_{asof.replace('-', '')}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    out_dir = out_root / run_id
    write_json(out_dir / "paper_portfolio_state.json", portfolio_state)
    write_json(out_dir / "paper_order_intent.json", order_intent)
    write_json(out_dir / "paper_apply_preview.json", apply_preview)
    write_json(out_dir / "forbidden_action_audit.json", forbidden)
    write_json(out_dir / "schema.json", {
        "schema_version": SCHEMA,
        "artifacts": [STATE_SCHEMA, INTENT_SCHEMA, PREVIEW_SCHEMA],
        "readonly_only": True,
        "forbidden_fields": ["broker", "quick_trade", "target_position", "target_weight", "real_order"],
    })
    manifest = {
        "artifact_type": "PaperDecisionBundleArtifact",
        "schema_version": SCHEMA,
        "run_id": run_id,
        "created_at": now_iso(),
        "created_by": rel(Path(__file__)),
        "model_id": MODEL,
        "strategy_rule": RULE,
        "paper_account_id": portfolio_state["paper_account_id"],
        "user_id": portfolio_state["user_id"],
        "paper_account_epoch": portfolio_state["paper_account_epoch"],
        "asof": asof,
        "readonly_only": True,
        "not_applied": True,
        "not_real_order": True,
        "not_target_position": True,
        "not_investment_advice": True,
        "no_broker_order": True,
        "no_quick_trade": True,
        "source_model_signal_artifact": rel(signal_manifest_path),
        "source_strategy_config": rel(strategy_path),
        "input_checksum": input_checksum,
        "decision_id": decision_id,
        "action_counts": {
            "paper_buy_intent": sum(1 for action in actions if action["action_type"] == "paper_buy_intent"),
            "paper_sell_intent": sum(1 for action in actions if action["action_type"] == "paper_sell_intent"),
            "paper_skip": sum(1 for action in actions if action["action_type"] == "paper_skip"),
        },
        "files": {
            "paper_portfolio_state": "paper_portfolio_state.json",
            "paper_order_intent": "paper_order_intent.json",
            "paper_apply_preview": "paper_apply_preview.json",
            "forbidden_action_audit": "forbidden_action_audit.json",
            "schema": "schema.json",
        },
    }
    manifest["checksum"] = sha_payload({k: v for k, v in manifest.items() if k != "checksum"})
    write_json(out_dir / "manifest.json", manifest)
    return {"ok": True, "manifest": rel(out_dir / "manifest.json"), "artifact": rel(out_dir), "decision_id": decision_id, "action_counts": manifest["action_counts"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build readonly Phase X1 paper portfolio decision artifacts.")
    parser.add_argument("--paper-account-json", default="")
    parser.add_argument("--account-uid", default="")
    parser.add_argument("--user-id", type=int, default=0)
    parser.add_argument("--model-signal", default="")
    parser.add_argument("--strategy-config", default=str(DEFAULT_STRATEGY))
    parser.add_argument("--signal-asof", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT))
    parser.add_argument("--lot-size", type=int, default=10)
    parser.add_argument("--target-holding-count", type=int, default=10)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.paper_account_json:
        account_state = load_account_state_from_json(resolve(args.paper_account_json))
    else:
        if not args.account_uid or not args.user_id:
            raise SystemExit("--account-uid and --user-id are required unless --paper-account-json is provided")
        account_state = load_account_state_from_db(account_uid=args.account_uid, user_id=args.user_id)
    signal_manifest_path = resolve(args.model_signal) if args.model_signal else load_signal_manifest_from_latest()
    result = build_artifact(
        account_state=account_state,
        signal_manifest_path=signal_manifest_path,
        strategy_path=resolve(args.strategy_config),
        out_root=resolve(args.out_root),
        run_id=args.run_id,
        signal_asof=args.signal_asof,
        lot_size=args.lot_size,
        target_holding_count=args.target_holding_count,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["manifest"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
