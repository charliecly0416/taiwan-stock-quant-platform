#!/usr/bin/env python3
"""Controlled publish/rollback gate for Option C Yahoo Scrapling staged refresh.

Step 3A supports a dry-run publish audit first. In dry-run-publish mode this
script does not mutate formal normalized/provider paths; it validates the staged
job, records backup/publish/rollback plans, runs daily signal dry-run only, and
verifies latest_signal.json remains unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.tw.run_option_c_yahoo_scrapling_refresh import (  # noqa: E402
    accepted_prediction_universe,
    artifact_manifest,
    rebuild_staged_provider,
    rel,
    staged_model_smoke,
    validate_normalized,
    validate_provider,
    write_json,
)

OPS_ROOT = ROOT / "data_tw/experiments/option_c_ops"
LEGACY_FORMAL_NORMALIZED = ROOT / "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"
LEGACY_FORMAL_PROVIDER = ROOT / "data_tw/experiments/yahoo_adjusted_primary/qlib_bin"
OPTION_C_FORMAL_NORMALIZED = ROOT / "data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized"
OPTION_C_FORMAL_PROVIDER = ROOT / "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin"
LATEST_SIGNAL = ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json"
DEFAULT_REPORT_PATH = ROOT / "docs/tw_audit/168_option_c_yahoo_scrapling_publish_rollback_report.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def path_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": rel(path), "exists": False, "file_count": 0, "total_bytes": 0}
    files = [p for p in path.rglob("*") if p.is_file()] if path.is_dir() else [path]
    return {
        "path": rel(path),
        "exists": True,
        "file_count": len(files),
        "total_bytes": sum(p.stat().st_size for p in files),
        "sample": [rel(p) for p in files[:20]],
    }


def file_fingerprint(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {"exists": False, "path": rel(path)}
    return {"exists": True, "path": rel(path), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_job_dir(raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    return path


def provider_paths(scope: str) -> dict[str, Path]:
    if scope != "option_c_150":
        raise ValueError("Step 3A only allows provider-scope option_c_150 in this script")
    return {
        "formal_normalized": OPTION_C_FORMAL_NORMALIZED,
        "formal_provider": OPTION_C_FORMAL_PROVIDER,
        "legacy_formal_normalized": LEGACY_FORMAL_NORMALIZED,
        "legacy_formal_provider": LEGACY_FORMAL_PROVIDER,
    }


def validate_staged_job(job_dir: Path, asof: str) -> dict[str, Any]:
    reports = job_dir / "reports"
    required = {
        "execution_summary": reports / "execution_summary.json",
        "fetch": reports / "fetch_report.json",
        "normalized_validation": reports / "normalized_validation.json",
        "provider_validation": reports / "provider_validation.json",
        "model_smoke": reports / "model_smoke.json",
        "artifact_manifest": reports / "artifact_manifest.json",
    }
    missing = [name for name, path in required.items() if not path.exists()]
    payload = {name: read_json(path) for name, path in required.items() if path.exists()}
    errors: list[str] = []
    if missing:
        errors.append(f"missing_reports:{','.join(missing)}")
    execution = payload.get("execution_summary", {})
    fetch = payload.get("fetch", {})
    normalized = payload.get("normalized_validation", {})
    provider = payload.get("provider_validation", {})
    smoke = payload.get("model_smoke", {})
    if execution.get("status") != "staged_refresh_complete_waiting_for_review":
        errors.append("execution_status_not_ready")
    if execution.get("asof") != asof:
        errors.append("execution_asof_mismatch")
    if execution.get("formal_provider_mutated") is not False:
        errors.append("staged_job_formal_provider_mutated")
    if execution.get("latest_signal_updated") is not False:
        errors.append("staged_job_latest_signal_updated")
    if fetch.get("status") != "pass":
        errors.append("fetch_not_pass")
    if fetch.get("symbols_expected") != 150 or fetch.get("symbols_success") != 150:
        errors.append("fetch_symbol_count_not_150")
    if fetch.get("symbols_failed") not in ({}, None):
        errors.append("fetch_failed_symbols_present")
    if normalized.get("status") != "pass":
        errors.append("normalized_not_pass")
    if normalized.get("missing_asof_count") != 0:
        errors.append("normalized_missing_asof")
    if provider.get("status") != "pass":
        errors.append("provider_not_pass")
    if smoke.get("status") != "pass":
        errors.append("model_smoke_not_pass")
    if smoke.get("prediction_rows") != 150 or smoke.get("finite_prediction_share") != 1.0:
        errors.append("model_smoke_prediction_contract_failed")
    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "job_dir": rel(job_dir),
        "reports": {name: rel(path) for name, path in required.items()},
        "summary": {
            "execution_status": execution.get("status"),
            "asof": execution.get("asof"),
            "symbols_success": fetch.get("symbols_success"),
            "symbols_expected": fetch.get("symbols_expected"),
            "normalized_status": normalized.get("status"),
            "provider_status": provider.get("status"),
            "model_smoke_status": smoke.get("status"),
            "prediction_rows": smoke.get("prediction_rows"),
            "finite_prediction_share": smoke.get("finite_prediction_share"),
        },
    }


def build_backup_plan(paths: dict[str, Path], publish_dir: Path) -> dict[str, Any]:
    return {
        "status": "planned",
        "backup_root": rel(publish_dir / "backup"),
        "provider_scope": "option_c_150",
        "strategy": "Option C dedicated 150-symbol provider; legacy wider provider is not overwritten",
        "sources": {
            "option_c_formal_normalized": path_summary(paths["formal_normalized"]),
            "option_c_formal_provider": path_summary(paths["formal_provider"]),
            "legacy_formal_normalized_observed_only": path_summary(paths["legacy_formal_normalized"]),
            "legacy_formal_provider_observed_only": path_summary(paths["legacy_formal_provider"]),
        },
    }


def copytree_replace(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def dir_sha256_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "files": [], "file_count": 0, "total_bytes": 0}
    files = []
    total_bytes = 0
    for item in sorted(path.rglob("*")):
        if not item.is_file():
            continue
        size = item.stat().st_size
        total_bytes += size
        files.append({"path": rel(item), "size_bytes": size, "sha256": sha256_file(item)})
    return {"exists": True, "file_count": len(files), "total_bytes": total_bytes, "files": files}


def backup_source(name: str, src: Path, dst: Path) -> dict[str, Any]:
    if not src.exists():
        return {
            "name": name,
            "status": "source_missing_first_publish",
            "source": rel(src),
            "backup": rel(dst),
            "source_summary": path_summary(src),
            "backup_manifest": {"exists": False, "files": [], "file_count": 0, "total_bytes": 0},
        }
    copytree_replace(src, dst)
    return {
        "name": name,
        "status": "created",
        "source": rel(src),
        "backup": rel(dst),
        "source_summary": path_summary(src),
        "backup_summary": path_summary(dst),
        "backup_manifest": dir_sha256_manifest(dst),
    }


def atomic_publish_dir(src: Path, dst: Path, tmp_dst: Path) -> dict[str, Any]:
    remove_path(tmp_dst)
    shutil.copytree(src, tmp_dst)
    old_dst = dst.parent / f".{dst.name}.old_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    remove_path(old_dst)
    if dst.exists():
        dst.rename(old_dst)
    try:
        tmp_dst.rename(dst)
    except Exception:
        if old_dst.exists() and not dst.exists():
            old_dst.rename(dst)
        raise
    remove_path(old_dst)
    return {"status": "published", "source": rel(src), "target": rel(dst), "summary": path_summary(dst)}


def run_daily_signal_dry_run(asof: str, publish_dir: Path) -> dict[str, Any]:
    before = file_fingerprint(LATEST_SIGNAL)
    cmd = [sys.executable, "examples/tw/run_option_c_daily_signal_option_c_provider.py", "--asof", asof, "--dry-run"]
    result = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    after = file_fingerprint(LATEST_SIGNAL)
    stdout_path = publish_dir / "reports/daily_signal_dry_run_stdout.txt"
    stderr_path = publish_dir / "reports/daily_signal_dry_run_stderr.txt"
    stdout_path.write_text(result.stdout, encoding="utf-8")
    stderr_path.write_text(result.stderr, encoding="utf-8")
    latest_unchanged = before == after
    status = "pass" if result.returncode == 0 and '"status": "dry_run_preflight_pass"' in result.stdout and latest_unchanged else "fail"
    return {
        "status": status,
        "command": " ".join(cmd),
        "returncode": result.returncode,
        "stdout_path": rel(stdout_path),
        "stderr_path": rel(stderr_path),
        "stdout_tail": result.stdout[-1200:],
        "stderr_tail": result.stderr[-1200:],
        "latest_before": before,
        "latest_after": after,
        "latest_signal_unchanged": latest_unchanged,
        "normal_signal_run": False,
    }


def execute_publish(args: argparse.Namespace, publish_dir: Path, paths: dict[str, Path]) -> dict[str, Any]:
    candidate_dir = resolve_job_dir(args.job_dir) / "candidate_normalized"
    formal_normalized = paths["formal_normalized"]
    formal_provider = paths["formal_provider"]
    tmp_root = publish_dir / "tmp"
    tmp_normalized = tmp_root / "formal_normalized_publish"
    tmp_provider = tmp_root / "formal_provider_rebuild"
    tmp_provider_publish = tmp_root / "formal_provider_publish"
    backup_root = publish_dir / "backup"
    backup_root.mkdir(parents=True, exist_ok=True)
    backup = build_backup_plan(paths, publish_dir)
    backup["status"] = "completed"
    backup["results"] = {
        "formal_normalized": backup_source("formal_normalized", formal_normalized, backup_root / "formal_normalized"),
        "formal_provider": backup_source("formal_provider", formal_provider, backup_root / "formal_provider"),
    }
    write_json(publish_dir / "reports/backup_report.json", backup)
    normalized_publish = atomic_publish_dir(candidate_dir, formal_normalized, tmp_normalized)
    rebuild = rebuild_staged_provider(formal_normalized, tmp_provider, args.max_workers)
    symbols = accepted_prediction_universe()
    provider_validation = validate_provider(tmp_provider, symbols, args.asof)
    if provider_validation.get("status") != "pass":
        return {"status": "failed_before_provider_publish", "backup": backup, "normalized_publish": normalized_publish, "provider_rebuild": rebuild, "provider_validation": provider_validation}
    provider_publish = atomic_publish_dir(tmp_provider, formal_provider, tmp_provider_publish)
    smoke = staged_model_smoke(formal_provider, args.asof, symbols, publish_dir / "reports")
    return {
        "status": "published" if smoke.get("status") == "pass" else "published_but_smoke_failed",
        "backup": backup,
        "normalized_publish": normalized_publish,
        "provider_rebuild": rebuild,
        "provider_validation": provider_validation,
        "provider_publish": provider_publish,
        "model_smoke": smoke,
        "formal_provider_mutated": True,
        "legacy_formal_provider_mutated": False,
        "legacy_formal_normalized_mutated": False,
    }


def rollback(publish_job_id: str) -> dict[str, Any]:
    publish_dir = OPS_ROOT / publish_job_id
    rollback_dir = publish_dir / f"rollback_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    backup_root = publish_dir / "backup"
    errors: list[str] = []
    if not publish_dir.exists():
        errors.append("publish_job_missing")
    if not backup_root.exists():
        errors.append("backup_root_missing")
    if errors:
        payload = {"status": "rollback_not_possible", "errors": errors, "publish_job_id": publish_job_id}
    else:
        rollback_dir.mkdir(parents=True, exist_ok=True)
        restored = []
        removed = []
        backup_report_path = publish_dir / "reports/backup_report.json"
        backup_report = read_json(backup_report_path) if backup_report_path.exists() else {}
        backup_results = backup_report.get("results", {})
        normalized_backup = backup_results.get("formal_normalized", {})
        provider_backup = backup_results.get("formal_provider", {})
        if normalized_backup.get("status") == "source_missing_first_publish":
            remove_path(OPTION_C_FORMAL_NORMALIZED)
            removed.append("formal_normalized")
        elif (backup_root / "formal_normalized").exists():
            copytree_replace(backup_root / "formal_normalized", OPTION_C_FORMAL_NORMALIZED)
            restored.append("formal_normalized")
        if provider_backup.get("status") == "source_missing_first_publish":
            remove_path(OPTION_C_FORMAL_PROVIDER)
            removed.append("formal_provider")
        elif (backup_root / "formal_provider").exists():
            copytree_replace(backup_root / "formal_provider", OPTION_C_FORMAL_PROVIDER)
            restored.append("formal_provider")
        payload = {
            "status": "rollback_completed",
            "publish_job_id": publish_job_id,
            "restored": restored,
            "removed_first_publish_paths": removed,
            "backup_report": rel(backup_report_path) if backup_report_path.exists() else None,
            "after_state": {
                "option_c_formal_normalized": path_summary(OPTION_C_FORMAL_NORMALIZED),
                "option_c_formal_provider": path_summary(OPTION_C_FORMAL_PROVIDER),
                "legacy_formal_normalized_observed_only": path_summary(LEGACY_FORMAL_NORMALIZED),
                "legacy_formal_provider_observed_only": path_summary(LEGACY_FORMAL_PROVIDER),
            },
            "latest_signal_updated": False,
            "rollback_dir": rel(rollback_dir),
        }
    write_json(rollback_dir / "rollback_report.json", payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return payload


def write_markdown_report(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "---",
        f"created_at: {utc_now()}",
        f"status: {payload.get('status')}",
        "scope: option_c_yahoo_scrapling_publish_rollback_report",
        "---",
        "",
        "# Option C Yahoo Scrapling Publish/Rollback Report",
        "",
        "## Summary",
        "",
        f"- publish_job_id: `{payload.get('publish_job_id')}`",
        f"- mode: `{payload.get('mode')}`",
        f"- status: `{payload.get('status')}`",
        f"- provider_scope: `{payload.get('provider_scope')}`",
        f"- asof: `{payload.get('asof')}`",
        f"- staged_gate: `{payload.get('staged_gate', {}).get('status')}`",
        f"- publish_result: `{payload.get('publish_result', {}).get('status')}`",
        f"- daily_signal_dry_run: `{payload.get('daily_signal_dry_run', {}).get('status')}`",
        f"- latest_signal_unchanged: `{payload.get('daily_signal_dry_run', {}).get('latest_signal_unchanged')}`",
        "",
        "## Payload",
        "",
        "```json",
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        "```",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish or dry-run-publish reviewed Option C Yahoo Scrapling staged refresh.")
    parser.add_argument("--job-dir", help="Reviewed staged job directory under qlib root.")
    parser.add_argument("--asof", help="Selected asof YYYY-MM-DD.")
    parser.add_argument("--mode", choices=["dry-run-publish", "publish"], default="dry-run-publish")
    parser.add_argument("--provider-scope", choices=["option_c_150"], default="option_c_150")
    parser.add_argument("--publish-job-id", default=None)
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--rollback", default=None, help="Rollback a prior publish job id and exit.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.rollback:
        payload = rollback(args.rollback)
        return 0 if payload.get("status") == "rollback_completed" else 1
    if not args.job_dir or not args.asof:
        raise SystemExit("--job-dir and --asof are required unless --rollback is used")
    job_dir = resolve_job_dir(args.job_dir)
    pd_asof = args.asof
    publish_job_id = args.publish_job_id or f"option_c_yahoo_scrapling_publish_{pd_asof.replace('-', '')}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    publish_dir = OPS_ROOT / publish_job_id
    reports_dir = publish_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    paths = provider_paths(args.provider_scope)
    staged_gate = validate_staged_job(job_dir, pd_asof)
    backup_plan = build_backup_plan(paths, publish_dir)
    payload: dict[str, Any] = {
        "publish_job_id": publish_job_id,
        "created_at": utc_now(),
        "mode": args.mode,
        "provider_scope": args.provider_scope,
        "provider_strategy": "Strategy A: Option C dedicated 150-symbol formal normalized/provider; legacy wider provider remains observed-only and is not overwritten",
        "asof": pd_asof,
        "staged_job_dir": rel(job_dir),
        "publish_dir": rel(publish_dir),
        "staged_gate": staged_gate,
        "backup_plan": backup_plan,
        "formal_paths": {key: rel(value) for key, value in paths.items()},
        "latest_signal_before": file_fingerprint(LATEST_SIGNAL),
        "latest_signal_updated": False,
        "normal_signal_run": False,
        "trading": {
            "orders_enabled": False,
            "connects_to_broker": False,
            "paper_orders_enabled": False,
            "live_trading_enabled": False,
            "quick_trade_enabled": False,
            "writes_orders": False,
            "writes_positions": False,
            "research_signal_not_order": True,
        },
        "errors": [],
    }
    status = "failed"
    try:
        if staged_gate.get("status") != "pass":
            status = "pre_publish_gate_failed"
            raise RuntimeError("staged pre-publish gate failed")
        if args.mode == "dry-run-publish":
            payload["publish_result"] = {
                "status": "dry_run_only_no_mutation",
                "normalized_publish": "planned_not_executed",
                "provider_publish": "planned_not_executed",
                "rollback": "designed_not_executed_without_publish",
            }
        else:
            payload["publish_result"] = execute_publish(args, publish_dir, paths)
            if payload["publish_result"].get("status") not in {"published"}:
                status = "publish_failed"
                raise RuntimeError("publish failed")
        payload["daily_signal_dry_run"] = run_daily_signal_dry_run(pd_asof, publish_dir)
        if payload["daily_signal_dry_run"].get("status") != "pass":
            status = "daily_signal_dry_run_failed"
            raise RuntimeError("daily signal dry-run failed")
        payload["latest_signal_after"] = file_fingerprint(LATEST_SIGNAL)
        payload["latest_signal_updated"] = payload["latest_signal_before"] != payload["latest_signal_after"]
        if payload["latest_signal_updated"]:
            status = "latest_signal_changed_unexpectedly"
            raise RuntimeError("latest_signal.json changed unexpectedly")
        status = "publish_dry_run_complete_waiting_for_review" if args.mode == "dry-run-publish" else "publish_complete_waiting_for_review"
    except Exception as exc:
        payload["errors"].append(str(exc))
        payload.setdefault("publish_result", {"status": "not_run"})
        payload.setdefault("daily_signal_dry_run", {"status": "not_run"})
        payload.setdefault("latest_signal_after", file_fingerprint(LATEST_SIGNAL))
    finally:
        payload["status"] = status
        payload["completed_at"] = utc_now()
        write_json(reports_dir / "publish_execution_summary.json", payload)
        payload["artifact_manifest"] = artifact_manifest(publish_dir)
        write_json(reports_dir / "artifact_manifest.json", payload["artifact_manifest"])
        report_path = Path(args.report_path)
        if not report_path.is_absolute():
            report_path = ROOT / report_path
        write_markdown_report(report_path, payload)
        write_markdown_report(reports_dir / "publish_report.md", payload)
        print(json.dumps({"status": status, "publish_job_id": publish_job_id, "publish_dir": rel(publish_dir), "report": rel(report_path), "errors": payload["errors"]}, ensure_ascii=False, indent=2))
    return 0 if status in {"publish_dry_run_complete_waiting_for_review", "publish_complete_waiting_for_review"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
