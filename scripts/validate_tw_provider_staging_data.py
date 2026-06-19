#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_SOURCE_IDS = {
    "yahoo_daily_price",
    "finmind_institutional_flow",
    "finmind_margin_short",
    "orthogonal_o2_features",
    "existing_signal_manifest",
}
ALLOWED_PROVIDER_HOSTS = {"query1.finance.yahoo.com", "api.finmindtrade.com"}

REQUIRED_SOURCE_FIELDS = [
    "source_id",
    "provider",
    "required",
    "required_fields",
    "expected_asof",
    "actual_latest_asof",
    "available_at",
    "coverage_count",
    "coverage_ratio",
    "write_path",
    "failure_reason",
    "retryable",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def err(code: str, message: str, path: Path, field: str = "") -> dict[str, str]:
    return {"code": code, "message": message, "path": rel(path), "field": field}


def parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.fromisoformat(value + "T00:00:00+00:00")
        except ValueError:
            return None


def validate(staging_dir: Path) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    manifest_path = staging_dir / "provider_staging_pull_manifest.json"
    if not manifest_path.exists():
        return {"ok": False, "status": "failed", "errors": [err("pull_manifest_missing", "provider staging pull manifest missing", manifest_path)], "warnings": warnings}
    manifest = load_json(manifest_path)
    if manifest.get("staging_only") is not True:
        errors.append(err("not_staging_only", "provider pull must be staging_only", manifest_path, "staging_only"))
    sources = manifest.get("sources") or []
    source_ids = {str(source.get("source_id")) for source in sources}
    missing_required = sorted(REQUIRED_SOURCE_IDS - source_ids)
    scenario = str(manifest.get("scenario", ""))
    if missing_required:
        errors.append(err("required_source_missing", f"required sources missing: {missing_required}", manifest_path, "sources"))
    decision_cutoff = parse_dt(str(manifest.get("decision_cutoff", "")))
    for index, source in enumerate(sources):
        field_prefix = f"sources[{index}]"
        for field in REQUIRED_SOURCE_FIELDS:
            if field not in source:
                errors.append(err("source_field_missing", f"{field} is required", manifest_path, f"{field_prefix}.{field}"))
        source_path = ROOT / str(source.get("write_path", "")) / "source_status.json"
        if not source_path.exists():
            errors.append(err("source_status_missing", "source_status.json missing", source_path))
        if bool(source.get("required")) and not source.get("required_fields"):
            errors.append(err("required_fields_missing", "required source must list required_fields", manifest_path, f"{field_prefix}.required_fields"))
        if bool(source.get("required")) and source.get("status") == "ready" and float(source.get("coverage_ratio") or 0) < 0.8:
            errors.append(err("coverage_ratio_below_threshold", "required ready source coverage_ratio below 0.8", manifest_path, f"{field_prefix}.coverage_ratio"))
        available_at = parse_dt(str(source.get("available_at", "")))
        if bool(source.get("required")) and available_at and decision_cutoff and available_at > decision_cutoff:
            errors.append(err("available_at_after_decision_cutoff", "available_at must be <= decision_cutoff", manifest_path, f"{field_prefix}.available_at"))
        if bool(source.get("required")) and source.get("pit_audit_passed") is False:
            errors.append(err("orthogonal_pit_audit_failed", "required source PIT audit failed", manifest_path, f"{field_prefix}.pit_audit_passed"))
        if bool(source.get("required")) and source.get("symbol_mapping_ready") is False:
            errors.append(err("symbol_mapping_missing", "symbol mapping/universe mapping missing", manifest_path, f"{field_prefix}.symbol_mapping_ready"))
    audit_path = staging_dir / "forbidden_action_audit.json"
    if not audit_path.exists():
        errors.append(err("forbidden_action_audit_missing", "forbidden action audit missing", audit_path))
    else:
        actions = (load_json(audit_path).get("actions") or {})
        for key, value in actions.items():
            if value is True:
                errors.append(err("forbidden_action_triggered", f"{key} must be false", audit_path, key))
    mode = str(manifest.get("mode") or manifest.get("scenario") or "")
    if mode == "external_provider_reader":
        audit_ref = str(manifest.get("provider_network_audit") or "")
        network_path = ROOT / audit_ref if audit_ref else staging_dir / "external_provider_fetch" / "provider_network_audit.json"
        if not network_path.exists():
            errors.append(err("provider_network_audit_missing", "external provider mode requires provider_network_audit.json", network_path, "provider_network_audit"))
        else:
            network = load_json(network_path)
            if int(network.get("actual_external_request_count") or 0) <= 0:
                errors.append(err("provider_network_request_missing", "external provider mode must send at least one audited external request", network_path, "actual_external_request_count"))
            if int(network.get("unauthorized_request_count") or 0) != 0:
                errors.append(err("provider_network_unauthorized_request", "provider network audit contains unauthorized domains", network_path, "unauthorized_request_count"))
            hosts = {str(row.get("host") or "") for row in (network.get("requests") or [])}
            unauthorized_hosts = sorted(host for host in hosts if host and host not in ALLOWED_PROVIDER_HOSTS)
            if unauthorized_hosts:
                errors.append(err("provider_network_host_not_allowlisted", f"unauthorized provider hosts: {unauthorized_hosts}", network_path, "requests.host"))
            request_sources = {str(row.get("source_id") or "") for row in (network.get("requests") or [])}
            for required_network_source in ["yahoo_daily_price", "finmind_daily_price", "finmind_institutional_flow", "finmind_margin_short"]:
                if required_network_source not in request_sources:
                    errors.append(err("provider_network_source_missing", f"missing audited request for {required_network_source}", network_path, required_network_source))
            network_forbidden = ((network.get("forbidden_action_audit") or {}).get("actions") or {})
            price_policy = manifest.get("price_source_policy") or {}
            if price_policy.get("policy") == "preferred_yahoo_fallback_finmind":
                yahoo = next((s for s in sources if s.get("source_id") == "yahoo_daily_price"), {})
                finmind = next((s for s in sources if s.get("source_id") == "finmind_daily_price"), {})
                if yahoo.get("fallback_used") is True:
                    if yahoo.get("status") != "ready":
                        errors.append(err("price_fallback_not_ready", "fallback-used yahoo price layer must be ready", manifest_path, "sources.yahoo_daily_price.status"))
                    if yahoo.get("fallback_source_id") != "finmind_daily_price":
                        errors.append(err("price_fallback_source_invalid", "fallback source must be finmind_daily_price", manifest_path, "sources.yahoo_daily_price.fallback_source_id"))
                    if finmind.get("status") != "ready":
                        errors.append(err("price_fallback_finmind_not_ready", "FinMind fallback source must be ready", manifest_path, "sources.finmind_daily_price.status"))
                    if price_policy.get("fallback_used") is not True:
                        errors.append(err("price_fallback_manifest_missing", "manifest price_source_policy must record fallback_used=true", manifest_path, "price_source_policy.fallback_used"))
            for key, value in network_forbidden.items():
                if value is True:
                    errors.append(err("provider_network_forbidden_action", f"{key} must be false in provider network audit", network_path, key))
    ok = not errors
    return {"ok": ok, "status": "passed" if ok else "failed", "schema_version": "v1.provider_staging_validator.v1", "staging_dir": rel(staging_dir), "errors": errors, "warnings": warnings}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase V1 provider staging pull outputs.")
    parser.add_argument("--staging-dir", "--artifact-path", dest="staging_dir", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    staging_dir = Path(args.staging_dir)
    if not staging_dir.is_absolute():
        staging_dir = ROOT / staging_dir
    result = validate(staging_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else f"ok={result['ok']}\nstatus={result['status']}")
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
