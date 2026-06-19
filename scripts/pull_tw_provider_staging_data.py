#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "data_tw/artifacts/provider_staging"
SCHEMA_VERSION = "v2.provider_staging_pull.v1"
YAHOO_LOCAL_DIR = ROOT / "data_tw/self_contained_demo/normalized"
FINMIND_PIT_DIR = ROOT / "data_tw/experiments/decision_orthogonal/phase0d_pit_clean"
O2_DIR = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder"
P3_ORTHO_DIR = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank"
SIGNAL_ROOT = ROOT / "data_tw/artifacts/signals"


SOURCE_CONTRACTS: list[dict[str, Any]] = [
    {
        "source_id": "yahoo_daily_price",
        "provider": "Yahoo",
        "required": True,
        "required_fields": ["date", "instrument", "open", "high", "low", "close", "volume", "adjusted_close"],
        "write_dir": "yahoo",
        "coverage_count": 150,
        "coverage_ratio": 1.0,
    },
    {
        "source_id": "finmind_daily_price",
        "provider": "FinMind",
        "required": False,
        "required_fields": ["date", "instrument", "open", "high", "low", "close", "volume"],
        "write_dir": "finmind/daily_price",
        "coverage_count": 150,
        "coverage_ratio": 1.0,
    },
    {
        "source_id": "finmind_institutional_flow",
        "provider": "FinMind",
        "required": True,
        "required_fields": [
            "foreign_net_buy",
            "investment_trust_net_buy",
            "dealer_net_buy",
            "institutional_total_net_buy",
            "rolling_sums",
            "streak",
            "missing_flag",
            "delay_flag",
        ],
        "write_dir": "finmind/institutional_flow",
        "coverage_count": 150,
        "coverage_ratio": 1.0,
    },
    {
        "source_id": "finmind_margin_short",
        "provider": "FinMind",
        "required": True,
        "required_fields": [
            "margin_balance",
            "margin_balance_change",
            "short_balance",
            "short_balance_change",
            "rolling_sums",
            "direction_proxy",
            "divergence_proxy",
            "missing_flag",
            "delay_flag",
        ],
        "write_dir": "finmind/margin_short",
        "coverage_count": 150,
        "coverage_ratio": 1.0,
    },
    {
        "source_id": "orthogonal_o2_features",
        "provider": "DerivedOrthogonal",
        "required": True,
        "required_fields": ["date", "instrument", "available_at", "feature_family", "lineage", "missing_flag"],
        "write_dir": "orthogonal",
        "coverage_count": 150,
        "coverage_ratio": 1.0,
    },
    {
        "source_id": "existing_signal_manifest",
        "provider": "LocalArtifacts",
        "required": True,
        "required_fields": ["model_id", "signal_asof", "available_at", "candidate_rank", "buy_score", "full_qlib_rank"],
        "write_dir": "model_signals",
        "coverage_count": 5,
        "coverage_ratio": 1.0,
        "retryable": False,
    },
]

SCENARIOS = {
    "all_required_ready",
    "no_new_data",
    "partial_data_pending",
    "provider_failed",
    "validator_failed_future_available_at",
    "deadline_missed_keep_previous_latest",
    "missing_orthogonal_required_source",
    "missing_symbol_mapping",
    "provider_publish_triggered",
    "accepted_latest_switched",
    "monitor_or_broker_action",
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def csv_latest_and_coverage(path: Path, date_field: str, symbol_field_candidates: list[str], limit: int | None = None) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "latest": "", "symbol_count": 0, "row_count": 0}
    files = sorted(path.glob("TW*.csv")) if path.is_dir() else [path]
    if limit:
        files = files[:limit]
    latest = ""
    symbols: set[str] = set()
    row_count = 0
    for file in files:
        try:
            with file.open("r", encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f):
                    row_count += 1
                    value = str(row.get(date_field, ""))
                    if value > latest:
                        latest = value
                    for field in symbol_field_candidates:
                        symbol = str(row.get(field, "")).strip().upper()
                        if symbol:
                            symbols.add(symbol)
                            break
                    if not symbol_field_candidates and file.stem:
                        symbols.add(file.stem.upper())
        except Exception:
            continue
    return {"exists": True, "latest": latest, "symbol_count": len(symbols), "row_count": row_count}


