#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OPS_DIR = ROOT / "data_tw/ops/daily_auto_update"
CATALOG_DIR = ROOT / "data_tw/catalog"

OBS_JSON = CATALOG_DIR / "dng14_multi_day_chain_observation.json"
OBS_CSV = CATALOG_DIR / "dng14_multi_day_chain_observation.csv"
OVERLAY_JSON = CATALOG_DIR / "dng14_latest_status_chain_overlay.json"

CLASSIFICATIONS = {
    "READY_CHAIN",
    "RAW_READY_BUT_QLIB_PROVIDER_STALE",
    "DATA_WINDOW_WAIT",
    "WEEKEND_OR_HOLIDAY_SKIPPED",
    "MODEL_A_SCORE_MISSING",
    "STRATEGY_OR_READONLY_CONTEXT_MISSING",
    "PUBLISH_READY_BUT_NOT_PUBLISHED",
    "BLOCKED_OTHER",
}

CSV_FIELDS = [
    "asof",
    "classification",
    "representative_job_id",
    "representative_job_dir",
    "created_at",
    "is_trading_day",
    "counts_as_trade_day",
    "data_window_status",
    "raw_status",
    "qlib_provider_view_status",
    "model_a_score_status",
    "model_a_signal_status",
    "strategy_input_bundle_status",
    "readonly_source_context_status",
    "publish_latest_gate_status",
    "blocked_at",
    "blocker_reason",
    "next_required_action",
    "candidate_count",
    "selection_reason",
    "conflict_detected",
    "forbidden_actions_all_false",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in CSV_FIELDS})


def parse_created_at(value: Any) -> str:
    return str(value or "")


def forbidden_all_false(status: dict[str, Any]) -> bool:
    forbidden = status.get("forbidden_actions")
    return bool(isinstance(forbidden, dict) and forbidden.get("all_false") is True)


def classify(status: dict[str, Any]) -> str:
    data_window = str(status.get("data_window_status") or "")
    raw_status = str(status.get("raw_status") or "")
    qlib_status = str(status.get("qlib_provider_view_status") or "")
    score_status = str(status.get("model_a_score_status") or "")
    signal_status = str(status.get("model_a_signal_status") or "")
    strategy_status = str(status.get("strategy_input_bundle_status") or "")
    readonly_status = str(status.get("readonly_source_context_status") or "")
    publish_status = str(status.get("publish_latest_gate_status") or "")
    blocked_at = str(status.get("blocked_at") or "")

    if data_window == "NON_TRADING_DAY_OR_WEEKEND" or status.get("is_trading_day") is False or blocked_at == "market_calendar":
        return "WEEKEND_OR_HOLIDAY_SKIPPED"
    if data_window == "WAITING_FOR_TAIPEI_DATA_WINDOW":
        return "DATA_WINDOW_WAIT"
    if raw_status.startswith("READY") and qlib_status == "BLOCKED_PROVIDER_VIEW_STALE":
        return "RAW_READY_BUT_QLIB_PROVIDER_STALE"
    if signal_status == "READY" and strategy_status == "READY" and readonly_status == "READY":
        if publish_status == "DISABLED_BY_DEFAULT":
            return "READY_CHAIN"
        return "PUBLISH_READY_BUT_NOT_PUBLISHED"
    if qlib_status == "READY" and score_status in {"MISSING", "SOURCE_RUN_EXISTS_BUT_STANDARD_SCORE_ARTIFACT_MISSING"}:
        return "MODEL_A_SCORE_MISSING"
    if signal_status == "READY" and (strategy_status != "READY" or readonly_status != "READY"):
        return "STRATEGY_OR_READONLY_CONTEXT_MISSING"
    return "BLOCKED_OTHER"


def candidate_record(status_path: Path) -> dict[str, Any] | None:
    status = load_json(status_path)
    if not status:
        return None
    job_dir = status_path.parent
    ledger_path = job_dir / "skipped_asof_ledger.json"
    job_path = job_dir / "job.json"
    return {
        "job_dir": rel(job_dir),
        "daily_chain_status_path": rel(status_path),
        "skipped_asof_ledger_path": rel(ledger_path) if ledger_path.exists() else "",
        "job_path": rel(job_path) if job_path.exists() else "",
        "status": status,
        "ledger": load_json(ledger_path) if ledger_path.exists() else {},
        "job": load_json(job_path) if job_path.exists() else {},
        "required_fields_present": bool(status.get("required_fields_present")),
        "forbidden_actions_all_false": forbidden_all_false(status),
        "created_at": parse_created_at(status.get("created_at")),
        "classification": classify(status),
    }


