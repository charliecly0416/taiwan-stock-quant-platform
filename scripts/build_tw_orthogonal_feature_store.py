#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_ASOF = "2026-06-25"
FEATURE_SET_ID = "daily_orthogonal"

DAILY_LTR_DIR = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank"
YZ2_DIR = ROOT / "data_tw/artifacts/phase_yz/yz2_orthogonal_feature_package/2026-06-17"
SEGMENT_CACHE_DIR = ROOT / "data_tw/ops/daily_auto_update/finmind_segment_cache"
MONTHLY_REVENUE_HISTORICAL = (
    ROOT / "data_tw/experiments/archive/historical_research/decision_fundamental/phasef0b_monthly_revenue_normalized_pit.csv"
)

FEATURE_REQUIRED_FIELDS = [
    "feature_date",
    "instrument",
    "feature_name",
    "feature_value",
    "source_dataset",
    "source_path",
    "source_provider",
    "available_at",
    "pit_policy",
    "coverage_status",
]

FORBIDDEN_ACTION_FLAGS = {
    "real_data_fetch_triggered": False,
    "provider_refresh_triggered": False,
    "provider_publish_triggered": False,
    "qlib_accepted_latest_switched": False,
    "readonly_latest_published": False,
    "agent_prompt_published": False,
    "model_training_triggered": False,
    "model_inference_triggered": False,
    "strategy_replay_triggered": False,
    "broker_order_quick_trade_triggered": False,
    "target_position_or_weight_generated": False,
}

INSTITUTIONAL_FEATURES = [
    "foreign_net_buy",
    "investment_trust_net_buy",
    "dealer_net_buy",
    "institutional_total_net_buy",
    "foreign_net_buy_roll1",
    "foreign_net_buy_roll3",
    "foreign_net_buy_roll5",
    "foreign_net_buy_roll10",
    "investment_trust_net_buy_roll1",
    "investment_trust_net_buy_roll3",
    "investment_trust_net_buy_roll5",
    "investment_trust_net_buy_roll10",
    "dealer_net_buy_roll1",
    "dealer_net_buy_roll3",
    "dealer_net_buy_roll5",
    "dealer_net_buy_roll10",
    "institutional_total_net_buy_roll1",
    "institutional_total_net_buy_roll3",
    "institutional_total_net_buy_roll5",
    "institutional_total_net_buy_roll10",
    "institutional_total_net_buy_streak",
    "institutional_missing_flag",
    "institutional_delay_flag",
]

MARGIN_SHORT_FEATURES = [
    "margin_balance",
    "margin_balance_change",
    "short_balance",
    "short_balance_change",
    "margin_balance_change_roll1",
    "margin_balance_change_roll3",
    "margin_balance_change_roll5",
    "margin_balance_change_roll10",
    "short_balance_change_roll1",
    "short_balance_change_roll3",
    "short_balance_change_roll5",
    "short_balance_change_roll10",
    "margin_direction_proxy",
    "short_direction_proxy",
    "margin_short_divergence_proxy",
    "margin_short_missing_flag",
    "margin_short_delay_flag",
]

DATASET_FEATURES = {
    "institutional_flow": INSTITUTIONAL_FEATURES,
    "margin_short": MARGIN_SHORT_FEATURES,
}