def status_from_latest(latest: str, target_asof: str) -> str:
    if not latest:
        return "failed"
    if latest < target_asof:
        return "no_new_data"
    return "ready"


def run_external_provider_fetch(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    fetch_run_id = "external_provider_fetch"
    cmd = [
        sys.executable,
        "scripts/fetch_tw_provider_external_data.py",
        "--run-id",
        fetch_run_id,
        "--out-root",
        str(out_dir),
        "--target-asof",
        args.target_asof,
        "--start",
        args.external_start,
        "--end",
        args.external_end or args.target_asof,
        "--max-symbols",
        str(args.max_symbols),
        "--timeout",
        str(args.timeout),
        "--retries",
        str(args.retries),
        "--retry-sleep-seconds",
        str(args.retry_sleep_seconds),
        "--sleep-seconds",
        str(args.sleep_seconds),
        "--json",
    ]
    if args.symbols_file:
        cmd.extend(["--symbols-file", args.symbols_file])
    for symbol in args.symbol or []:
        cmd.extend(["--symbol", symbol])
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        result = {"ok": False, "stdout": proc.stdout, "stderr": proc.stderr}
    result["returncode"] = proc.returncode
    if proc.returncode != 0:
        result.setdefault("error", proc.stderr or proc.stdout or "external provider fetch failed")
    return result


def source_for_external_provider(contract: dict[str, Any], args: argparse.Namespace, out_dir: Path, external_manifest: dict[str, Any]) -> dict[str, Any]:
    source_id = contract["source_id"]
    retryable = bool(contract.get("retryable", True))
    external_sources = external_manifest.get("sources") or {}
    summary = external_sources.get(source_id) or {}
    expected_count = int(args.max_symbols or contract.get("coverage_count") or 150)
    latest = str(summary.get("latest") or "")
    coverage_count = int(summary.get("symbols_success") or 0)
    if source_id in {"orthogonal_o2_features", "existing_signal_manifest"}:
        return source_for_real_provider(contract, args, out_dir)
    status = status_from_latest(latest, args.target_asof)
    failure_reason = ""
    fallback_used = False
    fallback_source_id = ""
    fallback_reason = ""
    price_source_policy = "single_source"
    if source_id == "yahoo_daily_price":
        price_source_policy = "preferred_yahoo_fallback_finmind"
        finmind_summary = external_sources.get("finmind_daily_price") or {}
        finmind_latest = str(finmind_summary.get("latest") or "")
        finmind_coverage = int(finmind_summary.get("symbols_success") or 0)
        finmind_status = status_from_latest(finmind_latest, args.target_asof)
        finmind_ratio = min(1.0, finmind_coverage / max(1, expected_count))
        if status == "failed" and finmind_status == "ready" and finmind_ratio >= 0.8:
            fallback_used = True
            fallback_source_id = "finmind_daily_price"
            fallback_reason = "Yahoo preferred price source failed; FinMind daily price is ready and used as required price fallback."
            latest = finmind_latest
            coverage_count = finmind_coverage
            status = "ready"
            failure_reason = ""
    if summary.get("symbols_failed") and not fallback_used:
        failure_reason = f"external provider failed symbols: {len(summary.get('symbols_failed') or {})}"
    if status == "no_new_data":
        failure_reason = failure_reason or f"External {contract['provider']} latest {latest} is before target_asof {args.target_asof}"
    elif status == "failed":
        failure_reason = failure_reason or f"External {contract['provider']} returned no usable rows"
    coverage_ratio = min(1.0, coverage_count / max(1, expected_count))
    if status == "ready" and contract.get("required") and coverage_ratio < 0.8:
        status = "partial"
        failure_reason = failure_reason or f"external coverage_ratio {coverage_ratio:.3f} below readiness threshold"
    source_output = summary.get("output") or summary.get("raw_output") or ""
    return {
        "source_id": source_id,
        "provider": contract["provider"],
        "required": bool(contract["required"]),
        "required_fields": list(contract["required_fields"]),
        "expected_asof": args.target_asof,
        "actual_latest_asof": latest,
        "available_at": args.decision_cutoff if latest else "",
        "coverage_count": coverage_count,
        "coverage_ratio": coverage_ratio,
        "write_path": rel(out_dir / contract["write_dir"]),
        "failure_reason": failure_reason,
        "retryable": retryable,
        "status": status,
        "symbol_mapping_ready": True,
        "pit_audit_passed": True,
        "reader_mode": "external_provider_reader",
        "real_provider_mode": True,
        "external_provider_mode": True,
        "price_source_policy": price_source_policy,
        "fallback_used": fallback_used,
        "fallback_source_id": fallback_source_id,
        "fallback_reason": fallback_reason,
        "source_evidence": {"external_manifest": external_manifest.get("run_id"), "summary": summary, "materialized_output": source_output},
    }


def source_for_real_provider(contract: dict[str, Any], args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    source_id = contract["source_id"]
    retryable = bool(contract.get("retryable", True))
    latest = ""
    coverage_count = 0
    expected_count = int(contract.get("coverage_count") or 150)
    failure_reason = ""
    status = "ready"
    pit_audit_passed = True
    symbol_mapping_ready = True
    evidence: dict[str, Any] = {}

    if source_id == "yahoo_daily_price":
        info = csv_latest_and_coverage(YAHOO_LOCAL_DIR, "date", [], limit=expected_count)
        latest = info["latest"]
        coverage_count = int(info["symbol_count"])
        status = status_from_latest(latest, args.target_asof)
        evidence = {"local_source_dir": rel(YAHOO_LOCAL_DIR), **info}
        if status == "no_new_data":
            failure_reason = f"Yahoo local staging latest {latest} is before target_asof {args.target_asof}"
        elif status == "failed":
            failure_reason = "Yahoo local staging data missing or unreadable"
    elif source_id == "finmind_daily_price":
        info = csv_latest_and_coverage(YAHOO_LOCAL_DIR, "date", [], limit=expected_count)
        latest = info["latest"]
        coverage_count = int(info["symbol_count"])
        status = status_from_latest(latest, args.target_asof)
        evidence = {"local_proxy_source_dir": rel(YAHOO_LOCAL_DIR), "note": "FinMind daily price local staging not separately present; price coverage proxied for optional cross-check", **info}
        if status == "no_new_data":
            failure_reason = f"Optional FinMind price proxy latest {latest} is before target_asof {args.target_asof}"
    elif source_id == "finmind_institutional_flow":
        path = FINMIND_PIT_DIR / "phase0d_institutional_flow_pit_clean.csv"
        info = csv_latest_and_coverage(path, "trade_date", ["symbol", "stock_id"])
        latest = info["latest"]
        coverage_count = int(info["symbol_count"])
        status = status_from_latest(latest, args.target_asof)
        evidence = {"local_source_file": rel(path), **info}
        if status == "no_new_data":
            failure_reason = f"FinMind institutional local PIT latest {latest} is before target_asof {args.target_asof}"
        elif status == "failed":
            failure_reason = "FinMind institutional local PIT data missing or unreadable"
    elif source_id == "finmind_margin_short":
        path = FINMIND_PIT_DIR / "phase0d_margin_short_pit_clean.csv"
        info = csv_latest_and_coverage(path, "trade_date", ["symbol", "stock_id"])
        latest = info["latest"]
        coverage_count = int(info["symbol_count"])
        status = status_from_latest(latest, args.target_asof)
        evidence = {"local_source_file": rel(path), **info}
        if status == "no_new_data":
            failure_reason = f"FinMind margin/short local PIT latest {latest} is before target_asof {args.target_asof}"
        elif status == "failed":
            failure_reason = "FinMind margin/short local PIT data missing or unreadable"
    elif source_id == "orthogonal_o2_features":
        p3_latest = P3_ORTHO_DIR / "daily_ltr_rerank_latest.json"
        if p3_latest.exists():
            payload = json.loads(p3_latest.read_text(encoding="utf-8"))
            latest = str(payload.get("asof") or "")[:10]
            coverage_count = int(payload.get("top50_scored_count") or payload.get("top50_input_count") or 0)
            expected_count = max(1, int(payload.get("top50_input_count") or coverage_count or 50))
            status = status_from_latest(latest, args.target_asof)
            refresh = payload.get("orthogonal_refresh_status") or {}
            pit_audit_passed = bool(payload.get("pit_pass")) and payload.get("status") == "ready" and refresh.get("status") == "current_or_pit_delayed"
            evidence = {
                "local_summary": rel(p3_latest),
                "source": "daily_ltr_rerank_latest",
                "latest_feature_table_path": refresh.get("latest_feature_table_path"),
                "latest_feature_table_created_at": refresh.get("latest_feature_table_created_at"),
                "institutional_latest_available_at": refresh.get("institutional_latest_available_at"),
                "margin_latest_available_at": refresh.get("margin_latest_available_at"),
                "top50_input_count": payload.get("top50_input_count"),
                "top50_scored_count": payload.get("top50_scored_count"),
                "p3_status": payload.get("status"),
                "refresh_status": refresh.get("status"),
                "failure_isolation_audit": payload.get("failure_isolation_audit"),
            }
            if status == "no_new_data":
                failure_reason = f"Orthogonal daily rerank latest {latest} is before target_asof {args.target_asof}"
            if not pit_audit_passed:
                status = "invalid"
                failure_reason = "Orthogonal daily rerank PIT or refresh gate not ready"
        else:
            summary = O2_DIR / "phaseo2_summary.json"
            if summary.exists():
                payload = json.loads(summary.read_text(encoding="utf-8"))
                latest = str(payload.get("feature_daily_date_max") or "")
                coverage_count = int(payload.get("feature_daily_symbol_count") or payload.get("control_symbol_count") or 0)
                status = status_from_latest(latest, args.target_asof)
                evidence = {"local_summary": rel(summary), "available_at_contract": payload.get("available_at_contract"), "feature_daily_rows": payload.get("feature_daily_rows"), "source": "legacy_o2_summary"}
                pit_audit_passed = payload.get("gate") == "phase_o2_pit_safe_feature_builder_passed"
                if status == "no_new_data":
                    failure_reason = f"Orthogonal O2 latest {latest} is before target_asof {args.target_asof}"
                if not pit_audit_passed:
                    status = "invalid"
                    failure_reason = "Orthogonal O2 PIT gate not passed"
            else:
                status = "failed"; failure_reason = "Orthogonal O2 summary missing"; coverage_count = 0
    elif source_id == "existing_signal_manifest":
        manifests = sorted(SIGNAL_ROOT.glob("*/r1_legacy_signal_adapter_20260616/manifest.json"))
        coverage_count = len(manifests)
        latest = args.target_asof if manifests else ""
        status = "ready" if manifests else "failed"
        retryable = False
        evidence = {"manifest_count": len(manifests), "manifests": [rel(m) for m in manifests]}
        if status == "failed":
            failure_reason = "No local signal manifests found"

    coverage_ratio = min(1.0, coverage_count / max(1, expected_count))
    if status == "ready" and contract.get("required") and coverage_ratio < 0.8:
        status = "partial"
        failure_reason = failure_reason or f"coverage_ratio {coverage_ratio:.3f} below readiness threshold"
    if status == "no_new_data":
        # Stale but present data is a real provider no-new-data state; coverage should describe available source breadth.
        failure_reason = failure_reason or f"actual_latest_asof {latest} is before target_asof {args.target_asof}"
    available_at = args.decision_cutoff if latest else ""
    return {
        "source_id": source_id,
        "provider": contract["provider"],
        "required": bool(contract["required"]),
        "required_fields": list(contract["required_fields"]),
        "expected_asof": args.target_asof,
        "actual_latest_asof": latest,
        "available_at": available_at,
        "coverage_count": coverage_count,
        "coverage_ratio": coverage_ratio,
        "write_path": rel(out_dir / contract["write_dir"]),
        "failure_reason": failure_reason,
        "retryable": retryable,
        "status": status,
        "symbol_mapping_ready": symbol_mapping_ready,
        "pit_audit_passed": pit_audit_passed,
        "real_provider_mode": True,
        "source_evidence": evidence,
    }


def source_for_scenario(contract: dict[str, Any], args: argparse.Namespace, out_dir: Path) -> dict[str, Any] | None:
    if args.scenario == "missing_orthogonal_required_source" and contract["source_id"] == "orthogonal_o2_features":
        return None
    retryable = bool(contract.get("retryable", True))
    actual_latest_asof = args.target_asof
    available_at = args.decision_cutoff
    coverage_count = int(contract["coverage_count"])
    coverage_ratio = float(contract["coverage_ratio"])
    failure_reason = ""
    status = "ready"
    required_fields = list(contract["required_fields"])

    if args.scenario == "no_new_data":
        actual_latest_asof = args.previous_readonly_latest
        status = "no_new_data"
    elif args.scenario == "partial_data_pending" and contract["required"]:
        coverage_count = max(0, coverage_count - 80)
        coverage_ratio = 0.45
        status = "partial"
        failure_reason = "coverage_ratio below readiness threshold"
    elif args.scenario == "provider_failed" and contract["provider"] in {"Yahoo", "FinMind"} and contract["required"]:
        status = "failed"
        actual_latest_asof = ""
        available_at = ""
        coverage_count = 0
        coverage_ratio = 0.0
        failure_reason = "provider request failed in staging pull"
    elif args.scenario == "validator_failed_future_available_at" and contract["required"]:
        available_at = "2099-01-01T00:00:00+00:00"
        status = "invalid"
        failure_reason = "available_at is after decision_cutoff"
    elif args.scenario == "missing_symbol_mapping" and contract["source_id"] == "yahoo_daily_price":
        status = "invalid"
        failure_reason = "symbol mapping missing for required universe"
    elif args.scenario == "deadline_missed_keep_previous_latest":
        status = "deadline_missed"
        failure_reason = "decision deadline reached before all required sources became ready"

    source = {
        "source_id": contract["source_id"],
        "provider": contract["provider"],
        "required": bool(contract["required"]),
        "required_fields": required_fields,
        "expected_asof": args.target_asof,
        "actual_latest_asof": actual_latest_asof,
        "available_at": available_at,
        "coverage_count": coverage_count,
        "coverage_ratio": coverage_ratio,
        "write_path": rel(out_dir / contract["write_dir"]),
        "failure_reason": failure_reason,
        "retryable": retryable,
        "status": status,
        "symbol_mapping_ready": args.scenario != "missing_symbol_mapping",
        "pit_audit_passed": args.scenario != "validator_failed_future_available_at",
    }
    return source


def forbidden_actions(scenario: str) -> dict[str, Any]:
    actions = {
        "provider_publish_triggered": False,
        "provider_refresh_official_path_triggered": False,
        "accepted_latest_switched": False,
        "qlib_accepted_latest_switched": False,
        "monitor_config_written": False,
        "monitor_scan_triggered": False,
        "alerts_written": False,
        "broker_connected": False,
        "quick_trade_triggered": False,
        "orders_created_or_sent": False,
        "agent_prompt_or_tool_modified": False,
        "readonly_latest_updated": False,
    }
    if scenario == "provider_publish_triggered":
        actions["provider_publish_triggered"] = True
    elif scenario == "accepted_latest_switched":
        actions["accepted_latest_switched"] = True
        actions["qlib_accepted_latest_switched"] = True
    elif scenario == "monitor_or_broker_action":
        actions["monitor_config_written"] = True
        actions["broker_connected"] = True
        actions["orders_created_or_sent"] = True
    return {"schema_version": "v1.forbidden_action_audit.v1", "actions": actions}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Phase V1 provider staging source snapshots without publishing latest.")
    parser.add_argument("--target-asof", default="2026-06-10")
    parser.add_argument("--decision-for", default="2026-06-11")
    parser.add_argument("--decision-cutoff", default="2026-06-11T23:59:59+00:00")
    parser.add_argument("--previous-readonly-latest", default="2026-05-07")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--out-root", default=str(OUT_ROOT))
    parser.add_argument("--mode", choices=["real_provider", "external_provider_reader", "local_real_provider_reader", "test_scenario"], default="real_provider")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="all_required_ready")
    parser.add_argument("--external-start", default="2026-06-01")
    parser.add_argument("--external-end", default="")
    parser.add_argument("--symbol", action="append")
    parser.add_argument("--symbols-file", default="")
    parser.add_argument("--max-symbols", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--retry-sleep-seconds", type=float, default=0.5)
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    run_id = args.run_id or f"phasev1_provider_staging_{args.target_asof.replace('-', '')}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    out_dir = Path(args.out_root) / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    effective_mode = "external_provider_reader" if args.mode == "real_provider" else args.mode
    external_result: dict[str, Any] = {}
    external_manifest: dict[str, Any] = {}
    if effective_mode == "external_provider_reader":
        external_result = run_external_provider_fetch(args, out_dir)
        manifest_path = ROOT / str(external_result.get("manifest", ""))
        if manifest_path.exists():
            external_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        else:
            external_manifest = {"run_id": "external_provider_fetch_failed", "sources": {}, "error": external_result.get("error") or external_result}
    sources: list[dict[str, Any]] = []
    for contract in SOURCE_CONTRACTS:
        if effective_mode == "test_scenario":
            source = source_for_scenario(contract, args, out_dir)
        elif effective_mode == "external_provider_reader":
            source = source_for_external_provider(contract, args, out_dir, external_manifest)
        else:
            source = source_for_real_provider(contract, args, out_dir)
        if source is None:
            continue
        source_dir = out_dir / str(contract["write_dir"])
        write_json(source_dir / "source_status.json", source)
        sources.append(source)
    if effective_mode == "external_provider_reader" and (out_dir / "external_provider_fetch" / "forbidden_action_audit.json").exists():
        forbidden = json.loads((out_dir / "external_provider_fetch" / "forbidden_action_audit.json").read_text(encoding="utf-8"))
        shutil.copyfile(out_dir / "external_provider_fetch" / "forbidden_action_audit.json", out_dir / "forbidden_action_audit.json")
    else:
        forbidden = forbidden_actions(args.scenario if effective_mode == "test_scenario" else "all_required_ready")
        write_json(out_dir / "forbidden_action_audit.json", forbidden)
    pull_manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "provider_staging_pull",
        "run_id": run_id,
        "mode": effective_mode,
        "requested_mode": args.mode,
        "scenario": args.scenario if effective_mode == "test_scenario" else effective_mode,
        "target_asof": args.target_asof,
        "decision_for": args.decision_for,
        "decision_cutoff": args.decision_cutoff,
        "previous_readonly_latest": args.previous_readonly_latest,
        "created_at": now(),
        "created_by": "scripts/pull_tw_provider_staging_data.py",
        "staging_only": True,
        "provider_publish_triggered": False,
        "accepted_latest_switched": False,
        "sources": sources,
        "price_source_policy": {
            "policy": "preferred_yahoo_fallback_finmind",
            "preferred_source_id": "yahoo_daily_price",
            "fallback_source_id": "finmind_daily_price",
            "fallback_used": any(bool(s.get("fallback_used")) for s in sources),
            "ready_source_id": next((s.get("fallback_source_id") or s.get("source_id") for s in sources if s.get("source_id") == "yahoo_daily_price" and s.get("status") == "ready"), ""),
        } if effective_mode == "external_provider_reader" else {},
        "external_provider_fetch": external_result if effective_mode == "external_provider_reader" else {},
        "provider_network_audit": rel(out_dir / "external_provider_fetch" / "provider_network_audit.json") if effective_mode == "external_provider_reader" else "",
        "files": {
            "forbidden_action_audit": "forbidden_action_audit.json",
            "provider_network_audit": "external_provider_fetch/provider_network_audit.json" if effective_mode == "external_provider_reader" else "",
            "source_status_files": [str(Path(s["write_path"]) / "source_status.json") for s in sources],
        },
    }
    write_json(out_dir / "provider_staging_pull_manifest.json", pull_manifest)
    result = {"ok": True, "staging_dir": rel(out_dir), "pull_manifest": rel(out_dir / "provider_staging_pull_manifest.json"), "source_count": len(sources), "mode": effective_mode, "requested_mode": args.mode, "scenario": args.scenario if effective_mode == "test_scenario" else effective_mode}
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result["pull_manifest"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
