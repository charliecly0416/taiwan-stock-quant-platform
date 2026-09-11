#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DAPR_ROOT = ROOT / "data_tw/experiments/daily_accepted_production_readiness"
DAPR1_DIR = DAPR_ROOT / "dapr1_canonical_bridge_contract"
DAPR6_DIR = DAPR_ROOT / "dapr6_lineage_model_compatibility_review_or_stop"
OUT_DIR = DAPR_ROOT / "dapr7_same_lineage_yahoo_adjusted_exact_target_bridge_build_no_publish"
PBPR_MATERIAL_ROOT = ROOT / "data_tw/experiments/provider_bridge_productionization"

TARGET_ASOF_FALLBACK = "2026-07-17"
REQUIRED_FIELDS = {"open", "high", "low", "close", "volume", "vwap", "factor"}
REQUIRED_COLUMNS = {"symbol", "date", *REQUIRED_FIELDS}
SAME_LINEAGE_HINTS = ("yahoo", "scrapling", "yahoo_adjusted", "provider_bridge_productionization")
FORBIDDEN_ACTIONS = {
    "provider_pull_triggered": False,
    "provider_publish_triggered": False,
    "formal_provider_or_calendar_mutated": False,
    "formal_normalized_mutated": False,
    "accepted_latest_switch_triggered": False,
    "qlib_refresh_triggered": False,
    "model_scoring_triggered": False,
    "model_inference_input_built": False,
    "score_job_built": False,
    "model_signal_artifact_built": False,
    "readonly_latest_published": False,
    "agent_prompt_built_or_published": False,
    "openai_called": False,
    "database_read_or_write_triggered": False,
    "monitor_broker_order_or_target_written": False,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(name: str, payload: Any) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def same_lineage_path(path: Path) -> bool:
    text = rel(path).lower()
    return any(hint in text for hint in SAME_LINEAGE_HINTS)


def discover_normalized_roots() -> list[Path]:
    roots: set[Path] = set()
    for base in [ROOT / "qlib_pipeline/data_tw/experiments", ROOT / "data_tw/experiments"]:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_dir():
                continue
            if path.name in {"candidate_normalized", "option_c_150_normalized", "normalized_nonempty"}:
                roots.add(path)
    return sorted(roots)


def discover_provider_roots() -> list[Path]:
    roots: set[Path] = set()
    for base in [ROOT / "qlib_pipeline/data_tw/experiments", ROOT / "data_tw/experiments"]:
        if not base.exists():
            continue
        for calendar in base.rglob("calendars/day.txt"):
            provider_root = calendar.parent.parent
            if (provider_root / "features").exists() and (provider_root / "instruments").exists():
                roots.add(provider_root)
    return sorted(roots)


def audit_normalized_root(path: Path, target_asof: str) -> dict[str, Any]:
    files = sorted(path.glob("TW*.csv"))
    date_min = ""
    date_max = ""
    rows_total = 0
    files_with_target = 0
    symbols_with_target: set[str] = set()
    missing_columns_samples: list[dict[str, Any]] = []
    malformed_samples: list[dict[str, Any]] = []
    for file_path in files:
        try:
            with file_path.open("r", encoding="utf-8", newline="") as fh:
                reader = csv.DictReader(fh)
                columns = set(reader.fieldnames or [])
                missing = sorted(REQUIRED_COLUMNS - columns)
                symbol = file_path.stem
                has_target = False
                for row in reader:
                    rows_total += 1
                    date = str(row.get("date") or "").strip()
                    if date:
                        date_min = date if not date_min else min(date_min, date)
                        date_max = date if not date_max else max(date_max, date)
                        if date == target_asof:
                            has_target = True
                if has_target:
                    files_with_target += 1
                    symbols_with_target.add(symbol)
                if missing and len(missing_columns_samples) < 10:
                    missing_columns_samples.append({"path": rel(file_path), "missing_columns": missing})
        except Exception as exc:  # pragma: no cover - route evidence records local file defects.
            if len(malformed_samples) < 10:
                malformed_samples.append({"path": rel(file_path), "error": f"{type(exc).__name__}: {exc}"})
    exact_target_150 = len(files) >= 150 and len(symbols_with_target) >= 150 and not missing_columns_samples and not malformed_samples
    return {
        "path": rel(path),
        "same_lineage_hint": same_lineage_path(path),
        "file_count": len(files),
        "rows_total": rows_total,
        "date_min": date_min,
        "date_max": date_max,
        "files_with_target_asof": files_with_target,
        "symbols_with_target_asof": len(symbols_with_target),
        "missing_columns_samples": missing_columns_samples,
        "malformed_samples": malformed_samples,
        "exact_target_150_ready": exact_target_150,
        "same_lineage_exact_target_ready": exact_target_150 and same_lineage_path(path),
    }


def read_instrument_symbols(provider_root: Path) -> list[str]:
    path = provider_root / "instruments/all.txt"
    if not path.exists():
        return []
    return [line.split()[0].strip().upper() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def audit_provider_root(path: Path, target_asof: str) -> dict[str, Any]:
    calendar = path / "calendars/day.txt"
    calendar_rows = [line.strip() for line in calendar.read_text(encoding="utf-8").splitlines() if line.strip()] if calendar.exists() else []
    symbols = read_instrument_symbols(path)
    counts = {field: 0 for field in sorted(REQUIRED_FIELDS)}
    missing_feature_symbols: list[str] = []
    for symbol in symbols:
        feature_dir = path / "features" / symbol.lower()
        if not feature_dir.exists():
            missing_feature_symbols.append(symbol)
            continue
        fields = {item.name.split(".")[0] for item in feature_dir.glob("*.day.bin")}
        for field in REQUIRED_FIELDS:
            if field in fields:
                counts[field] += 1
    calendar_max = max(calendar_rows) if calendar_rows else ""
    provider_ready = (
        same_lineage_path(path)
        and len(symbols) == 150
        and calendar_max >= target_asof
        and all(count == 150 for count in counts.values())
        and not missing_feature_symbols
    )
    return {
        "path": rel(path),
        "same_lineage_hint": same_lineage_path(path),
        "calendar_exists": calendar.exists(),
        "calendar_min": min(calendar_rows) if calendar_rows else "",
        "calendar_max": calendar_max,
        "calendar_has_target_asof": target_asof in set(calendar_rows),
        "calendar_row_count": len(calendar_rows),
        "instrument_count": len(symbols),
        "required_feature_counts": counts,
        "missing_feature_symbols_count": len(missing_feature_symbols),
        "missing_feature_symbols_sample": missing_feature_symbols[:20],
        "same_lineage_provider_ready": provider_ready,
    }


def build_provider_only_rerun_plan(target_asof: str) -> dict[str, Any]:
    job_id = f"dapr7_yahoo_adjusted_provider_only_{target_asof.replace('-', '')}_AUTHORIZED_RERUN"
    output_root = PBPR_MATERIAL_ROOT / "dapr7_same_lineage_yahoo_adjusted_exact_target_bridge_build_no_publish" / job_id
    report_path = output_root / "reports" / f"{job_id}_report.md"
    command = [
        "python",
        "qlib_pipeline/examples/tw/run_option_c_yahoo_scrapling_refresh.py",
        "--asof",
        target_asof,
        "--start",
        "2015-01-01",
        "--universe",
        "option_c_accepted_150",
        "--output-root",
        str(output_root),
        "--job-id",
        job_id,
        "--report-path",
        str(report_path),
        "--provider-only",
        "--suffix",
        "auto",
        "--timeout",
        "30",
        "--retries",
        "2",
        "--sleep-seconds",
        "1.0",
        "--max-workers",
        "4",
        "--proxy",
        "http://127.0.0.1:7890",
        "--yahoo-session-warmup",
        "--yahoo-quote-page-warmup",
        "--http-403-backoff-seconds",
        "3.0",
    ]
    return {
        "schema_version": "dapr7.provider_only_rerun_plan.v1",
        "target_asof": target_asof,
        "job_id": job_id,
        "output_root": str(output_root),
        "report_path": str(report_path),
        "command": command,
        "command_text": " ".join(command),
        "requires_explicit_live_provider_authorization": True,
        "no_publish_boundary": {
            "provider_only": True,
            "provider_publish_allowed": False,
            "formal_provider_mutation_allowed": False,
            "qlib_refresh_allowed": False,
            "accepted_latest_switch_allowed": False,
            "model_scoring_allowed": False,
            "agent_or_readonly_publish_allowed": False,
        },
        "source_policy": "Yahoo/Scrapling only; no FinMind fallback; no mixed provider; no prior-asof fill.",
    }


def build() -> dict[str, Any]:
    created_at = utc_now()
    dapr6_decision = read_json(DAPR6_DIR / "lineage_model_compatibility_decision.json")
    target_asof = str(dapr6_decision.get("target_asof") or TARGET_ASOF_FALLBACK)

    normalized_audits = [audit_normalized_root(path, target_asof) for path in discover_normalized_roots()]
    provider_audits = [audit_provider_root(path, target_asof) for path in discover_provider_roots()]
    ready_normalized = [row for row in normalized_audits if row["same_lineage_exact_target_ready"]]
    ready_provider = [row for row in provider_audits if row["same_lineage_provider_ready"]]

    decision = (
        "LOCAL_SAME_LINEAGE_YAHOO_ADJUSTED_PROVIDER_READY_FOR_DAPR3_VALIDATION"
        if ready_provider
        else "LOCAL_SAME_LINEAGE_YAHOO_ADJUSTED_NORMALIZED_READY_PROVIDER_BUILD_REQUIRED"
        if ready_normalized
        else "BLOCKED_NO_LOCAL_SAME_LINEAGE_YAHOO_ADJUSTED_EXACT_TARGET_CANDIDATE"
    )
    plan = build_provider_only_rerun_plan(target_asof)

    local_inventory = {
        "schema_version": "dapr7.local_same_lineage_yahoo_adjusted_inventory.v1",
        "created_at": created_at,
        "target_asof": target_asof,
        "dapr6_decision": dapr6_decision.get("decision"),
        "normalized_root_count": len(normalized_audits),
        "provider_root_count": len(provider_audits),
        "ready_normalized_count": len(ready_normalized),
        "ready_provider_count": len(ready_provider),
        "normalized_roots": normalized_audits,
        "provider_roots": provider_audits,
    }
    blocker = {
        "schema_version": "dapr7.same_lineage_bridge_blocker.v1",
        "created_at": created_at,
        "target_asof": target_asof,
        "decision": decision,
        "blocker_reasons": []
        if ready_provider
        else [
            "no local same-lineage Yahoo-adjusted provider root covers target_asof",
            "no local same-lineage Yahoo-adjusted normalized candidate covers 150/150 at target_asof"
            if not ready_normalized
            else "same-lineage normalized candidate exists but provider/bin build still required",
            "live Yahoo/Scrapling provider-only rerun is not executed in DAPR7 without explicit authorization",
        ],
        "provider_only_rerun_plan_path": rel(OUT_DIR / "provider_only_rerun_plan.json"),
    }
    decision_payload = {
        "schema_version": "dapr7.candidate_or_blocker_decision.v1",
        "created_at": created_at,
        "target_asof": target_asof,
        "decision": decision,
        "local_same_lineage_provider_ready": bool(ready_provider),
        "local_same_lineage_normalized_ready": bool(ready_normalized),
        "ready_for_model_a_no_publish_dry_run": False,
        "ready_for_latest_switch": False,
        "ready_for_provider_publish": False,
        "provider_only_live_rerun_executed": False,
        "next_required_action": (
            "validate local provider readiness against DAPR1"
            if ready_provider
            else "execute authorized provider-only Yahoo/Scrapling rerun using provider_only_rerun_plan.json"
        ),
        "forbidden_actions_all_false": True,
    }
    forbidden_action_audit = {
        "schema_version": "dapr.forbidden_action_audit.v1",
        "created_at": created_at,
        "route": "DAPR7_SAME_LINEAGE_YAHOO_ADJUSTED_EXACT_TARGET_BRIDGE_BUILD_NO_PUBLISH",
        "all_false": all(value is False for value in FORBIDDEN_ACTIONS.values()),
        "actions": FORBIDDEN_ACTIONS,
        "write_scope": [rel(OUT_DIR)],
        "provider_pull_allowed": False,
        "provider_pull_attempted": False,
        "provider_only_live_rerun_executed": False,
    }

    paths = [
        write_json("local_same_lineage_inventory.json", local_inventory),
        write_json("provider_only_rerun_plan.json", plan),
        write_json("candidate_or_blocker_decision.json", decision_payload),
        write_json("same_lineage_bridge_blocker.json", blocker),
        write_json("forbidden_action_audit.json", forbidden_action_audit),
    ]
    manifest = {
        "schema_version": "dapr.artifact_manifest.v1",
        "created_at": utc_now(),
        "artifact_manifest_status": "written",
        "route_decision": decision,
        "route_verdict": "BLOCKED_REQUIRES_EXPLICIT_PROVIDER_ONLY_RERUN_AUTHORIZATION"
        if not ready_provider
        else "LOCAL_PROVIDER_CANDIDATE_FOUND",
        "status": "pass",
        "entries": [
            {
                "path": rel(path),
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() else None,
                "sha256": sha256(path) if path.exists() else "",
            }
            for path in paths
        ],
    }
    write_json("artifact_manifest.json", manifest)
    return decision_payload


def main() -> int:
    result = build()
    print(
        "DAPR7 same-lineage Yahoo-adjusted bridge no-publish: "
        f"decision={result['decision']} target_asof={result['target_asof']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