def select_representative(candidates: list[dict[str, Any]]) -> tuple[dict[str, Any], str]:
    eligible = [
        candidate
        for candidate in candidates
        if candidate["required_fields_present"] and candidate["forbidden_actions_all_false"]
    ]
    pool = eligible or candidates
    chosen = sorted(pool, key=lambda item: item["created_at"], reverse=True)[0]
    if eligible:
        return chosen, "latest_created_at_among_required_fields_and_forbidden_actions_all_false"
    return chosen, "latest_created_at_no_fully_eligible_candidate"


def counts_as_trade_day(status: dict[str, Any], classification: str) -> bool:
    return status.get("is_trading_day") is True and classification != "WEEKEND_OR_HOLIDAY_SKIPPED"


def flatten_row(asof: str, rep: dict[str, Any], candidates: list[dict[str, Any]], reason: str) -> dict[str, Any]:
    status = rep["status"]
    classifications = {candidate["classification"] for candidate in candidates}
    return {
        "asof": asof,
        "classification": rep["classification"],
        "representative_job_id": status.get("job_id", ""),
        "representative_job_dir": rep["job_dir"],
        "created_at": status.get("created_at", ""),
        "is_trading_day": status.get("is_trading_day", ""),
        "counts_as_trade_day": counts_as_trade_day(status, rep["classification"]),
        "data_window_status": status.get("data_window_status", ""),
        "raw_status": status.get("raw_status", ""),
        "qlib_provider_view_status": status.get("qlib_provider_view_status", ""),
        "model_a_score_status": status.get("model_a_score_status", ""),
        "model_a_signal_status": status.get("model_a_signal_status", ""),
        "strategy_input_bundle_status": status.get("strategy_input_bundle_status", ""),
        "readonly_source_context_status": status.get("readonly_source_context_status", ""),
        "publish_latest_gate_status": status.get("publish_latest_gate_status", ""),
        "blocked_at": status.get("blocked_at", ""),
        "blocker_reason": status.get("blocker_reason", ""),
        "next_required_action": status.get("next_required_action", ""),
        "candidate_count": len(candidates),
        "selection_reason": reason,
        "conflict_detected": len(classifications) > 1,
        "forbidden_actions_all_false": rep["forbidden_actions_all_false"],
    }