REQUIRED_ORTHOGONAL_DATASETS = [
    "institutional_flow",
    "margin_short",
    "corporate_actions",
    "monthly_revenue",
    "valuation",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path | str) -> str:
    path_obj = Path(path)
    try:
        return str(path_obj.resolve().relative_to(ROOT.resolve()))
    except (ValueError, FileNotFoundError):
        return str(path)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def csv_header_and_count(path: Path) -> tuple[list[str], int]:
    if not path.exists():
        return [], 0
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return [], 0
        return header, sum(1 for _ in reader)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def non_empty(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def boolish_zero(value: Any) -> bool:
    if value is None:
        return False
    return str(value).strip() in {"0", "0.0", "False", "false", ""}


def source_provider_for(dataset_id: str, row: dict[str, str]) -> str:
    if dataset_id == "institutional_flow":
        return row.get("data_source") or "FinMind:TaiwanStockInstitutionalInvestorsBuySell"
    if dataset_id == "margin_short":
        return "FinMind:TaiwanStockMarginPurchaseShortSale"
    return "local_file"


def coverage_status_for(dataset_id: str, row: dict[str, str]) -> str:
    if dataset_id == "institutional_flow":
        if not boolish_zero(row.get("institutional_missing_flag")):
            return "PARTIAL_READY"
        if not boolish_zero(row.get("institutional_delay_flag")):
            return "PIT_DELAYED"
        return "READY"
    if dataset_id == "margin_short":
        if not boolish_zero(row.get("margin_short_missing_flag")):
            return "PARTIAL_READY"
        if not boolish_zero(row.get("margin_short_delay_flag")):
            return "PIT_DELAYED"
        return "READY"
    return "READY"


def build_long_features(asof: str, source_path: Path, out_path: Path) -> dict[str, Any]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    stats: dict[str, Any] = {
        dataset_id: {
            "feature_rows": 0,
            "source_rows_with_features": 0,
            "symbols": set(),
            "dates": set(),
            "available_ats": set(),
            "features": set(),
            "coverage_status_counter": Counter(),
        }
        for dataset_id in DATASET_FEATURES
    }
    skipped_rows_after_asof = 0

    with source_path.open("r", encoding="utf-8", newline="") as src, out_path.open(
        "w", encoding="utf-8", newline=""
    ) as dst:
        reader = csv.DictReader(src)
        writer = csv.DictWriter(dst, fieldnames=FEATURE_REQUIRED_FIELDS)
        writer.writeheader()
        for row in reader:
            feature_date = row.get("trade_date", "")
            instrument = row.get("symbol", "")
            available_at = row.get("available_at", "")
            if feature_date > asof:
                skipped_rows_after_asof += 1
                continue
            for dataset_id, feature_names in DATASET_FEATURES.items():
                wrote_for_row = False
                coverage_status = coverage_status_for(dataset_id, row)
                raw_snapshot_path = row.get("raw_snapshot_path") or rel(source_path)
                pit_policy = row.get("available_at_contract") or (
                    "point_in_time_by_available_at; consumers must filter available_at <= decision_asof"
                )
                for feature_name in feature_names:
                    value = row.get(feature_name)
                    if not non_empty(value):
                        continue
                    writer.writerow(
                        {
                            "feature_date": feature_date,
                            "instrument": instrument,
                            "feature_name": feature_name,
                            "feature_value": value,
                            "source_dataset": dataset_id,
                            "source_path": raw_snapshot_path,
                            "source_provider": source_provider_for(dataset_id, row),
                            "available_at": available_at,
                            "pit_policy": pit_policy,
                            "coverage_status": coverage_status,
                        }
                    )
                    stats[dataset_id]["feature_rows"] += 1
                    stats[dataset_id]["symbols"].add(instrument)
                    stats[dataset_id]["dates"].add(feature_date)
                    stats[dataset_id]["available_ats"].add(available_at)
                    stats[dataset_id]["features"].add(feature_name)
                    stats[dataset_id]["coverage_status_counter"][coverage_status] += 1
                    wrote_for_row = True
                if wrote_for_row:
                    stats[dataset_id]["source_rows_with_features"] += 1

    compact: dict[str, Any] = {}
    for dataset_id, value in stats.items():
        dates = sorted(value["dates"])
        available_ats = sorted(value["available_ats"])
        compact[dataset_id] = {
            "feature_rows": value["feature_rows"],
            "source_rows_with_features": value["source_rows_with_features"],
            "symbol_count": len(value["symbols"]),
            "date_min": dates[0] if dates else "",
            "date_max": dates[-1] if dates else "",
            "available_at_min": available_ats[0] if available_ats else "",
            "available_at_max": available_ats[-1] if available_ats else "",
            "feature_count": len(value["features"]),
            "features": sorted(value["features"]),
            "coverage_status_counter": dict(value["coverage_status_counter"]),
        }
    compact["skipped_rows_after_asof"] = skipped_rows_after_asof
    return compact


def load_refresh_status(asof: str) -> dict[str, Any]:
    return read_json(DAILY_LTR_DIR / f"latest_orthogonal_features_{asof}_refresh_status.json")


def load_segment_cache(segment: str) -> dict[str, Any]:
    candidates = sorted(SEGMENT_CACHE_DIR.glob(f"*_{segment}.json"))
    if not candidates:
        return {}
    return read_json(candidates[-1])


def parse_json_file(path: Path) -> dict[str, Any]:
    try:
        return read_json(path)
    except json.JSONDecodeError:
        return {}


def corporate_actions_stdout_summary(cache: dict[str, Any]) -> dict[str, Any]:
    stdout = ROOT / cache.get("stdout_path", "")
    payload = parse_json_file(stdout) if stdout.exists() else {}
    actions = payload.get("corporate_actions", {}) if isinstance(payload, dict) else {}
    return {
        "stdout_path": rel(stdout) if stdout.exists() else cache.get("stdout_path", ""),
        "row_count": int(actions.get("count") or 0),
        "symbol_count": len(actions.get("symbols") or []),
        "symbols_sample": (actions.get("symbols") or [])[:20],
        "date_min": "",
        "date_max": cache.get("asof", ""),
    }


def provider_status_rows(
    asof: str,
    feature_stats: dict[str, Any],
    refresh_status: dict[str, Any],
) -> list[dict[str, Any]]:
    raw_status_by_family = {
        row.get("feature_family"): row for row in refresh_status.get("raw_status", []) if isinstance(row, dict)
    }
    rows: list[dict[str, Any]] = []
    for dataset_id in ["institutional_flow", "margin_short"]:
        raw = raw_status_by_family.get(dataset_id, {})
        stats = feature_stats.get(dataset_id, {})
        rows.append(
            {
                "dataset_id": dataset_id,
                "provider": "FinMind",
                "source_max_date": raw.get("raw_trade_date_max") or stats.get("date_max", ""),
                "row_count": stats.get("source_rows_with_features", 0),
                "symbol_count": stats.get("symbol_count", 0),
                "status": "PARTIAL_READY",
                "status_reason": (
                    "Local research/controlled feature table is available and PIT fields exist, "
                    "but scope is top50/controlled, not a canonical full-universe provider store."
                ),
                "quota_or_permission_status": raw.get("db_error", "") or "local_raw_archive_available",
                "holiday_or_no_data_evidence": "",
                "requires_external_source_repair": False,
            }
        )

    corporate_cache = load_segment_cache("corporate_actions")
    corporate_summary = corporate_actions_stdout_summary(corporate_cache)
    rows.append(
        {
            "dataset_id": "corporate_actions",
            "provider": "FinMind",
            "source_max_date": corporate_cache.get("asof", ""),
            "row_count": corporate_summary["row_count"],
            "symbol_count": corporate_summary["symbol_count"],
            "status": "PARTIAL_READY" if corporate_cache.get("ok") else "MISSING",
            "status_reason": (
                "Local ops segment cache reports covered=true and archived corporate actions, "
                "but no normalized daily feature body was found for canonical long-form conversion."
            ),
            "quota_or_permission_status": corporate_cache.get("provider_error", "") or "covered_by_local_ops_cache",
            "holiday_or_no_data_evidence": "",
            "requires_external_source_repair": False,
        }
    )

    monthly_cache = load_segment_cache("monthly_revenue")
    monthly_header, monthly_rows = csv_header_and_count(MONTHLY_REVENUE_HISTORICAL)
    monthly_status = "BLOCKED_QUOTA" if monthly_cache.get("provider_error") else "MISSING"
    rows.append(
        {
            "dataset_id": "monthly_revenue",
            "provider": "FinMind",
            "source_max_date": monthly_cache.get("asof", ""),
            "row_count": monthly_rows,
            "symbol_count": 0,
            "status": monthly_status,
            "status_reason": (
                "Local historical PIT file has no data rows; latest ops segment cache is not covered."
            ),
            "quota_or_permission_status": monthly_cache.get("provider_error", "") or "missing_local_body",
            "holiday_or_no_data_evidence": "",
            "requires_external_source_repair": True,
        }
    )

    valuation_cache = load_segment_cache("valuation")
    valuation_status = "BLOCKED_QUOTA" if valuation_cache.get("provider_error") else "MISSING"
    rows.append(
        {
            "dataset_id": "valuation",
            "provider": "FinMind",
            "source_max_date": valuation_cache.get("asof", ""),
            "row_count": 0,
            "symbol_count": 0,
            "status": valuation_status,
            "status_reason": "No local normalized valuation body was found; latest ops segment cache is not covered.",
            "quota_or_permission_status": valuation_cache.get("provider_error", "") or "missing_local_body",
            "holiday_or_no_data_evidence": "",
            "requires_external_source_repair": True,
        }
    )

    yz2_manifest = read_json(YZ2_DIR / "manifest.json")
    rows.append(
        {
            "dataset_id": "yz2_orthogonal_feature_package",
            "provider": "local_artifact",
            "source_max_date": yz2_manifest.get("signal_asof", ""),
            "row_count": yz2_manifest.get("row_count", 0),
            "symbol_count": len(yz2_manifest.get("covered_symbols", [])),
            "status": "LEGACY_RESEARCH_ONLY",
            "status_reason": "Existing YZ2 top50 package is retained as lineage evidence only, not as fresh canonical DNG3 source.",
            "quota_or_permission_status": "not_applicable",
            "holiday_or_no_data_evidence": "",
            "requires_external_source_repair": False,
        }
    )
    return rows


def write_provider_status(path: Path, rows: list[dict[str, Any]]) -> None:
    write_json(
        path,
        {
            "schema_version": "v1.dng3.provider_status",
            "generated_at": utc_now(),
            "datasets": rows,
            "forbidden_action_flags": FORBIDDEN_ACTION_FLAGS,
        },
    )


def write_coverage_audit(path: Path, feature_stats: dict[str, Any], provider_rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "dataset_id",
        "status",
        "coverage_status",
        "date_min",
        "date_max",
        "available_at_min",
        "available_at_max",
        "row_count",
        "feature_row_count",
        "symbol_count",
        "feature_count",
        "source_path",
        "status_reason",
    ]
    provider_by_dataset = {row["dataset_id"]: row for row in provider_rows}
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for dataset_id in REQUIRED_ORTHOGONAL_DATASETS + ["yz2_orthogonal_feature_package"]:
            stats = feature_stats.get(dataset_id, {})
            provider = provider_by_dataset.get(dataset_id, {})
            writer.writerow(
                {
                    "dataset_id": dataset_id,
                    "status": provider.get("status", "MISSING"),
                    "coverage_status": "READY" if stats.get("feature_rows", 0) else provider.get("status", "MISSING"),
                    "date_min": stats.get("date_min", ""),
                    "date_max": stats.get("date_max", "") or provider.get("source_max_date", ""),
                    "available_at_min": stats.get("available_at_min", ""),
                    "available_at_max": stats.get("available_at_max", ""),
                    "row_count": provider.get("row_count", 0),
                    "feature_row_count": stats.get("feature_rows", 0),
                    "symbol_count": stats.get("symbol_count", "") or provider.get("symbol_count", 0),
                    "feature_count": stats.get("feature_count", 0),
                    "source_path": provider_source_path(dataset_id),
                    "status_reason": provider.get("status_reason", ""),
                }
            )


def provider_source_path(dataset_id: str) -> str:
    if dataset_id in {"institutional_flow", "margin_short"}:
        return rel(DAILY_LTR_DIR)
    if dataset_id == "corporate_actions":
        return rel(load_segment_cache("corporate_actions").get("stdout_path", ""))
    if dataset_id == "monthly_revenue":
        return rel(MONTHLY_REVENUE_HISTORICAL)
    if dataset_id == "valuation":
        return rel(load_segment_cache("valuation").get("stdout_path", ""))
    if dataset_id == "yz2_orthogonal_feature_package":
        return rel(YZ2_DIR)
    return ""


def write_pit_audit(path: Path, asof: str, feature_stats: dict[str, Any]) -> dict[str, Any]:
    counters: dict[str, Counter] = defaultdict(Counter)
    feature_path = path.parent / "features.csv"
    with feature_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            dataset_id = row.get("source_dataset", "")
            feature_date = row.get("feature_date", "")
            available_at = row.get("available_at", "")
            counters[dataset_id]["rows_checked"] += 1
            if not available_at:
                counters[dataset_id]["missing_available_at"] += 1
            if available_at and feature_date and available_at < feature_date:
                counters[dataset_id]["available_before_feature_date"] += 1
            if available_at and available_at > asof:
                counters[dataset_id]["available_after_asof"] += 1

    fieldnames = [
        "dataset_id",
        "rows_checked",
        "pit_violation_count",
        "available_after_asof_count",
        "min_available_at",
        "max_available_at",
        "pit_policy",
        "status",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for dataset_id in REQUIRED_ORTHOGONAL_DATASETS:
            stats = feature_stats.get(dataset_id, {})
            counter = counters[dataset_id]
            violation_count = counter["missing_available_at"] + counter["available_before_feature_date"]
            writer.writerow(
                {
                    "dataset_id": dataset_id,
                    "rows_checked": counter["rows_checked"],
                    "pit_violation_count": violation_count,
                    "available_after_asof_count": counter["available_after_asof"],
                    "min_available_at": stats.get("available_at_min", ""),
                    "max_available_at": stats.get("available_at_max", ""),
                    "pit_policy": "point_in_time_by_available_at; no future labels; consumers filter available_at <= decision_asof",
                    "status": "READY" if counter["rows_checked"] and violation_count == 0 else "MISSING_OR_BLOCKED",
                }
            )
    return {dataset_id: dict(counter) for dataset_id, counter in counters.items()}


def build_source_data_audit(
    asof: str,
    run_id: str,
    source_path: Path,
    feature_stats: dict[str, Any],
    provider_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    source_header, source_rows = csv_header_and_count(source_path)
    yz2_manifest = read_json(YZ2_DIR / "manifest.json")
    corporate_cache = load_segment_cache("corporate_actions")
    monthly_cache = load_segment_cache("monthly_revenue")
    valuation_cache = load_segment_cache("valuation")
    return {
        "schema_version": "v1.dng3.source_data_audit",
        "generated_at": utc_now(),
        "run_id": run_id,
        "asof": asof,
        "selected_local_sources": [
            {
                "dataset_ids": ["institutional_flow", "margin_short"],
                "path": rel(source_path),
                "row_count": source_rows,
                "column_count": len(source_header),
                "checksum": sha256_file(source_path) if source_path.exists() else "",
                "status": "PARTIAL_READY",
                "source_role": "primary local wide feature evidence converted to canonical long-form",
            },
            {
                "dataset_ids": ["yz2_orthogonal_feature_package"],
                "path": rel(YZ2_DIR),
                "row_count": yz2_manifest.get("row_count", 0),
                "column_count": yz2_manifest.get("feature_schema_column_count", 0),
                "status": "LEGACY_RESEARCH_ONLY",
                "source_role": "lineage and historical top50 coverage evidence only",
            },
            {
                "dataset_ids": ["corporate_actions"],
                "path": rel(corporate_cache.get("stdout_path", "")),
                "status": "PARTIAL_READY" if corporate_cache.get("ok") else "MISSING",
                "source_role": "ops segment cache evidence; no daily feature body converted",
            },
            {
                "dataset_ids": ["monthly_revenue"],
                "path": rel(MONTHLY_REVENUE_HISTORICAL),
                "status": "BLOCKED_QUOTA" if monthly_cache.get("provider_error") else "MISSING",
                "source_role": "historical file/header and ops cache blocker evidence only",
            },
            {
                "dataset_ids": ["valuation"],
                "path": rel(valuation_cache.get("stdout_path", "")),
                "status": "BLOCKED_QUOTA" if valuation_cache.get("provider_error") else "MISSING",
                "source_role": "ops cache blocker evidence only",
            },
        ],
        "feature_stats": feature_stats,
        "provider_status_summary": provider_rows,
        "forbidden_action_flags": FORBIDDEN_ACTION_FLAGS,
    }


def write_schema(path: Path) -> None:
    write_json(
        path,
        {
            "schema_version": "v1.dng3.orthogonal_feature_store.schema",
            "artifact_type": "CanonicalOrthogonalFeatureStore",
            "format": "csv",
            "required_fields": FEATURE_REQUIRED_FIELDS,
            "field_definitions": {
                "feature_date": "Source economic/trading date for the feature value.",
                "instrument": "Taiwan stock instrument id, e.g. TW2330.",
                "feature_name": "Canonical long-form feature identifier.",
                "feature_value": "String-encoded numeric or categorical feature value.",
                "source_dataset": "Origin dataset family.",
                "source_path": "Local source artifact path; no network fetch is triggered.",
                "source_provider": "Provider or local artifact label.",
                "available_at": "Earliest date the value may be visible to a PIT consumer.",
                "pit_policy": "Point-in-time availability rule.",
                "coverage_status": "READY, PARTIAL_READY, PIT_DELAYED, MISSING, or BLOCKED status for this row.",
            },
            "forbidden_fields": [
                "target_position",
                "target_weight",
                "order_qty",
                "broker_order_id",
                "future_return_*",
                "forward_return_*",
                "label_*",
                "strategy_action",
            ],
        },
    )


def write_lineage(
    path: Path,
    asof: str,
    run_id: str,
    source_path: Path,
    readiness_path: Path,
) -> None:
    write_json(
        path,
        {
            "schema_version": "v1.dng3.orthogonal_feature_store.lineage",
            "artifact_type": "CanonicalOrthogonalFeatureStoreLineage",
            "run_id": run_id,
            "asof": asof,
            "lineage_type": "local_canonicalization_no_fetch",
            "transformations": [
                {
                    "step": "wide_to_long_feature_canonicalization",
                    "input": rel(source_path),
                    "output": f"data_tw/canonical/orthogonal_feature_store/{FEATURE_SET_ID}/{run_id}/features.csv",
                    "notes": "Only institutional_flow and margin_short feature columns are converted; qlib score/rank fields are excluded.",
                },
                {
                    "step": "local_provider_status_audit",
                    "input": "data_tw/ops/daily_auto_update/finmind_segment_cache/*.json",
                    "output": f"data_tw/canonical/orthogonal_feature_store/{FEATURE_SET_ID}/{run_id}/provider_status.json",
                    "notes": "Ops cache files are read as evidence only; no provider refresh is triggered.",
                },
            ],
            "readiness_matrix": rel(readiness_path),
            "forbidden_action_flags": FORBIDDEN_ACTION_FLAGS,
            "no_provider_publish": True,
            "no_accepted_latest_switch": True,
            "readonly_publish": False,
            "agent_prompt_publish": False,
        },
    )


def readiness_dependencies(
    asof: str,
    run_id: str,
    feature_stats: dict[str, Any],
    provider_rows: list[dict[str, Any]],
    out_dir: Path,
) -> tuple[list[dict[str, Any]], list[str]]:
    provider_by_dataset = {row["dataset_id"]: row for row in provider_rows}
    blockers: list[str] = []
    dependencies: list[dict[str, Any]] = []
    for dataset_id in REQUIRED_ORTHOGONAL_DATASETS:
        stats = feature_stats.get(dataset_id, {})
        provider = provider_by_dataset.get(dataset_id, {})
        has_features = stats.get("feature_rows", 0) > 0
        provider_status = provider.get("status", "MISSING")
        can_continue = bool(has_features and provider_status in {"READY", "PARTIAL_READY"})
        blocker_reason = ""
        if not can_continue:
            blocker_reason = provider.get("status_reason", "No canonical feature rows were produced.")
            blockers.append(dataset_id)
        dependencies.append(
            {
                "route_id": "orthogonal_feature_store",
                "dependency_name": dataset_id,
                "required_dataset_id": dataset_id,
                "required_layer": "canonical_orthogonal_feature_store",
                "required_date_max": asof,
                "required_fields": FEATURE_REQUIRED_FIELDS,
                "required_pit_policy": "available_at present; no future label fields; consumers filter available_at <= decision_asof",
                "required_symbols_scope": "declared local evidence scope",
                "asof": asof,
                "source_artifact": rel(out_dir / "features.csv") if has_features else provider_source_path(dataset_id),
                "catalog_status": provider_status,
                "schema_status": "READY" if has_features else "MISSING_OR_BLOCKED",
                "coverage_status": "READY" if has_features else provider_status,
                "pit_status": "READY" if has_features else "MISSING_OR_BLOCKED",
                "latest_status": "canonical artifact only; not published latest",
                "can_continue": can_continue,
                "blocker_reason": blocker_reason,
                "repair_recommendation": (
                    "" if can_continue else "Add local normalized/PIT-safe source body or resolve provider quota/permission outside DNG3."
                ),
            }
        )
    return dependencies, blockers


def write_readiness_matrix(
    path: Path,
    asof: str,
    run_id: str,
    feature_stats: dict[str, Any],
    provider_rows: list[dict[str, Any]],
    out_dir: Path,
) -> dict[str, Any]:
    dependencies, blockers = readiness_dependencies(asof, run_id, feature_stats, provider_rows, out_dir)
    can_continue_to_model_b_ltr = not blockers
    readiness = {
        "schema_version": "v1.dng3.orthogonal_feature_store.readiness",
        "route_id": "orthogonal_feature_store",
        "run_id": run_id,
        "asof": asof,
        "generated_at": utc_now(),
        "status": "PARTIAL_READY" if blockers else "READY",
        "status_reason": (
            "Canonical institutional_flow and margin_short features were produced, but one or more required "
            "orthogonal families are missing or provider-blocked."
            if blockers
            else "All required DNG3 orthogonal families have canonical feature rows."
        ),
        "can_continue": False,
        "can_continue_to_model_b_ltr": can_continue_to_model_b_ltr,
        "can_continue_to_model_score": True,
        "model_score_scope": "qlib_only_score_not_blocked_by_DNG3; orthogonal/LTR score remains blocked when can_continue_to_model_b_ltr=false",
        "can_continue_to_dng4": True,
        "can_continue_to_replay": False,
        "can_continue_to_shadow_execution": False,
        "blocking_datasets": blockers,
        "allowed_fallbacks": [
            "qlib_only_score_path_may_continue_without_DNG3_orthogonal_features",
            "DNG4_input_bundle_contract_design_may_continue_with_declared_blockers",
        ],
        "dependencies": dependencies,
        "external_source_repair_required": any(row.get("requires_external_source_repair") for row in provider_rows),
        "forbidden_action_flags": FORBIDDEN_ACTION_FLAGS,
        "source_paths": {
            "daily_ltr_wide_features": rel(DAILY_LTR_DIR / f"latest_orthogonal_features_{asof}.csv"),
            "yz2_orthogonal_feature_package": rel(YZ2_DIR),
            "provider_segment_cache_dir": rel(SEGMENT_CACHE_DIR),
        },
    }
    write_json(path, readiness)
    return readiness


def write_manifest(
    path: Path,
    asof: str,
    run_id: str,
    feature_stats: dict[str, Any],
    provider_rows: list[dict[str, Any]],
    readiness: dict[str, Any],
) -> dict[str, Any]:
    feature_dates = sorted(
        date
        for dataset_id in DATASET_FEATURES
        for date in [feature_stats.get(dataset_id, {}).get("date_min"), feature_stats.get(dataset_id, {}).get("date_max")]
        if date
    )
    symbols = max((feature_stats.get(dataset_id, {}).get("symbol_count", 0) for dataset_id in DATASET_FEATURES), default=0)
    feature_row_count = sum(feature_stats.get(dataset_id, {}).get("feature_rows", 0) for dataset_id in DATASET_FEATURES)
    source_row_count = sum(feature_stats.get(dataset_id, {}).get("source_rows_with_features", 0) for dataset_id in DATASET_FEATURES)
    manifest = {
        "schema_version": "v1.dng3.orthogonal_feature_store.manifest",
        "artifact_type": "CanonicalOrthogonalFeatureStore",
        "feature_set_id": FEATURE_SET_ID,
        "run_id": run_id,
        "asof": asof,
        "created_at": utc_now(),
        "status": readiness["status"],
        "status_reason": readiness["status_reason"],
        "date_min": feature_dates[0] if feature_dates else "",
        "date_max": feature_dates[-1] if feature_dates else "",
        "row_count": feature_row_count,
        "source_row_count": source_row_count,
        "symbol_count": symbols,
        "dataset_status": {row["dataset_id"]: row["status"] for row in provider_rows},
        "required_datasets": REQUIRED_ORTHOGONAL_DATASETS,
        "blocking_datasets": readiness["blocking_datasets"],
        "can_continue_to_model_b_ltr": readiness["can_continue_to_model_b_ltr"],
        "can_continue_to_model_score": readiness["can_continue_to_model_score"],
        "can_continue_to_dng4": readiness["can_continue_to_dng4"],
        "files": {
            "features": "features.csv",
            "schema": "schema.json",
            "source_data_audit": "source_data_audit.json",
            "pit_audit": "pit_audit.csv",
            "coverage_audit": "coverage_audit.csv",
            "provider_status": "provider_status.json",
            "lineage": "lineage.json",
        },
        "available_at_policy": "point_in_time_by_available_at; consumers must filter available_at <= decision_asof",
        "pit_policy": "no future labels or returns; source values are local evidence only",
        "canonicality": "canonical_store_builder_output_no_publish",
        "no_provider_publish": True,
        "no_accepted_latest_switch": True,
        "readonly_only": True,
        "forbidden_action_flags": FORBIDDEN_ACTION_FLAGS,
    }
    write_json(path, manifest)
    return manifest


def write_report(path: Path, asof: str, run_id: str, readiness: dict[str, Any], provider_rows: list[dict[str, Any]]) -> None:
    provider_lines = "\n".join(
        f"| {row['dataset_id']} | {row['status']} | {row['row_count']} | {row['symbol_count']} | {row['status_reason']} |"
        for row in provider_rows
    )
    text = f"""# DNG3 正交数据 Canonical Store 执行报告

生成时间：{utc_now()}

执行者：DNG3 Executor

## 1. 结论

- run_id：`{run_id}`
- asof：`{asof}`
- canonical store：`data_tw/canonical/orthogonal_feature_store/{FEATURE_SET_ID}/{run_id}`
- can_continue_to_model_b_ltr：`{str(readiness['can_continue_to_model_b_ltr']).lower()}`
- can_continue_to_model_score：`{str(readiness['can_continue_to_model_score']).lower()}`，仅表示 qlib-only score 路线不被 DNG3 阻断。
- can_continue_to_dng4：`{str(readiness['can_continue_to_dng4']).lower()}`
- blocking_datasets：`{', '.join(readiness['blocking_datasets']) if readiness['blocking_datasets'] else ''}`

## 2. 本地来源与状态

| dataset | status | rows | symbols | reason |
| --- | ---: | ---: | ---: | --- |
{provider_lines}

## 3. 产物

- `manifest.json`
- `features.csv`
- `schema.json`
- `source_data_audit.json`
- `pit_audit.csv`
- `coverage_audit.csv`
- `provider_status.json`
- `lineage.json`
- `data_tw/catalog/readiness_matrix/{asof}/orthogonal_feature_store.json`
- `data_tw/catalog/dng3_orthogonal_feature_store_validation.json`（validator 运行后写入）

## 4. LTR Model B 判断

当前本地 canonical feature body 只覆盖 `institutional_flow` 与 `margin_short`。`corporate_actions` 只有 ops covered/archive 证据但没有可转换日频特征体；`monthly_revenue` 与 `valuation` 在本地 ops segment cache 中记录 quota/payment blocker。因此 `can_continue_to_model_b_ltr=false`。

## 5. DNG4 判断

DNG4 如果只做 input bundle contract / readiness contract，可继续，必须携带上述 blocker；不得把本产物解释为 LTR Model B ready。

## 6. Validator 输出

尚未运行 validator。请执行：

```bash
python scripts/validate_tw_orthogonal_feature_store.py --run-id {run_id} --asof {asof} --json
```

## 7. Forbidden Action Audit

本次 builder 只读取本地文件并写 canonical/catalog/report 产物。未触发真实抓数、provider refresh/publish、accepted latest switch、readonly/Agent publish、训练、推理、score、replay、broker/order/quick-trade、target_position/target_weight。
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build DNG3 canonical TW orthogonal feature store from local evidence only.")
    parser.add_argument("--asof", default=DEFAULT_ASOF)
    parser.add_argument("--run-id", default="")
    args = parser.parse_args()

    asof = args.asof
    run_id = args.run_id or f"dng3_orthogonal_feature_store_{asof.replace('-', '')}"
    source_path = DAILY_LTR_DIR / f"latest_orthogonal_features_{asof}.csv"
    if not source_path.exists():
        raise SystemExit(f"missing local source file: {rel(source_path)}")

    out_dir = ROOT / "data_tw/canonical/orthogonal_feature_store" / FEATURE_SET_ID / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    readiness_path = ROOT / "data_tw/catalog/readiness_matrix" / asof / "orthogonal_feature_store.json"

    feature_stats = build_long_features(asof, source_path, out_dir / "features.csv")
    refresh_status = load_refresh_status(asof)
    provider_rows = provider_status_rows(asof, feature_stats, refresh_status)

    write_schema(out_dir / "schema.json")
    write_provider_status(out_dir / "provider_status.json", provider_rows)
    write_coverage_audit(out_dir / "coverage_audit.csv", feature_stats, provider_rows)
    write_pit_audit(out_dir / "pit_audit.csv", asof, feature_stats)
    source_audit = build_source_data_audit(asof, run_id, source_path, feature_stats, provider_rows)
    write_json(out_dir / "source_data_audit.json", source_audit)

    readiness = write_readiness_matrix(readiness_path, asof, run_id, feature_stats, provider_rows, out_dir)
    write_lineage(out_dir / "lineage.json", asof, run_id, source_path, readiness_path)
    manifest = write_manifest(out_dir / "manifest.json", asof, run_id, feature_stats, provider_rows, readiness)
    write_report(
        ROOT / "docs/tw_data_governance/DNG3_ORTHOGONAL_DATA_STORE_EXECUTION_REPORT_CN.md",
        asof,
        run_id,
        readiness,
        provider_rows,
    )

    print(
        json.dumps(
            {
                "ok": True,
                "run_id": run_id,
                "asof": asof,
                "output_dir": rel(out_dir),
                "row_count": manifest["row_count"],
                "status": manifest["status"],
                "blocking_datasets": manifest["blocking_datasets"],
                "can_continue_to_model_b_ltr": manifest["can_continue_to_model_b_ltr"],
                "can_continue_to_dng4": manifest["can_continue_to_dng4"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
