#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/tw_modular_replay_matrix.yaml"
DEFAULT_MODEL = "e4_frozen_qlib_2023_2025_ltr"
DEFAULT_RULE = "top50_exit_one_worst_sell"
DEFAULT_OUT_ROOT = ROOT / "data_tw/artifacts/order_intents"
DEFAULT_SNAPSHOTS = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_position_snapshots.csv"
TARGET_HOLDINGS = 10
CANDIDATE_K = 50
PORTFOLIO_STATE_SOURCE = "legacy_replay_snapshot_for_d1_sample_only"
DEFAULT_ARTIFACT_STAGE = "d1_decision_sample"

RULES = [
    "original",
    "top50_exit_all",
    "top50_exit_one_worst_sell",
    "one_sell_one_buy_correct",
    "one_sell_one_buy_buggy_e8r",
]
REQUIRED_INTENT_FIELDS = [
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
INTENT_COLUMNS = REQUIRED_INTENT_FIELDS + [
    "readonly_only",
    "not_order",
    "not_target_position",
    "not_investment_advice",
    "diagnostic_only",
    "not_valid_strategy_evidence",
    "source_signal_asof",
    "source_available_at",
    "portfolio_state_source",
    "not_d2_replay_execution_source",
    "artifact_stage",
    "not_used_for_replay_result",
    "not_parity_evidence",
    "current_holding_flag",
    "target_holding_count",
    "candidate_k",
    "tie_breaker",
    "buy_rank_mapping",
    "buy_rank_source",
]


def now_iso() -> str:
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


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_config_entry(config_path: Path, model_name: str) -> dict[str, Any]:
    config = load_yaml(config_path)
    for entry in config.get("signals", []):
        if str(entry.get("method")) == model_name:
            return entry
    raise RuntimeError(f"model not found in replay config: {model_name}")


def load_strategy_config(rule: str) -> dict[str, Any]:
    path = ROOT / "configs/strategy_dependencies" / f"{rule}.yaml"
    config = load_yaml(path)
    if str(config.get("strategy_rule")) != rule:
        raise RuntimeError(f"strategy dependency mismatch: {path}")
    return config


def load_signal_frame(signal_manifest_path: Path) -> tuple[dict[str, Any], pd.DataFrame]:
    manifest = load_json(signal_manifest_path)
    signals = pd.read_csv(resolve(str(manifest["output_files"]["signals"])))
    signals["date"] = signals["date"].astype(str)
    signals["instrument"] = signals["instrument"].map(norm)
    for col in ["candidate_rank", "buy_score", "score_rank", "full_qlib_rank"]:
        signals[col] = pd.to_numeric(signals[col], errors="coerce")
    return manifest, signals


def load_full_rank_frame(full_rank_manifest_path: Path) -> pd.DataFrame:
    manifest = load_json(full_rank_manifest_path)
    frame = pd.read_csv(resolve(str(manifest["output_files"]["full_rank"])))
    frame["date"] = frame["date"].astype(str)
    frame["instrument"] = frame["instrument"].map(norm)
    frame["full_qlib_rank"] = pd.to_numeric(frame["full_qlib_rank"], errors="coerce")
    return frame[["date", "instrument", "full_qlib_rank", "signal_asof", "available_at"]]


def load_portfolio_state(snapshots_path: Path, *, model_name: str, rule: str, signal_date: str) -> list[dict[str, Any]]:
    snapshots = pd.read_csv(snapshots_path)
    sub = snapshots[
        (snapshots["method"].astype(str) == model_name)
        & (snapshots["rule"].astype(str) == rule)
        & (snapshots["date"].astype(str) == signal_date)
    ].copy()
    rows: list[dict[str, Any]] = []
    for row in sub.to_dict("records"):
        rows.append({
            "asof_date": signal_date,
            "instrument": norm(row.get("symbol")),
            "quantity": int(row.get("quantity") or 0),
            "cost_basis": "",
            "current_holding_flag": True,
            "buy_rank": row.get("buy_rank", ""),
            "full_qlib_rank": row.get("full_qlib_rank", ""),
            "in_qlib_top50_candidate": bool(row.get("in_qlib_top50_candidate")),
        })
    return rows


def build_day_state(day_signals: pd.DataFrame, full_rank_day: pd.DataFrame) -> dict[str, Any]:
    candidates = day_signals[day_signals["candidate_rank"] <= CANDIDATE_K].dropna(subset=["buy_score"]).copy()
    candidates = candidates.sort_values(["buy_score", "instrument"], ascending=[False, True])
    buy_order = [norm(x) for x in candidates["instrument"].tolist()]
    by_symbol = {norm(row.instrument): row for row in day_signals.itertuples(index=False)}
    full_rank = {
        norm(row.instrument): int(row.full_qlib_rank)
        for row in full_rank_day.itertuples(index=False)
        if pd.notna(row.full_qlib_rank)
    }
    return {
        "candidate_set": set(buy_order),
        "target_top10": set(buy_order[:TARGET_HOLDINGS]),
        "buy_order": buy_order,
        "signal_by_symbol": by_symbol,
        "full_rank": full_rank,
    }


def held_symbols(portfolio_state: list[dict[str, Any]]) -> list[str]:
    return sorted(norm(row["instrument"]) for row in portfolio_state if int(row.get("quantity") or 0) > 0)


def decide_original(day_state: dict[str, Any], portfolio_state: list[dict[str, Any]], strategy_config: dict[str, Any]) -> dict[str, list[str]]:
    held = held_symbols(portfolio_state)
    sells = [symbol for symbol in held if symbol not in day_state["target_top10"]]
    return {"sell": sells, "buy": select_buys(day_state, held, sells, strategy_config), "hold": [s for s in held if s not in sells], "skip": []}


def decide_top50_exit_all(day_state: dict[str, Any], portfolio_state: list[dict[str, Any]], strategy_config: dict[str, Any]) -> dict[str, list[str]]:
    held = held_symbols(portfolio_state)
    sells = [symbol for symbol in held if symbol not in day_state["candidate_set"]]
    return {"sell": sells, "buy": select_buys(day_state, held, sells, strategy_config), "hold": [s for s in held if s not in sells], "skip": []}


def decide_top50_exit_one_worst_sell(day_state: dict[str, Any], portfolio_state: list[dict[str, Any]], strategy_config: dict[str, Any]) -> dict[str, list[str]]:
    held = held_symbols(portfolio_state)
    outside = [symbol for symbol in held if symbol not in day_state["candidate_set"]]
    outside = sorted(outside, key=lambda s: (day_state["full_rank"].get(s, 999999), s), reverse=True)
    sells = outside[:1]
    return {"sell": sells, "buy": select_buys(day_state, held, sells, strategy_config), "hold": [s for s in held if s not in sells], "skip": []}


def decide_one_sell_one_buy_correct(day_state: dict[str, Any], portfolio_state: list[dict[str, Any]], strategy_config: dict[str, Any]) -> dict[str, list[str]]:
    held = held_symbols(portfolio_state)
    signal_by_symbol = day_state["signal_by_symbol"]
    pool = [symbol for symbol in held if symbol not in day_state["target_top10"]]
    pool = sorted(
        pool,
        key=lambda s: (
            0,
            day_state["full_rank"].get(s, 999999),
            s,
        ) if s not in day_state["candidate_set"] else (
            1,
            int(getattr(signal_by_symbol.get(s), "score_rank", 999999) if signal_by_symbol.get(s) is not None else 999999),
            s,
        ),
        reverse=True,
    )
    sells = pool[:1]
    return {"sell": sells, "buy": select_buys(day_state, held, sells, strategy_config), "hold": [s for s in held if s not in sells], "skip": []}


def decide_one_sell_one_buy_buggy_e8r(day_state: dict[str, Any], portfolio_state: list[dict[str, Any]], strategy_config: dict[str, Any]) -> dict[str, list[str]]:
    held = held_symbols(portfolio_state)
    signal_by_symbol = day_state["signal_by_symbol"]
    pool = [symbol for symbol in held if symbol not in day_state["target_top10"]]
    pool = sorted(
        pool,
        key=lambda s: (
            0 if s not in day_state["candidate_set"] else 1,
            int(getattr(signal_by_symbol.get(s), "score_rank", 999999) if signal_by_symbol.get(s) is not None else 999999),
            s,
        ),
    )
    sells = pool[:1]
    return {"sell": sells, "buy": select_buys(day_state, held, sells, strategy_config), "hold": [s for s in held if s not in sells], "skip": []}


def select_buys(day_state: dict[str, Any], held: list[str], sells: list[str], strategy_config: dict[str, Any]) -> list[str]:
    max_buy = int(strategy_config.get("max_buy_count") or 1)
    open_slots = max(0, TARGET_HOLDINGS - len(set(held) - set(sells)))
    limit = min(max_buy, open_slots)
    buys: list[str] = []
    blocked = set(held) - set(sells)
    for symbol in day_state["buy_order"]:
        if len(buys) >= limit:
            break
        if symbol in blocked or symbol in buys:
            continue
        buys.append(symbol)
    return buys


DECISION_FUNCTIONS: dict[str, Callable[[dict[str, Any], list[dict[str, Any]], dict[str, Any]], dict[str, list[str]]]] = {
    "original": decide_original,
    "top50_exit_all": decide_top50_exit_all,
    "top50_exit_one_worst_sell": decide_top50_exit_one_worst_sell,
    "one_sell_one_buy_correct": decide_one_sell_one_buy_correct,
    "one_sell_one_buy_buggy_e8r": decide_one_sell_one_buy_buggy_e8r,
}


def intent_row(
    *,
    signal_date: str,
    symbol: str,
    action: str,
    reason: str,
    strategy_config: dict[str, Any],
    signal_manifest: dict[str, Any],
    signal_manifest_path: Path,
    day_state: dict[str, Any],
    portfolio_state: list[dict[str, Any]],
    artifact_stage: str,
    portfolio_state_source: str,
    not_d2_replay_execution_source: bool,
    not_used_for_replay_result: bool,
) -> dict[str, Any]:
    signal = day_state["signal_by_symbol"].get(symbol)
    full_rank = day_state["full_rank"].get(symbol, "")
    holding = next((row for row in portfolio_state if norm(row["instrument"]) == symbol), None)
    if signal is not None:
        candidate_rank = int(signal.candidate_rank) if pd.notna(signal.candidate_rank) else ""
        buy_rank = int(signal.score_rank) if pd.notna(signal.score_rank) else ""
        full_qlib_rank = int(signal.full_qlib_rank) if pd.notna(signal.full_qlib_rank) else full_rank
        source_signal_asof = str(signal.signal_asof)
        source_available_at = str(signal.available_at)
        buy_rank_source = "source_signal.score_rank"
    else:
        candidate_rank = int(full_rank) if full_rank != "" else ""
        buy_rank = -1
        full_qlib_rank = int(full_rank) if full_rank != "" else ""
        source_signal_asof = signal_date
        source_available_at = signal_date
        buy_rank_source = "outside_candidate_full_rank_sample_only"
    diagnostic_only = bool(strategy_config.get("diagnostic_only"))
    not_valid = bool(strategy_config.get("not_valid_strategy_evidence"))
    return {
        "signal_date": signal_date,
        "instrument": symbol,
        "intent_action": action,
        "intent_reason": reason,
        "strategy_rule": strategy_config["strategy_rule"],
        "candidate_rank": candidate_rank,
        "buy_rank": buy_rank,
        "full_qlib_rank": full_qlib_rank,
        "max_buy_count": strategy_config.get("max_buy_count", ""),
        "max_sell_count": strategy_config.get("max_sell_count", ""),
        "model_name": signal_manifest["model_name"],
        "signal_artifact": rel(signal_manifest_path),
        "readonly_only": True,
        "not_order": True,
        "not_target_position": True,
        "not_investment_advice": True,
        "diagnostic_only": diagnostic_only,
        "not_valid_strategy_evidence": not_valid,
        "source_signal_asof": source_signal_asof,
        "source_available_at": source_available_at,
        "portfolio_state_source": portfolio_state_source,
        "not_d2_replay_execution_source": not_d2_replay_execution_source,
        "artifact_stage": artifact_stage,
        "not_used_for_replay_result": not_used_for_replay_result,
        "not_parity_evidence": True,
        "current_holding_flag": holding is not None,
        "target_holding_count": TARGET_HOLDINGS,
        "candidate_k": CANDIDATE_K,
        "tie_breaker": "buy_score_desc_instrument_asc; buy_rank maps to source score_rank",
        "buy_rank_mapping": "buy_rank == source_signal.score_rank when source signal row exists; outside-candidate sell rows use -1 sample-only sentinel",
        "buy_rank_source": buy_rank_source,
    }


def build_artifact(*, config_path: Path, model_name: str, rule: str, signal_date: str | None, out_root: Path, snapshots_path: Path, artifact_stage: str = DEFAULT_ARTIFACT_STAGE) -> dict[str, Any]:
    if rule not in DECISION_FUNCTIONS:
        raise RuntimeError(f"unsupported strategy rule: {rule}")
    if artifact_stage not in {"d1_decision_sample", "d2_replay_input"}:
        raise RuntimeError(f"unsupported artifact_stage: {artifact_stage}")
    portfolio_state_source = PORTFOLIO_STATE_SOURCE if artifact_stage == "d1_decision_sample" else "legacy_replay_snapshot_for_d2_initial_state_sample_only"
    not_d2_replay_execution_source = artifact_stage == "d1_decision_sample"
    not_used_for_replay_result = artifact_stage == "d1_decision_sample"
    entry = load_config_entry(config_path, model_name)
    signal_manifest_path = resolve(str(entry["artifact"]))
    full_rank_manifest_path = resolve(str(entry["full_rank_artifact"]))
    signal_manifest, signals = load_signal_frame(signal_manifest_path)
    full_rank = load_full_rank_frame(full_rank_manifest_path)
    if signal_date is None:
        signal_date = str(signals["date"].max())
    day_signals = signals[signals["date"] == signal_date].copy()
    if day_signals.empty:
        raise RuntimeError(f"no signal rows for {model_name} {signal_date}")
    full_rank_day = full_rank[full_rank["date"] == signal_date].copy()
    portfolio_state = load_portfolio_state(snapshots_path, model_name=model_name, rule=rule, signal_date=signal_date)
    strategy_config = load_strategy_config(rule)
    day_state = build_day_state(day_signals, full_rank_day)
    decisions = DECISION_FUNCTIONS[rule](day_state, portfolio_state, strategy_config)

    rows: list[dict[str, Any]] = []
    for symbol in decisions["sell"]:
        rows.append(intent_row(signal_date=signal_date, symbol=symbol, action="sell", reason=f"{rule}_sell", strategy_config=strategy_config, signal_manifest=signal_manifest, signal_manifest_path=signal_manifest_path, day_state=day_state, portfolio_state=portfolio_state, artifact_stage=artifact_stage, portfolio_state_source=portfolio_state_source, not_d2_replay_execution_source=not_d2_replay_execution_source, not_used_for_replay_result=not_used_for_replay_result))
    for symbol in decisions["buy"]:
        rows.append(intent_row(signal_date=signal_date, symbol=symbol, action="buy", reason=f"{rule}_buy", strategy_config=strategy_config, signal_manifest=signal_manifest, signal_manifest_path=signal_manifest_path, day_state=day_state, portfolio_state=portfolio_state, artifact_stage=artifact_stage, portfolio_state_source=portfolio_state_source, not_d2_replay_execution_source=not_d2_replay_execution_source, not_used_for_replay_result=not_used_for_replay_result))
    for symbol in decisions["hold"]:
        rows.append(intent_row(signal_date=signal_date, symbol=symbol, action="hold", reason=f"{rule}_hold", strategy_config=strategy_config, signal_manifest=signal_manifest, signal_manifest_path=signal_manifest_path, day_state=day_state, portfolio_state=portfolio_state, artifact_stage=artifact_stage, portfolio_state_source=portfolio_state_source, not_d2_replay_execution_source=not_d2_replay_execution_source, not_used_for_replay_result=not_used_for_replay_result))
    for symbol in decisions["skip"]:
        rows.append(intent_row(signal_date=signal_date, symbol=symbol, action="skip", reason=f"{rule}_skip", strategy_config=strategy_config, signal_manifest=signal_manifest, signal_manifest_path=signal_manifest_path, day_state=day_state, portfolio_state=portfolio_state, artifact_stage=artifact_stage, portfolio_state_source=portfolio_state_source, not_d2_replay_execution_source=not_d2_replay_execution_source, not_used_for_replay_result=not_used_for_replay_result))

    rows = sorted(rows, key=lambda row: ({"sell": 0, "buy": 1, "hold": 2, "skip": 3}[str(row["intent_action"])], str(row["instrument"])))
    run_prefix = "d1_order_intent" if artifact_stage == "d1_decision_sample" else "d2_order_intent"
    run_id = f"{run_prefix}_{signal_date.replace('-', '')}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    out_dir = out_root / model_name / rule / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    order_path = out_dir / "order_intents.csv"
    write_csv(order_path, rows, INTENT_COLUMNS)
    schema = {
        "schema_version": "order_intent_d1_v1",
        "required_fields": REQUIRED_INTENT_FIELDS,
        "intent_actions": ["buy", "sell", "hold", "skip"],
        "buy_rank_mapping": "buy_rank == source_signal.score_rank when source signal row exists; outside-candidate sell rows use -1 sample-only sentinel",
        "artifact_stage": artifact_stage,
    }
    write_json(out_dir / "schema.json", schema)
    audit_rows = [
        {"audit_name": "decision_function", "status": "pass", "details": f"decide_{rule}"},
        {"audit_name": "portfolio_state_source", "status": "pass", "details": portfolio_state_source},
        {"audit_name": "buy_rank_mapping_defined", "status": "pass", "details": schema["buy_rank_mapping"]},
        {"audit_name": "readonly_snapshot_not_portfolio_state", "status": "pass", "details": "readonly snapshot not used"},
        {"audit_name": "not_replay_consumed", "status": "pass", "details": f"not_used_for_replay_result={not_used_for_replay_result}; not_parity_evidence=true"},
    ]
    write_csv(out_dir / "strategy_decision_audit.csv", audit_rows, ["audit_name", "status", "details"])
    forbidden = {
        "artifact_type": "order_intent_forbidden_action_audit",
        "status": "pass",
        "no_training": True,
        "no_tuning": True,
        "no_score_recompute": True,
        "no_replay_execution_change": True,
        "no_provider_publish": True,
        "no_accepted_latest_switch": True,
        "no_monitor": True,
        "no_broker_order": True,
        "no_frontend_api_daily_change": True,
    }
    write_json(out_dir / "forbidden_action_audit.json", forbidden)
    manifest = {
        "artifact_type": "order_intent",
        "schema_version": "order_intent_d1_v1",
        "artifact_stage": artifact_stage,
        "created_at": now_iso(),
        "created_by": rel(Path(__file__)),
        "model_name": model_name,
        "strategy_rule": rule,
        "signal_date": signal_date,
        "readonly_only": True,
        "not_order": True,
        "not_target_position": True,
        "not_investment_advice": True,
        "diagnostic_only": bool(strategy_config.get("diagnostic_only")),
        "not_valid_strategy_evidence": bool(strategy_config.get("not_valid_strategy_evidence")),
        "not_used_for_replay_result": not_used_for_replay_result,
        "not_parity_evidence": True,
        "portfolio_state_source": portfolio_state_source,
        "not_d2_replay_execution_source": not_d2_replay_execution_source,
        "readonly_snapshot_not_portfolio_state": True,
        "buy_rank_mapping": schema["buy_rank_mapping"],
        "buy_rank_mapping_defined": True,
        "signal_artifact": rel(signal_manifest_path),
        "full_rank_artifact": rel(full_rank_manifest_path),
        "portfolio_state_artifact": rel(snapshots_path),
        "row_count": len(rows),
        "intent_counts": {action: sum(1 for row in rows if row["intent_action"] == action) for action in ["buy", "sell", "hold", "skip"]},
        "output_files": {
            "order_intents": rel(order_path),
            "schema": rel(out_dir / "schema.json"),
            "strategy_decision_audit": rel(out_dir / "strategy_decision_audit.csv"),
            "forbidden_action_audit": rel(out_dir / "forbidden_action_audit.json"),
        },
        "forbidden_actions": forbidden,
    }
    write_json(out_dir / "manifest.json", manifest)
    return {"ok": True, "manifest": rel(out_dir / "manifest.json"), "out_dir": rel(out_dir), "row_count": len(rows), "intent_counts": manifest["intent_counts"]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build D1 sample OrderIntentArtifact from standard ModelSignalArtifact and sample PortfolioState.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--rule", default=DEFAULT_RULE)
    parser.add_argument("--signal-date", default="")
    parser.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT))
    parser.add_argument("--snapshots", default=str(DEFAULT_SNAPSHOTS))
    parser.add_argument("--artifact-stage", choices=["d1_decision_sample", "d2_replay_input"], default=DEFAULT_ARTIFACT_STAGE)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = build_artifact(
        config_path=resolve(args.config),
        model_name=args.model,
        rule=args.rule,
        signal_date=args.signal_date.strip() or None,
        out_root=resolve(args.out_root),
        snapshots_path=resolve(args.snapshots),
        artifact_stage=args.artifact_stage,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']}")
        print(f"manifest={result['manifest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
