#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FIELDS = [
    "signal_date",
    "instrument",
    "intent_action",
    "intent_reason",
    "strategy_rule",
    "candidate_rank",
    "buy_rank",
    "full_qlib_rank",
    "max_buy_count",
    "max_sell_count",
    "model_name",
    "signal_artifact",
]
ALLOWED_ACTIONS = {"buy", "sell", "hold", "skip"}
FORBIDDEN_EXACT_FIELDS = {
    "execution_date",
    "execution_price",
    "execution_quantity",
    "commission",
    "tax",
    "fee",
    "fee_and_tax",
    "cash",
    "equity",
    "daily_return",
    "drawdown",
    "realized_pnl",
    "unrealized_pnl",
    "broker_order_id",
    "broker_account",
    "quick_trade_status",
    "real_order_status",
    "provider_publish_status",
    "accepted_latest_status",
    "target_position",
    "target_weight",
}
FORBIDDEN_PREFIXES = ("future_return_", "future_excess_return_", "forward_return_", "label_")


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


def bool_series_true(frame: pd.DataFrame, column: str) -> bool:
    if column not in frame.columns:
        return False
    return frame[column].map(lambda value: str(value).strip().lower() in {"true", "1", "yes"}).all()


def check(name: str, ok: bool, details: str = "") -> dict[str, Any]:
    return {"name": name, "status": "pass" if ok else "fail", "details": details}


def source_signal_frame(frame: pd.DataFrame) -> pd.DataFrame:
    paths = sorted(str(x) for x in frame["signal_artifact"].dropna().unique())
    if len(paths) != 1:
        raise RuntimeError(f"expected one signal_artifact, got {paths}")
    manifest = load_json(resolve(paths[0]))
    signals = pd.read_csv(resolve(str(manifest["output_files"]["signals"])))
    signals["date"] = signals["date"].astype(str)
    signals["instrument"] = signals["instrument"].astype(str)
    signals["score_rank"] = pd.to_numeric(signals["score_rank"], errors="coerce")
    return signals


def validate_buy_rank(frame: pd.DataFrame) -> tuple[bool, str]:
    try:
        signals = source_signal_frame(frame)
    except Exception as exc:
        return False, str(exc)
    rows = frame[pd.to_numeric(frame["buy_rank"], errors="coerce") >= 0].copy()
    if rows.empty:
        return True, "no source-signal rows requiring score_rank mapping"
    merged = rows.merge(
        signals[["date", "instrument", "score_rank"]],
        left_on=["signal_date", "instrument"],
        right_on=["date", "instrument"],
        how="left",
    )
    left = pd.to_numeric(merged["buy_rank"], errors="coerce")
    right = pd.to_numeric(merged["score_rank"], errors="coerce")
    bad = merged[left.ne(right) | right.isna()]
    if not bad.empty:
        return False, bad[["signal_date", "instrument", "buy_rank", "score_rank"]].head(10).to_dict("records").__repr__()
    return True, "buy_rank == source_signal.score_rank for source-signal rows"


