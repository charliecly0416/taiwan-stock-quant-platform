#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ARTIFACTS = ["summary", "actions", "daily_nav", "snapshots", "coverage", "integrity", "forbidden", "execution_audit", "decision_source_audit"]
REQUIRED_ACTION_COLUMNS = ["signal_date", "execution_date", "instrument", "action", "quantity", "execution_price", "commission", "tax", "cash_after", "position_after", "intent_reason", "strategy_rule", "model_name", "order_intent_artifact"]
REQUIRED_SNAPSHOT_COLUMNS = ["date", "instrument", "quantity", "cost_basis", "mark_price", "market_value", "unrealized_pnl", "strategy_rule", "model_name"]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def check(name: str, ok: bool, details: str = "") -> dict[str, Any]:
    return {"name": name, "status": "pass" if ok else "fail", "details": details}


def csv_has_no_fail(path: Path) -> bool:
    frame = pd.read_csv(path)
    if "status" not in frame.columns:
        return True
    return not frame["status"].astype(str).str.lower().eq("fail").any()


def norm(symbol: Any) -> str:
    text = str(symbol or "").strip().upper()
    return text if text.startswith("TW") else f"TW{text}"


def to_int(value: Any, default: int = 0) -> int:
    converted = pd.to_numeric(pd.Series([value]), errors="coerce").fillna(default).iloc[0]
    return int(converted)


def snapshot_state(snapshots: pd.DataFrame, day: str) -> dict[str, int]:
    if snapshots.empty or not {"date", "instrument", "quantity"}.issubset(snapshots.columns):
        return {}
    sub = snapshots[snapshots["date"].astype(str) == day].copy()
    if sub.empty:
        return {}
    sub["quantity"] = pd.to_numeric(sub["quantity"], errors="coerce").fillna(0).astype(int)
    return {
        norm(row["instrument"]): int(row["quantity"])
        for row in sub.to_dict("records")
        if int(row.get("quantity") or 0) > 0
    }


def load_initial_holdings(order_manifest_path: Path, *, model: str, rule: str, signal_date: str) -> dict[str, int] | None:
    order_manifest = load_json(order_manifest_path)
    portfolio_artifact = order_manifest.get("portfolio_state_artifact")
    if not portfolio_artifact:
        return None
    path = resolve(str(portfolio_artifact))
    if not path.exists():
        return None
    frame = pd.read_csv(path)
    required = {"method", "rule", "date", "symbol", "quantity"}
    if not required.issubset(frame.columns):
        return None
    sub = frame[
        (frame["method"].astype(str) == model)
        & (frame["rule"].astype(str) == rule)
        & (frame["date"].astype(str) == signal_date)
    ].copy()
    sub["quantity"] = pd.to_numeric(sub["quantity"], errors="coerce").fillna(0).astype(int)
    return {
        norm(row["symbol"]): int(row["quantity"])
        for row in sub.to_dict("records")
        if int(row.get("quantity") or 0) > 0
    }


def validate_daily_snapshot_dates(daily_nav: pd.DataFrame, snapshots: pd.DataFrame) -> tuple[bool, str]:
    if not {"date", "holding_count"}.issubset(daily_nav.columns) or not {"date", "quantity"}.issubset(snapshots.columns):
        return False, "missing date/holding_count/quantity columns"
    nav_dates = {str(value) for value in daily_nav["date"].astype(str)}
    snapshot_dates = {str(value) for value in snapshots["date"].astype(str)}
    nav_positive_dates = set(
        daily_nav[pd.to_numeric(daily_nav["holding_count"], errors="coerce").fillna(0) > 0]["date"].astype(str)
    )
    positive_snapshot_dates = set(
        snapshots[pd.to_numeric(snapshots["quantity"], errors="coerce").fillna(0) > 0]["date"].astype(str)
    )
    zero_nav_dates = nav_dates - nav_positive_dates
    extra_zero_rows = snapshot_dates.intersection(zero_nav_dates)
    ok = positive_snapshot_dates == nav_positive_dates and not extra_zero_rows and snapshot_dates.issubset(nav_dates)
    details = f"nav_positive={sorted(nav_positive_dates)} snapshot_positive={sorted(positive_snapshot_dates)} extra={sorted(snapshot_dates - nav_dates)} zero_extra={sorted(extra_zero_rows)}"
    return bool(ok), details


