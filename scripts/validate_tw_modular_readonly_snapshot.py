#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LATEST = ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json"
ALLOWED_DISPLAY_ROLES = {"primary_readonly_candidate", "primary_baseline", "bridge_fresh_ltr", "bridge_frozen_short_ltr", "pure_frozen_baseline"}
FORBIDDEN_UNSAFE_KEYS = {
    "broker",
    "quick_trade",
    "quick-trade",
    "order_action",
    "target_position",
    "target-position",
    "targetposition",
    "target_weight",
    "target_qty",
    "target_quantity",
    "production_trade_instruction",
}


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


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check(name: str, ok: bool, details: str = "") -> dict[str, Any]:
    return {"name": name, "status": "pass" if ok else "fail", "details": details}


def contains_forbidden_key(obj: Any, path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            lowered = str(key).lower()
            if lowered in FORBIDDEN_UNSAFE_KEYS:
                hits.append(f"{path}.{key}" if path else str(key))
            hits.extend(contains_forbidden_key(value, f"{path}.{key}" if path else str(key)))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            hits.extend(contains_forbidden_key(value, f"{path}[{idx}]"))
    return hits


def validate_checksum(manifest_path: Path, manifest: dict[str, Any]) -> tuple[bool, str]:
    checksum_path = manifest_path.parent / str(manifest.get("checksum_manifest", ""))
    if not checksum_path.exists():
        return False, "checksum_manifest missing"
    payload = load_json(checksum_path)
    if any(str(item.get("path", "")).endswith("checksum_manifest.json") for item in payload.get("files", [])):
        return False, "checksum_manifest includes itself"
    bad = []
    for item in payload.get("files", []):
        path = resolve(str(item.get("path", "")))
        if not path.exists() or sha256_file(path) != item.get("sha256"):
            bad.append(str(item.get("path", "")))
    if bad:
        return False, "|".join(bad)
    return bool(payload.get("validation", {}).get("ok", True)), f"checked={len(payload.get('files', []))}"


def latest_pointer_ok(latest_path: Path, manifest_path: Path) -> tuple[bool, str]:
    if not latest_path.exists():
        return False, "latest pointer missing"
    latest = load_json(latest_path)
    ok = (
        latest.get("artifact_type") == "readonly_strategy_snapshot_latest_pointer"
        and latest.get("readonly_only") is True
        and latest.get("production_trade_enabled") is False
        and latest.get("not_provider_accepted_latest") is True
        and latest.get("not_trade_target_latest") is True
        and resolve(str(latest.get("snapshot_manifest", ""))).resolve() == manifest_path.resolve()
    )
    return ok, str(latest.get("snapshot_manifest", ""))


def validate_snapshot(manifest_path: Path, latest_path: Path | None = None) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    snapshot = load_json(manifest_path.parent / str(manifest.get("snapshot", "")))
    forbidden_scope = load_json(manifest_path.parent / str(manifest.get("forbidden_scope_audit", "")))
    checks = [
        check("artifact_type", manifest.get("artifact_type") == "readonly_strategy_snapshot", str(manifest.get("artifact_type"))),
        check("schema_version", manifest.get("schema_version") == "readonly_strategy_snapshot_r13_v1", str(manifest.get("schema_version"))),
        check("readonly_only", manifest.get("readonly_only") is True and snapshot.get("readonly_only") is True),
        check("production_trade_enabled_false", manifest.get("production_trade_enabled") is False),
        check("no_order_action", manifest.get("no_order_action") is True and snapshot.get("no_order_action") is True),
        check("not_target_position", manifest.get("not_target_position") is True and snapshot.get("not_target_position") is True),
        check("not_investment_advice", manifest.get("not_investment_advice") is True and snapshot.get("not_investment_advice") is True),
        check("is_production_trading_default_false", manifest.get("is_production_trading_default") is False and snapshot.get("is_production_trading_default") is False),
        check("display_role", manifest.get("display_role") in ALLOWED_DISPLAY_ROLES and snapshot.get("display_role") == manifest.get("display_role")),
        check("primary_display_contract", snapshot.get("model_id") == "e4_frozen_qlib_2023_2025_ltr" and snapshot.get("strategy_rule") == "top50_exit_one_worst_sell"),
        check(
            "source_signal_manifest",
            (
                "data_tw/artifacts/shadow_modular_daily/" in str(manifest.get("source_shadow_manifest", ""))
                or "data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/" in str(manifest.get("source_signal_manifest", ""))
            ),
            str(manifest.get("source_signal_manifest") or manifest.get("source_shadow_manifest", "")),
        ),
        check(
            "source_signal_exists",
            resolve(str(manifest.get("source_signal_manifest") or manifest.get("source_shadow_manifest", ""))).exists(),
        ),
        check("candidate_boundary", snapshot.get("candidate_boundary") == "qlib_top50"),
        check("ranking_source", snapshot.get("ranking_source") == "ltr_rerank_within_qlib_top50"),
        check("forbidden_scope_audit", forbidden_scope.get("status") == "pass", str(forbidden_scope.get("status"))),
        check("no_provider_publish", forbidden_scope.get("no_provider_publish") is True),
        check("no_accepted_latest_switch", forbidden_scope.get("no_accepted_latest_switch") is True),
        check("no_monitor_broker_order", forbidden_scope.get("no_monitor_broker_order") is True),
    ]
    unsafe_hits = contains_forbidden_key(manifest) + contains_forbidden_key(snapshot)
    checks.append(check("no_unsafe_field_names", not unsafe_hits, "|".join(unsafe_hits)))
    checksum_ok, checksum_details = validate_checksum(manifest_path, manifest)
    checks.append(check("checksum_ok", checksum_ok, checksum_details))
    latest_ok = True
    latest_details = "not requested"
    if latest_path is not None:
        latest_ok, latest_details = latest_pointer_ok(latest_path, manifest_path)
    checks.append(check("latest_pointer_points_to_readonly_snapshot_only", latest_ok, latest_details))
    ok = all(row["status"] == "pass" for row in checks)
    return {
        "ok": ok,
        "artifact": rel(manifest_path),
        "latest": rel(latest_path) if latest_path else "",
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate readonly modular strategy snapshot artifact.")
    parser.add_argument("--manifest", default="", help="Readonly snapshot manifest path")
    parser.add_argument("--latest", action="store_true", help="Validate the latest readonly snapshot pointer")
    parser.add_argument("--write-report", action="store_true", help="Write validation_report.json next to the manifest")
    parser.add_argument("--json", action="store_true", help="Print result JSON")
    args = parser.parse_args()

    latest_path = DEFAULT_LATEST if args.latest else None
    if args.latest:
        latest = load_json(DEFAULT_LATEST)
        manifest_path = resolve(str(latest["snapshot_manifest"]))
    elif args.manifest:
        manifest_path = resolve(args.manifest)
    else:
        raise SystemExit("--manifest or --latest is required")
    result = validate_snapshot(manifest_path, latest_path=latest_path)
    if args.write_report:
        report = {
            "artifact_type": "readonly_strategy_snapshot_validation_report",
            "schema_version": "readonly_strategy_snapshot_validation_r13_v1",
            "status": "pass" if result["ok"] else "fail",
            **result,
        }
        write_json(manifest_path.parent / "validation_report.json", report)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']}")
        print(f"artifact={result['artifact']}")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
