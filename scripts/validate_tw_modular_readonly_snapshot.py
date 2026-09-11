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


def resolve_listed_file(manifest_path: Path, listed_path: str) -> Path:
    p = Path(listed_path)
    if p.is_absolute():
        return p
    if listed_path.startswith("data_tw/"):
        return ROOT / p
    return manifest_path.parent / p


def checksum_file_entries(payload: dict[str, Any]) -> tuple[list[dict[str, str]], list[str]]:
    files = payload.get("files", [])
    errors: list[str] = []
    if isinstance(files, dict):
        return [{"path": str(path), "sha256": str(sha256)} for path, sha256 in files.items()], errors
    if isinstance(files, list):
        entries: list[dict[str, str]] = []
        for idx, item in enumerate(files):
            if not isinstance(item, dict):
                errors.append(f"files[{idx}] is not object")
                continue
            entries.append({"path": str(item.get("path", "")), "sha256": str(item.get("sha256", ""))})
        return entries, errors
    return [], ["files must be list or object"]


def check(name: str, ok: bool, details: str = "") -> dict[str, Any]:
    return {"name": name, "status": "pass" if ok else "fail", "details": details}


def nested_bool_false(payload: dict[str, Any], *keys: str) -> bool:
    seen = False
    for key in keys:
        values = payload.get(key, {})
        if not isinstance(values, dict) or not values:
            continue
        seen = True
        if any(value is not False for value in values.values()):
            return False
    return seen


def model_signal_source_ok(manifest_path: str, *, model_id: str) -> tuple[bool, str]:
    if not manifest_path:
        return False, "missing_source_signal_manifest"
    path = resolve(manifest_path)
    if not path.exists():
        return False, f"missing:{manifest_path}"
    try:
        payload = load_json(path)
    except Exception as exc:  # pragma: no cover - defensive detail for operator output
        return False, f"unreadable:{manifest_path}:{exc}"
    ok = (
        payload.get("artifact_type") == "ModelSignalArtifact"
        and payload.get("model_id") == model_id
        and payload.get("status") in {"READY", "PASS", "accepted"}
        and int(payload.get("row_count") or 0) >= 50
        and payload.get("production_allowed") is False
        and payload.get("not_published_latest") is True
        and payload.get("no_latest") is True
        and nested_bool_false(payload, "forbidden_actions", "governance_forbidden_actions")
    )
    details = "|".join(
        [
            str(payload.get("artifact_type")),
            str(payload.get("model_id")),
            str(payload.get("status")),
            str(payload.get("row_count")),
            str(payload.get("run_id")),
        ]
    )
    return ok, details


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
    entries, entry_errors = checksum_file_entries(payload)
    if entry_errors:
        return False, "|".join(entry_errors)
    if any(str(item.get("path", "")).endswith("checksum_manifest.json") for item in entries):
        return False, "checksum_manifest includes itself"
    bad = []
    for item in entries:
        path = resolve_listed_file(manifest_path, str(item.get("path", "")))
        if not path.exists() or sha256_file(path) != item.get("sha256"):
            bad.append(str(item.get("path", "")))
    if bad:
        return False, "|".join(bad)
    return bool(payload.get("validation", {}).get("ok", True)), f"checked={len(entries)}"


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
    forbidden_flags = forbidden_scope.get("flags", {}) if isinstance(forbidden_scope.get("flags", {}), dict) else {}
    model_id = str(manifest.get("model_id") or snapshot.get("model_id") or "")
    strategy_rule = str(manifest.get("strategy_rule") or snapshot.get("strategy_rule") or "")
    ranking_source = str(manifest.get("ranking_source") or snapshot.get("ranking_source") or "")
    source_signal_manifest = str(manifest.get("source_signal_manifest") or manifest.get("source_shadow_manifest", ""))
    source_model_signal_ok, source_model_signal_details = model_signal_source_ok(source_signal_manifest, model_id=model_id)
    known_contract_ok = (
        (
            model_id == "e4_frozen_qlib_2023_2025_ltr"
            and strategy_rule == "top50_exit_one_worst_sell"
            and ranking_source == "ltr_rerank_within_qlib_top50"
        )
        or (
            model_id == "e4_frozen_qlib_2018_2022"
            and strategy_rule == "candidate_only_no_strategy_replay"
            and ranking_source == "qlib_rank_controlled_signal"
            and source_signal_manifest == "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/manifest.json"
            and (manifest.get("candidate_boundary") or snapshot.get("candidate_boundary")) == "qlib_top50"
        )
        or (
            model_id == "e4_frozen_qlib_2018_2022"
            and strategy_rule == "candidate_only_no_strategy_replay"
            and ranking_source == "qlib_rank_controlled_signal"
            and source_model_signal_ok
            and (manifest.get("candidate_boundary") or snapshot.get("candidate_boundary")) == "qlib_top50"
        )
    )
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
        check("known_readonly_contract", known_contract_ok, f"{model_id}|{strategy_rule}|{ranking_source}|{source_signal_manifest}"),
        check(
            "source_signal_manifest",
            (
                "data_tw/artifacts/shadow_modular_daily/" in str(manifest.get("source_shadow_manifest", ""))
                or "data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/" in str(manifest.get("source_signal_manifest", ""))
                or source_signal_manifest == "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/manifest.json"
                or source_model_signal_ok
            ),
            source_model_signal_details,
        ),
        check(
            "source_signal_exists",
            resolve(str(manifest.get("source_signal_manifest") or manifest.get("source_shadow_manifest", ""))).exists(),
        ),
        check("candidate_boundary", snapshot.get("candidate_boundary") == "qlib_top50"),
        check("ranking_source", ranking_source in {"ltr_rerank_within_qlib_top50", "qlib_rank_controlled_signal"}, ranking_source),
        check("forbidden_scope_audit", forbidden_scope.get("status") == "pass", str(forbidden_scope.get("status"))),
        check("no_provider_publish", forbidden_scope.get("no_provider_publish") is True or forbidden_flags.get("provider_publish_triggered") is False),
        check(
            "no_accepted_latest_switch",
            forbidden_scope.get("no_accepted_latest_switch") is True
            or (
                forbidden_flags.get("provider_accepted_latest_switched") is False
                and forbidden_flags.get("qlib_accepted_latest_switched") is False
            ),
        ),
        check("no_monitor_broker_order", forbidden_scope.get("no_monitor_broker_order") is True or forbidden_flags.get("monitor_broker_order_triggered") is False),
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
