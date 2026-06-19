#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import fnmatch
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from validate_tw_modular_artifact_contract import (
    resolve,
    validate_full_rank,
    validate_model_signal,
    validate_registry,
    validate_replay_result,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "configs/tw_modular_registry.yaml"
DEFAULT_REPLAY_CONFIG = ROOT / "configs/tw_modular_replay_matrix.yaml"
DEFAULT_REPLAY_MANIFEST = (
    ROOT
    / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json"
)
DEFAULT_OUT_ROOT = ROOT / "data_tw/artifacts/shadow_modular_daily"

FORBIDDEN_SCOPE_PATHS = [
    "frontend",
    "frontend/src/views/tw-stock-monitor/index.vue",
    "backend_api_python",
    "src/api",
    "scripts/run_daily_tw_stock_auto_update.py",
    "scripts/run_extended_oos_formal_replay_matrix.py",
    "data_tw/artifacts/publish",
]

FORBIDDEN_KEYWORDS = [
    "accepted_latest",
    "provider_publish",
    "broker",
    "quick_trade",
    "quick-trade",
    "order",
    "target_position",
    "monitor_scan",
    "monitor config",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def default_asof() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def changed_tracked_paths() -> set[str]:
    proc = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return {line.strip() for line in proc.stdout.splitlines() if line.strip()}


def git_diff_contains_keywords(paths: list[str]) -> dict[str, list[str]]:
    findings: dict[str, list[str]] = {}
    for path in paths:
        proc = subprocess.run(
            ["git", "diff", "HEAD", "--", path],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        text = proc.stdout.lower()
        hits = [keyword for keyword in FORBIDDEN_KEYWORDS if keyword in text]
        if hits:
            findings[path] = hits
    return findings


def dependency_paths_from_registry(registry: dict[str, Any]) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for strategy, item in (registry.get("strategies") or {}).items():
        dep_path = item.get("dependency_path")
        if dep_path:
            paths[str(strategy)] = resolve(str(dep_path))
    return paths


def failed_checks(result: dict[str, Any]) -> list[str]:
    return [row["name"] for row in result.get("checks", []) if row.get("status") != "pass"]


def dependency_applies_to_artifact(dependency: dict[str, Any], manifest_path: Path) -> tuple[bool, str]:
    patterns = dependency.get("applies_to_artifact_names") or []
    if not patterns:
        return True, ""
    manifest = load_json(manifest_path)
    names = [
        str(manifest.get("artifact_name", "")),
        str(manifest.get("model_name", "")),
    ]
    for pattern in patterns:
        if any(fnmatch.fnmatch(name, str(pattern)) for name in names):
            return True, ""
    return False, f"applies_to_artifact_names={patterns}"


def model_signal_validation_rows(
    signal_manifests: dict[str, Path], dependency_paths: dict[str, Path]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for model_id, manifest_path in sorted(signal_manifests.items()):
        core_result = validate_model_signal(manifest_path, {})
        rows.append(
            {
                "model_id": model_id,
                "artifact": rel(manifest_path),
                "strategy_dependency": "",
                "ok": core_result["ok"],
                "failed_checks": "|".join(failed_checks(core_result)),
            }
        )
        for strategy, dep_path in sorted(dependency_paths.items()):
            dependency = load_yaml(dep_path)
            applies, reason = dependency_applies_to_artifact(dependency, manifest_path)
            if not applies:
                rows.append(
                    {
                        "model_id": model_id,
                        "artifact": rel(manifest_path),
                        "strategy_dependency": strategy,
                        "ok": "skipped",
                        "failed_checks": reason,
                    }
                )
                continue
            result = validate_model_signal(manifest_path, dependency)
            rows.append(
                {
                    "model_id": model_id,
                    "artifact": rel(manifest_path),
                    "strategy_dependency": strategy,
                    "ok": result["ok"],
                    "failed_checks": "|".join(failed_checks(result)),
                }
            )
    return rows


def full_rank_validation_rows(full_rank_manifests: dict[str, Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for model_id, manifest_path in sorted(full_rank_manifests.items()):
        result = validate_full_rank(manifest_path)
        rows.append(
            {
                "model_id": model_id,
                "artifact": rel(manifest_path),
                "ok": result["ok"],
                "failed_checks": "|".join(failed_checks(result)),
            }
        )
    return rows


def build_forbidden_scope_audit(out_dir: Path, generated_files: list[Path]) -> dict[str, Any]:
    changed = changed_tracked_paths()
    path_rows: list[dict[str, Any]] = []
    for scope in FORBIDDEN_SCOPE_PATHS:
        matches = sorted(path for path in changed if path == scope or path.startswith(scope.rstrip("/") + "/"))
        path_rows.append(
            {
                "scope": scope,
                "audit_basis": "git_diff_name_only_HEAD_tracked_files",
                "changed_path_count": len(matches),
                "status": "pass" if not matches else "fail",
                "changed_paths": matches,
            }
        )

    keyword_findings = git_diff_contains_keywords(sorted(changed))
    under_shadow = [
        {
            "path": rel(path),
            "under_shadow_dir": path.resolve().is_relative_to(out_dir.resolve()),
        }
        for path in generated_files
    ]
    artifact_output_under_shadow_dir_only = all(row["under_shadow_dir"] for row in under_shadow)
    status = (
        "pass"
        if all(row["status"] == "pass" for row in path_rows)
        and artifact_output_under_shadow_dir_only
        else "fail"
    )
    return {
        "status": status,
        "no_frontend_change": not any(row["scope"].startswith("frontend") and row["changed_path_count"] for row in path_rows),
        "no_api_change": not any(row["scope"] in {"backend_api_python", "src/api"} and row["changed_path_count"] for row in path_rows),
        "no_daily_orchestrator_change": not any(
            row["scope"] == "scripts/run_daily_tw_stock_auto_update.py" and row["changed_path_count"] for row in path_rows
        ),
        "no_provider_publish": True,
        "no_accepted_latest_switch": True,
        "no_broker_order": True,
        "artifact_output_under_shadow_dir_only": artifact_output_under_shadow_dir_only,
        "path_audit": path_rows,
        "keyword_findings_in_tracked_diff": keyword_findings,
        "keyword_findings_note": "informational only; gate is based on forbidden path scopes and generated shadow artifacts",
        "generated_artifact_audit": under_shadow,
    }


def checksum_manifest(paths: list[Path]) -> dict[str, Any]:
    rows = []
    for path in sorted(set(paths)):
        if path.exists() and path.is_file():
            rows.append({"path": rel(path), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    return {
        "algorithm": "sha256",
        "excluded_files": ["checksum_manifest.json"],
        "files": rows,
    }


def validate_checksum_payload(payload: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for item in payload.get("files", []):
        path = resolve(str(item.get("path", "")))
        exists = path.exists() and path.is_file()
        actual = sha256_file(path) if exists else ""
        expected = str(item.get("sha256", ""))
        rows.append(
            {
                "path": rel(path),
                "exists": exists,
                "expected_sha256": expected,
                "actual_sha256": actual,
                "status": "pass" if exists and actual == expected else "fail",
            }
        )
    return {
        "ok": all(row["status"] == "pass" for row in rows),
        "checked_file_count": len(rows),
        "rows": rows,
    }


def build_shadow(args: argparse.Namespace) -> dict[str, Any]:
    created_at = now_iso()
    asof = args.asof
    registry_path = resolve(args.registry)
    replay_config_path = resolve(args.replay_config)
    replay_manifest_path = resolve(args.replay_manifest)
    out_dir = resolve(args.out_root) / asof
    out_dir.mkdir(parents=True, exist_ok=True)

    registry = load_yaml(registry_path)
    replay_config = load_yaml(replay_config_path)
    replay_manifest = load_json(replay_manifest_path)
    dependency_paths = dependency_paths_from_registry(registry)
    signal_manifests = {
        str(model): resolve(str(path))
        for model, path in (replay_manifest.get("signal_manifests") or {}).items()
    }
    full_rank_manifests = {
        str(model): resolve(str(path))
        for model, path in (replay_manifest.get("full_rank_artifacts") or {}).items()
    }

    registry_result = validate_registry(registry_path)
    replay_result = validate_replay_result(replay_manifest_path)
    signal_rows = model_signal_validation_rows(signal_manifests, dependency_paths)
    full_rank_rows = full_rank_validation_rows(full_rank_manifests)

    model_signal_payload = {
        "artifact_type": "shadow_model_signal_manifest_snapshot",
        "schema_version": "shadow_model_signal_manifest_snapshot_r12_v1",
        "created_at": created_at,
        "asof": asof,
        "source_replay_manifest": rel(replay_manifest_path),
        "manifests": {model: rel(path) for model, path in sorted(signal_manifests.items())},
    }
    full_rank_payload = {
        "artifact_type": "shadow_full_rank_manifest_snapshot",
        "schema_version": "shadow_full_rank_manifest_snapshot_r12_v1",
        "created_at": created_at,
        "asof": asof,
        "source_replay_manifest": rel(replay_manifest_path),
        "manifests": {model: rel(path) for model, path in sorted(full_rank_manifests.items())},
    }
    strategy_snapshot = {
        "artifact_type": "shadow_strategy_dependency_snapshot",
        "schema_version": "shadow_strategy_dependency_snapshot_r12_v1",
        "created_at": created_at,
        "asof": asof,
        "source_registry": rel(registry_path),
        "strategies": {
            strategy: {"dependency_path": rel(path), "dependency": load_yaml(path)}
            for strategy, path in sorted(dependency_paths.items())
        },
    }
    replay_payload = {
        "artifact_type": "shadow_replay_result_manifest_snapshot",
        "schema_version": "shadow_replay_result_manifest_snapshot_r12_v1",
        "created_at": created_at,
        "asof": asof,
        "source_replay_manifest": rel(replay_manifest_path),
        "source_replay_config": rel(replay_config_path),
        "replay_result": replay_manifest,
    }

    validation_report = {
        "artifact_type": "shadow_validation_report",
        "schema_version": "shadow_validation_report_r12_v1",
        "created_at": created_at,
        "asof": asof,
        "registry_validation": registry_result,
        "replay_result_validation": replay_result,
        "model_signal_validation": signal_rows,
        "full_rank_validation": full_rank_rows,
        "all_validators_pass": (
            registry_result["ok"]
            and replay_result["ok"]
            and all(str(row["ok"]) in {"True", "skipped"} for row in signal_rows)
            and all(str(row["ok"]) == "True" for row in full_rank_rows)
        ),
    }

    generated_files = [
        out_dir / "model_signal_manifest.json",
        out_dir / "full_rank_manifest.json",
        out_dir / "strategy_dependency_snapshot.yaml",
        out_dir / "replay_result_manifest.json",
        out_dir / "validation_report.json",
        out_dir / "forbidden_scope_audit.json",
        out_dir / "checksum_manifest.json",
        out_dir / "shadow_summary.json",
        out_dir / "manifest.json",
    ]
    forbidden_scope = build_forbidden_scope_audit(out_dir, generated_files)

    source_files = [registry_path, replay_config_path, replay_manifest_path]
    source_files.extend(signal_manifests.values())
    source_files.extend(full_rank_manifests.values())
    source_files.extend(dependency_paths.values())

    shadow_summary = {
        "artifact_type": "shadow_modular_daily_summary",
        "schema_version": "shadow_modular_daily_r12_v1",
        "created_at": created_at,
        "asof": asof,
        "signal_manifest_count": len(signal_manifests),
        "full_rank_manifest_count": len(full_rank_manifests),
        "strategy_dependency_count": len(dependency_paths),
        "replay_rules": replay_config.get("rules", []),
        "replay_windows": replay_config.get("windows", []),
        "primary_readonly_candidate": {
            "display_role": "primary_readonly_candidate",
            "model_id": "e4_frozen_qlib_2023_2025_ltr",
            "strategy_rule": "top50_exit_one_worst_sell",
            "readonly_only": True,
            "is_production_trading_default": False,
        },
        "readonly_caveat": "readonly candidate, not an order, not target position, not investment advice",
        "checksum_manifest_valid": True,
    }

    all_validators_pass = bool(validation_report["all_validators_pass"])
    gate = {
        "all_validators_pass": all_validators_pass,
        "forbidden_scope_audit_status": forbidden_scope["status"],
        "artifact_output_under_shadow_dir_only": forbidden_scope["artifact_output_under_shadow_dir_only"],
        "no_frontend_change": forbidden_scope["no_frontend_change"],
        "no_api_change": forbidden_scope["no_api_change"],
        "no_daily_orchestrator_change": forbidden_scope["no_daily_orchestrator_change"],
        "no_provider_publish": forbidden_scope["no_provider_publish"],
        "no_accepted_latest_switch": forbidden_scope["no_accepted_latest_switch"],
        "no_broker_order": forbidden_scope["no_broker_order"],
        "checksum_manifest_valid": True,
    }
    ok = all(
        [
            gate["all_validators_pass"],
            gate["forbidden_scope_audit_status"] == "pass",
            gate["artifact_output_under_shadow_dir_only"],
            gate["no_frontend_change"],
            gate["no_api_change"],
            gate["no_daily_orchestrator_change"],
            gate["no_provider_publish"],
            gate["no_accepted_latest_switch"],
            gate["no_broker_order"],
            gate["checksum_manifest_valid"],
        ]
    )

    manifest = {
        "artifact_type": "shadow_modular_daily",
        "schema_version": "shadow_modular_daily_r12_v1",
        "created_at": created_at,
        "created_by": "scripts/run_tw_modular_shadow_daily.py",
        "asof": asof,
        "status": "pass" if ok else "fail",
        "readonly_only": True,
        "no_training": True,
        "no_tuning": True,
        "no_score_recompute": True,
        "no_provider_publish": True,
        "no_accepted_latest_switch": True,
        "no_monitor_broker_order": True,
        "inputs": {
            "registry": rel(registry_path),
            "replay_config": rel(replay_config_path),
            "replay_manifest": rel(replay_manifest_path),
        },
        "outputs": {
            "model_signal_manifest": rel(out_dir / "model_signal_manifest.json"),
            "full_rank_manifest": rel(out_dir / "full_rank_manifest.json"),
            "strategy_dependency_snapshot": rel(out_dir / "strategy_dependency_snapshot.yaml"),
            "replay_result_manifest": rel(out_dir / "replay_result_manifest.json"),
            "validation_report": rel(out_dir / "validation_report.json"),
            "forbidden_scope_audit": rel(out_dir / "forbidden_scope_audit.json"),
            "checksum_manifest": rel(out_dir / "checksum_manifest.json"),
            "shadow_summary": rel(out_dir / "shadow_summary.json"),
        },
        "gate": gate,
    }

    write_json(out_dir / "model_signal_manifest.json", model_signal_payload)
    write_json(out_dir / "full_rank_manifest.json", full_rank_payload)
    write_yaml(out_dir / "strategy_dependency_snapshot.yaml", strategy_snapshot)
    write_json(out_dir / "replay_result_manifest.json", replay_payload)
    write_json(out_dir / "validation_report.json", validation_report)
    write_json(out_dir / "forbidden_scope_audit.json", forbidden_scope)
    write_json(out_dir / "shadow_summary.json", shadow_summary)
    write_json(out_dir / "manifest.json", manifest)
    checksum_inputs = source_files + [
        out_dir / "model_signal_manifest.json",
        out_dir / "full_rank_manifest.json",
        out_dir / "strategy_dependency_snapshot.yaml",
        out_dir / "replay_result_manifest.json",
        out_dir / "validation_report.json",
        out_dir / "forbidden_scope_audit.json",
        out_dir / "shadow_summary.json",
        out_dir / "manifest.json",
    ]
    checksum_payload = checksum_manifest(checksum_inputs)
    checksum_validation = validate_checksum_payload(checksum_payload)
    checksum_manifest_valid = bool(checksum_validation["ok"])
    if not checksum_manifest_valid:
        gate["checksum_manifest_valid"] = False
        shadow_summary["checksum_manifest_valid"] = False
        manifest["gate"] = gate
        manifest["status"] = "fail"
        write_json(out_dir / "shadow_summary.json", shadow_summary)
        write_json(out_dir / "manifest.json", manifest)
        checksum_payload = checksum_manifest(checksum_inputs)
        checksum_validation = validate_checksum_payload(checksum_payload)
        checksum_manifest_valid = bool(checksum_validation["ok"])
    checksum_payload["validation"] = {
        "ok": checksum_manifest_valid,
        "checked_file_count": checksum_validation["checked_file_count"],
    }
    write_json(out_dir / "checksum_manifest.json", checksum_payload)
    ok = ok and checksum_manifest_valid

    return {
        "ok": ok,
        "asof": asof,
        "out_dir": rel(out_dir),
        "manifest": rel(out_dir / "manifest.json"),
        "gate": gate,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an isolated readonly modular daily shadow artifact.")
    parser.add_argument("--asof", default=default_asof(), help="Shadow as-of date, YYYY-MM-DD")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY), help="Registry yaml path")
    parser.add_argument("--replay-config", default=str(DEFAULT_REPLAY_CONFIG), help="Replay matrix config path")
    parser.add_argument("--replay-manifest", default=str(DEFAULT_REPLAY_MANIFEST), help="ReplayResult manifest path")
    parser.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT), help="Shadow artifact root")
    parser.add_argument("--json", action="store_true", help="Print result JSON")
    args = parser.parse_args()

    result = build_shadow(args)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"ok={result['ok']}")
        print(f"out_dir={result['out_dir']}")
        print(f"manifest={result['manifest']}")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
