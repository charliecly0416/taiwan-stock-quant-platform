#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TARGET_ASOF = "2026-06-26"
MODEL_ID = "e4_frozen_qlib_2018_2022"

QLIB_PROVIDER = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin"
QLIB_NORMALIZED = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized"
QLIB_DUMP_BIN = ROOT / "qlib_pipeline/scripts/dump_bin.py"
QLIB_DAILY_SIGNAL_SCRIPT = ROOT / "qlib_pipeline/examples/tw/run_option_c_daily_signal_option_c_provider.py"
MODEL_INFERENCE_BUILDER = ROOT / "scripts/build_tw_model_inference_input.py"
MODEL_SCORE_JOB = ROOT / "scripts/run_tw_model_score_job.py"
MODELA_COMMON = ROOT / "scripts/tw_modela_score_common.py"
UNIVERSE = (
    ROOT
    / "qlib_pipeline/data_tw/experiments/option_c_forward_validation/"
    "timed_data_availability_retry_20260601T101323Z/symbols_accepted_prediction_universe.txt"
)

OUT_DECISION = ROOT / "data_tw/catalog/dng15_provider_or_bridge_repair_decision.json"
OUT_READINESS = ROOT / "data_tw/catalog/dng15_modela_20260626_readiness.json"

FORBIDDEN_ACTIONS = {
    "real_data_fetch_triggered": False,
    "provider_refresh_triggered": False,
    "provider_publish_triggered": False,
    "qlib_accepted_latest_switched": False,
    "readonly_latest_published": False,
    "agent_prompt_published": False,
    "production_default_model_or_strategy_switched": False,
    "model_training_triggered": False,
    "model_tuning_triggered": False,
    "strategy_replay_triggered": False,
    "broker_order_quick_trade_triggered": False,
    "target_position_or_weight_generated": False,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_universe() -> list[str]:
    if not UNIVERSE.exists():
        return []
    return sorted(line.strip().upper() for line in UNIVERSE.read_text(encoding="utf-8").splitlines() if line.strip())


def provider_calendar_max() -> str | None:
    path = QLIB_PROVIDER / "calendars/day.txt"
    if not path.exists():
        return None
    rows = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return max(rows) if rows else None


def normalized_summary(asof: str, symbols: list[str]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    missing_files: list[str] = []
    missing_asof: list[str] = []
    for symbol in symbols:
        path = QLIB_NORMALIZED / f"{symbol}.csv"
        if not path.exists():
            missing_files.append(symbol)
            continue
        try:
            dates = pd.read_csv(path, usecols=["date"])["date"].astype(str)
        except Exception:
            missing_files.append(symbol)
            continue
        has_asof = bool((dates == asof).any())
        if not has_asof:
            missing_asof.append(symbol)
        rows.append(
            {
                "instrument": symbol,
                "date_min": str(dates.min()) if not dates.empty else "",
                "date_max": str(dates.max()) if not dates.empty else "",
                "has_asof": has_asof,
            }
        )
    frame = pd.DataFrame(rows)
    return {
        "source_path": rel(QLIB_NORMALIZED),
        "symbols_expected": len(symbols),
        "symbols_found": len(rows),
        "symbols_with_asof": int(frame["has_asof"].sum()) if not frame.empty else 0,
        "min_date_max": str(frame["date_max"].min()) if not frame.empty else "",
        "max_date_max": str(frame["date_max"].max()) if not frame.empty else "",
        "missing_files_count": len(missing_files),
        "missing_files_head": missing_files[:30],
        "missing_asof_count": len(missing_asof),
        "missing_asof_head": missing_asof[:30],
        "status": "READY" if symbols and len(missing_files) == 0 and len(missing_asof) == 0 else "MISSING_TARGET_ASOF",
    }


def raw_daily_price_evidence(asof: str) -> dict[str, Any]:
    candidates = sorted((ROOT / "data_tw/ops/daily_auto_update").glob(f"daily_tw_stock_auto_update_{asof.replace('-', '')}_*/daily_source_inventory.json"))
    evidence: list[dict[str, Any]] = []
    for path in candidates:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        source = payload.get("sources", {}).get("finmind_raw_daily_price", {})
        if source:
            evidence.append(
                {
                    "path": rel(path),
                    "source_max_date": source.get("source_max_date", ""),
                    "row_count": source.get("row_count", ""),
                    "symbol_count": source.get("symbol_count", ""),
                    "source_boundary": source.get("source_boundary", ""),
                }
            )
    ready = [row for row in evidence if str(row.get("source_max_date")) >= asof]
    return {
        "status": "READY_FROM_PRIOR_JOB" if ready else "MISSING",
        "candidate_count": len(evidence),
        "ready_candidate_count": len(ready),
        "latest_ready_evidence": ready[-1] if ready else {},
    }


def hardcoded_risk_inventory(asof: str) -> list[dict[str, Any]]:
    checks = [
        {
            "file": MODELA_COMMON,
            "patterns": ["TARGET_ASOF = \"2026-06-25\"", "readiness_matrix/2026-06-25", "dng2_r_price_market_calendar_20260625", "option_c_150_qlib_bin"],
        },
        {
            "file": MODEL_INFERENCE_BUILDER,
            "patterns": ["PRICE_MARKET_READINESS", "PRICE_STORE_DIR", "QLIB_PROVIDER", "TARGET_ASOF"],
        },
        {
            "file": MODEL_SCORE_JOB,
            "patterns": ["run_option_c_daily_signal_option_c_provider.py", "QLIB_PROVIDER", "TARGET_ASOF", "--normal"],
        },
        {
            "file": QLIB_DAILY_SIGNAL_SCRIPT,
            "patterns": ["OPTION_C_PROVIDER", "option_c_150_qlib_bin", "latest_signal.json", "publish_triggered"],
        },
    ]
    out: list[dict[str, Any]] = []
    for check in checks:
        text = check["file"].read_text(encoding="utf-8") if check["file"].exists() else ""
        out.append(
            {
                "file": rel(check["file"]),
                "exists": check["file"].exists(),
                "matched_patterns": [pattern for pattern in check["patterns"] if pattern in text],
                "risk_for_target_asof": asof,
            }
        )
    return out


def build(asof: str) -> dict[str, Any]:
    symbols = read_universe()
    calendar_max = provider_calendar_max()
    normalized = normalized_summary(asof, symbols)
    raw = raw_daily_price_evidence(asof)
    hardcoded = hardcoded_risk_inventory(asof)

    route_a = {
        "route": "A_FORMAL_QLIB_PROVIDER_REFRESH",
        "status": "BLOCKED_NOT_EXECUTED",
        "blockers": ["needs_network_provider_refresh", "requires_formal_provider_write_or_publish_flow"],
        "reason": "DNG15 was not authorized to trigger real network refresh or formal provider publish/write.",
    }
    route_b_blockers: list[str] = []
    if calendar_max is None or calendar_max < asof:
        route_b_blockers.append("qlib_provider_calendar_stale")
    if normalized["symbols_with_asof"] != len(symbols):
        route_b_blockers.append("normalized_source_missing_asof")
    if normalized["symbols_with_asof"] == len(symbols) and QLIB_DUMP_BIN.exists():
        route_b_status = "FEASIBLE_NOT_EXECUTED_BY_DNG15_DIAGNOSTIC"
    else:
        route_b_status = "BLOCKED_NOT_SAFE_TO_BUILD"

    route_b = {
        "route": "B_VALIDATED_CANONICAL_BRIDGE",
        "status": route_b_status,
        "blockers": route_b_blockers,
        "reason": (
            "A validated isolated provider bridge can only be built from same-lineage Option C normalized data. "
            "Current Option C normalized source does not contain the target asof."
        )
        if route_b_blockers
        else "Local same-mouth normalized data and dump tool appear available.",
        "dump_tool": rel(QLIB_DUMP_BIN),
        "dump_tool_exists": QLIB_DUMP_BIN.exists(),
        "not_published_latest": True,
        "production_allowed": False,
    }

    selected_route = "B_VALIDATED_CANONICAL_BRIDGE"
    selected_status = "BLOCKED"
    concrete_blocker = "normalized_source_missing_asof"
    if route_b["status"].startswith("FEASIBLE"):
        selected_status = "FEASIBLE"
        concrete_blocker = "requires_bridge_builder_execution"
    elif route_a["status"].startswith("BLOCKED"):
        concrete_blocker = "normalized_source_missing_asof_and_formal_refresh_requires_network"

    readiness = {
        "schema_version": "dng15.modela_20260626_readiness.v1",
        "generated_at": utc_now(),
        "asof": asof,
        "model_id": MODEL_ID,
        "status": "BLOCKED_INPUT_NOT_READY" if selected_status == "BLOCKED" else "FEASIBLE_NOT_SCORED",
        "score_status": "NOT_SCORED",
        "selected_route": selected_route,
        "blocked_at": concrete_blocker,
        "blockers": sorted(set(route_a["blockers"] + route_b_blockers)),
        "raw_daily_price_evidence": raw,
        "formal_provider": {
            "provider_uri": rel(QLIB_PROVIDER),
            "calendar_max": calendar_max,
            "calendar_status": "READY" if calendar_max and calendar_max >= asof else "STALE",
        },
        "formal_option_c_normalized": normalized,
        "model_inference_input": {
            "generated": False,
            "status": "BLOCKED_INPUT_NOT_READY",
            "reason": concrete_blocker,
        },
        "score_job": {"generated": False, "status": "NOT_SCORED"},
        "model_signal_artifact": {"generated": False, "status": "NOT_GENERATED"},
        "strategy_input_bundle": {"generated": False, "status": "NOT_GENERATED"},
        "readonly_source_context": {"generated": False, "status": "NOT_GENERATED"},
        "agent_source_context": {"generated": False, "status": "NOT_GENERATED"},
        "hardcoded_risk_inventory": hardcoded,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "production_allowed": False,
        "not_published_latest": True,
    }

    decision = {
        "schema_version": "dng15.provider_or_bridge_repair_decision.v1",
        "generated_at": utc_now(),
        "asof": asof,
        "model_id": MODEL_ID,
        "decision": "NO_SCORE_GENERATED_BLOCKER_CONCRETIZED" if selected_status == "BLOCKED" else "BRIDGE_FEASIBLE_NEXT",
        "selected_route": selected_route,
        "route_a": route_a,
        "route_b": route_b,
        "concrete_blocker": concrete_blocker,
        "recommended_next_route": (
            "DNG15_REPAIR_SAME_LINEAGE_NORMALIZED_REFRESH_OR_EXPLICIT_MIXED_PROVIDER_BRIDGE_DECISION"
            if selected_status == "BLOCKED"
            else "DNG16_DAILY_AUTO_MODEL_SCORE_INTEGRATION"
        ),
        "readiness_path": rel(OUT_READINESS),
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "production_go": False,
        "publish_latest_authorized": False,
    }

    write_json(OUT_READINESS, readiness)
    write_json(OUT_DECISION, decision)
    return {"decision": decision, "readiness": readiness}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build DNG15 provider/bridge repair decision artifacts.")
    parser.add_argument("--asof", default=TARGET_ASOF)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = build(args.asof)
    summary = {
        "decision": payload["decision"]["decision"],
        "selected_route": payload["decision"]["selected_route"],
        "concrete_blocker": payload["decision"]["concrete_blocker"],
        "readiness_status": payload["readiness"]["status"],
        "decision_path": rel(OUT_DECISION),
        "readiness_path": rel(OUT_READINESS),
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=True, indent=2))
    else:
        print(f"{summary['decision']} {summary['concrete_blocker']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