def validate_daily_holding_counts(daily_nav: pd.DataFrame, snapshots: pd.DataFrame) -> tuple[bool, str]:
    if not {"date", "holding_count"}.issubset(daily_nav.columns) or not {"date", "quantity"}.issubset(snapshots.columns):
        return False, "missing date/holding_count/quantity columns"
    positive = snapshots[pd.to_numeric(snapshots["quantity"], errors="coerce").fillna(0) > 0].copy()
    snapshot_counts = positive.groupby(positive["date"].astype(str)).size().to_dict() if not positive.empty else {}
    mismatches = []
    for row in daily_nav.to_dict("records"):
        day = str(row["date"])
        expected = to_int(row["holding_count"], default=-1)
        actual = int(snapshot_counts.get(day, 0))
        if expected != actual:
            mismatches.append(f"{day}:{expected}!={actual}")
    return not mismatches, "|".join(mismatches)


def validate_artifact(manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    # WF-2A is not a D2/D3 parity artifact. Delegate to its authoritative
    # validator instead of reporting a false schema/lineage failure here.
    if manifest.get("schema_version") == "readonly_replay_result_wf2a_v1":
        try:
            from scripts.validate_tw_readonly_replay_window_artifact import validate_artifact as validate_wf2a
        except ModuleNotFoundError:
            from validate_tw_readonly_replay_window_artifact import validate_artifact as validate_wf2a

        return validate_wf2a(manifest_path)
    artifacts = manifest.get("artifacts") or {}
    missing = [key for key in REQUIRED_ARTIFACTS if not artifacts.get(key) or not resolve(str(artifacts.get(key))).exists()]
    checks = [
        check("artifact_type", manifest.get("artifact_type") == "replay_result", str(manifest.get("artifact_type"))),
        check("schema_version", str(manifest.get("schema_version")) == "replay_result_d2_order_intent_v1", str(manifest.get("schema_version"))),
        check("decision_source", manifest.get("decision_source") == "order_intent_artifact", str(manifest.get("decision_source"))),
        check("order_intent_artifact_exists", bool(manifest.get("order_intent_artifact")) and resolve(str(manifest.get("order_intent_artifact"))).exists(), str(manifest.get("order_intent_artifact"))),
        check("not_d3_parity_evidence", manifest.get("not_d3_parity_evidence") is True),
        check("parity_not_claimed", str(manifest.get("parity_status")) == "not_claimed_d2_single_strategy_sample", str(manifest.get("parity_status"))),
        check("no_inline_strategy_decision", manifest.get("no_inline_strategy_decision") is True),
        check("no_choose_sells_call", manifest.get("no_choose_sells_call") is True),
        check("no_model_signal_decision_read", manifest.get("no_model_signal_decision_read") is True),
        check("required_artifact_files", not missing, "|".join(missing)),
    ]
    if missing:
        return {"ok": False, "artifact": rel(manifest_path), "checks": checks}

    actions = pd.read_csv(resolve(str(artifacts["actions"])))
    daily_nav = pd.read_csv(resolve(str(artifacts["daily_nav"])))
    snapshots = pd.read_csv(resolve(str(artifacts["snapshots"])))
    missing_action_cols = sorted(set(REQUIRED_ACTION_COLUMNS) - set(actions.columns))
    missing_snapshot_cols = sorted(set(REQUIRED_SNAPSHOT_COLUMNS) - set(snapshots.columns))
    checks.append(check("actions_required_columns", not missing_action_cols, "|".join(missing_action_cols)))
    checks.append(check("snapshots_required_columns", not missing_snapshot_cols, "|".join(missing_snapshot_cols)))

    active = actions[actions["action"].isin(["historical_add", "historical_risk_reduce"])] if "action" in actions.columns else pd.DataFrame()
    if not active.empty:
        execution_ok = (pd.to_datetime(active["execution_date"], errors="coerce") > pd.to_datetime(active["signal_date"], errors="coerce")).all()
        qty_ok = (pd.to_numeric(active["quantity"], errors="coerce") > 0).all()
        source_ok = set(active["order_intent_artifact"].astype(str)) == {str(manifest.get("order_intent_artifact"))}
    else:
        execution_ok = True
        qty_ok = True
        source_ok = True
    checks.append(check("execution_date_after_signal", bool(execution_ok), "active actions only"))
    checks.append(check("active_quantity_positive", bool(qty_ok), "active actions only"))
    checks.append(check("actions_reference_order_intent", bool(source_ok), str(manifest.get("order_intent_artifact"))))

    dates_ok, dates_details = validate_daily_snapshot_dates(daily_nav, snapshots)
    counts_ok, counts_details = validate_daily_holding_counts(daily_nav, snapshots)
    checks.append(check("daily_nav_snapshot_dates_match", dates_ok, dates_details))
    checks.append(check("daily_nav_holding_count_matches_snapshots", counts_ok, counts_details))

    signal_date = str(manifest.get("signal_date") or (daily_nav["date"].astype(str).iloc[0] if "date" in daily_nav.columns and not daily_nav.empty else ""))
    initial_expected = None
    if manifest.get("order_intent_artifact"):
        initial_expected = load_initial_holdings(
            resolve(str(manifest.get("order_intent_artifact"))),
            model=str(manifest.get("model_name")),
            rule=str(manifest.get("strategy_rule")),
            signal_date=signal_date,
        )
    initial_actual = snapshot_state(snapshots, signal_date)
    checks.append(check(
        "initial_snapshot_matches_portfolio_state_or_manifest_initial_state",
        initial_expected is not None and initial_actual == initial_expected,
        f"expected={initial_expected} actual={initial_actual}",
    ))

    sell_failures: list[str] = []
    buy_failures: list[str] = []
    future_buy_failures: list[str] = []
    signal_state = snapshot_state(snapshots, signal_date)
    if not active.empty:
        for row in active.to_dict("records"):
            day = str(row["execution_date"])
            symbol = norm(row["instrument"])
            qty = to_int(row["quantity"])
            state = snapshot_state(snapshots, day)
            if row["action"] == "historical_risk_reduce" and state.get(symbol, 0) > 0:
                sell_failures.append(f"{day}:{symbol}")
            if row["action"] == "historical_add":
                if state.get(symbol, 0) != qty:
                    buy_failures.append(f"{day}:{symbol}:{qty}!={state.get(symbol, 0)}")
                if signal_state.get(symbol, 0) > 0:
                    future_buy_failures.append(f"{signal_date}:{symbol}")
    checks.append(check("sell_action_removed_from_execution_snapshot", not sell_failures, "|".join(sell_failures)))
    checks.append(check("buy_action_present_in_execution_snapshot_with_quantity", not buy_failures, "|".join(buy_failures)))
    checks.append(check("no_future_buy_in_signal_date_snapshot", not future_buy_failures, "|".join(future_buy_failures)))

    for key in ["coverage", "integrity", "forbidden", "execution_audit", "decision_source_audit"]:
        checks.append(check(f"{key}_status", csv_has_no_fail(resolve(str(artifacts[key]))), str(artifacts[key])))
    decision = pd.read_csv(resolve(str(artifacts["decision_source_audit"])))
    decision_rows = {str(row["audit_name"]): row for row in decision.to_dict("records")}
    checks.append(check("decision_source_audit_order_intent", str(decision_rows.get("decision_source", {}).get("value")) == "order_intent_artifact"))
    checks.append(check("decision_source_audit_no_choose_sells", str(decision_rows.get("no_choose_sells_call", {}).get("value")).lower() == "true"))
    checks.append(check("decision_source_audit_no_model_signal_decision_read", str(decision_rows.get("no_model_signal_decision_read", {}).get("value")).lower() == "true"))
    return {"ok": all(row["status"] == "pass" for row in checks), "artifact": rel(manifest_path), "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate D2 replay result generated from OrderIntentArtifact.")
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = validate_artifact(resolve(args.artifact))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']}")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