def validate_artifact(manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    order_path = resolve(str((manifest.get("output_files") or {}).get("order_intents", "")))
    frame = pd.read_csv(order_path)
    columns = set(frame.columns)
    missing = sorted(set(REQUIRED_FIELDS) - columns)
    forbidden = sorted(
        col for col in columns
        if col in FORBIDDEN_EXACT_FIELDS
        or col.startswith(FORBIDDEN_PREFIXES)
        or col in {"relevance_10d_top_heavy", "ltr_relevance_label"}
    )
    checks: list[dict[str, Any]] = [
        check("artifact_type", manifest.get("artifact_type") == "order_intent", str(manifest.get("artifact_type"))),
        check("schema_version", str(manifest.get("schema_version")) == "order_intent_d1_v1", str(manifest.get("schema_version"))),
        check("required_fields", not missing, "|".join(missing)),
        check("intent_action_enum", set(frame.get("intent_action", pd.Series(dtype=str)).astype(str)).issubset(ALLOWED_ACTIONS)),
        check("forbidden_fields_absent", not forbidden, "|".join(forbidden)),
        check("readonly_only", manifest.get("readonly_only") is True and bool_series_true(frame, "readonly_only")),
        check("not_order", manifest.get("not_order") is True and bool_series_true(frame, "not_order")),
        check("not_target_position", manifest.get("not_target_position") is True and bool_series_true(frame, "not_target_position")),
        check("not_investment_advice", manifest.get("not_investment_advice") is True and bool_series_true(frame, "not_investment_advice")),
        check("artifact_stage", manifest.get("artifact_stage") in {"d1_decision_sample", "d2_replay_input"} and set(frame.get("artifact_stage", pd.Series(dtype=str)).astype(str)).issubset({"d1_decision_sample", "d2_replay_input"}), str(manifest.get("artifact_stage"))),
        check("not_used_for_replay_result", (manifest.get("artifact_stage") == "d2_replay_input" and manifest.get("not_used_for_replay_result") is False) or (manifest.get("not_used_for_replay_result") is True and bool_series_true(frame, "not_used_for_replay_result"))),
        check("not_parity_evidence", manifest.get("not_parity_evidence") is True and bool_series_true(frame, "not_parity_evidence")),
        check("portfolio_state_source", bool(manifest.get("portfolio_state_source")) and "portfolio_state_source" in frame.columns and frame["portfolio_state_source"].astype(str).ne("").all()),
        check("legacy_portfolio_state_boundary", (manifest.get("portfolio_state_source") != "legacy_replay_snapshot_for_d1_sample_only" or (manifest.get("not_d2_replay_execution_source") is True and bool_series_true(frame, "not_d2_replay_execution_source"))) and (manifest.get("portfolio_state_source") != "legacy_replay_snapshot_for_d2_initial_state_sample_only" or manifest.get("not_d2_replay_execution_source") is False), str(manifest.get("portfolio_state_source"))),
        check("readonly_snapshot_not_portfolio_state", manifest.get("readonly_snapshot_not_portfolio_state") is True),
        check("signal_artifact_exists", resolve(str(manifest.get("signal_artifact", ""))).exists()),
    ]
    if "intent_reason" in frame.columns and "intent_action" in frame.columns:
        hold_skip = frame[frame["intent_action"].isin(["hold", "skip"])]
        checks.append(check("hold_skip_reasons", hold_skip.empty or hold_skip["intent_reason"].astype(str).str.contains("_hold|_skip", regex=True).all()))
    for action, config_col in [("buy", "max_buy_count"), ("sell", "max_sell_count")]:
        ok = True
        details = ""
        for (day, rule), group in frame.groupby(["signal_date", "strategy_rule"]):
            max_value = str(group[config_col].iloc[0])
            if max_value == "unbounded" and action == "sell":
                continue
            limit = int(float(max_value))
            count = int((group["intent_action"] == action).sum())
            if count > limit:
                ok = False
                details = f"{day}/{rule}: {action} count {count} > {limit}"
                break
        checks.append(check(f"daily_{action}_count_lte_max", ok, details))
    diagnostic_rule = str(manifest.get("strategy_rule")) == "one_sell_one_buy_buggy_e8r"
    checks.append(check(
        "diagnostic_rule_boundary",
        (not diagnostic_rule) or (manifest.get("diagnostic_only") is True and manifest.get("not_valid_strategy_evidence") is True and bool_series_true(frame, "diagnostic_only") and bool_series_true(frame, "not_valid_strategy_evidence")),
    ))
    mapping_ok = bool(manifest.get("buy_rank_mapping_defined")) and "source_signal.score_rank" in str(manifest.get("buy_rank_mapping", ""))
    checks.append(check("buy_rank_mapping_defined", mapping_ok, str(manifest.get("buy_rank_mapping", ""))))
    buy_rank_ok, buy_rank_details = validate_buy_rank(frame)
    checks.append(check("buy_rank_mapping_validated", buy_rank_ok, buy_rank_details))
    audit_path = resolve(str((manifest.get("output_files") or {}).get("forbidden_action_audit", "")))
    audit = load_json(audit_path) if audit_path.exists() else {}
    checks.append(check("forbidden_action_audit_pass", audit.get("status") == "pass", rel(audit_path)))
    ok = all(row["status"] == "pass" for row in checks)
    return {
        "ok": ok,
        "artifact": rel(manifest_path),
        "order_intents": rel(order_path),
        "row_count": int(len(frame)),
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate D1 OrderIntentArtifact.")
    parser.add_argument("--artifact", required=True, help="OrderIntentArtifact manifest path")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = validate_artifact(resolve(args.artifact))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']}")
        print(f"artifact={result['artifact']}")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
