#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOG_DIR = ROOT / "data_tw/catalog"
OPS_ROOT = ROOT / "data_tw/ops/daily_auto_update"

DEFAULT_OUTPUT = CATALOG_DIR / "daily_readiness_dashboard.json"

LATEST_CONCEPTS = [
    "provider_raw_latest",
    "normalized_latest",
    "price_store_latest",
    "feature_store_latest",
    "qlib_accepted_latest",
    "model_signal_latest",
    "readonly_snapshot_latest",
    "agent_prompt_latest",
]

FORBIDDEN_ACTION_KEYS = [
    "real_data_fetch_triggered",
    "provider_refresh_triggered",
    "provider_publish_triggered",
    "qlib_accepted_latest_switched",
    "readonly_latest_published",
    "agent_prompt_published",
    "model_training_triggered",
    "model_inference_triggered",
    "model_score_generation_triggered",
    "strategy_replay_triggered",
    "replay_result_nav_generated",
    "broker_order_quick_trade_triggered",
    "target_position_or_weight_generated",
]

BLOCKING_STATUSES = {
    "MISSING",
    "STALE",
    "BLOCKED_PROVIDER",
    "BLOCKED_SCHEMA",
    "BLOCKED_PIT",
    "BLOCKED_COVERAGE",
    "BLOCKED_VALIDATOR",
    "BLOCKED_QUOTA",
    "BLOCK",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def resolve(path_text: str | Path) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def latest_job_path() -> Path | None:
    jobs = [path for path in OPS_ROOT.glob("daily_tw_stock_auto_update_*/job.json") if path.is_file()]
    if not jobs:
        return None
    return max(jobs, key=lambda path: path.stat().st_mtime)


def compact_latest(item: Any, *, concept: str = "") -> dict[str, Any]:
    if not isinstance(item, dict):
        item = {}
    return {
        "latest_concept": concept,
        "asof": str(item.get("asof") or ""),
        "status": str(item.get("status") or "MISSING"),
        "path": str(item.get("path") or ""),
        "target_path": str(item.get("target_path") or ""),
        "run_id": str(item.get("run_id") or ""),
        "status_reason": str(item.get("status_reason") or ""),
    }


def latest_by_dataset(catalog: dict[str, Any], concept: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for entry in catalog.get("entries", []) or []:
        if not isinstance(entry, dict) or entry.get("latest_concept") != concept:
            continue
        dataset_id = str(entry.get("dataset_id") or entry.get("layer") or "unknown")
        out[dataset_id] = {
            "dataset_id": dataset_id,
            "layer": str(entry.get("layer") or ""),
            "asof": str(entry.get("asof") or ""),
            "date_max": str(entry.get("date_max") or ""),
            "status": str(entry.get("status") or ""),
            "path": str(entry.get("path") or ""),
            "status_reason": str(entry.get("status_reason") or ""),
        }
    return dict(sorted(out.items()))


def model_signal_latest_by_model(catalog: dict[str, Any], latest_status: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for entry in catalog.get("entries", []) or []:
        if not isinstance(entry, dict):
            continue
        if entry.get("latest_concept") != "model_signal_latest" and entry.get("layer") != "model_signal":
            continue
        key = str(entry.get("dataset_id") or entry.get("source_run_id") or "model_signal")
        out[key] = {
            "model_id": key,
            "asof": str(entry.get("asof") or ""),
            "status": str(entry.get("status") or ""),
            "path": str(entry.get("path") or ""),
            "status_reason": str(entry.get("status_reason") or ""),
            "latest_concept": str(entry.get("latest_concept") or "model_signal_latest"),
        }

    latest = (latest_status.get("latest_by_concept") or {}).get("model_signal_latest") or {}
    if isinstance(latest, dict):
        out.setdefault("latest_status_primary", compact_latest(latest, concept="model_signal_latest"))
        for idx, candidate in enumerate(latest.get("candidates") or []):
            if isinstance(candidate, dict):
                key = str(candidate.get("run_id") or candidate.get("target_path") or candidate.get("path") or f"candidate_{idx}")
                out.setdefault(key, compact_latest(candidate, concept="model_signal_latest"))
    return dict(sorted(out.items()))


def dependency_blockers(dependencies: list[Any]) -> list[str]:
    blockers: list[str] = []
    for dep in dependencies:
        if not isinstance(dep, dict):
            continue
        dep_name = str(dep.get("dependency_name") or dep.get("dataset_id") or "dependency")
        status_values = [
            str(dep.get("gate_status") or ""),
            str(dep.get("catalog_status") or ""),
            str(dep.get("coverage_status") or ""),
            str(dep.get("schema_status") or ""),
            str(dep.get("pit_status") or ""),
        ]
        reason = str(dep.get("blocker_reason") or "")
        messages = dep.get("messages") if isinstance(dep.get("messages"), list) else []
        if dep.get("can_continue") is False or any(value in BLOCKING_STATUSES for value in status_values) or reason or messages:
            details = reason or "; ".join(str(message) for message in messages if message)
            blockers.append(f"{dep_name}: {details or 'blocked_or_not_ready'}")
    return blockers


def summarize_price_market(price_matrix: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    deps = price_matrix.get("dependencies") if isinstance(price_matrix.get("dependencies"), list) else []
    price_deps = [dep for dep in deps if isinstance(dep, dict) and "price" in str(dep.get("dependency_name") or "").lower()]
    market_deps = [
        dep
        for dep in deps
        if isinstance(dep, dict)
        and any(token in str(dep.get("dependency_name") or "").lower() for token in ["twii", "calendar", "market"])
    ]
    price_blockers = dependency_blockers(price_deps)
    market_blockers = dependency_blockers(market_deps)
    price = {
        "asof": str(price_matrix.get("asof") or ""),
        "status": "PARTIAL_READY" if price_blockers or not price_matrix.get("can_continue_to_replay") else "READY",
        "can_continue_to_model_score": bool(price_matrix.get("can_continue_to_model_score")),
        "can_continue_to_replay": bool(price_matrix.get("can_continue_to_replay")),
        "production_ready": False,
        "blockers": price_blockers,
        "source": rel(CATALOG_DIR / "readiness_matrix/2026-06-25/price_market_calendar.json"),
    }
    market = {
        "asof": str(price_matrix.get("asof") or ""),
        "status": "PARTIAL_READY" if market_blockers or not price_matrix.get("can_continue_to_shadow_execution") else "READY",
        "can_continue_to_model_score": bool(price_matrix.get("can_continue_to_model_score")),
        "can_continue_to_shadow_execution": bool(price_matrix.get("can_continue_to_shadow_execution")),
        "production_ready": False,
        "blockers": market_blockers,
        "source": rel(CATALOG_DIR / "readiness_matrix/2026-06-25/price_market_calendar.json"),
    }
    return price, market


def summarize_orthogonal(matrix: dict[str, Any]) -> dict[str, Any]:
    deps = matrix.get("dependencies") if isinstance(matrix.get("dependencies"), list) else []
    blockers = dependency_blockers(deps)
    return {
        "asof": str(matrix.get("asof") or ""),
        "status": "BLOCKED_FOR_MODEL_B_LTR" if not matrix.get("can_continue_to_model_b_ltr") else "READY",
        "can_continue_to_model_score": bool(matrix.get("can_continue_to_model_score")),
        "can_continue_to_model_b_ltr": bool(matrix.get("can_continue_to_model_b_ltr")),
        "can_continue_to_replay": bool(matrix.get("can_continue_to_replay")),
        "production_ready": False,
        "blocking_datasets": matrix.get("blocking_datasets") if isinstance(matrix.get("blocking_datasets"), list) else [],
        "allowed_fallbacks": matrix.get("allowed_fallbacks") if isinstance(matrix.get("allowed_fallbacks"), list) else [],
        "blockers": blockers,
        "source": rel(CATALOG_DIR / "readiness_matrix/2026-06-25/orthogonal_feature_store.json"),
    }


def summarize_bundle(validation: dict[str, Any]) -> dict[str, Any]:
    strategy = validation.get("strategy_input_bundle") if isinstance(validation.get("strategy_input_bundle"), dict) else {}
    replay = validation.get("replay_input_bundle") if isinstance(validation.get("replay_input_bundle"), dict) else {}
    status = str(validation.get("status") or strategy.get("status") or replay.get("status") or "MISSING")
    blockers = []
    for label, payload in (("strategy_input_bundle", strategy), ("replay_input_bundle", replay)):
        partial = str(payload.get("partial_reason") or "")
        if partial:
            blockers.append(f"{label}: {partial}")
        for warning in payload.get("warnings") or []:
            blockers.append(f"{label}: {warning}")
    return {
        "asof": str(strategy.get("asof") or replay.get("asof") or ""),
        "status": status,
        "strategy_input_bundle_status": str(strategy.get("status") or "MISSING"),
        "replay_input_bundle_status": str(replay.get("status") or "MISSING"),
        "model_b_ltr_ready": bool(strategy.get("model_b_ltr_ready")),
        "not_replay_result": bool(replay.get("not_replay_result", True)),
        "production_ready": False,
        "blockers": blockers,
        "source": rel(CATALOG_DIR / "dng4_input_bundle_validation.json"),
    }


def summarize_route_dependency(validation: dict[str, Any]) -> dict[str, Any]:
    validations = validation.get("validations") if isinstance(validation.get("validations"), dict) else {}
    routes: dict[str, Any] = {}
    blockers: list[str] = []
    for route_id, payload in validations.items():
        if not isinstance(payload, dict):
            continue
        route_blockers = [str(item) for item in payload.get("gate_blockers") or [] if item]
        routes[str(route_id)] = {
            "asof": str(payload.get("asof") or ""),
            "gate_result": str(payload.get("gate_result") or ""),
            "gate_pass": bool(payload.get("gate_pass")),
            "validation_ok": bool(payload.get("validation_ok")),
            "production_ready": False,
            "blockers": route_blockers,
        }
        blockers.extend(f"{route_id}: {item}" for item in route_blockers)
    summary = validation.get("summary") if isinstance(validation.get("summary"), dict) else {}
    return {
        "status": "BLOCK" if int(summary.get("block_count") or 0) else ("PARTIAL" if int(summary.get("partial_count") or 0) else "PASS"),
        "all_gate_pass": bool(validation.get("all_gate_pass")),
        "production_ready": False,
        "summary": summary,
        "routes": routes,
        "blockers": blockers,
        "source": rel(CATALOG_DIR / "dng5_route_dependency_validation.json"),
    }


def collect_source_forbidden_flags(*sources: dict[str, Any]) -> dict[str, bool]:
    out = {key: False for key in FORBIDDEN_ACTION_KEYS}
    legacy_to_extended = {
        "model_score_generated": "model_score_generation_triggered",
        "replay_result_nav_generated": "replay_result_nav_generated",
    }
    for source in sources:
        candidates = [
            source.get("forbidden_action_flags"),
            (source.get("forbidden_action_audit") or {}).get("actions") if isinstance(source.get("forbidden_action_audit"), dict) else None,
        ]
        for flags in candidates:
            if not isinstance(flags, dict):
                continue
            for key, value in flags.items():
                mapped = legacy_to_extended.get(str(key), str(key))
                if mapped in out and value is True:
                    out[mapped] = True
    return out


def provider_quota_from_job(job: dict[str, Any]) -> dict[str, Any]:
    finmind = job.get("finmind_update") if isinstance(job.get("finmind_update"), dict) else {}
    quota_control = finmind.get("quota_scope_control") if isinstance(finmind.get("quota_scope_control"), dict) else {}
    batch = job.get("finmind_orthogonal_batch_update") if isinstance(job.get("finmind_orthogonal_batch_update"), dict) else {}
    batch_summary = batch.get("summary") if isinstance(batch.get("summary"), dict) else {}
    status = str(job.get("finmind_orthogonal_batch_status") or batch_summary.get("status") or "")
    if not status and not job.get("finmind_update_triggered"):
        status = "not_attempted_by_current_safe_status_run"
    return {
        "status": status or "unknown",
        "finmind_update_triggered": bool(job.get("finmind_update_triggered")),
        "finmind_orthogonal_batch_update_triggered": bool(job.get("finmind_orthogonal_batch_update_triggered")),
        "last_provider_error": str(batch_summary.get("last_provider_error") or ""),
        "cooldown_until": str(batch_summary.get("cooldown_until") or ""),
        "next_retry_hint": str(batch_summary.get("next_retry_hint") or ""),
        "quota_scope_control": quota_control,
    }


def holiday_from_job(job: dict[str, Any]) -> dict[str, Any]:
    status = str(job.get("status") or "")
    if status == "weekend_no_pending_wait":
        return {"status": "non_trading_day_or_weekend", "holiday_name": "weekend", "source": "latest_daily_auto_job"}
    if status == "today_data_window_wait":
        return {"status": "pending_data_window", "holiday_name": "", "source": "latest_daily_auto_job"}
    accounting_path = ((job.get("daily_full_capture_accounting") or {}).get("json_path") if isinstance(job.get("daily_full_capture_accounting"), dict) else "")
    accounting = read_json(resolve(accounting_path)) if accounting_path else {}
    rows = accounting.get("rows") if isinstance(accounting.get("rows"), list) else []
    for row in rows:
        if isinstance(row, dict) and row.get("dataset_category") == "schema_coverage_holiday_pending_evidence":
            return {
                "status": str(row.get("market_calendar_status") or "unknown"),
                "holiday_name": str(row.get("holiday_name") or ""),
                "source": accounting_path,
            }
    return {"status": "unknown", "holiday_name": "", "source": "latest_daily_auto_job"}


def build_dashboard(args: argparse.Namespace) -> dict[str, Any]:
    catalog_path = resolve(args.catalog)
    latest_status_path = resolve(args.latest_status)
    route_validation_path = resolve(args.route_validation)
    dng4_validation_path = resolve(args.dng4_validation)
    price_matrix_path = resolve(args.price_market_readiness)
    orthogonal_matrix_path = resolve(args.orthogonal_readiness)
    pending_path = resolve(args.pending_asof)
    job_path = resolve(args.job_json) if args.job_json else latest_job_path()

    catalog = read_json(catalog_path)
    latest_status = read_json(latest_status_path)
    route_validation = read_json(route_validation_path)
    dng4_validation = read_json(dng4_validation_path)
    price_matrix = read_json(price_matrix_path)
    orthogonal_matrix = read_json(orthogonal_matrix_path)
    pending = read_json(pending_path)
    job = read_json(job_path) if job_path else {}

    latest_by_concept = latest_status.get("latest_by_concept") if isinstance(latest_status.get("latest_by_concept"), dict) else {}
    concept_summary = {concept: compact_latest(latest_by_concept.get(concept), concept=concept) for concept in LATEST_CONCEPTS}
    price_layer, market_layer = summarize_price_market(price_matrix)
    route_layer = summarize_route_dependency(route_validation)
    readiness_by_layer = {
        "price": price_layer,
        "market": market_layer,
        "orthogonal": summarize_orthogonal(orthogonal_matrix),
        "bundle": summarize_bundle(dng4_validation),
        "route_dependency": route_layer,
    }

    known_blockers: list[str] = []
    for mismatch in latest_status.get("known_mismatch") or []:
        if isinstance(mismatch, dict):
            known_blockers.append(f"{mismatch.get('mismatch_id')}: {mismatch.get('description')}")
    for layer_name, layer in readiness_by_layer.items():
        for blocker in layer.get("blockers") or []:
            known_blockers.append(f"{layer_name}: {blocker}")

    source_flags = collect_source_forbidden_flags(
        catalog,
        latest_status,
        route_validation,
        dng4_validation,
        price_matrix,
        orthogonal_matrix,
        job,
    )
    dashboard_status = "BLOCKED_OR_PARTIAL_NOT_PRODUCTION_READY" if known_blockers or not route_layer.get("all_gate_pass") else "OBSERVABLE_READY_NOT_PRODUCTION_READY"
    next_retry_hint = (
        str(pending.get("reason") or "")
        or str(provider_quota_from_job(job).get("next_retry_hint") or "")
        or ("retry_after_today_data_window" if job.get("status") == "today_data_window_wait" else "")
        or "advance only via next explicit DNG gate; do not publish latest from DNG6"
    )
    asof = args.asof or str(job.get("asof") or pending.get("asof") or price_matrix.get("asof") or orthogonal_matrix.get("asof") or concept_summary["provider_raw_latest"].get("asof") or "")

    dashboard = {
        "schema_version": "v1.dng6.daily_readiness_dashboard",
        "generated_at": utc_now(),
        "asof": asof,
        "dashboard_status": dashboard_status,
        "production_ready": False,
        "provider_raw_latest_by_dataset": latest_by_dataset(catalog, "provider_raw_latest"),
        "normalized_latest_by_dataset": latest_by_dataset(catalog, "normalized_latest"),
        "price_store_latest": concept_summary["price_store_latest"],
        "feature_store_latest": concept_summary["feature_store_latest"],
        "qlib_accepted_latest": concept_summary["qlib_accepted_latest"],
        "model_signal_latest_by_model": model_signal_latest_by_model(catalog, latest_status),
        "readonly_snapshot_latest": concept_summary["readonly_snapshot_latest"],
        "agent_prompt_latest": concept_summary["agent_prompt_latest"],
        "pending_asof": {
            "exists": bool(pending),
            "asof": str(pending.get("asof") or ""),
            "reason": str(pending.get("reason") or ""),
            "job_id": str(pending.get("job_id") or ""),
            "path": rel(pending_path),
        },
        "provider_quota_status": provider_quota_from_job(job),
        "holiday_status": holiday_from_job(job),
        "next_retry_hint": next_retry_hint,
        "readiness_by_layer": readiness_by_layer,
        "route_dependency_summary": {
            "ok": bool(route_validation.get("ok")),
            "all_gate_pass": bool(route_validation.get("all_gate_pass")),
            "summary": route_validation.get("summary") if isinstance(route_validation.get("summary"), dict) else {},
            "routes": route_layer.get("routes", {}),
        },
        "known_blockers": known_blockers,
        "allowed_next_steps": [
            "Keep DNG6 dashboard/validator as static observability in daily auto.",
            "Repair canonical PriceStore/latest_status lineage before replay or production claims.",
            "Proceed to DNG7 only under a separate explicit gate for ModelInferenceInput and qlib Model A ScoreJob contracts.",
            "Continue using DNG5 route dependency validation before any model/strategy route.",
        ],
        "forbidden_actions_audit": {
            "scope": "DNG6 static dashboard build and validation; no provider, model, replay, publish, or trading side effects",
            "actions": source_flags,
            "all_false": not any(source_flags.values()),
        },
        "latest_concepts": concept_summary,
        "daily_auto_integration": {
            "mode": "optional_finalize_observability_step",
            "enabled_by": "TW_DAILY_AUTO_ENABLE_DATA_CATALOG_DASHBOARD or --enable-data-catalog-dashboard",
            "default_enabled": False,
            "safe_static_only": True,
            "job_json": rel(job_path) if job_path else "",
        },
        "source_files": {
            "catalog": rel(catalog_path),
            "latest_status": rel(latest_status_path),
            "route_validation": rel(route_validation_path),
            "dng4_validation": rel(dng4_validation_path),
            "price_market_readiness": rel(price_matrix_path),
            "orthogonal_readiness": rel(orthogonal_matrix_path),
            "pending_asof": rel(pending_path),
            "job_json": rel(job_path) if job_path else "",
        },
        "source_summary": {
            "catalog_entry_count": len(catalog.get("entries") or []),
            "catalog_status_counts": dict(sorted(Counter(str(entry.get("status")) for entry in catalog.get("entries", []) if isinstance(entry, dict)).items())),
            "latest_generated_at": latest_status.get("generated_at", ""),
            "route_validation_generated_at": route_validation.get("generated_at", ""),
        },
    }
    return dashboard


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the DNG6 Taiwan daily readiness dashboard from static catalog evidence.")
    parser.add_argument("--catalog", default="data_tw/catalog/data_catalog.json")
    parser.add_argument("--latest-status", default="data_tw/catalog/latest_status.json")
    parser.add_argument("--route-validation", default="data_tw/catalog/dng5_route_dependency_validation.json")
    parser.add_argument("--dng4-validation", default="data_tw/catalog/dng4_input_bundle_validation.json")
    parser.add_argument("--price-market-readiness", default="data_tw/catalog/readiness_matrix/2026-06-25/price_market_calendar.json")
    parser.add_argument("--orthogonal-readiness", default="data_tw/catalog/readiness_matrix/2026-06-25/orthogonal_feature_store.json")
    parser.add_argument("--pending-asof", default="data_tw/ops/daily_auto_update/pending_asof.json")
    parser.add_argument("--job-json", default="")
    parser.add_argument("--asof", default="")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT.relative_to(ROOT)))
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dashboard = build_dashboard(args)
    output = resolve(args.output)
    write_json(output, dashboard)
    if args.json:
        print(json.dumps(dashboard, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"wrote {rel(output)} status={dashboard.get('dashboard_status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