def build_observation() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    by_asof: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in sorted(OPS_DIR.glob("*/daily_chain_status.json")):
        record = candidate_record(path)
        if not record:
            continue
        asof = str(record["status"].get("asof") or "")
        if asof:
            by_asof[asof].append(record)

    rows: list[dict[str, Any]] = []
    asof_entries: list[dict[str, Any]] = []
    classification_counts: Counter[str] = Counter()
    forbidden_violations: list[dict[str, Any]] = []

    for asof in sorted(by_asof):
        candidates = by_asof[asof]
        rep, reason = select_representative(candidates)
        row = flatten_row(asof, rep, candidates, reason)
        rows.append(row)
        classification_counts[row["classification"]] += 1
        if not row["forbidden_actions_all_false"]:
            forbidden_violations.append({"asof": asof, "job_dir": rep["job_dir"]})
        candidate_summaries = []
        for candidate in sorted(candidates, key=lambda item: item["created_at"], reverse=True):
            status = candidate["status"]
            candidate_summaries.append({
                "job_id": status.get("job_id", ""),
                "job_dir": candidate["job_dir"],
                "daily_chain_status_path": candidate["daily_chain_status_path"],
                "skipped_asof_ledger_path": candidate["skipped_asof_ledger_path"],
                "job_path": candidate["job_path"],
                "created_at": candidate["created_at"],
                "classification": candidate["classification"],
                "required_fields_present": candidate["required_fields_present"],
                "forbidden_actions_all_false": candidate["forbidden_actions_all_false"],
                "raw_status": status.get("raw_status", ""),
                "qlib_provider_view_status": status.get("qlib_provider_view_status", ""),
                "model_a_score_status": status.get("model_a_score_status", ""),
                "blocked_at": status.get("blocked_at", ""),
            })
        asof_entries.append({
            **row,
            "daily_chain_status_path": rep["daily_chain_status_path"],
            "skipped_asof_ledger_path": rep["skipped_asof_ledger_path"],
            "lineage_evidence": rep["status"].get("lineage_evidence", {}),
            "candidates": candidate_summaries,
        })

    observed_trade_day_count = sum(1 for row in rows if row["counts_as_trade_day"])
    required_additional_trade_days = max(0, 5 - observed_trade_day_count)
    latest = lambda pred: max((row["asof"] for row in rows if pred(row)), default="")
    current_blocker = ""
    recommended_next_route = "DNG15_DAILY_CHAIN_DASHBOARD_INTEGRATION"
    if latest(lambda row: row["classification"] == "RAW_READY_BUT_QLIB_PROVIDER_STALE"):
        current_blocker = "formal qlib provider/calendar has not advanced to latest raw-ready asof"
        recommended_next_route = "formal_qlib_provider_refresh_route_or_validated_canonical_bridge_route"
    elif required_additional_trade_days:
        current_blocker = "insufficient observed trade-day samples"
        recommended_next_route = "continue_daily_observation_or_safe_shadow_backfill"

    overlay = {
        "schema_version": "dng14.latest_status_chain_overlay.v1",
        "generated_at": now(),
        "latest_ready_chain_asof": latest(lambda row: row["classification"] == "READY_CHAIN"),
        "latest_raw_ready_asof": latest(lambda row: str(row["raw_status"]).startswith("READY")),
        "latest_provider_stale_asof": latest(lambda row: row["classification"] == "RAW_READY_BUT_QLIB_PROVIDER_STALE"),
        "latest_model_a_ready_asof": latest(lambda row: row["model_a_signal_status"] == "READY"),
        "latest_strategy_context_ready_asof": latest(lambda row: row["strategy_input_bundle_status"] == "READY"),
        "latest_readonly_context_ready_asof": latest(lambda row: row["readonly_source_context_status"] == "READY"),
        "current_blocker": current_blocker,
        "recommended_next_route": recommended_next_route,
        "observed_trade_day_count": observed_trade_day_count,
        "required_additional_trade_days": required_additional_trade_days,
        "forbidden_actions_all_false": not forbidden_violations,
        "forbidden_action_violations": forbidden_violations,
        "production_go": False,
        "publish_latest_authorized": False,
    }
    observation = {
        "schema_version": "dng14.multi_day_chain_observation.v1",
        "generated_at": now(),
        "source_root": rel(OPS_DIR),
        "classification_enum": sorted(CLASSIFICATIONS),
        "asof_count": len(rows),
        "candidate_job_count": sum(len(items) for items in by_asof.values()),
        "observed_trade_day_count": observed_trade_day_count,
        "required_additional_trade_days": required_additional_trade_days,
        "classification_counts": dict(sorted(classification_counts.items())),
        "forbidden_actions_all_false": not forbidden_violations,
        "sample_note": "Safe shadow/backfill jobs generated with --skip-finmind --skip-qlib are audit artifacts only; they are not real data fetches or production readiness.",
        "asof_observations": asof_entries,
        "overlay_path": rel(OVERLAY_JSON),
        "csv_path": rel(OBS_CSV),
    }
    return observation, rows, overlay


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Print a short JSON summary to stdout.")
    args = parser.parse_args()

    observation, rows, overlay = build_observation()
    write_json(OBS_JSON, observation)
    write_csv(OBS_CSV, rows)
    write_json(OVERLAY_JSON, overlay)
    if args.json:
        print(json.dumps({
            "observation_path": rel(OBS_JSON),
            "csv_path": rel(OBS_CSV),
            "overlay_path": rel(OVERLAY_JSON),
            "asof_count": observation["asof_count"],
            "observed_trade_day_count": observation["observed_trade_day_count"],
            "required_additional_trade_days": observation["required_additional_trade_days"],
            "latest_ready_chain_asof": overlay["latest_ready_chain_asof"],
            "latest_provider_stale_asof": overlay["latest_provider_stale_asof"],
            "recommended_next_route": overlay["recommended_next_route"],
        }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
